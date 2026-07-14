from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.onboarding import (
    current_trust_consent_version,
    load_assistant_onboarding_complete,
    load_glow_onboarding_complete,
    load_onboarding_complete,
    load_startup_wizard_prompt_suppressed,
    load_trust_consent_complete,
    load_trust_consent_status,
    load_watch_folder_onboarding_complete,
    mark_assistant_onboarding_complete,
    mark_glow_onboarding_complete,
    mark_onboarding_complete,
    mark_startup_wizard_prompt_suppressed,
    mark_trust_consent_complete,
    mark_watch_folder_onboarding_complete,
    trust_consent_change_log,
)
from quill.core.storage import write_json_atomic


def test_onboarding_completion_is_stored_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    assert load_onboarding_complete() is False

    (tmp_path / "features.json").write_text(
        '{"active_profile_id": "essential"}',
        encoding="utf-8",
    )
    assert load_onboarding_complete() is False

    mark_onboarding_complete()

    assert load_onboarding_complete() is True
    assert (tmp_path / "onboarding-complete.json").exists()


def test_assistant_onboarding_completion_is_stored_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    assert load_assistant_onboarding_complete() is False

    mark_assistant_onboarding_complete()

    assert load_assistant_onboarding_complete() is True
    assert (tmp_path / "assistant-onboarding-complete.json").exists()


def test_watch_folder_onboarding_completion_is_stored_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    assert load_watch_folder_onboarding_complete() is False

    mark_watch_folder_onboarding_complete()

    assert load_watch_folder_onboarding_complete() is True
    assert (tmp_path / "watch-folder-onboarding-complete.json").exists()


def test_glow_onboarding_completion_is_stored_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    assert load_glow_onboarding_complete() is False

    mark_glow_onboarding_complete()

    assert load_glow_onboarding_complete() is True
    assert (tmp_path / "glow-onboarding-complete.json").exists()


def test_trust_consent_completion_is_versioned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    assert load_trust_consent_complete() is False
    mark_trust_consent_complete()
    assert load_trust_consent_complete() is True
    assert (tmp_path / "trust-consent.json").exists()


def test_startup_wizard_prompt_suppression_is_stored_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    assert load_startup_wizard_prompt_suppressed() is False

    mark_startup_wizard_prompt_suppressed()

    assert load_startup_wizard_prompt_suppressed() is True
    assert (tmp_path / "startup-wizard-prompt.json").exists()


# ---------------------------------------------------------------------------
# #305 -- trust-consent re-consent flow for users with older consent.
# ---------------------------------------------------------------------------


def test_trust_consent_status_no_file_returns_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    status = load_trust_consent_status()

    assert status.accepted is False
    assert status.loaded_version == 0
    assert status.needs_reconsent is False


def test_trust_consent_status_current_version_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    mark_trust_consent_complete()

    status = load_trust_consent_status()

    assert status.accepted is True
    assert status.loaded_version == current_trust_consent_version()
    assert status.needs_reconsent is False


def test_trust_consent_status_older_version_is_unaccepted_with_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    current = current_trust_consent_version()
    older = current - 1 if current > 1 else 1
    write_json_atomic(
        tmp_path / "trust-consent.json",
        {"accepted": True, "version": older},
    )

    status = load_trust_consent_status()

    # The boolean "complete" gate stays False (no silent re-acceptance), but
    # the status preserves the drift so the re-consent dialog can describe it.
    assert load_trust_consent_complete() is False
    assert status.accepted is False
    assert status.loaded_version == older
    assert status.needs_reconsent is False  # because accepted=False


def test_trust_consent_status_reconsent_helper_flags_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    current = current_trust_consent_version()
    older = current - 1 if current > 1 else 1
    # Simulate the "user accepted at older version" state and verify the
    # helper correctly computes the drift once we promote it to accepted.
    status = load_trust_consent_status()
    promoted = type(status)(accepted=True, loaded_version=older)
    assert promoted.needs_reconsent is True


def test_trust_consent_status_handles_malformed_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    write_json_atomic(
        tmp_path / "trust-consent.json",
        {"accepted": True, "version": "not-a-number"},
    )

    status = load_trust_consent_status()

    assert status.accepted is False
    assert status.loaded_version == 0


def test_trust_consent_status_handles_non_dict_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    write_json_atomic(tmp_path / "trust-consent.json", [1, 2, 3])

    status = load_trust_consent_status()

    assert status.accepted is False
    assert status.loaded_version == 0


def test_trust_consent_change_log_has_entry_for_current_version() -> None:
    """The change log must include a non-empty delta for the current version
    so the re-consent dialog has something to announce (#305)."""
    current = current_trust_consent_version()
    log = trust_consent_change_log()
    assert current in log
    assert log[current], "current version must have a non-empty delta"
