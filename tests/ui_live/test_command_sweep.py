"""Command sweep: invoke every in-process command and assert none crashes.

With a live frame and a sample document, this fires each registered command's
handler (modals auto-dismissed) and checks the frame survives. It is the broad
multiplier: every command — and every *future* command — gets a "does not crash
when run" check for free. Side-effecting categories (open a browser/Explorer,
network, spawn a subprocess, quit/close/restart, microphone capture) are skipped
so the sweep stays in-process and side-effect-free; what remains is the large
crash-prone surface (navigation, editing, formatting, view, verbosity, ...).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live_ui

# Skip a command when its id contains any of these — they leave the process,
# touch the network/filesystem/hardware, or tear the app down.
_SKIP_SUBSTRINGS = (
    "exit",
    "quit",
    "close",
    "restart",
    "reload",
    "delete",
    "forget",
    "uninstall",
    "clear_recent",
    "remote",
    "github",
    "update",  # check-for-updates: network
    "report_bug",
    "feedback",
    "export",  # may shell out to pandoc
    "import",
    "convert",
    "batch",
    "print",
    "page_setup",
    "dictation",  # microphone
    "voice_command",  # microphone
    "transcribe",
    "captions",
    "read_aloud",  # starts a TTS engine / audio
    "open_log",
    "open_diagnostics",
    "reveal",
    "browser",  # opens a system browser
    "ai_",  # AI provider calls
    "assistant",
    "speech_models",  # network download
)

_SKIP_IDS = {
    "app.exit",
    "file.new",  # replaces the active document; keep the sweep's doc stable
}


def _should_skip(command_id: str) -> bool:
    if command_id in _SKIP_IDS:
        return True
    lowered = command_id.lower()
    return any(token in lowered for token in _SKIP_SUBSTRINGS)


def test_invoking_every_command_does_not_crash(build_frame, tmp_path) -> None:
    import wx

    frame = build_frame(safe_mode=True, settings={"setup_wizard_completed": True})

    # Give the sweep real content and a selection to act on.
    target = tmp_path / "sweep.md"
    target.write_text(
        "# Heading\n\nThe quick brown fox jumps over the lazy dog.\n\n- one\n- two\n",
        encoding="utf-8",
        newline="",
    )
    frame.open_file(path=target, record_recent=False)
    editor = frame.editor
    if hasattr(editor, "SetSelection") and hasattr(editor, "GetLastPosition"):
        editor.SetSelection(0, min(9, editor.GetLastPosition()))

    commands = list(frame.commands.list())
    assert len(commands) > 100, "expected the full command surface to be registered"

    failures: list[str] = []
    swept = 0
    for command in commands:
        if _should_skip(command.id):
            continue
        swept += 1
        try:
            command.handler()
            wx.SafeYield()
        except Exception as exc:  # noqa: BLE001 - capturing crashes is the point
            failures.append(f"{command.id}: {type(exc).__name__}: {exc}")
        # The frame must still be alive after each command.
        if not frame.frame:  # a destroyed wx object is falsy
            failures.append(f"{command.id}: destroyed the main frame")
            break

    assert swept > 50, f"sweep covered too few commands ({swept}); check the skip list"
    assert not failures, f"{len(failures)} command(s) raised during the sweep:\n  " + "\n  ".join(
        failures
    )
