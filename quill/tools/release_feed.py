"""Publishing and promoting QuillVille builds through the signed v2 feed.

The engine behind ``scripts/publish_release.py``, ``scripts/promote_release.py``,
``scripts/feed_tool.py`` and ``scripts/dev_build_plan.py`` (release-channels
plan 4). The rules themselves live in :mod:`quill.core.updater.feed_publish`;
this module adds the outside world -- ``gh``, the files on disk, the feed folder
in the site, and the owner's signing key -- each behind something a test can
replace.

**The signing key never leaves the owner's computer.** It is read from
``QUILL_FEED_KEY_FILE`` or ``~/.config/quill/quill-feed-priv.key`` only at the
moment a feed is signed, and only by :func:`read_seed`. In CI (the promote
workflow) the scripts run with ``--no-sign``: the feed change is written
without a signature, the ``.sig`` is removed so GATE-FEED fails, and the owner
signs it locally with ``python scripts/feed_tool.py sign --app <app>`` before
the change can merge.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from quill.core.updater.feed import (
    FeedAsset,
    ReleaseFeed,
    parse_feed,
    verify_feed_bytes,
)
from quill.core.updater.feed_publish import (
    ListedRelease,
    expiry_warnings,
    new_feed,
    sign_bytes,
)
from quill.core.versioning import ReleaseVersion

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_REPO = "Community-Access/quill"
DEV_REPO = "Community-Access/quillville-dev-builds"
KEY_FILE_ENV = "QUILL_FEED_KEY_FILE"
DEFAULT_KEY_FILE = Path.home() / ".config" / "quill" / "quill-feed-priv.key"


@dataclass(frozen=True)
class AppRelease:
    key: str
    name: str
    tag_prefix: str
    asset_prefix: str
    changelog: str
    version_file: str
    version_constant: str


APPS: dict[str, AppRelease] = {
    a.key: a
    for a in (
        AppRelease(
            "quill", "QUILL", "v", "Quill", "CHANGELOG.md", "quill/__init__.py", "__version__"
        ),
        AppRelease(
            "quilllite",
            "QUILL Lite",
            "quill-lite-v",
            "QuillLite",
            "standalone/quilllite/docs/CHANGELOG.md",
            "quill/core/lite/__init__.py",
            "APP_VERSION",
        ),
        AppRelease(
            "radio",
            "Quill Radio",
            "quill-radio-v",
            "Quill-Radio",
            "standalone/radio/docs/CHANGELOG.md",
            "quill/apps/radio.py",
            "_VERSION",
        ),
        AppRelease(
            "cast",
            "QUILL Cast",
            "quill-cast-v",
            "Quill-Cast",
            "standalone/cast/docs/CHANGELOG.md",
            "quill/apps/podcasts_menu.py",
            "APP_VERSION",
        ),
    )
}


def app(key: str) -> AppRelease:
    if key not in APPS:
        raise SystemExit(f"Unknown app {key!r}; choose one of {', '.join(APPS)}.")
    return APPS[key]


def tag_for(app_key: str, version: str) -> str:
    return app(app_key).tag_prefix + version


def app_for_tag(tag: str) -> tuple[str, str] | None:
    """``("radio", "3.3.0")`` for ``quill-radio-v3.3.0``; ``None`` for anything else."""
    for spec in sorted(APPS.values(), key=lambda a: -len(a.tag_prefix)):
        if tag.startswith(spec.tag_prefix):
            version = tag[len(spec.tag_prefix) :]
            if spec.key == "quill" and not re.match(r"\d", version):
                continue
            return spec.key, version
    return None


def source_version(app_key: str, root: Path = REPO_ROOT) -> str:
    spec = app(app_key)
    text = (root / spec.version_file).read_text(encoding="utf-8")
    match = re.search(
        rf'^{re.escape(spec.version_constant)}\s*(?::\s*str\s*)?=\s*"([^"]+)"', text, re.M
    )
    return match.group(1) if match else ""


# -- gh ---------------------------------------------------------------------------


class Gh(Protocol):
    def __call__(self, args: Sequence[str]) -> str: ...


def gh_cli(args: Sequence[str]) -> str:
    """Run ``gh`` with an argument list (never a shell) and return its output."""
    result = subprocess.run(  # noqa: S603 - fixed executable, argument list
        ["gh", *args], check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout


def release_listing(gh: Gh, repo: str = MAIN_REPO) -> list[ListedRelease]:
    """The first 100 releases on *repo*'s default listing, as installed copies see it."""
    raw = json.loads(gh(["api", f"repos/{repo}/releases?per_page=100"]) or "[]")
    listing = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or item.get("draft"):
            continue
        tag = str(item.get("tag_name") or "")
        found = app_for_tag(tag)
        listing.append(
            ListedRelease(
                tag=tag,
                version=found[1] if found else "",
                app=found[0] if found else "",
                prerelease=bool(item.get("prerelease")),
                created_at=str(item.get("created_at") or ""),
            )
        )
    return listing


# -- files -----------------------------------------------------------------------


def asset_kind(name: str) -> str:
    lower = name.lower()
    if lower == "app-build.json" or lower.endswith("-build.json"):
        return "build-info"
    if "-setup-" in lower and lower.endswith(".exe"):
        return "installer"
    if "portable" in lower and lower.endswith(".zip"):
        return "portable"
    return ""


def hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return path.stat().st_size, digest.hexdigest()


def assets_from_files(files: Sequence[Path], *, repo: str, tag: str) -> list[FeedAsset]:
    assets = []
    for path in sorted(files):
        kind = asset_kind(path.name)
        if not kind:
            continue
        size, sha = hash_file(path)
        url = f"https://github.com/{repo}/releases/download/{tag}/{path.name}"
        assets.append(FeedAsset(kind=kind, name=path.name, url=url, size=size, sha256=sha))
    return assets


def dist_files(folder: Path, app_key: str, version: str) -> list[Path]:
    """The release files a local build left in *folder* for this app and version."""
    prefix = app(app_key).asset_prefix.lower()
    return [
        p
        for p in sorted(folder.iterdir())
        if p.is_file()
        and p.name.lower().startswith(prefix)
        and version in p.name
        and asset_kind(p.name)
    ]


# -- the feed folder --------------------------------------------------------------


def feed_dir(root: Path = REPO_ROOT) -> Path:
    return root / "docs" / "site" / "updates" / "v2"


def load_feed(app_key: str, root: Path = REPO_ROOT) -> ReleaseFeed:
    path = feed_dir(root) / f"{app_key}.json"
    if not path.exists():
        return new_feed(app_key, app(app_key).name)
    return parse_feed(path.read_bytes(), app_key=app_key)


def all_feeds(root: Path = REPO_ROOT) -> list[ReleaseFeed]:
    folder = feed_dir(root)
    if not folder.is_dir():
        return []
    return [
        parse_feed(p.read_bytes()) for p in sorted(folder.glob("*.json")) if p.name != "index.json"
    ]


def read_seed(path: Path | None = None) -> bytes:
    """The owner's feed-signing seed. Read only when signing; never printed."""
    from quill.core.updater.feed_publish import load_seed

    target = path or Path(os.environ.get(KEY_FILE_ENV, "") or DEFAULT_KEY_FILE)
    if not target.is_file():
        raise SystemExit(
            f"No feed signing key at {target}. Sign on the computer that holds it, or "
            f"set {KEY_FILE_ENV}. CI never holds this key: use --no-sign there."
        )
    return load_seed(target.read_text(encoding="utf-8"))


def write_feed(feed: ReleaseFeed, *, seed: bytes | None, root: Path = REPO_ROOT) -> Path:
    """Write ``<app>.json`` (LF bytes) and its ``.sig`` -- or remove a stale ``.sig``."""
    folder = feed_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{feed.app}.json"
    data = feed.to_bytes()
    path.write_bytes(data)
    sig = path.with_name(path.name + ".sig")
    if seed is None:
        sig.unlink(missing_ok=True)
    else:
        sig.write_bytes(sign_bytes(data, seed).encode("ascii"))
    write_index(root=root, seed=seed)
    return path


def write_index(*, root: Path = REPO_ROOT, seed: bytes | None) -> Path:
    folder = feed_dir(root)
    entries = [
        {"app": f.app, "app_name": f.app_name, "path": f"{f.app}.json", "sequence": f.sequence}
        for f in all_feeds(root)
    ]
    path = folder / "index.json"
    data = (
        json.dumps({"format": "quillville-release-index/1", "apps": entries}, indent=2) + "\n"
    ).encode()
    path.write_bytes(data)
    sig = path.with_name("index.json.sig")
    if seed is None:
        sig.unlink(missing_ok=True)
    else:
        sig.write_bytes(sign_bytes(data, seed).encode("ascii"))
    return path


def feed_signature_ok(path: Path, keys: Sequence[bytes] | None = None) -> bool:
    sig = path.with_name(path.name + ".sig")
    if not sig.is_file():
        return False
    return verify_feed_bytes(path.read_bytes(), sig.read_text(encoding="utf-8"), keys)


def warnings_now(root: Path = REPO_ROOT, now: datetime | None = None) -> list[str]:
    return expiry_warnings(all_feeds(root), now=now or datetime.now(UTC))


# -- Dev builds -------------------------------------------------------------------


@dataclass(frozen=True)
class DevPlan:
    build: bool
    reason: str
    number: int = 1
    versions: dict[str, str] = field(default_factory=dict)


def dev_base(source: str, published: Sequence[str]) -> str:
    """The base a Dev build carries: the source version, or the next patch once
    that version has been published, so a Dev build always sorts above it."""
    parsed = ReleaseVersion.try_parse(source)
    if parsed is None:
        return source
    base = parsed.base_text
    for text in published:
        other = ReleaseVersion.try_parse(text)
        if other is not None and other.base == parsed.base and other.stage == "final":
            major, minor, patch = parsed.base
            return f"{major}.{minor}.{patch + 1}"
    return base


def dev_build_plan(
    *,
    head_sha: str,
    dev_releases: Sequence[dict[str, object]],
    today: str,
    sources: dict[str, str],
    published: dict[str, Sequence[str]],
    force: bool = False,
) -> DevPlan:
    """Whether today's Dev build should run, and the versions it would carry.

    At most once a day, and only when ``main`` changed since the last one.
    *dev_releases* is the dev-builds repository's release list; each body
    names the commit it was built from (``Built from Community-Access/quill@<sha>``).
    """
    bodies = [str(r.get("body") or "") for r in dev_releases]
    tags = [str(r.get("tag_name") or "") for r in dev_releases]
    todays = {t for t in tags if f"-dev.{today}." in t}
    if head_sha and any(head_sha in body for body in bodies) and not force:
        return DevPlan(False, f"main has not changed since the last Dev build ({head_sha[:7]})")
    numbers = [int(t.rsplit(".", 1)[-1]) for t in todays if t.rsplit(".", 1)[-1].isdigit()]
    if numbers and not force:
        return DevPlan(False, f"a Dev build was already made today ({today})")
    number = max(numbers, default=0) + 1
    versions = {
        key: f"{dev_base(sources[key], published.get(key, ()))}-dev.{today}.{number}"
        for key in sorted(sources)
    }
    return DevPlan(True, "main changed since the last Dev build", number, versions)


# -- reports ----------------------------------------------------------------------


def changelog_has(app_key: str, version: str, root: Path = REPO_ROOT) -> bool:
    from quill.core.release_notes import extract_version_section

    path = root / app(app_key).changelog
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(extract_version_section(text, version).strip())


def signoff_problems(app_key: str, version: str, root: Path = REPO_ROOT) -> list[str]:
    """What a Stable promotion's screen-reader sign-off sheet is missing (P9)."""
    path = root / "docs" / "qa" / "signoffs" / f"{app_key}-{version}.md"
    if not path.is_file():
        return [f"no sign-off sheet at {path.relative_to(root).as_posix()}"]
    text = path.read_text(encoding="utf-8")
    problems = []
    if not re.search(r"^Result:\s*pass\b", text, re.M | re.I):
        problems.append("the sheet does not say 'Result: pass'")
    for label in ("Tester", "Screen readers", "Date"):
        if not re.search(rf"^{label}:\s*\S", text, re.M | re.I):
            problems.append(f"the sheet has no '{label}:' line")
    return problems


def append_promotion_log(
    line: str, *, root: Path = REPO_ROOT, now: Callable[[], datetime] | None = None
) -> Path:
    path = root / "docs" / "release" / "promotions.log"
    stamp = (now or (lambda: datetime.now(UTC)))().strftime("%Y-%m-%d %H:%M UTC")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"Promotions log: every listing change made by scripts/promote_release.py, "
            b"newest last.\n\n"
        )
    with path.open("ab") as handle:
        handle.write(f"{stamp}  {line}\n".encode())
    return path
