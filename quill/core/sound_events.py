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
    QUILL_KEY_PRESSED = "quill_key_pressed"
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
    # Locked Dictation uses a distinct cue from Hold-to-Dictate so a sustained
    # hands-free session sounds different from a press-and-hold one.
    DICTATION_LOCKED_ON = "dictation_locked_on"
    DICTATION_LOCKED_OFF = "dictation_locked_off"

    # Voice conversation mode (Hey QUILL Phase 2). Warm, consonant bell cues
    # that make every state of a hands-free exchange audible: on/off, the mic
    # opening (listen), an utterance captured (review), an action done (ready),
    # relaxing back (idle), a "still working" tick, and a calm error fall.
    # The wake cue is used by the always-listening "Hey QUILL" loop (Phase 3,
    # shipped); it was defined alongside the Phase 2 cues so sound packs could
    # override the full set from the start.
    CONVERSATION_ON = "conversation_on"
    CONVERSATION_OFF = "conversation_off"
    CONVERSATION_WAKE = "conversation_wake"
    CONVERSATION_LISTEN = "conversation_listen"
    CONVERSATION_REVIEW = "conversation_review"
    CONVERSATION_READY = "conversation_ready"
    CONVERSATION_IDLE = "conversation_idle"
    CONVERSATION_THINKING_TICK = "conversation_thinking_tick"
    CONVERSATION_ERROR = "conversation_error"

    # Connectivity
    SSH_CONNECTED = "ssh_connected"
    SSH_DISCONNECTED = "ssh_disconnected"

    # Indentation depth tones (issue #182)
    # Each level has an _up variant (cursor moved to deeper indent) and a
    # _down variant (cursor moved to shallower indent). Fired only when the
    # indent level changes; blank lines are silent (previous level held).
    # The active tone pack (pentatonic / whole_tone / diatonic / chromatic)
    # maps these canonical IDs to its WAV files at load time.
    INDENT_LEVEL_0_UP = "indent_level_0_up"
    INDENT_LEVEL_0_DOWN = "indent_level_0_down"
    INDENT_LEVEL_1_UP = "indent_level_1_up"
    INDENT_LEVEL_1_DOWN = "indent_level_1_down"
    INDENT_LEVEL_2_UP = "indent_level_2_up"
    INDENT_LEVEL_2_DOWN = "indent_level_2_down"
    INDENT_LEVEL_3_UP = "indent_level_3_up"
    INDENT_LEVEL_3_DOWN = "indent_level_3_down"
    INDENT_LEVEL_4_UP = "indent_level_4_up"
    INDENT_LEVEL_4_DOWN = "indent_level_4_down"
    INDENT_LEVEL_5_UP = "indent_level_5_up"
    INDENT_LEVEL_5_DOWN = "indent_level_5_down"
    INDENT_LEVEL_6_UP = "indent_level_6_up"
    INDENT_LEVEL_6_DOWN = "indent_level_6_down"
    INDENT_LEVEL_7_UP = "indent_level_7_up"
    INDENT_LEVEL_7_DOWN = "indent_level_7_down"

    # Compare mode (issue #186)
    COMPARE_ENTER_MODE = "compare_enter_mode"
    COMPARE_EXIT_MODE = "compare_exit_mode"
    COMPARE_NEXT_DIFFERENCE = "compare_next_difference"
    COMPARE_PREVIOUS_DIFFERENCE = "compare_previous_difference"
    COMPARE_NO_MORE_DIFFERENCES = "compare_no_more_differences"

    # System
    ERROR = "error"
    WARNING = "warning"
    SOUND_ON = "sound_on"
    SOUND_OFF = "sound_off"
