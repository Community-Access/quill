"""Install planner for the optional SDK harness packs (Phase 10)."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

from quill.ai_packs import all_packs
from quill.core.ai.sdk_install import (
    BUNDLED_PACKS,
    PACK_INSTALLS,
    PackInstall,
    PackInstallError,
    ai_packs_dir,
    install_command,
    install_pack,
    is_pack_importable,
    known_pack_ids,
    manual_install_hint,
    pack_dir,
    pack_install_for,
    pack_is_bundled,
    run_install,
)


def test_specs_cover_every_optional_pack() -> None:
    # Every optional pack (everything except always-present Native) is either
    # bundled or has an install spec, and the keys match the packs' own ids.
    assert set(known_pack_ids()) == {p.id for p in all_packs()}
    assert not set(BUNDLED_PACKS) & set(PACK_INSTALLS)


def test_copilot_is_bundled_and_never_installed_on_demand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # codex.md 10A.12: the SDK ships in the shared runtime; nothing downloads.
    assert "copilot" not in PACK_INSTALLS
    assert pack_is_bundled("copilot")
    assert pack_install_for("copilot") is None
    by_id = {p.id: p for p in all_packs()}
    assert (BUNDLED_PACKS["copilot"],) == by_id["copilot"].sdk_modules
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    calls: list[object] = []
    with pytest.raises(PackInstallError, match="nothing to install"):
        install_pack("copilot", runner=lambda *a, **k: calls.append(a))
    assert calls == []


def test_copilot_sdk_is_pinned_in_the_runtime_extra() -> None:
    import tomllib

    root = Path(__file__).resolve().parents[4]
    optional = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "optional-dependencies"
    ]
    assert optional["ai-copilot"] == ["github-copilot-sdk==1.0.28"]
    assert "quill[ai-copilot]" in optional["runtime"]


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
    cmd = install_command("claude_agent_sdk")
    assert cmd[0] == sys.executable
    assert cmd[1:4] == ["-m", "pip", "install"]
    assert cmd[-1] == "quill[ai-claude]"


def test_manual_hint_is_copy_pasteable() -> None:
    assert manual_install_hint("claude_agent_sdk") == 'pip install "quill[ai-claude]"'


def test_run_install_success() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> tuple[int, str]:
        calls.append(argv)
        return 0, "Successfully installed claude-agent-sdk-0.2"

    result = run_install("claude_agent_sdk", runner=runner)
    assert result.ok and result.exit_code == 0
    assert calls == [install_command("claude_agent_sdk")]
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

    result = run_install("claude_agent_sdk", runner=runner)
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
    assert pack_dir("openai_agents").name == "openai_agents"
    assert ai_packs_dir() in pack_dir("openai_agents").parents


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
        install_pack("claude_agent_sdk", dest_dir=tmp_path / "claude", runner=runner)
    cmd = seen["command"]
    assert "--only-binary=:all:" in cmd
    assert "--target" in cmd
    assert cmd[-1] == "claude-agent-sdk>=0.1.0"


def test_install_pack_blocked_in_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(PackInstallError, match="Safe Mode"):
        install_pack("openai_agents", runner=_ok_result)


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


def test_is_pack_importable_detects_crash_interrupted_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression (support report): after Quill crashed mid on-demand SDK
    install, the OpenAI engine "shows up as being active" but is unusable and
    unswitchable. A ``pip install --target`` interrupted by the host process
    dying can leave a package's ``__init__.py`` written while the rest of it
    is missing: ``find_spec`` alone is satisfied (the file is right there),
    but the module cannot actually import. ``is_pack_importable`` must catch
    that, or a crashed install is reported "installed" forever with no signal
    telling the Hub to offer Set Up again.
    """
    pkg_dir = tmp_path / "quill_crashed_sdk_pack"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text(
        "from . import never_written_submodule\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("quill_crashed_sdk_pack", None)
    importlib.invalidate_caches()

    fake_spec = PackInstall(
        pack_id="crashed_test_pack",
        display_name="Crashed Test Pack",
        extra="ai-crashed-test",
        requirement="crashed-test-pack>=0.1",
        import_name="quill_crashed_sdk_pack",
    )
    monkeypatch.setitem(PACK_INSTALLS, "crashed_test_pack", fake_spec)

    assert is_pack_importable("crashed_test_pack") is False
