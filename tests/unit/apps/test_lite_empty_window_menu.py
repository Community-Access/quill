"""QUILL Lite with every document closed: a full menu bar, not File alone.

The empty bar borrows the document window's handlers (``ShellMenuMixin``), which
is only safe for a handler that asks its window for nothing the shell lacks. The
first test is the guarantee: it reads each borrowed handler's source, and every
helper it calls on ``self``, and fails on any attribute the shell does not have.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

from quill.apps import lite_shell_menu  # noqa: E402
from quill.apps.lite_shell_menu import NO_DOCUMENT_COMMANDS, ShellMenuMixin  # noqa: E402
from quill.core.lite.commands import COMMANDS  # noqa: E402

_APPS = pathlib.Path(__file__).resolve().parents[3] / "quill" / "apps"


def _methods() -> dict[str, ast.FunctionDef]:
    """Every method defined on a class in QUILL Lite's window modules, by name."""
    found: dict[str, ast.FunctionDef] = {}
    for path in sorted(_APPS.glob("lite*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            for item in cls.body:
                if isinstance(item, ast.FunctionDef):
                    found.setdefault(item.name, item)
    return found


def _self_attributes(fn: ast.FunctionDef) -> set[str]:
    return {
        node.attr
        for node in ast.walk(fn)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    }


def _shell_provides() -> set[str]:
    return {name for name in vars(ShellMenuMixin) if not name.startswith("__")} | {"app"}


def test_every_borrowed_handler_reads_only_what_the_shell_has() -> None:
    methods = _methods()
    provided = _shell_provides()

    def reach(name: str, seen: set[str]) -> set[str]:
        if name in seen or name not in methods:
            return set()
        seen.add(name)
        out: set[str] = set()
        for attribute in _self_attributes(methods[name]):
            if attribute in provided:
                continue
            out.add(attribute)
            out |= reach(attribute, seen)
        return out

    problems = {}
    for handler in NO_DOCUMENT_COMMANDS:
        if handler in lite_shell_menu._SHELL_OWN:
            continue
        assert handler in methods, f"{handler}: no such handler"
        missing = reach(handler, set()) - {handler}
        if missing:
            problems[handler] = sorted(missing)
    assert problems == {}, f"handlers that need a document window: {problems}"


def test_every_empty_window_command_is_a_row_in_the_table() -> None:
    handlers = {row[3] for row in COMMANDS}
    assert [h for h in NO_DOCUMENT_COMMANDS if h not in handlers] == []


class _Voice:
    def __init__(self) -> None:
        self.said: list[str] = []

    def speak(self, message: str, *, interrupt: bool = True) -> None:
        self.said.append(message)


class _ShellFrame(ShellMenuMixin, wx.Frame):
    def __init__(self, app: object) -> None:
        wx.Frame.__init__(self, None)
        self.app = app
        self._build_placeholder_menu()


def _app(**overrides: object) -> SimpleNamespace:
    app = SimpleNamespace(
        feature_enabled=lambda _area: True,
        keymap={},
        voice=_Voice(),
    )
    for name, value in overrides.items():
        setattr(app, name, value)
    return app


@pytest.fixture
def shell(wx_session_app):
    frame = _ShellFrame(_app())
    yield frame
    frame.Destroy()


def _bar(frame: wx.Frame) -> dict[str, list[str]]:
    bar = frame.GetMenuBar()
    return {
        bar.GetMenuLabel(index): [
            item.GetItemLabel()
            for item in bar.GetMenu(index).GetMenuItems()
            if not item.IsSeparator()
        ]
        for index in range(bar.GetMenuCount())
    }


def test_the_empty_bar_has_file_tools_and_help(shell) -> None:
    bar = _bar(shell)
    assert list(bar) == ["&File", "&Tools", "&Help"]
    help_rows = " ".join(bar["&Help"])
    for wanted in ("What's New", "About QUILL Lite", "Check for &Updates", "Keyboard Shortcuts"):
        assert wanted in help_rows
    assert any("Recent &Documents" in row for row in bar["&File"])
    assert any("&Preferences" in row for row in bar["&Tools"])


def test_every_keyed_row_shows_its_key_and_no_key_is_claimed_twice(shell) -> None:
    keys = []
    for rows in _bar(shell).values():
        for row in rows:
            if "\t" in row:
                keys.append(row.split("\t", 1)[1].lower())
    assert keys and len(keys) == len(set(keys))


def test_a_switched_off_area_stays_off_in_the_empty_bar(wx_session_app) -> None:
    from quill.core.lite.command_areas import visible_commands

    everything = {row[3] for row in visible_commands(lambda _a: True)}
    nothing = {row[3] for row in visible_commands(lambda _a: False)}
    hidden = [h for h in NO_DOCUMENT_COMMANDS if h in everything and h not in nothing]
    frame = _ShellFrame(_app(feature_enabled=lambda _area: False))
    try:
        labels = " ".join(" ".join(rows) for rows in _bar(frame).values())
    finally:
        frame.Destroy()
    rows = {row[3]: row[1] for row in COMMANDS if row[3]}
    for handler in hidden:
        assert rows[handler] not in labels, handler


def test_open_from_the_empty_window_opens_each_chosen_file_through_the_funnel(
    shell, monkeypatch
) -> None:
    """The shell's own Open: the chosen files go to ``app.open_path``, where the
    large-file guard sits, and a cancelled dialog opens nothing."""
    opened: list[object] = []
    shell.app.open_path = opened.append

    class _Dialog:
        def __init__(self, *_a, **_kw) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> None:
            return None

        def GetPaths(self):  # noqa: N802 - wx spelling
            return ["C:/one.txt", "C:/two.md"]

    answers = iter([wx.ID_OK, wx.ID_CANCEL])
    monkeypatch.setattr(lite_shell_menu.wx, "FileDialog", _Dialog)
    monkeypatch.setattr(shell, "_show_lite_modal", lambda _d, _label: next(answers))
    shell.run_shell_command("cmd_open")
    assert [p.name for p in opened] == ["one.txt", "two.md"]
    shell.run_shell_command("cmd_open")
    assert len(opened) == 2


def test_whats_new_from_the_empty_window_opens_the_changelog(shell, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake(app: str, name: str, announce, **_kw) -> bool:
        calls.append((app, name))
        announce("opened")
        return True

    monkeypatch.setattr("quill.ui.whats_new.open_whats_new", fake)
    shell.run_shell_command("cmd_whats_new")
    assert calls == [("quilllite", "QUILL Lite")]
    assert shell.app.voice.said == ["opened"]


def test_whats_new_from_a_document_opens_quill_lites_changelog(lite_window, monkeypatch) -> None:
    win = lite_window("text")
    calls: list[tuple[str, str]] = []

    def fake(app: str, name: str, announce, **_kw) -> bool:
        calls.append((app, name))
        announce("Opened What's New in QUILL Lite in your browser")
        return True

    monkeypatch.setattr("quill.ui.whats_new.open_whats_new", fake)
    win.cmd_whats_new()
    assert calls == [("quilllite", "QUILL Lite")]
    assert win.app.voice.said[-1] == "Opened What's New in QUILL Lite in your browser"


def test_the_shell_stands_in_for_the_window_where_handlers_look(shell) -> None:
    assert shell.control is shell
    assert shell.path is None and shell.modified is False
    assert inspect.ismethod(shell._announce)
