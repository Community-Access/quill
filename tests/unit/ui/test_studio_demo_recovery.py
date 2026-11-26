"""Studio's unfinished demonstration recordings, offered by name (FUX-05).

Recovery named each recording by its hidden work folder, spoke exception text
with temporary paths, offered no way to throw one away, announced itself at
every launch, and finished a recording whose check had failed a second time,
saving a " (2)" copy.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import wx

import quill.apps.studio_demo_finish as finish_module
from quill.apps.studio_demo_finish import StudioDemoFinishMixin
from quill.core.demo_recording import WORK_PREFIX
from quill.core.demo_recording_session import SegmentRecord, SessionRecord
from quill.core.demo_unfinished import describe_unfinished
from quill.stability.task_manager import CancellationToken, UiLifetimeToken


class Tasks:
    def submit(self, _name, work, *, on_success, on_failure, ui_lifetime=None):
        try:
            result = work(cancellation_token=CancellationToken())
        except Exception as error:  # noqa: BLE001
            on_failure(None, error)
        else:
            on_success(None, result)


class Host(StudioDemoFinishMixin):
    def __init__(self, folder: Path) -> None:
        self.frame = None
        self.folder = folder
        self.spoken: list[str] = []
        self.status: list[tuple[str, bool]] = []
        self.choices: list[str] = []
        self.asked: list[str] = []
        self.confirm = wx.YES
        self.results: list[object] = []
        self._task_manager = Tasks()

    def _announce(self, text: str) -> None:
        self.spoken.append(text)

    def _set_status(self, text: str) -> None:
        self.status.append((text, True))

    def _set_status_quiet(self, text: str) -> None:
        self.status.append((text, False))

    def _show_message_box(self, message, *_args):
        self.asked.append(message)
        return self.confirm

    def _ask_unfinished(self, item):
        self.asked.append(item.label)
        return self.choices.pop(0)

    def _demo_folders(self):
        return [self.folder]

    def _demo_ffmpeg(self):
        return "ffmpeg"

    def _demo_caps(self, _ffmpeg):
        return SimpleNamespace(h264_encoder="libx264")

    def _demo_lifetime(self):
        return UiLifetimeToken()

    def _show_demo_result(self, verification, *, title=""):
        self.results.append(verification)


def _work(folder: Path, name: str, *, state: str = "recording", saved: str = "") -> Path:
    work = folder / f"{WORK_PREFIX}{name.replace(' ', '')}"
    work.mkdir(parents=True)
    SessionRecord(
        plan={},
        output=str(folder / f"{name}.mp4"),
        started=datetime(2026, 11, 20, 16, 58).isoformat(),
        segments=[SegmentRecord(index=0, folder=str(work / "1"), duration=725.0, closed=True)],
        state=state,  # type: ignore[arg-type]
        saved=saved,
    ).save(work)
    return work


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(finish_module, "app_data_dir", lambda: tmp_path / "data")
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(
        "quill.platform.windows.focus_guard.restore_after_crash", lambda _dir: False
    )
    return tmp_path


def test_a_recording_is_named_by_what_it_is_not_its_folder(data):
    item = describe_unfinished(_work(data, "Product demo"))
    assert item.label == "Product demo, started Friday 4:58 PM, 12 minutes recorded"
    assert WORK_PREFIX not in item.label


def test_launch_notice_names_them_and_is_spoken_only_once(data):
    _work(data, "Product demo")
    host = Host(data)
    host._offer_demo_recovery()
    host._offer_demo_recovery()
    sentence = (
        "Studio found an unfinished recording: Product demo, started Friday 4:58 PM, "
        "12 minutes recorded. Capture, Recover unfinished recordings finishes or discards it."
    )
    assert host.status == [(sentence, True), (sentence, False)]
    _work(data, "Second demo")
    host._offer_demo_recovery()
    assert host.status[-1][1] is True  # a new set is said again


def test_discard_asks_first_says_it_is_permanent_and_deletes(data):
    work = _work(data, "Product demo")
    host = Host(data)
    host.choices = ["discard"]
    host.recover_demonstrations()
    assert "do not go to the Recycle Bin" in host.asked[-1]
    assert not work.exists()
    assert host.spoken == ["Discarded Product demo."]


def test_declining_the_discard_keeps_it(data):
    work = _work(data, "Product demo")
    host = Host(data)
    host.choices = ["discard"]
    host.confirm = wx.NO
    host.recover_demonstrations()
    assert work.exists()
    assert host.spoken == ["Product demo is kept."]


def test_a_failed_finish_names_the_recording_without_paths(data, monkeypatch):
    _work(data, "Product demo")

    def broken(work, **_kwargs):
        raise RuntimeError(f"Segment 1 could not be finished. The pieces are kept in {work}.")

    monkeypatch.setattr("quill.platform.windows.screen_recorder_finish.finalize", broken)
    host = Host(data)
    host.choices = ["finish"]
    host.recover_demonstrations()
    assert host.spoken == [
        "Product demo could not be finished. Its recorded pieces are kept; Capture, "
        "Recover unfinished recordings tries again or discards them."
    ]


def test_an_already_saved_recording_is_not_finished_twice(data, monkeypatch):
    saved = data / "Product demo.mp4"
    saved.write_bytes(b"video")
    _work(data, "Product demo", state="failed", saved=str(saved))
    calls: list[Path] = []
    monkeypatch.setattr(
        "quill.platform.windows.screen_recorder_finish.finalize",
        lambda work, **_k: calls.append(work),
    )
    host = Host(data)
    host._offer_demo_recovery()
    assert host.status == []  # nothing left to finish: not announced at launch
    item = describe_unfinished(next(data.glob(f"{WORK_PREFIX}*")))
    assert "already saved as Product demo.mp4, but its check found problems" in item.label
    assert not item.needs_finishing
    host.choices = ["skip"]
    host.recover_demonstrations()
    assert calls == []
