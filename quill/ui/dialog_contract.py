from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

# accessible_label / set_accessible_name are re-exported here because the
# #994 naming sweep imports them from this module at its ~100 call sites.
# The implementation lives in accessible_names: its native NSAccessibility
# push is the part VoiceOver actually hears — the SetName-only versions
# these re-exports replace were live-verified inaudible on macOS (#1012).
from quill.ui.accessible_names import accessible_label as accessible_label
from quill.ui.accessible_names import ensure_accessible_names
from quill.ui.accessible_names import set_accessible_name as set_accessible_name

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


def dialog_alive(dialog: object) -> bool:
    """Return True when *dialog* is still safe to touch from a UI callback.

    Background threads in several AI dialogs (AI Hub auto-probe / list-models /
    test-connection, Thesaurus lookup, Document Q&A ask, Model Panel download)
    post their result back to the UI thread via ``wx.CallAfter``. If the user
    closed the dialog before the background work finished, the queued callback
    would touch a destroyed ``wx.StaticText`` / ``wx.Button`` and raise
    ``RuntimeError: wrapped C/C++ object of type StaticText has been deleted``
    (#1067). Call this at the top of each such callback and no-op when False --
    the result is no longer relevant once the dialog is gone.

    Mirrors ``status_dialog.is_alive``. Best-effort: any failure to read the
    window state is treated as "not alive" so a torn-down window never crashes
    the callback that was trying to be careful.
    """
    try:
        return bool(dialog) and not dialog.IsBeingDeleted()
    except Exception:  # noqa: BLE001 - liveness check must never raise
        return False


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
    # macOS VoiceOver announces a control only by its own accessible name;
    # the neighbouring StaticText that Windows screen readers use is not
    # linked (#1012). Every modal dialog routes through here, so inferring
    # names at show time fixes all of them globally. Guarded: a naming
    # failure must never block a dialog from opening.
    try:
        ensure_accessible_names(dialog)
    except Exception:  # noqa: BLE001
        pass
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


def show_modeless_surface(
    frame: object,
    label: str,
    *,
    announce: Callable[[str], None] | None = None,
    enter_region: Callable[[str], None] | None = None,
) -> None:
    """Show a modeless surface *frame* with the same accessibility onboarding a
    modal dialog gets from :func:`show_modal_dialog`, minus the blocking loop.

    The radio window model converts heavy surfaces from ``wx.Dialog`` to modeless
    ``wx.Frame`` (so each carries the persistent menu bar + &Window menu). A
    modeless frame does not run its own event loop, so this only does the
    *entry* onboarding: infer accessible names (VoiceOver, #1012), announce
    region entry, show the frame, and move focus to its first content control.
    The matching *exit* side (region exit + "Exited ..." cue + WindowManager
    unregister + raising the previous window) belongs in the frame's own
    ``EVT_CLOSE`` handler, since teardown is event-driven, not inline.
    """
    try:
        ensure_accessible_names(frame)
    except Exception:  # noqa: BLE001 - a naming failure must never block the window
        pass
    if enter_region is not None:
        enter_region(label)
    if announce is not None and _transition_cues_enabled():
        announce(f"Entered {label}")
    show = getattr(frame, "Show", None)
    if callable(show):
        show()
    focus_primary_control(frame)


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


def bind_close_button(window: object, button: object, *, modeless: bool) -> None:
    """Make a Close/Cancel *button* actually close its *window*, either shape.

    A ``wx.Dialog`` handles ``ID_CANCEL`` for free, so a Close button wired to
    nothing still worked -- and every surface the radio window model converted
    to a modeless ``wx.Frame`` (Browse Stations, Find Stations, Manage
    Favorites, Schedule Recording) silently lost that, because a frame has no
    such handling. The button did nothing; only Escape closed the window
    (reported 2026-08-16). A button that looks like the way out and is not is
    worse than no button, so this is the one way both shapes wire it:
    ``Close()`` on a frame (its ``EVT_CLOSE`` does the teardown), ``EndModal``
    on a dialog.
    """
    import wx

    if button is None or window is None:
        return

    def _close(_event: object) -> None:
        if modeless:
            window.Close()  # type: ignore[attr-defined]
            return
        end_modal = getattr(window, "EndModal", None)
        if callable(end_modal):
            end_modal(wx.ID_CANCEL)
        else:  # a frame passed as modal: closing is still the right answer
            window.Close()  # type: ignore[attr-defined]

    button.Bind(wx.EVT_BUTTON, _close)  # type: ignore[attr-defined]
