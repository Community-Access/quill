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
    "listCtrlNameStr",
    "treeCtrl",
    "treelistctrl",
    "dataviewCtrl",
    "gauge",
    "slider",
    "searchCtrl",
    "SearchCtrl",
    "wxSpinCtrl",
    "wxSpinCtrlDouble",
    "grid",
    "stcwindow",
    "richTextCtrl",
    "editableListBox",
    "filepickerctrl",
    "dirpickerctrl",
    "datectrl",
    "timectrl",
    "colourpickerctrl",
    "fontpickerctrl",
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
    """Notebook/Listbook/Treebook/... — page containers, per dialog_contract."""
    return type(control).__name__.lower().endswith("book")


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
    return True


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
        if _class_matches(child, frozenset({"StaticBox"})):
            # A StaticBox is a *container* (StaticBoxSizer contents are its
            # children) whose label names the group, not any single field:
            # descend with a clean slate and keep the group boundary tight.
            _walk(child, unnamed, None)
            pending = None
            continue
        # Plain container (Panel, splitter, book page, ...): descend.
        pending = _walk(child, unnamed, None if _is_book(child) else pending)
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
