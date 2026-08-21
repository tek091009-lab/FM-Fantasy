create or replace function public.fmfantasy_restore_world_backup(p_backup_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
set statement_timeout = '0'
as $function$
declare
  b public.fmfantasy_world_backups%rowtype;
begin
  select * into b
  from public.fmfantasy_world_backups
  where id = p_backup_id;

  if not found then
    raise exception 'Backup not found';
  end if;

  if auth.uid() is null or not exists (
    select 1 from public.worlds w
    where w.id = b.world_id and w.creator_id = auth.uid()
  ) then
    raise exception 'Creator permission required';
  end if;

  perform set_config('fmfantasy.maintenance','on',true);
  perform set_config('statement_timeout','0',true);

  update public.worlds w
  set payload = b.world_row->'payload',
      payload_version = coalesce((b.world_row->>'payload_version')::integer,w.payload_version),
      updated_at = now()
  where w.id = b.world_id;

  delete from public.manager_states where world_id = b.world_id;
  insert into public.manager_states(world_id,user_id,state,updated_at)
  select (r->>'world_id')::uuid,
         (r->>'user_id')::uuid,
         r->'state',
         coalesce(nullif(r->>'updated_at','')::timestamptz, now())
  from jsonb_array_elements(coalesce(b.manager_rows,'[]'::jsonb)) r;

  delete from public.fmfantasy_market_state where world_id = b.world_id;
  insert into public.fmfantasy_market_state(
    world_id,pid,launch_price,current_price,dynamic_price,
    price_change_history,price_baseline_gw,updated_at
  )
  select (r->>'world_id')::uuid,
         r->>'pid',
         (r->>'launch_price')::numeric,
         (r->>'current_price')::numeric,
         (r->>'dynamic_price')::numeric,
         coalesce(r->'price_change_history','[]'::jsonb),
         coalesce(nullif(r->>'price_baseline_gw','')::integer,0),
         coalesce(nullif(r->>'updated_at','')::timestamptz, now())
  from jsonb_array_elements(coalesce(b.market_rows,'[]'::jsonb)) r;

  delete from public.fmfantasy_world_snapshots where world_id = b.world_id;
  insert into public.fmfantasy_world_snapshots(
    id,world_id,snapshot_no,snapshot_date,snapshot_date_source,
    competition_code,latest_gameweek,payload_version,payload,created_at,created_by
  )
  select (r->>'id')::uuid,
         (r->>'world_id')::uuid,
         (r->>'snapshot_no')::bigint,
         nullif(r->>'snapshot_date','')::date,
         r->>'snapshot_date_source',
         r->>'competition_code',
         coalesce(nullif(r->>'latest_gameweek','')::integer,0),
         nullif(r->>'payload_version','')::integer,
         r->'payload',
         coalesce(nullif(r->>'created_at','')::timestamptz,now()),
         nullif(r->>'created_by','')::uuid
  from jsonb_array_elements(coalesce(b.snapshot_rows,'[]'::jsonb)) r;
end;
$function$;

create or replace function public.fmfantasy_undo_last_import(p_world_id uuid)
returns uuid
language plpgsql
security definer
set search_path = ''
set statement_timeout = '0'
as $function$
declare
  v_backup uuid;
begin
  if auth.uid() is null or not exists(
    select 1 from public.worlds w
    where w.id=p_world_id and w.creator_id=auth.uid()
  ) then
    raise exception 'Creator permission required';
  end if;

  perform set_config('statement_timeout','0',true);

  select b.id into v_backup
  from public.fmfantasy_world_backups b
  where b.world_id=p_world_id
    and b.reason='pre-successful-import-auto-v1'
  order by b.created_at desc,b.id desc
  limit 1;

  if v_backup is null then
    raise exception 'No successful import is available to undo';
  end if;

  perform set_config('fmfantasy.maintenance','on',true);
  perform public.fmfantasy_restore_world_backup(v_backup);
  delete from public.fmfantasy_world_backups where id=v_backup;
  return v_backup;
end;
$function$;

grant execute on function public.fmfantasy_restore_world_backup(uuid) to authenticated;
grant execute on function public.fmfantasy_undo_last_import(uuid) to authenticated;
