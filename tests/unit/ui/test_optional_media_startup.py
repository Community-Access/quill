"""Feature-gated media bootstrapping for minimal QUILL profiles."""

from __future__ import annotations

import inspect

from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.main_frame_radio import RadioMixin


def test_disabled_radio_profile_never_constructs_player_state() -> None:
    class Host:
        def _feature_enabled(self, feature_id: str) -> bool:
            assert feature_id == "core.radio"
            return False

    host = Host()
    RadioMixin._init_radio(host)  # type: ignore[arg-type]

    assert host._radio_controller is None
    assert host._radio_recorder is None
    assert host._radio_scheduler is None
    assert host._radio_wake_watcher is None


def test_enabled_radio_profile_keeps_the_player_bootstrap() -> None:
    from quill.ui.radio import startup_bootstrap

    source = inspect.getsource(startup_bootstrap.initialize_radio)
    assert source.index('if not host._feature_enabled("core.radio")') < source.index(
        "RadioPlayerController("
    )
    assert source.index("RadioPlayerController(") < source.index("RecordingScheduler(")


def test_disabled_podcast_profile_never_constructs_player_state() -> None:
    class Host:
        def _feature_enabled(self, feature_id: str) -> bool:
            assert feature_id == "core.podcasts"
            return False

    host = Host()
    PodcastsMixin._init_podcasts(host)  # type: ignore[arg-type]

    assert host._podcast_library is None
    assert host._podcast_history is None
    assert host._podcast_controller is None
    assert host._podcast_check_monitor is None


def test_enabled_podcast_profile_keeps_the_player_bootstrap() -> None:
    source = inspect.getsource(PodcastsMixin._init_podcasts)
    assert source.index('if not self._feature_enabled("core.podcasts")') < source.index(
        "PodcastPlayerController("
    )
    assert "PodcastCheckMonitor(" in source
