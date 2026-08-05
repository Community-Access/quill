"""Offer to fetch a sibling QUILL app that is not installed yet.

QUILL, Quill Radio, and Quill Weather (and Quill Cast) can each open the others;
when the sibling app is not on disk, we don't just say "not installed" -- we
offer to *get* it. This resolves the sibling app's own release asset from the
Community-Access/quill GitHub releases -- the installer ``.exe`` for an installed
build, the portable ``.zip`` for a portable build -- and downloads it over the
same HTTPS + trusted-host verified path the self-updater uses
(:mod:`quill.core.updates`). Every app is treated as its own product with its own
release assets, so each updates and installs independently.

No ``wx`` here: the UI layer runs the warn/ask/progress flow and, after a portable
extract, retries the launch.

GATE-9 / network egress: the only outbound call is :func:`fetch_companion_asset`
(the GitHub releases listing); the actual asset bytes are fetched by
``updates.download_release_asset`` (already reviewed). Both run only on an
explicit user action ("yes, get it").
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from quill.core import updates
from quill.core.app_launcher import app_name, portable_sibling_dirname

#: app key -> the release-asset basename prefix each app publishes. Kept beside
#: the launcher's app table on purpose: a new app is added in both places.
ASSET_PREFIX: dict[str, str] = {
    "quill": "QUILL",
    "radio": "Quill-Radio",
    "weather": "Quill-Weather",
    "cast": "Quill-Cast",
    # Audio Studio's two artifacts are named inconsistently by its own build
    # scripts -- "QUILL-Audio-Studio-Portable-Lean-*.zip" but
    # "Quill-AudioStudio-Setup-*.exe" (no hyphen inside "AudioStudio") -- so the
    # prefix stops at the last segment they share. "Quill-Studio" matched
    # NEITHER, which would have made Studio unresolvable the moment it ships.
    "studio": "Quill-Audio",
}


@dataclass(frozen=True, slots=True)
class CompanionAsset:
    """One resolved release asset for a sibling app."""

    app_key: str
    kind: str  # "installer" | "portable"
    filename: str
    url: str
    version: str


def can_offer_download(app_key: str) -> bool:
    """Whether obtaining ``app_key`` is even possible on this build. Only a
    frozen build has a real install/portable layout to add a sibling to; from
    source, ``python -m`` already runs any app, so there is nothing to fetch.
    Gated companion apps (not in RELEASED_APPS) are never offered for download in
    a public build, so a public build has no path to fetch a hidden app."""
    from quill.core.app_launcher import is_app_released

    return (
        bool(getattr(sys, "frozen", False)) and app_key in ASSET_PREFIX and is_app_released(app_key)
    )


def _kind_markers(portable: bool) -> tuple[str, str]:
    """(needle that must appear in the asset name, required extension)."""
    return ("-portable-", ".zip") if portable else ("-setup-", ".exe")


def resolve_companion_asset(
    app_key: str, releases_json: object, *, portable: bool
) -> CompanionAsset | None:
    """Pure: pick the newest matching release asset for a sibling app.

    ``releases_json`` is the GitHub Releases API payload (a list of releases,
    each a dict with an ``assets`` list of ``{"name", "browser_download_url"}``).
    Returns the installer asset (``portable=False``) or the portable-zip asset
    (``portable=True``) from the newest release that carries one, else ``None``.
    Releases are taken newest-first, exactly as the API returns them.
    """
    prefix = ASSET_PREFIX.get(app_key)
    if prefix is None or not isinstance(releases_json, list):
        return None
    needle, ext = _kind_markers(portable)
    prefix_low = prefix.lower()
    # QUILL's own prefix ("QUILL") is a prefix of every companion's
    # ("Quill-Radio", ...), so a plain startswith would let "install QUILL"
    # resolve Quill-Radio's zip. Claim an asset only when no OTHER app's
    # prefix matches it more specifically -- longest prefix wins.
    rival_prefixes = [
        other.lower()
        for key, other in ASSET_PREFIX.items()
        if key != app_key and len(other) > len(prefix)
    ]
    for release in releases_json:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        for asset in release.get("assets") or []:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "")
            url = str(asset.get("browser_download_url") or "")
            low = name.lower()
            if any(low.startswith(rival) for rival in rival_prefixes):
                continue  # belongs to a sibling app whose prefix is more specific
            if (
                url.lower().startswith("https://")
                and low.startswith(prefix_low)
                and needle in low
                and low.endswith(ext)
            ):
                version = str(release.get("tag_name") or release.get("name") or "").lstrip("vV")
                kind = "portable" if portable else "installer"
                return CompanionAsset(app_key, kind, name, url, version)
    return None


def fetch_companion_asset(
    app_key: str,
    *,
    portable: bool | None = None,
    timeout: int = 10,
    api_url: str | None = None,
) -> CompanionAsset | None:
    """Fetch the releases listing and resolve the sibling's asset for this
    build's flavor. ``portable`` defaults to :func:`updates.running_portable`.
    Returns ``None`` on any network/parse failure (the caller degrades to the
    web release page)."""
    if portable is None:
        portable = updates.running_portable()
    url = api_url or updates.resolve_releases_api_url()
    try:
        request = Request(
            url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "Quill-Updater"},
        )
        with urlopen(request, timeout=timeout, context=updates._ssl_context()) as response:  # noqa: S310 - https-only API URL
            payload = response.read().decode("utf-8")
        return resolve_companion_asset(app_key, json.loads(payload), portable=bool(portable))
    except Exception:  # noqa: BLE001 - discovery failure is non-fatal; caller offers the web page
        return None


@dataclass(frozen=True, slots=True)
class ObtainResult:
    """Outcome of obtaining a companion app."""

    ok: bool
    kind: str  # "installer" | "portable" | ""
    #: For a portable extract, the sibling folder now ready to launch; else "".
    installed_dir: str = ""
    message: str = ""


def obtain_companion(
    asset: CompanionAsset,
    *,
    download_dir: str | os.PathLike[str] | None = None,
    progress: object = None,
) -> ObtainResult:
    """Download the resolved asset and make the sibling runnable.

    installer: download the ``.exe`` and launch it (Windows shows the UAC prompt
    if it requests elevation). The install is user-driven and asynchronous, so
    the caller cannot auto-retry the launch -- it tells the user the installer is
    running. portable: extract the ``.zip`` into an adjacent sibling folder next
    to the current app and return that folder so the caller can retry the launch
    immediately.

    Best-effort and never raises: any failure returns ``ok=False`` with a
    human-readable message.
    """
    try:
        here = Path(sys.executable).resolve().parent
        target = Path(download_dir) if download_dir is not None else here.parent
        target.mkdir(parents=True, exist_ok=True)
        local = target / asset.filename
        cb = progress if callable(progress) else None
        updates.download_release_asset(asset.url, local, progress=cb)  # type: ignore[arg-type]

        if asset.kind == "portable":
            sibling = portable_sibling_dirname(asset.app_key) or asset.app_key
            dest = here.parent  # extract the QuillWeather/ folder beside us
            updates.extract_portable_update(local, dest)
            try:
                local.unlink(missing_ok=True)
            except OSError:
                pass
            return ObtainResult(
                True,
                "portable",
                installed_dir=str(dest / sibling),
                message=f"{app_name(asset.app_key)} is ready.",
            )

        # Installer: hand the verified .exe to the shell so Windows can elevate.
        os.startfile(str(local))  # type: ignore[attr-defined]  # noqa: S606 - our own verified release asset
        return ObtainResult(
            True,
            "installer",
            message=f"The {app_name(asset.app_key)} installer is running. "
            "Follow its prompts, then open the app again.",
        )
    except Exception as exc:  # noqa: BLE001 - obtaining must never crash the caller
        return ObtainResult(
            False, "", message=f"Could not download {app_name(asset.app_key)}: {exc}"
        )


def release_page_url() -> str:
    """The human releases page, for the 'open the website instead' fallback."""
    return "https://github.com/Community-Access/quill/releases"
