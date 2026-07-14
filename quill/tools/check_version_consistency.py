"""Version consistency gate (GATE-VC).

Ensures that all version-bearing files in the repo agree with the
authoritative version in ``quill/__init__.py`` (and ``build/version.toml``
when present, since 0.7.0 the toml is the canonical source for the
display version, channel, and build identity that feed the About
dialog, support info, and InnoSetup installer metadata).

Files checked:

- ``quill/__init__.py`` -- authoritative source for the PEP 440 version
- ``build/version.toml`` -- authoritative source for the display
                            version and release channel (0.7.0+)
- ``pyproject.toml``    -- must use ``dynamic = ["version"]`` (not a static
                           ``version =`` field); ``[tool.hatch.version] path``
                           must point at ``quill/__init__.py``
- ``installer/quill.iss`` -- ``#define AppVersion`` and
                             ``OutputBaseFilename`` must match
- ``CHANGELOG.md``     -- the topmost version heading (``## <version>``) must match

Exit 0 on success, 1 with diagnostics on any mismatch.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


def _authoritative_version(repo_root: Path) -> str:
    """Return the display version that drives user-visible strings.

    Prefers ``build/version.toml`` (the canonical source as of 0.7.0);
    falls back to the PEP 440 version in ``quill/__init__.py`` for
    pre-0.7.0 checkouts where the toml is absent.
    """
    toml_path = repo_root / "build" / "version.toml"
    if toml_path.exists():
        with toml_path.open("rb") as handle:
            data = tomllib.load(handle)
        base = str(data.get("base_version", "")).strip()
        channel = str(data.get("channel", "stable")).strip().lower()
        pre = int(data.get("prerelease_number", 0))
        if channel == "stable":
            return base
        if channel == "alpha":
            return f"{base} Alpha {pre}"
        if channel == "beta":
            return f"{base} Beta {pre}"
        if channel == "rc":
            return f"{base} Release Candidate {pre}"
        return f"{base} Dev"
    init_py = repo_root / "quill" / "__init__.py"
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_py.read_text(), re.M)
    if not match:
        raise RuntimeError(f"Could not find __version__ in {init_py}")
    return match.group(1)


def _check_pyproject(repo_root: Path, canonical: str) -> list[str]:
    errors: list[str] = []
    pyproject = repo_root / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)

    project = data.get("project", {})
    if "version" in project:
        errors.append(
            f"pyproject.toml: static 'version = \"{project['version']}\"' found. "
            "Remove it; quill/__init__.py is the authoritative source. "
            'Use dynamic = ["version"] + [tool.hatch.version] path = "quill/__init__.py".'
        )

    dynamic = project.get("dynamic", [])
    if "version" not in dynamic:
        errors.append(
            "pyproject.toml: 'version' is not in project.dynamic. "
            'Add dynamic = ["version"] and [tool.hatch.version] path = "quill/__init__.py".'
        )

    hatch_version = data.get("tool", {}).get("hatch", {}).get("version", {})
    path_val = hatch_version.get("path", "")
    if path_val != "quill/__init__.py":
        errors.append(
            f'pyproject.toml: [tool.hatch.version] path = "{path_val}" '
            'does not point at "quill/__init__.py".'
        )

    return errors


def _check_iss(repo_root: Path, canonical: str) -> list[str]:
    errors: list[str] = []
    iss = repo_root / "installer" / "quill.iss"
    if not iss.exists():
        return errors  # not required for all contributors

    text = iss.read_text(encoding="utf-8")
    match = re.search(r'#define AppVersion "([^"]+)"', text)
    if not match:
        errors.append("installer/quill.iss: could not find #define AppVersion line.")
        return errors

    iss_version = match.group(1)
    if iss_version != canonical:
        errors.append(
            f'installer/quill.iss: AppVersion is "{iss_version}", '
            f'expected "{canonical}" (from quill/__init__.py).'
        )

    # OutputBaseFilename should also match. Accept both the pre-0.7.0
    # ``Quill-Setup-X`` and the current ``Quill-for-All-Setup-X`` forms so
    # the gate does not break while older install artefacts age out.
    fn_match = re.search(r"OutputBaseFilename=(?:Quill-Setup|Quill-for-All-Setup)-([^\r\n]+)", text)
    if fn_match:
        fn_version = fn_match.group(1).strip()
        if fn_version != canonical:
            errors.append(
                f'installer/quill.iss: OutputBaseFilename contains version "{fn_version}", '
                f'expected "{canonical}".'
            )

    return errors


def _check_changelog(repo_root: Path, canonical: str) -> list[str]:
    errors: list[str] = []
    changelog = repo_root / "CHANGELOG.md"
    if not changelog.exists():
        return errors

    text = changelog.read_text(encoding="utf-8")
    # Find first ## heading that looks like a version. Accepts stable
    # (``## 0.5.0``), pre-release (``## 0.7.0 Beta 1``, ``## 0.7.0a1``,
    # ``## 0.7.0rc1``, ``## 0.7.0 Release Candidate 2``) and dev
    # (``## 0.7.0.dev20260619``) forms.
    match = re.search(
        r"^## (\d+\.\d+(?:\.\d+)?"
        r"(?:[._-]?(?:a|b|rc|alpha|beta|dev)\d*|"
        r"\s+(?:alpha|beta|release\s+candidate|rc|dev)\.?\s*\d*)?)",
        text,
        re.M | re.I,
    )
    if not match:
        errors.append("CHANGELOG.md: could not find a version heading (## X.Y.Z).")
        return errors

    top_version = match.group(1)
    if top_version != canonical:
        errors.append(
            f'CHANGELOG.md: top version heading is "{top_version}", '
            f'expected "{canonical}" (from quill/__init__.py). '
            "Add a new ## entry for the current release."
        )

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        canonical = _authoritative_version(repo_root)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"GATE-VC FAIL: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    errors.extend(_check_pyproject(repo_root, canonical))
    errors.extend(_check_iss(repo_root, canonical))
    errors.extend(_check_changelog(repo_root, canonical))

    if errors:
        print("GATE-VC FAIL: version inconsistency detected.", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            f"\nAuthoritative version (quill/__init__.py): {canonical}",
            file=sys.stderr,
        )
        return 1

    print(f"GATE-VC OK: all version references agree on {canonical}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
