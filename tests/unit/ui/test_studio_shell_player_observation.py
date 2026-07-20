"""Headless smoke for the standalone Studio shell's player-observation
wiring (Tasks 2.7/2.9/2.11 shell halves: media keys, per-book prefs,
queue auto-advance)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def app():
    import wx

    a = wx.App(False)
    yield a
    a.Destroy()


class _FakePlayer:
    """Records transport calls; stands in for a workbench PlayerPanel."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.muted = False

    def play_pause(self) -> None:
        self.calls.append("play_pause")

    def stop_playback(self) -> None:
        self.calls.append("stop")

    def next_chapter(self) -> None:
        self.calls.append("next")

    def previous_chapter(self) -> None:
        self.calls.append("prev")

    def toggle_mute(self) -> None:
        self.muted = not self.muted
        self.calls.append(f"mute:{self.muted}")

    def apply_book_prefs(self, prefs) -> None:  # noqa: ANN001
        self.calls.append(f"prefs:{prefs.volume_percent}/{prefs.muted}")


def _make_frame(tmp_path: Path):
    from quill.apps.studio import StudioAppFrame

    return StudioAppFrame()


def test_media_keys_delegate_to_active_player(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        # No active player -> handlers are silent no-ops.
        frame._on_media_play_pause()
        frame._on_media_stop()
        # Wire a fake active player.
        fake = _FakePlayer()
        frame._on_player_ready(fake, str(tmp_path / "book.m4b"))
        fake.calls.clear()  # drop the apply_book_prefs call from _on_player_ready
        frame._on_media_play_pause()
        frame._on_media_stop()
        frame._on_media_next_chapter()
        frame._on_media_prev_chapter()
        assert fake.calls == ["play_pause", "stop", "next", "prev"]
    finally:
        frame.frame.Destroy()


def test_per_book_volume_and_mute_persist(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        path = str(tmp_path / "book.m4b")
        frame._on_player_ready(_FakePlayer(), path)
        frame._on_book_volume(path, 37)
        frame._on_book_mute(path, True)
        from quill.core.audio_studio.book_prefs import get_prefs, load_prefs

        reloaded = load_prefs(tmp_path)
        assert get_prefs(reloaded, path).volume_percent == 37
        assert get_prefs(reloaded, path).muted is True
    finally:
        frame.frame.Destroy()


def test_queue_advances_after_finish_then_close(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        import wx

        # Stage two real files so the advance target exists.
        a = tmp_path / "a.m4b"
        b = tmp_path / "b.m4b"
        a.write_bytes(b"")
        b.write_bytes(b"")
        from quill.core.audio_studio.play_queue import (
            PlayQueue,
            QueueEntry,
            add as queue_add,
        )
        q = PlayQueue()
        queue_add(q, QueueEntry(str(a), "A"))
        queue_add(q, QueueEntry(str(b), "B"))
        frame._play_queue = q
        # Capture CallAfter instead of flushing events (which would also fire
        # the deferred startup update check and hit the network).
        scheduled: list[tuple[object, tuple]] = []
        monkeypatch.setattr(
            wx, "CallAfter", lambda fn, *a2: scheduled.append((fn, a2))
        )
        # Simulate book A finishing, then the workbench closing.
        frame._on_book_finished(str(a))
        frame._on_book_closed(str(a), position_ms=1000, chapter=2)
        assert len(scheduled) == 1
        fn, args = scheduled[0]
        assert fn == frame.open_book
        assert str(args[0]) == str(b)
    finally:
        frame.frame.Destroy()


def test_auto_advance_skips_a_missing_next_file(app, tmp_path, monkeypatch) -> None:
    # A missing next entry used to be announced ("Up next") then silently
    # dead-end. Now the queue skips missing files to the next playable one, and
    # the announcement names the book that actually opens.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        import wx

        a = tmp_path / "a.m4b"
        c = tmp_path / "c.m4b"
        a.write_bytes(b"")
        c.write_bytes(b"")  # b is intentionally NOT created (missing)
        from quill.core.audio_studio.play_queue import (
            PlayQueue,
            QueueEntry,
            add as queue_add,
        )
        q = PlayQueue()
        queue_add(q, QueueEntry(str(a), "A"))
        queue_add(q, QueueEntry(str(tmp_path / "b.m4b"), "B"))  # missing
        queue_add(q, QueueEntry(str(c), "C"))
        frame._play_queue = q
        said: list[str] = []
        monkeypatch.setattr(frame, "_announce", said.append)
        scheduled: list[tuple[object, tuple]] = []
        monkeypatch.setattr(wx, "CallAfter", lambda fn, *a2: scheduled.append((fn, a2)))
        frame._on_book_finished(str(a))
        # Announcement names C (the next PLAYABLE), not the missing B.
        assert said == ["Finished. Up next in the queue: C"]
        frame._on_book_closed(str(a), position_ms=0, chapter=0)
        assert len(scheduled) == 1
        fn, args = scheduled[0]
        assert fn == frame.open_book
        assert str(args[0]) == str(c)
    finally:
        frame.frame.Destroy()


def test_auto_advance_all_missing_says_end_of_book(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        import wx

        a = tmp_path / "a.m4b"
        a.write_bytes(b"")
        from quill.core.audio_studio.play_queue import (
            PlayQueue,
            QueueEntry,
            add as queue_add,
        )
        q = PlayQueue()
        queue_add(q, QueueEntry(str(a), "A"))
        queue_add(q, QueueEntry(str(tmp_path / "gone.m4b"), "Gone"))  # missing
        frame._play_queue = q
        said: list[str] = []
        monkeypatch.setattr(frame, "_announce", said.append)
        scheduled: list[tuple[object, tuple]] = []
        monkeypatch.setattr(wx, "CallAfter", lambda fn, *a2: scheduled.append((fn, a2)))
        frame._on_book_finished(str(a))
        assert said == ["End of book."]  # nothing playable ahead
        frame._on_book_closed(str(a), position_ms=0, chapter=0)
        assert scheduled == []  # no lie: nothing opens
    finally:
        frame.frame.Destroy()


def test_resume_missing_book_announces(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        said: list[str] = []
        monkeypatch.setattr(frame, "_announce", said.append)
        frame._history.record(
            str(tmp_path / "gone.m4b"), title="gone", position_ms=0, chapter=0
        )
        frame._maybe_resume_last_book()
        assert said == ["gone is no longer where it was; it may have been moved or renamed."]
    finally:
        frame.frame.Destroy()


def test_sleep_fired_without_player_announces_ended(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        said: list[str] = []
        monkeypatch.setattr(frame, "_announce", said.append)
        frame._active_player = None
        frame._on_sleep_fired()
        assert said == ["Sleep timer ended."]  # not "playback stopped" when nothing played
    finally:
        frame.frame.Destroy()


def test_stale_delay_sleep_timer_cleared_on_launch(app, tmp_path, monkeypatch) -> None:
    # A delay-mode sleep timer that was enabled at a previous close is stale on
    # relaunch (its countdown can't survive a restart), so it is cleared rather
    # than lying that a timer is armed. End-of-chapter mode is kept.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    from quill.core.audio_studio.sleep_timer import SleepTimerSetting, save_sleep_setting

    save_sleep_setting(
        tmp_path, SleepTimerSetting(enabled=True, delay_minutes=30, end_of_chapter=False)
    )
    frame = _make_frame(tmp_path)
    try:
        assert frame._sleep_setting.enabled is False  # stale delay timer cleared
    finally:
        frame.frame.Destroy()


class _ChapterPlayer:
    """A player that reports a settable chapter index, for sleep-timer tests."""

    def __init__(self, chapter: int = 0) -> None:
        self.chapter = chapter
        self.calls: list[str] = []

    def current_chapter_index(self) -> int:
        return self.chapter

    def stop_playback(self) -> None:
        self.calls.append("stop")


def test_end_of_chapter_sleep_stops_when_chapter_advances(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        player = _ChapterPlayer(chapter=2)
        frame._active_player = player
        frame._sleep_setting.enabled = True
        frame._sleep_setting.end_of_chapter = True
        frame._arm_end_of_chapter_watch()
        assert frame._sleep_eoc_from_chapter == 2
        # Still inside the armed chapter -> no stop.
        frame._poll_end_of_chapter()
        assert "stop" not in player.calls
        # Playhead crosses into the next chapter -> stop at end of chapter.
        player.chapter = 3
        frame._poll_end_of_chapter()
        assert "stop" in player.calls
        assert frame._sleep_eoc_from_chapter == -1  # disarmed
    finally:
        frame.frame.Destroy()


def test_reveal_missing_file_announces(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        from quill.core.audio_studio.library import BookEntry

        said: list[str] = []
        monkeypatch.setattr(frame, "_announce", said.append)
        frame._reveal_book_in_folder(
            BookEntry(path=str(tmp_path / "gone.m4b"), title="Gone")
        )
        assert said == ["Gone is no longer where it was; it may have been moved or renamed."]
    finally:
        frame.frame.Destroy()


def test_reveal_existing_file_invokes_file_manager(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        import subprocess

        from quill.core.audio_studio.library import BookEntry

        book = tmp_path / "book.m4b"
        book.write_bytes(b"")
        launched: list[object] = []
        monkeypatch.setattr(subprocess, "Popen", lambda args, *a, **k: launched.append(args))
        said: list[str] = []
        monkeypatch.setattr(frame, "_announce", said.append)
        frame._reveal_book_in_folder(BookEntry(path=str(book), title="Book"))
        assert len(launched) == 1
        assert any("book.m4b" in str(part) for part in launched[0])
        assert said and "file manager" in said[0]
    finally:
        frame.frame.Destroy()

def test_media_keys_grabbed_only_while_a_book_is_open(app, tmp_path, monkeypatch) -> None:
    """The system media keys are registered when a book starts playing and
    released when it closes, so an idle Studio never swallows them."""
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        assert frame._media_keys_active is False  # idle at startup
        frame._on_player_ready(_FakePlayer(), "/x.m4b")
        assert frame._media_keys_active is True  # book playing -> grabbed
        frame._on_book_closed("/x.m4b", position_ms=0, chapter=0)
        assert frame._media_keys_active is False  # closed -> released
    finally:
        frame.frame.Destroy()
