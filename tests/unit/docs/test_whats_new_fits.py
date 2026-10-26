"""Every release's "What's new" fits the update window whole (2026-10-25).

The update window shows release notes as plain prose and stops at
``MAX_NOTE_LINES`` lines or ``MAX_NOTE_CHARS`` characters, saying "Notes
shortened". The release-notes documents run to 50,000 characters, and a Stable
roll-up of the changelog can reach 155,000, so either one would be cut off a
third of the way down its first list. ``docs/release/whats-new`` holds the
notes written for that window instead, passed to ``publish_release.py`` and
``promote_release.py`` with ``--notes-file``. The feed's ``notes_summary`` keeps
only the first 4,000 characters of the raw file, so the Markdown counts too.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.tools import release_feed as rf
from quill.ui.update_notice import MAX_NOTE_CHARS, MAX_NOTE_LINES, summarize_release_notes

_ROOT = Path(__file__).resolve().parents[3]
_DIR = _ROOT / "docs" / "release" / "whats-new"
_FILES = sorted(_DIR.glob("whats-new-*.md"))
_NAME = re.compile(r"^whats-new-(?P<app>[a-z]+)-(?P<version>\d+\.\d+\.\d+)\.md$")


def test_there_are_notes_to_check() -> None:
    assert _FILES, f"no What's new notes in {_DIR}"


@pytest.mark.parametrize("path", _FILES, ids=lambda p: p.name)
def test_the_notes_show_in_full(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    shown = summarize_release_notes(raw)
    assert "Notes shortened" not in shown, path.name
    assert len(shown.splitlines()) <= MAX_NOTE_LINES, path.name
    assert len(shown) <= MAX_NOTE_CHARS, path.name
    # feed_publish keeps notes_summary[:4000] of the file as written.
    assert len(raw) <= 4000, path.name


@pytest.mark.parametrize("path", _FILES, ids=lambda p: p.name)
def test_the_notes_name_a_released_app_and_its_version(path: Path) -> None:
    match = _NAME.match(path.name)
    assert match, path.name
    release = rf.app(match["app"])
    assert release.name in path.read_text(encoding="utf-8").splitlines()[0], path.name
    assert rf.changelog_has(match["app"], match["version"], _ROOT), path.name


def test_the_release_plan_publishes_and_promotes_with_them() -> None:
    plan = (_ROOT / "docs" / "release" / "release-plan-lite-radio-cast-transcribe.md").read_text(
        encoding="utf-8"
    )
    for path in _FILES:
        rel = path.relative_to(_ROOT).as_posix()
        assert plan.count(rel) >= 3, f"{rel}: publish, its dry run, and promotion"
