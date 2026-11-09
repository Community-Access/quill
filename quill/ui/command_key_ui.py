"""Say or Type a Command: the Command Key's windows, shared by every app.

docs/design/command-key.md sections 10 and 11. F11 opens the box in QUILL,
QUILL Lite and Quill Radio; each app supplies a :class:`WxCommandKeyHost` with
its own registry, candidate list and voice, and this module supplies the four
small windows every app shows the same way:

- **Say or Type a Command**: one line, Enter to go, Escape to leave.
- **Did You Mean**: two or three commands, each with its key, then Something
  Else, which reopens the box.
- **What Can I Say Here**: this window's commands right now, grouped, with an
  example and a key each. Enter runs one.
- **the confirmation** for a CONFIRM command: one line, Enter to go ahead.

Every window says nothing the screen reader already says (GATE-13): its title,
its controls and the rows read themselves. The app speaks only what it alone
knows -- a refusal, a result, the count when the help list opens -- through its
announcement service, so it is brailled too (GATE-BRAILLE).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from quill.core.command_catalogue import CommandSpec, Risk, rows_for_app
from quill.core.command_catalogue.help_list import (
    HelpRow,
    count_line,
    help_rows,
    nothing_about_line,
)
from quill.core.command_catalogue.policy import CommandKeySession, Elsewhere, Unavailable
from quill.core.command_catalogue.resolver import Candidate
from quill.ui.dpi import dip_size

__all__ = [
    "BOX_TITLE",
    "CHOOSE_TITLE",
    "CONFIRM_TITLE",
    "FIRST_HINT",
    "HELP_TITLE",
    "WxCommandKeyHost",
    "ask_for_command",
    "choose_command",
    "confirm_command",
    "run_command_key",
    "show_command_help",
]

BOX_TITLE = "Say or Type a Command"
CHOOSE_TITLE = "Did You Mean"
HELP_TITLE = "What Can I Say Here"
CONFIRM_TITLE = "Confirm Command"
#: Said once, the first time the box ever opens, in any app (11.4).
FIRST_HINT = "Type what you want, or say 'what can I say'."
SOMETHING_ELSE = "Something else..."

ShowModal = Callable[[Any, str], int]


def _sized(dialog: Any, width: int, height: int) -> Any:
    dialog.SetSize(dip_size(dialog, width, height))
    return dialog


def _buttons(
    wx: Any, dialog: Any, ok_label: str, ok_help: str, cancel_help: str
) -> tuple[Any, Any]:
    from quill.ui.dialog_contract import bind_close_button

    row = wx.BoxSizer(wx.HORIZONTAL)
    # OK and Cancel carry no access key: Enter and Escape already serve them (GATE-14).
    ok = wx.Button(dialog, wx.ID_OK, label=ok_label)
    ok.SetHelpText(ok_help)
    cancel = wx.Button(dialog, wx.ID_CANCEL, label="Cancel")
    cancel.SetHelpText(cancel_help)
    row.AddStretchSpacer()
    row.Add(ok, 0, wx.RIGHT, 6)
    row.Add(cancel, 0)
    bind_close_button(dialog, cancel, modeless=False)
    ok.SetDefault()
    return row, ok


def ask_for_command(wx: Any, parent: Any, show_modal: ShowModal, initial: str = "") -> str | None:
    """The box. Returns what was typed, or None on Escape."""
    from quill.ui.dialog_contract import apply_modal_ids

    dialog = _sized(
        wx.Dialog(parent, title=BOX_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER),
        520,
        160,
    )
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(wx.StaticText(dialog, label="&Command:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
    entry = wx.TextCtrl(dialog, value=initial, style=wx.TE_PROCESS_ENTER)
    entry.SetName("Command")
    entry.SetHelpText(
        "Type what you want this window to do, in your own words: 'turn it down a "
        "bit', 'go to line 120', 'save'. Enter does it. Type 'what can I say' for a "
        "list of everything you can do here. F11 never starts or stops dictation."
    )
    sizer.Add(entry, 0, wx.EXPAND | wx.ALL, 10)
    buttons, _ok = _buttons(
        wx,
        dialog,
        "Go",
        "Do what you typed.",
        "Close the box without doing anything.",
    )
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    entry.Bind(wx.EVT_TEXT_ENTER, lambda _event: dialog.EndModal(wx.ID_OK))
    wx.CallAfter(entry.SetFocus)
    try:
        if show_modal(dialog, BOX_TITLE) != wx.ID_OK:
            return None
        return str(entry.GetValue())
    finally:
        dialog.Destroy()


def _pick_from_list(
    wx: Any,
    parent: Any,
    show_modal: ShowModal,
    *,
    title: str,
    label: str,
    rows: Sequence[str],
    list_help: str,
    ok_help: str,
    start: int = 0,
) -> int | None:
    from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

    chosen: dict[str, int | None] = {"index": None}
    dialog = _sized(
        wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER), 640, 420
    )
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(wx.StaticText(dialog, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
    listing = wx.ListBox(dialog, choices=list(rows), style=wx.LB_SINGLE)
    listing.SetName(title)
    listing.SetHelpText(list_help)
    sizer.Add(listing, 1, wx.EXPAND | wx.ALL, 10)
    buttons, _ok = _buttons(wx, dialog, "Go", ok_help, "Close the list without doing anything.")
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

    def _go(_event: Any = None) -> None:
        index = listing.GetSelection()
        if 0 <= index < len(rows):
            chosen["index"] = int(index)
            if dialog.IsModal():
                dialog.EndModal(wx.ID_OK)

    apply_listbox_activation(listing, _go)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    if rows:
        listing.SetSelection(max(0, min(start, len(rows) - 1)))
    wx.CallAfter(listing.SetFocus)
    try:
        result = show_modal(dialog, title)
        if result == wx.ID_OK and chosen["index"] is None:
            index = listing.GetSelection()
            if 0 <= index < len(rows):
                chosen["index"] = int(index)
        return chosen["index"] if result == wx.ID_OK else None
    finally:
        dialog.Destroy()


def _with_key(candidate: Candidate) -> str:
    spec = candidate.spec
    return f"{spec.title}, {candidate.key}" if candidate.key else spec.title


def choose_command(
    wx: Any, parent: Any, show_modal: ShowModal, choices: Sequence[Candidate]
) -> Candidate | str | None:
    """Did You Mean. Returns the pick, ``"else"`` for Something Else, or None."""
    rows = [_with_key(item) for item in choices] + [SOMETHING_ELSE]
    index = _pick_from_list(
        wx,
        parent,
        show_modal,
        title=CHOOSE_TITLE,
        label="&Commands:",
        rows=rows,
        list_help=(
            "The commands closest to what you typed, each with its key. Enter does the "
            "one you choose; Something else lets you type it another way."
        ),
        ok_help="Do the chosen command.",
    )
    if index is None:
        return None
    if index >= len(choices):
        return "else"
    return choices[index]


def show_command_help(
    wx: Any,
    parent: Any,
    show_modal: ShowModal,
    rows: Sequence[HelpRow],
) -> Candidate | None:
    """What Can I Say Here. Returns the command chosen to run, or None."""
    start = next((index for index, row in enumerate(rows) if not row.is_heading), 0)
    while True:
        index = _pick_from_list(
            wx,
            parent,
            show_modal,
            title=HELP_TITLE,
            label="&Things you can do here:",
            rows=[row.label for row in rows],
            list_help=(
                "Everything you can ask for in this window right now, by menu, with "
                "one way of saying each and its key. Enter does the chosen one. Type "
                "a letter to move to a row that starts with it."
            ),
            ok_help="Do the chosen command.",
            start=start,
        )
        if index is None:
            return None
        if not rows[index].is_heading:
            return rows[index].candidate
        # A group heading does nothing; reopen on the group's first command.
        start = index + 1


def confirm_command(wx: Any, parent: Any, show_modal: ShowModal, question: str) -> bool:
    """One line, Enter to go ahead, Escape to cancel (10.6)."""
    from quill.ui.dialog_contract import apply_modal_ids

    dialog = _sized(
        wx.Dialog(parent, title=CONFIRM_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER),
        480,
        150,
    )
    sizer = wx.BoxSizer(wx.VERTICAL)
    text = wx.StaticText(dialog, label=question)
    text.SetHelpText("The command you asked for, which changes or stops something.")
    sizer.Add(text, 0, wx.ALL, 10)
    buttons, ok = _buttons(
        wx,
        dialog,
        "Go Ahead",
        "Do the command.",
        "Do nothing.",
    )
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    wx.CallAfter(ok.SetFocus)
    try:
        return bool(show_modal(dialog, CONFIRM_TITLE) == wx.ID_OK)
    finally:
        dialog.Destroy()


CONSENT_TITLE = "Understanding Commands"
#: Section 7.8, with what TypeSafe's terms say about keeping requests.
CONSENT_TEXT = (
    "To understand requests the quick matcher can't, QUILL can send the words you "
    "typed or said, the name of this app, and the names of the commands it can do "
    "right now to Community Access's service, which asks TypeSafe, a company in San "
    "Francisco, to pick one (if you stored your own TypeSafe key, QUILL asks TypeSafe "
    "directly). Nothing else is sent: no document text, file names, stations, places "
    "or accounts. TypeSafe "
    "keep the requests they receive, and say they do not train on them. You can "
    "change this at any time."
)
#: The three equal answers, and the setting each one stores.
CONSENT_CHOICES: tuple[tuple[str, str], ...] = (
    ("Use Jev", "jev"),
    ("Use My Own AI Instead", "my_ai"),
    ("Match on This Computer Only", "local"),
)


def ask_command_understanding(wx: Any, parent: Any, show_modal: ShowModal) -> str:
    """The consent question, asked once. Escape means "on this computer only"."""
    from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

    dialog = _sized(
        wx.Dialog(parent, title=CONSENT_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER),
        560,
        260,
    )
    sizer = wx.BoxSizer(wx.VERTICAL)
    # Constructed just before the box, so wxMSW reads it as the box's name.
    sizer.Add(wx.StaticText(dialog, label="&What is sent:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
    text = wx.TextCtrl(
        dialog, value=CONSENT_TEXT, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
    )
    text.SetName("What is sent")
    text.SetHelpText("What QUILL would send to understand a command, and to whom.")
    sizer.Add(text, 1, wx.EXPAND | wx.ALL, 10)
    row = wx.BoxSizer(wx.HORIZONTAL)
    chosen = {"value": "local"}
    buttons = []
    for index, (label, value) in enumerate(CONSENT_CHOICES):
        button = wx.Button(dialog, wx.ID_OK if index == 0 else wx.ID_ANY, label=label)
        button.SetHelpText(
            {
                "jev": "Send requests the quick matcher cannot settle to TypeSafe's Jev.",
                "my_ai": "Ask the AI you chose in Choose Your AI instead of Jev.",
                "local": "Never send a request anywhere; match on this computer only.",
            }[value]
        )

        def _pick(_event: Any, value: str = value) -> None:
            chosen["value"] = value
            dialog.EndModal(wx.ID_OK)

        button.Bind(wx.EVT_BUTTON, _pick)
        row.Add(button, 0, wx.RIGHT, 6)
        buttons.append(button)
    sizer.Add(row, 0, wx.ALL, 10)
    dialog.SetSizer(sizer)
    cancel = wx.Button(dialog, wx.ID_CANCEL, label="Cancel")
    cancel.Hide()
    bind_close_button(dialog, cancel, modeless=False)
    apply_modal_ids(dialog, escape_id=wx.ID_CANCEL)
    wx.CallAfter(text.SetFocus)
    try:
        if show_modal(dialog, CONSENT_TITLE) != wx.ID_OK:
            return "local"
        return chosen["value"]
    finally:
        dialog.Destroy()


class WxCommandKeyHost:
    """One app window, as the Command Key sees it.

    Built per F11 press, so the candidate list is this window's, right now.
    The app passes its own registry (or a factory, for QUILL Lite, whose
    palette registry is built per document), its key lookup, its voice, its
    modal helper, and any per-command probes it has.
    """

    def __init__(
        self,
        *,
        wx: Any,
        parent: Any,
        app: str,
        registry: Any,
        show_modal: ShowModal,
        announce: Callable[[str], None],
        key_for: Callable[[str], str] = lambda _command_id: "",
        probe: Callable[[CommandSpec], str] | None = None,
        other_apps: Sequence[tuple[str, CommandSpec]] = (),
        args_runner: Callable[[CommandSpec, Mapping[str, object]], bool] | None = None,
        dictation_help: Callable[[], None] | None = None,
        usage: Mapping[str, int] | None = None,
    ) -> None:
        self._wx = wx
        self._parent = parent
        self.app = app
        self.registry = registry
        self._show_modal = show_modal
        self._announce = announce
        self._key_for = key_for
        self._probe = probe
        self._other_apps = tuple(other_apps)
        self._args_runner = args_runner
        self._dictation_help = dictation_help
        self._usage = dict(usage or {})
        self.retype = False

    # -- the lists ----------------------------------------------------------

    def _registered(self, command_id: str) -> bool:
        """Whether the registry has *command_id*. A registry that cannot say has nothing."""
        get = getattr(self.registry, "get", None)
        return bool(callable(get) and get(command_id) is not None)

    def _reason(self, spec: CommandSpec) -> str:
        if not self._registered(spec.id):
            return ""
        reason = str(self.registry.unavailable_reason(spec.id) or "")
        if not reason and self._probe is not None:
            try:
                reason = str(self._probe(spec) or "")
            except Exception:  # noqa: BLE001 - a probe failure means "no reason known"
                reason = ""
        return reason

    def candidates(self) -> Sequence[Candidate]:
        out: list[Candidate] = []
        for spec in rows_for_app(self.app):
            if spec.risk is Risk.NEVER or not self._registered(spec.id):
                continue
            if self._reason(spec):
                continue
            out.append(Candidate(spec, self._key_for(spec.id) or ""))
        return tuple(out)

    def elsewhere(self) -> Elsewhere:
        unavailable: list[Unavailable] = []
        never: list[CommandSpec] = []
        for spec in rows_for_app(self.app):
            if not spec.offered:
                never.append(spec)
                continue
            if not self._registered(spec.id):
                continue
            reason = self._reason(spec)
            if reason:
                unavailable.append(Unavailable(spec, reason))
        return Elsewhere(tuple(unavailable), tuple(never), self._other_apps)

    # -- speaking and asking ---------------------------------------------------

    def announce(self, text: str) -> None:
        self._announce(text)

    def confirm(self, question: str) -> bool:
        return confirm_command(self._wx, self._parent, self._show_modal, question)

    def choose(self, choices: Sequence[Candidate]) -> Candidate | None:
        picked = choose_command(self._wx, self._parent, self._show_modal, choices)
        if picked == "else":
            self.retype = True
            return None
        return picked if isinstance(picked, Candidate) else None

    def show_help(self, help_filter: str) -> Candidate | None:
        candidates = self.candidates()
        rows = help_rows(candidates, help_filter=help_filter, usage=self._usage)
        if help_filter and not rows:
            self.announce(nothing_about_line(help_filter))
            rows = help_rows(candidates, usage=self._usage)
        if not rows:
            self.announce("Nothing can be done here right now.")
            return None
        # The count is the one thing only the app knows (GATE-13).
        self.announce(count_line(rows))
        return show_command_help(self._wx, self._parent, self._show_modal, rows)

    def show_dictation_help(self) -> None:
        if self._dictation_help is not None:
            self._dictation_help()
        else:
            self.announce("Dictation's phrases are in Dictation Settings, Commands.")

    def run_with_args(self, spec: CommandSpec, args: Mapping[str, object]) -> bool:
        return bool(self._args_runner(spec, args)) if self._args_runner is not None else False


def run_command_key(
    host: WxCommandKeyHost,
    session: CommandKeySession | None = None,
    *,
    first_time: bool = False,
    assist: Any = None,
) -> CommandKeySession:
    """F11: open the box, and do what was typed. "Something else" reopens it.

    Pass the app's last *session* back in, so "undo that" and "do that again"
    reach the box's earlier actions in this window; it is returned for keeping.
    """
    session = session or CommandKeySession(host)
    session.host = host
    session.assist = assist
    if first_time:
        host.announce(FIRST_HINT)
    text = ""
    for _attempt in range(3):
        typed = ask_for_command(host._wx, host._parent, host._show_modal, text)
        if typed is None:
            return session
        host.retype = False
        session.submit(typed)
        if not host.retype:
            return session
        text = typed
    return session
