"""Find Streams from a Website: a results list you can work with.

The accessibility review of the design (radio-plan.md section 5, 2026-11-22)
asked for: counts in labels and results; every refill in one order (frozen,
refilled keeping the stream, thawed, list focused, then the sentence after);
never filtering to an empty list; fixed menu letters; QUILL's dialog contract;
and Scan This Stream's Server moving focus to the address field first. Each is
pinned here, with every key and accessible name.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.link_finder import PageScanResult, PageStreamCandidate
from quill.core.radio.playlist_formats import parse_playlist
from quill.core.sound_events import SoundEvent
from quill.ui.radio import find_streams_actions as actions
from quill.ui.radio import find_streams_menus as menus
from quill.ui.radio.link_finder_dialog import LinkFinderDialog

wx = pytest.importorskip("wx")


class _Tasks:
    def __init__(self) -> None:
        self.pending: list[dict[str, Any]] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> None:
        self.pending.append({"func": func, **kwargs})


class _Controller:
    def __init__(self) -> None:
        self.played: list[Any] = []

    def play_station(self, station: Any) -> None:
        self.played.append(station)

    def stop(self) -> None:
        pass


def _c(url: str, check: str = "live", **fields: Any) -> PageStreamCandidate:
    candidate = PageStreamCandidate(url=url, reason="audio tag", check=check)
    for name, value in fields.items():
        setattr(candidate, name, value)
    return candidate


def _rows() -> list[PageStreamCandidate]:
    return [
        _c("https://a.example/zulu", stream_name="Zulu FM", codec="MP3", bitrate_kbps=64),
        _c("https://a.example/alpha", stream_name="Alpha FM", codec="AAC", bitrate_kbps=128),
        _c("https://a.example/mike", stream_name="Mike FM", codec="MP3", bitrate_kbps=320),
        _c("https://a.example/slow", "not checked", check_note="it took too long to answer"),
    ]


@pytest.fixture
def d(wx_session_app: Any, wx_call_after: Any) -> Any:
    events: list[str] = []
    wx_call_after(lambda fn, *a, **k: (events.append("after"), fn(*a, **k)))
    frame = wx.Frame(None)
    said: list[str] = []
    sounds: list[str] = []
    used: list[Any] = []

    def announce(text: str, **kwargs: Any) -> None:
        events.append(f"say:{text}")
        said.append(text)
        sounds.append(kwargs.get("sound", ""))

    host = SimpleNamespace(
        frame=frame,
        _radio_controller=_Controller(),
        _task_manager=None,
        _safe_mode=False,
        _announce=announce,
        _radio_open_add_custom=used.append,
        _radio_favorites=RadioFavoritesStore(),
        _save_radio_favorites=lambda: events.append("saved"),
    )
    dlg = LinkFinderDialog(host)
    dlg._task_manager = _Tasks()
    yield SimpleNamespace(dlg=dlg, said=said, sounds=sounds, events=events, host=host, used=used)
    dlg._still_timer.Stop()
    dlg.dialog.Destroy()
    frame.Destroy()


def _scan(d: Any, rows: list[PageStreamCandidate], url: str = "https://a.example/") -> None:
    d.dlg._url_ctrl.ChangeValue(url)
    d.dlg._on_scan(None)
    task = d.dlg._task_manager.pending.pop()
    task["on_success"](None, PageScanResult("WXYZ", "", rows, checked=True))


def _texts(d: Any) -> list[str]:
    results = d.dlg._results
    return [results.GetItemText(row, 0) for row in range(results.GetItemCount())]


def _focused_url(d: Any) -> str:
    focused = d.dlg._list.focused()
    return focused.url if focused else ""


# -- refills -----------------------------------------------------------------------


def test_a_scan_fills_once_and_the_sentence_comes_after(d: Any) -> None:
    _scan(d, _rows())
    assert d.said == ["Found 3 live streams and 1 link not checked."]
    assert d.events[-2:] == ["after", "say:Found 3 live streams and 1 link not checked."]
    assert _focused_url(d) == "https://a.example/zulu"


def test_a_sort_keeps_focus_on_the_same_stream_and_says_once(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    d.dlg._results.Focus(1)  # Alpha FM
    order: list[str] = []
    real_fill = d.dlg._list.fill
    monkeypatch.setattr(d.dlg.dialog, "Freeze", lambda: order.append("freeze"))
    monkeypatch.setattr(d.dlg.dialog, "Thaw", lambda: order.append("thaw"))
    monkeypatch.setattr(
        d.dlg._list, "fill", lambda *a, **k: (order.append("fill"), real_fill(*a, **k))
    )
    monkeypatch.setattr(d.dlg._results, "SetFocus", lambda: order.append("focus list"))
    d.said.clear()
    d.dlg._choose_order("bitrate")
    assert order == ["freeze", "fill", "thaw", "focus list"]
    assert _texts(d)[:3] == [
        "Live: Mike FM, MP3, 320 kbps",
        "Live: Alpha FM, AAC, 128 kbps",
        "Live: Zulu FM, MP3, 64 kbps",
    ]
    assert _focused_url(d) == "https://a.example/alpha"
    assert d.said == ["Sorted by bitrate, highest first."]
    assert d.events[-2] == "after"


def test_choosing_what_is_already_on_repeats_the_sentence_without_a_refill(
    d: Any, monkeypatch: Any
) -> None:
    _scan(d, _rows())
    d.said.clear()
    monkeypatch.setattr(d.dlg._list, "fill", lambda *a, **k: pytest.fail("refilled"))
    d.dlg._choose_order("scan")
    assert d.said == ["Back in scan order."]


def test_a_filter_says_its_sentence_once_and_keeps_the_stream(d: Any) -> None:
    _scan(d, _rows())
    d.dlg._results.Focus(2)  # Mike FM, MP3
    d.said.clear()
    d.dlg._choose_filter(fmt="MP3")
    assert d.said == ["Showing 2 of 4 links: MP3 only."]
    assert _texts(d) == ["Live: Zulu FM, MP3, 64 kbps", "Live: Mike FM, MP3, 320 kbps"]
    assert _focused_url(d) == "https://a.example/mike"


def test_a_filter_never_empties_the_list(d: Any, monkeypatch: Any) -> None:
    rows = _rows()
    rows[1].check = "not checked"  # the only AAC row is not live
    _scan(d, rows)
    d.dlg._choose_filter(live_only=True)
    d.said.clear()
    monkeypatch.setattr(d.dlg._list, "fill", lambda *a, **k: pytest.fail("refilled"))
    d.dlg._choose_filter(fmt="AAC")
    assert d.said == ["No links are live AAC streams, so the list is unchanged."]
    assert d.dlg._state.format == ""


def test_a_new_scan_clears_the_filter_and_keeps_the_order(d: Any) -> None:
    _scan(d, _rows())
    d.dlg._choose_order("bitrate")
    d.dlg._choose_filter(fmt="MP3")
    d.said.clear()
    _scan(d, _rows())
    assert d.said == [
        "Found 3 live streams and 1 link not checked. Sorted by bitrate, highest first. "
        "The filter was cleared."
    ]
    assert len(_texts(d)) == 4


def test_the_listener_order_says_when_it_cannot_apply(d: Any) -> None:
    rows = _rows()
    rows[0].listeners = 5
    _scan(d, rows)
    d.dlg._choose_order("listeners")
    d.said.clear()
    _scan(d, _rows())
    assert d.said[-1].endswith("In scan order: this page gave no listener counts.")


# -- keys --------------------------------------------------------------------------


class _Key:
    def __init__(self, code: int, modifiers: int) -> None:
        self.code, self.modifiers, self.skipped = code, modifiers, False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx's name
        return self.code

    def GetModifiers(self) -> int:  # noqa: N802
        return self.modifiers

    def Skip(self) -> None:  # noqa: N802
        self.skipped = True


def _press(d: Any, monkeypatch: Any, code: int, mods: int, *, focus: Any) -> _Key:
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: focus))
    key = _Key(code, mods)
    d.dlg._on_char_hook(key)
    return key


def test_ctrl_a_and_ctrl_c_act_only_in_the_list(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    copied: list[str] = []
    monkeypatch.setattr(
        "quill.ui.say_commands.set_clipboard_text", lambda t: copied.append(t) or True
    )
    d.said.clear()
    assert _press(d, monkeypatch, ord("A"), wx.MOD_CONTROL, focus=d.dlg._url_ctrl).skipped
    assert _press(d, monkeypatch, ord("C"), wx.MOD_CONTROL, focus=d.dlg._url_ctrl).skipped
    assert d.said == [] and copied == []
    assert not _press(d, monkeypatch, ord("A"), wx.MOD_CONTROL, focus=d.dlg._results).skipped
    assert d.said == ["Selected all 4 links."]
    assert not _press(d, monkeypatch, ord("A"), wx.MOD_CONTROL, focus=d.dlg._results).skipped
    assert d.said[-1] == "All 4 links are already selected."
    assert not _press(d, monkeypatch, ord("C"), wx.MOD_CONTROL, focus=d.dlg._results).skipped
    assert d.said[-1] == "Copied 4 stream links."
    assert copied[-1].splitlines()[0] == "https://a.example/zulu"


def test_modifiers_match_exactly(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    shift_ctrl = wx.MOD_CONTROL | wx.MOD_SHIFT
    # Ctrl+Shift+C is Chapters, Ctrl+Shift+A is not Select All.
    assert _press(d, monkeypatch, ord("C"), shift_ctrl, focus=d.dlg._results).skipped
    assert _press(d, monkeypatch, ord("A"), shift_ctrl, focus=d.dlg._results).skipped
    assert _press(d, monkeypatch, wx.WXK_UP, wx.MOD_CONTROL, focus=d.dlg._results).skipped


def test_the_keys(wx_session_app: Any) -> None:
    key = menus.key_command
    assert key(wx, ord("A"), wx.MOD_CONTROL) == "select_all"
    assert key(wx, ord("C"), wx.MOD_CONTROL) == "copy"
    assert key(wx, ord("F"), wx.MOD_CONTROL) == "find"
    assert key(wx, ord("S"), wx.MOD_CONTROL) == "save"
    assert key(wx, wx.WXK_F3, wx.MOD_NONE) == "find_next"
    assert key(wx, wx.WXK_F3, wx.MOD_SHIFT) == "find_previous"
    assert key(wx, ord("C"), wx.MOD_CONTROL | wx.MOD_SHIFT) is None
    assert key(wx, ord("X"), wx.MOD_CONTROL) is None


# -- Find --------------------------------------------------------------------------


class _Prompt:
    answer = wx.ID_OK if hasattr(wx, "ID_OK") else 5100
    value = ""
    shown_value = ""
    destroyed_after: list[str] = []

    def __init__(self, parent: Any, message: str, title: str, value: str = "") -> None:
        type(self).shown_value = value

    def GetValue(self) -> str:  # noqa: N802
        return type(self).value

    def Destroy(self) -> None:  # noqa: N802
        type(self).destroyed_after.append("destroyed")

    def SetAffirmativeId(self, _id: int) -> None:  # noqa: N802
        pass

    def SetEscapeId(self, _id: int) -> None:  # noqa: N802
        pass


@pytest.fixture
def prompt(monkeypatch: Any) -> type[_Prompt]:
    _Prompt.destroyed_after = []
    monkeypatch.setattr(wx, "TextEntryDialog", _Prompt)
    monkeypatch.setattr(
        "quill.ui.dialog_contract.show_modal_dialog", lambda dlg, label, **k: _Prompt.answer
    )
    return _Prompt


def test_find_lands_on_the_match_before_the_prompt_goes(d: Any, prompt: Any) -> None:
    _scan(d, _rows())
    prompt.value = "mike"
    d.said.clear()
    d.dlg._find()
    assert _focused_url(d) == "https://a.example/mike"
    assert d.dlg._list.selected_candidates()[0].url == "https://a.example/mike"
    assert d.said == []  # the row is read; nothing else to say
    # F3 again: the only match is where we are.
    d.dlg._find_again(backwards=False)
    assert d.said == ["That is the only match."]


def test_find_keeps_the_last_term_and_cancel_does_nothing(d: Any, prompt: Any) -> None:
    _scan(d, _rows())
    prompt.value = "fm"
    d.dlg._find()
    prompt.answer = wx.ID_CANCEL
    d.dlg._find()
    assert prompt.shown_value == "fm"
    prompt.answer = wx.ID_OK
    d.dlg._find_again(backwards=False)
    assert _focused_url(d) == "https://a.example/mike"  # zulu, alpha, then mike


def test_f3_with_no_term_opens_find(d: Any, prompt: Any) -> None:
    _scan(d, _rows())
    prompt.value = "nothing like it"
    d.dlg._find_again(backwards=False)
    assert d.said[-1] == "Nothing in the list matches 'nothing like it'."


def test_find_names_matches_hidden_by_the_filter(d: Any, prompt: Any) -> None:
    _scan(d, _rows())
    d.dlg._choose_filter(fmt="MP3")
    prompt.value = "alpha"
    d.dlg._find()
    assert d.said[-1] == "Nothing shown matches 'alpha'; 1 link that does is hidden by the filter."


# -- the actions ---------------------------------------------------------------------


def test_one_stream_is_added_with_no_question(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    monkeypatch.setattr(actions, "_ask_folder", lambda *a: pytest.fail("asked"))
    d.dlg._add()
    assert d.said[-1] == "Added Zulu FM to Favorites."
    assert d.sounds[-1] == SoundEvent.RADIO_FAVORITE_ADDED
    assert "saved" in d.events


def test_several_go_into_a_folder_and_duplicates_are_counted(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    asked: list[tuple[int, str]] = []
    monkeypatch.setattr(
        actions,
        "_ask_folder",
        lambda wx_, parent, count, value, say: asked.append((count, value)) or "WXYZ",
    )
    d.dlg._add()  # Zulu alone
    d.dlg._list.select_all()
    d.dlg._enable_row_buttons()
    assert d.dlg._add_btn.GetLabel() == "Add 4 to &Favorites"
    assert d.dlg._save_btn.GetLabel() == "Save 4 as Play&list..."
    d.dlg._add()
    assert asked == [(4, "WXYZ")]  # prefilled with the page title
    assert d.said[-1] == "Added 3 streams to Favorites, in the folder WXYZ; 1 was already there."
    store = d.host._radio_favorites
    assert "WXYZ" in store.folder_names()


def test_cancelling_the_folder_adds_nothing(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    monkeypatch.setattr(actions, "_ask_folder", lambda *a: None)
    d.dlg._list.select_all()
    d.said.clear()
    d.dlg._add()
    assert d.said == []
    assert d.host._radio_favorites.favorites == []


class _Chooser:
    path = ""
    index = 0

    def __init__(self, *a: Any, **k: Any) -> None:
        pass

    def GetFilterIndex(self) -> int:  # noqa: N802
        return type(self).index

    def GetPath(self) -> str:  # noqa: N802
        return type(self).path

    def Destroy(self) -> None:  # noqa: N802
        pass


@pytest.mark.parametrize(("index", "extension"), [(0, "m3u"), (1, "pls"), (2, "xspf"), (3, "asx")])
def test_saving_each_format_reads_back(
    d: Any, monkeypatch: Any, tmp_path: Path, index: int, extension: str
) -> None:
    _scan(d, _rows())
    _Chooser.path, _Chooser.index = str(tmp_path / "WXYZ"), index
    monkeypatch.setattr(wx, "FileDialog", _Chooser)
    monkeypatch.setattr(
        "quill.ui.dialog_contract.show_modal_dialog", lambda dlg, label, **k: wx.ID_OK
    )
    d.dlg._list.select_all()
    d.dlg._save()
    saved = tmp_path / f"WXYZ.{extension}"
    assert d.said[-1] == f"Saved 4 streams to WXYZ.{extension}."
    stations = parse_playlist(saved.read_text(encoding="utf-8"), url=str(saved))
    assert [s.stream_url for s in stations] == [c.url for c in _rows()]


def test_copy_with_nothing_selected_copies_the_focused_link(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    copied: list[str] = []
    monkeypatch.setattr(
        "quill.ui.say_commands.set_clipboard_text", lambda t: copied.append(t) or True
    )
    for row in range(d.dlg._results.GetItemCount()):
        d.dlg._results.Select(row, False)
    d.dlg._results.Focus(1)
    d.dlg._copy()
    assert copied == ["https://a.example/alpha"]
    assert d.said[-1] == "Copied the stream link."


def test_scan_this_streams_server_moves_focus_to_the_address_first(
    d: Any, monkeypatch: Any
) -> None:
    rows = [_c("http://radio.example.net:8000/live", stream_name="WXYZ", codec="MP3")]
    _scan(d, rows, url="https://www.station.example/")
    order: list[str] = []
    real_change = d.dlg._url_ctrl.ChangeValue
    monkeypatch.setattr(
        d.dlg._url_ctrl, "ChangeValue", lambda v: (order.append(f"value:{v}"), real_change(v))
    )
    monkeypatch.setattr(d.dlg._url_ctrl, "SetFocus", lambda: order.append("focus"))
    monkeypatch.setattr(d.dlg, "_on_scan", lambda _e: order.append("scan"))
    d.dlg._scan_server()
    assert order == ["value:http://radio.example.net:8000/", "focus", "scan"]


# -- what is shown, named and spoken -------------------------------------------------


def test_the_details_field_follows_focus_and_says_nothing(d: Any) -> None:
    rows = _rows()
    rows[1].listeners = 12
    _scan(d, rows)
    d.said.clear()
    d.dlg._list.go_to(1)
    details = d.dlg._list.details.GetValue().splitlines()
    assert details == [
        "Name: Alpha FM",
        "Status: Live stream",
        "Format: AAC, 128 kbps",
        "Listeners: 12",
        "Link: https://a.example/alpha",
        "Server: https://a.example",
        "Found by: audio tag",
    ]
    assert d.said == []


def test_the_tab_order_and_the_labels(wx_session_app: Any, wx_call_after: Any) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # SetHelpText stores nothing without one
    wx_call_after()
    frame = wx.Frame(None)
    host = SimpleNamespace(
        frame=frame,
        _radio_controller=_Controller(),
        _task_manager=None,
        _safe_mode=False,
        _announce=lambda *a, **k: None,
    )
    dlg = LinkFinderDialog(host)
    try:
        _check_tab_order_and_labels(dlg)
    finally:
        dlg._still_timer.Stop()
        dlg.dialog.Destroy()
        frame.Destroy()


def _check_tab_order_and_labels(dlg: Any) -> None:
    focusable = [w for w in dlg.dialog.GetChildren() if not isinstance(w, wx.StaticText)]
    assert focusable == [
        dlg._url_ctrl,
        dlg._scan_btn,
        dlg._results,
        dlg._list.details,
        dlg._sort_btn,
        dlg._test_btn,
        dlg._use_btn,
        dlg._add_btn,
        dlg._save_btn,
        focusable[-1],
    ]
    labels = [w.GetLabel() for w in focusable[4:]]
    assert labels == [
        "S&ort and Filter",
        "&Test",
        "&Use This Link...",
        "Add to &Favorites",
        "Save as Play&list...",
        "Close",
    ]
    statics = [w.GetLabel() for w in dlg.dialog.GetChildren() if isinstance(w, wx.StaticText)]
    assert "St&reams found" in statics and "Stream &details" in statics
    for control in (dlg._results, dlg._list.details, dlg._sort_btn, dlg._add_btn, dlg._save_btn):
        assert control.GetHelpText(), control


def test_the_sort_and_filter_menu_letters(d: Any) -> None:
    rows = _rows()
    rows[0].listeners = 3
    rows[2].codec = "Ogg Opus"
    _scan(d, rows)
    menu = d.dlg._sort_menu()
    try:
        labels = [item.GetItemLabel() for item in menu.GetMenuItems()]
        assert labels == [
            "&Scan order",
            "&Name, A to Z",
            "&Bitrate, highest first",
            "L&isteners, most first",
            "",
            "&Live streams only",
            "",
            "&All formats",
            "&MP3 only",
            "AA&C only",
            "O&pus only",
        ]
        assert menu.GetMenuItems()[0].IsChecked()
        assert menu.GetMenuItems()[7].IsChecked()
    finally:
        menu.Destroy()


def test_the_context_menu_letters_and_keys(d: Any) -> None:
    rows = [_c("http://radio.example.net:8000/live", stream_name="WXYZ", codec="MP3")]
    _scan(d, rows, url="https://www.station.example/")
    menu = d.dlg._context_menu()
    try:
        labels = [item.GetItemLabel() for item in menu.GetMenuItems()]
    finally:
        menu.Destroy()
    assert labels == [
        "&Test",
        "&Use This Link...",
        "Add to &Favorites",
        "Save as Play&list...",
        "&Copy Stream Link\tCtrl+C",
        "&Scan This Stream's Server",
        "",
        "F&ind...\tCtrl+F",
        "Find &Next\tF3",
        "Find &Previous\tShift+F3",
        "Select &All\tCtrl+A",
        "",
        "S&ort and Filter",
    ]
    letters = [label.split("&")[1][0].lower() for label in labels if "&" in label]
    assert len(letters) == len(set(letters))


def test_no_server_item_for_the_pages_own_host_and_no_menu_on_an_empty_list(
    d: Any, monkeypatch: Any
) -> None:
    _scan(d, _rows())
    menu = d.dlg._context_menu()
    try:
        assert "&Scan This Stream's Server" not in [i.GetItemLabel() for i in menu.GetMenuItems()]
    finally:
        menu.Destroy()
    d.dlg._on_scan_done(None, RuntimeError("gone"))
    monkeypatch.setattr(d.dlg._results, "PopupMenu", lambda *a: pytest.fail("menu opened"))
    d.dlg._open_context_menu()


def test_test_and_use_act_on_the_focused_row(d: Any) -> None:
    _scan(d, _rows())
    d.dlg._results.Focus(2)
    d.dlg._on_test(None)
    assert d.host._radio_controller.played[-1].stream_url == "https://a.example/mike"
    d.dlg._on_use(None)
    assert d.used[-1].stream_url == "https://a.example/mike"
