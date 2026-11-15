"""wp-admin parity for Comments and People, the wx-free half (wordpress.md 9.18, packages 4 and 5).

Counts, the comment conflict stand-in, the comment type filter, the guards on
bulk role changes and removals, the Add New body and the password rule; and
that every new command has a key or a written reason, and F1 help.
"""

from __future__ import annotations

import pytest

from quill.core.wordpress.site import Account
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, WORDPRESS_KEYS, command
from quill.core.wordpress.workbench_admin_actions import KEYLESS
from quill.core.wordpress.workbench_edit import EditRefused
from quill.core.wordpress.workbench_filter import params_for
from quill.core.wordpress.workbench_moderation import counts_sentence, version_of
from quill.core.wordpress.workbench_people_bulk import (
    NEW_USER_SHEET,
    new_user_body,
    new_user_preview,
    password_problem,
    remove_plan,
    role_plan,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.filters import parse

_ADMIN = Account(3, "Jeff", "jeff", ("administrator",), frozenset({"promote_users"}))


def _person(user_id: int, name: str, role: str) -> WbRow:
    return WbRow("user", "Site", str(user_id), {"name": name}, name, status=role)


def test_every_new_command_has_a_key_or_a_reason_and_help() -> None:
    for verb in ("comment_counts", "show_comments", "empty_comment_trash", "your_profile"):
        assert WORDPRESS_KEYS.get(command(verb)), verb
    assert KEYLESS[command("set_password")]
    offered = {
        row.command_id: row for kind in ("item", "user") for row in WORDPRESS_ACTIONS.rows_for(kind)
    }
    assert offered[command("show_comments")].help
    assert offered[command("set_password")].help


def test_counts_read_as_one_sentence_with_all_and_mine() -> None:
    said = counts_sentence("Radio", {"hold": 4, "approve": 120, "spam": 37, "trash": 2}, 3)
    assert said.startswith("Radio: 4 waiting, 120 approved, 37 spam and 2 in the Trash")
    assert "124 in All" in said and "3 are yours" in said


def test_a_comment_or_user_has_a_version_from_its_fields() -> None:
    raw = {"status": "hold", "content": {"raw": "Hi"}, "author_name": "Ann"}
    assert version_of("comment", raw) == version_of("comment", dict(raw))
    assert version_of("comment", raw) != version_of("comment", {**raw, "content": {"raw": "Ho"}})
    assert version_of("item", {"modified_gmt": "2026-11-01T10:00:00"}) == "2026-11-01T10:00:00"
    assert version_of("term", {"name": "x"}) == ""


def test_comment_type_filters_by_the_comments_route_own_type() -> None:
    assert params_for(parse("comment_type:pingback")) == {"type": "pingback"}


def test_bulk_role_change_never_removes_you_or_the_last_administrator() -> None:
    users = [
        {"id": 3, "roles": ["administrator"]},
        {"id": 4, "roles": ["administrator"]},
        {"id": 5, "roles": ["author"]},
    ]
    rows = [_person(3, "Jeff", "administrator"), _person(4, "Ann", "administrator")]
    plan = dict((row.title, problem) for row, problem in role_plan(_ADMIN, rows, "editor", users))
    assert "own Administrator" in plan["Jeff"] and plan["Ann"] == ""
    other = Account(9, "Root", "root", ("administrator",), frozenset())
    plan = dict((r.title, p) for r, p in role_plan(other, rows, "editor", users))
    assert plan["Jeff"] == "" and "only Administrator" in plan["Ann"]  # checked in turn


def test_bulk_remove_keeps_you_and_the_one_who_gets_the_posts() -> None:
    users = [{"id": 3, "roles": ["administrator"]}, {"id": 4, "roles": ["author"]}]
    rows = [_person(3, "Jeff", "administrator"), _person(4, "Ann", "author")]
    plan = dict((r.title, p) for r, p in remove_plan(_ADMIN, rows, 4, users))
    assert "own account" in plan["Jeff"] and "receive the posts" in plan["Ann"]


def test_add_new_body_validates_and_never_needs_a_typed_password() -> None:
    body = new_user_body({"username": "cara", "email": "cara@example.org", "roles": "author"})
    assert body["roles"] == ["author"] and len(body["password"]) == 24
    assert "sends no email" in new_user_preview(body, "Radio")
    with pytest.raises(EditRefused):
        new_user_body({"username": "", "email": "x@example.org"})
    with pytest.raises(EditRefused):
        new_user_body({"username": "cara", "email": "nope"})
    assert {f.key for f in NEW_USER_SHEET.fields()} >= {
        "username",
        "email",
        "url",
        "locale",
        "roles",
    }


def test_a_new_password_must_be_long_and_unpadded() -> None:
    assert password_problem("")
    assert password_problem("short")
    assert password_problem(" padded password ")
    assert password_problem("correct horse battery") == ""
