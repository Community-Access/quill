from __future__ import annotations

import html
import json
import os
import re
import sys
import threading
import time
import unicodedata
import webbrowser
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar
from urllib.error import URLError
from uuid import uuid4

try:
    import winsound as _winsound  # type: ignore[import]
except ImportError:  # pragma: no cover - non-Windows fallback
    _winsound = None  # type: ignore[assignment]

if TYPE_CHECKING:  # imports kept out of cold-start path
    from quill.core.epub import EpubBook, EpubChapter

from quill import __version__
from quill.core import thesaurus as thesaurus_engine
from quill.core.a11y_regions import (
    RegionTracker,
    build_accessibility_audit_report,
    render_snapshot,
)
from quill.core.accessibility_agent import AgentRunResult, summarize_plan
from quill.core.ai import Assistant
from quill.core.ai.agent import allowed_tools
from quill.core.autoformat import EM_DASH, is_dash_merge, smart_quote_for
from quill.core.autosave import autosave_document
from quill.core.backups import backup_document, list_backups
from quill.core.bookmarks import (  # N-13: keep the module as the supported home for these helpers
    bookmark_names,
    bookmark_position,
    set_bookmark,
)
from quill.core.browser_preview import (
    available_browser_options,
    browser_choice_label_for_value,
    browser_choice_value_for_label,
    guess_preview_kind,
    normalize_browser_choice,
    open_preview_url,
    preview_anchor_for_text,
    render_preview_body,
    render_preview_html,
)
from quill.core.bw_providers import (
    get_provider as bw_get_provider,
)
from quill.core.bw_providers import (
    list_providers as bw_list_providers,
)
from quill.core.bw_providers import (
    provider_mode_guidance as bw_provider_mode_guidance,
)
from quill.core.bw_providers import (
    provider_readiness as bw_provider_readiness,
)
from quill.core.bw_providers import (
    recommended_provider_id as bw_recommended_provider_id,
)
from quill.core.bw_speech import (
    download_model as bw_download_model,
)
from quill.core.bw_speech import (
    downloaded_model_ids as bw_downloaded_model_ids,
)
from quill.core.bw_speech import (
    faster_whisper_status,
)
from quill.core.bw_speech import (
    get_model as bw_get_model,
)
from quill.core.bw_speech import (
    has_disk_capacity as bw_has_disk_capacity,
)
from quill.core.bw_speech import (
    list_models as bw_list_models,
)
from quill.core.bw_speech import (
    machine_guidance as bw_machine_guidance,
)
from quill.core.bw_speech import (
    recommended_model_id as bw_recommended_model_id,
)
from quill.core.bw_speech import (
    remove_model as bw_remove_model,
)
from quill.core.commands import CommandRegistry
from quill.core.compliance import (
    build_dependency_notices,
    bundled_component_notices,
    render_bundled_component_table,
    render_dependency_notice_table,
    render_full_third_party_notices,
)
from quill.core.context_menu import (
    CMD_COPY,
    CMD_CUT,
    CMD_LOOK_UP,
    CMD_PASTE,
    CMD_SPELL_ADD,
    CMD_SPELL_IGNORE,
    CMD_SPELL_SUGGESTION,
    CMD_THESAURUS,
    CursorContext,
    build_context_menu,
)
from quill.core.contrast import render_contrast_report, validate_theme_contrast
from quill.core.custom_profiles import (
    CustomProfile,
    build_bare_bones_profile_data,
    build_parent_profile_data,
    generate_custom_profile_id,
    load_custom_profiles,
    save_custom_profiles,
)
from quill.core.dectalk_runtime import download_dectalk_runtime
from quill.core.diagnostics import (
    build_bug_report_payload,
    build_diagnostics_review_text,
    build_support_issue_url,
    collect_environment_info,
    record_diagnostic_event,
    write_diagnostics_bundle,
)
from quill.core.dictation import (
    DictationController,
    DictationSettings,
    DictationUnavailableError,
)
from quill.core.diffing import build_unified_diff
from quill.core.document import Document
from quill.core.external_change import (
    ExternalChangeWatcher,
    FileSnapshot,
    ReloadAction,
    decide_reload,
)
from quill.core.external_tools import (
    copyable_install_command,
    get_external_tool_status,
    get_external_tool_statuses,
)
from quill.core.features import (
    FEATURE_DEFINITIONS,
    PROFILE_DEFINITIONS,
    PROFILE_ESSENTIAL,
    FeatureManager,
    export_feature_profile_file,
    import_feature_profile_file,
)
from quill.core.file_search import (
    FileReplaceReport,
    FileSearchReport,
    render_replace_preview,
    render_replace_report,
    render_search_report,
    replace_files,
    search_files,
)
from quill.core.format_ops import (
    continue_markdown_list,
    indent_lines,
    outdent_lines,
    toggle_block_comment,
    toggle_line_comment,
)
from quill.core.glow import build_audit_report, build_fix_report, fix_text
from quill.core.glow_updates import (
    GlowUpdateCheck,
    apply_glow_update,
    check_for_glow_update,
)
from quill.core.guides import (
    build_keyboard_shortcut_html,
    build_welcome_guide,
)
from quill.core.heading_organizer import (
    HeadingBlock,
    apply_heading_organizer_edits,
    heading_context_at,
    parse_heading_blocks,
    validate_heading_sequence,
)
from quill.core.heading_styles import HeadingStyle, apply_heading_style
from quill.core.intake import (
    build_bad_extraction_package,
    build_context_help,
    build_extraction_quality_report,
    build_intake_report,
    build_intake_summary,
    build_source_reference,
)
from quill.core.intellisense import (
    IntellisenseContext,
    IntellisenseSuggestion,
)
from quill.core.ipc import drain_open_requests
from quill.core.keymap import (
    DEFAULT_KEYMAP,
    KEYBOARD_PACK_CUSTOM,
    KEYBOARD_PACK_DEFAULT,
    KQP_EXTENSION,
    build_keymap_for_pack,
    export_keyboard_pack,
    export_keymap,
    find_keymap_conflict,
    import_keyboard_pack,
    import_keymap,
    keyboard_pack_description,
    keyboard_pack_names,
    keyboard_pack_preview,
    load_keymap,
    reset_keymap,
    save_keymap,
)
from quill.core.language_profile import (
    PLAIN_PROFILE,
    LanguageProfile,
    all_profiles,
    get_profile_by_name,
    get_profile_for_path,
)
from quill.core.lexical import (
    build_lookup_items,
    default_service,
    render_lookup,
)
from quill.core.lexical_preload import start_lexical_preload
from quill.core.link_inventory import collect_link_inventory, render_link_inventory_report
from quill.core.links import build_link_text, find_link_at_cursor, infer_markup_kind
from quill.core.locations import LocationRing
from quill.core.macros import MacroManager
from quill.core.marks import MarkRing, NamedMarks, line_column_for_position
from quill.core.menu_customization import (
    MenuCustomization,
    load_menu_customization,
    save_menu_customization,
)
from quill.core.metrics import compute_document_stats
from quill.core.multi_press import MultiPressDispatcher
from quill.core.navigation import (
    next_block_start,
    next_heading_start,
    page_start_for_number,
    page_starts,
    parse_line_column,
    previous_block_start,
    previous_heading_start,
)
from quill.core.notifications import add_notification, clear_notifications, load_notifications
from quill.core.onboarding import (
    load_assistant_onboarding_complete,
    load_glow_onboarding_complete,
    load_onboarding_complete,
    load_speech_onboarding_complete,
    load_startup_wizard_prompt_suppressed,
    load_trust_consent_complete,
    load_watch_folder_onboarding_complete,
    mark_assistant_onboarding_complete,
    mark_glow_onboarding_complete,
    mark_onboarding_complete,
    mark_speech_onboarding_complete,
    mark_startup_wizard_prompt_suppressed,
    mark_trust_consent_complete,
    mark_watch_folder_onboarding_complete,
)
from quill.core.outline import OutlineEntry, extract_outline_entries
from quill.core.paths import app_data_dir, ensure_app_directories
from quill.core.quick_nav import (
    NavItem,
    build_nav_index,
    filter_nav_items,
    include_nav_items,
    nav_category,
    nav_item_display,
    nav_type_summary,
)
from quill.core.read_aloud import (
    ReadAloudController,
    ReadAloudUnavailableError,
    discover_dectalk_executable,
    discover_espeak_executable,
    discover_openvoice_executable,
    discover_piper_executable,
    list_dectalk_voices,
    list_espeak_english_voices,
    list_kokoro_voices,
    list_openvoice_english_voices,
    list_piper_voices,
    list_voices,
    synthesize_to_file_with_dectalk,
    synthesize_to_file_with_pyttsx3,
    synthesize_with_espeak,
    synthesize_with_kokoro,
    synthesize_with_openvoice,
    synthesize_with_piper,
)
from quill.core.read_aloud import (
    VoiceOption as ReadAloudVoiceOption,
)
from quill.core.recent import add_recent_file, clear_recent_files, load_recent_files
from quill.core.recovery import (
    begin_session,
    mark_clean_exit,
    mark_recovery_offer_dismissed,
    mark_recovery_offer_recovered,
    read_recovery_snapshot,
)
from quill.core.search import SearchOptions, SearchPatternError, find_matches, replace_all
from quill.core.search_history import add_search_term, load_search_history
from quill.core.selection import (
    line_span,
    paragraph_span,
)
from quill.core.sessions import (
    load_recent_sessions,
)
from quill.core.settings import Settings, load_settings, save_settings
from quill.core.share_package import (
    KIND_BACKUP,
    KIND_PROFILE,
    PackageError,
    extension_for_kind,
    package_summary,
)
from quill.core.snippets import (
    ExpansionResult as SnippetExpansionResult,
)
from quill.core.snippets import (
    Snippet,
    SnippetLibrary,
    extract_placeholders,
    find_snippet_by_trigger,
    load_snippet_library,
    merge_starter_pack,
    render_snippet,
    save_snippet_library,
    search_snippets,
    starter_pack_names,
)
from quill.core.spellcheck import (
    Misspelling,
    add_word_to_scope,
    list_misspellings,
    load_combined_dictionary,
    load_scope_dictionary,
    misspelling_at_position,
    suggest_words,
)
from quill.core.spellcheck import (
    backend_info as spellcheck_backend_info,
)
from quill.core.spellcheck import (
    next_misspelling as find_next_misspelling,
)
from quill.core.spellcheck import (
    previous_misspelling as find_previous_misspelling,
)
from quill.core.sticky_notes import save_sticky_note
from quill.core.structure_nav import (
    find_matching_bracket,
    next_structure_position,
    previous_structure_position,
)
from quill.core.tagging import (
    HTML_TAG_CHOICES,
    MARKDOWN_TAG_CHOICES,
    InsertionResult,
    build_html_code_block,
    build_html_insertion,
    build_html_table,
    build_markdown_code_block,
    build_markdown_insertion,
    build_markdown_table,
    parse_attribute_pairs,
    search_html_tag_choices,
    search_markdown_tag_choices,
)
from quill.core.token_nav import classify_token, next_token_position, prev_token_position
from quill.core.transforms import to_lower, to_sentence_case, to_title, to_toggle_case, to_upper
from quill.core.trust import is_trusted_location, load_trusted_locations, save_trusted_locations
from quill.core.undo_store import load_undo_history, save_undo_history
from quill.core.updates import (
    GitHubRelease,
    UpdateManifest,
    download_release_asset,
    fetch_latest_release,
    fetch_releases,
    fetch_update_manifest,
    find_release,
    is_newer_version,
    select_latest,
)
from quill.core.url_ops import format_content_length
from quill.core.voice_commands import (
    build_voice_command_aliases,
    resolve_voice_command,
    split_text_delta,
)
from quill.core.watch_actions import WatchActionOutcome, WatchItem
from quill.core.watch_profiles import (
    POST_DELETE,
    POST_LEAVE,
    POST_MOVE,
    SCHED_ALWAYS,
    SCHED_QUIET,
    SCHED_WINDOW,
    WatchProfile,
    iter_matching_files,
)
from quill.core.watch_queue import (
    STATE_DONE,
    STATE_FAILED,
    STATE_PROCESSING,
    STATE_QUEUED,
    STATE_SKIPPED,
    QueueItem,
)
from quill.core.watch_service import WatchService
from quill.core.yaml_structure import (
    YamlNode,
    YamlNodeKind,
    add_yaml_child,
    add_yaml_sibling,
    delete_yaml_node,
    extract_yaml_nodes,
    rename_yaml_node,
)
from quill.io.export import format_label_for_path, write_document_as, write_plain_text_document
from quill.io.open_read import OFFICE_STREAM_SUFFIXES as _OFFICE_STREAM_SUFFIXES
from quill.io.open_read import read_open_document
from quill.io.pandoc import (
    PandocConversionError,
    PandocUnavailableError,
    convert_document_with_pandoc,
)
from quill.io.text import read_text_document
from quill.platform.windows.high_contrast import is_high_contrast_enabled
from quill.platform.windows.prism_bridge import AnnouncementEngine
from quill.platform.windows.shell_integration import (
    apply_shell_verb_settings,
    build_shell_integration_plan,
    install_shell_integration,
    launcher_command,
    remove_context_menu,
    remove_shell_integration,
)
from quill.platform.windows.sr_announce import (
    announce,
    enable_transcript_capture,
    set_announce_handler,
    set_transcript_path,
)
from quill.platform.windows.sr_detect import detect_screen_reader
from quill.stability.memory_watch import should_trace_memory, start_memory_tracing
from quill.stability.ui_responsiveness import mark_wx_main_thread
from quill.stability.wx_heartbeat import HeartbeatState, WxHeartbeatTimer, WxHeartbeatWatchdog
from quill.ui.ai_model_panel import AIModelDialog
from quill.ui.assistant_panel import AskQuillChatDialog
from quill.ui.assistant_tools import (
    AccessibilityAgentDialog,
    AgentCenterDialog,
    AssistantConnectionDialog,
    PromptStudioDialog,
    RunPythonDialog,
    WritingAssistantDialog,
)
from quill.ui.context_help import ContextHelpMixin
from quill.ui.csv_grid import CsvGridSurface
from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control, show_modal_dialog
from quill.ui.editor_surface import PLAIN, RICH, surface_kind
from quill.ui.html_paste_cleaner import analyze_paste
from quill.ui.main_frame_abbreviations import AbbreviationsMixin
from quill.ui.main_frame_ai_actions import AiActionsMixin
from quill.ui.main_frame_browse import BrowseModeMixin
from quill.ui.main_frame_copy_tray import CopyTrayMixin
from quill.ui.main_frame_devtools import DevToolsMixin
from quill.ui.main_frame_github import GitHubRemoteMixin
from quill.ui.main_frame_image import ImageCaptureMixin
from quill.ui.main_frame_intellisense import IntellisensePopupMixin
from quill.ui.main_frame_line_commands import LineCommandsMixin
from quill.ui.main_frame_menu import MenuBuilderMixin
from quill.ui.main_frame_notebook import NotebookUIMixin
from quill.ui.main_frame_power_tools import PowerToolsActionsMixin
from quill.ui.main_frame_power_tools_menu import PowerToolsMenuMixin
from quill.ui.main_frame_profile_picker import ProfilePickerMixin
from quill.ui.main_frame_quill_key import QuillKeyMixin
from quill.ui.main_frame_quillins import QuillinsMenuMixin
from quill.ui.main_frame_selection import SelectionMarksMixin
from quill.ui.main_frame_sessions import SessionsMixin
from quill.ui.main_frame_ssh import SshEditingMixin
from quill.ui.main_frame_statusbar import StatusBarMixin, _StatusBarCell
from quill.ui.notebook_panel import NotebookEntriesPanel
from quill.ui.palette import CommandPaletteDialog
from quill.ui.rich_text_surface import RichTextSurface
from quill.ui.session_browser import SessionBrowserDialog
from quill.ui.share_dialogs import (
    apply_import,
    build_export_document,
    gather_export_offers,
    importable_sections,
    read_import,
    write_export,
)
from quill.ui.sticky_notes import StickyNoteEditorDialog, StickyNotesVaultDialog
from quill.ui.style_panel import TrainStyleDialog
from quill.ui.word_view import WordDocumentSurface


def _wcag_contrast_ratio(fr: int, fg: int, fb: int, br: int, bg: int, bb: int) -> float:
    """Return the WCAG 2.1 contrast ratio between two sRGB colours.

    Arguments are R/G/B channel values in [0, 255].  The returned value is in
    the range [1.0, 21.0] where 21.0 is black-on-white.
    """

    def _relative_luminance(r: int, g: int, b: int) -> float:
        def _channel(c: int) -> float:
            s = c / 255.0
            return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

        return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)

    l1 = _relative_luminance(fr, fg, fb)
    l2 = _relative_luminance(br, bg, bb)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _word_feature_enabled() -> bool:
    """Structured Word (.docx) view is NOT enabled on this branch.

    Experimental and not ready for users: hard-disabled,
    so Word files always open in the normal text editor and there is no env-var
    override. Developed on the feature/structured-surfaces branch."""
    return False


def _csv_feature_enabled() -> bool:
    """CSV grid view is NOT enabled on this branch.

    Experimental and not ready for users: hard-disabled,
    so CSV files always open in the normal text editor and there is no env-var
    override. Developed on the feature/structured-surfaces branch."""
    return False


#: Stable key and factory label for each top-level menu, in default order.
#: The Menu Editor and the menu-build transform pass share this list so a person
#: can reorder, hide, and rename top-level menus without touching item code.
_TOP_MENU_DEFS: tuple[tuple[str, str], ...] = (
    ("file", "&File"),
    ("edit", "&Edit"),
    ("view", "&View"),
    ("insert", "&Insert"),
    ("format", "F&ormat"),
    ("navigate", "&Navigate"),
    ("search", "&Search"),
    ("tools", "&Tools"),
    ("window", "&Window"),
    ("help", "&Help"),
)


def _normalize_menu_label(label: str) -> str:
    """Return a menu label without mnemonics or surrounding whitespace."""
    return label.replace("&", "").strip()


@dataclass(slots=True)
class _DocumentTab:
    panel: object
    editor: object
    document: Document
    splitter: object = None
    preview: object = None
    source_label: str = ""
    read_only_remote: bool = False


@dataclass(slots=True)
class _NavigatorNode:
    label: str
    preview: str
    payload: object
    action_label: str
    children: list[_NavigatorNode]


@dataclass(frozen=True, slots=True)
class _EpubNavigatorTarget:
    chapter_index: int
    heading_index: int | None = None


@dataclass(slots=True)
class _BrowserPreviewSession:
    tab_index: int
    preview_path: Path
    browser_choice: str
    title: str


@dataclass(slots=True)
class _ListManagerItem:
    kind: str
    text: str
    level: int
    bullet: str = "-"
    checked: bool = False


@dataclass(slots=True)
class _ListManagerState:
    start: int
    end: int
    trailing_newline: bool
    base_indent: str
    items: list[_ListManagerItem]


@dataclass(slots=True)
class _CompareLineBlock:
    document_name: str
    start_line: int | None
    end_line: int | None
    text: list[str]


@dataclass(slots=True)
class _CompareDifferenceGroup:
    index: int
    kind: str
    blocks: list[_CompareLineBlock]


@dataclass(slots=True)
class _CompareSession:
    source_documents: list[tuple[str, str]]
    groups: list[_CompareDifferenceGroup]
    current_index: int = 0
    synchronized_navigation: bool = True


@dataclass(slots=True)
class _FileSearchRequest:
    root: Path
    pattern: str
    query: str
    replacement: str | None
    options: SearchOptions
    output_mode: str
    preview_before_replace: bool


class _IntellisensePopup:
    def __init__(self, wx: object, parent: object) -> None:
        self._wx = wx
        self._accept_callback = None
        self._dismiss_callback = None
        self.frame = wx.Frame(
            parent,
            title="Word Prediction",
            style=wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP | wx.BORDER_SIMPLE,
        )
        self.frame.SetSize((420, 220))
        root = wx.BoxSizer(wx.VERTICAL)
        self.status = wx.StaticText(self.frame, label="")
        root.Add(self.status, 0, wx.EXPAND | wx.ALL, 6)
        self.listbox = wx.ListBox(self.frame)
        # Accessible name so a screen reader announces the list's purpose if
        # focus ever lands here directly.
        self.listbox.SetName("Word prediction suggestions")
        root.Add(self.listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.frame.SetSizer(root)
        self.suggestions: list[IntellisenseSuggestion] = []
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._on_accept)
        # The intended flow keeps focus in the editor and drives this list from
        # the editor's char hook. But focus can still land in the listbox (Tab,
        # mouse, or screen-reader navigation into this floating window), and a
        # bare wx.ListBox has no way out — Escape/Tab/Enter would do nothing,
        # trapping the user. Handle those keys here too so the list is never a
        # dead end regardless of where focus is.
        self.listbox.Bind(wx.EVT_CHAR_HOOK, self._on_listbox_key)

    def set_accept_callback(self, callback: object) -> None:
        self._accept_callback = callback

    def set_dismiss_callback(self, callback: object) -> None:
        self._dismiss_callback = callback

    def _on_close(self, event: object) -> None:
        self.frame.Hide()
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def _on_accept(self, _event: object) -> None:
        if callable(self._accept_callback):
            self._accept_callback()

    def _dismiss(self) -> None:
        if callable(self._dismiss_callback):
            self._dismiss_callback()

    def _on_listbox_key(self, event: object) -> None:
        """Keep the listbox from becoming a keyboard trap when it has focus.

        Escape cancels; Enter and Tab accept the highlighted suggestion. All
        three return focus to the editor (via the accept/dismiss callbacks),
        mirroring the editor-focused behaviour. Arrow keys fall through to the
        native listbox so the screen reader announces each selection."""
        wx = self._wx
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_ESCAPE:
            self._dismiss()
            return
        if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB):
            if callable(self._accept_callback):
                self._accept_callback()
            else:
                self._dismiss()
            return
        event.Skip()

    def update(self, suggestions: list[IntellisenseSuggestion], status: str) -> None:
        self.suggestions = list(suggestions)
        labels = [item.label for item in suggestions]
        self.listbox.Set(labels)
        if labels:
            self.listbox.SetSelection(0)
        self.status.SetLabel(status)

    def show(self, position: tuple[int, int]) -> None:
        self.frame.SetPosition(position)
        show_without_activating = getattr(self.frame, "ShowWithoutActivating", None)
        if callable(show_without_activating):
            show_without_activating()
        else:
            self.frame.Show(True)
        self.frame.Raise()

    def hide(self) -> None:
        self.frame.Hide()

    def is_visible(self) -> bool:
        return bool(self.frame.IsShown())

    def selection_index(self) -> int:
        return self.listbox.GetSelection()

    def set_selection(self, index: int) -> None:
        if not self.suggestions:
            return
        index = max(0, min(index, len(self.suggestions) - 1))
        self.listbox.SetSelection(index)

    def selected_suggestion(self) -> IntellisenseSuggestion | None:
        index = self.listbox.GetSelection()
        if index < 0 or index >= len(self.suggestions):
            return None
        return self.suggestions[index]


class MainFrame(
    AbbreviationsMixin,
    AiActionsMixin,
    ImageCaptureMixin,
    BrowseModeMixin,
    MenuBuilderMixin,
    NotebookUIMixin,
    QuillKeyMixin,
    SelectionMarksMixin,
    SessionsMixin,
    StatusBarMixin,
    IntellisensePopupMixin,
    LineCommandsMixin,
    CopyTrayMixin,
    ProfilePickerMixin,
    SshEditingMixin,
    GitHubRemoteMixin,
    DevToolsMixin,
    PowerToolsActionsMixin,
    PowerToolsMenuMixin,
    QuillinsMenuMixin,
    ContextHelpMixin,
):
    _ANNOUNCEMENT_BACKEND_LABELS: dict[str, str] = {
        "auto": "Automatic (use Prism when available)",
        "prism": "Prism",
        "status_only": "Status Bar Only",
    }
    _STATUS_BAR_LABELS: dict[str, str] = {
        "message": "Status Message",
        "line_column": "Line / Column",
        "word_count": "Word Count",
        "mode": "Insert / Overwrite",
        "selection": "Selection Length",
        "encoding": "Encoding",
        "line_endings": "Line Endings",
        "spell_check": "Spell Check",
        "background_tasks": "Background Tasks",
        "notifications": "Notifications",
        "read_aloud": "Read Aloud",
        "autosave": "Autosave",
        "search_term": "Search Term",
        "file_path": "File Path",
        "quill_key_mode": "QUILL Key",
        "extend_mode": "Extend Mode",
        "abbreviations": "Abbreviations",
        "copy_tray_slots": "Copy Tray",
        "language_profile": "Language",
        "sr_name": "Screen Reader",
        "suggestion": "Suggested Action",
        "notebook_goal": "Notebook Goal",
    }
    _STATUS_BAR_WIDTHS: dict[str, int] = {
        "message": -1,
        "line_column": 140,
        "word_count": 140,
        "mode": 110,
        "selection": 110,
        "encoding": 120,
        "line_endings": 140,
        "spell_check": 120,
        "background_tasks": 150,
        "notifications": 140,
        "read_aloud": 140,
        "autosave": 130,
        "search_term": 160,
        "file_path": 260,
        "quill_key_mode": 130,
        "extend_mode": 110,
        "abbreviations": 120,
        "copy_tray_slots": 110,
        "language_profile": 130,
        "sr_name": 160,
        "suggestion": 220,
        "notebook_goal": 200,
    }
    _STATUS_BAR_FEATURES: dict[str, str] = {
        "message": "core.app",
        "line_column": "core.editor",
        "word_count": "core.analysis",
        "mode": "core.editor",
        "selection": "core.editor",
        "encoding": "core.file",
        "line_endings": "core.file",
        "spell_check": "core.spellcheck",
        "background_tasks": "core.notifications",
        "notifications": "core.notifications",
        "read_aloud": "core.read_aloud",
        "autosave": "core.recovery",
        "search_term": "core.search",
        "file_path": "core.file",
        "quill_key_mode": "core.navigate",
        "extend_mode": "core.edit",
        "abbreviations": "core.edit",
        "copy_tray_slots": "core.edit",
        "language_profile": "core.navigate",
        "sr_name": "core.app",
        "suggestion": "core.app",
        "notebook_goal": "core.notebook",
    }
    _MACRO_CONTROL_COMMANDS: frozenset[str] = frozenset({
        "tools.start_macro_recording",
        "tools.stop_macro_recording",
        "tools.play_last_macro",
        "tools.manage_macros",
    })
    _EXTEND_SELECTION_ACTION_EXEMPT_COMMANDS: set[str] = {
        "edit.toggle_extend_selection_mode",
        "edit.start_selection",
        "edit.complete_selection",
        "edit.reselect",
        "edit.go_to_start_of_selection",
        "edit.copy_all",
        "edit.unselect_all",
        "edit.say_selected",
        "edit.read_all",
        "edit.find",
        "edit.find_next",
        "edit.find_previous",
        "edit.find_all_matches",
        "edit.set_mark",
        "edit.pop_mark",
        "edit.list_marks",
        "edit.exchange_point_mark",
        "edit.set_named_mark",
        "edit.jump_to_named_mark",
        "edit.open_review_buffer",
        "edit.follow_link",
    }
    _EXTEND_SELECTION_ACTION_COMMAND_PREFIXES: tuple[str, ...] = (
        "edit.",
        "format.",
    )
    _EXTEND_SELECTION_ACTION_COMMANDS: set[str] = {
        "tools.glow_fix_document",
        "tools.glow_fix_selection",
    }

    def __init__(self, safe_mode: bool = False) -> None:
        import wx
        import wx.adv

        self._wx = wx
        self._safe_mode = safe_mode
        # Build a wx.Accessible subclass that replaces each layout container's
        # built-in accessible so screen readers encounter a nameless
        # ROLE_SYSTEM_WINDOW and skip it in the ancestor context chain (#170).
        # wxSplitterWindow and wxPanel install their *own* wx.Accessible in
        # their constructors, so SetName() alone cannot override what the SR
        # reads.  SetAccessible() called after construction replaces theirs.
        try:
            _acc_ok = wx.ACC_OK
            _role_win = wx.ROLE_SYSTEM_WINDOW

            class _SilentLayout(wx.Accessible):  # type: ignore[misc]
                def GetName(self, childId: int) -> tuple[int, str]:
                    return _acc_ok, ""

                def GetRole(self, childId: int) -> tuple[int, int]:
                    return _acc_ok, _role_win

            self._silent_layout_cls: type | None = _SilentLayout
        except Exception:
            self._silent_layout_cls = None
        self.document = Document()
        ensure_app_directories()
        self._first_run_profile_prompt = not safe_mode and not load_onboarding_complete()
        self._first_run_trust_consent_prompt = not safe_mode and not load_trust_consent_complete()
        self.features = FeatureManager.load(persistent=not safe_mode)
        self.macros = MacroManager.load(persistent=not safe_mode)
        self.settings = load_settings()
        self._first_run_assistant_prompt = (
            not safe_mode
            and not load_assistant_onboarding_complete()
            and not getattr(self.settings, "assistant_enabled", False)
        )
        self._first_run_speech_prompt = not safe_mode and not load_speech_onboarding_complete()
        self._first_run_glow_prompt = not safe_mode and not load_glow_onboarding_complete()
        self._first_run_watch_folder_prompt = (
            not safe_mode and not load_watch_folder_onboarding_complete()
        )
        # Seed with Documents so the first-ever file dialog doesn't open in
        # the install directory.  Updated to the last-used parent after each
        # successful open or save-as (#168).
        self._last_file_dir: str = ""
        if safe_mode:
            self.settings.theme = "system"
            self.settings.tray_enabled = False
            self.settings.persistent_undo = False
            self.settings.spellcheck_as_you_type = False
            self.settings.start_with_no_document_open = False
            self.settings.announcement_backend = "status_only"
            self.settings.announcement_trace_enabled = False
            self.settings.assistant_enabled = False
        try:
            from quill.core.i18n import init_locale

            lang = getattr(self.settings, "language", None) or None
            self._active_language = init_locale(lang)
        except Exception:
            self._active_language = "en"
        self.keymap = dict(DEFAULT_KEYMAP) if safe_mode else load_keymap()
        self.recent_files = [] if safe_mode else load_recent_files()
        self._trusted_locations = set() if safe_mode else load_trusted_locations()
        self.session_id = str(uuid4())
        self._recovery_offers = [] if safe_mode else begin_session(self.session_id)
        self._last_autosave_at: datetime | None = None
        self._autosave_interval = timedelta(
            seconds=int(getattr(self.settings, "autosave_interval_seconds", 30))
        )
        self._last_find_query = ""
        self._last_search_options = SearchOptions()
        self._last_match: tuple[int, int] | None = None
        self._search_history = [] if safe_mode else load_search_history()
        self._searchable_picker_queries: dict[str, str] = {}
        self._browse_navigation_cache: dict[str, object] | None = None
        self._browse_prewarm_call_later = None
        self._browse_prewarm_request_force = False
        self._browse_prewarm_large_document_threshold = 20_000
        self._browse_prewarm_delay_ms = 250
        self._browse_cache_build_generation = 0
        self._browse_cache_build_thread: threading.Thread | None = None
        self._quill_key_mode_active = False
        self._quill_key_prefix_pending = False
        self._quill_key_prefix_started_at = 0.0
        self._last_quill_action: str | None = None
        self._quill_key_mode_started_at = 0.0
        self._quill_key_mode_timeout_seconds = 1.5
        self._quill_key_mode_sticky = False
        self._notifications = [] if safe_mode else load_notifications()
        self._mark_ring = MarkRing()
        self._named_marks = NamedMarks()
        self._location_ring = LocationRing()
        self._region_tracker = RegionTracker()
        # The F6 / Shift+F6 region rotation is computed live (see
        # _current_focus_region_labels) because the side preview pane only
        # exists while it is split open. _active_region is the tracked label so
        # we always know where to resume cycling from.
        self._active_region = "Editor"
        self._persistent_undo_history: list[str] = [self.document.text]
        self._persistent_undo_index = 0
        self._suspend_persistent_undo = False
        self._persistent_undo_dirty = False
        self._last_persistent_undo_write_at: datetime | None = None
        self._spell_dictionary_cache: tuple[tuple[Path | None, Path], set[str]] | None = None
        self._last_live_misspelling_feedback: tuple[str, int, int] | None = None
        self._last_live_misspelling_feedback_at: float = 0.0
        self._extend_selection_mode = False
        self._extend_selection_anchor: int | None = None
        self._selection_anchor: int | None = None
        self._last_selection: tuple[int, int] | None = None
        self._epub_book: EpubBook | None = None
        self._browser_preview_session: _BrowserPreviewSession | None = None
        self._bookmarks: dict[str, int] = {}
        self._tray_icon: object | None = None
        self._is_exiting = False
        self._ipc_timer: object | None = None
        self._status_message = "Ready"
        self._background_task_count = 0
        self._background_tasks: list[dict[str, object]] = []
        self._background_task_sequence = 0
        self._status_page_live_updates = False
        self._status_page_refresh_ms = 2000
        self._status_page_timer: object | None = None
        self._status_page_last_announce_at = 0.0
        self._status_page_last_announce_signature = ""
        self._bw_download_status: dict[str, dict[str, object]] = {}
        self._last_intake_report = ""
        self._startup_deferred_ran = False
        self._compare_session: _CompareSession | None = None
        self._compare_ignore_trailing_spaces = True
        self._compare_ignore_line_endings = True
        self._empty_workspace_active = False
        self._announcement_engine = AnnouncementEngine(self.settings.announcement_backend)
        self._announcement_error_reported = ""
        self._read_aloud = ReadAloudController()
        self._dictation = DictationController()
        self._lexical_service = default_service(include_online=True)
        self._external_change_watcher: ExternalChangeWatcher | None = None
        self._external_change_timer: object | None = None
        self._watch_service = WatchService(
            data_dir=app_data_dir(),
            feature_enabled=self._feature_enabled,
            on_open=lambda path: self._wx.CallAfter(self._on_watch_file_opened, path),
            on_convert=self._watch_convert_file,
            on_run_macro=self._watch_run_macro,
            on_ai=self._watch_run_ai,
            queue_listener=lambda event, item: self._wx.CallAfter(
                self._on_watch_queue_event,
                event,
                item,
            ),
        )
        self._watch_queue_monitor: object | None = None
        self._watch_queue_listbox: object | None = None
        self._voice_command_scan_timer: threading.Timer | None = None
        self._voice_command_baseline_text = ""
        self._voice_command_aliases: dict[str, str] = {}
        self._voice_command_guard = False
        self._overwrite_mode = False
        self._insert_key_down = False
        self._print_data = wx.PrintData()
        self._page_setup_data = wx.PageSetupDialogData(self._print_data)
        self._snippet_library = (
            load_snippet_library() if not safe_mode else SnippetLibrary(version=1, snippets=[])
        )
        self._snippet_expansion_guard = False
        self._init_abbreviations()
        self._intellisense_popup: _IntellisensePopup | None = None
        self._intellisense_context: IntellisenseContext | None = None
        self._intellisense_fragment_text = ""
        self._intellisense_suggestions: list[IntellisenseSuggestion] = []
        self._intellisense_guard = False
        self._sticky_note_hotkey_id = wx.NewIdRef()
        self.commands = CommandRegistry()
        self.commands.set_run_listener(self._on_command_run)
        self._recent_menu_ids: dict[int, Path] = {}
        self._recent_session_menu_ids: dict[int, Path] = {}
        self._session_menu_ids: dict[int, int] = {}
        self._menu_open_depth = 0
        self._pending_menu_refresh = False
        self._recent_sessions = [] if safe_mode else load_recent_sessions()

        # Title starts as "Quill" (not "Untitled - Quill") so screen readers
        # that see the Win32 HWND before Show() is called don't announce
        # "Untitled" combined with any transient status-bar text. _refresh_title()
        # sets the real document-name title as soon as the editor is ready.
        self.frame = wx.Frame(None, title="Quill", size=(1000, 700))
        self._intellisense_popup = _IntellisensePopup(wx, self.frame)
        self._intellisense_popup.set_accept_callback(self._apply_intellisense_selection)
        self._intellisense_popup.set_dismiss_callback(self._dismiss_intellisense_popup)
        self._tab_control_visible = bool(self.settings.show_tab_control)
        self._active_notebook = None  # type: ignore[assignment]  # Notebook | None
        self._entries_panel_visible = False
        self._main_splitter = wx.SplitterWindow(self.frame, style=wx.SP_LIVE_UPDATE | wx.SP_3D)
        self._main_splitter.SetName("Document area")
        self._main_splitter.Bind(wx.EVT_SET_FOCUS, self._on_container_focus)
        self._apply_silent_accessible(self._main_splitter)
        self._documents_panel = wx.Panel(self._main_splitter)
        self._documents_panel.SetName("Documents")
        self._documents_panel.Bind(wx.EVT_SET_FOCUS, self._on_container_focus)
        self._apply_silent_accessible(self._documents_panel)
        self._documents_sizer = wx.BoxSizer(wx.VERTICAL)
        self._documents_panel.SetSizer(self._documents_sizer)
        self.notebook = self._create_tab_host(self._tab_control_visible)
        self._document_tabs: list[_DocumentTab] = []
        self._active_tab_index = -1
        self._statusbar_cells: list[_StatusBarCell] = []
        self._active_statusbar_cell_index = 0
        self._documents_sizer.Add(self.notebook, 1, wx.EXPAND)
        self._entries_panel = NotebookEntriesPanel(self._main_splitter, wx)
        self._entries_panel.panel.Bind(wx.EVT_SET_FOCUS, self._on_container_focus)
        self._apply_silent_accessible(self._entries_panel.panel)
        self._main_splitter.Initialize(self._documents_panel)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self._main_splitter, 1, wx.EXPAND)
        self.statusbar = wx.Panel(self.frame)
        self.statusbar.SetName("Status bar")
        self.statusbar.Bind(wx.EVT_SET_FOCUS, self._on_container_focus)
        self._apply_silent_accessible(self.statusbar)
        self._statusbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.statusbar.SetSizer(self._statusbar_sizer)
        layout.Add(self.statusbar, 0, wx.EXPAND)
        self.frame.SetSizer(layout)
        self._create_document_tab(self.document, select=True)
        self._location_ring.record(0)
        self._region_tracker.enter("Editor")
        self._apply_theme(self.settings.theme)

        self._build_commands()
        self._refresh_voice_command_aliases()
        self._build_menu()
        self._apply_watch_folder_menu_state()
        self._refresh_sessions_menu()
        self._apply_accelerators()
        self._reload_global_hotkeys()
        self._bind_events()
        self._init_context_help()
        self._apply_startup_document_preference()
        self._apply_announcement_trace_setting()

        set_announce_handler(self._announce)
        if safe_mode:
            self._set_status("Safe mode enabled. Optional state is disabled.")
        else:
            self._set_status("Ready. Tip: press Ctrl+Shift+P for Command Palette.")
        # This tail runs right after the startup tip is announced; never let it
        # take down construction (that was a "reads the tip then crashes" path).
        try:
            self._announce_backend_state_on_startup()
            self._refresh_title()
        except Exception:
            self._report_startup_task_failure("startup finalization")
        if not safe_mode:
            try:
                from quill.ui import sound_manager

                sound_manager.init(self.settings)
            except Exception:
                self._report_startup_task_failure("sound manager init")

    @property
    def _help_frame(self) -> object:
        return self.frame

    def show(self) -> None:
        self.frame.Show(True)
        # Bring the window to the front and focus the editor, so it doesn't open
        # behind the launching console (screen-reader users land in the editor).
        # On Windows, Raise() is blocked by focus-stealing prevention when the
        # launcher (e.g. a terminal) owns the foreground; use the
        # AttachThreadInput technique to bypass it (#166).
        if sys.platform == "win32":
            try:
                from quill.platform.windows.foreground import force_foreground_window

                force_foreground_window(self.frame.GetHandle())
            except Exception:
                pass
        self.frame.Raise()
        self.frame.RequestUserAttention()
        if getattr(self, "editor", None) is not None:
            self._wx.CallAfter(self.editor.SetFocus)
        if not self._startup_deferred_ran:
            self._startup_deferred_ran = True
            self._wx.CallAfter(self._run_deferred_startup_tasks)
        focus_target = (
            self.notebook if self._empty_workspace_active else getattr(self, "editor", None)
        )
        if focus_target is not None and hasattr(focus_target, "SetFocus"):
            self._wx.CallAfter(focus_target.SetFocus)

    def _run_deferred_startup_tasks(self) -> None:
        _profile = os.environ.get("QUILL_PROFILE_STARTUP") == "1"
        _times: list[tuple[str, float]] = []

        try:
            self._start_ipc_poll()
        except Exception:
            self._report_startup_task_failure("IPC poll")
        # detect_screen_reader() shells out to `tasklist`, which can take
        # 400-600 ms on the UI thread.  Run it on a daemon thread and update
        # the status bar via wx.CallAfter so the window is fully responsive
        # while the subprocess runs.
        _t = time.perf_counter()
        _safe_mode_snap = self._safe_mode

        def _sr_detect_worker() -> None:
            t_worker = time.perf_counter()
            try:
                detection = detect_screen_reader()
                if detection.detected:
                    self._wx.CallAfter(
                        self._set_status,
                        f"Detected screen reader: {detection.name}. Adaptive hints enabled.",
                    )
                elif not _safe_mode_snap:
                    self._wx.CallAfter(
                        self._set_status,
                        "Ready. Tip: press Ctrl+Shift+P for Command Palette.",
                    )
            except Exception:
                pass
            if _profile:
                self._wx.CallAfter(
                    _times.append,
                    ("screen-reader detection (bg)", time.perf_counter() - t_worker),
                )

        import threading

        threading.Thread(  # GATE-40-OK: one-shot tasklist probe; posts result via CallAfter.
            target=_sr_detect_worker, daemon=True, name="sr-detect"
        ).start()
        if _profile:
            _times.append(("screen-reader detection (dispatch)", time.perf_counter() - _t))
        # A first-run / onboarding step must NEVER take down the whole app on
        # launch. Previously an exception here propagated out of the wx CallAfter
        # handler and the app "crashed right away" after the startup tip, with
        # nothing in the log. Now we isolate each step, record the full
        # traceback, and keep Quill open. (Tracked for a proper fix in #73.)
        try:
            if getattr(self, "_first_run_trust_consent_prompt", False):
                accepted = self._show_trust_consent_onboarding(force=False)
                self._first_run_trust_consent_prompt = False
                if not accepted:
                    self._set_status("Startup consent declined. Quill is closing.")
                    self.frame.Close()
                    return
        except Exception:
            self._report_startup_task_failure("trust-consent onboarding")
        for label, task in (
            # Pre-warm the WebView2 subprocess before the user opens a preview
            # or the AI chat pane.  The first WebView.New() call initialises the
            # Edge WebView2 process and can block the UI thread for several
            # seconds (sometimes minutes) on slower or first-time Windows
            # installations.  Paying that cost here — once, in the deferred
            # startup sequence — means subsequent preview opens (F6, auto-preview,
            # AI panel) are near-instant.  Fixes #174 and reduces #177.
            ("WebView2 warm-up", self._prewarm_webview_runtime),
            ("crash recovery", self._offer_crash_recovery),
            ("first-run onboarding", self._maybe_run_first_run_onboarding),
            ("startup profile prompt", self.run_startup_profile_prompt),
            ("watch-folder startup", self._maybe_start_watch_folder),
            ("lexical cache warm-up", start_lexical_preload),
            # §8.2 TTS-FALLBACK-ANNOUNCE: show status prompt when TTS init failed.
            ("TTS fallback check", self._check_tts_fallback_on_startup),
        ):
            _t = time.perf_counter() if _profile else 0.0
            try:
                task()
            except Exception:
                self._report_startup_task_failure(label)
            if _profile:
                _times.append((label, time.perf_counter() - _t))
        _t = time.perf_counter() if _profile else 0.0
        if (
            getattr(self.settings, "auto_check_updates", False)
            and not self._safe_mode
            and self._update_check_due()
        ):
            try:
                self.check_for_updates(silent_no_update=True)
            except Exception:
                self._report_startup_task_failure("update check")
        if _profile:
            _times.append(("update check", time.perf_counter() - _t))
            self._write_startup_timing(_times)

    def _report_startup_task_failure(self, task_label: str) -> None:
        """Log a startup task's traceback to a findable file and keep going.

        Startup runs inside a wx CallAfter, where an unhandled exception kills
        the app with no visible error. We persist the traceback so the failing
        step can be diagnosed, and surface a non-fatal status instead.
        """
        import logging
        import traceback

        logging.getLogger(__name__).exception("Startup task failed: %s", task_label)
        try:
            from quill.core.paths import app_data_dir

            log_path = app_data_dir() / "logs" / "startup-errors.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"--- startup task failed: {task_label} ---\n")
                handle.write(traceback.format_exc())
                handle.write("\n")
        except Exception:
            pass
        self._set_status(
            f"Startup step '{task_label}' could not run; Quill is ready. "
            "See logs/startup-errors.log."
        )

    def _write_startup_timing(self, times: list[tuple[str, float]]) -> None:
        from quill.core.paths import app_data_dir

        total = sum(e for _, e in times)
        lines = [f"Startup task timing  (total {total * 1000:.0f} ms)\n", "=" * 50 + "\n"]
        for label, elapsed in times:
            pct = elapsed / total * 100 if total > 0 else 0
            lines.append(f"  {label:<45} {elapsed * 1000:7.1f} ms  ({pct:.0f}%)\n")
        out = app_data_dir() / "logs" / "startup_tasks.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(lines), encoding="utf-8")
        print(f"[profile] startup task timing -> {out}", flush=True)

    def _apply_startup_document_preference(self) -> None:
        if not self.settings.start_with_no_document_open:
            return
        if len(self._document_tabs) != 1:
            return
        if self.document.path is not None or self.document.modified or self.editor.GetValue():
            return
        self._empty_workspace_active = True
        self.editor.SetEditable(False)
        self._set_tab_page_text(0, "Start")
        self._set_status("No document open. Use File > New or File > Open.")

    def _clear_empty_workspace_state(self) -> None:
        if not self._empty_workspace_active:
            return
        self._empty_workspace_active = False
        self.editor.SetEditable(True)
        self._set_tab_page_text(self._current_tab_index(), self.document.name)

    def _build_commands(self) -> None:
        self.commands.register(
            "file.new",
            "New File",
            self.new_file,
            self._binding_for("file.new"),
        )
        self.commands.register(
            "file.open",
            "Open File...",
            self.open_file,
            self._binding_for("file.open"),
        )
        self.commands.register(
            "file.ssh_quick_connect",
            "Open over SSH: Quick Connect...",
            self.open_ssh_quick_connect,
            self._binding_for("file.ssh_quick_connect"),
        )
        self.commands.register(
            "file.ssh_site_manager",
            "Open over SSH: Site Manager...",
            self.open_ssh_site_manager,
            self._binding_for("file.ssh_site_manager"),
        )
        self.commands.register(
            "file.open_github_repository",
            "Open Remote GitHub Repository...",
            self.open_github_repository,
            None,
        )
        self.commands.register(
            "file.open_github_file_url",
            "Open Remote GitHub File URL...",
            self.open_github_file_url,
            None,
        )
        self.commands.register(
            "file.github_save_back",
            "Save to GitHub...",
            self.github_save_back,
            None,
        )
        self.commands.register(
            "file.github_manage_accounts",
            "Manage GitHub Accounts...",
            self.manage_github_accounts,
            None,
        )
        self.commands.register(
            "tools.open_python_console",
            "Open Python Console...",
            self.open_python_console,
            None,
        )
        self.commands.register(
            "tools.open_typescript_console",
            "Open TypeScript Console...",
            self.open_typescript_console,
            None,
        )
        self.commands.register(
            "tools.copy_diagnostic_summary",
            "Copy Diagnostic Summary",
            self.copy_diagnostic_summary,
            None,
        )
        self.commands.register(
            "tools.restart_typescript_worker",
            "Restart TypeScript Worker",
            self.restart_typescript_worker,
            None,
        )
        self.commands.register(
            "file.save",
            "Save",
            self.save_file,
            self._binding_for("file.save"),
        )
        self.commands.register(
            "file.save_as",
            "Save As...",
            self.save_file_as,
            self._binding_for("file.save_as"),
        )
        self.commands.register(
            "file.close_document",
            "Close Document",
            self.close_current_document,
            self._binding_for("file.close_document"),
        )
        self.commands.register(
            "file.save_all",
            "Save All",
            self.save_all_files,
            None,
        )
        self.commands.register(
            "file.reload_from_disk",
            "Reload from Disk",
            self.reload_from_disk,
            None,
        )
        self.commands.register(
            "file.restore_backup",
            "Restore Backup...",
            self.restore_backup,
            None,
        )
        self.commands.register(
            "file.page_setup",
            "Page Setup...",
            self.page_setup,
            None,
        )
        self.commands.register(
            "file.print",
            "Print...",
            self.print_document,
            self._binding_for("file.print"),
        )
        self.commands.register(
            "file.save_as_plain_text",
            "Save As Plain Text...",
            self.save_as_plain_text,
            None,
        )
        self.commands.register(
            "file.choose_encoding",
            "Choose Encoding...",
            self.choose_document_encoding,
            None,
        )
        self.commands.register(
            "file.toggle_line_endings",
            "Toggle Line Endings",
            self.toggle_line_endings,
            None,
        )
        self.commands.register(
            "file.open_containing_folder",
            "Open Containing Folder",
            self.open_containing_folder,
            None,
        )
        self.commands.register(
            "file.open_url",
            "Open from URL...",
            self.open_url,
            None,
        )
        self.commands.register(
            "file.save_session",
            "Save Session...",
            self.save_session,
            None,
        )
        self.commands.register(
            "file.open_session",
            "Open Session...",
            self.open_session,
            None,
        )
        self.commands.register(
            "app.command_palette",
            "Command Palette...",
            self.open_palette,
            self._binding_for("app.command_palette"),
        )
        self.commands.register(
            "app.preferences",
            "Preferences...",
            self.open_preferences,
            self._binding_for("app.preferences"),
        )
        self.commands.register(
            "app.exit",
            "Exit",
            self.exit_app,
            self._binding_for("app.exit"),
        )
        self.commands.register(
            "window.next_document",
            "Next Document",
            self.next_document,
            self._binding_for("window.next_document"),
        )
        self.commands.register(
            "window.previous_document",
            "Previous Document",
            self.previous_document,
            self._binding_for("window.previous_document"),
        )
        self.commands.register(
            "navigate.speak_window_title",
            "Speak Window Title",
            self.speak_window_title,
            self._binding_for("navigate.speak_window_title"),
        )
        self.commands.register(
            "navigate.speak_full_path",
            "Speak Full Path",
            self.speak_full_path,
            self._binding_for("navigate.speak_full_path"),
        )
        self.commands.register(
            "navigate.speak_status_summary",
            "Speak Status Summary",
            self.speak_status_summary,
            self._binding_for("navigate.speak_status_summary"),
        )
        self.commands.register(
            "view.send_to_tray",
            "Send to Tray",
            self.send_to_tray,
            self._binding_for("view.send_to_tray"),
        )
        self.commands.register(
            "view.toggle_soft_wrap",
            "Toggle Soft Wrap",
            self.toggle_soft_wrap,
            self._binding_for("view.toggle_soft_wrap"),
        )
        self.commands.register(
            "view.toggle_tab_control",
            "Toggle Tab Control",
            self.toggle_tab_control,
            self._binding_for("view.toggle_tab_control"),
        )
        self.commands.register(
            "view.toggle_find_wrap",
            "Toggle Find Wrap",
            self.toggle_find_wrap,
            None,
        )
        self.commands.register(
            "view.toggle_dark_mode",
            "Toggle Dark Mode",
            self.toggle_dark_mode,
            None,
        )
        self.commands.register(
            "view.toggle_persistent_undo",
            "Toggle Persistent Undo",
            self.toggle_persistent_undo,
            None,
        )
        self.commands.register(
            "view.toggle_spellcheck_as_you_type",
            "Toggle Spell Check As You Type",
            self.toggle_spellcheck_as_you_type,
            None,
        )
        self.commands.register(
            "view.toggle_intellisense_as_you_type",
            "Toggle Word Prediction As You Type",
            self.toggle_intellisense_as_you_type,
            None,
        )
        self.commands.register(
            "view.preview",
            "Preview",
            self.preview_in_app,
            self._binding_for("view.preview"),
        )
        self.commands.register(
            "view.split_preview",
            "Preview Side by Side",
            self.toggle_side_preview,
            self._binding_for("view.split_preview"),
        )
        self.commands.register(
            "view.focus_preview",
            "Focus Preview",
            self.focus_preview,
            self._binding_for("view.focus_preview"),
        )
        self.commands.register(
            "view.switch_editing_lens",
            "Switch Editing Lens",
            self.switch_editing_lens,
            self._binding_for("view.switch_editing_lens"),
        )
        self.commands.register(
            "view.browser_preview",
            "Browser Preview",
            self.preview_in_browser,
            self._binding_for("view.browser_preview"),
        )
        self.commands.register(
            "tools.ai_hub",
            "AI Hub",
            self.open_ai_hub,
            None,
        )
        self.commands.register(
            "tools.ai_assistant",
            "Writing Assistant",
            self.open_writing_assistant,
            None,
        )
        self.commands.register(
            "tools.ai_prompt_studio",
            "Prompt Studio",
            self.open_prompt_studio,
            None,
        )
        self.commands.register(
            "tools.ai_agent_center",
            "Agent Center",
            self.open_agent_center,
            None,
        )
        self.commands.register(
            "tools.ai_accessibility_agent",
            "Accessibility Tune-Up",
            self.make_document_accessible,
            None,
        )
        self.commands.register(
            "tools.ask_ai",
            "Ask AI...",
            self.open_ask_ai,
            None,
        )
        self.commands.register(
            "tools.prompt_library",
            "Prompt Library",
            self.open_prompt_library,
            None,
        )
        self.commands.register(
            "tools.skill_library",
            "Skill Library",
            self.open_skill_library,
            None,
        )
        self.commands.register(
            "tools.check_grammar_ai",
            "Check Grammar with AI",
            self.check_grammar_with_ai,
            None,
        )
        self.commands.register(
            "tools.ask_quill_chat",
            "Ask Quill Chat",
            self.open_ask_quill_chat,
            self._binding_for("tools.ask_quill_chat"),
        )
        self.commands.register(
            "tools.ai_model",
            "AI Model",
            self.open_ai_model_settings,
            None,
        )
        self.commands.register(
            "tools.ai_session_browser",
            "AI Session Branches",
            self.open_ai_session_browser,
            None,
        )
        self.commands.register(
            "tools.ai_connection",
            "AI Connection",
            self.open_ai_preferences,
            None,
        )
        self.commands.register(
            "tools.ai_rewrite_selection",
            "Rewrite Selection",
            self.open_ai_rewrite_selection,
            None,
        )
        self.commands.register(
            "tools.ai_summarize_selection",
            "Summarize Selection",
            self.open_ai_summarize_selection,
            None,
        )
        self.commands.register(
            "tools.ai_continue_writing",
            "Continue Writing",
            self.open_ai_continue_writing,
            None,
        )
        self.commands.register(
            "tools.ai_fix_grammar",
            "Fix Grammar",
            self.open_ai_fix_grammar,
            None,
        )
        self.commands.register(
            "tools.train_writing_style",
            "Train Writing Style",
            self.open_train_writing_style,
            None,
        )
        self.commands.register(
            "tools.writing_instructions",
            "Open Writing Instructions",
            self.open_writing_instructions,
            None,
        )
        self.commands.register(
            "view.toggle_overwrite_mode",
            "Toggle Overwrite Mode",
            self.toggle_overwrite_mode,
            None,
        )
        self.commands.register(
            "navigate.go_to_line",
            "Go To Line...",
            self.go_to_line,
            self._binding_for("navigate.go_to_line"),
        )
        self.commands.register(
            "navigate.go_to_page",
            "Go To Page...",
            self.go_to_page,
            self._binding_for("navigate.go_to_page"),
        )
        self.commands.register(
            "navigate.back_location",
            "Back Location",
            self.navigate_back_location,
            self._binding_for("navigate.back_location"),
        )
        self.commands.register(
            "navigate.forward_location",
            "Forward Location",
            self.navigate_forward_location,
            self._binding_for("navigate.forward_location"),
        )
        self.commands.register(
            "navigate.next_heading",
            "Next Heading",
            self.navigate_next_heading,
            None,
        )
        self.commands.register(
            "navigate.previous_heading",
            "Previous Heading",
            self.navigate_previous_heading,
            None,
        )
        self.commands.register(
            "navigate.next_block",
            "Next Block",
            self.navigate_next_block,
            None,
        )
        self.commands.register(
            "navigate.previous_block",
            "Previous Block",
            self.navigate_previous_block,
            None,
        )
        self.commands.register(
            "navigate.outline_navigator",
            "Outline Navigator...",
            self.open_outline_navigator,
            self._binding_for("navigate.outline_navigator"),
        )
        self.commands.register(
            "navigate.heading_organizer",
            "Heading Organizer...",
            self.open_heading_organizer,
            self._binding_for("navigate.heading_organizer"),
        )
        self.commands.register(
            "navigate.next_token",
            "Next Token",
            self.navigate_next_token,
            self._binding_for("navigate.next_token"),
        )
        self.commands.register(
            "navigate.previous_token",
            "Previous Token",
            self.navigate_previous_token,
            self._binding_for("navigate.previous_token"),
        )
        self.commands.register(
            "navigate.set_language",
            "Set Document Language...",
            self.set_document_language,
            self._binding_for("navigate.set_language"),
        )
        self.commands.register(
            "navigate.match_bracket",
            "Match Bracket",
            self.match_bracket,
            self._binding_for("navigate.match_bracket"),
        )
        self.commands.register(
            "navigate.next_structure",
            "Next Structure",
            self.navigate_next_structure,
            self._binding_for("navigate.next_structure"),
        )
        self.commands.register(
            "navigate.previous_structure",
            "Previous Structure",
            self.navigate_previous_structure,
            self._binding_for("navigate.previous_structure"),
        )
        self.commands.register(
            "navigate.next_region",
            "Next Region",
            self.navigate_next_region,
            self._binding_for("navigate.next_region"),
        )
        self.commands.register(
            "navigate.previous_region",
            "Previous Region",
            self.navigate_previous_region,
            self._binding_for("navigate.previous_region"),
        )
        self.commands.register(
            "navigate.set_bookmark",
            "Set Bookmark...",
            self.set_bookmark,
            None,
        )
        self.commands.register(
            "navigate.go_to_bookmark",
            "Go To Bookmark...",
            self.go_to_bookmark,
            None,
        )
        self.commands.register(
            "navigate.list_bookmarks",
            "List Bookmarks...",
            self.list_bookmarks,
            self._binding_for("navigate.list_bookmarks"),
        )
        self.commands.register(
            "tools.word_count",
            "Word Count...",
            self.show_word_count,
            self._binding_for("tools.word_count"),
        )
        self.commands.register(
            "tools.sticky_notes",
            "Sticky Notes...",
            self.manage_sticky_notes,
            None,
        )
        self.commands.register(
            "tools.sticky_note_capture",
            "New Sticky Note...",
            self.create_sticky_note,
            self._binding_for("tools.sticky_note_capture"),
        )
        self.commands.register(
            "tools.spell_check_dialog",
            "Spell Check...",
            self.open_spell_check_dialog,
            self._binding_for("tools.spell_check_dialog"),
        )
        self.commands.register(
            "tools.next_misspelling",
            "Next Misspelling",
            self.next_misspelling,
            self._binding_for("tools.next_misspelling"),
        )
        self.commands.register(
            "tools.previous_misspelling",
            "Previous Misspelling",
            self.previous_misspelling,
            self._binding_for("tools.previous_misspelling"),
        )
        self.commands.register(
            "tools.misspelling_list",
            "Misspelling List...",
            self.open_misspelling_list,
            self._binding_for("tools.misspelling_list"),
        )
        self.commands.register(
            "tools.thesaurus",
            "Thesaurus...",
            self.show_thesaurus,
            self._binding_for("tools.thesaurus"),
        )
        self.commands.register(
            "tools.dictionary_status",
            "Dictionary Status...",
            self.show_dictionary_status,
            None,
        )
        self.commands.register(
            "tools.ocr_image",
            "OCR Image...",
            self.ocr_image_file,
            None,
        )
        self.commands.register(
            "tools.ocr_clipboard",
            "OCR Clipboard Image",
            self.ocr_clipboard_image,
            self._binding_for("tools.ocr_clipboard"),
        )
        self.commands.register(
            "tools.ocr_screen",
            "OCR Screen Capture...",
            self.ocr_screen_capture,
            self._binding_for("tools.ocr_screen"),
        )
        self.commands.register(
            "tools.describe_image",
            "Describe Image...",
            self.describe_image_with_ai,
            None,
        )
        self.commands.register(
            "tools.read_aloud_start_pause",
            "Read Aloud Start/Pause",
            self.toggle_read_aloud,
            self._binding_for("tools.read_aloud_start_pause"),
        )
        self.commands.register(
            "tools.read_aloud_stop",
            "Read Aloud Stop",
            self.stop_read_aloud,
            self._binding_for("tools.read_aloud_stop"),
        )
        self.commands.register(
            "tools.read_aloud_voice",
            "Read Aloud Voice...",
            self.choose_read_aloud_voice,
            None,
        )
        self.commands.register(
            "tools.read_aloud_settings",
            "Read Aloud Settings...",
            self.choose_read_aloud_settings,
            None,
        )
        self.commands.register(
            "tools.read_aloud_generate_audio",
            "Generate Speech Audio...",
            self.generate_speech_audio,
            None,
        )
        self.commands.register(
            "tools.announcement_backend",
            "Announcement Backend...",
            self.choose_announcement_backend,
            None,
        )
        self.commands.register(
            "tools.announcement_trace_toggle",
            "Toggle Announcement Trace Capture",
            self.toggle_announcement_trace_capture,
            None,
        )
        self.commands.register(
            "tools.sound_toggle",
            "Toggle Sound Notifications",
            self.toggle_sound,
            self._binding_for("tools.sound_toggle"),
        )
        self.commands.register(
            "tools.sound_events",
            "Manage Sound Events",
            self.open_sound_events_dialog,
            self._binding_for("tools.sound_events"),
        )
        self.commands.register(
            "tools.dictation_toggle",
            "Dictation",
            self.toggle_dictation,
            self._binding_for("tools.dictation_toggle"),
            feature_id="core.dictation",
        )
        self.commands.register(
            "tools.dictation_voice_commands_toggle",
            "Hey QUILL Commands",
            self.toggle_dictation_voice_commands,
            None,
            feature_id="core.voice_commands",
        )
        self.commands.register(
            "whisperer.model_manager",
            "BITS Whisperer Speech Model Manager...",
            self.open_bw_model_manager,
            None,
            feature_id="core.bw_transcription",
        )
        self.commands.register(
            "whisperer.model_status",
            "BITS Whisperer Speech Model Status",
            self.show_bw_model_status,
            None,
            feature_id="core.bw_transcription",
        )
        self.commands.register(
            "whisperer.model_recommend",
            "BITS Whisperer Use Recommended Speech Model",
            self.apply_bw_recommended_model,
            None,
            feature_id="core.bw_transcription",
        )
        self.commands.register(
            "whisperer.toggle_parakeet",
            "BITS Whisperer Toggle Parakeet Model Visibility",
            self.toggle_bw_parakeet_visibility,
            None,
            feature_id="core.bw_parakeet",
        )
        self.commands.register(
            "whisperer.check_faster_whisper",
            "BITS Whisperer Check faster-whisper Engine",
            self.check_bw_faster_whisper_engine,
            None,
            feature_id="core.bw_transcription",
        )
        self.commands.register(
            "whisperer.provider_center",
            "BITS Whisperer Provider Center...",
            self.open_bw_provider_center,
            None,
            feature_id="core.bw_providers",
        )
        self.commands.register(
            "whisperer.provider_status",
            "BITS Whisperer Provider Status",
            self.show_bw_provider_status,
            None,
            feature_id="core.bw_providers",
        )
        self.commands.register(
            "whisperer.provider_recommend",
            "BITS Whisperer Use Recommended Provider",
            self.apply_bw_recommended_provider,
            None,
            feature_id="core.bw_providers",
        )
        self.commands.register(
            "whisperer.provider_select",
            "BITS Whisperer Select Provider...",
            self.select_bw_provider,
            None,
            feature_id="core.bw_providers",
        )
        self.commands.register(
            "whisperer.readiness_check",
            "BITS Whisperer Readiness Check",
            self.show_bw_readiness_check,
            None,
            feature_id="core.bw_insights",
        )
        self.commands.register(
            "whisperer.capability_matrix",
            "BITS Whisperer Capability Matrix",
            self.show_bw_capability_matrix_page,
            None,
            feature_id="core.bw_insights",
        )
        self.commands.register(
            "whisperer.download_queue",
            "BITS Whisperer Download Queue...",
            self.manage_bw_download_queue,
            None,
            feature_id="core.bw_insights",
        )
        self.commands.register(
            "tools.watch_folder_toggle",
            "Watch Folder Monitoring",
            self.toggle_watch_folder_monitoring,
            None,
            feature_id="core.watch_folder",
        )
        self.commands.register(
            "tools.watch_folder_settings",
            "Watch Folder Settings...",
            self.open_watch_folder_settings,
            None,
            feature_id="core.watch_folder",
        )
        self.commands.register(
            "tools.watch_folder_status",
            "Watch Folder Status...",
            self.show_watch_folder_status,
            None,
            feature_id="core.watch_folder",
        )
        self.commands.register(
            "tools.document_intake_report",
            "Document Intake Report...",
            self.show_document_intake_report,
            self._binding_for("tools.document_intake_report"),
        )
        self.commands.register(
            "tools.review_extraction_quality",
            "Review Extraction Quality...",
            self.review_extraction_quality,
            None,
        )
        self.commands.register(
            "tools.regex_helper",
            "Regular Expression Helper...",
            self.show_regex_helper,
            None,
        )
        self.commands.register(
            "tools.pandoc_wizard",
            "Pandoc Conversion Wizard...",
            self.open_pandoc_wizard,
            None,
        )
        self.commands.register(
            "tools.external_tools",
            "External Tools and Format Support...",
            self.show_external_tools_dialog,
            None,
        )
        self.commands.register(
            "tools.report_bad_extraction",
            "Report Bad Extraction...",
            self.report_bad_extraction,
            None,
        )
        self.commands.register(
            "tools.shell_install",
            "Install Shell Integration...",
            self.install_shell_integration,
            None,
        )
        self.commands.register(
            "tools.shell_remove",
            "Remove Shell Integration",
            self.remove_shell_integration,
            None,
        )
        self.commands.register(
            "tools.notifications",
            "Open Notifications...",
            self.open_notifications,
            None,
        )
        self.commands.register(
            "tools.check_updates",
            "Check for Updates...",
            self.check_for_updates,
            None,
        )
        self.commands.register(
            "tools.check_glow_updates",
            "Check for GLOW Updates...",
            self.check_for_glow_updates,
            None,
        )
        self.commands.register(
            "tools.validate_contrast",
            "Validate Contrast...",
            self.validate_contrast,
            None,
        )
        self.commands.register(
            "tools.link_inventory",
            "Link Inventory and Alt-Text Catalog...",
            self.show_link_inventory,
            None,
        )
        self.commands.register(
            "tools.compare_with_file",
            "Compare with File...",
            self.compare_with_file,
            None,
        )
        self.commands.register(
            "tools.compare_open_documents",
            "Compare Open Documents...",
            self.compare_open_documents,
            None,
        )
        self.commands.register(
            "tools.compare_next_difference",
            "Next Difference",
            self.compare_next_difference,
            None,
        )
        self.commands.register(
            "tools.compare_previous_difference",
            "Previous Difference",
            self.compare_previous_difference,
            None,
        )
        self.commands.register(
            "tools.compare_announce_difference",
            "Announce Current Difference",
            self.compare_announce_difference,
            None,
        )
        self.commands.register(
            "tools.compare_difference_list",
            "Open Difference List...",
            self.open_compare_difference_list,
            None,
        )
        self.commands.register(
            "tools.compare_toggle_sync",
            "Toggle Compare Synchronization",
            self.toggle_compare_synchronization,
            None,
        )
        self.commands.register(
            "tools.compare_options",
            "Compare Options...",
            self.open_compare_options,
            None,
        )
        self.commands.register(
            "tools.compare_create_summary",
            "Create Difference Summary",
            self.create_compare_summary_document,
            None,
        )
        self.commands.register(
            "tools.compare_copy_current_difference",
            "Copy Current Difference",
            self.copy_current_difference,
            None,
        )
        self.commands.register(
            "tools.compare_copy_all_differences",
            "Copy All Differences",
            self.copy_all_differences,
            None,
        )
        self.commands.register(
            "tools.export_keymap",
            "Export Keymap...",
            self.export_keymap_file,
            None,
        )
        self.commands.register(
            "tools.keymap_editor",
            "Keymap Editor...",
            self.open_keymap_editor,
            None,
        )
        self.commands.register(
            "tools.status_bar_settings",
            "Status Bar Layout...",
            self.open_status_bar_settings,
            None,
        )
        self.commands.register(
            "tools.share_export",
            "Export and Back Up...",
            self.open_share_export_dialog,
            None,
        )
        self.commands.register(
            "tools.share_import",
            "Import or Restore...",
            self.open_share_import_dialog,
            None,
        )
        self.commands.register(
            "tools.import_keymap",
            "Import Keymap...",
            self.import_keymap_file,
            None,
        )
        self.commands.register(
            "tools.export_keyboard_pack",
            "Export Keyboard Pack (.kqp)...",
            self.export_keyboard_pack_file,
            None,
        )
        self.commands.register(
            "tools.import_keyboard_pack",
            "Import Keyboard Pack (.kqp)...",
            self.import_keyboard_pack_file,
            None,
        )
        self.commands.register(
            "tools.reset_keymap",
            "Reset Keymap",
            self.reset_keymap_defaults,
            None,
        )
        self.commands.register(
            "tools.open_welcome_guide",
            "Open Welcome Guide",
            self.open_welcome_guide,
            None,
        )
        self.commands.register(
            "tools.open_keyboard_reference",
            "Open Keyboard Reference",
            self.open_keyboard_reference,
            None,
        )
        self.commands.register(
            "help.open_user_guide",
            "Open User Guide",
            self.open_user_guide,
            None,
        )
        self.commands.register(
            "help.open_third_party_notices",
            "Open Third-Party Notices",
            self.open_third_party_notices,
            None,
        )
        self.commands.register(
            "help.why_dont_i_see_feature",
            "Why Don't I See a Feature?",
            self.show_feature_explanation,
            None,
        )
        self.commands.register(
            "help.switch_feature_profile",
            "Switch Feature Profile...",
            self.switch_feature_profile,
            None,
        )
        self.commands.register(
            "help.feature_profile_health_check",
            "Feature Profile Health Check...",
            self.show_feature_profile_health_check,
            None,
        )
        self.commands.register(
            "tools.individual_feature_toggles",
            "Manage Individual Features...",
            self.open_individual_feature_toggles,
            None,
        )
        self.commands.register(
            "tools.profiles_and_features_settings",
            "Profiles and Features...",
            self.open_profiles_and_features_settings,
            None,
        )
        self.commands.register(
            "help.undo_last_profile_change",
            "Undo Last Profile Change",
            self.undo_last_profile_change,
            None,
        )
        self.commands.register(
            "help.reset_feature_profile",
            "Reset to Essential Profile",
            self.reset_feature_profile_to_essential,
            None,
        )
        self.commands.register(
            "help.startup_wizard",
            "Startup Wizard...",
            self.run_startup_wizard,
            None,
        )
        self.commands.register(
            "help.run_profile_onboarding",
            "Startup Wizard...",
            self.run_startup_wizard,
            None,
        )
        self.commands.register(
            "tools.start_macro_recording",
            "Start Macro Recording",
            self.start_macro_recording,
            None,
        )
        self.commands.register(
            "tools.stop_macro_recording",
            "Stop Macro Recording",
            self.stop_macro_recording,
            None,
        )
        self.commands.register(
            "tools.play_last_macro",
            "Play Last Macro",
            self.play_last_macro,
            None,
        )
        self.commands.register(
            "tools.manage_macros",
            "Manage Macros...",
            self.manage_macros,
            None,
        )
        self.commands.register(
            "tools.cycle_autosave_interval",
            "Cycle Autosave Interval",
            self.cycle_autosave_interval,
            None,
        )
        self.commands.register(
            "help.about_quill",
            "About Quill",
            self.show_about_quill,
            None,
        )
        self.commands.register(
            "help.save_diagnostics",
            "Save Diagnostics...",
            self.save_diagnostics_bundle,
            None,
        )
        self.commands.register(
            "help.report_bug",
            "Report a Bug...",
            self.report_bug,
            None,
        )
        self.commands.register(
            "help.open_logs_folder",
            "Open Logs Folder",
            self.open_logs_folder,
            None,
        )
        self.commands.register(
            "help.open_diagnostics_folder",
            "Open Diagnostics Folder",
            self.open_diagnostics_folder,
            None,
        )
        self.commands.register(
            "help.what_can_i_do_here",
            "What Can I Do Here?",
            self.show_context_help,
            None,
        )
        self.commands.register(
            "whisperer.about",
            "About BITS Whisperer",
            self.show_whisperer_about_page,
            None,
        )
        self.commands.register(
            "help.status_page",
            "Status Page",
            self.show_help_status_page,
            None,
        )
        self.commands.register(
            "tools.keyboard_trap_snapshot",
            "Keyboard Trap Audit Snapshot...",
            self.show_keyboard_trap_snapshot,
            None,
        )
        self.commands.register(
            "tools.accessibility_audit",
            "Accessibility Audit...",
            self.show_accessibility_audit,
            None,
        )
        self.commands.register(
            "tools.glow_audit_document",
            "GLOW Audit Current Document",
            self.glow_audit_document,
            None,
        )
        self.commands.register(
            "tools.glow_audit_selection",
            "GLOW Audit Selection",
            self.glow_audit_selection,
            None,
        )
        self.commands.register(
            "tools.glow_fix_document",
            "GLOW Fix Current Document",
            self.glow_fix_document,
            None,
        )
        self.commands.register(
            "tools.glow_fix_selection",
            "GLOW Fix Selection",
            self.glow_fix_selection,
            None,
        )
        self.commands.register(
            "edit.undo",
            "Undo",
            self.undo,
            self._binding_for("edit.undo"),
        )
        self.commands.register(
            "edit.redo",
            "Redo",
            self.redo,
            self._binding_for("edit.redo"),
        )
        self.commands.register(
            "edit.copy_with_source",
            "Copy With Source",
            self.copy_with_source,
            self._binding_for("edit.copy_with_source"),
        )
        self.commands.register(
            "edit.toggle_extend_selection_mode",
            "Toggle Extend Selection Mode",
            self.toggle_extend_selection_mode,
            self._binding_for("edit.toggle_extend_selection_mode"),
        )
        self.commands.register(
            "edit.start_selection",
            "Start Selection",
            self.start_selection,
            self._binding_for("edit.start_selection"),
        )
        self.commands.register(
            "edit.complete_selection",
            "Complete Selection",
            self.complete_selection,
            self._binding_for("edit.complete_selection"),
        )
        self.commands.register(
            "edit.reselect",
            "Reselect",
            self.reselect,
            self._binding_for("edit.reselect"),
        )
        self.commands.register(
            "edit.go_to_start_of_selection",
            "Go to Start of Selection",
            self.go_to_start_of_selection,
            self._binding_for("edit.go_to_start_of_selection"),
        )
        self.commands.register(
            "edit.copy_all",
            "Copy All",
            self.copy_all,
            self._binding_for("edit.copy_all"),
        )
        self.commands.register(
            "edit.unselect_all",
            "Unselect All",
            self.unselect_all,
            self._binding_for("edit.unselect_all"),
        )
        self.commands.register(
            "edit.say_selected",
            "Say Selected",
            self.say_selected,
            self._binding_for("edit.say_selected"),
        )
        self.commands.register(
            "edit.read_all",
            "Read All",
            self.read_all,
            self._binding_for("edit.read_all"),
        )
        self.commands.register(
            "edit.find",
            "Find...",
            self.find_text,
            self._binding_for("edit.find"),
        )
        self.commands.register(
            "edit.find_next",
            "Find Next",
            self.find_next,
            self._binding_for("edit.find_next"),
        )
        self.commands.register(
            "edit.find_previous",
            "Find Previous",
            self.find_previous,
            self._binding_for("edit.find_previous"),
        )
        self.commands.register(
            "edit.replace",
            "Replace...",
            self.replace_text,
            self._binding_for("edit.replace"),
        )
        self.commands.register(
            "edit.find_all_matches",
            "Find All Matches",
            self.find_all_matches,
            self._binding_for("edit.find_all_matches"),
        )
        self.commands.register(
            "tools.search_in_files",
            "Search in Files...",
            self.search_in_files,
            self._binding_for("tools.search_in_files"),
        )
        self.commands.register(
            "tools.replace_in_files",
            "Replace Across Files...",
            self.replace_in_files,
            self._binding_for("tools.replace_in_files"),
        )
        self.commands.register(
            "edit.replace_all",
            "Replace All...",
            self.replace_all_text,
            self._binding_for("edit.replace_all"),
        )
        self.commands.register(
            "edit.insert_link",
            "Insert Link...",
            self.insert_link,
            self._binding_for("edit.insert_link"),
        )
        self.commands.register(
            "edit.follow_link",
            "Follow Link",
            self.follow_link,
            self._binding_for("edit.follow_link"),
        )
        self.commands.register(
            "edit.word_prediction",
            "Word Prediction...",
            self.show_word_prediction,
            self._binding_for("edit.word_prediction"),
        )
        self.commands.register(
            "edit.select_line",
            "Select Line",
            self.select_line,
            self._binding_for("edit.select_line"),
        )
        self.commands.register(
            "edit.select_paragraph",
            "Select Paragraph",
            self.select_paragraph,
            None,
        )
        self.commands.register(
            "edit.set_mark",
            "Set Mark",
            self.set_mark,
            self._binding_for("edit.set_mark"),
        )
        self.commands.register(
            "edit.pop_mark",
            "Pop Mark",
            self.pop_mark,
            self._binding_for("edit.pop_mark"),
        )
        self.commands.register(
            "edit.exchange_point_mark",
            "Exchange Point and Mark",
            self.exchange_point_and_mark,
            self._binding_for("edit.exchange_point_mark"),
        )
        self.commands.register(
            "edit.list_marks",
            "List Marks",
            self.list_marks,
            self._binding_for("edit.list_marks"),
        )
        self.commands.register(
            "edit.select_block",
            "Select Block",
            self.select_block,
            None,
        )
        self.commands.register(
            "edit.expand_selection",
            "Expand Selection",
            self.expand_selection,
            self._binding_for("edit.expand_selection"),
        )
        self.commands.register(
            "edit.shrink_selection",
            "Shrink Selection",
            self.shrink_selection,
            self._binding_for("edit.shrink_selection"),
        )
        self.commands.register(
            "edit.set_named_mark",
            "Set Named Mark",
            self.set_named_mark,
            self._binding_for("edit.set_named_mark"),
        )
        self.commands.register(
            "edit.jump_to_named_mark",
            "Jump to Named Mark",
            self.jump_to_named_mark,
            self._binding_for("edit.jump_to_named_mark"),
        )
        self.commands.register(
            "edit.open_review_buffer",
            "Open Review Buffer",
            self.open_review_buffer,
            self._binding_for("edit.open_review_buffer"),
        )
        self.commands.register(
            "edit.selection_actions",
            "Selection Actions",
            self.quill_key_selection_actions,
            self._binding_for("edit.selection_actions"),
        )
        self.commands.register(
            "navigate.quick_nav",
            "Quick Nav (Go to Anything)",
            self.open_quick_nav,
            self._binding_for("navigate.quick_nav"),
        )
        self.commands.register(
            "edit.select_to_start_of_line",
            "Select to Start of Line",
            self.select_to_start_of_line,
            self._binding_for("edit.select_to_start_of_line"),
        )
        self.commands.register(
            "edit.select_to_end_of_line",
            "Select to End of Line",
            self.select_to_end_of_line,
            self._binding_for("edit.select_to_end_of_line"),
        )
        self.commands.register(
            "edit.select_to_start_of_document",
            "Select to Start of Document",
            self.select_to_start_of_document,
            self._binding_for("edit.select_to_start_of_document"),
        )
        self.commands.register(
            "edit.select_to_end_of_document",
            "Select to End of Document",
            self.select_to_end_of_document,
            self._binding_for("edit.select_to_end_of_document"),
        )
        self.commands.register(
            "format.insert_html_tag",
            "Insert HTML Tag...",
            self.insert_html_tag,
            self._binding_for("format.insert_html_tag"),
        )
        self.commands.register(
            "format.toggle_line_comment",
            "Toggle Line Comment",
            self.format_toggle_line_comment,
            self._binding_for("format.toggle_line_comment"),
        )
        self.commands.register(
            "format.toggle_block_comment",
            "Toggle Block Comment",
            self.format_toggle_block_comment,
            self._binding_for("format.toggle_block_comment"),
        )
        self.commands.register(
            "format.auto_indent_newline",
            "Auto-Indent Newline",
            self.format_auto_indent_newline,
            self._binding_for("format.auto_indent_newline"),
        )
        self.commands.register(
            "format.indent",
            "Indent",
            self.format_indent,
            self._binding_for("format.indent"),
        )
        self.commands.register(
            "format.outdent",
            "Outdent",
            self.format_outdent,
            self._binding_for("format.outdent"),
        )
        self.commands.register(
            "format.insert_markdown_tag",
            "Insert Markdown Tag...",
            self.insert_markdown_tag,
            self._binding_for("format.insert_markdown_tag"),
        )
        self.commands.register(
            "format.insert_snippet",
            "Insert Snippet...",
            self.insert_snippet,
            self._binding_for("format.insert_snippet"),
        )
        self.commands.register(
            "format.manage_snippets",
            "Manage Snippets...",
            self.manage_snippets,
            self._binding_for("format.manage_snippets"),
        )
        self.commands.register(
            "format.expand_abbreviation",
            "Expand Abbreviation",
            self.expand_abbreviation_at_cursor,
            self._binding_for("format.expand_abbreviation"),
        )
        self.commands.register(
            "format.manage_abbreviations",
            "Manage Abbreviations...",
            self.open_abbreviation_manager,
            self._binding_for("format.manage_abbreviations"),
        )
        self.commands.register(
            "format.toggle_abbreviation_expansion",
            "Toggle Abbreviation Expansion",
            self.toggle_abbreviation_expansion,
            self._binding_for("format.toggle_abbreviation_expansion"),
        )
        self.commands.register(
            "format.bold",
            "Bold",
            self.format_bold,
            self._binding_for("format.bold"),
        )
        self.commands.register(
            "format.italic",
            "Italic",
            self.format_italic,
            self._binding_for("format.italic"),
        )
        self.commands.register(
            "format.heading_1",
            "Insert Heading 1",
            lambda: self.format_heading(1),
            self._binding_for("format.heading_1"),
        )
        self.commands.register(
            "format.heading_2",
            "Insert Heading 2",
            lambda: self.format_heading(2),
            self._binding_for("format.heading_2"),
        )
        self.commands.register(
            "format.heading_3",
            "Insert Heading 3",
            lambda: self.format_heading(3),
            self._binding_for("format.heading_3"),
        )
        self.commands.register(
            "format.heading_4",
            "Insert Heading 4",
            lambda: self.format_heading(4),
            self._binding_for("format.heading_4"),
        )
        self.commands.register(
            "format.heading_5",
            "Insert Heading 5",
            lambda: self.format_heading(5),
            self._binding_for("format.heading_5"),
        )
        self.commands.register(
            "format.heading_6",
            "Insert Heading 6",
            lambda: self.format_heading(6),
            self._binding_for("format.heading_6"),
        )
        self.commands.register(
            "format.decrease_heading_level",
            "Decrease Heading Level",
            self.decrease_heading_level,
            self._binding_for("format.decrease_heading_level"),
        )
        self.commands.register(
            "format.increase_heading_level",
            "Increase Heading Level",
            self.increase_heading_level,
            self._binding_for("format.increase_heading_level"),
        )
        self.commands.register(
            "format.style_headings",
            "Style Headings...",
            self.style_headings,
            self._binding_for("format.style_headings"),
        )
        self.commands.register(
            "format.upper_case",
            "Upper Case",
            self.format_upper_case,
            self._binding_for("format.upper_case"),
        )
        self.commands.register(
            "format.lower_case",
            "Lower Case",
            self.format_lower_case,
            self._binding_for("format.lower_case"),
        )
        self.commands.register(
            "format.title_case",
            "Title Case",
            self.format_title_case,
            None,
        )
        self.commands.register(
            "format.sentence_case",
            "Sentence Case",
            self.format_sentence_case,
            None,
        )
        self.commands.register(
            "format.toggle_case",
            "Toggle Case",
            self.format_toggle_case,
            None,
        )
        self.commands.register(
            "format.move_line_up",
            "Move Line Up",
            self.move_line_up,
            self._binding_for("format.move_line_up"),
        )
        self.commands.register(
            "format.move_line_down",
            "Move Line Down",
            self.move_line_down,
            self._binding_for("format.move_line_down"),
        )
        self.commands.register(
            "format.duplicate_line",
            "Duplicate Line",
            self.duplicate_line,
            self._binding_for("format.duplicate_line"),
        )
        self.commands.register(
            "format.delete_line",
            "Delete Line",
            self.delete_line,
            self._binding_for("format.delete_line"),
        )
        self.commands.register(
            "format.join_lines",
            "Join Lines",
            self.join_lines,
            None,
        )
        self.commands.register(
            "format.insert_bullet_list",
            "Insert Bullet List",
            self.format_insert_bullet_list,
            None,
        )
        self.commands.register(
            "format.insert_numbered_list",
            "Insert Numbered List",
            self.format_insert_numbered_list,
            None,
        )
        self.commands.register(
            "format.insert_task_list",
            "Insert Task List",
            self.format_insert_task_list,
            None,
        )
        self.commands.register(
            "format.list_manager",
            "List Manager",
            self.open_list_manager,
            self._binding_for("format.list_manager"),
        )
        self.commands.register(
            "format.insert_code_block",
            "Insert Code Block",
            self.format_insert_code_block,
            None,
        )
        self.commands.register(
            "format.insert_footnote",
            "Insert Footnote",
            self.format_insert_footnote,
            None,
        )
        self.commands.register(
            "format.insert_table",
            "Insert Table",
            self.format_insert_table,
            None,
        )
        self.commands.register(
            "edit.sort_lines_ascending",
            "Sort Lines Ascending",
            self.sort_lines_ascending,
            None,
        )
        self.commands.register(
            "edit.sort_lines_descending",
            "Sort Lines Descending",
            self.sort_lines_descending,
            None,
        )
        self.commands.register(
            "edit.reverse_lines",
            "Reverse Lines",
            self.reverse_lines,
            self._binding_for("edit.reverse_lines"),
        )
        self.commands.register(
            "edit.remove_duplicate_lines",
            "Remove Duplicate Lines",
            self.remove_duplicate_lines,
            None,
        )
        self.commands.register(
            "edit.quote_lines",
            "Quote Lines",
            self.quote_lines,
            self._binding_for("edit.quote_lines"),
        )
        self.commands.register(
            "edit.unquote_lines",
            "Unquote Lines",
            self.unquote_lines,
            self._binding_for("edit.unquote_lines"),
        )
        self.commands.register(
            "edit.duplicate_selection",
            "Duplicate Selection",
            self.duplicate_selection,
            None,
        )
        self.commands.register(
            "edit.select_chunk",
            "Select Chunk",
            self.select_chunk,
            self._binding_for("edit.select_chunk"),
        )
        self.commands.register(
            "edit.trim_trailing_whitespace",
            "Trim Trailing Whitespace",
            self.trim_trailing_whitespace,
            None,
        )
        self.commands.register(
            "edit.normalize_whitespace",
            "Normalize Whitespace",
            self.normalize_whitespace,
            None,
        )
        self.commands.register(
            "edit.convert_indentation_to_spaces",
            "Convert Indentation to Spaces",
            self.convert_indentation_to_spaces,
            None,
        )
        self.commands.register(
            "edit.convert_indentation_to_tabs",
            "Convert Indentation to Tabs",
            self.convert_indentation_to_tabs,
            None,
        )
        self.commands.register(
            "help.context_help",
            "Context Help: Current Mode Keys",
            self.announce_context_mode_shortcuts,
            None,
        )
        self.commands.register(
            "document.summary",
            "Document Summary",
            self.show_document_summary,
            None,
        )
        self.commands.register(
            "navigate.go_to_anything",
            "Go to Anything",
            self.open_go_to_anything,
            None,
        )
        self.commands.register(
            "help.key_cheatsheet",
            "Key Cheatsheet",
            self.open_key_cheatsheet,
            None,
        )
        self.commands.register(
            "view.announce_contrast",
            "Announce Contrast Ratio",
            self.announce_contrast_ratio,
            None,
        )
        self.commands.register(
            "help.why_unavailable",
            "Why Is This Unavailable?",
            self.explain_unavailable_feature,
            None,
        )
        self.commands.register(
            "edit.magic_paste",
            "Magic Paste",
            self.magic_paste,
            None,
        )
        # Copy Tray per-slot commands — registered here (not through the power-tools
        # manifest) so they share the explicit menu-ID arrays and avoid duplicate entries.
        for _ct_n in range(1, 13):
            self.commands.register(
                f"edit.copy_to_tray_{_ct_n}",
                f"Copy to Tray Slot {_ct_n}",
                (lambda _n=_ct_n: lambda: self.copy_to_tray_slot(_n))(),
                self._binding_for(f"edit.copy_to_tray_{_ct_n}"),
            )
            self.commands.register(
                f"edit.paste_from_tray_{_ct_n}",
                f"Paste from Tray Slot {_ct_n}",
                (lambda _n=_ct_n: lambda: self.paste_from_tray_slot(_n))(),
                self._binding_for(f"edit.paste_from_tray_{_ct_n}"),
            )
        self.commands.register(
            "edit.copy_to_next_slot",
            "Copy to Next Empty Tray Slot",
            self.copy_to_next_slot,
            self._binding_for("edit.copy_to_next_slot"),
        )
        self.commands.register(
            "edit.search_tray_slots",
            "Search Copy Tray Slots",
            self.search_tray_slots,
            self._binding_for("edit.search_tray_slots"),
        )
        self._register_power_tools_commands()
        self._register_quillins_commands()

    def _apply_accelerators(self) -> None:
        wx = self._wx
        command_to_menu_id = self._command_to_menu_id_map()
        entries: list[object] = []
        for command_id, menu_id in command_to_menu_id.items():
            binding = self.commands.keybinding_for(command_id)
            parsed = self._parse_keybinding(binding)
            if parsed is None:
                continue
            flags, key_code = parsed
            entries.append(wx.AcceleratorEntry(flags, key_code, menu_id))
        entries.append(wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_F4, self._id_close_document))

        self.frame.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def _reload_global_hotkeys(self) -> None:
        if self._safe_mode:
            return
        self._unregister_global_hotkeys()
        binding = self._binding_for("tools.sticky_note_capture")
        parsed = self._parse_keybinding(binding)
        if parsed is None or not hasattr(self.frame, "RegisterHotKey"):
            return
        flags, key_code = parsed
        try:
            self.frame.RegisterHotKey(int(self._sticky_note_hotkey_id), flags, key_code)
        except Exception:
            self._set_status("Sticky note hotkey could not be registered")

    def _unregister_global_hotkeys(self) -> None:
        if not hasattr(self.frame, "UnregisterHotKey"):
            return
        try:
            self.frame.UnregisterHotKey(int(self._sticky_note_hotkey_id))
        except Exception:
            pass

    def _on_global_hotkey(self, event: object) -> None:
        if event.GetId() == int(self._sticky_note_hotkey_id):
            self.create_sticky_note()
            return
        event.Skip()

    def _command_to_menu_id_map(self) -> dict[str, int]:
        return {
            "file.new": self._id_new,
            "file.open": self._id_open,
            "file.save": self._id_save,
            "file.save_as": self._id_save_as,
            "file.close_document": self._id_close_document,
            "file.save_all": self._id_save_all,
            "file.reload_from_disk": self._id_reload_from_disk,
            "file.restore_backup": self._id_restore_backup,
            "file.page_setup": self._id_page_setup,
            "file.print": self._id_print,
            "window.next_document": self._id_next_document,
            "window.previous_document": self._id_previous_document,
            "view.send_to_tray": self._id_send_to_tray,
            "view.toggle_soft_wrap": self._id_toggle_soft_wrap,
            "view.toggle_find_wrap": self._id_toggle_find_wrap,
            "view.preview": self._id_preview,
            "view.split_preview": self._id_split_preview,
            "view.focus_preview": self._id_focus_preview,
            "view.browser_preview": self._id_browser_preview,
            "tools.read_aloud_generate_audio": self._id_read_aloud_generate_audio,
            "tools.ai_hub": self._id_ai_hub,
            "tools.ai_assistant": self._id_ai_assistant,
            "tools.ai_prompt_studio": self._id_ai_prompt_studio,
            "tools.ai_agent_center": self._id_ai_agent_center,
            "tools.ai_accessibility_agent": self._id_ai_accessibility_agent,
            "tools.prompt_library": self._id_prompt_library,
            "tools.skill_library": self._id_skill_library,
            "tools.check_grammar_ai": self._id_check_grammar_ai,
            "tools.ask_quill_chat": self._id_ask_quill_chat,
            "tools.ai_model": self._id_ai_model,
            "tools.ai_session_browser": self._id_ai_session_browser,
            "tools.ai_connection": self._id_ai_connection,
            "tools.ai_rewrite_selection": self._id_ai_rewrite_selection,
            "tools.ai_summarize_selection": self._id_ai_summarize_selection,
            "tools.ai_continue_writing": self._id_ai_continue_writing,
            "tools.ai_fix_grammar": self._id_ai_fix_grammar,
            "tools.train_writing_style": self._id_train_style,
            "tools.writing_instructions": self._id_writing_instructions,
            "app.exit": self._id_exit,
            "app.command_palette": self._id_palette,
            "app.preferences": self._id_preferences,
            "app.menu_editor": self._id_menu_editor,
            "edit.undo": self._id_undo,
            "edit.redo": self._id_redo,
            "edit.toggle_extend_selection_mode": self._id_toggle_extend_selection_mode,
            "edit.start_selection": self._id_start_selection,
            "edit.complete_selection": self._id_complete_selection,
            "edit.reselect": self._id_reselect,
            "edit.go_to_start_of_selection": self._id_go_to_start_of_selection,
            "edit.copy_all": self._id_copy_all,
            "edit.unselect_all": self._id_unselect_all,
            "edit.say_selected": self._id_say_selected,
            "edit.read_all": self._id_read_all,
            "edit.insert_link": self._id_insert_link,
            "edit.follow_link": self._id_follow_link,
            "edit.find": self._id_find,
            "edit.find_next": self._id_find_next,
            "edit.find_previous": self._id_find_previous,
            "edit.find_all_matches": self._id_find_all_matches,
            "edit.replace": self._id_replace,
            "edit.replace_all": self._id_replace_all,
            "edit.select_to_start_of_line": self._id_select_to_start_of_line,
            "edit.select_to_end_of_line": self._id_select_to_end_of_line,
            "edit.select_to_start_of_document": self._id_select_to_start_of_document,
            "edit.select_to_end_of_document": self._id_select_to_end_of_document,
            "edit.set_mark": self._id_set_mark,
            "edit.pop_mark": self._id_pop_mark,
            "edit.exchange_point_mark": self._id_exchange_point_mark,
            "edit.list_marks": self._id_list_marks,
            "edit.set_named_mark": self._id_set_named_mark,
            "edit.jump_to_named_mark": self._id_jump_to_named_mark,
            "edit.open_review_buffer": self._id_open_review_buffer,
            "navigate.go_to_line": self._id_go_to_line,
            "navigate.go_to_page": self._id_go_to_page,
            "navigate.list_bookmarks": self._id_list_bookmarks,
            "navigate.back_location": self._id_back_location,
            "navigate.forward_location": self._id_forward_location,
            "navigate.outline_navigator": self._id_outline_navigator,
            "navigate.heading_organizer": self._id_heading_organizer,
            "navigate.match_bracket": self._id_match_bracket,
            "navigate.next_token": self._id_next_token,
            "navigate.previous_token": self._id_previous_token,
            "navigate.set_language": self._id_set_language,
            "navigate.next_structure": self._id_next_structure,
            "navigate.previous_structure": self._id_previous_structure,
            "navigate.next_region": self._id_next_region,
            "navigate.previous_region": self._id_previous_region,
            "tools.word_count": self._id_word_count,
            "tools.sticky_notes": self._id_sticky_notes,
            "tools.sticky_note_capture": self._id_new_sticky_note,
            "tools.spell_check_dialog": self._id_spell_check,
            "tools.previous_misspelling": self._id_previous_misspelling,
            "tools.next_misspelling": self._id_next_misspelling,
            "tools.misspelling_list": self._id_misspelling_list,
            "tools.thesaurus": self._id_thesaurus,
            "tools.dictionary_status": self._id_dictionary_status,
            "tools.announcement_backend": self._id_announcement_backend,
            "tools.announcement_trace_toggle": self._id_toggle_announcement_trace,
            "tools.sound_toggle": self._id_toggle_sound,
            "tools.sound_events": self._id_sound_events,
            "tools.watch_folder_toggle": self._id_watch_folder_toggle,
            "tools.watch_folder_settings": self._id_watch_folder_settings,
            "tools.watch_folder_status": self._id_watch_folder_status,
            "tools.document_intake_report": self._id_document_intake_report,
            "tools.review_extraction_quality": self._id_review_extraction_quality,
            "tools.report_bad_extraction": self._id_report_bad_extraction,
            "tools.pandoc_wizard": self._id_pandoc_wizard,
            "tools.external_tools": self._id_external_tools,
            "tools.compare_with_file": self._id_compare_with_file,
            "tools.compare_open_documents": self._id_compare_open_documents,
            "tools.compare_next_difference": self._id_compare_next_difference,
            "tools.compare_previous_difference": self._id_compare_previous_difference,
            "tools.compare_announce_difference": self._id_compare_announce_difference,
            "tools.compare_difference_list": self._id_compare_difference_list,
            "tools.compare_toggle_sync": self._id_compare_toggle_sync,
            "tools.compare_options": self._id_compare_options,
            "tools.compare_create_summary": self._id_compare_create_summary,
            "tools.compare_copy_current_difference": self._id_compare_copy_current,
            "tools.compare_copy_all_differences": self._id_compare_copy_all,
            "tools.start_macro_recording": self._id_start_macro_recording,
            "tools.stop_macro_recording": self._id_stop_macro_recording,
            "tools.play_last_macro": self._id_play_last_macro,
            "tools.manage_macros": self._id_manage_macros,
            "tools.glow_audit_document": self._id_glow_audit_document,
            "tools.glow_audit_selection": self._id_glow_audit_selection,
            "tools.glow_fix_document": self._id_glow_fix_document,
            "tools.glow_fix_selection": self._id_glow_fix_selection,
            "help.save_diagnostics": self._id_save_diagnostics,
            "help.report_bug": self._id_report_bug,
            "help.open_logs_folder": self._id_open_logs_folder,
            "help.open_diagnostics_folder": self._id_open_diagnostics_folder,
            "help.status_page": self._id_help_status_page,
            "help.startup_wizard": self._id_profile_onboarding,
            "help.context_help": self._id_announce_context_shortcuts,
            "whisperer.about": self._id_whisperer_about,
            "whisperer.model_manager": self._id_bw_model_manager,
            "whisperer.model_status": self._id_bw_model_status,
            "whisperer.model_recommend": self._id_bw_model_recommend,
            "whisperer.toggle_parakeet": self._id_bw_toggle_parakeet,
            "whisperer.check_faster_whisper": self._id_bw_check_faster_whisper,
            "whisperer.provider_center": self._id_bw_provider_center,
            "whisperer.provider_status": self._id_bw_provider_status,
            "whisperer.provider_recommend": self._id_bw_provider_recommend,
            "whisperer.provider_select": self._id_bw_provider_select,
            "whisperer.readiness_check": self._id_bw_readiness_check,
            "whisperer.capability_matrix": self._id_bw_capability_matrix,
            "whisperer.download_queue": self._id_bw_download_queue,
            "tools.yaml_structure_editor": self._id_yaml_structure_editor,
            "edit.copy_with_source": self._id_copy_with_source,
            "edit.select_line": self._id_select_line,
            "format.decrease_heading_level": self._id_decrease_heading_level,
            "format.increase_heading_level": self._id_increase_heading_level,
            "format.style_headings": self._id_style_headings,
            "format.bold": self._id_format_bold,
            "format.italic": self._id_format_italic,
            "format.upper_case": self._id_upper_case,
            "format.lower_case": self._id_lower_case,
            "format.heading_1": self._id_heading_1,
            "format.heading_2": self._id_heading_2,
            "format.heading_3": self._id_heading_3,
            "format.heading_4": self._id_heading_4,
            "format.heading_5": self._id_heading_5,
            "format.heading_6": self._id_heading_6,
            "format.toggle_line_comment": self._id_toggle_line_comment,
            "format.toggle_block_comment": self._id_toggle_block_comment,
            "format.indent": self._id_indent,
            "format.outdent": self._id_outdent,
            "format.move_line_up": self._id_move_line_up,
            "format.move_line_down": self._id_move_line_down,
            "format.duplicate_line": self._id_duplicate_line,
            "format.delete_line": self._id_delete_line,
            "format.insert_html_tag": self._id_insert_html_tag,
            "format.insert_markdown_tag": self._id_insert_markdown_tag,
            "format.insert_snippet": self._id_insert_snippet,
            "format.manage_snippets": self._id_manage_snippets,
            "format.expand_abbreviation": self._id_expand_abbreviation,
            "format.manage_abbreviations": self._id_manage_abbreviations,
            "format.toggle_abbreviation_expansion": self._id_toggle_abbreviation_expansion,
            "edit.word_prediction": self._id_word_prediction,
            # Copy Tray
            "edit.open_copy_tray": self._id_open_copy_tray,
            "edit.clear_all_tray_slots": self._id_clear_all_tray_slots,
            "edit.copy_to_next_slot": self._id_copy_to_next_slot,
            "edit.search_tray_slots": self._id_search_tray_slots,
            **{f"edit.copy_to_tray_{i}": self._id_copy_tray_slots[i - 1] for i in range(1, 13)},
            **{f"edit.paste_from_tray_{i}": self._id_paste_tray_slots[i - 1] for i in range(1, 13)},
        }

    def _on_command_run(self, command_id: str) -> None:
        if self._command_should_commit_extend_selection(command_id):
            self._commit_pending_extend_selection()
        self._record_macro_step(command_id)
        record_diagnostic_event("command", command_id)

    def _on_menu_command_activity(self, event: object) -> None:
        command_id = None
        command_by_menu_id = {
            menu_id: cid for cid, menu_id in self._command_to_menu_id_map().items()
        }
        get_id = getattr(event, "GetId", None)
        if callable(get_id):
            command_id = command_by_menu_id.get(get_id())
        if command_id is not None:
            if self._command_should_commit_extend_selection(command_id):
                self._commit_pending_extend_selection()
            self._record_macro_step(command_id)
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def _parse_keybinding(self, keybinding: str | None) -> tuple[int, int] | None:
        if not keybinding:
            return None
        wx = self._wx
        parts = [part.strip() for part in keybinding.split("+") if part.strip()]
        if not parts:
            return None

        flags = 0
        for modifier in parts[:-1]:
            lowered = modifier.lower()
            if lowered == "ctrl":
                flags |= wx.ACCEL_CTRL
            elif lowered == "shift":
                flags |= wx.ACCEL_SHIFT
            elif lowered == "alt":
                flags |= wx.ACCEL_ALT
            else:
                return None

        key_token = parts[-1].upper()
        if len(key_token) == 1:
            return flags, ord(key_token)

        function_keys: dict[str, int] = {
            f"F{index}": getattr(wx, f"WXK_F{index}") for index in range(1, 13)
        }
        named_keys: dict[str, int] = {
            "ENTER": wx.WXK_RETURN,
            "TAB": wx.WXK_TAB,
            "SPACE": wx.WXK_SPACE,
            "ESC": wx.WXK_ESCAPE,
            "ESCAPE": wx.WXK_ESCAPE,
            "DELETE": wx.WXK_DELETE,
            "BACKSPACE": wx.WXK_BACK,
            "HOME": wx.WXK_HOME,
            "END": wx.WXK_END,
            "LEFT": wx.WXK_LEFT,
            "RIGHT": wx.WXK_RIGHT,
        }
        if key_token in function_keys:
            return flags, function_keys[key_token]
        if key_token in named_keys:
            return flags, named_keys[key_token]
        return None

    def _bind_events(self) -> None:
        wx = self._wx
        if self._tab_control_visible:
            self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_notebook_page_changed)
            self.notebook.Bind(wx.EVT_CONTEXT_MENU, self._on_notebook_context_menu)
            self.notebook.Bind(wx.EVT_KEY_DOWN, self._on_notebook_key_down)
        menu_open_event = getattr(wx, "EVT_MENU_OPEN", None)
        if menu_open_event is not None:
            self.frame.Bind(menu_open_event, self._on_menu_open)
        menu_close_event = getattr(wx, "EVT_MENU_CLOSE", None)
        if menu_close_event is not None:
            self.frame.Bind(menu_close_event, self._on_menu_close)
        self.frame.Bind(wx.EVT_ACTIVATE, self._on_frame_activate)
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.statusbar.Bind(wx.EVT_CONTEXT_MENU, self._on_statusbar_context_menu)
        self.frame.Bind(wx.EVT_CONTEXT_MENU, self._on_frame_context_menu)
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        self.frame.Bind(wx.EVT_ICONIZE, self._on_iconize)
        self.frame.Bind(wx.EVT_HOTKEY, self._on_global_hotkey)
        self._apply_soft_wrap(self.settings.soft_wrap)

    def _menu_updates_allowed(self) -> bool:
        return int(getattr(self, "_menu_open_depth", 0)) <= 0

    def _request_menu_refresh(self) -> None:
        self._pending_menu_refresh = True
        if not self._menu_updates_allowed():
            return
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(self._flush_pending_menu_refresh)
            return
        self._flush_pending_menu_refresh()

    def _flush_pending_menu_refresh(self) -> None:
        if not getattr(self, "_pending_menu_refresh", False):
            return
        if not self._menu_updates_allowed():
            return
        self._pending_menu_refresh = False
        self._refresh_recent_menu()
        self._refresh_sessions_menu()
        self._refresh_contextual_menu_items()
        self._sync_announcement_backend_menu_state()
        self._apply_watch_folder_menu_state()
        self._apply_ai_menu_enabled()

    def _on_menu_open(self, event: object) -> None:
        self._menu_open_depth += 1
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def _on_menu_close(self, event: object) -> None:
        self._menu_open_depth = max(0, self._menu_open_depth - 1)
        if self._menu_open_depth == 0 and getattr(self, "_pending_menu_refresh", False):
            self._request_menu_refresh()
        # After the menu closes, wx may return focus to the splitter or panel
        # instead of the editor, causing JAWS to announce "splitter window" /
        # "panel".  Redirect to the editor after the event loop has dispatched
        # any command that the menu item triggered (#170).
        if self._menu_open_depth == 0:
            self._wx.CallAfter(self._return_focus_to_editor)
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def _on_frame_activate(self, event: object) -> None:
        # On first open or Alt-Tab, wx may land focus on the splitter or
        # panel.  Redirect to the editor so JAWS announces the document (#170).
        active = getattr(event, "GetActive", lambda: True)()
        if active:
            self._wx.CallAfter(self._return_focus_to_editor)
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def _apply_silent_accessible(self, widget: object) -> None:
        """Replace a layout container's built-in accessible so screen readers
        skip it in the ancestor context chain (#170)."""
        cls = self._silent_layout_cls
        if cls is not None:
            try:
                widget.SetAccessible(cls(widget))  # type: ignore[attr-defined]
            except Exception:
                pass

    def _on_container_focus(self, event: object) -> None:
        # Fires when focus lands directly on a layout container (splitter or
        # panel).  Redirect synchronously to the active editor so screen readers
        # announce the document rather than the container class (#170).
        # Synchronous (not CallAfter) so the first container in the startup
        # focus chain grabs the editor before subsequent containers even get
        # focus -- CallAfter was too late and caused NVDA to announce all four.
        if getattr(self, "_in_container_focus_redirect", False):
            skip = getattr(event, "Skip", None)
            if callable(skip):
                skip()
            return
        editor = getattr(self, "editor", None)
        if editor is not None:
            self._in_container_focus_redirect = True
            try:
                editor.SetFocus()
            finally:
                self._in_container_focus_redirect = False
            return  # do not skip -- we redirected, container should not keep focus
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def _return_focus_to_editor(self) -> None:
        """Redirect focus from layout containers to the editor (#170).

        SplitterWindow and Panel are not interactive; if wx routes focus to
        them (after menu close or frame activation), JAWS announces the control
        class instead of the document.  Only redirects when focus is on a known
        layout container so command handlers that set their own focus target are
        not disturbed.
        """
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        focused = self._wx.Window.FindFocus()
        if focused is None:
            return
        containers: set[object] = {
            getattr(self, "_main_splitter", None),
            getattr(self, "_documents_panel", None),
            getattr(self, "statusbar", None),
            getattr(getattr(self, "_entries_panel", None), "panel", None),
        }
        for tab in getattr(self, "_document_tabs", []):
            for attr in ("splitter", "panel"):
                obj = getattr(tab, attr, None)
                if obj is not None:
                    containers.add(obj)
        containers.discard(None)
        if focused in containers:
            editor.SetFocus()

    def _bind_editor_events(self, editor: object) -> None:
        binder = getattr(editor, "bind_editor_events", None)
        if callable(binder):
            binder(self)
            return
        wx = self._wx
        editor.Bind(wx.EVT_TEXT, self._on_text_changed)
        editor.Bind(wx.EVT_CHAR_HOOK, self._on_editor_char_hook)
        editor.Bind(wx.EVT_KEY_DOWN, self._on_editor_key_down)
        editor.Bind(wx.EVT_KEY_UP, self._on_editor_key_up)
        editor.Bind(wx.EVT_LEFT_UP, self._on_editor_caret_activity)
        editor.Bind(wx.EVT_SET_FOCUS, self._on_editor_caret_activity)
        editor.Bind(wx.EVT_CONTEXT_MENU, self._on_editor_context_menu)

    def _on_editor_char_hook(self, event: object) -> None:
        wx = self._wx
        if self._maybe_describe_key(event):
            return
        if (
            event.ControlDown()
            and not event.AltDown()
            and not event.ShiftDown()
            and event.GetKeyCode() in (ord("K"), ord("k"), 11)
        ):
            self.insert_link()
            return
        if event.GetKeyCode() == wx.WXK_ESCAPE and self._extend_selection_mode:
            event.Skip()
            return
        if self._maybe_autoformat_char(event):
            return
        event.Skip()

    def _maybe_autoformat_char(self, event: object) -> bool:
        """Apply SET-4 typography autoformat to a typed character.

        Returns ``True`` when the keystroke was consumed (the replacement was
        inserted directly), ``False`` to let the editor handle it normally.
        """
        if event.ControlDown() or event.AltDown():
            return False
        try:
            typed = chr(event.GetUnicodeKey())
        except (ValueError, OverflowError):
            return False
        editor = self.editor
        if editor is None:
            return False
        smart_quotes = bool(getattr(self.settings, "autoformat_smart_quotes", False))
        dashes = bool(getattr(self.settings, "autoformat_dashes", False))
        if typed in {'"', "'"} and smart_quotes:
            position = editor.GetInsertionPoint()
            preceding = editor.GetRange(position - 1, position) if position > 0 else ""
            replacement = smart_quote_for(preceding, typed)
            if replacement != typed:
                editor.WriteText(replacement)
                return True
            return False
        if typed == "-" and dashes:
            position = editor.GetInsertionPoint()
            preceding = editor.GetRange(position - 1, position) if position > 0 else ""
            if is_dash_merge(preceding):
                editor.Replace(position - 1, position, EM_DASH)
                editor.SetInsertionPoint(position - 1 + len(EM_DASH))
                return True
        return False

    def _create_document_tab(self, document: Document, select: bool = True) -> int:
        wx = self._wx
        panel = wx.Panel(self.notebook)
        panel.SetName("Editor panel")
        panel.Bind(wx.EVT_SET_FOCUS, self._on_container_focus)
        self._apply_silent_accessible(panel)
        # The editor lives in a splitter so a live preview can be shown to its
        # right (View → Preview Side by Side). It starts unsplit (editor only).
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE | wx.SP_3DSASH)
        splitter.SetName("Editor area")
        splitter.Bind(wx.EVT_SET_FOCUS, self._on_container_focus)
        self._apply_silent_accessible(splitter)
        splitter.SetMinimumPaneSize(160)
        editor = wx.TextCtrl(
            splitter,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL,
        )
        editor.SetName("Document")
        splitter.Initialize(editor)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.EXPAND)
        panel.SetSizer(sizer)
        if document.text:
            editor.ChangeValue(document.text)
        self._bind_editor_events(editor)
        tab = _DocumentTab(panel=panel, editor=editor, document=document, splitter=splitter)
        self._document_tabs.append(tab)
        index = self.notebook.GetPageCount()
        self.notebook.AddPage(panel, document.name, select=select)
        if select:
            self._active_tab_index = index
            self.editor = editor
            self.document = document
            self._apply_statusbar_layout()
            self._refresh_title()
            self._refresh_read_only_state()
            self._maybe_auto_side_preview(tab)
        self._refresh_sessions_menu()
        return index

    def _create_tab_host(self, show_tab_control: bool) -> object:
        wx = self._wx
        if show_tab_control:
            return wx.Notebook(self._documents_panel)
        simplebook = getattr(wx, "Simplebook", None)
        if simplebook is not None:
            return simplebook(self._documents_panel)
        return wx.Notebook(self._documents_panel)

    def _rebuild_tab_host(self, show_tab_control: bool) -> None:
        if show_tab_control == self._tab_control_visible:
            return
        wx = self._wx
        old_host = self.notebook
        active_index = self._current_tab_index()
        self._documents_sizer.Detach(old_host)
        new_host = self._create_tab_host(show_tab_control)
        self.notebook = new_host
        self._tab_control_visible = show_tab_control
        for index, tab in enumerate(self._document_tabs):
            tab.panel.Reparent(new_host)
            new_host.AddPage(tab.panel, tab.document.name, select=False)
            self._set_tab_page_text(index, tab.document.name)
        self._documents_sizer.Add(new_host, 1, wx.EXPAND)
        old_host.Destroy()
        if self._tab_control_visible:
            new_host.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_notebook_page_changed)
            new_host.Bind(wx.EVT_CONTEXT_MENU, self._on_notebook_context_menu)
            new_host.Bind(wx.EVT_KEY_DOWN, self._on_notebook_key_down)
        if 0 <= active_index < len(self._document_tabs):
            self._select_tab(active_index)
        self._documents_panel.Layout()
        self.frame.Layout()

    def _set_tab_page_text(self, index: int, title: str) -> None:
        setter = getattr(self.notebook, "SetPageText", None)
        if callable(setter) and 0 <= index < self.notebook.GetPageCount():
            setter(index, title)

    def _tab_page_title(self, index: int) -> str:
        if index < 0 or index >= len(self._document_tabs):
            return "this tab"
        return self._document_tabs[index].document.name or "this tab"

    def _on_notebook_page_changed(self, event: object) -> None:
        selection = self.notebook.GetSelection()
        if selection != self._active_tab_index:
            self._activate_tab(selection)
        event.Skip()

    def _on_notebook_key_down(self, event: object) -> None:
        wx = self._wx
        key_code = event.GetKeyCode()
        return_keys = {
            getattr(wx, "WXK_RETURN", 13),
            getattr(wx, "WXK_NUMPAD_ENTER", 13),
            getattr(wx, "WXK_SPACE", 32),
        }
        if key_code in return_keys:
            selection = self.notebook.GetSelection()
            if selection != getattr(wx, "NOT_FOUND", -1):
                self._activate_tab(selection)
                self.editor.SetFocus()
                self._set_status(f"Focused document {self.document.name}")
                return
        tab_key = getattr(wx, "WXK_TAB", 9)
        if key_code == tab_key and not event.ShiftDown():
            self.editor.SetFocus()
            self._set_status(f"Focused document {self.document.name}")
            return
        event.Skip()

    def _on_char_hook(self, event: object) -> None:
        key_code = event.GetKeyCode()
        if (
            event.ControlDown()
            and not event.AltDown()
            and not event.ShiftDown()
            and key_code in (ord("K"), ord("k"), 11)
            and self._active_tab() is not None
        ):
            self.insert_link()
            return
        # Ctrl-W closes the side preview unconditionally — even when the WebView
        # holds native focus.  WebView2 captures its own keyboard events and does
        # not forward them to wx, so this must be handled at the frame level
        # before the browser control can consume the keystroke.
        if (
            event.ControlDown()
            and not event.AltDown()
            and not event.ShiftDown()
            and key_code in (ord("W"), ord("w"), 23)
        ):
            tab = self._active_tab()
            splitter = getattr(tab, "splitter", None) if tab is not None else None
            if splitter is not None and splitter.IsSplit():
                self.toggle_side_preview()
                return
        if not self._focus_is_in_document_surface():
            # Modal dialogs (including WebView-hosted HTML surfaces) should
            # receive keys directly. If browse mode was active in the editor,
            # drop it silently when focus leaves the document surface.
            self._quill_key_mode_active = False
            self._quill_key_prefix_pending = False
            self._quill_key_prefix_started_at = 0.0
            self._quill_key_mode_started_at = 0.0
            event.Skip()
            return
        if self._handle_quill_key_mode_event(event):
            return
        event.Skip()

    def _focus_is_in_document_surface(self) -> bool:
        wx = self._wx
        finder = getattr(getattr(wx, "Window", None), "FindFocus", None)
        if not callable(finder):
            return False
        focus = finder()
        if focus is None:
            return False
        document_surface = getattr(self, "_documents_panel", None)
        node = focus
        while node is not None:
            if node is document_surface or node is self.notebook or node is self.editor:
                return True
            get_parent = getattr(node, "GetParent", None)
            node = get_parent() if callable(get_parent) else None
        return False

    def _activate_tab(self, index: int) -> None:
        if index < 0 or index >= len(self._document_tabs):
            return
        self._stop_external_change_watcher()
        tab = self._document_tabs[index]
        self._active_tab_index = index
        self._browse_navigation_cache = None
        self.editor = tab.editor
        self.document = tab.document
        tab._indent_tone_last_level = -1  # reset per-tab indent tone cache on switch
        if not getattr(tab, "_language_profile_pinned", False):
            tab._language_profile = get_profile_for_path(tab.document.path)
        self._schedule_browse_prewarm(force=True)
        if self.settings.persistent_undo:
            if self.document.path is not None:
                self._load_persistent_undo_state(self.document.path, self.editor.GetValue())
            else:
                self._persistent_undo_history = [self.editor.GetValue()]
                self._persistent_undo_index = 0
        self._apply_statusbar_layout()
        self._refresh_title()
        self._refresh_contextual_menu_items()
        self._refresh_sessions_menu()
        self._refresh_read_only_state()
        self._maybe_auto_side_preview(tab)
        self._start_external_change_watcher()

    def _maybe_auto_side_preview(self, tab) -> None:
        """Auto-show the side-by-side preview for previewable (Markdown/HTML)
        documents when the setting is on, so the user doesn't have to ask each
        time. Plain text is left alone, and an explicit toggle still wins."""
        if not getattr(self.settings, "auto_side_preview", True):
            return
        splitter = getattr(tab, "splitter", None)
        if splitter is None or splitter.IsSplit():
            return
        text = tab.editor.GetValue()
        if guess_preview_kind(tab.document.path, text) == "plain":
            return
        # Defer so the splitter has its real size before we set the sash.
        self._wx.CallAfter(self._show_side_preview_for, tab)

    def _show_side_preview_for(self, tab) -> None:
        splitter = getattr(tab, "splitter", None)
        if splitter is None or splitter.IsSplit():
            return
        if tab.preview is None:
            from quill.ui.preview_dialog import SidePreview

            tab.preview = SidePreview(splitter, on_return=self._focus_editor_from_preview)
        sash = max(splitter.GetClientSize().x // 2, 200)
        splitter.SplitVertically(tab.editor, tab.preview.control, sash)
        self._update_side_preview(tab)

    def _start_ipc_poll(self) -> None:
        wx = self._wx
        timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_ipc_timer, timer)
        timer.Start(800)
        self._ipc_timer = timer

    def _on_ipc_timer(self, _event: object) -> None:
        requests = drain_open_requests()
        if not requests:
            return
        for candidate in requests:
            if candidate is None:
                continue
            if candidate.path.exists() and candidate.path.is_file():
                self._handle_shell_request(candidate)
        self.frame.Show(True)
        self.frame.Raise()
        self.frame.RequestUserAttention()

    def _handle_shell_request(self, candidate: object) -> None:
        """Dispatch a single IPC open request by its "Send to Quill" action.

        ``open`` (and any unknown action) loads the file in the editor. ``ocr``
        and ``ocr-structured`` run local OCR on an image or PDF. ``read`` opens
        the file and starts reading it aloud. The image OCR helpers live in
        :class:`ImageCaptureMixin` (OCR-3).
        """
        action = str(getattr(candidate, "action", "open") or "open").strip().lower()
        path = candidate.path
        if action in {"ocr", "ocr-structured"}:
            self._run_ocr_on_path(path, confirm=False, structured=action == "ocr-structured")
            return
        if action == "read":
            self.open_file(path, line=candidate.line, column=candidate.column)
            self.toggle_read_aloud()
            return
        if action == "compare":
            diff_with = getattr(candidate, "diff_with", None)
            if diff_with is not None:
                self.open_file(path)
                self.compare_start_with_file(diff_with)
                return
        self.open_file(path, line=candidate.line, column=candidate.column)

    def _on_text_changed(self, _event: object) -> None:
        if self._voice_command_guard:
            return
        if (
            not self._abbreviation_expansion_guard
            and getattr(self.settings, "abbreviation_expansion", True)
            and self._expand_abbreviation_if_match()
        ):
            return
        if (
            not self._snippet_expansion_guard
            and self.settings.snippet_trigger_expansion
            and self._expand_snippet_trigger_if_match()
        ):
            return
        self._sync_editor_change("Modified")

    def _sync_editor_change(self, status: str) -> None:
        self._browse_navigation_cache = None
        self.document.set_text(self.editor.GetValue())
        self._schedule_browse_prewarm()
        if not self._suspend_persistent_undo:
            self._record_persistent_undo_state(self.document.text)
        if self.settings.spellcheck_as_you_type:
            self._announce_spellcheck_hint()
        if self._dictation.state == "listening" and self.settings.voice_commands_enabled:
            self._schedule_voice_command_scan()
        self._refresh_intellisense_popup()
        self._refresh_side_preview()
        self._refresh_browser_preview()
        self._maybe_autosave()
        self._refresh_title()
        self._refresh_contextual_menu_items()
        # Quiet: this fires on every keystroke; speaking "Modified" each time is
        # noise for a screen reader (it already echoes the typed character).
        self._set_status_quiet(status)

    def _on_csv_surface_changed(self) -> None:
        self._sync_editor_change("Modified")

    def _expand_snippet_trigger_if_match(self) -> bool:
        if self.editor.GetSelection()[0] != self.editor.GetSelection()[1]:
            return False
        text = self.editor.GetValue()
        caret = self.editor.GetInsertionPoint()
        if caret <= 0 or caret > len(text):
            return False
        delimiter = text[caret - 1]
        if delimiter not in {" ", "\n", "\t", ".", ",", ";", ":", "!", "?", ")", "]", "}"}:
            return False
        token_end = caret - 1
        token_start = token_end
        while token_start > 0 and not text[token_start - 1].isspace():
            token_start -= 1
        token = text[token_start:token_end]
        if not token.startswith(";") or len(token) < 2:
            return False
        snippet = find_snippet_by_trigger(self._snippet_library.snippets, token)
        if snippet is None:
            return False
        rendered = self._render_snippet_with_prompts(snippet)
        if rendered is None:
            return False
        before = text[:token_start]
        after = text[token_end:]
        has_cursor_marker = "${cursor}" in snippet.body
        new_text = before + rendered.text + after
        new_caret = token_start + rendered.cursor
        if not has_cursor_marker:
            new_caret += 1
        if new_caret < 0:
            new_caret = 0
        if new_caret > len(new_text):
            new_caret = len(new_text)
        self._snippet_expansion_guard = True
        try:
            self.editor.ChangeValue(new_text)
            self.editor.SetInsertionPoint(new_caret)
            self.editor.SetSelection(new_caret, new_caret)
        finally:
            self._snippet_expansion_guard = False
        self.document.set_text(new_text)
        if not self._suspend_persistent_undo:
            self._record_persistent_undo_state(new_text)
        self._maybe_autosave()
        self._refresh_title()
        self._refresh_contextual_menu_items()
        self._set_status(f'Expanded snippet trigger "{snippet.trigger}".')
        return True

    def _on_editor_caret_activity(self, event: object) -> None:
        self._refresh_statusbar()
        self._maybe_announce_indent()
        self._maybe_play_indent_tone()
        event.Skip()

    def _on_editor_key_up(self, event: object) -> None:
        wx = self._wx
        if event.GetKeyCode() == wx.WXK_INSERT:
            self._insert_key_down = False
        self._on_editor_caret_activity(event)

    def _on_editor_key_down(self, event: object) -> None:
        wx = self._wx
        if (
            event.ControlDown()
            and not event.AltDown()
            and not event.ShiftDown()
            and event.GetKeyCode() in (ord("K"), ord("k"), 11)
        ):
            self.insert_link()
            return
        if event.ControlDown() and event.ShiftDown() and event.GetKeyCode() in (ord("O"), ord("o")):
            self.open_outline_navigator()
            return
        f8_key = getattr(wx, "WXK_F8", None)
        if (
            f8_key is not None
            and event.GetKeyCode() == f8_key
            and self._compare_session is not None
        ):
            if event.ControlDown() and event.ShiftDown():
                self.open_compare_options()
                return
            if event.ControlDown() and event.AltDown():
                self.toggle_compare_synchronization()
                return
            if event.ControlDown():
                self.compare_announce_difference()
                return
            if event.AltDown():
                self.open_compare_difference_list()
                return
            if event.ShiftDown():
                self.compare_previous_difference()
                return
            self.compare_next_difference()
            return
        if event.GetKeyCode() == wx.WXK_INSERT:
            if not self._insert_key_down:
                self._overwrite_mode = not self._overwrite_mode
                self._insert_key_down = True
                self._refresh_statusbar()
            event.Skip()
            return
        if self._handle_intellisense_key_down(event):
            return
        return_keys = {
            key
            for key in (
                getattr(wx, "WXK_RETURN", None),
                getattr(wx, "WXK_NUMPAD_ENTER", None),
            )
            if key is not None
        }
        if (
            return_keys
            and event.GetKeyCode() in return_keys
            and not event.ControlDown()
            and not event.AltDown()
            and not event.ShiftDown()
        ):
            if self._handle_markdown_list_return():
                return
        tab_key = getattr(wx, "WXK_TAB", None)
        if tab_key is not None and event.GetKeyCode() == tab_key:
            self._commit_pending_extend_selection()
            if self._is_caret_on_markdown_list_item():
                if event.ShiftDown():
                    self.format_outdent()
                    self._set_status("Promoted list item")
                else:
                    self.format_indent()
                    self._set_status("Nested list item")
                return
            if event.ShiftDown():
                self.format_outdent()
            else:
                self.format_indent()
            return
        if (
            hasattr(self, "_dictation")
            and self._dictation.state == "listening"
            and event.GetKeyCode() == wx.WXK_ESCAPE
        ):
            self.toggle_dictation()
            return
        space_key = getattr(wx, "WXK_SPACE", None)
        if (
            space_key is not None
            and event.GetKeyCode() == space_key
            and event.ShiftDown()
            and not event.ControlDown()
            and not event.AltDown()
        ):
            _sel_start, _sel_end = self.editor.GetSelection()
            if _sel_start != _sel_end:
                self.say_selected()
                return
        if self._extend_selection_mode and event.GetKeyCode() == wx.WXK_ESCAPE:
            caret = self.editor.GetInsertionPoint()
            self.toggle_extend_selection_mode(False)
            self.editor.SetSelection(caret, caret)
            return
        if not self._extend_selection_mode:
            event.Skip()
            return
        movement_keys = {
            wx.WXK_LEFT,
            wx.WXK_RIGHT,
            wx.WXK_UP,
            wx.WXK_DOWN,
            wx.WXK_HOME,
            wx.WXK_END,
            wx.WXK_PAGEUP,
            wx.WXK_PAGEDOWN,
        }
        if event.GetKeyCode() not in movement_keys:
            self._commit_pending_extend_selection()
            event.Skip()
            return
        if self._extend_selection_anchor is None:
            self._extend_selection_anchor = self.editor.GetInsertionPoint()
        if self._move_extend_selection_caret(event):
            caret = self.editor.GetInsertionPoint()
            self.editor.SetSelection(caret, caret)
            return
        event.Skip()

    def _handle_markdown_list_return(self) -> bool:
        if infer_markup_kind(self.document.path) not in {"markdown", "plain"}:
            return False
        start, end = self.editor.GetSelection()
        if start != end:
            return False
        continuation = continue_markdown_list(
            self.editor.GetValue(), self.editor.GetInsertionPoint()
        )
        if continuation is None:
            return False
        self._replace_document_text(continuation.text)
        self.document.set_text(continuation.text)
        self.editor.SetInsertionPoint(continuation.caret)
        self.editor.SetSelection(continuation.caret, continuation.caret)
        if continuation.exited_list:
            self._set_status("Exited list")
        else:
            self._set_status("Continued list item")
        return True

    def _is_caret_on_markdown_list_item(self) -> bool:
        if infer_markup_kind(self.document.path) not in {"markdown", "plain"}:
            return False
        selection_start, selection_end = self.editor.GetSelection()
        if selection_start != selection_end:
            return False
        text = self.editor.GetValue()
        line_start, line_end = line_span(text, self.editor.GetInsertionPoint())
        line = text[line_start:line_end].strip()
        return bool(re.match(r"^(?:[-+*]|\d+[.)])\s+", line))

    def _apply_extend_selection(self) -> None:
        if not self._extend_selection_mode or self._extend_selection_anchor is None:
            return
        caret = self.editor.GetInsertionPoint()
        start = min(self._extend_selection_anchor, caret)
        end = max(self._extend_selection_anchor, caret)
        self.editor.SetSelection(start, end)
        if start != end:
            self._last_selection = (start, end)

    def _has_pending_extend_selection(self) -> bool:
        if not self._extend_selection_mode or self._extend_selection_anchor is None:
            return False
        selection_start, selection_end = self.editor.GetSelection()
        if selection_start != selection_end:
            return False
        return self.editor.GetInsertionPoint() != self._extend_selection_anchor

    def _commit_pending_extend_selection(self) -> bool:
        if not self._has_pending_extend_selection():
            return False
        self._apply_extend_selection()
        return True

    def _command_should_commit_extend_selection(self, command_id: str) -> bool:
        if command_id in self._EXTEND_SELECTION_ACTION_COMMANDS:
            return True
        if command_id in self._EXTEND_SELECTION_ACTION_EXEMPT_COMMANDS:
            return False
        return command_id.startswith(self._EXTEND_SELECTION_ACTION_COMMAND_PREFIXES)

    def _move_extend_selection_caret(self, event: object) -> bool:
        wx = self._wx
        text = self.editor.GetValue()
        caret = self.editor.GetInsertionPoint()
        key_code = event.GetKeyCode()
        line_starts = [0]
        for index, character in enumerate(text):
            if character == "\n":
                line_starts.append(index + 1)

        def line_index_for_position(position: int) -> int:
            for index in range(1, len(line_starts)):
                if line_starts[index] > position:
                    return index - 1
            return len(line_starts) - 1

        def line_limit(index: int) -> int:
            if index + 1 < len(line_starts):
                return line_starts[index + 1] - 1
            return len(text)

        def move_vertical(delta: int) -> bool:
            current_line = line_index_for_position(caret)
            target_line = max(0, min(current_line + delta, len(line_starts) - 1))
            if target_line == current_line:
                return False
            column = caret - line_starts[current_line]
            target = min(line_starts[target_line] + column, line_limit(target_line))
            self.editor.SetInsertionPoint(target)
            return True

        def move_word(reverse: bool) -> bool:
            if not text:
                return False
            target = caret
            if reverse:
                while target > 0 and text[target - 1].isspace():
                    target -= 1
                while target > 0 and not text[target - 1].isspace():
                    target -= 1
            else:
                while target < len(text) and not text[target].isspace():
                    target += 1
                while target < len(text) and text[target].isspace():
                    target += 1
            if target == caret:
                return False
            self.editor.SetInsertionPoint(target)
            return True

        target = caret
        if event.ControlDown() and key_code == wx.WXK_HOME:
            target = 0
        elif event.ControlDown() and key_code == wx.WXK_END:
            target = len(text)
        elif event.ControlDown() and key_code == wx.WXK_LEFT:
            return move_word(reverse=True)
        elif event.ControlDown() and key_code == wx.WXK_RIGHT:
            return move_word(reverse=False)
        elif key_code == wx.WXK_LEFT:
            target = max(0, caret - 1)
        elif key_code == wx.WXK_RIGHT:
            target = min(len(text), caret + 1)
        elif key_code == wx.WXK_UP:
            return move_vertical(-1)
        elif key_code == wx.WXK_DOWN:
            return move_vertical(1)
        elif key_code == wx.WXK_HOME:
            target = line_starts[line_index_for_position(caret)]
        elif key_code == wx.WXK_END:
            target = line_limit(line_index_for_position(caret))
        elif key_code == wx.WXK_PAGEUP:
            return move_vertical(-10)
        elif key_code == wx.WXK_PAGEDOWN:
            return move_vertical(10)
        else:
            return False
        if target == caret:
            return False
        self.editor.SetInsertionPoint(target)
        return True

    def _move_point(self, position: int) -> None:
        capped = max(0, min(position, len(self.editor.GetValue())))
        self.editor.SetInsertionPoint(capped)
        self.editor.SetSelection(capped, capped)

    def _build_ctx1_menu_items(self) -> tuple[object, ...]:
        """Build CTX-1 context menu items using the core builder (CTX-1 wiring).

        Returns a tuple of wx menu item IDs and their handlers for the CTX-1
        context menu model (spelling, lookup/thesaurus, cut/copy/paste).
        The caller binds each (id, handler) to the menu.
        """
        wx = self._wx
        text = self.editor.GetValue()
        caret = self.editor.GetInsertionPoint()
        sel_start, sel_end = self.editor.GetSelection()
        selection_text = text[sel_start:sel_end] if sel_end > sel_start else ""

        # Extract word at cursor for lookup/thesaurus.
        word = ""
        if caret <= len(text):
            # Simple word extraction: find word boundaries around cursor.
            start = caret
            while start > 0 and text[start - 1].isalnum():
                start -= 1
            end = caret
            while end < len(text) and text[end].isalnum():
                end += 1
            word = text[start:end] if start < end else ""

        # Check spelling.
        dictionary = self._spell_dictionary()
        misspelling = misspelling_at_position(text, caret, dictionary)
        is_misspelled = misspelling is not None
        suggestions = suggest_words(misspelling.word, dictionary) if misspelling else ()

        # Build the CTX-1 menu model.
        context = CursorContext(
            word=word,
            selection=selection_text,
            misspelled=is_misspelled,
            suggestions=suggestions,
            can_paste=True,  # wx clipboard state is optimistic here
        )
        items = build_context_menu(
            context,
            is_feature_enabled=self._feature_enabled,
            max_suggestions=5,
        )

        # Convert model to wx menu items with handlers.
        menu_items: list[tuple[object, Callable[[], None]]] = []
        for item in items:
            if item.is_separator:
                # Separator marker; caller appends wx.Menu separator.
                menu_items.append((wx.ID_SEPARATOR, lambda: None))
                continue

            item_id = wx.NewIdRef()
            if item.command == CMD_SPELL_SUGGESTION:
                # Apply the suggestion.
                def handler(
                    word_to_replace: str = misspelling.word if misspelling else "",
                    start: int = misspelling.start if misspelling else 0,
                    end: int = misspelling.end if misspelling else 0,
                    replacement: str = item.value,
                ) -> None:
                    self.editor.Replace(start, end, replacement)
                    self.document.set_text(self.editor.GetValue())
                    self._set_status(f'Replaced "{word_to_replace}" with "{replacement}"')

                menu_items.append((item_id, handler))
            elif item.command == CMD_SPELL_ADD:
                menu_items.append((
                    item_id,
                    lambda w=item.value: self._add_word_to_dictionary_scope(w, 0),
                ))
            elif item.command == CMD_SPELL_IGNORE:
                menu_items.append((
                    item_id,
                    lambda w=item.value: self._add_word_to_dictionary_scope(w, 1),
                ))
            elif item.command == CMD_LOOK_UP:
                menu_items.append((item_id, lambda w=item.value: self.show_lookup_dialog(w)))
            elif item.command == CMD_THESAURUS:
                menu_items.append((item_id, lambda w=item.value: self.show_thesaurus_or_lookup(w)))
            elif item.command == CMD_CUT:
                menu_items.append((item_id, lambda: self.editor.Cut()))
            elif item.command == CMD_COPY:
                menu_items.append((item_id, lambda: self.editor.Copy()))
            elif item.command == CMD_PASTE:
                menu_items.append((item_id, lambda: self.editor.Paste()))

        return tuple(menu_items)

    def show_lookup_dialog(self, word: str) -> None:
        """Show the DICT-2 Look Up dialog for ``word``."""
        wx = self._wx
        if not self._feature_enabled("core.dictionary"):
            self._set_status("Dictionary feature is disabled.")
            return

        # Query the lexical service (consent is per-feature, so online is enabled
        # if the user has consented to network lookups).
        online = self._feature_enabled("core.dictionary")
        result = self._lexical_service.lookup(word, online=online)

        # Render the result for screen-reader paging.
        text = render_lookup(result)
        items = build_lookup_items(result)

        # Build a simple list dialog.
        dialog = wx.Dialog(
            self.frame, title=f"Look Up: {word}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Read-only text control for the rendered lookup.
        text_ctrl = wx.TextCtrl(
            dialog,
            value=text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        text_ctrl.SetMinSize((500, 300))
        sizer.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 8)

        # List of insertable items.
        if items:
            list_label = wx.StaticText(dialog, label="Select a word to insert:")
            sizer.Add(list_label, 0, wx.LEFT | wx.RIGHT, 8)
            list_box = wx.ListBox(dialog, choices=[item.label for item in items])
            list_box.SetMinSize((500, 150))
            sizer.Add(list_box, 0, wx.EXPAND | wx.ALL, 8)

            def on_insert(_event: object) -> None:
                selection = list_box.GetSelection()
                if selection != wx.NOT_FOUND and 0 <= selection < len(items):
                    selected_item = items[selection]
                    if selected_item.action == "insert":
                        # Replace the word at the cursor with the selected value.
                        caret = self.editor.GetInsertionPoint()
                        text_val = self.editor.GetValue()
                        # Find word boundaries around cursor.
                        start = caret
                        while start > 0 and text_val[start - 1].isalnum():
                            start -= 1
                        end = caret
                        while end < len(text_val) and text_val[end].isalnum():
                            end += 1
                        self.editor.Replace(start, end, selected_item.value)
                        self.document.set_text(self.editor.GetValue())
                        self._set_status(f'Inserted "{selected_item.value}"')
                        dialog.Close()

            list_box.Bind(wx.EVT_LISTBOX_DCLICK, on_insert)

        def on_add_to_dictionary(_event: object) -> None:
            self._add_word_to_dictionary_scope(word, 0)
            dialog.Close()

        # A non-standard "Add to Dictionary" action row sits above the
        # standard dialog buttons so the looked-up word can be added to the
        # personal dictionary directly from the results.
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_dict_btn = wx.Button(dialog, label="Add to &Dictionary")
        add_dict_btn.Bind(wx.EVT_BUTTON, on_add_to_dictionary)
        action_sizer.Add(add_dict_btn, 0)
        sizer.Add(action_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        if items:
            btn_sizer = wx.StdDialogButtonSizer()
            insert_btn = wx.Button(dialog, wx.ID_OK, "Insert")
            insert_btn.Bind(wx.EVT_BUTTON, on_insert)
            btn_sizer.AddButton(insert_btn)
            close_btn = wx.Button(dialog, wx.ID_CANCEL, "Close")
            btn_sizer.AddButton(close_btn)
            btn_sizer.Realize()
            insert_btn.SetDefault()
            sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)
        else:
            # No insertable items; just a Close button.
            btn_sizer = wx.StdDialogButtonSizer()
            close_btn = wx.Button(dialog, wx.ID_CANCEL, "Close")
            btn_sizer.AddButton(close_btn)
            btn_sizer.Realize()
            close_btn.SetDefault()
            sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

        dialog.SetSizer(sizer)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.Fit()
        dialog.CenterOnParent()
        # Route through _show_modal_dialog (not dialog.ShowModal() directly) so
        # this custom dialog gets the shared contract: initial focus on its
        # content control instead of the OK button, region tracking,
        # enter/exit announcements, and focus return to the editor on close.
        self._show_modal_dialog(dialog, "Look Up")
        dialog.Destroy()

    def show_thesaurus_or_lookup(self, word: str) -> None:
        """Show the thesaurus or Look Up dialog for ``word``.

        If the offline thesaurus is available, use the existing thesaurus dialog.
        Otherwise, fall back to the DICT-2 Look Up dialog.
        """
        if thesaurus_engine.is_available():
            # Use the existing thesaurus implementation.
            self.show_thesaurus()
        else:
            self.show_lookup_dialog(word)

    def _start_external_change_watcher(self) -> None:
        """Start the FEAT-19 external file-change watcher for the open document."""
        wx = getattr(self, "_wx", None)
        if wx is None:
            return
        if self._external_change_watcher is not None:
            # Already watching.
            return
        if self.document.path is None:
            # No file to watch.
            return
        if not getattr(self.settings, "external_change_watch_enabled", True):
            # Watching is disabled.
            return

        self._external_change_watcher = ExternalChangeWatcher(self.document.path)
        self._external_change_watcher.prime(FileSnapshot.of(self.document.path))

        # Poll every N milliseconds (debounce interval from settings).
        debounce_ms = int(getattr(self.settings, "external_change_debounce_ms", 1000))

        def poll_external_change() -> None:
            if self._external_change_watcher is None:
                return
            change = self._external_change_watcher.poll()
            if change == "none":
                return

            decision = decide_reload(
                change,
                buffer_dirty=self.document.modified,
                watch_enabled=getattr(self.settings, "external_change_watch_enabled", True),
                auto_reload_when_clean=getattr(
                    self.settings, "external_change_auto_reload_when_clean", True
                ),
                prompt_on_conflict=getattr(
                    self.settings, "external_change_prompt_on_conflict", True
                ),
                file_name=self.document.path.name if self.document.path else "",
            )

            if decision.action == ReloadAction.RELOAD:
                self._reload_from_disk_preserving_cursor()
                self._announce(decision.announcement)
            elif decision.needs_prompt:
                # Pause the timer while the dialog is open to prevent re-entrancy.
                timer = self._external_change_timer
                if timer is not None:
                    timer.Stop()
                self._announce(decision.announcement)
                self._show_external_change_prompt(decision.action)
                # Restart the timer unless the user closed or replaced the document.
                if timer is not None and self._external_change_watcher is not None:
                    timer.Start(debounce_ms)

        self._external_change_timer = wx.Timer(self.frame)
        self.frame.Bind(
            wx.EVT_TIMER, lambda _e: poll_external_change(), self._external_change_timer
        )
        self._external_change_timer.Start(debounce_ms)

    def _stop_external_change_watcher(self) -> None:
        """Stop the FEAT-19 external file-change watcher."""
        if self._external_change_timer is not None:
            self._external_change_timer.Stop()
            self._external_change_timer = None
        self._external_change_watcher = None

    def _reload_from_disk_preserving_cursor(self) -> None:
        """Reload the document from disk, preserving the cursor and scroll position (FEAT-19)."""
        if self.document.path is None:
            return
        # Save cursor position before the reload.
        caret = self.editor.GetInsertionPoint()
        # Use the document's detected encoding so non-UTF-8 files round-trip cleanly.
        encoding = getattr(self.document, "encoding", None) or "utf-8"
        try:
            reloaded_text = self.document.path.read_text(encoding=encoding)
        except (UnicodeDecodeError, OSError, ValueError):
            try:
                reloaded_text = self.document.path.read_text(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                self._set_status(f"Could not reload '{self.document.path.name}' from disk.")
                return
        self.document.set_text(reloaded_text)
        self.document.modified = False
        self.editor.SetValue(reloaded_text)
        # Restore cursor, capped to valid range.
        capped_caret = max(0, min(caret, len(reloaded_text)))
        self.editor.SetInsertionPoint(capped_caret)
        self.editor.SetSelection(capped_caret, capped_caret)
        # Prime the watcher with the new snapshot so the reload is not re-reported.
        if self._external_change_watcher is not None:
            self._external_change_watcher.prime(FileSnapshot.of(self.document.path))

    def _show_external_change_prompt(self, action: ReloadAction) -> None:
        """Show the FEAT-19 conflict or deleted-file dialog and act on the user's choice.

        PROMPT_CONFLICT: file changed on disk while buffer is dirty.
          - Reload from Disk: discard edits and reload.
          - Keep My Version: keep edits; on-disk version is ignored until next save.
          - Open Disk Version in New Tab: open the on-disk copy alongside.

        PROMPT_DELETED: file deleted or moved on disk.
          - Keep Text: keep editing; document marked modified/unsaved.
          - Save As...: immediately open Save As so the user can rescue the text.
          - Close Tab: discard and close (with dirty-check).
        """
        wx = self._wx
        if self.document.path is None:
            return
        file_name = self.document.path.name

        if action == ReloadAction.PROMPT_DELETED:
            with wx.MessageDialog(
                self.frame,
                f"'{file_name}' was deleted or moved by another program.\n\n"
                "Your text is still open in the editor and has not been lost.\n"
                "What would you like to do?",
                "File Deleted from Disk",
                wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
            ) as dlg:
                set_labels = getattr(dlg, "SetYesNoCancelLabels", None)
                if callable(set_labels):
                    set_labels("Keep Text", "Save As...", "Close Tab")
                result = self._show_modal_dialog(dlg, "File Deleted from Disk")
            if result == wx.ID_YES:
                self.document.modified = True
                self._refresh_title()
                self._set_status(
                    f"'{file_name}' was deleted from disk. "
                    "Your text is unsaved. Use File > Save As to keep it."
                )
                self._stop_external_change_watcher()
            elif result == wx.ID_NO:
                self.document.modified = True
                self._refresh_title()
                self._stop_external_change_watcher()
                self.save_file_as()
            else:
                if not self.document.modified or self._confirm_discard_changes():
                    self._close_tab_at(self._active_tab_index)
            return

        # PROMPT_CONFLICT: file changed on disk, buffer has unsaved edits.
        with wx.MessageDialog(
            self.frame,
            f"'{file_name}' was changed on disk while you have unsaved edits.\n\n"
            "Reloading will replace your edits with the on-disk version.\n"
            "Keeping your version will overwrite the disk changes when you save.\n"
            "Opening in a new tab lets you compare both versions side by side.",
            "File Changed on Disk",
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        ) as dlg:
            set_labels = getattr(dlg, "SetYesNoCancelLabels", None)
            if callable(set_labels):
                set_labels("Reload from Disk", "Keep My Version", "Open Disk Version in New Tab")
            result = self._show_modal_dialog(dlg, "File Changed on Disk")

        if result == wx.ID_YES:
            self._reload_from_disk_preserving_cursor()
            self._announce("Reloaded from disk.")
            self._set_status(f"Reloaded '{file_name}' from disk.")
        elif result == wx.ID_NO:
            # Prime with the current on-disk snapshot so the watcher doesn't re-fire
            # immediately; the user's edits will overwrite on next save.
            if self._external_change_watcher is not None and self.document.path is not None:
                self._external_change_watcher.prime(FileSnapshot.of(self.document.path))
            self._set_status(f"Keeping your edits. '{file_name}' will be overwritten on next save.")
        else:
            # Open the on-disk version in a new tab.
            path = self.document.path
            if path is not None and path.exists():
                self.open_file(path, refresh_existing=False, record_recent=False)
                self._set_status(
                    f"Opened the on-disk version of '{file_name}' in a new tab. "
                    "Compare and decide which to keep."
                )

    def check_external_changes_now(self) -> None:
        """Manually trigger the external file-change check for the active document.

        Useful when the user wants to see whether the file changed on disk without
        waiting for the next poll cycle, or when auto-reload is on and they want
        a chance to compare before reloading.
        """
        if self.document.path is None:
            self._set_status("No file to check.")
            return
        if not getattr(self.settings, "external_change_watch_enabled", True):
            self._set_status(
                "External-change watching is disabled. "
                "Enable it in Preferences > General to use this feature."
            )
            return

        # Ensure a watcher exists (in case the file had no path when opened).
        if self._external_change_watcher is None:
            self._start_external_change_watcher()
            if self._external_change_watcher is None:
                self._set_status("Could not start external-change watcher.")
                return

        change = self._external_change_watcher.poll()
        decision = decide_reload(
            change,
            buffer_dirty=self.document.modified,
            watch_enabled=True,
            auto_reload_when_clean=False,
            prompt_on_conflict=True,
            file_name=self.document.path.name,
        )

        if decision.action == ReloadAction.NONE:
            self._set_status(f"'{self.document.path.name}' matches the on-disk version.")
        elif decision.action == ReloadAction.RELOAD:
            # Force-prompt even though auto_reload_when_clean would normally reload silently.
            self._show_external_change_prompt(ReloadAction.PROMPT_CONFLICT)
        else:
            self._announce(decision.announcement)
            self._show_external_change_prompt(decision.action)

    def _on_editor_context_menu(self, event: object) -> None:
        wx = self._wx
        menu = wx.Menu()

        # Inspect current context so we can offer context-aware actions.
        text = self.editor.GetValue()
        caret = self.editor.GetInsertionPoint()
        sel_start, sel_end = self.editor.GetSelection()
        has_selection = sel_end > sel_start
        link_target = find_link_at_cursor(text, caret) if text else None

        # --- Link actions appear first when the caret sits on a link. ---
        if link_target:
            open_link_id = wx.NewIdRef()
            copy_link_id = wx.NewIdRef()
            display_target = link_target if len(link_target) <= 60 else link_target[:57] + "..."
            menu.Append(open_link_id, f'Open Link  "{display_target}"')
            menu.Append(copy_link_id, "Copy Link Address")
            menu.AppendSeparator()
            menu.Bind(wx.EVT_MENU, lambda _e: self.follow_link(), id=open_link_id)
            menu.Bind(
                wx.EVT_MENU,
                lambda _e, target=link_target: (
                    self._copy_text_to_clipboard(target),
                    self._set_status(f"Copied link: {target}"),
                ),
                id=copy_link_id,
            )

        undo_id = wx.NewIdRef()
        redo_id = wx.NewIdRef()
        cut_id = wx.NewIdRef()
        copy_id = wx.NewIdRef()
        copy_source_id = wx.NewIdRef()
        paste_id = wx.NewIdRef()
        select_all_id = wx.NewIdRef()
        select_line_id = wx.NewIdRef()
        spell_id = wx.NewIdRef()
        next_spell_id = wx.NewIdRef()

        menu.Append(undo_id, self._menu_label("Undo", "edit.undo"))
        menu.Append(redo_id, self._menu_label("Redo", "edit.redo"))
        menu.AppendSeparator()
        cut_item = menu.Append(cut_id, "Cut")
        copy_item = menu.Append(copy_id, "Copy")
        copy_source_item = menu.Append(
            copy_source_id, self._menu_label("Copy With Source", "edit.copy_with_source")
        )
        menu.Append(paste_id, "Paste")
        menu.AppendSeparator()
        select_chunk_id = wx.NewIdRef()
        menu.Append(select_all_id, "Select All")
        menu.Append(select_line_id, "Select Line")
        menu.Append(
            select_chunk_id,
            self._menu_label("Select Chunk", "edit.select_chunk"),
        )

        # Disable selection-only actions when there is no selection.
        if not has_selection:
            cut_item.Enable(False)
            copy_item.Enable(False)
            copy_source_item.Enable(False)

        # --- Transform submenu (case + lines). Always available; some items
        #     are only meaningful with a selection but still safe to invoke. ---
        transform_menu = wx.Menu()
        upper_id = wx.NewIdRef()
        lower_id = wx.NewIdRef()
        title_id = wx.NewIdRef()
        sentence_id = wx.NewIdRef()
        toggle_case_id = wx.NewIdRef()
        sort_asc_id = wx.NewIdRef()
        sort_desc_id = wx.NewIdRef()
        transform_menu.Append(upper_id, "UPPER CASE")
        transform_menu.Append(lower_id, "lower case")
        transform_menu.Append(title_id, "Title Case")
        transform_menu.Append(sentence_id, "Sentence case")
        transform_menu.Append(toggle_case_id, "Toggle Case")
        transform_menu.AppendSeparator()
        quote_id = wx.NewIdRef()
        unquote_id = wx.NewIdRef()
        dup_sel_id = wx.NewIdRef()
        transform_menu.Append(sort_asc_id, "Sort Lines Ascending")
        transform_menu.Append(sort_desc_id, "Sort Lines Descending")
        transform_menu.AppendSeparator()
        transform_menu.Append(quote_id, self._menu_label("Quote Lines", "edit.quote_lines"))
        transform_menu.Append(unquote_id, self._menu_label("Unquote Lines", "edit.unquote_lines"))
        transform_menu.AppendSeparator()
        transform_menu.Append(
            dup_sel_id, self._menu_label("Duplicate Selection", "edit.duplicate_selection")
        )
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_upper_case(), id=upper_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_lower_case(), id=lower_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_title_case(), id=title_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_sentence_case(), id=sentence_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_toggle_case(), id=toggle_case_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.sort_lines_ascending(), id=sort_asc_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.sort_lines_descending(), id=sort_desc_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.quote_lines(), id=quote_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.unquote_lines(), id=unquote_id)
        transform_menu.Bind(wx.EVT_MENU, lambda _e: self.duplicate_selection(), id=dup_sel_id)
        menu.AppendSubMenu(transform_menu, "Change &Case")

        # --- Line submenu. ---
        line_menu = wx.Menu()
        dup_id = wx.NewIdRef()
        del_id = wx.NewIdRef()
        move_up_id = wx.NewIdRef()
        move_down_id = wx.NewIdRef()
        join_id = wx.NewIdRef()
        line_menu.Append(dup_id, self._menu_label("Duplicate Line", "edit.duplicate_line"))
        line_menu.Append(del_id, self._menu_label("Delete Line", "edit.delete_line"))
        line_menu.Append(move_up_id, self._menu_label("Move Line Up", "edit.move_line_up"))
        line_menu.Append(move_down_id, self._menu_label("Move Line Down", "edit.move_line_down"))
        line_menu.Append(join_id, "Join With Next Line")
        line_menu.Bind(wx.EVT_MENU, lambda _e: self.duplicate_line(), id=dup_id)
        line_menu.Bind(wx.EVT_MENU, lambda _e: self.delete_line(), id=del_id)
        line_menu.Bind(wx.EVT_MENU, lambda _e: self.move_line_up(), id=move_up_id)
        line_menu.Bind(wx.EVT_MENU, lambda _e: self.move_line_down(), id=move_down_id)
        line_menu.Bind(wx.EVT_MENU, lambda _e: self.join_lines(), id=join_id)
        menu.AppendSubMenu(line_menu, "Line")

        glow_menu = wx.Menu()
        glow_audit_document_id = wx.NewIdRef()
        glow_audit_selection_id = wx.NewIdRef()
        glow_fix_document_id = wx.NewIdRef()
        glow_fix_selection_id = wx.NewIdRef()
        glow_menu.Append(glow_audit_document_id, "GLOW Audit Current Document")
        glow_menu.Append(glow_audit_selection_id, "GLOW Audit Selection / Paragraph")
        glow_menu.AppendSeparator()
        glow_menu.Append(glow_fix_document_id, "GLOW Fix Current Document")
        glow_menu.Append(glow_fix_selection_id, "GLOW Fix Selection / Paragraph")
        glow_menu.Bind(
            wx.EVT_MENU,
            lambda _e: self.glow_audit_document(),
            id=glow_audit_document_id,
        )
        glow_menu.Bind(
            wx.EVT_MENU,
            lambda _e: self.glow_audit_selection(),
            id=glow_audit_selection_id,
        )
        glow_menu.Bind(
            wx.EVT_MENU,
            lambda _e: self.glow_fix_document(),
            id=glow_fix_document_id,
        )
        glow_menu.Bind(
            wx.EVT_MENU,
            lambda _e: self.glow_fix_selection(),
            id=glow_fix_selection_id,
        )
        menu.AppendSubMenu(glow_menu, "GLOW")

        menu.AppendSeparator()
        menu.Append(spell_id, self._menu_label("Spell Check...", "tools.spell_check_dialog"))
        menu.Append(next_spell_id, self._menu_label("Next Misspelling", "tools.next_misspelling"))

        # --- Thesaurus lookup (when on/within a word). ---
        if thesaurus_engine.is_available():
            thes_id = wx.NewIdRef()
            menu.Append(thes_id, "Look Up in Thesaurus")
            menu.Bind(wx.EVT_MENU, lambda _e: self.show_thesaurus(), id=thes_id)

        dictionary = self._spell_dictionary()
        misspelling = misspelling_at_position(text, caret, dictionary)
        if misspelling is not None:
            spelling_menu = wx.Menu()
            suggestions = suggest_words(misspelling.word, dictionary)
            if suggestions:
                for suggestion in suggestions:
                    item_id = wx.NewIdRef()
                    spelling_menu.Append(item_id, suggestion)

                    def _apply_replacement(
                        _event,
                        replacement: str = suggestion,
                        start: int = misspelling.start,
                        end: int = misspelling.end,
                        original: str = misspelling.word,
                    ) -> None:
                        self.editor.Replace(start, end, replacement)
                        self.document.set_text(self.editor.GetValue())
                        self._set_status(f'Replaced "{original}" with "{replacement}"')

                    spelling_menu.Bind(
                        wx.EVT_MENU,
                        _apply_replacement,
                        id=item_id,
                    )
            else:
                empty_id = wx.NewIdRef()
                item = spelling_menu.Append(empty_id, "(No suggestions)")
                item.Enable(False)
            spelling_menu.AppendSeparator()
            add_menu = wx.Menu()
            personal_id = wx.NewIdRef()
            document_id = wx.NewIdRef()
            project_id = wx.NewIdRef()
            add_menu.Append(personal_id, "Personal dictionary")
            add_menu.Append(document_id, "Document dictionary")
            add_menu.Append(project_id, "Project dictionary")
            add_menu.Bind(
                wx.EVT_MENU,
                lambda _e, word=misspelling.word: self._add_word_to_dictionary_scope(word, 0),
                id=personal_id,
            )
            add_menu.Bind(
                wx.EVT_MENU,
                lambda _e, word=misspelling.word: self._add_word_to_dictionary_scope(word, 1),
                id=document_id,
            )
            add_menu.Bind(
                wx.EVT_MENU,
                lambda _e, word=misspelling.word: self._add_word_to_dictionary_scope(word, 2),
                id=project_id,
            )
            spelling_menu.AppendSubMenu(add_menu, "Add to dictionary")
            menu.AppendSubMenu(spelling_menu, "Spelling Suggestions")

        menu.AppendSeparator()
        # --- Navigation actions. ---
        go_line_id = wx.NewIdRef()
        bookmark_id = wx.NewIdRef()
        palette_id = wx.NewIdRef()
        menu.Append(go_line_id, self._menu_label("Go to Line...", "navigate.go_to_line"))
        menu.Append(bookmark_id, self._menu_label("Set Bookmark Here...", "navigate.set_bookmark"))
        menu.Append(palette_id, self._menu_label("Command Palette...", "app.command_palette"))

        menu.Bind(wx.EVT_MENU, lambda _e: self.undo(), id=undo_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.redo(), id=redo_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.editor.Cut(), id=cut_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.editor.Copy(), id=copy_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.copy_with_source(), id=copy_source_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.editor.Paste(), id=paste_id)
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: self.editor.SetSelection(0, len(self.editor.GetValue())),
            id=select_all_id,
        )
        menu.Bind(wx.EVT_MENU, lambda _e: self.select_line(), id=select_line_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.select_chunk(), id=select_chunk_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_spell_check_dialog(), id=spell_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.next_misspelling(), id=next_spell_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.go_to_line(), id=go_line_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.set_bookmark(), id=bookmark_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_palette(), id=palette_id)
        self._popup_context_menu(self.editor, menu, event)

    def _on_statusbar_context_menu(self, event: object) -> None:
        wx = self._wx
        menu = wx.Menu()
        dark_id = wx.NewIdRef()
        wrap_id = wx.NewIdRef()
        spell_id = wx.NewIdRef()
        layout_id = wx.NewIdRef()
        menu.AppendCheckItem(dark_id, "Dark Mode")
        menu.Check(dark_id, self.settings.theme == "dark")
        menu.AppendCheckItem(wrap_id, "Soft Wrap")
        menu.Check(wrap_id, self.settings.soft_wrap)
        menu.AppendCheckItem(spell_id, "Spell Check As You Type")
        menu.Check(spell_id, self.settings.spellcheck_as_you_type)
        menu.AppendSeparator()
        menu.Append(layout_id, "Status Bar Layout...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.toggle_dark_mode(), id=dark_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.toggle_soft_wrap(), id=wrap_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.toggle_spellcheck_as_you_type(), id=spell_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_status_bar_settings(), id=layout_id)
        self._popup_context_menu(self.statusbar, menu, event)

    def _on_frame_context_menu(self, event: object) -> None:
        wx = self._wx
        menu = wx.Menu()
        new_id = wx.NewIdRef()
        open_id = wx.NewIdRef()
        save_id = wx.NewIdRef()
        palette_id = wx.NewIdRef()
        notifications_id = wx.NewIdRef()
        updates_id = wx.NewIdRef()
        menu.Append(new_id, self._menu_label("New", "file.new"))
        menu.Append(open_id, self._menu_label("Open...", "file.open"))
        menu.Append(save_id, self._menu_label("Save", "file.save"))
        menu.AppendSeparator()
        menu.Append(palette_id, self._menu_label("Command Palette...", "app.command_palette"))
        menu.Append(notifications_id, "Notifications...")
        menu.Append(updates_id, "Check for Updates...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.new_file(), id=new_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_file(), id=open_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.save_file(), id=save_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_palette(), id=palette_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_notifications(), id=notifications_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.check_for_updates(), id=updates_id)
        self._popup_context_menu(self.frame, menu, event)

    def _on_notebook_context_menu(self, event: object) -> None:
        wx = self._wx
        if not self._document_tabs:
            event.Skip()
            return
        # Determine the tab under the cursor (if any).
        screen_pos = event.GetPosition()
        target_index = self._current_tab_index()
        try:
            client_pos = self.notebook.ScreenToClient(screen_pos)
            hit_index, _flags = self.notebook.HitTest(client_pos)
            if hit_index >= 0:
                target_index = hit_index
        except Exception:
            pass
        if target_index < 0 or target_index >= len(self._document_tabs):
            target_index = self._current_tab_index()
        tab_label = self._tab_page_title(target_index)

        menu = wx.Menu()
        close_id = wx.NewIdRef()
        close_others_id = wx.NewIdRef()
        close_right_id = wx.NewIdRef()
        copy_path_id = wx.NewIdRef()
        reveal_id = wx.NewIdRef()
        menu.Append(close_id, f'Close "{tab_label}"')
        menu.Append(close_others_id, "Close Other Tabs")
        menu.Append(close_right_id, "Close Tabs to the Right")
        menu.AppendSeparator()
        tab_document = self._document_tabs[target_index].document
        copy_item = menu.Append(copy_path_id, "Copy File Path")
        reveal_item = menu.Append(reveal_id, "Show in File Explorer")
        if tab_document.path is None:
            copy_item.Enable(False)
            reveal_item.Enable(False)
        if len(self._document_tabs) <= 1:
            close_others_id_item = menu.FindItemById(close_others_id)
            if close_others_id_item is not None:
                close_others_id_item.Enable(False)
        if target_index >= len(self._document_tabs) - 1:
            close_right_item = menu.FindItemById(close_right_id)
            if close_right_item is not None:
                close_right_item.Enable(False)

        menu.Bind(
            wx.EVT_MENU,
            lambda _e, idx=target_index: self._close_tab_at(idx),
            id=close_id,
        )
        menu.Bind(
            wx.EVT_MENU,
            lambda _e, idx=target_index: self._close_other_tabs(idx),
            id=close_others_id,
        )
        menu.Bind(
            wx.EVT_MENU,
            lambda _e, idx=target_index: self._close_tabs_to_right(idx),
            id=close_right_id,
        )
        if tab_document.path is not None:
            path_text = str(tab_document.path)
            menu.Bind(
                wx.EVT_MENU,
                lambda _e, text=path_text: (
                    self._copy_text_to_clipboard(text),
                    self._set_status(f"Copied path: {text}"),
                ),
                id=copy_path_id,
            )
            menu.Bind(
                wx.EVT_MENU,
                lambda _e, p=tab_document.path: self._reveal_in_explorer(p),
                id=reveal_id,
            )
        self._popup_context_menu(self.notebook, menu, event)

    def _close_tab_at(self, index: int) -> None:
        if index < 0 or index >= len(self._document_tabs):
            return
        previous_active = self._active_tab_index
        self._select_tab(index)
        if not self._prompt_to_save_active_document("closing"):
            self._select_tab(previous_active)
            self._set_status("Close cancelled")
            return
        self._close_tab(index)
        self._set_status("Closed document")

    def _close_other_tabs(self, keep_index: int) -> None:
        if keep_index < 0 or keep_index >= len(self._document_tabs):
            return
        keep_tab = self._document_tabs[keep_index]
        # Close from the end backwards so indices stay valid.
        closed = 0
        for index in range(len(self._document_tabs) - 1, -1, -1):
            if self._document_tabs[index] is keep_tab:
                continue
            self._select_tab(index)
            if not self._prompt_to_save_active_document("closing"):
                self._set_status("Close other tabs cancelled")
                # Restore focus to the tab we wanted to keep, if it still exists.
                if keep_tab in self._document_tabs:
                    self._select_tab(self._document_tabs.index(keep_tab))
                return
            self._close_tab(index)
            closed += 1
        if keep_tab in self._document_tabs:
            self._select_tab(self._document_tabs.index(keep_tab))
        self._set_status(f"Closed {closed} other tab(s)")

    def _close_tabs_to_right(self, anchor_index: int) -> None:
        if anchor_index < 0 or anchor_index >= len(self._document_tabs):
            return
        anchor_tab = self._document_tabs[anchor_index]
        closed = 0
        for index in range(len(self._document_tabs) - 1, anchor_index, -1):
            self._select_tab(index)
            if not self._prompt_to_save_active_document("closing"):
                self._set_status("Close tabs to the right cancelled")
                if anchor_tab in self._document_tabs:
                    self._select_tab(self._document_tabs.index(anchor_tab))
                return
            self._close_tab(index)
            closed += 1
        if anchor_tab in self._document_tabs:
            self._select_tab(self._document_tabs.index(anchor_tab))
        self._set_status(f"Closed {closed} tab(s) to the right")

    def _reveal_in_explorer(self, path: Path) -> None:
        import subprocess

        try:
            if not path.exists():
                self._set_status(f"Path no longer exists: {path}")
                return
            if path.is_dir():
                subprocess.Popen(["explorer", str(path)])  # noqa: S603,S607
                self._set_status(f"Opened {path.name} folder in Explorer")
                return
            # /select, highlights the file in Windows Explorer.
            subprocess.Popen(["explorer", f"/select,{path}"])  # noqa: S603,S607
            self._set_status(f"Revealing {path.name} in Explorer")
        except OSError as error:
            self._set_status(f"Could not open Explorer: {error}")

    def open_logs_folder(self) -> None:
        logs_path = app_data_dir() / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)
        self._reveal_in_explorer(logs_path)

    def open_diagnostics_folder(self) -> None:
        diagnostics_path = app_data_dir() / "diagnostics"
        diagnostics_path.mkdir(parents=True, exist_ok=True)
        self._reveal_in_explorer(diagnostics_path)

    def _apply_editor_text(self, text: str, status: str) -> None:
        if text == self.editor.GetValue():
            self._set_status(status)
            return
        self.editor.ChangeValue(text)
        self.document.set_text(text)
        if not self._suspend_persistent_undo:
            self._record_persistent_undo_state(text)
        self._maybe_autosave()
        self._refresh_title()
        self._refresh_contextual_menu_items()
        self._refresh_sessions_menu()
        self._set_status(status)

    def _popup_context_menu(self, widget: object, menu: object, event: object) -> None:
        wx = self._wx
        position = event.GetPosition()
        if isinstance(position, tuple):
            point = wx.Point(position[0], position[1])
        else:
            point = position
        if point == wx.DefaultPosition or (point.x == -1 and point.y == -1):
            widget.PopupMenu(menu)
        else:
            widget.PopupMenu(menu, widget.ScreenToClient(point))

    def _on_close(self, event: object) -> None:
        if self.settings.tray_enabled and not self._is_exiting:
            self._ensure_tray_icon()
            self.frame.Hide()
            self._set_status("Quill is running in the system tray")
            event.Veto()
            return
        if not self._can_close_all_documents():
            event.Veto()
            return
        # H-3-ui: destroy the modeless Watch Queue Monitor so it does not
        # outlive the main frame and leak a window reference.
        if self._watch_queue_monitor is not None:
            try:
                self._watch_queue_monitor.Destroy()
            except Exception:  # noqa: BLE001
                pass
            self._watch_queue_monitor = None
            self._watch_queue_listbox = None
            self._watch_queue_pause_button = None
        self._watch_service.stop()
        self._unregister_global_hotkeys()
        self._remove_tray_icon()
        self.close_ssh_connections()
        # #32: drop GitHub-temp files no longer referenced by an open tab so
        # the user's app-data directory does not accumulate copies of files
        # they opened once and never saved back.
        prune = getattr(self, "prune_orphaned_github_temp", None)
        if callable(prune):
            try:
                prune()
            except Exception:  # noqa: BLE001 - cleanup must never block shutdown
                pass
        save_settings(self.settings)
        self.flush_persistent_undo()
        mark_clean_exit(self.session_id)
        try:
            from quill.ui import sound_manager

            sound_manager.shutdown()
        except Exception:  # noqa: BLE001
            pass
        event.Skip()

    def _on_iconize(self, event: object) -> None:
        if self.settings.tray_enabled and event.IsIconized():
            self._ensure_tray_icon()
            self.frame.Hide()
            self._set_status("Minimized to system tray")
        event.Skip()

    def _on_toggle_tray_mode(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.settings.tray_enabled = enabled
        if enabled:
            self._ensure_tray_icon()
            self._set_status("System tray mode enabled")
            return
        self._remove_tray_icon()
        self._set_status("System tray mode disabled")

    def _on_toggle_soft_wrap(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.toggle_soft_wrap(enabled)

    def _on_toggle_auto_side_preview(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.settings.auto_side_preview = enabled
        save_settings(self.settings)
        if enabled:
            tab = self._active_tab()
            if tab is not None:
                self._maybe_auto_side_preview(tab)
            self._set_status("Auto side-by-side preview on")
        else:
            self._set_status("Auto side-by-side preview off")

    def _on_toggle_tab_control(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.toggle_tab_control(enabled)

    def _on_toggle_find_wrap(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.toggle_find_wrap(enabled)

    def _on_toggle_title_full_path(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.settings.title_bar_path_mode = "full_path" if enabled else "name"
        save_settings(self.settings)
        self._refresh_title()
        self._set_status("Title bar shows full path" if enabled else "Title bar shows file name")

    def _on_toggle_auto_check_updates(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.settings.auto_check_updates = enabled
        save_settings(self.settings)
        self._set_status(
            "Check for updates on startup on" if enabled else "Check for updates on startup off"
        )

    def _on_toggle_dark_mode(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.toggle_dark_mode(enabled)

    def _on_toggle_persistent_undo(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.toggle_persistent_undo(enabled)

    def _on_toggle_spellcheck_as_you_type(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.toggle_spellcheck_as_you_type(enabled)

    def _on_toggle_intellisense_as_you_type(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.toggle_intellisense_as_you_type(enabled)

    def _on_toggle_start_with_no_document_open(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.settings.start_with_no_document_open = enabled
        save_settings(self.settings)
        self._set_status(
            "Start with no document open on" if enabled else "Start with no document open off"
        )

    def _on_toggle_extend_selection_mode(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.toggle_extend_selection_mode(enabled)

    def _offer_crash_recovery(self) -> None:
        if not self._recovery_offers:
            return
        wx = self._wx
        offer = self._recovery_offers[0]
        logs_path = app_data_dir() / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)

        # M-28 / §8.2: adaptive prompt text after repeated dismissals.
        if offer.dismissal_count >= 3:
            intro = (
                "You have dismissed this recovery offer "
                f"{offer.dismissal_count} time(s). "
                "Press Restore to keep the recovered version, "
                "or Skip to discard it and continue with a blank document. "
                "Pressing Skip again will keep the in-memory version; "
                "press Restore now to save your work."
            )
        else:
            intro = (
                "Quill detected an unclean exit. Restore the latest autosave snapshot, "
                "open the logs folder, or save diagnostics before continuing."
            )

        # Pre-read the snapshot so we can show a preview (§8.2 recovery diff).
        preview_text = ""
        try:
            _preview_full, _had_rep = read_recovery_snapshot(offer.snapshot)
            lines = _preview_full.splitlines()
            preview_text = "\n".join(lines[:30])
            if len(lines) > 30:
                preview_text += f"\n\n... ({len(lines) - 30} more lines)"
        except OSError:
            preview_text = "(Could not read snapshot preview)"

        dialog = wx.Dialog(self.frame, title="Crash Recovery", size=(780, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(dialog, label=intro),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )

        # §8.2: read-only snapshot preview so the user can decide before restoring.
        root.Add(
            wx.StaticText(dialog, label="Snapshot preview (first 30 lines):"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        # TE_RICH2 is required for screen-reader accessibility on Windows. A plain
        # ES_READONLY EDIT control (the default for TE_MULTILINE | TE_READONLY) does
        # not expose its value through UIA or IA2 when read-only, so NVDA and JAWS
        # announce the field but read no content. Switching to a RichEdit control via
        # TE_RICH2 fixes this — the accessible value is correctly reported.
        # SetName gives the control a programmatic accessible name; the preceding
        # StaticText label is not automatically associated with the TextCtrl on Windows
        # so without SetName screen readers announce "edit" with no context.
        # If the snapshot file was empty (e.g. Quill crashed before writing any
        # content), preview_text is "". An empty string is indistinguishable from a
        # control that failed to populate, so we show a descriptive fallback instead.
        preview_ctrl = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP | wx.TE_RICH2,
        )
        preview_ctrl.SetName("Snapshot preview")
        preview_ctrl.SetValue(preview_text if preview_text else "(snapshot is empty)")
        root.Add(preview_ctrl, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        root.Add(wx.StaticText(dialog, label="Logs folder"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        logs_field = wx.TextCtrl(dialog, style=wx.TE_READONLY)
        logs_field.SetValue(str(logs_path))
        root.Add(logs_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        restore_button = wx.Button(dialog, id=wx.ID_YES, label="Restore Latest Snapshot")
        open_logs_button = wx.Button(dialog, label="Open Logs Folder")
        save_diagnostics_button = wx.Button(dialog, label="Save Diagnostics...")
        skip_label = "Discard and Continue" if offer.dismissal_count >= 3 else "Skip Recovery"
        skip_button = wx.Button(dialog, id=wx.ID_NO, label=skip_label)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(restore_button, 0, wx.RIGHT, 6)
        buttons.Add(open_logs_button, 0, wx.RIGHT, 6)
        buttons.Add(save_diagnostics_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(skip_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)

        restore_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_YES))
        open_logs_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_APPLY))
        save_diagnostics_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_SAVE))
        skip_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_NO))
        dialog.SetDefaultItem(restore_button)
        apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
        restore_button.SetFocus()
        dialog._quill_keep_initial_focus = True

        try:
            while True:
                result = self._show_modal_dialog(
                    dialog, "Crash Recovery", restore_editor_focus=False
                )
                if result == wx.ID_APPLY:
                    self.open_logs_folder()
                    continue
                if result == wx.ID_SAVE:
                    self.save_diagnostics_bundle()
                    continue
                if result != wx.ID_YES:
                    mark_recovery_offer_dismissed(offer)
                    record_diagnostic_event(
                        "recovery",
                        "offer-dismissed",
                        detail=f"session={offer.session_id}; snapshot={offer.snapshot}",
                    )
                    self._set_status("Skipped crash recovery")
                    self._record_notification("Crash recovery offer dismissed", "recovery")
                    return
                try:
                    recovered_text, had_replacements = read_recovery_snapshot(offer.snapshot)
                except OSError as error:
                    record_diagnostic_event(
                        "recovery",
                        "snapshot-read-failed",
                        detail=(
                            f"session={offer.session_id}; snapshot={offer.snapshot}; error={error}"
                        ),
                    )
                    self._show_message_box(
                        f"Could not restore snapshot: {error}",
                        "Crash Recovery",
                        wx.ICON_ERROR | wx.OK,
                    )
                    self._set_status("Crash recovery failed")
                    return
                self._create_document_tab(
                    Document(text=recovered_text, path=None, modified=True),
                    select=True,
                )
                # §8.2: warn when bytes were silently replaced during decode.
                if had_replacements:
                    self._record_notification(
                        "This file had undecodable bytes; some characters may have been replaced "
                        "(shown as •).",
                        "recovery",
                    )
                mark_recovery_offer_recovered(offer)
                record_diagnostic_event(
                    "recovery",
                    "snapshot-recovered",
                    detail=f"session={offer.session_id}; snapshot={offer.snapshot}",
                )
                self._location_ring = LocationRing()
                # §8.4: restore the cursor to where the user was working.
                restore_pos = offer.cursor_position
                if restore_pos > 0 and self.editor is not None:
                    try:
                        wx.CallAfter(self.editor.SetInsertionPoint, restore_pos)
                        self._location_ring.record(restore_pos)
                    except Exception:  # noqa: BLE001
                        self._location_ring.record(0)
                else:
                    self._location_ring.record(0)
                self._refresh_title()
                status = "Recovered latest autosave snapshot"
                if had_replacements:
                    status += " (some bytes replaced — check notifications)"
                self._set_status(status)
                self._record_notification("Recovered autosave snapshot", "recovery")
                return
        finally:
            dialog.Destroy()

    def _apply_theme(self, theme: str) -> None:
        wx = self._wx
        if theme == "dark":
            foreground = wx.Colour(230, 230, 230)
            background = wx.Colour(30, 30, 30)
            chrome_background = wx.Colour(45, 45, 45)
        elif theme == "system" and is_high_contrast_enabled():
            foreground = wx.Colour(0, 0, 0)
            background = wx.Colour(255, 255, 255)
            chrome_background = wx.Colour(255, 212, 0)
        else:
            foreground = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            background = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
            chrome_background = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE)
        self.editor.SetForegroundColour(foreground)
        self.editor.SetBackgroundColour(background)
        self.frame.SetForegroundColour(foreground)
        self.frame.SetBackgroundColour(chrome_background)
        self.statusbar.SetForegroundColour(foreground)
        self.statusbar.SetBackgroundColour(chrome_background)
        self.editor.Refresh()
        self.frame.Refresh()
        # §8.1 live contrast checker: announce the resulting contrast ratio after
        # every theme application so the user knows whether the palette is readable.
        wx.CallAfter(self._announce_contrast_after_theme, foreground, background)

    def _announce_contrast_after_theme(self, foreground: object, background: object) -> None:
        """Announce the approximate WCAG contrast ratio between *foreground* and *background*."""
        try:
            fr, fg, fb = foreground.Red(), foreground.Green(), foreground.Blue()
            br, bg, bb = background.Red(), background.Green(), background.Blue()
            ratio = _wcag_contrast_ratio(fr, fg, fb, br, bg, bb)
            if ratio >= 7.0:
                grade = "AAA"
            elif ratio >= 4.5:
                grade = "AA"
            elif ratio >= 3.0:
                grade = "AA large text"
            else:
                grade = "below AA"
            self._set_status(f"Theme applied. Contrast ratio: {ratio:.1f}:1 ({grade})")
        except Exception:  # noqa: BLE001
            pass

    def announce_contrast_ratio(self) -> None:
        """§8.1: Announce the current editor foreground/background contrast ratio."""
        try:
            fg = self.editor.GetForegroundColour()
            bg = self.editor.GetBackgroundColour()
            ratio = _wcag_contrast_ratio(
                fg.Red(), fg.Green(), fg.Blue(), bg.Red(), bg.Green(), bg.Blue()
            )
            if ratio >= 7.0:
                grade = "AAA (excellent)"
            elif ratio >= 4.5:
                grade = "AA (good)"
            elif ratio >= 3.0:
                grade = "AA large text only (marginal)"
            else:
                grade = "below AA (insufficient)"
            msg = f"Contrast ratio: {ratio:.1f}:1, WCAG grade: {grade}"
            self._announce(msg)
        except Exception:  # noqa: BLE001
            self._set_status("Could not calculate contrast ratio")

    # ---------- §8.1 / §8.2 delight feature handlers ----------

    def announce_context_mode_shortcuts(self) -> None:
        """§8.2: Announce the most useful keys for the current mode (Ctrl+Shift+H)."""
        if getattr(self, "_quill_key_mode_active", False):
            self._announce(
                "QUILL browse mode keys: "
                "H headings, A links, L lists, I list items, T tables, "
                "B bookmarks, P paragraphs, S sentences, C table of contents, "
                "left bracket and right bracket to skip, Escape to exit."
            )
            return
        region = getattr(self, "_active_region", "Editor")
        if region == "Status Bar":
            self._announce(
                "Status bar keys: Left and Right arrows to move between cells, "
                "Enter or Space to activate, Escape to return to the editor."
            )
            return
        # Default: editor mode key summary.
        bindings = self.keymap

        def _b(cmd: str) -> str:
            return bindings.get(cmd) or DEFAULT_KEYMAP.get(cmd) or ""

        tips = [
            f"Save: {_b('file.save')}",
            f"Undo: {_b('edit.undo')}",
            f"Find: {_b('edit.find')}",
            f"Go to line: {_b('navigate.go_to_line')}",
            f"Command palette: {_b('app.command_palette')}",
            f"Go to anything: {_b('navigate.go_to_anything')}",
            "QUILL browse mode: Ctrl+Alt+Q or Ctrl+Shift+Grave comma Q",
            f"Document summary: {_b('document.summary')}",
            f"Context help: {_b('help.context_help')} (this message)",
        ]
        self._announce("Editor mode shortcuts. " + ", ".join(tips) + ".")

    def show_document_summary(self) -> None:
        """§8.3: Announce a one-sentence document summary (Alt+I)."""
        if self.editor is None:
            self._set_status("No document open")
            return
        try:
            stats = compute_document_stats(self.editor.GetValue())
            doc = getattr(self, "document", None)
            path_part = doc.path.name if (doc and doc.path) else "unsaved document"
            save_state = ""
            if doc and doc.modified:
                save_state = ", unsaved changes"
            headings = getattr(stats, "headings", 0)
            heading_part = f", {headings} heading(s)" if headings else ""
            summary = (
                f"{path_part}: {stats.words:,} words, "
                f"{stats.lines:,} lines{heading_part}{save_state}."
            )
            self._announce(summary)
        except Exception:  # noqa: BLE001
            self._set_status("Could not summarize document")

    def open_go_to_anything(self) -> None:
        """§8.1 NAV-4: Universal 'Go to anything' palette (Quill+G).

        Opens the command palette with an expanded scope that also surfaces
        outline headings, bookmarks, and recent files in addition to commands.
        The search-as-you-type box accepts the same prefix conventions as the
        command palette (>, :, ? etc.) plus a # prefix for headings.
        """
        from quill.ui.palette import GoToAnythingDialog

        headings = self._collect_outline_headings()
        dialog = GoToAnythingDialog(
            self.frame,
            self.commands,
            feature_manager=getattr(self, "features", None),
            headings=headings,
            announce_fn=self._announce,
        )
        dialog.show_modal_and_run(self)

    def _collect_outline_headings(self) -> list[tuple[str, int]]:
        """Return ``[(heading_text, line_number), ...]`` for the current document."""
        if self.editor is None:
            return []
        try:
            text = self.editor.GetValue()
            results: list[tuple[str, int]] = []
            for lineno, line in enumerate(text.splitlines(), start=1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    level = len(stripped) - len(stripped.lstrip("#"))
                    if 1 <= level <= 6:
                        heading = stripped.lstrip("#").strip()
                        if heading:
                            results.append((heading, lineno))
            return results
        except Exception:  # noqa: BLE001
            return []

    def open_key_cheatsheet(self) -> None:
        """§8.1 QK-1..9: Full key cheatsheet overlay (Alt+Shift+/).

        Presents every bound command grouped by category in a read-only
        searchable dialog.  Screen readers can navigate by group heading and
        individual key entry.
        """
        wx = self._wx
        dialog = wx.Dialog(
            self.frame,
            title="Key Cheatsheet",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        dialog.SetSize((720, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        search = wx.SearchCtrl(dialog, style=wx.TE_PROCESS_ENTER)
        search.SetDescriptiveText("Search by command name or key binding")
        root.Add(search, 0, wx.EXPAND | wx.ALL, 8)

        cheatsheet_ctrl = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        root.Add(cheatsheet_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        close_btn = wx.Button(dialog, id=wx.ID_CANCEL, label="Close")
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizer(root)

        all_bindings = self._build_cheatsheet_text("")
        cheatsheet_ctrl.SetValue(all_bindings)
        apply_modal_ids(dialog, affirmative_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)

        def _on_cheatsheet_search(event: object) -> None:
            query = search.GetValue().strip().lower()
            cheatsheet_ctrl.SetValue(self._build_cheatsheet_text(query))
            event.Skip()

        search.Bind(wx.EVT_TEXT, _on_cheatsheet_search)
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))

        try:
            self._show_modal_dialog(dialog, "Key Cheatsheet")
        finally:
            dialog.Destroy()

    def _build_cheatsheet_text(self, query: str) -> str:
        """Return a human-readable key cheatsheet, filtered by *query*."""
        commands = self.commands.list(feature_manager=getattr(self, "features", None))
        lines: list[str] = []
        for cmd in sorted(commands, key=lambda c: c.title):
            binding = self.keymap.get(cmd.id) or DEFAULT_KEYMAP.get(cmd.id) or ""
            if query and query not in cmd.title.lower() and query not in binding.lower():
                continue
            if binding:
                lines.append(f"{cmd.title}: {binding}")
            else:
                lines.append(f"{cmd.title}: (no binding)")
        if not lines:
            return "No matching commands."
        return "\n".join(lines)

    def explain_unavailable_feature(self) -> None:
        """§8.1: 'Why Don't I See a Feature?' — explain why the focused item is greyed out."""
        wx = self._wx
        focused = wx.Window.FindFocus()
        if focused is None:
            self._set_status(
                "Focus the greyed-out button or menu item you are curious about, then press Alt+F1."
            )
            return
        # Try to read a help text from the widget.
        help_text = ""
        try:
            help_text = focused.GetHelpText()
        except Exception:  # noqa: BLE001
            pass
        name = ""
        try:
            name = focused.GetName() or focused.GetLabel()
        except Exception:  # noqa: BLE001
            pass
        enabled = True
        try:
            enabled = focused.IsEnabled()
        except Exception:  # noqa: BLE001
            pass

        if enabled:
            self._announce(
                f"{name or 'This item'} is currently available. "
                "To learn about unavailable features, focus a greyed-out button "
                "and press Alt+F1."
            )
            return

        # Check whether the feature is gated by a profile.
        feature_reason = ""
        if name:
            for item_id, feature_id in self._STATUS_BAR_FEATURES.items():
                label = self._STATUS_BAR_LABELS.get(item_id, "")
                if label.lower() in name.lower():
                    feature_manager = getattr(self, "features", None)
                    if feature_manager and not feature_manager.is_enabled(feature_id):
                        feature_reason = (
                            f"The '{feature_id}' feature is disabled in your current "
                            f"profile. Switch profiles (Alt+Shift+P) to enable it."
                        )
                    break

        if feature_reason:
            self._announce(feature_reason)
        elif help_text:
            self._announce(f"{name or 'This item'} is unavailable. {help_text}")
        else:
            self._announce(
                f"{name or 'This item'} is currently unavailable. "
                "It may require a file to be open, a selection to be active, "
                "or a feature enabled in the current profile."
            )

    def magic_paste(self) -> None:
        """§8.2: Inspect clipboard and offer format-aware paste options before inserting."""
        wx = self._wx
        clipboard = wx.TheClipboard
        if not clipboard.Open():
            self._set_status("Clipboard is unavailable")
            return
        try:
            has_text = clipboard.IsSupported(wx.DataFormat(wx.DF_TEXT))
            has_unicode = clipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT))
            has_bitmap = clipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP))
            raw_text = ""
            if has_text or has_unicode:
                obj = wx.TextDataObject()
                if clipboard.GetData(obj):
                    raw_text = obj.GetText()
        finally:
            clipboard.Close()

        # Detect clipboard content type.
        content_type = "plain text"
        is_url = raw_text.strip().startswith(("http://", "https://", "ftp://"))
        is_markdown = bool(raw_text.strip()) and (
            raw_text.startswith("#")
            or "\n#" in raw_text
            or "**" in raw_text
            or raw_text.startswith("- ")
            or "\n- " in raw_text
            or raw_text.startswith("[")
            and "](" in raw_text
        )

        # Detect HTML (before checking markdown, since HTML can look like markdown).
        html_context = analyze_paste(raw_text)
        is_html = html_context.is_html

        if has_bitmap:
            content_type = "image"
        elif is_html:
            content_type = "HTML"
        elif is_url:
            content_type = "URL"
        elif is_markdown:
            content_type = "Markdown"

        if content_type == "plain text":
            # Nothing special detected — fall through to standard paste.
            if self.editor is not None:
                self.editor.Paste()
            return

        # Show the magic paste picker.
        dialog = wx.Dialog(
            self.frame,
            title=f"Magic Paste: {content_type} detected",
            style=wx.DEFAULT_DIALOG_STYLE,
        )
        dialog.SetSize((480, 280))
        root = wx.BoxSizer(wx.VERTICAL)

        label_text = f"Clipboard contains {content_type}. How would you like to paste it?"
        root.Add(wx.StaticText(dialog, label=label_text), 0, wx.ALL | wx.EXPAND, 8)

        choices: list[tuple[str, str]] = [("Paste as plain text", "plain")]
        if content_type == "URL":
            choices.insert(0, ("Paste as Markdown link", "link"))
        elif content_type == "Markdown":
            choices.insert(0, ("Paste as Markdown (keep formatting)", "markdown"))
        elif content_type == "HTML":
            choices.insert(0, ("Paste HTML as clean text", "html_clean"))
            choices.insert(1, ("Paste HTML as-is", "html_raw"))
        elif content_type == "image":
            choices.insert(0, ("Insert image reference", "image_ref"))

        choice_box = wx.RadioBox(
            dialog,
            label="Paste mode",
            choices=[c[0] for c in choices],
            style=wx.RA_SPECIFY_ROWS,
        )
        choice_box.SetSelection(0)
        root.Add(choice_box, 1, wx.ALL | wx.EXPAND, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(dialog, id=wx.ID_OK, label="Paste")
        cancel_btn = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
        btn_row.AddStretchSpacer(1)
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn, 0)
        root.Add(btn_row, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        try:
            result = self._show_modal_dialog(dialog, "Magic Paste")
        finally:
            dialog.Destroy()

        if result != wx.ID_OK:
            return

        mode_key = choices[choice_box.GetSelection()][1]
        if mode_key == "plain":
            if self.editor is not None:
                self.editor.Paste()
        elif mode_key == "link":
            if self.editor is not None:
                link_text = raw_text.strip().rstrip("/").rsplit("/", 1)[-1] or "link"
                self.editor.WriteText(f"[{link_text}]({raw_text.strip()})")
        elif mode_key == "markdown":
            if self.editor is not None:
                self.editor.WriteText(raw_text)
        elif mode_key == "html_clean":
            if self.editor is not None:
                clean_text = html_context.get_paste_text(clean=True)
                self.editor.WriteText(clean_text)
                if self.quill_settings.auto_clean_html_paste:
                    self._set_status(f"Pasted cleaned HTML ({len(clean_text)} chars)")
        elif mode_key == "html_raw":
            if self.editor is not None:
                self.editor.WriteText(raw_text)
        elif mode_key == "image_ref":
            if self.editor is not None:
                self.editor.WriteText("![image]()")

    def _check_tts_fallback_on_startup(self) -> None:
        """§8.2 TTS-FALLBACK-ANNOUNCE: show a status-bar prompt when pyttsx3 fails to init."""
        try:
            from quill.platform.windows.prism_bridge import tts_init_failed

            if not tts_init_failed():
                return
            self._set_status(
                "Screen reader fallback active. TTS engine failed to start. "
                "Press F8 to toggle overwrite mode / check menus for Retry TTS."
            )
            self._record_notification(
                "Text-to-speech (pyttsx3) failed to start. "
                "Screen reader fallback is active. "
                "To retry, run Tools > Retry TTS Engine.",
                "accessibility",
            )
        except ImportError:
            pass

    def _binding_for(self, command_id: str) -> str | None:
        binding = self.keymap.get(command_id)
        if binding is None:
            return DEFAULT_KEYMAP.get(command_id)
        cleaned = binding.strip()
        if not cleaned:
            return None
        return cleaned

    def _menu_label(self, title: str, command_id: str) -> str:
        label = self._ensure_menu_customization().item_label(command_id, title)
        binding = self.commands.keybinding_for(command_id)
        if binding is None:
            return label
        return f"{label}\t{binding}"

    def _ensure_menu_customization(self) -> MenuCustomization:
        """Return the loaded menu customization, loading it on first use."""
        existing = getattr(self, "_menu_customization", None)
        if existing is None:
            try:
                existing = load_menu_customization()
            except Exception:
                existing = MenuCustomization()
            self._menu_customization = existing
        return existing

    def _apply_menu_customization(self, menu_bar: object) -> None:
        """Reorder, hide, and relabel top-level menus per the saved customization.

        Runs as a post-build transform pass so the imperative ``_build_menu``
        construction stays untouched. The pass is keyed by each menu's factory
        label, and bails out untouched if anything looks unexpected so a corrupt
        customization can never produce a broken menu bar.
        """
        cust = self._ensure_menu_customization()
        default_keys = [key for key, _ in _TOP_MENU_DEFS]
        cust.reconcile(set(default_keys), set())
        if not cust.is_customized():
            return

        default_by_key = dict(_TOP_MENU_DEFS)
        label_to_key = {_normalize_menu_label(label): key for key, label in _TOP_MENU_DEFS}
        try:
            count = menu_bar.GetMenuCount()
        except Exception:
            return
        current: list[tuple[object, str | None]] = []
        for index in range(count):
            menu = menu_bar.GetMenu(index)
            label = menu_bar.GetMenuLabelText(index)
            current.append((menu, label_to_key.get(_normalize_menu_label(label))))
        if any(key is None for _, key in current):
            return

        menu_by_key = {key: menu for menu, key in current if key is not None}
        desired = cust.visible_top_keys(default_keys)
        # Detach every menu (from the end so indices stay valid), then re-append
        # the visible ones in the desired order and destroy the hidden ones.
        for index in range(menu_bar.GetMenuCount() - 1, -1, -1):
            menu_bar.Remove(index)
        for key in desired:
            menu = menu_by_key[key]
            menu_bar.Append(menu, cust.top_label(key, default_by_key[key]))
        for key, menu in menu_by_key.items():
            if key not in desired:
                try:
                    menu.Destroy()
                except Exception:
                    pass

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, "_recent_menu") or not hasattr(self, "_wx"):
            return
        if not self._menu_updates_allowed():
            self._request_menu_refresh()
            return
        while self._recent_menu.GetMenuItemCount() > 0:
            item = self._recent_menu.FindItemByPosition(0)
            if item is None:
                break
            self._recent_menu.DestroyItem(item)
        self._recent_menu_ids.clear()
        if not self.recent_files:
            item = self._recent_menu.Append(self._wx.ID_ANY, "(No recent files)")
            item.Enable(False)
            self._recent_menu.AppendSeparator()
            self._recent_menu.Append(self._id_clear_recent, "C&lear Recent Files")
            return
        for path in self.recent_files:
            menu_id = self._wx.NewIdRef()
            self._recent_menu.Append(menu_id, str(path))
            self._recent_menu_ids[int(menu_id)] = path
        self._recent_menu.AppendSeparator()
        self._recent_menu.Append(self._id_clear_recent, "C&lear Recent Files")

    def _on_open_recent(self, event: object) -> None:
        menu_id = event.GetId()
        path = self._recent_menu_ids.get(menu_id)
        if menu_id == int(self._id_clear_recent):
            self.clear_recent_files()
            return
        if path is None:
            event.Skip()
            return
        self.open_file(path)

    def _refresh_title(self) -> None:
        modified_suffix = self._dirty_title_suffix()
        self.frame.SetTitle(f"{self._title_subject()}{modified_suffix} - Quill")
        if self._active_tab_index >= 0 and self._active_tab_index < self.notebook.GetPageCount():
            page_title = f"{self.document.name}{self._remote_title_suffix()}{modified_suffix}"
            self._set_tab_page_text(self._active_tab_index, page_title)
        self._refresh_statusbar()

    def _remote_title_suffix(self) -> str:
        tab = self._active_tab()
        suffix = getattr(tab, "source_label", "")
        if not suffix:
            return ""
        return f" ({suffix})"

    def _title_subject(self) -> str:
        path = self.document.path
        name = self.document.name
        mode = getattr(self.settings, "title_bar_path_mode", "name")
        if mode == "full_path" and path is not None:
            return str(path)
        return name

    def _dirty_title_suffix(self) -> str:
        if not self.document.modified:
            return ""
        style = getattr(self.settings, "dirty_title_style", "text")
        if style == "asterisk":
            return " *"
        if style == "asterisk_text":
            return " * [modified]"
        return " [modified]"

    def _current_markup_context(self) -> str:
        path = self.document.path
        if path is not None:
            suffix = path.suffix.lower()
            if suffix in {".md", ".markdown", ".mdown", ".mkd"}:
                return "markdown"
            if suffix in {".html", ".htm", ".xhtml"}:
                return "html"
        sample = self.editor.GetValue()[:4000]
        if re.search(
            r"<\s*(html|head|body|div|span|p|h[1-6]|section|article)\b", sample, re.IGNORECASE
        ):
            return "html"
        markdown_hits = 0
        if re.search(r"(?m)^\s{0,3}#{1,6}\s+\S", sample):
            markdown_hits += 1
        if re.search(r"(?m)^\s{0,3}(-|\*|\+)\s+\S", sample):
            markdown_hits += 1
        if re.search(r"\[[^\]]+\]\([^)]+\)", sample):
            markdown_hits += 1
        if re.search(r"(?m)^```", sample):
            markdown_hits += 1
        if markdown_hits >= 2:
            return "markdown"
        return "plain"

    def _refresh_contextual_menu_items(self) -> None:
        if not self._menu_updates_allowed():
            self._request_menu_refresh()
            return
        get_menu_bar = getattr(self.frame, "GetMenuBar", None)
        if not callable(get_menu_bar):
            return
        menu_bar = get_menu_bar()
        if menu_bar is None:
            return
        context = self._current_markup_context()
        html_only = context == "html"
        markdown_ready = context in {"markdown", "plain"}
        active_surface = self._active_markup_surface()
        structured_markup_ready = active_surface in {"markdown", "html"}
        markdown_ids = tuple(
            item_id
            for item_id in (
                self._id_insert_markdown_tag,
                self._id_heading_1,
                self._id_heading_2,
                self._id_heading_3,
                self._id_heading_4,
                self._id_heading_5,
                self._id_heading_6,
                getattr(self, "_id_style_headings", None),
                self._id_insert_bullet_list,
                self._id_insert_numbered_list,
                self._id_insert_task_list,
                getattr(self, "_id_open_list_manager", None),
                self._id_insert_code_block,
                self._id_insert_footnote,
            )
            if item_id is not None
        )
        structured_markup_ids = (self._id_insert_table,)
        html_ids = (self._id_insert_html_tag,)
        for item_id in markdown_ids:
            menu_item = menu_bar.FindItemById(item_id)
            if menu_item is not None:
                menu_item.Enable(markdown_ready)
        for item_id in structured_markup_ids:
            menu_item = menu_bar.FindItemById(item_id)
            if menu_item is not None:
                menu_item.Enable(structured_markup_ready)
        for item_id in html_ids:
            menu_item = menu_bar.FindItemById(item_id)
            if menu_item is not None:
                menu_item.Enable(html_only)

    def _set_status(self, message: str) -> None:
        self._status_message = message
        self._refresh_statusbar()
        throttle_ms = int(getattr(self.settings, "announcement_throttle_ms", 0) or 0)
        if throttle_ms > 0:
            now = time.monotonic()
            last = getattr(self, "_last_status_announce_at", 0.0)
            if (now - last) * 1000.0 < throttle_ms:
                return
            self._last_status_announce_at = now
        announce(message)

    def _set_status_quiet(self, message: str) -> None:
        """Update the status bar text WITHOUT speaking it. Used for per-keystroke
        states like "Modified" so the screen reader doesn't repeat it on every
        character (it already echoes what you type)."""
        self._status_message = message
        self._refresh_statusbar()

    def _feature_enabled(self, feature_id: str) -> bool:
        feature_manager = getattr(self, "features", None)
        if feature_manager is None:
            return True
        return feature_manager.is_enabled(feature_id)

    def _record_notification(self, message: str, category: str = "info") -> None:
        self._notifications = add_notification(message, category)

    def _announce(self, message: str) -> None:
        self._status_message = message
        self._refresh_statusbar()
        engine = getattr(self, "_announcement_engine", None)
        if engine is None:
            return
        backend_error = engine.announce(message)
        if backend_error and backend_error != self._announcement_error_reported:
            self._announcement_error_reported = backend_error
            self._record_notification(backend_error, "accessibility")

    def _show_modal_dialog(
        self, dialog: object, label: str, *, restore_editor_focus: bool = True
    ) -> int:
        # Land initial focus on the dialog's primary content control rather than
        # its OK button. Only custom wx.Dialog surfaces are adjusted; native
        # dialogs (MessageDialog, FileDialog, RichMessageDialog, ...) manage
        # their own focus and must not be touched.
        wx = getattr(self, "_wx", None)
        dialog_cls = getattr(wx, "Dialog", None)
        if dialog_cls is not None and type(dialog) is dialog_cls:
            focus_primary_control(dialog)
        result = show_modal_dialog(
            dialog,
            label,
            announce=announce,
            enter_region=self._region_tracker.enter,
            exit_region=self._region_tracker.exit,
        )
        if restore_editor_focus:
            editor = getattr(self, "editor", None)
            if editor is not None and hasattr(editor, "SetFocus"):
                call_after = getattr(self._wx, "CallAfter", None)
                if callable(call_after):
                    call_after(editor.SetFocus)
                else:
                    editor.SetFocus()
        return result

    def _show_message_box(self, message: str, caption: str, style: int) -> int:
        self._region_tracker.enter(caption)
        announce(f"Entered {caption} dialog")
        try:
            result = self._wx.MessageBox(message, caption, style)
        finally:
            announce(f"Exited {caption} dialog")
            self._region_tracker.exit(caption)
        return result

    def _show_error_with_hint(self, message: str, caption: str, hint: str) -> None:
        """§8.2 Soft error recovery link: show an error with a 'What to try next' toggle.

        Displays a non-native dialog so we can include an expandable
        read-only text area containing *hint* without cluttering the primary
        message.  Screen readers announce the hint area label automatically.
        """
        wx = self._wx
        self._region_tracker.enter(caption)
        announce(f"Entered {caption} dialog")
        try:
            dlg = wx.Dialog(
                self.frame,
                title=caption,
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            dlg.SetMinSize((420, -1))
            root = wx.BoxSizer(wx.VERTICAL)

            msg_label = wx.StaticText(dlg, label=message)
            msg_label.Wrap(400)
            root.Add(msg_label, 0, wx.EXPAND | wx.ALL, 12)

            hint_label = wx.StaticText(dlg, label="What to try next:")
            hint_label.Hide()
            root.Add(hint_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

            hint_ctrl = wx.TextCtrl(
                dlg,
                value=hint,
                style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            )
            hint_ctrl.SetMinSize((-1, 80))
            hint_ctrl.Hide()
            root.Add(hint_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

            btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
            toggle_btn = wx.Button(dlg, label="What to try next...")
            ok_btn = wx.Button(dlg, id=wx.ID_OK, label="OK")
            ok_btn.SetDefault()
            btn_sizer.Add(toggle_btn, 0, wx.RIGHT, 8)
            btn_sizer.AddStretchSpacer()
            btn_sizer.Add(ok_btn, 0)
            root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 12)

            dlg.SetSizer(root)
            dlg.Fit()
            apply_modal_ids(dlg, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)

            def _toggle(_event: object) -> None:
                visible = not hint_ctrl.IsShown()
                hint_label.Show(visible)
                hint_ctrl.Show(visible)
                toggle_btn.SetLabel("Hide hint" if visible else "What to try next...")
                dlg.Layout()
                dlg.Fit()
                if visible:
                    announce(f"What to try next: {hint}")

            toggle_btn.Bind(wx.EVT_BUTTON, _toggle)
            dlg.CentreOnParent()
            self._show_modal_dialog(dlg, caption)
            dlg.Destroy()
        finally:
            announce(f"Exited {caption} dialog")
            self._region_tracker.exit(caption)

    def _prompt_untrusted_location(self, folder: Path) -> bool | None:
        # Native dialog (#74): the old hand-rolled wx.Dialog never set its own
        # sizer (only the inner panel did) and its OK/Cancel did nothing.
        # wx.RichMessageDialog gives reliable native buttons plus the "trust"
        # checkbox, and is read directly by VoiceOver/NVDA.
        # Returns None to cancel, or True/False = open + whether to trust.
        wx = self._wx
        dialog = wx.RichMessageDialog(
            self.frame,
            f"{folder} is not trusted yet. Open this file anyway?",
            "Untrusted Location",
            wx.OK | wx.CANCEL | wx.ICON_WARNING,
        )
        if hasattr(dialog, "SetOKCancelLabels"):
            dialog.SetOKCancelLabels("Open", "Cancel")
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.ShowCheckBox("Trust this folder for future opens")
        result = self._show_modal_dialog(dialog, "Untrusted Location")
        trust = bool(dialog.IsCheckBoxChecked())
        dialog.Destroy()
        if result != wx.ID_OK:
            return None
        return trust

    def _prompt_unsaved_changes_action(
        self,
        title: str,
        message: str,
        affirmative_label: str,
        negative_label: str,
    ) -> int:
        wx = self._wx
        # Use the native message dialog rather than a hand-rolled wx.Dialog.
        # The custom version wired each button to EndModal() by hand and layered
        # a CHAR_HOOK on top; on macOS that machinery could swallow the Save /
        # Don't Save activations so every button behaved like Cancel. The native
        # dialog has rock-solid button handling and is read directly by VoiceOver
        # / NVDA, and ShowModal() returns exactly wx.ID_YES / wx.ID_NO /
        # wx.ID_CANCEL — the contract both callers depend on.
        dialog = wx.MessageDialog(
            self.frame,
            message,
            title,
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
        )
        if hasattr(dialog, "SetYesNoCancelLabels"):
            dialog.SetYesNoCancelLabels(affirmative_label, negative_label, "Cancel")
        try:
            return self._show_modal_dialog(dialog, title)
        finally:
            dialog.Destroy()

    def _confirm_discard_changes(self) -> bool:
        wx = self._wx
        if not getattr(self.settings, "confirm_destructive_actions", True):
            return True
        result = self._prompt_unsaved_changes_action(
            "Unsaved changes",
            "You have unsaved changes. Reload and discard them?",
            "Reload",
            "Keep Editing",
        )
        return result == wx.ID_YES

    def _run_background_task(
        self,
        label: str,
        work: Callable[[Callable[[str, int, int], None]], object],
        on_success: Callable[[object], None],
        *,
        notify_on_success: bool = False,
        notify_on_error: bool = False,
        notification_category: str = "info",
    ) -> None:
        self._background_task_count = getattr(self, "_background_task_count", 0) + 1
        task_id = self._track_background_task_start(label)
        self._set_status(f"{label} started")

        def progress(message: str, current: int, total: int) -> None:
            self._wx.CallAfter(
                self._track_background_task_progress,
                task_id,
                message,
                current,
                total,
            )
            self._wx.CallAfter(self._set_status, f"{label}: {current}/{total} - {message}")

        def worker() -> None:
            try:
                result = work(progress)
            except Exception as error:  # surfaced to the user on the UI thread
                self._wx.CallAfter(
                    self._finish_background_task,
                    label,
                    error,
                    None,
                    on_success,
                    task_id,
                    notify_on_success,
                    notify_on_error,
                    notification_category,
                )
                return
            self._wx.CallAfter(
                self._finish_background_task,
                label,
                None,
                result,
                on_success,
                task_id,
                notify_on_success,
                notify_on_error,
                notification_category,
            )

        threading.Thread(  # GATE-40-OK: main-frame background task dispatch.
            target=worker, daemon=True
        ).start()

    def _finish_background_task(
        self,
        label: str,
        error: Exception | None,
        result: object,
        on_success: Callable[[object], None],
        task_id: int,
        notify_on_success: bool,
        notify_on_error: bool,
        notification_category: str,
    ) -> None:
        self._background_task_count = max(0, getattr(self, "_background_task_count", 1) - 1)
        if error is not None:
            self._track_background_task_finish(task_id, "failed", str(error))
            # §8.2 Soft error recovery link: file-open and network background tasks get a hint.
            if label.startswith("Opening "):
                self._show_error_with_hint(
                    str(error),
                    label,
                    "Check that the file exists, is not locked by another application, "
                    "and that QUILL has permission to read it. "
                    "For format errors, try opening in a text editor first to verify the content.",
                )
            else:
                self._show_message_box(str(error), label, self._wx.ICON_ERROR | self._wx.OK)
            self._set_status(f"{label} failed")
            if notify_on_error:
                self._record_notification(f"{label} failed: {error}", notification_category)
            return
        self._track_background_task_finish(task_id, "completed", "Completed")
        on_success(result)
        if notify_on_success:
            self._record_notification(f"{label} completed", notification_category)

    def _track_background_task_start(self, label: str) -> int:
        self._background_task_sequence = int(getattr(self, "_background_task_sequence", 0)) + 1
        task_id = self._background_task_sequence
        tasks = getattr(self, "_background_tasks", [])
        tasks.append({
            "id": task_id,
            "label": label,
            "status": "running",
            "progress": "Starting",
            "started_at": datetime.now(UTC).isoformat(),
            "finished_at": "",
        })
        self._background_tasks = tasks[-100:]
        return task_id

    def _track_background_task_progress(
        self,
        task_id: int,
        message: str,
        current: int,
        total: int,
    ) -> None:
        tasks = getattr(self, "_background_tasks", [])
        for task in reversed(tasks):
            if int(task.get("id", -1)) != task_id:
                continue
            task["progress"] = f"{current}/{total} - {message}"
            break
        self._maybe_refresh_live_status_tabs()

    def _track_background_task_finish(self, task_id: int, status: str, detail: str) -> None:
        tasks = getattr(self, "_background_tasks", [])
        for task in reversed(tasks):
            if int(task.get("id", -1)) != task_id:
                continue
            task["status"] = status
            task["progress"] = detail
            task["finished_at"] = datetime.now(UTC).isoformat()
            break
        self._maybe_refresh_live_status_tabs()

    def _status_tab_indexes(self) -> list[int]:
        getter = getattr(self.notebook, "GetPageText", None)
        if not callable(getter):
            return []
        indexes: list[int] = []
        for index in range(self.notebook.GetPageCount()):
            if getter(index) == "Application Status":
                indexes.append(index)
        return indexes

    def _ensure_status_page_timer(self) -> None:
        if self._status_page_timer is not None:
            return
        wx = self._wx
        timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_status_page_timer, timer)
        self._status_page_timer = timer

    def _set_status_page_live_updates(self, enabled: bool) -> None:
        self._status_page_live_updates = enabled
        self._status_page_last_announce_at = time.monotonic()
        self._status_page_last_announce_signature = ""
        timer = self._status_page_timer
        if timer is None:
            return
        if enabled:
            timer.Start(self._status_page_refresh_ms)
        else:
            timer.Stop()

    def _status_page_announcement_interval_seconds(self) -> int | None:
        cadence = str(
            getattr(self.settings, "status_page_refresh_announcement_cadence", "quiet")
        ).lower()
        if cadence == "quiet":
            return None
        if cadence == "verbose":
            return 10
        return 30

    def _status_page_refresh_signature(self) -> str:
        tasks = getattr(self, "_background_tasks", [])[-20:]
        task_snapshot = [
            {
                "id": int(task.get("id", -1)),
                "status": str(task.get("status", "")),
                "progress": str(task.get("progress", "")),
            }
            for task in tasks
        ]
        bw_snapshot = {
            model_id: {
                "status": str(entry.get("status", "")),
                "progress": str(entry.get("progress", "")),
            }
            for model_id, entry in sorted(self._bw_download_status.items())
        }
        payload = {
            "active_tasks": int(getattr(self, "_background_task_count", 0)),
            "notifications": len(getattr(self, "_notifications", [])),
            "bw_provider_mode": str(getattr(self.settings, "bw_provider_mode", "local_first")),
            "bw_provider_id": str(getattr(self.settings, "bw_provider_id", "local_whisper")),
            "bw_model": str(getattr(self.settings, "bw_speech_model_id", "whisper-base")),
            "tasks": task_snapshot,
            "bw_downloads": bw_snapshot,
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _maybe_announce_status_page_refresh(self, signature: str) -> None:
        interval_seconds = self._status_page_announcement_interval_seconds()
        if interval_seconds is None:
            return
        if signature == self._status_page_last_announce_signature:
            return
        now = time.monotonic()
        if now - self._status_page_last_announce_at < interval_seconds:
            return
        active_tasks = int(getattr(self, "_background_task_count", 0))
        bw_running = sum(
            1
            for entry in self._bw_download_status.values()
            if str(entry.get("status", "")).lower() == "running"
        )
        message = f"Status page refreshed. {active_tasks} background task(s) active."
        # BITS Whisperer is deferred to QUILL 2.0; only name transcription downloads
        # when one is actually running, which never happens in a 1.0 build.
        if bw_running:
            message += f" {bw_running} BITS Whisperer download(s) running."
        self._announce(message)
        self._status_page_last_announce_at = now
        self._status_page_last_announce_signature = signature

    def _refresh_help_status_tabs(self) -> None:
        indexes = self._status_tab_indexes()
        if not indexes:
            self._set_status_page_live_updates(False)
            return
        report_html = self._build_help_status_html()
        selected_index = self._current_tab_index()
        for index in indexes:
            if not (0 <= index < len(self._document_tabs)):
                continue
            tab = self._document_tabs[index]
            tab.editor.ChangeValue(report_html)
            tab.document.set_text(report_html)
            tab.document.modified = False
            if index == selected_index and self._browser_preview_session is not None:
                self._show_side_preview_for(tab)

    def _maybe_refresh_live_status_tabs(self) -> None:
        if not self._status_page_live_updates:
            return
        self._refresh_help_status_tabs()

    def _on_status_page_timer(self, _event: object) -> None:
        self._refresh_help_status_tabs()
        self._maybe_announce_status_page_refresh(self._status_page_refresh_signature())

    def _open_generated_tab(self, title: str, text: str) -> int:
        index = self._create_document_tab(
            Document(text=text, path=None, modified=False), select=True
        )
        self._document_tabs[index].editor.SetEditable(False)
        self._set_tab_page_text(index, title)
        return index

    def _current_tab_index(self) -> int:
        return self.notebook.GetSelection()

    def _find_tab_index(self, path: Path | None) -> int:
        if path is None:
            return -1
        resolved = path.resolve()
        for index, tab in enumerate(self._document_tabs):
            if tab.document.path is not None and tab.document.path.resolve() == resolved:
                return index
        return -1

    def _select_tab(self, index: int) -> None:
        if index < 0 or index >= len(self._document_tabs):
            return
        change_selection = getattr(self.notebook, "ChangeSelection", None)
        if callable(change_selection):
            change_selection(index)
        else:
            self.notebook.SetSelection(index)
        self._activate_tab(index)

    def _active_tab(self) -> _DocumentTab:
        index = self._current_tab_index()
        if index < 0:
            index = self._active_tab_index
        return self._document_tabs[index]

    def _close_tab(self, index: int) -> None:
        if index < 0 or index >= len(self._document_tabs):
            return
        self.notebook.DeletePage(index)
        del self._document_tabs[index]
        if not self._document_tabs:
            self._create_document_tab(Document(), select=True)
            self._refresh_sessions_menu()
            return
        next_index = min(index, len(self._document_tabs) - 1)
        self._select_tab(next_index)
        self._refresh_sessions_menu()

    def _prompt_to_save_active_document(self, action_label: str) -> bool:
        if not self.document.modified:
            return True
        wx = self._wx
        result = self._prompt_unsaved_changes_action(
            "Unsaved changes",
            f"You have unsaved changes. Save before {action_label}?",
            "Save",
            "Don't Save",
        )
        if result == wx.ID_CANCEL:
            return False
        if result == wx.ID_YES:
            self.save_file()
            return not self.document.modified
        if result == wx.ID_NO:
            return True
        return True

    def _can_close_all_documents(self) -> bool:
        for index in range(len(self._document_tabs) - 1, -1, -1):
            self._select_tab(index)
            if not self._prompt_to_save_active_document("closing"):
                return False
        return True

    def new_file(self) -> None:
        self._clear_empty_workspace_state()
        document = Document()
        self._create_document_tab(document, select=True)
        self._persistent_undo_history = [""]
        self._persistent_undo_index = 0
        self._location_ring = LocationRing()
        self._location_ring.record(0)
        self._set_status("New document")
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        post_sound(SoundEvent.DOCUMENT_CREATED)

    def _file_dialog_default_dir(self) -> str:
        """Return the best initial directory for a file open/save dialog (#168).

        Priority: session last-used dir → startup_folder setting → Documents → "".
        startup_folder is the persistent user preference; _last_file_dir tracks the
        most recent location within the current session and overrides it once set.
        """
        last = self._last_file_dir
        if last and Path(last).is_dir():
            return last
        configured = getattr(self.settings, "startup_folder", "")
        if configured and Path(configured).is_dir():
            return configured
        try:
            docs = self._wx.StandardPaths.Get().GetDocumentsDir()
            if docs and Path(docs).is_dir():
                return docs
        except Exception:
            pass
        return ""

    def open_file(
        self,
        path: Path | None = None,
        record_recent: bool = True,
        refresh_existing: bool = False,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        self._clear_empty_workspace_state()
        wx = self._wx
        selected_path = path
        if selected_path is None:
            with wx.FileDialog(
                self.frame,
                "Open text file",
                defaultDir=self._file_dialog_default_dir(),
                wildcard=(
                    "Supported files"
                    " (*.txt;*.md;*.html;*.htm;*.xhtml;*.json;*.yaml;*.yml;"
                    "*.toml;*.xml;*.csv;*.tsv;*.ipynb;*.sqlite;*.db;"
                    "*.doc;*.docx;*.ppt;*.pptx;*.epub;*.pages;*.pdf;*.odt;*.rtf;"
                    "*.py;*.js;*.jsx;*.ts;*.tsx;*.kt;*.kts;*.go;*.rs;*.c;*.cpp;"
                    "*.h;*.hpp;*.java;*.swift;*.cs;*.rb;*.php;*.sh;*.ps1;*.lua;"
                    "*.css;*.scss;*.less;*.sql;*.log;*.diff;*.patch;*.ini;*.cfg;*.conf;"
                    "*.gradle;*.properties;*.gitignore;*.env)|"
                    "*.txt;*.md;*.html;*.htm;*.xhtml;*.json;*.yaml;*.yml;"
                    "*.toml;*.xml;*.csv;*.tsv;*.ipynb;*.sqlite;*.db;"
                    "*.doc;*.docx;*.ppt;*.pptx;*.epub;*.pages;*.pdf;*.odt;*.rtf;"
                    "*.py;*.js;*.jsx;*.ts;*.tsx;*.kt;*.kts;*.go;*.rs;*.c;*.cpp;"
                    "*.h;*.hpp;*.java;*.swift;*.cs;*.rb;*.php;*.sh;*.ps1;*.lua;"
                    "*.css;*.scss;*.less;*.sql;*.log;*.diff;*.patch;*.ini;*.cfg;*.conf;"
                    "*.gradle;*.properties;*.gitignore;*.env|"
                    "Documents (*.txt;*.md;*.html;*.htm;*.docx;*.odt;*.rtf;*.pdf;*.epub)|"
                    "*.txt;*.md;*.html;*.htm;*.docx;*.odt;*.rtf;*.pdf;*.epub|"
                    "Source code"
                    " (*.py;*.js;*.jsx;*.ts;*.tsx;*.kt;*.kts;*.go;*.rs;*.c;*.cpp;"
                    "*.h;*.hpp;*.java;*.swift;*.cs;*.rb;*.php;*.sh;*.ps1;*.lua)|"
                    "*.py;*.js;*.jsx;*.ts;*.tsx;*.kt;*.kts;*.go;*.rs;*.c;*.cpp;"
                    "*.h;*.hpp;*.java;*.swift;*.cs;*.rb;*.php;*.sh;*.ps1;*.lua|"
                    "All files (*.*)|*.*"
                ),
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if self._show_modal_dialog(dialog, "Open text file") != wx.ID_OK:
                    return
                selected_path = Path(dialog.GetPath())
                self._last_file_dir = str(selected_path.parent)
        if selected_path is None:
            return
        existing_index = self._find_tab_index(selected_path)
        if existing_index >= 0 and not refresh_existing:
            self._select_tab(existing_index)
            if record_recent:
                self._record_recent(selected_path)
            self._position_editor_at(line=line, column=column)
            self._set_status(f"Opened {selected_path.name}")
            return
        if not is_trusted_location(selected_path, self._trusted_locations):
            trust_folder = self._prompt_untrusted_location(selected_path.parent.resolve())
            if trust_folder is None:
                self._set_status("Open cancelled for untrusted location")
                return
            if trust_folder:
                self._trusted_locations.add(selected_path.parent.resolve())
                save_trusted_locations(self._trusted_locations)

        suffix = selected_path.suffix.lower()

        def finish(result: object) -> None:
            self._finish_open_document(
                result,
                selected_path=selected_path,
                suffix=suffix,
                existing_index=existing_index,
                record_recent=record_recent,
                line=line,
                column=column,
            )

        if suffix in _OFFICE_STREAM_SUFFIXES:
            # PERF-12: large office and PDF files are parsed on a worker thread
            # so the UI thread never blocks while reading them. Any UI prompt
            # (the Word open-mode chooser) is resolved here, before the worker
            # starts, because workers must not touch wx.
            word_mode = (
                self._resolve_word_open_mode(selected_path) if suffix in {".doc", ".docx"} else None
            )
            self._run_background_task(
                f"Opening {selected_path.name}",
                lambda _progress: read_open_document(selected_path, suffix, word_mode=word_mode),
                finish,
            )
            return

        csv_mode = None
        if suffix in {".csv", ".tsv"}:
            csv_mode = self._resolve_csv_open_mode(selected_path)
        finish(read_open_document(selected_path, suffix, csv_mode=csv_mode))

    def _finish_open_document(
        self,
        result: object,
        *,
        selected_path: Path,
        suffix: str,
        existing_index: int,
        record_recent: bool,
        line: int | None,
        column: int | None,
    ) -> None:
        """Install a freshly read document into the UI (PERF-12 continuation).

        Always runs on the UI thread: directly for cheap reads, or marshalled
        through ``wx.CallAfter`` by :meth:`_run_background_task` for the office
        and PDF formats that were parsed on a worker thread.
        """
        assert isinstance(result, tuple)
        loaded, epub_book = result
        self._epub_book = epub_book if suffix == ".epub" else None
        if existing_index >= 0:
            tab = self._document_tabs[existing_index]
            tab.document = loaded
            tab.editor.ChangeValue(loaded.text)
            self._load_persistent_undo_state(selected_path, loaded.text)
            self._select_tab(existing_index)
        else:
            if loaded.source_metadata.get("csv_open_mode") == "grid":
                self._create_csv_document_tab(loaded, select=True)
            elif loaded.source_metadata.get("word_open_mode") == "structured":
                self._create_word_document_tab(loaded, select=True)
            elif suffix == ".rtf" and self._rich_editor_enabled():
                # An .rtf is inherently a rich document, so it opens in the Rich
                # text lens when that lens is enabled (rtf.md "Opening files").
                self._create_rich_document_tab(loaded, select=True)
                self._announce_rtf_safety(loaded)
            else:
                self._create_document_tab(loaded, select=True)
            self._load_persistent_undo_state(selected_path, loaded.text)
            self._location_ring = LocationRing()
            self._location_ring.record(0)
        self._position_editor_at(line=line, column=column)
        if record_recent:
            self._record_recent(selected_path)
        self._refresh_title()
        self._last_intake_report = build_intake_report(loaded)
        self._set_status(build_intake_summary(loaded))
        # Switch to the profile mapped to this file's extension, if one is set (#138).
        self.maybe_switch_profile_for_open(selected_path)
        # FEAT-19: (re)start the external change watcher for the freshly loaded document.
        self._stop_external_change_watcher()
        self._start_external_change_watcher()
        # #187: SR users must not need Alt+Tab after open. Defer SetFocus so the
        # sizer and notebook have finished layout before focus moves.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after) and hasattr(self, "editor"):
            call_after(self.editor.SetFocus)
        self._announce(f"Opened {loaded.name or selected_path.name}")

    def _position_editor_at(self, line: int | None = None, column: int | None = None) -> None:
        if line is None and column is None:
            return
        text = self.editor.GetValue()
        target = self._cursor_position_for_line_column(text, line=line, column=column)
        self.editor.SetInsertionPoint(target)
        self.editor.SetSelection(target, target)
        self._set_status(
            f"Moved cursor to line {line if line is not None else 1}, "
            f"column {column if column is not None else 1}"
        )

    def _cursor_position_for_line_column(
        self,
        text: str,
        *,
        line: int | None,
        column: int | None,
    ) -> int:
        target_line = 1 if line is None else max(1, line)
        target_column = 1 if column is None else max(1, column)
        if target_line <= 1 and target_column <= 1:
            return 0
        offset = 0
        current_line = 1
        for segment in text.splitlines(keepends=True):
            if current_line == target_line:
                line_text = segment.rstrip("\r\n")
                return min(offset + target_column - 1, offset + len(line_text))
            offset += len(segment)
            current_line += 1
        return len(text)

    def _resolve_csv_open_mode(self, path: Path) -> str:
        if not _csv_feature_enabled():
            return "text"
        mode = getattr(self.settings, "csv_open_mode", "prompt")
        if mode in {"grid", "text"}:
            return mode
        return self._prompt_csv_open_mode(path)

    def _resolve_word_open_mode(self, path: Path) -> str:
        if not _word_feature_enabled():
            return "text"
        mode = getattr(self.settings, "word_open_mode", "prompt")
        if mode in {"structured", "text"}:
            return mode
        return self._prompt_word_open_mode(path)

    def _prompt_open_mode(
        self,
        path: Path,
        *,
        question: str,
        special_label: str,
        special_mode: str,
        remember_label: str,
        settings_attr: str,
    ) -> str:
        """Native open-mode chooser (special view vs plain text) + remember box.

        Uses wx.RichMessageDialog so it's a real native dialog with a checkbox —
        no hand-rolled wx.Dialog that can render over the startup wizard. Yes
        opens the special view, No opens plain text, and closing defaults to text.
        """
        wx = self._wx
        dialog = wx.RichMessageDialog(
            self.frame,
            question,
            f"Open {path.name}",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        dialog.SetYesNoLabels(special_label, "Open in normal text editor")
        dialog.ShowCheckBox(remember_label)
        apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
        result = self._show_modal_dialog(dialog, "Open Choice")
        remembered = bool(dialog.IsCheckBoxChecked())
        dialog.Destroy()
        mode = special_mode if result == wx.ID_YES else "text"
        if remembered:
            setattr(self.settings, settings_attr, mode)
            save_settings(self.settings)
        return mode

    def _prompt_csv_open_mode(self, path: Path) -> str:
        return self._prompt_open_mode(
            path,
            question=(
                f"{path.name} can open in the special CSV grid or in the normal text editor."
            ),
            special_label="Open in special CSV grid",
            special_mode="grid",
            remember_label="Remember this choice for CSV files",
            settings_attr="csv_open_mode",
        )

    def _prompt_word_open_mode(self, path: Path) -> str:
        return self._prompt_open_mode(
            path,
            question=(
                f"{path.name} can open in a structured Word view or in the normal text editor."
            ),
            special_label="Open in structured Word view",
            special_mode="structured",
            remember_label="Remember this choice for Word files",
            settings_attr="word_open_mode",
        )

    def _create_csv_document_tab(self, document: Document, select: bool = True) -> int:
        wx = self._wx
        surface = CsvGridSurface(wx, self.notebook, document, self._on_csv_surface_changed)
        panel = surface.panel
        self._bind_editor_events(surface)
        tab = _DocumentTab(panel=panel, editor=surface, document=document)
        self._document_tabs.append(tab)
        index = self.notebook.GetPageCount()
        self.notebook.AddPage(panel, document.name, select=select)
        if select:
            self._active_tab_index = index
            self.editor = surface
            self.document = document
            self._apply_statusbar_layout()
            self._refresh_title()
            self._refresh_read_only_state()
        self._refresh_sessions_menu()
        return index

    def _create_word_document_tab(self, document: Document, select: bool = True) -> int:
        wx = self._wx
        surface = WordDocumentSurface(wx, self.notebook, document, self._sync_editor_change)
        panel = surface.panel
        self._bind_editor_events(surface)
        tab = _DocumentTab(panel=panel, editor=surface, document=document)
        self._document_tabs.append(tab)
        index = self.notebook.GetPageCount()
        self.notebook.AddPage(panel, document.name, select=select)
        if select:
            self._active_tab_index = index
            self.editor = surface
            self.document = document
            self._apply_statusbar_layout()
            self._refresh_title()
            self._refresh_read_only_state()
        self._refresh_sessions_menu()
        return index

    def _create_rich_document_tab(self, document: Document, select: bool = True) -> int:
        """Create a tab backed by the native Rich text lens (rtf.md Part One).

        Mirrors :meth:`_create_word_document_tab`: a duck-typed surface stands in
        for ``self.editor``. The surface keeps QUILL markup canonical, so all
        existing editor commands keep working through it.
        """
        wx = self._wx
        surface = RichTextSurface(wx, self.notebook, document, self._sync_editor_change)
        panel = surface.panel
        self._bind_editor_events(surface)
        tab = _DocumentTab(panel=panel, editor=surface, document=document)
        self._document_tabs.append(tab)
        index = self.notebook.GetPageCount()
        self.notebook.AddPage(panel, document.name, select=select)
        if select:
            self._active_tab_index = index
            self.editor = surface
            self.document = document
            self._apply_statusbar_layout()
            self._refresh_title()
            self._refresh_read_only_state()
        self._refresh_sessions_menu()
        return index

    def _rich_editor_enabled(self) -> bool:
        """True when the writer has opted into the Rich text lens (off by default)."""
        return str(getattr(self.settings, "editor_surface", "plain")).lower() == "rich"

    def _announce_lens(self, lens: str) -> None:
        """Speak and show which editing lens is now active."""
        self._set_status(f"{lens}")

    def switch_editing_lens(self) -> None:
        """Flip the current document between the Rich text and Markdown lenses.

        On a rich surface this toggles the in-tab lens losslessly (the canonical
        markup is shared, so no word is lost and the document is not marked dirty).
        On a plain-text surface it reports how to enable the Rich text lens, since
        QUILL's offset-based commands stay exact on the plain surface.
        """
        editor = self.editor
        toggler = getattr(editor, "toggle_mode", None)
        if surface_kind(editor) == "rich" and callable(toggler):
            self._announce_lens(toggler())
            return
        if not self._rich_editor_enabled():
            self._set_status("Rich text lens is off. Turn it on in Settings, Editing.")
            return
        self._set_status("This document is open in the Markdown lens.")

    def _announce_rtf_safety(self, document: Document) -> None:
        """Announce the Rich text lens and any RTF safety findings on open."""
        metadata = document.source_metadata
        blocked = metadata.get("rtf_blocked")
        warnings = metadata.get("rtf_warnings")
        parts = ["Opened in Rich text lens."]
        if isinstance(blocked, list) and blocked:
            parts.append(
                "Removed unsafe content: " + ", ".join(str(item) for item in blocked) + "."
            )
        if isinstance(warnings, list) and warnings:
            parts.append(
                "Flagged for your consent: " + ", ".join(str(item) for item in warnings) + "."
            )
        self._set_status(" ".join(parts))

    def next_document(self) -> None:
        self._switch_document(reverse=False)

    def previous_document(self) -> None:
        self._switch_document(reverse=True)

    def close_current_document(self) -> None:
        if not self._prompt_to_save_active_document("Close"):
            self._set_status("Close cancelled")
            return
        closing_index = self._current_tab_index()
        self._close_tab(closing_index)
        self._set_status("Closed document")

    def _switch_document(self, reverse: bool) -> None:
        if len(self._document_tabs) < 2:
            self._announce("Only one document open")
            self._set_status("No other open document to switch to")
            return
        current_index = self._current_tab_index()
        step = -1 if reverse else 1
        target_index = (current_index + step) % len(self._document_tabs)
        self._select_tab(target_index)
        name = self.document.name
        self._announce(f"Switched to {name}")
        self._set_status(f"Switched to {name}")

    def speak_window_title(self) -> None:
        title = self.frame.GetTitle()
        self._announce(title)
        self._set_status(title)

    def speak_full_path(self) -> None:
        path = self.document.path
        if path is None:
            msg = f"{self.document.name} — not saved to disk"
        else:
            msg = str(path)
        self._announce(msg)
        self._set_status(msg)

    def speak_status_summary(self) -> None:
        name = self.document.name
        path = self.document.path
        modified = "modified" if self.document.modified else "saved"
        encoding = getattr(self.document, "encoding", None) or "UTF-8"
        parts = [name]
        if path:
            parts.append(str(path))
        parts.extend([modified, f"encoding {encoding}"])
        msg = ". ".join(parts)
        self._announce(msg)
        self._set_status(msg)

    # ------------------------------------------------------------------
    # Compare mode (#193/#194) — Boxer-style keyboard-first diff navigation
    # ------------------------------------------------------------------

    def compare_start_with_file(self, path: object = None) -> None:
        from quill.core.compare_service import CompareOptions, CompareService
        from quill.ui.compare_dialog import CompareDialog

        wx = self._wx
        right_path: Path | None = path if isinstance(path, Path) else None
        if right_path is None:
            with wx.FileDialog(
                self.frame,
                "Compare with file",
                wildcard="All files (*.*)|*.*",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dlg:
                if self._show_modal_dialog(dlg, "Compare with file") != wx.ID_OK:
                    return
                right_path = Path(dlg.GetPath())
        left_text = self.editor.GetValue()
        try:
            right_text = right_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._set_status(f"Cannot read {right_path.name}: {exc}")
            return
        svc = CompareService()
        opts = getattr(self, "_compare_options", CompareOptions())
        left_label = self.document.name or "Left"
        right_label = right_path.name
        groups = svc.compare(
            left_text,
            right_text,
            left_label=left_label,
            right_label=right_label,
            left_path=self.document.path,
            right_path=right_path,
            options=opts,
        )
        self._compare_service = svc
        self._compare_left_text = left_text
        self._compare_right_text = right_text
        if not groups:
            msg = "No differences found."
            if opts.ignore_all_whitespace or opts.ignore_trailing_whitespace:
                msg += " (whitespace ignored)"
            self._announce(msg)
            self._set_status(msg)
            return
        dlg = CompareDialog(self.frame, svc)
        self._show_modal_dialog(dlg, "Compare")
        dlg.Destroy()
        self._compare_service = None

    def compare_dialog_next(self) -> None:
        svc = getattr(self, "_compare_service", None)
        if svc is None:
            self._announce("Not in compare mode")
            return
        g = svc.next()
        if g is None:
            self._announce("No differences")
            return
        self._announce(g.summary_verbose)
        self._set_status(g.summary_short)

    def compare_dialog_previous(self) -> None:
        svc = getattr(self, "_compare_service", None)
        if svc is None:
            self._announce("Not in compare mode")
            return
        g = svc.previous()
        if g is None:
            self._announce("No differences")
            return
        self._announce(g.summary_verbose)
        self._set_status(g.summary_short)

    def compare_current_summary(self) -> None:
        svc = getattr(self, "_compare_service", None)
        if svc is None:
            self._announce("Not in compare mode")
            return
        g = svc.current()
        if g is None:
            self._announce("No current difference — press F8 to navigate")
            return
        self._announce(g.summary_verbose)
        self._set_status(g.summary_short)

    def compare_toggle_ignore_whitespace(self) -> None:
        from quill.core.compare_service import CompareOptions

        opts = getattr(self, "_compare_options", CompareOptions())
        if opts.ignore_all_whitespace:
            self._compare_options = CompareOptions(ignore_all_whitespace=False)
            msg = "Whitespace comparison: exact"
        elif opts.ignore_trailing_whitespace:
            self._compare_options = CompareOptions(ignore_all_whitespace=True)
            msg = "Whitespace comparison: ignore all"
        else:
            self._compare_options = CompareOptions(ignore_trailing_whitespace=True)
            msg = "Whitespace comparison: ignore trailing"
        self._announce(msg)
        self._set_status(msg)

    def compare_generate_report(self) -> None:
        svc = getattr(self, "_compare_service", None)
        if svc is None:
            self._set_status("No active comparison")
            return
        from quill.core.document import Document

        lines: list[str] = [
            f"# Compare Report: {svc.left_label} vs {svc.right_label}",
            f"{svc.group_count} difference(s) found.",
            "",
        ]
        for g in svc._groups:
            lines.append(g.summary_verbose)
            lines.append("")
        text = "\n".join(lines)
        doc = Document(name="Compare Report.md", text=text)
        self._create_document_tab(doc, select=True)
        self._set_status("Compare report opened in new tab")

    def send_to_tray(self) -> None:
        self._ensure_tray_icon()
        self.settings.tray_enabled = True
        self.frame.Hide()
        self._set_status("Sent Quill to system tray")

    def toggle_soft_wrap(self, enabled: bool | None = None) -> None:
        next_state = (not self.settings.soft_wrap) if enabled is None else enabled
        self.settings.soft_wrap = next_state
        self._apply_soft_wrap(next_state)
        self._set_status("Soft wrap on" if next_state else "Soft wrap off")

    def toggle_tab_control(self, enabled: bool | None = None) -> None:
        next_state = (not self._tab_control_visible) if enabled is None else enabled
        self.settings.show_tab_control = next_state
        save_settings(self.settings)
        self._rebuild_tab_host(next_state)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            item = menu_bar.FindItemById(self._id_toggle_tab_control)
            if item is not None:
                item.Check(next_state)
        self._set_status("Tab control shown" if next_state else "Tab control hidden")

    def toggle_find_wrap(self, enabled: bool | None = None) -> None:
        next_state = (not self.settings.wrap_find) if enabled is None else enabled
        self.settings.wrap_find = next_state
        save_settings(self.settings)
        self._set_status("Find wrap on" if next_state else "Find wrap off")

    def set_dirty_title_style(self, style: str) -> None:
        if style not in {"text", "asterisk", "asterisk_text"}:
            return
        self.settings.dirty_title_style = style
        save_settings(self.settings)
        self._refresh_title()
        label = {
            "text": "Dirty title style: text",
            "asterisk": "Dirty title style: asterisk",
            "asterisk_text": "Dirty title style: asterisk plus text",
        }[style]
        self._set_status(label)

    def toggle_dark_mode(self, enabled: bool | None = None) -> None:
        current = self.settings.theme == "dark"
        next_state = (not current) if enabled is None else enabled
        self.settings.theme = "dark" if next_state else "system"
        self._apply_theme(self.settings.theme)
        # Re-render an open side preview so the WebView matches the editor's
        # theme instead of staying light in dark mode (issue #83).
        tab = self._active_tab()
        if (
            tab is not None
            and getattr(tab, "preview", None) is not None
            and getattr(tab, "splitter", None) is not None
            and tab.splitter.IsSplit()
        ):
            self._update_side_preview(tab)
        self._set_status("Dark mode on" if next_state else "Dark mode off")

    def toggle_persistent_undo(self, enabled: bool | None = None) -> None:
        next_state = (not self.settings.persistent_undo) if enabled is None else enabled
        self.settings.persistent_undo = next_state
        if self.document.path is not None:
            self._load_persistent_undo_state(self.document.path, self.editor.GetValue())
        else:
            self._persistent_undo_history = [self.editor.GetValue()]
            self._persistent_undo_index = 0
        self._set_status("Persistent undo on" if next_state else "Persistent undo off")

    def toggle_spellcheck_as_you_type(self, enabled: bool | None = None) -> None:
        next_state = (not self.settings.spellcheck_as_you_type) if enabled is None else enabled
        self.settings.spellcheck_as_you_type = next_state
        self._set_status(
            "Spell check as you type on" if next_state else "Spell check as you type off"
        )

    def toggle_intellisense_as_you_type(self, enabled: bool | None = None) -> None:
        next_state = (
            not getattr(self.settings, "intellisense_as_you_type", False)
            if enabled is None
            else enabled
        )
        self.settings.intellisense_as_you_type = next_state
        if not next_state:
            self._hide_intellisense_popup()
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            item = menu_bar.FindItemById(self._id_toggle_intellisense_as_you_type)
            if item is not None:
                item.Check(next_state)
        self._set_status(
            "Word prediction as you type on" if next_state else "Word prediction as you type off"
        )

    def toggle_extend_selection_mode(self, enabled: bool | None = None) -> None:
        next_state = (not self._extend_selection_mode) if enabled is None else enabled
        self._extend_selection_mode = next_state
        if next_state:
            self._extend_selection_anchor = self.editor.GetInsertionPoint()
            text = self.editor.GetValue()
            anchor = self._extend_selection_anchor
            line, col = line_column_for_position(text, anchor)
            self._set_status(f"Extend selection mode on. Anchor at line {line}, column {col}.")
        else:
            self._extend_selection_anchor = None
            sel = self._last_selection
            if sel is not None:
                text = self.editor.GetValue()
                s_line, s_col = line_column_for_position(text, sel[0])
                e_line, e_col = line_column_for_position(text, sel[1])
                self._set_status(
                    f"Extend selection mode off. Last region: line {s_line} column {s_col}"
                    f" to line {e_line} column {e_col}."
                )
            else:
                self._set_status("Extend selection mode off.")

    def start_selection(self) -> None:
        self._selection_anchor = self.editor.GetInsertionPoint()
        text = self.editor.GetValue()
        line, col = line_column_for_position(text, self._selection_anchor)
        self._set_status(f"Selection started at line {line}, column {col}.")

    def complete_selection(self) -> None:
        if self._selection_anchor is None:
            self._set_status("No selection anchor. Press F8 to set one.")
            return
        caret = self.editor.GetInsertionPoint()
        start = min(self._selection_anchor, caret)
        end = max(self._selection_anchor, caret)
        self.editor.SetSelection(start, end)
        if start != end:
            self._last_selection = (start, end)
        self._selection_anchor = None
        text = self.editor.GetValue()
        s_line, s_col = line_column_for_position(text, start)
        e_line, e_col = line_column_for_position(text, end)
        char_count = end - start
        self._set_status(
            f"Selected {char_count} character{'s' if char_count != 1 else ''},"
            f" line {s_line} column {s_col} to line {e_line} column {e_col}."
        )

    def reselect(self) -> None:
        if self._last_selection is None:
            self._set_status("No previous selection to restore.")
            return
        start, end = self._last_selection
        text_len = len(self.editor.GetValue())
        start = min(start, text_len)
        end = min(end, text_len)
        if start == end:
            self._set_status("Previous selection is no longer valid.")
            return
        self.editor.SetSelection(start, end)
        text = self.editor.GetValue()
        s_line, s_col = line_column_for_position(text, start)
        e_line, e_col = line_column_for_position(text, end)
        char_count = end - start
        self._set_status(
            f"Reselected {char_count} character{'s' if char_count != 1 else ''},"
            f" line {s_line} column {s_col} to line {e_line} column {e_col}."
        )

    def go_to_start_of_selection(self) -> None:
        start, end = self.editor.GetSelection()
        if start == end:
            self._set_status("No selection.")
            return
        self.editor.SetInsertionPoint(start)
        text = self.editor.GetValue()
        line, col = line_column_for_position(text, start)
        self._set_status(f"Moved to start of selection: line {line}, column {col}.")

    def copy_all(self) -> None:
        text = self.editor.GetValue()
        if not text:
            self._set_status("Document is empty.")
            return
        if not self._copy_to_clipboard(text):
            self._set_status("Could not copy to clipboard.")
            return
        char_count = len(text)
        self._set_status(
            f"All text copied ({char_count} character{'s' if char_count != 1 else ''})."
        )

    def unselect_all(self) -> None:
        caret = self.editor.GetInsertionPoint()
        self.editor.SetSelection(caret, caret)
        self._set_status("Selection cleared.")

    def say_selected(self) -> None:
        start, end = self.editor.GetSelection()
        if start == end:
            self._set_status("Nothing selected.")
            return
        text = self.editor.GetRange(start, end)
        preview = text[:60].replace("\n", " ")
        self._set_status_quiet("Say selected: " + preview + ("..." if len(text) > 60 else ""))
        announce(text)

    def read_all(self) -> None:
        if self._safe_mode:
            return
        if self._read_aloud.state in ("playing", "paused"):
            self._read_aloud.stop()
        self.editor.SetInsertionPoint(0)
        self.toggle_read_aloud()

    def toggle_overwrite_mode(self, enabled: bool | None = None) -> None:
        next_state = (not self._overwrite_mode) if enabled is None else enabled
        self._overwrite_mode = next_state
        self._refresh_statusbar()
        self._set_status("Overwrite mode on" if next_state else "Insert mode on")

    def choose_document_encoding(self) -> None:
        wx = self._wx
        choices = ["utf-8", "utf-16", "cp1252", "latin-1"]
        current_index = (
            choices.index(self.document.encoding) if self.document.encoding in choices else 0
        )
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose document encoding:",
            "Encoding",
            choices,
        ) as dialog:
            dialog.SetSelection(current_index)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Encoding") != wx.ID_OK:
                self._set_status("Encoding selection cancelled")
                return
            selected = dialog.GetSelection()
        if selected < 0 or selected >= len(choices):
            return
        self.document.encoding = choices[selected]
        self._refresh_statusbar()
        self._set_status(f"Encoding set to {choices[selected]}")

    def toggle_line_endings(self) -> None:
        self.document.line_ending = "\n" if self.document.line_ending == "\r\n" else "\r\n"
        self._refresh_statusbar()
        self._set_status(
            "Line endings set to LF"
            if self.document.line_ending == "\n"
            else "Line endings set to CRLF"
        )

    def cycle_autosave_interval(self) -> None:
        choices = [
            timedelta(seconds=15),
            timedelta(seconds=30),
            timedelta(seconds=60),
            timedelta(minutes=5),
            timedelta(0),
        ]
        try:
            index = choices.index(self._autosave_interval)
        except ValueError:
            index = 1
        next_interval = choices[(index + 1) % len(choices)]
        self._autosave_interval = next_interval
        self._refresh_statusbar()
        if next_interval.total_seconds() == 0:
            self._set_status("Autosave off")
            return
        seconds = int(next_interval.total_seconds())
        if seconds >= 60 and seconds % 60 == 0:
            self._set_status(f"Autosave every {seconds // 60} min")
            return
        self._set_status(f"Autosave every {seconds} s")

    def open_containing_folder(self) -> None:
        if self.document.path is None:
            self.save_file_as()
            return
        os.startfile(str(self.document.path.parent))
        self._set_status(f"Opened folder for {self.document.name}")

    def undo(self) -> None:
        if self.settings.persistent_undo:
            self._step_persistent_undo(-1)
            return
        if hasattr(self.editor, "CanUndo") and self.editor.CanUndo():
            self.editor.Undo()
            self._set_status("Undo")
            return
        self._set_status("Nothing to undo")

    def redo(self) -> None:
        if self.settings.persistent_undo:
            self._step_persistent_undo(1)
            return
        if hasattr(self.editor, "CanRedo") and self.editor.CanRedo():
            self.editor.Redo()
            self._set_status("Redo")
            return
        self._set_status("Nothing to redo")

    def _apply_soft_wrap(self, enabled: bool) -> None:
        wx = self._wx
        style = self.editor.GetWindowStyleFlag()
        if enabled:
            style = style & ~wx.TE_DONTWRAP
        else:
            style = style | wx.TE_DONTWRAP
        self.editor.SetWindowStyleFlag(style)

    def _load_persistent_undo_state(self, path: Path, text: str) -> None:
        history = load_undo_history(path)
        if not history:
            history = [text]
        elif history[-1] != text:
            history.append(text)
        self._persistent_undo_history = history[-100:]
        self._persistent_undo_index = len(self._persistent_undo_history) - 1
        if self.settings.persistent_undo:
            save_undo_history(path, self._persistent_undo_history)

    def _record_persistent_undo_state(self, text: str) -> None:
        if not self.settings.persistent_undo or self.document.path is None:
            return
        if (
            self._persistent_undo_history
            and self._persistent_undo_history[self._persistent_undo_index] == text
        ):
            return
        if self._persistent_undo_index < len(self._persistent_undo_history) - 1:
            self._persistent_undo_history = self._persistent_undo_history[
                : self._persistent_undo_index + 1
            ]
        self._persistent_undo_history.append(text)
        self._persistent_undo_history = self._persistent_undo_history[-100:]
        self._persistent_undo_index = len(self._persistent_undo_history) - 1
        # Persisting the full history JSON on every keystroke is wasteful (and
        # can write many MB per second on large documents). Throttle disk
        # writes; flush_persistent_undo() forces a write on save/close.
        self._persistent_undo_dirty = True
        self._maybe_flush_persistent_undo()

    def _maybe_flush_persistent_undo(self, force: bool = False) -> None:
        if not getattr(self, "_persistent_undo_dirty", False):
            return
        if self.document.path is None:
            return
        now = datetime.now(UTC)
        last = getattr(self, "_last_persistent_undo_write_at", None)
        interval = timedelta(seconds=3)
        if not force and last is not None and now - last < interval:
            return
        save_undo_history(self.document.path, self._persistent_undo_history)
        self._last_persistent_undo_write_at = now
        self._persistent_undo_dirty = False

    def flush_persistent_undo(self) -> None:
        self._maybe_flush_persistent_undo(force=True)

    def _step_persistent_undo(self, direction: int) -> None:
        if not self._persistent_undo_history:
            self._set_status("Nothing to undo")
            return
        target = self._persistent_undo_index + direction
        if target < 0 or target >= len(self._persistent_undo_history):
            self._set_status("Nothing to redo" if direction > 0 else "Nothing to undo")
            return
        text = self._persistent_undo_history[target]
        self._persistent_undo_index = target
        self._suspend_persistent_undo = True
        try:
            self.editor.ChangeValue(text)
        finally:
            self._suspend_persistent_undo = False
        self.document.set_text(text)
        self._refresh_title()
        self._set_status("Redo" if direction > 0 else "Undo")

    def _restore_from_tray(self) -> None:
        self.frame.Show(True)
        self.frame.Iconize(False)
        self.frame.Raise()
        self.frame.RequestUserAttention()
        self._set_status("Restored from system tray")

    def _on_tray_right_click(self, _event: object) -> None:
        wx = self._wx
        if self._tray_icon is None:
            return
        menu = wx.Menu()
        show_id = wx.NewIdRef()
        sticky_id = wx.NewIdRef()
        new_sticky_id = wx.NewIdRef()
        exit_id = wx.NewIdRef()
        menu.Append(show_id, "Show Quill")
        menu.AppendSeparator()
        # Copy Tray submenu — list occupied slots for quick paste
        ct_sub = wx.Menu()
        tray = self._tray()
        has_any = False
        for n, slot in tray.all_slots():
            if not slot.is_empty():
                has_any = True
                label_part = f" ({slot.label})" if slot.label else ""
                item_label = f"&{n}.{label_part} {slot.preview(50)}"
                slot_id = wx.NewIdRef()
                ct_sub.Append(slot_id, item_label)
                menu.Bind(
                    wx.EVT_MENU,
                    lambda _e, _n=n: self._tray_paste_slot(_n),
                    id=slot_id,
                )
        if not has_any:
            empty_id = wx.NewIdRef()
            ct_sub.Append(empty_id, "(all slots empty)")
            ct_sub.Enable(empty_id, False)
        ct_sub.AppendSeparator()
        open_tray_id = wx.NewIdRef()
        ct_sub.Append(open_tray_id, "Open Copy Tray...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_copy_tray(), id=open_tray_id)
        menu.AppendSubMenu(ct_sub, "Copy &Tray")
        menu.AppendSeparator()
        menu.Append(sticky_id, "Sticky Notes...")
        menu.Append(new_sticky_id, "New Sticky Note...")
        menu.AppendSeparator()
        menu.Append(exit_id, "Exit Quill")
        menu.Bind(wx.EVT_MENU, lambda _e: self._restore_from_tray(), id=show_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.manage_sticky_notes(), id=sticky_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.create_sticky_note(), id=new_sticky_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._exit_from_tray(), id=exit_id)
        self._tray_icon.PopupMenu(menu)
        menu.Destroy()

    def _tray_paste_slot(self, n: int) -> None:
        """Restore the window (if hidden) then paste from Copy Tray slot *n*."""
        self._restore_from_tray()
        self.paste_from_tray_slot(n)

    def _exit_from_tray(self) -> None:
        self._is_exiting = True
        self.frame.Close()

    def _ensure_tray_icon(self) -> None:
        wx = self._wx
        if self._tray_icon is not None:
            return
        taskbar_icon = wx.adv.TaskBarIcon()
        icon = wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
        taskbar_icon.SetIcon(icon, "Quill")
        taskbar_icon.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, lambda _e: self._restore_from_tray())
        taskbar_icon.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self._on_tray_right_click)
        self._tray_icon = taskbar_icon

    def _remove_tray_icon(self) -> None:
        if self._tray_icon is None:
            return
        self._tray_icon.RemoveIcon()
        self._tray_icon.Destroy()
        self._tray_icon = None

    def _write_document_to_disk(self, document: object, target: Path | None = None) -> None:
        """Write a document, converting to the format of the target extension.

        The editor surface stores QUILL Markdown-style markup; Save As routes that
        markup through :func:`write_document_as`, which re-serializes it to RTF,
        HTML, or stripped plain text for those extensions and writes it verbatim
        (as Markdown) otherwise. The plain-text link style follows the setting so
        URLs survive when the writer wants them to.
        """
        link_style = str(
            getattr(getattr(self, "settings", None), "plain_text_link_style", "text_url")
        )
        write_document_as(document, target, plain_text_link_style=link_style)  # type: ignore[arg-type]

    def save_file(self) -> None:
        if self._active_tab().read_only_remote:
            self.save_copy_remote()
            return
        if self.document.path is None:
            self.save_file_as()
            return
        if self.document.modified:
            backup_document(self.document)
        self._write_document_to_disk(self.document)
        # FEAT-19: prime the watcher so our own save is not reported as an external change.
        if self._external_change_watcher is not None and self.document.path is not None:
            self._external_change_watcher.prime(FileSnapshot.of(self.document.path))
        self._record_persistent_undo_state(self.document.text)
        self.flush_persistent_undo()
        self._refresh_title()
        self._set_status(f"Saved {self.document.name}")
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        post_sound(SoundEvent.DOCUMENT_SAVED)
        # If this file was opened over SSH, upload it back to the remote host
        # with a tilde backup in its original newline style (#139).
        self.maybe_upload_remote_on_save()

    def save_all_files(self) -> None:
        for index in range(len(self._document_tabs)):
            self._select_tab(index)
            if self.document.modified:
                self.save_file()
                if self.document.modified:
                    self._set_status("Save all cancelled")
                    return
        self._set_status("Saved all documents")

    def reload_from_disk(self) -> None:
        if self.document.path is None:
            self._set_status("No file to reload")
            return
        if self.document.modified and not self._confirm_discard_changes():
            self._set_status("Reload cancelled")
            return
        self.open_file(self.document.path, record_recent=False, refresh_existing=True)
        self._set_status(f"Reloaded {self.document.name}")

    def restore_backup(self) -> None:
        wx = self._wx
        if self.document.path is None:
            self._set_status("Open a file before restoring a backup")
            return
        backups = list_backups(self.document.path)
        if not backups:
            self._set_status("No backups available")
            return
        choices = [backup.name for backup in backups]
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose a backup to restore:",
            "Restore Backup",
            choices=choices,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Restore Backup") != wx.ID_OK:
                return
            selection = dialog.GetSelection()
        backup_path = backups[selection]
        restored_text = backup_path.read_text(encoding=self.document.encoding)
        self.document.set_text(restored_text)
        self._replace_document_text(restored_text)
        self._refresh_title()
        self._set_status(f"Restored backup {backup_path.name}")

    def _build_text_printout(self, title: str, text: str) -> object:
        wx = self._wx

        class _TextPrintout(wx.Printout):
            def __init__(self, print_title: str, print_text: str) -> None:
                super().__init__(print_title)
                self._text = print_text

            def OnPrintPage(self, _page: int) -> bool:
                dc = self.GetDC()
                if dc is None:
                    return False
                dc.SetFont(
                    wx.Font(
                        10,
                        wx.FONTFAMILY_TELETYPE,
                        wx.FONTSTYLE_NORMAL,
                        wx.FONTWEIGHT_NORMAL,
                    )
                )
                width, height = dc.GetSize()
                margin = 50
                y = margin
                line_height = dc.GetTextExtent("A")[1] + 2
                for line in self._text.splitlines() or [""]:
                    dc.DrawText(line, margin, y)
                    y += line_height
                    if y > height - margin:
                        break
                return True

            def HasPage(self, page: int) -> bool:
                return page == 1

            def GetPageInfo(self) -> tuple[int, int, int, int]:
                return (1, 1, 1, 1)

        return _TextPrintout(title, text)

    def page_setup(self) -> None:
        wx = self._wx
        dialog = wx.PageSetupDialog(self.frame, self._page_setup_data)
        try:
            if self._show_modal_dialog(dialog, "Page Setup") != wx.ID_OK:
                self._set_status("Page setup cancelled")
                return
            self._page_setup_data = dialog.GetPageSetupData()
            self._print_data = self._page_setup_data.GetPrintData()
            self._set_status("Page setup updated")
        finally:
            dialog.Destroy()

    def print_document(self) -> None:
        wx = self._wx
        text = self.editor.GetValue()
        printout = self._build_text_printout(self.document.name, text)
        printer = wx.Printer(wx.PrintDialogData(self._print_data))
        try:
            success = bool(printer.Print(self.frame, printout, True))
        except Exception as error:
            printout.Destroy()
            self._show_message_box(f"Printing failed: {error}", "Print", wx.ICON_ERROR | wx.OK)
            return
        if not success:
            read_last_error = getattr(printer, "GetLastError", None)
            last_error = read_last_error() if callable(read_last_error) else None
            cancelled_code = getattr(wx, "PRINTER_CANCELLED", None)
            no_error_code = getattr(wx, "PRINTER_NO_ERROR", None)
            if last_error == cancelled_code or last_error in {None, no_error_code}:
                self._set_status("Printing cancelled")
                printout.Destroy()
                return
            self._show_message_box("Printing failed.", "Print", wx.ICON_ERROR | wx.OK)
            printout.Destroy()
            return
        self._print_data = printer.GetPrintDialogData().GetPrintData()
        printout.Destroy()
        self._set_status("Printed document")

    # Save As wildcard filter index -> the extension that filter implies.
    _SAVE_FILTER_EXTENSIONS = {0: ".txt", 1: ".md", 2: ".html", 3: ".rtf"}

    def _resolve_save_target(self, target: Path, filter_index: int) -> Path:
        """Give ``target`` an extension from the chosen type filter when none typed.

        A typed extension always wins (so ``notes.txt`` stays plain text even if the
        HTML filter was highlighted, and no ``notes.txt.html`` double extension is
        created). Only when the user typed no extension do we fall back to the
        selected filter, defaulting to Markdown for the "All files" choice.
        """
        if target.suffix:
            return target
        extension = self._SAVE_FILTER_EXTENSIONS.get(filter_index, ".md")
        return target.with_suffix(extension)

    def save_file_as(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Save file as",
            defaultDir=self._file_dialog_default_dir(),
            wildcard=(
                "Text files (*.txt)|*.txt|Markdown files (*.md)|*.md|"
                "HTML files (*.html;*.htm;*.xhtml)|*.html;*.htm;*.xhtml|"
                "Rich Text Format (*.rtf)|*.rtf|All files (*.*)|*.*"
            ),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self.document.path is None:
                default_format = getattr(self.settings, "default_new_document_format", "markdown")
                filter_index = {"text": 0, "markdown": 1, "html": 2}.get(default_format, 1)
                set_filter_index = getattr(dialog, "SetFilterIndex", None)
                if callable(set_filter_index):
                    set_filter_index(filter_index)
            if self._show_modal_dialog(dialog, "Save file as") != wx.ID_OK:
                return
            get_filter_index = getattr(dialog, "GetFilterIndex", None)
            chosen_filter = get_filter_index() if callable(get_filter_index) else -1
            target = self._resolve_save_target(Path(dialog.GetPath()), chosen_filter)
            self._last_file_dir = str(target.parent)

        self.document.set_text(self.editor.GetValue())
        if self.document.modified and self.document.path is not None:
            backup_document(self.document)
        self._write_document_to_disk(self.document, target)
        # FEAT-19: restart the watcher on the new path so our save is the baseline.
        self._stop_external_change_watcher()
        self._start_external_change_watcher()
        self._load_persistent_undo_state(target, self.document.text)
        self._record_recent(target)
        self._refresh_title()
        self._set_status(f"Saved as {target.name} ({format_label_for_path(target)})")
        self._maybe_reload_surface_after_save_as(target)

    def _surface_kind_for_path(self, path: Path) -> str:
        """The editing surface ``open_file`` would use for ``path``.

        Mirrors the open dispatch: an ``.rtf`` opens in the Rich text lens when
        that lens is enabled, and everything else opens on the plain surface.
        """
        if path.suffix.lower() == ".rtf" and self._rich_editor_enabled():
            return RICH
        return PLAIN

    @staticmethod
    def _resolve_surface_sync(current_kind: str, desired_kind: str, mode: str) -> str:
        """Decide the post-Save-As surface action: ``none``, ``prompt`` or ``reload``."""
        if current_kind == desired_kind:
            return "none"
        if mode == "never":
            return "none"
        if mode == "always":
            return "reload"
        return "prompt"

    def _maybe_reload_surface_after_save_as(self, target: Path) -> None:
        """Offer to reload ``target`` so the surface matches its new format.

        Governed by the ``save_as_surface_sync`` setting (ask / always / never).
        Structured surfaces (CSV grid, Word) are never disturbed, and nothing
        happens unless the format's natural surface differs from the current one.
        """
        editor = self.editor
        if isinstance(editor, (CsvGridSurface, WordDocumentSurface)):
            return
        current = surface_kind(editor)
        if current not in (PLAIN, RICH):
            return
        desired = self._surface_kind_for_path(target)
        mode = str(getattr(self.settings, "save_as_surface_sync", "prompt")).strip().lower()
        action = self._resolve_surface_sync(current, desired, mode)
        if action == "none":
            return
        if action == "prompt":
            wx = self._wx
            view_label = "Rich text" if desired == RICH else "plain text"
            response = self._show_message_box(
                f"This file is now {format_label_for_path(target)}. Reload it in the "
                f"{view_label} editor so the view matches the format? Reloading replaces "
                f"the editor contents with the saved file.",
                "Reload in matching view?",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            if response != wx.YES:
                return
        self._reload_in_place(target)

    def _reload_in_place(self, target: Path) -> None:
        """Replace the current tab with ``target`` reopened in its natural surface.

        The file is read *before* the current tab is disturbed, so a read failure
        leaves the live document intact. On success the current page is removed
        without spawning a placeholder tab and the freshly typed surface is built
        by the shared open-finish path.
        """
        suffix = target.suffix.lower()
        try:
            result = read_open_document(target, suffix)
        except Exception:
            self._set_status("Could not reload in the matching view.")
            return
        index = self._current_tab_index()
        if index < 0:
            index = self._active_tab_index
        if 0 <= index < len(self._document_tabs):
            self.notebook.DeletePage(index)
            del self._document_tabs[index]
        self._finish_open_document(
            result,
            selected_path=target,
            suffix=suffix,
            existing_index=-1,
            record_recent=False,
            line=None,
            column=None,
        )

    def save_as_plain_text(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Save as plain text",
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save as plain text") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())

        plain_doc = Document(
            text=self.editor.GetValue(),
            path=target,
            modified=True,
            encoding="utf-8",
            line_ending="\n",
        )
        link_style = str(getattr(self.settings, "plain_text_link_style", "text_url"))
        write_plain_text_document(plain_doc, target, link_style=link_style)
        self._record_recent(target)
        self._set_status(f"Saved plain text to {target.name}")

    def clear_recent_files(self) -> None:
        clear_recent_files()
        self.recent_files = []
        self._refresh_recent_menu()
        self._set_status("Cleared recent files")

    def open_url(self) -> None:
        wx = self._wx
        from quill.io.http_transport import download_url
        from quill.io.open_read import read_open_document

        with wx.TextEntryDialog(
            self.frame,
            "Enter URL (http or https):",
            "Open from URL",
            value="https://",
        ) as dialog:
            if self._show_modal_dialog(dialog, "Open from URL") != wx.ID_OK:
                return
            raw_url = dialog.GetValue().strip()
        if not raw_url:
            self._set_status("Open from URL cancelled")
            return

        from urllib.error import HTTPError, URLError
        from urllib.parse import urlparse

        parsed = urlparse(raw_url)
        if parsed.scheme not in {"http", "https"}:
            self._show_message_box(
                "Only http and https URLs are supported.",
                "Open from URL",
                wx.ICON_ERROR | wx.OK,
            )
            return

        try:
            download = download_url(raw_url)
        except HTTPError as exc:  # pragma: no cover - exercised through error path
            self._show_message_box(
                f"Could not open URL: HTTP {exc.code} from {parsed.netloc or raw_url}.",
                "Open from URL",
                wx.ICON_ERROR | wx.OK,
            )
            return
        except URLError as exc:
            self._show_message_box(
                f"Could not open URL: {exc.reason}",
                "Open from URL",
                wx.ICON_ERROR | wx.OK,
            )
            return

        from pathlib import Path

        from quill.io.detect import STRUCTURED_EXTENSIONS, TEXT_EXTENSIONS

        suffix = Path(download.filename).suffix.lower()
        selected_path = Path(download.local_path)
        try:
            if suffix in STRUCTURED_EXTENSIONS or suffix in {".odt", ".rtf", ".pages"}:
                # Heavy formats use the office-stream path. Run on a worker so
                # the UI thread does not block on PDF/DOCX parses.
                from quill.io.open_read import OFFICE_STREAM_SUFFIXES

                if suffix in OFFICE_STREAM_SUFFIXES:
                    word_mode = (
                        self._resolve_word_open_mode(selected_path)
                        if suffix in {".doc", ".docx"}
                        else None
                    )

                    def _worker(_progress: object) -> tuple[object, object]:
                        return read_open_document(selected_path, suffix, word_mode=word_mode)

                    self._run_background_task(
                        f"Opening {download.filename}",
                        _worker,
                        lambda result: self._install_remote_document(result, suffix, download),
                    )
                    return
                loaded, epub_book = read_open_document(selected_path, suffix)
            elif suffix in TEXT_EXTENSIONS:
                loaded, epub_book = read_open_document(selected_path, suffix)
            else:
                # Unknown extension — treat as text via the new format pipeline.
                loaded, epub_book = read_open_document(selected_path, suffix or ".txt")
        except Exception as exc:  # noqa: BLE001 - format dispatch can fail
            self._show_message_box(
                f"Could not parse downloaded file: {exc}",
                "Open from URL",
                wx.ICON_ERROR | wx.OK,
            )
            return

        self._install_remote_document((loaded, epub_book), suffix, download)

    def _install_remote_document(
        self,
        result: object,
        suffix: str,
        download: object,
    ) -> None:
        """Open a downloaded URL document and tag the tab as a remote view."""

        assert isinstance(result, tuple)
        loaded, epub_book = result
        self._epub_book = epub_book if suffix == ".epub" else None
        self._create_document_tab(loaded, select=True)
        # Tag the tab as remote-sourced; saves go to "Save Copy to Local File..."
        # rather than the original URL.
        try:
            current_tab = self._document_tabs[-1]
            current_tab.source_label = f"from {getattr(download, 'final_url', '')}"
            current_tab.read_only_remote = True
        except (IndexError, AttributeError):
            pass
        self._location_ring = LocationRing()
        self._location_ring.record(0)
        self._refresh_title()
        size_text = format_content_length(getattr(download, "size", 0))
        self._set_status(
            f"Opened {getattr(download, 'filename', 'remote document')} "
            f"({size_text}) from {getattr(download, 'final_url', '')}"
        )

    # --- Remote Sites (issues #154, #155, #156, #157) -----------------------

    def open_from_remote(self) -> None:
        from quill.ui.remote_sites_dialog import DialogMode, RemoteSitesDialog

        with RemoteSitesDialog(
            self.frame, mode=DialogMode.OPEN, title="Open from Remote"
        ) as dialog:
            if self._show_modal_dialog(dialog, "Open from Remote") != self._wx.ID_OK:
                self._set_status("Open from Remote cancelled")
                return
            result = dialog.result
        if result is None:
            return
        self._download_remote_into_new_tab(result.site, result.path)

    def save_to_remote(self) -> None:
        from quill.ui.remote_sites_dialog import DialogMode, RemoteSitesDialog

        if self._active_tab().read_only_remote:
            # The active tab was opened from a URL; nothing to write back.
            self._show_message_box(
                "This document was opened from a URL and cannot be saved back to it. "
                "Use Save Copy to Remote... to write a local copy to a remote site.",
                "Save to Remote",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        with RemoteSitesDialog(self.frame, mode=DialogMode.SAVE, title="Save to Remote") as dialog:
            if self._show_modal_dialog(dialog, "Save to Remote") != self._wx.ID_OK:
                self._set_status("Save to Remote cancelled")
                return
            result = dialog.result
        if result is None:
            return
        self._upload_active_document(result.site, result.path)

    def save_copy_to_remote(self) -> None:
        from quill.ui.remote_sites_dialog import DialogMode, RemoteSitesDialog

        with RemoteSitesDialog(
            self.frame, mode=DialogMode.SAVE, title="Save Copy to Remote"
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save Copy to Remote") != self._wx.ID_OK:
                self._set_status("Save Copy to Remote cancelled")
                return
            result = dialog.result
        if result is None:
            return
        self._upload_active_document(result.site, result.path)

    def save_copy_remote(self) -> None:
        """Local-folder analogue of Save Copy to Remote; used by remote tabs."""

        self.save_copy_to_remote()

    def manage_remote_sites(self) -> None:
        from quill.ui.remote_sites_dialog import DialogMode, RemoteSitesDialog

        with RemoteSitesDialog(
            self.frame,
            mode=DialogMode.OPEN,
            title="Manage Remote Sites",
        ) as dialog:
            self._show_modal_dialog(dialog, "Manage Remote Sites")

    def _download_remote_into_new_tab(self, site, remote_path: str) -> None:
        from pathlib import Path

        from quill.io.open_read import read_open_document

        self._set_status(f"Downloading {remote_path} from {site.name}...")
        local_path = self._alloc_remote_temp_path(remote_path)
        try:
            self._run_remote_download(site, remote_path, local_path)
        except Exception as exc:  # noqa: BLE001 - transport errors are surfaced
            self._show_message_box(
                f"Could not download from {site.name}: {exc}",
                "Open from Remote",
                self._wx.ICON_ERROR | self._wx.OK,
            )
            return
        suffix = Path(remote_path).suffix.lower() or Path(local_path).suffix.lower()
        self._create_document_tab(
            Document(text="", path=Path(local_path), modified=False), select=True
        )
        existing_index = len(self._document_tabs) - 1
        from quill.io.open_read import OFFICE_STREAM_SUFFIXES

        if suffix in OFFICE_STREAM_SUFFIXES:
            self._run_background_task(
                f"Opening {Path(remote_path).name}",
                lambda _p: read_open_document(Path(local_path), suffix),
                lambda result: self._finish_remote_download(
                    result, suffix, site, remote_path, existing_index
                ),
            )
            return
        result = read_open_document(Path(local_path), suffix)
        self._finish_remote_download(result, suffix, site, remote_path, existing_index)

    def _finish_remote_download(
        self,
        result: object,
        suffix: str,
        site,
        remote_path: str,
        existing_index: int,
    ) -> None:
        assert isinstance(result, tuple)
        loaded, epub_book = result
        if 0 <= existing_index < len(self._document_tabs):
            tab = self._document_tabs[existing_index]
            tab.document = loaded
            tab.editor.ChangeValue(loaded.text)
            tab.source_label = f"from {site.name}:{remote_path}"
            tab.read_only_remote = False
        self._epub_book = epub_book if suffix == ".epub" else None
        self._select_tab(existing_index)
        self._refresh_title()
        self._set_status(f"Downloaded {remote_path} from {site.name}")

    def _upload_active_document(self, site, remote_path: str) -> None:
        from pathlib import Path

        from quill.core.remote_sites import load_password

        local_path = self._alloc_remote_temp_path(remote_path)
        Path(local_path).write_text(self.editor.GetValue(), encoding="utf-8")
        password = load_password(site.id)
        try:
            self._run_remote_upload(site, local_path, remote_path, password)
        except Exception as exc:  # noqa: BLE001
            self._show_message_box(
                f"Could not save to {site.name}: {exc}",
                "Save to Remote",
                self._wx.ICON_ERROR | self._wx.OK,
            )
            return
        self._set_status(f"Saved {remote_path} to {site.name}")

    def _alloc_remote_temp_path(self, remote_path: str) -> str:
        import os
        import tempfile

        base = os.path.basename(remote_path.rstrip("/")) or "remote"
        suffix = os.path.splitext(base)[1]
        fd, path = tempfile.mkstemp(prefix="quill-remote-", suffix=suffix)
        os.close(fd)
        return path

    def _run_remote_download(self, site, remote_path: str, local_path: str) -> None:
        """Synchronous download on the calling thread.

        The dialog UI is modal and short-lived; threading is intentionally
        minimal. The transport still raises :class:`RemoteTransportError` on
        failure so the caller can present a single error message.
        """

        from quill.core.remote_sites import load_password
        from quill.io.ftp_transport import FtpTransport
        from quill.io.remote_transport import RemoteTransport
        from quill.io.s3_transport import S3Transport
        from quill.io.sftp_transport import SftpTransport
        from quill.io.webdav_transport import WebDavTransport

        password = load_password(site.id)
        protocol = site.protocol
        transport: RemoteTransport
        if protocol == "ftp":
            transport = FtpTransport(site, password=password)
        elif protocol == "sftp":
            transport = SftpTransport(site, password=password)
        elif protocol == "webdav":
            transport = WebDavTransport(site, password=password)
        elif protocol == "s3":
            transport = S3Transport(site, password=password)
        else:
            raise RuntimeError(f"Unsupported protocol: {protocol}")
        try:
            transport.download(remote_path, local_path)
        finally:
            transport.close()

    def _run_remote_upload(self, site, local_path: str, remote_path: str, password: str) -> None:
        from quill.io.ftp_transport import FtpTransport
        from quill.io.remote_transport import RemoteTransport
        from quill.io.s3_transport import S3Transport
        from quill.io.sftp_transport import SftpTransport
        from quill.io.webdav_transport import WebDavTransport

        protocol = site.protocol
        transport: RemoteTransport
        if protocol == "ftp":
            transport = FtpTransport(site, password=password)
        elif protocol == "sftp":
            transport = SftpTransport(site, password=password)
        elif protocol == "webdav":
            transport = WebDavTransport(site, password=password)
        elif protocol == "s3":
            transport = S3Transport(site, password=password)
        else:
            raise RuntimeError(f"Unsupported protocol: {protocol}")
        try:
            transport.upload(local_path, remote_path)
        finally:
            transport.close()

    def _record_recent(self, path: Path) -> None:
        self.recent_files = add_recent_file(path, self.settings.recent_files_limit)
        self._refresh_recent_menu()

    def _maybe_autosave(self) -> None:
        if self._autosave_interval.total_seconds() <= 0:
            return
        now = datetime.now(UTC)
        if (
            self._last_autosave_at is not None
            and now - self._last_autosave_at < self._autosave_interval
        ):
            return
        # Skip snapshots when nothing has changed since the last one. This
        # avoids spinning up identical 10 MB autosave files for a document
        # that the user is just navigating through.
        revision = getattr(self.document, "revision", 0)
        last_revision = getattr(self, "_last_autosave_revision", None)
        if last_revision == revision:
            self._last_autosave_at = now
            return
        autosave_document(self.document, self.session_id)
        self._last_autosave_at = now
        self._last_autosave_revision = revision
        # §8.4 "Resume from where I left off": persist cursor position alongside
        # every autosave so the next session can restore it.
        try:
            from quill.core.recovery import save_cursor_position

            if self.editor is not None:
                save_cursor_position(self.session_id, self.editor.GetInsertionPoint())
        except Exception:  # noqa: BLE001
            pass

    def open_palette(self) -> None:
        """Open Command Palette (single press) or re-run last command (double press)."""
        if not hasattr(self, "_palette_dispatcher"):
            window_ms = int(getattr(getattr(self, "settings", None), "multi_press_window_ms", 400))
            self._palette_dispatcher = MultiPressDispatcher(window_ms=window_ms)
            self._palette_timer: object = None
            self._last_palette_command_id: str | None = None
        dispatcher = self._palette_dispatcher
        count, needs_timer = dispatcher.press("palette")
        existing = self._palette_timer
        if existing is not None:
            stop = getattr(existing, "Stop", None)
            if callable(stop):
                stop()
        if needs_timer:
            self._palette_timer = self._wx.CallLater(
                dispatcher.window_ms,
                self._fire_palette_action,
            )
        else:
            self._palette_timer = None
            self._fire_palette_action_with_count(count)

    def _fire_palette_action(self) -> None:
        count = self._palette_dispatcher.timeout("palette")
        self._palette_timer = None
        self._fire_palette_action_with_count(count)

    def _fire_palette_action_with_count(self, count: int) -> None:
        if count >= 2:
            self._run_last_palette_command()
        else:
            self._open_palette_dialog()

    def _open_palette_dialog(self) -> None:
        dialog = CommandPaletteDialog(
            self.frame, self.commands, self.features, announce_fn=self._announce
        )
        dialog.show_modal_and_run()
        command_id = dialog.last_run_command_id()
        if command_id:
            self._last_palette_command_id = command_id

    def _run_last_palette_command(self) -> None:
        command_id = getattr(self, "_last_palette_command_id", None)
        if command_id is None:
            self._announce("No recent palette command to repeat")
            return
        try:
            self.commands.run(command_id)
            self._announce("Repeated last palette command")
        except Exception:  # noqa: BLE001
            self._announce("Could not repeat last palette command")

    def create_sticky_note(self) -> None:
        if self._safe_mode:
            self._set_status("Sticky notes are unavailable in safe mode")
            return
        editor = StickyNoteEditorDialog(self.frame)
        body = editor.show_modal_and_get_body()
        if body is None:
            self._set_status("Sticky note cancelled")
            return
        note = save_sticky_note(body)
        self._set_status(f"Saved sticky note: {note.title}")

    def manage_sticky_notes(self) -> None:
        if self._safe_mode:
            self._set_status("Sticky notes are unavailable in safe mode")
            return
        StickyNotesVaultDialog(self.frame).show_modal()
        self._set_status("Closed sticky notes vault")

    def open_preferences(self) -> None:
        """Open the multi-page Preferences hub.

        A single book control hosts one page per settings area. The selector is
        a stock wx book widget so it is keyboard- and screen-reader-accessible
        by construction, with native first-letter type-ahead and arrow-key
        movement, and the first category is selected on open. The selector chrome
        is chosen per platform: a left-hand category list (``wx.Listbook``,
        Edge/Settings style) on Windows and Linux, and a top category toolbar
        (``wx.Toolbook``, macOS System Settings style) on macOS. Moving across
        categories immediately swaps the content pane -- no intermediate
        "choose then press OK" step -- and each page opens its area with an
        explicit button.
        """
        wx = self._wx
        # (label, description, handler) per settings area. The description is
        # shown in the content pane so arrowing the selector previews each area.
        areas: list[tuple[str, str, Callable[[], None]]] = [
            (
                "General",
                "Appearance, editing, autosave, updates, and the AI master switch.",
                self.open_general_preferences,
            ),
            (
                "Profiles and Features",
                "Turn optional features on or off and switch between feature profiles.",
                self.open_profiles_and_features_settings,
            ),
            (
                "Status Bar Layout",
                "Choose which fields appear in the status bar and their order.",
                self.open_status_bar_settings,
            ),
            (
                "Keymap Editor",
                "Review and change the keyboard shortcuts for every command.",
                self.open_keymap_editor,
            ),
            (
                "AI Connection",
                "Connect an AI provider, enter your key, and verify the connection.",
                self.open_ai_preferences,
            ),
            (
                "Watch Folder Automation",
                "Automate actions when files appear in a folder you watch.",
                self.open_watch_folder_settings,
            ),
            (
                "GLOW Accessibility",
                "Quill's built-in accessibility engine and its optional network features.",
                self.open_glow_settings,
            ),
            (
                "Install Starter Snippet Packs",
                "Add a set of ready-made text snippets you can insert while writing.",
                self.install_starter_snippet_packs,
            ),
        ]
        # macOS users expect a top toolbar selector (System Settings); Windows
        # and Linux expect a left-hand category list (Edge / Windows Settings).
        use_toolbook = sys.platform == "darwin"
        # The handler chosen by the user; run after the hub closes so only one
        # modal is on screen at a time.
        chosen: dict[str, Callable[[], None] | None] = {"handler": None}

        with wx.Dialog(self.frame, title="Preferences") as dialog:
            outer = wx.BoxSizer(wx.VERTICAL)
            if use_toolbook:
                book = wx.Toolbook(dialog, style=wx.BK_TOP)
            else:
                book = wx.Listbook(dialog, style=wx.BK_LEFT)
            book.SetName("Preferences categories")

            def _make_open(handler: Callable[[], None]) -> Callable[[object], None]:
                def _on_open(_event: object) -> None:
                    chosen["handler"] = handler
                    dialog.EndModal(wx.ID_OK)

                return _on_open

            for label, description, handler in areas:
                page = wx.Panel(book, style=wx.TAB_TRAVERSAL)
                page_sizer = wx.BoxSizer(wx.VERTICAL)
                heading = wx.StaticText(page, label=label)
                heading_font = heading.GetFont()
                heading_font.MakeBold()
                heading.SetFont(heading_font)
                page_sizer.Add(heading, 0, wx.ALL, 8)
                intro = wx.StaticText(page, label=description)
                intro.Wrap(420)
                page_sizer.Add(intro, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
                open_btn = wx.Button(page, label=f"&Open {label}...")
                open_btn.SetName(f"Open {label}")
                open_btn.Bind(wx.EVT_BUTTON, _make_open(handler))
                page_sizer.Add(open_btn, 0, wx.ALL, 8)
                page.SetSizer(page_sizer)
                book.AddPage(page, label)

            if book.GetPageCount() > 0:
                book.SetSelection(0)
            outer.Add(book, 1, wx.EXPAND | wx.ALL, 8)

            # Enter on a highlighted category opens it, so keyboard users do not
            # have to Tab to the page's Open button. When a button already holds
            # focus, let the keystroke fall through so it activates that button
            # (or the default Close button) as usual.
            def _on_char_hook(event: object) -> None:
                key = event.GetKeyCode()
                if key not in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                    event.Skip()
                    return
                focused = wx.Window.FindFocus()
                if isinstance(focused, wx.Button):
                    event.Skip()
                    return
                index = book.GetSelection()
                if 0 <= index < len(areas):
                    chosen["handler"] = areas[index][2]
                    dialog.EndModal(wx.ID_OK)
                    return
                event.Skip()

            dialog.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)

            buttons = dialog.CreateButtonSizer(wx.CLOSE)
            if buttons is not None:
                outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
            dialog.SetSizerAndFit(outer)
            # Land initial focus on the category selector so arrow keys and
            # first-letter type-ahead work the instant the hub opens. The
            # selector (Listbook list / Toolbook toolbar) is not one of the
            # generic preferred-focus classes, so opt out of the heuristic and
            # keep this explicit focus on both platforms.
            book.SetFocus()
            dialog._quill_keep_initial_focus = True
            self._show_modal_dialog(dialog, "Preferences")

        handler = chosen["handler"]
        if handler is None:
            self._set_status("Preferences closed")
            return
        handler()

    def open_glow_settings(self) -> None:
        """Open the GLOW accessibility settings (engine toggle + network consent).

        GLOW is enabled by default and runs locally; the optional networked
        features stay off until the user explicitly turns them on here (GLOW-7).
        """
        from quill.ui.web_form import show_web_form

        values = show_web_form(
            self.frame,
            self._wx,
            title="GLOW Accessibility",
            intro=(
                "GLOW is Quill's built-in accessibility engine. It is on by default "
                "and runs entirely on your computer. The optional features below can "
                "use a network connection and are off until you turn them on. Quill "
                "never sends your document anywhere without asking first."
            ),
            fields=[
                {
                    "name": "enabled",
                    "label": "Enable the GLOW accessibility engine",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_enabled", True),
                },
                {
                    "name": "ai_alt_text",
                    "label": "Allow optional AI alt-text generation (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_ai_alt_text_consent", False),
                },
                {
                    "name": "pii_redaction",
                    "label": "Allow optional PII redaction (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_pii_redaction_consent", False),
                },
                {
                    "name": "language_processing",
                    "label": "Allow optional WCAG language processing (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_language_processing_consent", False),
                },
            ],
        )
        if values is None:
            self._set_status("GLOW settings cancelled")
            return
        self.settings.glow_enabled = bool(values.get("enabled", True))
        self.settings.glow_ai_alt_text_consent = bool(values.get("ai_alt_text"))
        self.settings.glow_pii_redaction_consent = bool(values.get("pii_redaction"))
        self.settings.glow_language_processing_consent = bool(values.get("language_processing"))
        save_settings(self.settings)
        self._set_status("GLOW settings saved")

    #: Wildcard for exported QUILL settings files (SET-7).
    QSF_WILDCARD = "QUILL settings file (*.qsf)|*.qsf|All files (*.*)|*.*"
    QPF_WILDCARD = "QUILL profile file (*.qpf)|*.qpf|All files (*.*)|*.*"
    KQP_WILDCARD = "Keyboard Quill Pack (*.kqp)|*.kqp|All files (*.*)|*.*"

    def _settings_dialog_apply_refresh(self, status: str) -> None:
        """Persist ``self.settings`` and re-run every UI side effect.

        Shared by the OK, Reset to Factory Defaults, and Import paths of the
        tabbed Settings dialog so each one leaves the app in a consistent state.
        """
        save_settings(self.settings)
        self.set_theme(self.settings.theme)
        self._set_spellcheck_mode(self.settings.spellcheck_as_you_type)
        self._autosave_interval = timedelta(
            seconds=int(getattr(self.settings, "autosave_interval_seconds", 30))
        )
        self._apply_ai_menu_enabled()
        self._refresh_ai_status()
        self._apply_soft_wrap_setting()
        self._rebuild_tab_host(self.settings.show_tab_control)
        self._build_menu()
        self._apply_dirty_title_style_setting()
        self._refresh_title()
        self._refresh_view_menu_checks()
        self._clear_navigation_issue_state()
        try:
            from quill.ui import sound_manager

            sound_manager.on_settings_changed(self.settings)
        except Exception:  # noqa: BLE001
            pass
        self._set_status(status)

    def open_menu_editor(self) -> None:
        """Open the accessible Menu Editor for reordering, hiding, and renaming
        top-level menus, menu items, and context menu items, with one Reset to
        Factory Defaults (MENU-5).

        Edits are made on a working copy and only persisted when the person
        chooses Save, so Cancel always leaves the live menus untouched.
        """
        wx = self._wx
        default_keys = [key for key, _ in _TOP_MENU_DEFS]
        default_labels = dict(_TOP_MENU_DEFS)
        current = self._ensure_menu_customization()
        working = MenuCustomization.from_dict(current.to_dict())

        # Discover menu items from the currently built menu bar
        menu_items_by_menu: dict[str, list[tuple[str, str]]] = {}
        context_menu_items: list[tuple[str, str]] = []

        try:
            menu_bar = self.frame.GetMenuBar()
            if menu_bar is not None:
                # Build a label-to-key mapping for top-level menus
                label_to_key = {_normalize_menu_label(label): key for key, label in _TOP_MENU_DEFS}

                for menu_index in range(menu_bar.GetMenuCount()):
                    menu = menu_bar.GetMenu(menu_index)
                    menu_label = menu_bar.GetMenuLabelText(menu_index)
                    menu_key = label_to_key.get(_normalize_menu_label(menu_label))

                    if menu_key:
                        items = self._discover_menu_items(menu)
                        if items:
                            menu_items_by_menu[menu_key] = items

                # Discover context menu items (we'll build a temporary one)
                context_menu_items = self._discover_context_menu_items()
        except Exception:
            # If discovery fails, continue with empty item lists
            pass

        # Collect all known item keys for reconciliation
        all_item_keys = set()
        for items in menu_items_by_menu.values():
            all_item_keys.update(key for key, _ in items)
        all_item_keys.update(key for key, _ in context_menu_items)

        working.reconcile(set(default_keys), all_item_keys)

        with wx.Dialog(self.frame, title="Customize Menus", size=(720, 560)) as dialog:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(
                wx.StaticText(
                    dialog,
                    label=(
                        "Customize menus, menu items, and the context menu. "
                        "Changes apply when you choose Save."
                    ),
                ),
                0,
                wx.ALL,
                8,
            )

            notebook = wx.Notebook(dialog)
            notebook.SetName("Menu customization tabs")

            # Tab 1: Top-level menus
            top_panel = wx.Panel(notebook)
            self._build_top_menu_editor_tab(
                top_panel, wx, working, default_keys, default_labels, dialog
            )
            notebook.AddPage(top_panel, "Top-Level Menus")

            # Tab 2: Menu items
            items_panel = wx.Panel(notebook)
            self._build_menu_items_editor_tab(
                items_panel, wx, working, default_keys, default_labels, menu_items_by_menu, dialog
            )
            notebook.AddPage(items_panel, "Menu Items")

            # Tab 3: Context menu
            context_panel = wx.Panel(notebook)
            self._build_context_menu_editor_tab(
                context_panel, wx, working, context_menu_items, dialog
            )
            notebook.AddPage(context_panel, "Context Menu")

            outer.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)

            buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
            if buttons is not None:
                outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            ok_button = dialog.FindWindow(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetLabel("&Save")
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            dialog.SetSizer(outer)
            dialog.CentreOnParent()

            if self._show_modal_dialog(dialog, "Customize Menus") != wx.ID_OK:
                self._set_status("Menu customization cancelled")
                return

        working.reconcile(set(default_keys), all_item_keys)
        self._menu_customization = working
        try:
            save_menu_customization(working)
        except Exception:
            self._set_status("Could not save menu customization")
            return
        self._build_menu()
        if working.is_customized():
            self._set_status("Menu customization saved")
        else:
            self._set_status("Menus reset to factory defaults")

    def _discover_menu_items(self, menu: object) -> list[tuple[str, str]]:
        """Discover menu items (key, label) from a wx.Menu."""
        items: list[tuple[str, str]] = []
        try:
            for item_obj in menu.GetMenuItems():
                if item_obj.IsSeparator():
                    continue
                if item_obj.IsSubMenu():
                    continue  # Skip submenus for now
                item_id = item_obj.GetId()
                label = item_obj.GetItemLabelText()
                # Try to find the command key for this ID
                key = self._find_command_key_for_id(item_id)
                if key:
                    items.append((key, label))
                elif label:  # Fallback: use a synthesized key
                    synth_key = f"item.{label.lower().replace(' ', '_').replace('&', '')}"
                    items.append((synth_key, label))
        except Exception:
            pass
        return items

    def _find_command_key_for_id(self, item_id: int) -> str | None:
        """Find the command key for a given menu item ID."""
        # Build a reverse mapping from ID to command key
        id_to_command = {v: k for k, v in getattr(self, "_command_to_id", {}).items()}
        return id_to_command.get(item_id)

    def _discover_context_menu_items(self) -> list[tuple[str, str]]:
        """Discover context menu items by building a temporary context menu."""
        items: list[tuple[str, str]] = []
        # Return a hardcoded list of common context menu items for now
        # In a real implementation, we'd build the actual context menu
        # and discover items from it
        items = [
            ("edit.undo", "Undo"),
            ("edit.redo", "Redo"),
            ("edit.cut", "Cut"),
            ("edit.copy", "Copy"),
            ("edit.copy_with_source", "Copy With Source"),
            ("edit.paste", "Paste"),
            ("edit.select_all", "Select All"),
            ("edit.select_line", "Select Line"),
        ]
        return items

    def _build_top_menu_editor_tab(
        self,
        panel: object,
        wx: object,
        working: MenuCustomization,
        default_keys: list[str],
        default_labels: dict[str, str],
        dialog: object,
    ) -> None:
        """Build the top-level menus editor tab."""
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(
            wx.StaticText(
                panel,
                label="Reorder, rename, or hide top-level menus.",
            ),
            0,
            wx.ALL,
            8,
        )

        body = wx.BoxSizer(wx.HORIZONTAL)
        menu_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        menu_list.SetName("Top-level menus")
        body.Add(menu_list, 1, wx.EXPAND | wx.RIGHT, 8)

        button_col = wx.BoxSizer(wx.VERTICAL)
        up_btn = wx.Button(panel, label="Move &Up")
        down_btn = wx.Button(panel, label="Move &Down")
        rename_btn = wx.Button(panel, label="&Rename...")
        hide_btn = wx.Button(panel, label="&Show/Hide")
        reset_btn = wx.Button(panel, label="Reset to &Factory Defaults")
        for btn in (up_btn, down_btn, rename_btn, hide_btn, reset_btn):
            button_col.Add(btn, 0, wx.EXPAND | wx.BOTTOM, 6)
        body.Add(button_col, 0)
        outer.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        def _ordered() -> list[str]:
            return working.ordered_top_keys(default_keys)

        def _entry_label(key: str) -> str:
            label = _normalize_menu_label(working.top_label(key, default_labels[key]))
            if working.is_top_hidden(key):
                return f"{label} (hidden)"
            return label

        def _refresh(select_key: str | None = None) -> None:
            keys = _ordered()
            menu_list.Set([_entry_label(key) for key in keys])
            if not keys:
                return
            target = select_key if select_key in keys else keys[0]
            menu_list.SetSelection(keys.index(target))

        def _selected_key() -> str | None:
            index = menu_list.GetSelection()
            keys = _ordered()
            if index is None or index < 0 or index >= len(keys):
                return None
            return keys[index]

        def _move(delta: int) -> None:
            keys = _ordered()
            key = _selected_key()
            if key is None:
                return
            index = keys.index(key)
            new_index = index + delta
            if new_index < 0 or new_index >= len(keys):
                return
            keys.insert(new_index, keys.pop(index))
            working.set_top_order(keys)
            _refresh(key)

        def _on_up(_event: object) -> None:
            _move(-1)

        def _on_down(_event: object) -> None:
            _move(1)

        def _on_rename(_event: object) -> None:
            key = _selected_key()
            if key is None:
                return
            current_label = _normalize_menu_label(working.top_label(key, default_labels[key]))
            with wx.TextEntryDialog(
                dialog,
                "Menu name (use & before a letter for the keyboard mnemonic):",
                "Rename Menu",
                current_label,
            ) as entry:
                if self._show_modal_dialog(entry, "Rename Menu") != wx.ID_OK:
                    return
                new_label = entry.GetValue().strip()
            if not new_label:
                return
            working.rename_top(key, new_label)
            _refresh(key)

        def _on_hide(_event: object) -> None:
            key = _selected_key()
            if key is None:
                return
            working.set_top_hidden(key, not working.is_top_hidden(key))
            _refresh(key)

        def _on_reset(_event: object) -> None:
            working.reset()
            _refresh()

        up_btn.Bind(wx.EVT_BUTTON, _on_up)
        down_btn.Bind(wx.EVT_BUTTON, _on_down)
        rename_btn.Bind(wx.EVT_BUTTON, _on_rename)
        hide_btn.Bind(wx.EVT_BUTTON, _on_hide)
        reset_btn.Bind(wx.EVT_BUTTON, _on_reset)

        panel.SetSizer(outer)
        _refresh()

    def _build_menu_items_editor_tab(
        self,
        panel: object,
        wx: object,
        working: MenuCustomization,
        default_keys: list[str],
        default_labels: dict[str, str],
        menu_items_by_menu: dict[str, list[tuple[str, str]]],
        dialog: object,
    ) -> None:
        """Build the menu items editor tab."""

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(
            wx.StaticText(
                panel,
                label="Select a menu, then reorder, rename, or hide its items.",
            ),
            0,
            wx.ALL,
            8,
        )

        body = wx.BoxSizer(wx.HORIZONTAL)

        # Left side: menu selection
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(panel, label="Menu:"), 0, wx.BOTTOM, 4)
        menu_choice = wx.ListBox(panel, style=wx.LB_SINGLE)
        menu_choice.SetName("Select menu")
        left.Add(menu_choice, 1, wx.EXPAND)
        body.Add(left, 0, wx.EXPAND | wx.RIGHT, 8)

        # Middle: item list
        middle = wx.BoxSizer(wx.VERTICAL)
        middle.Add(wx.StaticText(panel, label="Items:"), 0, wx.BOTTOM, 4)
        item_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        item_list.SetName("Menu items")
        middle.Add(item_list, 1, wx.EXPAND)
        body.Add(middle, 1, wx.EXPAND | wx.RIGHT, 8)

        # Right side: buttons
        button_col = wx.BoxSizer(wx.VERTICAL)
        up_btn = wx.Button(panel, label="Move &Up")
        down_btn = wx.Button(panel, label="Move &Down")
        rename_btn = wx.Button(panel, label="&Rename...")
        hide_btn = wx.Button(panel, label="&Show/Hide")
        for btn in (up_btn, down_btn, rename_btn, hide_btn):
            button_col.Add(btn, 0, wx.EXPAND | wx.BOTTOM, 6)
        body.Add(button_col, 0)
        outer.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        current_menu_key: list[str | None] = [None]  # Mutable container for closure

        def _selected_menu_key() -> str | None:
            index = menu_choice.GetSelection()
            if index is None or index < 0:
                return None
            return current_menu_key[0]

        def _refresh_menu_list() -> None:
            menus = [
                (key, default_labels[key]) for key in default_keys if key in menu_items_by_menu
            ]
            menu_choice.Set([label for _, label in menus])
            if menus and menu_choice.GetSelection() < 0:
                menu_choice.SetSelection(0)
                current_menu_key[0] = menus[0][0]
            elif menus:
                idx = menu_choice.GetSelection()
                current_menu_key[0] = menus[idx][0] if 0 <= idx < len(menus) else None

        def _get_default_items(menu_key: str) -> list[tuple[str, str]]:
            return menu_items_by_menu.get(menu_key, [])

        def _ordered_items(menu_key: str) -> list[str]:
            default_items = _get_default_items(menu_key)
            default_keys_for_menu = [key for key, _ in default_items]
            return working.ordered_item_keys(menu_key, default_keys_for_menu)

        def _item_entry_label(item_key: str, default_label: str) -> str:
            label = _normalize_menu_label(working.item_label(item_key, default_label))
            if working.is_item_hidden(item_key):
                return f"{label} (hidden)"
            return label

        def _refresh_item_list(select_key: str | None = None) -> None:
            menu_key = _selected_menu_key()
            if not menu_key:
                item_list.Set([])
                return

            default_items = _get_default_items(menu_key)
            default_labels_map = dict(default_items)
            keys = _ordered_items(menu_key)
            item_list.Set([
                _item_entry_label(key, default_labels_map.get(key, key)) for key in keys
            ])
            if keys:
                if select_key and select_key in keys:
                    item_list.SetSelection(keys.index(select_key))
                elif item_list.GetSelection() < 0:
                    item_list.SetSelection(0)

        def _selected_item_key() -> str | None:
            menu_key = _selected_menu_key()
            if not menu_key:
                return None
            index = item_list.GetSelection()
            keys = _ordered_items(menu_key)
            if index is None or index < 0 or index >= len(keys):
                return None
            return keys[index]

        def _move_item(delta: int) -> None:
            menu_key = _selected_menu_key()
            if not menu_key:
                return
            item_key = _selected_item_key()
            if not item_key:
                return
            keys = _ordered_items(menu_key)
            index = keys.index(item_key)
            new_index = index + delta
            if new_index < 0 or new_index >= len(keys):
                return
            keys.insert(new_index, keys.pop(index))
            working.set_item_order(menu_key, keys)
            _refresh_item_list(item_key)

        def _on_menu_select(_event: object) -> None:
            idx = menu_choice.GetSelection()
            if idx >= 0:
                menus = [
                    (key, default_labels[key]) for key in default_keys if key in menu_items_by_menu
                ]
                if idx < len(menus):
                    current_menu_key[0] = menus[idx][0]
            _refresh_item_list()

        def _on_up(_event: object) -> None:
            _move_item(-1)

        def _on_down(_event: object) -> None:
            _move_item(1)

        def _on_rename(_event: object) -> None:
            item_key = _selected_item_key()
            if not item_key:
                return
            menu_key = _selected_menu_key()
            if not menu_key:
                return
            default_items = _get_default_items(menu_key)
            default_labels_map = dict(default_items)
            current_label = _normalize_menu_label(
                working.item_label(item_key, default_labels_map.get(item_key, item_key))
            )
            with wx.TextEntryDialog(
                dialog,
                "Item name (use & before a letter for the keyboard mnemonic):",
                "Rename Item",
                current_label,
            ) as entry:
                if self._show_modal_dialog(entry, "Rename Item") != wx.ID_OK:
                    return
                new_label = entry.GetValue().strip()
            if not new_label:
                return
            working.rename_item(item_key, new_label)
            _refresh_item_list(item_key)

        def _on_hide(_event: object) -> None:
            item_key = _selected_item_key()
            if not item_key:
                return
            working.set_item_hidden(item_key, not working.is_item_hidden(item_key))
            _refresh_item_list(item_key)

        menu_choice.Bind(wx.EVT_LISTBOX, _on_menu_select)
        up_btn.Bind(wx.EVT_BUTTON, _on_up)
        down_btn.Bind(wx.EVT_BUTTON, _on_down)
        rename_btn.Bind(wx.EVT_BUTTON, _on_rename)
        hide_btn.Bind(wx.EVT_BUTTON, _on_hide)

        panel.SetSizer(outer)
        _refresh_menu_list()
        _refresh_item_list()

    def _build_context_menu_editor_tab(
        self,
        panel: object,
        wx: object,
        working: MenuCustomization,
        context_items: list[tuple[str, str]],
        dialog: object,
    ) -> None:
        """Build the context menu editor tab."""
        from quill.core.menu_customization import CONTEXT_MENU_KEY

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(
            wx.StaticText(
                panel,
                label="Reorder, rename, or hide context menu items.",
            ),
            0,
            wx.ALL,
            8,
        )

        body = wx.BoxSizer(wx.HORIZONTAL)
        item_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        item_list.SetName("Context menu items")
        body.Add(item_list, 1, wx.EXPAND | wx.RIGHT, 8)

        button_col = wx.BoxSizer(wx.VERTICAL)
        up_btn = wx.Button(panel, label="Move &Up")
        down_btn = wx.Button(panel, label="Move &Down")
        rename_btn = wx.Button(panel, label="&Rename...")
        hide_btn = wx.Button(panel, label="&Show/Hide")
        for btn in (up_btn, down_btn, rename_btn, hide_btn):
            button_col.Add(btn, 0, wx.EXPAND | wx.BOTTOM, 6)
        body.Add(button_col, 0)
        outer.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        default_items_map = dict(context_items)
        default_item_keys = [key for key, _ in context_items]

        def _ordered() -> list[str]:
            return working.ordered_item_keys(CONTEXT_MENU_KEY, default_item_keys)

        def _entry_label(key: str) -> str:
            default_label = default_items_map.get(key, key)
            label = _normalize_menu_label(working.item_label(key, default_label))
            if working.is_item_hidden(key):
                return f"{label} (hidden)"
            return label

        def _refresh(select_key: str | None = None) -> None:
            keys = _ordered()
            item_list.Set([_entry_label(key) for key in keys])
            if not keys:
                return
            if select_key and select_key in keys:
                item_list.SetSelection(keys.index(select_key))
            elif item_list.GetSelection() < 0:
                item_list.SetSelection(0)

        def _selected_key() -> str | None:
            index = item_list.GetSelection()
            keys = _ordered()
            if index is None or index < 0 or index >= len(keys):
                return None
            return keys[index]

        def _move(delta: int) -> None:
            keys = _ordered()
            key = _selected_key()
            if key is None:
                return
            index = keys.index(key)
            new_index = index + delta
            if new_index < 0 or new_index >= len(keys):
                return
            keys.insert(new_index, keys.pop(index))
            working.set_item_order(CONTEXT_MENU_KEY, keys)
            _refresh(key)

        def _on_up(_event: object) -> None:
            _move(-1)

        def _on_down(_event: object) -> None:
            _move(1)

        def _on_rename(_event: object) -> None:
            key = _selected_key()
            if key is None:
                return
            current_label = _normalize_menu_label(
                working.item_label(key, default_items_map.get(key, key))
            )
            with wx.TextEntryDialog(
                dialog,
                "Item name (use & before a letter for the keyboard mnemonic):",
                "Rename Context Menu Item",
                current_label,
            ) as entry:
                if self._show_modal_dialog(entry, "Rename Context Menu Item") != wx.ID_OK:
                    return
                new_label = entry.GetValue().strip()
            if not new_label:
                return
            working.rename_item(key, new_label)
            _refresh(key)

        def _on_hide(_event: object) -> None:
            key = _selected_key()
            if key is None:
                return
            working.set_item_hidden(key, not working.is_item_hidden(key))
            _refresh(key)

        up_btn.Bind(wx.EVT_BUTTON, _on_up)
        down_btn.Bind(wx.EVT_BUTTON, _on_down)
        rename_btn.Bind(wx.EVT_BUTTON, _on_rename)
        hide_btn.Bind(wx.EVT_BUTTON, _on_hide)

        panel.SetSizer(outer)
        _refresh()

    def open_general_preferences(self) -> None:
        from quill.core import settings_registry as registry
        from quill.core.ai.model_manager import load_ai_enabled, save_ai_enabled

        wx = self._wx

        # Readers map each rendered registry key to a callable returning its
        # stored (normalized) value. Index maps key -> (page_index, control) so
        # the search box can jump straight to a matching control.
        readers: dict[str, Callable[[], object]] = {}
        # writers set a rendered control back to a given stored value; used by
        # the per-setting Reset buttons (SET-6) to restore a single default.
        writers: dict[str, Callable[[object], None]] = {}
        control_index: dict[str, tuple[int, object]] = {}
        ai_enabled_cb = None  # special-cased: not a Settings field
        ext_master_cb = None  # special-cased: external-engine master consent
        ext_name_field = None
        ext_command_field = None
        ext_engine_enabled_cb = None
        collected: dict[str, object] = {}
        ai_value: bool | None = None
        ext_master_value: bool | None = None
        ext_engine_spec: tuple[str, str, bool] | None = None

        with wx.Dialog(self.frame, title="Settings") as dialog:
            outer = wx.BoxSizer(wx.VERTICAL)

            notebook = wx.Notebook(dialog)
            notebook.SetName("Settings categories")

            def _add_field_row(
                parent_panel, sizer, label: str, control_or_factory, reset=None
            ) -> object:
                row = wx.BoxSizer(wx.HORIZONTAL)
                row.Add(
                    wx.StaticText(parent_panel, label=label),
                    0,
                    wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                    8,
                )
                ctrl = control_or_factory() if callable(control_or_factory) else control_or_factory
                row.Add(ctrl, 1, wx.EXPAND)
                if reset is not None:
                    row.Add(reset, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
                sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)
                return ctrl

            def _reset_one(key: str) -> None:
                writer = writers.get(key)
                if writer is None:
                    return
                writer(registry.default_value(key))
                spec = registry.find_spec(key)
                self._set_status(f"Reset {spec.label if spec else key} to default")

            def _reset_button(parent_panel, spec):
                button = wx.Button(parent_panel, label="Reset", style=wx.BU_EXACTFIT)
                button.SetName(f"Reset {spec.label} to default")
                button.Bind(wx.EVT_BUTTON, lambda _e, k=spec.key: _reset_one(k))
                return button

            def _make_control(parent_panel, sizer, spec, page_index: int) -> None:
                current = registry.get_value(self.settings, spec.key)
                reset_btn = _reset_button(parent_panel, spec)
                # preview_browser is stored as text but is best chosen from the
                # list of installed browsers.
                if spec.key == "preview_browser":
                    choice = wx.Choice(
                        parent_panel,
                        choices=[opt.label for opt in available_browser_options()],
                    )
                    choice.SetName(spec.label)
                    choice.SetStringSelection(browser_choice_label_for_value(str(current)))
                    _add_field_row(parent_panel, sizer, spec.label, choice, reset_btn)
                    readers[spec.key] = lambda c=choice: browser_choice_value_for_label(
                        c.GetStringSelection() or "System default browser"
                    )
                    writers[spec.key] = lambda v, c=choice: c.SetStringSelection(
                        browser_choice_label_for_value(str(v))
                    )
                    control_index[spec.key] = (page_index, choice)
                    return
                if spec.key == "startup_folder":
                    text = wx.TextCtrl(parent_panel)
                    text.SetValue(str(current))
                    text.SetName(spec.label)
                    browse_btn = wx.Button(parent_panel, label="Browse...")
                    browse_btn.SetName(f"Browse for {spec.label}")
                    folder_row = wx.BoxSizer(wx.HORIZONTAL)
                    folder_row.Add(text, 1, wx.EXPAND | wx.RIGHT, 8)
                    folder_row.Add(browse_btn, 0, wx.ALIGN_CENTER_VERTICAL)

                    def _on_browse_folder(_evt, _t=text, _pp=parent_panel) -> None:
                        with wx.DirDialog(
                            _pp,
                            "Choose default file-open folder",
                            defaultPath=_t.GetValue().strip(),
                            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
                        ) as ddlg:
                            if (
                                self._show_modal_dialog(ddlg, "Default file-open folder")
                                == wx.ID_OK
                            ):
                                _t.SetValue(ddlg.GetPath())

                    browse_btn.Bind(wx.EVT_BUTTON, _on_browse_folder)
                    _add_field_row(parent_panel, sizer, spec.label, folder_row, reset_btn)
                    readers[spec.key] = lambda c=text: str(c.GetValue())
                    writers[spec.key] = lambda v, c=text: c.SetValue(str(v))
                    control_index[spec.key] = (page_index, text)
                    return
                if spec.key in {
                    "quill_key_sound_enter",
                    "quill_key_sound_exit",
                    "quill_key_sound_move",
                    "quill_key_sound_error",
                }:
                    text = wx.TextCtrl(parent_panel)
                    text.SetValue(str(current))
                    text.SetName(spec.label)
                    browse_btn = wx.Button(parent_panel, label="Browse...")
                    browse_btn.SetName(f"Browse for {spec.label}")
                    file_row = wx.BoxSizer(wx.HORIZONTAL)
                    file_row.Add(text, 1, wx.EXPAND | wx.RIGHT, 8)
                    file_row.Add(browse_btn, 0, wx.ALIGN_CENTER_VERTICAL)

                    def _on_browse_sound(_evt, _t=text, _pp=parent_panel) -> None:
                        with wx.FileDialog(
                            _pp,
                            "Choose a WAV file",
                            wildcard="WAV files (*.wav)|*.wav",
                            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                        ) as fdlg:
                            if self._show_modal_dialog(fdlg, "Choose Keyboard Sound") == wx.ID_OK:
                                _t.SetValue(fdlg.GetPath())

                    browse_btn.Bind(wx.EVT_BUTTON, _on_browse_sound)
                    _add_field_row(parent_panel, sizer, spec.label, file_row, reset_btn)
                    readers[spec.key] = lambda c=text: str(c.GetValue())
                    writers[spec.key] = lambda v, c=text: c.SetValue(str(v))
                    control_index[spec.key] = (page_index, text)
                    return
                if spec.kind == "bool":
                    cb = wx.CheckBox(parent_panel, label=spec.label)
                    cb.SetValue(bool(current))
                    if spec.description:
                        cb.SetName(f"{spec.label}. {spec.description}")
                    bool_row = wx.BoxSizer(wx.HORIZONTAL)
                    bool_row.Add(cb, 1, wx.ALIGN_CENTER_VERTICAL)
                    bool_row.Add(reset_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
                    sizer.Add(bool_row, 0, wx.EXPAND | wx.ALL, 6)
                    readers[spec.key] = lambda c=cb: bool(c.GetValue())
                    writers[spec.key] = lambda v, c=cb: c.SetValue(bool(v))
                    control_index[spec.key] = (page_index, cb)
                    if spec.key == "beta_updates":

                        def _on_beta_toggle(_event: object, _cb=cb) -> None:
                            if _cb.GetValue() and not self._confirm_beta_channel():
                                _cb.SetValue(False)

                        cb.Bind(wx.EVT_CHECKBOX, _on_beta_toggle)
                    return
                if spec.kind == "choice":
                    labels = [label for _value, label in spec.choices]
                    value_for_label = {label: value for value, label in spec.choices}
                    label_for_value = {value: label for value, label in spec.choices}
                    choice = wx.Choice(parent_panel, choices=labels)
                    choice.SetName(spec.label)
                    choice.SetStringSelection(label_for_value.get(str(current), labels[0]))
                    _add_field_row(parent_panel, sizer, spec.label, choice, reset_btn)
                    readers[spec.key] = lambda c=choice, m=value_for_label, d=str(current): m.get(
                        c.GetStringSelection(), d
                    )
                    writers[spec.key] = lambda v, c=choice, m=label_for_value, ls=labels: (
                        c.SetStringSelection(m.get(str(v), ls[0]))
                    )
                    control_index[spec.key] = (page_index, choice)
                    return
                if spec.kind == "int":
                    spin = wx.SpinCtrl(parent_panel)
                    if spec.minimum is not None and spec.maximum is not None:
                        spin.SetRange(int(spec.minimum), int(spec.maximum))
                    spin.SetValue(int(current))
                    spin.SetName(spec.label)
                    _add_field_row(parent_panel, sizer, spec.label, spin, reset_btn)
                    readers[spec.key] = lambda c=spin: int(c.GetValue())
                    writers[spec.key] = lambda v, c=spin: c.SetValue(int(v))
                    control_index[spec.key] = (page_index, spin)
                    return
                if spec.kind == "float":
                    spin = wx.SpinCtrlDouble(parent_panel, inc=0.1)
                    if spec.minimum is not None and spec.maximum is not None:
                        spin.SetRange(float(spec.minimum), float(spec.maximum))
                    spin.SetValue(float(current))
                    spin.SetName(spec.label)
                    _add_field_row(parent_panel, sizer, spec.label, spin, reset_btn)
                    readers[spec.key] = lambda c=spin: float(c.GetValue())
                    writers[spec.key] = lambda v, c=spin: c.SetValue(float(v))
                    control_index[spec.key] = (page_index, spin)
                    return
                # text
                text = wx.TextCtrl(parent_panel)
                text.SetValue(str(current))
                text.SetName(spec.label)
                _add_field_row(parent_panel, sizer, spec.label, text, reset_btn)
                readers[spec.key] = lambda c=text: str(c.GetValue())
                writers[spec.key] = lambda v, c=text: c.SetValue(str(v))
                control_index[spec.key] = (page_index, text)

            page_index = 0
            for group in registry.groups():
                specs = [
                    spec
                    for spec in registry.specs_for_group(group.id)
                    if not spec.feature_id or self._feature_enabled(spec.feature_id)
                ]
                # Surface the AI master toggle on the AI page even though it is
                # stored outside Settings.
                show_ai_master = group.id == "ai"
                if not specs and not show_ai_master:
                    continue
                page = wx.Panel(notebook, style=wx.TAB_TRAVERSAL)
                page_sizer = wx.BoxSizer(wx.VERTICAL)
                if group.description:
                    intro = wx.StaticText(page, label=group.description)
                    page_sizer.Add(intro, 0, wx.ALL, 6)
                if show_ai_master:
                    ai_enabled_cb = wx.CheckBox(page, label="Use Artificial Intelligence")
                    ai_enabled_cb.SetValue(load_ai_enabled())
                    ai_enabled_cb.SetName(
                        "Use Artificial Intelligence. Master switch for all AI features."
                    )
                    page_sizer.Add(ai_enabled_cb, 0, wx.ALL, 6)
                    # External engines (AI-24): consent + one engine's command,
                    # folded into the Settings home rather than a separate dialog.
                    from quill.core.ai.external_engine import (
                        external_engines_enabled,
                        list_engine_ids,
                        load_engine_config,
                    )

                    ext_master_cb = wx.CheckBox(page, label="Allow external engines")
                    ext_master_cb.SetValue(external_engines_enabled())
                    ext_master_cb.SetName(
                        "Allow external engines. Off by default. Let QUILL drive a "
                        "trusted helper program as a local subprocess."
                    )
                    page_sizer.Add(ext_master_cb, 0, wx.ALL, 6)
                    _engine_ids = list_engine_ids()
                    _first_engine = load_engine_config(_engine_ids[0]) if _engine_ids else None
                    ext_name_field = _add_field_row(
                        page,
                        page_sizer,
                        "External engine name",
                        lambda p=page: wx.TextCtrl(p),
                    )
                    ext_name_field.SetName("External engine name")
                    ext_name_field.SetValue(_first_engine.engine_id if _first_engine else "")
                    ext_command_field = _add_field_row(
                        page,
                        page_sizer,
                        "External engine command",
                        lambda p=page: wx.TextCtrl(p),
                    )
                    ext_command_field.SetName("External engine command")
                    ext_command_field.SetValue(
                        " ".join(_first_engine.command) if _first_engine else ""
                    )
                    ext_engine_enabled_cb = wx.CheckBox(page, label="Enable this external engine")
                    ext_engine_enabled_cb.SetValue(
                        bool(_first_engine.enabled) if _first_engine else False
                    )
                    page_sizer.Add(ext_engine_enabled_cb, 0, wx.ALL, 6)
                for spec in specs:
                    _make_control(page, page_sizer, spec, page_index)
                page.SetSizer(page_sizer)
                notebook.AddPage(page, group.title)
                page_index += 1

            outer.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)

            # --- Maintenance buttons (SET-7): Export / Import / Reset ----------
            maintenance = wx.BoxSizer(wx.HORIZONTAL)
            export_btn = wx.Button(dialog, label="&Export settings...")
            import_btn = wx.Button(dialog, label="&Import settings...")
            reset_btn = wx.Button(dialog, label="&Reset to Factory Defaults")
            maintenance.Add(export_btn, 0, wx.RIGHT, 8)
            maintenance.Add(import_btn, 0, wx.RIGHT, 8)
            maintenance.Add(reset_btn, 0)
            outer.Add(maintenance, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # --- Profile buttons (FLAG-4): export / import feature-flag state --
            profile_row = wx.BoxSizer(wx.HORIZONTAL)
            export_profile_btn = wx.Button(dialog, label="Export &profile...")
            import_profile_btn = wx.Button(dialog, label="Import pro&file...")
            profile_row.Add(export_profile_btn, 0, wx.RIGHT, 8)
            profile_row.Add(import_profile_btn, 0)
            outer.Add(profile_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # action carries the post-dialog instruction: "ok" | "cancel" |
            # "import" | "reset"; imported holds the Settings parsed from a file.
            action: dict[str, object] = {"mode": "cancel", "imported": None}

            def _on_export(_event: object) -> None:
                with wx.FileDialog(
                    dialog,
                    "Export settings",
                    wildcard=self.QSF_WILDCARD,
                    style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                ) as file_dialog:
                    if self._show_modal_dialog(file_dialog, "Export settings") != wx.ID_OK:
                        return
                    target = Path(file_dialog.GetPath())
                if target.suffix.lower() != ".qsf":
                    target = target.with_suffix(".qsf")
                payload = registry.export_settings(self.settings)
                target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                self._set_status(f"Exported settings to {target.name}")

            def _on_import(_event: object) -> None:
                with wx.FileDialog(
                    dialog,
                    "Import settings",
                    wildcard=self.QSF_WILDCARD,
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                ) as file_dialog:
                    if self._show_modal_dialog(file_dialog, "Import settings") != wx.ID_OK:
                        return
                    source = Path(file_dialog.GetPath())
                try:
                    raw = json.loads(source.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    self._set_status(f"Could not read settings from {source.name}")
                    return
                action["mode"] = "import"
                action["imported"] = registry.import_settings(raw)
                dialog.EndModal(wx.ID_CANCEL)

            def _on_reset(_event: object) -> None:
                result = self._show_message_box(
                    "Reset every setting to its factory default? This cannot be undone.",
                    "Reset to Factory Defaults",
                    wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
                )
                if result != wx.YES:
                    return
                action["mode"] = "reset"
                dialog.EndModal(wx.ID_CANCEL)

            def _on_export_profile(_event: object) -> None:
                with wx.FileDialog(
                    dialog,
                    "Export profile",
                    wildcard=self.QPF_WILDCARD,
                    style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                ) as file_dialog:
                    if self._show_modal_dialog(file_dialog, "Export profile") != wx.ID_OK:
                        return
                    target = Path(file_dialog.GetPath())
                if target.suffix.lower() != ".qpf":
                    target = target.with_suffix(".qpf")
                try:
                    export_feature_profile_file(self.features, target)
                except OSError:
                    self._set_status(f"Could not write profile to {target.name}")
                    return
                self._set_status(f"Exported feature profile to {target.name}")

            def _on_import_profile(_event: object) -> None:
                with wx.FileDialog(
                    dialog,
                    "Import profile",
                    wildcard=self.QPF_WILDCARD,
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                ) as file_dialog:
                    if self._show_modal_dialog(file_dialog, "Import profile") != wx.ID_OK:
                        return
                    source = Path(file_dialog.GetPath())
                try:
                    warnings = import_feature_profile_file(self.features, source)
                except (OSError, ValueError):
                    self._set_status(f"Could not read a feature profile from {source.name}")
                    return
                self._apply_accelerators()
                self._build_menu()
                profile_name = self.features.active_profile.name
                if warnings:
                    self._set_status(
                        f"Imported profile {profile_name} ({len(warnings)} item(s) ignored)"
                    )
                else:
                    self._set_status(f"Imported feature profile {profile_name}")

            export_btn.Bind(wx.EVT_BUTTON, _on_export)
            import_btn.Bind(wx.EVT_BUTTON, _on_import)
            reset_btn.Bind(wx.EVT_BUTTON, _on_reset)
            export_profile_btn.Bind(wx.EVT_BUTTON, _on_export_profile)
            import_profile_btn.Bind(wx.EVT_BUTTON, _on_import_profile)

            buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
            if buttons is not None:
                outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            dialog.SetSizerAndFit(outer)

            result = self._show_modal_dialog(dialog, "Settings")
            if result == wx.ID_OK:
                action["mode"] = "ok"
                collected = {key: reader() for key, reader in readers.items()}
                ai_value = bool(ai_enabled_cb.GetValue()) if ai_enabled_cb is not None else None
                ext_master_value = (
                    bool(ext_master_cb.GetValue()) if ext_master_cb is not None else None
                )
                if ext_name_field is not None and ext_command_field is not None:
                    ext_engine_spec = (
                        str(ext_name_field.GetValue()),
                        str(ext_command_field.GetValue()),
                        bool(ext_engine_enabled_cb.GetValue())
                        if ext_engine_enabled_cb is not None
                        else False,
                    )

        mode = action["mode"]
        if mode == "import":
            imported = action["imported"]
            if isinstance(imported, Settings):
                self.settings = imported
                self._settings_dialog_apply_refresh("Imported settings")
            return
        if mode == "reset":
            self.settings = registry.reset_all()
            self._settings_dialog_apply_refresh("Reset settings to factory defaults")
            return
        if mode != "ok":
            self._set_status("Settings cancelled")
            return

        updated = self.settings
        for key, value in collected.items():
            updated = registry.set_value(updated, key, value)
        self.settings = updated
        if ai_value is not None:
            save_ai_enabled(ai_value)
            self._sync_ai_enabled_menu(ai_value)
        if ext_master_value is not None:
            from quill.core.ai.external_engine import (
                configure_engine,
                set_external_engines_enabled,
            )

            set_external_engines_enabled(ext_master_value)
            if ext_engine_spec is not None and ext_engine_spec[0].strip():
                try:
                    configure_engine(
                        ext_engine_spec[0],
                        ext_engine_spec[1],
                        enabled=ext_engine_spec[2],
                    )
                except ValueError as error:
                    self._set_status(str(error))
        self._settings_dialog_apply_refresh("Updated settings")

    def open_ai_preferences(self) -> None:
        dialog = AssistantConnectionDialog(self.frame)
        if dialog.show_modal():
            self._set_ai_menu_status_badge(
                dialog.last_verification_ok,
                dialog.last_verification_message,
            )
            detail = self._compact_ai_status_detail(
                self._plain_language_ai_status_detail(dialog.last_verification_message)
            )
            if dialog.last_verification_ok:
                self._set_status(f"Updated AI connection settings. Ready. {detail}")
            else:
                self._set_status(f"Updated AI connection settings. Needs attention. {detail}")
        else:
            self._set_status("AI connection settings cancelled")

    def _set_ai_menu_status_badge(
        self, ready: bool | None, detail: str, badge: str | None = None
    ) -> None:
        if badge is not None:
            label = f"AI Status: {badge}"
        elif ready is True:
            label = "AI Status: Ready"
        elif ready is False:
            label = "AI Status: Needs attention"
        else:
            label = "AI Status: Not checked"

        menu_bar = self.frame.GetMenuBar()
        if menu_bar is None:
            return
        if not self._menu_updates_allowed():
            self._request_menu_refresh()
            return
        item = menu_bar.FindItemById(self._id_ai_status_badge)
        if item is not None:
            item.SetItemLabel(label)
            item.SetHelp(detail)
        detail_item = menu_bar.FindItemById(self._id_ai_status_detail)
        if detail_item is not None:
            compact = self._compact_ai_status_detail(detail, max_length=72)
            detail_item.SetItemLabel(f"AI Detail: {compact}")
            detail_item.SetHelp(detail)

    def _compact_ai_status_detail(self, detail: str, *, max_length: int = 96) -> str:
        compact = " ".join((detail or "Not checked").split())
        if len(compact) <= max_length:
            return compact
        return compact[: max_length - 3].rstrip() + "..."

    def _plain_language_ai_status_detail(self, detail: str) -> str:
        text = (detail or "").strip()
        lowered = text.lower()
        if not text:
            return "AI connection has not been checked yet."
        if "access denied" in lowered or "lacks permission" in lowered:
            return (
                "Connected, but this key lacks permission for the model or region. "
                "Check the provider's model access, billing, or quota."
            )
        if "authentication failed" in lowered or "401" in lowered:
            return "Authentication failed. Check your API key and try again."
        if "could not be unlocked" in lowered or "could not be read" in lowered:
            return (
                "Your saved API key could not be unlocked on this device. "
                "Open AI Connection and enter the key again."
            )
        if "warming up" in lowered:
            return "The AI provider is warming up. Try again in a moment."
        if "not running" in lowered:
            return "The local AI server is not running. Start Ollama and try again."
        if "rate limited" in lowered:
            return "Rate limited by the AI provider. Wait a moment and try again."
        if "timed out" in lowered:
            return "Connection timed out. Check your internet or host URL and try again."
        if "could not reach" in lowered or "failed to reach" in lowered:
            return "Could not reach the AI endpoint. Check the host URL and network connection."
        if "no models" in lowered:
            return "Connected, but no models were returned by the endpoint."
        if "verified" in lowered:
            return "Connection verified successfully."
        return text

    def _apply_announcement_trace_setting(self) -> None:
        trace_enabled = bool(self.settings.announcement_trace_enabled)
        if trace_enabled:
            trace_path = app_data_dir() / "diagnostics" / "announcement-trace.log"
            set_transcript_path(trace_path)
            enable_transcript_capture(True)
            return
        enable_transcript_capture(False)
        set_transcript_path(None)

    def _announce_backend_state_on_startup(self) -> None:
        state = self._announcement_engine.state()
        if state.requested_backend == "prism" and state.active_backend != "prism":
            self._record_notification(
                "Prism backend requested but unavailable; using status bar announcements.",
                "accessibility",
            )

    def _sync_announcement_backend_menu_state(self) -> None:
        if not self._menu_updates_allowed():
            self._request_menu_refresh()
            return
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is None:
            return
        requested = self.settings.announcement_backend
        item = menu_bar.FindItemById(self._id_announcement_backend_auto)
        if item is not None:
            item.Check(requested == "auto")
        item = menu_bar.FindItemById(self._id_announcement_backend_prism)
        if item is not None:
            item.Check(requested == "prism")
        item = menu_bar.FindItemById(self._id_announcement_backend_status_only)
        if item is not None:
            item.Check(requested == "status_only")

    def set_announcement_backend(self, requested_backend: str) -> None:
        state = self._announcement_engine.configure(requested_backend)
        self._announcement_error_reported = ""
        self.settings.announcement_backend = state.requested_backend
        save_settings(self.settings)
        self._sync_announcement_backend_menu_state()
        if state.active_backend == "prism":
            self._set_status(f"Announcement backend set to Prism ({state.backend_name})")
            return
        if state.requested_backend == "prism":
            self._set_status("Prism unavailable. Using status bar announcements.")
            return
        self._set_status("Announcement backend set to status bar")

    def choose_announcement_backend(self) -> None:
        wx = self._wx
        backend_order = ["auto", "prism", "status_only"]
        choices = [self._ANNOUNCEMENT_BACKEND_LABELS[item] for item in backend_order]
        current = self.settings.announcement_backend
        current_index = backend_order.index(current) if current in backend_order else 0
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose how Quill routes spoken announcements:",
            "Announcement Backend",
            choices=choices,
        ) as dialog:
            dialog.SetSelection(current_index)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Announcement Backend") != wx.ID_OK:
                self._set_status("Announcement backend selection cancelled")
                return
            selected = dialog.GetSelection()
        if selected < 0 or selected >= len(backend_order):
            return
        self.set_announcement_backend(backend_order[selected])

    def toggle_announcement_trace_capture(self) -> None:
        """Open Settings at the Accessibility tab where announcement trace can be toggled."""
        self.open_general_preferences()
        self._set_status("Announcement trace setting is in Settings > Accessibility")

    def toggle_sound(self, enabled: bool | None = None) -> None:
        from quill.core.settings import save_settings
        from quill.core.sound_events import SoundEvent
        from quill.ui import sound_manager

        current = bool(getattr(self.settings, "sound_enabled", True))
        if enabled is None:
            enabled = not current
        if not enabled:
            sound_manager.post_sound(SoundEvent.SOUND_OFF)
        self.settings.sound_enabled = enabled
        save_settings(self.settings)
        sound_manager.on_settings_changed(self.settings)
        if enabled:
            sound_manager.post_sound(SoundEvent.SOUND_ON)
        state = "on" if enabled else "off"
        self._announce(f"Sound notifications {state}")
        self._set_status(f"Sound notifications {state}")

    def open_sound_events_dialog(self) -> None:
        from quill.core.settings import save_settings
        from quill.ui import sound_manager
        from quill.ui.sound_events_dialog import SoundEventsDialog

        disabled_str = str(getattr(self.settings, "sound_events_disabled", ""))
        disabled = frozenset(e.strip() for e in disabled_str.split(",") if e.strip())
        loaded = sound_manager.get_loaded_events()
        dialog = SoundEventsDialog(self.frame, disabled, loaded_events=loaded or None)
        result = self._show_modal_dialog(dialog, "Sound Events")
        if result == self._wx.ID_OK:
            self.settings.sound_events_disabled = dialog.get_disabled()
            save_settings(self.settings)
            sound_manager.on_settings_changed(self.settings)

    def _set_keyboard_pack(self, pack_name: str) -> None:
        self.settings.keyboard_pack = pack_name
        save_settings(self.settings)

    def _mark_keyboard_pack_custom(self) -> None:
        if self.settings.keyboard_pack == KEYBOARD_PACK_CUSTOM:
            return
        self._set_keyboard_pack(KEYBOARD_PACK_CUSTOM)

    def apply_keyboard_pack(self, pack_name: str) -> None:
        if pack_name == KEYBOARD_PACK_CUSTOM:
            self._set_status("Custom layouts are created from manual keymap edits")
            return
        self.keymap = build_keymap_for_pack(pack_name)
        save_keymap(self.keymap)
        self._set_keyboard_pack(pack_name)
        self._reload_shortcuts_from_keymap()
        self._set_status(f"Keyboard pack changed to {pack_name}")

    def export_keymap_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Export keymap",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Export keymap") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        export_keymap(target, self.keymap)
        self._set_status(f"Exported keymap to {target.name}")

    def open_keymap_editor(self) -> None:
        wx = self._wx
        quick_nav_actions: list[tuple[str, str]] = [
            ("QUILL Quick Nav: Heading", "quill.quick_nav.heading"),
            ("QUILL Quick Nav: Link", "quill.quick_nav.link"),
            ("QUILL Quick Nav: List", "quill.quick_nav.list"),
            ("QUILL Quick Nav: List Item", "quill.quick_nav.list_item"),
            ("QUILL Quick Nav: Table", "quill.quick_nav.table"),
            ("QUILL Quick Nav: Block Quote", "quill.quick_nav.block_quote"),
            ("QUILL Quick Nav: Bookmark", "quill.quick_nav.bookmark"),
            ("QUILL Quick Nav: Code Block", "quill.quick_nav.code_block"),
            ("QUILL Quick Nav: Table of Contents", "quill.quick_nav.table_of_contents"),
            ("QUILL Quick Nav: Paragraph", "quill.quick_nav.paragraph"),
            ("QUILL Quick Nav: Sentence", "quill.quick_nav.sentence"),
            ("QUILL Quick Nav: Block", "quill.quick_nav.block"),
            ("QUILL Quick Nav: Skip Forward Past Container", "quill.quick_nav.skip_forward"),
            ("QUILL Quick Nav: Skip Backward Past Container", "quill.quick_nav.skip_backward"),
        ]
        entries: list[tuple[str, str]] = [
            (command.title, command.id)
            for command in self.commands.list()
            if not command.id.startswith("tools.keymap_editor")
        ]
        entries.extend(quick_nav_actions)
        if not entries:
            self._set_status("No commands available for keymap editing")
            return

        dialog = wx.Dialog(self.frame, title="Keymap Editor", size=(640, 480))
        # Parent every control directly to the dialog and lay them out in a
        # single sizer (issue #119). The previous build parented controls to an
        # inner wx.Panel but added dialog.CreateButtonSizer()'s buttons (children
        # of the dialog) to the panel's sizer. That parent/sizer mismatch
        # mislaid the OK button (it could not dismiss the dialog) and collapsed
        # the command list. This matches the working _choose_searchable_option.
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Select a command and choose Edit to change its keybinding. "
                    "The current key (or 'Unassigned') is shown for each command. "
                    "Choose OK to return to the editor."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        listbox = wx.ListBox(dialog, style=wx.LB_SINGLE)
        root.Add(listbox, 1, wx.ALL | wx.EXPAND, 8)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        edit_button = wx.Button(dialog, label="&Edit Keybinding...")
        controls.Add(edit_button, 0, wx.RIGHT, 8)
        root.Add(controls, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        buttons = dialog.CreateButtonSizer(wx.OK)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        # This editor has only an OK button, so Escape closes via OK rather than
        # a non-existent Cancel button; SetEscapeId needs an id that a real
        # button carries or Escape is inert (a keyboard trap, #124).
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        dialog.SetSizer(root)

        def refresh_list(keep: int | None = None) -> None:
            labels = [
                f"{title} — {self._binding_for(command_id) or 'Unassigned'}"
                for title, command_id in entries
            ]
            listbox.Set(labels)
            if keep is not None and 0 <= keep < len(entries):
                listbox.SetSelection(keep)

        def edit_selected(_event: object = None) -> None:
            selected = listbox.GetSelection()
            if selected == wx.NOT_FOUND:
                self._set_status("Select a command to edit")
                return
            title, command_id = entries[selected]
            current_binding = self._binding_for(command_id) or ""
            with wx.TextEntryDialog(
                dialog,
                f"Enter new keybinding for {title} (example: Ctrl+Shift+K):",
                "Edit Keybinding",
                value=current_binding,
            ) as binding_dialog:
                if self._show_modal_dialog(binding_dialog, "Edit Keybinding") != wx.ID_OK:
                    return
                new_binding = binding_dialog.GetValue().strip()
            if self._apply_keymap_binding(command_id, new_binding):
                refresh_list(keep=selected)

        edit_button.Bind(wx.EVT_BUTTON, edit_selected)
        listbox.Bind(wx.EVT_LISTBOX_DCLICK, edit_selected)
        refresh_list(keep=0)

        self._show_modal_dialog(dialog, "Keymap Editor")
        dialog.Destroy()

    def _apply_keymap_binding(self, command_id: str, new_binding: str) -> bool:
        """Validate and persist a new keybinding. Returns True when applied.

        Shared by the Keymap Editor dialog so a single edit returns to the
        command list (issue #117) rather than dismissing the editor entirely.
        """
        wx = self._wx
        if not new_binding:
            self._show_message_box(
                "Keybinding cannot be blank.",
                "Keymap Editor",
                wx.ICON_ERROR | wx.OK,
            )
            return False
        if self._parse_keybinding(new_binding) is None:
            self._show_message_box(
                "Keybinding format is invalid.",
                "Keymap Editor",
                wx.ICON_ERROR | wx.OK,
            )
            return False
        if command_id.startswith("quill.quick_nav."):
            normalized = new_binding.strip().upper()
            quick_nav_valid = (len(normalized) == 1) or (normalized == "TAB")
            if not quick_nav_valid:
                self._show_message_box(
                    "QUILL Quick Nav bindings must be a single key or TAB.",
                    "Keymap Editor",
                    wx.ICON_ERROR | wx.OK,
                )
                return False
        conflict = find_keymap_conflict(self.keymap, command_id, new_binding)
        if conflict:
            self._show_message_box(
                f'Binding conflicts with "{conflict}". Choose a different keybinding.',
                "Keymap Editor",
                wx.ICON_WARNING | wx.OK,
            )
            self._set_status("Keymap edit cancelled")
            return False
        self.keymap[command_id] = new_binding
        save_keymap(self.keymap)
        self._mark_keyboard_pack_custom()
        self._reload_shortcuts_from_keymap()
        self._set_status(f"Updated keybinding for {command_id}")
        return True

    def open_status_bar_settings(self) -> None:
        wx = self._wx
        item_order = list(self.settings.status_bar_order)
        hidden = set(self.settings.status_bar_hidden)
        dialog = wx.Dialog(self.frame, title="Status Bar Layout", size=(560, 420))
        # Parent every control directly to the dialog and lay them out in one
        # sizer (issue #119 pattern). The previous build parented controls to an
        # inner wx.Panel but added dialog.CreateButtonSizer()'s buttons (children
        # of the dialog) to the panel's sizer. That parent/sizer mismatch
        # mislaid the OK/Cancel buttons, and because SetEscapeId(wx.ID_CANCEL)
        # needs a realized Cancel button, neither the buttons nor Escape could
        # dismiss the dialog. This matches the working Keymap Editor and search
        # dialogs.
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Choose visible status items and order. "
                    "Use Move Up/Down, or right-click for Move Left/Right and Hide/Show."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )

        def state_label(item: str, shown: bool) -> str:
            # Spell out the visibility in the item text so it is obvious without
            # relying solely on the checkbox state (which some screen readers
            # announce only on focus, not at a glance).
            base = self._STATUS_BAR_LABELS.get(item, item)
            return f"{base} (shown)" if shown else f"{base} (hidden)"

        chooser = wx.CheckListBox(  # A11Y-SR-1-OK: state in label text; pending CheckBox conversion
            dialog,
            choices=[state_label(item, item not in hidden) for item in item_order],
        )
        for index, item in enumerate(item_order):
            chooser.Check(index, item not in hidden)
        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)

        def refresh_label(index: int) -> None:
            if 0 <= index < len(item_order):
                chooser.SetString(index, state_label(item_order[index], chooser.IsChecked(index)))

        def announce_state(index: int) -> None:
            if not (0 <= index < len(item_order)):
                return
            base = self._STATUS_BAR_LABELS.get(item_order[index], item_order[index])
            self._set_status(f"{base} {'shown' if chooser.IsChecked(index) else 'hidden'}")

        def toggle_item(index: int) -> None:
            # Programmatic toggle (context menu) — Check() does not fire
            # EVT_CHECKLISTBOX, so refresh the label and announce here.
            if not (0 <= index < len(item_order)):
                return
            chooser.Check(index, not chooser.IsChecked(index))
            refresh_label(index)
            announce_state(index)

        def on_toggle(event: object) -> None:
            # Fired by the native checkbox toggle, including the Spacebar.
            index = event.GetInt() if hasattr(event, "GetInt") else chooser.GetSelection()
            refresh_label(index)
            announce_state(index)

        chooser.Bind(wx.EVT_CHECKLISTBOX, on_toggle)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        move_up = wx.Button(dialog, label="Move Up")
        move_down = wx.Button(dialog, label="Move Down")
        restore_defaults = wx.Button(dialog, label="Restore Defaults")
        controls.Add(move_up, 0, wx.RIGHT, 8)
        controls.Add(move_down, 0, wx.RIGHT, 8)
        controls.Add(restore_defaults, 0, wx.RIGHT, 8)
        root.Add(controls, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizer(root)
        restore_defaults_selected = False

        def swap_items(first: int, second: int) -> None:
            if first < 0 or second < 0:
                return
            if first >= len(item_order) or second >= len(item_order):
                return
            item_order[first], item_order[second] = item_order[second], item_order[first]
            first_checked = chooser.IsChecked(first)
            second_checked = chooser.IsChecked(second)
            chooser.Check(first, second_checked)
            chooser.Check(second, first_checked)
            chooser.SetString(first, state_label(item_order[first], second_checked))
            chooser.SetString(second, state_label(item_order[second], first_checked))
            chooser.SetSelection(second)

        def move_selected(offset: int) -> None:
            selected = chooser.GetSelection()
            if selected == wx.NOT_FOUND:
                return
            target = selected + offset
            if target < 0 or target >= len(item_order):
                return
            swap_items(selected, target)

        def on_move_up(_event: object) -> None:
            move_selected(-1)

        def on_move_down(_event: object) -> None:
            move_selected(1)

        def on_context_menu(event: object) -> None:
            selected = chooser.GetSelection()
            if selected == wx.NOT_FOUND:
                return
            menu = wx.Menu()
            move_left_id = wx.NewIdRef()
            move_right_id = wx.NewIdRef()
            toggle_id = wx.NewIdRef()
            menu.Append(move_left_id, "Move Left")
            menu.Append(move_right_id, "Move Right")
            menu.AppendSeparator()
            toggle_label = "Hide Item" if chooser.IsChecked(selected) else "Show Item"
            menu.Append(toggle_id, toggle_label)
            menu.Bind(wx.EVT_MENU, lambda _e: move_selected(-1), id=move_left_id)
            menu.Bind(wx.EVT_MENU, lambda _e: move_selected(1), id=move_right_id)
            menu.Bind(
                wx.EVT_MENU,
                lambda _e: toggle_item(selected),
                id=toggle_id,
            )
            self._popup_context_menu(chooser, menu, event)

        def on_restore_defaults(_event: object) -> None:
            nonlocal restore_defaults_selected
            restore_defaults_selected = True
            self._set_status("Status bar defaults selected")

        move_up.Bind(wx.EVT_BUTTON, on_move_up)
        move_down.Bind(wx.EVT_BUTTON, on_move_down)
        restore_defaults.Bind(wx.EVT_BUTTON, on_restore_defaults)
        chooser.Bind(wx.EVT_CONTEXT_MENU, on_context_menu)

        if self._show_modal_dialog(dialog, "Status Bar Layout") != wx.ID_OK:
            return
        if restore_defaults_selected:
            self._restore_default_statusbar_layout()
        else:
            self.settings.status_bar_order = list(item_order)
            self.settings.status_bar_hidden = [
                item for index, item in enumerate(item_order) if not chooser.IsChecked(index)
            ]
        save_settings(self.settings)
        self._apply_statusbar_layout()
        self._set_status("Status bar layout updated")

    def open_share_export_dialog(self) -> None:
        """SHARE-1: Export and back up settings, features, and customizations.

        Profile mode produces a privacy-clean package that never includes
        machine-specific paths or secrets; backup mode keeps everything for the
        person's own use.
        """
        wx = self._wx
        offers = gather_export_offers(self.settings, self.features)
        if not offers:
            self._set_status("Nothing available to export")
            return
        dialog = wx.Dialog(self.frame, title="Export and Back Up", size=(560, 460))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Share a profile to give someone your setup without personal "
                    "paths or secrets, or back up everything for yourself."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        kind_choice = wx.RadioBox(
            dialog,
            label="What to create",
            choices=["Share a profile (privacy-clean)", "Back up everything"],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        root.Add(kind_choice, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(wx.StaticText(dialog, label="&Name:"), 0, wx.LEFT | wx.RIGHT, 8)
        name_field = wx.TextCtrl(dialog, value="My QUILL setup")
        root.Add(name_field, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(dialog, label="Include these sections:"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        chooser = wx.CheckListBox(  # A11Y-SR-1-OK: export picker; pending CheckBox conversion
            dialog,
            choices=[f"{offer.title} - {offer.summary}" for offer in offers],
        )
        for index in range(len(offers)):
            chooser.Check(index, True)
        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)
        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizerAndFit(root)

        def sync_private(_event: object = None) -> None:
            profile_mode = kind_choice.GetSelection() == 0
            for index, offer in enumerate(offers):
                if offer.private:
                    if profile_mode:
                        chooser.Check(index, False)
                    chooser.Enable(index, not profile_mode)

        kind_choice.Bind(wx.EVT_RADIOBOX, sync_private)
        sync_private()

        if self._show_modal_dialog(dialog, "Export and Back Up") != wx.ID_OK:
            self._set_status("Export cancelled")
            return
        profile_mode = kind_choice.GetSelection() == 0
        kind = KIND_PROFILE if profile_mode else KIND_BACKUP
        selected_ids = [
            offers[index].id for index in range(len(offers)) if chooser.IsChecked(index)
        ]
        name = name_field.GetValue().strip() or "My QUILL setup"
        if not selected_ids:
            self._set_status("Select at least one section to export")
            return
        try:
            document = build_export_document(
                kind=kind,
                name=name,
                source_version=__version__,
                selected_ids=selected_ids,
                offers=offers,
            )
        except (ValueError, PackageError) as exc:
            self._show_error_with_hint(
                str(exc),
                "Export",
                "Check that all selected sections are valid and that QUILL has permission "
                "to read the source data. If the error persists, try exporting fewer sections.",
            )
            self._set_status("Export failed")
            return
        extension = extension_for_kind(kind)
        label = "profile" if profile_mode else "backup"
        wildcard = f"QUILL {label} (*{extension})|*{extension}|All files (*.*)|*.*"
        with wx.FileDialog(
            self.frame,
            "Save export",
            wildcard=wildcard,
            defaultFile=f"{name}{extension}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if self._show_modal_dialog(file_dialog, "Save export") != wx.ID_OK:
                self._set_status("Export cancelled")
                return
            target = Path(file_dialog.GetPath())
        try:
            write_export(document, target)
        except OSError as exc:
            self._show_error_with_hint(
                str(exc),
                "Export",
                "Verify the destination folder is writable and that no other application "
                "has the file open. Check available disk space.",
            )
            self._set_status("Export failed")
            return
        self._set_status(f"Saved {label} with {len(selected_ids)} section(s) to {target.name}")

    def open_share_import_dialog(self) -> None:
        """SHARE-2: Import a profile or restore a backup, with preview and undo.

        Feature changes are snapshotted and rolled back automatically if any
        section fails to apply, so a bad file never leaves the app half-changed.
        """
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Open profile or backup",
            wildcard=(
                "QUILL profile or backup (*.quillprofile;*.quillbackup)"
                "|*.quillprofile;*.quillbackup|All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as file_dialog:
            if self._show_modal_dialog(file_dialog, "Open profile or backup") != wx.ID_OK:
                self._set_status("Import cancelled")
                return
            source = Path(file_dialog.GetPath())
        try:
            package = read_import(source)
        except (PackageError, OSError, ValueError) as exc:
            self._show_error_with_hint(
                str(exc),
                "Import",
                "Check that the file is a valid QUILL profile or backup (*.quillprofile or "
                "*.quillbackup). If the file came from a different QUILL version, export a "
                "fresh copy and try again.",
            )
            self._set_status("Import failed")
            return
        sections = importable_sections(package)
        if not sections:
            self._show_message_box(
                "This file has no sections QUILL can import.",
                "Import",
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("Nothing to import")
            return
        dialog = wx.Dialog(self.frame, title="Import and Restore", size=(580, 480))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label="Review what this file contains, then choose what to apply.",
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        preview = wx.TextCtrl(
            dialog,
            value=package_summary(package),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        root.Add(preview, 1, wx.ALL | wx.EXPAND, 8)
        root.Add(wx.StaticText(dialog, label="Apply these sections:"), 0, wx.LEFT | wx.RIGHT, 8)
        chooser = wx.CheckListBox(  # A11Y-SR-1-OK: import picker; pending CheckBox conversion
            dialog,
            choices=[f"{title} - {summary}" for _id, title, summary in sections],
        )
        for index in range(len(sections)):
            chooser.Check(index, True)
        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)
        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizerAndFit(root)
        if self._show_modal_dialog(dialog, "Import and Restore") != wx.ID_OK:
            self._set_status("Import cancelled")
            return
        selected_ids = [
            sections[index][0] for index in range(len(sections)) if chooser.IsChecked(index)
        ]
        if not selected_ids:
            self._set_status("Select at least one section to import")
            return
        try:
            outcome = apply_import(package, selected_ids, self.settings, self.features)
        except (PackageError, ValueError) as exc:
            self._show_error_with_hint(
                str(exc),
                "Import",
                "The import was rolled back; no changes were applied. "
                "Try importing individual sections one at a time to identify "
                "the problematic entry.",
            )
            self._set_status("Import failed; no changes were applied")
            return
        applied = len(outcome.applied)
        if outcome.settings is not None:
            self.settings = outcome.settings
            self._settings_dialog_apply_refresh(f"Imported {applied} section(s)")
        else:
            self._build_menu()
            self._set_status(f"Imported {applied} section(s)")
        notes = list(package.warnings) + list(outcome.warnings)
        if notes:
            self._show_message_box("\n".join(notes), "Import notes", wx.ICON_INFORMATION | wx.OK)

    def import_keymap_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Import keymap",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Import keymap") != wx.ID_OK:
                return
            source = Path(dialog.GetPath())
        self.keymap = import_keymap(source)
        self._mark_keyboard_pack_custom()
        self._reload_shortcuts_from_keymap()
        self._set_status(f"Imported keymap from {source.name}")

    def export_keyboard_pack_file(self) -> None:
        wx = self._wx
        pack_name = self.settings.keyboard_pack
        pack_desc = keyboard_pack_description(pack_name)

        # Collect name and description via a simple dialog before the file picker.
        dlg = wx.Dialog(self.frame, title="Export Keyboard Pack", size=(480, 220))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(dlg, label="Pack &name:"), 0, wx.ALL, 8)
        name_ctrl = wx.TextCtrl(dlg, value=pack_name)
        root.Add(name_ctrl, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(dlg, label="&Description (optional):"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8
        )
        desc_ctrl = wx.TextCtrl(dlg, value=pack_desc if pack_desc else "")
        root.Add(desc_ctrl, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        buttons = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dlg, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dlg.SetSizer(root)

        if self._show_modal_dialog(dlg, "Export Keyboard Pack") != wx.ID_OK:
            return
        name = name_ctrl.GetValue().strip() or pack_name
        description = desc_ctrl.GetValue().strip()

        default_file = name.replace(" ", "-").lower() + KQP_EXTENSION
        with wx.FileDialog(
            self.frame,
            "Export keyboard pack",
            defaultFile=default_file,
            wildcard=self.KQP_WILDCARD,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dlg:
            if self._show_modal_dialog(file_dlg, "Export keyboard pack") != wx.ID_OK:
                return
            target = Path(file_dlg.GetPath())
        if target.suffix.lower() != KQP_EXTENSION:
            target = target.with_suffix(KQP_EXTENSION)
        export_keyboard_pack(target, self.keymap, name=name, description=description)
        self._set_status(f"Exported keyboard pack to {target.name}")

    def import_keyboard_pack_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Import keyboard pack",
            wildcard=self.KQP_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Import keyboard pack") != wx.ID_OK:
                return
            source = Path(dialog.GetPath())
        try:
            name, description, merged = import_keyboard_pack(source)
        except ValueError as exc:
            self._show_message_box(str(exc), "Import Failed", wx.ICON_ERROR | wx.OK)
            return
        self.keymap = merged
        self._mark_keyboard_pack_custom()
        self._reload_shortcuts_from_keymap()
        summary = f"Imported keyboard pack: {name}"
        if description:
            summary += f". {description}"
        self._set_status(summary)
        self._announce(summary)

    def reset_keymap_defaults(self) -> None:
        wx = self._wx
        result = self._show_message_box(
            "Reset all keybindings to defaults?",
            "Reset Keymap",
            wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
        )
        if result != wx.YES:
            self._set_status("Reset keymap cancelled")
            return
        self.keymap = reset_keymap()
        self._set_keyboard_pack(KEYBOARD_PACK_DEFAULT)
        self._reload_shortcuts_from_keymap()
        self._set_status("Reset keymap to defaults")

    def _reload_shortcuts_from_keymap(self) -> None:
        self.commands = CommandRegistry()
        self._build_commands()
        self._refresh_voice_command_aliases()
        self._build_menu()
        self._apply_accelerators()
        self._reload_global_hotkeys()

    def open_welcome_guide(self) -> None:
        self._create_document_tab(
            Document(text=build_welcome_guide(self.features), path=None, modified=False),
            select=True,
        )
        self._location_ring = LocationRing()
        self._location_ring.record(0)
        self._refresh_title()
        self._set_status("Opened welcome guide")

    def open_keyboard_reference(self) -> None:
        """Open an HTML table of every defined keyboard shortcut in the browser.

        Similar to Reaper's keyboard shortcut export: because QUILL is highly
        configurable, this renders the live keymap as a self-contained, screen
        reader-friendly HTML table that opens in the default browser.
        """
        html = build_keyboard_shortcut_html(self.commands.list(), self.features)
        target_dir = app_data_dir() / "keyboard-shortcuts"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / "keyboard-shortcuts.html"
            temp_path = target_path.with_suffix(".tmp")
            temp_path.write_text(html, encoding="utf-8")
            os.replace(temp_path, target_path)
        except OSError as error:
            self._set_status(f"Could not write keyboard reference: {error}")
            return
        if webbrowser.open(target_path.as_uri()):
            self._set_status("Opened keyboard reference in browser")
        else:
            self._set_status(f"Keyboard reference saved to {target_path}")

    def open_user_guide(self, *, start_anchor: str | None = None) -> None:
        """Open the bundled user guide as rendered HTML in the system browser.

        Searches a small set of candidate locations so the command works in
        the dev tree, an installed package, and a packaged Windows build.
        Falls back to the in-app welcome guide if the markdown file cannot
        be located on disk.
        """
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "docs" / "userguide.md",
            Path(__file__).resolve().parent.parent / "docs" / "userguide.md",
            Path.cwd() / "docs" / "userguide.md",
        ]
        guide_path: Path | None = None
        for candidate in candidates:
            try:
                if candidate.is_file():
                    guide_path = candidate
                    break
            except OSError:
                continue
        if guide_path is None:
            self.open_welcome_guide()
            self._set_status("User guide file not found; opened welcome guide instead.")
            return
        try:
            text = guide_path.read_text(encoding="utf-8")
        except OSError as error:
            self._set_status(f"Could not read user guide: {error}")
            self.open_welcome_guide()
            return
        html_content = render_preview_html(
            "Quill User Guide", text, "markdown", start_anchor=start_anchor
        )
        target_dir = app_data_dir() / "user-guide"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / "userguide.html"
            temp_path = target_path.with_suffix(".tmp")
            temp_path.write_text(html_content, encoding="utf-8")
            os.replace(temp_path, target_path)
        except OSError as error:
            self._set_status(f"Could not write user guide: {error}")
            return
        if webbrowser.open(target_path.as_uri()):
            self._set_status("Opened user guide in browser")
        else:
            self._set_status(f"User guide saved to {target_path}")

    def open_third_party_notices(self) -> None:
        project_root = self._project_root_path()
        pyproject_path = self._pyproject_path()
        notices = render_full_third_party_notices(pyproject_path, project_root)
        self._create_document_tab(
            Document(text=notices, path=None, modified=False),
            select=True,
        )
        self._location_ring = LocationRing()
        self._location_ring.record(0)
        self._refresh_title()
        self._set_status("Opened third-party notices")

    # Org links shown in the About dialog.
    _ABOUT_LINKS: tuple[tuple[str, str], ...] = (
        ("Community Access", "https://community-access.org"),
        ("Blind Information Technology Solutions (BITS)", "https://bits-acb.org"),
        ("Techopolis", "https://techopolis.app"),
        ("GLOW (Community Access)", "https://letitglow.app"),
    )

    # Contributor / project profiles on GitHub.
    _ABOUT_GITHUB_LINKS: tuple[tuple[str, str], ...] = (
        ("QUILL on GitHub", "https://github.com/Community-Access/quill"),
        ("Community Access on GitHub", "https://github.com/Community-Access"),
        ("Taylor Arndt on GitHub", "https://github.com/taylorarndt"),
        ("Michael Doise on GitHub", "https://github.com/mikedoise"),
        ("Becky K on GitHub", "https://github.com/BeckyK102125"),
        ("Doug Langley on GitHub", "https://github.com/douglangley"),
        ("Kelly Ford on GitHub", "https://github.com/kellylford"),
        (
            "wx-accessible-webview on GitHub",
            "https://github.com/Community-Access/wx-accessible-webview",
        ),
    )

    def _project_root_path(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent

    def _pyproject_path(self) -> Path:
        return self._project_root_path() / "pyproject.toml"

    def _about_markdown(self) -> str:
        def md_links(links: tuple[tuple[str, str], ...]) -> str:
            return "\n".join(f"- [{name}]({url})" for name, url in links)

        from quill.core.contributors import contributor_bullet_list

        pyproject_path = self._pyproject_path()
        dependency_rows = build_dependency_notices(pyproject_path)
        bundled_rows = bundled_component_notices()
        dependency_table = render_dependency_notice_table(dependency_rows)
        bundled_table = render_bundled_component_table(bundled_rows)
        try:
            from quill.core.glow import glow_engine_version_summary

            glow_summary = glow_engine_version_summary()
        except Exception:
            glow_summary = "GLOW engine: unknown"
        return (
            f"# Quill {__version__} Beta\n\n"
            f"Quill {__version__} Beta is a screen-reader-first writing and document environment "
            "for Windows and Mac from Blind Information Technology Solutions (BITS) "
            "and Community Access.\n\n"
            "With sincere thanks to our contributors and beta testers: "
            "Techopolis, Taylor Arndt, Michael Doise, Kayla Bentas, "
            "Shane Popplestone, Doug Langley, Becky K, and Kelly Ford.\n\n"
            f"{glow_summary}\n\n"
            "## BITS Whisperer\n\n"
            "BITS Whisperer brings speech and dictation integration to Quill, arriving in "
            "phases: a speech-model manager with machine-aware recommendations, a provider "
            "center with local-first and cloud planning, readiness checks, and a download "
            "queue. Bundled Read Aloud voices (DECtalk and eSpeak NG) play immediately with "
            "no downloads; Piper and Kokoro models install through the Speech Center.\n\n"
            "## Links\n\n" + md_links(self._ABOUT_LINKS) + "\n\n"
            "## Contributors\n\n"
            "Everyone who has contributed to Quill on GitHub:\n\n"
            + contributor_bullet_list()
            + "\n\n"
            "## Project on GitHub\n\n" + md_links(self._ABOUT_GITHUB_LINKS) + "\n\n"
            "## Dependencies and attributions\n\n"
            "The tables below are generated from declared project metadata and "
            "installed package metadata. "
            "They include dependency versions, licenses, and upstream links.\n\n"
            "### Declared dependencies\n\n" + dependency_table + "\n\n"
            "### Bundled components and data sources\n\n" + bundled_table + "\n\n"
            "For full license texts and expanded notices, open "
            "**Help -> Open Third-Party Notices**.\n\n"
            "Copyright (c) Blind Information Technology Solutions (BITS) and Community Access"
        )

    def show_about_quill(self) -> None:
        from quill.core.browser_preview import render_preview_body
        from quill.ui.preview_dialog import MarkdownPreviewDialog

        body = render_preview_body(self._about_markdown(), "markdown")
        MarkdownPreviewDialog(self.frame, "About Quill", body).show()
        self._set_status("Opened About Quill")

    def show_whisperer_about_page(self) -> None:
        index = self._open_generated_tab(
            "About BITS Whisperer",
            self._build_whisperer_about_html(),
        )
        self._select_tab(index)
        if 0 <= index < len(self._document_tabs):
            self._show_side_preview_for(self._document_tabs[index])
        self._set_status("Opened About BITS Whisperer")

    def _build_whisperer_about_html(self) -> str:
        roadmap_rows = [
            (
                "Provider and feature-flag gating",
                "Mature feature flag service and staged rollout controls",
                "Phase 1",
                "Introduce opt-in experiments and safe launch toggles in Quill.",
            ),
            (
                "Audio intake and watch-folder workflows",
                "Reliable automatic job intake and background transcription flow",
                "Phase 1",
                "Apply to document/audio intake and asynchronous assistant pipelines.",
            ),
            (
                "Rich export and transformation pipeline",
                "Multiple output formats and conversion strategy patterns",
                "Phase 2",
                "Expand Quill exports and structured conversion workflows.",
            ),
            (
                "Model/provider orchestration",
                "Multi-provider manager abstraction with graceful fallback",
                "Phase 2",
                "Align with Quill AI + speech backends for reliability and control.",
            ),
            (
                "Plugin and extension surfaces",
                "Extensible plugin architecture for advanced integrations",
                "Phase 3",
                "Open controlled extension points in Quill once core stability is proven.",
            ),
        ]
        roadmap_html = "".join(
            (
                "<tr>"
                f"<td>{html.escape(capability)}</td>"
                f"<td>{html.escape(from_bw)}</td>"
                f"<td>{html.escape(phase)}</td>"
                f"<td>{html.escape(notes)}</td>"
                "</tr>"
            )
            for capability, from_bw, phase, notes in roadmap_rows
        )

        principles_rows = [
            (
                "Accessibility first",
                "Screen-reader-first design with clear headings and keyboard flow.",
            ),
            ("Offline-friendly", "Strong local capabilities before cloud dependencies."),
            ("Safe rollout", "Feature flags and staged onboarding for predictable adoption."),
            ("Transparent status", "Status pages and notifications for every async operation."),
        ]
        principles_html = "".join(
            f"<tr><th scope='row'>{html.escape(name)}</th><td>{html.escape(detail)}</td></tr>"
            for name, detail in principles_rows
        )

        return (
            "<h1 id='whisperer-about'>BITS Whisperer and Quill</h1>"
            "<p>The future is bright. BITS Whisperer patterns are being evaluated "
            "for selective adoption "
            "inside Quill to improve accessibility, reliability, and creative flow.</p>"
            "<h2 id='what-is-coming'>What Is Coming</h2>"
            "<p>Quill will progressively absorb proven ideas from BITS Whisperer "
            "in focused phases, "
            "while preserving Quill's writing-first experience.</p>"
            "<h2 id='roadmap'>Integration Roadmap</h2>"
            "<table>"
            "<caption>Planned feature pull-through from BITS Whisperer into Quill</caption>"
            "<thead><tr>"
            "<th scope='col'>Capability</th>"
            "<th scope='col'>Whisperer Source</th>"
            "<th scope='col'>Phase</th>"
            "<th scope='col'>Quill Plan</th>"
            "</tr></thead>"
            f"<tbody>{roadmap_html}</tbody>"
            "</table>"
            "<h2 id='experience-principles'>Experience Principles</h2>"
            "<table>"
            "<caption>User experience principles guiding the integration</caption>"
            "<thead><tr><th scope='col'>Principle</th>"
            "<th scope='col'>How it applies</th></tr></thead>"
            f"<tbody>{principles_html}</tbody>"
            "</table>"
            "<h2 id='next-steps'>Next Steps</h2>"
            "<ol>"
            "<li>Use Startup Wizard to configure profile, AI, and speech foundation.</li>"
            "<li>Use Status Page to check on downloads, speech, and what's turned on.</li>"
            "<li>Iterate in small, accessible milestones with clear release notes.</li>"
            "</ol>"
            "<p>It all starts with a whisper that glows and writes with a magical Quill.</p>"
        )

    def show_external_tools_dialog(self) -> None:
        wx = self._wx
        statuses = get_external_tool_statuses()
        dialog = wx.Dialog(
            self.frame,
            title="External Tools and Format Support",
            size=(860, 620),
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Quill can grow with optional external tools. Each tool below explains what "
                    "it unlocks, how Quill uses it, and how to install it safely if you want it."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        choices = [status.name for status in statuses]
        chooser = wx.ListBox(dialog, choices=choices)
        chooser.SetSelection(0 if choices else wx.NOT_FOUND)
        details = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        copy_button = wx.Button(dialog, label="Copy Install Command")
        website_button = wx.Button(dialog, label="Open Website")
        wizard_button = wx.Button(dialog, label="Open Wizard")
        close_button = wx.Button(dialog, id=wx.ID_OK, label="Close")

        touch_points = {
            "pandoc": (
                "Pandoc Conversion Wizard",
                "Document conversion into Markdown, HTML, or plain text tabs",
            ),
            "libreoffice": (
                "Future office conversion fallback",
                "Difficult legacy office imports and format repair",
            ),
            "tidy_html5": (
                "Future HTML validation",
                "Check HTML exports and authoring output before handoff",
            ),
            "pymarkdownlnt": (
                "Future Markdown validation",
                "Lint Markdown structure and style without Node.js or Java",
            ),
        }

        def selected_status() -> object | None:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND:
                return None
            return statuses[selection]

        def refresh_details() -> None:
            status = selected_status()
            if status is None:
                details.SetValue("No external tools are registered.")
                copy_button.Enable(False)
                website_button.Enable(False)
                wizard_button.Enable(False)
                return
            touch_lines = touch_points.get(status.tool_id, ())
            lines = [status.definition.description, ""]
            lines.append(f"Category: {status.definition.category}")
            if status.installed:
                lines.append(f"Status: installed via {status.source}")
                if status.path:
                    lines.append(f"Path: {status.path}")
                if status.version:
                    lines.append(f"Version: {status.version}")
            else:
                lines.append("Status: not installed yet")
                lines.append("Install command:")
                lines.append(status.definition.install_command)
            lines.extend(["", "What this unlocks in Quill:"])
            lines.extend(f"- {item}" for item in status.definition.capabilities)
            if touch_lines:
                lines.extend(["", "Suggested first touch points:"])
                lines.extend(f"- {item}" for item in touch_lines)
            if status.definition.category == "validation":
                lines.extend([
                    "",
                    "Why Quill recommends this:",
                    "- It adds validation value without pulling in Node.js or Java.",
                ])
            lines.extend(["", f"Learn more: {status.definition.website_url}"])
            details.SetValue("\n".join(lines))
            copy_button.Enable(True)
            website_button.Enable(True)
            wizard_button.Enable(status.tool_id == "pandoc")

        def copy_install_command() -> None:
            status = selected_status()
            if status is None:
                return
            if not self._copy_to_clipboard(copyable_install_command(status.tool_id)):
                self._set_status("Clipboard is unavailable")
                return
            self._set_status(f"Copied install command for {status.name}")

        def open_website() -> None:
            status = selected_status()
            if status is None:
                return
            webbrowser.open(status.definition.website_url)
            self._set_status(f"Opened website for {status.name}")

        def open_wizard() -> None:
            status = selected_status()
            if status is None or status.tool_id != "pandoc":
                return
            dialog.EndModal(wx.ID_OK)
            self.open_pandoc_wizard()

        chooser.Bind(wx.EVT_LISTBOX, lambda _e: refresh_details())
        copy_button.Bind(wx.EVT_BUTTON, lambda _e: copy_install_command())
        website_button.Bind(wx.EVT_BUTTON, lambda _e: open_website())
        wizard_button.Bind(wx.EVT_BUTTON, lambda _e: open_wizard())
        close_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))

        root.Add(chooser, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(details, 1, wx.ALL | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(copy_button, 0, wx.RIGHT, 6)
        buttons.Add(website_button, 0, wx.RIGHT, 6)
        buttons.Add(wizard_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(close_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        refresh_details()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        self._show_modal_dialog(dialog, "External Tools and Format Support")

    def open_pandoc_wizard(self) -> None:
        wx = self._wx
        status = get_external_tool_status("pandoc")
        if not status.installed:
            result = self._show_message_box(
                (
                    "Pandoc is not installed yet. Quill can guide you, but the conversion wizard "
                    "needs Pandoc first. Copy the install command now?"
                ),
                "Pandoc Conversion Wizard",
                wx.ICON_INFORMATION | wx.YES_NO | wx.NO_DEFAULT,
            )
            if result == wx.YES and self._copy_to_clipboard(copyable_install_command("pandoc")):
                self._set_status("Copied Pandoc install command")
            else:
                self._set_status("Pandoc wizard unavailable until Pandoc is installed")
            return

        request = self._prompt_pandoc_conversion_request()
        if request is None:
            self._set_status("Pandoc wizard cancelled")
            return
        source_path, output_kind = request
        self._set_status(f"Running Pandoc on {source_path.name}...")
        try:
            result = convert_document_with_pandoc(source_path, output_kind, tool_status=status)
        except (PandocUnavailableError, PandocConversionError, ValueError) as error:
            self._show_message_box(
                f"Pandoc conversion failed: {error}",
                "Pandoc Conversion Wizard",
                wx.ICON_ERROR | wx.OK,
            )
            self._set_status("Pandoc conversion failed")
            return
        document = Document(
            text=result.text,
            path=None,
            modified=False,
            source_metadata={
                "source_kind": output_kind,
                "engine": "pandoc",
                "quality_score": 100,
                "source_file": source_path.name,
                "pandoc_path": result.pandoc_path,
            },
        )
        index = self._create_document_tab(document, select=True)
        self._set_tab_page_text(index, f"Pandoc - {source_path.stem} ({output_kind})")
        self._set_status(f"Opened {source_path.name} as {output_kind} via Pandoc")

    def _prompt_pandoc_conversion_request(self) -> tuple[Path, str] | None:
        wx = self._wx
        wildcard = (
            "Pandoc-friendly files "
            "(*.docx;*.md;*.markdown;*.html;*.htm;*.epub;*.odt;*.rst;*.txt)|"
            "*.docx;*.md;*.markdown;*.html;*.htm;*.epub;*.odt;*.rst;*.txt|"
            "All files (*.*)|*.*"
        )
        dialog = wx.Dialog(self.frame, title="Pandoc Conversion Wizard", size=(760, 360))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Choose a source file and output format. Quill will convert it with Pandoc "
                    "and open the converted text in a new tab."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        source_row = wx.BoxSizer(wx.HORIZONTAL)
        source_label = wx.StaticText(dialog, label="Source file")
        source_field = wx.TextCtrl(dialog)
        browse_button = wx.Button(dialog, label="Browse...")
        source_row.Add(source_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        source_row.Add(source_field, 1, wx.RIGHT | wx.EXPAND, 8)
        source_row.Add(browse_button, 0)
        root.Add(source_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        format_row = wx.BoxSizer(wx.HORIZONTAL)
        format_label = wx.StaticText(dialog, label="Output format")
        format_choice = wx.Choice(
            dialog,
            choices=[
                "Markdown (.md)",
                "HTML (.html)",
                "Plain text (.txt)",
            ],
        )
        # SET-4: pre-select the user's default export preset where the wizard
        # offers it; pdf/docx/epub have no wizard output, so fall back to Markdown.
        _preset_to_index = {"markdown": 0, "html": 1, "text": 2}
        format_choice.SetSelection(
            _preset_to_index.get(getattr(self.settings, "default_export_preset", "html"), 0)
        )
        format_row.Add(format_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        format_row.Add(format_choice, 1, wx.EXPAND)
        root.Add(format_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        validation_text = wx.StaticText(dialog, label="")
        root.Add(validation_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        convert_button = wx.Button(dialog, id=wx.ID_OK, label="Convert and Open")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
        buttons.AddStretchSpacer(1)
        buttons.Add(convert_button, 0, wx.RIGHT, 6)
        buttons.Add(cancel_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        dialog_result: dict[str, object] = {}

        def browse_source() -> None:
            with wx.FileDialog(
                dialog,
                "Choose a source document for Pandoc",
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as file_dialog:
                if self._show_modal_dialog(file_dialog, "Pandoc Source File") == wx.ID_OK:
                    source_field.SetValue(file_dialog.GetPath())
                    validation_text.SetLabel("")

        def submit() -> None:
            raw_path = source_field.GetValue().strip()
            if not raw_path:
                validation_text.SetLabel("Choose a source file before continuing.")
                source_field.SetFocus()
                return
            candidate = Path(raw_path)
            if not candidate.exists() or not candidate.is_file():
                validation_text.SetLabel("The selected source file was not found.")
                source_field.SetFocus()
                return
            output_options = ["markdown", "html", "plain"]
            selection = format_choice.GetSelection()
            if selection < 0 or selection >= len(output_options):
                validation_text.SetLabel("Choose an output format before continuing.")
                format_choice.SetFocus()
                return
            dialog_result["source_path"] = candidate
            dialog_result["output_kind"] = output_options[selection]
            dialog.EndModal(wx.ID_OK)

        browse_button.Bind(wx.EVT_BUTTON, lambda _e: browse_source())
        convert_button.Bind(wx.EVT_BUTTON, lambda _e: submit())
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        if self._show_modal_dialog(dialog, "Pandoc Conversion Wizard") != wx.ID_OK:
            return None
        source_path = dialog_result.get("source_path")
        output_kind = dialog_result.get("output_kind")
        if not isinstance(source_path, Path) or not isinstance(output_kind, str):
            return None
        return source_path, output_kind

    def save_diagnostics_bundle(self) -> None:
        wx = self._wx
        include_paths = self._review_diagnostics_export()
        if include_paths is None:
            self._set_status("Diagnostics export cancelled")
            return
        default_name = f"quill-diagnostics-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.zip"
        with wx.FileDialog(
            self.frame,
            "Save diagnostics bundle",
            wildcard="ZIP archives (*.zip)|*.zip|All files (*.*)|*.*",
            defaultFile=default_name,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save Diagnostics") != wx.ID_OK:
                self._set_status("Diagnostics export cancelled")
                return
            target = Path(dialog.GetPath())

        detection = detect_screen_reader()
        bundle_path = write_diagnostics_bundle(
            target,
            settings=self.settings,
            keymap=self.keymap,
            notifications=self._notifications,
            current_document=self.document,
            include_file_paths=include_paths,
            extra_environment={
                "screen_reader": detection.name,
                "wx_version": self._wx.version(),
                **self._announcement_engine.diagnostics_environment(),
                "bw_rollout": self._bw_diagnostics_snapshot(),
            },
        )
        self._record_notification(f"Saved diagnostics to {bundle_path.name}", "diagnostics")
        self._set_status(f"Saved diagnostics bundle to {bundle_path.name}")

    def report_bug(self) -> None:
        if not self._feedback_hub_available():
            self._report_bug_legacy()
            return
        from feedback_hub import load_schema
        from feedback_hub.wx_dialog import FeedbackDialog

        schema_path = Path(__file__).parent.parent / "core" / "schemas" / "feedback.json"
        dlg = FeedbackDialog(
            self.frame,
            schema=load_schema(schema_path),
            app_version=__version__ or "0.0.0",
        )
        result = self._show_modal_dialog(dlg, "Report an Issue")
        dlg.Destroy()
        if result == self._wx.ID_OK:
            self._record_notification("Submitted feedback via feedback hub", "support")

    def _feedback_hub_available(self) -> bool:
        try:
            import feedback_hub  # noqa: F401
            from feedback_hub.wx_dialog import FeedbackDialog  # noqa: F401

            return True
        except ImportError:
            return False

    def _report_bug_legacy(self) -> None:
        review = self._review_bug_report()
        if review is None:
            self._set_status("Bug report cancelled")
            return
        payload, issue_url = review
        diagnostics_path = getattr(self, "_last_bug_report_diagnostics_path", None)
        clipboard_text = payload["body"]
        if isinstance(diagnostics_path, Path):
            clipboard_text = f"{clipboard_text}\n\nDiagnostics bundle path:\n{diagnostics_path}"
        self._copy_to_clipboard(clipboard_text)
        webbrowser.open(issue_url)
        self._record_notification("Opened support-hub bug report form", "support")
        if isinstance(diagnostics_path, Path):
            self._set_status(
                "Opened bug report form, copied report, and prepared diagnostics bundle path"
            )
        else:
            self._set_status("Opened bug report form and copied environment summary to clipboard")

    def _review_diagnostics_export(self) -> bool | None:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Review Diagnostics Export", size=(780, 560))
        root = wx.BoxSizer(wx.VERTICAL)
        include_paths = wx.CheckBox(dialog, label="Include plain file paths in the bundle")
        review = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        copy_button = wx.Button(dialog, label="Copy Summary")
        continue_button = wx.Button(dialog, id=wx.ID_OK, label="Continue")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")

        def refresh() -> None:
            detection = detect_screen_reader()
            review.SetValue(
                build_diagnostics_review_text(
                    settings=self.settings,
                    keymap=self.keymap,
                    notifications=self._notifications,
                    current_document=self.document,
                    include_file_paths=include_paths.GetValue(),
                    extra_environment={
                        "screen_reader": detection.name,
                        "wx_version": self._wx.version(),
                        **self._announcement_engine.diagnostics_environment(),
                        "bw_rollout": self._bw_diagnostics_snapshot(),
                    },
                )
            )

        include_paths.Bind(wx.EVT_CHECKBOX, lambda _e: refresh())
        copy_button.Bind(
            wx.EVT_BUTTON,
            lambda _e: self._copy_to_clipboard(review.GetValue()),
        )
        continue_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Review what Quill will include before writing the diagnostics zip. "
                    "Nothing leaves your machine from this step."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        root.Add(wx.StaticText(dialog, label="Logs folder"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        logs_field = wx.TextCtrl(dialog, style=wx.TE_READONLY)
        logs_field.SetValue(str(app_data_dir() / "logs"))
        root.Add(logs_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(dialog, label="Diagnostics folder"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        diagnostics_field = wx.TextCtrl(dialog, style=wx.TE_READONLY)
        diagnostics_field.SetValue(str(app_data_dir() / "diagnostics"))
        root.Add(diagnostics_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        root.Add(include_paths, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        root.Add(review, 1, wx.ALL | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(copy_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(continue_button, 0, wx.RIGHT, 6)
        buttons.Add(cancel_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        refresh()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        if self._show_modal_dialog(dialog, "Review Diagnostics Export") != wx.ID_OK:
            return None
        return include_paths.GetValue()

    def _review_bug_report(self) -> tuple[dict[str, str], str] | None:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Report a Bug", size=(860, 720))
        root = wx.BoxSizer(wx.VERTICAL)
        announcement_engine = getattr(self, "_announcement_engine", None)
        announcement_environment = (
            announcement_engine.diagnostics_environment() if announcement_engine is not None else {}
        )
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Describe the issue, then open the support form. Quill can create a "
                    "diagnostics bundle in this wizard so you can attach it to the issue."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        # Contact identity (pre-filled from settings, saved back after submit).
        _sr_detection = detect_screen_reader()
        _SR_CHOICES = [
            "Not using a screen reader",
            "JAWS",
            "NVDA",
            "Narrator",
            "VoiceOver",
            "Other",
        ]
        _detected_sr = _sr_detection.name if _sr_detection.detected else "Not using a screen reader"

        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(dialog, label="Your name (optional)")
        name_field = wx.TextCtrl(dialog)
        name_field.SetValue(getattr(self.settings, "bug_reporter_name", ""))
        email_label = wx.StaticText(dialog, label="Contact email (optional)")
        email_field = wx.TextCtrl(dialog)
        email_field.SetValue(getattr(self.settings, "bug_reporter_email", ""))
        name_row.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        name_row.Add(name_field, 1, wx.RIGHT, 16)
        name_row.Add(email_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        name_row.Add(email_field, 1)
        root.Add(name_row, 0, wx.ALL | wx.EXPAND, 8)

        sr_row = wx.BoxSizer(wx.HORIZONTAL)
        sr_label = wx.StaticText(dialog, label="Screen reader")
        sr_combo = wx.ComboBox(
            dialog,
            choices=_SR_CHOICES,
            style=wx.CB_READONLY,
        )
        sr_combo.SetStringSelection(_detected_sr)
        if sr_combo.GetSelection() == wx.NOT_FOUND:
            sr_combo.SetSelection(0)
        sr_row.Add(sr_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        sr_row.Add(sr_combo, 1)
        root.Add(sr_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        summary_label = wx.StaticText(dialog, label="Summary")
        summary_field = wx.TextCtrl(dialog)
        summary_field.SetValue(f"Bug report: {self.document.name}")
        root.Add(summary_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        root.Add(summary_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        happened_label = wx.StaticText(dialog, label="What happened")
        happened_field = wx.TextCtrl(dialog, style=wx.TE_MULTILINE)
        root.Add(happened_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        root.Add(happened_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        expected_label = wx.StaticText(dialog, label="What you expected")
        expected_field = wx.TextCtrl(dialog, style=wx.TE_MULTILINE)
        root.Add(expected_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        root.Add(expected_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        steps_label = wx.StaticText(dialog, label="Steps to reproduce")
        steps_field = wx.TextCtrl(dialog, style=wx.TE_MULTILINE)
        root.Add(steps_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        root.Add(steps_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        include_diagnostics = wx.CheckBox(
            dialog,
            label="Create diagnostics bundle in this wizard",
        )
        include_diagnostics.SetValue(True)
        include_paths = wx.CheckBox(dialog, label="Include plain file paths in diagnostics")
        include_paths.SetValue(False)
        diagnostics_path_field = wx.TextCtrl(dialog, style=wx.TE_READONLY)
        root.Add(include_diagnostics, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        root.Add(include_paths, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        root.Add(wx.StaticText(dialog, label="Diagnostics bundle path"), 0, wx.LEFT | wx.RIGHT, 8)
        root.Add(diagnostics_path_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        preview_label = wx.StaticText(dialog, label="Report preview")
        review = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        root.Add(preview_label, 0, wx.LEFT | wx.RIGHT, 8)
        root.Add(review, 1, wx.ALL | wx.EXPAND, 8)
        validation_text = wx.StaticText(dialog, label="")
        root.Add(validation_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        copy_button = wx.Button(dialog, label="Copy Preview")
        open_button = wx.Button(dialog, id=wx.ID_OK, label="Open Support Form")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
        dialog_result: dict[str, object] = {}

        def build_payload(
            diagnostics_note: str | None = None,
        ) -> tuple[dict[str, str], str]:
            chosen_sr = sr_combo.GetStringSelection() or _detected_sr
            payload = build_bug_report_payload(
                current_document=self.document,
                extra_environment={
                    "screen_reader": chosen_sr,
                    "wx_version": self._wx.version(),
                    **announcement_environment,
                },
                summary_override=summary_field.GetValue().strip(),
                happened=happened_field.GetValue().strip(),
                expected=expected_field.GetValue().strip(),
                steps=steps_field.GetValue().strip(),
                diagnostics_note=diagnostics_note,
                screen_reader_name=chosen_sr,
                reporter_name=name_field.GetValue().strip() or None,
                reporter_email=email_field.GetValue().strip() or None,
            )
            issue_url = build_support_issue_url(
                payload,
                source_app="Quill",
                version=__version__,
                platform_label=str(collect_environment_info()["platform"]),
                diagnostics_note=diagnostics_note,
            )
            return payload, issue_url

        def refresh_preview() -> None:
            diagnostics_note = None
            path_text = diagnostics_path_field.GetValue().strip()
            if path_text:
                diagnostics_note = (
                    "Diagnostics bundle created by Quill. Please attach this zip in the issue: "
                    f"{path_text}"
                )
            elif include_diagnostics.GetValue():
                diagnostics_note = (
                    "Quill will create a diagnostics bundle when you continue. Attach the "
                    "generated zip file to the issue."
                )
            payload, issue_url = build_payload(diagnostics_note=diagnostics_note)
            review.SetValue(
                f"Summary: {payload['summary']}\n\n{payload['body']}\n\nDestination:\n{issue_url}"
            )

        def confirm_preflight() -> bool:
            include_diag = include_diagnostics.GetValue()
            include_plain_paths = include_paths.GetValue() if include_diag else False
            lines = [
                "You are about to prepare this report with:",
                "",
                f"- Diagnostics bundle: {'Yes' if include_diag else 'No'}",
                (
                    f"- Plain file paths in diagnostics: {'Yes' if include_plain_paths else 'No'}"
                    if include_diag
                    else "- Plain file paths in diagnostics: N/A (diagnostics disabled)"
                ),
                "- Report summary and details shown in preview",
                "",
                "Continue?",
            ]
            with wx.MessageDialog(
                dialog,
                "\n".join(lines),
                "Report a Bug preflight",
                style=wx.OK | wx.CANCEL | wx.ICON_QUESTION,
            ) as preflight:
                return self._show_modal_dialog(preflight, "Report a Bug Preflight") == wx.ID_OK

        def submit_report() -> None:
            if not confirm_preflight():
                validation_text.SetLabel("Report submission cancelled from preflight summary.")
                return
            diagnostics_path: Path | None = None
            if include_diagnostics.GetValue():
                try:
                    diagnostics_path = self._create_diagnostics_bundle_for_report(
                        include_paths.GetValue()
                    )
                except OSError as error:
                    validation_text.SetLabel(f"Could not write diagnostics bundle: {error}")
                    return
                diagnostics_path_field.SetValue(str(diagnostics_path))
            diagnostics_note = None
            if diagnostics_path is not None:
                diagnostics_note = (
                    "Diagnostics bundle created by Quill. Please attach this zip in the issue: "
                    f"{diagnostics_path}"
                )
            elif include_diagnostics.GetValue():
                diagnostics_note = (
                    "Diagnostics bundle requested, but no local bundle path is available."
                )
            payload, issue_url = build_payload(diagnostics_note=diagnostics_note)
            dialog_result["payload"] = payload
            dialog_result["issue_url"] = issue_url
            dialog_result["diagnostics_path"] = diagnostics_path
            dialog.EndModal(wx.ID_OK)

        copy_button.Bind(wx.EVT_BUTTON, lambda _e: self._copy_to_clipboard(review.GetValue()))
        open_button.Bind(wx.EVT_BUTTON, lambda _e: submit_report())
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))

        def on_toggle_include_diagnostics() -> None:
            include_paths.Enable(include_diagnostics.GetValue())
            refresh_preview()

        include_diagnostics.Bind(wx.EVT_CHECKBOX, lambda _e: on_toggle_include_diagnostics())
        include_paths.Bind(wx.EVT_CHECKBOX, lambda _e: refresh_preview())
        summary_field.Bind(wx.EVT_TEXT, lambda _e: refresh_preview())
        happened_field.Bind(wx.EVT_TEXT, lambda _e: refresh_preview())
        expected_field.Bind(wx.EVT_TEXT, lambda _e: refresh_preview())
        steps_field.Bind(wx.EVT_TEXT, lambda _e: refresh_preview())
        name_field.Bind(wx.EVT_TEXT, lambda _e: refresh_preview())
        email_field.Bind(wx.EVT_TEXT, lambda _e: refresh_preview())
        sr_combo.Bind(wx.EVT_COMBOBOX, lambda _e: refresh_preview())
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(copy_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(open_button, 0, wx.RIGHT, 6)
        buttons.Add(cancel_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        include_paths.Enable(include_diagnostics.GetValue())
        refresh_preview()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        refresh_preview()
        # #188: ensure SR focus lands on the Summary field, not the OK button.
        self._wx.CallAfter(summary_field.SetFocus)
        if self._show_modal_dialog(dialog, "Review Bug Report") != wx.ID_OK:
            return None
        # Persist name and email so the next report is pre-filled.
        saved_name = name_field.GetValue().strip()
        saved_email = email_field.GetValue().strip()
        if hasattr(self.settings, "bug_reporter_name"):
            self.settings.bug_reporter_name = saved_name
        if hasattr(self.settings, "bug_reporter_email"):
            self.settings.bug_reporter_email = saved_email
        payload = dialog_result.get("payload")
        issue_url = dialog_result.get("issue_url")
        diagnostics_path = dialog_result.get("diagnostics_path")
        if isinstance(diagnostics_path, Path):
            self._last_bug_report_diagnostics_path = diagnostics_path
        else:
            self._last_bug_report_diagnostics_path = None
        if not isinstance(payload, dict) or not isinstance(issue_url, str):
            return None
        return payload, issue_url

    def _create_diagnostics_bundle_for_report(self, include_file_paths: bool) -> Path:
        detection = detect_screen_reader()
        announcement_engine = getattr(self, "_announcement_engine", None)
        announcement_environment = (
            announcement_engine.diagnostics_environment() if announcement_engine is not None else {}
        )
        target = (
            app_data_dir()
            / "diagnostics"
            / (f"quill-diagnostics-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.zip")
        )
        bundle_path = write_diagnostics_bundle(
            target,
            settings=self.settings,
            keymap=self.keymap,
            notifications=self._notifications,
            current_document=self.document,
            include_file_paths=include_file_paths,
            extra_environment={
                "screen_reader": detection.name,
                "wx_version": self._wx.version(),
                **announcement_environment,
                "bw_rollout": self._bw_diagnostics_snapshot(),
            },
        )
        self._record_notification(f"Saved diagnostics to {bundle_path.name}", "diagnostics")
        return bundle_path

    def show_keyboard_trap_snapshot(self) -> None:
        wx = self._wx
        snapshot = self._region_tracker.snapshot()
        report = render_snapshot(snapshot)
        self._show_message_box(report, "Keyboard Trap Audit", wx.ICON_INFORMATION | wx.OK)
        self._set_status(
            "Keyboard trap audit: potential trap detected"
            if snapshot.has_keyboard_trap
            else "Keyboard trap audit: no trap detected"
        )

    def show_accessibility_audit(self) -> None:
        wx = self._wx
        snapshot = self._region_tracker.snapshot()
        detection = detect_screen_reader()
        report = build_accessibility_audit_report(snapshot, detection.name)
        self._show_message_box(report, "Accessibility Audit", wx.ICON_INFORMATION | wx.OK)
        self._set_status("Accessibility audit complete")

    def _create_named_scratch_tab(self, title: str, text: str) -> None:
        index = self._create_document_tab(
            Document(text=text, path=None, modified=False),
            select=True,
        )
        self._set_tab_page_text(index, title)

    def _glow_scope(self) -> tuple[str, int, int, str]:
        start, end = self.editor.GetSelection()
        if start != end:
            return self.editor.GetRange(start, end), start, end, "selection"
        cursor = self.editor.GetInsertionPoint()
        text = self.editor.GetValue()
        start, end = paragraph_span(text, cursor)
        scope = self.editor.GetRange(start, end)
        if not scope.strip():
            start, end = line_span(text, cursor)
            scope = self.editor.GetRange(start, end)
            return scope, start, end, "current line"
        return scope, start, end, "current paragraph"

    def glow_audit_document(self) -> None:
        markup = self._current_markup_context()
        text = self.editor.GetValue()
        report = build_audit_report(self.document.name, text, markup, "current document")
        self._create_named_scratch_tab(f"GLOW Audit - {self.document.name}", report)
        self._set_status(f"Opened GLOW audit for {self.document.name}")

    def glow_audit_selection(self) -> None:
        text, _start, _end, scope_label = self._glow_scope()
        markup = self._current_markup_context()
        report = build_audit_report(self.document.name, text, markup, scope_label)
        self._create_named_scratch_tab(f"GLOW Audit - {scope_label.title()}", report)
        self._set_status(f"Opened GLOW audit for {scope_label}")

    def glow_fix_document(self) -> None:
        original = self.editor.GetValue()
        markup = self._current_markup_context()
        result = fix_text(original, markup)
        if result.text == original:
            report = build_fix_report(self.document.name, result, markup, "current document")
            self._create_named_scratch_tab(f"GLOW Fix Report - {self.document.name}", report)
            self._set_status("No deterministic GLOW fixes were available")
            return
        preview_title = f"{self.document.name} - GLOW Fix Preview"
        index = self._create_document_tab(
            Document(text=result.text, path=None, modified=False),
            select=True,
        )
        self._set_tab_page_text(index, preview_title)
        report = build_fix_report(self.document.name, result, markup, "current document")
        self._record_notification(report.splitlines()[0], "glow")
        self._start_compare_session([(self.document.name, original), (preview_title, result.text)])
        self._set_status(
            f"Opened GLOW fix preview with {len(result.fixes)} changes and started compare"
        )

    def glow_fix_selection(self) -> None:
        text, start, end, scope_label = self._glow_scope()
        markup = self._current_markup_context()
        result = fix_text(text, markup)
        if result.text == text:
            self._set_status(f"No deterministic GLOW fixes were available for {scope_label}")
            return
        self.editor.Replace(start, end, result.text)
        self.editor.SetSelection(start, start + len(result.text))
        self.document.set_text(self.editor.GetValue())
        report = build_fix_report(self.document.name, result, markup, scope_label)
        self._record_notification(report.splitlines()[0], "glow")
        self._set_status(f"Applied {len(result.fixes)} GLOW fixes to {scope_label}")

    def make_document_accessible(self) -> None:
        markup = self._current_markup_context()
        original = self.editor.GetValue()

        def _on_apply(result: AgentRunResult) -> None:
            last = self.editor.GetLastPosition()
            self.editor.Replace(0, last, result.text)
            self.document.set_text(self.editor.GetValue())
            self._record_notification(
                f"Accessibility Tune-Up applied {len(result.applied)} changes "
                f"to {self.document.name}",
                "glow",
            )
            self._create_named_scratch_tab(
                f"Accessibility Tune-Up - {self.document.name}", result.report
            )
            self._set_status(
                f"Accessibility Tune-Up applied {len(result.applied)} changes; "
                f"{result.findings_after} findings remain"
            )

        dialog = AccessibilityAgentDialog(
            self.frame,
            document_name=self.document.name,
            document_text=original,
            markup=markup,
            scope_label="current document",
            on_apply=_on_apply,
            announce=self._announce,
        )
        self._announce(summarize_plan(dialog.plan))
        dialog.show_modal()

    def go_to_line(self) -> None:
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame,
            "Enter line or line,column:",
            "Go To Line",
            value="1",
        ) as dialog:
            if self._show_modal_dialog(dialog, "Go To Line") != wx.ID_OK:
                return
            raw_line = dialog.GetValue().strip()

        try:
            target_line, target_column = parse_line_column(raw_line)
        except ValueError:
            self._show_message_box(
                "Use a line number or line,column (for example: 12 or 12,4).",
                "Go To Line",
                wx.ICON_ERROR | wx.OK,
            )
            return
        if target_line < 1:
            self._show_message_box(
                "Line number must be at least 1.",
                "Go To Line",
                wx.ICON_ERROR | wx.OK,
            )
            return
        if target_column is not None and target_column < 1:
            self._show_message_box(
                "Column number must be at least 1.",
                "Go To Line",
                wx.ICON_ERROR | wx.OK,
            )
            return

        text = self.editor.GetValue()
        line_starts = [0]
        for index, char in enumerate(text):
            if char == "\n":
                line_starts.append(index + 1)

        if target_line > len(line_starts):
            self._show_message_box(
                f"Document has only {len(line_starts)} lines.",
                "Go To Line",
                wx.ICON_ERROR | wx.OK,
            )
            return

        line_start = line_starts[target_line - 1]
        if target_line < len(line_starts):
            line_end = line_starts[target_line] - 1
        else:
            line_end = len(text)
        if target_column is None:
            insertion_point = line_start
        else:
            insertion_point = min(line_start + target_column - 1, line_end)
        self._record_location_before_jump()
        self._move_point(insertion_point)
        self.editor.SetFocus()
        self._location_ring.record(insertion_point)
        if target_column is None:
            self._set_status(f"Moved to line {target_line}")
        else:
            self._set_status(f"Moved to line {target_line}, column {target_column}")

    def go_to_line_number(self, lineno: int) -> None:
        """Navigate to *lineno* (1-based) without prompting.

        Used by GoToAnythingDialog (§8.1 NAV-4).
        """
        if self.editor is None:
            return
        text = self.editor.GetValue()
        line_starts = [0]
        for index, char in enumerate(text):
            if char == "\n":
                line_starts.append(index + 1)
        if lineno < 1 or lineno > len(line_starts):
            self._set_status(f"Line {lineno} out of range (document has {len(line_starts)} lines)")
            return
        insertion_point = line_starts[lineno - 1]
        self._record_location_before_jump()
        self._move_point(insertion_point)
        self.editor.SetFocus()
        self._location_ring.record(insertion_point)
        self._set_status(f"Moved to line {lineno}")

    def go_to_page(self) -> None:
        wx = self._wx
        text = self.editor.GetValue()
        starts = page_starts(text)
        with wx.TextEntryDialog(
            self.frame,
            f"Enter a page number (1-{len(starts)}):",
            "Go To Page",
            value="1",
        ) as dialog:
            if self._show_modal_dialog(dialog, "Go To Page") != wx.ID_OK:
                return
            raw_value = dialog.GetValue().strip()
        try:
            page_number = int(raw_value)
        except ValueError:
            self._show_message_box(
                "Page number must be a number.",
                "Go To Page",
                wx.ICON_ERROR | wx.OK,
            )
            return
        target = page_start_for_number(text, page_number)
        if target is None:
            self._show_message_box(
                f"Document has only {len(starts)} page(s).",
                "Go To Page",
                wx.ICON_ERROR | wx.OK,
            )
            return
        self._record_location_before_jump()
        self._move_point(target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        self._set_status(f"Moved to page {page_number}")

    def navigate_back_location(self) -> None:
        cursor = self.editor.GetInsertionPoint()
        target = self._location_ring.back(cursor)
        if target is None:
            self._set_status("No earlier location")
            return
        self._move_point(target)
        self.editor.SetFocus()
        self._set_status("Moved back")

    def navigate_forward_location(self) -> None:
        cursor = self.editor.GetInsertionPoint()
        target = self._location_ring.forward(cursor)
        if target is None:
            self._set_status("No later location")
            return
        self._move_point(target)
        self.editor.SetFocus()
        self._set_status("Moved forward")

    def navigate_next_heading(self) -> None:
        self._navigate_heading(reverse=False)

    def navigate_previous_heading(self) -> None:
        self._navigate_heading(reverse=True)

    def _navigate_heading(self, reverse: bool) -> None:
        markup_kind = infer_markup_kind(self.document.path)
        if markup_kind not in {"markdown", "html"}:
            self._set_status("Heading navigation is available in Markdown or HTML documents")
            return
        cursor = self.editor.GetInsertionPoint()
        if reverse:
            target = previous_heading_start(self.editor.GetValue(), cursor, markup_kind)
            if target is None:
                self._set_status("No previous heading")
                return
            label = "previous heading"
        else:
            target = next_heading_start(self.editor.GetValue(), cursor, markup_kind)
            if target is None:
                self._set_status("No next heading")
                return
            label = "next heading"
        self._record_location_before_jump()
        self.editor.SetInsertionPoint(target)
        self.editor.SetSelection(target, target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        context = heading_context_at(self.editor.GetValue(), target, markup_kind)
        if context is not None:
            title = context.title or "untitled"
            self._set_status(
                f"Moved to {label}, H{context.level}, {context.ordinal} of {context.total}: {title}"
            )
        else:
            self._set_status(f"Moved to {label}")

    def navigate_next_block(self) -> None:
        self._navigate_block(reverse=False)

    def navigate_previous_block(self) -> None:
        self._navigate_block(reverse=True)

    def _navigate_block(self, reverse: bool) -> None:
        cursor = self.editor.GetInsertionPoint()
        if reverse:
            target = previous_block_start(self.editor.GetValue(), cursor)
            if target is None:
                self._set_status("No previous block")
                return
            label = "previous block"
        else:
            target = next_block_start(self.editor.GetValue(), cursor)
            if target is None:
                self._set_status("No next block")
                return
            label = "next block"
        self._record_location_before_jump()
        self.editor.SetInsertionPoint(target)
        self.editor.SetSelection(target, target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        self._set_status(f"Moved to {label}")

    def open_outline_navigator(self) -> None:
        if self.document.path is not None and self.document.path.suffix.lower() == ".epub":
            self.open_epub_navigator()
            return
        markup_kind = infer_markup_kind(self.document.path)
        if markup_kind == "plain":
            self._set_status("Outline is not available for plain text files")
            return
        action_label = "Jump to Key" if markup_kind == "yaml" else "Jump to Heading"
        nodes = self._build_outline_navigator_nodes(action_label=action_label)
        if not nodes:
            if markup_kind == "yaml":
                self._set_status("No YAML structure found")
            else:
                self._set_status("No outline headings found")
            return
        title = "YAML Navigator" if markup_kind == "yaml" else "Outline Navigator"
        root_label = "Keys" if markup_kind == "yaml" else "Headings"
        selected = self._show_tree_navigator(
            title=title,
            root_label=root_label,
            nodes=nodes,
        )
        if not isinstance(selected, OutlineEntry):
            self._set_status("Outline navigation cancelled")
            return
        self._jump_to(selected.position, "Moved to heading")

    def open_quick_nav(self) -> None:
        """Open the unified Quick Nav / Go to Anything surface (NAV-1, NAV-4).

        Builds one index of navigable landmarks (headings, links, lists, list
        items, tables, block quotes, bookmarks, code blocks) and presents it with
        a category filter that shows counts (NAV-1) and a type-ahead jump field
        (NAV-4). Selecting an entry jumps to it.
        """
        text = self.editor.GetValue()
        context = self._browse_navigation_context()
        items = build_nav_index(text, context)
        items = include_nav_items(
            items,
            headings=getattr(self.settings, "quick_nav_include_headings", True),
            links=getattr(self.settings, "quick_nav_include_links", True),
            lists=getattr(self.settings, "quick_nav_include_lists", True),
        )
        if not items:
            self._set_status("No navigable elements found")
            return
        selected = self._present_quick_nav(items)
        if not isinstance(selected, NavItem):
            self._set_status("Quick Nav cancelled")
            return
        self._jump_to(selected.position, f"Moved to {nav_category(selected.kind).lower()}")

    def _present_quick_nav(self, items: list[NavItem]) -> NavItem | None:
        """Show the Quick Nav dialog and return the chosen item, or None."""
        wx = self._wx
        dialog = wx.Dialog(
            self.frame,
            title="Quick Nav",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(640, 640),
        )
        chosen: dict[str, NavItem | None] = {"item": None}
        try:
            inner = wx.BoxSizer(wx.VERTICAL)
            inner.Add(
                wx.StaticText(
                    dialog,
                    label=(
                        "Type to filter. Choose a category to narrow by type. "
                        "Enter jumps to the selected element."
                    ),
                ),
                0,
                wx.ALL | wx.EXPAND,
                8,
            )
            search = wx.TextCtrl(dialog)
            inner.Add(search, 0, wx.ALL | wx.EXPAND, 8)
            summary = nav_type_summary(items)
            category_labels = [f"All ({len(items)})"] + [
                f"{name} ({count})" for name, count in summary
            ]
            category_values: list[str | None] = [None] + [name for name, _ in summary]
            category_box = wx.ListBox(dialog, choices=category_labels)
            category_box.SetSelection(0)
            inner.Add(category_box, 0, wx.ALL | wx.EXPAND, 8)
            results = wx.ListBox(dialog)
            inner.Add(results, 1, wx.ALL | wx.EXPAND, 8)
            go_button = wx.Button(dialog, id=wx.ID_OK, label="Go")
            cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
            buttons = wx.StdDialogButtonSizer()
            buttons.AddButton(go_button)
            buttons.AddButton(cancel_button)
            buttons.Realize()
            inner.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
            dialog.SetSizer(inner)

            filtered: list[NavItem] = []
            # SET-2: only start matching once the query reaches the configured
            # minimum length; shorter queries fall back to showing the whole
            # (category-filtered) list rather than an empty result set.
            min_chars = max(1, int(getattr(self.settings, "quick_nav_min_chars", 1) or 1))
            # SET-2: debounce type-ahead filtering so large documents do not
            # re-filter on every keystroke.
            debounce_ms = int(getattr(self.settings, "quick_nav_debounce_ms", 250) or 0)
            debounce_timer: dict[str, object] = {"handle": None}

            def refresh() -> None:
                nonlocal filtered
                index = category_box.GetSelection()
                category = category_values[index] if 0 <= index < len(category_values) else None
                raw_query = search.GetValue()
                query = raw_query if len(raw_query.strip()) >= min_chars else ""
                filtered = filter_nav_items(items, query, category)
                results.Set([nav_item_display(item) for item in filtered])
                if filtered:
                    results.SetSelection(0)

            def schedule_refresh() -> None:
                if debounce_ms <= 0:
                    refresh()
                    return
                handle = debounce_timer.get("handle")
                stop = getattr(handle, "Stop", None)
                if callable(stop):
                    stop()
                call_later = getattr(wx, "CallLater", None)
                if callable(call_later):
                    debounce_timer["handle"] = call_later(debounce_ms, refresh)
                else:
                    refresh()

            def on_text(_event: object) -> None:
                schedule_refresh()

            def on_category(_event: object) -> None:
                refresh()

            def on_activate(_event: object) -> None:
                index = results.GetSelection()
                if 0 <= index < len(filtered):
                    chosen["item"] = filtered[index]
                    dialog.EndModal(wx.ID_OK)

            search.Bind(wx.EVT_TEXT, on_text)
            category_box.Bind(wx.EVT_LISTBOX, on_category)
            results.Bind(wx.EVT_LISTBOX_DCLICK, on_activate)
            go_button.SetDefault()
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            refresh()
            call_after = getattr(wx, "CallAfter", None)
            if callable(call_after):
                call_after(search.SetFocus)
            else:
                search.SetFocus()
            if self._show_modal_dialog(dialog, "Quick Nav") == wx.ID_OK:
                if chosen["item"] is None:
                    index = results.GetSelection()
                    if 0 <= index < len(filtered):
                        chosen["item"] = filtered[index]
                return chosen["item"]
            return None
        finally:
            handle = debounce_timer.get("handle")
            stop = getattr(handle, "Stop", None)
            if callable(stop):
                stop()
            dialog.Destroy()
            self.editor.SetFocus()

    def open_heading_organizer(self) -> None:
        markup_kind = infer_markup_kind(self.document.path)
        if markup_kind not in {"markdown", "html"}:
            self._set_status("Heading Organizer is only available for Markdown or HTML documents")
            return
        text = self.editor.GetValue()
        headings = parse_heading_blocks(text, markup_kind)
        if not headings:
            self._set_status("No headings found for Heading Organizer")
            return
        updated = self._show_heading_organizer_dialog(markup_kind, headings)
        if updated is None:
            self._set_status("Heading Organizer cancelled")
            return
        transformed = apply_heading_organizer_edits(text, markup_kind, updated)
        if transformed == text:
            self._set_status("Heading Organizer closed without changes")
            return
        self._apply_editor_text(transformed, "Applied heading organizer changes")

    def _show_heading_organizer_dialog(
        self,
        markup_kind: str,
        headings: list[HeadingBlock],
    ) -> list[HeadingBlock] | None:
        wx = self._wx
        dialog = wx.Dialog(
            self.frame,
            title="Heading Organizer",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(920, 620),
        )
        working = [replace(heading) for heading in headings]
        source_text = self.editor.GetValue()
        originals = {heading.source_index: heading for heading in headings}
        selected_index = 0
        list_box = wx.ListBox(dialog)
        preview = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        instructions = wx.StaticText(
            dialog,
            label=(
                "Arrow through headings. Tab demotes, Shift+Tab promotes. "
                "Use Move Up/Down to reorder sections and Rename to edit heading text."
            ),
        )
        promote_button = wx.Button(dialog, label="Promote")
        demote_button = wx.Button(dialog, label="Demote")
        move_up_button = wx.Button(dialog, label="Move Up")
        move_down_button = wx.Button(dialog, label="Move Down")
        rename_button = wx.Button(dialog, label="Rename...")
        validate_button = wx.Button(dialog, label="Validate")
        apply_button = wx.Button(dialog, id=wx.ID_OK, label="Apply")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")

        def labels() -> list[str]:
            return [
                f"Heading {entry.level}: {entry.title or '(empty heading)'}" for entry in working
            ]

        def refresh() -> None:
            nonlocal selected_index
            list_box.Set(labels())
            if not working:
                preview.ChangeValue("No headings found.")
                return
            selected_index = max(0, min(selected_index, len(working) - 1))
            list_box.SetSelection(selected_index)
            update_preview()

        def selected() -> HeadingBlock | None:
            if not working:
                return None
            current = list_box.GetSelection()
            if current == wx.NOT_FOUND:
                return None
            return working[current]

        def set_selected(entry: HeadingBlock) -> None:
            nonlocal selected_index
            current = list_box.GetSelection()
            if current == wx.NOT_FOUND:
                return
            working[current] = entry
            selected_index = current
            refresh()

        def update_preview() -> None:
            entry = selected()
            if entry is None:
                preview.ChangeValue("No heading selected.")
                return
            origin = originals.get(entry.source_index)
            if origin is None:
                preview.ChangeValue(entry.title)
                return
            section = source_text[origin.section_start : origin.section_end].strip()
            preview.ChangeValue(section or entry.title)

        def promote() -> None:
            entry = selected()
            if entry is None:
                return
            if entry.level <= 1:
                self._set_status("Heading already at level 1")
                return
            set_selected(replace(entry, level=entry.level - 1))
            self._set_status(f"{entry.title or '(empty heading)'} is now Heading {entry.level - 1}")

        def demote() -> None:
            entry = selected()
            if entry is None:
                return
            if entry.level >= 6:
                self._set_status("Heading already at level 6")
                return
            set_selected(replace(entry, level=entry.level + 1))
            self._set_status(f"{entry.title or '(empty heading)'} is now Heading {entry.level + 1}")

        def move(delta: int) -> None:
            nonlocal selected_index
            current = list_box.GetSelection()
            if current == wx.NOT_FOUND:
                return
            target = current + delta
            if target < 0 or target >= len(working):
                return
            working[current], working[target] = working[target], working[current]
            selected_index = target
            refresh()
            self._set_status("Moved heading")

        def rename() -> None:
            entry = selected()
            if entry is None:
                return
            with wx.TextEntryDialog(
                dialog,
                "Enter heading text:",
                "Rename Heading",
                value=entry.title,
            ) as rename_dialog:
                if self._show_modal_dialog(rename_dialog, "Rename Heading") != wx.ID_OK:
                    return
                new_title = rename_dialog.GetValue().strip()
            set_selected(replace(entry, title=new_title))
            self._set_status("Renamed heading")

        def validate(show_success: bool = False) -> bool:
            issues = validate_heading_sequence(working)
            if not issues:
                if show_success:
                    self._show_message_box(
                        "Heading order passed accessibility checks.",
                        "Heading Organizer",
                        wx.OK | wx.ICON_INFORMATION,
                    )
                return True
            self._show_message_box(
                "Fix these heading issues before applying:\n\n"
                + "\n".join(f"- {issue}" for issue in issues),
                "Heading Organizer",
                wx.OK | wx.ICON_WARNING,
            )
            return False

        def on_key(event: object) -> None:
            key_code = event.GetKeyCode()
            if key_code == wx.WXK_TAB:
                if event.ShiftDown():
                    promote()
                else:
                    demote()
                return
            if key_code in (wx.WXK_ADD, wx.WXK_NUMPAD_ADD):
                demote()
                return
            if key_code in (wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT):
                promote()
                return
            event.Skip()

        body = wx.BoxSizer(wx.HORIZONTAL)
        main = wx.BoxSizer(wx.VERTICAL)
        main.Add(instructions, 0, wx.ALL | wx.EXPAND, 8)
        main.Add(list_box, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        main.Add(
            wx.StaticText(dialog, label="Preview of selected heading section:"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        main.Add(preview, 1, wx.ALL | wx.EXPAND, 8)
        actions = wx.BoxSizer(wx.VERTICAL)
        actions.Add(promote_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        actions.Add(demote_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        actions.Add(move_up_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        actions.Add(move_down_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        actions.Add(rename_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        actions.Add(validate_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        actions.AddStretchSpacer(1)
        actions.Add(apply_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        actions.Add(cancel_button, 0, wx.EXPAND)
        body.Add(main, 1, wx.EXPAND)
        body.Add(actions, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(body)

        list_box.Bind(wx.EVT_LISTBOX, lambda _e: update_preview())
        list_box.Bind(wx.EVT_CHAR_HOOK, on_key)
        promote_button.Bind(wx.EVT_BUTTON, lambda _e: promote())
        demote_button.Bind(wx.EVT_BUTTON, lambda _e: demote())
        move_up_button.Bind(wx.EVT_BUTTON, lambda _e: move(-1))
        move_down_button.Bind(wx.EVT_BUTTON, lambda _e: move(1))
        rename_button.Bind(wx.EVT_BUTTON, lambda _e: rename())
        validate_button.Bind(wx.EVT_BUTTON, lambda _e: validate(show_success=True))
        apply_button.Bind(
            wx.EVT_BUTTON,
            lambda _e: dialog.EndModal(wx.ID_OK) if validate() else None,
        )
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))

        refresh()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        if self._show_modal_dialog(dialog, "Heading Organizer") != wx.ID_OK:
            return None
        return working

    def open_yaml_structure_editor(self) -> None:
        if infer_markup_kind(self.document.path) != "yaml":
            self._set_status("YAML structure editing is only available for YAML files")
            return
        updated_text = self._show_yaml_structure_editor()
        if updated_text is None:
            self._set_status("YAML structure editor cancelled")
            return
        if updated_text == self.editor.GetValue():
            self._set_status("YAML structure editor closed without changes")
            return
        self._apply_editor_text(updated_text, "Updated YAML structure")

    def navigate_next_token(self) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        pos, token = next_token_position(text, cursor + 1)
        if not token:
            self._announce("End of document")
            return
        tab = getattr(self, "_current_tab", None)
        profile = getattr(tab, "_language_profile", None)
        keywords = profile.keywords if profile else ()
        label = classify_token(token, keywords)
        self._move_point(pos)
        self.editor.SetFocus()
        self._announce(label)
        self._set_status(label)

    def navigate_previous_token(self) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        pos, token = prev_token_position(text, cursor)
        if not token:
            self._announce("Beginning of document")
            return
        tab = getattr(self, "_current_tab", None)
        profile = getattr(tab, "_language_profile", None)
        keywords = profile.keywords if profile else ()
        label = classify_token(token, keywords)
        self._move_point(pos)
        self.editor.SetFocus()
        self._announce(label)
        self._set_status(label)

    def set_document_language(self, language: str | None = None) -> None:
        """Set the active language profile for the current document tab."""
        wx = self._wx
        tab = getattr(self, "_current_tab", None)
        if tab is None:
            return
        if language:
            profile: LanguageProfile | None = get_profile_by_name(language)
            if profile is None:
                self._set_status(f"Unknown language: {language}")
                return
        else:
            profiles = all_profiles()
            names = [p.name for p in profiles] + ["Plain text"]
            dlg = wx.SingleChoiceDialog(
                self.frame,
                "Select language profile for this document:",
                "Set Document Language",
                names,
            )
            current = getattr(tab, "_language_profile", None)
            if current is not None:
                try:
                    idx = names.index(current.name)
                    dlg.SetSelection(idx)
                except ValueError:
                    pass
            if self._show_modal_dialog(dlg, "Set Document Language") != wx.ID_OK:
                return
            chosen = dlg.GetStringSelection()
            profile = get_profile_by_name(chosen) if chosen != "Plain text" else PLAIN_PROFILE
        tab._language_profile = profile
        tab._language_profile_pinned = True
        self._apply_statusbar_layout()
        name = profile.name if profile else "Plain text"
        self._set_status(f"Language set to {name}")
        self._announce(f"Language: {name}")

    def format_auto_indent_newline(self) -> None:
        """Insert a newline with language-aware indentation."""
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        if not hasattr(editor, "GetCurrentLine"):
            if hasattr(editor, "WriteText"):
                editor.WriteText("\n")
            return
        line = editor.GetCurrentLine()
        line_text = editor.GetLine(line) if hasattr(editor, "GetLine") else ""
        stripped = line_text.rstrip("\r\n")
        leading = stripped[: len(stripped) - len(stripped.lstrip())]
        tab = getattr(self, "_current_tab", None)
        profile = getattr(tab, "_language_profile", None)
        last_char = stripped.rstrip()[-1:] if stripped.rstrip() else ""
        extra = ""
        if last_char in (":", "{"):
            unit = profile.indent_unit if profile else int(getattr(self.settings, "indent_size", 4))
            if profile and profile.uses_tabs:
                extra = "\t"
            else:
                extra = " " * unit
        new_text = "\n" + leading + extra
        if hasattr(editor, "ReplaceSelection"):
            editor.ReplaceSelection(new_text)
        elif hasattr(editor, "WriteText"):
            editor.WriteText(new_text)
        self._set_status("Auto-indent newline")

    def match_bracket(self) -> None:
        target = find_matching_bracket(self.editor.GetValue(), self.editor.GetInsertionPoint())
        if target is None:
            self._set_status("No matching bracket found")
            return
        self._jump_to(target, "Moved to matching bracket")

    def navigate_next_structure(self) -> None:
        self._navigate_structure(reverse=False)

    def navigate_previous_structure(self) -> None:
        self._navigate_structure(reverse=True)

    def _navigate_structure(self, reverse: bool) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        markup_kind = infer_markup_kind(self.document.path)
        if reverse:
            target = previous_structure_position(text, cursor, markup_kind)
            if target is None:
                self._set_status("No previous structure")
                return
            label = "Moved to previous structure"
        else:
            target = next_structure_position(text, cursor, markup_kind)
            if target is None:
                self._set_status("No next structure")
                return
            label = "Moved to next structure"
        self._jump_to(target, label)

    def navigate_next_region(self) -> None:
        self._cycle_region(reverse=False)

    def navigate_previous_region(self) -> None:
        self._cycle_region(reverse=True)

    def _current_focus_region_labels(self) -> tuple[str, ...]:
        """Regions reachable with F6 right now.

        Editor and Status Bar are always present. The side preview is only in
        the rotation while it is split open, so screen reader users can F6 into
        the rendered Markdown/HTML and use browse-mode heading navigation, then
        F6 back out."""
        labels = ["Editor"]
        tab = self._active_tab()
        if (
            tab is not None
            and getattr(tab, "preview", None) is not None
            and getattr(tab, "splitter", None) is not None
            and tab.splitter.IsSplit()
        ):
            labels.append("Preview")
        labels.append("Status Bar")
        return tuple(labels)

    def _detect_active_region(self, regions: tuple[str, ...]) -> str:
        """Resolve which region currently holds focus.

        Editor and Status Bar report focus reliably through wx. The preview is
        a WebView whose native child often hides focus from wx.Window.FindFocus,
        so for that case we trust the tracked region instead."""
        tab = self._active_tab()
        preview_ctrl = (
            tab.preview.control
            if tab is not None and getattr(tab, "preview", None) is not None
            else None
        )
        try:
            win = self._wx.Window.FindFocus()
        except Exception:
            win = None
        while win is not None:
            if preview_ctrl is not None and win is preview_ctrl and "Preview" in regions:
                return "Preview"
            if win is self.statusbar:
                return "Status Bar"
            if win is self.editor:
                return "Editor"
            get_parent = getattr(win, "GetParent", None)
            win = get_parent() if callable(get_parent) else None
        # The WebView preview can hide focus from wx; fall back to the tracked
        # region so the cycle still resumes from the right place.
        if self._active_region in regions:
            return self._active_region
        return "Editor"

    def _focus_region(self, label: str) -> None:
        if label == "Status Bar":
            self.statusbar.SetFocus()
            return
        if label == "Preview":
            tab = self._active_tab()
            if tab is not None and getattr(tab, "preview", None) is not None:
                tab.preview.control.SetFocus()
                return
        self.editor.SetFocus()

    def _set_active_region(self, label: str) -> None:
        """Record a region transition for the keyboard-trap audit, keeping the
        tracker's enter/exit balanced. Routing every focus move through here
        keeps F6 cycling consistent regardless of how focus got there."""
        previous = self._active_region
        if label == previous:
            return
        self._region_tracker.exit(previous)
        self._region_tracker.enter(label)
        self._active_region = label

    def _cycle_region(self, reverse: bool) -> None:
        regions = self._current_focus_region_labels()
        if len(regions) < 2:
            return
        current_label = self._detect_active_region(regions)
        # Reconcile the tracker to where focus actually is before we move, so a
        # detected drift (e.g. preview just closed) doesn't unbalance the audit.
        self._active_region = current_label
        current = regions.index(current_label)
        step = -1 if reverse else 1
        next_label = regions[(current + step) % len(regions)]
        if next_label == current_label:
            return
        self._set_active_region(next_label)
        self._focus_region(next_label)
        self._set_status(f"Focused {next_label} region")

    def _outline_entries(self) -> list[OutlineEntry]:
        markup_kind = infer_markup_kind(self.document.path)
        return extract_outline_entries(self.editor.GetValue(), markup_kind)

    def _build_yaml_structure_navigator_nodes(self) -> list[_NavigatorNode]:
        nodes = extract_yaml_nodes(self.editor.GetValue())
        roots: list[_NavigatorNode] = []
        for node in nodes:
            roots.append(self._build_yaml_structure_node(node))
        return roots

    def _build_yaml_structure_node(self, node: YamlNode) -> _NavigatorNode:
        preview = self._yaml_node_preview(node)
        return _NavigatorNode(
            label=f"{node.label or '(item)'} (Ln {node.line_no + 1})",
            preview=preview,
            payload=node,
            action_label="Edit Node",
            children=[self._build_yaml_structure_node(child) for child in node.children],
        )

    def _yaml_node_preview(self, node: YamlNode, text: str | None = None) -> str:
        source = text if text is not None else self.editor.GetValue()
        lines = source.splitlines()
        if not lines or node.line_no >= len(lines):
            return node.label or "(item)"
        end_line = min(node.end_line, len(lines) - 1)
        excerpt = "\n".join(lines[node.line_no : end_line + 1]).strip()
        return excerpt or (node.label or "(item)")

    def _yaml_node_accepts_children(self, node: YamlNode) -> bool:
        return not node.value.strip()

    def _show_yaml_structure_editor(self) -> str | None:
        wx = self._wx
        working_text = self.editor.GetValue()
        dialog = wx.Dialog(self.frame, title="YAML Structure Editor", size=(1020, 700))
        splitter = wx.SplitterWindow(dialog, style=wx.SP_LIVE_UPDATE)
        tree = wx.TreeCtrl(
            splitter,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HAS_VARIABLE_ROW_HEIGHT,
        )
        preview = wx.TextCtrl(splitter, style=wx.TE_MULTILINE | wx.TE_READONLY)
        splitter.SplitVertically(tree, preview, 360)
        splitter.SetMinimumPaneSize(240)

        item_payloads: dict[object, YamlNode] = {}
        selected_node: YamlNode | None = None
        root = tree.AddRoot("YAML Structure")

        def build_tree(preferred_line_no: int | None = None) -> None:
            nonlocal selected_node, root
            nodes = extract_yaml_nodes(working_text)
            item_payloads.clear()
            tree.DeleteAllItems()
            root = tree.AddRoot("YAML Structure")

            def append_nodes(parent: object, children: list[YamlNode]) -> object | None:
                first_item = None
                for node in children:
                    label = f"{node.label or '(item)'} (Ln {node.line_no + 1})"
                    item = tree.AppendItem(parent, label)
                    item_payloads[item] = node
                    if first_item is None:
                        first_item = item
                    append_nodes(item, node.children)
                return first_item

            first_item = append_nodes(root, nodes)
            tree.Expand(root)
            selected_node = None
            target_item = first_item
            if preferred_line_no is not None:
                for item, node in item_payloads.items():
                    if node.line_no == preferred_line_no:
                        target_item = item
                        break
            if target_item is not None:
                selected_node = item_payloads.get(target_item)
                if selected_node is not None:
                    preview.ChangeValue(self._yaml_node_preview(selected_node, working_text))
                tree.SelectItem(target_item)
            else:
                preview.ChangeValue("No YAML structure found")
                return

        def current_node() -> YamlNode | None:
            return selected_node

        def refresh_preview(node: YamlNode | None) -> None:
            if node is None:
                preview.ChangeValue("No YAML structure found")
                return
            preview.ChangeValue(self._yaml_node_preview(node, working_text))

        def prompt_kind(default_kind: str) -> YamlNodeKind | None:
            with wx.SingleChoiceDialog(
                dialog,
                "Choose the YAML structure kind to insert:",
                "Insert YAML Node",
                choices=["Mapping key", "List item"],
            ) as choice:
                choice.SetSelection(0 if default_kind == "mapping" else 1)
                if self._show_modal_dialog(choice, "Insert YAML Node Kind") != wx.ID_OK:
                    return None
                return "mapping" if choice.GetSelection() == 0 else "sequence"

        def prompt_label(title: str, default_value: str = "") -> str | None:
            with wx.TextEntryDialog(
                dialog,
                "Enter the YAML label or item text:",
                title,
                value=default_value,
            ) as entry:
                if self._show_modal_dialog(entry, title) != wx.ID_OK:
                    return None
                value = entry.GetValue().strip()
                return value or None

        def select_node_from_event(event: object) -> None:
            nonlocal selected_node
            node = item_payloads.get(event.GetItem())
            selected_node = node
            refresh_preview(node)
            event.Skip()

        def perform_update(action: str, update: str, preferred_line_no: int | None = None) -> None:
            nonlocal working_text
            working_text = update
            build_tree(preferred_line_no)
            node = current_node()
            if node is not None:
                refresh_preview(node)
            self._set_status(action)

        def add_child() -> None:
            node = current_node()
            if node is None:
                return
            if not self._yaml_node_accepts_children(node):
                self._show_message_box(
                    "This YAML node already has a scalar value, so it cannot accept children.",
                    "YAML Structure Editor",
                    wx.ICON_WARNING | wx.OK,
                )
                return
            kind = prompt_kind("mapping" if node.kind == "mapping" else "sequence")
            if kind is None:
                return
            label = prompt_label("Add YAML Child")
            if label is None:
                return
            try:
                updated = add_yaml_child(working_text, node.line_no, kind, label)
            except ValueError as error:
                self._show_message_box(str(error), "YAML Structure Editor", wx.ICON_ERROR | wx.OK)
                return
            perform_update("Added YAML child", updated, node.end_line + 1)

        def add_sibling() -> None:
            node = current_node()
            if node is None:
                return
            kind = prompt_kind("mapping" if node.kind == "mapping" else "sequence")
            if kind is None:
                return
            label = prompt_label("Add YAML Sibling")
            if label is None:
                return
            try:
                updated = add_yaml_sibling(working_text, node.line_no, kind, label)
            except ValueError as error:
                self._show_message_box(str(error), "YAML Structure Editor", wx.ICON_ERROR | wx.OK)
                return
            perform_update("Added YAML sibling", updated, node.end_line + 1)

        def rename_node() -> None:
            node = current_node()
            if node is None:
                return
            label = prompt_label("Rename YAML Node", node.label)
            if label is None:
                return
            try:
                updated = rename_yaml_node(working_text, node.line_no, label)
            except ValueError as error:
                self._show_message_box(str(error), "YAML Structure Editor", wx.ICON_ERROR | wx.OK)
                return
            perform_update("Renamed YAML node", updated, node.line_no)

        def delete_node() -> None:
            node = current_node()
            if node is None:
                return
            confirm = self._show_message_box(
                f"Delete '{node.label or '(item)'}' and its children?",
                "Delete YAML Node",
                wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
            )
            if confirm != wx.YES:
                return
            try:
                updated = delete_yaml_node(working_text, node.line_no)
            except ValueError as error:
                self._show_message_box(str(error), "YAML Structure Editor", wx.ICON_ERROR | wx.OK)
                return
            perform_update("Deleted YAML node", updated, max(node.line_no - 1, 0))

        buttons = wx.BoxSizer(wx.VERTICAL)
        add_child_button = wx.Button(dialog, label="Add Child...")
        add_sibling_button = wx.Button(dialog, label="Add Sibling...")
        rename_button = wx.Button(dialog, label="Rename...")
        delete_button = wx.Button(dialog, label="Delete")
        apply_button = wx.Button(dialog, id=wx.ID_OK, label="Apply Changes")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Close")
        buttons.Add(add_child_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        buttons.Add(add_sibling_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        buttons.Add(rename_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        buttons.Add(delete_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(apply_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        buttons.Add(cancel_button, 0, wx.EXPAND)

        controls = wx.BoxSizer(wx.VERTICAL)
        controls.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Use the structure tree to add, rename, and delete YAML keys or list items. "
                    "Child insertions stay indented to match the current node."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        controls.Add(splitter, 1, wx.ALL | wx.EXPAND, 8)
        content = wx.BoxSizer(wx.HORIZONTAL)
        content.Add(controls, 1, wx.EXPAND)
        content.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(content)

        tree.Bind(wx.EVT_TREE_SEL_CHANGED, select_node_from_event)
        add_child_button.Bind(wx.EVT_BUTTON, lambda _e: add_child())
        add_sibling_button.Bind(wx.EVT_BUTTON, lambda _e: add_sibling())
        rename_button.Bind(wx.EVT_BUTTON, lambda _e: rename_node())
        delete_button.Bind(wx.EVT_BUTTON, lambda _e: delete_node())
        apply_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))

        build_tree()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        if self._show_modal_dialog(dialog, "YAML Structure Editor") != wx.ID_OK:
            return None
        return working_text

    def _build_outline_navigator_nodes(
        self,
        *,
        action_label: str = "Jump to Heading",
    ) -> list[_NavigatorNode]:
        entries = self._outline_entries()
        if not entries:
            return []
        text = self.editor.GetValue()
        roots: list[_NavigatorNode] = []
        stack: list[tuple[int, _NavigatorNode]] = []
        for index, entry in enumerate(entries):
            end = entries[index + 1].position if index + 1 < len(entries) else len(text)
            preview = text[entry.position : end].strip() or entry.title
            node = _NavigatorNode(
                label=entry.title,
                preview=preview,
                payload=entry,
                action_label=action_label,
                children=[],
            )
            while stack and stack[-1][0] >= entry.level:
                stack.pop()
            if stack:
                stack[-1][1].children.append(node)
            else:
                roots.append(node)
            stack.append((entry.level, node))
        return roots

    def _build_epub_navigator_nodes(self, book: EpubBook) -> list[_NavigatorNode]:
        roots: list[_NavigatorNode] = []
        for chapter_index, chapter in enumerate(book.chapters):
            chapter_node = _NavigatorNode(
                label=chapter.title,
                preview=self._render_epub_chapter_text(chapter),
                payload=_EpubNavigatorTarget(chapter_index=chapter_index),
                action_label="Open Chapter",
                children=[],
            )
            heading_stack: list[tuple[int, _NavigatorNode]] = []
            for heading_index, heading in enumerate(chapter.headings):
                heading_node = _NavigatorNode(
                    label=heading.title,
                    preview=self._render_epub_heading_preview(chapter, heading.title),
                    payload=_EpubNavigatorTarget(
                        chapter_index=chapter_index,
                        heading_index=heading_index,
                    ),
                    action_label="Jump to Heading",
                    children=[],
                )
                while heading_stack and heading_stack[-1][0] >= heading.level:
                    heading_stack.pop()
                if heading_stack:
                    heading_stack[-1][1].children.append(heading_node)
                else:
                    chapter_node.children.append(heading_node)
                heading_stack.append((heading.level, heading_node))
            roots.append(chapter_node)
        return roots

    def _render_epub_chapter_text(self, chapter: EpubChapter) -> str:
        return f"# {chapter.title}\n\n{chapter.text}\n"

    def _render_epub_heading_preview(self, chapter: EpubChapter, heading_title: str) -> str:
        return f"# {chapter.title}\n\n## {heading_title}\n\n{chapter.text}\n"

    def _build_misspelling_navigator_nodes(
        self,
        misspellings: list[Misspelling],
    ) -> list[_NavigatorNode]:
        text = self.editor.GetValue()
        nodes: list[_NavigatorNode] = []
        for item in misspellings:
            line, column = line_column_for_position(text, item.start)
            line_start = text.rfind("\n", 0, item.start) + 1
            line_end = text.find("\n", item.end)
            if line_end == -1:
                line_end = len(text)
            excerpt = text[line_start:line_end].strip() or item.word
            nodes.append(
                _NavigatorNode(
                    label=f"{item.word} (Ln {line}, Col {column})",
                    preview=f"Line {line}, Column {column}\n\n{excerpt}",
                    payload=item,
                    action_label="Jump to Occurrence",
                    children=[],
                )
            )
        return nodes

    def _show_tree_navigator(
        self,
        *,
        title: str,
        root_label: str,
        nodes: list[_NavigatorNode],
    ) -> object | None:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title=title, size=(900, 620))
        splitter = wx.SplitterWindow(dialog, style=wx.SP_LIVE_UPDATE)
        tree = wx.TreeCtrl(splitter, style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT)
        preview = wx.TextCtrl(splitter, style=wx.TE_MULTILINE | wx.TE_READONLY)
        splitter.SplitVertically(tree, preview, 300)
        splitter.SetMinimumPaneSize(200)

        item_payloads: dict[object, object] = {}
        root = tree.AddRoot(root_label)

        def append_nodes(parent: object, children: list[_NavigatorNode]) -> object | None:
            first_item = None
            for node in children:
                item = tree.AppendItem(parent, node.label)
                item_payloads[item] = node.payload
                if first_item is None:
                    first_item = item
                append_nodes(item, node.children)
            return first_item

        first_item = append_nodes(root, nodes)
        tree.Expand(root)
        if first_item is not None:
            tree.SelectItem(first_item)
            preview.ChangeValue(nodes[0].preview)

        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        ok_button = None
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(splitter, 1, wx.EXPAND | wx.ALL, 8)
        if buttons is not None:
            layout.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        dialog.SetSizer(layout)

        node_by_payload: dict[object, _NavigatorNode] = {}

        def collect(children: list[_NavigatorNode]) -> None:
            for node in children:
                node_by_payload[node.payload] = node
                collect(node.children)

        collect(nodes)
        selected_payload = nodes[0].payload if nodes else None
        if ok_button is not None and nodes:
            ok_button.SetLabel(nodes[0].action_label)

        def on_select(event: object) -> None:
            nonlocal selected_payload
            item = event.GetItem()
            payload = item_payloads.get(item)
            if payload in node_by_payload:
                selected_payload = payload
                node = node_by_payload[payload]
                preview.ChangeValue(node.preview)
                if ok_button is not None:
                    ok_button.SetLabel(node.action_label)
            event.Skip()

        tree.Bind(wx.EVT_TREE_SEL_CHANGED, on_select)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        def focus_tree() -> None:
            tree.SetFocus()

        if hasattr(wx, "CallAfter"):
            wx.CallAfter(focus_tree)
        else:
            focus_tree()
        try:
            result = self._show_modal_dialog(dialog, title)
        finally:
            destroy = getattr(dialog, "Destroy", None)
            if callable(destroy):
                destroy()
        if result != wx.ID_OK:
            return None
        return selected_payload

    def _jump_to(self, position: int, message: str) -> None:
        self._record_location_before_jump()
        self._move_point(position)
        self.editor.SetFocus()
        self._location_ring.record(position)
        self._set_status(message)

    def _record_location_before_jump(self) -> None:
        self._location_ring.record(self.editor.GetInsertionPoint())

    def set_bookmark(self) -> None:
        wx = self._wx
        default_name = f"Bookmark {len(self._bookmarks) + 1}"
        with wx.TextEntryDialog(
            self.frame,
            "Enter bookmark name (named jump point):",
            "Set Bookmark",
            value=default_name,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Set Bookmark") != wx.ID_OK:
                return
            name = dialog.GetValue().strip()
        if not name:
            self._set_status("Set bookmark cancelled")
            return
        position = self.editor.GetInsertionPoint()
        self._bookmarks = set_bookmark(self._bookmarks, name, position)
        self._set_status(f'Set bookmark "{name}"')

    def go_to_bookmark(self) -> None:
        wx = self._wx
        names = bookmark_names(self._bookmarks)
        if not names:
            self._set_status("No bookmarks available. Bookmarks are named jump points.")
            return
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose bookmark (named jump point):",
            "Go To Bookmark",
            choices=names,
        ) as dialog:
            # Guarantee a valid selection so OK always resolves to a bookmark,
            # and wire the standard affirmative/escape ids so the dialog is
            # reliably dismissible by keyboard.
            if hasattr(dialog, "SetSelection"):
                dialog.SetSelection(0)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Go To Bookmark") != wx.ID_OK:
                return
            name = dialog.GetStringSelection()
        target = bookmark_position(self._bookmarks, name)
        if target is None:
            self._set_status("Bookmark was not found")
            return
        self._move_point(target)
        self.editor.SetFocus()
        self._set_status(f'Jumped to bookmark "{name}"')

    def list_bookmarks(self) -> None:
        names = bookmark_names(self._bookmarks)
        if not names:
            self._set_status("No bookmarks available. Bookmarks are named jump points.")
            return
        text = self.editor.GetValue()
        nodes: list[_NavigatorNode] = []
        for name in names:
            position = self._bookmarks[name]
            line, column = line_column_for_position(text, position)
            nodes.append(
                _NavigatorNode(
                    label=f"{name} (Ln {line}, Col {column})",
                    preview=f"Bookmark: {name}\n\nLine {line}, Column {column}",
                    payload=name,
                    action_label="Jump to Bookmark",
                    children=[],
                )
            )
        selected = self._show_tree_navigator(
            title="List Bookmarks",
            root_label="Bookmarks (Named Jump Points)",
            nodes=nodes,
        )
        if not isinstance(selected, str):
            self._set_status("Bookmark list cancelled")
            return
        target = bookmark_position(self._bookmarks, selected)
        if target is None:
            self._set_status("Bookmark was not found")
            return
        self._move_point(target)
        self.editor.SetFocus()
        self._set_status(f'Jumped to bookmark "{selected}"')

    def show_word_count(self) -> None:
        wx = self._wx
        stats = compute_document_stats(self.editor.GetValue())
        message = f"Words: {stats.words}\nLines: {stats.lines}\nCharacters: {stats.characters}"
        self._show_message_box(message, "Word Count", wx.ICON_INFORMATION | wx.OK)
        summary = f"Word count: {stats.words} words"
        if getattr(self.settings, "announce_counts", True):
            self._set_status(summary)
        else:
            self._set_status_quiet(summary)

    def show_dictionary_status(self) -> None:
        wx = self._wx
        project_root = Path.cwd()
        personal_count = len(load_scope_dictionary("personal", self.document.path, project_root))
        document_count = len(load_scope_dictionary("document", self.document.path, project_root))
        project_count = len(load_scope_dictionary("project", self.document.path, project_root))
        personal_path = app_data_dir() / "dictionaries" / "personal.json"
        document_path = (
            self.document.path.with_suffix(self.document.path.suffix + ".quill-dict.json")
            if self.document.path is not None
            else None
        )
        project_path = project_root / ".quill-dictionary.json"
        backend = spellcheck_backend_info()
        thesaurus_status = "installed" if thesaurus_engine.is_available() else "not installed"
        if personal_path.exists():
            personal_line = f"- Personal: {personal_count} (stored at {personal_path})"
        else:
            personal_line = (
                f"- Personal: {personal_count} "
                f"(not created yet; add a word to create {personal_path})"
            )
        if document_path is None:
            document_line = (
                f"- Document: {document_count} (not available until the current document is saved)"
            )
        elif document_path.exists():
            document_line = f"- Document: {document_count} (stored at {document_path})"
        else:
            document_line = (
                f"- Document: {document_count} (not created yet for this document: {document_path})"
            )
        if project_path.exists():
            project_line = f"- Project: {project_count} (stored at {project_path})"
        else:
            project_line = (
                f"- Project: {project_count} (not created yet in this folder: {project_path})"
            )
        lines = [
            f"Spell-check backend: {backend.name} — {backend.detail}",
            f"Thesaurus data: {thesaurus_status} ({thesaurus_engine.data_path()})",
            "",
            "User dictionary entries:",
            personal_line,
            document_line,
            project_line,
        ]
        self._show_message_box("\n".join(lines), "Dictionary Status", wx.ICON_INFORMATION | wx.OK)
        self._set_status(
            f"Spell check: {backend.name}; user dictionaries: personal={personal_count}, "
            f"document={document_count}, project={project_count}"
        )

    def open_spell_check_dialog(self) -> None:
        wx = self._wx
        dictionary = self._spell_dictionary()
        text = self.editor.GetValue()
        misspellings = list_misspellings(text, dictionary)
        if not misspellings:
            self._set_status("No misspellings found")
            return
        # A single typo (the common case, e.g. "This is a bligtest") goes straight
        # to its corrections. Previously F7 always opened a "choose the misspelling"
        # chooser first, which showed no correction options and made spell check
        # look broken (#129). Multiple misspellings still use the chooser so each
        # can be reviewed in context.
        if len(misspellings) == 1:
            item = misspellings[0]
        else:
            selection = self._choose_misspelling_with_context(misspellings, text, dictionary)
            if selection == wx.NOT_FOUND:
                return
            item = misspellings[selection]
        suggestions = suggest_words(item.word, dictionary)
        if suggestions:
            with wx.SingleChoiceDialog(
                self.frame,
                f'Suggestions for "{item.word}":',
                "Spell Check",
                choices=suggestions,
            ) as suggestion_dialog:
                if self._show_modal_dialog(suggestion_dialog, "Spell Check") == wx.ID_OK:
                    replacement = suggestion_dialog.GetStringSelection()
                    if replacement:
                        self.editor.Replace(item.start, item.end, replacement)
                        self.document.set_text(self.editor.GetValue())
                        self._set_status(f'Replaced "{item.word}" with "{replacement}"')
                        return
        else:
            # Announce explicitly so screen-reader users aren't surprised
            # when the dialog jumps straight to "Add to dictionary".
            self._set_status(f'No suggestions for "{item.word}"')
            self._announce(f"No suggestions for {item.word}")
        scopes = ["Personal dictionary", "Document dictionary", "Project dictionary"]
        with wx.SingleChoiceDialog(
            self.frame,
            f'No suggestions found. Add "{item.word}" to dictionary scope?'
            if not suggestions
            else f'Add "{item.word}" to dictionary scope:',
            "Spell Check",
            choices=scopes,
        ) as scope_dialog:
            if self._show_modal_dialog(scope_dialog, "Spell Check") != wx.ID_OK:
                self._set_status("Spell check reviewed")
                return
            scope = scope_dialog.GetSelection()
        if scope == wx.NOT_FOUND:
            self._set_status("Spell check reviewed")
            return
        self._add_word_to_dictionary_scope(item.word, scope)

    def _choose_misspelling_with_context(
        self,
        misspellings: list[Misspelling],
        text: str,
        dictionary: set[str],
    ) -> int:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Spell Check", size=(860, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Choose a misspelled word, then Show Corrections to see replacement "
                    "options. Tab to Context to read the nearby sentence; use Speak Word to "
                    "hear the word and its spelling."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        choices = []
        for item in misspellings:
            line, column = line_column_for_position(text, item.start)
            choices.append(f"{item.word} (Ln {line}, Col {column})")
        chooser = wx.ListBox(dialog, choices=choices)
        chooser.SetSelection(0 if choices else wx.NOT_FOUND)
        root.Add(chooser, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        root.Add(wx.StaticText(dialog, label="Context"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        context_field = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        root.Add(context_field, 1, wx.ALL | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        speak_button = wx.Button(dialog, label="Speak Word")
        review_button = wx.Button(dialog, id=wx.ID_OK, label="Show Corrections...")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
        buttons.AddStretchSpacer(1)
        buttons.Add(speak_button, 0, wx.RIGHT, 8)
        buttons.Add(review_button, 0, wx.RIGHT, 8)
        buttons.Add(cancel_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizerAndFit(root)
        review_button.SetDefault()

        def refresh_context() -> None:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND:
                context_field.SetValue("")
                return
            item = misspellings[selection]
            context_field.SetValue(self._misspelling_context_text(text, item))

        chooser.Bind(wx.EVT_LISTBOX, lambda _event: refresh_context())
        speak_button.Bind(
            wx.EVT_BUTTON,
            lambda _event: (
                self._speak_spellcheck_word(
                    misspellings[chooser.GetSelection()].word,
                    suggest_words(misspellings[chooser.GetSelection()].word, dictionary),
                )
                if chooser.GetSelection() != wx.NOT_FOUND
                else self._set_status("Select a misspelling to speak")
            ),
        )
        review_button.Bind(wx.EVT_BUTTON, lambda _event: dialog.EndModal(wx.ID_OK))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _event: dialog.EndModal(wx.ID_CANCEL))
        refresh_context()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        result = self._show_modal_dialog(dialog, "Spell Check")
        selection = chooser.GetSelection()
        dialog.Destroy()
        if result != wx.ID_OK:
            return wx.NOT_FOUND
        return selection

    def _misspelling_context_text(self, text: str, item: Misspelling) -> str:
        if not text:
            return item.word
        boundaries = ".!?\n"
        start = item.start
        end = item.end
        sentence_start = 0
        for marker in boundaries:
            position = text.rfind(marker, 0, start)
            if position > sentence_start:
                sentence_start = position
        if sentence_start > 0:
            sentence_start += 1
        sentence_end = len(text)
        for marker in boundaries:
            position = text.find(marker, end)
            if position != -1:
                sentence_end = min(sentence_end, position + 1)
        sentence = text[sentence_start:sentence_end].strip()
        if not sentence:
            window = 80
            excerpt_start = max(0, start - window)
            excerpt_end = min(len(text), end + window)
            sentence = text[excerpt_start:excerpt_end].strip()
            if excerpt_start > 0:
                sentence = f"...{sentence}"
            if excerpt_end < len(text):
                sentence = f"{sentence}..."
        return sentence or item.word

    def _speak_spellcheck_word(self, word: str, suggestions: list[str]) -> None:
        single_suggestion = suggestions[0] if len(suggestions) == 1 else None
        message = self._spellcheck_speech_message(word, single_suggestion)
        self._speak_with_announcement_backend(message)
        if single_suggestion is None:
            self._set_status(f'Spoke misspelling "{word}" and spelling')
        else:
            self._set_status(
                f'Spoke misspelling "{word}" and single suggestion "{single_suggestion}"'
            )

    def _spellcheck_speech_message(self, word: str, single_suggestion: str | None = None) -> str:
        parts = [
            f'Misspelled word: "{word}".',
            f"Spelling: {self._spell_word_for_speech(word)}.",
        ]
        if single_suggestion is not None:
            parts.append(f'Only suggestion: "{single_suggestion}".')
            parts.append(f"Suggestion spelling: {self._spell_word_for_speech(single_suggestion)}.")
        return " ".join(parts)

    def _spell_word_for_speech(self, word: str) -> str:
        if not word:
            return "empty"
        spoken_letters: list[str] = []
        for character in word:
            if character == "-":
                spoken_letters.append("dash")
            elif character == "_":
                spoken_letters.append("underscore")
            elif character == "'":
                spoken_letters.append("apostrophe")
            elif character.isspace():
                spoken_letters.append("space")
            else:
                spoken_letters.append(character.upper())
        return ", ".join(spoken_letters)

    def _speak_with_announcement_backend(self, message: str) -> None:
        backend = getattr(self, "_announcement_engine", None)
        if backend is not None:
            backend_error = backend.announce(message)
            if backend_error and backend_error != self._announcement_error_reported:
                self._announcement_error_reported = backend_error
                self._record_notification(backend_error, "accessibility")
            if backend_error is None and backend.state().active_backend in {"prism", "speech"}:
                return
        announce(message)

    def open_misspelling_list(self) -> None:
        dictionary = self._spell_dictionary()
        misspellings = list_misspellings(self.editor.GetValue(), dictionary)
        if not misspellings:
            self._set_status("No misspellings found")
            return
        nodes = self._build_misspelling_navigator_nodes(misspellings)
        selected = self._show_tree_navigator(
            title="Misspelling List",
            root_label="Misspellings",
            nodes=nodes,
        )
        if not isinstance(selected, Misspelling):
            self._set_status("Misspelling list cancelled")
            return
        self._record_location_before_jump()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(selected.start)
        else:
            self.editor.SetInsertionPoint(selected.start)
            self.editor.SetSelection(selected.start, selected.end)
        self.editor.SetFocus()
        self._location_ring.record(selected.start)
        self._set_status(f'Jumped to misspelling "{selected.word}"')

    def next_misspelling(self) -> None:
        dictionary = self._spell_dictionary()
        cursor = self.editor.GetInsertionPoint()
        item = find_next_misspelling(self.editor.GetValue(), cursor, dictionary)
        if item is None:
            self._set_status("No next misspelling")
            return
        self._record_location_before_jump()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(item.start)
        else:
            self.editor.SetInsertionPoint(item.start)
            self.editor.SetSelection(item.start, item.end)
        self.editor.SetFocus()
        self._set_status(f'Next misspelling: "{item.word}"')

    def previous_misspelling(self) -> None:
        dictionary = self._spell_dictionary()
        cursor = self.editor.GetInsertionPoint()
        item = find_previous_misspelling(self.editor.GetValue(), cursor, dictionary)
        if item is None:
            self._set_status("No previous misspelling")
            return
        self._record_location_before_jump()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(item.start)
        else:
            self.editor.SetInsertionPoint(item.start)
            self.editor.SetSelection(item.start, item.end)
        self.editor.SetFocus()
        self._set_status(f'Previous misspelling: "{item.word}"')

    def show_thesaurus(self) -> None:
        """Open the thesaurus for the selected word or the word under the caret."""
        wx = self._wx
        if not thesaurus_engine.is_available():
            message = (
                "The thesaurus data file is not installed.\n\n"
                f"Expected location:\n  {thesaurus_engine.data_path()}\n\n"
                "To enable the thesaurus, install the optional English thesaurus "
                "data file (LibreOffice MyThes en_US, ~18 MB). Reinstall Quill "
                "with the thesaurus component, or copy 'th_en_US_v2.dat' into "
                "the data folder shown above."
            )
            self._show_message_box(message, "Thesaurus Not Installed", wx.ICON_INFORMATION | wx.OK)
            self._set_status("Thesaurus data not installed")
            return

        # Determine the word to look up: selection takes priority, else the
        # word at the caret.
        text = self.editor.GetValue()
        sel_start, sel_end = self.editor.GetSelection()
        word: str | None = None
        word_start: int | None = None
        word_end: int | None = None
        if sel_end > sel_start:
            candidate = text[sel_start:sel_end].strip()
            if candidate and all(ch.isalpha() or ch == "'" for ch in candidate):
                word = candidate
                word_start = sel_start
                word_end = sel_end
        if word is None:
            located = thesaurus_engine.word_at(text, self.editor.GetInsertionPoint())
            if located is not None:
                word, word_start, word_end = located

        if not word:
            with wx.TextEntryDialog(
                self.frame,
                "Look up word in thesaurus:",
                "Thesaurus",
                value="",
            ) as dialog:
                if self._show_modal_dialog(dialog, "Thesaurus") != wx.ID_OK:
                    return
                word = dialog.GetValue().strip()
                if not word:
                    self._set_status("Thesaurus: no word entered")
                    return

        entry = thesaurus_engine.lookup(word)
        if entry is None:
            self._set_status(f'No thesaurus entry for "{word}"')
            self._show_message_box(
                f'No thesaurus entries were found for "{word}".',
                "Thesaurus",
                wx.ICON_INFORMATION | wx.OK,
            )
            return

        # Build a flat choice list grouped by part of speech so screen
        # readers announce the grouping naturally.
        choices: list[str] = []
        choice_words: list[str] = []
        for meaning in entry.meanings:
            pos = meaning.part_of_speech or "other"
            for synonym in meaning.synonyms:
                choices.append(f"[{pos}] {synonym}")
                choice_words.append(synonym)

        if not choices:
            self._set_status(f'No synonyms available for "{word}"')
            return

        replace_allowed = word_start is not None and word_end is not None
        prompt = f'Synonyms for "{word}":\n\nChoose one to copy to the clipboard' + (
            " or replace the word in the editor." if replace_allowed else "."
        )

        with wx.SingleChoiceDialog(
            self.frame,
            prompt,
            "Thesaurus",
            choices=choices,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Thesaurus") != wx.ID_OK:
                self._set_status("Thesaurus closed")
                return
            selection = dialog.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        chosen = choice_words[selection]

        if replace_allowed:
            actions = ["Replace word in editor", "Copy to clipboard"]
            with wx.SingleChoiceDialog(
                self.frame,
                f'Use "{chosen}":',
                "Thesaurus",
                choices=actions,
            ) as action_dialog:
                if self._show_modal_dialog(action_dialog, "Thesaurus") != wx.ID_OK:
                    return
                action = action_dialog.GetSelection()
        else:
            action = 1  # copy to clipboard

        if action == 0 and replace_allowed:
            # Preserve the original word's leading capitalisation.
            replacement = chosen
            if word[:1].isupper():
                replacement = chosen[:1].upper() + chosen[1:]
            self.editor.Replace(word_start, word_end, replacement)
            self.document.set_text(self.editor.GetValue())
            self._set_status(f'Replaced "{word}" with "{replacement}"')
        else:
            self._copy_text_to_clipboard(chosen)
            self._set_status(f'Copied "{chosen}" to clipboard')

    def _copy_text_to_clipboard(self, text: str) -> bool:
        wx = self._wx
        clipboard = wx.TheClipboard
        if not clipboard.Open():
            self._set_status("Clipboard is unavailable")
            return False
        try:
            clipboard.SetData(wx.TextDataObject(text))
            # Flush so the data survives if the app exits soon after.
            try:
                clipboard.Flush()
            except Exception:
                pass
            return True
        finally:
            clipboard.Close()

    def _announce_spellcheck_hint(self) -> None:
        if not getattr(self.settings, "announce_spelling", True):
            self._last_live_misspelling_feedback = None
            return
        dictionary = self._spell_dictionary()
        cursor = self.editor.GetInsertionPoint()
        item = find_next_misspelling(self.editor.GetValue(), cursor - 1, dictionary)
        if item is None or item.start != cursor:
            self._last_live_misspelling_feedback = None
            return
        key = (item.word.lower(), item.start, item.end)
        now = time.monotonic()
        if (
            self._last_live_misspelling_feedback == key
            and now - self._last_live_misspelling_feedback_at < 0.75
        ):
            return
        self._last_live_misspelling_feedback = key
        self._last_live_misspelling_feedback_at = now
        bell = getattr(self._wx, "Bell", None)
        if callable(bell):
            bell()
        self._set_status(f'Possible misspelling: "{item.word}"')

    def _spell_dictionary(self) -> set[str]:
        # Cache the combined dictionary keyed by (document path, project root).
        # Reading + parsing the three JSON scope files on every keystroke (via
        # "spell check as you type") is wasteful; we invalidate the cache when
        # a word is added or the active document changes.
        project_root = Path.cwd()
        cache_key = (self.document.path, project_root)
        cached = getattr(self, "_spell_dictionary_cache", None)
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        dictionary = load_combined_dictionary(self.document.path, project_root)
        self._spell_dictionary_cache = (cache_key, dictionary)
        return dictionary

    def _invalidate_spell_dictionary_cache(self) -> None:
        self._spell_dictionary_cache = None

    def _add_word_to_dictionary_scope(self, word: str, scope_index: int) -> None:
        if scope_index == 0:
            add_word_to_scope(word, "personal", self.document.path, Path.cwd())
        elif scope_index == 1:
            add_word_to_scope(word, "document", self.document.path, Path.cwd())
        elif scope_index == 2:
            add_word_to_scope(word, "project", self.document.path, Path.cwd())
        else:
            return
        self._invalidate_spell_dictionary_cache()
        self._set_status(f'Added "{word}" to dictionary')

    def open_epub_navigator(self) -> None:
        if self.document.path is None or self.document.path.suffix.lower() != ".epub":
            self._set_status("Open an EPUB file to use EPUB Navigator")
            return
        from quill.core.epub import load_epub_book

        book = self._epub_book or load_epub_book(self.document.path)
        nodes = self._build_epub_navigator_nodes(book)
        if not nodes:
            self._set_status("EPUB has no navigable chapters")
            return
        selected = self._show_tree_navigator(
            title=f"Navigator - {book.title}",
            root_label=book.title,
            nodes=nodes,
        )
        if not isinstance(selected, _EpubNavigatorTarget):
            self._set_status("Closed EPUB Navigator")
            return
        chapter_index = selected.chapter_index
        if chapter_index < 0 or chapter_index >= len(book.chapters):
            self._set_status("Closed EPUB Navigator")
            return
        chapter = book.chapters[chapter_index]
        chapter_text = self._render_epub_chapter_text(chapter)
        self._create_document_tab(
            Document(text=chapter_text, path=None, modified=False),
            select=True,
        )
        target_position = 0
        status = f'Opened chapter "{chapter.title}" from EPUB navigator'
        if selected.heading_index is not None and 0 <= selected.heading_index < len(
            chapter.headings
        ):
            heading = chapter.headings[selected.heading_index]
            target_position = self._find_heading_position(
                chapter_text,
                heading.title,
                selected.heading_index,
            )
            status = f'Jumped to heading "{heading.title}" in chapter "{chapter.title}"'
        self.editor.SetInsertionPoint(target_position)
        self.editor.SetSelection(target_position, target_position)
        self.editor.SetFocus()
        self._refresh_title()
        self._set_status(status)

    def _find_heading_position(
        self,
        chapter_text: str,
        heading_title: str,
        heading_index: int,
    ) -> int:
        occurrences = 0
        search_from = 0
        while True:
            position = chapter_text.find(heading_title, search_from)
            if position == -1:
                return 0
            if occurrences == heading_index:
                return position
            occurrences += 1
            search_from = position + len(heading_title)

    def toggle_read_aloud(self) -> None:
        wx = self._wx
        state = self._read_aloud.state
        if state == "playing":
            self._read_aloud.pause()
            self._set_status("Read aloud paused")
            return
        text = self.editor.GetValue()
        if state == "paused":
            start = self._read_aloud.cursor
            end = None
        else:
            start, end = self.editor.GetSelection()
            if start == end:
                start = self.editor.GetInsertionPoint()
                end = None
        try:
            read_aloud_engine = self.settings.read_aloud_engine.strip().lower() or "pyttsx3"
            self._read_aloud.start(
                text,
                start,
                self.settings.read_aloud_voice,
                engine_name=read_aloud_engine,
                rate=self.settings.read_aloud_rate,
                volume=self.settings.read_aloud_volume / 100.0,
                pitch=self.settings.read_aloud_pitch,
                dectalk_executable=self.settings.read_aloud_dectalk_executable,
                dectalk_voice=self.settings.read_aloud_dectalk_voice,
                dectalk_rate=self.settings.read_aloud_dectalk_rate,
                dectalk_dictionary=self.settings.read_aloud_dectalk_dictionary,
                end=end,
                piper_executable=self.settings.read_aloud_piper_executable,
                piper_model=self.settings.read_aloud_piper_model,
                kokoro_voice=self.settings.read_aloud_kokoro_voice,
                kokoro_speed=self.settings.read_aloud_kokoro_speed,
                espeak_executable=self.settings.read_aloud_espeak_executable,
                espeak_voice=self.settings.read_aloud_espeak_voice,
                espeak_rate=self.settings.read_aloud_espeak_rate,
                openvoice_executable=self.settings.read_aloud_openvoice_executable,
                openvoice_voice=self.settings.read_aloud_openvoice_voice,
                openvoice_rate=self.settings.read_aloud_openvoice_rate,
                openvoice_consent=self.settings.read_aloud_openvoice_consent,
                sentence_pause_ms=self.settings.read_aloud_sentence_pause_ms,
                punctuation_level=self.settings.announce_punctuation_level,
                on_progress=lambda progress_start, progress_end: self._wx.CallAfter(
                    self._on_read_aloud_progress,
                    progress_start,
                    progress_end,
                ),
                on_state_change=lambda next_state: self._wx.CallAfter(
                    self._on_read_aloud_state_change,
                    next_state,
                ),
                on_error=lambda error: self._wx.CallAfter(self._on_read_aloud_error, error),
            )
        except ReadAloudUnavailableError as exc:
            self._show_message_box(
                str(exc),
                "Read Aloud",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        self._set_status("Read aloud started")

    def stop_read_aloud(self) -> None:
        self._read_aloud.stop()
        self._set_status("Read aloud stopped")

    def _voice_is_english(self, engine: str, voice: ReadAloudVoiceOption) -> bool:
        engine_name = (engine or "").strip().lower()
        voice_id = (voice.id or "").strip().lower()
        voice_name = (voice.name or "").strip().lower()

        if engine_name in {
            "dectalk",
            "kokoro",
            "espeak",
            "openvoice",
        }:
            return True

        if engine_name == "pyttsx3":
            english_markers = ("english", "en-", " en", "_en", "en_us", "en_gb", "enu")
            return any(marker in voice_id or marker in voice_name for marker in english_markers)

        if engine_name == "piper":
            return (
                "en" in voice_id
                or "english" in voice_id
                or "en" in voice_name
                or "english" in voice_name
            )

        return True

    def _english_only_voices(
        self, engine: str, voices: list[ReadAloudVoiceOption]
    ) -> list[ReadAloudVoiceOption]:
        return [voice for voice in voices if self._voice_is_english(engine, voice)]

    # ------------------------------------------------------------------
    # Voice preview and settings for the supported read-aloud engines
    # ------------------------------------------------------------------

    _PREVIEW_TEXT = "Hello, this is a voice preview. The quick brown fox jumps over the lazy dog."

    def _voice_preview_catalog_roots(self) -> list[Path]:
        roots: list[Path] = []
        app_root_raw = os.environ.get("QUILL_APP_ROOT", "").strip()
        if app_root_raw:
            app_root = Path(app_root_raw)
            roots.append(app_root / "quill" / "data" / "voice-previews")
            roots.append(app_root / "tools" / "speech" / "previews")
        roots.append(Path(__file__).resolve().parents[1] / "data" / "voice-previews")
        roots.append(app_data_dir() / "speech" / "previews")
        deduped: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            marker = str(root).lower()
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(root)
        return deduped

    def _voice_preview_sample_path(self, engine: str, voice_id: str) -> Path | None:
        safe_engine = (engine or "").strip().lower()
        safe_voice = (voice_id or "").strip()
        if not safe_engine or not safe_voice:
            return None
        for root in self._voice_preview_catalog_roots():
            provider_dir = root / safe_engine
            if not provider_dir.exists():
                continue
            for extension in (".wav", ".mp3"):
                candidate = provider_dir / f"{safe_voice}{extension}"
                if candidate.exists():
                    return candidate
        return None

    def _voice_preview_voice_ids(self, engine: str) -> list[str]:
        safe_engine = (engine or "").strip().lower()
        if not safe_engine:
            return []
        discovered: set[str] = set()
        for root in self._voice_preview_catalog_roots():
            provider_dir = root / safe_engine
            if not provider_dir.exists():
                continue
            for candidate in provider_dir.glob("*.wav"):
                discovered.add(candidate.stem)
            for candidate in provider_dir.glob("*.mp3"):
                discovered.add(candidate.stem)
        return sorted(discovered)

    def _play_preview_asset(self, sample_path: Path) -> None:
        suffix = sample_path.suffix.lower()
        if suffix == ".wav" and _winsound is not None:
            _winsound.PlaySound(str(sample_path), _winsound.SND_FILENAME)
            return
        raise ReadAloudUnavailableError("Preview sample playback supports WAV files.")

    def _preview_voice(self, engine: str, voice_id: str) -> None:
        """Play a short preview of *voice_id* through *engine* on a background thread."""
        import tempfile as _tmpfile
        from pathlib import Path as _Path

        sample = self._PREVIEW_TEXT
        s = self.settings

        def _work(_progress: Callable[[str, int, int], None]) -> object:
            preview_sample = self._voice_preview_sample_path(engine, voice_id)
            if preview_sample is not None:
                self._play_preview_asset(preview_sample)
                return None
            with _tmpfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
                wav = _Path(fh.name)
            try:
                if engine == "pyttsx3":
                    synthesize_to_file_with_pyttsx3(
                        sample,
                        wav,
                        voice=voice_id,
                        rate=s.read_aloud_rate,
                        volume=s.read_aloud_volume / 100.0,
                    )
                elif engine == "dectalk":
                    exe = discover_dectalk_executable(s.read_aloud_dectalk_executable)
                    if exe is None:
                        raise ReadAloudUnavailableError("DECtalk executable not configured")
                    synthesize_to_file_with_dectalk(
                        sample,
                        wav,
                        executable_path=exe,
                        voice=voice_id,
                        rate=s.read_aloud_dectalk_rate,
                    )
                elif engine == "piper":
                    exe = discover_piper_executable(s.read_aloud_piper_executable)
                    if exe is None:
                        raise ReadAloudUnavailableError("Piper executable not configured")
                    synthesize_with_piper(
                        sample,
                        wav,
                        executable_path=exe,
                        model_path=_Path(voice_id),
                    )
                elif engine == "kokoro":
                    synthesize_with_kokoro(
                        sample,
                        wav,
                        voice=voice_id,
                        speed=s.read_aloud_kokoro_speed,
                    )
                elif engine == "espeak":
                    exe = discover_espeak_executable(s.read_aloud_espeak_executable)
                    if exe is None:
                        raise ReadAloudUnavailableError("eSpeak-NG not found")
                    synthesize_with_espeak(
                        sample,
                        wav,
                        executable_path=exe,
                        voice=voice_id,
                        rate=s.read_aloud_espeak_rate,
                    )
                elif engine == "openvoice":
                    if not s.read_aloud_openvoice_consent:
                        raise ReadAloudUnavailableError(
                            "OpenVoice requires explicit consent in Read Aloud Settings"
                        )
                    exe = discover_openvoice_executable(s.read_aloud_openvoice_executable)
                    if exe is None:
                        raise ReadAloudUnavailableError("OpenVoice executable not configured")
                    synthesize_with_openvoice(
                        sample,
                        wav,
                        executable_path=exe,
                        voice=voice_id,
                        rate=s.read_aloud_openvoice_rate,
                    )
                else:
                    raise ReadAloudUnavailableError(f"Unknown engine: {engine}")
                # Play via the existing read-aloud controller so pause/stop work
                import threading as _threading

                done = _threading.Event()

                def _on_state(st: str) -> None:
                    if st in ("idle", "error"):
                        done.set()

                self._read_aloud.start(
                    sample,
                    0,
                    voice_id,
                    engine_name=engine,
                    dectalk_executable=s.read_aloud_dectalk_executable,
                    dectalk_voice=voice_id if engine == "dectalk" else s.read_aloud_dectalk_voice,
                    dectalk_rate=s.read_aloud_dectalk_rate,
                    dectalk_dictionary=s.read_aloud_dectalk_dictionary,
                    piper_executable=s.read_aloud_piper_executable,
                    piper_model=voice_id if engine == "piper" else s.read_aloud_piper_model,
                    kokoro_voice=voice_id if engine == "kokoro" else s.read_aloud_kokoro_voice,
                    kokoro_speed=s.read_aloud_kokoro_speed,
                    espeak_executable=s.read_aloud_espeak_executable,
                    espeak_voice=voice_id if engine == "espeak" else s.read_aloud_espeak_voice,
                    espeak_rate=s.read_aloud_espeak_rate,
                    openvoice_executable=s.read_aloud_openvoice_executable,
                    openvoice_voice=voice_id
                    if engine == "openvoice"
                    else s.read_aloud_openvoice_voice,
                    openvoice_rate=s.read_aloud_openvoice_rate,
                    openvoice_consent=s.read_aloud_openvoice_consent,
                    on_state_change=lambda st: done.set() if st in ("idle", "error") else None,
                )
                done.wait(timeout=15)
            finally:
                try:
                    wav.unlink(missing_ok=True)
                except OSError:
                    pass
            return None

        self._run_background_task(
            f"Previewing {engine} voice",
            _work,
            lambda _r: self._set_status("Preview finished"),
        )

    def choose_read_aloud_voice(self) -> None:  # noqa: PLR0912
        wx = self._wx
        engine = self.settings.read_aloud_engine.strip().lower() or "pyttsx3"

        if (
            engine == "dectalk"
            and discover_dectalk_executable(self.settings.read_aloud_dectalk_executable) is None
        ):
            self._show_message_box(
                "DECtalk is not installed/configured.",
                "Read Aloud Voice",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        if (
            engine == "espeak"
            and discover_espeak_executable(self.settings.read_aloud_espeak_executable) is None
        ):
            self._show_message_box(
                "eSpeak-NG is not installed/configured.",
                "Read Aloud Voice",
                wx.ICON_INFORMATION | wx.OK,
            )
            return

        if engine == "dectalk":
            voices = list_dectalk_voices()
            current_voice_id = self.settings.read_aloud_dectalk_voice
        elif engine == "piper":
            voices = list_piper_voices(self.settings.read_aloud_piper_model_dir)
            if not voices:
                voices = [
                    ReadAloudVoiceOption(id=voice_id, name=f"{voice_id} (preview sample)")
                    for voice_id in self._voice_preview_voice_ids("piper")
                ]
            current_voice_id = self.settings.read_aloud_piper_model
        elif engine == "kokoro":
            voices = list_kokoro_voices()
            current_voice_id = self.settings.read_aloud_kokoro_voice
        elif engine == "espeak":
            voices = list_espeak_english_voices()
            current_voice_id = self.settings.read_aloud_espeak_voice
        elif engine == "openvoice":
            voices = list_openvoice_english_voices()
            current_voice_id = self.settings.read_aloud_openvoice_voice
        else:
            voices = list_voices()
            current_voice_id = self.settings.read_aloud_voice

        voices = self._english_only_voices(engine, voices)

        if not voices:
            self._show_message_box(
                "No English voices were found for this engine.",
                "Read Aloud Voice",
                wx.ICON_INFORMATION | wx.OK,
            )
            return

        dialog = wx.Dialog(self.frame, title="Read Aloud Voice", size=(640, 460))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=f"Choose an English voice for {engine}. Use Preview before confirming.",
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        choices = [v.name for v in voices]
        list_box = wx.ListBox(dialog, choices=choices, style=wx.LB_SINGLE)
        current_index = next((i for i, v in enumerate(voices) if v.id == current_voice_id), 0)
        if choices:
            list_box.SetSelection(current_index)
        root.Add(list_box, 1, wx.EXPAND | wx.ALL, 8)
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        preview_btn = wx.Button(dialog, label="&Preview")
        ok_btn = wx.Button(dialog, id=wx.ID_OK)
        cancel_btn = wx.Button(dialog, id=wx.ID_CANCEL)
        button_row.AddStretchSpacer(1)
        button_row.Add(preview_btn, 0, wx.RIGHT, 8)
        button_row.Add(ok_btn, 0, wx.RIGHT, 8)
        button_row.Add(cancel_btn, 0)
        root.Add(button_row, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizerAndFit(root)

        def _selected_index() -> int:
            return list_box.GetSelection()

        def _on_preview(_evt: wx.CommandEvent) -> None:
            idx = _selected_index()
            if 0 <= idx < len(voices):
                self._preview_voice(engine, voices[idx].id)

        preview_btn.Bind(wx.EVT_BUTTON, _on_preview)
        try:
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Read Aloud Voice") != wx.ID_OK:
                self._set_status("Read aloud voice selection cancelled")
                return
            selected = _selected_index()
        finally:
            dialog.Destroy()

        if selected < 0 or selected >= len(voices):
            return
        if engine == "dectalk":
            self.settings.read_aloud_dectalk_voice = voices[selected].id
        elif engine == "piper":
            self.settings.read_aloud_piper_model = voices[selected].id
        elif engine == "kokoro":
            self.settings.read_aloud_kokoro_voice = voices[selected].id
        elif engine == "espeak":
            self.settings.read_aloud_espeak_voice = voices[selected].id
        elif engine == "openvoice":
            self.settings.read_aloud_openvoice_voice = voices[selected].id
        else:
            self.settings.read_aloud_voice = voices[selected].id
        save_settings(self.settings)
        self._set_status(f"Selected voice: {voices[selected].name}")

    def choose_read_aloud_settings(self) -> None:  # noqa: PLR0912,PLR0915
        wx = self._wx
        _TITLE = "Read Aloud Settings"
        dectalk_available = (
            discover_dectalk_executable(self.settings.read_aloud_dectalk_executable) is not None
        )
        espeak_available = (
            discover_espeak_executable(self.settings.read_aloud_espeak_executable) is not None
        )
        engine_options = [
            ("Pyttsx3 (System TTS)", "pyttsx3"),
            ("DECtalk", "dectalk"),
            ("Piper (neural, offline)", "piper"),
            ("Kokoro (neural, offline)", "kokoro"),
            ("eSpeak-NG (English variants)", "espeak"),
            ("OpenVoice (advanced style module)", "openvoice"),
        ]
        engine_options = [
            option
            for option in engine_options
            if option[1] not in {"dectalk", "espeak"}
            or (option[1] == "dectalk" and dectalk_available)
            or (option[1] == "espeak" and espeak_available)
        ]
        engine_choices = [label for label, _ in engine_options]
        engine_values = [value for _, value in engine_options]
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose read-aloud engine:",
            _TITLE,
            choices=engine_choices,
        ) as engine_dialog:
            current_engine = self.settings.read_aloud_engine.strip().lower() or "pyttsx3"
            if current_engine not in engine_values:
                current_engine = "pyttsx3"
            current_index = (
                engine_values.index(current_engine) if current_engine in engine_values else 0
            )
            engine_dialog.SetSelection(current_index)
            if self._show_modal_dialog(engine_dialog, _TITLE) != wx.ID_OK:
                self._set_status("Read aloud settings cancelled")
                return
            selected_engine = engine_values[engine_dialog.GetSelection()]
        self.settings.read_aloud_engine = selected_engine

        def _ask_text(prompt: str, current: str) -> str | None:
            with wx.TextEntryDialog(self.frame, prompt, _TITLE, value=current) as d:
                if self._show_modal_dialog(d, _TITLE) != wx.ID_OK:
                    return None
                return d.GetValue().strip()

        def _ask_int(prompt: str, current: int, lo: int, hi: int) -> int | None:
            val = _ask_text(f"{prompt} ({lo}–{hi}):", str(current))
            if val is None:
                return None
            try:
                return max(lo, min(hi, int(val)))
            except ValueError:
                return current

        def _ask_float(prompt: str, current: float, lo: float, hi: float) -> float | None:
            val = _ask_text(f"{prompt} ({lo:.1f}–{hi:.1f}):", f"{current:.2f}")
            if val is None:
                return None
            try:
                return max(lo, min(hi, float(val)))
            except ValueError:
                return current

        # ---- per-engine settings ----
        if selected_engine == "pyttsx3":
            v = _ask_int("Speaking rate (words per minute)", self.settings.read_aloud_rate, 80, 450)
            if v is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_rate = v
            v2 = _ask_int("Volume (0–100)", self.settings.read_aloud_volume, 0, 100)
            if v2 is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_volume = v2
            v3 = _ask_int("Pitch (0–100)", self.settings.read_aloud_pitch, 0, 100)
            if v3 is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_pitch = v3

        elif selected_engine == "dectalk":
            exe = _ask_text(
                "Path to DECtalk speak.exe:", self.settings.read_aloud_dectalk_executable
            )
            if exe is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_dectalk_executable = exe
            dic = _ask_text(
                "Optional path to dtalk_us.dic (leave blank to auto-detect):",
                self.settings.read_aloud_dectalk_dictionary,
            )
            if dic is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_dectalk_dictionary = dic
            v = _ask_int("Speaking rate", self.settings.read_aloud_dectalk_rate, 75, 650)
            if v is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_dectalk_rate = v

        elif selected_engine == "piper":
            exe = _ask_text("Path to piper.exe:", self.settings.read_aloud_piper_executable)
            if exe is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_piper_executable = exe
            model_dir = _ask_text(
                "Directory containing Piper .onnx model files (for voice list):",
                self.settings.read_aloud_piper_model_dir,
            )
            if model_dir is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_piper_model_dir = model_dir

        elif selected_engine == "kokoro":
            v = _ask_float(
                "Speaking speed multiplier", self.settings.read_aloud_kokoro_speed, 0.5, 2.0
            )
            if v is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_kokoro_speed = v

        elif selected_engine == "espeak":
            exe = _ask_text(
                "Path to espeak-ng.exe (leave blank to use PATH):",
                self.settings.read_aloud_espeak_executable,
            )
            if exe is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_espeak_executable = exe
            v = _ask_int(
                "Speaking rate (words per minute)", self.settings.read_aloud_espeak_rate, 80, 450
            )
            if v is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_espeak_rate = v

        elif selected_engine == "openvoice":
            exe = _ask_text(
                "Path to OpenVoice executable:", self.settings.read_aloud_openvoice_executable
            )
            if exe is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_openvoice_executable = exe
            v = _ask_int("Speaking rate", self.settings.read_aloud_openvoice_rate, 80, 450)
            if v is None:
                self._set_status("Read aloud settings cancelled")
                return
            self.settings.read_aloud_openvoice_rate = v
            consent = self._show_message_box(
                "OpenVoice can apply advanced voice style transforms. "
                "Enable this only if you consent\n"
                "to advanced style processing workflows for this machine.",
                _TITLE,
                wx.YES_NO | wx.ICON_QUESTION,
            )
            self.settings.read_aloud_openvoice_consent = consent == wx.YES

        # Always offer a preview of the current voice with new settings
        current_voice = {
            "pyttsx3": self.settings.read_aloud_voice,
            "dectalk": self.settings.read_aloud_dectalk_voice,
            "piper": self.settings.read_aloud_piper_model,
            "kokoro": self.settings.read_aloud_kokoro_voice,
            "espeak": self.settings.read_aloud_espeak_voice,
            "openvoice": self.settings.read_aloud_openvoice_voice,
        }.get(selected_engine, "")
        with wx.MessageDialog(
            self.frame,
            f"Settings saved for {engine_choices[engine_values.index(selected_engine)]}.\n\n"
            "Would you like to hear a preview with the current voice?",
            _TITLE,
            wx.YES_NO | wx.ICON_QUESTION,
        ) as confirm:
            save_settings(self.settings)
            if self._show_modal_dialog(confirm, _TITLE) == wx.ID_YES:
                self._preview_voice(selected_engine, current_voice)
        engine_label = engine_choices[engine_values.index(selected_engine)]
        self._set_status(f"Read aloud engine set to {engine_label}")

    def generate_speech_audio(self) -> None:  # noqa: PLR0912,PLR0915
        wx = self._wx
        _TITLE = "Generate Speech Audio"
        if not self._document_tabs:
            self._set_status("No document open")
            return
        text = self.editor.GetStringSelection().strip() or self.editor.GetValue().strip()
        if not text:
            self._set_status("Nothing to synthesize")
            return

        with wx.FileDialog(
            self.frame,
            _TITLE,
            wildcard="Wave file (*.wav)|*.wav|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if self._show_modal_dialog(dlg, _TITLE) != wx.ID_OK:
                self._set_status("Speech generation cancelled")
                return
            output_path = Path(dlg.GetPath())
        if output_path.suffix.lower() != ".wav":
            output_path = output_path.with_suffix(".wav")

        engine = self.settings.read_aloud_engine.strip().lower() or "pyttsx3"
        s = self.settings

        # Resolve / prompt for engine-specific paths before background work
        if engine == "piper":
            exe = discover_piper_executable(s.read_aloud_piper_executable)
            if exe is None:
                with wx.TextEntryDialog(
                    self.frame, "Path to piper.exe:", _TITLE, value=s.read_aloud_piper_executable
                ) as d:
                    if self._show_modal_dialog(d, _TITLE) != wx.ID_OK:
                        self._set_status("Speech generation cancelled")
                        return
                    exe = discover_piper_executable(d.GetValue().strip())
                if exe is None:
                    self._show_message_box(
                        "Piper executable not found.", _TITLE, wx.ICON_ERROR | wx.OK
                    )
                    self._set_status("Speech generation cancelled")
                    return
                s.read_aloud_piper_executable = str(exe)
            model = Path(s.read_aloud_piper_model).expanduser()
            if not s.read_aloud_piper_model or not model.exists():
                with wx.FileDialog(
                    self.frame,
                    "Select Piper model (.onnx)",
                    wildcard="Piper model (*.onnx)|*.onnx|All files (*.*)|*.*",
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                ) as d:
                    if self._show_modal_dialog(d, _TITLE) != wx.ID_OK:
                        self._set_status("Speech generation cancelled")
                        return
                    model = Path(d.GetPath())
                s.read_aloud_piper_model = str(model)
            piper_exe_snap = exe
            piper_model_snap = model

        elif engine == "dectalk":
            exe = discover_dectalk_executable(s.read_aloud_dectalk_executable)
            if exe is None:
                self._show_message_box(
                    "DECtalk executable not found. Configure it in Read Aloud Settings.",
                    _TITLE,
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Speech generation cancelled")
                return
            dectalk_exe_snap = exe

        elif engine == "espeak":
            exe = discover_espeak_executable(s.read_aloud_espeak_executable)
            if exe is None:
                self._show_message_box(
                    "eSpeak-NG not found. Install it or configure the path in Read Aloud Settings.",
                    _TITLE,
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Speech generation cancelled")
                return
            espeak_exe_snap = exe

        elif engine == "openvoice":
            if not s.read_aloud_openvoice_consent:
                self._show_message_box(
                    "OpenVoice requires explicit consent in Read Aloud Settings.",
                    _TITLE,
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Speech generation cancelled")
                return
            exe = discover_openvoice_executable(s.read_aloud_openvoice_executable)
            if exe is None:
                self._show_message_box(
                    "OpenVoice executable not found. Configure it in Read Aloud Settings.",
                    _TITLE,
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Speech generation cancelled")
                return
            openvoice_exe_snap = exe

        save_settings(s)
        task_label = f"Generating speech audio ({output_path.name}) via {engine}"

        # Capture settings snapshot for the background thread
        _engine = engine
        _voice = s.read_aloud_voice
        _rate = s.read_aloud_rate
        _vol = s.read_aloud_volume / 100.0
        _dectalk_voice = s.read_aloud_dectalk_voice
        _dectalk_rate = s.read_aloud_dectalk_rate
        _kokoro_voice = s.read_aloud_kokoro_voice
        _kokoro_speed = s.read_aloud_kokoro_speed
        _espeak_voice = s.read_aloud_espeak_voice
        _espeak_rate = s.read_aloud_espeak_rate
        _openvoice_voice = s.read_aloud_openvoice_voice
        _openvoice_rate = s.read_aloud_openvoice_rate
        _out = output_path

        def work(progress: Callable[[str, int, int], None]) -> object:
            progress(f"Starting {_engine}", 0, 1)
            if _engine == "pyttsx3":
                synthesize_to_file_with_pyttsx3(
                    _out_text, _out, voice=_voice, rate=_rate, volume=_vol
                )
            elif _engine == "dectalk":
                synthesize_to_file_with_dectalk(
                    _out_text,
                    _out,
                    executable_path=dectalk_exe_snap,
                    voice=_dectalk_voice,
                    rate=_dectalk_rate,
                )
            elif _engine == "piper":
                synthesize_with_piper(
                    _out_text,
                    _out,
                    executable_path=piper_exe_snap,
                    model_path=piper_model_snap,
                )
            elif _engine == "kokoro":
                synthesize_with_kokoro(_out_text, _out, voice=_kokoro_voice, speed=_kokoro_speed)
            elif _engine == "espeak":
                synthesize_with_espeak(
                    _out_text,
                    _out,
                    executable_path=espeak_exe_snap,
                    voice=_espeak_voice,
                    rate=_espeak_rate,
                )
            elif _engine == "openvoice":
                synthesize_with_openvoice(
                    _out_text,
                    _out,
                    executable_path=openvoice_exe_snap,
                    voice=_openvoice_voice,
                    rate=_openvoice_rate,
                )
            progress("Finalizing output", 1, 1)
            return str(_out)

        _out_text = text

        def on_success(result: object) -> None:
            self._set_status(f"Speech generation complete: {Path(str(result)).name}")

        self._run_background_task(
            task_label,
            work,
            on_success,
            notify_on_success=True,
            notify_on_error=True,
            notification_category="speech",
        )

    def _on_read_aloud_progress(self, start: int, end: int) -> None:
        self.editor.SetSelection(start, end)
        self.editor.SetFocus()
        self._set_status("Read aloud speaking")

    def _on_read_aloud_state_change(self, state: str) -> None:
        if state == "paused":
            self._set_status("Read aloud paused")
        elif state == "error":
            self._set_status("Read aloud failed")
        else:
            self._set_status("Read aloud finished")

    def _on_read_aloud_error(self, error: str) -> None:
        self._set_status(f"Read aloud error: {error}")

    def toggle_dictation(self) -> None:
        wx = self._wx
        state = self._dictation.state
        if state == "listening":
            self._cancel_voice_command_scan()
            self._voice_command_baseline_text = ""
            self._dictation.stop()
            self._set_status("Windows dictation stopped")
            return

        self.editor.SetFocus()
        self._voice_command_baseline_text = self.editor.GetValue()
        try:
            self._dictation.start(DictationSettings())
        except DictationUnavailableError:
            self._show_message_box(
                "Windows dictation is unavailable on this system.",
                "Dictation",
                wx.ICON_INFORMATION | wx.OK,
            )
            self._voice_command_baseline_text = ""
            return
        if self.settings.voice_commands_enabled:
            self._set_status(
                'Windows dictation started. Say "Hey QUILL" plus a command to trigger Quill.'
            )
        else:
            self._set_status("Windows dictation started. Speak into the editor.")

    def toggle_dictation_voice_commands(self) -> None:
        """Open Settings at the Transcription tab where Hey QUILL commands can be toggled."""
        self.open_general_preferences()
        self._set_status("Hey QUILL commands setting is in Settings > Transcription")

    def _bw_include_parakeet_models(self) -> bool:
        if not self._feature_enabled("core.bw_parakeet"):
            return False
        return bool(getattr(self.settings, "bw_enable_parakeet_models", False))

    def show_bw_model_status(self) -> None:
        include_parakeet = self._bw_include_parakeet_models()
        models = bw_list_models(include_parakeet=include_parakeet)
        downloaded = bw_downloaded_model_ids(include_parakeet=include_parakeet)
        mode = str(getattr(self.settings, "bw_speech_selection_mode", "recommended"))
        current_model = str(getattr(self.settings, "bw_speech_model_id", "whisper-base"))
        recommended = bw_recommended_model_id(include_parakeet=include_parakeet)
        ok, engine_status = faster_whisper_status()
        status = [
            "BITS Whisperer Speech Model Status",
            "",
            bw_machine_guidance(),
            f"Selection mode: {mode}",
            f"Configured default: {current_model}",
            f"Recommended now: {recommended}",
            f"Installed models: {len(downloaded)} of {len(models)}",
            f"faster-whisper engine: {'Ready' if ok else 'Not installed'}",
            engine_status,
            "",
            "This is a phased rollout. Additional BITS Whisperer capabilities "
            "will arrive gradually.",
        ]
        self._show_message_box("\n".join(status), "BITS Whisperer Speech Models", self._wx.OK)
        self._set_status("BITS Whisperer speech model status shown")

    def apply_bw_recommended_model(self) -> None:
        model_id = bw_recommended_model_id(include_parakeet=self._bw_include_parakeet_models())
        self.settings.bw_speech_selection_mode = "recommended"
        self.settings.bw_speech_model_id = model_id
        save_settings(self.settings)
        self._set_status(f"Recommended mode active. Selected speech model: {model_id}")

    def toggle_bw_parakeet_visibility(self) -> None:
        self.settings.bw_enable_parakeet_models = not bool(
            getattr(self.settings, "bw_enable_parakeet_models", False)
        )
        save_settings(self.settings)
        item = self.frame.GetMenuBar().FindItemById(self._id_bw_toggle_parakeet)
        if item is not None:
            item.Check(self.settings.bw_enable_parakeet_models)
        state_text = "enabled" if self.settings.bw_enable_parakeet_models else "disabled"
        self._set_status(f"Parakeet model visibility {state_text}")

    def check_bw_faster_whisper_engine(self) -> None:
        ok, detail = faster_whisper_status()
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        self._show_message_box(detail, "faster-whisper Engine", self._wx.OK | icon)
        self._set_status("faster-whisper engine ready" if ok else "faster-whisper not installed")

    def _set_bw_download_status(
        self,
        model_id: str,
        *,
        model_name: str,
        status: str,
        progress: str,
        started_at: str | None = None,
        finished_at: str = "",
    ) -> None:
        existing = self._bw_download_status.get(model_id, {})
        self._bw_download_status[model_id] = {
            "model": model_name,
            "status": status,
            "progress": progress,
            "started_at": started_at
            or str(existing.get("started_at", datetime.now(UTC).isoformat())),
            "finished_at": finished_at,
        }
        self._maybe_refresh_live_status_tabs()

    def _bw_include_cloud_providers(self) -> bool:
        return bool(getattr(self.settings, "bw_show_cloud_providers", True))

    def _bw_local_first_mode(self) -> bool:
        return str(getattr(self.settings, "bw_provider_mode", "local_first")) == "local_first"

    def _bw_safe_mode_locked(self) -> bool:
        return bool(getattr(self.settings, "bw_safe_mode_lock", False))

    def _append_bw_safe_mode_badge(self, menu: object) -> None:
        if not self._bw_safe_mode_locked():
            return
        badge_item = menu.Append(self._wx.ID_ANY, "Safe Mode Lock: Enabled")
        badge_item.Enable(False)

    def apply_bw_recommended_provider(self) -> None:
        provider_id = bw_recommended_provider_id(local_first=self._bw_local_first_mode())
        self.settings.bw_provider_id = provider_id
        save_settings(self.settings)
        provider = bw_get_provider(provider_id, include_cloud=True)
        provider_name = provider.name if provider is not None else provider_id
        self._set_status(f"Recommended provider selected: {provider_name}")

    def select_bw_provider(self) -> None:
        providers = bw_list_providers(include_cloud=self._bw_include_cloud_providers())
        if not providers:
            self._set_status("No providers available for current provider visibility settings")
            return
        labels = [f"{provider.name} ({provider.provider_type})" for provider in providers]
        dialog = self._wx.SingleChoiceDialog(
            self.frame,
            "Select a provider to stage for upcoming BITS Whisperer phases.",
            "BITS Whisperer Provider Selection",
            labels,
        )
        apply_modal_ids(dialog, affirmative_id=self._wx.ID_OK, escape_id=self._wx.ID_CANCEL)
        try:
            if (
                self._show_modal_dialog(dialog, "BITS Whisperer Provider Selection")
                != self._wx.ID_OK
            ):
                return
            selection = dialog.GetSelection()
        finally:
            dialog.Destroy()

        if selection < 0 or selection >= len(providers):
            return
        selected = providers[selection]
        self.settings.bw_provider_id = selected.id
        save_settings(self.settings)
        self._set_status(f"Selected provider: {selected.name}")

    def show_bw_provider_status(self) -> None:
        provider_id = str(getattr(self.settings, "bw_provider_id", "local_whisper"))
        local_first = self._bw_local_first_mode()
        include_cloud = self._bw_include_cloud_providers()
        provider = bw_get_provider(provider_id, include_cloud=include_cloud)
        readiness = bw_provider_readiness(provider_id, local_first=local_first)
        recommended_id = bw_recommended_provider_id(local_first=local_first)
        recommended = bw_get_provider(recommended_id, include_cloud=True)
        mode_name = "Local-first" if local_first else "Cloud-first"
        lines = [
            "BITS Whisperer Provider Status",
            "",
            bw_provider_mode_guidance(local_first=local_first),
            f"Provider mode: {mode_name}",
            f"Cloud providers visible: {'Yes' if include_cloud else 'No'}",
            f"Configured provider: {provider.name if provider else provider_id}",
            f"Recommended provider: {recommended.name if recommended else recommended_id}",
            "",
            f"Readiness: {'Ready' if readiness.ready else 'Needs setup'}",
            readiness.summary,
            "",
            "Next steps:",
        ]
        lines.extend(f"- {step}" for step in readiness.next_steps)
        lines.append("")
        lines.append(
            "Providers are staged intentionally in this phase; "
            "runtime provider routing remains gated."
        )
        self._show_message_box("\n".join(lines), "BITS Whisperer Providers", self._wx.OK)
        self._set_status("BITS Whisperer provider status shown")

    def open_bw_provider_center(self) -> None:
        actions = [
            "Use recommended provider",
            "Select provider manually",
            "Show provider status",
            "Switch to local-first mode",
            "Switch to cloud-first mode",
            "Toggle cloud provider visibility",
        ]
        dialog = self._wx.SingleChoiceDialog(
            self.frame,
            "Choose a guided provider setup action.",
            "BITS Whisperer Provider Center",
            actions,
        )
        apply_modal_ids(dialog, affirmative_id=self._wx.ID_OK, escape_id=self._wx.ID_CANCEL)
        try:
            if self._show_modal_dialog(dialog, "BITS Whisperer Provider Center") != self._wx.ID_OK:
                return
            action = actions[dialog.GetSelection()]
        finally:
            dialog.Destroy()

        if action == "Use recommended provider":
            self.apply_bw_recommended_provider()
            return
        if action == "Select provider manually":
            self.select_bw_provider()
            return
        if action == "Show provider status":
            self.show_bw_provider_status()
            return
        if action == "Switch to local-first mode":
            self.settings.bw_provider_mode = "local_first"
            save_settings(self.settings)
            self._set_status("Provider mode set to local-first")
            return
        if action == "Switch to cloud-first mode":
            self.settings.bw_provider_mode = "cloud_first"
            save_settings(self.settings)
            self._set_status("Provider mode set to cloud-first")
            return
        if action == "Toggle cloud provider visibility":
            self.settings.bw_show_cloud_providers = not self._bw_include_cloud_providers()
            save_settings(self.settings)
            state_text = "enabled" if self.settings.bw_show_cloud_providers else "disabled"
            self._set_status(f"Cloud provider visibility {state_text}")
            return

    def _bw_readiness_snapshot(self) -> dict[str, object]:
        local_first = self._bw_local_first_mode()
        provider_id = str(getattr(self.settings, "bw_provider_id", "local_whisper"))
        provider = bw_get_provider(provider_id, include_cloud=True)
        readiness = bw_provider_readiness(provider_id, local_first=local_first)
        recommended_provider_id = bw_recommended_provider_id(local_first=local_first)
        recommended_provider = bw_get_provider(recommended_provider_id, include_cloud=True)
        downloaded_ids = bw_downloaded_model_ids(include_parakeet=False)
        available_model_count = len(bw_list_models(include_parakeet=False))
        engine_ok, engine_status = faster_whisper_status()
        return {
            "provider_mode": "local_first" if local_first else "cloud_first",
            "provider_id": provider_id,
            "provider_name": provider.name if provider is not None else provider_id,
            "recommended_provider_id": recommended_provider_id,
            "recommended_provider_name": (
                recommended_provider.name
                if recommended_provider is not None
                else recommended_provider_id
            ),
            "provider_ready": readiness.ready,
            "provider_summary": readiness.summary,
            "provider_next_steps": list(readiness.next_steps),
            "speech_model_mode": str(
                getattr(self.settings, "bw_speech_selection_mode", "recommended")
            ),
            "speech_model_id": str(getattr(self.settings, "bw_speech_model_id", "whisper-base")),
            "safe_mode_lock": self._bw_safe_mode_locked(),
            "downloaded_model_count": len(downloaded_ids),
            "available_model_count": available_model_count,
            "downloaded_model_ids": sorted(downloaded_ids),
            "engine_ready": engine_ok,
            "engine_status": engine_status,
            "machine_guidance": bw_machine_guidance(),
        }

    def _bw_diagnostics_snapshot(self) -> dict[str, object]:
        snapshot = self._bw_readiness_snapshot()
        snapshot["download_status"] = {
            model_id: {
                "model": str(entry.get("model", "")),
                "status": str(entry.get("status", "")),
                "progress": str(entry.get("progress", "")),
                "started_at": str(entry.get("started_at", "")),
                "finished_at": str(entry.get("finished_at", "")),
            }
            for model_id, entry in sorted(self._bw_download_status.items())
        }
        return snapshot

    def show_bw_readiness_check(self) -> None:
        snapshot = self._bw_readiness_snapshot()
        lines = [
            "BITS Whisperer Readiness Check",
            "",
            str(snapshot["machine_guidance"]),
            f"Provider mode: {snapshot['provider_mode']}",
            f"Configured provider: {snapshot['provider_name']}",
            f"Recommended provider: {snapshot['recommended_provider_name']}",
            f"Provider readiness: {'Ready' if snapshot['provider_ready'] else 'Needs setup'}",
            str(snapshot["provider_summary"]),
            f"Speech mode: {snapshot['speech_model_mode']}",
            f"Configured speech model: {snapshot['speech_model_id']}",
            f"Safe mode lock: {'Enabled' if snapshot['safe_mode_lock'] else 'Disabled'}",
            (
                "Downloaded whisper models: "
                f"{snapshot['downloaded_model_count']} of {snapshot['available_model_count']}"
            ),
            f"faster-whisper engine: {'Ready' if snapshot['engine_ready'] else 'Not installed'}",
            str(snapshot["engine_status"]),
            "",
            "Next steps:",
        ]
        lines.extend(f"- {step}" for step in snapshot["provider_next_steps"])
        self._show_message_box("\n".join(lines), "BITS Whisperer Readiness", self._wx.OK)
        self._set_status("BITS Whisperer readiness check complete")

    def _build_bw_capability_matrix_html(self) -> str:
        snapshot = self._bw_readiness_snapshot()
        rows = [
            (
                "Whisper model acquisition",
                "Phase 1",
                "Ready"
                if bool(snapshot["engine_ready"]) and int(snapshot["downloaded_model_count"]) > 0
                else "In setup",
                "Download and stage whisper models from the BITS Whisperer menu.",
            ),
            (
                "Provider onboarding",
                "Phase 1",
                "Ready" if bool(snapshot["provider_ready"]) else "In setup",
                "Use Provider Center and Readiness Check for safe staged onboarding.",
            ),
            (
                "Dynamic status monitoring",
                "Phase 1",
                "Ready",
                "Help Status Page refreshes live with accessibility-aware cadence controls.",
            ),
            (
                "Parakeet runtime",
                "Phase 2",
                "Gated",
                "Parakeet remains intentionally staged to reduce regression risk.",
            ),
            (
                "Runtime provider routing",
                "Phase 2",
                "Gated",
                "Cloud and advanced routing behavior is delayed until validation is complete.",
            ),
        ]
        rows_html = "".join(
            (
                "<tr>"
                f"<th scope='row'>{html.escape(name)}</th>"
                f"<td>{html.escape(phase)}</td>"
                f"<td>{html.escape(status)}</td>"
                f"<td>{html.escape(notes)}</td>"
                "</tr>"
            )
            for name, phase, status, notes in rows
        )
        return (
            "<h1 id='bw-capability-matrix'>BITS Whisperer Capability Matrix</h1>"
            "<p>This matrix shows rollout-safe capabilities currently staged in Quill.</p>"
            "<table>"
            "<caption>Capability status by rollout phase</caption>"
            "<thead><tr>"
            "<th scope='col'>Capability</th><th scope='col'>Phase</th>"
            "<th scope='col'>Status</th><th scope='col'>Notes</th>"
            "</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table>"
            "<h2 id='current-snapshot'>Current Snapshot</h2>"
            "<ul>"
            f"<li>Provider mode: {html.escape(str(snapshot['provider_mode']))}</li>"
            f"<li>Configured provider: {html.escape(str(snapshot['provider_name']))}</li>"
            f"<li>Speech model mode: {html.escape(str(snapshot['speech_model_mode']))}</li>"
            f"<li>Configured speech model: {html.escape(str(snapshot['speech_model_id']))}</li>"
            f"<li>Downloaded whisper models: {snapshot['downloaded_model_count']} "
            f"of {snapshot['available_model_count']}</li>"
            "</ul>"
        )

    def show_bw_capability_matrix_page(self) -> None:
        index = self._open_generated_tab(
            "BITS Whisperer Capability Matrix",
            self._build_bw_capability_matrix_html(),
        )
        self._select_tab(index)
        if 0 <= index < len(self._document_tabs):
            self._show_side_preview_for(self._document_tabs[index])
        self._set_status("Opened BITS Whisperer capability matrix")

    def _start_bw_model_download(self, spec: object) -> None:
        if self._bw_safe_mode_locked():
            self._show_message_box(
                "BITS Whisperer safe mode lock is enabled. Disable it in Preferences -> General "
                "to allow model downloads.",
                "BITS Whisperer Safe Mode",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            self._set_status("BITS Whisperer safe mode lock blocked model download")
            return
        model_id = str(getattr(spec, "id", ""))
        model_name = str(getattr(spec, "name", model_id))
        started_at = datetime.now(UTC).isoformat()
        self._set_bw_download_status(
            model_id,
            model_name=model_name,
            status="running",
            progress="Starting",
            started_at=started_at,
        )

        def work(progress: Callable[[str, int, int], None]) -> object:
            def _progress(done: int, total: int) -> None:
                total_display = total if total > 0 else 0
                self._wx.CallAfter(
                    self._set_bw_download_status,
                    model_id,
                    model_name=model_name,
                    status="running",
                    progress=f"{done}/{total_display}",
                    started_at=started_at,
                )
                progress("Downloading model", done, total)

            try:
                return bw_download_model(spec, progress=_progress)
            except Exception:
                self._wx.CallAfter(
                    self._set_bw_download_status,
                    model_id,
                    model_name=model_name,
                    status="failed",
                    progress="Failed",
                    started_at=started_at,
                    finished_at=datetime.now(UTC).isoformat(),
                )
                raise

        def on_success(_result: object) -> None:
            self._set_bw_download_status(
                model_id,
                model_name=model_name,
                status="completed",
                progress="Completed",
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
            )
            self._set_status(f"Downloaded {model_name}. Check Help -> Status Page for details.")

        self._run_background_task(
            f"BITS Whisperer model download: {model_name}",
            work,
            on_success,
            notify_on_success=True,
            notify_on_error=True,
            notification_category="speech",
        )
        if bool(
            getattr(
                self.settings,
                "bw_auto_open_status_page_on_download_start",
                False,
            )
        ):
            self.show_help_status_page()
        self._set_status(f"Started background download for {model_name}")

    def manage_bw_download_queue(self) -> None:
        actions = [
            "Open live status page",
            "Retry failed download",
            "Clear completed and failed download history",
        ]
        dialog = self._wx.SingleChoiceDialog(
            self.frame,
            "Choose a download queue action.",
            "BITS Whisperer Download Queue",
            actions,
        )
        apply_modal_ids(dialog, affirmative_id=self._wx.ID_OK, escape_id=self._wx.ID_CANCEL)
        try:
            if self._show_modal_dialog(dialog, "BITS Whisperer Download Queue") != self._wx.ID_OK:
                return
            action = actions[dialog.GetSelection()]
        finally:
            dialog.Destroy()

        if action == "Open live status page":
            self.show_help_status_page()
            return

        if action == "Retry failed download":
            if self._bw_safe_mode_locked():
                self._show_message_box(
                    "BITS Whisperer safe mode lock is enabled. Disable it in Preferences -> "
                    "General to allow download retries.",
                    "BITS Whisperer Safe Mode",
                    self._wx.ICON_INFORMATION | self._wx.OK,
                )
                self._set_status("BITS Whisperer safe mode lock blocked download retry")
                return
            failed_ids = [
                model_id
                for model_id, entry in self._bw_download_status.items()
                if str(entry.get("status", "")).lower() == "failed"
            ]
            if not failed_ids:
                self._set_status("No failed BITS Whisperer downloads to retry")
                return
            failed_choices = [
                f"{model_id} ({self._bw_download_status[model_id].get('model', model_id)})"
                for model_id in failed_ids
            ]
            retry_dialog = self._wx.SingleChoiceDialog(
                self.frame,
                "Choose a failed model download to retry.",
                "Retry Download",
                failed_choices,
            )
            apply_modal_ids(
                retry_dialog,
                affirmative_id=self._wx.ID_OK,
                escape_id=self._wx.ID_CANCEL,
            )
            try:
                if self._show_modal_dialog(retry_dialog, "Retry Download") != self._wx.ID_OK:
                    return
                selection = retry_dialog.GetSelection()
            finally:
                retry_dialog.Destroy()
            if selection < 0 or selection >= len(failed_ids):
                return
            model_id = failed_ids[selection]
            spec = bw_get_model(model_id, include_parakeet=True)
            if spec is None:
                self._set_status(f"Could not retry; model no longer available: {model_id}")
                return
            self._start_bw_model_download(spec)
            return

        if action == "Clear completed and failed download history":
            self._bw_download_status = {
                model_id: entry
                for model_id, entry in self._bw_download_status.items()
                if str(entry.get("status", "")).lower() == "running"
            }
            self._maybe_refresh_live_status_tabs()
            self._set_status("Cleared completed and failed BITS Whisperer download history")
            return

    def open_bw_model_manager(self) -> None:
        include_parakeet = self._bw_include_parakeet_models()
        models = bw_list_models(include_parakeet=include_parakeet)
        downloaded = bw_downloaded_model_ids(include_parakeet=include_parakeet)
        recommended = bw_recommended_model_id(include_parakeet=include_parakeet)

        quick_actions = [
            "Use recommended model",
            "Choose model manually",
            "Show model status",
            "Check faster-whisper engine",
        ]
        quick_dialog = self._wx.SingleChoiceDialog(
            self.frame,
            (f"{bw_machine_guidance()}\n\nSelect a guided action for speech model setup."),
            "BITS Whisperer Speech Setup",
            quick_actions,
        )
        apply_modal_ids(
            quick_dialog,
            affirmative_id=self._wx.ID_OK,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            if (
                self._show_modal_dialog(quick_dialog, "BITS Whisperer Speech Setup")
                != self._wx.ID_OK
            ):
                return
            quick_action = quick_actions[quick_dialog.GetSelection()]
        finally:
            quick_dialog.Destroy()

        if quick_action == "Use recommended model":
            self.apply_bw_recommended_model()
            return
        if quick_action == "Show model status":
            self.show_bw_model_status()
            return
        if quick_action == "Check faster-whisper engine":
            self.check_bw_faster_whisper_engine()
            return

        choices: list[str] = []
        model_ids: list[str] = []
        for spec in models:
            markers: list[str] = []
            if spec.id in downloaded:
                markers.append("downloaded")
            if spec.id == recommended:
                markers.append("recommended")
            marker_text = f" [{' | '.join(markers)}]" if markers else ""
            choices.append(f"{spec.name} ({spec.family}){marker_text}")
            model_ids.append(spec.id)

        dialog = self._wx.SingleChoiceDialog(
            self.frame,
            "Choose a speech model to configure.",
            "BITS Whisperer Speech Models",
            choices,
        )
        apply_modal_ids(dialog, affirmative_id=self._wx.ID_OK, escape_id=self._wx.ID_CANCEL)
        try:
            if self._show_modal_dialog(dialog, "BITS Whisperer Speech Models") != self._wx.ID_OK:
                return
            selection = dialog.GetSelection()
        finally:
            dialog.Destroy()

        if selection < 0 or selection >= len(model_ids):
            return

        model_id = model_ids[selection]
        spec = bw_get_model(model_id, include_parakeet=include_parakeet)
        if spec is None:
            return

        actions = ["Set as default", "Show status"]
        is_present = spec.id in downloaded
        if is_present:
            actions.insert(1, "Remove downloaded model")
        else:
            actions.insert(1, "Download model")

        action_dialog = self._wx.SingleChoiceDialog(
            self.frame,
            (
                f"{spec.name}\n\n{spec.description}\n"
                f"Approx size: {spec.approx_size_gb:.2f} GB\n"
                f"Minimum RAM: {spec.min_ram_gb} GB"
            ),
            "BITS Whisperer Model Action",
            actions,
        )
        apply_modal_ids(
            action_dialog,
            affirmative_id=self._wx.ID_OK,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            if (
                self._show_modal_dialog(action_dialog, "BITS Whisperer Model Action")
                != self._wx.ID_OK
            ):
                return
            action = actions[action_dialog.GetSelection()]
        finally:
            action_dialog.Destroy()

        if action == "Set as default":
            self.settings.bw_speech_selection_mode = "manual"
            self.settings.bw_speech_model_id = spec.id
            save_settings(self.settings)
            self._set_status(f"Manual mode active. Default speech model set to {spec.name}")
            return

        if action == "Download model":
            if spec.family != "whisper":
                self._show_message_box(
                    "Parakeet downloads are intentionally gated in phase 1. "
                    "Enable only whisper acquisition for now.",
                    "BITS Whisperer Speech Models",
                    self._wx.ICON_INFORMATION | self._wx.OK,
                )
                self._set_status("Parakeet download remains gated for later phases")
                return
            if not bw_has_disk_capacity(spec):
                self._show_message_box(
                    "Not enough disk space for this model plus safety buffer.",
                    "BITS Whisperer Speech Models",
                    self._wx.ICON_WARNING | self._wx.OK,
                )
                self._set_status("Speech model download blocked by disk space check")
                return
            self._start_bw_model_download(spec)
            return

        if action == "Remove downloaded model":
            if bw_remove_model(spec):
                self._set_status(f"Removed downloaded model {spec.name}")
            else:
                self._set_status(f"Model was not downloaded: {spec.name}")
            return

        if action == "Show status":
            self.show_bw_model_status()

    def _apply_watch_folder_menu_state(self) -> None:
        # Watch folder toggle is now in Settings; no menu state to sync
        pass

    def _maybe_start_watch_folder(self) -> None:
        # H-SAFE-1: safe mode must not start the watcher; the banner is a
        # contract. The WatchService can still be constructed so other
        # surfaces (settings UI, diagnostics) can inspect profiles, but
        # ``start()`` is the side effect we are refusing.
        if self._safe_mode:
            self._apply_watch_folder_menu_state()
            return
        if not bool(getattr(self.settings, "watch_folder_enabled", False)):
            self._apply_watch_folder_menu_state()
            return
        self._start_watch_folder_monitoring(announce=False)

    def _start_watch_folder_monitoring(self, *, announce: bool = True) -> bool:
        if not self._feature_enabled("core.watch_folder"):
            if announce:
                self._set_status("Watch folder is unavailable in this profile")
            return False
        started = self._watch_service.start()
        self.settings.watch_folder_enabled = True
        save_settings(self.settings)
        self._apply_watch_folder_menu_state()
        if announce:
            if started:
                count = len(started)
                noun = "profile" if count == 1 else "profiles"
                self._set_status(f"Watch folder monitoring started ({count} {noun})")
                self._record_notification("Watch folder monitoring started", "speech")
            else:
                self._set_status("Watch folder is on, but no profiles are enabled")
                self._record_notification(
                    "Watch folder monitoring is on, but no profiles are enabled",
                    "speech",
                )
        return True

    def _stop_watch_folder_monitoring(self, *, announce: bool = True) -> None:
        self._watch_service.stop()
        self._apply_watch_folder_menu_state()
        if announce:
            self._set_status("Watch folder monitoring stopped")
            self._record_notification("Watch folder monitoring stopped", "speech")

    def toggle_watch_folder_monitoring(self) -> None:
        """Open Settings at the Watch Folders tab where monitoring can be toggled."""
        self.open_general_preferences()
        self._set_status("Watch folder monitoring setting is in Settings > Watch Folders")

    def show_watch_folder_status(self) -> None:
        """Open the accessible Watch Queue Monitor (WATCH-4)."""
        if not self._feature_enabled("core.watch_folder"):
            self._set_status("Watch folder is unavailable in this profile")
            return
        existing = self._watch_queue_monitor
        if existing is not None:
            try:
                existing.Raise()
                existing.SetFocus()
                self._refresh_watch_queue_monitor()
                return
            except Exception:
                self._watch_queue_monitor = None
                self._watch_queue_listbox = None
        wx = self._wx
        dialog = wx.Dialog(
            self.frame,
            title="Watch Queue Monitor",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        root = wx.BoxSizer(wx.VERTICAL)

        summary = wx.StaticText(dialog, label="Watch queue")
        summary.SetName("Watch queue summary")
        root.Add(summary, 0, wx.ALL, 8)

        listbox = wx.ListBox(dialog, style=wx.LB_SINGLE)
        listbox.SetName("Watch queue items")
        root.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        pause_button = wx.Button(dialog, label="&Pause")
        pause_button.SetName("Pause or resume the watch queue")
        retry_button = wx.Button(dialog, label="&Retry")
        retry_button.SetName("Retry selected item")
        open_button = wx.Button(dialog, label="&Open Result")
        open_button.SetName("Open the result of the selected item")
        clear_button = wx.Button(dialog, label="&Clear Finished")
        clear_button.SetName("Clear finished items")
        refresh_button = wx.Button(dialog, label="Re&fresh")
        refresh_button.SetName("Refresh the watch queue")
        for button in (pause_button, retry_button, open_button, clear_button, refresh_button):
            button_row.Add(button, 0, wx.RIGHT, 6)
        root.Add(button_row, 0, wx.ALL, 8)

        buttons = dialog.CreateButtonSizer(wx.CLOSE)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizerAndFit(root)
        dialog.SetSize((640, 460))

        def _selected_item() -> QueueItem | None:
            index = listbox.GetSelection()
            if index == wx.NOT_FOUND:
                return None
            items = self._watch_queue_items_cache
            if 0 <= index < len(items):
                return items[index]
            return None

        def _on_pause(_event: object) -> None:
            if self._watch_service.queue.is_paused():
                self._watch_service.resume()
                self._set_status("Watch queue resumed")
            else:
                self._watch_service.pause()
                self._set_status("Watch queue paused")
            self._refresh_watch_queue_monitor()

        def _on_retry(_event: object) -> None:
            item = _selected_item()
            if item is None:
                self._set_status("Select a queue item to retry")
                return
            if self._watch_service.retry_item(item.item_id):
                self._set_status(f"Retrying {Path(item.source_path).name}")
            else:
                self._set_status("That item cannot be retried")
            self._refresh_watch_queue_monitor()

        def _on_open(_event: object) -> None:
            item = _selected_item()
            if item is None:
                self._set_status("Select a queue item to open")
                return
            target = item.result_path or item.source_path
            if not target:
                self._set_status("That item has no file to open")
                return
            self.open_file(Path(target), record_recent=True, refresh_existing=False)

        def _on_clear(_event: object) -> None:
            removed = self._watch_service.clear_finished()
            self._set_status(f"Cleared {removed} finished item{'s' if removed != 1 else ''}")
            self._refresh_watch_queue_monitor()

        def _on_refresh(_event: object) -> None:
            self._refresh_watch_queue_monitor()

        def _on_close(_event: object) -> None:
            self._watch_queue_monitor = None
            self._watch_queue_listbox = None
            self._watch_queue_pause_button = None
            dialog.Destroy()

        pause_button.Bind(wx.EVT_BUTTON, _on_pause)
        retry_button.Bind(wx.EVT_BUTTON, _on_retry)
        open_button.Bind(wx.EVT_BUTTON, _on_open)
        clear_button.Bind(wx.EVT_BUTTON, _on_clear)
        refresh_button.Bind(wx.EVT_BUTTON, _on_refresh)
        dialog.Bind(wx.EVT_BUTTON, _on_close, id=wx.ID_CLOSE)
        dialog.Bind(wx.EVT_CLOSE, _on_close)

        self._watch_queue_monitor = dialog
        self._watch_queue_listbox = listbox
        self._watch_queue_summary = summary
        self._watch_queue_pause_button = pause_button
        self._watch_queue_items_cache = []
        apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
        self._refresh_watch_queue_monitor()
        dialog.Show()
        listbox.SetFocus()

    def _refresh_watch_queue_monitor(self) -> None:
        dialog = self._watch_queue_monitor
        listbox = self._watch_queue_listbox
        if dialog is None or listbox is None:
            return
        try:
            items = self._watch_service.queue_items()
        except Exception:
            items = []
        self._watch_queue_items_cache = items
        previous = listbox.GetSelection()
        listbox.Clear()
        for item in items:
            name = Path(item.source_path).name if item.source_path else "(unknown)"
            label = f"{item.state.title()} - {name}"
            if item.attempts:
                label += f" (attempt {item.attempts})"
            if item.message:
                label += f" - {item.message}"
            listbox.Append(label)
        if items:
            target = previous if 0 <= previous < len(items) else 0
            listbox.SetSelection(target)
        counts = self._watch_service.queue_counts()
        summary = getattr(self, "_watch_queue_summary", None)
        if summary is not None:
            queued = counts.get(STATE_QUEUED, 0) + counts.get(STATE_PROCESSING, 0)
            done = counts.get(STATE_DONE, 0)
            failed = counts.get(STATE_FAILED, 0)
            skipped = counts.get(STATE_SKIPPED, 0)
            paused = " (paused)" if self._watch_service.queue.is_paused() else ""
            summary.SetLabel(
                f"Pending {queued}, done {done}, failed {failed}, skipped {skipped}{paused}"
            )
        pause_button = getattr(self, "_watch_queue_pause_button", None)
        if pause_button is not None:
            pause_button.SetLabel("Resume" if self._watch_service.queue.is_paused() else "Pause")

    def open_watch_folder_settings(self) -> None:
        """Open the accessible Watch Profile Manager (WATCH-5)."""
        if not self._feature_enabled("core.watch_folder"):
            self._set_status("Watch folder is unavailable in this profile")
            return
        wx = self._wx
        with wx.Dialog(
            self.frame,
            title="Watch Folder Profiles",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        ) as dialog:
            root = wx.BoxSizer(wx.VERTICAL)

            heading = wx.StaticText(dialog, label="Watch folder profiles")
            heading.SetName("Watch folder profiles")
            root.Add(heading, 0, wx.ALL, 8)

            listbox = wx.ListBox(dialog, style=wx.LB_SINGLE)
            listbox.SetName("Watch folder profile list")
            root.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

            button_row = wx.BoxSizer(wx.HORIZONTAL)
            add_button = wx.Button(dialog, label="&Add...")
            edit_button = wx.Button(dialog, label="&Edit...")
            duplicate_button = wx.Button(dialog, label="D&uplicate")
            toggle_button = wx.Button(dialog, label="Ena&ble/Disable")
            delete_button = wx.Button(dialog, label="De&lete")
            for button in (add_button, edit_button, duplicate_button, toggle_button, delete_button):
                button_row.Add(button, 0, wx.RIGHT, 6)
            root.Add(button_row, 0, wx.ALL, 8)

            buttons = dialog.CreateButtonSizer(wx.CLOSE)
            if buttons is not None:
                root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            dialog.SetSizerAndFit(root)
            dialog.SetSize((620, 440))

            def _refresh_list(select: int = -1) -> None:
                profiles = self._watch_service.profiles()
                listbox.Clear()
                for profile in profiles:
                    state = "enabled" if profile.enabled else "disabled"
                    folder = profile.folder_path or "(no folder)"
                    listbox.Append(f"{profile.name} - {state} - {folder}")
                if profiles:
                    index = select if 0 <= select < len(profiles) else 0
                    listbox.SetSelection(index)

            def _selected_profile() -> WatchProfile | None:
                index = listbox.GetSelection()
                if index == wx.NOT_FOUND:
                    return None
                profiles = self._watch_service.profiles()
                if 0 <= index < len(profiles):
                    return profiles[index]
                return None

            def _on_add(_event: object) -> None:
                profile = self._edit_watch_profile(None)
                if profile is not None:
                    self._watch_service.add_profile(profile)
                    _refresh_list()
                    self._set_status(f"Added watch profile {profile.name}")

            def _on_edit(_event: object) -> None:
                current = _selected_profile()
                if current is None:
                    self._set_status("Select a profile to edit")
                    return
                updated = self._edit_watch_profile(current)
                if updated is not None:
                    self._watch_service.update_profile(updated)
                    _refresh_list(listbox.GetSelection())
                    self._set_status(f"Updated watch profile {updated.name}")

            def _on_duplicate(_event: object) -> None:
                current = _selected_profile()
                if current is None:
                    self._set_status("Select a profile to duplicate")
                    return
                copy = self._watch_service.duplicate_profile(current.profile_id)
                if copy is not None:
                    _refresh_list()
                    self._set_status(f"Duplicated watch profile {current.name}")

            def _on_toggle(_event: object) -> None:
                current = _selected_profile()
                if current is None:
                    self._set_status("Select a profile to enable or disable")
                    return
                self._watch_service.set_profile_enabled(current.profile_id, not current.enabled)
                _refresh_list(listbox.GetSelection())
                state = "disabled" if current.enabled else "enabled"
                self._set_status(f"{current.name} {state}")

            def _on_delete(_event: object) -> None:
                current = _selected_profile()
                if current is None:
                    self._set_status("Select a profile to delete")
                    return
                response = self._show_message_box(
                    f"Delete watch profile '{current.name}'?",
                    "Delete Watch Profile",
                    wx.ICON_QUESTION | wx.YES_NO,
                )
                if response != wx.YES:
                    return
                self._watch_service.delete_profile(current.profile_id)
                _refresh_list()
                self._set_status(f"Deleted watch profile {current.name}")

            add_button.Bind(wx.EVT_BUTTON, _on_add)
            edit_button.Bind(wx.EVT_BUTTON, _on_edit)
            duplicate_button.Bind(wx.EVT_BUTTON, _on_duplicate)
            toggle_button.Bind(wx.EVT_BUTTON, _on_toggle)
            delete_button.Bind(wx.EVT_BUTTON, _on_delete)

            _refresh_list()
            apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
            self._show_modal_dialog(dialog, "Watch Folder Profiles")

        if self._watch_service.is_running:
            self._watch_service.restart()
        self._apply_watch_folder_menu_state()
        self._set_status("Updated watch folder profiles")

    def _edit_watch_profile(self, profile: WatchProfile | None) -> WatchProfile | None:  # noqa: PLR0915
        wx = self._wx
        base = profile if profile is not None else WatchProfile()
        title = "Edit Watch Profile" if profile is not None else "Add Watch Profile"
        with wx.Dialog(self.frame, title=title) as dialog:
            root = wx.BoxSizer(wx.VERTICAL)

            name_row = wx.BoxSizer(wx.HORIZONTAL)
            name_label = wx.StaticText(dialog, label="Profile name")
            name_input = wx.TextCtrl(dialog, value=base.name)
            name_input.SetName("Profile name")
            name_row.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            name_row.Add(name_input, 1, wx.EXPAND)
            root.Add(name_row, 0, wx.EXPAND | wx.ALL, 8)

            enabled = wx.CheckBox(dialog, label="Profile enabled")
            enabled.SetValue(base.enabled)
            enabled.SetName("Profile enabled")
            root.Add(enabled, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            path_row = wx.BoxSizer(wx.HORIZONTAL)
            path_label = wx.StaticText(dialog, label="Watch folder")
            path_input = wx.TextCtrl(dialog, value=base.folder_path)
            path_input.SetName("Watch folder path")
            path_browse = wx.Button(dialog, label="Bro&wse...")
            path_row.Add(path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            path_row.Add(path_input, 1, wx.EXPAND | wx.RIGHT, 8)
            path_row.Add(path_browse, 0)
            root.Add(path_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            include_subfolders = wx.CheckBox(dialog, label="Include subfolders")
            include_subfolders.SetValue(base.include_subfolders)
            include_subfolders.SetName("Include subfolders")
            root.Add(include_subfolders, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            process_existing = wx.CheckBox(dialog, label="Process existing files on start")
            process_existing.SetValue(base.process_existing)
            process_existing.SetName("Process existing files on start")
            root.Add(process_existing, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # --- Filters (WATCH-5) ---
            suffix_row = wx.BoxSizer(wx.HORIZONTAL)
            suffix_label = wx.StaticText(dialog, label="File types (comma separated)")
            suffix_input = wx.TextCtrl(dialog, value=", ".join(base.suffixes))
            suffix_input.SetName("File type suffixes, comma separated")
            suffix_row.Add(suffix_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            suffix_row.Add(suffix_input, 1, wx.EXPAND)
            root.Add(suffix_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            pattern_row = wx.BoxSizer(wx.HORIZONTAL)
            pattern_label = wx.StaticText(dialog, label="Name patterns (comma separated)")
            pattern_input = wx.TextCtrl(dialog, value=", ".join(base.name_patterns))
            pattern_input.SetName("File name patterns, comma separated")
            pattern_row.Add(pattern_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            pattern_row.Add(pattern_input, 1, wx.EXPAND)
            root.Add(pattern_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            size_row = wx.BoxSizer(wx.HORIZONTAL)
            size_label = wx.StaticText(dialog, label="Minimum size (bytes)")
            size_input = wx.SpinCtrl(dialog, min=0, max=1_000_000_000, initial=base.min_size_bytes)
            size_input.SetName("Minimum file size in bytes")
            size_row.Add(size_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            size_row.Add(size_input, 0)
            root.Add(size_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            age_row = wx.BoxSizer(wx.HORIZONTAL)
            age_label = wx.StaticText(dialog, label="Minimum age (seconds)")
            age_input = wx.SpinCtrlDouble(
                dialog, min=0.0, max=3600.0, inc=0.5, initial=base.min_age_seconds
            )
            age_input.SetName("Minimum file age in seconds")
            age_row.Add(age_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            age_row.Add(age_input, 0)
            root.Add(age_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            interval_row = wx.BoxSizer(wx.HORIZONTAL)
            interval_label = wx.StaticText(dialog, label="Poll interval (seconds)")
            interval_input = wx.SpinCtrl(dialog, min=2, max=300, initial=base.poll_interval_seconds)
            interval_input.SetName("Poll interval in seconds")
            interval_row.Add(interval_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            interval_row.Add(interval_input, 0)
            root.Add(interval_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # --- Schedule (WATCH-5) ---
            sched_modes = [SCHED_ALWAYS, SCHED_WINDOW, SCHED_QUIET]
            sched_labels = [
                "Always active",
                "Active only during a daily window",
                "Active except during quiet hours",
            ]
            sched_row = wx.BoxSizer(wx.HORIZONTAL)
            sched_label = wx.StaticText(dialog, label="Schedule")
            sched_choice = wx.Choice(dialog, choices=sched_labels)
            sched_choice.SetName("Schedule mode")
            sched_choice.SetSelection(
                sched_modes.index(base.schedule_mode) if base.schedule_mode in sched_modes else 0
            )
            sched_row.Add(sched_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            sched_row.Add(sched_choice, 1, wx.EXPAND)
            root.Add(sched_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            start_h, start_m = divmod(base.schedule_start_minute, 60)
            end_h, end_m = divmod(base.schedule_end_minute, 60)
            time_row = wx.BoxSizer(wx.HORIZONTAL)
            time_row.Add(
                wx.StaticText(dialog, label="From"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
            )
            start_hour = wx.SpinCtrl(dialog, min=0, max=23, initial=start_h)
            start_hour.SetName("Schedule start hour")
            start_minute = wx.SpinCtrl(dialog, min=0, max=59, initial=start_m)
            start_minute.SetName("Schedule start minute")
            time_row.Add(start_hour, 0, wx.RIGHT, 2)
            time_row.Add(start_minute, 0, wx.RIGHT, 12)
            time_row.Add(
                wx.StaticText(dialog, label="to"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
            )
            end_hour = wx.SpinCtrl(dialog, min=0, max=23, initial=end_h)
            end_hour.SetName("Schedule end hour")
            end_minute = wx.SpinCtrl(dialog, min=0, max=59, initial=end_m)
            end_minute.SetName("Schedule end minute")
            time_row.Add(end_hour, 0, wx.RIGHT, 2)
            time_row.Add(end_minute, 0)
            root.Add(time_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            available = list(self._watch_service.registry.available_actions())
            action_ids = [action.action_id for action in available]
            action_labels = [action.label for action in available]
            action_row = wx.BoxSizer(wx.HORIZONTAL)
            action_label = wx.StaticText(dialog, label="Action")
            action_choice = wx.Choice(dialog, choices=action_labels)
            action_choice.SetName("Watch action")
            if base.action_id in action_ids:
                action_choice.SetSelection(action_ids.index(base.action_id))
            elif action_labels:
                action_choice.SetSelection(0)
            action_row.Add(action_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            action_row.Add(action_choice, 1, wx.EXPAND)
            root.Add(action_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            action_dest_row = wx.BoxSizer(wx.HORIZONTAL)
            action_dest_label = wx.StaticText(dialog, label="Action destination")
            action_dest_input = wx.TextCtrl(
                dialog, value=str(base.action_options.get("destination", ""))
            )
            action_dest_input.SetName("Action destination folder")
            action_dest_browse = wx.Button(dialog, label="Brow&se...")
            action_dest_row.Add(action_dest_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            action_dest_row.Add(action_dest_input, 1, wx.EXPAND | wx.RIGHT, 8)
            action_dest_row.Add(action_dest_browse, 0)
            root.Add(action_dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            # --- Per-action options (WATCH-7) ---
            convert_formats = ["markdown", "html", "plain"]
            convert_labels = ["Markdown", "HTML", "Plain text"]
            convert_row = wx.BoxSizer(wx.HORIZONTAL)
            convert_row.Add(
                wx.StaticText(dialog, label="Convert to"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                8,
            )
            convert_choice = wx.Choice(dialog, choices=convert_labels)
            convert_choice.SetName("Convert target format")
            current_fmt = str(base.action_options.get("target_format", "")).strip().lower()
            convert_choice.SetSelection(
                convert_formats.index(current_fmt) if current_fmt in convert_formats else 0
            )
            convert_row.Add(convert_choice, 1, wx.EXPAND)
            root.Add(convert_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            macro_names = sorted(getattr(getattr(self, "macros", None), "macros", {}) or {})
            macro_row = wx.BoxSizer(wx.HORIZONTAL)
            macro_row.Add(
                wx.StaticText(dialog, label="Macro to run"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                8,
            )
            macro_input = wx.ComboBox(
                dialog,
                value=str(base.action_options.get("macro_name", "")),
                choices=macro_names,
            )
            macro_input.SetName("Macro name to run")
            macro_row.Add(macro_input, 1, wx.EXPAND)
            root.Add(macro_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            root.Add(
                wx.StaticText(dialog, label="Python transform (sandboxed)"),
                0,
                wx.LEFT | wx.RIGHT,
                8,
            )
            python_code = wx.TextCtrl(
                dialog,
                value=str(base.action_options.get("code", "")),
                style=wx.TE_MULTILINE,
                size=(-1, 80),
            )
            python_code.SetName("Python transform code")
            root.Add(python_code, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            py_opts_row = wx.BoxSizer(wx.HORIZONTAL)
            py_opts_row.Add(
                wx.StaticText(dialog, label="Output suffix"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                4,
            )
            python_suffix = wx.TextCtrl(
                dialog, value=str(base.action_options.get("output_suffix", ""))
            )
            python_suffix.SetName("Python transform output suffix")
            py_opts_row.Add(python_suffix, 1, wx.EXPAND | wx.RIGHT, 12)
            py_opts_row.Add(
                wx.StaticText(dialog, label="Timeout (s)"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                4,
            )
            python_timeout = wx.SpinCtrlDouble(
                dialog,
                min=0.1,
                max=60.0,
                inc=0.5,
                initial=float(base.action_options.get("timeout_seconds", 5.0) or 5.0),
            )
            python_timeout.SetName("Python transform timeout in seconds")
            py_opts_row.Add(python_timeout, 0)
            root.Add(py_opts_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            ai_modes = ["summarize", "tag", "rewrite"]
            ai_labels = ["Summarize", "Tag", "Rewrite"]
            ai_row = wx.BoxSizer(wx.HORIZONTAL)
            ai_row.Add(
                wx.StaticText(dialog, label="AI action"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                8,
            )
            ai_choice = wx.Choice(dialog, choices=ai_labels)
            ai_choice.SetName("AI action mode")
            current_ai = str(base.action_options.get("mode", "")).strip().lower()
            ai_choice.SetSelection(ai_modes.index(current_ai) if current_ai in ai_modes else 0)
            ai_row.Add(ai_choice, 1, wx.EXPAND)
            root.Add(ai_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            consent_detail = self._watch_ai_consent_detail()
            consent = wx.CheckBox(
                dialog,
                label="I consent to send this folder's files to the AI model",
            )
            consent.SetValue(bool(base.action_options.get("consent", False)))
            consent.SetName("AI consent for this profile")
            root.Add(consent, 0, wx.LEFT | wx.RIGHT, 8)
            consent_text = wx.StaticText(dialog, label=consent_detail)
            consent_text.SetName("AI consent details")
            root.Add(consent_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            post_choices = ["Leave file in place", "Move to folder", "Delete file"]
            post_values = [POST_LEAVE, POST_MOVE, POST_DELETE]
            post_row = wx.BoxSizer(wx.HORIZONTAL)
            post_label = wx.StaticText(dialog, label="After processing")
            post_choice = wx.Choice(dialog, choices=post_choices)
            post_choice.SetName("After processing")
            post_choice.SetSelection(
                post_values.index(base.post_action) if base.post_action in post_values else 0
            )
            post_row.Add(post_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            post_row.Add(post_choice, 1, wx.EXPAND)
            root.Add(post_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            post_dest_row = wx.BoxSizer(wx.HORIZONTAL)
            post_dest_label = wx.StaticText(dialog, label="Move destination")
            post_dest_input = wx.TextCtrl(dialog, value=base.post_action_destination)
            post_dest_input.SetName("Post-action move destination")
            post_dest_browse = wx.Button(dialog, label="Brows&e...")
            post_dest_row.Add(post_dest_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            post_dest_row.Add(post_dest_input, 1, wx.EXPAND | wx.RIGHT, 8)
            post_dest_row.Add(post_dest_browse, 0)
            root.Add(post_dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            preview_button = wx.Button(dialog, label="Pre&view (dry run)")
            preview_button.SetName("Preview the action without changing files")
            root.Add(preview_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            def _pick_folder(target: object) -> None:
                with wx.DirDialog(
                    dialog,
                    "Choose folder",
                    defaultPath=target.GetValue().strip(),
                    style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
                ) as picker:
                    if self._show_modal_dialog(picker, title) == wx.ID_OK:
                        target.SetValue(picker.GetPath())

            def _selected_action_id() -> str:
                index = action_choice.GetSelection()
                return action_ids[index] if 0 <= index < len(action_ids) else base.action_id

            def _collect_options(action_id: str) -> dict[str, object]:
                options: dict[str, object] = {}
                if action_id in {"move", "copy"}:
                    destination = action_dest_input.GetValue().strip()
                    if destination:
                        options["destination"] = destination
                elif action_id == "convert":
                    fmt_index = convert_choice.GetSelection()
                    options["target_format"] = convert_formats[fmt_index if fmt_index >= 0 else 0]
                elif action_id == "run_macro":
                    macro_name = macro_input.GetValue().strip()
                    if macro_name:
                        options["macro_name"] = macro_name
                elif action_id == "run_python":
                    code = python_code.GetValue()
                    if code.strip():
                        options["code"] = code
                    suffix = python_suffix.GetValue().strip()
                    if suffix:
                        options["output_suffix"] = suffix
                    options["timeout_seconds"] = float(python_timeout.GetValue())
                elif action_id == "ai":
                    ai_index = ai_choice.GetSelection()
                    options["mode"] = ai_modes[ai_index if ai_index >= 0 else 0]
                    options["consent"] = bool(consent.GetValue())
                return options

            def _build_profile() -> WatchProfile:
                action_id = _selected_action_id()
                post_index = post_choice.GetSelection()
                post_action = (
                    post_values[post_index] if 0 <= post_index < len(post_values) else POST_LEAVE
                )
                sched_index = sched_choice.GetSelection()
                schedule_mode = (
                    sched_modes[sched_index]
                    if 0 <= sched_index < len(sched_modes)
                    else SCHED_ALWAYS
                )
                suffixes = tuple(
                    part.strip() for part in suffix_input.GetValue().split(",") if part.strip()
                )
                name_patterns = tuple(
                    part.strip() for part in pattern_input.GetValue().split(",") if part.strip()
                )
                return WatchProfile(
                    profile_id=base.profile_id,
                    name=name_input.GetValue().strip() or "Untitled profile",
                    enabled=bool(enabled.GetValue()),
                    folder_path=path_input.GetValue().strip(),
                    include_subfolders=bool(include_subfolders.GetValue()),
                    process_existing=bool(process_existing.GetValue()),
                    suffixes=suffixes,
                    name_patterns=name_patterns,
                    min_size_bytes=int(size_input.GetValue()),
                    min_age_seconds=float(age_input.GetValue()),
                    poll_interval_seconds=int(interval_input.GetValue()),
                    action_id=action_id,
                    action_options=_collect_options(action_id),
                    schedule_mode=schedule_mode,
                    schedule_start_minute=int(start_hour.GetValue()) * 60
                    + int(start_minute.GetValue()),
                    schedule_end_minute=int(end_hour.GetValue()) * 60 + int(end_minute.GetValue()),
                    post_action=post_action,
                    post_action_destination=post_dest_input.GetValue().strip(),
                ).normalized()

            def _on_preview(_event: object) -> None:
                candidate = _build_profile()
                sample = self._watch_dry_run_sample(candidate)
                preview = self._watch_service.registry.dry_run(
                    candidate.action_id,
                    WatchItem(source_path=sample, profile_id=candidate.profile_id),
                    candidate.action_options,
                )
                self._show_message_box(preview, "Dry-run preview", wx.ICON_INFORMATION | wx.OK)

            path_browse.Bind(wx.EVT_BUTTON, lambda _event: _pick_folder(path_input))
            action_dest_browse.Bind(wx.EVT_BUTTON, lambda _event: _pick_folder(action_dest_input))
            post_dest_browse.Bind(wx.EVT_BUTTON, lambda _event: _pick_folder(post_dest_input))
            preview_button.Bind(wx.EVT_BUTTON, _on_preview)

            ok_cancel = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
            root.Add(dialog, 1, wx.EXPAND | wx.ALL, 8)
            if ok_cancel is not None:
                root.Add(ok_cancel, 0, wx.EXPAND | wx.ALL, 8)
            dialog.SetSizerAndFit(root)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None

            updated = _build_profile()
            problems = updated.validate()
            if problems:
                self._show_message_box(
                    "Please fix the following:\n\n- " + "\n- ".join(problems),
                    title,
                    wx.ICON_WARNING | wx.OK,
                )
                return None
            return updated

    def _watch_ai_consent_detail(self) -> str:
        """Plain-language description of where AI watch actions send content (WATCH-6)."""
        try:
            from quill.core.ai.model_manager import load_model_choice, resolve_spec

            spec = resolve_spec(load_model_choice())
            return (
                f"AI actions send each file's text to your selected model "
                f"({spec.name}). This runs only when consent is ticked."
            )
        except Exception:  # noqa: BLE001 - never block the dialog on this lookup
            return (
                "AI actions send each file's text to your selected AI model. "
                "This runs only when consent is ticked."
            )

    def _watch_dry_run_sample(self, profile: WatchProfile) -> Path:
        """Pick a representative file for a dry-run preview without side effects."""
        folder = Path(profile.folder_path) if profile.folder_path else None
        if folder is not None and folder.is_dir():
            try:
                for candidate in iter_matching_files(profile):
                    return candidate
            except Exception:  # noqa: BLE001 - preview must never raise
                pass
            return folder / "example-file.txt"
        return Path("example-file.txt")

    def _show_watch_folder_onboarding(self, force: bool) -> None:
        wx = self._wx
        response = self._show_message_box(
            "Set up watch folder automation now?\n\n"
            "When enabled, Quill monitors one folder and opens new supported files "
            "automatically as they appear.",
            "Watch Folder Setup",
            wx.ICON_QUESTION | wx.YES_NO,
        )
        if response != wx.YES:
            if not force:
                mark_watch_folder_onboarding_complete()
            self._set_status("Watch folder setup skipped")
            return
        self.open_watch_folder_settings()
        mark_watch_folder_onboarding_complete()

    def _on_watch_file_opened(self, path: Path) -> None:
        try:
            self.open_file(path, record_recent=True, refresh_existing=False)
        except Exception:
            self._set_status(f"Watch folder could not open {path.name}")
            return
        self._record_notification(f"Watch folder opened {path.name}", "speech")
        self._set_status(f"Watch folder opened {path.name}")

    def _on_watch_queue_event(self, event: str, item: object) -> None:
        if self._watch_queue_monitor is not None:
            self._refresh_watch_queue_monitor()
        if event == "failed" and item is not None:
            source = getattr(item, "source_path", "")
            name = Path(source).name if source else "a file"
            message = getattr(item, "message", "") or "unknown error"
            if self._watch_message_is_resource_cap(message):
                # WATCH-6: a runaway action that hit the shared SEC-9 wall-clock
                # cap is terminated; announce the termination distinctly so the
                # user understands the machine was protected, not that their
                # transform merely errored.
                self._record_notification(
                    f"Watch stopped {name}: it exceeded the time limit and was "
                    "terminated to protect your machine.",
                    "speech",
                )
                self._set_status(f"Watch stopped {name}: time limit exceeded")
                return
            self._record_notification(
                f"Watch failed for {name}: {message}",
                "speech",
            )
            self._set_status(f"Watch failed for {name}")

    @staticmethod
    def _watch_message_is_resource_cap(message: str) -> bool:
        """Return True when a failed watch item was terminated for a resource cap.

        The SEC-9 Python sandbox reports a wall-clock kill as "Execution timed
        out"; surface any timeout/limit phrasing as a resource-cap termination
        so WATCH-6 can announce it distinctly (WATCH-6).
        """
        lowered = (message or "").lower()
        return any(
            phrase in lowered
            for phrase in ("timed out", "timeout", "time limit", "exceeded", "resource cap")
        )

    # WATCH-7: built-in action handlers supplied to the watch action registry.
    # These run on the watch worker thread, so file I/O is done directly here
    # (the io layer is UI-agnostic) and any editor work is marshalled to the UI
    # thread via wx.CallAfter.
    _WATCH_CONVERT_KINDS: ClassVar[dict[str, tuple[str, str]]] = {
        "markdown": ("markdown", ".md"),
        "md": ("markdown", ".md"),
        "gfm": ("markdown", ".md"),
        "html": ("html", ".html"),
        "htm": ("html", ".html"),
        "plain": ("plain", ".txt"),
        "text": ("plain", ".txt"),
        "txt": ("plain", ".txt"),
    }

    def _watch_convert_file(self, path: Path, target_format: str) -> Path:
        """Convert a detected file to ``target_format`` via Pandoc (WATCH-7).

        Runs on the watch worker thread. Returns the written output path so the
        queue can report and optionally open the result.
        """
        key = (target_format or "").strip().lower()
        mapping = self._WATCH_CONVERT_KINDS.get(key)
        if mapping is None:
            raise ValueError(
                f"Unsupported convert target '{target_format}'. Use markdown, html, or plain text."
            )
        output_kind, suffix = mapping
        result = convert_document_with_pandoc(path, output_kind)
        target = path.with_suffix(suffix)
        if target == path:
            target = path.with_name(f"{path.stem}.converted{suffix}")
        target.write_text(result.text, encoding="utf-8")
        return target

    def _watch_run_macro(self, path: Path, macro_name: str) -> None:
        """Open a detected file and replay a saved macro over it (WATCH-7).

        Macro replay mutates the editor, so it must happen on the UI thread; the
        worker thread marshals it through wx.CallAfter and returns immediately.
        """
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(self._watch_run_macro_ui, path, macro_name)
        else:  # pragma: no cover - fallback for headless test stubs
            self._watch_run_macro_ui(path, macro_name)

    def _watch_run_macro_ui(self, path: Path, macro_name: str) -> None:
        try:
            self.open_file(path, record_recent=True, refresh_existing=False)
        except Exception:
            self._set_status(f"Watch folder could not open {path.name}")
            return
        macros = getattr(self, "macros", None)
        if macros is None or macro_name not in getattr(macros, "macros", {}):
            self._set_status(f"Macro {macro_name} is no longer available")
            return
        try:
            macros.play_macro(macro_name, self.commands.run)
        except KeyError:
            self._set_status(f"Macro {macro_name} is no longer available")
            return
        self._set_status(f"Ran macro {macro_name} on {path.name}")

    def _watch_run_ai(self, path: Path, options: Mapping[str, object]) -> WatchActionOutcome:
        """Run a consented AI action over a detected file (WATCH-7, AI-5, WATCH-6).

        Runs on the watch worker thread. Honors the AI on/off switch and writes
        the result to a sidecar file so nothing in the editor is overwritten.
        """
        from quill.core.ai.model_manager import load_ai_enabled

        if not load_ai_enabled():
            return WatchActionOutcome.skipped(
                "AI is turned off. Enable it in Tools > AI Assistant to use this action."
            )
        mode = str(options.get("mode", "")).strip().lower()
        if mode not in {"summarize", "tag", "rewrite"}:
            return WatchActionOutcome.failed("Choose an AI mode: summarize, tag, or rewrite.")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not read file: {error}")
        assistant = self._get_assistant()
        try:
            if mode in {"summarize", "rewrite"}:
                result = assistant.transform(mode, text)
            else:  # tag
                result = assistant.ask(
                    "Read the following document and return a short, comma-separated "
                    "list of topical tags that describe it. Return only the tags:\n\n" + text
                )
        except Exception as error:  # surfaced as a failed outcome
            return WatchActionOutcome.failed(str(error))
        target = path.with_name(f"{path.stem}.{mode}.md")
        try:
            target.write_text(result, encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not write AI result: {error}")
        return WatchActionOutcome.done(f"AI {mode} written to {target.name}", result_path=target)

    def _refresh_voice_command_aliases(self) -> None:
        self._voice_command_aliases = build_voice_command_aliases(
            self.commands.list(),
            {
                "new document": "file.new",
                "open document": "file.open",
                "open file": "file.open",
                "save document": "file.save",
                "save as": "file.save_as",
                "close document": "file.close_document",
                "close file": "file.close_document",
                "command palette": "app.command_palette",
                "read aloud": "tools.read_aloud",
                "stop read aloud": "tools.read_aloud_stop",
                "dictation": "tools.dictation_toggle",
                "toggle dictation": "tools.dictation_toggle",
                "hey quill commands": "tools.dictation_voice_commands_toggle",
                "voice commands": "tools.dictation_voice_commands_toggle",
            },
        )

    def _cancel_voice_command_scan(self) -> None:
        timer = self._voice_command_scan_timer
        if timer is not None:
            timer.cancel()
        self._voice_command_scan_timer = None

    def _schedule_voice_command_scan(self) -> None:
        if not self.settings.voice_commands_enabled or self._dictation.state != "listening":
            return
        self._cancel_voice_command_scan()

        def run() -> None:
            self._wx.CallAfter(self._process_voice_command_transcript)

        timer = threading.Timer(1.2, run)
        timer.daemon = True
        self._voice_command_scan_timer = timer
        timer.start()

    def _process_voice_command_transcript(self) -> None:
        self._voice_command_scan_timer = None
        if self._voice_command_guard:
            return
        if not self.settings.voice_commands_enabled or self._dictation.state != "listening":
            return
        baseline = self._voice_command_baseline_text
        current_text = self.editor.GetValue()
        if not baseline or current_text == baseline:
            return
        _prefix, inserted, _suffix = split_text_delta(baseline, current_text)
        if not inserted.strip():
            return
        match = resolve_voice_command(inserted, self._voice_command_aliases)
        if match is None:
            self._voice_command_baseline_text = current_text
            return
        command = self.commands.get(match.command_id)
        if command is None or not self._feature_enabled(command.feature_id):
            self._voice_command_baseline_text = current_text
            self._set_status("Hey QUILL command is unavailable in this profile")
            return
        self._voice_command_guard = True
        try:
            self._replace_document_text(baseline)
            self.document.set_text(baseline)
            if not self._suspend_persistent_undo:
                self._record_persistent_undo_state(baseline)
            self.editor.SetInsertionPoint(len(baseline))
            self.editor.SetSelection(len(baseline), len(baseline))
            self._refresh_browser_preview()
            self._maybe_autosave()
        finally:
            self._voice_command_guard = False
        self._refresh_title()
        self._refresh_contextual_menu_items()
        self._set_status(f"Hey QUILL: {command.title}")
        command.handler()
        self._voice_command_baseline_text = self.editor.GetValue()

    def _on_dictation_state_change(self, state: str) -> None:
        if state == "listening":
            if self.settings.voice_commands_enabled:
                self._set_status(
                    'Windows dictation started. Say "Hey QUILL" plus a command to trigger Quill.'
                )
            else:
                self._set_status("Windows dictation started. Speak into the editor.")
        else:
            self._cancel_voice_command_scan()
            self._voice_command_baseline_text = ""
            self._set_status("Windows dictation stopped")

    def _on_dictation_error(self, error_msg: str) -> None:
        self._cancel_voice_command_scan()
        self._voice_command_baseline_text = ""
        self._set_status("Windows dictation error")

    def install_shell_integration(self) -> None:
        wx = self._wx
        command = launcher_command()
        plan = build_shell_integration_plan(command)
        summary = "\n".join(entry.path for entry in plan[:8])
        result = self._show_message_box(
            "Install per-user Open-with associations and shell verbs for Quill?",
            "Shell Integration",
            wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if result != wx.YES:
            self._set_status("Shell integration install cancelled")
            return
        install_shell_integration(command)
        try:
            apply_shell_verb_settings(self.settings)
        except Exception:  # pragma: no cover - registry best-effort
            pass
        self._show_message_box(
            f"Installed shell integration for:\n{summary}",
            "Shell Integration",
            wx.ICON_INFORMATION | wx.OK,
        )
        self._set_status("Installed shell integration")

    def remove_shell_integration(self) -> None:
        wx = self._wx
        result = self._show_message_box(
            "Remove Quill shell integration from this user account?",
            "Shell Integration",
            wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if result != wx.YES:
            self._set_status("Shell integration removal cancelled")
            return
        remove_shell_integration()
        try:
            remove_context_menu()
        except Exception:  # pragma: no cover - registry best-effort
            pass
        self._set_status("Removed shell integration")

    def open_notifications(self) -> None:
        wx = self._wx
        result = self._show_notifications_dialog()
        if result == wx.ID_CLEAR:
            clear_notifications()
            self._notifications = []
            self._set_status("Cleared notifications")
            return
        if self._notifications:
            self._set_status("Viewed notifications")
            return
        self._set_status("No notifications")

    def _show_notifications_dialog(self) -> int:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Notifications", size=(900, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Quill notifications appear below. Selecting a row copies it to the clipboard, "
                    "or use Copy Selected."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        lines = [
            f"{entry.timestamp} [{entry.category}] {entry.message}"
            for entry in self._notifications[-200:]
        ]
        chooser = wx.ListBox(dialog, choices=lines)
        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        copy_button = wx.Button(dialog, label="Copy Selected")
        clear_button = wx.Button(dialog, id=wx.ID_CLEAR, label="Clear Notifications")
        close_button = wx.Button(dialog, id=wx.ID_CLOSE, label="Close")
        button_row.Add(copy_button, 0, wx.RIGHT, 8)
        button_row.Add(clear_button, 0, wx.RIGHT, 8)
        button_row.AddStretchSpacer(1)
        button_row.Add(close_button, 0)
        root.Add(button_row, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)

        if lines:
            chooser.SetSelection(len(lines) - 1)
        else:
            chooser.Enable(False)
            copy_button.Enable(False)
            clear_button.Enable(False)

        def selected_line() -> str:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND:
                return ""
            return lines[selection]

        def copy_selected() -> None:
            value = selected_line()
            if not value:
                self._set_status("No notification selected")
                return
            if not self._copy_to_clipboard(value):
                self._set_status("Could not copy notification")
                return
            self._set_status("Copied notification to clipboard")

        chooser.Bind(wx.EVT_LISTBOX, lambda _e: copy_selected())
        copy_button.Bind(wx.EVT_BUTTON, lambda _e: copy_selected())
        clear_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLEAR))
        close_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
        apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)

        try:
            return self._show_modal_dialog(dialog, "Notifications")
        finally:
            dialog.Destroy()

    def show_help_status_page(self) -> None:
        self._ensure_status_page_timer()
        indexes = self._status_tab_indexes()
        if indexes:
            index = indexes[0]
            self._select_tab(index)
            self._refresh_help_status_tabs()
        else:
            report_html = self._build_help_status_html()
            index = self._open_generated_tab("Application Status", report_html)
            self._select_tab(index)
            if 0 <= index < len(self._document_tabs):
                self._show_side_preview_for(self._document_tabs[index])
        self._set_status_page_live_updates(True)
        self._set_status("Opened application status page in HTML preview with live updates")

    def _build_help_status_html(self) -> str:
        feature_rows: list[str] = []
        for feature_id, definition in sorted(FEATURE_DEFINITIONS.items()):
            state = self.features.state_for(feature_id)
            state_label = {
                "on": "Enabled",
                "quiet": "Quiet",
                "off": "Disabled",
            }.get(state, state)
            feature_rows.append(
                "<tr>"
                f"<td>{html.escape(feature_id)}</td>"
                f"<td>{html.escape(definition.name)}</td>"
                f"<td>{html.escape(definition.category)}</td>"
                f"<td>{html.escape(state_label)}</td>"
                "</tr>"
            )

        settings = self.settings
        speech_rows = [
            ("Engine", settings.read_aloud_engine),
            ("Voice (pyttsx3)", settings.read_aloud_voice or "(default system)"),
            ("DECtalk executable", settings.read_aloud_dectalk_executable or "Not configured"),
            ("DECtalk voice", settings.read_aloud_dectalk_voice),
            ("Piper executable", settings.read_aloud_piper_executable or "Not configured"),
            ("Piper model", settings.read_aloud_piper_model or "Not configured"),
            ("Kokoro voice", settings.read_aloud_kokoro_voice),
            ("eSpeak executable", settings.read_aloud_espeak_executable or "PATH lookup"),
            ("eSpeak English voice", settings.read_aloud_espeak_voice),
            ("OpenVoice executable", settings.read_aloud_openvoice_executable or "Not configured"),
            ("OpenVoice voice", settings.read_aloud_openvoice_voice),
            (
                "OpenVoice consent",
                "Enabled" if settings.read_aloud_openvoice_consent else "Disabled",
            ),
        ]
        speech_table_rows = "".join(
            f"<tr><th scope='row'>{html.escape(name)}</th><td>{html.escape(str(value))}</td></tr>"
            for name, value in speech_rows
        )

        bw_mode = str(getattr(settings, "bw_provider_mode", "local_first"))
        bw_local_first = bw_mode == "local_first"
        bw_provider_id = str(getattr(settings, "bw_provider_id", "local_whisper"))
        bw_provider = bw_get_provider(bw_provider_id, include_cloud=True)
        bw_recommended_provider = bw_recommended_provider_id(local_first=bw_local_first)
        bw_recommended_provider_spec = bw_get_provider(bw_recommended_provider, include_cloud=True)
        bw_ready = bw_provider_readiness(bw_provider_id, local_first=bw_local_first)
        bw_models = bw_list_models(include_parakeet=False)
        bw_downloaded = bw_downloaded_model_ids(include_parakeet=False)
        bw_engine_ok, bw_engine_status = faster_whisper_status()
        bw_rows = [
            ("Provider mode", "Local-first" if bw_local_first else "Cloud-first"),
            ("Configured provider", bw_provider.name if bw_provider else bw_provider_id),
            (
                "Recommended provider",
                bw_recommended_provider_spec.name
                if bw_recommended_provider_spec
                else bw_recommended_provider,
            ),
            ("Provider readiness", "Ready" if bw_ready.ready else "Needs setup"),
            ("Model mode", str(getattr(settings, "bw_speech_selection_mode", "recommended"))),
            (
                "Configured speech model",
                str(getattr(settings, "bw_speech_model_id", "whisper-base")),
            ),
            ("Whisper models downloaded", f"{len(bw_downloaded)} of {len(bw_models)}"),
            ("faster-whisper engine", "Ready" if bw_engine_ok else "Not installed"),
            ("Engine detail", bw_engine_status),
            ("Last refresh", datetime.now(UTC).isoformat()),
        ]
        bw_table_rows = "".join(
            f"<tr><th scope='row'>{html.escape(name)}</th><td>{html.escape(str(value))}</td></tr>"
            for name, value in bw_rows
        )

        bw_download_rows: list[str] = []
        for entry in sorted(
            self._bw_download_status.values(),
            key=lambda item: str(item.get("started_at", "")),
            reverse=True,
        ):
            bw_download_rows.append(
                "<tr>"
                f"<td>{html.escape(str(entry.get('model', '')))}</td>"
                f"<td>{html.escape(str(entry.get('status', '')))}</td>"
                f"<td>{html.escape(str(entry.get('progress', '')))}</td>"
                f"<td>{html.escape(str(entry.get('started_at', '')))}</td>"
                f"<td>{html.escape(str(entry.get('finished_at', 'Running')))}</td>"
                "</tr>"
            )
        if not bw_download_rows:
            bw_download_rows.append(
                "<tr><td colspan='5'>No BITS Whisperer model downloads "
                "have run in this session.</td></tr>"
            )

        task_rows: list[str] = []
        for task in reversed(getattr(self, "_background_tasks", [])[-50:]):
            label = str(task.get("label", ""))
            status = str(task.get("status", ""))
            progress = str(task.get("progress", ""))
            started_at = str(task.get("started_at", ""))
            finished_at = str(task.get("finished_at", ""))
            task_rows.append(
                "<tr>"
                f"<td>{html.escape(label)}</td>"
                f"<td>{html.escape(status.title())}</td>"
                f"<td>{html.escape(progress)}</td>"
                f"<td>{html.escape(started_at)}</td>"
                f"<td>{html.escape(finished_at or 'Running')}</td>"
                "</tr>"
            )
        if not task_rows:
            task_rows.append(
                "<tr><td colspan='5'>No background tasks have run in this session.</td></tr>"
            )

        notification_count = len(getattr(self, "_notifications", []))
        active_tasks = int(getattr(self, "_background_task_count", 0))
        profile_name = self.features.active_profile.name

        return (
            "<h1 id='status-page'>Quill Application Status</h1>"
            "<p>This page reports current runtime status for features, speech setup, "
            "and background downloads/tasks.</p>"
            "<h2 id='runtime-overview'>Runtime Overview</h2>"
            "<table>"
            "<caption>Current runtime summary</caption>"
            "<thead><tr><th scope='col'>Item</th><th scope='col'>Value</th></tr></thead>"
            "<tbody>"
            f"<tr><th scope='row'>Version</th><td>{html.escape(__version__)}</td></tr>"
            f"<tr><th scope='row'>Active profile</th><td>{html.escape(profile_name)}</td></tr>"
            f"<tr><th scope='row'>Background tasks running</th><td>{active_tasks}</td></tr>"
            f"<tr><th scope='row'>Notifications queued</th><td>{notification_count}</td></tr>"
            "</tbody></table>"
            "<h2 id='bw-rollout-status'>BITS Whisperer Rollout Status</h2>"
            "<table>"
            "<caption>Provider and model rollout readiness</caption>"
            "<thead><tr><th scope='col'>Item</th><th scope='col'>Value</th></tr></thead>"
            f"<tbody>{bw_table_rows}</tbody></table>"
            "<h2 id='speech-status'>Speech Status</h2>"
            "<table>"
            "<caption>Speech engine configuration and downloads</caption>"
            "<thead><tr><th scope='col'>Setting</th><th scope='col'>Value</th></tr></thead>"
            f"<tbody>{speech_table_rows}</tbody></table>"
            "<h2 id='bw-downloads'>BITS Whisperer Model Downloads</h2>"
            "<table>"
            "<caption>Asynchronous model acquisition jobs</caption>"
            "<thead><tr>"
            "<th scope='col'>Model</th><th scope='col'>Status</th><th scope='col'>Progress</th>"
            "<th scope='col'>Started</th><th scope='col'>Finished</th>"
            "</tr></thead>"
            f"<tbody>{''.join(bw_download_rows)}</tbody></table>"
            "<h2 id='background-tasks'>Background Tasks and Downloads</h2>"
            "<table>"
            "<caption>Recent asynchronous jobs (downloads, generation, indexing)</caption>"
            "<thead><tr>"
            "<th scope='col'>Task</th><th scope='col'>Status</th><th scope='col'>Progress</th>"
            "<th scope='col'>Started</th><th scope='col'>Finished</th>"
            "</tr></thead>"
            f"<tbody>{''.join(task_rows)}</tbody></table>"
            "<h2 id='features'>Feature Status</h2>"
            "<table>"
            "<caption>Enabled, quiet, and disabled features</caption>"
            "<thead><tr>"
            "<th scope='col'>Feature ID</th>"
            "<th scope='col'>Feature Name</th>"
            "<th scope='col'>Category</th>"
            "<th scope='col'>Status</th>"
            "</tr></thead>"
            f"<tbody>{''.join(feature_rows)}</tbody></table>"
            "<h2 id='recommended-actions'>Recommended Actions</h2>"
            "<ul>"
            "<li>Open BITS Whisperer &gt; Providers &gt; Provider Center "
            "for staged onboarding guidance.</li>"
            "<li>Open BITS Whisperer &gt; Speech Models to choose "
            "recommended or manual model setup.</li>"
            "<li>Open AI &gt; Speech &gt; Settings to configure engine-specific paths.</li>"
            "<li>Open AI &gt; Speech &gt; Voice to preview voices and variants.</li>"
            "<li>Open AI &gt; Speech &gt; Generate Audio to run "
            "asynchronous speech output jobs.</li>"
            "<li>Open Tools &gt; Support &gt; Show Notifications for "
            "detailed alerts and outcomes.</li>"
            "</ul>"
        )

    def _update_check_due(self, interval_hours: int = 24) -> bool:
        """True when enough time has passed since the last startup update check.

        Manual checks always run; this only throttles the silent startup check so
        QUILL doesn't hit the network on every single launch.
        """
        last = str(getattr(self.settings, "last_update_check", "") or "").strip()
        if not last:
            return True
        try:
            previous = datetime.fromisoformat(last)
        except ValueError:
            return True
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=UTC)
        return datetime.now(UTC) - previous >= timedelta(hours=interval_hours)

    def check_for_updates(self, silent_no_update: bool = False) -> None:
        if getattr(self, "_update_check_in_progress", False):
            if not silent_no_update:
                self._set_status("Update check already in progress")
            return

        wx = self._wx
        current_version = getattr(getattr(self, "_updates", None), "current_version", "")
        if not current_version:
            current_version = __version__ or "0.0.0"

        self.settings.last_update_check = datetime.now(UTC).isoformat()
        try:
            save_settings(self.settings)
        except Exception:  # noqa: BLE001
            pass

        if not silent_no_update:
            self._set_status("Checking for updates...")
            self._announce("Checking for updates")

        beta = bool(getattr(self.settings, "beta_updates", False))
        self._update_check_in_progress = True

        def _run_fetch():
            manifest: UpdateManifest | None = None
            releases: list[GitHubRelease] | None = None
            fetch_error: str | None = None
            try:
                try:
                    manifest = fetch_update_manifest(
                        "https://community-access.github.io/quill/updates/.quill-update-feed-v1.json"
                    )
                except (URLError, ValueError, OSError):
                    pass
                if manifest is None or not is_newer_version(current_version, manifest.version):
                    releases = fetch_releases()
            except (URLError, ValueError, OSError) as exc:
                fetch_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                fetch_error = str(exc)
            return manifest, releases, fetch_error

        call_after = getattr(wx, "CallAfter", None)
        if callable(call_after):
            import threading

            def _bg() -> None:
                m, r, e = _run_fetch()
                call_after(
                    self._on_update_fetch_done,
                    m,
                    r,
                    e,
                    silent_no_update,
                    current_version,
                    beta,
                )

            threading.Thread(  # GATE-40-OK: update-manifest fetcher; one-shot network.
                target=_bg, daemon=True
            ).start()
        else:
            # Synchronous fallback for test environments without wx.CallAfter.
            m, r, e = _run_fetch()
            self._on_update_fetch_done(m, r, e, silent_no_update, current_version, beta)

    def _on_update_fetch_done(
        self,
        manifest: UpdateManifest | None,
        releases: list[GitHubRelease] | None,
        fetch_error: str | None,
        silent_no_update: bool,
        current_version: str,
        beta: bool,
    ) -> None:
        """UI-thread callback once the background update-network fetch finishes."""
        self._update_check_in_progress = False
        wx = self._wx

        # Compatibility path: signed manifest feed.
        if manifest is not None and is_newer_version(current_version, manifest.version):
            if silent_no_update:
                self._record_notification(
                    f"Update {manifest.version} found via manifest feed", "update"
                )
                return
            download_now = self._show_message_box(
                f"Update {manifest.version} is available.\n\nOpen the update download now?",
                "Check for Updates",
                wx.ICON_INFORMATION | wx.YES_NO,
            )
            if download_now == wx.YES:
                self._open_update_download_flow(manifest)
            else:
                self._set_status("Update deferred")
                self._record_notification(f"Update {manifest.version} deferred", "update")
            return

        # Network error during GitHub releases fetch.
        if fetch_error is not None:
            if silent_no_update:
                self._record_notification(f"Update check failed: {fetch_error}", "update")
                self._set_status("Update check failed")
                return
            self._html_info(
                "Check for Updates",
                f"# Update check failed\n\nCould not check for updates:\n\n`{fetch_error}`",
            )
            self._set_status("Update check failed")
            self._announce("Update check failed")
            self._record_notification("Update check failed", "update")
            return

        releases = releases or []
        latest_any = select_latest(releases, include_prereleases=True)
        latest_stable = select_latest(releases, include_prereleases=False)

        # Auto-enroll in beta channel when running a prerelease build.
        current_match = find_release(releases, current_version)
        if not beta and current_match is not None and current_match.prerelease:
            self.settings.beta_updates = True
            save_settings(self.settings)
            beta = True
            self._record_notification(
                "You're running a beta build, so beta updates are enabled.", "update"
            )

        target = latest_any if beta else latest_stable
        if target is not None and is_newer_version(current_version, target.version):
            if silent_no_update and target.version == getattr(
                self.settings, "skipped_update_version", ""
            ):
                self._record_notification(
                    f"Update {target.version} available (skipped by you)", "update"
                )
                return
            if silent_no_update:
                self._record_notification(f"Update {target.version} found; downloading", "update")
                self._download_update_release(target)
                return
            action = self._show_update_available_dialog(current_version, target)
            if action == "download":
                self._download_update_release(target)
            elif action == "skip":
                self._skip_update_version(target.version)
            else:
                self._set_status("Update deferred")
                self._record_notification(f"Update {target.version} deferred", "update")
            return

        # No update on current channel — check if a prerelease is available on stable.
        prerelease_available = (
            not beta
            and latest_any is not None
            and latest_any.prerelease
            and is_newer_version(current_version, latest_any.version)
        )
        if prerelease_available:
            if silent_no_update:
                self._record_notification(
                    f"A beta build {latest_any.version} is available. "
                    "Enable beta updates to install it.",
                    "update",
                )
                self._set_status("Beta update available")
                return
            self._route_prerelease_to_beta(current_version, latest_any)
            return

        # Genuinely up to date.
        if silent_no_update:
            self._record_notification("Update check found no newer version", "update")
            return
        self._set_status("No update available")
        self._announce("Quill is up to date")
        self._record_notification("Update check found no newer version", "update")
        if beta:
            self._html_info(
                "Check for Updates",
                "# You're up to date\n\n"
                "You're on the **beta** channel and running the newest build.\n\n"
                f"**Current version:** {current_version}",
            )
        else:
            self._offer_beta_switch(current_version, latest_stable)

    def _route_prerelease_to_beta(self, current_version: str, release: GitHubRelease) -> None:
        """A prerelease is available while on stable — enroll in beta (with the
        consent gate), then offer the prerelease for download."""
        if not self._confirm_beta_channel(release):
            self._set_status("Stayed on the stable channel")
            return
        self.settings.beta_updates = True
        save_settings(self.settings)
        self._set_status("Switched to the beta update channel")
        self._announce("Beta updates enabled")
        action = self._show_update_available_dialog(current_version, release)
        if action == "download":
            self._download_update_release(release)
        elif action == "skip":
            self._skip_update_version(release.version)

    def _render_html(self, markdown_text: str) -> str:
        from quill.core.browser_preview import render_preview_body

        return render_preview_body(markdown_text, "markdown")

    def _vendored_glow_wheels_dir(self) -> Path | None:
        """The directory holding QUILL's vendored GLOW wheels (rollback floor)."""
        candidate = Path(__file__).resolve().parents[2] / "vendor" / "wheels"
        if candidate.is_dir():
            return candidate
        # Frozen builds may place vendored wheels beside the interpreter prefix.
        alt = Path(sys.prefix) / "vendor" / "wheels"
        return alt if alt.is_dir() else None

    def check_for_glow_updates(self, silent_no_update: bool = False) -> None:
        """Check for, and optionally apply, a newer GLOW accessibility engine.

        Opt-in and consented (GLOW-8): invoking this command is the explicit
        action that authorizes the network check; a second confirmation gate is
        shown before anything is downloaded or installed. The engine is verified
        (signed manifest, per-wheel SHA-256) and installed offline; a failed
        install rolls back to the vendored wheels. The new engine loads on
        restart.
        """
        wx = self._wx
        self._set_status("Checking for GLOW engine updates...")
        try:
            check: GlowUpdateCheck = check_for_glow_update()
        except (URLError, ValueError, OSError) as error:
            if silent_no_update:
                self._record_notification(f"GLOW update check failed: {error}", "update")
                self._set_status("GLOW update check failed")
                return
            self._html_info(
                "Check for GLOW Updates",
                f"# GLOW update check failed\n\nCould not check for updates:\n\n`{error}`",
            )
            self._set_status("GLOW update check failed")
            return

        if not check.update_available:
            if silent_no_update:
                self._record_notification("GLOW engine is up to date", "update")
                return
            installed = check.installed_version or "not installed"
            self._html_info(
                "Check for GLOW Updates",
                "# GLOW engine is up to date\n\n"
                f"**Installed:** {installed}  \n"
                f"**Latest:** {check.available_version}",
            )
            self._set_status("GLOW engine is up to date")
            return

        if silent_no_update:
            self._record_notification(
                f"GLOW engine {check.available_version} is available", "update"
            )
            self._set_status("GLOW update available")
            return

        manifest = check.manifest
        wheel_list = "\n".join(f"- `{w.filename}`" for w in manifest.wheels)
        notes = manifest.notes or "_(no release notes provided)_"
        proceed = self._show_message_box(
            (
                f"GLOW engine {manifest.version} is available "
                f"(installed: {check.installed_version or 'none'}).\n\n"
                f"{notes}\n\n"
                "This downloads and installs the engine, then QUILL must restart "
                "to apply it. Download and install now?"
            ),
            "Check for GLOW Updates",
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if proceed != wx.YES:
            self._set_status("GLOW update deferred")
            self._record_notification(f"GLOW update {manifest.version} deferred", "update")
            return

        import tempfile

        staging = Path(tempfile.mkdtemp(prefix="quill-glow-update-"))
        self._set_status(f"Downloading GLOW engine {manifest.version}...")
        result = apply_glow_update(
            manifest,
            staging,
            rollback_dir=self._vendored_glow_wheels_dir(),
        )
        if result.applied:
            self._html_info(
                "GLOW update complete",
                f"# GLOW engine updated to {manifest.version}\n\n"
                f"{wheel_list}\n\n"
                "**Restart QUILL** to load the new accessibility engine.",
            )
            self._set_status(f"GLOW engine updated to {manifest.version}; restart to apply")
            self._announce(f"GLOW engine updated to {manifest.version}. Restart to apply.")
            self._record_notification(
                f"GLOW engine updated to {manifest.version}; restart to apply", "update"
            )
        else:
            rollback = " The previous engine was restored." if result.rolled_back else ""
            self._html_info(
                "GLOW update failed",
                f"# GLOW update failed\n\n`{result.message}`{rollback}",
            )
            self._set_status("GLOW update failed")
            self._announce("GLOW update failed." + rollback)
            self._record_notification(f"GLOW update failed: {result.message}", "update")

    def _html_info(self, title: str, markdown_text: str) -> None:
        """Show an informational message in the WebView dialog (with an OK button)."""
        from quill.ui.preview_dialog import HtmlMessageDialog

        HtmlMessageDialog(
            self.frame, title, self._render_html(markdown_text), [("OK", self._wx.ID_OK)]
        ).show_modal()

    def _show_update_available_dialog(self, current_version: str, release: GitHubRelease) -> str:
        """Present an available update. Returns one of ``"download"``,
        ``"skip"`` (don't offer this version again) or ``"later"``."""
        from quill.ui.preview_dialog import HtmlMessageDialog

        wx = self._wx
        self._announce(f"Update available: {release.version}")
        channel = "Beta / prerelease" if release.prerelease else "Stable"
        notes = release.notes or "_(no release notes provided)_"
        if len(notes) > 600:
            notes = notes[:600] + "…"
        published = f"**Published:** {release.published_at}  \n" if release.published_at else ""
        body = self._render_html(
            f"# Update available: {release.version}\n\n"
            f"**Channel:** {channel}  \n"
            f"{published}"
            f"**Current version:** {current_version}\n\n"
            "## Release notes\n\n" + notes
        )
        result = HtmlMessageDialog(
            self.frame,
            "Check for Updates",
            body,
            [
                ("Skip this version", wx.ID_IGNORE),
                ("Later", wx.ID_CANCEL),
                ("Download update", wx.ID_OK),
            ],
        ).show_modal()
        if result == wx.ID_OK:
            return "download"
        if result == wx.ID_IGNORE:
            return "skip"
        return "later"

    def _skip_update_version(self, version: str) -> None:
        """Remember a version the user chose to skip so we stop offering it."""
        self.settings.skipped_update_version = version
        save_settings(self.settings)
        self._set_status(f"Skipping update {version}")
        self._record_notification(f"Update {version} skipped", "update")
        self._announce(f"Update {version} skipped")

    def _offer_beta_switch(
        self, current_version: str, stable_release: GitHubRelease | None
    ) -> None:
        from quill.ui.preview_dialog import HtmlMessageDialog

        wx = self._wx
        stable_line = (
            f"the latest stable release is {stable_release.version}"
            if stable_release is not None
            else "no stable release is published yet"
        )
        body = self._render_html(
            "# You're up to date\n\n"
            f"You're on the **stable** channel (current version {current_version}; "
            f"{stable_line}).\n\n"
            "Want earlier features sooner? The **beta** channel delivers prerelease "
            "builds as soon as they're published.\n"
        )
        result = HtmlMessageDialog(
            self.frame,
            "Check for Updates",
            body,
            [("Stay on stable", wx.ID_CANCEL), ("Switch to beta...", wx.ID_YES)],
        ).show_modal()
        if result == wx.ID_YES and self._confirm_beta_channel():
            self.settings.beta_updates = True
            save_settings(self.settings)
            self._set_status("Switched to the beta update channel")
            self._announce("Beta updates enabled")
            # Surface the latest prerelease right away so the user can install it,
            # even if its version matches the current build (they opted into beta).
            self._offer_latest_beta(current_version)

    def _offer_latest_beta(self, current_version: str) -> None:
        try:
            release = fetch_latest_release(include_prereleases=True)
        except (URLError, ValueError, OSError) as error:
            self._html_info(
                "Check for Updates",
                f"# Update check failed\n\nCould not check beta updates: {error}",
            )
            return
        if release is None:
            self._html_info(
                "Check for Updates",
                "# No beta build yet\n\nNo beta (prerelease) build is available yet.",
            )
            return
        action = self._show_update_available_dialog(current_version, release)
        if action == "download":
            self._download_update_release(release)
        elif action == "skip":
            self._skip_update_version(release.version)

    def _confirm_beta_channel(self, release: GitHubRelease | None = None) -> bool:
        """HTML consent gate the user must agree to before beta updates turn on."""
        from quill.ui.preview_dialog import HtmlMessageDialog

        wx = self._wx
        detected = (
            f"A beta build (**{release.version}**) is available.\n\n" if release is not None else ""
        )
        body = self._render_html(
            "# Enable beta updates?\n\n"
            f"{detected}"
            "Beta updates are **prerelease** builds. They get new features and fixes "
            "first, but they **may be unstable** — expect rough edges, and occasional "
            "bugs that could affect your documents.\n\n"
            "- Beta builds are published as GitHub prereleases.\n"
            "- You can switch back to stable anytime in Settings.\n"
            "- Keep backups of important documents.\n\n"
            "Do you understand and want to receive beta updates?"
        )
        result = HtmlMessageDialog(
            self.frame,
            "Beta updates",
            body,
            [("Cancel", wx.ID_CANCEL), ("I understand, enable beta", wx.ID_YES)],
        ).show_modal()
        return result == wx.ID_YES

    def _download_update_release(self, release: GitHubRelease) -> None:
        """Auto-download the release asset to <app data>/updates, off-thread,
        with accessible progress reporting and a post-download install offer.

        If the release has no downloadable asset, open its page instead.
        """
        import threading

        from quill.core.paths import app_data_dir

        url = release.download_url or ""
        if "/releases/download/" not in url:
            if url and webbrowser.open(url):
                self._set_status(f"Opened download page for {release.version}")
                self._record_notification(f"Opened update page for {release.version}", "update")
            else:
                self._set_status("No downloadable update asset found")
            return

        target_dir = app_data_dir() / "updates"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / (url.rsplit("/", 1)[-1] or f"quill-{release.version}")
        self._set_status(f"Downloading update {release.version}...")
        self._announce(f"Downloading update {release.version}")

        # Announce progress at coarse milestones so screen readers aren't flooded.
        last_milestone = {"value": -1}

        def report(done: int, total: int) -> None:
            if total <= 0:
                return
            percent = int(done * 100 / total)
            milestone = percent - (percent % 25)
            if milestone > last_milestone["value"] and milestone <= 100:
                last_milestone["value"] = milestone
                if milestone in (25, 50, 75):
                    self._wx.CallAfter(self._set_status, f"Downloading update… {milestone}%")
                    self._wx.CallAfter(self._announce, f"Update download {milestone} percent")

        def worker() -> None:
            try:
                download_release_asset(url, target, progress=report)
            except Exception as exc:  # noqa: BLE001
                self._wx.CallAfter(
                    self._record_notification, f"Update download failed: {exc}", "update"
                )
                self._wx.CallAfter(self._set_status, "Update download failed")
                return
            self._wx.CallAfter(
                self._record_notification,
                f"Update {release.version} downloaded to {target}",
                "update",
            )
            self._wx.CallAfter(self._set_status, f"Downloaded update {release.version}")
            self._wx.CallAfter(self._announce, f"Update {release.version} downloaded")
            self._wx.CallAfter(self._offer_post_download_actions, release, target)

        threading.Thread(  # GATE-40-OK: update asset download worker; bounded by size.
            target=worker, daemon=True
        ).start()

    def _offer_post_download_actions(self, release: GitHubRelease, target: Path) -> None:
        """After a successful download, let the user install it now or reveal it
        in the folder. Installer launch is offered only for runnable assets."""
        from quill.ui.preview_dialog import HtmlMessageDialog

        wx = self._wx
        runnable = target.suffix.lower() in {".exe", ".msi"} and sys.platform.startswith("win")
        buttons = [("Close", wx.ID_CANCEL), ("Open folder", wx.ID_OPEN)]
        if runnable:
            buttons.append(("Install now…", wx.ID_OK))
        install_line = (
            "Select **Install now** to close Quill and run the installer, or " if runnable else ""
        )
        body = self._render_html(
            f"# Update {release.version} downloaded\n\n"
            f"Saved to:\n\n`{target}`\n\n"
            f"{install_line}**Open folder** to find it yourself.\n"
        )
        result = HtmlMessageDialog(self.frame, "Update downloaded", body, buttons).show_modal()
        if result == wx.ID_OPEN:
            self._reveal_in_folder(target)
        elif result == wx.ID_OK and runnable:
            self._launch_installer(target)

    def _reveal_in_folder(self, target: Path) -> None:
        """Reveal the downloaded file in the OS file manager."""
        try:
            if sys.platform.startswith("win"):
                import subprocess

                subprocess.Popen(["explorer", "/select,", str(target)])  # noqa: S603, S607
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["open", "-R", str(target)])  # noqa: S603, S607
            else:
                webbrowser.open(target.parent.as_uri())
            self._set_status(f"Revealed {target.name}")
        except Exception as exc:  # noqa: BLE001
            self._record_notification(f"Could not open folder: {exc}", "update")
            self._set_status("Could not open download folder")

    def _launch_installer(self, target: Path) -> None:
        """Close Quill and launch the downloaded installer (Windows)."""
        if not self._can_close_all_documents():
            self._set_status("Install cancelled")
            self._record_notification("Update install cancelled before closing documents", "update")
            return
        try:
            os.startfile(str(target))  # type: ignore[attr-defined]  # noqa: S606
        except Exception as exc:  # noqa: BLE001
            self._record_notification(f"Could not launch installer: {exc}", "update")
            self._set_status("Could not launch installer")
            return
        self._record_notification(f"Launching installer {target.name}", "update")
        self._set_status("Closing Quill for installation")
        self.exit_app()

    def _open_update_download_flow(self, manifest: UpdateManifest) -> None:
        wx = self._wx
        close_now = self._show_message_box(
            (
                f"Quill installer update {manifest.version} requires the editor to close.\n\n"
                "Open the download page and close Quill now?"
            ),
            "Install Update",
            wx.ICON_INFORMATION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if close_now != wx.YES:
            opened = webbrowser.open(manifest.download_url)
            if opened:
                self._set_status(f"Opened download page for {manifest.version}")
                self._record_notification(
                    (
                        f"Opened update download for {manifest.version}. "
                        "Close Quill before running installer."
                    ),
                    "update",
                )
                return
            self._set_status("Could not open update download page")
            self._record_notification("Could not open update download page", "update")
            return
        if not self._can_close_all_documents():
            self._set_status("Update cancelled")
            self._record_notification(
                f"Update {manifest.version} cancelled before closing documents",
                "update",
            )
            return
        opened = webbrowser.open(manifest.download_url)
        if not opened:
            self._set_status("Could not open update download page")
            self._record_notification("Could not open update download page", "update")
            return
        self._record_notification(f"Opened update download for {manifest.version}", "update")
        self._set_status(f"Closing Quill for update {manifest.version}")
        self.exit_app()

    def validate_contrast(self) -> None:
        wx = self._wx
        checks = validate_theme_contrast(self.settings.theme)
        report = render_contrast_report(self.settings.theme, checks)
        self._show_message_box(report, "Contrast Validation", wx.ICON_INFORMATION | wx.OK)
        failed = [check for check in checks if not check.passes_normal_text]
        if failed:
            self._set_status("Contrast validation found failing pairs")
            self._record_notification("Contrast validation reported failures", "accessibility")
            return
        self._set_status("Contrast validation passed")
        self._record_notification("Contrast validation passed", "accessibility")

    def show_link_inventory(self) -> None:
        wx = self._wx
        inventory = collect_link_inventory(self.editor.GetValue())
        report = render_link_inventory_report(inventory)
        self._show_message_box(report, "Link Inventory", wx.ICON_INFORMATION | wx.OK)
        self._set_status(
            f"Link inventory: {len(inventory.links)} link(s), {len(inventory.images)} image(s)"
        )

    def compare_with_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Compare with file",
            wildcard=(
                "Text files (*.txt;*.md;*.html;*.htm;*.xhtml)|*.txt;*.md;*.html;*.htm;*.xhtml|"
                "All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Compare with file") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        other_document = read_text_document(target)
        source_documents = [
            (self.document.name, self.editor.GetValue()),
            (target.name, other_document.text),
        ]
        if not self._start_compare_session(source_documents):
            self._set_status(f"No differences from {target.name}")
            return
        current_name = self.document.name
        diff_text = build_unified_diff(
            self.editor.GetValue(),
            other_document.text,
            current_name,
            target.name,
        )
        max_chars = 12000
        if len(diff_text) > max_chars:
            diff_text = diff_text[:max_chars] + "\n... (truncated)\n"
        self._show_message_box(diff_text, "Compare with File", wx.ICON_INFORMATION | wx.OK)
        self._set_status(f"Compared with {target.name}")

    def compare_open_documents(self) -> None:
        if len(self._document_tabs) < 2:
            self._set_status("Open at least two documents to compare")
            return
        source_documents = [
            (tab.document.name, tab.editor.GetValue()) for tab in self._document_tabs
        ]
        if not self._start_compare_session(source_documents):
            self._set_status("No differences across open documents")
            return
        self._set_status(
            f"Compare session started. {len(source_documents)} documents. "
            f"{len(self._compare_session.groups)} differing line groups found."
        )

    def compare_next_difference(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        session.current_index = (session.current_index + 1) % len(session.groups)
        self.compare_announce_difference()

    def compare_previous_difference(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        session.current_index = (session.current_index - 1) % len(session.groups)
        self.compare_announce_difference()

    def compare_announce_difference(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        group = session.groups[session.current_index]
        if session.synchronized_navigation:
            self._focus_active_document_on_difference(group)
        self._set_status(self._render_compare_group(group, len(session.groups)))

    def open_compare_difference_list(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        wx = self._wx
        choices = [self._render_compare_choice(group) for group in session.groups]
        with wx.SingleChoiceDialog(
            self.frame,
            "Select a difference:",
            "Difference List",
            choices=choices,
        ) as dialog:
            dialog.SetSelection(session.current_index)
            if self._show_modal_dialog(dialog, "Difference List") != wx.ID_OK:
                return
            selection = dialog.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        session.current_index = selection
        self.compare_announce_difference()

    def toggle_compare_synchronization(self) -> None:
        session = self._compare_session
        if session is None:
            self._set_status("No active compare session")
            return
        session.synchronized_navigation = not session.synchronized_navigation
        state = "on" if session.synchronized_navigation else "off"
        self._set_status(f"Synchronized compare navigation {state}")

    def open_compare_options(self) -> None:
        wx = self._wx
        trailing = (
            self._show_message_box(
                "Ignore trailing spaces while comparing?",
                "Compare Options",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            == wx.YES
        )
        endings = (
            self._show_message_box(
                "Ignore line-ending differences (CRLF vs LF)?",
                "Compare Options",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            == wx.YES
        )
        self._compare_ignore_trailing_spaces = trailing
        self._compare_ignore_line_endings = endings
        session = self._compare_session
        if session is not None:
            self._start_compare_session(session.source_documents)
        self._set_status("Updated compare options")

    def create_compare_summary_document(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        summary = self._build_compare_summary_text(session)
        self._create_document_tab(
            Document(text=summary, path=None, modified=False),
            select=True,
        )
        self._set_status("Opened compare summary document")

    def copy_current_difference(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        group = session.groups[session.current_index]
        text = self._render_compare_group(group, len(session.groups))
        if not self._copy_to_clipboard(text):
            self._set_status("Could not copy current difference")
            return
        self._set_status("Copied current difference")

    def copy_all_differences(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        text = self._build_compare_summary_text(session)
        if not self._copy_to_clipboard(text):
            self._set_status("Could not copy all differences")
            return
        self._set_status("Copied all differences")

    def _start_compare_session(self, source_documents: list[tuple[str, str]]) -> bool:
        groups = self._build_compare_groups(source_documents)
        if not groups:
            self._compare_session = None
            return False
        self._compare_session = _CompareSession(source_documents=source_documents, groups=groups)
        self._set_status(
            f"Compare session started. {len(source_documents)} documents. "
            f"{len(groups)} differing line groups found. "
            "Press F8 for next difference, Shift+F8 for previous difference, "
            "Ctrl+F8 for current difference."
        )
        self.compare_announce_difference()
        return True

    def _build_compare_groups(
        self, source_documents: list[tuple[str, str]]
    ) -> list[_CompareDifferenceGroup]:
        if len(source_documents) < 2:
            return []
        split_lines = [text.splitlines() for _name, text in source_documents]
        max_lines = max((len(lines) for lines in split_lines), default=0)
        groups: list[_CompareDifferenceGroup] = []
        start_line: int | None = None

        def flush(end_line_exclusive: int) -> None:
            nonlocal start_line
            if start_line is None:
                return
            block_end = end_line_exclusive - 1
            groups.append(
                self._build_compare_group(
                    source_documents, split_lines, start_line, block_end, len(groups) + 1
                )
            )
            start_line = None

        for line_index in range(max_lines):
            normalized = [
                self._normalize_compare_line(lines[line_index]) if line_index < len(lines) else None
                for lines in split_lines
            ]
            baseline = normalized[0]
            same = all(value == baseline for value in normalized[1:])
            if same:
                flush(line_index)
                continue
            if start_line is None:
                start_line = line_index
        flush(max_lines)
        return groups

    def _build_compare_group(
        self,
        source_documents: list[tuple[str, str]],
        split_lines: list[list[str]],
        start_line: int,
        end_line: int,
        group_index: int,
    ) -> _CompareDifferenceGroup:
        blocks: list[_CompareLineBlock] = []
        for doc_index, (doc_name, _text) in enumerate(source_documents):
            lines = split_lines[doc_index]
            if start_line >= len(lines):
                blocks.append(_CompareLineBlock(doc_name, None, None, []))
                continue
            chunk = lines[start_line : min(end_line + 1, len(lines))]
            start = start_line + 1
            finish = start + len(chunk) - 1
            blocks.append(_CompareLineBlock(doc_name, start, finish, chunk))
        kind = self._classify_difference_kind(blocks)
        return _CompareDifferenceGroup(index=group_index, kind=kind, blocks=blocks)

    def _normalize_compare_line(self, line: str) -> str:
        normalized = line
        if self._compare_ignore_line_endings:
            normalized = normalized.rstrip("\r\n")
        if self._compare_ignore_trailing_spaces:
            normalized = normalized.rstrip()
        return normalized

    def _classify_difference_kind(self, blocks: list[_CompareLineBlock]) -> str:
        if len(blocks) != 2:
            return "changed"
        left_text = "\n".join(blocks[0].text)
        right_text = "\n".join(blocks[1].text)
        if not blocks[0].text and blocks[1].text:
            return "added"
        if blocks[0].text and not blocks[1].text:
            return "removed"
        if left_text == right_text:
            return "changed"
        if left_text.lower() == right_text.lower():
            return "case-only"
        left_compact = re.sub(r"\s+", "", left_text)
        right_compact = re.sub(r"\s+", "", right_text)
        if left_compact == right_compact:
            return "whitespace-only"
        left_punct = re.sub(r"[^\w\s]", "", left_text)
        right_punct = re.sub(r"[^\w\s]", "", right_text)
        if left_punct == right_punct:
            return "punctuation-only"
        if unicodedata.normalize("NFKC", left_text) == unicodedata.normalize("NFKC", right_text):
            return "unicode-only"
        return "changed"

    def _focus_active_document_on_difference(self, group: _CompareDifferenceGroup) -> None:
        active_name = self.document.name
        for block in group.blocks:
            if block.document_name != active_name or block.start_line is None:
                continue
            self._move_caret_to_line(block.start_line)
            return

    def _move_caret_to_line(self, line_number: int) -> None:
        if line_number < 1:
            return
        text = self.editor.GetValue()
        starts = [0]
        for line in text.splitlines(keepends=True):
            starts.append(starts[-1] + len(line))
        if line_number >= len(starts):
            position = starts[-1]
        else:
            position = starts[line_number - 1]
        self.editor.SetInsertionPoint(position)
        self.editor.SetSelection(position, position)

    def _render_compare_choice(self, group: _CompareDifferenceGroup) -> str:
        first = group.blocks[0]
        line_label = "line ?"
        if first.start_line is not None:
            line_label = f"line {first.start_line}"
        preview = ""
        if first.text:
            preview = first.text[0].strip()
        if preview:
            preview = f" {preview[:60]}"
        return f"Difference {group.index}: {group.kind} at {line_label}.{preview}"

    def _render_compare_group(self, group: _CompareDifferenceGroup, total: int) -> str:
        parts = [f"Difference {group.index} of {total}. {group.kind}."]
        for block in group.blocks:
            if block.start_line is None:
                parts.append(f"{block.document_name}: no corresponding lines.")
                continue
            if block.start_line == block.end_line:
                location = f"line {block.start_line}"
            else:
                location = f"lines {block.start_line}-{block.end_line}"
            preview = " ".join(block.text[:2]).strip()[:140] if block.text else "(empty)"
            parts.append(f"{block.document_name} {location}: {preview}")
        return " ".join(parts)

    def _build_compare_summary_text(self, session: _CompareSession) -> str:
        lines = [
            "Compare Summary",
            f"Documents: {', '.join(name for name, _text in session.source_documents)}",
            (
                "Options: "
                + (
                    "ignored trailing spaces"
                    if self._compare_ignore_trailing_spaces
                    else "kept trailing spaces"
                )
                + ", "
                + (
                    "ignored line endings"
                    if self._compare_ignore_line_endings
                    else "kept line endings"
                )
            ),
            "",
            f"{len(session.groups)} differences found.",
            "",
        ]
        for group in session.groups:
            lines.append(f"Difference {group.index}: {group.kind}")
            for block in group.blocks:
                if block.start_line is None:
                    lines.append(f"- {block.document_name}: no corresponding lines")
                    continue
                if block.start_line == block.end_line:
                    location = f"line {block.start_line}"
                else:
                    location = f"lines {block.start_line}-{block.end_line}"
                text = " | ".join(block.text[:3]).strip()
                lines.append(f"- {block.document_name} {location}: {text}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _prompt_search(
        self, title: str, replacement: bool = False
    ) -> tuple[str, str | None, SearchOptions] | None:
        from quill.ui.web_form import show_web_form

        default_query = self._last_find_query or (
            self._search_history[0] if self._search_history else ""
        )
        mode_labels = ["Plain text", "Whole word", "Regular expression", "Wildcard"]
        fields = [
            {
                "name": "query",
                "label": "Find text",
                "type": "text",
                "value": default_query,
            },
        ]
        if replacement:
            fields.append({
                "name": "replacement",
                "label": "Replace with",
                "type": "text",
                "value": "",
            })
        fields.extend([
            {
                "name": "mode",
                "label": "Search mode",
                "type": "select",
                "value": "Plain text",
                "options": [(label, label) for label in mode_labels],
            },
            {
                "name": "case_sensitive",
                "label": "Case sensitive",
                "type": "checkbox",
                "value": False,
            },
        ])
        values = show_web_form(
            self.frame,
            self._wx,
            title=title,
            fields=fields,
        )
        if values is None:
            return None
        query = str(values.get("query", "")).strip()
        if not query:
            return None
        mode = str(values.get("mode", "Plain text"))
        options = SearchOptions(
            case_sensitive=bool(values.get("case_sensitive", False)),
            whole_word=mode == "Whole word",
            use_regex=mode == "Regular expression",
            wildcard=mode == "Wildcard",
        )
        replacement_value = str(values.get("replacement", "")) if replacement else None
        return query, replacement_value, options

    def find_text(self) -> None:
        self._open_find_replace(replace=False)

    def _open_find_replace(self, replace: bool) -> None:
        """Open the native (modeless) wx.FindReplaceDialog for Find / Replace.

        Native dialog = reliable buttons, read directly by VoiceOver/NVDA, and
        the standard Find Next / Replace / Replace All flow. It carries
        case-sensitive + whole-word + direction; regex and wildcard searches
        stay available via Find All Matches / Search in Files.
        """
        wx = self._wx
        existing = getattr(self, "_find_replace_dialog", None)
        if existing is not None:
            # Recreate so toggling Find<->Replace works and it returns to front.
            existing.Destroy()
            self._find_replace_dialog = None
        flags = wx.FR_DOWN
        options = getattr(self, "_last_search_options", None)
        if options is not None:
            if getattr(options, "case_sensitive", False):
                flags |= wx.FR_MATCHCASE
            if getattr(options, "whole_word", False):
                flags |= wx.FR_WHOLEWORD
        data = wx.FindReplaceData(flags)
        seed = getattr(self, "_last_find_query", "") or (
            self._search_history[0] if self._search_history else ""
        )
        if seed:
            data.SetFindString(seed)
        self._find_replace_data = data  # keep a reference alive for the dialog
        style = wx.FR_REPLACEDIALOG if replace else 0
        dialog = wx.FindReplaceDialog(self.frame, data, "Replace" if replace else "Find", style)
        dialog.Bind(wx.EVT_FIND, self._on_find_event)
        dialog.Bind(wx.EVT_FIND_NEXT, self._on_find_event)
        dialog.Bind(wx.EVT_FIND_REPLACE, self._on_find_replace_event)
        dialog.Bind(wx.EVT_FIND_REPLACE_ALL, self._on_find_replace_all_event)
        dialog.Bind(wx.EVT_FIND_CLOSE, self._on_find_close_event)
        self._find_replace_dialog = dialog
        dialog.Show(True)
        dialog.Raise()

    def _search_options_from_flags(self, flags: int) -> SearchOptions:
        wx = self._wx
        return SearchOptions(
            case_sensitive=bool(flags & wx.FR_MATCHCASE),
            whole_word=bool(flags & wx.FR_WHOLEWORD),
            use_regex=False,
            wildcard=False,
        )

    def _on_find_event(self, event: object) -> None:
        query = event.GetFindString()
        if not query:
            return
        self._last_find_query = query
        self._last_search_options = self._search_options_from_flags(event.GetFlags())
        self._search_history = add_search_term(query)
        reverse = not bool(event.GetFlags() & self._wx.FR_DOWN)
        self._find_relative(reverse=reverse)

    def _on_find_replace_event(self, event: object) -> None:
        query = event.GetFindString()
        if not query:
            return
        options = self._search_options_from_flags(event.GetFlags())
        self._last_find_query = query
        self._last_search_options = options
        self._replace_current_match(query, event.GetReplaceString(), options)

    def _on_find_replace_all_event(self, event: object) -> None:
        wx = self._wx
        query = event.GetFindString()
        if not query:
            return
        options = self._search_options_from_flags(event.GetFlags())
        self._last_find_query = query
        self._last_search_options = options
        text = self.editor.GetValue()
        try:
            updated_text, replacements = replace_all(text, query, event.GetReplaceString(), options)
        except SearchPatternError as error:
            self._show_message_box(str(error), "Replace All", wx.ICON_ERROR | wx.OK)
            return
        if replacements == 0:
            self._set_status("No replacements made")
            return
        self._replace_document_text(updated_text)
        self.document.set_text(updated_text)
        self._set_status(f"Replaced {replacements} occurrence(s)")

    def _on_find_close_event(self, _event: object) -> None:
        dialog = getattr(self, "_find_replace_dialog", None)
        if dialog is not None:
            dialog.Destroy()
        self._find_replace_dialog = None
        self._find_replace_data = None

    def _replace_current_match(self, query: str, replacement: str, options: SearchOptions) -> None:
        wx = self._wx
        text = self.editor.GetValue()
        try:
            matches = find_matches(text, query, options)
        except SearchPatternError as error:
            self._show_message_box(str(error), "Replace", wx.ICON_ERROR | wx.OK)
            return
        if not matches:
            self._set_status("No replacements made")
            return
        sel_start, sel_end = self.editor.GetSelection()
        chosen: tuple[int, int] | None = None
        wrapped = False
        if sel_start != sel_end and (sel_start, sel_end) in matches:
            chosen = (sel_start, sel_end)
        else:
            cursor = sel_end if sel_start != sel_end else self.editor.GetInsertionPoint()
            for start, end in matches:
                if start >= cursor:
                    chosen = (start, end)
                    break
            if chosen is None and self.settings.wrap_find:
                chosen = matches[0]
                wrapped = True
        if chosen is None:
            self._set_status("No replacements made from the current position")
            return
        start, end = chosen
        updated_text = text[:start] + replacement + text[end:]
        self._replace_document_text(updated_text)
        self.document.set_text(updated_text)
        replaced_end = start + len(replacement)
        self.editor.SetSelection(start, replaced_end)
        self.editor.SetInsertionPoint(replaced_end)
        self._last_match = (start, replaced_end)
        wrap_suffix = (
            " (wrapped)" if wrapped and getattr(self.settings, "announce_wrap", True) else ""
        )
        self._set_status(f"Replaced at position {start + 1}{wrap_suffix}")

    def find_next(self) -> None:
        self._find_relative(reverse=False)

    def find_previous(self) -> None:
        self._find_relative(reverse=True)

    def _find_relative(self, reverse: bool) -> None:
        if not self._last_find_query:
            self.find_text()
            return

        text = self.editor.GetValue()
        try:
            matches = find_matches(text, self._last_find_query, self._last_search_options)
        except SearchPatternError as error:
            self._show_message_box(str(error), "Find", self._wx.ICON_ERROR | self._wx.OK)
            self._set_status("Find error")
            return
        if not matches:
            self._set_status("No matches found")
            from quill.core.sound_events import SoundEvent
            from quill.ui.sound_manager import post_sound

            post_sound(SoundEvent.SEARCH_NOT_FOUND)
            return

        cursor = self.editor.GetInsertionPoint()
        selected_start, selected_end = self.editor.GetSelection()
        if selected_start != selected_end:
            cursor = selected_start if reverse else selected_end

        chosen: tuple[int, int] | None = None
        wrapped = False
        if reverse:
            for start, end in reversed(matches):
                if end <= cursor:
                    chosen = (start, end)
                    break
            if chosen is None and self.settings.wrap_find:
                chosen = matches[-1]
                wrapped = True
        else:
            for start, end in matches:
                if start >= cursor:
                    chosen = (start, end)
                    break
            if chosen is None and self.settings.wrap_find:
                chosen = matches[0]
                wrapped = True

        if chosen is None:
            self._set_status("No matches found from the current position")
            from quill.core.sound_events import SoundEvent
            from quill.ui.sound_manager import post_sound

            post_sound(SoundEvent.SEARCH_NOT_FOUND)
            return

        start, end = chosen
        self.editor.SetFocus()
        self._ensure_extend_selection_anchor()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(start if reverse else end)
        else:
            self.editor.SetSelection(start, end)
            self.editor.SetInsertionPoint(end)
        self._last_match = chosen
        direction = "previous" if reverse else "next"
        wrap_suffix = (
            " (wrapped)" if wrapped and getattr(self.settings, "announce_wrap", True) else ""
        )
        self._set_status(f"Found {direction} at position {start + 1}{wrap_suffix}")
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        post_sound(SoundEvent.SEARCH_WRAPPED if wrapped else SoundEvent.SEARCH_FOUND)

    def _ensure_extend_selection_anchor(self) -> None:
        if not self._extend_selection_mode or self._extend_selection_anchor is not None:
            return
        selection_start, selection_end = self.editor.GetSelection()
        if selection_start != selection_end:
            self._extend_selection_anchor = selection_start
            return
        self._extend_selection_anchor = self.editor.GetInsertionPoint()

    def find_all_matches(self) -> None:
        wx = self._wx
        if not self._last_find_query:
            # Rich modal prompt here keeps regex / wildcard search available
            # (the native Find dialog only does case / whole-word / direction).
            prompt = self._prompt_search("Find All Matches")
            if prompt is None:
                return
            query, _replacement, options = prompt
            if not query:
                return
            self._last_find_query = query
            self._last_search_options = options
            self._search_history = add_search_term(query)

        text = self.editor.GetValue()
        try:
            matches = find_matches(text, self._last_find_query, self._last_search_options)
        except SearchPatternError as error:
            self._show_message_box(str(error), "Find All Matches", wx.ICON_ERROR | wx.OK)
            self._set_status("Find error")
            return
        if not matches:
            self._show_message_box(
                "No matches found.",
                "Find All Matches",
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("No matches found")
            return

        lines = text.splitlines(keepends=True)
        starts = [0]
        for line in lines:
            starts.append(starts[-1] + len(line))

        def locate(position: int) -> tuple[int, int]:
            line_number = 1
            for index in range(1, len(starts)):
                if starts[index] > position:
                    line_number = index
                    break
            else:
                line_number = max(1, len(starts) - 1)
            column = position - starts[line_number - 1] + 1
            return line_number, column

        details: list[str] = []
        for idx, (start, _end) in enumerate(matches[:25], start=1):
            line_number, column = locate(start)
            details.append(f"{idx}. Line {line_number}, Column {column}")
        more = ""
        if len(matches) > 25:
            more = f"\n...and {len(matches) - 25} more"

        self._show_message_box(
            f'Matches for "{self._last_find_query}": {len(matches)}\n\n'
            + "\n".join(details)
            + more,
            "Find All Matches",
            wx.ICON_INFORMATION | wx.OK,
        )
        self._set_status(f"Found {len(matches)} match(es)")

    def replace_text(self) -> None:
        self._open_find_replace(replace=True)

    def replace_all_text(self) -> None:
        # The native Replace dialog has its own Replace All button.
        self._open_find_replace(replace=True)

    def _prompt_file_search(self, *, replace: bool) -> _FileSearchRequest | None:
        wx = self._wx
        default_root = self.document.path.parent if self.document.path is not None else Path.cwd()
        dialog_label = "Replace Across Files" if replace else "Search in Files"
        dialog = wx.Dialog(
            self.frame,
            title=dialog_label,
            size=(700, 0),
        )
        root = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(0, 3, 8, 8)
        form.AddGrowableCol(1, 1)

        def add_row(label: str, make_ctrl, button: object | None = None) -> object:
            form.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = make_ctrl()
            form.Add(ctrl, 1, wx.EXPAND)
            if button is None:
                form.AddSpacer(1)
            else:
                form.Add(button, 0)
            return ctrl

        folder_picker = add_row(
            "Starting folder", lambda: wx.DirPickerCtrl(dialog, path=str(default_root))
        )
        file_pattern_ctrl = add_row("File pattern", lambda: wx.TextCtrl(dialog, value="*"))
        query_ctrl = add_row(
            "Search text", lambda: wx.TextCtrl(dialog, value="", style=wx.TE_PROCESS_ENTER)
        )

        replacement_ctrl = None
        if replace:
            replacement_ctrl = add_row(
                "Replacement",
                lambda: wx.TextCtrl(dialog, value="", style=wx.TE_PROCESS_ENTER),
            )

        mode_choice = add_row(
            "Match mode",
            lambda: wx.Choice(dialog, choices=["Plain text", "Wildcard", "Regular expression"]),
        )
        mode_choice.SetSelection(0)

        output_choice = add_row(
            "Output format",
            lambda: wx.Choice(
                dialog,
                choices=[
                    "Filenames only",
                    "Filenames with line numbers and counts",
                    "Counts only",
                    "Filename with line context",
                ],
            ),
        )
        output_choice.SetSelection(3)

        case_sensitive = wx.CheckBox(dialog, label="Case sensitive")
        whole_word = wx.CheckBox(dialog, label="Whole word")
        root.Add(form, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(case_sensitive, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        root.Add(whole_word, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        preview_before_replace = None
        if replace:
            preview_before_replace = wx.CheckBox(dialog, label="Preview before replacing")
            preview_before_replace.SetValue(True)
            root.Add(preview_before_replace, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            # Mirror the proven single-document search dialog (_prompt_search):
            # a StdDialogButtonSizer must be added with wx.EXPAND, not
            # wx.ALIGN_RIGHT. Adding it right-aligned left the OK/Cancel buttons
            # unrealized on Windows, so the Cancel button could not be clicked
            # and the dialog trapped the user (#84). EXPAND plus an explicit
            # default button restores reliable, keyboard-accessible dismissal.
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizerAndFit(root)

        def submit(_event: object) -> None:
            dialog.EndModal(wx.ID_OK)

        query_ctrl.Bind(wx.EVT_TEXT_ENTER, submit)
        if replacement_ctrl is not None:
            replacement_ctrl.Bind(wx.EVT_TEXT_ENTER, submit)

        def focus_query() -> None:
            query_ctrl.SetFocus()

        if hasattr(wx, "CallAfter"):
            wx.CallAfter(focus_query)
        else:
            focus_query()

        try:
            if self._show_modal_dialog(dialog, dialog_label) != wx.ID_OK:
                return None
            query = query_ctrl.GetValue().strip()
            if not query:
                self._show_message_box(
                    "Search text cannot be blank.",
                    dialog_label,
                    wx.ICON_ERROR | wx.OK,
                )
                return None
            mode = mode_choice.GetStringSelection()
            options = SearchOptions(
                case_sensitive=bool(case_sensitive.GetValue()),
                whole_word=bool(whole_word.GetValue()),
                use_regex=mode == "Regular expression",
                wildcard=mode == "Wildcard",
            )
            replacement_value = (
                replacement_ctrl.GetValue() if replacement_ctrl is not None else None
            )
            preview = (
                bool(preview_before_replace.GetValue())
                if preview_before_replace is not None
                else False
            )
            output_modes = (
                "filenames",
                "filenames_lines_counts",
                "counts",
                "context",
            )
            return _FileSearchRequest(
                root=Path(folder_picker.GetPath()),
                pattern=file_pattern_ctrl.GetValue().strip() or "*",
                query=query,
                replacement=replacement_value,
                options=options,
                output_mode=output_modes[
                    max(0, min(output_choice.GetSelection(), len(output_modes) - 1))
                ],
                preview_before_replace=preview,
            )
        finally:
            dialog.Destroy()

    def search_in_files(self) -> None:
        request = self._prompt_file_search(replace=False)
        if request is None:
            self._set_status("Search in files cancelled")
            return

        def work(progress: Callable[[str, int, int], None]) -> FileSearchReport:
            return search_files(
                request.root,
                request.pattern,
                request.query,
                request.options,
                progress=progress,
            )

        def on_success(result: object) -> None:
            report = result if isinstance(result, FileSearchReport) else None
            if report is None:
                return
            text = render_search_report(report, request.output_mode)
            self._open_generated_tab(f"Search - {request.pattern}", text)
            match_count = report.total_matches
            file_count = len(report.entries)
            self._set_status(f"Search complete: {match_count} match(es) in {file_count} file(s)")

        self._run_background_task("Searching files", work, on_success)

    def replace_in_files(self) -> None:
        request = self._prompt_file_search(replace=True)
        if request is None:
            self._set_status("Replace across files cancelled")
            return
        replacement = request.replacement or ""

        if not request.preview_before_replace:
            self._start_replace_files(request, replacement)
            return

        def preview_work(progress: Callable[[str, int, int], None]) -> FileSearchReport:
            return search_files(
                request.root,
                request.pattern,
                request.query,
                request.options,
                progress=progress,
            )

        def preview_done(result: object) -> None:
            report = result if isinstance(result, FileSearchReport) else None
            if report is None:
                return
            text = render_replace_preview(report, replacement)
            self._open_generated_tab(f"Replace Preview - {request.pattern}", text)
            if report.total_matches == 0:
                self._set_status("No matches found")
                return
            confirm = self._show_message_box(
                "Apply these replacements across files?",
                "Replace Across Files",
                self._wx.ICON_QUESTION | self._wx.YES_NO | self._wx.NO_DEFAULT,
            )
            if confirm == self._wx.YES:
                self._start_replace_files(request, replacement)
                return
            self._set_status("Replace across files cancelled")

        self._run_background_task("Previewing file replacements", preview_work, preview_done)

    def _start_replace_files(self, request: _FileSearchRequest, replacement: str) -> None:
        def work(progress: Callable[[str, int, int], None]) -> FileReplaceReport:
            return replace_files(
                request.root,
                request.pattern,
                request.query,
                replacement,
                request.options,
                progress=progress,
            )

        def on_success(result: object) -> None:
            report = result if isinstance(result, FileReplaceReport) else None
            if report is None:
                return
            text = render_replace_report(report)
            self._open_generated_tab(f"Replace Results - {request.pattern}", text)
            replacement_count = report.total_replacements
            file_count = len(report.entries)
            self._set_status(f"Replaced {replacement_count} occurrence(s) in {file_count} file(s)")

        self._run_background_task("Replacing files", work, on_success)

    def insert_link(self) -> None:
        from quill.ui.web_form import show_web_form

        selected_text = self.editor.GetStringSelection()
        values = show_web_form(
            self.frame,
            self._wx,
            title="Insert Link",
            intro=("Enter the text to display and the destination URL, then choose Insert."),
            save_label="Insert",
            fields=[
                {
                    "name": "display_text",
                    "label": "Display text",
                    "type": "text",
                    "value": selected_text or "",
                },
                {
                    "name": "url",
                    "label": "URL",
                    "type": "text",
                    "value": "https://",
                },
            ],
        )
        if values is None:
            self._set_status("Insert link cancelled")
            return

        url = str(values.get("url", "")).strip()
        display_text = str(values.get("display_text", ""))
        if not url:
            self._set_status("Insert link cancelled")
            return

        markup_kind = infer_markup_kind(self.document.path)
        snippet = build_link_text(markup_kind, display_text, url)
        result = InsertionResult(inserted_text=snippet, caret_offset=len(snippet))
        self._apply_insertion_result(result)
        self._set_status(f"Inserted link ({markup_kind})")

    def follow_link(self) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        target = find_link_at_cursor(text, cursor)
        if not target:
            self._set_status("No link at cursor")
            return
        if target.startswith("#"):
            self._set_status("Anchor links are not yet supported")
            return

        import webbrowser
        from urllib.parse import urlparse

        host = urlparse(target).netloc or target
        self._set_status(f"Opening {host}...")
        webbrowser.open(target)

    def preview_in_browser(self) -> None:
        if not self._document_tabs:
            self._set_status("No document open")
            return
        tab_index = (
            self._active_tab_index if self._active_tab_index >= 0 else self._current_tab_index()
        )
        if tab_index < 0 or tab_index >= len(self._document_tabs):
            self._set_status("No document open")
            return
        tab = self._document_tabs[tab_index]
        text = tab.editor.GetValue()
        kind = guess_preview_kind(tab.document.path, text)
        anchor = preview_anchor_for_text(text, tab.editor.GetInsertionPoint(), kind)
        title = f"{tab.document.name or 'Preview'} - Browser Preview"
        preview_dir = app_data_dir() / "browser-preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        safe_name = (
            re.sub(r"[^a-zA-Z0-9]+", "-", tab.document.name or "preview").strip("-") or "preview"
        )
        preview_path = preview_dir / f"{tab_index}-{safe_name}.html"
        payload = render_preview_html(title, text, kind, anchor)
        temp_path = preview_path.with_suffix(".tmp")
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, preview_path)
        browser_choice = normalize_browser_choice(self.settings.preview_browser)
        session = self._browser_preview_session
        if (
            session is None
            or session.tab_index != tab_index
            or session.preview_path != preview_path
            or session.browser_choice != browser_choice
        ):
            open_preview_url(preview_path.as_uri(), browser_choice)
            self._browser_preview_session = _BrowserPreviewSession(
                tab_index=tab_index,
                preview_path=preview_path,
                browser_choice=browser_choice,
                title=title,
            )
            self._set_status(
                f"Opened browser preview in {browser_choice_label_for_value(browser_choice)}"
            )
            return
        self._set_status("Refreshed browser preview")

    def preview_in_app(self) -> None:
        if not self._document_tabs:
            self._set_status("No document open")
            return
        tab_index = (
            self._active_tab_index if self._active_tab_index >= 0 else self._current_tab_index()
        )
        if tab_index < 0 or tab_index >= len(self._document_tabs):
            self._set_status("No document open")
            return
        tab = self._document_tabs[tab_index]
        text = tab.editor.GetValue()
        kind = guess_preview_kind(tab.document.path, text)
        anchor = preview_anchor_for_text(text, tab.editor.GetInsertionPoint(), kind)
        title = f"{tab.document.name or 'Preview'} - Preview"
        body = render_preview_body(text, kind, dark=self._preview_is_dark())
        from quill.ui.preview_dialog import MarkdownPreviewDialog

        MarkdownPreviewDialog(self.frame, title, body, anchor).show()
        self._set_status("Opened preview")

    def _active_tab(self):
        index = self._active_tab_index if self._active_tab_index >= 0 else self._current_tab_index()
        if 0 <= index < len(self._document_tabs):
            return self._document_tabs[index]
        return None

    def toggle_side_preview(self) -> None:
        """Show / hide a live preview to the right of the editor (split view)."""
        tab = self._active_tab()
        if tab is None or getattr(tab, "splitter", None) is None:
            self._set_status("No document open")
            return
        splitter = tab.splitter
        if tab.preview is not None and splitter.IsSplit():
            splitter.Unsplit(tab.preview.control)
            self._set_status("Preview hidden")
            self.editor.SetFocus()
            self._set_active_region("Editor")
            return
        self._show_side_preview_for(tab)
        self._set_status("Preview shown on the right")

    def focus_preview(self) -> None:
        """Move focus into the preview pane (showing it first if needed).

        The editor is an edit field, so NVDA can't use browse-mode single-letter
        navigation there. The preview is a real web document, so once focus lands
        in it NVDA switches to browse mode and H / heading nav work natively.
        Press Escape or F6 in the preview to come back to the editor.
        """
        tab = self._active_tab()
        if tab is None or getattr(tab, "splitter", None) is None:
            self._set_status("No document open")
            return
        if tab.preview is None or not tab.splitter.IsSplit():
            self.toggle_side_preview()
        if tab.preview is not None and tab.splitter.IsSplit():
            tab.preview.control.SetFocus()
            self._set_active_region("Preview")
            self._set_status("Moved to preview. Press Escape or F6 to return to the editor.")

    def _focus_editor_from_preview(self) -> None:
        if self.editor is not None:
            self.editor.SetFocus()
            self._set_active_region("Editor")
            self._set_status("Back in the editor")

    def _refresh_side_preview(self) -> None:
        tab = self._active_tab()
        if tab is None:
            return
        splitter = getattr(tab, "splitter", None)
        if splitter is None:
            return
        if not splitter.IsSplit():
            if getattr(self.settings, "auto_side_preview", True):
                text = tab.editor.GetValue()
                if guess_preview_kind(tab.document.path, text) != "plain":
                    self._show_side_preview_for(tab)
            return
        if tab.preview is None:
            return
        # Debounce: refresh shortly after typing pauses so each keystroke stays
        # snappy (re-rendering on every character can stutter the editor).
        timer = getattr(self, "_side_preview_timer", None)
        if timer is not None and timer.IsRunning():
            timer.Stop()
        self._side_preview_timer = self._wx.CallLater(250, self._update_side_preview, tab)

    def _update_side_preview(self, tab) -> None:
        text = tab.editor.GetValue()
        kind = guess_preview_kind(tab.document.path, text)
        try:
            tab.preview.update(render_preview_body(text, kind, dark=self._preview_is_dark()))
        except Exception:
            # WebView2 can enter ERROR_INVALID_STATE (0x8007139f) after a forced
            # close or navigation error; JS/SetPage calls then raise. Discard the
            # faulted control and let _show_side_preview_for rebuild it.
            splitter = getattr(tab, "splitter", None)
            if splitter is not None and splitter.IsSplit():
                try:
                    splitter.Unsplit()
                except Exception:
                    pass
            tab.preview = None
            self._wx.CallAfter(self._show_side_preview_for, tab)

    def _prewarm_webview_runtime(self) -> None:
        """Initialise the WebView2 subprocess early so preview opens are instant.

        wx.html2.WebView.New() launches the Edge WebView2 process on the first
        call. On Windows this can take several seconds — occasionally minutes —
        the first time (COM init, Edge runtime discovery, subprocess spawn). All
        subsequent calls reuse the same subprocess and are near-instant.

        Creating and immediately destroying a 1×1 hidden WebView here (during
        the deferred startup task list, after the main window is visible) pays
        that one-time cost before the user presses F6 or the AI chat pane opens.
        The visible startup delay (#177) and the F6 freeze (#174) both trace back
        to this initialisation happening on the user's first interaction instead.

        No-ops silently if wx.html2 is unavailable (Linux/macOS without WebKit,
        or if the runtime was not installed).
        """
        try:
            import wx.html2

            sentinel = self._wx.Panel(self.frame, size=(1, 1))
            sentinel.Hide()
            # WebView.New() alone is enough to trigger WebView2 process
            # initialisation — no page load required.  WebView2 fires
            # EVT_WEBVIEW_LOADED for the implicit about:blank navigation; we
            # destroy the sentinel then.  A 5-second fallback timer covers the
            # case where the load event never arrives (e.g. no WebView2 runtime).
            # No explicit page load needed — WebView2 navigates to about:blank on
            # its own.  Explicit raw-HTML page calls are disallowed here by the
            # web-surface governance gate (test_web_surface_governance.py).
            wv = wx.html2.WebView.New(sentinel)

            # _alive guards both the EVT_WEBVIEW_LOADED callback and the
            # 5-second fallback CallLater against calling methods on C++
            # objects that have already been destroyed.  The parent frame
            # may close (e.g. during startup profiling) before the fallback
            # timer fires; EVT_WINDOW_DESTROY clears the flag so the
            # CallLater becomes a no-op instead of an access violation.
            _alive = [True]
            sentinel.Bind(wx.EVT_WINDOW_DESTROY, lambda _e: _alive.__setitem__(0, False))

            def _cleanup(_evt: object = None) -> None:
                if not _alive[0]:
                    return
                _alive[0] = False
                try:
                    wv.Unbind(wx.html2.EVT_WEBVIEW_LOADED, handler=_cleanup)
                    sentinel.Destroy()
                except Exception:
                    pass

            wv.Bind(wx.html2.EVT_WEBVIEW_LOADED, _cleanup)
            self._wx.CallLater(5000, _cleanup)
        except Exception:
            pass

    def _preview_is_dark(self) -> bool:
        """Whether preview surfaces should render with the dark theme (issue #83).

        Dark mode themes the wx editor control; the preview is a separate
        WebView that otherwise stays light, leaving the split view half dark and
        half bright. Mirror the editor's dark state so both panes match.

        The default ``system`` theme follows the OS appearance, so a user on a
        dark desktop saw light preview panes with low-contrast blue links
        (issue #126). Resolve ``system`` against the live wx system appearance so
        the preview tracks the OS instead of staying bright.
        """
        theme = getattr(self.settings, "theme", "system")
        if theme == "dark":
            return True
        if theme in ("system", "auto"):
            return self._system_appearance_is_dark()
        return False

    def _system_appearance_is_dark(self) -> bool:
        """Best-effort detection of an OS-level dark appearance via wx."""
        getter = getattr(self._wx, "SystemSettings", None)
        appearance_getter = getattr(getter, "GetAppearance", None) if getter else None
        if callable(appearance_getter):
            try:
                appearance = appearance_getter()
            except Exception:  # noqa: BLE001 - probing must never crash the preview
                appearance = None
            for probe in ("IsDark", "IsUsingDarkBackground"):
                method = getattr(appearance, probe, None)
                if callable(method):
                    try:
                        return bool(method())
                    except Exception:  # noqa: BLE001
                        continue
        return False

    def _refresh_browser_preview(self) -> None:
        session = self._browser_preview_session
        if session is None:
            return
        if session.tab_index != self._active_tab_index:
            return
        self.preview_in_browser()

    def _get_assistant(self) -> Assistant:
        assistant = getattr(self, "_assistant", None)
        if assistant is None:
            assistant = Assistant()
            self._assistant = assistant
            self._apply_style_to_assistant()
        return assistant

    def _apply_style_to_assistant(self) -> None:
        from quill.core.ai.style import load_style, style_preamble
        from quill.core.ai.writing_instructions import (
            instructions_preamble,
            load_instructions,
        )

        assistant = getattr(self, "_assistant", None)
        if assistant is not None:
            assistant.set_style_preamble(style_preamble(load_style()))
            # AI-21: pin the user's durable, editable writing instructions
            # (global + this document's sidecar), re-read live each time.
            document_path = getattr(self.document, "path", None)
            assistant.set_instructions_preamble(
                instructions_preamble(load_instructions(document_path))
            )

    def open_writing_instructions(self) -> None:
        """Open the user's durable writing-instructions file in the editor (AI-21).

        Creates the global instructions file with a friendly template on first
        use, then opens it as a normal document tab so the user edits it with
        QUILL's own accessible editor. The assistant re-reads it live on the
        next generation.
        """
        from quill.core.ai.writing_instructions import (
            global_instructions_path,
            save_global_instructions,
        )

        path = global_instructions_path()
        if not path.exists():
            save_global_instructions(
                "# Writing instructions\n\n"
                "Rules the assistant always follows for your writing. Edit freely.\n\n"
                "- Audience: \n"
                "- Tone: \n"
                "- Words to avoid: \n"
            )
        self.open_file(path)
        self._set_status("Opened writing instructions. The assistant honors these rules.")

    def open_train_writing_style(self) -> None:
        from quill.core.ai.model_manager import load_ai_enabled

        if not load_ai_enabled():
            self._set_status(
                "AI is turned off. Enable 'Use Artificial Intelligence' in Tools > AI Assistant."
            )
            return
        TrainStyleDialog(
            self.frame,
            self._get_assistant(),
            get_document=lambda: self.editor.GetValue(),
            announce=self._set_status,
        ).show()
        # Apply the (possibly updated) style to the assistant immediately.
        self._apply_style_to_assistant()

    def _on_toggle_ai_enabled(self, event: object) -> None:
        from quill.core.ai.model_manager import save_ai_enabled

        enabled = bool(event.IsChecked())
        save_ai_enabled(enabled)
        self._apply_ai_menu_enabled()
        self._refresh_ai_status()
        self._set_status("AI enabled" if enabled else "AI disabled")

    def _refresh_ai_status(self) -> None:
        """Check the active AI backend and update the AI Status badge (off-thread)."""
        from quill.core.ai.model_manager import load_ai_enabled

        if not load_ai_enabled():
            self._set_ai_menu_status_badge(None, "AI is turned off.", badge="Off")
            return
        try:
            from quill.core.assistant_ai import assistant_secret_unlock_failed

            if assistant_secret_unlock_failed():
                self._set_ai_menu_status_badge(
                    False,
                    "Your saved API key could not be unlocked on this device. "
                    "Open AI Connection and enter the key again.",
                    badge="Needs key",
                )
                return
        except Exception:  # noqa: BLE001 - never block status on this probe
            pass
        self._set_ai_menu_status_badge(None, "Checking the AI backend...", badge="Checking...")

        def worker() -> None:
            try:
                from quill.core.ai.assistant import make_default_backend

                ok, reason = make_default_backend().is_available()
            except Exception as exc:  # noqa: BLE001
                ok, reason = False, str(exc)
            from quill.core.ai.availability import describe_ai_availability

            status = describe_ai_availability(enabled=True, available=bool(ok), reason=reason)
            badge = "Needs key" if status.needs_key else None
            self._wx.CallAfter(self._set_ai_menu_status_badge, bool(ok), status.message, badge)

        threading.Thread(  # GATE-40-OK: AI menu status probe.
            target=worker, daemon=True
        ).start()

    def _apply_ai_menu_enabled(self) -> None:
        """Enable/disable the AI menu items behind the 'Use Artificial Intelligence'
        toggle. The toggle and the status lines stay available so AI can be turned
        back on."""
        from quill.core.ai.model_manager import load_ai_enabled

        if not self._menu_updates_allowed():
            self._request_menu_refresh()
            return
        bar = self.frame.GetMenuBar()
        if bar is None:
            return
        enabled = load_ai_enabled()
        ai_item_ids = (
            self._id_ai_hub,
            self._id_ask_quill_chat,
            self._id_ai_model,
            self._id_ai_session_browser,
            self._id_ai_assistant,
            self._id_ai_prompt_studio,
            self._id_ai_agent_center,
            self._id_ai_rewrite_selection,
            self._id_ai_summarize_selection,
            self._id_ai_continue_writing,
            self._id_ai_fix_grammar,
            self._id_train_style,
        )
        for item_id in ai_item_ids:
            if bar.FindItemById(item_id) is not None:
                bar.Enable(item_id, enabled)

        # "Forget API Key" is gated on whether a key is actually stored, not on
        # the AI on/off toggle (#128): a user must be able to forget a key even
        # with AI disabled, but the item is meaningless when nothing is stored.
        if bar.FindItemById(self._id_ai_forget_key) is not None:
            bar.Enable(self._id_ai_forget_key, self._assistant_api_key_present())

    def _assistant_api_key_present(self) -> bool:
        """True when an assistant API key is stored in either persistence layer."""
        from quill.core.assistant_ai import load_assistant_api_key

        try:
            return bool(load_assistant_api_key())
        except Exception:  # noqa: BLE001 - storage probing must never crash the menu
            return False

    def open_ask_quill_chat(self) -> None:
        from quill.core.ai.model_manager import load_ai_enabled

        if not load_ai_enabled():
            from quill.core.ai.availability import AI_DISABLED_MESSAGE

            self._set_status(AI_DISABLED_MESSAGE)
            return

        self._apply_style_to_assistant()
        tool_catalog = allowed_tools(self.commands, getattr(self, "features", None))
        dialog = AskQuillChatDialog(
            self.frame,
            self._get_assistant(),
            get_document=lambda: self.editor.GetValue(),
            get_selection=lambda: self.editor.GetStringSelection(),
            insert_text=self._ai_insert_text,
            replace_selection=self._ai_replace_selection,
            run_command=self._ai_run_command,
            tool_catalog=tool_catalog,
            announce=self._set_status,
            review_changes=self.open_ai_diff_review,
        )
        dialog.show()

    def open_ask_ai(self) -> None:
        from quill.ui.ai_chat_dialog import AskAIDialog

        dlg = AskAIDialog(self.frame, self.settings)
        dlg.show()
        dlg.close()

    def open_prompt_library(self) -> None:
        from quill.ui.prompt_library_dialog import PromptLibraryDialog

        lib = self._get_prompt_library()
        dlg = PromptLibraryDialog(
            self.frame,
            lib,
            self.settings,
            selection=str(self.editor.GetStringSelection()),
            document=str(self.editor.GetValue()),
            title=self._current_document_title(),
        )
        self._show_modal_dialog(dlg.dialog, "Prompt Library")
        dlg.close()

    def open_skill_library(self) -> None:
        from quill.ui.skill_library_dialog import SkillLibraryDialog

        dlg = SkillLibraryDialog(
            self.frame,
            self._get_skill_files(),
            self.settings,
            selection=str(self.editor.GetStringSelection()),
            document=str(self.editor.GetValue()),
            title_text=self._current_document_title(),
            on_insert=self._ai_insert_text,
        )
        dlg.dialog.CenterOnParent()
        self._show_modal_dialog(dlg.dialog, "Skill Library")
        dlg.close()

    def _get_skill_files(self) -> list:

        paths: list[Path] = []
        for item in self._installed_quillins():
            for sqp in sorted(item.directory.glob("*.sqp")):
                paths.append(sqp)
        return paths

    def check_grammar_with_ai(self) -> None:
        import threading

        lib = self._get_prompt_library()
        grammar = lib.find_by_id("builtin-check-grammar")
        if grammar is None:
            self._announce("Grammar prompt not found.")
            return
        selection = str(self.editor.GetStringSelection()) or str(self.editor.GetValue())
        if not selection.strip():
            self._announce("No text to check grammar for.")
            return
        provider_id = self.settings.ai_chat_default_provider
        model_id = self.settings.ai_prompt_default_model or self.settings.ai_chat_default_model
        if not model_id:
            self._set_status("No AI model configured. Set one in Preferences > AI.")
            return
        prompt_text = grammar.text.replace("{selection}", selection)
        self._announce(f"Checking grammar with {model_id}...")

        def run() -> None:
            import wx as _wx

            try:
                from quill.core.ai_chat import send_prompt
                from quill.platform.windows.credential_manager import get_credential

                api_key = get_credential(f"quill-{provider_id}-api-key") or ""
                result = send_prompt(provider_id, model_id, prompt_text, api_key=api_key)
                _wx.CallAfter(self._show_grammar_result, result, model_id, provider_id)
            except Exception as exc:  # noqa: BLE001
                _wx.CallAfter(self._announce, f"Grammar check failed: {exc}")

        threading.Thread(  # GATE-40-OK: one-shot grammar-check send.
            target=run, daemon=True
        ).start()

    def _show_grammar_result(self, result: str, model_id: str, provider_id: str) -> None:
        from quill.ui.ai_chat_dialog import AIResponseDialog

        dlg = AIResponseDialog(self.frame, result, model_id, provider_id)
        dlg.show()
        dlg.close()

    def _get_prompt_library(self) -> object:
        if not hasattr(self, "_prompt_library_cache"):
            from quill.core.paths import app_data_dir
            from quill.core.prompt_library import PromptLibrary

            lib = PromptLibrary(app_data_dir() / "prompts.json")
            for item in self._installed_quillins():
                lib.load_quillin_prompts(item.directory / "prompts.json")
            self._prompt_library_cache = lib
        return self._prompt_library_cache

    def _ai_insert_text(self, text: str) -> None:
        self.editor.WriteText(text)

    def open_ai_diff_review(
        self,
        original: str,
        revised: str,
        on_apply: Callable[[str], None],
        *,
        title: str = "Review AI Changes",
    ) -> None:
        """AI-7: present a navigable added/removed/changed diff and apply the
        accepted hunks as a single undo step via ``on_apply``."""
        from quill.ui.assistant_tools import DiffReviewDialog

        dialog = DiffReviewDialog(
            self.frame,
            title=title,
            original_text=original,
            revised_text=revised,
            on_apply=on_apply,
            announce=self._set_status,
        )
        dialog.show_modal()

    def _ai_replace_selection(self, text: str) -> None:
        start, end = self.editor.GetSelection()
        if start != end:
            self.editor.Replace(start, end, text)
            self.editor.SetInsertionPoint(start + len(text))
        else:
            self.editor.WriteText(text)

    def _ai_run_command(self, command_id: str) -> None:
        self.commands.run(command_id)

    def open_ai_model_settings(self) -> None:
        # Combined AI Model & Connection — the model dialog hosts a button to the
        # connection settings, so there's one entry point for all AI setup.
        AIModelDialog(
            self.frame,
            announce=self._set_status,
            open_connection=self.open_ai_preferences,
        ).show()

    def _forget_assistant_api_key(self) -> None:
        """Forget the stored assistant API key (SEC-7).

        Clears the key from both persistence layers (Windows Credential Manager
        and the DPAPI-protected fallback file) after an explicit confirmation,
        then announces the outcome.
        """
        from quill.core.assistant_ai import clear_assistant_api_key

        wx = self._wx
        result = self._show_message_box(
            "Forget the stored AI provider API key? This removes it from the "
            "Windows Credential Manager and the encrypted fallback file. You "
            "will need to re-enter the key to use cloud providers again.",
            "Forget API Key",
            wx.YES_NO | wx.ICON_WARNING,
        )
        if result != wx.YES:
            self._set_status("Forget API key cancelled. The stored key was kept.")
            return
        had_key = clear_assistant_api_key()
        if had_key:
            self._set_status("AI provider API key forgotten. Re-enter it to use cloud providers.")
        else:
            self._set_status("No stored AI provider API key was found.")
        # Reflect the now-absent key in the menu so "Forget API Key" greys out (#128).
        self._request_menu_refresh()

    def open_ai_session_browser(self) -> None:
        # Browse the branch tree of the most recent writing session and jump
        # between branches or compare them — fully keyboard- and screen-reader
        # driven via the wx-free session-tree engine.
        from quill.core.ai.sessions import most_recent_session

        session = most_recent_session()
        if session is None:
            self._set_status("No saved writing sessions yet. Start an AI session first.")
            return
        SessionBrowserDialog(
            self.frame,
            session,
            announce=self._set_status,
        ).show()

    def open_ai_hub(self) -> None:
        # The AI Hub is the single place to configure every provider (key, model,
        # Test Chat, per-provider Forget) plus on-device model settings. It
        # absorbed the former "AI Model and Connection" and "AI Connection"
        # entries (AICONS-1).
        dialog = AssistantConnectionDialog(
            self.frame,
            open_model_settings=self.open_ai_model_settings,
        )
        if dialog.show_modal():
            self._set_ai_menu_status_badge(
                dialog.last_verification_ok,
                dialog.last_verification_message,
            )
            detail = self._compact_ai_status_detail(
                self._plain_language_ai_status_detail(dialog.last_verification_message)
            )
            state = "Ready" if dialog.last_verification_ok else "Needs attention"
            self._set_status(f"Updated AI Hub settings. {state}. {detail}")
            self._request_menu_refresh()
        else:
            self._set_status("AI Hub closed")

    def open_writing_assistant(self, initial_prompt: str = "") -> None:
        # H-SAFE-1: refuse to even open the AI dialog in safe mode. The
        # assistant_enabled flag is forced off in safe mode (line 870)
        # but a user clicking the menu item or a future hot key could
        # still reach this surface; the dialog is the load-bearing
        # gate that the network calls are now also protected by.
        if self._safe_mode:
            self._set_status("Writing assistant is unavailable in safe mode")
            return
        dialog = WritingAssistantDialog(
            self.frame,
            self.commands,
            getattr(self, "features", None),
            open_python_tool=self.run_python_tool,
            selection_text=self._selected_text(),
            document_text=self.editor.GetValue(),
            initial_prompt=initial_prompt,
            assistant_enabled=getattr(self.settings, "assistant_enabled", False),
            prompt_style=getattr(self.settings, "assistant_prompt_style", "balanced"),
        )
        dialog.show_modal()

    def open_prompt_studio(self) -> None:
        dialog = PromptStudioDialog(
            self.frame,
            selection_text=self._selected_text(),
            document_text=self.editor.GetValue(),
            on_use_prompt=self.open_writing_assistant,
            announce=self._set_status,
        )
        dialog.show_modal()

    def open_agent_center(self) -> None:
        dialog = AgentCenterDialog(
            self.frame,
            selection_text=self._selected_text(),
            document_text=self.editor.GetValue(),
            on_use_prompt=self.open_writing_assistant,
            announce=self._set_status,
        )
        dialog.show_modal()

    def run_python_tool(self) -> None:
        outline = [
            {"level": entry.level, "title": entry.title, "position": entry.position}
            for entry in self._outline_entries()
        ]
        dialog = RunPythonDialog(
            self.frame,
            document_text=self.editor.GetValue(),
            selection_text=self._selected_text(),
            outline=outline,
            apply_callback=self._apply_python_result,
        )
        dialog.show_modal()

    def _selected_text(self) -> str:
        start, end = self.editor.GetSelection()
        if start == end:
            return ""
        return self.editor.GetValue()[start:end]

    def _apply_python_result(self, updated_text: str) -> None:
        start, end = self.editor.GetSelection()
        current = self.editor.GetValue()
        if start != end:
            new_text = current[:start] + updated_text + current[end:]
            replace_start = start
        else:
            new_text = updated_text
            replace_start = 0
        self._replace_document_text(new_text)
        self.document.set_text(new_text)
        self._record_persistent_undo_state(new_text)
        if start != end:
            self.editor.SetSelection(replace_start, replace_start + len(updated_text))
            self.editor.SetInsertionPoint(replace_start + len(updated_text))
        else:
            self.editor.SetSelection(0, len(updated_text))
        self._maybe_autosave()
        self._refresh_title()
        self._refresh_contextual_menu_items()
        self._set_status("Applied Python result")

    def format_bold(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Bold is unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Bold is only available in Markdown or HTML documents")
            return
        selected_text = self.editor.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_insertion("Bold", selected_text)
        else:
            result = build_html_insertion("strong", selected_text, {})
        self._apply_insertion_result(result)
        self._set_status(f"Applied bold ({surface})")

    def format_upper_case(self) -> None:
        self._transform_selection_or_document(to_upper, "Upper case")

    def format_lower_case(self) -> None:
        self._transform_selection_or_document(to_lower, "Lower case")

    def format_title_case(self) -> None:
        self._transform_selection_or_document(to_title, "Title case")

    def format_sentence_case(self) -> None:
        self._transform_selection_or_document(to_sentence_case, "Sentence case")

    def format_toggle_case(self) -> None:
        self._transform_selection_or_document(to_toggle_case, "Toggle case")

    def format_toggle_line_comment(self) -> None:
        self._apply_selection_operation(
            lambda text, start, end: toggle_line_comment(text, start, end, self.document.path),
            "Toggled line comment",
        )

    def format_toggle_block_comment(self) -> None:
        self._apply_selection_operation(
            lambda text, start, end: toggle_block_comment(text, start, end, self.document.path),
            "Toggled block comment",
        )

    def _indent_width(self) -> int:
        return max(1, int(getattr(self.settings, "indent_size", 4)))

    def _indent_unit(self) -> str:
        if bool(getattr(self.settings, "indent_with_tabs", False)):
            return "\t"
        return " " * self._indent_width()

    def format_indent(self) -> None:
        self._apply_selection_operation(
            lambda text, start, end: indent_lines(
                text,
                start,
                end,
                indent_unit=self._indent_unit(),
            ),
            "Indented lines",
        )

    def format_outdent(self) -> None:
        self._apply_selection_operation(
            lambda text, start, end: outdent_lines(
                text,
                start,
                end,
                indent_unit=self._indent_unit(),
            ),
            "Outdented lines",
        )

    def format_italic(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Italic is unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Italic is only available in Markdown or HTML documents")
            return
        selected_text = self.editor.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_insertion("Italic", selected_text)
        else:
            result = build_html_insertion("em", selected_text, {})
        self._apply_insertion_result(result)
        self._set_status(f"Applied italic ({surface})")

    def format_heading(self, level: int) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Heading tools are unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Headings are only available in Markdown or HTML documents")
            return
        selected_text = self.editor.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_insertion(f"Heading {level}", selected_text)
        else:
            result = build_html_insertion(f"h{level}", selected_text, {})
        self._apply_insertion_result(result)
        self._set_status(f"Inserted heading {level} ({surface})")

    def decrease_heading_level(self) -> None:
        self._adjust_heading_level(-1)

    def increase_heading_level(self) -> None:
        self._adjust_heading_level(1)

    def style_headings(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Heading tools are unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Headings are only available in Markdown or HTML documents")
            return
        levels = self._prompt_heading_style_levels(surface)
        if levels is None:
            self._set_status("Heading styling cancelled")
            return
        style = self._prompt_heading_style()
        if style is None:
            self._set_status("Heading styling cancelled")
            return
        text = self.editor.GetValue()
        updated, changed = apply_heading_style(
            text, markup_kind=surface, style=style, levels=levels
        )
        if changed == 0:
            self._set_status("No headings matched the selected level")
            return
        self._replace_document_text(updated)
        self.document.set_text(updated)
        self._set_status(f"Styled {changed} heading{'s' if changed != 1 else ''}")

    def _prompt_heading_style_levels(self, surface: str) -> set[int] | None:
        options = ["All heading levels", "Current heading level"]
        choice = self._wx.GetSingleChoice(
            "Choose which headings to style.",
            "Style Headings",
            options,
            self.frame,
        )
        if not choice:
            return None
        if choice == "All heading levels":
            return set(range(1, 7))
        level = self._current_heading_level(surface)
        if level is None:
            self._set_status("Place the cursor on a heading line to style current level")
            return None
        return {level}

    def _current_heading_level(self, surface: str) -> int | None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        start, end = line_span(text, cursor)
        line_text = text[start:end].strip()
        if surface == "markdown":
            match = re.match(r"^(#{1,6})\s+", line_text)
            if match is None:
                return None
            return len(match.group(1))
        match = re.match(r"^<h([1-6])(?:\s[^>]*)?>", line_text, flags=re.IGNORECASE)
        if match is None:
            return None
        return int(match.group(1))

    def _prompt_heading_style(self) -> HeadingStyle | None:
        font_family = self._wx.GetTextFromUser(
            "Font family (leave blank to keep existing):",
            "Style Headings",
            parent=self.frame,
        )
        if font_family is None:
            return None
        size_text = self._wx.GetTextFromUser(
            "Font size in points (leave blank to keep existing):",
            "Style Headings",
            parent=self.frame,
        )
        if size_text is None:
            return None
        size_value: int | None = None
        cleaned_size = size_text.strip()
        if cleaned_size:
            try:
                parsed_size = int(cleaned_size)
            except ValueError:
                self._set_status("Heading style requires a whole-number font size")
                return None
            if parsed_size <= 0:
                self._set_status("Heading style requires a positive font size")
                return None
            size_value = parsed_size
        alignment_options = ["Keep existing", "Left", "Center", "Right", "Justify"]
        alignment_choice = self._wx.GetSingleChoice(
            "Text alignment:",
            "Style Headings",
            alignment_options,
            self.frame,
        )
        if not alignment_choice:
            return None
        align_value = None if alignment_choice == "Keep existing" else alignment_choice.lower()
        style = HeadingStyle(
            font_family=font_family.strip() or None,
            font_size_pt=size_value,
            text_align=align_value,
        )
        if not style.declarations():
            self._set_status("Specify at least one heading style option")
            return None
        return style

    def _adjust_heading_level(self, delta: int) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Heading tools are unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Headings are only available in Markdown or HTML documents")
            return
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        start, end = line_span(text, cursor)
        line_text = text[start:end]
        replacement: str | None = None
        old_level: int | None = None
        if surface == "markdown":
            match = re.match(r"^(#{1,6})\s+(.*)$", line_text)
            if match is not None:
                old_level = len(match.group(1))
                new_level = min(6, max(1, old_level + delta))
                if new_level == old_level:
                    direction = "minimum" if delta < 0 else "maximum"
                    self._set_status(f"Heading already at {direction} level")
                    return
                replacement = f"{'#' * new_level} {match.group(2)}"
        else:
            match = re.match(
                r"^\s*<h([1-6])([^>]*)>(.*)</h\1>\s*$",
                line_text,
                flags=re.IGNORECASE,
            )
            if match is not None:
                old_level = int(match.group(1))
                new_level = min(6, max(1, old_level + delta))
                if new_level == old_level:
                    direction = "minimum" if delta < 0 else "maximum"
                    self._set_status(f"Heading already at {direction} level")
                    return
                attributes = match.group(2)
                content = match.group(3)
                replacement = f"<h{new_level}{attributes}>{content}</h{new_level}>"
        if replacement is None:
            self._set_status("Place cursor on a heading line to adjust its level")
            return
        self.editor.SetSelection(start, end)
        self.editor.Replace(start, end, replacement)
        self.document.set_text(self.editor.GetValue())
        self._set_status("Adjusted heading level")

    def format_insert_bullet_list(self) -> None:
        self._insert_structure("Bullet List", "Inserted bullet list")

    def format_insert_numbered_list(self) -> None:
        self._insert_structure("Numbered List", "Inserted numbered list")

    def format_insert_task_list(self) -> None:
        self._insert_structure("Task List", "Inserted task list")

    def open_list_manager(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("List Manager is unavailable in this profile")
            return
        if infer_markup_kind(self.document.path) not in {"markdown", "plain"}:
            self._set_status("List Manager is only available in Markdown documents")
            return
        state = self._extract_list_manager_state()
        if state is None or not state.items:
            self._set_status("Place the cursor inside a Markdown list to open List Manager")
            return
        updated_text = self._show_list_manager_dialog(state)
        if updated_text is None:
            self._set_status("List Manager cancelled")
            return
        if updated_text == self.editor.GetValue():
            self._set_status("List Manager closed without changes")
            return
        self._replace_document_text(updated_text)
        self.document.set_text(updated_text)
        self._set_status("Applied list manager changes")

    def _extract_list_manager_state(self) -> _ListManagerState | None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        current_start, current_end = line_span(text, cursor)
        current_line = text[current_start:current_end]
        if self._parse_list_manager_line(current_line) is None:
            return None

        starts: list[int] = [0]
        for index, character in enumerate(text):
            if character == "\n":
                starts.append(index + 1)

        current_index = 0
        for index, start in enumerate(starts):
            if start <= current_start:
                current_index = index
            else:
                break

        def line_text(line_index: int) -> str:
            line_start = starts[line_index]
            line_end = starts[line_index + 1] if line_index + 1 < len(starts) else len(text)
            return text[line_start:line_end]

        top = current_index
        while top > 0 and self._parse_list_manager_line(line_text(top - 1)) is not None:
            top -= 1
        bottom = current_index
        while (
            bottom + 1 < len(starts)
            and self._parse_list_manager_line(line_text(bottom + 1)) is not None
        ):
            bottom += 1

        block_start = starts[top]
        block_end = starts[bottom + 1] if bottom + 1 < len(starts) else len(text)
        block_lines = [line_text(i) for i in range(top, bottom + 1)]
        parsed: list[tuple[str, str, str, bool, str]] = []
        indent_widths: list[int] = []
        for raw_line in block_lines:
            item = self._parse_list_manager_line(raw_line)
            if item is None:
                return None
            parsed.append(item)
            indent, _kind, _bullet, _checked, _body = item
            indent_widths.append(self._indent_measure(indent))
        if not parsed:
            return None

        base_indent_width = min(indent_widths)
        step_width = max(1, self._indent_width())
        items: list[_ListManagerItem] = []
        for indent, kind, bullet, checked, body in parsed:
            level = max(0, (self._indent_measure(indent) - base_indent_width) // step_width)
            items.append(
                _ListManagerItem(
                    kind=kind,
                    text=body,
                    level=level,
                    bullet=bullet or "-",
                    checked=checked,
                )
            )
        return _ListManagerState(
            start=block_start,
            end=block_end,
            trailing_newline=text[block_end - 1 : block_end] == "\n",
            base_indent=" " * base_indent_width,
            items=items,
        )

    def _parse_list_manager_line(self, line: str) -> tuple[str, str, str, bool, str] | None:
        text = line.rstrip("\r\n")
        match = re.match(
            r"^(?P<indent>[ \t]*)(?:(?P<number>\d+)(?P<number_sep>[.)])|(?P<bullet>[-+*]))"
            r"(?P<spacing>[ \t]+)(?:(?P<task>\[[ xX]\])(?P<task_spacing>[ \t]+))?"
            r"(?P<body>.*)$",
            text,
        )
        if match is None:
            return None
        indent = match.group("indent") or ""
        bullet = match.group("bullet") or "-"
        task = match.group("task")
        body = match.group("body") or ""
        if task is not None:
            return indent, "task", bullet, "x" in task.lower(), body
        if match.group("number") is not None:
            return indent, "ordered", ".", False, body
        return indent, "bullet", bullet, False, body

    def _indent_measure(self, indent: str) -> int:
        return len(indent.expandtabs(self._indent_width()))

    def _render_list_manager_block(self, state: _ListManagerState) -> str:
        lines: list[str] = []
        ordered_counters: dict[int, int] = {}
        for item in state.items:
            level = max(0, item.level)
            indent = f"{state.base_indent}{self._indent_unit() * level}"
            for key in list(ordered_counters):
                if key > level:
                    ordered_counters.pop(key, None)
            if item.kind == "ordered":
                ordered_counters[level] = ordered_counters.get(level, 0) + 1
                marker = f"{ordered_counters[level]}. "
            elif item.kind == "task":
                marker = f"{item.bullet} [{'x' if item.checked else ' '}] "
                ordered_counters[level] = 0
            else:
                marker = f"{item.bullet} "
                ordered_counters[level] = 0
            lines.append(f"{indent}{marker}{item.text}".rstrip())
        block_text = "\n".join(lines)
        if state.trailing_newline:
            block_text += "\n"
        return block_text

    def _show_list_manager_dialog(self, state: _ListManagerState) -> str | None:
        wx = self._wx
        working_items = [
            _ListManagerItem(
                kind=item.kind,
                text=item.text,
                level=item.level,
                bullet=item.bullet,
                checked=item.checked,
            )
            for item in state.items
        ]
        selected_index: int | None = 0 if working_items else None
        dialog = wx.Dialog(self.frame, title="List Manager", size=(1020, 700))
        splitter = wx.SplitterWindow(dialog, style=wx.SP_LIVE_UPDATE)
        tree = wx.TreeCtrl(
            splitter,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HAS_VARIABLE_ROW_HEIGHT,
        )
        preview = wx.TextCtrl(splitter, style=wx.TE_MULTILINE | wx.TE_READONLY)
        splitter.SplitVertically(tree, preview, 420)
        splitter.SetMinimumPaneSize(260)
        item_indexes: dict[object, int] = {}
        root = tree.AddRoot("List Items")

        def list_preview(index: int | None) -> str:
            if index is None or index < 0 or index >= len(working_items):
                return "No list item selected."
            item = working_items[index]
            kind_label = {"bullet": "Bullet", "ordered": "Numbered", "task": "Task"}[item.kind]
            status = f"{kind_label} item at level {item.level + 1}"
            if item.kind == "task":
                status = f"{status} ({'checked' if item.checked else 'unchecked'})"
            return f"{status}\n\n{item.text or '(empty item)'}"

        def build_tree() -> None:
            nonlocal root, selected_index
            tree.DeleteAllItems()
            root = tree.AddRoot("List Items")
            item_indexes.clear()
            node_stack: list[tuple[int, object]] = []
            first_item = None
            selected_item = None
            for index, item in enumerate(working_items):
                label_prefix = (
                    "[ ]"
                    if item.kind == "task" and not item.checked
                    else "[x]"
                    if item.kind == "task"
                    else "1."
                    if item.kind == "ordered"
                    else item.bullet
                )
                label = f"{label_prefix} {item.text or '(empty item)'}"
                while node_stack and node_stack[-1][0] >= item.level:
                    node_stack.pop()
                parent = root if not node_stack else node_stack[-1][1]
                node = tree.AppendItem(parent, label)
                item_indexes[node] = index
                if first_item is None:
                    first_item = node
                if selected_index == index:
                    selected_item = node
                node_stack.append((item.level, node))
            tree.Expand(root)
            target = selected_item if selected_item is not None else first_item
            if target is not None:
                tree.SelectItem(target)
                selected_index = item_indexes.get(target)
            else:
                selected_index = None
            preview.ChangeValue(list_preview(selected_index))

        def subtree_bounds(index: int) -> tuple[int, int]:
            level = working_items[index].level
            end = index + 1
            while end < len(working_items) and working_items[end].level > level:
                end += 1
            return index, end

        def update_after_change(message: str, preferred_index: int | None) -> None:
            nonlocal selected_index
            if not working_items:
                selected_index = None
            elif preferred_index is None:
                selected_index = min(len(working_items) - 1, selected_index or 0)
            else:
                selected_index = max(0, min(preferred_index, len(working_items) - 1))
            build_tree()
            self._set_status(message)

        def require_selection() -> int | None:
            if selected_index is None or selected_index < 0 or selected_index >= len(working_items):
                return None
            return selected_index

        def move_up() -> None:
            index = require_selection()
            if index is None:
                return
            start, end = subtree_bounds(index)
            target = start - 1
            while target >= 0 and working_items[target].level != working_items[index].level:
                target -= 1
            if target < 0:
                return
            block = working_items[start:end]
            del working_items[start:end]
            insert_at = target
            working_items[insert_at:insert_at] = block
            update_after_change("Moved list item up", insert_at)

        def move_down() -> None:
            index = require_selection()
            if index is None:
                return
            start, end = subtree_bounds(index)
            target = end
            while (
                target < len(working_items)
                and working_items[target].level != working_items[index].level
            ):
                target += 1
            if target >= len(working_items):
                return
            next_start, next_end = subtree_bounds(target)
            block = working_items[start:end]
            del working_items[start:end]
            insert_at = next_end - len(block)
            working_items[insert_at:insert_at] = block
            update_after_change("Moved list item down", insert_at)

        def promote() -> None:
            index = require_selection()
            if index is None or working_items[index].level == 0:
                return
            start, end = subtree_bounds(index)
            for cursor in range(start, end):
                working_items[cursor].level = max(0, working_items[cursor].level - 1)
            update_after_change("Promoted list item", start)

        def demote() -> None:
            index = require_selection()
            if index is None or index == 0:
                return
            previous_level = working_items[index - 1].level
            if previous_level < working_items[index].level:
                return
            start, end = subtree_bounds(index)
            for cursor in range(start, end):
                working_items[cursor].level += 1
            update_after_change("Nested list item", start)

        def edit_item() -> None:
            index = require_selection()
            if index is None:
                return
            current = working_items[index]
            with wx.TextEntryDialog(
                dialog,
                "Edit list item text:",
                "Edit List Item",
                value=current.text,
            ) as entry:
                if self._show_modal_dialog(entry, "Edit List Item") != wx.ID_OK:
                    return
                current.text = entry.GetValue().strip()
            update_after_change("Updated list item", index)

        def add_item(as_child: bool) -> None:
            index = require_selection()
            if index is None:
                return
            current = working_items[index]
            with wx.TextEntryDialog(
                dialog,
                "Enter text for the new list item:",
                "Add List Item",
                value="",
            ) as entry:
                if self._show_modal_dialog(entry, "Add List Item") != wx.ID_OK:
                    return
                text_value = entry.GetValue().strip()
            level = current.level + 1 if as_child else current.level
            insert_at = subtree_bounds(index)[1] if as_child else subtree_bounds(index)[1]
            working_items.insert(
                insert_at,
                _ListManagerItem(
                    kind=current.kind,
                    text=text_value,
                    level=level,
                    bullet=current.bullet,
                    checked=False,
                ),
            )
            update_after_change("Added list item", insert_at)

        def delete_item() -> None:
            index = require_selection()
            if index is None:
                return
            start, end = subtree_bounds(index)
            del working_items[start:end]
            update_after_change("Deleted list item", start - 1 if start > 0 else 0)

        def on_select(event: object) -> None:
            nonlocal selected_index
            selected_index = item_indexes.get(event.GetItem())
            preview.ChangeValue(list_preview(selected_index))
            event.Skip()

        button_column = wx.BoxSizer(wx.VERTICAL)
        move_up_button = wx.Button(dialog, label="Move Up")
        move_down_button = wx.Button(dialog, label="Move Down")
        promote_button = wx.Button(dialog, label="Promote")
        demote_button = wx.Button(dialog, label="Demote")
        edit_button = wx.Button(dialog, label="Edit...")
        add_child_button = wx.Button(dialog, label="Add Child...")
        add_sibling_button = wx.Button(dialog, label="Add Sibling...")
        delete_button = wx.Button(dialog, label="Delete")
        apply_button = wx.Button(dialog, id=wx.ID_OK, label="Apply Changes")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Close")

        for button in (
            move_up_button,
            move_down_button,
            promote_button,
            demote_button,
            edit_button,
            add_child_button,
            add_sibling_button,
            delete_button,
        ):
            button_column.Add(button, 0, wx.EXPAND | wx.BOTTOM, 6)
        button_column.AddStretchSpacer(1)
        button_column.Add(apply_button, 0, wx.EXPAND | wx.BOTTOM, 6)
        button_column.Add(cancel_button, 0, wx.EXPAND)

        controls = wx.BoxSizer(wx.VERTICAL)
        controls.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Manage the current Markdown list as a tree. "
                    "Use Move/Promote/Demote to restructure without editing markers by hand."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        controls.Add(splitter, 1, wx.ALL | wx.EXPAND, 8)
        content = wx.BoxSizer(wx.HORIZONTAL)
        content.Add(controls, 1, wx.EXPAND)
        content.Add(button_column, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(content)

        tree.Bind(wx.EVT_TREE_SEL_CHANGED, on_select)
        move_up_button.Bind(wx.EVT_BUTTON, lambda _e: move_up())
        move_down_button.Bind(wx.EVT_BUTTON, lambda _e: move_down())
        promote_button.Bind(wx.EVT_BUTTON, lambda _e: promote())
        demote_button.Bind(wx.EVT_BUTTON, lambda _e: demote())
        edit_button.Bind(wx.EVT_BUTTON, lambda _e: edit_item())
        add_child_button.Bind(wx.EVT_BUTTON, lambda _e: add_item(as_child=True))
        add_sibling_button.Bind(wx.EVT_BUTTON, lambda _e: add_item(as_child=False))
        delete_button.Bind(wx.EVT_BUTTON, lambda _e: delete_item())
        apply_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))

        build_tree()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        if self._show_modal_dialog(dialog, "List Manager") != wx.ID_OK:
            return None

        block = self._render_list_manager_block(
            _ListManagerState(
                start=state.start,
                end=state.end,
                trailing_newline=state.trailing_newline,
                base_indent=state.base_indent,
                items=working_items,
            )
        )
        text = self.editor.GetValue()
        return text[: state.start] + block + text[state.end :]

    def format_insert_code_block(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Code Block is unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Code Block is only available in Markdown or HTML documents")
            return

        language_hint = self._prompt_code_language()
        if language_hint is None:
            self._set_status("Insert code block cancelled")
            return

        selected_text = self.editor.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_code_block(selected_text, language_hint=language_hint)
        else:
            result = build_html_code_block(selected_text, language_hint=language_hint)
        self._apply_insertion_result(result)
        language_display = language_hint.strip() or "plain"
        self._set_status(f"Inserted code block ({surface}, {language_display})")

    def format_insert_footnote(self) -> None:
        self._insert_structure("Footnote", "Inserted footnote")

    def format_insert_table(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Table is unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Table is only available in Markdown or HTML documents")
            return

        table_shape = self._prompt_table_shape()
        if table_shape is None:
            self._set_status("Insert table cancelled")
            return
        rows, columns, include_header = table_shape
        if surface == "markdown":
            result = build_markdown_table(rows, columns, include_header=include_header)
        else:
            result = build_html_table(rows, columns, include_header=include_header)
        self._apply_insertion_result(result)
        self._set_status(f"Inserted {rows}x{columns} table ({surface})")

    def _insert_structure(self, kind: str, status: str) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status(f"{kind} is unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status(
                f"{kind} is only available in Markdown or HTML documents",
            )
            return
        selected_text = self.editor.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_insertion(kind, selected_text)
        else:
            result = self._build_html_structure(kind, selected_text)
        self._apply_insertion_result(result)
        self._set_status(f"{status} ({surface})")

    def _build_html_structure(self, kind: str, selected_text: str) -> InsertionResult:
        lines = [line.strip() for line in selected_text.splitlines() if line.strip()]
        if kind == "Bullet List":
            items = lines or ["item"]
            snippet = "<ul>\n" + "\n".join(f"  <li>{item}</li>" for item in items) + "\n</ul>"
            return InsertionResult(snippet, len(snippet))
        if kind == "Numbered List":
            items = lines or ["item"]
            snippet = "<ol>\n" + "\n".join(f"  <li>{item}</li>" for item in items) + "\n</ol>"
            return InsertionResult(snippet, len(snippet))
        if kind == "Task List":
            items = lines or ["task"]
            snippet = (
                "<ul>\n"
                + "\n".join(f'  <li><input type="checkbox" /> {item}</li>' for item in items)
                + "\n</ul>"
            )
            return InsertionResult(snippet, len(snippet))
        if kind == "Code Block":
            return build_html_code_block(selected_text)
        if kind == "Footnote":
            text = selected_text or "text"
            snippet = (
                f'{text}<sup id="fnref-1"><a href="#fn-1">1</a></sup>\n\n'
                f'<aside id="fn-1">Footnote text</aside>'
            )
            return InsertionResult(snippet, len(text) + 8)
        return InsertionResult(selected_text or "text", len(selected_text or "text"))

    def _prompt_table_shape(self) -> tuple[int, int, bool] | None:
        wx = self._wx

        def prompt_dimension(message: str, minimum: int, maximum: int) -> int | None:
            while True:
                with wx.TextEntryDialog(
                    self.frame,
                    message,
                    "Insert Table",
                    value="2",
                ) as dialog:
                    if self._show_modal_dialog(dialog, "Insert Table") != wx.ID_OK:
                        return None
                    raw_value = dialog.GetValue().strip()
                try:
                    value = int(raw_value)
                except ValueError:
                    self._show_message_box(
                        "Rows and columns must be whole numbers.",
                        "Insert Table",
                        wx.ICON_ERROR | wx.OK,
                    )
                    continue
                if value < minimum or value > maximum:
                    label = "Columns" if maximum == 12 else "Rows"
                    self._show_message_box(
                        f"{label} must be between {minimum} and {maximum}.",
                        "Insert Table",
                        wx.ICON_ERROR | wx.OK,
                    )
                    continue
                return value

        columns = prompt_dimension("Enter number of columns (1-12):", 1, 12)
        if columns is None:
            return None
        rows = prompt_dimension("Enter number of rows (1-50):", 1, 50)
        if rows is None:
            return None
        with wx.MessageDialog(
            self.frame,
            "Include a header row?",
            "Insert Table",
            wx.YES_NO | wx.ICON_QUESTION,
        ) as header_dialog:
            include_header = self._show_modal_dialog(header_dialog, "Insert Table") == wx.ID_YES
        return rows, columns, include_header

    def _prompt_code_language(self) -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame,
            "Optional language hint (example: python, javascript, sql):",
            "Insert Code Block",
            value="",
        ) as dialog:
            if self._show_modal_dialog(dialog, "Insert Code Block") != wx.ID_OK:
                return None
            return dialog.GetValue().strip()

    def _active_markup_surface(self) -> str | None:
        kind = infer_markup_kind(self.document.path)
        if kind in {"markdown", "html"}:
            return kind
        return None

    def _transform_selection_or_document(
        self,
        transform: Callable[[str], str],
        label: str,
    ) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status(f"{label} is unavailable in this profile")
            return
        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        if start != end:
            original = text[start:end]
            updated = transform(original)
            self._atomic_replace(start, end, updated)
            self.editor.SetSelection(start, start + len(updated))
            self.document.set_text(self.editor.GetValue())
            self._set_status(f"{label} applied to selection")
            return

        word_span = self._current_word_span_at_caret(text, self.editor.GetInsertionPoint())
        if word_span is None:
            self._set_status("No current word to transform")
            return
        word_start, word_end = word_span
        updated = transform(text[word_start:word_end])
        self._atomic_replace(word_start, word_end, updated)
        self.editor.SetSelection(word_start, word_start + len(updated))
        self.document.set_text(self.editor.GetValue())
        self._set_status(f"{label} applied to current word")

    def _atomic_replace(self, start: int, end: int, updated: str) -> None:
        """Replace ``text[start:end]`` with ``updated`` as ONE undo step.

        wx ``TextCtrl.Replace`` is recorded by the native control as two separate
        undo entries (a delete followed by an insert). Undoing a whole-document
        case transform then lands on an empty/corrupted intermediate state
        instead of the original text (#131). Selecting the range and writing over
        it records a single, cleanly reversible edit on every surface — plain
        ``wx.TextCtrl`` and the RTF Markdown lens alike — so one Ctrl+Z restores
        exactly the pre-transform text.
        """
        set_selection = getattr(self.editor, "SetSelection", None)
        write_text = getattr(self.editor, "WriteText", None)
        if callable(set_selection) and callable(write_text):
            set_selection(start, end)
            write_text(updated)
        else:  # pragma: no cover - defensive fallback for minimal stubs
            self.editor.Replace(start, end, updated)

    def _current_word_span_at_caret(self, text: str, caret: int) -> tuple[int, int] | None:
        if not text:
            return None
        caret = max(0, min(caret, len(text)))

        def is_word_char(character: str) -> bool:
            return character.isalnum() or character in {"_", "'"}

        if caret < len(text) and is_word_char(text[caret]):
            start = caret
            end = caret + 1
        elif caret > 0 and is_word_char(text[caret - 1]):
            start = caret - 1
            end = caret
        else:
            return None

        while start > 0 and is_word_char(text[start - 1]):
            start -= 1
        while end < len(text) and is_word_char(text[end]):
            end += 1
        if start == end:
            return None
        return start, end

    def _replace_document_text(self, updated_text: str) -> None:
        self._browse_navigation_cache = None
        current_text = self.editor.GetValue()
        self._atomic_replace(0, len(current_text), updated_text)
        self.editor.SetSelection(0, len(updated_text))
        self._schedule_browse_prewarm()

    def _apply_selection_operation(
        self,
        operation: Callable[[str, int, int], tuple[str, int, int]],
        status: str,
        *,
        no_change_status: str | None = None,
    ) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status(f"{status} is unavailable in this profile")
            return
        if self._document_is_read_only():
            self._set_status("Document is read-only")
            return
        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        updated, new_start, new_end = operation(text, start, end)
        if no_change_status is not None and updated == text:
            # The operation was a no-op (e.g. moving the top block up): announce
            # that accurately instead of a misleading "Moved..." status (#133).
            self._set_status(no_change_status)
            return
        self._replace_document_text(updated)
        self.document.set_text(updated)
        if new_start == new_end:
            self.editor.SetInsertionPoint(new_start)
            self.editor.SetSelection(new_start, new_start)
        else:
            self.editor.SetSelection(new_start, new_end)
        self._set_status(status)

    def _apply_text_block_operation(
        self,
        transform: Callable[[str], str],
        status: str,
    ) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status(f"{status} is unavailable in this profile")
            return
        if self._document_is_read_only():
            self._set_status("Document is read-only")
            return
        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        if start == end:
            start, end = line_span(text, self.editor.GetInsertionPoint())
        else:
            start = line_span(text, start)[0]
            end = line_span(text, max(0, end - 1))[1]
        updated_block = transform(text[start:end])
        updated = text[:start] + updated_block + text[end:]
        self._replace_document_text(updated)
        self.document.set_text(updated)
        self.editor.SetSelection(start, start + len(updated_block))
        self._set_status(status)

    def _apply_line_operation(
        self,
        operation: Callable[[str, int], tuple[str, int]],
        status: str,
    ) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status(f"{status} is unavailable in this profile")
            return
        if self._document_is_read_only():
            self._set_status("Document is read-only")
            return
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        updated, new_cursor = operation(text, cursor)
        self._replace_document_text(updated)
        self.document.set_text(updated)
        self.editor.SetInsertionPoint(new_cursor)
        self.editor.SetSelection(new_cursor, new_cursor)
        self._set_status(status)

    def _choose_searchable_option(
        self,
        *,
        title: str,
        prompt: str,
        dialog_label: str,
        initial_choices: list[str],
        search_callback: Callable[[str], list[str]],
        empty_search_examples: tuple[str, ...] = (),
    ) -> str | None:
        wx = self._wx
        with wx.Dialog(
            self.frame,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        ) as dialog:
            dialog.SetSize((560, 420))
            root = wx.BoxSizer(wx.VERTICAL)

            search = wx.SearchCtrl(dialog, style=wx.TE_PROCESS_ENTER)
            search.ShowSearchButton(True)
            search.SetDescriptiveText(prompt)
            root.Add(search, 0, wx.EXPAND | wx.ALL, 8)

            status = wx.StaticText(dialog, label="")
            root.Add(status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            results = wx.ListBox(dialog)
            root.Add(results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
            if buttons is not None:
                root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            dialog.SetSizer(root)

            last_query = self._searchable_picker_queries.get(dialog_label, "")
            if last_query:
                search.SetValue(last_query)

            filtered = list(initial_choices)

            def _refresh() -> None:
                nonlocal filtered
                filtered = list(search_callback(search.GetValue()))
                results.Set(filtered)
                if filtered:
                    results.SetSelection(0)
                    status.SetLabel(f"{len(filtered)} match(es). Top match: {filtered[0]}")
                else:
                    if empty_search_examples:
                        examples = ", ".join(empty_search_examples)
                        status.SetLabel(f"No matching options. Try: {examples}")
                    else:
                        status.SetLabel("No matching options")

            def _announce_selected() -> None:
                selected = results.GetSelection()
                if selected == wx.NOT_FOUND:
                    return
                if selected < 0 or selected >= len(filtered):
                    return
                status.SetLabel(f"Selected: {filtered[selected]}")

            def _accept(_event: object) -> None:
                if results.GetCount() == 0:
                    return
                dialog.EndModal(wx.ID_OK)

            def _on_char_hook(event: object) -> None:
                key_code = event.GetKeyCode()
                if key_code == wx.WXK_ESCAPE:
                    dialog.EndModal(wx.ID_CANCEL)
                    return
                if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                    _accept(event)
                    return
                if key_code == wx.WXK_DOWN and results.GetCount() > 0:
                    results.SetSelection(0)
                    results.SetFocus()
                    _announce_selected()
                    return
                if key_code == wx.WXK_UP and results.GetCount() > 0:
                    results.SetSelection(results.GetCount() - 1)
                    results.SetFocus()
                    _announce_selected()
                    return
                event.Skip()

            search.Bind(wx.EVT_TEXT, lambda _event: _refresh())
            search.Bind(wx.EVT_TEXT_ENTER, _accept)
            results.Bind(wx.EVT_LISTBOX, lambda _event: _announce_selected())
            results.Bind(wx.EVT_LISTBOX_DCLICK, _accept)
            dialog.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            _refresh()
            search.SetFocus()

            result = self._show_modal_dialog(dialog, dialog_label)
            self._searchable_picker_queries[dialog_label] = search.GetValue().strip()
            if result != wx.ID_OK:
                return None
            selected = results.GetSelection()
            if selected == wx.NOT_FOUND or selected < 0 or selected >= len(filtered):
                return None
            return filtered[selected]

    def insert_html_tag(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("HTML tag tools are unavailable in this profile")
            return
        tag = self._choose_searchable_option(
            title="Insert HTML Tag",
            prompt="Type to filter tags (for example: text, radio, button)",
            dialog_label="Insert HTML Tag",
            initial_choices=HTML_TAG_CHOICES,
            search_callback=search_html_tag_choices,
            empty_search_examples=("text", "radio", "button"),
        )
        if not tag:
            return

        wx = self._wx
        with wx.TextEntryDialog(
            self.frame,
            "Optional attributes (example: class=note; id=main; aria-label=Summary):",
            "Insert HTML Tag",
            value="",
        ) as attributes_dialog:
            if self._show_modal_dialog(attributes_dialog, "Insert HTML Tag") != wx.ID_OK:
                return
            attributes_raw = attributes_dialog.GetValue()

        selected_text = self.editor.GetStringSelection()
        attributes = parse_attribute_pairs(attributes_raw)
        result = build_html_insertion(tag, selected_text, attributes)
        self._apply_insertion_result(result)
        self._set_status(f"Inserted HTML tag <{tag}>")

    def insert_markdown_tag(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Markdown tag tools are unavailable in this profile")
            return
        kind = self._choose_searchable_option(
            title="Insert Markdown Tag",
            prompt="Type to filter markdown tags/snippets",
            dialog_label="Insert Markdown Tag",
            initial_choices=MARKDOWN_TAG_CHOICES,
            search_callback=search_markdown_tag_choices,
            empty_search_examples=("heading", "link", "image"),
        )
        if not kind:
            return

        wx = self._wx
        link_target = ""
        if kind in {"Link", "Image"}:
            with wx.TextEntryDialog(
                self.frame,
                "Enter target URL:",
                f"Insert {kind}",
                value="https://",
            ) as url_dialog:
                if self._show_modal_dialog(url_dialog, f"Insert {kind}") != wx.ID_OK:
                    return
                link_target = url_dialog.GetValue().strip()

        selected_text = self.editor.GetStringSelection()
        result = build_markdown_insertion(kind, selected_text, link_target=link_target)
        self._apply_insertion_result(result)
        self._set_status(f"Inserted markdown {kind.lower()}")

    def _snippet_picker_label(self, snippet: Snippet) -> str:
        if snippet.description:
            return f"{snippet.name} ({snippet.trigger}) — {snippet.description}"
        return f"{snippet.name} ({snippet.trigger})"

    def _save_snippets(self) -> None:
        if self._safe_mode:
            return
        save_snippet_library(self._snippet_library)

    def _prompt_for_snippet(self, *, initial_query: str = "") -> Snippet | None:
        snippets = self._snippet_library.snippets
        if not snippets:
            return None
        by_label = {self._snippet_picker_label(snippet): snippet for snippet in snippets}
        initial_choices = [
            self._snippet_picker_label(snippet) for snippet in search_snippets(snippets, "")
        ]
        choice = self._choose_searchable_option(
            title="Insert Snippet",
            prompt="Type to filter snippets by name, trigger, or text",
            dialog_label="Insert Snippet",
            initial_choices=initial_choices,
            search_callback=lambda query: [
                self._snippet_picker_label(snippet) for snippet in search_snippets(snippets, query)
            ],
            empty_search_examples=("email", "bug", ";meeting"),
        )
        if not choice:
            return None
        return by_label.get(choice)

    def _render_snippet_with_prompts(self, snippet: Snippet) -> SnippetExpansionResult | None:
        wx = self._wx
        values: dict[str, str] = {}
        for placeholder in extract_placeholders(snippet.body):
            if placeholder.kind in {"cursor", "date", "time"}:
                continue
            if placeholder.kind == "choice":
                with wx.SingleChoiceDialog(
                    self.frame,
                    f"Choose a value for {placeholder.name}:",
                    f"Snippet: {snippet.name}",
                    choices=placeholder.options,
                ) as dialog:
                    if self._show_modal_dialog(dialog, f"Snippet: {snippet.name}") != wx.ID_OK:
                        return None
                    selected = dialog.GetSelection()
                if selected == wx.NOT_FOUND:
                    return None
                values[placeholder.token] = placeholder.options[selected]
                continue
            with wx.TextEntryDialog(
                self.frame,
                f"Value for {placeholder.name}:",
                f"Snippet: {snippet.name}",
                value="",
            ) as dialog:
                if self._show_modal_dialog(dialog, f"Snippet: {snippet.name}") != wx.ID_OK:
                    return None
                values[placeholder.token] = dialog.GetValue()
        return render_snippet(snippet.body, values)

    def insert_snippet(self) -> None:
        snippet = self._prompt_for_snippet()
        if snippet is None:
            self._set_status("No snippets available. Open Manage Snippets to add one.")
            return
        rendered = self._render_snippet_with_prompts(snippet)
        if rendered is None:
            self._set_status("Snippet insertion cancelled")
            return
        self._apply_insertion_result(
            InsertionResult(inserted_text=rendered.text, caret_offset=rendered.cursor)
        )
        self._set_status(f'Inserted snippet "{snippet.name}".')

    def show_word_prediction(self) -> None:
        if not self._feature_enabled("core.intellisense"):
            self._set_status("Word prediction is unavailable in this profile")
            return
        if not self._show_intellisense_popup(manual=True):
            self._set_status("No predictions available")

    def _prompt_snippet_editor(self, existing: Snippet | None = None) -> Snippet | None:
        wx = self._wx
        name = existing.name if existing is not None else ""
        trigger = existing.trigger if existing is not None else ";"
        description = existing.description if existing is not None else ""
        body = existing.body if existing is not None else "${cursor}"
        with wx.TextEntryDialog(
            self.frame,
            "Snippet name:",
            "Edit Snippet" if existing is not None else "New Snippet",
            value=name,
        ) as name_dialog:
            if self._show_modal_dialog(name_dialog, "Snippet Name") != wx.ID_OK:
                return None
            name = name_dialog.GetValue().strip()
        if not name:
            self._set_status("Snippet name is required")
            return None
        with wx.TextEntryDialog(
            self.frame,
            "Trigger text (example: ;meeting):",
            "Snippet Trigger",
            value=trigger,
        ) as trigger_dialog:
            if self._show_modal_dialog(trigger_dialog, "Snippet Trigger") != wx.ID_OK:
                return None
            trigger = trigger_dialog.GetValue().strip()
        if not trigger:
            self._set_status("Snippet trigger is required")
            return None
        with wx.TextEntryDialog(
            self.frame,
            "Optional description:",
            "Snippet Description",
            value=description,
        ) as description_dialog:
            if self._show_modal_dialog(description_dialog, "Snippet Description") != wx.ID_OK:
                return None
            description = description_dialog.GetValue().strip()
        with wx.TextEntryDialog(
            self.frame,
            "Snippet body (supports ${input:name}, ${choice:a|b}, ${date}, ${time}, ${cursor}):",
            "Snippet Body",
            value=body,
            style=wx.OK | wx.CANCEL | wx.TE_MULTILINE,
        ) as body_dialog:
            if self._show_modal_dialog(body_dialog, "Snippet Body") != wx.ID_OK:
                return None
            body = body_dialog.GetValue()
        if not body:
            self._set_status("Snippet body is required")
            return None
        if existing is not None:
            snippet_id = existing.id
        else:
            snippet_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not snippet_id:
            snippet_id = f"snippet-{int(time.time())}"
        return Snippet(
            id=snippet_id,
            name=name,
            trigger=trigger,
            body=body,
            description=description,
            tags=list(existing.tags or []) if existing is not None else [],
            enabled=True if existing is None else existing.enabled,
            source=existing.source if existing is not None else "user",
        )

    def install_starter_snippet_packs(self) -> None:
        wx = self._wx
        packs = starter_pack_names()
        with wx.MultiChoiceDialog(
            self.frame,
            "Choose starter snippet packs to install:",
            "Install Starter Snippet Packs",
            choices=packs,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Install Starter Snippet Packs") != wx.ID_OK:
                self._set_status("Starter snippet pack installation cancelled")
                return
            selections = dialog.GetSelections()
        if not selections:
            self._set_status("No starter snippet packs selected")
            return
        before = len(self._snippet_library.snippets)
        library = self._snippet_library
        for index in selections:
            if 0 <= index < len(packs):
                library = merge_starter_pack(library, packs[index])
        self._snippet_library = library
        self._save_snippets()
        added = max(0, len(library.snippets) - before)
        self._set_status(f"Installed {added} snippet(s) from starter packs.")

    def manage_snippets(self) -> None:
        wx = self._wx
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose a snippet action:",
            "Manage Snippets",
            choices=[
                "Create snippet",
                "Edit snippet",
                "Delete snippet",
                "Import snippet library",
                "Export snippet library",
                "Install starter snippet packs",
            ],
        ) as dialog:
            if self._show_modal_dialog(dialog, "Manage Snippets") != wx.ID_OK:
                self._set_status("Manage snippets cancelled")
                return
            action = dialog.GetSelection()
        if action == wx.NOT_FOUND:
            self._set_status("Manage snippets cancelled")
            return
        if action == 5:
            self.install_starter_snippet_packs()
            return
        if action == 3:
            with wx.FileDialog(
                self.frame,
                "Import snippet library",
                wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if self._show_modal_dialog(dialog, "Import snippet library") != wx.ID_OK:
                    self._set_status("Snippet import cancelled")
                    return
                source = Path(dialog.GetPath())
            incoming = load_snippet_library(source)
            if not incoming.snippets:
                self._set_status("No snippets found in selected file")
                return
            by_id = {snippet.id: snippet for snippet in self._snippet_library.snippets}
            for snippet in incoming.snippets:
                by_id[snippet.id] = snippet
            self._snippet_library = SnippetLibrary(
                version=self._snippet_library.version,
                snippets=sorted(by_id.values(), key=lambda item: item.name.lower()),
            )
            self._save_snippets()
            self._set_status(f"Imported {len(incoming.snippets)} snippet(s).")
            return
        if action == 4:
            with wx.FileDialog(
                self.frame,
                "Export snippet library",
                wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as dialog:
                if self._show_modal_dialog(dialog, "Export snippet library") != wx.ID_OK:
                    self._set_status("Snippet export cancelled")
                    return
                destination = Path(dialog.GetPath())
            save_snippet_library(self._snippet_library, destination)
            self._set_status(f"Exported snippets to {destination.name}.")
            return
        if action == 0:
            created = self._prompt_snippet_editor()
            if created is None:
                self._set_status("Snippet creation cancelled")
                return
            if any(item.id == created.id for item in self._snippet_library.snippets):
                self._set_status("A snippet with that name already exists")
                return
            self._snippet_library.snippets.append(created)
            self._snippet_library.snippets.sort(key=lambda item: item.name.lower())
            self._save_snippets()
            self._set_status(f'Snippet "{created.name}" created.')
            return
        snippets = sorted(self._snippet_library.snippets, key=lambda item: item.name.lower())
        if not snippets:
            self._set_status("No snippets available")
            return
        labels = [self._snippet_picker_label(snippet) for snippet in snippets]
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose a snippet:",
            "Manage Snippets",
            choices=labels,
        ) as choose_dialog:
            if self._show_modal_dialog(choose_dialog, "Manage Snippets") != wx.ID_OK:
                self._set_status("Manage snippets cancelled")
                return
            selected = choose_dialog.GetSelection()
        if selected == wx.NOT_FOUND or selected < 0 or selected >= len(snippets):
            self._set_status("Manage snippets cancelled")
            return
        snippet = snippets[selected]
        if action == 2:
            confirm = self._show_message_box(
                f'Delete snippet "{snippet.name}"?',
                "Delete Snippet",
                wx.YES_NO | wx.ICON_WARNING,
            )
            if confirm != wx.YES:
                self._set_status("Snippet delete cancelled")
                return
            self._snippet_library.snippets = [
                item for item in self._snippet_library.snippets if item.id != snippet.id
            ]
            self._save_snippets()
            self._set_status(f'Snippet "{snippet.name}" deleted.')
            return
        if action != 1:
            self._set_status("Manage snippets cancelled")
            return
        edited = self._prompt_snippet_editor(snippet)
        if edited is None:
            self._set_status("Snippet edit cancelled")
            return
        updated: list[Snippet] = []
        for item in self._snippet_library.snippets:
            if item.id == snippet.id:
                updated.append(edited)
            else:
                updated.append(item)
        self._snippet_library.snippets = updated
        self._save_snippets()
        self._set_status(f'Snippet "{edited.name}" saved.')

    def _apply_insertion_result(self, result: InsertionResult) -> None:
        start, end = self.editor.GetSelection()
        self.editor.Replace(start, end, result.inserted_text)
        caret = start + result.caret_offset
        self.editor.SetInsertionPoint(caret)
        self.editor.SetFocus()

    def show_document_intake_report(self) -> None:
        report = build_intake_report(self.document)
        self._show_message_box(
            report, "Document Intake Report", self._wx.ICON_INFORMATION | self._wx.OK
        )

    def review_extraction_quality(self) -> None:
        report = build_extraction_quality_report(self.document)
        self._show_message_box(
            report, "Extraction Quality Review", self._wx.ICON_INFORMATION | self._wx.OK
        )

    def report_bad_extraction(self) -> None:
        wx = self._wx
        payload = build_bad_extraction_package(self.document, self.settings, __version__)
        with wx.FileDialog(
            self.frame,
            "Save extraction report",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save extraction report") != wx.ID_OK:
                self._set_status("Bad extraction report cancelled")
                return
            target = Path(dialog.GetPath())
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self._set_status(f"Saved extraction report to {target.name}")

    def show_context_help(self) -> None:
        report = build_context_help(
            self.document, bool(self.editor.GetSelection()[0] != self.editor.GetSelection()[1])
        )
        self._show_message_box(
            report, "What Can I Do Here?", self._wx.ICON_INFORMATION | self._wx.OK
        )

    def show_feature_explanation(self) -> None:
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame,
            "Enter a feature name, command, or topic:",
            "Why Don't I See a Feature?",
            value="regex",
        ) as dialog:
            if self._show_modal_dialog(dialog, "Why Don't I See a Feature?") != wx.ID_OK:
                return
            query = dialog.GetValue().strip()
        if not query:
            self._set_status("Feature lookup cancelled")
            return
        report = self.features.describe_feature(query)
        self._show_message_box(report, "Why Don't I See a Feature?", wx.ICON_INFORMATION | wx.OK)

    def _load_custom_profiles(self) -> dict[str, CustomProfile]:
        return load_custom_profiles()

    def _save_custom_profiles(self, profiles: dict[str, CustomProfile]) -> None:
        save_custom_profiles(profiles)

    def _combined_profile_entries(self) -> list[tuple[str, str, str]]:
        entries: list[tuple[str, str, str]] = [
            ("built_in", profile.id, profile.name) for profile in PROFILE_DEFINITIONS.values()
        ]
        for profile in self._load_custom_profiles().values():
            entries.append(("custom", profile.id, profile.name))
        return entries

    def _custom_profile_summary(self, profile: CustomProfile) -> str:
        raw_profile_data = profile.feature_profile_data
        active_profile_id = str(raw_profile_data.get("active_profile_id", PROFILE_ESSENTIAL))
        if active_profile_id not in PROFILE_DEFINITIONS:
            active_profile_id = PROFILE_ESSENTIAL
        overrides_raw = raw_profile_data.get("overrides")
        overrides = overrides_raw if isinstance(overrides_raw, dict) else {}
        base_states = PROFILE_DEFINITIONS[active_profile_id].states
        enabled = 0
        for feature_id, definition in FEATURE_DEFINITIONS.items():
            if definition.locked_on:
                enabled += 1
                continue
            override = overrides.get(feature_id)
            state = override if isinstance(override, str) else base_states.get(feature_id, "on")
            if state != "off":
                enabled += 1
        parent_name = PROFILE_DEFINITIONS.get(
            profile.parent_profile_id, PROFILE_DEFINITIONS[PROFILE_ESSENTIAL]
        ).name
        inheritance = (
            f"Inherits from {parent_name}."
            if profile.inherits_parent
            else "Starts from a bare-bones baseline."
        )
        return (
            f"Custom profile: {profile.name}\n\n"
            f"{profile.description or 'No description provided.'}\n\n"
            f"{inheritance}\nEnabled features: {enabled}\n"
            f"Keyboard bindings captured: {len(profile.keymap_data)}"
        )

    def _apply_custom_profile(self, profile: CustomProfile) -> None:
        self.features.import_profile_data(profile.feature_profile_data)
        merged_settings = asdict(self.settings)
        merged_settings.update(profile.settings_data)
        self.settings = Settings.from_dict(merged_settings)
        save_settings(self.settings)
        self.keymap = DEFAULT_KEYMAP.copy()
        self.keymap.update(profile.keymap_data)
        save_keymap(self.keymap)
        self._reload_shortcuts_from_keymap()
        self._apply_soft_wrap(self.settings.soft_wrap)
        self._rebuild_tab_host(self.settings.show_tab_control)
        self._apply_statusbar_layout()
        self._refresh_title()

    def switch_feature_profile(self) -> None:
        # The dedicated, accessible profile picker (Alt+Shift+P) replaced the old
        # SingleChoiceDialog + confirm + info-box flow (#138).
        self.open_profile_picker()

    def show_feature_profile_health_check(self) -> None:
        report = self.features.health_report(self.commands.list())
        self._show_message_box(
            report,
            "Feature Profile Health Check",
            self._wx.ICON_INFORMATION | self._wx.OK,
        )

    def open_individual_feature_toggles(self) -> None:
        """Per-feature override surface (FLAG-3).

        Lists every user-toggleable feature with a CheckBox reflecting its
        current effective state on top of the active profile. Locked-on and
        locked-off features are omitted because neither is user-toggleable.
        Individual wx.CheckBox controls are used instead of CheckListBox so
        screen readers (NVDA/JAWS) announce checked state on navigation.
        """
        wx = self._wx
        toggleable = sorted(
            (
                (feature_id, definition)
                for feature_id, definition in FEATURE_DEFINITIONS.items()
                if not definition.locked_on and not definition.locked_off
            ),
            key=lambda item: (item[1].category, item[1].name),
        )
        feature_ids = [feature_id for feature_id, _definition in toggleable]
        dialog = wx.Dialog(self.frame, title="Manage Individual Features", size=(700, 640))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Turn individual features on or off on top of your profile. "
                    "Enabling a feature also enables what it needs; disabling one "
                    "turns off the features that depend on it. "
                    "Use Space or Enter to toggle the focused feature."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )

        # Scrolled panel of individual CheckBox controls — NVDA/JAWS announce
        # "checked" / "not checked" natively when focus moves between them,
        # unlike CheckListBox which only announces name without state.
        scroll = wx.ScrolledWindow(dialog, style=wx.VSCROLL)
        scroll.SetScrollRate(0, 20)
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        checkboxes: list[wx.CheckBox] = []
        for feature_id, definition in toggleable:
            cb = wx.CheckBox(scroll, label=definition.name)
            cb.SetValue(self.features.is_enabled(feature_id))
            checkboxes.append(cb)
            scroll_sizer.Add(cb, 0, wx.ALL, 3)
        scroll.SetSizer(scroll_sizer)

        detail = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        detail.SetValue("Tab to a feature checkbox to see details below.")

        def sync_checks() -> None:
            for index, feature_id in enumerate(feature_ids):
                if index < len(checkboxes):
                    checkboxes[index].SetValue(self.features.is_enabled(feature_id))

        def refresh_detail(index: int) -> None:
            if 0 <= index < len(feature_ids):
                detail.SetValue(self.features.describe_feature(feature_ids[index]))

        def make_focus_handler(index: int):
            def _on_focus(_event: object) -> None:
                refresh_detail(index)

            return _on_focus

        def make_toggle_handler(index: int):
            def _on_toggle(_event: object) -> None:
                if index < 0 or index >= len(feature_ids):
                    return
                feature_id = feature_ids[index]
                enabled = checkboxes[index].GetValue()
                affected = self.features.set_feature_enabled(feature_id, enabled)
                announcement = self.features.describe_feature_toggle(feature_id, enabled, affected)
                sync_checks()
                refresh_detail(index)
                self._build_menu()
                self._apply_accelerators()
                self._set_status(announcement)

            return _on_toggle

        for i, cb in enumerate(checkboxes):
            cb.Bind(wx.EVT_CHECKBOX, make_toggle_handler(i))
            cb.Bind(wx.EVT_SET_FOCUS, make_focus_handler(i))

        root.Add(scroll, 1, wx.ALL | wx.EXPAND, 8)
        root.Add(detail, 0, wx.ALL | wx.EXPAND, 8)
        root.SetItemMinSize(detail, (-1, 80))
        buttons = dialog.CreateButtonSizer(wx.OK)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        dialog.SetSizerAndFit(root)
        if checkboxes:
            wx.CallAfter(checkboxes[0].SetFocus)
        self._show_modal_dialog(dialog, "Manage Individual Features")
        self._refresh_title()

    def _record_macro_step(self, command_id: str) -> None:
        macros = getattr(self, "macros", None)
        if macros is None:
            return
        if command_id in self._MACRO_CONTROL_COMMANDS:
            return
        macros.record(command_id)

    def start_macro_recording(self) -> None:
        wx = self._wx
        if self.macros.recording_name is not None:
            self._set_status(f"Already recording macro {self.macros.recording_name}")
            return
        with wx.TextEntryDialog(
            self.frame,
            "Enter a name for the new macro:",
            "Start Macro Recording",
            value="My Macro",
        ) as dialog:
            if self._show_modal_dialog(dialog, "Start Macro Recording") != wx.ID_OK:
                self._set_status("Macro recording cancelled")
                return
            name = dialog.GetValue().strip()
        if not name:
            self._set_status("Macro name cannot be empty")
            return
        try:
            self.macros.start_recording(name)
        except ValueError as error:
            self._set_status(str(error))
            return
        self._set_status(f"Recording macro {name}")

    def stop_macro_recording(self) -> None:
        macro = self.macros.stop_recording()
        if macro is None:
            self._set_status("No macro is being recorded")
            return
        self._set_status(f"Saved macro {macro.name} with {len(macro.steps)} step(s)")

    def play_last_macro(self) -> None:
        if self.macros.last_macro_name is None:
            self._set_status("No recorded macro to play")
            return
        try:
            self.macros.play_last_macro(self.commands.run)
        except KeyError:
            self._set_status("No recorded macro to play")
            return
        self._set_status(f"Played macro {self.macros.last_macro_name}")

    def manage_macros(self) -> None:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Manage Macros", size=(720, 420))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(dialog, label="Recorded macros are reusable command sequences."),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        names = list(self.macros.macros)
        chooser = wx.ListBox(dialog, choices=names)
        details = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        if names:
            chooser.SetSelection(0)

        def refresh_details() -> None:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND:
                details.SetValue("No macros recorded yet.")
                return
            name = names[selection]
            macro = self.macros.macros[name]
            details.SetValue(
                f"Macro: {macro.name}\nSteps: {len(macro.steps)}\n\n"
                + "\n".join(f"{index + 1}. {step}" for index, step in enumerate(macro.steps))
            )

        def play_selected() -> None:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND:
                return
            name = names[selection]
            try:
                self.macros.play_macro(name, self.commands.run)
            except KeyError:
                self._set_status(f"Macro {name} is no longer available")
                return
            self._set_status(f"Played macro {name}")

        def rename_selected() -> None:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND:
                return
            old_name = names[selection]
            with wx.TextEntryDialog(
                dialog,
                "Enter a new macro name:",
                "Rename Macro",
                value=old_name,
            ) as rename_dialog:
                if self._show_modal_dialog(rename_dialog, "Rename Macro") != wx.ID_OK:
                    return
                new_name = rename_dialog.GetValue().strip()
            if not new_name:
                self._set_status("Macro name cannot be empty")
                return
            try:
                self.macros.rename_macro(old_name, new_name)
            except (KeyError, ValueError) as error:
                self._set_status(str(error))
                return
            names[selection] = new_name
            chooser.SetItems(names)
            chooser.SetSelection(selection)
            refresh_details()
            self._set_status(f"Renamed macro to {new_name}")

        def delete_selected() -> None:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND:
                return
            name = names[selection]
            if (
                self._show_message_box(
                    f"Delete macro {name}?",
                    "Delete Macro",
                    wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
                )
                != wx.YES
            ):
                return
            try:
                self.macros.delete_macro(name)
            except KeyError:
                self._set_status(f"Macro {name} is no longer available")
                return
            del names[selection]
            chooser.SetItems(names)
            chooser.SetSelection(0 if names else wx.NOT_FOUND)
            refresh_details()
            self._set_status(f"Deleted macro {name}")

        chooser.Bind(wx.EVT_LISTBOX, lambda _e: refresh_details())
        play_button = wx.Button(dialog, label="Play")
        rename_button = wx.Button(dialog, label="Rename")
        delete_button = wx.Button(dialog, label="Delete")
        close_button = wx.Button(dialog, id=wx.ID_OK, label="Close")
        play_button.Bind(wx.EVT_BUTTON, lambda _e: play_selected())
        rename_button.Bind(wx.EVT_BUTTON, lambda _e: rename_selected())
        delete_button.Bind(wx.EVT_BUTTON, lambda _e: delete_selected())
        close_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))

        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)
        root.Add(details, 1, wx.ALL | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(play_button, 0, wx.RIGHT, 6)
        buttons.Add(rename_button, 0, wx.RIGHT, 6)
        buttons.Add(delete_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(close_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        refresh_details()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        self._show_modal_dialog(dialog, "Manage Macros")

    def open_profiles_and_features_settings(self) -> None:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Profiles and Features", size=(820, 700))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Choose a feature profile, inspect what it changes, and import or export "
                    "profile data."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        chooser = wx.ListBox(dialog, choices=[])
        entries: list[tuple[str, str, str]] = []
        summary = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        keyboard_pack_choices = keyboard_pack_names(include_custom=True)
        keyboard_pack_choice = wx.Choice(dialog, choices=keyboard_pack_choices)
        current_pack = self.settings.keyboard_pack
        if current_pack not in keyboard_pack_choices:
            current_pack = KEYBOARD_PACK_DEFAULT
        keyboard_pack_choice.SetStringSelection(current_pack)
        keyboard_preview = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 160),
        )

        def refresh_profile_list(preferred_id: str | None = None) -> None:
            nonlocal entries
            entries = self._combined_profile_entries()
            labels = [
                name if kind == "built_in" else f"{name} (Custom)"
                for kind, _profile_id, name in entries
            ]
            chooser.Set(labels)
            selected_id = preferred_id or self.features.active_profile_id
            selected_index = 0
            for index, (_kind, profile_id, _name) in enumerate(entries):
                if profile_id == selected_id:
                    selected_index = index
                    break
            if entries:
                chooser.SetSelection(selected_index)

        def selected_entry() -> tuple[str, str, str] | None:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND or selection < 0 or selection >= len(entries):
                return None
            return entries[selection]

        def refresh_summary() -> None:
            entry = selected_entry()
            if entry is None:
                summary.SetValue(self.features.profile_summary())
                return
            kind, profile_id, _name = entry
            if kind == "built_in":
                summary.SetValue(self.features.change_profile_preview(profile_id))
                return
            custom_profile = self._load_custom_profiles().get(profile_id)
            if custom_profile is None:
                summary.SetValue("Custom profile is no longer available.")
                return
            summary.SetValue(self._custom_profile_summary(custom_profile))

        def refresh_keyboard_preview() -> None:
            pack_name = keyboard_pack_choice.GetStringSelection() or KEYBOARD_PACK_DEFAULT
            description = keyboard_pack_description(pack_name)
            preview = keyboard_pack_preview(pack_name)
            if preview == description:
                keyboard_preview.SetValue(description)
                return
            keyboard_preview.SetValue(preview)

        def switch_selected() -> None:
            entry = selected_entry()
            if entry is None:
                return
            kind, profile_id, name = entry
            if kind == "built_in":
                if profile_id == self.features.active_profile_id:
                    self._set_status(f"Already using {name}")
                    return
                self.features.switch_profile(profile_id)
                self._set_status(f"Profile changed to {name}. Undo available.")
            else:
                custom_profile = self._load_custom_profiles().get(profile_id)
                if custom_profile is None:
                    self._set_status("Custom profile is no longer available")
                    refresh_profile_list()
                    refresh_summary()
                    return
                self._apply_custom_profile(custom_profile)
                self._set_status(f"Profile changed to {custom_profile.name}.")
            refresh_summary()
            self._refresh_title()

        def compare_selected() -> None:
            entry = selected_entry()
            if entry is None:
                return
            kind, profile_id, _name = entry
            if kind != "built_in":
                self._show_message_box(
                    "Profile comparison is available for built-in profiles.",
                    "Compare Profiles",
                    wx.ICON_INFORMATION | wx.OK,
                )
                return
            message = self.features.compare_profiles(self.features.active_profile_id, profile_id)
            self._show_message_box(message, "Compare Profiles", wx.ICON_INFORMATION | wx.OK)

        def undo_change() -> None:
            if self.features.undo_last_profile_change():
                self._set_status(f"Restored {self.features.active_profile.name}")
                refresh_summary()
                self._refresh_title()
                return
            self._set_status("No profile change to undo")

        def reset_essential() -> None:
            self.features.reset_to_essential_profile()
            refresh_profile_list(PROFILE_ESSENTIAL)
            refresh_summary()
            self._set_status("Reset to Essential profile")
            self._refresh_title()

        def create_custom_profile() -> None:
            with wx.TextEntryDialog(
                dialog,
                "Enter a name for the custom profile:",
                "Create Custom Profile",
                value="My Custom Profile",
            ) as name_dialog:
                if self._show_modal_dialog(name_dialog, "Create Custom Profile") != wx.ID_OK:
                    return
                name = name_dialog.GetValue().strip()
            if not name:
                self._set_status("Custom profile name cannot be empty")
                return
            with wx.TextEntryDialog(
                dialog,
                "Optional description:",
                "Create Custom Profile",
                value="",
            ) as description_dialog:
                if self._show_modal_dialog(description_dialog, "Create Custom Profile") != wx.ID_OK:
                    return
                description = description_dialog.GetValue().strip()
            built_in_profiles = list(PROFILE_DEFINITIONS.values())
            parent_labels = [self._profile_choice_label(profile) for profile in built_in_profiles]
            with wx.SingleChoiceDialog(
                dialog,
                "Choose the parent (global) profile:",
                "Create Custom Profile",
                choices=parent_labels,
            ) as parent_dialog:
                if self._show_modal_dialog(parent_dialog, "Create Custom Profile") != wx.ID_OK:
                    return
                parent_selection = parent_dialog.GetSelection()
            if parent_selection == wx.NOT_FOUND:
                return
            parent_profile = built_in_profiles[parent_selection]
            with wx.MessageDialog(
                dialog,
                (
                    "Inherit the selected parent profile's feature set?\n\n"
                    "Yes keeps inherited defaults. No starts from bare bones "
                    "(only locked core features remain enabled)."
                ),
                "Custom Profile Inheritance",
                wx.YES_NO | wx.ICON_QUESTION,
            ) as inherit_dialog:
                inherits_parent = (
                    self._show_modal_dialog(inherit_dialog, "Custom Profile Inheritance")
                    == wx.ID_YES
                )
            if not inherits_parent:
                self._show_message_box(
                    "Bare-bones mode selected. Most features are disabled until you turn them on.",
                    "Bare-Bones Profile",
                    wx.ICON_WARNING | wx.OK,
                )
            custom_profiles = self._load_custom_profiles()
            profile_id = generate_custom_profile_id(name, set(custom_profiles))
            if inherits_parent:
                feature_profile_data = build_parent_profile_data(parent_profile.id)
                settings_data = asdict(self.settings)
                keymap_data = dict(self.keymap)
            else:
                feature_profile_data = build_bare_bones_profile_data()
                settings_data = asdict(Settings())
                keymap_data = DEFAULT_KEYMAP.copy()
            custom_profiles[profile_id] = CustomProfile(
                id=profile_id,
                name=name,
                description=description,
                parent_profile_id=parent_profile.id,
                inherits_parent=inherits_parent,
                feature_profile_data=feature_profile_data,
                settings_data=settings_data,
                keymap_data=keymap_data,
            )
            self._save_custom_profiles(custom_profiles)
            refresh_profile_list(profile_id)
            refresh_summary()
            self._set_status(f"Created custom profile {name}")

        def update_selected_custom_profile() -> None:
            entry = selected_entry()
            if entry is None:
                return
            kind, profile_id, _name = entry
            if kind != "custom":
                self._set_status("Select a custom profile to update")
                return
            custom_profiles = self._load_custom_profiles()
            custom_profile = custom_profiles.get(profile_id)
            if custom_profile is None:
                self._set_status("Custom profile is no longer available")
                refresh_profile_list()
                refresh_summary()
                return
            custom_profile.feature_profile_data = self.features.export_profile_data()
            custom_profile.settings_data = asdict(self.settings)
            custom_profile.keymap_data = dict(self.keymap)
            custom_profiles[profile_id] = custom_profile
            self._save_custom_profiles(custom_profiles)
            refresh_summary()
            self._set_status(f"Updated custom profile {custom_profile.name} from current state")

        def delete_selected_custom_profile() -> None:
            entry = selected_entry()
            if entry is None:
                return
            kind, profile_id, name = entry
            if kind != "custom":
                self._set_status("Select a custom profile to delete")
                return
            confirm = self._show_message_box(
                f"Delete custom profile {name}?",
                "Delete Custom Profile",
                wx.YES_NO | wx.ICON_WARNING,
            )
            if confirm != wx.YES:
                return
            custom_profiles = self._load_custom_profiles()
            custom_profiles.pop(profile_id, None)
            self._save_custom_profiles(custom_profiles)
            refresh_profile_list()
            refresh_summary()
            self._set_status(f"Deleted custom profile {name}")

        def apply_selected_keyboard_pack() -> None:
            pack_name = keyboard_pack_choice.GetStringSelection() or KEYBOARD_PACK_DEFAULT
            if pack_name == KEYBOARD_PACK_CUSTOM:
                self._set_status("Custom layouts are managed by the keymap editor")
                return
            self.apply_keyboard_pack(pack_name)
            refresh_keyboard_preview()

        def reset_keyboard_pack() -> None:
            keyboard_pack_choice.SetStringSelection(KEYBOARD_PACK_DEFAULT)
            self.apply_keyboard_pack(KEYBOARD_PACK_DEFAULT)
            refresh_keyboard_preview()

        def customize_keymap() -> None:
            self.open_keymap_editor()
            current = self.settings.keyboard_pack
            if current not in keyboard_pack_choices:
                current = KEYBOARD_PACK_CUSTOM
            keyboard_pack_choice.SetStringSelection(current)
            refresh_keyboard_preview()

        def export_profile() -> None:
            with wx.FileDialog(
                dialog,
                message="Export profile data",
                wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as file_dialog:
                if self._show_modal_dialog(file_dialog, "Export Profile") != wx.ID_OK:
                    return
                target = Path(file_dialog.GetPath())
            target.write_text(
                json.dumps(self.features.export_profile_data(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self._set_status(f"Exported profile data to {target.name}")

        def import_profile() -> None:
            with wx.FileDialog(
                dialog,
                message="Import profile data",
                wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as file_dialog:
                if self._show_modal_dialog(file_dialog, "Import Profile") != wx.ID_OK:
                    return
                source = Path(file_dialog.GetPath())
            raw = json.loads(source.read_text(encoding="utf-8"))
            warnings = self.features.import_profile_data(raw)
            for warning in warnings:
                self._record_notification(warning, "warning")
            refresh_profile_list(self.features.active_profile_id)
            refresh_summary()
            self._set_status(f"Imported profile data from {source.name}")
            self._refresh_title()

        chooser.Bind(wx.EVT_LISTBOX, lambda _e: refresh_summary())
        keyboard_pack_choice.Bind(wx.EVT_CHOICE, lambda _e: refresh_keyboard_preview())
        switch_button = wx.Button(dialog, label="Switch Profile")
        compare_button = wx.Button(dialog, label="Compare Profiles")
        undo_button = wx.Button(dialog, label="Undo Last Change")
        reset_button = wx.Button(dialog, label="Reset to Essential")
        create_custom_button = wx.Button(dialog, label="Create Custom...")
        update_custom_button = wx.Button(dialog, label="Update Custom from Current")
        delete_custom_button = wx.Button(dialog, label="Delete Custom")
        export_button = wx.Button(dialog, label="Export...")
        import_button = wx.Button(dialog, label="Import...")
        apply_pack_button = wx.Button(dialog, label="Apply Keyboard Pack")
        reset_pack_button = wx.Button(dialog, label="Reset Keyboard Pack")
        customize_pack_button = wx.Button(dialog, label="Customize Shortcuts...")
        close_button = wx.Button(dialog, id=wx.ID_OK, label="Close")
        switch_button.Bind(wx.EVT_BUTTON, lambda _e: switch_selected())
        compare_button.Bind(wx.EVT_BUTTON, lambda _e: compare_selected())
        undo_button.Bind(wx.EVT_BUTTON, lambda _e: undo_change())
        reset_button.Bind(wx.EVT_BUTTON, lambda _e: reset_essential())
        create_custom_button.Bind(wx.EVT_BUTTON, lambda _e: create_custom_profile())
        update_custom_button.Bind(wx.EVT_BUTTON, lambda _e: update_selected_custom_profile())
        delete_custom_button.Bind(wx.EVT_BUTTON, lambda _e: delete_selected_custom_profile())
        export_button.Bind(wx.EVT_BUTTON, lambda _e: export_profile())
        import_button.Bind(wx.EVT_BUTTON, lambda _e: import_profile())
        apply_pack_button.Bind(wx.EVT_BUTTON, lambda _e: apply_selected_keyboard_pack())
        reset_pack_button.Bind(wx.EVT_BUTTON, lambda _e: reset_keyboard_pack())
        customize_pack_button.Bind(wx.EVT_BUTTON, lambda _e: customize_keymap())
        close_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))

        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)
        root.Add(summary, 1, wx.ALL | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Keyboard experience: choose a golden pack inspired by familiar editors, "
                    "or keep a fully custom layout."
                ),
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND,
            8,
        )
        root.Add(keyboard_pack_choice, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(keyboard_preview, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(switch_button, 0, wx.RIGHT, 6)
        buttons.Add(compare_button, 0, wx.RIGHT, 6)
        buttons.Add(undo_button, 0, wx.RIGHT, 6)
        buttons.Add(reset_button, 0, wx.RIGHT, 6)
        buttons.Add(create_custom_button, 0, wx.RIGHT, 6)
        buttons.Add(update_custom_button, 0, wx.RIGHT, 6)
        buttons.Add(delete_custom_button, 0, wx.RIGHT, 6)
        buttons.Add(export_button, 0, wx.RIGHT, 6)
        buttons.Add(import_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(apply_pack_button, 0, wx.RIGHT, 6)
        buttons.Add(reset_pack_button, 0, wx.RIGHT, 6)
        buttons.Add(customize_pack_button, 0, wx.RIGHT, 6)
        buttons.Add(close_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        refresh_profile_list()
        refresh_summary()
        refresh_keyboard_preview()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        self._show_modal_dialog(dialog, "Profiles and Features")

    def undo_last_profile_change(self) -> None:
        if self.features.undo_last_profile_change():
            self._set_status(f"Profile changed back to {self.features.active_profile.name}")
            self._refresh_title()
            return
        self._set_status("No profile change to undo")

    def reset_feature_profile_to_essential(self) -> None:
        wx = self._wx
        with wx.MessageDialog(
            self.frame,
            "Reset Quill to the Essential profile?",
            "Reset Feature Profile",
            wx.YES_NO | wx.ICON_QUESTION,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Reset Feature Profile") != wx.ID_YES:
                return
        self.features.reset_to_essential_profile()
        self._set_status("Reset to Essential profile")
        self._refresh_title()

    def show_help_on_control(self) -> None:
        """F1: show context-sensitive help for the currently focused control.

        The main editor is a plain ``wx.TextCtrl`` with a friendly accessible name
        rather than a help-topic name, so F1 in the document window is routed to
        the ``main.editor`` topic explicitly (otherwise it resolved to "no help").
        """
        focused = self._wx.Window.FindFocus()
        editor = getattr(self, "editor", None)
        if editor is not None and focused is editor:
            self.show_topic_help("main.editor", user_guide_opener=self.open_user_guide_section)
            return
        self.show_control_help(user_guide_opener=self.open_user_guide_section)

    def open_user_guide_section(self, section: str | None = None) -> None:
        """Open the user guide, optionally scrolling to *section*."""
        self.open_user_guide(start_anchor=section)

    def run_startup_wizard(self, *, first_run: bool = False) -> None:
        from quill.core.settings import save_settings
        from quill.ui.setup_wizard import run_setup_wizard

        feature_manager: FeatureManager = self.features
        changed = run_setup_wizard(
            self.frame, self.settings, feature_manager, show_modal_fn=self._show_modal_dialog
        )
        if changed:
            save_settings(self.settings)
            feature_manager.save()
            self._apply_accelerators()
            self._set_status("Personalise QUILL completed")
        elif first_run:
            # User pressed Escape or Cancel on the first-run wizard.  Ask
            # whether they want to stop seeing it on every launch.
            with self._wx.MessageDialog(
                self.frame,
                "The setup wizard will appear again next time QUILL starts.\n\n"
                "Do you want to disable it so it does not open automatically?",
                "Setup Wizard",
                self._wx.YES_NO | self._wx.NO_DEFAULT | self._wx.ICON_QUESTION,
            ) as dlg:
                if self._show_modal_dialog(dlg, "Setup Wizard") == self._wx.ID_YES:
                    self.settings.setup_wizard_completed = True
                    save_settings(self.settings)

    def run_profile_onboarding(self) -> None:
        # Backward-compatible alias for older command IDs and automation scripts.
        self.run_startup_wizard()

    def _maybe_run_first_run_onboarding(self) -> None:
        def _focus_editor() -> None:
            editor = getattr(self, "editor", None)
            if editor is not None and hasattr(editor, "SetFocus"):
                self._wx.CallAfter(editor.SetFocus)

        # New unified first-run wizard: run when setup_wizard_completed is False
        # (i.e., a fresh install that has not seen the wizard yet).  After the
        # wizard finishes or is cancelled, skip the legacy per-feature prompts so
        # they do not double-up on top of the new flow.
        if not getattr(self.settings, "setup_wizard_completed", True):
            try:
                self.run_startup_wizard(first_run=True)
            except Exception:
                self._report_startup_task_failure("first-run setup wizard")
            for _flag in (
                "_first_run_profile_prompt",
                "_first_run_assistant_prompt",
                "_first_run_glow_prompt",
                "_first_run_speech_prompt",
                "_first_run_watch_folder_prompt",
            ):
                setattr(self, _flag, False)
            _focus_editor()
            return

        if any((
            getattr(self, "_first_run_trust_consent_prompt", False),
            getattr(self, "_first_run_profile_prompt", False),
            getattr(self, "_first_run_assistant_prompt", False),
            getattr(self, "_first_run_glow_prompt", False),
            getattr(self, "_first_run_speech_prompt", False),
            getattr(self, "_first_run_watch_folder_prompt", False),
        )):
            if load_startup_wizard_prompt_suppressed():
                self._set_status("Startup Wizard prompt suppressed")
                _focus_editor()
                return
            self.show_startup_wizard_page()
            if hasattr(self.frame, "SetFocus"):
                self.frame.SetFocus()
            if not self._show_startup_wizard_first_run_prompt():
                self._set_status("Startup Wizard overview opened")
                _focus_editor()
                return
        if getattr(self, "_first_run_profile_prompt", False):
            self._show_profile_onboarding(force=False)
            self._first_run_profile_prompt = False
            self._offer_ai_onboarding()
        if getattr(self, "_first_run_assistant_prompt", False):
            self._show_assistant_onboarding(force=False)
            self._first_run_assistant_prompt = False
        if getattr(self, "_first_run_glow_prompt", False):
            self._show_glow_onboarding(force=False)
            self._first_run_glow_prompt = False
        if getattr(self, "_first_run_speech_prompt", False):
            self._show_speech_onboarding(force=False)
            self._first_run_speech_prompt = False
        if getattr(self, "_first_run_watch_folder_prompt", False):
            self._show_watch_folder_onboarding(force=False)
            self._first_run_watch_folder_prompt = False
        _focus_editor()

    def _show_startup_wizard_first_run_prompt(self) -> bool:
        wx = self._wx
        dialog = wx.RichMessageDialog(
            self.frame,
            "Start guided setup now?\n\n"
            "Choose Yes to continue through profile, AI, assistant, speech, "
            "and watch folder setup.",
            "Startup Wizard",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        if hasattr(dialog, "SetYesNoLabels"):
            dialog.SetYesNoLabels("Yes", "No")
        if hasattr(dialog, "ShowCheckBox"):
            dialog.ShowCheckBox("Do not show this again")

        apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
        try:
            result = self._show_modal_dialog(dialog, "Startup Wizard")
            is_checked = getattr(dialog, "IsCheckBoxChecked", None)
            if callable(is_checked) and is_checked():
                mark_startup_wizard_prompt_suppressed()
        finally:
            dialog.Destroy()
        return result == wx.ID_YES

    def show_startup_wizard_page(self) -> None:
        from quill.ui.preview_dialog import MarkdownPreviewDialog

        MarkdownPreviewDialog(
            self.frame,
            "Startup Wizard",
            self._build_startup_wizard_html(),
        ).show()
        self._set_status("Opened Startup Wizard overview")

    def _show_trust_consent_onboarding(self, force: bool) -> bool:
        wx = self._wx
        message = (
            "By selecting I accept, you confirm that:\n\n"
            "1. You are responsible for how AI outputs are used, reviewed, and shared.\n"
            "2. Cloud AI requests are user-initiated and subject to provider terms.\n"
            "3. Quill does not persist chat session transcripts from AI interactions.\n"
            "4. API keys are stored in Windows Credential Manager when available, "
            "with DPAPI-encrypted fallback storage.\n\n"
            "Do you accept and want to continue?"
        )
        dialog = wx.MessageDialog(
            self.frame,
            message,
            "Trust, Privacy, and Responsible AI Use",
            wx.YES_NO | wx.ICON_INFORMATION,
        )
        if hasattr(dialog, "SetYesNoLabels"):
            dialog.SetYesNoLabels("I accept", "I do not accept")
        try:
            accepted = self._show_modal_dialog(dialog, "Trust and Privacy Consent") == wx.ID_YES
        finally:
            dialog.Destroy()
        if accepted:
            mark_trust_consent_complete()
            return True
        return False

    def _build_startup_wizard_html(self) -> str:
        done = "Done"
        todo = "Not set up yet"
        setup_steps = [
            (
                "A quick word on privacy",
                done if load_trust_consent_complete() else todo,
                "How Quill looks after your writing and uses AI, in plain terms.",
            ),
            (
                "How Quill starts",
                done if load_onboarding_complete() else todo,
                "Pick a starting setup that matches how you like to work.",
            ),
            (
                "Writing help",
                done if load_assistant_onboarding_complete() else todo,
                "Turn on optional AI writing help and choose its style.",
            ),
            (
                "Accessibility engine (GLOW)",
                done if load_glow_onboarding_complete() else todo,
                "GLOW is on by default and runs on your computer; optional network "
                "features stay off until you turn them on.",
            ),
            (
                "Speech and voices",
                done if load_speech_onboarding_complete() else todo,
                "Choose voices and download optional speech only if you want it.",
            ),
            (
                "Speech model preferences",
                (
                    done
                    if bool(getattr(self.settings, "bw_provider_id", ""))
                    and bool(getattr(self.settings, "bw_speech_model_id", ""))
                    else todo
                ),
                "Pick your preferred speech provider and voice model.",
            ),
            (
                "Open a folder automatically",
                done if load_watch_folder_onboarding_complete() else todo,
                "Let Quill open files you drop into one folder for you.",
            ),
        ]
        steps_html = "".join(
            (
                "<li>"
                f"<strong>{html.escape(step)}</strong> &mdash; {html.escape(state)}. "
                f"{html.escape(detail)}"
                "</li>"
            )
            for step, state, detail in setup_steps
        )

        return (
            "<h1 id='startup-wizard'>Startup Wizard</h1>"
            "<p>Welcome to Quill &mdash; a fast, friendly writing app built to work "
            "beautifully with your screen reader. This short setup gets things ready "
            "the way you like. You can stop any time and come back later.</p>"
            "<h2 id='what-youll-set-up'>What you'll set up</h2>"
            "<p>Each step is optional and takes a moment. Here's what it gives you "
            "and what you've finished so far:</p>"
            f"<ul>{steps_html}</ul>"
            "<h2 id='good-to-know'>Good to know</h2>"
            "<ul>"
            "<li>Everything works from the keyboard, and Quill tells you what just happened.</li>"
            "<li>You can skip a step now and set it up later.</li>"
            "<li>Nothing is downloaded until you say yes.</li>"
            "<li>To start over, open Startup Wizard again from the Help menu.</li>"
            "</ul>"
            "<h2 id='where-next'>You're all set</h2>"
            "<p>That's it &mdash; you're ready to write. To check on downloads, "
            "speech, and what's turned on, open Help &gt; Status Page.</p>"
        )

    def _show_bw_onboarding(self, force: bool) -> None:
        wx = self._wx
        response = self._show_message_box(
            "Configure BITS Whisperer rollout defaults now?\n\n"
            "This step safely stages provider/model setup and status preferences without enabling "
            "runtime routing changes.",
            "BITS Whisperer Setup",
            wx.ICON_QUESTION | wx.YES_NO,
        )
        if response != wx.YES:
            if force:
                self._set_status("BITS Whisperer setup skipped")
            return
        self.apply_bw_recommended_provider()
        self.apply_bw_recommended_model()
        if not bool(getattr(self.settings, "bw_auto_open_status_page_on_download_start", False)):
            auto_open = self._show_message_box(
                "Auto-open Help > Status Page when BITS Whisperer model downloads start?",
                "BITS Whisperer Setup",
                wx.ICON_QUESTION | wx.YES_NO,
            )
            self.settings.bw_auto_open_status_page_on_download_start = auto_open == wx.YES
            save_settings(self.settings)
        self._set_status("BITS Whisperer rollout defaults configured")

    def _offer_ai_onboarding(self) -> None:
        """First run: ask whether to use AI; if yes, set up the model."""
        from quill.core.ai.llama_cpp_backend import LlamaCppBackend
        from quill.core.ai.model_manager import existing_model, save_ai_enabled

        wx = self._wx
        use_ai = self._show_message_box(
            "Do you want to use Quill's built-in artificial intelligence (Ask Quill)?\n\n"
            "It runs entirely on your computer. You can turn it on or off later from "
            "Tools > AI Assistant.",
            "Use Artificial Intelligence?",
            wx.ICON_QUESTION | wx.YES_NO,
        )
        enabled = use_ai == wx.YES
        save_ai_enabled(enabled)
        self._sync_ai_enabled_menu(enabled)
        if not enabled:
            self._set_status("AI is off. You can enable it later from Tools > AI Assistant.")
            return
        # Foundation Models (macOS) needs no download; only llama.cpp does.
        assistant = self._get_assistant()
        if (
            isinstance(assistant.backend, LlamaCppBackend)
            and assistant.is_available()[0]
            and not existing_model()
        ):
            AIModelDialog(self.frame, announce=self._set_status).show()
        else:
            self._set_status("AI is ready.")

    def _sync_ai_enabled_menu(self, enabled: bool) -> None:
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None and hasattr(self, "_id_ai_enabled"):
            item = menu_bar.FindItemById(self._id_ai_enabled)
            if item is not None:
                item.Check(enabled)

    def _show_profile_onboarding(self, force: bool) -> None:
        wx = self._wx
        profiles = list(PROFILE_DEFINITIONS.values())
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose how Quill should start:",
            "Profile Onboarding",
            choices=self._profile_choice_labels(profiles),
        ) as dialog:
            if self._show_modal_dialog(dialog, "Profile Onboarding") != wx.ID_OK:
                if not force:
                    mark_onboarding_complete()
                if force:
                    self._set_status("Profile onboarding skipped")
                return
            selection = dialog.GetSelection()
        if selection == wx.NOT_FOUND:
            if not force:
                mark_onboarding_complete()
            return
        profile = profiles[selection]
        self.features.switch_profile(profile.id)
        mark_onboarding_complete()
        self._set_status(f"Quill starts in the {profile.name} profile")
        self._refresh_title()

    def _show_assistant_onboarding(self, force: bool) -> None:
        from quill.ui.web_form import show_web_form

        styles = [
            ("balanced", "Balanced"),
            ("concise", "Concise"),
            ("gentle", "Gentle"),
            ("technical", "Technical"),
        ]
        values = show_web_form(
            self.frame,
            self._wx,
            title="Writing Assistant Onboarding",
            intro=(
                "Quill can seed the writing assistant with a few focused prompt styles. "
                "You can change this later in General Preferences."
            ),
            fields=[
                {
                    "name": "enabled",
                    "label": "Enable the writing assistant by default",
                    "type": "checkbox",
                    "value": getattr(self.settings, "assistant_enabled", False),
                },
                {
                    "name": "style",
                    "label": "Prompt style",
                    "type": "select",
                    "value": getattr(self.settings, "assistant_prompt_style", "balanced"),
                    "options": styles,
                },
            ],
        )
        if values is None:
            if not force:
                mark_assistant_onboarding_complete()
            return
        self.settings.assistant_enabled = bool(values.get("enabled"))
        style = str(values.get("style", "balanced"))
        if style not in {key for key, _ in styles}:
            style = "balanced"
        self.settings.assistant_prompt_style = style
        save_settings(self.settings)
        mark_assistant_onboarding_complete()
        self._set_status("Configured writing assistant onboarding")

    def _show_glow_onboarding(self, force: bool) -> None:
        from quill.ui.web_form import show_web_form

        values = show_web_form(
            self.frame,
            self._wx,
            title="GLOW Accessibility Onboarding",
            intro=(
                "GLOW is Quill's built-in accessibility engine. It is turned on by "
                "default and runs entirely on your computer. A few optional GLOW "
                "features can use a network connection; these stay off until you turn "
                "them on here, and Quill never sends your document anywhere without "
                "asking first. You can change any of this later in Preferences."
            ),
            fields=[
                {
                    "name": "enabled",
                    "label": "Keep the GLOW accessibility engine enabled",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_enabled", True),
                },
                {
                    "name": "ai_alt_text",
                    "label": "Allow optional AI alt-text generation (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_ai_alt_text_consent", False),
                },
                {
                    "name": "pii_redaction",
                    "label": "Allow optional PII redaction (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_pii_redaction_consent", False),
                },
                {
                    "name": "language_processing",
                    "label": "Allow optional WCAG language processing (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_language_processing_consent", False),
                },
            ],
        )
        if values is None:
            if not force:
                mark_glow_onboarding_complete()
            return
        self.settings.glow_enabled = bool(values.get("enabled", True))
        self.settings.glow_ai_alt_text_consent = bool(values.get("ai_alt_text"))
        self.settings.glow_pii_redaction_consent = bool(values.get("pii_redaction"))
        self.settings.glow_language_processing_consent = bool(values.get("language_processing"))
        save_settings(self.settings)
        mark_glow_onboarding_complete()
        self._set_status("Configured GLOW accessibility onboarding")

    def _show_speech_onboarding(self, force: bool) -> None:  # noqa: PLR0912
        wx = self._wx
        start_setup = self._show_message_box(
            "Set up speech engines now?\n\n"
            "You can download/configure DECtalk, eSpeak-NG, Piper, Kokoro, "
            "and OpenVoice.\n"
            "You can always change these later in AI > Speech > Settings.",
            "Speech Setup",
            wx.ICON_QUESTION | wx.YES_NO,
        )
        if start_setup != wx.YES:
            if not force:
                mark_speech_onboarding_complete()
            self._set_status("Speech setup skipped")
            return

        choices = [
            "Download and configure DECtalk runtime (recommended)",
            "Configure eSpeak-NG path and English variant",
            "Configure Piper executable and English model folder",
            "Configure Kokoro English voice defaults",
            "Configure OpenVoice executable, English voice, and consent",
            "Open speech setup docs",
        ]
        with wx.MultiChoiceDialog(
            self.frame,
            "Select the speech setup steps you want to run now:",
            "Speech Setup",
            choices=choices,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Speech Setup") != wx.ID_OK:
                if not force:
                    mark_speech_onboarding_complete()
                self._set_status("Speech setup cancelled")
                return
            selected = set(dialog.GetSelections())

        def _ask_text(prompt: str, value: str) -> str | None:
            with wx.TextEntryDialog(self.frame, prompt, "Speech Setup", value=value) as td:
                if self._show_modal_dialog(td, "Speech Setup") != wx.ID_OK:
                    return None
                return td.GetValue().strip()

        if 0 in selected:
            speech_root = app_data_dir() / "speech" / "dectalk"

            def work(progress: Callable[[str, int, int], None]) -> object:
                progress("Downloading DECtalk runtime", 0, 1)
                exe = download_dectalk_runtime(speech_root)
                progress("Finalizing DECtalk runtime", 1, 1)
                return str(exe)

            def on_success(result: object) -> None:
                self.settings.read_aloud_dectalk_executable = str(result)
                save_settings(self.settings)
                self._set_status("DECtalk runtime downloaded and configured")

            self._run_background_task(
                "Downloading DECtalk speech runtime",
                work,
                on_success,
                notify_on_success=True,
                notify_on_error=True,
                notification_category="speech",
            )

        if 1 in selected:
            path = _ask_text(
                "Path to espeak-ng.exe (leave blank to use PATH):",
                self.settings.read_aloud_espeak_executable,
            )
            if path is not None:
                self.settings.read_aloud_espeak_executable = path
            voices = list_espeak_english_voices()
            if voices:
                voice_names = [voice.name for voice in voices]
                with wx.SingleChoiceDialog(
                    self.frame,
                    "Choose default eSpeak English voice:",
                    "Speech Setup",
                    choices=voice_names,
                ) as voice_dialog:
                    if self._show_modal_dialog(voice_dialog, "Speech Setup") == wx.ID_OK:
                        idx = voice_dialog.GetSelection()
                        if 0 <= idx < len(voices):
                            self.settings.read_aloud_espeak_voice = voices[idx].id

        if 2 in selected:
            exe = _ask_text("Path to piper.exe:", self.settings.read_aloud_piper_executable)
            if exe is not None:
                self.settings.read_aloud_piper_executable = exe
            model_dir = _ask_text(
                "Folder containing English Piper .onnx models:",
                self.settings.read_aloud_piper_model_dir,
            )
            if model_dir is not None:
                self.settings.read_aloud_piper_model_dir = model_dir

        if 3 in selected:
            voices = list_kokoro_voices()
            if voices:
                with wx.SingleChoiceDialog(
                    self.frame,
                    "Choose default Kokoro English voice:",
                    "Speech Setup",
                    choices=[voice.name for voice in voices],
                ) as voice_dialog:
                    if self._show_modal_dialog(voice_dialog, "Speech Setup") == wx.ID_OK:
                        idx = voice_dialog.GetSelection()
                        if 0 <= idx < len(voices):
                            self.settings.read_aloud_kokoro_voice = voices[idx].id

        if 4 in selected:
            exe = _ask_text(
                "Path to OpenVoice executable:", self.settings.read_aloud_openvoice_executable
            )
            if exe is not None:
                self.settings.read_aloud_openvoice_executable = exe
            voices = list_openvoice_english_voices()
            if voices:
                with wx.SingleChoiceDialog(
                    self.frame,
                    "Choose default OpenVoice English voice:",
                    "Speech Setup",
                    choices=[voice.name for voice in voices],
                ) as voice_dialog:
                    if self._show_modal_dialog(voice_dialog, "Speech Setup") == wx.ID_OK:
                        idx = voice_dialog.GetSelection()
                        if 0 <= idx < len(voices):
                            self.settings.read_aloud_openvoice_voice = voices[idx].id
            consent = self._show_message_box(
                "Enable OpenVoice advanced style module on this machine?\n\n"
                "This feature is optional and remains disabled unless you explicitly consent.",
                "Speech Setup",
                wx.YES_NO | wx.ICON_QUESTION,
            )
            self.settings.read_aloud_openvoice_consent = consent == wx.YES

        if 5 in selected:
            docs_path = app_data_dir().parent / "Quill" / "docs" / "userguide.md"
            webbrowser.open(str(docs_path))

        save_settings(self.settings)
        mark_speech_onboarding_complete()
        self._set_status("Speech setup complete")

    def _profile_choice_labels(self, profiles: list[object]) -> list[str]:
        return [self._profile_choice_label(profile) for profile in profiles]

    def _profile_choice_label(self, profile: object) -> str:
        name = str(getattr(profile, "name", "Profile")).strip()
        description = " ".join(str(getattr(profile, "description", "")).split())
        if not description:
            return name
        return f"{name} — {description}"

    def show_regex_helper(self) -> None:
        wx = self._wx

        recipes = [
            (
                "Email address",
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
                "Matches common email addresses.",
            ),
            (
                "HTTP or HTTPS URL",
                r"https?://[^\s)]+",
                "Matches links that begin with http:// or https://.",
            ),
            (
                "Markdown heading",
                r"(?m)^\s{0,3}#{1,6}\s+.+$",
                "Matches Markdown headings from H1 to H6.",
            ),
            (
                "Numbered list item",
                r"(?m)^\s*\d+[.)]\s+.+$",
                "Matches list lines like 1. Item or 2) Item.",
            ),
            (
                "Markdown link",
                r"\[[^\]]+\]\([^)]+\)",
                "Matches Markdown links like [label](url).",
            ),
            (
                "Double-spaced words",
                r"\S\s{2,}\S",
                "Finds words separated by two or more spaces.",
            ),
        ]

        dialog = wx.Dialog(
            self.frame,
            title="Regular Expression Helper",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        dialog.SetSize((820, 640))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            dialog,
            label=(
                "Choose a recipe, review the pattern in plain language, then preview matches "
                "against sample text before using it in Find/Replace."
            ),
        )
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        content = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(dialog, label="Recipes"), 0, wx.BOTTOM, 6)
        recipe_list = wx.ListBox(dialog, choices=[item[0] for item in recipes])
        left.Add(recipe_list, 1, wx.EXPAND)
        content.Add(left, 0, wx.EXPAND | wx.ALL, 10)

        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(dialog, label="Pattern"), 0, wx.BOTTOM, 4)
        pattern_ctrl = wx.TextCtrl(dialog, style=wx.TE_PROCESS_ENTER)
        right.Add(pattern_ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)

        right.Add(wx.StaticText(dialog, label="What this pattern means"), 0, wx.BOTTOM, 4)
        explanation_ctrl = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        explanation_ctrl.SetMinSize((480, 80))
        right.Add(explanation_ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)

        right.Add(wx.StaticText(dialog, label="Sample text"), 0, wx.BOTTOM, 4)
        default_sample = self.editor.GetStringSelection().strip() or self.editor.GetValue()[:1200]
        sample_ctrl = wx.TextCtrl(dialog, value=default_sample, style=wx.TE_MULTILINE)
        sample_ctrl.SetMinSize((480, 170))
        right.Add(sample_ctrl, 1, wx.EXPAND | wx.BOTTOM, 8)

        right.Add(wx.StaticText(dialog, label="Preview results"), 0, wx.BOTTOM, 4)
        results_ctrl = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        results_ctrl.SetMinSize((480, 170))
        right.Add(results_ctrl, 1, wx.EXPAND)

        content.Add(right, 1, wx.EXPAND | wx.ALL, 10)
        root.Add(content, 1, wx.EXPAND)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        preview_btn = wx.Button(dialog, label="Preview")
        copy_btn = wx.Button(dialog, label="Copy Pattern")
        close_btn = wx.Button(dialog, id=wx.ID_CLOSE, label="Close")
        button_row.Add(preview_btn, 0, wx.RIGHT, 8)
        button_row.Add(copy_btn, 0, wx.RIGHT, 8)
        button_row.AddStretchSpacer(1)
        button_row.Add(close_btn, 0)
        root.Add(button_row, 0, wx.EXPAND | wx.ALL, 10)

        dialog.SetSizerAndFit(root)
        apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)

        def set_recipe(index: int) -> None:
            if index < 0 or index >= len(recipes):
                return
            _name, pattern, explanation = recipes[index]
            pattern_ctrl.SetValue(pattern)
            explanation_ctrl.SetValue(explanation)

        def render_preview() -> None:
            pattern = pattern_ctrl.GetValue()
            sample = sample_ctrl.GetValue()
            if not pattern.strip():
                results_ctrl.SetValue("Enter a pattern to preview matches.")
                return
            try:
                matches = list(re.finditer(pattern, sample, re.MULTILINE))
            except re.error as error:
                results_ctrl.SetValue(f"Pattern error: {error}")
                return
            if not matches:
                results_ctrl.SetValue("No matches found in sample text.")
                return
            lines = [f"Matches found: {len(matches)}"]
            for idx, match in enumerate(matches[:25], start=1):
                value = match.group(0).replace("\n", "\\n")
                if len(value) > 80:
                    value = value[:77] + "..."
                lines.append(f"{idx}. {match.start()}-{match.end()}: {value}")
            if len(matches) > 25:
                lines.append(f"...and {len(matches) - 25} more")
            results_ctrl.SetValue("\n".join(lines))

        def on_recipe_selected(_event: object) -> None:
            set_recipe(recipe_list.GetSelection())
            render_preview()

        def on_preview(_event: object) -> None:
            render_preview()

        def on_copy(_event: object) -> None:
            pattern = pattern_ctrl.GetValue()
            if not pattern.strip():
                self._set_status("Regular Expression helper: no pattern to copy")
                return
            if self._copy_to_clipboard(pattern):
                self._set_status("Regular Expression pattern copied")
            else:
                self._set_status("Regular Expression helper could not copy pattern")

        def on_close(_event: object) -> None:
            dialog.EndModal(wx.ID_CLOSE)

        recipe_list.Bind(wx.EVT_LISTBOX, on_recipe_selected)
        preview_btn.Bind(wx.EVT_BUTTON, on_preview)
        copy_btn.Bind(wx.EVT_BUTTON, on_copy)
        close_btn.Bind(wx.EVT_BUTTON, on_close)
        pattern_ctrl.Bind(wx.EVT_TEXT_ENTER, on_preview)

        recipe_list.SetSelection(0)
        set_recipe(0)
        render_preview()
        recipe_list.SetFocus()

        try:
            self._show_modal_dialog(dialog, "Regular Expression Helper")
        finally:
            dialog.Destroy()

    def copy_with_source(self) -> None:
        start, end = self.editor.GetSelection()
        if start == end:
            start, end = line_span(self.editor.GetValue(), self.editor.GetInsertionPoint())
        selection = self.editor.GetRange(start, end)
        if not selection.strip():
            self._set_status("Nothing selected to copy")
            return
        source = build_source_reference(
            self.document, self.editor.GetInsertionPoint(), self.editor.GetValue()
        )
        payload = f"{selection}\n\n{source}"
        if not self._copy_to_clipboard(payload):
            self._set_status("Could not copy with source")
            return
        self._set_status("Copied selection with source")

    def _copy_to_clipboard(self, text: str) -> bool:
        wx = self._wx
        data_object = wx.TextDataObject(text)
        clipboard = wx.TheClipboard
        if not clipboard.Open():
            return False
        try:
            clipboard.SetData(data_object)
        finally:
            clipboard.Close()
        return True

    def exit_app(self) -> None:
        self._is_exiting = True
        self.frame.Close()


def run_app(
    startup_requests: list[object] | None = None,
    safe_mode: bool = False,
    diagnostics_mode: bool = False,
) -> None:
    import wx

    app = wx.App(False)
    mark_wx_main_thread()
    if diagnostics_mode or should_trace_memory():
        start_memory_tracing()
    frame = MainFrame(safe_mode=safe_mode)
    heartbeat_state = HeartbeatState()
    frame._stability_heartbeat_state = heartbeat_state
    frame._stability_heartbeat_timer = WxHeartbeatTimer(frame.frame, heartbeat_state)
    frame._stability_watchdog = WxHeartbeatWatchdog(heartbeat_state)
    frame._stability_watchdog.start()
    for request in startup_requests or []:
        if request is None:
            continue
        path = getattr(request, "path", None)
        if isinstance(path, Path) and path.exists() and path.is_file():
            frame._handle_shell_request(request)
    frame.show()
    try:
        app.MainLoop()
    finally:
        timer = getattr(frame, "_stability_heartbeat_timer", None)
        if timer is not None:
            timer.stop()
        watchdog = getattr(frame, "_stability_watchdog", None)
        if watchdog is not None:
            watchdog.stop()
