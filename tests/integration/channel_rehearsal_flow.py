"""One release-channel rehearsal, shared by the offline and the live test.

Publish a Quill Radio build on Dev, promote it to Beta and then Stable,
publish the next Beta, withdraw it, and go back to Stable -- with the real
scripts (``publish_release.py``, ``promote_release.py``,
``revoke_release.py``), a fake ``gh``, a throwaway key, and an app reading the
lists through ``QUILL_UPDATE_FEED_BASE`` the way an installed copy does.

The caller decides how the lists reach the app: ``deploy`` is called with the
feed folder after every script that wrote it, and ``get`` fetches a URL (the
offline test reads the folder; the live one passes ``None`` for the real
HTTPS fetch from wherever ``deploy`` copied them).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

REPO = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

CHANGELOG = """# Changelog

## 3.4.0-beta.1 (Beta) - 2026-10-12

### Added

- Station notes.

## 3.3.0 (Stable) - 2026-10-02

### Fixed

- The sleep timer keeps counting after a station drops.

## 3.3.0-beta.2 (Beta) - 2026-10-01

### Fixed

- Fixed the crash on start that Beta 1 brought in. [beta-only]
  It only happened with an empty favorites list.
- Recordings keep their station name.

### Known rough edges

- None known.

## 3.3.0-beta.1 (Beta) - 2026-09-25

### Added

- A Website button beside Play and Stop.

## [3.2.0] - 2026-09-20

- Everything before.
"""


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"rehearsal_{name}", REPO / "scripts" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeGh:
    """``gh`` as the scripts call it: release files come from *files*."""

    def __init__(self) -> None:
        self.files: dict[str, dict[str, bytes]] = {}
        self.titles: dict[str, str] = {}
        self.calls: list[list[str]] = []

    def __call__(self, args: Sequence[str]) -> str:
        argv = list(args)
        self.calls.append(argv)
        if argv[0] == "api":
            return "[]"
        if argv[:2] == ["release", "download"]:
            folder = Path(argv[argv.index("--dir") + 1])
            for name, data in self.files.get(argv[2], {}).items():
                (folder / name).write_bytes(data)
            return ""
        if argv[:2] == ["release", "view"]:
            return json.dumps({
                "isDraft": False,
                "tagName": argv[2],
                "name": self.titles.get(argv[2], ""),
            })
        if argv[:2] in (["release", "create"], ["release", "edit"]) and "--title" in argv:
            self.titles[argv[2]] = argv[argv.index("--title") + 1]
        return ""


def _dist(root: Path, gh: FakeGh, version: str) -> Path:
    folder = root / "dist" / version
    folder.mkdir(parents=True)
    files = {
        f"Quill-Radio-Setup-Shared-{version}.exe": f"installer {version}".encode(),
        f"Quill-Radio-Portable-{version}.zip": f"portable {version}".encode(),
    }
    for name, data in files.items():
        (folder / name).write_bytes(data)
    gh.files[f"quill-radio-v{version}"] = files
    return folder


def rehearse(
    root: Path,
    *,
    seed: bytes,
    keys: list[bytes],
    state_dir: Path,
    monkeypatch: Any,
    get: Callable[[str], bytes] | None,
    deploy: Callable[[Path], None],
) -> dict[str, Any]:
    """Run the whole rehearsal; returns what each step saw, for the caller to assert."""
    from quill.core.data_format_ledger import Ledger, LedgerEntry
    from quill.core.updater.channels import ChannelState
    from quill.core.updater.feed_fetch import fetch_feed, offers_from_feed
    from quill.core.updater.going_back import assess_return, authorize_downgrade
    from quill.tools import release_feed as rf

    publish = load_script("publish_release")
    promote = load_script("promote_release")
    revoke = load_script("revoke_release")
    gh = FakeGh()
    log: list[str] = []
    seen: dict[str, Any] = {"log": log, "gh": gh}
    original_ok = rf.feed_signature_ok
    monkeypatch.setattr(rf, "feed_signature_ok", lambda path, k=None: original_ok(path, keys))
    changelog = root / "standalone" / "radio" / "docs" / "CHANGELOG.md"
    changelog.parent.mkdir(parents=True, exist_ok=True)
    changelog.write_bytes(CHANGELOG.encode("utf-8"))
    signoff = root / "docs" / "qa" / "signoffs" / "radio-3.3.0.md"
    signoff.parent.mkdir(parents=True, exist_ok=True)
    signoff.write_bytes(
        b"Result: pass\nTester: Rehearsal\nScreen readers: JAWS, NVDA\nDate: 2026-10-10\n"
    )
    common = {"gh": gh, "root": root, "seed_reader": lambda _p: seed, "out": log.append}
    folder = rf.feed_dir(root)

    def client(day: float) -> Any:
        result = fetch_feed(
            "radio", get=get, keys=keys, state_dir=state_dir, now=T0 + timedelta(days=day)
        )
        assert result.status == "ok", result.reason
        return result.feed

    # 1. A final-numbered candidate, first listed on Dev.
    dist = _dist(root, gh, "3.3.0")
    # A build meant for Stable lives in the main repository, where installed
    # copies that predate the feed look; Dev-only builds go to the dev-builds one.
    argv = ["--app", "radio", "--version", "3.3.0", "--channel", "dev", "--dist", str(dist)]
    argv += ["--repo", "Community-Access/quill"]
    # 3.3.0 is a Stable candidate, built signed; 3.4.0-beta.1 below is not.
    signed = {"authenticode": lambda path: "-beta." not in path.name}
    assert publish.run(argv, now=T0, **common, **signed) == 0, log
    deploy(folder)
    seen["dev"] = client(0.1)

    # 2. Dev to Beta, then 3. Beta to Stable, as the same files.
    to = ["--app", "radio", "--version", "3.3.0", "--to"]
    gate = {"docs_gate": lambda: True, **signed}
    assert promote.run([*to, "beta"], now=T0 + timedelta(days=2), **common, **gate) == 0, log
    deploy(folder)
    seen["beta"] = client(2.1)
    dry: list[str] = []
    dry_common = {**common, "out": dry.append}
    assert (
        promote.run([*to, "stable", "--dry-run"], now=T0 + timedelta(days=10), **dry_common, **gate)
        == 0
    ), dry
    seen["dry_run"] = dry
    assert promote.run([*to, "stable"], now=T0 + timedelta(days=10), **common, **gate) == 0, log
    deploy(folder)
    seen["stable"] = client(10.1)

    # 4. The next Beta, then 5. withdraw it.
    dist = _dist(root, gh, "3.4.0-beta.1")
    argv = ["--app", "radio", "--version", "3.4.0-beta.1", "--channel", "beta", "--dist", str(dist)]
    assert publish.run(argv, now=T0 + timedelta(days=11), **common, **signed) == 0, log
    deploy(folder)
    seen["next_beta"] = client(11.1)
    argv = ["--app", "radio", "--version", "3.4.0-beta.1", "--reason", "can lose favorites"]
    assert revoke.run(argv, now=T0 + timedelta(days=12), **common) == 0, log
    deploy(folder)
    feed = client(12.1)
    seen["revoked"] = feed
    seen["offers"] = offers_from_feed(feed, portable=False)

    # 6. A computer on the withdrawn Beta goes back to Stable. Beta lists the
    # release with its build ("3.4.0-beta.1+1"); the withdrawal above named it
    # the way a person does, without one.
    listed = seen["next_beta"].current("beta").version
    ledger = Ledger({
        fid: LedgerEntry(high) for fid, high in feed.release(listed).data_formats.items()
    })
    assessment = assess_return(
        "radio",
        listed,
        feed,
        ChannelState(channel="beta"),
        [ledger],
        {"radio": ChannelState(channel="beta")},
    )
    seen["assessment"] = assessment
    seen["target"] = authorize_downgrade(assessment)
    return seen
