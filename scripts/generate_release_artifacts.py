from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from quill.core.compliance import dependency_names_from_pyproject
from quill.core.storage import write_json_atomic


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate SBOM, provenance, and optional vulnerability scan artefacts.",
    )
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--output-dir", type=Path, default=Path("dist") / "release-artifacts")
    parser.add_argument("--include-optional", action="store_true")
    parser.add_argument("--run-audit", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sbom = build_sbom(args.pyproject, include_optional=args.include_optional)
    sbom_path = args.output_dir / "sbom.json"
    write_json_atomic(sbom_path, sbom)

    audit = run_vulnerability_scan() if args.run_audit else {"status": "skipped"}
    provenance = build_provenance(args.pyproject, sbom_path, audit)
    provenance_path = args.output_dir / "provenance.json"
    write_json_atomic(provenance_path, provenance)

    print(f"Wrote {sbom_path}")
    print(f"Wrote {provenance_path}")
    return 0


def build_sbom(pyproject: Path, include_optional: bool = False) -> dict[str, object]:
    dependency_names = dependency_names_from_pyproject(pyproject, include_optional=include_optional)
    components = [
        {
            "name": "quill",
            "type": "application",
            "version": _project_version(pyproject),
        }
    ]
    for name in dependency_names:
        components.append({
            "name": name,
            "type": "library",
            "version": _installed_version(name),
        })
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "metadata": {
            "component": {
                "name": "quill",
                "version": _project_version(pyproject),
            }
        },
        "components": components,
    }


def build_provenance(
    pyproject: Path,
    sbom_path: Path,
    audit: dict[str, object],
) -> dict[str, object]:
    return {
        "buildTimeUtc": datetime.now(UTC).isoformat(),
        "builder": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "project": {
            "name": "quill",
            "version": _project_version(pyproject),
        },
        "artifacts": [
            {
                "path": str(sbom_path),
                "kind": "sbom",
            }
        ],
        "vulnerabilityScan": audit,
    }


def run_vulnerability_scan() -> dict[str, object]:
    executable = shutil.which("pip-audit")
    if executable is None:
        return {"status": "unavailable", "reason": "pip-audit not installed"}
    completed = subprocess.run(
        [executable, "-f", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "status": "failed",
            "returncode": completed.returncode,
            "stderr": completed.stderr.strip(),
        }
    try:
        return {
            "status": "ok",
            "report": json.loads(completed.stdout),
        }
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "reason": "pip-audit returned invalid JSON",
        }


def _installed_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _project_version(pyproject: Path) -> str:
    import tomllib

    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    project = data.get("project", {})
    if isinstance(project, dict):
        version = project.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
