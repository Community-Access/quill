from __future__ import annotations

import os
import sys
import time
import types
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path

from quill import __version__
from quill.core.ai.key_migration import consolidate_provider_keys_quietly
from quill.core.data_location import (
    apply_pending_data_location_migration,
    apply_pending_legacy_import,
)
from quill.core.features import reset_feature_profile_store
from quill.core.paths import app_data_dir, ensure_app_directories
from quill.core.prompt_migration import consolidate_prompts_quietly
from quill.core.settings import load_settings as _load_settings
from quill.core.startup_maintenance import run_pending_startup_maintenance
from quill.stability.diagnostics import dump_all_thread_stacks, setup_fault_handler
from quill.stability.logging_config import configure_logging


# Indirection so the excepthook helpers can be monkeypatched in tests
# without re-importing the settings module on every call. Defaults
# to the real ``load_settings`` so production callers see the
# current behaviour.
def quill_main_load_settings() -> object:
    """Return the user's settings; replaced by tests via monkeypatch."""
    return _load_settings()


def _propagate_portable_environment() -> None:
    """Set QUILL_APP_ROOT and QUILL_PORTABLE when running from a portable bundle.

    The portable bundle's primary entry point is ``quill.exe`` at the bundle
    root, next to a ``data/`` folder -- the evidence rules in
    :func:`quill.core.storage_mode._resolve_app_root` apply here too. When
    the host process can resolve a verified portable anchor, mirror the
    fact into the env so the legacy ``QUILL_APP_ROOT`` consumers (braille
    pack, bundled tool paths, read-aloud assets, AI key DPAPI fallback)
    keep working without each doing its own walk-up from ``sys.executable``.

    Skipped when the env vars are already set -- the launcher or a test
    harness may have set them deliberately.
    """
    from quill.core.storage_mode import _resolve_app_root

    if os.environ.get("QUILL_APP_ROOT") or os.environ.get("QUILL_PORTABLE"):
        return
    anchor = _resolve_app_root()
    if anchor is None:
        return
    os.environ["QUILL_APP_ROOT"] = str(anchor)
    os.environ["QUILL_PORTABLE"] = "1"


def _install_excepthook() -> None:
    """Install sys.excepthook so unhandled crashes offer a submit dialog (#622).

    Without this, a crash in the windowed build just silently closes QUILL —
    a blank screen with no feedback for blind users (finding #51). The
    native ``ctypes`` ``MessageBoxW`` is the always-on floor (works even
    when wx is unavailable or the crash happens before wx is initialised).

    When wx is alive and the user has the ``auto_ask_crash_submit`` setting
    enabled (default True during the beta phase), the handler instead
    schedules :class:`quill.ui.crash_report_dialog.CrashReportDialog` on
    the UI thread via :func:`wx.CallAfter`. The dialog shows a redacted
    preview of the report the user is about to send and returns the
    user's choice; this handler then either submits via
    :func:`quill.core.issue_submit.submit_crash_issue`, copies the
    report to the clipboard, or leaves the local crash file untouched.

    Every step is wrapped in ``try/except``: a misbehaving dialog or
    network failure must never prevent the local traceback file from
    being saved and the standard interpreter traceback from firing.
    """
    import datetime
    import traceback

    def _handler(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: types.TracebackType | None,
    ) -> None:
        # 1. Save the local traceback file first. This is the only
        #    step whose success matters -- the dialog is a nicety on
        #    top of this durable artifact.
        crash_file: Path | None = None
        try:
            crash_dir = app_data_dir() / "crash-reports"
            crash_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            crash_file = crash_dir / f"crash-{ts}.txt"
            with crash_file.open("w", encoding="utf-8") as fh:
                traceback.print_exception(exc_type, exc_value, exc_tb, file=fh)
        except Exception:  # noqa: BLE001
            crash_file = None

        # 2. Try the wx dialog path. Any failure here drops back to
        #    the native MessageBoxW so the user always sees
        #    *something*.
        dialog_used = False
        try:
            dialog_used = _try_offer_crash_submit(exc_type, exc_value, exc_tb, crash_file)
        except Exception:  # noqa: BLE001
            dialog_used = False

        # 3. If the dialog path did not run (no wx, pre-init crash,
        #    dialog disabled, or it threw), fall back to the native
        #    MessageBoxW so the user can find the local crash file.
        if not dialog_used:
            _show_native_fallback(exc_type, exc_value, crash_file)

        # 4. Always end with the standard interpreter traceback so
        #    console / debugger capture works.
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _handler


def _try_offer_crash_submit(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: types.TracebackType | None,
    crash_file: Path | None,
) -> bool:
    """Try to offer the wx crash-submit dialog; return True on success.

    Returns ``False`` for every "cannot show the dialog" path --
    missing wx, no running wx.App, the user turned the setting off,
    pre-init crash -- so the caller can fall back to a native
    MessageBoxW. Every internal step is best-effort: any exception is
    swallowed and surfaced as ``False``.
    """
    try:
        import wx  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return False

    # Only attempt the dialog when wx is fully alive (an App is
    # running) and the user opted in via Settings. Both checks are
    # best-effort: a failure here is the same as "user said no".
    try:
        app = wx.GetApp()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        app = None
    if app is None:
        return False

    try:
        settings = quill_main_load_settings()
        if not getattr(settings, "auto_ask_crash_submit", True):
            return False
    except Exception:  # noqa: BLE001
        # If we cannot read settings (e.g. a corrupt file), default to
        # "show the dialog" because the beta-phase default is on.
        pass

    # Build the redacted payload. This is the wx-free half of the
    # flow; if it raises we still fall back to the native path.
    try:
        from quill import __version__
        from quill.core.diagnostics import load_diagnostic_events
        from quill.core.storage_mode import portable_root_dir
        from quill.stability.crash_submit import build_crash_report_payload

        recent = [event.name for event in load_diagnostic_events(limit=50)]
        portable = portable_root_dir() is not None
        screen_reader_name: str | None = None
        if sys.platform == "win32":
            try:
                from quill.platform.windows.sr_detect import detect_screen_reader

                detected = detect_screen_reader()
                if detected and getattr(detected, "detected", False):
                    screen_reader_name = getattr(detected, "name", None)
            except Exception:  # noqa: BLE001
                screen_reader_name = None

        active_document = _active_document_snapshot()

        payload = build_crash_report_payload(
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=exc_tb,
            local_crash_file=crash_file,
            app_version=__version__,
            portable=portable,
            screen_reader_name=screen_reader_name,
            recent_commands=recent,
            active_document=active_document,
        )
    except Exception:  # noqa: BLE001
        return False

    # Schedule the dialog on the UI thread. We cannot show a modal
    # dialog from inside sys.excepthook because we are not on the
    # main loop. wx.CallAfter defers the call to the next idle, which
    # is exactly what we want -- the user sees the dialog after
    # QUILL has had a moment to settle.
    def _run_on_ui() -> None:
        try:
            from quill.core.feedback_token import effective_github_token
            from quill.core.issue_submit import submit_crash_issue
            from quill.ui.crash_report_dialog import (
                CrashReportDialog,
                merge_user_context_into_body,
            )

            parent = _find_main_frame_window()
            dialog = CrashReportDialog(parent, payload=payload)
            try:
                result = dialog.show()
            except Exception:  # noqa: BLE001
                # Dialog construction or modal loop blew up; leave
                # the local crash file in place and do not submit.
                return

            if result.act == "cancel":
                return
            merged = merge_user_context_into_body(payload.body, result)
            if result.act == "copy":
                _copy_to_clipboard(merged)
                _notify_crash_action(
                    "The crash report was copied to your clipboard. "
                    "Paste it into a new issue to send it."
                )
                return
            # act == "send"
            token = effective_github_token()
            if not token:
                # No token to submit with: fall back to the clipboard and TELL the
                # user, so pressing Send never looks like it silently did nothing.
                _copy_to_clipboard(merged)
                _notify_crash_action(
                    "No GitHub sign-in is configured, so the report was copied to "
                    "your clipboard instead. Paste it into a new issue to send it."
                )
                return
            # The submit is the only step whose success/failure the user needs to
            # hear: they explicitly chose Send. A silent swallow here is
            # indistinguishable from success for a screen-reader user.
            try:
                submit_crash_issue(
                    summary=payload.summary,
                    message=merged,
                    app_version=__version__,
                    github_token=token,
                    metadata=payload.metadata,
                )
            except Exception:  # noqa: BLE001 - report the failure, then fall back
                _copy_to_clipboard(merged)
                _notify_crash_action(
                    "Sending the crash report failed (for example, no network). "
                    "It was copied to your clipboard instead — paste it into a new "
                    "issue to send it."
                )
                return
            _notify_crash_action("Your crash report was sent. Thank you.")
        except Exception:  # noqa: BLE001
            pass

    try:
        wx.CallAfter(_run_on_ui)  # type: ignore[attr-defined]
        return True
    except Exception:  # noqa: BLE001
        return False


def _show_native_fallback(
    exc_type: type[BaseException],
    exc_value: BaseException,
    crash_file: Path | None,
) -> None:
    """The always-on MessageBoxW so the user can find the local crash file.

    Mirrors the original (#51) behaviour: a native dialog with the
    file path, regardless of platform. On non-Windows the message is
    logged to stderr instead.
    """
    import ctypes

    msg = "QUILL encountered an unexpected error and needs to close.\n\n"
    msg += f"Error: {exc_type.__name__}: {exc_value}\n\n"
    if crash_file:
        msg += f"A crash report was saved to:\n{crash_file}"
    else:
        msg += "Could not save a crash report."
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.MessageBoxW(0, msg, "QUILL — Unexpected Error", 0x10)
        except Exception:  # noqa: BLE001
            pass
    else:
        try:
            print(msg, file=sys.stderr)
        except Exception:  # noqa: BLE001
            pass


def _active_document_snapshot() -> object | None:
    """Return the active ``Document`` if MainFrame has one ready.

    Best-effort: returns ``None`` when wx is not yet alive, MainFrame
    has not finished its ``__init__``, or any attribute lookup fails.
    The excepthook uses this only for context; ``None`` is fine.
    """
    try:
        import wx  # type: ignore[import-not-found]

        app = wx.GetApp()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None
    if app is None:
        return None
    try:
        top = app.GetTopWindow()
    except Exception:  # noqa: BLE001
        return None
    if top is None:
        return None
    # MainFrame is a mixin; the actual wx.Frame is `frame`. The
    # active document lives on the mixin instance. Walk the typical
    # shapes so a future refactor does not crash the excepthook.
    for owner in (top, getattr(top, "frame", None), getattr(top, "_main", None)):
        if owner is None:
            continue
        document = getattr(owner, "document", None)
        if document is not None:
            return document
    return None


def _find_main_frame_window() -> object | None:
    """Return the ``wx.Window`` to parent the dialog against, or ``None``.

    Prefers the real ``wx.Frame`` (``top.frame`` when MainFrame is a
    mixin) over the mixin instance because wxPython's SIP wrapper
    rejects non-Frame parents (see #624).
    """
    try:
        import wx  # type: ignore[import-not-found]

        app = wx.GetApp()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None
    if app is None:
        return None
    try:
        top = app.GetTopWindow()
    except Exception:  # noqa: BLE001
        return None
    if top is None:
        return None
    real_frame = getattr(top, "frame", None)
    return real_frame if real_frame is not None else top


def _notify_crash_action(message: str) -> None:
    """Tell the user the outcome of their crash-report choice (best-effort).

    Runs in the excepthook path where wx may be unstable, so it uses the native
    ``MessageBoxW`` (same floor as :func:`_show_native_fallback`) rather than a wx
    dialog. Non-fatal: any failure is swallowed. Its purpose is that pressing
    Send / Copy is never silent for a screen-reader user.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, "QUILL — Crash Report", 0x40)
            return
        except Exception:  # noqa: BLE001
            pass
    try:
        print(message, file=sys.stderr)
    except Exception:  # noqa: BLE001
        pass


def _copy_to_clipboard(text: str) -> None:
    """Copy ``text`` to the clipboard via wx (best-effort)."""
    try:
        import wx  # type: ignore[import-not-found]

        clipboard = wx.TheClipboard  # type: ignore[attr-defined]
        if not clipboard.Open():
            return
        try:
            clipboard.SetData(wx.TextDataObject(text))  # type: ignore[attr-defined]
        finally:
            clipboard.Close()
    except Exception:  # noqa: BLE001
        pass


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

    # #615: apply a pending data-location move (Preferences > General >
    # Data location) before anything resolves app_data_dir() for real, so
    # logs/settings/recovery land in the new location from this launch on.
    apply_pending_data_location_migration()
    # Import data stranded in a prior install's location (queued on first run),
    # before settings are read so the imported files are present this launch.
    apply_pending_legacy_import()
    _propagate_portable_environment()
    ensure_app_directories()
    consolidate_provider_keys_quietly()  # one provider truth (PRD 7): migrate keys
    consolidate_prompts_quietly()  # one prompt store (AI Library): merge legacy prompts
    # One-time, epoch-gated cleanup of stale diagnostic clutter (old logs/crash
    # reports) so upgraders start fresh. Runs before configure_logging opens the
    # active log file, and only touches regenerable diagnostics -- never user work.
    run_pending_startup_maintenance()
    # Add any on-demand-installed speech engine packs (e.g. Faster Whisper) to
    # sys.path so the speech registry can find them this session (#669 follow-up).
    try:
        from quill.core.speech.engine_install import activate_engine_packs

        activate_engine_packs()
    except Exception:  # noqa: BLE001 - an optional engine must never break startup
        pass
    # Add any on-demand-installed AI SDK packs (Copilot/Claude/OpenAI Agents) to
    # sys.path so the harness registry can find them this session (Phase 6/10).
    try:
        from quill.core.ai.sdk_install import activate_ai_packs

        activate_ai_packs()
    except Exception:  # noqa: BLE001 - an optional pack must never break startup
        pass
    log_listener = configure_logging(app_data_dir() / "logs")
    setup_fault_handler()
    _install_excepthook()
    try:
        from quill.core.publishing_bundled import bootstrap_bundled_publishing_providers

        bootstrap_bundled_publishing_providers()

        try:
            _t_import_main_frame = time.perf_counter()
            from quill.ui.main_frame import run_app

            _import_main_frame_seconds = time.perf_counter() - _t_import_main_frame
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
            run_app(
                launch_requests,
                safe_mode=safe_mode,
                diagnostics_mode=diagnostics_mode,
                cold_import_seconds=_import_main_frame_seconds,
            )
        finally:
            release_primary_instance()
    finally:
        log_listener.stop()
    return 0


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
            print(f"Warning: could not open '{candidate.name}': file not found.", file=sys.stderr)
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
