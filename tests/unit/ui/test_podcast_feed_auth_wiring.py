"""Every per-show network call site passes gated credentials (spec D-1).

The shared implementations live in show_actions (enqueue_episode_download,
start_episode_playback, announce_if_feed_auth_failure) so a call site can't
forget the Authorization header; these tests pin both the helpers' contents
and that every surface actually routes through them.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3] / "quill"


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_feed_refresh_passes_credentials_and_reports_auth_failure() -> None:
    src = _read("ui/main_frame_podcasts.py")
    assert "auth_for_url(show, show.feed_url)" in src
    assert "announce_if_feed_auth_failure(" in src
    helpers = _read("ui/podcasts/show_actions.py")
    assert "FeedAuthError" in helpers
    assert "feed sign-in failed" in helpers


def test_download_helper_applies_the_same_host_gate() -> None:
    helpers = _read("ui/podcasts/show_actions.py")
    assert "auth_header_for_url(show, episode.audio_url)" in helpers


def test_every_download_site_routes_through_the_helper() -> None:
    for rel in ("ui/main_frame_podcasts.py", "ui/podcasts/manager_dialog.py"):
        src = _read(rel)
        assert "enqueue_episode_download(" in src, rel
        assert ".enqueue(" not in src, rel


def test_chapters_and_transcripts_pass_auth_header() -> None:
    assert "auth_header_for_url(show, episode.chapters_url)" in _read(
        "ui/podcasts/manager_dialog.py"
    )
    assert "auth_header_for_url(show, episode.chapters_url)" in _read("ui/main_frame_podcasts.py")
    assert "auth_header_for_url(show, episode.transcript_url)" in _read(
        "ui/podcasts/manager_phase4.py"
    )


def test_every_play_call_site_uses_the_shared_playback_helper() -> None:
    assert "playback_source(show, episode)" in _read("ui/podcasts/show_actions.py")
    for rel in (
        "ui/podcasts/manager_dialog.py",
        "ui/podcasts/manager_phase4.py",
        "ui/main_frame_podcasts.py",
        "apps/podcasts.py",
    ):
        src = _read(rel)
        assert "start_episode_playback(" in src, rel
        assert "episode.downloaded_path or episode.audio_url" not in src, rel
