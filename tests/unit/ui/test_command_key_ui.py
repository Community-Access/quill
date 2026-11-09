"""The Command Key's windows and each app's host (docs/design/command-key.md 10, 11, 16.4)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.command_catalogue import row
from quill.core.command_catalogue.resolver import Candidate
from quill.ui import command_key_hosts as hosts
from quill.ui import command_key_ui as ui


class _Registry:
    def __init__(self, ids: set[str], keys: dict[str, str] | None = None) -> None:
        self.ids = ids
        self.keys = keys or {}
        self.ran: list[str] = []
        self.reasons: dict[str, str] = {}

    def get(self, command_id: str) -> object | None:
        return object() if command_id in self.ids else None

    def unavailable_reason(self, command_id: str) -> str:
        return self.reasons.get(command_id, "")

    def run(self, command_id: str) -> None:
        self.ran.append(command_id)

    def arm_repeat(self, count: int) -> None:
        pass

    def keybinding_for(self, command_id: str) -> str | None:
        return self.keys.get(command_id)


def _host(app: str = "radio", **kwargs: Any) -> tuple[ui.WxCommandKeyHost, _Registry, list[str]]:
    from quill.core.command_catalogue import rows_for_app

    registry = _Registry(
        {spec.id for spec in rows_for_app(app)}, {"radio.volume_down": "Ctrl+Down"}
    )
    spoken: list[str] = []
    host = ui.WxCommandKeyHost(
        wx=object(),
        parent=None,
        app=app,
        registry=registry,
        show_modal=lambda _dialog, _label: 0,
        announce=spoken.append,
        key_for=hosts._keys(registry),
        **kwargs,
    )
    return host, registry, spoken


# -- the host ------------------------------------------------------------------


def test_candidates_are_registered_available_and_never_never() -> None:
    host, registry, _spoken = _host()
    registry.ids.discard("radio.mute_toggle")
    registry.reasons["radio.stop"] = "Nothing is playing."
    ids = {item.spec.id for item in host.candidates()}
    assert "radio.volume_down" in ids
    assert "radio.mute_toggle" not in ids and "radio.stop" not in ids
    assert "radio.update_catalog" not in ids  # NEVER
    key = next(item.key for item in host.candidates() if item.spec.id == "radio.volume_down")
    assert key == "Ctrl+Down"
    elsewhere = host.elsewhere()
    assert [item.spec.id for item in elsewhere.unavailable] == ["radio.stop"]
    assert any(spec.id == "radio.update_catalog" for spec in elsewhere.never)


def test_a_dimmed_menu_row_is_a_command_switched_off_here() -> None:
    class _Item:
        def __init__(self, enabled: bool) -> None:
            self.enabled = enabled

        def IsEnabled(self) -> bool:  # noqa: N802 - wx's name
            return self.enabled

    spec = row("format.bold")
    assert spec is not None
    assert hosts._dimmed(_Item(False), spec) == "Bold isn't available here right now."
    assert hosts._dimmed(_Item(True), spec) == ""
    assert hosts._dimmed(None, spec) == ""

    host, _registry, _spoken = _host(
        "quill", probe=lambda s: "Bold needs a rich document." if s.id == "format.bold" else ""
    )
    assert "format.bold" not in {item.spec.id for item in host.candidates()}
    assert host.elsewhere().unavailable[0].reason == "Bold needs a rich document."


def test_a_probe_that_fails_does_not_hide_the_command() -> None:
    def broken(_spec: object) -> str:
        raise RuntimeError("probe bug")

    host, _registry, _spoken = _host(probe=broken)
    assert any(item.spec.id == "radio.volume_down" for item in host.candidates())


def test_keys_survive_a_registry_that_cannot_say() -> None:
    class _Broken:
        def keybinding_for(self, _command_id: str) -> str:
            raise RuntimeError("no keymap")

    assert hosts._keys(_Broken())("radio.stop") == ""


# -- the F11 loop -------------------------------------------------------------------


def test_f11_runs_what_was_typed_and_keeps_the_session(monkeypatch: pytest.MonkeyPatch) -> None:
    host, registry, spoken = _host()
    typed = iter(["turn it down a bit", "undo that"])
    monkeypatch.setattr(ui, "ask_for_command", lambda *_args: next(typed))
    session = ui.run_command_key(host)
    session = ui.run_command_key(host, session)
    assert registry.ran == ["radio.volume_down", "radio.volume_up"]
    assert spoken == []  # both say their own new level


def test_escape_from_the_box_does_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    host, registry, spoken = _host()
    monkeypatch.setattr(ui, "ask_for_command", lambda *_args: None)
    ui.run_command_key(host)
    assert registry.ran == [] and spoken == []


def test_the_first_time_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    host, _registry, spoken = _host()
    monkeypatch.setattr(ui, "ask_for_command", lambda *_args: None)
    ui.run_command_key(host, first_time=True)
    assert spoken == [ui.FIRST_HINT]
    assert len(ui.FIRST_HINT.split()) <= 12


def test_the_hint_is_said_once_ever(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    assert hosts.hint_shown() is False
    assert hosts.hint_shown() is True


def test_something_else_reopens_the_box_with_the_words(monkeypatch: pytest.MonkeyPatch) -> None:
    host, registry, _spoken = _host("quill")
    seen: list[str] = []
    answers = iter(["headings", "next heading"])

    def ask(_wx: Any, _parent: Any, _show: Any, initial: str = "") -> str:
        seen.append(initial)
        return next(answers)

    monkeypatch.setattr(ui, "ask_for_command", ask)
    monkeypatch.setattr(ui, "choose_command", lambda *_args: "else")
    ui.run_command_key(host)
    assert seen == ["", "headings"]
    assert registry.ran == ["navigate.next_heading"]


def test_did_you_mean_pick_and_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    host, _registry, _spoken = _host("quill")
    spec = row("navigate.next_heading")
    assert spec is not None
    choice = Candidate(spec)
    monkeypatch.setattr(ui, "choose_command", lambda *_args: choice)
    assert host.choose([choice]) is choice
    monkeypatch.setattr(ui, "choose_command", lambda *_args: None)
    assert host.choose([choice]) is None and host.retype is False


def test_a_confirm_command_goes_through_the_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    host, registry, _spoken = _host()
    asked: list[str] = []
    monkeypatch.setattr(ui, "ask_for_command", lambda *_args: "stop every recording")
    monkeypatch.setattr(
        ui, "confirm_command", lambda _wx, _p, _s, question: asked.append(question) or False
    )
    ui.run_command_key(host)
    assert asked and registry.ran == []


# -- What Can I Say Here --------------------------------------------------------


def test_help_says_the_count_once_and_runs_the_pick(monkeypatch: pytest.MonkeyPatch) -> None:
    host, registry, spoken = _host()
    shown: list[Any] = []

    def show(_wx: Any, _parent: Any, _show: Any, rows: Any, *_extra: Any) -> Candidate | None:
        shown.append(rows)
        return next(r.candidate for r in rows if r.candidate is not None)

    monkeypatch.setattr(ui, "show_command_help", show)
    picked = host.show_help("")
    assert picked is not None
    assert len(spoken) == 1 and spoken[0].startswith("30 things you can do here, in ")


def test_help_with_a_filter_that_finds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    host, _registry, spoken = _host()
    monkeypatch.setattr(ui, "show_command_help", lambda *_args: None)
    host.show_help("zebras")
    assert spoken[0] == "Nothing about zebras here. Here is everything."


def test_help_with_nothing_to_do() -> None:
    host, registry, spoken = _host()
    registry.ids.clear()
    assert host.show_help("") is None
    assert spoken == ["Nothing can be done here right now."]


def test_dictation_help_and_arguments_without_an_app_hook() -> None:
    host, _registry, spoken = _host()
    host.show_dictation_help()
    assert spoken == ["Dictation's phrases are in Dictation Settings, Commands."]
    spec = row("radio.play_favorite", "radio")
    assert spec is not None
    assert host.run_with_args(spec, {"number": 3}) is False
    called: list[int] = []
    hooked, _r, _s = _host(dictation_help=lambda: called.append(1), args_runner=lambda _s, _a: True)
    hooked.show_dictation_help()
    assert called == [1] and hooked.run_with_args(spec, {"number": 3}) is True


def test_what_can_i_say_here_runs_through_the_session(monkeypatch: pytest.MonkeyPatch) -> None:
    host, registry, _spoken = _host()
    spec = row("radio.mute_toggle", "radio")
    assert spec is not None
    monkeypatch.setattr(host, "show_help", lambda _filter: Candidate(spec))

    class _Owner:
        _command_key_session = None

    owner = _Owner()
    monkeypatch.setattr(hosts, "_radio_host", lambda _frame: host)
    hosts.radio_what_can_i_say_here(owner)
    assert registry.ran == ["radio.mute_toggle"]
    assert owner._command_key_session is not None


# -- the real windows ----------------------------------------------------------------


@pytest.mark.usefixtures("wx_session_app")
def test_the_box_and_lists_are_real_dialogs_with_help_and_no_access_keys() -> None:
    import wx

    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # SetHelpText stores nothing without one
    seen: dict[str, Any] = {}

    def show(dialog: Any, label: str) -> int:
        seen[label] = dialog
        buttons = [c for c in dialog.GetChildren() if isinstance(c, wx.Button)]
        assert buttons and all("&" not in b.GetLabel() for b in buttons)
        for child in dialog.GetChildren():
            if isinstance(child, wx.TextCtrl):
                assert child.GetHelpText()
                child.SetValue("louder")
            if isinstance(child, wx.ListBox):
                assert child.GetHelpText()
                child.SetSelection(1)
        return wx.ID_OK

    assert ui.ask_for_command(wx, None, show) == "louder"
    spec = row("radio.volume_up", "radio")
    other = row("radio.volume_down", "radio")
    assert spec is not None and other is not None
    picked = ui.choose_command(wx, None, show, [Candidate(spec), Candidate(other)])
    assert (
        picked is not None and not isinstance(picked, str) and picked.spec.id == "radio.volume_down"
    )
    rows = ui.help_rows([Candidate(spec)])
    assert ui.show_command_help(wx, None, show, rows) is not None
    assert ui.confirm_command(wx, None, show, "Stop Every Recording?") is True
    assert set(seen) == {ui.BOX_TITLE, ui.CHOOSE_TITLE, ui.HELP_TITLE, ui.CONFIRM_TITLE}


@pytest.mark.usefixtures("wx_session_app")
def test_escape_answers_none_from_each_window() -> None:
    import wx

    def escape(_dialog: Any, _label: str) -> int:
        return wx.ID_CANCEL

    assert ui.ask_for_command(wx, None, escape) is None
    spec = row("radio.stop", "radio")
    assert spec is not None
    assert ui.choose_command(wx, None, escape, [Candidate(spec)]) is None
    assert ui.show_command_help(wx, None, escape, ui.help_rows([Candidate(spec)])) is None
    assert ui.confirm_command(wx, None, escape, "Stop?") is False


@pytest.mark.usefixtures("wx_session_app")
def test_something_else_is_the_last_row() -> None:
    import wx

    def pick_last(dialog: Any, _label: str) -> int:
        listing = next(c for c in dialog.GetChildren() if isinstance(c, wx.ListBox))
        listing.SetSelection(listing.GetCount() - 1)
        assert listing.GetString(listing.GetCount() - 1) == ui.SOMETHING_ELSE
        return wx.ID_OK

    spec = row("radio.stop", "radio")
    assert spec is not None
    assert ui.choose_command(wx, None, pick_last, [Candidate(spec)]) == "else"


# -- tier 3's consent (command-key.md 7.8) ---------------------------------------------


def test_no_key_means_no_jev_and_no_question(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.command_catalogue import jev

    monkeypatch.setattr(jev, "_key_from_credential_manager", lambda: "")
    monkeypatch.setattr(hosts, "_gateway_token", lambda: "")
    asked: list[int] = []
    monkeypatch.setattr(ui, "ask_command_understanding", lambda *_a, **_k: asked.append(1) or "jev")
    host, _registry, _spoken = _host()
    assert hosts._assist_for(host) is None and asked == []


def test_signed_in_to_free_ai_offers_jev_through_the_gateway(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.paths as paths
    from quill.core.command_catalogue import jev

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(jev, "_key_from_credential_manager", lambda: "")
    monkeypatch.setattr(hosts, "_gateway_token", lambda: "device-token")
    monkeypatch.setattr(hosts, "_JEV_ROUTE", None)
    monkeypatch.setattr(ui, "ask_command_understanding", lambda *_a, **_k: "jev")
    host, _registry, _spoken = _host()
    assert hosts._assist_for(host) is not None
    assert isinstance(hosts._JEV_ROUTE, jev.GatewayJev)


def test_safe_mode_means_no_jev(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.command_catalogue import jev

    monkeypatch.setattr(jev, "_key_from_credential_manager", lambda: "sk-test")
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    host, _registry, _spoken = _host()
    assert hosts._assist_for(host) is None


@pytest.mark.parametrize(
    ("answer", "assisted"), [("jev", True), ("my_ai", False), ("local", False)]
)
def test_the_consent_question_is_asked_once_and_remembered(
    answer: str, assisted: bool, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.paths as paths
    from quill.core.command_catalogue import jev

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(jev, "_key_from_credential_manager", lambda: "sk-test")
    asked: list[int] = []
    monkeypatch.setattr(
        ui, "ask_command_understanding", lambda *_a, **_k: asked.append(1) or answer
    )
    host, _registry, _spoken = _host()
    first = hosts._assist_for(host)
    second = hosts._assist_for(host)
    assert asked == [1]
    assert hosts.command_understanding() == answer
    assert (first is not None, second is not None) == (assisted, assisted)


def test_the_consent_says_typesafe_keeps_requests_and_does_not_train() -> None:
    assert "keep the requests they receive" in ui.CONSENT_TEXT
    assert "do not train on them" in ui.CONSENT_TEXT
    assert "no document text, file names" in ui.CONSENT_TEXT
    assert [value for _label, value in ui.CONSENT_CHOICES] == ["jev", "my_ai", "local"]


@pytest.mark.usefixtures("wx_session_app")
def test_the_consent_window_answers_and_escape_means_local() -> None:
    import wx

    def escape(_dialog: Any, _label: str) -> int:
        return wx.ID_CANCEL

    assert ui.ask_command_understanding(wx, None, escape) == "local"

    def press_second(dialog: Any, _label: str) -> int:
        buttons = [c for c in dialog.GetChildren() if isinstance(c, wx.Button) and c.IsShown()]
        assert [b.GetLabel() for b in buttons] == [label for label, _v in ui.CONSENT_CHOICES]
        event = wx.CommandEvent(wx.wxEVT_BUTTON, buttons[1].GetId())
        event.SetEventObject(buttons[1])
        dialog.IsModal = lambda: True  # type: ignore[method-assign]
        dialog.EndModal = lambda _code: None  # type: ignore[method-assign]
        buttons[1].ProcessEvent(event)
        return wx.ID_OK

    assert ui.ask_command_understanding(wx, None, press_second) == "my_ai"
