"""What each sound event is *called*, and which group it belongs to.

Split out of :mod:`quill.ui.sound_events_dialog` so the Sound Scheme window and
the older Sound Events checklist cannot disagree about what an event is called.
They did not disagree yet; they would have, the first time somebody added an
event to one table and not the other, and the failure mode is a listener hearing
two different names for one sound and reasonably concluding they are two sounds.

**Grouped, and the grouping is the reading order.** Ninety-odd events in
declaration order is a list nobody can navigate. Grouped by the moment they
belong to -- the clipboard, the document, moving about, the assistant -- they
become a catalogue you can arrow through, because the group name is the first
thing in every row and a listener can skip a whole family in one press of Down.

**Named for the moment, not for the mechanism.** "Paste" rather than
``text_pasted``, "Nothing left to undo" rather than ``nothing_to_undo``. The id
is what a bug report quotes; the label is what somebody looking for the right
row reads.

No wx here, so the catalogue is importable from anywhere and testable without a
display -- including by the gate that checks every declared event has a label.
"""

from __future__ import annotations

__all__ = ["EVENT_GROUPS", "GROUP_FOR", "LABELS", "label_for"]

#: ``(group title, event ids)``, in the order the Sound Scheme window shows
#: them. An event that exists and is missing here would be invisible in that
#: window, which is why ``tests/unit/ui/test_sound_event_labels.py`` asserts the
#: two sets match exactly.
EVENT_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "The app",
        ("app_started", "app_exiting", "sound_on", "sound_off", "keepalive"),
    ),
    (
        "Documents",
        (
            "document_created",
            "document_opened",
            "document_saved",
            "document_closed",
            "print_started",
            "print_complete",
        ),
    ),
    (
        "Clipboard",
        ("text_cut", "text_copied", "text_pasted", "text_deleted"),
    ),
    (
        "Undo",
        ("undo_performed", "redo_performed", "nothing_to_undo"),
    ),
    (
        "Writing",
        (
            "abbreviation_expanded",
            "abbreviation_deleted",
            "snippet_inserted",
            "autocomplete_accepted",
            "word_corrected",
            "spelling_alert",
        ),
    ),
    (
        "Selection and edges",
        (
            "selection_started",
            "selection_completed",
            "document_top",
            "document_bottom",
        ),
    ),
    (
        "Moving about",
        (
            "quill_key_pressed",
            "heading_jumped",
            "table_entered",
            "list_entered",
            "browse_mode_on",
            "browse_mode_off",
        ),
    ),
    (
        "Finding",
        ("search_found", "search_not_found", "search_wrapped"),
    ),
    (
        "Comparing",
        (
            "compare_enter_mode",
            "compare_exit_mode",
            "compare_next_difference",
            "compare_previous_difference",
            "compare_no_more_differences",
        ),
    ),
    (
        "The assistant",
        (
            "ai_thinking_started",
            "ai_response_received",
            "ai_error",
            "voice_preview_generating",
        ),
    ),
    (
        "Dictation",
        (
            "transcription_started",
            "transcription_stopped",
            "transcription_word_inserted",
            "dictation_locked_on",
            "dictation_locked_off",
            "windows_dictation_on",
            "windows_dictation_phrase",
            "windows_dictation_off",
            "windows_dictation_error",
        ),
    ),
    (
        "Talking to QUILL",
        (
            "conversation_on",
            "conversation_off",
            "conversation_wake",
            "conversation_listen",
            "conversation_review",
            "conversation_ready",
            "conversation_idle",
            "conversation_thinking_tick",
            "conversation_error",
        ),
    ),
    (
        "Messages",
        ("information", "question", "warning", "error", "task_complete"),
    ),
    (
        "Connections",
        ("ssh_connected", "ssh_disconnected"),
    ),
    (
        "Radio and Cast",
        (
            "radio_connecting",
            "radio_playing",
            "radio_buffering",
            "radio_stopped",
            "radio_stream_error",
            "radio_recording_started",
            "radio_recording_stopped",
            "radio_favorite_added",
            "radio_reminder",
            "cast_download_started",
            "cast_download_complete",
            "cast_episode_finished",
            "weather_alert",
            "beacon_captured",
            "beacon_sync_complete",
        ),
    ),
    (
        "Copy tray slots",
        tuple(f"copy_slot_{n}" for n in range(1, 13)),
    ),
    (
        "Bookmark slots",
        tuple(f"bookmark_slot_{n}" for n in range(10)),
    ),
    (
        "Progress",
        (*(f"progress_{n}" for n in range(5, 101, 5)), "progress_tick"),
    ),
    (
        "Indentation depth",
        tuple(
            f"indent_level_{level}_{direction}"
            for level in range(8)
            for direction in ("up", "down")
        ),
    ),
)

LABELS: dict[str, str] = {
    # The app
    "app_started": "App started",
    "app_exiting": "App closing",
    "sound_on": "Sound switched on",
    "sound_off": "Sound switched off",
    "keepalive": "Keep the sound card awake (silent)",
    # Documents
    "document_created": "New document",
    "document_opened": "Open a document",
    "document_saved": "Save a document",
    "document_closed": "Close a document",
    "print_started": "Printing started",
    "print_complete": "Printing finished",
    # Clipboard
    "text_cut": "Cut",
    "text_copied": "Copy",
    "text_pasted": "Paste",
    "text_deleted": "Delete text",
    # Undo
    "undo_performed": "Undo",
    "redo_performed": "Redo",
    "nothing_to_undo": "Nothing left to undo",
    # Writing
    "abbreviation_expanded": "Abbreviation expanded",
    "abbreviation_deleted": "Abbreviation taken back",
    "snippet_inserted": "Snippet inserted",
    "autocomplete_accepted": "Autocomplete accepted",
    "word_corrected": "Autocorrect changed a word",
    "spelling_alert": "Possible misspelling as you type",
    # Selection and edges
    "selection_started": "Selection started",
    "selection_completed": "Selection finished",
    "document_top": "Top of the document",
    "document_bottom": "Bottom of the document",
    # Moving about
    "quill_key_pressed": "QUILL key pressed",
    "heading_jumped": "Moved to a heading",
    "table_entered": "Entered a table",
    "list_entered": "Entered a list",
    "browse_mode_on": "Browse mode on",
    "browse_mode_off": "Browse mode off",
    # Finding
    "search_found": "Found it",
    "search_not_found": "Not found",
    "search_wrapped": "Search wrapped around",
    # Comparing
    "compare_enter_mode": "Compare mode on",
    "compare_exit_mode": "Compare mode off",
    "compare_next_difference": "Next difference",
    "compare_previous_difference": "Previous difference",
    "compare_no_more_differences": "No more differences",
    # The assistant
    "ai_thinking_started": "Assistant thinking",
    "ai_response_received": "Assistant answered",
    "ai_error": "Assistant could not answer",
    "voice_preview_generating": "Making a voice preview",
    # Dictation
    "transcription_started": "Dictation started",
    "transcription_stopped": "Dictation stopped",
    "transcription_word_inserted": "Dictated word inserted",
    "dictation_locked_on": "Hands-free dictation on",
    "dictation_locked_off": "Hands-free dictation off",
    "windows_dictation_on": "Live dictation listening",
    "windows_dictation_phrase": "Live dictation wrote a phrase",
    "windows_dictation_off": "Live dictation stopped listening",
    "windows_dictation_error": "Live dictation could not go on",
    # Talking to QUILL
    "conversation_on": "Conversation mode on",
    "conversation_off": "Conversation mode off",
    "conversation_wake": "Heard its name",
    "conversation_listen": "Listening",
    "conversation_review": "Caught what you said",
    "conversation_ready": "Ready",
    "conversation_idle": "Resting",
    "conversation_thinking_tick": "Still working",
    "conversation_error": "Something went wrong",
    # Messages
    "information": "Information",
    "question": "A question for you",
    "warning": "Warning",
    "error": "Error",
    "task_complete": "Task finished",
    # Connections
    "ssh_connected": "Connected to a server",
    "ssh_disconnected": "Disconnected from a server",
    # Radio and Cast
    "radio_connecting": "Radio connecting",
    "radio_playing": "Radio playing",
    "radio_buffering": "Radio buffering",
    "radio_stopped": "Radio stopped",
    "radio_stream_error": "Radio stream failed",
    "radio_recording_started": "Recording started",
    "radio_recording_stopped": "Recording stopped",
    "radio_favorite_added": "Added to favourites",
    "radio_reminder": "Reminder due",
    "cast_download_started": "Episode download started",
    "cast_download_complete": "Episode downloaded",
    "cast_episode_finished": "Episode finished",
    "weather_alert": "Weather alert",
    "beacon_captured": "Item captured",
    "beacon_sync_complete": "Sync finished",
    "progress_tick": "Working (indeterminate)",
}

LABELS.update({f"copy_slot_{n}": f"Copy tray slot {n}" for n in range(1, 13)})
LABELS.update({f"bookmark_slot_{n}": f"Bookmark slot {n}" for n in range(10)})
LABELS.update({f"progress_{n}": f"Progress {n} percent" for n in range(5, 101, 5)})
LABELS.update({
    f"indent_level_{level}_{direction}": (
        f"Indent level {level}, {'deeper' if direction == 'up' else 'shallower'}"
    )
    for level in range(8)
    for direction in ("up", "down")
})

#: Which group each event is in, for a caller that has an id and wants context.
GROUP_FOR: dict[str, str] = {event: group for group, events in EVENT_GROUPS for event in events}


def label_for(event: str) -> str:
    """What to call *event* on screen. Falls back to the id, never to nothing.

    The id is an ugly but honest last resort: an event added to the enum and not
    to this table still appears in the Sound Scheme window, as
    ``some_new_event``, which somebody will notice and fix. Returning "" would
    make it a blank row, which nobody notices at all.
    """
    return LABELS.get(event, event)
