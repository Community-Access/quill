"""The two Community Picks web pages: the rules that must not rot.

The review page holds a GitHub token and displays text written by the public,
so an injection there steals the token. The rule is absolute -- every public
field is rendered with ``textContent``, never ``innerHTML`` -- and a rule that
lives only in a comment is one somebody removes in a hurry. So it is a test.

The suggest page has no token, but keeps the same discipline: no third-party
script, and nothing from the network rendered as markup.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SITE = Path(__file__).resolve().parents[3] / "docs" / "site" / "picks"
_REVIEW_HTML = _SITE / "review" / "index.html"
_REVIEW_JS = _SITE / "review" / "review.js"
_SUGGEST_HTML = _SITE / "suggest" / "index.html"
_SUGGEST_JS = _SITE / "suggest" / "suggest.js"

_PAGES = (_REVIEW_HTML, _SUGGEST_HTML)
_SCRIPTS = (_REVIEW_JS, _SUGGEST_JS)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", [*_PAGES, *_SCRIPTS], ids=lambda p: p.name)
def test_the_file_exists(path: Path) -> None:
    assert path.is_file()


# -- the token rule ------------------------------------------------------------


def _code_only(source: str) -> str:
    """The script with its comments stripped.

    Needed because the rule below is *documented* in these files, and a check
    that reads prose fails on the sentence explaining why it exists.
    """
    without_blocks = re.sub(r"/\*.*?\*/", " ", source, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", without_blocks, flags=re.M)


def _markup_only(source: str) -> str:
    """The page with its HTML comments stripped.

    Same reason as :func:`_code_only`. These pages explain their accessibility
    decisions in comments beside the markup -- including the reasons an
    attribute is *absent* -- so a check that reads the raw file finds the
    sentence saying "deliberately no role=alert" and fails on it.
    """
    return re.sub(r"<!--.*?-->", " ", source, flags=re.S)


@pytest.mark.parametrize("path", _SCRIPTS, ids=lambda p: p.name)
def test_nothing_is_ever_rendered_as_markup(path: Path) -> None:
    """innerHTML on a page holding a token is how the token leaves.

    outerHTML, insertAdjacentHTML and document.write are the same hole wearing
    different names.
    """
    code = _code_only(_read(path))
    for hole in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert hole not in code, f"{path.name} uses {hole}"


def test_the_review_page_uses_text_nodes_for_public_fields() -> None:
    source = _read(_REVIEW_JS)

    assert "textContent" in source
    assert "createTextNode" in source


def test_a_suggested_address_is_only_linked_when_it_is_the_web() -> None:
    """An href the suggester controls is the other way to run script on a page
    holding a token, so javascript:, file: and data: stay inert text.

    http IS linked: 41% of the stations Radio can already play are http-only,
    and refusing them would exclude exactly the community stations this is for.
    """
    source = _read(_REVIEW_JS)
    block = source[source.index("function safeLink") : source.index("function render")]

    assert 'indexOf("https://") === 0' in block
    assert 'indexOf("http://") === 0' in block
    assert "createTextNode" in block


# -- the content security policy -----------------------------------------------


@pytest.mark.parametrize("path", _PAGES, ids=lambda p: p.name)
def test_the_page_carries_a_strict_policy(path: Path) -> None:
    source = _read(path)
    policy = re.search(r'Content-Security-Policy" content="([^"]+)"', source)

    assert policy, f"{path.name} has no CSP"
    text = policy.group(1)
    assert "default-src 'none'" in text
    assert "script-src 'self'" in text
    assert "base-uri 'none'" in text


def test_the_review_page_can_only_talk_to_github() -> None:
    """So even a successful injection would have nowhere to send the token."""
    policy = re.search(r'Content-Security-Policy" content="([^"]+)"', _read(_REVIEW_HTML))

    assert policy
    assert "connect-src https://api.github.com" in policy.group(1)


@pytest.mark.parametrize("path", _PAGES, ids=lambda p: p.name)
def test_no_third_party_anything(path: Path) -> None:
    """No CDN, no fonts, no analytics: every request this page makes is to us.

    Checks src/href attributes rather than the whole file, because the page
    legitimately mentions "http://" in prose when explaining that an http
    station address is acceptable.
    """
    source = _read(path)
    refs = re.findall(r'(?:src|href)="([^"]+)"', source)
    for ref in refs:
        assert not ref.startswith("http://"), f"{path.name} loads {ref} over http"
    for external in ("cdn.", "googleapis", "gstatic", "unpkg", "jsdelivr"):
        assert external not in source, f"{path.name} reaches {external}"


# -- the token's storage --------------------------------------------------------


def test_the_token_is_session_scoped_unless_asked_otherwise() -> None:
    """On a shared machine the default has to be the safe one."""
    source = _read(_REVIEW_JS)

    assert "sessionStorage" in source
    assert "remember ? localStorage : sessionStorage" in source


def test_signing_out_clears_both_stores() -> None:
    source = _read(_REVIEW_JS)
    block = source[source.index("function signOut") : source.index("function signIn")]

    assert "sessionStorage.removeItem" in block
    assert "localStorage.removeItem" in block


def test_the_review_page_is_not_indexed() -> None:
    assert 'name="robots"' in _read(_REVIEW_HTML)


# -- accessibility ---------------------------------------------------------------


@pytest.mark.parametrize("path", _PAGES, ids=lambda p: p.name)
def test_the_page_has_a_skip_link_a_main_landmark_and_a_language(path: Path) -> None:
    source = _read(path)

    assert '<html lang="en">' in source
    assert 'class="skip-link"' in source
    # Prefix, not the whole tag: the suggest page also carries class and
    # tabindex on <main>, and a test that pins the exact string turns adding a
    # focusable skip target into a failure.
    assert '<main id="main"' in source


@pytest.mark.parametrize("path", _PAGES, ids=lambda p: p.name)
def test_every_input_has_a_label(path: Path) -> None:
    """A field a screen reader cannot name is a field nobody can fill in."""
    source = _read(path)
    ids = set(re.findall(r'<(?:input|textarea|select)[^>]*\bid="([^"]+)"', source))
    labelled = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', source))

    assert ids, f"{path.name} has no fields at all"
    assert ids <= labelled, f"unlabelled in {path.name}: {sorted(ids - labelled)}"


@pytest.mark.parametrize("path", _PAGES, ids=lambda p: p.name)
def test_outcomes_are_announced(path: Path) -> None:
    """A result that only appears visually is a result a screen reader user
    never learns about."""
    source = _read(path)

    assert 'role="status"' in source or 'aria-live="polite"' in source


def test_the_suggest_page_carries_errors_by_focus_rather_than_by_alert() -> None:
    """role="alert" on a container that is then focused reads everything twice.

    Both fire: the alert on injection, the focus a moment later. NVDA and JAWS
    deliver the whole list, then deliver it again, and the first reading is
    routinely clipped mid-word. Worse, an alert whose content has not changed
    may not fire at all -- so resubmitting with the same errors announces
    nothing, and the mechanism being relied on is the unreliable one.

    Focus is deterministic, puts the user *at* the errors rather than merely
    telling them, and leaves the list there to re-read.
    """
    html = _markup_only(_read(_SUGGEST_HTML))
    js = _read(_SUGGEST_JS)

    assert 'role="alert"' not in html
    assert '<div id="errors" tabindex="-1">' in html
    assert "heading.focus()" in js


def test_the_suggest_page_never_disables_its_submit_button() -> None:
    """Disabling the focused element blurs it and sets no sequential starting
    point, so the next Tab restarts at the top of the document -- thirteen
    stops back through every field just filled in, announced by nothing.

    aria-disabled says the same thing to assistive technology and keeps the
    button focusable; a plain guard flag is what actually prevents a second
    send.
    """
    code = _code_only(_read(_SUGGEST_JS))

    assert ".disabled" not in code
    assert 'setAttribute("aria-disabled"' in code


def test_focus_moves_to_the_next_suggestion_after_a_decision() -> None:
    """Otherwise every approval dumps the keyboard back at the top of the page
    and the next one is a scroll away."""
    source = _read(_REVIEW_JS)

    assert "first.focus()" in source
    assert "tabIndex = -1" in source


def test_each_suggestion_is_a_real_heading_rather_than_bold_text() -> None:
    source = _read(_REVIEW_JS)

    assert 'createElement("h3")' in source
    assert 'setAttribute("aria-labelledby"' in source


# -- the shared body format -------------------------------------------------------


def test_the_public_form_writes_the_same_block_the_app_does() -> None:
    """One format for picks-build.yml however a suggestion arrived."""
    from quill.core.pick_suggestion import Suggestion, issue_body, parse_issue_body

    web = _read(_SUGGEST_JS)
    assert '"```json pick"' in web
    assert "feed_url" in web and "stream_url" in web

    body = issue_body(Suggestion(type="stream", title="X", url="https://e.org/s"))
    assert parse_issue_body(body) == {
        "type": "stream",
        "title": "X",
        "stream_url": "https://e.org/s",
    }


def test_the_public_form_says_the_app_can_do_this_without_a_website() -> None:
    """The in-app route needs no account and no browser; a visitor who has the
    app should be told rather than left to find out."""
    source = _read(_SUGGEST_HTML)

    assert "Suggest a Station or Podcast" in source
    assert "no account" in source.lower() or "do not need" in source.lower()


# -- the submission route ---------------------------------------------------------


def test_the_form_posts_to_the_submission_server() -> None:
    """The whole point: the visitor needs no GitHub account.

    Falling back to GitHub's pre-filled new-issue form was the old behaviour
    and it required an account for the final press. If this constant is ever
    emptied, say so on the page as well -- a form that silently stops working
    is worse than one that admits it.
    """
    js = _read(_SUGGEST_JS)

    assert 'var SUBMIT_URL = "https://lp.csedesigns.com/submit/picks";' in js
    assert "fetch(SUBMIT_URL" in js


def test_the_pages_policy_allows_the_endpoint_it_posts_to() -> None:
    """The failure this prevents is the nastiest kind: everything works and the
    form still says it could not be sent.

    ``default-src 'none'`` with no ``connect-src`` blocks the fetch inside the
    browser, before a single packet leaves, and the page reports it exactly the
    way it reports a dead server. The origin in the policy and the origin in
    SUBMIT_URL have to be the same string, so they are checked against each
    other rather than each against a literal.
    """
    html = _read(_SUGGEST_HTML)
    js = _read(_SUGGEST_JS)

    submit_url = re.search(r'var SUBMIT_URL = "([^"]+)"', js)
    assert submit_url, "SUBMIT_URL is not set"
    origin = "/".join(submit_url.group(1).split("/")[:3])

    policy = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)
    assert policy, "the suggest page has no Content-Security-Policy"
    connect = re.search(r"connect-src ([^;\"]+)", policy.group(1))
    assert connect, "the policy has no connect-src, so the fetch cannot leave the browser"
    assert origin in connect.group(1).split()


def test_the_suggest_page_no_longer_claims_an_account_is_needed() -> None:
    """Stale instructions are worse here than missing ones.

    A sighted visitor glances, sees no new tab and re-reads. Somebody using a
    screen reader *acts*: hunts for a GitHub tab that does not exist, searches
    for a "Submit new issue" button that is not there, concludes it failed, and
    sends it again -- which is how one suggestion becomes three.
    """
    html = _read(_SUGGEST_HTML)

    assert "Submit new issue" not in html
    assert "is being removed" not in html
    # The one honest remaining mention: the github.com route under Other ways,
    # which really does need an account and now says so where it is offered.
    account_mentions = re.findall(r"[^.]*GitHub account[^.]*\.", html)
    assert len(account_mentions) == 1, account_mentions
    assert "Other ways" in html[: html.index(account_mentions[0])]
