"""The duplicate Parakeet/Nemotron path's deprecation (design record sections 32.6, 35).

Said once, never silently; old files offered for deletion once, No by default;
nothing deleted without a Yes; the space freed measured, not estimated.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core.settings import Settings
from quill.core.speech import sherpa_migration as sm


def test_a_saved_legacy_engine_owes_one_notice() -> None:
    assert sm.migration_notice({"speech_provider": "nemotron"}) == "pending"
    assert sm.migration_notice({"speech_provider": "parakeet"}) == "pending"
    assert sm.migration_notice({"speech_provider": "sherpa"}) == ""
    assert sm.migration_notice({"speech_provider": ""}) == ""


def test_a_notice_already_said_is_never_rearmed() -> None:
    data = {"speech_provider": "nemotron", "sherpa_migration_notice": "done"}
    assert sm.migration_notice(data) == "done"
    assert sm.migration_notice({"sherpa_migration_notice": "bogus"}) == ""


def test_settings_carry_the_notice_and_the_moved_engine() -> None:
    settings = Settings.from_dict({"speech_provider": "nemotron"})
    assert settings.speech_provider == "sherpa"
    assert settings.sherpa_migration_notice == "pending"
    assert Settings.from_dict({}).sherpa_migration_notice == ""


def _write(path: Path, size: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


def test_the_older_nemotron_is_a_leftover_and_a_linked_parakeet_is_not(tmp_path: Path) -> None:
    legacy = tmp_path / "speech-models"
    _write(legacy / "nemotron" / "nemotron-streaming-en-0.6b" / "encoder.onnx", 3000)
    store = _write(tmp_path / "store" / "parakeet" / "encoder.onnx", 2000)
    linked = legacy / "parakeet" / "parakeet-tdt-0.6b-v3" / "encoder.onnx"
    linked.parent.mkdir(parents=True)
    os.link(store, linked)  # adopted: the same bytes, a second name
    found = sm.legacy_leftovers(legacy)
    assert [(folder.name, size) for folder, size in found] == [("nemotron-streaming-en-0.6b", 3000)]


def test_nothing_is_a_leftover_without_the_old_folders(tmp_path: Path) -> None:
    assert sm.legacy_leftovers(tmp_path / "missing") == []


def test_removal_reports_the_bytes_it_actually_freed(tmp_path: Path) -> None:
    legacy = tmp_path / "speech-models"
    folder = legacy / "nemotron" / "old"
    _write(folder / "a.onnx", 1500)
    _write(folder / "sub" / "b.txt", 500)
    assert sm.remove_leftovers([folder], legacy) == 2000
    assert not folder.exists()


def test_removal_never_reaches_outside_the_old_engine_folders(tmp_path: Path) -> None:
    legacy = tmp_path / "speech-models"
    outside = _write(tmp_path / "documents" / "keep.txt", 100)
    assert sm.remove_leftovers([outside.parent], legacy) == 0
    assert outside.is_file()


# --------------------------------------------------------------------------- #
# The one-time notice (quill.ui.sherpa_migration_notice)
# --------------------------------------------------------------------------- #


class _Host:
    def __init__(self, settings: Settings, answer: int = wx.NO) -> None:
        self.settings = settings
        self.spoken: list[str] = []
        self.asked: list[tuple[str, str, int]] = []
        self.answer = answer

    def _announce(self, message: str, **_kwargs: Any) -> None:
        self.spoken.append(message)

    def _show_message_box(self, message: str, caption: str, style: int) -> int:
        self.asked.append((message, caption, style))
        return self.answer


@pytest.fixture
def _no_save(monkeypatch: pytest.MonkeyPatch) -> list[Settings]:
    saved: list[Settings] = []
    monkeypatch.setattr("quill.core.settings.save_settings", saved.append)
    return saved


def _now(_delay_ms: int, run: Any) -> None:
    run()


def test_without_old_files_the_move_is_said_once(_no_save: list[Settings]) -> None:
    from quill.ui import sherpa_migration_notice as notice

    host = _Host(Settings.from_dict({"speech_provider": "parakeet"}))
    assert notice.say_now(host, leftovers=list) is True
    assert host.spoken == [notice.NOTICE]
    assert host.asked == []
    assert host.settings.sherpa_migration_notice == "done"
    assert notice.say_now(host, leftovers=list) is False
    assert host.spoken == [notice.NOTICE]


def test_old_files_are_offered_once_with_no_the_default(
    tmp_path: Path, _no_save: list[Settings]
) -> None:
    from quill.ui import sherpa_migration_notice as notice

    removed: list[list[Path]] = []
    host = _Host(Settings.from_dict({"speech_provider": "nemotron"}), answer=wx.NO)
    found = [(tmp_path / "old", 650_000_000)]
    assert notice.say_now(host, leftovers=lambda: found, remove=removed.append) is True
    message, title, style = host.asked[0]
    assert "free 650 MB" in message and "No keeps them" in message
    assert title == notice.TITLE
    assert style & wx.NO_DEFAULT and style & wx.YES_NO
    assert removed == []  # No: nothing deleted
    assert host.spoken == []  # the box was read whole; nothing announced beside it
    assert host.settings.sherpa_migration_notice == "done"


def test_yes_deletes_and_says_the_space_freed(tmp_path: Path, _no_save: list[Settings]) -> None:
    from quill.ui import sherpa_migration_notice as notice

    host = _Host(Settings.from_dict({"speech_provider": "nemotron"}), answer=wx.YES)
    found = [(tmp_path / "old", 1_500_000_000)]
    asked_for: list[list[Path]] = []

    def remove(folders: list[Path]) -> int:
        asked_for.append(folders)
        return 1_480_000_000

    notice.say_now(host, leftovers=lambda: found, remove=remove)
    assert asked_for == [[tmp_path / "old"]]
    assert host.spoken == ["Freed 1.5 GB."]


def test_the_notice_waits_while_a_modal_window_is_open(_no_save: list[Settings]) -> None:
    from quill.ui import sherpa_migration_notice as notice

    host = _Host(Settings.from_dict({"speech_provider": "nemotron"}))
    queued: list[Any] = []
    assert notice.surface_sherpa_migration_notice(
        host, later=lambda _ms, run: queued.append(run), modal_open=lambda: True
    )
    queued.pop(0)()  # blocked: tries again later, says nothing
    assert host.spoken == [] and host.settings.sherpa_migration_notice == "pending"


def test_nothing_is_scheduled_without_a_move() -> None:
    from quill.ui import sherpa_migration_notice as notice

    host = _Host(Settings.from_dict({"speech_provider": "sherpa"}))
    assert notice.surface_sherpa_migration_notice(host, later=_now) is False


def test_sizes_are_said_in_plain_units() -> None:
    from quill.ui.sherpa_migration_notice import size_words

    assert size_words(650_000_000) == "650 MB"
    assert size_words(1_500_000_000) == "1.5 GB"
    assert size_words(10) == "1 MB"
