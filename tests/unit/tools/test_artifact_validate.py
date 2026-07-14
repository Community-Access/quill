"""Tests for quill.tools.artifact_validate (unified artifact detection + validation)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from quill.tools import artifact_validate

REPO = Path(__file__).resolve().parents[3]
BUNDLED_QUILLIN = REPO / "quill" / "quillins_bundled" / "journal-stamp"
BUNDLED_AGENT = REPO / "quill" / "core" / "ai" / "agents" / "summarizer.md"
BUNDLED_SKILL = REPO / "quill" / "quillins_bundled" / "ai-writing-skills" / "accessible-rewrite.sqp"


def _write(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _minimal_qvp() -> dict:
    return {
        "schema_version": "1",
        "kind": "quill-verbosity-pack",
        "min_quill_version": "0.9.0",
        "pack": {
            "name": "Test pack",
            "author": "Tester",
            "version": "1.0.0",
            "license": "MIT",
        },
        "templates": [
            {
                "id": "test.template",
                "name": "Test template",
                "applies_to": "status",
                "template": "{name}",
            }
        ],
    }


def _minimal_kqp() -> dict:
    return {"kqp_version": 1, "name": "Test keys", "bindings": {}}


def _minimal_pronunciation() -> dict:
    return {"id": "test-dict", "name": "Test dictionary", "entries": [{"term": "QUILL"}]}


def _minimal_qsp_manifest() -> dict:
    return {"format": "qsp", "version": "1", "name": "Test sounds", "events": {}}


class TestDetection:
    def test_quillin_directory(self) -> None:
        assert artifact_validate.detect_artifact_type(BUNDLED_QUILLIN) == "quillin"

    def test_quillin_collection_directory(self) -> None:
        assert artifact_validate.detect_artifact_type(BUNDLED_QUILLIN.parent) == "quillin"

    def test_agent_markdown(self) -> None:
        assert artifact_validate.detect_artifact_type(BUNDLED_AGENT) == "agent"

    def test_agent_json(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "helper.json", {"schema": "quill.agent/1", "id": "helper"})
        assert artifact_validate.detect_artifact_type(path) == "agent"

    def test_verbosity_pack_suffix(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "pack.qvp.json", _minimal_qvp())
        assert artifact_validate.detect_artifact_type(path) == "verbosity-pack"

    def test_verbosity_pack_sniffed_from_plain_json(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "pack.json", _minimal_qvp())
        assert artifact_validate.detect_artifact_type(path) == "verbosity-pack"

    def test_keyboard_pack(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "keys.kqp", _minimal_kqp())
        assert artifact_validate.detect_artifact_type(path) == "keyboard-pack"

    def test_skill_pack(self) -> None:
        assert artifact_validate.detect_artifact_type(BUNDLED_SKILL) == "skill-pack"

    def test_pronunciation_dictionary(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "dict.json", _minimal_pronunciation())
        assert artifact_validate.detect_artifact_type(path) == "pronunciation-dictionary"

    def test_sound_pack_directory(self, tmp_path: Path) -> None:
        pack = tmp_path / "sounds"
        pack.mkdir()
        _write(pack / "manifest.json", _minimal_qsp_manifest())
        assert artifact_validate.detect_artifact_type(pack) == "sound-pack"

    def test_unknown_file(self, tmp_path: Path) -> None:
        path = tmp_path / "mystery.xyz"
        path.write_text("nothing", encoding="utf-8")
        assert artifact_validate.detect_artifact_type(path) is None

    def test_unknown_json(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "misc.json", {"hello": "world"})
        assert artifact_validate.detect_artifact_type(path) is None


class TestValidation:
    def test_bundled_quillin_passes(self) -> None:
        report = artifact_validate.validate_artifact(BUNDLED_QUILLIN)
        assert report["type"] == "quillin"
        assert report["status"] == "pass"
        assert report["errors"] == []

    def test_bundled_agent_passes(self) -> None:
        report = artifact_validate.validate_artifact(BUNDLED_AGENT)
        assert report["type"] == "agent"
        assert report["status"] == "pass"

    def test_bundled_skill_pack_passes(self) -> None:
        report = artifact_validate.validate_artifact(BUNDLED_SKILL)
        assert report["type"] == "skill-pack"
        assert report["status"] == "pass"

    def test_verbosity_pack_passes(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "pack.qvp.json", _minimal_qvp())
        report = artifact_validate.validate_artifact(path)
        assert report["status"] == "pass"

    def test_verbosity_pack_missing_templates_fails(self, tmp_path: Path) -> None:
        broken = _minimal_qvp()
        broken["templates"] = []
        path = _write(tmp_path / "pack.qvp.json", broken)
        report = artifact_validate.validate_artifact(path)
        assert report["status"] == "fail"
        assert any("templates" in error for error in report["errors"])

    def test_keyboard_pack_passes(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "keys.kqp", _minimal_kqp())
        report = artifact_validate.validate_artifact(path)
        assert report["status"] == "pass"
        # missing description/author surface as warnings, not errors
        assert report["warnings"]

    def test_keyboard_pack_strict_fails_on_warnings(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "keys.kqp", _minimal_kqp())
        report = artifact_validate.validate_artifact(path, strict=True)
        assert report["status"] == "fail"

    def test_keyboard_pack_missing_fields_fails(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "keys.kqp", {"name": "No version"})
        report = artifact_validate.validate_artifact(path)
        assert report["status"] == "fail"

    def test_pronunciation_passes(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "dict.json", _minimal_pronunciation())
        report = artifact_validate.validate_artifact(path)
        assert report["status"] == "pass"

    def test_pronunciation_missing_term_fails(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "dict.json", {"id": "bad", "entries": [{}]})
        report = artifact_validate.validate_artifact(path)
        assert report["status"] == "fail"

    def test_sound_pack_passes(self, tmp_path: Path) -> None:
        pack = tmp_path / "sounds"
        pack.mkdir()
        _write(pack / "manifest.json", _minimal_qsp_manifest())
        report = artifact_validate.validate_artifact(pack)
        assert report["status"] == "pass"

    def test_sound_pack_bad_format_fails(self, tmp_path: Path) -> None:
        pack = tmp_path / "sounds"
        pack.mkdir()
        manifest = {"format": "nope", "version": "1", "name": "x", "events": {}}
        _write(pack / "manifest.json", manifest)
        report = artifact_validate.validate_artifact(pack, artifact_type="sound-pack")
        assert report["status"] == "fail"

    def test_unknown_type_report(self, tmp_path: Path) -> None:
        path = tmp_path / "mystery.xyz"
        path.write_text("nothing", encoding="utf-8")
        report = artifact_validate.validate_artifact(path)
        assert report["status"] == "unknown"

    def test_explicit_type_override(self, tmp_path: Path) -> None:
        # A pronunciation dictionary validated as an agent should fail loudly.
        path = _write(tmp_path / "dict.json", _minimal_pronunciation())
        report = artifact_validate.validate_artifact(path, artifact_type="agent")
        assert report["type"] == "agent"
        assert report["status"] == "fail"


class TestCli:
    def test_pass_exit_code(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = _write(tmp_path / "dict.json", _minimal_pronunciation())
        assert artifact_validate.main([str(path)]) == 0
        assert "PASS" in capsys.readouterr().out

    def test_json_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        path = _write(tmp_path / "dict.json", _minimal_pronunciation())
        assert artifact_validate.main([str(path), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["type"] == "pronunciation-dictionary"
        assert payload["status"] == "pass"

    def test_fail_exit_code(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "keys.kqp", {"name": "No version"})
        assert artifact_validate.main([str(path)]) == 1

    def test_missing_path_exit_code(self, tmp_path: Path) -> None:
        assert artifact_validate.main([str(tmp_path / "absent.kqp")]) == 2

    def test_unknown_type_exit_code(self, tmp_path: Path) -> None:
        path = tmp_path / "mystery.xyz"
        path.write_text("nothing", encoding="utf-8")
        assert artifact_validate.main([str(path)]) == 2

    def test_validate_unsigned_artifact_marks_signature_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "quill.tools.signing.PUBLIC_KEY_B64",
            base64.b64encode(b"\x42" * 32).decode(),
            raising=False,
        )
        path = _write(tmp_path / "pack.qvp.json", _minimal_qvp())
        # Without require_signed: the per-type validator passes; the
        # signature is reported in the 'signature' field but is not
        # counted as an error.
        report = artifact_validate.validate_artifact(path)
        assert "signature" in report
        assert report["signature"]["signed"] is False
        assert report["signature"]["verified"] is False
        assert "no sidecar" in (report["signature"]["error"] or "").lower()
        assert report["status"] == "pass"
        # With require_signed: an unsigned artifact is failed and the
        # signature line is added to errors.
        report_strict = artifact_validate.validate_artifact(path, require_signed=True)
        assert report_strict["status"] == "fail"
        assert any("signature" in err.lower() for err in report_strict["errors"])

    def test_cli_require_signed_disables_pass_for_unsigned(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "quill.tools.signing.PUBLIC_KEY_B64",
            base64.b64encode(b"\x42" * 32).decode(),
            raising=False,
        )
        path = _write(tmp_path / "pack.qvp.json", _minimal_qvp())
        code = artifact_validate.main([str(path), "--require-signed"])
        captured = capsys.readouterr()
        assert code == 1
        assert "signature" in captured.out.lower()
