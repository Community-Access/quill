"""wp-admin parity for Comments and People in the WordPress Workbench (wordpress.md 9.18, 4 and 5).

The real frame on a fake site, the work run inline: Comment Counts, Show Its
Comments, Empty Comment Trash, one outcome per comment, the comment sheet's
date and IP and its conflict check, bulk Change Role and Remove with the
self-lockout guards, Add a Person as one sheet, Set New Password and Your
Profile. Every handler is called through the window's own command path.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.api import WordPressApiError  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _go,
    _inline,
    _select,
)


class _Total:
    def __init__(self, total: int) -> None:
        self.payload: Any = []
        self.total = total


class ParityApi(FakeApi):
    """Counts by X-WP-Total, comments by id, three people, and refusals on demand."""

    def __init__(self) -> None:
        super().__init__()
        self.role = "administrator"
        self.comments.append({
            "id": 9,
            "post": 1,
            "author_name": "Old",
            "status": "trash",
            "date_gmt": "2026-10-01T08:00:00",
            "content": {"rendered": "<p>Gone</p>"},
        })
        for comment in self.comments:
            comment.update({
                "author_email": f"{comment['author_name'].lower()}@example.org",
                "date": "2026-11-03T09:00:00",
            })
        self.comments[0]["author_ip"] = "203.0.113.7"
        self.people = [
            {"id": 3, "name": "Jeff", "roles": ["administrator"]},
            {"id": 4, "name": "Ann", "roles": ["author"]},
            {"id": 5, "name": "Bo", "roles": ["contributor"]},
        ]
        self.refuse: set[str] = set()

    def get(self, route: str, **params: Any) -> Any:
        answer = super().get(route, **params)
        if route == "wp/v2/users/me":
            answer["capabilities"].update({"edit_users": True, "create_users": True})
            answer.update({"email": "jeff@example.org", "nickname": "jeff", "url": ""})
        elif route.startswith("wp/v2/comments/"):
            comment_id = int(route.rsplit("/", 1)[1])
            return dict(next(c for c in self.comments if c["id"] == comment_id))
        return answer

    def request(self, method: str, route: str, **kw: Any) -> Any:
        params = dict(kw.get("params") or {})
        if method == "GET" and route == "wp/v2/comments":
            status = params.get("status")
            wanted = ("hold", "approved") if status == "all" else (status,)
            wanted = tuple("approved" if s == "approve" else s for s in wanted)
            found = [
                c
                for c in self.comments
                if c["status"] in wanted
                and (not params.get("post") or c["post"] == params["post"])
                and not params.get("author")
            ]
            return _Total(len(found))
        if method == "GET" and route == "wp/v2/posts":
            return _Total(2 if params.get("author") == 4 else 0)
        return super().request(method, route, **kw)

    def iter_collection(self, route: str, params: Any = None, **kw: Any):
        if route == "wp/v2/users":
            yield from (dict(p) for p in self.people)
            return
        yield from super().iter_collection(route, params, **kw)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route in self.refuse:
            raise WordPressApiError("You are not allowed to do that.")
        if route.startswith("wp/v2/comments/") and "status" not in (body or {}):
            self.writes.append(("POST", route, body))
            return {"id": int(route.rsplit("/", 1)[1]), **body}
        return super().post(route, body, **params)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = ParityApi()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def sheets(monkeypatch):
    from quill.ui import workbench_sheet_editor as editor

    opened: list[Any] = []
    monkeypatch.setattr(editor.WorkbenchSheetEditor, "show", lambda self: opened.append(self) or 0)
    return opened


@pytest.fixture
def yes(monkeypatch):
    asked: list[str] = []

    def confirm(*_a: Any, **k: Any) -> bool:
        asked.append(k["message"])
        return True

    monkeypatch.setattr(dlg, "confirm", confirm)
    return asked


# -- comments (package 4) -------------------------------------------------------


def test_comment_counts_say_every_view_in_one_sentence(bench) -> None:
    _go(bench, NodeRef("site", "comments", SITE))
    bench.run(command("comment_counts"))
    said = bench.said[-1]
    assert "1 waiting" in said and "1 spam" in said and "1 in the Trash" in said
    assert "in All" in said and "are yours" in said


def test_show_its_comments_filters_to_the_post_and_counts(bench) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 1)  # News, post 2: Ann's comment waits, Bot's is spam
    bench.run(command("show_comments"))
    assert bench.current == NodeRef("site", "comments", SITE)
    assert bench.filter.GetValue() == "post:2"
    assert bench.said[-1].startswith("1 comment on News")


def test_empty_comment_trash_confirms_the_count_and_deletes(bench, yes) -> None:
    _go(bench, NodeRef("site", "comments_trash", SITE))
    bench.run(command("empty_comment_trash"))
    assert "1 comment" in yes[-1] and "cannot be undone" in yes[-1]
    assert ("DELETE", "wp/v2/comments/9", {"force": True}) in bench.api.writes
    assert "Deleted 1 comment" in bench.said[-1]


def test_bulk_moderation_says_each_failure_and_undoes_only_the_changed(bench) -> None:
    _go(bench, NodeRef("site", "comments_waiting", SITE))
    bench.api.comments[1]["status"] = "hold"  # two waiting now: 7 and 8
    bench.run(command("refresh"))
    _select(bench, 0, 1)
    bench.api.refuse.add("wp/v2/comments/8")
    bench.run(command("approve"))
    said = bench.said[-1]
    assert said.startswith("1 of 2 items approved") and "Not changed" in said
    bench.api.refuse.clear()
    bench.run(command("undo"))
    undone = [w for w in bench.api.writes if w[1] == "wp/v2/comments/8"]
    assert undone == []  # the refused one is not "put back"


def test_the_comment_sheet_edits_date_shows_ip_and_checks_conflicts(
    bench, sheets, monkeypatch
) -> None:
    _go(bench, NodeRef("site", "comments_waiting", SITE))
    _select(bench, 0)
    bench.run(command("sheet"))
    sheet = sheets[-1]
    assert sheet.controls["author_ip"].GetValue() == "203.0.113.7"
    assert sheet.controls["date"].GetValue() == "2026-11-03T09:00:00"
    sheet.controls["author_name"].ChangeValue("Ann Smith")
    sheet.collect()
    bench.api.comments[0]["content"] = {"raw": "Changed elsewhere", "rendered": "x"}
    asked: list[str] = []
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: asked.append(k["message"]) or False)
    sheet._on_save(sheet.state)
    assert asked and "Nothing was sent" in asked[0]
    assert not any(
        w[1] == "wp/v2/comments/7" and "author_name" in (w[2] or {}) for w in bench.api.writes
    )


# -- people (package 5) ---------------------------------------------------------


def _users(bench: WorkbenchFrame) -> None:
    _go(bench, NodeRef("site", "users", SITE))


def test_bulk_change_role_keeps_you_and_undoes(bench, yes, monkeypatch) -> None:
    _users(bench)
    _select(bench, 0, 1, 2)
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 3)  # Editor
    bench.run(command("change_role"))
    assert "Jeff" in yes[-1] and "Administrator" in yes[-1]  # left out, with why
    roles = [(w[1], w[2]) for w in bench.api.writes if w[1].startswith("wp/v2/users/")]
    assert roles == [
        ("wp/v2/users/4", {"roles": ["editor"]}),
        ("wp/v2/users/5", {"roles": ["editor"]}),
    ]
    assert bench.said[-1].startswith("2 people now Editor")
    bench.run(command("undo"))
    assert ("POST", "wp/v2/users/5", {"roles": ["contributor"]}) in bench.api.writes


def test_bulk_remove_gives_the_posts_to_one_person_and_cannot_be_undone(
    bench, yes, monkeypatch
) -> None:
    _users(bench)
    _select(bench, 1, 2)
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)  # Jeff, the only other
    bench.run(command("remove_user"))
    assert "2 posts move to Jeff" in yes[-1] and "cannot be undone" in yes[-1]
    deletes = [w for w in bench.api.writes if w[0] == "DELETE"]
    assert deletes == [
        ("DELETE", "wp/v2/users/4", {"force": True, "reassign": 3}),
        ("DELETE", "wp/v2/users/5", {"force": True, "reassign": 3}),
    ]
    assert "Removed 2 people" in bench.said[-1]


def test_add_a_person_is_one_sheet_previewed_with_no_email(bench, sheets, yes) -> None:
    _users(bench)
    bench.run(command("new_here"))
    sheet = sheets[-1]
    for key, value in (("username", "cara"), ("email", "cara@example.org"), ("first_name", "Cara")):
        sheet.controls[key].ChangeValue(value)
    sheet.controls["roles"].SetStringSelection("author")
    sheet.collect()
    sheet._on_save(sheet.state)
    assert "sends no email" in yes[-1]
    body = next(w[2] for w in bench.api.writes if w[1] == "wp/v2/users")
    assert (
        body["username"] == "cara" and body["roles"] == ["author"] and body["first_name"] == "Cara"
    )
    assert len(body["password"]) >= 24 and not any(body["password"] in s for s in bench.said)


def test_set_new_password_previews_and_never_says_it(bench, yes, monkeypatch) -> None:
    _users(bench)
    _select(bench, 1)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "correct horse battery")
    bench.run(command("set_password"))
    assert "Ann" in yes[-1] and "cannot be put back" in yes[-1]
    assert ("POST", "wp/v2/users/4", {"password": "correct horse battery"}) in bench.api.writes
    assert not any("horse" in s for s in bench.said)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "short")
    bench.run(command("set_password"))
    assert "12 characters" in bench.said[-1]


def test_your_profile_is_your_sheet_without_the_role_page(bench, sheets) -> None:
    _users(bench)
    bench.run(command("your_profile"))
    sheet = sheets[-1]
    assert "role" not in [page.key for page in sheet.sheet.pages]
    sheet.controls["nickname"].ChangeValue("jb")
    sheet.collect()
    sheet._on_save(sheet.state)
    assert ("POST", "wp/v2/users/me", {"nickname": "jb"}) in bench.api.writes


def test_the_user_sheet_says_how_many_posts_they_wrote(bench, sheets) -> None:
    _users(bench)
    _select(bench, 1)
    bench.run(command("sheet"))
    assert sheets[-1].controls["post_count"].GetValue() == "2"
