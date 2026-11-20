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


def test_save_level_posts_a_new_one_and_puts_a_change() -> None:
    sent: list[tuple[str, Any]] = []

    class _Api:
        def request(self, method: str, route: str, **kw: Any) -> Any:
            sent.append((method, kw["json_body"].get("id")))
            return type("R", (), {"payload": {"id": 4}})()

    lv.save_level(_Api(), lv.level_body(lv.LevelSpec("Silver")))
    lv.save_level(_Api(), lv.level_body(lv.LevelSpec("Silver"), 4))
    assert sent == [("POST", None), ("PUT", 4)]


def test_not_saved_names_what_the_site_left_out() -> None:
    body = lv.level_body(lv.LevelSpec("Gold", "", "10.00", "5.00", 1, "Month", 0, 2, "Year"), 2)
    # PMPro 3.9.2 as read back on the test site: no period, the expiry period cast to 0.
    stored = {"id": "2", "name": "Gold", "initial_payment": "10.00000000",
              "billing_amount": "5.00000000", "cycle_number": "1", "cycle_period": "",
              "billing_limit": "0", "expiration_number": "2", "expiration_period": "0",
              "allow_signups": "1"}  # fmt: skip
    assert lv.not_saved(body, stored) == ["Billing period", "Expiry period"]
    assert (
        lv.not_saved(body, {**stored, "cycle_period": "month", "expiration_period": "Year"}) == []
    )
    free = lv.level_body(lv.LevelSpec("Free"))  # no recurring payment, no expiry: no periods
    assert lv.not_saved(free, {"name": "Free", "initial_payment": 0, "billing_amount": 0,
                               "cycle_number": "0", "cycle_period": "", "billing_limit": "0",
                               "expiration_number": "0", "expiration_period": "",
                               "allow_signups": "1"}) == []  # fmt: skip


# -- in the Workbench ----------------------------------------------------------------


def _answers(monkeypatch: pytest.MonkeyPatch, texts: list[str], choices: list[int]) -> list[Any]:
    previews: list[Any] = []
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: texts.pop(0))
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: choices.pop(0))
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k) or True)
    return previews


def test_ctrl_n_on_membership_levels_makes_one() -> None:
    assert PLUGIN_NEW_HERE["membership_levels"] == "do_new_membership_level"


def _sends(bench: Any, monkeypatch: pytest.MonkeyPatch, answer: Any, stored: Any) -> None:
    """Level saves go through api.request (POST to make, PUT to change); reads get *stored*."""

    class _R:
        payload = answer

    def request(method: str, route: str, **kw: Any) -> Any:
        bench.api.writes.append((method, route, kw.get("json_body")))
        return _R()

    monkeypatch.setattr(bench.api, "request", request)
    real_get = bench.api.get
    monkeypatch.setattr(
        bench.api,
        "get",
        lambda r, **p: dict(stored) if r == lv.LEVEL_ROUTE else real_get(r, **p),
    )


def test_a_new_level_is_previewed_sent_and_undone_by_deleting_it(bench, monkeypatch) -> None:
    previews = _answers(monkeypatch, ["Silver", "5", "2", "1", "0"], [2, 0])  # Month; allowed
    stored = {"id": 9, "name": "Silver", "initial_payment": "5.00000000",
              "billing_amount": "2.00000000", "cycle_number": "1", "cycle_period": "Month",
              "billing_limit": "0", "expiration_number": "0", "allow_signups": "1"}  # fmt: skip
    _sends(bench, monkeypatch, {"id": 9}, stored)
    bench.provider.do_new_membership_level(_LEVELS, None)
    assert previews[-1]["lines"][3] == "Recurring payment: 2.00 every month."
    method, route, body = bench.api.writes[-1]
    assert (method, route) == ("POST", "pmpro/v1/membership_level")
    assert body["initial_payment"] == "5.00" and "id" not in body
    assert bench.said[-1] == f"Made the membership level Silver on {SITE}."
    bench.provider.history.entries[-1].undo()
    assert bench.api.writes[-1] == ("DELETE", "pmpro/v1/membership_level", {"id": 9})


def test_a_new_level_names_what_pmpro_did_not_keep(bench, monkeypatch) -> None:
    # Live (PMPro 3.9.2): the route reads cycle_period and never stores it.
    _answers(monkeypatch, ["Silver", "5", "2", "1", "0"], [2, 0])
    stored = {"id": 9, "name": "Silver", "initial_payment": "5.00000000",
              "billing_amount": "2.00000000", "cycle_number": "1", "cycle_period": "",
              "billing_limit": "0", "expiration_number": "0", "allow_signups": "1"}  # fmt: skip
    _sends(bench, monkeypatch, {"id": 9}, stored)
    bench.provider.do_new_membership_level(_LEVELS, None)
    assert bench.said[-1].startswith(f"Made the membership level Silver on {SITE}. {SITE} did")
    assert "did not keep: Billing period." in bench.said[-1]
    assert "Memberships > Settings > Levels" in bench.said[-1]


def test_undoing_a_new_level_says_where_to_delete_it_when_pmpro_refuses(bench, monkeypatch) -> None:
    from quill.core.wordpress.api import WordPressApiError

    # Live (PMPro 3.9.2): DELETE is off unless pmpro_rest_api_methods allows it; 403.
    _answers(monkeypatch, ["Silver", "0", "0", "0"], [0])
    _sends(bench, monkeypatch, {"id": 9}, {"id": 9, "name": "Silver", "allow_signups": "1"})

    def refuse(route: str, **params: Any) -> Any:
        raise WordPressApiError("Sorry, you are not allowed to do that.", status=403)

    monkeypatch.setattr(bench.api, "delete", refuse)
    bench.provider.do_new_membership_level(_LEVELS, None)
    said = bench.provider.history.entries[-1].undo()
    assert said == lv.delete_refused_words("Silver", SITE)
    assert "pmpro_rest_api_methods" in said and "Memberships > Settings > Levels" in said


def test_editing_a_level_puts_it_by_its_id_and_undo_puts_the_old_settings(
    bench, monkeypatch
) -> None:
    # Live (PMPro 3.9.2): a POST with an id made a second level; only PUT changes one.
    row = WbRow("pmpro", SITE, "2", {"name": "Gold"}, "", subkind="level", raw=dict(_GOLD))
    _answers(monkeypatch, ["Gold", "12", "5", "1", "0"], [2, 0])
    _sends(bench, monkeypatch, {"id": 2}, {**_GOLD, "initial_payment": "12.00"})
    bench.provider.do_edit_membership_level(_LEVELS, row)
    method, route, body = bench.api.writes[-1]
    assert (method, route) == ("PUT", "pmpro/v1/membership_level")
    assert body["id"] == 2 and body["initial_payment"] == "12.00"
    assert bench.said[-1] == f"Saved the membership level Gold on {SITE}."
    bench.provider.history.entries[-1].undo()
    assert (
        bench.api.writes[-1][0] == "PUT" and bench.api.writes[-1][2]["initial_payment"] == "10.00"
    )


def test_nothing_changed_sends_nothing(bench, monkeypatch) -> None:
    row = WbRow("pmpro", SITE, "2", {"name": "Gold"}, "", subkind="level", raw=dict(_GOLD))
    _answers(monkeypatch, ["Gold", "10", "5", "1", "0"], [2, 0])
    bench.provider.do_edit_membership_level(_LEVELS, row)
    assert bench.api.writes == [] and bench.said[-1] == "Nothing about Gold would change."
