-- Interval Timer — Phase 2 backend schema (Supabase / Postgres)
-- Paste this whole file into the Supabase SQL Editor and click "Run".
-- Safe to run more than once (idempotent).

-- ── Profiles ────────────────────────────────────────────────────────────────
create table if not exists public.profiles (
  id           uuid primary key references auth.users on delete cascade,
  display_name text,
  unit_pref    text default 'metric',
  created_at   timestamptz default now()
);

-- ── Saved custom workouts ("My workouts") ───────────────────────────────────
create table if not exists public.workouts (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users on delete cascade,
  client_id  text not null,                 -- id generated on the device
  name       text not null,
  mode       text not null,                 -- rounds|interval|emom|amrap|fortime
  emoji      text,
  config     jsonb not null,                -- the mode's settings snapshot
  updated_at timestamptz default now(),
  created_at timestamptz default now(),
  unique (user_id, client_id)               -- makes sync idempotent
);

-- ── Sessions (the training log) ─────────────────────────────────────────────
create table if not exists public.sessions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users on delete cascade,
  client_id    text not null,
  sport        text,
  mode         text not null,
  started_at   timestamptz not null,
  ended_at     timestamptz,
  duration_sec integer not null,
  completed    boolean default true,
  detail       jsonb,                        -- rounds/laps/tally/splits per mode
  updated_at   timestamptz default now(),
  created_at   timestamptz default now(),
  unique (user_id, client_id)
);

-- ── Keep updated_at fresh on every write ────────────────────────────────────
create or replace function public.touch_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

drop trigger if exists t_workouts_touch on public.workouts;
create trigger t_workouts_touch before update on public.workouts
  for each row execute function public.touch_updated_at();

drop trigger if exists t_sessions_touch on public.sessions;
create trigger t_sessions_touch before update on public.sessions
  for each row execute function public.touch_updated_at();

-- ── Auto-create a profile row when a user signs up ──────────────────────────
create or replace function public.handle_new_user() returns trigger as $$
begin
  insert into public.profiles (id) values (new.id) on conflict do nothing;
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists t_on_auth_user_created on auth.users;
create trigger t_on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- ── Row-Level Security: each user can only touch their own rows ──────────────
alter table public.profiles enable row level security;
alter table public.workouts enable row level security;
alter table public.sessions enable row level security;

drop policy if exists "own profile" on public.profiles;
create policy "own profile" on public.profiles
  for all using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists "own workouts" on public.workouts;
create policy "own workouts" on public.workouts
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "own sessions" on public.sessions;
create policy "own sessions" on public.sessions
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ── Report views (the dashboard reads these) ────────────────────────────────
create or replace view public.v_weekly_summary as
select user_id,
       date_trunc('week', started_at) as week,
       count(*)              as sessions,
       sum(duration_sec)     as total_sec,
       count(distinct sport) as sports
from public.sessions
group by 1, 2;

create or replace view public.v_sport_totals as
select user_id, sport,
       count(*)          as sessions,
       sum(duration_sec) as total_sec
from public.sessions
group by 1, 2;

-- Views inherit the base tables' RLS, so users only ever see their own totals.
