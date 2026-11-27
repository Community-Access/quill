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
    assert d.said[-1] == f"Saved 4 streams to WXYZ.{extension} in {tmp_path.name}."
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
        dlg._reopen_btn,
        focusable[-1],
    ]
    labels = [w.GetLabel() for w in focusable[4:]]
    assert labels == [
        "S&ort and Filter",
        "&Test",
        "&Use This Link...",
        "Add to &Favorites",
        "Save as Play&list...",
        "Reo&pen Last Results",
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
        "&Test\tEnter",
        "&Use This Link...",
        "Play &Random Stream\tCtrl+Shift+O",
        "Add to &Favorites",
        "Save as Play&list...\tCtrl+S",
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


# -- Reopen Last Results ---------------------------------------------------------


def test_reopen_is_dimmed_with_nothing_saved(d: Any) -> None:
    assert not d.dlg._reopen_btn.IsEnabled()
    d.dlg._on_reopen_last()
    assert d.said[-1] == "There are no saved results to reopen."


def test_a_scan_saves_and_reopen_restores_rows_order_filter_and_row(d: Any) -> None:
    from quill.core.radio import find_streams_view as view

    _scan(d, _rows())
    assert d.dlg._reopen_btn.IsEnabled()
    d.dlg._choose_order("name")
    d.dlg._choose_filter(fmt="MP3")
    d.dlg._results.Focus(1)
    d.dlg._remember_last()  # what closing the window does
    focused = _focused_url(d)

    # A new window, as after closing and opening Find Streams again.
    d.dlg._candidates, d.dlg._rows = [], []
    d.dlg._state = view.ViewState()
    d.dlg._list.clear()
    d.dlg._load_last()
    assert d.dlg._reopen_btn.IsEnabled()
    d.said.clear()
    d.host._radio_controller.played.clear()
    d.dlg._on_reopen_last()
    assert d.dlg._state == view.ViewState(order="name", format="MP3")
    assert len(_texts(d)) == 2 and _focused_url(d) == focused
    assert d.said[-1].startswith("Reopened 4 streams from a.example, found")
    assert d.said[-1].endswith("Nothing was scanned or played.")
    assert d.host._radio_controller.played == []
    assert d.dlg._task_manager.pending == []  # nothing rescans


def test_the_offer_is_said_when_results_wait(d: Any) -> None:
    _scan(d, _rows())
    d.dlg._remember_last()
    d.dlg._load_last()
    d.said.clear()
    d.dlg._offer_last()
    assert d.said == [
        "Your last results are saved: 4 streams from a.example. "
        "Choose Reopen Last Results to see them."
    ]


def test_a_search_that_finds_nothing_clears_the_saved_results(d: Any) -> None:
    _scan(d, _rows())
    assert d.dlg._reopen_btn.IsEnabled()
    _scan(d, [])
    assert not d.dlg._reopen_btn.IsEnabled()
    d.dlg._load_last()
    assert d.dlg._last is None


def test_damaged_saved_results_are_ignored_quietly(d: Any) -> None:
    from quill.ui.radio import find_streams_last

    folder = find_streams_last._directory()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "find_streams_last.json").write_text("{not json", encoding="utf-8")
    d.said.clear()
    d.dlg._load_last()
    d.dlg._offer_last()
    assert d.dlg._last is None and not d.dlg._reopen_btn.IsEnabled() and d.said == []


# -- Play Random Stream in the list ------------------------------------------------


def test_ctrl_shift_o_plays_a_random_shown_stream_and_says_which(d: Any) -> None:
    _scan(d, _rows())
    d.dlg._choose_filter(fmt="MP3")  # two rows shown: Zulu and Mike
    d.said.clear()
    d.dlg._run("random")
    played = d.host._radio_controller.played
    assert len(played) == 1 and played[0].stream_url in {
        "https://a.example/zulu",
        "https://a.example/mike",
    }
    assert d.said[-1].endswith("picked at random from 2 streams found.")
    d.dlg._run("random")
    assert played[1].stream_url != played[0].stream_url


def test_the_random_key_is_ctrl_shift_o_in_the_list() -> None:
    assert menus.key_command(wx, ord("O"), wx.MOD_CONTROL | wx.MOD_SHIFT) == "random"
    assert menus.key_command(wx, ord("O"), wx.MOD_CONTROL) is None


# -- Search sounds and live titles -------------------------------------------------


def _fail(d: Any) -> None:
    d.dlg._url_ctrl.ChangeValue("https://a.example/")
    d.dlg._on_scan(None)
    d.dlg._task_manager.pending.pop()["on_failure"](None, RuntimeError("down"))


def test_an_empty_search_and_a_failed_one_each_play_their_own_cue(d: Any) -> None:
    _scan(d, [])
    assert d.sounds[-1] == str(SoundEvent.RADIO_SEARCH_EMPTY)
    _fail(d)
    assert d.sounds[-1] == str(SoundEvent.RADIO_SEARCH_FAILED)


def test_a_search_that_finds_streams_adds_no_cue(d: Any) -> None:
    _scan(d, _rows())
    assert d.sounds == [""]


def test_the_off_switch_silences_the_cues_but_not_the_words(d: Any) -> None:
    d.host._radio_history = SimpleNamespace(find_streams_sounds=False)
    _scan(d, [])
    assert d.sounds[-1] == "" and d.said[-1]
    d.dlg._start_cues()
    assert not d.dlg._cue_timer.IsRunning()


def test_the_working_cue_runs_only_while_scanning(d: Any, monkeypatch: Any) -> None:
    posted: list[Any] = []
    monkeypatch.setattr(d.dlg, "_post_cue", lambda event: posted.append(event))
    d.dlg._url_ctrl.ChangeValue("https://a.example/")
    d.dlg._on_scan(None)
    assert d.dlg._cue_timer.IsRunning() and d.dlg._cue_timer.GetInterval() == 2000
    d.dlg._on_cue_timer(None)
    assert posted == [SoundEvent.RADIO_SEARCH_WORKING]
    d.dlg._task_manager.pending.pop()["on_success"](None, PageScanResult("W", "", [], checked=True))
    assert not d.dlg._cue_timer.IsRunning()
    d.dlg._on_cue_timer(None)  # a queued tick after the scan ended says nothing
    assert len(posted) == 1


def test_a_reported_name_is_shown_and_spoken_while_checking(d: Any) -> None:
    d.dlg._url_ctrl.ChangeValue("https://a.example/")
    d.dlg._on_scan(None)
    d.said.clear()
    d.dlg._show_title("KEXP 90.3")
    assert d.dlg._status.GetLabel() == "Checking KEXP 90.3."
    assert d.said == ["Checking KEXP 90.3."]
    d.dlg._show_title("WFMU")  # inside the gap: shown, not spoken
    assert d.dlg._status.GetLabel() == "Checking WFMU." and d.said == ["Checking KEXP 90.3."]
    d.dlg._task_manager.pending.pop()["on_success"](None, PageScanResult("W", "", [], checked=True))
    d.dlg._show_title("Late")  # after the scan: ignored
    assert d.dlg._status.GetLabel() != "Checking Late."


# -- Other ways to find a stream -----------------------------------------------------


def _directory_hit(name: str = "KEXP 90.3") -> Any:
    from quill.core.radio.find_fallback_io import FoundResult

    scan = PageScanResult("", "", [_c("http://rb.example/kexp", stream_name=name)], checked=True)
    return FoundResult(scan, "Found by the public directories (Radio Browser and IPRD).")


def test_a_typed_name_is_looked_up_not_scanned_and_says_which_way(d: Any, monkeypatch: Any) -> None:
    seen: list[tuple[str, bool]] = []

    def find(text: str, *, safe_mode: bool, fallback: bool, on_checked: Any) -> Any:
        seen.append((text, fallback))
        return _directory_hit()

    monkeypatch.setattr("quill.ui.radio.find_streams_ways.io.find", find)
    d.dlg._url_ctrl.ChangeValue("kexp")
    d.dlg._on_scan(None)
    assert d.dlg._status.GetLabel().startswith("Looking up kexp in the public directories")
    task = d.dlg._task_manager.pending.pop()
    task["on_success"](None, task["func"]())
    assert seen == [("kexp", False)]
    assert d.said[-1].endswith("Found by the public directories (Radio Browser and IPRD).")
    assert d.dlg._page_url == "" and d.dlg._page_title == "kexp"


def test_the_setting_reaches_the_scan(d: Any, monkeypatch: Any) -> None:
    seen: list[bool] = []

    def find(text: str, *, safe_mode: bool, fallback: bool, on_checked: Any) -> Any:
        seen.append(fallback)
        return _directory_hit()

    monkeypatch.setattr("quill.ui.radio.find_streams_ways.io.find", find)
    d.host._radio_history = SimpleNamespace(find_streams_fallback=True, recent_websites=())
    d.dlg._url_ctrl.ChangeValue("https://www.kexp.org/")
    d.dlg._on_scan(None)
    d.dlg._task_manager.pending.pop()["func"]()
    assert seen == [True]


@pytest.mark.parametrize("answer", [True, False])
def test_a_matching_recent_website_is_offered_and_yes_scans_it(
    d: Any, monkeypatch: Any, answer: bool
) -> None:
    asked: list[str] = []
    monkeypatch.setattr(d.dlg, "_ask_recheck", lambda site: asked.append(site) or answer)
    d.host._radio_history = SimpleNamespace(
        find_streams_fallback=False, recent_websites=("https://www.kexp.org/listen",)
    )
    ran: list[str] = []
    monkeypatch.setattr(
        "quill.ui.radio.find_streams_ways.io.find",
        lambda text, **_k: ran.append(text) or _directory_hit(),
    )
    d.dlg._url_ctrl.ChangeValue("kexp")
    d.dlg._on_scan(None)
    d.dlg._task_manager.pending.pop()["func"]()
    assert asked == ["https://www.kexp.org/listen"]
    assert ran == (["https://www.kexp.org/listen"] if answer else ["kexp"])
    assert d.dlg._url_ctrl.GetValue() == ("https://www.kexp.org/listen" if answer else "kexp")


def test_no_recent_site_means_no_question(d: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(d.dlg, "_ask_recheck", lambda site: pytest.fail("asked"))
    monkeypatch.setattr(
        "quill.ui.radio.find_streams_ways.io.find", lambda *a, **k: _directory_hit()
    )
    d.dlg._url_ctrl.ChangeValue("kexp")
    d.dlg._on_scan(None)
