"""Scribe for Documents' UI after Pneuma's answers of 2026-11-21 (PRD 3, 7.3, 7.4).

Files Scribe does not take are refused before the dialog with their
sentence; the convert dialog starts from the account defaults, offers only
the website's speeds and braille ranges, says "no pages used" and names an
organization's credits, and fixes the settings an earlier upload set; a
batch ends with one sentence naming what was made and what was not; and
Send Next File and the batch setting are gone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.scribe import queue as q
from quill.core.scribe.model import DocumentSummary, Output, ScribeSettings
from tests.unit.ui.test_scribe_ui import (  # noqa: F401 - fixtures used by name
    _fake_dialog,
    _source,
    controller,
    isolated,
)

pytestmark = pytest.mark.usefixtures("wx_session_app")


@pytest.fixture
def sync(controller: Any, monkeypatch: pytest.MonkeyPatch) -> Any:  # noqa: F811
    """Background requests answered at once, so the dialog's reads land in the test."""

    def run(work: Any, done: Any, failed: Any = None) -> None:
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            if failed is not None:
                failed(error)
            return
        done(result)

    monkeypatch.setattr(controller, "_background", run)
    return controller


def _dialog(controller: Any, **kw: Any) -> Any:  # noqa: F811
    from quill.ui.scribe_convert_dialog import ScribeConvertDialog

    kw.setdefault("formats", ["docx"])
    return ScribeConvertDialog(None, controller, options=controller.options(), **kw)


# ------------------------------------------------------------ inputs (3.1)


def test_a_web_page_is_refused_before_the_dialog(
    controller: Any,  # noqa: F811
    isolated: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wx

    shown = _fake_dialog(monkeypatch, wx.ID_OK)
    page = isolated / "Story.html"
    page.write_text("<p>x</p>")
    assert controller.convert_files([page]) == []
    assert not shown and controller.queue.jobs() == []
    assert controller.host.said == [
        "Story.html: Scribe for Documents does not take web pages. Save it as Word or PDF first."
    ]
    assert controller.convert_url("https://example.com/news/story.html") == []
    assert controller.server.requests == []


def test_only_the_files_scribe_takes_are_queued(
    controller: Any,  # noqa: F811
    isolated: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wx

    _fake_dialog(monkeypatch, wx.ID_OK)
    notes = isolated / "notes.md"
    notes.write_text("# x")
    shown = _fake_dialog(monkeypatch, wx.ID_OK)
    jobs = controller.convert_files([_source(isolated), notes])
    assert [j.file_name for j in jobs] == ["Notes.pdf"]
    # Not spoken (the dialog opening would cut it off): it is in the consent text.
    assert controller.host.said == []
    assert "cannot convert notes.md" in shown[-1]["refused"][0]


def test_a_refused_file_is_listed_in_what_will_be_sent(sync: Any, isolated: Path) -> None:  # noqa: F811
    dialog = _dialog(sync, paths=[_source(isolated)], refused=["Story.html: no web pages."])
    try:
        assert "Not sent: Story.html: no web pages." in dialog.consent.GetValue()
    finally:
        dialog.Destroy()


def test_the_file_picker_offers_only_what_scribe_takes() -> None:
    from quill.core.scribe.inputs import input_wildcard

    wildcard = input_wildcard()
    assert "*.djvu" in wildcard and "*.mobi" in wildcard and "*.html" not in wildcard


# ------------------------------------------------------- the dialog (7.3)


def test_the_dialog_starts_from_the_account_defaults(sync: Any, isolated: Path) -> None:  # noqa: F811
    sync.server.account_defaults = {"tts_rate": 1.5, "braille_cells_per_line": 32, "math": True}
    dialog = _dialog(sync, paths=[_source(isolated)])
    try:
        groups = dialog.groups
        assert groups.speed.GetStringSelection() == "1.5 times"
        assert groups.cells.GetValue() == 32 and groups.math.GetValue()
        assert not dialog.defaults.GetValue()  # never on unless the person ticks it
        choice = dialog.result()
        assert choice.base is not None and choice.base.tts_rate == 1.5
        assert sync.server.default_patches == []  # reading them changes nothing
    finally:
        dialog.Destroy()


def test_the_speeds_and_braille_ranges_are_the_websites(sync: Any, isolated: Path) -> None:  # noqa: F811
    dialog = _dialog(sync, paths=[_source(isolated)], formats=["brf", "mp3"])
    try:
        groups = dialog.groups
        speeds = [groups.speed.GetString(i) for i in range(groups.speed.GetCount())]
        assert speeds == [
            "0.5 times",
            "0.75 times",
            "Normal",
            "1.5 times",
            "2 times",
            "3 times (may not be faster than 2 times)",
            "4 times (may not be faster than 2 times)",
        ]
        assert (groups.cells.GetMin(), groups.cells.GetMax(), groups.cells.GetValue()) == (
            20,
            42,
            40,
        )
        assert (groups.lines.GetMin(), groups.lines.GetMax()) == (20, 30)
        groups.speed.SetSelection(6)
        assert dialog.result().settings.tts_rate == 4.0
    finally:
        dialog.Destroy()


def test_a_change_the_person_made_beats_the_late_defaults(sync: Any, isolated: Path) -> None:  # noqa: F811
    dialog = _dialog(sync, paths=[_source(isolated)])
    try:
        dialog.groups.touched = True
        assert not dialog.groups.apply(ScribeSettings(tts_rate=4.0))
    finally:
        dialog.Destroy()


def test_organization_credits_are_named_in_the_pages_line(sync: Any, isolated: Path) -> None:  # noqa: F811
    sync.server.organization_name = "Acme Library"
    sync.server.pages_remaining = 1240
    dialog = _dialog(sync, paths=[_source(isolated)])
    try:
        assert (
            dialog.pages.GetValue() == "You have 1,240 pages left, using credits from Acme Library."
        )
    finally:
        dialog.Destroy()


def test_a_document_already_in_the_account_uses_no_pages(sync: Any) -> None:  # noqa: F811
    doc = sync.server.add_document(outputs={"html": "complete", "docx": "complete"})
    existing = DocumentSummary(
        id=doc.id,
        title="Notes",
        page_count=3,
        outputs=(Output(format="html", stage="complete"), Output(format="docx", stage="complete")),
    )
    dialog = _dialog(sync, existing=existing, formats=["brf"])
    try:
        assert dialog.format_boxes["docx"].GetLabel() == "Word, already made"
        assert dialog.format_boxes["brf"].GetLabel() == "Braille (BRF), no pages used"
        assert dialog.pages.GetValue().startswith("No pages used:")
        assert "unconfirmed" not in dialog.pages.GetValue().lower()
        assert "were fixed when Notes was uploaded" in dialog.consent.GetValue()
        groups = dialog.groups
        # Hidden, not disabled (a disabled control leaves Tab), and listed instead.
        for control in (groups.language, groups.describe, groups.math, groups.large_print):
            assert not control.IsShown() and control.IsEnabled()
        assert not groups.language._quill_label.IsShown()
        assert groups.fixed.IsShown() and groups.fixed_label.IsShown()
        assert groups.fixed_label.GetLabel() == "Fi&xed when Notes was uploaded:"
        assert groups.fixed.GetValue() == (
            "Language: Detect automatically. Describe the pictures: on. Mathematics: off. "
            "Large print: off."
        )
        assert not groups.boxes["print"].GetStaticBox().IsShown()
        dialog.format_boxes["docx"].SetValue(True)
        dialog._formats_changed()  # Word would show Print: it stays hidden, it is fixed
        assert not groups.boxes["print"].GetStaticBox().IsShown()
        assert not groups.describe.IsShown()
        assert groups.speed.IsEnabled() and groups.cells.IsEnabled()
        assert dialog.send.GetLabel() == "Convert"
    finally:
        dialog.Destroy()


def test_this_apps_choices_are_remembered_as_what_differs(controller: Any) -> None:  # noqa: F811
    class Choice:
        formats = ["docx"]
        settings = ScribeSettings(tts_rate=2.0)
        save_as_defaults = False
        password = ""
        base = ScribeSettings(tts_rate=1.0)

    controller.queue_choice(Choice(), existing=None, paths=[])
    assert controller.options().last_settings == {"QUILL": {"tts_rate": 2.0}}
    Choice.save_as_defaults = True
    controller.queue_choice(Choice(), existing=None, paths=[])
    assert controller.options().last_settings == {"QUILL": {}}


# ----------------------------------------------------------- batch (7.4)


def test_the_last_file_of_a_batch_says_what_was_made_and_what_was_not(controller: Any) -> None:  # noqa: F811
    controller._service = type("S", (), {"holding": True})()
    a, b = controller.queue.add([
        q.Job(file_name="a.pdf", formats=["docx"]),
        q.Job(file_name="b.pdf", formats=["docx"]),
    ])
    controller.queue.update(a.id, state=q.DONE)
    controller._on_event("done", controller.queue.get(a.id))
    assert not any("finished 2 files" in s for s in controller.host.said)
    controller.queue.update(b.id, state=q.FAILED, message="Damaged.")
    controller._on_event("error", controller.queue.get(b.id))
    controller._on_event("error", controller.queue.get(b.id))
    summary = [s for s in controller.host.said if "finished 2 files" in s]
    assert summary == [
        "Scribe for Documents finished 2 files. Made: a.pdf. Not made: b.pdf; "
        "the Conversions on This Computer window has the details."
    ]


def test_a_refused_file_is_said_in_its_own_words(controller: Any) -> None:  # noqa: F811
    controller._service = type("S", (), {"holding": True})()
    sentence = "Big.pdf is 600 MB. Scribe for Documents takes files up to 500 MB."
    job = q.Job(file_name="Big.pdf", state=q.FAILED, message=sentence)
    job.error_code = "QUILL-SCRIBE-TOOBIG"
    controller._on_event("error", job)
    assert controller.host.said == [sentence]


def test_busy_is_said_once_with_the_minute(controller: Any) -> None:  # noqa: F811
    from tests.unit.ui.test_scribe_ui import speak_everything

    speak_everything(controller)
    controller._service = type("S", (), {"holding": True})()
    job = q.Job(file_name="Notes.pdf", state=q.BUSY)
    controller._on_event("busy", job)
    controller._on_event("busy", job)
    assert controller.host.said == [
        "Scribe for Documents asked QUILL to slow down; trying again in a minute."
    ]


def test_no_send_next_file_and_the_wait_shows_silently(controller: Any) -> None:  # noqa: F811
    from quill.ui.scribe_conversions_window import COMMANDS, ScribeConversionsWindow, job_details

    assert "send_next" not in [method for _label, method in COMMANDS]
    import time

    busy = q.Job(file_name="Notes.pdf", state=q.BUSY, not_before=1060.0)
    at = time.strftime("%H:%M:%S", time.localtime(1060.0))
    assert f"Trying again at {at}." in job_details(busy, now=1015.0)
    assert "Trying again" not in job_details(busy, now=1100.0)
    controller.queue.add([q.Job(file_name="Notes.pdf", formats=["docx"])])
    window = ScribeConversionsWindow(None, controller)
    try:
        assert "send_next" not in window.buttons
        assert controller.host.said == []
    finally:
        window.Destroy()


def test_time_left_is_units_aware_and_not_shown_after_conversion() -> None:
    from quill.core.scribe.sentences import time_left_words
    from quill.ui.scribe_conversions_window import job_details

    assert time_left_words(30) == "less than a minute left"
    assert time_left_words(551) == "about 9 minutes left"
    assert time_left_words(93780) == "about 1 day and 2 hours left"
    active = q.Job(
        file_name="Notes.pdf",
        state=q.CONVERTING,
        progress=0.8,
        eta_seconds=551,
    )
    done = q.Job(
        file_name="Notes.pdf",
        state=q.DONE,
        progress=1.0,
        eta_seconds=551,
    )
    assert "About 9 minutes left." in job_details(active)
    assert "minutes left" not in job_details(done)


def test_the_options_have_no_batch_setting(controller: Any) -> None:  # noqa: F811
    import quill.ui.scribe_options_dialog as options_dialog

    assert not hasattr(options_dialog, "BATCH_EXCEPTION_GRANTED")
    dialog = options_dialog.ScribeOptionsDialog(None, controller)
    try:
        assert not hasattr(dialog, "batch")
        texts = []
        stack = list(dialog.GetChildren())
        while stack:
            child = stack.pop()
            stack.extend(child.GetChildren())
            if child.GetClassName() == "wxTextCtrl":
                texts.append(child.GetValue())
        assert any("Mathpix" in text and "train AI" in text for text in texts)
        result = dialog.result()
        assert not hasattr(result, "batch_exception")
    finally:
        dialog.Destroy()


def test_the_options_groups_say_which_group_they_are(controller: Any) -> None:  # noqa: F811
    """Jeff, 2026-11-23: the format check boxes and the open-results choices
    read without their caption. Each now carries it as its description."""
    import sys

    import quill.ui.scribe_options_dialog as options_dialog
    from quill.ui.accessible_group import group_description

    if sys.platform != "win32":
        pytest.skip("wx.Accessible is Windows-only")
    dialog = options_dialog.ScribeOptionsDialog(None, controller)
    try:
        assert {group_description(check) for check in dialog.formats.values()} == {
            "Default formats"
        }
        buttons = dialog.open_results.buttons()
        assert [group_description(b) for b in buttons] == [
            "Open each result when it is ready"
        ] * len(buttons)
        dialog.open_results.SetSelection(1)
        assert dialog.result().open_results == options_dialog.OPEN_CHOICES[1][0]
    finally:
        dialog.Destroy()


# ------------------------------------- the corpus variants, from the dialog


def test_the_large_print_and_math_variants_come_from_the_dialogs_controls(
    sync: Any,  # noqa: F811
    isolated: Path,  # noqa: F811
) -> None:
    """Pneuma's two variants (large print with 32-cell braille; math on) are
    what the dialog's own controls send, and Scribe's email starts off even
    when the account's default is on (F8)."""
    sync.server.account_defaults = {"notify_when_complete": True}
    dialog = _dialog(sync, paths=[_source(isolated)], formats=["pdf", "docx", "brf"])
    try:
        groups = dialog.groups
        assert not groups.notify.GetValue()
        assert groups.math.GetLabel() == "&Mathematics (beta)"
        groups.large_print.SetValue(True)
        groups.cells.SetValue(32)
        groups.math.SetValue(True)
        fields = dict(dialog.result().settings.to_upload_fields())
        assert fields["document[settings][large_print]"] == "true"
        assert fields["document[settings][braille_cells_per_line]"] == "32"
        assert fields["document[settings][math]"] == "true"
        assert fields["document[settings][notify_when_complete]"] == "false"
    finally:
        dialog.Destroy()


def test_a_document_already_in_the_account_starts_with_scribes_email_off(sync: Any) -> None:  # noqa: F811
    doc = sync.server.add_document(outputs={"html": "complete"})
    doc.settings = {"notify_when_complete": True}  # the document's own, from the account
    existing = DocumentSummary(id=doc.id, title="Notes", outputs=(Output("html", "complete"),))
    dialog = _dialog(sync, existing=existing, formats=["brf"])
    try:
        assert not dialog.groups.notify.GetValue()
        assert not dialog.result().email_changed
    finally:
        dialog.Destroy()


def test_saving_account_defaults_leaves_the_email_unless_it_was_changed(
    sync: Any,  # noqa: F811
    isolated: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.scribe.client import ScribeClient
    from quill.ui import scribe_convert_settings
    from tests.unit.core.scribe.fake_scribe import BASE, StaticTokens

    # No dialect suggested from this computer's language: one would be left
    # out too (tests/unit/ui/test_scribe_voice_settings.py), and this is the email.
    monkeypatch.setattr(scribe_convert_settings, "os_language_tags", lambda: [])
    dialog = _dialog(sync, paths=[_source(isolated)], formats=["docx"])
    try:
        dialog.defaults.SetValue(True)
        unchanged = dialog.result()
        dialog.groups.notify.SetValue(True)
        changed = dialog.result()
    finally:
        dialog.Destroy()
    assert not unchanged.email_changed and changed.email_changed
    left, sent = sync.queue_choice(unchanged, paths=[_source(isolated)])[0], None
    assert left.defaults_leave_out == ["notify_when_complete"]
    sent = sync.queue_choice(changed, paths=[_source(isolated, "Other.pdf")])[0]
    assert sent.defaults_leave_out == []
    # The PATCH itself: without notify_when_complete when it was left out.
    client = ScribeClient(StaticTokens(sync.server), base_url=BASE, transport=sync.server.transport)
    client.update_default_settings(ScribeSettings(), leave_out=left.defaults_leave_out)
    client.update_default_settings(ScribeSettings(notify_when_complete=True))
    first, second = sync.server.default_patches[-2:]
    assert "notify_when_complete" not in first and second["notify_when_complete"] is True


def test_retry_says_the_stages_again(controller: Any) -> None:  # noqa: F811
    from quill.core.scribe.sentences import Speaker

    speaker = Speaker(speak_stages="always")
    job = q.Job(id="j1", file_name="Notes.pdf", state=q.CONVERTING, stage="queue", progress=0.3)
    assert speaker.on_change(job, app_in_front=True) == "Notes.pdf, waiting in Scribe's queue."
    assert speaker.once(job, "busy")
    speaker._said_stage["other"] = "x"
    speaker.forget_job("j1")
    assert speaker.on_change(job, app_in_front=True) == "Notes.pdf, waiting in Scribe's queue."
    assert speaker.once(job, "busy") and "other" in speaker._said_stage
    # Retry, on the controller, forgets the job's speech.
    controller.queue.add([q.Job(id="j2", file_name="B.pdf", state=q.FAILED)])
    controller._speaker.once(q.Job(id="j2"), "stage:B.pdf, uploading.")
    controller.wake = lambda: None
    controller.retry("j2")
    assert controller._speaker.once(q.Job(id="j2"), "stage:B.pdf, uploading.")
