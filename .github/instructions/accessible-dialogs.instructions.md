---
applyTo: "quill/ui/**/*.py"
---

# Accessible Dialog Patterns (wxPython, screen-reader-first)

These rules govern every dialog and modal surface in QUILL's wxPython UI. They
go beyond keyboard navigation: a dialog is only "done" when a blind keyboard
user, a low-vision user, and a sighted mouse user each get an equally clear,
predictable experience.

Authoritative sources these rules are grounded in:

- wxWidgets/wxPython Phoenix dialog, sizer, and validator overviews
  (`wx.Dialog`, `wx.StdDialogButtonSizer`, `CreateButtonSizer`, `SetAffirmativeId`,
  `SetEscapeId`, `SetDefault`, `wx.Accessible`).
- WCAG 2.2 success criteria: 1.4.3/1.4.11 (contrast), 1.4.10 (reflow),
  1.4.12 (text spacing), 2.1.2 (no keyboard trap), 2.4.3 (focus order),
  2.4.7 (focus visible), 2.4.11 (focus not obscured), 3.3.1/3.3.2/3.3.3
  (error identification, labels, suggestions), 4.1.2 (name/role/value).
- QUILL's shared contract: `apply_modal_ids(...)` and `show_modal_dialog(...)`
  in `quill/ui/dialog_contract.py`, enforced by the DLG-3 / A11Y-4 guards
  (`tests/unit/ui/test_dialog_inventory.py`,
  `tests/unit/ui/test_dialog_hardening_contract.py`,
  `quill/tools/dialog_button_contract.py`).

When any rule below conflicts with QUILL's machine-enforced contract, the
enforced contract wins. Otherwise, treat these as required. This file is the
authoring companion to `docs/qa/dialogs.md` (manual regression map) and the DLG-3
dialog estate governance described in the repository Copilot instructions.

---

## 1. Surface choice (native-first)

| Need | Use | Avoid |
| --- | --- | --- |
| Confirm / yes-no / warning | `wx.MessageDialog` / `wx.RichMessageDialog` | Bespoke `wx.Dialog` |
| One choice from a list | `wx.SingleChoiceDialog` | Hand-rolled list dialog |
| Simple text entry | `wx.TextEntryDialog` | Custom panel plus button |
| File / folder selection | `wx.FileDialog` / `wx.DirDialog` | Custom browser |
| Color / font | `wx.ColourDialog` / `wx.FontDialog` | Custom picker |
| Long progress | `wx.ProgressDialog` / `wx.GenericProgressDialog` | Spinner with no name |
| Rich / multi-control form | hardened `wx.Dialog` (only sanctioned bespoke base) | Any non-`wx` modal surface |

- Native stock dialogs already carry correct roles, names, and platform
  keyboard behavior. Reach for a custom `wx.Dialog` only when no stock dialog
  fits.
- Only `native`, `web` (`show_web_form`), or `hardened_custom` surfaces are
  allowed. Never invent a new modal framework or a non-`wx` modal surface.
- After adding, moving, or removing a dialog, run
  `python -m quill.tools.dialog_inventory --write` and stage
  `tests/unit/ui/fixtures/dialog_inventory.json`.

---

## 2. Focus management

Initial focus, focus order, and focus return are the three things screen-reader
users notice first.

- **Initial focus lands on the first meaningful content control**, not on the
  OK/affirmative button. Opening on OK hides the dialog's purpose from assistive
  technology (AT) users.
  - Prefer text/list/choice/checkbox/slider controls. Set it explicitly with
    `control.SetFocus()` after layout, or route through
    `focus_primary_control(...)` in `quill/ui/dialog_contract.py`.
  - If a dialog deliberately needs focus on a specific control, set it
    explicitly during construction and do not let a helper override it.
- **Tab order matches visual and logical order** (WCAG 2.4.3). Add controls to
  sizers in reading order; use `MoveAfterInTabOrder` only to correct, never as
  the primary layout mechanism.
- **Focus is visible** (WCAG 2.4.7) and **not obscured** (WCAG 2.4.11) by
  overlays, sticky headers, or the dialog chrome itself.
- **Focus is trapped inside the modal** while it is open (this is `ShowModal`'s
  job) but **never trapped against Escape** (see section 3). No path may strand
  focus with no way out.
- **Return focus deterministically on close**: after the modal ends, restore
  focus to the control or editor that launched it. Capture the launcher before
  showing and `SetFocus()` it in a `finally` block.
- Do not move focus programmatically while the user is mid-interaction (for
  example on every keystroke); it disorients AT users.

---

## 3. Default action, Escape, and buttons

Every modal needs exactly one Enter action and one guaranteed Escape path.

- **Affirmative (Enter)**: declare it. With the project contract,
  `apply_modal_ids(dialog, affirmative_id=..., escape_id=...)`. With raw wx,
  `dialog.SetAffirmativeId(id)` and `okBtn.SetDefault()`.
- **Escape (cancel/close)**: declare `escape_id` AND back it with a real path.
  An `escape_id` with no matching button and no `WXK_ESCAPE` handler is a
  keyboard trap (WCAG 2.1.2, the regression behind issue #124). Provide one of:
  - a `wx.Button` carrying that id (for example `wx.Button(parent, id=wx.ID_CANCEL)`),
  - a `CreateButtonSizer` / `wx.StdDialogButtonSizer` that includes it, or
  - an explicit `EVT_CHAR_HOOK` handler that calls `EndModal(escape_id)` on
    `WXK_ESCAPE`.
  The `quill/tools/dialog_button_contract.py` audit enforces this.
- **Button layout**: build buttons with `wx.StdDialogButtonSizer` (or
  `CreateButtonSizer`) so platform button order is correct. Add the sizer with
  `wx.EXPAND`, never `wx.ALIGN_RIGHT` / `wx.ALIGN_CENTER` hacks that break
  reflow.
- **Button labels are specific verbs** where it adds clarity: prefer "Delete
  note" or "Discard changes" over a bare "OK" when the action is consequential.
- **Destructive actions** are not the default button. Make the safe choice
  (Cancel/Keep) the default, and confirm destructive actions explicitly.
- **Show modal through the announcing path**, never a bare `ShowModal()` where
  the contract is mandated: `show_modal_dialog(dialog, title, ...)`.
- **Lifecycle**: a raw `wx.Dialog(...)` must `Destroy()` (or use the
  `with wx.Dialog(...)` form). Pair modeless monitor windows with `EVT_CLOSE`
  bound to `Destroy`.

---

## 4. Accessible naming, roles, and value (WCAG 4.1.2)

Every actionable or informative control must expose an accessible name.

- **Give the dialog a real title** via the `title=` argument (or `SetTitle`).
  AT announces it on open; an untitled dialog is a navigation failure.
- **Label every control.** Either:
  - precede it with a `wx.StaticText` whose text describes it and place them
    adjacent in tab order, or
  - set an explicit accessible name with `control.SetName("...")` (and
    `SetLabel` / `SetHint` where appropriate).
- **Static labels are real text**, so they can be read, zoomed, and translated.
  Do not paint label text onto a bitmap.
- **Icon-only buttons get a name**: `button.SetName("Close")` /
  `SetToolTip("Close")`. A bare icon button announces nothing.
- **Group related controls** with `wx.StaticBox` / `wx.StaticBoxSizer` (radio
  groups, option clusters) so the group name is announced with each member.
- **Expose state**: checkboxes, toggles, and choices must reflect checked/
  selected state through the standard control (do not fake state with color
  alone). Where a custom control is unavoidable, implement a `wx.Accessible`
  subclass exposing `GetName` / `GetRole` / `GetState` / `GetValue`.
- **Required fields are programmatically indicated**, not signaled by an
  asterisk alone: include the word "required" in the label or accessible name.

---

## 5. Announcements and live regions (NVDA / JAWS / Narrator parity)

- **Announce open and close** of the modal with consistent phrasing
  ("Entered [Title] dialog" / "Exited [Title] dialog").
  `show_modal_dialog(...)` does this via its `announce` / `enter_region` /
  `exit_region` hooks; pass them through.
- **Announce outcomes, not mechanics**: report what happened ("Note saved",
  "3 matches replaced"), consistently across NVDA, JAWS, and Narrator.
- **Status and validation updates** that appear without a focus change must be
  announced (a polite live region or status text the AT will read). Do not rely
  on the user discovering a silently updated label.
- **Progress**: long operations use a named progress surface with periodic,
  meaningful updates ("Indexing 40 of 120 files"), not an unlabeled spinner.
- **No surprise focus stealing**: a background completion should announce
  through a live region, not yank focus into a new dialog.
- **Long instructional content** belongs in a focusable, reviewable control
  (`wx.TextCtrl` with `wx.TE_MULTILINE | wx.TE_READONLY`, or a list), not in a
  transient `MessageBox` the user cannot re-read line by line.
- Marshal all cross-thread UI and announcement updates through
  `wx.CallAfter` / `wx.CallLater`; guard with `getattr(wx, "CallAfter", None)`
  for test and headless fallback.

---

## 6. Visual: contrast, high-contrast, motion, zoom

- **Contrast** meets WCAG 1.4.3 (text 4.5:1, large text 3:1) and 1.4.11
  (UI components and state 3:1). Never encode meaning in color alone
  (WCAG 1.4.1): pair color with text, icon, or shape.
- **Respect the system theme.** Pull colors from
  `wx.SystemSettings.GetColour(...)` rather than hard-coding. Verify against
  high-contrast themes and dark mode
  (`wx.SystemAppearance.IsUsingDarkBackground()` / `IsDark()` where available).
  Do not force a light palette onto a dark or high-contrast theme.
- **High-contrast mode**: ensure borders, focus rings, and disabled states stay
  visible; do not rely on subtle drop shadows or low-contrast separators.
- **Reflow and resize** (WCAG 1.4.10): dialogs use sizers (`SetSizerAndFit`) so
  they grow with font scaling and DPI. Test at 200% OS scaling and 200% text
  size; nothing clips or requires two-axis scrolling. Make content-heavy dialogs
  resizable (`wx.RESIZE_BORDER`).
- **Text spacing** (WCAG 1.4.12): layout survives increased line/letter/word
  spacing; avoid fixed pixel heights that clip wrapped text.
- **DPI changes**: handle `EVT_DPI_CHANGED` (or rely on sizers) so the dialog
  re-lays-out cleanly when moved between monitors.
- **Reduced motion**: avoid animated transitions in dialogs; if any animation
  exists, gate it on the platform reduced-motion preference.

---

## 7. Errors, validation, and instructional content (WCAG 3.3)

- **Identify errors in text** (WCAG 3.3.1): say which field and what is wrong,
  in words, not by color or border alone.
- **Move focus to the first error** on a failed submit and announce a summary
  ("2 fields need attention"). Keep the error text programmatically associated
  with its field (adjacent label or `SetName`).
- **Labels and instructions are present before input** (WCAG 3.3.2): describe
  format expectations up front ("Date as YYYY-MM-DD"), not only after a failure.
- **Offer suggestions** (WCAG 3.3.3) when the fix is knowable ("Did you mean
  .docx?").
- **Prefer validators**: `wx.Validator` plus `SetValidator` ties validation and
  data transfer to controls; the stock OK handler runs `Validate()` and
  `TransferDataFromWindow()` automatically.
- **Confirm before destructive or hard-to-reverse actions**, and make the
  confirmation's safe option the default.
- Validation messages are announced via a live region if they appear without a
  focus change (see section 5).

---

## 8. Parent ownership and layout integrity

- Keep the parent/child tree consistent: if controls are parented to a
  `wx.Panel(dialog)`, keep that subtree in the panel's sizer and attach the
  panel to the dialog's outer sizer. **Never attach one root sizer to both the
  panel and the dialog.**
- Use `SetSizerAndFit` so the dialog sizes to content and enforces minimum size.
- Center on parent (`CentreOnParent`) before showing.
- Do not mutate menu items or labels while a menu or dialog is open; defer
  label/enable/check updates until close to avoid focus churn.

---

## 9. Per-dialog change checklist

Before considering any dialog change complete:

- [ ] Surface classified correctly (native / web / hardened custom);
      `dialog_inventory.json` snapshot regenerated and staged.
- [ ] `dialogs.md` updated (new row, binding, or nested/startup note).
- [ ] `apply_modal_ids(affirmative_id, escape_id)` set (or raw
      `SetAffirmativeId` / `SetEscapeId` plus `SetDefault`).
- [ ] Escape id is backed by a real button or a `WXK_ESCAPE` handler (no trap).
- [ ] Shown via `show_modal_dialog(...)` (announce plus region hooks), not a
      bare `ShowModal()` where the contract is mandated.
- [ ] Deterministic initial focus on a content control; focus returned to the
      launcher on close.
- [ ] Dialog title set; every control has an accessible name; groups labeled.
- [ ] Errors identified in text, focus moves to first error, suggestions given.
- [ ] Colors from system settings; verified in dark and high-contrast themes;
      meaning never carried by color alone.
- [ ] Reflows at 200% scale / 200% text; resizable when content-heavy.
- [ ] Raw `wx.Dialog` destroyed (or `with` form); button sizer uses `wx.EXPAND`.
- [ ] At least one focused source-contract or behavior test per dialog bug
      class.
- [ ] Manual NVDA/JAWS/Narrator and keyboard pass logged for shipped dialogs.

---

## 10. wx-specific hardening (often-missed areas)

These come straight from the wxWidgets/Phoenix APIs and close gaps the rules
above do not cover explicitly.

### Mnemonics / access keys

- **Put a mnemonic (`&`) in every actionable label**:
  `wx.Button(parent, label="&Save")`, `wx.StaticText(panel, label="&Name:")`.
  The `&` gives keyboard users an Alt-letter access key and is announced by AT.
- **A label's mnemonic activates the next control in tab order.** Place a
  `wx.StaticText` with `&` immediately before the `wx.TextCtrl` or choice it
  labels so the access key moves focus into that field. This also forms the
  label/field association screen readers rely on.
- **Keep mnemonics unique within a dialog**; duplicates make Alt-letter
  ambiguous.
- To show a literal ampersand, double it (`"Search && Replace"`).

### Accelerators

- Menu and command accelerators are declared with a tab in the item text
  (`"&Open\tCtrl+O"`) so the shortcut is both shown and announced.
- For dialog-local shortcuts use `wx.AcceleratorTable` (or `EVT_CHAR_HOOK`),
  not raw key polling, so the binding is discoverable and consistent.

### Non-modal messaging (do not over-use modals)

- **Prefer `wx.InfoBar`** for inline, dismissible status or validation messages
  above or below content. It is more noticeable than a status bar without the
  workflow interruption of a modal: ideal for "Saved", "Couldn't reach server",
  or inline form errors. Pair it with a live-region announcement (see
  section 5).
- Reserve modals for decisions that must block; transient feedback should not be
  a `MessageBox`.

### Help and descriptions

- Set `SetHelpText(...)` and/or `SetToolTip(...)` on non-obvious controls so
  context help and hover/AT descriptions are available.
- For richer semantics on a genuinely custom control, subclass `wx.Accessible`
  and implement `GetName`, `GetRole`, `GetState`, `GetValue`, and
  `GetDescription`; attach via `SetAccessible(...)`.

### Multi-page dialogs (Notebook / Treebook / wizards)

- **Give every page or tab a real text label** (the `AddPage(page, "General")`
  string); AT announces it on tab change.
- Ensure tab traversal enters each page's content; panels added to a notebook
  inherit `wx.TAB_TRAVERSAL`, so do not disable it.
- On `EVT_NOTEBOOK_PAGE_CHANGED`, announce or move focus to the new page's first
  content control so AT users know context changed.
- For wizards, announce step position ("Step 2 of 4") and keep Back/Next/Finish
  ids and defaults consistent across pages.

### Data tables and lists

- Use **report mode** `wx.ListCtrl` (`wx.LC_REPORT`) or `wx.dataview` controls
  with **named columns** (`InsertColumn(0, "Name")`) so cells are announced with
  their column header.
- Provide selection and activation events (`EVT_LIST_ITEM_SELECTED` /
  `EVT_LIST_ITEM_ACTIVATED`) and make single versus multi-select explicit
  (`wx.LC_SINGLE_SEL`) so AT reports the right selection model.
- Never put actionable controls only in a custom-drawn grid cell with no
  accessible name.

### Window lookup and identity

- Find controls with `wx.FindWindowByName` / `FindWindowById` rather than
  caching fragile references; this also nudges you to set stable `name=` / `id=`
  values, which improve AT identity.

### Recursive validation and persistence

- Set `wx.WS_EX_VALIDATE_RECURSIVELY` (via `SetExtraStyle`) so `Validate()` and
  `TransferData*` reach nested panels, which matters once a dialog uses
  sub-panels or notebooks.
- Persist size and position of resizable dialogs (for example
  `wx.PersistenceManager`) so a user's zoom/reflow layout choices survive reopen
  instead of resetting to a cramped default.

### Window-modal (sheet) dialogs, macOS only

- `dialog.ShowWindowModal()` makes a dialog **window-modal**: on macOS it slides
  down as a sheet attached to the parent window; on other platforms wx falls
  back to app-modal behavior, so it is safe to use cross-platform.
- **It is asynchronous**: unlike `ShowModal()`, it returns immediately and does
  **not** give you a return code inline. Bind
  `wx.EVT_WINDOW_MODAL_DIALOG_CLOSED` and read `event.GetReturnCode()` to get
  the result, then `Destroy()` the dialog there. Do not assume a result on the
  line after the call.
- All other rules still apply: set affirmative/escape ids, ensure Escape has a
  real path, give the dialog a title and accessible names, set deterministic
  initial focus, and announce open/close through the project's region/announce
  hooks (sheets are not automatically announced by every AT).
- Return focus to the launching control after the sheet closes (in the closed
  handler), exactly as with `ShowModal`.
- Do not use `wx.Frame.MakeModal` (removed); a window-modal `wx.Dialog` is the
  sanctioned mechanism.
