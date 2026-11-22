"""Scribe for Documents in Quill Media Player (PRD 8.3).

**File > Listen to a Document with Scribe for Documents...** picks one
document (only the 23 types Scribe takes), opens the shared Convert dialog
with MP3 audio and DAISY (text and audio) checked, and queues it. When it is
ready, and this Player started it and is in front, the book opens here:

* **The DAISY book wins.** Scribe writes DAISY 3 as a zip; it is unpacked
  beside itself and opened from its ``.ncx``, with its headings as chapters.
  The MP3 opens only when there is no DAISY.
* **Loaded, not playing,** so the result sentence is not talked over, and the
  sentence says how to start: "The DAISY book is open in Media Player, 12
  headings, at the start. Press Alt+A to play." The Player's own "DAISY book
  opened" is not said on this path (one sentence, FUX-04), and focus does not
  move.

Next Steps: Play in Media Player for each audio result, then Open in QUILL for
a document made with it. The Scribe for Documents submenu in File holds the
shared rows (:mod:`quill.ui.scribe_app_host`).

A thin adapter, like :mod:`quill.apps.lite_window_scribe`: no window of its own.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from quill.ui.scribe_app_host import AppScribeHost, AppScribeMixin, elsewhere_steps

__all__ = ["PlayerScribeHost", "PlayerScribeMixin", "open_daisy_zip"]

_TITLE = "Quill Media Player"
#: Play/Pause's button in the main window (``player_access_keys``: "Pl&ay").
_PLAY_KEY = "Alt+A"


def open_daisy_zip(path: Path) -> Path | None:
    """A DAISY zip's navigation file, unpacked beside it; ``None`` for any other zip.

    Only a zip that holds a DAISY navigation file is unpacked, so a zip passed
    to the Player by mistake never leaves a folder behind.
    """
    from quill.core.scribe.results import daisy_entry

    try:
        with zipfile.ZipFile(path) as archive:
            names = [name.lower() for name in archive.namelist()]
    except (OSError, zipfile.BadZipFile):
        return None
    if not any(name.endswith((".ncx", "ncc.html")) for name in names):
        return None
    return daisy_entry(path)


class PlayerScribeHost(AppScribeHost):
    """The Media Player's side: its results open in itself."""

    #: Audio opens here, in this process, so it may open by itself (7.4a).
    scribe_opens_on_its_own = True

    def scribe_open_result(self, job: Any, format_id: str, path: Path) -> str:
        """Open an MP3 or DAISY book here; anything else is a Next Step."""
        if format_id == "mp3" and self._has_daisy(job):
            return ""  # the DAISY book, with its chapters, is opened instead
        if format_id in ("mp3", "daisy"):
            return self._owner._scribe_load(format_id, path)
        return ""

    @staticmethod
    def _has_daisy(job: Any) -> bool:
        daisy = job.outputs.get("daisy") if job is not None else None
        return bool(daisy and Path(daisy).exists())

    def scribe_next_steps(self, job: Any, ready: dict[str, Path]) -> list[tuple[str, Any]]:
        from quill.core.scribe.model import format_label

        steps: list[tuple[str, Any]] = []
        for format_id in ("daisy", "mp3"):
            if format_id in ready:

                def play(f: str = format_id, path: Path = ready[format_id]) -> None:
                    said = self._owner._scribe_load(f, path)
                    if said:
                        self.scribe_announce(f"{said}.")

                steps.append((f"Play in Media Player ({format_label(format_id)})", play))
        return steps + elsewhere_steps(job, ready, self.scribe_announce, player=False)


class PlayerScribeMixin(AppScribeMixin):
    """File > Listen to a Document with Scribe for Documents..., and the submenu."""

    scribe_app_name = _TITLE

    def _scribe_make_host(self) -> Any:
        return PlayerScribeHost(self, _TITLE)

    def scribe_listen(self) -> None:
        """Listen to a Document: MP3 and DAISY checked, played here when ready."""
        controller = self._scribe()
        if not controller.check_available():
            return
        paths = self._scribe_pick(multiple=False)
        if paths:
            controller.convert_files(paths, app_formats=["mp3", "daisy"], open_as="listen")

    def _scribe_load(self, format_id: str, path: Path) -> str:
        """Load a Scribe result without playing it or moving focus; what to say."""
        if format_id == "daisy":
            entry = path if path.suffix.lower() == ".ncx" else open_daisy_zip(path)
            if entry is None or entry.suffix.lower() != ".ncx":
                return ""
            self._load_daisy(entry, quiet=True)  # type: ignore[attr-defined]
            if getattr(self, "_book_key", "") != str(entry):
                return ""
            headings = len(getattr(self, "_chapter_nodes", []))
            noun = "heading" if headings == 1 else "headings"
            return (
                f"The DAISY book is open in Media Player, {headings} {noun}, at the start. "
                f"Press {_PLAY_KEY} to play"
            )
        self._load_book(path)  # type: ignore[attr-defined]
        if getattr(self, "_book_key", "") != str(path):
            return ""
        return f"The MP3 audio is open in Media Player. Press {_PLAY_KEY} to play"
