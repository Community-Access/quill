"""Start and Stop Watching for Changes in QUILL Studio (codex.md decision 25).

**Start Watching for Changes** (Ctrl+F9, AI menu) watches the capture target
Studio already knows -- the last target chosen in Capture screen, which Repeat
Last Selected Target uses -- or, when none was chosen, the whole desktop with
Studio's own windows kept out of the picture while the watch runs. It looks
every few seconds on this computer; when the picture changes, OCR on this
computer says how if it can, and only otherwise is the AI in use asked, at most
once a minute and 30 times a watch. **Stop Watching for Changes**
(Ctrl+Shift+F9) ends it, and so does closing Studio.

The timer, the worker and the words are the shared
:mod:`quill.ui.change_watch_controller`; the rules are
:mod:`quill.core.ai.change_watch`.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

__all__ = ["StudioWatchMixin"]


class StudioWatchMixin:
    """The two watch commands. Mixed in through ``StudioAiMixin``."""

    def cmd_studio_watch_start(self) -> None:
        """Start Watching for Changes (Ctrl+F9): a foreground watch, said and brailled."""
        from quill.ui.change_watch_controller import controller_for

        controller = controller_for(self)
        target, subject = self._studio_watch_target()
        controller.request_start(
            subject=subject,
            grab=lambda: _grab(target),
            refusal=lambda: "" if target is not None else _NO_TARGET,
            on_start=lambda: self._studio_watch_hide_self(target, True),
            on_end=lambda: self._studio_watch_hide_self(target, False),
            stop_key=self._studio_watch_stop_key(),
        )

    def cmd_studio_watch_stop(self) -> None:
        """Stop Watching for Changes (Ctrl+Shift+F9)."""
        from quill.ui.change_watch_controller import controller_for

        controller_for(self).stop()

    def _studio_watch_stop_key(self) -> str:
        try:
            return str(self._binding_for("studio.ai_watch_stop") or "")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - no keymap names no key
            return ""

    def _studio_watch_target(self) -> tuple[Any, str]:
        """``(capture target, subject)``: the chosen target, or the whole desktop."""
        recipe = getattr(self, "_capture_recipe", None)
        if recipe:
            target = recipe[0]
            label = str(getattr(target, "friendly_label", "") or "the chosen target")
            return target, label
        try:
            from quill.platform.windows.studio_capture import (
                desktop_target,
                display_targets,
                physical_pixels,
            )

            with physical_pixels():
                return desktop_target(display_targets()), "the screen"
        except Exception:  # noqa: BLE001 - no desktop here means nothing to watch
            return None, ""

    def _studio_watch_hide_self(self, target: Any, hide: bool) -> None:
        """Keep Studio out of a desktop watch; a recording in progress owns this."""
        if target is None or getattr(target, "window_handle", 0):
            return  # a window is rendered on its own: Studio is never in it
        if getattr(self, "_demo", None) is not None:
            return
        exclude = getattr(self, "_exclude_studio_windows", None)
        if callable(exclude):
            exclude(hide)


_NO_TARGET = "There is nothing to watch: no screen could be found. Choose one in Capture screen."


def _grab(target: Any) -> bytes | None:
    """One picture of *target*, taken on this computer and not kept."""
    from quill.platform.windows.studio_capture import capture_target

    folder = Path(tempfile.mkdtemp(prefix="quill-studio-watch-"))
    try:
        evidence = capture_target(folder, target)
        return Path(evidence.path).read_bytes()
    finally:
        shutil.rmtree(folder, ignore_errors=True)
