"""Regressions from the 2026-10 crash-report sweep (#1613/#1617/#1619/#1634, #1614)."""

from __future__ import annotations

from pathlib import Path

import pytest

import quill.ui.large_file_guard as large_file_guard
import quill.ui.main_frame as main_frame_module
from quill.ui.main_frame import MainFrame


class _KeyEvent:
    def __init__(
        self, key_code: int, *, ctrl: bool = False, alt: bool = False, shift: bool = False
    ) -> None:
        self._key_code = key_code
        self._ctrl = ctrl
        self._alt = alt
        self._shift = shift
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._key_code

    def ControlDown(self) -> bool:
        return self._ctrl

    def AltDown(self) -> bool:
        return self._alt

    def ShiftDown(self) -> bool:
        return self._shift

    def Skip(self) -> None:
        self.skipped = True


def _frame_before_first_document() -> MainFrame:
    """A frame whose focus is on the empty tab host and which has no editor yet.

    That is the first-run wizard window: the notebook exists, the first blank
    document is deferred until the wizard finishes, so ``self.editor`` is unset.
    """
    frame = MainFrame.__new__(MainFrame)
    frame._active_tab = lambda: None  # type: ignore[method-assign]
    frame._focus_is_in_document_surface = lambda: True  # type: ignore[method-assign]

    def _no_key_mode(_event: object) -> bool:
        raise AssertionError("QUILL key mode must not run without an editor")

    frame._handle_quill_key_mode_event = _no_key_mode  # type: ignore[method-assign]
    frame._quill_key_mode_active = True
    frame._quill_key_prefix_pending = True
    frame._quill_key_prefix_started_at = 1.0
    frame._quill_key_mode_started_at = 1.0
    return frame


@pytest.mark.parametrize(
    "event",
    [
        _KeyEvent(ord("B")),  # 1634: NVDA's B for "next button" during the wizard
        _KeyEvent(ord("3"), alt=True, shift=True),  # set quick bookmark 3
        _KeyEvent(ord("3"), ctrl=True, alt=True, shift=True),  # go to quick bookmark 3
    ],
)
def test_char_hook_before_first_document_passes_keys_through(event: _KeyEvent) -> None:
    frame = _frame_before_first_document()
    assert not hasattr(frame, "editor")

    frame._on_char_hook(event)

    assert event.skipped is True
    assert frame._quill_key_mode_active is False
    assert frame._quill_key_prefix_pending is False


def test_too_large_to_open_threshold_and_message() -> None:
    ceiling = large_file_guard.TOO_LARGE_TO_OPEN_BYTES
    assert not large_file_guard.is_too_large_to_open(ceiling)
    assert large_file_guard.is_too_large_to_open(ceiling + 1)
    assert large_file_guard.is_large_file(ceiling)  # the ceiling sits above the warning
    message = large_file_guard.too_large_message("model.gguf", 4 * 1024**3)
    assert "model.gguf" in message and "4.0 GB" in message and "too large" in message
    assert large_file_guard.open_prompt("a.txt", 10) is None
    assert large_file_guard.open_prompt("a.log", ceiling)[1] is False  # type: ignore[index]
    assert large_file_guard.open_prompt("a.img", ceiling + 1)[1] is True  # type: ignore[index]


def test_open_file_refuses_past_the_ceiling_without_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#1614: a multi-gigabyte file was read whole and raised MemoryError."""
    big = tmp_path / "model.gguf"
    big.write_bytes(b"x" * 64)
    monkeypatch.setattr(large_file_guard, "TOO_LARGE_TO_OPEN_BYTES", 32)
    monkeypatch.setattr(main_frame_module, "is_trusted_location", lambda *_a: True)

    def _must_not_read(*_a: object, **_k: object) -> object:
        raise AssertionError("the file must not be read")

    monkeypatch.setattr(main_frame_module, "read_open_document", _must_not_read)

    frame = MainFrame.__new__(MainFrame)
    frame._trusted_locations = set()
    frame._clear_empty_workspace_state = lambda: None  # type: ignore[method-assign]
    frame._find_tab_index = lambda _path: -1  # type: ignore[method-assign]
    boxes: list[tuple[str, str]] = []
    statuses: list[str] = []
    frame._show_message_box = lambda message, caption, *_a, **_k: (
        boxes.append((message, caption)) or 0
    )  # type: ignore[method-assign]
    frame._set_status = statuses.append  # type: ignore[method-assign]
    frame._read_open_document_guarded = _must_not_read  # type: ignore[method-assign]
    frame._run_background_task = _must_not_read  # type: ignore[method-assign]

    frame.open_file(big)

    assert len(boxes) == 1
    assert "model.gguf" in boxes[0][0] and "too large" in boxes[0][0]
    assert boxes[0][1] == "File too large"
    assert statuses == ["Open cancelled"]


def test_quill_lite_refuses_past_the_same_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.apps.lite as lite

    big = tmp_path / "disk.img"
    big.write_bytes(b"x" * 64)
    monkeypatch.setattr(large_file_guard, "TOO_LARGE_TO_OPEN_BYTES", 32)
    shown: list[str] = []
    monkeypatch.setattr(
        lite, "show_message_box", lambda message, *_a, **_k: shown.append(message) or 0
    )

    assert lite.QuillLiteApp._confirm_large_file(None, big) is False  # type: ignore[arg-type]
    assert len(shown) == 1 and "disk.img" in shown[0] and "too large" in shown[0]


def test_quill_lite_still_asks_below_the_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    import quill.apps.lite as lite

    big = tmp_path / "big.log"
    big.write_bytes(b"x" * 64)
    monkeypatch.setattr(large_file_guard, "LARGE_FILE_WARN_BYTES", 16)
    asked: list[int] = []
    monkeypatch.setattr(
        lite, "show_message_box", lambda _m, _c, style: asked.append(style) or wx.YES
    )

    assert lite.QuillLiteApp._confirm_large_file(None, big) is True  # type: ignore[arg-type]
    assert asked and asked[0] & wx.YES_NO
