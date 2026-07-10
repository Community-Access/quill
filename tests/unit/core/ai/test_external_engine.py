"""Tests for the consented external-engine stdio boundary (AI-24)."""

from __future__ import annotations

import json
import subprocess

import pytest

from quill.core.ai import external_engine as ee


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    import quill.core.paths as paths_mod

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QUILL_DEV_BUILD", "1")
    monkeypatch.setattr(paths_mod, "_DEV_BUILD", True)
    return tmp_path


def _echo_runner(payload: dict) -> ee.Runner:
    def runner(command, stdin_text, timeout):
        request = json.loads(stdin_text)
        out = dict(payload)
        out.setdefault("echo", request)
        return 0, json.dumps(out) + "\n", ""

    return runner


def test_master_switch_off_by_default():
    assert ee.external_engines_enabled() is False
    config = ee.load_engine_config("a11y")
    assert config.enabled is False
    assert config.command == ()


def test_disabled_engine_takes_clean_unavailable_path():
    ee.set_external_engines_enabled(True)
    config = ee.load_engine_config("a11y")  # still per-engine disabled
    result = ee.run_request(config, ee.JsonlRequest("ping"))
    assert result.ok is False
    assert result.unavailable is True
    assert "off by default" in result.error


def test_master_off_blocks_even_enabled_engine():
    ee.save_engine_config(ee.EngineConfig("a11y", command=("node", "x.js"), enabled=True))
    config = ee.load_engine_config("a11y")
    status = ee.probe_engine(config, master_enabled=False)
    assert status.available is False
    assert "turned off" in status.reason


def test_missing_executable_is_unavailable():
    ee.set_external_engines_enabled(True)
    config = ee.set_engine_enabled("a11y", True)
    # "node" is on the allowlist; an allowed-but-missing binary is the test
    # case. The unallowed-executable path is covered by
    # ``test_probe_engine_rejects_unallowed_executable`` below.
    config = ee.EngineConfig("a11y", command=("node",), enabled=True)
    ee.save_engine_config(config)
    result = ee.run_request(
        ee.load_engine_config("a11y"),
        ee.JsonlRequest("ping"),
        which=lambda name: None,
    )
    assert result.unavailable is True
    assert "not found" in result.error


def test_successful_round_trip_with_injected_runner():
    ee.set_external_engines_enabled(True)
    ee.save_engine_config(ee.EngineConfig("a11y", command=("node", "engine.js"), enabled=True))
    config = ee.load_engine_config("a11y")
    result = ee.run_request(
        config,
        ee.JsonlRequest("audit", {"text": "hi"}),
        which=lambda name: "/usr/bin/node",
        runner=_echo_runner({"result": "ok"}),
    )
    assert result.ok is True
    assert result.response["result"] == "ok"
    assert result.response["echo"] == {"method": "audit", "params": {"text": "hi"}}


def test_engine_error_field_surfaces():
    ee.set_external_engines_enabled(True)
    ee.save_engine_config(ee.EngineConfig("a11y", command=("node", "x.js"), enabled=True))

    def runner(command, stdin_text, timeout):
        return 0, json.dumps({"error": "bad input"}) + "\n", ""

    result = ee.run_request(
        ee.load_engine_config("a11y"),
        ee.JsonlRequest("audit"),
        which=lambda name: "/usr/bin/node",
        runner=runner,
    )
    assert result.ok is False
    assert result.error == "bad input"


def test_nonzero_exit_reports_stderr():
    ee.set_external_engines_enabled(True)
    ee.save_engine_config(ee.EngineConfig("a11y", command=("node", "x.js"), enabled=True))

    def runner(command, stdin_text, timeout):
        return 2, "", "boom"

    result = ee.run_request(
        ee.load_engine_config("a11y"),
        ee.JsonlRequest("audit"),
        which=lambda name: "/usr/bin/node",
        runner=runner,
    )
    assert result.ok is False
    assert "boom" in result.error


def test_invalid_json_is_reported():
    ee.set_external_engines_enabled(True)
    ee.save_engine_config(ee.EngineConfig("a11y", command=("node", "x.js"), enabled=True))

    def runner(command, stdin_text, timeout):
        return 0, "not json\n", ""

    result = ee.run_request(
        ee.load_engine_config("a11y"),
        ee.JsonlRequest("audit"),
        which=lambda name: "/usr/bin/node",
        runner=runner,
    )
    assert result.ok is False
    assert "invalid JSON" in result.error


def test_timeout_is_reported():
    ee.set_external_engines_enabled(True)
    ee.save_engine_config(ee.EngineConfig("a11y", command=("node", "x.js"), enabled=True))

    def runner(command, stdin_text, timeout):
        raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)

    result = ee.run_request(
        ee.load_engine_config("a11y"),
        ee.JsonlRequest("audit"),
        which=lambda name: "/usr/bin/node",
        runner=runner,
    )
    assert result.ok is False
    assert "timed out" in result.error


def test_config_persists_round_trip():
    ee.set_external_engines_enabled(True)
    ee.save_engine_config(
        ee.EngineConfig("a11y", command=("node", "a.js"), enabled=True, description="A11y backend")
    )
    reloaded = ee.load_engine_config("a11y")
    assert reloaded.command == ("node", "a.js")
    assert reloaded.enabled is True
    assert reloaded.description == "A11y backend"
    assert ee.external_engines_enabled() is True


def test_list_engine_ids_is_sorted():
    ee.save_engine_config(ee.EngineConfig("zeta", command=("z",)))
    ee.save_engine_config(ee.EngineConfig("alpha", command=("a",)))
    ids = ee.list_engine_ids()
    # The list is sorted; we assert that alpha and zeta are present in
    # order, without coupling to whatever other engines prior tests in
    # the session may have left behind.
    assert "alpha" in ids and "zeta" in ids
    assert ids.index("alpha") < ids.index("zeta")


def test_configure_engine_parses_command_text():
    config = ee.configure_engine("helper", '  node "tool one.js" --flag ', enabled=True)
    assert config.engine_id == "helper"
    assert config.command == ("node", "tool one.js", "--flag")
    assert config.enabled is True
    assert ee.load_engine_config("helper").command == ("node", "tool one.js", "--flag")


def test_configure_engine_rejects_blank_id():
    with pytest.raises(ValueError):
        ee.configure_engine("   ", "node tool.js")


def test_configure_engine_rejects_unparseable_command():
    with pytest.raises(ValueError):
        ee.configure_engine("helper", 'node "unterminated')


def test_configure_engine_rejects_unallowed_executable():
    """H-2-core: a tampered settings file must not be able to launch arbitrary binaries."""
    with pytest.raises(ValueError) as excinfo:
        ee.configure_engine("helper", r"C:\Windows\System32\cmd.exe")
    assert "allowlist" in str(excinfo.value)
    # The bad config must not be persisted.
    assert ee.load_engine_config("helper").command == ()


def test_configure_engine_rejects_powershell_under_alias():
    """H-2-core: spoofed basenames are checked verbatim, not by extension only."""
    with pytest.raises(ValueError):
        ee.configure_engine("helper", "/usr/bin/powershell")


def test_probe_engine_rejects_unallowed_executable():
    """H-2-core: probe_engine surfaces a clean 'not in allowlist' unavailable path."""
    ee.set_external_engines_enabled(True)
    config = ee.EngineConfig("a11y", command=("definitely-not-on-allowlist",), enabled=True)
    ee.save_engine_config(config)
    status = ee.probe_engine(config, which=lambda name: "/usr/bin/x")
    assert status.available is False
    assert "allowlist" in status.reason


def test_configure_engine_accepts_node_executable():
    """H-2-core: canonical engine basenames are accepted."""
    config = ee.configure_engine(
        "a11y", "node engine.js", enabled=True, which=lambda _: "/usr/bin/node"
    )
    assert config.command == ("node", "engine.js")


def test_unresolvable_executable_rejected():
    """M-3: a short name that is not on PATH must be rejected at configure time."""
    with pytest.raises(ValueError, match="not found on PATH"):
        ee.configure_engine("a11y", "node engine.js", enabled=True, which=lambda _: None)


# ---------------------------------------------------------------------------
# macOS engine-path resolution: Homebrew dirs + nvm (#48)
# ---------------------------------------------------------------------------


def test_resolve_which_finds_homebrew_node_on_macos(monkeypatch, tmp_path):
    """A Finder-launched .app gets a minimal PATH, so a Homebrew node install
    at /opt/homebrew/bin is invisible to shutil.which but resolvable here."""
    monkeypatch.setattr(ee.sys, "platform", "darwin")
    monkeypatch.setattr(ee.shutil, "which", lambda _name: None)
    bin_dir = tmp_path / "opt-homebrew-bin"
    bin_dir.mkdir()
    (bin_dir / "node").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(ee, "_MACOS_FALLBACK_DIRS", (str(bin_dir),))
    assert ee._resolve_which("node") == str(bin_dir / "node")


def test_resolve_which_finds_nvm_node_on_macos(monkeypatch, tmp_path):
    """nvm keeps per-version node binaries under ~/.nvm/versions/node/<ver>/bin;
    the highest installed version wins."""
    import quill.core.node_install as ni

    monkeypatch.setattr(ee.sys, "platform", "darwin")
    monkeypatch.setattr(ee.shutil, "which", lambda _name: None)
    monkeypatch.setattr(ee, "_MACOS_FALLBACK_DIRS", ())
    monkeypatch.setattr(ni, "node_executable_path", lambda: None)
    nvm_root = tmp_path / ".nvm" / "versions" / "node"
    v18 = nvm_root / "v18.20.0" / "bin"
    v20 = nvm_root / "v20.10.0" / "bin"
    v20.mkdir(parents=True)
    v18.mkdir(parents=True)
    (v20 / "node").write_text("x", encoding="utf-8")
    (v18 / "node").write_text("x", encoding="utf-8")
    monkeypatch.setattr(ee.Path, "home", lambda: tmp_path)
    assert ee._resolve_which("node") == str(v20 / "node")


def test_resolve_which_skips_macos_fallback_on_windows(monkeypatch, tmp_path):
    """On Windows the macOS well-known dirs are not consulted (#48)."""
    import quill.core.node_install as ni

    monkeypatch.setattr(ee.sys, "platform", "win32")
    monkeypatch.setattr(ee.shutil, "which", lambda _name: None)
    bin_dir = tmp_path / "usr-local-bin"
    bin_dir.mkdir()
    (bin_dir / "node").write_text("x", encoding="utf-8")
    monkeypatch.setattr(ee, "_MACOS_FALLBACK_DIRS", (str(bin_dir),))
    monkeypatch.setattr(ni, "node_executable_path", lambda: None)
    assert ee._resolve_which("node") is None
