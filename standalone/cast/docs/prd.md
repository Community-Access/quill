# QUILL Cast -- Product Requirements

Version 2.0.0, released 2026-10-03.

## 1. Product statement

QUILL Cast is QUILL's podcast environment, shipped as its own small Windows app for people who want their shows without loading a full writing environment. It is screen-reader-first, keyboard-complete, and deliberately small.

## 2. Architecture requirement: not a fork

- R-1. All feature code lives in the upstream `quill` package (`quill.apps.podcasts`, `PodcastsMixin`, `AppShellFrame`). This repository contains only the product wrapper (entry point, installer, docs). Nothing here reimplements a feature.
- R-2. The app stays in sync with QUILL by construction: the wrapper depends on `quill` from the upstream repository, and the installer payload is built from an upstream portable bundle. Divergence is only permitted for content that exists because QUILL is not in the picture (branding, installer, app docs).
- R-3. Data is shared, not copied: settings, subscriptions, queue, positions, notes, and downloads live in the same `%APPDATA%\Quill` store QUILL uses. Subscribing in one app is visible in all.

## 3. Scope

In scope (all reused from upstream):

- Subscriptions: search, feed URL, OPML import/export, ACB Media directory, podcast settings, per-podcast settings.
- **Acquisition policy** (1.1): auto-download the newest N episodes per show on subscribe and on every refresh (0/1/3/5/10/all, per-podcast overridable), plus separate toggles for anything queued or in the Inbox. Always Sync is the same instruction as "all" and the two are kept in step.
- **Queue Expiration and Recently Expired** (1.1): a per-podcast age limit removes a queued episode that has waited too long, into a Recently Expired list held for seven days and restorable; only the sweep at the end of that window deletes a downloaded file.
- **Listening statistics** (1.1): an append-only session log with a retention window, summarized by period and by podcast, with CSV export.
- **Quick Actions** (1.1): a user-ordered action list per content type (episode, podcast, queue item). The first entry is what Enter does; the first nine answer to Ctrl+1..Ctrl+9; the whole list is the context-menu order.
- **Storage management** (1.1): total and per-podcast download usage, an age limit, a total cap, an Unheard/All filter that announces what it hid, and a manual Free Up Space.
- **Bulk OPML import** (1.1): planning, deduplication, and an optional concurrent reachability sweep for subscription lists in the thousands, with a report that can write back a pruned copy of the source file.
- **Private feeds**: username/password (HTTP Basic) authentication for protected feeds -- Patreon-style supporter feeds, premium shows, members-only feeds. Prompted automatically when adding a protected feed URL; managed later via **Feed Credentials...** on the show's context menu. Covers refresh, downloads, streaming, transcripts, and chapters for that show, under the security requirements in §8.
- **Main-page library tree**: the same pinned views (Favorites, New Episodes, Continue Listening, Inbox) and nested folders the Podcast Manager shows, right on the main window, with a full context menu (Play/Stop, Favorite toggle, Move to Folder, Unsubscribe, New Folder). Enter on a show plays its next unplayed episode directly.
- **One state-aware transport control** (Play/Pause/Resume) and a **Favorites toggle button** for whatever show is currently playing, mirroring Quill Radio's main-page pattern.
- **Resume Last Episode on Launch** (an appliance switch, backed by a shared recently-played history store) and a **Recently Played** submenu, distinct from the Continue Listening virtual view.
- **Play Queue** reachable as a top-level menu item and a registered command, not only from inside the Manager dialog.
- **Mute/Unmute** for podcast playback.
- The full Podcast Manager: pinned views (Favorites, New Episodes, Continue Listening), Inbox with per-show filing memory, Play Queue with keyboard reordering, Search Everywhere, filters.
- Playback: transport, chapters, volume boost, sleep-timer-safe restore, reliable position saves.
- Feed-provided transcripts (Podcasting 2.0; VTT/SRT/JSON), cached; episode notes with timestamp jump.
- **Bulk actions across the Inbox** (§14): File N to Inbox Folder, Add N to Playlist, Remove N Downloaded Copies -- alongside the queue/download/played trio 1.1.0 shipped.
- **The `.opml` file association** (§14): an opt-in installer task plus a path accepted on the command line, so a subscription list exported from another app opens by double-clicking it.
- **Hold-to-scan at 4x** (§14): Shift+Right held scans forward and releases back to the exact speed you were at, announced at both edges.
- **Continue Listening** (QUILL PRD §5.84i): one list of everything started and unfinished, across every provider the running app has.
- **The rest of the Podcasting 2.0 namespace** (§13): people, soundbites, live items, podroll, funding, location and alternate enclosures, read from the feed and surfaced through **About This Episode...**. Soundbites additionally feed the chapter cascade as an authored tier.
- Local podcasts and watched folders (stored outside the synced data folder by construction).
- Downloads: queue, pause/resume all, Always Sync, auto-trim silence, normalize loudness, and **auto-reconnect on a dropped connection** (configurable attempts/wait, mirroring Quill Radio's recording reconnect).
- System tray presence with podcast controls, plus an opt-in preference that makes Alt+F4 minimize to the tray instead of closing (the titlebar X and Exit keep the configured close behavior).
- Announcement-engine speech through the user's screen reader, **and braille output to the user's display** through the same screen-reader bridge, governed by the shared announcement service (§4).
- **Quillins host**: a top-level Quillins menu running app-targeted, sandboxed, permission-gated extensions, including the bundled `cast-premium-auth` sample. Off in Safe Mode; third-party Quillins remain disabled.
- **Keyboard Shortcuts...** (the shared Keymap Editor, scoped to this app's commands) and **Global Hotkeys...** (system-wide keys for Play/Pause, Stop, and Show/Hide QUILL Cast to the Tray).
- **Spotify podcasts (experimental)**, shipped dark behind `future.spotify`: requires a signed unlock code, Spotify Premium, a user-supplied Client ID, and WebView2. Play-only -- Spotify audio is DRM-protected and cannot be downloaded. Off in Safe Mode.
- Help: Get FFmpeg (recovery download if the bundled copy goes missing), Open in Quill, Redeem Unlock Code (shared unlock store), Check for Updates against this repo's releases, About.

Out of scope, by decision (D-1, "basic level of functionality"):

- Speech transcription engines (whisper.cpp / Faster Whisper / Vosk). Feed transcripts are plain downloads and remain fully functional; generating a transcript from audio is full-QUILL territory.
- QUILL's editor, AI assistants, braille translation stacks (liblouis tables, BRF authoring), neural TTS voice stacks (Kokoro/Piper), Pandoc conversions. The installer excludes their payloads outright. Braille *announcements* are in scope and are not part of those payloads: they are written through the screen reader's own bridge, which requires no translation stack here.
- "Send Show Notes to Editor" copies to the clipboard instead (documented standalone difference).
- QUILL's update extras (signed manifest feed, portable zip swaps, version skipping). Check for Updates downloads the installer in-app and offers Install now; the rest stays in QUILL.

## 4. Accessibility requirements

- A-1. Every interactive element has an accessible name; the inventory gate upstream audits the shared surfaces.
- A-2. Focus lands on the library tree at launch; a bare-frame focus dead zone is a defect.
- A-3. All dialogs route through the shared dialog contract (modal ids, focus placement, region announcements).
- A-4. Every action announces its outcome through the announcement engine; silent state changes are defects.
- A-5. Full keyboard operation, including Play Queue reordering; the tray menu is reachable with keyboard alone.
- A-6. Announcements are delivered by the shared announcement service, not by a per-app path, so a channel added upstream reaches this app automatically. Speech and braille are both required channels; a braille burst is coalesced (first message immediate, newest-wins inside the conflation window) and ERROR-severity messages bypass coalescing entirely and may be held on the display. Braille style, the repeat window, sticky errors, and interrupt severity are shared accessibility settings, edited in QUILL and honored here.
- A-7. Every Yes/No confirmation whose outcome destroys or discards something defaults to No -- Delete Folder, Delete Playlist, Remove All Episodes, Delete Downloaded Files, Mark All as Played, Forget Expired Episode, Remove Downloads, Clear Statistics, Delete All Podcast Data. Enter must always be the safe answer. Enforced upstream by an automated build check over the shared dialog surfaces.
- A-8. **Numbers are spoken as language.** A duration is "3 hours, 47 minutes", never `3:47:00` -- a screen reader reads a clock face as a time of day. A size is "812 MB". Where a report could be a chart, the text is the primary representation and not a caption for a picture of one.
- A-9. **No silent caps.** Where a list is truncated for performance (a cross-show view, a show's episodes in the main tree), the surface says how many it is showing out of how many there are, and where the rest is. A filtered list always says it is filtered.
- A-10. **No fabricated measurements.** A statistic that cannot be measured honestly is omitted, not estimated. Time saved by silence trimming is reported only when the trimming path actually reports what it dropped.

## 5. Packaging requirements

- P-1. PyInstaller onedir build with the app's own icon; Inno Setup installer with its own AppId, installs to its own directory ({autopf}\QUILL Cast), per-user privileges by default.
- P-2. Everything bundled, nothing downloaded at install or runtime: the onedir build carries the whole quill package and data (`collect_all("quill")`); ffmpeg installs to {app}\tools\ffmpeg, found via the wrapper exporting QUILL_APP_ROOT. A portable zip ships the same onedir build plus a `data\` folder that switches storage to travel with the app.
- P-3. Uninstall never deletes `%APPDATA%\Quill` -- QUILL or Quill Radio may still use it. Only the full QUILL uninstaller owns that decision.
- P-4. Upgrade hygiene: the installer wipes its own `{app}\_internal` tree before re-laying files so module renames upstream never leave stale imports.

## 6. Update requirements

- U-1. Help > Check for Updates queries the shared repository's GitHub releases for this app's own asset (newest stable vs running version), downloads it in-app with spoken 25/50/75 percent milestones, and offers Install now / Open folder. A manual check that finds nothing newer shows a dialog, not only a spoken announcement.
- U-2. Release artifacts are named `QUILL-Cast-Setup-<version>.exe` and tagged `v<version>` so the check can compare. Each app carries its own asset prefix so every QuillVille app updates independently from the shared repository.
- U-3. A throttled silent check runs once a day on launch, quiet unless a real update exists; Preferences (Ctrl+,) turns it off.
- U-4. **Install and restart now**: QUILL Cast applies an update itself -- extracting portable files over the existing folder, or running the installer silently -- and relaunches, preserving shows, downloads, and settings. Shared with the rest of the family.

## 7. Non-goals

macOS/Linux standalone builds (upstream QUILL covers macOS; the tray-icon pattern does not exist there), silent or unattended background updating (an update is always offered and accepted before it is applied -- see U-4), telemetry of any kind. Downloading Spotify audio, which is DRM-protected and play-only by design. A full DSP effects rack (reverb, tempo/pitch, spatial audio) -- Sound Enhancements (§9) is a small, purpose-built three-band EQ, compressor, and Smart Speed, not a general effects rack. For private feeds: no OAuth/token/cookie auth schemes, no per-episode credentials, no cross-machine credential sync -- one username/password per show, HTTP Basic only.

Also deliberately not built, and not to be relitigated without new information: **CarPlay / Android Auto / AirPlay / lock-screen / Control Center** -- the tray plus global hotkeys plus media keys *is* the desktop answer, and it is complete. **Paid tiers of any shape** -- subscription plus-tiers, a free-podcast-count limit, paywalls, StoreKit. **Cloud sync, gpodder, or a hosted account** -- QUILL Sync is the family's own answer and a separate programme (see the QUILL PRD). **Dynamic Type, touch-target sizing, Reduce Motion, Material You** -- their desktop equivalents are the shell's job, not this app's. **Cloud transcript generation** -- §3 puts audio-to-text in full QUILL, on the listener's own machine.

## 8. Security requirements

- S-1. Feed passwords are stored only in a platform secret store: Windows Credential Manager on installed copies, a DPAPI-encrypted file inside the portable `data` folder in portable mode. Never in `podcasts.json`, settings files, logs, or crash reports.
- S-2. Stored credentials are sent only to the host of the feed URL they belong to. A request for the same show going to any other host (third-party audio CDNs, tokenized enclosure URLs) carries no Authorization header.
- S-3. OPML export never contains credentials, so an exported subscription list is always safe to share. Deleting a show, or clearing its credentials, deletes the stored secret -- no orphaned entries.
- S-4. An authentication failure is reported as such ("feed sign-in failed", pointing at Feed Credentials...), never blurred into a generic network error; background refresh never opens modal credential prompts.

## 9. Performance requirements (1.1)

A subscription list exported from another app after a decade of listening is
routinely more than a thousand feeds. Every requirement here was written
against a real one (1,307 feeds), refreshed to roughly 196,000 episodes.

- **PF-1. Nothing quadratic on import.** Duplicate detection and folder
  resolution index once and answer in constant time, so importing N entries
  into a library of M is O(N + M). Duplicates are matched on a normalized
  URL, so `http://` and `https://` forms of one feed are one feed.
- **PF-2. No blocking work in a button handler.** Reading, parsing,
  planning, and adding an OPML file all happen off the UI thread; the
  reachability sweep runs afterwards on a bounded pool, reports progress,
  and can be cancelled without losing what was already imported.
- **PF-3. Saves must not scale with the library.** A full library write is
  ~7 seconds and 164 MB at 196,000 episodes, and it is triggered by every
  position checkpoint. Above a threshold, writes and the main-page tree
  rebuild coalesce onto a short timer; below it they stay immediate. The
  shutdown path always forces a final flush.
- **PF-4. No unbounded list materialization.** Cross-show views fill a
  bounded number of rows, a show's episodes in the main tree are built on
  demand when it is expanded, and both say what they are not showing (A-9).
- **PF-5. Per-refresh work stays proportional to what changed.** Choosing
  the newest N episodes to auto-download does not sort a show's whole
  catalog, and a refresh announces one coalesced summary rather than one
  message per episode.

## 10. Since 1.0

- **Sound Enhancements** (Episode > Sound Enhancements...): a three-band equalizer (Bass/Mid/Treble sliders, -12 to +12 dB), a compressor, and Smart Speed (live silence trimming between words/sentences), applied via an ffmpeg filter graph relayed to the playback engine over a loopback-only local HTTP server -- shared with Quill Radio's own Sound Enhancements. Off by default. A "Quick preset" shortcut sets all three sliders at once. Full seek/scrub-bar support while enhanced (an ffmpeg `-ss` restart is how scrubbing works, since a running relay can't be seeked within; duration comes from an independent `ffprobe` call). Every setting is per-podcast: a shared default plus a per-show override, resolved at play time -- the same mechanism playback speed already used.
- **Quieter dialogs and a real "up to date" answer**: dialog-transition announcements are now off by default (Preferences), and a manual Check for Updates that finds nothing newer shows a dialog instead of only announcing it.
- **In-app documentation**: Help > User Guide / Release Notes / Product Requirements open the bundled docs in your browser.
- **Skip Forward/Back and auto-skip intro/outro**: configurable per-podcast skip distances (30s forward/15s back by default) plus per-podcast auto-skip-intro (applies only on a fresh start, never a resume) and auto-skip-outro (ends the episode early through the same code path a natural finish uses, so auto-advance/delete-after-play still fire). New context-aware Skip Settings... dialog, same shape as Sound Enhancements.
- **Playlists**: saved, named episode lists distinct from the transient Play Queue and the fixed pinned views. Smart Playlists re-resolve live from rules (shows, episode status, recency, duration, sort); manual Playlists are a curated, ordered, self-healing list built via each episode's own "Add to Playlist..." context-menu item.
- **Private feeds (username and password)**: HTTP Basic authentication for protected feeds, end to end. Add by Feed URL detects a protected feed and opens a Feed Credentials prompt; **Feed Credentials...** on every show's context menu changes or clears them later. Credentials cover refresh, downloads, streaming, transcripts, and chapters, gated by the same-host rule (S-2); passwords live in the platform secret store (S-1) and never in OPML exports or logs (S-3). Documented portable caveat: DPAPI binding means a stick moved to another PC/account keeps subscriptions but asks for private-feed passwords once more.

- **Library tree episodes in place**: shows in the main-page tree expand to reveal their episodes (collapsed by default so the tree stays a list of shows), with Enter on an episode playing that episode and Enter on the show still playing its next unplayed one.
- **Playback keyboard shortcuts**: Stop (Ctrl+.), Skip Back/Forward (Ctrl+Left/Right), Volume Down/Up (Ctrl+Down/Up), matching Quill Radio's convention.
- **Focus return after subscribing**: the Add Podcast search path returns focus to the results list and re-selects the subscribed row on success, already-subscribed, and error alike; the Add-by-Feed-URL path deliberately leaves focus by the URL box.
- **Alt+F4 to tray**, opt-in, intercepted at the char hook before Windows converts it to a close; distinct from the configured close action so deliberate exits still exit.
- **Announcement service adoption**: speech and braille both delivered through the shared service, with burst coalescing, sticky errors, compact braille style, and the shared accessibility settings (A-6).
- **Destructive defaults**: the podcast confirmation surfaces default to No (A-7).
- **Quillins app host** and the **Keyboard Shortcuts / Global Hotkeys** managers, both scoped to this app's own command registry.
- **Spotify (experimental, dark)**: unlock-gated, Premium-only, user-supplied Client ID, WebView2-hosted playback; play-only.
- **Startup fix**: the library tree no longer asks Windows to expand its hidden root node, which aborted the app before its window appeared. Guarded on the tree style, with a regression test asserting the guard stays adjacent to the call.

## 11. Since 1.0.7 (1.1.0)

**Acquisition, the layer that was missing.** Through 1.0.x QUILL Cast had a
retention policy and no acquisition policy: it knew what to throw away and
nothing about what to fetch. Auto-download (0/1/3/5/10/all, per podcast) plus
Auto-Queue per show plus per-show new-episode announcements mean subscribing
to a show and pressing play is now one step.

**Sharing and audio export.** "Share this" has no single desktop gesture, and
inventing one would produce a menu item that opens a dialog nobody wants. The
requirement is a **file** the listener can place and an **address** they can
paste: **Save Episode Audio As...**, **Copy Podcast Link**, and **Show in File
Explorer**. All three are Quick Actions entries, never hard-coded menu items,
so they take the listener's order like everything else on those menus.

The normative rule: **saving copies, it never moves.** QUILL Cast goes on
managing its own downloaded copy -- retention, the storage cap, resume, and
Remove Downloaded Copy all still apply to it -- and the saved copy is the
listener's, outside all of that. Moving the managed file would silently break
resume and the download's own bookkeeping. An episode that is not yet
downloaded offers the download and returns, rather than blocking the UI thread
behind a transfer of unknown length.

**Episode notes reachable from the player.** A timestamped note is made *while
listening*, so requiring the listener to leave the player, locate the episode
in the library tree and open a context menu to read notes back was the wrong
shape. `My Notes in This Episode...` acts on whatever is playing; the Manager's
per-episode route stays, and both build the list from one implementation so
their wording cannot drift. **Copy Note** carries the episode, the podcast, the
timestamp, the note and the audio link together -- a note's own text alone is a
fragment with no way back to the moment it marks.

**Re-published episodes resurface.** A publisher re-issuing an episode (a
corrected file, a re-cut, one pulled and reissued) moves its `published` stamp
forward; `merge_episodes` collects those guids at the only moment both stamps
exist, and `inbox.resurface_republished` clears the trim marker so the episode
returns to the Inbox. **The exemptions are normative and are the same three
`trim_inbox` applies** -- played, started (`position_ms > 0`), and queued -- plus
any hand-filed assignment, which is the listener's own and is never overruled by
a publisher. Announced as a re-publication rather than as a new episode: calling
it new would misdescribe what the publisher did.

**Queue Expiration + Recently Expired.** Per-podcast, off by default, with a
seven-day restorable hold. The one migration risk in the release -- a queue
saved before 1.1.0 has no timestamps -- is handled by reading an unstamped
slot as "added now" rather than "infinitely old".

**Listening statistics.** Time listened, extra content bought by speed,
episodes finished, per-podcast breakdown, CSV export, 90-day retention. The
report is a read-only text field you arrow through, and durations are words
(A-8). Time saved by Smart Speed is omitted rather than estimated (A-10).

**Quick Actions.** Three orderable action lists: a chosen default for Enter, a
chosen menu order, and Ctrl+1..Ctrl+9 for the top nine.

**Session control.** Stop After This Episode; the continue-after-queue /
continue-after-group pair (with both off, playback stops at the end of the
current episode); speed as a real 0.5x-5.0x continuum with Speed Up / Speed
Down / Reset commands; Mark All as Played; sleep timer "end of this episode"
and Extend +5.

**Inbox caps and storage management.** Per-podcast Inbox count and age caps
that trim without deleting and never touch anything played, started, or
queued; a Downloads screen with usage, an age limit, a total cap, and Free
Up Space, under the rule that a queued or part-played episode is never
evicted.

**Bulk OPML import.** Threaded, deduplicating, and reportable at the scale a
real subscription list actually reaches -- with a pruning export that writes
the source file back without the feeds that no longer answer (§9).

**Winamp classic transport keys**, shared with Quill Radio's recordings
player rather than reimplemented: `Z X C V B`, arrows to seek, `J`, `Ctrl+J`,
`T`, `L`. On by default, one Preferences checkbox to turn off.

**Two correctness fixes**:
finishing a mid-queue episode now continues from the slot after it instead of
jumping back to the queue head, and chapter auto-skip carries a loop guard so
a seek's own position report cannot re-trigger the skip that caused it.

**Onboarding and one-shot tips** (`core/podcasts/onboarding.py`,
`ui/podcasts/first_run_dialog.py`, persisted on `PodcastLibrary.onboarding`).

**Three screens, not seven.** Welcome, add your first podcast, you're set. Cast
has no account, no tracker and no cloud, so it does not need the privacy screens
a phone app needs -- and a first-run flow that pages somebody through consent
they never gave anything is how people learn to dismiss dialogs unread. The
screens are a **read-only text area**, arrowable and copyable, rather than a wall
of labels: somebody who missed a sentence goes back over it at their own pace
instead of asking the app to repeat itself. **Skip is a first-class button**, and
skipping counts as completed -- it was a choice, and re-showing the flow would be
overriding it with a guess. `needs_first_run` is false for anybody who already
has shows, however they got them (OPML import, restored backup, upgrade):
explaining how to add a first podcast to somebody with two hundred says nobody
checked.

**Tips are one sentence, once ever.** `TIPS` is a reviewable dict rather than
strings at call sites, so the whole set can be audited in one place. Four rules:
once ever (a tip that reappears is an interruption; one that appears once is a
fact you now know); never modal and never focus-stealing -- they ride the ordinary
announcement path, so speech and braille both get them; only where they change
what somebody can *do*, never to explain a button whose label already does; and
**off in one place, permanently**, because somebody who does not want them should
not have to dismiss each one to discover that. `tip_for` and `mark_seen` are
deliberately separate calls, so a tip that could not actually be delivered is not
recorded as shown.

State is **a set of ids, not a version stamp**: a tip added next year must fire
for somebody who has used Cast for a year, and a version number would say they
had already seen it. An unknown id from a newer build is kept rather than
dropped, so moving between builds does not replay tips.

**Prebuffering the next queue item** (`core/podcasts/prebuffer.py`,
`PodcastSettings.prebuffer_next`). Sample-accurate gapless playback is a property
of the *decoder* and neither engine offers it; what is achievable, and what
actually removes the wait, is **having the next episode's first seconds on disk
before the current one ends** -- the switch then costs an open and a seek rather
than a network round trip and a buffer fill.

A pure policy function with every input passed in (`plan`), so it is testable
without a player, a queue or a network: the caller knows what is playing and what
is next, this knows when. Four refusals carry the design: **off unless asked for**
(speculative bytes are paid for by the megabyte on a metered connection), never
for an episode already local (there is nothing to gain), never before the final
`LEAD_MS` (thirty seconds -- longer than a stream takes to open on a poor line,
short enough that skipping around does not trigger it repeatedly), and never for
a source with no known length, because a live item never becomes "nearly over" so
there is no cue to fire on. What it fetches is a **cache** capped at
`PREBUFFER_BYTES`, landing in the playback cache rather than the library, and a
prune may take it. It announces nothing: a player narrating its own buffering is
the wrong kind of feedback.

**Chapter inference: scored answers, a budget, and titles that say what a
section is about** (`core/podcasts/chapter_scoring.py`, `chapter_cascade.py`,
`chapter_naming.py`, `show_note_chapters.py`, `inference_budget.py`).

*The five gaps this closes, in the order they mattered.*

1. **Nothing named anything.** Tier 3 titled a section with its literal opening
   words; tier 4 titled them `Section 1..N`. Neither says what the part is
   *about*, which is the entire point of a chapter list. `chapter_naming`
   closes it with **one batched, text-only call** that names every section at
   once -- never one call per chapter, which would be N times the cost, N times
   the latency and N chances to leave a hole in the list. A section the model
   cannot summarise gets a single hyphen and keeps the title it had, because a
   plausible invention is worse than an honest gap.
2. **Tier 3 never fetched a transcript.** It read the cache and gave up when it
   was cold, so an episode publishing a perfectly good `podcast:transcript` URL
   nobody had opened fell straight through to the slow audio scan. The best free
   answer available was routinely skipped; the budget now allows the fetch.
3. **Every knob was a hard-coded constant and none was reachable.** Replaced by
   **one control with three values** -- Quick, Thorough, Deep -- from which every
   constant derives (`InferenceBudget`). Not because the knobs do not matter, but
   because *nobody can reason about "silence threshold -35 dB"* and everybody can
   reason about how long they are willing to wait. The advanced values stay
   adjustable in a settings file and are deliberately absent from the UI: the
   failure mode of exposing them is somebody nudging `noise_db` once and quietly
   getting worse chapters forever.
4. **First answer won, with no idea whether it was any good.** Now every tier
   returns a scored `ChapterAnswer`, the cascade runs every tier the budget
   allows and **keeps the best**, and a low-confidence segmentation no longer
   suppresses a better scan. Below `MIN_USEFUL_CONFIDENCE` the honest answer
   stays "no chapters could be found". **Authored always beats inferred** --
   published, file tags, show notes short-circuit outright, because a person
   wrote those titles and no heuristic produces titles worth more.
5. **A chapter was a start and a title.** It now carries `end_ms` (so "3 of 12,
   four minutes long" is sayable and the last chapter has an honest end),
   `source` **per chapter** rather than only per set, `confidence`, and `reason`
   in words -- which is what makes the *"How were these found?"* report possible
   at all.

*The show-notes tier is the biggest unclaimed win in the whole cascade*, and it
costs nothing: a publisher who wrote timestamps has already done the work, and
the words beside each one are an **authored title**. `show_note_chapters` reads
what people actually write -- `00:00`, `1:02:03`, `12.34`, `1h05m`, bracketed,
bulleted and numbered forms, the timestamp at the **end** of the line, and
**HTML**, since show notes usually arrive as markup -- and refuses anything that
does not look like a chapter list (out of order, one mark, starting an hour in,
running past the end), because a page that merely contains times is not a
chapter list and returning it would be a confident wrong answer.

*Sampling is a cost-avoidance measure for transcription, never a quality
choice.* Where the text is already in hand -- a published transcript, or one Deep
just produced -- the section's **whole** text names it, because reading less would
save nothing and lose accuracy. Only where naming would otherwise mean
transcribing audio nobody asked to pay for does it sample, and even then the
sample is the opening **plus a probe from the middle**: a section's first minute
is very often the tail of the previous topic, an ad read or throat-clearing, and
naming a chapter after what the host was just finishing is exactly the
confident-but-wrong output rule A-10 exists to prevent.

*Nothing may interrupt.* The work runs in the background with a real cancel; a
cheap tier answering first never blocks a better one from replacing its answer;
**a published list is never overwritten**; the menu item is *disabled and
renamed* during a scan (`working_label`) so a screen reader reads the state as
part of the item rather than having to discover it; opening Chapters mid-scan
says so and returns rather than offering a spinner; and completion is announced
politely, once, in one short sentence.

*Settings, global and per show* (`PodcastSettings.chapters_*`, resolved through
`effective_settings` like everything else): when to run at all (off / when
downloaded / always), the effort, each individual tier, whether to name sections
with a model, which speech engine, and whether to announce. **A tier switched off
is disabled, not deprioritised** -- somebody who says "never scan the audio" has
said something specific and must be obeyed at any effort level -- and the whole
feature is switchable off in one place, because somebody who does not want
inferred chapters should never hear about them again.

**Inbox opt-out mode** (`PodcastSettings.inbox_mode`, `inbox.in_inbox`). The
Inbox was opt-in only -- a show is in it because it was marked. `inbox_mode`
adds `"exclude"`: every show is in the Inbox except the ones marked, which is a
materially different object over a 1,300-show library and the shape somebody
with a large subscription list actually wants.

**One flag, read two ways.** The existing `PodcastShow.route_to_inbox` is
reused rather than a second per-show field being added, because two fields can
disagree and a listener would have no way to tell which won. Every surface that
asks "is this show in the Inbox?" goes through `inbox.in_inbox`, so the listing,
the trim sweep, the republish sweep and auto-download can never diverge on what
the mark means. The per-show menu label and the spoken confirmation both change
with the mode, since "keep this one out" and "put this one in" are not the same
instruction.

**Global, not per show**, deliberately: the mode answers *which shows*, and a
per-show mode would be a question about a question. An unknown stored value
reads as `"include"` -- the direction that can only ever show *fewer* shows than
expected, never sweep a whole library in by accident. And the **Inbox caps that
shipped in 1.1.0 came first for this reason**: an opt-out Inbox is only
survivable because they exist.

## 12. Transcripts: the foundation, and the surface that followed

Recorded together so that "built" and "usable" are never confused. This section
was written when only the first half existed; the reading surface has since
shipped, and the heading said otherwise for longer than it should have.

**Transcripts keep their timings** (`quill/core/podcasts/transcripts.py`).
Cast could already fetch a feed-provided transcript, read it, cache it for
offline search, and open it as a QUILL document -- and the reader threw the
timings away, which was exactly right for "open this as a document" and useless
for anything that follows along. `TranscriptCue`, `parse_transcript_cues`,
`cues_to_text` and a binary-search `cue_at` now parse WebVTT, SubRip,
Podcasting 2.0 JSON **and** YouTube's `json3` (which arrives free with every
YouTube resolve in Quill Radio and was being discarded). `parse_transcript` is
redefined as the timed form with the timings removed, so there is one reader
rather than two that drift apart, and Cast's existing transcript tests are the
regression gate and pass untouched.

**And the reading surface now exists**: `quill/ui/transcript_reader.py`, shared
with Quill Radio rather than owned by either app, reached from **Read
Transcript...** on the episode context menu (`ui/podcasts/transcript_actions.py`,
extracted from `manager_phase4.py`, which was at its GATE-11 ceiling).

A read-only `wx.TextCtrl` on purpose: arrow keys, word and line movement,
selection, the screen reader's own review cursor and Find all come free and
behave identically to everywhere else, where a custom list would have removed
them and returned nothing. The timings sit alongside the text rather than in it
-- `line_starts` and `cue_index_for_offset` map character offsets to cues and
back, which is what lets Enter on any line seek correctly however the caret got
there (arrowed, clicked, searched, or moved by the review cursor).

Four rules it keeps: **following is opt-in and reading wins** (with Follow off,
playback never moves the caret; with it on, the caret moves and says nothing,
because a position announcement per line would be unusable); **every position is
spoken as words** through `bounded_playback_ui.spoken_duration`, never as a
timecode; **a control that cannot work says why** (jump needs a seekable player,
and follow and jump are offered only while *this* episode is the one playing);
and **saving keeps the timings** -- `cues_to_vtt` and `cues_to_srt` are asserted
to round-trip through the parser, not merely to serialise. An automatic caption
track is announced as automatic in the window's heading.

## 13. The rest of the Podcasting 2.0 namespace

`core/podcasts/feed_reader.py` read **`podcast:chapters`** and
**`podcast:transcript`** and discarded everything else in the namespace --
tags real shows already publish, sitting in bytes Cast had already downloaded
and parsed. All of it is now read (`core/podcasts/namespace_tags.py`), kept with
the episode and the show, and surfaced through **About This Episode...**
(`core/podcasts/extras.py` for the rows and the words,
`ui/podcasts/episode_extras_dialog.py` for the window,
`ui/podcasts/extras_command.py` for the three actions a row can take).

What each tag is for, and the decision that goes with it:

- **`podcast:person`** -- *who is on this?* Hosts, co-hosts and guests, with role
  and link. A host belongs to the podcast and a guest belongs to the episode, and
  the People list says which is which rather than flattening the two: that
  distinction is what somebody opened the list for. Every row is a whole sentence
  ("Bob Brown, guest (this episode)"), never a Name column and a Role column.
- **`podcast:soundbite`** -- *what is the good bit?* A publisher-marked highlight
  with a start and a length. **This is a chapter marker in all but name**, and it
  is the one that changed the chapter work (below).
- **`podcast:liveItem`** -- *is this on right now?* A live stream carried inside a
  podcast feed. It plays through the ordinary podcast transport rather than a
  second one of its own, so pause and volume are the same keys wherever the audio
  came from. Channel-level, but read from anywhere in the feed, because
  publishers write them among the episodes.
- **`podcast:podroll`** -- *what else does this show recommend?* Feed addresses
  the host vouches for, which beats any recommendation this app could compute.
  Subscribing goes through the same path Add by Feed URL uses, so the show
  arrives with its real name, artwork and episodes rather than as a bare address.
  Nothing is resolved until somebody chooses to subscribe: resolving is a network
  act and `namespace_tags.py` never performs one.
- **`podcast:funding`** -- *how do I support this?* Opened in the browser and
  processed no further. Listening stays free and QUILL is not buying anything, so
  this does not touch the cost rule.
- **`podcast:location`** -- *where is this about?* Text only. No map is offered.
- **Alternate enclosures** -- a second audio source for the same episode, which is
  what a low-bandwidth or lossless option looks like in a feed.

**Value-for-value / cryptocurrency streaming remains out of scope**, deliberately
and permanently: Cast can claim meaningful Podcasting 2.0 support without it.

### 13.1 Soundbites as an authored chapter tier

A soundbite is an authored mark -- a person chose the moment and wrote its title
-- so it belongs in the chapter cascade rather than in a side list nothing
consults. It is added as `SOURCE_SOUNDBITES` in `chapter_scoring.py` (base
confidence 0.85, inside `is_authored`) and as the last of the authored tiers in
both `chapter_sources.chapter_cascade` and the scored `chapter_cascade.run`.

Last of the authored tiers, and the reason is the whole design: **a highlight is
not a partition.** Two soundbites in an hour answers *what is the good bit*
completely and *how is this laid out* barely at all. So they win only when
nothing better was published; each chapter keeps the soundbite's own `end_ms`
rather than running on to the next mark, so the silence between two highlights
stays silence instead of being absorbed into whichever came first; and the source
is labelled **Moments this podcast marked**, so a set of highlights is never
mistaken for a chapter list covering the episode.

One exception to the shape of the other tiers: the floor is **one** mark, not
two. A single marked moment is still a place worth jumping to, and the honest
label carries the meaning.

### 13.2 Reading, persistence and refusals

Read with regular expressions over the raw item fragment, matching how
`chapters` and `transcript` are already read: the feed parser in use does not
surface unknown namespaces, a second full XML parse of every feed on every
refresh is real cost across a large library, and each of these is a shallow
attribute grab. Every parser is tolerant -- a malformed tag yields nothing rather
than raising, because one bad tag must never cost somebody their whole feed.

The channel half is read from the feed text **before the first item**, so an
episode's guests are never credited to the podcast itself. Tags are persisted
with the episode and the show, and **only when non-empty**, so a library of feeds
that publish none of this pays nothing for the feature existing. A refresh brings
in a credit added after publication; a feed that stops carrying them does **not**
erase what it already said, because an empty replacement is far more often a
partial feed than a retraction.

`About This Episode...` speaks a one-line summary before the window opens, builds
a tab only when it has something in it, and still opens (saying so) when a
podcast published none of it: *this podcast publishes no extra details* and
*QUILL Cast cannot read them* are very different facts, and a greyed-out menu
item would leave the listener unable to tell which. The action button is named
from the highlighted row and disabled with *Nothing to Open* where there is
nothing to do -- a control that silently declines is worse than one not offered.

## 14. Triage, hand-off, and scanning

Three small things, each removing a reason somebody works around the app.

**Bulk actions reached the Inbox.** The episode list has allowed a multiple
selection since 1.0 and gained bulk queue/download/played in 1.1.0, but the one
surface where selecting forty episodes is the *normal* thing to do -- the Inbox,
whose entire job is triage -- had only single-episode filing. **File N Episodes
to Inbox Folder...** asks once which folder and files the lot; being asked the
same question forty times is how a bulk action stops being one. The
remembered-default rule is unchanged and still per show, so filing thirty
episodes of one podcast sets its default once and says so once. **Add N
Episodes to Playlist...** and **Remove N Downloaded Copies** came with it;
removing downloads never removes episodes, because freeing space and
unsubscribing are different things to want. The shared
`retention.remove_downloaded_copy` is now the one implementation, so the single
and bulk paths cannot drift.

**The `.opml` association** (`core/podcasts/opml_cli.py`, an opt-in
`[Tasks]`/`[Registry]` pair in the installer). An OPML file is how one podcast
app hands its whole subscription list to another, and Cast could only receive
one through a file picker inside a dialog inside a menu. The task is
**unchecked** by default -- taking over a file type without being asked is how
an installer earns a reputation -- and uninstalling gives the extension back
rather than leaving a dead handler. Only `.opml` is claimed, though the command
line also accepts `.xml`: that extension belongs to no single application and
claiming it would break unrelated files. The import is deferred with `CallAfter`
so the window exists before a modal appears over it, or the app looks like it
failed to start.

**Hold-to-scan** (`core/podcasts/scan_hold.py`,
`ui/podcasts/scan_hold_control.py`). Skipping in fixed jumps answers "get me
past this"; it does not answer "where does this bit end?", which needs to hear
the audio going past. Shift+Right held runs at 4x -- fast enough to cover a
minute in fifteen seconds, slow enough that speech is still recognisable -- and
release restores the *exact* prior speed, so somebody who listens at 1.5 gets
1.5 back. Both edges are announced, because a player stuck at 4x with no
announcement is indistinguishable from a broken one.

**Release is inferred from the auto-repeat stopping, not from a key-up event.**
A key-up can be missed outright when focus moves, a dialog opens, or the window
is deactivated mid-hold, and every one of those would leave playback at 4x
forever. Repeats that stop arriving cannot fail that way; the key-up is still
honoured when it comes, so the drop back is immediate rather than up to the
grace window late. Losing the window and closing the app both end a scan too.

## 15. The library is yours to arrange

**Per-episode download from the tree**
(`quill/apps/podcasts_library_actions.py`, the extracted
`CastLibraryActionsMixin`). An expanded show's episode rows carry Play
Episode and Download Episode on their context menu; the download goes
through the one shared `enqueue_episode_download` helper, so the
private-feed Authorization rule (same-host only) can never be forgotten at a
new call site. Files are named for humans -- `<download root>/<show
slug>/<episode slug><ext>` -- because a download whose name is a feed GUID
is unfindable in Explorer.

**Renamable pinned views** (`PodcastSettings.view_names`;
`virtual_views.view_label`/`set_view_name`/`reset_view_name`). The shipped
views (Favorites, New Episodes, Continue Listening, Inbox) are the one kind
of tree node the listener may rename -- F2 or the context menu -- because
they belong to the app, not to a feed. Setting the shipped label or a blank
IS the reset, so the settings file only ever stores genuine customizations;
Reset Name appears on the menu only while a custom name exists. Shows and
episodes refuse renaming with an explanation: an alias would silently stop
matching what every other player, share link and search result calls them.
The Manager reads the same names, so the two windows cannot drift.

**Show ordering, including by hand**
(`PodcastSettings.show_sort_mode`; `PodcastLibrary.move_show`;
`sorting.SHOW_SORT_MODES`). Ascending, descending, and **custom** -- custom
order is the `shows` list's own order, maintained by one-step swaps among a
show's *folder siblings* only, so each folder keeps its own arrangement even
though all shows live in one flat list. Taking manual control (Alt+Up/Down)
is itself the act of choosing custom, and entering custom freezes the order
currently on screen first -- otherwise the first nudge would scramble
everything visibly. The Subscriptions menu's radio group and the Manager's
dropdown both reflect the live mode.

**Counts that say what they count.** A folder's badge is its subtree's
podcast count; a show's badge reads "(n unheard)" in words. Two bare
numbers that read identically would make the listener remember which node
kind they were on -- the exact cost badges exist to remove.

**Emptied search fields empty their results**
(`quill/ui/search_reset.py`). One shared binding backs every search surface
with a separate results list, in Cast and across the family: when the query
becomes empty (whitespace counts), the surface resets exactly as its own
blank-search path would. A results list showing matches for text that no
longer exists is stale state presented as current -- invisible as such to a
screen reader arrowing the list.

**Show notes are paragraphs** (`show_notes.html_to_plain_text`). Block
elements now contribute a blank line, collapsed so empty tags can never
stack more than one -- a screen reader's next-paragraph navigation needs a
real boundary to land on, and a wall of single-spaced lines has none.

## 16. Reaching outside this machine (2.0)

Sections 12 to 15 all made QUILL Cast better at what it already did. This one
is different in kind: four of its five parts are Cast talking to something that
is not Cast. That is a class of feature the app had none of, and each part
carries a rule about *how far* the reach goes.

### 16.1 Listening Places: a format, not a service

QUILL Sync already carries listening positions between two copies of QUILL,
encrypted, over a folder the listener already syncs. It always will, and it will
only ever work QUILL-to-QUILL.

**Listening Places** (`core/sync/listening_places.py`, format id
`listening-places/1`, specified in `docs/engineering/listening-places-spec.md`)
is the interchange half: a small plain-JSON format any podcast app can read and
write, in the same folder, with no account, no server and no signup. It is a
second, independent switch from the encrypted half and requires **no recovery
phrase** -- gating it behind one would mean a feature nobody can set up, which
syncs nothing.

Four properties are requirements, not implementation details, and each one rules
out a specific failure:

- **P-1. One writer per file.** Every device writes exactly one file and reads
  every other. Cloud drives resolve simultaneous edits to one file by leaving a
  conflicted copy behind, which is the worst failure available here; if no two
  devices ever write the same file, it cannot occur. It also scales past two
  devices for free.
- **P-2. Last write wins, never furthest position.** Jumping back twenty minutes
  deliberately and then opening the episode elsewhere must not be undone. Every
  record carries an RFC 3339 UTC timestamp, spelled so that string comparison
  sorts it.
- **P-3. Reads happen at launch and on an explicit Sync Now, and nowhere else.**
  Not on a timer, not on foreground, not on a file-change notification. A
  position arriving mid-session has no acceptable behaviour: moving the playhead
  under somebody is unacceptable and worse without a visual cue, queuing it is
  confusing, and asking mid-episode is an interruption. At launch nothing is
  playing.
- **P-4. Identity is derived, never a path.** An episode is keyed on
  `sha256(guid)[0:16]` -- the GUID alone, because two apps disagree about a
  feed's URL far more often than about its GUIDs. A local file is keyed on its
  size and the digest of its two ends, which is the one key that agrees across
  Windows and iOS for the same file in the same cloud folder.

The episode adapter (`core/podcasts/position_sync.py`) closes a gap Cast owed
itself regardless: `position_ms` lived inside the monolithic library file with
no timestamp, so there was nothing to merge on. `PodcastEpisode` now carries
`position_updated_at`, and **every** site that moves a position goes through
`position_sync` -- one site that forgot the stamp would be a device whose place
silently stopped travelling.

Conformance fixtures live beside the spec and are executed by
`tests/unit/core/sync/test_conformance.py`, so a change that breaks the other
implementation fails a test rather than a user.

### 16.2 Sharing a moment

`quill-cast://episode?feed=...&guid=...&t=<seconds>`, registered by every Cast
installer. Two rules:

- **The sentence ships with the link, always.** "Blind Abilities, Episode 214,
  at 41 minutes 12 seconds" goes on the clipboard with it, because the recipient
  usually does not have Cast, and a link nobody can open is worth less than a
  sentence anybody can paste.
- **A link is untrusted input and resolves only inside the library.**
  `share_links.parse_link` refuses anything that is not the scheme, refuses a
  `feed` that is not an http(s) address, and yields a feed address and a GUID
  and nothing else. The caller must find both in the library the listener
  already subscribes to. **Cast never fetches a URL, and never adds a
  subscription, because a link asked it to.**

### 16.3 A second directory

Podcast Index (`core/podcasts/podcast_index.py`) joins iTunes as an opt-in
source, for its Podcasting 2.0 metadata. This reverses the 2026-08-13 decision
not to integrate it; the reversal is recorded in the egress audit beside the
call site so a stale rationale cannot keep asserting itself.

- **The credential became the application's (2026-08-23).** This section
  shipped saying iTunes stays the default because "Podcast Index requires" a key
  the listener has to register for -- and that was the right call while the key
  was theirs to get. It is now the app's: `tools/generate_podcast_index_key.py`
  bakes a key and secret into the gitignored `quill/_podcast_index_key.py` at
  build time (never committed), and
  `podcast_index.credentials()` prefers a listener's own pair from the platform
  credential store, so pasting a key is a rotation lever rather than an entry
  fee. `directory_source` therefore defaults to `both` for a new library, while
  a stored choice is never overridden. What ships is an application identifier
  for public data: it authorises nothing on anyone's behalf, reads no account,
  and sends no listener data -- a search carries the term alone. The catalogue
  half (`podcast_index_catalog.py`: a show's fact sheet, its episodes without
  subscribing, trending, the taxonomy) is shared with Quill Radio's Podcast
  Index browse branch.
- **Credentials go to the platform credential store**, never `podcasts.json`,
  and must survive `stability/redaction.py` scrubbing.
- **One directory failing is not the search failing.**
  `core/podcasts/directory_search.py` returns what did arrive plus a sentence
  about what did not.

### 16.4 Folders as a listening lens, and the queue that follows

A folder is a place to listen from (`core/podcasts/folder_actions.py`). The
subtree walk is one function everything else reuses, so no two folder actions
can disagree about what a folder contains, and `move_folder` refuses to make a
folder its own descendant -- a ring is a tree nothing can render and nobody can
undo.

**Play All Unplayed means one episode per show.** A folder of forty shows holds
hundreds of unplayed episodes; a queue of hundreds is not a queue.

**Folder settings apply at save time, not read time.** Choosing a value writes
it into every member show's own override and the folder forgets it. One
inheritance chain: what a show's setting *is* remains what
`PodcastLibrary.effective_settings` says. The cost -- a show moved in later
inherits nothing -- is stated in the window. The alternative, resolving folder
values at read time, means every consumer walks the tree and two shows in one
folder can disagree about their own setting depending which code path asked.

`queue.group_queue_by` groups the Play Queue by nothing, podcast or folder.
Grouping is presentation only: the play order is untouched, headers announce
themselves as headers, and no action can act on one.

### 16.5 Rules that can express a disjunction

`PlaylistRules` ANDed everything, which cannot express "anything from these
three shows **or** anything I have bookmarked". It gains `match_mode`,
`folder_ids` (subtree aware), `download_state`, `has_note`, `text_contains`,
`progress` and `item_limit`.

Two rules govern the implementation. A rule left at its "does not narrow" value
contributes **no predicate at all** -- otherwise every `any` playlist would
match everything. And `item_limit` applies **after** sorting, so "the ten
newest" is the ten newest.

Scope (`show_ids`, `folder_ids`) is always AND, whatever `match_mode` says: "any
of these rules, but only in this folder" is what naming a folder means.

The live **"Matches N episodes right now"** count is a requirement rather than a
nicety. A filter set with no feedback is a guess somebody must save, close,
reopen and read to check -- and there is no list quietly filtering itself in the
background to glance at.

### 16.6 Chapters: authored titles without a model

`core/podcasts/note_anchors.py` matches the running order publishers write in
prose against where each topic's distinctive words **arrive** in the transcript,
aligned monotonically because notes are written in programme order. It is the
only route to authored titles that involves no model at all. Two measured
findings are recorded in the module and hold: anchor on **onset**, not density
(a long interview mentions its guest most often in the middle); and where the
notes describe two or more segments, use them and stop, because padding them
out with lexical boundaries measurably made the list worse.

**Thorough no longer offers the pause scan.** It scored 0.06 against a 0.15
do-nothing floor -- worse than dividing the episode by *n*. It remains available
under Deep, where the listener has accepted a weak answer over none, and for a
recording (`inference_budget.for_recording`), where there is nothing else.

**Deep transcribes locally, and the engine ships in the box** (~40 MB, CPU-only,
in `DEFAULT_BUNDLED_DEPENDENCY_GROUPS` with its model staged by
`_stage_vosk_model`). `speech.service.preferred_chapter_provider_id` is
deliberately **not** the dictation ladder: dictation wants an engine that never
invents text from silence; chapters want cue boundaries that fall on pauses.
The engine that wins the second is a 40 MB model that beat one thirty-five times
its size on measurement (0.372 against 0.316) at 4.7 times the speed.

Bundling is what makes the feature real: chapters have to answer the first time
somebody asks, and an engine that must be downloaded first means the first
answer is always "no chapters could be found".

## 17. The columns are the sentence (2.0)

The counterpart of Quill Radio's section 13, on the same shared machinery
(`core/media/list_columns.py`) and for the same reason: an episode list is read
out one column at a time, so the column set is not a display preference but a
speech setting. **Subscriptions > Choose Columns...** (Ctrl+Alt+Shift+C) covers
the episode list, Downloads, and Add Podcast's search results.

The four properties are Radio's, unchanged -- hidden means absent rather than
last, a hidden column keeps its place, one column per surface is pinned, and a
saved layout is repaired against this build on every read. The window is the same
two lists with the same live preview of the sentence a row will speak.

**What Cast offers beyond its defaults**, and why each is off to start with:

- **Podcast** on an episode row. Worth having in a list that spans several
  shows -- the Inbox, Continue Listening, a playlist -- and pure noise in a list
  of one show's episodes, which is the common case and therefore the default.
- **Time Left**, said only where something was started and something remains.
  "58 min left" on an untouched episode is the duration read twice, and a
  negative answer on an overrun position is nonsense, so both are blank.
- **Downloaded**, for somebody who decides what to play by what is already on the
  machine.
- **Feed Address** on a search result, which is what tells two shows with the
  same name apart.

**Applied while the window is open.** Cast holds a live reference to its Manager
so it can be refreshed in place, so a layout saved while the Manager is up takes
effect there rather than next time. Radio's two lists are modal windows opened
from the menu bar the item lives on, so its cache is simply dropped -- the next
window built is the very next thing somebody does.

`tests/unit/core/podcasts/test_podcast_list_columns.py` fails the build if the
catalogue offers a column no fill site produces.

## 18. What both listening apps owe a listener (2026-08-24)

Eleven requirements that arrived together because most of them are **one
answer shared between Quill Radio and QUILL Cast** rather than two answers
that happen to agree today. Where a section below says "shared", the store,
the module and the wording are literally one thing, and a change to either
app changes both.

### 18.1 Nothing is a dead end

**Requirement.** A command that cannot run says *why*, at the moment somebody
asks for it.

This family dims a great deal on purpose: Mark All as Played with nothing
unheard is a **state of a verb the row owns**, which is exactly why it dims
rather than vanishing -- a verb that comes and goes teaches nobody anything.
But a screen reader says "dimmed" and stops, and the item itself said nothing
about what would un-dim it. That is a dead end you cannot see around.

Every dimmed action now carries a `reason`: one lower-case clause naming the
condition, with a count wherever a count makes it concrete.

- **Where it lives.** `quill/core/dimmed_reason.py` -- shared vocabulary, so
  the two apps say the same thing. `RowAction` (Radio) and `ResolvedAction`
  (Cast) carry the reason beside the label, in the same wx-free table.
- **Where it is spent.** The context menu's help string; the Quick Action
  direct keys (Ctrl+1..Ctrl+9), which used to answer "that Quick Action is not
  available"; and the command palette, through the registry's availability
  probe (`quill/ui/app_availability.py`) that every shell app now installs.
- **Wording.** Lower case, no trailing stop (`explain()` supplies both), state
  the condition rather than the fix, and prefer a count to an adjective:
  "nothing to download, all 40 are already here" answers a question "nothing
  to download" leaves open.
- **Enforced.** `tests/unit/ui/test_dimmed_action_reasons.py`: an action built
  with a conditional `enabled=` and no `reason` fails the build.

### 18.2 One step of undo, in preference to a prompt on every verb

**Requirement.** The last destructive action can be taken back, once, and the
offer is spoken.

A confirmation prompt is the cheap answer and a poor one: it costs a keystroke
and a sentence *every single time*, including the nine hundred times the
listener meant it, and it still cannot help the one time the wrong row was
focused. One step of undo is cheaper than a prompt on every verb and kinder
than either.

- **Scope.** Unsubscribe, Remove All Episodes, Remove All Downloads, Mark All
  as Played, Delete Recording -- in both apps.
- **One slot, not a stack** (`quill/core/undo_last.py`). Remembering displaces;
  taking empties. A listener who has to remember how many times to press
  Ctrl+Z has been given a puzzle, not an undo.
- **Deleted files are moved aside, not unlinked.** `hold_files` puts them in a
  holding folder that only ever contains the one undoable step; the slot's
  disposer empties it when the step is displaced. Ctrl+Z restores the bytes,
  not the intention to fetch them again. No new dependency and no recycle-bin
  round trip.
- **Retention deletions are caught too.** `capturing_deletes()` installs a hook
  on `core/podcasts/retention.py` for the duration of one verb, so
  delete-after-play, keep-last-N and the storage cap are held with the rest.
- **It says what it cannot bring back.** A private feed's stored password is
  deleted by design when you unsubscribe; the offer says so in the same breath.
- **QUILL itself never activates.** Its Ctrl+Z is the editor's, and
  `hold_or_delete` deletes outright without a slot -- so no bytes are ever held
  aside for a slot nobody can reach.
- **The offer is spoken.** Every undoable verb ends its announcement with
  "Ctrl+Z undoes this": an undo you do not know about is not an undo.

### 18.3 A verb that touches many rows says how many

**Requirement.** Every action on more than one row ends by announcing exact
eligible / done / skipped counts, with the skipped *reason* beside the number.

"Removed downloads" tells a listener who cannot see the list neither how many
files went nor whether the ones it could not touch were mentioned.

- `quill/core/counted.py` is the shared vocabulary; nothing eligible is a
  sentence of its own that says *why*, and failures are never folded into
  skipped (a file that could not be deleted and a file deliberately kept are
  different news).
- **GATE-BULK-COUNT** (`quill/tools/bulk_count_audit.py`) covers every
  bulk-named function in both apps, each classified `counted` /
  `counts-elsewhere` / `no-announce`; a new one that announces no count fails
  the build. Silent truncation is a failure too: a verb that caps its work
  says what it deferred.

### 18.4 A failure that was spoken once still exists

**Requirement.** Feeds, downloads, recordings and streams that fail are
written down, with reason, time and a way to try again.

Announcements are transient by design, which is right until the sentence you
needed went past while you were in another window. That was the one place this
family was **not** screen-reader-first: a sighted listener still had a list to
scroll back through and a listener who missed the speech had nothing at all.

- `quill/core/problem_log.py`: bounded (200), newest-first, local, and shared
  by both apps. Consecutive identical failures collapse onto one row's
  timestamp, so a feed checked every fifteen minutes cannot fill the window by
  itself -- but a *different* reason is a different fact and gets its own row.
- **Retry is registered by kind, not stored as a closure**, because the log
  outlives the session that wrote it: a row from last Tuesday must be
  retryable by today's handler. A kind nothing claims simply has no Retry, and
  the button says so rather than pretending.
- **Never carries a credential.** Copy All is meant for a bug report.

### 18.5 Quiet hours, and the line they must not cross

**Requirement.** One window, shared by both apps, in which the apps stop
speaking *on their own*.

**Unprompted is the whole distinction, and it is a hard rule.** Quiet hours
must never silence the answer to a keypress: a listener who presses Play at
three in the morning is entitled to hear what is playing, because they asked.
What is held back is speech nobody asked for -- check ticks, new-episode
notices, download notices, reminders. This is why the implementation is a
small vocabulary of *kinds* each call site opts into
(`quill/core/quiet_hours.py`) rather than a gate around `_announce`: a gate
would silence replies as well, and no amount of care at the call sites would
make that safe.

- `Kind.URGENT` is never held back. A recording that failed at 3 a.m. is
  exactly the thing somebody set an alarm-clock radio for, and an app that
  swallowed it to be polite would have chosen the wrong side.
- Windows wrap past midnight (22:00-07:00 is the ordinary case), and a
  zero-length window means *nothing* rather than everything.
- One explicit override: reminders may be let through, since an alarm clock is
  a reason to set one.
- The readout says what the setting does **not** do -- feeds are still checked,
  downloads still run -- because "quiet hours" invites exactly those two
  misreadings.
- This is most of the machinery the Reminders feature needs for Do Not Disturb.

### 18.6 The setup is portable, and says what it is not carrying

**Requirement.** One file carries everything this machine has been taught, out
and back in.

OPML moves subscriptions and nothing else -- which is to say it moves the part
that was easy to standardise and leaves the part somebody actually built.

- A `.quillsetup` is an ordinary ZIP with a readable manifest, over a
  **declared inventory** (`quill/core/setup_transfer.py`) of 17 stores. Not a
  sweep of the data folder: a sweep would eventually carry a cache, a lock
  file, or a credential nobody meant to move.
- **No secrets, ever**, and the report says so rather than leaving somebody to
  discover it. A test enforces that no secret store is in the inventory, and
  import refuses to write any file the inventory does not name -- a setup file
  is not a way to drop an arbitrary file into somebody's data folder.
- **Import replaces, and says so first.** Merging two libraries is a different
  feature with different questions; pretending otherwise would be the
  expensive kind of kindness.

### 18.7 A place is a place, whichever app you were in

**Requirement.** An episode started in one app picks up in the other, on this
machine, at the position the listener last decided on.

Listening Places already defined *what a place is* between devices. What was
missing was one shared local store and the write on pause -- Radio never wrote
a position when you paused at all, so its handoff to Cast reported wherever
you had last pressed Stop.

- **Last write wins, not furthest wins** -- the rule `position_sync` already
  states for cross-device sync, for the same reason. Somebody who skipped to
  the outro to check something and went back to the middle has *decided* the
  middle is where they are; an app that dragged them forward again would be
  overruling them with arithmetic.
- **A finish is sticky.** "Finished" and "at 0:00" are the same stored state,
  so reading a newer zero as "start again" would undo a completion every time.
- **The jump is explained.** A cross-app resume says which app the place came
  from; a jump nobody explained is indistinguishable from a bug. Resuming
  where you left off in the app you left off in stays silent, because that is
  the ordinary behaviour and does not need narrating.

### 18.8 Adding something you already have

**Requirement.** Say so, name it, and move to the row that already exists.

The reason anybody adds a thing twice is that they could not find the first
one, so a refusal that leaves the cursor where it was answers the wrong
question. The root cause on the Radio side was a store that answered `None`
whether or not it had added anything, so every caller announced success over
nothing happening.

### 18.9 Find an episode inside one show

**Requirement.** Search the episodes of the show you are on, over **titles and
descriptions**, composing with the state filter and the sort, announcing the
match count on submit.

Between "filter by state" and a cross-library search there was nothing, so
*which episode of this show was the one about the harbour* had no answer but
arrowing two hundred rows. Descriptions are in scope because a show that
numbers its episodes and puts the subject in the notes -- most interview
podcasts -- is precisely where a title-only search finds nothing.

- **It narrows, it does not replace.** The query is applied inside the filter
  step, after the state filter and before the sort, so all three compose.
- **Typing is silent; Enter counts.** A per-keystroke announcement talks over
  the typing. No matches says what was searched and that a filter above may be
  the reason, rather than announcing a bare zero.

### 18.10 Timeline verbs mean the same thing in both players

**Requirement.** One parser and one dialog for "go to this position", and one
key for Skip Silence.

- `1:02:03`, `62:03` and `3723` are the same moment in both apps. They were
  not: two parsers disagreed, and Cast's jump existed only on a Winamp letter
  key -- which means it existed for whoever had those keys on and knew about
  them, and for nobody else.
- Skip Silence is a transport verb in both, on the same key, because the
  shared transport table's contract is that a verb means the same thing in
  each player. Cast had it as a per-show setting with no way to reach it while
  listening, which is the only moment anybody forms an opinion about it.

### 18.11 Every surface says what it is for

**Requirement.** F1 in QUILL Cast opens with an authored paragraph about the
window, exactly as Quill Radio's has since 3.0 -- and a new window cannot ship
without one.

The family-wide F1 engine had worked everywhere since 2026-08-23 and only
Radio had authored purposes, so every Cast window answered with the generic
sentence: true, and useless.

**GATE-CAST-HELP** (`quill/tools/cast_help_audit.py`) mirrors GATE-RADIO-HELP
over the podcast UI. The scanner and snapshot rules both gates share now live
in `quill/tools/help_audit.py`, so the two cannot drift.

## 19. The first launch (2026-08-24)

**Requirement.** A genuinely first launch shows three screens -- welcome, add
your first podcast, you're set -- and nothing else ever does.

The screens themselves shipped in 1.1. **Nothing called them**, for two
releases, which is the failure Quill Radio's equivalent carries a docstring
about; a feature can be written, reviewed and fully unit-tested and still be
entirely absent, because nothing in a test suite asks "and can anybody reach
this?".

Four rules the flow follows:

- **Skip is a first-class button**, and skipping counts as done. Somebody who
  skipped chose to; asking again next launch would override that with a guess.
- **Not for somebody who already has podcasts**, however they got there -- an
  imported OPML, a restored `.quillsetup`, an upgrade. Explaining how to add a
  first podcast to somebody with two hundred says nobody checked.
- **It refuses over a window that is not on screen.** A deferred modal with
  nothing behind it is a hang rather than a welcome, and a welcome nobody can
  see is not a welcome. Safe because the launch path shows the main window
  before entering the loop the deferred call runs in.
- **It never raises.** A welcome that can take the app down on its very first
  launch would be the worst possible first impression.

The state persists in `PodcastHistory.onboarding`, a nested record of ids
rather than a version number -- a tip added next year should fire for somebody
who has used Cast for a year, and a version stamp would say they had seen it.

**The wiring is what the tests assert.**
`tests/unit/ui/test_podcast_first_run.py` checks that the app actually calls
the flow and that the launch shows its window first, alongside the behaviour:
a test that only exercised the dialog would have passed throughout the two
releases in which nobody could reach it.

## 20. Six answers Quill Radio already had (2026-08-24)

The two apps share an audience and a window model, and a feature built for one
of them is usually right for the other. These six were Radio's, and Cast had
none of them. Where the *machinery* was genuinely the same it was extracted
and is now shared; where the *words* were the product, each app keeps its own.
That distinction is the requirement, not an implementation note: a shared
dialog with the nouns swapped by parameter reads as neither app's, and a
second copy of a mechanism is how two apps come to disagree about it.

### 20.1 A sheet, not just an editor

**Requirement.** A listener must be able to find out which keys exist, not
only change a key they can already name.

Help > Keyboard Shortcuts Sheet (Ctrl+Alt+Shift+K), filterable, generated by
walking the live `wx.MenuBar`. Walking the menus rather than the keymap is the
design: the sheet lists the keys this listener has, rebindings included, and
cannot fall out of step with the menus because it *is* the menus. Radio's
implementation, called rather than copied -- it asks its host for a frame, an
announcer and a modal helper, all of which Cast has.

### 20.2 One key for every place

**Requirement.** Reaching a place must not require remembering which of a
dozen chords opens it, and the numbering must never move.

Go To (Ctrl+G), ten places, 1-9 then 0. The machinery is
`quill/core/go_to_menu`, shared; each app supplies its own catalogue
(`core/radio/go_to`, `core/podcasts/go_to`) and its own file. The pool -- every
known destination not in the menu, derived rather than stored -- is what makes
the numbering permanent: a destination added by a later release can only land
in the pool, so an upgrade cannot renumber what somebody has learned.

Cast's previous "Go To" jumped to a time inside an episode. Two features with
the same two words is worse than one missing feature, because the wrong one
answers.

### 20.3 A word when a media tool is missing

**Requirement.** A capability the installation cannot deliver must be named
once, in the listener's words, and never mentioned again while it stays that
way.

`core/podcasts/media_health` (pure) and `ui/podcasts/media_preflight` (the
probe). Cast-specific rather than shared with Radio's, because the sentences
are the product and none of Radio's survive the move -- Cast does not record
stations, and a listener told they had lost that would go looking for a
feature that was never there.

The reason this matters more in Cast than in Radio: a missing playback engine
announces itself, but every FFmpeg-dependent feature here fails by producing a
**plausible** result. The download completes and is not trimmed; the chapter
analysis finishes and finds nothing, which is exactly what an episode with no
chapters looks like. Remembered by signature rather than a flag, so a machine
repaired and later broken again is told again.

### 20.4 Closing means what you chose

**Requirement.** The titlebar X, Alt+F4 and Exit follow one persisted answer:
ask, exit, or minimize to tray.

`PodcastHistory.close_action`, shipped as `exit` -- what Cast has always done,
because an upgrade that starts asking a question has changed somebody's Alt+F4
under them. Ask only asks when something is at stake, and names it. The
confirm never runs from inside `EVT_CLOSE` (`AppShellFrame.handle_app_close`
vetoes and re-runs it deferred), because `ShowModal` from a close handler on
wxMSW can return without displaying and silently veto the close.

### 20.5 A search box with a memory

**Requirement.** A search worth running twice must not be worth typing twice.

`core/podcasts/search_history`, on `PodcastHistory.recent_searches`, surfaced
as the Search Everywhere box's dropdown. One string rather than Radio's
three-field triple, because Cast searches one box across shows, episodes,
notes and transcripts at once. It rides the history file the recently-played
list already uses, so clearing that clears this -- a second record of what
somebody has been searching for, kept somewhere they did not know about, is
the wrong answer for a list like this.

### 20.6 A backup you can restore

**Requirement.** A listener must be able to carry their library to another
machine, and to get it back after losing one.

`core/podcasts/backup`, a `.qcbackup` zip with a manifest, restored in place
with the running app reloaded afterwards. File-level -- the JSON is copied
verbatim rather than re-serialised -- so a backup made by one version restores
into another and a field this build has never heard of survives. Downloaded
episodes are optional and off by default: they are tens of gigabytes and can
be fetched again, where the 40 KB beside them cannot.

Export My Data is not this. It is a readable snapshot, deliberately, and it is
kept.

### 20.7 A setting you can reach in one keystroke

**Requirement.** A per-show setting somebody changes often must be reachable
without navigating a window of two dozen controls.

`core/podcasts/single_settings` (three descriptions, tested without a window)
and `ui/podcasts/single_setting_dialog` (one control, focus on it). Episodes to
Keep, Queue Expiry and Playback Speed, each also a Quick Action so the order
is the listener's. Every write goes through
`PodcastLibrary.apply_show_override`, which writes **only the field named** as
that podcast's own opinion -- setting a speed here cannot silently reset a
retention rule set there, and cannot freeze one either. It cloned the whole
effective record until section 22; that clone is the bug section 22 removes.

## 21. Rules for the episodes you did not want (2026-08-28)

**Requirement.** A podcast that publishes more than one thing must be
followable without the parts you do not want arriving, being triaged by hand,
and consuming an Inbox cap set for a different reason.

`core/podcasts/models_filters` (the record and its scopes), `episode_filters`
(matching, preview, the save gate), `episode_filter_speech` (the reviewed word
orders), `episode_filter_maintenance` (the library-facing half), and
`ui/podcasts/episode_filters_dialog` + `episode_filter_rule_dialog`.

### 21.1 A rule set, and eight places to mean it

Per podcast: named rules, each independently switchable, each with an optional
title criterion (wildcard or regular expression, case-insensitive by default)
and an optional minimum duration. Within a rule the criteria are **and**-ed;
across a configuration the rules are **or**-ed. Two modes -- filter-matching
and keep-matching.

The scopes are the half that matters: the Inbox, Auto-Queue, auto-download, the
new-episode announcement, the podcast's own episode list, the cross-show views,
smart playlists, Search Everywhere. Ticked independently, so one feature answers
"do not put it in front of me", "do not spend my bandwidth on it" and "I never
want to see it again" without any of them implying the others. A new filter
ships with the four **routing** scopes on and the four **hiding** scopes off:
declining to route is invisible and reversible, hiding changes what can be
found.

### 21.2 Asked, not stamped

The verdict is computed at every point of use rather than written onto an
episode at ingest. That is why unticking a scope takes effect on the next
redraw with nothing to migrate and nothing to undo. Two things are still
written down because they are events rather than opinions: a Play Queue slot
removed by the explicit apply-to-existing pass, and the Needs review warning.

`hide_predicate` returns `None` for a podcast with no active filter in that
scope, so the hot loops -- the Inbox over a 1,300-podcast library, a smart
playlist over every episode of every show -- skip the question with one branch.

### 21.3 Fail open, four times over

An unusable rule never matches. A configuration with no usable enabled rule is
not active. A configuration with no scope is not active. An unknown stored
version, a malformed record or an unknown scope name reads as *no filter*.
**The cost of failing open is an episode you did not want; the cost of failing
closed is a podcast that silently stops arriving and no message anywhere saying
why.**

### 21.4 The save is gated, and nothing hidden is unreachable

Refused: on with no enabled rule; a regular expression that will not compile
(the compiler's own message is quoted); every enabled rule empty; on with no
scope; a minimum-duration rule where none of the newest 50 episodes publishes a
duration. Asked, with exact counts: partial duration coverage, and any hiding
scope -- with the two ways back named in the question.

Preview evaluates the draft **while the top-level switch is off and while no
scope is ticked**, because it answers "what do these rules catch?", which is a
question about the rules. The episode list's state filter gains **Filtered
out**, present for every podcast rather than only for filtered ones; and a
per-episode **exemption** beats every rule in every scope and survives editing
the rules.

### 21.5 More tests, any-one-of, and a rule from an episode (2026-10-01)

**Requirement.** A rule must be able to ask what real feeds actually vary on --
the show notes, the people credited, the publisher's episode type, a maximum
length, age, season and number -- by words, wildcard or regular expression;
and a listener who knows only *which episode* they do not want must be able to
get a rule without writing one.

- `core/podcasts/filter_conditions.py`: `FilterCondition(field, op, value,
  case_sensitive)` -- fields title, notes, people, type, duration, age, season,
  number; text ops contains / not_contains / starts_with / ends_with / is /
  is_not / wildcard (whole text) / regex / not_regex (`re.search`, so `^` and
  `$` anchor); number ops at_least / at_most / is / is_not; type ops is /
  is_not over full, trailer, bonus. `error` names why a condition is unusable;
  `condition_matches` is total. **A missing fact never matches a number test**
  (no duration, unparseable date, season or number 0); an empty type is
  `full`, the iTunes default; a people test asks about any one person.
- `EpisodeFilterRule` gains `conditions` and `match_any`. The title and
  minimum-length criteria are tests like any other: all must hold, or any one
  when `match_any`. `pattern_error` and `is_usable` include the conditions, so
  an unusable condition makes its rule match nothing (21.3 holds unchanged),
  and the save gate's duration check counts a duration condition.
- **Storage stays readable backwards.** `FILTER_CONFIG_VERSION` is 2 and
  `READABLE_VERSIONS` is (1, 2), but a configuration is *written* as version 1
  unless a rule uses `conditions` or `match_any`, whose keys are omitted when
  empty -- so every filter made the old way stays byte-for-byte what older
  builds read. A version-2 filter on an older build reads as no filter (21.3).
  An unknown field or op is kept and read as unusable, never dropped, because
  dropping a test widens the rule.
- `ui/podcasts/episode_filter_test_dialog.py` ("Episode Filter Test"): Look
  at, Test (refilled from the field; the type's rows are whole phrases, so the
  value box is disabled), Value, capitals. Refuses an unusable test with the
  reason and focus on Value. The rule editor gains Match when, More tests with
  Add / Edit / Remove Test, and **Try It on Recent Episodes**, which runs the
  draft through `rule_matches` over `newest_episodes` and both shows and
  announces `filter_suggestions.describe_trial` (count, five titles, "and N
  more"; an unusable draft says why).
- `core/podcasts/filter_suggestions.py`: `suggest_rule(episode, episodes,
  newest=)` -> `FilterSuggestion(rule, reason, matches, sample)`. Order: the
  publisher's trailer/bonus type; a series name (text before or after `: `,
  ` | `, ` - `, en and em dashes, ` #`, or the opening two to four words) that
  at least one sibling shares, the highest count winning; a length ceiling
  when the episode is under 40% of the sample's median; else the exact title.
  A candidate matching every sampled episode is never offered.
- **Filter Episodes Like This...** (`filter_like_this`, an episode Quick
  Action, access key F) opens `EpisodeFiltersDialog(suggestion=...)`, which
  opens the rule editor on the draft with the reason as its first line; a kept
  rule is appended and the draft's switch turned on, announced as "Rule added
  and filtering switched on. Preview to check it, then Save to keep it."
  Nothing is stored before Save; the gate and Preview are unchanged.

Tests: `tests/unit/core/podcasts/test_episode_filter_conditions.py`,
`tests/unit/ui/test_cast_episode_filter_tests_ui.py`.

---

## 22. A podcast can answer for itself (2026-08-29)

**Requirement.** Almost every complaint a podcast listener has is about one
podcast behaving differently from the rest. A setting must be settable at the
level it is actually meant at, and a shared default must keep reaching the
podcasts that have no opinion about it.

### 22.1 Four levels, one resolver

`shared default -> folder (outermost first) -> podcast`, nearest wins, each
level storing **only the settings it has an opinion about**
(`PodcastLibrary.scope_overrides`; `core/podcasts/settings_resolver`).

Cast had three of these and they did not compose. A folder was not a level --
Folder Settings wrote its values into each member podcast and forgot them, so a
podcast filed there later inherited nothing. Worse, a per-show override was a
**complete copy of the settings record**, which meant Cast could not tell *"I
have no opinion"* from *"I want exactly this"*; once those are the same thing,
changing a shared default silently stops reaching the podcasts most likely to
need it.

`PodcastLibrary.effective_settings` keeps its signature -- every existing
caller gained the folder level unchanged -- and its fast path returns the
shared record by identity, because it is called per podcast per refresh and on
some paths per episode. `apply_show_override` now writes exactly the fields
named. Legacy whole-record overrides migrate at load by diffing against the
shared default and keeping only what differs: a best-effort recovery, and
deliberately the safer of the two readings.

### 22.2 A setting is described, not merely stored

`SettingDef` (`core/podcasts/settings_types`) carries the label, the house-rule
help, the kind, the levels it may be set at, its choices, its search aliases,
and the words its value reads back as. Definitions live beside the families
they describe; `settings_catalog` assembles them.

Three things follow that were previously impossible: **search** that matches
label, help, choice labels and synonyms somebody would really type ("wifi"
finds the metered guard), ranked so a label match outranks a help match; a
**"what have I changed?"** report, which is the question support always asks
and the only honest basis for a reset; and **generated controls**, so a setting
added to the catalogue appears in the per-podcast window with no UI code.

### 22.3 Provenance is a first-class answer

`describe_provenance` produces *"Every 60 minutes, from the folder News."* An
editor that shows `60` has told somebody the number; one that names the level
has told them why, and where to change it for everything else in that folder
too. It is in every control's F1 help.

### 22.4 The twenty-five

Arrival: per-podcast check cadence; backfill on subscribe, distinct from the
forward-looking download count; off-peak download windows; Auto-Queue from the
oldest unplayed episode; transcript policy; permanent-redirect following;
re-publish handling.

Playback: chapter policy surfaced per podcast; chapter-title skip patterns,
exact where a seconds-based skip is a guess; silence-trim strength; a
sleep-timer default; the session behaviour that was already overridable and
unreachable.

Storage: a per-podcast disk budget; a **never-evict pin**, which exists because
the only previous way to protect one archived podcast was to switch the sweeps
off for everything; a preferred audio variant using the `alternateEnclosure`
tags Cast already parsed and never used; a catalogue **view** limit for
four-thousand-episode feeds -- a view rather than a trim, because the obvious
fix would have been the one thing here that destroys something.

Announcements: three-position notification priority replacing a boolean; a
per-podcast quiet-hours exemption; a spoken-name override for titles TTS
mangles; title-cleanup rules with a preview; a per-podcast earcon; the
gone-quiet and failed-check notices; a global announcement budget; and
per-podcast row speech.

Curation: season/episode sort read from `itunes:season` and `itunes:episode`; a
default playlist; free-text **labels** usable as a smart-playlist rule; an
artwork override.

### 22.5 What a row says

A screen reader reads every row of every list out loud, in full. Cast's answer
had been one boolean over a question with at least seven answers.
`core/podcasts/row_speech` is the composer: a named order (title, podcast or
date first) and independent switches for the podcast's name, the date, the
length or time remaining, the download state, the numbering, whether the
episode has chapters or a transcript, and the description at off/brief/full.
Per podcast as well as globally.

Two rules the composer keeps: nothing is said twice (the podcast's name is
dropped inside its own episode list), and every part is droppable with the row
still parsing.

### 22.6 Where the numbering came from

`PodcastEpisode` gained `season`, `episode_number` and `episode_type`, all
three of which were in the feed bytes all along and were being discarded. The
numbering is the only dependable order a serial show has, because its published
dates get re-stamped on a feed rebuild. A merge only ever takes them *upward*,
so a partial feed cannot un-number episodes a sort is relying on.

### 22.7 The safety properties

Nothing added here deletes anything. Everything fails open -- an unreadable
value, an unknown choice, a clock that cannot be read all land on "carry on as
before", because these settings restrict and a restriction nobody chose is the
worst kind. Both hiding settings name their way back in their own help. And
every catalogue entry says what it does *not* do, enforced by a test.

## 23. The main window, reworked (2026-09-30)

One afternoon of a screen-reader user actually using the app produced the
list behind this section. None of it was a missing feature; all of it was the
app being harder to use than it had to be. The full plan, its principles and
its phases are in the repository's `qc.md`; this section records what shipped.

### 23.1 Follow, not Subscribe

`core/podcasts/follow_words.py` holds the vocabulary once -- Follow, Unfollow,
Following, the menu labels with their access keys, and the sentences -- because
a wording that lives in fourteen literals is one that gets half-changed. Two
things keep the old word on purpose: the OPML *file* is a subscription list,
the format's own name; and no on-disk field is renamed, because a migration is
too much risk for a wording preference. On 2026-10-01 the remaining
user-visible strings followed (row menu, Preview, the ACB row, Podcast
Settings, Delete Folder, extras, refresh and check-state sentences, the
add-by-address outcome shared with Radio, the shared undo label); internal
identifiers such as `ACTION_SUBSCRIBE` and `unsubscribe_show_prompt` keep
their names.

### 23.2 Add Podcast

Preview had never worked: it called a function that did not exist, failed in
the background, and set a status label a screen reader does not read. Both edit
fields announced as bare "edit" because `SetName` is not an accessible name on
wxMSW -- the name comes from the `wx.StaticText` created immediately before the
control. Both now have a real label created first, with inline `SetHelpText` so
the help audit can see it. The results list gained a Following column (silent
on rows not followed: the interesting state is the rare one), the action button
alternates Follow and Unfollow through the shared undoable prompt, and the list
has a context menu on `EVT_CONTEXT_MENU` as well as the mouse, with items
disabled rather than absent so the menu's shape is the same on every row.

### 23.3 The pinned views open

Inbox, New Episodes, Continue Listening and Favorites carried counts and had no
children. `ui/podcasts/library_tree.py` fills each on first expansion through
the placeholder mechanism podcasts already used. Cross-show lists name the
podcast on every row; Favorites opens to podcasts rather than flattening their
episodes, so no episode appears under two parents. Play on a view plays its
first playable episode. `tests/unit/ui/podcasts/test_cast_library_tree.py` pins all of
it: no expander on an empty view, newest first with the podcast named, the
200-row cap and its "more" row, Favorites to podcasts, and Play's choice per view.

### 23.4 Places, modes and switches

The View menu carries the spine: seven places in Earshot's order, each landing
focus in the tree (`ui/podcasts/places.py`), with no announcement because the
focus move says it (GATE-13). `core/podcasts/menu_mode.py` defines Simple and
Advanced: rows are omitted, not disabled; the switch is present in both modes;
every omitted row is a command the palette and Go To reach. `CAST_AREAS` in
`apps/podcasts_view_menu.py` lists the eight areas Customize Features can turn
off; defaults are on and only an explicit off is stored. Hide Caught-Up
Podcasts, the Inbox folder scope (`core/podcasts/inbox_scope.py`, narrowing by
the *library* folder tree and never the Inbox's own), Show Status Bar and the
Window menu complete it. Keyboard Shortcuts and Global Hotkeys are **not**
advanced rows (removed from `ADVANCED_ROWS` 2026-10-01): every key is the
listener's, and the editors stay in Help in both modes, as in Radio and Lite.

### 23.5 The menu bar wins the letter

GATE-15 (`tools/check_menubar_mnemonics.py`): no control in a window may share
an Alt letter with a top-level menu, because wxMSW gives an ambiguous Alt+letter
to the control. The first run found Alt+S (Stop against Subscriptions) and
Alt+V (Favorites against View). Subscriptions became Podcasts; the buttons
yielded to Y, T, F, U, A, I.

### 23.6 The status bar

Nine cells (`ui/podcasts/status_bar.py`, readouts in `status_bar_cells.py`),
off the Tab order, entered with F6. An action cell's label is its action; a
readout's label is its value; a readout with nothing to say shows its bare
name. Every cell carries authored help, no cell claims an access key, and
entering the bar says the region once and nothing else. Built even when
hidden, so the first F6 after switching it on has something to focus.

### 23.7 Feed Check

`core/podcasts/feed_health.py` builds a worst-first report from the
bookkeeping `check_state.py` already keeps; reading it never checks a feed.
The window (`ui/podcasts/feed_check_dialog.py`) adds Retry, Retry All Failed
and Copy Feed Address, a context menu on the keyboard route, and a summary
spoken on open. A failing feed is never described as abandoned. Asking about a
podcast's state no longer creates an empty record for it, which would have
grown the saved file by one entry per podcast every time the window opened.

### 23.8 Cores landed ahead of their surfaces

Three wx-free modules shipped with tests and no window yet:
`core/podcasts/refresh_audio.py` (get this episode's file again from wherever
the feed now says it is; position, played mark and note untouched),
`core/podcasts/inbox_removal.py` (Remove from Inbox is a triage decision with
its own marker, so a publisher's re-issue cannot undo a listener's dismissal;
the download goes only if the show's own settings say downloads go when done),
and `core/podcasts/quick_plays.py` (Play an Unheard Episode: queue, then Inbox,
then everything unplayed, never anything already started; Play Queue Shuffled;
Clear Entire Queue). The three quick plays are reachable from the Command
Palette; the other two wait for the Phase 2 episode surfaces.

### 23.9 Every control has a name

GATE-CTLLABEL (`tools/check_control_labels.py`) found 165 controls across the
family whose name was set through `SetName` and never read. Cast's fifteen are
fixed; the family count may only fall. `ui/labelled_field.py` makes the correct
construction order the easy one; since 2026-10-01 it takes no `help=`, because help
set inside a helper is invisible to the help audits -- callers set it inline.

### 23.13 Find in library, the interim of P10 (2026-10-01)

`ui/podcasts/library_find.py` (`CastLibraryFindMixin`, inherited by the main
panel's mixin): a labelled box above the tree; `EVT_TEXT` restarts a 350 ms
pause, after which the tree is rebuilt as `find_rows` (podcasts, then episodes
newest first, then notes, from `filtering.search_everywhere`) tagged with the
library's own item data, capped at 200 with a "more" row, and the count is
announced once. `_reload_library_tree` refreshes the matches instead of the
library while Find is active. Escape or an empty box restores the library
with the cursor on the row it left; Down moves into the matches. View > Find
in Library is Ctrl+F. Transcripts are excluded until F-09's index exists.
`podcasts_view_menu.py` joined the app menu-accelerator gate, whose first run
gave Customize Features Radio's Ctrl+Alt+C.

### 23.25 Earshot parity, complete (2026-10-03)

The Earshot parity plan (ear.md, compared against Earshot 1.2.3, TestFlight
273, S:/code/earshot 63dc641) is closed and its working file retired. Parity
meant the listener gets the same outcome, not the same screen: keys where iOS
has gestures, the Command Palette where iOS has Siri.

- R1 Hide Caught-Up Podcasts (View, remembered; "All caught up" when everything
  is hidden). R2 Feed Check. R3 Refresh Episode Audio on the episode menu and
  the palette (`ui/podcasts/refresh_audio_command.py` over
  `core/podcasts/refresh_audio.py`: re-read the feed, ask once naming the
  download, keep position, played, note and speed). R4 Delete in the Inbox
  also deletes the download when "Delete its downloaded file" is on, never for
  a kept episode. R5 the Inbox scoped to one library folder (View > Inbox
  Folder). R6 Play an Unheard Episode (queue, then Inbox, then everything;
  newest or oldest), Play Queue Shuffled, Clear Entire Queue, in the palette.
  R7 Jump List: dropped by Jeff, 2026-10-03; not planned. R8 to R10: 23.20.
- A1 to A12, the AI verbs: 23.21 and the shared hosted AI.
- B1 to B3: 23.24.
- Principle kept from the plan: no invented formats -- where Earshot has not
  defined something, Cast follows the shared Listening Places proposal or
  waits.

### 23.23 Library and Inbox layouts (2026-10-03)

- Six catalogue settings, global, stored by id (`settings_defs_views.py`):
  `library_layout` (folders_first | folders_only | podcasts_only | mixed),
  `folder_sort_mode` (custom | name_az | name_za | most_unheard |
  most_podcasts), `library_folders_open` (open | closed), `library_counts`
  (unheard | podcasts | both | none), `library_hide_empty_folders`,
  `inbox_layout` (episodes | folders_first | folders_only).
- Plans in `library_view.py`; invariant: no layout hides a podcast or an Inbox
  episode. Folders only adds a "Podcasts in no folder" group, tagged `group`.
- The Inbox groups by each show's top-level library folder; a folder row opens
  in place, Backspace returns.
- View > Rearrange Library and Inbox (Ctrl+Shift+R), live; Preferences > The
  library (ninth section).

### 23.24 Earshot B1-B3 (2026-10-03)

- B1: `PodcastEpisode.last_played_on` from the winning device file's
  `device_label`, or its app name; shown in Continue Listening; cleared by any
  local position change.
- B2: an Earshot 1.2.3 device file fixture written to Earshot's encoder.
- B3: subscriptions and folders in the plain file per the shared proposal's
  section 6.7, behind `PlacesConfig.share_subscriptions` (off).

### 23.22 Why it is queued, and choices shared with Quill Radio (qc.md X-04, X-05; 2026-10-03)

- A queue slot carries an optional `reason` (`QueueItem.reason`, written only
  when set): Auto-Queue, "the lineup <name>", "your listening run", "a watched
  folder". The Play Queue place adds "; queued by <reason>" to the row's
  status. A slot the listener added has no reason and says nothing extra.
- Preferences > The window: **Share these choices with my other Quill apps**
  (`share_family_prefs`, off). Shared through `quill/core/family_preferences.py`
  in the shared data folder, only between apps that each turned it on, and only
  `announce_dialog_transitions` and `action_feedback`. Cast adopts at launch
  and says which choice it took; turning it on adopts or publishes; saving
  Preferences publishes.
- Settings search covers all eight Preferences sections (X-01).

### 23.21 Cast's own AI verbs (ear.md A2-A10; 2026-10-03)

`quill/core/podcasts/ai_listening.py` (wx-free: prompts and readers for A3-A8,
`tidy_rows` for A9) and `quill/ui/podcasts/cast_ai_features.py`
(`CastDomainAiMixin`, carried by `CastExtensionsMixin` under GATE-11), with
`ai_review_dialog.py` (Accept/Skip per row in words, Space toggles, Apply
Selected, Cancel changes nothing) and `ai_answer_dialog.py` (read-only answer,
Copy). Every request goes through the shared service's `ask("ask", ...)` behind
`_ai_ready` (switch and agreement); failures through `report_failure`. Rows are
appended to Help > AI Features by a hook the adapter calls, so `CastAiMixin`
still has no command of its own. Organise asks in batches of 40; a run is
measured with Cast's own lengths; playlist rules resolve names to ids;
chapter titles are saved to the inference cache. Tidy sends nothing and works
with AI off; unfollow rows go through the ordinary undoable prompt. A10 is a
test: the background passes and destructive verbs cannot import the AI.

### 23.20 Earshot parity R8-R10 (ear.md; 2026-10-03)

- **R8, names that survive.** `PodcastShow.feed_title` and
  `PodcastEpisode.feed_title` hold the feed's own name when the listener
  renamed it ("" otherwise; written only when set). `custom_names.rename`
  applies a rename and keeps the feed's name; renaming to nothing or to the
  feed's name restores it. `merge_episodes` updates `feed_title`, never the
  listener's title. `PodcastFolder` and `ExpiredEntry` moved to
  `models_folder.py` (re-exported) to make room; `models.py` ratcheted to 200.
- **R9, notice actions on keys.** `ui/podcasts/notice_actions.py`: Ctrl+Enter
  plays, Space queues, on a new-episode notice in the Notifications place and
  the Notifications window, and in both rows' menus.
- **R10, this computer only.** Delete All Podcast Data is now Clear All
  Podcast Data from This Computer, and every sentence says the phone, other
  computers and the shared place folder are untouched. Cast has no "delete
  everywhere": subscriptions do not sync (B3).
- B1-B3 stay blocked on Earshot (ear.md 5a).

### 23.19 Phase 3: nothing silent (qc.md P4, section 10; 2026-10-03)

- `ui/podcasts/say_status.py`: the one way to write a status line -- set it
  and speak it once when it changed; clearing is silent; `speak=False` is
  written at the call site with its reason (a paced progress count, a line
  whose fuller sentence the caller speaks, a count that follows the
  selection). Every Cast status write was moved to it: Add Podcast (Find,
  Find failed, Fetching, Could not follow it, sign-in needed, Safe Mode,
  empty fields -- several of which were silent), Preview, Search Everywhere,
  OPML import, Find in library, the Podcast Manager's episode counts.
- `ui/podcasts/failure_report.py`: one helper for a failure -- spoken (with
  the error sound through `outcome_feedback.say_failure`), or for work Cast
  did on its own spoken unless Quiet Hours hold it back, or only recorded --
  and always written to Recent Problems. The two `on_failure=lambda *_a: None`
  handlers (chapter prefetch, audio processing), ACB Media, chapter inference
  and analysis, transcripts, the chapters dialog, Follow from About This
  Episode, Preview and watched folders use it.
- GATE-CAST-SILENT (`quill/tools/check_cast_silence.py`, in
  `platform_report`): in Cast's scope, a status `SetLabel` outside
  `say_status`, or an `on_failure` that says nothing or only logs, fails.

### 23.18 Phase 7: the listening extensions (qc.md section 18, 2026-10-03)

`quill/apps/podcasts_extensions.py` (`CastExtensionsMixin`, ahead of the shared
podcast mixins) and `quill/core/podcasts/listening_words.py` (wx-free):

- **Time Remaining**, Ctrl+Shift+T (`podcasts.time_remaining`, Episode menu,
  also offered as a global hotkey): position of length, what is left, the real
  time at the speed in force, and the sleep timer.
- **Ctrl+Home** to the launch place, first row; caught in the frame's char
  hook, never an accelerator, so a text field keeps Ctrl+Home.
- **Shift+Space**, Play This Next: `listening_words.play_this_next` inserts
  after the playing episode's slot (the playing episode stays queued, ear.md
  R4), else at the front; char hook, skipped in text fields.
- **Up next**, about ten real seconds before the end, through the
  controller's one-second tick: the run-end choice's next episode
  (`queue_steps.step_next` or the folder's next unplayed), once per episode,
  never with Stop After This Episode or a sleep-at-end, through
  `quiet_hours_ui.speak_background`; `PodcastHistory.announce_up_next` (on).
- **Ctrl+N** with one web address on the clipboard fills Add Podcast's feed
  address and focuses it (`AddPodcastDialog.prefill_address`); Enter follows.
  No preview: Add by URL fetches and validates the feed as it follows.
- **Bookmarks**: Bookmark with a Note (Ctrl+Shift+D), Bookmarks in This
  Episode (Ctrl+Shift+J; `show_bookmarks(anchor=...)` filters the shared
  window), a Bookmarks button in Now Playing, and a Bookmarks tab in About
  This Episode (`extras.ACTION_JUMP`, Go There plays from that moment).
- **Earcons** for added-to-queue, removed and marked played
  (`SoundEvent.CAST_QUEUE_ADDED`, `CAST_REMOVED`, `CAST_MARKED_PLAYED`, in the
  ink pack), resolved through `action_feedback.resolve` by Cast's own
  `PodcastHistory.action_feedback` (default *both*, so nothing went quiet);
  failures through `resolve_failure` (`ui/podcasts/outcome_feedback.py`).
- **What I care about in this podcast**: a show-level text setting
  (`listening_note`, Curation) for later AI features to read.
- **Global hotkeys**: Podcasts: Now Playing window and Podcasts: Time
  Remaining join the allowlist; Cast's Global Hotkeys window now lists only
  commands Cast registers (`_global_hotkeys_registered_only`), so it no
  longer offers Radio's and the editor's.
- **Undo History** (Edit > Undo History, shared with Quill Radio):
  `undo_last.UndoHistory` keeps ten steps; Ctrl+Z still takes the newest, and
  pressing it again takes the one before; each held deletion gets its own
  holding folder (`undo_last_ui._step_dir`).
- Timestamps in show notes were already links (`notes_reader`, 23.13).
- Not built: a braille *status line*. Neither JAWS nor NVDA gives an app a
  status region, and every Cast announcement already goes to braille as a
  flash message through the shared announcement service.

### 23.17 The 2.0 follow-ups: watched folders, a show/hide chord, two menu rows (qc.md C2-01 to C2-03, 2026-10-03)

**Watched folders (C2-02, section 5d of qc.md).** `WatchedFolder` records live
in the library file (`watched_folders`), replacing the one `watched_folder`
string a Personal Audio show carried; `watched_folders.migrate` turns each old
string into a record with the defaults and marks the files the show already
has as seen, so an upgrade imports nothing twice. Each record carries a name,
include-subfolders, one-group-per-subfolder, file types, what happens to the
original (keep a copy, move, or play in place), what an arrival does (add,
queue, play when idle), Tell me (each, batch, quiet), a minimum length
(30 seconds) and a speed. `plan` does the slow half on the task manager (find,
skip seen by size and time, wait for anything modified in the last five
seconds or not yet openable, skip known content hashes and short files, copy
through `_staged_copy`); `apply` does the quick half on the UI thread. Live
watching is `wx.FileSystemWatcher` (created after the event loop starts) feeding
`SettleTracker`, which releases a path once its size has held still for five
seconds and it opens; a network path (`is_network_path`) is polled every ten
minutes instead. A full look runs at launch and on `EVT_POWER_RESUME`. Arrivals
write an `IMPORT_FINISHED` notice and are spoken by Tell me; a folder's problem
is spoken once until it recovers and written to Recent Problems. The window
(`ui/podcasts/watched_folders_window.py`) is a peer like Notifications; the
settings page is `ui/podcasts/watched_folder_settings.py`; the host side is
`ui/podcasts/folder_watch.FolderWatchMixin`, shared by QUILL through
`PodcastsMixin`, where Podcasts: Watched Folders... is a palette command. Safe
Mode watches nothing. Ctrl+Alt+W opens the window; Scan Watched Folders stays
as a palette command and scans every folder.

**Show/hide chord (C2-01).** Cast registers its own system-wide show/hide,
Ctrl+Alt+Shift+F12 (`podcasts_routes.CAST_TRAY_HOTKEY`), and sets
`_own_tray_hotkey` so the shared default (Ctrl+Alt+Shift+Q, which is QUILL's
own show/hide key) is never added, even when Windows refuses Cast's own
chord. Every Ctrl+Alt+Shift letter already belongs to a family app.

**Menu rows (C2-03).** Episode > Player Information... (Ctrl+I) and Podcasts >
Carry My Place Between Machines... (Alt+H in the menu) were palette-only.
Bookmark This Moment (Ctrl+Alt+A) and Skip Silence (Ctrl+Shift+9) gained
Episode rows in the same pass; their keys never fired in Cast without one.

### 23.16 Phase 5: one vocabulary, two settings windows, refresh schedules (2026-10-02)

**Words** (section 12): `core/podcasts/words.py` is the list (forbidden word ->
the word to use) and the allowed phrases that carry a format's own name;
`quill/tools/cast_words_audit.py` (GATE-CAST-WORDS, on the `platform_report`
roster) walks every non-docstring literal of two or more words in
`quill/ui/podcasts` and `quill/apps/podcasts*.py`. The sweep fixed 39
literals; nine remain in the reviewed allowlist
(`tests/unit/ui/fixtures/cast_words_allowlist.json`), all in QUILL's Podcast
Manager and Search Everywhere, which Cast never opens, each with its reason.
An entry with no reason fails, as does a stale one.

**Settings** (section 13): `ui/podcasts/preferences_window.py` is a Section
choice over a scrolling panel rebuilt per section. App rows are the table in
`apps/podcasts_preferences.app_rows` (history-backed); shared defaults are the
catalogue at `LEVEL_GLOBAL`, placed by `section_of` (by id, by prefix, else by
category), built by kind with the definition's own help, and written with
`set_value` only when changed -- so a new default needs a definition and
nothing in the window. `default_launch_view` is offered as the places
(`launch_place.CHOICES`, appended so stored values keep meaning);
`refresh_schedule` is a button that opens the schedule dialog. Podcast
Settings and Skip Settings open Preferences on Fetching and Playing; the menu
row is Settings for This Podcast (Ctrl+Alt+,) on the selection.

**Schedules** (5e): `core/podcasts/refresh_schedule.py` is pure -- `Schedule`
with five kinds, JSON `encode`/`decode`, `from_legacy`, `describe`, `learn`
(the usual weekday and hour of the newest twelve, three agreeing within an
hour), `parse_hint` (`sy:updatePeriod`/`updateFrequency`,
`podcast:updateFrequency` rrule) and `next_due(schedule, now, last_checked, *,
published, hint)`, tested against a fixed clock. `settings_defs_fetching.py`
adds `refresh_schedule`, `check_on_launch`, `check_on_resume`,
`check_in_quiet_hours`, `check_burst_after_miss` at every level, stored by id.
`schedule_policy.py` resolves them: an empty schedule at every level falls back
to `refresh_minutes` (the migration -- nothing rewritten, nothing changed on
upgrade), `next_check`, `is_due`, `describe_for`, `next_check_words`, and
`summary` for Preferences. The feed reader carries the hint as
`FeedInfo.hint_minutes/hint_words`; `check_state.record_hint` keeps it beside
the success stamp. `PodcastCheckMonitor._show_is_due` asks `schedule_policy`,
honouring Quiet Hours unless `check_in_quiet_hours`. Feed Check gains Schedule
and Next check columns and Check Now / Change Schedule rows;
`ui/podcasts/schedule_dialog.py` is the dialog, its kind rows shown per kind,
confirming in `describe`'s words.

At launch, `CastPlaceRoutesMixin._check_at_launch` checks each podcast whose
*Check when Cast opens* is on, and -- with the automatic check on -- each
whose schedule fell due while Cast was closed (*Catch up on a missed check*).
*Check when the computer wakes* binds `wx.EVT_POWER_RESUME` on the frame
(`_watch_power_resume`) and checks each podcast whose switch is on, once.

### 23.15 Phase 2: one window (2026-10-02)

The main window is `CastMainPanelMixin._build_main_panel`: Now Playing (a
read-only bold field), Find, `PlacesList` (`ui/podcasts/places_list.py`) beside
`ContentPane` (`content_pane.py`: a heading and a Simplebook with the report
list and the folder tree, carrying Radio's Tab-across-Simplebook fix), the
Notes reader, the button row and the status bar. `core/podcasts/places.py` is
the model: eleven places with kind, area and empty sentence; `PlacesLayout`
(order and hidden, `places_layout` on `PodcastSettings`, Recently Expired
hidden by default), `move` (skipping hidden rows), `move_sentence`, `label`,
`count`, `empty_state`. `ui/podcasts/places_host.py` is the one verb,
`show_place`, used by every route -- Places, View rows, Go To, status cells,
a notice's Enter, the old openers (`apps/podcasts_routes.py` answers
`open_podcast_manager`, `_open_play_queue`, `open_podcast_downloads`,
`open_continue_listening` with places, ahead of `PodcastsMixin`). Delete in a
list removes from the place only, per place.

The Manager's verbs moved to `ui/podcasts/manager_verbs.py`
(`ManagerVerbsMixin`, 38 methods) and are shared by QUILL's Podcast Manager and
Cast's frame; `ui/podcasts/episode_list.py` (`CastEpisodeListMixin`) gives the
frame the Manager-shaped names (`_library`, `_controller`, `_episodes`,
`_current_episodes`, `refresh_tree`, `dialog`...) so `ManagerActionsMixin`,
`ManagerDownloadsMixin`, `ManagerRowViewMixin` and `ManagerExpiredMixin` run on
the frame unchanged. Rows are filled by column id, which fixed the Manager's
cross-show fill writing by position. The selection contract
(`_selected_tree_data`, `_selected_show`, `_selected_episode`) reads whichever
pane is up, so the tree's context menus, the button row, the Winamp letters and
the notes pane follow both. `manager_dialog.py` stays for QUILL's editor, which
still opens it; Cast has no door to it.

Notifications (5b): `core/podcasts/notices.py` -- six kinds as the notice
`category`, a `notify_<kind>` switch each on `PodcastHistory`, `record`, and
`digest` (one sentence since `last_seen_at`, stamped at shutdown). Cast's feed
refresh writes new-episode, feed-failed and gone-quiet notices; a finished
download writes one and the toast honours `toasts_enabled`.
`ui/podcasts/notifications_window.py` is a peer (Window menu, Close Ctrl+W,
hidden on close) with Play Now, Add to Queue, Go to the Podcast, Mark Read.
The status bar gains a Notifications cell between Downloads and the sleep
timer, and `support_menu` now keeps its Notifications id.

Feature switches (17): `core/podcasts/cast_features.py` -- 47 `AppArea`s in
eight groups (the eight original ids kept), `COMMAND_AREAS` mapping every id
Cast registers or binds, and three `PROFILES`. Places, menu rows (`_area_row`),
status cells (`CastStatusBar._build_specs` filters by `_cell_enabled`) and Go
To (`DESTINATION_AREAS`) follow; the palette shows "(off in Customize
Features)" through the frame's availability probe and `palette._unavailable_suffix`.

Not yet built from Phase 2: the episode-state filter is one View > Show setting
but not yet per place; folder tree reorder of places via the tree; the
transcripts in Find (F-09).

### 23.14 AI help: the shared hosted AI through an adapter (ear.md A1, A11, A12; 2026-10-02)

`quill/ui/podcasts/cast_ai_host.py` is what QUILL got when the hosted AI came
to the big editor: `CastAiHost` answers the five things
`hosted_ai_commands` asks of "the app" (a data dir, settings it can read and
write, a feature switch, a menu rebuild, `ai_agent_name = "QUILL Cast"`), and
`CastAiMixin(HostedAiMixin)` is hooks only -- `_ai_parent`, `_ai_control`
(the Notes reader's field under the library tree), `_ai_host`,
`_ai_switch_route`, and `_replace_range` / `_insert_below` which announce
that the notes cannot be changed here and name Copy. A test asserts the mixin
has no `cmd_*` of its own, the way `test_main_frame_hosted_ai.py` does for
QUILL, because a second implementation is how the family rule gets broken
quietly. "The settings" are the `PodcastHistory` record: `ai_help_enabled`
(off), `ai_privacy_accepted_version`, `ai_own_key_provider`,
`ai_own_key_model`, all round-tripped. The switch is **AI help** in
Preferences, with the sending named in the label; the agreement is the
shared one, and both are needed. Help > **AI Features** holds the family's
rows on the family's chords (`APP_KEYMAPS["cast"]`), the one divergence
commented: Privacy Agreement is Alt+Shift+F2 because Ctrl+Alt+Shift+K is the
Keyboard Shortcuts Sheet. The rows register with the command registry, so
the Command Palette and the Keyboard Manager see them. The user guide's "AI
help: what the AI can do, and what it will never do" is A12's section.

**One ChatGPT sign-in per app** (`quill/core/ai/chatgpt_state.py`, split from
`chatgpt_account.py` under GATE-11). Every app shares `app_data_dir()`, and
one `ai/chatgpt.json` meant the second app to sign in overwrote the first's
client id and model while each kept its own refresh token under its own slug
-- an app that believed it was signed in and could not refresh. The state is
now `ai/chatgpt-<slug>.json`, the legacy file is read until the app writes
its own, each record carries `agent_name`, and `sibling_sign_ins` reports the
other apps signed in by name; the account window's signed-out status says so,
because a browser that is already signed in makes Continue one Allow.

### 23.13 Now Playing, the Notes reader and Links in These Notes (section 5 and 5c, 2026-10-02)

`quill/ui/podcasts/now_playing_window.py` is window 2: `NowPlayingWindow` over
the host's controller, library, chapter list and sleep-timer controller, with
its controls built in `now_playing_layout.py` (GATE-11) in the order a screen
reader meets them, every label created immediately before the control it
names and every control's help inline (GATE-CAST-HELP). `CastNowPlayingMixin`
(`apps/podcasts_now_playing.py`) makes it at start-up, hidden, and registers it
with the `WindowManager` so it is always Ctrl+2; closing vetoes and hides,
which keeps the number and stops the once-a-second `wx.Timer` (the
timer-ownership gate sees the stop). The Episode menu row (`podcasts.now_playing`,
Ctrl+Alt+2 in `APP_KEYMAPS`) and the Play cell's first row open it;
`_on_podcast_state_changed` is overridden to refresh an open window and, when
`PodcastHistory.switch_to_now_playing` is on, to show it once per episode as
playback starts.

Three rules in the window are load-bearing: the slider is never written while
it has focus or is being dragged (a value written under a focused slider is a
value the reader repeats), so only the time readout moves each second; the
chapters' *playing* mark is a Status-column write and never a selection
change; and the window announces nothing on show -- the slider's own key
handler says the time, the chapter jump says the chapter, and the rest is the
host's own verbs (`podcast_toggle_play_pause`, `open_sleep_timer_dialog`,
`podcast_mark_played_and_next`, `share_moment`, `open_podcast_episode_extras`),
so a sentence is never worded twice. Speed goes through `speed.apply_speed`
(scope and all); Custom... is a `TextEntryDialog`.

**Your note** is one `EpisodeNote` per episode at position 0 under an id that
starts `about:` (`episode_notes.episode_level_note` /
`set_episode_level_note`), so every existing list and jump treats it as a
note at the start and the field can find it again; empty text removes it.

**The Notes reader** (`quill/ui/notes_reader.py`) is a native `TE_RICH2`
read-only field over `core/podcasts/notes_render.py`, which parses the HTML
into blocks (heading with level, paragraph, list item, preformatted) and
absolute-offset spans for links and timestamps (`h:mm:ss` or `m:ss`, a span
inside a link belongs to the link). Styles are applied by range; Tab,
Shift+Tab, Enter, H, Shift+H, Ctrl+F and F3 are handled in the field's
`EVT_CHAR_HOOK`. `core/podcasts/notes_export.py` is the one place the four
copy formats live (plain, plain with links, Markdown, formatted = HTML on the
clipboard with an RTF object and a text object beside it), with a test per
format, and `browser_page` is the podcast's own HTML with scripts, styles,
frames and event handlers removed. `PodcastHistory.notes_copy_format` keeps
the chosen format. `link_list_dialog.py` gained Copy Title and Address and the
spec's names; the reader passes it the unique links with their titles.

**Outside Now Playing (later the same day, Jeff: "if you arrow to a podcast
episode and hit tab shouldn't the show notes show there").** The main window
gets a `NotesReader` under the library tree (`main_panel.py`:
`_refresh_notes_pane` on `EVT_TREE_SEL_CHANGED`; an episode's notes, a show's
description, else a placeholder; `_seek_selected_episode` seeks the playing
episode or starts the selected one at the timestamp through
`start_episode_playback(resume_ms=)`), with this window's own access keys (O,
C, K, R -- N and L are Find and Library). `ShowNotesDialog` is rewritten over
the reader (Send to Editor and Save As kept; the View-as choice and the
`HtmlWindow` are gone, and with them the rich-label test), and the Manager's
`view_show_notes` hands it a seek that works while that episode is playing and
says what to do otherwise. The reader gained `labels=` and `set_placeholder`.

Tests: `tests/unit/core/podcasts/test_cast_notes_render.py` (the renderer, the
four formats, the browser page, the episode-level note, the two history
fields) and `tests/unit/ui/podcasts/test_now_playing_window.py` (a real
`wx.App`, a fake host: loading, the hidden-not-destroyed close, the slider
keys, every button's verb, the chapter mark, Your note, the copy format, the
sleep readout, speed, volume, favorites; and the reader's Tab, H, find,
timestamp and empty cases).

### 23.12 Closing keeps a record of what it could not save (F-06, 2026-10-01)

`_cast_shutdown` runs each step through `core/shutdown_report.ShutdownReport`:
the listening-statistics and library flushes are must-record; Quillin
teardown, the player, transfers, media keys, hotkeys and tray are best-effort;
the task manager is background. A must-record failure is persisted as a
pending sentence and a `KIND_SHUTDOWN` problem row; `_cast_launch_notices`
says it once at the next launch after media health, and registers a Retry that
flushes both again. Nothing persisted carries exception text.

### 23.11 Preferences, extracted, with a launch place (2026-10-01)

`_open_preferences` moved to `apps/podcasts_preferences.py` (`CastPreferencesMixin`)
under GATE-11, and `podcasts.py`'s budget was ratcheted down to its new size. The
window gained "Where to land on la&unch:" in the Podcasts group, over
`core/podcasts/launch_place.CHOICES`, saved to `PodcastSettings.default_launch_view`
with the library and only when it changed. "Switch to Now Playing when playback
starts" landed with Now Playing on 2026-10-02 (23.13). The planned "Switch to Now Playing when
playback starts" is deliberately absent until Now Playing exists: a switch for a
surface that is not there is a setting that lies.

### 23.10 The object is in the label (2026-10-01)

The same rule renamed the per-setting revert button in Settings for This
Podcast from "Follow" to "Use shared default for <setting>" (its inert
`SetName` removed), and the bulk button to "Use Shared &Defaults".

The 2026-09-30 "Play what?" fix put the object in the button's accessible name.
The survey the next day (qc.md 6b, item 1) found that on wxMSW a button is
self-labelled and `set_accessible_name` is inert on it, so the fix was
inaudible. `core/transport_button.py` is the family answer, shared with Quill
Radio's main window: one function returns the button's label (verb, access key,
object, elided at forty visible characters, ampersands doubled), its full
sentence, and its verb, from one reading of one state; per-app mnemonics and
the app's own active verb (Cast pauses, Radio stops) are parameters.
`core/podcasts/transport_intent.py` is Cast's reading of it. The row gives each
button an equal share so it never reflows; Unfollow names the selected podcast
or the selected episode's podcast; Stop is enabled only while something is
playing or paused. GATE-15 now reads every label the button can produce
through `label_samples()`, and `test_button_object_in_label.py` fails the
build if `set_accessible_name` ever targets a `wx.Button` in Cast again.

---

See `CHANGELOG.md` for the full, versioned history.
