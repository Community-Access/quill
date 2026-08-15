"""Compile the native QuillVille launcher for one product.

Each QuillVille app ships a tiny native ``.exe`` (50-200 KB) compiled from
``quill/native/launcher/``: it locates the shared QuillVille Runtime, downloads
and runs the runtime installer if none is present, and then launches
``pythonw.exe -m <module>``. The alternative -- a stamped copy of
``pythonw.exe`` -- is a pattern antivirus engines flag, which is why the
per-product build scripts refuse to fall back to it.

This wrapper is the piece the per-product builds call. It reads the product's
identity, configures the CMake project once per product, builds Release, and
copies the resulting executable to ``--out``::

    python scripts/build_native_launcher.py --product radio  --out dist\\QuillRadio
    python scripts/build_native_launcher.py --product quill  --out dist\\windows\\portable

**The build is best-effort by design.** With no MSVC or CMake on the machine it
prints what is missing and exits 0 without producing an exe, leaving the caller
to decide whether that is fatal -- and the per-product builds do treat it as
fatal, checking for the exe themselves. Splitting it that way means this script
stays usable on a developer machine with no C toolchain (where a missing
launcher is expected) while a release build still cannot silently ship without
one.

The executable's basename is the product's ``PRODUCT_NAME``, and it must match
what the Inno installer copies (``dist\\QuillRadio\\QuillRadio.exe``) and what
``quill.core.storage_mode`` looks for when deciding a portable install.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LAUNCHER_SRC = _REPO_ROOT / "quill" / "native" / "launcher"

#: The GitHub repo the launcher's in-app updater points at.
_REPO = "Community-Access/quill"


@dataclass(frozen=True, slots=True)
class Product:
    """One launcher build's identity.

    ``name`` is authoritative: it becomes ``PRODUCT_NAME``, the CMake target,
    and therefore the executable filename the installer expects.
    """

    key: str
    name: str
    display: str
    module: str
    #: ``quill/apps/<version_from>.py`` supplies ``_VERSION``; empty means the
    #: product versions with QUILL itself.
    version_from: str = ""
    #: ``standalone/<icon_dir>/assets/<icon_name>.ico``; empty means no icon.
    icon_dir: str = ""
    icon_name: str = ""

    @property
    def app_id(self) -> str:
        """AppUserModelID, for Windows taskbar grouping."""
        return f"CommunityAccess.{self.name}"


PRODUCTS: dict[str, Product] = {
    "radio": Product(
        key="radio",
        name="QuillRadio",
        display="Quill Radio",
        module="quill.apps.radio",
        version_from="radio",
        icon_dir="radio",
        icon_name="quill-radio",
    ),
    "weather": Product(
        key="weather",
        name="QuillWeather",
        display="Quill Weather",
        module="quill.apps.weather",
        version_from="weather",
        icon_dir="weather",
        icon_name="quill-weather",
    ),
    "studio": Product(
        key="studio",
        name="QuillAudioStudio",
        display="QUILL Audio Studio",
        module="quill.apps.studio",
        version_from="studio",
        icon_dir="studio",
        icon_name="quill-audio-studio",
    ),
    "converter": Product(
        key="converter",
        name="QuillConverter",
        display="Quill Converter",
        module="quill.apps.converter",
        version_from="converter",
        icon_dir="converter",
        icon_name="quill-converter",
    ),
    "cast": Product(
        key="cast",
        name="QuillCast",
        display="QUILL Cast",
        module="quill.apps.podcasts",
        icon_dir="cast",
        icon_name="quill-cast",
    ),
    # Main QUILL: the launcher sits at the portable bundle root as quill.exe,
    # which is also the name storage_mode's portable detection looks for.
    "quill": Product(
        key="quill",
        name="quill",
        display="QUILL for All",
        module="quill",
    ),
}


class LauncherToolchainMissing(RuntimeError):
    """No usable C toolchain. Reported, not raised at the user."""


# -- toolchain discovery ------------------------------------------------------


def _vswhere() -> Path | None:
    """Microsoft's own VS locator, installed with any modern VS/Build Tools."""
    for root_var in ("ProgramFiles(x86)", "ProgramFiles"):
        root = os.environ.get(root_var, "").strip()
        if not root:
            continue
        candidate = Path(root) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
        if candidate.is_file():
            return candidate
    return None


def find_msvc() -> Path | None:
    """The install path of a Visual Studio 2022 with the C++ toolset, or None.

    Asks ``vswhere`` for an installation that actually has
    ``VC.Tools.x86.x64`` rather than guessing directory names -- Build Tools
    lands under ``Program Files (x86)`` while the IDE editions land under
    ``Program Files``, and only requiring the component avoids picking a VS
    install that cannot compile C at all.
    """
    locator = _vswhere()
    if locator is None:
        return None
    try:
        result = subprocess.run(
            [
                str(locator),
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
                "-latest",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    path = (result.stdout or "").strip().splitlines()
    return Path(path[0]) if path else None


def _discard_relocated_cmake_cache(build_dir: Path) -> bool:
    """Delete a CMake cache that was generated for a different path.

    CMakeCache.txt records the absolute source and binary directories it was
    configured with, and CMake hard-errors rather than reusing a cache whose
    recorded paths differ ("the current CMakeCache.txt directory ... is
    different than the directory ... where CMakeCache.txt was created"). That
    is exactly what a checkout moved between drives produces: caches written
    when this repo lived on S:\\ stopped every Radio and Weather build on D:\\,
    and because build/ is gitignored the stale files were invisible.

    The cache is a pure build artifact, so discarding it costs one reconfigure.
    Returns True when a stale cache was removed.
    """
    cache = build_dir / "CMakeCache.txt"
    if not cache.is_file():
        return False
    expected = _LAUNCHER_SRC.as_posix().casefold()
    try:
        text = cache.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    # Compared as a whole value rather than as a substring of the file: a cache
    # recording ".../launcher-old" contains ".../launcher", so a substring test
    # keeps a genuinely foreign cache and the build fails with CMake's own
    # error instead -- which is the failure this function exists to prevent.
    recorded = ""
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key.strip().casefold() == "cmake_home_directory:internal":
            recorded = value.strip().casefold()
            break
    if recorded == expected:
        return False
    print(f"Discarding CMake cache configured for another path: {build_dir}")
    shutil.rmtree(build_dir, ignore_errors=True)
    return True


def find_cmake() -> str | None:
    found = shutil.which("cmake")
    if found:
        return found
    for root_var in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(root_var, "").strip()
        if not root:
            continue
        candidate = Path(root) / "CMake" / "bin" / "cmake.exe"
        if candidate.is_file():
            return str(candidate)
    return None


# -- product identity ---------------------------------------------------------


def product_version(product: Product) -> str:
    """The dotted version compiled into the launcher's VERSIONINFO.

    Read from ``quill/apps/<module>.py``'s ``_VERSION`` so a launcher can never
    disagree with the app it starts. Products that version in lockstep with
    QUILL (and any app whose ``_VERSION`` is just ``__version__``) fall through
    to ``quill.__version__``.
    """
    if product.version_from:
        source = _REPO_ROOT / "quill" / "apps" / f"{product.version_from}.py"
        if source.is_file():
            match = re.search(
                r'^_VERSION\s*=\s*["\']([0-9][0-9A-Za-z.\-]*)["\']',
                source.read_text(encoding="utf-8"),
                re.MULTILINE,
            )
            if match:
                return match.group(1)
    sys.path.insert(0, str(_REPO_ROOT))
    from quill import __version__

    return str(__version__)


def product_icon(product: Product) -> Path | None:
    if not product.icon_dir:
        return None
    icon = _REPO_ROOT / "standalone" / product.icon_dir / "assets" / f"{product.icon_name}.ico"
    return icon if icon.is_file() else None


# -- build --------------------------------------------------------------------


def build_launcher(product: Product, out_dir: Path, *, build_root: Path | None = None) -> Path:
    """Configure, build, and stage the launcher. Returns the copied exe path.

    Raises :class:`LauncherToolchainMissing` when MSVC or CMake is absent, so
    the caller can decide whether that is fatal.
    """
    cmake = find_cmake()
    if cmake is None:
        raise LauncherToolchainMissing(
            "CMake 3.20+ was not found. Install it from https://cmake.org/download/ "
            "(or 'winget install Kitware.CMake') and re-run."
        )
    if find_msvc() is None:
        raise LauncherToolchainMissing(
            "Visual Studio 2022 with the C++ workload was not found. Install "
            "'Visual Studio 2022 Build Tools' with 'Desktop development with C++' "
            "(or 'winget install Microsoft.VisualStudio.2022.BuildTools') and re-run."
        )

    version = product_version(product)
    build_dir = (build_root or _REPO_ROOT / "build" / "launcher") / product.key
    _discard_relocated_cmake_cache(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    configure = [
        cmake,
        "-S",
        str(_LAUNCHER_SRC),
        "-B",
        str(build_dir),
        "-G",
        "Visual Studio 17 2022",
        "-A",
        "x64",
        f"-DPRODUCT_NAME={product.name}",
        f"-DPRODUCT_DISPLAY_NAME={product.display}",
        f"-DPRODUCT_VERSION={version}",
        f"-DPRODUCT_PYTHON_MODULE={product.module}",
        f"-DPRODUCT_REPO={_REPO}",
        f"-DPRODUCT_APP_ID={product.app_id}",
    ]
    icon = product_icon(product)
    if icon is not None:
        # Forward slashes: CMake treats a backslash as an escape in -D values.
        configure.append(f"-DPRODUCT_ICON={icon.as_posix()}")

    print(f"  configuring {product.name} {version}")
    subprocess.run(configure, check=True)
    print(f"  building {product.name}")
    subprocess.run([cmake, "--build", str(build_dir), "--config", "Release"], check=True)

    exe_name = f"{product.name}.exe"
    built = build_dir / "Release" / exe_name
    if not built.is_file():  # single-config generators put it at the root
        alternative = build_dir / exe_name
        if alternative.is_file():
            built = alternative
    if not built.is_file():
        raise RuntimeError(f"CMake reported success but {exe_name} is not in {build_dir}.")

    out_dir.mkdir(parents=True, exist_ok=True)
    staged = out_dir / exe_name
    shutil.copy2(built, staged)
    size_kb = staged.stat().st_size // 1024
    print(f"  staged {staged} ({size_kb} KB)")
    return staged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", required=True, choices=sorted(PRODUCTS), help="Product key.")
    parser.add_argument("--out", required=True, type=Path, help="Directory to copy the exe into.")
    parser.add_argument(
        "--require-toolchain",
        action="store_true",
        help="Exit non-zero when the C toolchain is missing instead of skipping.",
    )
    args = parser.parse_args(argv)

    product = PRODUCTS[args.product]
    try:
        build_launcher(product, args.out)
    except LauncherToolchainMissing as exc:
        # Best-effort by design: the caller checks for the exe and decides.
        print(f"Skipping the native launcher for {product.name}: {exc}", file=sys.stderr)
        return 1 if args.require_toolchain else 0
    except subprocess.CalledProcessError as exc:
        print(f"Native launcher build failed for {product.name}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
