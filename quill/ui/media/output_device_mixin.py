"""The device a player is routed to, and switching it live -- once, for all of them.

QUILL Cast's podcast controller and the shared transport panel (Audio Studio,
Quill Media Player) both gained the same three methods when the family learned
to choose a sound card, and two copies of "remember the device, ask the engine
to take it, keep the old one if it will not" is exactly how the two drift into
answering differently.

They differ in one thing only -- *which* engine is theirs -- so that is the one
thing a user of this mixin says. Cast's answer is its stream engine rather than
``self._engine``, because a Spotify episode swaps that for the Web Playback
engine, which plays in a browser process and has no sound card of ours to pick.
"""

from __future__ import annotations

__all__ = ["OutputDeviceMixin"]


class OutputDeviceMixin:
    """Shared output-device state for a player.

    The host sets ``self._output_device`` in its own ``__init__`` (to the device
    it loaded from settings, or ``""``) and implements :meth:`output_engine`.
    """

    _output_device: str

    def output_engine(self) -> object:
        """The engine actually playing -- the host's to answer.

        Asked of the host rather than worked out from what the machine has
        installed: a computer with libmpv present can still be playing on the
        classic ``wx.media`` control, which has no device API at all, and only
        the live engine knows which it is.
        """
        raise NotImplementedError

    def output_device(self) -> str:
        """The device this player is routed to ("" = the system default)."""
        return getattr(self, "_output_device", "")

    def set_output_device(self, name: str) -> bool:
        """Send this player's audio to device *name*. Did it take?

        Live, with no reload: both engines that can route switch a playing file
        themselves, so somebody forty minutes into an episode -- or an hour into
        a book -- keeps their place.

        False when the engine has no device API, or refused the name (a headset
        asleep, a card another program holds, an id Windows changed). The
        remembered device is then left alone, because a setting naming a device
        you cannot hear is the split this whole area exists to close.
        """
        from quill.ui.audio.output_routing import set_engine_output_device

        if not set_engine_output_device(self.output_engine(), name):
            return False
        self._output_device = name.strip()
        return True
