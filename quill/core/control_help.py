"""The app-agnostic half of F1 context help: roles, composition, fallback.

Every Quill app answers F1 the same way -- the window's purpose, then the
control under focus -- and the pieces that do not depend on which app you are
in live here: the role-usage sentences ("A tree: Up and Down move between
rows..."), the body composition that layers authored help, the accessible
name, and the role line so no control ever answers with nothing, and the
generic window purpose a surface falls back to before its app has authored
one.

Grew out of Quill Radio's F1 build-out (2026-08-23) when the experience was
wired family-wide: the radio-specific purpose catalogue stays in
:mod:`quill.core.radio.surface_help`, which re-exports these helpers so its
callers and tests are unchanged. Other apps register only the wiring for now
and author their catalogues later -- the composition here already gives their
controls a real answer (name + help text + role) in the meantime.

wx-free and pure, like every ``quill.core`` module.
"""

from __future__ import annotations

#: The honest fallback for a window whose app has not authored a purpose yet.
#: Deliberately app-neutral: it is the floor every surface stands on, and an
#: app's own catalogue (gated, in Radio's case) is what lifts it.
GENERIC_PURPOSE = (
    "A window in this app. Tab moves between its controls, Escape closes it, "
    "and F1 on any control explains that control."
)

#: How to *use* a control, by wx class name -- the closing line of the control
#: section, so even a control with no authored help still answers F1 with its
#: name, its role, and how to drive it.
_ROLE_USAGE: dict[str, str] = {
    "Button": "A button: press Enter or Space to press it.",
    "ToggleButton": (
        "A toggle button: press Space to switch it, and it stays pressed until you switch it back."
    ),
    "CheckBox": "A checkbox: press Space to check or uncheck it.",
    "TextCtrl": (
        "A text field: type into it, or arrow through it to review what it "
        "says. If it is read-only, the text is there to be read and copied."
    ),
    "SearchCtrl": "A search field: type what you are looking for.",
    "TreeCtrl": (
        "A tree: Up and Down move between rows, Right expands a folder, Left "
        "collapses it, Enter acts on the row, and Shift+F10 lists everything "
        "else you can do to it."
    ),
    "ListCtrl": (
        "A list: Up and Down move between rows, Enter acts on the row, and "
        "Shift+F10 lists everything else you can do to it."
    ),
    "ListBox": "A list: Up and Down move between rows, and Enter acts on the row.",
    "CheckListBox": (
        "A list of checkboxes: Up and Down move between rows, Space checks or unchecks the row."
    ),
    "Choice": "A dropdown: Alt+Down opens it, Up and Down choose, Enter picks.",
    "ComboBox": "A combo box: type a value, or Alt+Down to open the list and choose.",
    "Slider": (
        "A slider: Left and Right (or Up and Down) nudge it, Page Up and "
        "Page Down move it in bigger steps, Home and End jump to the ends."
    ),
    "SpinCtrl": "A number field: type a value, or Up and Down to step it.",
    "RadioButton": "One choice in a group: arrow between the options; landing on one selects it.",
    "Gauge": "A progress readout; it fills as the work completes.",
    "StaticText": "A label; it names what sits next to it.",
}

_GENERIC_USAGE = "Tab moves on to the next control; Shift+Tab goes back."


def role_usage(class_name: str) -> str:
    """One sentence on driving a control of wx class *class_name*."""
    return _ROLE_USAGE.get(class_name, _GENERIC_USAGE)


def compose_control_body(*, accessible_name: str, help_text: str, usage: str) -> str:
    """The control section's body, from whichever of the pieces exist.

    Never empty: with nothing authored it still says what the control is
    called and how to drive its kind. Pieces are separated by blank lines and
    never repeated -- a help text that IS the accessible name appears once.
    """
    parts: list[str] = []
    name = accessible_name.strip()
    help_body = help_text.strip()
    if help_body:
        parts.append(help_body)
    if name and name.lower() not in help_body.lower():
        parts.insert(0, f"{name}.")
    if usage:
        parts.append(usage)
    return "\n\n".join(parts) if parts else _GENERIC_USAGE
