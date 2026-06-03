from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

FEATURE_STATE_ON = "on"
FEATURE_STATE_QUIET = "quiet"
FEATURE_STATE_OFF = "off"

PROFILE_ESSENTIAL = "essential"
PROFILE_WRITER = "writer"
PROFILE_DEVELOPER_POWER_TEXT = "developer_power_text"
PROFILE_ACCESSIBILITY_PROFESSIONAL = "accessibility_professional"
PROFILE_FULL_QUILL = "full_quill"


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    id: str
    name: str
    description: str = ""
    aliases: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    maturity: str = "stable"
    privacy: str = "local only"
    locked_on: bool = False
    locked_off: bool = False
    category: str = ""


@dataclass(slots=True)
class FeatureProfile:
    id: str
    name: str
    description: str
    states: dict[str, str] = field(default_factory=dict)


FEATURE_DEFINITIONS: dict[str, FeatureDefinition] = {
    "core.app": FeatureDefinition("core.app", "App Shell", category="core"),
    "core.editor": FeatureDefinition(
        "core.editor", "Editor Core", category="core", dependencies=("core.app",)
    ),
    "core.file": FeatureDefinition(
        "core.file", "File Commands", category="core", dependencies=("core.app",)
    ),
    "core.edit": FeatureDefinition(
        "core.edit", "Editing Commands", category="core", dependencies=("core.app",)
    ),
    "core.search": FeatureDefinition(
        "core.search", "Search", category="core", dependencies=("core.editor",)
    ),
    "core.search.regex": FeatureDefinition(
        "core.search.regex",
        "Regular Expression Search",
        aliases=("regex", "regular expression", "find regex"),
        dependencies=("core.search",),
        category="power text",
    ),
    "core.format": FeatureDefinition(
        "core.format", "Format Commands", category="core", dependencies=("core.editor",)
    ),
    "core.macros": FeatureDefinition(
        "core.macros", "Macros", category="power text", dependencies=("core.editor",)
    ),
    "core.links": FeatureDefinition(
        "core.links", "Link Tools", category="core", dependencies=("core.editor",)
    ),
    "core.navigate": FeatureDefinition(
        "core.navigate", "Navigation", category="core", dependencies=("core.editor",)
    ),
    "core.window": FeatureDefinition(
        "core.window", "Window Switching", category="core", dependencies=("core.app",)
    ),
    "core.view": FeatureDefinition(
        "core.view", "View Toggles", category="core", dependencies=("core.app",)
    ),
    "core.spellcheck": FeatureDefinition(
        "core.spellcheck", "Spell Check", category="core", dependencies=("core.editor",)
    ),
    "core.dictionary": FeatureDefinition(
        "core.dictionary",
        "Dictionary and Thesaurus",
        aliases=("dictionary", "thesaurus", "look up", "lexical"),
        description="Definitions, synonyms, and the Look Up surface (DICT-1/DICT-2).",
        category="core",
        dependencies=("core.editor",),
    ),
    "core.intellisense": FeatureDefinition(
        "core.intellisense",
        "Word Prediction",
        aliases=("intellisense", "autocomplete", "word prediction"),
        category="core",
        dependencies=("core.editor",),
    ),
    "core.read_aloud": FeatureDefinition(
        "core.read_aloud", "Read Aloud", category="accessibility", dependencies=("core.editor",)
    ),
    "core.dictation": FeatureDefinition(
        "core.dictation",
        "Dictation",
        description="Launches Windows dictation in the active editor.",
        category="accessibility",
        dependencies=("core.editor",),
    ),
    "core.voice_commands": FeatureDefinition(
        "core.voice_commands",
        "Voice Commands",
        description="Interprets Windows dictation phrases as Quill commands.",
        category="accessibility",
        dependencies=("core.dictation",),
    ),
    "core.bw_whisperer": FeatureDefinition(
        "core.bw_whisperer",
        "BITS Whisperer",
        description=(
            "Master flag for the BITS Whisperer transcription suite. Disabled for "
            "QUILL 1.0 (deferred to 2.0) until it reaches feature parity; gating "
            "this off hides the entire BITS Whisperer menu and its sub-features."
        ),
        category="accessibility",
        dependencies=("core.dictation",),
        locked_off=True,
    ),
    "core.bw_transcription": FeatureDefinition(
        "core.bw_transcription",
        "BITS Whisperer Transcription Rollout",
        description="Phased BITS Whisperer speech-model and dictation rollout surface.",
        category="accessibility",
        dependencies=("core.dictation", "core.bw_whisperer"),
    ),
    "core.bw_parakeet": FeatureDefinition(
        "core.bw_parakeet",
        "BITS Whisperer Parakeet Models",
        description="Controls visibility for phased Parakeet model options.",
        category="accessibility",
        dependencies=("core.bw_transcription",),
    ),
    "core.bw_providers": FeatureDefinition(
        "core.bw_providers",
        "BITS Whisperer Provider Onboarding",
        description="Guided provider planning and readiness checks for phased rollout.",
        category="accessibility",
        dependencies=("core.bw_transcription",),
    ),
    "core.bw_insights": FeatureDefinition(
        "core.bw_insights",
        "BITS Whisperer Rollout Insights",
        description="Readiness checks, capability matrix, and rollout diagnostics surfaces.",
        category="accessibility",
        dependencies=("core.bw_transcription",),
    ),
    "core.watch_folder": FeatureDefinition(
        "core.watch_folder",
        "Watch Folder Automation",
        description="Monitors a folder and opens newly detected supported files.",
        category="accessibility",
        dependencies=("core.file",),
    ),
    "core.analysis": FeatureDefinition(
        "core.analysis", "Document Analysis", category="core", dependencies=("core.editor",)
    ),
    "core.trust": FeatureDefinition(
        "core.trust", "Trust and Intake", category="safety", dependencies=("core.file",)
    ),
    "core.accessibility": FeatureDefinition(
        "core.accessibility",
        "Accessibility Tools",
        category="accessibility",
        dependencies=("core.editor",),
    ),
    "core.notifications": FeatureDefinition(
        "core.notifications",
        "Notifications",
        category="core",
        dependencies=("core.app",),
    ),
    "core.updates": FeatureDefinition(
        "core.updates", "Update Checks", category="safety", dependencies=("core.app",)
    ),
    "core.shell": FeatureDefinition(
        "core.shell", "Shell Integration", category="system", dependencies=("core.app",)
    ),
    "core.keymap": FeatureDefinition(
        "core.keymap", "Keymap Management", category="core", dependencies=("core.app",)
    ),
    "core.help": FeatureDefinition(
        "core.help", "Help and Guides", category="core", dependencies=("core.app",)
    ),
    "core.palette": FeatureDefinition(
        "core.palette", "Command Palette", category="core", dependencies=("core.app",)
    ),
    "core.profile": FeatureDefinition(
        "core.profile",
        "Feature Profiles",
        description="Profile switching, previews, and recovery.",
        dependencies=("core.app",),
        category="core",
        locked_on=True,
    ),
    "core.recovery": FeatureDefinition(
        "core.recovery",
        "Recovery Paths",
        description="Safe mode, restore prompts, and emergency reset.",
        dependencies=("core.app",),
        category="safety",
        locked_on=True,
    ),
    "core.ocr": FeatureDefinition(
        "core.ocr", "OCR", category="accessibility", dependencies=("core.file",)
    ),
    "future.character_inspector": FeatureDefinition(
        "future.character_inspector",
        "Character Inspector",
        aliases=("character inspector", "inspect character"),
        maturity="advanced",
        category="power text",
    ),
    "future.cleanup": FeatureDefinition(
        "future.cleanup",
        "Unicode Cleanup",
        aliases=("cleanup", "unicode cleanup"),
        maturity="advanced",
        category="power text",
    ),
    "future.regex_library": FeatureDefinition(
        "future.regex_library",
        "Regex Library",
        aliases=("regex library", "regex recipes"),
        maturity="advanced",
        category="power text",
    ),
    "future.ai": FeatureDefinition(
        "future.ai",
        "AI Assistance",
        aliases=("ai", "assistant"),
        maturity="advanced",
        privacy="network after confirmation",
        category="future",
    ),
}


FEATURE_ALIASES: dict[str, str] = {}
for feature in FEATURE_DEFINITIONS.values():
    FEATURE_ALIASES[feature.id.lower()] = feature.id
    FEATURE_ALIASES[feature.name.lower()] = feature.id
    for alias in feature.aliases:
        FEATURE_ALIASES[alias.lower()] = feature.id


PROFILE_DEFINITIONS: dict[str, FeatureProfile] = {
    PROFILE_ESSENTIAL: FeatureProfile(
        id=PROFILE_ESSENTIAL,
        name="Essential",
        description="Core editing, file, and navigation features.",
        states={
            "core.app": FEATURE_STATE_ON,
            "core.editor": FEATURE_STATE_ON,
            "core.file": FEATURE_STATE_ON,
            "core.edit": FEATURE_STATE_ON,
            "core.search": FEATURE_STATE_ON,
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_QUIET,
            "core.macros": FEATURE_STATE_OFF,
            "core.links": FEATURE_STATE_QUIET,
            "core.navigate": FEATURE_STATE_ON,
            "core.window": FEATURE_STATE_ON,
            "core.view": FEATURE_STATE_ON,
            "core.spellcheck": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_QUIET,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_QUIET,
            "core.analysis": FEATURE_STATE_QUIET,
            "core.trust": FEATURE_STATE_ON,
            "core.accessibility": FEATURE_STATE_ON,
            "core.notifications": FEATURE_STATE_ON,
            "core.updates": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_QUIET,
            "core.help": FEATURE_STATE_ON,
            "core.palette": FEATURE_STATE_ON,
            "core.profile": FEATURE_STATE_ON,
            "core.recovery": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_QUIET,
            "core.intellisense": FEATURE_STATE_OFF,
            "future.character_inspector": FEATURE_STATE_OFF,
            "future.cleanup": FEATURE_STATE_OFF,
            "future.regex_library": FEATURE_STATE_OFF,
            "future.ai": FEATURE_STATE_QUIET,
        },
    ),
    PROFILE_WRITER: FeatureProfile(
        id=PROFILE_WRITER,
        name="Writer",
        description="Writing, formatting, and cleanup with guided power features.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_ON,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_QUIET,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_QUIET,
            "core.ocr": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
            "future.ai": FEATURE_STATE_QUIET,
        },
    ),
    "reader_and_student": FeatureProfile(
        id="reader_and_student",
        name="Reader and Student",
        description="Reading, highlights, references, and light writing workflows.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_QUIET,
            "core.macros": FEATURE_STATE_OFF,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_ON,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_QUIET,
            "core.ocr": FEATURE_STATE_QUIET,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_OFF,
            "future.cleanup": FEATURE_STATE_OFF,
            "future.regex_library": FEATURE_STATE_OFF,
        },
    ),
    "office_and_admin": FeatureProfile(
        id="office_and_admin",
        name="Office and Admin",
        description="Reliable file work, sessions, cleanup, and printing.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_ON,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_QUIET,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_QUIET,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    PROFILE_DEVELOPER_POWER_TEXT: FeatureProfile(
        id=PROFILE_DEVELOPER_POWER_TEXT,
        name="Developer and Power Text",
        description="Regex, cleanup, inspection, and document analysis tools.",
        states={
            "core.search.regex": FEATURE_STATE_ON,
            "core.format": FEATURE_STATE_ON,
            "core.macros": FEATURE_STATE_ON,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_QUIET,
            "core.watch_folder": FEATURE_STATE_QUIET,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_ON,
            "core.keymap": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_ON,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    "low_vision": FeatureProfile(
        id="low_vision",
        name="Low Vision",
        description="Higher contrast, larger reading aids, and friendly inspection tools.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_ON,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_ON,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_QUIET,
            "core.ocr": FEATURE_STATE_ON,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    "braille_screen_reader_power_user": FeatureProfile(
        id="braille_screen_reader_power_user",
        name="Braille and Screen Reader Power User",
        description="Screen-reader-friendly navigation with advanced text tools surfaced calmly.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_QUIET,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_ON,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_ON,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    PROFILE_ACCESSIBILITY_PROFESSIONAL: FeatureProfile(
        id=PROFILE_ACCESSIBILITY_PROFESSIONAL,
        name="Accessibility Professional",
        description="Reading, inspection, trust, and accessibility diagnostics.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_QUIET,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_ON,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_ON,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    PROFILE_FULL_QUILL: FeatureProfile(
        id=PROFILE_FULL_QUILL,
        name="Full Quill",
        description="Everything visible, including advanced and experimental paths.",
        states={feature_id: FEATURE_STATE_ON for feature_id in FEATURE_DEFINITIONS},
    ),
}


DEFAULT_PROFILE_ID = PROFILE_ESSENTIAL


def features_path() -> Path:
    return app_data_dir() / "features.json"


QPF_EXTENSION = ".qpf"


def export_feature_profile_file(manager: FeatureManager, path: Path) -> None:
    """Write a manager's profile and feature-flag state to a ``.qpf`` file.

    The on-disk shape is the versioned mapping produced by
    :meth:`FeatureManager.export_profile_data`, so a power user or
    administrator can pre-tune which features are on before first run.
    """

    write_json_atomic(path, manager.export_profile_data())


def import_feature_profile_file(manager: FeatureManager, path: Path) -> list[str]:
    """Apply a ``.qpf`` profile file to ``manager`` and persist the result.

    Returns a list of human-readable warnings for anything that was ignored
    (for example an unknown profile id). Raises ``ValueError`` when the file is
    missing, empty, or not a supported profile document.
    """

    raw = read_json(path, default=None)
    return manager.import_profile_data(raw)


def reset_feature_profile_store() -> None:
    manager = FeatureManager.load()
    manager.reset_to_essential_profile()


def feature_for_command(command_id: str) -> str:
    explicit = {
        "app.command_palette": "core.palette",
        "app.preferences": "core.view",
        "app.exit": "core.app",
        "file.new": "core.file",
        "file.open": "core.file",
        "file.save": "core.file",
        "file.save_as": "core.file",
        "file.close_document": "core.file",
        "file.save_all": "core.file",
        "file.reload_from_disk": "core.file",
        "file.restore_backup": "core.recovery",
        "file.page_setup": "core.file",
        "file.print": "core.file",
        "file.save_as_plain_text": "core.file",
        "file.choose_encoding": "core.file",
        "file.toggle_line_endings": "core.file",
        "file.open_containing_folder": "core.file",
        "file.open_url": "core.file",
        "file.save_session": "core.recovery",
        "file.open_session": "core.recovery",
        "window.next_document": "core.window",
        "window.previous_document": "core.window",
        "view.send_to_tray": "core.view",
        "view.toggle_tab_control": "core.view",
        "view.toggle_soft_wrap": "core.view",
        "view.toggle_dark_mode": "core.view",
        "view.toggle_persistent_undo": "core.view",
        "view.toggle_spellcheck_as_you_type": "core.view",
        "view.toggle_intellisense_as_you_type": "core.view",
        "view.toggle_overwrite_mode": "core.view",
        "navigate.go_to_line": "core.navigate",
        "navigate.go_to_page": "core.navigate",
        "navigate.back_location": "core.navigate",
        "navigate.forward_location": "core.navigate",
        "navigate.next_heading": "core.navigate",
        "navigate.previous_heading": "core.navigate",
        "navigate.next_block": "core.navigate",
        "navigate.previous_block": "core.navigate",
        "navigate.outline_navigator": "core.navigate",
        "navigate.match_bracket": "core.navigate",
        "navigate.next_structure": "core.navigate",
        "navigate.previous_structure": "core.navigate",
        "navigate.next_region": "core.navigate",
        "navigate.previous_region": "core.navigate",
        "navigate.set_bookmark": "core.navigate",
        "navigate.go_to_bookmark": "core.navigate",
        "navigate.list_bookmarks": "core.navigate",
        "navigate.quick_nav": "core.navigate",
        "tools.word_count": "core.analysis",
        "tools.spell_check_dialog": "core.spellcheck",
        "tools.next_misspelling": "core.spellcheck",
        "tools.misspelling_list": "core.spellcheck",
        "tools.dictionary_status": "core.spellcheck",
        "tools.ocr_image": "core.ocr",
        "tools.read_aloud_start_pause": "core.read_aloud",
        "tools.read_aloud_stop": "core.read_aloud",
        "tools.read_aloud_voice": "core.read_aloud",
        "tools.read_aloud_settings": "core.read_aloud",
        "tools.dictation_toggle": "core.dictation",
        "tools.dictation_voice_commands_toggle": "core.voice_commands",
        "whisperer.model_manager": "core.bw_transcription",
        "whisperer.model_status": "core.bw_transcription",
        "whisperer.model_recommend": "core.bw_transcription",
        "whisperer.toggle_parakeet": "core.bw_parakeet",
        "whisperer.check_faster_whisper": "core.bw_transcription",
        "whisperer.provider_center": "core.bw_providers",
        "whisperer.provider_status": "core.bw_providers",
        "whisperer.provider_recommend": "core.bw_providers",
        "whisperer.provider_select": "core.bw_providers",
        "whisperer.readiness_check": "core.bw_insights",
        "whisperer.capability_matrix": "core.bw_insights",
        "whisperer.download_queue": "core.bw_insights",
        "tools.watch_folder_toggle": "core.watch_folder",
        "tools.watch_folder_settings": "core.watch_folder",
        "tools.watch_folder_status": "core.watch_folder",
        "tools.announcement_backend": "core.accessibility",
        "tools.announcement_trace_toggle": "core.accessibility",
        "tools.document_intake_report": "core.trust",
        "tools.review_extraction_quality": "core.trust",
        "tools.regex_helper": "core.search.regex",
        "tools.search_in_files": "core.search",
        "tools.replace_in_files": "core.search.regex",
        "tools.sticky_notes": "core.notes",
        "tools.sticky_note_capture": "core.notes",
        "tools.pandoc_wizard": "core.analysis",
        "tools.external_tools": "core.help",
        "tools.report_bad_extraction": "core.trust",
        "tools.shell_install": "core.shell",
        "tools.shell_remove": "core.shell",
        "tools.notifications": "core.notifications",
        "tools.check_updates": "core.updates",
        "tools.previous_misspelling": "core.spellcheck",
        "tools.validate_contrast": "core.accessibility",
        "tools.link_inventory": "core.accessibility",
        "tools.compare_with_file": "core.analysis",
        "tools.compare_open_documents": "core.analysis",
        "tools.compare_next_difference": "core.analysis",
        "tools.compare_previous_difference": "core.analysis",
        "tools.compare_announce_difference": "core.analysis",
        "tools.compare_difference_list": "core.analysis",
        "tools.compare_toggle_sync": "core.analysis",
        "tools.compare_options": "core.analysis",
        "tools.compare_create_summary": "core.analysis",
        "tools.compare_copy_current_difference": "core.analysis",
        "tools.compare_copy_all_differences": "core.analysis",
        "tools.start_macro_recording": "core.macros",
        "tools.stop_macro_recording": "core.macros",
        "tools.play_last_macro": "core.macros",
        "tools.manage_macros": "core.macros",
        "tools.export_keymap": "core.keymap",
        "tools.keymap_editor": "core.keymap",
        "tools.status_bar_settings": "core.view",
        "tools.share_export": "core.view",
        "tools.share_import": "core.view",
        "tools.import_keymap": "core.keymap",
        "tools.reset_keymap": "core.keymap",
        "tools.open_welcome_guide": "core.help",
        "tools.open_keyboard_reference": "core.help",
        "tools.cycle_autosave_interval": "core.view",
        "help.about_quill": "core.help",
        "help.save_diagnostics": "core.trust",
        "help.report_bug": "core.help",
        "help.open_logs_folder": "core.help",
        "help.open_diagnostics_folder": "core.help",
        "help.what_can_i_do_here": "core.help",
        "tools.keyboard_trap_snapshot": "core.accessibility",
        "tools.accessibility_audit": "core.accessibility",
        "tools.yaml_structure_editor": "core.format",
        "tools.glow_audit_document": "core.analysis",
        "tools.glow_audit_selection": "core.analysis",
        "tools.glow_fix_document": "core.analysis",
        "tools.glow_fix_selection": "core.analysis",
        "edit.undo": "core.edit",
        "edit.redo": "core.edit",
        "edit.copy_with_source": "core.edit",
        "edit.copy_selection_for_email": "core.edit",
        "edit.toggle_extend_selection_mode": "core.edit",
        "edit.find": "core.search",
        "edit.find_next": "core.search",
        "edit.find_previous": "core.search",
        "edit.find_all_matches": "core.search",
        "edit.word_prediction": "core.intellisense",
        "edit.replace": "core.search",
        "edit.replace_all": "core.search.regex",
        "edit.insert_link": "core.links",
        "edit.follow_link": "core.links",
        "edit.select_line": "core.edit",
        "edit.select_paragraph": "core.edit",
        "edit.set_mark": "core.edit",
        "edit.pop_mark": "core.edit",
        "edit.exchange_point_mark": "core.edit",
        "edit.list_marks": "core.edit",
        "edit.select_block": "core.edit",
        "edit.expand_selection": "core.edit",
        "edit.shrink_selection": "core.edit",
        "edit.selection_actions": "core.edit",
        "edit.select_to_start_of_line": "core.edit",
        "edit.select_to_end_of_line": "core.edit",
        "edit.select_to_start_of_document": "core.edit",
        "edit.select_to_end_of_document": "core.edit",
        "format.insert_html_tag": "core.format",
        "format.toggle_line_comment": "core.format",
        "format.toggle_block_comment": "core.format",
        "format.indent": "core.format",
        "format.outdent": "core.format",
        "format.insert_markdown_tag": "core.format",
        "format.bold": "core.format",
        "format.italic": "core.format",
        "format.heading_1": "core.format",
        "format.heading_2": "core.format",
        "format.heading_3": "core.format",
        "format.heading_4": "core.format",
        "format.heading_5": "core.format",
        "format.heading_6": "core.format",
        "format.decrease_heading_level": "core.format",
        "format.increase_heading_level": "core.format",
        "format.upper_case": "core.format",
        "format.lower_case": "core.format",
        "format.title_case": "core.format",
        "format.sentence_case": "core.format",
        "format.toggle_case": "core.format",
        "format.move_line_up": "core.format",
        "format.move_line_down": "core.format",
        "format.duplicate_line": "core.format",
        "format.delete_line": "core.format",
        "format.join_lines": "core.format",
        "format.insert_bullet_list": "core.format",
        "format.insert_numbered_list": "core.format",
        "format.insert_task_list": "core.format",
        "format.insert_code_block": "core.format",
        "format.insert_footnote": "core.format",
        "format.insert_table": "core.format",
        "edit.sort_lines_ascending": "core.format",
        "edit.sort_lines_descending": "core.format",
        "edit.reverse_lines": "core.format",
        "edit.remove_duplicate_lines": "core.format",
        "edit.trim_trailing_whitespace": "future.cleanup",
        "edit.normalize_whitespace": "future.cleanup",
        "edit.convert_indentation_to_spaces": "future.cleanup",
        "edit.convert_indentation_to_tabs": "future.cleanup",
        "tools.ai_assistant": "future.ai",
        "tools.ai_rewrite_selection": "future.ai",
        "tools.ai_summarize_selection": "future.ai",
        "tools.ai_continue_writing": "future.ai",
        "tools.ai_fix_grammar": "future.ai",
        "tools.writing_instructions": "future.ai",
        "tools.run_python": "future.ai",
    }
    if command_id in explicit:
        return explicit[command_id]
    if command_id.startswith("tools.read_aloud"):
        return "core.read_aloud"
    if command_id.startswith("tools.shell"):
        return "core.shell"
    if command_id.startswith("tools."):
        return "core.help"
    if command_id.startswith("format.") or command_id.startswith("edit.sort_"):
        return "core.format"
    if command_id.startswith("edit."):
        return "core.edit"
    if command_id.startswith("file."):
        return "core.file"
    if command_id.startswith("navigate."):
        return "core.navigate"
    if command_id.startswith("view."):
        return "core.view"
    if command_id.startswith("window."):
        return "core.window"
    if command_id.startswith("help."):
        return "core.help"
    return "core.app"


def find_feature(feature_name: str) -> FeatureDefinition | None:
    key = feature_name.strip().lower()
    feature_id = FEATURE_ALIASES.get(key)
    if feature_id is not None:
        return FEATURE_DEFINITIONS.get(feature_id)
    for feature in FEATURE_DEFINITIONS.values():
        if key in feature.id.lower() or key in feature.name.lower():
            return feature
    return None


def _normalize_states(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    states: dict[str, str] = {}
    for feature_id, state in raw.items():
        if not isinstance(feature_id, str) or not isinstance(state, str):
            continue
        normalized_state = state.strip().lower()
        if normalized_state not in {FEATURE_STATE_ON, FEATURE_STATE_QUIET, FEATURE_STATE_OFF}:
            continue
        if feature_id not in FEATURE_DEFINITIONS:
            continue
        states[feature_id] = normalized_state
    return states


@dataclass(slots=True)
class FeatureManager:
    active_profile_id: str = DEFAULT_PROFILE_ID
    previous_profile_id: str | None = None
    overrides: dict[str, str] = field(default_factory=dict)
    show_quiet_features: bool = True

    @classmethod
    def load(cls, *, persistent: bool = True) -> FeatureManager:
        if not persistent:
            return cls()
        raw = read_json(features_path(), default={})
        if not isinstance(raw, dict):
            return cls()
        active_profile_id = str(raw.get("active_profile_id", DEFAULT_PROFILE_ID))
        if active_profile_id not in PROFILE_DEFINITIONS:
            active_profile_id = DEFAULT_PROFILE_ID
        previous_profile_id = str(raw.get("previous_profile_id", "")) or None
        if previous_profile_id not in PROFILE_DEFINITIONS:
            previous_profile_id = None
        overrides = _normalize_states(raw.get("overrides"))
        show_quiet_features = bool(raw.get("show_quiet_features", True))
        return cls(
            active_profile_id=active_profile_id,
            previous_profile_id=previous_profile_id,
            overrides=overrides,
            show_quiet_features=show_quiet_features,
        )

    def save(self) -> None:
        write_json_atomic(
            features_path(),
            {
                "active_profile_id": self.active_profile_id,
                "previous_profile_id": self.previous_profile_id,
                "overrides": self.overrides,
                "show_quiet_features": self.show_quiet_features,
            },
            base=app_data_dir(),
        )

    @property
    def active_profile(self) -> FeatureProfile:
        return PROFILE_DEFINITIONS[self.active_profile_id]

    def dependency_chain(self, feature_id: str) -> tuple[str, ...]:
        dependency_ids: list[str] = []
        feature = FEATURE_DEFINITIONS.get(feature_id)
        if feature is None:
            return ()
        for dependency_id in feature.dependencies:
            dependency_ids.append(dependency_id)
            dependency_ids.extend(self.dependency_chain(dependency_id))
        seen: set[str] = set()
        ordered: list[str] = []
        for dependency_id in dependency_ids:
            if dependency_id in seen:
                continue
            seen.add(dependency_id)
            ordered.append(dependency_id)
        return tuple(ordered)

    def state_for(self, feature_id: str) -> str:
        definition = FEATURE_DEFINITIONS.get(feature_id)
        if definition is None:
            return FEATURE_STATE_OFF
        if definition.locked_on:
            return FEATURE_STATE_ON
        if definition.locked_off:
            return FEATURE_STATE_OFF
        if feature_id in self.overrides:
            return self.overrides[feature_id]
        return self.active_profile.states.get(feature_id, FEATURE_STATE_ON)

    def state_for_command(self, command_id: str) -> str:
        return self.state_for(feature_for_command(command_id))

    def is_enabled(self, feature_id: str) -> bool:
        if self.state_for(feature_id) == FEATURE_STATE_OFF:
            return False
        # FLAG-1: a feature whose dependency chain is not fully enabled stays
        # off, no matter how the dependency was turned off (profile or override).
        return all(
            self.state_for(dependency_id) != FEATURE_STATE_OFF
            for dependency_id in self.dependency_chain(feature_id)
        )

    def is_visible(self, feature_id: str) -> bool:
        if not self.is_enabled(feature_id):
            return False
        state = self.state_for(feature_id)
        return state == FEATURE_STATE_ON or (
            state == FEATURE_STATE_QUIET and self.show_quiet_features
        )

    def visible_commands(self, commands: list[Any]) -> list[Any]:
        return [command for command in commands if self.is_visible(command.feature_id)]

    def describe_feature(self, feature_name: str) -> str:
        feature = find_feature(feature_name)
        if feature is None:
            return f"No feature named {feature_name!r} was found."
        state = self.state_for(feature.id)
        profile = self.active_profile
        reason = "This feature is on."
        if state == FEATURE_STATE_QUIET:
            reason = "This feature is quiet in the current profile."
        elif state == FEATURE_STATE_OFF:
            reason = f"This feature is off in the {profile.name} profile."
        return (
            f"Feature: {feature.name}\n"
            f"ID: {feature.id}\n"
            f"State: {state}\n"
            f"Profile: {profile.name}\n"
            f"Maturity: {feature.maturity}\n"
            f"Privacy: {feature.privacy}\n"
            f"{reason}"
        )

    def profile_summary(self) -> str:
        profile = self.active_profile
        return f"Profile: {profile.name}\n\n{profile.description}"

    def available_profiles(self) -> list[FeatureProfile]:
        return [PROFILE_DEFINITIONS[key] for key in PROFILE_DEFINITIONS]

    def change_profile_preview(self, target_profile_id: str) -> str:
        target = PROFILE_DEFINITIONS[target_profile_id]
        current = self.active_profile
        if target.id == current.id:
            return (
                f"{target.name} is already active.\n\n"
                "No switch was made because this profile is already in use."
            )
        turn_on: list[str] = []
        turn_quiet: list[str] = []
        turn_off: list[str] = []
        for feature_id, definition in FEATURE_DEFINITIONS.items():
            current_state = self.state_for(feature_id)
            target_state = target.states.get(feature_id, FEATURE_STATE_ON)
            if definition.locked_on:
                continue
            if current_state == target_state:
                continue
            if target_state == FEATURE_STATE_ON:
                turn_on.append(definition.name)
            elif target_state == FEATURE_STATE_QUIET:
                turn_quiet.append(definition.name)
            else:
                turn_off.append(definition.name)
        return (
            f"Switching from {current.name} to {target.name} will turn on "
            f"{len(turn_on)} features, make {len(turn_quiet)} features quiet, "
            f"and turn off {len(turn_off)} features.\n\n"
            + self._format_feature_lines("Turned on", turn_on)
            + self._format_feature_lines("Made quiet", turn_quiet)
            + self._format_feature_lines("Turned off", turn_off)
        ).rstrip()

    def compare_profiles(self, source_profile_id: str, target_profile_id: str) -> str:
        if source_profile_id not in PROFILE_DEFINITIONS:
            raise KeyError(source_profile_id)
        if target_profile_id not in PROFILE_DEFINITIONS:
            raise KeyError(target_profile_id)
        source = PROFILE_DEFINITIONS[source_profile_id]
        target = PROFILE_DEFINITIONS[target_profile_id]
        if source.id == target.id:
            return f"{source.name} and {target.name} are the same profile."
        changes: list[str] = []
        for feature_id, definition in FEATURE_DEFINITIONS.items():
            source_state = source.states.get(feature_id, FEATURE_STATE_ON)
            target_state = target.states.get(feature_id, FEATURE_STATE_ON)
            if definition.locked_on or source_state == target_state:
                continue
            changes.append(f"- {definition.name}: {source_state} -> {target_state}")
        if not changes:
            return f"{source.name} and {target.name} have the same effective feature states."
        return f"Comparing {source.name} to {target.name}\n\n" + "\n".join(changes)

    def enable_feature(self, feature_id: str) -> list[str]:
        if feature_id not in FEATURE_DEFINITIONS:
            raise KeyError(feature_id)
        affected: list[str] = []
        for dependency_id in self.dependency_chain(feature_id):
            if self.state_for(dependency_id) == FEATURE_STATE_ON:
                continue
            self.overrides[dependency_id] = FEATURE_STATE_ON
            affected.append(dependency_id)
        if (
            not FEATURE_DEFINITIONS[feature_id].locked_on
            and self.state_for(feature_id) != FEATURE_STATE_ON
        ):
            self.overrides[feature_id] = FEATURE_STATE_ON
            affected.append(feature_id)
        self.save()
        return affected

    def disable_feature(self, feature_id: str) -> list[str]:
        if feature_id not in FEATURE_DEFINITIONS:
            raise KeyError(feature_id)
        definition = FEATURE_DEFINITIONS[feature_id]
        if definition.locked_on:
            return []
        affected: list[str] = []
        for dependent_id, dependent in FEATURE_DEFINITIONS.items():
            if feature_id not in dependent.dependencies:
                continue
            if self.state_for(dependent_id) == FEATURE_STATE_OFF:
                continue
            self.overrides[dependent_id] = FEATURE_STATE_OFF
            affected.append(dependent_id)
        self.overrides[feature_id] = FEATURE_STATE_OFF
        affected.append(feature_id)
        self.save()
        return affected

    def set_feature_enabled(self, feature_id: str, enabled: bool) -> list[str]:
        """Turn a single feature on or off, resolving dependencies.

        Returns the feature ids whose effective state changed (including the
        target feature). Enabling a feature also enables what it needs;
        disabling one also turns off the features that depend on it.
        """
        if enabled:
            return self.enable_feature(feature_id)
        return self.disable_feature(feature_id)

    def describe_feature_toggle(
        self, feature_id: str, enabled: bool, affected: Sequence[str]
    ) -> str:
        """Build a screen-reader announcement for a single feature toggle.

        ``affected`` is the list returned by :meth:`set_feature_enabled` and
        is expected to include ``feature_id`` itself when a change occurred.
        """
        definition = FEATURE_DEFINITIONS.get(feature_id)
        name = definition.name if definition is not None else feature_id
        if not affected:
            return f"{name} is already {'on' if enabled else 'off'}."
        others = [
            FEATURE_DEFINITIONS[other_id].name
            for other_id in affected
            if other_id != feature_id and other_id in FEATURE_DEFINITIONS
        ]
        verb = "Turned on" if enabled else "Turned off"
        if not others:
            return f"{verb} {name}."
        count = len(others)
        noun = "feature" if count == 1 else "features"
        relation = "it needs" if enabled else "that need it"
        return f"{verb} {name} (and {count} {noun} {relation}: {', '.join(others)})."

    def switch_profile(self, target_profile_id: str) -> None:
        if target_profile_id not in PROFILE_DEFINITIONS:
            raise KeyError(target_profile_id)
        self.previous_profile_id = self.active_profile_id
        self.active_profile_id = target_profile_id
        self.overrides = {}
        self.save()

    def undo_last_profile_change(self) -> bool:
        if self.previous_profile_id is None:
            return False
        target = self.previous_profile_id
        self.previous_profile_id = self.active_profile_id
        self.active_profile_id = target
        self.overrides = {}
        self.save()
        return True

    def reset_to_essential_profile(self) -> None:
        self.previous_profile_id = self.active_profile_id
        self.active_profile_id = DEFAULT_PROFILE_ID
        self.overrides = {}
        self.save()

    def export_profile_data(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "active_profile_id": self.active_profile_id,
            "previous_profile_id": self.previous_profile_id,
            "overrides": self.overrides,
            "show_quiet_features": self.show_quiet_features,
        }

    def import_profile_data(self, raw: object) -> list[str]:
        if not isinstance(raw, dict):
            raise ValueError("Profile import must be a JSON object.")
        if int(raw.get("schema_version", 0)) != 1:
            raise ValueError("Unsupported profile schema version.")
        warnings: list[str] = []
        active_profile_id = str(raw.get("active_profile_id", DEFAULT_PROFILE_ID))
        if active_profile_id not in PROFILE_DEFINITIONS:
            warnings.append(f"Ignored unknown profile {active_profile_id!r}.")
            active_profile_id = DEFAULT_PROFILE_ID
        previous_profile_id = str(raw.get("previous_profile_id", "")) or None
        if previous_profile_id not in PROFILE_DEFINITIONS:
            previous_profile_id = None
        overrides = _normalize_states(raw.get("overrides"))
        show_quiet_features = bool(raw.get("show_quiet_features", True))
        self.active_profile_id = active_profile_id
        self.previous_profile_id = previous_profile_id
        self.overrides = {
            feature_id: state
            for feature_id, state in overrides.items()
            if not FEATURE_DEFINITIONS[feature_id].locked_on
        }
        self.show_quiet_features = show_quiet_features
        self._enforce_dependencies()
        self.save()
        return warnings

    def _enforce_dependencies(self) -> None:
        for feature_id, state in list(self.overrides.items()):
            if state != FEATURE_STATE_ON:
                continue
            for dependency_id in self.dependency_chain(feature_id):
                if FEATURE_DEFINITIONS[dependency_id].locked_on:
                    continue
                self.overrides[dependency_id] = FEATURE_STATE_ON

    def health_report(self, commands: list[Any]) -> str:
        missing = [command.id for command in commands if not command.feature_id]
        disabled_required = [
            command.id
            for command in commands
            if self.state_for(command.feature_id) == FEATURE_STATE_OFF
            and FEATURE_DEFINITIONS[command.feature_id].locked_on
        ]
        lines = [
            "Feature profile health check",
            f"Active profile: {self.active_profile.name}",
            f"Visible feature definitions: {len(FEATURE_DEFINITIONS)}",
            f"Commands without a feature mapping: {len(missing)}",
            f"Locked features disabled: {len(disabled_required)}",
        ]
        if missing:
            lines.append("")
            lines.append("Unmapped commands:")
            lines.extend(f"- {command_id}" for command_id in missing)
        if disabled_required:
            lines.append("")
            lines.append("Locked commands turned off:")
            lines.extend(f"- {command_id}" for command_id in disabled_required)
        if not missing and not disabled_required:
            lines.append("")
            lines.append("No coverage problems found.")
        return "\n".join(lines)

    @staticmethod
    def _format_feature_lines(label: str, items: list[str]) -> str:
        if not items:
            return ""
        return f"{label}:\n" + "\n".join(f"- {item}" for item in items) + "\n\n"
