# Quill Cast -- the standalone podcast app (not part of public QUILL 1.0)

> **Not part of the public 1.0 product.** Quill Cast is one of the five companion
> apps gated behind `RELEASED_APPS` (`quill/core/app_launcher.py`) for QUILL
> 1.0.0, and the editor-embedded **Podcasts** feature it shares its code with is
> dev-build-only for the same release. Neither is reachable in a public build:
> the QuillVille menu lists only QUILL, Quill Radio, and Quill Weather, and the
> Podcasts commands, dialogs, status-bar cell, and tray section are gated with
> them.
>
> This file is the home of every piece of Podcasts / Quill Cast documentation
> that used to live in the public user guide and PRD. Nothing here was deleted --
> it was moved during the 1.0.0 documentation consolidation, with heading levels
> shifted to fit this file and wording changed only where one sentence described
> both a public app and a gated one. When Cast ships publicly, this material is
> what gets promoted back into the public docs, or into Cast's own doc bundle.

**Where each part came from**

| Relocated from | Source section |
|---|---|
| `docs/user guide/userguide.md` | `## Podcasts` (the whole chapter) |
| `docs/user guide/userguide.md` | `## Quill Radio and QUILL Cast: the standalone apps` (the Cast half) |
| `docs/user guide/userguide.md` | "Background checks..." -- the podcast-feed monitor paragraph |
| `docs/user guide/userguide.md` | "Global Hotkeys..." -- the Podcasts row |
| `docs/user guide/userguide.md` | "Sound notifications and earcons" -- the Cast clause |
| `docs/user guide/userguide.md` | `## Sleep Timer` -- the Podcasts half |
| `QUILL-PRD.md` | `### 5.84g Podcasts (Phase 1-2, shipped)` (the whole section) |
| `QUILL-PRD.md` | `### 5.89e Standalone companion apps` (the Cast half) |
| `QUILL-PRD.md` | `### 5.84h Shared media Sleep Timer` (the Podcasts half) |
| `QUILL-PRD.md` | `§35.1 The apps` -- the Quill Cast family entry |

> **Naming note.** `docs/podcast/` is *not* this app. That folder holds the
> 54-episode audio course *about* QUILL (documentation/marketing content, also
> styled "The QUILL Cast"); it has nothing to do with the Quill Cast podcast
> client documented here.

---

## Part 1 -- relocated user guide material

_Moved from `docs/user guide/userguide.md`. Heading levels are one deeper than in
the source; wording is otherwise unchanged._

### Podcasts

**Tools > Media > Podcasts...** is QUILL's podcast client: subscribe to shows, organize them into folders, download episodes for offline listening, and resume exactly where you left off. It shares Internet Radio's core idea — one player that keeps going after you close the dialog — and is disabled entirely in Safe Mode, since it is a network feature.

#### Subscribing to a podcast

The Podcasts dialog's **Add Podcast...** button opens a dialog with three ways in:

- **Search.** Type a show name and press **Search** to query Apple's free, keyless iTunes Search directory. Arrow to a result and press **Subscribe to Selected**.
- **Add by Feed URL.** If you already know a show's RSS/Atom feed address (or it isn't in iTunes' directory), paste it into the URL field and press **Add**.
- **Import OPML...** reads a whole subscription list — including its folder structure — exported from another podcast app, so switching to QUILL doesn't mean starting over. **Export OPML...**, back on the main Podcasts dialog, writes your library out the same way.

#### Organizing your library

The Podcasts dialog shows a folder tree on the left and, for whatever folder or show is selected, an episode list on the right — the same tree-and-list shape Internet Radio's dialogs use.

- **New Folder...** creates a folder, nested under whatever's currently selected in the tree.
- A show's right-click context menu (or Menu/Shift+F10) offers **Refresh Feed** (check for new episodes now), **Pause/Resume Downloads for This Podcast** (keeps the show, its episodes, and any downloads in your library, but stops fetching or downloading anything new until you resume it), and **Unsubscribe**.
- **Unsubscribe** also works with the **Delete** key on a selected show. What happens to that show's downloaded files depends on **Podcast Settings...** (below): ask each time, always delete them, or never delete them.

#### Podcast Settings

The **Podcast Settings...** button opens the global defaults every newly subscribed show starts with: default playback mode (download or stream), default retention, default speed, a default download location, and the delete-on-unsubscribe policy used above. Any individual podcast can still override any of these from its own context menu — these are only where a new subscription begins.

#### Downloading episodes

Select an episode and press **Download**, or use its context menu. Downloads run on their own dedicated background thread, so a large backlog never slows down AI calls, transcription, or anything else QUILL is doing in the background.

Pausing a download is two separate controls, not one setting doing two jobs:

- **Pause All Downloads** / **Resume All Downloads** (from the tray menu, the status bar's Podcasts cell, or the Podcasts dialog) stops the queue from *starting* anything new. Anything already mid-transfer keeps running to completion.
- Pausing **one specific episode** (its context menu, or the **Pause Download** button) halts that transfer immediately, wherever it is. Resuming it later continues from the exact byte it left off, rather than starting over.

**Retention** — what happens to a downloaded file over time — is a setting per podcast, or a global default: keep every episode, keep only the most recent few, or delete a file automatically once you finish listening to it.

#### Playing an episode

Select an episode and press **Play/Pause**, double-click it, or use its context menu. Playing a different episode always replaces whatever was playing — QUILL never plays two things at once, the same rule Internet Radio follows. Closing the Podcasts dialog never stops playback.

Your position within an episode is saved automatically, so returning to it later — even from a different session — resumes exactly where you stopped. That position is stored the same way QUILL Sync already carries your settings between machines, so it travels with you if you sync your data folder.

A **Speed** control on the Podcasts dialog's player row sets playback rate for the selected podcast, from 0.75x to 2.0x, remembered the next time you open that show.

#### Streaming an episode, and keeping one

A streamed episode is a fully capable episode. While one plays, Quill Cast also saves its audio, which is what makes three things work that used to need a download first:

- **A dropped connection is no longer an interruption.** The audio you were about to hear has almost always already arrived, so playback simply continues from it instead of going silent and re-buffering.
- **Chapters can be found in it.** **Find Chapters in This Episode** scans the audio, which it can only do when there is audio to scan.
- **Keeping it costs nothing.** **Episode > Keep This Episode** turns what you are streaming into a permanent download. If the audio is already here, that is a move, not a second download of the same bytes — nothing is fetched and it is instant. If it isn't (you pressed play a moment ago, or you turned this off for this show), it falls back to an ordinary download.

None of this is announced while it happens, and none of it appears in Downloads: it is not a download, it is removed automatically, and the episode you are listening to is never the one removed. **Podcast Settings...** offers **Keep streamed episodes ready while they play** (on by default) and the space it may use between them (1024 MB by default, 0 for no limit); a single podcast can turn it off from **Settings for This Podcast**. The Downloads dialog says how much streamed audio is currently held, separately from your downloads, so the two figures can never be confused.

#### Chapters

If an episode carries Podcasting 2.0 chapter data, its **Chapters...** button is enabled. Press it to see a list of chapter markers by name and timestamp; select one and press **Jump To Chapter** to go straight there — this works whether or not that episode is already playing. **Podcasts: Next Chapter** and **Podcasts: Previous Chapter**, in the Command Palette, jump between chapter boundaries in whatever episode is currently playing, from anywhere in QUILL.

#### Sound Enhancements

**Episode > Sound Enhancements...** applies live, on top of whatever is playing: a three-band equalizer (Bass, Mid, Treble sliders, -12 to +12 dB each) plus a "Quick preset" shortcut (Flat, Bass Boost, Voice Clarity, Podcast) that sets all three at once, a compressor ("Even Out Volume"), and **Smart Speed** (trims silence between words and sentences, distinct from the one-time leading/trailing silence trim Downloads can already do to the saved file — Smart Speed is reversible and live, on any episode, any time). All of it needs FFmpeg; if it's missing, playback continues unfiltered and QUILL tells you why. Turning anything on or off, or scrubbing the seek bar while enhanced, briefly reconnects — QUILL restarts the filter at your exact position, so you never lose your place, and pausing/resuming works normally throughout.

Every setting here is **per-podcast**: open Sound Enhancements while an episode is playing to set that show's own sound, or with nothing playing to set the shared default every other show follows.

#### Skip Forward, Skip Back, and auto-skip intro/outro

**Episode > Skip Forward** and **Skip Back** jump the current episode by a configurable number of seconds (30 forward, 15 back, by default) — different from Next/Previous Chapter, which jump to the nearest chapter boundary instead of a fixed distance. **Episode > Skip Settings...** edits how far each jumps: open it while an episode is playing to set that show's own skip distance, or with nothing playing to set the shared default.

The same dialog also offers, only when a podcast is loaded, **auto-skip intro** and **auto-skip outro** (0 = off, per podcast only — a global "skip N seconds of every show" default isn't something anyone wants). Auto-skip intro jumps forward that many seconds automatically the moment an episode starts fresh — never when resuming a checkpointed position, so you never lose your place. Auto-skip outro ends the episode that many seconds before its own true end, exactly as if it had finished naturally: auto-advance to the next queued episode, delete-after-play, and everything else that happens when an episode finishes still happens.

#### Sorting and finding what's unheard

**Sort episodes**, above the episode list, offers newest first, oldest first, title A-Z, longest first, shortest first, or unplayed first. **Sort shows**, above the folder tree, offers title A-Z, most unheard first, or recently updated first. Every folder and show name in the tree also shows its own unheard-episode count in parentheses, so you can see where you're behind without opening each show.

#### Show notes

An episode's right-click context menu includes **View Show Notes...**, which opens its description either as **Plain text** (HTML stripped out, real paragraph line breaks so a screen reader's line-by-line navigation moves by line rather than word-by-word through one wrapped line, and links written as `link text (https://...)`) or as **Rich text** (formatted, with any images removed so opening show notes can never trigger a network image fetch QUILL didn't audit). **Send to Editor**, in the same dialog, or **Send Show Notes to Editor** on the episode's context menu, opens the plain-text version as a new QUILL document.

#### Controlling playback without opening a dialog

- **The status bar.** A **Podcasts** cell appears the first time you play an episode (hidden until then). Press Enter on it, or click it, to play or pause. Its context menu adds Stop and Pause/Resume All Downloads.
- **The system tray.** Minimize QUILL to the tray and its right-click menu carries the same Play/Pause, Stop, and download-pause controls.
- **Keyboard shortcuts.** With QUILL focused, **Ctrl+Shift+Grave** (the QUILL Key), then **8**, toggles play/pause; then **7** stops. Like every QUILL Key chord, these are remappable in **Preferences > Keyboard Shortcuts**.

#### Rich context menus

Right-click an episode (or open its context menu from the keyboard) for: Play/Pause, Stop, Download, Pause/Resume Download, Remove Downloaded Copy, Mark as Played/Unplayed, Copy Episode Link, View Show Notes..., and Send Show Notes to Editor. Right-click a show in the tree for: Refresh Feed, Pause/Resume This Podcast's Downloads, and Unsubscribe. Right-click a folder for: New Folder.

#### The pinned views: Favorites, New Episodes, Continue Listening, and the Inbox

The top of the Podcast Manager's folder tree carries four pinned views, above your own folders, each with a live count:

- **Favorites** — every show you've marked as a favorite (right-click a show > **Add to Favorites**), all episodes together.
- **New Episodes** — every unplayed episode across every subscription, so "what's new" is one selection away.
- **Continue Listening** — every episode you're partway through, because QUILL remembers your position in each one.
- **Inbox** — a personal triage space, described next.

In any pinned view, each row carries both the episode and show name, so cross-show lists stay unambiguous.

#### The Inbox: organize episodes, not shows

The Inbox organizes *episodes*, cutting across your library folders entirely. Right-click a show and choose **Route New Episodes to Inbox**: its unplayed episodes now appear in the Inbox view, regardless of where the show lives in your folder tree. Inside the Inbox you can create your own nested folders and file episodes into them: right-click an episode > **File to Inbox Folder...** opens the same searchable folder picker used elsewhere. The first time you file an episode from a given show, QUILL remembers that folder and auto-files that show's future episodes there — the announcement tells you so — and **Forget Remembered Inbox Folder** (on the show's menu) reverts to manual filing. Deleting an Inbox folder only moves its episodes up a level; Inbox actions never delete an episode. The Inbox is deliberately excluded from OPML in both directions: it's your local curation, not part of the subscription list.

#### The Play Queue

Any episode's right-click menu offers **Play Next** (front of the queue) and **Add to Queue** (back). When an episode finishes, the queue's next episode starts automatically — including across different shows. The **Play Queue...** button opens the queue itself: Enter or **Play Now** plays the selected item immediately, **Move Up/Down** nudges one slot, and for long moves, **Mark for Move** then **Move Marked Above/Below** places the marked item exactly where you want it relative to the selection — the same accessible reordering pattern as Interactive Rebase's commit list. Queued episodes that disappear (an unsubscribed show, a pruned episode) simply skip; nothing crashes. The queue survives restarts.

#### Playlists

Below the Play Queue in the Podcast Manager's tree sits **Playlists** — saved, named episode lists, distinct from the transient Play Queue (which empties as it plays) and the four fixed pinned views (which you can't customize). Right-click **Playlists** for two kinds:

- **New Playlist...** creates a manually curated list. Build it from any episode's context menu: **Add to Playlist...** picks an existing playlist (or lets you create one on the spot) and appends that episode. Order is exactly how you added things; a playlist keeps working even if you later unsubscribe from one of its shows or an episode disappears — that one entry just drops out.
- **New Smart Playlist...** creates a rule-based list that re-resolves live every time you open it — the same idea as New Episodes or Continue Listening, but with rules you set: which shows (leave none checked for every show), episode status (any, unplayed, in progress, played), how recently published, a minimum and maximum length, and how to sort the result. **Edit Rules...** on any Smart Playlist's context menu reopens the same dialog to change them later.

Selecting a playlist in the tree fills the episode list exactly like a pinned view does, with each row's episode and show name both visible. **Rename Playlist...** (also F2) and **Delete Playlist...** round out the context menu; deleting a playlist never deletes or unsubscribes anything, it only forgets the saved list itself.

#### Filters and Search Everywhere

Above the manager's tree: an **Episodes** filter (All, Unplayed, Played, Downloaded, Not downloaded), a **Shows** filter (All, Favorites only, Has unplayed), and **Search Everywhere...** — one search across every subscription, every episode, your episode notes, and every transcript you've already fetched (never a network call), grouped by type. Enter on a result jumps the manager straight to it.

#### Transcripts

When a feed provides an episode transcript (Podcasting 2.0), the episode's right-click menu offers **Save Transcript As...** and **Open Transcript in Editor** — the transcript arrives as plain readable text (VTT/SRT/JSON formats handled), and once fetched it's cached locally so Search Everywhere can search it and reopening is instant.

#### About This Episode

A podcast feed can carry a good deal more than a title and an audio file, and most of it was being downloaded and discarded. **About This Episode...** (QUILL Cast's Episode menu, the command palette, or any episode's right-click menu in the Manager) opens it as tabs, and a tab is only there when it has something in it:

- **People** — who is on this episode, and who makes the podcast. Each row reads as a sentence ("Bob Brown, guest (this episode)"), and Enter opens the publisher's link where there is one.
- **Highlights** — the moments the podcast marked as worth hearing, with when each starts and how long it runs, in words. These also appear in the chapter list, where Enter plays from one.
- **Live** — some podcasts carry a live stream inside their feed. If one is on the air, Enter plays it through the ordinary transport, so pause and volume are the same keys as everywhere else.
- **Other Audio** — a second version of the same episode, usually a smaller one for a slow or metered connection.
- **Recommended** — the podcasts this show recommends. Subscribing here is a real subscribe: the show arrives with its proper name, artwork and episodes.
- **Support** — where the podcast asked to be supported. QUILL opens the page in your browser and takes no further part. Nothing in QUILL costs money.
- **Place** — where the episode is about, as text.

The command speaks a one-line summary before the window opens, so if all you wanted was to know whether there was anything, you never have to open it. Where a podcast published none of it, the window still opens and says so. The button names what it will do — *Open in Browser*, *Play*, *Subscribe to This Podcast* — and reads *Nothing to Open*, disabled, on a row with nothing to do.

#### Episode notes

**Podcasts: Add Episode Note...** (command palette, or QUILL Cast's Episode menu) saves a timestamped note on whatever is playing, at the current position. An episode's right-click menu > **Episode Notes...** lists its notes; Enter on one jumps playback to that moment — starting the episode first if it isn't playing.

#### Local podcasts and watched folders

**Podcasts: Add Local Podcast...** turns your own audio files into a show — one episode per file, titles guessed from filenames. Local shows live *outside* your synced data folder by design, so pointing QUILL Sync at a cloud folder never tries to sync gigabytes of audio. Give a local show a **watched folder** and **Scan Watched Folders** picks up any new audio files dropped there as new episodes. Local shows never appear in OPML export.

#### ACB Media Podcasts, in one command

**Podcasts: Subscribe to ACB Media Podcasts** fetches ACB's live podcast directory and subscribes to all of it, inside its own "ACB Media Podcasts" folder. It's idempotent — run it again later and only genuinely new shows are added — and every arriving show is set to stream (not download), so one command never queues three dozen shows' downloads.

#### Always Sync, and downloaded-audio processing

Podcast Settings gains three per-show-overridable switches. **Always sync the full catalog**: beyond the routine "what's new" refresh, a download-mode show backfills and downloads every episode the live feed still offers — and because backfilling a catalog while keep-last-N retention prunes it would fight itself, ticking it nudges retention to keep-all (announced, never silent). **Auto-trim silence** and **Normalize loudness** process each finished download using the same ffmpeg passes the Audio Studio's audiobook builder uses. And for quiet audio right now, the manager's **volume boost** control (1.5x/2x/3x) raises playback gain live without touching your saved volume — the Sleep Timer still restores the true, unboosted level.

#### What's not in Podcasts

No video podcasts — QUILL plays audio only, on every platform, and that is a promise rather than a gap.

## User guide: the Quill Cast standalone app

_Moved from the user guide's `## Quill Radio and QUILL Cast: the standalone apps`
section. The Quill Radio half stayed in the public user guide (Radio is a public
1.0 app); everything below is the Cast half of that shared prose._

You don't have to open the full QUILL editor to listen. **QUILL Cast** runs
Podcasts as a small standalone app -- its own window, its own menu bar, its own
system tray icon.

It is the same feature, not a copy: the app runs the exact same code QUILL itself
uses, and reads the same settings and podcast subscriptions from the same place
on disk. A show you subscribe to in QUILL Cast is subscribed everywhere.
Everything described in the Podcasts chapter above -- the Podcast Manager, OPML
import/export, downloads with pause/resume, chapter navigation -- works
identically here.

**Starting the app.** On an installed QUILL, QUILL Cast is in the Start Menu next
to QUILL itself, and the installer offers an optional desktop icon (a checkbox
during setup; unchecked by default so your desktop stays yours). From a source
checkout or the portable build, use `run-quill-cast.bat`, or
`python -m quill.apps.podcasts`.

**Everything is keyboard-first.** The app opens on a real main panel, not an
empty window: focus lands on the app's most important list the moment it opens.

- **QUILL Cast** — focus starts in your **Subscribed shows** list: press **Enter** on a show to open the full Podcast Manager, where all episode-level work happens. Tab reaches Open Manager, Add Podcast, Play/Pause, and Stop buttons, with the live now-playing line above. Menus: **Subscriptions** (Open Podcast Manager with Ctrl+M, Add Podcast, Import/Export OPML, Podcast Settings), **Episode** (a live now-playing line, Play/Pause, Stop, Next/Previous Chapter), **Downloads** (Pause All / Resume All), and **Help**. One difference from inside QUILL: "Send Show Notes to Editor" copies the notes to the clipboard instead — there is no editor buffer standalone — and announces that it did.

The app puts an icon in the system tray with the same podcast controls QUILL's
own tray icon offers, plus **Show** (double-click also works) and **Exit**. And
when you decide you want the full editor after all, **Help > Open in Quill**
launches it.

The app respects Safe Mode (`QUILL_SAFE_MODE=1`) and skips the tray icon on
macOS, where the system has no equivalent notification-area icon (the same rule
QUILL itself follows).

## User guide: background podcast-feed checks

_Moved from the user guide's "Background checks: how often, how loud, how urgent"
section, which otherwise stays public (it also covers the watched folder, the
weather, and GitHub)._

One monitor is new: **Check podcast feeds in the background**. Until now, podcast feeds were only read when you asked for a refresh. Turn this on and Quill checks your subscriptions on your chosen cadence and tells you what arrived. It is off by default, it only reads the feeds (nothing is downloaded unless your show settings already say to), and it never runs in Safe Mode.

## User guide: global hotkeys

_Moved from the user guide's "Global Hotkeys (Tools > Global Hotkeys...)" list of
the commands that can be bound system-wide. The remaining rows (Radio, sticky
notes, Mastodon, show/hide QUILL) stay public._

- Podcasts: Play/Pause, Stop

## User guide: sound events

_Moved from the user guide's "The companion apps have their own voice" bullet
under sound notifications and earcons, which otherwise stays public for Quill
Radio and Quill Weather._

Cast marks downloads beginning, each episode landing on disk, and an episode
reaching its end. Each is a **Sound Event** you can turn off individually, and
each fires on a real change of state: a forty-episode download batch says
"downloading" once.

## User guide: sleep timer (the Podcasts half)

_Moved from the user guide's `## Sleep Timer` section, which stays public for
Internet Radio._

**Tools > Media > Sleep Timer...** covers Podcasts as well as Internet Radio from
one place, since it isn't specific to either. Over the final 20 seconds,
whichever of Radio or Podcasts is currently playing fades gently down rather than
cutting off abruptly, then stops; your volume is set back to what it was before
the fade started. Since Radio and Podcasts are independent players, the timer
fades and stops whichever of the two is actually active.

---

## Part 2 -- relocated PRD material

_Moved from `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`.
Heading levels are two deeper than in the source; wording is otherwise unchanged
except where a sentence described both a public app and a gated one._

## PRD 5.84g Podcasts (Phase 1-2, shipped)

_The PRD keeps a stub at 5.84g pointing here, so every existing `5.84g`
cross-reference in the code and the docs still resolves._

### 5.84g Podcasts (Phase 1-2, shipped)

**Goal.** Subscribe to, organize, download, and play podcasts inside QUILL,
sharing Internet Radio's (§5.84f) proven "one player that outlives any
dialog" architecture rather than inventing a second one. Covers Phase 1 of
the original 5-phase plan (discovery, subscriptions,
nested folders, OPML, two-control downloads, retention, playback with
per-show speed and resume position) plus chapters, sorting, and rich
context menus pulled forward from Phase 3. Transcript UI, the Inbox, the
Play Queue, and local (imported-file) podcasts remain later phases in that
same document.

**Data model (`quill/core/podcasts/models.py`).** `PodcastShow` (one per
subscription, or one `is_local` show for a later phase) owns a flat list of
`PodcastEpisode` and an optional `PodcastSettings` override; `PodcastFolder`
is a plain adjacency-list node (`parent_folder_id`), letting a show nest
arbitrarily deep. `PodcastEpisode` carries `chapters_url`/`transcript_url`/
`transcript_type` today as forward schema the feed reader already populates,
even though Phase 1 has no UI that reads them yet — landing the on-disk
shape now means the later chapters/transcript phase needs no migration.
`position_ms` is the resume-position field the plan's sync design (§5.84f's
persistence note) already anticipated.

**Discovery and subscription.** `core/podcasts/itunes_search.py` queries
Apple's free, keyless iTunes Search API — the same starting point FastPlay
uses — for `search_podcasts()`. `core/podcasts/feed_reader.py` is a
deliberate two-step design: QUILL fetches feed bytes itself
(`_fetch_feed_bytes`, the one reviewed egress site, HTTPS-only, optional
HTTP Basic auth for private feeds sent preemptively), then hands those bytes
to `feedparser` for parsing only — never letting `feedparser`'s own fetch
path make the network call, which would move it outside QUILL's audited
egress surface. Podcasting 2.0's `<podcast:chapters>`/`<podcast:transcript>`
tags aren't reliably exposed by `feedparser` across versions, so those two
are extracted with a tolerant regex pass scoped per-`<item>` fragment as a
fallback that doesn't depend on guessing `feedparser`'s internal key
mapping. **The rest of the namespace is read the same way**
(`core/podcasts/namespace_tags.py`): `podcast:person`, `podcast:soundbite`,
`podcast:liveItem`, `podcast:podroll`, `podcast:funding`,
`podcast:location` and alternate enclosures, for the same reason plus one
more -- a second full XML parse of every feed on every refresh is real cost
across a large library, and each of these is a shallow attribute grab. Every
parser is tolerant: a malformed tag yields nothing rather than raising,
because one bad tag must never cost somebody their whole feed. The channel
half is read from the text *before the first `<item>`*, so an episode's
guests are never credited to the podcast itself; live items are looked for
across the whole feed, because publishers write them among the episodes.
Tags persist with the episode and the show and **only when non-empty**, so a
library of feeds that publish none of this pays nothing for the feature
existing, and `merge_episodes` never lets an empty replacement erase what a
feed already said -- that is far more often a partial feed than a
retraction. `core/podcasts/subscriptions.py`'s `PodcastLibrary` is the one
atomic-JSON store (shows, folders, global settings); `merge_episodes()`
refreshes a known episode's feed-supplied metadata but never drops one just
because a refreshed feed no longer lists it, and never resets its local
state (played, position, downloaded file, mode override) — an old episode
scrolling off a feed's live listing must not erase what you already did
with it.

**OPML (`core/podcasts/opml.py`).** Export walks the folder tree into nested
`<outline>` elements (local shows excluded — they have no feed URL to
export); import reconstructs that same tree from the nesting and reuses
`PodcastLibrary.add_show`'s existing duplicate-feed-URL detection, so
re-importing a list you already have adds nothing twice. Untrusted OPML is
parsed through `quill.core.safe_xml` (entity-expansion attacks disabled),
never the bare stdlib parser; exporting uses plain `ElementTree`
construction, which is not a parsing-of-untrusted-input operation.

**Downloads (`core/podcasts/download_queue.py`).** One dedicated worker
thread per process (not the shared `QuillTaskManager` pool), so a backlog of
podcast downloads never competes with AI calls or transcription for a pool
slot. Two independent pause controls, matching the plan's explicit
requirement that this not be one setting wearing two hats:
`pause_all`/`resume_all` stop the worker from *starting* new transfers,
letting anything mid-transfer finish; `pause_item`/`resume_item` halt one
specific transfer immediately via a per-item `threading.Event`, checked
between each bounded chunk read so pause takes effect within a chunk, not
only between whole-file attempts. Resuming reads the partial file's size and
sends an HTTP `Range` request, falling back to a clean restart when the
server doesn't honor it. `core/podcasts/retention.py` applies
`keep_last_n` pruning after every completed download and
`delete_after_play` after every finished episode — pure functions, testable
without a real download or a real file.

**Playback (`quill/ui/podcasts/player_controller.py`).** One
`PodcastPlayerController`, owned by `MainFrame` for the process's lifetime —
the exact same shape as `RadioPlayerController` (§5.84f), including the
"every dialog drives the shared controller, none of them own it" rule that
makes closing the Podcasts dialog never stop playback, and makes starting a
new episode always replace whatever was playing rather than layering two
streams. Unlike Radio, podcast episodes are bounded files (even mid-stream,
the enclosure reports a real `Content-Length`), so this uses Audio Studio's
normal `create_engine()` (mpv-preferred, `WxMediaEngine` fallback) rather
than being restricted to Radio's wx.media-only backend. Per-show playback
speed (`PodcastSettings.speed`, 0.75x-2.0x in the UI) is applied via
`set_rate()` once the engine reports loaded, not before — some backends
only accept a rate change after a file is open. Finishing an episode marks
it played and applies `delete_after_play` before the state resets.

**Surfaces.** `Tools > Media > Podcasts...` (Podcast Manager: folder tree +
episode list, Add Podcast/New Folder/Import/Export OPML, Download/Pause
Download/Remove Download, Unsubscribe) registers eight commands in
`CommandRegistry` (`feature_id="core.podcasts"`), command-palette visible.
Rich context menus close the plan's explicit "even playback and pause, etc."
requirement: the episode list's menu covers Play/Pause, Stop, Download,
Pause/Resume Download, Remove Downloaded Copy, Mark as Played/Unplayed, and
Copy Episode Link; the folder tree's menu covers Refresh Feed, Pause/Resume
Downloads for This Podcast (keeps the show and its episodes in the library
while stopping new fetches — the plan's "mark a podcast to not download but
keep in the library" ask), Unsubscribe, and New Folder. A `podcast_player`
status-bar cell (auto-surfaces on first play, same pattern as Radio's cell)
and a system-tray section (Play/Pause, Stop, Pause/Resume All Downloads)
both drive the shared controller. Two QUILL-key chords
(`Ctrl+Shift+Grave, 8/7` for play-pause/stop) sit adjacent to, not
overlapping, Radio's `N/0/9`.

**Chapters (`core/podcasts/chapters.py`).** Fetches and parses the
Podcasting 2.0 JSON chapters format the feed's `<podcast:chapters>` tag
points at, the same fetch-then-parse split `feed_reader.py` uses (one
reviewed egress site, pure parsing). `chapter_at_position()`/
`next_chapter()`/`previous_chapter()` are pure functions over a sorted
chapter list, driving both the Chapters dialog's jump action and the
global `podcasts.next_chapter`/`podcasts.previous_chapter` commands.
Chapters for the currently-playing episode are fetched once per episode
change (tracked by a `(show_id, episode_guid)` key, not re-fetched on every
play/pause toggle) via a background `_task_manager.submit()` call, never
blocking playback.

**Sorting and unheard counts (`core/podcasts/sorting.py`).** Pure
`sort_episodes()`/`sort_shows()` functions — six episode sort modes
(newest/oldest/title/duration-longest/duration-shortest/unplayed-first) and
three show sort modes (title/most-unheard-first/recently-updated-first),
each with a sensible fallback for an unrecognized mode rather than raising.
Publish dates are parsed via `email.utils.parsedate_to_datetime` (the
typical RSS `pubDate` format), falling back to the oldest possible sort
position for an unparseable or missing date rather than erroring. Unheard
counts are computed recursively per folder (a folder's count includes every
subfolder's shows) and per show, rendered as `"{name} (N unheard)"` in the
tree only when non-zero.

**Show notes (`core/podcasts/show_notes.py`).** `html_to_plain_text()`
converts an episode's HTML description to plain text with real paragraph
line breaks (block-level tag ends become newlines) so a screen reader's
line-by-line navigation moves by line, not by wrapping a single giant line
word by word — the specific, named failure mode this was built to avoid.
Links become `text (url)` rather than being silently dropped.
`strip_html_images()` removes every `<img>` tag before any HTML is handed
to the "rich" `wx.html.HtmlWindow` view: an HTML renderer that itself
fetches `<img src="...">` would be a silent, unreviewed network egress site
invisible to a static audit of QUILL's own `urlopen` call sites, so images
are removed rather than rendered. **Send Show Notes to Editor** reuses the
existing `_power_tools_open_text_in_new_buffer()` new-document path (the
same one AI transcribe/translate use).

**Global settings and delete-on-remove (`PodcastSettings.
delete_files_on_remove`).** A new `"ask"`/`"always"`/`"never"` field,
consulted in the Unsubscribe flow via `effective_settings()` (so a show's
own override wins over the library global): `"ask"` prompts a second
confirmation naming the downloaded-episode count only when there are any to
delete; `"always"`/`"never"` act without asking. `PodcastLibrary.settings`
(playback mode, retention, speed, download root) existed in the data model
since Phase 1 but had no UI until this pass's Podcast Settings dialog.

**Non-goals (deliberate).** Video podcasts, in any form — audio only,
matching every other QUILL playback surface; this was an explicit,
repeated constraint during planning, not an oversight. TuneIn/iHeartRadio
apply to Radio, not here; podcast feeds are an open standard (RSS/Atom),
so there is no equivalent commercial-API question for this feature.

**Planned next (Phase 3+), not yet built.** Transcript viewing/export/
QUILL-transcription (the feed already parses the URL; §5.84b's
transcription engines are the intended target), a separate Inbox view with
its own folder tree, a cross-show reorderable Play Queue, local
(imported-file) podcasts and watched folders, virtual views
(Favorites/New Episodes/Continue Listening), and rich filtering (including
Search Everywhere) — all shipped; see the Phase 4 block below for the full
plan.

**Value.** Closes the other half of the "why QUILL and not a dedicated
player" answer §5.84f opened: a downloaded episode chains directly into the
Listening Companion (§5.84b) for transcribe-and-summarize, something no
standalone podcast app offers, and the same QUILL Sync story that already
carries settings between machines now carries listening position too.

#### Phase 4 (shipped): views, Inbox, queue, transcripts, notes, local, sync

Everything the original phased plan deferred, now shipped. Every core is
wx-free and unit-tested; the manager UI additions live in
``quill/ui/podcasts/manager_phase4.py`` (a mixin, per the manager's CQ-1
decomposition note) and ``play_queue_dialog.py``; standalone QUILL Cast
(§5.89e) inherits all of it and adds matching menu items.

- **Pinned virtual views (P4-1).** Favorites / New Episodes / Continue
  Listening / Inbox sit above the folder tree with live counts
  (``virtual_views.py``; Favorites via ``PodcastShow.is_favorite``, toggled
  from the show context menu). Cross-show rows always carry the show name.
- **The Inbox (P4-2, ``inbox.py``).** An episode-level curation layer:
  ``route_to_inbox`` shows surface unplayed episodes in the Inbox regardless
  of library folder; a second, independent nested folder tree
  (``PodcastLibrary.inbox_folders``) files episodes
  (``inbox_assignments``); the first manual filing per show is remembered
  (``inbox_default_folder_id``, announced) with Forget to revert. Folder
  deletion only promotes contents; Inbox actions never delete an episode;
  the whole layer is excluded from OPML both directions.
- **Play Queue (P4-3, ``queue.py`` + ``PlayQueueDialog``).** Cross-show
  ordered queue persisted on the library; Play Next / Add to Queue on any
  episode; auto-advance on natural finish via ``pop_next_playable`` (stale
  slots self-heal); reordering is nudge (Move Up/Down) plus mark-and-move
  (Move Marked Above/Below) -- the Interactive Rebase pattern.
- **Search Everywhere + filters (P4-4, ``filtering.py``).** One query over
  shows, episodes, episode notes, and cached transcripts (never a network
  fetch), grouped by type with jump-to-result; episode-state and show
  filters narrow the manager live.
- **Transcripts (P4-5, ``transcripts.py``).** Feed-provided Podcasting 2.0
  transcripts (VTT/SRT/JSON parsed to plain text) save to a file or open in
  the editor; fetched transcripts cache locally (searchable, instant
  reopen).
- **The rest of the Podcasting 2.0 namespace (``namespace_tags.py``,
  ``extras.py``).** People, soundbites, live items, podroll, funding,
  location and alternate enclosures, surfaced through **About This
  Episode...** (``ui/podcasts/episode_extras_dialog.py``, a ``wx.Notebook``
  of ``wx.ListBox`` pages; ``ui/podcasts/extras_command.py`` for the three
  actions a row can take: open a link, play a stream, subscribe to a feed).
  A tab exists only when it has something in it; the one-line summary is
  spoken before the window opens; the window still opens and says so when a
  podcast published none of it, because *publishes nothing* and *cannot be
  read* are different facts a greyed-out item cannot distinguish. The action
  button is named from the highlighted row and reads *Nothing to Open*,
  disabled, where there is nothing to do. Subscribing from a podroll goes
  through the same path Add by Feed URL uses, on the task manager and
  refused in Safe Mode; funding opens in the browser and is processed no
  further, so listening stays free. Value-for-value / cryptocurrency
  streaming is out of scope, deliberately.
- **Soundbites as an authored chapter tier (``chapter_scoring.py``,
  ``chapter_sources.py``, ``chapter_cascade.py``).** A soundbite is a
  chapter marker in all but name -- a person chose the moment and titled it
  -- so ``SOURCE_SOUNDBITES`` joins the authored tiers (base confidence
  0.85, inside ``is_authored``) as the **last** of them. Last, because a
  highlight is not a partition: two marks in an hour answers *what is the
  good bit* completely and *how is this laid out* barely at all. They win
  only where nothing better was published; each chapter keeps the
  soundbite's own ``end_ms`` rather than running on to the next mark; and
  the source is labelled *Moments this podcast marked*. The floor is one
  mark rather than two -- a single marked moment is still a place worth
  jumping to.
- **Episode notes (P4-6, ``episode_notes.py``).** Timestamped notes on the
  playing episode; the notes dialog jumps playback to a note's moment.
- **Local podcasts + watched folders (P4-7, ``local_import.py``).** Audio
  files become an ``is_local`` show (one episode per file); stored under
  ``~/.quill-local/podcasts`` -- outside the syncable data directory *by
  construction*, per the sync-safety requirement. A per-show
  ``watched_folder`` turns dropped files into episodes on scan. Never
  exported to OPML.
- **ACB Media directory (P4-8, ``acb_media_podcasts.py``).** One idempotent
  command subscribes the live ACB directory into its own folder, every
  arrival stream-only (``import_opml``'s ``stream_only``/``into_folder``).
- **Always Sync (P4-9).** ``always_sync_full_catalog`` (per-show
  overridable): refresh backfills the catalog and queues downloads for
  download-mode shows; the settings checkbox nudges retention to keep-all
  (announced) since backfill fights keep-last-N.
- **Download processing + volume boost (P4-10, ``audio_processing.py``).**
  Optional auto-trim-silence and loudness-normalization on each finished
  download (the audiobook builder's ffmpeg passes, off-thread);
  ``set_volume_boost`` (0.5x-3.0x clamp) scales live gain only --
  ``volume_percent`` stays unboosted so the Sleep Timer's restore is honest.
- **Position checkpoints (P4-11).** ``on_position_checkpoint`` fires with
  the outgoing episode's position at pause/stop/switch/shutdown and the
  mixin persists it -- the write half of resume, which previously only read.
- **Status page rows (P4-12, ``status_report.py``).** Podcast library
  summary rows and download-task rows (with started/finished timestamps)
  for the Help Status page.

#### Phase 5 (shipped): Sound Enhancements + Smart Speed

Shares Radio's ``core/audio_enhance.py`` (§5.84f) rather than duplicating
it, with the one real wrinkle Radio doesn't have: episodes support seeking
and a duration/scrub bar, which a live one-way ffmpeg relay has neither of
natively. Full parity was built, not a degraded no-seek mode.

- **Three-band EQ + compressor.** Same as Radio (§5.84f): Bass/Mid/Treble
  sliders plus a compressor, applied live via the shared relay. Off by
  default; a "Quick preset" shortcut still sets all three sliders at once
  from the four original named presets.
- **Smart Speed (podcasts only).** A ``silenceremove`` filter trims silence
  anywhere in the audio (not just leading/trailing), for the gaps between
  sentences a spoken-word episode is full of -- reversible and live, not the
  one-time, permanent leading/trailing trim ``audio_processing.py`` (P4-10)
  already does to a saved download. Not exposed for Radio: a live stream has
  no fixed content to trim ahead of time, and "silence" in music is often
  intentional.
- **Seek while enhanced (``player_controller.py``).** There is no way to
  seek within an already-running relay, so scrubbing restarts it with an
  ffmpeg ``-ss`` offset -- an async reload, not the engine's normal instant
  seek. ``_pending_play_after_load`` carries play/pause intent through that
  reload so scrubbing or toggling enhancement mid-episode never forces a
  paused episode to resume.
- **Duration (``probe_source_duration_ms``).** The relay's own MP3 output
  never declares a length for the engine to compute a scrub bar from, so
  duration comes from an independent ``ffprobe`` call instead.

#### Phase 6 (shipped): Download All Episodes / Remove All Episodes

Two new show-level context-menu actions, implemented once in
``quill/ui/podcasts/show_actions.py`` and called from both surfaces that act
on a subscribed show (the Podcast Manager dialog and QUILL Cast's own
library tree) rather than duplicating the logic a third time.

- **Download All Episodes.** Queues every not-yet-downloaded,
  not-already-queued episode of a show -- purely additive, no confirmation,
  matching the existing single-episode Download action's own behavior.
- **Remove All Episodes.** A two-step confirm mirroring Unsubscribe's shape:
  confirm the removal, then -- only if any episode has a downloaded file --
  a follow-up asking whether to also delete those files. The show stays
  subscribed (unlike Unsubscribe); a future feed refresh can repopulate its
  episode list from the feed itself. Cancels any in-flight/queued download
  for a removed episode first, so nothing is left running against a guid
  about to disappear.

#### Phase 7 (shipped): Inbox grouping + per-podcast sort for every cross-show view

The Inbox (and every other cross-show virtual view -- New Episodes,
Continue Listening, Favorites) previously rendered ``(show, episode)``
pairs in raw feed-fetch order, with the Podcast Manager's existing "Sort
episodes" control silently doing nothing outside a single show's own
episode list. Root-caused from a direct user question about whether Inbox
episodes were grouped by show or interleaved, and whether that order could
be controlled; the first shipped design (a single "Group by Show" checkbox)
was corrected mid-review into the fuller shape below once it became clear
"folder" meant a real tree, and "resettable per podcast" meant a genuine
per-show override, not a global-only toggle.

- **``PodcastSettings.episode_list_view_mode``** (global only -- a single
  show has no "grouped vs flat" shape of its own): ``"flat"`` (one stream
  sorted by the library's global sort mode across every show), ``"grouped"``
  (the pre-existing look -- pairs grouped contiguously by show, shows
  ordered by title), or ``"folders"`` (the same per-show grouping, presented
  as real expandable tree nodes instead of a flat list). Default
  ``"grouped"`` matches the pre-existing de-facto order.
- **``PodcastSettings.episode_sort_mode``**, per-show overridable the same
  way ``speed`` already was. **``core/podcasts/sorting.py::sort_pairs``**
  (pure, unit-tested): in ``"flat"`` mode every pair sorts by the one global
  mode (per-show overrides don't apply -- there's no single well-defined
  order once different shows compare by different keys); in
  ``"grouped"``/``"folders"`` mode each show's own group sorts by *that
  show's* effective mode, so one podcast can read oldest-first while
  another reads newest-first.
- **``PodcastLibrary.apply_show_override``**, the one correct way to write
  any per-show settings override: clones the currently effective settings
  (the show's own override if it has one, else the global default) via
  ``dataclasses.replace``, so setting one field never resets sibling
  overrides to class defaults. Also fixed ``_on_speed_choice``, which
  predates this and hand-cloned only 5 of the (now) 14 ``PodcastSettings``
  fields -- setting a show's playback speed silently wiped any other
  override that show already had.
- **UI (``manager_dialog.py``, ``manager_phase4.py``).** A "View cross-show
  lists as" combo box (Flat list / Grouped in list / Folders per podcast)
  and a context-aware "Sort episodes" control: it reads and writes the
  selected podcast's own override when a single show (or its Folders tree
  node) is selected, or the shared global default otherwise.
  ``_add_virtual_view_show_children`` builds the Folders mode's per-podcast
  tree nodes fresh on every ``refresh_tree()`` -- auto-generated, never
  persisted, distinct from the existing manual freeform Inbox folder tree.

#### Phase 8 (shipped): per-podcast Sound Enhancements, Skip Forward/Back, auto-skip intro/outro

A competitive pass against Downcast/Overcast/Pocket Casts/Castro surfaced two
gaps: Sound Enhancements (Phase 5, above) was global-only, and there was no
skip-by-N-seconds command at all (only absolute chapter-boundary seeks).

- **Per-podcast Sound Enhancements.** ``PodcastSettings`` gained
  ``eq_bass_db``/``eq_mid_db``/``eq_treble_db``/``compressor_enabled``/
  ``smart_speed_enabled``, per-show overridable via ``apply_show_override``
  exactly like ``episode_sort_mode`` (Phase 7). Opening Sound Enhancements
  while an episode is playing edits that show's own override; with nothing
  playing, it edits the shared default. Every ``play_episode`` call site (6,
  across the Manager, the Play Queue, Recently Played, and both standalone
  apps) resolves ``effective_settings(show)`` and passes the result through
  new optional ``bass_db``/``mid_db``/``treble_db``/``compressor_enabled``/
  ``smart_speed_enabled`` kwargs.
- **Skip Forward / Skip Back.** ``PodcastSettings.skip_forward_seconds``/
  ``skip_back_seconds`` (global default + per-show override, 30/15 by
  default) back two new commands (``podcasts.skip_forward``/``skip_back``,
  Episode-menu items, default chords) that jump the player controller's
  position by that many seconds, clamped to ``[0, length_ms]``.
- **Auto-skip intro/outro** (``auto_skip_intro_seconds``/
  ``auto_skip_outro_seconds``, per-show only -- a global "skip N seconds of
  every podcast" default isn't a thing anyone wants). Intro-skip applies
  once, only on a fresh start (``resume_ms <= 0``) -- a checkpointed
  position is never jumped past. Outro-skip is a new 1-second
  ``PodcastPlayerController`` position poll that ends the episode early
  through the exact same ``_on_finished`` path a natural end uses, so
  auto-advance and delete-after-play still fire.
- **New context-aware Skip Settings... dialog** (``skip_settings_dialog.py``)
  mirrors Sound Enhancements exactly: edits the currently-loaded show's
  override, or the shared default with the intro/outro fields hidden
  entirely when nothing is loaded (they have no meaningful global value).
- Also fixed a real bug found while touching ``PodcastSettingsDialog``:
  ``_on_save`` built a fresh ``PodcastSettings(...)`` that silently reset 7
  unedited fields (view mode, sort mode, EQ, smart speed) to class defaults
  on every save. Now ``dataclasses.replace(self._settings, **edits)``, the
  same pattern ``apply_show_override`` already uses.

#### Phase 9 (shipped): saved Playlists -- Smart (rule-based) and manual

The other half of the same competitive pass: no way to save a curated or
rule-based cross-show episode list, only the four fixed pinned views and the
transient Play Queue -- a real gap against Pocket Casts' Smart Playlists/
Filters and curated Playlists.

- **``Playlist``/``PlaylistRules``** (``models.py``, mirrors ``QueueItem``'s
  own data-class-in-``models.py``/operations-in-a-sibling-module split).
  ``kind="smart"`` resolves live against ``rules`` every time it's opened
  (which shows -- empty means every show, episode status, published-within-
  days, min/max duration, sort mode, reusing ``sorting.py``'s own sort-key
  builder so results order exactly like every other episode list in the
  app); ``kind="manual"`` is a named, ordered, persistent list of specific
  episode references (``QueueItem``s) -- the saved counterpart to the
  transient Play Queue, self-healing against a since-unsubscribed show or
  vanished episode the same way the Play Queue already does.
  ``core/podcasts/playlists.py::resolve_playlist`` is pure and fully unit
  tested.
- **``PodcastLibrary.playlists``** + find/add/remove/rename CRUD, persisted
  the same hand-rolled-dict way ``queue``/``inbox_folders`` already are.
- **Tree integration** (``manager_phase4.py``) mirrors the existing
  pinned-views/Inbox-folder pattern exactly: a "Playlists" node (context
  menu: New Smart Playlist.../New Playlist...), one child per saved
  playlist showing its live-resolved count, Edit Rules.../Rename/Delete on
  each, F2 rename support, and the episode list fills via
  ``resolve_playlist`` the same way a virtual view fills via
  ``virtual_view_pairs``.
- **New ``playlist_rules_dialog.py``** (the Smart Playlist rule editor) uses
  individual ``wx.CheckBox`` controls in a ``wx.ScrolledWindow`` for the show
  picker, not ``wx.CheckListBox`` -- caught by the banned-patterns gate
  (A11Y-SR-1: screen readers do not announce ``CheckListBox`` item checked
  state as it's navigated, only the label text).
- Episode context menu gained "Add to Playlist..." (a native
  ``wx.SingleChoiceDialog`` among existing manual playlists, or create one
  inline).

##### 5.84g.7 The playback cache -- a streamed episode is a fully capable episode

**The problem, stated as what it costs the listener.** Through 1.1.0 Cast had
two classes of episode and a listener had to know which one they were holding
before they knew which features they had. Chapters found in the audio, exact
bookmarks, dependable resume, precise seeking and any kind of analysis were all
downloaded-only, because every one of them needs a *file* and a stream is a
socket. This is not a file-management feature; it is the removal of that tier
split.

**The mechanism, which is the boring part.** While a streamed episode plays,
its bytes are also written to a managed cache
(``core/podcasts/playback_cache.py``), so the episode becomes byte-backed
without anybody asking for a download. The cache is keyed by show id and
episode guid (never by URL -- a feed that moves its enclosures must not orphan
every file), hashed rather than named after publisher-supplied text, and writes
to a ``.part`` file that is promoted to the real name with one ``os.replace``,
so no reader can ever see a half-written file under the complete name.

**What the bytes buy, which is the point.**

1. **A dropped connection stops being an interruption.** The player asks, on
   error, whether a local file already covers the position it was at
   (``PodcastPlayerController._recover_locally``) and reloads from it if so.
   The fetch runs far ahead of realtime, so it usually does. It recovers once
   per source: if the local file also fails, the error is reported rather than
   looped on.
2. **"Keep this one" costs nothing.** ``playback_cache.promote`` moves the file
   into the download folder -- a rename on the same volume -- rather than
   downloading the same bytes a second time. **Keep This Episode**
   (``podcasts.keep_episode``) falls back to an ordinary download when there is
   no complete entry, which is exactly what the listener would have done.
3. **The analysis tiers get something to analyse.** ``local_audio_path`` is the
   single resolver -- download first, then cache -- that ``chapter_sources``
   and ``chapter_inference_ui`` now ask, so the file tiers cannot tell a
   streamed episode from a downloaded one.

**Cache, never content.** Bounded (``playback_cache_cap_mb``, 1024 MB by
default), evicted least-recently-used, and losing all of it costs nothing but
bandwidth. **The episode you are listening to is never evicted** --
``evict_to_cap`` and ``clear`` both take the in-use paths and skip them, the
same instinct as ``retention.is_protected``. An unreachable cap is simply not
reached; nothing protected is taken to satisfy it.

**Its own queue.** Cache fills run on a second ``PodcastDownloadQueue`` with
``max_concurrent=1`` and no status callback. Separate from the download queue
because the episode being listened to must never wait behind a forty-episode
download batch for the bytes that make it drop-proof; silent because a cache
fill is not a download -- it never earcons, never reaches the status bar, and
never appears in the Downloads list. Starting a different episode cancels the
fill for the one you left (the ``.part`` file stays, so replaying that episode
resumes by Range rather than starting over).

**Naming.** The setting reads as reliability, not disk management: *Keep
streamed episodes ready while they play*. "Playback cache" is the internal
name, and is deliberately unremarkable -- this is something the listener should
never have to think about.

**Found while wiring this.** ``chapter_inference_ui`` read ``show.show_id``,
but ``PodcastShow`` names the field ``id`` (``show_id`` is what a *download
queue item* calls it), so Find Chapters answered "this episode cannot be
identified" for every episode and had never run. ``chapter_sources.
show_identity`` is now the one place that resolves either spelling.

## PRD 5.89e The Quill Cast standalone app

_Moved from `### 5.89e Standalone companion apps -- Quill Radio and QUILL Cast`,
which described the two apps jointly. The PRD keeps the section under the title
`5.89e Standalone companion app -- Quill Radio`; the Cast-specific goal,
architecture consequences, surfaces, and installer integration are below._

**Goal.** Podcasts are useful without the editor: someone who wants to manage a
podcast queue should not have to load all of QUILL to do it. QUILL Cast is a
small standalone executable -- its own window, its own menu bar, its own system
tray icon -- that reuses QUILL's feature code *unchanged* rather than forking it.

**Architecture.** The `PodcastsMixin` that `MainFrame` already uses only ever
touches the small, fixed host protocol `AppShellFrame` implements
(`quill/ui/app_shell.py`), so `class PodcastAppFrame(AppShellFrame,
PodcastsMixin)` gets the entire feature -- commands, dialogs, subscriptions,
downloads -- with zero changes to the mixin. Consequences that matter:

- **No fork, ever.** A bug fix or feature added to `quill/core/podcasts` or the
  shared dialogs lands in the standalone app automatically -- same modules, same
  imports.
- **One data store.** The app loads the same `core.settings`/`core.keymap` and
  reads/writes the same subscription library and download state under
  `app_data_dir()` -- what you subscribe to in QUILL Cast is subscribed in QUILL,
  with no sync layer.
- **Same accessibility contract.** Announcements route through the same
  `AnnouncementEngine`; dialogs keep their existing keyboard/naming behavior
  because they are the same dialog classes.

**Per-app surface.**

- **QUILL Cast** (`python -m quill.apps.podcasts`; `run-quill-cast.bat`).
  Menu bar: Subscriptions (Open Podcast Manager, Add Podcast, Import/Export
  OPML, Podcast Settings), Episode (now-playing line, Play/Pause, Stop,
  Next/Previous Chapter), Downloads (Pause All / Resume All), Help. Tray
  icon mirrors QUILL's podcast tray section. One behavioral override: "Send
  Show Notes to Editor" copies to the clipboard instead (there is no editor
  buffer standalone), announced as such.

**Open in Quill.** The app carries a Help > Open in Quill command that launches
the full editor as a separate process (v1: always a new process; a
focus-existing-instance IPC variant is deliberately deferred -- see
`docs/planning/apps.md`).

**Installer integration.** The Windows installer creates a Start Menu entry for
QUILL Cast alongside QUILL's own, launching it via the bundled Python runtime
(`-m quill.apps.podcasts`), with both launcher variants (bundled runtime and exe)
covered. Its desktop icon is part of the opt-in `companionicons` installer task
(unchecked by default). Defined in the `.iss` generator
(`scripts/build_windows_distribution.py`), never the generated script. For 1.0.0
these entries are gated with the app itself.

**Keyboard-first main panel.** The app opens on a real, tabbable main surface --
never a bare frame: a live now-playing line, the subscribed-shows list focused on
launch with Enter to act, and its core action buttons, every control named via
`dialog_contract.set_accessible_name`.

## PRD 5.84h Sleep Timer -- the Podcasts half

_Moved from `### 5.84h Shared media Sleep Timer, and start-at-Windows-login`,
which stays in the PRD for Internet Radio and the start-at-login setting._

The sleep timer covers Podcasts (5.84g) as well as Internet Radio (5.84f) from
one place, since duplicating it per-feature would mean two timers, two dialogs,
and no guarantee they agree on what "active" means. `SleepTimerController` takes
a `get_podcast_controller` callable rather than a direct reference, so it works
whether one, both, or neither feature is enabled. Radio and Podcasts are
independent players (nothing stops one when the other starts), so both are
faded/stopped if both happen to be active at once. `PodcastPlayerController`
gained a `volume_percent` property/tracked field for this -- Phase 1 shipped with
a `set_volume()` method but no readable state, since nothing needed to read it
back before the sleep timer did.

## PRD 35.1 The Quill Cast family entry

_Moved from `## 35. The QuillVille family` / `### 35.1 The apps`, whose inventory
now lists only the publicly released apps and points here for the gated ones._

- **Quill Cast** (`quill/apps/podcasts.py`) -- the podcast client. Not yet
  shipped; targets a clean **1.0.0**. Gated out of the public QUILL 1.0.0 build
  via `RELEASED_APPS`.
