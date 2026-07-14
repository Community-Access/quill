"""Tests for the QVP pack loader, validator, and install flow (§20-§21)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.verbosity import qvp as qvp_module
from quill.core.verbosity.qvp import (
    KIND,
    QVPError,
    install_pack,
    load_pack,
    parse_pack,
)


def _pack(**overrides: object) -> dict:
    base: dict = {
        "schema_version": "1",
        "kind": KIND,
        "min_quill_version": "0.7.0",
        "pack": {
            "name": "Concise Nav",
            "author": "Kelly Ford",
            "description": "Tighter navigation announcements.",
            "version": "1.0",
            "license": "MIT",
        },
        "templates": [
            {
                "id": "concise.next_line",
                "name": "Concise next line",
                "applies_to": "nav.next_line",
                "template": "L{line}",
            }
        ],
    }
    base.update(overrides)
    return base


# --- parse / schema ------------------------------------------------------


def test_parse_valid_pack() -> None:
    pack = parse_pack(_pack())
    assert pack.kind == KIND
    assert pack.author == "Kelly Ford"
    assert len(pack.templates) == 1
    assert pack.templates[0].applies_to == "nav.next_line"


def test_load_pack_from_json_text() -> None:
    pack = load_pack(json.dumps(_pack()))
    assert pack.name == "Concise Nav"


def test_reject_non_json() -> None:
    with pytest.raises(QVPError):
        load_pack("{ not valid json")


def test_reject_wrong_kind() -> None:
    with pytest.raises(QVPError) as exc:
        parse_pack(_pack(kind="something-else"))
    assert any("kind" in e for e in exc.value.errors)


def test_reject_missing_metadata() -> None:
    bad = _pack()
    del bad["pack"]["license"]
    with pytest.raises(QVPError) as exc:
        parse_pack(bad)
    assert any("license" in e for e in exc.value.errors)


def test_reject_empty_templates() -> None:
    with pytest.raises(QVPError):
        parse_pack(_pack(templates=[]))


def test_reject_duplicate_template_ids() -> None:
    two = _pack()
    two["templates"].append(dict(two["templates"][0]))
    with pytest.raises(QVPError) as exc:
        parse_pack(two)
    assert any("unique" in e for e in exc.value.errors)


# --- install flow --------------------------------------------------------


def test_install_happy_path() -> None:
    result = install_pack(_pack(), current_version="0.7.0")
    assert result.ok
    assert len(result.accepted) == 1
    assert result.rejected_templates == ()
    assert "Pack installed. 1 template added. Author: Kelly Ford." in result.spoken_sequence


def test_install_version_gate_blocks_newer_pack() -> None:
    result = install_pack(_pack(min_quill_version="9.9.9"), current_version="0.7.0")
    assert not result.ok
    assert result.accepted == ()
    assert any("Cannot install" in line for line in result.spoken_sequence)


def test_install_version_gate_allows_equal_or_lower() -> None:
    assert install_pack(_pack(min_quill_version="0.6.0"), current_version="0.7.0").ok
    assert install_pack(_pack(min_quill_version="0.7.0"), current_version="0.7.0").ok


def test_install_rejects_template_for_unknown_verb() -> None:
    pack = _pack()
    pack["templates"][0]["applies_to"] = "nav.nonexistent"
    result = install_pack(pack, current_version="0.7.0")
    assert result.accepted == ()
    assert result.rejected_templates[0][0] == "concise.next_line"
    assert "unknown verb" in result.rejected_templates[0][1]


def test_install_rejects_template_with_invalid_token() -> None:
    pack = _pack()
    pack["templates"][0]["template"] = "{not_a_real_token}"
    result = install_pack(pack, current_version="0.7.0")
    assert result.accepted == ()
    assert result.rejected_templates


def test_install_namespace_collision_rejected() -> None:
    result = install_pack(
        _pack(), current_version="0.7.0", installed_template_ids=("concise.next_line",)
    )
    assert result.accepted == ()
    assert "already installed" in result.rejected_templates[0][1]


def test_install_missing_dependency_warns_not_fatal() -> None:
    pack = _pack()
    pack["pack"]["depends"] = ["org.kelly.base"]
    result = install_pack(pack, current_version="0.7.0", available_packs=())
    assert any("depends on org.kelly.base" in w for w in result.warnings)
    assert result.ok  # missing dep is a warning; the UI offers proceed


def test_install_present_dependency_no_warning() -> None:
    pack = _pack()
    pack["pack"]["depends"] = ["org.kelly.base"]
    result = install_pack(pack, current_version="0.7.0", available_packs=("org.kelly.base",))
    assert result.warnings == ()


def test_invalid_json_install_reports_error() -> None:
    result = install_pack("{bad json", current_version="0.7.0")
    assert not result.ok
    assert result.errors


def test_no_code_execution_paths_in_module() -> None:
    source = Path(qvp_module.__file__).read_text(encoding="utf-8")
    for banned in ("exec(", "eval(", "__import__("):
        assert banned not in source
