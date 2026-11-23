"""QUILL Lite's File > Scribe for Documents, through the handlers the menu binds (PRD 8.2).

Each ``cmd_scribe_*`` reaches the shared controller (the same entry points
QUILL has); with the ``scribe`` area off, a command reached anyway says how to
turn it on and sends nothing; the scanned-import question offers Scribe, and
with the area off it offers to turn it on, then says once where it is.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class _Controller:
    """Records what the shared commands asked the controller for."""

    app_name = "QUILL Lite"

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, Any]] = []
        self.session = type("S", (), {"is_signed_in": lambda self: False})()

    def check_available(self) -> bool:
        return True

    def unavailable(self) -> str:
        return ""

    def convert_files(self, *a: Any, **k: Any) -> list[str]:
        self.calls.append(("convert_files", a, k))
        return ["a job"]

    def about(self) -> str:
        return "Powered by Scribe for Documents."

    def __getattr__(self, name: str) -> Any:
        return lambda *a, **k: self.calls.append((name, a, k))


@pytest.fixture
def scribe_window(lite_window: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    win = lite_window("Some text")
    controller = _Controller()
    monkeypatch.setattr(win, "_scribe", lambda: controller)
    win.controller = controller
    source = tmp_path / "Notes.docx"
    source.write_bytes(b"docx")
    win.path = source
    win.modified = False
    return win


def test_every_row_reaches_the_shared_controller(scribe_window: Any, monkeypatch: Any) -> None:
    import quill.ui.dialog_contract as contract

    monkeypatch.setattr(contract, "show_message_box", lambda *a, **k: None)
    win = scribe_window
    for command in (
        lambda w: w.cmd_scribe_my_documents(),
        lambda w: w.cmd_scribe_conversions(),
        lambda w: w.cmd_scribe_window(),
        lambda w: w.cmd_scribe_status(),
        lambda w: w.cmd_scribe_repeat(),
        lambda w: w.cmd_scribe_sign_in(),
        lambda w: w.cmd_scribe_sign_out(),
        lambda w: w.cmd_scribe_account(),
        lambda w: w.cmd_scribe_options(),
        lambda w: w.cmd_scribe_about(),
    ):
        command(win)
    assert [c[0] for c in win.controller.calls] == [
        "my_documents",
        "open_conversions",
        "open_conversions",
        "status",
        "repeat_last",
        "sign_in",
        "sign_out",
        "open_account_in_browser",
        "show_options",
    ]


def test_convert_this_and_export_send_the_saved_document(scribe_window: Any) -> None:
    win = scribe_window
    (lambda w: w.cmd_scribe_convert_this())(win)
    (lambda w: w.cmd_scribe_export())(win)
    assert win.controller.calls == [
        ("convert_files", ([win.path],), {"app_formats": None, "open_as": "", "title": "Notes"}),
        ("convert_files", ([win.path],), {"app_formats": ["pdf"], "open_as": "", "title": "Notes"}),
    ]


def test_convert_a_file_offers_only_what_scribe_takes(
    scribe_window: Any, fake_wx_dialog: Any, tmp_path: Path
) -> None:
    import wx

    picked = tmp_path / "Scan.pdf"
    picked.write_bytes(b"%PDF")
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPaths=[str(picked)], GetPath=str(picked))
    win = scribe_window
    (lambda w: w.cmd_scribe_convert_file())(win)
    assert win.controller.calls[0][0] == "convert_files"
    assert win.controller.calls[0][1][0] == [picked]


def test_convert_from_a_link_refuses_what_is_not_an_address(
    scribe_window: Any, fake_wx_dialog: Any
) -> None:
    import wx

    fake_wx_dialog("TextEntryDialog", wx.ID_OK, GetValue="not a link")
    win = scribe_window
    (lambda w: w.cmd_scribe_convert_link())(win)
    assert win.controller.calls == []
    assert win.announcements[-1] == "That is not a web address. Nothing was sent."


def test_with_the_area_off_a_command_says_how_to_turn_it_on(
    scribe_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    win = scribe_window
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "scribe")
    (lambda w: w.cmd_scribe_my_documents())(win)
    assert win.controller.calls == []
    assert "Customize Features" in win.announcements[-1]


def test_the_import_question_turns_scribe_on_on_first_need(
    scribe_window: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    win = scribe_window
    switched: list[tuple[str, bool]] = []
    win.app.features = type(
        "F", (), {"set_enabled": lambda self, a, on: switched.append((a, on))}
    )()
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "scribe")
    asked: list[bool] = []

    def question(source: Path, pages: int, *, turn_on: bool = False) -> str:
        asked.append(turn_on)
        return "scribe"

    monkeypatch.setattr(win, "_scribe_scanned_choice", question)
    scan = tmp_path / "Scan.pdf"
    scan.write_bytes(b"%PDF")
    outcome = type("O", (), {"offer_local_ocr": True, "page_count": 3, "text": ""})()
    win._import_lifetime = lifetime = type("L", (), {"is_alive": True})()
    win._import_finished(lifetime, scan, outcome)
    assert asked == [True] and switched == [("scribe", True)]
    assert win.controller.calls[0][0] == "convert_files"
    assert win.controller.calls[0][2]["open_as"] == "import"
    assert win.announcements[-1] == "Scribe for Documents is on. It is in the File menu."


# ------------------------------------- a result opens after its sentence


def test_a_result_window_waits_for_its_sentence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new window (Lite's or Media Player's) takes focus and the reader says
    it, which would cut the result sentence off: it opens after the sentence,
    once, or after a second when no sentence follows."""
    import wx

    from quill.apps import lite_window_scribe
    from quill.apps.lite_window_scribe import LiteScribeHost, wait_for_sentence
    from quill.core.scribe import queue as q
    from quill.stability import wx_dispatch

    timers: list[tuple[int, Any]] = []
    monkeypatch.setattr(
        wx_dispatch, "call_later_safely", lambda ms, fn, *a, **k: timers.append((ms, fn))
    )
    monkeypatch.setattr(wx, "GetActiveWindow", lambda: object())  # QUILL Lite is in front
    sent: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        lite_window_scribe, "_send_to_player", lambda f, p: sent.append((f, p)) or True
    )
    said: list[str] = []
    window = type("W", (), {"_announce": lambda _s, text: said.append(text)})()
    opened: list[Path] = []
    app = type("App", (), {"frames": [window], "active_frame": window,
                           "open_path": lambda _s, p: opened.append(Path(p))})()  # fmt: skip
    host = LiteScribeHost(app)
    mp3 = tmp_path / "Notes.mp3"
    mp3.write_bytes(b"ID3")

    assert host.scribe_open_result(q.Job(), "mp3", mp3) == "The MP3 audio is open in Media Player"
    assert sent == []  # not yet: the sentence comes first
    host.scribe_announce("The MP3 audio is open in Media Player.")
    assert sorted(ms for ms, _fn in timers) == [1_000, wait_for_sentence(said[0])]
    for _ms, fn in timers:
        fn()
    assert sent == [("mp3", mp3)]  # once, not once per timer

    # No sentence at all: it still opens, after a second.
    timers.clear()
    host.scribe_open_result(q.Job(), "docx", tmp_path / "Notes.docx")
    assert [ms for ms, _fn in timers] == [1_000]
    timers[0][1]()
    assert opened == [tmp_path / "Notes.docx"]
    assert 1_500 <= wait_for_sentence("x") and wait_for_sentence("x" * 1000) == 6_000
