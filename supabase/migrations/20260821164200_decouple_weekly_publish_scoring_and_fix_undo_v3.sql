-- Weekly-import reliability v3
-- Keep manager scoring out of the world-publish transaction.
drop trigger if exists fmfantasy_score_managers_after_world_advance on public.worlds;

create or replace function public.fmfantasy_score_managers_after_world_advance()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  v_old integer;
  v_new integer;
begin
  if coalesce(current_setting('fmfantasy.maintenance',true),'')='on'
     or coalesce(current_setting('fmfantasy.maintenance_mode',true),'')='on'
     or coalesce(current_setting('fmfantasy.backup_restore',true),'')='on' then
    return new;
  end if;
  v_old:=coalesce(nullif(old.payload->'meta'->>'completed_gameweek','')::numeric,0)::integer;
  v_new:=coalesce(nullif(new.payload->'meta'->>'completed_gameweek','')::numeric,0)::integer;
  if v_new>v_old then
    perform public.fmfantasy_score_world_managers_internal(new.id,true);
  end if;
  return new;
end;
$function$;

-- Controlled backup restores must be allowed to move the canonical world backwards.
do $patch_guard$
declare
  v_oid oid;
  v_def text;
  v_new text;
  v_anchor text := E'begin\n  if auth.uid() is null or new.payload is null then return new; end if;';
  v_replacement text := E'begin\n  if coalesce(current_setting(''fmfantasy.maintenance'',true),'''')=''on''\n     or coalesce(current_setting(''fmfantasy.backup_restore'',true),'''')=''on'' then\n    return new;\n  end if;\n  if auth.uid() is null or new.payload is null then return new; end if;';
begin
  select p.oid into v_oid
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and p.proname='fmfantasy_guard_world_payload_update'
  limit 1;
  if v_oid is null then raise exception 'fmfantasy_guard_world_payload_update missing'; end if;
  select pg_get_functiondef(v_oid) into v_def;
  if position('fmfantasy.backup_restore' in v_def)=0 then
    v_new:=replace(v_def,v_anchor,v_replacement);
    if v_new=v_def then raise exception 'Could not patch world payload guard maintenance bypass'; end if;
    execute v_new;
  end if;
end;
$patch_guard$;

-- Backups store only the historical snapshot boundary instead of recursively embedding
-- every previous full-world snapshot on every weekly import.
create or replace function public.fmfantasy_backup_world_before_import()
returns trigger
language plpgsql
security definer
set search_path to ''
as $function$
declare
  v_snapshot_boundary bigint := 0;
begin
  if current_setting('fmfantasy.maintenance', true) = 'on' then
    return new;
  end if;
  if old.payload is null or new.payload is not distinct from old.payload then
    return new;
  end if;

  select coalesce(max(ss.snapshot_no),0)
    into v_snapshot_boundary
  from public.fmfantasy_world_snapshots ss
  where ss.world_id=old.id;

  insert into public.fmfantasy_world_backups(
    world_id,created_by,reason,world_row,manager_rows,market_rows,snapshot_rows
  )
  values(
    old.id,
    auth.uid(),
    'pre-successful-import-auto-v1',
    to_jsonb(old),
    coalesce((select jsonb_agg(to_jsonb(ms)) from public.manager_states ms where ms.world_id=old.id),'[]'::jsonb),
    coalesce((select jsonb_agg(to_jsonb(mk)) from public.fmfantasy_market_state mk where mk.world_id=old.id),'[]'::jsonb),
    jsonb_build_object('format','snapshot-boundary-v1','max_snapshot_no',v_snapshot_boundary)
  );

  delete from public.fmfantasy_world_backups b
  where b.world_id=old.id
    and b.reason='pre-successful-import-auto-v1'
    and b.id in (
      select x.id
      from public.fmfantasy_world_backups x
      where x.world_id=old.id and x.reason='pre-successful-import-auto-v1'
      order by x.created_at desc,x.id desc
      offset 6
    );
  return new;
end;
$function$;

-- Restore supports both new compact backups and legacy backups containing full snapshot rows.
create or replace function public.fmfantasy_restore_world_backup(p_backup_id uuid)
returns void
language plpgsql
security definer
set search_path to ''
set statement_timeout to '0'
as $function$
declare
  b public.fmfantasy_world_backups%rowtype;
  v_snapshot_boundary bigint;
begin
  select * into b from public.fmfantasy_world_backups where id=p_backup_id;
  if not found then raise exception 'Backup not found'; end if;
  if auth.uid() is null or not exists(
    select 1 from public.worlds w where w.id=b.world_id and w.creator_id=auth.uid()
  ) then
    raise exception 'Creator permission required';
  end if;

  perform set_config('statement_timeout','0',true);
  perform set_config('fmfantasy.maintenance','on',true);
  perform set_config('fmfantasy.backup_restore','on',true);

  update public.worlds w
  set payload=b.world_row->'payload',
      payload_version=coalesce((b.world_row->>'payload_version')::integer,w.payload_version),
      updated_at=now()
  where w.id=b.world_id;

  delete from public.manager_states where world_id=b.world_id;
  insert into public.manager_states(world_id,user_id,state,updated_at)
  select (r->>'world_id')::uuid,(r->>'user_id')::uuid,r->'state',coalesce(nullif(r->>'updated_at','')::timestamptz,now())
  from jsonb_array_elements(coalesce(b.manager_rows,'[]'::jsonb)) r;

  delete from public.fmfantasy_market_state where world_id=b.world_id;
  insert into public.fmfantasy_market_state(world_id,pid,launch_price,current_price,dynamic_price,price_change_history,price_baseline_gw,updated_at)
  select (r->>'world_id')::uuid,r->>'pid',(r->>'launch_price')::numeric,(r->>'current_price')::numeric,(r->>'dynamic_price')::numeric,
         coalesce(r->'price_change_history','[]'::jsonb),coalesce(nullif(r->>'price_baseline_gw','')::integer,0),coalesce(nullif(r->>'updated_at','')::timestamptz,now())
  from jsonb_array_elements(coalesce(b.market_rows,'[]'::jsonb)) r;

  if jsonb_typeof(b.snapshot_rows)='object'
     and coalesce(b.snapshot_rows->>'format','')='snapshot-boundary-v1' then
    v_snapshot_boundary:=coalesce(nullif(b.snapshot_rows->>'max_snapshot_no','')::bigint,0);
    delete from public.fmfantasy_world_snapshots
    where world_id=b.world_id and snapshot_no>v_snapshot_boundary;
  else
    delete from public.fmfantasy_world_snapshots where world_id=b.world_id;
    insert into public.fmfantasy_world_snapshots(id,world_id,snapshot_no,snapshot_date,snapshot_date_source,competition_code,latest_gameweek,payload_version,payload,created_at,created_by)
    select (r->>'id')::uuid,(r->>'world_id')::uuid,(r->>'snapshot_no')::bigint,nullif(r->>'snapshot_date','')::date,r->>'snapshot_date_source',r->>'competition_code',
           coalesce(nullif(r->>'latest_gameweek','')::integer,0),nullif(r->>'payload_version','')::integer,r->'payload',coalesce(nullif(r->>'created_at','')::timestamptz,now()),nullif(r->>'created_by','')::uuid
    from jsonb_array_elements(coalesce(b.snapshot_rows,'[]'::jsonb)) r;
  end if;
end;
$function$;

alter function public.fmfantasy_publish_world(uuid,text) set statement_timeout='180s';
