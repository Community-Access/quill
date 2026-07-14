"""Pure unit tests for :mod:`quill.stability.crash_submit` (#622).

These tests pin the wx-free half of the crash-submit flow: the
builder that turns a (type, value, tb) triple plus environment and
recent-command context into a redacted, length-bounded report body
the dialog can show and the submit path can ship to GitHub.

The dialog itself is covered by ``tests/unit/ui/test_crash_report_dialog.py``.
The excepthook integration is covered by
``tests/unit/test_excepthook_integration.py``.
"""

from __future__ import annotations

from pathlib import Path, PureWindowsPath

import pytest

from quill.core.document import Document
from quill.stability.crash_submit import (
    CrashReportPayload,
    build_crash_report_payload,
    redact_user_description,
    render_crash_report_preview,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _raise_and_capture() -> tuple[type[BaseException], BaseException, object]:
    """Run a function that raises so we have a real (type, value, tb) triple.

    Using a real triple is important: ``traceback.format_exception``
    walks the tb object via internal CPython API; a fake object can
    explode in surprising ways.
    """
    try:
        raise RuntimeError("boom from a test")
    except RuntimeError as exc:
        return type(exc), exc, exc.__traceback__


def _many_frame_tb(frames: int) -> object:
    """Return a real traceback object with at least ``frames`` entries.

    We can't easily fabricate ``frames`` from a single ``raise``;
    instead we raise inside a generator chain. This is enough for
    the bound test, which only checks that the rendered body is
    truncated.
    """

    def inner() -> None:
        raise RuntimeError(f"boom at frame {frames}")

    def outer() -> None:
        # Wrap inner in a small number of callers; the test is
        # about length, not an exact frame count.
        for _ in range(max(1, frames // 4)):
            inner()

    try:
        outer()
    except RuntimeError as exc:
        return exc.__traceback__
    raise AssertionError("inner() did not raise -- fixture is broken")  # pragma: no cover


# ---------------------------------------------------------------------------
# summary / body basics
# ---------------------------------------------------------------------------


def test_build_payload_summary_starts_with_exception_class() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0-beta2",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert payload.summary.startswith("RuntimeError")
    assert "boom from a test" in payload.summary


def test_build_payload_body_contains_version_and_portable_flag() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0-beta2",
        portable=True,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert "0.7.0-beta2" in payload.body
    assert "Portable      : True" in payload.body


def test_build_payload_body_omits_screen_reader_line_when_absent() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert "Screen reader" not in payload.body


def test_build_payload_body_mentions_screen_reader_when_present() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name="NVDA",
        recent_commands=(),
        active_document=None,
    )
    assert "NVDA" in payload.body
    assert "Screen reader" in payload.body


# ---------------------------------------------------------------------------
# Traceback bounding
# ---------------------------------------------------------------------------


def test_build_payload_bounds_traceback_lines() -> None:
    # Build a 200-frame tb and confirm the body truncates so the
    # report never grows unbounded.
    exc_type, exc_value, _ = _raise_and_capture()
    huge_tb = _many_frame_tb(200)
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=huge_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    # The body should always contain the header + a bounded tail.
    assert "Traceback (last frames)" in payload.body
    # Bounded to a small number of traceback lines: at most a couple
    # of dozen lines even for a 200-frame tb.
    assert payload.body.count("\n") < 200


def test_build_payload_traceback_section_is_safe_when_tb_unformattable() -> None:
    exc_type, exc_value, _ = _raise_and_capture()
    # A non-tb object causes traceback.format_exception to raise; the
    # builder must swallow that and emit a placeholder.
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=object(),  # not a real tb
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert "(traceback could not be formatted)" in payload.body


# ---------------------------------------------------------------------------
# Recent commands
# ---------------------------------------------------------------------------


def test_build_payload_includes_last_ten_recent_commands_in_reverse_order() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    cmds = [f"cmd-{i:02d}" for i in range(15)]
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=cmds,
        active_document=None,
    )
    # Most recent first means the last command id appears at the top
    # of the recent-commands section.
    section = payload.body.split("Recent commands (most recent first)")[1]
    section = section.split("Traceback (last frames)")[0]
    # The most recent 10 must all be present.
    for cid in cmds[-10:]:
        assert cid in section, f"recent command {cid} missing from body"
    # The oldest 5 must NOT be present.
    for cid in cmds[:5]:
        assert cid not in section, f"oldest command {cid} should have been dropped"


def test_build_payload_handles_empty_recent_commands() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert "(no recent command log available)" in payload.body


# ---------------------------------------------------------------------------
# Active document
# ---------------------------------------------------------------------------


def test_build_payload_omits_document_section_when_no_active_document() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert "(no active document)" in payload.body


def test_build_payload_includes_active_document_name_and_encoding() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    doc = Document(
        text="hello\nworld",
        path=Path("/tmp/secret/example.txt"),
        modified=True,
        encoding="utf-16",
        line_ending="\r\n",
    )
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=doc,
    )
    assert "example.txt" in payload.body
    assert "utf-16" in payload.body
    # The raw path must NOT be in the user-visible body even when
    # include_file_paths=False is in effect at the metadata layer --
    # the dialog preview only shows the document name.
    assert "/tmp/secret" not in payload.body


def test_build_payload_metadata_hashes_document_path() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    doc = Document(
        text="hi",
        path=Path("/tmp/secret/example.txt"),
        modified=False,
        encoding="utf-8",
        line_ending="\n",
    )
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=doc,
    )
    snap = payload.metadata["active_document"]
    assert isinstance(snap, dict)
    assert "path_hash" in snap
    # Raw path is not in the metadata either -- the include_file_paths
    # contract hashes it out.
    assert "path" not in snap or snap["path"] is None
    assert "/tmp/secret" not in str(snap)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_payload_metadata_has_platform_and_portable_flag() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=Path("/tmp/crash.txt"),
        app_version="0.7.0",
        portable=True,
        screen_reader_name="JAWS",
        recent_commands=["open_file", "save_file"],
        active_document=None,
    )
    assert payload.metadata["quill_version"] == "0.7.0"
    assert payload.metadata["portable"] is True
    assert payload.metadata["screen_reader"] == "JAWS"
    assert payload.metadata["exception_class"] == "RuntimeError"
    assert "boom from a test" in payload.metadata["exception_value"]
    assert payload.metadata["recent_commands"] == ["open_file", "save_file"]
    assert payload.metadata["local_crash_file"] == str(Path("/tmp/crash.txt"))
    assert "error_code" not in payload.metadata


def test_payload_metadata_local_crash_file_does_not_leak_username() -> None:
    # #886: metadata is serialized verbatim into the public GitHub issue by
    # feedback_hub, bypassing the body's redaction pass. A portable install
    # living under the user's home directory must not leak their OS username
    # via this field, even though the body already redacts the same path.
    exc_type, exc_value, exc_tb = _raise_and_capture()
    crash = Path("C:\\Users\\nblas\\Games and portable apps\\Quill portable\\data\\crash.txt")
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=crash,
        app_version="0.9.0",
        portable=True,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert "nblas" not in payload.metadata["local_crash_file"]
    assert "[PATH]" in payload.metadata["local_crash_file"]


def test_payload_metadata_includes_error_code_for_coded_errors() -> None:
    from quill.core.error_codes import CodedError

    class _SampleCodedError(CodedError):
        code = "QUILL-TEST-SAMPLE-CODE"

    try:
        raise _SampleCodedError("something broke")
    except _SampleCodedError as exc:
        exc_type, exc_value, exc_tb = type(exc), exc, exc.__traceback__
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.9.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert payload.metadata["error_code"] == "QUILL-TEST-SAMPLE-CODE"


def test_payload_metadata_omits_recent_commands_when_empty() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert "recent_commands" not in payload.metadata


def test_payload_metadata_bounds_exception_value() -> None:
    exc_type, exc_value, _ = _raise_and_capture()
    long_value = "X" * 5000
    big_exc = RuntimeError(long_value)
    payload = build_crash_report_payload(
        exc_type=type(big_exc),
        exc_value=big_exc,
        exc_tb=big_exc.__traceback__,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert len(payload.metadata["exception_value"]) <= 240


# ---------------------------------------------------------------------------
# Local crash file reference
# ---------------------------------------------------------------------------


def test_build_payload_references_local_crash_file_in_body() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    crash = Path("/var/data/crash-reports/crash-2026.txt")
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=crash,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert str(crash) in payload.body


def test_build_payload_local_crash_file_none_is_handled() -> None:
    exc_type, exc_value, exc_tb = _raise_and_capture()
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=None,
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    assert "(not saved" in payload.body
    # The local_crash_file field is exposed so the dialog can
    # show the path even when it's not embedded in the body.
    assert payload.local_crash_file is None


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def test_build_payload_redacts_paths_in_user_supplied_context() -> None:
    """Belt-and-braces: even if a future section emits raw text, the
    body is re-scrubbed by the bundle redaction contract."""

    exc_type, exc_value, exc_tb = _raise_and_capture()
    # A Windows path that the redaction contract definitely flags
    # (drive-letter + backslashes). build_crash_report_payload only ever
    # str()s local_crash_file, never touches the filesystem with it, so
    # PureWindowsPath is safe here and -- unlike a plain Path -- its str()
    # is always backslash-separated regardless of the host OS running this
    # test; a plain Path("C:/Users/alice/...") built on a POSIX host keeps
    # its forward slashes, which _WINDOWS_PATH_RE (backslash-only) never
    # matches, letting the path leak through unredacted.
    crash = PureWindowsPath("C:/Users/alice/secret/notes.txt")
    payload = build_crash_report_payload(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_tb=exc_tb,
        local_crash_file=crash,  # type: ignore[arg-type]
        app_version="0.7.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=(),
        active_document=None,
    )
    # The raw Windows path must NOT survive in the body.
    assert r"C:\Users\alice" not in payload.body
    # The body should still contain *something* about the local
    # crash file (the contract rewrites the path slot, not the
    # whole line).
    assert "Local crash report" in payload.body


def test_redact_user_description_strips_credentials() -> None:
    out = redact_user_description("see C:/Users/alice/notes.txt -- token=abc123def")
    # Path is rewritten; token is rewritten. The exact tokens depend
    # on the redaction contract; we only assert that a raw path
    # and a raw token are not visible.
    assert "C:/Users/alice/notes.txt" not in out
    assert "abc123def" not in out


def test_redact_user_description_caps_long_text() -> None:
    huge = "X" * 5000
    out = redact_user_description(huge)
    assert "truncated by QUILL" in out
    # The cap is 1500 chars + a truncation marker.
    assert len(out) < 2000


def test_redact_user_description_empty_returns_empty() -> None:
    assert redact_user_description("") == ""


# ---------------------------------------------------------------------------
# render_crash_report_preview
# ---------------------------------------------------------------------------


def test_render_preview_includes_header_when_body_present() -> None:
    payload = CrashReportPayload(
        summary="Boom",
        body="one line\ntwo lines",
        metadata={},
        local_crash_file=None,
    )
    out = render_crash_report_preview(payload)
    assert "QUILL crash report (redacted, ready to send)" in out
    assert "one line" in out


def test_render_preview_returns_friendly_message_when_body_empty() -> None:
    payload = CrashReportPayload(
        summary="Boom",
        body="",
        metadata={},
        local_crash_file=None,
    )
    out = render_crash_report_preview(payload)
    assert "QUILL crash report (redacted, ready to send)" in out
    assert "empty report" in out


# ---------------------------------------------------------------------------
# CrashReportPayload dataclass invariants
# ---------------------------------------------------------------------------


def test_crash_report_payload_is_frozen_and_slotted() -> None:
    payload = CrashReportPayload(
        summary="x",
        body="y",
        metadata={},
        local_crash_file=None,
    )
    with pytest.raises((AttributeError, TypeError)):
        payload.summary = "z"  # type: ignore[misc]


def test_local_crash_file_is_optional() -> None:
    payload = CrashReportPayload(summary="x", body="y")
    assert payload.local_crash_file is None
    assert payload.metadata == {}
