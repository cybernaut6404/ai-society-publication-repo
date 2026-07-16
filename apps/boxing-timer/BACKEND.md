# Backend sketch — Phase 2 (accounts, sync, reports)

Goal: let users **create an account**, have their **workouts and session logs
sync across devices**, and see **reports/dashboards** — while the app keeps
working offline with no account (offline-first).

This is a design sketch, not built yet. It's written so any developer (or a
future session) can implement it directly.

---

## Guiding principles

1. **Offline-first.** The phone's `localStorage` stays the source of truth for
   a logged-out user. Everything works with no network, exactly like today.
2. **Account is optional and additive.** Signing in only *adds* cloud sync +
   the web dashboard. It never gates the timer itself. (Good for App Store
   review and for a free→Pro upgrade path.)
3. **Managed backend, minimal ops.** Use a Backend-as-a-Service so there are no
   servers to run, patch, or scale by hand. Recommended: **Supabase**
   (hosted Postgres + Auth + auto REST API + row-level security). Free tier
   covers early launch ($0); ~$25/mo when it grows.

---

## Recommended stack

| Concern | Choice | Why |
|---|---|---|
| Database | Supabase Postgres | Real SQL → easy reports/aggregations |
| Auth | Supabase Auth | Email magic-link + **Apple** + Google. Apple sign-in is needed for iOS anyway |
| API | Supabase auto REST/GraphQL + one `sync` Edge Function | No API server to write |
| Authorization | Postgres Row-Level Security | Each user can only read/write their own rows — enforced in the DB |
| Web dashboard | A static page in this repo (`apps/dashboard/`) | Same hosting as the timer |
| Native apps | Capacitor wrapper (Phase 3) hits the same API | One backend for web + iOS + Android |

Firebase is a fine alternative, but Postgres makes the reporting queries
(weekly volume, streaks, PRs, per-sport breakdowns) much simpler than
Firestore.

---

## Data model

```sql
-- One row per user (extends Supabase's auth.users)
create table profiles (
  id           uuid primary key references auth.users on delete cascade,
  display_name text,
  unit_pref    text default 'metric',
  created_at   timestamptz default now()
);

-- Saved custom workouts (the "My workouts" list, now cloud-backed)
create table workouts (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users on delete cascade,
  client_id  text not null,               -- id generated on the device
  name       text not null,
  mode       text not null,               -- rounds | interval | emom | amrap | fortime
  emoji      text,
  config     jsonb not null,              -- the mode's settings snapshot
  updated_at timestamptz default now(),
  created_at timestamptz default now(),
  unique (user_id, client_id)             -- makes sync idempotent
);

-- One row per completed/stopped session (the training log)
create table sessions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users on delete cascade,
  client_id    text not null,
  sport        text,
  mode         text not null,
  started_at   timestamptz not null,
  ended_at     timestamptz,
  duration_sec integer not null,
  completed    boolean default true,
  detail       jsonb,                      -- rounds/laps/tally/splits per mode
  created_at   timestamptz default now(),
  unique (user_id, client_id)
);
```

### Row-Level Security (the whole authorization model)

```sql
alter table profiles enable row level security;
alter table workouts enable row level security;
alter table sessions enable row level security;

-- Identical policy pattern on each table:
create policy "own rows" on sessions
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

With RLS on, the client can talk to the auto-generated REST API directly and
still only ever touch its own data — no custom API server needed for CRUD.

### Reports = SQL views

```sql
create view v_weekly_summary as
select user_id,
       date_trunc('week', started_at) as week,
       count(*)               as sessions,
       sum(duration_sec)      as total_sec,
       count(distinct sport)  as sports
from sessions group by 1,2;

create view v_sport_totals as
select user_id, sport,
       count(*) as sessions, sum(duration_sec) as total_sec
from sessions group by 1,2;
```

The dashboard reads these views; new report types are just new views.

---

## Sync flow (offline-first)

Each locally-created workout/session already gets a unique `id` (we use
`Date.now()` today; switch to a UUID `client_id`). Sync is a
**last-write-wins upsert** keyed on `(user_id, client_id)`:

```
On login OR on regaining network:
  PUSH:  upsert all local rows changed since last_sync  → sessions/workouts
  PULL:  GET rows where updated_at > last_sync          → merge into local
  store last_sync = now()
Conflict: newer updated_at wins (fine for single-user, multi-device).
```

Logged-out users never sync; their data lives only on the device until they
create an account, at which point the first PUSH uploads their history.

---

## What changes in the current app

Small, contained additions to `index.html` (or a split-out `sync.js`):

1. Swap session/workout `id` for a UUID `client_id` (one-line change).
2. Add a **"Sign in"** row in Settings (Supabase JS client, ~1 file, CDN or
   bundled). Anonymous stays the default.
3. Add a `sync()` call on login, on app open (if signed in), and after each
   logged session.
4. New `apps/dashboard/` page: charts of weekly volume, day streak, per-sport
   totals, personal records — reading the SQL views above.

---

## Build phases

- **2a — Provision:** create Supabase project, run the schema + RLS above.
- **2b — Auth + sync:** add optional sign-in and the `sync()` module to the app.
- **2c — Dashboard:** build `apps/dashboard/` reading the report views.
- **2d — Native hook-up (with Phase 3):** the Capacitor apps use the same API.

## Cost

- Supabase free tier: **$0** (500 MB DB, 50k monthly active users) — plenty for
  launch.
- Supabase Pro: **$25/mo** only once you outgrow the free tier.
- No other backend hosting cost — there's no server to run.

## Monetization tie-in

Natural free vs. paid split:
- **Free:** full timer, local history on one device.
- **Pro:** cloud sync across devices + web dashboard + unlimited history export.
