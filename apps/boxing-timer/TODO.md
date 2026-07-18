# Interval Timer — Backlog & Run Protocol

Single source of truth for what's left across the three apps:
`apps/boxing-timer/` (web), `apps/dashboard/` (reports), `apps/boxing-timer-native/` (Capacitor).

## How I run this (so you don't have to repeat it)

- **Long uninterrupted runs.** I pick up **Category A** items and work through as many
  as I can in one go — no yes-clicking between them.
- **I never block on Category B mid-run.** If a solo task turns out to need your
  input, I park it, note why, and move to the next solo task.
- **End of every run I report, in this exact shape:**
  1. **% complete by category** (A and B)
  2. **What's left**
  3. **What I can do next by myself** (Category A)
  4. **What I need from you** (Category B) — the specific action, not a vague ask
- I don't wait to be asked "what can you do" — the next-steps are always in the report.
- Ports: if a task needs one, I check the fleet registry (`ports check`), take a free
  one, and `ports claim` it. Nothing in the current backlog binds a port.

Status keys: `[ ]` todo · `[~]` in progress / parked · `[x]` done.

---

## ✅ Shipped baseline (already merged to `master`)
- Phase 1 — timer app (modes, presets, cues, themes, local log)
- Phase 2 — optional Supabase cloud sync + standalone reports dashboard + report-view RLS fix
- Phase 3 — Capacitor iOS + Android scaffold
- Native deep-link magic-link sign-in — **verified live on both iOS & Android simulators**

---

## Category A — I can do myself (no input needed)   `0/9 · 0%`

- [ ] **A1. App icon + splash source art.** Generate `resources/icon.png` (1024²) and
      `resources/splash.png` (2732², dark `#0d0d12`), commit them, confirm `npm run assets` wiring.
- [ ] **A2. PWA install + offline.** Add a web app manifest + service worker to
      `apps/boxing-timer/` so the web version installs to home screen and works offline.
- [ ] **A3. GitHub Pages deploy workflow.** `.github/workflows/pages.yml` that publishes
      `apps/` to Pages on push to `master`. (Enabling Pages is a B item — see B3.)
- [ ] **A4. CI + committed tests.** Move the ad-hoc dashboard/sync test harnesses into
      `apps/.../tests/` and run them in GitHub Actions on PRs.
- [ ] **A5. Dashboard: date-range filter** (last 7 / 30 / 90 / all).
- [ ] **A6. Dashboard: per-mode breakdown** (rounds / interval / EMOM / AMRAP / For-Time) + personal records.
- [ ] **A7. Harden deep-link handler.** Fallback parse of implicit-flow hash tokens; clean ignore of non-login URLs.
- [ ] **A8. Sync status surface.** A small "last synced / pending changes" indicator + a "sign out" affordance in the dashboard.
- [ ] **A9. Top-level product README** tying the three apps together (setup, deploy, store).

## Category B — I need your input / action   `0/7 · 0%`

- [ ] **B1. Real magic-link end-to-end test.** On a device/simulator: connect the backend,
      request a sign-in link, open the email **in the device**, tap → confirm it returns signed in. (~5 min)
- [ ] **B2. Supabase dashboard.** Set **Site URL** to the GitHub Pages URL (currently
      `http://localhost:3000`); confirm all redirect URLs (web, dashboard, `intervaltimer://login-callback`).
- [ ] **B3. Enable GitHub Pages** in repo Settings → Pages (Source = the workflow from A3).
- [ ] **B4. App icon direction.** Approve a generated icon (from A1) or give brand/colour direction.
- [ ] **B5. Store accounts.** Apple Developer Program ($99/yr) + Google Play Console ($25 once), and signing setup.
- [ ] **B6. Store listing assets.** Screenshots, description, privacy-policy URL. (I can draft copy; you provide accounts/URLs.)
- [ ] **B7. Confirm bundle ID.** Keep `ai.rickai.intervaltimer` or change it before first store upload.

---

_Last updated: run that created this file. Percentages recomputed each run._
