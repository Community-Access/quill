"""Per-branch visibility, and the last four browse sources."""

from __future__ import annotations

from quill.core.radio import browse_sources as bs
from quill.core.radio import browse_visibility as bv
from quill.core.radio.browse_nodes import make_id
from quill.core.radio.models import RadioStation


def _station(name="Test FM", url="https://a.example/s"):
    return RadioStation(name=name, stream_url=url)


# --- visibility ----------------------------------------------------------------


def test_never_set_means_the_defaults() -> None:
    assert bv.normalize(None) == bv.default_enabled()
    assert "popular" in bv.normalize(None)


def test_an_unknown_id_cannot_resurrect_itself() -> None:
    # A branch removed in a later release must not come back from a stored setting.
    assert "gone_forever" not in bv.normalize(["popular", "gone_forever"])


def test_normalize_returns_tree_order_not_stored_order() -> None:
    # So the settings list and the tree cannot disagree about ordering.
    stored = ["ccmixter", "favorites", "popular"]
    assert bv.normalize(stored) == ("favorites", "popular", "ccmixter")


def test_toggle_turns_on_and_off() -> None:
    on = bv.normalize(None)
    off = bv.toggle(on, "popular")
    assert "popular" not in off
    assert "popular" in bv.toggle(off, "popular")


def test_every_root_source_has_a_visibility_entry() -> None:
    # The failure this prevents: a source added to the tree and not to the
    # settings list, which is then impossible to turn off.
    known = {s.id for s in bv.BROWSE_SOURCES}
    for node_id, _label in bs.ROOT_SOURCES:
        assert node_id in known, f"{node_id} has no visibility entry"


def test_every_visibility_entry_is_a_real_source() -> None:
    roots = {node_id for node_id, _label in bs.ROOT_SOURCES}
    for info in bv.BROWSE_SOURCES:
        assert info.id in roots, f"{info.id} is not a browse source"


def test_a_hidden_source_is_absent_from_the_tree_entirely() -> None:
    # Not a display filter: absent means never opened, so never contacted.
    visible = bs.visible_roots(bv.toggle(None, "ccmixter"))
    assert all(node_id != "ccmixter" for node_id, _label in visible)
    assert any(node_id == "popular" for node_id, _label in visible)


def test_wikidata_is_off_by_default_because_it_is_derived() -> None:
    assert "wikidata" not in bv.default_enabled()
    assert any(s.id == "wikidata" for s in bv.BROWSE_SOURCES)


def test_describe_selection_speaks_the_count() -> None:
    assert "All" in bv.describe_selection(bv.enable_all())
    assert "hidden" in bv.describe_selection(["popular"])
    assert "empty" in bv.describe_selection([])


def test_groups_cover_every_source_and_keep_order() -> None:
    grouped = bv.in_groups(None)
    assert [name for name, _rows in grouped] == [g for g in bv.GROUPS if g in dict(grouped)]
    assert sum(len(rows) for _name, rows in grouped) == len(bv.BROWSE_SOURCES)


# --- My Servers -----------------------------------------------------------------


def test_my_servers_offers_an_add_action_even_when_empty(monkeypatch, tmp_path) -> None:
    from quill.core.radio import my_servers

    real = my_servers.ServerStore  # capture first: patching the name would recurse
    monkeypatch.setattr(my_servers, "ServerStore", lambda *a, **k: real(tmp_path))
    nodes = bs.browse("myservers")
    assert nodes[-1].is_action and nodes[-1].label == "Add a Server..."


def test_a_server_lists_its_mounts_with_now_playing(monkeypatch) -> None:
    from quill.core.radio import my_servers

    monkeypatch.setattr(
        my_servers,
        "mounts",
        lambda root, **_kw: [RadioStation(name="Jazz", stream_url="http://x/j", tags=("A Song",))],
    )
    node = bs.browse(make_id("myservers", "http://ice.example:8000"))[0]
    assert node.label == "Jazz" and node.note == "A Song"


# --- YouTube channels ------------------------------------------------------------


def test_youtube_offers_an_add_action_per_kind(monkeypatch, tmp_path) -> None:
    from quill.core.radio import youtube_channels as yt
    from quill.core.radio import youtube_saved

    real = yt.ChannelStore  # capture first: patching the name would recurse
    monkeypatch.setattr(yt, "ChannelStore", lambda *a, **k: real(tmp_path))
    real_saved = youtube_saved.SavedStore
    monkeypatch.setattr(youtube_saved, "SavedStore", lambda *a, **k: real_saved(tmp_path))
    nodes = bs.browse("youtube")
    # One way in per link shape (QA: a pasted link had no obvious way in).
    assert [n.label for n in nodes if n.is_action] == [
        "Add a Channel...",
        "Add a Playlist...",
        "Add a Video...",
    ]


def test_youtube_lists_saved_playlists_and_videos(monkeypatch, tmp_path) -> None:
    from quill.core.radio import youtube_channels as yt
    from quill.core.radio import youtube_saved

    real = yt.ChannelStore
    monkeypatch.setattr(yt, "ChannelStore", lambda *a, **k: real(tmp_path))
    real_saved = youtube_saved.SavedStore
    monkeypatch.setattr(youtube_saved, "SavedStore", lambda *a, **k: real_saved(tmp_path))
    real_saved(tmp_path).add(youtube_saved.PLAYLIST, "https://www.youtube.com/playlist?list=PL1x")
    real_saved(tmp_path).add(youtube_saved.VIDEO, "https://youtu.be/dQw4w9WgXcQ")
    nodes = bs.browse("youtube")
    playlist = next(n for n in nodes if n.node_id.startswith("ytplaylist:"))
    assert playlist.is_folder
    video = next(n for n in nodes if n.node_id.startswith("ytvideo:"))
    assert video.station is not None and video.station.is_recording
    assert video.station.stream_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_a_described_video_reads_as_a_video_and_not_as_an_address(monkeypatch, tmp_path) -> None:
    """The row shows what YouTube says the video IS (reported 2026-08-23)."""
    from quill.core.radio import youtube_channels as yt
    from quill.core.radio import youtube_saved

    real = yt.ChannelStore
    monkeypatch.setattr(yt, "ChannelStore", lambda *a, **k: real(tmp_path))
    real_saved = youtube_saved.SavedStore
    monkeypatch.setattr(youtube_saved, "SavedStore", lambda *a, **k: real_saved(tmp_path))
    url = "https://www.youtube.com/watch?v=iG9CE55wbtY"
    store = real_saved(tmp_path)
    store.add(youtube_saved.VIDEO, url)
    store.describe(
        youtube_saved.SavedItem(
            kind=youtube_saved.VIDEO,
            url=url,
            name="Do schools kill creativity?",
            uploader="TED",
            duration_ms=1_203_000,
            description="Sir Ken Robinson makes an entertaining case...",
        )
    )

    video = next(n for n in bs.browse("youtube") if n.node_id.startswith("ytvideo:"))

    assert video.label == "Do schools kill creativity?"
    assert video.note == "TED, 20 minutes 3 seconds"
    # And the description reaches the details panel, which had only an address.
    assert video.station is not None
    assert "Sir Ken Robinson" in video.station.details_text


def test_a_channel_lists_uploads_then_its_playlists(monkeypatch) -> None:
    from quill.core.radio import youtube_channels as yt

    monkeypatch.setattr(yt, "playlists", lambda url, **_kw: [("Lectures", "https://y/pl?list=1")])
    nodes = bs.browse(make_id("youtubechannel", "https://www.youtube.com/@NASA"))
    assert [n.label for n in nodes] == ["Uploads", "Lectures"]


def test_videos_page_offers_more_when_there_is_another_page(monkeypatch) -> None:
    from quill.core.radio import youtube_channels as yt

    monkeypatch.setattr(yt, "videos", lambda url, page=1, **_kw: ([_station("A Video")], True))
    nodes = bs.browse(make_id("youtubevideos", "https://www.youtube.com/@NASA", "1"))
    assert [n.label for n in nodes] == ["A Video", "More..."]


def test_a_channel_url_is_normalised_from_what_people_paste() -> None:
    from quill.core.radio.youtube_channels import normalize_channel_url as n

    assert n("@NASA") == "https://www.youtube.com/@NASA"
    assert n("https://www.youtube.com/@NASA/videos") == "https://www.youtube.com/@NASA"
    assert n("youtube.com/channel/UC123") == "https://www.youtube.com/channel/UC123"
    # A video link names a video, not a channel; following it would follow a
    # channel the listener never chose.
    assert n("https://www.youtube.com/watch?v=abc") == ""
    assert n("") == ""


# --- Wikidata --------------------------------------------------------------------


def test_wikidata_offers_its_axes_including_the_dial() -> None:
    labels = [n.label for n in bs.browse("wikidata")]
    assert "By City" in labels and "By Format" in labels
    assert "On the Dial" in labels


def test_wikidata_offers_no_axis_radio_browser_cannot_answer() -> None:
    """By Owner counted fine and opened to nothing about three times in four.

    Ownership is not a field Radio Browser carries, so the folder could only be
    filled by matching call signs one at a time -- the same failure that took
    By Network out, arriving one level lower down (removed 2026-08-17).
    """
    from quill.core.radio import wikidata

    assert "owner" not in {key for key, _label, _prop in wikidata.AXES}
    assert "By Owner" not in [n.label for n in bs.browse("wikidata")]
    # A stale saved position under the retired axis opens empty rather than raising.
    assert bs.browse(make_id("wikidata", "owner", "iHeartMedia")) == []


def test_wikidata_rows_say_they_are_derived() -> None:
    assert all(n.note == "from Wikidata" for n in bs.browse("wikidata") if n.label != "On the Dial")


def test_the_dial_groups_by_band(monkeypatch) -> None:
    from quill.core.radio import wikidata

    monkeypatch.setattr(
        wikidata,
        "stations_for_axis",
        lambda axis, *a, **k: [
            wikidata.WikidataStation("KJZZ", "KJZZ", "Phoenix", 91.5),
            wikidata.WikidataStation("KBAQ", "KBAQ", "Phoenix", 89.5),
            wikidata.WikidataStation("KMLE", "KMLE", "Phoenix", 107.9),
        ],
    )
    bands = bs.browse("wikidatadial")
    assert [b.label for b in bands] == ["87 to 91 MHz", "91 to 95 MHz", "103 to 108 MHz"]
    # The number is what WIKIDATA knows, and opening the band drops any station
    # without a matching playable stream -- so it is stated as "known" in the
    # note rather than promised as a child count. A band that announced 13 and
    # opened to one row is the bug this wording replaced (2026-08-16).
    assert bands[0].child_count is None
    assert bands[0].note == "1 known; those with a stream can play"


def test_wikidata_matches_call_signs_conservatively(monkeypatch) -> None:
    from quill.core.radio import radio_browser, wikidata

    monkeypatch.setattr(
        radio_browser,
        "search_stations",
        lambda q, **_kw: [
            RadioStation(name="Radio KJZZLAND", stream_url="https://wrong/1"),
            RadioStation(name="KJZZ 91.5", stream_url="https://right/1"),
        ],
    )
    found = wikidata.playable([wikidata.WikidataStation("KJZZ", "KJZZ")])
    assert [s.stream_url for s in found] == ["https://right/1"], "a fragment match is not a match"


def test_a_place_folder_lists_what_can_actually_play(monkeypatch) -> None:
    # Arizona opened to nothing while KJZZ and forty-seven others were
    # playable (reported 2026-08-16). Wikidata's list is a capped, unordered
    # slice; Radio Browser's place lookup starts from the set that can play.
    from quill.core.radio import radio_browser, wikidata

    monkeypatch.setattr(
        wikidata,
        "stations_for_axis",
        lambda axis, *a, **k: [wikidata.WikidataStation("KAAA", "KAAA", "Arizona")],
    )
    # Wikidata's one station is not carried; the place lookup has real ones.
    monkeypatch.setattr(radio_browser, "search_stations", lambda *a, **k: [])
    monkeypatch.setattr(
        wikidata,
        "stations_in_place",
        lambda place, **k: [_station("KBAQ 89.5", "https://kbaq/1")] if place == "Arizona" else [],
    )
    rows = bs.browse(make_id("wikidata", "city", "Arizona"))
    assert [n.label for n in rows] == ["KBAQ 89.5"]


def test_a_place_folder_does_not_promise_wikidatas_number(monkeypatch) -> None:
    # It usually holds more than Wikidata knows, so a count would be wrong in
    # the other direction from the bug it replaced.
    from quill.core.radio import wikidata

    monkeypatch.setattr(
        wikidata,
        "stations_for_axis",
        lambda axis, *a, **k: [wikidata.WikidataStation("KAAA", "KAAA", "Arizona")],
    )
    folders = bs.browse(make_id("wikidata", "city"))
    assert folders[0].child_count is None
    assert folders[0].note == "stations for this place"


def test_a_place_row_is_never_listed_twice(monkeypatch) -> None:
    from quill.core.radio import radio_browser, wikidata

    same = _station("KBAQ 89.5", "https://kbaq/1")
    monkeypatch.setattr(
        wikidata,
        "stations_for_axis",
        lambda axis, *a, **k: [wikidata.WikidataStation("KBAQ", "KBAQ", "Arizona")],
    )
    monkeypatch.setattr(radio_browser, "search_stations", lambda *a, **k: [same])
    monkeypatch.setattr(wikidata, "stations_in_place", lambda place, **k: [same])
    assert len(bs.browse(make_id("wikidata", "city", "Arizona"))) == 1


def test_a_place_falls_back_to_a_name_search_when_the_state_field_misses() -> None:
    # Cities are not in Radio Browser's state field, so the second try matters.
    from quill.core.radio import radio_browser, wikidata

    calls: list[dict] = []

    def fake(query="", **kwargs):
        calls.append({"query": query, **kwargs})
        return [] if kwargs.get("state") else [_station("Flagstaff FM", "https://f/1")]

    original = radio_browser.search_stations
    radio_browser.search_stations = fake  # type: ignore[assignment]
    try:
        found = wikidata.stations_in_place("Flagstaff")
    finally:
        radio_browser.search_stations = original  # type: ignore[assignment]
    assert [s.name for s in found] == ["Flagstaff FM"]
    assert calls[0].get("state") == "Flagstaff" and calls[1]["query"] == "Flagstaff"


def test_an_unreachable_directory_empties_the_place_rather_than_raising() -> None:
    from quill.core.radio import radio_browser, wikidata

    def down(*_a, **_k):
        raise OSError("radio browser is down")

    original = radio_browser.search_stations
    radio_browser.search_stations = down  # type: ignore[assignment]
    try:
        assert wikidata.stations_in_place("Arizona") == []
    finally:
        radio_browser.search_stations = original  # type: ignore[assignment]


def test_no_axis_is_grouped_by_a_property_stations_do_not_carry() -> None:
    """The failure this prevents shipped twice, silently.

    "By Format" was grouped by P2360 ("intended public"), carried by *zero* US
    radio stations, and "By Network" by P449 ("original broadcaster"), carried
    by two. Both folders opened to nothing and nothing in the build noticed,
    because an axis with no groups is indistinguishable from an axis whose
    upstream is slow. These are the properties that were counted live against
    Wikidata on 2026-08-16 and found to be populated.
    """
    from quill.core.radio import wikidata

    populated = {"P131", "P127", "P415"}
    for _key, label, prop in wikidata.AXES:
        assert prop in populated, f"{label} groups by {prop}, which stations do not carry"


def test_the_grouping_property_is_required_by_the_query() -> None:
    # OPTIONAL is what let an axis return 400 stations and zero groups: the
    # capped slice simply had no value for the property being grouped by.
    from quill.core.radio import wikidata

    query = wikidata._query("P415", "Q30")
    assert "wdt:P415 ?group" in query
    assert "OPTIONAL { ?station wdt:P415" not in query.replace("{{", "{")


def test_changing_a_property_cannot_serve_the_old_cached_answer(monkeypatch) -> None:
    # Correcting By Format's property would otherwise leave every existing
    # install on the empty answer until the cache aged out.
    from quill.core.radio import directory_cache, wikidata

    keys: list[str] = []
    monkeypatch.setattr(
        directory_cache,
        "resolve",
        lambda key, produce, **kw: (keys.append(key), ([], 0))[1],
    )
    wikidata.stations_for_axis("format")
    assert any("P415" in key for key in keys), keys


def test_a_format_tag_is_asked_for_the_way_radio_browser_spells_it() -> None:
    # Tags are lower case and matched exactly: "Christian" finds nothing where
    # "christian" finds hundreds, and "Active rock" needs its last word.
    from quill.core.radio import radio_browser, wikidata

    asked: list[str] = []

    def fake(query="", *, tag="", **_kw):
        asked.append(tag)
        return [_station("Rock FM")] if tag == "rock" else []

    original = radio_browser.search_stations
    radio_browser.search_stations = fake  # type: ignore[assignment]
    try:
        found = wikidata.stations_with_format("Active rock")
    finally:
        radio_browser.search_stations = original  # type: ignore[assignment]
    assert [s.name for s in found] == ["Rock FM"]
    assert asked[0] == "active rock", "the whole name is tried first"
    assert "rock" in asked and all(t == t.lower() for t in asked)
