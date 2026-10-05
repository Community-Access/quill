"""Edit Station Tags...: save, cancel, unchanged, and the dialog's own shape."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.radio import station_tags as tags_mod
from quill.core.radio.favorites import RadioFavoritesStore, load_favorites
from quill.core.radio.models import RadioStation
from quill.ui.radio import station_tags_dialog

STATION = RadioStation(name="97.1 The Ticket", stream_url="http://s/wxyt", tags=("sports",))


def _host(favorites: RadioFavoritesStore | None = None) -> SimpleNamespace:
    said: list[str] = []
    return SimpleNamespace(frame=None, _announce=said.append, _radio_favorites=favorites, said=said)


def _asker(answer: str | None, seen: list[tuple[str, str, str]]):
    def ask(_parent, name, current, directory):
        seen.append((name, current, directory))
        return answer

    return ask


def test_save_on_a_non_favorite_writes_the_tag_map(tmp_path: Path) -> None:
    host = _host(RadioFavoritesStore())
    seen: list[tuple[str, str, str]] = []
    changed = station_tags_dialog.edit_station_tags(
        host, STATION, ask=_asker("Detroit Tigers, MLB", seen), data_dir=tmp_path
    )
    assert changed is True
    assert seen == [("97.1 The Ticket", "", "sports")]
    assert tags_mod.load_tag_store(tmp_path).tags_for(STATION) == ("Detroit Tigers", "MLB")
    assert host.said == ["Tags saved."]


def test_save_on_a_favorite_writes_the_favorites_file(tmp_path: Path) -> None:
    favorites = RadioFavoritesStore()
    favorites.add(STATION)
    host = _host(favorites)
    seen: list[tuple[str, str, str]] = []
    assert station_tags_dialog.edit_station_tags(
        host, STATION, ask=_asker("baseball", seen), data_dir=tmp_path
    )
    assert load_favorites(tmp_path).favorites[0].user_tags == ("baseball",)
    assert not (tmp_path / tags_mod.FILE_NAME).exists()
    # Opening it again shows what is there.
    station_tags_dialog.edit_station_tags(host, STATION, ask=_asker(None, seen), data_dir=tmp_path)
    assert seen[-1][1] == "baseball"


def test_cancel_changes_nothing(tmp_path: Path) -> None:
    host = _host(RadioFavoritesStore())
    assert not station_tags_dialog.edit_station_tags(
        host, STATION, ask=_asker(None, []), data_dir=tmp_path
    )
    assert not (tmp_path / tags_mod.FILE_NAME).exists()
    assert host.said == []


def test_unchanged_text_is_not_a_save_and_empty_removes(tmp_path: Path) -> None:
    host = _host(RadioFavoritesStore())
    station_tags_dialog.edit_station_tags(host, STATION, ask=_asker("a, b", []), data_dir=tmp_path)
    assert not station_tags_dialog.edit_station_tags(
        host, STATION, ask=_asker(" a ,b ", []), data_dir=tmp_path
    )
    assert station_tags_dialog.edit_station_tags(
        host, STATION, ask=_asker("", []), data_dir=tmp_path
    )
    assert tags_mod.load_tag_store(tmp_path).entries == {}
    assert host.said[-1] == "Tags removed."


def test_nothing_playing_says_so() -> None:
    host = _host()
    host._radio_controller = SimpleNamespace(state=SimpleNamespace(station=None))
    assert station_tags_dialog.edit_playing(host) is False
    assert host.said == ["Nothing is playing."]


def test_details_for_never_raises_and_includes_tags(quill_data_dir: Path) -> None:
    store = tags_mod.StationTagStore()
    store.set(STATION, ("Tigers",))
    tags_mod.save_tag_store(quill_data_dir, store)
    assert "Your tags: Tigers" in station_tags_dialog.details_for(_host(), STATION)
    assert station_tags_dialog.details_for(_host(), object(), "plain") == "plain"


def test_the_dialog_is_labelled_and_helped() -> None:
    wx = pytest.importorskip("wx")
    app = wx.App()
    try:
        seen: list[str] = []

        def _inspect(dialog, title):
            # Built and handed to the show path, never shown for real.
            seen.append(title)
            assert dialog.GetTitle() == station_tags_dialog.TITLE
            box = next(
                child
                for child in dialog.GetChildren()
                if isinstance(child, wx.TextCtrl) and child.IsEditable()
            )
            assert box.GetValue() == "MLB"
            assert box.GetName() == "Your tags, separated by commas"
            labels = [
                child.GetLabel()
                for child in dialog.GetChildren()
                if isinstance(child, wx.StaticText)
            ]
            assert "&Your tags, separated by commas:" in labels
            assert "&Directory tags (read-only):" in labels
            readonly = [
                child
                for child in dialog.GetChildren()
                if isinstance(child, wx.TextCtrl) and not child.IsEditable()
            ]
            assert readonly and readonly[0].GetValue() == "sports, talk"
            return wx.ID_CANCEL

        answer = station_tags_dialog.ask_tags(None, "WXYT", "MLB", "sports, talk", show=_inspect)
        assert seen == [station_tags_dialog.TITLE]
        assert answer is None  # cancelled
    finally:
        del app


def test_the_title_has_an_f1_purpose() -> None:
    from quill.core.radio import surface_help

    assert surface_help.is_known_title(station_tags_dialog.TITLE)


def test_row_menus_offer_it_on_live_stations_only() -> None:
    from quill.core.radio import row_actions

    live = row_actions.actions_for("rbgenre", station=STATION)
    assert row_actions.EDIT_TAGS in {a.id for a in live}
    episode = RadioStation(name="Ep", stream_url="http://e", is_recording=True)
    assert row_actions.EDIT_TAGS not in {
        a.id for a in row_actions.actions_for("rbgenre", station=episode)
    }


def test_search_lane_uses_the_catalog_and_prepends_to_search_all(
    monkeypatch: pytest.MonkeyPatch, quill_data_dir: Path
) -> None:
    from quill.core.radio import federated_browse, sports_flagships
    from quill.ui.radio import catalog_search, station_lookup_lane

    team = sports_flagships.Team(
        "Detroit Tigers",
        "MLB",
        "baseball",
        aliases=("Tigers",),
        stations=(sports_flagships.FlagshipStation("97.1 The Ticket", "WXYT-FM"),),
    )
    monkeypatch.setattr(sports_flagships, "load_teams", lambda path=None: (team,))
    wxyt = RadioStation(name="WXYT 97.1 The Ticket", stream_url="http://s/wxyt")
    monkeypatch.setattr(
        catalog_search, "catalog_search_rows", lambda _c, text, limit: [wxyt] if text else []
    )
    host = SimpleNamespace(_catalog=object(), _favorites=RadioFavoritesStore())
    rows = station_lookup_lane.lane_rows(host, "Tigers", safe_mode=True)
    assert [(r.name, r.match_reason) for r in rows] == [(wxyt.name, "carries the Detroit Tigers")]
    found = federated_browse.FederatedBrowse()
    station_lookup_lane.prepend_to_federated(host, "Tigers", found, safe_mode=True)
    assert found.rows[0].note == "Station, carries the Detroit Tigers"
    assert found.counts["Station"] == 1
