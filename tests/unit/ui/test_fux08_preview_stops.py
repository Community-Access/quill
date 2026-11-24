"""FUX-08: a preview stops on a second press, on Escape and when its window
closes, and never becomes the saved value -- Weather's alert sound, the Speech
Hub's voices and the Audio Studio wizard's Preview voice."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")


def _weather_dialog(monkeypatch, tmp_path):
    from quill.core.weather.settings import WeatherSettings
    from quill.platform import alert_sound
    from quill.ui.weather.settings_dialog import WeatherSettingsDialog

    played: list[int] = []
    stopped: list[int] = []
    playing = {"now": False}

    def play(_path, repeat):
        played.append(repeat)
        playing["now"] = True
        return len(played)

    def stop(play_number=0):
        stopped.append(play_number)
        was, playing["now"] = playing["now"], False
        return was

    monkeypatch.setattr(alert_sound, "play_alert_sound", play)
    monkeypatch.setattr(alert_sound, "stop_alert_sound", stop)
    monkeypatch.setattr(alert_sound, "is_playing", lambda: playing["now"])
    said: list[str] = []
    dialog = WeatherSettingsDialog(
        None, settings=WeatherSettings(), data_dir=tmp_path, announce_cb=said.append
    )
    dialog.said = said
    dialog.playing = playing
    return dialog, played, stopped


def test_weather_play_again_stops_the_alert_sound(wx_session_app, monkeypatch, tmp_path) -> None:
    dialog, played, stopped = _weather_dialog(monkeypatch, tmp_path)
    try:
        dialog._preview_alert_sound()
        assert played == [dialog._alert_sound_repeat.GetValue()]
        dialog._preview_alert_sound()  # the second press stops it, repeats and all
        assert stopped == [1] and len(played) == 1
        assert dialog.said[-1] == "Alert sound stopped."
        dialog._preview_alert_sound()  # and a third plays again
        assert len(played) == 2
    finally:
        dialog.dialog.Destroy()


def test_weather_settings_guards_its_preview_when_shown(
    wx_session_app, monkeypatch, tmp_path
) -> None:
    import quill.ui.dialog_contract as contract
    import quill.ui.preview_guard as guard

    dialog, _played, _stopped = _weather_dialog(monkeypatch, tmp_path)
    guarded: list[object] = []
    monkeypatch.setattr(guard, "guard_preview", lambda _w, stop, *_a: guarded.append(stop))
    monkeypatch.setattr(contract, "show_modal_dialog", lambda *_a, **_kw: wx.ID_CANCEL)
    dialog.show()
    assert guarded and guarded[0] == dialog._stop_alert_preview


class _Browser:
    def __init__(self, playing: bool) -> None:
        self.playing = playing
        self._borrowed: object = {"read_aloud_volume": 1}  # what a preview took

    def end_preview(self, *, give_back: bool = False) -> bool:
        was, self.playing = self.playing, False
        return was

    def collect_result(self):
        assert self._borrowed is None, "collected before the hub took the values back"
        return "selection"


def test_speech_hub_gives_back_before_collecting_and_stops_either_tab() -> None:
    from quill.ui.speech_hub_dialog import TAB_SPEECH_OFFLINE, SpeechHubDialog

    offline, online = _Browser(playing=False), _Browser(playing=True)
    hub = SimpleNamespace(
        _voice_browser_offline=offline,
        _voice_browser_online=online,
        _ra_action=None,
        _dict_action=None,
        _wx=wx,
        _nb=SimpleNamespace(GetSelection=lambda: TAB_SPEECH_OFFLINE),
        _borrowed=[],
        dialog=SimpleNamespace(Destroy=lambda: None),
    )
    hub._end_previews = lambda **kw: SpeechHubDialog._end_previews(hub, **kw)
    assert hub._end_previews() is True  # Escape: the online preview was playing
    assert hub._end_previews() is False  # nothing left: Escape closes the hub
    import quill.ui.speech_hub_dialog as module

    original = module.focus_primary_control
    module.focus_primary_control = lambda _dialog: None
    try:
        result = SpeechHubDialog.show(hub, lambda *_a: wx.ID_OK)
    finally:
        module.focus_primary_control = original
    assert result == ("selection", None)
    assert offline._borrowed is None and online._borrowed is None


def test_audio_studio_wizard_stops_a_voice_preview(wx_session_app, monkeypatch) -> None:
    import quill.ui.audio_studio as studio
    import quill.ui.audio_studio.wizard as wizard
    import quill.ui.batch_speech_runner as runner
    import quill.ui.preview_guard as guard

    class _Wizard:
        def __init__(self, *_a, **_kw) -> None:
            self.destroyed = False

        def Destroy(self) -> None:  # noqa: N802 - wx's name
            self.destroyed = True

    guarded: list[object] = []
    monkeypatch.setattr(wizard, "AudioStudioWizard", _Wizard)
    monkeypatch.setattr(guard, "guard_preview", lambda _w, stop, *_a: guarded.append(stop))
    monkeypatch.setattr(runner, "_defaults", lambda _frame: None)
    monkeypatch.setattr(runner, "_engine_available", lambda _frame: {})
    stops: list[bool] = []
    frame = SimpleNamespace(
        frame=None,
        settings=SimpleNamespace(audio_studio_last_journey="documents"),
        _announce=lambda _m: None,
        _show_modal_dialog=lambda *_a: wx.ID_CANCEL,
        _stop_active_voice_preview=lambda: stops.append(True),
    )
    assert studio.show_audio_studio(frame) is None
    assert len(guarded) == 1
    assert guarded[0]() is False  # stops the voice; Escape still closes the wizard
    assert stops == [True]


def test_weather_play_never_cuts_off_a_real_alert(wx_session_app, monkeypatch, tmp_path) -> None:
    dialog, played, _stopped = _weather_dialog(monkeypatch, tmp_path)
    try:
        dialog.playing["now"] = True  # a real alert, not this window's preview
        dialog._preview_alert_sound()
        assert played == []
        assert dialog.said == ["An alert sound is playing. Try again when it ends."]
    finally:
        dialog.dialog.Destroy()


class _Settings:
    read_aloud_volume = 100
    read_aloud_rate = 0


def test_speech_hub_gives_back_the_first_saved_values_after_both_tabs_preview() -> None:
    """Both tabs share one settings object: what was saved before either tab
    previewed is what Cancel keeps, whatever order they previewed in."""
    from quill.ui import voice_browser_settings
    from quill.ui.speech_hub_dialog import SpeechHubDialog

    settings = _Settings()
    offline, online = _Browser(playing=False), _Browser(playing=False)
    hub = SimpleNamespace(
        _voice_browser_offline=offline,
        _voice_browser_online=online,
        _borrowed=[(settings, voice_browser_settings.borrow(settings))],
    )
    settings.read_aloud_volume = 50  # the Offline tab's preview
    offline._borrowed = voice_browser_settings.borrow(settings)
    settings.read_aloud_volume = 30  # then the Online tab's
    online._borrowed = voice_browser_settings.borrow(settings)
    SpeechHubDialog._end_previews(hub, give_back=True)
    assert settings.read_aloud_volume == 100


def test_voice_preview_for_plays_or_says_choose_a_voice() -> None:
    from quill.ui.audio_studio import voice_preview_for

    played: list[tuple] = []
    said: list[str] = []
    host = SimpleNamespace(_preview_voice=lambda engine, voice: played.append((engine, voice)))
    preview = voice_preview_for(host, said.append)
    preview("piper", "amy")
    preview("piper", "")
    assert played == [("piper", "amy")]
    assert said == ["Choose a voice to preview"]
