# 📱 Interval Timer — native wrapper (Phase 3)

[Capacitor](https://capacitorjs.com) shell that packages the
[Interval Timer](../boxing-timer/) web app as native **iOS** and **Android**
apps for the App Store and Google Play. Same code as the web app — Capacitor
just runs `index.html` inside a native WebView and adds native niceties
(status bar, splash screen, store packaging).

## Prerequisites (on your Mac)

- **Node 18+**
- **iOS**: Xcode + CocoaPods (`sudo gem install cocoapods`)
- **Android**: Android Studio (SDK + an emulator or a device)

## First-time setup

```bash
cd apps/boxing-timer-native
npm install

# Copy the web app into www/ and create the native projects:
npm run copy
npx cap add ios
npx cap add android
```

`npx cap add` generates the `ios/` and `android/` folders on your machine
(they're git-ignored here — regenerate rather than commit them).

## Everyday loop

Edit the web app in `../boxing-timer/`, then:

```bash
npm run ios       # copy → sync → open Xcode  (Cmd-R to run)
npm run android   # copy → sync → open Android Studio (▶ to run)
```

`npm run sync` alone copies the latest web assets into both native projects
without opening an IDE. **Always re-run it after changing the web app** — the
native projects bundle a *copy* of `www/`, they don't live-link it.

## App icon & splash screen

Drop a 1024×1024 `resources/icon.png` and a 2732×2732 `resources/splash.png`
(dark `#0d0d12` background) in this folder, then:

```bash
npm run assets    # generates every icon/splash size for both platforms
npm run sync
```

## Configuration

- **Identifiers** live in `capacitor.config.json`:
  - `appId` — `ai.rickai.intervaltimer` (the bundle/application ID). **Change
    this before your first store upload if you want a different one** — it's
    permanent per app once published. After editing, delete and re-add the
    platforms (`npx cap add ios/android`).
  - `appName` — `Interval Timer` (home-screen label).
- `backgroundColor` / `SplashScreen` are pre-set to the app's dark theme.
- The web app applies status-bar styling and hides the splash via a small
  Capacitor-guarded script at the end of `../boxing-timer/index.html` (a no-op
  in a normal browser).

## Cloud sync note

The optional Supabase magic-link sign-in redirects back to the app. For the
packaged app you'll want a custom URL scheme / deep link (e.g.
`intervaltimer://`) added to the Supabase redirect list and the native config —
not required to build and run locally, but needed before shipping sign-in to
the stores. Tracked as a follow-up.

## What's committed vs generated

| Committed | Generated (git-ignored) |
|---|---|
| `capacitor.config.json`, `package.json`, `copy-web.mjs`, this README | `node_modules/`, `www/`, `ios/`, `android/` |
