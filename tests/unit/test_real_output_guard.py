"""GATE: the test suite never speaks through the real screen reader.

Jeff, 2026-10-17: with JAWS running, agents' test runs read Radio's errors to
him ("Radio settings could not be saved", the missing-mpv notice). The guard is
``tests/real_output_guard.py``, installed for the whole session by
``tests/conftest.py``. These tests prove it holds for the window that did it --
a real Quill Radio frame -- and that each layer answers the way it says.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests import real_output_guard as guard
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture
def radio_frame(quill_data_dir):
    app = shared_wx_app()
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        frame._radio_shutdown()
        frame.frame.Destroy()
        del app


def test_a_radio_window_built_in_a_test_speaks_only_to_the_recorder(radio_frame) -> None:
    engine = radio_frame._announcement_engine
    state = engine.state()
    # No live reader was acquired: what CI gets, whatever runs on this machine.
    assert state.active_backend not in {"prism", "accessible_output2", "uia_notification"}
    assert engine._runtime_backend is None
    assert engine._ao2_speaker is None

    with guard.spoken_during() as said:
        radio_frame._announce("Guard check: nothing reaches the reader.")
        engine.announce("Guard check, straight to the engine.", force_speech=True)
        guard.flush_speech()
    assert "Guard check, straight to the engine." in said
    assert guard.VIOLATIONS == []


def test_a_radio_window_has_no_real_media_engine(radio_frame) -> None:
    controller = radio_frame._radio_controller
    assert isinstance(controller._wx_engine, guard.InertMediaEngine)


def test_radio_history_saves_into_the_tests_own_folder_and_reloads(radio_frame) -> None:
    from quill.core.radio.history_store import load_history
    from quill.ui.radio.history_save import save_history_async

    radio_frame._radio_history.resume_on_launch = True
    assert save_history_async(radio_frame)
    assert radio_frame._radio_history_save_coordinator.flush(3)
    data_dir = Path(os.environ["QUILL_DATA_DIR"])
    assert load_history(data_dir).resume_on_launch is True


def test_each_test_gets_its_own_data_folder_by_default() -> None:
    folder = os.environ.get("QUILL_DATA_DIR", "")
    assert "default-data" in folder
    appdata = os.environ.get("APPDATA")
    if appdata:
        assert not Path(folder).resolve().is_relative_to(Path(appdata).resolve())


def test_a_real_sapi_voice_or_message_box_is_a_tripwire() -> None:
    from quill.platform.windows import sapi5

    with pytest.raises(RuntimeError):
        sapi5.create_voice()
    assert wx.MessageBox("Should never show", "Guard") == wx.CANCEL
    reached = guard.take_violations()
    assert any("SAPI" in item for item in reached)
    assert any("MessageBox" in item for item in reached)


def test_a_staged_libmpv_is_invisible_and_a_real_one_refused(tmp_path) -> None:
    from quill.core import source_tools
    from quill.ui.audio import mpv_engine

    assert source_tools.staged_tool_dir("mpv") is None
    dll = tmp_path / "libmpv-2.dll"
    dll.write_bytes(b"not really a dll")
    with pytest.raises(OSError):
        mpv_engine._MpvClient(dll)
    assert any("libmpv" in item for item in guard.take_violations())


def test_sounds_are_recorded_not_played() -> None:
    winsound = pytest.importorskip("winsound")
    before = len(guard.SOUNDS)
    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
    assert guard.SOUNDS[before:] == ["SystemAsterisk"]
