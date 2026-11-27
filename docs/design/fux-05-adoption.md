# FUX-05: recovery that speaks in terms of the person's work

**Date:** 2026-11-24
**Feature:** FUX-05, "Recovery that speaks in terms of the person's work", from the family UX plan (read it with `git show b7c6a1a04^:complete2.md`). It is held to [family-interaction-contracts.md](family-interaction-contracts.md).
**Out of scope:** Earshot and the macOS apps.

The moment: "I changed the wrong thing, or the app closed. Can I get back?" A recovery offer is a question about somebody's work, so it has to say *which* work: "Your changes to chapter3.md, autosaved today at 2:14 PM, 1,200 words more than the saved file", not a file name, a temporary folder or an exception. Each answer says what it does to the work. Nothing is lost without being said. The offer is said once and reached from the keyboard.

No new recovery system was added. Every fix extends the recovery code the app already had.

## 1. The questions asked of every path

1. **Names the work.** The document, recording, conversion or draft by its own name, when its copy was made, and how much it holds or how it differs from what is saved. Not a hidden folder, a hash, a raw timestamp or exception text.
2. **Choices with consequences.** Can the person restore, keep both, or discard? Does each answer say what it does, and does a permanent deletion say it cannot be undone?
3. **Nothing lost silently.** Is any copy dropped, expired, skipped on an error or overwritten without a sentence saying so?
4. **Said once, reachable.** Is the offer made once (not every launch for the same thing), and can it be reached again from a menu, a list or a key after it is dismissed?

**Gap** marks a path that failed one of these before this work.

## 2. Inventory, app by app

### QUILL: unsaved documents after an unclean exit (first pull request)

| Question | Before | After |
| --- | --- | --- |
| Names the work | **Gap.** "Quill detected an unclean exit. Restore the latest autosave snapshot". The snapshot file is named by a hash of the path, so QUILL could not say which document it was. | Autosave writes one small note per document beside its snapshots, naming the file (`autosave._note_source`, `snapshot_source`). The offer says "QUILL closed without saving your work. Unsaved changes to chapter3.md, autosaved today at 2:14 PM: 1,200 words more than the saved file. It begins: ..." (`recovery_naming.offer_sentence`, `compare_with_saved`). A Word file is compared by date only; a copy from an older build with no note says "a document whose name was not recorded". |
| Choices | Restore Latest Snapshot, or Skip Recovery. After three skips the window said Skip would "discard it and continue with a blank document" and, a sentence later, that it would keep it; the button became "Discard and Continue", which deleted nothing. | **Restore Document** opens the copy as a new, unsaved document, and the sentence says the file on disk is not changed, so Save As keeps both. **Skip Recovery** says the copy stays in the autosave folder and is not offered again. The contradictory wording is gone. |
| Nothing lost silently | **Gap, twice.** Only the newest snapshot of the session was offered: a second modified document was never mentioned. And with no error in the log, as after a power cut or a forced close, nothing was offered although the copies were on disk. | One offer per document that left unsaved changes, newest first (`recovery_naming.snapshots_by_document`, `recovery._offers_for`). A copy identical to its saved file is not offered (nothing would come back), so a copy with changes no longer needs log evidence. Only a copy nothing can be said about (no note, or a Word file) still waits for an error in the log, as every copy did before. A copy that cannot be read says so by name, without the exception. |
| Said once, reachable | Once, at the launch after the exit. | Unchanged, now once per document: "Document 1 of 3", each in turn. The result is in Notifications. |

### QUILL Lite: unsaved documents (first pull request)

| Question | Before | After |
| --- | --- | --- |
| Names the work | Each row names the document, its folder, how it begins, its size and when it was written (`recovery_triage.row_label`). | Each row also says how the copy stands against its saved file: "2 words more than the saved file", "the same as the saved file", "the saved file is no longer there" (`recovery_triage.saved_comparison`, shared with QUILL). |
| Choices | Restore Checked, Restore All, Not Now, Discard Checked, Discard Everything (asks first), Never Offer Untitled, each described in **What this would do**. | **What this would do** also says each document opens under its own name, unsaved, that the file on disk changes only when saved, and that Save As keeps both. |
| Nothing lost silently | Tidying (duplicates, month-old copies, untitled by preference) is said. A failed restore leaves the copy and says so. | A failed restore no longer shows the exception text: "Could not restore your unsaved work in chapter3.md: its saved-aside copy could not be read. It stays saved aside and is offered again next time." |
| Said once, reachable | Once per launch; Not Now offers the same list next time. | Unchanged. |

### Quill Radio: recordings interrupted by a close or crash (second pull request)

| Question | Before | After |
| --- | --- | --- |
| Names the work | Station name, and the end time as a raw ISO string ("2026-11-24 21:00:00-05:00"). Leftover temp files: "Recovered 2 recording file(s)", a count only. | See the second pull request. |
| Choices | Resume / Skip, Don't ask again. Resume records the rest as a new file; the window did not say the part already recorded is kept. | See the second pull request. |
| Nothing lost silently | **Gap.** A marker past the 10-minute grace was cleared without a word. A failed resume showed the exception text. | See the second pull request. |
| Said once, reachable | Once, inside the grace window. | Unchanged. |

Radio's stream recovery (a station whose address moved) is not the person's work; it is noted in section 4.

### QUILL Studio: unfinished demonstration recordings and Chapter Workbench edits (second pull request)

| Question | Before | After |
| --- | --- | --- |
| Names the work | **Gap.** The Recover prompt listed each hidden work folder by path (`.studio-recording-<id>`), with no title, date or length; failures carried exception text and temporary paths. | See the second pull request. |
| Choices | Yes/No for all of them; no way to discard one. | See the second pull request. |
| Nothing lost silently | **Gap.** A recording whose check failed after its file was written came back next launch and produced a " (2)" copy. Chapter Workbench's Close discarded unsaved chapter and tag edits without asking. | See the second pull request. |
| Said once, reachable | **Gap.** The launch notice repeated every launch. Capture > Recover unfinished recordings reaches it. | See the second pull request. |

Studio has no project autosave; Resume Last Book reopens a book for playback only. Quill Cast keeps playback positions and resumes partial downloads; it holds no work of the person's to recover.

### Quill Transcribe, QUILL's Locked Dictation, Quill Converter and Scribe (third pull request)

| Path | Before | After |
| --- | --- | --- |
| Transcribe: dictated words not written | "2 dictated phrases were not written last time and are kept. Recent Phrases, Shift+F11, brings them back." Each row names its kind, time and words. | No gap; unchanged. |
| Transcribe: recordings queued for transcription | **Gap.** Exit asked nothing about a transcription running or waiting; the queue was lost without a word. | See the third pull request. |
| QUILL Locked Dictation: recordings awaiting review | "N dictation recording(s) await review" with a literal "(s)"; the State column showed internal codes; Discard deleted at once. | See the third pull request. |
| Converter: a conversion batch | **Gap.** "A conversion is still running. Stop it and exit?" said neither how many files were left nor what Stop removes. | See the third pull request. |
| Converter: Auphonic work waiting | Names the production, file count, when sent and where it saves; Ctrl+Alt+A brings it back. | No gap in naming. |
| Scribe: conversions left in flight | **Gap.** QUILL resumed them silently; QUILL Lite did not resume them at launch at all; signed out, waiting jobs were never mentioned. | See the third pull request. |

### GitHub Workbench drafts, Quill Beacon and Quill Inkwell (fourth pull request)

| Path | Before | After |
| --- | --- | --- |
| Workbench: unsent issue drafts | "Recovered a local draft for owner/repo. It has not been submitted." Not announced; no time or title. **Gap:** Workbench's New Issue never cleared the draft after the issue was created, so the next New Issue offered an already-created issue again. A damaged drafts file was overwritten. | See the fourth pull request. |
| Workbench: review drafts and pending line comments | The review draft names the HEAD by 12-character SHA; line comments are named by place and first line. | See the fourth pull request. |
| Beacon: Sync History rollback | **Gap.** Snapshots listed as `sync_1732456789012.db`; the rollback could not itself be undone. | See the fourth pull request. |
| Inkwell: the abbreviation library | **Gap.** A damaged library silently fell back to the built-in list, which was later saved over it. | See the fourth pull request. |

## 3. Acceptance, from the proposal

- **The proposed recovery names what will change and what cannot be restored.** QUILL's offer names the document and says the file on disk is not changed; Skip says the copy is not offered again.
- **Local edits preserve ordinary undo grouping and selection.** Restoring opens a document; no undo history is touched. QUILL still puts the caret where it was in the document that was in front.
- **Recoverable drafts and original files are distinct from disposable caches.** A restored copy opens unsaved beside the file (QUILL) or under its name, unsaved (QUILL Lite); neither writes the file until the person saves.
- **Destructive or remote actions are not labelled undoable until recovery is verified.** "Discard and Continue", which discarded nothing, is gone.
- **Review ambiguous duplicates instead of silently declaring one copy worthless.** Only byte-identical copies are folded, and that is said. A copy identical to its saved file is not offered; one that differs by a single word is.
- **Include failures during undo and recovery.** A copy that cannot be read is named, stays where it is, and the person is told.

## 4. Left for later

- QUILL asks about each document in its own Crash Recovery window. QUILL Lite's chooser, one list with checkboxes, is the better shape for many documents; moving QUILL onto it means moving the diagnostics buttons too, and was left to keep this change small.
- A copy Skip Recovery leaves in QUILL's autosave folder is kept for the "Days of unsaved work to keep" setting but can only be opened from that folder. A "recover an earlier session" command would reach it.
- Radio's stream recovery rewrites a favourite's address when the station has moved. That is not the person's work, but it changes something they saved without asking; it is noted for the Radio owners.
- Quill Social's drafts (standalone) are saved only when you press Save Draft. Restoring one keeps only its text, and Delete does not ask. It is outside this family pass because Social's composer is being rebuilt.
- To check by hand with a screen reader in a frozen build: QUILL after a power cut with two documents changed (two offers, each named), QUILL Lite's row wording, and every second- to fourth-pull-request path listed in its own pull request.
