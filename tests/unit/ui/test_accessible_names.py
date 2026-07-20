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


class SpinButton(_FakeWindow):
    """The stepper half of the macOS spin composite."""


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


def test_spin_stepper_child_is_named_too() -> None:
    """Live #1012 finding: VoiceOver walks the stepper as its own object
    right after the edit field, and it announced nameless when only the
    TextCtrl child was covered."""
    inner = TextCtrl(name="text")
    stepper = SpinButton(name="spinButton")
    spin = SpinCtrl(name="wxSpinCtrl", children=[inner, stepper])

    set_accessible_name(spin, "Font size:")

    assert inner.GetName() == "Font size"
    assert stepper.GetName() == "Font size"


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


# ---------------------------------------------------------------------------
# macOS native NSAccessibility layer (fakes; the real path needs VoiceOver)
# ---------------------------------------------------------------------------
#
# Live #1012 testing showed wx.Window.SetName is inaudible to VoiceOver:
# wxOSX never bridges the wx name into NSAccessibility, so the helper must
# additionally wrap GetHandle()'s bare NSView pointer with PyObjC and call
# setAccessibilityLabel:. These fakes validate that plumbing cross-platform.


class _FakeNSView:
    def __init__(self, document_view: _FakeNSView | None = None) -> None:
        self.label: str | None = None
        self.role: str | None = None
        self._document_view = document_view

    def documentView(self) -> _FakeNSView:  # noqa: N802 - ObjC selector
        if self._document_view is None:
            raise AttributeError("documentView")  # plain NSView: no such selector
        return self._document_view

    def setAccessibilityLabel_(self, value: str) -> None:  # noqa: N802
        self.label = value

    def setAccessibilityRole_(self, value: str) -> None:  # noqa: N802
        self.role = value


class _FakeObjc:
    def __init__(self, view: _FakeNSView) -> None:
        self._view = view
        self.wrapped: list = []

    def objc_object(self, c_void_p=None) -> _FakeNSView:
        self.wrapped.append(c_void_p)
        return self._view


class _HandleTextCtrl(TextCtrl):
    def GetHandle(self) -> int:  # noqa: N802
        return 0xBEEF


def test_native_label_reaches_the_ns_view(monkeypatch) -> None:
    import quill.ui.accessible_names as an

    view = _FakeNSView()
    fake_objc = _FakeObjc(view)
    monkeypatch.setattr(an.sys, "platform", "darwin")
    monkeypatch.setattr(an, "_objc_cache", fake_objc)
    ctrl = _HandleTextCtrl(name="text")

    set_accessible_name(ctrl, "&Word or phrase:")

    assert ctrl.GetName() == "Word or phrase"
    assert view.label == "Word or phrase"
    assert fake_objc.wrapped == [0xBEEF]


def test_native_label_targets_the_scrollviews_document_view(monkeypatch) -> None:
    import quill.ui.accessible_names as an

    inner = _FakeNSView()
    scroll = _FakeNSView(document_view=inner)
    monkeypatch.setattr(an.sys, "platform", "darwin")
    monkeypatch.setattr(an, "_objc_cache", _FakeObjc(scroll))

    set_accessible_name(_HandleTextCtrl(name="text"), "Notes")

    assert inner.label == "Notes"
    assert scroll.label == "Notes"


class Choice(_FakeWindow):
    """Class name matters (Choice is labelable); carries a native handle."""

    def GetHandle(self) -> int:  # noqa: N802
        return 0xF00D


def test_walker_pushes_native_label_for_already_named_controls(monkeypatch) -> None:
    """Live #1012 finding: Settings' Theme choice is named via a direct
    SetName call, which never touched NSAccessibility — VoiceOver read just
    "System". The show-time walk must push the existing wx name natively."""
    import quill.ui.accessible_names as an

    view = _FakeNSView()
    monkeypatch.setattr(an.sys, "platform", "darwin")
    monkeypatch.setattr(an, "_objc_cache", _FakeObjc(view))
    theme = Choice(name="Theme")
    dialog = Dialog(children=[theme])

    ensure_accessible_names(dialog)

    assert theme.GetName() == "Theme"  # wx name untouched
    assert view.label == "Theme"  # but now audible


class CheckBox(_FakeWindow):
    """Self-labeled; class name matters for the walker's branch choice."""

    def GetHandle(self) -> int:  # noqa: N802
        return 0xCAFE


def test_walker_pushes_enriched_names_of_self_labeled_controls(monkeypatch) -> None:
    """Settings checkboxes carry "Label. Description" wx names; Windows
    hears them via MSAA, so macOS must get the same via the native push."""
    import quill.ui.accessible_names as an

    view = _FakeNSView()
    monkeypatch.setattr(an.sys, "platform", "darwin")
    monkeypatch.setattr(an, "_objc_cache", _FakeObjc(view))
    cb = CheckBox(name="Beta updates. Get prerelease builds first")
    dialog = Dialog(children=[cb])

    ensure_accessible_names(dialog)

    assert view.label == "Beta updates. Get prerelease builds first"


def test_walker_leaves_default_named_self_labeled_controls_alone(monkeypatch) -> None:
    """A plain checkbox announces its own title natively; no push needed."""
    import quill.ui.accessible_names as an

    view = _FakeNSView()
    monkeypatch.setattr(an.sys, "platform", "darwin")
    monkeypatch.setattr(an, "_objc_cache", _FakeObjc(view))
    dialog = Dialog(children=[CheckBox(name="check")])

    ensure_accessible_names(dialog)

    assert view.label is None


def test_walker_never_speaks_machine_key_names(monkeypatch) -> None:
    """Help-topic keys ("wizard.kb_pack_choice") must stay silent: speaking
    them would be worse than the current nameless announcement."""
    import quill.ui.accessible_names as an

    view = _FakeNSView()
    monkeypatch.setattr(an.sys, "platform", "darwin")
    monkeypatch.setattr(an, "_objc_cache", _FakeObjc(view))
    choice = Choice(name="wizard.kb_pack_choice")
    dialog = Dialog(children=[choice])

    ensure_accessible_names(dialog)

    assert choice.GetName() == "wizard.kb_pack_choice"
    assert view.label is None


def test_pin_macos_text_area_role_sets_role_and_label(monkeypatch) -> None:
    import quill.ui.accessible_names as an
    from quill.ui.accessible_names import pin_macos_text_area_role

    inner = _FakeNSView()
    scroll = _FakeNSView(document_view=inner)
    monkeypatch.setattr(an.sys, "platform", "darwin")
    monkeypatch.setattr(an, "_objc_cache", _FakeObjc(scroll))

    pin_macos_text_area_role(_HandleTextCtrl(name="text"), "Document")

    assert inner.role == "AXTextArea"
    assert inner.label == "Document"


def test_native_layer_is_inert_off_macos(monkeypatch) -> None:
    """Off darwin the native gate must short-circuit before touching PyObjC.

    Forces a non-darwin platform so this is exercised on EVERY runner. On the
    macOS-release CI job (which runs the full UI suite natively) the host is
    really darwin, so without this patch ``set_accessible_name`` would take the
    real native path and call ``objc.objc_object(c_void_p=...)`` on the fake
    ``_HandleTextCtrl`` handle (0xBEEF). Dereferencing that garbage NSView in
    Cocoa is a SIGSEGV -- not a Python exception the helper's try/except can
    catch -- and it took down the whole test job (exit 139).

    ``_objc_cache`` is reset because it is a process-global the real native
    path populates with the ``objc`` module the first time it runs: on the
    macOS runner an earlier test leaves it set, so asserting ``is None`` off a
    clean baseline is what actually proves *this* call never took the native
    path (which would repopulate it)."""
    import quill.ui.accessible_names as an

    monkeypatch.setattr(an.sys, "platform", "win32")
    monkeypatch.setattr(an, "_objc_cache", None)
    ctrl = _HandleTextCtrl(name="text")
    set_accessible_name(ctrl, "Port:")

    assert ctrl.GetName() == "Port"
    assert an._objc_cache is None  # never even attempted the import
