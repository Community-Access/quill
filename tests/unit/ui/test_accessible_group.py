"""The group-caption helper: a check box or radio button says which group it is in.

Jeff found it testing the QUILL Lite portable (2026-11-23): in Scribe Options
the "Default formats" check boxes read "Word, check box, not checked" with no
word of what Word was for, and the "Open each result when it is ready" radio
box read its choices without its question. :mod:`quill.ui.accessible_group`
answers MSAA's ``accDescription`` with the caption and leaves ``accName`` as
the visible label. These tests prove what the accessible object answers; what
NVDA and JAWS then say needs the live check listed in the pull request.
"""

from __future__ import annotations

import sys
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.ui import accessible_group as ag  # noqa: E402

pytestmark = pytest.mark.usefixtures("wx_session_app")

windows_only = pytest.mark.skipif(
    sys.platform != "win32" or not hasattr(wx, "Accessible"),
    reason="wx.Accessible is Windows-only",
)


@pytest.fixture
def dialog() -> Any:
    frame = wx.Dialog(None, title="Group test")
    yield frame
    frame.Destroy()


def _group(dialog: Any, caption: str, *labels: str) -> tuple[Any, list[Any]]:
    box = wx.StaticBoxSizer(wx.VERTICAL, dialog, caption)
    checks = []
    for label in labels:
        check = wx.CheckBox(box.GetStaticBox(), label=label)
        box.Add(check)
        checks.append(check)
    return box, checks


def test_group_name_reads_a_caption_a_box_or_its_sizer(dialog: Any) -> None:
    box, _ = _group(dialog, "&Default formats:")
    assert ag.group_name(box) == "Default formats"
    assert ag.group_name(box.GetStaticBox()) == "Default formats"
    assert ag.group_name("Open each result &when it is ready") == (
        "Open each result when it is ready"
    )
    assert ag.group_name(object()) == ""


_OBJID_CLIENT = -4


def _msaa(window: Any) -> Any:
    """The IAccessible NVDA and JAWS ask for (``AccessibleObjectFromWindow``)."""
    import ctypes

    comtypes_client = pytest.importorskip("comtypes.client")
    comtypes_client.GetModule("oleacc.dll")
    from comtypes.gen.Accessibility import IAccessible

    ptr = ctypes.POINTER(IAccessible)()
    ctypes.oledll.oleacc.AccessibleObjectFromWindow(
        window.GetHandle(),
        ctypes.c_long(_OBJID_CLIENT),
        ctypes.byref(IAccessible._iid_),
        ctypes.byref(ptr),
    )
    return ptr


@windows_only
def test_the_name_stays_the_label_and_the_description_is_the_group(dialog: Any) -> None:
    box, (word, epub) = _group(dialog, "Default formats", "Word", "&EPUB")
    epub.SetValue(True)
    before = _msaa(epub).accState(0)
    assert ag.describe_group(box, word, epub) == 2
    # The name is not answered by the helper: Windows' own label stands.
    assert word.GetAccessible().GetName(0)[0] == wx.ACC_NOT_IMPLEMENTED
    assert _msaa(word).accName(0) == "Word"
    assert _msaa(epub).accName(0) == "EPUB"
    assert _msaa(word).accDescription(0) == "Default formats"
    assert ag.group_description(epub) == "Default formats"
    # Role and checked state are still the control's own.
    assert _msaa(epub).accRole(0) == 44  # ROLE_SYSTEM_CHECKBUTTON
    assert _msaa(epub).accState(0) == before
    # Only the control itself: anything else falls through to the standard object.
    assert word.GetAccessible().GetDescription(1)[0] == wx.ACC_NOT_IMPLEMENTED


@windows_only
def test_the_help_text_is_kept_after_the_group(dialog: Any) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)
    box, (word,) = _group(dialog, "Default formats", "Word")
    word.SetHelpText("Checked in the convert dialog.")
    assert _msaa(word).accDescription(0) == "Checked in the convert dialog."  # wxMSW's own
    ag.describe_group(box, word)
    assert _msaa(word).accDescription(0) == "Default formats. Checked in the convert dialog."
    assert _msaa(word).accHelp(0) == "Checked in the convert dialog."


@windows_only
def test_a_name_given_on_purpose_wins_either_way_round(dialog: Any) -> None:
    from quill.ui.spoken_name import set_spoken_name, spoken_name

    box, (word, epub) = _group(dialog, "Default formats", "Word", "EPUB")
    ag.describe_group(box, word)
    set_spoken_name(word, "Word document")
    set_spoken_name(epub, "EPUB book")
    ag.describe_group(box, epub)
    for control, name in ((word, "Word document"), (epub, "EPUB book")):
        assert _msaa(control).accName(0) == name
        assert _msaa(control).accDescription(0) == "Default formats"
        assert spoken_name(control) == name


@windows_only
def test_the_fallback_spoken_name_names_the_group_helper(dialog: Any) -> None:
    """Without SetAccessibleName, set_spoken_name must not replace the helper."""
    from quill.ui import spoken_name as sn

    box, (word,) = _group(dialog, "Default formats", "Word")
    ag.describe_group(box, word)
    assert sn._attach(word, "Word document") is getattr(word, ag._HELPER_ATTR)
    assert word.GetAccessible().GetName(0) == (wx.ACC_OK, "Word document")
    assert ag.group_description(word) == "Default formats"


@windows_only
def test_the_helper_is_kept_alive_and_describing_again_updates_it(dialog: Any) -> None:
    box, (word,) = _group(dialog, "Default formats", "Word")
    ag.describe_group(box, word)
    helper = getattr(word, ag._HELPER_ATTR)
    assert helper in getattr(dialog, ag._ANCHOR_ATTR)
    assert ag.describe_group("What you want back", word) == 1
    assert getattr(word, ag._HELPER_ATTR) is helper
    assert _msaa(word).accDescription(0) == "What you want back"


def test_no_op_without_wx_accessible(dialog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ag, "_MEMBER_CLASS", False)
    box, (word,) = _group(dialog, "Default formats", "Word")
    assert ag.describe_group(box, word) == 0
    assert getattr(word, ag._HELPER_ATTR, None) is None
    assert ag.group_description(word) == ""


def test_no_op_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ag, "_MEMBER_CLASS", None)
    monkeypatch.setattr(ag.sys, "platform", "darwin")
    assert ag._member_class() is None


@windows_only
def test_an_empty_caption_describes_nothing(dialog: Any) -> None:
    box, (word,) = _group(dialog, "", "Word")
    assert ag.describe_group(box, word, None) == 0


# --------------------------------------------------------- GroupedRadioBox


def _radio(dialog: Any, **kwargs: Any) -> Any:
    kwargs.setdefault("label", "Open each result &when it is ready")
    kwargs.setdefault("choices", ["Open it", "Ask me first", "Don't open"])
    return ag.GroupedRadioBox(dialog, **kwargs)


def test_grouped_radio_box_answers_the_radio_box_calls(dialog: Any) -> None:
    box = _radio(dialog, majorDimension=1)
    assert box.GetCount() == 3
    assert box.GetSelection() == 0
    box.SetSelection(2)
    assert box.GetSelection() == 2
    assert box.GetStringSelection() == "Don't open"
    assert box.SetStringSelection("ask me first")
    assert box.GetSelection() == 1
    assert not box.SetStringSelection("Never")
    assert box.FindString("Open it") == 0
    assert box.GetString(5) == ""
    box.SetString(0, "Open it now")
    assert box.GetString(0) == "Open it now"
    assert box.GetLabel() == "Open each result &when it is ready"
    assert (box.GetColumnCount(), box.GetRowCount()) == (1, 3)
    box.EnableItem(2, False)
    assert not box.IsItemEnabled(2)
    assert box.IsItemEnabled(1)


def test_grouped_radio_box_lays_out_by_rows_or_columns(dialog: Any) -> None:
    by_cols = _radio(dialog, choices=list("abcde"), majorDimension=2)
    assert (by_cols.GetColumnCount(), by_cols.GetRowCount()) == (2, 3)
    by_rows = _radio(dialog, choices=list("abcde"), majorDimension=2, style=wx.RA_SPECIFY_ROWS)
    assert (by_rows.GetColumnCount(), by_rows.GetRowCount()) == (3, 2)
    one_row = _radio(dialog, choices=list("abc"))
    assert (one_row.GetColumnCount(), one_row.GetRowCount()) == (3, 1)


def test_grouped_radio_box_sends_evt_radiobox(dialog: Any) -> None:
    box = _radio(dialog)
    seen: list[tuple[int, str, Any]] = []
    dialog.Bind(
        wx.EVT_RADIOBOX, lambda e: seen.append((e.GetInt(), e.GetString(), e.GetEventObject())), box
    )
    button = box.buttons()[1]
    button.SetValue(True)
    event = wx.CommandEvent(wx.wxEVT_RADIOBUTTON, button.GetId())
    event.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(event)
    assert seen == [(1, "Ask me first", box)]


def test_grouped_radio_box_help_reaches_every_button(dialog: Any) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # SetHelpText stores nothing without one
    box = _radio(dialog)
    box.SetItemHelpText(2, "Only saved.")
    box.SetHelpText("When a result opens.")
    texts = [button.GetHelpText() for button in box.buttons()]
    assert texts == ["When a result opens.", "When a result opens.", "Only saved."]
    assert box.GetItemHelpText(2) == "Only saved."


@windows_only
def test_grouped_radio_box_buttons_carry_the_question(dialog: Any) -> None:
    box = _radio(dialog)
    for button, label in zip(box.buttons(), ["Open it", "Ask me first", "Don't open"], strict=True):
        assert _msaa(button).accName(0) == label
        assert _msaa(button).accRole(0) == 45  # ROLE_SYSTEM_RADIOBUTTON
        assert _msaa(button).accDescription(0) == "Open each result when it is ready"
    box.SetLabel("&Open results")
    assert _msaa(box.buttons()[0]).accDescription(0) == "Open results"


def test_the_access_key_is_read_from_the_caption() -> None:
    assert ag._access_key("Open each result &when it is ready") == "w"
    assert ag._access_key("Fish && &Chips") == "c"
    assert ag._access_key("No key") == ""
    assert ag._access_key("Trailing &") == ""


def test_the_access_key_hook_is_dialog_only_and_unhooked_on_destroy(dialog: Any) -> None:
    box = _radio(dialog)
    assert box._hooked is dialog
    frame = wx.Frame(None)
    try:
        assert _radio(frame)._hooked is None
    finally:
        frame.Destroy()
    box.Destroy()
    wx.GetApp().Yield()
    assert box._hooked is None or not box


def test_the_access_key_focuses_the_chosen_button(dialog: Any) -> None:
    box = _radio(dialog)
    box.SetSelection(1)
    focused: list[Any] = []
    box.buttons()[1].SetFocus = lambda: focused.append(1)  # type: ignore[method-assign]
    box.IsShownOnScreen = lambda: True  # type: ignore[method-assign]

    class _Key:
        def __init__(self, char: str, alt: bool = True) -> None:
            self.char, self.alt, self.skipped = char, alt, False

        def AltDown(self) -> bool:  # noqa: N802
            return self.alt

        def ControlDown(self) -> bool:  # noqa: N802
            return False

        def ShiftDown(self) -> bool:  # noqa: N802
            return False

        def GetUnicodeKey(self) -> int:  # noqa: N802
            return ord(self.char)

        def Skip(self) -> None:  # noqa: N802
            self.skipped = True

    other = _Key("x")
    box._on_char_hook(other)
    assert other.skipped and focused == []
    plain = _Key("W", alt=False)
    box._on_char_hook(plain)
    assert plain.skipped and focused == []
    mine = _Key("W")
    box._on_char_hook(mine)
    assert not mine.skipped and focused == [1]


def test_f1_reaches_the_box_from_any_of_its_choices(dialog: Any) -> None:
    """F1 topics are keyed on the focused window's name, which was the box's."""
    from quill.ui.app_context_help import _accessible_name

    box = _radio(dialog, name="batch_wizard.output_layout")
    button = box.buttons()[1]
    assert ag.radio_box_of(button) is box
    assert ag.radio_box_of(dialog) is None
    assert _accessible_name(button) == "batch_wizard.output_layout"
    box.SetName("Search direction")  # a name set later is followed too
    assert _accessible_name(button) == "Search direction"
