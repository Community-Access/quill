"""Unified QUILL artifact detector and validator.

One entry point that recognises every shareable QUILL artifact type and runs
the same checks the Quillin Hub Forge applies to a submission. The per-type
validators stay authoritative (``quillin_lint``, ``agent_lint``,
``kqp_validator``, ``sqp_validator``, and the core pack loaders); this module
only detects the type and dispatches.

Usage::

    python -m quill.tools.artifact_validate path/to/artifact
    python -m quill.tools.artifact_validate path/to/artifact --type agent
    python -m quill.tools.artifact_validate path/to/artifact --strict --json

Supported artifact types:

    quillin                   Quillin extension (directory or .zip with manifest.json)
    agent                     AI agent definition (.md or .json, quill.agent/1)
    verbosity-pack            Verbosity pack (.qvp.json)
    sound-pack                Sound pack (.qsp ZIP or directory)
    keyboard-pack             Keyboard Quill Pack (.kqp)
    skill-pack                Skill Quill Pack (.sqp)
    pronunciation-dictionary  Pronunciation dictionary (.json)

Exit codes:
    0  Artifact passes (warnings allowed unless ``--strict``).
    1  Validation errors (or warnings with ``--strict``).
    2  Path not found, or the artifact type could not be detected.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_QVP_KIND = "quill-verbosity-pack"
_QSP_FORMAT = "qsp"
_MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class ArtifactType:
    """One shareable QUILL artifact family the Hub accepts."""

    id: str
    label: str
    suffixes: tuple[str, ...]
    description: str
    validator: str  # human-readable name of the authoritative checker


ARTIFACT_TYPES: tuple[ArtifactType, ...] = (
    ArtifactType(
        id="quillin",
        label="Quillin extension",
        suffixes=(".zip",),
        description="A sandboxed QUILL extension: manifest.json plus optional handler code.",
        validator="quill.tools.quillin_lint",
    ),
    ArtifactType(
        id="agent",
        label="AI agent",
        suffixes=(".md", ".json"),
        description="A declarative agent the AI Hub can list and any harness can run.",
        validator="quill.tools.agent_lint",
    ),
    ArtifactType(
        id="verbosity-pack",
        label="Verbosity pack",
        suffixes=(".qvp.json",),
        description="A data-only bundle of verbosity templates (.qvp.json).",
        validator="quill.core.verbosity.qvp",
    ),
    ArtifactType(
        id="sound-pack",
        label="Sound pack",
        suffixes=(".qsp",),
        description="A QSP earcon pack: WAV files plus manifest.json.",
        validator="quill.core.sound_pack",
    ),
    ArtifactType(
        id="keyboard-pack",
        label="Keyboard pack",
        suffixes=(".kqp",),
        description="A Keyboard Quill Pack of command-to-key bindings (.kqp).",
        validator="quill.tools.kqp_validator",
    ),
    ArtifactType(
        id="skill-pack",
        label="Skill pack",
        suffixes=(".sqp",),
        description="A Skill Quill Pack: a reusable multi-step AI skill (.sqp).",
        validator="quill.tools.sqp_validator",
    ),
    ArtifactType(
        id="pronunciation-dictionary",
        label="Pronunciation dictionary",
        suffixes=(".json",),
        description="A named collection of pronunciation entries for QUILL speech.",
        validator="quill/core/schemas/pronunciation.json",
    ),
)

_TYPES_BY_ID = {artifact_type.id: artifact_type for artifact_type in ARTIFACT_TYPES}


def artifact_type_ids() -> tuple[str, ...]:
    return tuple(_TYPES_BY_ID)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sniff_manifest_type(manifest: Any) -> str:
    """A directory/zip manifest.json is either a sound pack or a Quillin."""
    if isinstance(manifest, dict) and manifest.get("format") == _QSP_FORMAT:
        return "sound-pack"
    return "quillin"


def _detect_json(path: Path) -> str | None:
    try:
        data = _read_json(path)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    schema = data.get("schema")
    if isinstance(schema, str) and schema.startswith("quill.agent/"):
        return "agent"
    if data.get("kind") == _QVP_KIND:
        return "verbosity-pack"
    if "kqp_version" in data:
        return "keyboard-pack"
    if data.get("format") == _QSP_FORMAT:
        return "sound-pack"
    if "entries" in data and "id" in data:
        return "pronunciation-dictionary"
    return None


def _detect_zip(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            manifest_names = [
                name
                for name in names
                if Path(name).name == _MANIFEST_FILENAME and len(Path(name).parts) <= 2
            ]
            if not manifest_names:
                return None
            manifest = json.loads(archive.read(manifest_names[0]))
    except (OSError, ValueError, zipfile.BadZipFile, KeyError):
        return None
    return _sniff_manifest_type(manifest)


def detect_artifact_type(path: Path) -> str | None:
    """Best-effort detection of the artifact type at ``path``.

    Returns an artifact type id, or ``None`` when nothing recognisable is found.
    """
    if path.is_dir():
        manifest = path / _MANIFEST_FILENAME
        if manifest.is_file():
            try:
                return _sniff_manifest_type(_read_json(manifest))
            except (OSError, ValueError):
                return "quillin"
        if any(
            child.is_dir() and (child / _MANIFEST_FILENAME).is_file() for child in path.iterdir()
        ):
            return "quillin"
        return None

    name = path.name.lower()
    if name.endswith(".qvp.json"):
        return "verbosity-pack"
    suffix = path.suffix.lower()
    if suffix == ".qsp":
        return "sound-pack"
    if suffix == ".kqp":
        return "keyboard-pack"
    if suffix == ".sqp":
        return "skill-pack"
    if suffix == ".zip":
        return _detect_zip(path)
    if suffix == ".md":
        return "agent"
    if suffix == ".json":
        return _detect_json(path)
    return None


# ---------------------------------------------------------------------------
# Per-type validation (errors, warnings)
# ---------------------------------------------------------------------------


def _validate_quillin(path: Path) -> tuple[list[str], list[str]]:
    from quill.tools import quillin_lint

    if path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory(prefix="quill-artifact-") as tmp:
            try:
                with zipfile.ZipFile(path) as archive:
                    archive.extractall(tmp)
            except (OSError, zipfile.BadZipFile) as exc:
                return ([f"could not read ZIP archive: {exc}"], [])
            return _validate_quillin(Path(tmp))

    directories = quillin_lint.discover_quillins(path)
    if not directories:
        return (["no Quillin (manifest.json) found here"], [])
    schema = quillin_lint.load_schema()
    errors: list[str] = []
    warnings: list[str] = []
    for directory in directories:
        report = quillin_lint.lint_quillin(directory, schema=schema)
        for problem in report.problems:
            message = f"[{problem.code}] {problem.message}"
            if problem.severity == "error":
                errors.append(message)
            else:
                warnings.append(message)
    return (errors, warnings)


def _validate_agent(path: Path) -> tuple[list[str], list[str]]:
    from quill.tools import agent_lint

    findings = agent_lint.lint_path(path)
    errors = [finding.message for finding in findings if finding.level == agent_lint.ERROR]
    warnings = [finding.message for finding in findings if finding.level != agent_lint.ERROR]
    return (errors, warnings)


def _validate_verbosity_pack(path: Path) -> tuple[list[str], list[str]]:
    from quill.core.verbosity import qvp

    try:
        qvp.load_pack(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return ([f"cannot read: {exc}"], [])
    except qvp.QVPError as exc:
        return (list(exc.errors), [])
    return ([], [])


def _validate_sound_pack(path: Path) -> tuple[list[str], list[str]]:
    from quill.core import sound_pack

    try:
        sound_pack.load_sound_pack(path)
    except sound_pack.SoundPackError as exc:
        return ([str(exc)], [])
    return ([], [])


def _validate_keyboard_pack(path: Path) -> tuple[list[str], list[str]]:
    from quill.tools import kqp_validator

    issues = kqp_validator.validate_file(path, strict=True)
    errors = [issue for issue in issues if not issue.startswith("warning:")]
    warnings = [
        issue.removeprefix("warning:").strip() for issue in issues if issue.startswith("warning:")
    ]
    return (errors, warnings)


def _validate_skill_pack(path: Path) -> tuple[list[str], list[str]]:
    from quill.core.skill_pack import SkillValidationError, parse_skill, validate_skill

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return ([f"cannot read: {exc}"], [])
    try:
        pack = parse_skill(source)
    except SkillValidationError as exc:
        return ([f"parse error: {error}" for error in exc.errors], [])
    errors = list(validate_skill(pack))
    warnings: list[str] = []
    if not pack.description:
        warnings.append("no description in front matter")
    if not pack.author:
        warnings.append("no author in front matter")
    return (errors, warnings)


def _validate_pronunciation(path: Path) -> tuple[list[str], list[str]]:
    try:
        data = _read_json(path)
    except OSError as exc:
        return ([f"cannot read: {exc}"], [])
    except ValueError as exc:
        return ([f"invalid JSON: {exc}"], [])

    if not isinstance(data, dict):
        return (["root value must be a JSON object"], [])

    errors: list[str] = []
    warnings: list[str] = []
    if not str(data.get("id", "")).strip():
        errors.append("missing required field: 'id'")
    entries = data.get("entries")
    if not isinstance(entries, list):
        errors.append("'entries' must be an array")
    else:
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"entries[{index}]: must be an object")
                continue
            if not str(entry.get("term", "")).strip():
                errors.append(f"entries[{index}]: missing required field 'term'")
            mode = entry.get("mode")
            if mode in ("phoneme", "ssml") and not str(entry.get("plain_fallback", "")).strip():
                warnings.append(
                    f"entries[{index}]: mode '{mode}' without a 'plain_fallback' respelling"
                )
    if not str(data.get("name", "")).strip():
        warnings.append("no 'name' field (recommended for listing)")
    return (errors, warnings)


_VALIDATORS = {
    "quillin": _validate_quillin,
    "agent": _validate_agent,
    "verbosity-pack": _validate_verbosity_pack,
    "sound-pack": _validate_sound_pack,
    "keyboard-pack": _validate_keyboard_pack,
    "skill-pack": _validate_skill_pack,
    "pronunciation-dictionary": _validate_pronunciation,
}


def validate_artifact(
    path: Path,
    artifact_type: str | None = None,
    *,
    strict: bool = False,
    require_signed: bool = False,
) -> dict[str, Any]:
    """Validate the artifact at ``path`` and return a structured report.

    The report is JSON-serialisable: ``{path, type, label, status, errors,
    warnings, signature}`` where ``status`` is ``pass``, ``fail``, or
    ``unknown`` (type could not be detected). With ``strict`` warnings also
    fail the artifact. With ``require_signed`` an unsigned or bad-signature
    artifact is also failed, and the per-type validator still runs so the
    author sees the existing errors. ``signature`` is always present in the
    report and contains a ``SignatureStatus`` dict or ``None`` when the type
    could not be detected.
    """
    # Import lazily so tests that patch PUBLIC_KEY_B64 after import time
    # see the patched value.
    from quill.tools.signing import signature_status

    detected = artifact_type or detect_artifact_type(path)
    if detected is None or detected not in _TYPES_BY_ID:
        return {
            "path": str(path),
            "type": None,
            "label": None,
            "status": "unknown",
            "errors": ["could not detect a supported QUILL artifact type"],
            "warnings": [],
            "signature": None,
        }

    sig = signature_status(path)
    errors, warnings = _VALIDATORS[detected](path)
    failed = bool(errors) or (strict and bool(warnings))
    if require_signed and not sig.verified:
        errors.append(f"signature: {sig.error or 'unsigned'}")
        failed = True
    return {
        "path": str(path),
        "type": detected,
        "label": _TYPES_BY_ID[detected].label,
        "status": "fail" if failed else "pass",
        "errors": errors,
        "warnings": warnings,
        "signature": {
            "signed": sig.signed,
            "verified": sig.verified,
            "signer_key_id": sig.signer_key_id,
            "error": sig.error,
        },
    }


def render_report(report: dict[str, Any]) -> str:
    """Human-readable, screen-reader-friendly rendering of a report."""
    lines = [f"{report['status'].upper()}  {report['path']}"]
    if report["label"]:
        lines.append(f"  type: {report['label']} ({report['type']})")
    if report.get("signature") is not None:
        sig = report["signature"]
        if sig["verified"]:
            lines.append(f"  signature: ok ({sig['signer_key_id']})")
        elif sig["signed"]:
            lines.append(f"  signature: invalid ({sig['error']})")
        else:
            lines.append(f"  signature: missing ({sig['error']})")
    for error in report["errors"]:
        lines.append(f"  error: {error}")
    for warning in report["warnings"]:
        lines.append(f"  warning: {warning}")
    if not report["errors"] and not report["warnings"]:
        lines.append("  no problems found")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m quill.tools.artifact_validate",
        description="Detect and validate any shareable QUILL artifact.",
    )
    parser.add_argument("path", type=Path, help="Artifact file or directory.")
    parser.add_argument(
        "--type",
        choices=sorted(artifact_type_ids()),
        help="Override auto-detection with an explicit artifact type.",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    parser.add_argument(
        "--require-signed",
        action="store_true",
        help="Fail the artifact if no valid .minisig is present.",
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report.")
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"Error: '{args.path}' not found.", file=sys.stderr)
        return 2

    report = validate_artifact(
        args.path, args.type, strict=args.strict, require_signed=args.require_signed
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_report(report))

    if report["status"] == "unknown":
        return 2
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
