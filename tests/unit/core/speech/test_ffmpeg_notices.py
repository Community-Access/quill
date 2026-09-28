"""FFmpeg ships with its licence, wherever QUILL puts it.

The bundled FFmpeg is a GPLv3 build. Until 2026-09-28 every family bundle and
QUILL's own on-demand install carried the executables and neither the licence
nor the source offer. One copy of both lives in the package; the standalone
builds stage it (scripts/StageMediaTools.ps1) and the install writes it out.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.ffmpeg_install import write_license_notices

_ROOT = Path(__file__).resolve().parents[4]


def test_the_install_writes_the_licence_and_source_offer(tmp_path: Path) -> None:
    write_license_notices(tmp_path)
    licence = (tmp_path / "LICENSE.GPLv3.txt").read_text(encoding="utf-8")
    offer = (tmp_path / "README-SOURCE.txt").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in licence and "Version 3" in licence
    assert "ffmpeg-8.1.2" in offer and "support@community-access.org" in offer


def test_the_offer_names_the_pinned_build() -> None:
    from quill.core.speech.ffmpeg_install import FFMPEG_PINNED_SHA256, FFMPEG_PINNED_VERSION

    offer = (_ROOT / "quill/data/notices/ffmpeg/README-SOURCE.txt").read_text(encoding="utf-8")
    # A version bump must update the source offer in the same change.
    assert f"FFmpeg {FFMPEG_PINNED_VERSION}" in offer
    assert FFMPEG_PINNED_SHA256 in offer


def test_the_standalone_builds_stage_the_same_files() -> None:
    script = (_ROOT / "scripts/StageMediaTools.ps1").read_text(encoding="utf-8")
    assert "quill\\data\\notices\\ffmpeg" in script
