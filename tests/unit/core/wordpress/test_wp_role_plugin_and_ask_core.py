"""Roles through a role plugin, who has never signed in, and Ask About This Site (15.11)."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress import role_plugin as rp
from quill.core.wordpress import site_ask as sa
from quill.core.wordpress.api import WordPressApiError


class Api:
    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, str, Any]] = []
        self.params: list[dict[str, Any]] = []
        self.refuse: set[str] = set()

    def get(self, route: str, **_params: Any) -> Any:
        return self.answers.get(route)

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        self.params.append(dict(params or {}))
        if route in self.refuse:
            raise WordPressApiError("Sorry, you are not allowed to do that.", status=403)
        yield from self.answers.get(route, [])

    def post(self, route: str, body: Any = None, **_kw: Any) -> Any:
        self.sent.append(("POST", route, body))
        return body

    def delete(self, route: str, **kw: Any) -> Any:
        self.sent.append(("DELETE", route, kw))
        return {}


# -- roles ---------------------------------------------------------------------------


def test_the_role_plugin_is_found_only_by_its_namespace() -> None:
    assert rp.role_namespace(["wp/v2", "members/v1"]) == "members/v1"
    assert rp.role_namespace(["wp/v2", "/members/v1/"]) == "members/v1"
    assert rp.role_namespace(["wp/v2"]) == ""


def test_roles_read_from_a_list_or_an_object_keyed_by_slug() -> None:
    listed = Api({
        "members/v1/roles": [
            {"slug": "editor", "name": "Editor", "capabilities": {"edit_posts": True, "x": False}},
            {"slug": "volunteer", "label": "Volunteer", "capabilities": ["read"]},
        ]
    })
    roles = rp.read_roles(listed, "members/v1")
    assert [(r.slug, r.name, set(r.capabilities)) for r in roles] == [
        ("editor", "Editor", {"edit_posts"}),
        ("volunteer", "Volunteer", {"read"}),
    ]
    assert roles[1].line == "Volunteer (volunteer): 1 capability"
    keyed = Api({"members/v1/roles": {"author": {"name": "Author", "capabilities": {"read": 1}}}})
    assert rp.read_roles(keyed, "members/v1")[0].slug == "author"


def test_a_capability_change_is_planned_sent_whole_and_put_back() -> None:
    role = rp.SiteRole("editor", "Editor", frozenset({"read", "edit_posts"}))
    plan = rp.plan_capabilities(role, ["upload_files", "read"], ["edit_posts", "fly"])
    assert plan.added == ["upload_files"] and plan.removed == ["edit_posts"]
    assert plan.unknown == ["fly"]
    assert plan.after == ["read", "upload_files"] and plan.before == ["edit_posts", "read"]
    assert plan.lines() == [
        "Editor may now also: upload_files",
        "Editor may no longer: edit_posts",
        "Left alone, Editor never had it: fly",
    ]
    api = Api({})
    rp.save_capabilities(api, "members/v1", "editor", plan.after)
    assert api.sent[-1] == (
        "POST",
        "members/v1/roles/editor",
        {"capabilities": {"read": True, "upload_files": True}},
    )


def test_a_new_role_needs_a_free_well_formed_slug_and_is_taken_away_on_undo() -> None:
    assert rp.valid_slug("volunteer", ["editor"]) == ""
    assert "already has" in rp.valid_slug("editor", ["editor"])
    assert "lower-case" in rp.valid_slug("Bad Slug", [])
    assert rp.parse_capabilities("read,\nedit_posts\nNot A Cap\n\nread") == (
        ["read", "edit_posts"],
        ["Not A Cap"],
    )
    api = Api({})
    rp.create_role(api, "members/v1", "volunteer", "Volunteer", ["read"])
    rp.delete_role(api, "members/v1", "volunteer")
    assert api.sent == [
        (
            "POST",
            "members/v1/roles",
            {"slug": "volunteer", "name": "Volunteer", "capabilities": {"read": True}},
        ),
        ("DELETE", "members/v1/roles/volunteer", {}),
    ]


# -- who has never signed in ---------------------------------------------------------


def test_never_signed_in_lists_people_with_no_time_where_the_site_gives_one() -> None:
    users = [
        {"id": 1, "name": "Jeff", "meta": {"last_login": "2026-11-01T10:00:00"}},
        {"id": 2, "name": "Ann", "meta": {"last_login": ""}},
        {"id": 3, "name": "Bob", "meta": {}},
    ]
    assert rp.never_signed_in(users) == ("meta.last_login", ["Ann", "Bob"])
    top = [{"name": "Sam", "wfls_last_login": 0}, {"name": "Kim", "wfls_last_login": 1730000000}]
    assert rp.never_signed_in(top) == ("wfls_last_login", ["Sam"])


def test_a_site_with_no_sign_in_times_says_so_rather_than_calling_everyone_new() -> None:
    assert rp.never_signed_in([{"name": "Jeff"}, {"name": "Ann", "meta": {}}]) == ("", [])
    assert "does not give sign-in times over REST" in rp.NO_SIGN_IN_TIMES
    assert "last_login" in rp.NO_SIGN_IN_TIMES


# -- Ask About This Site -------------------------------------------------------------


def _post(ident: int, title: str, text: str, status: str = "publish", when: str = "") -> dict:
    return {
        "id": ident,
        "type": "post",
        "title": {"rendered": title},
        "status": status,
        "link": f"https://radio.example/?p={ident}",
        "modified": when or f"2026-11-0{ident}T00:00:00",
        "content": {"rendered": f"<p>{text}</p>"},
    }


def test_only_published_content_is_read_unless_private_is_chosen() -> None:
    api = Api({"wp/v2/posts": [_post(1, "Hello", "Our address is 1 Main St.")]})
    items, unread = sa.read_content(api, include_private=False)
    assert [i["id"] for i in items] == [1] and unread == []
    assert api.params[0]["status"] == "publish" and "context" not in api.params[0]
    sa.read_content(api, include_private=True)
    assert "private" in api.params[-1]["status"] and api.params[-1]["context"] == "edit"


def test_a_list_the_site_refuses_is_named_not_passed_off_as_empty() -> None:
    api = Api({"wp/v2/posts": [_post(1, "Hello", "Hi")]})
    api.refuse.add("wp/v2/pages")
    items, unread = sa.read_content(api, include_private=False)
    assert len(items) == 1 and unread[0].startswith("wp/v2/pages: ")


def test_the_digest_is_plain_text_titled_and_capped_and_the_prompt_is_grounded() -> None:
    items = [
        _post(2, "Schedule", "Jazz on Fridays. " * 300),
        _post(1, "Draft idea", "Secret plan", status="draft"),
        _post(3, "Too much", "x " * 800),
    ]
    digest = sa.content_digest(items, max_chars=3000, per_item=2000)
    assert digest.included == 2 and digest.left_out == 1 and digest.private == 1
    assert "<p>" not in digest.text and "(cut short)" in digest.text
    assert "## Schedule (post, publish, https://radio.example/?p=2)" in digest.text
    prompt = sa.ask_prompt("Community Radio", "When is jazz on?", digest)
    assert "Question: When is jazz on?" in prompt
    assert "using only the site content below" in prompt
    assert "1 more items were not included" in prompt


def test_the_consent_names_the_site_the_count_the_ai_and_what_is_not_public() -> None:
    digest = sa.Digest("text", 3, 0, private=1, unread=["wp/v2/pages: refused"])
    said = sa.consent_message("Community Radio", "the AI you chose", digest)
    assert said.startswith(
        "Send the text of 3 posts and pages from Community Radio with your question to the AI"
    )
    assert "1 of them are not public" in said and "Not read: wp/v2/pages: refused." in said
    public = sa.consent_message("Community Radio", "X", sa.Digest("t", 2, 0))
    assert "Only published content is included." in public
