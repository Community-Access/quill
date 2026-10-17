"""QUILL's clipboard collector saves a named document as it collects (2026-10-15).

``clipboard_collector_saves``, on by default: each collected clip in a document
with a file name is followed by a quiet save, and the person hears one sentence,
"Collected and saved". An untitled document is never saved and Save As never
opens. A save that cannot happen is spoken, and collecting carries on.

The host is the real collector mixin plus the real write-safety mixin (so the
failure sentence is the one Save shows); only the disk write itself is faked,
because ``_write_named_document`` is Save's own step and Save's tests own it.
"""

from __future__ import annotations

import errno
import os
import time
from pathlib import Path
from types import SimpleNamespace

from quill.core.clipboard_collector import (
    COLLECTED,
    COLLECTED_AND_SAVED,
    DEFAULT_DIVIDER,
    collected_but_not_saved,
    disk_changed_reason,
    encoding_reason,
    saves_after_collect,
)
from quill.core.external_change import FileSnapshot
from quill.ui.main_frame_clipboard_collector import ClipboardCollectorMixin
from quill.ui.main_frame_write_safety import WriteSafetyMixin


class _Editor:
    def __init__(self) -> None:
        self.value = ""

    def GetValue(self) -> str:
        return self.value

    def SetValue(self, text: str) -> None:
        self.value = text

    def SetInsertionPoint(self, _pos: int) -> None:
        pass

    def SetSelection(self, _start: int, _end: int) -> None:
        pass


class _Document:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.text = ""
        self.modified = False
        self.encoding = "utf-8"

    @property
    def name(self) -> str:
        return self.path.name if self.path is not None else "Untitled"

    def set_text(self, text: str) -> None:
        self.text = text
        self.modified = True


class _Host(ClipboardCollectorMixin, WriteSafetyMixin):
    def __init__(self, path: Path | None, *, saves: bool = True) -> None:
        self.settings = SimpleNamespace(clipboard_collector_saves=saves)
        self.document = _Document(path)
        self.editor = _Editor()
        self.tab = SimpleNamespace(read_only_remote=False, disk_baseline=None)
        self.said: list[str] = []
        self.written: list[str] = []
        self.fail_with: OSError | None = None
        self.clip = ""

    # What the frame provides.
    def _document_is_read_only(self) -> bool:
        return False

    def _power_tools_clipboard_text(self) -> str:
        return self.clip

    def _replace_document_text(self, text: str) -> None:
        self.editor.SetValue(text)

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _active_tab(self) -> object:
        return self.tab

    def _write_named_document(self) -> OSError | None:
        if self.fail_with is not None:
            return self.fail_with
        self.written.append(self.document.text)
        self.document.modified = False
        return None

    # Windows the collector must never open.
    def save_file(self) -> None:  # pragma: no cover - reaching this fails the test
        raise AssertionError("the collector must not run Save")

    def save_file_as(self) -> None:  # pragma: no cover - reaching this fails the test
        raise AssertionError("the collector must never open Save As")

    def _show_message_box(self, *_args: object) -> None:  # pragma: no cover
        raise AssertionError("a quiet save must never open a message box")

    def collect(self, clip: str) -> None:
        self.clip = clip
        self.collect_clipboard_now(announce_refusals=False)


def test_the_shared_rule_saves_only_a_named_document_with_the_setting_on() -> None:
    assert saves_after_collect(True, True)
    assert not saves_after_collect(True, False)
    assert not saves_after_collect(False, True)
    assert collected_but_not_saved("Disk full.") == "Collected, but not saved. Disk full."


def test_a_named_document_is_saved_after_every_clip_and_says_so_once(tmp_path: Path) -> None:
    host = _Host(tmp_path / "notes.md")
    host.collect("first")
    host.collect("second")
    assert host.written == ["first", "first" + DEFAULT_DIVIDER + "second"]
    assert host.said == [COLLECTED_AND_SAVED, COLLECTED_AND_SAVED]
    assert host.document.modified is False


def test_an_untitled_document_collects_and_is_never_saved() -> None:
    host = _Host(None)
    host.collect("clip")
    assert host.editor.GetValue() == "clip"
    assert host.written == []
    assert host.said == [COLLECTED]
    assert host.document.modified is True


def test_the_setting_off_collects_without_saving(tmp_path: Path) -> None:
    host = _Host(tmp_path / "notes.md", saves=False)
    host.collect("clip")
    assert host.written == []
    assert host.said == [COLLECTED]


def test_a_failed_save_is_spoken_and_collecting_carries_on(tmp_path: Path) -> None:
    host = _Host(tmp_path / "notes.md")
    host.fail_with = OSError(errno.ENOSPC, "No space left on device")
    host.collect("one")
    assert len(host.said) == 1
    assert host.said[0].startswith("Collected, but not saved. The disk is full.")
    assert "notes.md" in host.said[0]
    host.fail_with = None
    host.collect("two")
    assert host.editor.GetValue() == "one" + DEFAULT_DIVIDER + "two"
    assert host.said[-1] == COLLECTED_AND_SAVED


def test_a_file_another_program_changed_is_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("mine", encoding="utf-8")
    host = _Host(path)
    host.tab.disk_baseline = FileSnapshot.of(path)
    path.write_text("theirs, and longer", encoding="utf-8")
    later = time.time() + 5
    os.utime(path, (later, later))
    host.collect("clip")
    assert host.written == []
    assert host.said == [collected_but_not_saved(disk_changed_reason("notes.md"))]


def test_a_document_save_would_send_to_save_as_just_collects(tmp_path: Path) -> None:
    host = _Host(tmp_path / "scan.pdf")  # extracted text: Save would ask for a new name
    host.collect("clip")
    assert host.written == []
    assert host.said == [COLLECTED]


def test_the_encoding_reason_names_the_file_and_the_encoding() -> None:
    reason = encoding_reason("notes.txt", "cp1252")
    assert "notes.txt" in reason and "cp1252" in reason
