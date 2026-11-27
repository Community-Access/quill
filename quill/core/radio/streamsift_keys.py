"""The Quill Radio keys that came with the ideas from StreamSift.

StreamSift is Andre Louis's screen-reader-first stream finder
(https://github.com/OnjLouis/StreamSift, MIT); the ideas are re-implemented in
QUILL's own code. The keys live here, apart from ``app_keymaps.py``, for the
same reason the song-mark and dial keys do: that table is at its size budget,
and a set of keys that arrive together is easier to review as one list.

A chord is bound in :data:`quill.core.app_keymaps.APP_KEYMAPS` ``["radio"]``
only, because these are app keys. In QUILL the same commands sit in the Internet
Radio menu with the Alt route the menu adds itself, and in the Command Palette.
"""

from __future__ import annotations

__all__ = ["STREAMSIFT_KEYS"]

STREAMSIFT_KEYS: dict[str, str] = {
    # Play Random Station: O, as in rand-O-m: every nearer letter was taken, which a test of the
    # real Radio menu bar showed on 2026-11-27 (Ctrl+Alt+M and Ctrl+Alt+K are Help).
    "radio.play_random": "Ctrl+Shift+O",
    # Play Random Favorite: one of two three-modifier letters left (R is the
    # system-wide show and hide key).
    "radio.play_random_favorite": "Ctrl+Alt+Shift+Q",
}
