"""New and Edit Membership Level, through pmpro/v1/membership_level (complete.md 2.3)."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import workbench_pmpro_levels as lv  # noqa: E402
from quill.core.wordpress.workbench_plugin_actions import PLUGIN_NEW_HERE  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_rest_limits import SITE, bench  # noqa: E402

__all__ = ["bench"]

_GOLD = {
    "id": 2,
    "name": "Gold",
    "initial_payment": "10",
    "billing_amount": "5",
    "cycle_number": "1",
    "cycle_period": "Month",
    "expiration_number": "0",
    "allow_signups": "1",
}
_LEVELS = NodeRef("site", "membership_levels", SITE)


# -- the wx-free half ----------------------------------------------------------------


def test_amounts_are_kept_to_the_cent_and_bad_ones_are_said() -> None:
    assert lv.money("$1,200.5", "price") == "1200.50"
    with pytest.raises(lv.LevelValueError, match="is not an amount"):
        lv.money("ten", "initial payment")


def test_a_new_level_body_has_no_id_and_a_change_has_one() -> None:
    spec = lv.LevelSpec("Silver", initial_payment="5.00")
    body = lv.level_body(spec)
    assert "id" not in body and body["name"] == "Silver" and body["cycle_number"] == 0
    assert lv.level_body(spec, 7)["id"] == 7
    with pytest.raises(lv.LevelValueError, match="needs a name"):
        lv.level_body(lv.LevelSpec("  "))


def test_a_change_previews_only_what_changes_and_warns_about_prices() -> None:
    old = lv.level_from(_GOLD)
    assert old.billing_words() == "5.00 every month"
    new = lv.LevelSpec("Gold", "", "12.00", "5.00", 1, "Month", 0, 1, "Year", True)
    lines = lv.level_preview(new, SITE, old)
    assert lines[1:3] == [
        "Initial payment: 10.00 becomes 12.00.",
        "Expiry: never expires becomes expires after 1 year.",
    ]
    assert "PMPro does not change what members pay now" in lines[-1]


# -- in the Workbench ----------------------------------------------------------------


def _answers(monkeypatch: pytest.MonkeyPatch, texts: list[str], choices: list[int]) -> list[Any]:
    previews: list[Any] = []
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: texts.pop(0))
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: choices.pop(0))
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k) or True)
    return previews


def test_ctrl_n_on_membership_levels_makes_one() -> None:
    assert PLUGIN_NEW_HERE["membership_levels"] == "do_new_membership_level"


def test_a_new_level_is_previewed_sent_and_undone_by_deleting_it(bench, monkeypatch) -> None:
    previews = _answers(monkeypatch, ["Silver", "5", "2", "1", "0"], [2, 0])  # Month; allowed
    monkeypatch.setattr(
        bench.api,
        "post",
        lambda r, b=None, **p: (bench.api.writes.append(("POST", r, b)), {"id": 9})[1],
    )
    bench.provider.do_new_membership_level(_LEVELS, None)
    assert previews[-1]["lines"][3] == "Recurring payment: 2.00 every month."
    route, body = bench.api.writes[-1][1:]
    assert route == "pmpro/v1/membership_level" and body["initial_payment"] == "5.00"
    assert bench.said[-1] == f"Made the membership level Silver on {SITE}."
    bench.provider.history.entries[-1].undo()
    assert bench.api.writes[-1] == ("DELETE", "pmpro/v1/membership_level", {"id": 9})


def test_editing_a_level_sends_its_id_and_undo_sends_the_old_settings(bench, monkeypatch) -> None:
    row = WbRow("pmpro", SITE, "2", {"name": "Gold"}, "", subkind="level", raw=dict(_GOLD))
    _answers(monkeypatch, ["Gold", "12", "5", "1", "0"], [2, 0])
    bench.provider.do_edit_membership_level(_LEVELS, row)
    route, body = bench.api.writes[-1][1:]
    assert body["id"] == 2 and body["initial_payment"] == "12.00"
    bench.provider.history.entries[-1].undo()
    assert bench.api.writes[-1][2]["initial_payment"] == "10.00"


def test_nothing_changed_sends_nothing(bench, monkeypatch) -> None:
    row = WbRow("pmpro", SITE, "2", {"name": "Gold"}, "", subkind="level", raw=dict(_GOLD))
    _answers(monkeypatch, ["Gold", "10", "5", "1", "0"], [2, 0])
    bench.provider.do_edit_membership_level(_LEVELS, row)
    assert bench.api.writes == [] and bench.said[-1] == "Nothing about Gold would change."
