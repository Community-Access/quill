"""Build a Windows distribution of Quill.

Outputs under ``windows-distribution/``:

* ``portable/`` — the runnable bundle (launcher, manifest, README, the
  Quill package source, and optionally an embedded Python runtime with
  all required wheels pre-installed).
* ``installer/quill.iss`` — an Inno Setup script that turns the portable
  bundle into a polished Windows installer (per-user by default, Start
  Menu shortcut, optional Desktop shortcut, optional Open-With entries,
  proper Add/Remove Programs metadata).

The ``--bundle-python`` flag downloads the official Windows embeddable
Python distribution and pre-installs ``wxPython`` and ``pyttsx3`` into
it, so end users do **not** need to install Python or pip themselves.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import textwrap
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from quill.core.shell_verbs import ShellVerb, default_shell_verbs
from quill.core.storage import write_json_atomic

# Product-name fallback. The canonical source is build/version.toml; this
# constant from quill.branding is the safety default when the TOML is
# absent or missing the ``product_name`` field.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from quill.branding import APP_DISPLAY_NAME, APP_ORGANIZATION  # noqa: E402

# Architecture note: all bundled binaries below are amd64/x86_64.  The Inno
# Setup script uses ArchitecturesAllowed=x64compatible, which covers both
# genuine x64 hardware and ARM64 Windows (Snapdragon / Surface Pro X), where
# Windows runs x64 binaries under hardware emulation transparently.  Native
# ARM64 builds are not produced because none of the three speech engines
# (DECtalk, Piper, eSpeak-NG) ship ARM64 Windows binaries.  Revisit when any
# of them do: Python (embed-arm64.zip), Pandoc, and Node all have arm64 assets.

# A contributor's local dev-tool caches (mypy/pytest/ruff, stray bytecode)
# must never leak into a shipped build -- they're sizable, irrelevant to end
# users, and only present because *this* machine happened to run those tools.
_DEV_CACHE_IGNORE = shutil.ignore_patterns(
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"
)


def _bundled_token_value(path: Path) -> str:
    """Read ``quill/_feedback_token.py``'s ``BUNDLED_TOKEN`` without importing quill.

    The build runs under a bare embedded interpreter with the QUILL source not
    yet on ``sys.path``, so it must not import the app it is packaging. Parse the
    module text instead. Returns the token string, or "" when the file is absent
    or has no ``BUNDLED_TOKEN = "..."`` assignment (the empty-token case the
    build refuses to ship).
    """
    if not path.is_file():
        return ""
    match = re.search(
        r"""^BUNDLED_TOKEN\s*=\s*['"]([^'"]*)['"]""", path.read_text("utf-8"), re.MULTILINE
    )
    return match.group(1) if match else ""


def _assert_bundled_token_nonempty(site_packages: Path) -> None:
    """Refuse to ship a tokenless distributable, unconditionally.

    Guards the true end-user invariant -- the ``_feedback_token.py`` inside the
    bundled ``quill/`` package that Report a Bug reads at runtime (via
    ``quill.core.feedback_token._bundled_token``) -- against any path that bakes
    an empty token or fails to copy it into the bundle. This is the exact
    "upgrade beta 2 and get No token" symptom (#919), locked out. There is no
    opt-out: every build must bake a real token.
    """
    bundled_token_file = site_packages / "quill" / "_feedback_token.py"
    if not bundled_token_file.is_file():
        raise RuntimeError(
            "Bundled quill/_feedback_token.py is missing from the runtime -- the "
            "feedback-hub token never made it into the distributable. A build must "
            "always bake the QUILL_FEEDBACK_GITHUB_TOKEN; there is no opt-out (#919)."
        )
    if not _bundled_token_value(bundled_token_file):
        raise RuntimeError(
            "Bundled quill/_feedback_token.py has an empty BUNDLED_TOKEN -- the "
            "distributable would ship a broken Report a Bug (no GitHub token). Set "
            "QUILL_FEEDBACK_GITHUB_TOKEN before building; there is no opt-out (#919)."
        )


# Pinned Windows embeddable Python. Bumping these values is the only
# thing needed to ship on a new Python point release.
EMBEDDED_PYTHON_VERSION = "3.13.14"
EMBEDDED_PYTHON_URL = (
    f"https://www.python.org/ftp/python/{EMBEDDED_PYTHON_VERSION}/"
    f"python-{EMBEDDED_PYTHON_VERSION}-embed-amd64.zip"
)
# SHA-256 of the official embeddable zip. If python.org rotates the file
# the build will fail loudly rather than ship an unverified runtime.
EMBEDDED_PYTHON_SHA256 = "90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907"

DECTALK_RELEASE_ZIP_URL = (
    "https://github.com/dectalk/dectalk/releases/download/2023-10-30/vs2022.zip"
)
DECTALK_RELEASE_ZIP_SHA256 = "4a778056c109b37f95ade4b3d3e308b9396b22a4b0629f9756ec0e5051b9636d"

# Pinned Pandoc Windows release. _download_and_stage_pandoc() tries the
# latest GitHub release first and falls back to these if the API is unreachable.
PANDOC_PINNED_VERSION = "3.10"
PANDOC_PINNED_URL = (
    "https://github.com/jgm/pandoc/releases/download/3.10/pandoc-3.10-windows-x86_64.zip"
)
PANDOC_PINNED_SHA256 = "bb808d00fd58762299d64582a9b4c3e4b106cd929e62c5f19bcdcb496f1e54ae"

# Pinned eSpeak-NG Windows release. _download_and_stage_espeak() tries the
# latest GitHub release first and falls back to these if the API is unreachable.
ESPEAK_PINNED_VERSION = "1.52.0"
ESPEAK_PINNED_URL = "https://github.com/espeak-ng/espeak-ng/releases/download/1.52.0/espeak-ng.msi"
ESPEAK_PINNED_SHA256 = "7f673c709ea5dd579d3b5ebb98688cc575328a6ab7438d2bc405b88cedaeafb9"

# Piper is no longer bundled by the installer (PRD 10.2.x footprint unbundle):
# fresh installs download the engine + voice on demand from the Voice Picker, so
# there is no build-time Piper staging and no pinned Piper release to track here.

# Pinned whisper.cpp Windows release. _download_and_stage_whisper() tries the
# latest GitHub release first and falls back to these if the API is unreachable.
# The plain CPU x64 zip ships whisper-cli.exe (under Release/) alongside its
# whisper.dll / ggml*.dll dependencies -- the offline speech engine (#617, #742).
# whisper.cpp is the DEFAULT offline transcription/dictation provider, so unlike
# the other speech engines it MUST ship: the build raises rather than producing
# an installer whose selected "speechwhisper" component has no payload.
WHISPERCPP_PINNED_URL = (
    "https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-bin-x64.zip"
)
WHISPERCPP_PINNED_SHA256 = "7d8be46ecd31828e1eb7a2ecdd0d6b314feafd82163038ab6092594b0a063539"

# Kokoro neural-TTS model + voices. Always STAGED into the portable bundle under
# kokoro-models/, but the INSTALLER gates the copy behind the optional
# "speechkokoro" component (Types: full custom) -- so Full installs still ship it
# while Custom installs can drop ~120 MB; the generic ..\portable\* copy excludes
# kokoro-models\* to avoid installing it unconditionally. The runtime resolves
# {app}\kokoro-models (quill.core.read_aloud._bundled_kokoro_model_dir) and, when
# skipped, downloads on demand to %APPDATA%\Quill\kokoro-models, which it prefers
# over the bundled copy (default_kokoro_model_dir). The filenames mirror
# KOKORO_ONNX_MODEL_FILENAME / KOKORO_ONNX_VOICES_FILENAME in read_aloud.py; keep
# them in sync. _stage_kokoro downloads + SHA-256 verifies these unless a local
# --kokoro-dir is provided.
KOKORO_MODEL_FILENAME = "kokoro-v1.0.int8.onnx"
KOKORO_VOICES_FILENAME = "voices-v1.0.bin"
KOKORO_MODEL_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
    "model-files-v1.0/kokoro-v1.0.int8.onnx"
)
KOKORO_MODEL_SHA256 = "6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb"
KOKORO_VOICES_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
)
KOKORO_VOICES_SHA256 = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"

# GLOW is hidden for 0.5.0 (the core.glow feature is locked off), so the heavy
# `glow` extra (quill-glow-core[glow], not yet on a public index) is NOT bundled
# in the shipping build. The vendored contract wheel (see _install_vendored_glow)
# still installs the safe GLOW seam. Re-add "glow" here when GLOW is re-enabled
# and its wheels are published.
# "speech" bundles sounddevice (PortAudio) so offline dictation works out of the
# box (#617) without a separate pip install. The whisper.cpp engine itself is a
# separate InnoSetup component (tools/speech/whispercpp), not a pip wheel.
# Vosk (the very-low-resource CPU-only offline engine, #669) is NOT bundled: at
# ~51 MB of self-contained wheel (it ships libvosk) it is the single largest optional
# engine, and it is not the default (whisper.cpp is). Like Faster Whisper it downloads
# on demand into a user-writable engine pack (quill/core/speech/engine_install.install_vosk,
# activated on sys.path) via Tools > Speech > Download Vosk, so the base installer no
# longer carries it. Its ~40 MB model still downloads on demand via Manage Speech Models.
# The default whisper.cpp engine is itself already on-demand (~8 MB, excluded from the
# installer in quill.iss and fetched via release_assets / the dictation pre-flight), so no
# offline engine is bundled -- the installer stays small and the first offline use fetches
# the tiny default in-flow.
# "feedback" bundles feedback_hub (direct GitHub issue submission) so Report a
# Bug offers the accessible Submit flow instead of the browser support form.
# "kokoro" is intentionally NOT bundled: kokoro-onnx pulls in onnxruntime (large),
# phonemizer, espeakng-loader and babel. Kokoro is an on-demand feature -- its
# models already download on first use, and install_kokoro_onnx() pip-installs the
# package tree into an engine-pack (activated on sys.path), so bundling it just
# bloated the installer. Keeping it out trims the installer substantially and lets
# babel arrive with the on-demand install (#881). See the guided-installer spec.
DEFAULT_BUNDLED_DEPENDENCY_GROUPS = ("ui", "spellcheck", "ocr", "speech", "feedback")

# Pinned rcedit release (electron/rcedit). Build-tool only -- never copied into
# the portable bundle or the installer payload. Used to stamp the bundled
# launcher's VERSIONINFO so JAWS's Ctrl+JAWSKey+V (which reads the foreground
# window's owning .exe, not the window title) reports "QUILL for All" instead
# of the embeddable Python runtime's own "Python 3.x.x" (issue #615).
RCEDIT_PINNED_VERSION = "2.0.0"
RCEDIT_PINNED_URL = (
    f"https://github.com/electron/rcedit/releases/download/v{RCEDIT_PINNED_VERSION}/rcedit-x64.exe"
)
RCEDIT_PINNED_SHA256 = "3e7801db1a5edbec91b49a24a094aad776cb4515488ea5a4ca2289c400eade2a"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate portable and Inno Setup packaging artefacts for Windows.",
    )
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--output-dir", type=Path, default=Path("windows-distribution"))
    parser.add_argument(
        "--bundle-python",
        action="store_true",
        help=(
            "Download an embedded Python runtime and install wxPython/pyttsx3 "
            "into the portable bundle so end users do not need Python."
        ),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("."),
        help="Repository root that contains the quill/ package source to ship.",
    )
    parser.add_argument(
        "--pandoc-dir",
        type=Path,
        default=None,
        help="Optional local Pandoc directory to bundle under portable\\tools\\pandoc.",
    )
    parser.add_argument(
        "--dectalk-dir",
        type=Path,
        default=None,
        help="Optional local DECtalk runtime directory to bundle under portable\\tools\\speech\\dectalk.",
    )
    parser.add_argument(
        "--espeak-dir",
        type=Path,
        default=None,
        help="Optional local eSpeak-NG runtime directory to bundle under portable\\tools\\speech\\espeak-ng.",
    )
    parser.add_argument(
        "--kokoro-dir",
        type=Path,
        default=None,
        help=(
            "Optional local directory holding the Kokoro model files "
            "(kokoro-v1.0.int8.onnx, voices-v1.0.bin) to stage under "
            "portable\\kokoro-models. When omitted the files are downloaded from "
            "the pinned kokoro-onnx release and SHA-256 verified."
        ),
    )
    parser.add_argument(
        "--whisper-dir",
        type=Path,
        default=None,
        help=(
            "Optional local whisper.cpp directory (containing whisper-cli.exe and its "
            "DLLs) to bundle under portable\\tools\\speech\\whispercpp for the offline "
            "speech engine (#617). Installed via the 'speechwhisper' component."
        ),
    )
    parser.add_argument(
        "--braille-pack-dir",
        type=Path,
        default=None,
        help=(
            "Local braille pack directory (containing lou_translate.exe, tables/, "
            "brf_profiles.json) to bundle under portable\\vendor\\braille-pack. "
            "Defaults to liblouis/vendor/braille/pack relative to the source root. "
            "Run scripts/build_braille_pack.py first to generate the catalog and profiles."
        ),
    )
    parser.add_argument(
        "--compile-installer",
        action="store_true",
        help="Compile the generated Inno Setup script into an installer executable.",
    )
    parser.add_argument(
        "--require-feedback-token",
        action="store_true",
        help=(
            "Accepted for backward compatibility (the CI release workflow passes "
            "it) but now a NO-OP: the feedback-hub token is ALWAYS required. A "
            "distributable must never ship a broken Report a Bug, so a build with "
            "an unset QUILL_FEEDBACK_GITHUB_TOKEN always fails. There is no opt-out "
            "(#919: beta-2 upgrades shipped a tokenless bug reporter)."
        ),
    )
    parser.add_argument(
        "--iscc-path",
        type=Path,
        default=None,
        help="Optional explicit path to ISCC.exe for installer compilation.",
    )
    args = parser.parse_args()

    bundle = build_windows_distribution(
        args.pyproject,
        args.output_dir,
        bundle_python=args.bundle_python,
        source_root=args.source_root,
        braille_pack_dir=args.braille_pack_dir,
        bundled_tool_dirs={
            tool_id: path
            for tool_id, path in {
                "pandoc": args.pandoc_dir,
                "speech/dectalk": args.dectalk_dir,
                "speech/espeak-ng": args.espeak_dir,
                "speech/whispercpp": args.whisper_dir,
            }.items()
            if path is not None
        },
        kokoro_dir=args.kokoro_dir,
        compile_installer=args.compile_installer,
        iscc_path=args.iscc_path,
    )
    print(f"Wrote portable bundle to {bundle['portable_dir']}")
    print(f"Wrote installer template to {bundle['installer_script']}")
    if bundle.get("python_runtime"):
        print(f"Bundled embedded Python to {bundle['python_runtime']}")
    if bundle.get("installer_exe"):
        print(f"Built installer executable at {bundle['installer_exe']}")
    return 0


def build_windows_distribution(
    pyproject: Path,
    output_dir: Path,
    bundle_python: bool = False,
    source_root: Path | None = None,
    bundled_tool_dirs: dict[str, Path] | None = None,
    kokoro_dir: Path | None = None,
    braille_pack_dir: Path | None = None,
    compile_installer: bool = False,
    iscc_path: Path | None = None,
) -> dict[str, str]:
    identity = _build_identity(pyproject.parent)
    version = identity.display_version
    resolved_source_root = source_root or Path(".")
    portable_dir = output_dir / "portable"
    installer_dir = output_dir / "installer"
    reference_installer_dir = pyproject.parent / "installer"
    portable_dir.mkdir(parents=True, exist_ok=True)
    installer_dir.mkdir(parents=True, exist_ok=True)
    reference_installer_dir.mkdir(parents=True, exist_ok=True)

    # The portable bundle ships a ``data/`` folder so the install is recognised
    # as portable from first launch with zero setup. ``data/`` is the user's
    # deliberate opt-in: a folder with quill.exe but no data/ is not portable
    # (see quill.core.storage_mode._has_portable_evidence). The keep-file makes
    # the folder non-empty so it survives zipping/unzipping -- many archivers
    # drop empty directories, which would silently break portable detection.
    data_dir = portable_dir / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "README.txt").write_text(
        "This folder holds your QUILL data when you choose portable mode on first\n"
        "run (settings, keymap, and documents you keep here). It ships empty; QUILL\n"
        "fills it the first time you opt into portable storage. Keeping this folder\n"
        "next to quill.exe is what marks this bundle as portable -- do not delete\n"
        "it.\n",
        encoding="utf-8",
    )

    staged_docs = _stage_distribution_docs(portable_dir, resolved_source_root)
    effective_bundled_tools = dict(bundled_tool_dirs or {})
    # Pandoc, Piper, Node.js, and the braille pack are NO LONGER bundled, and the
    # installer no longer ships or prompts for any of them (footprint unbundle,
    # PRD 10.2.x -- completing the 10.2.4 sweep that already dropped whisper.cpp,
    # Kokoro, DECtalk, and eSpeak-NG). Fresh installs fetch each on demand from
    # its verified source: Pandoc via quill/core/pandoc_install.py on the first
    # conversion, Piper via the Voice Picker (quill.core.read_aloud /
    # download_piper_exe), Node.js via quill/core/node_install.py, and the braille
    # pack via download_braille_pack (Help > Download Optional Components). A dev
    # build may still stage a local Pandoc/DECtalk/eSpeak/whisper copy with the
    # matching --*-dir flag, but that only populates the portable bundle -- the
    # installer ships none of them.
    # whisper.cpp, DECtalk, and eSpeak-NG are NO LONGER bundled by default
    # (PRD 10.2.4 unbundle): fresh installs download them on demand from QUILL's
    # pinned, SHA-256-verified "assets-v1" release, and offline speech offers the
    # download at point of use. SAPI 5 remains the always-present offline floor.
    # A build may still stage a local copy by passing --whisper-dir / --dectalk-dir
    # / --espeak-dir (populates effective_bundled_tools above, staged below).
    # Upgraders keep their existing copies ([InstallDelete] does not touch them).
    bundled_tools = _stage_bundled_tools(portable_dir, effective_bundled_tools)
    # Kokoro is NO LONGER bundled by default (PRD 10.2.4 unbundle): fresh installs
    # download it on demand from QUILL's pinned, SHA-256-verified release asset, and
    # the runtime prefers the %APPDATA% copy. A build may still opt to stage a local
    # copy into the portable bundle by passing --kokoro-dir. Upgraders keep their
    # existing {app}/kokoro-models (Inno never removes it).
    if kokoro_dir is not None:
        _stage_kokoro(portable_dir, kokoro_dir)

    readme = portable_dir / "README.txt"
    readme.write_text(
        _render_readme(
            version,
            bundle_python,
            product_name=identity.product_name,
            publisher=identity.publisher,
            bundled_tools=bundled_tools,
            staged_docs=staged_docs,
        ),
        encoding="utf-8",
    )

    manifest_path = portable_dir / "manifest.json"
    manifest = {
        "project": "quill",
        "productName": identity.product_name,
        "version": version,
        "baseVersion": identity.base_version,
        "channel": identity.channel,
        "prereleaseNumber": identity.prerelease_number,
        "publisher": identity.publisher,
        "portableEntry": str(portable_dir / "quill.exe"),
        "installerScript": str(installer_dir / "quill.iss"),
        "bundledPython": bool(bundle_python),
        "embeddedPythonVersion": EMBEDDED_PYTHON_VERSION if bundle_python else None,
        "bundledTools": bundled_tools,
        "docs": [str(path.relative_to(portable_dir)) for path in staged_docs],
        "speechAssets": _speech_asset_manifest(portable_dir, bundled_tools),
    }
    write_json_atomic(manifest_path, manifest)

    braille_pack_staged = _stage_braille_pack(
        portable_dir, braille_pack_dir, source_root=resolved_source_root
    )

    iss_numeric_version = _iss_numeric_version(
        identity.base_version, identity.channel, identity.prerelease_number
    )
    installer_script = installer_dir / "quill.iss"
    reference_installer_script = reference_installer_dir / "quill.iss"
    installer_script_text = build_inno_setup_script(
        version=version,
        product_name=identity.product_name,
        publisher=identity.publisher,
        bundle_braille_pack=braille_pack_staged,
        numeric_version=iss_numeric_version,
    )
    installer_script.write_text(installer_script_text, encoding="utf-8")
    reference_installer_script.write_text(installer_script_text, encoding="utf-8")

    installer_readme = build_installer_readme(version, identity)
    (installer_dir / "README-installer.txt").write_text(installer_readme, encoding="utf-8")
    (reference_installer_dir / "README-installer.txt").write_text(
        installer_readme, encoding="utf-8"
    )

    # Copy LICENSE into the installer dir so ISCC can resolve "LicenseFile=LICENSE"
    # regardless of where output_dir sits relative to the repo root.
    repo_license = resolved_source_root / "LICENSE"
    if repo_license.exists():
        shutil.copy2(repo_license, installer_dir / "LICENSE")

    python_runtime_dir: Path | None = None
    if bundle_python:
        staged_runtime = bundle_embedded_python(
            portable_dir / "python",
            source_root=resolved_source_root,
            pyproject=pyproject,
            identity=identity,
            launcher_file_version=iss_numeric_version,
            build_cache_dir=output_dir / "_build-tools",
        )
        # Flatten the runtime to the bundle root. quill.exe (a VERSIONINFO-stamped
        # pythonw.exe) can only bootstrap when its python313.dll/zip/_pth sit next
        # to it; nesting them in python\ orphaned the root quill.exe (#722). With
        # the runtime at the root, double-clicking quill.exe loads its own
        # interpreter and the sitecustomize self-run hook starts QUILL -- no
        # python\, no -m, no console, no .cmd. The runtime ships none of the
        # already-staged bundle entries (data/docs/tools/vendor/kokoro-models/
        # manifest.json/README.txt), so the move cannot clobber them; a future
        # collision fails loudly rather than overwriting. The full launcher
        # contract is documented in docs/design/portable-launcher.md.
        for entry in sorted(staged_runtime.iterdir()):
            dest = portable_dir / entry.name
            if dest.exists():
                raise RuntimeError(
                    f"Embedded-runtime file {entry.name!r} collides with a staged "
                    f"bundle entry at {dest}; flatten would clobber it."
                )
            shutil.move(str(entry), str(dest))
        staged_runtime.rmdir()
        python_runtime_dir = portable_dir

    result = {
        "portable_dir": str(portable_dir),
        "installer_script": str(installer_script),
        "reference_installer_script": str(reference_installer_script),
    }
    if python_runtime_dir is not None:
        result["python_runtime"] = str(python_runtime_dir)
    if compile_installer:
        installer_exe = compile_inno_setup_installer(
            installer_script,
            version=version,
            iscc_path=iscc_path,
        )
        result["installer_exe"] = str(installer_exe)
    return result


# The sitecustomize.py written next to the bundled quill.exe. Auto-imported at
# interpreter startup (the embeddable runtime's python<ver>._pth enables site),
# it makes quill.exe both self-running (bare double-click) and file-association
# aware, so quill.exe never needs "-m quill", a console window, or a .cmd shim.
# See docs/design/portable-launcher.md.
_SELF_RUN_SITECUSTOMIZE = '''\
"""Launcher hook for the bundled quill.exe (build-generated).

Auto-imported at startup because the embeddable runtime's python<ver>._pth
enables site. See docs/design/portable-launcher.md.
"""
import os
import sys


def _is_quill_exe():
    return os.path.basename(sys.executable).lower() == "quill.exe"


def _bare_launch():
    # A bare double-click gives the no-script interactive argv: [''] (or empty).
    return len(sys.argv) <= 1 and (not sys.argv or sys.argv[0] == "")


def _associated_file():
    # The OS opened a document with quill.exe (a renamed pythonw.exe): pythonw
    # treats the document path as the "script" in sys.argv[0]. Return it so we
    # open it in QUILL instead of letting Python run the document as code.
    # Skipped for `quill.exe -m quill ...`, where argv[0] is quill's __main__.py.
    if not sys.argv:
        return None
    first = sys.argv[0]
    if not first or os.path.basename(first).lower() == "__main__.py":
        return None
    return first if os.path.isfile(first) else None


def _run(paths):
    try:
        sys.argv = ["quill", *paths]
        from quill.__main__ import main

        main()
    except SystemExit:
        raise
    except BaseException:
        import traceback

        traceback.print_exc()
    finally:
        os._exit(0)


if _is_quill_exe():
    if _bare_launch():
        _run([])
    else:
        _doc = _associated_file()
        if _doc is not None:
            _run([_doc])
'''


def _self_run_sitecustomize_source() -> str:
    """The sitecustomize.py that makes quill.exe self-running and
    file-association aware (docs/design/portable-launcher.md). A bare
    double-click launches QUILL; opening a document with quill.exe set as the
    default app forwards that document to QUILL instead of letting pythonw try
    to run it as a script. ``python.exe``, ``pip``, and ``quill.exe -m quill``
    take the no-op path and behave normally.
    """
    return _SELF_RUN_SITECUSTOMIZE


def _render_readme(
    version: str,
    bundle_python: bool,
    *,
    product_name: str,
    publisher: str,
    bundled_tools: list[str],
    staged_docs: list[Path],
) -> str:
    if bundle_python:
        runtime_paragraph = (
            "This bundle ships a private Python runtime in the python\\ folder,\n"
            "so you do NOT need to install Python, pip, wxPython, or anything\n"
            "else. Just double-click quill.exe and start writing."
        )
    else:
        runtime_paragraph = (
            "This bundle does not include a Python runtime. To run it,\n"
            "install Python 3.12+ from https://www.python.org/downloads/windows/\n"
            "and run:  pip install wxPython pyttsx3\n"
            "Then double-click quill.exe."
        )

    docs_paragraph = ""
    if staged_docs:
        docs_paragraph = (
            "\nIncluded guides:\n"
            "- docs\\userguide.md - the full guided user manual\n"
            "Internal engineering docs are published on the Quill GitHub Pages site\n"
            "instead of being bundled in the installer.\n"
        )
    bundled_tools_paragraph = ""
    if bundled_tools:
        bundled_tools_paragraph = (
            "\nBundled external tools:\n"
            + "\n".join(f"- {tool_id}" for tool_id in bundled_tools)
            + (
                "\nQuill can also detect additional tools installed system-wide "
                "and guide users through what they unlock.\n"
            )
        )

    return (
        textwrap.dedent(
            f"""
            {product_name} Portable {version}
            Publisher: {publisher}

            {runtime_paragraph}

            Quill is a screen-reader-first writing, reading, review, and document-intelligence
            environment for Windows. It is designed to stay calm on the keyboard while still
            giving power users deep navigation, structured editing, comparison, GLOW review,
            diagnostics, and optional external-tool workflows.

            Optional tool onboarding is built into Quill itself. If Pandoc, Tesseract OCR,
            or other supported tools are installed or bundled, Quill explains what they unlock
            and offers guided touch points such as the Pandoc Conversion Wizard.

            {bundled_tools_paragraph}{docs_paragraph}

            On first run, Quill asks whether to store its data in your
            Windows AppData folder (default) or alongside this bundle
            (portable mode). Choose portable if you are running Quill from
            a USB stick or a managed work laptop where AppData is volatile.

            To rebuild the installer from this portable bundle, open
            installer\\quill.iss in Inno Setup 6.
            """
        ).strip()
        + "\r\n"
    )


def build_shell_verb_registry_lines(
    verbs: tuple[ShellVerb, ...] | list[ShellVerb] | None = None,
) -> list[str]:
    """Return Inno ``[Registry]`` lines for the "Send to Quill" verbs (SHELL-3).

    Driven entirely by :func:`quill.core.shell_verbs.default_shell_verbs` so the
    installer, the runtime registry writer
    (``quill/platform/windows/shell_integration.py``), the CLI ``--action`` map,
    and the Settings toggles can never drift. Each verb is registered per file
    extension under
    ``Software\\Classes\\SystemFileAssociations\\<ext>\\shell\\Quill.<verb_id>``
    so QUILL appears in the file right-click menu without owning the file's
    default association. Every key is gated behind the opt-in ``shellverbs`` task
    and tagged ``uninsdeletekey`` so a full uninstall removes the verbs cleanly.

    The launch command is ``"{app}\\{#AppExeName}" -m quill --action <action>
    "%1"``. quill.exe is the bundled launcher (a stamped copy of pythonw.exe);
    the ``-m quill`` is required so pythonw runs QUILL with the verb and file as
    arguments rather than trying to execute the selected file as a script, and
    the file path and verb then reach the same dispatch as the in-app menu.
    """

    selected = tuple(verbs) if verbs is not None else default_shell_verbs()
    lines: list[str] = []
    for verb in selected:
        key_name = f"Quill.{verb.verb_id}"
        label = verb.label.replace('"', '""')
        # Inno escapes a literal double-quote inside a string value as "".
        command = f'"""{{app}}\\{{#AppExeName}}"" -m quill --action {verb.action} ""%1"""'
        for extension in verb.extensions:
            base = f"Software\\Classes\\SystemFileAssociations\\{extension}\\shell\\{key_name}"
            lines.append(
                f'Root: HKCU; Subkey: "{base}";'
                f' ValueType: string; ValueName: ""; ValueData: "{label}";'
                " Flags: uninsdeletekey; Tasks: shellverbs"
            )
            lines.append(
                f'Root: HKCU; Subkey: "{base}";'
                f' ValueType: string; ValueName: "MUIVerb"; ValueData: "{label}";'
                " Tasks: shellverbs"
            )
            lines.append(
                f'Root: HKCU; Subkey: "{base}\\command";'
                f' ValueType: string; ValueName: ""; ValueData: {command};'
                " Tasks: shellverbs"
            )
    return lines


def build_installer_readme(version: str, identity: BuildIdentity) -> str:
    """Return the post-install info page shown by the full installer.

    Deliberately separate from portable\\README.txt which targets users
    running Quill from a USB stick or without an installer.
    """
    return (
        f"{identity.product_name} {version} — Windows Installer\r\n"
        f"Publisher: {identity.publisher}\r\n"
        "\r\n"
        "Thank you for installing Quill.\r\n"
        "\r\n"
        "WHERE YOUR DATA LIVES\r\n"
        "Quill stores settings, autosaves, dictionaries, and session data in:\r\n"
        "  %APPDATA%\\Quill\r\n"
        "\r\n"
        "This folder is separate from the install directory. On uninstall you are\r\n"
        "asked whether to remove it; upgrades never touch it automatically.\r\n"
        "\r\n"
        "GETTING STARTED\r\n"
        "  * Launch Quill from the Start Menu or the Desktop shortcut (if you chose one).\r\n"
        "  * Press F1 or open Help > User Guide for the full guided manual.\r\n"
        "  * An onboarding flow runs on first launch to introduce key features.\r\n"
        "\r\n"
        "OPTIONAL TOOLS\r\n"
        "Tools selected during setup (DECtalk, eSpeak-NG, Piper TTS, Pandoc, Braille Pack)\r\n"
        "are bundled inside the install directory and require no separate installation.\r\n"
        "To add or remove tools, re-run this installer and choose Modify.\r\n"
        "\r\n"
        "PORTABLE EDITION\r\n"
        "A portable build (no installer, runs from a USB stick or managed machine) is\r\n"
        "available from the Quill releases page on GitHub.\r\n"
        "\r\n"
        "SUPPORT\r\n"
        "  https://github.com/Community-Access/quill\r\n"
    )


def build_inno_setup_script(
    version: str,
    *,
    product_name: str = APP_DISPLAY_NAME,
    publisher: str = APP_ORGANIZATION,
    bundle_braille_pack: bool = False,
    numeric_version: str | None = None,
) -> str:
    """Return a production-quality Inno Setup script for the portable bundle.

    The script is assembled line-by-line to avoid the f-string + triple-
    quote pitfalls of templating Inno (which uses ``""`` as its own
    quote-escape) inside a Python triple-quoted string.

    ``product_name`` and ``publisher`` come from ``build/version.toml``
    (via :func:`_build_identity`) so the installer's Add/Remove Programs
    metadata, Start Menu shortcut, and About dialog never drift apart.
    """

    lines: list[str] = [
        "; Generated by scripts/build_windows_distribution.py",
        "; Edit build_inno_setup_script(), not this file, to change packaging.",
        "",
        f'#define AppName "{product_name}"',
        f'#define AppVersion "{version}"',
        f'#define AppPublisher "{publisher}"',
        '#define AppURL "https://github.com/Community-Access/quill"',
        '#define AppExeName "quill.exe"',
        "",
        "[Setup]",
        "AppId={{6E0A1C52-4A90-4C6E-A8A1-3C2A16E2B7F2}",
        "AppName={#AppName}",
        "AppVersion={#AppVersion}",
        "AppPublisher={#AppPublisher}",
        "AppPublisherURL={#AppURL}",
        "AppSupportURL={#AppURL}",
        "AppUpdatesURL={#AppURL}",
        # Inno Setup's VersionInfoVersion directive requires a numeric
        # quadruple (Major.Minor.Build.Revision) for the Windows VERSIONINFO
        # resource; the user-visible "0.7.0 Beta 1" string cannot be
        # parsed. Default to <base>.0.0 if the caller did not pass an
        # explicit numeric_version.
        f"VersionInfoVersion={numeric_version or '0.0.0.0'}",
        "VersionInfoCompany={#AppPublisher}",
        "VersionInfoDescription={#AppName} accessible writing environment",
        "DefaultDirName={autopf}\\{#AppName}",
        "DefaultGroupName={#AppName}",
        "DisableDirPage=no",
        "DisableProgramGroupPage=auto",
        "AllowNoIcons=yes",
        "PrivilegesRequired=lowest",
        "PrivilegesRequiredOverridesAllowed=dialog",
        "; The bundle ships the amd64 embedded Python runtime, so refuse to",
        "; install it on a non-x64-compatible CPU and place it in the real",
        "; 64-bit Program Files (not the x86 folder). x64compatible also covers",
        "; ARM64 Windows, which runs the x64 runtime under emulation.",
        "; (Requires Inno Setup 6.3 or newer.)",
        "ArchitecturesAllowed=x64compatible",
        "ArchitecturesInstallIn64BitMode=x64compatible",
        "; Quill targets Windows 10 and 11: the zero-install OCR backend, winget",
        "; Node bootstrap, and modern wxPython all assume Windows 10+.",
        "MinVersion=10.0",
        "; The file-association and Send-to-Quill tasks write Explorer keys, so",
        "; tell Windows to refresh association/icon caches after install.",
        "ChangesAssociations=yes",
        f"OutputBaseFilename=Quill-for-All-Setup-{version}",
        "Compression=lzma2/ultra",
        "SolidCompression=yes",
        "WizardStyle=modern",
        "; Force-close any processes that lock app files before copying new ones.",
        "; This avoids silent upgrade failures on in-use binaries.",
        "CloseApplications=force",
        "RestartApplications=no",
        "UninstallDisplayName={#AppName} {#AppVersion}",
        "; The bundled launcher carries a real icon so Add/Remove Programs",
        "; shows one. BundledLauncherPath (see [Code]) is {app}\\quill.exe -- a",
        "; VERSIONINFO-stamped copy of pythonw.exe (see _stamp_quill_launcher)",
        "; that sits next to the flattened embedded runtime -- then plain",
        "; pythonw.exe, and gracefully returns blank when no bundled runtime",
        "; is present (e.g. a dev build), in which case no icon is shown.",
        "UninstallDisplayIcon={code:BundledLauncherPath}",
        "LicenseFile=LICENSE",
        "InfoAfterFile=README-installer.txt",
        "SetupLogging=yes",
        "",
        "[Languages]",
        'Name: "english"; MessagesFile: "compiler:Default.isl"',
        "",
        "[Tasks]",
        'Name: "fileassoc"; Description: "Register Quill in the Open With menu'
        ' for common text formats (.txt, .md, .rst, .log, .csv, .json)";'
        ' GroupDescription: "File associations:"; Flags: unchecked',
        'Name: "shellverbs"; Description: "Add ""Send to Quill"" actions'
        ' (OCR, Open, Read aloud) to the file right-click menu";'
        ' GroupDescription: "File associations:"; Flags: unchecked',
        "",
        "; No [Types] or [Components] section: every optional component is fetched",
        "; on demand from its verified source, so the installer shows no setup-type",
        "; or component-selection page at all. Pandoc, Piper, Node.js, the braille",
        "; pack, whisper.cpp, Kokoro, DECtalk, and eSpeak-NG all download at point",
        "; of use (PRD 10.2.x footprint unbundle). Quill's core -- the Writing",
        "; Assistant and everything else -- ships unconditionally in the main",
        "; bundle below.",
        "",
        "[InstallDelete]",
        "; Upgrade hygiene -- the single most important fix for reliable upgrades.",
        "; Inno only overlays the new [Files] on top of an existing install; it",
        "; never removes files the new build no longer ships. So a first-party",
        "; module renamed, moved, or deleted between releases (and any stale",
        "; __pycache__) would otherwise linger next to the new code and cause the",
        "; ImportError / AttributeError version-skew crashes we hit on upgrade.",
        ";",
        "; Scope this to exactly what changes release-to-release and is the proven",
        "; risk: our own 'quill' package. Wiping it before [Files] re-lays it makes",
        "; every install a clean, self-consistent copy of our code, while leaving",
        "; the embedded Python runtime and third-party site-packages in place --",
        "; those keep stable module names, are overwritten as needed by the",
        "; ignoreversion [Files] entry, and re-extracting the whole runtime every",
        "; upgrade would only make installs slow for no safety gain. Bundled",
        "; tools/voices/braille live under {app}\\tools and {app}\\vendor; user",
        "; documents live in %APPDATA%\\Quill -- neither is touched here.",
        'Type: filesandordirs; Name: "{app}\\Lib\\site-packages\\quill"',
        'Type: filesandordirs; Name: "{app}\\__pycache__"',
        "; Upgrade cleanup (flat layout). A pre-flatten install kept the embedded",
        "; runtime under {app}\\python with an orphaned root quill.exe. The runtime",
        "; now lives flattened in {app}, so installing this build OVER an old nested",
        "; install must wipe the stale {app}\\python tree -- Inno only overlays new",
        "; [Files] and never removes it, so it would otherwise linger forever as",
        "; orphaned cruft (~150 MB, and a second dead quill.exe). It holds no user",
        "; data (that is %APPDATA%\\Quill or {app}\\data), so this is always safe;",
        "; on a clean or already-flat install the dir is absent and this is a no-op.",
        'Type: filesandordirs; Name: "{app}\\python"',
        "; NOTE: user CONFIG in %APPDATA%\\Quill (settings.json, keymap.json,",
        "; features.json) is intentionally NOT deleted here. Those stores now",
        "; carry forward safely across releases -- each is a delta of the user's",
        "; overrides stamped with a schema version, so changed/added defaults",
        "; reach the user automatically while their customizations are preserved,",
        "; and a pre-migration backup is written before any one-time conversion",
        "; (see quill.core.settings_migration / keymap.merge_keymaps). An earlier",
        "; beta reset these on every install for a clean slate; that is no longer",
        "; needed now that migration protects the data.",
        "",
        "[Files]",
        'Source: "..\\portable\\*"; DestDir: "{app}";'
        " Flags: ignoreversion recursesubdirs createallsubdirs;"
        ' Excludes: "docs\\QUILL-PRD.md,tools\\pandoc\\*,tools\\speech\\dectalk\\*,tools\\speech\\espeak-ng\\*,tools\\speech\\piper\\*,tools\\speech\\whispercpp\\*,tools\\nodejs\\*,vendor\\braille-pack\\*,kokoro-models\\*,_tool-download\\*,_speech-download\\*,*\\__pycache__\\*"',
        "; Only Quill's core bundle is installed. Every optional component --",
        "; Pandoc, Piper, Node.js, the braille pack, whisper.cpp, Kokoro, DECtalk,",
        "; and eSpeak-NG -- is fetched on demand to %APPDATA%\\Quill (verified,",
        "; pinned release assets or official builds), which the app's resolvers",
        "; prefer. The Excludes above keep any locally staged copy (from a --*-dir",
        "; dev build) out of the shipped installer; [InstallDelete] never touches",
        "; an upgrader's existing {app} copies.",
        "",
        "[Icons]",
        'Name: "{group}\\{#AppName}"; Filename: "{code:BundledLauncherPath}"; Parameters: "-m quill"; WorkingDir: "{app}"; Check: HasBundledLauncher',
        'Name: "{group}\\{#AppName}"; Filename: "{app}\\{#AppExeName}"; WorkingDir: "{app}"; Check: not HasBundledLauncher',
        'Name: "{group}\\{#AppName} README"; Filename: "{app}\\README.txt"',
        ('Name: "{group}\\{#AppName} User Guide"; Filename: "{app}\\docs\\userguide.html"'),
        'Name: "{group}\\Uninstall {#AppName}"; Filename: "{uninstallexe}"',
        'Name: "{autodesktop}\\{#AppName}"; Filename: "{code:BundledLauncherPath}"; Parameters: "-m quill";'
        ' WorkingDir: "{app}"; Check: HasBundledLauncher',
        'Name: "{autodesktop}\\{#AppName}"; Filename: "{app}\\{#AppExeName}";'
        ' WorkingDir: "{app}"; Check: not HasBundledLauncher',
        "",
        "[Registry]",
        "; Register Quill in the OpenWithList for common text formats. We",
        "; never overwrite the user's chosen default app for any extension.",
        # Inno uses "" as an escaped quote inside a string; we feed it via
        # Python str.format-style concatenation to keep the file readable.
        (
            "Root: HKCU;"
            ' Subkey: "Software\\Classes\\Applications\\{#AppExeName}\\shell\\open\\command";'
            ' ValueType: string; ValueName: "";'
            ' ValueData: """{app}\\{#AppExeName}"" -m quill ""%1""";'
            " Flags: uninsdeletekey; Tasks: fileassoc"
        ),
    ]
    for extension in (".txt", ".md", ".rst", ".log", ".csv", ".json"):
        lines.append(
            f'Root: HKCU; Subkey: "Software\\Classes\\{extension}\\OpenWithList\\{{#AppExeName}}";'
            " Flags: uninsdeletekey; Tasks: fileassoc"
        )
    lines += [
        "",
        '; "Send to Quill" file right-click verbs (SHELL-3). Generated from',
        "; quill.core.shell_verbs so the installer, runtime registry writer, CLI",
        "; --action map, and Settings toggles stay in lockstep. Opt-in via the",
        "; shellverbs task; uninsdeletekey removes them on uninstall.",
    ]
    lines += build_shell_verb_registry_lines()
    lines += [
        "",
        "[Run]",
        'Filename: "{app}\\README.txt"; Description: "View the Quill README";'
        " Flags: postinstall shellexec skipifsilent unchecked",
        'Filename: "{app}\\docs\\userguide.html";'
        ' Description: "View the User Guide";'
        " Flags: postinstall shellexec skipifsilent unchecked",
        'Filename: "{code:BundledLauncherPath}"; Parameters: "-m quill"; Description: "Launch {#AppName}";'
        " Flags: postinstall nowait skipifsilent unchecked; Check: HasBundledLauncher",
        'Filename: "{app}\\{#AppExeName}"; Description: "Launch {#AppName}";'
        " Flags: postinstall nowait skipifsilent unchecked; Check: not HasBundledLauncher",
        "",
        "[UninstallDelete]",
        "; Always remove install-dir build junk. Whether to also remove the",
        "; user's data in %APPDATA%\\Quill is decided by an explicit prompt in",
        "; [Code] below -- we never silently keep or wipe it.",
        'Type: filesandordirs; Name: "{app}\\__pycache__"',
        "; {app}\\Lib is the bundled embedded runtime's library tree: wholly owned",
        "; by Quill, no user data lives there (that's %APPDATA%\\Quill). Python",
        "; generates __pycache__ dirs across Lib\\site-packages on first run (the",
        "; build uses --no-compile), and those nest arbitrarily deep, so the only",
        "; reliable cleanup is removing the whole tree rather than chasing",
        "; specific __pycache__ paths.",
        'Type: filesandordirs; Name: "{app}\\Lib"',
        "",
        "[Code]",
        "// -- Bundled launcher resolution ------------------------------------------------",
        "// The embedded runtime is flattened into {app}: python313.dll, python313.zip,",
        "// the .pyd modules and python313._pth sit at the install root next to",
        "// {app}\\quill.exe (a VERSIONINFO-stamped copy of pythonw.exe, issue #615).",
        "// So {app}\\quill.exe loads the bundled interpreter in isolation (correct",
        "// sys.prefix, pywin32 bootstrap runs) and the sitecustomize self-run hook",
        "// starts QUILL. pythonw.exe is the no-stamp fallback; both are absent only",
        "// in a dev build with no bundled runtime, where this returns blank and no",
        "// shortcut/icon is wired.",
        "function BundledLauncherPath(Param: String): String;",
        "begin",
        "  if FileExists(ExpandConstant('{app}\\quill.exe')) then",
        "    Result := ExpandConstant('{app}\\quill.exe')",
        "  else if FileExists(ExpandConstant('{app}\\pythonw.exe')) then",
        "    Result := ExpandConstant('{app}\\pythonw.exe')",
        "  else",
        "    Result := '';",
        "end;",
        "",
        "function HasBundledLauncher(): Boolean;",
        "begin",
        "  Result := BundledLauncherPath('') <> '';",
        "end;",
        "",
        "// -- Post-install: write the new-install marker -----------------------------",
        "// The new-install marker tells the app to re-run the setup wizard on first",
        "// launch even when %APPDATA% settings from a prior install say it completed.",
        "// Node.js is no longer bundled or offered here; the app installs it on",
        "// demand (quill/core/node_install.py) if a Node Quillin needs it.",
        "procedure CurStepChanged(CurStep: TSetupStep);",
        "var",
        "  StaleShortcut: String;",
        "begin",
        "  if CurStep = ssInstall then",
        "  begin",
        "    // Remove any pre-existing desktop shortcut before [Icons] recreates",
        "    // it, so an upgrade never leaves a shortcut pointing at a launcher",
        "    // that no longer exists. Earlier installs targeted run-quill.cmd",
        "    // (beta 1) or, in the nested layout, quill.exe inside the old python",
        "    // subfolder -- both now invalid (the runtime is flattened into {app}",
        "    // and the stale python subfolder is wiped by [InstallDelete] above).",
        "    // [Icons] then recreates the shortcut pointing at the flat,",
        "    // self-running {app}\\quill.exe (via BundledLauncherPath).",
        "    StaleShortcut := ExpandConstant('{autodesktop}\\{#AppName}.lnk');",
        "    if FileExists(StaleShortcut) then",
        "      DeleteFile(StaleShortcut);",
        "  end;",
        "  if CurStep = ssPostInstall then",
        "  begin",
        "    SaveStringToFile(ExpandConstant('{app}\\quill-new-install.txt'), 'new-install', False);",
        "  end;",
        "end;",
        "",
        "// -- Uninstall: discover a custom data location ----------------------------",
        "// When the user chose a custom data folder, save_storage_mode writes",
        '// {"mode":"custom","path":"..."} into storage-mode.json under',
        "// %APPDATA%\\Quill (quill.core.storage_mode). The pointer therefore lives",
        "// INSIDE the folder the uninstaller deletes, so it must be read first --",
        "// otherwise the custom directory is silently orphaned on 'remove all data'.",
        "// JSON stores backslashes doubled, so they are collapsed after extraction.",
        "function ReadCustomDataDir(): String;",
        "var",
        "  ModeFile: String;",
        "  Raw: AnsiString;",
        "  S: String;",
        "  P, Q: Integer;",
        "begin",
        "  Result := '';",
        "  ModeFile := ExpandConstant('{userappdata}\\Quill\\storage-mode.json');",
        "  if not FileExists(ModeFile) then",
        "    Exit;",
        "  if not LoadStringFromFile(ModeFile, Raw) then",
        "    Exit;",
        "  S := String(Raw);",
        "  // Only honour an explicit custom mode; appdata/portable have no path.",
        "  if Pos('\"custom\"', S) = 0 then",
        "    Exit;",
        "  P := Pos('\"path\"', S);",
        "  if P = 0 then",
        "    Exit;",
        "  S := Copy(S, P + 6, Length(S));",
        "  P := Pos(':', S);",
        "  if P = 0 then",
        "    Exit;",
        "  S := Copy(S, P + 1, Length(S));",
        "  P := Pos('\"', S);",
        "  if P = 0 then",
        "    Exit;",
        "  S := Copy(S, P + 1, Length(S));",
        "  Q := Pos('\"', S);",
        "  if Q = 0 then",
        "    Exit;",
        "  S := Copy(S, 1, Q - 1);",
        "  StringChangeEx(S, '\\\\', '\\', True);",
        "  Result := S;",
        "end;",
        "",
        "function NormalizedDir(Dir: String): String;",
        "begin",
        "  Result := Lowercase(RemoveBackslashUnlessRoot(Dir));",
        "end;",
        "",
        "// Guard: never let a stray or hostile storage-mode.json point the",
        "// uninstaller at a drive root, the install dir, or a well-known shell",
        "// folder. Only an existing directory more specific than a drive root",
        "// (Length > 3, e.g. not 'c:\\') and outside those locations is eligible.",
        "function IsSafeCustomDataDir(Dir: String): Boolean;",
        "var",
        "  N: String;",
        "begin",
        "  Result := False;",
        "  if Dir = '' then",
        "    Exit;",
        "  if not DirExists(Dir) then",
        "    Exit;",
        "  N := NormalizedDir(Dir);",
        "  if Length(N) <= 3 then",
        "    Exit;",
        "  if N = NormalizedDir(ExpandConstant('{app}')) then Exit;",
        "  if N = NormalizedDir(ExpandConstant('{userappdata}')) then Exit;",
        "  if N = NormalizedDir(ExpandConstant('{userappdata}\\Quill')) then Exit;",
        "  if N = NormalizedDir(ExpandConstant('{localappdata}')) then Exit;",
        "  if N = NormalizedDir(ExpandConstant('{userprofile}')) then Exit;",
        "  if N = NormalizedDir(ExpandConstant('{userdocs}')) then Exit;",
        "  if N = NormalizedDir(ExpandConstant('{win}')) then Exit;",
        "  if N = NormalizedDir(ExpandConstant('{sys}')) then Exit;",
        "  Result := True;",
        "end;",
        "",
        "// -- Uninstall: ask before wiping personal data ----------------------------",
        "procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);",
        "var",
        "  DataDir: String;",
        "  CustomDir: String;",
        "  Prompt: String;",
        "  HasCustom: Boolean;",
        "begin",
        "  if CurUninstallStep = usUninstall then",
        "  begin",
        "    DataDir := ExpandConstant('{userappdata}\\Quill');",
        "    // Read the custom-location pointer BEFORE DataDir is deleted below.",
        "    CustomDir := ReadCustomDataDir();",
        "    HasCustom := (CustomDir <> '') and IsSafeCustomDataDir(CustomDir);",
        "    if DirExists(DataDir) or HasCustom then",
        "    begin",
        "      Prompt := 'Also remove your Quill data?' + #13#10 + #13#10 +",
        "                'This deletes your settings, dictionaries, autosaves, backups,' + #13#10 +",
        "                'and onboarding state in:';",
        "      if DirExists(DataDir) then",
        "        Prompt := Prompt + #13#10 + DataDir;",
        "      if HasCustom then",
        "        Prompt := Prompt + #13#10 + CustomDir;",
        "      Prompt := Prompt + #13#10 + #13#10 +",
        "                'Choose No to keep your documents and settings for a future' + #13#10 +",
        "                'reinstall. Choose Yes to remove everything.';",
        "      if MsgBox(Prompt, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then",
        "      begin",
        "        if HasCustom then",
        "          DelTree(CustomDir, True, True, True);",
        "        if DirExists(DataDir) then",
        "          DelTree(DataDir, True, True, True);",
        "      end;",
        "    end;",
        "  end;",
        "end;",
    ]
    return "\n".join(lines) + "\n"


def compile_inno_setup_installer(
    installer_script: Path,
    *,
    version: str,
    iscc_path: Path | None = None,
) -> Path:
    compiler = iscc_path or find_inno_setup_compiler()
    if compiler is None:
        raise RuntimeError(
            "Inno Setup compiler not found. Install Inno Setup 6 or pass --iscc-path."
        )
    subprocess.run([str(compiler), str(installer_script)], check=True)
    expected_name = f"Quill-for-All-Setup-{version}.exe"
    for installer_exe in (
        installer_script.parent / expected_name,
        installer_script.parent / "Output" / expected_name,
    ):
        if installer_exe.exists():
            return installer_exe
    raise RuntimeError(
        "Expected installer executable at "
        f"{installer_script.parent / expected_name} or "
        f"{installer_script.parent / 'Output' / expected_name}"
    )


def find_inno_setup_compiler() -> Path | None:
    for candidate_name in ("ISCC.exe", "iscc"):
        discovered = shutil.which(candidate_name)
        if discovered:
            return Path(discovered)
    for candidate in (
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ):
        if candidate.exists():
            return candidate
    return None


def bundle_embedded_python(
    target_dir: Path,
    source_root: Path,
    pyproject: Path,
    identity: BuildIdentity | None = None,
    launcher_file_version: str | None = None,
    build_cache_dir: Path | None = None,
    download_url: str = EMBEDDED_PYTHON_URL,
    expected_sha256: str | None = EMBEDDED_PYTHON_SHA256,
) -> Path:
    """Download the official Windows embeddable Python and prepare it for use.

    The embeddable distribution is a small (~10 MB) zip that does NOT
    include pip and disables ``sys.path`` discovery of site-packages by
    default. To ship Quill as a single self-contained bundle we:

    1. Download and SHA-256 verify the official zip from python.org.
    2. Extract it to ``target_dir``.
    3. Patch the ``python<ver>._pth`` file so ``site`` is enabled
       (otherwise ``pip``-installed wheels are invisible).
    4. Bootstrap pip via the official ``get-pip.py``.
    5. ``pip install`` the runtime dependencies (wxPython, pyttsx3).
    6. Drop the Quill package source into the runtime so
       ``python -m quill`` resolves without a wheel build step.
    7. Copy ``pythonw.exe`` to ``quill.exe`` and stamp its VERSIONINFO with
       the Quill identity (issue #615), when ``identity`` is supplied.

    Returns the path to the prepared runtime directory.
    """

    target_dir = target_dir.resolve()
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)

    archive = target_dir.parent / f"python-{EMBEDDED_PYTHON_VERSION}-embed-amd64.zip"
    print(f"Downloading {download_url}...")
    _download_with_verification(download_url, archive, expected_sha256)

    print(f"Extracting embedded Python to {target_dir}...")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(target_dir)

    # Enable site-packages discovery in the embedded distribution.
    pth_files = list(target_dir.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError("Embedded Python zip did not contain a ._pth file")
    pth = pth_files[0]
    pth_text = pth.read_text(encoding="utf-8")
    if "#import site" in pth_text:
        pth_text = pth_text.replace("#import site", "import site")
        pth.write_text(pth_text, encoding="utf-8")

    # Make the stamped quill.exe a self-running launcher (no console window, no
    # "-m quill" argument, no .cmd shim). site is enabled above, so Python
    # auto-imports this sitecustomize at startup; it launches QUILL only when the
    # running executable is quill.exe and no script/args were given (a bare
    # double-click). Every other use of the runtime -- python.exe, pip during
    # this build, an explicit "quill.exe -m quill" -- is left untouched.
    sitecustomize = target_dir / "sitecustomize.py"
    sitecustomize.write_text(_self_run_sitecustomize_source(), encoding="utf-8")

    python_exe = target_dir / "python.exe"
    if not python_exe.exists():
        raise RuntimeError(f"Embedded Python missing python.exe at {python_exe}")

    print("Bootstrapping pip into the embedded runtime...")
    get_pip = target_dir / "get-pip.py"
    _download_with_verification(
        "https://bootstrap.pypa.io/get-pip.py",
        get_pip,
        expected_sha256=None,
    )
    subprocess.run([str(python_exe), str(get_pip), "--no-warn-script-location"], check=True)
    get_pip.unlink(missing_ok=True)

    # Embedded Python has no setuptools; install it before any sdist-only packages.
    subprocess.run(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--no-warn-script-location",
            "--no-compile",
            "setuptools",
        ],
        check=True,
    )

    runtime_dependencies = bundled_runtime_dependencies(pyproject)
    print(f"Installing runtime dependencies ({', '.join(runtime_dependencies)})...")
    subprocess.run(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--no-warn-script-location",
            "--no-compile",
            *runtime_dependencies,
        ],
        check=True,
    )

    # A distributable must ALWAYS ship a working Report a Bug. The bundled
    # GitHub token is what makes the rich bug-reporter fire instead of falling
    # back to a bare web link. An unset QUILL_FEEDBACK_GITHUB_TOKEN HARD-FAILS
    # the build, unconditionally -- there is no opt-out. This guard was once
    # opt-in (--require-feedback-token) and then fail-by-default with an
    # --allow-missing-feedback-token escape hatch; both still silently let an
    # ad-hoc build ship a tokenless bundle, so every beta-2 upgrade user got
    # "No token" (#919). It is now mandatory for every build, period.
    print("Generating bundled feedback-hub token (quill/_feedback_token.py)...")
    token_cmd = [
        str(python_exe),
        str(source_root / "tools" / "generate_feedback_token.py"),
        "--require-token",
    ]
    subprocess.run(token_cmd, check=True)

    # Copy the Quill package source into site-packages so `python -m quill`
    # works without requiring a separate wheel build.
    site_packages = target_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    quill_source = source_root / "quill"
    if not quill_source.is_dir():
        raise RuntimeError(f"Could not find quill/ package source under {source_root.resolve()}.")
    print(f"Copying Quill package source from {quill_source} into runtime...")
    shutil.copytree(
        quill_source, site_packages / "quill", dirs_exist_ok=True, ignore=_DEV_CACHE_IGNORE
    )

    # Belt-and-suspenders: assert the token that ACTUALLY ships is non-empty.
    # The generation step above already fails on an unset secret, but this
    # guards the true end-user invariant -- the file inside the bundled quill/
    # package that Report a Bug reads at runtime (via
    # quill.core.feedback_token._bundled_token) -- against any future path that
    # bakes an empty token or fails to copy it into the bundle. This is the
    # exact "Michael upgrades beta 2 and gets no token" symptom, locked out.
    _assert_bundled_token_nonempty(site_packages)

    # Stage the changelog inside the package so the running build can show
    # abbreviated "What's New" / Check-for-Updates release notes offline
    # (quill.core.release_notes.find_changelog reads quill/CHANGELOG.md).
    changelog_src = source_root / "CHANGELOG.md"
    if changelog_src.is_file():
        shutil.copy2(changelog_src, site_packages / "quill" / "CHANGELOG.md")

    _install_vendored_glow(python_exe, source_root)
    _stage_table_uia(site_packages, source_root)
    _prune_embedded_runtime(site_packages)

    if identity is not None:
        _stamp_quill_launcher(
            target_dir,
            identity=identity,
            file_version=launcher_file_version or "0.0.0.0",
            build_cache_dir=build_cache_dir or target_dir.parent / "_build-tools",
        )

    archive.unlink(missing_ok=True)
    return target_dir


def _stamp_quill_launcher(
    runtime_dir: Path,
    *,
    identity: BuildIdentity,
    file_version: str,
    build_cache_dir: Path,
) -> None:
    """Copy pythonw.exe to quill.exe and stamp its VERSIONINFO (issue #615).

    JAWS's Ctrl+JAWSKey+V reads VersionInfo from the foreground window's
    owning .exe at the OS layer, not from the window title -- the earlier
    fix (window-title version) cannot reach that channel because the
    process actually running the whole session is pythonw.exe, whose
    VersionInfo says "Python 3.x.x". quill.exe is a byte-for-byte copy of
    that same interpreter binary; rcedit only edits its resource section in
    place, so behavior is unchanged and only its reported identity differs.
    """
    pythonw_exe = runtime_dir / "pythonw.exe"
    if not pythonw_exe.exists():
        print(f"Warning: {pythonw_exe} not found; skipping launcher VersionInfo stamp.")
        return
    quill_exe = runtime_dir / "quill.exe"
    shutil.copy2(pythonw_exe, quill_exe)

    rcedit_path = _download_rcedit(build_cache_dir)
    print(f"Stamping {quill_exe} VersionInfo as {identity.product_name} {file_version}...")
    subprocess.run(
        [
            str(rcedit_path),
            str(quill_exe),
            "--set-version-string",
            "ProductName",
            identity.product_name,
            "--set-version-string",
            "FileDescription",
            f"{identity.product_name} accessible writing environment",
            "--set-version-string",
            "CompanyName",
            identity.publisher,
            "--set-version-string",
            "OriginalFilename",
            quill_exe.name,
            "--set-version-string",
            "InternalName",
            "quill",
            "--set-file-version",
            file_version,
            "--set-product-version",
            file_version,
        ],
        check=True,
    )


def _download_rcedit(cache_dir: Path) -> Path:
    """Download and SHA-256-verify rcedit-x64.exe into cache_dir, reusing it if present.

    rcedit patches the Windows VERSIONINFO/icon resources of an existing PE
    executable in place; it is a build-time tool only and is never copied
    into the portable bundle or the installer payload.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    rcedit_exe = cache_dir / "rcedit-x64.exe"
    if rcedit_exe.exists():
        return rcedit_exe
    print(f"Downloading rcedit from {RCEDIT_PINNED_URL}...")
    _download_with_verification(RCEDIT_PINNED_URL, rcedit_exe, expected_sha256=RCEDIT_PINNED_SHA256)
    return rcedit_exe


def _stage_table_uia(site_packages: Path, source_root: Path) -> None:
    """Build (best-effort) and stage the optional Table Studio native UIA
    provider (`_quill_table_uia.pyd`) into site-packages so it is importable.

    Entirely optional: Table Studio / CSV Studio run with the wx.Accessible
    MSAA fallback when the module is absent, so a missing MSVC/Windows-SDK
    toolchain never fails the distribution build. A prebuilt .pyd already in
    quill/native/table_uia is staged as-is.
    """
    native_dir = source_root / "quill" / "native" / "table_uia"
    if not native_dir.is_dir():
        return
    existing = next(native_dir.glob("_quill_table_uia*.pyd"), None)
    if existing is None:
        build_script = source_root / "scripts" / "build_table_uia.py"
        if build_script.is_file():
            try:
                subprocess.run([sys.executable, str(build_script)], cwd=source_root, check=False)
            except Exception as exc:  # noqa: BLE001 - optional; never fail the build
                print(f"Table Studio native UIA provider build skipped: {exc}")
        existing = next(native_dir.glob("_quill_table_uia*.pyd"), None)
    if existing is not None:
        shutil.copy2(existing, site_packages / existing.name)
        print(f"Staged native UIA provider {existing.name} into the runtime.")
    else:
        print("No native UIA provider built; Table Studio ships with the MSAA fallback.")


def _prune_embedded_runtime(site_packages: Path) -> None:
    """Remove packages that are only needed during the build, not at runtime.

    setuptools and wheel are bootstrapped to install dependencies, then stripped
    so they don't bloat the installer.  The pywin32 extras (pythonwin, isapi,
    adodbapi, PyWin32.chm) are also removed.

    pip is deliberately *kept*: the optional Faster Whisper engine is installed
    on demand at runtime (wheel-only, into a user-writable engine-pack folder --
    see ``quill/core/speech/engine_install.py``), which needs ``python -m pip``.
    Modern pip vendors its own dependencies, so removing setuptools/wheel does not
    break a wheel-only ``pip install``.

    ``quill/devtools`` (the in-app Developer Console) and ``quill/tools``
    (``kqp_validator`` backs the runtime "Import Keyboard Pack" command) are
    imported by ``quill/ui`` and ``quill/core`` at runtime, so they must ship
    even though most of ``quill/tools`` is otherwise CI-only.

    Babel is intentionally NOT pruned. QUILL's own i18n uses stdlib ``gettext``
    and never imports ``babel`` at runtime, so it looks build-only -- but
    ``kokoro-onnx`` pulls it in transitively (``kokoro_onnx -> phonemizer ->
    segments -> csvw -> babel.numbers``). Pruning it broke Kokoro's onnx path on
    a clean build (#881), so babel stays bundled.
    """
    removable = [
        # Build tools - used during pip install, not at runtime. pip stays (it
        # powers the optional on-demand Faster Whisper engine install).
        "setuptools",
        "setuptools-*",
        "wheel",
        "wheel-*",
        "pkg_resources",
        # pywin32 extras not used by Quill (~21 MB)
        "pythonwin",
        "PyWin32.chm",
        "adodbapi",
        "isapi",
        # NOTE: babel is NOT pruned. It looks build-only (we compile translations
        # with it and runtime i18n uses stdlib gettext), but kokoro-onnx pulls it
        # in transitively at runtime -- kokoro_onnx -> phonemizer -> segments ->
        # csvw -> `import babel.numbers`. Pruning it made Kokoro's onnx path fail
        # to import on a clean build, silently falling back to the torch path and
        # showing "Kokoro needs one more component" (#881). Keep babel bundled.
    ]
    total_removed = 0
    for pattern in removable:
        for path in site_packages.glob(pattern):
            size = (
                sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                if path.is_dir()
                else path.stat().st_size
            )
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            total_removed += size
    mb = total_removed / 1_048_576
    print(f"Pruned {mb:.0f} MB of build-only packages from the runtime.")


def _install_vendored_glow(python_exe: Path, source_root: Path) -> None:
    """Install the vendored GLOW contract wheel into the runtime, fully offline.

    GLOW now ships as part of the base bundle: the full ``quill-glow-core[glow]``
    engine is installed into the runtime by ``bundle_embedded_python`` via the
    ``glow`` group in :data:`DEFAULT_BUNDLED_DEPENDENCY_GROUPS`. This step is the
    offline fallback — it bundles the lightweight ``quill-glow-core`` contract
    wheel from ``vendor/wheels`` (``--no-index`` keeps it offline) so the GLOW
    seam and its safe behavior are present even if the online extra install was
    skipped, and the consented GLOW updater (GLOW-8) can still refresh the engine.
    When no vendored wheel is present the build continues rather than failing.
    """
    wheels_dir = source_root / "vendor" / "wheels"
    if not wheels_dir.is_dir():
        print("No vendor/wheels directory found; skipping GLOW bundling.")
        return
    contract_wheels = sorted(wheels_dir.glob("quill_glow_core-*.whl"))
    if not contract_wheels:
        print("No vendored quill-glow-core wheel found; skipping GLOW bundling.")
        return
    print(f"Installing vendored GLOW contract wheel from {wheels_dir} (offline)...")
    subprocess.run(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--no-warn-script-location",
            "--no-compile",
            "--no-index",
            "--find-links",
            str(wheels_dir),
            "quill-glow-core",
        ],
        check=True,
    )
    # Smoke check: the contract package must import in the built runtime.
    result = subprocess.run(
        [str(python_exe), "-c", "import quill_glow_core; print('glow contract ok')"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "GLOW contract wheel was installed but failed to import in the "
            f"built runtime:\n{result.stderr}"
        )
    print(result.stdout.strip() or "glow contract ok")


def bundled_runtime_dependencies(pyproject: Path) -> list[str]:
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    project = data.get("project", {})
    if not isinstance(project, dict):
        return ["wxPython>=4.2.2", "pyttsx3>=2.99"]
    dependencies: list[str] = []
    raw_dependencies = project.get("dependencies", [])
    if isinstance(raw_dependencies, list):
        dependencies.extend(item for item in raw_dependencies if isinstance(item, str))
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        for group in DEFAULT_BUNDLED_DEPENDENCY_GROUPS:
            values = optional.get(group, [])
            if isinstance(values, list):
                dependencies.extend(item for item in values if isinstance(item, str))
    unique: list[str] = []
    for dependency in dependencies:
        if dependency not in unique:
            unique.append(dependency)
    return unique or ["wxPython>=4.2.2", "pyttsx3>=2.99"]


def _stage_distribution_docs(portable_dir: Path, source_root: Path) -> list[Path]:
    docs_dir = portable_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []
    for relative in (Path("docs") / "user guide" / "userguide.md",):
        source = source_root / relative
        if not source.exists():
            continue
        target = docs_dir / source.name
        shutil.copy2(source, target)
        staged.append(target)
    return staged


def _stage_braille_pack(
    portable_dir: Path,
    braille_pack_dir: Path | None,
    *,
    source_root: Path | None = None,
) -> bool:
    """Copy the braille pack into portable/vendor/braille-pack/. Returns True if staged.

    Footprint unbundle: the pack (~68 MB of translation tables) is NO LONGER
    bundled by default. Fresh installs fetch it on demand from QUILL's pinned,
    SHA-256-verified assets-v1 release (quill/core/braille_pack.py) the first
    time Translation/BRF export is used. A build may still stage a local copy by
    passing --braille-pack-dir. Upgraders keep their existing {app} copy.
    """
    _ = source_root  # retained for signature stability; default staging removed.
    if braille_pack_dir is None:
        return False
    if not braille_pack_dir.is_dir():
        raise RuntimeError(f"Braille pack directory not found: {braille_pack_dir}")
    target = portable_dir / "vendor" / "braille-pack"
    shutil.copytree(braille_pack_dir, target, dirs_exist_ok=True)
    print(f"Staged braille pack from {braille_pack_dir} to {target}")
    return True


def _stage_bundled_tools(portable_dir: Path, bundled_tool_dirs: dict[str, Path]) -> list[str]:
    if not bundled_tool_dirs:
        return []
    tools_root = portable_dir / "tools"
    tools_root.mkdir(parents=True, exist_ok=True)
    bundled: list[str] = []
    for tool_id, source in bundled_tool_dirs.items():
        if not source.exists():
            raise RuntimeError(f"Bundled tool path does not exist: {source}")
        target = tools_root / tool_id
        shutil.copytree(source, target, dirs_exist_ok=True)
        bundled.append(tool_id)
    return sorted(bundled)


def _stage_kokoro(portable_dir: Path, source_dir: Path | None) -> bool:
    """Stage the Kokoro ONNX model + voices into portable/kokoro-models/.

    The runtime (quill.core.read_aloud._bundled_kokoro_model_dir) resolves a
    bundled Kokoro copy from {app}/kokoro-models, so the two files ship via the
    generic ..\\portable\\* installer copy rather than a dedicated component.

    When *source_dir* is given (the --kokoro-dir flag) the model and voices are
    copied from there; otherwise they are downloaded from the pinned kokoro-onnx
    release and SHA-256 verified. An already-staged pair is reused. Returns True
    when both files are present after staging.
    """
    target = portable_dir / "kokoro-models"
    target.mkdir(parents=True, exist_ok=True)
    model_dst = target / KOKORO_MODEL_FILENAME
    voices_dst = target / KOKORO_VOICES_FILENAME
    if model_dst.exists() and voices_dst.exists():
        print("Kokoro models already staged; skipping.")
        return True

    if source_dir is not None:
        model_src = source_dir / KOKORO_MODEL_FILENAME
        voices_src = source_dir / KOKORO_VOICES_FILENAME
        missing = [str(p) for p in (model_src, voices_src) if not p.exists()]
        if missing:
            raise RuntimeError(
                "Kokoro source directory is missing required files: " + ", ".join(missing)
            )
        shutil.copy2(model_src, model_dst)
        shutil.copy2(voices_src, voices_dst)
        print(f"Kokoro models copied from {source_dir} to {target}")
        return True

    print(f"Downloading Kokoro model from {KOKORO_MODEL_URL}...")
    _download_with_verification(KOKORO_MODEL_URL, model_dst, expected_sha256=KOKORO_MODEL_SHA256)
    print(f"Downloading Kokoro voices from {KOKORO_VOICES_URL}...")
    _download_with_verification(KOKORO_VOICES_URL, voices_dst, expected_sha256=KOKORO_VOICES_SHA256)
    print(f"Kokoro models staged to {target}")
    return True


def _speech_asset_manifest(
    portable_dir: Path, bundled_tools: list[str]
) -> dict[str, dict[str, object]]:
    speech_root = portable_dir / "tools" / "speech"
    manifest: dict[str, dict[str, object]] = {}
    engine_dirs = {
        "dectalk": "dectalk",
        "espeak": "espeak-ng",
        "piper": "piper",
        "whispercpp": "whispercpp",
    }
    for engine, dir_name in engine_dirs.items():
        engine_dir = speech_root / dir_name
        manifest[engine] = {
            "bundled": f"speech/{dir_name}" in bundled_tools,
            "path": str(engine_dir) if engine_dir.exists() else "",
            "exists": engine_dir.exists(),
            "downloadable": True,
        }
    # Kokoro lives at the bundle root (kokoro-models/), not under tools/speech,
    # because that is where the runtime resolves a bundled copy via QUILL_APP_ROOT.
    kokoro_dir = portable_dir / "kokoro-models"
    kokoro_ready = (kokoro_dir / KOKORO_MODEL_FILENAME).exists() and (
        kokoro_dir / KOKORO_VOICES_FILENAME
    ).exists()
    manifest["kokoro"] = {
        "bundled": kokoro_ready,
        "path": str(kokoro_dir) if kokoro_ready else "",
        "exists": kokoro_ready,
        "downloadable": True,
    }
    return manifest


def _fetch_latest_github_asset_url(owner: str, repo: str, asset_suffix: str) -> str | None:
    """Return the download URL for the first release asset whose name ends with asset_suffix.

    Queries the GitHub releases API. Returns None on any network or parse error so
    callers can fall back to pinned versions without aborting the build.
    """
    import json

    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        with urllib.request.urlopen(api_url, timeout=15) as resp:  # noqa: S310
            release = json.loads(resp.read())
        for asset in release.get("assets", []):
            if asset.get("name", "").endswith(asset_suffix):
                tag = release.get("tag_name", "unknown")
                print(f"Found latest {owner}/{repo} release {tag}: {asset['name']}")
                return asset["browser_download_url"]
    except Exception as exc:
        print(
            f"Warning: could not fetch latest {owner}/{repo} release ({exc}); using pinned version."
        )
    return None


def _download_and_stage_pandoc(portable_dir: Path) -> Path:
    """Download Pandoc for Windows and return a staging directory for _stage_bundled_tools.

    Tries the latest GitHub release first; falls back to the pinned version.
    Stages to portable/_tool-download/pandoc/ so _stage_bundled_tools() copies
    from there to tools/pandoc/. Re-uses a prior download to avoid redundant calls.
    """
    stage_dir = portable_dir / "_tool-download" / "pandoc"
    stage_dir.mkdir(parents=True, exist_ok=True)
    if (stage_dir / "pandoc.exe").exists():
        print("Pandoc already downloaded; skipping.")
        return stage_dir

    url = (
        _fetch_latest_github_asset_url("jgm", "pandoc", "-windows-x86_64.zip") or PANDOC_PINNED_URL
    )
    sha256 = PANDOC_PINNED_SHA256 if url == PANDOC_PINNED_URL else None

    archive = stage_dir / "pandoc-windows-x86_64.zip"
    print(f"Downloading Pandoc from {url}...")
    _download_with_verification(url, archive, expected_sha256=sha256)

    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():
            if member.endswith("/pandoc.exe") or member == "pandoc.exe":
                (stage_dir / "pandoc.exe").write_bytes(zf.read(member))
                break
    archive.unlink(missing_ok=True)
    if not (stage_dir / "pandoc.exe").exists():
        raise RuntimeError("Pandoc zip did not contain pandoc.exe")
    print(f"Pandoc staged to {stage_dir}")
    return stage_dir


def _download_and_stage_whisper(portable_dir: Path) -> Path:
    """Download the whisper.cpp engine for Windows and return a staging directory.

    Tries the latest ggml-org/whisper.cpp GitHub release first; falls back to the
    pinned version. Stages to portable/_tool-download/whispercpp/stage/ so
    _stage_bundled_tools() copies it to tools/speech/whispercpp/. Re-uses a prior
    download. The staged folder keeps whisper-cli.exe alongside its whisper.dll /
    ggml*.dll dependencies so resolve_whisper_executable() finds a runnable engine.

    whisper.cpp is the default offline transcription/dictation provider (#617), so
    this download is not optional: a failure raises rather than letting the build
    produce an installer whose selected "speechwhisper" component ships no engine
    (the empty-component regression behind #742).
    """
    stage_dir = portable_dir / "_tool-download" / "whispercpp" / "stage"
    if (stage_dir / "whisper-cli.exe").exists() or (stage_dir / "main.exe").exists():
        print("whisper.cpp already downloaded; skipping.")
        return stage_dir

    url = (
        _fetch_latest_github_asset_url("ggml-org", "whisper.cpp", "-bin-x64.zip")
        or WHISPERCPP_PINNED_URL
    )
    if url == WHISPERCPP_PINNED_URL and WHISPERCPP_PINNED_SHA256.startswith("<"):
        raise RuntimeError(
            "Could not reach the whisper.cpp releases API and the pinned fallback "
            "SHA-256 is still a placeholder. Set WHISPERCPP_PINNED_URL / "
            "WHISPERCPP_PINNED_SHA256 to a verified release before building offline, "
            "or supply --whisper-dir with a local engine."
        )
    sha256 = WHISPERCPP_PINNED_SHA256 if url == WHISPERCPP_PINNED_URL else None

    tmp_dir = portable_dir / "_tool-download" / "whispercpp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    archive = tmp_dir / "whisper-bin-x64.zip"
    print(f"Downloading whisper.cpp from {url}...")
    _download_with_verification(url, archive, expected_sha256=sha256)

    extract_dir = tmp_dir / "extracted"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract_dir)

    # Newer releases ship whisper-cli.exe; older ones shipped main.exe. Either is
    # on resolve_whisper_executable()'s allowlist, so accept whichever is present.
    exe_candidates = list(extract_dir.rglob("whisper-cli.exe")) or list(
        extract_dir.rglob("main.exe")
    )
    if not exe_candidates:
        raise RuntimeError("whisper.cpp zip did not contain whisper-cli.exe or main.exe")
    engine_root = exe_candidates[0].parent
    stage_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(engine_root, stage_dir, dirs_exist_ok=True)
    archive.unlink(missing_ok=True)
    print(f"whisper.cpp staged to {stage_dir}")
    return stage_dir


def _download_with_verification(
    url: str,
    target: Path,
    expected_sha256: str | None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - URL is pinned
        data = response.read()
    if expected_sha256:
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_sha256:
            raise RuntimeError(
                f"SHA-256 mismatch for {url}\n  expected: {expected_sha256}\n  got:      {digest}"
            )
    target.write_bytes(data)


def _project_version(pyproject: Path) -> str:
    # ``build/version.toml`` is the single source of truth for the release
    # identity (see tools/generate_build_info.py). It feeds the installer
    # filename, the About dialog, and the embedded ``quill._build_info``.
    # Keep the resolution in sync with ``tools/generate_build_info.py`` so
    # every consumer agrees.
    return _build_identity(pyproject.parent).display_version


def _build_identity(source_root: Path) -> BuildIdentity:
    """Return the build identity derived from ``build/version.toml``.

    Falls back to ``quill/__init__.py`` and a default publisher string if
    the file is missing (e.g. in test sandboxes). Importing this helper
    keeps ``build_inno_setup_script()`` and ``manifest.json`` honest about
    where the version number comes from.
    """
    version_file = source_root / "build" / "version.toml"
    if version_file.exists():
        with version_file.open("rb") as handle:
            data = tomllib.load(handle)
        base = str(data.get("base_version", "")).strip()
        channel = str(data.get("channel", "dev")).strip().lower()
        pre = int(data.get("prerelease_number", 0))
        product_name = str(data.get("product_name", APP_DISPLAY_NAME))
        publisher = str(data.get("publisher", APP_ORGANIZATION))
    else:
        base = _base_version_from_init_py(source_root)
        channel = "dev"
        pre = 0
        product_name = APP_DISPLAY_NAME
        publisher = APP_ORGANIZATION
    display = _display_version(base, channel, pre)
    return BuildIdentity(
        base_version=base,
        channel=channel,
        prerelease_number=pre,
        display_version=display,
        product_name=product_name,
        publisher=publisher,
    )


def _base_version_from_init_py(source_root: Path) -> str:
    """Last-resort version resolver: parse ``quill/__init__.py``.

    Used only when ``build/version.toml`` is missing (legacy checkout,
    tests, partial clones). Matches ``tools/generate_build_info.py`` by
    stripping prerelease/build suffixes so the installer version is just
    the base.
    """
    import re

    init_py = source_root / "quill" / "__init__.py"
    if init_py.exists():
        match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_py.read_text(), re.M)
        if match:
            raw = match.group(1)
            # Keep only the leading "X.Y.Z" — drop a/b/rc/dev suffixes.
            head = re.match(r"^\d+(?:\.\d+){0,2}", raw)
            if head:
                return head.group(0)
    return "unknown"


def _display_version(base: str, channel: str, pre: int) -> str:
    """User-facing release label, matching tools/generate_build_info.py.

    Examples: "0.7.0", "0.7.0 Beta 1", "0.7.0 Release Candidate 2".
    """
    if channel == "stable":
        return base
    if channel == "alpha":
        return f"{base} Alpha {pre}"
    if channel == "beta":
        return f"{base} Beta {pre}"
    if channel == "rc":
        return f"{base} Release Candidate {pre}"
    return f"{base} Dev"


def _iss_numeric_version(base: str, channel: str, pre: int) -> str:
    """Return a Major.Minor.Build.Revision quadruple for Inno Setup.

    Inno Setup's ``VersionInfoVersion`` directive (which feeds the
    Windows VERSIONINFO resource) requires a numeric quadruple, not
    the user-visible "0.7.0 Beta 1" string. The ``base`` is split on
    dots; missing segments are filled with zeros; ``pre`` fills the
    Revision slot for alpha/beta/rc channels so beta 1 is distinguishable
    from the final 0.7.0 release once a user has both installed.
    """
    parts = base.split(".")
    while len(parts) < 3:
        parts.append("0")
    major, minor, build = parts[0], parts[1], parts[2]
    revision = str(pre) if channel in {"alpha", "beta", "rc"} else "0"
    return f"{major}.{minor}.{build}.{revision}"


@dataclass(frozen=True)
class BuildIdentity:
    """A snapshot of the values that drive installer, manifest, and About."""

    base_version: str
    channel: str
    prerelease_number: int
    display_version: str
    product_name: str
    publisher: str


if __name__ == "__main__":
    sys.exit(main())
