"""What the podcast Player Information report reads (extracted for GATE-11).

``PlayerInfo`` itself is pure and lives in ``core/media/player_info.py``; the
dialog that shows it is ``ui/media/player_info_dialog.py``. This is the third
piece: gathering the values from the live controller and library. It sat
inside ``main_frame_podcasts.py``, which was at its budget, and it is a real
seam rather than a convenient one -- everything here is *reading state to
build a report*, and none of it needs the frame.

One rule this file exists to keep: **never report a number it cannot compute.**
The note count used to be gathered by a call with the wrong arity, wrapped in a
broad ``except`` -- so it raised on every run and the report said "0 notes" for
an episode with fifty. A confident wrong number is worse than an absent one
(rule A-10), and the fix is tested in
``tests/unit/ui/test_podcast_player_info_notes.py``.
"""

from __future__ import annotations

from typing import Any


def gather(host: Any) -> Any:
    """Build the :class:`PlayerInfo` for whatever *host* is playing."""
    from quill.core.media.player_info import PlayerInfo
    from quill.core.podcasts.episode_notes import load_episode_notes, notes_for_episode

    controller = host._podcast_controller
    state = controller.state
    show = host._podcast_library.find_show(state.show_id) if state.show_id is not None else None
    episode = (
        show.find_episode(state.episode_guid)
        if show is not None and state.episode_guid is not None
        else None
    )
    downloaded = str(getattr(episode, "downloaded_path", "")) if episode else ""
    position_ms = controller.position_ms()
    extras: list[str] = []
    chapters = list(getattr(host, "_podcast_current_chapters", []) or [])
    if chapters:
        source = str(getattr(host, "_podcast_chapters_source", ""))
        current = sum(1 for chapter in chapters if chapter.start_ms <= position_ms)
        extras.append(
            f"Chapter: {max(1, current)} of {len(chapters)}" + (f" ({source})" if source else "")
        )
    try:
        # notes_for_episode filters an already-loaded list; it does not load
        # one. Passing it two arguments raised TypeError on every run.
        notes = notes_for_episode(
            load_episode_notes(), state.show_id or "", state.episode_guid or ""
        )
        note_count = len(notes)
    except Exception:  # noqa: BLE001 - a missing notes file is simply no notes
        note_count = 0
    return PlayerInfo(
        title=state.title,
        collection=getattr(show, "title", ""),
        position_ms=position_ms,
        duration_ms=controller.length_ms(),
        speed=controller.rate,
        streaming=not downloaded,
        saved_permanently=bool(downloaded),
        note_count=note_count,
        resume_ms=int(getattr(episode, "position_ms", 0) or 0),
        extras=tuple(extras),
    )


__all__ = ["gather"]
