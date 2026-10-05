"""Withdrawing a build, and rolling Beta notes up into Stable ones (plan 4.2, 4.5).

``scripts/revoke_release.py`` and ``scripts/feed_tool.py revoke`` share one
function, ``release_feed.withdraw``; ``scripts/rollup_release_notes.py`` and
``promote_release.py`` share ``release_feed.rolled_up_notes``. No network, no
real key.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("nacl")
from nacl.signing import SigningKey  # noqa: E402

from quill.core.updater.feed import FeedAsset, parse_feed  # noqa: E402
from quill.core.updater.feed_publish import list_release, new_feed, promote  # noqa: E402
from quill.core.updater.notes_rollup import notes_summary, parse_sections, rollup  # noqa: E402
from quill.tools import release_feed as rf  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

NOTES = """# Changelog

## 3.3.0 (Stable) - 2026-10-20

### Fixed

- Recordings keep their station name.

## 3.3.0-beta.1 (Beta) - 2026-10-10

Intro words for Beta 1.

### Added

- Station notes.

### Fixed

- Fixed a crash Beta 1 brought in. [beta-only]
  Only with an empty list.
- The sleep timer keeps counting.

### Known rough edges

- Notes are not in the backup yet.

## [3.2.0] - 2026-09-20

- Older.
"""


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _asset(version: str) -> FeedAsset:
    name = f"Quill-Radio-Setup-Shared-{version}.exe"
    url = (
        f"https://github.com/Community-Access/quill/releases/download/quill-radio-v{version}/{name}"
    )
    return FeedAsset(kind="installer", name=name, url=url, size=10, sha256="c" * 64)


def _feed(tmp_path: Path, key: SigningKey, *, favorites: int = 1):
    feed = new_feed("radio", "Quill Radio")
    for version, when, writes in (("3.2.0", T0, 1), ("3.3.0", T0 + timedelta(days=1), favorites)):
        feed = list_release(
            feed,
            version=version,
            tag=f"quill-radio-v{version}",
            channel="beta",
            assets=[_asset(version)],
            now=when,
            data_formats={"radio.favorites": writes},
            reads_formats={"radio.favorites": writes},
        )
    feed = promote(feed, "3.2.0", "stable", now=T0 + timedelta(days=9))
    rf.write_feed(feed, seed=bytes(key), root=tmp_path)
    return feed


class Gh:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, args):
        self.calls.append(list(args))
        if list(args[:2]) == ["release", "view"]:
            return json.dumps({"name": "Quill Radio 3.3.0"})
        return ""


# -- rollup -------------------------------------------------------------------------


def test_sections_are_read_whatever_the_heading_style() -> None:
    assert [v for v, _ in parse_sections(NOTES)] == ["3.3.0", "3.3.0-beta.1", "3.2.0"]


def test_the_rollup_merges_by_kind_and_drops_what_was_only_ever_beta() -> None:
    result = rollup(NOTES, app_name="Quill Radio", from_version="3.2.0", to_version="3.3.0")
    text = result.markdown()
    assert result.merged == ("3.3.0-beta.1", "3.3.0")
    assert text.startswith("## What's new since 3.2.0\n")
    assert text.count("### Fixed") == 1 and text.count("### Added") == 1
    assert text.index("Intro words") < text.index("### Added")
    assert text.index("sleep timer") < text.index("station name")
    assert "Beta 1 brought in" not in text and "empty list" not in text
    assert "Known rough edges" not in text and "backup yet" not in text
    assert "Before you update" not in text


def test_before_you_update_comes_first_when_a_format_moved() -> None:
    result = rollup(
        NOTES,
        app_name="Quill Radio",
        from_version="3.2.0",
        to_version="3.3.0",
        formats_before={"radio.favorites": 1, "radio.history": 1},
        formats_after={"radio.favorites": 2, "radio.history": 1},
    )
    text = result.markdown()
    assert result.moved == ("radio.favorites",)
    assert text.index("### Before you update") < text.index("### Added")
    assert "saves your favorites in a newer way" in text
    assert "going back to 3.2.0 means restoring a copy" in text


def test_the_summary_is_plain_text_and_fits_the_feed() -> None:
    long = "## What's new\n\n" + "\n".join(f"- **Item** number {n}." for n in range(800))
    summary = notes_summary(long)
    assert len(summary) <= 4000 and "**" not in summary and summary.endswith("...")


def test_the_script_reads_the_formats_from_the_feed(tmp_path: Path) -> None:
    key = SigningKey.generate()
    _feed(tmp_path, key, favorites=2)
    path = tmp_path / rf.app("radio").changelog
    path.parent.mkdir(parents=True)
    path.write_bytes(NOTES.encode())
    out: list[str] = []
    script = _load("rollup_release_notes")
    assert script.run(["--app", "radio", "--to", "3.3.0"], root=tmp_path, out=out.append) == 0
    assert "What's new since 3.2.0" in out[-1]
    assert "favorites in a newer way" in out[-1]
    summary: list[str] = []
    args = ["--app", "radio", "--from", "3.2.0", "--to", "3.3.0", "--summary"]
    assert script.run(args, root=tmp_path, out=summary.append) == 0
    assert "#" not in summary[-1]


# -- withdrawing --------------------------------------------------------------------


def test_withdrawing_falls_back_renames_the_release_and_deletes_nothing(tmp_path: Path) -> None:
    key = SigningKey.generate()
    _feed(tmp_path, key)
    gh = Gh()
    out: list[str] = []
    code = _load("revoke_release").run(
        ["--app", "radio", "--version", "3.3.0", "--reason", "loses favorites", "--no-sign"],
        gh=gh,
        root=tmp_path,
        now=T0 + timedelta(days=10),
        seed_reader=lambda _p: pytest.fail("--no-sign must not read the key"),
        out=out.append,
    )
    assert code == 0, out
    feed = parse_feed((rf.feed_dir(tmp_path) / "radio.json").read_bytes())
    assert feed.release("3.3.0").revoked
    assert feed.release("3.3.0").revoked_reason == "loses favorites"
    assert feed.current("beta").version == "3.2.0"
    assert "Beta now offers 3.2.0 instead of 3.3.0." in out
    edit = next(c for c in gh.calls if c[:2] == ["release", "edit"])
    assert edit[edit.index("--title") + 1] == "Quill Radio 3.3.0 (withdrawn)"
    assert not any("delete" in c for c in gh.calls)
    assert not (rf.feed_dir(tmp_path) / "radio.json.sig").exists()
    assert out[-1] == "Unsigned: run python scripts/feed_tool.py sign --app radio"


def test_a_dry_run_or_a_bad_replacement_changes_nothing(tmp_path: Path) -> None:
    key = SigningKey.generate()
    _feed(tmp_path, key)
    before = (rf.feed_dir(tmp_path) / "radio.json").read_bytes()
    script = _load("revoke_release")
    gh = Gh()
    args = ["--app", "radio", "--version", "3.3.0", "--reason", "x"]
    common = dict(gh=gh, root=tmp_path, seed_reader=lambda _p: bytes(key), out=lambda _s: None)
    assert script.run([*args, "--dry-run"], **common) == 0
    assert script.run([*args, "--replacement", "9.9.9"], **common) == 1
    assert script.run(["--app", "radio", "--version", "4.0.0", "--reason", "x"], **common) == 1
    assert (rf.feed_dir(tmp_path) / "radio.json").read_bytes() == before
    assert gh.calls == []


def test_feed_tool_revoke_is_the_same_withdrawal(tmp_path: Path) -> None:
    key = SigningKey.generate()
    _feed(tmp_path, key)
    gh = Gh()
    code = _load("feed_tool").run(
        ["revoke", "--app", "radio", "--version", "3.3.0", "--reason", "loses favorites"],
        root=tmp_path,
        now=T0 + timedelta(days=10),
        seed_reader=lambda _p: bytes(key),
        out=lambda _s: None,
        gh=gh,
    )
    assert code == 0
    assert any(c[:2] == ["release", "edit"] for c in gh.calls)
    assert parse_feed((rf.feed_dir(tmp_path) / "radio.json").read_bytes()).release("3.3.0").revoked
    assert (rf.feed_dir(tmp_path) / "radio.json.sig").exists()
