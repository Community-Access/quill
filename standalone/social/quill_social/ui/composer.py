"""The composer dialog (PRD 15).

An accessible, keyboard-complete composer. On focus it announces the active
accounts and privacy state (PRD 15.1). As the user types it recomputes the live
composition report -- per-network character count, thread segment count, and any
capability or accessibility problem -- and exposes it as text (PRD 15.3, 15.6).

Beyond plain text the composer exposes media attachments with alt text, a native
poll, native scheduling, and reusable templates -- every control keyboard
operable and screen-reader labelled. The three primary actions (publish now,
schedule, save draft) are plain buttons; nothing here needs a mouse.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime

import wx

from quill_social import model
from quill_social.capabilities import Capabilities
from quill_social.model import Account, Draft, Media, Poll, PollOption
from quill_social.services import composer as composer_svc
from quill_social.services import templates as templates_svc

# Extension -> media kind, so an attachment records the right ``model.Media.kind``.
_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".gifv", ".webp", ".bmp", ".heic", ".tif", ".tiff"}
_VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
_AUDIO_EXT = {".mp3", ".wav", ".ogg", ".oga", ".m4a", ".flac", ".aac"}

# Poll durations offered in the editor: visible label -> milliseconds.
_POLL_DURATIONS: list[tuple[str, int]] = [
    ("1 hour", 60 * 60 * 1000),
    ("6 hours", 6 * 60 * 60 * 1000),
    ("1 day", 24 * 60 * 60 * 1000),
    ("3 days", 3 * 24 * 60 * 60 * 1000),
    ("7 days", 7 * 24 * 60 * 60 * 1000),
]

_ONE_HOUR_MS = 60 * 60 * 1000


def media_kind_for_path(path: str) -> str:
    """Classify an attachment by file extension (image | video | audio | unknown)."""
    ext = os.path.splitext(path or "")[1].lower()
    if ext in _IMAGE_EXT:
        return "image"
    if ext in _VIDEO_EXT:
        return "video"
    if ext in _AUDIO_EXT:
        return "audio"
    return "unknown"


def schedule_to_ms(date_text: str, time_text: str) -> int | None:
    """Convert a ``YYYY-MM-DD`` date and ``HH:MM`` time (UTC) to epoch milliseconds.

    Pure and unit-testable: returns ``None`` when either field is empty or does
    not parse, so the caller can flag the schedule as incomplete rather than
    guessing a time.
    """
    date_text = (date_text or "").strip()
    time_text = (time_text or "").strip()
    dm = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", date_text)
    tm = re.match(r"^(\d{1,2}):(\d{2})$", time_text)
    if not dm or not tm:
        return None
    year, month, day = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
    hour, minute = int(tm.group(1)), int(tm.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    try:
        dt = datetime(year, month, day, hour, minute, tzinfo=UTC)
    except ValueError:
        return None
    return int(dt.timestamp() * 1000)


class ComposerDialog(wx.Dialog):
    def __init__(
        self,
        parent,
        accounts: list[Account],
        caps: dict[str, Capabilities],
        *,
        store=None,
        reply_to=None,
        quote_of: str = "",
        now_ms: int | None = None,
    ):
        title = "Reply" if reply_to else "Compose"
        super().__init__(parent, title=title,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._accounts = accounts
        self._caps = caps
        self._store = store
        self._reply_to = reply_to
        self._quote_of = quote_of
        self._now = model.now_ms() if now_ms is None else int(now_ms)

        self.result_action: str = ""
        self.result_draft: Draft | None = None
        self.result_schedule_at: int | None = None

        # Attachment records, kept in step with the media list control.
        self._media: list[Media] = []
        # Poll option texts, kept in step with the poll option list box.
        self._poll_options: list[str] = ["", ""]
        # Loaded templates (empty unless a store was provided).
        self._templates: list[templates_svc.Template] = []

        outer = wx.BoxSizer(wx.VERTICAL)

        # Target accounts.
        outer.Add(wx.StaticText(self, label="Post from these accounts:"),
                  0, wx.LEFT | wx.TOP, 8)
        self.accounts_box = wx.CheckListBox(
            self, choices=[f"{a.label} ({a.network})" for a in accounts])
        self.accounts_box.SetName("Target accounts")
        for i, a in enumerate(accounts):
            if a.is_default or len(accounts) == 1:
                self.accounts_box.Check(i, True)
        outer.Add(self.accounts_box, 0, wx.EXPAND | wx.ALL, 8)

        # Content warning.
        cw_row = wx.BoxSizer(wx.HORIZONTAL)
        cw_row.Add(wx.StaticText(self, label="Content warning:"),
                   0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.cw = wx.TextCtrl(self)
        self.cw.SetName("Content warning")
        cw_row.Add(self.cw, 1)
        outer.Add(cw_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Main editor.
        outer.Add(wx.StaticText(self, label="Post text:"), 0, wx.LEFT, 8)
        self.editor = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_PROCESS_TAB)
        self.editor.SetName("Post text")
        outer.Add(self.editor, 1, wx.EXPAND | wx.ALL, 8)

        self._build_template_row(outer)
        self._build_media_section(outer)
        self._build_poll_section(outer)
        self._build_options_row(outer)
        self._build_schedule_row(outer)

        # Live report (read-only, screen-reader reviewable).
        outer.Add(wx.StaticText(self, label="Status:"), 0, wx.LEFT, 8)
        self.report = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 90))
        self.report.SetName("Composition status")
        outer.Add(self.report, 0, wx.EXPAND | wx.ALL, 8)

        # Buttons.
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.publish_btn = wx.Button(self, label="&Publish now")
        self.schedule_btn = wx.Button(self, label="&Schedule")
        self.save_btn = wx.Button(self, label="Save &draft")
        cancel_btn = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        for b in (self.publish_btn, self.schedule_btn, self.save_btn, cancel_btn):
            btns.Add(b, 0, wx.RIGHT, 6)
        outer.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.SetSizer(outer)
        self.SetMinSize((560, 620))
        self.SetSize((640, 860))

        self.editor.Bind(wx.EVT_TEXT, lambda _e: self._refresh_report())
        self.cw.Bind(wx.EVT_TEXT, lambda _e: self._refresh_report())
        self.accounts_box.Bind(wx.EVT_CHECKLISTBOX, lambda _e: self._refresh_report())
        self.visibility.Bind(wx.EVT_CHOICE, lambda _e: self._refresh_report())
        self.thread_mode.Bind(wx.EVT_CHECKBOX, lambda _e: self._refresh_report())
        self.publish_btn.Bind(wx.EVT_BUTTON, lambda _e: self._finish("publish"))
        self.schedule_btn.Bind(wx.EVT_BUTTON, lambda _e: self._finish("schedule"))
        self.save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._finish("save"))

        self._sync_media_list()
        self._sync_poll_options()
        self._sync_poll_enabled()
        self.editor.SetFocus()
        self._refresh_report()

    # -- section builders -----------------------------------------------------

    def _build_template_row(self, outer: wx.Sizer) -> None:
        """Optional 'insert template' control, shown only when a store is given."""
        if self._store is not None:
            try:
                self._templates = [
                    templates_svc.Template.from_dict(d)
                    for d in self._store.list_documents("template")
                ]
            except Exception:  # pragma: no cover - defensive against store errors
                self._templates = []
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="Insert template:"),
                0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        choices = [t.name or "(untitled)" for t in self._templates]
        self.template_choice = wx.Choice(self, choices=choices)
        self.template_choice.SetName("Template to insert")
        if choices:
            self.template_choice.SetSelection(0)
        row.Add(self.template_choice, 1, wx.RIGHT, 6)
        self.template_btn = wx.Button(self, label="&Insert")
        self.template_btn.SetName("Insert template")
        row.Add(self.template_btn, 0)
        outer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        enabled = bool(self._templates)
        self.template_choice.Enable(enabled)
        self.template_btn.Enable(enabled)
        self.template_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_insert_template())

    def _build_media_section(self, outer: wx.Sizer) -> None:
        outer.Add(wx.StaticText(self, label="Attachments:"), 0, wx.LEFT, 8)
        self.media_list = wx.ListCtrl(
            self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(-1, 90))
        self.media_list.SetName("Attachments")
        self.media_list.InsertColumn(0, "File", width=260)
        self.media_list.InsertColumn(1, "Alt text", width=260)
        outer.Add(self.media_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.media_add_btn = wx.Button(self, label="&Add media")
        self.media_add_btn.SetName("Add media")
        self.media_alt_btn = wx.Button(self, label="Edit alt &text")
        self.media_alt_btn.SetName("Edit alt text")
        self.media_remove_btn = wx.Button(self, label="&Remove media")
        self.media_remove_btn.SetName("Remove media")
        for b in (self.media_add_btn, self.media_alt_btn, self.media_remove_btn):
            row.Add(b, 0, wx.RIGHT, 6)
        outer.Add(row, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)
        self.media_add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_add_media())
        self.media_alt_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_edit_alt())
        self.media_remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_remove_media())

    def _build_poll_section(self, outer: wx.Sizer) -> None:
        self.poll_toggle = wx.CheckBox(self, label="Add a poll")
        self.poll_toggle.SetName("Add a poll")
        outer.Add(self.poll_toggle, 0, wx.LEFT | wx.TOP, 8)
        self.poll_toggle.Bind(wx.EVT_CHECKBOX, lambda _e: self._on_poll_toggle())

        outer.Add(wx.StaticText(self, label="Poll options:"), 0, wx.LEFT, 8)
        self.poll_options_box = wx.ListBox(self, size=(-1, 70))
        self.poll_options_box.SetName("Poll options")
        outer.Add(self.poll_options_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        opt_row = wx.BoxSizer(wx.HORIZONTAL)
        opt_row.Add(wx.StaticText(self, label="Option text:"),
                    0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.poll_option_text = wx.TextCtrl(self)
        self.poll_option_text.SetName("New poll option text")
        opt_row.Add(self.poll_option_text, 1, wx.RIGHT, 6)
        self.poll_add_btn = wx.Button(self, label="Add &option")
        self.poll_add_btn.SetName("Add poll option")
        opt_row.Add(self.poll_add_btn, 0, wx.RIGHT, 6)
        self.poll_remove_btn = wx.Button(self, label="Remove o&ption")
        self.poll_remove_btn.SetName("Remove poll option")
        opt_row.Add(self.poll_remove_btn, 0)
        outer.Add(opt_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        cfg_row = wx.BoxSizer(wx.HORIZONTAL)
        self.poll_multiple = wx.CheckBox(self, label="Allow multiple choices")
        self.poll_multiple.SetName("Allow multiple choices")
        cfg_row.Add(self.poll_multiple, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        cfg_row.Add(wx.StaticText(self, label="Poll duration:"),
                    0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.poll_duration = wx.Choice(self, choices=[d[0] for d in _POLL_DURATIONS])
        self.poll_duration.SetName("Poll duration")
        self.poll_duration.SetSelection(2)  # default 1 day
        cfg_row.Add(self.poll_duration, 0)
        outer.Add(cfg_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.poll_add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_add_poll_option())
        self.poll_remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_remove_poll_option())
        self.poll_multiple.Bind(wx.EVT_CHECKBOX, lambda _e: self._refresh_report())
        self.poll_duration.Bind(wx.EVT_CHOICE, lambda _e: self._refresh_report())

    def _build_options_row(self, outer: wx.Sizer) -> None:
        opt = wx.BoxSizer(wx.HORIZONTAL)
        opt.Add(wx.StaticText(self, label="Visibility:"),
                0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.visibility = wx.Choice(
            self, choices=["public", "unlisted", "followers", "direct"])
        self.visibility.SetName("Visibility")
        self.visibility.SetSelection(0)
        opt.Add(self.visibility, 0, wx.RIGHT, 12)
        self.thread_mode = wx.CheckBox(self, label="Split into a thread")
        self.thread_mode.SetName("Split into a thread")
        opt.Add(self.thread_mode, 0, wx.ALIGN_CENTER_VERTICAL)
        outer.Add(opt, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    def _build_schedule_row(self, outer: wx.Sizer) -> None:
        default_dt = datetime.fromtimestamp(
            (self._now + _ONE_HOUR_MS) / 1000, tz=UTC)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="Schedule date (YYYY-MM-DD):"),
                0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.schedule_date = wx.TextCtrl(self, value=default_dt.strftime("%Y-%m-%d"))
        self.schedule_date.SetName("Schedule date")
        row.Add(self.schedule_date, 0, wx.RIGHT, 12)
        row.Add(wx.StaticText(self, label="Time UTC (HH:MM):"),
                0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.schedule_time = wx.TextCtrl(self, value=default_dt.strftime("%H:%M"))
        self.schedule_time.SetName("Schedule time")
        row.Add(self.schedule_time, 0)
        outer.Add(row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # -- media handlers -------------------------------------------------------

    def _on_add_media(self) -> None:
        with wx.FileDialog(
            self, "Choose media to attach",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            for path in dlg.GetPaths():
                self._media.append(
                    Media(kind=media_kind_for_path(path), local_path=path))
        self._sync_media_list()
        self._refresh_report()

    def _selected_media_index(self) -> int:
        return self.media_list.GetFirstSelected()

    def _on_edit_alt(self) -> None:
        idx = self._selected_media_index()
        if idx < 0:
            wx.MessageBox("Select an attachment first.", "Composer",
                          wx.OK | wx.ICON_INFORMATION, self)
            return
        media = self._media[idx]
        with wx.TextEntryDialog(
            self, f"Alt text for {os.path.basename(media.local_path)}",
            "Edit alt text", value=media.alt_text,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            media.alt_text = dlg.GetValue().strip()
        self._sync_media_list()
        self.media_list.Select(idx)
        self._refresh_report()

    def _on_remove_media(self) -> None:
        idx = self._selected_media_index()
        if idx < 0:
            return
        del self._media[idx]
        self._sync_media_list()
        self._refresh_report()

    def _sync_media_list(self) -> None:
        self.media_list.DeleteAllItems()
        for i, m in enumerate(self._media):
            name = os.path.basename(m.local_path) or m.local_path or m.kind
            self.media_list.InsertItem(i, name)
            alt = m.alt_text if m.has_alt else "MISSING alt text"
            self.media_list.SetItem(i, 1, alt)

    # -- poll handlers --------------------------------------------------------

    def _on_poll_toggle(self) -> None:
        self._sync_poll_enabled()
        self._refresh_report()

    def _sync_poll_enabled(self) -> None:
        on = self.poll_toggle.GetValue()
        for ctrl in (
            self.poll_options_box, self.poll_option_text, self.poll_add_btn,
            self.poll_remove_btn, self.poll_multiple, self.poll_duration,
        ):
            ctrl.Enable(on)

    def _on_add_poll_option(self) -> None:
        text = self.poll_option_text.GetValue().strip()
        if not text:
            return
        self._poll_options.append(text)
        self.poll_option_text.SetValue("")
        self._sync_poll_options()
        self._refresh_report()

    def _on_remove_poll_option(self) -> None:
        idx = self.poll_options_box.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        del self._poll_options[idx]
        self._sync_poll_options()
        self._refresh_report()

    def _sync_poll_options(self) -> None:
        self.poll_options_box.Set(self._poll_options)

    # -- template handler -----------------------------------------------------

    def _on_insert_template(self) -> None:
        idx = self.template_choice.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self._templates):
            return
        rendered = templates_svc.render(self._templates[idx], {})
        current = self.editor.GetValue()
        if current and not current.endswith("\n"):
            current += "\n"
        self.editor.SetValue(current + rendered)
        self.editor.SetInsertionPointEnd()
        self._refresh_report()

    # -- draft building -------------------------------------------------------

    def _selected_account_ids(self) -> list[str]:
        return [
            self._accounts[i].account_id
            for i in range(self.accounts_box.GetCount())
            if self.accounts_box.IsChecked(i)
        ]

    def _build_poll(self) -> Poll | None:
        if not self.poll_toggle.GetValue():
            return None
        options = [PollOption(title=t) for t in self._poll_options if t.strip()]
        dur_idx = self.poll_duration.GetSelection()
        if dur_idx == wx.NOT_FOUND:
            dur_idx = 0
        expires_at = self._now + _POLL_DURATIONS[dur_idx][1]
        return Poll(
            options=options,
            multiple=self.poll_multiple.GetValue(),
            expires_at=expires_at,
        )

    def _build_draft(self) -> Draft:
        return Draft(
            text=self.editor.GetValue(),
            targets=self._selected_account_ids(),
            visibility=self.visibility.GetStringSelection() or "public",
            content_warning=self.cw.GetValue().strip(),
            thread_mode=self.thread_mode.GetValue(),
            in_reply_to=getattr(self._reply_to, "remote_id", "") if self._reply_to else "",
            quote_of=self._quote_of,
            media=[Media.from_dict(m.to_dict()) for m in self._media],
            poll=self._build_poll(),
        )

    def _refresh_report(self) -> None:
        draft = self._build_draft()
        accounts = {a.account_id: a for a in self._accounts}
        report = composer_svc.analyze_draft(draft, accounts, self._caps)
        lines: list[str] = []
        if not draft.targets:
            lines.append("No accounts selected.")
        if draft.media:
            missing = sum(1 for m in draft.media if not m.has_alt)
            note = f"{len(draft.media)} attachment(s)"
            if missing:
                note += f", {missing} missing alt text"
            lines.append(note)
        if draft.poll:
            lines.append(f"Poll with {len(draft.poll.options)} option(s)")
        for r in report.per_network:
            head = f"{r.account_label}: {r.length}/{r.limit} characters"
            if r.segments > 1:
                head += f", {r.segments} segments"
            lines.append(head)
            for e in r.errors:
                lines.append(f"  Error: {e}")
            for w in r.warnings:
                lines.append(f"  Note: {w}")
        self.report.SetValue("\n".join(lines))

    def _finish(self, action: str) -> None:
        draft = self._build_draft()
        if not draft.targets:
            wx.MessageBox("Select at least one account.", "Composer",
                          wx.OK | wx.ICON_INFORMATION, self)
            return
        if not draft.text.strip() and not draft.media:
            wx.MessageBox("Write something first.", "Composer",
                          wx.OK | wx.ICON_INFORMATION, self)
            return
        schedule_at: int | None = None
        if action == "schedule":
            schedule_at = schedule_to_ms(
                self.schedule_date.GetValue(), self.schedule_time.GetValue())
            if schedule_at is None:
                wx.MessageBox(
                    "Enter a valid schedule date (YYYY-MM-DD) and time (HH:MM).",
                    "Composer", wx.OK | wx.ICON_INFORMATION, self)
                return
        self.result_action = action
        self.result_draft = draft
        self.result_schedule_at = schedule_at
        self.EndModal(wx.ID_OK)
