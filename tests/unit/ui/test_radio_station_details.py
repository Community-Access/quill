"""Station Details is reachable, labelled, helped, and reads the store. No real input.

The window is built in memory against a fake host; typing is ``SetValue``
(which raises EVT_TEXT like a keystroke would), never a real key.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import wx
from nacl import signing

from quill.core import app_keymaps
from quill.core.radio import surface_help
from quill.core.radio.enrichment import client, pack
from quill.core.radio.enrichment.facts import StationFacts
from quill.ui.radio import station_details_dialog as details


@pytest.fixture(scope="module")
def wx_app():  # noqa: ANN201 - wx types are dynamic
    app = wx.App()
    # SetHelpText stores nothing without a provider; the app installs one at
    # activation (ensure_help_provider), so the test does too.
    previous = wx.HelpProvider.Set(wx.SimpleHelpProvider())
    yield app
    wx.HelpProvider.Set(previous)
    app.Destroy()


def _store(tmp_path: Path) -> Any:
    key = signing.SigningKey.generate()
    stations = [
        StationFacts(
            key="uuid-kiro",
            name="KIRO-FM",
            stream_url="https://k.example/kiro",
            frequency="97.3 FM",
            slogan="Official home of the Seattle Seahawks",
        ),
        StationFacts(key="uuid-jazz", name="Jazz24", stream_url="https://j.example/j"),
    ]
    built = pack.build_pack(stations, [pack.SourceCredit("t", "Test")], built_at="2026-10-16")
    path, _sig, _manifest = pack.write_pack(tmp_path / "p", built, signing_key=key)
    store = client.open_store(tmp_path / "profile")
    client.install_pack_file(store, path, public_key=key.verify_key)
    return store


def test_station_details_has_a_key_no_other_radio_command_claims() -> None:
    radio = app_keymaps.APP_KEYMAPS["radio"]
    assert radio[details.COMMAND] == "Alt+Shift+I"
    assert [c for c, k in radio.items() if k.lower() == "alt+shift+i"] == [details.COMMAND]


def test_the_menu_row_shows_its_key_and_is_bound() -> None:
    radio = app_keymaps.APP_KEYMAPS["radio"]
    rows: list[str] = []
    bound: list[Any] = []
    host = SimpleNamespace(
        _menu_label=lambda title, cmd: f"{title}\t{radio[cmd]}",
        frame=SimpleNamespace(Bind=lambda *a, **k: bound.append(k.get("id"))),
    )
    menu = SimpleNamespace(
        Append=lambda _id, label: rows.append(label) or SimpleNamespace(SetHelp=lambda _t: None)
    )
    item_id = details.append_menu_item(host, menu, wx)
    assert rows == ["Station Deta&ils...\tAlt+Shift+I"]
    assert bound == [item_id]


def test_the_command_is_registered() -> None:
    registered: dict[str, Any] = {}
    commands = SimpleNamespace(
        try_register=lambda cid, title, handler, **_k: registered.setdefault(cid, (title, handler))
    )
    details.register(SimpleNamespace(commands=commands))
    assert registered[details.COMMAND][0] == "Station Details"


def test_f1_knows_what_the_window_is_for() -> None:
    assert "Station Details" in surface_help.PURPOSES


def _host(frame: Any, store: Any, said: list[str], seen: dict[str, Any], station: Any = None):
    def _show(dialog: Any, _title: str) -> int:
        seen["dialog"] = dialog
        seen["check"](dialog)
        return wx.ID_CANCEL

    return SimpleNamespace(
        _wx=wx,
        frame=frame,
        _announce=said.append,
        _show_modal_dialog=_show,
        _radio_controller=SimpleNamespace(state=SimpleNamespace(station=station)),
        _radio_enrichment=store,
    )


def _controls(dialog: Any) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for child in dialog.GetChildren():
        if isinstance(child, wx.ListBox):
            found["results"] = child
        elif isinstance(child, wx.TextCtrl):
            found["details" if child.IsMultiLine() else "query"] = child
        elif isinstance(child, wx.Button):
            found["close"] = child
    return found


def test_typing_fills_results_that_say_why_and_details_that_are_labelled(
    wx_app: Any, tmp_path: Path
) -> None:
    store = _store(tmp_path)
    frame = wx.Frame(None)
    said: list[str] = []
    checked: dict[str, Any] = {}

    def check(dialog: Any) -> None:
        controls = _controls(dialog)
        for name in ("query", "results", "details", "close"):
            assert controls[name].GetHelpText(), name  # F1 answers on every control
        assert controls["details"].HasFlag(wx.TE_READONLY)
        assert controls["close"].GetLabel() == "Close"  # no access key (GATE-14)
        controls["query"].SetValue("Seahawks")
        assert controls["results"].GetStrings() == [
            "KIRO-FM, matched slogan: Official home of the Seattle Seahawks"
        ]
        text = controls["details"].GetValue()
        assert "Name: KIRO-FM" in text and "Frequency: 97.3 FM" in text
        controls["query"].SetValue("zzzzqqqq")
        assert controls["results"].GetCount() == 0 and controls["details"].GetValue() == ""
        enter = wx.CommandEvent(wx.wxEVT_TEXT_ENTER, controls["query"].GetId())
        enter.SetEventObject(controls["query"])
        controls["query"].GetEventHandler().ProcessEvent(enter)
        assert said == ["No stations match zzzzqqqq."]
        controls["query"].SetValue("Jaz24")
        assert controls["results"].GetCount() == 0  # no fuzzy pass while typing
        controls["query"].GetEventHandler().ProcessEvent(enter)
        assert controls["results"].GetStrings() == ["Jazz24, close spelling of the name"]
        said.clear()
        checked["ok"] = True

    try:
        host = _host(frame, store, said, {"check": check})
        details.open_station_details(host)
        assert checked.get("ok")
        assert said == []  # opening and typing say nothing the reader already says
    finally:
        frame.Destroy()
        store.close()


def test_the_playing_station_opens_already_selected(wx_app: Any, tmp_path: Path) -> None:
    store = _store(tmp_path)
    frame = wx.Frame(None)
    station = SimpleNamespace(station_uuid="uuid-jazz", stream_url="", name="Jazz24")

    def check(dialog: Any) -> None:
        controls = _controls(dialog)
        assert controls["results"].GetStrings() == ["Jazz24, playing now"]
        assert controls["details"].GetValue().startswith("Name: Jazz24")

    try:
        details.open_station_details(_host(frame, store, [], {"check": check}, station))
    finally:
        frame.Destroy()
        store.close()


def test_first_open_installs_and_says_the_outcome_once(
    wx_app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    monkeypatch.setattr(details, "_prepare_store", lambda _host: (store, "Installed: 2 new."))
    frame = wx.Frame(None)
    said: list[str] = []
    host = _host(frame, None, said, {"check": lambda _d: None})
    host._radio_enrichment = None
    try:
        details.open_station_details(host)
        assert said == ["Installed: 2 new."]
        assert host._radio_enrichment is store
    finally:
        frame.Destroy()
        store.close()
