"""Export Podcasts to OPML... in Quill Radio (3.0.4).

Radio could import OPML and not export it; only Quill Cast had the way out.
The verb is a row action beside the import, and the handler writes the same
document Cast writes, from the same core exporter. Counts are always spoken.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.opml import parse_opml
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id, save_library
from quill.core.radio import row_actions
from quill.ui.radio import browse_actions, browse_podcast_actions


class _Chooser:
    def __init__(self, path: str | None) -> None:
        self._path = path

    def __enter__(self) -> _Chooser:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def ShowModal(self) -> int:  # noqa: N802
        return 5100 if self._path else 5101

    def GetPath(self) -> str:  # noqa: N802
        return self._path or ""


class _Wx:
    ID_OK = 5100
    FD_SAVE = 1
    FD_OVERWRITE_PROMPT = 2

    def __init__(self, path: str | None) -> None:
        self.path = path
        self.opened: list[dict[str, Any]] = []

    def FileDialog(self, _parent: Any, title: str, **kwargs: Any) -> _Chooser:  # noqa: N802
        self.opened.append({"title": title, **kwargs})
        return _Chooser(self.path)


class _Dialog:
    def __init__(self, path: str | None) -> None:
        self._wx = _Wx(path)
        self._win = object()
        self.said: list[str] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)


def _library_with(tmp_path: Path, *titles: str) -> None:
    library = PodcastLibrary()
    for title in titles:
        show = PodcastShow(
            id=new_id(), title=title, feed_url=f"https://feeds.example/{title.replace(' ', '')}"
        )
        library.shows.append(show)
    save_library(tmp_path, library)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from quill.core import paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    return tmp_path


def test_export_writes_the_library_and_speaks_the_count(data_dir: Path) -> None:
    _library_with(data_dir, "Morning Show", "Night Owls")
    target = data_dir / "out" / "mine.opml"
    target.parent.mkdir()
    dialog = _Dialog(str(target))

    browse_podcast_actions.export_opml(dialog)

    assert target.is_file()
    assert sorted(s.title for s in parse_opml(target.read_text(encoding="utf-8"))) == [
        "Morning Show",
        "Night Owls",
    ]
    assert dialog.said == ["Exported 2 podcasts to mine.opml."]
    assert dialog._wx.opened[0]["defaultFile"] == "quill-radio-podcasts.opml"


def test_one_show_is_singular(data_dir: Path) -> None:
    _library_with(data_dir, "Only One")
    target = data_dir / "one.opml"
    dialog = _Dialog(str(target))
    browse_podcast_actions.export_opml(dialog)
    assert dialog.said == ["Exported 1 podcast to one.opml."]


def test_an_empty_library_is_said_not_written(data_dir: Path) -> None:
    _library_with(data_dir)
    dialog = _Dialog(str(data_dir / "never.opml"))
    browse_podcast_actions.export_opml(dialog)
    assert dialog._wx.opened == []  # no file window for nothing
    assert not (data_dir / "never.opml").exists()
    assert dialog.said == ["No podcasts to export. Subscribe to a show first."]


def test_cancel_writes_nothing_and_says_nothing(data_dir: Path) -> None:
    _library_with(data_dir, "A Show")
    dialog = _Dialog(None)
    browse_podcast_actions.export_opml(dialog)
    assert dialog.said == []
    assert list(data_dir.glob("*.opml")) == []


def test_an_unwritable_path_is_reported(data_dir: Path) -> None:
    _library_with(data_dir, "A Show")
    dialog = _Dialog(str(data_dir / "missing-folder" / "x.opml"))
    browse_podcast_actions.export_opml(dialog)
    assert len(dialog.said) == 1 and dialog.said[0].startswith("Could not write that file.")


def test_the_verb_sits_beside_import_on_both_library_roots() -> None:
    def labels(kind: str, state: row_actions.FolderState) -> list[str]:
        return [a.label.replace("&", "") for a in row_actions.folder_actions(kind, state)]

    on_podcasts = labels("apple", row_actions.FolderState(root_source=True))
    assert "Export Podcasts to OPML..." in on_podcasts
    assert on_podcasts.index("Import Podcasts from OPML...") < on_podcasts.index(
        "Export Podcasts to OPML..."
    )
    assert "Export Podcasts to OPML..." in labels("mypodcasts", row_actions.FolderState())
    for kind, state in (
        ("apple", row_actions.FolderState(root_source=False)),
        ("mypodcastfolder", row_actions.FolderState()),
        ("mypodcastshow", row_actions.FolderState()),
    ):
        assert "Export Podcasts to OPML..." not in labels(kind, state), kind


def test_the_palette_row_dispatches_to_the_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[object] = []
    monkeypatch.setattr(browse_podcast_actions, "export_opml", lambda host: called.append(host))
    host = object()
    browse_actions.perform(host, "exportpodcastsopml")
    assert called == [host]
