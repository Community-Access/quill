"""Scribe for Documents in Quill Converter: documents as a source type (PRD 8.4).

**File > Convert Documents with Scribe for Documents...** chooses one or more
documents (only the 23 types Scribe takes) and opens the shared Convert
dialog; several go one after another under the batch exception (7.4).

* **Converter's output folder rules:** the results go where Converter's own
  conversions go -- the Output folder when one is set, otherwise a
  ``Converted`` folder beside the first document -- not a folder per document.
* **Effect recipes do not apply**, and the document jobs are not rows in the
  audio queue: they are in the shared Scribe Conversions window (File > Scribe
  for Documents > Scribe Conversions), which every QUILL app shares, while the
  audio queue stays the list the person edits (accessibility review,
  2026-11-21; PRD section 2, "Built differently").
* **A document added to the audio queue** (Add Files, a drop, Paste Files) is
  left out with one sentence for all of them that says where documents go.
* **Audio goes on as a second, chosen step:** Next Steps' "Add to the
  Converter Queue" puts the MP3, or a DAISY book's audio, in the audio queue,
  for loudness or another format. Converter says so once; focus stays where
  it was.

Results never open by themselves here: Word opens in QUILL and audio in
Media Player only from Open Result or Next Steps, so the result sentence is
never cut off by another app coming to the front.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.scribe.inputs import is_accepted
from quill.ui.scribe_app_host import AppScribeHost, AppScribeMixin, elsewhere_steps

__all__ = ["ConverterScribeHost", "ConverterScribeMixin", "left_out_note"]

_TITLE = "Quill Converter"
_MENU_PATH = "File, Convert Documents with Scribe for Documents"


def left_out_note(skipped: list[Path]) -> str:
    """What add_paths says about the files it left out, in one sentence (8.4)."""
    if not skipped:
        return ""
    documents = [path for path in skipped if is_accepted(path)]
    others = len(skipped) - len(documents)
    note = f" {others} not a media file, left out." if others else ""
    if len(documents) == 1:
        note += f" {documents[0].name} is a document. To convert it, use {_MENU_PATH}."
    elif documents:
        names = ", ".join(path.name for path in documents)
        note += (
            f" {len(documents)} files are documents: {names}. To convert them, use {_MENU_PATH}."
        )
    return note


def daisy_audio(path: Path) -> list[Path]:
    """The audio files of a DAISY book (its zip unpacked beside it), in order."""
    from quill.core.scribe.results import daisy_entry

    entry = daisy_entry(path)
    if entry is None:
        return []
    return sorted(p for p in entry.parent.rglob("*") if p.suffix.lower() in (".mp3", ".wav"))


class ConverterScribeHost(AppScribeHost):
    """Converter's side: audio can go on into its own queue."""

    def scribe_next_steps(self, job: Any, ready: dict[str, Path]) -> list[tuple[str, Any]]:
        from quill.core.scribe.model import format_label

        steps: list[tuple[str, Any]] = []
        for format_id in ("mp3", "daisy"):
            if format_id in ready:

                def add(f: str = format_id, path: Path = ready[format_id]) -> None:
                    files = [path] if f == "mp3" else daisy_audio(path)
                    self._owner._scribe_add_to_queue(files, job.display_name)

                steps.append((f"Add to the Converter Queue ({format_label(format_id)})", add))
        return steps + elsewhere_steps(job, ready, self.scribe_announce)


class ConverterScribeMixin(AppScribeMixin):
    """File > Convert Documents with Scribe for Documents..., and the submenu."""

    scribe_app_name = _TITLE

    def _scribe_make_host(self) -> Any:
        return ConverterScribeHost(self, _TITLE)

    def scribe_convert_documents(self) -> None:
        controller = self._scribe()
        if not controller.check_available():
            return
        paths = self._scribe_pick(multiple=True)
        if not paths:
            return
        typed = self._dest.GetValue().strip()  # type: ignore[attr-defined]
        from quill.core.audio.convert import default_destination

        folder = Path(typed) if typed else default_destination(paths[0])
        controller.convert_files(paths, open_as="converter", folder=str(folder))

    def _scribe_left_out(self, skipped: list[Path]) -> str:
        return left_out_note(skipped)

    def _scribe_add_to_queue(self, files: list[Path], name: str) -> None:
        """Next Steps' Add to the Converter Queue: once said, focus left alone."""
        if not files:
            self._announce(f"{name} has no audio to add.")  # type: ignore[attr-defined]
            return
        before = len(self._entries)  # type: ignore[attr-defined]
        self.add_paths(files, announce=False)  # type: ignore[attr-defined]
        added = len(self._entries) - before  # type: ignore[attr-defined]
        total = len(self._entries)  # type: ignore[attr-defined]
        what = files[0].name if len(files) == 1 else f"{added} audio files from {name}"
        if not added:
            self._announce(f"{what} is already in the Converter queue.")  # type: ignore[attr-defined]
            return
        self._announce(f"{what} added to the Converter queue, {total} in all.")  # type: ignore[attr-defined]
