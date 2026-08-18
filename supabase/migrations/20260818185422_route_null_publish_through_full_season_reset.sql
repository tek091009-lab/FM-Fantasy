do $$
declare
  v_oid oid;
  v_def text;
  v_old text := E'  if p_payload_text is null then\n    update public.worlds set payload=null, updated_at=now() where id=p_world_id;\n    return;\n  end if;';
  v_new text := E'  if p_payload_text is null then\n    perform public.fmfantasy_reset_world_season(p_world_id);\n    return;\n  end if;';
begin
  select p.oid into v_oid
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and p.proname='fmfantasy_publish_world'
    and pg_get_function_identity_arguments(p.oid)='p_world_id uuid, p_payload_text text';
  if v_oid is null then raise exception 'fmfantasy_publish_world(uuid,text) not found'; end if;
  v_def := pg_get_functiondef(v_oid);
  if position(v_old in v_def)=0 then raise exception 'Expected null-publish branch not found'; end if;
  v_def := replace(v_def,v_old,v_new);
  execute v_def;
end $$;
