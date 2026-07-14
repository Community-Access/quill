"""Source-contract tests for the Download Optional Components dialog.

Constructing a real wx.Dialog is not exercised in this suite (matching the
repo's dialog-test convention); these assert the source wires the warm-hub
contract: a rich description box, Download-gating, Test and Remove buttons, the
seam helpers, and controller delegation.
"""

from __future__ import annotations

from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"


def _src(name: str) -> str:
    return (_UI / name).read_text(encoding="utf-8")


def test_dialog_has_download_test_remove_buttons() -> None:
    src = _src("optional_components_dialog.py")
    assert 'name="optional_components_download"' in src
    assert 'name="optional_components_test"' in src
    assert 'name="optional_components_remove"' in src


def test_dialog_uses_a_readonly_multiline_description() -> None:
    src = _src("optional_components_dialog.py")
    assert "TE_MULTILINE" in src and "TE_READONLY" in src
    assert "describe_component(" in src


def test_dialog_gates_download_when_installed() -> None:
    src = _src("optional_components_dialog.py")
    # Download/Test key off effective_ready, not installed: most components
    # agree, but the Dictation row is "installed" as soon as its engine binary
    # exists even with no model downloaded yet (#kokoro-focus follow-up).
    # Download itself is gated through download_allowed(), not a bare "not
    # ready" check: the Offline Edition build always disables Download since
    # every component is already bundled or was never included at build time
    # (Offline Edition awareness).
    assert "can_download = download_allowed(comp)" in src
    assert "download_btn.Enable(can_download)" in src
    assert 'test_btn.Enable(ready or testing["active"])' in src
    assert "comp.effective_ready" in src


def test_dialog_delegates_to_controller_and_uses_the_seam() -> None:
    src = _src("optional_components_dialog.py")
    assert "controller.test(" in src
    assert "controller.remove(" in src
    assert "controller.removable(" in src
    assert "apply_modal_ids(" in src
    assert "show_message_box(" in src  # not raw wx.MessageBox
    assert "preselect" in src


def test_open_optional_components_routes_and_covers_all_downloads() -> None:
    src = _src("main_frame_speech.py")
    # Stay-open hub via a controller, preselect support, and the downloads wired
    # into the dispatch.
    assert "preselect" in src
    assert '"node": lambda: self.download_node_runtime(on_done=_back)' in src
    assert "def download_node_runtime" in src
    assert "def _test_optional_component" in src
    assert "def _remove_optional_component" in src


def test_hub_downloads_reopen_the_hub_when_done() -> None:
    """After a download the hub reopens, so the user is never dropped out of it
    (the hub closes itself to dispatch). It reopens on the row just downloaded,
    not the top of the list, so returning doesn't jarringly reset position."""
    src = _src("main_frame_speech.py")
    assert "def _back(" in src and "self.open_optional_components(preselect=chosen)" in src
    # Every download handler gets the reopen callback -- no download drops you out.
    # Vosk has no standalone hub row (it's a guided-picker engine choice), and
    # FFmpeg is folded into the "audio_extras" row (fetched on demand at export),
    # so neither is in this list.
    for handler in (
        "self.download_piper_exe(on_done=_back)",
        "self.download_espeak_exe(on_done=_back)",
        "self.download_dectalk_exe(on_done=_back)",
        "self.download_node_runtime(on_done=_back)",
        "self._download_kokoro_models(on_done=_back)",
        "self.download_braille_pack(on_done=_back)",
        "self.download_audio_extras(on_done=_back)",
        "self.download_mathcat(on_done=_back)",
        "self.download_git(on_done=_back)",
        "self.download_gh(on_done=_back)",
    ):
        assert handler in src, f"hub dispatch missing reopen-hub for {handler}"
    assert "on_ok=(lambda: on_done(True)) if on_done else" in src
    # The spell-check download path reopens the hub too, instead of dropping
    # the user into the editor.
    assert '_download_then_apply(wx, self, chosen[len("spell-") :], on_done=_back)' in src


def test_startup_braille_prompt_routes_into_the_hub() -> None:
    src = _src("main_frame.py")
    assert 'open_optional_components(preselect="braille")' in src


def test_dialog_loads_component_list_off_the_ui_thread() -> None:
    """gather runs tool version probes + filesystem scans; the dialog must build
    the list on a worker so it opens instantly, not stall on those probes."""
    src = _src("optional_components_dialog.py")
    assert "import threading" in src
    assert "threading.Thread(" in src
    assert "wx.CallAfter(_populate" in src
    assert "Loading components" in src


def test_dialog_has_manage_routing_button() -> None:
    src = _src("optional_components_dialog.py")
    assert 'name="optional_components_manage"' in src
    assert "controller.manage(" in src
    assert "manage_target(" in src  # label/enable driven by the component's route


def test_manage_routes_to_speech_models_and_voices() -> None:
    src = _src("main_frame_speech.py")
    assert "def _manage_component_models_or_voices" in src
    assert "self.open_speech_models()" in src  # STT engines -> Manage Speech Models
    assert "self.choose_read_aloud_configuration()" in src  # voice engines -> Manage Voices


def test_test_button_toggles_to_stop_for_voice_rows() -> None:
    src = _src("optional_components_dialog.py")
    assert '"&Stop"' in src
    assert "controller.stop_test(" in src
    assert "controller.is_previewable(" in src


def test_controller_protocol_supports_preview_state() -> None:
    src = _src("optional_components_dialog.py")
    assert "def stop_test(self, component_id: str) -> None:" in src
    assert "def is_previewable(self, component_id: str) -> bool:" in src


def test_test_button_stays_enabled_across_a_selection_change_mid_preview() -> None:
    """Regression (voice-preview-feedback final review): a running preview must
    not strand the user with a disabled-but-labeled-Stop button just because
    they navigated to a not-yet-downloaded row. Enable() has to key off
    ``testing["active"]`` in addition to the newly-selected row's readiness --
    keying off ``ready`` alone (the pre-fix expression) meant Stop went
    unreachable the moment focus moved to a not-ready row."""
    src = _src("optional_components_dialog.py")
    assert 'test_btn.Enable(ready or testing["active"])' in src
