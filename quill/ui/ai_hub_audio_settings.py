"""Where the AI Hub keeps its Audio page: the Deepgram key and max speakers.

Moved out of :mod:`quill.ui.ai_hub_dialog` (GATE-11) unchanged. The key lives
in the credential store; the default max speakers lives in
``ai_audio_settings.json`` in the app data folder.
"""

from __future__ import annotations

_DEEPGRAM_KEY_CRED_TARGET = "QUILL_DEEPGRAM_API_KEY"
_DEEPGRAM_MAX_SPEAKERS_KEY = "deepgram_default_max_speakers"


def _load_deepgram_key() -> str:
    try:
        from quill.platform.windows.credential_manager import load_generic_credential

        stored = load_generic_credential(_DEEPGRAM_KEY_CRED_TARGET)
        return (stored.secret if stored else "") or ""
    except Exception:  # noqa: BLE001
        return ""


def _save_deepgram_key(key: str) -> None:
    try:
        from quill.platform.windows.credential_manager import (
            delete_generic_credential,
            save_generic_credential,
        )

        if key.strip():
            save_generic_credential(_DEEPGRAM_KEY_CRED_TARGET, key.strip())
        else:
            delete_generic_credential(_DEEPGRAM_KEY_CRED_TARGET)
    except Exception:  # noqa: BLE001 - never crash the dialog on a store failure
        # A silently-unsaved API key would look saved but leave transcription
        # broken. Log it so the failure is diagnosable (the dialog surfaces the
        # working/not-working state via its own Test/refresh path).
        import logging

        logging.getLogger("quill.ui.ai_hub_dialog").warning(
            "Could not persist the Deepgram API key to the credential store",
            exc_info=True,
        )


def _load_deepgram_max_speakers() -> int:
    try:
        from quill.core.paths import app_data_dir
        from quill.core.storage import read_json

        data = read_json(app_data_dir() / "ai_audio_settings.json", default={})
        return int(data.get(_DEEPGRAM_MAX_SPEAKERS_KEY, 6))
    except Exception:  # noqa: BLE001
        return 6


def _save_deepgram_max_speakers(value: int) -> None:
    try:
        from quill.core.paths import app_data_dir
        from quill.core.storage import write_json_atomic

        path = app_data_dir() / "ai_audio_settings.json"
        try:
            from quill.core.storage import read_json

            data = dict(read_json(path, default={}))
        except Exception:  # noqa: BLE001
            data = {}
        data[_DEEPGRAM_MAX_SPEAKERS_KEY] = value
        data["schema_version"] = 1  # persistence contract
        write_json_atomic(path, data)
    except Exception:  # noqa: BLE001
        pass
