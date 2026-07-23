"""Per-app feature areas: default-on semantics, per-app keying so sibling apps
do not collide, and atomic persistence."""

from __future__ import annotations

from quill.core.app_features import (
    AppArea,
    AppFeatureSettings,
    load_app_features,
    save_app_features,
)


def test_unknown_area_defaults_enabled() -> None:
    s = AppFeatureSettings(app_id="radio")
    assert s.is_enabled("weather") is True  # nothing disabled -> everything on
    assert s.is_enabled("anything-new") is True


def test_set_and_clear() -> None:
    s = AppFeatureSettings(app_id="radio")
    s.set_enabled("weather", False)
    assert s.is_enabled("weather") is False
    s.set_enabled("weather", True)
    assert s.is_enabled("weather") is True


def test_round_trip(tmp_path) -> None:
    s = load_app_features(tmp_path, "radio")
    assert s.is_enabled("weather") is True  # absent file -> all on
    s.set_enabled("weather", False)
    save_app_features(tmp_path, s)
    reloaded = load_app_features(tmp_path, "radio")
    assert reloaded.is_enabled("weather") is False
    assert reloaded.is_enabled("recording") is True


def test_apps_do_not_collide(tmp_path) -> None:
    radio = load_app_features(tmp_path, "radio")
    radio.set_enabled("weather", False)
    save_app_features(tmp_path, radio)
    # A different app in the same data dir is unaffected.
    cast = load_app_features(tmp_path, "cast")
    assert cast.is_enabled("weather") is True
    cast.set_enabled("podcasts", False)
    save_app_features(tmp_path, cast)
    # And saving cast did not resurrect radio's weather.
    assert load_app_features(tmp_path, "radio").is_enabled("weather") is False


def test_area_is_a_simple_value() -> None:
    area = AppArea("weather", "Weather", "The Weather menu.")
    assert (area.id, area.label) == ("weather", "Weather")
