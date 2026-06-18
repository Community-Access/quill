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
import shutil
import subprocess
import sys
import textwrap
import tomllib
import urllib.request
import zipfile
from pathlib import Path

from quill.core.shell_verbs import ShellVerb, default_shell_verbs
from quill.core.storage import write_json_atomic

# Architecture note: all bundled binaries below are amd64/x86_64.  The Inno
# Setup script uses ArchitecturesAllowed=x64compatible, which covers both
# genuine x64 hardware and ARM64 Windows (Snapdragon / Surface Pro X), where
# Windows runs x64 binaries under hardware emulation transparently.  Native
# ARM64 builds are not produced because none of the three speech engines
# (DECtalk, Piper, eSpeak-NG) ship ARM64 Windows binaries.  Revisit when any
# of them do: Python (embed-arm64.zip), Pandoc, and Node all have arm64 assets.

# Pinned Windows embeddable Python. Bumping these values is the only
# thing needed to ship on a new Python point release.
EMBEDDED_PYTHON_VERSION = "3.12.6"
EMBEDDED_PYTHON_URL = (
    f"https://www.python.org/ftp/python/{EMBEDDED_PYTHON_VERSION}/"
    f"python-{EMBEDDED_PYTHON_VERSION}-embed-amd64.zip"
)
# SHA-256 of the official embeddable zip. If python.org rotates the file
# the build will fail loudly rather than ship an unverified runtime.
EMBEDDED_PYTHON_SHA256 = "a86a2e28870967745d255cc597d1e4d19ae79e65e927cdc324baa0256202231c"

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

# Pinned Piper TTS Windows release. _download_and_stage_piper() tries the
# latest GitHub release first and falls back to these if the API is unreachable.
PIPER_PINNED_URL = (
    "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
)
PIPER_PINNED_SHA256 = "f3c58906402b24f3a96d92145f58acba6d86c9b5db896d207f78dc80811efcea"

# GLOW is hidden for 0.5.0 (the core.glow feature is locked off), so the heavy
# `glow` extra (quill-glow-core[glow], not yet on a public index) is NOT bundled
# in the shipping build. The vendored contract wheel (see _install_vendored_glow)
# still installs the safe GLOW seam. Re-add "glow" here when GLOW is re-enabled
# and its wheels are published.
DEFAULT_BUNDLED_DEPENDENCY_GROUPS = ("ui", "spellcheck", "ocr", "kokoro")


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
        help="Optional local Kokoro voices/models directory to bundle under portable\\tools\\speech\\kokoro.",
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
                "speech/kokoro": args.kokoro_dir,
            }.items()
            if path is not None
        },
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
    braille_pack_dir: Path | None = None,
    compile_installer: bool = False,
    iscc_path: Path | None = None,
) -> dict[str, str]:
    version = _project_version(pyproject)
    resolved_source_root = source_root or Path(".")
    portable_dir = output_dir / "portable"
    installer_dir = output_dir / "installer"
    reference_installer_dir = pyproject.parent / "installer"
    portable_dir.mkdir(parents=True, exist_ok=True)
    installer_dir.mkdir(parents=True, exist_ok=True)
    reference_installer_dir.mkdir(parents=True, exist_ok=True)

    launcher = portable_dir / "run-quill.cmd"
    launcher.write_text(_render_launcher_script(), encoding="utf-8")

    staged_docs = _stage_distribution_docs(portable_dir, resolved_source_root)
    effective_bundled_tools = dict(bundled_tool_dirs or {})
    # Auto-download Pandoc, DECtalk, and eSpeak-NG unless the caller provided
    # a local directory for them. Each function tries the latest GitHub release
    # first and falls back to a pinned version; existing staged files are reused.
    if "pandoc" not in effective_bundled_tools:
        effective_bundled_tools["pandoc"] = _download_and_stage_pandoc(portable_dir)
    if "speech/dectalk" not in effective_bundled_tools:
        effective_bundled_tools["speech/dectalk"] = _download_and_stage_dectalk_release(
            portable_dir
        )
    if "speech/espeak-ng" not in effective_bundled_tools:
        effective_bundled_tools["speech/espeak-ng"] = _download_and_stage_espeak(portable_dir)
    if "speech/piper" not in effective_bundled_tools:
        effective_bundled_tools["speech/piper"] = _download_and_stage_piper(portable_dir)
    bundled_tools = _stage_bundled_tools(portable_dir, effective_bundled_tools)

    readme = portable_dir / "README.txt"
    readme.write_text(
        _render_readme(
            version,
            bundle_python,
            bundled_tools=bundled_tools,
            staged_docs=staged_docs,
        ),
        encoding="utf-8",
    )

    manifest_path = portable_dir / "manifest.json"
    manifest = {
        "project": "quill",
        "version": version,
        "publisher": "Blind Information Technology Solutions (BITS) and Community Access",
        "portableLauncher": str(launcher),
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

    installer_script = installer_dir / "quill.iss"
    reference_installer_script = reference_installer_dir / "quill.iss"
    installer_script_text = build_inno_setup_script(
        version=version, bundle_braille_pack=braille_pack_staged
    )
    installer_script.write_text(installer_script_text, encoding="utf-8")
    reference_installer_script.write_text(installer_script_text, encoding="utf-8")

    installer_readme = build_installer_readme(version)
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
        python_runtime_dir = bundle_embedded_python(
            portable_dir / "python",
            source_root=resolved_source_root,
            pyproject=pyproject,
        )

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


def _render_launcher_script() -> str:
    """Return the contents of ``run-quill.cmd``.

    The launcher prefers a Python interpreter shipped alongside it
    (``python\\pythonw.exe`` for normal windowed launch and
    ``python\\python.exe`` with ``--console``) so the
    typical end user never has to install Python. If no bundled
    interpreter is present we fall back to one on ``PATH`` and, failing
    that, print a clear screen-reader-friendly error.
    """

    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "set QUILL_PORTABLE=1\r\n"
        "set QUILL_APP_ROOT=%~dp0\r\n"
        "set QUILL_PORTABLE_ROOT=%~dp0data\r\n"
        "set QUILL_CONSOLE_MODE=0\r\n"
        'if /I "%~1"=="--console" (\r\n'
        "    set QUILL_CONSOLE_MODE=1\r\n"
        "    shift\r\n"
        ")\r\n"
        'if /I "%~1"=="--no-console" (\r\n'
        "    set QUILL_CONSOLE_MODE=0\r\n"
        "    shift\r\n"
        ")\r\n"
        ":: Prefer the bundled embedded Python that ships with the installer.\r\n"
        'set "QUILL_BUNDLED_PYTHON=%~dp0python\\python.exe"\r\n'
        'set "QUILL_BUNDLED_PYTHONW=%~dp0python\\pythonw.exe"\r\n'
        'if "%QUILL_CONSOLE_MODE%"=="0" (\r\n'
        '    if exist "%QUILL_BUNDLED_PYTHONW%" (\r\n'
        '        start "" "%QUILL_BUNDLED_PYTHONW%" -m quill %*\r\n'
        "        exit /b 0\r\n"
        "    )\r\n"
        "    where pythonw >nul 2>nul\r\n"
        "    if errorlevel 1 goto :run_console\r\n"
        '    start "" pythonw -m quill %*\r\n'
        "    exit /b 0\r\n"
        ")\r\n"
        ":run_console\r\n"
        'if exist "%QUILL_BUNDLED_PYTHON%" (\r\n'
        '    "%QUILL_BUNDLED_PYTHON%" -m quill %*\r\n'
        "    goto :after_run\r\n"
        ")\r\n"
        ":: Fallback: a system-wide Python on PATH (developer / dev-build mode).\r\n"
        "where python >nul 2>nul\r\n"
        "if errorlevel 1 (\r\n"
        "    echo.\r\n"
        "    echo Quill could not find its bundled Python runtime, and no Python\r\n"
        "    echo interpreter is available on PATH.\r\n"
        "    echo.\r\n"
        "    echo If you installed Quill from the official installer, please\r\n"
        "    echo reinstall: this build is missing the bundled runtime.\r\n"
        "    echo.\r\n"
        "    pause\r\n"
        "    exit /b 1\r\n"
        ")\r\n"
        "python -m quill %*\r\n"
        ":after_run\r\n"
        "if errorlevel 1 (\r\n"
        "    echo.\r\n"
        "    echo Quill exited with an error. See the messages above.\r\n"
        "    pause\r\n"
        ")\r\n"
    )


def _render_readme(
    version: str,
    bundle_python: bool,
    *,
    bundled_tools: list[str],
    staged_docs: list[Path],
) -> str:
    if bundle_python:
        runtime_paragraph = (
            "This bundle ships a private Python runtime in the python\\ folder,\n"
            "so you do NOT need to install Python, pip, wxPython, or anything\n"
            "else. Just run run-quill.cmd and start writing."
        )
    else:
        runtime_paragraph = (
            "This bundle does not include a Python runtime. To run it,\n"
            "install Python 3.12+ from https://www.python.org/downloads/windows/\n"
            "and run:  pip install wxPython pyttsx3\n"
            "Then double-click run-quill.cmd."
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
            Quill Portable {version}
            Publisher: Blind Information Technology Solutions (BITS) and Community Access

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

    The launch command is ``"{app}\\run-quill.cmd" --action <action> "%1"``;
    ``run-quill.cmd`` forwards ``%*`` to ``python -m quill``, so the selected
    file path and verb reach the same dispatch used by the in-app menu.
    """

    selected = tuple(verbs) if verbs is not None else default_shell_verbs()
    lines: list[str] = []
    for verb in selected:
        key_name = f"Quill.{verb.verb_id}"
        label = verb.label.replace('"', '""')
        # Inno escapes a literal double-quote inside a string value as "".
        command = f'"""{{app}}\\{{#AppExeName}}"" --action {verb.action} ""%1"""'
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


def build_installer_readme(version: str) -> str:
    """Return the post-install info page shown by the full installer.

    Deliberately separate from portable\\README.txt which targets users
    running Quill from a USB stick or without an installer.
    """
    return (
        f"Quill {version} — Windows Installer\r\n"
        "Publisher: Blind Information Technology Solutions (BITS) and Community Access\r\n"
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


def build_inno_setup_script(version: str, bundle_braille_pack: bool = False) -> str:
    """Return a production-quality Inno Setup script for the portable bundle.

    The script is assembled line-by-line to avoid the f-string + triple-
    quote pitfalls of templating Inno (which uses ``""`` as its own
    quote-escape) inside a Python triple-quoted string.
    """

    lines: list[str] = [
        "; Generated by scripts/build_windows_distribution.py",
        "; Edit build_inno_setup_script(), not this file, to change packaging.",
        "",
        '#define AppName "Quill"',
        f'#define AppVersion "{version}"',
        '#define AppPublisher "Blind Information Technology Solutions (BITS) and Community Access"',
        '#define AppURL "https://github.com/Community-Access/quill"',
        '#define AppExeName "run-quill.cmd"',
        "",
        "[Setup]",
        "AppId={{6E0A1C52-4A90-4C6E-A8A1-3C2A16E2B7F2}",
        "AppName={#AppName}",
        "AppVersion={#AppVersion}",
        "AppPublisher={#AppPublisher}",
        "AppPublisherURL={#AppURL}",
        "AppSupportURL={#AppURL}",
        "AppUpdatesURL={#AppURL}",
        "VersionInfoVersion={#AppVersion}",
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
        f"OutputBaseFilename=Quill-Setup-{version}",
        "Compression=lzma2/ultra",
        "SolidCompression=yes",
        "WizardStyle=modern",
        "; Force-close any processes that lock app files before copying new ones.",
        "; This avoids silent upgrade failures on in-use binaries.",
        "CloseApplications=force",
        "RestartApplications=no",
        "UninstallDisplayName={#AppName} {#AppVersion}",
        "; pythonw.exe carries a real icon so Add/Remove Programs shows one;",
        "; the .cmd launcher has none. Falls back gracefully when no bundled",
        "; runtime is present (e.g. a dev build).",
        "UninstallDisplayIcon={app}\\python\\pythonw.exe",
        "LicenseFile=LICENSE",
        "InfoAfterFile=README-installer.txt",
        "SetupLogging=yes",
        "",
        "[Languages]",
        'Name: "english"; MessagesFile: "compiler:Default.isl"',
        "",
        "[Tasks]",
        'Name: "desktopicon"; Description: "Create a &Desktop shortcut";'
        ' GroupDescription: "Additional shortcuts:"; Flags: unchecked',
        'Name: "fileassoc"; Description: "Register Quill in the Open With menu'
        ' for common text formats (.txt, .md, .rst, .log, .csv, .json)";'
        ' GroupDescription: "File associations:"; Flags: unchecked',
        'Name: "shellverbs"; Description: "Add ""Send to Quill"" actions'
        ' (OCR, Open, Read aloud) to the file right-click menu";'
        ' GroupDescription: "File associations:"; Flags: unchecked',
        "",
        "[Types]",
        "; Full installs everything and skips the component and voice pages.",
        "; Full is the recommended choice for most users.",
        'Name: "full"; Description: "Full installation (recommended)"',
        'Name: "custom"; Description: "Custom installation"; Flags: iscustom',
        "",
        "[Components]",
        "; Every component below gates real [Files] payload. The Writing",
        "; Assistant and the rest of Quill's core ship unconditionally with the",
        "; main bundle, so there is no separate AI component to toggle here.",
        "; DECtalk voice selection is handled by a guided wizard page (see [Code]).",
        'Name: "pandoc"; Description: "Install bundled Pandoc for document conversion";'
        " Types: full custom; Flags: checkablealone",
        'Name: "speechdectalk"; Description: "Install bundled DECtalk runtime";'
        " Types: full custom; Flags: checkablealone",
        'Name: "speechespeak"; Description: "Install bundled eSpeak-NG runtime";'
        " Types: full custom; Flags: checkablealone",
        'Name: "speechpiper"; Description: "Install bundled Piper neural TTS runtime";'
        " Types: full custom; Flags: checkablealone",
        'Name: "nodejs"; Description: "Install portable Node.js runtime for Node Quillins'
        " and the Developer Console TypeScript interface (~30 MB);"
        ' not required for Python Quillins";'
        " Flags: checkablealone",
        'Name: "braillepack"; Description: "Install QUILL Braille Pack'
        " (liblouis translation engine, UEB, Standard American English,"
        ' and international braille profiles, ~15 MB)";'
        " Types: full custom; Flags: checkablealone",
        "",
        "[Files]",
        'Source: "..\\portable\\*"; DestDir: "{app}";'
        " Flags: ignoreversion recursesubdirs createallsubdirs;"
        ' Excludes: "docs\\QUILL-PRD.md,tools\\pandoc\\*,tools\\speech\\dectalk\\*,tools\\speech\\espeak-ng\\*,tools\\speech\\piper\\*,tools\\nodejs\\*,vendor\\braille-pack\\*,_tool-download\\*,_speech-download\\*"',
        "; QUILL Braille Pack: liblouis runtime, translation tables, and BRF profiles.",
        "; Installed to vendor\\braille-pack so QUILL detects it automatically via QUILL_APP_ROOT.",
        'Source: "..\\portable\\vendor\\braille-pack\\*"; DestDir: "{app}\\vendor\\braille-pack";'
        " Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist;"
        " Components: braillepack",
        'Source: "..\\portable\\tools\\pandoc\\*"; DestDir: "{app}\\tools\\pandoc";'
        " Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist;"
        " Components: pandoc",
        "; All DECtalk voices ship when the DECtalk component is selected.",
        'Source: "..\\portable\\tools\\speech\\dectalk\\*"; DestDir: "{app}\\tools\\speech\\dectalk";'
        " Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist;"
        " Components: speechdectalk",
        'Source: "..\\portable\\tools\\speech\\espeak-ng\\*"; DestDir: "{app}\\tools\\speech\\espeak-ng";'
        " Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist;"
        " Components: speechespeak",
        'Source: "..\\portable\\tools\\speech\\piper\\*"; DestDir: "{app}\\tools\\speech\\piper";'
        " Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist;"
        " Components: speechpiper",
        "; Node.js portable runtime (optional). The build script copies a portable",
        "; node.exe distribution into portable\\tools\\nodejs when building with",
        "; --bundle-nodejs. skipifsourcedoesntexist means a build without bundled",
        "; Node still works; users are offered WinGet installation in [Code] below.",
        'Source: "..\\portable\\tools\\nodejs\\*"; DestDir: "{app}\\tools\\nodejs";'
        " Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist;"
        " Components: nodejs",
        "",
        "[Icons]",
        'Name: "{group}\\{#AppName}"; Filename: "{app}\\python\\pythonw.exe"; Parameters: "-m quill"; WorkingDir: "{app}"; Check: FileExists(ExpandConstant(\'{app}\\python\\pythonw.exe\'))',
        'Name: "{group}\\{#AppName}"; Filename: "{app}\\{#AppExeName}"; WorkingDir: "{app}"; Check: not FileExists(ExpandConstant(\'{app}\\python\\pythonw.exe\'))',
        'Name: "{group}\\{#AppName} README"; Filename: "{app}\\README.txt"',
        ('Name: "{group}\\{#AppName} User Guide"; Filename: "{app}\\docs\\userguide.html"'),
        'Name: "{group}\\Uninstall {#AppName}"; Filename: "{uninstallexe}"',
        'Name: "{autodesktop}\\{#AppName}"; Filename: "{app}\\python\\pythonw.exe"; Parameters: "-m quill";'
        " WorkingDir: \"{app}\"; Tasks: desktopicon; Check: FileExists(ExpandConstant('{app}\\python\\pythonw.exe'))",
        'Name: "{autodesktop}\\{#AppName}"; Filename: "{app}\\{#AppExeName}";'
        " WorkingDir: \"{app}\"; Tasks: desktopicon; Check: not FileExists(ExpandConstant('{app}\\python\\pythonw.exe'))",
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
            ' ValueData: """{app}\\{#AppExeName}"" ""%1""";'
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
        'Filename: "{app}\\python\\pythonw.exe"; Parameters: "-m quill"; Description: "Launch {#AppName}";'
        " Flags: postinstall nowait skipifsilent unchecked; Check: FileExists(ExpandConstant('{app}\\python\\pythonw.exe'))",
        'Filename: "{app}\\{#AppExeName}"; Description: "Launch {#AppName}";'
        " Flags: postinstall nowait skipifsilent unchecked; Check: not FileExists(ExpandConstant('{app}\\python\\pythonw.exe'))",
        "",
        "[UninstallDelete]",
        "; Always remove install-dir build junk. Whether to also remove the",
        "; user's data in %APPDATA%\\Quill is decided by an explicit prompt in",
        "; [Code] below -- we never silently keep or wipe it.",
        'Type: filesandordirs; Name: "{app}\\__pycache__"',
        "; {app}\\python is the bundled embedded runtime: wholly owned by Quill,",
        "; no user data lives there (that's %APPDATA%\\Quill). Python generates",
        "; __pycache__ dirs across Lib\\site-packages on first run (the build",
        "; uses --no-compile), and those nest arbitrarily deep, so the only",
        "; reliable cleanup is removing the whole tree rather than chasing",
        "; specific __pycache__ paths.",
        'Type: filesandordirs; Name: "{app}\\python"',
        "",
        "[Code]",
        "// -- Skip component page for full installs ------------------------------------",
        "// Full install: skip component selection (everything is pre-selected).",
        "function ShouldSkipPage(PageID: Integer): Boolean;",
        "begin",
        "  Result := False;",
        "  if PageID = wpSelectComponents then",
        "    Result := (WizardSetupType(False) = 'full');",
        "end;",
        "",
        "// -- Post-install: write new-install marker + optional Node.js bootstrap --",
        "// The new-install marker tells the app to re-run the setup wizard on first",
        "// launch even when %APPDATA% settings from a prior install say it completed.",
        "// The Node.js check is opt-in (unchecked by default): fires only when the",
        "// user explicitly selected it and the portable node.exe was not bundled.",
        "procedure CurStepChanged(CurStep: TSetupStep);",
        "var",
        "  NodePath: String;",
        "  WingetResult: Integer;",
        "begin",
        "  if CurStep = ssPostInstall then",
        "  begin",
        "    SaveStringToFile(ExpandConstant('{app}\\quill-new-install.txt'), 'new-install', False);",
        "    if WizardIsComponentSelected('nodejs') then",
        "    begin",
        "      NodePath := ExpandConstant('{app}\\tools\\nodejs\\node.exe');",
        "      if not FileExists(NodePath) then",
        "      begin",
        "        if MsgBox(",
        "          'Node.js was not found in the bundled tools.' + #13#10 + #13#10 +",
        "          'Node.js is needed for Node Quillins and the Developer Console ' +",
        "          'TypeScript interface. Would you like Quill to install Node.js ' +",
        "          'LTS via Windows Package Manager (winget)?' + #13#10 + #13#10 +",
        "          'This requires an internet connection. Choose No to install Node.js ' +",
        "          'manually later from nodejs.org.',",
        "          mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then",
        "        begin",
        "          Exec(",
        "            ExpandConstant('{cmd}'),",
        "            '/C winget install --id OpenJS.NodeJS.LTS"
        " --accept-source-agreements --accept-package-agreements --silent',",
        "            '', SW_SHOW, ewWaitUntilTerminated, WingetResult);",
        "          if WingetResult <> 0 then",
        "            MsgBox(",
        "              'Node.js installation did not complete.' + #13#10 +",
        "              'You can install it manually from https://nodejs.org/ and Quill' +",
        "              ' will find it automatically.',",
        "              mbInformation, MB_OK);",
        "        end;",
        "      end;",
        "    end;",
        "  end;",
        "end;",
        "",
        "// -- Uninstall: ask before wiping personal data ----------------------------",
        "procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);",
        "var",
        "  DataDir: String;",
        "begin",
        "  if CurUninstallStep = usUninstall then",
        "  begin",
        "    DataDir := ExpandConstant('{userappdata}\\Quill');",
        "    if DirExists(DataDir) then",
        "    begin",
        "      if MsgBox('Also remove your Quill data?' + #13#10 + #13#10 +",
        "                'This deletes your settings, dictionaries, autosaves, backups,'"
        " + #13#10 +",
        "                'and onboarding state in:' + #13#10 + DataDir + #13#10 + #13#10 +",
        "                'Choose No to keep your documents and settings for a future' + #13#10 +",
        "                'reinstall. Choose Yes to remove everything.',",
        "                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then",
        "      begin",
        "        DelTree(DataDir, True, True, True);",
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
    expected_name = f"Quill-Setup-{version}.exe"
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

    # Copy the Quill package source into site-packages so `python -m quill`
    # works without requiring a separate wheel build.
    site_packages = target_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    quill_source = source_root / "quill"
    if not quill_source.is_dir():
        raise RuntimeError(f"Could not find quill/ package source under {source_root.resolve()}.")
    print(f"Copying Quill package source from {quill_source} into runtime...")
    shutil.copytree(quill_source, site_packages / "quill", dirs_exist_ok=True)

    _install_vendored_glow(python_exe, source_root)
    _prune_embedded_runtime(site_packages)

    archive.unlink(missing_ok=True)
    return target_dir


def _prune_embedded_runtime(site_packages: Path) -> None:
    """Remove packages that are only needed during the build, not at runtime.

    pip and setuptools are bootstrapped to install dependencies, then stripped
    so they don't bloat the installer.  The pywin32 extras (pythonwin, isapi,
    adodbapi, PyWin32.chm) are also removed.

    ``quill/devtools`` (the in-app Developer Console) and ``quill/tools``
    (``kqp_validator`` backs the runtime "Import Keyboard Pack" command) are
    imported by ``quill/ui`` and ``quill/core`` at runtime, so they must ship
    even though most of ``quill/tools`` is otherwise CI-only.
    """
    removable = [
        # Build tools - used during pip install, not at runtime (~155 MB)
        "pip",
        "pip-*",
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
    """Copy the braille pack into portable/vendor/braille-pack/. Returns True if staged."""
    if braille_pack_dir is None:
        default = (source_root or Path(".")) / "liblouis" / "vendor" / "braille" / "pack"
        if not default.is_dir():
            print(
                f"Warning: braille pack not found at {default}; skipping. "
                "Run scripts/build_braille_pack.py first or pass --braille-pack-dir."
            )
            return False
        braille_pack_dir = default
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


def _download_and_stage_dectalk_release(portable_dir: Path) -> Path:
    speech_root = portable_dir / "_speech-download" / "dectalk"
    speech_root.mkdir(parents=True, exist_ok=True)
    archive = speech_root / "vs2022.zip"
    print(f"Downloading DECtalk release from {DECTALK_RELEASE_ZIP_URL}...")
    _download_with_verification(
        DECTALK_RELEASE_ZIP_URL, archive, expected_sha256=DECTALK_RELEASE_ZIP_SHA256
    )

    extract_root = speech_root / "extracted"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract_root)

    # Prefer AMD64 runtime payload; keep the entire folder to preserve voices/dictionaries.
    amd64 = extract_root / "AMD64"
    if amd64.exists():
        return amd64
    return extract_root


def _speech_asset_manifest(
    portable_dir: Path, bundled_tools: list[str]
) -> dict[str, dict[str, object]]:
    speech_root = portable_dir / "tools" / "speech"
    manifest: dict[str, dict[str, object]] = {}
    engine_dirs = {
        "dectalk": "dectalk",
        "espeak": "espeak-ng",
        "piper": "piper",
    }
    for engine, dir_name in engine_dirs.items():
        engine_dir = speech_root / dir_name
        manifest[engine] = {
            "bundled": f"speech/{dir_name}" in bundled_tools,
            "path": str(engine_dir) if engine_dir.exists() else "",
            "exists": engine_dir.exists(),
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


def _download_and_stage_espeak(portable_dir: Path) -> Path:
    """Download eSpeak-NG for Windows and return a staging directory for _stage_bundled_tools.

    Tries the latest GitHub release first; falls back to the pinned version.
    Stages to portable/_tool-download/espeak/stage/ so _stage_bundled_tools()
    copies from there to tools/speech/espeak-ng/. Re-uses a prior download.
    Uses msiexec /a (administrative extract) to unpack the MSI without installing.
    """
    stage_dir = portable_dir / "_tool-download" / "espeak" / "stage"
    if (stage_dir / "espeak-ng.exe").exists():
        print("eSpeak-NG already downloaded; skipping.")
        return stage_dir

    url = _fetch_latest_github_asset_url("espeak-ng", "espeak-ng", ".msi") or ESPEAK_PINNED_URL
    sha256 = ESPEAK_PINNED_SHA256 if url == ESPEAK_PINNED_URL else None

    tmp_dir = portable_dir / "_tool-download" / "espeak"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    archive = tmp_dir / "espeak-ng.msi"
    print(f"Downloading eSpeak-NG from {url}...")
    _download_with_verification(url, archive, expected_sha256=sha256)

    extract_dir = tmp_dir / "extracted"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["msiexec", "/a", str(archive.resolve()), "/qn", f"TARGETDIR={extract_dir.resolve()}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"msiexec /a failed for eSpeak-NG MSI:\n{result.stderr}")

    exe_candidates = list(extract_dir.rglob("espeak-ng.exe"))
    if not exe_candidates:
        raise RuntimeError("eSpeak-NG MSI did not extract espeak-ng.exe")
    espeak_root = exe_candidates[0].parent
    stage_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(espeak_root, stage_dir, dirs_exist_ok=True)
    archive.unlink(missing_ok=True)
    print(f"eSpeak-NG staged to {stage_dir}")
    return stage_dir


def _download_and_stage_piper(portable_dir: Path) -> Path:
    """Download Piper TTS for Windows and return a staging directory for _stage_bundled_tools.

    Tries the latest GitHub release first; falls back to the pinned version.
    Stages to portable/_tool-download/piper/stage/ so _stage_bundled_tools()
    copies from there to tools/speech/piper/. Re-uses a prior download.
    """
    stage_dir = portable_dir / "_tool-download" / "piper" / "stage"
    if (stage_dir / "piper.exe").exists():
        print("Piper already downloaded; skipping.")
        return stage_dir

    url = (
        _fetch_latest_github_asset_url("rhasspy", "piper", "_windows_amd64.zip") or PIPER_PINNED_URL
    )
    sha256 = PIPER_PINNED_SHA256 if url == PIPER_PINNED_URL else None

    tmp_dir = portable_dir / "_tool-download" / "piper"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    archive = tmp_dir / "piper_windows_amd64.zip"
    print(f"Downloading Piper from {url}...")
    _download_with_verification(url, archive, expected_sha256=sha256)

    extract_dir = tmp_dir / "extracted"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract_dir)

    exe_candidates = list(extract_dir.rglob("piper.exe"))
    if not exe_candidates:
        raise RuntimeError("Piper zip did not contain piper.exe")
    piper_root = exe_candidates[0].parent
    stage_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(piper_root, stage_dir, dirs_exist_ok=True)
    archive.unlink(missing_ok=True)
    print(f"Piper staged to {stage_dir}")
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
    # quill/__init__.py is the authoritative version source; pyproject uses
    # hatchling dynamic version so project.version is not a static field.
    # Fall back to project.version in pyproject.toml if __init__.py isn't present
    # (e.g. in test sandboxes that create an isolated pyproject.toml).
    init_py = pyproject.parent / "quill" / "__init__.py"
    if init_py.exists():
        import re

        match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_py.read_text(), re.M)
        if match:
            return match.group(1)
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    project = data.get("project", {})
    if isinstance(project, dict):
        version = project.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    return "unknown"


if __name__ == "__main__":
    sys.exit(main())
