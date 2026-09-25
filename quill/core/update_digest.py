"""The SHA-256 GitHub publishes beside a release asset.

Split out of :mod:`quill.core.updates` (GATE-11): both the main release reader
and the sibling-app reader need it, and a download is verified only when this
finds a digest to verify against.
"""

from __future__ import annotations

import re

__all__ = ["asset_digest_for_url"]


def asset_digest_for_url(assets: object, url: str) -> str:
    """SHA-256 hex for the asset at *url* from GitHub's ``digest`` field, or ""."""
    if not url or not isinstance(assets, list):
        return ""
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if str(asset.get("browser_download_url") or "") != url:
            continue
        digest = str(asset.get("digest") or "").strip().lower()
        if digest.startswith("sha256:"):
            candidate = digest.split(":", 1)[1]
            if re.fullmatch(r"[0-9a-f]{64}", candidate):
                return candidate
        return ""
    return ""
