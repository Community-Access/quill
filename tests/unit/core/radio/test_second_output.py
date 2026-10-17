"""A second output device: background station and mirror (xradio2 4.6, 4.7).

The rules are pure; the player is driven against a fake engine and fake
choosers, so no sound device is touched and no dialog opens.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.radio import second_output as rule
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation

# -- the rules ------------------------------------------------------------------


def test_background_volume_scales_with_the_main_volume() -> None:
    assert rule.scaled_volume(40, 100) == 40
    assert rule.scaled_volume(40, 50) == 20
    assert rule.scaled_volume(40, 80, main_muted=True) == 0


def test_background_pauses_with_the_main_player_and_comes_back() -> None:
    step = rule.follow(rule.BACKGROUND, main_state="PAUSED", main_url="a", main_volume=100)
    assert step.pause and step.volume == 40
    step = rule.follow(
        rule.BACKGROUND, main_state="PLAYING", main_url="a", main_volume=100, paused=True
    )
    assert step.resume


def test_background_keeps_playing_through_stop_and_station_changes() -> None:
    for state in ("STOPPED", "ERROR", "CONNECTING"):
        step = rule.follow(rule.BACKGROUND, main_state=state, main_url="b", main_volume=100)
        assert not (step.close or step.pause or step.load)


def test_mirror_follows_station_pause_and_stop() -> None:
    step = rule.follow(rule.MIRROR, main_state="PLAYING", main_url="a", main_volume=70)
    assert step.load == "a" and step.volume == 70
    step = rule.follow(
        rule.MIRROR, main_state="PLAYING", main_url="b", main_volume=70, playing_url="a"
    )
    assert step.load == "b"
    step = rule.follow(
        rule.MIRROR, main_state="PAUSED", main_url="b", main_volume=70, playing_url="b"
    )
    assert step.pause
    step = rule.follow(
        rule.MIRROR, main_state="STOPPED", main_url="b", main_volume=70, playing_url="b"
    )
    assert step.close


# -- the player -----------------------------------------------------------------


class _Engine:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def set_audio_device(self, name: str) -> None:
        self.calls.append(("device", name))

    def set_volume(self, percent: int) -> None:
        self.calls.append(("volume", percent))

    def load(self, url: str) -> bool:
        self.calls.append(("load", url))
        return True

    def play(self) -> None:
        self.calls.append(("play",))

    def pause(self) -> None:
        self.calls.append(("pause",))

    def close(self) -> None:
        self.calls.append(("close",))


def _state(name: str, url: str = "", volume: int = 100):
    station = RadioStation(name="Main", stream_url=url) if url else None
    return SimpleNamespace(
        state=SimpleNamespace(name=name), station=station, volume_percent=volume, muted=False
    )


def _app(engine: _Engine, monkeypatch):
    from quill.ui.radio import second_output_ui

    monkeypatch.setattr(
        "quill.ui.audio.output_routing.list_output_devices",
        lambda: [("wasapi/main", "Speakers"), ("wasapi/phones", "Headphones")],
    )
    store = RadioFavoritesStore()
    store.add(RadioStation(name="Rain Sounds", stream_url="https://rain.test/"))
    said: list[str] = []
    app = SimpleNamespace(
        frame=None,
        _radio_favorites=store,
        _radio_history=SimpleNamespace(output_device="wasapi/main"),
        _radio_controller=SimpleNamespace(state=_state("PLAYING", "https://main.test/", 50)),
        _announce=said.append,
        _second_engine_factory=lambda _parent, _device: engine,
        said=said,
    )
    return app, second_output_ui


def test_a_background_station_plays_on_the_other_device(monkeypatch) -> None:
    engine = _Engine()
    app, ui = _app(engine, monkeypatch)
    answers = iter([0, 0, 2])  # the favourite, the only other device, 40 percent

    ui.toggle_background(app, choose=lambda _p, _labels: next(answers), ask_yes_no=lambda _q: True)

    assert ("device", "wasapi/phones") in engine.calls
    assert ("load", "https://rain.test/") in engine.calls
    assert ("volume", 20) in engine.calls, "40 percent of a main volume of 50"
    assert app.said[-1].startswith("Rain Sounds is playing in the background on Headphones.")
    ui.follow(app, _state("PAUSED", "https://main.test/", 50))
    assert engine.calls[-1] == ("pause",)
    ui.follow(app, _state("STOPPED"))
    assert engine.calls[-1] == ("play",), "pause follows; a stop does not"


def test_choosing_it_again_offers_to_turn_it_off(monkeypatch) -> None:
    engine = _Engine()
    app, ui = _app(engine, monkeypatch)
    answers = iter([0, 0, 2])
    ui.toggle_background(app, choose=lambda _p, _l: next(answers), ask_yes_no=lambda _q: True)
    asked: list[str] = []

    ui.toggle_background(app, choose=lambda _p, _l: 0, ask_yes_no=lambda q: asked.append(q) or True)

    assert asked == ["The background station Rain Sounds is playing on Headphones. Turn it off?"]
    assert engine.calls[-1] == ("close",)
    assert app.said[-1] == "The background station Rain Sounds turned off."


def test_mirroring_plays_what_the_main_player_plays(monkeypatch) -> None:
    engine = _Engine()
    app, ui = _app(engine, monkeypatch)

    ui.toggle_mirror(app, choose=lambda _p, _l: 0, ask_yes_no=lambda _q: True)

    assert ("load", "https://main.test/") in engine.calls
    assert app.said[-1] == "Mirroring to Headphones. It follows the main player."
    ui.follow(app, _state("PLAYING", "https://next.test/", 50))
    assert engine.calls[-1] == ("load", "https://next.test/")
    ui.follow(app, _state("STOPPED"))
    assert engine.calls[-1] == ("close",)


def test_no_other_device_says_so(monkeypatch) -> None:
    engine = _Engine()
    app, ui = _app(engine, monkeypatch)
    monkeypatch.setattr(
        "quill.ui.audio.output_routing.list_output_devices", lambda: [("wasapi/main", "Speakers")]
    )
    ui.toggle_mirror(app, choose=lambda _p, _l: 0, ask_yes_no=lambda _q: True)
    assert app.said[-1] == "There is no other output device to send it to."
    assert engine.calls == []


def test_without_a_second_player_following_does_nothing() -> None:
    from quill.ui.radio import second_output_ui

    second_output_ui.follow(SimpleNamespace(), _state("PLAYING", "https://x.test/"))
