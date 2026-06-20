from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import ssl
import sys
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_UPDATE_MANIFEST_URL = (
    "https://community-access.github.io/quill/updates/.quill-update-feed-v1.json"
)
# GitHub Releases: stable releases reach everyone; anything marked "prerelease"
# reaches beta users only (see fetch_latest_release / the Get beta updates setting).
GITHUB_RELEASES_API = "https://api.github.com/repos/Community-Access/quill/releases"
_SIGNATURE_SALT = "quill-manifest-signature-v1"
_MANIFEST_KEY_ENV = "QUILL_UPDATE_MANIFEST_KEY"
_TRUSTED_HOSTS_ENV = "QUILL_UPDATE_TRUSTED_HOSTS"
# Pre-release ordering: a final (non-pre-release) build outranks every
# pre-release of the same major.minor.patch. See _version_tuple / _prerelease_rank.
_STABLE_PRERELEASE_RANK = (9, 0)


def _ssl_context() -> ssl.SSLContext:
    """An SSL context with a real CA bundle.

    Python on macOS ships without trusted roots wired into urllib, which causes
    'CERTIFICATE_VERIFY_FAILED'. Delegates to the shared verified context so
    every network path in Quill uses the same certificate-verifying policy.
    """
    from quill.core.net import verified_ssl_context

    return verified_ssl_context()


@dataclass(frozen=True, slots=True)
class UpdateManifest:
    version: str
    download_url: str
    published_at: str
    notes: str
    signature: str


def fetch_update_manifest(
    url: str = DEFAULT_UPDATE_MANIFEST_URL,
    timeout: int = 10,
) -> UpdateManifest:
    _validate_remote_url(url)
    with urlopen(url, timeout=timeout, context=_ssl_context()) as response:
        payload = response.read().decode("utf-8", errors="strict")
    return parse_update_manifest(payload)


@dataclass(frozen=True, slots=True)
class GitHubRelease:
    version: str
    download_url: str
    published_at: str
    notes: str
    prerelease: bool


def fetch_latest_release(
    include_prereleases: bool = False,
    api_url: str = GITHUB_RELEASES_API,
    timeout: int = 10,
) -> GitHubRelease | None:
    """Return the newest GitHub release the user is eligible for.

    Stable channel (default): newest non-prerelease, non-draft release.
    Beta channel (include_prereleases=True): newest release including prereleases.
    Returns None when no eligible release exists.
    """
    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Quill-Updater",
        },
    )
    with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        payload = response.read().decode("utf-8", errors="strict")
    releases = json.loads(payload)
    if not isinstance(releases, list):
        raise ValueError("GitHub releases payload must be a JSON array")

    candidates = [r for r in releases if isinstance(r, dict) and not r.get("draft")]
    if not include_prereleases:
        candidates = [r for r in candidates if not r.get("prerelease")]
    if not candidates:
        return None
    # The API returns releases newest-first; pick the newest by version to be safe.
    best = max(candidates, key=lambda r: _version_tuple(str(r.get("tag_name") or "")))
    return _release_from_json(best)


# Assets that are NOT the installer (CI artifacts, signatures, checksums).
_SKIP_ASSET_SUFFIXES = (
    ".json",
    ".sig",
    ".asc",
    ".pem",
    ".sha256",
    ".sha512",
    ".txt",
    ".sbom",
    ".sbom.json",
)
_SKIP_ASSET_KEYWORDS = ("provenance", "checksum", "sbom", "signature")


def _platform_asset_suffixes() -> tuple[str, ...]:
    if sys.platform == "darwin":
        return (".dmg", ".pkg", ".zip")
    if sys.platform.startswith("win"):
        return (".exe", ".msi", ".zip")
    return (".appimage", ".tar.gz", ".zip")


def _pick_asset(assets: list) -> str:
    """Choose the real installer for this platform; skip provenance/checksums/etc."""
    usable: list[tuple[str, str]] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        url = asset.get("browser_download_url")
        name = str(asset.get("name") or "").lower()
        if not url:
            continue
        if name.endswith(_SKIP_ASSET_SUFFIXES):
            continue
        if any(keyword in name for keyword in _SKIP_ASSET_KEYWORDS):
            continue
        usable.append((name, str(url)))
    # Prefer the current platform's installer extension.
    for suffix in _platform_asset_suffixes():
        for name, url in usable:
            if name.endswith(suffix):
                return url
    # Otherwise the first non-artifact asset (if any).
    return usable[0][1] if usable else ""


def _release_from_json(data: dict) -> GitHubRelease:
    # Pick the platform installer asset; fall back to the release page when the
    # release has no real installer (e.g. only provenance/checksum artifacts).
    download_url = _pick_asset(data.get("assets") or [])
    if not download_url:
        download_url = str(data.get("html_url") or "")
    return GitHubRelease(
        version=str(data.get("tag_name") or data.get("name") or "").strip(),
        download_url=download_url,
        published_at=str(data.get("published_at") or "").strip(),
        notes=str(data.get("body") or "").strip(),
        prerelease=bool(data.get("prerelease")),
    )


def fetch_releases(api_url: str = GITHUB_RELEASES_API, timeout: int = 10) -> list[GitHubRelease]:
    """All non-draft GitHub releases (newest-first as GitHub returns them)."""
    request = Request(
        api_url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Quill-Updater"},
    )
    with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        payload = response.read().decode("utf-8", errors="strict")
    raw = json.loads(payload)
    if not isinstance(raw, list):
        raise ValueError("GitHub releases payload must be a JSON array")
    return [_release_from_json(r) for r in raw if isinstance(r, dict) and not r.get("draft")]


def select_latest(
    releases: list[GitHubRelease], include_prereleases: bool = False
) -> GitHubRelease | None:
    candidates = [r for r in releases if include_prereleases or not r.prerelease]
    if not candidates:
        return None
    return max(candidates, key=lambda r: _version_tuple(r.version))


def find_release(releases: list[GitHubRelease], version: str) -> GitHubRelease | None:
    """The release whose tag matches ``version`` (so we can tell if the running
    build is itself a prerelease)."""
    target = _version_tuple(version)
    for release in releases:
        if _version_tuple(release.version) == target:
            return release
    return None


def parse_update_manifest(payload: str) -> UpdateManifest:
    raw = json.loads(payload)
    if not isinstance(raw, dict):
        raise ValueError("Manifest payload must be a JSON object")
    manifest = UpdateManifest(
        version=str(raw.get("version", "")).strip(),
        download_url=str(raw.get("download_url", "")).strip(),
        published_at=str(raw.get("published_at", "")).strip(),
        notes=str(raw.get("notes", "")).strip(),
        signature=str(raw.get("signature", "")).strip(),
    )
    if not manifest.version or not manifest.download_url or not manifest.signature:
        raise ValueError("Manifest is missing required fields")
    _validate_remote_url(manifest.download_url)
    if not verify_manifest_signature(manifest):
        raise ValueError("Manifest signature verification failed")
    return manifest


def verify_manifest_signature(manifest: UpdateManifest) -> bool:
    env_key = os.getenv(_MANIFEST_KEY_ENV, "").strip()
    if not env_key:
        # No deployment key configured — salt-only signatures are not trusted.
        # Operators must set QUILL_UPDATE_MANIFEST_KEY at install time.
        return False
    canonical = json.dumps(
        {
            "download_url": manifest.download_url,
            "notes": manifest.notes,
            "published_at": manifest.published_at,
            "version": manifest.version,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    key = env_key.encode("utf-8")
    expected = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(manifest.signature, expected)


def is_newer_version(current: str, available: str) -> bool:
    return _version_tuple(available) > _version_tuple(current)


def _version_tuple(value: str) -> tuple[int, int, int, tuple[int, int]]:
    """Sortable version key with intentional pre-release ordering.

    The fourth element ranks the pre-release stage so that, for the same
    ``major.minor.patch``, a final release always sorts *after* any of its
    pre-releases (``1.2.0`` > ``1.2.0-rc2`` > ``1.2.0-rc1`` > ``1.2.0-beta1`` >
    ``1.2.0-alpha1``). Unrecognized suffixes are treated as the earliest stage so
    an unknown pre-release never outranks a stable build.

    Accepts both PEP 440 hyphen form (``1.2.0-rc1``) and the human-readable
    display form produced by :func:`quill.build_info.get_short_version`
    (``1.2.0 Beta 1``). Without the second form the running 0.7.0 beta build
    would compare its display string against ``__version__`` (the base
    ``0.7.0``) and never recognize an updated beta as "newer".
    """

    cleaned = value.strip().lstrip("v")
    # Normalize the display form ("0.7.0 Beta 1", "0.7.0 Release Candidate 2")
    # to the PEP 440 hyphen form ("0.7.0-beta1", "0.7.0-rc2") so the rest of
    # the parser only has to know one shape. Without this normalization the
    # running 0.7.0 beta build would compare its display string against
    # ``__version__`` (the base ``0.7.0``) and never recognize an updated
    # beta as "newer" -- or, worse, would treat the suffix digits as part
    # of the patch number ("Release Candidate 1" -> 0.7.1).
    space_match = re.match(
        r"^(\d+\.\d+(?:\.\d+)?)\s+"
        r"(alpha|beta|release\s+candidate|rc|dev)"
        r"\.?\s*(\d*)\b",
        cleaned,
        re.I,
    )
    if space_match:
        base, label, number = space_match.groups()
        label_key = label.strip().lower()
        if label_key == "release candidate":
            label_key = "rc"
        cleaned = f"{base}-{label_key}{number}"
    # Separate the core x.y.z from any pre-release suffix (-rc1, -beta.2, ...) so
    # the suffix digits cannot leak into the patch number.
    core, separator, suffix = cleaned.partition("-")
    parts = core.split(".")
    integers: list[int] = []
    for index in range(3):
        if index < len(parts):
            token = "".join(char for char in parts[index] if char.isdigit())
            integers.append(int(token or "0"))
        else:
            integers.append(0)
    prerelease = _prerelease_rank(suffix) if separator else _STABLE_PRERELEASE_RANK
    return integers[0], integers[1], integers[2], prerelease


def _prerelease_rank(suffix: str) -> tuple[int, int]:
    lowered = suffix.strip().lower()
    if lowered.startswith("rc"):
        tier = 2
    elif lowered.startswith(("beta", "b")):
        tier = 1
    else:
        # alpha/a and anything unrecognized fall to the earliest stage.
        tier = 0
    number = "".join(char for char in lowered if char.isdigit())
    return tier, int(number or "0")


def download_release_asset(
    url: str,
    destination: str | os.PathLike[str],
    timeout: int = 60,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    """Download an update asset to ``destination`` (verified TLS).

    When ``progress`` is supplied it is called as ``progress(bytes_done, total)``
    after each chunk so callers can surface accessible download progress. ``total``
    is ``0`` when the server does not report a Content-Length.
    """
    _validate_remote_url(url)
    request = Request(url, headers={"User-Agent": "Quill-Updater"})
    chunk_size = 64 * 1024
    with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        if progress is not None:
            progress(0, total)
        with open(destination, "wb") as handle:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, total)


def _validate_remote_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("Update URLs must use HTTPS.")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("Update URL must include a host.")
    trusted_hosts = _trusted_update_hosts()
    if trusted_hosts and host not in trusted_hosts:
        raise ValueError(f"Update URL host is not trusted: {host}")


def _trusted_update_hosts() -> set[str]:
    raw_hosts = os.getenv(_TRUSTED_HOSTS_ENV, "")
    trusted = {item.strip().lower() for item in raw_hosts.split(",") if item.strip()}
    trusted.update({
        "community-access.github.io",
        "github.com",
        "objects.githubusercontent.com",
        "github-releases.githubusercontent.com",
    })
    return trusted


__all__ = [
    "DEFAULT_UPDATE_MANIFEST_URL",
    "GITHUB_RELEASES_API",
    "GitHubRelease",
    "UpdateManifest",
    "URLError",
    "download_release_asset",
    "fetch_latest_release",
    "fetch_releases",
    "find_release",
    "select_latest",
    "fetch_update_manifest",
    "is_newer_version",
    "parse_update_manifest",
    "verify_manifest_signature",
]
