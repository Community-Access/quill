"""The Forge audit pipeline.

Every submission, whatever its type, flows through the same three stages:

1. **Signature verification** -- ``quill.tools.signing.signature_status()``
   runs first, before validation. An unsigned submission is rejected before
   its content is parsed.
2. **Validation** -- ``python -m quill.tools.artifact_validate --json`` is the
   single authority. It detects the artifact type and runs the exact checks
   QUILL itself uses (quillin_lint, agent_lint, the pack loaders).
3. **Security scan** (Quillins only) -- Bandit over any Python, plus the AST
   SecurityWatchdog for capability honesty.
4. **Metadata extraction** -- the Forge reads the artifact's own manifest or
   front matter so submitters never retype their name, version, and
   description.
"""

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from .security_scanner import SecurityWatchdog

_MANIFEST_FILENAME = "manifest.json"


def _run_artifact_validate(path: str, artifact_type: str | None) -> dict[str, Any]:
    """Run the unified validator and return its JSON report."""
    command = [sys.executable, "-m", "quill.tools.artifact_validate", path, "--json"]
    if artifact_type:
        command += ["--type", artifact_type]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except Exception as exc:  # noqa: BLE001 - report, never crash the Forge
        return {
            "path": path,
            "type": artifact_type,
            "label": None,
            "status": "error",
            "errors": [f"validator execution error: {exc}"],
            "warnings": [],
        }
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {
            "path": path,
            "type": artifact_type,
            "label": None,
            "status": "error",
            "errors": [f"validator produced no report (exit {proc.returncode})", proc.stderr],
            "warnings": [],
        }


def _read_manifest(upload_path: str) -> dict[str, Any] | None:
    candidate = os.path.join(upload_path, _MANIFEST_FILENAME)
    if os.path.isfile(candidate):
        try:
            with open(candidate, encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else None
        except (OSError, ValueError):
            return None
    if os.path.isdir(upload_path):
        for child in sorted(os.listdir(upload_path)):
            nested = os.path.join(upload_path, child, _MANIFEST_FILENAME)
            if os.path.isfile(nested):
                try:
                    with open(nested, encoding="utf-8") as handle:
                        data = json.load(handle)
                    return data if isinstance(data, dict) else None
                except (OSError, ValueError):
                    return None
    return None


def _extract_front_matter(path: str) -> dict[str, Any]:
    """Best-effort YAML-lite front matter reader for .md/.sqp artifacts."""
    fields: dict[str, Any] = {}
    try:
        with open(path, encoding="utf-8") as handle:
            first = handle.readline().strip()
            if first != "---":
                return fields
            for line in handle:
                stripped = line.strip()
                if stripped == "---":
                    break
                if ":" in stripped and not stripped.startswith(("-", "#")):
                    key, _, value = stripped.partition(":")
                    fields[key.strip()] = value.strip()
    except OSError:
        return fields
    return fields


def extract_metadata(upload_path: str, artifact_type: str | None) -> dict[str, Any]:
    """Pull name/id/version/description out of the artifact itself."""
    meta: dict[str, Any] = {}
    if os.path.isdir(upload_path) or upload_path.endswith((".zip", ".qsp")):
        manifest = None
        if upload_path.endswith((".zip", ".qsp")):
            try:
                with zipfile.ZipFile(upload_path) as archive:
                    names = [n for n in archive.namelist() if n.endswith(_MANIFEST_FILENAME)]
                    if names:
                        manifest = json.loads(archive.read(sorted(names, key=len)[0]))
            except (OSError, ValueError, zipfile.BadZipFile):
                manifest = None
        else:
            manifest = _read_manifest(upload_path)
        if isinstance(manifest, dict):
            for key in ("id", "name", "version", "description", "author", "license"):
                if manifest.get(key):
                    meta[key] = manifest[key]
        return meta

    if upload_path.endswith((".md", ".sqp")):
        front = _extract_front_matter(upload_path)
        for source_key, target_key in (
            ("id", "id"),
            ("name", "name"),
            ("display_name", "name"),
            ("version", "version"),
            ("description", "description"),
            ("author", "author"),
        ):
            if front.get(source_key) and target_key not in meta:
                meta[target_key] = front[source_key]
        return meta

    if upload_path.endswith((".json", ".kqp")):
        try:
            with open(upload_path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return meta
        if isinstance(data, dict):
            pack_meta = data.get("pack") if isinstance(data.get("pack"), dict) else data
            for key in ("id", "name", "display_name", "version", "description", "author"):
                if pack_meta.get(key) and key not in meta:
                    meta["name" if key == "display_name" else key] = pack_meta[key]
        return meta

    return meta


def _security_scan(upload_path: str, manifest: dict[str, Any]) -> tuple[str | None, str | None]:
    """Bandit + AST watchdog over a Quillin's Python. Returns (bandit, watchdog)."""
    bandit_report: str | None = None
    watchdog_report: str | None = None

    has_python = any(
        filename.endswith(".py")
        for _root, _dirs, files in os.walk(upload_path)
        for filename in files
    )
    if not has_python:
        if manifest.get("capabilities") and manifest.get("main"):
            watchdog_report = "Capabilities declared but no implementation file found."
        return (bandit_report, watchdog_report)

    try:
        bandit_proc = subprocess.run(
            ["bandit", "-r", upload_path, "-f", "json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if bandit_proc.returncode != 0:
            security_data = json.loads(bandit_proc.stdout)
            high_issues = [
                issue
                for issue in security_data.get("results", [])
                if issue["issue_severity"] == "HIGH"
            ]
            if high_issues:
                bandit_report = "High-severity security vulnerabilities detected via Bandit."
            else:
                bandit_report = "Minor security warnings detected."
    except Exception as exc:  # noqa: BLE001
        bandit_report = f"Security scan error: {exc}"

    watchdog = SecurityWatchdog(manifest)
    issues: list[str] = []
    try:
        for root, _dirs, files in os.walk(upload_path):
            for filename in files:
                if filename.endswith(".py"):
                    for line_no, message in watchdog.scan_file(os.path.join(root, filename)):
                        issues.append(f"{filename} line {line_no}: {message}")
    except (OSError, RecursionError) as exc:  # noqa: BLE001 - report, never crash the Forge
        issues.append(f"watchdog scan error: {exc}")
    if issues:
        watchdog_report = "\n".join(issues)

    return (bandit_report, watchdog_report)


def audit_submission(
    upload_path: str,
    artifact_type: str | None = None,
    sidecar_path: str | None = None,
    sign_target: str | None = None,
) -> dict[str, Any]:
    """End-to-end audit of any Hub submission.

    The signature check runs first, before the validator, so an unsigned
    submission is rejected before its content is parsed. ``sidecar_path``
    is the explicitly-uploaded ``.minisig`` file. ``sign_target`` is the
    path whose bytes the sidecar actually signs (for a zipped Quillin
    the sidecar signs the *zip* bytes, not the extracted files);
    defaults to ``upload_path``.

    Returns ``{status, artifact_type, label, metadata, reports}`` where
    ``status`` is PASS / FAIL / ERROR and ``reports`` carries the signature,
    validator, security, and watchdog details.
    """
    from quill.tools.signing import signature_status

    sig_target = sign_target or upload_path
    sig = signature_status(Path(sig_target), sidecar=Path(sidecar_path) if sidecar_path else None)
    sig_dict = {
        "signed": sig.signed,
        "verified": sig.verified,
        "signer_key_id": sig.signer_key_id,
        "error": sig.error,
    }

    validation = _run_artifact_validate(upload_path, artifact_type)
    detected_type = validation.get("type") or artifact_type

    results: dict[str, Any] = {
        "status": "PASS",
        "artifact_type": detected_type,
        "label": validation.get("label"),
        "metadata": extract_metadata(upload_path, detected_type),
        "reports": {
            "signature": sig_dict,
            "validator": {
                "errors": validation.get("errors", []),
                "warnings": validation.get("warnings", []),
            },
            "security": None,
            "watchdog": None,
        },
    }

    if validation.get("status") == "error":
        results["status"] = "ERROR"
        return results
    if not sig.verified:
        results["status"] = "FAIL"
    if validation.get("status") in ("fail", "unknown"):
        results["status"] = "FAIL"

    # Only Quillins carry executable code; everything else is data-only.
    if detected_type == "quillin" and os.path.isdir(upload_path):
        manifest = _read_manifest(upload_path) or {}
        bandit_report, watchdog_report = _security_scan(upload_path, manifest)
        results["reports"]["security"] = bandit_report
        results["reports"]["watchdog"] = watchdog_report
        if bandit_report and "High-severity" in bandit_report:
            results["status"] = "FAIL"
        if watchdog_report:
            results["status"] = "FAIL"

    return results
