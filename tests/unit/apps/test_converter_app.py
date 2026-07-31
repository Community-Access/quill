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


def test_converter_in_quillville_order_but_not_yet_released() -> None:
    # Ordered (so siblings know about it) but unreleased -> not advertised yet,
    # exactly like cast/studio.
    assert "converter" in qv.QUILLVILLE_APP_ORDER
    assert "converter" not in qv.RELEASED_APPS


# --------------------------------------------------------------------------- #
# App wiring (source scrape -- no wx App needed)
# --------------------------------------------------------------------------- #


def _src() -> str:
    return _CONVERTER.read_text(encoding="utf-8")


def test_app_reuses_shared_converter_logic() -> None:
    src = _src()
    # Reuses the tested engine + orchestration, does not reimplement it.
    assert "from quill.core.audio.convert import" in src
    assert "build_request" in src and "plan_and_run(self, request)" in src
    assert "run_url_conversion(self)" in src  # URL import
    assert "run_audio_conversion(self, initial_entries=" in src  # Advanced -> full dialog


def test_app_shell_and_bootstrap_present() -> None:
    src = _src()
    assert "class QuillConverterFrame(AppShellFrame)" in src
    assert "def _run_background_task(" in src  # self-contained batch runner
    assert "def main() -> int:" in src
    assert "try_claim_primary_instance(slot=_IPC_SLOT)" in src  # single instance
    assert "_ensure_tray_icon(" in src  # tray resident


def test_app_pickers_carry_exempt_pragma() -> None:
    # Stock wx.FileDialog / wx.DirDialog ShowModal calls are exempt-tagged.
    assert _src().count("dialog_button_contract: exempt") >= 3
