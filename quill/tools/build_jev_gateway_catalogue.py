"""Write the gateway's copy of the Command Key catalogue (command-key.md 7.4 and 7.6).

The gateway's ``/v1/decide`` builds the Jev request itself, from its own copy of
the descriptions, so a caller can only name command ids the server already
knows and cannot send questions of its own. This tool writes that copy, one
JSON file per catalogue version, beside the gateway's code::

    python -m quill.tools.build_jev_gateway_catalogue --write
    python -m quill.tools.build_jev_gateway_catalogue --check   (what the test runs)

Each entry is exactly what :mod:`quill.core.command_catalogue.jev_request` puts
in a choice for that command (its criterion), plus whether the command is
stepped (which adds the ``size`` question). The gateway runs a copy of the same
question builder, so the own-key route and the gateway route ask Jev the same
questions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quill.core.command_catalogue import rows_for_app
from quill.core.command_catalogue.jev_request import CATALOGUE_VERSION, _criterion
from quill.core.command_catalogue.resolver import Candidate
from quill.core.command_catalogue.spec import ArgKind, Kind

APPS = ("quill", "lite", "radio")
_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = _ROOT / "quill-ai-gateway" / "app" / "jev_catalogue"


def build() -> dict[str, object]:
    apps: dict[str, dict[str, dict[str, object]]] = {}
    for app in APPS:
        rows: dict[str, dict[str, object]] = {}
        for spec in rows_for_app(app):
            if not spec.offered:
                continue
            stepped = spec.kind is Kind.STEP or any(
                arg.kind is ArgKind.STEPPED for arg in spec.args
            )
            rows[spec.id] = {"criterion": _criterion(Candidate(spec)), "stepped": stepped}
        apps[app] = dict(sorted(rows.items()))
    return {"version": CATALOGUE_VERSION, "apps": apps}


def render() -> str:
    return json.dumps(build(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def target() -> Path:
    return OUT_DIR / f"{CATALOGUE_VERSION}.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    path = target()
    text = render()
    if args.write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(_ROOT).as_posix()}")
        return 0
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    if current != text:
        print(
            f"{path.relative_to(_ROOT).as_posix()} is out of date; run "
            "python -m quill.tools.build_jev_gateway_catalogue --write",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
