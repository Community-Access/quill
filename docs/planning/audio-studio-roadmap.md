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
