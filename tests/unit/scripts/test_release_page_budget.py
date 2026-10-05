"""GATE-RELEASE-PAGE: the 30-release page budget (release-channels plan 9.2).

Installed Quill Radio 3.0.4 and QUILL Lite 1.1.2 read only GitHub's first page
of 30 releases, newest created first, and ignore prereleases. Every Beta
published to ``Community-Access/quill`` pushes their newest Stable release one
place further down; past the page it vanishes, and those copies stop seeing
updates without saying so. ``publish_release.py`` refuses to publish once any
app's newest Stable would be more than 20 releases down, and Dev builds never
go to that repository at all.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from quill.core.updater.feed_publish import PAGE_BUDGET, ListedRelease, page_budget_problems
from quill.tools import release_feed as rf

REPO = Path(__file__).resolve().parents[3]


def _listing(betas_after_stable: int) -> list[ListedRelease]:
    rows = [ListedRelease("quill-radio-v3.2.0", "3.2.0", "radio", False, "2026-10-01T00:00:00Z")]
    for n in range(betas_after_stable):
        rows.append(
            ListedRelease(
                f"quill-lite-v1.3.0-beta.{n}",
                f"1.3.0-beta.{n}",
                "quilllite",
                True,
                f"2026-10-02T00:{n:02d}:00Z",
            )
        )
    return rows


def test_budget_is_twenty_with_room_left_on_the_page() -> None:
    assert PAGE_BUDGET == 20
    assert PAGE_BUDGET < 30


def test_within_budget_is_allowed() -> None:
    assert page_budget_problems(_listing(18), adding=1) == []


def test_over_budget_is_refused_and_says_what_to_do() -> None:
    problems = page_budget_problems(_listing(20), adding=1)
    assert len(problems) == 1
    assert "radio" in problems[0]
    assert "keep their tags" in problems[0]


def test_an_app_with_no_stable_release_is_not_counted() -> None:
    rows = [
        ListedRelease(f"quill-cast-v2.0.0-beta.{n}", "", "cast", True, f"{n}") for n in range(40)
    ]
    assert page_budget_problems(rows) == []


def _load_publish():
    spec = importlib.util.spec_from_file_location(
        "publish_release", REPO / "scripts" / "publish_release.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["publish_release"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_publish_release_refuses_before_creating_anything(tmp_path: Path) -> None:
    publish = _load_publish()
    listing = [
        {
            "tag_name": "quill-radio-v3.2.0",
            "prerelease": False,
            "created_at": "2026-10-01T00:00:00Z",
        }
    ] + [
        {
            "tag_name": f"quill-lite-v1.3.0-beta.{n}",
            "prerelease": True,
            "created_at": f"2026-10-02T00:{n:02d}:00Z",
        }
        for n in range(20)
    ]
    calls: list[list[str]] = []

    def gh(args):
        calls.append(list(args))
        if args[0] == "api":
            return json.dumps(listing)
        raise AssertionError(f"nothing may be created when over budget: {args}")

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "Quill-Cast-Setup-Shared-2.1.0-beta.1.exe").write_bytes(b"x")
    out: list[str] = []
    code = publish.run(
        ["--app", "cast", "--version", "2.1.0-beta.1", "--channel", "beta", "--dist", str(dist)],
        gh=gh,
        root=tmp_path,
        now=datetime(2026, 10, 3, tzinfo=UTC),
        seed_reader=lambda _p: pytest.fail("no signing when refused"),
        out=out.append,
    )
    assert code == 1
    assert any(line.startswith("Refused:") for line in out)
    assert [c[0] for c in calls] == ["api"]


def test_dev_builds_never_touch_the_main_repository() -> None:
    assert rf.DEV_REPO == "Community-Access/quillville-dev-builds"
    assert rf.DEV_REPO != rf.MAIN_REPO
