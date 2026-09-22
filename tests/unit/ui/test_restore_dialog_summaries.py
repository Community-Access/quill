"""Both startup choosers carry a read-only field, and keep it in step.

What the field *says* is tested wx-free in
``tests/unit/core/test_restore_plan_text.py``. What is held here is the wiring,
which is the half that can rot silently: a field that is built and never
rebound describes the window as it was when it opened, and nothing about it
looks wrong.

Asserted against the source rather than a live dialog. Putting a real modal up
in the suite is what the UIA tests are for, and this is the seam that actually
breaks -- somebody adds a checkbox and forgets the ``Bind``, or swaps
``ChangeValue`` for ``SetValue`` and the field starts talking over the reader.
"""

from __future__ import annotations

import inspect

import pytest


@pytest.fixture(params=["recovery", "session"])
def chooser(request):
    """The two windows, so every rule below is asserted of both."""
    if request.param == "recovery":
        from quill.ui import recovery_dialog

        return inspect.getsource(recovery_dialog.ask_recovery)
    from quill.ui import session_restore_dialog

    return inspect.getsource(session_restore_dialog.ask_session_restore)


def test_it_has_a_read_only_multiline_field(chooser: str) -> None:
    """Read-only, so nothing in it can be typed into or changed by accident."""
    assert "wx.TE_MULTILINE | wx.TE_READONLY" in chooser


def test_the_field_is_a_text_control_not_a_static_text(chooser: str) -> None:
    """A text control is focusable: Tab reaches it and arrows read it.

    A long StaticText can only be heard once, whole, if it happens to be
    announced -- which for a paragraph describing five buttons is no use.
    """
    assert "summary = wx.TextCtrl(" in chooser


def test_the_field_carries_an_accessible_name_and_help(chooser: str) -> None:
    assert 'set_accessible_name(summary, "What this would do")' in chooser
    assert "summary.SetHelpText(" in chooser


def test_every_checkbox_updates_the_field(chooser: str) -> None:
    """Including the ones rebuilt after a row is removed.

    Twice, deliberately: once for the boxes the window opens with, and once
    inside the rebuild. The rebuild is where this goes wrong, because the
    original binding is destroyed with the box that carried it.
    """
    assert chooser.count("box.Bind(wx.EVT_CHECKBOX, _refresh_summary)") == 2


def test_the_field_is_filled_before_the_window_is_shown(chooser: str) -> None:
    """An empty field on arrival is a field nobody trusts afterwards."""
    assert "_refresh_summary()" in chooser


def test_the_field_is_refilled_after_rows_are_rebuilt(chooser: str) -> None:
    assert chooser.count("_refresh_summary()") >= 2


def test_it_uses_changevalue_so_it_does_not_talk_over_the_reader(chooser: str) -> None:
    """``SetValue`` fires a text event; ``ChangeValue`` does not.

    A read-only field that announced itself on every tick would talk over the
    reader saying "checked", which is the announcement the person asked for by
    pressing Space (GATE-13).
    """
    assert "summary.ChangeValue(" in chooser
    assert "summary.SetValue(" not in chooser


def test_the_recovery_field_describes_the_list_as_it_now_stands() -> None:
    """Rows can leave the window; the description must leave with them.

    The counts of what was tidied *before* the window opened are carried across
    deliberately -- they are still true, and they are the part somebody most
    needs not to have silently vanish.
    """
    from quill.ui import recovery_dialog

    source = inspect.getsource(recovery_dialog.ask_recovery)
    assert "def _live_triage() -> Triage:" in source
    assert "offer=tuple(live)" in source
    assert "duplicates=result.duplicates" in source
    assert "stale=result.stale" in source


def test_the_session_field_describes_the_list_as_it_now_stands() -> None:
    from quill.ui import session_restore_dialog

    source = inspect.getsource(session_restore_dialog.ask_session_restore)
    assert "describe_session_plan(" in source
    assert "tuple(live)" in source
