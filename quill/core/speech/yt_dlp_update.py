"""Repair YouTube support by fetching the newest yt-dlp wheel -- no pip.

yt-dlp ships inside every build that plays YouTube (pyproject's ``youtube``
group, with ``yt-dlp-ejs`` and the bundled deno that solve YouTube's
JavaScript challenges). This module is the **emergency repair** for the day
YouTube changes its player faster than a release ships: Station > Repair
YouTube Support, or the one-time offer after a stale-component failure. It is
only ever an explicit user action.

It used to run ``python -m pip install``; neither the shared runtime nor the
portable bundle carries pip, so the repair failed exactly where it was needed.
It now talks to PyPI directly:

1. Read ``https://pypi.org/pypi/yt-dlp/json`` for the newest release and its
   pure-Python ``py3-none-any`` wheel (URL on files.pythonhosted.org and the
   SHA-256 PyPI publishes for it).
2. Download that wheel through the hardened
   :func:`quill.core.release_assets.download_verified` path, which verifies
   the SHA-256 before the file is used.
3. Unzip only the ``yt_dlp`` package and its ``.dist-info`` into the engine
   pack. When the new yt-dlp pins a ``yt-dlp-ejs`` whose major.minor differs
   from the bundled one, that wheel is fetched and verified the same way.

A pack copy only ever supersedes the bundled copy when it is **newer**
(:func:`pack_is_newer_than_bundled`); a pack left behind by an older repair,
after an app update shipped a newer yt-dlp, is simply ignored.

wx-free, strict-typed. Split out of ``engine_install`` (GATE-11).
"""

from __future__ import annotations

import importlib.machinery
import importlib.metadata
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from quill.core.error_codes import CodedError

ProgressCallback = Callable[[float, str], None]
#: ``fetch(url) -> bytes`` for the small PyPI JSON documents. Injectable.
Fetch = Callable[[str], bytes]
#: ``download(url, dest, sha256) -> None``; must verify the hash. Injectable.
Download = Callable[[str, Path, str], None]

YT_DLP_DIST = "yt-dlp"
YT_DLP_MODULE = "yt_dlp"
EJS_DIST = "yt-dlp-ejs"
EJS_MODULE = "yt_dlp_ejs"

_PYPI_JSON = "https://pypi.org/pypi/{name}/json"
_PYPI_RELEASE_JSON = "https://pypi.org/pypi/{name}/{version}/json"
_WHEEL_HOSTS = frozenset({"files.pythonhosted.org"})
_MAX_JSON_BYTES = 16 * 1024 * 1024


class YtDlpRepairError(CodedError):
    """Raised when the yt-dlp repair cannot complete."""

    code = "QUILL-SPEECH-YTDLP-REPAIR"


class YtDlpAlreadyCurrent(YtDlpRepairError):
    """The copy in use is already the newest release; nothing was changed."""

    code = "QUILL-SPEECH-YTDLP-CURRENT"


@dataclass(frozen=True)
class Wheel:
    """One pure-Python wheel as PyPI describes it."""

    version: str
    filename: str
    url: str
    sha256: str
    requires: tuple[str, ...] = ()


def version_tuple(text: str) -> tuple[int, ...]:
    """``"2026.08.19"`` -> ``(2026, 8, 19)``; the leading numeric run only.

    yt-dlp versions are dates (with an optional build number), so the numeric
    run is what orders them. ``()`` for anything unreadable, which sorts below
    every real version.
    """
    match = re.match(r"\s*v?(\d+(?:\.\d+)*)", text or "")
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def _dist_prefix(dist: str) -> str:
    return dist.replace("-", "_") + "-"


def pack_version(pack_dir: Path, dist: str = YT_DLP_DIST) -> str:
    """The version of *dist* inside the engine pack, or ``""``.

    Read from the ``.dist-info`` folder name (both pip and this module write
    one), falling back to ``yt_dlp/version.py`` for yt-dlp itself.
    """
    prefix = _dist_prefix(dist)
    try:
        for entry in pack_dir.iterdir():
            name = entry.name
            if name.startswith(prefix) and name.endswith(".dist-info"):
                return name[len(prefix) : -len(".dist-info")]
    except OSError:
        return ""
    if dist == YT_DLP_DIST:
        return _version_from_source(pack_dir / YT_DLP_MODULE / "version.py")
    return ""


def _version_from_source(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"""^__version__\s*=\s*['"]([^'"]+)['"]""", text, re.MULTILINE)
    return match.group(1) if match else ""


def _same_path(a: str, b: Path) -> bool:
    try:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(str(b.resolve()))
    except OSError:
        return False


def bundled_version(pack_dir: Path, dist: str = YT_DLP_DIST, module: str = YT_DLP_MODULE) -> str:
    """The version of the copy the app was built with, ignoring the pack.

    Distribution metadata first (``collect_all`` carries it into the frozen
    runtime; pip installs it into the portable's site-packages); then the
    package's own ``version.py`` found by the path machinery. ``""`` when the
    build carries no copy at all.
    """
    search = [entry for entry in sys.path if not _same_path(entry, pack_dir)]
    for found in importlib.metadata.distributions(name=dist, path=search):
        version = str(found.version or "")
        if version:
            return version
    spec = importlib.machinery.PathFinder.find_spec(module, search)
    if spec is not None and spec.origin:
        return _version_from_source(Path(spec.origin).parent / "version.py")
    return ""


def pack_is_newer_than_bundled(pack_dir: Path) -> bool:
    """Whether the pack's yt-dlp should shadow the bundled copy.

    Only a strictly newer pack wins. A build with no bundled copy uses any
    readable pack (it is the only copy there is).
    """
    pack = version_tuple(pack_version(pack_dir))
    if not pack or not (pack_dir / YT_DLP_MODULE).is_dir():
        return False
    bundled = version_tuple(bundled_version(pack_dir))
    return not bundled or pack > bundled


def _default_fetch(url: str) -> bytes:
    """GET a small PyPI JSON document (a reviewed egress site)."""
    import urllib.request

    from quill.core.net import verified_ssl_context

    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(  # noqa: S310 - fixed https pypi.org URL
        request, timeout=30, context=verified_ssl_context()
    ) as response:
        data: bytes = response.read(_MAX_JSON_BYTES + 1)
    if len(data) > _MAX_JSON_BYTES:
        raise YtDlpRepairError("PyPI sent an unexpectedly large answer.")
    return data


def _default_download(url: str, dest: Path, sha256: str) -> None:
    from quill.core.release_assets import download_verified

    download_verified(url, dest, sha256=sha256, label="Downloading YouTube support...")


def pick_wheel(document: dict[str, object]) -> Wheel:
    """The ``py3-none-any`` wheel out of a PyPI JSON document (pure).

    Refuses anything that is not an https URL on files.pythonhosted.org or
    that lacks a SHA-256: the hash PyPI publishes is what the download is
    checked against.
    """
    info = document.get("info")
    files = document.get("urls")
    if not isinstance(info, dict) or not isinstance(files, list):
        raise YtDlpRepairError("PyPI's answer was not in the expected shape.")
    version = str(info.get("version") or "")
    raw_requires = info.get("requires_dist") or []
    requires = tuple(str(r) for r in raw_requires) if isinstance(raw_requires, list) else ()
    for entry in files:
        if not isinstance(entry, dict) or entry.get("yanked"):
            continue
        filename = str(entry.get("filename") or "")
        if entry.get("packagetype") != "bdist_wheel" or not filename.endswith("-py3-none-any.whl"):
            continue
        url = str(entry.get("url") or "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in _WHEEL_HOSTS:
            raise YtDlpRepairError(f"PyPI offered the wheel from an unexpected address: {url}")
        digests = entry.get("digests")
        sha256 = str(digests.get("sha256") or "") if isinstance(digests, dict) else ""
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise YtDlpRepairError("PyPI published no SHA-256 for the wheel.")
        return Wheel(version, filename, url, sha256, requires)
    raise YtDlpRepairError(f"PyPI lists no pure-Python wheel for version {version or '?'}.")


def ejs_pin(requires: Sequence[str]) -> str:
    """The exact ``yt-dlp-ejs`` a yt-dlp release pins (its ``pin`` extra)."""
    for requirement in requires:
        match = re.match(r"\s*yt-dlp-ejs\s*==\s*([0-9][0-9A-Za-z.]*)\s*;(.*)$", requirement)
        if match and "pin" in match.group(2):
            return match.group(1)
    return ""


def _install_wheel(wheel_file: Path, dest: Path, module: str, dist: str) -> None:
    """Unzip *module* and its dist-info from *wheel_file* into *dest* (atomic-ish).

    Everything else in the wheel (``.data`` man pages, shell completions) is
    left out, and no member may resolve outside the staging folder.
    """
    prefix = _dist_prefix(dist)
    dest.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{module}-", dir=dest))
    try:
        root = staging.resolve()
        with zipfile.ZipFile(wheel_file) as zf:
            for member in zf.infolist():
                top = member.filename.split("/", 1)[0]
                wanted = top == module or (top.startswith(prefix) and top.endswith(".dist-info"))
                if not wanted or member.is_dir():
                    continue
                target = (staging / member.filename).resolve()
                if not target.is_relative_to(root):
                    raise YtDlpRepairError(f"Refusing an unsafe wheel path: {member.filename}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(member))
        if not (staging / module).is_dir():
            raise YtDlpRepairError(f"The downloaded wheel contains no {module} package.")
        _remove_package(dest, module, dist)
        for item in staging.iterdir():
            item.replace(dest / item.name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _remove_package(dest: Path, module: str, dist: str) -> None:
    prefix = _dist_prefix(dist)
    try:
        entries = list(dest.iterdir())
    except OSError:
        return
    for old in entries:
        if old.name == module or (old.name.startswith(prefix) and old.name.endswith(".dist-info")):
            shutil.rmtree(old, ignore_errors=True)


def _fetch_json(fetch: Fetch, url: str) -> dict[str, object]:
    try:
        document = json.loads(fetch(url).decode("utf-8"))
    except YtDlpRepairError:
        raise
    except Exception as exc:  # noqa: BLE001 - one clean, coded message
        raise YtDlpRepairError(f"Could not reach the Python package index: {exc}") from exc
    if not isinstance(document, dict):
        raise YtDlpRepairError("PyPI's answer was not in the expected shape.")
    return document


def repair(
    dest: Path,
    *,
    floor: str,
    progress: ProgressCallback | None = None,
    fetch: Fetch | None = None,
    download: Download | None = None,
) -> str:
    """Install the newest yt-dlp into *dest* when it beats what is in use.

    Returns the version installed. Raises :class:`YtDlpAlreadyCurrent` when
    the bundled (or an earlier repaired) copy is already the newest release,
    and :class:`YtDlpRepairError` for anything that went wrong -- in which case
    the copy in use is untouched.
    """
    get = fetch or _default_fetch
    save = download or _default_download
    if progress is not None:
        progress(0.05, "Checking for the newest YouTube support...")
    wheel = pick_wheel(_fetch_json(get, _PYPI_JSON.format(name=YT_DLP_DIST)))
    newest = version_tuple(wheel.version)
    if newest < version_tuple(floor):
        raise YtDlpRepairError(
            f"PyPI offered yt-dlp {wheel.version}, older than the {floor} this app needs."
        )
    in_use = bundled_version(dest)
    if pack_is_newer_than_bundled(dest):
        in_use = pack_version(dest)
    if in_use and newest <= version_tuple(in_use):
        raise YtDlpAlreadyCurrent(
            f"YouTube support is already the newest version ({in_use}); nothing needed repairing."
        )
    with tempfile.TemporaryDirectory(prefix="quill-yt-dlp-") as tmp:
        if progress is not None:
            progress(0.2, f"Downloading YouTube support {wheel.version}...")
        wheel_file = Path(tmp) / wheel.filename
        save(wheel.url, wheel_file, wheel.sha256)
        pin = ejs_pin(wheel.requires)
        ejs_file: Path | None = None
        if (
            pin
            and version_tuple(bundled_version(dest, EJS_DIST, EJS_MODULE))[:2]
            != (version_tuple(pin)[:2])
        ):
            if progress is not None:
                progress(0.6, "Downloading the matching challenge solver...")
            ejs = pick_wheel(
                _fetch_json(get, _PYPI_RELEASE_JSON.format(name=EJS_DIST, version=pin))
            )
            ejs_file = Path(tmp) / ejs.filename
            save(ejs.url, ejs_file, ejs.sha256)
        if progress is not None:
            progress(0.85, "Installing...")
        _install_wheel(wheel_file, dest, YT_DLP_MODULE, YT_DLP_DIST)
        if ejs_file is not None:
            _install_wheel(ejs_file, dest, EJS_MODULE, EJS_DIST)
        else:
            # The bundled solver matches this yt-dlp: a solver left by an
            # earlier repair would now be the wrong one, so it goes.
            _remove_package(dest, EJS_MODULE, EJS_DIST)
    return wheel.version
