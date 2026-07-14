"""Context-sensitive help for QUILL (F1 = control help, Ctrl+F1 = user guide).

``ContextHelpMixin`` is mixed into ``MainFrame`` and any modal dialog that
wants F1 help. It tracks the last-focused control via ``EVT_CHILD_FOCUS``
(so F1 still works after the user opens a menu, which moves focus away from
the control), and shows a ``ContextHelpDialog`` with:

  1. The parent dialog's description (if the focused control lives inside a
     named dialog rather than the main frame).
  2. The specific help for the focused control.

Topic keys follow a convention that matches ``wx.Window.GetName()``:

- Main-frame controls: ``"main.<ctrl_name>"`` e.g. ``"main.search_text"``
- Preference panel controls: ``"prefs.<ctrl_name>"`` e.g. ``"prefs.theme"``
- Dialog controls: ``"<dialog_name>.<ctrl_name>"`` e.g. ``"ai.provider"``

The mixin reads topics through the global ``HelpRenderer`` (loaded once at
app start via ``ContextHelpMixin._init_context_help()``).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import wx

from quill.core.help import HelpRenderer, HelpTopic
from quill.ui.dialog_contract import apply_modal_ids

_log = logging.getLogger(__name__)

_renderer: HelpRenderer | None = None
_renderer_lock = threading.Lock()


def _get_renderer() -> HelpRenderer:
    global _renderer
    with _renderer_lock:
        if _renderer is None:
            _renderer = HelpRenderer.from_file()
    return _renderer


def warm_help_topics() -> bool:
    """Force ``HelpRenderer.from_file()`` to run once and cache the topics.

    Called from :meth:`MainFrame._run_deferred_startup_tasks` so the first
    ``F1`` / ``Shift+F1`` press is instant.  The first call to
    ``_get_renderer()`` reads ``topics.json`` synchronously and decodes all
    entries; on a cold machine + AV scan this can take several hundred
    milliseconds, which is enough to trip the ``wx`` heartbeat watchdog
    while a modal is open (#179).

    Returns ``True`` on success, ``False`` if the topics file is missing or
    corrupt.  Never raises — a corrupt ``topics.json`` must not break
    startup; the dialog will fall back to a "no help available" topic.
    """
    try:
        _get_renderer()
        return True
    except Exception:
        _log.exception(
            "warm_help_topics: HelpRenderer.from_file() failed; help will lazy-load on first F1"
        )
        return False


def _find_named_ancestor_dialog(ctrl: wx.Window) -> wx.Window | None:
    """Walk up the parent chain to find the nearest named dialog."""
    parent = ctrl.GetParent()
    while parent is not None:
        if isinstance(parent, wx.Dialog) and parent.GetName():
            return parent
        parent = parent.GetParent()
    return None


def describe_focused(ctrl: wx.Window | None) -> tuple[HelpTopic | None, HelpTopic]:
    """Return ``(dialog_topic_or_None, control_topic)`` for *ctrl*.

    The first element is the parent dialog's topic (for context); the second
    is the specific control's topic (or a generic fallback if none exists).
    """
    renderer = _get_renderer()

    if ctrl is None:
        return None, HelpTopic(
            id="",
            title="No control focused",
            body="Move focus to a control and press F1 for help on that item.",
        )

    ctrl_name = ctrl.GetName()

    dialog = _find_named_ancestor_dialog(ctrl)
    dialog_topic: HelpTopic | None = None
    if dialog is not None:
        dialog_name = dialog.GetName()
        topic_key = f"{dialog_name}.{ctrl_name}"
        dialog_topic = renderer.get(dialog_name)
        ctrl_topic = renderer.get_or_missing(topic_key)
    else:
        ctrl_topic = renderer.get_or_missing(ctrl_name)

    return dialog_topic, ctrl_topic


def _compose_help_text(dialog_topic: HelpTopic | None, ctrl_topic: HelpTopic) -> str:
    """Build the full text string that the help TextCtrl displays.

    Combining context and control help into ONE text block means the screen
    reader reads everything in a single pass when focus arrives on the
    TextCtrl at dialog open — no silent header elements above the fold.
    """
    lines: list[str] = []
    if dialog_topic is not None:
        lines.append(f"In this dialog: {dialog_topic.title}")
        lines.append(dialog_topic.body)
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append(ctrl_topic.title)
    lines.append("")
    lines.append(ctrl_topic.body)
    if ctrl_topic.keystrokes:
        lines.append("")
        lines.append("Keyboard shortcuts:")
        lines.extend(f"  {k}" for k in ctrl_topic.keystrokes)
    if ctrl_topic.see_also:
        lines.append("")
        lines.append(f"See also: {', '.join(ctrl_topic.see_also)}")
    return "\n".join(lines)


class ContextHelpDialog(wx.Dialog):
    """Modal dialog that shows context help for a single focused control.

    All content — the parent-dialog description (when present) and the
    control-specific help — is rendered into a single read-only TextCtrl
    that receives focus when the dialog opens.  This ensures a screen
    reader announces the complete text in one pass rather than silently
    skipping StaticText elements that precede the first focusable widget.

    Screen-reader experience on open:
      1. SR announces: "Help: <ctrl title>, dialog"
      2. Focus arrives on the TextCtrl
      3. SR reads: "[In this dialog: <name>] <dialog desc>  ---  <ctrl title>
                    <ctrl body>  Keyboard shortcuts: ..."
      4. Tab / Shift+Tab cycles to Close (and optional Open User Guide)
      5. Escape or Enter on Close dismisses
    """

    def __init__(
        self,
        parent: wx.Window,
        dialog_topic: HelpTopic | None,
        ctrl_topic: HelpTopic,
        user_guide_opener: Callable[..., None] | None = None,
    ) -> None:
        # Title = "Help: <ctrl title>" so the SR announces context immediately.
        super().__init__(
            parent,
            title=f"Help: {ctrl_topic.title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="context_help",
        )
        self._user_guide_opener = user_guide_opener
        self._ctrl_topic = ctrl_topic
        self._body_text = self._build_ui(dialog_topic, ctrl_topic)
        self.SetMinSize((440, 220))
        self.Fit()
        self.CentreOnParent()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        # Explicitly focus the TextCtrl so the SR reads all content on open.
        self._body_text.SetFocus()

    def _build_ui(self, dialog_topic: HelpTopic | None, ctrl_topic: HelpTopic) -> wx.TextCtrl:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Single TextCtrl containing dialog context + control help.
        # It is the FIRST focusable control so the SR reads it on dialog open.
        combined = _compose_help_text(dialog_topic, ctrl_topic)
        body_text = wx.TextCtrl(
            panel,
            value=combined,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_AUTO_URL,
            name="help_body",
        )
        body_text.SetMinSize((-1, 120))
        sizer.Add(body_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        close_btn = wx.Button(panel, wx.ID_OK, label="Close")
        close_btn.SetDefault()
        btn_sizer.AddButton(close_btn)

        if ctrl_topic.user_guide_section:
            guide_btn = wx.Button(panel, wx.ID_HELP, label="Open User Guide")
            btn_sizer.AddButton(guide_btn)
            guide_btn.Bind(wx.EVT_BUTTON, self._on_open_guide)

        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        panel.SetSizer(sizer)
        close_btn.Bind(wx.EVT_BUTTON, lambda _: self.EndModal(wx.ID_OK))
        return body_text

    def _on_open_guide(self, _: wx.CommandEvent) -> None:
        self.EndModal(wx.ID_HELP)
        if self._user_guide_opener is not None:
            self._user_guide_opener(self._ctrl_topic.user_guide_section)


class ContextHelpMixin:
    """Mixin for MainFrame and dialogs that want F1 context help.

    Add to the MRO before wx.Frame / wx.Dialog and call
    ``_init_context_help()`` in ``__init__`` after the window is built.

    Binds ``EVT_CHILD_FOCUS`` so focus moves away when menus open do not
    clear the remembered last-focused control.

    For classes that are wx.Window subclasses, ``_help_frame`` returns
    ``self``.  MainFrame (which wraps a ``self.frame`` rather than
    inheriting from wx.Frame) overrides this property to return
    ``self.frame``.
    """

    @property
    def _help_frame(self) -> wx.Window:
        return self  # type: ignore[return-value]

    def _init_context_help(self) -> None:
        self._last_focused_ctrl: wx.Window | None = None
        self._help_frame.Bind(wx.EVT_CHILD_FOCUS, self._on_child_focus_for_help)

    def _on_child_focus_for_help(self, event: wx.ChildFocusEvent) -> None:
        win = event.GetWindow()
        if win is not None and not isinstance(win, (wx.Panel, wx.StaticBox)):
            self._last_focused_ctrl = win
        event.Skip()

    def show_control_help(self, user_guide_opener: Callable[..., None] | None = None) -> None:
        """Show the F1 context-help dialog for the currently focused control.

        Shows two sections:
        1. A description of the parent dialog (for orientation).
        2. Specific help for the focused control.
        """
        ctrl = wx.Window.FindFocus() or self._last_focused_ctrl  # type: ignore[attr-defined]
        dialog_topic, ctrl_topic = describe_focused(ctrl)
        dlg = ContextHelpDialog(
            self._help_frame,
            dialog_topic=dialog_topic,
            ctrl_topic=ctrl_topic,
            user_guide_opener=user_guide_opener,
        )
        result = self._show_modal_dialog(dlg, "Context Help")
        dlg.Destroy()
        if result == wx.ID_HELP and user_guide_opener is not None:
            section = ctrl_topic.user_guide_section
            user_guide_opener(section)

    def show_topic_help(
        self, topic_id: str, user_guide_opener: Callable[..., None] | None = None
    ) -> None:
        """Show the context-help dialog for a specific topic id.

        Used when the focused control has no help-topic name of its own but maps
        to a known topic — e.g. F1 in the main document window resolving to the
        ``main.editor`` topic without giving the editor an unfriendly accessible
        name.
        """
        renderer = _get_renderer()
        ctrl_topic = renderer.get(topic_id) or renderer.get_or_missing(topic_id)
        dlg = ContextHelpDialog(
            self._help_frame,
            dialog_topic=None,
            ctrl_topic=ctrl_topic,
            user_guide_opener=user_guide_opener,
        )
        result = self._show_modal_dialog(dlg, "Context Help")
        dlg.Destroy()
        if result == wx.ID_HELP and user_guide_opener is not None:
            user_guide_opener(ctrl_topic.user_guide_section)
