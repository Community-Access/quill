# Earshot parity in QUILL Cast, round two

QUILL Cast and Earshot, the iPhone podcast app by Michael Babcock (Payown
Media), are built for the same listeners, and Cast keeps in step with it. This
document is the plan of record for the second round of that work: what Earshot
added after the first round, what Cast now does about each item, and what is
left. Code cites it by item, for example `earshot.md E1`, and those citations
resolve here.

The first round (2026-09 to 2026-10-03) had its own working file, `ear.md`,
which was never committed; it is summarised in the Cast product requirements
document (PRD), `standalone/cast/docs/prd.md`, section 23.25. Its citations
(`ear.md R4`, `ear.md B3` and so on) still resolve there and in git history.
This round's review file was also called `ear.md` and lived only on Jeff's
machine; everything in it is carried into this document.

## 1. The rule

Parity means the listener gets the **same outcome**, not the same screen: keys
where iOS has gestures, the Command Palette where iOS has Siri, a menu where iOS
has a swipe action. Nothing is copied where Earshot made a choice only iOS
needs, and nothing is invented where Earshot has not defined something: Cast
then follows the shared Listening Places format or waits.

## 2. What was compared

| | Round one | Round two |
|---|---|---|
| Earshot | `63dc641`, 2026-09-29, version 1.2.3, TestFlight build 273 | `c11dda93`, 2026-11-15, version 1.2.6, TestFlight build 317 |
| QUILL Cast | 2.0.0 | `Community-Access/quill` main at `7738f92` |

The 62 Earshot commits between the two were read one by one, together with
Earshot's tester notes (`docs/kashe.md`, chapters 96 to 122), its settings
store (`Earshot/Data/Persistence/AppSettingsStore.swift`) and the code behind
each feature. Earshot's whole settings list was matched against Cast's
settings catalogue, and its older features were spot-checked, which found one
gap the first round did not record (E9).

## 3. Decisions

- **2026-11-15, Jeff: everything.** Build every item in the review, the
  "consider" items included, not only the recommended ones.
- **2026-11-15, Jeff: Played and Unplayed** (D1). Cast moves from "unheard" to
  Earshot's wording.
- **2026-11-15, Jeff: stopping near the end counts as finished, and the
  listener chooses how near** (FW). This came from a listener's report, not
  from Earshot, and shipped first, in pull request #1844.

## 4. The items

Each item gives Earshot's behaviour, what Cast did before, and what it does
now, with the code that carries it.

### FW. Stopping near the end counts as finished

- **Report:** a listener (2026-11-15) asked why finished episodes stayed in
  Continue Listening. They had stopped during the closing credits, so Cast kept
  a place at 99 percent and never marked them played.
- **Now:** **Count as finished when stopped within the last** (Preferences >
  Playing, and Settings for This Podcast; `finished_within_seconds`, one minute
  by default, zero for only a true end). Leaving an episode inside the window
  (stop, switch, close) marks it played; a pause never does. Continue
  Listening hides a place already inside it. The window only applies past an
  episode's halfway point, so a short clip is never finished on starting.
- **Code:** `quill/core/podcasts/finish_window.py`,
  `quill/ui/podcasts/finish_bookkeeping.py`, the `leaving` checkpoint in
  `quill/ui/podcasts/player_controller.py`.

### E1. The outro skip fires only on a natural crossing

- **Earshot** (`b8bdf852`, `PlaybackLogic.crossedOutroSkipBoundary`): only when
  playback moves forward by 10 seconds or less from before the boundary to
  after it, and only when the episode is more than 2 seconds longer than the
  skip.
- **Cast before:** fired whenever the position was inside the window. Resuming
  an episode saved there ended it at once, seeking in to hear a last sentence
  ended it, and an episode shorter than the skip ended the moment it started.
- **Now:** Earshot's rule exactly. The controller remembers the last polled
  position and forgets it on every start, resume and seek.
- **Code:** `quill/core/podcasts/outro_skip.py`, `_on_outro_poll` in
  `player_controller.py`.

### E2. Publisher times are validated

- **Earshot** (`77a21a17`): a chapter time must be finite, at least zero,
  representable, and not a boolean; a bad entry drops only itself.
- **Cast before:** Python's JSON (JavaScript Object Notation) reader accepts
  `NaN` and `Infinity`. One `NaN` chapter raised `ValueError` and lost the
  whole list; `Infinity` raised `OverflowError` there, in transcripts, and in
  a feed's soundbite tags (so in feed parsing itself); `true` became a chapter
  at one second; `1e300` became a chapter no episode has.
- **Now:** one rule for every source: a finite non-boolean number from zero to
  under a week. A chapter with a bad time is dropped; a transcript cue keeps
  its text at zero.
- **Code:** `quill/core/podcasts/time_values.py`, used by `chapters.py`,
  `transcripts.py` and `namespace_tags.py`.

### E3. Listening Places: never over somebody else's file, never fail in silence

- **Earshot** (`b6d37e8e`, `7d702f9b`): its device file is replaced only when
  it still holds what Earshot last wrote; anything else is left untouched with
  a sentence saying why, and a failed write is announced.
- **Cast before:** wrote over whatever was at its path, and returned the same
  `False` for "write failed" as for "nothing changed", so a failure was never
  reported.
- **Now:** this device's file is replaced only while it is still ours (the
  fingerprint beside it matches, or, with no fingerprint yet, it is a
  `listening-places/1` file naming this device). Otherwise, and when the write
  fails, `ListeningPlacesWriteError` (`QUILL-SYNC-PLACES-NOT-WRITTEN`) carries
  one sentence into the sync report.
- **Code:** `quill/core/sync/listening_places_guard.py`,
  `write_device_file` in `listening_places.py`, `places_interchange.py`.

### F1. Mark as Played and Next does the whole finish

- **Found during the review**, not an Earshot item. The command set
  `played` by hand, so the finish had no sync timestamp, was not shared with
  Quill Radio, recorded no statistics and skipped delete-after-play; then the
  next episode's start checkpointed the old one and wrote a position back onto
  it.
- **Now:** it calls the same `record_finish` as a natural end and tells the
  player to forget the finished episode before the next one starts.
- **Also:** delete-after-play on a file the player still has open now waits a
  turn of the event loop, because Windows refuses to delete an open file.
- **Code:** `quill/ui/podcasts/finish_bookkeeping.py`,
  `queue_commands.mark_played_and_next`, `forget_current_episode` in
  `player_transport.py`.

### E4. Keep finished episodes in the Play Queue

- **Earshot** (`85df19c8`, chapter 96): an option, off by default; a finished
  queued episode stays, marked played, and automatic playback skips it.
- **Now:** **Keep finished episodes in the Play Queue** (Preferences >
  Playing, `keep_finished_in_queue`, off). The slot stays, its row ends
  ", played", and the run steps over finished slots. Delete in the queue still
  removes one.
- **Code:** `finish_slot(keep=...)` and `step_after_finishing` in
  `quill/core/podcasts/queue_steps.py`; the row in `play_queue_dialog.py`.

### E5. Select All, Invert Selection, Mark Selected as Unplayed

- **Earshot** (`de3422f1`, chapter 98): select all matching, invert, and bulk
  mark played or unplayed.
- **Now:** **Ctrl+A** and **Alt+Shift+I** on the episode list, answered only
  while the list has focus (as menu accelerators they would take Ctrl+A from
  Cast's search box); both on the list's context menu with their keys shown;
  **Mark N Episodes as Unplayed** beside Mark as Played when the selection has
  a played episode. The count is spoken, because a screen reader announces only
  the focused row.
- **Code:** `quill/ui/podcasts/episode_selection.py`,
  `context_menus.py`, `_on_bulk_mark_unplayed` in `manager_actions.py`. QUILL's
  Podcast Manager answers the same two keys and has the same bulk menu.

### E6. Compression strength

- **Earshot** (`b28ce177`): Off, Light, Balanced, Strong.
- **Cast before:** one fixed compressor, on or off.
- **Now:** **How much to even out the volume** (`compression_level`), used
  while Even out volume is on, with Earshot's values. ffmpeg's `acompressor`
  takes make-up gain as a factor, not decibels, so +2, +4 and +6 dB become
  1.26, 1.58 and 2.

  | Level | Threshold | Ratio | Make-up gain |
  |---|---|---|---|
  | Light | -24 dB | 2:1 | +2 dB |
  | Balanced | -30 dB | 3:1 | +4 dB |
  | Strong | -36 dB | 4:1 | +6 dB |

  Quill Radio's compressor is unchanged: the builders take `True` for it and a
  level name from Cast, so no second argument had to be threaded through the
  six functions that build an ffmpeg graph.
- **Code:** `quill/core/audio/compressor_levels.py`,
  `PodcastSettings.compressor()`.

### E7. Start the queue again

- **Earshot** (#950, before round one but not recorded then): optional queue
  wrap.
- **Cast before:** "there is no wrap", with no recorded reason.
- **Now:** **At the end of the queue, start again from the first unplayed
  episode** (`wrap_queue`, off). It never plays a finished episode again, so a
  run cannot loop on itself.
- **Code:** `step_after_finishing` in `queue_steps.py`.

### E8. Preview reads episode descriptions

- **Earshot** (`a35a703b`): previewing a podcast you do not follow reads each
  episode's description.
- **Now:** the Preview window has **Episode description** (Alt+D), showing
  the episode selected in Recent episodes.
- **Code:** `quill/ui/podcasts/feed_preview_dialog.py`.

### E9. Listening statistics by folder

- **Earshot** (1.1.1): All folders, any folder and its subfolders, or Unfiled.
- **Now:** **Folder** (Alt+F) in Listening Statistics when the library has
  folders. A folder means its subtree; a podcast filed twice counts once;
  history follows today's filing.
- **Code:** `quill/core/podcasts/stats_scope.py`, `summarize(show_ids=...)` in
  `stats.py`, `stats_dialog.py`.

### E10. Whole groups in the Play Queue

- **Earshot** (`85df19c8`): group moves and pick up and drop for groups.
- **Now:** in a grouped Play Queue a heading stands for its group: **Move to
  Top** and **Move to Bottom** move it, and **Mark for Move** picks it up to
  drop above or below another group or episode.
- **Code:** `move_block_next_to` in `quill/core/podcasts/queue_selection.py`,
  `_heading_group` and `_move_marked_group` in `play_queue_dialog.py`.

### D1. Played and Unplayed

- **Earshot** (`64b56ac9`, 2026-11-12) moved every listener-facing word to
  Played and Unplayed.
- **Now:** GATE-CAST-WORDS (`quill/tools/cast_words_audit.py`, with the word
  list in `quill/core/podcasts/words.py`) forbids "unheard" and suggests
  "unplayed". 58 strings in Cast, QUILL's Podcasts menu and Quill Radio's
  podcast browsing changed, and the guide and tutorials with them. Saved
  values are unchanged (the `unheard` count mode and column, `unheard_first`,
  `most_unheard`), and "unheard" stays a Find a Setting alias.

## 5. Settings added

| Setting | Label | Levels | Default |
|---|---|---|---|
| `finished_within_seconds` | Count as finished when stopped within the last | all, per podcast | 60 seconds |
| `compression_level` | How much to even out the volume | all, per podcast | Light |
| `keep_finished_in_queue` | Keep finished episodes in the Play Queue | all | off |
| `wrap_queue` | At the end of the queue, start again from the first unplayed episode | all | off |

All four come from the settings catalogue, so they appear in Preferences, in
Settings for This Podcast where the level allows, and in Find a Setting.

## 6. Checked and not carried over

| Earshot feature | Why not for Cast |
|---|---|
| Apple Watch app, handoff, Watch queue sync, complications | No desktop counterpart |
| iPad navigation, iPhone Duo layouts, multiple windows | Platform layout |
| Magic Tap play and pause | Cast's Play/Pause can be a global hotkey (Tools, Global Hotkeys) |
| Siri, Shortcuts, system search, listening suggestions | The Command Palette covers it; Windows has no matching system |
| BBC HTTPS media selector, HTTPS-first playback with an HTTP warning | Exist because iOS blocks plain HTTP audio; Windows does not |
| Player transport button customization | A touchscreen layout preference; Cast has keys and Quick Actions |
| Keep place when loading older episodes | Cast does not page its episode list |
| Position slider step, haptics, theme, accent colour | iOS controls |
| Earshot Plus, tips, podcast cap | Business model |
| Download journal, backup exclusion, library-reset recovery | iOS storage and iCloud plumbing |
| Episode names kept out of logs | Already true in Cast |

## 7. Progress log

- **2026-11-15.** Review against Earshot `c11dda93`. FW shipped (#1844), with
  its guide EPUB in #1845. E1, E2, E3 and F1 built and tested; E4 to E7, then
  E8 to E10, then D1. This document, the Cast PRD section 23.26, both
  changelogs, the user guide, the tutorials, and the generated F1 help
  reference updated.

## 8. Remaining tasks

- **Screen-reader acceptance** with NVDA and JAWS on Windows: the spoken
  counts for Ctrl+A and Alt+Shift+I, the ", played" row in the Play Queue,
  the Folder choice in Listening Statistics, and the Episode description field
  in Preview. Add them to `docs/qa/screen-reader-checks-2026-10.md` when run.
- **Listen to the three compression levels** on quiet and loud speech, and
  decide whether turning compression on should keep starting at Light. A
  listener who had it on before now hears Earshot's Light, which is a little
  gentler than the old fixed setting (-18 dB, 3:1).
- **Sound Enhancements window.** It still offers Even Out Volume as on or off;
  the strength is chosen in Preferences or Settings for This Podcast. A
  strength choice in the window itself means changing the editor Quill Radio
  shares, so it waits for a reason.
- **Round three** starts from Earshot `c11dda93`. Earshot's Listening Places
  still writes only; when it starts reading other devices' files, check the
  records Cast writes against what it expects.
