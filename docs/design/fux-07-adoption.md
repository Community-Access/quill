# FUX-07 adoption: dictated and expanded text goes only to the intended place

Date: 2026-11-23. Scope: every path in the QUILL family that types into another
program's window. Earshot and macOS are out of scope.

The rule, from [the family UX pilots, section 4](2026-11-19-family-ux-pilots.md):
text is inserted only into the target that was current when the input began.
If the target's identity changes, or cannot be confirmed, the text is kept and
offered as Insert or Copy. It is never typed somewhere else, and never read
aloud unasked. A secure or password field is refused only where the platform
can tell, and nothing claims to detect one where it cannot.

## How a target is identified

Two identities exist, and both are now built from the same three facts: the
foreground window handle, its process id, and the focused control.

- **Dictation** (`focus_identity` in `quill/ui/windows_dictation_external.py`):
  `(window, process, control)`, where the control is UI Automation's runtime
  id, else UI Automation's native window handle, else the focused window
  handle Windows reports for the foreground thread (`focused_window_handle` in
  `quill/platform/windows/text_target.py`). No window in front gives `None`,
  which never equals a locked field.
- **Inkwell's text runtime** (`TargetSnapshot.same_identity` in
  `quill/core/external_text.py`, built by `probe_focused_target` in
  `quill/platform/windows/external_target.py`): target id, window, process and
  control id. The control id now falls back to the focused window handle
  before the class name.

Before this change both fell back to the focused window's *class name* when UI
Automation had nothing, and two edit boxes in one dialog share a class.

A restarted program gets a new process id (and normally a new window handle),
so it is never the same target. A password field is refused when UI
Automation's `IsPassword` says so, and by the deny-list of password managers
and sign-in windows (`quill/core/expansion/targets.py`). Neither is described
to the user as a general password detector.

## The insertion paths

| # | App | Path (file) | How it picks the target | Re-checked before typing? (before) | Gap | Fix |
|---|-----|-------------|-------------------------|-----------------------------------|-----|-----|
| 1 | Transcribe, Inkwell | Live dictation: `locked_external_document` wrapping `ExternalDocument` in `LockedTarget` (`quill/ui/windows_dictation_external.py`, `quill/core/windows_dictation/target_lock.py`) | Field in front when the session starts | Yes: before every phrase and again inside `insert`; a mismatch pauses and holds (`target_hold.py`) | Identity fell back to the control's class name, so two edit boxes without UI Automation were "the same field"; Windows unable to name the window gave an identity that could match | Control falls back to the focused window handle; no foreground window gives `None` (never a match). Tests: `tests/unit/core/test_dictation_destination.py` |
| 2 | Transcribe, Inkwell | Resume / Resume in This Field / Discard Held Words (`target_hold.py`, `quill/ui/dictation_field_hold.py`) | Resume: the locked field; Resume in This Field: relocks after the start checks | Yes | None found | Covered by the identity fix in row 1 |
| 3 | Transcribe | Review Dictation's Insert (`quill/apps/transcribe_review.py`) | Brings the locked window forward, then writes through the locked document | Yes (the lock), and a refusal leaves the words in Recent Phrases for Insert Again or Copy | None found | None needed |
| 4 | Transcribe, Inkwell | Recent Phrases' Insert Again, Review Transcript's Type into a Field (`quill/apps/transcribe_recent.py`, `quill/ui/windows_dictation_tools.py`) | A one-shot `LockedTarget` on the program you switch to after choosing it | Yes | None found: the person chooses the target at the moment of insertion | None needed |
| 5 | Transcribe | Starting from the tray (arming, `quill/core/transcribe/arming.py`) | The next program you return to | Yes, as row 1 | None found | None needed |
| 6 | Inkwell | System-wide expansion (`quill/platform/windows/expansion_hook.py` then `InkwellExpansionMixin._inject` in `quill/ui/inkwell_expansion.py`) | Should be the window the abbreviation was typed in | Intended (`expected_window=match.target_window`), but `GlobalMatch` had no `target_window` field, so every expansion raised in the worker and typed nothing | **Broken**: no expansion reached any program; no target recorded at input start | `GlobalMatch.target_window` set by the hook when the abbreviation completes (and by Expand Word); the runtime re-checks it at typing time; a refusal says "Not expanded, because ..." and the abbreviation stays as typed |
| 7 | Inkwell | Expansion with fields (`_expand_with_fields`) | Foreground window before the fill-in form | Window only; the focused control was not compared, and a refusal lost the filled-in answers | Focus restored to another control in the same window, or not restored, typed nowhere and lost the text; nothing captured the control | The focused control is captured before the form (`_destination_now`), the window must still match the hook's, and typing goes through `InkwellDestinationMixin._insert_held` with `expected_target`; on mismatch the text is kept and Text Not Typed offers Insert or Copy |
| 8 | Inkwell | Quick Insert (`open_quick_insert`, moved from `quill/apps/inkwell.py` to `quill/ui/inkwell_destination.py`) | Foreground window handle before the picker | **No**: forced the window forward and typed 150 ms later with unchecked `inject_expansion` into whatever was in front; no password, administrator or partial-delivery check | Text could be typed into the wrong program if bringing the window back failed | Same as row 7: captured before the picker, checked by `InkwellTextRuntime` with `expected_target`, kept and offered on mismatch |
| 9 | Inkwell | Undo after an expansion (Backspace, `_on_global_undo`) | Hook checks the Backspace came in the same window | **No** at typing time: unchecked `inject_expansion` on the worker | Small window, but typed blind | `UndoPlan.window_handle` carries the window; the undo types through the checked runtime with `expected_window`, and says "Not undone, because ..." otherwise |
| 10 | Cast, Radio (via Transcribe) | Edit > Dictate Here (`quill/core/windows_dictation/dictate_here.py`, `quill/ui/dictate_here_ui.py`) | The `start` request carries no target; Transcribe locks whatever is in front when it answers (under a second when running, several seconds when it has to start) | No | If the focus moved before Transcribe answered, dictation started somewhere else, while Cast or Radio had said "Dictation starts here" | The request (and the launch command line, `--dictate-here-place`) carries the field's place -- window, process, focused control window (`focus_place`) -- taken when the key is pressed; Transcribe starts only if `still_there`, else says `left_sentence` and starts nothing. A request naming no field (an older Cast or Radio) starts as before. Tests: `tests/unit/core/test_dictate_here.py` |
| 11 | Inkwell | AI rewrite of a selection in another program (`InkwellTextRuntime.replace_selection`, `quill/apps/inkwell_ai.py`) | The focused target at capture | Yes: compare-before-write of target and selection (`text_transaction.py`) | None found | None needed |
| 12 | QUILL, QUILL Lite | Dictation and expansion inside the editor | The editor's own document | Not cross-window | Out of FUX-07's scope | None |

## What "offer Insert or Copy" looks like

- **Dictation** keeps its existing pause: Resume, Resume in This Field and
  Discard Held Words, in the tray menu and the Dictation menu, with held words
  also kept sealed on disk for Recent Phrases (Insert Again, Copy).
- **Inkwell's one-shot insertions** (rows 7 and 8) show **Text Not Typed**
  (`quill/ui/held_text_dialog.py`): one sentence from
  `quill/core/expansion/destination.py`, which names the reason and the
  choices and never contains the text; **Insert** (Alt+I, offered only where
  trying again can work: the focus moved or Windows could not answer), **Copy**
  (Alt+C), and Cancel (Escape). The window's sentence is read with its title
  when it opens, and nothing else announces it (GATE-13). Insert goes back to
  the *same* target and checks it again; it never types into a new one.
- **Inkwell's typed-as-you-go expansions and undo** (rows 6 and 9) have
  nothing to keep: nothing was erased, the abbreviation is still on screen.
  They say one sentence with the reason.

## Acceptance items from the plan

| Item | Where it is met |
|------|-----------------|
| The user can determine the current target and whether insertion is live or pending | Dictation Status (Transcribe, Alt+F9 and its key) names the locked program and the held count; Inkwell's Text Not Typed window is the pending state of a one-shot insertion |
| Alt+Tab, dialogs, closed controls and restart cannot redirect a pending insertion silently | Identity of window, process and control, re-checked at typing time on every path in the table; tests fake each change |
| Ambiguous targets preserve text instead of losing it | Dictation holds; Inkwell keeps the text in Text Not Typed; an unreadable focus is never the same target |
| Literal/escape path and usable undo where the target allows it | Unchanged: the literal path is the trigger mode and Expand Word; the Backspace undo now types only in its own window |
| Password/secure controls follow explicit platform-supported restrictions | UI Automation `IsPassword` and the deny-list only; the user guide says Inkwell cannot tell a password field that does not say so to Windows |
| Explain target failures without reading private text aloud | Every sentence is built from a reason code; `HeldText.__repr__` hides the words; tests assert the text is absent |
| Test with actual supported receiving applications and assistive tools | Not done here: see below |

## What only a live check can show

Unit tests fake the target identity; they cannot show what real programs
report. These need a person at a Windows machine with NVDA and JAWS, on a
source run and on the frozen build:

- Inkwell expansions type again in Notepad, Word, Outlook, Chrome, Edge,
  Firefox and an Electron app (for example Teams or VS Code), after this fix.
- Quick Insert and a fields snippet type into the same field after the picker
  or form closes, in each of those, including Outlook's To and Subject boxes
  and a browser form with several text fields.
- That Windows' focus-stealing prevention does not stop Inkwell bringing the
  window back from the tray-launched picker; when it does, Text Not Typed
  appears and Insert succeeds once the person returns.
- That UI Automation runtime ids stay stable while a field keeps the focus in
  Chrome, Edge, Firefox, Word and Outlook; if one changes on its own, dictation
  would pause there with no move.
- A browser password field and a Windows sign-in prompt are refused, and
  Text Not Typed offers Copy only.
- NVDA and JAWS read Text Not Typed's sentence once, with its title, and do not
  read the text.
- Cast's and Radio's Dictate Here with QUILL Transcribe both running and
  starting from closed, moving the focus in between.
