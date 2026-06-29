"""Download and stage the optional DECtalk speech runtime.

Split out of :mod:`quill.core.read_aloud` so the read-aloud module stays within
its size budget (GATE-11). The download is verified against a pinned SHA-256
before extraction (SEC-6) and runs with a certifi-aware TLS context.
"""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path

from quill.core.read_aloud import ReadAloudUnavailableError

# Hosted on QUILL's own "assets-v1" GitHub release rather than the upstream
# dectalk release: the byte-identical vs2022.zip is re-published there so the
# on-demand download has a single, controlled, SHA-pinned acquisition point
# (matching the bundled-build pin in scripts/build_windows_distribution.py).
DECTALK_RELEASE_ZIP_URL = (
    "https://github.com/Community-Access/quill/releases/download/assets-v1/vs2022.zip"
)
# SHA-256 of the pinned vs2022.zip release asset, verified before extraction (SEC-6).
DECTALK_RELEASE_ZIP_SHA256 = "4a778056c109b37f95ade4b3d3e308b9396b22a4b0629f9756ec0e5051b9636d"


def download_dectalk_runtime(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / "vs2022.zip"
    from quill.core.net import verified_ssl_context

    with urllib.request.urlopen(  # noqa: S310 - HTTPS URL constant, verified context
        DECTALK_RELEASE_ZIP_URL, timeout=180, context=verified_ssl_context()
    ) as response:
        payload = response.read()
    actual = hashlib.sha256(payload).hexdigest()
    if actual.lower() != DECTALK_RELEASE_ZIP_SHA256.lower():
        raise ReadAloudUnavailableError(
            "Downloaded DECtalk runtime failed its integrity check and was discarded.\n"
            f"  expected: {DECTALK_RELEASE_ZIP_SHA256}\n"
            f"  got:      {actual}"
        )
    archive.write_bytes(payload)
    extract_root = target_dir / "release"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract_root)
    # Return the synthesis runtime (DECtalk.dll), not the graphical speak.exe.
    # speak.exe is the "Sample Speak Window" GUI and cannot synthesize from the
    # command line; QUILL drives DECtalk.dll directly. See
    # quill.core.speech.dectalk_say and discover_dectalk_executable.
    for candidate in (
        extract_root / "AMD64" / "DECtalk.dll",
        extract_root / "DECtalk.dll",
    ):
        if candidate.exists():
            return candidate.resolve()
    raise ReadAloudUnavailableError(
        "Downloaded DECtalk package did not contain DECtalk.dll (the synthesis runtime)."
    )
