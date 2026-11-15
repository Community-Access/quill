"""Ability row > Offer to Ask the Site: the opt-in Ask the Site reads, from the Workbench."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import abilities as ab  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
)


@pytest.fixture
def provider(wx_session_app, tmp_path):
    said: list[str] = []
    commands = _Commands(said)
    commands.ability_choices = lambda profile: ab.AbilityChoices(tmp_path, profile.id)
    made = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: FakeApi()
    )
    made.said = said  # type: ignore[attr-defined]
    made.say = said.append  # type: ignore[method-assign]
    return made


def _row(readonly: bool) -> WbRow:
    return WbRow(
        "ability",
        SITE,
        "acme/count",
        {"ability": "Count Things"},
        "Count Things",
        raw={"name": "acme/count", "readonly": readonly},
    )


def _on(provider: Any) -> set[str]:
    return provider.commands.ability_choices(provider.profile(SITE)).on()


def test_a_read_only_ability_is_offered_and_withdrawn_without_asking(provider, monkeypatch):
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: pytest.fail("no question for a read"))
    provider.do_offer_to_ask(None, _row(readonly=True))
    assert _on(provider) == {"acme/count"}
    assert "may now offer Count Things" in provider.said[-1]
    provider.do_offer_to_ask(None, _row(readonly=True))
    assert _on(provider) == set()
    assert "no longer offers Count Things" in provider.said[-1]


def test_an_ability_that_changes_the_site_asks_first_and_cancel_keeps_it_off(provider, monkeypatch):
    asked: list[dict[str, Any]] = []
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: (asked.append(k), False)[1])
    provider.do_offer_to_ask(None, _row(readonly=False))
    assert asked and "It can change the site" in asked[0]["message"]
    assert _on(provider) == set()
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: True)
    provider.do_offer_to_ask(None, _row(readonly=False))
    assert _on(provider) == {"acme/count"}


def test_another_row_is_refused(provider):
    provider.do_offer_to_ask(None, WbRow("route", SITE, "x", {}, "x", raw={}))
    assert "works on one of the site's abilities" in provider.said[-1]
