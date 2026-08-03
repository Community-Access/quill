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
    # Live spell-check-as-you-type alert: a sound, not speech, so the alert
    # never interrupts what the screen reader is saying mid-sentence.
    SPELLING_ALERT = "spelling_alert"

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

    # Companion-app cues (#1302). The apps had no earcons at all before the
    # announcement service: every one of these is a state a listener
    # otherwise had to infer from silence. Kept short and consonant with the
    # Ink pack, and every one is disableable and pack-overridable.
    RADIO_CONNECTING = "radio_connecting"
    RADIO_PLAYING = "radio_playing"
    RADIO_BUFFERING = "radio_buffering"
    RADIO_STOPPED = "radio_stopped"
    RADIO_STREAM_ERROR = "radio_stream_error"
    RADIO_RECORDING_STARTED = "radio_recording_started"
    RADIO_RECORDING_STOPPED = "radio_recording_stopped"
    RADIO_FAVORITE_ADDED = "radio_favorite_added"
    CAST_DOWNLOAD_STARTED = "cast_download_started"
    CAST_DOWNLOAD_COMPLETE = "cast_download_complete"
    CAST_EPISODE_FINISHED = "cast_episode_finished"
    WEATHER_ALERT = "weather_alert"
    BEACON_CAPTURED = "beacon_captured"
    BEACON_SYNC_COMPLETE = "beacon_sync_complete"

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

    # Voice preview (Voice Browser + Download Optional Components hub)
    VOICE_PREVIEW_GENERATING = "voice_preview_generating"

    # Per-slot earcons (audio identity). Numbered features
    # are unusable at speed when every slot sounds the same: each copy-tray
    # slot (1-12) and quick-bookmark slot (0-9) has its own pitch on a shared
    # pentatonic scale, so "slot seven" is a note you learn, not a sentence
    # you wait through. Copy tray and bookmarks use different timbres so the
    # family is instantly recognisable before the pitch lands.
    COPY_SLOT_1 = "copy_slot_1"
    COPY_SLOT_2 = "copy_slot_2"
    COPY_SLOT_3 = "copy_slot_3"
    COPY_SLOT_4 = "copy_slot_4"
    COPY_SLOT_5 = "copy_slot_5"
    COPY_SLOT_6 = "copy_slot_6"
    COPY_SLOT_7 = "copy_slot_7"
    COPY_SLOT_8 = "copy_slot_8"
    COPY_SLOT_9 = "copy_slot_9"
    COPY_SLOT_10 = "copy_slot_10"
    COPY_SLOT_11 = "copy_slot_11"
    COPY_SLOT_12 = "copy_slot_12"
    BOOKMARK_SLOT_0 = "bookmark_slot_0"
    BOOKMARK_SLOT_1 = "bookmark_slot_1"
    BOOKMARK_SLOT_2 = "bookmark_slot_2"
    BOOKMARK_SLOT_3 = "bookmark_slot_3"
    BOOKMARK_SLOT_4 = "bookmark_slot_4"
    BOOKMARK_SLOT_5 = "bookmark_slot_5"
    BOOKMARK_SLOT_6 = "bookmark_slot_6"
    BOOKMARK_SLOT_7 = "bookmark_slot_7"
    BOOKMARK_SLOT_8 = "bookmark_slot_8"
    BOOKMARK_SLOT_9 = "bookmark_slot_9"

    # Progress as audio (5-percent steps plus an indeterminate tick): a short
    # blip whose pitch rises with completion never interrupts speech the way
    # a spoken "forty-five percent" does. The quarter marks carry a touch of
    # harmony and 100 percent resolves, so progress is legible eyes-free.
    PROGRESS_5 = "progress_5"
    PROGRESS_10 = "progress_10"
    PROGRESS_15 = "progress_15"
    PROGRESS_20 = "progress_20"
    PROGRESS_25 = "progress_25"
    PROGRESS_30 = "progress_30"
    PROGRESS_35 = "progress_35"
    PROGRESS_40 = "progress_40"
    PROGRESS_45 = "progress_45"
    PROGRESS_50 = "progress_50"
    PROGRESS_55 = "progress_55"
    PROGRESS_60 = "progress_60"
    PROGRESS_65 = "progress_65"
    PROGRESS_70 = "progress_70"
    PROGRESS_75 = "progress_75"
    PROGRESS_80 = "progress_80"
    PROGRESS_85 = "progress_85"
    PROGRESS_90 = "progress_90"
    PROGRESS_95 = "progress_95"
    PROGRESS_100 = "progress_100"
    PROGRESS_TICK = "progress_tick"

    # Selection and document boundaries: begin/complete selection get a
    # mirrored pair, and the top/bottom of the document get a ceiling tick
    # and a floor thud so hitting an edge is felt, not narrated.
    SELECTION_STARTED = "selection_started"
    SELECTION_COMPLETED = "selection_completed"
    DOCUMENT_TOP = "document_top"
    DOCUMENT_BOTTOM = "document_bottom"

    # Soundcard keep-alive: a silent clip played on a timer (opt-in setting)
    # so cheap USB/Bluetooth audio devices never power down and clip the
    # first earcon after a pause.
    KEEPALIVE = "keepalive"

    # System
    ERROR = "error"
    WARNING = "warning"
    SOUND_ON = "sound_on"
    SOUND_OFF = "sound_off"


def progress_sound_event(percent: int) -> str:
    """The 5-percent-step progress event id at or below *percent*, or "".

    ``progress_sound_event(47) == "progress_45"``. Returns "" below 5 so a
    just-started task stays silent, and clamps at 100. Callers post the sound
    only when the step *changes*, which is what makes progress audible
    without becoming a metronome.
    """
    step = min(100, max(0, int(percent))) // 5 * 5
    return f"progress_{step}" if step >= 5 else ""
