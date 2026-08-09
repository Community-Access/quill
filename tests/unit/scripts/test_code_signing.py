"""Unit tests for scripts/code_signing.py (Authenticode signing helper).

These never touch the real signing service or a certificate: they exercise the
argv construction, the opt-in / fail-open contract, discovery ordering, and file
collection. The one live end-to-end signing path is a manual/CI concern
documented in docs/code-signing.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import code_signing as cs


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "QUILL_SIGN",
        "QUILL_SIGN_REQUIRED",
        "QUILL_SIGN_METADATA",
        "QUILL_SIGN_PATTERNS",
    ):
        monkeypatch.delenv(var, raising=False)


def _fake_config(tmp_path: Path) -> cs.SigningConfig:
    # Keep the fake toolchain out of any directory a test then walks for *.exe/
    # *.dll, so collect_files never mistakes signtool.exe/dlib.dll for payload.
    toolchain = tmp_path / "_toolchain"
    toolchain.mkdir(exist_ok=True)
    signtool = toolchain / "signtool.exe"
    dlib = toolchain / "dlib.dll"
    meta = toolchain / "metadata.json"
    for path in (signtool, dlib, meta):
        path.write_text("x", encoding="utf-8")
    return cs.SigningConfig(signtool=signtool, dlib=dlib, metadata=meta)


def test_env_flags(monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    assert not cs.signing_requested()
    assert not cs.signing_required()
    monkeypatch.setenv("QUILL_SIGN", "1")
    assert cs.signing_requested()
    monkeypatch.setenv("QUILL_SIGN_REQUIRED", "TRUE")
    assert cs.signing_required()
    monkeypatch.setenv("QUILL_SIGN", "no")
    assert not cs.signing_requested()


def test_default_patterns_override(monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    assert cs.default_patterns() == cs.DEFAULT_SIGN_PATTERNS
    monkeypatch.setenv("QUILL_SIGN_PATTERNS", "*.exe; *.dll ,*.pyd")
    assert cs.default_patterns() == ("*.exe", "*.dll", "*.pyd")
    monkeypatch.setenv("QUILL_SIGN_PATTERNS", "   ")
    assert cs.default_patterns() == cs.DEFAULT_SIGN_PATTERNS


def test_sign_command_shape(tmp_path: Path) -> None:
    config = _fake_config(tmp_path)
    target = tmp_path / "a.exe"
    target.write_text("x", encoding="utf-8")
    command = cs._sign_command(config, [target])
    # signtool first, then the digest + timestamp + dlib/metadata switches, files last.
    assert command[0] == str(config.signtool)
    assert command[1] == "sign"
    assert command[command.index("/fd") + 1] == "SHA256"
    assert command[command.index("/td") + 1] == "SHA256"
    assert command[command.index("/tr") + 1] == config.timestamp_url
    assert command[command.index("/dlib") + 1] == str(config.dlib)
    assert command[command.index("/dmdf") + 1] == str(config.metadata)
    assert command[-1] == str(target)


def test_collect_files_matches_patterns(tmp_path: Path) -> None:
    (tmp_path / "app.exe").write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "lib.dll").write_text("x", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    (tmp_path / "ext.pyd").write_text("x", encoding="utf-8")
    default = cs.collect_files(tmp_path)
    assert {p.name for p in default} == {"app.exe", "lib.dll"}
    widened = cs.collect_files(tmp_path, ("*.exe", "*.dll", "*.pyd"))
    assert {p.name for p in widened} == {"app.exe", "lib.dll", "ext.pyd"}


def test_sign_paths_skips_when_not_requested(
    monkeypatch: pytest.MonkeyPatch, clean_env: None, tmp_path: Path
) -> None:
    called = False

    def _boom(*_a: object, **_k: object) -> cs.SigningConfig:
        nonlocal called
        called = True
        raise AssertionError("resolve_config must not run when signing is off")

    monkeypatch.setattr(cs, "resolve_config", _boom)
    assert cs.sign_paths([tmp_path / "a.exe"]) == []
    assert not called


def test_sign_paths_fail_open(
    monkeypatch: pytest.MonkeyPatch, clean_env: None, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_SIGN", "1")

    def _fail() -> cs.SigningConfig:
        raise cs.SigningError("signtool not found")

    monkeypatch.setattr(cs, "resolve_config", _fail)
    monkeypatch.setattr(cs, "azure_credential_available", lambda: False)
    # Fail-open: no exception, returns nothing signed.
    assert cs.sign_paths([tmp_path], label="test") == []


def test_sign_paths_fail_closed_when_required(
    monkeypatch: pytest.MonkeyPatch, clean_env: None, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_SIGN", "1")
    monkeypatch.setenv("QUILL_SIGN_REQUIRED", "1")

    def _fail() -> cs.SigningConfig:
        raise cs.SigningError("signtool not found")

    monkeypatch.setattr(cs, "resolve_config", _fail)
    with pytest.raises(cs.SigningError):
        cs.sign_paths([tmp_path], label="test")


def test_sign_paths_require_forces_on(
    monkeypatch: pytest.MonkeyPatch, clean_env: None, tmp_path: Path
) -> None:
    # require=True must force signing on even without QUILL_SIGN, and then fail
    # closed on a resolve error.
    def _fail() -> cs.SigningError:
        raise cs.SigningError("nope")

    monkeypatch.setattr(cs, "resolve_config", _fail)
    with pytest.raises(cs.SigningError):
        cs.sign_paths([tmp_path], require=True)


def test_sign_paths_signs_collected_files(
    monkeypatch: pytest.MonkeyPatch, clean_env: None, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_SIGN", "1")
    config = _fake_config(tmp_path)
    monkeypatch.setattr(cs, "resolve_config", lambda: config)
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "app.exe").write_text("x", encoding="utf-8")
    (payload / "lib.dll").write_text("x", encoding="utf-8")
    (payload / "skip.txt").write_text("x", encoding="utf-8")

    seen: list[Path] = []
    monkeypatch.setattr(cs, "sign_files", lambda files, cfg: seen.extend(files) or list(files))
    signed = cs.sign_paths([payload], label="test")
    assert {p.name for p in signed} == {"app.exe", "lib.dll"}
    assert {p.name for p in seen} == {"app.exe", "lib.dll"}


def test_version_key_orders_sdk_builds() -> None:
    assert cs._version_key("10.0.26100.0") > cs._version_key("10.0.22621.0")
    assert cs._version_key("10.0.22621.0") > cs._version_key("10.0.19041.0")
