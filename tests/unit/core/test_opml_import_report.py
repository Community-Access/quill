"""Tests for the OPML import validation report's plain-text export
format -- pure, no wx."""

from __future__ import annotations

from quill.core.podcasts.opml import OpmlValidationResult
from quill.ui.podcasts.opml_import_report_dialog import format_report_text


def test_report_lists_only_failures_with_reasons() -> None:
    results = [
        OpmlValidationResult("Good Show", "https://good/feed.xml", True),
        OpmlValidationResult("Dead Show", "https://dead/feed.xml", False, "404 Not Found"),
    ]
    text = format_report_text(results)
    assert "Dead Show" in text
    assert "404 Not Found" in text
    assert "Good Show (https://good/feed.xml)" not in text  # successes aren't itemized


def test_report_summarizes_counts() -> None:
    results = [
        OpmlValidationResult("A", "https://a", True),
        OpmlValidationResult("B", "https://b", True),
        OpmlValidationResult("C", "https://c", False, "timeout"),
    ]
    text = format_report_text(results)
    assert "3 feed(s) checked" in text
    assert "2 reachable" in text
    assert "1 unreachable" in text


def test_report_with_no_failures_says_so() -> None:
    results = [OpmlValidationResult("A", "https://a", True)]
    text = format_report_text(results)
    assert "Every imported feed was reachable." in text
