from __future__ import annotations

from pathlib import Path


def _publishing_tools_source() -> str:
    return Path("quill/ui/publishing_tools.py").read_text(encoding="utf-8")


def _schedule_dialog_source() -> str:
    source = _publishing_tools_source()
    start = source.index("class SchedulePublishDialog")
    return source[start:]


def test_schedule_dialog_controls_set_accessible_names() -> None:
    body = _schedule_dialog_source()
    assert 'self.content_kind.SetName("Content type")' in body
    assert 'self.date.SetName("Publish date (YYYY-MM-DD)")' in body
    assert 'self.time.SetName("Publish time (24-hour HH:MM)")' in body
    assert 'self.timezone.SetName("Time zone")' in body


def test_schedule_dialog_labels_are_immediately_paired_with_controls() -> None:
    body = _schedule_dialog_source()
    assert "wx.FlexGridSizer(0, 2, 8, 8)" in body
    assert "form.AddGrowableCol(1, 1)" in body
    assert 'self.content_kind_caption = wx.StaticText(panel, label="Content type")' in body
    assert "add_row(self.content_kind_caption, self.content_kind)" in body
    assert 'self.date_caption = wx.StaticText(panel, label="Publish date (YYYY-MM-DD)")' in body
    assert "add_row(self.date_caption, self.date)" in body
    assert 'self.time_caption = wx.StaticText(panel, label="Publish time (24-hour HH:MM)")' in body
    assert "add_row(self.time_caption, self.time)" in body
    assert 'self.timezone_caption = wx.StaticText(panel, label="Time zone")' in body
    assert "add_row(self.timezone_caption, self.timezone)" in body


def test_schedule_dialog_content_kind_control_depends_on_fixed_content_kind() -> None:
    body = _schedule_dialog_source()
    assert "if fixed_content_kind:" in body
    assert "self.content_kind: object = wx.StaticText(" in body
    assert "self.content_kind = wx.Choice(" in body


def test_schedule_dialog_sets_initial_focus() -> None:
    body = _schedule_dialog_source()
    assert "self.content_kind.SetFocus()" in body


def test_schedule_dialog_uses_modal_contract() -> None:
    body = _schedule_dialog_source()
    assert "apply_modal_ids(" in body
    assert "show_modal_dialog(" in body
    assert ".ShowModal()" not in body


def test_schedule_dialog_revalidates_instead_of_closing_on_bad_input() -> None:
    body = _schedule_dialog_source()
    assert "while True:" in body
    assert "validate_scheduled_publish_time(scheduled_at)" in body
    assert "show_message_box(" in body


def test_schedule_dialog_defaults_timezone_to_utc() -> None:
    body = _schedule_dialog_source()
    assert '_TIMEZONE_CHOICES.index("UTC")' in body


def test_schedule_dialog_uses_plain_language_intro() -> None:
    source = _publishing_tools_source()
    assert "Choose when this content should publish." in source
