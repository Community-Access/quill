"""Explorer's Convert with Quill: hand the files to Quill Converter (FUX-02).

The verb starts QUILL with ``--action convert``, and QUILL passes the files to
Quill Converter through the family's launcher and exits before its own window
starts (``quill/__main__.py``). When Converter was not installed beside QUILL
the launcher's False was ignored, so the verb did nothing at all, silently.
Now it says so, in the one place left to say it: there is no QUILL window, so
it is a native message box, which every screen reader reads.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from pathlib import Path


def missing_sentence(paths: Sequence[str]) -> str:
    """What to say when Converter is not there (pure)."""
    names = [Path(str(path)).name for path in paths if str(path).strip()]
    what = names[0] if len(names) == 1 else f"{len(names)} files"
    verb = "was" if len(names) == 1 else "were"
    return (
        f"Quill Converter is not installed with this copy of QUILL, so {what} {verb} not converted."
    )


def _message_box(message: str) -> None:
    if sys.platform != "win32":
        print(message, file=sys.stderr)
        return
    try:
        import ctypes

        user32 = getattr(ctypes, "windll").user32  # noqa: B009 - Windows only
        # MB_ICONWARNING | MB_SETFOREGROUND | MB_TOPMOST: QUILL may take a few
        # seconds to get here, and the box must not open behind Explorer.
        user32.MessageBoxW(0, message, "Convert with Quill", 0x30 | 0x10000 | 0x40000)
    except Exception:  # noqa: BLE001 - a message never blocks the exit
        print(message, file=sys.stderr)


def _launch(app_key: str, *, extra_args: tuple[str, ...]) -> bool:
    from quill.core.app_launcher import launch_app

    return launch_app(app_key, extra_args=extra_args)


def hand_to_converter(
    paths: Sequence[str],
    *,
    launch: Callable[..., bool] = _launch,
    tell: Callable[[str], None] = _message_box,
) -> bool:
    """Start Quill Converter on *paths*; say so when it cannot be. True when started."""
    if launch("converter", extra_args=tuple(paths)):
        return True
    tell(missing_sentence(paths))
    return False


__all__ = ["hand_to_converter", "missing_sentence"]
