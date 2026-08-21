# QUILL Cast -- Product Requirements

Version 1.1

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
- Unlock-gated Audio Description Project menu (top-level) when `future.adp_assistant` is unlocked.

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

- **iTunes stays the default and stays keyless.** Podcast Index requires
  credentials, and the source is simply absent from the picker until they exist
  -- a feature that only works after registering for an API key is a feature
  most people do not have.
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

See `CHANGELOG.md` for the full, versioned history.
