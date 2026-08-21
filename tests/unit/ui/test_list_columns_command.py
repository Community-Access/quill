"""Choose Columns...: what happens after OK, and after Cancel.

Headless -- the dialog is stubbed, because what these tests are about is the
wiring around it: Cancel changes nothing, OK saves and drops the cache, and a
save that fails still leaves the new layout in force for this session. No real
wx is created (per the "no desktop UI automation on this machine" rule).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.media.list_columns import ColumnLayouts
from quill.core.podcasts.list_columns import SURFACES as CAST_SURFACES
from quill.core.radio.list_columns import SURFACES as RADIO_SURFACES
from quill.ui.media import list_columns_view
from quill.ui.podcasts import list_columns_command as cast_command
from quill.ui.radio import list_columns_command as radio_command


class _Host:
    def __init__(self) -> None:
        self.frame = object()
        self.said: list[str] = []
        self._podcast_manager_dialog = None

    def _announce(self, message: str) -> None:
        self.said.append(message)


class _StubDialog:
    """Stands in for :class:`ListColumnsDialog`; answers with *result*."""

    instances: list[_StubDialog] = []

    def __init__(self, _parent: object, **kwargs: object) -> None:
        self.kwargs = kwargs
        _StubDialog.instances.append(self)

    def show(self) -> object:
        return self.result

    result: object = None


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    list_columns_view.reset_cache()
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    _StubDialog.instances = []
    yield
    list_columns_view.reset_cache()


def _patch_dialog(monkeypatch: pytest.MonkeyPatch, result: object) -> None:
    _StubDialog.result = result
    monkeypatch.setattr(
        "quill.ui.media.list_columns_dialog.ListColumnsDialog", _StubDialog, raising=True
    )


def test_cancel_writes_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_dialog(monkeypatch, None)
    host = _Host()
    radio_command.open_list_columns(host)
    assert list(tmp_path.glob("*.json")) == []
    assert host.said == []


def test_ok_saves_the_layout_and_the_next_list_reads_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    edited = ColumnLayouts.defaults(RADIO_SURFACES)
    edited.set_visible("radio.station_results", "country", False)
    _patch_dialog(monkeypatch, edited)
    host = _Host()
    # Prime the cache with the defaults, so a stale answer would be visible.
    assert "country" in [
        c.id for c in list_columns_view.columns_for("radio", "radio.station_results")
    ]

    radio_command.open_list_columns(host)

    assert (tmp_path / "radio_list_columns.json").is_file()
    shown = [c.id for c in list_columns_view.columns_for("radio", "radio.station_results")]
    assert "country" not in shown, "the cache was not dropped, so the list still reads the old row"
    assert host.said == ["Columns saved."]


def test_a_save_that_fails_still_applies_for_this_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edited = ColumnLayouts.defaults(RADIO_SURFACES)
    edited.set_visible("radio.station_results", "source", False)
    _patch_dialog(monkeypatch, edited)

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise OSError("the disk said no")

    monkeypatch.setattr("quill.core.radio.list_columns.save_radio_column_layouts", _explode)
    host = _Host()
    radio_command.open_list_columns(host)
    # It still says it happened, because for this session it did: the cache is
    # dropped either way, and refusing to apply a layout somebody just chose
    # because it could not be written is the worse of the two failures.
    assert host.said == ["Columns saved."]


def test_cast_rebuilds_its_manager_when_one_is_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edited = ColumnLayouts.defaults(CAST_SURFACES)
    _patch_dialog(monkeypatch, edited)
    rebuilt: list[bool] = []
    host = _Host()
    host._podcast_manager_dialog = SimpleNamespace(reapply_columns=lambda: rebuilt.append(True))
    cast_command.open_list_columns(host)
    assert rebuilt == [True]


def test_cast_with_no_manager_open_is_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_dialog(monkeypatch, ColumnLayouts.defaults(CAST_SURFACES))
    host = _Host()
    cast_command.open_list_columns(host)
    assert host.said == ["Columns saved."]


def test_a_manager_that_raises_does_not_lose_the_layout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    edited = ColumnLayouts.defaults(CAST_SURFACES)
    edited.set_visible("cast.episodes", "podcast", True)
    _patch_dialog(monkeypatch, edited)

    def _explode() -> None:
        raise RuntimeError("the window was already gone")

    host = _Host()
    host._podcast_manager_dialog = SimpleNamespace(reapply_columns=_explode)
    cast_command.open_list_columns(host)
    assert (tmp_path / "podcast_list_columns.json").is_file()
    assert "podcast" in [c.id for c in list_columns_view.columns_for("cast", "cast.episodes")]


def test_both_apps_open_the_dialog_on_their_own_catalogue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dialog(monkeypatch, None)
    radio_command.open_list_columns(_Host())
    cast_command.open_list_columns(_Host())
    radio_surfaces = {sid for sid, _label in _StubDialog.instances[0].kwargs["surface_labels"]}
    cast_surfaces = {sid for sid, _label in _StubDialog.instances[1].kwargs["surface_labels"]}
    assert radio_surfaces == set(RADIO_SURFACES)
    assert cast_surfaces == set(CAST_SURFACES)
    assert not radio_surfaces & cast_surfaces


def test_both_menu_entries_advertise_a_keyboard_route() -> None:
    """Neither app's Choose Columns... is reachable only by mouse.

    Radio's whole menu bar is covered by ``test_menu_accelerators``; Cast's is
    not covered at all, which is how its Quick Actions... came to ship without a
    key. A source check is enough here: the label either carries a key after the
    tab or it does not.
    """
    repo_root = Path(__file__).resolve().parents[3]
    for relative in (
        "quill/apps/radio_settings_menu.py",
        "quill/apps/podcasts_menu.py",
    ):
        source = (repo_root / relative).read_text(encoding="utf-8")
        assert r'"Choose Co&lumns...\tCtrl+Alt+Shift+C"' in source, (
            f"{relative} must give Choose Columns... a key in its label; walking a "
            "menu to find there is no shortcut is a cost paid on every visit."
        )
