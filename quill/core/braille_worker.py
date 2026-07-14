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
"""

from __future__ import annotations

import json
import sys

DEFAULT_TABLE = "en-ueb-g2"


def _translate(request: dict[str, object]) -> dict[str, str]:
    cmd = str(request.get("cmd", ""))
    text = str(request.get("text", ""))
    table = str(request.get("table", DEFAULT_TABLE))
    try:
        import louis  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001 - liblouis absent is an expected runtime state
        return {"error": "liblouis is not installed"}
    try:
        if cmd == "forward":
            return {"result": louis.translateString([table], text)}
        if cmd == "back":
            return {"result": louis.backTranslateString([table], text)}
        return {"error": f"unknown command: {cmd}"}
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
