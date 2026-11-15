"""Change a Field Type on a Gravity Forms form, through the real Workbench window (WP-C).

A fake ``gf/v2`` site whose form can change under the person while they read
the preview. Background work runs inline; dialogs are answered by patching the
helpers the command calls. Each test calls the handler the context menu reaches.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.core.wordpress.workbench_permissions import Access  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"
ROUTE = "gf/v2/forms/1"

FORM = {
    "id": "1",
    "title": "Signup",
    "notifications": {"a1": {"id": "a1", "name": "Admin"}},
    "fields": [
        {"id": 1, "type": "text", "label": "Name", "isRequired": True, "cssClass": "x"},
        {
            "id": 2,
            "type": "radio",
            "label": "Show",
            "choices": [{"text": "Morning", "value": "am", "isSelected": False}],
        },
        {"id": 3, "type": "address", "label": "Address", "inputs": [{"id": "3.1"}]},
    ],
}


class ConversionApi:
    def __init__(self) -> None:
        self.site_name = SITE
        self.form = copy.deepcopy(FORM)
        self.caps: dict[str, bool] = {"edit_posts": True, "gform_full_access": True}
        self.puts: list[dict[str, Any]] = []
        self.reads = 0
        self.edit_before_read: dict[int, Any] = {}  # somebody else's change, by read number
        self.store_as: Any = None  # what the site keeps instead of what was sent

    def get(self, route: str, **_p: Any) -> Any:
        if route == "wp/v2/users/me":
            return {"id": 3, "name": "Jeff", "roles": ["editor"], "capabilities": self.caps}
        if route == "":
            return {"name": SITE, "namespaces": ["wp/v2", "gf/v2"], "routes": {}}
        if route == "gf/v2/forms":
            return {"1": {"id": "1", "title": "Signup", "entries": "0"}}
        if route == ROUTE:
            self.reads += 1
            if self.reads in self.edit_before_read:
                self.edit_before_read.pop(self.reads)(self.form)
            return copy.deepcopy(self.form)
        return []

    def iter_collection(self, *_a: Any, **_k: Any):
        yield from ()

    def request(self, method: str, route: str, **kw: Any) -> Any:
        body = kw.get("json_body")
        assert (method, route) == ("PUT", ROUTE)
        self.puts.append(copy.deepcopy(body))
        self.form = copy.deepcopy(self.store_as(body) if self.store_as else body)

        class _R:
            payload = body

        return _R()


class _Host:
    def __init__(self, said: list[str]) -> None:
        self.said = said
        self.parent = None

    def announce(self, text: str) -> None:
        self.said.append(text)

    def open_in_browser(self, url: str) -> None:
        pass


class _Commands:
    def __init__(self, said: list[str]) -> None:
        self.host = _Host(said)

    def sites(self) -> SiteStore:
        return SiteStore([SiteProfile("s1", SITE, "https://radio.example", "jeff")], "s1")


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = ConversionApi()
    provider = WordPressWorkbenchProvider(
        _Commands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def answers(monkeypatch):
    asked: dict[str, list[Any]] = {"previews": [], "choices": []}
    replies: dict[str, list[Any]] = {"choice": [], "preview": []}

    def preview(*_a: Any, **kw: Any) -> bool:
        asked["previews"].append(kw)
        return replies["preview"].pop(0) if replies["preview"] else True

    def choice(*_a: Any, **kw: Any) -> Any:
        asked["choices"].append(kw)
        return replies["choice"].pop(0)

    monkeypatch.setattr(wdlg, "ask_preview", preview)
    monkeypatch.setattr(dlg, "ask_choice", choice)
    asked["replies"] = replies  # type: ignore[assignment]
    return asked


def _form_row(frame: WorkbenchFrame) -> Any:
    ref = NodeRef("site", "forms", SITE)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    assert frame.rows and frame.rows[0].kind == "gravity_form"
    frame.list.Select(0)
    return frame.rows[0]


_SELECT = 4  # "Drop-down list" in GRAVITY_FIELD_TYPES order


def test_a_conversion_previews_sends_the_whole_form_verifies_and_undoes(bench, answers) -> None:
    api = bench.api
    answers["replies"]["choice"] += [0, _SELECT]  # Name, then Drop-down list
    bench.provider.do_change_gravity_field_type(None, _form_row(bench))

    fields_offered = answers["choices"][0]["rows"]
    assert fields_offered == ["1: Name (Single line text)", "2: Show (Radio buttons)"]
    preview = answers["previews"][-1]
    assert preview["summary"] == "Change Name (field 1) from Single line text to Drop-down list."
    assert preview["lines"][:2] == [f"Site: {SITE}", "Form: Signup"]
    assert any(
        line.startswith("Kept: id, label, isRequired, cssClass") for line in preview["lines"]
    )

    sent = api.puts[-1]
    assert sent["notifications"] == FORM["notifications"]
    assert sent["fields"][1:] == FORM["fields"][1:]
    assert sent["fields"][0]["type"] == "select" and sent["fields"][0]["isRequired"] is True
    assert bench.said[-1] == f"Changed Name in Signup on {SITE}."

    assert bench.provider.history.undo()
    assert api.form == FORM


def test_declining_the_preview_sends_nothing(bench, answers) -> None:
    answers["replies"]["choice"] += [0, _SELECT]
    answers["replies"]["preview"].append(False)
    bench.provider.do_change_gravity_field_type(None, _form_row(bench))
    assert bench.api.puts == []


def test_a_form_changed_during_the_preview_is_not_overwritten(bench, answers) -> None:
    api = bench.api
    answers["replies"]["choice"] += [0, _SELECT]
    # Read 1 fills the field list; somebody renames field 2 before the save reads again.
    api.edit_before_read[2] = lambda form: form["fields"][1].__setitem__("label", "Programme")
    bench.provider.do_change_gravity_field_type(None, _form_row(bench))
    assert api.puts == []
    assert api.form["fields"][0]["type"] == "text"
    assert any("changed while you reviewed" in s for s in bench.said)


def test_a_replacement_that_reads_back_wrong_is_said_and_can_be_undone(bench, answers) -> None:
    api = bench.api
    api.store_as = lambda body: {**body, "fields": copy.deepcopy(FORM["fields"])}
    answers["replies"]["choice"] += [0, _SELECT]
    bench.provider.do_change_gravity_field_type(None, _form_row(bench))
    said = bench.said[-1]
    assert "reads back differently" in said and "Field 1 reads back as text, not select." in said
    assert "Ctrl+Z" in said
    assert bench.provider.history.undo() and api.puts[-1] == FORM


def test_complex_fields_are_never_offered(bench, answers) -> None:
    answers["replies"]["choice"] += [None]
    bench.provider.do_change_gravity_field_type(None, _form_row(bench))
    assert "Address" not in " ".join(answers["choices"][0]["rows"])
    assert bench.api.puts == []


def test_it_needs_full_access_and_gravityforms_create_form(bench, answers) -> None:
    provider = bench.provider
    row = _form_row(bench)
    change = command("change_gravity_field_type")
    assert provider.refusal_for(change, row) == ""  # gform_full_access grants it

    provider.access_store.set("s1", Access.ORGANIZE)
    assert "Workbench access" in provider.refusal_for(change, row)
    provider.do_change_gravity_field_type(None, row)
    assert answers["choices"] == [] and bench.api.puts == []

    provider.access_store.set("s1", Access.FULL)
    bench.api.caps = {"edit_posts": True}
    provider._contexts.clear()
    row = _form_row(bench)
    said = provider.refusal_for(change, row)
    assert "gravityforms create form" in said and "Editor" in said

    bench.api.caps = {"edit_posts": True, "gravityforms_create_form": True}
    provider._contexts.clear()
    assert provider.refusal_for(change, _form_row(bench)) == ""
