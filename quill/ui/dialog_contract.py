from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

# Control classes that should receive initial keyboard focus when a custom
# dialog opens, in priority order. These are the "content" controls a user came
# to interact with — lists, trees, text fields, choices. Buttons (OK/Cancel)
# are deliberately excluded: a dialog that focuses its OK button on open hides
# the actual content from screen-reader and keyboard users, who then cannot tell
# what the dialog is for without hunting with Tab. Progress gauges and static
# text are excluded because they are not interactive.
_PREFERRED_FOCUS_CLASSES: tuple[str, ...] = (
    "CheckListBox",
    "ListBox",
    "ListCtrl",
    "ListView",
    "TreeCtrl",
    "TreeListCtrl",
    "DataViewCtrl",
    "DataViewListCtrl",
    "DataViewTreeCtrl",
    "EditableListBox",
    "TextCtrl",
    "SearchCtrl",
    "ComboBox",
    "BitmapComboBox",
    "Choice",
    "SpinCtrl",
    "SpinCtrlDouble",
    "RadioBox",
    "CheckBox",
    "Slider",
)


def apply_modal_ids(
    dialog: object,
    *,
    affirmative_id: int | None = None,
    affirmative_label: str | None = None,
    cancel_id: int | None = None,
    cancel_label: str | None = None,
    escape_id: int | None = None,
) -> None:
    """Apply modal affirmative/escape ids when supported by the dialog.

    The ``affirmative_label`` / ``cancel_label`` keyword arguments are the
    recommended way to make the OK/Cancel labels visible in the dialog
    contract snapshot; :func:`quill.tools.dialog_button_contract` reads the
    button labels by id to confirm each ``apply_modal_ids`` call has a
    matching button.
    """

    if affirmative_id is not None and hasattr(dialog, "SetAffirmativeId"):
        dialog.SetAffirmativeId(affirmative_id)
    if escape_id is not None and hasattr(dialog, "SetEscapeId"):
        dialog.SetEscapeId(escape_id)
    if escape_id is None and cancel_id is not None and hasattr(dialog, "SetEscapeId"):
        dialog.SetEscapeId(cancel_id)
    if affirmative_label is not None and hasattr(dialog, "FindWindowById"):
        button = dialog.FindWindowById(affirmative_id)
        if button is not None and hasattr(button, "SetLabel"):
            button.SetLabel(affirmative_label)
    if cancel_label is not None and hasattr(dialog, "FindWindowById"):
        button = dialog.FindWindowById(cancel_id) if cancel_id is not None else None
        if button is not None and hasattr(button, "SetLabel"):
            button.SetLabel(cancel_label)


def accessible_label(label: str) -> str:
    """Strip a wx keyboard-mnemonic marker and trailing colon from *label*.

    Hand-rolled dialogs write labels like ``"&Word or phrase:"`` for a
    ``StaticText`` sitting next to a control; that raw string is not a fit
    spoken name. A literal ``&&`` (wx's escape for a real ampersand) is
    preserved as a single ``&``; a lone ``&`` (the mnemonic marker) is
    dropped.
    """
    text = label.replace("&&", "\0").replace("&", "").replace("\0", "&")
    return text.strip().rstrip(":").strip()


def set_accessible_name(control: object, label: str) -> None:
    """Give *control* an accessible name derived from its visible *label*.

    macOS VoiceOver does not synthesize a control's name from a neighbouring
    ``StaticText`` the way Windows screen readers do (#1012): with nothing
    set explicitly, VoiceOver announces only the control's raw value -- a
    bare number for a spin control, nothing at all for a text field. Call
    this once, right after building the control, instead of relying on the
    Windows-only label/mnemonic association.

    ``wx.SpinCtrl``/``wx.SpinCtrlDouble`` are composites on macOS: an inner
    ``TextCtrl`` (what VoiceOver actually lands on) plus a stepper button.
    Naming the composite alone does not propagate to the inner field, so
    this also names every immediate child -- a no-op for controls with none.
    """
    name = accessible_label(label)
    set_name = getattr(control, "SetName", None)
    if callable(set_name):
        set_name(name)
    get_children = getattr(control, "GetChildren", None)
    if not callable(get_children):
        return
    try:
        children = list(get_children())
    except Exception:
        return
    for child in children:
        child_set_name = getattr(child, "SetName", None)
        if callable(child_set_name):
            child_set_name(name)


def ok_cancel_platform_order(ok_btn: object, cancel_btn: object) -> tuple[object, object]:
    """Return ``(first, second)`` for a manual OK/Cancel button sizer row.

    macOS reads Cancel on the left and the affirmative (OK) button on the
    right; Windows/Linux read OK on the left and Cancel on the right (#53).
    Use this when a dialog builds its own button ``BoxSizer`` instead of
    ``wx.StdDialogButtonSizer`` so the pair follows native muscle memory. The
    caller still owns the ``Add`` calls (and any stretch spacer / border gap),
    and both buttons must carry their stock ``wx.ID_OK`` / ``wx.ID_CANCEL`` ids
    so :func:`apply_modal_ids` and the dialog button-contract audit keep working.
    """
    import sys

    if sys.platform == "darwin":
        return cancel_btn, ok_btn
    return ok_btn, cancel_btn


def apply_listbox_activation(listbox: object, handler: Callable[[object], None]) -> None:
    """Make a ``wx.ListBox`` activatable by keyboard as well as double-click.

    A ``wx.ListBox`` emits no item-activated event (unlike ``wx.ListCtrl``'s
    ``EVT_LIST_ITEM_ACTIVATED``), so binding only ``EVT_LISTBOX_DCLICK`` leaves the
    action unreachable for keyboard and screen-reader users. This binds the
    double-click **and** Enter / NumpadEnter / Space (when an item is selected),
    calling *handler* for both. The key event is consumed on activation so the
    dialog's default button does not also fire. *handler* takes the wx event, so an
    existing double-click handler works unchanged.
    """
    import wx

    listbox.Bind(wx.EVT_LISTBOX_DCLICK, handler)

    def _on_key(event: object) -> None:
        code = event.GetKeyCode()
        has_selection = listbox.GetSelection() != wx.NOT_FOUND
        if has_selection and code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            handler(event)
            return  # consume so the modal default button does not also activate
        event.Skip()

    listbox.Bind(wx.EVT_KEY_DOWN, _on_key)


def _selected_book_page(control: object) -> object | None:
    """Return the currently selected page of a *book* control, else ``None``.

    Book controls (``wx.Notebook`` and its ``Listbook`` / ``Treebook`` /
    ``Choicebook`` / ``Toolbook`` / ``Simplebook`` / ``AuiNotebook`` siblings)
    show only their selected page; the other pages are hidden. Detected by the
    ``*book`` class-name suffix so a leaf control that merely exposes
    ``GetSelection`` (``ListBox``, ``Choice``, ``ComboBox``) is never mistaken
    for a page container.
    """
    if not type(control).__name__.lower().endswith("book"):
        return None
    get_selection = getattr(control, "GetSelection", None)
    get_page = getattr(control, "GetPage", None)
    if not callable(get_selection) or not callable(get_page):
        return None
    try:
        index = get_selection()
    except Exception:
        return None
    if not isinstance(index, int) or index < 0:
        return None
    try:
        return get_page(index)
    except Exception:
        return None


def _iter_descendant_controls(widget: object) -> Iterable[object]:
    """Yield a widget's descendants in creation (tab) order, depth-first.

    A book control is confined to its selected page (see
    :func:`_selected_book_page`): initial-focus routing must land on the first
    control of the tab the user actually sees, never a hidden page's control and
    never the tab strip itself (the notebook is not a preferred-focus class, so
    it is skipped as a focus target regardless). This is what keeps a tabbed
    dialog from opening with focus parked on the tab control instead of the
    first field inside the active tab.
    """
    get_children = getattr(widget, "GetChildren", None)
    if not callable(get_children):
        return
    try:
        children = list(get_children())
    except Exception:
        return
    for child in children:
        yield child
        page = _selected_book_page(child)
        if page is not None:
            yield from _iter_descendant_controls(page)
        else:
            yield from _iter_descendant_controls(child)


def _is_focusable(control: object) -> bool:
    is_enabled = getattr(control, "IsEnabled", None)
    is_shown = getattr(control, "IsShown", None)
    can_focus = getattr(control, "CanAcceptFocus", None)
    try:
        if callable(is_enabled) and not is_enabled():
            return False
        if callable(is_shown) and not is_shown():
            return False
        if callable(can_focus) and not can_focus():
            return False
    except Exception:
        return False
    return callable(getattr(control, "SetFocus", None))


def _has_explicit_focus(dialog: object) -> bool:
    """Return True if a *content* control already holds focus, or the dialog
    opted out of auto-focus.

    A construction-time ``content.SetFocus()`` is reflected by ``HasFocus()``
    even before the dialog is shown, so honouring it lets dialogs that
    deliberately target a specific field keep their intended initial focus.
    A focused *button*, by contrast, is the platform's default auto-park (the
    very bug this helper fixes) and is therefore not treated as explicit.

    A dialog may force its initial focus to be kept — even on a button — by
    setting a truthy ``_quill_keep_initial_focus`` attribute (used by the rare
    dialog whose primary action button should hold focus, e.g. crash recovery).
    """
    if getattr(dialog, "_quill_keep_initial_focus", False):
        return True
    preferred_set = set(_PREFERRED_FOCUS_CLASSES)
    for control in _iter_descendant_controls(dialog):
        has_focus = getattr(control, "HasFocus", None)
        if not callable(has_focus):
            continue
        try:
            focused = has_focus()
        except Exception:
            continue
        if focused and type(control).__name__ in preferred_set:
            return True
    return False


def find_primary_focus_target(
    dialog: object,
    *,
    preferred: Sequence[str] = _PREFERRED_FOCUS_CLASSES,
) -> object | None:
    """Return the first preferred, focusable content control inside *dialog*.

    Walks the dialog's descendants in tab order and returns the first control
    whose class name matches *preferred* and that can currently accept focus.
    Returns ``None`` when no such control exists (e.g. a button-only dialog),
    leaving the platform's default focus untouched.
    """
    preferred_set = set(preferred)
    for control in _iter_descendant_controls(dialog):
        if type(control).__name__ in preferred_set and _is_focusable(control):
            return control
    return None


def focus_primary_control(
    dialog: object,
    *,
    preferred: Sequence[str] = _PREFERRED_FOCUS_CLASSES,
) -> object | None:
    """Move initial focus to the dialog's first content control, if any.

    Honours an explicit initial focus already set during construction (so
    dialogs that deliberately target a specific control are left untouched).
    Otherwise moves focus to the first content control, keeping custom dialogs
    from opening with focus parked on their OK button — which hides the
    dialog's purpose from keyboard and screen-reader users. Idempotent and
    side-effect-free when no suitable control is found.
    """
    if _has_explicit_focus(dialog):
        return None
    target = find_primary_focus_target(dialog, preferred=preferred)
    if target is None:
        return None
    set_focus = getattr(target, "SetFocus", None)
    if callable(set_focus):
        try:
            set_focus()
        except Exception:
            return None
    return target


# The "Entered/Exited <name> dialog" cues are opt-out via the
# announce_dialog_transitions setting. Standalone dialogs call the module
# helpers below directly (no MainFrame in scope), so the shell registers a
# live lookup here at startup; None (bare unit tests, no shell) keeps the
# cues on, matching the MainFrame wrappers' fallback for test doubles.
_transition_announcement_policy: Callable[[], bool] | None = None


def set_transition_announcement_policy(policy: Callable[[], bool] | None) -> None:
    """Register the live announce_dialog_transitions lookup (None resets)."""
    global _transition_announcement_policy
    _transition_announcement_policy = policy


def _transition_cues_enabled() -> bool:
    if _transition_announcement_policy is None:
        return True
    try:
        return bool(_transition_announcement_policy())
    except Exception:
        return True


def show_modal_dialog(
    dialog: object,
    label: str,
    *,
    announce: Callable[[str], None] | None = None,
    enter_region: Callable[[str], None] | None = None,
    exit_region: Callable[[str], None] | None = None,
) -> int:
    """Show a modal dialog with optional region and announcement hooks."""
    speak_transitions = announce is not None and _transition_cues_enabled()
    if enter_region is not None:
        enter_region(label)
    if speak_transitions:
        announce(f"Entered {label} dialog")
    try:
        result = dialog.ShowModal()
    finally:
        if speak_transitions:
            announce(f"Exited {label} dialog")
        if exit_region is not None:
            exit_region(label)
    return result


def show_message_box(
    message: str,
    caption: str,
    style: int,
    parent: object = None,
    *,
    announce: Callable[[str], None] | None = None,
) -> int:
    """Show a wx.MessageBox with enter/exit announcements.

    Drop-in replacement for raw ``wx.MessageBox`` calls that ensures screen
    readers hear a region-entry cue before the dialog appears and an exit cue
    after it closes.
    """
    import wx

    speak_transitions = announce is not None and _transition_cues_enabled()
    if speak_transitions:
        announce(f"Entered {caption} dialog")
    try:
        result = wx.MessageBox(message, caption, style, parent)
    finally:
        if speak_transitions:
            announce(f"Exited {caption} dialog")
    return result
