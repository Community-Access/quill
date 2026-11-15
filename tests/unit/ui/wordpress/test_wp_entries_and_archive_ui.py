"""Copy Old Entries into QAF and Archive a Static Copy, through the real Workbench frame.

Copy Old Entries runs on the Gravity Forms bench of ``test_wp_gravity_build_ui``
(a site with ``gf/v2`` and ``qaf/v1``); Archive a Static Copy on the WXR bench
of ``test_wp_workbench_wxr``. Background work runs inline; the dialogs are
answered by patching the helpers the commands call.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import media_tools as mt  # noqa: E402
from quill.core.wordpress.gravity_qaf import to_qaf  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command  # noqa: E402
from quill.core.wordpress.workbench_gravity_actions import KEYLESS as GRAVITY_KEYLESS  # noqa: E402
from quill.core.wordpress.workbench_site_files_actions import KEYLESS, WXR_SUB  # noqa: E402
from quill.core.wordpress.workbench_tiers import tier_of  # noqa: E402
from quill.core.workbench.actions import Tier  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from tests.unit.ui.wordpress import test_wp_gravity_build_ui as gbui  # noqa: E402
from tests.unit.ui.wordpress import test_wp_workbench_wxr as wxui  # noqa: E402

answers = gbui.answers
gravity_bench = gbui.bench
wxr_bench = wxui.bench

ENTRY = {"id": "41", "form_id": "1", "date_created": "2024-05-01 10:00:00", "1": "Ann", "2": "am"}


def _target() -> dict[str, Any]:
    model = to_qaf(gbui.FORM).form
    return {"id": 8, "title": "Signup", "status": "draft", "entry_count": 0, "model": model}


def _fake_entries(api: Any, *, route_missing: bool = False) -> list[tuple[str, str, Any]]:
    sent: list[tuple[str, str, Any]] = []
    get = api.get

    def get_more(route: str, **params: Any) -> Any:
        if route == "gf/v2/entries":
            return {"total_count": "1", "entries": [dict(ENTRY)]}
        if route == "qaf/v1/forms/8":
            return _target()
        return get(route, **params)

    def collection(route: str, *_a: Any, **_k: Any):
        if route == "qaf/v1/forms":
            yield _target()

    def post(route: str, body: Any = None, **_k: Any) -> Any:
        sent.append(("POST", route, copy.deepcopy(body)))
        if route_missing:
            from quill.core.wordpress.api import WordPressApiError

            raise WordPressApiError("No route was found.", status=404, wp_code="rest_no_route")
        return {"id": 300}

    def delete(route: str, **params: Any) -> Any:
        sent.append(("DELETE", route, params))
        return {}

    api.get, api.iter_collection, api.post, api.delete = get_more, collection, post, delete
    return sent


def test_copy_old_entries_previews_sends_each_and_undoes(gravity_bench, answers, monkeypatch):
    sent = _fake_entries(gravity_bench.api)
    chosen: list[dict[str, Any]] = []
    reports: list[str] = []
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **k: chosen.append(k) or 0)
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **k: reports.append(k["text"]))
    provider = gravity_bench.provider
    provider.do_copy_entries_to_qaf(None, gbui._row(gravity_bench, "gravity_form"))
    assert chosen[0]["rows"] == ["Signup, 0 responses, draft"]
    preview = answers["previews"][-1]
    assert preview["yes"] == "Copy Entries" and "Copy 1 entries from Signup" in preview["summary"]
    assert any("POST qaf/v1/entries" in line for line in preview["lines"])
    assert any("Songs: a list field" in line for line in preview["lines"])
    (post,) = [s for s in sent if s[0] == "POST"]
    assert post[1] == "qaf/v1/entries"
    assert post[2]["fields"] == {"field_1": "Ann", "field_2": "am"} and post[2]["form_id"] == 8
    assert gravity_bench.said[-1] == f"Copied 1 of 1 entries into Signup on {gbui.SITE}."
    assert "Done. " in reports[-1] and "copied as entry 300" in reports[-1]
    assert "1 copied entries" in provider.history.undo()
    assert sent[-1][:2] == ("DELETE", "qaf/v1/entries/300")


def test_a_qaf_without_the_create_route_says_so_once(gravity_bench, answers, monkeypatch):
    _fake_entries(gravity_bench.api, route_missing=True)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **_k: None)
    gravity_bench.provider.do_copy_entries_to_qaf(None, gbui._row(gravity_bench, "gravity_form"))
    assert "cannot take entries yet" in gravity_bench.said[-1]


def test_a_cancelled_preview_or_choice_sends_nothing(gravity_bench, answers, monkeypatch):
    sent = _fake_entries(gravity_bench.api)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: None)
    gravity_bench.provider.do_copy_entries_to_qaf(None, gbui._row(gravity_bench, "gravity_form"))
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    answers["replies"]["preview"].append(False)
    gravity_bench.provider.do_copy_entries_to_qaf(None, gbui._row(gravity_bench, "gravity_form"))
    assert sent == []


def test_copy_old_entries_is_on_the_gravity_form_row_with_a_reason_for_no_chord() -> None:
    verb = command("copy_entries_to_qaf")
    rows = {a.command_id: a for a in WORDPRESS_ACTIONS.rows_for("gravity_form")}
    assert rows[verb].tier is Tier.WRITE and "qaf/v1/entries" in rows[verb].help
    assert GRAVITY_KEYLESS[verb]


def test_archive_a_static_copy_writes_the_folder(wxr_bench, monkeypatch, tmp_path: Path):
    out = tmp_path / "archive"
    out.mkdir()
    monkeypatch.setattr(wxr_bench.provider, "site_of", lambda _ref: wxui.SITE)
    monkeypatch.setattr(wxr_bench.provider, "_folder", lambda _title: out)
    reports = wxui._reports(monkeypatch)

    class Got:
        content = b"png"

    monkeypatch.setattr(mt, "download_file", lambda *_a, **_k: Got())
    wxr_bench.provider.do_archive_static(None, None)
    assert (out / "index.html").exists()
    assert list((out / "posts").glob("*.html"))
    assert wxr_bench.said[-1].startswith("Archived ") and "index.html" in wxr_bench.said[-1]
    assert reports and reports[-1].startswith("Archived ")
    assert wxr_bench.api.writes == []


def test_archive_goes_in_a_new_subfolder_when_the_chosen_one_is_not_empty(
    wxr_bench, monkeypatch, tmp_path: Path
):
    (tmp_path / "keep.txt").write_bytes(b"x")
    monkeypatch.setattr(wxr_bench.provider, "site_of", lambda _ref: wxui.SITE)
    monkeypatch.setattr(wxr_bench.provider, "_folder", lambda _title: tmp_path)
    wxui._reports(monkeypatch)
    wxr_bench.provider.do_archive_static(None, None)
    made = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(made) == 1 and made[0].name.endswith("-archive")
    assert (made[0] / "index.html").exists()


def test_archive_is_in_wxr_files_read_only_with_a_reason() -> None:
    verb = command("archive_static")
    assert verb in {row.command_id for row in WXR_SUB.rows if row is not None}
    assert KEYLESS[verb] and tier_of(verb, WORDPRESS_ACTIONS) is Tier.READ
