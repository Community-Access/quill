"""Settings-apply must refresh long-lived policy snapshots (polish.md P0.3).

The staleness class: a controller built lazily snapshots its config from
settings and holds it for the life of the shell, so a Preferences change
silently means "after the next restart" while the dialog implies "now". The
dictation controller had it (fixed 2026-08-17 by re-snapshotting per access);
the audit then found the announcement service's policy and the verbosity
controller had the same shape — core-side refresh hooks existed for both, with
no caller. These tests pin the wiring so the class cannot quietly return.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.announce.policy import AnnouncementPolicy
from quill.ui.announce_wiring import policy_from_settings, refresh_announcement_policy


class _Service:
    def __init__(self) -> None:
        self.policy = AnnouncementPolicy()

    def set_policy(self, policy: AnnouncementPolicy) -> None:
        self.policy = policy


def test_refresh_announcement_policy_rederives_from_current_settings() -> None:
    service = _Service()
    host = SimpleNamespace(
        _announcement_service=service,
        settings=SimpleNamespace(announcement_braille_dedupe_seconds=7.5),
    )
    refresh_announcement_policy(host)
    from quill.core.announce.message import Channel

    assert service.policy._dedupe[Channel.BRAILLE] == 7.5  # noqa: SLF001 - pinning the derived value


def test_refresh_is_a_noop_before_the_service_exists() -> None:
    host = SimpleNamespace(settings=SimpleNamespace())
    refresh_announcement_policy(host)  # must not raise, must not build a service
    assert getattr(host, "_announcement_service", None) is None


def test_policy_from_settings_matches_build_path() -> None:
    """The refresh derives policy through the same helper the builder uses, so
    the two can never disagree about what a setting means."""
    settings = SimpleNamespace(announcement_braille_dedupe_seconds=3.0)
    policy = policy_from_settings(settings)
    from quill.core.announce.message import Channel

    assert policy._dedupe[Channel.BRAILLE] == 3.0  # noqa: SLF001 - pinning the derived value


def test_settings_apply_path_names_both_refreshes() -> None:
    """The wiring lives in _settings_dialog_apply_refresh; pin its presence
    textually (the method needs a full wx frame to run) so a refactor that
    drops either refresh fails loudly here rather than silently regressing."""
    from pathlib import Path

    source = Path("quill/ui/main_frame_preferences.py").read_text(encoding="utf-8")
    apply_body = source.split("def _settings_dialog_apply_refresh", 1)[1].split("\n    def ", 1)[0]
    assert "refresh_live_policies" in apply_body  # the one-call P0.3 fix
    wiring = Path("quill/ui/announce_wiring.py").read_text(encoding="utf-8")
    trio = wiring.split("def refresh_live_policies", 1)[1].split("\ndef ", 1)[0]
    assert "refresh_announcement_policy" in trio
    assert "apply_settings" in trio  # the verbosity controller refresh
    assert "refresh_policy" in trio  # the watch-service monitor policy


def test_watch_service_adopts_a_new_policy_live(tmp_path) -> None:
    from quill.core.monitor_policy import MonitorPolicy
    from quill.core.watch_profiles import WatchManager, WatchQueue

    queue = WatchQueue(storage_path=tmp_path / "queue.json")
    manager = WatchManager(queue, policy=MonitorPolicy(poll_interval_seconds=60))
    replacement = MonitorPolicy(poll_interval_seconds=5)
    manager.set_policy(replacement)
    assert manager.policy is replacement
