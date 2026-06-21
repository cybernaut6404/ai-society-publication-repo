# 🥊 Boxing Timer

A single-file boxing / interval round timer that runs entirely in your phone's
browser. No install, no account, no network needed — open the page and go.

## What it does

- **Round length** — how long each round is (e.g. 3:00)
- **Number of rounds** — e.g. 12
- **Rest between rounds** — e.g. 1:00
- **Prep countdown** — a "get ready" delay before round 1
- **Sound + warning beeps** — 10-second warning during a round, a bell at the
  end of each round, and a fanfare when the whole workout is done
- **Vibration** on phones that support it
- **Keeps the screen awake** while the timer runs (Wake Lock)
- **Remembers your settings** between sessions (localStorage)

## Use it on your phone

Pick whichever is easiest:

1. **Host it (recommended).** Put this folder on any static host
   (GitHub Pages, Netlify, Vercel, or `python3 -m http.server` on your laptop)
   and open the URL on your phone. Then **Add to Home Screen** so it opens
   full-screen like a native app.
2. **Open the file directly.** Email/AirDrop/save `index.html` to your phone
   and open it in your browser.

### Quick local serve

```bash
cd apps/boxing-timer
python3 -m http.server 8080
# then open http://<your-computer-ip>:8080 on your phone (same Wi-Fi)
```

## Notes

- Tap the big clock to pause/resume.
- Sound needs one tap to start (browsers block audio until you interact) —
  pressing **START** handles that automatically.
- Everything is in `index.html` — no build step, no dependencies.
