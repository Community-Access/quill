"""Read while it converts: QUILL's streaming Scribe tab (PRD 8.1.3), a MainFrame mixin.

When a QUILL conversion asks for Accessible HTML and the person ticked "Read
while it converts", QUILL opens a new read-only tab, "<stem> (Scribe,
converting)", and fills it from Scribe's free ``html_stream`` preview.

* **Only complete blocks are added** -- whole paragraphs, headings, list items
  (:class:`quill.core.scribe.stream.BlockAssembler`) -- never a raw chunk, so a
  half-built line never changes under the caret or on the braille line.
* **At the end, without moving the caret, and never announced** (FUX-06). On
  the RichEdit surface the text goes in through a TOM range at the end of the
  story, which does not touch the selection; elsewhere the selection is put
  back exactly. Whether a screen reader reports a caret event then is an
  acceptance check (docs/qa/screen-reader-checks-2026-10.md).
* **The tab's name says whether more is coming**: "(Scribe, converting)",
  then "(Scribe, complete)" or "(Scribe, incomplete)". The rename is not
  spoken: the job's one result sentence says the tab is complete (7.4a), and
  an error sentence is the one message when it fails partway.
* **Tools > Scribe for Documents > Replace with Finished Document** swaps in
  the finished Word or HTML and keeps the reading place at the same block,
  matched by its words rather than its index, because the finished document
  may add a title or picture descriptions. It is the person's own command, so
  it says one short sentence.

Chunks reach only the app running the job (the runner-lock holder). When
another QUILL app runs it, the tab still follows the job's state from the
shared queue and, when the job is done, fills with the finished text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.scribe.stream import BlockAssembler, block_at, block_lines, offset_of_block

#: How often a tab whose job another app runs looks at the shared queue.
_POLL_MS = 3000
_STATES = {"converting": "converting", "complete": "complete", "incomplete": "incomplete"}


@dataclass
class _Stream:
    job_id: str
    stem: str
    tab: Any
    assembler: BlockAssembler = field(default_factory=BlockAssembler)
    state: str = "converting"
    got_text: bool = False
    finished_path: str = ""
    timer: Any = None


def tab_name(stem: str, state: str) -> str:
    """``"Notes (Scribe, converting)"``; ``"Notes (Scribe)"`` once replaced."""
    return f"{stem} (Scribe, {state})" if state else f"{stem} (Scribe)"


class ScribeStreamMixin:
    """The streaming tab and Replace with Finished Document."""

    def _scribe_stream_table(self) -> dict[str, _Stream]:
        table: dict[str, _Stream] | None = getattr(self, "_scribe_stream_tabs", None)
        if table is None:
            table = {}
            self._scribe_stream_tabs = table
        return table

    # -- opening ------------------------------------------------------------

    def _scribe_open_stream_tab(self, job: Any) -> None:
        """A new, read-only, unsaved tab that the stream fills (8.1.3)."""
        from quill.core.document import Document

        stem = Path(job.file_name).stem or job.title or "Scribe document"
        document = Document(text="", path=None, modified=False)
        document.source_metadata["display_name"] = tab_name(stem, "converting")
        document.source_metadata["read_only_guard"] = True
        document.source_metadata["scribe_job"] = job.id
        self._clear_empty_workspace_state()  # type: ignore[attr-defined]
        index = self._create_document_tab(document, select=True)  # type: ignore[attr-defined]
        tab = self._document_tabs[index]  # type: ignore[attr-defined]
        getattr(tab.editor, "SetEditable", lambda _v: None)(False)
        stream = _Stream(job_id=job.id, stem=stem, tab=tab)
        self._scribe_stream_table()[job.id] = stream
        controller = self._scribe()  # type: ignore[attr-defined]
        controller.add_chunk_listener(job.id, lambda text: self._scribe_stream_chunk(job.id, text))
        controller.add_job_listener(job.id, lambda kind, j: self._scribe_stream_event(kind, j))
        self._scribe_stream_poll_later(stream)

    def _scribe_stream_poll_later(self, stream: _Stream) -> None:
        import wx

        stream.timer = wx.CallLater(_POLL_MS, self._scribe_stream_poll, stream.job_id)

    def _scribe_stream_poll(self, job_id: str) -> None:
        """For a job another app runs: follow its state in the shared queue."""
        stream = self._scribe_stream_table().get(job_id)
        if stream is None or not self._scribe_stream_alive(stream):
            return
        from quill.core.scribe import queue as q

        try:
            job = self._scribe().queue.get(job_id)  # type: ignore[attr-defined]
        except (OSError, TimeoutError):
            job = None
        if job is not None and job.state in q.FINISHED:
            self._scribe_stream_event("done" if job.state == q.DONE else "error", job)
            return
        self._scribe_stream_poll_later(stream)

    def _scribe_stream_alive(self, stream: _Stream) -> bool:
        tabs = getattr(self, "_document_tabs", [])
        if stream.tab in tabs:
            return True
        self._scribe_stream_table().pop(stream.job_id, None)  # its tab was closed
        return False

    # -- filling ------------------------------------------------------------

    def _scribe_stream_chunk(self, job_id: str, text: str) -> None:
        stream = self._scribe_stream_table().get(job_id)
        if stream is None or stream.state != "converting" or not self._scribe_stream_alive(stream):
            return
        self._scribe_stream_add(stream, stream.assembler.push(text))

    def _scribe_stream_add(self, stream: _Stream, blocks: list[str]) -> None:
        if not blocks:
            return
        editor = stream.tab.editor
        text = block_lines(blocks, after_text=bool(editor.GetValue()))
        append_quietly(editor, text)
        stream.got_text = True
        document = stream.tab.document
        document.set_text(editor.GetValue())
        document.modified = False  # nothing of the person's to lose; the result is saved

    def _scribe_stream_event(self, kind: str, job: Any) -> None:
        """``stream_done``, ``done`` or ``error`` for a streaming job: rename, silently."""
        stream = self._scribe_stream_table().get(job.id)
        if stream is None or not self._scribe_stream_alive(stream):
            return
        if kind == "stream_done" and stream.state == "converting":
            self._scribe_stream_add(stream, stream.assembler.finish())
            self._scribe_stream_rename(stream, "complete")
        elif kind == "done":
            if stream.state == "converting":
                self._scribe_stream_add(stream, stream.assembler.finish())
            stream.finished_path = _finished_output(job)
            if not stream.got_text and stream.finished_path:
                # Another app ran it, so no chunk came: read the finished text.
                self._scribe_stream_fill_finished(stream)
            self._scribe_stream_rename(stream, "complete")
        elif kind == "error" and stream.state == "converting":
            self._scribe_stream_add(stream, stream.assembler.finish())
            self._scribe_stream_rename(stream, "incomplete")

    def _scribe_stream_rename(self, stream: _Stream, state: str) -> None:
        stream.state = state
        name = tab_name(stream.stem, _STATES.get(state, ""))
        stream.tab.document.source_metadata["display_name"] = name
        tabs = getattr(self, "_document_tabs", [])
        if stream.tab in tabs:
            self._set_tab_page_text(tabs.index(stream.tab), name)  # type: ignore[attr-defined]
            if getattr(self, "document", None) is stream.tab.document:
                self._refresh_title()  # type: ignore[attr-defined]

    def _scribe_stream_fill_finished(self, stream: _Stream) -> None:
        text = _read_text(Path(stream.finished_path))
        if text:
            append_quietly(stream.tab.editor, text)
            stream.tab.document.set_text(stream.tab.editor.GetValue())
            stream.tab.document.modified = False
            stream.got_text = True

    # -- the host's part of the result sentence ------------------------------

    def _scribe_stream_finished_phrase(self, job: Any) -> str:
        stream = self._scribe_stream_table().get(job.id)
        if stream is None or not self._scribe_stream_alive(stream):
            return ""
        self._scribe_stream_event("done", job)
        return (
            f"{stream.stem} is complete in its tab; Replace with Finished Document, in Tools, "
            "swaps in the finished one"
        )

    # -- Replace with Finished Document --------------------------------------

    def scribe_replace_finished(self) -> None:
        """Tools > Scribe for Documents > Replace with Finished Document (8.1.3)."""
        document = getattr(self, "document", None)
        job_id = str(getattr(document, "source_metadata", {}).get("scribe_job", "") or "")
        stream = self._scribe_stream_table().get(job_id) if job_id else None
        if stream is None:
            self._announce(  # type: ignore[attr-defined]
                "Replace with Finished Document works in a tab that is reading a Scribe "
                "for Documents conversion."
            )
            return
        if not stream.finished_path:
            job = self._scribe().queue.get(job_id)  # type: ignore[attr-defined]
            stream.finished_path = _finished_output(job) if job is not None else ""
        text = _read_text(Path(stream.finished_path)) if stream.finished_path else ""
        if not text:
            self._announce("The finished document is not ready yet.")  # type: ignore[attr-defined]
            return
        editor = stream.tab.editor
        caret = editor.GetInsertionPoint()
        anchor = block_at(editor.GetValue(), caret)
        getattr(editor, "SetEditable", lambda _v: None)(True)
        editor.ChangeValue(text)
        editor.SetInsertionPoint(offset_of_block(text, anchor))
        stream.tab.document.set_text(text)
        stream.tab.document.modified = True  # new, unsaved text, as an import is
        stream.tab.document.source_metadata["read_only_guard"] = False
        stream.tab.document.source_metadata.pop("scribe_job", None)
        self._scribe_stream_rename(stream, "")
        self._scribe_stream_table().pop(job_id, None)
        self._announce("Replaced with the finished document.")  # type: ignore[attr-defined]


def _finished_output(job: Any) -> str:
    """The finished document to swap in: Word first, then the HTML."""
    for format_id in ("docx", "html", "epub"):
        path = str(getattr(job, "outputs", {}).get(format_id, "") or "")
        if path and Path(path).exists():
            return path
    return ""


def _read_text(path: Path) -> str:
    try:
        from quill.io.docconvert import convert_document

        return str(convert_document(path).text)
    except Exception:  # noqa: BLE001 - the stream text stays; nothing is lost
        return ""


def append_quietly(editor: Any, text: str) -> None:
    """Add *text* at the end of *editor* without moving the caret or selection.

    The RichEdit surface takes it through a TOM range at the end of the story,
    which leaves the selection alone. Anything else appends and puts the
    selection back exactly. A read-only editor is made writable only if the
    first way is refused, and only for the moment of the append.
    """
    if not text:
        return
    hwnd = getattr(editor, "hwnd", None)
    if callable(hwnd):
        try:
            from quill.ui.richedit_rtf_surface import _get_text_document

            story = _get_text_document(hwnd())
            end = editor._story_end(story)
            story.Range(end, end).Text = text
            return
        except Exception:  # noqa: BLE001 - fall back to the plain append below
            pass
    start, stop = editor.GetSelection()
    editable = getattr(editor, "IsEditable", lambda: True)()
    if not editable:
        editor.SetEditable(True)
    try:
        editor.AppendText(text)
        editor.SetSelection(start, stop)
    finally:
        if not editable:
            editor.SetEditable(False)


__all__ = ["ScribeStreamMixin", "append_quietly", "tab_name"]
