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
    # The Manager's download actions moved to manager_downloads.py in 1.1.0,
    # and auto-download to main_frame_podcast_acquisition.py. Every one of
    # them still has to go through the helper that attaches the same-host
    # Authorization header -- which is exactly what this checks, so the list
    # grows with the extraction rather than the rule being narrowed.
    for rel in (
        "ui/main_frame_podcasts.py",
        "ui/podcasts/manager_downloads.py",
        "ui/main_frame_podcast_acquisition.py",
    ):
        src = _read(rel)
        assert "enqueue_episode_download(" in src, rel
        assert ".enqueue(" not in src, rel


def test_chapters_and_transcripts_pass_auth_header() -> None:
    # Chapters now come from the free cascade (published feed -> the file's own
    # tags -> timestamps in the show notes), so the authenticated fetch moved
    # into that one core helper. Both UI sites must route through it rather than
    # fetching for themselves, which is the same "one helper" rule the download
    # sites follow above.
    cascade = _read("core/podcasts/chapter_sources.py")
    assert "auth_header_for_url(show, chapters_url)" in cascade
    for rel in ("ui/podcasts/manager_dialog.py", "ui/main_frame_podcasts.py"):
        src = _read(rel)
        assert "build_episode_chapters(" in src, rel
        assert "fetch_and_parse_chapters(" not in src, rel
    # The transcript commands moved to ui/podcasts/transcript_actions.py when the
    # shared reader arrived (manager_phase4.py was at its GATE-11 ceiling); the
    # rule follows them. Both fetch paths there -- text, and timed cues -- must
    # carry the feed's own credentials, or a private feed's transcript 401s.
    actions = _read("ui/podcasts/transcript_actions.py")
    assert actions.count("auth_header_for_url(show, episode.transcript_url)") == 2
    assert "auth_header_for_url" not in _read("ui/podcasts/manager_phase4.py")


def test_every_play_call_site_uses_the_shared_playback_helper() -> None:
    assert "playback_source(show, episode)" in _read("ui/podcasts/show_actions.py")
    # The 1.1.0 surfaces that start playback (the Winamp transport keys, the
    # per-show actions) deliberately do NOT call the helper themselves -- they
    # go through their host's one play method, which does. What matters is
    # that no site anywhere builds its own source URL, asserted below.
    for rel in ("ui/podcasts/winamp_mixin.py", "ui/podcasts/manager_actions.py"):
        assert "episode.downloaded_path or episode.audio_url" not in _read(rel), rel
    for rel in (
        "ui/podcasts/manager_dialog.py",
        "ui/podcasts/manager_phase4.py",
        "ui/main_frame_podcasts.py",
        "apps/podcasts.py",
    ):
        src = _read(rel)
        assert "start_episode_playback(" in src, rel
        assert "episode.downloaded_path or episode.audio_url" not in src, rel
