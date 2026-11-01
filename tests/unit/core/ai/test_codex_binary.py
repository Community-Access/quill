"""The bundled Codex app-server lookup and its launch-time hash pin."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

from quill.core.ai import codex_binary as cb


def _exe(directory: Path, content: bytes = b"MZ") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    exe = directory / cb.CODEX_APP_SERVER_EXE
    exe.write_bytes(content)
    return exe


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    monkeypatch.setattr(sys, "executable", str(tmp_path / "rt" / "python.exe"))
    return tmp_path


def test_search_order_is_app_root_then_the_interpreter_folder(isolated: Path) -> None:
    assert cb.codex_search_dirs() == [
        isolated / "app" / "tools" / "codex",
        isolated / "rt" / "tools" / "codex",
    ]


def test_app_root_wins_when_both_carry_one(isolated: Path) -> None:
    _exe(isolated / "rt" / "tools" / "codex")
    exe = _exe(isolated / "app" / "tools" / "codex")
    assert cb.find_codex_app_server() == exe


def test_falls_back_to_the_runtime_folder(isolated: Path) -> None:
    exe = _exe(isolated / "rt" / "tools" / "codex")
    assert cb.find_codex_app_server() == exe


def test_none_when_nothing_is_bundled_and_path_is_never_consulted(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A codex somewhere on the host is not one QUILL shipped."""
    on_path = _exe(isolated / "elsewhere")
    monkeypatch.setenv("PATH", str(on_path.parent))
    assert cb.find_codex_app_server() is None


def test_without_app_root_only_the_interpreter_folder_is_searched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python.exe"))
    assert cb.codex_search_dirs() == [tmp_path / "tools" / "codex"]


def test_the_pin_is_a_sha256_and_the_version_a_release_number() -> None:
    assert re.fullmatch(r"[0-9a-f]{64}", cb.CODEX_APP_SERVER_SHA256)
    assert re.fullmatch(r"\d+\.\d+\.\d+", cb.CODEX_VERSION)


def test_file_sha256_matches_hashlib(tmp_path: Path) -> None:
    data = b"codex" * 300_000  # spans several read chunks
    path = tmp_path / "blob"
    path.write_bytes(data)
    assert cb.file_sha256(path) == hashlib.sha256(data).hexdigest()


def test_matches_pin_accepts_only_the_pinned_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = _exe(tmp_path, b"the pinned build")
    monkeypatch.setattr(
        cb, "CODEX_APP_SERVER_SHA256", hashlib.sha256(b"the pinned build").hexdigest()
    )
    assert cb.codex_app_server_matches_pin(exe) is True
    exe.write_bytes(b"something else")
    assert cb.codex_app_server_matches_pin(exe) is False


def test_matches_pin_is_false_for_a_missing_file(tmp_path: Path) -> None:
    assert cb.codex_app_server_matches_pin(tmp_path / "absent.exe") is False
