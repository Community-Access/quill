"""The controller's track, caption and chapter face, as a mixin (GATE-11).

Four methods that only ever forwarded to :mod:`quill.ui.radio.track_selection`
lived on ``RadioPlayerController``, which is the largest module in the radio
UI and at its budget. Delegations are exactly the thing worth moving when a
module has to give something back: the behaviour is entirely elsewhere
already, so nothing moves except the forwarding, and the controller keeps the
same public surface through the MRO.

Extracted 2026-08-24, when Skip Silence (11.7) pushed the controller past its
ceiling. The rule GATE-11 states -- extract, never raise the budget -- is why
this file exists rather than a bigger number in ``module_size_budgets.json``.
"""

from __future__ import annotations

from typing import Any


class PlayerTracksMixin:
    """Audio renditions, captions and chapters for whatever is playing."""

    def chapters(self) -> list[Any]:
        """The published chapters of what is playing, or an empty list.

        A video's own markers, or a podcast episode's Podcasting 2.0
        chapters -- both published by the source, never guessed. The two
        shapes are unified in quill/ui/radio/episode_profile.py.
        """
        from quill.ui.radio import episode_profile

        return episode_profile.chapters_for(self)

    def current_chapter_index(self) -> int:
        """Index of the chapter the playhead sits in, or -1 if none applies."""
        chapters = self.chapters()
        if not chapters:
            return -1
        position = int(self._engine.position_ms())
        current = -1
        for index, chapter in enumerate(chapters):
            if int(getattr(chapter, "start_ms", 0)) <= position:
                current = index
            else:
                break
        return current

    def audio_tracks(self) -> list[Any]:
        """Every selectable audio rendition of what is playing.
        See :mod:`quill.ui.radio.track_selection`."""
        from quill.ui.radio import track_selection

        return track_selection.audio_tracks(self)

    def play_audio_track(self, track: Any) -> bool:
        """Switch to *track* (a reload, keeping the position). True on success."""
        from quill.ui.radio import track_selection

        return track_selection.play_audio_track(self, track)

    def selected_audio_track(self) -> Any:
        """The rendition currently playing, or ``None`` for the default."""
        from quill.ui.radio import track_selection

        return track_selection.selected_audio_track(self)

    def caption_track(self) -> tuple[str, bool]:
        """``(caption url, is automatic)`` for what is playing."""
        from quill.ui.radio import track_selection

        return track_selection.caption_track(self)
