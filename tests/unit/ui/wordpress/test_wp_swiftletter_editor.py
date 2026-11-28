"""SwiftLetter articles in the editor: open, save as a draft, refusals, compare and reopen.

The shared WordPress commands over the fake editor, a fake site answering with
SwiftLetter's contract fixtures, and scripted dialogs (``conftest.py``). What is
asserted is what reaches the person (``wp_host.announced``, the dialogs) and
what reaches the site (``wp_site.requests``), because "nothing retries" and
"never publishes" are both claims about requests that were not made.
"""

from __future__ import annotations

import io
import json
from typing import Any
from urllib.error import HTTPError

import pytest

from quill.core.wordpress import swiftletter_copy as sc
from tests.unit.core.wordpress.test_wp_swiftletter_contract import _SEED, _step

ARTICLE = "/wp-json/wp/v2/swl-articles/4"
SAVE = "/wp-json/swiftletter/v1/articles/4/save"
_CONTEXT = _step("article-context", "editor-opens-article")["response"]["example"]
_SAVED = _step("article-save", "save-current-version")
_V1 = _CONTEXT["swiftletter"]["edit_version"]
#: The save example, for an article whose title QUILL did not change (the fixture's save
#: also renames it, which is a change WordPress did not make and QUILL must not hide).
_STORED = {**_SAVED["response"]["example"], "title": _SEED["articles"]["garden"]["title"]}


def _refusal(scenario: str, step_id: str) -> HTTPError:
    response = _step(scenario, step_id)["response"]
    body = io.BytesIO(json.dumps(response["body"]).encode())
    return HTTPError("https://radio.example", response["status"], "Refused", {}, body)  # type: ignore[arg-type]


def _locked() -> HTTPError:
    body = {
        "code": "swiftletter_article_locked",
        "message": (
            "Pat Reyes is editing this article in WordPress. Your changes are still in QUILL."
        ),
        "data": {"status": 409},
    }
    return HTTPError(
        "https://radio.example",
        409,
        "Locked",
        {},
        io.BytesIO(json.dumps(body).encode()),  # type: ignore[arg-type]
    )


def _open(wp: Any, wp_site: Any, wp_dialogs: Any, *, fmt: int = 1, **kw: Any) -> None:
    wp_site.on("GET", ARTICLE, _CONTEXT)
    wp_dialogs.answer("ask_choice", fmt)
    wp.open_swiftletter(wp.profile, 4, **kw)


def _saves(wp_site: Any) -> list[Any]:
    return wp_site.sent("POST", SAVE)


# -- opening --------------------------------------------------------------------


def test_open_reads_the_edit_route_and_says_title_and_review_state(
    wp, wp_host, wp_site, wp_dialogs
):
    _open(wp, wp_site, wp_dialogs)
    request = wp_site.sent("GET", ARTICLE)[-1]
    assert request.full_url.endswith("?context=edit")
    title = _SEED["articles"]["garden"]["title"]
    assert wp_host.announced[-1] == (
        f"Opened {title} from SwiftLetter on Community Radio. Reviewed."
    )
    assert "## Planting day {#planting-day}" in wp_host.text
    assert wp_dialogs.asked("ask_choice")[0]["prompt"] == "Open &as:"
    assert not _saves(wp_site)  # opening never writes


def test_opening_again_opens_the_local_working_copy_not_the_site(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs)
    wp_host.text += "\nMy edit.\n"
    wp_host.save_current()
    wp.open_swiftletter(wp.profile, 4)
    assert len(wp_site.sent("GET", ARTICLE)) == 1
    assert "My edit." in wp_host.text
    assert wp_host.announced[-1].startswith("Opened your working copy of")
    assert "It was reviewed when you last opened or saved it" in wp_host.announced[-1]


def test_an_account_that_cannot_edit_opens_read_only_and_cannot_send(
    wp, wp_host, wp_site, wp_dialogs
):
    _open(wp, wp_site, wp_dialogs, can_edit=False)
    assert wp_host.announced[-1].endswith(
        "Your account cannot edit this article, so it opened read-only."
    )
    assert wp_host.extras["guarded"] == {wp_host.path: True}  # the editor's own guard
    wp.cmd_save_draft()
    assert "opened read-only, so QUILL did not send it" in wp_host.announced[-1]
    assert not _saves(wp_site)


def test_a_site_that_takes_no_saves_from_quill_opens_read_only(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs, can_save=False)
    assert "does not take saves from QUILL, so it opened read-only" in wp_host.announced[-1]
    assert wp_host.extras["guarded"] == {wp_host.path: True}


def test_an_editable_article_clears_any_old_guard(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs)
    assert wp_host.extras["guarded"] == {wp_host.path: False}


def test_a_permission_taken_away_since_guards_the_working_copy(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs)
    wp.open_swiftletter(wp.profile, 4, can_edit=False)
    assert wp_host.extras["guarded"][wp_host.path] is True
    wp.cmd_save_draft()
    assert not _saves(wp_site)


def test_cancelling_the_format_question_opens_nothing(wp, wp_host, wp_site, wp_dialogs):
    wp_site.on("GET", ARTICLE, _CONTEXT)
    wp.open_swiftletter(wp.profile, 4)  # unscripted: the dialog answers cancel
    assert wp_host.opened == [] and wp_host.announced == []


# -- saving -----------------------------------------------------------------------


def test_save_sends_title_and_content_with_if_match_and_keeps_the_persons_copy(
    wp, wp_host, wp_site, wp_dialogs
):
    _open(wp, wp_site, wp_dialogs, fmt=0)  # HTML, as the site has it
    wp_host.text = _SAVED["request"]["json"]["content"]
    mine = wp_host.text
    wp_site.on("POST", SAVE, _STORED)
    wp.cmd_save_draft()
    (request,) = _saves(wp_site)
    assert request.get_header("If-match") == _V1
    body = json.loads(request.data)
    assert set(body) == {"title", "content"} and body["content"] == mine
    said = wp_host.announced[-1]
    assert said.startswith("Draft saved to SwiftLetter on Community Radio. It is not published.")
    assert "Its review state is now Changed since review." in said
    assert "WordPress tidied the markup" in said  # kses: "/> became " />
    assert wp_host.text == mine  # the person's copy is never replaced
    # The next save describes the text the site now has.
    wp_host.text += "\n<!-- wp:paragraph -->\n<p>More.</p>\n<!-- /wp:paragraph -->"
    wp.cmd_save_draft()
    assert (
        _saves(wp_site)[-1].get_header("If-match") == _SAVED["response"]["example"]["edit_version"]
    )
    assert "tidied" not in wp_host.announced[-1]  # said once, not after every save
    assert "not published" not in wp_host.announced[-1]  # first save only


def test_a_markdown_save_sends_block_markup(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs)
    wp_host.text = wp_host.text.replace("forty raised beds", "forty-two raised beds")
    wp_site.on("POST", SAVE, _SAVED["response"]["example"])
    wp.cmd_save_draft()
    content = json.loads(_saves(wp_site)[-1].data)["content"]
    assert "<!-- wp:heading -->" in content and 'id="planting-day"' in content
    assert "forty-two raised beds" in content
    assert 'alt="Two volunteers lift a wooden raised bed' in content


def test_a_save_that_changes_nothing_sends_nothing(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs)
    wp.cmd_save_draft()
    assert not _saves(wp_site)
    assert wp_host.announced[-1].startswith("Nothing to save")


def test_markdown_that_cannot_be_kept_stops_the_save_and_keeps_the_draft(
    wp, wp_host, wp_site, wp_dialogs
):
    _open(wp, wp_site, wp_dialogs)
    wp_host.text += "\n::: block core/image island-99\n"
    draft = wp_host.text
    wp.cmd_save_draft()
    assert not _saves(wp_site)
    assert wp_host.announced[-1].startswith("Not saved to SwiftLetter")
    assert wp_host.text == draft and wp_host.path.read_text(encoding="utf-8") == draft


def test_publish_is_refused_and_never_reaches_the_site(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs)
    wp_host.text += "\nMore.\n"
    wp.cmd_publish()
    assert wp_host.announced[-1] == sc.NEVER_PUBLISHES
    assert [r.get_method() for r in wp_site.requests] == ["GET"]


def test_trash_is_left_to_swiftletter(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs)
    wp.cmd_trash()
    assert "moved to the Trash from SwiftLetter" in wp_host.announced[-1]
    assert [r.get_method() for r in wp_site.requests] == ["GET"]


def test_an_rc1_site_answering_only_id_and_version_still_saves(wp, wp_host, wp_site, wp_dialogs):
    _open(wp, wp_site, wp_dialogs, fmt=0)
    wp_host.text = _SAVED["request"]["json"]["content"]
    rc1 = _step("compat/article-save-1.1.0-rc.1", "save-current-version")
    wp_site.on("POST", SAVE, rc1["response"]["example"])
    wp.cmd_save_draft()
    said = wp_host.announced[-1]
    assert said.startswith("Draft saved to SwiftLetter on Community Radio.")
    assert "WordPress" not in said  # nothing is known to differ


# -- refusals -----------------------------------------------------------------------


def _edited_then_refused(wp, wp_host, wp_site, wp_dialogs, refusal) -> str:
    _open(wp, wp_site, wp_dialogs)
    wp_host.text = wp_host.text.replace("forty raised beds", "forty-one raised beds")
    wp_host.save_current()
    draft = wp_host.text
    wp_site.on("POST", SAVE, refusal)
    wp.cmd_save_draft()
    return draft


def test_a_stale_save_says_swiftletters_words_keeps_the_draft_and_offers_compare(
    wp, wp_host, wp_site, wp_dialogs
):
    stale = _refusal("article-save", "stale-save-after-wordpress-edit-is-refused")
    message = _step("article-save", "stale-save-after-wordpress-edit-is-refused")["response"][
        "body"
    ]["message"]
    wp_dialogs.answer("ask_choice", 1, 0)  # Markdown, then Compare with Site
    draft = _edited_then_refused(wp, wp_host, wp_site, wp_dialogs, stale)
    asked = wp_dialogs.asked("ask_choice")[-1]
    assert asked["title"] == "Not Saved to SwiftLetter"
    assert asked["message"].startswith(message)  # dialog text, not the list's label
    assert asked["prompt"] == "&What now:"
    assert [row.split(":")[0] for row in asked["rows"]] == [
        "Compare with Site",
        "Reopen",
        "Keep editing",
    ]
    assert asked["rows"][-1] == "Keep editing"
    assert len(_saves(wp_site)) == 1  # never retried
    assert wp_host.text == draft  # the local draft is untouched
    (report,) = wp_dialogs.reports
    assert report["title"] == "Compare with Site"
    assert wp_site.sent("GET", ARTICLE)[-1].full_url.endswith("?context=edit")


def test_reopen_loads_the_site_copy_and_keeps_the_persons_in_versions(
    wp, wp_host, wp_site, wp_dialogs
):
    stale = _refusal("article-save", "stale-save-after-wordpress-edit-is-refused")
    wp_dialogs.answer("ask_choice", 1, 1)  # Markdown, then Reopen
    draft = _edited_then_refused(wp, wp_host, wp_site, wp_dialogs, stale)
    assert "forty raised beds" in wp_host.text and wp_host.text != draft
    assert wp_host.announced[-1].endswith(
        "Your text is in Previous Versions, and Undo brings it back."
    )
    copy = wp.local.copy_for_path(wp_host.path)
    assert any(v.text == draft for v in wp.local.versions(copy.key))


def test_a_locked_article_says_who_has_it_open_and_asks_nothing(wp, wp_host, wp_site, wp_dialogs):
    draft = _edited_then_refused(wp, wp_host, wp_site, wp_dialogs, _locked())
    assert wp_host.announced[-1].startswith("Pat Reyes is editing this article in WordPress.")
    assert wp_host.announced[-1].endswith("Your changes are still in QUILL.")  # not twice
    assert "unchanged" not in wp_host.announced[-1]
    assert len(wp_dialogs.asked("ask_choice")) == 1  # only the format question
    assert len(_saves(wp_site)) == 1 and wp_host.text == draft


@pytest.mark.parametrize("step_id", ["save-without-version", "save-with-wildcard-version"])
def test_428_and_400_say_the_exact_message(wp, wp_host, wp_site, wp_dialogs, step_id):
    message = _step("article-save", step_id)["response"]["body"]["message"]
    _edited_then_refused(wp, wp_host, wp_site, wp_dialogs, _refusal("article-save", step_id))
    asked = wp_dialogs.asked("ask_choice")[-1]
    assert asked["message"].startswith(message)
    assert len(_saves(wp_site)) == 1


def test_compare_with_site_on_an_article_reads_swiftletters_edit_route(
    wp, wp_host, wp_site, wp_dialogs
):
    _open(wp, wp_site, wp_dialogs)
    wp.cmd_compare()
    (report,) = wp_dialogs.reports
    assert report["text"].startswith("Title: the same on the site and in your copy")
    assert "Your copy and the copy on Community Radio are the same." in report["text"]
    assert [r.get_method() for r in wp_site.requests] == ["GET", "GET"]
