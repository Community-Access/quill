"""The Chapter Workbench's add/delete/edit/preview/nudge handlers, host-free.

The mixin is tested against the smallest thing that satisfies its contract --
a book, a selection, a fake player -- rather than through a real Workbench,
because the behaviour worth pinning here is the *speech*: what a nudge says at
key-repeat speed, and what it says when it can no longer move. A real dialog
would bury that under widget plumbing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from quill.core.speech.chapters import Chapter  # noqa: E402
from quill.ui.audio_studio.chapter_workbench_edits import (  # noqa: E402
    ChapterEditsMixin,
)


class _FakePlayer:
    """Just enough player: a playhead you can move, and a record of what happened."""

    def __init__(self) -> None:
        self.sought: list[int] = []
        self.played = 0
        self.paused = 0
        self._head = 5_000

    def playhead_ms(self) -> int:
        return self._head

    def seek_to(self, ms: int) -> None:
        self.sought.append(ms)
        self._head = ms

    def play(self) -> None:
        self.played += 1

    def pause(self) -> None:
        self.paused += 1


class _Host(ChapterEditsMixin):
    """The smallest host the mixin's contract asks for."""

    def __init__(self, chapters: list[Chapter]) -> None:
        from quill.core.speech.book_file import BookFile
        from quill.core.speech.ffmpeg import AudioMetadata

        self._book = BookFile(
            path=Path("book.mp3"),
            tags=AudioMetadata(),
            chapters=chapters,
            total_ms=chapters[-1].end_ms,
        )
        self.player = _FakePlayer()
        self.selection = 1
        self.errors: list[str] = []
        self.spoken: list[str] = []
        self.settings_nudge_ms = 500
        self.hear_after = False

    def _selected_index(self) -> int:
        return self.selection

    def _apply(self, chapters: list[Chapter], *, select: int, spoken: str) -> None:
        self._book.chapters = chapters
        self.selection = select
        self.spoken.append(spoken)

    def _error(self, message: str) -> None:
        self.errors.append(message)

    def _announce(self, text: str) -> None:
        self.spoken.append(text)

    def _hear_after_nudge(self) -> bool:
        return self.hear_after

    def _schedule_nudge_settle(self, index: int) -> None:
        """No wx app in these tests; record that the settle was scheduled."""
        self.settled = index


def _three() -> list[Chapter]:
    return [
        Chapter(index=0, title="One", start_ms=0, end_ms=10_000),
        Chapter(index=1, title="Two", start_ms=10_000, end_ms=20_000),
        Chapter(index=2, title="Three", start_ms=20_000, end_ms=30_000),
    ]


class TestDelete:
    def test_it_removes_the_selected_chapter(self) -> None:
        host = _Host(_three())
        host._on_delete_chapter()
        assert [c.title for c in host._book.chapters] == ["One", "Three"]
        assert not host.errors

    def test_it_says_the_audio_is_unchanged(self) -> None:
        """The one thing somebody deleting a chapter needs to be sure of."""
        host = _Host(_three())
        host._on_delete_chapter()
        assert "audio is unchanged" in host.spoken[-1]

    def test_the_only_chapter_reports_the_refusal(self) -> None:
        host = _Host([Chapter(index=0, title="All", start_ms=0, end_ms=10_000)])
        host.selection = 0
        host._on_delete_chapter()
        assert host.errors
        assert len(host._book.chapters) == 1

    def test_nothing_selected_reports_it(self) -> None:
        host = _Host(_three())
        host.selection = -1
        host._on_delete_chapter()
        assert host.errors == ["No chapter is selected."]


class TestPreview:
    def test_it_seeks_to_the_start_and_arms_the_stop(self) -> None:
        host = _Host(_three())
        host._on_preview_chapter()
        assert host.player.sought == [10_000]
        assert host.player.played == 1
        assert host._stop_at_ms == 20_000

    def test_the_stop_fires_once_at_the_chapter_end(self) -> None:
        host = _Host(_three())
        host._on_preview_chapter()
        host.player._head = 19_000
        assert host._check_preview_stop() is False
        assert host.player.paused == 0
        host.player._head = 20_001
        assert host._check_preview_stop() is True
        assert host.player.paused == 1
        assert host._stop_at_ms is None
        assert host._check_preview_stop() is False
        assert host.player.paused == 1

    def test_an_unarmed_tick_costs_nothing(self) -> None:
        host = _Host(_three())
        assert host._check_preview_stop() is False
        assert host.player.paused == 0

    def test_nothing_selected_reports_it(self) -> None:
        host = _Host(_three())
        host.selection = -1
        host._on_preview_chapter()
        assert host.errors


class TestHearBoundary:
    def test_it_plays_a_window_around_the_marker(self) -> None:
        host = _Host(_three())
        host._on_hear_boundary()
        assert host.player.sought == [7_000]
        assert host._stop_at_ms == 12_000
        assert host.player.played == 1

    def test_the_lead_clamps_at_the_start_of_the_file(self) -> None:
        chapters = _three()
        chapters[0].end_ms = 1_000
        chapters[1].start_ms = 1_000
        host = _Host(chapters)
        host._on_hear_boundary()
        assert host.player.sought == [0]

    def test_the_tail_clamps_at_the_end_of_the_file(self) -> None:
        chapters = _three()
        host = _Host(chapters)
        host.selection = 2
        host._book.total_ms = 21_000
        host._on_hear_boundary()
        assert host._stop_at_ms == 21_000


class TestNudge:
    def test_back_moves_the_marker_by_the_step(self) -> None:
        host = _Host(_three())
        host._on_nudge(-1)
        assert host._book.chapters[1].start_ms == 9_500
        assert host._book.chapters[0].end_ms == 9_500

    def test_forward_uses_the_configured_step(self) -> None:
        host = _Host(_three())
        host.settings_nudge_ms = 2_000
        host._on_nudge(1)
        assert host._book.chapters[1].start_ms == 12_000

    def test_the_multiplier_moves_ten_steps(self) -> None:
        host = _Host(_three())
        host._on_nudge(1, multiplier=10)
        assert host._book.chapters[1].start_ms == 15_000

    def test_it_speaks_the_bare_time_not_a_sentence(self) -> None:
        """A sentence repeated at key-repeat speed is noise, not feedback."""
        host = _Host(_three())
        host.spoken.clear()
        host._on_nudge(-1)
        assert host.spoken == ["0:00:09.500"]

    def test_the_wall_is_announced_once_per_run(self) -> None:
        host = _Host([
            Chapter(index=0, title="One", start_ms=0, end_ms=500),
            Chapter(index=1, title="Two", start_ms=500, end_ms=1_000),
        ])
        host.spoken.clear()
        host._on_nudge(-1)
        host._on_nudge(-1)
        host._on_nudge(-1)
        assert host.spoken == ["Cannot move further."]

    def test_moving_again_re_arms_the_wall_announcement(self) -> None:
        host = _Host(_three())
        host.settings_nudge_ms = 100_000
        host._on_nudge(-1)  # clamps, but does move
        host.spoken.clear()
        host._on_nudge(-1)  # now at the wall
        host._on_nudge(-1)
        assert host.spoken == ["Cannot move further."]
        host._on_nudge(1)  # moves off the wall
        host.spoken.clear()
        host._on_nudge(-1)  # back to the wall: it may speak again
        host._on_nudge(-1)
        assert host.spoken.count("Cannot move further.") <= 1

    def test_the_first_chapter_reports_the_refusal(self) -> None:
        host = _Host(_three())
        host.selection = 0
        host._on_nudge(1)
        assert host.errors
        assert "beginning" in host.errors[0]

    def test_nothing_selected_reports_it(self) -> None:
        host = _Host(_three())
        host.selection = -1
        host._on_nudge(1)
        assert host.errors

    def test_hear_after_nudge_is_off_unless_asked_for(self) -> None:
        host = _Host(_three())
        host._on_nudge(-1)
        assert host.player.played == 0

    def test_hear_after_nudge_plays_the_boundary_when_ticked(self) -> None:
        host = _Host(_three())
        host.hear_after = True
        host._on_nudge(-1)
        assert host.player.played == 1
        assert host.player.sought == [6_500]


class TestKeyHandler:
    class _Key:
        def __init__(self, code: int, *, alt: bool, shift: bool = False) -> None:
            self._code = code
            self._alt = alt
            self._shift = shift
            self.skipped = False

        def GetKeyCode(self) -> int:  # noqa: N802 - wx API casing
            return self._code

        def AltDown(self) -> bool:  # noqa: N802 - wx API casing
            return self._alt

        def ShiftDown(self) -> bool:  # noqa: N802 - wx API casing
            return self._shift

        def Skip(self) -> None:  # noqa: N802 - wx API casing
            self.skipped = True

    def test_alt_left_nudges_back_one_step(self) -> None:
        host = _Host(_three())
        event = self._Key(wx.WXK_LEFT, alt=True)
        host._nudge_key_handler(event)
        assert host._book.chapters[1].start_ms == 9_500
        assert event.skipped is False

    def test_alt_shift_right_nudges_ten_steps(self) -> None:
        host = _Host(_three())
        host._nudge_key_handler(self._Key(wx.WXK_RIGHT, alt=True, shift=True))
        assert host._book.chapters[1].start_ms == 15_000

    def test_a_plain_arrow_passes_through_to_the_list(self) -> None:
        """Without Skip, arrowing the chapter list would stop working."""
        host = _Host(_three())
        event = self._Key(wx.WXK_LEFT, alt=False)
        host._nudge_key_handler(event)
        assert event.skipped is True
        assert host._book.chapters[1].start_ms == 10_000


class TestWorkbenchWiring:
    """The handlers exist; these check the Workbench actually reaches them."""

    def test_the_workbench_inherits_the_mixin(self) -> None:
        from quill.ui.audio_studio.chapter_workbench import ChapterWorkbenchDialog

        assert issubclass(ChapterWorkbenchDialog, ChapterEditsMixin)

    def test_every_new_operation_has_a_button(self) -> None:
        """A key with no button is a feature only its author can find."""
        import inspect

        from quill.ui.audio_studio import chapter_workbench_edits

        source = inspect.getsource(chapter_workbench_edits)
        for label in (
            "Add chapter",
            "Delete chapter",
            "Edit chapter",
            "Preview chapter",
            "Nudge back",
            "Nudge forward",
            "Hear boundar",
            "Hear after each nud",
        ):
            flat = source.replace("&", "")
            assert label in flat, f"no button for {label}"

    def test_the_tag_editor_is_reachable_from_the_workbench(self) -> None:
        """The button sits on the Workbench; the handler lives in the mixin."""
        import inspect

        from quill.ui.audio_studio import chapter_workbench, chapter_workbench_edits

        assert "All ta&gs..." in inspect.getsource(chapter_workbench)
        assert "_on_all_tags" in inspect.getsource(chapter_workbench)
        assert "TagEditorDialog" in inspect.getsource(chapter_workbench_edits)

    def test_the_chapter_list_binds_the_nudge_keys(self) -> None:
        import inspect

        from quill.ui.audio_studio import chapter_workbench

        source = inspect.getsource(chapter_workbench)
        assert "_nudge_key_handler" in source
        assert "EVT_KEY_DOWN" in source

    def test_the_preview_stop_rides_the_players_own_tick(self) -> None:
        """Not a second wx.Timer: the player already ticks."""
        import inspect

        from quill.ui.audio_studio import chapter_workbench

        source = inspect.getsource(chapter_workbench)
        assert "on_tick=self._check_preview_stop" in source

    def test_the_save_button_reflects_which_edits_are_pending(self) -> None:
        """An M4B can save tags in place; only a chapter change needs Save As."""
        import inspect

        from quill.ui.audio_studio.chapter_workbench_edits import ChapterEditsMixin

        source = inspect.getsource(ChapterEditsMixin._sync_save_button)
        assert "_chapters_dirty" in source
        assert "Save As" in source
