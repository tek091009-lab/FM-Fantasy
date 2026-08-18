create or replace function public.fmfantasy_require_v73_fixture_club_mapping_proof()
returns trigger
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_meta jsonb := coalesce(new.payload->'meta','{}'::jsonb);
  v_ev jsonb := null;
  v_clubs integer := 0;
  v_safe integer := 0;
  v_team_count integer := 0;
  v_shift integer := null;
  v_evidence_shift integer := null;
  v_unsafe integer := 0;
  v_name_mismatch integer := 0;
  v_mapping_proof text := '';
  v_squad_policy text := '';
begin
  if auth.uid() is null or new.payload is null or new.payload is not distinct from old.payload then
    return new;
  end if;
  if jsonb_typeof(new.payload->'clubs') <> 'array' then
    raise exception 'FM update blocked: club payload is missing.';
  end if;

  v_clubs := jsonb_array_length(new.payload->'clubs');
  if jsonb_typeof(v_meta->'fixture_club_mapping_evidence')='object' then
    v_ev := v_meta->'fixture_club_mapping_evidence';
  else
    select c.value into v_ev
    from jsonb_array_elements(case when jsonb_typeof(v_meta->'current_season_candidates')='array' then v_meta->'current_season_candidates' else '[]'::jsonb end) c(value)
    where jsonb_typeof(c.value)='object'
      and coalesce(c.value->>'error','')=''
      and nullif(c.value->>'shift','')::integer = nullif(v_meta->>'fixture_to_club_shift','')::integer
    order by
      case when nullif(c.value->>'competition_id','')::integer = nullif(v_meta->>'competition_fixture_id','')::integer then 0 else 1 end,
      coalesce(nullif(c.value->>'expected_name_overlap','')::integer,0) desc
    limit 1;
  end if;

  if v_ev is null or jsonb_typeof(v_ev)<>'object' then
    raise exception 'FM update blocked: current-squad fixture-to-club mapping evidence is missing.';
  end if;

  v_safe := coalesce(nullif(v_ev->>'safe_squad_clubs','')::integer,0);
  v_team_count := coalesce(nullif(v_ev->>'team_count','')::integer,0);
  v_shift := nullif(v_meta->>'fixture_to_club_shift','')::integer;
  v_evidence_shift := nullif(v_ev->>'shift','')::integer;
  v_mapping_proof := coalesce(v_ev->>'mapping_proof','');
  v_squad_policy := coalesce(v_meta->>'current_squad_identity_policy',v_ev->>'squad_policy','');

  if v_clubs < 2 or v_safe <> v_clubs or v_team_count <> v_clubs then
    raise exception 'FM update blocked: fixture-to-club proof covers % safe current squads for % clubs.',v_safe,v_clubs;
  end if;
  if v_shift is null or v_evidence_shift is null or v_shift <> v_evidence_shift then
    raise exception 'FM update blocked: fixture-to-club shift evidence does not match the published shift.';
  end if;
  if v_squad_policy not in ('strict-db-membership-only-no-history-mutation-v68','strict_current_db_membership_only_v68') then
    raise exception 'FM update blocked: strict current-squad identity proof is missing.';
  end if;
  if not (
    coalesce(v_meta->>'fixture_club_mapping_policy','')='current-squad-validated-shift-v73'
    or v_mapping_proof like '%current-db-roster-proof-v79%'
    or v_mapping_proof like '%current-squad%'
  ) then
    raise exception 'FM update blocked: fixture-to-club mapping proof marker is invalid.';
  end if;

  if jsonb_typeof(v_ev->'unsafe_squad_names')='array' then
    v_unsafe := jsonb_array_length(v_ev->'unsafe_squad_names');
  end if;
  if v_unsafe <> 0 then
    raise exception 'FM update blocked: fixture-to-club proof still contains % unsafe current squad(s).',v_unsafe;
  end if;

  with actual as (
    select distinct lower(trim(n)) n
    from jsonb_array_elements(new.payload->'clubs') c
    cross join lateral unnest(array[nullif(c->>'short_name',''),nullif(c->>'name','')]) n
    where n is not null
  ), proven as (
    select distinct lower(trim(x#>>'{}')) n
    from jsonb_array_elements(coalesce(v_ev->'mapped_clubs','[]'::jsonb)) x
    where x#>>'{}' <> ''
  ), published as (
    select distinct lower(trim(coalesce(c->>'short_name',c->>'name',''))) n
    from jsonb_array_elements(new.payload->'clubs') c
    where coalesce(c->>'short_name',c->>'name','') <> ''
  )
  select count(*) into v_name_mismatch
  from (
    (select n from published except select n from proven)
    union all
    (select n from proven except select n from actual)
  ) d;
  if v_name_mismatch <> 0 then
    raise exception 'FM update blocked: proven club identities do not match the published club set.';
  end if;

  return new;
end;
$function$;

create or replace function public.fmfantasy_guard_world_payload_update()
returns trigger
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_new_latest integer := 0;
  v_old_latest integer := 0;
  v_new_completed integer := 0;
  v_old_completed integer := 0;
  v_manager_completed integer := 0;
  v_old_comp text := '';
  v_new_comp text := '';
  v_old_date text := null;
  v_new_date text := null;
  v_missing_manager_ids integer := 0;
  v_same_world boolean := false;
  v_bad_side_sizes integer := 0;
  v_bad_scores integer := 0;
  v_bad_side_duplicates integer := 0;
  v_duplicate_fixture_details integer := 0;
  v_missing_new_fixture_details integer := 0;
  v_bad_club_sizes integer := 0;
  v_match_count integer := 0;
  v_played_results integer := 0;
  v_rich_missing integer := 0;
  v_history_status text := '';
  v_import_mode text := '';
  v_declared_partial boolean := false;
  v_catchup boolean := false;
begin
  if auth.uid() is null or new.payload is null then return new; end if;

  if jsonb_typeof(new.payload->'players') <> 'array' or jsonb_typeof(new.payload->'clubs') <> 'array' then
    raise exception 'FM update blocked: player/club database is incomplete';
  end if;

  with counts as (
    select coalesce(c->>'short_name',c->>'name','') club,
      (select count(*) from jsonb_array_elements(new.payload->'players') p
       where (lower(trim(coalesce(p->>'club',''))) = lower(trim(coalesce(c->>'short_name','')))
          or lower(trim(coalesce(p->>'club',''))) = lower(trim(coalesce(c->>'name',''))))
         and coalesce(p->>'available','true')<>'false'
         and coalesce(p->>'historical_only','false')<>'true') n
    from jsonb_array_elements(new.payload->'clubs') c
  )
  select count(*) into v_bad_club_sizes from counts where n<12 or n>60;
  if v_bad_club_sizes>0 then
    raise exception 'FM update blocked: % current club squad(s) fall outside the safe 12-60 player range',v_bad_club_sizes;
  end if;

  if jsonb_typeof(new.payload->'matches')='array' then
    v_match_count := jsonb_array_length(new.payload->'matches');
    select count(*) into v_bad_side_sizes
    from jsonb_array_elements(new.payload->'matches') m
    where jsonb_typeof(m->'home_players')<>'array' or jsonb_typeof(m->'away_players')<>'array'
       or jsonb_array_length(m->'home_players') not between 11 and 25
       or jsonb_array_length(m->'away_players') not between 11 and 25;
    if v_bad_side_sizes>0 then
      raise exception 'FM update blocked: % retained match(es) have impossible player-block sizes',v_bad_side_sizes;
    end if;

    select count(*) into v_bad_scores
    from jsonb_array_elements(new.payload->'matches') m
    where (
      (select coalesce(sum(coalesce(nullif(r->>'goals','')::integer,0)),0) from jsonb_array_elements(m->'home_players') r)
      +(select coalesce(sum(coalesce(nullif(r->>'own_goals','')::integer,0)),0) from jsonb_array_elements(m->'away_players') r)
    ) <> coalesce(nullif(m->>'home_score','')::integer,0)
       or (
      (select coalesce(sum(coalesce(nullif(r->>'goals','')::integer,0)),0) from jsonb_array_elements(m->'away_players') r)
      +(select coalesce(sum(coalesce(nullif(r->>'own_goals','')::integer,0)),0) from jsonb_array_elements(m->'home_players') r)
    ) <> coalesce(nullif(m->>'away_score','')::integer,0);
    if v_bad_scores>0 then
      raise exception 'FM update blocked: % retained match(es) do not reproduce the official score from decoded player goals',v_bad_scores;
    end if;

    select count(*) into v_bad_side_duplicates
    from jsonb_array_elements(new.payload->'matches') m
    where (select count(*) from jsonb_array_elements(m->'home_players')) <>
          (select count(distinct r->>'player_id') from jsonb_array_elements(m->'home_players') r)
       or (select count(*) from jsonb_array_elements(m->'away_players')) <>
          (select count(distinct r->>'player_id') from jsonb_array_elements(m->'away_players') r)
       or exists(
          select 1 from jsonb_array_elements(m->'home_players') h
          join jsonb_array_elements(m->'away_players') a on h->>'player_id'=a->>'player_id');
    if v_bad_side_duplicates>0 then
      raise exception 'FM update blocked: % retained match(es) contain duplicate/cross-side player IDs',v_bad_side_duplicates;
    end if;

    select count(*)-count(distinct coalesce(m->>'fixture_id','')) into v_duplicate_fixture_details
    from jsonb_array_elements(new.payload->'matches') m;
    if v_duplicate_fixture_details>0 then
      raise exception 'FM update blocked: % duplicate retained match detail row(s) target the same fixture',v_duplicate_fixture_details;
    end if;
  end if;

  v_new_comp := coalesce(new.payload->'meta'->>'competition_code',new.payload->'meta'->>'competition','');
  if old.payload is not null then
    v_old_comp := coalesce(old.payload->'meta'->>'competition_code',old.payload->'meta'->>'competition','');
    v_same_world := v_old_comp<>'' and v_old_comp=v_new_comp;
  end if;

  v_old_latest:=case when v_same_world then coalesce(nullif(old.payload->'meta'->>'latest_gameweek_with_result','')::integer,0) else 0 end;
  v_new_latest:=coalesce(nullif(new.payload->'meta'->>'latest_gameweek_with_result','')::integer,0);
  v_old_completed:=case when v_same_world then coalesce(nullif(old.payload->'meta'->>'completed_gameweek','')::integer,0) else 0 end;
  v_new_completed:=coalesce(nullif(new.payload->'meta'->>'completed_gameweek','')::integer,0);

  if v_same_world and v_new_completed<v_old_completed then
    raise exception 'FM update blocked: shared world completed Gameweek would regress from GW% to GW%',v_old_completed,v_new_completed;
  end if;
  if v_same_world and v_new_latest<v_old_latest and v_new_completed<=v_old_completed then
    raise exception 'FM update blocked: latest played-result Gameweek would regress from GW% to GW%',v_old_latest,v_new_latest;
  end if;

  v_history_status := lower(coalesce(new.payload->'meta'->>'history_coverage_status',''));
  v_rich_missing := coalesce(nullif(new.payload->'meta'->>'rich_matches_missing','')::integer,0);
  v_played_results := coalesce(nullif(new.payload->'meta'->>'played_results','')::integer,0);
  v_import_mode := lower(coalesce(new.payload->'meta'->>'import_mode',new.payload->'meta'->'update_validation'->'summary'->>'import_mode',''));
  v_declared_partial := v_history_status='partial' or v_rich_missing>0 or (v_played_results>v_match_count and v_match_count>0);
  v_catchup := (not v_same_world) or v_old_completed=0;

  if jsonb_typeof(new.payload->'fixtures')='array' then
    select count(*) into v_missing_new_fixture_details
    from jsonb_array_elements(new.payload->'fixtures') f
    where coalesce(nullif(f->>'gameweek','')::integer,0)>v_old_completed
      and coalesce(nullif(f->>'gameweek','')::integer,0)<=v_new_completed
      and (coalesce(f->>'status','')='played' or (f ? 'home_score' and f ? 'away_score' and f->'home_score'<>'null'::jsonb and f->'away_score'<>'null'::jsonb))
      and not exists(
        select 1 from jsonb_array_elements(case when jsonb_typeof(new.payload->'matches')='array' then new.payload->'matches' else '[]'::jsonb end) m
        where coalesce(m->>'fixture_id','')=coalesce(f->>'fixture_id','')
      );
    if v_missing_new_fixture_details>0 and not ((v_catchup or v_import_mode='season') and v_declared_partial and v_match_count>0) then
      raise exception 'FM update blocked: % newly completed fixture(s) have no validated player-level match detail',v_missing_new_fixture_details;
    end if;
  end if;

  select coalesce(max(coalesce(nullif(ms.state->>'completedGameweek','')::integer,0)),0)
  into v_manager_completed from public.manager_states ms where ms.world_id=new.id;
  if v_new_completed<v_manager_completed then
    raise exception 'FM update blocked: managers are completed through GW% but this payload is only completed through GW%',v_manager_completed,v_new_completed;
  end if;

  if v_same_world and jsonb_typeof(old.payload->'matches')='array' then
    select max(nullif(m->>'date','')) into v_old_date from jsonb_array_elements(old.payload->'matches') m;
  end if;
  if jsonb_typeof(new.payload->'matches')='array' then
    select max(nullif(m->>'date','')) into v_new_date from jsonb_array_elements(new.payload->'matches') m;
  end if;
  if v_same_world and v_old_date is not null and v_new_date is not null and v_new_date<v_old_date and v_new_completed<=v_old_completed then
    raise exception 'FM update blocked: retained match date regressed from % to %',v_old_date,v_new_date;
  end if;

  select count(*) into v_missing_manager_ids
  from public.manager_states ms
  cross join lateral jsonb_array_elements_text(case when jsonb_typeof(ms.state->'lockedSquad')='array' then ms.state->'lockedSquad' when jsonb_typeof(ms.state->'squad')='array' then ms.state->'squad' else '[]'::jsonb end) sid
  where ms.world_id=new.id and not exists(
    select 1 from jsonb_array_elements(new.payload->'players') p where coalesce(p->>'pid',p->>'id')=sid
  );
  if v_missing_manager_ids>0 then
    raise exception 'FM update blocked: % protected manager-squad player IDs disappear from the new world',v_missing_manager_ids;
  end if;
  return new;
end;
$function$;
