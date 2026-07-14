from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_ONBOARDING_STATE_FILE = "onboarding-complete.json"
_ASSISTANT_ONBOARDING_STATE_FILE = "assistant-onboarding-complete.json"
_SPEECH_ONBOARDING_STATE_FILE = "speech-onboarding-complete.json"
_WATCH_FOLDER_ONBOARDING_STATE_FILE = "watch-folder-onboarding-complete.json"
_GLOW_ONBOARDING_STATE_FILE = "glow-onboarding-complete.json"
_TRUST_CONSENT_STATE_FILE = "trust-consent.json"
_STARTUP_WIZARD_PROMPT_STATE_FILE = "startup-wizard-prompt.json"
_TRUST_CONSENT_VERSION = 2

# Human-readable description of the changes introduced at each trust-consent
# version.  The first entry is the empty string so the very first install
# shows no diff; subsequent entries announce the delta since the prior
# version.  Bump _TRUST_CONSENT_VERSION and append a delta when the trust
# disclosure materially changes.
_TRUST_CONSENT_CHANGE_LOG: dict[int, str] = {
    1: "",
    2: (
        "Trust, privacy, and responsible-AI disclosure updated for QUILL 0.7.0. "
        "The disclosure now names on-device speech recognition and the new local "
        "Quillin extension permission model; cloud AI transcripts continue to not "
        "be persisted, and API keys continue to be stored in Windows Credential "
        "Manager with a DPAPI-encrypted fallback."
    ),
}


def onboarding_complete_path() -> Path:
    return app_data_dir() / _ONBOARDING_STATE_FILE


def assistant_onboarding_complete_path() -> Path:
    return app_data_dir() / _ASSISTANT_ONBOARDING_STATE_FILE


def speech_onboarding_complete_path() -> Path:
    return app_data_dir() / _SPEECH_ONBOARDING_STATE_FILE


def watch_folder_onboarding_complete_path() -> Path:
    return app_data_dir() / _WATCH_FOLDER_ONBOARDING_STATE_FILE


def glow_onboarding_complete_path() -> Path:
    return app_data_dir() / _GLOW_ONBOARDING_STATE_FILE


def trust_consent_state_path() -> Path:
    return app_data_dir() / _TRUST_CONSENT_STATE_FILE


def startup_wizard_prompt_state_path() -> Path:
    return app_data_dir() / _STARTUP_WIZARD_PROMPT_STATE_FILE


def load_onboarding_complete() -> bool:
    raw = read_json(onboarding_complete_path(), default={})
    if not isinstance(raw, dict):
        return False
    return bool(raw.get("completed", False))


def mark_onboarding_complete() -> None:
    write_json_atomic(onboarding_complete_path(), {"completed": True})


def load_assistant_onboarding_complete() -> bool:
    raw = read_json(assistant_onboarding_complete_path(), default={})
    if not isinstance(raw, dict):
        return False
    return bool(raw.get("completed", False))


def mark_assistant_onboarding_complete() -> None:
    write_json_atomic(assistant_onboarding_complete_path(), {"completed": True})


def load_speech_onboarding_complete() -> bool:
    raw = read_json(speech_onboarding_complete_path(), default={})
    if not isinstance(raw, dict):
        return False
    return bool(raw.get("completed", False))


def mark_speech_onboarding_complete() -> None:
    write_json_atomic(speech_onboarding_complete_path(), {"completed": True})


def load_glow_onboarding_complete() -> bool:
    raw = read_json(glow_onboarding_complete_path(), default={})
    if not isinstance(raw, dict):
        return False
    return bool(raw.get("completed", False))


def mark_glow_onboarding_complete() -> None:
    write_json_atomic(glow_onboarding_complete_path(), {"completed": True})


def load_watch_folder_onboarding_complete() -> bool:
    raw = read_json(watch_folder_onboarding_complete_path(), default={})
    if not isinstance(raw, dict):
        return False
    return bool(raw.get("completed", False))


def mark_watch_folder_onboarding_complete() -> None:
    write_json_atomic(watch_folder_onboarding_complete_path(), {"completed": True})


def load_trust_consent_complete() -> bool:
    raw = read_json(trust_consent_state_path(), default={})
    if not isinstance(raw, dict):
        return False
    accepted = bool(raw.get("accepted", False))
    version = int(raw.get("version", 0))
    return accepted and version == _TRUST_CONSENT_VERSION


def current_trust_consent_version() -> int:
    """Return the trust-consent version this build ships (#305)."""
    return _TRUST_CONSENT_VERSION


def trust_consent_change_log() -> dict[int, str]:
    """Return a copy of the version -> delta map (#305).

    Callers use this to render the "what changed since your prior consent"
    banner for the re-consent dialog.  The map is keyed by consent version
    and values are short human-readable descriptions of the changes.
    """
    return dict(_TRUST_CONSENT_CHANGE_LOG)


@dataclass(frozen=True)
class TrustConsentStatus:
    """Result of inspecting the on-disk trust consent state (#305).

    ``accepted`` is True only when the user has accepted the disclosure at
    the current version.  ``loaded_version`` is the version stamp on disk
    (0 if no consent file exists).  ``needs_reconsent`` is True when the
    user previously accepted an older version of the disclosure.
    """

    accepted: bool
    loaded_version: int

    @property
    def needs_reconsent(self) -> bool:
        return self.accepted and self.loaded_version < _TRUST_CONSENT_VERSION


def load_trust_consent_status() -> TrustConsentStatus:
    """Return the trust-consent state from disk (#305).

    Never raises.  A missing or malformed file yields
    ``TrustConsentStatus(accepted=False, loaded_version=0)``.
    """
    raw = read_json(trust_consent_state_path(), default={})
    if not isinstance(raw, dict):
        return TrustConsentStatus(accepted=False, loaded_version=0)
    accepted = bool(raw.get("accepted", False))
    try:
        version = int(raw.get("version", 0))
    except (TypeError, ValueError):
        version = 0
    if accepted and version == _TRUST_CONSENT_VERSION:
        return TrustConsentStatus(accepted=True, loaded_version=version)
    return TrustConsentStatus(accepted=False, loaded_version=version)


def mark_trust_consent_complete() -> None:
    write_json_atomic(
        trust_consent_state_path(),
        {
            "accepted": True,
            "version": _TRUST_CONSENT_VERSION,
        },
    )


def load_startup_wizard_prompt_suppressed() -> bool:
    raw = read_json(startup_wizard_prompt_state_path(), default={})
    if not isinstance(raw, dict):
        return False
    return bool(raw.get("suppressed", False))


def mark_startup_wizard_prompt_suppressed() -> None:
    write_json_atomic(startup_wizard_prompt_state_path(), {"suppressed": True})
