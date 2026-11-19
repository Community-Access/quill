"""Help > Ask a Person > Report a Help Problem (GH-R-117)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

wx = pytest.importorskip("wx")

from quill.core.github import workbench_help as catalogue  # noqa: E402
from quill.core.github.explore_models import ExploreRow  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.test_github_workbench_window import REPO, _go, bench  # noqa: E402

__all__ = ["bench"]


def _body(link: str) -> str:
    return parse_qs(urlparse(link).query)["body"][0]


def test_the_report_names_the_place_and_the_last_words_and_never_a_token() -> None:
    link = catalogue.help_report_mailto(
        "Pull Requests, owner/repo", "Merged with token ghp_" + "A" * 36, "1.0.0"
    )
    assert link.startswith("mailto:support@community-access.org?subject=GitHub%20Workbench")
    body = _body(link)
    assert "Where I was: Pull Requests, owner/repo" in body
    assert "ghp_" + "A" * 36 not in body
    assert "QUILL version: 1.0.0" in body


def test_ask_a_person_offers_the_report_beside_writing_to_support() -> None:
    titles = [t.title for t in catalogue.help_rows("ask")]
    assert titles == ["Write to support", "Report a Help Problem"]


def test_enter_on_the_report_opens_your_own_email_from_where_you_were(bench, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr("quill.ui.github_workbench_help.webbrowser.open", opened.append)
    _go(bench, NodeRef("repository", "runs", REPO))
    bench.last_result = "Re-ran the workflow."
    _go(bench, NodeRef("", "help_ask", ""))
    row = ExploreRow("Report a Help Problem", "", "", "", "help_topic", catalogue.REPORT_TARGET)
    bench.provider._do_open_topic(None, row)
    body = _body(opened[-1])
    assert f"Where I was: Runs, {REPO}" in body
    assert "The last thing the Workbench said: Re-ran the workflow." in body
