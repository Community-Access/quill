"""Stage Node, the language servers and ripgrep for the shared runtime.

Called by :mod:`scripts.fetch_build_deps` as three components; the pins and
the reasons live here so that module stays a dispatcher.

* ``nodejs``: the official Node.js 24.22.1 LTS (Krypton) Windows x64 zip from
  nodejs.org, SHA-256-pinned. Only ``node.exe`` ships (``tools/nodejs``), with
  Node's ``LICENSE`` beside it as ``NODE-LICENSE.txt``: MIT, and its bundled
  parts' licences in the same file (V8, ICU, OpenSSL, libuv, zlib and the
  rest, all permissive; read 2026-11-08). npm, from the same verified zip, is
  kept in the build cache only, to install the servers; it never ships.
* ``language-servers``: ``scripts/language_servers/package.json`` with its
  committed ``package-lock.json``, installed by that npm with ``npm ci
  --ignore-scripts``. Every tarball is checked against the lock's sha512
  ``integrity``, and no package's install script runs. Ships at
  ``tools/language-servers``. The four packages and their licences, read from
  the packages themselves on 2026-11-08: ``vscode-langservers-extracted``
  4.10.0 (MIT; the VS Code HTML, CSS, JSON and Markdown servers),
  ``typescript-language-server`` 6.0.2 (Apache-2.0, with MIT parts copied from
  VS Code), ``typescript`` 6.0.3 (Apache-2.0) and ``pyright`` 1.1.414 (MIT).
  Their 32 dependencies are MIT, ISC or BSD-2-Clause. TypeScript 7 (the native
  rewrite) has no ``tsserver``, which typescript-language-server drives, so it
  waits for a later change (docs/design/intellisense.md).
* ``ripgrep``: ripgrep 15.2.0 for Windows x64 from its GitHub release,
  SHA-256-pinned (the release's own ``.sha256`` file agreed). ``rg.exe`` ships
  at ``tools/ripgrep`` with ``COPYING``, ``LICENSE-MIT`` and ``UNLICENSE``:
  dual Unlicense or MIT. IntelliSense layer 2 uses it to list a project's
  files when it is present.

All three are local at run time: nothing they do reaches the network (the
servers' network features are switched off in quill/core/lsp/servers.py).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from quill.core.release_assets import ReleaseAssetError, download_verified

__all__ = [
    "LANGUAGE_SERVERS_PACKAGES",
    "NODE_VERSION",
    "RIPGREP_VERSION",
    "fetch_language_servers",
    "fetch_nodejs",
    "fetch_ripgrep",
]

NODE_VERSION = "24.22.1"
NODE_ZIP = f"node-v{NODE_VERSION}-win-x64.zip"
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/{NODE_ZIP}"
#: From nodejs.org's SHASUMS256.txt for v24.22.1, and a local download (2026-11-08).
NODE_SHA256 = "d2046d28c2c3dcd211ac5145c0bf30e2047ef9dfb306693c8c6e2eccd8b95fa5"
NODE_LICENSE_NAME = "NODE-LICENSE.txt"

RIPGREP_VERSION = "15.2.0"
RIPGREP_ZIP = f"ripgrep-{RIPGREP_VERSION}-x86_64-pc-windows-msvc.zip"
RIPGREP_URL = (
    f"https://github.com/BurntSushi/ripgrep/releases/download/{RIPGREP_VERSION}/{RIPGREP_ZIP}"
)
#: From the release's own .zip.sha256 file, and a local download (2026-11-08).
RIPGREP_SHA256 = "71b2fef860abe467217a538ff31de02f5258807c0129f771846f87bd029aafc5"
RIPGREP_FILES = ("rg.exe", "COPYING", "LICENSE-MIT", "UNLICENSE")

PACKAGE_DIR = Path(__file__).with_name("language_servers")
#: The four packages, as package.json pins them; tests read this to keep the
#: two in step.
LANGUAGE_SERVERS_PACKAGES = {
    "prettier": "3.9.10",
    "pyright": "1.1.414",
    "typescript": "6.0.3",
    "typescript-language-server": "6.0.2",
    "vscode-langservers-extracted": "4.10.0",
}
LICENSES_SUMMARY = "LANGUAGE-SERVERS-LICENSES.txt"

#: WordPress Playground's command-line tool, for the Practice Site (WordPress
#: PRD 15.1). GPL-2.0-or-later, like WordPress; each package's licence stays in
#: its folder and PLAYGROUND-LICENSES.txt lists them. The pin is the version
#: named in scripts/wp_playground/package.json. Not yet fetched or run: the
#: first fetch writes package-lock.json beside it, which is then committed so
#: later fetches are `npm ci`, as the language servers are.
PLAYGROUND_DIR = Path(__file__).with_name("wp_playground")
PLAYGROUND_PACKAGES = {"@wp-playground/cli": "1.0.28"}
PLAYGROUND_LICENSES = "PLAYGROUND-LICENSES.txt"


def _node_zip(tmp: Path, progress: Callable[[float, str], None] | None) -> zipfile.ZipFile:
    archive = tmp / NODE_ZIP
    download_verified(NODE_URL, archive, sha256=NODE_SHA256, progress=progress)
    return zipfile.ZipFile(archive)


def fetch_nodejs(
    dest: Path, npm_dest: Path, *, progress: Callable[[float, str], None] | None = None
) -> Path:
    """Stage ``node.exe`` and its licence into *dest*, and npm into *npm_dest*."""
    prefix = f"node-v{NODE_VERSION}-win-x64/"
    tmp = Path(tempfile.mkdtemp(prefix="quill-build-dep-"))
    try:
        with _node_zip(tmp, progress) as zf:
            names = set(zf.namelist())
            for needed in ("node.exe", "LICENSE", "node_modules/npm/bin/npm-cli.js"):
                if prefix + needed not in names:
                    raise ReleaseAssetError(f"Unexpected Node archive layout: no {needed}")
            dest.mkdir(parents=True, exist_ok=True)
            part = dest / "node.exe.part"
            part.write_bytes(zf.read(prefix + "node.exe"))
            part.replace(dest / "node.exe")
            (dest / NODE_LICENSE_NAME).write_bytes(zf.read(prefix + "LICENSE"))
            if npm_dest.exists():
                shutil.rmtree(npm_dest)
            npm_prefix = prefix + "node_modules/npm/"
            for name in names:
                if name.startswith(npm_prefix) and not name.endswith("/"):
                    target = npm_dest / name[len(npm_prefix) :]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return dest


def fetch_language_servers(dest: Path, node: Path, npm: Path) -> Path:
    """Install the pinned servers into *dest* with ``npm ci --ignore-scripts``."""
    package = json.loads((PACKAGE_DIR / "package.json").read_text(encoding="utf-8"))
    if package.get("dependencies") != LANGUAGE_SERVERS_PACKAGES:
        raise ReleaseAssetError("scripts/language_servers/package.json drifted from its pins")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copy2(PACKAGE_DIR / name, dest / name)
    command = [
        str(node),
        str(npm / "bin" / "npm-cli.js"),
        "ci",
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
        "--omit=dev",
        "--loglevel=error",
    ]
    result = subprocess.run(  # noqa: S603 - fixed argv, the pinned Node and npm
        command, cwd=dest, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ReleaseAssetError(f"npm ci failed: {result.stderr.strip()[-2000:]}")
    _prune(dest / "node_modules")
    _write_licence_summary(dest)
    return dest


def fetch_wp_playground(dest: Path, node: Path, npm: Path) -> Path:
    """Install the pinned Playground tool into *dest* (``npm ci`` once a lockfile exists)."""
    package = json.loads((PLAYGROUND_DIR / "package.json").read_text(encoding="utf-8"))
    if package.get("dependencies") != PLAYGROUND_PACKAGES:
        raise ReleaseAssetError("scripts/wp_playground/package.json drifted from its pin")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    lock = PLAYGROUND_DIR / "package-lock.json"
    for source in (PLAYGROUND_DIR / "package.json", lock):
        if source.is_file():
            shutil.copy2(source, dest / source.name)
    verb = "ci" if lock.is_file() else "install"
    command = [
        str(node),
        str(npm / "bin" / "npm-cli.js"),
        verb,
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
        "--omit=dev",
        "--loglevel=error",
    ]
    result = subprocess.run(  # noqa: S603 - fixed argv, the pinned Node and npm
        command, cwd=dest, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ReleaseAssetError(f"npm {verb} failed: {result.stderr.strip()[-2000:]}")
    if not lock.is_file() and (dest / "package-lock.json").is_file():
        shutil.copy2(dest / "package-lock.json", lock)  # commit it: later fetches are npm ci
    _prune(dest / "node_modules")
    _write_licence_summary(dest, PLAYGROUND_LICENSES, "WordPress Playground's tool")
    return dest


def _prune(modules: Path) -> None:
    """Drop source maps: debugging aids, a large share of the bytes, never read."""
    for path in modules.rglob("*.map"):
        path.unlink()


def _write_licence_summary(
    dest: Path, name: str = LICENSES_SUMMARY, what: str = "The language servers QUILL runs"
) -> None:
    rows: list[str] = []
    for manifest in sorted((dest / "node_modules").rglob("package.json")):
        holder = manifest.parent.parent
        if holder.name.startswith("@"):
            holder = holder.parent
        if holder.name != "node_modules":
            continue  # a package's own fixtures or nested data, not a package
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or "name" not in data or "version" not in data:
            continue
        licence = data.get("license") or data.get("licenses") or "see the package"
        rows.append(f"{data['name']} {data['version']}: {licence}")
    text = (
        f"{what}, and the licence each package declares.\n"
        "Every package's own licence file is inside its folder under node_modules.\n\n"
        + "\n".join(sorted(set(rows)))
        + "\n"
    )
    (dest / name).write_text(text, encoding="utf-8")


def fetch_ripgrep(dest: Path, *, progress: Callable[[float, str], None] | None = None) -> Path:
    """Stage ``rg.exe`` and its three licence files into *dest*."""
    prefix = f"ripgrep-{RIPGREP_VERSION}-x86_64-pc-windows-msvc/"
    tmp = Path(tempfile.mkdtemp(prefix="quill-build-dep-"))
    try:
        archive = tmp / RIPGREP_ZIP
        download_verified(RIPGREP_URL, archive, sha256=RIPGREP_SHA256, progress=progress)
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
            dest.mkdir(parents=True, exist_ok=True)
            for name in RIPGREP_FILES:
                if prefix + name not in names:
                    raise ReleaseAssetError(f"Unexpected ripgrep archive layout: no {name}")
                (dest / name).write_bytes(zf.read(prefix + name))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return dest
