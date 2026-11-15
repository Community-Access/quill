"""Nothing done on the Practice Site reaches a real site by accident.

Copy to Site and Make Them the Same each ask -- naming the practice site and
the real one, defaulting to No -- before practice work goes to a real site,
and stop when the answer is No. Between two real sites, or onto the practice
site, nothing extra is asked. And the practice site is labelled as practice in
the name every Workbench row, preview and status line is keyed by.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import sites as st  # noqa: E402
from quill.core.wordpress.workbench_practice import (  # noqa: E402
    crossing_warning,
    practice_label,
    site_url,
)
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402

PRACTICE = "Practice Site"
REAL = "Radio Club"
OTHER = "Second Real"


class _Commands:
    def __init__(self, store: st.SiteStore) -> None:
        self.store = store

    def sites(self) -> st.SiteStore:
        return self.store


@pytest.fixture
def provider(tmp_path) -> WordPressWorkbenchProvider:
    store = st.SiteStore([
        st.SiteProfile("p1", PRACTICE, site_url(), "admin"),
        st.SiteProfile("r1", REAL, "https://radio.example", "jeff"),
        st.SiteProfile("r2", OTHER, "https://second.example", "jeff"),
    ])
    made = WordPressWorkbenchProvider(_Commands(store), announce=lambda _s: None, data_dir=tmp_path)
    made.reload_profiles()
    return made


@pytest.fixture
def asked(monkeypatch) -> list[dict[str, Any]]:
    """Every confirmation, answered No (the dialog's own default)."""
    seen: list[dict[str, Any]] = []

    def confirm(_parent, _show, **kw) -> bool:
        seen.append(kw)
        return False

    monkeypatch.setattr(dlg, "confirm", confirm)
    return seen


@pytest.fixture
def started(provider, monkeypatch) -> list[str]:
    """What would have been sent: every background job's name."""
    jobs: list[str] = []
    monkeypatch.setattr(provider, "background", lambda name, *_a, **_k: jobs.append(name))
    monkeypatch.setattr(provider, "write_refusal", lambda *_a, **_k: "")
    return jobs


def test_the_warning_names_both_sites_and_only_when_crossing() -> None:
    said = crossing_warning("Copy to Site", [PRACTICE], [REAL])
    assert PRACTICE in said and REAL in said and "real site" in said
    assert crossing_warning("Copy to Site", [], [REAL]) == ""
    assert crossing_warning("Copy to Site", [PRACTICE], []) == ""


def test_the_practice_site_is_labelled_practice_wherever_it_is_named() -> None:
    assert practice_label("My Blog", site_url()) == "My Blog (practice)"
    assert practice_label("Practice Site", site_url()) == "Practice Site"
    assert practice_label("My Blog", "https://blog.example") == "My Blog"


def test_a_renamed_practice_site_still_says_practice_in_the_workbench(tmp_path) -> None:
    store = st.SiteStore([st.SiteProfile("p1", "Sandbox", site_url(), "admin")])
    made = WordPressWorkbenchProvider(_Commands(store), announce=lambda _s: None, data_dir=tmp_path)
    made.reload_profiles()
    assert list(made._profiles) == ["Sandbox (practice)"]
    assert made.is_practice("Sandbox (practice)")


def _row(site: str) -> WbRow:
    return WbRow("item", site, "7", {"title": "Hello"}, "", subkind="post")


def test_copy_from_practice_to_a_real_site_asks_and_no_sends_nothing(
    provider, asked, started, monkeypatch
) -> None:
    monkeypatch.setattr(provider, "_other_site", lambda _s, _t: REAL)
    provider.do_copy_to_site(None, _row(PRACTICE))
    assert len(asked) == 1
    assert PRACTICE in asked[0]["message"] and REAL in asked[0]["message"]
    assert REAL in asked[0]["yes_label"]
    assert started == [], "nothing was planned or sent after No"


def test_copy_goes_ahead_when_the_person_chooses_it(provider, started, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    monkeypatch.setattr(provider, "_other_site", lambda _s, _t: REAL)
    provider.do_copy_to_site(None, _row(PRACTICE))
    assert started == [f"planning the copy to {REAL}"]


@pytest.mark.parametrize(("source", "target"), [(REAL, OTHER), (REAL, PRACTICE)])
def test_copy_between_real_sites_or_onto_practice_asks_nothing_extra(
    provider, asked, started, monkeypatch, source, target
) -> None:
    monkeypatch.setattr(provider, "_other_site", lambda _s, _t: target)
    provider.do_copy_to_site(None, _row(source))
    assert asked == []
    assert started == [f"planning the copy to {target}"]


def _across(variants: dict[str, list[str]]) -> WbRow:
    return WbRow(
        "across", "", "News", {}, "", subkind="terms", raw={"variants": variants, "objects": {}}
    )


def test_make_them_the_same_from_practice_onto_real_sites_asks_first(
    provider, asked, monkeypatch
) -> None:
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)  # the practice version wins
    sent: list[str] = []
    monkeypatch.setattr(provider, "_across_refusal", lambda *_a: sent.append("went on") or "")
    provider.do_make_same(None, _across({"Practice news": [PRACTICE], "Club news": [REAL]}))
    assert len(asked) == 1
    assert PRACTICE in asked[0]["message"] and REAL in asked[0]["message"]
    assert sent == [], "No stopped it before any site was checked or changed"


def test_make_them_the_same_with_a_real_winner_asks_nothing_extra(
    provider, asked, monkeypatch
) -> None:
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)  # the real version wins
    went: list[str] = []
    monkeypatch.setattr(provider, "_across_refusal", lambda site, _k: went.append(site) or "")
    monkeypatch.setattr("quill.ui.wordpress_workbench_across.make_same_edits", lambda *_a: ([], []))
    provider.do_make_same(None, _across({"Club news": [REAL], "Practice news": [PRACTICE]}))
    assert asked == []
    assert went == [PRACTICE]


# -- Promote to Network, Revoke Everywhere, Install Missing, Put Back from a Snapshot --


def test_the_together_warning_names_both_and_only_when_mixed() -> None:
    from quill.core.wordpress.workbench_practice import together_warning

    said = together_warning("Promote to Network", [PRACTICE], [REAL, OTHER])
    assert PRACTICE in said and REAL in said and OTHER in said and "real sites" in said
    assert together_warning("Promote to Network", [], [REAL]) == ""
    assert together_warning("Promote to Network", [PRACTICE], []) == ""


@pytest.fixture
def inline(provider, monkeypatch) -> list[str]:
    """Background work run at once; previews recorded and declined."""
    previews: list[str] = []

    def run(_name: str, work: Any, done: Any, *_a: Any) -> None:
        done(work())

    monkeypatch.setattr(provider, "background", run)
    monkeypatch.setattr(provider, "write_refusal", lambda *_a, **_k: "")
    monkeypatch.setattr(provider, "account_for", lambda _s: None)
    monkeypatch.setattr(
        "quill.ui.wordpress_workbench_dialogs.ask_preview",
        lambda *_a, **k: previews.append(k["title"]) or False,
    )
    return previews


def _plugin_across(sites: list[str], subkind: str = "plugins") -> WbRow:
    objects = {s: {"plugin": "forms/forms", "user": "me"} for s in sites}
    return WbRow("across", "", "Forms", {}, "", subkind=subkind, raw={"objects": objects})


def test_promote_to_network_over_practice_and_real_asks_and_no_stops(
    provider, asked, inline, monkeypatch
) -> None:
    import quill.ui.wordpress_workbench_across as across

    monkeypatch.setattr(across, "network_status", lambda _api: "")
    monkeypatch.setattr(across, "network_refusal", lambda *_a: "")
    provider.do_promote_network(None, _plugin_across([PRACTICE, REAL]))
    assert len(asked) == 1 and "Together" in asked[0]["title"]
    assert PRACTICE in asked[0]["message"] and REAL in asked[0]["message"]
    assert inline == [], "No stopped it before the preview"
    provider.do_promote_network(None, _plugin_across([REAL, OTHER]))
    assert len(asked) == 1 and inline == ["Promote to Network"]  # real only: nothing extra


def test_revoke_everywhere_over_practice_and_real_asks_and_no_stops(
    provider, asked, inline, monkeypatch
) -> None:
    import quill.ui.wordpress_workbench_across as across

    monkeypatch.setattr(
        across, "revoke_plan", lambda _k, objects, _r: ([(s, f"r/{s}") for s in objects], [])
    )
    provider.do_revoke_everywhere(None, _plugin_across([PRACTICE, REAL], "app_passwords"))
    assert len(asked) == 1 and "Revoke Everywhere" in asked[0]["title"]
    assert inline == []


def test_install_missing_from_only_the_practice_site_asks_first(provider, asked, inline) -> None:
    row = _plugin_across([PRACTICE])
    row.raw["missing"] = [REAL]
    provider.do_install_missing(None, row)
    assert len(asked) == 1 and "Install on Sites Missing It" in asked[0]["title"]
    assert REAL in asked[0]["yes_label"]


def _snapshot(provider, site: str, taken_on: str, practice: bool) -> None:
    import json

    where = provider._snapshots(site) / "2026-11-14 100000"
    where.mkdir(parents=True)
    about = {"site": taken_on, "practice": practice}
    (where / "snapshot.json").write_text(json.dumps(about), encoding="utf-8")


def test_put_back_a_practice_snapshot_on_a_real_site_asks_first(
    provider, asked, started, monkeypatch
) -> None:
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    monkeypatch.setattr(provider, "_site_now", lambda _r: REAL)
    _snapshot(provider, REAL, PRACTICE, True)
    provider.do_restore_snapshot(None, None)
    assert len(asked) == 1 and "Put Back from a Snapshot" in asked[0]["title"]
    assert PRACTICE in asked[0]["message"] and REAL in asked[0]["message"]
    assert started == [], "No: nothing compared or put back"


def test_put_back_a_real_snapshot_asks_nothing_extra(provider, asked, started, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    monkeypatch.setattr(provider, "_site_now", lambda _r: REAL)
    _snapshot(provider, REAL, REAL, False)
    provider.do_restore_snapshot(None, None)
    assert asked == [] and started == ["comparing with the snapshot"]
