# Part 0 — Getting Started (you have never used QUILL)

Do this part **first**, once on each test machine, before any feature section. It
takes you from "I have a download" to "I have created, saved, closed, and reopened
a document in QUILL, using only the keyboard, hearing every step." If you can
finish Part 0, the machine is ready for the rest of the book. If you cannot, stop
and report — nothing downstream will be trustworthy.

Read §2 and §3 of `README.md` once before you begin so the scenario layout and the
Pass/Fail/Blocked/N-A boxes make sense.

---

## GS-01 — Turn on your screen reader and confirm it is speaking

*What & why.* QUILL is designed to be used by ear. Before you touch QUILL, make
sure the screen reader itself is running and talking, so that later "it was silent"
means QUILL was silent, not that your screen reader was off.

**Before you start**
- A Windows machine with **NVDA** or **JAWS** installed. (macOS testers: use
  **VoiceOver**, Command+F5.)
- Nothing else needs to be open.

**Do this**
1. Start your screen reader: **NVDA** with **Ctrl+Alt+N**, or **JAWS** from its
   Start-menu shortcut. (Narrator: **Ctrl+Windows+Enter**.)
2. Press the keys to read the focused item — with NVDA, tap **NVDA+Tab** (NVDA is
   usually the Insert key or Caps Lock).
3. Open the Start menu (**Windows key**) and press **Down Arrow** once or twice.

**You should see and hear**
- The screen reader speaks as you move: it announces the Start menu and reads each
  item you arrow onto. You hear a clear, responsive voice.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-02 — Install QUILL (system installer)

*What & why.* Most users run the system installer: a normal Windows setup that
adds QUILL to the Start menu. This scenario proves it installs and appears where a
new user would look. (If you are testing the **portable ZIP** instead, skip to
GS-03.)

**Before you start**
- The file **`Quill-Setup-1.0.0.exe`** (the system installer) downloaded to a known
  folder, e.g. your Downloads.
- You know whether this is a **per-user** install (no admin needed) — the default.

**Do this**
1. In File Explorer, arrow to `Quill-Setup-1.0.0.exe` and press **Enter** to run
   it.
2. Move through the installer with **Tab** and **Enter**; read each screen. Accept
   the default install location. When offered a **Desktop shortcut** and
   **Open-With** file associations, note the choices but you may accept defaults.
3. On the last screen, leave **Launch QUILL** unchecked for now and press
   **Finish**.
4. Open the Start menu (**Windows key**), type **QUILL**, and confirm an entry
   appears.

**You should see and hear**
- Each installer screen is keyboard-navigable and its controls are announced (this
  is the Inno Setup UI, not QUILL, but it must still be operable by keyboard).
- After finishing, **QUILL** appears in the Start menu. If you accepted them, a
  Desktop shortcut exists and QUILL appears in **Add or Remove Programs** with a
  proper name, version **1.0.0**, and publisher **Community Access**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-03 — Set up the portable copy (portable ZIP) [do instead of GS-02 for portable]

*What & why.* The portable edition runs from a folder with no installation, keeping
all its data beside itself — ideal for a USB stick or a locked-down machine. This
proves the ZIP unpacks into a self-contained, runnable folder.

**Before you start**
- The file **`Quill-Portable-1.0.0.zip`** downloaded.
- A folder you can write to, e.g. `C:\QuillPortable` or a USB drive.

**Do this**
1. In File Explorer, select the ZIP, press the **Application/Menu key**, and choose
   **Extract All…**; extract into your chosen folder.
2. Open the extracted folder and confirm it contains a launcher named **`QUILL.exe`**
   (a genuine native launcher, not a script) and a **`data`** subfolder beside it.

**You should see and hear**
- The folder is self-contained: `QUILL.exe`, a bundled `pythonw.exe`, and a `data\`
  folder are all present. Nothing had to be installed system-wide.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-04 — Launch QUILL for the first time

*What & why.* The first launch is the moment of truth: the window must open, take
focus, and be announced, with no crash dialog. First launch may also show a
one-time welcome/onboarding — that is expected.

**Before you start**
- QUILL installed (GS-02) or extracted (GS-03). Screen reader running (GS-01).

**Do this**
1. Launch QUILL: from the **Start menu** (system install) press **Enter** on the
   QUILL entry, **or** run **`QUILL.exe`** in the portable folder.
2. Wait a few seconds for the main window to appear. Do not click anything.
3. If a welcome / first-run dialog appears, read it fully with the screen reader,
   then dismiss it with its default button (or **Escape**) — note what it offered.

**You should see and hear**
- The QUILL window opens and **comes to the foreground**; the screen reader
  announces the window (its title includes **QUILL**). There is **no crash or error
  dialog**.
- Any first-run welcome is keyboard-operable and announced; after dismissing it,
  focus lands in the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-05 — Confirm the version and build (Help ▸ About)

*What & why.* Sign-off is only valid against a known build. This records exactly
which build you are testing.

**Before you start**
- QUILL open (GS-04).

**Do this**
1. Press **Alt** to enter the menu bar; the screen reader announces the first menu.
2. **Right Arrow** to the **Help** menu, then **Down Arrow** to **About QUILL…** and
   press **Enter**. (Or open the menu and press its mnemonic letter.)
3. Read the dialog top to bottom with your screen reader. Write the version and
   build stamp in your notebook.
4. Close the dialog with **Escape** or its **OK/Close** button.

**You should see and hear**
- The About dialog opens, is fully readable by keyboard, and states version
  **1.0.0** and a build/commit stamp. Closing it returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-06 — Get your bearings: the main window

*What & why.* Later sections say things like "focus returns to the editor" or
"check the status bar." This scenario teaches you those places so the rest of the
book makes sense.

**Before you start**
- QUILL open, no document changes yet.

**Do this**
1. Press **F6** a few times to cycle between the window's main regions (editor,
   status bar, and any panels). Listen to what each region is called.
2. Press **Alt** and **Right Arrow** across the whole menu bar once — File, Edit,
   View, Insert, Format, Navigate, Search, Tools, and so on — just to hear the menu
   names. Press **Escape** to leave the menu bar.
3. Return to the editor (press **Escape** until the screen reader says you are in
   the document / text area).

**You should see and hear**
- **F6** moves between named regions and each is announced (e.g. the editor as a
  multi-line "Document" text area, and a status bar). The menu bar lists the
  expected top-level menus. Escape lands you back in the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-07 — Your first document: type, hear it, and read it back

*What & why.* The core of QUILL is typing and having it spoken. This proves the
editor accepts text and reads back what you wrote.

**Before you start**
- A new, empty document. If one is not already open, press **Ctrl+N** (New File).
- The exact text to type: **`Hello QUILL, this is my first line.`**

**Do this**
1. With focus in the editor, type: `Hello QUILL, this is my first line.`
2. Press **Enter**, then type a second line: `And this is my second line.`
3. Press **Ctrl+Home** to go to the top, then **Down Arrow** to move line by line
   and listen. Press **Ctrl+A** to select all and listen to the selection
   announcement.

**You should see and hear**
- Characters/words are echoed as you type (per your screen reader's echo setting).
  Arrowing reads each line back **exactly** as typed. **Ctrl+A** announces that all
  text is selected. The title bar now shows a **modified** indicator (an unsaved
  change marker).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-08 — Save it, close it, reopen it (the round trip)

*What & why.* A newcomer's real first task is "write something and get it back
later." This proves save, the unsaved-changes guard, and reopen — the safety net
every other scenario relies on.

**Before you start**
- The two-line document from GS-07, unsaved.
- A filename to use: **`first.md`**, saved to your Documents folder.

**Do this**
1. Press **Ctrl+S** (Save). Because the document is new, a **Save As** dialog opens.
2. In the dialog, type the name **`first`**, confirm the type is Markdown/`.md`, and
   press **Enter** to save into Documents.
3. Press **Ctrl+W** (Close Document).
4. Press **Ctrl+O** (Open), navigate to **`first.md`** in Documents, and press
   **Enter**.

**You should see and hear**
- On save, the screen reader confirms the save and the title bar updates to
  **`first.md`** with the modified marker **gone**.
- Close leaves you with no unsaved-changes prompt (you just saved). Reopening
  **`first.md`** shows both lines exactly as written; focus lands in the editor.
- Cross-check the guard: type one character, press **Ctrl+W**, and confirm QUILL
  **asks before discarding** the change (you can hear and cancel the prompt). Cancel
  it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-09 — Undo, redo, and getting unstuck

*What & why.* Newcomers make mistakes; QUILL must make them recoverable. This also
teaches Escape as the universal "get me out of here."

**Before you start**
- `first.md` open from GS-08.

**Do this**
1. Type the word `TEMP` somewhere, then press **Ctrl+Z** (Undo). Press **Ctrl+Y**
   (Redo).
2. Open any menu with **Alt**, then press **Escape** to confirm it closes and focus
   returns to the editor.
3. Open a dialog you have already met — **Help ▸ About** — and close it with
   **Escape** alone.

**You should see and hear**
- Undo removes `TEMP` and says so; Redo restores it. Escape reliably closes menus
  and dialogs and returns you to the editor every time. Nothing is silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GS-10 — Find every command without memorizing anything (Command Palette)

*What & why.* No one can memorize 700 commands. The Command Palette lets you find
any command by typing part of its name — your escape hatch for the entire rest of
this book. Learn it now.

**Before you start**
- QUILL open with any document.

**Do this**
1. Open the **Command Palette** (**Ctrl+Shift+P**). A search box appears with focus.
2. Type **`save as`** and listen as the results filter. Arrow through them.
3. Press **Escape** to close it without running anything.

**You should see and hear**
- The palette opens with focus in the search field; typing filters a list that is
  announced as it changes (result count and the focused item). Arrowing reads each
  match with its name and shortcut. Escape closes it and returns focus to the
  editor. **From here on, if you cannot find a command in a menu, open the palette
  and type its name.**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 10
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
