"""#245 (BR-022): Translation submenu gating and command behavior."""

from __future__ import annotations

from pathlib import Path

import quill.core.braille_pack as pack
import quill.core.braille_worker_client as worker
import quill.ui.main_frame_braille as main_frame_braille_module
import quill.ui.main_frame_speech as main_frame_speech_module
from quill.ui.main_frame import MainFrame


class _FakeWx:
    ICON_ERROR = 1
    OK = 2


def _frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._safe_mode = False
    frame._wx = _FakeWx()  # type: ignore[attr-defined]
    frame._announced = []  # type: ignore[attr-defined]
    frame._status = []  # type: ignore[attr-defined]
    frame._message_boxes = []  # type: ignore[attr-defined]
    frame._announce = lambda m: frame._announced.append(m)  # type: ignore[attr-defined]
    frame._set_status = lambda m: frame._status.append(m)  # type: ignore[attr-defined]
    frame._show_message_box = (  # type: ignore[attr-defined]
        lambda message, title, style=0: frame._message_boxes.append((message, title))
    )
    return frame


class _Editor:
    def __init__(self, text: str = "hello", selection: str = "") -> None:
        self._text = text
        self._selection = selection

    def GetValue(self) -> str:
        return self._text

    def GetStringSelection(self) -> str:
        return self._selection


def test_translation_items_hidden_when_pack_absent(monkeypatch) -> None:
    monkeypatch.setattr(pack, "is_braille_pack_installed", lambda: False)
    assert _frame()._braille_translation_items() == []


def test_translation_items_shown_when_pack_present(monkeypatch) -> None:
    monkeypatch.setattr(pack, "is_braille_pack_installed", lambda: True)
    items = _frame()._braille_translation_items()
    assert [command_id for _label, command_id in items] == [
        "braille.translate_ueb_g2",
        "braille.translate_ueb_g1",
        "braille.translate_selection",
        "braille.back_translate",
        "braille.translate_standard_g2",
        "braille.translate_standard_g1",
    ]


def test_translation_items_hidden_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setattr(pack, "is_braille_pack_installed", lambda: True)
    frame = _frame()
    frame._safe_mode = True
    assert frame._braille_translation_items() == []


def test_translate_opens_document_and_announces(monkeypatch) -> None:
    monkeypatch.setattr(worker, "forward_translate", lambda *_a, **_k: ",hello _w\x0c")
    frame = _frame()
    frame.editor = _Editor("hello world")  # type: ignore[attr-defined]
    opened: list[str] = []
    frame._create_document_tab = lambda doc, select=True: opened.append(doc.text)  # type: ignore[attr-defined]

    frame.translate_to_ueb_g2()

    assert opened == [",hello _w\x0c"]
    assert "Translated to UEB G2" in frame._announced[-1]


def test_back_translate_labels_draft(monkeypatch) -> None:
    monkeypatch.setattr(worker, "back_translate", lambda *_a, **_k: "hello world")
    frame = _frame()
    frame.editor = _Editor(",hello _w")  # type: ignore[attr-defined]
    frame._create_document_tab = lambda doc, select=True: None  # type: ignore[attr-defined]

    frame.back_translate_ueb()

    assert "draft" in frame._announced[-1].lower()


def test_translation_failure_is_announced(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise worker.WorkerError("liblouis is not installed")

    monkeypatch.setattr(worker, "forward_translate", _boom)
    frame = _frame()
    frame.editor = _Editor("hello")  # type: ignore[attr-defined]
    opened: list[str] = []
    frame._create_document_tab = lambda doc, select=True: opened.append(doc.text)  # type: ignore[attr-defined]

    frame.translate_to_ueb_g2()

    assert opened == []  # no empty document on failure
    assert "Translation failed" in frame._announced[-1]


def test_translation_failure_also_shows_a_visible_dialog(monkeypatch) -> None:
    """A live report described back-translation as appearing to "do nothing"
    on a large BRF file (whose real failure -- a command-line-length limit,
    fixed separately -- raised and was only ever spoken via _say/_announce).
    A spoken-only failure is easy to miss entirely; a failure this specific
    (which table, which file) deserves a real, readable dialog too, not just
    an announcement that can go right past a user who wasn't listening for
    it at that exact moment."""

    def _boom(*_a, **_k):
        raise worker.WorkerError("liblouis is not installed")

    monkeypatch.setattr(worker, "back_translate", _boom)
    frame = _frame()
    frame.editor = _Editor(",hello _w")  # type: ignore[attr-defined]
    frame._create_document_tab = lambda doc, select=True: None  # type: ignore[attr-defined]

    frame.back_translate_ueb()

    assert len(frame._message_boxes) == 1
    message, title = frame._message_boxes[0]
    assert "liblouis is not installed" in message
    assert "Braille" in title


def test_back_translate_uses_selection_when_present(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _fake_back(text, table=worker.DEFAULT_TABLE, **_k):
        captured["text"] = text
        return "recovered passage"

    monkeypatch.setattr(worker, "back_translate", _fake_back)
    frame = _frame()
    frame.editor = _Editor(",whole _docu;t", selection=",sel")  # type: ignore[attr-defined]
    frame._create_document_tab = lambda doc, select=True: None  # type: ignore[attr-defined]

    frame.back_translate_ueb()

    assert captured["text"] == ",sel"  # back-translated the selection, not the whole doc
    assert "selection" in frame._announced[-1].lower()


def test_back_translate_uses_document_when_no_selection(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _fake_back(text, table=worker.DEFAULT_TABLE, **_k):
        captured["text"] = text
        return "whole document"

    monkeypatch.setattr(worker, "back_translate", _fake_back)
    frame = _frame()
    frame.editor = _Editor(",whole _docu;t", selection="")  # type: ignore[attr-defined]
    frame._create_document_tab = lambda doc, select=True: None  # type: ignore[attr-defined]

    frame.back_translate_ueb()

    assert captured["text"] == ",whole _docu;t"
    assert "document" in frame._announced[-1].lower()


def test_download_braille_pack_rebuilds_menu_on_success() -> None:
    """A downloaded braille pack was not lighting up the Translation submenu.

    Same root cause as #974 (Quillin menu contributions): the Translation
    submenu is only added to Tools > Braille when
    ``_is_braille_pack_available()`` is True at ``_build_menu()`` time -- it
    is a structural AppendSubMenu, not a menu-item enabled/disabled state.
    ``download_braille_pack``'s success callback called
    ``self._request_menu_refresh()``, but that only refreshes existing menu
    item *state* (recent files, sessions, contextual items, announcement
    backend, watch folder, AI menu) -- it never calls ``_build_menu()``, so
    the Translation submenu stayed absent until the next restart even though
    the pack was correctly installed on disk.
    """
    source = Path(main_frame_speech_module.__file__).read_text(encoding="utf-8")
    method = source[source.index("def download_braille_pack") :]
    method = method[: method.index("\n    def download_mathcat")]
    finished = method[method.index("def _finished") :][:600]
    assert "self._build_menu()" in finished


def test_download_pack_menu_item_routes_through_optional_components_hub() -> None:
    """Downloading the pack from Tools > Braille dropped the user back into
    the editor instead of keeping them in a guided flow.

    ``download_braille_pack()`` run standalone has no ``on_done`` to return
    to, so its own progress dialog closing was the last thing the user saw.
    The existing "Set Up Braille" prompt (main_frame.py's
    ``enable_braille_mode``) already solves this by routing into
    ``open_optional_components(preselect="braille")``, whose Download button
    reopens the hub via its own ``on_done=_back`` callback afterward -- the
    user is never dropped out into the editor. The direct menu item should
    use the same routing instead of calling ``download_braille_pack()`` on
    its own.
    """
    source = Path(main_frame_braille_module.__file__).read_text(encoding="utf-8")
    binding = source[source.index("self._id_braille_get_pack = wx.NewIdRef()") :][:750]
    assert 'self.open_optional_components(preselect="braille")' in binding
    assert "self.download_braille_pack()" not in binding
