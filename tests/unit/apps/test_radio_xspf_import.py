"""Station > Import Stations from Playlist, driven end to end with an XSPF (#1691).

The handler is called for real; only the two modals it opens (the file dialog
and the folder prompt) and persistence are stood in for. The playlist is the
Victor Stream export fixture, which before #1691 imported nothing.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.apps.radio import RadioAppFrame
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.radio import import_stations_dialog

_FIXTURE = (
    Path(__file__).parents[1]
    / "core"
    / "radio"
    / "fixtures"
    / "victor_stream_reading_services.xspf"
)


class _FileDialog:
    def __init__(self, path: Path) -> None:
        self._path = path

    def __enter__(self) -> _FileDialog:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def ShowModal(self) -> int:  # noqa: N802 - wx API
        return 5100

    def GetPath(self) -> str:  # noqa: N802 - wx API
        return str(self._path)


class _ChoiceDialog(_FileDialog):
    def __init__(self, selection: int) -> None:
        self._selection = selection

    def GetSelection(self) -> int:  # noqa: N802 - wx API
        return self._selection


def _frame(tmp_path: Path, store: RadioFavoritesStore, *, duplicate_choice: int = 0):
    source = tmp_path / "Radio Reading Services.xspf.txt"
    shutil.copyfile(_FIXTURE, source)
    spoken: list[str] = []
    saves: list[int] = []
    frame = RadioAppFrame.__new__(RadioAppFrame)
    frame.frame = None
    frame._radio_favorites = store
    frame._wx = SimpleNamespace(
        FileDialog=lambda *_a, **_k: _FileDialog(source),
        SingleChoiceDialog=lambda *_a, **_k: _ChoiceDialog(duplicate_choice),
        ID_OK=5100,
        FD_OPEN=1,
        FD_FILE_MUST_EXIST=2,
        OK=4,
        ICON_INFORMATION=8,
    )
    frame._announce = lambda text, *_a, **_k: spoken.append(text)
    frame._save_radio_favorites = lambda: saves.append(1)
    frame._reload_favorites_tree = lambda *_a, **_k: None
    frame._show_message_box = lambda *_a, **_k: pytest.fail("no message box expected")
    return frame, spoken, saves


def test_xspf_import_adds_every_playable_track_and_says_how_many(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        import_stations_dialog, "prompt_import_target", lambda *_a, **_k: "Reading Services"
    )
    store = RadioFavoritesStore()
    frame, spoken, saves = _frame(tmp_path, store)

    frame.import_stations_from_playlist()

    assert len(store.favorites) == 5
    assert {f.folder for f in store.favorites} == {"Reading Services"}
    assert saves == [1]
    assert spoken == ['Imported 5 stations into the "Reading Services" folder.']


def test_xspf_import_skips_duplicates_the_same_way_as_other_formats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(import_stations_dialog, "prompt_import_target", lambda *_a, **_k: "")
    store = RadioFavoritesStore()
    store.add(RadioStation(name="KPBS", stream_url="https://kpbs-rrs.streamguys1.com/kpbs-rrs"))
    frame, spoken, _saves = _frame(tmp_path, store, duplicate_choice=0)

    frame.import_stations_from_playlist()

    assert len(store.favorites) == 5  # the one already there, plus four new
    assert spoken == ["Imported 4 stations into your favorites."]
