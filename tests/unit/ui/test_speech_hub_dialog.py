"""Source-contract test for the Speech Hub dialog (fix.md #3).

Assert the wiring in :mod:`quill.ui.speech_hub_dialog` without spinning up a
real wx UI, matching the convention in test_remote_sites_dialog.py.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "quill" / "ui" / "speech_hub_dialog.py"
_MAIN_FRAME = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py"


def _read_source() -> str:
    return ROOT.read_text(encoding="utf-8")


def _read_main_frame_source() -> str:
    return _MAIN_FRAME.read_text(encoding="utf-8")


def test_module_calls_focus_primary_control() -> None:
    src = _read_source()
    # The dialog was opening with focus parked on OK/Cancel instead of the
    # first real Read Aloud / Dictation control (fix.md #3).
    assert "focus_primary_control" in src


def test_four_tabs_named_and_indexed() -> None:
    """Speech and Dictation each split into Offline/Online tabs (#847) so
    local engines (installed once) and cloud providers (an API key, per-use
    network cost) are not mixed in one flat list."""
    src = _read_source()
    for label in (
        '"Speech (Offline)"',
        '"Speech (Online)"',
        '"Dictation (Offline)"',
        '"Dictation (Online)"',
    ):
        assert label in src
    assert "TAB_SPEECH_OFFLINE = 0" in src
    assert "TAB_SPEECH_ONLINE = 1" in src
    assert "TAB_DICTATION_OFFLINE = 2" in src
    assert "TAB_DICTATION_ONLINE = 3" in src


def test_both_speech_tabs_share_one_action_callback() -> None:
    """Whichever Speech tab (Offline or Online) is used, the result is handled
    identically by the caller -- both dispatch into the same callback."""
    src = _read_source()
    assert "self._voice_browser_offline = VoiceBrowserDialog(" in src
    assert "self._voice_browser_online = VoiceBrowserDialog(" in src
    assert src.count("on_action=self._on_ra_action") == 2


def test_both_dictation_tabs_share_one_action_callback() -> None:
    src = _read_source()
    assert "self._speech_setup_offline = SpeechSetupDialog(" in src
    assert "self._speech_setup_online = SpeechSetupDialog(" in src
    assert src.count("on_action=self._on_dict_action") == 2


def test_no_cloud_dictation_provider_shows_a_message_not_an_empty_dialog() -> None:
    """A wx.RadioBox cannot hold zero choices -- when no cloud dictation
    provider is registered, Dictation (Online) must not try to construct
    SpeechSetupDialog with an empty engine list."""
    src = _read_source()
    assert "if dictation_online_kwargs is None:" in src
    assert "_build_no_cloud_dictation_panel(wx, dict_online_page)" in src
    assert "def _build_no_cloud_dictation_panel(" in src


def test_ok_without_action_collects_from_whichever_speech_tab_is_active() -> None:
    src = _read_source()
    assert "selection = self._nb.GetSelection()" in src
    assert "self._voice_browser_offline.collect_result()" in src
    assert "self._voice_browser_online.collect_result()" in src


def test_open_speech_hub_builds_four_kwargs_sets() -> None:
    """main_frame.py's open_speech_hub splits the engine/provider lists into
    Offline/Online before constructing the hub, rather than the old single
    read_aloud_kwargs/dictation_kwargs pair."""
    src = _read_main_frame_source()
    assert "read_aloud_offline_kwargs=read_aloud_offline_kwargs," in src
    assert "read_aloud_online_kwargs=read_aloud_online_kwargs," in src
    assert "dictation_offline_kwargs=dictation_offline_kwargs," in src
    assert "dictation_online_kwargs=dictation_online_kwargs," in src
    # ElevenLabs is the only cloud Read Aloud engine; everything else is offline.
    assert 'online_engine_options: list[tuple[str, str]] = [\n            ("ElevenLabs' in src
    # Dictation (Online) is None (empty-state panel) when nothing is registered
    # beyond the three known offline engines.
    assert "known_offline_ids = {" in src
    assert "cloud_providers = [" in src


def test_common_dict_kwargs_supplies_every_speech_setup_dialog_required_arg() -> None:
    """Regression for #949/#950: SpeechSetupDialog.__init__ requires kokoro_ok
    and kokoro_can_install as keyword-only args (alongside the already-passed
    vosk_ok/vosk_can_install), but common_dict_kwargs in open_speech_hub never
    supplied them -- every call to Tools > Speech > Speech and Dictation raised
    'TypeError: SpeechSetupDialog.__init__() missing 2 required keyword-only
    arguments' since common_dict_kwargs is spread into both the offline and
    online SpeechSetupDialog constructions."""
    setup_dialog_src = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "speech_setup_dialog.py"
    ).read_text(encoding="utf-8")
    assert "kokoro_ok: bool," in setup_dialog_src
    assert "kokoro_can_install: bool," in setup_dialog_src

    main_frame_src = _read_main_frame_source()
    assert '"kokoro_ok": is_kokoro_onnx_available(),' in main_frame_src
    assert '"kokoro_can_install": kokoro_onnx_install_supported(),' in main_frame_src
    # Both must live inside common_dict_kwargs (spread into both dictation
    # kwargs dicts), not bolted onto only one of them.
    common_start = main_frame_src.index("common_dict_kwargs: dict = {")
    common_end = main_frame_src.index("}", common_start)
    common_block = main_frame_src[common_start:common_end]
    assert '"kokoro_ok": is_kokoro_onnx_available(),' in common_block
    assert '"kokoro_can_install": kokoro_onnx_install_supported(),' in common_block


def test_open_speech_hub_callers_use_named_tab_constants() -> None:
    src = _read_main_frame_source()
    assert "self.open_speech_hub(TAB_SPEECH_OFFLINE)" in src
    speech_setup_src = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_speech.py"
    ).read_text(encoding="utf-8")
    assert "self.open_speech_hub(TAB_DICTATION_OFFLINE)" in speech_setup_src
