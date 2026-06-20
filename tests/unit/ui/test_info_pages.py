"""Unit tests for ``quill.ui.info_pages.show_about_quill_native``.

The About dialog was rewritten in #260 to use ``wx.Notebook`` with
Overview / Dependencies / Links tabs so JAWS in Forms mode reads the
version as a navigable element instead of flattening everything into a
single read-only blob. These source-level tests pin the dialog's
structure (3 tabs, button labels, dependency rows, link rows, visit
on Enter, Copy uses clipboard) without requiring a live wx event loop.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _info_pages_source() -> str:
    return (Path(__file__).resolve().parents[3] / "quill" / "ui" / "info_pages.py").read_text(
        encoding="utf-8"
    )


def _dialog_inventory() -> dict[str, str]:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "unit"
        / "ui"
        / "fixtures"
        / "dialog_inventory.json"
    )
    return json.loads(fixture.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Structural tests (no wx needed)
# ---------------------------------------------------------------------------


def test_show_about_quill_native_uses_notebook() -> None:
    # #260: the fix uses wx.Notebook so each section is a real tab JAWS
    # can navigate with Ctrl+Tab. A flat TextCtrl was the original bug.
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert "wx.Notebook" in about_fn


def test_show_about_quill_native_has_four_tabs() -> None:
    # Overview, Dependencies, Links, plus the Legal tab added with the
    # trademark/About-dialog hardening. The exact order is intentional
    # (Legal sits next to Overview so the independence notice is the
    # second thing a new user reads).
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    notebook_section = about_fn.split("notebook = wx.Notebook", 1)[1]
    addpage_calls = re.findall(r"notebook\.AddPage\([^,]+,\s*\"([^\"]+)\"", notebook_section)
    assert addpage_calls == ["Overview", "Legal", "Dependencies", "Links"]


def test_show_about_quill_native_has_legal_tab() -> None:
    """The Legal tab surfaces the independence notice, copyright, and license."""
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert 'notebook.AddPage(legal_panel, "Legal")' in about_fn
    assert "about_legal_text" in about_fn
    assert "independence_notice" in about_fn


def test_show_about_quill_native_title_uses_product_name() -> None:
    """The dialog title uses the AboutInfo.product_name, not a hard-coded string."""
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert '"About Quill"' not in about_fn
    assert "about_info.product_name" in about_fn


def test_show_about_quill_native_has_copy_support_info_button() -> None:
    """The About dialog has a Copy Support Info button that uses the clipboard."""
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert "about_copy_support" in about_fn
    assert "Copy Support Info" in about_fn
    assert "support_info" in about_fn


def test_show_about_quill_native_overview_includes_headline() -> None:
    # The first line JAWS reads on the Overview tab is the version headline.
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert "about_info.headline()" in about_fn


def test_show_about_quill_native_dependencies_uses_listctrl() -> None:
    # Dependency rows are a wx.ListCtrl so JAWS announces column headers.
    src = _info_pages_source()
    assert "about_dependency_list" in src
    assert "_build_dependency_list" in src


def test_show_about_quill_native_link_list_has_columns() -> None:
    # Links tab uses a wx.ListCtrl with Name and URL columns.
    src = _info_pages_source()
    assert "about_link_list" in src
    assert "_build_link_list" in src


def test_show_about_quill_native_has_visit_and_copy_buttons() -> None:
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert "about_link_visit" in about_fn
    assert "about_link_copy" in about_fn


def test_show_about_quill_native_visit_opens_browser() -> None:
    src = _info_pages_source()
    assert "import webbrowser" in src
    assert "webbrowser.open" in src


def test_show_about_quill_native_copy_uses_clipboard() -> None:
    src = _info_pages_source()
    assert "wx.TheClipboard" in src
    assert "wx.TextDataObject" in src


def test_show_about_quill_native_enter_on_row_visits() -> None:
    # EVT_LIST_ITEM_ACTIVATED on a row opens the URL so keyboard users get
    # one-press activation. Visit button is still available for mouse users.
    src = _info_pages_source()
    assert "EVT_LIST_ITEM_ACTIVATED" in src


def test_show_about_quill_native_still_applies_modal_ids() -> None:
    # dialog_button_contract gate requires apply_modal_ids in the same
    # function scope as the wx.Dialog constructor.
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert "apply_modal_ids" in about_fn


def test_show_about_quill_native_dialog_inventory_still_hardened_custom() -> None:
    # The dialog surface category must stay ``hardened_custom`` so the
    # dialog_inventory gate doesn't flag this commit as a regression.
    inventory = _dialog_inventory()
    key = "quill/ui/info_pages.py::show_about_quill_native::wx.Dialog"
    assert inventory.get(key) == "hardened_custom"


def test_show_about_quill_native_dependencies_section_handles_missing_metadata() -> None:
    # When pyproject.toml is absent the Dependencies tab shows a single
    # StaticText message rather than a broken list.
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert "about_dependencies_missing" in about_fn
    assert "Dependency metadata is not available" in about_fn


def test_show_about_quill_native_no_longer_uses_md_to_plain() -> None:
    # The old implementation flattened Markdown via _md_to_plain which is
    # exactly what made the dialog unreadable in JAWS Forms mode. The new
    # implementation must not call it.
    src = _info_pages_source()
    about_fn = _extract_function(src, "show_about_quill_native")
    assert "_md_to_plain" not in about_fn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_function(source: str, name: str) -> str:
    """Return the body of ``def name(...): ...`` from ``source``.

    Stops at the next top-level ``def`` or ``class``. Used by structural
    tests so they don't have to import the module (which would require
    wxPython).
    """
    start = re.search(rf"^def {re.escape(name)}\(", source, re.MULTILINE)
    assert start is not None, f"{name} not found"
    rest = source[start.start() :]
    next_def = re.search(r"^def\s+\w+\(|^class\s+\w+", rest[len(name) + 4 :], re.MULTILINE)
    if next_def is None:
        return rest
    return rest[: next_def.start() + len(name) + 4]
