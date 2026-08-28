"""F1 context help: the provider, the composition, and the central wiring.

The three facts that make "every surface answers F1" true:

1. ``SetHelpText`` stores nothing until a ``wx.HelpProvider`` exists
   (measured; this was silently true of every help text in the codebase), so
   ``ensure_help_provider`` is load-bearing, not ceremony.
2. ``topics_for`` composes the window's purpose and the focused control's
   help/name/role into two topics -- and never returns an empty answer.
3. The dialog contract's show paths bind F1 whenever an app has registered a
   handler, so a new dialog cannot ship without F1 help: the dialog gate
   already forces it through those paths.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui import dialog_contract  # noqa: E402
from quill.ui.radio import context_help  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture(autouse=True)
def _reset_handler():
    from quill.ui import app_context_help

    yield
    dialog_contract.set_context_help_handler(None)
    app_context_help._purpose_resolver = None


def test_help_provider_makes_set_help_text_live(wx_app) -> None:
    context_help.ensure_help_provider(wx)
    frame = wx.Frame(None)
    try:
        button = wx.Button(frame, label="X")
        button.SetHelpText("Does the thing.")
        assert button.GetHelpText() == "Does the thing."
    finally:
        frame.Destroy()


def test_topics_compose_surface_purpose_and_control_help(wx_app) -> None:
    context_help.activate()  # register Radio's purpose catalogue
    frame = wx.Frame(None, title="Browse Stations")
    try:
        panel = wx.Panel(frame)
        tree = wx.TreeCtrl(panel)
        tree.SetName("Station sources; expand one to browse its stations")
        tree.SetHelpText("Expand a source to load its stations on the spot.")
        frame.Show()
        tree.SetFocus()
        surface, control = context_help.topics_for(frame, wx)
        assert surface.title == "Browse Stations"
        assert "search-free tree" in surface.body
        # The heading is the name's first clause; the body keeps the teaching.
        assert control.title == "Station sources"
        assert "Expand a source to load its stations" in control.body
        assert "A tree:" in control.body, "the role line teaches the keyboard"
    finally:
        frame.Destroy()


def test_topics_never_answer_empty_for_a_bare_control(wx_app) -> None:
    context_help.ensure_help_provider(wx)
    frame = wx.Frame(None, title="Some Window Nobody Wrote Yet")
    try:
        panel = wx.Panel(frame)
        naked = wx.Button(panel, label="&Mystery")
        frame.Show()
        naked.SetFocus()
        surface, control = context_help.topics_for(frame, wx)
        assert surface.body  # the generic purpose, never ""
        assert control.title == "Mystery"
        assert "button" in control.body.lower(), "role usage still teaches the control"
    finally:
        frame.Destroy()


def _press_f1(window: object) -> None:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_F1)
    window.GetEventHandler().ProcessEvent(event)


def test_show_paths_bind_f1_when_a_handler_is_registered(wx_app) -> None:
    calls: list[object] = []
    dialog_contract.set_context_help_handler(calls.append)
    frame = wx.Frame(None, title="Player")
    try:
        dialog_contract.show_modeless_surface(frame, "Player")
        _press_f1(frame)
        assert calls == [frame], "F1 on a shown surface reaches the registered handler"
    finally:
        frame.Destroy()


def test_show_paths_leave_windows_alone_without_a_handler(wx_app) -> None:
    dialog_contract.set_context_help_handler(None)
    frame = wx.Frame(None, title="Player")
    try:
        dialog_contract.show_modeless_surface(frame, "Player")
        _press_f1(frame)  # must not raise; F1 simply falls through
        assert not getattr(frame, "_quill_f1_help_bound", False)
    finally:
        frame.Destroy()


def test_radio_startup_registers_the_handler() -> None:
    # Pinned as source: the activation must live in RadioAppFrame.__init__,
    # or a refactor could silently ship an app where no window answers F1.
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    source = (repo / "quill" / "apps" / "radio.py").read_text(encoding="utf-8")
    assert "context_help.activate()" in source
    # The Help menu's F1 row moved into apps/radio_help_docs.py with the rest of
    # that menu's documents when Tutorials arrived (GATE-11: extract, never
    # rebaseline). Both halves are pinned, so neither can drop out on its own.
    assert "radio_help_docs.install_help_items(self, help_menu, wx)" in source
    menu_source = (repo / "quill" / "apps" / "radio_help_docs.py").read_text(encoding="utf-8")
    assert 'help_menu.Append(ids["what_is_this"], "&What Is This?\\tF1")' in menu_source
    # Radio's shim hands the shared engine Radio's authored purpose catalogue.
    shim = (repo / "quill" / "ui" / "radio" / "context_help.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(surface_help.purpose_for_title)" in shim


def test_every_shell_app_inherits_f1_and_quill_installs_the_provider() -> None:
    # 2026-08-23, "get this across all app experiences so it is wired in":
    # the app shell activates the shared engine for every standalone app, and
    # QUILL's own context-help init installs the provider + generic handler.
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    shell = (repo / "quill" / "ui" / "app_shell.py").read_text(encoding="utf-8")
    assert "app_context_help.activate()" in shell
    assert "app_context_help.install(self.frame" in shell
    quill_help = (repo / "quill" / "ui" / "context_help.py").read_text(encoding="utf-8")
    assert "app_context_help.activate()" in quill_help, (
        "QUILL must install the provider and the generic dialog F1 handler"
    )
    engine = (repo / "quill" / "ui" / "app_context_help.py").read_text(encoding="utf-8")
    assert "set_context_help_handler(show_help)" in engine


def test_registered_purpose_resolver_wins_and_generic_is_the_floor(wx_app) -> None:
    from quill.core import control_help
    from quill.ui import app_context_help

    original = app_context_help._purpose_resolver
    try:
        app_context_help.activate(lambda title: f"All about {title}.")
        assert app_context_help.purpose_for_title("Player") == "All about Player."
        app_context_help._purpose_resolver = None
        assert app_context_help.purpose_for_title("Player") == control_help.GENERIC_PURPOSE
        # A resolver that raises must degrade to the generic floor, not to F1
        # dying.
        app_context_help._purpose_resolver = lambda _t: (_ for _ in ()).throw(RuntimeError())
        assert app_context_help.purpose_for_title("Player") == control_help.GENERIC_PURPOSE
    finally:
        app_context_help._purpose_resolver = original
        dialog_contract.set_context_help_handler(None)


def test_a_window_that_owns_f1_is_left_alone(wx_app) -> None:
    # QUILL's Preferences hub and Command Palette answer F1 with authored
    # topic help; the generic hook must never shadow them.
    calls: list[object] = []
    dialog_contract.set_context_help_handler(calls.append)
    frame = wx.Frame(None, title="Owns Its Own Help")
    frame._quill_owns_f1 = True
    try:
        dialog_contract.show_modeless_surface(frame, "Owns Its Own Help")
        _press_f1(frame)
        assert calls == [], "the generic hook must defer to a window's own F1"
        assert not getattr(frame, "_quill_f1_help_bound", False)
    finally:
        frame.Destroy()
