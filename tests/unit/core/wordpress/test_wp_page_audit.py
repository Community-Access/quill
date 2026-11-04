"""Check This Page's engine: axe results and the accessibility tree in plain words (9.4).

The browser is faked: a connection that answers DevTools commands from a script.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from quill.core.wordpress import cdp
from quill.core.wordpress import page_audit as pa

AXE_RESULT = [
    {
        "id": "image-alt",
        "impact": "critical",
        "help": "Images must have alternate text",
        "description": "Ensures img elements have alternate text",
        "helpUrl": "https://dequeuniversity.com/rules/axe/image-alt",
        "tags": ["wcag2a", "wcag111"],
        "outcome": "violation",
        "nodes": [
            {
                "target": [".entry-content img"],
                "html": '<img src="https://r.example/desk.jpg">',
                "summary": "Fix: add alt",
                "owner": "content",
            }
        ],
    },
    {
        "id": "color-contrast",
        "impact": "serious",
        "help": "Contrast",
        "description": "",
        "helpUrl": "",
        "tags": ["wcag143"],
        "outcome": "incomplete",
        "nodes": [{"target": ["footer p"], "html": "<p>Footer</p>", "owner": "theme"}],
    },
]

AX_TREE = [
    {"role": {"value": "banner"}, "name": {"value": ""}},
    {
        "role": {"value": "heading"},
        "name": {"value": "Community Radio"},
        "properties": [{"name": "level", "value": {"value": 1}}],
    },
    {
        "role": {"value": "heading"},
        "name": {"value": "Schedule"},
        "properties": [{"name": "level", "value": {"value": 1}}],
    },
    {"role": {"value": "link"}},
    {"role": {"value": "link"}},
    {"role": {"value": "button"}},
    {"role": {"value": "main"}, "ignored": True},
]


class FakeConnection:
    def __init__(self, *, error_text: str = "") -> None:
        self.calls: list[str] = []
        self.error_text = error_text

    def call(self, method, params=None, *, session_id="", timeout=30.0):
        self.calls.append(method)
        if method == "Target.createTarget":
            return {"targetId": "T"}
        if method == "Target.attachToTarget":
            return {"sessionId": "S"}
        if method == "Page.navigate":
            return {"errorText": self.error_text} if self.error_text else {}
        if method == "Runtime.evaluate" and params.get("awaitPromise"):
            return {"result": {"value": json.dumps(AXE_RESULT)}}
        if method == "Accessibility.getFullAXTree":
            return {"nodes": AX_TREE}
        return {}

    def wait_event(self, method, *, session_id="", timeout=30.0):
        self.calls.append(method)


def _launcher(connection):
    @contextmanager
    def launch(_path):
        yield connection

    return launch


def test_audit_runs_axe_reads_the_tree_and_closes_the_tab(tmp_path) -> None:
    connection = FakeConnection()
    audit = pa.audit_url(
        "https://r.example/",
        browser=tmp_path / "msedge.exe",
        axe="axe",
        launcher=_launcher(connection),
    )
    assert connection.calls[-1] == "Target.closeTarget"
    assert "Page.loadEventFired" in connection.calls
    assert audit.problems == 1 and audit.to_check == 1
    assert audit.findings[0].owner == "content" and audit.findings[1].owner == "theme"
    assert audit.shape.headings == ((1, "Community Radio"), (1, "Schedule"))
    assert audit.shape.landmarks == ("header",)
    assert (audit.shape.links, audit.shape.buttons) == (2, 1)
    assert pa.summary_line("Community Radio home page", audit) == (
        "Community Radio home page: 1 problem, 1 to check"
    )


def test_a_page_that_will_not_load_is_a_plain_error(tmp_path) -> None:
    with pytest.raises(cdp.CdpError):
        pa.audit_url(
            "https://r.example/",
            browser=tmp_path / "chrome.exe",
            axe="axe",
            launcher=_launcher(FakeConnection(error_text="net::ERR_NAME_NOT_RESOLVED")),
        )


def test_no_browser_and_no_axe_say_so_before_starting_anything(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cdp, "find_browser", lambda candidates=None: None)
    with pytest.raises(cdp.BrowserMissingError):
        pa.audit_url("https://r.example/", axe="axe", launcher=_launcher(FakeConnection()))
    with pytest.raises(pa.AxeMissingError):
        pa.axe_source(tmp_path / "missing.js")
    assert not pa.axe_available(tmp_path / "missing.js")
    script = tmp_path / "axe.min.js"
    script.write_text("/*! axe v4 */ var axe = {};", encoding="utf-8")
    assert pa.axe_source(script).startswith("/*! axe")


def test_plain_words_explain_and_the_theme_note() -> None:
    image, contrast = pa.parse_axe_results(json.dumps(AXE_RESULT))
    assert pa.finding_row(image) == (
        "Images with no alt text: 1 place, in your content. "
        "Affects people who cannot see the picture"
    )
    assert "to check" in pa.finding_row(contrast)
    text = pa.explain(image)
    assert "WCAG: 1.1.1 Non-text Content." in text and "Fix: add alt" in text
    assert pa.wcag_criteria(["wcag143", "wcag2aa", "wcag999"]) == [
        "1.4.3 Contrast (Minimum)",
        "9.9.9",
    ]
    note = pa.theme_note(contrast, page_url="https://r.example/", theme="Twenty Twenty-Five")
    assert "Twenty Twenty-Five" in note and "1.4.3" in note and "footer p" in note


def test_shape_report_points_out_two_heading_ones() -> None:
    report = pa.shape_report(pa.parse_ax_tree(AX_TREE))
    assert "Heading 1: Schedule" in report
    assert "There are 2 Heading 1s" in report


def test_locate_in_source_by_address_then_text() -> None:
    source = "Intro\n\n![x](https://r.example/desk.jpg)\n\nThe studio is open."
    assert pa.locate_in_source(
        '<img src="https://r.example/desk.jpg?w=300">', source
    ) == source.index("https://r.example/desk.jpg")
    assert pa.locate_in_source("<p>The studio is open.</p>", source) == source.index("The studio")
    assert pa.locate_in_source("<p></p>", source) == -1


def test_find_browser_only_accepts_edge_or_chrome(tmp_path) -> None:
    edge = tmp_path / "msedge.exe"
    other = tmp_path / "calc.exe"
    edge.write_text("", encoding="utf-8")
    other.write_text("", encoding="utf-8")
    assert cdp.find_browser([other, edge]) == edge
    assert cdp.find_browser([other]) is None
    assert all(p.name in ("msedge.exe", "chrome.exe") for p in cdp.browser_candidates({}))
    with pytest.raises(cdp.BrowserMissingError):
        cdp.HeadlessBrowser(Path("calc.exe"))
