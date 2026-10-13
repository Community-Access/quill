"""Each app's side of Lineups: Radio plays through, Cast queues and hands over.

Radio's play-through is driven with a stand-in player, through the same
``track_end`` path a real item ending takes. Cast's adapter is driven with a
stand-in frame. The hand-off is checked end to end: Cast writes a request, the
open-request queue carries it, Radio's drain reads it and plays the rows.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.lineups import ops  # noqa: E402
from quill.core.lineups.fields import ItemFacts  # noqa: E402
from quill.core.lineups.handoff import ACTION, read_request, write_request  # noqa: E402
from quill.core.lineups.model import Lineup, Row  # noqa: E402
from quill.core.lineups.refs import KIND_PLACE, KIND_STATION, ItemRef, episode_ref  # noqa: E402
from quill.core.lineups.store import LineupStore  # noqa: E402
from quill.ui.radio import lineups_playback as playback  # noqa: E402
from quill.ui.radio.playback_state import RadioPlayerState  # noqa: E402


class _Player:
    def __init__(self) -> None:
        self.state = SimpleNamespace(state=RadioPlayerState.STOPPED, station=None)
        self.played: list[str] = []

    def play_station(self, station: Any) -> None:
        self.played.append(station.name)
        self.state = SimpleNamespace(state=RadioPlayerState.PLAYING, station=station)

    def _remember_resume_point(self) -> None:
        pass

    def _set_state(self, state: Any, message: str = "") -> None:
        self.state = SimpleNamespace(state=state, station=None)


class _RadioApp:
    def __init__(self) -> None:
        self._radio_controller = _Player()
        self._radio_history = SimpleNamespace()
        self.said: list[str] = []
        self.frame = None

    def _announce(self, text: str, *_a: object, **_k: object) -> None:
        self.said.append(text)


def _facts(key: str, *, live: bool = False, kind: str = KIND_STATION) -> ItemFacts:
    return ItemFacts(
        ref=ItemRef(kind, key),
        name=key.title(),
        live=live,
        payload={"name": key.title(), "stream_url": f"http://{key}", "is_recording": not live},
    )


def _lineup(*items: ItemFacts) -> Lineup:
    return Lineup(
        id="l1",
        name="Morning",
        rows=tuple(Row(ref=i.ref, name=i.name, held="added") for i in items),
    )


def test_radio_plays_through_skipping_places_noting_live_and_saying_the_end() -> None:
    from quill.ui.radio import track_end

    app = _RadioApp()
    items = [
        _facts("news", live=True),
        ItemFacts(ref=ItemRef(KIND_PLACE, "rbgenre:jazz"), name="Jazz"),
        _facts("talk"),
    ]
    lineup = _lineup(*items)
    said = playback.start(app, lineup, [i.ref for i in items], 0, items)
    assert app._radio_controller.played == ["News"]
    assert said == "Playing News. Live. Press Ctrl+Shift+Period for the next item."
    track_end.handle(app._radio_controller)  # the stream ended by itself
    assert app._radio_controller.played == ["News", "Talk"]
    assert app.said[-1] == "Skipped Jazz, a place to browse, not something to play. Playing Talk."
    track_end.handle(app._radio_controller)
    assert app.said[-1] == "End of Morning."
    assert playback.session_of(app._radio_controller) is None


def test_next_and_previous_step_within_the_lineup() -> None:
    app = _RadioApp()
    items = [_facts("one"), _facts("two")]
    lineup = _lineup(*items)
    playback.start(app, lineup, [i.ref for i in items], 0, items)
    assert playback.step(app, 1) == "Playing Two."
    assert playback.step(app, -1) == "Playing One."
    assert playback.step(app, -1) == "This is the first item."


def test_stop_after_this_item_ends_the_run_quietly() -> None:
    from quill.ui.radio import track_end

    app = _RadioApp()
    items = [_facts("one"), _facts("two")]
    playback.start(app, _lineup(*items), [i.ref for i in items], 0, items)
    assert playback.stop_after(app) == "Stops after this item."
    track_end.handle(app._radio_controller)
    assert app._radio_controller.played == ["One"]
    assert app._radio_controller.state.state == RadioPlayerState.STOPPED


# -- Cast ------------------------------------------------------------------------------


class _CastApp:
    def __init__(self, library: Any) -> None:
        self._podcast_library = library
        self.played: list[tuple[str, str]] = []
        self.launched: list[str] = []
        self.saved = 0
        self.frame = None

    def _play_specific_episode(self, show_id: str, guid: str) -> None:
        self.played.append((show_id, guid))

    def _save_podcast_library(self) -> None:
        self.saved += 1

    def _launch_sibling(self, key: str) -> None:
        self.launched.append(key)

    def _announce(self, *_a: object, **_k: object) -> None:
        pass


def _cast_library() -> Any:
    from quill.core.podcasts.models import PodcastShow, QueueItem
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary

    show = PodcastShow(
        id="daily",
        title="The Daily",
        episodes=[
            PodcastEpisode(guid="e1", title="Monday", audio_url="http://x/1"),
            PodcastEpisode(guid="e2", title="Tuesday", audio_url="http://x/2"),
        ],
    )
    return PodcastLibrary(shows=[show], queue=[QueueItem("daily", "e2")])


def test_cast_plays_an_episode_by_putting_the_rest_at_the_front_of_the_queue(
    quill_data_dir,
) -> None:
    from quill.ui.podcasts.lineups_host import CastLineupsHost

    library = _cast_library()
    app = _CastApp(library)
    refs = [episode_ref("daily", "e1"), ItemRef(KIND_STATION, "s"), episode_ref("daily", "e2")]
    said = CastLineupsHost(app).play(
        _lineup(*(ItemFacts(ref=r, name=r.key) for r in refs)), refs, 0, [None] * 3
    )
    assert app.played == [("daily", "e1")]
    assert [(q.show_id, q.episode_guid) for q in library.queue] == [
        ("daily", "e1"),
        ("daily", "e2"),
    ]
    assert "other 1 item play in Quill Radio" in said


def test_cast_hands_what_it_cannot_play_to_radio(quill_data_dir, monkeypatch) -> None:
    from quill.ui.podcasts.lineups_host import CastLineupsHost

    queued: list[tuple[Path, str, str]] = []
    monkeypatch.setattr(
        "quill.core.ipc.enqueue_open_request",
        lambda path, *, action, slot, **_k: queued.append((path, action, slot)),
    )
    app = _CastApp(_cast_library())
    refs = [ItemRef(KIND_STATION, "bbc")]
    said = CastLineupsHost(app).play(_lineup(_facts("bbc")), refs, 0, [None])
    assert said == "Sent to Quill Radio to play."
    assert app.launched == ["radio"]
    path, action, slot = queued[0]
    assert (action, slot) == (ACTION, "radio")
    request = read_request(path)
    assert request is not None and request.tokens == ("station:bbc",)
    assert not Path(path).exists()  # consumed


def test_radio_plays_the_rows_cast_handed_over(quill_data_dir, monkeypatch) -> None:
    from quill.core.ipc import OpenRequest
    from quill.ui.radio import opened_files_ui

    store = LineupStore(quill_data_dir)
    _book, created = store.update(ops.create_lineup("Shared"))
    store.update(
        ops.add_items(
            created.lineup_id,
            [_facts("bbc")],
            payloads={ItemRef(KIND_STATION, "bbc"): _facts("bbc").payload},
        )
    )
    path = write_request(quill_data_dir, created.lineup_id, ["station:bbc"])
    app = _RadioApp()
    monkeypatch.setattr(
        "quill.ui.radio.lineups_host.RadioLineupsHost.data_dir",
        property(lambda self: quill_data_dir),
    )
    opened_files_ui.drain_requests(
        app, "radio", drain=lambda slot: [OpenRequest(path=path, action=ACTION)]
    )
    assert app._radio_controller.played == ["Bbc"]


def test_next_and_previous_never_end_the_run_at_either_end() -> None:
    app = _RadioApp()
    items = [_facts("one"), _facts("two")]
    playback.start(app, _lineup(*items), [i.ref for i in items], 1, items)
    assert playback.step(app, 1) == "This is the last item."
    assert playback.session_of(app._radio_controller) is not None  # still playing Two
    assert app._radio_controller.played == ["Two"]


def test_the_app_wide_next_key_steps_a_lineup_even_on_a_live_stream() -> None:
    from quill.ui.radio import bounded_playback_ui

    app = _RadioApp()
    app._radio_controller.is_seekable = lambda: False  # a live stream: no chapters, no seeking
    app._radio_controller.chapters = lambda: []
    items = [_facts("news", live=True), _facts("talk")]
    playback.start(app, _lineup(*items), [i.ref for i in items], 0, items)
    bounded_playback_ui.next_chapter(app)
    assert app._radio_controller.played == ["News", "Talk"]
    assert app.said[-1] == "Playing Talk."


def test_tuning_something_else_lets_go_of_the_lineup_for_the_next_key() -> None:
    from quill.core.radio.models import RadioStation
    from quill.ui.radio import bounded_playback_ui

    app = _RadioApp()
    app._radio_controller.is_seekable = lambda: False
    app._radio_controller.chapters = lambda: []
    items = [_facts("news", live=True), _facts("talk")]
    playback.start(app, _lineup(*items), [i.ref for i in items], 0, items)
    app._radio_controller.play_station(RadioStation(name="Other", stream_url="http://other"))
    bounded_playback_ui.next_chapter(app)  # the old lineup must not take over again
    assert app._radio_controller.played == ["News", "Other"]
