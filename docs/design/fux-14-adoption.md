# FUX-14: navigate meaningful structure, app by app

**Date:** 2026-11-23
**Source:** FUX-14, "Navigate meaningful structure, not just distances", in the family UX plan (`git show b7c6a1a04^:complete2.md`), held to [family-interaction-contracts.md](family-interaction-contracts.md). It is not one of the promoted pilots ([2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md), section 5), so the work here is limited to gaps in structure the family already has. It reuses each app's chapters, bookmarks, headings and lists, and their key conventions. It adds no new outline, tree or panel. Earshot and the macOS apps are out of scope.

## The rule every move follows

A structural move says where it landed **once**: the name of the thing, what kind of thing it is, and its place in the whole. A structure the app worked out, rather than one a person published or placed, says "estimated". A move past the end says so and leaves you where you are.

> Interview with the author, chapter 3 of 12.
> The news, chapter 2 of 5, estimated.
> The storm starts, bookmark 1 of 4, 12 minutes 5 seconds.
> This is the last chapter.

The sentence is `quill/core/structure_landing.py` (`describe_landing`, `describe_boundary`). Quill Radio had already said its chapters this way; the module gives that sentence a name, so the other apps say it too. Which chapter sources count as estimated is `quill/core/podcasts/chapter_scoring.py` (`ESTIMATED_SOURCES`, `is_estimated`): the transcript, the silence scan and the show-notes running order matched to the audio. Published, file and edited chapters are not estimated.

At the start of the first chapter, Previous says "This is the first chapter." rather than replaying it as if it had moved; further in, it restarts the chapter, as every media player does.

Only the move the person asked for is announced. Playback that crosses into a new chapter on its own keeps the existing once-per-chapter latch, and a list that has focus is left to the screen reader, which already says the row it moved to (GATE-13).

## What the family already had

- **QUILL** moves by heading (Ctrl+Alt+H, with level and "3 of 12"), bookmark (F2), highlight (Alt+PageDown), inline note (Alt+Shift+J), section fold (Alt+Shift+]), table cell (Ctrl+Alt+arrows, "Row r of R, column c of C"), problem, indent, misspelling (Ctrl+F7) and region (F6). Browse mode (Ctrl+Shift+Grave, then N) adds single letters for heading, heading level, link, list, list item, table, quote, code block, page, paragraph and sentence. The caret cue (`StructureAnnouncer`) and the page latch say a boundary once.
- **QUILL Lite** has the same chords for headings, sections, table cells, bookmarks, highlights, inline notes, misspellings and code, with no browse mode.
- **Quill Radio** moves by chapter (Ctrl+Shift+. and Ctrl+Shift+,), by song in the time-shift buffer (Alt+Shift+Right and Alt+Shift+Left), by Lineup or playlist item on the chapter keys, and back to live (Ctrl+Shift+L).
- **Quill Cast** moves by chapter (Ctrl+Alt+Right and Ctrl+Alt+Left) and by queue item (Ctrl+Alt+Down and Ctrl+Alt+Up).
- **Media Player and QUILL Studio** share one player panel with Previous and Next chapter buttons, the Winamp B and Z keys in the Player, and a Chapters tree with DAISY levels.
- **GitHub Workbench** moves by unread row (Ctrl+. and Ctrl+Shift+.). Group By makes each group a tree node with its count, so F6 to the tree and Up or Down moves by group.
- **Quill Social** moves by pane (F6), by search match (F3, "3 of 12") and by read-aloud article (Ctrl+Shift+. and Ctrl+Shift+,); Open Conversation (Ctrl+G) shows a thread.

## App by app

| App | Structure today | Only by distance, or a gap | Done |
| --- | --- | --- | --- |
| QUILL | Headings, levels, lists, tables, links, footnote insertion, pages, bookmarks, notes, highlights; browse letters | Alt+Down (Next Structure) said only "Moved to next structure"; browse-mode heading levels said the level and line but not the title. Footnotes, comments and tracked changes are detected on import but not kept as structure, so there is nothing to move through | #2044 |
| QUILL Lite | The shared chords; Go To (Ctrl+G) lists headings, pages and the PDF outline | No browse mode and no next/previous link, list, table, page or sentence. Lite is behind QUILL here, never ahead | Left: adding browse mode to Lite is its own piece of work, not a gap fix |
| Quill Radio | Chapters, songs, Lineup and playlist items | Next Chapter in the last chapter jumped back to its start and announced it as a move. The chapter keys read only published chapters, while the Chapters list also found the file's marks and Cast's worked-out ones, so the list offered chapters the keys said did not exist. "This video has no chapters." was said for episodes and files | #2043 |
| Quill Cast | Chapters, queue items | Chapter moves said "Chapter: title" with no place. Previous Chapter never restarted the current chapter: twenty minutes into chapter 1 it said "Already at the first chapter". Worked-out chapters were not told apart on landing | #2043 |
| Media Player | Chapters (buttons, B and Z, tree), bookmarks list | Bookmarks only through the list (Ctrl+Alt+M, arrow, Enter), and choosing one said only the time. The arrow seeks said the time twice. Previous that restarted the chapter, or Previous on chapter 1, said nothing | #2043: Next and Previous Bookmark on F2 and Shift+F2, the editors' keys |
| QUILL Studio | The shared player panel; the Chapter Workbench list | The same panel fixes as the Player. Recording markers are written to a sidecar only the picture-video dialog reads, and silence ranges become proposed chapters directly | #2043 for the panel. Left: a marker list needs a place to show it, which is Studio's recording work |
| Quill Converter | Chapters through Studio's Chapter Workbench (Ctrl+H) | None of its own: the queue is files, and chapters are edited in the Workbench | None needed |
| Quill Transcribe | Paragraph start times and diarized speaker turns, flattened to text in Review Transcript | No next/previous segment or speaker, and nothing marks a time as measured or estimated | Left: Review Transcript is a read-only text box, and turning it into a list of segments is Transcribe's review work |
| Quill Inkwell | Abbreviations and lists | No document structure | None needed |
| Quill Beacon | Episode chapters in the player's list | The chapter list's name promised "N next, P previous", and no key did either. The 30 seconds forward button skipped 15 | #2045 |
| Quill Social | Panes, search matches, conversations, unread counts on folders | No next or previous unread post | #2045 |
| Quill Weather | Alerts, periods, hourly and daily lists, each with a detail field | Rows are few and each list is one mnemonic away | None needed |
| GitHub Workbench | Unread rows, groups as tree nodes | Covered: groups are tree nodes, and the Workbench frame is being reworked in parallel | None needed now |

## Keys

New keys were chosen only after checking `keymap.DEFAULT_KEYMAP`, `APP_KEYMAPS`, the QUILL Lite command table, `quill/core/data/family_menu_chords.json` and the screen-reader keys (NVDA and JAWS use Insert or Caps Lock with these, never plain F2).

| App | Command | Key | Why this key |
| --- | --- | --- | --- |
| Media Player | Navigation > Next Bookmark, Previous Bookmark | F2, Shift+F2 | Next and Previous Bookmark in QUILL and QUILL Lite; nothing in the Player claimed them |
| Quill Beacon (player window) | Next Chapter, Previous Chapter | Ctrl+Shift+Period, Ctrl+Shift+Comma | Quill Radio's chapter keys. Plain N and P, which the list's name had promised, would have taken type-ahead from the chapter list |
| Quill Social | Item > Next unread, Previous unread | Alt+Period, Alt+Comma | The GitHub Workbench's Ctrl+Period pair could not be used: its Previous, Ctrl+Shift+Period, is Listen > Next article in Social, and Ctrl+Alt+Period is AltGr+Period, which types a character on some European layouts. Punctuation is never a menu letter, and no screen reader uses Alt+Period or Alt+Comma |

## Acceptance (from the plan)

- **Available structure is navigable and announced with name, type and position:** `describe_landing` in every app above that moves by chapter or bookmark.
- **Next and previous keep the expected playback behaviour:** Previous restarts the current chapter after its first three seconds in Radio, Cast, the Player and Studio; Next in the last chapter stays put.
- **Timed evidence is told apart from estimated alignment:** worked-out chapters say "estimated". Transcribe is left, above.
- **Navigation after edits:** chapters and bookmarks are read fresh on each press, so an edited list is what the next press moves through.
- **No established key is reassigned silently:** the only new keys are in the table above, and no existing chord changed.
- **Readable lists accompany visual timelines:** the family has no waveform view; Studio's sections dialog says so and uses list rows.
