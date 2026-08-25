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


def test_a_suggested_address_is_only_linked_when_it_is_https() -> None:
    """An address we would refuse to fetch is one we should not invite a click
    on either -- and javascript: in an href is the other way to run script."""
    source = _read(_REVIEW_JS)
    block = source[source.index("function safeLink") : source.index("function render")]

    assert 'indexOf("https://") !== 0' in block
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
    """No CDN, no fonts, no analytics: every request this page makes is to us."""
    source = _read(path)
    for external in ("http://", "cdn.", "googleapis", "gstatic", "unpkg", "jsdelivr"):
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
    assert '<main id="main">' in source


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
    assert 'role="alert"' in source


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
