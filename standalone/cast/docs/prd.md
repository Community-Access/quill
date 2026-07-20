# QUILL Cast -- Product Requirements

Version 1.0

## 1. Product statement

QUILL Cast is QUILL's podcast environment, shipped as its own small Windows app for people who want their shows without loading a full writing environment. It is screen-reader-first, keyboard-complete, and deliberately small.

## 2. Architecture requirement: not a fork

- R-1. All feature code lives in the upstream `quill` package (`quill.apps.podcasts`, `PodcastsMixin`, `AppShellFrame`). This repository contains only the product wrapper (entry point, installer, docs). Nothing here reimplements a feature.
- R-2. The app stays in sync with QUILL by construction: the wrapper depends on `quill` from the upstream repository, and the installer payload is built from an upstream portable bundle. Divergence is only permitted for content that exists because QUILL is not in the picture (branding, installer, app docs).
- R-3. Data is shared, not copied: settings, subscriptions, queue, positions, notes, and downloads live in the same `%APPDATA%\Quill` store QUILL uses. Subscribing in one app is visible in all.

## 3. Scope

In scope (all reused from upstream):

- Subscriptions: search, feed URL, OPML import/export, ACB Media directory, podcast settings.
- **Private feeds**: username/password (HTTP Basic) authentication for protected feeds -- Patreon-style supporter feeds, premium shows, members-only feeds. Prompted automatically when adding a protected feed URL; managed later via **Feed Credentials...** on the show's context menu. Covers refresh, downloads, streaming, transcripts, and chapters for that show, under the security requirements in §8.
- **Main-page library tree**: the same pinned views (Favorites, New Episodes, Continue Listening, Inbox) and nested folders the Podcast Manager shows, right on the main window, with a full context menu (Play/Stop, Favorite toggle, Move to Folder, Unsubscribe, New Folder). Enter on a show plays its next unplayed episode directly.
- **One state-aware transport control** (Play/Pause/Resume) and a **Favorites toggle button** for whatever show is currently playing, mirroring Quill Radio's main-page pattern.
- **Resume Last Episode on Launch** (an appliance switch, backed by a shared recently-played history store) and a **Recently Played** submenu, distinct from the Continue Listening virtual view.
- **Play Queue** reachable as a top-level menu item and a registered command, not only from inside the Manager dialog.
- **Mute/Unmute** for podcast playback.
- The full Podcast Manager: pinned views (Favorites, New Episodes, Continue Listening), Inbox with per-show filing memory, Play Queue with keyboard reordering, Search Everywhere, filters.
- Playback: transport, chapters, volume boost, sleep-timer-safe restore, reliable position saves.
- Feed-provided transcripts (Podcasting 2.0; VTT/SRT/JSON), cached; episode notes with timestamp jump.
- Local podcasts and watched folders (stored outside the synced data folder by construction).
- Downloads: queue, pause/resume all, Always Sync, auto-trim silence, normalize loudness, and **auto-reconnect on a dropped connection** (configurable attempts/wait, mirroring Quill Radio's recording reconnect).
- System tray presence with podcast controls.
- Announcement-engine speech through the user's screen reader.
- Help: Get FFmpeg (recovery download if the bundled copy goes missing), Open in Quill, Redeem Unlock Code (shared unlock store), basic Check for Updates against this repo's releases, About.
- Unlock-gated Audio Description Project menu (top-level) when `future.adp_assistant` is unlocked.

Out of scope, by decision (D-1, "basic level of functionality"):

- Speech transcription engines (whisper.cpp / Faster Whisper / Vosk). Feed transcripts are plain downloads and remain fully functional; generating a transcript from audio is full-QUILL territory.
- QUILL's editor, AI assistants, braille, neural TTS voice stacks (Kokoro/Piper), Pandoc conversions, Quillins. The installer excludes their payloads outright.
- "Send Show Notes to Editor" copies to the clipboard instead (documented standalone difference).
- QUILL's update extras (signed manifest feed, portable zip swaps, version skipping). Check for Updates downloads the installer in-app and offers Install now; the rest stays in QUILL.

## 4. Accessibility requirements

- A-1. Every interactive element has an accessible name; the inventory gate upstream audits the shared surfaces.
- A-2. Focus lands on the library tree at launch; a bare-frame focus dead zone is a defect.
- A-3. All dialogs route through the shared dialog contract (modal ids, focus placement, region announcements).
- A-4. Every action announces its outcome through the announcement engine; silent state changes are defects.
- A-5. Full keyboard operation, including Play Queue reordering; the tray menu is reachable with keyboard alone.

## 5. Packaging requirements

- P-1. PyInstaller onedir build with the app's own icon; Inno Setup installer with its own AppId, installs to its own directory ({autopf}\QUILL Cast), per-user privileges by default.
- P-2. Everything bundled, nothing downloaded at install or runtime: the onedir build carries the whole quill package and data (`collect_all("quill")`); ffmpeg installs to {app}\tools\ffmpeg, found via the wrapper exporting QUILL_APP_ROOT. A portable zip ships the same onedir build plus a `data\` folder that switches storage to travel with the app.
- P-3. Uninstall never deletes `%APPDATA%\Quill` -- QUILL or Quill Radio may still use it. Only the full QUILL uninstaller owns that decision.
- P-4. Upgrade hygiene: the installer wipes its own `{app}\_internal` tree before re-laying files so module renames upstream never leave stale imports.

## 6. Update requirements

- U-1. Help > Check for Updates queries this repository's GitHub releases (newest stable vs running version), downloads the installer in-app with spoken 25/50/75 percent milestones, and offers Install now / Open folder. No background checks in 1.0.
- U-2. Release artifacts are named `QUILL-Cast-Setup-<version>.exe` and tagged `v<version>` so the check can compare.

## 7. Non-goals

macOS/Linux standalone builds (upstream QUILL covers macOS; the tray-icon pattern does not exist there), auto-updating in place, telemetry of any kind. A full DSP effects rack (reverb, tempo/pitch, spatial audio) -- Sound Enhancements (§9) is a small, purpose-built three-band EQ, compressor, and Smart Speed, not a general effects rack. For private feeds: no OAuth/token/cookie auth schemes, no per-episode credentials, no cross-machine credential sync -- one username/password per show, HTTP Basic only.

## 8. Security requirements

- S-1. Feed passwords are stored only in a platform secret store: Windows Credential Manager on installed copies, a DPAPI-encrypted file inside the portable `data` folder in portable mode. Never in `podcasts.json`, settings files, logs, or crash reports.
- S-2. Stored credentials are sent only to the host of the feed URL they belong to. A request for the same show going to any other host (third-party audio CDNs, tokenized enclosure URLs) carries no Authorization header.
- S-3. OPML export never contains credentials, so an exported subscription list is always safe to share. Deleting a show, or clearing its credentials, deletes the stored secret -- no orphaned entries.
- S-4. An authentication failure is reported as such ("feed sign-in failed", pointing at Feed Credentials...), never blurred into a generic network error; background refresh never opens modal credential prompts.

## 9. Since 1.0

- **Sound Enhancements** (Episode > Sound Enhancements...): a three-band equalizer (Bass/Mid/Treble sliders, -12 to +12 dB), a compressor, and Smart Speed (live silence trimming between words/sentences), applied via an ffmpeg filter graph relayed to the playback engine over a loopback-only local HTTP server -- shared with Quill Radio's own Sound Enhancements. Off by default. A "Quick preset" shortcut sets all three sliders at once. Full seek/scrub-bar support while enhanced (an ffmpeg `-ss` restart is how scrubbing works, since a running relay can't be seeked within; duration comes from an independent `ffprobe` call). Every setting is per-podcast: a shared default plus a per-show override, resolved at play time -- the same mechanism playback speed already used.
- **Quieter dialogs and a real "up to date" answer**: dialog-transition announcements are now off by default (Preferences), and a manual Check for Updates that finds nothing newer shows a dialog instead of only announcing it.
- **In-app documentation**: Help > User Guide / Release Notes / Product Requirements open the bundled docs in your browser.
- **Skip Forward/Back and auto-skip intro/outro**: configurable per-podcast skip distances (30s forward/15s back by default) plus per-podcast auto-skip-intro (applies only on a fresh start, never a resume) and auto-skip-outro (ends the episode early through the same code path a natural finish uses, so auto-advance/delete-after-play still fire). New context-aware Skip Settings... dialog, same shape as Sound Enhancements.
- **Playlists**: saved, named episode lists distinct from the transient Play Queue and the fixed pinned views. Smart Playlists re-resolve live from rules (shows, episode status, recency, duration, sort); manual Playlists are a curated, ordered, self-healing list built via each episode's own "Add to Playlist..." context-menu item.
- **Private feeds (username and password)**: HTTP Basic authentication for protected feeds, end to end. Add by Feed URL detects a protected feed and opens a Feed Credentials prompt; **Feed Credentials...** on every show's context menu changes or clears them later. Credentials cover refresh, downloads, streaming, transcripts, and chapters, gated by the same-host rule (S-2); passwords live in the platform secret store (S-1) and never in OPML exports or logs (S-3). Documented portable caveat: DPAPI binding means a stick moved to another PC/account keeps subscriptions but asks for private-feed passwords once more.

See `CHANGELOG.md` for the full, versioned history.
