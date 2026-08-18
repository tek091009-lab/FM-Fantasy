do $repair$
declare
  fn text;
  ddl text;
begin
  foreach fn in array array[
    'fmfantasy_apply_first_seen_price_overrides',
    'fmfantasy_lock_accepted_price_history',
    'fmfantasy_merge_locked_history'
  ] loop
    select pg_get_functiondef(p.oid)
      into ddl
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and p.proname=fn and p.prokind='f'
    limit 1;

    if ddl is null then
      raise exception 'Expected function public.% was not found', fn;
    end if;
    if position('pid text;' in ddl)=0 then
      raise exception 'Expected local pid declaration was not found in public.%', fn;
    end if;

    ddl := replace(ddl, 'pid text;', 'v_pid text;');
    ddl := replace(ddl, 'pid:=', 'v_pid:=');
    ddl := replace(ddl, 'pid is not null', 'v_pid is not null');
    ddl := replace(ddl, '=pid', '=v_pid');

    execute ddl;
  end loop;
end
$repair$;
