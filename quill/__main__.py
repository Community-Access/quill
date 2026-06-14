from __future__ import annotations

import os
import sys
import time
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path

from quill import __version__
from quill.core.features import reset_feature_profile_store
from quill.core.paths import app_data_dir, ensure_app_directories
from quill.core.storage_mode import load_storage_mode, portable_root_dir, save_storage_mode
from quill.stability.diagnostics import dump_all_thread_stacks, setup_fault_handler
from quill.stability.logging_config import configure_logging


@dataclass(frozen=True, slots=True)
class LaunchRequest:
    path: Path
    line: int | None = None
    column: int | None = None
    action: str = "open"
    diff_with: Path | None = None  # set by --diff; second file for compare mode


def main() -> int:
    parsed = _parse_cli_arguments(sys.argv[1:])
    if parsed.version:
        print(__version__)
        return 0

    ensure_app_directories()
    log_listener = configure_logging(app_data_dir() / "logs")
    setup_fault_handler()
    try:
        _bootstrap_storage_mode()

        try:
            from quill.ui.main_frame import run_app
        except ModuleNotFoundError as exc:
            if exc.name == "wx":
                print("wxPython is required to run the UI. Install with: pip install -e .[ui]")
                return 1
            raise

        from quill.core.ipc import (
            enqueue_open_request,
            release_primary_instance,
            try_claim_primary_instance,
        )

        if parsed.dump_stacks:
            dump_file = dump_all_thread_stacks("manual CLI request")
            print(dump_file)
            return 0

        launch_requests, safe_mode, reset_profile, diagnostics_mode, force_new_window, wait = (
            _launch_configuration(parsed)
        )
        if reset_profile:
            reset_feature_profile_store()
        # H-SAFE-1: when the user (or the env) asked for safe mode, set
        # ``QUILL_SAFE_MODE`` so any subsystem that short-circuits on
        # the env var (assistant_ai, watch folder startup) gets the
        # same answer even if a future caller forgets to thread the
        # ``safe_mode`` flag through to it.
        if safe_mode:
            os.environ["QUILL_SAFE_MODE"] = "1"
        if not force_new_window and not try_claim_primary_instance():
            for request in launch_requests:
                enqueue_open_request(
                    request.path,
                    line=request.line,
                    column=request.column,
                    action=request.action,
                )
            enqueue_open_request(None)
            if wait:
                _wait_for_primary_instance_shutdown()
            return 0
        try:
            run_app(launch_requests, safe_mode=safe_mode, diagnostics_mode=diagnostics_mode)
        finally:
            release_primary_instance()
    finally:
        log_listener.stop()
    return 0


def _bootstrap_storage_mode() -> None:
    if os.environ.get("QUILL_PORTABLE") != "1":
        return
    if os.environ.get("QUILL_DATA_DIR"):
        return
    root = portable_root_dir()
    if root is None:
        return
    mode = load_storage_mode()
    if mode == "portable":
        os.environ["QUILL_DATA_DIR"] = str(root)
        return
    if mode == "appdata":
        return

    try:
        import wx
    except ModuleNotFoundError:
        return

    app = wx.App(False)
    try:
        with wx.SingleChoiceDialog(
            None,
            "Where should Quill store its settings and other local data?",
            "Quill Storage Location",
            choices=[
                "AppData (recommended)",
                "Portable folder next to Quill",
            ],
        ) as dialog:
            selection = dialog.ShowModal()
            if selection != wx.ID_OK:
                choice = "appdata"
            elif dialog.GetSelection() == 1:
                choice = "portable"
            else:
                choice = "appdata"
    finally:
        app.Destroy()

    save_storage_mode(choice)
    if choice == "portable":
        root.mkdir(parents=True, exist_ok=True)
        os.environ["QUILL_DATA_DIR"] = str(root)


def _parse_cli_arguments(arguments: list[str]) -> Namespace:
    parser = ArgumentParser(
        prog="quill",
        description="Quill: screen-reader-first writing and document environment.",
    )
    parser.add_argument("paths", nargs="*", help="Optional files to open on startup.")
    parser.add_argument("--version", action="store_true", help="Show QUILL version and exit.")
    parser.add_argument("--safe-mode", action="store_true", help="Start QUILL in safe mode.")
    parser.add_argument(
        "--reset-profile",
        action="store_true",
        help="Reset the feature profile store before launch.",
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Start with diagnostics tracing enabled.",
    )
    parser.add_argument(
        "--dump-stacks",
        action="store_true",
        help="Write a thread-stack dump and exit.",
    )
    parser.add_argument(
        "--new-window",
        action="store_true",
        help="Force a new QUILL process instead of reusing an existing instance.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="When forwarding to an existing instance, wait for it to close.",
    )
    parser.add_argument(
        "--line",
        type=int,
        default=None,
        help="1-based line number for the first opened file.",
    )
    parser.add_argument(
        "--column",
        type=int,
        default=None,
        help="1-based column number for the first opened file.",
    )
    parser.add_argument(
        "--action",
        default="open",
        help=(
            "Shell verb to run on the opened file(s): one of "
            "open, ocr, ocr-structured, read. Defaults to open."
        ),
    )
    parser.add_argument(
        "--goto",
        default=None,
        metavar="FILE[:LINE[:COL]]",
        help=("Open FILE at an optional 1-based LINE and COL. Example: --goto main.kt:27:5"),
    )
    parser.add_argument(
        "--diff",
        nargs=2,
        metavar=("LEFT", "RIGHT"),
        default=None,
        help="Open two files in compare mode. Example: --diff old.kt new.kt",
    )
    return parser.parse_args(arguments)


def _launch_configuration(
    parsed: Namespace,
) -> tuple[list[LaunchRequest], bool, bool, bool, bool, bool]:
    from quill.core.shell_verbs import verb_actions

    raw_action = str(getattr(parsed, "action", "open") or "open").strip().lower()
    action = raw_action if raw_action in {"open", *verb_actions()} else "open"

    requests: list[LaunchRequest] = []

    # --diff LEFT RIGHT  →  single compare LaunchRequest
    diff_pair = getattr(parsed, "diff", None)
    if diff_pair:
        left_path = Path(str(diff_pair[0])).expanduser()
        right_path = Path(str(diff_pair[1])).expanduser()
        if left_path.exists() and right_path.exists():
            requests.append(
                LaunchRequest(
                    path=left_path.resolve(),
                    action="compare",
                    diff_with=right_path.resolve(),
                )
            )

    # --goto FILE[:LINE[:COL]]
    goto_arg = getattr(parsed, "goto", None)
    if goto_arg:
        goto_path, goto_line, goto_col = _parse_goto(goto_arg)
        if goto_path is not None and goto_path.exists():
            requests.append(
                LaunchRequest(
                    path=goto_path.resolve(),
                    line=goto_line,
                    column=goto_col,
                    action="open",
                )
            )

    for index, raw_path in enumerate(parsed.paths):
        if not str(raw_path).strip():
            continue
        candidate = Path(str(raw_path)).expanduser()
        if not candidate.exists():
            continue
        request = LaunchRequest(
            path=candidate.resolve(),
            line=parsed.line if index == 0 else None,
            column=parsed.column if index == 0 else None,
            action=action,
        )
        requests.append(request)

    safe_mode = bool(parsed.safe_mode)
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        safe_mode = True
    return (
        requests,
        safe_mode,
        bool(parsed.reset_profile),
        bool(parsed.diagnostics),
        bool(parsed.new_window),
        bool(parsed.wait),
    )


def _parse_goto(raw: str) -> tuple[Path | None, int | None, int | None]:
    """Parse --goto FILE[:LINE[:COL]] into (path, line, col)."""
    parts = raw.rsplit(":", 2)
    # Collect up to 2 trailing integer segments (right-to-left, re-ordered).
    numbers: list[int] = []
    while len(parts) > 1 and parts[-1].isdigit() and len(numbers) < 2:
        numbers.insert(0, int(parts.pop()))
    # numbers is [] | [line] | [line, col]
    line: int | None = numbers[0] if numbers else None
    col: int | None = numbers[1] if len(numbers) > 1 else None
    # Remaining parts rejoin to form the path.
    candidate = Path(":".join(parts)).expanduser()
    if not candidate.exists():
        return None, None, None
    return candidate, line, col


def _launch_arguments(arguments: list[str]) -> tuple[list[Path], bool, bool]:
    """Compatibility helper retained for existing tests and integrations."""
    paths: list[Path] = []
    safe_mode = False
    reset_profile = False
    for value in arguments:
        if value == "--safe-mode":
            safe_mode = True
            continue
        if value == "--reset-profile":
            reset_profile = True
            continue
        if value.startswith("--"):
            continue
        if not value.strip():
            continue
        candidate = Path(value).expanduser()
        if candidate.exists():
            paths.append(candidate.resolve())
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        safe_mode = True
    return paths, safe_mode, reset_profile


def _wait_for_primary_instance_shutdown(timeout_seconds: int = 3600) -> None:
    from quill.core.ipc import release_primary_instance, try_claim_primary_instance

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if try_claim_primary_instance():
            release_primary_instance()
            return
        time.sleep(0.25)


if __name__ == "__main__":
    raise SystemExit(main())
