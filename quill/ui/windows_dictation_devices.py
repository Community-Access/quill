"""Which microphones and Windows speech languages this computer has, by name.

For Dictation Settings (:mod:`quill.ui.windows_dictation_dialog`). Each probe
never raises: a machine without Windows speech, or without an audio stack, gets
an empty list, which is the honest answer. Kept out of the dialog module so the
window itself stays about the window.
"""

from __future__ import annotations

__all__ = ["default_microphone_name", "microphone_names", "recognizer_names"]


def microphone_names() -> list[str]:
    """Every microphone by name: Windows speech's full names, else sounddevice's."""
    names: list[str] = []
    try:
        from quill.platform.windows.sapi_dictation import list_microphones

        names = [microphone.name for microphone in list_microphones()]
    except Exception:  # noqa: BLE001 - try the other list
        names = []
    if not names:
        try:
            from quill.core.windows_dictation.local_recognizer import list_input_names

            names = list_input_names()
        except Exception:  # noqa: BLE001 - an empty list is the honest answer
            names = []
    return names


def recognizer_names() -> list[str]:
    try:
        from quill.platform.windows.sapi_dictation import list_recognizers

        return list_recognizers()
    except Exception:  # noqa: BLE001 - Windows speech not available here
        return []


def default_microphone_name() -> str:
    try:
        from quill.platform.windows.sapi_dictation import default_microphone_id, list_microphones

        default_id = default_microphone_id()
        return next((m.name for m in list_microphones() if m.id == default_id), "")
    except Exception:  # noqa: BLE001 - the row simply does not name it
        return ""
