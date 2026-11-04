"""Abilities, Ask the Site, and Site Check with every Site Health test (9.15)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import abilities as ab
from quill.ui.wordpress_abilities_commands import WordPressAbilitiesCommands

API = "/wp-json/wp/v2"
ABL = "/wp-json/wp-abilities/v1"
HEALTH = "/wp-json/wp-site-health/v1/tests"

ADMIN = {
    "id": 1,
    "name": "Jeff",
    "roles": ["administrator"],
    "capabilities": {"manage_options": True, "edit_posts": True},
}

ABILITIES = [
    {
        "name": "core/get-site-info",
        "label": "Get Site Info",
        "description": "The site's name and address.",
        "meta": {"annotations": {"readonly": True}},
    },
    {
        "name": "radio/add-show",
        "label": "Add a Show",
        "description": "Adds a show to the schedule.",
        "input_schema": {"properties": {"title": {"type": "string"}}},
    },
]


@pytest.fixture
def site(wp: Any) -> Any:
    if not issubclass(type(wp), WordPressAbilitiesCommands):
        wp.__class__ = type("Wired", (type(wp), WordPressAbilitiesCommands), {})
    return wp


def _index(wp_site: Any, namespaces: list[str]) -> None:
    wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2", *namespaces], "routes": {}})
    wp_site.on("GET", f"{API}/users/me", ADMIN)


class FakeService:
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.prompts: list[str] = []

    def converse(self, prompt: str, _image: Any, _history: Any, **kwargs: Any) -> None:
        self.prompts.append(prompt)
        kwargs["on_done"](self.replies.pop(0), None, None)


class FakeAi:
    def __init__(self, service: FakeService) -> None:
        self.service = service

    def _ai_ready(self) -> bool:
        return True

    def _ai_service(self) -> FakeService:
        return self.service


def _ai(site: Any, *replies: str) -> FakeService:
    service = FakeService(list(replies))
    site.host.ai_editor = lambda: FakeAi(service)
    return service


# --------------------------------------------------------------------------- #
# Abilities


def test_abilities_without_the_namespace_say_why(site, wp_site, wp_dialogs):
    _index(wp_site, [])
    site.cmd_abilities()
    assert "offers no abilities for AI. That needs WordPress 6.9" in site.host.said


def test_every_ability_is_listed_off_until_turned_on(site, wp_site, wp_dialogs):
    _index(wp_site, ["wp-abilities/v1"])
    wp_site.on("GET", f"{ABL}/abilities", ABILITIES)
    site.cmd_abilities()
    rows = wp_dialogs.window["rows"]
    assert rows == [
        "Add a Show, off, can change the site: Adds a show to the schedule.",
        "Get Site Info, off, changes nothing: The site's name and address.",
    ]
    assert "Takes: title" in wp_dialogs.window["details"](0)
    rows = wp_dialogs.press("&Turn On or Off", 1)
    assert rows[1].startswith("Get Site Info, on")
    assert "Get Site Info is on." in site.host.said
    assert ab.AbilityChoices(site.local.root, "radio").on() == {"core/get-site-info"}


def test_turning_on_an_ability_that_changes_the_site_is_confirmed(site, wp_site, wp_dialogs):
    _index(wp_site, ["wp-abilities/v1"])
    wp_site.on("GET", f"{ABL}/abilities", ABILITIES)
    site.cmd_abilities()
    assert wp_dialogs.press("&Turn On or Off", 0) is None
    assert ab.AbilityChoices(site.local.root, "radio").on() == set()
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Turn On or Off", 0)
    assert ab.AbilityChoices(site.local.root, "radio").on() == {"radio/add-show"}
    wp_dialogs.press("&Turn On or Off", 0)
    assert "Add a Show is off." in site.host.said


def test_a_site_listing_no_abilities_says_so(site, wp_site, wp_dialogs):
    _index(wp_site, ["wp-abilities/v1"])
    wp_site.on("GET", f"{ABL}/abilities", [])
    site.cmd_abilities()
    assert "lists no abilities" in site.host.said


# --------------------------------------------------------------------------- #
# Ask the Site


def _ready(site: Any, wp_site: Any, *on: str) -> None:
    _index(wp_site, ["wp-abilities/v1"])
    wp_site.on("GET", f"{ABL}/abilities", ABILITIES)
    choices = ab.AbilityChoices(site.local.root, "radio")
    for name in on:
        choices.set(name, True)


def test_ask_the_site_needs_an_ability_turned_on(site, wp_site, wp_dialogs):
    _ready(site, wp_site)
    site.cmd_ask_site()
    assert "No ability of Community Radio is turned on" in site.host.said


def test_ask_the_site_without_ai_here_says_so(site, wp_site, wp_dialogs):
    _ready(site, wp_site, "core/get-site-info")
    site.cmd_ask_site()
    assert "AI help is not available in this window." in site.host.said


def test_a_plain_answer_says_no_ability_was_used(site, wp_site, wp_dialogs):
    _ready(site, wp_site, "core/get-site-info")
    service = _ai(site, "It is a radio station.")
    wp_dialogs.answer("ask_text", "What is this site?")
    site.cmd_ask_site()
    assert "core/get-site-info" in service.prompts[0]
    assert "radio/add-show" not in service.prompts[0]
    assert wp_dialogs.reports[-1]["text"] == (
        "It is a radio station.\n\nNo ability of Community Radio was used."
    )


def test_an_ability_runs_only_after_a_yes_and_is_shown_in_the_answer(site, wp_site, wp_dialogs):
    _ready(site, wp_site, "core/get-site-info")
    wp_site.on("GET", f"{ABL}/abilities/core/get-site-info/run", {"name": "Community Radio"})
    service = _ai(site, "RUN core/get-site-info {}", "It is called Community Radio.")
    wp_dialogs.answer("ask_text", "What is it called?").answer("confirm", True)
    site.cmd_ask_site()
    assert (
        "run Get Site Info (core/get-site-info) on Community Radio, given nothing"
        in (wp_dialogs.asked("confirm")[0]["message"])
    )
    assert '{"name": "Community Radio"}' in service.prompts[1]
    text = wp_dialogs.reports[-1]["text"]
    assert text.endswith(
        "Used on Community Radio: Get Site Info (core/get-site-info), given nothing."
    )


def test_a_write_ability_is_posted_with_its_input(site, wp_site, wp_dialogs):
    _ready(site, wp_site, "radio/add-show")
    wp_site.on("POST", f"{ABL}/abilities/radio/add-show/run", {"id": 5})
    _ai(site, 'RUN radio/add-show {"title": "Jazz"}', "Added.")
    wp_dialogs.answer("ask_text", "Add Jazz").answer("confirm", True)
    site.cmd_ask_site()
    body = wp_site.body(wp_site.sent("POST", f"{ABL}/abilities/radio/add-show/run")[0])
    assert body == {"input": {"title": "Jazz"}}
    assert "It can change the site." in wp_dialogs.asked("confirm")[0]["message"]


def test_declining_the_run_runs_nothing(site, wp_site, wp_dialogs):
    _ready(site, wp_site, "radio/add-show")
    _ai(site, 'RUN radio/add-show {"title": "Jazz"}')
    wp_dialogs.answer("ask_text", "Add Jazz")
    site.cmd_ask_site()
    assert not wp_site.sent("POST", f"{ABL}/abilities/radio/add-show/run")
    assert "Nothing was run on Community Radio." in site.host.said


def test_an_ability_that_is_off_is_never_run(site, wp_site, wp_dialogs):
    _ready(site, wp_site, "core/get-site-info")
    _ai(site, 'RUN radio/add-show {"title": "Jazz"}')
    wp_dialogs.answer("ask_text", "Add Jazz")
    site.cmd_ask_site()
    assert not wp_dialogs.asked("confirm")
    assert "No ability of Community Radio was used." in wp_dialogs.reports[-1]["text"]


# --------------------------------------------------------------------------- #
# Site Check, every test


def test_site_check_runs_every_test_the_index_lists_and_explains_the_header(
    wp, wp_site, wp_dialogs
):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp_site.on(
        "GET",
        "/wp-json/",
        {
            "home": "https://radio.example",
            "namespaces": ["wp/v2", "wp-site-health/v1", "tribe/events/v1"],
            "routes": {
                "/wp-site-health/v1/tests/page-cache": {},
                "/wp-site-health/v1/tests/authorization-header": {},
                "/wp-site-health/v1/directory-sizes": {},
            },
        },
    )
    wp_site.on("GET", f"{HEALTH}/page-cache", {"label": "Page cache is enabled", "status": "good"})
    wp_site.on(
        "GET",
        f"{HEALTH}/authorization-header",
        {"label": "The authorization header is missing", "status": "recommended"},
    )
    wp.cmd_site_check()
    text = wp_dialogs.reports[-1]["text"]
    assert "Recommended: The authorization header is missing." in text
    assert "application passwords cannot work" in text
    assert "Good: Page cache is enabled." in text
    assert "The Events Calendar: recognised." in text
    assert not wp_site.sent("GET", f"{HEALTH}/https-status")


def test_site_check_says_when_a_test_could_not_run(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp_site.on(
        "GET",
        "/wp-json/",
        {
            "namespaces": ["wp-site-health/v1"],
            "routes": {"/wp-site-health/v1/tests/loopback-requests": {}},
        },
    )
    wp.cmd_site_check()
    assert "Loopback requests: the site could not run this test." in wp_dialogs.reports[-1]["text"]


def test_site_check_without_health_checks_says_so_and_only_reads(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp_site.on("GET", "/wp-json/", {"namespaces": []})
    wp.cmd_site_check()
    assert "does not offer its health checks" in wp_dialogs.reports[-1]["text"]
    assert all(r.get_method() == "GET" for r in wp_site.requests)
