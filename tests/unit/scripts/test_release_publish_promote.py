"""Release channels, Phase 2: publishing, promoting and looking after feeds.

Every rule of ``quill.core.updater.feed_publish`` (first listing, promotion
checks, the 7-day soak and its written reason, final-numbered Stable builds
that were on Beta first, rollback targets, withdrawal, expiry warnings), and
the three scripts end to end against a fake ``gh`` and a throwaway feed
folder. No network, no real key: a key is generated per test.
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

from quill.core.updater.feed import FeedAsset, parse_feed, verify_feed_bytes  # noqa: E402
from quill.core.updater.feed_publish import (  # noqa: E402
    EXPIRY_DAYS,
    blocking,
    expiry_warnings,
    list_release,
    load_seed,
    new_feed,
    promote,
    promotion_checks,
    revoke,
    validate_feed,
)
from quill.tools import release_feed as rf  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _asset(version: str, kind: str = "installer") -> FeedAsset:
    name = f"Quill-Radio-Setup-Shared-{version}.exe"
    return FeedAsset(
        kind=kind,
        name=name,
        url=f"https://github.com/Community-Access/quill/releases/download/quill-radio-v{version}/{name}",
        size=10,
        sha256="b" * 64,
    )


def _listed(feed, version, channel="beta", when=T0, writes=1, reads=1):
    return list_release(
        feed,
        version=version,
        tag=f"quill-radio-v{version}",
        channel=channel,
        assets=[_asset(version)],
        now=when,
        data_formats={"radio.favorites": writes},
        reads_formats={"radio.favorites": reads},
    )


# -- rules --------------------------------------------------------------------------


def test_a_new_build_is_never_listed_straight_on_stable() -> None:
    with pytest.raises(ValueError, match="Beta or Dev"):
        _listed(new_feed("radio", "Quill Radio"), "3.3.0", channel="stable")


def test_every_change_bumps_the_sequence_and_sets_a_90_day_expiry() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.3.0-beta.1")
    assert feed.sequence == 1
    assert feed.days_left(T0) == pytest.approx(EXPIRY_DAYS)
    again = promote(feed, "3.3.0-beta.1", "dev", now=T0 + timedelta(days=1))
    assert again.sequence == 2


def test_stable_takes_only_final_builds_that_were_on_beta_for_a_week() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.3.0-beta.2")
    checks = promotion_checks(feed, "3.3.0-beta.2", "stable", now=T0 + timedelta(days=10))
    assert {c.id for c in blocking(checks)} == {"P4"}
    feed = _listed(feed, "3.3.0", when=T0 + timedelta(days=1))
    early = promotion_checks(feed, "3.3.0", "stable", now=T0 + timedelta(days=3))
    assert {c.id for c in blocking(early)} == {"P10"}
    reasoned = promotion_checks(
        feed, "3.3.0", "stable", now=T0 + timedelta(days=3), skip_soak_reason="crash fix"
    )
    assert blocking(reasoned) == []
    assert "crash fix" in next(c for c in reasoned if c.id == "P10").detail
    ripe = promotion_checks(feed, "3.3.0", "stable", now=T0 + timedelta(days=9))
    assert blocking(ripe) == []


def test_a_dev_build_must_reach_beta_before_stable() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.3.0", channel="dev")
    checks = promotion_checks(feed, "3.3.0", "stable", now=T0 + timedelta(days=30))
    assert "P4b" in {c.id for c in blocking(checks)}


def test_a_shortened_soak_is_written_into_the_feed_history() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.3.0")
    feed = promote(feed, "3.3.0", "stable", now=T0 + timedelta(days=2), skip_soak_reason="hotfix")
    entry = feed.release("3.3.0").history[-1]
    assert entry["channel"] == "stable"
    assert entry["reason"] == "hotfix"
    assert feed.current("stable").version == "3.3.0"


def test_rollback_targets_are_older_stable_builds_that_can_read_everything() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.2.0", writes=1, reads=1)
    feed = promote(feed, "3.2.0", "stable", now=T0 + timedelta(days=8))
    feed = _listed(feed, "3.3.0", when=T0 + timedelta(days=9), writes=1, reads=2)
    feed = _listed(feed, "3.4.0-beta.1", when=T0 + timedelta(days=10), writes=2, reads=2)
    assert feed.release("3.3.0").can_roll_back_to == ("3.2.0",)
    assert feed.release("3.3.0").min_safe_downgrade == "3.2.0"
    assert feed.release("3.4.0-beta.1").can_roll_back_to == ()
    assert validate_feed(feed) == []


def test_the_format_warning_names_what_moved() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.2.0")
    feed = promote(feed, "3.2.0", "stable", now=T0 + timedelta(days=8))
    feed = _listed(feed, "3.3.0", when=T0, writes=2, reads=2)
    checks = promotion_checks(feed, "3.3.0", "stable", now=T0 + timedelta(days=9))
    warning = next(c for c in checks if c.id == "P11")
    assert warning.warning and not warning.passed
    assert "radio.favorites 1 -> 2" in warning.detail
    assert blocking(checks) == []


def test_a_sibling_ahead_of_its_own_channel_blocks_stable() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.3.0")
    release = feed.release("3.3.0")
    from dataclasses import replace

    feed = replace(feed, releases=(replace(release, carries={"quilllite": "1.3.0"}),))
    lite = new_feed("quilllite", "QUILL Lite")
    checks = promotion_checks(
        feed, "3.3.0", "stable", now=T0 + timedelta(days=9), sibling_feeds={"quilllite": lite}
    )
    assert "P7" in {c.id for c in blocking(checks)}


def test_withdrawing_keeps_the_entry_but_offers_it_nowhere() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.4.0-beta.1")
    feed = revoke(
        feed, "3.4.0-beta.1", reason="loses favorites", replacement="3.4.0-beta.2", now=T0
    )
    assert feed.release("3.4.0-beta.1").revoked
    assert feed.current("beta") is None


def test_expiry_warning_fourteen_days_ahead() -> None:
    feed = _listed(new_feed("radio", "Quill Radio"), "3.3.0-beta.1")
    assert expiry_warnings([feed], now=T0 + timedelta(days=60)) == []
    soon = expiry_warnings([feed], now=T0 + timedelta(days=80))
    assert len(soon) == 1 and "expires in 10 days" in soon[0]
    gone = expiry_warnings([feed], now=T0 + timedelta(days=95))
    assert "expired" in gone[0]


def test_key_files_in_both_shapes_load() -> None:
    import base64

    key = SigningKey.generate()
    seed = bytes(key)
    as_seed = base64.b64encode(seed).decode()
    as_pair = "untrusted comment: x\n" + base64.b64encode(seed + bytes(key.verify_key)).decode()
    assert load_seed(as_seed) == seed
    assert load_seed(as_pair) == seed


def test_dev_build_plan_runs_once_a_day_and_only_when_main_changed() -> None:
    sources = {"radio": "3.2.0", "quill": "1.0.0"}
    published = {"radio": ["3.0.4", "3.2.0"], "quill": ["0.9.0-beta.3"]}
    fresh = rf.dev_build_plan(
        head_sha="abc1234", dev_releases=[], today="20261003", sources=sources, published=published
    )
    assert fresh.build
    assert fresh.versions["radio"] == "3.2.1-dev.20261003.1"
    assert fresh.versions["quill"] == "1.0.0-dev.20261003.1"
    same = rf.dev_build_plan(
        head_sha="abc1234",
        dev_releases=[{"tag_name": "quill-radio-v3.2.1-dev.20261002.1", "body": "@abc1234"}],
        today="20261003",
        sources=sources,
        published=published,
    )
    assert not same.build and "not changed" in same.reason
    twice = rf.dev_build_plan(
        head_sha="def5678",
        dev_releases=[{"tag_name": "quill-radio-v3.2.1-dev.20261003.1", "body": "@abc1234"}],
        today="20261003",
        sources=sources,
        published=published,
    )
    assert not twice.build and "already" in twice.reason


# -- the scripts --------------------------------------------------------------------


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class FakeGh:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.calls: list[list[str]] = []

    def __call__(self, args):
        args = list(args)
        self.calls.append(args)
        if args[0] == "api":
            return json.dumps([])
        if args[:2] == ["release", "download"]:
            folder = Path(args[args.index("--dir") + 1])
            for name, data in self.files.items():
                (folder / name).write_bytes(data)
            return ""
        if args[:2] == ["release", "view"]:
            return json.dumps({"isDraft": False, "tagName": args[2]})
        return ""


@pytest.fixture
def key() -> SigningKey:
    return SigningKey.generate()


def _changelog(root: Path, version: str) -> None:
    path = root / "standalone" / "radio" / "docs" / "CHANGELOG.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Changelog\n\n## {version} - 2026-10-01\n\n- Something better.\n", "utf-8")


def _signoff(root: Path, version: str) -> None:
    path = root / "docs" / "qa" / "signoffs" / f"radio-{version}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "Result: pass\nTester: Jeff\nScreen readers: JAWS 2026, NVDA 2026.3\nDate: 2026-10-09\n",
        "utf-8",
    )


def test_publish_then_promote_to_stable_end_to_end(tmp_path: Path, key) -> None:
    publish = _load("publish_release")
    promote_script = _load("promote_release")
    version = "3.3.0"
    files = {
        f"Quill-Radio-Setup-Shared-{version}.exe": b"installer bytes",
        f"Quill-Radio-Portable-{version}.zip": b"portable bytes",
    }
    dist = tmp_path / "dist"
    dist.mkdir()
    for name, data in files.items():
        (dist / name).write_bytes(data)
    gh = FakeGh(files)
    out: list[str] = []
    seed = bytes(key)
    code = publish.run(
        ["--app", "radio", "--version", version, "--channel", "beta", "--dist", str(dist)],
        gh=gh,
        root=tmp_path,
        now=T0,
        seed_reader=lambda _p: seed,
        out=out.append,
    )
    assert code == 0, out
    create = next(c for c in gh.calls if c[:2] == ["release", "create"])
    assert "--prerelease" in create and "--latest=false" in create
    feed_path = tmp_path / "docs" / "site" / "updates" / "v2" / "radio.json"
    sig = (feed_path.parent / "radio.json.sig").read_text("utf-8")
    assert verify_feed_bytes(feed_path.read_bytes(), sig, [bytes(key.verify_key)])
    feed = parse_feed(feed_path.read_bytes())
    assert feed.release(version).channels == ("beta",)
    assert feed.release(version).data_formats.get("radio.favorites") == 1

    _changelog(tmp_path, version)
    common = dict(gh=gh, root=tmp_path, seed_reader=lambda _p: seed, docs_gate=lambda: True)
    monkey_keys = [bytes(key.verify_key)]
    original = rf.feed_signature_ok
    rf.feed_signature_ok = lambda path, keys=None: original(path, monkey_keys)  # type: ignore[assignment]
    try:
        early: list[str] = []
        args = ["--app", "radio", "--version", version, "--to", "stable"]
        assert (
            promote_script.run(
                [*args, "--dry-run"], now=T0 + timedelta(days=3), out=early.append, **common
            )
            == 1
        )
        assert any(line.startswith("FAIL P10") for line in early)
        assert any(line.startswith("FAIL P9") for line in early)
        _signoff(tmp_path, version)
        report = tmp_path / "report.txt"
        dry: list[str] = []
        assert (
            promote_script.run(
                [*args, "--dry-run", "--report", str(report)],
                now=T0 + timedelta(days=8),
                out=dry.append,
                **common,
            )
            == 0
        ), dry
        assert "PASS P2" in report.read_text("utf-8")
        assert parse_feed(feed_path.read_bytes()).release(version).channels == ("beta",)
        done: list[str] = []
        assert promote_script.run(args, now=T0 + timedelta(days=8), out=done.append, **common) == 0
    finally:
        rf.feed_signature_ok = original  # type: ignore[assignment]
    feed = parse_feed(feed_path.read_bytes())
    assert feed.current("stable").version == version
    edit = next(c for c in gh.calls if c[:2] == ["release", "edit"])
    assert "--prerelease=false" in edit and "--latest=false" in edit
    log = (tmp_path / "docs" / "release" / "promotions.log").read_text("utf-8")
    assert f"radio {version} promoted to stable" in log


def test_a_tampered_file_fails_promotion(tmp_path: Path, key) -> None:
    publish = _load("publish_release")
    promote_script = _load("promote_release")
    version = "3.3.0-beta.1"
    files = {f"Quill-Radio-Setup-Shared-{version}.exe": b"good"}
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / next(iter(files))).write_bytes(b"good")
    gh = FakeGh(files)
    publish.run(
        ["--app", "radio", "--version", version, "--channel", "dev", "--dist", str(dist)],
        gh=gh,
        root=tmp_path,
        now=T0,
        seed_reader=lambda _p: bytes(key),
        out=lambda _s: None,
    )
    gh.files = {next(iter(files)): b"evil"}
    out: list[str] = []
    code = promote_script.run(
        ["--app", "radio", "--version", version, "--to", "beta", "--dry-run"],
        gh=gh,
        root=tmp_path,
        now=T0 + timedelta(days=2),
        docs_gate=lambda: True,
        out=out.append,
    )
    assert code == 1
    assert any(line.startswith("FAIL P2") for line in out)


def test_no_sign_leaves_the_feed_unsigned_for_the_owner(tmp_path: Path, key) -> None:
    publish = _load("publish_release")
    tool = _load("feed_tool")
    files = {"Quill-Radio-Portable-3.3.0-dev.20261003.1.zip": b"zip"}
    gh = FakeGh(files)
    publish.run(
        [
            "--app",
            "radio",
            "--version",
            "3.3.0-dev.20261003.1",
            "--channel",
            "dev",
            "--existing",
            "--no-sign",
        ],
        gh=gh,
        root=tmp_path,
        now=T0,
        seed_reader=lambda _p: pytest.fail("--no-sign must not read the key"),
        out=lambda _s: None,
    )
    folder = tmp_path / "docs" / "site" / "updates" / "v2"
    assert (folder / "radio.json").exists()
    assert not (folder / "radio.json.sig").exists()
    assert any(
        "Community-Access/quillville-dev-builds" in a.url
        for a in parse_feed((folder / "radio.json").read_bytes()).releases[0].assets
    )
    out: list[str] = []
    assert (
        tool.run(
            ["sign", "--app", "radio"],
            root=tmp_path,
            seed_reader=lambda _p: bytes(key),
            out=out.append,
        )
        == 0
    )
    assert verify_feed_bytes(
        (folder / "radio.json").read_bytes(),
        (folder / "radio.json.sig").read_text("utf-8"),
        [bytes(key.verify_key)],
    )


# -- the scorecard row ----------------------------------------------------------------


def test_feed_audit_fails_unsigned_and_warns_near_expiry(tmp_path: Path, key, monkeypatch) -> None:
    from quill.tools import release_feed_audit
    from quill.tools.platform_report import GATES, GateResult, render_markdown

    feed = list_release(
        new_feed("radio", "Quill Radio"),
        version="3.3.0-beta.1",
        tag="quill-radio-v3.3.0-beta.1",
        channel="beta",
        assets=[_asset("3.3.0-beta.1")],
        now=T0,
    )
    rf.write_feed(feed, seed=None, root=tmp_path)
    folder = rf.feed_dir(tmp_path)
    problems, _ = release_feed_audit.audit(folder, now=T0)
    assert any("unsigned" in p for p in problems)
    rf.write_feed(feed, seed=bytes(key), root=tmp_path)
    monkeypatch.setattr(
        rf,
        "feed_signature_ok",
        lambda path, keys=None: rf.verify_feed_bytes(
            path.read_bytes(),
            path.with_name(path.name + ".sig").read_text("utf-8"),
            [bytes(key.verify_key)],
        ),
    )
    problems, warnings = release_feed_audit.audit(folder, now=T0 + timedelta(days=80))
    assert problems == []
    assert len(warnings) == 1 and "expires in 10 days" in warnings[0]
    gate = next(g for g in GATES if g.name == "release-feeds")
    text = render_markdown([GateResult(gate, True, 0.1, "Warning: soon", warning=True)])
    assert "pass, with a warning" in text and "## Warnings" in text and "FAIL" not in text
