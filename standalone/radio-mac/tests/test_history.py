"""Tests for quill_radio_mac.core.history.

Covers RadioHistory.record()'s dedup/most-recent-first/cap-at-15
behavior, the load_history/save_history atomic-JSON round trip, the
one-time eq_preset -> eq_bass_db/mid/treble_db migration, the "wx"
playback_engine normalization to "auto" (the mac build is mpv-only --
see history.py's docstring for why "wx" still loads instead of
rejecting old data), and close_action/playback_engine value validation.
No wx, no network.
"""

from __future__ import annotations

import json

from quill_radio_mac.core.history import RadioHistory, load_history, save_history
from quill_radio_mac.core.models import RadioStation


def _station(name="A", uuid="a"):
    return RadioStation(name=name, stream_url=f"https://example.com/{uuid}", station_uuid=uuid)


def test_record_moves_existing_station_to_front():
    history = RadioHistory()
    history.record(_station("A", "a"))
    history.record(_station("B", "b"))
    history.record(_station("A", "a"))
    assert [s.station_uuid for s in history.stations] == ["a", "b"]


def test_record_caps_at_fifteen_entries():
    history = RadioHistory()
    for i in range(20):
        history.record(_station(f"S{i}", f"u{i}"))
    assert len(history.stations) == 15
    # Most recently recorded stays first; oldest entries fall off the end.
    assert history.stations[0].station_uuid == "u19"
    assert history.stations[-1].station_uuid == "u5"


def test_last_station_property():
    history = RadioHistory()
    assert history.last_station is None
    history.record(_station("A", "a"))
    assert history.last_station.station_uuid == "a"


def test_defaults_match_upstream_values():
    history = RadioHistory()
    assert history.resume_on_launch is False
    assert history.announce_track_titles is False
    assert history.check_updates_on_startup is True
    assert history.last_update_check == ""
    assert (history.eq_bass_db, history.eq_mid_db, history.eq_treble_db) == (0.0, 0.0, 0.0)
    assert history.compressor_enabled is False
    assert history.close_action == "ask"
    assert history.announce_dialog_transitions is False
    assert history.now_playing_template == "{title}[ by {artist}]"
    assert history.recover_from_website is True
    assert history.output_device == ""
    assert history.playback_engine == "auto"
    assert history.volume_boost is False
    assert history.mono_enabled is False
    assert history.night_mode_enabled is False


def test_load_history_missing_file_returns_defaults(tmp_path):
    history = load_history(tmp_path)
    assert history.stations == []
    assert history.playback_engine == "auto"


def test_load_history_corrupt_file_returns_defaults(tmp_path):
    (tmp_path / "radio_history.json").write_text("not json", encoding="utf-8")
    history = load_history(tmp_path)
    assert history.stations == []


def test_save_and_load_history_round_trip(tmp_path):
    history = RadioHistory()
    history.record(_station("A", "a"))
    history.resume_on_launch = True
    history.eq_bass_db = 5.0
    history.eq_mid_db = -2.0
    history.eq_treble_db = 1.0
    history.compressor_enabled = True
    history.close_action = "minimize"
    history.playback_engine = "mpv"
    history.volume_boost = True
    history.mono_enabled = True
    history.night_mode_enabled = True
    history.output_device = "wasapi/{guid}"
    history.now_playing_template = "{raw}"

    save_history(tmp_path, history)
    reloaded = load_history(tmp_path)

    assert [s.station_uuid for s in reloaded.stations] == ["a"]
    assert reloaded.resume_on_launch is True
    assert (reloaded.eq_bass_db, reloaded.eq_mid_db, reloaded.eq_treble_db) == (5.0, -2.0, 1.0)
    assert reloaded.compressor_enabled is True
    assert reloaded.close_action == "minimize"
    assert reloaded.playback_engine == "mpv"
    assert reloaded.volume_boost is True
    assert reloaded.mono_enabled is True
    assert reloaded.night_mode_enabled is True
    assert reloaded.output_device == "wasapi/{guid}"
    assert reloaded.now_playing_template == "{raw}"


def test_eq_preset_migration_when_no_band_fields_present(tmp_path):
    path = tmp_path / "radio_history.json"
    path.write_text(json.dumps({"eq_preset": "Bass Boost"}), encoding="utf-8")
    history = load_history(tmp_path)
    assert (history.eq_bass_db, history.eq_mid_db, history.eq_treble_db) == (7.0, 0.0, 1.0)


def test_eq_preset_migration_unknown_preset_defaults_to_flat(tmp_path):
    path = tmp_path / "radio_history.json"
    path.write_text(json.dumps({"eq_preset": "Nonexistent"}), encoding="utf-8")
    history = load_history(tmp_path)
    assert (history.eq_bass_db, history.eq_mid_db, history.eq_treble_db) == (0.0, 0.0, 0.0)


def test_band_fields_take_priority_over_eq_preset(tmp_path):
    path = tmp_path / "radio_history.json"
    path.write_text(
        json.dumps({"eq_preset": "Bass Boost", "eq_bass_db": 2.0, "eq_mid_db": 0.0, "eq_treble_db": 0.0}),
        encoding="utf-8",
    )
    history = load_history(tmp_path)
    assert history.eq_bass_db == 2.0


def test_playback_engine_wx_normalizes_to_auto_on_load(tmp_path):
    path = tmp_path / "radio_history.json"
    path.write_text(json.dumps({"playback_engine": "wx"}), encoding="utf-8")
    history = load_history(tmp_path)
    assert history.playback_engine == "auto"


def test_playback_engine_invalid_value_normalizes_to_auto(tmp_path):
    path = tmp_path / "radio_history.json"
    path.write_text(json.dumps({"playback_engine": "bogus"}), encoding="utf-8")
    history = load_history(tmp_path)
    assert history.playback_engine == "auto"


def test_playback_engine_mpv_is_preserved(tmp_path):
    path = tmp_path / "radio_history.json"
    path.write_text(json.dumps({"playback_engine": "mpv"}), encoding="utf-8")
    history = load_history(tmp_path)
    assert history.playback_engine == "mpv"


def test_close_action_invalid_value_falls_back_to_ask(tmp_path):
    path = tmp_path / "radio_history.json"
    path.write_text(json.dumps({"close_action": "bogus"}), encoding="utf-8")
    history = load_history(tmp_path)
    assert history.close_action == "ask"


def test_now_playing_template_blank_falls_back_to_default(tmp_path):
    path = tmp_path / "radio_history.json"
    path.write_text(json.dumps({"now_playing_template": "   "}), encoding="utf-8")
    history = load_history(tmp_path)
    assert history.now_playing_template == "{title}[ by {artist}]"


def test_saved_json_keys_match_upstream_schema(tmp_path):
    # Byte-for-byte key parity with upstream quill.core.radio.history's
    # save_history, minus alt_f4_to_tray (deliberately dropped: no system
    # tray exists on macOS for it to control). A radio_history.json copied
    # from a Windows machine must load unchanged.
    save_history(tmp_path, RadioHistory())
    saved = json.loads((tmp_path / "radio_history.json").read_text(encoding="utf-8"))
    assert set(saved) == {
        "resume_on_launch",
        "announce_track_titles",
        "check_updates_on_startup",
        "last_update_check",
        "eq_bass_db",
        "eq_mid_db",
        "eq_treble_db",
        "compressor_enabled",
        "close_action",
        "announce_dialog_transitions",
        "now_playing_template",
        "recover_from_website",
        "output_device",
        "playback_engine",
        "volume_boost",
        "mono_enabled",
        "night_mode_enabled",
        "stations",
    }


def test_load_history_caps_stations_at_fifteen(tmp_path):
    path = tmp_path / "radio_history.json"
    stations = [_station(f"S{i}", f"u{i}").to_dict() for i in range(20)]
    path.write_text(json.dumps({"stations": stations}), encoding="utf-8")
    history = load_history(tmp_path)
    assert len(history.stations) == 15
