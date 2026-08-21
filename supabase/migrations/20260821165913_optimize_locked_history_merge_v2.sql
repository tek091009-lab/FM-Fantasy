create or replace function public.fmfantasy_merge_locked_history(p_old jsonb, p_new jsonb)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_new jsonb:=p_new;
  v_cutoff date:=public.fmfantasy_payload_snapshot_date(p_old);
  v_new_date date:=public.fmfantasy_payload_snapshot_date(p_new);
  v_old_done integer:=coalesce(nullif(p_old->'meta'->>'completed_gameweek','')::integer,0);
  v_old_latest integer:=coalesce(nullif(p_old->'meta'->>'latest_gameweek_with_result','')::integer,0);
  v_players jsonb:='[]'::jsonb; v_fixtures jsonb:='[]'::jsonb; v_matches jsonb:='[]'::jsonb; v_stars jsonb:='{}'::jsonb;
  v_old_player_map jsonb:='{}'::jsonb; v_new_pid_set jsonb:='{}'::jsonb;
  p jsonb; op jsonb; v_pid text; hist jsonb; wp jsonb; old_wp jsonb; new_wp jsonb;
  apps_n integer; mins_n numeric; goals_n numeric; assists_n numeric; yc_n numeric; rc_n numeric; saves_n numeric; gc_n numeric; pts_n numeric; avg_rating numeric; form_pts numeric;
begin
  if p_old is null or p_new is null or jsonb_typeof(p_new->'players')<>'array' then return p_new; end if;
  if v_cutoff is not null and v_new_date is not null and v_new_date<v_cutoff then
    raise exception 'FM update blocked: snapshot date regressed from % to %',v_cutoff,v_new_date;
  end if;

  if jsonb_typeof(p_old->'players')='array' then
    select coalesce(jsonb_object_agg(pid,player),'{}'::jsonb) into v_old_player_map
    from (
      select coalesce(value->>'pid',value->>'id') pid,value player
      from jsonb_array_elements(p_old->'players')
    ) q where pid is not null;
  end if;
  select coalesce(jsonb_object_agg(pid,'true'::jsonb),'{}'::jsonb) into v_new_pid_set
  from (
    select coalesce(value->>'pid',value->>'id') pid
    from jsonb_array_elements(p_new->'players')
  ) q where pid is not null;

  for p in select value from jsonb_array_elements(p_new->'players') loop
    v_pid:=coalesce(p->>'pid',p->>'id');
    op:=case when v_pid is null then null else v_old_player_map->v_pid end;
    if op is not null then
      if v_cutoff is not null then
        select coalesce(jsonb_agg(h order by coalesce(h->>'date',''),coalesce(nullif(h->>'gameweek','')::integer,0),coalesce(nullif(h->>'match_id','')::integer,0)),'[]'::jsonb)
        into hist
        from (
          select distinct on (k) h,k,src from (
            select value h, public.fmfantasy_history_key(value) k,0 src
            from jsonb_array_elements(case when jsonb_typeof(op->'history')='array' then op->'history' else '[]'::jsonb end)
            union all
            select value h, public.fmfantasy_history_key(value) k,1 src
            from jsonb_array_elements(case when jsonb_typeof(p->'history')='array' then p->'history' else '[]'::jsonb end)
            where ((value->>'date') ~ '^\d{4}-\d{2}-\d{2}$' and (value->>'date')::date>=v_cutoff)
               or (coalesce(nullif(value->>'gameweek','')::integer,0)>v_old_latest)
          ) s order by k,src
        ) q;
      else
        select coalesce(jsonb_agg(h order by coalesce(nullif(h->>'gameweek','')::integer,0),coalesce(h->>'date',''),coalesce(nullif(h->>'match_id','')::integer,0)),'[]'::jsonb)
        into hist from (
          select value h from jsonb_array_elements(case when jsonb_typeof(op->'history')='array' then op->'history' else '[]'::jsonb end)
          where coalesce(nullif(value->>'gameweek','')::integer,0)<=v_old_done
          union all
          select value h from jsonb_array_elements(case when jsonb_typeof(p->'history')='array' then p->'history' else '[]'::jsonb end)
          where coalesce(nullif(value->>'gameweek','')::integer,0)>v_old_done
        ) q;
      end if;

      old_wp:=case when jsonb_typeof(op->'weekly_points')='object' then op->'weekly_points' else '{}'::jsonb end;
      new_wp:=case when jsonb_typeof(p->'weekly_points')='object' then p->'weekly_points' else '{}'::jsonb end;
      select coalesce(jsonb_object_agg(k,v),'{}'::jsonb) into wp from (
        select key k,value v,0 src from jsonb_each(old_wp)
        union all
        select key k,value v,1 src from jsonb_each(new_wp) where not (old_wp ? key)
      ) q;
      p:=jsonb_set(p,'{history}',hist,true); p:=jsonb_set(p,'{weekly_points}',wp,true);

      select count(*) filter(where coalesce(nullif(h->>'minutes','')::numeric,0)>0),
             coalesce(sum(coalesce(nullif(h->>'minutes','')::numeric,0)),0),coalesce(sum(coalesce(nullif(h->>'goals','')::numeric,0)),0),
             coalesce(sum(coalesce(nullif(h->>'assists','')::numeric,0)),0),coalesce(sum(coalesce(nullif(h->>'yc','')::numeric,0)),0),
             coalesce(sum(coalesce(nullif(h->>'rc','')::numeric,0)),0),coalesce(sum(coalesce(nullif(h->>'saves','')::numeric,0)),0),
             coalesce(sum(coalesce(nullif(h->>'gc','')::numeric,0)),0),coalesce(avg(nullif(h->>'rating','')::numeric),0)
      into apps_n,mins_n,goals_n,assists_n,yc_n,rc_n,saves_n,gc_n,avg_rating from jsonb_array_elements(hist) h;
      select coalesce(sum(value::text::numeric),0) into pts_n from jsonb_each(wp);
      select coalesce(avg(v),0) into form_pts from (select value::text::numeric v from jsonb_each(wp) where key ~ '^[0-9]+$' order by key::integer desc limit 4) z;
      p:=jsonb_set(p,'{apps}',to_jsonb(apps_n),true); p:=jsonb_set(p,'{minutes}',to_jsonb(mins_n),true);
      p:=jsonb_set(p,'{goals}',to_jsonb(goals_n),true); p:=jsonb_set(p,'{assists}',to_jsonb(assists_n),true);
      p:=jsonb_set(p,'{yc}',to_jsonb(yc_n),true); p:=jsonb_set(p,'{rc}',to_jsonb(rc_n),true); p:=jsonb_set(p,'{saves}',to_jsonb(saves_n),true); p:=jsonb_set(p,'{gc}',to_jsonb(gc_n),true);
      p:=jsonb_set(p,'{avg_rating}',to_jsonb(round(avg_rating,2)),true); p:=jsonb_set(p,'{fantasy_points}',to_jsonb(pts_n),true); p:=jsonb_set(p,'{points}',to_jsonb(pts_n),true);
      p:=jsonb_set(p,'{form_points}',to_jsonb(round(form_pts,1)),true); p:=jsonb_set(p,'{form}',to_jsonb(round(form_pts,1)),true);
    end if;
    v_players:=v_players||jsonb_build_array(p);
  end loop;

  if jsonb_typeof(p_old->'players')='array' then
    for op in select value from jsonb_array_elements(p_old->'players') loop
      v_pid:=coalesce(op->>'pid',op->>'id');
      if v_pid is not null and not (v_new_pid_set ? v_pid) then
        op:=jsonb_set(op,'{available}','false'::jsonb,true); op:=jsonb_set(op,'{historical_only}','true'::jsonb,true);
        v_players:=v_players||jsonb_build_array(op);
      end if;
    end loop;
  end if;
  v_new:=jsonb_set(v_new,'{players}',v_players,true);

  select coalesce(jsonb_agg(f order by coalesce(f->>'date',''),coalesce(nullif(f->>'fixture_id','')::integer,0)),'[]'::jsonb) into v_fixtures
  from (
    select distinct on(k) f,k,src from (
      select value f,public.fmfantasy_fixture_key(value) k,0 src from jsonb_array_elements(case when jsonb_typeof(p_old->'fixtures')='array' then p_old->'fixtures' else '[]'::jsonb end) where coalesce(value->>'status','')='played'
      union all
      select value f,public.fmfantasy_fixture_key(value) k,1 src from jsonb_array_elements(case when jsonb_typeof(v_new->'fixtures')='array' then v_new->'fixtures' else '[]'::jsonb end)
      where v_cutoff is null or coalesce(value->>'status','')<>'played' or ((value->>'date') ~ '^\d{4}-\d{2}-\d{2}$' and (value->>'date')::date>=v_cutoff)
      union all
      select value f,public.fmfantasy_fixture_key(value) k,2 src from jsonb_array_elements(case when jsonb_typeof(p_old->'fixtures')='array' then p_old->'fixtures' else '[]'::jsonb end) where coalesce(value->>'status','')<>'played'
    ) s order by k,src
  ) q;
  v_new:=jsonb_set(v_new,'{fixtures}',v_fixtures,true);

  select coalesce(jsonb_agg(m order by coalesce(m->>'date',''),coalesce(nullif(m->>'gameweek','')::integer,0),coalesce(nullif(m->>'fixture_id','')::integer,0)),'[]'::jsonb) into v_matches
  from (
    select distinct on(k) m,k,src from (
      select value m,public.fmfantasy_match_key(value) k,0 src from jsonb_array_elements(case when jsonb_typeof(p_old->'matches')='array' then p_old->'matches' else '[]'::jsonb end)
      union all
      select value m,public.fmfantasy_match_key(value) k,1 src from jsonb_array_elements(case when jsonb_typeof(v_new->'matches')='array' then v_new->'matches' else '[]'::jsonb end)
      where v_cutoff is null or ((value->>'date') ~ '^\d{4}-\d{2}-\d{2}$' and (value->>'date')::date>=v_cutoff) or coalesce(nullif(value->>'gameweek','')::integer,0)>v_old_latest
    ) s order by k,src
  ) q;
  v_new:=jsonb_set(v_new,'{matches}',v_matches,true);

  select coalesce(jsonb_object_agg(k,v),'{}'::jsonb) into v_stars from (
    select key k,value v,0 src from jsonb_each(case when jsonb_typeof(p_old->'star_teams')='object' then p_old->'star_teams' else '{}'::jsonb end)
    union all
    select key k,value v,1 src from jsonb_each(case when jsonb_typeof(v_new->'star_teams')='object' then v_new->'star_teams' else '{}'::jsonb end)
    where not ((case when jsonb_typeof(p_old->'star_teams')='object' then p_old->'star_teams' else '{}'::jsonb end) ? key)
  ) q;
  v_new:=jsonb_set(v_new,'{star_teams}',v_stars,true);

  if v_new_date is not null then v_new:=jsonb_set(v_new,'{meta,snapshot_date}',to_jsonb(v_new_date::text),true); end if;
  v_new:=jsonb_set(v_new,'{meta,snapshot_date_source}',to_jsonb(public.fmfantasy_payload_snapshot_source(p_new)),true);
  v_new:=jsonb_set(v_new,'{meta,previous_snapshot_date}',to_jsonb(case when v_cutoff is null then null else v_cutoff::text end),true);
  v_new:=jsonb_set(v_new,'{meta,historical_frozen_through}',to_jsonb(case when v_cutoff is null then null else v_cutoff::text end),true);
  v_new:=jsonb_set(v_new,'{meta,history_merge_policy}',to_jsonb('accepted snapshot history is immutable; later saves refresh current state and append only new historical rows'::text),true);
  v_new:=jsonb_set(v_new,'{meta,historical_freeze_policy}',to_jsonb('append-only-by-snapshot-date-v1'::text),true);
  return v_new;
end;
$function$;
