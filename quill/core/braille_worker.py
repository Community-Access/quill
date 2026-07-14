"""liblouis translation worker subprocess (#244 / BR-021).

This module runs OUT of QUILL's process. It reads one JSON request from
stdin, performs the liblouis translation, and prints a single JSON result
line. liblouis is imported only inside :func:`_translate`, so importing this
module never pulls liblouis into any process; QUILL's main process never imports
liblouis at all -- it only ever spawns this script (see
:mod:`quill.core.braille_worker_client`).

The request travels on stdin, not argv: a whole document's text can run to
hundreds of KB, and Windows' CreateProcess has a roughly 32K total
command-line-length limit -- an argv-embedded payload silently fails to
launch once the caller's text grows past that.

Two backends, tried in order:

1. the python ``louis`` binding, when someone installed it (fastest);
2. the pack's own ``lou_translate`` CLI (text over stdin/stdout). The pack
   has always shipped this binary plus the tables, but the worker only ever
   tried ``import louis`` -- so translation silently required a separately
   pip-installed binding that nothing installs, and running from source
   always failed with "liblouis is not installed". The CLI fallback makes
   translation work out of the box from source, portable, and installed
   builds alike.
"""

from __future__ import annotations

import json
import subprocess
import sys

DEFAULT_TABLE = "en-ueb-g2"

#: No single translation should take this long; a wedged lou_translate must
#: never wedge the worker (whose caller enforces its own timeout as well).
_CLI_TIMEOUT_SECONDS = 60.0


def _table_argument(table: str) -> str:
    """Absolute path into the pack's tables when available, else the bare name."""
    from quill.core.braille_pack import find_table_file

    resolved = find_table_file(table)
    return str(resolved) if resolved is not None else table


def _translate_one(text: str, table: str, *, backward: bool) -> dict[str, object]:
    """Translate via the python binding, else the pack's lou_translate CLI."""
    try:
        import louis  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001 - the binding is optional; the CLI is the fallback
        louis = None

    if louis is not None:
        translate = louis.backTranslateString if backward else louis.translateString
        return {"result": translate([_table_argument(table)], text)}

    from quill.core.braille_pack import find_lou_translate

    exe = find_lou_translate()
    if exe is None:
        return {
            "error": "liblouis is not installed. Install the braille pack from "
            "Help > Download Optional Components."
        }
    direction = "--backward" if backward else "--forward"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    completed = subprocess.run(  # noqa: S603 - fixed pack binary, controlled args
        [str(exe), direction, _table_argument(table)],
        input=text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_CLI_TIMEOUT_SECONDS,
        creationflags=creationflags,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip() or f"exit code {completed.returncode}"
        return {"error": f"lou_translate failed: {detail}"}
    # lou_translate appends one trailing newline to its output stream.
    result = completed.stdout
    if result.endswith("\r\n"):
        result = result[:-2]
    elif result.endswith("\n"):
        result = result[:-1]
    return {"result": result}


def _translate(request: dict[str, object]) -> dict[str, object]:
    cmd = str(request.get("cmd", ""))
    text = str(request.get("text", ""))
    table = str(request.get("table", DEFAULT_TABLE))
    try:
        if cmd == "forward":
            return _translate_one(text, table, backward=False)
        if cmd == "back":
            return _translate_one(text, table, backward=True)
        if cmd == "detect":
            # Back-translate the same sample against every candidate table in
            # one worker launch (a fresh worker per candidate would multiply
            # process-startup cost by the candidate count). Scoring is
            # deliberately NOT done here: it lives in braille_detect, where
            # it is importable and unit-testable without any subprocess.
            raw_tables = request.get("tables")
            tables = (
                [str(t) for t in raw_tables] if isinstance(raw_tables, list) else [DEFAULT_TABLE]
            )
            results: dict[str, str] = {}
            for candidate in tables:
                outcome = _translate_one(text, candidate, backward=True)
                if "result" in outcome:
                    results[candidate] = str(outcome["result"])
            if not results:
                return {"error": "no candidate table produced a back-translation"}
            return {"results": results}
        return {"error": f"unknown command: {cmd}"}
    except subprocess.TimeoutExpired:
        return {"error": "lou_translate timed out"}
    except Exception as exc:  # noqa: BLE001 - never let liblouis raise into the pipe
        return {"error": str(exc)}


def main(stdin_text: str) -> int:
    if not stdin_text.strip():
        print(json.dumps({"error": "no request"}))
        return 1
    try:
        request = json.loads(stdin_text)
    except ValueError:
        print(json.dumps({"error": "bad request json"}))
        return 1
    print(json.dumps(_translate(request)))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    sys.exit(main(sys.stdin.read()))
