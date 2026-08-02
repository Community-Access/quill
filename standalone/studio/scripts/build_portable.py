"""Build a QuillVille app's *portable* bundle -- the self-contained edition
that runs from a USB stick with no install and no shared runtime.

One builder, many products (studio / radio / weather). Layout (mirrors the old
"Lean" bundles, minus the AV-flagged stamped pythonw.exe)::

    <App>/
        <App>.exe                native C launcher (spawns pythonw.exe -m quill.apps.<x>)
        <App>.ico
        python.exe / pythonw.exe genuine, UNMODIFIED CPython embeddable trampolines
        python313.dll / python3.dll / python313.zip / python313._pth
        *.pyd, vcruntime*.dll, libssl-3/libcrypto-3/libffi-8/sqlite3 ...
        Lib/site-packages/       quill dependency closure + the quill source
        data/                    (studio) offline speech/TTS engines
        tools/ffmpeg, tools/mpv  (studio/radio) recording + playback binaries
        docs/

Why this shape, and why NOT a PyInstaller onedir or a stamped pythonw:

* The native launcher needs a real interpreter to spawn. A PyInstaller onedir
  ships *no* python.exe, so on a machine with no shared runtime the launcher
  finds nothing and the portable fails. The embeddable distribution ships
  genuine python.exe / pythonw.exe.
* pythonw.exe is CPython's own one-line GUI-subsystem trampoline
  (PC/WinMain.c: ``wWinMain -> Py_Main``). We ship it byte-for-byte. We do NOT
  rename it to <App>.exe or rcedit-stamp its VERSIONINFO -- that
  repackaged-interpreter shape is exactly what tripped the malware heuristic
  (see docs/design/native-launcher-2026-07-24.md). The QUILL identity lives on
  the tiny, honestly-compiled native launcher instead.

Usage::

    python standalone/studio/scripts/build_portable.py --product studio \
        --out standalone/studio/dist/QuillAudioStudio \
        --source-root . --ffmpeg-dir <dir> --mpv-dir <dir> --version 2.2.0
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

# Pinned embeddable CPython -- kept in lockstep with
# scripts/build_windows_distribution.py::EMBEDDED_PYTHON_* so every QuillVille
# product ships the identical interpreter.
EMBEDDED_PYTHON_VERSION = "3.13.14"
EMBEDDED_PYTHON_URL = (
    f"https://www.python.org/ftp/python/{EMBEDDED_PYTHON_VERSION}/"
    f"python-{EMBEDDED_PYTHON_VERSION}-embed-amd64.zip"
)
EMBEDDED_PYTHON_SHA256 = "90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

_DEV_CACHE_IGNORE = shutil.ignore_patterns(
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", "*.pyc"
)

# Offline speech/TTS engine trees copied from the local Quill app-data folder
# into the portable data/ dir (studio only). Each is skipped when absent.
ENGINE_SUBDIRS = (
    "speech-engine",   # whisper.cpp (the DEFAULT offline transcription engine)
    "speech",          # dectalk, espeak-ng, piper
    "engine-packs",    # kokoro-onnx, mp3-support, mathcat, ... (heavy pruned below)
    "kokoro-models",   # neural TTS model + voices
    "piper-models",    # piper voices
    "speech-models",   # downloaded GGML whisper models
)
# Redundant / very heavy on-demand trees dropped so the bundle stays lean:
# faster-whisper is an alternative ASR to the bundled default (whisper.cpp) and
# drags ~600 MB; engine-packs/mpv duplicates tools/mpv; _vosk-download is
# partial-download scratch. Relative to the portable data/ dir.
ENGINE_PRUNE = (
    "engine-packs/faster-whisper",
    "engine-packs/mpv",
    "engine-packs/_vosk-download",
    "speech-models/fasterwhisper",
    "speech-models/faster-whisper-cache",
)


@dataclass(frozen=True)
class Product:
    key: str            # build_native_launcher.py product key
    module: str         # python -m <module>
    exe: str            # on-disk launcher exe name (no .exe)
    display: str
    zip_name: str       # {ver} placeholder
    dep_groups: tuple[str, ...]
    stage_engines: bool
    stage_ffmpeg: bool
    stage_mpv: bool


PRODUCTS: dict[str, Product] = {
    "studio": Product(
        key="studio",
        module="quill.apps.studio",
        exe="QuillAudioStudio",
        display="QUILL Audio Studio",
        zip_name="QUILL-Audio-Studio-Portable-Lean-{ver}.zip",
        dep_groups=("ui", "speech", "feedback"),
        stage_engines=True,
        stage_ffmpeg=True,
        stage_mpv=True,
    ),
    "radio": Product(
        key="radio",
        module="quill.apps.radio",
        exe="QuillRadio",
        display="Quill Radio",
        zip_name="Quill-Radio-Portable-{ver}.zip",
        dep_groups=("ui", "speech", "feedback"),
        stage_engines=False,   # radio streams/records; no bundled speech engines
        stage_ffmpeg=True,     # podcast/stream recording
        stage_mpv=True,        # playback engine
    ),
    "weather": Product(
        key="weather",
        module="quill.apps.weather",
        exe="QuillWeather",
        display="Quill Weather",
        zip_name="Quill-Weather-Portable-{ver}.zip",
        dep_groups=("ui", "feedback"),  # small app: no media stack
        stage_engines=False,
        stage_ffmpeg=False,
        stage_mpv=False,
    ),
    "converter": Product(
        key="converter",
        module="quill.apps.converter",
        exe="QuillConverter",
        display="Quill Converter",
        zip_name="Quill-Converter-Portable-{ver}.zip",
        # Basic app: the whole job is FFmpeg format conversion, so ffmpeg is
        # staged as a bundled binary (tools/ffmpeg), but no Python media stack,
        # no speech engines, and no playback (mpv) are needed. yt-dlp (URL
        # import) is never bundled -- it installs on demand into the user dir.
        dep_groups=("ui", "feedback"),
        stage_engines=False,
        stage_ffmpeg=True,
        stage_mpv=False,
    ),
    "quill": Product(
        key="quill",
        module="quill",
        exe="quill",
        display="QUILL for All",
        zip_name="QUILL-for-All-Portable-{ver}.zip",
        # The full editor: the complete bundled dependency set QUILL ships.
        dep_groups=("ui", "spellcheck", "ocr", "speech", "feedback", "github"),
        # Engines download on demand (QUILL's standard portable); the fully
        # offline variant is the separate --bundle-offline Offline Edition.
        stage_engines=False,
        stage_ffmpeg=True,   # transcription / media
        stage_mpv=True,      # podcasts / cast playback
    ),
}


def _download(url: str, target: Path, expected_sha256: str | None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    with urllib.request.urlopen(url, timeout=180) as response:  # noqa: S310 - pinned URL
        data = response.read()
    if expected_sha256:
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_sha256:
            raise RuntimeError(
                f"SHA-256 mismatch for {url}\n  expected: {expected_sha256}\n  got:      {digest}"
            )
    target.write_bytes(data)


def _runtime_dependencies(root_pyproject: Path, groups: tuple[str, ...]) -> list[str]:
    """quill's base + the requested optional-group dependency specifiers."""
    with root_pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    project = data.get("project", {})
    deps: list[str] = [d for d in (project.get("dependencies") or []) if isinstance(d, str)]
    optional = project.get("optional-dependencies", {}) or {}
    for group in groups:
        deps.extend(d for d in (optional.get(group) or []) if isinstance(d, str))
    return deps


def _extract_embeddable(out_dir: Path, cache_dir: Path) -> Path:
    archive = cache_dir / f"python-{EMBEDDED_PYTHON_VERSION}-embed-amd64.zip"
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != EMBEDDED_PYTHON_SHA256:
        _download(EMBEDDED_PYTHON_URL, archive, EMBEDDED_PYTHON_SHA256)
    print(f"  extracting embeddable CPython -> {out_dir}")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(out_dir)
    if not (out_dir / "python.exe").is_file() or not (out_dir / "pythonw.exe").is_file():
        raise RuntimeError("Embeddable zip did not contain python.exe / pythonw.exe")
    return out_dir / "python.exe"


def _enable_site_packages(out_dir: Path) -> None:
    pth_files = list(out_dir.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError("Embeddable Python missing its ._pth file")
    zip_name = next(out_dir.glob("python*.zip")).name
    pth_files[0].write_text(
        f"{zip_name}\n.\nLib\\site-packages\nimport site\n", encoding="utf-8"
    )


def _pip(python_exe: Path, *args: str) -> None:
    subprocess.run([str(python_exe), "-m", "pip", *args], check=True)


def _bootstrap_pip_and_deps(
    python_exe: Path, root_pyproject: Path, groups: tuple[str, ...]
) -> None:
    get_pip = python_exe.parent / "get-pip.py"
    _download(GET_PIP_URL, get_pip, expected_sha256=None)
    print("  bootstrapping pip")
    subprocess.run([str(python_exe), str(get_pip), "--no-warn-script-location"], check=True)
    get_pip.unlink(missing_ok=True)
    _pip(python_exe, "install", "--no-warn-script-location", "--no-compile", "setuptools")
    deps = _runtime_dependencies(root_pyproject, groups)
    print(f"  installing {len(deps)} runtime dependencies")
    _pip(python_exe, "install", "--no-warn-script-location", "--no-compile", *deps)


def _copy_quill_source(out_dir: Path, source_root: Path) -> None:
    site_packages = out_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    if (site_packages / "quill").exists():
        shutil.rmtree(site_packages / "quill")
    quill_source = source_root / "quill"
    if not quill_source.is_dir():
        raise RuntimeError(f"quill/ package source not found under {source_root}")
    print(f"  copying quill source -> Lib/site-packages/quill")
    shutil.copytree(quill_source, site_packages / "quill", ignore=_DEV_CACHE_IGNORE)
    token = site_packages / "quill" / "_feedback_token.py"
    if not token.is_file():
        raise RuntimeError(
            "quill/_feedback_token.py missing -- generate the feedback token first "
            "(build_release.ps1 does this via tools/generate_feedback_token.py)."
        )
    match = re.search(
        r"""^BUNDLED_TOKEN\s*=\s*['"]([^'"]*)['"]""",
        token.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match or not match.group(1):
        raise RuntimeError("Bundled feedback token is empty -- refusing to ship.")


def _prune_build_only(out_dir: Path) -> None:
    site_packages = out_dir / "Lib" / "site-packages"
    for name in ("setuptools", "pkg_resources", "_distutils_hack", "wheel"):
        target = site_packages / name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
    for pat in ("setuptools-*", "wheel-*"):
        for dist in site_packages.glob(pat):
            shutil.rmtree(dist, ignore_errors=True)
    # setuptools' distutils-precedence.pth imports _distutils_hack (just removed)
    # at every interpreter start -- drop it or every launch prints a traceback.
    (site_packages / "distutils-precedence.pth").unlink(missing_ok=True)


def _build_native_launcher(out_dir: Path, source_root: Path, product: Product) -> None:
    build_script = source_root / "scripts" / "build_native_launcher.py"
    print(f"  building native launcher ({product.exe}.exe)")
    subprocess.run(
        [sys.executable, str(build_script), "--product", product.key, "--out", str(out_dir)],
        check=True,
    )
    if not (out_dir / f"{product.exe}.exe").is_file():
        raise RuntimeError(
            f"Native launcher build produced no {product.exe}.exe. Install MSVC 2022 "
            "Build Tools (C++ workload) + CMake 3.20+; the portable must NOT fall "
            "back to a stamped pythonw.exe (the AV-flagged pattern)."
        )


def _stage_engines(out_dir: Path, engines_dir: Path) -> list[str]:
    data_dir = out_dir / "data"
    data_dir.mkdir(exist_ok=True)
    staged: list[str] = []
    prune_names = {Path(p).name for p in ENGINE_PRUNE}

    def _ignore(dir_path: str, names: list[str]) -> set[str]:
        ignored = set(_DEV_CACHE_IGNORE(dir_path, names))
        ignored |= {n for n in names if n in prune_names}
        return ignored

    for sub in ENGINE_SUBDIRS:
        src = engines_dir / sub
        if src.is_dir():
            print(f"  staging engine tree data/{sub}")
            shutil.copytree(src, data_dir / sub, dirs_exist_ok=True, ignore=_ignore)
            staged.append(sub)
    for rel in ENGINE_PRUNE:
        target = data_dir / rel
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
    return staged


def _write_portable_marker(out_dir: Path, display: str) -> None:
    data_dir = out_dir / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "storage-mode.json").write_text('{"mode": "portable"}', encoding="utf-8")
    (data_dir / "README.txt").write_text(
        f"This folder makes {display} portable: your settings and data live here,\n"
        "right next to the app, so the whole thing travels on a stick with no\n"
        "install. Delete this folder and the app uses the shared Quill data in your\n"
        "Windows profile instead.\n",
        encoding="utf-8",
    )


def _stage_tools(out_dir: Path, product: Product, ffmpeg_dir: Path | None, mpv_dir: Path | None) -> None:
    if product.stage_ffmpeg and ffmpeg_dir:
        dest = out_dir / "tools" / "ffmpeg"
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("ffmpeg.exe", "ffprobe.exe"):
            if (ffmpeg_dir / name).is_file():
                print(f"  staging tools/ffmpeg/{name}")
                shutil.copy2(ffmpeg_dir / name, dest / name)
        lic = ffmpeg_dir.parent / "LICENSE"
        if lic.is_file():
            shutil.copy2(lic, dest / "FFMPEG-LICENSE.txt")
    if product.stage_mpv and mpv_dir:
        dest = out_dir / "tools" / "mpv"
        dest.mkdir(parents=True, exist_ok=True)
        if (mpv_dir / "libmpv-2.dll").is_file():
            print("  staging tools/mpv/libmpv-2.dll")
            shutil.copy2(mpv_dir / "libmpv-2.dll", dest / "libmpv-2.dll")
        for txt in mpv_dir.glob("*.txt"):
            shutil.copy2(txt, dest / txt.name)


def _stage_docs(out_dir: Path, product: Product, source_root: Path) -> None:
    # Main QUILL's docs live at repo docs/; the standalone apps keep their own
    # under standalone/<key>/docs.
    if product.key == "quill":
        docs_src = source_root / "docs"
        readme = source_root / "README.md"
    else:
        docs_src = source_root / "standalone" / product.key / "docs"
        readme = source_root / "standalone" / product.key / "README.md"
    if docs_src.is_dir():
        dest = out_dir / "docs"
        dest.mkdir(exist_ok=True)
        for item in docs_src.iterdir():
            if item.is_file() and item.suffix.lower() in (".md", ".html", ".epub", ".txt"):
                shutil.copy2(item, dest / item.name)
    if readme.is_file():
        shutil.copy2(readme, out_dir / f"README-{product.exe}.md")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--product", required=True, choices=list(PRODUCTS))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--ffmpeg-dir", type=Path, default=None)
    parser.add_argument("--mpv-dir", type=Path, default=None)
    parser.add_argument(
        "--engines-dir",
        type=Path,
        default=Path(os.environ.get("APPDATA", "")) / "Quill",
        help="Local Quill app-data dir to source offline engine trees from (studio).",
    )
    parser.add_argument("--version", default="2.2.0")
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument(
        "--no-runtime",
        action="store_true",
        help=(
            "Build the tiny 'Companion' variant: native launcher + docs + "
            "per-app engines only, with NO embedded Python/Lib. It runs off the "
            "shared QuillVille Runtime the native launcher resolves at "
            "%%LOCALAPPDATA%%\\QuillVille\\Runtime (installed once, reused by "
            "every app). Drops ~900 MB vs the full self-contained bundle."
        ),
    )
    args = parser.parse_args()

    product = PRODUCTS[args.product]
    out_dir = args.out.resolve()
    source_root = args.source_root.resolve()
    cache_dir = (args.cache_dir or (out_dir.parent / "_build-tools")).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    if out_dir.exists():
        print(f"Cleaning existing {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    if args.no_runtime:
        print(f"[1/6] Companion (runtime-less) build for {product.display}")
        print("      no embedded Python -- runs off the shared QuillVille Runtime")
    else:
        print(f"[1/8] Embeddable CPython ({product.display})")
        python_exe = _extract_embeddable(out_dir, cache_dir)
        _enable_site_packages(out_dir)

        print(f"[2/8] pip + runtime dependencies {product.dep_groups}")
        _bootstrap_pip_and_deps(python_exe, source_root / "pyproject.toml", product.dep_groups)

        print("[3/8] quill package source")
        _copy_quill_source(out_dir, source_root)
        _prune_build_only(out_dir)

    print(f"[{'2/6' if args.no_runtime else '4/8'}] native launcher")
    _build_native_launcher(out_dir, source_root, product)

    if args.no_runtime:
        # Companion: ffmpeg/mpv come from the shared runtime's tools\ (found via
        # QUILL_APP_ROOT); speech engines download on demand into %APPDATA%\Quill.
        # So we stage neither -- only the portable-mode marker + docs. That is
        # what keeps the Companion feather-light.
        print("[3/6] portable marker (no bundled engines/tools -- shared runtime provides them)")
        _write_portable_marker(out_dir, product.display)
        print("[4/6] docs/")
        _stage_docs(out_dir, product, source_root)
    else:
        print("[5/8] offline engines -> data/")
        if product.stage_engines:
            staged = _stage_engines(out_dir, args.engines_dir)
            print(f"      staged: {', '.join(staged) if staged else '(none found)'}")
        else:
            print("      (product ships no bundled engines)")
        _write_portable_marker(out_dir, product.display)

        print("[6/8] tools/ (ffmpeg, mpv)")
        _stage_tools(out_dir, product, args.ffmpeg_dir, args.mpv_dir)

        print("[7/8] docs/")
        _stage_docs(out_dir, product, source_root)

    print(f"[{'6/6' if args.no_runtime else '8/8'}] sanity check")
    if not (out_dir / f"{product.exe}.exe").is_file():
        raise RuntimeError(f"Bundle missing native {product.exe}.exe launcher")
    if args.no_runtime:
        # No interpreter is bundled; the launcher resolves the shared runtime.
        # Leave a human-readable note so the layout is self-explanatory.
        (out_dir / "READ-ME-FIRST.txt").write_text(
            f"{product.display} -- Companion edition\n\n"
            "This is the lightweight edition. It does NOT include its own copy of\n"
            "Python; it runs on the shared QuillVille Runtime that any QuillVille\n"
            "app installs once. If the runtime is not present the first time you\n"
            f"launch {product.display}, it will offer to download and install it\n"
            "(about 230 MB, once) -- after that every QuillVille app starts\n"
            "instantly. To stay fully offline instead, use the full portable\n"
            "edition, which bundles everything.\n",
            encoding="utf-8",
        )
        zip_name = product.zip_name.format(ver=args.version).replace(
            "-Portable", "-Companion"
        ).replace("-Lean", "")
        print(f"\nCompanion bundle ready: {out_dir}")
        print(f"(zip as: {zip_name})")
        return 0
    if not (out_dir / "pythonw.exe").is_file():
        raise RuntimeError("Bundle missing genuine pythonw.exe")
    check = subprocess.run(
        [str(out_dir / "python.exe"), "-c",
         f"import quill, wx; import {product.module}; print('OK', quill.__version__)"],
        capture_output=True, text=True,
    )
    print("      runtime import check:", (check.stdout or check.stderr).strip().splitlines()[-1:])
    if check.returncode != 0:
        raise RuntimeError(
            f"Bundled runtime failed to import {product.module}:\n" + (check.stderr or "")
        )

    print(f"\nPortable bundle ready: {out_dir}")
    print(f"(zip as: {product.zip_name.format(ver=args.version)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
