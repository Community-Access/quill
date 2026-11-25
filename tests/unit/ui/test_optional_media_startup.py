"""Feature-gated media bootstrapping and live profile transitions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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


class _Resource:
    def __init__(self) -> None:
        self.shutdowns = 0

    def shutdown(self) -> None:
        self.shutdowns += 1


class _Timer:
    def __init__(self) -> None:
        self.starts: list[int] = []
        self.stops = 0
        self.running = False

    def Start(self, milliseconds: int) -> None:  # noqa: N802 - wx shape
        self.starts.append(milliseconds)
        self.running = True

    def Stop(self) -> None:  # noqa: N802 - wx shape
        self.stops += 1
        self.running = False

    def IsRunning(self) -> bool:  # noqa: N802 - wx shape
        return self.running


class _Controller(_Resource):
    def __init__(self) -> None:
        super().__init__()
        self.state = SimpleNamespace()

    def play_station(self, _station: object) -> None:
        raise AssertionError("disabled Radio must not wake")


class _Monitor(_Resource):
    def __init__(self) -> None:
        super().__init__()
        self.applies = 0
        self.cancellations = 0
        self.stops = 0

    def apply(self) -> bool:
        self.applies += 1
        return True

    def cancel_all(self) -> list[str]:
        self.cancellations += 1
        return []

    def stop(self) -> None:
        self.stops += 1


class _Frame:
    @staticmethod
    def Bind(*_args: object) -> None:  # noqa: N802 - wx shape
        return None


class _ProfileHost(ProfilePickerMixin):
    def __init__(self) -> None:
        self.features = _Features()
        self.frame = _Frame()
        self._wx = SimpleNamespace()
        self._safe_mode = False
        self._podcast_library_loading = False
        self.menu_rebuilds = 0
        self.accelerator_rebuilds = 0
        self.startup_failures: list[str] = []
        self.automatic_calls: list[str] = []

    def _feature_enabled(self, feature_id: str) -> bool:
        attr = {
            "core.radio": "_radio_runtime_failed",
            "core.podcasts": "_podcast_runtime_failed",
        }.get(feature_id, "")
        failed = bool(attr and getattr(self, attr, False))
        return self.features.is_enabled(feature_id) and not failed

    def _init_radio(self) -> None:
        RadioMixin._init_radio(self)

    def _init_podcasts(self, *, defer_library_load: bool = False) -> None:
        PodcastsMixin._init_podcasts(self, defer_library_load=defer_library_load)

    def _build_menu(self) -> None:
        self.menu_rebuilds += 1

    def _apply_accelerators(self) -> None:
        self.accelerator_rebuilds += 1

    def _report_startup_task_failure(self, label: str) -> None:
        self.startup_failures.append(label)

    def _on_radio_scheduled_recording_fired(self, *_args: object) -> None:
        return None

    def _on_radio_scheduled_recording_busy(self, *_args: object) -> None:
        return None

    def _radio_recording_filter_graph(self) -> str:
        return ""

    def _on_radio_wake_up(self, *_args: object) -> None:
        return None

    def _radio_minute_tick(self) -> None:
        self.automatic_calls.append("radio minute")

    def _radio_track_titles_follow_playback(self, _state: object) -> None:
        self.automatic_calls.append("radio titles")

    def _report_missed_recordings(self) -> None:
        self.automatic_calls.append("missed recordings")

    def _reconcile_and_offer_radio_resume(self) -> None:
        self.automatic_calls.append("recording resume")

    def _refresh_radio_wake_task(self) -> None:
        self.automatic_calls.append("wake task")

    def podcast_run_maintenance(self, *, announce: bool) -> None:
        assert announce is False
        self.automatic_calls.append("podcast maintenance")


def _capture_deferred(monkeypatch: Any) -> list[tuple[str, Any, Any]]:
    from quill.ui import startup_launch

    captured: list[tuple[str, Any, Any]] = []

    def capture(
        _wx: object,
        tasks: tuple[tuple[str, Any], ...],
        *,
        on_failure: Any = None,
    ) -> None:
        captured.extend((label, task, on_failure) for label, task in tasks)

    monkeypatch.setattr(startup_launch, "defer_after_ssl_trust", capture)
    return captured


def _build_radio(host: Any) -> None:
    host._radio_controller = _Controller()
    host._radio_recorder = _Resource()
    host._radio_recording_settings = object()
    host._radio_scheduler = _Resource()
    host._radio_wake_watcher = _Resource()
    host._radio_last_seen_timer = _Timer()
    host._radio_title_timer = _Timer()


def _build_podcasts(host: Any, *, defer_library_load: bool) -> None:
    assert defer_library_load is False
    host._podcast_controller = _Controller()
    host._podcast_library = object()
    host._podcast_history = object()
    host._podcast_check_monitor = _Monitor()
    host._podcast_download_queue = _Resource()
    host._podcast_cache_queue = _Resource()


def test_customize_features_toggle_uses_the_profile_runtime_path() -> None:
    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    start = source.index("def open_individual_feature_toggles")
    body = source[start : start + 8_000]
    assert "affected = self._set_profile_feature_enabled(feature_id, enabled)" in body
    menu_source = Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8")
    build = menu_source.index("def _build_menu")
    assert "_ensure_profile_feature_runtime" in menu_source[build : build + 160]


def test_live_feature_toggle_initializes_each_runtime_once(monkeypatch: Any) -> None:
    from quill.ui.podcasts import startup_bootstrap as podcast_bootstrap
    from quill.ui.radio import startup_bootstrap as radio_bootstrap

    radio_builds: list[object] = []
    podcast_builds: list[object] = []
    queued = _capture_deferred(monkeypatch)

    def build_radio(host: Any) -> None:
        radio_builds.append(host)
        _build_radio(host)

    def build_podcasts(host: Any, *, defer_library_load: bool) -> None:
        podcast_builds.append(host)
        _build_podcasts(host, defer_library_load=defer_library_load)

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
    assert len(queued) == 2
    assert host.menu_rebuilds == host.accelerator_rebuilds == 2


def test_disabling_then_reenabling_pauses_only_automatic_work(monkeypatch: Any) -> None:
    from quill.core.radio import recording_schedule, wake_timer
    from quill.ui.podcasts import startup_bootstrap as podcast_bootstrap
    from quill.ui.radio import catalog_ui
    from quill.ui.radio import startup_bootstrap as radio_bootstrap

    queued = _capture_deferred(monkeypatch)
    radio_builds: list[object] = []
    podcast_builds: list[object] = []
    schedulers: list[_Resource] = []
    watchers: list[_Resource] = []

    def scheduler_factory(**_kwargs: object) -> _Resource:
        value = _Resource()
        schedulers.append(value)
        return value

    def watcher_factory(*_args: object, **_kwargs: object) -> _Resource:
        value = _Resource()
        watchers.append(value)
        return value

    def build_radio(host: Any) -> None:
        radio_builds.append(host)
        _build_radio(host)

    def build_podcasts(host: Any, *, defer_library_load: bool) -> None:
        podcast_builds.append(host)
        _build_podcasts(host, defer_library_load=defer_library_load)

    monkeypatch.setattr(recording_schedule, "RecordingScheduler", scheduler_factory)
    monkeypatch.setattr(wake_timer, "WakeUpWatcher", watcher_factory)
    monkeypatch.setattr(catalog_ui, "refresh_on_startup", lambda host: None)
    monkeypatch.setattr(radio_bootstrap, "_build_radio", build_radio)
    monkeypatch.setattr(podcast_bootstrap, "_build_podcasts", build_podcasts)

    host = _ProfileHost()
    host.features.enabled.update({"core.radio": True, "core.podcasts": True})
    host._refresh_profile_feature_runtime()
    radio_controller = host._radio_controller
    old_scheduler = host._radio_scheduler
    old_watcher = host._radio_wake_watcher
    radio_timer = host._radio_last_seen_timer
    podcast_controller = host._podcast_controller
    podcast_library = host._podcast_library
    podcast_monitor = host._podcast_check_monitor

    host._set_profile_feature_enabled("core.radio", False)
    host._set_profile_feature_enabled("core.podcasts", False)
    assert host._radio_controller is radio_controller
    assert host._radio_scheduler is None
    assert host._radio_wake_watcher is None
    assert host._radio_last_seen_timer is radio_timer
    assert old_scheduler.shutdowns == old_watcher.shutdowns == 1
    assert radio_timer.stops == 1
    assert host._podcast_controller is podcast_controller
    assert host._podcast_library is podcast_library
    assert host._podcast_check_monitor is podcast_monitor
    assert podcast_monitor.cancellations == podcast_monitor.stops == 1

    host._set_profile_feature_enabled("core.radio", True)
    host._set_profile_feature_enabled("core.podcasts", True)
    assert host._radio_controller is radio_controller
    assert len(schedulers) == len(watchers) == 1
    assert host._radio_scheduler is schedulers[0]
    assert host._radio_wake_watcher is watchers[0]
    assert host._radio_last_seen_timer is radio_timer
    assert host._podcast_controller is podcast_controller
    assert host._podcast_library is podcast_library
    assert host._podcast_check_monitor is podcast_monitor

    for _label, task, _failure in queued:
        task()

    assert radio_builds == [host]
    assert podcast_builds == [host]
    assert radio_timer.starts == [60_000, 60_000]
    assert podcast_monitor.applies == 1
    assert host.automatic_calls.count("podcast maintenance") == 1
    assert host.automatic_calls.count("missed recordings") == 1


def test_partial_radio_failure_rolls_back_and_retries(monkeypatch: Any) -> None:
    from quill.ui.radio import startup_bootstrap

    _capture_deferred(monkeypatch)
    attempts: list[str] = []
    partial = SimpleNamespace(
        controller=_Controller(),
        recorder=_Resource(),
        scheduler=_Resource(),
        watcher=_Resource(),
        timer=_Timer(),
    )

    def fail_after_assignment(host: Any) -> None:
        attempts.append("fail")
        host._radio_controller = partial.controller
        host._radio_recorder = partial.recorder
        host._radio_scheduler = partial.scheduler
        host._radio_wake_watcher = partial.watcher
        host._radio_last_seen_timer = partial.timer
        raise RuntimeError("radio builder failed")

    monkeypatch.setattr(startup_bootstrap, "_build_radio", fail_after_assignment)
    host = _ProfileHost()
    host.features.enabled["core.radio"] = True
    host._ensure_profile_feature_runtime()

    assert getattr(host, "_radio_controller", None) is None
    assert getattr(host, "_radio_scheduler", None) is None
    assert host._radio_runtime_initialized is False
    assert host._radio_runtime_failed is True
    assert host.startup_failures == ["Radio runtime"]
    assert partial.controller.shutdowns == partial.recorder.shutdowns == 1
    assert partial.scheduler.shutdowns == partial.watcher.shutdowns == 1
    assert partial.timer.stops == 1

    def succeed(host: Any) -> None:
        attempts.append("retry")
        _build_radio(host)

    monkeypatch.setattr(startup_bootstrap, "_build_radio", succeed)
    host._ensure_profile_feature_runtime()
    assert attempts == ["fail", "retry"]
    assert host._radio_controller is not None
    assert host._radio_runtime_initialized is True
    assert host._radio_runtime_failed is False


def test_partial_podcast_failure_rolls_back_and_retries(monkeypatch: Any) -> None:
    from quill.ui.podcasts import startup_bootstrap

    _capture_deferred(monkeypatch)
    attempts: list[str] = []
    partial = SimpleNamespace(
        controller=_Controller(),
        monitor=_Monitor(),
        downloads=_Resource(),
        cache=_Resource(),
    )

    def fail_after_assignment(host: Any, *, defer_library_load: bool) -> None:
        assert defer_library_load is False
        attempts.append("fail")
        host._podcast_controller = partial.controller
        host._podcast_check_monitor = partial.monitor
        host._podcast_download_queue = partial.downloads
        host._podcast_cache_queue = partial.cache
        raise RuntimeError("podcast builder failed")

    monkeypatch.setattr(startup_bootstrap, "_build_podcasts", fail_after_assignment)
    host = _ProfileHost()
    host.features.enabled["core.podcasts"] = True
    host._ensure_profile_feature_runtime()

    assert getattr(host, "_podcast_controller", None) is None
    assert getattr(host, "_podcast_check_monitor", None) is None
    assert host._podcast_runtime_initialized is False
    assert host._podcast_runtime_failed is True
    assert host.startup_failures == ["Podcast runtime"]
    assert partial.controller.shutdowns == partial.monitor.shutdowns == 1
    assert partial.downloads.shutdowns == partial.cache.shutdowns == 1

    def succeed(host: Any, *, defer_library_load: bool) -> None:
        attempts.append("retry")
        _build_podcasts(host, defer_library_load=defer_library_load)

    monkeypatch.setattr(startup_bootstrap, "_build_podcasts", succeed)
    host._ensure_profile_feature_runtime()
    assert attempts == ["fail", "retry"]
    assert host._podcast_controller is not None
    assert host._podcast_runtime_initialized is True
    assert host._podcast_runtime_failed is False


def test_queued_wake_is_blocked_after_the_feature_is_disabled(monkeypatch: Any) -> None:
    monkeypatch.setattr("quill.ui.startup_launch.ssl_trust_ready", lambda: True)
    host = _ProfileHost()
    controller = _Controller()
    host._radio_controller = controller
    host.features.enabled["core.radio"] = False

    RadioMixin._apply_radio_wake_up(host, object())

    assert controller.shutdowns == 0


def test_queued_catalog_refresh_is_blocked_after_disable_and_reenable(
    monkeypatch: Any,
) -> None:
    from quill.ui.radio import catalog_ui

    work: list[Any] = []

    class _Tasks:
        @staticmethod
        def submit(_name: str, callback: Any, **_kwargs: object) -> None:
            work.append(callback)

    host = _ProfileHost()
    host.features.enabled["core.radio"] = True
    host._radio_history = SimpleNamespace(
        catalog_enabled=True,
        catalog_refresh_on_startup=True,
    )
    host._task_manager = _Tasks()
    monkeypatch.setattr(
        catalog_ui,
        "catalog_for",
        lambda _host: SimpleNamespace(age_seconds=lambda: 60 * 60 * 24),
    )
    refreshes: list[bool] = []
    monkeypatch.setattr(catalog_ui, "_refresh_now", lambda *_a, **_kw: refreshes.append(True))

    catalog_ui.refresh_on_startup(host)
    from quill.ui.radio.startup_bootstrap import pause_radio_automatic

    host.features.enabled["core.radio"] = False
    pause_radio_automatic(host)
    host.features.enabled["core.radio"] = True
    assert len(work) == 1
    work[0]()
    assert refreshes == []


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
