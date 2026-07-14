# macOS VoiceOver accessible names (#1012)

**Status:** implemented, awaiting live VoiceOver validation on macOS.

## The problem

On macOS, most input controls in Settings and other dialogs were announced by
VoiceOver with only their *value* — the Font size spin box read "0", the SSH
port read "22" — with no indication of what the value was for.

The same controls read correctly on Windows because NVDA/JAWS infer a
control's name from the neighbouring `wx.StaticText` (and the `&`-mnemonic),
and wxMSW exposes that association through MSAA/UIA. **VoiceOver does not
synthesize that association**: a control is announced only by its own
`NSAccessibility` label — and wxOSX never sets one. Two root causes:

* **Cause A** — the control relies on a neighbouring `StaticText` and never
  calls `SetName()`.
* **Cause B** — `wx.SpinCtrl` / `wx.SpinCtrlDouble` on macOS is a composite
  (inner `NSTextField` + stepper). VoiceOver lands on the inner text field,
  which does **not** inherit the composite's name, so even spin controls that
  set a name read as a bare number (support#69).

### The mechanism (learned the hard way)

Issue #1012 assumed wxOSX maps `wx.Window.SetName` to the NSAccessibility
label. **Live VoiceOver testing disproved that**: wx's accessibility plumbing
(`wxAccessible`) is MSW-only, and wxOSX bridges *nothing* into
NSAccessibility — every `SetName` in the codebase (including the two
"working" workarounds the issue cited) was inaudible on macOS. The existing
#616 editor role pin was likewise a silent no-op: on macOS `GetHandle()`
returns the `NSView` as a bare *integer*, and calling `getattr(int,
"setAccessibilityRole_")` finds nothing.

What actually talks to VoiceOver: wrap the handle with PyObjC —
`objc.objc_object(c_void_p=ctrl.GetHandle())` — and call
`setAccessibilityLabel_(name)` on the resulting `NSView` (for multiline text
controls, also on the scroll view's `documentView`, which is what VoiceOver
focuses). PyObjC is already bundled by the `[macos]` extra. `SetName` is
still applied everywhere (it feeds the label inference, tests, and the
Alt+F1 announcer), but the native push is the part macOS hears.

## The fix — one global mechanism, not per-site edits

Everything lives in `quill/ui/accessible_names.py`:

* `ensure_accessible_names(root)` walks a widget tree in creation order and
  gives every *labelable* control (text fields, choices, combos, lists, trees,
  spins, sliders, gauges, pickers — see `_LABELABLE_CLASSES`) that still has
  wx's *default* window name an accessible name inferred from the nearest
  preceding `StaticText` — the same association Windows already makes.
  Mnemonics (`&`), trailing `:` and ellipses are stripped. Composite controls
  (Cause B) propagate their name onto their default-named inner children —
  including spins that were already named composite-only.
* `set_accessible_name(ctrl, label)` is the explicit per-control helper for
  surfaces the walker cannot reach; it performs the same cleanup and inner
  child propagation.

### Where the walker runs

1. **`quill.ui.dialog_contract.show_modal_dialog`** — the choke point every
   modal dialog already routes through (`MainFrame._show_modal_dialog`
   delegates here; standalone dialogs call it directly). This fixes all
   ~120 previously unnamed dialog controls at show time with no per-site
   edits, and covers future dialogs automatically. The call is guarded — a
   naming failure can never block a dialog from opening.
2. **Settings lazy pages** — the Settings dialog builds pages on first
   selection, *after* the show-time pass, so `_build_page` in
   `main_frame.open_general_preferences` re-runs the walker after each page
   builds (idempotent).

### Hard safety rules

* **Explicit names are never overwritten.** Window names are overloaded in
  QUILL: F1 context help uses `GetName()` as its topic key
  (`quill/ui/context_help.py`, e.g. `name="wizard.kb_pack_choice"`), and
  `quill/ui/audio_studio/wizard.py` locates widgets with `FindWindowByName`.
  The walker touches only controls whose name is still a wx default
  (`"text"`, `"choice"`, `"wxSpinCtrl"`, ...).
* **Prose is not a label.** A `StaticText` longer than 60 characters or
  containing a sentence break is treated as instructions: it never becomes a
  control name, and it clears any pending label.
* **Names are applied on all platforms.** wxMSW stores the window name as an
  inert string — MSAA/UIA never read it — so Windows screen-reader behaviour
  is unchanged (verified: NVDA/JAWS names come from the native label
  association, not the wx name). Running everywhere keeps the walker
  exercised by Windows CI.

## The gate — new controls cannot regress

`quill/tools/accessible_name_audit.py` AST-scans every `quill/**/*.py` for
labelable-control constructions and compares against the committed snapshot
`tests/unit/ui/fixtures/accessible_name_inventory.json`
(gate: `tests/unit/ui/test_accessible_name_inventory.py`). Each site is
classified:

| Status | Meaning |
| --- | --- |
| `named` | Names itself inline (constructor `name=`, `SetName`, or `set_accessible_name`) — auto-verified by the scan. |
| `modal-hook` | Lives in a dialog shown via `show_modal_dialog`; named at show time by the walker. |
| `named-elsewhere` | Named by code the inline scan cannot see. |
| `opt-out` | Deliberately nameless (justify in the diff). |

Adding a labelable control fails the gate until
`python -m quill.tools.accessible_name_audit --write` is run and the diff is
reviewed — a control on a *non-modal* surface must not be left `modal-hook`.
The snapshot is therefore also the authoritative list of deviations.

## Deviations from the global fix

* **Non-modal surfaces** (never pass through `show_modal_dialog`) are named
  explicitly: the document editor (`SetName("Document")`, pre-existing), the
  CSV surface (`CSV grid` / `CSV text`), the Word structure surface
  (`Word view` / `Document text`), and the sticky-notes vault list/preview
  (`Sticky notes` / `Note preview` — its only preceding text is prose).
* **Machine-key names remain machine keys.** Controls named for F1 help
  topics (`info_pages.py`, `setup_wizard_pages.py`, `guided_speech_dialog.py`,
  devtools console, ...) keep those names, so VoiceOver reads e.g.
  "wizard.kb_pack_choice". Pre-existing behaviour, out of scope here; fixing
  it means giving the help system its own key channel (follow-up candidate).
* **Controls with no visible label anywhere** stay unnamed unless a site
  names them (the walker returns them as leftovers; the audit keeps them
  visible). Fixed-by-hand cases so far: sticky-notes vault.

## VoiceOver test surface

The fix is one shared code path, so testing does not require visiting all
~570 control sites. Verify the mechanism once per *pattern*, then spot-check.
Expected result everywhere: VoiceOver announces **"<label>, <value>"** (e.g.
"Font size, 12"), not a bare value.

| # | Pattern exercised | Where to test | What to check |
| --- | --- | --- | --- |
| 1 | Settings **eager page** (page 0) text/choice fields | Settings, first page | Fields announce their label |
| 2 | Settings **lazy page** + `int` spin (Cause B) | Settings → a later page with a number field, e.g. Font size / Read Aloud rate | Spin announces label + number; arrows still adjust |
| 3 | Hand-rolled dialog, label + `TextCtrl` (Cause A) | Pronunciation dictionary → Add entry ("Word or phrase") | Text field announces "Word or phrase" |
| 4 | Composite-only-named spin, `StaticBoxSizer` contents | Voice Browser (Read Aloud voices): Rate / Volume / Pitch / Speed | Each spin announces its label |
| 5 | SSH port spin (named composite, previously bare "22") | SSH Quick Connect dialog | "Port, 22" |
| 6 | Label + row-panel field (label outside the row container) | Settings → sound pack / abbreviation sound rows | Field announces its label |
| 7 | Non-modal editor surfaces | Open a .csv and a .docx | Grid/text announce "CSV grid"/"CSV text"; Word view announces "Word view"/"Document text"; main editor announces "Document" |
| 8 | No-label controls (explicit names) | Sticky Notes vault | List announces "Sticky notes", preview "Note preview" |
| 9 | Explicit-name preservation (F1 keys) | Setup wizard; F1 on a wizard field | F1 help still resolves; names unchanged (reads the machine key — known deviation) |
| 10 | Windows regression check (NVDA/JAWS) | Same dialogs as 1–5 on Windows | Announcements unchanged from before the fix |

If a specific control still reads as a bare value on macOS, it is either
explicitly machine-named (deviation 2), has no preceding `StaticText`
(deviation 3 — name it with `set_accessible_name`), or is built lazily after
its dialog was shown (re-run `ensure_accessible_names` after building, as
Settings does).

## Build for testing

No Mac is needed to produce a test build: dispatch the **macos-test-build**
GitHub Actions workflow (Actions tab → macos-test-build → Run workflow on the
fix branch). It produces an unsigned, ad-hoc-signed `Quill-test-unsigned.zip`
artifact — on the test Mac, unzip and either right-click → Open (twice) or
`xattr -dr com.apple.quarantine Quill.app`, then launch and test with
VoiceOver (Cmd+F5). Signed builds still come from `macos-release.yml` only.
