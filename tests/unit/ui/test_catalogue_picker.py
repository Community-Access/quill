"""The shared catalogue picker, and the promise its help exemption makes.

One dialog serves many catalogues -- ACB Media Podcasts today, Community Picks
next -- so its window title is the *caller's*, not a literal. GATE-RADIO-HELP
cannot resolve a title it cannot see, so the dialog is listed in
``radio_help_audit.TITLE_EXEMPT`` with a reason that ends "pinned by
test_catalogue_picker". This is that pin: if a caller ever passes a title with
no purpose paragraph, F1 on that window would answer nothing, and the exemption
would have hidden it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from quill.core.radio import surface_help

_ROOT = Path(__file__).resolve().parents[3]
_UI_RADIO = _ROOT / "quill" / "ui" / "radio"
_PICKER = _UI_RADIO / "catalogue_picker_dialog.py"


def _callers() -> list[Path]:
    """Every module that opens the shared picker."""
    return [
        path
        for path in sorted(_UI_RADIO.glob("*.py"))
        if path != _PICKER and "choose_from_catalogue(" in path.read_text(encoding="utf-8")
    ]


def test_the_picker_has_at_least_one_caller() -> None:
    """A shared dialog nobody opens is an unreachable surface (GATE-REACH),
    and this test would otherwise pass vacuously forever."""
    assert _callers(), "nothing opens choose_from_catalogue"


def test_every_caller_passes_a_title_the_help_catalogue_knows() -> None:
    """The whole content of the TITLE_EXEMPT promise."""
    unknown: list[str] = []
    for path in _callers():
        source = path.read_text(encoding="utf-8")
        # Titles are module constants by convention (_TITLE = "..."), which is
        # what makes them greppable here and readable at the call site.
        for name, value in re.findall(r'^(_\w*TITLE\w*)\s*=\s*"([^"]+)"', source, re.M):
            if not surface_help.is_known_title(value):
                unknown.append(f"{path.name}::{name} = {value!r}")
    assert not unknown, (
        "these window titles have no purpose paragraph in surface_help.PURPOSES, "
        "so F1 would answer nothing: " + ", ".join(unknown)
    )


def test_no_caller_passes_a_bare_string_title() -> None:
    """A literal at the call site would escape the constant-based check above.

    Not a style rule: the check that keeps F1 honest reads module constants, so
    a title written inline is a title nothing verifies.
    """
    offenders: list[str] = []
    for path in _callers():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name != "choose_from_catalogue":
                continue
            for keyword in node.keywords:
                if keyword.arg == "title" and isinstance(keyword.value, ast.Constant):
                    offenders.append(f"{path.name}: title={keyword.value.value!r}")
    assert not offenders, (
        "pass the title as a module constant so test_catalogue_picker can verify "
        "it: " + ", ".join(offenders)
    )


def test_every_control_in_the_picker_carries_help() -> None:
    """Belt and braces over the audit: this window is the one place a listener
    meets forty unfamiliar names, so every control has to explain itself."""
    source = _PICKER.read_text(encoding="utf-8")

    assert source.count("SetHelpText(") >= 8
    # The two lists are the window; both must be reachable and explained.
    assert "apply_listbox_activation(self._available_list" in source
    assert "apply_listbox_activation(self._chosen_list" in source


def test_the_description_is_a_field_not_a_label() -> None:
    """Static text cannot be tabbed to, arrowed through, or re-read a word at a
    time -- and the description is the whole reason somebody can choose."""
    source = _PICKER.read_text(encoding="utf-8")
    block = source[source.index("self._description = ") :]

    assert "TE_READONLY" in block[:400]
    assert "TE_MULTILINE" in block[:400]
