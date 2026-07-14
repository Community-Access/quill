"""Tests for quill.tools._check_binding_label_consistency.

The 4th menu_lint invariant walks the AST of main_frame_menu.py and
flags three regressions:

1. ``_menu_label("", "command.with.binding")`` — empty title routed
   through the builder for a command that has a keybinding.
2. ``<name>\\t<binding>`` literals where the binding portion disagrees
   with what DEFAULT_KEYMAP / the wx stock id would resolve.
3. ``<name>\\t`` — tab at the end with no binding portion.

The real main_frame_menu.py is the integration test (see
``test_run_checks_passes_on_current_codebase`` in test_menu_lint.py).
This file uses synthetic menu snippets to exercise each branch.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make ``quill`` importable when pytest is invoked from a parent dir.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from quill.tools._check_binding_label_consistency import (  # noqa: E402
    _check_empty_label_with_binding,
    _check_manual_tab_literals,
    _check_tab_without_binding,
    run_checks,
)

# ---------------------------------------------------------------------------
# Sub-check 1: empty label routed through _menu_label
# ---------------------------------------------------------------------------


def test_empty_label_with_binding_is_flagged() -> None:
    """The motivating regression: a blank title + a bound command."""
    src = "menu.Append(id, self._menu_label('', 'format.bold'))\n"
    errors = _check_empty_label_with_binding(src, keymap={"format.bold": "Ctrl+B"})
    assert len(errors) == 1
    assert "format.bold" in errors[0]
    assert "Ctrl+B" in errors[0]


def test_empty_label_with_no_binding_passes() -> None:
    """A command with no binding is allowed to have an empty title."""
    src = "menu.Append(id, self._menu_label('', 'help.about'))\n"
    errors = _check_empty_label_with_binding(src, keymap={"help.about": ""})
    assert errors == []


def test_nonempty_label_with_binding_passes() -> None:
    src = "menu.Append(id, self._menu_label('&Bold', 'format.bold'))\n"
    errors = _check_empty_label_with_binding(src, keymap={"format.bold": "Ctrl+B"})
    assert errors == []


def test_i18n_wrapper_resolved() -> None:
    """The ``_('...')`` i18n wrapper is unwrapped to its literal text."""
    src = "menu.Append(id, self._menu_label(_(''), 'format.bold'))\n"
    errors = _check_empty_label_with_binding(src, keymap={"format.bold": "Ctrl+B"})
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# Sub-check 2: manual-tab literal drift
# ---------------------------------------------------------------------------


def test_menu_label_tab_matches_keymap() -> None:
    """A correctly-typed ``<name>\\t<binding>`` literal passes."""
    src = "menu.Append(id, self._menu_label(_('&Save\\tCtrl+S'), 'file.save'))\n"
    errors = _check_manual_tab_literals(src)
    assert errors == []


def test_menu_label_tab_drift_is_flagged() -> None:
    """Tab portion disagreeing with DEFAULT_KEYMAP is flagged."""
    src = "menu.Append(id, self._menu_label(_('&Save\\tCtrl+B'), 'file.save'))\n"
    errors = _check_manual_tab_literals(src)
    assert len(errors) == 1
    assert "file.save" in errors[0]
    assert "Ctrl+B" in errors[0]
    assert "Ctrl+S" in errors[0]


def test_stock_cut_binding_matches() -> None:
    """wx stock items use the conventional Ctrl+X binding."""
    src = 'edit_menu.Append(wx.ID_CUT, _("Cu&t\\tCtrl+X"))\n'
    errors = _check_manual_tab_literals(src)
    assert errors == []


def test_stock_cut_binding_drift_is_flagged() -> None:
    """If someone hand-edits the wx.CUT literal, the gate flags it."""
    src = 'edit_menu.Append(wx.ID_CUT, _("Cu&t\\tCtrl+Y"))\n'
    errors = _check_manual_tab_literals(src)
    assert len(errors) == 1
    assert "Cu&t" in errors[0]
    assert "Ctrl+Y" in errors[0]
    assert "Ctrl+X" in errors[0]


# ---------------------------------------------------------------------------
# Sub-check 3: tab-without-binding
# ---------------------------------------------------------------------------


def test_trailing_tab_is_flagged() -> None:
    src = 'menu.Append(id, _("&Save\\t"))\n'
    errors = _check_tab_without_binding(src)
    assert len(errors) == 1
    assert "Save" in errors[0]


def test_no_tab_passes() -> None:
    src = 'menu.Append(id, _("&Save"))\n'
    errors = _check_tab_without_binding(src)
    assert errors == []


def test_proper_tab_binding_passes() -> None:
    src = 'menu.Append(id, _("&Save\\tCtrl+S"))\n'
    errors = _check_tab_without_binding(src)
    assert errors == []


# ---------------------------------------------------------------------------
# Integration: live source
# ---------------------------------------------------------------------------


def test_run_checks_clean_against_real_menu_source() -> None:
    """The current main_frame_menu.py satisfies the new check."""
    errors = run_checks()
    assert errors == [], "\n".join(errors)
