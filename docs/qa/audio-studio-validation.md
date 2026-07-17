# Audio Studio: The Road to Feature Complete

## Tier 1 — Merge gate: two items, both now scoped to what only Jeff can do

Both items below were partially executed 2026-07-05 at the level an agent can
safely reach on Jeff's own desktop (never launching the real app or sending
synthetic keystrokes — see the "no desktop UI automation" rule). What's left
in each is now exactly the part that needs a human at the keyboard with a
real screen reader.

### 1. Real screen-reader validation (JAWS, then NVDA) — needs Jeff

**What:** Walk every new surface with JAWS on real hardware: the wizard
(focus landing on each page change, step announcements, the radio-driven
journey switch, Skip to summary), the Chapter Workbench (list refresh after
each surgery operation, the title edit flow, button states), the player
(transport labels, spoken position slider, chapter-crossing announcements,
Where am I?), and the Publish dialog. Fix what your ears find.

**Why an agent can't do this:** it requires launching the real `quill.exe`
and driving it with a live JAWS/NVDA session — exactly the desktop UI
automation that's off-limits on Jeff's machine (it fights JAWS: focus theft,
Dictionary Manager triggered by intercepted keystrokes). The `tests/uia`
pywinauto harness covers this mechanically in CI/a VM, but "does JAWS
announce this well" is a human judgment call, not a pass/fail an agent can
render.

**Outcome:** The feature's core promise — screen-reader-first audiobook
production — is verified by the person it was built for, not just by the
dialog gates.

### 2. End-to-end run on real audio, especially M4B playback — core half done, one real bug found and fixed

**What:** One complete journey on real files: narrate a folder into an M4B,
open it in the Workbench, play it, split a chapter at the playhead, save as,
verify in a podcast app.

**Done 2026-07-05 (core-level, no GUI, safe to run alongside a live JAWS
session):** real SAPI5 synthesis + real ffmpeg built an actual 3-chapter M4B
from real Markdown source; `book_file.read_book` read it back correctly;
`chapters.split_chapter` split a chapter at a computed playhead; the split
was saved via `save_m4b_book_as` (the lossless `-c copy` re-mux) and verified
independently with `ffprobe` to have the correct 4 chapters at the correct
timestamps; the untouched original file still round-tripped afterward.

**Real bug found this way, not by any stubbed-source unit test:** the resave
step failed against a real Windows-encoded M4B with `ffmpeg`'s "Tag text
incompatible with output codec id" — the source carried a stray
`bin_data`/`SubtitleHandler` data track that `-map 0` blindly copied into the
`ipod` muxer, which rejects it. Fixed in `build_m4b_remux_command`
(`quill/core/speech/book_file.py`): map `0:a` and `0:v?` explicitly instead
of `0`, so only audio and an optional cover-art stream are copied. New
regression test `test_m4b_remux_command_maps_audio_and_video_only`. This is
exactly the class of bug this roadmap item existed to catch.

**Still needs Jeff:** actually pressing Play in the Workbench and listening —
loading the file into `WxMediaEngine`/`MpvAudioEngine` requires a live
`wx.App` pumping the Windows message loop, which is the same JAWS-hostile
territory as item 1. The remaining risk is narrower now: whether the WMP
backend's *audio playback and seek feel*, not the file's correctness, holds
up on a real 8-hour book. If it doesn't, the already-shipped libmpv backend
(Help > Download Optional Components > mpv player engine) is the fallback.

**Outcome:** File-format correctness is proven end-to-end with real tools;
only the subjective "does it play and seek well by ear" question remains.

## Tier 2 — Phase 2 port-in validation (shared modules, standalone-surfaced)

The Phase 2 port-in adds shared `quill/` modules
(`core/audio_studio/{book_prefs,history,library,play_queue,sleep_timer}`) and
UIs (`library_tree`, `play_queue_dialog`, `sleep_timer_dialog`) that the
standalone QUILL-AS Studio shell surfaces (library tree, resume-on-launch,
Recently Played, media keys, sleep timer, per-book volume/mute, play queue +
auto-advance). Embedded QUILL exposes only the Workbench **Mute** button from
this round. The unit suites (QUILL `tests/unit/{core,ui}/audio_studio/`,
QUILL-AS `tests/unit/ui/test_studio_shell_*`) cover the headless behavior;
these items are the live, ears-on checks.

### 3. Per-book volume/mute and media keys — needs Jeff

**What:** In the standalone Studio, open a book, set volume to about 40%,
mute (Ctrl+M), unmute — confirm volume restores to 40. Close and reopen the
same book — confirm it remembers 40% and the mute state. With the book
playing, press the media Play/Pause, Stop, and Next/Previous keys — confirm
they route to the Workbench player.

**Why an agent can't do this:** media-key hotkeys and audible volume need a
real desktop session; the headless tests only assert the callbacks delegate
and the prefs round-trip to JSON.

**Outcome:** per-book prefs persist across launches and media keys drive the
active player — the two pieces of shell-only behavior the contract exists to
enable.

### 4. Play queue auto-advance + sleep timer — needs Jeff

**What:** Add two books to the Play Queue (Book Tools > Play Queue), open the
first, let it finish (or seek to the end) — confirm the Studio announces the
next and opens it on close. Set Book Tools > Sleep Timer to one minute (or
end of chapter) — confirm playback stops on cue and the status announces it.

**Why an agent can't do this:** end-of-book and the timer fire against a live
player pumping the message loop; the headless test only asserts
`wx.CallAfter(open_book, next)` is scheduled on finish-then-close and the
watcher calls `on_sleep` once.

**Outcome:** queue auto-advance and the sleep timer behave by ear, not just
in the unit oracle.

### 5. Library tree + resume-on-launch — needs Jeff

**What:** Add books, mark one Favorite, move one into a new folder, and
confirm the tree (Favorites / In Progress / Recently Played / Inbox + your
folders) reads correctly with JAWS/NVDA and the context menu (Open / Reveal /
Favorite / Move / New Folder / Remove) is keyboard-complete. Toggle Studio >
Resume on launch, close mid-chapter, relaunch — confirm it reopens at the
saved position.

**Why an agent can't do this:** tree navigation and resume-on-launch need a
live app and screen reader; the headless tests assert the tree builds from
`library.py` and the resume flag persists.

**Outcome:** the library tree is screen-reader-navigable and resume-on-launch
lands you where you stopped.
