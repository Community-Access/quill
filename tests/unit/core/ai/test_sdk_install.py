"""Install planner for the optional SDK harness packs (Phase 10)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from quill.ai_packs import all_packs
from quill.core.ai.sdk_install import (
    PACK_INSTALLS,
    PackInstallError,
    ai_packs_dir,
    install_command,
    install_pack,
    manual_install_hint,
    pack_dir,
    pack_install_for,
    run_install,
)


def test_specs_cover_every_optional_pack() -> None:
    # Every optional pack (everything except always-present Native) has an install
    # spec, and the keys match the packs' own ids.
    assert set(PACK_INSTALLS) == {p.id for p in all_packs()}


def test_specs_match_pyproject_extras_and_imports() -> None:
    # The probe module and extra recorded here must match each pack's declaration,
    # so a planned install actually makes the pack importable.
    by_id = {p.id: p for p in all_packs()}
    for pack_id, spec in PACK_INSTALLS.items():
        pack = by_id[pack_id]
        assert spec.extra == pack.extra
        assert (spec.import_name,) == pack.sdk_modules


def test_native_has_no_install_spec() -> None:
    assert pack_install_for("native") is None


def test_pip_target_and_command_target_running_interpreter() -> None:
    cmd = install_command("copilot")
    assert cmd[0] == sys.executable
    assert cmd[1:4] == ["-m", "pip", "install"]
    assert cmd[-1] == "quill[ai-copilot]"


def test_manual_hint_is_copy_pasteable() -> None:
    assert manual_install_hint("claude_agent_sdk") == 'pip install "quill[ai-claude]"'


def test_run_install_success() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> tuple[int, str]:
        calls.append(argv)
        return 0, "Successfully installed github-copilot-sdk-1.0"

    result = run_install("copilot", runner=runner)
    assert result.ok and result.exit_code == 0
    assert calls == [install_command("copilot")]
    assert "ready" in result.message().lower()


def test_run_install_failure_reports_last_line() -> None:
    def runner(argv: list[str]) -> tuple[int, str]:
        return 1, "Collecting...\nERROR: No matching distribution found"

    result = run_install("openai_agents", runner=runner)
    assert not result.ok
    assert "No matching distribution" in result.error
    assert "Could not install" in result.message()


def test_run_install_contains_runner_exception() -> None:
    def runner(argv: list[str]) -> tuple[int, str]:
        raise OSError("pip is missing")

    result = run_install("copilot", runner=runner)
    assert not result.ok
    assert "pip is missing" in result.error


def test_run_install_unknown_pack() -> None:
    result = run_install("nope", runner=lambda argv: (0, ""))
    assert not result.ok and "Unknown" in result.error


# -- engine-pack install (frozen-build-safe) --------------------------------


def _ok_result(command, *, timeout_seconds):  # type: ignore[no-untyped-def]
    return subprocess.CompletedProcess(command, 0, stdout="Successfully installed", stderr="")


def test_pack_dir_under_app_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assert ai_packs_dir().name == "ai-packs"
    assert pack_dir("copilot").name == "copilot"
    assert ai_packs_dir() in pack_dir("copilot").parents


def test_install_pack_runs_wheel_only_target_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    seen: dict[str, object] = {}

    def runner(command, *, timeout_seconds):  # type: ignore[no-untyped-def]
        seen["command"] = list(command)
        return _ok_result(command, timeout_seconds=timeout_seconds)

    # The pack imports during verification; the SDK is not installed in CI, so
    # install_pack raises at the import check after the (faked) pip run. We assert
    # on the command that was issued, which is the security-relevant surface.
    with pytest.raises(PackInstallError):
        install_pack("copilot", dest_dir=tmp_path / "copilot", runner=runner)
    cmd = seen["command"]
    assert "--only-binary=:all:" in cmd
    assert "--target" in cmd
    assert cmd[-1] == "github-copilot-sdk>=1.0"


def test_install_pack_blocked_in_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(PackInstallError, match="Safe Mode"):
        install_pack("copilot", runner=_ok_result)


def test_install_pack_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    with pytest.raises(PackInstallError, match="Unknown"):
        install_pack("nope", runner=_ok_result)


def test_install_pack_reports_pip_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    def runner(command, *, timeout_seconds):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            command, 1, stdout="", stderr="ERROR: No matching distribution"
        )

    with pytest.raises(PackInstallError, match="No matching distribution"):
        install_pack("openai_agents", dest_dir=tmp_path / "o", runner=runner)
