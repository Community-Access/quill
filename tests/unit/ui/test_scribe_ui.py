"""Scribe for Documents' shared UI and QUILL's entry points, behaviourally.

Consent (nothing is queued without Send and Convert), Safe Mode and a build
with no client ID (nothing is queued, the reason is said), what the holding
app says and what a non-holding app keeps silent, the convert dialog's parts,
the Conversions on This Computer window updating rows in place, and every QUILL entry
point reaching the shared controller with the right formats.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core import scribe
from quill.core.scribe import queue as q
from quill.core.scribe.model import ScribeSettings
from tests.unit.core.scribe.fake_scribe import BASE, FakeScribe, StaticTokens

pytestmark = pytest.mark.usefixtures("wx_session_app")


class Host:
    app_name = "QUILL"

    def __init__(self) -> None:
        self.said: list[str] = []
        self.opened: list[tuple[str, Path]] = []
        self.front = True

    def scribe_parent(self) -> Any:
        return None

    def scribe_announce(self, text: str) -> None:
        self.said.append(text)

    def scribe_in_front(self) -> bool:
        return self.front

    def scribe_has_sound(self, _event: str) -> bool:
        """No sounds here, whatever another test left in the sound manager: a
        "Play a sound" moment is then spoken (the family rule), so these tests
        hear the result sentences. test_scribe_feedback_routing.py has sounds."""
        return False

    def scribe_open_result(self, job: q.Job, format_id: str, path: Path) -> str:
        self.opened.append((format_id, path))
        return "Word is open in QUILL"


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(scribe, "CLIENT_ID", "test-client")
    return tmp_path


@pytest.fixture
def controller(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    from quill.ui.scribe_controller import ScribeController

    server = FakeScribe()
    made = ScribeController(Host())
    made._queue = q.FamilyQueue(isolated / "data" / "scribe")

    class Session:
        base_url = BASE

        def is_signed_in(self) -> bool:
            return True

        def access_token(self) -> str:
            return server.access_token

        def force_refresh(self) -> str:
            return server.access_token

    made._session = Session()
    from quill.core.scribe.client import ScribeClient

    monkeypatch.setattr(
        made,
        "client",
        lambda: ScribeClient(StaticTokens(server), base_url=BASE, transport=server.transport),
    )
    monkeypatch.setattr(made, "ensure_service", lambda: None)
    made.server = server
    return made


class Choice:
    formats = ["docx", "brf"]
    settings = ScribeSettings()
    save_as_defaults = False
    password = ""


def _fake_dialog(monkeypatch: pytest.MonkeyPatch, answer: int) -> list[dict]:
    import wx

    import quill.ui.dialog_contract as contract
    import quill.ui.scribe_convert_dialog as convert

    made: list[dict] = []

    class Dialog:
        def __init__(self, *_a: Any, **kw: Any) -> None:
            made.append(kw)

        def result(self) -> Choice:
            return Choice()

        def Destroy(self) -> None:  # noqa: N802 - wx API
            pass

    monkeypatch.setattr(convert, "ScribeConvertDialog", Dialog)
    monkeypatch.setattr(contract, "show_modal_dialog", lambda *_a, **_k: answer)
    assert wx.ID_OK != wx.ID_CANCEL
    return made


def _source(tmp_path: Path, name: str = "Notes.pdf") -> Path:
    path = tmp_path / name
    path.write_bytes(b"%PDF-1.4 fake")
    return path


# ------------------------------------------------------------------ consent


def test_nothing_is_queued_without_send_and_convert(
    controller: Any, isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    shown = _fake_dialog(monkeypatch, wx.ID_CANCEL)
    assert controller.convert_files([_source(isolated)]) == []
    assert shown and controller.queue.jobs() == []
    assert controller.server.requests == []  # and nothing went to Scribe


def test_send_and_convert_queues_one_job_per_file(
    controller: Any, isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    _fake_dialog(monkeypatch, wx.ID_OK)
    jobs = controller.convert_files([_source(isolated), _source(isolated, "b.pdf")])
    queued = controller.queue.jobs()
    assert [j.state for j in queued] == [q.QUEUED, q.QUEUED]  # one after another, unasked
    assert queued[0].batch and queued[0].batch == queued[1].batch
    assert jobs[0].formats == ["docx", "brf"]
    assert controller.options().last_formats == ["docx", "brf"]
    assert controller.options().first_upload_done


def test_safe_mode_says_so_and_shows_nothing(
    controller: Any, isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    shown = _fake_dialog(monkeypatch, wx.ID_OK)
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    assert controller.convert_files([_source(isolated)]) == []
    assert not shown and controller.queue.jobs() == []
    assert "disabled in Safe Mode" in controller.host.said[-1]


def test_a_build_without_a_client_id_says_it_is_not_available(
    controller: Any, isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    shown = _fake_dialog(monkeypatch, wx.ID_OK)
    monkeypatch.setattr(scribe, "CLIENT_ID", "")
    monkeypatch.delenv("QUILL_SCRIBE_CLIENT_ID", raising=False)
    controller.my_documents()
    controller.open_conversions()
    assert not shown
    assert all("not available in this build of QUILL yet" in s for s in controller.host.said)


# ------------------------------------------------------------- who speaks


def _job(**kw: Any) -> q.Job:
    kw.setdefault("file_name", "Notes.pdf")
    return q.Job(formats=["docx"], **kw)


def speak_everything(controller: Any) -> None:
    """Words for every moment, everywhere: for the tests about what is said.
    By default nothing is spoken (test_scribe_feedback.py)."""
    from quill.core.scribe.feedback import EVERYWHERE, FeedbackChoices

    options = controller.options()
    options.feedback = FeedbackChoices(
        started="speech",
        stage="speech",
        finished="speech",
        failed="speech",
        stage_scope=EVERYWHERE,
    )
    controller.save_options(options)


def test_only_the_holding_app_speaks(controller: Any) -> None:
    speak_everything(controller)
    controller._service = type("S", (), {"holding": False})()
    controller._on_event("started", _job())
    assert controller.host.said == []
    controller._service.holding = True
    controller._on_event("started", _job())
    assert controller.host.said == ["Scribe for Documents: sending Notes.pdf, for Word."]


def test_each_stage_is_said_once_and_errors_name_scribe(controller: Any) -> None:
    speak_everything(controller)
    controller._service = type("S", (), {"holding": True})()
    job = _job(state=q.CONVERTING, format="docx", stage="add_image_descriptions")
    controller._on_event("changed", job)
    controller._on_event("changed", job)
    assert controller.host.said == ["Notes.pdf, adding image descriptions."]
    failed = _job(state=q.FAILED, message="The file is damaged.", error_code="QUILL-SCRIBE-FAILED")
    controller._on_event("error", failed)
    assert controller.host.said[-1] == (
        "Scribe for Documents could not convert Notes.pdf: The file is damaged."
    )
    assert "QUILL-SCRIBE" not in controller.host.said[-1]


def test_a_finished_job_is_one_sentence_and_opens_in_the_app_that_asked(
    controller: Any, isolated: Path
) -> None:
    controller._service = type("S", (), {"holding": True})()
    made = isolated / "Notes.docx"
    made.write_text("x")
    job = _job(state=q.DONE, outputs={"docx": str(made)}, folder=str(isolated))
    controller._on_event("done", job)
    assert controller.host.opened == [("docx", made)]
    assert len(controller.host.said) == 1
    assert controller.host.said[0].startswith("Scribe for Documents made Notes.docx in ")
    assert controller.host.said[0].endswith("Word is open in QUILL.")


def test_a_result_for_another_app_is_offered_not_opened(controller: Any, isolated: Path) -> None:
    controller._service = type("S", (), {"holding": True})()
    made = isolated / "Notes.docx"
    made.write_text("x")
    controller._on_event("done", _job(app="QUILL Lite", outputs={"docx": str(made)}))
    assert controller.host.opened == []
    assert controller.host.said[0].endswith("Open it from the Conversions on This Computer window.")


def test_a_job_that_needs_the_person_says_so_once(controller: Any) -> None:
    controller._service = type("S", (), {"holding": True})()
    job = _job(state=q.NEEDS_PASSWORD)
    controller._on_event("needs_you", job)
    controller._on_event("needs_you", job)
    assert controller.host.said == [
        "Notes.pdf needs its password. Open the Conversions on This Computer window to enter it."
    ]


def test_cancel_waiting_says_what_it_means(controller: Any) -> None:
    (job,) = controller.queue.add([_job()])
    controller.cancel_waiting(job.id)
    assert controller.queue.get(job.id).state == q.STOPPED
    assert "Scribe will still finish it and may use pages" in controller.host.said[-1]


# ------------------------------------------------------------- the dialog


def test_the_convert_dialog_opens_on_what_will_be_sent(controller: Any, isolated: Path) -> None:
    import wx

    from quill.ui.scribe_convert_dialog import ScribeConvertDialog

    dialog = ScribeConvertDialog(
        None,
        controller,
        paths=[_source(isolated, "tax return.pdf")],
        formats=["docx"],
        options=controller.options(),
    )
    try:
        assert wx.Window.FindFocus() in (dialog.consent, None)
        text = dialog.consent.GetValue()
        assert "will be sent to Scribe for Documents (Pneuma Solutions) and converted in" in text
        assert "Caution:" in text and "Before your first upload:" in text
        assert dialog.send.GetLabel() == "Send and Convert"
        assert not dialog.groups.boxes["braille"].GetStaticBox().IsShown()
        dialog.format_boxes["brf"].SetValue(True)
        dialog._formats_changed()
        assert dialog.groups.boxes["braille"].GetStaticBox().IsShown()
        assert "Braille" in dialog.summary.GetValue()
        assert dialog.result().formats == ["docx", "brf"]
    finally:
        dialog.Destroy()


def test_an_encrypted_pdf_asks_for_its_password_at_send(controller: Any, isolated: Path) -> None:
    from quill.ui.scribe_convert_dialog import ScribeConvertDialog

    locked = isolated / "Locked.pdf"
    locked.write_bytes(b"%PDF-1.4\ntrailer << /Encrypt 5 0 R >>")
    dialog = ScribeConvertDialog(
        None, controller, paths=[locked], formats=["docx"], options=controller.options()
    )
    try:
        assert not dialog.password.IsShown()
        dialog._on_send(None)
        assert dialog.password.IsShown() and dialog.IsModal() is False
        dialog.password.SetValue("open sesame")
        dialog.show_password.SetValue(True)
        dialog._swap_password()
        assert dialog.password_plain.GetValue() == "open sesame"
        assert dialog.result().password == "open sesame"
    finally:
        dialog.Destroy()


# ------------------------------------------------------- conversions window


def test_rows_update_in_place_and_keep_focus(controller: Any) -> None:
    from quill.ui.scribe_conversions_window import ScribeConversionsWindow

    a, b = controller.queue.add([_job(), _job(file_name="b.pdf")])
    window = ScribeConversionsWindow(None, controller)
    try:
        assert window.list.GetItemCount() == 2
        window.list.Focus(1)
        controller.queue.update(a.id, state=q.CONVERTING, stage="convert", format="docx")
        window.refresh()
        assert window.list.GetItemText(0, 2) == "Converting: Word"
        assert window.list.GetFocusedItem() == 1
        window.run("remove")
        assert window.list.GetItemCount() == 1 and controller.queue.get(b.id) is None
    finally:
        window.Destroy()


# ------------------------------------------------------ QUILL's entry points


class Frame:
    """Just enough of MainFrame for the Scribe mixin's entry points."""

    def __init__(self, path: Path) -> None:
        self.calls: list[tuple] = []
        self.document = type("D", (), {"path": path, "modified": False, "text": "Hello"})()
        self.said: list[str] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)


@pytest.fixture
def frame(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    from quill.ui.main_frame_scribe import ScribeMixin

    class Mixed(Frame, ScribeMixin):
        pass

    made = Mixed(_source(isolated, "Report.docx"))

    class Recorder:
        def check_available(self) -> bool:
            return True

        def convert_files(self, paths: list, **kw: Any) -> list:
            made.calls.append(("convert_files", [p.name for p in paths], kw))
            return []

        def __getattr__(self, name: str) -> Any:
            return lambda *a, **k: made.calls.append((name, a, k))

    monkeypatch.setattr(made, "_scribe", lambda: Recorder())
    return made


def test_export_with_scribe_sends_the_saved_document(frame: Any) -> None:
    frame.scribe_export()
    assert frame.calls == [
        (
            "convert_files",
            ["Report.docx"],
            {"app_formats": ["pdf"], "open_as": "", "title": "Report"},
        )
    ]


def test_translate_with_scribe_asks_for_braille(frame: Any) -> None:
    frame.scribe_braille()
    assert frame.calls[0][2]["app_formats"] == ["brf"]
    assert frame.calls[0][2]["open_as"] == "braille"


def test_import_with_scribe_opens_as_a_new_tab(frame: Any, isolated: Path) -> None:
    frame.scribe_import_file(_source(isolated))
    assert frame.calls == [
        ("convert_files", ["Notes.pdf"], {"app_formats": ["docx"], "open_as": "import"})
    ]


def test_a_markdown_document_goes_as_text_when_pandoc_is_missing(
    frame: Any, isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.external_tools as tools

    monkeypatch.setattr(
        tools, "get_external_tool_status", lambda _n: type("S", (), {"installed": False})()
    )
    frame.document.path = isolated / "notes.md"
    frame.document.path.write_text("# Hi")
    frame.scribe_convert_this()
    assert frame.calls[0][1] == ["notes.txt"]


def test_the_commands_go_to_the_shared_controller(frame: Any) -> None:
    for command in (
        frame.scribe_my_documents,
        frame.scribe_conversions,
        frame.scribe_status,
        frame.scribe_repeat,
        frame.scribe_account,
        frame.scribe_options,
    ):
        command()
    assert [c[0] for c in frame.calls] == [
        "my_documents",
        "open_conversions",
        "status",
        "repeat_last",
        "open_account_in_browser",
        "show_options",
    ]


def test_the_scanned_offer_falls_back_when_scribe_is_not_available(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.main_frame_scribe import ScribeMixin

    class Mixed(Frame, ScribeMixin):
        pass

    made = Mixed(_source(isolated))
    monkeypatch.setattr(scribe, "CLIENT_ID", "")
    monkeypatch.delenv("QUILL_SCRIBE_CLIENT_ID", raising=False)
    made.frame = None
    made.settings = object()
    assert made._scribe_scanned_choice(isolated / "Scan.pdf", 4) is None


def test_the_rows_land_in_their_menus(isolated: Path) -> None:
    import wx

    from quill.ui.main_frame_scribe import ROWS, ScribeMixin

    class Commands:
        def __init__(self) -> None:
            self.ids: list[str] = []

        def try_register(self, command_id: str, *_a: Any) -> bool:
            self.ids.append(command_id)
            return True

    class Mixed(Frame, ScribeMixin):
        pass

    made = Mixed(_source(isolated))
    made.frame = wx.Frame(None)
    made.commands = Commands()
    made._menu_label = lambda title, _cid: title
    bar = wx.MenuBar()
    file_menu, tools, window = wx.Menu(), wx.Menu(), wx.Menu()
    file_menu.AppendSubMenu(wx.Menu(), "&Import")
    file_menu.AppendSubMenu(wx.Menu(), "&Export")
    file_menu.AppendSeparator()
    file_menu.Append(wx.ID_EXIT, "E&xit")
    tools.AppendSubMenu(wx.Menu(), "&Braille")
    window.Append(wx.ID_ANY, "&Next Document")
    window.AppendSeparator()
    for menu, title in ((file_menu, "&File"), (tools, "&Tools"), (window, "&Window")):
        bar.Append(menu, title)
    try:
        made._place_scribe_rows(bar)
        assert made.commands.ids == [row[0] for row in ROWS]
        labels = [i.GetItemLabelText() for i in file_menu.GetMenuItems()]
        assert labels[-1] == "Exit" and "Documents in My Scribe Account..." in labels
        assert [i.GetItemLabelText() for i in window.GetMenuItems()][
            1
        ] == "Conversions on This Computer"
        submenu = tools.GetMenuItems()[-1]
        assert submenu.GetItemLabelText() == "Scribe for Documents"
        # The twelve commands and Replace with Finished Document (File has no letter left).
        assert submenu.GetSubMenu().GetMenuItemCount() == 13
    finally:
        made.frame.Destroy()


# ------------------------------------------- jobs left in flight (FUX-05)


def test_jobs_under_way_last_time_are_named_once_as_they_carry_on(
    controller: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A resumed job carried on silently: now the launch says which ones."""
    speak_everything(controller)
    started: list[bool] = []
    monkeypatch.setattr(controller, "ensure_service", lambda: started.append(True))
    controller.queue.add([
        _job(title="Chapter 3", state=q.CONVERTING, document_id="d1"),
        _job(title="Minutes", state=q.DOWNLOADING, document_id="d2"),
        _job(title="Queued only", state=q.QUEUED),
        _job(title="Old", state=q.DONE),
    ])
    controller.start_if_jobs_waiting()
    assert started == [True]
    assert controller.host.said == [
        "Scribe for Documents is finishing 2 conversions from last time: Chapter 3 and Minutes."
    ]


def test_jobs_that_cannot_run_are_said_to_wait_not_dropped(
    controller: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Safe Mode used to leave waiting jobs unmentioned; now they are named."""
    speak_everything(controller)
    started: list[bool] = []
    monkeypatch.setattr(controller, "ensure_service", lambda: started.append(True))
    controller.queue.add([_job(title="Chapter 3", state=q.UPLOADING)])
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    controller.start_if_jobs_waiting()
    assert started == []
    said = controller.host.said[-1]
    assert said.startswith(
        "1 Scribe for Documents conversion from last time is waiting: Chapter 3."
    )
    assert "disabled in Safe Mode" in said and "They are kept" in said


def test_nothing_is_said_when_another_app_runs_the_queue(
    controller: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    speak_everything(controller)
    monkeypatch.setattr(controller, "ensure_service", lambda: None)
    controller.queue.add([_job(title="Chapter 3", state=q.CONVERTING)])
    other = q.FamilyQueue(controller.queue.folder)
    assert other.try_acquire("QUILL Lite")
    controller.start_if_jobs_waiting()
    assert controller.host.said == []


def test_quill_lite_picks_up_jobs_left_in_flight_at_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """QUILL Lite never started the queue at launch, unlike QUILL."""
    from quill.apps import lite_window_scribe

    asked: list[object] = []

    class Controller:
        def start_if_jobs_waiting(self) -> None:
            asked.append(True)

    monkeypatch.setattr(lite_window_scribe, "lite_controller", lambda app: Controller())
    lite_window_scribe.start_scribe_at_launch(object())
    assert asked == [True]

    later: list[tuple] = []
    import wx

    from quill.apps.lite_recovery import LiteRecoveryMixin

    monkeypatch.setattr(wx, "CallLater", lambda ms, fn, *a: later.append((ms, fn, a)))
    app = LiteRecoveryMixin()
    app._resume_scribe_jobs()
    assert later == [(5000, lite_window_scribe.start_scribe_at_launch, (app,))]
