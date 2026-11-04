"""A WordPress harness: a fake editor, a fake site, and scripted dialogs.

Every shared WordPress command (``quill/ui/wordpress_*``) runs against these
with no network, no Credential Manager and no real window:

- ``wp_host`` is a :class:`~quill.ui.wordpress_host.WordPressHost` that keeps
  its text in a string, records what it announced, runs background work
  synchronously, and keeps a fake clipboard and browser;
- ``wp_site`` answers REST routes by ``(method, path)`` and records every
  request, so a test asserts what was sent as well as what was said;
- ``wp_dialogs`` replaces each dialog entry point in ``wordpress_dialogs`` and
  ``wordpress_item_dialogs`` with a scripted answer. Unscripted questions
  answer **cancel**, because cancel is the branch people forget to write;
- ``wp`` builds :class:`~quill.ui.wordpress_commands.WordPressCommands` on all
  three, with one connected site.

Patch where the command module looks the function up: these fixtures patch
the dialog modules' attributes, which is where every command calls them
(``dlg.ask_choice``), so a command that imports a name directly is invisible
to them and should not.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest


class FakeResponse:
    def __init__(self, payload: Any, status: int = 200, headers: dict[str, str] | None = None):
        self._raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.status = status
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


class FakeSite:
    """An opener that answers by (method, path) and records every request.

    *answer* may be a JSON-able value, a :class:`FakeResponse`, an exception to
    raise, or a callable ``(request, query) -> any of those``. Paths are the
    URL path, so a self-hosted route is ``/wp-json/wp/v2/posts``.
    """

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Any] = {}
        self.requests: list[Any] = []

    def on(self, method: str, path: str, answer: Any) -> FakeSite:
        self.routes[(method, path)] = answer
        return self

    def sent(self, method: str, path: str) -> list[Any]:
        """The requests made to one route, oldest first."""
        return [
            r
            for r in self.requests
            if r.get_method() == method and urlparse(r.full_url).path == path
        ]

    def body(self, request: Any) -> Any:
        data = request.data or b""
        try:
            return json.loads(data)
        except ValueError:
            return data

    def __call__(self, request: Any, timeout: Any = None, context: Any = None) -> Any:
        self.requests.append(request)
        parsed = urlparse(request.full_url)
        answer = self.routes.get((request.get_method(), parsed.path))
        if answer is None:
            raise HTTPError(
                request.full_url, 404, "nf", {}, io.BytesIO(b'{"code":"rest_no_route"}')
            )
        if callable(answer):
            answer = answer(request, parse_qs(parsed.query))
        if isinstance(answer, BaseException):
            raise answer
        if isinstance(answer, FakeResponse):
            return answer
        return FakeResponse(answer)


@dataclass
class FakeHost:
    """The editor, as the WordPress commands see it, with nothing real behind it."""

    text: str = ""
    caret: int = 0
    selection: tuple[int, int] = (0, 0)
    path: Path | None = None
    clipboard: str = ""
    parent: Any = None
    announced: list[str] = field(default_factory=list)
    opened: list[Path] = field(default_factory=list)
    browsed: list[str] = field(default_factory=list)
    modal_labels: list[str] = field(default_factory=list)
    saves: int = 0
    tasks: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    # -- the protocol ------------------------------------------------------ #

    def show_modal(self, dialog: Any, label: str) -> int:
        self.modal_labels.append(label)
        return 0

    def announce(self, text: str) -> None:
        self.announced.append(text)

    def run_task(self, name: str, func: Any, on_success: Any, on_failure: Any) -> None:
        self.tasks.append(name)
        try:
            result = func()
        except BaseException as exc:  # noqa: BLE001 - the host hands every failure back
            on_failure(exc)
            return
        on_success(result)

    def current_path(self) -> Path | None:
        return self.path

    def current_text(self) -> str:
        return self.text

    def replace_text(self, text: str) -> None:
        self.text = text
        self.caret = min(self.caret, len(text))
        self.selection = (self.caret, self.caret)

    def insert_text(self, text: str) -> None:
        start, end = self.selection if self.selection[0] != self.selection[1] else (self.caret,) * 2
        self.text = self.text[:start] + text + self.text[end:]
        self.caret = start + len(text)
        self.selection = (self.caret, self.caret)

    def selected_text(self) -> str:
        start, end = self.selection
        return self.text[start:end]

    def caret_offset(self) -> int:
        return self.caret

    def go_to_offset(self, offset: int) -> None:
        self.caret = offset
        self.selection = (offset, offset)

    def open_path(self, path: Path) -> None:
        self.opened.append(path)
        self.path = path
        self.text = path.read_text(encoding="utf-8") if path.exists() else ""
        self.caret = 0
        self.selection = (0, 0)

    def save_current(self) -> bool:
        self.saves += 1
        if self.path is not None:
            self.path.write_text(self.text, encoding="utf-8", newline="")
        return True

    def clipboard_text(self) -> str:
        return self.clipboard

    def set_clipboard_text(self, text: str) -> None:
        self.clipboard = text

    def open_in_browser(self, url: str) -> None:
        self.browsed.append(url)

    # -- helpers for tests --------------------------------------------------- #

    @property
    def said(self) -> str:
        """Everything announced, one line each, for ``in`` checks."""
        return "\n".join(self.announced)


class DialogScript:
    """Scripted answers for every WordPress dialog entry point.

    ``answers[name]`` is a list consumed in order; each item is the value the
    entry point returns, or a callable ``(**kwargs) -> value``. With no answer
    left, the entry point returns its cancel value (``None`` or ``False``).
    ``list_windows`` records every list window's keyword arguments, so a test
    can press one of its actions: ``script.press("&Restore", index)``.
    """

    CANCEL: dict[str, Any] = {
        "ask_connect": None,
        "ask_paste_password": None,
        "ask_choice": None,
        "ask_text": None,
        "confirm": False,
        "ask_new_item": None,
        "ask_properties": None,
        "ask_image": None,
    }

    def __init__(self) -> None:
        self.answers: dict[str, list[Any]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.list_windows: list[dict[str, Any]] = []
        self.reports: list[dict[str, Any]] = []

    def answer(self, name: str, *values: Any) -> DialogScript:
        self.answers.setdefault(name, []).extend(values)
        return self

    def asked(self, name: str) -> list[dict[str, Any]]:
        return [kw for n, kw in self.calls if n == name]

    def _entry(self, name: str) -> Any:
        def entry(_parent: Any = None, _show_modal: Any = None, **kwargs: Any) -> Any:
            self.calls.append((name, kwargs))
            queue = self.answers.get(name) or []
            if not queue:
                return self.CANCEL.get(name)
            value = queue.pop(0)
            return value(**kwargs) if callable(value) else value

        return entry

    # -- list windows and reports ------------------------------------------ #

    def _show_list_window(self, _parent: Any, _show_modal: Any, **kwargs: Any) -> Any:
        self.list_windows.append(kwargs)
        return _ClosedWindow()

    def _show_report(self, _parent: Any, _show_modal: Any, **kwargs: Any) -> None:
        self.reports.append(kwargs)

    @property
    def window(self) -> dict[str, Any]:
        """The last list window shown."""
        assert self.list_windows, "no list window was shown"
        return self.list_windows[-1]

    def enter(self, index: int | None = 0) -> object:
        """Press Enter on row *index* of the last list window."""
        on_enter = self.window.get("on_enter")
        assert on_enter is not None, "this window has no Enter action"
        return on_enter(index)

    def press(self, label: str, index: int | None = 0) -> object:
        """Press the button whose label (access key and all) is *label*."""
        for action in self.window.get("actions", []):
            if action.label == label or action.label.replace("&", "") == label:
                return action.run(index)
        names = [a.label for a in self.window.get("actions", [])]
        raise AssertionError(f"no action {label!r} in {names}")


class _ClosedWindow:
    def Destroy(self) -> None:  # noqa: N802 - wx's name
        return None


@pytest.fixture
def wp_response() -> type[FakeResponse]:
    """The response class, for a route that must answer with headers or a status."""
    return FakeResponse


@pytest.fixture
def wp_site() -> FakeSite:
    return FakeSite()


@pytest.fixture
def wp_host() -> FakeHost:
    return FakeHost()


@pytest.fixture
def wp_dialogs(monkeypatch: pytest.MonkeyPatch) -> DialogScript:
    from quill.ui import wordpress_dialogs as dlg
    from quill.ui import wordpress_item_dialogs as idlg

    script = DialogScript()
    for name in DialogScript.CANCEL:
        module = idlg if hasattr(idlg, name) and not hasattr(dlg, name) else dlg
        monkeypatch.setattr(module, name, script._entry(name))
    monkeypatch.setattr(dlg, "show_list_window", script._show_list_window)
    monkeypatch.setattr(dlg, "show_report", script._show_report)
    return script


SITE_URL = "https://radio.example"
API = "/wp-json/wp/v2"


@pytest.fixture
def wp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wp_host: FakeHost,
    wp_site: FakeSite,
    wp_dialogs: DialogScript,
) -> Any:
    """Shared WordPress commands on one connected site, Community Radio (an Editor)."""
    from quill.core.wordpress import sites as st
    from quill.ui.wordpress_commands import WordPressCommands

    monkeypatch.setattr(st, "_load_secret", lambda _site_id: "abcd efgh ijkl mnop qrst uvwx")
    monkeypatch.setattr(st, "save_secret", lambda _site_id, _secret: None)
    monkeypatch.setattr(st, "forget_secret", lambda _site_id: None)
    monkeypatch.setattr(st, "_import_publishing_connections", lambda: st.SiteStore())
    profile = st.SiteProfile(
        id="radio",
        name="Community Radio",
        site_url=SITE_URL,
        username="jeff",
        role="Editor",
        wp_version="6.8",
        # Off here, so a test's request list is only the command's own; the
        # waiting-comments count has its own tests, which turn it on.
        announce_waiting_comments=False,
    )
    st.save_sites(st.SiteStore([profile], "radio"), tmp_path)
    commands = WordPressCommands(wp_host, data_dir=tmp_path, opener=wp_site)
    commands.profile = profile  # for tests: the one site
    return commands
