# FUX-12: compare changes in a way people can inspect, app by app

**Date:** 2026-11-24
**Source:** FUX-12 in the family UX plan (`git show b7c6a1a04^:complete2.md`), held to [family-interaction-contracts.md](family-interaction-contracts.md). It is not one of the promoted pilots ([2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md), section 5), so the work here is limited to gaps in comparisons the family already has. It adds no new viewer, panel or history centre.

## The questions asked of every surface

For each place in the family that shows a change, can a screen-reader user:

1. move change by change, from the keyboard;
2. hear what changed: added, removed or changed, with the old and the new text;
3. know how many changes there are and where each one is;
4. act on one change (keep mine, take theirs) without taking or losing the rest;
5. read it in braille, as lines of text, never as colour or layout alone?

## What the family already has

- **QUILL's compare engine** (`quill/core/compare_service.py`): difference groups, each with "Difference 2 of 5", its kind, its line and, for a one-line change, the words that changed. The editor's Compare dialog (`quill/ui/compare_dialog.py`) walks them with F8 and Shift+F8.
- **Kelly Ford's line marks** (`quill/core/diff_marks.py`): every changed line is written as a line of text whose first word says what happened to it ("Added:", "Removed:", or the symbol styles), in the one Diff Line Marks style the person chose. Every diff view in the family uses it, so no change is ever shown by colour alone.
- **The review of a proposed text** (`quill/core/ai/diff_review.py` and `quill/ui/ai_diff_review_dialog.py`, the AI's Review Changes): a check box for each change, its old and new lines and the words that differ in a details box, single word edits that can be kept or dropped, and Apply Checked as one undo step. This is the family's one way to act on a single change, and the fixes below reuse it rather than build another.
- **The Workbenches' previews**: WordPress and GitHub write nothing without a preview that names each change in words, line by line, and an undo where the site allows one.

## Surface by surface

| Surface | Today | The gap | What changed |
| --- | --- | --- | --- |
| QUILL Compare with File (`compare_dialog.py`, `main_frame_compare.py`) | Every difference in a list, "Difference 2 of 5" and its line; F8, Shift+F8 and Ctrl+F8; the lines in the details box with their marks | 4: nothing could be taken from the other file. Ignore trailing whitespace and Ctrl+Shift+F8 only flipped the box; the comparison and its count stayed the same | **Take Changes** (Alt+T) opens the shared review of the same two texts, and only the checked differences go in, as one undo step. It refuses when the document changed after the compare, leaves out a whitespace-only line when Ignore trailing whitespace is checked, and is not offered for a read-only document (the window says so). The whitespace box compares again and says the new count |
| QUILL Compare Open Documents | The same walk through every open document, by key | 4, by design: it compares several documents at once, so there is no single "theirs" | None: Compare with File is the two-text compare, and it now takes changes |
| QUILL Restore Previous Version (`main_frame_restore_points.py`) | Restore the whole version, or open it as a copy | 1 to 4: no way to hear what a version has that the current text does not, or to bring back one paragraph without restoring all of it | **Compare...** (Alt+M) opens the Compare dialog on the current text and the chosen version, so Take Changes brings back only what is checked. Left: closing Compare goes back to the editor, not to the list of versions |
| QUILL's AI Review Changes | The model above | None | Its window now takes the opening sentence from the caller, so Take Changes can reuse it; its list help no longer says "the AI" |
| QUILL Lite Browse Backups | Open or restore a whole backup | As Restore Previous Version | Left: QUILL Lite has no compare yet, and QUILL Lite may be behind QUILL but never ahead. It can take the same two pieces when it gains Compare |
| WordPress Compare with Site (both editors) | A report of every run of changes in the Diff Line Marks style, with a summary that counts the lines and places | 1 and 3: the report is one long text; a run says where it is ("Lines 10 to 15:") but not which of how many, and the only way to the next one is line by line | M12 group 2: F8 and Shift+F8 in the report move to the next and previous change and say "Change 2 of 4" with where it is |
| WordPress Previous Versions (editor) | A list of the site's revisions and your local versions; View shows a version's full text; Restore | 2: a version is read whole, never against your copy | Left: Earlier Versions on a Workbench row already compares a version with the item, line by line in words (`workbench_item_versions.compare_lines`), and the editor's Compare with Site covers the current one |
| WordPress Workbench: Make Them the Same, snapshots, Earlier Versions | Choose the winning version by name and sites; a preview of every site's change in words; Put Back from a Snapshot previews before it writes; undo where the site allows | None: each change is a line of words with the site it is on | None |
| GitHub pull request diff and Compare Branches (`github_pr_diff_dialog.py`, `github_compare_branches_dialog.py`) | One row per file; the file's differences through QUILL's compare engine ("Difference 2 of 5. Text changed at line 41."), with marks | 1: inside a file the differences are one long text, read line by line | M12 group 2: F8 and Shift+F8 move to the next and previous difference in the text, and say which one of how many |
| GitHub Compare Configuration (`github_config_compare_dialog.py`) | A check box for each file to update, and the selected file's unified diff | 1 and 3: as above, and the diff is not marked in the Diff Line Marks style | M12 group 2: the same walk |
| GitHub Workbench pull request review | Each line of the diff a row, in the reading order of the chosen marks, with comments on a line | None: rows already move one line at a time and say their mark | None |
| GitHub Workbench across repositories | Compare and propose updates across many repositories | Not audited here | Left: GH-R-150 (#2013) is changing these files |
| Studio Chapter Workbench, AI title proposals | The proposals replace every title in the list; Restore Original undoes them all | 2 and 4: the list reads only the new title, so a person cannot hear what it replaced, and cannot keep some proposals and refuse others | M12 group 3: the proposals open in the shared review, one check box for each chapter whose title would change, "Changed Track 3 to The Storm at chapter 3", and only the checked titles go into the list |
| Beacon Sync History conflicts (`beacon/dialogs.py`) | Use Local, Use Remote and Use Merged for the selected conflict | 2: the row says only the beacon, the field and a message, so a person chooses a version without hearing either | M12 group 3: the selected conflict's two versions are shown below the list as marked lines, this device's against the other's |
| Converter outputs | Every file's result, kept in Activity (FUX-04, FUX-10) | No before and after text to compare | None: a conversion's losses are part of its result, which FUX-04 covers |
| Social drafts | Drafts are edited in the composer | No compare surface: the AI writing proposals (`services/ai/writing.py`) are not reachable from any window yet | Left: when a proposal is shown, it should open in the shared review rather than a new window |
| Earshot, macOS | | Out of scope for this work | |

## Acceptance

- **Preserve original and proposed versions until the person decides:** Take Changes reviews the two texts that were compared and changes nothing until Apply Checked; Reject All leaves the document as it was. A restore point is only read. Studio keeps the original titles until the person applies the checked proposals.
- **Repeated playback compares the same region:** N/A. No audio comparison is part of this work; the audio previews are FUX-08's.
- **Explain level matching:** N/A for the same reason.
- **Text changes have changed-item navigation and source references:** the Compare dialog, the reviews and (group 2) the read-only diff texts move difference by difference and say which one of how many and the line it is at.
- **State format loss, omissions and uncertain judgments plainly:** the review says when a change is spacing or punctuation only, and Take Changes says when it could not take anything because the document changed.
- **"Keep this" applies exactly the reviewed result:** Take Changes applies the reviewed texts or nothing; it never compares again behind the person's back.

## Interaction contracts

- Keys: Alt+T (Take Changes) and Alt+I (Ignore trailing whitespace) are new access keys inside the Compare dialog; Alt+M (Compare...) is new in Restore Previous Version, a different window from the Compare dialog's Mark lines as. GATE-14 checks each window.
- Speech: the new count after a whitespace change is said once, because it changed on controls that do not have focus. Moving through a list says nothing extra.
- Nothing new is added to a menu, and no new window: the review is the existing one.
