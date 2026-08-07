# Section — Quillins (extensions system)

**Quillins** are QUILL's extensions: small add-ons that contribute commands, menu
items, hotkeys, snippets, abbreviations, status-bar cells, preferences pages, and
background/document-event handlers. QUILL ships a set of **bundled** Quillins
(trusted, first-party) that always load. **Third-party** Quillins are a separate,
locked-off capability in a public 1.0 build (security gate **SEC-8**): a shipping
build discovers and runs nothing third-party, but the Manager still opens and is
fully operable, and every bundled Quillin runs normally.

This section proves the whole Quillin lifecycle: opening the Manager, seeing what
bundled Quillins ship, running each observable one, confirming contributed menu
items/commands/hotkeys appear and work, enabling/disabling, installing a user
Quillin (locked in public), surfacing manifest errors, Safe Mode disabling all
contributions, and removing a Quillin. Finish **Part 0** first. Read §2–§3 of
`README.md` for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes; read §5 for what **[GATED]** means.

The **bundled editor Quillins** that ship (the ones this section walks) are:
**Insert Tools**, **Insert Character**, **Line Tools**, **Markdown Helpers**,
**Text Tools**, **Math Equations**, **Smart Insert**, **Word Count (Node)**,
**Status Scribe**, **Document Guardian**, **Journal Stamp**, **BRF Tools**,
**Daily Stamp**, **AI Writing Prompts**, and **AI Writing Skills**. Five more
bundled Quillins ship for the **companion apps** (Radio Community Directory, Cast
Premium Auth, Weather Extra Alerts, Studio Normalizer, Beacon Transit Resolver)
plus three cloud transcription providers; those do **not** appear in the editor's
Manager because they target other apps.

Common inputs used below (copy the `../qa-samples/` folder onto the machine first):
`plain.txt`, `formatting.md`.

---

## QLN-01 — Open the Quillins Manager (`tools.quillins_manager`)

*What & why.* The Manager is the one place to see every installed Quillin, read
its details, and act on it. It must open by keyboard and be fully announced.

**Before you start**
- QUILL open, any document. A normal (public) build.

**Do this**
1. Press **Alt** to reach the menu bar, open the **Tools menu**, then the
   **Quillins** submenu, then choose **Manage Quillins…**. (You can also run it
   from the Command Palette → "Manage Quillins".)

**You should see and hear**
- A dialog titled **Quillins Manager** opens; focus lands in a list named
  **Installed Quillins**. Below the list are a read-only **Details** text area and
  buttons **Enable**, **Disable**, **Configure Events…**, **Reload**,
  **Remove…**, **Install from Folder…**, and **Close**.
- At the top, an intro line is announced. On a **public** build it reads in
  substance: *"Bundled Quillins ship enabled and run normally. Third-party
  Quillins are disabled in this build and are listed for review only. Choose a
  Quillin to read its details."* (On a dev build with third-party enabled it
  instead offers Enable/Disable/Reload/Remove.)
- **Tab** reaches every control; **Escape** closes the dialog and returns focus to
  the Tools menu / the control that opened it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-02 — The bundled Quillins that ship (list + details)

*What & why.* A release must prove the expected first-party Quillins are present,
named correctly, and describe themselves accurately — including their signature
status, capabilities, and contributed commands.

**Before you start**
- Quillins Manager open (QLN-01).

**Do this**
1. **Down/Up arrow** through the **Installed Quillins** list, reading each entry.
2. On a few entries, **Tab** to the **Details** area and read it.

**You should see and hear**
- Each list item is announced as **name plus state**, e.g. "Insert Tools
  (enabled)", "Markdown Helpers (enabled)". The bundled editor Quillins listed in
  the section intro above are all present and marked **enabled**; none is marked
  **(invalid)**.
- The **Details** area for a selected Quillin reads its **Id, Folder, Name,
  Version, Author, Description, Categories, Capabilities, Type** (snippet-only vs
  Python/Node handler), its contributed **Commands**, any **Events**, an
  **Enabled: yes/no** line, and a **Signature** line — for a shipped bundled
  Quillin this should say **"Signature: verified, signed by …"** (or, if the build
  is unsigned, "Signature: unsigned. This Quillin is not publisher-attested.").
- The companion-app Quillins (Radio/Cast/Weather/Studio/Beacon) and the cloud
  transcription providers do **not** appear here — correct, because they target
  other apps, not the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-03 — A contributed menu item appears and runs: Insert Tools

*What & why.* Insert Tools is a pure snippet Quillin (no capabilities, so it can
never touch files, network, or clipboard). It proves a Quillin's declared
**menu placement** actually lands in the host menu and runs.

**Before you start**
- A document open with the caret in the editor.

**Do this**
1. Open the **Insert menu** and find the **Date and Time** submenu.
2. Choose **Insert Date**. Repeat with **Insert Time** and **Insert Date and
   Time**.

**You should see and hear**
- The **Insert ▸ Date and Time** submenu contains **Insert Date**, **Insert
  Time**, and **Insert Date and Time** (contributed by the Quillin). Activating
  one inserts today's date / current time / both at the caret, and QUILL announces
  **"Quillin snippet inserted."** The caret sits after the inserted text.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-04 — Line Tools: handler commands on the Edit menu

*What & why.* Line Tools is a Python-handler Quillin that edits text with
cursor-aware operations. It proves handler commands (out-of-process) work and land
on the **Edit** menu.

**Before you start**
- `plain.txt` open. Put the caret on a line with some text.

**Do this**
1. Open the **Edit menu**. Confirm it lists **Duplicate Line**, **Delete Line**,
   **Move Line Up**, **Move Line Down**, **Join Paragraph Lines**, and **Join
   with Next Line**.
2. Choose **Duplicate Line**. Then **Move Line Down**. Then **Delete Line**.

**You should see and hear**
- **Duplicate Line** adds an identical copy of the current line below it. **Move
  Line Down** swaps the current line with the one below. **Delete Line** removes
  the current line. Each result is spoken (the changed text is read where focus
  lands); no error, no crash, and focus stays in the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-05 — Insert Character: menu, context menu, and a prompt

*What & why.* Insert Character proves a Quillin can contribute to both a top-level
menu **and** the editor context menu, and prompt for input.

**Before you start**
- A document open with the caret in the editor.

**Do this**
1. Open the **Insert menu** and choose **Insert Special Character…**. (It is also
   on the editor **context menu** — open that with the **Menu/Applications key**
   or **Shift+F10** and choose the same item.)
2. In the prompt, type a code point — e.g. **`U+2764`** (a heart), or **`2764`**
   hex, or a decimal value; confirm.

**You should see and hear**
- A labelled prompt asks for the character/code point; on confirm the matching
  Unicode character is inserted at the caret and the action is announced. A bad or
  empty value is reported clearly, not silently ignored. The command is reachable
  from **both** the Insert menu and the context menu.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-06 — Math Equations: Insert Equation, hotkey, abbreviations, gallery

*What & why.* Math Equations is a rich handler Quillin: a dialog, a hotkey, dozens
of Math-AutoCorrect abbreviations, and Snippet Gallery formulas. It proves the
hotkey and abbreviation contribution paths.

**Before you start**
- A document open with the caret in the editor.

**Do this**
1. Press **Ctrl+Shift+E** (or **Insert menu ▸ Insert Equation…**). Enter a simple
   LaTeX formula, e.g. `a^2 + b^2 = c^2`; choose inline or display; confirm.
2. Back in the editor, type a math abbreviation followed by a delimiter, e.g.
   type **`\alpha`** then a space; then **`\ne`** then a space.
3. Select a formula you inserted, then use **Explore Equation Structure…**
   (**Ctrl+Shift+Grave** then **F**, or Insert menu / context menu).

**You should see and hear**
- Insert Equation inserts the LaTeX wrapped as inline `\(…\)` or display `$$…$$`
  (or MathML verbatim), and announces it. The abbreviation `\alpha` expands to
  **α** and `\ne` to **≠** on the delimiter. Explore Equation Structure steps
  through the formula's parts with a plain-English reading of each. The Snippet
  Gallery (Insert ▸ Snippet Gallery…) lists this Quillin's formulas (Quadratic
  Formula, Pythagorean Theorem, etc.).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-07 — Markdown Helpers: Format menu, a hotkey, and a guarded context item

*What & why.* Markdown Helpers mixes a Layer-1 snippet and a Layer-2 handler, and
declares a hotkey plus a **selection-only** context-menu entry — proving the
`when: editor.hasSelection` guard.

**Before you start**
- A Markdown document open (e.g. copy `formatting.md`). Some text present.

**Do this**
1. Open the **Format menu** and confirm it lists **Wrap Selection in Bold** and
   **Insert Markdown Front Matter**.
2. Select a word, then press **Ctrl+Shift+B**.
3. With text **selected**, open the editor **context menu** (**Shift+F10**) and
   confirm **Wrap Selection in Bold** is present; with **no** selection, open it
   again and confirm the item is **absent**.
4. With the caret at the top of the document, choose **Insert Markdown Front
   Matter**.

**You should see and hear**
- **Ctrl+Shift+B** wraps the selection in `**…**` and announces it. The context
  menu shows Wrap Selection in Bold **only when text is selected** (the guard
  works). Insert Markdown Front Matter inserts a `---` YAML block seeded with the
  filename and today's date, then leaves the caret below it, announced as a
  snippet insertion.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-08 — Text Tools: commands across Format, Search, and Edit

*What & why.* Text Tools contributes to three different host menus at once, and
one command reads the clipboard — proving multi-menu placement and a
capability-scoped handler.

**Before you start**
- `plain.txt` open with several lines of text.

**Do this**
1. **Format menu ▸ Number Lines**.
2. **Format menu ▸ Hard-Wrap Lines**.
3. **Search menu ▸ Count Regular Expression Matches**; enter a simple pattern
   (e.g. `\w+`); confirm.
4. Copy some HTML to the clipboard from a browser, then **Edit menu ▸ Paste
   Clipboard HTML as Markdown**.

**You should see and hear**
- Number Lines prefixes each line with a number. Hard-Wrap reflows long lines. The
  regex count reports how many matches were found (spoken). Paste HTML as Markdown
  converts the clipboard HTML to Markdown at the caret. Each command is announced;
  the Search-menu ones prompt with labelled fields.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-09 — Smart Insert: smart triggers and abbreviations

*What & why.* Smart Insert proves the two typed-automation contribution paths: a
`=name()` **smart trigger** fired on Enter, and a **contributed abbreviation**
expanded after a delimiter.

**Before you start**
- A new empty document, caret in the editor.

**Do this**
1. On a blank line type **`=todo(3)`** and press **Enter**.
2. On a new line type **`=bug()`** and press **Enter**.
3. On a new line type **`qbug`** then press **Space** (or another delimiter).

**You should see and hear**
- `=todo(3)` is replaced in place by a 3-item to-do checklist; `=bug()` is replaced
  by a bug-report skeleton (Title / Steps / Expected / Actual). The typed trigger
  text is removed and the generated text inserted where it was — Enter is consumed
  (no stray blank line). The `qbug` abbreviation expands to the QUILL bug-report
  template. These triggers/abbreviations can be turned off individually in Smart
  Insert's preferences (see QLN-13).
- **Note.** These commands are also on the **Insert menu** (Insert Bug Report
  Template, Insert Meeting Notes Template, etc.) if you prefer menus to typing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-10 — Word Count (Node): a Node.js runtime Quillin

*What & why.* Most bundled Quillins run on QUILL's embedded Python worker; **Word
Count (Node)** runs on a spawned Node.js subprocess. It proves the Node runtime
path end-to-end.

**Before you start**
- **Precondition:** Node.js available to QUILL (it is one of the allowlisted
  engine executables). If Node is not installed/allowed, mark **Blocked**.
- `plain.txt` open with several words; optionally select a phrase.

**Do this**
1. **Tools menu ▸ Word Count (Node)** (also in the Command Palette).

**You should see and hear**
- QUILL announces the word count of the current selection, or of the whole
  document when nothing is selected. The result is spoken; no console window flashes
  and the editor never blocks. If Node is unavailable, QUILL reports the failure in
  substance ("Quillin error: …") rather than crashing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-11 — Status Scribe: a contributed status-bar cell

*What & why.* Status Scribe contributes a live word-count **status-bar cell** that
refreshes after every save and when switching tabs. It proves the `status_bar`
and `schedule` contribution paths and lifecycle events.

**Before you start**
- `plain.txt` open. Note the status bar.

**Do this**
1. Read the status bar (with your screen reader's status-review command, e.g. NVDA
   **Insert+End** on the desktop layout) and find the **Words:** cell.
2. Type a few words, then **Ctrl+S** to save.
3. Read the status cell again.

**You should see and hear**
- A status cell shows the count (e.g. "Words: 42"); its tooltip/name is announced
  when it receives focus. After a save the count updates to match the new content;
  switching to another tab updates the cell to that document's count. (Counting
  mode — words / characters / sentences — and optional spoken feedback are set in
  Status Scribe's preferences.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-12 — Document Guardian: document-lifecycle events + Configure Events…

*What & why.* Document Guardian reacts to document lifecycle events (before-close,
before-save, after-save). It proves event dispatch and the Manager's **Configure
Events…** per-event on/off control.

**Before you start**
- Quillins Manager open. Document Guardian is enabled.

**Do this**
1. Open a **new** document, type only one or two words (a "work in progress"), and
   press **Ctrl+W** to close it.
2. In the Manager, select **Document Guardian** and press **Configure Events…**.
   Read the checkbox list of its events; **uncheck** "Warn before closing short
   documents"; press **Save**.
3. Repeat step 1 and confirm the warning no longer speaks.

**You should see and hear**
- Closing the very short unsaved document speaks a **warning that it looks
  unfinished** — it does not block the close, it just makes sure you heard it.
- **Configure Events…** opens a dialog titled *Configure Events — com.quill.docguardian*
  listing each event with a title, the event id, a description, and a checkbox
  reflecting its current state. Unchecking one and saving stops that handler from
  firing; the Details area then shows that event as **off**. **Escape/Cancel**
  makes no change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-13 — Configure a Quillin's preferences (multi-tab page)

*What & why.* Quillins declare preferences as data; QUILL renders them with
accessible stock controls. This proves a multi-tab Quillin preferences page is
keyboard-complete and announced.

**Before you start**
- A Quillin that contributes preferences (e.g. **Smart Insert**, **Document
  Guardian**, **Status Scribe**, or **BRF Tools**).

**Do this**
1. Open the Quillin's preferences (from **Preferences/Settings**, find the
   Quillin's page — e.g. Smart Insert under Editing ▸ Insert Automation — or use
   the Manager's detail view to locate it).
2. **Tab**/**Shift+Tab** through the controls; move between tabs with **Ctrl+Tab**
   or the arrow keys on the tab strip.
3. Change one setting (e.g. Smart Insert's "Default to-do list length", or a
   trigger's Enable checkbox); confirm; reopen to verify it persisted.

**You should see and hear**
- The page has named **tabs** (e.g. Smart Insert: General, Log Mode, Smart
  Triggers, Abbreviations, BRF Testing). Every control (checkbox, choice, integer
  spinner, text field) is labelled and reachable by keyboard; its role, state, and
  value are announced. Conditional fields appear/enable only when their controlling
  setting matches (e.g. a "Custom pattern" field shows only when the format choice
  is Custom). Changes persist across a reopen.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-14 — Quillin permission (consent) prompt

*What & why.* A Quillin action that needs a privacy-sensitive capability must ask
first, in a dialog you can hear and cancel — QUILL never lets a Quillin act behind
your back.

**Before you start**
- A Quillin command that exercises a consent-gated capability at runtime.

**Do this**
1. Run such a command (e.g. a handler that reads the clipboard, writes a file, or
   makes a network request).
2. Read the permission dialog; choose **No** once (confirm it is refused), then run
   again and choose **Yes**.

**You should see and hear**
- A dialog titled **Quillin Permission Request** appears, announcing in substance:
  *"A Quillin is requesting the '<capability>' capability for: <detail>. Allow this
  action?"* with **Yes/No** buttons (No is the default). Choosing **No** refuses
  and the action does not happen; **Yes** allows it. **Escape** cancels.
- **Note.** The prompt only appears for capabilities that require consent; a
  Quillin whose capabilities are pre-granted may act without prompting. If no
  bundled command triggers a prompt in your build, mark **N/A** and note which
  capabilities were exercised silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-15 — Enable / Disable a Quillin  **[GATED]**

*What & why.* Enabling/disabling toggles whether a Quillin's contributions load.
The announced result must be clear.

**Before you start**
- Quillins Manager open. **Note the gate:** in a **public** build the **Enable**
  and **Disable** buttons are present but **not operable** (greyed) — bundled
  Quillins ship enabled and third-party ones are locked off, so there is nothing to
  toggle. These buttons become operable only in a **dev/admin build** with the
  third-party flag on (`QUILL_DEV_BUILD=1`).

**Do this**
1. Select a Quillin. Confirm **Enable/Disable** are **disabled** on a public build
   (mark **N/A** for the toggle here).
2. **[Dev build only]** Select an enabled Quillin, press **Disable**; then press
   **Enable**.

**You should see and hear**
- **Public build:** the Enable/Disable buttons are greyed and cannot be activated;
  the intro line explains why. Mark **N/A**.
- **Dev build:** Disable speaks **"Disabled <id>."** and Enable speaks **"Enabled
  <id>."**; the menus rebuild so the Quillin's contributed items disappear on
  disable and reappear on enable, and the list state updates.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-16 — Install a user Quillin from a folder  **[GATED]**

*What & why.* Third-party install is the untrusted path. For 1.0 it is **locked
off** (SEC-8): a user Quillin never loads or runs in a public build. This proves
the lock holds.

**Before you start**
- A folder containing a valid third-party `manifest.json` (a simple snippet
  Quillin is fine). A **public** build.

**Do this**
1. In the Manager, press **Install from Folder…**; pick the folder; confirm.
2. Look for the Quillin in the list; try to run any command it declares.

**You should see and hear**
- On a **public** build, even though the files may be copied, the installed
  third-party Quillin **does not appear** in the Manager list and **its commands
  never run** — third-party discovery returns nothing while the SEC-8 flag is
  locked off. The Manager intro states third-party Quillins are disabled; if you
  reach a third-party command by any path, QUILL says **"Third-party Quillins are
  disabled in this build."** Mark this scenario **N/A** for the "installed Quillin
  runs" outcome and record the locked message you heard.
- **[Dev build only]** With the third-party flag on, the installed Quillin appears
  in the list (announced **"Installed <id>."**) and its commands run.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-17 — Manifest validation errors are surfaced clearly

*What & why.* A broken Quillin must never fail silently or crash the editor — its
problems must be readable.

**Before you start**
- A folder with an **invalid** `manifest.json` (e.g. missing the required `name`
  field, or a malformed `version`). This exercises the same validation whether or
  not third-party install is unlocked.

**Do this**
1. In the Manager, press **Install from Folder…** and pick the invalid folder.

**You should see and hear**
- The install is **rejected before anything is copied**, with a spoken error
  message box titled **Install Quillin** reading in substance **"Install failed:
  …"** followed by the specific problem(s). The editor keeps running.
- **Cross-check (dev build):** an already-installed Quillin with a bad manifest
  shows in the list as **"(invalid)"**, and its Details area ends with a
  **"Problems:"** section listing each error. It is visible for review but does not
  load.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-18 — Safe Mode disables all Quillin contributions (cross-ref INST-07)

*What & why.* Safe Mode is the recovery lifeline: it must strip **every** Quillin
contribution (commands, menus, status cells, event handlers, timers) while still
letting you open the Manager. This is a non-negotiable invariant.

**Before you start**
- Ability to launch QUILL in **Safe Mode**: the **`--safe-mode`** flag or
  **`QUILL_SAFE_MODE=1`**. See install-matrix **INST-07** (Safe Mode is identical
  in portable and system builds).

**Do this**
1. Launch QUILL in Safe Mode.
2. Open **Tools ▸ Quillins ▸ Manage Quillins…**.
3. Check the menus that normally carry Quillin items (Insert ▸ Date and Time, Edit,
   Format, Search) and try a smart trigger like **`=todo()`** + Enter.

**You should see and hear**
- No Quillin-contributed commands, menu items, hotkeys, status cells, smart
  triggers, or abbreviations are present or active — `=todo()` does **not** expand.
- The **Manager still opens** and is operable; it announces in substance
  **"Quillins are disabled in Safe Mode."** rather than loading anything. No error,
  no crash. Restarting normally restores all bundled Quillins.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## QLN-19 — Remove a Quillin  **[GATED]**

*What & why.* Removing uninstalls a user Quillin from disk, guarded by a
confirmation you can cancel. Bundled Quillins are trusted first-party and are not
deletable from the Manager.

**Before you start**
- **[Dev build]** A user-installed Quillin present in the list (from QLN-16 with
  the third-party flag on). On a **public** build there are no user Quillins to
  remove — mark **N/A**.

**Do this**
1. Select the user Quillin and press **Remove…**.
2. In the confirmation, choose **No** first (confirm it is kept), then **Remove…**
   again and choose **Yes**.

**You should see and hear**
- A confirmation titled **Remove Quillin** asks in substance **"Remove the Quillin
  '<id>'? This deletes it from disk."** with **Yes/No** (No default). **No** keeps
  it. **Yes** deletes its folder, rebuilds the menus, and announces **"Removed
  <id>."**; it disappears from the list.
- **Note.** Selecting a **bundled** Quillin and pressing Remove does not delete it
  from the trusted install tree — it reappears on the next Reload. Do not fail this
  for bundled Quillins persisting; that is by design.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 19
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
