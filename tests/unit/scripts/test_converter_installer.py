"""Quill Converter 1.0.0 ships an installer and a portable zip that need nothing else.

Source-level guards on the packaging, in the shape Radio's and QUILL Lite's
builds are held to: two artifacts, the shared runtime with FFmpeg staged,
everything bundled so first use downloads nothing, no feedback token, and an
Explorer verb block generated from the format catalogue rather than typed.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_APP = _ROOT / "standalone" / "converter"
_ISS = _APP / "installer" / "quill-converter.iss"
_BUILD = _APP / "scripts" / "build_release.ps1"


def _load_build_portable():
    name = "quill_build_portable_converter"
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_release_files_exist() -> None:
    for rel in (
        "LICENSE",
        ".gitignore",
        "installer/quill-converter.iss",
        "installer/explorer-verb.isi",
        "installer/edition-installer-full.txt",
        "scripts/build_release.ps1",
        "scripts/render_docs.ps1",
        "docs/CHANGELOG.md",
    ):
        assert (_APP / rel).is_file(), rel


def test_portable_bundles_everything_and_no_token() -> None:
    product = _load_build_portable().PRODUCTS["converter"]
    assert product.feedback_token is False
    assert "feedback" not in product.dep_groups
    # yt-dlp (Convert from URL) and mutagen (cover art) ship inside: no download.
    assert "youtube" in product.dep_groups and "mp3" in product.dep_groups
    assert product.stage_ffmpeg and product.stage_mpv  # mpv plays in the Chapter Workbench


def test_installer_version_matches_the_app_and_the_build() -> None:
    from quill.apps import converter

    iss = _ISS.read_text(encoding="utf-8")
    build = _BUILD.read_text(encoding="utf-8")
    assert f'#define AppVersion "{converter._VERSION}"' in iss
    assert f'$version = "{converter._VERSION}"' in build
    assert f"VersionInfoVersion={converter._VERSION}.0" in iss


def test_installer_ships_ffmpeg_and_the_explorer_verb_task() -> None:
    iss = _ISS.read_text(encoding="utf-8")
    assert "#define ToolFfmpeg" in iss and "#define ToolMpv" in iss  # mpv: the Workbench
    assert '#define AppRefId "converter"' in iss
    assert '#include "explorer-verb.isi"' in iss
    # A native checkbox (TNewCheckBox), checked by default -- never a [Tasks]
    # entry, which screen readers read as "not checked" whatever its state.
    assert "ExplorerVerbCheck.Checked := True;" in iss
    assert "function WantsExplorerVerb(): Boolean;" in iss
    assert iss.index('#include "explorer-verb.isi"') < iss.index('shared-runtime.iss"')
    assert "OutputBaseFilename=Quill-Converter-Setup-Shared-{#AppVersion}" in iss


def test_explorer_verb_block_is_current() -> None:
    completed = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "build_converter_verb_iss.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_explorer_verb_covers_every_media_extension_and_uninstalls() -> None:
    from quill.core.shell_verbs import MEDIA_EXTENSIONS

    block = (_APP / "installer" / "explorer-verb.isi").read_text(encoding="utf-8")
    for ext in MEDIA_EXTENSIONS:
        assert f"SystemFileAssociations\\{ext}\\shell\\QuillConverter.Convert" in block, ext
    assert block.count("uninsdeletekey") == len(MEDIA_EXTENSIONS)
    assert "Tasks:" not in block and "Check: WantsExplorerVerb" in block
    assert "Root: HKCU" in block and "HKLM" not in block


def test_build_stages_ffmpeg_proves_bundled_libraries_and_uses_no_token() -> None:
    build = _BUILD.read_text(encoding="utf-8")
    assert "Stage-QuillMediaTools -RuntimeDist $sharedRuntimeDist -FfmpegDir $FfmpegDir" in build
    assert "import yt_dlp, mutagen" in build
    assert "Assert-QuillRuntimeHasModule" in build
    assert "--product converter" in build
    assert "generate_feedback_token" not in build and "TokenFile" not in build


def test_runtime_freezes_mutagen_for_the_installed_app() -> None:
    spec = (_ROOT / "standalone" / "runtime" / "quillville-runtime.spec").read_text(
        encoding="utf-8"
    )
    assert 'collect_submodules("mutagen")' in spec and "mutagen_hidden" in spec
    assert 'collect_all("yt_dlp")' in spec
