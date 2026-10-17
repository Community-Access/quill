from __future__ import annotations

from pathlib import Path

from quill.platform.windows import sr_announce


def setup_function() -> None:
    sr_announce.enable_transcript_capture(False)
    sr_announce.clear_transcript()
    sr_announce.set_announce_handler(lambda _message: None)
    sr_announce.set_transcript_path(None)


def test_announce_records_transcript_entries_when_enabled() -> None:
    sr_announce.enable_transcript_capture(True)
    sr_announce.announce("alpha")
    sr_announce.announce("beta")

    assert sr_announce.transcript_entries() == ["alpha", "beta"]


def test_announce_writes_transcript_file_when_path_set(tmp_path: Path) -> None:
    target = tmp_path / "a11y.log"
    sr_announce.enable_transcript_capture(True)
    sr_announce.set_transcript_path(target)
    sr_announce.announce("hello")

    assert target.read_text(encoding="utf-8") == "hello\n"


def test_transcript_file_never_holds_a_remembered_secret(tmp_path: Path) -> None:
    from quill.stability.redaction import remember_secret

    remember_secret("hunter2-is-my-password")
    path = tmp_path / "trace.txt"
    sr_announce.enable_transcript_capture(True)
    sr_announce.set_transcript_path(path)
    try:
        sr_announce.announce("Saved key hunter2-is-my-password for Azure")
    finally:
        sr_announce.set_transcript_path(None)
        sr_announce.enable_transcript_capture(False)
    written = path.read_text(encoding="utf-8")
    assert "hunter2-is-my-password" not in written
    assert "[SECRET]" in written
