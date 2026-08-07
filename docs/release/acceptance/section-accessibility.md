# Section — Accessibility (cross-cutting, applies to every feature)

This section is different from the feature sections. It does not test one menu; it
tests the **promises QUILL makes about *every* menu**: that you can drive the whole
app by keyboard, that every control says its name and role out loud, that nothing
changes state in silence, and that the outcome reaches you in **speech and in
braille**. Run these scenarios against the everyday surfaces you already met in
Part 0 and in the File section — they are the lens you look through, not a new
feature to find.

These scenarios **complement, and do not replace,** the repo's
`../screen-reader-test-plan.md` (the fix-by-fix SR/keyboard cases) and the
core-journey plan `../qa-core-journeys.md`. Where those prove a specific fix, this
section proves the guarantee holds app-wide. The guarantees themselves are the
master plan's cross-cutting list,
`../../planning/signoff/QUILL-1.0.0-SIGNOFF.md` §F. Read §2–§3 of `README.md` first
— especially **§3, the universal keyboard contract**, which every scenario below
leans on.

The behaviours proven here are backed by build gates named in `../../../CLAUDE.md`:
`accessible_name_audit` (every focusable control has a name), `apply_modal_ids` /
the A11Y-4 dialog inventory (Escape/Close contract), **GATE-12** (announce-gap: no
silent outcomes), and the **#1283** braille-mirroring path (announcements go to a
refreshable display across Editor + Radio + Cast).

**Preconditions used below** (copy `../qa-samples/` onto the machine first):
`plain.txt`, `formatting.md`. A screen reader you can hear (NVDA or JAWS). For the
braille scenario, a **refreshable braille display**; for the matrix scenario, also
**Narrator** (Windows) and — on environment **E5** only — **VoiceOver** (macOS).

**How to run every scenario here:** do it **twice** — once with the **mouse
physically unplugged** (keyboard only), then again reading with your screen
reader's review / virtual cursor. If you ever reach for the mouse to finish a step,
that alone fails **Accessible**.

---

## A11Y-01 — Do a whole task with the mouse unplugged

*What & why.* The core promise: a screen-reader user with no mouse can complete
real work end to end. If any single step needs a pointer, the app is not usable for
its primary audience.

**Before you start**
- **Physically unplug the mouse** (or disable the trackpad). Leave it unplugged for
  this whole section.
- `../qa-samples/` on disk.

**Do this**
1. Press **Ctrl+O**; in the Open dialog type or arrow to **`plain.txt`**; press
   **Enter**.
2. In the editor, type the word **`accessible`** at the caret.
3. Press **Ctrl+S** to save.
4. Press **Alt** to enter the menu bar, arrow to **File**, arrow to **Close
   Document**, press **Enter**.

**You should see and hear (and feel)**
- Every step completes from the keyboard alone: the file opens with focus landing in
  the editor (announced as **Document**, multi-line text area); your typed word reads
  back; the save is confirmed aloud and the title bar's **modified marker clears**;
  the document closes and focus moves to another open document or a clean empty state
  — **never to nowhere**. At no point were you forced to click.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-02 — Tab / Shift+Tab move through a dialog in a sensible order

*What & why.* In any dialog, Tab must walk the controls in the order a person reads
them, and Shift+Tab must walk back. A jumbled or dead-ending tab order strands a
keyboard user.

**Before you start**
- Any document open. You will use a plain multi-field dialog — **File menu ▸ Header
  and Footer…** (or **Page Setup…** if your build routes header/footer through the
  system dialog).

**Do this**
1. Open the dialog (**Alt, F**, then arrow to the item, **Enter**).
2. Press **Tab** repeatedly and listen to each control's name/role as focus lands.
3. From somewhere in the middle, press **Shift+Tab** several times.

**You should see and hear (and feel)**
- **Tab** visits each field, then the buttons, in a logical top-to-bottom order and
  eventually cycles (it never lands on nothing and never jumps out of the dialog
  while it is open). **Shift+Tab** retraces the same path backward. Each stop
  announces a **name and a role** (e.g. "Test Header, edit"; "OK, button"). No stop
  is silent or announced only as a bare role ("edit", "button") with no name.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-03 — Escape cancels and returns focus to the control that opened the dialog

*What & why.* Escape must always back out of a dialog with no change, and focus must
snap back to exactly where you were — the menu item or button you opened it from —
so you never lose your place. This is the `apply_modal_ids` contract.

**Before you start**
- `plain.txt` open. Note where the caret is (e.g. start of line 1).

**Do this**
1. Open **File menu ▸ Header and Footer…** (or any modal dialog you can reach).
2. Type something into the first field so the dialog is "dirty".
3. Press **Escape**.

**You should see and hear (and feel)**
- The dialog closes with **no change saved** (re-open it: the field is empty again).
  Focus **returns to the opener** — the File menu item / the editor — not to some
  unrelated control and not to nowhere. If the screen reader goes silent after
  Escape, focus was lost: that is a fail.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-04 — Enter activates the default button

*What & why.* Pressing Enter from anywhere in a dialog should fire its default
(usually OK / Save), so a keyboard user does not have to Tab to a button first.
Destructive defaults are the exception — those must confirm, not just fire.

**Before you start**
- Any document open. Use **File menu ▸ Header and Footer…**.

**Do this**
1. Open the dialog; type **`Test Header`** in the first field.
2. Without tabbing to any button, press **Enter**.

**You should see and hear (and feel)**
- The default button fires — the dialog accepts the value and closes — and the
  outcome is announced (focus returns to the editor). Re-open the dialog to confirm
  **`Test Header`** was kept. Cross-check the guard case: on a **destructive**
  confirmation (e.g. the unsaved-changes prompt on Close), Enter must **not** silently
  discard work — the safe choice is the default or the action is spoken and
  cancellable (§3).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-05 — Every focusable control has an accessible name (spotting an unnamed one by ear)

*What & why.* If a control has no name, a screen reader can only say its **role** —
"edit", "button", "list" — with nothing to tell you *which* one. QUILL's
`accessible_name_audit` gate exists to prevent exactly this. Here you learn to hear
the failure.

**Before you start**
- Open a dialog that is dense with fields. Good choices: **Help ▸ Application
  Status** (tabbed lists), or an AI authoring / model-search dialog if AI is
  configured. Any multi-field surface works.

**Do this**
1. Open the dialog.
2. **Tab** through every control, one at a time. For each, say out loud what you
   heard: does it have a **human name**, or only a role?
3. Listen specifically for two failure sounds: a bare role with **no name** ("edit"
   … silence), and a **snake_case / code name** spelled or run together
   ("status underscore overview", "status overview" read as an identifier rather
   than words).

**You should see and hear (and feel)**
- Every stop announces a **readable name + role**, e.g. "Status overview, list";
  "Refresh, button"; "Search models, edit". **No** control is nameless, and **none**
  reads as a raw identifier (`status_overview`, letter-for-letter or underscore
  spoken). A single unnamed or code-named focusable control is a fail — note exactly
  which control and what it said.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-06 — Roles are correct: an edit sounds like an edit, a list like a list

*What & why.* A name is not enough — the **role** must match what the control really
is, or the screen reader gives the wrong navigation hints (e.g. announcing a text
area as read-only, or a list as a plain pane). This confirms the editor and a list
surface expose the right role and state.

**Before you start**
- `plain.txt` open.

**Do this**
1. Move focus into the editor text area.
2. Type a few words, then select them (**Shift+Home**).
3. Open **Help ▸ Application Status**; Tab to one of its lists and arrow within it.

**You should see and hear (and feel)**
- The editor announces as **Document**, **edit / text-area** role, **multi-line**;
  typed text reads back and the **selection is announced** and stays visible when
  focus leaves. The Application-Status list announces as a **list** with items you
  can arrow through (item count / position spoken). A control whose spoken role
  contradicts its behaviour (a real text area announced as a button, an interactive
  list announced as static text) is a fail.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-07 — Menu mnemonics and shortcuts work, with no mnemonic collisions

*What & why.* Every top menu and item carries an **underlined letter** (a mnemonic)
you can press after Alt, plus its accelerator (e.g. Ctrl+S). Two items in the same
menu must not share a mnemonic, or one becomes unreachable by letter.

**Before you start**
- Any document open.

**Do this**
1. Press **Alt** to enter the menu bar. Note the underlined letter on each top menu
   (**F**ile, **E**dit, …); press each letter in turn to open that menu.
2. Inside one open menu (e.g. File), press **Down** through every item and, for each,
   note the underlined letter the screen reader announces.
3. Type a mnemonic letter within the open menu and confirm exactly one item responds.
   Then close the menu and confirm the printed **accelerator** for a couple of items
   (e.g. **Ctrl+S** Save, **Ctrl+O** Open) actually fires the command.

**You should see and hear (and feel)**
- **Alt** enters the menu bar (announced); each top-level letter opens its menu.
  Within a menu, **no two enabled items share the same mnemonic** — pressing a letter
  activates one item unambiguously, or (if the platform cycles duplicates) the screen
  reader clearly moves between them rather than silently doing nothing. The printed
  accelerators fire their commands. A duplicated mnemonic that makes an item
  unreachable by letter is a fail — record the menu and the two items.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-08 — No silent state changes: every outcome is announced

*What & why.* QUILL's **GATE-12** promise is that a user-visible change never happens
in silence — a toggle, a mode switch, a save, a count all speak. A screen-reader user
who hears nothing has no way to know it worked.

**Before you start**
- `plain.txt` open.

**Do this**
1. Fire a **toggle** with a spoken outcome — e.g. **File menu ▸ Toggle Line Endings**
   (or a View toggle such as word-wrap). Do it, then do it again to flip back.
2. Fire a **save**: press **Ctrl+S** after making one edit.
3. Fire a **navigation/status** action with a spoken result — e.g. the
   focus-status-bar command, or Go To Line — anything that changes state.

**You should see and hear (and feel)**
- Each action produces an **immediate spoken announcement of the new state** — e.g.
  "Line endings: Unix (LF)", then "Windows (CRLF)" on the second press; a save
  confirmation with the modified marker clearing; the status/position spoken. A
  toggle that changes the app but says **nothing** is an accessibility fail even
  though it "worked" — note which action was silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-09 — A validation error speaks *and* moves focus to the field to fix

*What & why.* When a form rejects your input, two things must happen together: the
error is **announced**, and focus **moves to the offending field** so you can correct
it without hunting. Announcing an error while leaving focus on the button is a
half-failure that strands a keyboard user.

**Before you start**
- **Precondition:** a way to open a validating form. The reference case is the GitHub
  open-repository form (**File ▸ Open Remote GitHub Repository…**). If GitHub is not
  configured, substitute any dialog with a required/format-checked field, or mark
  **Blocked** and say why.

**Do this**
1. Open the form.
2. Leave the required field empty (or enter a value in the wrong format, e.g. a repo
   name with no `/`).
3. Activate the submit/Load button.

**You should see and hear (and feel)**
- The rejection is **spoken** ("Enter a repository name…" / "Repository must be in
  owner/repo format."), **and** focus lands **in the field to fix**, not on the button
  you just pressed. You can immediately type the correction. Silence, or a spoken
  error with focus left on the button, is a fail.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-10 — Announcements mirror to a refreshable braille display (Editor, Radio, Cast)

*What & why.* A braille user who has speech muted must still receive QUILL's spoken
outcomes **on the braille display**. The **#1283** path mirrors every announcement to
braille (Settings ▸ `announcement_braille`, on by default) and must do so in the
editor **and** in the standalone Quill Radio app.

**Before you start**
- **Precondition:** a **refreshable braille display** connected and driving your
  screen reader. **If you have no braille hardware, mark this Blocked** and say so —
  it cannot be felt without a display.
- Confirm braille mirroring is enabled (it is on by default).

**Do this**
1. In the editor, fire an announcing action — **Ctrl+S** on an edited `plain.txt`, or
   **Toggle Line Endings**. Read the braille display.
2. Launch **Quill Radio** (QuillVille switcher). Perform an announcing action there
   (e.g. play/stop, or change station); read the braille display.
3. **Cast:** the **Quill Cast** app is **gated out of the public 1.0 build** — mark
   the Cast leg **N/A** on a public build. On a dev/admin build (`QUILL_DEV_BUILD=1`)
   only, repeat step 2 in Cast.

**You should see and hear (and feel)**
- The same message you **hear** also appears **on the braille cells** — the save
  confirmation, the line-ending mode, the Radio state — in both the editor and Radio.
  It routes through the active braille backend without throwing (a braille failure is
  recorded, never crashes the app). If speech spoke but the display stayed blank,
  that is the #1283 failure — note which surface.
- **Note:** Cast is not present in a public build; do not fail its leg for being
  absent — mark **N/A** and confirm its true absence in `gated-absence.md`.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-11 — The screen-reader matrix: one representative task under each SR

*What & why.* QUILL commits to **NVDA, JAWS, Narrator** (Windows) and **VoiceOver**
(macOS, environment **E5**). The same task must succeed and be announced correctly
under each — a control named for NVDA can still be mute under JAWS.

**Before you start**
- The representative task is **A11Y-01** (open `plain.txt`, type a word, save, close).
- Have **NVDA**, **JAWS**, and **Narrator** available on Windows. On **E5** (macOS app
  bundle) have **VoiceOver**. On a Windows-only run, mark the VoiceOver row **N/A**
  and note it will be covered on E5.

**Do this**
1. Start **NVDA**. Run the A11Y-01 task start to finish, keyboard only; record the
   actual spoken text at each step.
2. Quit NVDA, start **JAWS**. Repeat the same task; record what it said.
3. Quit JAWS, start **Narrator**. Repeat; record.
4. On **E5 only**: with **VoiceOver** on, repeat; record.

**You should see and hear (and feel)**
- Under **each** screen reader the task completes by keyboard, focus lands correctly
  (editor announced as Document; close returns focus sensibly), and the save is spoken
  with the modified marker clearing. Exact wording differs per SR — that is expected —
  but the **name, role, state, and load-bearing values** must be present and correct
  in all of them. A step that works under one SR but is silent or misnamed under
  another is a fail for that SR; record which one and the words.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-12 — High-contrast theme and reduced-motion are respected

*What & why.* Low-vision users who are not on a screen reader rely on the OS
**high-contrast** theme and, where the OS asks for it, **reduced motion**. QUILL's
native wx controls should repaint under high contrast and stay legible; any animation
must never be the *only* signal that something happened.

**Before you start**
- Any document open.
- Know how to toggle Windows **High Contrast** (Left Alt + Left Shift + Print Screen,
  or Settings ▸ Accessibility ▸ Contrast themes) and **Animation effects** off
  (Settings ▸ Accessibility ▸ Visual effects).

**Do this**
1. Turn **High Contrast** on. Look at QUILL: menus, dialog fields, the editor, the
   status bar.
2. Open a dialog (e.g. Header and Footer…) and read its fields under the theme.
3. Turn **reduce animations** on. Trigger anything with progress/motion (a save, a
   conversion, any spinner) and confirm you can still tell it happened.

**You should see and hear (and feel)**
- Under high contrast, text and controls repaint to the theme's colours and stay
  **readable** (no invisible text on a same-colour background, no controls that vanish
  into the background). With reduced motion, outcomes are still conveyed by **text /
  speech / a settled end state**, not by animation alone.
- **Note:** QUILL is screen-reader-first and largely non-animated; if the build has no
  bespoke theming it inherits the OS/wx high-contrast behaviour — that is acceptable
  as long as everything stays legible. If a surface has custom colours that ignore the
  OS theme, or a spinner is the sole indicator, fail and record the surface.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## A11Y-13 — Focus is never lost and never trapped

*What & why.* Two opposite failures strand a keyboard user: focus **lost** (Tab lands
on nothing; the SR goes silent), or focus **trapped** (a control eats Tab so you can
never leave it). Neither may happen anywhere in QUILL.

**Before you start**
- `plain.txt` open, and a second document (Ctrl+N) so the tab bar exists.

**Do this**
1. From the editor, press **Tab** and keep pressing it, listening at every stop, all
   the way around the main window (editor → controls → menu region → back). Note any
   stop that is **silent** or any point where Tab **stops responding**.
2. Focus the **editor text area** and press **Tab** once — confirm focus **leaves** the
   editor to the next control (it must not insert a tab character or trap you).
3. Focus a **multi-line prose field** in any dialog (e.g. a Note / prompt body) and
   press **Tab** — confirm focus moves to the next control.
4. Open a dialog and close it with **Escape**; confirm focus returns (cross-check with
   A11Y-03).

**You should see and hear (and feel)**
- Tab always moves to a **named, announced** control and eventually cycles — it never
  lands on nothing and never dead-ends in silence. The editor and prose fields **let
  Tab out** (no tab character inserted, no trap). Focus after any dialog closes is
  accounted for.
- **Note:** the restricted-Python **code editor** field is a deliberate exception — it
  keeps Tab for indentation and does not yet offer a keyboard focus-exit (a recorded
  follow-up, not a new fail). If you test that specific field, confirm the documented
  behaviour and note it; do not fail the section for it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 13
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
