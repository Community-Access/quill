"""Running the Site: Users, Application Passwords and Sign Out This Site."""

from __future__ import annotations

from quill.core.wordpress import sites as st

API = "/wp-json/wp/v2"

ADMIN = {
    "id": 1,
    "name": "Jeff",
    "roles": ["administrator"],
    "capabilities": {
        "list_users": True,
        "create_users": True,
        "edit_users": True,
        "delete_users": True,
        "promote_users": True,
    },
}
EDITOR = {"id": 3, "name": "Eve", "roles": ["editor"], "capabilities": {"list_users": True}}
AUTHOR = {"id": 9, "name": "Ann", "roles": ["author"], "capabilities": {"edit_posts": True}}

USERS = [
    {
        "id": 1,
        "name": "Jeff",
        "username": "jeff",
        "email": "jeff@radio.example",
        "roles": ["administrator"],
    },
    {"id": 9, "name": "Ann", "username": "ann", "email": "ann@radio.example", "roles": ["author"]},
]


def _site(wp_site, account=ADMIN):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on("GET", f"{API}/users", USERS)


def test_users_list_and_role_aware_buttons(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp.cmd_users()
    assert wp_dialogs.window["rows"] == [
        "Jeff, jeff, Administrator, jeff@radio.example, you",
        "Ann, ann, Author, ann@radio.example",
    ]
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert labels == [
        "&Add User...",
        "&Edit...",
        "Change &Role...",
        "De&lete...",
        "Application &Passwords...",
        "&My Profile...",
    ]


def test_an_editor_sees_users_but_no_buttons_it_would_be_refused(wp, wp_site, wp_dialogs):
    _site(wp_site, account=EDITOR)
    wp.cmd_users()
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert labels == ["&My Profile..."]


def test_an_author_is_told_and_offered_their_profile(wp, wp_site, wp_dialogs):
    _site(wp_site, account=AUTHOR)
    wp_site.on("POST", f"{API}/users/me", {"id": 9, "name": "Ann B"})
    wp_dialogs.answer("ask_text", "Ann B", "", "")
    wp.cmd_users()
    assert wp.host.announced[0].startswith(
        "Your account on Community Radio is an Author, which cannot manage users."
    )
    assert wp_site.body(wp_site.sent("POST", f"{API}/users/me")[0]) == {"name": "Ann B"}
    assert wp.host.announced[-1] == "Your profile on Community Radio is saved."


def test_my_profile_cancel_or_no_change_sends_nothing(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp.cmd_users()
    wp_dialogs.press("My Profile...", None)
    wp_dialogs.answer("ask_text", "Jeff", "", "")
    wp_dialogs.press("My Profile...", None)
    assert wp_site.sent("POST", f"{API}/users/me") == []


def test_add_user_never_shows_the_password(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp_site.on(
        "POST",
        f"{API}/users",
        {"id": 12, "name": "Bo", "username": "bo", "email": "bo@x.example", "roles": ["editor"]},
    )
    wp.cmd_users()
    wp_dialogs.answer("ask_text", "bo", "bo@x.example", "Bo").answer("ask_choice", 3)
    wp_dialogs.press("Add User...", None)  # cancelled at the confirmation
    assert wp_site.sent("POST", f"{API}/users") == []
    wp_dialogs.answer("ask_text", "bo", "bo@x.example", "Bo").answer("ask_choice", 3)
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("Add User...", None)
    body = wp_site.body(wp_site.sent("POST", f"{API}/users")[0])
    assert body["username"] == "bo" and body["roles"] == ["editor"]
    assert len(body["password"]) == 24
    assert body["password"] not in wp.host.said
    assert wp.host.announced[-1].startswith("Bo added to Community Radio as Editor.")


def test_edit_and_change_role(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp_site.on("POST", f"{API}/users/9", USERS[1])
    wp.cmd_users()
    wp_dialogs.answer("ask_text", "Ann Lee", "ann@radio.example")
    rows = wp_dialogs.press("Edit...", 1)
    assert wp_site.body(wp_site.sent("POST", f"{API}/users/9")[0]) == {"name": "Ann Lee"}
    assert rows[1].startswith("Ann Lee")
    wp_dialogs.answer("ask_choice", 3).answer("confirm", True)
    wp_dialogs.press("Change Role...", 1)
    assert wp_site.body(wp_site.sent("POST", f"{API}/users/9")[1]) == {"roles": ["editor"]}
    assert wp.host.announced[-1] == "Ann Lee is now Editor on Community Radio."
    assert wp_dialogs.press("Change Role...", 0) is None
    assert "your own role" in wp.host.announced[-1]


def test_delete_asks_who_gets_the_posts_and_refuses_yourself(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp_site.on("GET", f"{API}/posts", [{"id": 1}, {"id": 2}])
    wp_site.on("DELETE", f"{API}/users/9", {"deleted": True})
    wp.cmd_users()
    assert wp_dialogs.press("Delete...", 0) is None
    assert "your own account" in wp.host.announced[-1]
    wp_dialogs.answer("ask_choice", 0).answer("confirm", True)
    wp_dialogs.press("Delete...", 1)
    assert "Their 2 posts move to Jeff" in wp_dialogs.asked("confirm")[-1]["message"]
    request = wp_site.sent("DELETE", f"{API}/users/9")[0]
    assert "reassign=1" in request.full_url and "force=true" in request.full_url
    assert wp.host.announced[-1] == "Ann deleted; their posts are now Jeff's."


def test_users_passwords_button_lists_that_persons_passwords(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp_site.on("GET", f"{API}/users/me/application-passwords/introspect", {"uuid": "mine"})
    wp_site.on(
        "GET",
        f"{API}/users/9/application-passwords",
        [{"uuid": "u9", "name": "Phone", "created": "2026-01-01T10:00:00", "last_used": None}],
    )
    wp.cmd_users()
    wp_dialogs.press("Application Passwords...", 1)
    assert wp_dialogs.window["rows"] == ["Ann: Phone, made 1 January 2026, 10:00 AM, never used"]


# --------------------------------------------------------------------------- #
# Application Passwords


def _passwords(wp_site, account=ADMIN):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on("GET", f"{API}/users", USERS)
    wp_site.on("GET", f"{API}/users/me/application-passwords/introspect", {"uuid": "q1"})
    wp_site.on(
        "GET",
        f"{API}/users/me/application-passwords",
        [
            {
                "uuid": "q1",
                "name": "QUILL",
                "created": "2026-11-01T10:00:00",
                "last_used": "2026-11-04T09:00:00",
            },
            {"uuid": "o1", "name": "Old laptop", "created": "2025-01-01T10:00:00"},
        ],
    )
    wp_site.on("GET", f"{API}/users/9/application-passwords", [])


def test_app_passwords_mark_this_computers_and_revoke_others(wp, wp_site, wp_dialogs):
    _passwords(wp_site)
    wp_site.on("DELETE", f"{API}/users/me/application-passwords/o1", {"deleted": True})
    wp.cmd_app_passwords()
    rows = wp_dialogs.window["rows"]
    assert rows[0].startswith("Jeff: QUILL, this computer's QUILL")
    assert wp_dialogs.press("Revoke...", 0) is None
    assert "Sign Out This Site" in wp.host.announced[-1]
    wp_dialogs.press("Revoke...", 1)  # cancelled
    assert wp_site.sent("DELETE", f"{API}/users/me/application-passwords/o1") == []
    wp_dialogs.answer("confirm", True)
    assert len(wp_dialogs.press("Revoke...", 1)) == 1
    assert wp.host.announced[-1] == "Old laptop revoked on Community Radio."


def test_an_author_sees_only_their_own_passwords(wp, wp_site, wp_dialogs):
    _passwords(wp_site, account=AUTHOR)
    wp.cmd_app_passwords()
    assert len(wp_dialogs.window["rows"]) == 2
    assert wp_site.sent("GET", f"{API}/users") == []


# --------------------------------------------------------------------------- #
# Sign Out This Site


def test_sign_out_revokes_forgets_and_removes(wp, wp_site, wp_dialogs, monkeypatch):
    forgot = []
    monkeypatch.setattr(st, "forget_secret", forgot.append)
    wp_site.on("GET", f"{API}/users/me/application-passwords/introspect", {"uuid": "q1"})
    wp_site.on("DELETE", f"{API}/users/me/application-passwords/q1", {"deleted": True})
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_sign_out()
    assert len(wp_site.sent("DELETE", f"{API}/users/me/application-passwords/q1")) == 1
    assert forgot == ["radio"]
    assert wp.sites().sites == []
    assert wp.host.announced[-1] == (
        "Signed out of Community Radio: the password is revoked on the site and forgotten here, "
        "and the site is removed from QUILL."
    )


def test_sign_out_can_keep_the_site_and_explains_an_unknown_password(
    wp, wp_site, wp_dialogs, monkeypatch
):
    forgot = []
    monkeypatch.setattr(st, "forget_secret", forgot.append)
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_sign_out()  # no introspect route: an old WordPress
    assert forgot == ["radio"]
    assert wp.sites().get("radio") is not None
    assert "kept in your list" in wp.host.announced[-1]
    assert "did not say which password" in wp.host.announced[-1]


def test_sign_out_cancelled_does_nothing(wp, wp_site, wp_dialogs, monkeypatch):
    forgot = []
    monkeypatch.setattr(st, "forget_secret", forgot.append)
    wp.cmd_sign_out()
    assert forgot == [] and wp_site.requests == []
