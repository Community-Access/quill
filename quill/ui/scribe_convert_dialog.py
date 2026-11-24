"""Convert with Scribe for Documents: the one dialog, the same in every app (PRD 7.3).

Its parts, in tab order:

1. **What will be sent** -- a read-only multi-line field, the first control
   and focused on open, holding the consent (:mod:`quill.core.scribe.consent`):
   what goes where, the sensitive-name caution, the privacy lines on the first
   upload, the copyright notice. There is no "don't ask again".
2. **What you want back** -- a check box per format; one already made says
   ", already made", and any other format of a document already in the
   account says ", no pages used": pages are charged once per document (3.6).
3. A silent summary of the setting groups shown, then the groups themselves
   (:mod:`quill.ui.scribe_convert_settings`). Their starting values are the
   person's Scribe account defaults (``GET /api/document_settings``, read when
   the dialog opens) with this app's last choices on top; the full set goes
   with the upload. For a document already in the account they are that
   document's own settings, and the ones its upload fixed are turned off.
4. "Also save as my Scribe account defaults", off by default and never
   remembered on: account defaults change only when the person asks.
5. **Password**, only when the file needs one: QUILL sees an encrypted PDF and
   asks at Send; "Show password" swaps in a plain field (each with its own
   label) so braille and typing-echo users can check what they typed. Never
   pre-filled, saved or logged. A wrong password is caught by Scribe after the
   upload; the job then waits in Scribe Conversions with three tries.
6. **Pages** -- "This uses about x of your n pages", updated silently, and
   Buy Pages.
7. **Send and Convert** (default; "Convert" when nothing is uploaded) and Cancel.

Escape stops a playing sample without closing; otherwise it cancels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import wx
import wx.lib.scrolledpanel as scrolled

from quill.core.scribe.consent import consent_text, pages_text
from quill.core.scribe.model import FORMATS, ScribeSettings, settings_summary
from quill.ui.accessible_group import describe_group
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button


@dataclass
class ConvertChoice:
    formats: list[str]
    settings: ScribeSettings
    save_as_defaults: bool = False
    password: str = ""
    #: The account defaults the dialog started from, when they were read.
    base: ScribeSettings | None = None
    #: Read while it converts: open the streaming tab (QUILL only, 8.1.3).
    stream: bool = False
    #: The person changed "Email me when it is finished" in this dialog: only
    #: then may "Also save as my Scribe account defaults" change the account's.
    email_changed: bool = False


def pdf_needs_password(path: Path) -> bool:
    """A cheap look for an encrypted PDF: ``/Encrypt`` in its trailer (or anywhere
    in a small file). Only ever decides whether to ask; Scribe has the last word."""
    if path.suffix.lower() != ".pdf":
        return False
    try:
        with path.open("rb") as handle:
            head = handle.read(1024 * 1024)
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - 64 * 1024))
            tail = handle.read()
    except OSError:
        return False
    return b"/Encrypt" in tail or b"/Encrypt" in head


def pdf_pages(path: Path) -> int | None:
    if path.suffix.lower() != ".pdf":
        return None
    try:
        from quill.io.docconvert import _default_pdf_page_count

        count = int(_default_pdf_page_count(path))
        return count if count > 0 else None
    except Exception:  # noqa: BLE001 - an estimate only
        return None


class ScribeConvertDialog(wx.Dialog):
    def __init__(
        self,
        parent: Any,
        controller: Any,
        *,
        paths: list[Path] | None = None,
        url: str = "",
        existing: Any = None,
        formats: list[str],
        options: Any,
        refused: list[str] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title="Convert with Scribe for Documents",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.SetName("scribe_convert_dialog")  # F1 finds its topic by this name (topics.json)
        self._controller = controller
        self._paths = list(paths or [])
        self._url = url
        self._existing = existing
        self._options = options
        self._remaining: int | None = None
        self._organization = ""
        self._base: ScribeSettings | None = None
        app = controller.app_name
        ai_off = bool(getattr(controller.host, "scribe_ai_off", lambda: False)())
        self._page_counts = {str(p): c for p in self._paths if (c := pdf_pages(p))}
        self._needs_password = any(pdf_needs_password(p) for p in self._paths[:1])

        outer = wx.BoxSizer(wx.VERTICAL)
        panel = scrolled.ScrolledPanel(self, style=wx.TAB_TRAVERSAL)
        self._panel = panel
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label="&What will be sent:"), 0, wx.LEFT | wx.TOP, 6)
        self.consent = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.consent.SetMinSize(self.FromDIP(wx.Size(520, 140)))
        self.consent.SetValue(
            consent_text(
                self._paths,
                pages=self._page_counts,
                url=url,
                first_upload=not options.first_upload_done and existing is None,
                existing_title=existing.display_title if existing is not None else "",
                ai_off=ai_off,
                app_name=app,
                refused=refused or [],
            )
        )
        self.consent.SetInsertionPoint(0)
        self.consent.SetHelpText(
            "Exactly what will be sent to Scribe for Documents and where, read it again "
            "at any time. Nothing is sent until you press Send and Convert."
        )
        sizer.Add(self.consent, 0, wx.EXPAND | wx.ALL, 6)

        made = set(existing.ready_formats) if existing is not None else set()
        free = bool(existing is not None and getattr(existing, "charged", False))
        box = wx.StaticBoxSizer(wx.VERTICAL, panel, "What you want back")
        self.format_boxes: dict[str, Any] = {}
        for item in FORMATS:
            suffix = ", already made" if item.id in made else ", no pages used" if free else ""
            label = item.label + suffix
            check = wx.CheckBox(box.GetStaticBox(), label=label)
            check.SetValue(item.id in formats)
            check.SetHelpText(f"Ask Scribe for {item.label}. You can choose several.")
            check.Bind(wx.EVT_CHECKBOX, lambda _e: self._formats_changed())
            describe_group(box, check)
            box.Add(check, 0, wx.ALL, 3)
            self.format_boxes[item.id] = check
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 6)

        # Read while it converts (8.1.3): only in an app with a streaming tab,
        # and then always shown, so the tab order never changes under the person.
        self.stream: Any = None
        can_stream = callable(getattr(controller.host, "scribe_stream_started", None))
        if can_stream and existing is None and not url and len(self._paths) == 1:
            # No access key: every letter it has is taken in this dialog (GATE-14).
            self.stream = wx.CheckBox(
                panel, label="Read while it converts, in a new tab (adds Accessible HTML)"
            )
            self.stream.SetHelpText(
                f"Opens a read-only tab in {app} that fills with the text as Scribe makes it, "
                "a whole paragraph at a time, without moving your place or speaking. One file "
                "at a time. Replace with Finished Document, in Tools, Scribe for Documents, "
                "swaps in the finished one."
            )
            self.stream.Bind(wx.EVT_CHECKBOX, lambda _e: self._stream_changed())
            sizer.Add(self.stream, 0, wx.ALL, 6)

        sizer.Add(wx.StaticText(panel, label="Settings shown:"), 0, wx.LEFT | wx.TOP, 6)
        self.summary = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.summary.SetName("Settings shown")
        self.summary.SetHelpText("Which setting groups below apply to the formats you chose.")
        sizer.Add(self.summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        from quill.ui.scribe_convert_settings import SettingsGroups

        self.groups = SettingsGroups(
            panel,
            sizer,
            controller,
            options.starting_settings(None, app),
            ai_off=ai_off,
            app_name=app,
        )
        if existing is not None:
            self.groups.fix_upload_settings(existing.display_title)

        self.defaults = wx.CheckBox(
            panel,
            label=(
                "Also save as my Scribe &account defaults "
                "(changes your Scribe website settings too)"
            ),
        )
        self.defaults.SetHelpText(
            "Off: these settings are used for this conversion and remembered in "
            f"{app} only. On: Scribe's own account defaults change too."
        )
        sizer.Add(self.defaults, 0, wx.ALL, 6)

        name = self._paths[0].name if self._paths else "this document"
        self.password_label = wx.StaticText(panel, label=f"&Password for {name}:")
        self.password = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self.password.SetHelpText("Used for this one upload; never saved or logged.")
        self.password_plain_label = wx.StaticText(panel, label=f"&Password for {name}:")
        self.password_plain = wx.TextCtrl(panel)
        self.password_plain.SetHelpText("The password as plain text. Never saved or logged.")
        self.show_password = wx.CheckBox(panel, label="Sh&ow password")
        self.show_password.SetHelpText(
            "Shows the password as plain text, so you can check what you typed with braille "
            "or typing echo."
        )
        for control in (
            self.password_label,
            self.password,
            self.password_plain_label,
            self.password_plain,
            self.show_password,
        ):
            sizer.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
            control.Hide()
        self.show_password.Bind(wx.EVT_CHECKBOX, lambda _e: self._swap_password())

        sizer.Add(wx.StaticText(panel, label="Pages:"), 0, wx.LEFT | wx.TOP, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.pages = wx.TextCtrl(panel, style=wx.TE_READONLY, value=pages_text(None, None))
        self.pages.SetName("Pages")
        self.pages.SetHelpText(
            "About how many of your Scribe pages this uses, and how many you have left."
        )
        row.Add(self.pages, 1, wx.ALL, 6)
        self.buy = wx.Button(panel, label="&Buy Pages")
        self.buy.SetHelpText(
            "Opens Scribe's purchase page in your browser. QUILL never takes payment."
        )
        self.buy.Bind(wx.EVT_BUTTON, lambda _e: self._controller.buy_pages())
        row.Add(self.buy, 0, wx.ALL, 6)
        sizer.Add(row, 0, wx.EXPAND)

        panel.SetSizer(sizer)
        panel.SetupScrolling(scroll_x=False, rate_y=20)
        outer.Add(panel, 1, wx.EXPAND)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        send_label = "Convert" if existing is not None else "Send and Convert"
        self.send = wx.Button(self, wx.ID_OK, label=send_label)
        self.send.SetHelpText(
            "Convert: makes the formats from the document already in your account."
            if existing is not None
            else "Sends the file to Scribe for Documents and converts it. This is your consent."
        )
        self.send.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Closes this. Nothing is sent.")
        buttons.Add(self.send, 0, wx.ALL, 6)
        buttons.Add(cancel, 0, wx.ALL, 6)
        outer.Add(buttons, 0, wx.EXPAND)
        self.SetSizer(outer)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        size = self.FromDIP(wx.Size(620, 640))
        display = wx.Display(wx.Display.GetFromWindow(parent) if parent else 0).GetClientArea()
        self.SetSize(wx.Size(min(size.width, display.width), min(size.height, display.height)))
        self.SetMinSize(self.FromDIP(wx.Size(360, 320)))

        bind_close_button(self, cancel, modeless=False)
        self.send.Bind(wx.EVT_BUTTON, self._on_send)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self._formats_changed()
        self._refresh_pages()
        self._load_starting_values()
        self.consent.SetFocus()

    # ------------------------------------------------------------ changes

    def chosen_formats(self) -> list[str]:
        return [item.id for item in FORMATS if self.format_boxes[item.id].GetValue()]

    def _formats_changed(self) -> None:
        chosen = self.chosen_formats()
        self.summary.SetValue(settings_summary(chosen))
        focused = wx.Window.FindFocus()
        fallback = focused if focused in self.format_boxes.values() else self.format_boxes["docx"]
        self.groups.show_for(chosen, focus_fallback=fallback)
        self._show_pages()
        self._panel.Layout()
        self._panel.SetupScrolling(scroll_x=False, rate_y=20, scrollToTop=False)

    def _load_starting_values(self) -> None:
        """The account defaults (or the document's own settings), then this app's
        last choices: read in the background and put in silently (3.3)."""
        controller, existing, app = self._controller, self._existing, self._controller.app_name

        def work() -> tuple[ScribeSettings | None, ScribeSettings]:
            client = controller.client()
            if existing is not None:  # its own settings, but never Scribe's email (F8)
                own = client.get_settings(existing.id).to_dict()
                return None, ScribeSettings.from_mapping({**own, "notify_when_complete": False})
            defaults = client.default_settings()
            return defaults, self._options.starting_settings(defaults, app)

        def done(result: tuple[ScribeSettings | None, ScribeSettings]) -> None:
            try:
                if not self or self.IsBeingDeleted():
                    return
            except RuntimeError:
                return
            self._base = result[0]
            self.groups.apply(result[1])

        # If they cannot be read, the local values stay and Scribe fills the rest.
        controller._background(work, done, lambda _error: None)

    def _free(self) -> bool:
        """Every format still to make is of a document already charged (3.6)."""
        existing = self._existing
        if existing is None:
            return False
        made = set(existing.ready_formats)
        return all(f in made for f in self.chosen_formats()) or bool(
            getattr(existing, "charged", False)
        )

    def _estimate(self) -> int | None:
        if self._existing is not None:
            return 0 if self._free() else self._existing.page_count
        if self._paths and len(self._page_counts) == len(self._paths):
            return sum(self._page_counts.values())
        return None

    def _show_pages(self) -> None:
        self.pages.SetValue(
            pages_text(
                self._estimate(),
                self._remaining,
                organization=self._organization,
                free=self._free(),
            )
        )

    def _refresh_pages(self) -> None:
        self._controller._background(
            lambda: self._controller.client().account(),
            self._got_pages,
            lambda _error: None,  # the line just stays "not known"
        )

    def _got_pages(self, account: Any) -> None:
        try:
            if not self or self.IsBeingDeleted():
                return
        except RuntimeError:
            return
        self._remaining = account.pages_remaining
        self._organization = account.organization_name
        self._show_pages()

    def _on_activate(self, event: wx.ActivateEvent) -> None:
        event.Skip()
        if event.GetActive():
            self._refresh_pages()  # after Buy Pages, silently

    def _stream_changed(self) -> None:
        """Reading while it converts needs the HTML: check it, silently (the label says so)."""
        if self.stream is not None and self.stream.GetValue():
            self.format_boxes["html"].SetValue(True)
            self._formats_changed()

    # ----------------------------------------------------------- password

    def _show_password_fields(self) -> None:
        plain = self.show_password.GetValue()
        self.password_label.Show(not plain)
        self.password.Show(not plain)
        self.password_plain_label.Show(plain)
        self.password_plain.Show(plain)
        self.show_password.Show()
        self._panel.Layout()

    def _swap_password(self) -> None:
        plain = self.show_password.GetValue()
        source, target = (
            (self.password, self.password_plain) if plain else (self.password_plain, self.password)
        )
        target.SetValue(source.GetValue())
        start, end = source.GetSelection()
        target.SetSelection(start, end)
        self._show_password_fields()

    def password_value(self) -> str:
        field = self.password_plain if self.show_password.GetValue() else self.password
        return field.GetValue() if field.IsShown() else ""

    # --------------------------------------------------------------- send

    def _on_key(self, event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE and self.groups.sample_playing():
            self.groups.stop_sample()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and wx.Window.FindFocus() is self.consent:
            self._on_send(None)
            return
        event.Skip()

    def _on_send(self, _event: Any) -> None:
        if not self.chosen_formats():
            self.format_boxes["docx"].SetFocus()
            wx.CallLater(
                200,
                self._controller.host.scribe_announce,
                "Choose at least one format to get back.",
            )
            return
        if (
            self._needs_password
            and not self.password.IsShown()
            and not self.password_plain.IsShown()
        ):
            self._show_password_fields()
            self.password.SetFocus()
            name = self._paths[0].name
            wx.CallLater(
                200,
                self._controller.host.scribe_announce,
                f"{name} needs its password. Type it, then press Send and Convert.",
            )
            return
        self.groups.stop_sample()
        self.EndModal(wx.ID_OK)

    def result(self) -> ConvertChoice:
        return ConvertChoice(
            formats=self.chosen_formats(),
            settings=self.groups.settings(),
            save_as_defaults=self.defaults.GetValue(),
            password=self.password_value(),
            base=self._base,
            stream=bool(
                self.stream is not None and self.stream.GetValue() and len(self._paths) == 1
            ),
            email_changed=self.groups.email_changed(),
        )

    def _on_destroy(self, event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is self:
            self.groups.stop_sample()
            for field in (self.password, self.password_plain):
                field.SetValue("")
        event.Skip()


__all__ = ["ConvertChoice", "ScribeConvertDialog", "pdf_needs_password"]
