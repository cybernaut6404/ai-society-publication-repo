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

## Cloud sync — deep-link sign-in

The optional Supabase sign-in emails a magic link. In the packaged app that
link must reopen the app, so it uses a custom URL scheme
**`intervaltimer://login-callback`** (PKCE flow: the app exchanges the returned
`code` for a session). The web app keeps using its normal page URL.

The web side is already wired (`../boxing-timer/sync.js` +
`@capacitor/app`'s `appUrlOpen` listener). Three things to register once, on
your Mac / in the Supabase dashboard:

**1. Supabase → Authentication → URL Configuration → Redirect URLs** — add:
```
intervaltimer://login-callback
```

**2. iOS — `ios/App/App/Info.plist`** — add inside the top-level `<dict>`:
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLName</key>
    <string>ai.rickai.intervaltimer</string>
    <key>CFBundleURLSchemes</key>
    <array><string>intervaltimer</string></array>
  </dict>
</array>
```

**3. Android — `android/app/src/main/AndroidManifest.xml`** — add inside the
main `<activity>` (alongside the existing launcher intent-filter):
```xml
<intent-filter android:autoVerify="false">
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="intervaltimer" android:host="login-callback" />
</intent-filter>
```

Then `npm run sync` and rebuild. To test on device/simulator: connect a backend
in Settings → Cloud sync, request a sign-in link, open the email **on the
device**, tap it — it should reopen the app signed in. (If the scheme is
missing, the OS won't hand the link back to the app.)

## What's committed vs generated

| Committed | Generated (git-ignored) |
|---|---|
| `capacitor.config.json`, `package.json`, `copy-web.mjs`, this README | `node_modules/`, `www/`, `ios/`, `android/` |
