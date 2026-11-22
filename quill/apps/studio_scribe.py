"""Scribe for Documents in QUILL Studio: narration from a document (PRD 8.5).

**Studio > Narration from Scribe for Documents...** chooses one document and
opens the shared Convert dialog with MP3 audio and DAISY (text and audio)
checked; Scribe reads it aloud with the voice and speed chosen there. Studio
has no File menu, so the row is in the Studio menu (PRD section 2, "Built
differently").

When it is ready, Studio writes the DAISY book's headings into the MP3 as
chapter markers (:mod:`quill.core.scribe.narration`) **before** the one result
sentence, and the sentence says what happened: "...made Notes.mp3 and
Notes.zip in ..., with 12 chapter markers." The markers go into the file the
Scribe library records.

**It never opens by itself.** The Chapter Workbench is a modal window, and a
background job must not open a dialog (7.4a), so the sentence ends "Open it
from Scribe Conversions." Open Result and Next Steps' "Open in the Chapter
Workbench" open it on the person's command; there they edit chapters, run the
loudness check and export M4B as with any book. When it closes, focus goes back
to the window it was opened from.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.scribe_app_host import AppScribeHost, AppScribeMixin, elsewhere_steps

__all__ = ["StudioScribeHost", "StudioScribeMixin"]

_TITLE = "QUILL Studio"
NARRATION = "narration"


def _ncx_for(job: Any) -> Path | None:
    from quill.core.scribe.results import daisy_entry

    daisy = job.outputs.get("daisy") if job is not None else None
    if not daisy or not Path(daisy).exists():
        return None
    entry = daisy_entry(Path(daisy))
    return entry if entry is not None and entry.suffix.lower() == ".ncx" else None


def narration_markers(job: Any) -> str:
    """Write the markers for a narration job; the phrase for its sentence."""
    from quill.core.scribe.narration import mark_narration

    mp3 = job.outputs.get("mp3")
    if not mp3 or not Path(mp3).exists():
        return ""
    ncx = _ncx_for(job)
    if ncx is None:
        return "with no chapter markers, because there was no DAISY book to take them from"
    return mark_narration(Path(mp3), ncx).phrase


class StudioScribeHost(AppScribeHost):
    """Studio's side: a narration opens in the Chapter Workbench, on command."""

    def scribe_finish_job(self, job: Any) -> str:
        """Chapter markers first, said inside the result sentence (8.5)."""
        return narration_markers(job) if job.open_as == NARRATION else ""

    def scribe_open_result(self, job: Any, format_id: str, path: Path) -> str:
        if format_id == "mp3":
            return self._owner._scribe_open_workbench(job, path)
        if format_id == "daisy":
            return ""  # its audio is the MP3's; the book opens as the MP3
        return super().scribe_open_result(job, format_id, path)

    def scribe_next_steps(self, job: Any, ready: dict[str, Path]) -> list[tuple[str, Any]]:
        steps: list[tuple[str, Any]] = []
        if "mp3" in ready:
            steps.append((
                "Open in the Chapter Workbench",
                lambda: self._owner._scribe_open_workbench(job, ready["mp3"]),
            ))
        return steps + elsewhere_steps(job, ready, self.scribe_announce)


class StudioScribeMixin(AppScribeMixin):
    """Studio > Narration from Scribe for Documents..., and the submenu."""

    scribe_app_name = _TITLE

    def _scribe_make_host(self) -> Any:
        return StudioScribeHost(self, _TITLE)

    def scribe_narration(self) -> None:
        controller = self._scribe()
        if not controller.check_available():
            return
        paths = self._scribe_pick(multiple=False)
        if paths:
            controller.convert_files(paths, app_formats=["mp3", "daisy"], open_as=NARRATION)

    def _scribe_open_workbench(self, job: Any, path: Path) -> str:
        """Open the narration in the Chapter Workbench, after the sentence."""
        import wx

        if job is not None and job.open_as == NARRATION and job.app != _TITLE:
            narration_markers(job)  # another app finished it: mark it now (idempotent)
        back = wx.GetActiveWindow()
        focus = wx.Window.FindFocus()

        def open_it() -> None:
            self.open_book(path)  # type: ignore[attr-defined]
            for window in (back, focus):
                try:
                    if window and window is not getattr(self, "frame", None):
                        (window.Raise if window is back else window.SetFocus)()
                except RuntimeError:  # it closed while the Workbench was open
                    pass

        wx.CallLater(400, open_it)  # after the sentence, so it is not cut off
        return "The narration opens in the Chapter Workbench"
