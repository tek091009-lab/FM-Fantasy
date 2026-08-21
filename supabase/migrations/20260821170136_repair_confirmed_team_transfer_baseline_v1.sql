create or replace function public.fmfantasy_align_unplayed_manager_entry()
returns trigger
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_world_current integer := 1;
  v_old_entry integer := 1;
  v_new_entry integer := 1;
  v_entry integer := 1;
  v_old_hist_count integer := 0;
  v_old_first boolean := false;
  v_old_confirmed boolean := false;
  v_hist jsonb := '[]'::jsonb;
  v_lineups jsonb := '{}'::jsonb;
  v_hist_count integer := 0;
  v_max_gw integer := 0;
  v_total numeric := 0;
  v_squad_count integer := 0;
  v_locked_count integer := 0;
begin
  if new.state is null then return new; end if;

  select greatest(1,coalesce(
           nullif(w.payload->'meta'->>'current_gameweek','')::integer,
           coalesce(nullif(w.payload->'meta'->>'completed_gameweek','')::integer,0)+1,
           1))
    into v_world_current
  from public.worlds w where w.id=new.world_id;
  if not found then v_world_current:=1; end if;

  v_new_entry := greatest(1,coalesce(nullif(new.state->>'entryGameweek','')::integer,1));

  if tg_op='UPDATE' then
    v_old_entry := greatest(1,coalesce(nullif(old.state->>'entryGameweek','')::integer,1));
    v_old_hist_count := case when jsonb_typeof(old.state->'pointsHistory')='array' then jsonb_array_length(old.state->'pointsHistory') else 0 end;
    v_old_first := coalesce(nullif(old.state->>'firstGameweekPlayed','')::boolean,false);
    v_old_confirmed := coalesce(nullif(old.state->>'teamConfirmed','')::boolean,false);
    if v_old_entry>1 or v_old_hist_count>0 or v_old_first or v_old_confirmed then
      v_entry := v_old_entry;
    else
      v_entry := greatest(v_old_entry,v_world_current);
    end if;
  else
    v_entry := greatest(v_new_entry,v_world_current);
  end if;

  if jsonb_typeof(new.state->'pointsHistory')='array' then
    select coalesce(jsonb_agg(v order by gw),'[]'::jsonb),
           count(*),coalesce(max(gw),0),
           coalesce(sum(coalesce(nullif(v->>'net','')::numeric,nullif(v->>'gross','')::numeric,0)),0)
      into v_hist,v_hist_count,v_max_gw,v_total
    from (
      select value v,coalesce(nullif(value->>'gw','')::integer,0) gw
      from jsonb_array_elements(new.state->'pointsHistory')
      where coalesce(nullif(value->>'gw','')::integer,0)>=v_entry
    ) q;
  end if;

  if jsonb_typeof(new.state->'gameweekLineups')='object' then
    select coalesce(jsonb_object_agg(key,value),'{}'::jsonb)
      into v_lineups
    from jsonb_each(new.state->'gameweekLineups')
    where key ~ '^[0-9]+$' and key::integer>=v_entry;
  end if;

  new.state := coalesce(new.state,'{}'::jsonb) || jsonb_build_object(
    'entryGameweek',v_entry,
    'pointsHistory',v_hist,
    'history',v_hist,
    'gameweekLineups',v_lineups,
    'totalPoints',v_total,
    'completedGameweek',case when v_hist_count>0 then greatest(v_entry-1,v_max_gw) else v_entry-1 end,
    'currentGameweek',case when v_hist_count>0 then greatest(v_entry,v_max_gw+1) else v_entry end,
    'firstGameweekPlayed',(v_hist_count>0)
  );

  if v_hist_count=0 then
    new.state := new.state || jsonb_build_object(
      'freeTransfers',1,
      'lastTransferRollGW',v_entry-1,
      'transferHitThisGW',0
    );
  elsif coalesce(nullif(new.state->>'lastTransferRollGW','')::integer,0)<v_entry-1 then
    new.state := jsonb_set(new.state,'{lastTransferRollGW}',to_jsonb(v_entry-1),true);
  end if;

  v_squad_count := case when jsonb_typeof(new.state->'squad')='array' then jsonb_array_length(new.state->'squad') else 0 end;
  v_locked_count := case when jsonb_typeof(new.state->'lockedSquad')='array' then jsonb_array_length(new.state->'lockedSquad') else 0 end;
  if coalesce(nullif(new.state->>'teamConfirmed','')::boolean,false) and v_squad_count=15 and v_locked_count<>15 then
    new.state := jsonb_set(new.state,'{lockedSquad}',new.state->'squad',true);
    if new.state ? 'bank' then new.state := jsonb_set(new.state,'{lockedBank}',new.state->'bank',true); end if;
    if new.state ? 'captain' then new.state := jsonb_set(new.state,'{lockedCaptain}',new.state->'captain',true); end if;
    if new.state ? 'vice' then new.state := jsonb_set(new.state,'{lockedVice}',new.state->'vice',true); end if;
  end if;

  return new;
end;
$function$;
