from __future__ import annotations

import json
import zipfile
from pathlib import Path

from quill.core.diagnostics import (
    build_bug_report_payload,
    build_diagnostics_review_text,
    build_support_issue_url,
    document_snapshot,
    load_diagnostic_events,
    record_diagnostic_event,
    write_diagnostics_bundle,
)
from quill.core.document import Document
from quill.core.notifications import Notification
from quill.core.settings import Settings


def test_document_snapshot_never_leaks_content_and_hashes_path() -> None:
    # Crash reports / bug reports attach this snapshot. It must never carry the
    # document text, and with include_file_paths=False (the crash-report default)
    # the full path is hashed, not sent, so a sensitive path cannot leak.
    secret = "TОP SECRET manuscript body text that must never be sent"
    document = Document(text=secret, path=Path("C:/Private/Resignation letter.docx"))

    snap = document_snapshot(document, include_file_paths=False)
    serialized = json.dumps(snap)

    assert secret not in serialized
    assert "text" not in snap  # no content field at all
    assert "path" not in snap  # full path never included when hashing
    assert snap.get("path_hash")  # the hash stands in for the path
    assert "Private" not in serialized  # the directory path is never present
    # The basename is still exposed via name (shown in the user-reviewed preview).
    assert snap["name"] == "Resignation letter.docx"

    # With include_file_paths=True (explicit opt-in), the raw path is present but
    # the content still is not.
    snap_paths = document_snapshot(document, include_file_paths=True)
    assert snap_paths["path"] == str(document.path)
    assert secret not in json.dumps(snap_paths)


def test_record_diagnostic_event_round_trips(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    record_diagnostic_event("command", "tools.pandoc_wizard")
    events = load_diagnostic_events()

    assert events[-1].kind == "command"
    assert events[-1].name == "tools.pandoc_wizard"


def test_write_diagnostics_bundle_writes_expected_members(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    target = tmp_path / "quill-diagnostics.zip"
    document = Document(text="hello", path=Path("C:/Docs/sample.md"), modified=False)

    write_diagnostics_bundle(
        target,
        settings=Settings(),
        keymap={"file.open": "Ctrl+O"},
        notifications=[
            Notification(
                timestamp="2026-05-29T00:00:00+00:00",
                category="info",
                message="Ready",
            )
        ],
        current_document=document,
        include_file_paths=False,
        extra_environment={"screen_reader": "NVDA"},
    )

    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        assert "metadata.json" in names
        assert "recent-actions.json" in names
        assert "settings-redacted.json" in names
        metadata = json.loads(archive.read("metadata.json").decode("utf-8"))
        assert metadata["screen_reader"] == "NVDA"
        assert metadata["current_document"]["path_hash"]


def test_build_bug_report_payload_mentions_diagnostics() -> None:
    payload = build_bug_report_payload(current_document=Document(text="x"))

    assert "Bug report:" in payload["summary"]
    assert "Save Diagnostics" in payload["body"]


def test_build_bug_report_payload_supports_user_entered_sections() -> None:
    payload = build_bug_report_payload(
        current_document=Document(text="x", path=Path("C:/Docs/sample.md")),
        summary_override="Bug report: Spell check speaks too fast",
        happened="Pressed Speak Word and could not follow the letters.",
        expected="Letters should be spoken slowly and clearly.",
        steps="1. Open spell check\n2. Select misspelling\n3. Press Speak Word",
        diagnostics_note="Attach diagnostics bundle: C:\\Temp\\quill-diagnostics.zip",
    )

    assert payload["summary"] == "Bug report: Spell check speaks too fast"
    assert "Pressed Speak Word" in payload["body"]
    assert "Expected behavior:" in payload["body"]
    assert "Steps to reproduce:" in payload["body"]
    assert "Attach diagnostics bundle" in payload["body"]


def test_build_diagnostics_review_text_mentions_hashing() -> None:
    review = build_diagnostics_review_text(
        settings=Settings(),
        keymap={"file.open": "Ctrl+O"},
        notifications=[],
        current_document=Document(text="x", path=Path("C:/Docs/a.md")),
        include_file_paths=False,
    )

    assert "Diagnostics Review" in review
    assert "File path will be hashed" in review


def test_build_support_issue_url_targets_support_hub() -> None:
    url = build_support_issue_url(
        {"summary": "Bug report: sample", "body": "Body"},
        source_app="Quill",
        version="1.0.0",
        platform_label="Windows 11",
    )

    assert url.startswith("https://github.com/Community-Access/support/issues/new?")
    assert "source-app=Quill" in url


def test_diagnostics_bundle_redacts_log_secrets(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "latest.log").write_text(
        "Authorization: Bearer super-secret-token\napi_key=abc123\nvalue=sk-test-secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("QUILL_DATA_DIR", str(data_dir))

    target = tmp_path / "quill-diagnostics.zip"
    write_diagnostics_bundle(
        target,
        settings=Settings(),
        keymap={},
        notifications=[],
        current_document=None,
        include_file_paths=False,
    )

    with zipfile.ZipFile(target) as archive:
        payload = archive.read("logs/latest.log").decode("utf-8")
        assert "super-secret-token" not in payload
        assert "abc123" not in payload
        assert "sk-test-secret" not in payload
        assert "[REDACTED]" in payload


def test_sanitize_log_text_redacts_broadened_secret_shapes() -> None:
    from quill.core.diagnostics import _sanitize_log_text

    raw = "\n".join([
        "password: hunter2",
        "client_secret=abcdEF1234567890",
        "token = my-very-long-token-value",
        "x-goog-api-key: GOOGSECRETVALUE123",
        "google=AIzaSyA1234567890123456789012345678901234",
        "aws=AKIAABCDEFGHIJKLMNOP",
        "github=ghp_0123456789abcdefghijklmnopqrstuvwx",
    ])
    sanitized = _sanitize_log_text(raw)
    for leaked in (
        "hunter2",
        "abcdEF1234567890",
        "my-very-long-token-value",
        "GOOGSECRETVALUE123",
        "AIzaSyA1234567890123456789012345678901234",
        "AKIAABCDEFGHIJKLMNOP",
        "ghp_0123456789abcdefghijklmnopqrstuvwx",
    ):
        assert leaked not in sanitized
    assert "[REDACTED]" in sanitized


def test_redact_settings_masks_secret_named_fields() -> None:
    from dataclasses import make_dataclass

    from quill.core.diagnostics import redact_settings

    fake_cls = make_dataclass(
        "FakeSettings",
        [("theme", str), ("api_key", str), ("auth_token", str), ("keyboard_pack", str)],
    )
    fake = fake_cls(theme="dark", api_key="secret123", auth_token="tok456", keyboard_pack="Default")

    payload = redact_settings(fake)  # type: ignore[arg-type]

    assert payload["api_key"] == "[REDACTED]"
    assert payload["auth_token"] == "[REDACTED]"
    # Benign fields must be preserved for useful diagnostics.
    assert payload["theme"] == "dark"
    assert payload["keyboard_pack"] == "Default"
