"""Fill It In Yourself: the form as a real window, tabbed through as a visitor would (17a.6).

Every question is a native control -- an edit field, a check box, a group of
radio buttons in a labelled group box, a drop-down list -- so the screen
reader announces labels, groups, required states and help exactly as it
would anywhere else, and Tab moves through them in form order. What decides
what is on screen is :class:`~quill.ui.forms_fill.FillSession`; this window
only draws it.

Speech: the reader already says each control as focus reaches it (GATE-13),
so the window speaks only what it alone knows -- a question that appeared or
disappeared because of an answer, the page you moved to, and which questions
still need an answer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.forms import model as M
from quill.ui import forms_doc as fd
from quill.ui import forms_fill as ff
from quill.ui import wordpress_dialogs as dlg
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

PURPOSE = (
    "Your form as a visitor meets it. Tab through the questions and answer them; rules show and "
    "hide questions as you go, and worked-out answers update. Submit sends nothing: it shows "
    "what would have been sent."
)
_NO_ANSWER = "(no answer)"


def _text(label: str) -> str:
    """A form's own words as a wx label: an & is a character, never an access key."""
    return label.replace("&", "&&")


class FillWindow(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        session: ff.FillSession,
        *,
        announce: Callable[[str], None],
        show_modal: dlg.ShowModal,
    ) -> None:
        title = f"Fill It In Yourself: {session.model.get('title') or 'Untitled form'}"
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(PURPOSE)
        self.session = session
        self._announce = announce
        self._show_modal = show_modal
        self.rows: dict[str, list[wx.Window]] = {}
        self.first: dict[str, wx.Window] = {}
        self.worked: dict[str, wx.TextCtrl] = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.language: wx.Choice | None = None
        if len(session.languages()) > 1:
            self.language = wx.Choice(self, choices=session.languages())
            self.language.SetSelection(session.languages().index(session.language))
            self.language.SetHelpText(
                "Try the form in each language it is translated into. Untranslated words "
                "stay in the form's own language."
            )
            self.language.Bind(wx.EVT_CHOICE, self._on_language)
            dlg.labelled_row(sizer, self, "&Language:", self.language)
        self.heading = wx.StaticText(self, label=session.heading())
        sizer.Add(self.heading, 0, wx.ALL, 8)
        self.panel = wx.ScrolledWindow(self, style=wx.VSCROLL | wx.TAB_TRAVERSAL)
        self.panel.SetScrollRate(0, 20)
        self.panel.SetMinSize(dip_size(self, 560, 360))
        self.panel.SetSizer(wx.BoxSizer(wx.VERTICAL))
        sizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, 4)
        bar = wx.BoxSizer(wx.HORIZONTAL)
        self.back = wx.Button(self, label="&Back")
        self.back.SetHelpText("Go to the page before this one.")
        self.back.Bind(wx.EVT_BUTTON, lambda _e: self.go(-1))
        self.next = wx.Button(self, label="&Next")
        self.next.SetHelpText("Check this page's required questions, then go to the next page.")
        self.next.Bind(wx.EVT_BUTTON, lambda _e: self.go(1))
        self.submit = wx.Button(self, label="&Submit")
        self.submit.SetHelpText(
            "Send nothing, and show what would have been sent, question by question."
        )
        self.submit.Bind(wx.EVT_BUTTON, lambda _e: self.on_submit())
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close the form. Nothing is kept or sent. Escape does the same.")
        for button in (self.back, self.next, self.submit, close):
            bar.Add(button, 0, wx.ALL, 4)
        sizer.Add(bar, 0, wx.ALL, 4)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)
        self.build_page()

    # -- building a page --------------------------------------------------- #

    def build_page(self) -> None:
        self.panel.DestroyChildren()
        page_sizer = self.panel.GetSizer()
        page_sizer.Clear()
        self.rows, self.first, self.worked = {}, {}, {}
        for depth, item in self.session.page_items():
            widgets = self._build(item, page_sizer, depth)
            self.rows[str(item.get("id"))] = widgets
        self.heading.SetLabel(self.session.heading())
        self.refresh()
        first = next((w for i, w in self.first.items() if self._shown(i)), None)
        if first is not None:
            first.SetFocus()

    def _build(self, item: dict[str, Any], sizer: wx.Sizer, depth: int) -> list[wx.Window]:
        kind = str(item.get("type"))
        item_id = str(item.get("id"))
        name = fd.name_of(item) + (" (required)" if item.get("required") else "")
        help_text = str(item.get("help") or "")
        pad = 8 + 16 * depth
        made: list[wx.Window] = []

        def add(window: wx.Window, flag: int = wx.EXPAND) -> wx.Window:
            sizer.Add(window, 0, flag | wx.LEFT | wx.RIGHT | wx.TOP, pad)
            made.append(window)
            return window

        if kind == "section":
            heading = add(wx.StaticText(self.panel, label=_text(fd.name_of(item))))
            heading.SetFont(heading.GetFont().Bold())
        elif kind == "html" or not M.is_field_type(kind):
            add(wx.StaticText(self.panel, label=_text(str(item.get("label") or help_text))))
        else:
            control = self._control(item, kind, name, add, (sizer, pad, made))
            self.first[item_id] = control
            control.SetHelpText(help_text or f"{name}: answer it as a visitor would.")
        if help_text and kind != "html":
            add(wx.StaticText(self.panel, label=_text(help_text)))
        return made

    def _control(
        self, item: dict[str, Any], kind: str, name: str, add: Callable[..., Any], where: Any
    ) -> Any:
        item_id = str(item.get("id"))
        answer = self.session.answers.get(item_id)
        if kind in ff.YES_NO:
            box = add(wx.CheckBox(self.panel, label=_text(name)))
            box.SetValue(bool(answer))
            box.Bind(wx.EVT_CHECKBOX, lambda e: self.answer(item_id, bool(e.IsChecked())))
            return box
        if kind in ff.NOT_HERE or kind in ff.WORKED_OUT or item.get("calculation"):
            add(wx.StaticText(self.panel, label=_text(name)))
            value = (
                self.session.worked_out(item_id)
                if kind not in ff.NOT_HERE
                else f"QUILL cannot show a {M.TYPE_NAMES.get(kind, kind)} question here. It "
                "works on the site."
            )
            shown = add(wx.TextCtrl(self.panel, value=value, style=wx.TE_READONLY))
            set_spoken_name(shown, name)
            if kind not in ff.NOT_HERE:
                self.worked[item_id] = shown
            return shown
        choices = ff.choices_of(item)
        if kind in ff.MANY or (kind in ff.ONE and kind != "select"):
            return self._group(item_id, kind, name, choices, answer, where)
        if kind in ff.ONE or choices:
            add(wx.StaticText(self.panel, label=_text(name)))
            values = [""] + [v for v, _l in choices]
            pick = add(wx.Choice(self.panel, choices=[_NO_ANSWER] + [lbl for _v, lbl in choices]))
            pick.SetSelection(values.index(str(answer)) if str(answer) in values else 0)
            set_spoken_name(pick, name)
            pick.Bind(wx.EVT_CHOICE, lambda e: self.answer(item_id, values[e.GetSelection()]))
            return pick
        add(wx.StaticText(self.panel, label=_text(name)))
        multi = kind in ("textarea", "rich_text")
        style = wx.TE_MULTILINE if multi else (wx.TE_PASSWORD if kind == "password" else 0)
        edit = add(
            wx.TextCtrl(self.panel, value="" if answer is None else str(answer), style=style)
        )
        if multi:
            edit.SetMinSize(dip_size(self.panel, 480, 80))
        set_spoken_name(edit, name)
        edit.Bind(wx.EVT_TEXT, lambda e: self.answer(item_id, e.GetString()))
        return edit

    def _group(
        self,
        item_id: str,
        kind: str,
        name: str,
        choices: list[tuple[str, str]],
        answer: Any,
        where: Any,
    ) -> Any:
        sizer, pad, made = where
        inner = wx.StaticBoxSizer(wx.VERTICAL, self.panel, _text(name))
        box = inner.GetStaticBox()
        sizer.Add(inner, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, pad)
        made.append(box)
        picked = set(answer) if isinstance(answer, list) else {str(answer)}
        first: Any = None
        for index, (value, label) in enumerate(choices):
            if kind in ff.MANY:
                control: Any = wx.CheckBox(box, label=_text(label))
                control.SetValue(value in picked)
                control.Bind(wx.EVT_CHECKBOX, lambda _e, k=item_id: self._many(k))
            else:
                style = wx.RB_GROUP if index == 0 else 0
                control = wx.RadioButton(box, label=_text(label), style=style)
                control.Bind(wx.EVT_RADIOBUTTON, lambda _e, k=item_id, v=value: self.answer(k, v))
            control.SetHelpText(f"One of the choices for {name}.")
            control._quill_value = value  # read back by _many
            inner.Add(control, 0, wx.ALL, 2)
            first = first or control
        if kind not in ff.MANY:
            for child in box.GetChildren():
                child.SetValue(getattr(child, "_quill_value", None) in picked)
        return first or box

    def _many(self, item_id: str) -> None:
        box = next(w for w in self.rows.get(item_id) or [] if isinstance(w, wx.StaticBox))
        values = [c._quill_value for c in box.GetChildren() if c.GetValue()]
        self.answer(item_id, values)

    # -- answering ---------------------------------------------------------- #

    def answer(self, item_id: str, value: Any) -> None:
        change = self.session.answer(item_id, value)
        self.refresh()
        said = change.sentence()
        if said:
            self._announce(said)

    def _shown(self, item_id: str) -> bool:
        item = M.find(self.session.model, item_id)
        return item is None or self.session.is_shown(item)

    def refresh(self) -> None:
        for item_id, widgets in self.rows.items():
            shown = self._shown(item_id)
            for widget in widgets:
                widget.Show(shown)
        for item_id, edit in self.worked.items():
            edit.ChangeValue(self.session.worked_out(item_id))
        self.back.Enable(self.session.back_possible())
        self.next.Enable(not self.session.is_last())
        self.submit.Enable(self.session.is_last())
        self.panel.Layout()
        self.panel.FitInside()

    def go(self, step: int) -> None:
        if step > 0:
            missing = self.session.missing_here()
            if missing:
                self._say_missing(missing)
                return
            moved = self.session.next()
        else:
            moved = self.session.back()
        if moved:
            self.build_page()
            self._announce(self.session.heading())

    def _say_missing(self, missing: list[str]) -> None:
        count = "1 question needs" if len(missing) == 1 else f"{len(missing)} questions need"
        self._announce(f"{count} an answer: {', '.join(missing)}.")
        for item_id, control in self.first.items():
            item = M.find(self.session.model, item_id) or {}
            if fd.name_of(item) == missing[0]:
                control.SetFocus()
                return

    def on_submit(self) -> None:
        dlg.show_report(
            self,
            self._show_modal,
            title="What Would Be Sent",
            text=self.session.summary(),
            help_text=(
                "Each question and its answer, as the form would send them. Nothing was sent."
            ),
        )

    def _on_language(self, _event: object) -> None:
        if self.language is None:
            return
        self.session.set_language(self.session.languages()[self.language.GetSelection()])
        self.build_page()
        self.language.SetFocus()


def show_fill_window(
    parent: wx.Window,
    show_modal: dlg.ShowModal,
    *,
    session: ff.FillSession,
    announce: Callable[[str], None],
) -> None:
    window = FillWindow(parent, session, announce=announce, show_modal=show_modal)
    try:
        show_modal(window, window.GetTitle())
    finally:
        window.Destroy()
