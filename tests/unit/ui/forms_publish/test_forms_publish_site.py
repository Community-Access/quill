"""Publish Form, Insert Form Into Page, Test on Site and the new-responses count (17a.7, 17a.8)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QAF = "/wp-json/qaf/v1"


def _created(make_form: Any, **changes: Any) -> Any:
    def answer(request: Any, _query: Any) -> Any:
        body = json.loads(request.data)
        return make_form(12, title=body["title"], status=body["status"], **changes)

    return answer


# --------------------------------------------------------------------------- #
# Publish Form


def test_publish_creates_the_form_after_naming_the_site(
    fp, pub_site, pub_dialogs, pub_host, make_form
):
    pub_site.on("POST", f"{QAF}/forms", _created(make_form))
    pub_dialogs.answer("ask_choice", 0).answer("confirm", True)

    fp.cmd_publish_form()

    assert "Community Radio" in pub_dialogs.asked("confirm")[0]["message"]
    body = pub_site.body(pub_site.sent("POST", f"{QAF}/forms")[0])
    assert body["status"] == "active"
    assert body["model"]["title"] == "Spring fair"
    assert body["config"]["form_model"] == body["model"]
    assert body["bfl_source"].startswith("bfl 1")
    assert "Published Spring fair on Community Radio, form 12, live." in pub_host.said
    link = fp.published().link_for(pub_host.path)
    assert (link.site_id, link.form_id) == ("radio", 12)


def test_publish_prefers_qaf_v1_when_the_site_still_lists_baf_v1(
    fp, pub_site, pub_dialogs, make_form
):
    """QAF keeps baf/v1 for reading only (17a.17): every write goes to qaf/v1."""
    pub_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2", "baf/v1", "qaf/v1"], "routes": {}})
    pub_site.on("POST", f"{QAF}/forms", _created(make_form))
    pub_dialogs.answer("ask_choice", 0).answer("confirm", True)

    fp.cmd_publish_form()

    assert len(pub_site.sent("POST", f"{QAF}/forms")) == 1
    assert not [r for r in pub_site.requests if "/baf/v1/" in r.full_url]


def test_a_site_still_running_baf_is_published_to_on_baf_v1(
    fp, pub_site, pub_dialogs, pub_host, make_form, tmp_path
):
    baf = "/wp-json/baf/v1"
    pub_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2", "baf/v1"], "routes": {}})
    pub_site.on("POST", f"{baf}/forms", _created(make_form))
    pub_dialogs.answer("ask_choice", 0).answer("confirm", True)

    fp.cmd_publish_form()

    assert len(pub_site.sent("POST", f"{baf}/forms")) == 1
    assert "Published Spring fair on Community Radio, form 12, live." in pub_host.said

    _wordpress_page(tmp_path, pub_host, "markdown")
    pub_site.on("GET", f"{baf}/forms", [make_form(12)])
    pub_dialogs.answer("ask_choice", 0)

    fp.cmd_insert_into_page()

    assert '[baf_form id="12"]' in pub_host.text


def test_publish_cancelled_at_the_confirmation_sends_nothing(fp, pub_site, pub_dialogs):
    pub_dialogs.answer("ask_choice", 1)

    fp.cmd_publish_form()

    assert not pub_site.sent("POST", f"{QAF}/forms")


def test_publish_on_a_site_without_qaf_says_so(fp, pub_site, pub_host, pub_dialogs):
    pub_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"], "routes": {}})

    fp.cmd_publish_form()

    assert "needs QUILL Accessible Forms on Community Radio" in pub_host.said
    assert not pub_dialogs.asked("confirm")


def test_publish_refuses_a_form_with_problems(fp, pub_host, pub_site):
    pub_host.text = 'bfl 1\nform "Broken"\n\ntext #a "A"\ntext #a "Again"\n'

    fp.cmd_publish_form()

    assert "stopped: this form has" in pub_host.said
    assert not pub_site.requests


def test_publish_outside_a_form_says_where_it_works(fp, pub_host, tmp_path):
    pub_host.path = tmp_path / "notes.txt"

    fp.cmd_publish_form()

    assert "works in a form document" in pub_host.said


def test_publish_is_off_in_safe_mode(fp, pub_host, pub_site):
    pub_host.ai._safe_mode = True

    fp.cmd_publish_form()

    assert "off in Safe Mode" in pub_host.said
    assert not pub_site.requests


def test_publish_with_no_site_connected_says_so(fp, pub_host, tmp_path):
    from quill.core.wordpress import sites as st

    st.save_sites(st.SiteStore(), tmp_path)

    fp.cmd_publish_form()

    assert "Connect a WordPress site first" in pub_host.said


def test_update_keeps_the_sites_config_and_its_previous_version(
    fp, pub_site, pub_dialogs, pub_host, make_form
):
    from quill.core.forms import published as pub

    fp.published().set_link(
        pub_host.path, pub.Link("radio", 12, "Spring fair", "2026-11-03 14:10:00")
    )
    pub_site.on("GET", f"{QAF}/forms/12", make_form(12))
    pub_site.on("POST", f"{QAF}/forms/12", _created(make_form, updated_at="2026-11-04 09:00:00"))
    pub_dialogs.answer("confirm", True)

    fp.cmd_publish_form()

    assert pub_dialogs.asked("confirm")[0]["yes_label"] == "Update"
    body = pub_site.body(pub_site.sent("POST", f"{QAF}/forms/12")[0])
    assert body["config"]["fields"] == [{"id": "old", "label": "Old"}]
    assert body["status"] == "active"
    assert "Updated Spring fair on Community Radio" in pub_host.said
    assert fp.published().versions("radio", 12)
    assert fp.published().link_for(pub_host.path).updated_at == "2026-11-04 09:00:00"


def test_update_over_a_change_on_the_site_warns_first(
    fp, pub_site, pub_dialogs, pub_host, make_form
):
    from quill.core.forms import published as pub

    fp.published().set_link(
        pub_host.path, pub.Link("radio", 12, "Spring fair", "2026-11-01 08:00:00")
    )
    pub_site.on("GET", f"{QAF}/forms/12", make_form(12))

    fp.cmd_publish_form()

    asked = pub_dialogs.asked("confirm")[0]
    assert "after you last published it" in asked["message"]
    assert asked["yes_label"] == "Publish Over It"
    assert not pub_site.sent("POST", f"{QAF}/forms/12")


def test_publish_failure_is_one_plain_sentence(fp, pub_site, pub_dialogs, pub_host):
    from urllib.error import URLError

    pub_site.on("POST", f"{QAF}/forms", URLError("down"))
    pub_dialogs.answer("ask_choice", 0).answer("confirm", True)

    fp.cmd_publish_form()

    assert pub_host.announced[-1].endswith(".")
    assert fp.published().link_for(pub_host.path) is None


# --------------------------------------------------------------------------- #
# Insert Form Into Page


def _wordpress_page(tmp_path: Path, pub_host: Any, text_format: str) -> None:
    from quill.core.wordpress import local as lc

    store = lc.LocalStore(tmp_path)
    copy = lc.WorkingCopy("radio", "page", lc.new_local_id(), 40, "About", "Intro\n", text_format)
    path = store.write_document(copy)
    pub_host.path = Path(path)
    pub_host.text = "Intro\n"
    pub_host.caret = len("Intro\n")


def test_insert_puts_the_block_in_a_block_page(
    fp, pub_site, pub_dialogs, pub_host, make_form, tmp_path
):
    _wordpress_page(tmp_path, pub_host, "html")
    pub_site.on("GET", f"{QAF}/forms", [make_form(12), make_form(14, title="Survey")])
    pub_dialogs.answer("ask_choice", 1)

    fp.cmd_insert_into_page()

    assert '<!-- wp:qaf/form {"formId":14} /-->' in pub_host.text
    assert "Inserted the Survey form, as a block." in pub_host.said


def test_insert_puts_a_shortcode_in_a_markdown_page(
    fp, pub_site, pub_dialogs, pub_host, make_form, tmp_path
):
    _wordpress_page(tmp_path, pub_host, "markdown")
    pub_site.on("GET", f"{QAF}/forms", [make_form(12, status="draft")])
    pub_dialogs.answer("ask_choice", 0)

    fp.cmd_insert_into_page()

    assert '[qaf_form id="12"]' in pub_host.text
    assert "It is a draft" in pub_host.said


def test_insert_outside_a_wordpress_page_says_where_it_works(fp, pub_host):
    fp.cmd_insert_into_page()

    assert "works in a WordPress page or post" in pub_host.said


def test_insert_cancelled_changes_nothing(fp, pub_site, pub_host, make_form, tmp_path):
    _wordpress_page(tmp_path, pub_host, "html")
    pub_site.on("GET", f"{QAF}/forms", [make_form(12)])

    fp.cmd_insert_into_page()

    assert pub_host.text == "Intro\n"


# --------------------------------------------------------------------------- #
# Test on Site


def test_test_on_site_opens_the_page_that_shows_the_form(fp, pub_site, pub_host, make_form):
    from quill.core.forms import published as pub

    fp.published().set_link(pub_host.path, pub.Link("radio", 12, "Spring fair"))
    pub_site.on("GET", f"{QAF}/forms/12", make_form(12))
    page = {
        "id": 5,
        "link": "https://radio.example/fair/",
        "status": "publish",
        "title": {"raw": "Fair"},
        "content": {"raw": '<!-- wp:baf/form {"formId":12} /-->'},
    }
    pub_site.on("GET", "/wp-json/wp/v2/pages", [page])
    pub_site.on("GET", "/wp-json/wp/v2/posts", [])

    fp.cmd_test_on_site()

    assert pub_host.browsed == ["https://radio.example/fair/"]
    assert "Opened Fair on Community Radio" in pub_host.said


def test_test_on_site_with_no_page_opens_qaf_itself(fp, pub_site, pub_host, make_form):
    from quill.core.forms import published as pub

    fp.published().set_link(pub_host.path, pub.Link("radio", 12, "Spring fair"))
    pub_site.on("GET", f"{QAF}/forms/12", make_form(12))
    pub_site.on("GET", "/wp-json/wp/v2/pages", [])
    pub_site.on("GET", "/wp-json/wp/v2/posts", [])

    fp.cmd_test_on_site()

    assert pub_host.browsed[0].startswith("https://radio.example/wp-admin/admin.php?")
    assert "form_id=12" in pub_host.browsed[0]
    assert "No page on Community Radio shows Spring fair" in pub_host.said


def test_test_on_site_before_publishing_says_publish_first(fp, pub_host, pub_site):
    fp.cmd_test_on_site()

    assert "not on a site yet" in pub_host.said
    assert not pub_site.requests


# --------------------------------------------------------------------------- #
# the new-responses count, once per site per session


def test_new_responses_are_said_once_a_session(fp, pub_site, pub_host, make_form, profile_factory):
    fp.profile = profile_factory(announce_new_responses=True)
    fp.published().mark_seen("radio", 12, 1)
    pub_site.on(
        "GET",
        f"{QAF}/forms",
        [make_form(12, entry_count=5), make_form(14, title="Survey", entry_count=0)],
    )

    fp.site_api(fp.profile)
    fp.site_api(fp.profile)

    said = [s for s in pub_host.announced if "new response" in s]
    assert said == ["Community Radio: 4 new responses to Spring fair."]


def test_new_responses_count_respects_the_site_setting(fp, pub_site, pub_host, make_form):
    pub_site.on("GET", f"{QAF}/forms", [make_form(12, entry_count=5)])

    fp.site_api(fp.profile)

    assert not pub_site.sent("GET", f"{QAF}/forms")


def test_new_responses_count_is_silent_on_a_site_without_qaf(
    fp, pub_site, pub_host, profile_factory
):
    fp.profile = profile_factory(announce_new_responses=True)
    pub_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"]})

    fp.site_api(fp.profile)

    assert not pub_host.announced
    assert not pub_site.sent("GET", f"{QAF}/forms")


def test_wordpress_commands_say_the_count_too(
    tmp_path, pub_host, pub_site, make_form, profile_factory
):
    from quill.ui import forms_site_base as base
    from quill.ui.wordpress_commands import WordPressCommands

    base.forget_told()
    profile = profile_factory(announce_new_responses=True)
    pub_site.on("GET", f"{QAF}/forms", [make_form(12, entry_count=1)])
    commands = WordPressCommands(pub_host, data_dir=tmp_path, opener=pub_site)

    commands.api(profile)

    assert "Community Radio: 1 new response to Spring fair." in pub_host.said
    base.forget_told()
