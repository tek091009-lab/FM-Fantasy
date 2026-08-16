create extension if not exists pgcrypto;
create schema if not exists private;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  username text not null,
  role text not null check (role in ('creator','user')),
  created_at timestamptz not null default now()
);
create unique index if not exists profiles_username_lower_uq on public.profiles (lower(username));

create table if not exists public.worlds (
  id uuid primary key default gen_random_uuid(),
  creator_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  join_code text not null unique,
  payload jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.world_members (
  world_id uuid not null references public.worlds(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  joined_at timestamptz not null default now(),
  primary key (world_id,user_id)
);

create table if not exists public.manager_states (
  world_id uuid not null references public.worlds(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  primary key (world_id,user_id)
);

create or replace function private.fmfantasy_is_world_member(p_world_id uuid, p_user_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists(select 1 from public.world_members wm where wm.world_id=p_world_id and wm.user_id=p_user_id)
$$;

create or replace function private.fmfantasy_share_world(p_left uuid, p_right uuid)
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists(
    select 1 from public.world_members a
    join public.world_members b on b.world_id=a.world_id
    where a.user_id=p_left and b.user_id=p_right
  )
$$;

revoke all on schema private from public;
grant usage on schema private to authenticated;
revoke all on function private.fmfantasy_is_world_member(uuid,uuid) from public;
revoke all on function private.fmfantasy_share_world(uuid,uuid) from public;
grant execute on function private.fmfantasy_is_world_member(uuid,uuid) to authenticated;
grant execute on function private.fmfantasy_share_world(uuid,uuid) to authenticated;

alter table public.profiles enable row level security;
alter table public.worlds enable row level security;
alter table public.world_members enable row level security;
alter table public.manager_states enable row level security;

create policy "profiles read self or world peers" on public.profiles
for select to authenticated
using (
  user_id=(select auth.uid())
  or private.fmfantasy_share_world((select auth.uid()), user_id)
);

create policy "world members read world" on public.worlds
for select to authenticated
using (private.fmfantasy_is_world_member(id,(select auth.uid())));

create policy "creator updates world" on public.worlds
for update to authenticated
using (creator_id=(select auth.uid()))
with check (creator_id=(select auth.uid()));

create policy "members read memberships" on public.world_members
for select to authenticated
using (private.fmfantasy_is_world_member(world_id,(select auth.uid())));

create policy "members read manager states" on public.manager_states
for select to authenticated
using (private.fmfantasy_is_world_member(world_id,(select auth.uid())));

create policy "manager inserts own state" on public.manager_states
for insert to authenticated
with check (
  user_id=(select auth.uid())
  and private.fmfantasy_is_world_member(world_id,(select auth.uid()))
);

create policy "manager updates own state" on public.manager_states
for update to authenticated
using (user_id=(select auth.uid()))
with check (
  user_id=(select auth.uid())
  and private.fmfantasy_is_world_member(world_id,(select auth.uid()))
);

create or replace function public.fmfantasy_finish_signup(
  p_username text,
  p_role text,
  p_world_name text default null,
  p_join_code text default null
) returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_uid uuid := auth.uid();
  v_world uuid;
  v_code text;
begin
  if v_uid is null then raise exception 'Authentication required'; end if;
  if p_role not in ('creator','user') then raise exception 'Invalid role'; end if;
  if length(trim(p_username)) < 3 then raise exception 'Username is too short'; end if;
  if exists(select 1 from public.profiles where user_id=v_uid) then
    select wm.world_id into v_world from public.world_members wm where wm.user_id=v_uid limit 1;
    return v_world;
  end if;
  if exists(select 1 from public.profiles where lower(username)=lower(trim(p_username))) then
    raise exception 'Username already taken';
  end if;

  insert into public.profiles(user_id,username,role)
  values(v_uid,trim(p_username),p_role);

  if p_role='creator' then
    loop
      v_code := upper(substr(replace(gen_random_uuid()::text,'-',''),1,6));
      exit when not exists(select 1 from public.worlds where join_code=v_code);
    end loop;
    insert into public.worlds(creator_id,name,join_code)
    values(v_uid,coalesce(nullif(trim(p_world_name),''),trim(p_username)||'''s FM Fantasy'),v_code)
    returning id into v_world;
  else
    select id into v_world from public.worlds where join_code=upper(trim(p_join_code)) limit 1;
    if v_world is null then
      delete from public.profiles where user_id=v_uid;
      raise exception 'Creator code not found';
    end if;
  end if;

  insert into public.world_members(world_id,user_id) values(v_world,v_uid);
  insert into public.manager_states(world_id,user_id,state) values(v_world,v_uid,'{}'::jsonb)
  on conflict do nothing;
  return v_world;
end;
$$;

revoke all on function public.fmfantasy_finish_signup(text,text,text,text) from public;
revoke all on function public.fmfantasy_finish_signup(text,text,text,text) from anon;
grant execute on function public.fmfantasy_finish_signup(text,text,text,text) to authenticated;

grant select on public.profiles to authenticated;
grant select, update on public.worlds to authenticated;
grant select on public.world_members to authenticated;
grant select, insert, update on public.manager_states to authenticated;
