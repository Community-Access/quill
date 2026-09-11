"""QUILL's Help > Tutorials..., as a mixin.

In its own module rather than in ``main_frame.py``, because that file is the
largest in the repo and GATE-11's rule is extract, never rebaseline. The lessons
themselves are :mod:`quill.core.quill_tutorials` and the window is shared with
Quill Radio, QUILL Cast and Quill Weather.

Radio's lessons are here too, because QUILL's Internet Radio registers a
``radio.tutorials`` palette command (``quill/ui/radio/palette_commands.py``) and
reads the handler off the frame. The handler only ever existed on the standalone
Radio app, so QUILL raised ``AttributeError`` building its command table and
never reached a window -- a whole-app startup crash from a command nobody had
run yet.
"""

from __future__ import annotations


class TutorialsMixin:
    """Opens QUILL's guided lessons in the shared Tutorials window."""

    def open_quill_tutorials(self, slug: str = "") -> None:
        """Help > Tutorials...: the guided lessons, in their own window.

        *slug* opens straight into one lesson, which is how a surface can
        offer "teach me this" without making somebody find it in the contents
        first.
        """
        from quill.ui.quill_tutorials import open_tutorials

        open_tutorials(self, slug=slug)

    def open_radio_tutorials(self, slug: str = "") -> None:
        """Internet Radio's guided lessons, opened from inside QUILL.

        The same book and the same window the standalone Quill Radio opens;
        ``quill/ui/radio/tutorials.py`` is shared code, not the app's.
        """
        from quill.ui.radio.tutorials import open_tutorials

        open_tutorials(self, slug=slug)
