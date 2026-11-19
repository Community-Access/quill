"""GitHub's service status, in words (complete.md 1.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.github import service_status as ss

_SUMMARY = {
    "status": {"indicator": "minor", "description": "Partial System Outage"},
    "components": [
        {"name": "Git Operations", "status": "operational"},
        {"name": "Actions", "status": "degraded_performance"},
        {"name": "Pages", "status": "major_outage"},
        {"name": "Visit www.githubstatus.com", "status": "partial_outage", "group": True},
    ],
    "incidents": [
        {
            "name": "Disruption with some GitHub services",
            "status": "investigating",
            "incident_updates": [
                {"body": "We are  investigating reports\nof slow Actions runs."},
                {"body": "older"},
            ],
        }
    ],
}


def test_everything_working_says_so() -> None:
    text = ss.parse_summary(
        {"status": {"description": "All Systems Operational"}, "components": [], "incidents": []}
    ).sentences()
    assert text == "GitHub says: All Systems Operational.\nGitHub lists no incident."


def test_trouble_names_parts_and_the_latest_update() -> None:
    status = ss.parse_summary(_SUMMARY)
    assert status.overall == "GitHub says: Partial System Outage."
    assert status.trouble == ["Actions is slow", "Pages is down"]
    assert status.incidents == [
        "Disruption with some GitHub services, investigating. Latest: We are investigating "
        "reports of slow Actions runs."
    ]
    assert "Not working normally: Actions is slow; Pages is down." in status.sentences()


def test_a_strange_answer_still_reads() -> None:
    assert ss.parse_summary({}).sentences().startswith("GitHub says: GitHub did not say")


def test_consent_is_remembered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ss, "app_data_dir", lambda: tmp_path)
    assert not ss.consented()
    ss.record_consent()
    assert ss.consented()


def test_a_failed_read_is_one_coded_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Opener:
        def open(self, *_a: object, **_k: object) -> None:
            raise OSError("offline")

    monkeypatch.setattr(ss, "build_opener", lambda *_a: _Opener())
    with pytest.raises(ss.ServiceStatusError, match="could not read GitHub's status page"):
        ss.read_status()
    assert ss.ServiceStatusError.code == "QUILL-GITHUB-STATUS-READ"
