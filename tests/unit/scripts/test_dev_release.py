"""Dev builds are files in ONE rolling release of this repository.

The rolling ``dev-builds`` release exists so that eleven apps' daily Dev builds
take a single place on the page of releases that installed Quill Radio 3.0.4 and
QUILL Lite 1.1.2 read (``GATE-RELEASE-PAGE``). These tests cover the three things
that make that safe: the adapter that gives the planner and the batch promoter
the per-build rows they always had, the script that records builds and retires
old ones, and the protection that keeps a Beta or Stable build's files.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from quill.tools import dev_release as dev
from quill.tools import release_feed as rf

REPO = Path(__file__).resolve().parents[3]
SHA = "c" * 40
OLD_SHA = "d" * 40


def _load_finalize() -> Any:
    spec = importlib.util.spec_from_file_location(
        "dev_release_finalize", REPO / "scripts" / "dev_release_finalize.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["dev_release_finalize"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


finalize = _load_finalize()


def _version(date: str = "20261126", number: int = 1, base: str = "3.2.0") -> str:
    return f"{base}-dev.{date}.{number}"


def _files(app: str, version: str) -> list[str]:
    """The files one Dev build puts in the rolling release."""
    prefix = rf.app(app).asset_prefix
    tag = rf.tag_for(app, version)
    return [
        f"{prefix}-Setup-Shared-{version}.exe",
        f"{prefix}-Portable-{version}.zip",
        f"{tag}{dev.CHECKSUMS_SUFFIX}",
        f"{tag}.LICENSE.txt",
    ]


class RollingGh:
    """An in-memory ``gh`` serving, and editing, the one rolling release."""

    def __init__(self, names: Sequence[str] = (), body: str = "") -> None:
        self.names = list(names)
        self.body = body
        self.exists = True
        self.calls: list[list[str]] = []

    def __call__(self, args: Sequence[str]) -> str:
        argv = list(args)
        self.calls.append(argv)
        if argv[0] == "api" and argv[1].endswith(f"/releases/tags/{dev.DEV_TAG}"):
            if not self.exists:
                raise __import__("subprocess").CalledProcessError(1, argv)
            return json.dumps({"id": 7, "body": self.body})
        if argv[0] == "api" and "/releases/7/assets" in argv[1]:
            return json.dumps([
                [{"name": n, "created_at": "2026-11-26T06:00:00Z"} for n in self.names]
            ])
        if argv[:2] == ["release", "delete-asset"]:
            self.names.remove(argv[3])
            return ""
        if argv[:2] == ["release", "edit"]:
            self.body = Path(argv[argv.index("--notes-file") + 1]).read_text(encoding="utf-8")
            return ""
        if argv[:2] == ["release", "create"]:
            assert argv[2] == dev.DEV_TAG
            assert "--prerelease" in argv and "--latest=false" in argv
            self.exists = True
            self.body = Path(argv[argv.index("--notes-file") + 1]).read_text(encoding="utf-8")
            return ""
        raise AssertionError(argv)


# -- which build a file belongs to -------------------------------------------------


@pytest.mark.parametrize("app", sorted(rf.APPS))
def test_every_app_s_files_are_grouped_to_that_app_even_where_prefixes_overlap(app: str) -> None:
    """``Quill`` begins every other Quill name, so the longest prefix has to win."""
    version = _version(base="1.0.0")
    for name in _files(app, version):
        assert dev.split_asset(name) == (app, version), name


def test_files_that_are_not_dev_builds_are_not_grouped() -> None:
    assert dev.split_asset("Quill-Radio-Setup-Shared-3.2.0.exe") is None
    assert dev.split_asset("notes.md") is None
    assert dev.split_asset("Unknown-App-Setup-1.0.0-dev.20261126.1.exe") is None


def test_the_rolling_tag_is_not_an_app_s_tag() -> None:
    """The tag must never parse as a build, or the release listing would mistake it for one."""
    assert dev.DEV_TAG == "dev-builds"
    assert rf.app_for_tag(dev.DEV_TAG) is None


# -- the rows the planner and the batch promoter read ------------------------------


def _release(builds: dict[tuple[str, str], str]) -> dict[str, Any]:
    names: list[str] = []
    lines: list[str] = []
    for (app, version), sha in builds.items():
        names += _files(app, version)
        lines.append(dev.source_line(app, version, sha))
    gh = RollingGh(names, "\n".join(lines))
    return dev.get_release(gh)


def test_a_recorded_build_becomes_the_row_the_per_build_release_was() -> None:
    version = _version()
    rows = dev.build_rows(_release({("radio", version): SHA}))
    assert len(rows) == 1
    row = rows[0]
    assert row["tag_name"] == rf.tag_for("radio", version)
    assert row["name"] == f"Quill Radio {version} (Dev)"
    assert (
        row["body"]
        == f"Dev build of Quill Radio, unsigned. Built from Community-Access/quill@{SHA}."
    )
    assert row["draft"] is False and row["prerelease"] is True
    names = [a["name"] for a in row["assets"]]
    assert "SHA256SUMS.txt" in names and f"Quill-Radio-Portable-{version}.zip" in names


def test_a_build_with_no_line_in_the_notes_is_not_ready_to_promote() -> None:
    """Files that have arrived, but not yet been recorded, are not a build."""
    release = _release({("radio", _version()): SHA})
    release["body"] = ""
    assert dev.build_rows(release) == []


def test_asset_names_are_one_builds_files_only() -> None:
    release = _release({("radio", _version()): SHA, ("cast", _version(base="2.0.0")): SHA})
    names = dev.asset_names(release, "radio", _version())
    assert names == sorted(_files("radio", _version()))
    assert not any("Cast" in n or "cast" in n for n in names)


def test_a_missing_release_reads_as_empty_never_an_error() -> None:
    gh = RollingGh()
    gh.exists = False
    assert dev.get_release(gh) == {}
    assert dev.build_rows({}) == []


def test_the_download_command_fetches_only_the_builds_own_files_from_the_rolling_release() -> None:
    command = dev.download_command(dev.DEV_TAG, rf.MAIN_REPO, "out", ["a.exe", "b.zip"])
    assert command[:3] == ["release", "download", dev.DEV_TAG]
    assert command.count("--pattern") == 2 and "a.exe" in command and "b.zip" in command
    # Any other release is one build, fetched whole.
    assert "--pattern" not in dev.download_command("quill-radio-v3.2.0", rf.MAIN_REPO, "out", ["a"])


def test_the_tag_a_listed_build_lives_under_comes_from_its_file_addresses() -> None:
    from datetime import UTC, datetime

    from quill.core.updater.feed import FeedAsset
    from quill.core.updater.feed_publish import list_release, new_feed

    version = _version()
    name = f"Quill-Radio-Portable-{version}.zip"
    asset = FeedAsset(
        "portable",
        name,
        f"https://github.com/{rf.MAIN_REPO}/releases/download/{dev.DEV_TAG}/{name}",
        1,
        "b" * 64,
    )
    feed = list_release(
        new_feed("radio", "Quill Radio"),
        version=version,
        tag=rf.tag_for("radio", version),
        channel="dev",
        assets=[asset],
        now=datetime(2026, 11, 26, tzinfo=UTC),
    )
    assert dev.release_tag_of(feed, version, "radio") == dev.DEV_TAG
    assert dev.release_tag_of(feed, "9.9.9", "radio") == rf.tag_for("radio", "9.9.9")


# -- the finalize script -----------------------------------------------------------


def test_ensure_makes_the_release_once_and_never_twice() -> None:
    gh = RollingGh()
    gh.exists = False
    out: list[str] = []
    assert finalize.ensure_release(gh, rf.MAIN_REPO, out=out.append) is True
    assert finalize.ensure_release(gh, rf.MAIN_REPO, out=out.append) is False
    assert sum(c[:2] == ["release", "create"] for c in gh.calls) == 1
    assert "Anyone can download" in gh.body


def test_new_builds_are_recorded_with_the_commit_they_came_from() -> None:
    version = _version()
    gh = RollingGh(_files("radio", version) + _files("cast", _version(base="2.0.0")))
    out: list[str] = []
    assert finalize.finalize(gh, rf.MAIN_REPO, SHA, root=REPO, out=out.append) == 0
    lines = dev.build_lines(gh.body)
    assert lines[rf.tag_for("radio", version)] == SHA
    assert lines[rf.tag_for("cast", _version(base="2.0.0"))] == SHA
    # And the rows the batch promoter reads are now complete.
    assert len(dev.build_rows(dev.get_release(gh))) == 2


def test_a_build_whose_upload_stopped_early_is_not_recorded() -> None:
    version = _version()
    only_checksums = [f"{rf.tag_for('radio', version)}{dev.CHECKSUMS_SUFFIX}"]
    gh = RollingGh(only_checksums)
    finalize.finalize(gh, rf.MAIN_REPO, SHA, root=REPO, out=lambda _l: None)
    assert dev.build_lines(gh.body) == {}


def test_a_build_already_recorded_keeps_its_original_commit() -> None:
    version = _version()
    gh = RollingGh(_files("radio", version), dev.source_line("radio", version, OLD_SHA))
    finalize.finalize(gh, rf.MAIN_REPO, SHA, root=REPO, out=lambda _l: None)
    assert dev.build_lines(gh.body)[rf.tag_for("radio", version)] == OLD_SHA


def test_only_the_newest_few_builds_of_each_app_are_kept() -> None:
    names: list[str] = []
    lines: list[str] = []
    for number in range(1, 6):
        version = _version(number=number)
        names += _files("radio", version)
        lines.append(dev.source_line("radio", version, OLD_SHA))
    gh = RollingGh(names, "\n".join(lines))
    out: list[str] = []
    finalize.finalize(gh, rf.MAIN_REPO, SHA, root=REPO, keep=3, out=out.append)
    kept = {split[1] for n in gh.names if (split := dev.split_asset(n))}
    assert kept == {_version(number=n) for n in (3, 4, 5)}
    assert set(dev.build_lines(gh.body)) == {
        rf.tag_for("radio", _version(number=n)) for n in (3, 4, 5)
    }
    assert "2 retired" in out[-1]


def test_retention_is_per_app_not_across_apps() -> None:
    names = _files("radio", _version(number=1)) + _files("cast", _version(base="2.0.0", number=1))
    gh = RollingGh(names)
    finalize.finalize(gh, rf.MAIN_REPO, SHA, root=REPO, keep=1, out=lambda _l: None)
    assert len(gh.names) == len(names)  # each app's only build stays


def test_a_build_a_signed_feed_points_at_is_never_deleted(tmp_path: Path) -> None:
    """A Beta or Stable listing's files must outlive retention."""
    old, new = _version(number=1), _version(number=2)
    names = _files("radio", old) + _files("radio", new)
    feed_folder = rf.feed_dir(tmp_path)
    feed_folder.mkdir(parents=True)
    protected_file = f"Quill-Radio-Portable-{old}.zip"
    (feed_folder / "radio.json").write_text(
        json.dumps({
            "assets": [
                {
                    "url": f"https://github.com/{rf.MAIN_REPO}/releases/download/"
                    f"{dev.DEV_TAG}/{protected_file}"
                }
            ]
        }),
        encoding="utf-8",
    )
    gh = RollingGh(names)
    out: list[str] = []
    finalize.finalize(gh, rf.MAIN_REPO, SHA, root=tmp_path, keep=1, out=out.append)
    assert protected_file in gh.names and all(n in gh.names for n in _files("radio", old))
    assert any("an update feed points at it" in line for line in out)
    assert not any(c[:2] == ["release", "delete-asset"] for c in gh.calls)


def test_protected_names_read_the_files_feeds_point_at(tmp_path: Path) -> None:
    folder = rf.feed_dir(tmp_path)
    folder.mkdir(parents=True)
    (folder / "a.json").write_text(
        f'{{"url": "https://github.com/x/y/releases/download/{dev.DEV_TAG}/A%20File.zip"}}',
        encoding="utf-8",
    )
    (folder / "b.json").write_text(
        '{"url": "https://github.com/x/y/releases/download/quill-radio-v3.2.0/Other.zip"}',
        encoding="utf-8",
    )
    assert finalize.protected_names(tmp_path) == {"A File.zip"}


def test_a_dry_run_changes_nothing() -> None:
    names = [n for number in range(1, 5) for n in _files("radio", _version(number=number))]
    gh = RollingGh(names)
    finalize.finalize(gh, rf.MAIN_REPO, SHA, root=REPO, keep=1, dry_run=True, out=lambda _l: None)
    assert len(gh.names) == len(names) and gh.body == ""
    assert not any(c[:2] in (["release", "edit"], ["release", "delete-asset"]) for c in gh.calls)


def test_a_bad_commit_is_refused_before_anything_is_touched() -> None:
    gh = RollingGh(_files("radio", _version()))
    assert finalize.finalize(gh, rf.MAIN_REPO, "abc", root=REPO, out=lambda _l: None) == 2
    assert gh.calls == []


def test_the_planner_sees_todays_builds_and_the_commit_they_came_from() -> None:
    """dev_build_plan reads these rows: same commit means nothing to build."""
    version = _version(date="20261126", number=1)
    rows = dev.build_rows(_release({("radio", version): SHA}))
    sources = {key: rf.source_version(key) for key in rf.APPS}
    unchanged = rf.dev_build_plan(
        head_sha=SHA, dev_releases=rows, today="20261126", sources=sources, published={}
    )
    assert unchanged.build is False and "has not changed" in unchanged.reason
    changed = rf.dev_build_plan(
        head_sha="e" * 40, dev_releases=rows, today="20261127", sources=sources, published={}
    )
    assert changed.build is True
