# QUILL and QuillLite: all items are addressed

Closed 2026-09-18. All twenty-nine rows of the parity audit are done, the three
failures this file recorded as "known red, and none of it ours" are green, and
the six gates it asked for are written and running.

Nothing in this file is load-bearing any more, because everything it held now
lives in the repository:

- **The eleven family rules** are `quill/core/family_rules.py`, cited by number
  from `keymap.py` and `lite/parity.py`, with
  `tests/unit/core/test_family_rules_and_gates.py` checking that every citation
  resolves. Summarised in `CLAUDE.md`.
- **The six gates** are `tests/unit/core/test_family_rules_and_gates.py`
  (bound-command, Quillin hotkeys), `tests/unit/ui/test_menu_shape_against_microsoft.py`,
  `quill/tools/settings_vocabulary_audit.py` (in `platform_report`, 42 gates
  now), `tests/unit/ui/test_documentation_chords.py`, and
  `tests/unit/core/test_large_document_budget.py` (GATE-PERF).
- **Rule 1 itself** is `tests/unit/core/test_microsoft_habits.py`: every chord
  Word, WordPad or Notepad binds for a function both editors have, checked
  against both keymaps. It found the last disagreement on the day it was
  written -- Word's `F12`, `Ctrl+F12` and `Ctrl+Shift+F12` were QUILL aliases and
  not QuillLite's -- and all three are aliases in both now.
- **The decisions** are in `CLAUDE.md` and beside the code they govern.
- **What shipped** is in `CHANGELOG.md` and `standalone/quilllite/docs/CHANGELOG.md`.
- **What a person does with it** is in both user guides, whose chords the
  documentation gate now keeps true.

The next program gets a new file.
