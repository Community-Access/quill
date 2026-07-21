"""Tests for the recently-played radio history store."""

from __future__ import annotations

from pathlib import Path

from quill.core.radio.history import RadioHistory, load_history, save_history
from quill.core.radio.models import RadioStation


def _station(name: str, uuid: str = "") -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://{name}.example.com", station_uuid=uuid)


def test_record_moves_repeat_plays_to_the_front_without_duplicates() -> None:
    history = RadioHistory()
    a, b = _station("a", "u-a"), _station("b", "u-b")
    history.record(a)
    history.record(b)
    history.record(a)
    assert [s.name for s in history.stations] == ["a", "b"]
    assert history.last_station is not None and history.last_station.name == "a"


def test_history_is_capped() -> None:
    history = RadioHistory()
    for i in range(30):
        history.record(_station(f"s{i}", f"u{i}"))
    assert len(history.stations) == 15
    assert history.stations[0].name == "s29"


def test_round_trip_and_missing_file(tmp_path: Path) -> None:
    assert load_history(tmp_path).stations == []
    history = RadioHistory(resume_on_launch=True)
    history.record(_station("keep", "u-k"))
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.resume_on_launch is True
    assert loaded.last_station is not None and loaded.last_station.name == "keep"


def test_corrupt_file_reads_empty(tmp_path: Path) -> None:
    (tmp_path / "radio_history.json").write_text("nope", encoding="utf-8")
    history = load_history(tmp_path)
    assert history.stations == [] and history.resume_on_launch is False


def test_check_updates_on_startup_defaults_on() -> None:
    assert RadioHistory().check_updates_on_startup is True


def test_check_updates_on_startup_round_trips(tmp_path: Path) -> None:
    history = RadioHistory(check_updates_on_startup=False, last_update_check="2026-07-16T00:00:00")
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.check_updates_on_startup is False
    assert loaded.last_update_check == "2026-07-16T00:00:00"


def test_log_dir_round_trips_and_defaults_empty(tmp_path: Path) -> None:
    # quill-radio #5: the settable log-folder preference.
    assert load_history(tmp_path).log_dir == ""
    save_history(tmp_path, RadioHistory(log_dir="D:/radio-logs"))
    assert load_history(tmp_path).log_dir == "D:/radio-logs"


def test_last_seen_round_trips_and_defaults_empty(tmp_path: Path) -> None:
    # quill-radio #4: the "last running" stamp for the missed-recording report.
    assert load_history(tmp_path).last_seen == ""
    save_history(tmp_path, RadioHistory(last_seen="2026-07-17T10:00:00"))
    assert load_history(tmp_path).last_seen == "2026-07-17T10:00:00"


def test_debug_mode_round_trips_and_defaults_off(tmp_path: Path) -> None:
    # quill-radio #5: the verbose-logging preference persists; absent = off.
    assert load_history(tmp_path).debug_mode is False
    save_history(tmp_path, RadioHistory(debug_mode=True))
    assert load_history(tmp_path).debug_mode is True
    (tmp_path / "radio_history.json").write_text(
        '{"resume_on_launch": true, "stations": []}', encoding="utf-8"
    )
    assert load_history(tmp_path).debug_mode is False


def test_check_updates_on_startup_missing_from_file_defaults_on(tmp_path: Path) -> None:
    (tmp_path / "radio_history.json").write_text(
        '{"resume_on_launch": true, "stations": []}', encoding="utf-8"
    )
    loaded = load_history(tmp_path)
    assert loaded.check_updates_on_startup is True
    assert loaded.last_update_check == ""


def test_sound_enhancements_default_off() -> None:
    history = RadioHistory()
    assert (history.eq_bass_db, history.eq_mid_db, history.eq_treble_db) == (0.0, 0.0, 0.0)
    assert history.compressor_enabled is False


def test_sound_enhancements_round_trip(tmp_path: Path) -> None:
    history = RadioHistory(
        eq_bass_db=-4.0, eq_mid_db=3.0, eq_treble_db=0.0, compressor_enabled=True
    )
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert (loaded.eq_bass_db, loaded.eq_mid_db, loaded.eq_treble_db) == (-4.0, 3.0, 0.0)
    assert loaded.compressor_enabled is True


def test_sound_enhancements_missing_from_file_default_off(tmp_path: Path) -> None:
    (tmp_path / "radio_history.json").write_text(
        '{"resume_on_launch": true, "stations": []}', encoding="utf-8"
    )
    loaded = load_history(tmp_path)
    assert (loaded.eq_bass_db, loaded.eq_mid_db, loaded.eq_treble_db) == (0.0, 0.0, 0.0)
    assert loaded.compressor_enabled is False


def test_sound_enhancements_migrates_old_preset_field(tmp_path: Path) -> None:
    (tmp_path / "radio_history.json").write_text(
        '{"resume_on_launch": false, "stations": [], "eq_preset": "Bass Boost"}',
        encoding="utf-8",
    )
    loaded = load_history(tmp_path)
    assert (loaded.eq_bass_db, loaded.eq_mid_db, loaded.eq_treble_db) == (7.0, 0.0, 1.0)


def test_close_action_defaults_to_ask() -> None:
    assert RadioHistory().close_action == "ask"


def test_close_action_round_trips(tmp_path: Path) -> None:
    history = RadioHistory(close_action="minimize")
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.close_action == "minimize"


def test_close_action_rejects_unknown_value(tmp_path: Path) -> None:
    (tmp_path / "radio_history.json").write_text(
        '{"resume_on_launch": false, "stations": [], "close_action": "bogus"}',
        encoding="utf-8",
    )
    loaded = load_history(tmp_path)
    assert loaded.close_action == "ask"


def test_announce_dialog_transitions_defaults_off() -> None:
    assert RadioHistory().announce_dialog_transitions is False


def test_announce_dialog_transitions_round_trips(tmp_path: Path) -> None:
    history = RadioHistory(announce_dialog_transitions=True)
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.announce_dialog_transitions is True


def test_now_playing_template_round_trips(tmp_path: Path) -> None:
    history = RadioHistory(now_playing_template="{artist}: {title}")
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.now_playing_template == "{artist}: {title}"


def test_now_playing_template_defaults_when_absent(tmp_path: Path) -> None:
    # A file saved before this field existed (or with a blank value) loads the
    # clean default rather than an empty template.
    assert load_history(tmp_path).now_playing_template == "{title}[ by {artist}]"


def test_recover_from_website_round_trips(tmp_path: Path) -> None:
    save_history(tmp_path, RadioHistory(recover_from_website=False))
    assert load_history(tmp_path).recover_from_website is False
    save_history(tmp_path, RadioHistory(recover_from_website=True))
    assert load_history(tmp_path).recover_from_website is True


def test_recover_from_website_defaults_on(tmp_path: Path) -> None:
    assert load_history(tmp_path).recover_from_website is True


def test_output_device_round_trips(tmp_path: Path) -> None:
    save_history(tmp_path, RadioHistory(output_device="wasapi/{some-guid}"))
    assert load_history(tmp_path).output_device == "wasapi/{some-guid}"


def test_output_device_defaults_to_system_default(tmp_path: Path) -> None:
    # "" = system default = the wx.media engine, byte-for-byte today's path.
    assert load_history(tmp_path).output_device == ""


def test_alt_f4_to_tray_round_trips_and_defaults_off(tmp_path: Path) -> None:
    # Off by default: Alt+F4 keeps its Windows-wide meaning unless opted in.
    assert load_history(tmp_path).alt_f4_to_tray is False
    save_history(tmp_path, RadioHistory(alt_f4_to_tray=True))
    assert load_history(tmp_path).alt_f4_to_tray is True


def test_show_status_bar_defaults_on_and_round_trips(tmp_path: Path) -> None:
    # On by default: the arrow-navigable status bar is visible out of the box.
    assert load_history(tmp_path).show_status_bar is True
    save_history(tmp_path, RadioHistory(show_status_bar=False))
    assert load_history(tmp_path).show_status_bar is False


def test_ui_font_scale_defaults_round_trips_and_clamps(tmp_path: Path) -> None:
    import json

    assert load_history(tmp_path).ui_font_scale == 1.0  # normal out of the box
    save_history(tmp_path, RadioHistory(ui_font_scale=1.25))
    assert load_history(tmp_path).ui_font_scale == 1.25
    # An out-of-range or garbage value is clamped/coerced into [1.0, 2.0].
    (tmp_path / "radio_history.json").write_text(
        json.dumps({"ui_font_scale": 9.0}), encoding="utf-8"
    )
    assert load_history(tmp_path).ui_font_scale == 2.0
    (tmp_path / "radio_history.json").write_text(
        json.dumps({"ui_font_scale": "big"}), encoding="utf-8"
    )
    assert load_history(tmp_path).ui_font_scale == 1.0


def test_prevent_sleep_defaults_on_and_round_trips(tmp_path: Path) -> None:
    # On by default: playing radio should keep the machine awake unless opted out.
    assert load_history(tmp_path).prevent_sleep is True
    save_history(tmp_path, RadioHistory(prevent_sleep=False))
    assert load_history(tmp_path).prevent_sleep is False


def test_channel_mode_defaults_to_stereo_and_round_trips(tmp_path: Path) -> None:
    assert load_history(tmp_path).channel_mode == "stereo"
    for mode in ("mono", "left", "right", "stereo"):
        save_history(tmp_path, RadioHistory(channel_mode=mode))
        assert load_history(tmp_path).channel_mode == mode


def test_favorites_sort_defaults_az_round_trips_and_coerces_invalid(tmp_path: Path) -> None:
    import json

    assert load_history(tmp_path).favorites_sort == "az"  # alphabetized out of the box
    for order in ("az", "za", "manual"):
        save_history(tmp_path, RadioHistory(favorites_sort=order))
        assert load_history(tmp_path).favorites_sort == order
    (tmp_path / "radio_history.json").write_text(
        json.dumps({"favorites_sort": "bogus"}), encoding="utf-8"
    )
    assert load_history(tmp_path).favorites_sort == "az"


def test_folder_sort_orders_round_trip_and_drop_invalid(tmp_path: Path) -> None:
    import json

    save_history(tmp_path, RadioHistory(folder_sort_orders={"News": "za", "Music": "manual"}))
    assert load_history(tmp_path).folder_sort_orders == {"News": "za", "Music": "manual"}
    (tmp_path / "radio_history.json").write_text(
        json.dumps({"folder_sort_orders": {"News": "az", "Bad": "nope"}}), encoding="utf-8"
    )
    assert load_history(tmp_path).folder_sort_orders == {"News": "az"}  # invalid dropped


def test_channel_mode_migrates_legacy_mono_enabled(tmp_path: Path) -> None:
    # An older store had a mono_enabled bool; a true value migrates to "mono".
    import json

    (tmp_path / "radio_history.json").write_text(
        json.dumps({"mono_enabled": True}), encoding="utf-8"
    )
    assert load_history(tmp_path).channel_mode == "mono"
    (tmp_path / "radio_history.json").write_text(
        json.dumps({"mono_enabled": False}), encoding="utf-8"
    )
    assert load_history(tmp_path).channel_mode == "stereo"


def test_optilab_defaults_off_and_round_trips(tmp_path: Path) -> None:
    # Defaults: bypassed, mode off, input 0, adapt 0 (per product choice).
    fresh = RadioHistory()
    assert fresh.optilab_enabled is False
    assert fresh.optilab_mode == "off"
    assert fresh.optilab_input_db == 0.0
    assert fresh.optilab_auto_adapt == 0
    history = RadioHistory(
        optilab_enabled=True,
        optilab_mode="stream",
        optilab_input_db=4.5,
        optilab_auto_adapt=60,
    )
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.optilab_enabled is True
    assert loaded.optilab_mode == "stream"
    assert loaded.optilab_input_db == 4.5
    assert loaded.optilab_auto_adapt == 60


def test_optilab_coerces_invalid_values(tmp_path: Path) -> None:
    import json

    (tmp_path / "radio_history.json").write_text(
        json.dumps({
            "optilab_mode": "bogus",
            "optilab_input_db": "not-a-number",
            "optilab_auto_adapt": 500,
        }),
        encoding="utf-8",
    )
    loaded = load_history(tmp_path)
    assert loaded.optilab_mode == "off"  # unknown mode -> off
    assert loaded.optilab_input_db == 0.0  # unparseable -> 0
    assert loaded.optilab_auto_adapt == 100  # clamped into 0..100


def _write_history(tmp_path: Path, raw: dict) -> None:
    import json

    from quill.core.radio.history import _store_path

    _store_path(tmp_path).write_text(json.dumps(raw), encoding="utf-8")


def test_absent_favorites_sort_preserves_manual_order(tmp_path) -> None:
    """Regression for #1168 / #1178: a store written before 2.0.2 (no
    ``favorites_sort`` key) kept favorites in the user's hand-arranged order;
    it must load as "manual", not be silently re-sorted A-Z on upgrade."""
    _write_history(tmp_path, {"resume_on_launch": False})  # pre-feature store, no key
    assert load_history(tmp_path).favorites_sort == "manual"


def test_explicit_favorites_sort_is_honored(tmp_path) -> None:
    for value in ("az", "za", "manual"):
        _write_history(tmp_path, {"favorites_sort": value})
        assert load_history(tmp_path).favorites_sort == value
    # A garbage stored value falls back to the A-Z default, not manual.
    _write_history(tmp_path, {"favorites_sort": "bogus"})
    assert load_history(tmp_path).favorites_sort == "az"
