# Section — File menu (`file.*`, 29 commands)

Everything about getting documents **in and out** of QUILL: new, open, save, close,
print, and the remote/GitHub/SSH ways of doing the same. Finish **Part 0** first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `file.*`. Read §2–§3 of `README.md` for
the scenario layout and the Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible
boxes.

Common inputs used below (copy the `../qa-samples/` folder onto the machine first):
`plain.txt`, `formatting.md`, `table.md`.

---

## FILE-01 — New File (`file.new`, Ctrl+N)

*What & why.* Start a blank document. The everyday "give me a fresh page."

**Before you start**
- QUILL open, any state.

**Do this**
1. Press **Ctrl+N**, or open **File menu (Alt, F) ▸ New File**.

**You should see and hear**
- A new empty document opens with focus in the editor; the title bar shows an
  untitled/new document. If a document with unsaved changes was open, it is **not**
  disturbed (the new one opens alongside or as a fresh buffer per QUILL's tab model).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-02 — Open File… (`file.open`, Ctrl+O)

*What & why.* Open an existing document from disk.

**Before you start**
- The `../qa-samples/` folder on disk. You will open **`formatting.md`**.

**Do this**
1. Press **Ctrl+O**, or **File menu ▸ Open File…**.
2. In the file dialog, navigate to `qa-samples` and select **`formatting.md`**;
   press **Enter**.

**You should see and hear**
- The file dialog is keyboard-navigable and announced. On confirm, `formatting.md`
  opens; focus lands in the editor (announced as a multi-line Document/text area);
  the title bar reads **`formatting.md`** with **no** modified marker.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-03 — Save (`file.save`, Ctrl+S)

*What & why.* Write the current document back to its file. On a never-saved
document this becomes Save As.

**Before you start**
- Open `plain.txt`, then type one extra word so there is an unsaved change.

**Do this**
1. Press **Ctrl+S**, or **File menu ▸ Save**.

**You should see and hear**
- The save is confirmed aloud; the title bar's **modified marker disappears**. No
  dialog appears for an already-named file. A second **Ctrl+S** with no new change
  saves silently or reports "no changes" — never errors.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-04 — Save As… (`file.save_as`, Ctrl+Shift+S)

*What & why.* Write the document to a new name and/or a different format, converting
faithfully. This is the fidelity promise (headings, lists, links, tables survive).

**Before you start**
- `formatting.md` open. Target names: **`formatting.docx`** (Word) and
  **`formatting.html`** (HTML).

**Do this**
1. Press **Ctrl+Shift+S**, or **File menu ▸ Save As…**.
2. Change the file type to **Word Document**, name it **`formatting`**, press
   **Enter**.
3. Repeat, choosing type **HTML**, name **`formatting`**.

**You should see and hear**
- A converting-Save-As is announced in substance: "Saved as formatting.docx, Word
  format. You are still editing QUILL text; each save converts it to Word." The
  title bar updates; a follow-up **Ctrl+S** saves without a dialog.
- Opening `formatting.docx` in Word: six heading styles H1–H6, real bullet and
  numbered lists, a live **QUILL project** hyperlink, image alt "Red circle", and
  bold/italic/underline/strikethrough on the right words. `formatting.html` opens in
  a browser with an `<h1>`…`<h6>` outline, `<ul>`/`<ol>`, `<blockquote>`, a
  `<pre><code>` block, the `<a href>`, and `<img alt="Red circle">`.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-05 — Save As Plain Text… (`file.save_as_plain_text`)

*What & why.* Flatten to `.txt`, telling you first what rich content will be lost —
never a silent drop.

**Before you start**
- `formatting.md` open (it has links, an image, styles that plain text cannot hold).

**Do this**
1. **File menu ▸ Save As Plain Text…** (or Command Palette → "Save As Plain Text").
2. Name it **`formatting`**; confirm.

**You should see and hear**
- Before writing, QUILL tells you what will be dropped (per the Links-in-plain-text
  setting) and lets you cancel. On confirm, a `.txt` is written containing the text
  content only. Nothing is dropped silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-06 — Save All (`file.save_all`)

*What & why.* Save every open document at once.

**Before you start**
- Two documents open, each with an unsaved change (e.g. `plain.txt` and a new file
  already named).

**Do this**
1. **File menu ▸ Save All** (or Command Palette → "Save All").

**You should see and hear**
- All modified documents are saved; QUILL announces how many were saved. Any
  never-named document prompts for a name (Save As) rather than failing silently.
  Modified markers clear on the saved tabs.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-07 — Close Document (`file.close_document`, Ctrl+W)

*What & why.* Close the current document, guarding unsaved work.

**Before you start**
- A document open with **one unsaved change**.

**Do this**
1. Press **Ctrl+W**, or **File menu ▸ Close Document**.
2. In the guard prompt, choose **Cancel** first (hear it), then repeat and choose
   **Don't Save** / **Save** as appropriate.

**You should see and hear**
- With unsaved changes, a **spoken confirmation** appears offering Save / Don't Save
  / Cancel; Cancel keeps the document. After closing, focus moves to another open
  document or a clean empty state — never nowhere.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-08 — Open from URL… (`file.open_url`)

*What & why.* Open a document straight from a web address, confirming the host and
size **before** any download.

**Before you start**
- Network available. A small plain-text URL you trust, staged in your notebook.

**Do this**
1. **File menu ▸ Open from URL…**.
2. Paste the URL into the field; proceed.

**You should see and hear**
- Before fetching, QUILL confirms the **host and expected size**; nothing writes to
  disk until you confirm. A blocked/unreachable host is reported clearly, not
  silently. On success the document opens in the editor.
- Cross-check: paste a **local file path** into the URL field — it is handled
  gracefully (opened as a local file or reported "not a URL"), never a silent
  network fetch.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-09 — Open Containing Folder (`file.open_containing_folder`)

*What & why.* Jump to the current file's folder in File Explorer.

**Before you start**
- A **saved** document open (e.g. `formatting.md`).

**Do this**
1. **File menu ▸ Open Containing Folder** (or Command Palette).

**You should see and hear**
- File Explorer opens focused on the folder with the current file selected. For an
  **unsaved/untitled** document, QUILL says there is no folder yet rather than
  erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-10 — Reload from Disk (`file.reload_from_disk`)

*What & why.* Discard in-memory edits and re-read the file as it is on disk (useful
after an external change).

**Before you start**
- `plain.txt` open. Type a change but **do not save**.

**Do this**
1. **File menu ▸ Reload from Disk**.
2. Read the confirmation; confirm.

**You should see and hear**
- QUILL warns that unsaved changes will be lost and lets you cancel. On confirm, the
  document reverts to the on-disk content (your typed change is gone) and says so.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-11 — Restore Backup… (`file.restore_backup`)

*What & why.* Recover a document from QUILL's automatic backups.

**Before you start**
- A document that has been edited and autosaved at least once (edit `plain.txt`,
  wait for an autosave, or edit over a few minutes).

**Do this**
1. **File menu ▸ Restore Backup…**.
2. Read the list of available backups; pick one and confirm.

**You should see and hear**
- A keyboard-navigable list of backups with timestamps is announced. Selecting one
  restores its content (into the document or a new buffer) and says which backup was
  restored. If there are none, QUILL says so plainly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-12 — Restore Previous Version (`file.restore_previous_version`)

*What & why.* Step back to the prior saved version of the current file.

**Before you start**
- A saved document you have saved **at least twice** with different content.

**Do this**
1. **File menu ▸ Restore Previous Version**.
2. Confirm the restore.

**You should see and hear**
- QUILL restores the previous version and announces it; if no previous version
  exists it says so rather than erroring. Any overwrite of current content is
  confirmed first.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-13 — Choose Encoding… (`file.choose_encoding`)

*What & why.* Open or re-interpret a file with a specific text encoding (e.g. UTF-8
vs a legacy code page) when characters look wrong.

**Before you start**
- `plain.txt` open.

**Do this**
1. **File menu ▸ Choose Encoding…**.
2. Arrow the encoding list; pick **UTF-8**; confirm.

**You should see and hear**
- A named, keyboard-navigable encoding list. Choosing one re-reads the document in
  that encoding and announces the change; the text stays correct for a UTF-8 file.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-14 — Toggle Line Endings (`file.toggle_line_endings`)

*What & why.* Switch between Windows (CRLF) and Unix (LF) line endings — matters for
cross-platform files.

**Before you start**
- `plain.txt` open. Note the current line-ending mode in the status bar if shown.

**Do this**
1. **File menu ▸ Toggle Line Endings** (or Command Palette).

**You should see and hear**
- QUILL announces the new mode (e.g. "Line endings: Unix (LF)"); saving then writes
  that ending. Toggling again returns to the original and is announced.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-15 — Header and Footer… (`file.header_footer`)

*What & why.* Set page header/footer text for printing/export.

**Before you start**
- Any document open.

**Do this**
1. **File menu ▸ Header and Footer…**.
2. Tab through the fields; type a header **`Test Header`** and a footer
   **`Page`**; confirm.

**You should see and hear**
- The dialog's fields are labelled and keyboard-complete; on confirm QUILL accepts
  the values (verified later in Print Preview / export). Escape cancels with no
  change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-16 — Page Setup… (`file.page_setup`)

*What & why.* Choose paper size, orientation, and margins for print/export.

**Before you start**
- Any document open.

**Do this**
1. **File menu ▸ Page Setup…**.
2. Tab through paper size, orientation, margins; change orientation to
   **Landscape**; confirm.

**You should see and hear**
- Every control is labelled and reachable by keyboard; changes are accepted and
  announced. Escape cancels cleanly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-17 — Print… (`file.print`, Ctrl+P)

*What & why.* Send the document to a printer (or a PDF printer).

**Before you start**
- Any document open; at least one printer installed (the built-in "Microsoft Print
  to PDF" is fine).

**Do this**
1. Press **Ctrl+P**, or **File menu ▸ Print…**.
2. Choose **Microsoft Print to PDF**; proceed and save a PDF.

**You should see and hear**
- The print dialog is keyboard-operable; the printer list is announced. Printing to
  PDF produces a readable file containing the document text. Cancel leaves nothing
  printed.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-18 — Print Studio… (`file.print_studio`)

*What & why.* QUILL's richer print/preview workspace (layout and options beyond the
system dialog).

**Before you start**
- `formatting.md` open.

**Do this**
1. **File menu ▸ Print Studio…**.
2. Explore its controls by keyboard; trigger a preview if offered; close with
   **Escape**.

**You should see and hear**
- Print Studio opens as a keyboard-navigable, announced surface; its options are
  labelled; a preview reflects the document. Escape/Close returns focus to the
  editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-19 — Convert File… (`file.convert_file`)

*What & why.* Convert a document on disk from one format to another without opening
it for editing.

**Before you start**
- `formatting.md` on disk. Target: convert to **`.docx`**.

**Do this**
1. **File menu ▸ Convert File…**.
2. Pick the source **`formatting.md`**, choose target **Word**, confirm the output
   location.

**You should see and hear**
- Source and target are chosen with labelled, keyboard-navigable controls; the
  conversion runs and reports success with the output path. The result opens in Word
  as a faithful `.docx`.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-20 — Import / Convert Document (OCR) (`file.import_convert`)

*What & why.* Bring in a scanned/image PDF and OCR it into editable text.

**Before you start**
- A scanned/image PDF (or image) available. **Precondition:** an OCR engine
  installed (Tesseract via `tools.install_local_ocr`, or a configured OCR service).
  If none, mark **Blocked**.

**Do this**
1. **File menu ▸ Import / Convert Document (OCR)**.
2. Pick the image/PDF; run the import.

**You should see and hear**
- Progress is announced; on success the recognized text opens as a document. With no
  OCR engine, QUILL points you to install one rather than failing silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-21 — Save Session… (`file.save_session`) and FILE-22 — Open Session… (`file.open_session`)

*What & why.* Save the whole set of open documents (a "session") and restore it
later — your desk exactly as you left it.

**Before you start**
- Two or three documents open (e.g. `plain.txt`, `formatting.md`, `table.md`).
- A session name: **`qa-session`**.

**Do this**
1. **File menu ▸ Save Session…**; name it **`qa-session`**; confirm.
2. Close all documents (**Ctrl+W** each).
3. **File menu ▸ Open Session…**; pick **`qa-session`**; confirm.

**You should see and hear**
- Save announces the session was saved. Open restores **all** the documents from the
  session with focus in a sensible one; the set matches what you saved.

**Sign off (Save Session)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Open Session)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-23 — Open over SSH: Quick Connect… (`file.ssh_quick_connect`)

*What & why.* Open a file on a remote server over SSH by entering the connection
once.

**Before you start**
- **Precondition:** an SSH server you can reach with credentials. If none, mark
  **Blocked**. Note QUILL rejects unknown host keys by default (trust-on-first-use
  is opt-in).

**Do this**
1. **File menu ▸ Open over SSH: Quick Connect…**.
2. Enter host, username, and credentials by keyboard; connect; browse to a file and
   open it.

**You should see and hear**
- Fields are labelled and keyboard-complete. An **unknown host key** is refused with
  a clear spoken message unless you have enabled trust-first-use — it does not
  silently connect. On success the remote file opens.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-24 — Open over SSH: Site Manager… (`file.ssh_site_manager`)

*What & why.* Save and manage named SSH sites for repeat connections.

**Before you start**
- Same SSH precondition as FILE-23 (else **Blocked**).

**Do this**
1. **File menu ▸ Open over SSH: Site Manager…**.
2. Add a site (host/user), save it, then connect from the saved entry.

**You should see and hear**
- The site list and its add/edit/remove controls are labelled and keyboard-operable;
  a saved site connects on activation. Secrets are stored via the platform secret
  store, not in plain text.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-25 — Save to GitHub… (`file.github_save_back`, Ctrl+Shift+Grave then Shift+Q)

*What & why.* Commit the current document back to a GitHub repository.

**Before you start**
- **Precondition:** a GitHub account connected (see FILE-28) and a document opened
  from a repo. If not connected, mark **Blocked**.
- The chord shortcut is a two-step: press **Ctrl+Shift+Grave**, release, then
  **Shift+Q**. (Grave is the backtick key.)

**Do this**
1. Open the command via the chord, or **File menu ▸ Save to GitHub…**.
2. Enter a commit message by keyboard; confirm.

**You should see and hear**
- A labelled commit-message field; on confirm QUILL reports the commit/push result
  (success or a clear error). Nothing is pushed without your confirmation.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-26 — Open Remote GitHub File URL… (`file.open_github_file_url`, chord then Shift+W)

*What & why.* Open a single file directly from a GitHub URL.

**Before you start**
- A GitHub file URL (a public one needs no auth). Chord: **Ctrl+Shift+Grave** then
  **Shift+W**.

**Do this**
1. Open the command (chord or **File menu**), paste the file URL, confirm.

**You should see and hear**
- The URL field is labelled; the file's content opens in the editor; a bad URL or
  private file without auth is reported clearly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-27 — Open Remote GitHub Repository… (`file.open_github_repository`, chord then Shift+Y)

*What & why.* Browse and open files from a whole GitHub repository.

**Before you start**
- A GitHub repo URL. Chord: **Ctrl+Shift+Grave** then **Shift+Y**.

**Do this**
1. Open the command; enter the repository; browse its file tree by keyboard; open a
   file.

**You should see and hear**
- The repo browser is keyboard-navigable and announced; selecting a file opens it.
  Errors (missing repo, no access) are spoken clearly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-28 — Open GitHub Items… (`file.open_github_items`, chord then Shift+I)

*What & why.* Open issues / pull requests from a repository as readable documents.

**Before you start**
- A connected GitHub account (FILE-29) and a repo with issues/PRs. Chord:
  **Ctrl+Shift+Grave** then **Shift+I**.

**Do this**
1. Open the command; pick a repo; browse issues/PRs; open one.

**You should see and hear**
- The item list is announced with titles/numbers; opening one shows its content as
  navigable text. Read-only browsing needs no write scope.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FILE-29 — Manage GitHub Accounts… (`file.github_manage_accounts`, chord then Shift+Z)

*What & why.* Connect, view, and remove the GitHub accounts the file/GitHub features
use. Do this **before** FILE-25/28 if not yet connected.

**Before you start**
- A GitHub account and its sign-in (token or device flow). Chord:
  **Ctrl+Shift+Grave** then **Shift+Z**.

**Do this**
1. Open the command, or **File menu ▸ Manage GitHub Accounts…**.
2. Add an account by keyboard, following the sign-in prompts; confirm it appears in
   the list; then remove it to confirm removal works.

**You should see and hear**
- The account list and add/remove controls are labelled and keyboard-operable; a
  connected account is announced. **Tokens are stored in the platform secret store**
  (Credential Manager / DPAPI), never printed or written in plain text. Removal is
  confirmed.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 29
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
