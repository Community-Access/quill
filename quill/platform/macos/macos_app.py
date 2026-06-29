"""Entry point for the macOS .app bundle (used by scripts/setup_macos.py / py2app).

Wraps QUILL's startup so a failure in *our* code — anything after py2app's own
bootstrap has handed control to ``quill.__main__.main`` — writes the real
traceback to ``~/Library/Logs/Quill/startup-error.log`` and shows a native
alert, instead of leaving the user staring at py2app's opaque error screen
(#755). Failures *inside* py2app's bootstrap (e.g. a missing @rpath dylib)
happen before this runs and are addressed in scripts/build_macos.sh.
"""

from __future__ import annotations


def _log_startup_error(exc: BaseException) -> str:
    """Write the traceback to the user Logs dir; return the log path (best effort)."""
    import traceback
    from pathlib import Path

    log_path = Path.home() / "Library" / "Logs" / "Quill" / "startup-error.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("".join(traceback.format_exception(exc)), encoding="utf-8")
    except Exception:  # noqa: BLE001 - never let error logging raise
        pass
    return str(log_path)


def _show_native_error(message: str) -> None:
    """Show a native macOS alert via osascript. Best effort; never raises."""
    import subprocess

    escaped = message.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display alert "QUILL could not start" message "{escaped}" as critical'
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=30)
    except Exception:  # noqa: BLE001 - a missing/again-failing osascript must not mask the error
        pass


def _main() -> int:
    try:
        from quill.__main__ import main

        return main()
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - capture *any* startup failure for the user
        log_path = _log_startup_error(exc)
        _show_native_error(
            f"QUILL hit an error while starting. The details were written to {log_path}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
