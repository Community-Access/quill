"""Check This Page, behaviourally, with the browser and axe-core faked (wordpress.md 9.4)."""

from __future__ import annotations

from pathlib import Path

from quill.core.wordpress import cdp
from quill.core.wordpress import local as lc
from quill.core.wordpress import page_audit as pa

API = "/wp-json/wp/v2"

IMAGE = pa.AxeFinding(
    "image-alt",
    "critical",
    "Images must have alternate text",
    "Ensures images have alt",
    "",
    ("wcag111",),
    "violation",
    (
        pa.AxeNode(
            (".entry-content img",), '<img src="https://radio.example/desk.jpg">', "", "content"
        ),
    ),
)
CONTRAST = pa.AxeFinding(
    "color-contrast",
    "serious",
    "Contrast",
    "",
    "",
    ("wcag143",),
    "violation",
    (pa.AxeNode(("footer p",), "<p>Footer</p>", "", "theme"),),
)
AUDIT = pa.PageAudit(
    "https://radio.example/schedule/",
    (IMAGE, CONTRAST),
    pa.PageShape(("main content",), ((1, "Schedule"),), 3, 1),
)


def _open_doc(wp, *, status="publish", link="https://radio.example/schedule/", text=None):
    text = text if text is not None else "Intro\n\n![desk](https://radio.example/desk.jpg)\n"
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id="",
        remote_id=12,
        title="Schedule",
        text=text,
        text_format="markdown",
        status=status,
        link=link,
    )
    path = wp.local.write_document(copy)
    wp.host.path = path
    wp.host.text = text
    return copy


def _ready(monkeypatch, audit=AUDIT, seen=None):
    monkeypatch.setattr(pa, "axe_available", lambda path=None: True)
    monkeypatch.setattr(cdp, "find_browser", lambda candidates=None: Path("msedge.exe"))

    def fake_audit(url, **kwargs):
        if seen is not None:
            seen.append(url)
        if isinstance(audit, BaseException):
            raise audit
        return audit

    monkeypatch.setattr(pa, "audit_url", fake_audit)


def test_without_axe_it_says_so_and_sends_nothing(wp, wp_site, monkeypatch) -> None:
    monkeypatch.setattr(pa, "axe_available", lambda path=None: False)
    wp.cmd_check_page()
    assert wp.host.announced[-1] == pa.AXE_MISSING
    assert wp_site.requests == []


def test_without_a_browser_it_says_so(wp, monkeypatch) -> None:
    monkeypatch.setattr(pa, "axe_available", lambda path=None: True)
    monkeypatch.setattr(cdp, "find_browser", lambda candidates=None: None)
    wp.cmd_check_page()
    assert "neither is on this computer" in wp.host.said


def test_an_unpublished_page_points_at_check_before_publishing(wp, monkeypatch) -> None:
    _ready(monkeypatch)
    _open_doc(wp, status="draft", link="")
    wp.cmd_check_page()
    assert "not published on Community Radio yet" in wp.host.said


def test_with_no_wordpress_document_it_checks_the_home_page(wp, wp_dialogs, monkeypatch) -> None:
    seen: list[str] = []
    _ready(monkeypatch, seen=seen)
    wp.cmd_check_page()
    assert seen == ["https://radio.example"]
    assert "Community Radio home page: 2 problems" in wp.host.said
    assert wp_dialogs.window["title"] == "Check This Page"


def test_a_published_page_reports_by_rule_with_explain_and_go_to(
    wp, wp_dialogs, wp_site, monkeypatch
) -> None:
    _ready(monkeypatch)
    wp_site.on(
        "GET", f"{API}/themes", [{"name": {"raw": "Twenty Twenty-Five"}, "stylesheet": "tt5"}]
    )
    _open_doc(wp)
    wp.cmd_check_page()
    assert wp.host.announced[-1] == "Community Radio, Schedule: 2 problems"
    rows = wp_dialogs.window["rows"]
    assert rows[0].startswith("Images with no alt text: 1 place, in your content")
    assert "in the theme or a plugin" in rows[1]

    wp_dialogs.press("&Explain...", 0)
    assert "1.1.1 Non-text Content" in wp_dialogs.reports[-1]["text"]

    assert wp_dialogs.press("&Go to It", 0) is not None
    assert wp.host.caret == wp.host.text.index("https://radio.example/desk.jpg")

    assert wp_dialogs.press("&Go to It", 1) is None
    assert "in the theme or a plugin, not in your document" in wp.host.said

    wp_dialogs.press("Write a &Note for the Theme Author...", 1)
    note = wp_dialogs.reports[-1]["text"]
    assert "Twenty Twenty-Five" in note and "https://radio.example/schedule/" in note
    wp_dialogs.press("Write a &Note for the Theme Author...", 0)
    assert "in your own content" in wp.host.said

    wp_dialogs.press("Page &Shape...", None)
    assert "Heading 1: Schedule" in wp_dialogs.reports[-1]["text"]


def test_go_to_it_says_when_the_place_is_not_in_the_text(wp, wp_dialogs, monkeypatch) -> None:
    _ready(monkeypatch)
    _open_doc(wp, text="Nothing matching here.")
    wp.cmd_check_page()
    assert wp_dialogs.press("&Go to It", 0) is None
    assert "could not find that place" in wp.host.said


def test_a_browser_failure_is_said_plainly(wp, monkeypatch) -> None:
    _ready(monkeypatch, audit=cdp.CdpError("The page took too long to answer."))
    _open_doc(wp)
    wp.cmd_check_page()
    assert wp.host.announced[-1] == (
        "Check This Page could not check Community Radio, Schedule: "
        "The page took too long to answer."
    )
