# ⏱️ Interval Timer

A single-file, multi-sport interval / round / lap timer that runs entirely in
your phone's browser. No install, no account, no network needed.

> Started life as a boxing round timer; now a general training timer. The
> folder name stays `boxing-timer` so existing links keep working.

## Features

**Timer modes**
- **Rounds** — work / rest × rounds (boxing, MMA, etc.)
- **Intervals** — build a custom sequence of named steps, repeated for N sets
  (Tabata, HIIT, running, circuits)
- **Stopwatch** — count up with lap splits

**Sport presets** — Boxing, MMA, Tabata, HIIT, Running, Circuit (one tap to
load sensible defaults, then tweak).

**Cues**
- Voice announcements (speaks each interval name aloud)
- Selectable bell sounds (Classic, Boxing Bell, Triple Beep, Air Horn, Chime,
  Buzzer) + last-3-seconds countdown beeps
- Vibration on transitions
- Audio layers over Spotify / Apple Music without pausing it

**Customisable look & feel** — 6 themes (Midnight, Carbon, Slate, Ocean, Light,
Sand) + 8 accent colours.

**Training log** — every completed session is saved locally; the History
screen shows weekly totals and a day streak. (Designed to later sync to a
backend for cross-device reports.)

**Quality-of-life** — keeps the screen awake while running (Wake Lock),
remembers all settings between sessions.

## Use it on your phone

Open the hosted URL in Safari/Chrome, then **Share → Add to Home Screen** for a
full-screen, app-like experience. Or host the folder yourself:

```bash
cd apps/boxing-timer
python3 -m http.server 9130
# open http://<your-computer-ip>:9130 on your phone (same Wi-Fi)
```

Port `9130` sits in this repo's `9100–9199` allocation (the backend API owns
`9100`). Before binding it on a fleet Mac, check and claim it against the port
registry (Postgres `fleet.port_registry` on the studioshare VPS):

```bash
ports check 9130   # exit 0 = free, 2 = taken; pick another with: ports next 9100-9199
ports claim 9130 --workspace ai-society-publication-repo --service "boxing-timer static server"
```

Everything lives in `index.html` — no build step, no dependencies.

## Roadmap

- **Phase 1:** the app itself — modes, presets, cues, themes, local log ✅
- **Phase 2:** backend — accounts + cloud sync + reports dashboard ✅
  (optional Supabase; see `SETUP_SUPABASE.md`. Charts live in the standalone
  `apps/dashboard/` app.)
- **Phase 3:** native wrappers (Capacitor) for the App Store & Google Play
- **Backlog:** EMOM / AMRAP / For-Time formats, save named custom workouts,
  Apple Watch, background audio
