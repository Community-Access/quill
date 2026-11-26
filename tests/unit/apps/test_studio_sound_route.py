"""Where Is the Sound? and Recording status in QUILL Studio (FUX-03)."""

from __future__ import annotations

from types import SimpleNamespace

from quill.apps import studio_sound_route
from quill.apps.studio_sound_route import compose
from quill.core.demo_recording import SoundSource
from quill.platform.windows.screen_recorder import _spoken_source

RENDER = [("{0.0.0.00000000}.{1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d}", "Speakers (Realtek)", True)]
CAPTURE = [("{0.0.1.00000000}.{aaaa}", "Microphone (USB Audio)", True)]


class _Host:
    def __init__(self, prefs=None, **extra) -> None:
        self._prefs = prefs or {}
        self.said: list[str] = []
        for key, value in extra.items():
            setattr(self, key, value)

    def _demo_preferences(self):
        return self._prefs

    def _announce(self, text: str) -> None:
        self.said.append(text)


def _lister(flow_devices):
    return lambda: flow_devices


def test_idle_studio_names_its_playback_device_and_recording_microphone(monkeypatch) -> None:
    monkeypatch.setattr(studio_sound_route.sound_route, "_render_lister", _lister(RENDER))
    monkeypatch.setattr(studio_sound_route.sound_route, "_capture_lister", _lister(CAPTURE))
    host = _Host({"sources": [{"kind": "microphone", "device": "Microphone (USB Audio)"}]})
    answer = compose(host, app_output=lambda _pid: "", holder=lambda: None)
    assert answer == (
        "No demonstration is recording. "
        "Recordings use Microphone (USB Audio). "
        "Studio's players and previews play on Speakers (Realtek), the system default."
    )


def test_a_saved_microphone_windows_does_not_list_is_said_to_be_missing(monkeypatch) -> None:
    monkeypatch.setattr(studio_sound_route.sound_route, "_render_lister", _lister(RENDER))
    monkeypatch.setattr(studio_sound_route.sound_route, "_capture_lister", _lister(CAPTURE))
    host = _Host({"sources": [{"kind": "microphone", "device": "Podcast Mic"}]})
    answer = compose(host, app_output=lambda _pid: "", holder=lambda: None)
    assert "Recordings use Podcast Mic, not connected." in answer


def test_another_app_on_the_microphone_and_a_recording_in_progress(monkeypatch) -> None:
    monkeypatch.setattr(studio_sound_route.sound_route, "_render_lister", _lister(RENDER))
    recorder = SimpleNamespace(
        sound_line=lambda: "Recording, 0:05; sound: Microphone (USB).",
        status_line=lambda: "Recording, 0:05; sound: Microphone (USB); 0 dropped frames.",
    )
    host = _Host(_demo=recorder)
    answer = compose(host, app_output=lambda _pid: "", holder=lambda: "transcribe")
    assert answer.startswith("Recording, 0:05; sound: Microphone (USB).")  # first, route only
    assert "dropped frames" not in answer
    assert answer.endswith("QUILL Transcribe is listening on the microphone.")
    assert "Recordings use" not in answer  # the recording already says it


def test_windows_moving_studio_to_another_card_is_what_is_said(monkeypatch) -> None:
    headset = "{0.0.0.00000000}.{0f3c7a1e-1111-4222-8333-944455556666}"
    devices = [*RENDER, (headset, "Headphones (USB)", False)]
    monkeypatch.setattr(studio_sound_route.sound_route, "_render_lister", _lister(devices))
    answer = compose(_Host(), app_output=lambda _pid: headset, holder=lambda: None)
    assert answer.endswith("Studio's players and previews play on Headphones (USB).")


def test_where_is_sound_is_said_once(monkeypatch) -> None:
    monkeypatch.setattr(studio_sound_route, "compose", lambda _host: "the answer")
    host = _Host()
    studio_sound_route.StudioSoundRouteMixin.where_is_sound(host)
    assert host.said == ["the answer"]


def _source(label, kind, *, name="", lost=False):
    return SimpleNamespace(
        label=label,
        source=SimpleNamespace(kind=kind),
        device_name=lambda: name,
        is_lost=lambda: lost,
    )


def test_recording_status_names_the_device_behind_each_source() -> None:
    assert _spoken_source(_source("Microphone", "microphone", name="USB Mic")) == (
        "Microphone, USB Mic"
    )
    # A Windows name that already starts with the label is said once.
    assert _spoken_source(_source("Microphone", "microphone", name="Microphone (Realtek)")) == (
        "Microphone (Realtek)"
    )
    assert _spoken_source(_source("System sound", "system")) == "System sound"


def test_a_lost_source_comes_first_and_the_rest_are_joined_with_and() -> None:
    from quill.platform.windows.screen_recorder import DemoRecorder

    recorder = SimpleNamespace(
        state="recording",
        mic_muted=False,
        sources=[
            _source("Microphone", "microphone", name="USB Mic", lost=True),
            _source("System sound", "system"),
            _source("Sound card", "device", name="Line Out"),
        ],
        plan=SimpleNamespace(source=lambda _kind: None),
        elapsed=lambda: 65.0,
    )
    recorder.sound_parts = lambda: DemoRecorder.sound_parts(recorder)
    line = DemoRecorder.sound_line(recorder)
    assert line.startswith("Microphone, USB Mic disconnected, recording silence; Recording, ")
    assert "sound: System sound and Sound card, Line Out; screen reader out." in line


def test_sources_report_their_device_and_a_lost_sound_card(monkeypatch) -> None:
    from quill.platform.windows import demo_audio
    from quill.platform.windows.demo_microphone import MicrophoneSource

    monkeypatch.setattr(demo_audio, "_render_device_name", lambda _id: "Line Out (USB)")
    card = demo_audio.LoopbackSource(
        SoundSource("device", "Sound card", "card", device="{id}"),
        lambda *_a: None,
        studio_pid=1,
    )
    assert card.device_name() == "Line Out (USB)"
    assert not card.is_lost()
    card._lost = True
    assert card.is_lost()
    system = demo_audio.LoopbackSource(
        SoundSource("system", "System sound", "system"), lambda *_a: None, studio_pid=1
    )
    assert system.device_name() == ""
    mic = MicrophoneSource(
        SoundSource("microphone", "Microphone", "mic", device="Saved Mic"), lambda *_a: None
    )
    assert mic.device_name() == "Saved Mic"
    mic.device = SimpleNamespace(name="Microphone (USB Audio)")
    assert mic.device_name() == "Microphone (USB Audio)"


def test_the_studio_command_has_the_family_key() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.ui.audio.sound_route import DEFAULT_KEY

    assert APP_KEYMAPS["studio"]["studio.where_is_sound"] == DEFAULT_KEY
