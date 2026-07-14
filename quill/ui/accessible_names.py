"""Accessible names for input controls — the macOS VoiceOver label fix (#1012).

Windows screen readers (NVDA/JAWS) infer a control's accessible name from the
neighbouring ``wx.StaticText`` and the ``&``-mnemonic; wxMSW exposes that
association through MSAA/UIA, so a bare ``wx.TextCtrl`` next to a label reads
correctly. macOS VoiceOver does **not** synthesize that association: a control
is announced only by its own accessible name (wxOSX maps ``wx.Window.SetName``
to ``NSAccessibility``'s label), and when none was set there is nothing to
speak but the value — the Settings font-size spin reads "0", the SSH port
reads "22".

This module is the global fix. :func:`ensure_accessible_names` walks a widget
tree in creation order and gives every *labelable* control that still carries
wx's default window name an accessible name inferred from the nearest
preceding ``wx.StaticText`` — the same association Windows screen readers
already make, applied once at show time. It is wired into
:func:`quill.ui.dialog_contract.show_modal_dialog`, which every modal dialog
already routes through, so hand-rolled dialogs get correct VoiceOver names
without per-site edits. Non-modal surfaces call it (or
:func:`set_accessible_name`) explicitly.

Two hard rules keep this safe:

* **Never rename an explicitly named control.** Window names are overloaded in
  this codebase: F1 context help uses ``GetName()`` as its topic key
  (``name="wizard.kb_pack_choice"``, see :mod:`quill.ui.context_help`) and
  :mod:`quill.ui.audio_studio.wizard` looks widgets up with
  ``FindWindowByName``. Only controls whose name is still a wx *default*
  (``"text"``, ``"choice"``, ``"wxSpinCtrl"``, ...) are ever touched.
* **Composite controls propagate their name to their inner children.** On
  macOS ``wx.SpinCtrl`` is an inner ``NSTextField`` plus a stepper; VoiceOver
  lands on the inner text field, which does not inherit the composite's name
  (support#69). Any labelable control that has a real name gets that name
  copied onto its default-named labelable descendants, generalizing the
  inner-child workaround that previously lived inline in
  ``voice_browser_dialog.py`` and ``main_frame.py``.

Everything here is duck-typed (no module-level ``wx`` import) so unit tests
can drive it with fakes, and every wx call is guarded — a naming failure must
never break showing a dialog. Names are applied on all platforms: wxMSW keeps
its window name as an inert string (MSAA/UIA never read it), so Windows
behaviour is unchanged, and running everywhere keeps the walker testable on
Windows CI.
"""

from __future__ import annotations

import sys

#: Controls that VoiceOver announces by their wx window name and that carry no
#: visible label of their own — the "value only" bug surface. CheckBox /
#: RadioButton / Button are absent on purpose: they are self-labeled.
_LABELABLE_CLASSES: frozenset[str] = frozenset({
    "TextCtrl",
    "SearchCtrl",
    "Choice",
    "ComboBox",
    "BitmapComboBox",
    "OwnerDrawnComboBox",
    "ListBox",
    "CheckListBox",
    "ListCtrl",
    "ListView",
    "EditableListBox",
    "TreeCtrl",
    "TreeListCtrl",
    "DataViewCtrl",
    "DataViewListCtrl",
    "DataViewTreeCtrl",
    "SpinCtrl",
    "SpinCtrlDouble",
    "Slider",
    "Gauge",
    "FilePickerCtrl",
    "DirPickerCtrl",
    "DatePickerCtrl",
    "TimePickerCtrl",
    "ColourPickerCtrl",
    "FontPickerCtrl",
    "Grid",
    "StyledTextCtrl",
    "RichTextCtrl",
})

#: Self-labeled interactive controls. They never receive an inferred name, and
#: they *consume* any pending label: a StaticText followed by one of these was
#: not labelling a later field, so the label must not leak forward.
_SELF_LABELED_CLASSES: frozenset[str] = frozenset({
    "Button",
    "BitmapButton",
    "CommandLinkButton",
    "ToggleButton",
    "BitmapToggleButton",
    "CheckBox",
    "RadioButton",
    "RadioBox",
    "HyperlinkCtrl",
})

#: wx default window names that mark a control as "never explicitly named".
#: The live set is augmented from ``wx.*NameStr`` constants at first use (see
#: :func:`_default_control_names`); these literals cover the constants that
#: are not exported under ``wx.*NameStr`` (spin controls, STC, richtext) and
#: keep the walker working when the fakes-based tests run without wx.
_FALLBACK_DEFAULT_NAMES: frozenset[str] = frozenset({
    "text",
    "choice",
    "comboBox",
    "listBox",
    "listCtrl",
    "treeCtrl",
    "wxTreeListCtrl",
    "dataviewCtrl",
    "gauge",
    "slider",
    "searchCtrl",
    "wxSpinCtrl",
    "wxSpinCtrlDouble",
    "grid",
    "stcwindow",
    "richTextCtrl",
    "editableListBox",
    "filepicker",
    "dirpicker",
    "datectrl",
    "timectrl",
    "colourpicker",
    "fontpicker",
    "panel",
    "check",
    "button",
    "staticText",
})

#: A StaticText longer than this is prose (instructions, descriptions), not a
#: field label; it must never become a control's accessible name, and it ends
#: any pending label (a paragraph starts a new context). Sentence breaks
#: (". ") disqualify a text the same way — see :func:`_is_field_label`.
_MAX_LABEL_LENGTH = 60

_default_names_cache: frozenset[str] | None = None


def _default_control_names() -> frozenset[str]:
    """Every window name wx assigns by default (i.e. "no one named this").

    Collected once from the ``wx.*NameStr`` constants so the set tracks the
    running wx version, unioned with :data:`_FALLBACK_DEFAULT_NAMES` for the
    defaults wx does not export as constants. Falls back to the literal set
    when wx is unavailable (fakes-based unit tests).
    """
    global _default_names_cache
    if _default_names_cache is None:
        names = set(_FALLBACK_DEFAULT_NAMES)
        try:
            import wx

            for attr in dir(wx):
                if attr.endswith("NameStr"):
                    value = getattr(wx, attr, None)
                    # wxPython Phoenix exports these as bytes (b"text").
                    if isinstance(value, bytes):
                        value = value.decode("ascii", "ignore")
                    if isinstance(value, str) and value:
                        names.add(value)
        except Exception:  # noqa: BLE001 - no wx in fakes-based tests
            pass
        _default_names_cache = frozenset(names)
    return _default_names_cache


def _class_matches(control: object, class_names: frozenset[str]) -> bool:
    """True when *control*'s class (or any base) is in *class_names*.

    MRO matching (not exact-name matching) so project subclasses of wx
    controls are still recognized, while remaining fake-friendly.
    """
    return any(base.__name__ in class_names for base in type(control).__mro__)


def _is_book(control: object) -> bool:
    """Notebook/Listbook/Treebook/... — page containers, per dialog_contract.

    MRO-walked like :func:`_class_matches` so project subclasses of a book
    control keep the page boundary.
    """
    return any(base.__name__.lower().endswith("book") for base in type(control).__mro__)


def accessible_label(label: object) -> str:
    """Reduce a visible ``StaticText`` label to a speakable accessible name.

    Strips the ``&`` keyboard mnemonic (``&&`` stays a literal ``&``), a
    trailing ellipsis, and the trailing ``:`` that visual label rows carry.
    """
    text = str(label or "")
    text = text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")
    text = text.strip()
    while True:
        trimmed = text.rstrip(":…").rstrip()
        while trimmed.endswith("..."):
            trimmed = trimmed[:-3].rstrip()
        if trimmed == text:
            return text
        text = trimmed


def _get_name(control: object) -> str:
    get_name = getattr(control, "GetName", None)
    if not callable(get_name):
        return ""
    try:
        return str(get_name() or "")
    except Exception:  # noqa: BLE001
        return ""


def _has_default_name(control: object) -> bool:
    name = _get_name(control)
    return not name or name in _default_control_names()


def _set_name(control: object, name: str) -> bool:
    set_name = getattr(control, "SetName", None)
    if not callable(set_name):
        return False
    try:
        set_name(name)
    except Exception:  # noqa: BLE001
        return False
    # The wx window name alone is NOT what VoiceOver speaks: wxOSX never
    # bridges it (or wxAccessible, which is MSW-only) into NSAccessibility.
    # Live VoiceOver testing of #1012 confirmed SetName-only changes are
    # inaudible — the native label push below is the part that talks.
    _macos_native_label(control, name)
    return True


# Cached PyObjC module: None = not yet attempted, False = unavailable.
_objc_cache: object = None


def _objc_import() -> object:
    """Import PyObjC's ``objc`` once (bundled by the [macos] extra)."""
    global _objc_cache
    if _objc_cache is None:
        try:
            import objc  # type: ignore[import-not-found]

            _objc_cache = objc
        except Exception:  # noqa: BLE001 - not installed / not macOS
            _objc_cache = False
    return _objc_cache


def _macos_native_label(control: object, name: str) -> None:
    """Push *name* onto the control's native ``NSAccessibility`` label.

    On macOS, ``wx.Window.GetHandle()`` returns the underlying ``NSView``
    as a bare integer; PyObjC's ``objc.objc_object(c_void_p=...)`` wraps it
    so ``setAccessibilityLabel:`` can be called — the attribute VoiceOver
    actually announces. Multiline text controls hand back the enclosing
    ``NSScrollView``, while VoiceOver focuses its ``documentView``
    (``NSTextView``), so the label is set on both. Guarded end to end: a
    failure here must never break naming or dialog display, and on
    non-darwin platforms this is an immediate no-op.
    """
    if sys.platform != "darwin":
        return
    objc = _objc_import()
    if not objc:
        return
    get_handle = getattr(control, "GetHandle", None)
    if not callable(get_handle):
        return
    try:
        handle = get_handle()
    except Exception:  # noqa: BLE001
        return
    if not handle:
        return
    try:
        ns_view = objc.objc_object(c_void_p=handle)
        try:
            document_view = ns_view.documentView()
        except Exception:  # noqa: BLE001 - not an NSScrollView
            document_view = None
        if document_view is not None:
            document_view.setAccessibilityLabel_(name)
        ns_view.setAccessibilityLabel_(name)
    except Exception:  # noqa: BLE001
        return


def pin_macos_text_area_role(control: object, label: str) -> None:
    """#616: pin a text control's NSAccessibility role to ``AXTextArea``.

    wx's default shim may report the editor as a generic group, so VoiceOver
    does not announce it as editable text. The role string is passed literally
    rather than imported from AppKit (the constant's exported name has moved
    between releases; the AX string is the stable contract). Silent no-op off
    macOS, without PyObjC, or on any native failure.
    """
    if sys.platform != "darwin":
        return
    objc = _objc_import()
    if not objc:
        return
    get_handle = getattr(control, "GetHandle", None)
    if not callable(get_handle):
        return
    try:
        handle = get_handle()
    except Exception:  # noqa: BLE001
        return
    if not handle:
        return
    try:
        ns_view = objc.objc_object(c_void_p=handle)
        try:
            target = ns_view.documentView() or ns_view
        except Exception:  # noqa: BLE001 - not an NSScrollView
            target = ns_view
        target.setAccessibilityRole_("AXTextArea")
        target.setAccessibilityLabel_(label)
    except Exception:  # noqa: BLE001
        return


def _get_children(widget: object) -> list[object]:
    get_children = getattr(widget, "GetChildren", None)
    if not callable(get_children):
        return []
    try:
        return list(get_children())
    except Exception:  # noqa: BLE001
        return []


def _propagate_name_to_inner_children(control: object, name: str) -> None:
    """Copy *name* onto default-named labelable descendants of a composite.

    VoiceOver focuses the *inner* field of composite controls (the
    ``NSTextField`` inside ``wx.SpinCtrl``/``wx.ComboBox``, the ``ListCtrl``
    inside ``EditableListBox``), and the inner field does not inherit the
    composite's name (support#69). Explicitly named children are left alone.
    """
    if not name:
        return
    for child in _get_children(control):
        if _class_matches(child, _LABELABLE_CLASSES) and _has_default_name(child):
            _set_name(child, name)
        _propagate_name_to_inner_children(child, name)


def set_accessible_name(control: object, label: object) -> None:
    """Name *control* (and its composite inner children) from a visible label.

    The one call sites need: cleans the label text, names the control, and
    handles the spin-control inner ``TextCtrl`` so the number box is announced
    with its label on macOS. Safe on every platform and with test fakes.
    """
    name = accessible_label(label)
    if not name:
        return
    if _set_name(control, name):
        _propagate_name_to_inner_children(control, name)


def _label_text(static_text: object) -> str:
    # GetLabelText strips mnemonics natively; fall back to GetLabel + our own
    # stripping for fakes.
    for getter in ("GetLabelText", "GetLabel"):
        get = getattr(static_text, getter, None)
        if callable(get):
            try:
                return accessible_label(get())
            except Exception:  # noqa: BLE001
                continue
    return ""


def _is_field_label(label: str) -> bool:
    """Short, single-clause text is a field label; anything else is prose."""
    return len(label) <= _MAX_LABEL_LENGTH and ". " not in label


def _walk(widget: object, unnamed: list[object], pending: str | None) -> str | None:
    """Depth-first, creation-order walk carrying the "pending label" state.

    Mirrors the association Windows screen readers make: the most recent
    ``StaticText`` labels the *next* labelable control. The pending label is
    consumed by the first labelable or self-labeled control that follows it,
    flows into plain containers (a label above a row ``Panel`` still labels
    the row's field), and is dropped at book-control boundaries (a label
    before a Notebook does not label the first field of page one).
    """
    for child in _get_children(widget):
        if _class_matches(child, frozenset({"StaticText"})):
            label = _label_text(child)
            if label:
                pending = label if _is_field_label(label) else None
            continue
        if _class_matches(child, _LABELABLE_CLASSES):
            if _has_default_name(child):
                if pending:
                    set_accessible_name(child, pending)
                else:
                    unnamed.append(child)
            else:
                # Already named (explicitly, or via constructor ``name=``):
                # leave the name alone — it may be an F1 help-topic key or a
                # FindWindowByName target — but still sync composite children
                # so a named-composite spin control reads correctly.
                _propagate_name_to_inner_children(child, _get_name(child))
            pending = None
            continue
        if _class_matches(child, _SELF_LABELED_CLASSES):
            pending = None
            continue
        if _is_book(child):
            # A book's pages are isolated contexts: a page must neither
            # inherit a label from before the book nor from the previous
            # page's trailing label, and a label dangling at the end of the
            # last page must not name the sibling after the book. Walk every
            # page (book child) with its own clean slate.
            for page in _get_children(child):
                _walk(page, unnamed, None)
            pending = None
            continue
        if _class_matches(child, frozenset({"StaticBox"})):
            # A StaticBox is a *container* (StaticBoxSizer contents are its
            # children) whose label names the group, not any single field:
            # descend with a clean slate and keep the group boundary tight.
            _walk(child, unnamed, None)
            pending = None
            continue
        # Plain container (Panel, splitter, ...): descend, pending flows in
        # and any unconsumed label flows back out to later siblings.
        pending = _walk(child, unnamed, pending)
    return pending


def ensure_accessible_names(root: object) -> list[object]:
    """Infer accessible names across *root*'s widget tree; return the misses.

    Idempotent (a second pass finds nothing default-named that has a label)
    and side-effect-free for explicitly named controls. The returned list of
    still-unnamed labelable controls exists for tests and diagnostics; callers
    wired into dialog plumbing ignore it.
    """
    unnamed: list[object] = []
    _walk(root, unnamed, None)
    return unnamed
