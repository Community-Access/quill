"""Feature-gated media bootstrapping for minimal QUILL profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.main_frame_profile_picker import ProfilePickerMixin
from quill.ui.main_frame_radio import RadioMixin


class _Features:
    def __init__(self) -> None:
        self.enabled = {"core.radio": False, "core.podcasts": False}

    def is_enabled(self, feature_id: str) -> bool:
        return self.enabled[feature_id]

    def set_feature_enabled(self, feature_id: str, enabled: bool) -> list[str]:
        changed = self.enabled[feature_id] != enabled
        self.enabled[feature_id] = enabled
        return [feature_id] if changed else []


class _ProfileHost(ProfilePickerMixin):
    def __init__(self) -> None:
        self.features = _Features()
        self.menu_rebuilds = 0
        self.accelerator_rebuilds = 0

    def _feature_enabled(self, feature_id: str) -> bool:
        return self.features.is_enabled(feature_id)

    def _init_radio(self) -> None:
        RadioMixin._init_radio(self)

    def _init_podcasts(self, *, defer_library_load: bool = False) -> None:
        PodcastsMixin._init_podcasts(self, defer_library_load=defer_library_load)

    def _build_menu(self) -> None:
        self.menu_rebuilds += 1

    def _apply_accelerators(self) -> None:
        self.accelerator_rebuilds += 1


def test_customize_features_toggle_uses_the_profile_runtime_path() -> None:
    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    start = source.index("def open_individual_feature_toggles")
    body = source[start : start + 8_000]
    assert "affected = self._set_profile_feature_enabled(feature_id, enabled)" in body
    menu_source = Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8")
    build = menu_source.index("def _build_menu")
    assert "_ensure_profile_feature_runtime" in menu_source[build : build + 160]


def test_live_feature_toggle_initializes_each_runtime_once(monkeypatch) -> None:
    from quill.ui.podcasts import startup_bootstrap as podcast_bootstrap
    from quill.ui.radio import startup_bootstrap as radio_bootstrap

    radio_builds: list[object] = []
    podcast_builds: list[object] = []

    def build_radio(host: Any) -> None:
        radio_builds.append(host)
        host._radio_controller = object()
        host._radio_recorder = object()
        host._radio_scheduler = object()
        host._radio_wake_watcher = object()
        host._radio_last_seen_timer = object()

    def build_podcasts(host: Any, *, defer_library_load: bool) -> None:
        assert defer_library_load is False
        podcast_builds.append(host)
        host._podcast_library = object()
        host._podcast_history = object()
        host._podcast_controller = object()
        host._podcast_check_monitor = object()
        host._podcast_download_queue = object()
        host._podcast_cache_queue = object()

    monkeypatch.setattr(radio_bootstrap, "_build_radio", build_radio)
    monkeypatch.setattr(podcast_bootstrap, "_build_podcasts", build_podcasts)

    host = _ProfileHost()
    host._ensure_profile_feature_runtime()
    assert radio_builds == [] and podcast_builds == []
    assert host._radio_controller is None and host._podcast_controller is None

    host._set_profile_feature_enabled("core.radio", True)
    host._set_profile_feature_enabled("core.podcasts", True)
    radio_controller = host._radio_controller
    podcast_controller = host._podcast_controller

    host._ensure_profile_feature_runtime()
    host._ensure_profile_feature_runtime()

    assert radio_builds == [host]
    assert podcast_builds == [host]
    assert host._radio_controller is radio_controller
    assert host._podcast_controller is podcast_controller
    assert host.menu_rebuilds == host.accelerator_rebuilds == 2


def test_disabling_then_reenabling_preserves_live_references(monkeypatch) -> None:
    from quill.ui.podcasts import startup_bootstrap as podcast_bootstrap
    from quill.ui.radio import startup_bootstrap as radio_bootstrap

    radio_builds = []
    podcast_builds = []

    def build_radio(host: Any) -> None:
        radio_builds.append(host)
        host._radio_controller = object()
        host._radio_recorder = object()
        host._radio_scheduler = object()
        host._radio_wake_watcher = object()
        host._radio_last_seen_timer = object()

    def build_podcasts(host: Any, *, defer_library_load: bool) -> None:
        del defer_library_load
        podcast_builds.append(host)
        host._podcast_controller = object()
        host._podcast_library = object()
        host._podcast_history = object()
        host._podcast_check_monitor = object()
        host._podcast_download_queue = object()
        host._podcast_cache_queue = object()

    monkeypatch.setattr(radio_bootstrap, "_build_radio", build_radio)
    monkeypatch.setattr(podcast_bootstrap, "_build_podcasts", build_podcasts)

    host = _ProfileHost()
    host._ensure_profile_feature_runtime()
    host.features.enabled.update({"core.radio": True, "core.podcasts": True})
    host._refresh_profile_feature_runtime()
    radio_controller = host._radio_controller
    radio_scheduler = host._radio_scheduler
    radio_timer = host._radio_last_seen_timer
    podcast_controller = host._podcast_controller
    podcast_library = host._podcast_library
    podcast_monitor = host._podcast_check_monitor

    host._set_profile_feature_enabled("core.radio", False)
    host._set_profile_feature_enabled("core.podcasts", False)
    assert host._radio_controller is radio_controller
    assert host._radio_scheduler is radio_scheduler
    assert host._radio_last_seen_timer is radio_timer
    assert host._podcast_controller is podcast_controller
    assert host._podcast_library is podcast_library
    assert host._podcast_check_monitor is podcast_monitor

    host._set_profile_feature_enabled("core.radio", True)
    host._set_profile_feature_enabled("core.podcasts", True)
    assert host._radio_controller is radio_controller
    assert host._radio_scheduler is radio_scheduler
    assert host._radio_last_seen_timer is radio_timer
    assert host._podcast_controller is podcast_controller
    assert host._podcast_library is podcast_library
    assert host._podcast_check_monitor is podcast_monitor
    assert radio_builds == [host]
    assert podcast_builds == [host]


def test_passive_shutdown_and_status_probes_are_safe() -> None:
    host = _ProfileHost()
    host._ensure_profile_feature_runtime()
    host._clear_radio_recording_marker = lambda: (_ for _ in ()).throw(
        AssertionError("passive radio must not touch disk")
    )
    host._stamp_radio_last_seen = lambda: (_ for _ in ()).throw(
        AssertionError("passive radio must not persist history")
    )
    host._shutdown_podcast_transfers = lambda: (_ for _ in ()).throw(
        AssertionError("passive podcasts must not shut down missing queues")
    )

    RadioMixin._shutdown_radio(host)
    PodcastsMixin._shutdown_podcasts(host)

    assert RadioMixin._radio_status_text(host) == ""
    assert RadioMixin._radio_title_announce_command_title(host).endswith("(currently Off)")
    assert PodcastsMixin._podcast_status_text(host) == ""
