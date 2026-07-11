"""Optional in-app Node.js LTS runtime download for Node Quillins (#669 follow-up).

QUILL does not bundle a Node.js runtime. For users who want to run Node Quillins
but don't have Node.js on their PATH, this downloads the **official Node.js LTS
build** on an explicit action and extracts ``node.exe`` into the QUILL-managed
tools folder (``<app data>/tools/node``).

The binary comes straight from nodejs.org; QUILL never redistributes it.

Safety mirrors the ffmpeg download path: HTTPS-only with a verified TLS context,
blocked in Safe Mode, on an explicit user action only. Windows-only — on macOS
and Linux the system package manager (Homebrew / apt) is the right tool. wx-free.

Probe order in :func:`node_executable_path`:
1. QUILL-managed path (``<app data>/tools/node/node.exe``)
2. System PATH (``shutil.which("node")``)

Existing installs with Node on PATH are unaffected; the managed path is a
fallback for users who never needed Node before installing a Node Quillin.
"""

from __future__ import annotations

import os
import shutil
import ssl
import sys
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.paths import app_data_dir

ProgressCallback = Callable[[float, str], None]

#: LTS major stream. Bump this constant (and update the rebaseline comment below)
#: when moving to a new Node.js LTS stream — e.g. 20 → 22 when Node 20 reaches
#: end-of-life. The download always fetches the latest patch in this stream.
NODE_LTS_MAJOR = 20

_SHASUMS_URL = f"https://nodejs.org/dist/latest-v{NODE_LTS_MAJOR}.x/SHASUMS256.txt"
_DOWNLOAD_TIMEOUT_S = 1800.0


class NodeInstallError(CodedError):
    """Raised when the optional Node.js runtime download or extraction fails."""

    code = "QUILL-QUILLIN-NODE-INSTALL"


def node_install_supported() -> bool:
    """True where QUILL can download a managed Node.js runtime (Windows only)."""
    return sys.platform == "win32"


def managed_node_dir() -> Path:
    """The folder a managed node.exe is extracted into (resolver-searched)."""
    return app_data_dir() / "tools" / "node"


def bundled_node_dir() -> Path | None:
    """The Offline Edition's bundled Node under ``{app}/tools/nodejs``, or None.

    None when no ``QUILL_APP_ROOT`` is set (a source/dev run, or a slim install
    that fetches Node on demand). The Offline Edition stages the official Node
    build here so the resolver finds it without internet or a managed download.
    """
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if not app_root:
        return None
    return Path(app_root) / "tools" / "nodejs"


def node_executable_path() -> Path | None:
    """Return the node executable to use, or None if Node is not available.

    Probe order:
    1. QUILL-managed path (``<app data>/tools/node/node.exe``)
    2. Bundled Offline Edition copy (``{app}/tools/nodejs/node.exe``)
    3. System PATH (``shutil.which("node")``)
    """
    managed = managed_node_dir() / "node.exe"
    if managed.is_file():
        return managed
    bundled = bundled_node_dir()
    if bundled is not None and (bundled / "node.exe").is_file():
        return bundled
    found = shutil.which("node")
    return Path(found) if found else None


def is_node_available() -> bool:
    """True when a usable Node.js executable can be found (managed or system)."""
    return node_executable_path() is not None


def install_node_runtime(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    timeout_seconds: float = _DOWNLOAD_TIMEOUT_S,
) -> Path:
    """Download and extract the Node.js LTS runtime, returning the node.exe path.

    Raises :class:`NodeInstallError` on Safe Mode, unsupported platform, network
    error, or a bad archive. After this returns, :func:`node_executable_path`
    finds the managed binary immediately.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise NodeInstallError("Downloading the Node.js runtime is disabled in Safe Mode.")
    if not node_install_supported():
        raise NodeInstallError(
            "Automatic Node.js download is Windows-only. On macOS install it with "
            "Homebrew (brew install node); on Linux use your package manager."
        )
    dest = Path(dest_dir) if dest_dir is not None else managed_node_dir()
    dest.mkdir(parents=True, exist_ok=True)

    if progress is not None:
        progress(0.02, "Checking for the latest Node.js LTS release...")
    zip_url = _fetch_node_zip_url(timeout_seconds)

    fd, raw = tempfile.mkstemp(prefix="quill_node_", suffix=".zip")
    os.close(fd)
    tmp_zip = Path(raw)
    try:
        if progress is not None:
            progress(0.1, "Downloading Node.js runtime (this may take a minute)...")
        _download_node_zip(zip_url, tmp_zip, progress, timeout_seconds)
        if progress is not None:
            progress(0.92, "Extracting node.exe...")
        node_path = _extract_node_from_zip(tmp_zip, dest)
    finally:
        tmp_zip.unlink(missing_ok=True)

    if progress is not None:
        progress(1.0, "Done.")
    return node_path


def _fetch_node_zip_url(timeout_seconds: float) -> str:
    """Fetch SHASUMS256.txt from nodejs.org to discover the current win-x64 zip filename.

    GATE-9 / network-egress: fetches a small text file (~5 KB) over verified
    HTTPS. Runs only on an explicit user "download Node" action; no user data sent.
    """
    context = ssl.create_default_context()
    req = urllib.request.Request(_SHASUMS_URL, headers={"User-Agent": "QUILL"})
    try:
        with urllib.request.urlopen(  # noqa: S310 - HTTPS: _SHASUMS_URL is a hardcoded constant
            req, timeout=timeout_seconds, context=context
        ) as response:
            shasums_text = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        raise NodeInstallError(f"Could not fetch the Node.js release index: {exc}") from exc
    return _resolve_zip_url_from_shasums(shasums_text)


def _resolve_zip_url_from_shasums(shasums_text: str) -> str:
    """Parse SHASUMS256.txt and return the win-x64 zip download URL."""
    base = _SHASUMS_URL.rsplit("/", 1)[0]
    for line in shasums_text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].endswith("-win-x64.zip"):
            return f"{base}/{parts[1]}"
    raise NodeInstallError(
        f"Could not find a win-x64 zip in the Node.js v{NODE_LTS_MAJOR} release index. "
        "The index may have an unexpected format."
    )


def _download_node_zip(
    url: str,
    target: Path,
    progress: ProgressCallback | None,
    timeout_seconds: float,
) -> None:
    """Stream the Node.js zip over verified HTTPS.

    GATE-9 / network-egress: the large outbound call in this module. Refuses
    non-HTTPS URLs; uses a verified TLS context. A progress callback that raises
    (user cancel) aborts the download.
    """
    if not url.lower().startswith("https://"):
        raise NodeInstallError("Node.js download must use a secure (HTTPS) address.")
    context = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "QUILL"})
    try:
        with (
            urllib.request.urlopen(  # noqa: S310 - HTTPS enforced above
                req, timeout=timeout_seconds, context=context
            ) as response,
            target.open("wb") as out,
        ):
            total = int(response.headers.get("Content-Length", 0) or 0)
            read = 0
            while True:
                chunk = response.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                read += len(chunk)
                if progress is not None and total > 0:
                    frac = 0.1 + (read / total) * 0.8
                    progress(min(frac, 0.9), "Downloading Node.js runtime...")
    except NodeInstallError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise NodeInstallError(f"Could not download Node.js: {exc}") from exc


def _extract_node_from_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract node.exe from an official Node.js Windows zip, returning its path.

    Official Windows zips nest the binary under ``node-vX.Y.Z-win-x64/``; we
    match on the basename and write it flat into ``dest_dir``.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                base = member.rsplit("/", 1)[-1].lower()
                if base == "node.exe":
                    out_path = dest_dir / "node.exe"
                    with zf.open(member) as src, out_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    return out_path
    except zipfile.BadZipFile as exc:
        raise NodeInstallError("The downloaded Node.js archive was not a valid zip.") from exc
    raise NodeInstallError("node.exe was not found in the downloaded archive.")
