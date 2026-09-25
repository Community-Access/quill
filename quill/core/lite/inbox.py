"""One process, many windows: how a second launch hands its files to the first.

Double-clicking three files in Explorer starts three processes. Without a
handover each one would build its own window registry, its own recovery store
and its own settings writer, and the last one to exit would win the settings
file. QUILL Lite therefore keeps one process and many windows: a second launch
writes what it wanted into an inbox, asks the running instance to come forward,
and exits.

The inbox is a directory of tiny request files rather than a socket or a named
pipe, for three reasons that matter more here than elegance does:

* **No listening port and no firewall prompt.** An editor that makes Windows ask
  about network access on first run has already lost the user.
* **It survives the reader.** If the running instance is busy, or wedged, the
  request sits on disk until it is read; nothing is lost to a refused connect.
* **It is inspectable.** When a handover does not work, the evidence is a file
  in a folder the About box names.

Each request is written to a ``.tmp`` name and then ``os.replace``d to ``.req``,
so a reader polling the directory can never see a half-written request: the
rename is atomic and the file is only ever visible complete.

wx-free: this module decides *what* is asked for, and the app decides what to do
about it.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from quill.core.lite.paths import inbox_dir, instance_marker_path

__all__ = [
    "NEW_DEFAULT",
    "NEW_PLAIN",
    "NEW_RICH",
    "claim_instance_marker",
    "clear_instance_marker",
    "post_request",
    "read_requests",
    "running_instance_pid",
]

#: The three verbs a request line can carry. Anything else is a file path.
NEW_DEFAULT = "NEW"
NEW_RICH = "NEW:rich"
NEW_PLAIN = "NEW:plain"


def request_lines(paths: list[Path], mode: str | None) -> list[str]:
    """The lines a launch with *paths* and *mode* should ask for.

    A launch with files asks for those files. A launch with none -- somebody
    started the app again from the Start Menu -- asks for a new window, because
    the alternative is a click that appears to do nothing. An explicit
    ``--rich``/``--plain`` always asks for a new window in that mode as well, so
    "open a rich document" is one command rather than two.
    """
    lines = [str(Path(path).resolve()) for path in paths]
    if mode is not None:
        lines.append(f"NEW:{mode}")
    elif not lines:
        lines.append(NEW_DEFAULT)
    return lines


def post_request(paths: list[Path], mode: str | None, *, directory: Path | None = None) -> bool:
    """Leave a request for the running instance. ``True`` when it was written."""
    lines = request_lines(paths, mode)
    if not lines:
        return False
    root = directory if directory is not None else inbox_dir()
    stem = uuid.uuid4().hex
    temp = root / f"{stem}.tmp"
    try:
        temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(temp, root / f"{stem}.req")
    except OSError:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return True


def read_requests(directory: Path | None = None) -> list[str]:
    """Every pending request line, oldest file first, consuming as it goes.

    A request that cannot be read is left alone and skipped rather than retried
    forever: one unreadable file must not stop the ones behind it.
    """
    root = directory if directory is not None else inbox_dir()
    lines: list[str] = []
    try:
        requests = sorted(root.glob("*.req"))
    except OSError:
        return lines
    for request in requests:
        try:
            body = request.read_text(encoding="utf-8")
            request.unlink(missing_ok=True)
        except OSError:
            continue
        lines.extend(line.strip() for line in body.splitlines() if line.strip())
    return lines


def claim_instance_marker(pid: int | None = None) -> None:
    """Record this process's id so a later launch can hand focus to it."""
    try:
        instance_marker_path().write_text(
            str(os.getpid() if pid is None else pid), encoding="utf-8"
        )
    except OSError:
        pass  # the handover degrades to "opens, but you have to find the window"


def clear_instance_marker() -> None:
    """Forget this process's id on a clean exit."""
    try:
        instance_marker_path().unlink(missing_ok=True)
    except OSError:
        pass


def running_instance_pid() -> int:
    """The recorded process id of the running instance, or ``0``."""
    try:
        return int(instance_marker_path().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0
