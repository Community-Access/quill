"""A Forms harness: a fake editor holding a form, and scripted dialogs.

The shared Forms commands (``quill/ui/forms_*``) run against these with no
window, modelled on the WordPress harness (``tests/unit/ui/wordpress``):

- ``forms_host`` is the editor as the commands see it: its text in a string,
  a path ending in ``.qaf``, what it announced, and where the caret went;
- ``forms_dialogs`` replaces every dialog entry point the commands call with
  a scripted answer. Unscripted questions answer **cancel**, because cancel
  is the branch people forget to write. List windows (the outline, the rules,
  Check This Form) are recorded, so a test presses their buttons afterwards;
- ``forms`` builds :class:`~quill.ui.forms_commands.FormsCommands` on both,
  with :data:`FAIR` in the editor.

Patch where the command module looks the function up (``fdlg.pick_from_list``,
``wbd.ask_fields``): that is what these fixtures do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

FAIR = """bfl 1
form "Spring fair"

text #name "Your name"
  @required
  @autocomplete "name"
email #email "Email address"
  @required
  @autocomplete "email"
radio #heard "How did you hear about us?"
  + A friend
  + Somewhere else
text #heard_other "Where?"
  @when #heard is "somewhere-else"
"""


@dataclass
class FakeHost:
    text: str = ""
    caret: int = 0
    path: Path | None = None
    parent: Any = None
    announced: list[str] = field(default_factory=list)
    opened: list[Path] = field(default_factory=list)
    replaced: int = 0

    def show_modal(self, dialog: Any, label: str) -> int:
        return 0

    def announce(self, text: str) -> None:
        self.announced.append(text)

    def current_path(self) -> Path | None:
        return self.path

    def current_text(self) -> str:
        return self.text

    def replace_text(self, text: str) -> None:
        self.text = text
        self.replaced += 1
        self.caret = min(self.caret, len(text))

    def caret_offset(self) -> int:
        return self.caret

    def go_to_offset(self, offset: int) -> None:
        self.caret = offset

    def open_path(self, path: Path) -> None:
        self.opened.append(path)
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        self.caret = 0

    @property
    def said(self) -> str:
        return "\n".join(self.announced)

    def line_at_caret(self) -> str:
        start = self.text.rfind("\n", 0, self.caret) + 1
        end = self.text.find("\n", self.caret)
        return self.text[start : end if end >= 0 else len(self.text)]


class _Closed:
    def Destroy(self) -> None:  # noqa: N802 - wx's name
        return None


class FormsScript:
    """Scripted answers for every dialog the Forms commands open."""

    CANCEL: dict[str, Any] = {
        "ask_fields": None,
        "pick_from_list": None,
        "ask_save_path": None,
        "ask_properties": None,
        "ask_text": None,
        "ask_choice": None,
        "confirm": False,
    }

    def __init__(self) -> None:
        self.answers: dict[str, list[Any]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.list_windows: list[dict[str, Any]] = []
        self.reports: list[dict[str, Any]] = []
        self.fill_sessions: list[Any] = []

    def answer(self, name: str, *values: Any) -> FormsScript:
        self.answers.setdefault(name, []).extend(values)
        return self

    def asked(self, name: str) -> list[dict[str, Any]]:
        return [kw for n, kw in self.calls if n == name]

    def entry(self, name: str) -> Any:
        def run(_parent: Any = None, _show_modal: Any = None, **kwargs: Any) -> Any:
            self.calls.append((name, kwargs))
            queue = self.answers.get(name) or []
            if not queue:
                return self.CANCEL[name]
            value = queue.pop(0)
            return value(**kwargs) if callable(value) else value

        return run

    def show_list_window(self, _parent: Any, _show_modal: Any, **kwargs: Any) -> Any:
        self.list_windows.append(kwargs)
        return _Closed()

    def show_report(self, _parent: Any, _show_modal: Any, **kwargs: Any) -> None:
        self.reports.append(kwargs)

    def show_fill_window(self, _parent: Any, _show_modal: Any, **kwargs: Any) -> None:
        self.fill_sessions.append(kwargs["session"])

    @property
    def window(self) -> dict[str, Any]:
        assert self.list_windows, "no list window was shown"
        return self.list_windows[-1]

    def press(self, label: str, index: int | None = 0) -> object:
        for action in self.window.get("actions", []):
            if action.label == label or action.label.replace("&", "") == label:
                return action.run(index)
        names = [a.label for a in self.window.get("actions", [])]
        raise AssertionError(f"no action {label!r} in {names}")

    def enter(self, index: int | None = 0) -> object:
        return self.window["on_enter"](index)


@pytest.fixture
def forms_host(tmp_path: Path) -> FakeHost:
    return FakeHost(text=FAIR, path=tmp_path / "fair.qaf")


@pytest.fixture
def forms_dialogs(monkeypatch: pytest.MonkeyPatch) -> FormsScript:
    from quill.ui import forms_dialogs as fdlg
    from quill.ui import forms_fill_window as ffw
    from quill.ui import wordpress_block_dialogs as wbd
    from quill.ui import wordpress_dialogs as dlg

    script = FormsScript()
    monkeypatch.setattr(wbd, "ask_fields", script.entry("ask_fields"))
    for name in ("pick_from_list", "ask_save_path", "ask_properties"):
        monkeypatch.setattr(fdlg, name, script.entry(name))
    for name in ("ask_text", "ask_choice", "confirm"):
        monkeypatch.setattr(dlg, name, script.entry(name))
    monkeypatch.setattr(fdlg, "show_outline_window", script.show_list_window)
    monkeypatch.setattr(dlg, "show_list_window", script.show_list_window)
    monkeypatch.setattr(dlg, "show_report", script.show_report)
    monkeypatch.setattr(ffw, "show_fill_window", script.show_fill_window)
    return script


@pytest.fixture
def forms(forms_host: FakeHost, forms_dialogs: FormsScript) -> Any:
    from quill.ui.forms_commands import FormsCommands

    return FormsCommands(forms_host)
