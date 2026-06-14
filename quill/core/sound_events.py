"""Canonical sound event identifiers for QUILL's earcon system.

Each value is the string key used in a QSP manifest's ``events`` mapping and
in ``settings.sound_events_disabled``. No wx, no platform code.
"""

from __future__ import annotations

from enum import StrEnum


class SoundEvent(StrEnum):
    # Editing
    ABBREVIATION_EXPANDED = "abbreviation_expanded"
    ABBREVIATION_DELETED = "abbreviation_deleted"
    SNIPPET_INSERTED = "snippet_inserted"
    AUTOCOMPLETE_ACCEPTED = "autocomplete_accepted"
    WORD_CORRECTED = "word_corrected"

    # Document lifecycle
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_SAVED = "document_saved"
    DOCUMENT_CLOSED = "document_closed"

    # Navigation
    HEADING_JUMPED = "heading_jumped"
    TABLE_ENTERED = "table_entered"
    LIST_ENTERED = "list_entered"
    BROWSE_MODE_ON = "browse_mode_on"
    BROWSE_MODE_OFF = "browse_mode_off"

    # Search
    SEARCH_FOUND = "search_found"
    SEARCH_NOT_FOUND = "search_not_found"
    SEARCH_WRAPPED = "search_wrapped"

    # AI and transcription
    AI_THINKING_STARTED = "ai_thinking_started"
    AI_RESPONSE_RECEIVED = "ai_response_received"
    AI_ERROR = "ai_error"
    TRANSCRIPTION_STARTED = "transcription_started"
    TRANSCRIPTION_STOPPED = "transcription_stopped"
    TRANSCRIPTION_WORD_INSERTED = "transcription_word_inserted"

    # Connectivity
    SSH_CONNECTED = "ssh_connected"
    SSH_DISCONNECTED = "ssh_disconnected"

    # System
    ERROR = "error"
    WARNING = "warning"
    SOUND_ON = "sound_on"
    SOUND_OFF = "sound_off"
