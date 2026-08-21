-- Live installs used the trg_ prefix for the scorer trigger. Detach both names defensively.
drop trigger if exists trg_fmfantasy_score_managers_after_world_advance on public.worlds;
drop trigger if exists fmfantasy_score_managers_after_world_advance on public.worlds;
