# Setup: cloud sync with Supabase (Phase 2a)

This turns on **accounts + cross-device sync + reports**. The timer works fully
without it — this only *adds* backup and sync. One-time setup, ~10 minutes,
**free**.

## 1. Create a free Supabase project
1. Go to **https://supabase.com** → sign up (GitHub or email).
2. Click **New project**. Give it a name (e.g. `interval-timer`), pick a region
   near you, set a database password (save it), and create it.
3. Wait ~2 minutes for it to finish provisioning.

## 2. Create the database tables
1. In your project, open **SQL Editor** (left sidebar) → **New query**.
2. Open `apps/boxing-timer/backend/schema.sql` from this repo, copy the whole
   file, paste it in, and click **Run**. You should see "Success".

## 3. Allow the app to sign users in
1. Go to **Authentication → Sign In / Providers** and make sure **Email** is
   enabled (it is by default). Magic links need no extra setup.
2. Go to **Authentication → URL Configuration** → **Redirect URLs** and add your
   app's address:
   ```
   https://cybernaut6404.github.io/ai-society-publication-repo/apps/boxing-timer/
   https://cybernaut6404.github.io/ai-society-publication-repo/apps/dashboard/
   ```
   (The second is the standalone reports app, which has its own sign-in. Add
   `http://localhost` too if you test locally.)

## 4. Copy your two keys
Go to **Project Settings → API** and copy:
- **Project URL** — looks like `https://abcdefgh.supabase.co`
- **anon / public key** — a long token under "Project API keys" (the *anon*
  one, **not** the service_role key)

> These two are safe to use in the app. The anon key is designed to be public;
> Row-Level Security (from the schema) makes sure each user only ever sees their
> own data.

## 5. Connect the app
1. Open the timer → **⚙️ Settings** → scroll to **Cloud sync** →
   **☁️ Connect cloud backend**.
2. Paste the **Project URL**, then the **anon key**.
3. Enter your email → **Email me a sign-in link** → open the email → tap the
   link. It reopens the app, signed in.
4. Your existing history/workouts upload automatically. On any other device,
   connect the same project + sign in with the same email to see everything.

## 6. View your reports
The reports live in a **separate standalone app** at `apps/dashboard/`
(open it directly, or tap **📊 Open reports dashboard** in the timer's Cloud
sync section). It's self-contained: connect the same Supabase project and sign
in there once — weekly training volume, a per-sport breakdown, total time, and
your current day streak, read from your synced data. (Each chart has a **Table**
toggle if you'd rather read the numbers.) On the same host (e.g. GitHub Pages)
it reuses the backend you already connected in the timer, so it usually needs no
extra setup beyond the sign-in link.

## Troubleshooting
- **"Sign in first" / no email**: check the redirect URL in step 3 matches your
  app URL exactly (including the trailing slash).
- **Sync error mentioning a table**: re-run `schema.sql` (step 2).
- **Nothing appears on the other device**: hit **Sync now** in Settings on both.

## What's next
The reports dashboard (`apps/dashboard/`) reads the `v_weekly_summary` and
`v_sport_totals` views. Future ideas: date-range filters, personal records, and
per-mode breakdowns (EMOM/AMRAP/For-Time).
