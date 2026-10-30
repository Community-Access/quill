"""``set_spoken_name`` reaches the name a Windows screen reader speaks (#1693).

``SetName`` is inert on wxMSW, so the only proof that matters is the MSAA
``accName`` of the control's own window. The probe below asks for it the way
NVDA and JAWS do (``AccessibleObjectFromWindow`` with ``OBJID_CLIENT``), in
process, on a frame that is never shown.
"""

from __future__ import annotations

import ctypes
import gc
import sys
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.ui.spoken_name import set_spoken_name, spoken_name  # noqa: E402

_OBJID_CLIENT = -4


@pytest.fixture()
def panel(wx_session_app: Any) -> Any:
    frame = wx.Frame(None)
    yield wx.Panel(frame)
    frame.Destroy()
    wx_session_app.Yield()


def _acc_name(window: Any, child: int = 0) -> str | None:
    """The MSAA ``accName`` a screen reader reads for *window*."""
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
    return ptr.accName(child)


def test_the_name_is_cleaned_like_a_label_and_the_window_name_is_kept(panel: Any) -> None:
    """Window names double as F1 topic keys, so the helper must not touch them."""
    field = wx.TextCtrl(panel, name="search.query")
    assert set_spoken_name(field, "&Search:") is True
    assert spoken_name(field) == "Search"
    assert field.GetName() == "search.query"


def test_an_empty_name_is_refused(panel: Any) -> None:
    field = wx.TextCtrl(panel)
    assert set_spoken_name(field, "") is False
    assert set_spoken_name(None, "Name") is False
    assert spoken_name(field) == ""


def test_renaming_updates_the_live_helper(panel: Any) -> None:
    field = wx.TextCtrl(panel)
    set_spoken_name(field, "First")
    set_spoken_name(field, "Second")
    assert spoken_name(field) == "Second"


@pytest.mark.skipif(sys.platform != "win32", reason="MSAA is Windows-only")
def test_msaa_reads_the_name_and_it_survives_garbage_collection(panel: Any) -> None:
    """The helper must outlive the call: an unreferenced one speaks as absent."""
    field = wx.TextCtrl(panel)
    button = wx.Button(panel, label="")  # the picture-only shape from the issue
    set_spoken_name(field, "Station search")
    set_spoken_name(button, "Play")
    gc.collect()
    assert _acc_name(field) == "Station search"
    assert _acc_name(button) == "Play"


@pytest.mark.skipif(sys.platform != "win32", reason="MSAA is Windows-only")
def test_list_rows_keep_their_own_names(panel: Any) -> None:
    """Child id 0 is the list; its rows must not all speak as the list."""
    rows = wx.ListBox(panel, choices=["Alpha", "Beta"])
    set_spoken_name(rows, "Results")
    assert _acc_name(rows) == "Results"
    assert _acc_name(rows, 1) == "Alpha"
    assert _acc_name(rows, 2) == "Beta"


@pytest.mark.skipif(sys.platform != "win32", reason="MSAA is Windows-only")
def test_a_spin_double_names_its_inner_edit(panel: Any) -> None:
    spin = wx.SpinCtrlDouble(panel)
    set_spoken_name(spin, "Speed")
    assert _acc_name(spin) == "Speed"
    inner = [child for child in spin.GetChildren() if isinstance(child, wx.TextCtrl)]
    for child in inner:
        assert _acc_name(child) == "Speed"
