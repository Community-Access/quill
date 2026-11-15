"""New Gravity Form, Edit Form and Copy between plugins, through the real Workbench (WP-C).

A fake site with both ``gf/v2`` and ``qaf/v1`` whose forms are shaped as each
plugin documents them. Background work runs inline; the editor and the
previews are answered by patching the helpers the commands call. Each test
calls the handler the context menu, New Here or the Item menu reaches.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import gravity_build as gb  # noqa: E402
from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.gravity_build_save import ENTRIES_LINE  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command  # noqa: E402
from quill.core.wordpress.workbench_permissions import Access  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_gravity_editor as gedit  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"
ROUTE = "gf/v2/forms/1"

FORM = {
    "id": "1",
    "title": "Signup",
    "button": {"type": "text", "text": "Join", "imageUrl": ""},
    "gravityformsmailchimp": {"keep": "me"},
    "confirmations": {
        "c1": {"id": "c1", "isDefault": True, "type": "message", "message": "Thanks!"},
    },
    "notifications": {
        "n1": {"id": "n1", "name": "Admin Notification", "toType": "email",
               "to": "{admin_email}", "subject": "New"},
    },
    "fields": [
        {"id": 1, "type": "text", "label": "Name", "isRequired": True, "size": "large"},
        {"id": 2, "type": "radio", "label": "Show",
         "choices": [{"text": "Morning", "value": "am", "isSelected": False}]},
        {"id": 3, "type": "list", "label": "Songs", "choices": [{"text": "x"}]},
    ],
}  # fmt: skip

QAF_FORM = {
    "id": 5,
    "title": "Feedback",
    "status": "active",
    "entry_count": 2,
    "model": {
        "version": 1,
        "title": "Feedback",
        "pages": [
            {
                "id": "page_1",
                "items": [
                    {"id": "said", "type": "textarea", "label": "What did you think?"},
                    {"id": "stars", "type": "rating", "label": "Stars"},
                ],
            }
        ],
    },
}


class Api:
    def __init__(self) -> None:
        self.site_name = SITE
        self.form = copy.deepcopy(FORM)
        self.namespaces = ["wp/v2", "gf/v2", "qaf/v1"]
        self.caps: dict[str, bool] = {"edit_posts": True, "gform_full_access": True}
        self.writes: list[tuple[str, str, Any]] = []
        self.reads = 0
        self.edit_before_read: dict[int, Any] = {}

    def get(self, route: str, **_p: Any) -> Any:
        if route == "wp/v2/users/me":
            return {"id": 3, "name": "Jeff", "roles": ["editor"], "capabilities": self.caps}
        if route == "":
            return {"name": SITE, "namespaces": self.namespaces, "routes": {}}
        if route == "gf/v2/forms":
            return {"1": {"id": "1", "title": "Signup", "entries": "4"}}
        if route == ROUTE:
            self.reads += 1
            if self.reads in self.edit_before_read:
                self.edit_before_read.pop(self.reads)(self.form)
            return copy.deepcopy(self.form)
        if route == "gf/v2/forms/9":
            return copy.deepcopy(self.made)
        if route == "qaf/v1/forms/5":
            return copy.deepcopy(QAF_FORM)
        return []

    def iter_collection(self, route: str, *_a: Any, **_k: Any):
        if route == "qaf/v1/forms":
            yield copy.deepcopy(QAF_FORM)

    def request(self, method: str, route: str, **kw: Any) -> Any:
        body = copy.deepcopy(kw.get("json_body"))
        self.writes.append((method, route, body))
        answer: Any = body
        if (method, route) == ("PUT", ROUTE):
            self.form = copy.deepcopy(body)
        elif (method, route) == ("POST", "gf/v2/forms"):
            self.made = {**body, "id": "9"}
            answer = self.made
        elif (method, route) == ("POST", "qaf/v1/forms"):
            answer = {"id": 6, "title": body["title"], "status": "draft"}

        class _R:
            payload = answer

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
    api = Api()
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
    """The editor's, the previews' and the title's answers, and what each was asked."""
    asked: dict[str, list[Any]] = {"forms": [], "previews": [], "texts": []}
    replies: dict[str, list[Any]] = {"form": [], "preview": [], "text": []}

    def form(*_a: Any, **kw: Any) -> Any:
        asked["forms"].append(kw)
        edit = replies["form"].pop(0) if replies["form"] else None
        if edit is None:
            return None
        edited = copy.deepcopy(kw["form"])
        edit(edited)
        return edited

    def preview(*_a: Any, **kw: Any) -> bool:
        asked["previews"].append(kw)
        return replies["preview"].pop(0) if replies["preview"] else True

    def text(*_a: Any, **kw: Any) -> Any:
        asked["texts"].append(kw)
        return replies["text"].pop(0)

    monkeypatch.setattr(gedit, "ask_form", form)
    monkeypatch.setattr(wdlg, "ask_preview", preview)
    monkeypatch.setattr(dlg, "ask_text", text)
    asked["replies"] = replies  # type: ignore[assignment]
    return asked


def _row(frame: WorkbenchFrame, kind: str) -> Any:
    ref = NodeRef("site", "forms", SITE)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    index = next(i for i, r in enumerate(frame.rows) if r.kind == kind)
    frame.list.Select(index)
    return frame.rows[index]


def _rename(form: dict[str, Any]) -> None:
    gb.edit_field(form["fields"][0], {"label": "Full name"})
    gb.add_field(form, "email", {"label": "Email", "isRequired": True}, at=1)


def test_edit_form_previews_puts_the_whole_form_and_undoes(bench, answers) -> None:
    api = bench.api
    answers["replies"]["form"].append(_rename)
    bench.provider.do_edit_gravity_form(None, _row(bench, "gravity_form"))

    assert answers["forms"][0]["title"] == "Edit Gravity Form - Signup"
    preview = answers["previews"][-1]
    assert preview["yes"] == "Save Form" and preview["summary"] == f"Save Signup on {SITE}."
    assert "Change Full name: label." in preview["lines"]
    assert "Add field 2: Email, Email." in preview["lines"]
    assert preview["lines"][-1] == ENTRIES_LINE

    method, route, sent = api.writes[-1]
    assert (method, route) == ("PUT", ROUTE)
    assert sent["gravityformsmailchimp"] == {"keep": "me"} and sent["notifications"]
    assert sent["fields"][2]["id"] == 2 and sent["fields"][3] == FORM["fields"][2]
    assert sent["fields"][1]["id"] == 4  # a new id, above every id the form had
    assert not any("entries" in r for _m, r, _b in api.writes)
    assert bench.said[-1] == f"Saved Signup on {SITE}. Entries were not touched."

    assert bench.provider.history.undo()
    assert api.form == FORM


def test_a_form_changed_while_editing_is_not_overwritten(bench, answers) -> None:
    api = bench.api
    api.edit_before_read[2] = lambda form: form.__setitem__("title", "Their title")
    answers["replies"]["form"].append(_rename)
    bench.provider.do_edit_gravity_form(None, _row(bench, "gravity_form"))
    assert not [w for w in api.writes if w[0] == "PUT"]
    assert "changed on the site since you opened it" in bench.said[-1]


def test_findings_come_first_and_cancel_goes_back_to_the_field(bench, answers) -> None:
    def unlabelled(form: dict[str, Any]) -> None:
        gb.add_field(form, "text", {"label": ""})

    answers["replies"]["form"] += [unlabelled, None]  # then Cancel in the editor
    answers["replies"]["preview"].append(False)  # Cancel on the findings
    bench.provider.do_edit_gravity_form(None, _row(bench, "gravity_form"))
    checks = answers["previews"][0]
    assert checks["title"] == "Check Before Saving" and checks["yes"] == "Save Anyway"
    assert "Field 4 (text) has no label. Give it one." in checks["lines"]
    assert answers["forms"][1]["focus_field"] == "4"
    assert bench.api.writes == []


def test_new_here_on_forms_makes_a_new_gravity_form_and_undo_trashes_it(bench, answers) -> None:
    api = bench.api
    answers["replies"]["text"].append("Contact")
    answers["replies"]["form"].append(
        lambda form: gb.add_field(form, "email", {"label": "Email", "isRequired": True})
    )
    _row(bench, "gravity_form")
    bench.provider.do_new_here(NodeRef("site", "forms", SITE), None)

    assert answers["forms"][0]["form"]["button"]["text"] == "Submit"
    preview = answers["previews"][-1]
    assert preview["yes"] == "Make Form" and "New form: Contact." in preview["lines"]
    method, route, sent = api.writes[-1]
    assert (method, route) == ("POST", "gf/v2/forms") and sent["title"] == "Contact"
    assert sent["fields"][0]["type"] == "email"
    assert bench.said[-1] == f"Made Contact on {SITE}. Entries were not touched."
    assert bench.provider.history.undo()
    assert api.writes[-1] == ("DELETE", "gf/v2/forms/9", None)


def test_new_gravity_form_needs_the_plugin_and_its_permission(bench, answers) -> None:
    provider = bench.provider
    _row(bench, "gravity_form")
    bench.api.caps = {"edit_posts": True}
    provider._contexts.clear()
    provider.do_new_gravity_form(NodeRef("site", "forms", SITE), None)
    assert "gravityforms create form" in bench.said[-1] and "Editor" in bench.said[-1]
    assert answers["texts"] == []

    provider.access_store.set("s1", Access.ORGANIZE)
    provider.do_new_gravity_form(NodeRef("site", "forms", SITE), None)
    assert "Workbench access" in bench.said[-1]

    provider.access_store.set("s1", Access.FULL)
    bench.api.caps = {"edit_posts": True, "gravityforms_create_form": True}
    bench.api.namespaces = ["wp/v2", "qaf/v1"]
    provider._contexts.clear()
    tx.clear_cache()
    _row(bench, "form")
    provider.do_new_gravity_form(NodeRef("site", "forms", SITE), None)
    assert "Gravity Forms is not on" in bench.said[-1]


def test_edit_form_needs_gravityforms_edit_forms(bench, answers) -> None:
    provider = bench.provider
    edit = command("edit_gravity_form")
    bench.api.caps = {"edit_posts": True}
    provider._contexts.clear()
    row = _row(bench, "gravity_form")
    said = provider.refusal_for(edit, row)
    assert "gravityforms edit forms" in said and "fields and settings" in said
    bench.api.caps = {"edit_posts": True, "gravityforms_edit_forms": True}
    provider._contexts.clear()
    row = _row(bench, "gravity_form")
    assert provider.refusal_for(edit, row) == ""
    qaf = _row(bench, "form")
    assert "Gravity Forms command" in provider.refusal_for(edit, qaf)


def test_copy_a_qaf_form_as_a_gravity_form(bench, answers) -> None:
    api = bench.api
    bench.provider.do_copy_as_gravity_form(None, _row(bench, "form"))
    preview = answers["previews"][-1]
    assert preview["yes"] == "Make Gravity Form"
    assert any(line.startswith("Cannot carry over: Stars is a rating") for line in preview["lines"])
    method, route, sent = api.writes[-1]
    assert (method, route) == ("POST", "gf/v2/forms")
    assert [f["type"] for f in sent["fields"]] == ["textarea"]
    assert bench.said[-1] == f"Made Feedback on {SITE}. Entries were not touched."


def test_copy_a_gravity_form_as_a_qaf_draft(bench, answers) -> None:
    api = bench.api
    bench.provider.do_copy_as_qaf_form(None, _row(bench, "gravity_form"))
    preview = answers["previews"][-1]
    assert preview["yes"] == "Make Draft"
    assert any("Songs is a list field" in line for line in preview["lines"])
    method, route, sent = api.writes[-1]
    assert (method, route) == ("POST", "qaf/v1/forms") and sent["status"] == "draft"
    assert [i["id"] for i in sent["model"]["pages"][0]["items"]] == ["field_1", "field_2"]
    assert "draft of Signup" in bench.said[-1]


def test_the_build_commands_are_on_the_rows_they_belong_to() -> None:
    gravity = {a.command_id for a in WORDPRESS_ACTIONS.rows_for("gravity_form")}
    qaf = {a.command_id for a in WORDPRESS_ACTIONS.rows_for("form")}
    for verb in ("edit_gravity_form", "new_gravity_form", "copy_as_qaf_form"):
        assert command(verb) in gravity
    assert command("copy_as_gravity_form") in qaf
