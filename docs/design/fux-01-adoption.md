# FUX-01: return to the exact place, with a useful way back, app by app

**Date:** 2026-11-24
**Source:** FUX-01 in the family UX plan (`git show b7c6a1a04^:complete2.md`), held to [family-interaction-contracts.md](family-interaction-contracts.md). The QUILL Lite pilot task is "Reopen a long document and get back to the sentence you left" ([2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md), section 1). Jeff's order: QUILL Lite reading and editing first, then Cast and Media Player, then the rest only where a gap is clearly real. It adds no Start screen, panel or new store: places go into the stores each app already has.

## What "the exact place" has to mean

1. **The place, not only the file.** The sentence in a document, the time in an episode or a file, the station, the row you were on.
2. **Found again, not guessed.** An offset or a time can drift when the source changes. Where the app can check the place, it checks; where it cannot find it, it says what it restored, once, and puts you somewhere you can verify (the start of the line it was on), never somewhere else in silence.
3. **Kept through an interruption.** A clean close, closing the whole app, Windows signing out, and a crash, where the app can afford a periodic write.
4. **Nothing starts by itself.** A recovered recording or draft is not played, sent or published because it was recovered. Live radio is never offered as a seekable recording.
5. **A way back after a jump.** After Go To, a search hit, a heading, a link or a chapter jump, one command returns to where you were, said once.

## What the family already has

- **QUILL and QUILL Lite** keep each saved document's bookmarks and last cursor position in `DocumentMemory` (`quill/core/bookmarks.py`), one file per app. Bookmarks re-anchor by the text around them (`quill/core/bookmark_anchor.py`). Last session's documents reopen through the shared `quill/core/session_restore.py` and its window. **Alt+Left / Alt+Right** (Go Back, Go Forward) walk a per-window ring of jumps (`quill/core/locations.py`), recorded at one seam for Go To Line, headings, bookmarks and search hits.
- **Cast** keeps each episode's position in its library and writes it on pause, stop, switch and shutdown, and every 15 seconds while playing; the selected episode in each show is kept (`episode_cursor.py`).
- **Media Player** keeps a position per file (`quill/core/media/positions.py`), every 15 seconds and on close, and loads a file paused at it.
- **Radio** remembers the last station and the position in finite recordings; live audio goes back only through the timeshift buffer, which says how far behind live you are.
- **Studio** reopens the last book paused at its place, when asked to.
- **Social** keeps the reading position per timeline.

## The shared helpers

`quill/core/resume_place.py` is the one rule for putting the cursor back in a reopened document, used by QUILL and QUILL Lite:

- `anchor_if_saved(text, saved_text, position)` takes the text around the cursor, only when the text is what the file holds. While a document has unsaved changes, neither editor writes its place at all: the last place written is the one the file can confirm, and a place in text that is then discarded is one nothing can check.
- `resume_place(text, last, anchor)` finds the place again: still there, or moved because text above it changed, means the cursor goes to it and nothing is said. Gone means the start of the line it was on, marked `lost`; an emptied file stays at its start, which the reader already calls blank. No anchor (an older build) means the offset, as before.
- `lost_place_sentence(text, position)` is the one sentence for the lost case: "The text where you left off has changed. The cursor is at the start of line 42." Both editors say it when you arrive in that document or tab, `PLACE_NOTE_DELAY_MS` after the reader has said the window and the line, and without interrupting it: said while the window was still loading, the reader's own reading, the next document's load or another open notice cut it off, and in a session restore it would have been about a document you were not in.

`quill/core/media/jump_back.py` is the players' one place to go back to, used by Cast and Media Player: `JumpBack.before_jump(item, position, target)` notes the time a jump leaves (not for a nudge under two seconds, which the skip keys undo), and `back(item, position)` returns it and keeps where you are for the return trip, so pressing **Back to Where I Was** twice comes back. The place belongs to the episode or file it was in; another one forgets it. It is on **Alt+Left**, the key the editors' Go Back already uses, and says one sentence: "Back to 12 minutes 30 seconds."

`DocumentMemory` stores the anchor as `last_anchor` next to `last_position`, and now keeps any per-document key it does not know, so a newer build's fields survive an older one (GATE-DATAFMT). `bookmark_anchor.locate_anchor` is `resolve_anchor` plus whether the text was found; `resolve_anchor` is unchanged.

## App by app

| App | What is remembered | Where you land | The gap | What changed |
| --- | --- | --- | --- | --- |
| QUILL Lite | Open documents; each one's cursor and bookmarks; unsaved work in the recovery store | The last document to open, at its cursor | (1) The cursor was a bare offset: after another program edited the file it landed in a different sentence, silently. (2) Closing the whole app (Alt+F4 on the shell) or Windows signing out forgot the cursor in every open document: the shell's `Destroy` takes the windows down without their own close, and only that close wrote it (checked against wx). (3) A crash lost every cursor move since the window opened. (4) With several documents back, you landed in the last one numbered, not the one you were in | This pull request: the shared helper above; the shell writes each document's place on close, vetoable or not; each recovery copy also writes the cursor when it moved; `session_active_file` puts you back in the document you were in |
| QUILL | Open tabs; each one's cursor, bookmarks and inline notes; persistent undo | The tabs in order, the last one active | (1) as in QUILL Lite. Closing writes the active tab's cursor, and every other tab's was written when you left it, so (2) does not apply. (3) a crash loses the active tab's cursor since it became active. (4) the last tab, not the one you were in | This pull request: (1) through the same helper. (3) and (4) are left (below) |
| Cast | Episode position (pause, stop, switch, shutdown, every 15 seconds); the queue; the selected episode in each show | The launch place (configured, or "what is new"), first row | Go to Position and chapter jumps had no way back, and the 15-second checkpoint wrote the new time over the place you jumped from. Resume on launch plays the last episode, but only when turned on, and its own help says it "starts playing where you stopped as soon as Cast opens": the person asked for it, so it is not a recovered recording playing by itself | The Cast and Media Player pull request: **Back to Where I Was** (Alt+Left, Episode menu) after Go to Position, Next and Previous Chapter, and a chapter chosen in Now Playing |
| Media Player | Position per file (every 15 seconds and on close); loaded paused | The transport, with no file unless one was opened | A DAISY book never resumed. A book of several files saved the playing file's time under the first file's name, so reopening put you in track one at track four's time. A finished file kept saving near its end, so it reopened on the credits. Go to Position and chapter jumps had no way back | The Cast and Media Player pull request: Back to Where I Was (Alt+Left, File menu) after Go to Position and a chapter chosen in the tree; each file keeps its own place; DAISY resumes; within 20 seconds of the end counts as finished (the margin Radio's recordings use) |
| Radio | Last station; position in finite recordings; timeshift for live | The main list | Resume on launch, when turned on, plays the last station: that is what the setting asks for, and a live station is not a recovered recording. Live audio is never offered as seekable | None needed |
| Studio | Last book and its place, saved when the chapter workbench closes | The workbench, paused, when Resume Last Book is on | The place is written only when the workbench closes, so a crash loses it | Left (below) |
| Transcribe | Held and rescued words on disk; recent phrases for this run | The state text | Nothing that is a place to return to | None needed |
| Inkwell | Its list of snippets | The list, first row | The selected row is not restored; the list is short and reached by first letter | None needed |
| Converter | Format, preset, effect and chapter choices | The file list | The file queue is a task, not a place, and is not kept across restarts on purpose | None needed |
| Beacon | Window size and position | The search box | Scope, sort and selection reset; Beacon is not released | None now |
| Weather | Saved locations | Open Center | Nothing that is a place to return to | None needed |
| Social | Reading position per timeline (on switch, thread and close) | Home, all | A crash loses movement since the last switch; Social keeps its own model in `standalone/social` | Left, for Social's own work |

## Left, and why

- **QUILL's crash cadence and active tab.** QUILL writes the active tab's cursor on close and on save and every other tab's when you leave it, so only a crash in the middle of reading costs a place. A periodic write and an "active tab" field both belong in `main_frame.py` and QUILL's versioned settings groups, which is a change of their own; QUILL Lite, the pilot, has both.
- **A selection is not put back.** Only the cursor. A restored selection would be replaced by the first key typed, which is the opposite of returning to your work.
- **Studio's place on a crash** needs a periodic write in the chapter workbench, which has no timer today.
- **Social** and **Beacon**, as in the table.

## The acceptance list

- **The original passage and reading context are restored where supported:** the cursor returns to its sentence in QUILL and QUILL Lite, with bookmarks, and to the document you were in (QUILL Lite).
- **Missing or moved content stays visible and understandable:** moved text is followed silently; gone text is said once, with the line, and the cursor starts that line. A file that has gone is shown in the Reopen Last Session window as before.
- **Live radio is not represented as a seekable recording:** unchanged; see Radio.
- **A recovered recording or draft is not played, sent or published:** recovered drafts in both editors open as before, unsaved and unsent. Media Player and Studio load a book paused at its place. Cast and Radio play on launch only when their Resume on Launch setting, off by default, says to.
- **A way back after a jump, said once:** Alt+Left in QUILL and QUILL Lite (Go Back, unchanged) and now in Cast and Media Player (Back to Where I Was).
- **Observe time and wrong turns needed to resume:** a live check, listed in the pull request.
