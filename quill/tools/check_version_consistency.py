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


#: ``standalone/`` entries that are not an app with a version of its own.
#: ``runtime`` is the shared CPython the thin installers download; its
#: "AppVersion" is the Python version (3.13) and has nothing to do with any
#: app's release number.
_STANDALONE_NOT_AN_APP = frozenset({"runtime"})


def _iss_version_errors(iss: Path, canonical: str, label: str) -> list[str]:
    """AppVersion, VersionInfoVersion and OutputBaseFilename against *canonical*."""
    errors: list[str] = []
    text = iss.read_text(encoding="utf-8")

    match = re.search(r'#define AppVersion "([^"]+)"', text)
    if match and match.group(1) != canonical:
        errors.append(f'{label}: #define AppVersion is "{match.group(1)}", expected "{canonical}".')

    # Windows file properties. Four-part (3.0.0.0), so compare the first three:
    # this is the number a listener sees in the .exe's Details tab and the one
    # Windows uses to decide whether an upgrade is an upgrade.
    match = re.search(r"VersionInfoVersion=([0-9.]+)", text)
    if match:
        parts = match.group(1).split(".")
        if ".".join(parts[:3]) != canonical:
            errors.append(
                f"{label}: VersionInfoVersion is {match.group(1)}, "
                f"which is not {canonical} -- the version Windows shows in the "
                "file's Details tab and uses to order upgrades."
            )
    return errors


def _top_changelog_release(path: Path) -> tuple[str, str] | None:
    """``(version, date)`` from the first ``## [X.Y.Z] - DATE`` heading, or None.

    Both bracketed (Keep a Changelog) and bare headings are accepted, and the
    date is optional -- a missing date is not an error here, a *disagreeing*
    one is. Only an ISO date counts as a date: Quill Weather's heading reads
    ``## 2.2.0 -- first release``, and a looser pattern read "first" as the day
    it shipped and then reported it as a disagreement.
    """
    if not path.exists():
        return None
    match = re.search(
        r"^##\s*\[?(\d+\.\d+\.\d+)\]?\s*(?:-+\s*(\d{4}-\d{2}-\d{2}))?",
        path.read_text(encoding="utf-8"),
        re.M,
    )
    if not match:
        return None
    return match.group(1), (match.group(2) or "")


def _check_standalone_apps(repo_root: Path) -> list[str]:
    """Every ``standalone/<app>`` agrees with its own pyproject version.

    The main app has had this since 0.7.0; the standalone apps never did, and
    on 2026-08-25 -- readying Quill Radio 3.0.0 -- an audit by hand found three
    siblings shipping a wrong number: QUILL Cast's installer stamped
    VersionInfoVersion 1.0.1.0 onto a 2.0.0 release, Audio Studio's full
    installer said 1.0.0 for 2.2.0, and Quill Inkwell's said 2.2.0 for 1.0.0.
    None of it was catchable, because nothing looked.

    Each app is checked against **its own** ``pyproject.toml``; there is no
    repo-wide number to agree on, because the apps release independently.
    """
    errors: list[str] = []
    root = repo_root / "standalone"
    if not root.is_dir():
        return errors

    for app_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        app = app_dir.name
        if app in _STANDALONE_NOT_AN_APP:
            continue
        pyproject = app_dir / "pyproject.toml"
        if not pyproject.exists():
            continue
        with pyproject.open("rb") as fh:
            canonical = str(tomllib.load(fh).get("project", {}).get("version", "")).strip()
        if not canonical:
            continue

        build_ps1 = app_dir / "scripts" / "build_release.ps1"
        if build_ps1.exists():
            match = re.search(
                r'^\$version\s*=\s*"([^"]+)"', build_ps1.read_text(encoding="utf-8"), re.M
            )
            if match and match.group(1) != canonical:
                errors.append(
                    f"standalone/{app}/scripts/build_release.ps1: $version is "
                    f'"{match.group(1)}", expected "{canonical}" (from its pyproject.toml).'
                )

        for iss in sorted((app_dir / "installer").glob("*.iss")):
            errors.extend(
                _iss_version_errors(iss, canonical, f"standalone/{app}/installer/{iss.name}")
            )

        # The two changelogs an app can carry: the narrative one at its root and
        # the Keep a Changelog mirror under docs/. They must name the same
        # release, on the same day -- a release with two dates is a release
        # nobody can cite.
        releases = {}
        for rel in ("CHANGELOG.md", "docs/CHANGELOG.md"):
            found = _top_changelog_release(app_dir / rel)
            if found is not None:
                releases[rel] = found
        for rel, (version, _date) in releases.items():
            if version != canonical:
                errors.append(
                    f'standalone/{app}/{rel}: top version heading is "{version}", '
                    f'expected "{canonical}" (from its pyproject.toml).'
                )
        dates = {rel: date for rel, (_v, date) in releases.items() if date}
        if len(set(dates.values())) > 1:
            spelled = ", ".join(f"{rel} says {date}" for rel, date in sorted(dates.items()))
            errors.append(
                f"standalone/{app}: the changelogs disagree about the release date "
                f"({spelled}). One release, one date."
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
    # The standalone apps release independently, so each is checked against
    # its own pyproject version rather than against QUILL's.
    errors.extend(_check_standalone_apps(repo_root))

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
