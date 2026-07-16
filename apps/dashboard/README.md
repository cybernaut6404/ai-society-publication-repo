# 📊 Reports Dashboard

A **standalone**, single-file reports app for the [Interval Timer](../boxing-timer/).
Experimental — it stands on its own: connect a Supabase project and sign in
right here, no timer required.

Everything is in `index.html` — no build step, no dependencies (it loads the
Supabase JS client from a CDN at runtime, only after you connect a backend).

## What it shows

Read from your synced training data:

- **KPI tiles** — total sessions, total time, current day streak, sports count
- **Weekly volume** — minutes trained per week (missing weeks shown as 0)
- **By sport** — total minutes per sport

Each chart has a **Table** toggle, and the bars carry hover/tap tooltips.

## Use it

1. Open `index.html` (or the hosted URL). If no backend is connected yet, paste
   your Supabase **Project URL** + **anon key** on the connect screen.
2. Sign in with an email magic link (use the same email as the timer).
3. Reports render from your data. Hit **↻ Refresh** to re-pull.

It shares the timer's `itBackend` config on the same origin (e.g. GitHub Pages),
so a project you already connected in the timer is picked up automatically.

## Backend

Data comes from the same Supabase project the timer syncs to — see
[`../boxing-timer/SETUP_SUPABASE.md`](../boxing-timer/SETUP_SUPABASE.md). The
dashboard reads the `v_weekly_summary` and `v_sport_totals` views (plus a light
`sessions` read for the streak); those views enforce row-level security via
`security_invoker`, so you only ever see your own data.

> When hosting, add this app's URL
> (`…/apps/dashboard/`) to Supabase → Authentication → URL Configuration →
> Redirect URLs, so its sign-in link resolves.
