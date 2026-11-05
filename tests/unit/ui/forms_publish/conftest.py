"""A harness for Publish Form, the exports, Responses and the Forms AI (wordpress.md 17a.7-17a.9).

Modelled on the WordPress harness (``tests/unit/ui/wordpress/conftest.py``),
with nothing real behind it:

- ``pub_host`` is the editor as the shared commands see it (the WordPress
  host): its text in a string, a ``.bfl`` path, what it announced, background
  work run at once, a fake browser, and a fake chosen AI (``host.ai``);
- ``pub_site`` answers REST routes by ``(method, path)`` and records every
  request, so a test asserts what was sent as well as what was said. It starts
  with the REST index listing ``baf/v1``;
- ``pub_dialogs`` scripts every dialog the commands open. Unscripted questions
  answer **cancel**, because cancel is the branch people forget to write;
- ``fp`` builds :class:`~quill.ui.forms_publish_commands.FormsPublishCommands`
  on all three, with one connected site, Community Radio.
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

SITE_URL = "https://radio.example"
BAF = "/wp-json/baf/v1"
INDEX = {"namespaces": ["wp/v2", "baf/v1"], "routes": {}}

FAIR = """bfl 1
form "Spring fair"

text #name "Your name"
  @required
  @autocomplete "name"
email #email "Email address"
  @required
  @autocomplete "email"
phone #phone "Phone"
radio #heard "How did you hear about us?"
  + A friend
  + Somewhere else
textarea #notes "Anything else?"
"""


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
    """An opener that answers by (method, path) and records every request."""

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Any] = {("GET", "/wp-json/"): INDEX}
        self.requests: list[Any] = []

    def on(self, method: str, path: str, answer: Any) -> FakeSite:
        self.routes[(method, path)] = answer
        return self

    def sent(self, method: str, path: str) -> list[Any]:
        return [
            r
            for r in self.requests
            if r.get_method() == method and urlparse(r.full_url).path == path
        ]

    def query(self, request: Any) -> dict[str, list[str]]:
        return parse_qs(urlparse(request.full_url).query)

    @staticmethod
    def body(request: Any) -> Any:
        return json.loads(request.data or b"null")

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
        return answer if isinstance(answer, FakeResponse) else FakeResponse(answer)


class FakeAiService:
    """The chosen AI: records each request, answers from a script."""

    def __init__(self) -> None:
        self.answers: list[str] = []
        self.prompts: list[str] = []
        self.requires: list[tuple[str, ...]] = []

    def ask(
        self, _kind: str, prompt: str, _context: Any, *, on_done: Any, on_error: Any, requires: Any
    ) -> None:
        self.prompts.append(prompt)
        self.requires.append(tuple(requires))
        if self.answers:
            on_done(self.answers.pop(0), None)
        else:
            on_error("no answer scripted")


class FakeAiEditor:
    """The editor carrying HostedAiMixin, as ``host.ai_editor()`` returns it."""

    def __init__(self) -> None:
        self.service = FakeAiService()
        self._safe_mode = False
        self.ready = True

    def _ai_ready(self) -> bool:
        return self.ready

    def _ai_capable(self, _what: str) -> bool:
        return True

    def _ai_service(self) -> FakeAiService:
        return self.service


@dataclass
class FakeHost:
    text: str = ""
    caret: int = 0
    path: Path | None = None
    parent: Any = None
    announced: list[str] = field(default_factory=list)
    opened: list[Path] = field(default_factory=list)
    browsed: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    replaced: int = 0
    ai: FakeAiEditor = field(default_factory=FakeAiEditor)

    def show_modal(self, dialog: Any, label: str) -> int:
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
        self.replaced += 1

    def insert_text(self, text: str) -> None:
        self.text = self.text[: self.caret] + text + self.text[self.caret :]
        self.caret += len(text)

    def open_path(self, path: Path) -> None:
        self.opened.append(path)

    def open_in_browser(self, url: str) -> None:
        self.browsed.append(url)

    def ai_editor(self) -> Any:
        return self.ai

    @property
    def said(self) -> str:
        return "\n".join(self.announced)


class _Closed:
    def Destroy(self) -> None:  # noqa: N802 - wx's name
        return None


class Script:
    """Scripted answers for every dialog; unscripted ones cancel."""

    CANCEL: dict[str, Any] = {
        "ask_choice": None,
        "ask_text": None,
        "confirm": False,
        "save_as": None,
        "ask_save_path": None,
    }

    def __init__(self) -> None:
        self.answers: dict[str, list[Any]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.list_windows: list[dict[str, Any]] = []
        self.reports: list[dict[str, Any]] = []

    def answer(self, name: str, *values: Any) -> Script:
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

    @property
    def window(self) -> dict[str, Any]:
        assert self.list_windows, "no list window was shown"
        return self.list_windows[-1]

    def rows(self) -> list[str]:
        return list(self.window["rows"])

    def press(self, label: str, index: int | None = 0) -> object:
        for action in self.window.get("actions", []):
            if action.label == label or action.label.replace("&", "") == label:
                return action.run(index)
        names = [a.label for a in self.window.get("actions", [])]
        raise AssertionError(f"no action {label!r} in {names}")


@pytest.fixture
def pub_site() -> FakeSite:
    return FakeSite()


@pytest.fixture
def pub_host(tmp_path: Path) -> FakeHost:
    path = tmp_path / "fair.bfl"
    path.write_text(FAIR, encoding="utf-8")
    return FakeHost(text=FAIR, path=path)


@pytest.fixture
def pub_dialogs(monkeypatch: pytest.MonkeyPatch) -> Script:
    from quill.ui import forms_dialogs as fdlg
    from quill.ui import wordpress_dialogs as dlg
    from quill.ui import wordpress_route_dialogs as rdlg

    script = Script()
    for name in ("ask_choice", "ask_text", "confirm"):
        monkeypatch.setattr(dlg, name, script.entry(name))
    monkeypatch.setattr(dlg, "show_list_window", script.show_list_window)
    monkeypatch.setattr(dlg, "show_report", script.show_report)
    monkeypatch.setattr(rdlg, "save_as", script.entry("save_as"))
    monkeypatch.setattr(fdlg, "ask_save_path", script.entry("ask_save_path"))
    return script


@pytest.fixture
def profile_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    from quill.core.wordpress import sites as st

    monkeypatch.setattr(st, "_load_secret", lambda _site_id: "abcd efgh ijkl mnop qrst uvwx")
    monkeypatch.setattr(st, "_import_publishing_connections", lambda: st.SiteStore())

    def make(**changes: Any) -> Any:
        values: dict[str, Any] = {
            "id": "radio",
            "name": "Community Radio",
            "site_url": SITE_URL,
            "username": "jeff",
            "role": "Administrator",
            "announce_waiting_comments": False,
            "announce_new_responses": False,
        }
        values.update(changes)
        profile = st.SiteProfile(**values)
        st.save_sites(st.SiteStore([profile], profile.id), tmp_path)
        return profile

    return make


@pytest.fixture
def fp(
    tmp_path: Path,
    pub_host: FakeHost,
    pub_site: FakeSite,
    pub_dialogs: Script,
    profile_factory: Any,
) -> Any:
    """The second-half Forms commands on one connected site, Community Radio."""
    from quill.ui import forms_site_base as base
    from quill.ui.forms_publish_commands import FormsPublishCommands

    base.forget_told()

    class Commands(FormsPublishCommands):
        def __init__(self) -> None:
            self.host = pub_host
            self._data_dir = tmp_path
            self._opener = pub_site

    commands = Commands()
    commands.profile = profile_factory()
    yield commands
    base.forget_told()


def form_payload(form_id: int = 12, **changes: Any) -> dict[str, Any]:
    """A form as BAF's REST API returns it."""
    data: dict[str, Any] = {
        "id": form_id,
        "title": "Spring fair",
        "slug": "spring-fair",
        "status": "active",
        "entry_count": 2,
        "updated_at": "2026-11-03 14:10:00",
        "bfl_source": 'bfl 1\nform "Spring fair"\n',
        "config": {
            "fields": [{"id": "old", "label": "Old"}],
            "form_model": {
                "version": 1,
                "title": "Spring fair",
                "pages": [
                    {
                        "id": "page_1",
                        "items": [
                            {"id": "name", "type": "text", "label": "Your name"},
                            {"id": "email", "type": "email", "label": "Email address"},
                            {"id": "city", "type": "text", "label": "City"},
                        ],
                    }
                ],
            },
        },
    }
    data.update(changes)
    return data


def entry_payload(entry_id: int, when: str, **answers: Any) -> dict[str, Any]:
    return {
        "id": entry_id,
        "form_id": 12,
        "status": "active",
        "is_read": 0,
        "is_starred": 0,
        "fields": answers,
        "created_at": when,
    }


@pytest.fixture
def make_form() -> Any:
    return form_payload


@pytest.fixture
def make_entry() -> Any:
    return entry_payload
