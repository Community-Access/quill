"""ear.md B1 and B2: a device file exactly as Earshot 1.2.3 writes one.

``fixtures/device-earshot-1.2.3.json`` follows Earshot's own encoder
(``ListeningPlacesFormat.encodedDeviceFile`` at S:/code/earshot 63dc641):
Apple's pretty printing with ``" : "`` separators, sorted keys, unescaped
slashes, whole-second ISO 8601 dates, durations of 0 when the feed gave none,
tombstones with no ``kind``, and **no ``device_label``** -- the shipping
service never passes one. The two hand-written fixtures beside it predate that
reading and both carry a label, which is exactly what a real Earshot file does
not. A capture from a phone is still welcome; this is the next best thing,
and it caught the missing label.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.sync import listening_places as lp
from quill.core.sync.places_interchange import sync_interchange

FIXTURE = Path(__file__).parent / "fixtures" / "device-earshot-1.2.3.json"


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    show = PodcastShow(id="ba", title="Blind Abilities", feed_url="https://example.com/ba.xml")
    show.episodes = [
        PodcastEpisode(
            guid="blindabilities-214", title="214", audio_url="https://example.com/ba214.mp3"
        ),
        PodcastEpisode(
            guid="blindabilities-213", title="213", audio_url="https://example.com/ba213.mp3"
        ),
        PodcastEpisode(
            guid="", title="Double Tap 90", audio_url="https://example.com/doubletap-90.mp3"
        ),
    ]
    library.shows.append(show)
    return library


def test_the_file_reads_and_names_its_app_when_it_names_no_device() -> None:
    device_file = lp.DeviceFile.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert device_file is not None
    assert device_file.device_label == ""
    assert len(device_file.records) == 4
    assert sum(1 for record in device_file.records if record.deleted) == 1
    assert lp.spoken_device(device_file) == "Earshot"


def test_a_labelled_device_is_called_by_its_label() -> None:
    labelled = lp.DeviceFile(device="1f4c8a2e", device_label="Jeff's iPhone", app="earshot/1.2.3")
    assert lp.spoken_device(labelled) == "Jeff's iPhone"


def test_places_from_earshot_land_and_say_where_they_came_from(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    devices = lp.devices_dir(remote)
    devices.mkdir(parents=True)
    shutil.copy(FIXTURE, devices / "4be0c2d9.json")
    library = _library()
    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="9b30d7f1",
        device_label="Studio PC",
        library=library,
        save_library=lambda _library: None,
    )
    assert report.applied == 3, report.problems
    by_title = {episode.title: episode for episode in library.shows[0].episodes}
    assert by_title["214"].position_ms == 2412000
    assert by_title["214"].last_played_on == "Earshot"
    assert by_title["213"].played and by_title["213"].position_ms == 0
    assert by_title["Double Tap 90"].position_ms == 61000


def test_a_place_decided_here_forgets_where_the_last_one_came_from() -> None:
    from quill.core.podcasts import position_sync

    episode = PodcastEpisode(guid="g", title="t", audio_url="a", last_played_on="Earshot")
    position_sync.remember_position(episode, 5000)
    assert episode.last_played_on == ""
    assert "last_played_on" not in episode.to_dict()
