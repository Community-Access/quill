# FUX-16: a problem becomes a next step you can take

**Date:** 2026-11-24
**Source:** FUX-16, "Turn a problem into a recoverable next step", in the family UX plan (`git show b7c6a1a04^:complete2.md`), held to [family-interaction-contracts.md](family-interaction-contracts.md). It is not one of the promoted pilots ([2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md), section 5), so the work here is limited to the failure messages people meet most. It improves their words and buttons; it adds no error centre, panel or framework. Earshot and the macOS apps are out of scope. Recovery after a restart belongs to M6, and live and cached states to M13; this work stays out of both.

The moment: "Something failed. I don't know whether to retry or start over."

## The rule every failure message follows

A failure message says four things, in this order, and offers one button for the most useful next step:

1. **What did not happen**, naming the file, the station, the account or the task: "Could not open notes.txt."
2. **Why, in plain words**: "The disk is full." Never the exception's own text, a stack, an error number or a code. Those are for whoever fixes the fault, so they are behind **Show Details** and **Copy Details**.
3. **What was kept**: "Nothing was opened." "Your text is still open and unsaved." "Your copy is kept on this computer; nothing was published."
4. **The one next step, as the default button**: Retry, Choose Another File, Save As, Sign In Again, Open Settings. Close is the other way out. It has no access key, because Escape is Close (GATE-14).

The kind of failure decides the step, so the four kinds the plan names are told apart:

| Kind | Example sentence | Next step |
| --- | --- | --- |
| Something that passes (network, a busy service, a locked file) | "The connection failed or timed out." | Retry, when trying again cannot do anything twice |
| A denied permission or an expired sign-in | "The sign-in was not accepted, or it has expired." | Sign In Again, or Save As somewhere else |
| A missing part or device | "A part this needs is not installed." "The device is not connected or not ready." | Open Settings at the right page, or Choose Another File |
| Something the app cannot do | "This file or request is not one it can handle." | Choose Another File |

**Retry is never offered where it could repeat a remote action.** Opening, loading and checking change nothing, so they can be retried. Publishing, posting, sending and creating are not retried from a failure box. WordPress already checks whether a send landed before it offers Try Again, and that stays the model.

**Copy Details sends nothing.** The details are the app and its version, Windows, what was happening, the kind of failure and the error's text, all passed through the crash-report redaction (`redact_text_for_bundle`, then the Windows user name). The document is never included. The details field can be edited before copying, so a person can take out anything they do not want to share.

**After the next step, the result is said as it happens.** Retry opens or loads again and its own result is reported, so dismissing the box is not mistaken for recovery. Focus goes to what the step opens (the Open or Save As dialog) or back to where it was.

## The shared pieces

- `quill/core/command_failure.py` (wx-free, strict-typed): `plain_failure(error)` returns the kind and the plain sentence. It reads `errno`, the Windows error number and an HTTP status, and matches library classes such as requests' `ConnectTimeout` by name, so core imports no network library. A coded error keeps its own authored words, without the bracketed code, plus its hint; a coded error wrapping a full disk is a full disk. `failure_details(...)` builds the redacted text. `save_failure_sentence(...)` is the one set of save-failure words for both editors, so QUILL Lite is no longer behind QUILL.
- `quill/ui/next_step_box.py`: `show_next_step(...)` shows the box. The message, then the next-step button (default and focused), Show Details, Copy Details and Close. Every control has F1 help. It goes through the host's `_show_modal_dialog` where there is one, so focus returns to the control that was in use.
- Existing pieces are reused, not replaced: Recent Problems (`problem_log`) and its retry-by-kind, the Activity window's Retry and Open Folder, `persistence_reporting` for settings writes, WordPress's `plain_error`, GitHub's `github_exception_hint`, Cast's `feed_problems`, Radio's `recording_outcome` and `browse_failure`.

## Inventory

"Box" is a modal message, "spoken" is an announcement only. **Gap** marks a message that broke the rule before this work. The last column says which pull request fixed it, or why it was left.

### QUILL and QUILL Lite (the editors)

| Message | Before | After | Done |
| --- | --- | --- | --- |
| QUILL: a background open fails (Word, PDF, large or remote file) | **Gap**: box, OK only, whose main text was `str(error)`; a "What to try next" toggle with general advice | "Opening a.docx did not finish. Windows did not allow it... Nothing was opened." Retry is the default; a file that has gone offers Choose Another File. Details behind the buttons | PR 1 |
| QUILL: any other background task fails | **Gap**: box, OK only, the whole text `str(error)` | The same plain sentence. Reading tasks (Loading, Checking, Looking for, Previewing) offer Retry; tasks that change something (rebase, delete, switch branch) offer no Retry | PR 1 |
| QUILL: a save fails | Disk full, read-only and encoding had good words, but OK only. **Gap**: anything else was "Could not save notes.md: [Errno 5] ...", without saying the text was kept | Every case says "your text is still open and unsaved". Save As is the default button. The error is behind Copy Details | PR 1 |
| QUILL Lite: an open fails (small file, large file, Word, mode not available) | **Gap**: box, OK only, "Could not open notes.txt." then the raw exception. The large-file path asked "Try again?" with the raw text | "Could not open notes.txt. [plain reason] Nothing was opened." Retry, or Choose Another File when the file is gone | PR 1 |
| QUILL Lite: a save fails (text, rich text, Word) | **Gap**: box, OK only, raw exception, never said the text was kept, none of QUILL's disk-full or read-only words | QUILL's words, from the same function, and Save As | PR 1 |
| Ask Quill: the AI provider returns an error | **Gap**: "Error: {provider text}" in the conversation and spoken | Plain first: a refused key says where to fix it (the AI Hub or Choose Your AI); a rate limit says wait, then send again; no connection says check it. "Your document was not changed." The provider's text stays at the end of the conversation entry as "Details:", and is not spoken | PR 1 |
| QUILL: the hosted AI chat fails | Plain sentence, "Nothing was sent and nothing was used", Send stays enabled | Unchanged: already meets the rule | No gap |
| QUILL: a settings or history write fails | Activity with Retry and Open Folder, "Your changes stay in use for this session" | Unchanged: already meets the rule | No gap |
| QUILL: a command raises (status bar) | `describe_command_failure`, on the status bar | Unchanged: the status bar is a trace, not the message a person must act on; the command's own handler reports its result | Left |

### Converter, Scribe, Transcribe and Dictate

| Message | Before | After | Done |
| --- | --- | --- | --- |
| Converter: reading or downloading a link fails | **Gap**: box, OK only, "{label} failed." then the raw error | Plain reason, "Nothing was added to the queue", Retry, Copy Details | PR 2 |
| Converter: a playlist or channel cannot be read | **Gap**: the bare `str(error)`, spoken and on the status bar | Plain sentence naming the link and what was kept | PR 2 |
| Converter: Join fails; Chapter Workbench cannot read the book | **Gap**: raw text; the second an OK-only box with an information icon | Plain words; the Workbench box offers Choose Another File | PR 2 |
| Converter: a batch finishes with failures | Spoken sentence names the files; the report has translated FFmpeg reasons; Activity offers Retry and Open Folder | Unchanged | No gap |
| Converter: FFmpeg missing | Names the fix (Help > Get FFmpeg) | Unchanged in words | Left: a button for Get FFmpeg is a new action in that box, a candidate for later |
| Scribe: a background request fails with an exception that is not a Scribe error | **Gap**: "Scribe: {raw}" spoken | Plain reason; Scribe's own sentences were already plain | PR 2 |
| Scribe: QUILL cannot read the file Scribe made | **Gap**: "...but QUILL could not read it: {error}" | Plain reason, and the file is named as kept on disk | PR 2 |
| Scribe: a conversion fails; sign-in ends; offline | Plain sentences, Retry in the Conversions window, "paused until you sign in again" | Unchanged | No gap |
| Dictation cannot start | **Gap**: "Dictation could not start: {raw}", and the microphone and privacy hint written for this case was never spoken | Plain reason plus the hint | PR 2 |
| Dictation: the model is not on this computer | Says the three ways out, error sound, no button | Unchanged: the sentence names the Model Library, and dictation start is not a box | No gap |
| Model download fails on a full disk or an unwritable folder | **Gap**: an OSError that was not wrapped could reach the person as the bare text or an error number | Plain reason, "files that already arrived whole are kept" | PR 2 |

### Quill Cast and Quill Radio

| Message | Before | After | Done |
| --- | --- | --- | --- |
| Cast: a feed cannot be checked | Plain sentence, Recent Problems with Retry | Unchanged | No gap |
| Cast: a download fails on a full disk | "The disk is full ({free}). Free some space...", Recent Problems with Retry | Unchanged | No gap |
| Cast: a transcript, chapters, audio processing or OPML export fails | **Gap**: spoken and recorded with the raw error | Plain reason in the sentence; Recent Problems keeps it | PR 3 |
| Radio: a recording cannot start (folder cannot be made, disk full) | **Gap**: spoken only, "[QUILL-RADIO-RECORDING-FAILED]" and the raw OSError, not in Recent Problems | Plain reason and the setting to change; recorded in Recent Problems | PR 3 |
| Radio: a scheduled recording cannot start | **Gap**: raw error in the spoken sentence | Plain reason | PR 3 |
| Radio: a station cannot be reconnected | Plain sentence, Recent Problems with Retry | Unchanged | No gap |
| Radio: a capture saved nothing; ended early | Mapped reason, "No file was kept", Activity with Open Folder | Unchanged | No gap |
| Radio: the chosen output device cannot be opened | Says the fallback device | Unchanged | No gap |
| Radio: a backup cannot be restored | **Gap**: box with the raw error | Plain reason, "nothing was changed" | PR 3 |
| Radio: YouTube connect fails | **Gap**: raw error spoken | Plain reason | PR 3 |

### Quill Beacon, GitHub Workbench and WordPress

| Message | Before | After | Done |
| --- | --- | --- | --- |
| Beacon: Sync Now fails | **Gap**: box, OK only, "sync failed (local state intact): {raw requests error}"; an expired sign-in looked like a network failure | Plain reason. An expired sign-in offers Sign In Again; a network failure offers Retry (sync re-runs from the commit log, so nothing is pushed twice). "Your beacons on this computer are unchanged" | PR 4 |
| Beacon: the sign-in link cannot be sent or verified | **Gap**: box, OK only, "verify failed: {raw}" | Plain reason; an expired link says to ask for a new one | PR 4 |
| Beacon: a bookmark file cannot be imported, a feed cannot be fetched, an attachment cannot be opened | **Gap**: box, OK only, raw error | Plain reason and what was kept | PR 4 |
| GitHub Workbench: a view cannot load | **Gap**: "Could not load Issues: [QUILL-GITHUB-ITEMS-ERROR] ... 401 {json}"; a 401 or rate limit on a list skipped the sign-in hint | Plain reason with the hint (sign in again, wait for the rate limit); F5 tries again | PR 4 |
| QUILL Lite: GitHub Workbench cannot start | **Gap**: box, OK only, raw text with the code | Plain reason | PR 4 |
| WordPress: Publish or Update refused for sign-in, role or server | **Gap**: spoken only; did not say the copy was kept or that nothing was published | "Your copy is kept on this computer; nothing was published." | PR 4 |
| WordPress: Connect fails; the site cannot be reached while publishing | Reopens Connect with the answers kept; checks whether the send landed before offering Try Again | Unchanged: the model the rest follows | No gap |

## Acceptance, from the proposal

- **Preserve work before offering retry, another destination or export.** A failed save keeps the text open and says so, and offers Save As. A failed open leaves the window as it was. Retry is only offered for reads.
- **No "try again" where a retry could duplicate a remote action.** Writes and sends are never retried from a failure box. WordPress's check before Try Again is unchanged.
- **A support report can carry versions and error context without private content.** Copy Details: app, version, Windows, what was happening, the kind and the error, redacted, never the document.
- **The person can inspect, edit and copy the report without sending it.** Show Details reveals an editable field; Copy Details copies what is in it and says "Details copied. Nothing was sent."
- **Unsupported, denied, unavailable and passing failures are told apart.** `plain_failure` gives each its own sentence, and the button follows the kind.
- **Focus returns to a useful control after recovery.** The box goes through the host's modal path; the next step opens its own dialog or runs again.
- **Recovery is confirmed, not only dismissed.** Retry and Save As report their own outcome as usual.

## Left for later

- A Get FFmpeg button in Converter's FFmpeg-missing box, and a Model Library button in Transcribe, would each be a new action in an existing box. Both sentences already name the menu path.
- QUILL's status-bar trace of a failed command (`describe_command_failure`) keeps the raw text; it is a trace for support, not the message a person acts on.
- The Studio and Player boxes that show `str(error)` (capture, demo and launch) were not in the most-met set and are left for the Studio release work.
- To be checked by hand with a screen reader in a frozen build: the box reads its message on opening, Retry is the default, Show Details moves focus to the details, and Copy Details is heard once.
