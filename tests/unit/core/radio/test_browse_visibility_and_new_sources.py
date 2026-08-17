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


def test_youtube_offers_an_add_action(monkeypatch, tmp_path) -> None:
    from quill.core.radio import youtube_channels as yt

    real = yt.ChannelStore  # capture first: patching the name would recurse
    monkeypatch.setattr(yt, "ChannelStore", lambda *a, **k: real(tmp_path))
    nodes = bs.browse("youtube")
    assert nodes[-1].is_action and nodes[-1].label == "Add a Channel..."


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
    assert "By City" in labels and "By Owner" in labels
    assert "On the Dial" in labels


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
