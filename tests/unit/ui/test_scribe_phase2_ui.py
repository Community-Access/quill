"""Scribe for Documents, the rest of QUILL: the windows and QUILL's host, behaviourally.

Watch-folder jobs are silent in the controller (the watch result says them),
the streaming tab gets its chunks and its ends, Open Result skips a format
that is only saved, Next Steps (named by format, each a chosen command), the
streaming tab itself (blocks appended without moving the caret, renamed
silently, Replace with Finished Document keeping the reading place), the
watch profile's Scribe controls, the Convert dialog's Read while it converts
box, and the Preferences hub's Scribe page.
"""

# ruff: noqa: F811 - the shared fixtures are imported from test_scribe_ui and used by name
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.scribe import queue as q
from tests.unit.ui.test_scribe_ui import Host, controller, isolated  # noqa: F401

pytestmark = pytest.mark.usefixtures("wx_session_app")


def _holding(controller: Any) -> None:
    type(controller).holding = property(lambda _self: True)  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def _restore_holding() -> Any:
    from quill.ui.scribe_controller import ScribeController

    original = ScribeController.__dict__["holding"]
    yield
    ScribeController.holding = original  # type: ignore[assignment]


# ------------------------------------------------------- the controller


def test_a_watch_job_is_said_by_the_watch_folder_not_the_controller(controller: Any) -> None:
    _holding(controller)
    job = q.Job(file_name="Scan.pdf", formats=["docx"], open_as="watch", state=q.DONE)
    for kind in ("started", "changed", "done", "error", "needs_you", "busy"):
        controller._on_event(kind, job)
    assert controller.host.said == []


def test_the_streaming_tab_hears_its_chunks_and_its_ends(controller: Any) -> None:
    _holding(controller)
    heard: list[tuple[str, str]] = []
    controller.add_chunk_listener("j1", lambda text: heard.append(("chunk", text)))
    controller.add_job_listener("j1", lambda kind, job: heard.append((kind, job.id)))
    controller._on_event("chunk", q.Job(id="j1", message="<p>Hi</p>"))
    controller._on_event("stream_done", q.Job(id="j1"))
    controller._on_event("error", q.Job(id="j1", file_name="N.pdf", message="broke"))
    assert heard == [("chunk", "<p>Hi</p>"), ("stream_done", "j1"), ("error", "j1")]
    # stream_done is never spoken; the error is, once.
    assert len(controller.host.said) == 1 and "could not convert" in controller.host.said[0]


def test_a_stream_result_sentence_names_the_tab(controller: Any) -> None:
    _holding(controller)
    controller.host.scribe_stream_finished = lambda job: "Notes is complete in its tab"
    job = q.Job(
        app="QUILL", file_name="Notes.pdf", open_as="stream", state=q.DONE, formats=["html"]
    )
    controller._on_event("done", job)
    assert controller.host.said[-1].endswith("Notes is complete in its tab.")


def test_open_result_skips_a_format_that_is_only_saved(controller: Any, tmp_path: Path) -> None:
    pdf, brf = tmp_path / "N.pdf", tmp_path / "N.brf"
    pdf.write_bytes(b"x")
    brf.write_bytes(b"x")
    host = controller.host
    host.scribe_open_result = lambda job, fmt, path: "" if fmt == "pdf" else "The braille is open"
    job = q.Job(file_name="N.pdf", outputs={"pdf": str(pdf), "brf": str(brf)})
    assert controller.open_job_result(job) == "The braille is open"
    host.scribe_open_result = lambda *_a: ""
    controller.open_job_result(
        q.Job(file_name="N.pdf", outputs={"pdf": str(pdf)}, folder=str(tmp_path))
    )
    assert "was saved in" in host.said[-1]


def test_next_steps_come_from_the_app_for_finished_outputs_only(
    controller: Any, tmp_path: Path
) -> None:
    made = tmp_path / "N.docx"
    made.write_bytes(b"x")
    controller.host.scribe_next_steps = lambda job, ready: [("Step", lambda: None)] if ready else []
    assert controller.next_steps(q.Job(outputs={"docx": str(tmp_path / "gone.docx")})) == []
    assert [label for label, _ in controller.next_steps(q.Job(outputs={"docx": str(made)}))] == [
        "Step"
    ]


# -------------------------------------------------- QUILL's next steps


class _Frame:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def open_file(self, path: Path) -> None:
        self.calls.append(("open", path.name))

    def __getattr__(self, name: str) -> Any:
        return lambda *a: self.calls.append((name, a))


def test_quill_next_steps_are_named_by_format_when_there_are_several(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    from quill.ui.main_frame_scribe import QuillScribeHost

    frame = _Frame()
    host = QuillScribeHost(frame)
    ready = {f: tmp_path / f"N.{f}" for f in ("docx", "html", "brf", "mp3")}
    steps = dict(host.scribe_next_steps(q.Job(), ready))
    assert "Read Aloud with QUILL's Voices (Word)" in steps
    assert "Check Accessibility (GLOW Audit) (Accessible HTML)" in steps
    assert "Open in the Braille View" in steps and "Send to Media Player (MP3 audio)" in steps
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a: fn(*a))
    steps["Read Aloud with QUILL's Voices (Word)"]()
    assert frame.calls == [("open", "N.docx"), ("read_all", ())]
    single = dict(host.scribe_next_steps(q.Job(), {"docx": ready["docx"]}))
    assert "Summarize with Your AI..." in single  # one output: no format in the name


def test_lite_next_steps_put_the_media_player_first(tmp_path: Path) -> None:
    from quill.apps.lite_window_scribe import LiteScribeHost

    opened: list[Path] = []
    app = type("App", (), {"open_path": lambda self, p: opened.append(p), "frames": []})()
    host = LiteScribeHost(app)
    ready = {"docx": tmp_path / "N.docx", "mp3": tmp_path / "N.mp3"}
    labels = [label for label, _ in host.scribe_next_steps(q.Job(), ready)]
    assert labels == ["Send to Media Player (MP3 audio)", "Open in QUILL Lite (Word)"]
    host.scribe_next_steps(q.Job(), ready)[1][1]()
    assert opened == [ready["docx"]]
    assert host.scribe_open_result(q.Job(), "brf", tmp_path / "N.brf").endswith("QUILL Lite")
    assert host.scribe_open_result(q.Job(), "pdf", tmp_path / "N.pdf") == ""


def test_next_steps_on_an_unfinished_job_say_so(controller: Any) -> None:
    from quill.ui.scribe_conversions_window import ScribeConversionsWindow

    window = ScribeConversionsWindow(None, controller)
    try:
        window._next_steps(q.Job(file_name="Notes.pdf"))
        assert controller.host.said[-1] == "Notes.pdf has nothing made yet."
        assert "next_steps" in window.buttons
    finally:
        window.Destroy()


# ----------------------------------------------------- the streaming tab


class _Editor:
    def __init__(self) -> None:
        self.value = ""
        self.selection = (0, 0)
        self.editable = False

    def GetValue(self) -> str:  # noqa: N802 - wx API
        return self.value

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802
        return self.selection

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.selection = (start, end)

    def AppendText(self, text: str) -> None:  # noqa: N802
        assert self.editable, "appended while read-only"
        self.value += text
        self.selection = (len(self.value), len(self.value))

    def IsEditable(self) -> bool:  # noqa: N802
        return self.editable

    def SetEditable(self, value: bool) -> None:  # noqa: N802
        self.editable = value

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.selection[0]

    def SetInsertionPoint(self, at: int) -> None:  # noqa: N802
        self.selection = (at, at)

    def ChangeValue(self, text: str) -> None:  # noqa: N802
        self.value = text


def test_append_quietly_leaves_the_caret_and_read_only_alone() -> None:
    from quill.ui.main_frame_scribe_stream import append_quietly

    editor = _Editor()
    editor.value, editor.selection = "Hello", (2, 4)
    append_quietly(editor, "\n\nMore")
    assert editor.value == "Hello\n\nMore" and editor.selection == (2, 4)
    assert editor.editable is False


class _Tab:
    def __init__(self, document: Any) -> None:
        self.document = document
        self.editor = _Editor()


class _StreamFrame:
    """Just enough of MainFrame for the streaming mixin."""

    def __init__(self, controller: Any) -> None:
        self._document_tabs: list[_Tab] = []
        self.titles: dict[int, str] = {}
        self.said: list[str] = []
        self.document: Any = None
        self.controller = controller

    def _scribe(self) -> Any:
        return self.controller

    def _clear_empty_workspace_state(self) -> None:
        pass

    def _create_document_tab(self, document: Any, select: bool = True) -> int:
        self._document_tabs.append(_Tab(document))
        self.document = document
        return len(self._document_tabs) - 1

    def _set_tab_page_text(self, index: int, title: str) -> None:
        self.titles[index] = title

    def _refresh_title(self) -> None:
        pass

    def _announce(self, text: str) -> None:
        self.said.append(text)


@pytest.fixture
def stream_frame(controller: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    import wx

    from quill.ui.main_frame_scribe_stream import ScribeStreamMixin

    monkeypatch.setattr(wx, "CallLater", lambda *_a, **_k: None)

    class Mixed(_StreamFrame, ScribeStreamMixin):
        pass

    return Mixed(controller)


def test_the_stream_tab_fills_with_whole_blocks_and_renames_silently(
    stream_frame: Any, controller: Any
) -> None:
    _holding(controller)
    job = q.Job(id="s1", file_name="Notes.pdf", formats=["html"], open_as="stream")
    stream_frame._scribe_open_stream_tab(job)
    tab = stream_frame._document_tabs[0]
    assert tab.document.name == "Notes (Scribe, converting)"
    assert tab.document.source_metadata["read_only_guard"] is True
    controller._on_event("chunk", q.Job(id="s1", message="<h1>Notes</h1><p>Half"))
    assert tab.editor.value == "Notes"  # the half paragraph waits
    tab.editor.selection = (1, 1)
    controller._on_event("chunk", q.Job(id="s1", message=" done</p>"))
    assert tab.editor.value == "Notes\n\nHalf done" and tab.editor.selection == (1, 1)
    assert tab.document.modified is False
    controller._on_event("stream_done", q.Job(id="s1"))
    assert stream_frame.titles[0] == "Notes (Scribe, complete)"
    assert stream_frame.said == []  # the rename is never spoken


def test_a_failed_stream_keeps_its_text_and_says_incomplete(
    stream_frame: Any, controller: Any
) -> None:
    _holding(controller)
    stream_frame._scribe_open_stream_tab(q.Job(id="s2", file_name="Notes.pdf"))
    controller._on_event("chunk", q.Job(id="s2", message="<p>Some text</p>"))
    controller._on_event("error", q.Job(id="s2", file_name="Notes.pdf", message="broke"))
    assert stream_frame.titles[0] == "Notes (Scribe, incomplete)"
    assert stream_frame._document_tabs[0].editor.value == "Some text"


def test_replace_with_finished_document_keeps_the_reading_place(
    stream_frame: Any, controller: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.main_frame_scribe_stream as stream

    finished = tmp_path / "Notes.docx"
    finished.write_bytes(b"docx")
    monkeypatch.setattr(stream, "_read_text", lambda _p: "Title\n\nIntro\n\nSecond part here")
    stream_frame._scribe_open_stream_tab(q.Job(id="s3", file_name="Notes.pdf"))
    controller._on_event("chunk", q.Job(id="s3", message="<p>Intro</p><p>Second part here</p>"))
    tab = stream_frame._document_tabs[0]
    tab.editor.selection = (9, 9)  # in "Second part here"
    stream_frame._scribe_stream_event(
        "done", q.Job(id="s3", outputs={"docx": str(finished)}, state=q.DONE)
    )
    stream_frame.scribe_replace_finished()
    assert tab.editor.value.startswith("Title")
    assert tab.editor.value[tab.editor.selection[0] :].startswith("Second part")
    assert tab.document.modified is True and tab.document.name == "Notes (Scribe)"
    assert stream_frame.said == ["Replaced with the finished document."]


def test_replace_outside_a_stream_tab_says_where_it_works(stream_frame: Any) -> None:
    from quill.core.document import Document

    stream_frame.document = Document(text="plain")
    stream_frame.scribe_replace_finished()
    assert "tab that is reading a Scribe" in stream_frame.said[-1]


# --------------------------------------------------- the watch profile


def test_the_watch_profile_reads_the_consent_before_the_box_and_collects(
    isolated: Path,
) -> None:
    import wx

    from quill.ui.scribe_watch_profile import WATCH_CONSENT_TEXT, ScribeProfileControls

    dialog = wx.Dialog(None)
    try:
        root = wx.BoxSizer(wx.VERTICAL)
        controls = ScribeProfileControls(
            wx, dialog, root, {"formats": ["brf"], "settings": {"x": 1}}
        )
        order = list(dialog.GetChildren())
        assert order.index(controls.details) < order.index(controls.consent)
        assert controls.details.GetValue() == WATCH_CONSENT_TEXT
        assert "pages" in WATCH_CONSENT_TEXT and "nobody at the computer" in WATCH_CONSENT_TEXT
        problem = controls.problem()
        assert problem is not None and problem[1] is controls.consent
        controls.consent.SetValue(True)
        assert controls.problem() is None
        assert controls.collect() == {"formats": ["brf"], "consent": True, "settings": {"x": 1}}
        for check in controls.formats.values():
            check.SetValue(False)
        assert controls.problem()[1] is controls.formats["docx"]
    finally:
        dialog.Destroy()


# ---------------------------------------------------- the convert dialog


def _dialog(controller: Any, tmp_path: Path) -> Any:
    from quill.ui.scribe_convert_dialog import ScribeConvertDialog

    source = tmp_path / "Notes.pdf"
    source.write_bytes(b"%PDF-1.4")
    controller._background = lambda *_a, **_k: None
    return ScribeConvertDialog(
        None, controller, paths=[source], formats=["docx"], options=controller.options()
    )


def test_read_while_it_converts_is_offered_only_where_there_is_a_tab(
    controller: Any, isolated: Path
) -> None:
    dialog = _dialog(controller, isolated)
    try:
        assert dialog.stream is None  # this host has no streaming tab (QUILL Lite)
    finally:
        dialog.Destroy()
    controller.host.scribe_stream_started = lambda job: None
    dialog = _dialog(controller, isolated)
    try:
        assert dialog.stream is not None
        dialog.stream.SetValue(True)
        dialog._stream_changed()
        assert dialog.format_boxes["html"].GetValue()
        assert dialog.result().stream is True
    finally:
        dialog.Destroy()


def test_a_stream_choice_marks_the_job_and_opens_the_tab(controller: Any, isolated: Path) -> None:
    from quill.core.scribe.model import ScribeSettings

    opened: list[str] = []
    controller.host.scribe_stream_started = lambda job: opened.append(job.open_as)
    choice = type(
        "C",
        (),
        {
            "formats": ["html"],
            "settings": ScribeSettings(),
            "save_as_defaults": False,
            "password": "",
            "stream": True,
        },
    )()
    source = isolated / "Notes.pdf"
    source.write_bytes(b"%PDF")
    jobs = controller.queue_choice(choice, paths=[source])
    assert jobs[0].open_as == "stream" and opened == ["stream"]


def test_the_dialogs_carry_the_names_f1_looks_up(controller: Any, isolated: Path) -> None:
    dialog = _dialog(controller, isolated)
    try:
        assert dialog.GetName() == "scribe_convert_dialog"
    finally:
        dialog.Destroy()
