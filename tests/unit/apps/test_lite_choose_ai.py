"""Which AI Am I Using, Choose Your AI, the AI status cell and the gate (codex.md 10A).

Every handler is **called** in a lambda: ``quill.tools.lite_command_coverage``
finds coverage by walking the AST for real calls (``test_lite_ai.py`` says why).
The window is patched where the shared mixin looks it up,
``quill.ui.hosted_ai_connections``.
"""

from __future__ import annotations

import pytest


class _Window:
    """Records how Choose Your AI was built, and pretends to be a window."""

    last: dict | None = None

    def __init__(self, *args, **kwargs):
        type(self).last = {"args": args, "kwargs": kwargs}
        self.selected = ""
        self.signing_in = ""

    def Show(self):  # noqa: N802 - wx API shape
        pass

    def Raise(self):  # noqa: N802 - wx API shape
        pass

    def SetFocus(self):  # noqa: N802 - wx API shape
        pass

    def Bind(self, *_args, **_kwargs):  # noqa: N802 - wx API shape
        pass

    def select(self, connection):
        self.selected = connection

    def start_sign_in(self, connection):
        self.signing_in = connection


@pytest.fixture
def choose_window(monkeypatch):
    import quill.ui.hosted_ai_connections as connections

    cls = type("ChooseAiFrame", (_Window,), {"last": None})
    monkeypatch.setattr(connections, "ChooseAiFrame", cls)
    return cls


class _Service:
    """The free AI in use, connected; what Ctrl+8 and the cell read."""

    signed_in = True
    own_key_active = False
    direct = False

    def __init__(self):
        self.connection_in_use = "free"
        self.cells = 0

    def which_ai(self, free_quota=None):
        return "QUILL's free AI, QUILL chooses the model. 3 of 50 requests today."

    def status_cell(self):
        self.cells += 1
        return "AI: free"

    def can_do(self, capability):
        return capability != "pictures"

    def needs_label(self, capability):
        return "" if self.can_do(capability) else "(needs a connection that sees)"


@pytest.fixture
def service(monkeypatch):
    from quill.ui.hosted_ai_commands import HostedAiMixin

    monkeypatch.setattr(HostedAiMixin, "_ai_privacy_accepted", lambda _self: True)
    return _Service()


def _clock(monkeypatch, times):
    import quill.ui.hosted_ai_choose_commands as module

    ticks = iter(times)
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))


# --------------------------------------------------------------------------- #
# Which AI Am I Using (Ctrl+8)
# --------------------------------------------------------------------------- #


def test_which_ai_speaks_the_connection_the_model_and_one_usage_clause(
    lite_window, choose_window, service, monkeypatch
):
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_which())(win)

    assert win.announcements == [service.which_ai()]
    assert choose_window.last is None


def test_which_ai_pressed_twice_opens_choose_your_ai(
    lite_window, choose_window, service, monkeypatch
):
    """Within the half second QUILL's Spoken Echo double press uses (10A.9)."""
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: service)
    _clock(monkeypatch, [10.0, 10.3, 10.5])

    (lambda w: w.cmd_ai_which())(win)
    (lambda w: w.cmd_ai_which())(win)

    assert choose_window.last is not None
    assert win.announcements == [service.which_ai()], "the second press opens, it does not speak"

    (lambda w: w.cmd_ai_which())(win)  # a third press speaks again
    assert len(win.announcements) == 2


def test_two_slow_presses_speak_twice(lite_window, choose_window, service, monkeypatch):
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: service)
    _clock(monkeypatch, [10.0, 10.9])

    (lambda w: w.cmd_ai_which())(win)
    (lambda w: w.cmd_ai_which())(win)

    assert choose_window.last is None
    assert len(win.announcements) == 2


def test_which_ai_refuses_when_the_area_is_off(lite_window, choose_window, monkeypatch):
    win = lite_window("text")
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "hosted_ai")

    (lambda w: w.cmd_ai_which())(win)

    assert any("switched off" in said for said in win.announcements)


# --------------------------------------------------------------------------- #
# Choose Your AI (Ctrl+4)
# --------------------------------------------------------------------------- #


def test_choose_your_ai_opens_the_window_on_the_service_and_once(
    lite_window, choose_window, service, monkeypatch
):
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_choose())(win)
    first = choose_window.last
    (lambda w: w.cmd_ai_choose())(win)

    assert first["args"][1] is service
    assert first["args"][2].app_name  # the app's own agent name, for the sign-in step
    assert choose_window.last is first, "a second press raises the open window"
    assert win.announcements == [], "the reader announces the window (GATE-13)"


def test_choose_your_ai_refuses_when_the_area_is_off(lite_window, choose_window, monkeypatch):
    win = lite_window("text")
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "hosted_ai")

    (lambda w: w.cmd_ai_choose())(win)

    assert choose_window.last is None


def test_with_no_ai_in_use_an_ai_command_opens_the_window_and_says_so(
    lite_window, choose_window, service, monkeypatch
):
    """Decision 15: never a silent fall-back to the free AI or a key."""
    service.connection_in_use = ""
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_assistant())(win)

    assert choose_window.last is not None
    assert win.announcements == ["No AI is in use. Choose one."]


# --------------------------------------------------------------------------- #
# The AI status cell (decision 19) and the gated labels (10A.8)
# --------------------------------------------------------------------------- #


def test_the_ai_cell_is_last_before_the_message_and_enter_opens_the_window() -> None:
    from quill.apps.lite_status_cells import _CELL_ACTIONS, CELLS

    keys = [cell.key for cell in CELLS]
    assert keys[-2:] == ["ai", "message"]
    assert _CELL_ACTIONS["ai"] == "cmd_ai_choose"
    assert next(c for c in CELLS if c.key == "ai").help_text


def test_the_ai_cell_reads_the_service_once_until_the_connection_changes(
    lite_window, service, monkeypatch
):
    from quill.apps.lite_status_cells import ai_cell

    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    assert ai_cell(win) == "AI: free"
    assert ai_cell(win) == "AI: free"
    assert service.cells == 1, "the bar refreshes on every pause; the cell is cached"

    touches, menus = win.status_touches, win.app.rebuilt_menus
    win._ai_connection_refresh()
    assert win.status_touches == touches + 1
    assert win.app.rebuilt_menus == menus + 1
    assert ai_cell(win) == "AI: free"
    assert service.cells == 2


def test_a_command_the_connection_cannot_do_says_what_it_needs_in_its_label(
    lite_window, service, monkeypatch
):
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    assert win._ai_gated_label("cmd_ai_image", "Ask About an &Image...") == (
        "Ask About an &Image (needs a connection that sees)..."
    )
    assert win._ai_gated_label("cmd_ai_assistant", "AI &Assistant...") == "AI &Assistant..."
    assert win._ai_gated_label("cmd_save", "&Save") == "&Save"


def test_quills_status_bar_has_the_same_cell() -> None:
    from quill.core.settings_normalizers import STATUS_BAR_ITEMS
    from quill.ui.main_frame_ai_status import AiStatusCellMixin
    from quill.ui.statusbar_cell_help import STATUS_BAR_CELL_HELP

    assert STATUS_BAR_ITEMS[-2:] == ("ai", "message")
    assert STATUS_BAR_CELL_HELP["ai"]

    class Base:
        def _statusbar_text_for_item(self, item):
            return f"base {item}"

        def _activate_statusbar_cell(self, item):
            self.activated = item

    class Frame(AiStatusCellMixin, Base):
        opened = 0

        def ai_status_text(self):
            return "AI: ChatGPT plan"

        def cmd_ai_choose(self):
            self.opened += 1

    frame = Frame()
    assert frame._statusbar_text_for_item("ai") == "AI: ChatGPT plan"
    assert frame._statusbar_text_for_item("page") == "base page"
    frame._activate_statusbar_cell("ai")
    assert frame.opened == 1
    frame._activate_statusbar_cell("page")
    assert frame.activated == "page"
