"""Fail a release build when the builder's virtualenv does not match pyproject.

``standalone/runtime/quillville-runtime.spec`` builds with
``collect_all("quill")``, so PyInstaller bundles whatever is importable in the
virtualenv running it. Nothing declared what that should be, so the shared
QuillVille Runtime's contents were a photograph of one machine at one moment.

Two real failures came from that, both silent:

* wxPython sat at 4.2.5 while ``[ui]`` pins ``wxPython==4.3.1``. The runtime
  shipped wxWidgets 3.2.9 instead of 3.3.3 and the build reported success.
* ``vosk``, ``soundfile`` and ``hf_xet`` were absent, so a runtime shipped with
  no offline dictation -- again with a clean exit code.

Neither is detectable from the built artifact without unpacking the installer
and diffing it against a known-good one, which is how they were eventually
found. Checking before the build costs a second.

Usage::

    python scripts/check_build_env.py --groups runtime
    python scripts/check_build_env.py --groups runtime --python path/to/python.exe

Exits non-zero, listing every offending package, when a requirement is missing
or the installed version does not satisfy it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _expand(group: str, optional: dict[str, list[str]], seen: set[str]) -> list[Requirement]:
    """Every requirement in ``group``, following ``quill[other]`` references.

    The runtime group is expressed as ``quill[ui]``-style references so it stays
    a single source of truth rather than a copy that drifts from the groups it
    names.
    """
    if group in seen:
        return []
    seen.add(group)
    out: list[Requirement] = []
    for spec in optional.get(group, []):
        requirement = Requirement(spec)
        if requirement.name == "quill" and requirement.extras:
            for extra in requirement.extras:
                out.extend(_expand(extra, optional, seen))
        else:
            out.append(requirement)
    return out


def _installed(python: str | None) -> dict[str, str]:
    """Installed distributions of the target interpreter, name -> version."""
    if python is None or Path(python) == Path(sys.executable):
        from importlib.metadata import distributions

        # .get(), not ["Name"]: subscripting warns (and will later raise) when a
        # distribution has no Name, which a broken sdist in site-packages can hit.
        return {
            name.lower().replace("_", "-"): (d.version or "")
            for d in distributions()
            if (name := d.metadata.get("Name"))
        }
    # A different interpreter (the release venv) -- ask it directly.
    code = (
        "import json;from importlib.metadata import distributions;"
        "print(json.dumps({n.lower().replace('_','-'): d.version "
        "for d in distributions() if (n := d.metadata.get('Name'))}))"
    )
    result = subprocess.run([python, "-c", code], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def _applies(requirement: Requirement, python: str | None) -> bool:
    """Whether an environment marker (``sys_platform == 'win32'``) applies."""
    if requirement.marker is None:
        return True
    if python is None or Path(python) == Path(sys.executable):
        return requirement.marker.evaluate()
    # Markers here are platform-based and both interpreters are the same OS.
    return requirement.marker.evaluate()


def check(groups: list[str], python: str | None) -> list[str]:
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    optional = data["project"].get("optional-dependencies", {})
    unknown = [g for g in groups if g not in optional]
    if unknown:
        raise SystemExit(f"No such dependency group(s) in pyproject.toml: {', '.join(unknown)}")

    requirements: list[Requirement] = []
    for group in groups:
        requirements.extend(_expand(group, optional, set()))

    installed = _installed(python)
    problems: list[str] = []
    for requirement in requirements:
        if not _applies(requirement, python):
            continue
        name = requirement.name.lower().replace("_", "-")
        have = installed.get(name)
        if have is None:
            problems.append(f"{requirement.name}: MISSING (need {requirement.specifier or 'any'})")
            continue
        if not requirement.specifier:
            continue
        try:
            ok = requirement.specifier.contains(Version(have), prereleases=True)
        except InvalidVersion:
            continue  # a local/editable version string we cannot compare
        if not ok:
            problems.append(f"{requirement.name}: installed {have}, needs {requirement.specifier}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--groups",
        default="runtime",
        help="Comma-separated pyproject optional-dependency groups (default: runtime).",
    )
    parser.add_argument(
        "--python",
        default=None,
        help="Interpreter to inspect. Defaults to the one running this script.",
    )
    args = parser.parse_args()

    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    problems = check(groups, args.python)
    target = args.python or sys.executable
    if problems:
        print(f"Build environment does not match pyproject [{', '.join(groups)}]:", file=sys.stderr)
        for line in problems:
            print(f"  - {line}", file=sys.stderr)
        print(f"\nInterpreter: {target}", file=sys.stderr)
        print(
            f'Fix with: "{target}" -m pip install -e ".[{",".join(groups)}]"',
            file=sys.stderr,
        )
        return 1
    print(f"Build environment satisfies pyproject [{', '.join(groups)}].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
