# QUILL Keybinding Standard

This document is the canonical reference for the keybinding rules QUILL
follows. The gate that enforces these rules lives in
`quill/tools/menu_lint.py` (GATE-12).  Any change to this document must be
reflected in the gate and vice versa.

## §10.1 The QUILL-key chord space

Most editor commands bind to one of two kinds of chord:

1. **A standard modifier chord** (`Ctrl+X`, `Alt+Y`, `Ctrl+Shift+Z`, etc.)
   for actions the user reaches for in a sighted editor and that no
   screen reader intercepts app-globally.
2. **A QUILL-key chord** of the form `Ctrl+Shift+Grave, <second-key>` for
   everything else.  The grave-prefix is easy to type without looking, has
   no native screen-reader collision, and chains naturally so that the
   user's left hand never leaves the home row.

The default-second-key is single-character.  Shift variants use the
`Shift+` prefix on the second key (`Ctrl+Shift+Grave, Shift+J`).

> **Display form.** The chord is shown to the user as `QUILL Key + <key>`
> in menus, the About > Keyboard Reference page, the QUILL Key Help
> dialog, the cheat sheet, and the status bar. The stored grammar
> (`Ctrl+Shift+Grave, <key>`) is unchanged; only the user-visible label
> moves. The rewrite happens through
> `quill.core.keymap_format.format_binding_for_display`, and the brand
> itself is `QUILL_KEY_LABEL` in `quill/branding.py`. This document
> continues to use the stored grammar so it can serve as the canonical
> reference for the keymap; the user-facing surfaces use the display form.

## §10.2 The Ctrl+Alt+ policy (revised 0.7.0)

`Ctrl+Alt+` is screen-reader-hostile because NVDA, JAWS, and Windows
Speech Recognition intercept most of those chords app-globally.  For
years QUILL's policy was a flat ban.

In 0.7.0 the policy is relaxed: a `Ctrl+Alt+` binding may enter
`DEFAULT_KEYMAP` when **either**:

* the command id is in the `_CTRL_ALT_DOCUMENTED` allowlist in
  `quill/tools/menu_lint.py`, or
* the binding line in `keymap.py` ends with the inline comment
  `# §edsharp-ok — <justification>`.

The rename from `_CTRL_ALT_ALLOWED` to `_CTRL_ALT_DOCUMENTED` makes the
narrower scope explicit: the allowlist is now "documented exceptions,"
not a free pass.

### Documented bindings (allowlist, as of 0.7.0)

| Command id                          | Chord                | Justification                                          |
|-------------------------------------|----------------------|--------------------------------------------------------|
| `view.send_to_tray`                 | `Ctrl+Shift+Grave, T`        | Allowlisted for legacy `Ctrl+Alt+T`; now bound to the QUILL-key chord (see Migration map). |
| `view.toggle_tab_control`           | `Ctrl+Shift+Grave, Shift+T`  | Allowlisted for legacy `Ctrl+Alt+Shift+T`; now bound to the QUILL-key chord (see Migration map). |
| `format.heading_1`                  | `Ctrl+Alt+1`         | Overrides NVDA switch-to-synth-1.                      |
| `format.heading_2`                  | `Ctrl+Alt+2`         | Overrides NVDA switch-to-synth-2.                      |
| `format.heading_3`                  | `Ctrl+Alt+3`         | Overrides NVDA switch-to-synth-3.                      |
| `format.heading_4`                  | `Ctrl+Alt+4`         | Overrides NVDA switch-to-synth-4.                      |
| `format.heading_5`                  | `Ctrl+Alt+5`         | Overrides NVDA switch-to-synth-5.                      |
| `format.heading_6`                  | `Ctrl+Alt+6`         | Overrides NVDA switch-to-synth-6.                      |
| `format.toggle_bullet_list`         | `Ctrl+Alt+7`         | Overrides NVDA review-cursor (EdSharp port).           |
| `format.toggle_numbered_list`       | `Ctrl+Alt+8`         | Overrides NVDA review-cursor (EdSharp port).           |
| `tools.ai_spell_check`              | `Ctrl+Alt+Shift+S`   | AI reserved chord class (#357).                        |
| `tools.ai_spell_check_interactive`  | `Ctrl+Alt+Shift+I`   | AI reserved chord class (#357).                        |
| `tools.ai_grammar_style`            | `Ctrl+Alt+Shift+G`   | AI reserved chord class (#357).                        |
| `tools.ai_translate_selection`      | `Ctrl+Alt+Shift+T`   | AI reserved chord class (#357).                        |
| `tools.ai_thesaurus`                | `Ctrl+Alt+Shift+H`   | AI reserved chord class (#357).                        |
| `tools.compare_next_difference`     | `Ctrl+Alt+Shift+.`   | Compare reserved chord class (#357).                   |
| `tools.compare_previous_difference` | `Ctrl+Alt+Shift+,`   | Compare reserved chord class (#357).                   |
| `tools.compare_announce_difference` | `Ctrl+Alt+Shift+D`   | Compare reserved chord class (#357).                   |

NVDA's switch-to-synth-N has a documented QUILL-key alternative
(`Ctrl+Shift+Grave, <N>`) for users who want both behaviours.

The AI and compare chord classes share `Ctrl+Alt+Shift+<letter>` and
`Ctrl+Alt+Shift+<punct>` respectively. They were chosen because F8,
Shift+F8, and Ctrl+F8 (the previous inline accelerators) collided with
the selection bindings `edit.start_selection` / `edit.complete_selection`
/ `edit.reselect`. The chord class is documented as a reservation so
future AI / compare work reuses the modifier stack instead of inventing
a new one.

### The `# §edsharp-ok` escape hatch

A `Ctrl+Alt+` binding outside the allowlist passes the gate if the line
ends with the comment `# §edsharp-ok`.  The comment must name the
screen-reader binding the chord overrides (e.g. "overrides NVDA
review-cursor").  This is the path for one-off bindings that need a
documented exception without growing the global allowlist.

### Process for adding a new `Ctrl+Alt+` binding

1. Add the command id to `_CTRL_ALT_DOCUMENTED` in `menu_lint.py` if
   the binding is permanent.  Skip this step if the binding is one-off
   and you'll use the inline escape hatch instead.
2. In `keymap.py`, append the `# §edsharp-ok` comment to the binding
   line (or update the comment to reference the new justification).
3. Add a row to the table above with the screen-reader binding the
   chord overrides.
4. Add a test to `tests/unit/tools/test_menu_lint.py` covering the new
   allowlist entry or the inline escape-hatch path.
5. Document the new chord in `docs/CONTROL_REFERENCE.md`.

## §10.3 Tools-menu clusters

The Tools menu is organised into the nine clusters listed in
`_REQUIRED_CLUSTER_LABELS` in `menu_lint.py`.  Every cluster name must
appear as a menu label in `main_frame_menu.py`; a missing cluster name
fails the gate.

## §10.4 Two-level cap

No Tools-menu item may be more than two submenu levels deep.  The
gate rejects any `wx.Menu()` variable that is itself a child of a
submenu *and* has `AppendSubMenu` calls of its own (which would create
a three-level chain).

## Migration map

The following legacy bindings are rewritten on load by
`merge_keymaps` so a user with a saved pre-0.7.0 keymap is silently
routed to the new chord without losing muscle memory:

| Legacy chord                        | New chord                              | Reason                          |
|-------------------------------------|----------------------------------------|---------------------------------|
| `Ctrl+Alt+T`                        | `Ctrl+Shift+Grave, T`                  | view.send_to_tray               |
| `Ctrl+Alt+Shift+T`                  | `Ctrl+Shift+Grave, Shift+T`            | view.toggle_tab_control         |
| `Ctrl+Shift+Grave, 1..6` (heading)  | `Ctrl+Alt+1..6`                        | EdSharp port, PR2               |
| `Alt+Shift+Up/Down` (expand/shrink) | `Ctrl+Shift+Grave, J / Shift+J`        | EdSharp port, PR1               |

See `docs/release notes/release0.7.0.md` for the per-PR changelog.