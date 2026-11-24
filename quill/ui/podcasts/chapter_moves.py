"""Next and Previous Chapter for whatever Quill Cast is playing (FUX-14).

Moved out of ``main_frame_podcasts.py`` (2026-11-23), which sits at its GATE-11
budget, when the two commands learned to say where they landed: the chapter's
name, its place in the list, and "estimated" for one Cast worked out rather
than one the podcast published -- the family's one landing sentence
(:mod:`quill.core.structure_landing`). Previous restarts the chapter you are in
after its first three seconds, the rule Radio and the Media Player follow;
before this it never did, and twenty minutes into chapter 1 said "Already at
the first chapter."
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.chapter_scoring import is_estimated
from quill.core.podcasts.chapters import next_chapter, previous_chapter
from quill.core.structure_landing import describe_boundary, describe_landing

__all__ = ["CHAPTER_RESTART_MS", "step_chapter"]

#: Previous Chapter more than this far into a chapter restarts it
#: (``quill.ui.radio.player_controller._CHAPTER_RESTART_MS``).
CHAPTER_RESTART_MS = 3000


def step_chapter(host: Any, direction: int) -> None:
    """Next (1) or Previous (-1) Chapter on *host*, said once."""
    chapters = host._podcast_current_chapters
    if not chapters:
        host._announce("This episode has no chapters.")
        return
    position = host._podcast_controller.position_ms()
    if direction > 0:
        target = next_chapter(chapters, position)
    else:
        target = previous_chapter(chapters, position, restart_ms=CHAPTER_RESTART_MS)
    if target is None:
        host._announce(describe_boundary("chapter", forward=direction > 0))
        return
    host._podcast_controller.seek(target.start_ms)
    host._announce(
        describe_landing(
            "chapter",
            target.title,
            chapters.index(target),
            len(chapters),
            estimated=is_estimated(target),
        )
    )
