# FUX-15: keeping maintenance away from the moment that matters

**Date:** 2026-11-23
**Feature:** FUX-15, "Keep maintenance away from the moment that matters", from the family UX plan (read it with `git show b7c6a1a04^:complete2.md`). It is held to [family-interaction-contracts.md](family-interaction-contracts.md).
**Out of scope:** Earshot and the macOS apps.

The moment: "I'm about to record. Please don't make me manage software." Maintenance means update checks and offers, model and tool downloads, cache and library cleanup, re-indexing, migrations and their notices, "what's new", backups, sign-in refresh, tip-of-the-day and consent re-prompts. It must never interrupt recording, playback, dictation, a live broadcast, a save, or the first minute after launch. It waits for a quiet moment or an explicit command, says once what is waiting, and stays reachable later through what each app already has (Notifications, Update History, the Help menu). No new notification centre is added.

## 1. The one rule

`quill/core/maintenance_moment.py` (wx-free, strict-typed) decides when an *automatic* maintenance offer may open. `quill/ui/maintenance_moment_ui.py` is the wx side: `offer_when_quiet` either opens the offer now or holds it and polls every 2 seconds, so a short burst of work between polls is still seen. `quill/ui/maintenance_probes.py` lists, for each app, the state it already keeps that counts as protected work.

An offer is held:

- in the first 60 seconds after launch, when the screen reader is still reading the window;
- while a probe reports protected work (recording, playback, dictation, reading aloud, a live broadcast);
- while the app is not the window in front, which includes a modal on top of it, an open menu and an app hidden in the tray;
- for 20 seconds after that work stops or the app comes back to the front, so the offer never lands on the key that stopped a recording, or on somebody finding their place again;
- until there has been no key press or mouse movement for 10 seconds, so the offer never takes a keystroke meant for the document (Enter would press its default button).

Held offers open one at a time; after one closes, the moment is asked again.

While an offer is held, one sentence says what waits and how to get it now. When work holds it, the sentence names the work: "Update 3.4.0 waits until the recording ends. Help, Check for Updates offers it now." When only timing holds it (the first minute, typing, the window not in front), it says "Update 3.4.0 is ready and waits for a quiet moment." The sentence goes to the status bar and to the record the app already keeps: Notifications in QUILL, Update History in the apps with release channels. It is never spoken, because speech would land on top of the work it is protecting. It is said once for each update, and it is cleared from the status bar as the offer opens. In Radio, Cast and Studio, which rewrite their status bar on every playback change, the line is kept after the app's own status text until then. An explicit command, Help > Check for Updates, never waits: it takes the held offer and opens it straight away.

One held offer is kept for each kind, and a newer one replaces an older one. When the window is gone, the poll stops. A probe that raises an error counts as idle, so a broken probe can never block updates for good. When the app closes with an offer still held, nothing appears at close. The next launch's check finds the update again.

## 2. Inventory, app by app

"Steals focus" means the item can open a modal window or bring a window forward. "Speaks" means it can announce something. **Gap** marks an item that broke the rule before this work.

### QUILL

| Item | When it fires | Steals focus | Speaks | Before | After |
| --- | --- | --- | --- | --- | --- |
| Automatic update check (`main_frame.py`, `_on_update_fetch_done`) | End of deferred startup, at most once a day | Yes: "Update downloaded" modal when the download finishes | Yes: "Downloading update", 25/50/75 percent, "downloaded" | **Gap**: on Stable nothing held it, so the modal could open mid-dictation, over Read Aloud or seconds after launch | Download progress is written, not spoken. The modal waits for a quiet moment (`main_frame_quiet_moment.py`), and the first minute is counted from when the window appears. Check for Updates opens a held update at once. A failed silent check no longer speaks "Update check failed". |
| Update download (`core/updates.py download_release_asset`) | During the download | No | No | **Gap**: written straight to the final file name, so a dropped download left a half-written installer and overwrote a good copy | Streamed to `.partial`, checked for length and checksum, then moved into place. On failure the partial file is removed and any existing file is untouched. |
| Braille Pack question (`_maybe_prompt_braille_pack_install`) | Deferred startup, once after an upgrade | Modal | No | **Gap**: in the first seconds after launch | Waits silently for a quiet moment at launch. It is still immediate when you turn on Braille Mode yourself. |
| Kokoro install question (`_maybe_prompt_kokoro_package_install`) | Deferred startup, once | Modal | No | **Gap**: same as above | Waits silently for a quiet moment. |
| Migration notice (`_surface_migration_notice`) | Deferred startup | Modal only when the person chose "prompt"; spoken by default | Yes | The person's own setting decides, including "silent" | Unchanged: respects the stored choice. |
| Vosk and Sherpa retirement notices | About 1.5 s and 3.5 s after launch | Sherpa: a Yes/No box when old files remain | Yes | Already waits while any modal is open. It is a one-time notice owed under the deprecation policy | Unchanged. A candidate for the shared rule later; see section 4. |
| Dictation recovery ("N recordings await review") | 2 s after launch | No | Yes, forced | It is recovery of the person's own work, not maintenance | Unchanged. |
| Model prewarm, Scribe job resume, prompt migration, recent-files prune, close-time cleanup | Startup and close | No | No | Silent | Unchanged. |
| What's New, companion offers, Pandoc download | On demand only | Yes, when asked | Yes | Correct | Unchanged. |
| Startup tip ("Ready. Tip: ...") | Construction | No | If tips are on | A setting the person controls | Unchanged. |

### QUILL Lite

| Item | When it fires | Steals focus | Speaks | Before | After |
| --- | --- | --- | --- | --- | --- |
| Daily update check (`lite_updates.check_at_launch`) | Right after launch, once a day | Yes: the update offer, parented to the active document | Offer only | **Gap**: opened in the first seconds, while dictating, or over another app | Waits for a quiet moment (probe: dictation). The status bar message cell and Update History say once what waits. Ctrl+Alt+U opens it at once. It opens over the document in use when it opens, since the one the check began in may have been closed. |
| Beta/Dev background download | After the check | Then a modal | "Update X downloaded" | **Gap**: spoke over dictation, and the modal opened at once | "Downloaded" is written to the message cell, and the offer waits for a quiet moment. |
| Pending-work recovery, screen-reader watchdog, inbox poll, prompt migration | Startup | Recovery only | Recovery only | Recovery is the person's own work; the rest are silent | Unchanged. |

### Quill Radio, QUILL Cast, QUILL Studio (shared `app_shell.check_for_app_updates`)

| Item | When it fires | Steals focus | Speaks | Before | After |
| --- | --- | --- | --- | --- | --- |
| Silent update check, Stable | Radio: right after launch, after the last station resumes. Cast: after the library loads and the last episode resumes. Studio: right after launch | Yes: the update offer modal, even from the tray | No | **Gap**: opened over the station or episode that had just resumed, during a recording, over a Studio live broadcast or demo recording, and over a hidden tray window | Waits for a quiet moment. Probes: Radio recording and playback (connecting, buffering, playing, reconnecting); Cast playback and loading; Studio live broadcast, demo recording, capture, protected background jobs and book playback. Update History, or the status bar where an app has no release channel, says once what waits. Check for Updates opens it at once. |
| Silent update check, Beta/Dev | Same | Modal after the download | "Update X downloaded" | **Gap**: only a Radio *recording marker* and Quiet Hours held it. Live playback, Cast and Studio were not considered | The download keeps the existing gate (metered, Quiet Hours, recording). The offer waits for a quiet moment, and "downloaded" is written rather than spoken. |
| Radio launch tasks (catalogue refresh, reminders, feed monitor, missed-recordings report, resume prompt) | Startup and timers | The resume prompt only | Yes | Content and recovery of the person's own recordings, not maintenance; Quiet Hours already respected | Unchanged. |
| Radio portable favourites offer | `main()`, before the window, portable only | Modal | No | Before anything plays | Unchanged. |
| Cast launch digest, feed refresh, family sharing note | After library load | No | Yes | Content | Unchanged. |
| What's New, Last.fm and YouTube sign-in, Piper/Kokoro/DECtalk downloads, Backup and Restore | On demand only | When asked | When asked | Correct | Unchanged. |

### Quill Player, Transcribe, Converter, Inkwell, Weather, Beacon, Social

| App | Maintenance found | Verdict |
| --- | --- | --- |
| Player | None automatic: Check for Updates and What's New are on the Help menu only. | No gap. |
| Transcribe | No automatic update check. The first-run setup dialog is not maintenance and never opens in the tray. Model downloads happen only from the Model Library. The replaced-model removal offer is already suppressed while busy (`will_offer(..., in_use=busy)`). The post-update "I started" notice speaks only after a rollback. | No gap. |
| Converter | No automatic check. The FFmpeg box appears only when you convert, and Get FFmpeg is a menu item. The pending Auphonic note is read from a local file and written to the status bar. | No gap. |
| Inkwell | No automatic check. The launch-heal of the start-with-Windows entry is silent. | No gap. |
| Weather | No automatic check. Alerts are the work itself and keep their own policy (pilot decisions, section 4). | No gap. |
| Beacon | Auto-sync, off by default, makes a database backup and syncs on a timer. | **Gap**: it spoke "Auto-synced. Pushed 0, pulled 0." at every interval and refreshed the list under the reader even when nothing changed, and it ran while a dialog was open. Fixed in the third pull request. |
| Social | The scheduler publishes the person's own scheduled posts, and the feed refresh brings new articles. Both are the work itself, not maintenance. No sign-in refresh prompts. | No gap. |

The post-update "I started" sentence (`quill/ui/updates/started.py`) in every app with release channels is spoken 2.5 s after launch, and only when the updater had to *undo* an update. It is the honest result of something the person chose (FUX-04), it happens rarely, and it is kept.

## 3. Acceptance, from the proposal

- **Identify the app and the useful capability.** Every offer names the app (the update window's first line) and the version. A held offer's line names what waits.
- **A failed download leaves files and the current setup intact.** Downloads go to `.partial` and are moved into place only when whole and verified. Background downloads on Beta and Dev already resumed from `.partial`.
- **No forced restart during protected work.** Nothing installs without the person's button. Under this rule the button is not even offered during protected work.
- **Progress and a usable retry, without stealing focus.** Automatic progress is on the status bar. Check for Updates is the retry, and it opens a held update straight away.
- **Shared runtime and portable copies.** Unchanged: the same edition detection (`install_edition.detect`) chooses the asset.
- **Update notes emphasise changed behaviour.** The offer window still shows the release notes. This work changes when it opens, not what it says.
- **Release gates, and no quiet family install.** Unchanged: each app checks and offers only its own release.

## 4. Left for later

- The Vosk and Sherpa retirement notices in QUILL could use the shared rule instead of their own "wait while a modal is open" retry. They are one-time and already deferred, so they were left alone to keep the change small.
- QUILL's notification list gets the held line. QUILL Lite and the shell apps write it to Update History, which is reachable from Help > Release Channel. Studio has no release channel, so its line goes to the status bar only, and Help > Check for Updates is its route.
- The offer window itself does not yet say why it appeared later than the check. A line such as "held while you dictated" could be added to the shared update notice.
- A modeless QUILL tool window in front holds the offer until QUILL's main window is in front again. That is intended.
- To be checked by hand with a screen reader in a frozen build: an offer arriving 20 seconds after Stop in Radio, an offer arriving when an app comes back from the tray, and a held Beta download offer.
