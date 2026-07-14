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
from pathlib import Path
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
# Test/rehearsal overrides. Both default to the production endpoints and are
# inert unless explicitly set, so a release can be dry-run against a throwaway
# repo/feed without touching the public ones. The asset-download path still
# enforces HTTPS + the trusted-host allowlist, so an override can only redirect
# *discovery*, never relax download security.
_API_URL_ENV = "QUILL_UPDATE_API_URL"
_MANIFEST_URL_ENV = "QUILL_UPDATE_MANIFEST_URL"
# Pre-release ordering: a final (non-pre-release) build outranks every
# pre-release of the same major.minor.patch. See _version_tuple / _prerelease_rank.
_STABLE_PRERELEASE_RANK = (9, 0, 0)


def _env_url_override(name: str) -> str:
    """Read a URL override env var, tolerating accidental surrounding quotes.

    A value set with ``setx VAR "https://..."`` (or copied with quotes) can arrive
    wrapped in literal quote characters. urllib then rejects it with
    'unknown url type: "https', breaking the update check. Strip whitespace and a
    single matching pair of surrounding single/double quotes so the override works.
    """
    raw = os.getenv(name, "").strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        raw = raw[1:-1].strip()
    return raw


def resolve_releases_api_url(default: str = GITHUB_RELEASES_API) -> str:
    """The GitHub Releases API URL, honouring the QUILL_UPDATE_API_URL override."""
    return _env_url_override(_API_URL_ENV) or default


def resolve_manifest_url(default: str = DEFAULT_UPDATE_MANIFEST_URL) -> str:
    """The signed-manifest feed URL, honouring the QUILL_UPDATE_MANIFEST_URL override."""
    return _env_url_override(_MANIFEST_URL_ENV) or default


def _ssl_context() -> ssl.SSLContext:
    """An SSL context with a real CA bundle.

    Python on macOS ships without trusted roots wired into urllib, which causes
    'CERTIFICATE_VERIFY_FAILED'. Delegates to the shared verified context so
    every network path in Quill uses the same certificate-verifying policy.
    """
    from quill.core.net import verified_ssl_context

    return verified_ssl_context()


@dataclass(frozen=True, slots=True)
class FeatureAdvisory:
    """A remote instruction to disable one feature (a kill switch).

    Carried inside the signed update manifest, so it inherits the manifest's
    HTTPS + trusted-host + signature protections. It can only *disable* a known
    feature id (see ``quill.core.feature_command_map``) for a version range —
    never enable or execute anything — so the worst a forged advisory could do
    (if signing were ever broken) is make a feature unavailable, which the user
    can override locally. ``min_version`` / ``max_version`` bound which running
    builds it applies to (empty = unbounded); a fixed build lifts the lock by
    publishing a manifest without the advisory, or with a max_version below it.
    """

    feature_id: str
    reason: str = ""
    min_version: str = ""
    max_version: str = ""
    advisory_id: str = ""


@dataclass(frozen=True, slots=True)
class UpdateManifest:
    version: str
    download_url: str
    published_at: str
    notes: str
    signature: str
    advisories: tuple[FeatureAdvisory, ...] = ()


def fetch_update_manifest(
    url: str | None = None,
    timeout: int = 10,
) -> UpdateManifest:
    url = url or resolve_manifest_url()
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
    # False when this release published assets but none of them install on the
    # running platform (e.g. a release with only a macOS .dmg, seen from a
    # Windows client). select_latest() skips these so Check for Updates falls
    # back to the newest release that *is* installable here, instead of
    # offering a release with nothing this client can actually use.
    has_platform_asset: bool = True


def fetch_latest_release(
    include_prereleases: bool = False,
    api_url: str | None = None,
    timeout: int = 10,
) -> GitHubRelease | None:
    """Return the newest GitHub release the user is eligible for.

    Stable channel (default): newest non-prerelease, non-draft release.
    Beta channel (include_prereleases=True): newest release including prereleases.
    Returns None when no eligible release exists.
    """
    api_url = api_url or resolve_releases_api_url()
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

# Extensions that only ever mean "installer for this other platform" — never a
# legitimate asset for the running client. Unlike ``.zip`` (shared by every
# platform's portable/bundle format), these are exclusive, so they're safe to
# drop outright before any suffix matching runs.
_WINDOWS_ONLY_SUFFIXES = (".exe", ".msi")
_MACOS_ONLY_SUFFIXES = (".dmg", ".pkg")
_LINUX_ONLY_SUFFIXES = (".appimage", ".tar.gz")


def _platform_asset_suffixes() -> tuple[str, ...]:
    if sys.platform == "darwin":
        return (".dmg", ".pkg", ".zip")
    if sys.platform.startswith("win"):
        return (".exe", ".msi", ".zip")
    return (".appimage", ".tar.gz", ".zip")


def _foreign_platform_suffixes() -> tuple[str, ...]:
    """Installer extensions that unambiguously belong to a platform other than
    this one, so an asset ending in one is never a candidate here (a Windows
    a Windows client was handed a release's only asset, a macOS .dmg, because
    the old fallback picked *any* asset when nothing matched this platform)."""
    if sys.platform == "darwin":
        return _WINDOWS_ONLY_SUFFIXES + _LINUX_ONLY_SUFFIXES
    if sys.platform.startswith("win"):
        return _MACOS_ONLY_SUFFIXES + _LINUX_ONLY_SUFFIXES
    return _WINDOWS_ONLY_SUFFIXES + _MACOS_ONLY_SUFFIXES


def running_portable() -> bool:
    """True when this QUILL is a verified portable bundle (not an installed copy).

    A portable user updates by replacing the bundle, so they should be handed the
    portable .zip rather than the installer. Best-effort: any failure (or a
    non-portable install) reports False so asset selection falls back to the
    installer as before.
    """
    try:
        from quill.core.storage_mode import portable_root_dir

        return portable_root_dir() is not None
    except Exception:  # noqa: BLE001 - detection must never break update checks
        return False


def _pick_asset(assets: list, *, prefer_portable: bool | None = None) -> str:
    """Choose the real installer for this platform; skip provenance/checksums/etc.

    On a portable install we prefer the portable bundle .zip (e.g.
    ``Quill-Portable-<version>.zip``) and skip the installer .exe, so Check for
    Updates does not push the installer onto a portable user. The portable bundle
    is matched by name ("portable") so the unrelated delta ``*-update-windows.zip``
    artifact is never mistaken for it.

    Returns ``""`` when the release has no asset for this platform at all,
    rather than falling back to *any* remaining asset — a release that only
    published, say, a macOS .dmg must never be handed to a Windows client.
    """
    if prefer_portable is None:
        prefer_portable = running_portable()
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
        if name.endswith(_foreign_platform_suffixes()):
            continue
        usable.append((name, str(url)))
    # Portable installs: prefer the portable bundle .zip over the installer.
    if prefer_portable:
        for name, url in usable:
            if name.endswith(".zip") and "portable" in name:
                return url
        # No portable asset published — fall through to the normal order.
    # Prefer the current platform's installer extension.
    for suffix in _platform_asset_suffixes():
        for name, url in usable:
            if name.endswith(suffix):
                return url
    # Nothing matched this platform — this release has nothing installable
    # here, even though ``usable`` may still hold other platforms' assets.
    return ""


def _release_from_json(data: dict) -> GitHubRelease:
    # Pick the platform installer asset; fall back to the release page when the
    # release has no real installer (e.g. only provenance/checksum artifacts).
    raw_assets = data.get("assets") or []
    download_url = _pick_asset(raw_assets)
    # A release with zero real assets (nothing but provenance/checksums, or
    # nothing at all) is treated as usable — the html_url fallback below is
    # the best we can offer. A release with real assets none of which match
    # this platform (e.g. only a macOS .dmg) is not: mark it ineligible so
    # select_latest() skips it rather than offering a foreign-platform link.
    has_platform_asset = bool(download_url) or not _has_any_real_asset(raw_assets)
    if not download_url:
        download_url = str(data.get("html_url") or "")
    return GitHubRelease(
        version=str(data.get("tag_name") or data.get("name") or "").strip(),
        download_url=download_url,
        published_at=str(data.get("published_at") or "").strip(),
        notes=str(data.get("body") or "").strip(),
        prerelease=bool(data.get("prerelease")),
        has_platform_asset=has_platform_asset,
    )


def _has_any_real_asset(assets: list) -> bool:
    """True when ``assets`` has at least one entry that isn't provenance/
    checksum noise — regardless of which platform it installs on."""
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").lower()
        if not asset.get("browser_download_url"):
            continue
        if name.endswith(_SKIP_ASSET_SUFFIXES):
            continue
        if any(keyword in name for keyword in _SKIP_ASSET_KEYWORDS):
            continue
        return True
    return False


def fetch_releases(api_url: str | None = None, timeout: int = 10) -> list[GitHubRelease]:
    """All non-draft GitHub releases (newest-first as GitHub returns them)."""
    api_url = api_url or resolve_releases_api_url()
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
    """The newest release the user is eligible for and can actually install.

    A release with no asset for this platform (``has_platform_asset=False``,
    e.g. a build whose Windows asset failed and only a macOS one published) is
    skipped entirely, so this falls back to the newest older release that
    *does* have something installable here — never a release with nothing
    this client can use.
    """
    candidates = [
        r for r in releases if (include_prereleases or not r.prerelease) and r.has_platform_asset
    ]
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
        advisories=_parse_advisories(raw.get("advisories")),
    )
    if not manifest.version or not manifest.download_url or not manifest.signature:
        raise ValueError("Manifest is missing required fields")
    _validate_remote_url(manifest.download_url)
    if not verify_manifest_signature(manifest):
        raise ValueError("Manifest signature verification failed")
    return manifest


def _parse_advisories(raw: object) -> tuple[FeatureAdvisory, ...]:
    """Parse the optional ``advisories`` array; tolerant of a missing/odd shape."""
    if not isinstance(raw, list):
        return ()
    out: list[FeatureAdvisory] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        feature_id = str(item.get("feature_id", "")).strip()
        if not feature_id:
            continue
        out.append(
            FeatureAdvisory(
                feature_id=feature_id,
                reason=str(item.get("reason", "")).strip(),
                min_version=str(item.get("min_version", "")).strip(),
                max_version=str(item.get("max_version", "")).strip(),
                advisory_id=str(item.get("advisory_id", "")).strip(),
            )
        )
    return tuple(out)


def _advisories_canonical(advisories: tuple[FeatureAdvisory, ...]) -> list[dict[str, str]]:
    """Deterministic (sorted) serialization of advisories for signing."""
    rows = [
        {
            "advisory_id": a.advisory_id,
            "feature_id": a.feature_id,
            "max_version": a.max_version,
            "min_version": a.min_version,
            "reason": a.reason,
        }
        for a in advisories
    ]
    return sorted(rows, key=lambda r: (r["feature_id"], r["advisory_id"]))


def active_feature_locks(manifest: UpdateManifest, current_version: str) -> dict[str, str]:
    """Feature ids this manifest locks for ``current_version`` -> spoken reason (pure).

    An advisory applies when the running version is within
    ``[min_version, max_version]`` (either bound empty = unbounded on that side).
    """
    locks: dict[str, str] = {}
    current = _version_tuple(current_version)
    for advisory in manifest.advisories:
        if advisory.min_version and _version_tuple(advisory.min_version) > current:
            continue
        if advisory.max_version and _version_tuple(advisory.max_version) < current:
            continue
        locks[advisory.feature_id] = (
            advisory.reason or "temporarily disabled by a QUILL safety advisory"
        )
    return locks


def _canonical_manifest(
    *,
    version: str,
    download_url: str,
    published_at: str,
    notes: str,
    advisories: tuple[FeatureAdvisory, ...] = (),
) -> str:
    """Stable JSON encoding of the signed manifest fields.

    Keys are sorted and separators are tight so the publisher and the client
    hash byte-for-byte identical input. The ``advisories`` key is included only
    when there is at least one advisory, so every existing signed feed (which
    has none) still verifies byte-for-byte against its published signature.
    """
    body: dict[str, object] = {
        "download_url": download_url,
        "notes": notes,
        "published_at": published_at,
        "version": version,
    }
    if advisories:
        body["advisories"] = _advisories_canonical(advisories)
    return json.dumps(body, separators=(",", ":"), sort_keys=True)


def manifest_signature(
    *,
    version: str,
    download_url: str,
    published_at: str,
    notes: str,
    key: str | None = None,
    advisories: tuple[FeatureAdvisory, ...] = (),
) -> str:
    """Compute the update-manifest signature.

    This is the single source of truth shared by the publisher
    (``scripts/generate_update_feed.py``) and this client verifier, so the two
    can never drift apart (the historical bug: the publisher wrote a salt-only
    hash while the verifier demanded an HMAC and rejected every feed).

    Two modes, selected by whether a deployment key is supplied:

    * **Keyed (HMAC-SHA256)** — used when ``key`` is set (the
      ``QUILL_UPDATE_MANIFEST_KEY`` environment variable). The same secret must
      be present when signing *and* verifying, so this only helps when the key
      is provisioned to both the publisher and the installed clients.
    * **Salt-only (SHA-256 over canonical + public salt)** — the deployed
      baseline when no key is configured. The salt is public, so this protects
      against accidental corruption, not a determined attacker; authenticity
      rests on HTTPS to the feed host and to GitHub Releases. Asymmetric
      (Ed25519) signing is the future hardening (see docs/release/RELEASE.md).
    """
    canonical = _canonical_manifest(
        version=version,
        download_url=download_url,
        published_at=published_at,
        notes=notes,
        advisories=advisories,
    )
    if key:
        return hmac.new(key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return hashlib.sha256(f"{canonical}|{_SIGNATURE_SALT}".encode()).hexdigest()


def verify_manifest_signature(manifest: UpdateManifest) -> bool:
    """True when ``manifest.signature`` matches a signature we would compute.

    Uses :func:`manifest_signature` with the deployment key from the
    environment (``QUILL_UPDATE_MANIFEST_KEY``) when present, otherwise the
    salt-only baseline — exactly mirroring how the feed was signed.
    """
    env_key = os.getenv(_MANIFEST_KEY_ENV, "").strip() or None
    expected = manifest_signature(
        version=manifest.version,
        download_url=manifest.download_url,
        published_at=manifest.published_at,
        notes=manifest.notes,
        key=env_key,
        advisories=manifest.advisories,
    )
    return hmac.compare_digest(manifest.signature, expected)


def is_newer_version(current: str, available: str) -> bool:
    return _version_tuple(available) > _version_tuple(current)


def _version_tuple(value: str) -> tuple[int, int, int, tuple[int, int, int]]:
    """Sortable version key with intentional pre-release ordering.

    The fourth element ranks the pre-release stage so that, for the same
    ``major.minor.patch``, a final release always sorts *after* any of its
    pre-releases (``1.2.0`` > ``1.2.0-rc2`` > ``1.2.0-rc1`` > ``1.2.0-beta1`` >
    ``1.2.0-alpha1``). Unrecognized suffixes are treated as the earliest stage so
    an unknown pre-release never outranks a stable build.

    Its third sub-element is an *interim patch* so a hand-off test build can sit
    strictly between two pre-releases: ``Beta 1`` < ``Beta 1A`` < ``Beta 2``
    (display letter) and the equivalent PEP 440 ``0.8.0b1`` < ``0.8.0b1.post1`` <
    ``0.8.0b2``. This lets a tester run an interim build and still be offered the
    real next pre-release through Check for Updates, without being nagged to
    "update" back down to the published one.

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
        r"\.?\s*(\d*)([a-z]?)\b",
        cleaned,
        re.I,
    )
    if space_match:
        base, label, number, patch = space_match.groups()
        label_key = label.strip().lower()
        if label_key == "release candidate":
            label_key = "rc"
        cleaned = f"{base}-{label_key}{number}{patch}"
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


def _prerelease_rank(suffix: str) -> tuple[int, int, int]:
    lowered = suffix.strip().lower()
    if lowered.startswith("rc"):
        tier = 2
    elif lowered.startswith(("beta", "b")):
        tier = 1
    else:
        # alpha/a and anything unrecognized fall to the earliest stage.
        tier = 0
    # The pre-release number is the first run of digits (so "beta1.post1" is
    # number 1, not 11). The interim patch is either a trailing letter right
    # after that number ("beta1a" -> 1, i.e. "A") or a PEP 440 ".postN" suffix.
    number_match = re.search(r"(\d+)", lowered)
    number = int(number_match.group(1)) if number_match else 0
    post = 0
    letter_match = re.search(r"\d([a-z])", lowered)
    post_match = re.search(r"post(\d+)", lowered)
    if letter_match:
        post = ord(letter_match.group(1)) - ord("a") + 1
    elif post_match:
        post = int(post_match.group(1))
    return tier, number, post


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


def extract_portable_update(
    zip_path: str | os.PathLike[str],
    dest_dir: str | os.PathLike[str],
    *,
    max_total: int | None = None,
    max_ratio: int | None = None,
) -> None:
    """Extract a downloaded portable-update ZIP into ``dest_dir``.

    A portable update was previously left as a bare ``.zip`` in the downloads
    folder with no in-app way to act on it beyond "Open folder" -- a portable
    user had to know to extract it themselves. This gives the post-download
    dialog something real to do with a ``.zip`` asset: extract it to a
    ready-to-run sibling folder so "Open folder" reveals a working install
    instead of an unopened archive.

    Uses :func:`quill.core.safe_archive.open_zip` for decompression-bomb
    protection (``max_total``/``max_ratio`` default to that function's own
    limits when not given -- exposed as real parameters, not module-constant
    monkeypatching, so tests can override them deterministically), and
    additionally rejects any archive member whose extracted path would
    resolve outside ``dest_dir`` (zip-slip) -- defense in depth even though
    this only ever runs against Quill's own HTTPS+trusted-host-verified
    release asset, never arbitrary user-supplied input.
    """
    from quill.core.safe_archive import MAX_COMPRESSION_RATIO, MAX_TOTAL_UNCOMPRESSED, open_zip

    dest = Path(dest_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    with open_zip(
        Path(zip_path),
        max_total=max_total if max_total is not None else MAX_TOTAL_UNCOMPRESSED,
        max_ratio=max_ratio if max_ratio is not None else MAX_COMPRESSION_RATIO,
    ) as archive:
        for member in archive.infolist():
            member_path = (dest / member.filename).resolve()
            if member_path != dest and dest not in member_path.parents:
                raise ValueError(f"Refused to extract unsafe archive entry: {member.filename!r}")
        archive.extractall(dest)


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
    "FeatureAdvisory",
    "GitHubRelease",
    "UpdateManifest",
    "URLError",
    "active_feature_locks",
    "download_release_asset",
    "fetch_latest_release",
    "fetch_releases",
    "find_release",
    "select_latest",
    "fetch_update_manifest",
    "is_newer_version",
    "parse_update_manifest",
    "resolve_manifest_url",
    "resolve_releases_api_url",
    "running_portable",
    "manifest_signature",
    "verify_manifest_signature",
]
