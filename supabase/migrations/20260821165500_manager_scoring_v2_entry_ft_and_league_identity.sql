create or replace function public.fmfantasy_score_world_managers_internal(p_world_id uuid, p_apply boolean default true)
returns jsonb
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  v_payload jsonb;v_target integer;v_pmap jsonb;v_report jsonb:='[]'::jsonb;
  v_team_map jsonb:='{}'::jsonb;v_name_map jsonb:='{}'::jsonb;v_uid_map jsonb:='{}'::jsonb;v_squad_map jsonb:='{}'::jsonb;
  r record;r2 record;v_st jsonb;v_original jsonb;v_history jsonb;v_lineup jsonb;v_result jsonb;v_gl jsonb;
  v_entry integer;v_done integer;v_old_done integer;v_gw integer;v_total integer;v_ft integer;v_last_roll integer;
  v_squad_count integer;v_start_count integer;v_bench_count integer;v_cap text;v_vice text;v_username text;v_scored boolean;
  v_patch jsonb;v_team_key text;v_name_key text;v_squad_key text;v_leagues jsonb;v_new_leagues jsonb;v_league jsonb;v_members jsonb;v_new_members jsonb;v_member jsonb;v_source jsonb;
begin
  select payload into v_payload from public.worlds where id=p_world_id;
  if v_payload is null then return jsonb_build_object('ok',false,'error','world payload unavailable'); end if;
  v_target:=coalesce(nullif(v_payload->'meta'->>'completed_gameweek','')::numeric,0)::integer;
  if v_target<1 then return jsonb_build_object('ok',true,'target',v_target,'scored',v_report); end if;
  select coalesce(jsonb_object_agg(pid,p),'{}'::jsonb) into v_pmap from (
    select coalesce(nullif(p->>'pid',''),nullif(p->>'id',''),nullif(p->>'player_id','')) pid,p
    from jsonb_array_elements(coalesce(v_payload->'players','[]'::jsonb)) p
  ) q where pid is not null;

  for r in select user_id,state from public.manager_states where world_id=p_world_id order by updated_at,user_id loop
    v_st:=coalesce(r.state,'{}'::jsonb);v_original:=v_st;
    v_squad_count:=jsonb_array_length(case when jsonb_typeof(v_st->'squad')='array' then v_st->'squad' else '[]'::jsonb end);
    v_start_count:=jsonb_array_length(case when jsonb_typeof(v_st->'starters')='array' then v_st->'starters' else '[]'::jsonb end);
    v_bench_count:=jsonb_array_length(case when jsonb_typeof(v_st->'bench')='array' then v_st->'bench' else '[]'::jsonb end);
    v_cap:=coalesce(v_st->>'captain','');v_vice:=coalesce(v_st->>'vice','');
    if not (coalesce((v_st->>'teamConfirmed')::boolean,false) or (v_squad_count=15 and v_start_count=11 and v_bench_count=4 and v_cap<>'' and v_vice<>'' and v_cap<>v_vice)) then continue; end if;
    if v_squad_count<>15 or v_start_count<>11 or v_bench_count<>4 then continue; end if;
    v_st:=jsonb_set(v_st,'{teamConfirmed}','true'::jsonb,true);
    v_entry:=greatest(1,coalesce(nullif(v_st->>'entryGameweek','')::numeric,1)::integer);
    v_history:=case when jsonb_typeof(v_st->'pointsHistory')='array' then v_st->'pointsHistory' else '[]'::jsonb end;
    select coalesce(max((x->>'gw')::integer),v_entry-1) into v_done from jsonb_array_elements(v_history) x where coalesce((x->>'gw')::integer,0)>=v_entry;
    v_old_done:=v_done;v_scored:=false;
    v_gl:=case when jsonb_typeof(v_st->'gameweekLineups')='object' then v_st->'gameweekLineups' else '{}'::jsonb end;
    if v_done<v_target then
      for v_gw in greatest(v_entry,v_done+1)..v_target loop
        v_lineup:=v_gl->v_gw::text;
        if v_lineup is null or jsonb_array_length(case when jsonb_typeof(v_lineup->'starters')='array' then v_lineup->'starters' else '[]'::jsonb end)<>11 then
          v_lineup:=jsonb_build_object('gw',v_gw,'squad',coalesce(v_st->'squad',v_st->'lockedSquad','[]'::jsonb),'starters',coalesce(v_st->'starters','[]'::jsonb),'bench',coalesce(v_st->'bench','[]'::jsonb),'captain',coalesce(v_st->'captain','null'::jsonb),'vice',coalesce(v_st->'vice','null'::jsonb),'chip',coalesce(v_st->'activeChip','null'::jsonb),'hit',coalesce(nullif(v_st->>'transferHitThisGW','')::numeric,0));
        end if;
        v_result:=public.fmfantasy_score_lineup_json(v_pmap,v_lineup,v_gw);if v_result is null then exit; end if;
        select coalesce(jsonb_agg(x order by (x->>'gw')::integer),'[]'::jsonb) into v_history from (
          select value as x from jsonb_array_elements(v_history) where coalesce((value->>'gw')::integer,0)<>v_gw
          union all select v_result
        ) s;
        v_gl:=jsonb_set(v_gl,array[v_gw::text],jsonb_build_object('gw',v_gw,'squad',coalesce(v_lineup->'squad','[]'::jsonb),'starters',coalesce(v_lineup->'starters','[]'::jsonb),'bench',coalesce(v_lineup->'bench','[]'::jsonb),'captain',coalesce(v_lineup->'captain','null'::jsonb),'vice',coalesce(v_lineup->'vice','null'::jsonb),'chip',coalesce(v_lineup->'chip','null'::jsonb),'hit',coalesce(v_lineup->'hit','0'::jsonb)),true);
        v_done:=v_gw;v_scored:=true;
        v_last_roll:=coalesce(nullif(v_st->>'lastTransferRollGW','')::numeric,0)::integer;
        if v_last_roll<v_gw then
          if v_gw=v_entry then v_ft:=1;
          else v_ft:=least(5,greatest(0,coalesce(nullif(v_st->>'freeTransfers','')::numeric,0)::integer)+1); end if;
          v_st:=jsonb_set(v_st,'{freeTransfers}',to_jsonb(v_ft),true);
          v_st:=jsonb_set(v_st,'{lastTransferRollGW}',to_jsonb(v_gw),true);
        end if;
      end loop;
    end if;
    v_total:=coalesce((select sum(coalesce(nullif(x->>'net','')::numeric,nullif(x->>'gross','')::numeric,0))::integer from jsonb_array_elements(v_history) x),0);
    v_st:=jsonb_set(v_st,'{pointsHistory}',v_history,true);v_st:=jsonb_set(v_st,'{gameweekLineups}',v_gl,true);v_st:=jsonb_set(v_st,'{totalPoints}',to_jsonb(v_total),true);v_st:=jsonb_set(v_st,'{completedGameweek}',to_jsonb(v_done),true);v_st:=jsonb_set(v_st,'{currentGameweek}',to_jsonb(greatest(v_entry,v_done+1)),true);v_st:=jsonb_set(v_st,'{firstGameweekPlayed}',to_jsonb(jsonb_array_length(v_history)>0),true);v_st:=jsonb_set(v_st,'{transferHitThisGW}','0'::jsonb,true);v_st:=jsonb_set(v_st,'{activeChip}','null'::jsonb,true);
    select username into v_username from public.profiles where user_id=r.user_id;
    v_patch:=jsonb_build_object('user_id',r.user_id::text,'name',coalesce(nullif(v_st->>'managerName',''),v_username,''),'managerName',coalesce(nullif(v_st->>'managerName',''),v_username,''),'team',coalesce(v_st->>'teamName',''),'teamName',coalesce(v_st->>'teamName',''),'points',v_total,'totalPoints',v_total,'pointsHistory',v_history,'currentGameweek',greatest(v_entry,v_done+1),'completedGameweek',v_done,'entryGameweek',v_entry,'teamConfirmed',true,'squad',coalesce(v_st->'squad','[]'::jsonb),'starters',coalesce(v_st->'starters','[]'::jsonb),'bench',coalesce(v_st->'bench','[]'::jsonb),'captain',coalesce(v_st->'captain','null'::jsonb),'vice',coalesce(v_st->'vice','null'::jsonb),'gameweekLineups',v_gl);
    v_team_key:=public.fmfantasy_norm_text(coalesce(v_st->>'teamName',v_st->>'team',''));
    v_name_key:=public.fmfantasy_norm_text(coalesce(v_st->>'managerName',v_st->>'name',v_username,''));
    select coalesce(string_agg(x,',' order by x),'') into v_squad_key from jsonb_array_elements_text(coalesce(v_st->'squad','[]'::jsonb)) as t(x);
    v_uid_map:=jsonb_set(v_uid_map,array[r.user_id::text],v_patch,true);
    if v_team_key<>'' then v_team_map:=jsonb_set(v_team_map,array[v_team_key],v_patch,true); end if;
    if v_name_key<>'' then v_name_map:=jsonb_set(v_name_map,array[v_name_key],v_patch,true); end if;
    if v_squad_key<>'' then v_squad_map:=jsonb_set(v_squad_map,array[v_squad_key],v_patch,true); end if;
    v_report:=v_report||jsonb_build_array(jsonb_build_object('user_id',r.user_id,'username',v_username,'from_gw',v_old_done,'to_gw',v_done,'scored',v_scored,'total',v_total,'gw_points',coalesce((select (x->>'net')::integer from jsonb_array_elements(v_history) x where (x->>'gw')::integer=v_target limit 1),0)));
    if p_apply and v_st is distinct from v_original then update public.manager_states set state=v_st,updated_at=now() where world_id=p_world_id and user_id=r.user_id; end if;
  end loop;

  if p_apply then
    for r2 in select user_id,state from public.manager_states where world_id=p_world_id loop
      v_st:=coalesce(r2.state,'{}'::jsonb);v_leagues:=case when jsonb_typeof(v_st->'leagues')='array' then v_st->'leagues' else '[]'::jsonb end;v_new_leagues:='[]'::jsonb;
      for v_league in select value from jsonb_array_elements(v_leagues) loop
        v_members:=case when jsonb_typeof(v_league->'members')='array' then v_league->'members' else '[]'::jsonb end;v_new_members:='[]'::jsonb;
        for v_member in select value from jsonb_array_elements(v_members) loop
          v_source:=null;
          if coalesce(v_member->>'user_id','')<>'' then v_source:=v_uid_map->(v_member->>'user_id'); end if;
          if v_source is null then v_source:=coalesce(v_team_map->public.fmfantasy_norm_text(coalesce(v_member->>'team',v_member->>'teamName','')),v_name_map->public.fmfantasy_norm_text(coalesce(v_member->>'name',v_member->>'managerName',''))); end if;
          if v_source is null and jsonb_typeof(v_member->'squad')='array' then
            select coalesce(string_agg(x,',' order by x),'') into v_squad_key from jsonb_array_elements_text(v_member->'squad') as t(x);
            if v_squad_key<>'' then v_source:=v_squad_map->v_squad_key; end if;
          end if;
          if v_source is not null then v_member:=v_member||v_source; end if;
          v_new_members:=v_new_members||jsonb_build_array(v_member);
        end loop;
        v_league:=jsonb_set(v_league,'{members}',v_new_members,true);v_new_leagues:=v_new_leagues||jsonb_build_array(v_league);
      end loop;
      if v_new_leagues is distinct from v_leagues then v_st:=jsonb_set(v_st,'{leagues}',v_new_leagues,true);update public.manager_states set state=v_st,updated_at=now() where world_id=p_world_id and user_id=r2.user_id;end if;
    end loop;
  end if;
  return jsonb_build_object('ok',true,'version','server-authoritative-manager-scoring-v2','target',v_target,'applied',p_apply,'managers',v_report);
end;
$function$;
