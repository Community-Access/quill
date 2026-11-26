"""The all-app Dev-to-Beta batch path, offline and catalogue-driven."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core.release_catalog import PRODUCTS
from quill.core.updater.feed import FeedAsset
from quill.core.updater.feed_publish import (
    blocking,
    list_release,
    new_feed,
    promote,
    promotion_checks,
)
from quill.tools import release_feed as rf
from scripts import promote_release_batch as batch

SOURCE_SHA = "a" * 40
PUBLISHED = datetime(2026, 11, 24, 6, 0, tzinfo=UTC)
NOW = PUBLISHED + timedelta(days=2)


def _release_row(app: str, number: int = 1, *, sha: str = SOURCE_SHA) -> dict[str, object]:
    version = f"3.4.0-dev.20261124.{number}"
    return {
        "tag_name": rf.tag_for(app, version),
        "name": f"{rf.app(app).name} {version} (Dev)",
        "body": (
            f"Dev build of {rf.app(app).name}, unsigned. "
            f"Built from Community-Access/quill@{sha}.\n\n"
            "Not listed on the Dev channel until the owner signs it into the feed.\n"
        ),
        "draft": False,
        "prerelease": True,
        "published_at": PUBLISHED.isoformat().replace("+00:00", "Z"),
        "assets": [
            {"name": f"{rf.app(app).asset_prefix}-Portable-{version}.zip"},
            {"name": "SHA256SUMS.txt"},
        ],
    }


def _release_rows() -> list[dict[str, object]]:
    return [_release_row(app) for app in batch.catalogue_apps()]


class ReleaseListGh:
    def __init__(self, releases: Sequence[dict[str, object]]) -> None:
        self.releases = list(releases)
        self.calls: list[list[str]] = []

    def __call__(self, args: Sequence[str]) -> str:
        argv = list(args)
        self.calls.append(argv)
        assert argv[0] == "api"
        return json.dumps([self.releases])


def _candidate(app: str, version: str, *, when: datetime = PUBLISHED):
    name = f"{rf.app(app).asset_prefix}-Portable-{version}.zip"
    asset = FeedAsset(
        kind="portable",
        name=name,
        url=f"https://github.com/{rf.DEV_REPO}/releases/download/{rf.tag_for(app, version)}/{name}",
        size=10,
        sha256="b" * 64,
    )
    return list_release(
        new_feed(app, rf.app(app).name),
        version=version,
        tag=rf.tag_for(app, version),
        channel="dev",
        assets=[asset],
        now=when,
    )


def test_catalogue_coverage_comes_from_channels_not_a_handwritten_matrix() -> None:
    expected = tuple(product.key for product in PRODUCTS if product.channels_enabled)
    assert batch.catalogue_apps() == expected == tuple(rf.APPS)
    assert len(expected) == 11


def test_one_exact_release_is_resolved_for_every_catalogue_app() -> None:
    resolved = batch.resolve_dev_batch(_release_rows(), SOURCE_SHA)
    assert tuple(build.app for build in resolved) == batch.catalogue_apps()
    assert {build.source_sha for build in resolved} == {SOURCE_SHA}
    assert all(rf.tag_for(build.app, build.version) == build.tag for build in resolved)
    assert all(build.checksum_file == "SHA256SUMS.txt" for build in resolved)


def test_every_app_must_belong_to_the_same_dev_run_number() -> None:
    rows = _release_rows()
    rows[-1] = _release_row(batch.catalogue_apps()[-1], 2)
    with pytest.raises(batch.BatchError, match="run suffixes differ"):
        batch.resolve_dev_batch(rows, SOURCE_SHA)


def test_missing_and_duplicate_apps_are_reported_together() -> None:
    rows = _release_rows()
    missing = {"cast", "weather"}
    rows = [
        row
        for row in rows
        if rf.app_for_tag(str(row["tag_name"]))[0] not in missing  # type: ignore[index]
    ]
    rows.append(_release_row("radio", 2))
    with pytest.raises(batch.BatchError) as caught:
        batch.resolve_dev_batch(rows, SOURCE_SHA)
    message = str(caught.value)
    assert "missing: cast, weather" in message
    assert "duplicates: radio [" in message
    assert rf.tag_for("radio", "3.4.0-dev.20261124.1") in message
    assert rf.tag_for("radio", "3.4.0-dev.20261124.2") in message


@pytest.mark.parametrize(
    ("change", "detail"),
    [
        ({"tag_name": "quill-radio-v3.4.0-beta.1"}, "canonical Dev version"),
        ({"tag_name": "quill-weather-v3.4.0-dev.20261124.1"}, "not channel-enabled"),
        ({"prerelease": False}, "prerelease=true"),
        ({"name": "Quill Weather 3.4.0-dev.20261124.1 (Dev)"}, "has title"),
        (
            {"assets": [{"name": "Quill-Weather-Portable-3.4.0-dev.20261124.1.zip"}]},
            "mismatched app or version",
        ),
        (
            {"assets": [{"name": "Quill-Radio-Portable-3.4.0-dev.20261124.1.zip"}]},
            "SHA256SUMS.txt",
        ),
    ],
)
def test_tag_version_app_title_and_channel_shapes_are_exact(
    change: dict[str, object], detail: str
) -> None:
    row = _release_row("radio")
    row.update(change)
    with pytest.raises(batch.BatchError) as caught:
        batch.resolve_dev_batch([row], SOURCE_SHA, apps=("radio",))
    assert detail in str(caught.value)


def test_only_an_exact_full_sha_in_the_trusted_body_marker_matches() -> None:
    row = _release_row("radio")
    row["body"] = str(row["body"]).replace(f"@{SOURCE_SHA}.", f"@{SOURCE_SHA}", 1)
    with pytest.raises(batch.BatchError) as caught:
        batch.resolve_dev_batch([row], SOURCE_SHA, apps=("radio",))
    assert "trusted body marker" in str(caught.value)

    wrong = _release_row("radio", sha="b" * 40)
    with pytest.raises(batch.BatchError) as caught:
        batch.resolve_dev_batch([wrong], SOURCE_SHA, apps=("radio",))
    assert "missing: radio" in str(caught.value)


def test_dry_run_uses_existing_checks_and_never_writes_a_feed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases = _release_rows()
    gh = ReleaseListGh(releases)
    calls: list[tuple[str, str, list[str], dict[str, object]]] = []
    docs_calls = 0

    def docs_gate() -> bool:
        nonlocal docs_calls
        docs_calls += 1
        return True

    def fake_publish(argv: list[str], **kwargs):
        app = argv[argv.index("--app") + 1]
        version = argv[argv.index("--version") + 1]
        calls.append(("publish", app, argv, kwargs))
        kwargs["feed_preview"](_candidate(app, version, when=PUBLISHED))
        kwargs["out"](f"{app} preview listed")
        return 0

    def fake_promote(argv: list[str], **kwargs):
        app = argv[argv.index("--app") + 1]
        calls.append(("promote", app, argv, kwargs))
        assert kwargs["docs_gate"]()
        version = argv[argv.index("--version") + 1]
        candidate = kwargs["feed_override"]
        final = promote(candidate, version, "beta", now=NOW)
        kwargs["feed_preview"](final)
        kwargs["out"](f"{app} preview promoted")
        return 0

    monkeypatch.setattr(batch.publish_release, "run", fake_publish)
    monkeypatch.setattr(batch.promote_release, "run", fake_promote)
    monkeypatch.setattr(
        rf, "write_feed", lambda *_a, **_k: pytest.fail("dry-run wrote a release feed")
    )
    report = tmp_path / "audit.md"
    code = batch.run(
        ["--sha", SOURCE_SHA, "--dry-run", "--report", str(report)],
        gh=gh,
        root=tmp_path,
        now=NOW,
        sha_verifier=lambda _sha, _root: None,
        seed_reader=lambda _path: pytest.fail("dry-run read the signing key"),
        docs_gate=docs_gate,
        out=lambda _line: None,
        authenticode=lambda _path: False,
    )
    assert code == 0
    assert docs_calls == 1
    assert [(kind, app) for kind, app, _argv, _kwargs in calls] == [
        item for app in batch.catalogue_apps() for item in (("publish", app), ("promote", app))
    ]
    assert all("--dry-run" in argv for _kind, _app, argv, _kwargs in calls)
    assert not (tmp_path / "docs" / "site" / "updates" / "v2").exists()
    text = report.read_text(encoding="utf-8")
    assert all(f"| {app} |" in text for app in batch.catalogue_apps())
    assert "PASS (dry list + promote checks)" in text
    assert "(preview)" in text
    assert "`SHA256SUMS.txt`" in text


def test_real_batch_lists_then_promotes_each_app_sequentially_without_secret_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases = _release_rows()
    versions = {
        rf.app_for_tag(str(row["tag_name"]))[0]: rf.app_for_tag(str(row["tag_name"]))[1]  # type: ignore[index]
        for row in releases
    }
    gh = ReleaseListGh(releases)
    calls: list[tuple[str, str, list[str]]] = []

    def fake_publish(argv: list[str], **_kwargs):
        app = argv[argv.index("--app") + 1]
        calls.append(("publish", app, argv))
        return 0

    def fake_promote(argv: list[str], **_kwargs):
        app = argv[argv.index("--app") + 1]
        calls.append(("promote", app, argv))
        return 0

    def fake_load(app: str, _root: Path):
        feed = _candidate(app, versions[app])
        return promote(feed, versions[app], "beta", now=NOW)

    monkeypatch.setattr(batch.publish_release, "run", fake_publish)
    monkeypatch.setattr(batch.promote_release, "run", fake_promote)
    monkeypatch.setattr(rf, "load_feed", fake_load)
    monkeypatch.setenv("QUILL_FEED_SIGNING_KEY", "TOP-SECRET-NOT-AN-ARGUMENT")
    code = batch.run(
        ["--sha", SOURCE_SHA],
        gh=gh,
        root=tmp_path,
        now=NOW,
        sha_verifier=lambda _sha, _root: None,
        docs_gate=lambda: True,
        out=lambda _line: None,
        authenticode=lambda _path: False,
    )
    assert code == 0
    assert [(kind, app) for kind, app, _argv in calls] == [
        item for app in batch.catalogue_apps() for item in (("publish", app), ("promote", app))
    ]
    assert all("--dry-run" not in argv for _kind, _app, argv in calls)
    assert all("TOP-SECRET" not in " ".join(argv) for _kind, _app, argv in calls)
    assert all("QUILL_FEED_SIGNING_KEY" not in argv for _kind, _app, argv in calls)


def test_release_publication_starts_the_soak_and_skip_reason_is_one_argument(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases = _release_rows()
    rows: list[dict[str, object]] = []
    gh = ReleaseListGh(releases)
    reason = 'emergency"; touch NOT_CREATED'

    def fake_publish(argv: list[str], **kwargs):
        app = argv[argv.index("--app") + 1]
        version = argv[argv.index("--version") + 1]
        assert kwargs["now"] == PUBLISHED
        kwargs["feed_preview"](_candidate(app, version, when=kwargs["now"]))
        rows.append({"kind": "publish", "argv": argv})
        return 0

    def fake_promote(argv: list[str], **kwargs):
        assert kwargs["now"] == NOW
        assert argv[argv.index("--skip-soak") + 1] == reason
        version = argv[argv.index("--version") + 1]
        kwargs["feed_preview"](
            promote(kwargs["feed_override"], version, "beta", now=NOW, skip_soak_reason=reason)
        )
        rows.append({"kind": "promote", "argv": argv})
        return 0

    monkeypatch.setattr(batch.publish_release, "run", fake_publish)
    monkeypatch.setattr(batch.promote_release, "run", fake_promote)
    assert (
        batch.run(
            ["--sha", SOURCE_SHA, "--dry-run", "--skip-soak", reason],
            gh=gh,
            root=tmp_path,
            now=NOW,
            sha_verifier=lambda _sha, _root: None,
            docs_gate=lambda: True,
            out=lambda _line: None,
            authenticode=lambda _path: False,
        )
        == 0
    )
    assert len(rows) == 2 * len(batch.catalogue_apps())
    assert not (tmp_path / "NOT_CREATED").exists()


def test_one_day_soak_is_required_unless_an_explicit_reason_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    early = NOW - timedelta(hours=12)
    releases = _release_rows()
    for row in releases:
        row["published_at"] = early.isoformat().replace("+00:00", "Z")

    def fake_publish(argv: list[str], **kwargs):
        app = argv[argv.index("--app") + 1]
        version = argv[argv.index("--version") + 1]
        kwargs["feed_preview"](_candidate(app, version, when=kwargs["now"]))
        return 0

    def fake_promote(argv: list[str], **kwargs):
        reason = argv[argv.index("--skip-soak") + 1] if "--skip-soak" in argv else ""
        version = argv[argv.index("--version") + 1]
        checks = promotion_checks(
            kwargs["feed_override"],
            version,
            "beta",
            now=kwargs["now"],
            skip_soak_reason=reason,
        )
        if blocking(checks):
            return 1
        kwargs["feed_preview"](promote(kwargs["feed_override"], version, "beta", now=kwargs["now"]))
        return 0

    monkeypatch.setattr(batch.publish_release, "run", fake_publish)
    monkeypatch.setattr(batch.promote_release, "run", fake_promote)
    common = {
        "gh": ReleaseListGh(releases),
        "root": tmp_path,
        "now": NOW,
        "sha_verifier": lambda _sha, _root: None,
        "docs_gate": lambda: True,
        "out": lambda _line: None,
        "authenticode": lambda _path: False,
    }
    assert batch.run(["--sha", SOURCE_SHA, "--dry-run"], **common) == 1
    assert (
        batch.run(
            ["--sha", SOURCE_SHA, "--dry-run", "--skip-soak", "urgent accessibility fix"],
            **common,
        )
        == 0
    )


def test_sha_and_soak_input_are_rejected_before_gh_or_shell_use(
    tmp_path: Path,
) -> None:
    called = False

    def unexpected_gh(_args):
        nonlocal called
        called = True
        return "[]"

    with pytest.raises(batch.BatchError, match="40 hexadecimal"):
        batch.run(
            ["--sha", 'a"*40 + "; echo pwned'],
            gh=unexpected_gh,
            root=tmp_path,
            sha_verifier=lambda _sha, _root: None,
        )
    with pytest.raises(batch.BatchError, match="one line"):
        batch.run(
            ["--sha", SOURCE_SHA, "--skip-soak", "first\nsecond"],
            gh=unexpected_gh,
            root=tmp_path,
            sha_verifier=lambda _sha, _root: None,
        )
    assert not called


class DownloadGh:
    def __init__(self, tag: str, files: dict[str, bytes]) -> None:
        self.tag = tag
        self.files = files

    def __call__(self, args: Sequence[str]) -> str:
        argv = list(args)
        if argv[:2] == ["release", "download"]:
            folder = Path(argv[argv.index("--dir") + 1])
            for name, data in self.files.items():
                (folder / name).write_bytes(data)
            return ""
        if argv[:2] == ["release", "view"]:
            return json.dumps({"isDraft": False, "tagName": self.tag})
        raise AssertionError(argv)


def test_existing_publish_and_promote_dry_paths_write_only_their_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = "radio"
    version = "3.4.0-dev.20261124.1"
    tag = rf.tag_for(app, version)
    files = {
        f"Quill-Radio-Setup-Shared-{version}.exe": b"unsigned installer",
        f"Quill-Radio-Portable-{version}.zip": b"portable",
    }
    gh = DownloadGh(tag, files)
    changelog = tmp_path / "standalone" / "radio" / "docs" / "CHANGELOG.md"
    changelog.parent.mkdir(parents=True)
    changelog.write_text("# Changelog\n\n## 3.4.0\n\n- Ready for Beta.\n", encoding="utf-8")
    listed: list[object] = []
    final: list[object] = []
    monkeypatch.setattr(rf, "feed_signature_ok", lambda _path, _keys=None: True)
    publish_code = batch.publish_release.run(
        [
            "--app",
            app,
            "--version",
            version,
            "--channel",
            "dev",
            "--existing",
            "--repo",
            rf.DEV_REPO,
            "--dry-run",
        ],
        gh=gh,
        root=tmp_path,
        now=PUBLISHED,
        seed_reader=lambda _path: pytest.fail("dry-run read the signing key"),
        authenticode=lambda _path: False,
        out=lambda _line: None,
        feed_preview=listed.append,
    )
    assert publish_code == 0 and len(listed) == 1
    promote_code = batch.promote_release.run(
        ["--app", app, "--version", version, "--to", "beta", "--dry-run"],
        gh=gh,
        root=tmp_path,
        now=NOW,
        seed_reader=lambda _path: pytest.fail("dry-run read the signing key"),
        docs_gate=lambda: True,
        authenticode=lambda _path: False,
        out=lambda _line: None,
        feed_override=listed[0],
        feed_preview=final.append,
    )
    assert promote_code == 0 and len(final) == 1
    assert final[0].release(version).listed_on("beta")  # type: ignore[attr-defined]
    assert not (tmp_path / "docs" / "site").exists()
