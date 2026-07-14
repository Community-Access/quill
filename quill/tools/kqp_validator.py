"""Keyboard Quill Pack (.kqp) format validator.

Usage::

    python -m quill.tools.kqp_validator path/to/pack.kqp
    python -m quill.tools.kqp_validator path/to/directory/
    python -m quill.tools.kqp_validator path/to/pack.kqp --strict

Exit codes:
    0  All files valid (or no .kqp files found when scanning a directory).
    1  One or more validation errors.
    2  File/directory not found or unreadable.

``--strict`` also reports warnings (missing description, missing author,
unrecognised command IDs).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quill.core.keymap import _KQP_VERSION, DEFAULT_KEYMAP  # type: ignore[attr-defined]

_REQUIRED_FIELDS = ("kqp_version", "name", "bindings")


def validate_file(path: Path, strict: bool) -> list[str]:
    """Return a list of error/warning strings for the given .kqp file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read: {exc}"]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]

    if not isinstance(data, dict):
        return ["root value must be a JSON object"]

    errors: list[str] = []

    for field in _REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing required field: '{field}'")

    if "kqp_version" in data and data["kqp_version"] != _KQP_VERSION:
        errors.append(f"unsupported kqp_version {data['kqp_version']!r}; expected {_KQP_VERSION}")

    if "name" in data and not str(data["name"]).strip():
        errors.append("'name' must not be empty")

    bindings = data.get("bindings")
    if bindings is not None:
        if not isinstance(bindings, dict):
            errors.append("'bindings' must be a JSON object")
        else:
            for key, val in bindings.items():
                if not isinstance(key, str):
                    errors.append(f"binding key must be a string, got: {key!r}")
                if not isinstance(val, str):
                    errors.append(f"binding value for '{key}' must be a string, got: {val!r}")
                elif strict and key not in DEFAULT_KEYMAP:
                    errors.append(f"warning: unrecognised command ID '{key}'")

    if strict:
        if not str(data.get("description", "")).strip():
            errors.append("warning: no 'description' field")
        if not str(data.get("author", "")).strip():
            errors.append("warning: no 'author' field")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m quill.tools.kqp_validator",
        description="Validate .kqp (Keyboard Quill Pack) files.",
    )
    parser.add_argument("path", help="Path to a .kqp file or a directory to scan recursively.")
    parser.add_argument("--strict", action="store_true", help="Also report warnings.")
    args = parser.parse_args(argv)

    target = Path(args.path)
    if not target.exists():
        print(f"Error: '{target}' not found.", file=sys.stderr)
        return 2

    if target.is_dir():
        files = sorted(target.rglob("*.kqp"))
        if not files:
            print("No .kqp files found.")
            return 0
    else:
        files = [target]

    any_errors = False
    for f in files:
        issues = validate_file(f, args.strict)
        if issues:
            any_errors = True
            print(f"{f}: {len(issues)} issue{'s' if len(issues) != 1 else ''}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"{f}: OK")

    return 1 if any_errors else 0


if __name__ == "__main__":
    sys.exit(main())
