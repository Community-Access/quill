"""Tools > Practice Site, Set Up the Lesson Material: a preview, the files, Change History, undo.

And the two QUILL tutorial checks that watch the Workbench for the Practice
Site lessons: a change made there, and the lesson material being in place.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import sites as st  # noqa: E402
from quill.core.wordpress import workbench_practice_material as material  # noqa: E402
from quill.core.wordpress.workbench_practice import practice_dir, site_url  # noqa: E402
from quill.core.workbench.history import Change  # noqa: E402
from quill.ui import quill_tutorials  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_bold_practice as practice  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402


class _Commands:
    def __init__(self, store: st.SiteStore) -> None:
        self.store = store

    def sites(self) -> st.SiteStore:
        return self.store


class _Running:
    """A Practice Site server that is still going."""

    def poll(self) -> None:
        return None


@pytest.fixture
def provider(tmp_path: Path, monkeypatch) -> WordPressWorkbenchProvider:
    store = st.SiteStore([st.SiteProfile("p1", "Practice Site", site_url(), "admin")])
    said: list[str] = []
    made = WordPressWorkbenchProvider(_Commands(store), announce=said.append, data_dir=tmp_path)
    made.reload_profiles()
    made.said = said  # type: ignore[attr-defined]
    made._practice = _Running()
    monkeypatch.setattr(made, "background", lambda _name, work, done: done(work()))
    monkeypatch.setattr(made, "say", said.append)
    return made


@pytest.fixture
def started_once(provider) -> Path:
    folder = practice_dir(provider._base())
    (folder / "wordpress").mkdir(parents=True)
    (folder / "wordpress" / "wp-load.php").write_bytes(b"<?php\n")
    return folder


def _answer(monkeypatch, pick: str, *, confirm: bool) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def ask_choice(_parent, _show, **kw) -> int | None:
        seen["rows"] = kw["rows"]
        return kw["rows"].index(pick) if pick in kw["rows"] else None

    def ask_confirm(_parent, _show, **kw) -> bool:
        seen["confirm"] = kw
        return confirm

    monkeypatch.setattr(dlg, "ask_choice", ask_choice)
    monkeypatch.setattr(dlg, "confirm", ask_confirm)
    return seen


def test_the_row_appears_only_once_the_site_has_a_wordpress(provider, monkeypatch) -> None:
    seen = _answer(monkeypatch, "nothing", confirm=False)
    provider.do_practice(None, None)
    assert practice.SET_UP not in seen["rows"]


def test_cancel_at_the_preview_writes_nothing(provider, started_once, monkeypatch) -> None:
    seen = _answer(monkeypatch, practice.SET_UP, confirm=False)
    provider.do_practice(None, None)
    assert seen["confirm"]["message"] == material.PREVIEW
    assert seen["confirm"]["yes_label"] == "Set Up"
    assert not material.is_set_up(started_once)
    assert provider.history.recorded == 0


def test_set_up_writes_records_and_undoes(provider, started_once, monkeypatch) -> None:
    _answer(monkeypatch, practice.SET_UP, confirm=True)
    provider.do_practice(None, None)
    assert material.is_set_up(started_once)
    assert (started_once / "wordpress" / material.MATERIAL_PLUGIN).is_file()
    assert any("lesson material is on the Practice Site" in s for s in provider.said)
    (change,) = provider.history.entries
    assert "Set up the lesson material" in change.summary and change.undo is not None
    said = provider.history.undo()
    assert "going" in said
    assert not material.is_set_up(started_once)
    php = (started_once / "wordpress" / material.MATERIAL_PLUGIN).read_text(encoding="utf-8")
    assert "'clear'" in php


def test_once_set_up_the_row_offers_take_away(provider, started_once, monkeypatch) -> None:
    material.set_up(started_once)
    seen = _answer(monkeypatch, practice.TAKE_AWAY, confirm=True)
    provider.do_practice(None, None)
    assert practice.SET_UP not in seen["rows"]
    assert seen["confirm"]["message"] == material.TAKE_AWAY_PREVIEW
    assert not material.is_set_up(started_once)


def test_the_tutorial_checks_watch_the_open_workbench(provider, started_once, monkeypatch) -> None:
    from quill.ui import wordpress_workbench_window as window

    class _Frame:
        def __init__(self, provider: Any) -> None:
            self.provider = provider

    monkeypatch.setattr(provider, "current_site", lambda: "Practice Site")
    probe = quill_tutorials.PROBE
    host = object()
    assert probe.answer("lesson-material-ready", host, {}) == (
        False,
        "the lesson material is on the Practice Site",
    )
    monkeypatch.setitem(window._OPEN, "wordpress", _Frame(provider))
    baseline = probe.snapshot(host)
    assert probe.answer("practice-site-changed", host, baseline)[0] is False
    provider.history.record(Change("Practice Site", "Changed a title on Practice Site."))
    assert probe.answer("practice-site-changed", host, baseline)[0] is True
    assert probe.answer("lesson-material-ready", host, baseline)[0] is False
    material.set_up(started_once)
    assert probe.answer("lesson-material-ready", host, baseline)[0] is True


def test_a_change_on_a_real_site_does_not_count(provider, monkeypatch) -> None:
    from quill.ui import wordpress_workbench_window as window

    class _Frame:
        def __init__(self, provider: Any) -> None:
            self.provider = provider

    monkeypatch.setattr(provider, "current_site", lambda: "Radio Club")
    monkeypatch.setitem(window._OPEN, "wordpress", _Frame(provider))
    probe = quill_tutorials.PROBE
    baseline = probe.snapshot(object())
    provider.history.record(Change("Radio Club", "Changed a title on Radio Club."))
    assert probe.answer("practice-site-changed", object(), baseline)[0] is False
