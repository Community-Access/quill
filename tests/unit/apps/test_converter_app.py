"""Tests for the standalone Quill Converter app (#1255)."""

from __future__ import annotations

from pathlib import Path

from quill.core import app_launcher as al
from quill.ui import quillville_menu as qv

_CONVERTER = Path(__file__).resolve().parents[3] / "quill" / "apps" / "converter.py"


# --------------------------------------------------------------------------- #
# Launcher / registry (pure)
# --------------------------------------------------------------------------- #


def test_converter_registered_in_launcher() -> None:
    assert "converter" in al.APP_NAMES
    assert al.app_name("converter") == "Quill Converter"
    assert al.portable_sibling_dirname("converter") == "QuillConverter"


def test_build_launch_argv_from_source_runs_the_module(monkeypatch) -> None:
    monkeypatch.setattr(al.sys, "frozen", False, raising=False)
    argv = al.build_launch_argv("converter")
    assert argv is not None
    assert argv[1:] == ["-m", "quill.apps.converter"]


def test_converter_is_ordered_and_released() -> None:
    # Released publicly with 1.0.0 (2026-09-27): siblings advertise it.
    assert "converter" in qv.QUILLVILLE_APP_ORDER
    assert "converter" in qv.RELEASED_APPS


# --------------------------------------------------------------------------- #
# App wiring (source scrape -- no wx App needed)
# --------------------------------------------------------------------------- #


def _src() -> str:
    # The window, its menu bar and its commands are three modules since 1.0.0.
    modules = sorted(_CONVERTER.parent.glob("converter*.py"))
    return "\n".join(path.read_text(encoding="utf-8") for path in modules)


def test_app_reuses_shared_converter_logic() -> None:
    src = _src()
    # Reuses the tested engine + orchestration, does not reimplement it.
    assert "from quill.core.audio.convert import" in src
    assert "plan_jobs(" in src and "run_conversion_batch(" in src
    # URL import: one video through the shared orchestration; playlists and
    # channels through url_collections (2026-09-28).
    assert "_download_then_convert(self, url)" in src
    assert "download_collection(" in src
    # View > Advanced Options shows the encoder settings in the main window
    # (2026-09-27); the separate Convert Audio dialog is no longer opened.
    assert "converter_advanced.apply(self, spec)" in src
    assert "run_audio_conversion(" not in src


def test_app_shell_and_bootstrap_present() -> None:
    src = _src()
    frame_class = (
        "class QuillConverterFrame(\n"
        "    ConverterUrlMixin, ConverterChaptersMixin, ConverterActionsMixin, AppShellFrame\n"
        "):"
    )
    assert frame_class in src
    assert "def _run_background_task(" in src  # self-contained batch runner
    assert "def main() -> int:" in src
    assert "try_claim_primary_instance(slot=_IPC_SLOT)" in src  # single instance
    assert "_ensure_tray_icon(" in src  # tray resident


def test_app_pickers_carry_exempt_pragma() -> None:
    # Stock wx.FileDialog / wx.DirDialog ShowModal calls are exempt-tagged.
    assert _src().count("dialog_button_contract: exempt") >= 3
