"""Level, mute and boost for the podcast player.

Three numbers that have to stay honest about each other:

* ``volume_percent`` is what the listener set, and what the sleep timer will
  restore. It never reflects a boost -- restoring a boosted number is how a
  fade-out quietly becomes a permanent volume change.
* ``_pre_mute_volume`` is what mute has to give back, exactly.
* ``_volume_boost`` is live gain for quiet audio (0.5x-3.0x), applied only on
  the way to the engine.

Same shape and same words as ``RadioPlayerController``'s own volume handling,
so the two players cannot drift into behaving differently.
"""

from __future__ import annotations


class PodcastPlayerVolumeMixin:
    """Volume, mute and playback gain for :class:`PodcastPlayerController`."""

    def set_volume(self, percent: int) -> None:
        self._muted = False
        self._volume_percent = max(0, min(100, percent))
        self._apply_engine_volume()

    def toggle_mute(self) -> None:
        """Mirrors ``RadioPlayerController.toggle_mute``: silence without
        losing the level, restored exactly on the next toggle."""
        if self._muted:
            self._muted = False
            self._volume_percent = self._pre_mute_volume
        else:
            self._pre_mute_volume = self._volume_percent
            self._muted = True
            self._volume_percent = 0
        self._apply_engine_volume()

    @property
    def muted(self) -> bool:
        return self._muted

    def set_volume_boost(self, factor: float) -> None:
        """Live playback gain (0.5x - 3.0x, clamped) for quiet audio; scales
        the engine volume only. ``volume_percent`` keeps reporting the
        unboosted value so the sleep timer's restore stays honest."""
        self._volume_boost = max(0.5, min(3.0, float(factor)))
        self._apply_engine_volume()

    def _apply_engine_volume(self) -> None:
        if self._engine is not None:
            boosted = round(self._volume_percent * self._volume_boost)
            self._engine.set_volume(min(100, boosted))

    @property
    def volume_percent(self) -> int:
        return self._volume_percent
