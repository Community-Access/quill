"""Drive Report Fields without showing it: unknown ids are dropped, Add, Move
and Remove keep the order and say what happened, and the meaning follows
whichever control changed."""

from __future__ import annotations

import pytest

from quill.core.weather.nowcast import FIELD_CATALOG
from quill.ui.weather.report_fields_dialog import ReportFieldsDialog
from tests.wx_session import shared_wx_app


@pytest.fixture
def app():
    a = shared_wx_app()
    yield a
    a.Destroy()


def test_add_move_and_remove(app) -> None:
    said: list[str] = []
    dlg = ReportFieldsDialog(None, chosen=["cape", "nope"], announce_cb=said.append)
    try:
        assert dlg.chosen == ["cape"]
        dlg._available.SetSelection(0)  # wind gusts, first in the catalogue
        dlg.add()
        assert dlg.chosen == ["cape", "wind_gusts_10m"]
        assert said[-1] == "Added Wind gusts."
        dlg._list.SetSelection(1)
        dlg.move(-1)
        assert dlg.chosen == ["wind_gusts_10m", "cape"]
        assert said[-1] == "Moved Wind gusts to 1 of 2."
        dlg._list.SetSelection(0)
        dlg.remove()
        assert dlg.chosen == ["cape"] and said[-1] == "Removed Wind gusts."
    finally:
        dlg.dialog.Destroy()


def test_the_meaning_follows_the_control_that_changed(app) -> None:
    dlg = ReportFieldsDialog(None, chosen=["cape"])
    try:
        dlg._list.SetSelection(0)
        dlg._sync(source="list")
        assert dlg._meaning.GetValue() == FIELD_CATALOG["cape"].help
        dlg._available.SetSelection(0)
        dlg._sync(source="available")
        assert dlg._meaning.GetValue() == FIELD_CATALOG["wind_gusts_10m"].help
    finally:
        dlg.dialog.Destroy()
