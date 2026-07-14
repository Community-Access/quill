from __future__ import annotations

import sys

from quill.core.keymap import load_keymap
from quill.platform.sr_announce import (
    announce,
    clear_transcript,
    enable_transcript_capture,
    set_announce_handler,
    transcript_entries,
)
from quill.platform.windows.sr_detect import detect_screen_reader


def setup_function() -> None:
    clear_transcript()
    enable_transcript_capture(False)
    set_announce_handler(lambda _message: None)


def test_accessibility_announcements_are_captured_for_harnesses() -> None:
    enable_transcript_capture(True)
    announce("Focused editor region")
    assert transcript_entries() == ["Focused editor region"]


def test_accessibility_screen_reader_detection_snapshot() -> None:
    result = detect_screen_reader(["explorer.exe", "narrator.exe"])
    assert result.detected is True
    assert result.name == "Narrator"


def test_accessibility_key_shortcuts_include_core_navigation(quill_data_dir: object) -> None:
    # Isolate the data dir so this asserts the *default* bindings, not whatever
    # a prior (non-isolated) test left in the real keymap store. load_keymap()
    # reads and even rewrites keymap_path(); without an isolated QUILL_DATA_DIR
    # this test is order-dependent under pytest-randomly.
    keymap = load_keymap()
    # macOS HIG uses Cmd+G / Cmd+Shift+G for Find Next/Previous (keymap.py
    # DEFAULT_KEYMAP, #6) -- bare F3/Shift+F3 need the Fn key held on a stock
    # MacBook, so darwin gets a no-Fn alternate.
    if sys.platform == "darwin":
        assert keymap["edit.find_next"] == "Cmd+G"
        assert keymap["edit.find_previous"] == "Cmd+Shift+G"
    else:
        assert keymap["edit.find_next"] == "F3"
        assert keymap["edit.find_previous"] == "Shift+F3"
    assert keymap["app.command_palette"] == "Ctrl+Shift+P"
