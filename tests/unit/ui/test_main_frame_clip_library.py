"""Tests for ClipLibraryMixin (#895): the Keep/Open commands wired onto
MainFrame."""

from __future__ import annotations

from pathlib import Path

from quill.core.clip_library import ClipLibrary
from quill.core.fragment import Fragment
from quill.ui.main_frame_clip_library import ClipLibraryMixin


class _Host(ClipLibraryMixin):
    def __init__(self, tmp_path: Path, selection: tuple[int, int], text: str) -> None:
        self._selection = selection
        self._text = text
        self.announced: list[str] = []
        self.status: list[str] = []
        self._tmp_path = tmp_path

    # -- the bits ClipLibraryMixin relies on --
    class _Editor:
        def __init__(self, outer: _Host) -> None:
            self._outer = outer

        def GetSelection(self):
            return self._outer._selection

        def GetValue(self):
            return self._outer._text

    @property
    def editor(self):
        return self._Editor(self)

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)


def test_keep_selection_requires_a_real_selection(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path, selection=(5, 5), text="hello world")
    host.keep_selection_in_clip_library()
    assert host.announced == ["Select text first to keep it in the Clip Library"]
    assert len(host._clip_library()) == 0


def test_keep_selection_remembers_the_selected_text(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path, selection=(0, 5), text="hello world")
    host.keep_selection_in_clip_library()
    assert host.status == ["Kept in the Clip Library."]
    lib = host._clip_library()
    assert len(lib) == 1
    assert lib.entry(0).fragment.markup == "hello"


def test_keep_selection_reports_duplicate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path, selection=(0, 5), text="hello world")
    host.keep_selection_in_clip_library()
    host.keep_selection_in_clip_library()
    assert host.status[-1] == "Already in the Clip Library."
    assert len(host._clip_library()) == 1


def test_keep_fragment_in_clip_library_reports_title(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path, selection=(0, 0), text="")
    frag = Fragment(markup="Ada Lovelace was a mathematician.", title="Ada Lovelace")
    host.keep_fragment_in_clip_library(frag)
    assert host.status == ["Kept Ada Lovelace in the Clip Library."]


def test_clip_library_instance_is_lazy_and_cached(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path, selection=(0, 0), text="")
    first = host._clip_library()
    second = host._clip_library()
    assert first is second
    assert isinstance(first, ClipLibrary)
