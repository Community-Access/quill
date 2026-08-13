# Quill Inkwell -- Product Requirements

Version 1.0.0. Status: implemented.

## 1. Why this exists

QUILL has expanded abbreviations inside its own editor for a long time. The
limitation was obvious to anyone who used it: the moment you leave QUILL -- into
a browser, a mail client, a form, a spreadsheet -- the abbreviations you built up
stop existing.

Quill Inkwell removes that boundary. The same abbreviations, in every
application, from one shared library, free.

## 2. Goals

1. **System-wide expansion** that is fast, reliable, and screen-reader-first.
2. **One library, genuinely shared.** Not an import, not a sync, not a
   read-only mirror -- the same file, read and written by both apps.
3. **Per-entry control.** Case, trigger characters, speech, sound, trailing
   space, and category all belong to the individual abbreviation.
4. **Trustworthy by construction.** A program that watches typing has to be able
   to explain itself in a paragraph, and the code has to match the paragraph.
5. **A family member, not a fork.** Same dialog conventions, same announcement
   service, same sound events, same tray and update mechanics as the sibling
   apps.

## 3. Non-goals

- **Clipboard management.** Inkwell reads the clipboard only to resolve
  `${clipboard}` at the moment an expansion fires, and stores nothing. Clipboard
  history is a different product's job and stays that way.
- **Macros, scripting, and file automation.** Out of scope for 1.0. A second
  automation surface would be a second security surface.
- **A second extension system.** QUILL already has Quillins, which can
  contribute abbreviations. Inkwell uses those; it does not define its own.
- **Cross-platform.** The expansion path is Windows-specific by nature. The
  library and matcher are platform-free, so a future port has somewhere to
  start, but macOS is not in 1.0.

## 4. Architecture

Everything lives in the `quill` package. The standalone shell under
`standalone/inkwell/` only packages it.

| Layer | Module | Responsibility |
| --- | --- | --- |
| Data | `quill/core/abbreviations.py` | The shared library and its schema (v2), matching for the editor, variables. |
| Engine | `quill/core/expansion/ring_buffer.py` | The bounded memory of recent keys. |
| Engine | `quill/core/expansion/matcher.py` | Matching that buffer against the library. |
| Policy | `quill/core/expansion/targets.py` | Where expansion must never fire. |
| Settings | `quill/core/expansion/settings.py` | Inkwell's own preferences. |
| Platform | `quill/platform/windows/expansion_hook.py` | The `WH_KEYBOARD_LL` hook and its threads. |
| Platform | `quill/platform/windows/text_injector.py` | SendInput typing, and the clipboard fallback. |
| Platform | `quill/platform/windows/foreground.py` | What has focus right now. |
| Platform | `quill/platform/windows/inkwell_startup.py` | The per-user Run-key entry. |
| UI | `quill/apps/inkwell.py` | The tray app. |
| UI | `quill/ui/abbreviation_manager_dialog.py` | Shared with QUILL. |
| UI | `quill/ui/quick_insert_dialog.py` | Shared with QUILL. |

The core and engine layers are wx-free and strict-typed, so the matching rules
are testable without a display and without Windows.

### 4.1 Threading

Three threads, with one rule each:

- **The hook thread** runs the `WH_KEYBOARD_LL` procedure and its message pump.
  It decodes a key, appends it to the buffer, and queues any match. It must
  never do more, because Windows silently removes a hook whose procedure is slow
  (`LowLevelHooksTimeout`) -- which would end expansion for the session with no
  error anywhere.
- **The worker thread** performs the injection.
- **The UI thread** owns every widget, every announcement, and every save,
  reached only through `wx.CallAfter`.

### 4.2 Why the hook ignores its own output

Synthesised keystrokes come back through the same hook. Inkwell stamps a
signature into `dwExtraInfo` on every key it sends and skips exactly those.

The obvious alternative -- ignoring all injected keys -- would have been wrong
for this audience: dictation software and on-screen keyboards inject too, and
their users must get expansion like everyone else.

### 4.3 Keyboard layouts

Characters are decoded with `ToUnicodeEx` against the *foreground window's*
keyboard layout, with shift and caps read from the live key state rather than
the hook thread's stale view. A dead key returns nothing and is replayed into the
layout, so composing an accent still works.

AltGr is recognised as typing rather than as a command. Windows reports it as
Ctrl+Alt, so the naive rule ("any Ctrl or Alt means a command") discards real
characters on every layout that uses AltGr -- German, Polish, Spanish,
Portuguese, the Nordic layouts. The test is to ask the layout itself: right Alt
held *and* the key still resolves to a printable character means typing.

### 4.4 Reaching every editable surface

Three rules, all of which fail towards expanding rather than refusing, because a
missed expansion is the more annoying failure -- and the one rule that must fail
closed, the credential deny-list, is separate:

1. **Is this editable?** Checked once, at the moment a match fires, never per
   keystroke -- putting COM calls on the hot path of everything typed would be
   indefensible. A real caret (`GetGUIThreadInfo`) or a known text window class
   is an immediate yes; otherwise UI Automation's focused element decides; and
   if it has no opinion, the answer is yes.
2. **Can we see this window at all?** A normal-privilege process receives no
   keys from an elevated one. That is detected and reported once per window, so
   an administrator application reads as a known limit rather than a fault.
3. **How is the text delivered?** Typed keystrokes by default; the
   clipboard-paste route resolves **per application**, so one stubborn program
   does not cost every other program its clipboard.

### 4.4a One expander per window

QUILL's in-editor expansion and Inkwell's system-wide expansion are both correct
alone and catastrophic together: one keystroke would fire both, erasing and
retyping the same word twice. QUILL therefore sets a window property
(``QuillHandlesOwnExpansion``) on its own frame, and the hook refuses that window
before it even buffers the key.

A window property, not a list of executable names: it identifies the actual
window, so ``python -m quill``, a portable build, and a renamed executable are
all covered. Any future surface with its own expansion can claim it the same way.

### 4.4b Fill-in fields

``${field:Label}`` and ``${field:Label=default}`` make an expansion ask before
it finishes. The rules live in one wx-free module
(``quill/core/expansion/fields.py``) and the form in one shared dialog
(``quill/ui/fill_in_dialog.py``), so a template behaves identically in QUILL's
editor and here -- which matters, because the same library is used from both.

System-wide there is an ordering constraint the editor does not have: the form
takes focus away from the window being typed into. So nothing is erased until
the form is accepted, focus is restored to the original window first, and a
cancelled form costs exactly nothing. The expansion is re-resolved from the
filled template rather than patched afterwards, so ``${cursor}`` still lands
where the template put it once the answers have changed the text's length.

### 4.5 Taking an expansion back

Backspace immediately after an expansion restores the abbreviation. System-wide
there is no document to read, so the tracker remembers what was typed and types
the reverse. The offer expires after a few seconds, on any other keystroke, and
on a change of window -- an undo that fired later would delete text the user has
since written.

### 4.6 Expanding on demand

A system-wide chord expands the word before the cursor without a trigger
character: the counterpart of QUILL's Expand Abbreviation command, and the way
to reach a `manual` entry or to expand mid-word.

### 4.7 Surviving

Windows silently removes a low-level hook whose procedure exceeds
`LowLevelHooksTimeout`, and offers no way to ask whether a hook is still live. A
watchdog re-installs the hook every few minutes, so the worst case is a short gap
rather than the rest of the session.

## 5. Data model

Schema version 2 of `abbreviations.json`, extending v1 with per-entry settings.
Every new field has a default, so:

- a v1 file loads unchanged, and
- a v2 file opened by an older build simply ignores the extra keys and still
  expands.

| Field | Values | Default |
| --- | --- | --- |
| `abbreviation`, `expansion`, `description` | text | -- |
| `enabled`, `case_sensitive` | boolean | true, false |
| `category` | text ("" = Uncategorised) | "" |
| `triggers` | both, space, punctuation, manual | both |
| `speak_mode` | silent, name, expansion | silent |
| `sound` | inherit, on, off | inherit |
| `trailing_space` | boolean | false |
| `usage_count`, `last_used` | integer, ISO timestamp | 0, "" |

Unknown values in a hand-edited file degrade to the safe default rather than
failing the load.

Usage counters are written in batches of ten, never per expansion: a disk write
belongs nowhere near typing.

## 6. Security and privacy contract

This is a requirement, not a description. Each line is enforced in code and
covered by tests.

1. The keystroke buffer holds at most 64 characters, in memory only.
2. Nothing typed is written to disk, logged, or transmitted. There is no network
   call anywhere in the expansion path.
3. The buffer is cleared after every expansion, on Escape, on any navigation or
   editing key, on any Ctrl or Alt combination, on a change of foreground
   window, and on pause.
4. No decision anywhere is made from the *content* of typed characters. The
   suppression rule reads the foreground window's process, class, and title only.
5. Password managers, the Windows credential and lock surfaces, and the UAC
   prompt are permanently excluded; users may add their own.
6. `QUILL_SAFE_MODE=1` prevents the hook from being installed at all.
7. The clipboard is read only when an expansion contains `${clipboard}`, and the
   paste fallback always restores what was there.

## 7. Accessibility requirements

- Every control is labelled and reachable by keyboard; no mouse-only path.
- Dialogs go through QUILL's `_show_modal_dialog` and `apply_modal_ids`, so
  Escape and Enter behave identically everywhere in the family.
- Expansion confirmation is per-entry: silent, the abbreviation, or the full
  text -- because a screen reader has usually already spoken the result, and a
  second announcement is noise for some users and essential for others.
- Failures speak. A refused keyboard hook produces a dialog explaining the
  likely cause, never silence.

## 8. Distribution

- Windows installer and portable zip, built by
  `standalone/inkwell/scripts/build_release.ps1`.
- Shares the QuillVille Runtime with the sibling apps.
- Updates through the shared release repository, resolving its own asset.
- MIT licensed. Free permanently, for everyone.

## 9. Future work

Not committed, in rough order of value:

1. **Rich expansions.** Formatted text where the target accepts it.
3. **Per-application abbreviations.** Entries that only fire in a named app.
4. **Quillin-contributed abbreviations system-wide.** QUILL's editor already
   expands them; Inkwell should too.
5. **macOS.** The library and matcher are already platform-free.
