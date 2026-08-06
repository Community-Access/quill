"""Tests for tools/generate_adp_client_key.py (bundled ADP client key)."""

from __future__ import annotations

from pathlib import Path

import generate_adp_client_key as gen


def test_write_module_with_key(tmp_path: Path) -> None:
    output = tmp_path / "_adp_client_key.py"
    gen.write_module("1a77deadbeef", output)
    text = output.read_text("utf-8")
    assert "BUNDLED_ADP_CLIENT_KEY = '1a77deadbeef'" in text


def test_write_module_without_key_writes_empty_string(tmp_path: Path) -> None:
    output = tmp_path / "_adp_client_key.py"
    gen.write_module("", output)
    assert "BUNDLED_ADP_CLIENT_KEY = ''" in output.read_text("utf-8")


def test_resolve_key_reads_env_then_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_ADP_CLIENT_KEY", "from-env")
    assert gen.resolve_key() == "from-env"

    monkeypatch.delenv("QUILL_ADP_CLIENT_KEY", raising=False)
    key_file = tmp_path / "adp.key"
    key_file.write_text("  from-file\n", encoding="utf-8")
    monkeypatch.setenv("QUILL_ADP_CLIENT_KEY_FILE", str(key_file))
    assert gen.resolve_key() == "from-file"


def test_main_is_always_lenient_without_a_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("QUILL_ADP_CLIENT_KEY", raising=False)
    monkeypatch.delenv("QUILL_ADP_CLIENT_KEY_FILE", raising=False)
    output = tmp_path / "_adp_client_key.py"
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main([]) == 0
    assert "BUNDLED_ADP_CLIENT_KEY = ''" in output.read_text("utf-8")


def test_main_preserves_an_existing_key_when_env_is_unset(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("QUILL_ADP_CLIENT_KEY", raising=False)
    monkeypatch.delenv("QUILL_ADP_CLIENT_KEY_FILE", raising=False)
    output = tmp_path / "_adp_client_key.py"
    gen.write_module("previously-baked", output)
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main([]) == 0
    assert gen.read_existing_key(output) == "previously-baked"
