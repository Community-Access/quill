"""Agent standards linter (GATE)."""

from __future__ import annotations

from pathlib import Path

from quill.core.ai.agent_catalog import SCHEMA_ID, bundled_agents_dir
from quill.tools.agent_lint import (
    ERROR,
    WARNING,
    lint_agent_data,
    lint_dir,
    lint_path,
    main,
)


def _good() -> dict:
    return {
        "schema": SCHEMA_ID,
        "id": "tidy-editor",
        "display_name": "Tidy Editor",
        "description": "Tighten prose without changing the author's meaning.",
        "system_prompt": (
            "You are a careful copy editor. Tighten the prose, keep the author's "
            "voice, and never change the meaning. Return the full revised text."
        ),
        "risk": "low",
        "default_scope": "selection",
        "default_harness": "auto",
        "permissions": {"modify_selection": "preview_required"},
    }


def _errors(data: dict) -> list[str]:
    return [f.message for f in lint_agent_data(data) if f.level == ERROR]


def _warnings(data: dict) -> list[str]:
    return [f.message for f in lint_agent_data(data) if f.level == WARNING]


# --- the bundled set is the reference: it must pass clean -------------------


def test_bundled_agents_pass_clean() -> None:
    findings = lint_dir(bundled_agents_dir())
    assert findings == [], "\n".join(str(f) for f in findings)


def test_a_well_formed_agent_has_no_findings() -> None:
    assert lint_agent_data(_good()) == []


# --- standards rules -------------------------------------------------------


def test_mutating_permission_may_not_be_allow() -> None:
    data = _good()
    data["permissions"] = {"modify_document": "allow"}
    data["default_scope"] = "full_document"
    assert any("may not be 'allow'" in m for m in _errors(data))


def test_read_permission_allow_is_fine() -> None:
    data = _good()
    data["permissions"] = {"read_selection": "allow"}
    assert not any("allow" in m for m in _errors(data))


def test_high_risk_requires_explicit_permissions() -> None:
    data = _good()
    data["risk"] = "high"
    data["permissions"] = {}
    assert any("declare its permissions" in m for m in _errors(data))


def test_description_required_and_sized() -> None:
    short = _good()
    short["description"] = "too short"
    assert any("too short" in m for m in _errors(short))
    missing = _good()
    del missing["description"]
    assert any("description is required" in m for m in _errors(missing))


def test_system_prompt_must_be_substantive() -> None:
    data = _good()
    data["system_prompt"] = "Do stuff."
    assert any("system_prompt is too short" in m for m in _errors(data))


def test_unknown_harness_is_rejected() -> None:
    data = _good()
    data["default_harness"] = "langchain"
    assert any("default_harness" in m for m in _errors(data))


def test_file_type_and_tool_format() -> None:
    data = _good()
    data["recommended_file_types"] = [".md", "HTML"]
    data["tools"] = ["Not A Command"]
    msgs = _errors(data)
    assert any("recommended_file_types" in m for m in msgs)
    assert any("tools entry" in m for m in msgs)


def test_display_name_whitespace_flagged() -> None:
    data = _good()
    data["display_name"] = " Tidy Editor "
    assert any("whitespace" in m for m in _errors(data))


def test_scope_permission_coherence_is_a_warning() -> None:
    data = _good()
    data["permissions"] = {"modify_selection": "preview_required"}
    data["default_scope"] = "full_document"  # incoherent with modify_selection
    assert _errors(data) == []
    assert any("selection-level scope" in m for m in _warnings(data))


# --- file-level checks -----------------------------------------------------


def test_file_name_must_match_id(tmp_path: Path) -> None:
    import json

    (tmp_path / "wrong-name.json").write_text(json.dumps(_good()), encoding="utf-8")
    findings = lint_path(tmp_path / "wrong-name.json")
    assert any("file name must match" in f.message for f in findings)


def test_duplicate_ids_across_files(tmp_path: Path) -> None:
    md = (
        "---\nid: dup\ndisplay_name: Dup\n"
        "description: A duplicate agent for testing only.\n"
        "default_scope: selection\n---\n\n" + ("You are a test agent. " * 6)
    )
    (tmp_path / "dup.md").write_text(md, encoding="utf-8")
    (tmp_path / "dup-copy.md").write_text(md.replace("dup-copy", "dup"), encoding="utf-8")
    findings = lint_dir(tmp_path)
    # dup-copy.md re-declares id 'dup' and also trips the file-name rule.
    assert any("duplicate agent id" in f.message for f in findings)


def test_readme_and_partials_skipped(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# not an agent\n", encoding="utf-8")
    (tmp_path / "_template.md").write_text("# partial\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


# --- CLI -------------------------------------------------------------------


def test_main_passes_on_bundled() -> None:
    assert main([str(bundled_agents_dir())]) == 0


def test_main_fails_on_error(tmp_path: Path) -> None:
    (tmp_path / "bad.md").write_text("---\nid: bad\n---\n", encoding="utf-8")
    assert main([str(tmp_path)]) == 1


def test_strict_fails_on_warning_only(tmp_path: Path) -> None:
    import json

    data = _good()
    data["id"] = "warner"
    data["permissions"] = {"modify_selection": "preview_required"}
    data["default_scope"] = "full_document"  # warning, not error
    (tmp_path / "warner.json").write_text(json.dumps(data), encoding="utf-8")
    assert main([str(tmp_path)]) == 0
    assert main([str(tmp_path), "--strict"]) == 1
