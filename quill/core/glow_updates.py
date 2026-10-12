"""Consented, signed, offline-friendly updates for the GLOW accessibility engine.

QUILL ships a vendored GLOW wheel as the offline floor (see ``vendor/wheels``).
This module adds an *opt-in* path that lets a user check for, download, verify,
and apply a newer GLOW engine without waiting for a full QUILL release. It mirrors
the trust model of :mod:`quill.core.updates`:

* every URL is HTTPS and host-allow-listed (reused validation),
* the manifest is HMAC-signed and verified before any download,
* every wheel is SHA-256 verified before it is installed,
* nothing is fetched or installed without the caller's explicit consent.

The module stays ``wx``-free and is fully unit-testable: the install step takes an
injectable command runner so tests never shell out to ``pip``. The actual swap is
"download, verify, install into the runtime, restart to apply" with a recorded
prior version for rollback.

Honesty notes:

* Updating the lightweight ``quill-glow-core`` contract wheel is cheap; updating
  the heavy ``acb-large-print`` backend (pandas, onnxruntime, pymupdf, ...) is a
  large download. The manifest lists every wheel in a bundle so the UI can show
  the real size before the user consents.
* Applying an update mutates the running Python environment, so a restart is
  required for the new engine to load. ``rollback_glow_update`` reinstalls the
  previously vendored wheels when an install fails or is rejected.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.glow import glow_engine_versions
from quill.core.net import verified_ssl_context
from quill.core.updates import (
    URLError,
    _validate_remote_url,
    download_release_asset,
    is_newer_version,
)

DEFAULT_GLOW_MANIFEST_URL = (
    "https://community-access.github.io/quill/updates/.glow-update-feed-v1.json"
)
_GLOW_SIGNATURE_SALT = "quill-glow-update-signature-v1"
_GLOW_MANIFEST_KEY_ENV = "QUILL_GLOW_UPDATE_MANIFEST_KEY"

# A command runner is ``(args) -> returncode``. The default shells out to the
# current interpreter's pip; tests inject a fake so installs stay hermetic.
CommandRunner = Callable[[Sequence[str]], int]


@dataclass(frozen=True, slots=True)
class GlowWheel:
    """One wheel in an update bundle, with its expected SHA-256."""

    filename: str
    url: str
    sha256: str


@dataclass(frozen=True, slots=True)
class GlowUpdateManifest:
    """A signed description of an available GLOW engine update."""

    version: str
    component: str
    published_at: str
    notes: str
    signature: str
    wheels: tuple[GlowWheel, ...]

    @property
    def total_bytes(self) -> int:
        """Best-effort total download size if the manifest carried sizes.

        Size is optional in the wire format; callers that need an exact figure
        read ``Content-Length`` during download. Returns ``0`` when unknown.
        """
        return 0


@dataclass(frozen=True, slots=True)
class GlowUpdateCheck:
    """The outcome of comparing the installed engine to a manifest."""

    installed_version: str
    available_version: str
    update_available: bool
    manifest: GlowUpdateManifest


@dataclass(slots=True)
class GlowUpdateResult:
    """The outcome of a download-and-apply attempt."""

    applied: bool
    version: str
    message: str
    installed_wheels: list[str] = field(default_factory=list)
    rolled_back: bool = False


def installed_glow_version() -> str:
    """The currently active GLOW engine release version, or ``""`` when absent."""
    versions = glow_engine_versions()
    if versions.backend == "unavailable":
        return ""
    return versions.release_version or versions.core_version or ""


def fetch_glow_manifest(
    url: str = DEFAULT_GLOW_MANIFEST_URL,
    timeout: int = 10,
) -> GlowUpdateManifest:
    """Fetch and verify the signed GLOW update manifest over verified TLS."""
    _validate_remote_url(url)
    from urllib.request import urlopen

    with urlopen(url, timeout=timeout, context=verified_ssl_context()) as response:
        payload = response.read().decode("utf-8", errors="strict")
    return parse_glow_manifest(payload)


def parse_glow_manifest(payload: str) -> GlowUpdateManifest:
    """Parse a manifest payload, validating fields, URLs, and the signature."""
    raw = json.loads(payload)
    if not isinstance(raw, dict):
        raise ValueError("GLOW manifest payload must be a JSON object")
    raw_wheels = raw.get("wheels", [])
    if not isinstance(raw_wheels, list) or not raw_wheels:
        raise ValueError("GLOW manifest must list at least one wheel")
    wheels: list[GlowWheel] = []
    for item in raw_wheels:
        if not isinstance(item, dict):
            raise ValueError("Each GLOW wheel entry must be an object")
        wheel = GlowWheel(
            filename=str(item.get("filename", "")).strip(),
            url=str(item.get("url", "")).strip(),
            sha256=str(item.get("sha256", "")).strip().lower(),
        )
        if not wheel.filename or not wheel.url or not wheel.sha256:
            raise ValueError("GLOW wheel entry is missing required fields")
        _validate_remote_url(wheel.url)
        wheels.append(wheel)
    manifest = GlowUpdateManifest(
        version=str(raw.get("version", "")).strip(),
        component=str(raw.get("component", "")).strip() or "quill-glow-core",
        published_at=str(raw.get("published_at", "")).strip(),
        notes=str(raw.get("notes", "")).strip(),
        signature=str(raw.get("signature", "")).strip(),
        wheels=tuple(wheels),
    )
    if not manifest.version or not manifest.signature:
        raise ValueError("GLOW manifest is missing required fields")
    if not verify_glow_manifest_signature(manifest):
        raise ValueError("GLOW manifest signature verification failed")
    return manifest


def verify_glow_manifest_signature(manifest: GlowUpdateManifest) -> bool:
    """Constant-time HMAC-SHA256 check over the manifest's canonical form."""
    canonical = json.dumps(
        {
            "component": manifest.component,
            "notes": manifest.notes,
            "published_at": manifest.published_at,
            "version": manifest.version,
            "wheels": [
                {"filename": w.filename, "sha256": w.sha256, "url": w.url}
                for w in sorted(manifest.wheels, key=lambda w: w.filename)
            ],
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    key = os.getenv(_GLOW_MANIFEST_KEY_ENV, _GLOW_SIGNATURE_SALT).encode("utf-8")
    expected = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(manifest.signature, expected)


def check_for_glow_update(
    url: str = DEFAULT_GLOW_MANIFEST_URL,
    timeout: int = 10,
) -> GlowUpdateCheck:
    """Fetch the manifest and compare it to the installed engine version."""
    manifest = fetch_glow_manifest(url, timeout=timeout)
    installed = installed_glow_version()
    # When nothing is installed yet, any published version is an available update.
    available = bool(manifest.version) and (
        not installed or is_newer_version(installed, manifest.version)
    )
    return GlowUpdateCheck(
        installed_version=installed,
        available_version=manifest.version,
        update_available=available,
        manifest=manifest,
    )


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_glow_wheels(
    manifest: GlowUpdateManifest,
    staging_dir: str | os.PathLike[str],
    timeout: int = 120,
    progress: Callable[[int, int], None] | None = None,
) -> list[Path]:
    """Download every wheel in the manifest into ``staging_dir`` and verify it.

    Each wheel's SHA-256 is checked against the (signed) manifest before it is
    accepted; a mismatch raises ``ValueError`` and the partial file is removed.
    """
    staging = Path(staging_dir)
    staging.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    total = len(manifest.wheels)
    for index, wheel in enumerate(manifest.wheels):
        target = staging / wheel.filename
        download_release_asset(wheel.url, target, timeout=timeout)
        actual = _sha256_of(target)
        if not hmac.compare_digest(actual, wheel.sha256):
            target.unlink(missing_ok=True)
            raise ValueError(
                f"GLOW wheel {wheel.filename} failed checksum verification "
                f"(expected {wheel.sha256}, got {actual})."
            )
        downloaded.append(target)
        if progress is not None:
            progress(index + 1, total)
    return downloaded


def _default_runner(args: Sequence[str]) -> int:
    completed = subprocess.run(list(args), check=False)
    return completed.returncode


def _pip_install_args(wheel_paths: Sequence[Path], find_links: Path) -> list[str]:
    # ``--no-index`` keeps the install fully offline: only the verified, already
    # downloaded wheels in ``find_links`` are eligible.
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--no-index",
        "--find-links",
        str(find_links),
        *(str(path) for path in wheel_paths),
    ]


def install_glow_wheels(
    wheel_paths: Sequence[Path],
    *,
    runner: CommandRunner | None = None,
) -> None:
    """Install verified wheels into the current runtime (offline, no index).

    Raises ``RuntimeError`` when the install command returns non-zero so the
    caller can trigger rollback.
    """
    if not wheel_paths:
        raise ValueError("No GLOW wheels to install")
    run = runner or _default_runner
    find_links = wheel_paths[0].parent
    code = run(_pip_install_args(wheel_paths, find_links))
    if code != 0:
        raise RuntimeError(f"GLOW wheel install failed with exit code {code}")


def apply_glow_update(
    manifest: GlowUpdateManifest,
    staging_dir: str | os.PathLike[str],
    *,
    rollback_dir: str | os.PathLike[str] | None = None,
    runner: CommandRunner | None = None,
    timeout: int = 120,
    progress: Callable[[int, int], None] | None = None,
) -> GlowUpdateResult:
    """Download, verify, and install a GLOW update, rolling back on failure.

    ``rollback_dir`` is the directory holding the currently vendored wheels (the
    offline floor). When the install fails, those wheels are reinstalled so the
    runtime is never left in a half-updated state. Returns a result describing
    what happened; the new engine loads only after a restart.
    """
    try:
        wheels = download_glow_wheels(manifest, staging_dir, timeout=timeout, progress=progress)
    except (ValueError, URLError, OSError) as error:
        return GlowUpdateResult(
            applied=False,
            version=manifest.version,
            message=f"GLOW update download failed: {error}",
        )
    try:
        install_glow_wheels(wheels, runner=runner)
    except (RuntimeError, ValueError) as error:
        rolled_back = _attempt_rollback(rollback_dir, runner=runner)
        return GlowUpdateResult(
            applied=False,
            version=manifest.version,
            message=f"GLOW update install failed: {error}",
            rolled_back=rolled_back,
        )
    return GlowUpdateResult(
        applied=True,
        version=manifest.version,
        message=(
            f"GLOW engine updated to {manifest.version}. "
            "Restart QUILL to load the new accessibility engine."
        ),
        installed_wheels=[wheel.name for wheel in wheels],
    )


def _vendored_wheels(rollback_dir: Path) -> list[Path]:
    return sorted(rollback_dir.glob("quill_glow_core-*.whl")) + sorted(
        rollback_dir.glob("acb_large_print-*.whl")
    )


def _attempt_rollback(
    rollback_dir: str | os.PathLike[str] | None,
    *,
    runner: CommandRunner | None = None,
) -> bool:
    """Reinstall the vendored wheels to restore the previous engine."""
    if rollback_dir is None:
        return False
    directory = Path(rollback_dir)
    if not directory.is_dir():
        return False
    wheels = _vendored_wheels(directory)
    if not wheels:
        return False
    try:
        install_glow_wheels(wheels, runner=runner)
    except (RuntimeError, ValueError):
        return False
    return True


__all__ = [
    "DEFAULT_GLOW_MANIFEST_URL",
    "CommandRunner",
    "GlowWheel",
    "GlowUpdateManifest",
    "GlowUpdateCheck",
    "GlowUpdateResult",
    "installed_glow_version",
    "fetch_glow_manifest",
    "parse_glow_manifest",
    "verify_glow_manifest_signature",
    "check_for_glow_update",
    "download_glow_wheels",
    "install_glow_wheels",
    "apply_glow_update",
]
