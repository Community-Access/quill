# QUILL 1.1.0 - Release Notes (draft)

> **Working draft.** The version number is provisional and this document
> tracks the changelog's *Unreleased* section, which remains the canonical,
> fully detailed record until this release is cut. Sections below carry each
> change's own narrative opening; the dictation and platform work of
> 2026-08-17 is carried in full.

## What this release is

Everything here has landed since 1.0.0. This is a reliability pass driven entirely
by what people reported: a full disk that could lose a document, an editor that
was doing too much work between keystrokes, and three smaller things that were
already fixed in code nobody could run yet.

## The platform day: keys that fight stop fighting, settings apply now, and the gates watch the gates (2026-08-17)

A same-day execution of the ranked platform review at `polish.md` (root; its
header is the ledger). What a user feels first:

- **Six keyboard chords stopped silently fighting.** The QuillVille menu's
  "Open <app>" rows claimed **Ctrl+Alt+Shift+1–3** and Quill Radio's Sort
  Favorites claimed **4–6** — the same chords the quick-play favorites
  (`radio.play_favorite_1..10`) and QUILL's own previous-heading navigation
  already owned, so in every affected window one of each pair never fired. The
  launchers moved to **Ctrl+Alt+Shift+F1–F3** and Sort Favorites to
  **F4–F6**; quick-play and heading navigation keep the digits they were
  documented with. Found the honest way: the Favorites submenu began
  *advertising* its real bindings (below) and the strengthened gate saw the
  double claims immediately.
- **The Favorite Stations submenu finally shows its keys.** Its rows carried no
  keyboard route at all — the exact cost the menu rule exists to prevent. The
  first ten favorites now advertise their quick-play chords (following any
  rebinding), and anything past ten is a disabled readout naming the count.
  The gate that should have caught this was walking an *empty* profile; it now
  seeds favorites, so a data-driven submenu can never ship silent again.
- **Announcement, verbosity, and watch-folder settings apply immediately.**
  Three long-lived controllers snapshotted their settings at first use and
  never looked again, so braille style, dedupe hold-back, interrupt
  severities, verbosity profiles, and watch-monitor cadence quietly meant
  "after the next restart" while Preferences implied "now". All of them (and
  the model-lifecycle limits) re-derive from one seam on every settings apply
  (`announce_wiring.refresh_live_policies`), with tests pinning the wiring.
- **Whisper large-v3 is formally de-supported.** At ~3.1 GB it exceeds the
  2 GiB mirror limit, so it lived in an unexplained manual-install limbo; the
  pickers no longer offer it, while an installed copy keeps its identity, size
  estimates, and removal path. Medium and Parakeet 3 are the better answers.

Under the hood, the footing work:

- **A gate that was never wired in, now is.** GATE-40 (no raw
  `threading.Thread` in the UI layer without an audited exemption) had been
  written, documented, and unit-tested — and never dispatched, so fifteen
  unmarked thread sites accumulated while it slept. It runs in the
  banned-patterns gate now, and every site carries a specific, reviewed
  marker.
- **One scorecard over every gate** (`python -m quill.tools.platform_report`):
  all the ratchets — budgets, egress, dialogs, error codes, docs artifacts,
  inventories, and the rest — run as one accessible report. Its roster
  cross-check found **eleven more gates** nobody had listed anywhere on its
  very first run; the scorecard now reads 21 of 21.
- **The runtime inventory gate grew a portable layout** and guards
  `build_portable.py`'s tree-copy the way it guards the shared runtime
  (Quill Radio's baseline is committed; other apps adopt by writing theirs) —
  closing the remaining path of the drift class that once shipped 82 MB of
  undeclared payload.
- **A startup-import gate**: QUILL's core import measures ~83 ms because every
  heavy library loads lazily; nothing enforced that. A deterministic test now
  fails if the core import ever pulls wx, numpy, requests, or any of the
  known-heavy set — the regression is caught as a *fact*, not a flaky timing.
- **The test suite runs in half the time**: `pytest -q -n 8 --dist loadgroup`
  (8:58 → ~4–5:30, complete and zero-flake). All wx/UI tests share one worker
  by design — the Windows clipboard, global hotkeys, and screen-reader
  bridges are machine-global, and eight workers fighting over them crashed
  workers outright. Serial `pytest -q` behaves exactly as before.
- **Base runtime is Python 3.13.15 on Inno Setup 7.1**, with every installer
  now a 64-bit Setup; the ones embedding the near-identical ffmpeg/ffprobe
  pair use a 128 MB LZMA dictionary that dedupes it (−27 MB measured on Quill
  Radio — the same investigation that explained a 31 MB installer-size
  mystery and produced the inventory gates). The published site's copies of
  Quill Radio's docs are now synced mechanically at build time instead of
  rotting by hand.
- **Optional, never required:** `quill[rapidfuzz]` accelerates the dictation
  vocabulary corrector ~50–100× when installed; the stdlib implementation
  remains the behavioural contract and a parity test holds the two together.

## Dictation stops making things up (2026-08-17)

Five changes, one aim: what lands in your document is what you said — no more,
no less. Studied against the Handy project's production dictation experience
(MIT; the failure catalogue transferred almost verbatim) before a line was
written.

- **Parakeet 3, a new offline engine — and dictation prefers it once you
  install it.** NVIDIA's `parakeet-tdt-0.6b-v3` via sherpa-onnx: 25 languages,
  automatic language detection, CPU-only, no torch, ~650 MB, CC-BY-4.0,
  SHA-pinned on QUILL's own assets-v1 mirror like every model. The reason it
  outranks Whisper for dictation is structural: a transducer emits tokens only
  for audio evidence, so **it cannot invent text from silence** — the phantom
  "thank you" after a thinking pause is a Whisper-family behaviour Parakeet is
  simply incapable of. whisper.cpp remains the default (it works before any big
  download); the preference ladder (`service.preferred_dictation_provider_id`)
  promotes Parakeet only after you install its model, and an explicitly chosen
  engine always wins. Every row in Manage Speech Models now states its
  capabilities in plain words — "detects the spoken language; never invents
  text from silence" — *before* you download, not after.
- **A silence pre-pass in front of every engine** (`speech_vad.py`). Quiet
  lead-ins and tails are trimmed from the captured take before transcription
  (pure RMS, no model needed, same calibration as the Hey-QUILL turn
  detector), and an all-quiet recording short-circuits straight to the honest
  "no speech" answer — the engine is never even asked. Installing Parakeet
  upgrades the same decision to Silero VAD (the ~0.6 MB neural detector ships
  inside the model bundle), which may only ever *narrow* what the RMS tier
  found.
- **Your vocabulary now corrects every engine** (`speech/vocabulary.py`). The
  `dictation.md` profile's term list has always biased Whisper's
  `initial_prompt`; it now also drives a post-transcription fuzzy corrector —
  Soundex plus Levenshtein over 1–3-word spans, with a 25 % length gate so
  "openaigpt" can never collapse into "openai" — so engines that take no
  prompt (Parakeet) still learn your names, and "charge b" comes back
  "ChargeBee" in exactly your casing. One list, one file, both mechanisms.
- **Optional, language-honest filler removal** (`speech/fillers.py`, off by
  default). Two tiers: universal hesitations ("uh", "hmm") always qualify;
  ambiguous ones are removed only with language evidence, because "um" is a
  real word in Portuguese and German and deleting a user's words is worse than
  transcribing their hesitations. A custom list replaces both tiers; the
  toggle is `dictation_remove_fillers`.
- **The streaming contract, landed before the streaming engine**
  (`speech/streaming.py`). Live transcription, when it arrives, must be an
  append-only *committed* prefix plus a volatile *tentative* tail, and speech
  and braille announce only newly committed text, exactly once. Announcing
  repainted partials makes a screen reader speak the same words repeatedly as
  the decoder rewrites its tail; the `StreamAnnouncer` contract makes that
  structurally impossible, and survives a misbehaving provider without
  double-speaking. Adopted now, with tests, so the future streaming provider
  is built into it rather than retrofitted onto it.

All five pieces are in the shared `quill` package: QUILL's Locked Dictation
gets all of them, and QUILL Audio Studio's offline transcription sees Parakeet 3
in its engine chooser with the same honest capability labels.

## Radio browse becomes a place you can wander, and one contract underneath it

All of this lives in the shared `quill` package, so it is QUILL's as much as
Quill Radio's; the listener-facing telling of it is Quill Radio's own
`release-notes-3.0`.

*Full detail: CHANGELOG, “Radio browse becomes a place you can wander, and one contract underneath it”.*

## The described-audio picker was listing one track as three

Found by probing real videos while building Quill Radio's test plan, which is the
argument for building one. `audio_tracks.tracks_from_info` keyed a track on
`format_note` -- a field carrying a **quality tier** (`low`, `medium`, `high`),
not a track name. yt-dlp returns one audio-only format per codec and per
bitrate, so an ordinary single-track video (a TED talk returns four formats)
listed as two or three rows, every one of them reading "English", and
`summarise` reported the wrong count in the no-described-audio message.

*Full detail: CHANGELOG, “The described-audio picker was listing one track as three”.*

## ...and then the fix for that listed three tracks as one

The worse half, found by testing the first fix against the videos that really do
publish a descriptive track. That fix keyed identity on yt-dlp's `audio_track`
id, falling back to the language code. **yt-dlp does not populate `audio_track`
for YouTube at all**; it writes the track's own name into `format_note`
alongside the quality tier, comma-joined: `"English original (default), low"`,
`"English descriptive, medium"`. So the fallback did all the work -- and because
YouTube gives a video's original and descriptive renditions the *same* language
code, two tracks would have read as one, **silently discarding the described
track in the feature whose only job is to find it.**

*Full detail: CHANGELOG, “...and then the fix for that listed three tracks as one”.*

## ...and then YouTube's withheld renditions were reached anyway

The probing established that most described content on YouTube -- including
Apple's and Microsoft's accessibility films -- is a **separate upload** with the
narration mixed into its only track, so one track is the right answer there and
the absence path is the common case. But a smaller set of videos (Emily
Graslie's *ART LAB*, several *Tested* videos carrying a DCMP track, two Apple
films) publishes a genuinely selectable descriptive rendition -- and YouTube's
web player response *names* those renditions while serving them URL-less (SABR
streaming), so yt-dlp discards them and every caller sees the original alone,
labelled *"English original (default)"*: the platform admitting there are others
it withheld.

*Full detail: CHANGELOG, “...and then YouTube's withheld renditions were reached anyway”.*

## A scheduled recording now ensures the machine is awake for it

Field-reported, and invisible from inside the app: a recording set for 11:00
announced itself at 11:03, with nothing failing. `RecordingScheduler` polls
every 20 seconds, so twenty seconds is the entire budget -- minutes mean the
machine slept. Keep-awake was scoped to `(playing or recording)`, never to the
stretch *before* a scheduled recording, which is precisely when an idle
computer standbys.

*Full detail: CHANGELOG, “A scheduled recording now ensures the machine is awake for it”.*

## The Station Catalog: Quill Radio browses before the internet answers

The whole working-station directory now ships inside Quill Radio and lives on
the listener's computer (`quill/core/radio/catalog/`): 62k+ stations plus the
Project Gutenberg audio shelf, in an FTS5-indexed SQLite store built as
generations behind an atomically-replaced pointer file -- the design Windows
forced, since `os.replace` over an open database raises PermissionError there
(LibriVox stays live in v1: its 194,501 chapter rows measured 60 MB against
the 10 MB seed budget; a compact section format is the named follow-up).
Browse axes and the seeded audiobook shelf answer in under
a millisecond offline, every folder carries its count, and Find Stations gets
an instant local lane. Freshness is three switchable layers (startup check,
staggered 24-hour default cadence, a manual command with a spoken summary)
with field-derived rules: an empty answer from a populated source is an
outage, not truth; tombstones with a 14-day grace; unchanged dumps write
nothing; hidden sources are never contacted. The cached-versus-live boundary
is a product surface -- a Status view naming why TuneIn/iHeart/Apple/Archive
stay live-only, a per-branch provenance line, one offline sentence per
session -- and user stations are structurally outside the store, proven by a
byte-identity test across rebuilds. The seed builds at release time with a
hard 10 MB gate (`scripts/build_radio_catalog.py`); the full plan with its
measurements is `standalone/radio/docs/prd.md` (Section 11, the Station
Catalog).

*Full detail: CHANGELOG, “The Station Catalog: Quill Radio browses before the internet answers”.*

## YouTube subscriptions, imported from your own export rather than your account

A listener asked whether Quill Radio could sign in with a YouTube account and
sync their history. Researched against Google's documentation, both are no:
Premium's benefits are tied to YouTube's own player (the developer policies
forbid a third-party client from separating audio from video, from background
playback, and from offline storage, with no Premium exception), and watch
history was removed from third-party reach years ago -- `playlistItems.list`
answers `watchHistoryNotAccessible`. What sat under the question was
answerable: *do not make me paste forty channel addresses.*

*Full detail: CHANGELOG, “YouTube subscriptions, imported from your own export rather than your account”.*

## An update offers back the edition you are running

Reported twice -- #1100 ("what was downloaded was the portable version rather
than the full installer") and again on 2026-08-16 ("whenever i update it shows
me the portable"). #1100 was closed after fixing one axis; the complaint
outlived it because three faults produced the same symptom:

*Full detail: CHANGELOG, “An update offers back the edition you are running”.*

## Every menu item shows its key, and a Close button that closes

Two accessibility faults, both structural. **Menus:** Quill Radio shipped 115
menu items of which 49 advertised no keyboard route at all, seven keys were
claimed by two items each (so one of each pair silently never fired), and two
labels advertised `Ctrl+Shift+Plus`/`Minus`, which wx rejects outright --
menus promising keys that could not work. Every item now carries a unique,
parseable accelerator; command-backed items render through `_menu_label` so
the label shows what is *actually* bound and follows a rebinding. Per-app
defaults live in the new `keymap.APP_KEYMAPS` rather than the global table,
because these are app keys: Ctrl+B is Browse Stations in Quill Radio and Bold
in QUILL's editor. `tests/unit/ui/test_menu_accelerators.py` builds the real
menu bar and fails on a missing key, a duplicate, or one wx cannot bind.
**Close buttons:** `wx.Dialog` answers `ID_CANCEL` for free and `wx.Frame`
does not, so converting the radio's heavy surfaces to modeless frames left
Browse Stations, Find Stations, Manage Favorites and Schedule Recording each
showing a Close button that did nothing -- only Escape closed them.
`dialog_contract.bind_close_button` is now the one way both shapes wire it,
with a source gate. Both rules are written into CLAUDE.md and the radio PRD
(A-11, A-12).

*Full detail: CHANGELOG, “Every menu item shows its key, and a Close button that closes”.*

## Radio Find became a search engine, the tree reads ahead, AudioPub arrives

Find in this folder routes to the fastest honest channel per branch
(`core/radio/branch_find.py`): the Podcasts anchor asks the real iTunes
Search API and answers with expandable show folders (a crawl of chart pages
is how Double Tap came back unfindable); catalog-served axes answer scoped
from local FTS, offline included; and every branch with its own engine uses
it -- LibriVox (book folders), Internet Archive (drillable items),
Gutenberg, SomaFM, TuneIn (stream-resolved), iHeart (sitemap index), NOAA,
Audius, Mixcloud, ccMixter. The crawl remains only where no engine exists;
every answer states its origin, and an unreachable directory says so
instead of posing as "no matches." The Find box moved above the tree (one
Shift+Tab, or Ctrl+F from anywhere in the window).
`ui/radio/browse_prefetch.py` adds cursor-driven prefetch -- highlight-ahead
and one-level read-ahead -- so expands open instantly; hidden sources stay
uncontacted, Safe Mode fetches nothing. Find Stations results that are works
(Apple shows, LibriVox books) now resolve off-thread and play their latest
episode / first section instead of handing the player an empty URL. And
AudioPub (audiopub.site) lands as a Community Audio source
(`core/radio/audiopub.py`): a Discover shelf of fifty randomized uploads per
page, live-only because uploaders keep their rights -- further branches wait
on a developer-blessed public API rather than scraping internal ones. Two
source fixes rode along: ccMixter's content host 403s any request without a
ccmixter.org Referer, so playback failed silently -- `stream_headers.py` is
now the one place per-host header knowledge lives, feeding both mpv
(`referrer`, cleared between stations) and the ffmpeg recorder
(`-referer`); and Gutenberg's topic/language branches fetched exactly one
32-record gutendex page posing as the whole shelf -- they page through with
an honest "More audiobooks" row now, handlers extracted to
`browse_libraries.py`.

*Full detail: CHANGELOG, “Radio Find became a search engine, the tree reads ahead, AudioPub arrives”.*

## The standalone apps escape the editor's release gate

The `core.radio` release gate (#1347, public QUILL builds) also fired inside
Quill Radio itself: in a public build the recording scheduler, missed-recording
reports, the pre-recording wake task, and all 44 radio palette commands were
silently dead -- the app gated off its own reason for existing.
`FeatureManager.grant_product_features` is the sanctioned escape: a companion
app claims the feature it is built around at startup, in-memory only (never
persisted by `save()`), with safety locks still applying on top. Quill Radio
grants `core.radio`; Quill Cast grants `core.podcasts` (its episode-check
monitor and palette had the same latent gate). Tests pin the grant semantics,
non-persistence, and the per-app wiring.

*Full detail: CHANGELOG, “The standalone apps escape the editor's release gate”.*

## The browse tree is prunable, and the queue got its preferences

Two models that shipped complete and reached nothing now have their surfaces,
found in a review pass over the browse tree ("declared but never dispatched" --
the exact failure the action rows had). `browse_visibility` was written,
tested, and never consulted: the tree always built all twenty-eight branches.
**Station > Choose Browse Sources...** (`ui/radio/browse_sources_dialog.py`)
now feeds `visible_roots()` into `_populate_sources` through a
`RadioHistory.browse_sources_enabled` field whose "never set" state is kept
distinct from "chosen", so a branch added in a later release still appears for
anyone who never touched the setting. The Search Sources rule holds: off means
not in the tree and never contacted; all-hidden leaves one row naming the way
back. `DownloadPrefs` likewise had no editor and a dead `always_ask` flag:
**Station > Download Preferences...** (`ui/radio/download_prefs_dialog.py`,
also a button inside View > Downloads) edits every rule with a live "what will
happen to the next thing I save?" sentence, `always_ask` is honoured in
`download_runner.enqueue` -- one prompt per batch, a declined prompt cancelling
the enqueue out loud -- and a saved change takes effect on the very next
download. Find results now keep each row's note (a ccMixter licence, TuneIn's
"resolves when you play it"), an action row explains itself while merely
highlighted, and `iheart_letter_groups` became the one `letter_groups`
implementation instead of a hand-kept twin.

*Full detail: CHANGELOG, “The browse tree is prunable, and the queue got its preferences”.*

## A download queue, and books that play back as books

One transfer at a time, in the order asked (`core/radio/download_queue.py`,
`ui/radio/download_runner.py`). Not a pool: every source behind this is a free
library run on donations, and order is what makes a part-finished book a
*playable prefix* rather than a scattering. The pump is re-entrant-safe by
construction -- each completion schedules the next from the UI thread's own
callback -- so there is no lock, because there is no concurrency to guard.

*Full detail: CHANGELOG, “A download queue, and books that play back as books”.*

## Continue Listening reaches local files

`PositionStore` keys on file contents so a place survives moving and renaming --
which is why it holds no path, and why local files could never be *listed*. A
local-only sidecar (`core/media/local_paths.py`) records where each was last
seen. Deliberately not a field on the synced record: a path is a fact about one
machine, and two machines disagreeing about one is two correct answers rather
than a conflict. A stale hint is skipped rather than offered and then failing.

*Full detail: CHANGELOG, “Continue Listening reaches local files”.*

## Downloading what is yours to keep

`core/radio/downloadable.py` is the whole design, and it is a policy rather than
a feature: an **affirmative allow-list** of sources whose terms clearly permit
saving, so an unrecognised source is refused rather than guessed at. Never assume
a downloadable-looking file may be redistributed.

*Full detail: CHANGELOG, “Downloading what is yours to keep”.*

## Three music libraries could be searched all along

Audius, Mixcloud and ccMixter were carried in `federated_search.LIBRARY_SOURCES`
with `search=None` and a written reason -- "publishes trending", "browsed by
category", "queried by tag". The browse tree offers those shelves because they
are good shelves; somewhere along the way that hardened into a recorded belief
that the services published no keyword search, and it reached the release notes
and the app as a statement about somebody else's product.

*Full detail: CHANGELOG, “Three music libraries could be searched all along”.*

## Pages files stopped opening, and nobody noticed

`quill/io/pages.py` patched keynote-parser's `ID_NAME_MAP` on every read, to stop
an unknown Pages archive type crashing the parse. keynote-parser 1.14 removed
that map entirely -- it handles an unknown archive itself now -- so the patch
raised `AttributeError` on every `.pages` file opened against a current install.
The fallback that existed to prevent a crash had become the crash.

*Full detail: CHANGELOG, “Pages files stopped opening, and nobody noticed”.*

## Your place follows you between machines

The QuillSync engine could commit, push and pull encrypted records; the position
stores already satisfied its protocols; nothing moved a record.
`core/sync/places.py` is the adapter that does, and with it the two questions the
plan had left open are settled.

*Full detail: CHANGELOG, “Your place follows you between machines”.*

## Everything you started, in one list

`core/media/continue_listening.py` gathers the podcast, the streamed recording
and the local file into one list, newest first, with the provider named on every
row -- because pressing Enter on a mixed list starts three different kinds of
thing. Each source is asked separately and may fail alone; only rows that can
actually be resumed are offered; Resume is disabled where the running app has no
way to play that kind, and Forget is a first-class button.

*Full detail: CHANGELOG, “Everything you started, in one list”.*

## Quill Inkwell: choices, application scope, and Quillin reach

`${choice:Label|one|two|three}` offers its options instead of asking for typing.
`Abbreviation.apps` scopes an entry to named applications, honoured system-wide
only -- and a scoped entry does not fire when the foreground application cannot
be identified. Quillin-contributed abbreviations now reach Inkwell rather than
stopping at the edge of the editor, with the user's own entry always winning a
collision and nothing contributed ever persisted.

*Full detail: CHANGELOG, “Quill Inkwell: choices, application scope, and Quillin reach”.*

## Cast: the Inbox gets the bulk actions, and two smaller things

Triage is the Inbox's whole job and it happens a handful of episodes at a time,
so **File N Episodes to Inbox Folder...** joins the bulk actions (one folder
picker for the selection, not one per episode), alongside **Add N to Playlist**
and **Remove N Downloaded Copies**. A `.opml` subscription list can be opened by
double-clicking it -- the installer offers the association, unchecked, and the
app accepts a path on the command line. And **Shift+Right held** scans forward at
four times speed, dropping back to exactly the speed you were at when released,
announced at both edges.

*Full detail: CHANGELOG, “Cast: the Inbox gets the bulk actions, and two smaller things”.*

## The Book Library became a hub over libraries

Developer builds only, like the rest of `core.library`. Three changes, each
driven by how the window sounds rather than how it looks.

*Full detail: CHANGELOG, “The Book Library became a hub over libraries”.*

## The rest of the Podcasting 2.0 namespace, which Cast was discarding

`core/podcasts/feed_reader.py` read `podcast:chapters` and `podcast:transcript`
and threw away everything else in the namespace -- tags real shows already
publish, sitting in bytes Cast had already downloaded and parsed. All of it is
now read: people, soundbites, live items, podroll, funding, location, and
alternate enclosures.

*Full detail: CHANGELOG, “The rest of the Podcasting 2.0 namespace, which Cast was discarding”.*

## A streamed podcast episode is now a fully capable episode

Quill Cast quietly had two classes of episode. A downloaded one could have its
chapters found, its position resumed exactly, and its audio analysed; a streamed
one could not, and you had to know which kind you were holding before you knew
which features you had. That split is gone.

*Full detail: CHANGELOG, “A streamed podcast episode is now a fully capable episode”.*

## Fixes

- **Find Chapters had never worked.** *Find Chapters in This Episode* answered
  "This episode cannot be identified." for every episode, on every surface. The
  cause was one word: the code read a show's `show_id`, which is what a
  *download queue item* calls that value, while a show itself calls it `id` --
  so the lookup silently produced an empty string and the command bailed before
  doing anything. Both spellings now resolve through one helper, so they cannot
  disagree again.
- **A full disk can no longer close QUILL with your document unsaved (#1390).**
  This is the serious one. Choosing **Save** on the close prompt, on a disk with
  no space left, closed QUILL *without saving*. The cause was an ordering
  mistake with a real cost: the save path writes a backup copy first, and that
  backup write was the one thing outside the guard that catches a failed write.
  So the backup failed, the exception escaped the save entirely -- before the
  real file was ever touched -- the close path's safety net swallowed it as "the
  prompt misbehaved, close anyway", and the window went away with the work in
  it. Four changes, and the shape of the fix is the point:
  - **A backup can never stop a save.** A backup exists to protect you *from* a
    bad save; letting it prevent the save inverts its purpose. It now degrades
    to "Could not write a backup; saving anyway" and the real save proceeds.
  - **Backups are written the way autosave snapshots are** -- atomically, and
    always as UTF-8 rather than the document's own encoding. Atomic, so an
    interrupted backup can never be what you restore; UTF-8, because a document
    read as ASCII (a BRF braille file, say) used to raise the moment its buffer
    gained an accented character -- and *that* also aborted the save. Backups
    written by earlier versions still restore.
  - **The message says what to do.** "[Errno 28] No space left on device" is
    true and useless. A full disk now reads "The disk is full. QUILL could not
    save `notes.md`. Free some space and try again -- your text is still open
    and unsaved." A read-only file or folder gets its own sentence pointing at
    Save As.
  - **A failed save is not consent to close.** The window must always be
    closable, and it still is -- but the first close after a failed save is
    cancelled with an explanation, so you can free space or Save As somewhere
    else. Closing a second time proceeds, so the window can never be trapped
    open by this. (`quill/ui/main_frame_write_safety.py`, `core/backups.py`)
- **Autosave says so when it stops working (#1386).** Autosave already survived
  a full disk without crashing -- but it survived it *silently*, which means
  your crash-recovery safety net was gone with nothing to tell you. After two
  failures in a row it now says, once: "Autosave paused -- the disk is full.
  Your work is not being snapshotted." Once per failure streak, not per attempt,
  and it goes quiet again the moment autosave succeeds.
- **Typing is faster, and the screen reader keeps up with it (#1346).** The
  report was "long pauses between text entry and reporting from either NVDA and
  JAWS. Sometimes certain keys are not intercepted, such as the space, so that
  words run together." That is not a screen-reader setting; it is a blocked
  message pump, and the cause was QUILL's own work per keystroke. Every
  character typed triggered three or four *complete* copies of the document out
  of the Windows edit control -- roughly a megabyte of copying per keystroke on
  a 200 KB file -- plus a full-text comparison and a menu-state refresh, all
  before the next key could be handled. So the change notification the screen
  reader waits on arrived late, and keystrokes queued and coalesced, which is
  exactly what a dropped space is. Three changes: the buffer is now read **once**
  per keystroke and handed to everything that needs it; only the three things
  that must be true before the next keystroke stay synchronous (the document
  text, the modified marker, the status line), while previews, spell-check hints,
  word prediction, browse pre-warming, language detection and the contextual
  menu refresh move behind a restarting 120 ms timer -- so they run in the gap
  *after* the character has reached the screen reader, and are skipped entirely
  while you type faster than that; and the periodic autosave disk write moved off
  the UI thread, removing a recurring mid-sentence hitch on large files. A build
  check now asserts the one-read-per-keystroke budget, so this cannot quietly
  creep back. (`quill/ui/main_frame_typing.py`, `quill/ui/main_frame_write_safety.py`)

*Full detail: CHANGELOG, “Fixes”.*

## Improved

- **The two Italian Piper voices can be previewed before you download them.**
  Paola and Riccardo were in the voice list but were the only two Piper voices
  with no preview clip, so the one way to hear them was to download ~60 MB and
  hope. Both now have a preview like the other 37. The reason they were missing
  is worth naming: generating previews needed a Piper engine staged by hand,
  which nobody could reproduce -- so `scripts/fetch_build_deps.py --only piper`
  now stages the exact SHA-256-pinned engine QUILL itself installs, and
  `gen_voice_previews.py --fetch-missing-voices` fetches any voice model it is
  missing through the same verified path as the in-app download. A preview run
  no longer depends on what happens to be on the builder's machine.
  (`scripts/fetch_build_deps.py`, `scripts/gen_voice_previews.py`)
- **The Command Palette says which way every toggle is currently set (#1383).**
  The palette lists commands by name and has no checkmark column, so "Toggle
  Soft Wrap" read identically whether soft wrap was on or off -- the one thing
  you opened the palette to find out. Reported for Internet Radio's **Announce
  Track Titles** (by two people), but it was never one entry's problem: soft
  wrap, dark mode, find wrap, the tab control, persistent undo, spell check as
  you type, word prediction, overwrite mode, extend-selection mode, tab insert
  mode and abbreviation expansion all now read "(currently On)" or "(currently
  Off)", refreshed each time the palette opens.
  (`quill/ui/main_frame_palette_labels.py`)
- **Winamp's classic playback keys work in the radio Recordings player
  (#1344).** X play, C pause, V stop, B next, Z previous, arrows to seek, T for
  elapsed or remaining, J to jump to a recording, Ctrl+J to jump to a time. See
  `docs/CONTROL_REFERENCE.md` for the full map and the two places it knowingly
  differs from Winamp. (`quill/ui/radio/winamp_keys.py`)
- **...and the last three keys are bound now: the Recordings list has a play
  queue.** Shuffle (**R**), repeat (**S**) and stop-after-current (**Ctrl+V**)
  were deliberately left unbound, because all three describe a queue that did
  not exist and a key that only pretends to work is worse than one that is not
  offered. Shuffle is a **fixed order**, not a fresh roll each time: every
  recording plays once before any repeats, and **Z** reliably goes back to what
  you just heard -- which "random next" can never do. Repeat cycles off, all
  recordings, this recording, and repeat-one applies when a recording *ends*
  rather than when you press Next, because a Next that refused to move would
  look broken. Stop-after-current outranks repeat, clears itself when it fires,
  and never survives a restart. A recording that finishes on its own is now
  followed by whatever the queue says is next. Shuffle and repeat are
  remembered. (`quill/core/radio/play_queue.py`,
  `quill/ui/radio/recordings_queue.py`)
- **The Quill Media Player answers to the same Winamp keys.** It was the last
  holdout, and the one a Winamp user is most likely to reach for -- an
  audiobook with a track list is a playlist editor with a transport. Same
  letters, same seek steps, same words spoken back, from the same shared map,
  so nothing has to be relearned per app. **B** and **Z** step through the
  book's tracks, or by chapter when the book is a single file; **Ctrl+J**
  opens the accessible Go to Position dialog it already had rather than a
  second, lesser prompt. (`quill/ui/media/winamp_mixin.py`)
- **Sound Enhancements has a key in full QUILL too: Ctrl+E.** Both standalone
  apps have had it; full QUILL never did, because it has *both* players at
  once and two commands wanted the same key. It now follows the sound you can
  actually hear -- a playing (or paused) podcast wins, otherwise radio -- and
  says which one it opened, because one key with two destinations must never
  leave you guessing. The two per-player commands also became rebindable: they
  were registered as commands but missing from the keymap entirely, so the
  Keyboard Shortcuts editor had nothing to offer.
  (`quill/ui/media/sound_enhancements_route.py`)
- **Seeking a finished YouTube video moves along the video, not the live
  buffer.** Radio's Forward/Back 30 Seconds always ran the live-stream DVR
  seek, so on a finished video it announced how far you were "behind live" --
  a live edge that does not exist. It now moves along the real timeline and
  says "3 minutes 10 seconds of 18 minutes 40 seconds". A live stream is
  unchanged. **Go to Position...** (Ctrl+Shift+J in Quill Radio) adds the
  absolute jump, reusing the same accessible Hours/Minutes/Seconds dialog the
  Media Player uses. (`quill/ui/radio/bounded_playback_ui.py`)
- **A flaky connection no longer looks like a dead feed.** Feed refresh, the
  podcast directory search, and the OPML reachability sweep now retry twice --
  a second, then two seconds later -- on a *transient* failure: a 5xx, a
  dropped connection, a timeout. A 404, an address that does not resolve, and
  a sign-in failure still fail at once, because retrying them cannot change
  the answer. This matters most in the OPML sweep, whose verdict is what the
  import report offers to prune out of your subscription list: one busy
  moment's 503 must never be the reason a live subscription gets deleted.
  (`quill/core/net_retry.py`)
- **"Show in Explorer" now actually selects the file.** Four places had grown
  their own copy of the command and two were wrong the same way: Windows
  Explorer takes `/select,` and the path as *one* argument, and split in two it
  quietly drops the switch and opens Documents instead. A window opened, so it
  looked like it worked -- with no visual cue for a screen-reader user that the
  wrong folder had just appeared. One tested implementation now, used by the
  editor, the app shell's post-update "Open folder", Audio Studio, the radio
  Recordings list, and Cast's new Show in File Explorer.
  (`quill/core/file_manager.py`)

*Full detail: CHANGELOG, “Improved”.*

## The Media Player reads your notes back as you reach them

- **A note you left at 14:32 is spoken when playback gets there.** Bookmarks
  have carried an optional note for a while, but the only way to meet one again
  was to stop and open a list -- which is the wrong shape for a thing you make
  *while listening*. On by default (**Playback > Read My Notes Aloud as I Reach
  Them**); writing the note is the opt-in, since somebody who left one meant to
  hear it. Only bookmarks that actually have a note speak: a plain bookmark is a
  place to jump to, and announcing one with nothing to say is noise. A labelled
  bookmark speaks its label first; an unlabelled one is prefixed "Note:", so a
  sentence spoken over an audiobook is never heard as part of the book. No
  timestamp -- you are at that moment, and a spoken "14:32" is ambiguous where
  the written form is not (rule A-8).

*Full detail: CHANGELOG, “The Media Player reads your notes back as you reach them”.*

## Gates that no longer time out on a loaded machine

- **The whole-tree gates were re-reading the same 1,300 files up to a dozen
  times per run.** `check_banned_patterns` runs nine checks over overlapping
  file sets and each did its own read-and-parse, so `main_frame.py` -- around
  27,000 lines -- was parsed twelve times in a single pass. The gate was never
  wrong, only slow, and slow had a real cost: it grew until it brushed pytest's
  per-test timeout on a loaded machine and began failing intermittently. A gate
  that times out sometimes is one people learn to re-run rather than believe.
  Measured, the gate now takes **13 seconds instead of 35**.

*Full detail: CHANGELOG, “Gates that no longer time out on a loaded machine”.*

## Undo history that does not grow with your document

- **Persistent undo held up to a hundred full copies of the document, and
  rewrote all of them every few seconds while you typed.** A hundred snapshots
  of a shopping list is nothing; a hundred snapshots of a 1 MB manuscript is
  100 MB, in memory *and* on disk, because the whole history is one JSON file --
  so the cost of every keystroke grew with the length of the piece you were
  writing, which is exactly backwards. History is now bounded by total size as
  well as by count, keeping the newest steps; anything up to about 80 KB still
  keeps the full hundred. The in-memory copy and the undo cursor are kept in
  step with what actually survived, without which the cap would have bounded the
  file and not the memory, and Ctrl+Z would have quietly restored the wrong
  snapshot.

*Full detail: CHANGELOG, “Undo history that does not grow with your document”.*

## Every app in the family has its own face

- **Four apps were shipping the same icon.** Quill Inkwell, Quill Audio Studio
  and Quill Weather all carried a **byte-identical** copy of Quill Radio's
  broadcast-wave `.ico` -- the same SHA-256, not merely a similar drawing -- and
  two more, QuillBeacon and QUILL Social, shipped installers with no icon at
  all, so they wore PyInstaller's generic default. Nobody chose any of that: each
  new app was scaffolded from the last one, and an icon is easy not to notice.
  The cost is not cosmetic. Three products impersonating a fourth in the taskbar,
  in Alt+Tab, and in the tray is a real navigation problem, and the tray is
  exactly where a tray-resident app lives its whole life.

*Full detail: CHANGELOG, “Every app in the family has its own face”.*

## Fixed in passing

- **Player Information reported "0 notes" for every episode.** The count was
  gathered by a call with the wrong number of arguments, and the `TypeError`
  it raised on every single run was swallowed by a broad `except` -- so an
  episode with fifty notes read as having none. A confident wrong number is
  worse than an absent one (rule A-10). (`quill/ui/podcasts/player_info_source.py`)

*Full detail: CHANGELOG, “Fixed in passing”.*

