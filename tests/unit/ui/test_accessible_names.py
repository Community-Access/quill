"""macOS VoiceOver accessible-name inference (#1012).

Real-wx tests drive :func:`ensure_accessible_names` over the exact
construction patterns used across the dialogs (label row, spin composite,
StaticBoxSizer contents, label-above-row-panel), and fakes cover the pieces a
Windows CI runner cannot exercise natively (the macOS-only inner ``TextCtrl``
child of a spin composite) plus the ``show_modal_dialog`` wiring.

No ``wx.YieldIfNeeded()`` here — see test_voice_browser_dialog.py's header for
why pumping the native event loop is forbidden in this suite.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.accessible_names import (
    accessible_label,
    ensure_accessible_names,
    set_accessible_name,
)
from quill.ui.dialog_contract import show_modal_dialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


# ---------------------------------------------------------------------------
# accessible_label
# ---------------------------------------------------------------------------


def test_accessible_label_strips_mnemonic_colon_and_ellipsis() -> None:
    assert accessible_label("&Word or phrase:") == "Word or phrase"
    assert accessible_label("Choose &file...:") == "Choose file"
    assert accessible_label("Font si&ze:") == "Font size"
    assert accessible_label("Export…") == "Export"
    assert accessible_label("Ampers&&and:") == "Ampers&and"
    assert accessible_label("") == ""
    assert accessible_label(None) == ""


# ---------------------------------------------------------------------------
# ensure_accessible_names — real wx
# ---------------------------------------------------------------------------


def test_label_row_names_the_following_control(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(panel, label="&Word or phrase:")
        term = wx.TextCtrl(panel)

        ensure_accessible_names(frame)

        assert term.GetName() == "Word or phrase"
    finally:
        frame.Destroy()


def test_spin_composite_is_named_from_label(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(panel, label="Font si&ze:")
        spin = wx.SpinCtrl(panel, min=0, max=100)

        ensure_accessible_names(frame)

        assert spin.GetName() == "Font size"
        # On macOS the composite's inner TextCtrl (what VoiceOver lands on)
        # must carry the same name; wxMSW has no inner child, so this loop is
        # exercised natively only on the mac CI runner (fakes cover it below).
        for child in spin.GetChildren():
            if isinstance(child, wx.TextCtrl):
                assert child.GetName() == "Font size"
    finally:
        frame.Destroy()


def test_named_composite_spin_children_are_synced(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        spin = wx.SpinCtrl(panel, min=1, max=65535, initial=22)
        spin.SetName("SSH port")

        ensure_accessible_names(frame)

        assert spin.GetName() == "SSH port"
        for child in spin.GetChildren():
            if isinstance(child, wx.TextCtrl):
                assert child.GetName() == "SSH port"
    finally:
        frame.Destroy()


def test_explicit_names_are_never_overwritten(wx_app) -> None:
    """Window names double as F1 help-topic keys and FindWindowByName targets."""
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(panel, label="Engine:")
        choice = wx.Choice(panel, choices=["a"], name="guided_speech_engine")

        ensure_accessible_names(frame)

        assert choice.GetName() == "guided_speech_engine"
    finally:
        frame.Destroy()


def test_self_labeled_control_consumes_the_pending_label(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(panel, label="Orphan label:")
        wx.Button(panel, label="Browse...")
        orphan = wx.TextCtrl(panel)

        leftovers = ensure_accessible_names(frame)

        assert orphan.GetName() == "text"  # wx default: untouched
        assert orphan in leftovers
    finally:
        frame.Destroy()


def test_static_box_contents_are_walked(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        box = wx.StaticBoxSizer(wx.StaticBox(panel, label="Settings"), wx.VERTICAL)
        sb = box.GetStaticBox()
        wx.StaticText(sb, label="Rate:")
        rate = wx.SpinCtrl(sb, min=75, max=650)

        ensure_accessible_names(frame)

        assert rate.GetName() == "Rate"
    finally:
        frame.Destroy()


def test_pending_label_flows_into_a_row_panel(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(panel, label="Sound pack:")
        row = wx.Panel(panel)
        field = wx.TextCtrl(row)

        ensure_accessible_names(frame)

        assert field.GetName() == "Sound pack"
    finally:
        frame.Destroy()


def test_prose_static_text_is_not_a_label(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(
            panel,
            label=(
                "Manage global sticky notes. Delete removes the selected note. Ctrl+C copies it."
            ),
        )
        notes = wx.ListCtrl(panel, style=wx.LC_REPORT)

        leftovers = ensure_accessible_names(frame)

        assert notes.GetName() == "listCtrl"  # wx default: untouched
        assert notes in leftovers
    finally:
        frame.Destroy()


def test_picker_composites_are_named_from_label(wx_app) -> None:
    """Review finding #1012-r1: wx exports ``*NameStr`` as bytes and the
    picker family's defaults are "filepicker"/"dirpicker"/... — with the
    wrong default set the walker treated a default-named DirPickerCtrl as
    explicitly named and stamped "dirpicker" onto its inner TextCtrl."""
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(panel, label="Starting folder:")
        picker = wx.DirPickerCtrl(panel)

        ensure_accessible_names(frame)

        assert picker.GetName() == "Starting folder"
        for child in picker.GetChildren():
            if isinstance(child, wx.TextCtrl):
                assert child.GetName() == "Starting folder"
    finally:
        frame.Destroy()


def test_pending_label_never_crosses_notebook_boundaries(wx_app) -> None:
    """Review finding #1012-r2: a trailing label on one page must not name
    the next page's first control, a label before the book must not name
    page one's first control, and a label dangling at the end of the book
    must not name the next sibling after it."""
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(panel, label="Before the book:")
        book = wx.Notebook(panel)
        page1 = wx.Panel(book)
        first_field = wx.TextCtrl(page1)
        wx.StaticText(page1, label="Restart required")
        page2 = wx.Panel(book)
        second_page_list = wx.ListBox(page2)
        book.AddPage(page1, "One")
        book.AddPage(page2, "Two")
        after = wx.TextCtrl(panel)

        leftovers = ensure_accessible_names(frame)

        assert first_field.GetName() == "text"
        assert second_page_list.GetName() == "listBox"
        assert after.GetName() == "text"
        assert {first_field, second_page_list, after} <= set(leftovers)
    finally:
        frame.Destroy()


def test_idempotent_second_pass_changes_nothing(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        wx.StaticText(panel, label="Port:")
        port = wx.TextCtrl(panel)

        ensure_accessible_names(frame)
        first = port.GetName()
        leftovers = ensure_accessible_names(frame)

        assert port.GetName() == first == "Port"
        assert port not in leftovers
    finally:
        frame.Destroy()


# ---------------------------------------------------------------------------
# Fakes — spin inner-child propagation (macOS-only structure) and wiring
# ---------------------------------------------------------------------------


class _FakeWindow:
    def __init__(self, name: str = "", children: list | None = None) -> None:
        self._name = name
        self._children = children or []

    def GetName(self) -> str:
        return self._name

    def SetName(self, name: str) -> None:
        self._name = name

    def GetChildren(self) -> list:
        return self._children


class TextCtrl(_FakeWindow):
    """Class name matters: the walker matches on the MRO's class names."""


class SpinCtrl(_FakeWindow):
    pass


class StaticText(_FakeWindow):
    def __init__(self, label: str) -> None:
        super().__init__()
        self._label = label

    def GetLabel(self) -> str:
        return self._label


class Dialog(_FakeWindow):
    def __init__(self, children: list) -> None:
        super().__init__(children=children)
        self.shown = False

    def ShowModal(self) -> int:
        self.shown = True
        return 0


def test_set_accessible_name_propagates_to_inner_text_child() -> None:
    """The macOS spin composite: VoiceOver lands on the inner TextCtrl."""
    inner = TextCtrl(name="text")
    spin = SpinCtrl(name="wxSpinCtrl", children=[inner])

    set_accessible_name(spin, "Rate (words per minute):")

    assert spin.GetName() == "Rate (words per minute)"
    assert inner.GetName() == "Rate (words per minute)"


def test_set_accessible_name_leaves_explicitly_named_children_alone() -> None:
    inner = TextCtrl(name="custom_child")
    spin = SpinCtrl(name="wxSpinCtrl", children=[inner])

    set_accessible_name(spin, "Volume")

    assert spin.GetName() == "Volume"
    assert inner.GetName() == "custom_child"


def test_walker_syncs_children_of_already_named_spins() -> None:
    """The 'composite-only SetName' legacy sites from #1012."""
    inner = TextCtrl(name="text")
    spin = SpinCtrl(name="SSH port", children=[inner])
    dialog = Dialog(children=[spin])

    ensure_accessible_names(dialog)

    assert inner.GetName() == "SSH port"


def test_show_modal_dialog_names_controls_before_showing() -> None:
    field = TextCtrl(name="text")
    dialog = Dialog(children=[StaticText("Port:"), field])

    show_modal_dialog(dialog, "Quick Connect")

    assert dialog.shown
    assert field.GetName() == "Port"


def test_show_modal_dialog_survives_a_walker_failure() -> None:
    class _ExplodingDialog(Dialog):
        def GetChildren(self) -> list:
            raise RuntimeError("boom")

    dialog = _ExplodingDialog(children=[])

    assert show_modal_dialog(dialog, "Anything") == 0
    assert dialog.shown


def test_ensure_accessible_names_tolerates_windowless_objects() -> None:
    assert ensure_accessible_names(object()) == []
