"""F1 anywhere, in every Quill app: window purpose + focused control.

Quill Radio built this experience first (2026-08-23) and the family inherited
it the same day: press F1 on any control, in any window, and a help window
opens carrying the purpose of the surface you are standing in and then the
control under focus -- one read-only, multi-line text field a screen reader
reads in a single pass, the same :class:`quill.ui.context_help.ContextHelpDialog`
QUILL's editor shows.

The answer composes from three layers, each with a graceful floor:

1. **The window's purpose** -- resolved by the app's registered
   ``purpose_for_title`` callable (Radio's authored, gated catalogue in
   :mod:`quill.core.radio.surface_help`); apps that have not authored one yet
   fall back to :data:`quill.core.control_help.GENERIC_PURPOSE`.
2. **The control's own help** -- ``SetHelpText`` where authored, else its
   accessible name, which across this family is usually a teaching sentence.
3. **How to drive its kind** -- one role sentence per wx class, from
   :func:`quill.core.control_help.role_usage`.

**Wiring is central.** :func:`activate` registers a handler with
``dialog_contract.set_context_help_handler``; the contract's two show paths
bind F1 on every window they open, which -- by the existing dialog gate -- is
every window. ``AppShellFrame`` activates for all the standalone apps, so a
new app on the shell answers F1 on day one, help strings or not. Main frames
(which no show path wraps) bind directly via :func:`install`.

One load-bearing line: ``SetHelpText`` is a **no-op** until a
``wx.HelpProvider`` exists (measured: without one, ``GetHelpText`` answers
""). :func:`ensure_help_provider` installs ``wx.SimpleHelpProvider``, turning
every help text already written across the family from dead code into live
help.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core import control_help

#: wx default window names that identify nothing -- never worth showing.
_DEFAULT_WX_NAMES = frozenset({
    "button",
    "check",
    "choice",
    "comboBox",
    "dialog",
    "frame",
    "groupBox",
    "listBox",
    "listCtrl",
    "panel",
    "radioButton",
    "scrolledpanel",
    "slider",
    "staticText",
    "text",
    "treeCtrl",
    "wxSpinCtrl",
})

#: The app's window-purpose resolver (title -> paragraph). Registered by
#: :func:`activate`; the generic fallback keeps F1 honest before an app has
#: authored its catalogue.
_purpose_resolver: Callable[[str], str] | None = None


def ensure_help_provider(wx: Any = None) -> None:
    """Install ``wx.SimpleHelpProvider`` once, so ``SetHelpText`` stores text.

    Without a provider every ``SetHelpText`` in the app silently stores
    nothing and ``GetHelpText`` answers "" -- measured, not assumed. Idempotent
    and safe to call before any window exists.
    """
    if wx is None:
        import wx as wx_module

        wx = wx_module
    if wx.HelpProvider.Get() is None:
        wx.HelpProvider.Set(wx.SimpleHelpProvider())


def purpose_for_title(title: str) -> str:
    """The registered app's purpose for *title*, never empty."""
    if _purpose_resolver is not None:
        try:
            purpose = _purpose_resolver(title)
            if purpose:
                return purpose
        except Exception:  # noqa: BLE001 - a resolver bug must not kill F1
            pass
    return control_help.GENERIC_PURPOSE


def _top_level_of(window: Any, wx: Any) -> Any:
    """The frame or dialog *window* ultimately lives on (or *window* itself)."""
    current = window
    while current is not None:
        if isinstance(current, (wx.Frame, wx.Dialog)):
            return current
        parent = getattr(current, "GetParent", None)
        current = parent() if callable(parent) else None
    return window


def _clean_label(control: Any) -> str:
    """The control's visible label, minus mnemonics and menu-style suffixes."""
    get_label = getattr(control, "GetLabel", None)
    label = get_label() if callable(get_label) else ""
    if not isinstance(label, str):
        return ""
    return label.replace("&", "").split("\t")[0].strip()


def _accessible_name(control: Any) -> str:
    get_name = getattr(control, "GetName", None)
    name = get_name() if callable(get_name) else ""
    if not isinstance(name, str) or name in _DEFAULT_WX_NAMES:
        return ""
    return name.strip()


def _help_text_of(control: Any, top: Any) -> str:
    """The nearest authored help text at or above *control* (up to *top*)."""
    current = control
    while current is not None:
        get_help = getattr(current, "GetHelpText", None)
        text = get_help() if callable(get_help) else ""
        if isinstance(text, str) and text.strip():
            return text.strip()
        if current is top:
            return ""
        parent = getattr(current, "GetParent", None)
        current = parent() if callable(parent) else None
    return ""


def _heading_from(label: str, name: str) -> str:
    """A short heading for the help window's title bar.

    This family's accessible names are whole teaching sentences ("Station
    sources; expand one to browse..."); the heading takes the first clause and
    the body keeps the full sentence, so the title stays speakable at a
    glance.
    """
    text = label or name or "This control"
    for separator in (";", " -- ", ". "):
        if separator in text:
            text = text.split(separator, 1)[0]
            break
    return text.strip().rstrip(".") or "This control"


def topics_for(window: Any, wx: Any = None) -> tuple[Any, Any]:
    """The ``(surface_topic, control_topic)`` pair F1 shows for *window*.

    Pure composition over live widget state, split from the dialog so a test
    can assert the words without running a modal loop. Never returns an empty
    control topic: name, help and role compose so something true is always
    said.
    """
    if wx is None:
        import wx as wx_module

        wx = wx_module
    from quill.core.help import HelpTopic

    focused = wx.Window.FindFocus()
    top = _top_level_of(focused if focused is not None else window, wx)
    get_title = getattr(top, "GetTitle", None)
    title = (get_title() if callable(get_title) else "") or "This window"
    surface_topic = HelpTopic(id="", title=title, body=purpose_for_title(title))

    if focused is None:
        control_topic = HelpTopic(
            id="",
            title="No control focused",
            body="Move focus to a control and press F1 for help on that item.",
        )
        return surface_topic, control_topic

    label = _clean_label(focused)
    name = _accessible_name(focused)
    heading = _heading_from(label, name)
    body = control_help.compose_control_body(
        accessible_name="" if name == heading else name,
        help_text=_help_text_of(focused, top),
        usage=control_help.role_usage(type(focused).__name__),
    )
    control_topic = HelpTopic(id="", title=heading, body=body)
    return surface_topic, control_topic


def show_help(window: Any) -> None:
    """F1: show the context-help window for wherever focus is in *window*.

    Reuses QUILL's :class:`ContextHelpDialog` -- the same multi-line,
    read-only text field, focused on open so a screen reader reads the whole
    answer in one pass -- shown through the dialog contract like every other
    modal. Never raises: a help window that crashes the app answers the
    question nobody asked.
    """
    try:
        import wx

        from quill.ui.context_help import ContextHelpDialog
        from quill.ui.dialog_contract import show_modal_dialog

        ensure_help_provider(wx)
        surface_topic, control_topic = topics_for(window, wx)
        top = _top_level_of(wx.Window.FindFocus() or window, wx)
        dlg = ContextHelpDialog(top, dialog_topic=surface_topic, ctrl_topic=control_topic)
        try:
            show_modal_dialog(dlg, "Context Help")
        finally:
            dlg.Destroy()
    except Exception:  # noqa: BLE001 - help must never take the window down
        return


def activate(purpose_for_title_fn: Callable[[str], str] | None = None) -> None:
    """Turn F1 help on for the whole app (call once at startup).

    Installs the help provider (making every ``SetHelpText`` live), remembers
    the app's window-purpose resolver (or keeps the generic fallback), and
    registers :func:`show_help` with the dialog contract, whose two show
    paths bind F1 on every surface that opens. New dialogs inherit F1 by
    construction: the dialog gate already forces them through those paths.
    """
    global _purpose_resolver
    from quill.ui import dialog_contract

    if purpose_for_title_fn is not None:
        _purpose_resolver = purpose_for_title_fn
    ensure_help_provider()
    dialog_contract.set_context_help_handler(show_help)


def install(window: Any, wx: Any = None) -> None:
    """Bind F1 on *window* directly (for a main frame, which no show path
    wraps). Every other key falls through untouched."""
    if wx is None:
        import wx as wx_module

        wx = wx_module

    def _on_char_hook(event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_F1 and not event.HasAnyModifiers():
            show_help(window)
            return
        event.Skip()

    window.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)
