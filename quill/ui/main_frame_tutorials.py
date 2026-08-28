"""QUILL's Help > Tutorials..., as a mixin.

One method, in its own module rather than in ``main_frame.py``, because that
file is the largest in the repo and GATE-11's rule is extract, never
rebaseline. The lessons themselves are :mod:`quill.core.quill_tutorials` and
the window is shared with Quill Radio, QUILL Cast and Quill Weather.
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
