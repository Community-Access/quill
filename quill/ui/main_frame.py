from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import webbrowser
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar
from uuid import uuid4

try:
    import winsound as _winsound  # type: ignore[import]
except ImportError:  # pragma: no cover - non-Windows fallback
    _winsound = None  # type: ignore[assignment]

if TYPE_CHECKING:  # imports kept out of cold-start path
    from quill.core.accessibility_agent import AgentRunResult
    from quill.core.epub import EpubBook, EpubChapter
    from quill.ui.main_frame_compare import _CompareSession

from quill import __version__, build_info
from quill.branding import APP_SHORT_NAME
from quill.core import thesaurus as thesaurus_engine
from quill.core.a11y_regions import (
    RegionTracker,
)
from quill.core.ai import Assistant
from quill.core.ai.agent import allowed_tools
from quill.core.autoformat import EM_DASH, is_dash_merge, smart_quote_for
from quill.core.autosave import autosave_document
from quill.core.backups import backup_document, list_backups
from quill.core.bookmarks import (  # N-13: keep the module as the supported home for these helpers
    DocumentMemory,
    bookmark_names,
    bookmark_position,
    quick_slot_name,
    set_bookmark,
)
from quill.core.browser_preview import (
    browser_choice_label_for_value,
    guess_preview_kind,
    normalize_browser_choice,
    open_preview_url,
    preview_anchor_for_text,
    render_preview_body,
    render_preview_html,
)
from quill.core.code_folding import (
    FoldableRegion,
    extract_foldable_regions,
    next_region_boundary,
    previous_region_boundary,
    region_line_count,
    smallest_region_containing,
)
from quill.core.commands import CommandRegistry
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
from quill.core.custom_profiles import (
    CustomProfile,
    build_bare_bones_profile_data,
    build_parent_profile_data,
    generate_custom_profile_id,
    load_custom_profiles,
    save_custom_profiles,
)
from quill.core.deletion_ring import DeletionRing, removed_span
from quill.core.diagnostics import (
    build_diagnostics_review_text,
    build_support_issue_url,
    collect_environment_info,
    record_diagnostic_event,
    write_diagnostics_bundle,
)
from quill.core.dictation import (
    DictationController,
)
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
from quill.core.favorite_folders import (
    FavoriteFile,
    FavoriteFolders,
    filter_favorite_files,
    list_files_in_favorites,
)
from quill.core.features import (
    FEATURE_DEFINITIONS,
    PROFILE_DEFINITIONS,
    PROFILE_ESSENTIAL,
    FeatureManager,
)
from quill.core.format_ops import (
    continue_markdown_list,
    describe_indent_depth,
    indent_lines,
    outdent_lines,
    toggle_block_comment,
    toggle_line_comment,
)
from quill.core.glow import build_audit_report, build_fix_report, fix_text
from quill.core.guides import (
    build_keyboard_shortcut_html,
    build_welcome_guide,
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
    format_binding_for_display,
    keyboard_pack_description,
    keyboard_pack_names,
    keyboard_pack_preview,
    load_keymap,
    save_keymap,
)
from quill.core.language_profile import (
    PLAIN_PROFILE,
    LanguageProfile,
    all_profiles,
    get_profile_by_name,
    get_profile_for_path,
)
from quill.core.lexical_preload import start_lexical_preload
from quill.core.links import build_link_text, find_link_at_cursor, infer_markup_kind
from quill.core.locations import LocationRing
from quill.core.macros import MacroManager
from quill.core.markdown_sections import (
    _LIST_AUTO_FILL_ARM_SECONDS,
    HeadingBlock,
    apply_heading_organizer_edits,
    fill_numbered_markers,
    heading_context_at,
    is_caret_inside_list,
    parse_heading_blocks,
    should_auto_fill_numbers,
    strip_list_markers,
    validate_heading_sequence,
)
from quill.core.marks import MarkRing, NamedMarks, line_column_for_position
from quill.core.menu_customization import (
    MenuCustomization,
    load_menu_customization,
)
from quill.core.metrics import compute_document_stats
from quill.core.multi_press import MultiPressDispatcher
from quill.core.navigation import (
    estimate_page_count,
    estimate_page_start_for_number,
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
    load_trust_consent_complete,
    load_trust_consent_status,
    mark_trust_consent_complete,
    trust_consent_change_log,
)
from quill.core.outline import OutlineEntry, extract_outline_entries
from quill.core.paths import app_data_dir, ensure_app_directories
from quill.core.platform_nouns import credential_store_name, primary_command_chord_label
from quill.core.publishing_linkage import (
    apply_publishing_linkage_to_source_metadata,
    get_publishing_linkage,
    publishing_linkage_from_source_metadata,
    upsert_publishing_linkage,
)
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
    default_piper_model_dir,
    discover_dectalk_executable,
    discover_espeak_executable,
    discover_piper_executable,
    resolve_piper_model_path,
    synthesize_to_file_with_dectalk,
    synthesize_to_file_with_sapi5,
    synthesize_with_espeak,
    synthesize_with_kokoro,
    synthesize_with_macos,
    synthesize_with_piper,
)
from quill.core.recent import (
    add_recent_file,
    clear_recent_files,
    load_recent_files,
    prune_missing_recent_files,
    save_recent_files,
)
from quill.core.recovery import (
    begin_session,
    mark_clean_exit,
    mark_recovery_offer_dismissed,
    mark_recovery_offer_recovered,
    read_recovery_snapshot,
)
from quill.core.search import SearchOptions
from quill.core.search_history import load_search_history
from quill.core.selection import (
    line_span,
    paragraph_span,
)
from quill.core.sessions import (
    load_recent_sessions,
)
from quill.core.settings import Settings, load_settings, save_settings
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
from quill.core.sound_events import SoundEvent
from quill.core.spellcheck import (
    Misspelling,
    misspelling_at_position,
    suggest_words,
)
from quill.core.spellcheck import (
    set_active_language as spellcheck_set_active_language,
)
from quill.core.spoken_echo import format_spoken_echo, new_history, record_spoken
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
from quill.core.url_ops import format_content_length
from quill.core.watch_actions import WatchActionOutcome
from quill.core.watch_profiles import (
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
from quill.io.export import (
    EXPORT_ONLY_SUFFIXES,
    HTML_SUFFIXES,
    format_label_for_path,
    write_document_as,
    write_plain_text_document,
)
from quill.io.open_read import OFFICE_STREAM_SUFFIXES as _OFFICE_STREAM_SUFFIXES
from quill.io.open_read import read_open_document
from quill.io.pandoc import (
    PandocConversionError,
    PandocUnavailableError,
    convert_document_with_pandoc,
    convert_file_with_pandoc,
)
from quill.platform.announce_engine import AnnouncementEngine, prewarm_tts_engine
from quill.platform.sr_announce import (
    announce,
    enable_transcript_capture,
    set_announce_handler,
    set_transcript_path,
)
from quill.platform.windows.high_contrast import is_high_contrast_enabled
from quill.platform.windows.shell_integration import (
    apply_shell_verb_settings,
    build_shell_integration_plan,
    install_shell_integration,
    launcher_command,
    remove_context_menu,
    remove_shell_integration,
)
from quill.platform.windows.sr_detect import detect_screen_reader
from quill.stability.memory_watch import should_trace_memory, start_memory_tracing
from quill.stability.task_manager import TaskManager
from quill.stability.ui_responsiveness import mark_wx_main_thread
from quill.stability.wx_heartbeat import HeartbeatState, WxHeartbeatTimer, WxHeartbeatWatchdog
from quill.ui.accessible_names import pin_macos_text_area_role
from quill.ui.context_help import ContextHelpMixin, warm_help_topics
from quill.ui.csv_grid import CsvGridSurface
from quill.ui.dialog_contract import (
    apply_modal_ids,
    focus_primary_control,
    ok_cancel_platform_order,
    set_accessible_name,
    show_modal_dialog,
)
from quill.ui.html_paste_cleaner import analyze_paste
from quill.ui.keymap_editor import KeymapEditorMixin
from quill.ui.main_frame_abbreviations import AbbreviationsMixin
from quill.ui.main_frame_adp import AdpMixin
from quill.ui.main_frame_ai_actions import AiActionsMixin
from quill.ui.main_frame_braille import BrailleCommandsMixin
from quill.ui.main_frame_braille_phase2 import BraillePhase2CommandsMixin
from quill.ui.main_frame_braille_phase3 import BrailleProofingCommandsMixin
from quill.ui.main_frame_braille_repair import BrailleRepairMixin
from quill.ui.main_frame_browse import BrowseModeMixin
from quill.ui.main_frame_bw import BwSpeechMixin
from quill.ui.main_frame_classic_editor import ClassicEditorMixin
from quill.ui.main_frame_clip_library import ClipLibraryMixin
from quill.ui.main_frame_commands import CommandRegistryMixin
from quill.ui.main_frame_compare import CompareMixin
from quill.ui.main_frame_copy_tray import CopyTrayMixin
from quill.ui.main_frame_devtools import DevToolsMixin
from quill.ui.main_frame_dictation_hotkeys import DictationHotkeysMixin
from quill.ui.main_frame_docconvert import DocConvertMixin
from quill.ui.main_frame_emoji_picker import EmojiPickerMixin
from quill.ui.main_frame_format_codes import FormatCodesMixin
from quill.ui.main_frame_gh_bridge import GhBridgeMixin
from quill.ui.main_frame_git_sync import GitSyncMixin
from quill.ui.main_frame_github import GitHubRemoteMixin
from quill.ui.main_frame_github_admin import GitHubAdminMixin
from quill.ui.main_frame_github_extras import GitHubExtrasMixin
from quill.ui.main_frame_github_items import GitHubItemsMixin
from quill.ui.main_frame_glow import GlowFileMixin
from quill.ui.main_frame_hotkeys import GlobalHotkeysMixin
from quill.ui.main_frame_hygiene import HygieneMixin
from quill.ui.main_frame_image import ImageCaptureMixin
from quill.ui.main_frame_image_alt import ImageAltMixin
from quill.ui.main_frame_inline_notes import InlineNotesMixin
from quill.ui.main_frame_intellisense import IntellisensePopupMixin
from quill.ui.main_frame_keymap_io import KeymapIoMixin
from quill.ui.main_frame_language_detect import LanguageDetectMixin
from quill.ui.main_frame_line_commands import LineCommandsMixin
from quill.ui.main_frame_list_studio import ListStudioMixin
from quill.ui.main_frame_local_git import LocalGitMixin
from quill.ui.main_frame_media_sleep_timer import MediaSleepTimerMixin
from quill.ui.main_frame_menu import MenuBuilderMixin
from quill.ui.main_frame_menu_bindings import MenuBindingsMixin
from quill.ui.main_frame_menu_editor import (
    _TOP_MENU_DEFS,
    MenuEditorMixin,
    _normalize_menu_label,
)
from quill.ui.main_frame_notebook import NotebookUIMixin
from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.main_frame_power_tools import PowerToolsActionsMixin
from quill.ui.main_frame_power_tools_menu import PowerToolsMenuMixin
from quill.ui.main_frame_preferences import PreferencesMixin
from quill.ui.main_frame_print import PrintMixin
from quill.ui.main_frame_profile_picker import ProfilePickerMixin
from quill.ui.main_frame_publishing import PublishingCommandsMixin
from quill.ui.main_frame_quill_key import QuillKeyMixin
from quill.ui.main_frame_quillins import QuillinsMenuMixin
from quill.ui.main_frame_radio import RadioMixin
from quill.ui.main_frame_restore_points import RestorePointsMixin
from quill.ui.main_frame_reveal_codes import RevealCodesMixin
from quill.ui.main_frame_rich_mode import RichModeMixin
from quill.ui.main_frame_search import SearchCommandsMixin
from quill.ui.main_frame_section_move import SectionMoveMixin
from quill.ui.main_frame_selection import SelectionMarksMixin
from quill.ui.main_frame_sessions import SessionsMixin
from quill.ui.main_frame_simple_open import SimpleOpenMixin
from quill.ui.main_frame_speech import SpeechCommandsMixin
from quill.ui.main_frame_speech_downloads import SpeechDownloadsMixin
from quill.ui.main_frame_speech_voice import VoiceInteractionMixin
from quill.ui.main_frame_spellcheck import SpellcheckCommandsMixin
from quill.ui.main_frame_ssh import SshEditingMixin
from quill.ui.main_frame_statusbar import StatusBarMixin, _StatusBarCell
from quill.ui.main_frame_story_studio import StoryStudioMixin
from quill.ui.main_frame_unlock_codes import UnlockCodesMixin
from quill.ui.main_frame_updates import UpdatesMixin
from quill.ui.main_frame_vault import VaultMixin
from quill.ui.main_frame_verbosity import VerbosityCommandsMixin
from quill.ui.main_frame_watch_profile import WatchProfileDialogMixin
from quill.ui.main_frame_work_persona import WorkPersonaMixin
from quill.ui.notebook_panel import NotebookEntriesPanel
from quill.ui.sound_manager import post_sound
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
    """Structured Word (.docx) view is enabled for everyday use (#514).

    Un-gated once the accessible Word surface (``word_view.py``,
    ``WordDocumentSurface``) was complete and tested: opening a ``.doc``/``.docx``
    honours the ``word_open_mode`` setting (prompt / structured / text), so users
    can choose the structured Word view or the normal text editor. The CSV-grid
    half of #514 stays gated (``_csv_feature_enabled``) — that is table work."""
    return True


def _csv_feature_enabled() -> bool:
    """CSV grid view is NOT enabled on this branch.

    Experimental and not ready for users: hard-disabled,
    so CSV files always open in the normal text editor and there is no env-var
    override. Developed on the feature/structured-surfaces branch."""
    return False


def _sapi5_voice_short_name(voice_id: str) -> str:
    """Normalize a SAPI5 registry voice ID to a lowercase short name.

    Windows SAPI 5 voices have IDs like:
      'HKEY_LOCAL_MACHINE\\...\\TTS_MS_EN-US_DAVID_11.0'
    This extracts 'david' so we can look up a bundled preview sample.
    """
    last = voice_id.replace("/", "\\").rsplit("\\", 1)[-1]
    skip = {"TTS", "MS"}
    for part in last.upper().split("_"):
        if not part or part in skip:
            continue
        if "-" in part:  # language codes: EN-US, EN-GB
            continue
        try:
            float(part)
            continue  # version numbers: 11.0
        except ValueError:
            pass
        if part.isalpha():
            return part.lower()
    return last.lower()


@dataclass(slots=True)
class _DocumentTab:
    panel: object
    editor: object
    document: Document
    splitter: object = None
    preview: object = None
    source_label: str = ""
    read_only_remote: bool = False
    # One Editor, Every Format: how this tab presents its document.
    #   "markup"         — the buffer is canonical QUILL markup (default).
    #   "rich"           — the native control holds real formatting (TOM/RTF);
    #                      the buffer mirrors the plain text.
    #   "rich_converted" — an .rtf/.docx opened through the conversion bridge
    #                      (no native rich available); buffer is markup and
    #                      save re-serializes to the rich format.
    editor_mode: str = "markup"
    # The extension the Document Format switcher retargeted this tab to
    # ("" = follow document.path). Save As proposes the renamed path; Save
    # never silently rewrites a different extension in place.
    pending_format_suffix: str = ""
    # The remembered answer to the plain-text first-formatting-command prompt
    # ("" = not asked yet; "markdown" / "rich" / "plain" once answered).
    plain_format_choice: str = ""
    # Phase 7 (docx rich): this rich tab's on-disk format is .docx (save runs
    # RichDocument -> rich_to_docx_bytes instead of native RTF).
    docx_rich: bool = False
    # Phase 7: the honest-fidelity scan flagged out-of-vocabulary features in
    # the original (tables, images, tracked changes, ...).
    docx_flagged: bool = False
    # Phase 7 (docx rich): whether the one-time pre-overwrite backup of a
    # fidelity-flagged original has been written for this tab.
    rich_backup_done: bool = False
    # Per-document named bookmarks (loaded from / saved to DocumentMemory for saved
    # files; in-memory only for untitled documents). The active tab's dict is
    # aliased to MainFrame._bookmarks while it is the current tab.
    bookmarks: dict[str, int] = field(default_factory=dict)
    # Single unnamed, one-shot jump point (Leasey-style temp bookmark). Session-only:
    # never persisted to DocumentMemory, deliberately forgotten on restart.
    temp_bookmark: int | None = None
    # Per-document inline notes (content-anchored). Loaded from / saved to the
    # InlineNoteVault for saved files; in-memory only for untitled documents.
    inline_notes: list = field(default_factory=list)
    # Folded region state (accessible code folding, x.md PRD). Session-only:
    # never persisted, purely a reading-session convenience. Keyed by
    # (start, end) of the FoldableRegion currently marked folded.
    folded_regions: set[tuple[int, int]] = field(default_factory=set)
    _indent_tone_last_level: int = -1
    _language_profile: object = None
    _language_profile_pinned: bool = False


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
        # The popup's frame is a child of MainFrame's own frame; if that parent
        # was torn down and rebuilt (e.g. a crash-recovery restart) without this
        # popup object being recreated alongside it, self.frame is a deleted
        # C/C++ object and IsShown() raises RuntimeError (#917/#918).
        try:
            return bool(self.frame.IsShown())
        except RuntimeError:
            return False

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


# #615: Short product+version label for the window title bar. Read once at
# import time so every title refresh reuses the same string. This is the
# in-process channel screen readers announce when the user asks for the
# focused window title; the Ctrl+JAWSKey+V (version) hotkey lives in the
# OS layer and reads the launcher's VersionInfo, which the portable build
# does not have.
_APP_TITLE_VERSION = f"QUILL for All {build_info.get_short_version()}"

# #11: name the background-indicator surface what the user actually sees -- the
# Windows system tray, or the macOS menu-bar status item. Read once at import.
_TRAY_NOUN = "menu bar" if sys.platform == "darwin" else "system tray"

# Numbered quick bookmarks (0-9): maps the top-row digit key codes to their
# slot number for the direct Alt+Shift+<digit> / Ctrl+Alt+Shift+<digit>
# interception in _on_char_hook.
_DIGIT_KEY_CODES: dict[int, int] = {ord(str(digit)): digit for digit in range(10)}


class MainFrame(
    AbbreviationsMixin,
    AiActionsMixin,
    EmojiPickerMixin,
    RadioMixin,
    PodcastsMixin,
    MediaSleepTimerMixin,
    FormatCodesMixin,
    SpeechCommandsMixin,
    SpeechDownloadsMixin,
    VoiceInteractionMixin,
    VerbosityCommandsMixin,
    LanguageDetectMixin,
    BrailleProofingCommandsMixin,
    BraillePhase2CommandsMixin,
    BrailleRepairMixin,
    BrailleCommandsMixin,
    HygieneMixin,
    SimpleOpenMixin,
    ImageCaptureMixin,
    BrowseModeMixin,
    MenuBuilderMixin,
    MenuBindingsMixin,
    NotebookUIMixin,
    QuillKeyMixin,
    RichModeMixin,
    SelectionMarksMixin,
    SessionsMixin,
    StatusBarMixin,
    IntellisensePopupMixin,
    LineCommandsMixin,
    ListStudioMixin,
    StoryStudioMixin,
    AdpMixin,
    GlobalHotkeysMixin,
    UnlockCodesMixin,
    VaultMixin,
    GitSyncMixin,
    LocalGitMixin,
    GlowFileMixin,
    DocConvertMixin,
    DictationHotkeysMixin,
    SectionMoveMixin,
    CopyTrayMixin,
    ClipLibraryMixin,
    ImageAltMixin,
    PrintMixin,
    WorkPersonaMixin,
    ProfilePickerMixin,
    SshEditingMixin,
    GitHubRemoteMixin,
    GitHubItemsMixin,
    GitHubAdminMixin,
    GitHubExtrasMixin,
    GhBridgeMixin,
    DevToolsMixin,
    PowerToolsActionsMixin,
    ClassicEditorMixin,
    PowerToolsMenuMixin,
    RevealCodesMixin,
    InlineNotesMixin,
    RestorePointsMixin,
    QuillinsMenuMixin,
    CommandRegistryMixin,
    UpdatesMixin,
    CompareMixin,
    SearchCommandsMixin,
    SpellcheckCommandsMixin,
    BwSpeechMixin,
    PublishingCommandsMixin,
    KeymapIoMixin,
    MenuEditorMixin,
    PreferencesMixin,
    ContextHelpMixin,
    WatchProfileDialogMixin,
    KeymapEditorMixin,
):
    _ANNOUNCEMENT_BACKEND_LABELS: dict[str, str] = {
        "auto": "Automatic (use Prism when available)",
        "prism": "Prism",
        "status_only": "Status Bar Only",
    }
    _STATUS_BAR_LABELS: dict[str, str] = {
        "message": "Status Message",
        "line_column": "Position",
        "page": "Page",
        "word_count": "Word Count",
        "char_count": "Character Count",
        "line_count": "Line Count",
        "reading_time": "Reading Time",
        "document_progress": "Document Progress",
        "mode": "Keyboard Mode",
        "tab_mode": "Tab Mode",
        "document_format": "Format",
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
        "braille": "Braille",
        "section_heading": "Section",
        "ai_engine": "AI Engine",
        "radio_player": "Radio",
        "podcast_player": "Podcasts",
    }
    _STATUS_BAR_WIDTHS: dict[str, int] = {
        "message": -1,
        "line_column": 140,
        "page": 220,
        "word_count": 140,
        "char_count": 140,
        "line_count": 130,
        "reading_time": 150,
        "document_progress": 150,
        "mode": 110,
        "tab_mode": 130,
        "document_format": 170,
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
        "braille": 320,
        "section_heading": 220,
        "ai_engine": 200,
        "radio_player": 260,
        "podcast_player": 280,
    }
    _STATUS_BAR_FEATURES: dict[str, str] = {
        "message": "core.app",
        "line_column": "core.editor",
        "page": "core.analysis",
        "word_count": "core.analysis",
        "char_count": "core.analysis",
        "line_count": "core.analysis",
        "reading_time": "core.analysis",
        "document_progress": "core.editor",
        "mode": "core.editor",
        "tab_mode": "core.editor",
        "document_format": "core.format",
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
        "braille": "core.braille",
        "section_heading": "core.format",
        "radio_player": "core.radio",
        "podcast_player": "core.podcasts",
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
        self._first_run_trust_consent_prompt = not safe_mode and not load_trust_consent_complete()
        # Cache the on-disk consent status so the re-consent dialog can branch
        # between first-install and "your prior consent is out of date" (#305).
        self._trust_consent_status = load_trust_consent_status()
        self.features = FeatureManager.load(persistent=not safe_mode)
        self.macros = MacroManager.load(persistent=not safe_mode)
        self.settings = load_settings()
        # Standalone dialogs announce Entered/Exited via dialog_contract directly,
        # bypassing the gated wrappers; register the live setting to cover them.
        from quill.ui.dialog_contract import set_transition_announcement_policy

        set_transition_announcement_policy(lambda: self.settings.announce_dialog_transitions)
        # Remote feature kill switch: load the locally-cached locked set so any
        # active safety advisory is honored immediately at startup, even offline.
        from quill.core.safety.feature_lock import load_feature_locks

        self._feature_locks = load_feature_locks()
        # The first run shows exactly one onboarding surface: the unified setup
        # wizard (run_startup_wizard), plus the trust-consent gate. The legacy
        # per-feature startup prompts (profile, AI, assistant, GLOW, speech,
        # watch folder) and the "Startup Wizard overview" are retired; every one
        # of those is reachable from its own menu/button. (#700)
        # #606: when the setup wizard will run on this launch, defer the
        # default "Untitled" document tab until the wizard returns. macOS
        # VoiceOver announces the focused window's tab name as soon as the
        # window is shown, so users were hearing "Untitled" before they
        # ever heard "Setup Wizard." The wizard opens on top of an empty
        # notebook now; a fresh untitled document is created automatically
        # after the wizard closes (see _maybe_run_first_run_onboarding).
        # The `getattr(..., True)` default matches the existing wizard
        # gate at line 23753 — if the setting key is missing for any
        # reason, treat the wizard as already complete.
        self._first_run_wizard_pending = not safe_mode and not getattr(
            self.settings, "setup_wizard_completed", True
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
        if not safe_mode:
            self._apply_recommended_keymap_updates()
        self.recent_files = [] if safe_mode else load_recent_files()
        if not safe_mode and getattr(self.settings, "recent_files_auto_clear_missing", False):
            # #14: drop entries whose file is gone, but only on confirmed fixed
            # internal drives (never removable/network), then persist the pruned
            # list so the menu and the on-disk history stay in sync.
            self.recent_files, _dropped = prune_missing_recent_files(
                self.recent_files, enabled=True
            )
            if _dropped:
                save_recent_files(self.recent_files)
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
        self._deletion_ring = DeletionRing()
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
        # Single unnamed, one-shot jump point (Leasey-style temp bookmark).
        # Deliberately session-only (aliased per-tab, never persisted to
        # DocumentMemory) -- it is disposable scratch state by design.
        self._temp_bookmark: int | None = None
        # Folded region state (accessible code folding). Session-only, aliased
        # per-tab like _bookmarks/_temp_bookmark.
        self._folded_regions: set[tuple[int, int]] = set()
        # Active document's inline notes (aliased to the active tab's list).
        self._inline_notes: list = []
        # Persistent, per-document bookmarks + last cursor position (#300 follow-up).
        # Forgiving load so a missing/corrupt store never blocks startup.
        try:
            self._doc_memory = DocumentMemory.load()
        except Exception:  # noqa: BLE001 - persistence is best-effort
            self._doc_memory = DocumentMemory()
        self._tray_icon: object | None = None
        self._is_exiting = False
        # #210: a committed close arms a daemon watchdog that force-exits if the
        # graceful wx shutdown wedges. Set only on real frames so __new__-built
        # test frames never arm a real os._exit.
        self._hard_exit_enabled = True
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
        self._webview_warm = False
        # Background task pool for offloading I/O out of UI-thread modal paths.
        # Used by _offer_crash_recovery (snapshot read + mkdir) and the deferred
        # startup task list.  Closed in run_app() shutdown.
        self._task_manager = TaskManager()
        self._compare_session: _CompareSession | None = None
        self._compare_ignore_trailing_spaces = True
        self._compare_ignore_line_endings = True
        self._empty_workspace_active = False
        self._announcement_engine = AnnouncementEngine(self.settings.announcement_backend)
        prewarm_tts_engine()
        self._announcement_error_reported = ""
        self._read_aloud = ReadAloudController()
        self._dictation = DictationController()
        # Built lazily on first lookup: constructing the online providers pulls
        # the urllib request stack and the lexical provider tree, none of which
        # an empty editor needs at startup. See _get_lexical_service().
        self._lexical_service: object | None = None
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
        self._overwrite_mode = False
        # When True, the Tab key inserts a literal tab character at the caret
        # (VS Code-style) instead of running the smart line-indent command.
        # Session state, mirroring _overwrite_mode; toggled with QUILL Key + U.
        self._tab_inserts_literal = False
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
        # Kill switch: block remotely-locked commands at the single dispatch
        # chokepoint, so keybindings and the palette obey uniformly.
        self.commands.set_run_gate(self._command_allowed_by_locks)
        # The repeat-count arming command must never multiply itself when a count
        # is already pending (it would otherwise prompt once per pending count).
        self.commands.register_non_repeatable("edit.repeat_command")
        # #235: surface the soft BRF save warning (non-NABCC chars saved as-is).
        from quill.io.text import set_save_warning_hook

        set_save_warning_hook(self._announce_brf_save_warning)
        self._recent_menu_ids: dict[int, Path] = {}
        self._recent_session_menu_ids: dict[int, Path] = {}
        self._session_menu_ids: dict[int, int] = {}
        self._window_doc_menu_ids: dict[int, int] = {}
        self._menu_open_depth = 0
        self._pending_menu_refresh = False
        # Lifecycle gate: True once __init__ has finished creating widgets
        # (notably self.editor). False during construction so menu refreshes
        # triggered from _build_menu() defer until the editor exists.
        self._ui_ready = False
        self._recent_sessions = [] if safe_mode else load_recent_sessions()

        # Title starts as "Quill" (not "Untitled - Quill") so screen readers
        # that see the Win32 HWND before Show() is called don't announce
        # "Untitled" combined with any transient status-bar text. _refresh_title()
        # sets the real document-name title as soon as the editor is ready.
        self.frame = wx.Frame(None, title="Quill", size=(1000, 700))
        # Radio/podcast player controllers parent themselves on self.frame, so
        # they must be built after the frame exists (AttributeError otherwise).
        self._init_radio()
        self._init_podcasts()
        self._init_media_sleep_timer()
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
        # True only between the F6 landing into the status bar and the first
        # cell-focus announcement, so "Status bar" is spoken once on entry and
        # never again on intra-bar arrow navigation (see _on_statusbar_cell_focus).
        self._statusbar_entry_pending = False
        # EdSharp port: per-document arming flag for numbered-list auto-fill.
        # Set to time.monotonic() + _LIST_AUTO_FILL_ARM_SECONDS the first time
        # the user toggles a numbered list on the active document; cleared on
        # document close.  The flag means the three-way auto-fill gate in
        # should_auto_fill_numbers() returns True even when the surface is
        # not markdown and the setting is off.
        self._numbered_list_armed_until = 0.0
        self._documents_sizer.Add(self.notebook, 1, wx.EXPAND)
        self._entries_panel = NotebookEntriesPanel(self._main_splitter, wx)
        self._entries_panel.panel.Bind(wx.EVT_SET_FOCUS, self._on_container_focus)
        self._apply_silent_accessible(self._entries_panel.panel)
        self._main_splitter.Initialize(self._documents_panel)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self._main_splitter, 1, wx.EXPAND)
        # Reveal Codes pane: docked below the editor, above the status bar
        # (WordPerfect arrangement), hidden by default and shown via Alt+F3.
        from quill.ui.reveal_codes_pane import RevealCodesPane

        self._reveal_pane = RevealCodesPane(wx, self.frame, self)
        self._reveal_pane.panel.SetMinSize((-1, 160))
        self._reveal_last_state: tuple[int, int, int] | None = None
        layout.Add(self._reveal_pane.panel, 0, wx.EXPAND)
        self._reveal_pane.panel.Show(bool(getattr(self.settings, "reveal_codes_visible", False)))
        self.statusbar = wx.Panel(self.frame)
        self.statusbar.SetName("Status bar")
        self.statusbar.Bind(wx.EVT_SET_FOCUS, self._on_container_focus)
        self._apply_silent_accessible(self.statusbar)
        self._statusbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.statusbar.SetSizer(self._statusbar_sizer)
        layout.Add(self.statusbar, 0, wx.EXPAND)
        self.frame.SetSizer(layout)
        if not self._first_run_wizard_pending:
            # #606: skip the default tab when the wizard is about to run,
            # so the wizard modal opens on an empty notebook rather than
            # on top of an "Untitled" tab. _maybe_run_first_run_onboarding
            # creates the tab via new_document() after the wizard
            # returns, then re-runs the editor-dependent init steps
            # (location ring + region tracker) that this branch skips.
            self._create_document_tab(self.document, select=True)
            self._location_ring.record(0)
            self._region_tracker.enter("Editor")
        self._apply_theme(self.settings.theme)

        self._build_commands()
        self._build_menu()
        self._note_active_feature_locks()
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
            ready_tip = "Ready. Tip: press Ctrl+Shift+P for Command Palette."
            if self.settings.announcement_startup_tips_enabled:
                self._set_status(ready_tip)
            else:
                self._set_status_quiet(ready_tip)
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
            try:
                from quill.core.ai import harness_credentials

                # Bridges a key saved in an earlier session to the SDK's env-var
                # auth before anything asks whether that harness is available.
                harness_credentials.apply_all_stored_keys()
            except Exception:
                self._report_startup_task_failure("AI harness credential apply")
        # Construction is complete. Subsequent _refresh_contextual_menu_items
        # calls can read self.editor, self.notebook, etc. safely. Any refreshes
        # deferred from inside _build_menu() (e.g. when the first-run wizard
        # had not yet created the default tab) are flushed now so contextual
        # menu items reflect the active document.
        self._ui_ready = True
        self._flush_pending_menu_refresh()

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

    def _load_quillins_and_refresh_menu(self) -> None:
        """Load enabled Quillins, then rebuild the menu bar (#974).

        H-SAFE-1: mirrors the safe_mode gate that used to live in
        _register_quillins_commands -- Safe Mode keeps the manager/wizard
        commands (registered synchronously in __init__) but never loads
        contributed commands/providers.

        _build_menu() runs synchronously in __init__, before this deferred
        step (Quillin loading is deferred here for startup-speed and crash
        isolation -- see _run_deferred_startup_tasks). Without the rebuild,
        every Quillin-contributed menu item -- including the bundled
        insert-tools items behind Insert > Date and Time -- is silently
        absent for the rest of the session: the submenu itself still shows
        (it is created unconditionally), but with zero items inside it,
        so pressing Right Arrow on it has nothing to open and instead moves
        to the next top-level menu.
        """
        if self._safe_mode:
            return
        self._register_quillin_contributions()
        self._build_menu()

    def _run_deferred_startup_tasks(self) -> None:
        # Always capture startup timing so logs/startup_tasks.txt is fresh after
        # every launch (a field bug report can include it with no env var).
        _profile = True
        _times: list[tuple[str, float]] = []

        try:
            self._start_ipc_poll()
        except Exception:
            self._report_startup_task_failure("IPC poll")
        # detect_screen_reader() enumerates processes via the Windows API (no
        # subprocess). It is fast, but kept on a daemon thread so even a slow
        # snapshot can never block the UI; the result posts via wx.CallAfter.
        _t = time.perf_counter()
        _safe_mode_snap = self._safe_mode

        def _sr_detect_worker() -> None:
            t_worker = time.perf_counter()
            try:
                detection = detect_screen_reader()
                if detection.detected:
                    message = f"Detected screen reader: {detection.name}. Adaptive hints enabled."
                    if getattr(self.settings, "announce_screen_reader_detected", False) and getattr(
                        self.settings, "verbosity_speech_enabled", True
                    ):
                        self._wx.CallAfter(self._set_status, message)
                    else:
                        self._wx.CallAfter(self._set_status_quiet, message)
                # No-SR path: "Ready" was already announced in __init__; suppress the repeat.
                if _profile:
                    self._wx.CallAfter(
                        _times.append,
                        ("screen-reader detection (bg)", time.perf_counter() - t_worker),
                    )
            except Exception:
                # Nothing this one-shot probe does may ever escape the thread:
                # an unhandled exception here (e.g. a test double standing in
                # for wx without CallAfter, outliving its test) surfaces as an
                # async error in whatever code happens to be running later.
                pass

        import threading

        threading.Thread(  # GATE-40-OK: one-shot screen-reader probe; posts result via CallAfter.
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
            # H-SAFE-1: mirrors the safe_mode gate that used to live in
            # _register_quillins_commands -- Safe Mode keeps the manager/wizard
            # commands (registered synchronously in __init__) but never loads
            # contributed commands/providers.
            (
                "quillin contributions",
                self._load_quillins_and_refresh_menu,
            ),
            ("crash recovery", self._offer_crash_recovery),
            ("first-run onboarding", self._maybe_run_first_run_onboarding),
            ("migration notice", self._surface_migration_notice),
            ("braille pack prompt", self._maybe_prompt_braille_pack_install),
            ("kokoro package prompt", self._maybe_prompt_kokoro_package_install),
            ("startup profile prompt", self.run_startup_profile_prompt),
            ("watch-folder startup", self._maybe_start_watch_folder),
            # Apply the saved spell-check language before the cache warms so the
            # first F7 validates against it (downloaded dicts via Tools > Spelling).
            (
                "spell-check language",
                lambda: spellcheck_set_active_language(
                    getattr(self.settings, "spellcheck_language", "en_US")
                ),
            ),
            ("lexical cache warm-up", start_lexical_preload),
            # §179: F1 / Shift+F1 sync-decodes ``topics.json`` the first time it
            # is pressed. On a cold machine this can take a few hundred ms and
            # trip the wx heartbeat watchdog. warm_help_topics is lock-protected
            # and thread-safe, so warm it off the UI thread via the task manager
            # (kwargs absorbed) rather than blocking the deferred-startup sequence.
            (
                "help topics warm-up",
                lambda: self._task_manager.submit("help-warm", lambda **_kw: warm_help_topics()),
            ),
            # §8.2 TTS-FALLBACK-ANNOUNCE: show status prompt when TTS init failed.
            ("TTS fallback check", self._check_tts_fallback_on_startup),
            # Build the model-lifecycle manager from settings and start the idle
            # sweep, so the Performance settings (Low-resource mode, Unload idle
            # models after) actually take effect on the speech/TTS/LLM engines.
            ("model lifecycle", self._start_model_lifecycle),
        ):
            _t = time.perf_counter() if _profile else 0.0
            try:
                task()
            except Exception:
                self._report_startup_task_failure(label)
            if _profile:
                _times.append((label, time.perf_counter() - _t))
        # WebView2 warm-up runs LAST, on its own delayed CallLater — not inline.
        # The first ``wx.html2.WebView.New()`` initialises the Edge WebView2
        # process and can block the UI thread for several seconds (sometimes
        # minutes) on slower or first-run Windows installs (#174/#177). Running it
        # inline at the *front* of this list meant that block landed while the
        # user was waiting to interact — dead air a screen-reader user reads as a
        # frozen app (the wx heartbeat watchdog logged ~7 s stalls). Deferring it
        # to after the editor is focused and "Ready" is announced, on a short
        # delay, lets the user start working first; F6/preview before it finishes
        # is already handled by the ``_webview_warm`` deferral in preview_in_app.
        # Isolated like every other deferred step: a failure scheduling the
        # warm-up must never take down startup (the DLG-3 Phase 5 contract).
        try:
            self._wx.CallLater(1200, self._prewarm_webview_runtime)
        except Exception:
            self._report_startup_task_failure("webview warm-up scheduling")
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

        cold_times: list[tuple[str, float]] = getattr(self, "_cold_start_times", None) or []
        all_times = [*cold_times, *times]
        total = sum(e for _, e in all_times)
        lines = [f"Startup task timing  (total {total * 1000:.0f} ms)\n", "=" * 50 + "\n"]
        for label, elapsed in all_times:
            pct = elapsed / total * 100 if total > 0 else 0
            lines.append(f"  {label:<45} {elapsed * 1000:7.1f} ms  ({pct:.0f}%)\n")
        out = app_data_dir() / "logs" / "startup_tasks.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(lines), encoding="utf-8")
        import logging as _logging

        _logging.getLogger(__name__).debug("startup task timing -> %s", out)

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
        # Cmd+F4 close-document accelerator is a Windows convention; on macOS it
        # becomes Cmd+F4 (not idiomatic) and Cmd+W already closes documents. Gate
        # it to non-darwin so the Mac build doesn't get a redundant chord.
        if sys.platform != "darwin":
            entries.append(wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_F4, self._id_close_document))

        self.frame.SetAcceleratorTable(wx.AcceleratorTable(entries))

    # Global hotkeys (registration/dispatch/dialogs) live in GlobalHotkeysMixin
    # (main_frame_hotkeys.py): a user-configurable, allowlist-bounded table
    # that generalized the original single sticky-note RegisterHotKey.

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
            elif lowered in ("cmd", "command"):
                # "Cmd" is how DEFAULT_KEYMAP spells the macOS-only bindings
                # (navigate.back_location/forward_location, and
                # window.next_document/previous_document — see keymap.py).
                # wx has no separate ACCEL_CMD flag: wx.ACCEL_CTRL is what
                # already maps to the Command key in a wx.AcceleratorTable on
                # macOS, so "Cmd" parses to the same flag as "Ctrl". Without
                # this, a "Cmd+..." binding fell through to the "else: return
                # None" branch below and silently never got an accelerator
                # table entry at all on any platform.
                flags |= wx.ACCEL_CTRL
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
        # #920: bind the OS session-end events to the clean-exit marker handler
        # so a Windows shutdown/restart/logoff (which can end the process without
        # the EVT_CLOSE path running) is recorded as a clean exit, not a crash.
        # Guarded by getattr: not every wx build exposes these session events.
        for _session_evt in (
            getattr(wx, "EVT_QUERY_END_SESSION", None),
            getattr(wx, "EVT_END_SESSION", None),
        ):
            if _session_evt is not None:
                self.frame.Bind(_session_evt, self._on_session_end)
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
        #
        # #956: this handler runs inside wx's native event dispatch, so any
        # exception that escapes it (macOS raised a wxArrayString
        # "nIndex < m_nCount" C++ assertion here mid-Notebook-creation, while
        # dialogs were tearing down and re-activating the frame) surfaces as
        # "SystemError: ActivateEvent returned a result with an exception set"
        # and crashes the app. Frame activation is a convenience, never worth
        # the process: contain everything, best-effort.
        try:
            active = getattr(event, "GetActive", lambda: True)()
            if active:
                self._wx.CallAfter(self._return_focus_to_editor)
        except Exception:  # noqa: BLE001 - activation must never crash (#956)
            pass
        skip = getattr(event, "Skip", None)
        if callable(skip):
            try:
                skip()
            except Exception:  # noqa: BLE001 - see above (#956)
                pass

    def _apply_silent_accessible(self, widget: object) -> None:
        """Replace a layout container's built-in accessible so screen readers
        skip it in the ancestor context chain (#170)."""
        # #616: the silent-accessible shim is an MSAA (Windows) workaround
        # that returns ROLE_SYSTEM_WINDOW with an empty name. On macOS the
        # screen reader (VoiceOver) walks the NSAccessibility tree, and
        # installing a wx.Accessible subclass here would replace the
        # native NSView's role with a generic one, so VoiceOver no longer
        # sees the nested NSTextView as a real text area. macOS uses the
        # native tree as-is; the shim is a no-op there.
        if sys.platform == "darwin":
            return
        cls = self._silent_layout_cls
        if cls is not None:
            try:
                widget.SetAccessible(cls(widget))  # type: ignore[attr-defined]
            except Exception:
                pass

    def _pin_macos_editor_accessibility_role(self, editor: object) -> None:
        """#616: pin the editor's NSAccessibility role/label for VoiceOver.

        The original inline version called ``setAccessibilityRole_`` on the
        bare int from ``GetHandle()`` (and imported a misnamed AppKit
        constant), so it silently did nothing. The shared helper wraps the
        handle via PyObjC first — see accessible_names.pin_macos_text_area_role.
        """
        pin_macos_text_area_role(editor, "Document")

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
            try:
                editor.SetFocus()
            except RuntimeError:
                # The tab (and its C++ editor) can be torn down between the
                # CallAfter that queued us and now — e.g. mid-Notebook
                # creation, the #956 crash window. Focus is a nicety; skip.
                return

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
        editor.Bind(wx.EVT_TEXT_COPY, self._on_editor_text_copy)

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
        # Rich mode: the native RichEdit handles Ctrl+B/I/U itself, silently.
        # Route them through QUILL's commands instead so formatting is
        # announced, dirty-marked, and remappable — one command id everywhere.
        if (
            self._current_editor_mode() == "rich"
            and event.ControlDown()
            and not event.AltDown()
            and not event.ShiftDown()
        ):
            rich_keys = {
                ord("B"): self.format_bold,
                ord("I"): self.format_italic,
                ord("U"): self.format_underline,
            }
            handler = rich_keys.get(event.GetKeyCode())
            if handler is not None:
                handler()
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
        # #616: TE_RICH2 and TE_NOHIDESEL are Windows-specific. On Windows,
        # TE_RICH2 forces a RichEdit control whose IAccessible value is
        # reported correctly to screen readers (see the comment near the
        # preview Ctrl at line ~5890 for the original justification). On
        # macOS both flags are ignored by wx, but wx's macOS accessibility
        # shim can still install a generic role on the editor's NSView.
        # Drop the Windows-only flags on macOS and let wx map TE_MULTILINE
        # to the native NSTextView, then pin the AX role so VoiceOver
        # treats the editor as a real text area rather than a generic
        # group.
        if sys.platform == "darwin":
            # The same multiline wx.TextCtrl macOS always used (an NSTextView
            # underneath; wx.TE_MULTILINE alone so VoiceOver keeps the native
            # text-area mapping), built through the QuillMacRichText factory so
            # rich mode works on the Mac too when PyObjC is present. Absent
            # PyObjC — the soft 'mac' extra — the wrapper reports unavailable
            # and .rtf stays on converted rich; the control is identical.
            from quill.ui.nstextview_rtf_surface import create_nstextview_rtf

            editor = create_nstextview_rtf(wx, splitter, wx.TE_MULTILINE)
        else:
            # QuillRichEdit is THE editor surface (Windows/Linux): the same
            # native RichEdit (RICHEDIT50W) QUILL always shipped, wrapped for
            # native RTF via the TOM, with the braille fix applied per the two
            # Braille-tab checkboxes. The fix is two cooperating pieces, both on
            # by default: SES_EMULATESYSEDIT (text from cell 1, selection dots
            # 7-8 — #616/#813) and the hidden border (a visible border itself
            # pushes braille output out of cell 1). create_richedit_rtf falls
            # back to a plain wx.TextCtrl on any failure, so the editor can
            # never fail to build.
            from quill.ui.richedit_rtf_surface import create_richedit_rtf

            border = (
                wx.BORDER_NONE if getattr(self.settings, "braille_editor_hide_border", True) else 0
            )
            emulate = bool(getattr(self.settings, "braille_editor_system_edit_fix", True))
            editor = create_richedit_rtf(
                wx, splitter, wx.TE_MULTILINE | border, emulate_system_edit=emulate
            )
        editor.SetName("Document")
        if sys.platform == "darwin":
            self._pin_macos_editor_accessibility_role(editor)
        splitter.Initialize(editor)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.EXPAND)
        panel.SetSizer(sizer)
        if document.text:
            editor.ChangeValue(document.text)
        self._bind_editor_events(editor)
        tab = _DocumentTab(panel=panel, editor=editor, document=document, splitter=splitter)
        tab.source_label = str(document.source_metadata.get("source_label", "")).strip()
        # Load this document's saved bookmarks and restore its last cursor position.
        self._restore_document_memory(tab)
        # Load this document's saved inline notes.
        self._load_inline_notes_for(tab)
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
        panel = self._documents_panel
        simplebook = None if show_tab_control else getattr(wx, "Simplebook", None)
        host = simplebook(panel) if simplebook else wx.Notebook(panel)
        host.SetName("Open documents")  # SR announces the document tab group, not a bare notebook
        return host

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
            # #11: no side preview to close -> close the active document. The hook
            # consumes Ctrl+W here, so without this fallback the accelerator never
            # fires and Ctrl+W appears to do nothing. Guarded to the document
            # surface so it doesn't hijack Ctrl+W inside a modal/WebView dialog.
            if tab is not None and self._focus_is_in_document_surface():
                self.close_current_document()
                return
        # Numbered quick bookmarks (0-9): direct chords rather than a Quick Nav
        # sub-mode, so set/jump is always a single keystroke with no modal step.
        # The declarative keymap table has no "any digit" wildcard, so these 20
        # chords are intercepted here instead, mirroring the Ctrl+K/Ctrl+W
        # frame-level handling immediately above.
        if key_code in _DIGIT_KEY_CODES and self._focus_is_in_document_surface():
            slot = _DIGIT_KEY_CODES[key_code]
            if event.AltDown() and event.ShiftDown() and not event.ControlDown():
                self.set_quick_bookmark(slot)
                return
            if event.ControlDown() and event.AltDown() and event.ShiftDown():
                self.go_to_quick_bookmark(slot)
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
        notebook = getattr(self, "notebook", None)
        editor = getattr(self, "editor", None)
        node = focus
        while node is not None:
            if node is document_surface or node is notebook or node is editor:
                return True
            get_parent = getattr(node, "GetParent", None)
            node = get_parent() if callable(get_parent) else None
        return False

    def _activate_tab(self, index: int) -> None:
        if index < 0 or index >= len(self._document_tabs):
            return
        # Remember where the cursor was in the document we are leaving, so it is
        # restored next time that file is opened (last-position memory).
        self._remember_active_caret()
        self._stop_external_change_watcher()
        tab = self._document_tabs[index]
        self._active_tab_index = index
        self._browse_navigation_cache = None
        self.editor = tab.editor
        self.document = tab.document
        # The active document's bookmark set is this tab's own dict (per-document).
        self._bookmarks = getattr(tab, "bookmarks", {})
        # The active document's temp bookmark is this tab's own value (session-only).
        self._temp_bookmark = getattr(tab, "temp_bookmark", None)
        # The active document's folded regions are this tab's own set (session-only).
        self._folded_regions = getattr(tab, "folded_regions", set())
        # The active document's inline notes are this tab's own list (per-document).
        self._inline_notes = getattr(tab, "inline_notes", [])
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
        doc_path = self.document.path
        self._fire_quillin_event(
            "document.activated",
            {
                "file_path": str(doc_path) if doc_path is not None else "",
                "extension": doc_path.suffix.lower() if doc_path is not None else "",
                "title": self.document.name,
            },
        )

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
        self._refresh_intellisense_popup()
        self._refresh_side_preview()
        self._refresh_browser_preview()
        self._maybe_autosave()
        self._refresh_title()
        self._refresh_contextual_menu_items()
        # #181: debounced auto language detection (no-op unless enabled in Settings).
        self._schedule_language_detection()
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
        try:
            rendered = self._render_snippet_with_prompts(snippet)
        except ValueError as exc:
            self._set_status(f'Snippet "{snippet.name}" has an invalid placeholder: {exc}')
            return False
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
        self._fire_quillin_event("smart_trigger.entered", {"trigger": snippet.trigger})
        return True

    def _on_editor_caret_activity(self, event: object) -> None:
        self._refresh_statusbar()
        try:
            self._maybe_announce_indent()
            self._maybe_play_indent_tone()
            self._maybe_announce_format_transition()
        except RuntimeError:  # #603/#269: editor can be a dead TextCtrl mid-event.
            pass
        event.Skip()

    def _on_editor_key_up(self, event: object) -> None:
        wx = self._wx
        if self._dictation_handle_key_up(event):
            return
        if event.GetKeyCode() == wx.WXK_INSERT:
            self._insert_key_down = False
        self._on_editor_caret_activity(event)

    def _on_editor_key_down(self, event: object) -> None:
        wx = self._wx
        if self._dictation_handle_key_down(event):
            return
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
        # Shift+F10 and the dedicated Menu/Apps key both request the context
        # menu from the keyboard.  wx may not synthesise EVT_CONTEXT_MENU for
        # these keys inside a TextCtrl, so intercept them here and invoke the
        # handler directly with a fake event that positions the menu at the
        # caret (DefaultPosition → wx pops it up near the caret automatically).
        _f10 = getattr(wx, "WXK_F10", None)
        _menu_key = getattr(wx, "WXK_WINDOWS_MENU", getattr(wx, "WXK_MENU", None))
        _kc = event.GetKeyCode()
        if (
            _f10 is not None
            and _kc == _f10
            and event.ShiftDown()
            and not event.ControlDown()
            and not event.AltDown()
        ) or (_menu_key is not None and _kc == _menu_key):

            class _KeyboardContextEvent:  # noqa: N801
                def GetPosition(self_inner):  # noqa: N805
                    return wx.DefaultPosition

            self._on_editor_context_menu(_KeyboardContextEvent())
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
            if self._handle_smart_trigger_return():
                return
            if self._handle_markdown_list_return():
                return
        tab_key = getattr(wx, "WXK_TAB", None)
        if tab_key is not None and event.GetKeyCode() == tab_key:
            self._commit_pending_extend_selection()
            # Literal-tab mode (QUILL Key + U): forward Tab as a tab character at
            # the caret instead of running the smart indent. Shift+Tab still
            # outdents so a stray indent can be undone without leaving the mode.
            if self._tab_inserts_literal and not event.ShiftDown():
                self.editor.WriteText("\t")
                return
            # force_announce so the Tab indent is spoken even under JAWS/NVDA —
            # the edit has no focus change for the screen reader to pick up.
            if self._is_caret_on_markdown_list_item():
                if event.ShiftDown():
                    self.format_outdent(status="Promoted list item", force_announce=True)
                else:
                    self.format_indent(status="Nested list item", force_announce=True)
                return
            # Speak the new indent depth ("4 spaces" / "1 tab") rather than the
            # terse "Indented lines" when announce_indent_depth is on (default).
            # _set_status both shows and speaks, so it stays a single announcement.
            announce_depth = bool(getattr(self.settings, "announce_indent_depth", True))
            if event.ShiftDown():
                self.format_outdent(force_announce=not announce_depth)
            else:
                self.format_indent(force_announce=not announce_depth)
            if announce_depth:
                self._set_status(self._current_line_indent_phrase())
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

    def _handle_smart_trigger_return(self) -> bool:
        """Fire a Quillin ``=name(args)`` smart trigger on the current line.

        Returns True when a trigger fired so the caller consumes the Enter and
        skips list continuation. Dispatch/enablement lives in the Quillins mixin;
        this only supplies the current line span and re-syncs the model.
        """
        dispatch = getattr(self, "dispatch_smart_trigger_line", None)
        if dispatch is None:
            return False
        start, end = self.editor.GetSelection()
        if start != end:
            return False
        text = self.editor.GetValue()
        line_start, line_end = line_span(text, self.editor.GetInsertionPoint())
        line = text[line_start:line_end]
        if "=" not in line:  # cheap reject before parsing
            return False
        if not dispatch(line, line_start, line_end):
            return False
        self.document.set_text(self.editor.GetValue())
        return True

    def _handle_markdown_list_return(self) -> bool:
        if self._effective_markup_kind() not in {"markdown", "plain"}:
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
        if self._effective_markup_kind() not in {"markdown", "plain"}:
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
        # macOS text semantics (#7/#8): Option (Alt) is the word-movement
        # modifier and Cmd (wx ControlDown on darwin) is the line/document
        # bounds modifier. Windows uses Ctrl for both. Branching here keeps
        # the extend-selection caret movement matching native Mac muscle memory
        # instead of using Cmd for word movement.
        is_darwin = sys.platform == "darwin"
        word_mod = event.AltDown() if is_darwin else event.ControlDown()
        cmd_down = event.ControlDown()  # Cmd on darwin, Ctrl on Windows
        if cmd_down and key_code == wx.WXK_HOME:
            target = 0
        elif cmd_down and key_code == wx.WXK_END:
            target = len(text)
        elif word_mod and key_code == wx.WXK_LEFT:
            return move_word(reverse=True)
        elif word_mod and key_code == wx.WXK_RIGHT:
            return move_word(reverse=False)
        elif is_darwin and cmd_down and key_code == wx.WXK_LEFT:
            # Cmd+Left -> start of line (macOS HIG line-bound movement).
            target = line_starts[line_index_for_position(caret)]
        elif is_darwin and cmd_down and key_code == wx.WXK_RIGHT:
            # Cmd+Right -> end of line (macOS HIG line-bound movement).
            target = line_limit(line_index_for_position(caret))
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

    def _get_lexical_service(self) -> object:
        """The lexical (dictionary/thesaurus) service, built on first use.

        Deferred out of ``__init__`` so the online providers and their urllib
        request stack stay off the cold-start path; the first Look Up builds
        the service once and caches it.
        """
        if self._lexical_service is None:
            from quill.core.lexical import default_service

            self._lexical_service = default_service(include_online=True)
        return self._lexical_service

    def show_lookup_dialog(self, word: str) -> None:
        """Show the DICT-2 Look Up dialog for ``word``."""
        wx = self._wx
        if not self._feature_enabled("core.dictionary"):
            self._set_status("Dictionary feature is disabled.")
            return

        from quill.core.lexical import build_lookup_items, render_lookup

        # Query the lexical service (consent is per-feature, so online is enabled
        # if the user has consented to network lookups).
        online = self._feature_enabled("core.dictionary")
        result = self._get_lexical_service().lookup(word, online=online)

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
        set_accessible_name(text_ctrl, f"Look up result for {word}")
        text_ctrl.SetMinSize((500, 300))
        sizer.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 8)

        # List of insertable items.
        if items:
            list_label = wx.StaticText(dialog, label="Select a word to insert:")
            sizer.Add(list_label, 0, wx.LEFT | wx.RIGHT, 8)
            list_box = wx.ListBox(dialog, choices=[item.label for item in items])
            set_accessible_name(list_box, "Select a word to insert")
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
            # No external change. force-speak the result -- nothing moves focus,
            # so the plain status would be silent under a screen reader (#13).
            self._announce_result(f"'{self.document.path.name}' matches the on-disk version.")
        elif decision.action == ReloadAction.RELOAD:
            # Force-prompt even though auto_reload_when_clean would normally reload silently.
            self._show_external_change_prompt(ReloadAction.PROMPT_CONFLICT)
        else:
            self._announce(decision.announcement)
            self._show_external_change_prompt(decision.action)

    def _on_editor_context_menu(self, event: object) -> None:
        wx = self._wx
        menu = wx.Menu()
        features = self.features
        fmt_on = features.is_enabled("core.format")
        glow_on = self._feature_enabled("core.glow")
        spell_on = features.is_enabled("core.spellcheck")
        dict_on = features.is_enabled("core.dictionary")

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

        # --- Basic editing (always available). ---
        undo_id = wx.NewIdRef()
        redo_id = wx.NewIdRef()
        cut_id = wx.NewIdRef()
        copy_id = wx.NewIdRef()
        copy_source_id = wx.NewIdRef()
        paste_id = wx.NewIdRef()
        select_all_id = wx.NewIdRef()
        select_line_id = wx.NewIdRef()
        select_chunk_id = wx.NewIdRef()

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
        menu.Append(select_all_id, "Select All")
        menu.Append(select_line_id, "Select Line")
        menu.Append(select_chunk_id, self._menu_label("Select Chunk", "edit.select_chunk"))

        if not has_selection:
            cut_item.Enable(False)
            copy_item.Enable(False)
            copy_source_item.Enable(False)

        # --- Transform and line submenus (core.format). ---
        if fmt_on:
            transform_menu = wx.Menu()
            upper_id = wx.NewIdRef()
            lower_id = wx.NewIdRef()
            title_id = wx.NewIdRef()
            sentence_id = wx.NewIdRef()
            toggle_case_id = wx.NewIdRef()
            sort_asc_id = wx.NewIdRef()
            sort_desc_id = wx.NewIdRef()
            quote_id = wx.NewIdRef()
            unquote_id = wx.NewIdRef()
            dup_sel_id = wx.NewIdRef()
            transform_menu.Append(upper_id, "UPPER CASE")
            transform_menu.Append(lower_id, "lower case")
            transform_menu.Append(title_id, "Title Case")
            transform_menu.Append(sentence_id, "Sentence case")
            transform_menu.Append(toggle_case_id, "Toggle Case")
            transform_menu.AppendSeparator()
            transform_menu.Append(sort_asc_id, "Sort Lines Ascending")
            transform_menu.Append(sort_desc_id, "Sort Lines Descending")
            transform_menu.AppendSeparator()
            transform_menu.Append(quote_id, self._menu_label("Quote Lines", "edit.quote_lines"))
            transform_menu.Append(
                unquote_id, self._menu_label("Unquote Lines", "edit.unquote_lines")
            )
            transform_menu.AppendSeparator()
            transform_menu.Append(
                dup_sel_id, self._menu_label("Duplicate Selection", "edit.duplicate_selection")
            )
            transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_upper_case(), id=upper_id)
            transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_lower_case(), id=lower_id)
            transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_title_case(), id=title_id)
            transform_menu.Bind(wx.EVT_MENU, lambda _e: self.format_sentence_case(), id=sentence_id)
            transform_menu.Bind(
                wx.EVT_MENU, lambda _e: self.format_toggle_case(), id=toggle_case_id
            )
            transform_menu.Bind(wx.EVT_MENU, lambda _e: self.sort_lines_ascending(), id=sort_asc_id)
            transform_menu.Bind(
                wx.EVT_MENU, lambda _e: self.sort_lines_descending(), id=sort_desc_id
            )
            transform_menu.Bind(wx.EVT_MENU, lambda _e: self.quote_lines(), id=quote_id)
            transform_menu.Bind(wx.EVT_MENU, lambda _e: self.unquote_lines(), id=unquote_id)
            transform_menu.Bind(wx.EVT_MENU, lambda _e: self.duplicate_selection(), id=dup_sel_id)
            menu.AppendSubMenu(transform_menu, "Change &Case")

            line_menu = wx.Menu()
            dup_id = wx.NewIdRef()
            del_id = wx.NewIdRef()
            move_up_id = wx.NewIdRef()
            move_down_id = wx.NewIdRef()
            join_id = wx.NewIdRef()
            # PR1 (EdSharp port): section-move entries.
            move_section_up_id = wx.NewIdRef()
            move_section_down_id = wx.NewIdRef()
            line_menu.Append(dup_id, self._menu_label("Duplicate Line", "edit.duplicate_line"))
            line_menu.Append(del_id, self._menu_label("Delete Line", "edit.delete_line"))
            line_menu.Append(move_up_id, self._menu_label("Move Line Up", "edit.move_line_up"))
            line_menu.Append(
                move_down_id, self._menu_label("Move Line Down", "edit.move_line_down")
            )
            line_menu.Append(join_id, "Join With Next Line")
            line_menu.Append(
                move_section_up_id,
                self._menu_label("Move Section Up", "format.move_section_up"),
            )
            line_menu.Append(
                move_section_down_id,
                self._menu_label("Move Section Down", "format.move_section_down"),
            )
            line_menu.Bind(wx.EVT_MENU, lambda _e: self.duplicate_line(), id=dup_id)
            line_menu.Bind(wx.EVT_MENU, lambda _e: self.delete_line(), id=del_id)
            line_menu.Bind(wx.EVT_MENU, lambda _e: self.move_line_up(), id=move_up_id)
            line_menu.Bind(wx.EVT_MENU, lambda _e: self.move_line_down(), id=move_down_id)
            line_menu.Bind(wx.EVT_MENU, lambda _e: self.join_lines(), id=join_id)
            line_menu.Bind(wx.EVT_MENU, lambda _e: self.move_section_up(), id=move_section_up_id)
            line_menu.Bind(
                wx.EVT_MENU, lambda _e: self.move_section_down(), id=move_section_down_id
            )
            menu.AppendSubMenu(line_menu, "Line")

        # --- GLOW submenu (core.glow). ---
        if glow_on:
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
                wx.EVT_MENU, lambda _e: self.glow_audit_document(), id=glow_audit_document_id
            )
            glow_menu.Bind(
                wx.EVT_MENU, lambda _e: self.glow_audit_selection(), id=glow_audit_selection_id
            )
            glow_menu.Bind(
                wx.EVT_MENU, lambda _e: self.glow_fix_document(), id=glow_fix_document_id
            )
            glow_menu.Bind(
                wx.EVT_MENU, lambda _e: self.glow_fix_selection(), id=glow_fix_selection_id
            )
            glow_audit_file_id = wx.NewIdRef()
            glow_fix_file_id = wx.NewIdRef()
            glow_menu.AppendSeparator()
            glow_menu.Append(glow_audit_file_id, "GLOW Audit File...")
            glow_menu.Append(glow_fix_file_id, "GLOW Fix File...")
            glow_menu.Bind(wx.EVT_MENU, lambda _e: self.glow_audit_file(), id=glow_audit_file_id)
            glow_menu.Bind(wx.EVT_MENU, lambda _e: self.glow_fix_file(), id=glow_fix_file_id)
            menu.AppendSubMenu(glow_menu, "GLOW")

        menu.AppendSeparator()

        # --- Spell check (core.spellcheck): navigation + dialog + suggestions. ---
        if spell_on:
            spell_id = wx.NewIdRef()
            next_spell_id = wx.NewIdRef()
            prev_spell_id = wx.NewIdRef()
            menu.Append(spell_id, self._menu_label("Spell Check...", "tools.spell_check_dialog"))
            menu.Append(
                next_spell_id,
                self._menu_label("Next Misspelling\tCtrl+F7", "tools.next_misspelling"),
            )
            menu.Append(
                prev_spell_id,
                self._menu_label(
                    "Previous Misspelling\tCtrl+Shift+F7", "tools.previous_misspelling"
                ),
            )
            menu.Bind(wx.EVT_MENU, lambda _e: self.open_spell_check_dialog(), id=spell_id)
            menu.Bind(wx.EVT_MENU, lambda _e: self.next_misspelling(), id=next_spell_id)
            menu.Bind(wx.EVT_MENU, lambda _e: self.previous_misspelling(), id=prev_spell_id)

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

                        spelling_menu.Bind(wx.EVT_MENU, _apply_replacement, id=item_id)
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

        # --- Thesaurus (core.dictionary). ---
        if dict_on and thesaurus_engine.is_available():
            thes_id = wx.NewIdRef()
            menu.Append(thes_id, "Look Up in Thesaurus")
            menu.Bind(wx.EVT_MENU, lambda _e: self.show_thesaurus(), id=thes_id)

        # --- Navigation (always available). ---
        menu.AppendSeparator()
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
        menu.Bind(wx.EVT_MENU, lambda _e: self.go_to_line(), id=go_line_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.set_bookmark(), id=bookmark_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_palette(), id=palette_id)
        self._popup_context_menu(self.editor, menu, event)

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

    def _open_with_default_app(self, path: Path) -> None:
        import subprocess

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])  # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", str(path)])  # noqa: S603,S607
        except OSError as error:
            self._set_status(f"Could not open {path.name}: {error}")

    def _reveal_in_explorer(self, path: Path) -> None:
        # #25: this used to unconditionally shell out to "explorer", which
        # doesn't exist on macOS/Linux. Mirror _reveal_in_folder's platform
        # branching instead of assuming Windows.
        import subprocess

        try:
            if not path.exists():
                self._set_status(f"Path no longer exists: {path}")
                return
            if sys.platform.startswith("win"):
                if path.is_dir():
                    subprocess.Popen(["explorer", str(path)])  # noqa: S603,S607
                    self._set_status(f"Opened {path.name} folder in Explorer")
                    return
                # /select, highlights the file in Windows Explorer.
                subprocess.Popen(["explorer", f"/select,{path}"])  # noqa: S603,S607
                self._set_status(f"Revealing {path.name} in Explorer")
            elif sys.platform == "darwin":
                if path.is_dir():
                    subprocess.Popen(["open", str(path)])  # noqa: S603,S607
                    self._set_status(f"Opened {path.name} folder in Finder")
                    return
                subprocess.Popen(["open", "-R", str(path)])  # noqa: S603,S607
                self._set_status(f"Revealing {path.name} in Finder")
            else:
                target = path if path.is_dir() else path.parent
                webbrowser.open(target.as_uri())
                self._set_status(f"Opened {target.name} folder")
        except OSError as error:
            self._set_status(f"Could not open file manager: {error}")

    def open_logs_folder(self) -> None:
        logs_path = app_data_dir() / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)
        self._reveal_in_explorer(logs_path)

    def open_startup_logs(self) -> None:
        """Tools > Customize & Support > View Startup Logs... — open startup-errors.log directly."""
        log_path = app_data_dir() / "logs" / "startup-errors.log"
        if not log_path.exists():
            self._set_status(
                "No startup log entries yet. Logs are written when a startup task fails."
            )
            return
        self._reveal_in_explorer(log_path)

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
        import logging

        log = logging.getLogger(__name__)
        # Remember the active document's cursor position before we exit, so it is
        # restored next time that file is opened (last-position memory).
        self._remember_active_caret()
        # Tray mode hides instead of closing -- but only for a plain close, and a
        # failure in the tray path must never trap the window open.
        if not self._is_exiting:
            try:
                if self.settings.tray_enabled:
                    self._ensure_tray_icon()
                    # _ensure_tray_icon refuses on macOS (no menu-bar tray icon
                    # is created), so _tray_icon stays None. Hiding with no icon
                    # to restore from would leave the window non-restorable (#39);
                    # fall through to a normal close instead. The refusal already
                    # announced the limitation via the status bar.
                    if self._tray_icon is not None:
                        self.frame.Hide()
                        self._set_status(f"Quill is running in the {_TRAY_NOUN}")
                        event.Veto()
                        return
            except Exception:  # noqa: BLE001 - a tray failure must not block exit
                log.warning("Tray hide failed during close; closing instead", exc_info=True)

        # Offer to save. A user Cancel legitimately vetoes the close; an
        # *exception* here is a bug, not a cancel -- per #210 the window must
        # still close, so we log and proceed rather than aborting the handler
        # with no hard-exit armed (the previous behaviour: a raising save prompt
        # left the editor stuck open with nothing to force it shut).
        try:
            if not self._can_close_all_documents():
                event.Veto()
                return
        except Exception:  # noqa: BLE001 - never trap the window open on a prompt bug
            log.warning("Save-on-close prompt failed; closing anyway (#210)", exc_info=True)

        # Warn before silently abandoning real, hard-to-redo background work (an
        # Audio Studio export in progress, for example) -- only tasks that opted
        # in via _run_background_task(protect_on_close=True) count, so this never
        # fires for routine background activity (search/replace, dictation, pack
        # downloads, ...).
        try:
            protected = getattr(self, "_protected_background_jobs", None)
            if protected:
                if not self._confirm_close_with_busy_jobs(list(protected.values())):
                    event.Veto()
                    return
        except Exception:  # noqa: BLE001 - never trap the window open on a prompt bug
            log.warning("Busy-close prompt failed; closing anyway", exc_info=True)

        # #210: the close is committed. Arm the daemon hard-exit BEFORE any
        # cleanup so a blocking/throwing step -- or a wx main loop that never
        # returns -- can never leave the process running with no closable window.
        if getattr(self, "_hard_exit_enabled", False):
            from quill.stability.shutdown_watchdog import arm_hard_exit

            log.info("Close committed; arming hard-exit watchdog (#210)")
            arm_hard_exit()

        # #210: the window must always close. Every shutdown step below runs
        # under its own guard so that one failing or slow step (a watch worker,
        # an SSH socket, a settings write, the recovery lock, the sound backend)
        # can never throw out of this handler before we reach event.Skip() and
        # leave the frame stuck open. A failed step is logged, not fatal.
        def _safely(step: str, action: Callable[[], object]) -> None:
            try:
                action()
            except Exception:  # noqa: BLE001 - shutdown must never block close
                import logging

                logging.getLogger(__name__).warning("Shutdown step failed: %s", step, exc_info=True)

        # Quillin quill.shutdown event (best-effort; non-blocking). Fired before
        # teardown so a Quillin can persist its own state on exit.
        self._fire_quillin_event("quill.shutdown", {})

        def _shutdown_sound_manager() -> None:
            from quill.ui import sound_manager

            sound_manager.shutdown()

        # #210: persist critical state FIRST, before any teardown step that can
        # block (ssh socket, sound backend). If a later step wedges and the
        # hard-exit watchdog fires, settings, undo history, and the clean-exit
        # marker are already written, so the fast exit loses nothing.
        _safely("save settings", lambda: save_settings(self.settings))
        _safely("persistent undo flush", self.flush_persistent_undo)
        _safely("clean-exit marker", lambda: mark_clean_exit(self.session_id))
        # H-3-ui: destroy the modeless Watch Queue Monitor so it does not
        # outlive the main frame and leak a window reference.
        if self._watch_queue_monitor is not None:
            _safely("watch queue monitor", self._watch_queue_monitor.Destroy)
            self._watch_queue_monitor = None
            self._watch_queue_listbox = None
            self._watch_queue_pause_button = None
        _safely("watch service", self._watch_service.stop)
        _safely("model lifecycle timer", self._stop_lifecycle_sweep_timer)
        _safely("global hotkeys", self._unregister_global_hotkeys)
        _safely("tray icon", self._remove_tray_icon)
        radio_controller = getattr(self, "_radio_controller", None)
        if radio_controller is not None:
            _safely("radio player", radio_controller.shutdown)
        radio_recorder = getattr(self, "_radio_recorder", None)
        if radio_recorder is not None:
            _safely("radio recorder", radio_recorder.shutdown)
        radio_scheduler = getattr(self, "_radio_scheduler", None)
        if radio_scheduler is not None:
            _safely("radio recording scheduler", radio_scheduler.shutdown)
        radio_wake = getattr(self, "_radio_wake_watcher", None)
        if radio_wake is not None:
            _safely("radio wake-up timer", radio_wake.shutdown)
        podcast_controller = getattr(self, "_podcast_controller", None)
        if podcast_controller is not None:
            _safely("podcast player", podcast_controller.shutdown)
        podcast_queue = getattr(self, "_podcast_download_queue", None)
        if podcast_queue is not None:
            _safely("podcast downloads", podcast_queue.shutdown)
        sleep_timer = getattr(self, "_sleep_timer_controller", None)
        if sleep_timer is not None:
            _safely("media sleep timer", sleep_timer.shutdown)
        _safely("ssh connections", self.close_ssh_connections)
        # #32: drop GitHub-temp files no longer referenced by an open tab so
        # the user's app-data directory does not accumulate copies of files
        # they opened once and never saved back.
        prune = getattr(self, "prune_orphaned_github_temp", None)
        if callable(prune):
            _safely("github temp prune", prune)
        # Privacy: the browser read-aloud page holds the full document text as
        # plaintext in app-data; remove it on exit (quill/core/browser_reader.py).
        _safely("browser reader cleanup", self._cleanup_browser_reader_files)
        _safely("sound manager", _shutdown_sound_manager)
        # Destroy any straggler top-level windows (e.g. a modeless Ask Quill
        # chat frame) so they do not keep the wx main loop alive after the main
        # frame closes.
        wx = self._wx
        get_tlws = getattr(wx, "GetTopLevelWindows", None)
        if callable(get_tlws):
            for window in list(get_tlws()):
                if window is self.frame:
                    continue
                _safely("destroy window", window.Destroy)
        event.Skip()
        # Belt-and-suspenders: explicitly end the main loop after this event is
        # processed, so the process exits even if a window slipped past the
        # cleanup above or wx is not configured to exit on the last frame.
        app = wx.GetApp() if hasattr(wx, "GetApp") else None
        exit_loop = getattr(app, "ExitMainLoop", None)
        call_after = getattr(wx, "CallAfter", None)
        if callable(exit_loop) and callable(call_after):
            call_after(exit_loop)

    def _on_session_end(self, event: object) -> None:
        """Mark the session clean on an OS-initiated session end (#920).

        Windows fires ``EVT_QUERY_END_SESSION`` (whose default handler calls
        ``Close()`` on top-level windows, so the full ``_on_close`` teardown
        runs) and then the non-vetoable ``EVT_END_SESSION`` -- which has NO
        default ``Close()``, so the process can end here without ``_on_close``
        ever running. Either way an OS shutdown / restart / logoff is a CLEAN
        exit, not a crash, but the crash-recovery marker (``recovery_state.json``
        ``clean_exit``) is only ever set to True inside ``_on_close``. So a
        normal shutdown that bypassed ``_on_close`` left the marker stale, and
        the next launch falsely offered "Quill detected an unclean exit" with no
        traceback in the prior log -- the exact #920 report. Mark the session
        clean here, best-effort, so an OS shutdown is never misreported as a
        crash. Never raise: during shutdown any error must be swallowed so the
        process can still end; ``event.Skip()`` always runs.
        """
        try:
            mark_clean_exit(self.session_id)
        except Exception:  # noqa: BLE001 - shutdown-path best effort, never block
            import logging

            logging.getLogger(__name__).warning(
                "Session-end clean-exit marker write failed", exc_info=True
            )
        event.Skip()

    def _on_iconize(self, event: object) -> None:
        if self.settings.tray_enabled and event.IsIconized():
            self._ensure_tray_icon()
            self.frame.Hide()
            self._set_status(f"Minimized to {_TRAY_NOUN}")
        event.Skip()

    def _on_toggle_tray_mode(self, event: object) -> None:
        enabled = bool(event.IsChecked())
        self.settings.tray_enabled = enabled
        if enabled:
            self._ensure_tray_icon()
            self._set_status(f"{_TRAY_NOUN.capitalize()} mode enabled")
            return
        self._remove_tray_icon()
        self._set_status(f"{_TRAY_NOUN.capitalize()} mode disabled")

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

    def _clear_recovery_logs(self, logs_path: Path) -> int:
        """Delete log files in *logs_path*; return how many were removed.

        A file held open by the active logger (typically the current
        ``quill.log`` on Windows) cannot be unlinked, so it is truncated to zero
        bytes instead and still counted as cleared. Best effort: anything that
        can be neither removed nor truncated is skipped.
        """
        removed = 0
        try:
            entries = [entry for entry in logs_path.iterdir() if entry.is_file()]
        except OSError:
            return 0
        for entry in entries:
            try:
                entry.unlink()
                removed += 1
            except OSError:
                try:
                    entry.write_bytes(b"")
                    removed += 1
                except OSError:
                    continue
        return removed

    def _send_crash_report(self, offer: object, logs_path: Path) -> bool:
        """File a crash report from the recovery dialog. Returns True to close it.

        The Quill issue tracker is public, so this asks for explicit consent and
        only sends a redacted log summary. With a stored GitHub token it creates
        the issue directly, clears the logs, and returns True (close the dialog);
        without one it opens the manual report form and returns False.
        """
        wx = self._wx
        from quill.core.feedback_token import effective_github_token
        from quill.core.issue_submit import build_log_summary, submit_crash_issue

        with wx.MessageDialog(
            self.frame,
            "This files a report on Quill's PUBLIC issue tracker and includes a "
            "redacted summary of your most recent log file. Personal data is "
            "scrubbed, but the issue is visible to anyone. Send it now?",
            "Send Bug Report",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) as consent:
            if (
                self._show_modal_dialog(consent, "Send Bug Report", restore_editor_focus=False)
                != wx.ID_YES
            ):
                self._set_status("Bug report cancelled")
                return False

        if not effective_github_token():
            self._set_status("No GitHub token: opening the issue form")
            self.report_bug()
            return False

        # #1013: the report's log summary is a short tail (issue_submit's
        # _MAX_LOG_CHARS) that can miss the error evidence which actually
        # justified this offer, since the offer decision scans a much larger
        # window (recovery._LOG_TAIL_SCAN_BYTES). Include that evidence
        # explicitly so the filed report is self-explanatory.
        #
        # #1045/#1046: use the evidence begin_session() already captured on
        # the offer, not a fresh find_error_evidence(logs_path) scan here --
        # by the time this button is clicked (possibly long after launch),
        # the current session's own routine logging can have grown
        # quill.log enough to push the original evidence out of the scan
        # window, so a fresh scan would find nothing even though the offer
        # was correctly justified.
        evidence = getattr(offer, "error_evidence", None)
        evidence_section = (
            f"Error evidence that triggered this offer:\n{evidence}\n\n" if evidence else ""
        )
        body = (
            "Quill offered crash recovery after an unclean exit. Submitted "
            "automatically from the Crash Recovery dialog.\n\n"
            + evidence_section
            + build_log_summary(logs_path)
        )
        issue_url, error = submit_crash_issue(
            summary="Crash recovery: Quill detected an unclean exit",
            message=body,
            app_version=__version__ or "0.0.0",
            github_token=effective_github_token(),
            metadata={
                "session": getattr(offer, "session_id", ""),
                "snapshot": str(getattr(offer, "snapshot", "")),
            },
        )
        if not issue_url:
            self._set_status(f"Could not file report: {error}")
            with wx.MessageDialog(
                self.frame,
                f"The report could not be filed automatically:\n{error}\n\n"
                "Opening the manual report form instead.",
                "Bug Report",
                wx.OK | wx.ICON_WARNING,
            ) as failed:
                self._show_modal_dialog(failed, "Bug Report", restore_editor_focus=False)
            self.report_bug()
            return False

        self._copy_to_clipboard(issue_url)
        self._clear_recovery_logs(logs_path)
        self._record_notification(f"Filed crash report: {issue_url}", "support")
        self._set_status(f"Filed crash report: {issue_url}")
        with wx.MessageDialog(
            self.frame,
            f"Thanks. Your report was filed and the logs were cleared:\n{issue_url}\n\n"
            "The link is on your clipboard.",
            "Bug Report Sent",
            wx.OK | wx.ICON_INFORMATION,
        ) as done:
            self._show_modal_dialog(done, "Bug Report Sent", restore_editor_focus=False)
        return True

    def _prepare_crash_recovery_payload(
        self,
        offer: object,
        cancellation_token: object = None,
        operation_id: object = None,
        progress_callback: object = None,
    ) -> dict[str, object]:
        """Read the recovery snapshot + ensure the logs dir exist on a worker.

        This is the slow bit that used to block the UI thread for >30s on
        machines with large autosave files (#179).  No ``wx`` calls happen
        here, so the result is safe to deliver back through
        :class:`TaskManager` for the UI thread to render.
        """
        from quill.core.recovery import read_recovery_snapshot

        logs_path = app_data_dir() / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)

        preview_text = ""
        try:
            full, _had_rep = read_recovery_snapshot(offer.snapshot)
            lines = full.splitlines()
            preview_text = "\n".join(lines[:30])
            if len(lines) > 30:
                preview_text += f"\n\n... ({len(lines) - 30} more lines)"
        except OSError:
            preview_text = "(Could not read snapshot preview)"

        return {
            "logs_path": logs_path,
            "preview_text": preview_text,
        }

    def _offer_crash_recovery(self) -> None:
        """Show the crash-recovery dialog after offloading snapshot I/O.

        The pre-modal ``mkdir`` + ``read_recovery_snapshot`` work is submitted
        to :class:`TaskManager` so the UI thread stays responsive while the
        autosave file is being read (#179).  The actual ``wx.Dialog`` +
        ``ShowModal`` calls still run inside this method (on the UI thread,
        after the worker delivers its result), so the dialog-inventory
        qualname ``MainFrame._offer_crash_recovery`` is preserved.
        """
        if not self._recovery_offers:
            return
        offer = self._recovery_offers[0]

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

        # Hold a slot so the ``TaskManager`` callback can reach the offer and
        # intro without re-reading instance state.  The callback runs on the
        # UI thread (via ``call_ui_safely``), so it is safe to call back into
        # ``self._show_crash_recovery_dialog`` from inside the modal loop.
        ctx: dict[str, object] = {"offer": offer, "intro": intro}

        def _on_prepared(_operation_id: str, prepared: object) -> None:
            if not isinstance(prepared, dict):
                return
            self._show_crash_recovery_dialog(ctx, prepared)

        def _on_failed(_operation_id: str, _exc: BaseException) -> None:
            self._report_startup_task_failure("crash recovery")

        self._task_manager.submit(
            name="crash-recovery-prepare",
            func=self._prepare_crash_recovery_payload,
            on_success=_on_prepared,
            on_failure=_on_failed,
            offer=offer,
        )

    def _show_crash_recovery_dialog(
        self, ctx: dict[str, object], prepared: dict[str, object]
    ) -> None:
        """Build the crash-recovery modal and run the click loop on the UI thread.

        Kept in its own method so the dialog-inventory gate can attribute the
        ``wx.Dialog`` + ``wx.MessageDialog`` constructions to a stable qualname
        (``MainFrame._show_crash_recovery_dialog``).  Called by
        :meth:`_offer_crash_recovery` once ``TaskManager`` reports the
        snapshot read is done.
        """
        wx = self._wx
        offer = ctx["offer"]
        intro = ctx["intro"]
        logs_path = prepared["logs_path"]
        preview_text = prepared["preview_text"]

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
        set_accessible_name(logs_field, "Logs folder")
        logs_field.SetValue(str(logs_path))
        root.Add(logs_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        restore_button = wx.Button(dialog, id=wx.ID_YES, label="Restore Latest Snapshot")
        open_logs_button = wx.Button(dialog, label="Open Logs Folder")
        clear_logs_button = wx.Button(dialog, label="Clear Logs")
        save_diagnostics_button = wx.Button(dialog, label="Save Diagnostics...")
        send_report_button = wx.Button(dialog, label="Send Bug Report")
        skip_label = "Discard and Continue" if offer.dismissal_count >= 3 else "Skip Recovery"
        skip_button = wx.Button(dialog, id=wx.ID_NO, label=skip_label)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(restore_button, 0, wx.RIGHT, 6)
        buttons.Add(open_logs_button, 0, wx.RIGHT, 6)
        buttons.Add(clear_logs_button, 0, wx.RIGHT, 6)
        buttons.Add(save_diagnostics_button, 0, wx.RIGHT, 6)
        buttons.Add(send_report_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(skip_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)

        restore_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_YES))
        open_logs_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_APPLY))
        clear_logs_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLEAR))
        save_diagnostics_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_SAVE))
        send_report_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_HELP))
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
                if result == wx.ID_CLEAR:
                    removed = self._clear_recovery_logs(logs_path)
                    if removed:
                        message = (
                            f"Removed {removed} log file{'s' if removed != 1 else ''} from:\n"
                            f"{logs_path}"
                        )
                    else:
                        message = f"There were no log files to remove in:\n{logs_path}"
                    with wx.MessageDialog(
                        self.frame, message, "Logs Cleared", wx.OK | wx.ICON_INFORMATION
                    ) as confirm:
                        self._show_modal_dialog(confirm, "Logs Cleared", restore_editor_focus=False)
                    self._set_status(f"Cleared {removed} log file(s)")
                    continue
                if result == wx.ID_SAVE:
                    self.save_diagnostics_bundle()
                    continue
                if result == wx.ID_HELP:
                    if self._send_crash_report(offer, logs_path):
                        mark_recovery_offer_dismissed(offer)
                        return
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
                # Rich-mode sessions also snapshot RTF bytes (.rtfsnap): the
                # plain text alone would recover the words but lose the
                # formatting. Best-effort restore through the surface's TOM.
                self._maybe_restore_rich_snapshot(offer.snapshot)
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
        # #606: on a fresh install the default "Untitled" tab is deferred
        # until the Setup Wizard returns, so self.editor may not exist when
        # _apply_theme runs from __init__. Guard the editor writes with
        # getattr() (the same pattern used in show() and _focus_editor()).
        # The chrome + statusbar writes always apply, so the wizard still
        # sees the correct chrome even before the first document tab.
        editor = getattr(self, "editor", None)
        if editor is not None:
            editor.SetForegroundColour(foreground)
            editor.SetBackgroundColour(background)
            editor.Refresh()
        self.frame.SetForegroundColour(foreground)
        self.frame.SetBackgroundColour(chrome_background)
        self.statusbar.SetForegroundColour(foreground)
        self.statusbar.SetBackgroundColour(chrome_background)
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
            msg = f"Theme applied. Contrast ratio: {ratio:.1f}:1 ({grade})"
            if self.settings.announcement_startup_tips_enabled:
                self._set_status(msg)
            else:
                self._set_status_quiet(msg)
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
            if self.settings.announcement_startup_tips_enabled:
                self._announce(msg)
            else:
                self._set_status(msg)
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
            f"QUILL browse mode: {primary_command_chord_label()}+Q or Ctrl+Shift+Grave comma Q",
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
        set_accessible_name(search, "Search by command name or key binding")
        root.Add(search, 0, wx.EXPAND | wx.ALL, 8)

        cheatsheet_ctrl = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        set_accessible_name(cheatsheet_ctrl, "Key cheatsheet")
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
        from quill.ui.clipboard_retry import with_clipboard_read_retry

        has_text = has_unicode = has_bitmap = False
        raw_text = ""

        def _attempt() -> bool:
            nonlocal has_text, has_unicode, has_bitmap, raw_text
            if not clipboard.Open():
                return False
            try:
                has_text = clipboard.IsSupported(wx.DataFormat(wx.DF_TEXT))
                has_unicode = clipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT))
                has_bitmap = clipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP))
                if has_text or has_unicode:
                    obj = wx.TextDataObject()
                    if not clipboard.GetData(obj):
                        # Clipboard opened but the read itself lost the race
                        # (e.g. another process/AT briefly holds it) -- worth
                        # retrying rather than failing this attempt outright.
                        return False
                    raw_text = obj.GetText()
                return True
            finally:
                clipboard.Close()

        if not with_clipboard_read_retry(wx, _attempt):
            self._set_status("Clipboard is unavailable")
            return

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
        # #53: native button order -- Cancel-left/OK-right on macOS.
        first_btn, second_btn = ok_cancel_platform_order(ok_btn, cancel_btn)
        btn_row.Add(first_btn, 0, wx.RIGHT, 6)
        btn_row.Add(second_btn, 0)
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
        """When SAPI 5 self-voicing fails to initialise, surface it appropriately.

        SAPI 5 is QUILL's own fallback voice, used only when no screen reader is
        present. When a reader (NVDA/JAWS/Narrator) is doing the talking, a SAPI
        failure is benign, so it must not surface as an alarming accessibility
        error or a spoken "no voice" prompt -- the screen-reader user is not
        affected and has nothing to fix. We therefore decide the surface *before*
        recording anything: a detected reader gets only a quiet, unspoken status
        note plus a benign informational breadcrumb; without a reader the
        self-voice was the only voice, so the failure is spoken and recorded as a
        real accessibility problem (#749).
        """
        try:
            from quill.platform.windows.prism_bridge import tts_init_failed
        except ImportError:
            return
        if not tts_init_failed():
            return
        if self._screen_reader_handling_speech():
            # The screen reader is doing the talking; the self-voice is not needed.
            # Keep only a benign, informational breadcrumb (category "info", not
            # "accessibility") and a quiet, unspoken status note -- never an alarm.
            self._record_notification(
                "QUILL's optional SAPI 5 self-voice did not start. You are using a "
                "screen reader, so this has no effect on speech and no action is "
                "needed.",
                "info",
            )
            self._set_status_quiet("Speaking through your screen reader.")
            return
        # No screen reader: the self-voice was the only voice, so this is a real
        # problem the user must hear and may want to revisit. (The retry is
        # Tools > Retry TTS Engine.)
        self._record_notification(
            "Text-to-speech (the SAPI 5 self-voice) did not start. Run "
            "Tools > Retry TTS Engine to try again.",
            "accessibility",
        )
        self._set_status(
            "Text-to-speech failed to start, so QUILL has no voice. "
            "Run Tools > Retry TTS Engine to try again."
        )

    def _screen_reader_handling_speech(self) -> bool:
        """True when a screen reader is voicing QUILL's announcements.

        Either the announcement engine acquired a screen-reader backend
        (Prism / accessible_output2), or a known reader is running and will read
        the status bar and focus changes itself.
        """
        engine = getattr(self, "_announcement_engine", None)
        if engine is not None:
            try:
                if engine.state().active_backend in {"prism", "accessible_output2"}:
                    return True
            except Exception:  # noqa: BLE001 - never let a status check raise
                pass
        try:
            from quill.platform.windows.sr_detect import detect_screen_reader

            return bool(detect_screen_reader().detected)
        except Exception:  # noqa: BLE001
            return False

    def _binding_for(self, command_id: str) -> str | None:
        # Tolerate a not-yet-assigned keymap: key events (e.g. the dictation
        # hotkeys, matched in the editor key handlers) can fire before/around
        # full init, so fall back to the default binding rather than raising.
        keymap = getattr(self, "keymap", None)
        binding = keymap.get(command_id) if keymap is not None else None
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
            # Runtime gap check: a menu item that has no binding AND
            # no visible label produces a blank slot in the menu. The
            # customization layer can legitimately return a custom
            # label (we cannot tell that from the resolved label
            # alone), so we only warn when the original `title` is
            # empty too. This is loud at first menu build and lets the
            # CI audit gate (menu_lint) catch the same pattern
            # statically.
            if not (title or "").strip():
                import logging

                logging.getLogger(__name__).warning(
                    "menu item %r has no binding AND no visible label",
                    command_id,
                )
            return label
        # Route the binding through the chord-prefix display rewriter
        # so QUILL Key chords show as "QUILL Key + S" instead of the
        # raw "Ctrl+Shift+Grave, S" grammar. The stored binding
        # itself is unchanged.
        prefix = getattr(self.settings, "quill_key_binding", "Ctrl+Shift+Grave")
        display = format_binding_for_display(binding, prefix=prefix)
        if display != binding:
            # #612: text after a literal tab in a wx menu item label is not
            # just decorative -- wx parses it as a real native accelerator
            # (wxGetAccelFromString). "QUILL Key + S" parses as a clean,
            # modifier-less "S" accelerator because wx ignores the
            # unrecognized "QUILL Key" modifier token instead of rejecting
            # the whole string, silently binding bare S/R to menu commands
            # outside the chord dispatcher. The raw chord grammar
            # ("Ctrl+Shift+Grave, S") failed to parse for the same reason
            # the comma broke it, which is what kept this safe before the
            # display rewrite existed. Keep the friendly label visible but
            # out of the accelerator-parsed slot.
            return f"{label} ({display})"
        # macOS-only variant of #612: DEFAULT_KEYMAP spells the Command key
        # "Cmd" (matching how a person reads a Mac shortcut aloud, and matching
        # _parse_keybinding's own "Cmd" -> wx.ACCEL_CTRL mapping for the real
        # AcceleratorTable). But wx's menu-label accelerator parser
        # (wxGetAccelFromString) does not reliably recognize the literal token
        # "Cmd" -- it silently drops the unrecognized modifier and keeps the
        # bare final key, exactly like the QUILL Key case above. "Find
        # &Next\tCmd+G" bound a bare, unmodified G as a native menu
        # accelerator, intercepting every G/g keystroke before it ever reached
        # the editor. "Ctrl" is what wx already renders as the Command-key
        # glyph on macOS (see _parse_keybinding), so translate only for this
        # native-parsed slot; every other display surface keeps "Cmd".
        native_accelerator = re.sub(r"(?i)\bcmd\b", "Ctrl", display)
        return f"{label}\t{native_accelerator}"

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
        # #615: Surface the QUILL version in the window title so screen
        # readers announcing the focused window (JAWS Insert+T, NVDA+T,
        # Narrator Caps+H) read the version along with the document
        # name. The Ctrl+JAWSKey+V path lives in the OS layer and reads
        # from the launcher's VersionInfo; for the portable build
        # there is no versioned launcher, so JAWS reports only
        # "Version" with no number. The window title is the only
        # in-process channel we control, and it is reachable from
        # every screen reader.
        modified_suffix = self._dirty_title_suffix()
        version = _APP_TITLE_VERSION
        self.frame.SetTitle(f"{self._title_subject()}{modified_suffix} - {version}")
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

    def _pinned_markup_kind(self) -> str | None:
        """Markup kind from a user-pinned language profile, or None for auto-detect.

        When the user explicitly sets a Document Language (e.g. HTML on a .txt),
        that choice — not the file name — decides the markup surface. Returns one
        of "markdown"/"html"/"plain" when pinned, or None to fall back to the
        path/content auto-detection below.
        """
        tab = getattr(self, "_current_tab", None)
        if tab is None or not getattr(tab, "_language_profile_pinned", False):
            return None
        kind = getattr(getattr(tab, "_language_profile", None), "markup_kind", None)
        return kind if kind in {"markdown", "html", "plain"} else None

    def _effective_markup_kind(self) -> str:
        """Markup kind honoring a pinned profile, else inferred from the path.

        Drop-in replacement for the old infer_markup_kind(path) calls at the
        feature sites (heading/structure navigation, outline, preview, link
        insertion) so they follow the user's Document Language choice. Unpinned
        behaviour is identical to the path-based inference (including "yaml").
        """
        pinned = self._pinned_markup_kind()
        if pinned is not None:
            return pinned
        return infer_markup_kind(self.document.path)

    def _current_markup_context(self) -> str:
        pinned = self._pinned_markup_kind()
        if pinned is not None:
            return pinned
        path = self.document.path
        if path is not None:
            suffix = path.suffix.lower()
            if suffix in {".md", ".markdown", ".mdown", ".mkd"}:
                return "markdown"
            if suffix in {".html", ".htm", ".xhtml"}:
                return "html"
        # During the early phase of __init__ (e.g. fresh install with the
        # first-run wizard pending, or a multi-document notebook that has no
        # tab open yet) self.editor may not exist. Fall back to "plain" so
        # menu items default to a safe state and the refresh path returns.
        # The contextual refresh is re-queued via _request_menu_refresh and
        # re-runs once __init__ finishes and an editor is attached.
        editor = getattr(self, "editor", None)
        if editor is None:
            return "plain"
        sample = editor.GetValue()[:4000]
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
        # During the early phase of __init__ the editor and a number of
        # sub-views (notebook, preview pane, status-bar spell-check state)
        # are not yet constructed. Running the contextual refresh here would
        # touch attributes that do not exist. Mark the refresh pending so
        # the final flush in __init__ (and the wizard's post-create flush)
        # picks it up. We do not call _request_menu_refresh here: that
        # path flushes immediately, and flushing with the editor still
        # missing would recurse. The pending flag is idempotent, so
        # multiple deferrals collapse into a single later flush.
        #
        # The default for the gate is True (UI ready) so that tests using
        # ``MainFrame.__new__`` — which bypass __init__ and therefore do
        # not set ``_ui_ready`` at all — are unaffected. Only the real
        # ``__init__`` (which sets ``_ui_ready = False`` at the top) is
        # gated by this check.
        if getattr(self, "_ui_ready", True) is False:
            self._pending_menu_refresh = True
            return
        if not hasattr(self, "editor"):
            self._pending_menu_refresh = True
            return
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
                getattr(self, "_id_insert_bullet_list", None),
                getattr(self, "_id_insert_numbered_list", None),
                getattr(self, "_id_toggle_bullet_list", None),
                getattr(self, "_id_toggle_numbered_list", None),
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
        self._refresh_language_menu_radio(menu_bar)

    def _announce_result(self, message: str) -> None:
        """Set the status bar text and force-speak an explicit command result.

        The announcement engine deliberately stays silent while JAWS/NVDA is
        active (prism_bridge), on the assumption the screen reader will read
        whatever focus/control change the command caused. Commands that change
        nothing focus-wise -- an indent, a "no changes" check, a "nothing found"
        result -- would therefore update a status the user never hears. Route
        those results through here: ``force=True`` bypasses the suppression so
        the confirmation is spoken. The user explicitly invoked the command, so
        the result is spoken even in Quiet/Meeting verbosity modes."""
        self._announce(message, force=True)

    def _feature_enabled(self, feature_id: str) -> bool:
        # Remote kill switch (highest precedence): a signed safety advisory can
        # disable a feature for this version. Honored from the local cache even
        # offline; overridable with QUILL_IGNORE_FEATURE_LOCKS. Enforced here so
        # every feature-gated path (menu, palette, keybinding) obeys it uniformly.
        locks = getattr(self, "_feature_locks", None)
        if locks is not None and locks.is_locked(feature_id):
            return False
        feature_manager = getattr(self, "features", None)
        enabled = True if feature_manager is None else feature_manager.is_enabled(feature_id)
        # Experimental gates (Settings > Experimental). These features ship dark
        # until the user opts in: the master switch plus the per-feature checkbox.
        # GLOW is catalog-on, so the experimental gate narrows it; the read-only
        # publishing tools are profile-off, so the gate is the user's way to
        # light them (the locked send half is unaffected — it stays locked_off).
        if feature_id == "core.glow":
            return enabled and self._experimental_gate_on("glow_experimental_enabled")
        if feature_id == "future.publishing_read":
            return enabled or self._experimental_gate_on("publishing_experimental_enabled")
        return enabled

    def _experimental_gate_on(self, setting_name: str) -> bool:
        """True when the Experimental master switch AND ``setting_name`` are on."""
        return bool(getattr(self.settings, "experimental_acknowledged", False)) and bool(
            getattr(self.settings, setting_name, False)
        )

    def _note_active_feature_locks(self) -> None:
        """At startup, record a reviewable notice when cached safety locks apply."""
        try:
            active = self._feature_locks.active()
        except Exception:  # noqa: BLE001
            return
        if not active:
            return
        count = len(active)
        first_reason = next(iter(active.values()))
        self._record_notification(
            f"{count} feature{'s' if count != 1 else ''} temporarily disabled by a "
            f"QUILL safety advisory: {first_reason}",
            "update",
        )

    def _command_allowed_by_locks(self, command_id: str) -> bool:
        """Dispatch gate for the command registry: block remotely-locked commands.

        Consulted by keybindings and the command palette (both route through
        ``commands.run``), so a kill switch applies uniformly regardless of the
        per-handler ``_feature_enabled`` self-checks. Only remote *locks* are
        enforced here (profile/experimental gating stays with the handlers, so a
        feature disabled by a profile keeps its own explanatory behavior).
        """
        locks = getattr(self, "_feature_locks", None)
        if locks is None:
            return True
        command = self.commands.get(command_id)
        feature_id = command.feature_id if command is not None else "core.app"
        if not locks.is_locked(feature_id):
            return True
        reason = locks.reason(feature_id) or "a QUILL safety advisory"
        # _set_status_quiet (not _set_status) so the spoken _announce below is
        # the single spoken line, not a double-announce (#728).
        self._set_status_quiet(f"Turned off by a safety update: {reason}")
        self._announce(f"This feature is turned off by a safety update. {reason}")
        return False

    def _apply_feature_lock_menu_state(self) -> None:
        """Grey out menu items whose command's feature is remotely locked.

        Runs after each ``_build_menu`` so the menu path matches the dispatch
        gate: a locked feature's menu item is disabled (its accelerator and
        click become inert), not merely left enabled.
        """
        locks = getattr(self, "_feature_locks", None)
        if locks is None or not locks.active():
            return
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is None:
            return
        for command_id, menu_id in self._command_to_menu_id_map().items():
            command = self.commands.get(command_id)
            feature_id = command.feature_id if command is not None else "core.app"
            if locks.is_locked(feature_id):
                item = menu_bar.FindItemById(menu_id)
                if item is not None:
                    item.Enable(False)

    def _apply_feature_advisories(self, manifest: object, current_version: str) -> None:
        """Apply signed remote feature advisories from a fetched update manifest.

        Persists the resolved locked set, rebuilds the menu so newly-locked
        features dim, and announces any change. A manifest with no advisories
        clears prior locks (how a fixed build lifts a kill switch).
        """
        from quill.core.safety.feature_lock import apply_manifest_locks

        try:
            # Compare effective (escape-hatch-aware) state to effective state, so
            # running with QUILL_IGNORE_FEATURE_LOCKS set does not read as a
            # spurious "re-enabled" on every check.
            previous = self._feature_locks.active()
            self._feature_locks = apply_manifest_locks(manifest, current_version)
        except Exception:  # noqa: BLE001 - advisory handling must never break update check
            return
        now = self._feature_locks.active()
        if now == previous:
            return
        # Rebuild the menu, then dim the newly-locked items.
        try:
            self._build_menu()
        except Exception:  # noqa: BLE001
            pass
        newly_locked = [fid for fid in now if fid not in previous]
        lifted = [fid for fid in previous if fid not in now]
        if newly_locked:
            reason = now[newly_locked[0]]
            count = len(newly_locked)
            summary = (
                f"A QUILL safety update has temporarily disabled {count} "
                f"feature{'s' if count != 1 else ''}: {reason}"
            )
            self._announce(summary)
            self._record_notification(summary, "update")
        elif lifted:
            self._announce("A QUILL safety update has re-enabled a previously disabled feature.")

    def _record_notification(self, message: str, category: str = "info") -> None:
        self._notifications = add_notification(message, category)

    def _announce_brf_save_warning(self, message: str) -> None:
        """Surface the soft BRF save warning (#235): status + announcement."""
        self._set_status(message)

    def _announce(self, message: str, *, force: bool = False) -> None:
        self._status_message = message
        self._record_spoken(message)
        self._refresh_statusbar()
        # Verbosity routing (sub-PR 1.5): once the user has engaged verbosity, the
        # controller exists and decides whether Quiet/Meeting suppress speech. The
        # status bar (set above) is the always-on visual floor. Gated on the
        # controller existing, so the default path is unchanged until then.
        if not force and getattr(self, "_verbosity_controller", None) is not None:
            speech, suppressed = self._route_verbosity_announcement(message)
            if suppressed:
                return
            message = speech or message
        engine = getattr(self, "_announcement_engine", None)
        if engine is None:
            return
        backend_error = engine.announce(message, force_speech=force)
        if backend_error and backend_error != self._announcement_error_reported:
            self._announcement_error_reported = backend_error
            self._record_notification(backend_error, "accessibility")

    def _record_spoken(self, message: object) -> None:
        """Add a spoken line to the Spoken Echo history (newest kept last).

        Called from the announcement choke points (``_announce`` and
        ``_set_status``). The history is created lazily so stub frames in tests
        that never run ``__init__`` stay safe, and empty/consecutive-duplicate
        lines are dropped by ``record_spoken``.
        """
        history = getattr(self, "_spoken_echo_history", None)
        if history is None:
            history = new_history()
            self._spoken_echo_history = history
        record_spoken(history, message)

    def show_spoken_echo(self) -> None:
        """Virtualise the recent spoken announcements into a read-only dialog.

        This is the universal "Echo" review surface: after QUILL speaks
        anything (an indent depth, a formatting description, a save result),
        opening the Echo shows the last several announcements newest-first in a
        navigable, selectable, copyable control so the text can be re-read at
        leisure instead of chasing it in speech.
        """
        wx = self._wx
        history = getattr(self, "_spoken_echo_history", None)
        text = format_spoken_echo(list(history) if history else [])
        title = "Spoken Echo"
        dialog = wx.Dialog(
            self.frame,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(560, 420),
        )
        try:
            inner = wx.BoxSizer(wx.VERTICAL)
            inner.Add(
                wx.StaticText(
                    dialog,
                    label=(
                        "The most recent things QUILL announced, newest first. "
                        "Arrow through to re-read, select to copy."
                    ),
                ),
                0,
                wx.ALL | wx.EXPAND,
                8,
            )
            review = wx.TextCtrl(
                dialog,
                value=text,
                style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            )
            review.SetName("Spoken Echo — read-only history of recent announcements")
            inner.Add(review, 1, wx.ALL | wx.EXPAND, 8)
            close_button = wx.Button(dialog, id=wx.ID_OK, label="Close")
            buttons = wx.StdDialogButtonSizer()
            buttons.AddButton(close_button)
            buttons.Realize()
            inner.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
            dialog.SetSizer(inner)
            close_button.SetDefault()
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
            call_after = getattr(wx, "CallAfter", None)
            if callable(call_after):
                call_after(review.SetFocus)
            else:
                review.SetFocus()
            self._show_modal_dialog(dialog, title)
        finally:
            dialog.Destroy()
            self.editor.SetFocus()

    def _fire_quillin_event(self, event_name: str, context: dict) -> None:
        """Dispatch a Quillin document-lifecycle event if the mixin is loaded.

        Safe no-op when the Quillins mixin is absent (e.g. Safe Mode); the actual
        dispatch is non-blocking (background threads inside the mixin).
        """

        fire = getattr(self, "fire_quillin_event", None)
        if callable(fire):
            try:
                fire(event_name, context)
            except Exception:  # noqa: BLE001 - a Quillin must never break the editor
                pass

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
        # The "Entered/Exited <name> dialog" cues are opt-in via the
        # announce_dialog_transitions setting (off by default, matching
        # Settings); region tracking is unaffected.
        announce_transitions = (
            announce
            if getattr(getattr(self, "settings", None), "announce_dialog_transitions", False)
            else None
        )
        result = show_modal_dialog(
            dialog,
            label,
            announce=announce_transitions,
            enter_region=self._region_tracker.enter,
            exit_region=self._region_tracker.exit,
        )
        if restore_editor_focus:
            editor = getattr(self, "editor", None)
            if editor is not None and hasattr(editor, "SetFocus"):

                def _safe_set_focus() -> None:
                    # #619: the editor TextCtrl may be destroyed between the
                    # dialog returning and CallAfter dispatching this callable
                    # (e.g. the close-path save prompt, where DeletePage runs
                    # right after the dialog closes). Swallow the RuntimeError
                    # so the wx event loop does not surface it as a crash.
                    try:
                        editor.SetFocus()
                    except RuntimeError:
                        return

                call_after = getattr(self._wx, "CallAfter", None)
                if callable(call_after):
                    call_after(_safe_set_focus)
                else:
                    _safe_set_focus()
        return result

    def _show_message_box(self, message: str, caption: str, style: int) -> int:
        speak_transitions = getattr(
            getattr(self, "settings", None), "announce_dialog_transitions", False
        )
        self._region_tracker.enter(caption)
        if speak_transitions:
            announce(f"Entered {caption} dialog")
        try:
            result = self._wx.MessageBox(  # MSGBOX-OK: _show_message_box implementation
                message, caption, style
            )
        finally:
            if speak_transitions:
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
        # The "Entered/Exited" cues (and their settings gate) come from the inner
        # _show_modal_dialog call below; don't announce the transition twice.
        self._region_tracker.enter(caption)
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
            set_accessible_name(hint_ctrl, "What to try next")
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
        *,
        restore_focus: bool = True,
    ) -> int:
        wx = self._wx
        # #23: use the platform's native Yes / No / Cancel buttons (no
        # SetYesNoCancelLabels override). On at least one platform — macOS
        # Cocoa per user report — overriding the labels with "Save" /
        # "Don't Save" / "Cancel" also disables the built-in Y / N / Esc
        # keyboard accelerators that wx.MessageDialog normally wires up
        # against its synthesised buttons, so users had to Tab to a
        # button and press Space. Native labels = native accelerators, and
        # the title ("Unsaved changes") and body text still ask the
        # question in plain English so screen-reader users hear the
        # meaning, not just the button text.
        dialog = wx.MessageDialog(
            self.frame,
            message,
            title,
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
        )
        try:
            return self._show_modal_dialog(dialog, title, restore_editor_focus=restore_focus)
        finally:
            dialog.Destroy()

    def _confirm_close_with_busy_jobs(self, labels: list[str]) -> bool:
        """Ask whether to close now (stopping *labels*) or leave QUILL open.

        Returns True to proceed with closing, False to veto it. Native Yes/No
        (not a custom-labelled dialog) for the same keyboard-accelerator reason
        as ``_prompt_unsaved_changes_action`` (#23); the button meanings are
        spelled out in the message instead. Mentions Send to Tray as the
        alternative to keep the work running out of the way, rather than
        folding a third action into this dialog's buttons.
        """
        wx = self._wx
        what = labels[0] if len(labels) == 1 else f"{len(labels)} background jobs"
        message = (
            f"QUILL is still working: {what}.\n\n"
            "Yes closes QUILL now and stops it immediately -- anything it hasn't "
            "finished yet will be incomplete.\n"
            "No keeps QUILL open so it can finish.\n\n"
            f"Tip: File > Send to Tray keeps {what} running in the background "
            "and gets the window out of your way without stopping it."
        )
        dialog = wx.MessageDialog(
            self.frame,
            message,
            "QUILL is still working",
            wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT,
        )
        try:
            result = self._show_modal_dialog(dialog, "QUILL is still working")
        finally:
            dialog.Destroy()
        return result == wx.ID_YES

    def _confirm_discard_changes(self) -> bool:
        wx = self._wx
        if not getattr(self.settings, "confirm_destructive_actions", True):
            return True
        result = self._prompt_unsaved_changes_action(
            "Unsaved changes",
            "You have unsaved changes. Reload and discard them?",
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
        protect_on_close: bool = False,
    ) -> None:
        self._background_task_count = getattr(self, "_background_task_count", 0) + 1
        task_id = self._track_background_task_start(label)
        self._set_status(f"{label} started")
        # Opt-in: most background tasks (search/replace, dictation, pack downloads,
        # ...) are trivial to lose and would make a close-time warning noisy and
        # untrustworthy. Only tasks that explicitly ask to be protected -- real,
        # hard-to-redo work like an Audio Studio export -- gate the close prompt.
        if protect_on_close:
            jobs = getattr(self, "_protected_background_jobs", None)
            if jobs is None:
                jobs = {}
                self._protected_background_jobs = jobs
            jobs[task_id] = label

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
        # A no-op when this task was never protected (or the registry doesn't exist yet).
        getattr(self, "_protected_background_jobs", {}).pop(task_id, None)
        if error is not None:
            # A failed background task never invokes on_success, so if this
            # was a voice preview's synthesis raising (e.g. missing engine
            # executable), _synth_done never runs to cancel its pending
            # "generating preview" cue timer -- cancel it here instead so a
            # stray cue can't fire after the failure was already reported.
            self._cancel_preview_cue_timer()
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

    # ------------------------------------------------------------------
    # #262: Pandoc Import / Export and Batch Conversion handlers.
    # ------------------------------------------------------------------

    def import_document(self, format_name: str) -> None:
        """Import a single file of ``format_name`` into QUILL as a Markdown tab.

        Wires File > Import > {format} menu items. For editable output
        formats the post-conversion prompt asks the user to open the new
        file in a new window; for non-editable outputs we just show a
        "Converted to: {path}" message.
        """

        from quill.core import pandoc_formats

        wx = self._wx
        if not get_external_tool_status("pandoc").installed:
            self._offer_pandoc_download("Import")
            return
        exts = pandoc_formats.extensions_for(format_name)
        ext_list = ";".join(f"*{ext}" for ext in sorted(exts)) or "*.*"
        # The wx filter pattern needs the glob form (*.docx), not the bare
        # extension (.docx) -- otherwise the dialog matches no files and e.g.
        # .docx documents never appear in the list.
        ext_patterns = ";".join(f"*{ext}" for ext in sorted(exts)) or "*.*"
        format_label = pandoc_formats.get_format(format_name)
        label = format_label.display_name if format_label else format_name
        wildcard = f"{label} ({ext_list})|{ext_patterns}|All files (*.*)|*.*"

        with wx.FileDialog(
            self.frame,
            f"Import {label}",
            defaultDir=self._file_dialog_default_dir(),
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, f"Import {label}") != wx.ID_OK:
                return
            source_path = Path(dialog.GetPath())

        self._set_status(f"Importing {source_path.name} via Pandoc...")
        try:
            # Import always brings the file in as Markdown text (the editor's
            # format). The output must be a text writer, not the *input* format
            # -- passing format_name here made Pandoc try to write e.g. docx to
            # stdout ("Cannot write docx output to terminal").
            result = convert_document_with_pandoc(
                source_path,
                "markdown",
                from_format=format_name,
            )
        except (PandocUnavailableError, PandocConversionError, ValueError) as error:
            self._show_message_box(
                f"Pandoc import failed: {error}",
                "Import",
                wx.ICON_ERROR | wx.OK,
            )
            self._set_status("Pandoc import failed")
            return

        document = Document(
            text=result.text,
            path=None,
            modified=True,
            encoding="utf-8",
            line_ending="\n",
        )
        self._create_document_tab(document, select=True)
        self._record_recent(source_path)
        self._set_status_quiet(f"Imported {source_path.name}")
        self._announce(f"Imported {source_path.name} as Markdown.")
        # #187: the import file dialog's own close-out queues a CallAfter that
        # restores focus to the *previous* tab's editor (captured before this
        # new tab existed). Queue a second, correctly-bound CallAfter so it
        # runs after that stale one and wins, landing focus on the new editor
        # -- otherwise it never receives its first SetFocus and its content
        # stays visually blank until the user manually tabs into it.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after) and hasattr(self, "editor"):
            call_after(self.editor.SetFocus)

    def import_document_other(self) -> None:
        """Prompt the user for an arbitrary Tier-1 format name and import.

        The "Other Pandoc Format..." menu entry. Out of scope for Tier-2/3
        in this PR; this only offers the Tier-1 set the user has not seen
        on the standard menu.
        """

        from quill.core import pandoc_formats

        wx = self._wx
        choices = [fmt.display_name for fmt in pandoc_formats.formats_for_direction("import")]
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose a Tier-1 Pandoc input format",
            "Other Pandoc Format",
            choices,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Other Pandoc Format") != wx.ID_OK:
                return
            index = dialog.GetSelection()
        formats = pandoc_formats.formats_for_direction("import")
        if 0 <= index < len(formats):
            self.import_document(formats[index].name)

    def export_document(self, format_name: str) -> None:
        """Export the current buffer to ``format_name`` via Pandoc.

        For editable output formats the post-conversion prompt offers to
        open the new file; otherwise we just announce the destination.
        """

        from quill.core import pandoc_formats
        from quill.ui.single_convert_dialog import prompt_open_in_new_window

        wx = self._wx
        if not self.editor or not getattr(self, "document", None):
            self._show_message_box(
                "Open or create a document before exporting.",
                "Export",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        if not get_external_tool_status("pandoc").installed:
            self._offer_pandoc_download("Export")
            return

        if getattr(self.document, "modified", False):
            self.save_file()
            if self.document.path is None or self.document.modified:
                self._set_status("Export cancelled (save required first)")
                return

        target_ext = pandoc_formats.primary_extension_for(format_name) or ".out"
        format_label = pandoc_formats.get_format(format_name)
        label = format_label.display_name if format_label else format_name
        wildcard = f"{label} (*{target_ext})|*{target_ext}|All files (*.*)|*.*"

        default_name = self._suggested_save_basename("Untitled") + target_ext
        with wx.FileDialog(
            self.frame,
            f"Export as {label}",
            defaultDir=self._file_dialog_default_dir(),
            defaultFile=default_name,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, f"Export as {label}") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())

        self._set_status(f"Exporting to {target.name} via Pandoc...")
        try:
            # hard_line_breaks: the editor is line-oriented (one editor line is
            # one paragraph), so bare "gfm" — where a single newline is a soft
            # wrap — would join the user's lines into one paragraph in every
            # exported format.
            convert_file_with_pandoc(
                self.document.path or Path(""),
                target,
                from_format="gfm+hard_line_breaks",
                to_format=format_name,
            )
        except (PandocUnavailableError, PandocConversionError, ValueError) as error:
            self._show_message_box(
                f"Pandoc export failed: {error}",
                "Export",
                wx.ICON_ERROR | wx.OK,
            )
            self._set_status("Pandoc export failed")
            return

        self._record_recent(target)
        self._announce(f"Exported {target.name}")

        if prompt_open_in_new_window(
            self.frame,
            output_path=target.name,
            target_format=format_name,
            show_modal_fn=self._show_modal_dialog,
        ):
            self.open_file(path=target)
        else:
            self._set_status(f"Exported to {target}")

    def export_document_other(self) -> None:
        """Prompt the user for an arbitrary Tier-1 export format."""

        from quill.core import pandoc_formats

        wx = self._wx
        choices = [fmt.display_name for fmt in pandoc_formats.formats_for_direction("export")]
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose a Tier-1 Pandoc output format",
            "Other Pandoc Format",
            choices,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Other Pandoc Format") != wx.ID_OK:
                return
            index = dialog.GetSelection()
        formats = pandoc_formats.formats_for_direction("export")
        if 0 <= index < len(formats):
            self.export_document(formats[index].name)

    def export_daisy(self) -> None:
        """Export the current buffer as a DAISY 2.02 text-only talking book (#251).

        DAISY books are a *folder* of files, not a single file, so the chosen name
        becomes a folder that the three book files are written into. Unlike the
        Pandoc exports this reads the live editor buffer, so no save is required
        first. The result opens in DAISY readers and hardware players that read
        text-only books with their own text-to-speech.
        """
        from quill.io.daisy import NCC_FILENAME, write_daisy_textonly

        wx = self._wx
        if not self.editor or not getattr(self, "document", None):
            self._show_message_box(
                "Open or create a document before exporting.",
                "Export",
                wx.ICON_INFORMATION | wx.OK,
            )
            return

        text = self.editor.GetValue()
        stem = self._suggested_save_basename(self.document.name or "Untitled")
        title = stem or "Untitled"
        with wx.FileDialog(
            self.frame,
            "Export as DAISY talking book",
            defaultDir=self._file_dialog_default_dir(),
            defaultFile=f"{stem} (DAISY)",
            wildcard="DAISY talking book folder|*",
            style=wx.FD_SAVE,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Export as DAISY talking book") != wx.ID_OK:
                return
            book_dir = Path(dialog.GetPath())

        # The picker hands back a file-style path; treat it as the book folder.
        if book_dir.suffix:
            book_dir = book_dir.with_suffix("")
        if book_dir.exists() and any(book_dir.iterdir()):
            confirm = self._show_message_box(
                f"The folder {book_dir.name} already exists and is not empty. "
                "Write the DAISY book into it anyway?",
                "Folder exists",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            if confirm != wx.ID_YES:
                self._set_status("DAISY export cancelled")
                return

        try:
            write_daisy_textonly(text, book_dir, title=title)
        except OSError as error:
            self._show_message_box(
                f"DAISY export failed: {error}",
                "Export",
                wx.ICON_ERROR | wx.OK,
            )
            self._set_status("DAISY export failed")
            return

        self._announce(f"Exported DAISY talking book {book_dir.name}")
        self._set_status(f"Exported DAISY talking book to {book_dir / NCC_FILENAME}")

    def run_batch_conversion_wizard(self) -> None:
        """Open the Batch Conversion wizard and submit the resulting plan."""

        from quill.core.batch_convert import BatchPlan as _BatchPlan
        from quill.core.batch_convert import BatchReport as _BatchReport
        from quill.core.batch_convert import OverwriteRequired, run_batch
        from quill.ui.batch_wizard import run_batch_wizard

        request = run_batch_wizard(
            self.frame,
            self.settings,
            announce_cb=self._announce,
            show_modal_fn=self._show_modal_dialog,
        )
        if request is None:
            self._set_status("Batch conversion cancelled")
            return

        plan: _BatchPlan = request.plan

        def _confirm_overwrite_all(paths: tuple) -> bool:
            """Prompt the user once for a batch of would-overwrite outputs."""

            wx = self._wx
            listing = "\n".join(str(p) for p in paths[:10])
            if len(paths) > 10:
                listing += f"\n... and {len(paths) - 10} more"
            message = (
                f"{len(paths)} output file(s) already exist:\n\n{listing}\n\nOverwrite them all?"
            )
            with wx.MessageDialog(
                self.frame,
                message,
                "Overwrite files?",
                style=wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT,
            ) as dialog:
                return self._show_modal_dialog(dialog, "Overwrite files?") == wx.ID_YES

        def _worker(progress) -> object:
            try:
                return run_batch(
                    plan,
                    progress=progress,
                    ask_overwrite=_confirm_overwrite_all,
                )
            except OverwriteRequired as exc:
                if not _confirm_overwrite_all(exc.outputs):
                    return run_batch(
                        plan,
                        progress=progress,
                        ask_overwrite=lambda _p: False,
                    )
                return run_batch(
                    plan,
                    progress=progress,
                    ask_overwrite=lambda _p: True,
                )

        def _on_done(result: object) -> None:
            if not isinstance(result, _BatchReport):
                return
            self._announce(
                f"Batch conversion complete: {result.converted} of {result.total} files in "
                f"{result.duration_seconds:.1f} seconds. "
                f"{result.failed} failed, {result.skipped} skipped."
            )
            self._set_status(
                f"Batch conversion complete: {result.converted} converted, "
                f"{result.failed} failed, {result.skipped} skipped."
            )
            self.show_help_status_page()

        self._run_background_task(
            "Batch conversion",
            _worker,
            _on_done,
            notify_on_success=True,
            notify_on_error=True,
        )

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
        dlg = getattr(self, "_help_status_dialog", None)
        if dlg is not None and dlg.is_alive():
            dlg.refresh(self._build_help_status_data())
        else:
            self._set_status_page_live_updates(False)

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
        closing_doc = self._document_tabs[index].document
        closing_path = getattr(closing_doc, "path", None)
        close_context = {
            "file_path": str(closing_path) if closing_path is not None else "",
            "extension": closing_path.suffix.lower() if closing_path is not None else "",
            "title": getattr(closing_doc, "name", ""),
        }
        self._fire_quillin_event("document.before_close", close_context)
        self.notebook.DeletePage(index)
        del self._document_tabs[index]
        self._fire_quillin_event("document.after_close", close_context)
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
        # #619: the close path destroys the editor TextCtrl via DeletePage
        # right after this prompt returns, so restoring editor focus here
        # would queue a CallAfter that fires against a dead widget and
        # raises RuntimeError. The Reload caller
        # (_confirm_discard_changes) keeps the default restore_focus=True
        # because reloading does not destroy the editor.
        result = self._prompt_unsaved_changes_action(
            "Unsaved changes",
            f"You have unsaved changes. Save before {action_label}?",
            restore_focus=False,
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
        self._fire_quillin_event(
            "document.created",
            {"file_path": "", "extension": "", "title": self.document.name},
        )

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
        selected_path = path
        if selected_path is None:
            # #620: when ``Settings.use_simple_file_dialog`` is on, show the
            # keyboard-friendly picker; otherwise show the standard
            # ``wx.FileDialog``. The simple dialog can also route us back to
            # the native dialog for one invocation if the user clicks the
            # "Use Windows Dialog" button. ``_prompt_for_open_path`` is
            # defined on :class:`SimpleOpenMixin`.
            selected_path = self._prompt_for_open_path()
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
            docx_engine = self._docx_read_engine()
            self._run_background_task(
                f"Opening {selected_path.name}",
                lambda _progress: read_open_document(
                    selected_path, suffix, word_mode=word_mode, docx_engine=docx_engine
                ),
                finish,
            )
            return

        csv_mode = None
        if suffix in {".csv", ".tsv"}:
            csv_mode = self._resolve_csv_open_mode(selected_path)
        finish(read_open_document(selected_path, suffix, csv_mode=csv_mode))

    def _docx_read_engine(self) -> str:
        """The ``docx_read_engine`` setting, resolved on the UI thread.

        Workers must not touch settings mid-run, so callers capture this before
        handing a read to the task manager (same pattern as ``word_mode``).
        """
        return str(getattr(getattr(self, "settings", None), "docx_read_engine", "auto"))

    def _maybe_apply_illumination(self, loaded: object, selected_path: Path, suffix: str) -> bool:
        """Restore hidden formatting from a ``<name>.illumination`` sidecar when
        opening a plain-text file, so a .txt saved with an Illumination reopens
        fully formatted. No-op (returns False) when there is no sidecar, the
        version is unknown, or the text drifted (edited outside QUILL) — the file
        then opens as plain text. Returns True when formatting was restored."""
        if suffix != ".txt":
            return False
        text = getattr(loaded, "text", None)
        if not isinstance(text, str):
            return False
        from quill.io.illumination import read_illumination, restore_markup

        illumination = read_illumination(selected_path)
        if illumination is None:
            return False
        restored = restore_markup(illumination, text)
        if restored is None:
            return False
        loaded.text = restored
        loaded.modified = False
        return True

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
        illuminated = self._maybe_apply_illumination(loaded, selected_path, suffix)
        self._epub_book = epub_book if suffix == ".epub" else None
        linkage_entry = get_publishing_linkage(selected_path)
        if linkage_entry is not None:
            apply_publishing_linkage_to_source_metadata(loaded.source_metadata, linkage_entry)
        if existing_index >= 0:
            tab = self._document_tabs[existing_index]
            tab.document = loaded
            tab.editor.ChangeValue(loaded.text)
            self._load_persistent_undo_state(selected_path, loaded.text)
            self._select_tab(existing_index)
        else:
            if loaded.source_metadata.get("csv_open_mode") == "grid":
                # Consolidated CSV grid: when Table Studio is enabled it is the one
                # accessible grid, so open the file there (F2 edit, context-menu
                # sort/insert/move, row headers) and keep a normal text tab behind
                # it. Deferred so the open pipeline settles first. Otherwise the
                # legacy CsvGridSurface tab is used.
                if self._experimental_gate_on("table_studio_experimental_enabled"):
                    self._create_document_tab(loaded, select=True)
                    self._wx.CallAfter(self._open_csv_in_table_studio, selected_path)
                else:
                    self._create_csv_document_tab(loaded, select=True)
            elif loaded.source_metadata.get("word_open_mode") == "structured":
                self._create_word_document_tab(loaded, select=True)
            elif suffix == ".rtf":
                # An .rtf is inherently a rich document. The tab is a normal
                # QuillRichEdit tab; rich mode loads the sanitized RTF natively
                # through the TOM where available and stays on the converted
                # text (rich_converted) otherwise — never a blank editor.
                self._create_document_tab(loaded, select=True)
                self._enter_rich_mode_for_open(selected_path, loaded)
                self._announce_rtf_safety(loaded)
            elif suffix == ".docx":
                # Editable rich Word: the extracted text opens first (the
                # classic floor), then rich mode is offered/entered behind the
                # honest-fidelity scan — a flagged original is never rewritten
                # without a warning and a one-time backup.
                self._create_document_tab(loaded, select=True)
                self._enter_docx_rich_mode_for_open(selected_path, loaded)
            else:
                self._create_document_tab(loaded, select=True)
            self._load_persistent_undo_state(selected_path, loaded.text)
            self._location_ring = LocationRing()
            self._location_ring.record(0)
        self._announce_encoding_fallback(loaded)
        self._position_editor_at(line=line, column=column)
        if record_recent:
            self._record_recent(selected_path)
        self._refresh_title()
        self._last_intake_report = build_intake_report(loaded)
        if illuminated:
            self._set_status(
                f"Opened {selected_path.name}; formatting restored from its Illumination"
            )
        else:
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
        self._announce(self._brf_open_message(loaded, selected_path))
        # Quillin document.opened event, then any file-type handlers for this suffix.
        open_context = {
            "file_path": str(selected_path),
            "extension": selected_path.suffix.lower(),
            "title": loaded.name or selected_path.name,
        }
        self._fire_quillin_event("document.opened", open_context)
        fire_file_type = getattr(self, "fire_quillin_file_type_event", None)
        if callable(fire_file_type):
            try:
                fire_file_type(selected_path)
            except Exception:  # noqa: BLE001 - a Quillin must never break open
                pass

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

    def _announce_rtf_safety(self, document: Document) -> None:
        """Announce rich-mode open and any RTF safety findings."""
        metadata = document.source_metadata
        blocked = metadata.get("rtf_blocked")
        warnings = metadata.get("rtf_warnings")
        parts = ["Opened as Rich Text."]
        if isinstance(blocked, list) and blocked:
            parts.append(
                "Removed unsafe content: " + ", ".join(str(item) for item in blocked) + "."
            )
        if isinstance(warnings, list) and warnings:
            parts.append(
                "Flagged for your consent: " + ", ".join(str(item) for item in warnings) + "."
            )
        self._set_status(" ".join(parts))

    def _announce_encoding_fallback(self, document: Document) -> None:
        """Tell the user when #867's non-UTF-8 fallback decoded this file."""
        detected = document.source_metadata.get("encoding_detected")
        if not detected:
            return
        self._set_status(f"Opened using {detected} text encoding (not UTF-8).")

    def next_document(self) -> None:
        self._switch_document(reverse=False)

    def previous_document(self) -> None:
        self._switch_document(reverse=True)

    def go_to_document(self, position: int) -> None:
        """Switch to the document in tab ``position`` (1-based; 10 == Alt+0).

        Out-of-range positions (no such tab open) just announce that nothing is
        there rather than switching. A single status update carries the spoken
        feedback — ``_activate_tab`` does not speak, so there is no double-talk.
        """
        index = position - 1
        if 0 <= index < len(self._document_tabs):
            self._select_tab(index)
            self._set_status(f"Switched to {self.document.name}")
        else:
            self._set_status(f"No document {position} open")

    def close_other_documents(self) -> None:
        self._close_other_tabs(self._active_tab_index)

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
    # Compare mode (#193/#194) — keyboard-first diff navigation
    # ------------------------------------------------------------------

    def send_to_tray(self) -> None:
        self._ensure_tray_icon()
        self.settings.tray_enabled = True
        self.frame.Hide()
        self._set_status(f"Sent Quill to {_TRAY_NOUN}")

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

    def toggle_tab_insert_mode(self, enabled: bool | None = None) -> None:
        """Toggle whether the Tab key inserts a literal tab or indents lines.

        Default (off) keeps the smart line-indent behaviour. On, Tab types a
        tab character at the caret like a plain text editor. The new mode is
        spoken and reflected in the Tab Mode status-bar cell and the Format
        menu check item."""
        next_state = (not self._tab_inserts_literal) if enabled is None else enabled
        self._tab_inserts_literal = next_state
        self._sync_tab_mode_menu_check()
        self._refresh_statusbar()
        self._set_status(
            "Tab key inserts a tab character" if next_state else "Tab key indents the line"
        )

    def _sync_tab_mode_menu_check(self) -> None:
        menu_bar = getattr(self.frame, "GetMenuBar", None)
        menu_id = getattr(self, "_id_toggle_tab_mode", None)
        if menu_id is None or not callable(menu_bar):
            return
        bar = menu_bar()
        if bar is None:
            return
        item = bar.FindItemById(menu_id)
        if item is not None and item.IsCheckable():
            item.Check(self._tab_inserts_literal)

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
        self._reveal_in_explorer(self.document.path.parent)
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
        # On the first-run path the editor is created after the wizard closes,
        # but _bind_events() (which calls this) runs during __init__ before that.
        # No-op until the editor exists; _maybe_run_first_run_onboarding re-applies
        # soft wrap once the first document tab is created.
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        wx = self._wx
        style = editor.GetWindowStyleFlag()
        if enabled:
            style = style & ~wx.TE_DONTWRAP
        else:
            style = style | wx.TE_DONTWRAP
        editor.SetWindowStyleFlag(style)

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
        self._set_status(f"Restored from {_TRAY_NOUN}")

    def _on_tray_right_click(self, _event: object) -> None:
        wx = self._wx
        if self._tray_icon is None:
            return
        menu = wx.Menu()
        show_id = wx.NewIdRef()
        exit_id = wx.NewIdRef()
        menu.Append(show_id, "Show Quill")
        menu.Bind(wx.EVT_MENU, lambda _e: self._restore_from_tray(), id=show_id)
        if self._feature_enabled("core.abbreviations"):
            menu.AppendSeparator()
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
        if self._feature_enabled("core.notes"):
            sticky_id = wx.NewIdRef()
            new_sticky_id = wx.NewIdRef()
            menu.AppendSeparator()
            menu.Append(sticky_id, "Sticky Notes...")
            menu.Append(new_sticky_id, "New Sticky Note...")
            menu.Bind(wx.EVT_MENU, lambda _e: self.manage_sticky_notes(), id=sticky_id)
            menu.Bind(wx.EVT_MENU, lambda _e: self.create_sticky_note(), id=new_sticky_id)
        if self._feature_enabled("core.radio"):
            menu.AppendSeparator()
            self._build_radio_tray_menu(menu)
        if self._feature_enabled("core.podcasts"):
            menu.AppendSeparator()
            self._build_podcast_tray_menu(menu)
        menu.AppendSeparator()
        menu.Append(exit_id, "Exit Quill")
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
        # #29: wx.adv.TaskBarIcon constructs without a TaskBarIconType arg works on
        # Windows/Linux (notification area / status notifier) but on macOS it
        # produces a Dock tile, not a menu-bar extra, which is what users expect
        # when they tick "Enable system tray mode". Honouring the checkbox on
        # macOS would silently misrepresent the behaviour, so refuse the call,
        # surface the limitation once per session via the status bar, and let
        # the Hide-on-close path fall through to a normal close.
        if sys.platform == "darwin":
            if not getattr(self, "_tray_unsupported_announced", False):
                self._tray_unsupported_announced = True
                self._set_status(
                    "System tray mode is not available on macOS; the window will close instead."
                )
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
        Word (.docx), HTML, or stripped plain text for those extensions and writes
        it verbatim (as Markdown) otherwise. The plain-text link style follows the
        setting so URLs survive when the writer wants them to.
        """
        link_style = str(
            getattr(getattr(self, "settings", None), "plain_text_link_style", "text_url")
        )
        docx_engine = str(getattr(getattr(self, "settings", None), "docx_write_engine", "auto"))
        # Rich mode saves natively via the TOM (no conversion, no fidelity
        # loss); everything else routes through the classic conversion writer.
        if not self._save_rich_document_natively(document, target):
            write_document_as(
                document,
                target,  # type: ignore[arg-type]
                plain_text_link_style=link_style,
                docx_engine=docx_engine,
            )
        self._sync_publishing_linkage_for_document(document)  # type: ignore[arg-type]
        # Restore points: snapshot the canonical text of every successful save
        # (best-effort by contract; can never be the reason a save fails).
        self._record_save_restore_point(document)

    def _sync_publishing_linkage_for_document(self, document: Document) -> None:
        """Persist or refresh this document's publishing linkage, keyed by its path.

        Structured surfaces (CSV grid, Word) are excluded: Compare/Update only
        ever read ``self.editor.GetValue()`` as markdown/HTML text, a shape those
        surfaces were never designed to produce, so linkage is never persisted
        for them in the first place (and therefore never restored on reopen).
        Attribute access is defensive throughout, matching this method's other
        callers: ``document`` and ``self`` are not always a fully-populated
        ``Document``/``MainFrame`` in characterization tests that stub only the
        attributes a call path touches.
        """
        metadata = getattr(document, "source_metadata", None)
        if not isinstance(metadata, dict):
            return
        entry = publishing_linkage_from_source_metadata(metadata)
        if entry is None:
            return
        path = getattr(document, "path", None)
        if path is None:
            return
        if isinstance(getattr(self, "editor", None), (CsvGridSurface, WordDocumentSurface)):
            return
        upsert_publishing_linkage(path, entry)

    def save_file(self) -> None:
        wx = self._wx
        if self._active_tab().read_only_remote:
            self.save_copy_remote()
            return
        if self.document.path is None:
            self.save_file_as()
            return
        # The Document Format switcher retargeted this tab's file type: Save
        # proposes the renamed path through Save As instead of silently writing
        # a different format into the old extension.
        redirect = self._pending_format_redirect()
        if redirect is not None:
            self._set_status(f"Format changed; choose where to save {redirect.name}")
            self.save_file_as()
            return
        path = self.document.path
        if path.suffix.lower() in EXPORT_ONLY_SUFFIXES:
            # e.g. an opened PDF: the buffer is extracted text. Writing it back
            # would destroy the binary original, so route to Save As instead.
            self._show_message_box(
                f"{self.document.name} was opened as extracted text. QUILL cannot "
                f"write {path.suffix} files directly, so saving over the original "
                "would destroy it. Choose a new name and format (Markdown, Word, "
                "HTML, RTF, or text), or use File > Export.",
                "Save",
                wx.ICON_INFORMATION | wx.OK,
            )
            self.save_file_as()
            return
        # Optional pre-save proofread (off by default): review misspellings in the
        # editor before the file is written. save_file_as runs its own copy.
        if getattr(self.settings, "spell_check_before_save", False):
            self.open_spell_check_dialog()
        if self.document.modified:
            backup_document(self.document)
        try:
            self._write_document_to_disk(self.document)
        except OSError as error:
            self._show_message_box(
                f"Could not save {self.document.name}: {error}",
                "Save",
                wx.ICON_ERROR | wx.OK,
            )
            self._set_status(f"Could not save {self.document.name}")
            return
        # Persist this document's bookmarks + cursor position under its path now that
        # it is saved (also migrates an untitled document's in-memory bookmarks).
        self._save_active_bookmarks()
        self._save_inline_notes()
        self._remember_active_caret()
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
        # Quillin document.after_save event (non-blocking; dispatched async).
        path = self.document.path
        if path is not None:
            self._fire_quillin_event(
                "document.after_save",
                {
                    "file_path": str(path),
                    "extension": path.suffix.lower(),
                    "title": self.document.name,
                },
            )
        # Incremental vault indexing: if this note lives in the open vault, re-parse it
        # into the cached index so backlinks/search/tags reflect the save immediately.
        self._vault_on_document_saved(path)

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

    # Save As wildcard filter index -> the extension that filter implies.
    _SAVE_FILTER_EXTENSIONS = {0: ".txt", 1: ".md", 2: ".html", 3: ".rtf", 4: ".docx"}

    @staticmethod
    def _export_route_for_suffix(suffix: str) -> str | None:
        """The Pandoc export format for an export-only Save As target, or ``None``.

        Save As cannot write these formats itself; the ones Pandoc can produce
        get offered a hand-off to File > Export, the rest are refused outright.
        """
        return {".pdf": "pdf", ".odt": "odt", ".epub": "epub"}.get(suffix.lower())

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

    def _suggested_save_basename(self, fallback: str = "") -> str:
        """Suggested filename stem for a Save/Export dialog.

        A titled document keeps its current stem. For an untitled document, the
        'Suggest a filename from the first line' setting (``first_line_as_title``)
        derives a title from the first line across formats; otherwise *fallback*.
        """
        if self.document.path is not None:
            return self.document.path.stem
        if getattr(self.settings, "first_line_as_title", False):
            from quill.core.titles import suggested_title_from_text

            editor = getattr(self, "editor", None)
            if editor is not None:
                title = suggested_title_from_text(editor.GetValue())
                if title:
                    return title
        return fallback

    def save_file_as(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Save file as",
            defaultDir=self._file_dialog_default_dir(),
            defaultFile=self._suggested_save_basename(),
            wildcard=(
                "Text files (*.txt)|*.txt|Markdown files (*.md)|*.md|"
                "HTML files (*.html;*.htm;*.xhtml)|*.html;*.htm;*.xhtml|"
                "Rich Text Format (*.rtf)|*.rtf|Word Document (*.docx)|*.docx|"
                "All files (*.*)|*.*"
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

        if target.suffix.lower() in EXPORT_ONLY_SUFFIXES:
            # A typed .pdf/.odt/.epub/... would otherwise write Markdown text
            # into a file other apps cannot open. Route Pandoc-capable targets
            # to File > Export; refuse the rest with a pointer to the type list.
            export_format = self._export_route_for_suffix(target.suffix)
            if export_format is not None:
                answer = self._show_message_box(
                    f"QUILL saves Markdown, Word, HTML, RTF, and text directly. "
                    f"{target.suffix} goes through Export instead, which converts "
                    "with Pandoc. Open Export now?",
                    "Use Export for this format",
                    wx.ICON_QUESTION | wx.YES_NO | wx.YES_DEFAULT,
                )
                if answer == wx.YES:
                    self.export_document(export_format)
                return
            self._show_message_box(
                f"QUILL cannot save to {target.suffix}. Choose Markdown, Word, "
                "HTML, RTF, or text in the Save as type list.",
                "Format not supported",
                wx.ICON_INFORMATION | wx.OK,
            )
            return

        # Optional pre-save proofread (off by default), after the user has chosen
        # the destination but before the file is written.
        if getattr(self.settings, "spell_check_before_save", False):
            self.open_spell_check_dialog()
        self.document.set_text(self.editor.GetValue())
        if self.document.modified and self.document.path is not None:
            backup_document(self.document)
        try:
            self._write_document_to_disk(self.document, target)
        except OSError as error:
            self._show_message_box(
                f"Could not save {target.name}: {error}",
                "Save file as",
                wx.ICON_ERROR | wx.OK,
            )
            self._set_status(f"Could not save {target.name}")
            return
        # FEAT-19: restart the watcher on the new path so our save is the baseline.
        self._stop_external_change_watcher()
        self._start_external_change_watcher()
        self._load_persistent_undo_state(target, self.document.text)
        self._record_recent(target)
        # Persist this document's bookmarks + cursor position under the new path
        # (keyed on target directly so it is correct regardless of when the
        # document's own path attribute is updated).
        _bm_key = DocumentMemory.key_for(target)
        if _bm_key:
            try:
                self._doc_memory.set_bookmarks(_bm_key, self._bookmarks)
                self._doc_memory.set_last_position(_bm_key, self.editor.GetInsertionPoint())
                self._inline_vault().set_notes(_bm_key, self._inline_notes)
            except Exception:  # noqa: BLE001 - persistence is best-effort
                pass
        self._refresh_title()
        self._refresh_sessions_menu()
        self._set_status(f"Saved as {target.name} ({format_label_for_path(target)})")
        self._announce_save_as_conversion(target)

    def _announce_save_as_conversion(self, target: Path) -> None:
        """Speak what a converting Save As actually did.

        The file on disk is now Word/RTF/HTML, but the editing surface still
        holds QUILL's canonical text and every subsequent save re-converts it.
        That model is deliberate; this makes it audible instead of silent.
        Verbatim formats (.md/.txt/unknown) stay quiet — the status line
        already names them and nothing was converted.
        """
        if target.suffix.lower() not in ({".docx", ".rtf"} | HTML_SUFFIXES):
            return
        label = format_label_for_path(target)
        self._announce(
            f"Saved as {target.name}, {label} format. You are still editing "
            f"QUILL text; each save converts it to {label}."
        )

    def _reload_in_place(self, target: Path) -> None:
        """Replace the current tab with ``target`` reopened in its natural surface.

        The file is read *before* the current tab is disturbed, so a read failure
        leaves the live document intact. On success the current page is removed
        without spawning a placeholder tab and the freshly typed surface is built
        by the shared open-finish path.
        """
        suffix = target.suffix.lower()
        try:
            result = read_open_document(target, suffix, docx_engine=self._docx_read_engine())
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
            defaultFile=self._suggested_save_basename(),
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save as plain text") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())

        if self._save_plain_text_honoring_formatting(target, self.editor.GetValue()):
            self._record_recent(target)

    def _save_plain_text_honoring_formatting(self, target: Path, text: str) -> bool:
        """Save *text* as plain text at *target*, honouring the
        ``plain_text_with_formatting`` policy when the document carries hidden
        formatting. Writes/refreshes or removes the ``<name>.illumination`` sidecar
        as appropriate. Returns ``False`` only if the user cancelled."""
        from quill.io.illumination import (
            build_illumination,
            illumination_path_for,
            markup_has_formatting,
            write_illumination,
        )

        link_style = str(getattr(self.settings, "plain_text_link_style", "text_url"))

        def _write_plain() -> None:
            plain_doc = Document(
                text=text, path=target, modified=True, encoding="utf-8", line_ending="\n"
            )
            write_plain_text_document(plain_doc, target, link_style=link_style)

        def _illuminate() -> None:
            _write_plain()
            sidecar = write_illumination(target, build_illumination(text))
            self._set_status(
                f"Saved plain text to {target.name} with an Illumination ({sidecar.name})"
            )

        def _drop_and_clear_sidecar() -> None:
            _write_plain()
            stale = illumination_path_for(target)
            try:
                if stale.is_file():
                    stale.unlink()
            except OSError:
                pass
            self._set_status(f"Saved plain text to {target.name} (formatting not kept)")

        if not markup_has_formatting(text):
            _write_plain()
            self._set_status(f"Saved plain text to {target.name}")
            return True

        policy = str(getattr(self.settings, "plain_text_with_formatting", "ask"))
        if policy == "illuminate":
            _illuminate()
            return True
        if policy == "plain":
            _drop_and_clear_sidecar()
            return True

        choice = self._ask_plain_text_formatting_choice()
        if choice is None:
            return False
        if choice == "keep":
            # Let the user pick a format that carries formatting (.md / .rtf / .docx).
            self.save_file_as()
            return True
        if choice == "illuminate":
            _illuminate()
            return True
        _drop_and_clear_sidecar()
        return True

    def _ask_plain_text_formatting_choice(self) -> str | None:
        """Offer keep / illuminate / plain; returns 'keep' | 'illuminate' | 'plain'
        or ``None`` if the user cancelled."""
        wx = self._wx
        choices = [
            "Keep my formatting — save as Markdown, Word, or RTF instead",
            "Save plain text plus an Illumination sidecar (keeps formatting in QUILL)",
            "Save plain text only — remove the formatting",
        ]
        with wx.SingleChoiceDialog(
            self.frame,
            (
                "This document has formatting (fonts, colours, alignment) that a plain "
                "text file cannot hold. What would you like to do?"
            ),
            "Save as plain text",
            choices,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save as plain text") != wx.ID_OK:
                return None
            return ("keep", "illuminate", "plain")[dialog.GetSelection()]

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

                    docx_engine = self._docx_read_engine()

                    def _worker(_progress: object) -> tuple[object, object]:
                        return read_open_document(
                            selected_path, suffix, word_mode=word_mode, docx_engine=docx_engine
                        )

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
        # #187: the "Open from URL" dialog's own close-out queues a CallAfter
        # that restores focus to the *previous* tab's editor (captured before
        # this new tab existed). Queue a second, correctly-bound CallAfter so
        # it runs after that stale one and wins, landing focus on the new
        # editor -- otherwise it never receives its first SetFocus and its
        # content stays visually blank until the user manually tabs into it.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after) and hasattr(self, "editor"):
            call_after(self.editor.SetFocus)

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
            docx_engine = self._docx_read_engine()
            self._run_background_task(
                f"Opening {Path(remote_path).name}",
                lambda _p: read_open_document(Path(local_path), suffix, docx_engine=docx_engine),
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
        # #187: the "Open from Remote" dialog's own close-out queues a
        # CallAfter that restores focus to the *previous* tab's editor
        # (captured before this new tab existed). Queue a second,
        # correctly-bound CallAfter so it runs after that stale one and
        # wins, landing focus on the new editor -- otherwise it never
        # receives its first SetFocus and its content stays visually blank
        # until the user manually tabs into it.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after) and hasattr(self, "editor"):
            call_after(self.editor.SetFocus)

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
        try:
            autosave_document(self.document, self.session_id)
        except Exception:  # noqa: BLE001 - autosave must never break editing
            pass
        # Rich tabs also snapshot the RTF bytes: TOM formatting never changes
        # the plain text, so a text-only snapshot would lose formatting in a
        # crash. Best-effort by the same contract as the text snapshot.
        rich_payload = self._rich_autosave_payload()
        if rich_payload is not None:
            try:
                from quill.core.autosave import autosave_rich_document

                autosave_rich_document(self.document, self.session_id, rich_payload)
            except Exception:  # noqa: BLE001 - autosave must never break editing
                pass
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
        from quill.ui.palette import CommandPaletteDialog

        dialog = CommandPaletteDialog(
            self.frame,
            self.commands,
            self.features,
            announce_fn=self._announce,
            on_help=self.show_help_on_control,
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

    #: Informational, side-effect-free commands where a rapid second press means
    #: "show me what you just said" rather than "do it again". Re-running any of
    #: these is harmless, so hijacking the second press to open the Spoken Echo
    #: loses nothing. The dedicated Echo key works for every announcement; this
    #: set only governs the optional double-press shortcut.
    _ECHO_DOUBLE_PRESS_COMMANDS = frozenset({
        "format.describe_formatting",
        "document.summary",
        "help.context_help",
        "view.announce_contrast",
    })

    #: Maximum gap (seconds) between two presses to count as a double-press.
    _ECHO_DOUBLE_PRESS_WINDOW = 0.5

    def _run_command(self, command_id: str) -> None:
        if self._maybe_echo_on_double_press(command_id):
            return
        try:
            self.commands.run(command_id)
        except Exception:  # noqa: BLE001
            self._set_status(f"Command failed: {command_id}")

    def _maybe_echo_on_double_press(self, command_id: str) -> bool:
        """Return True (and open the Echo) on a rapid second press of an
        informational command, when the double-press shortcut is enabled.

        Always records the press for the next comparison. Returns False — letting
        the command run normally — for non-informational commands, when the
        setting is off, or on a first/slow press.
        """
        now = time.monotonic()
        previous = getattr(self, "_last_echo_command", None)
        previous_at = getattr(self, "_last_echo_command_at", 0.0)
        self._last_echo_command = command_id
        self._last_echo_command_at = now
        if command_id not in self._ECHO_DOUBLE_PRESS_COMMANDS:
            return False
        enabled = bool(
            getattr(getattr(self, "settings", None), "spoken_echo_on_double_press", True)
        )
        if not enabled:
            return False
        if previous == command_id and (now - previous_at) <= self._ECHO_DOUBLE_PRESS_WINDOW:
            # Reset so a third press re-runs the command rather than re-opening.
            self._last_echo_command = None
            self.show_spoken_echo()
            return True
        return False

    def create_sticky_note(self) -> None:
        if self._safe_mode:
            self._set_status("Sticky notes are unavailable in safe mode")
            return
        from quill.ui.sticky_notes import StickyNoteEditorDialog

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
        from quill.ui.sticky_notes import StickyNotesVaultDialog

        StickyNotesVaultDialog(self.frame).show_modal()
        self._set_status("Closed sticky notes vault")

    def _start_model_lifecycle(self) -> None:
        """Build the model-lifecycle manager from settings and start the idle sweep.

        Makes the Performance settings real: the speech, TTS, and LLM model holders
        register with ``lifecycle_service`` around their load/unload, and a repeating
        timer unloads models left idle past the threshold. Low-resource mode caps the
        engines loaded at once. All model work stays off the UI thread.
        """
        from quill.core import lifecycle_service
        from quill.core.model_lifecycle import should_auto_low_resource
        from quill.core.speech.service import detect_total_ram_gb

        ram = detect_total_ram_gb()
        low_res = bool(getattr(self.settings, "low_resource_mode", False))
        minutes = int(getattr(self.settings, "idle_unload_minutes", 10))
        lifecycle_service.configure(
            low_resource_mode=low_res, idle_unload_minutes=minutes, total_ram_gb=ram
        )
        # Accessible one-time (per-session) notice when low-resource mode auto-enables
        # on a small machine, so the behaviour is never silent (PRD 5.25f).
        if not low_res and should_auto_low_resource(ram):
            self._announce(
                "Low-resource mode is on because this computer has limited memory. "
                "AI and speech load one model at a time to save memory."
            )
        self._start_lifecycle_sweep_timer()

    def _start_lifecycle_sweep_timer(self) -> None:
        """Start (or restart) the repeating timer that unloads idle models off-thread."""
        from quill.core import lifecycle_service

        self._stop_lifecycle_sweep_timer()
        minutes = int(getattr(self.settings, "idle_unload_minutes", 10))
        if minutes <= 0:
            return  # idle-unload disabled; low-resource eviction still works on load
        wx = self._wx
        self._lifecycle_timer = wx.Timer(self.frame)
        self.frame.Bind(
            wx.EVT_TIMER,
            lambda _e: self._task_manager.submit("lifecycle-idle-sweep", lifecycle_service.sweep),
            self._lifecycle_timer,
        )
        # Poll about twice per idle window (clamped 30 s - 5 min) so an idle model is
        # freed reasonably promptly without busy-polling.
        interval_ms = max(30, min(300, minutes * 30)) * 1000
        self._lifecycle_timer.Start(interval_ms)

    def _stop_lifecycle_sweep_timer(self) -> None:
        """Stop the idle-sweep timer if running (idempotent; safe at shutdown)."""
        timer = getattr(self, "_lifecycle_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - a dead C++ timer must not block shutdown
                pass
            self._lifecycle_timer = None

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
            return (
                "QUILL can't reach a local AI server. If you use Ollama, start it "
                "(run 'ollama serve') and try again. If you use a different local AI "
                "such as LM Studio or GPT4All, choose the Custom provider in AI Hub "
                "and enter its OpenAI-compatible endpoint."
            )
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
        # _flush_pending_menu_refresh() may run during __init__ or while
        # the frame is still being built; guard against the menu bar
        # being absent (real wx: methods exist; stub _Frame: not).
        get_menu_bar = getattr(self.frame, "GetMenuBar", None)
        if not callable(get_menu_bar):
            return
        menu_bar = get_menu_bar()
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

    def post_to_mastodon(self) -> None:
        """Compose and publish the selection (or the whole document) to Mastodon.

        Grabs the editor selection if there is one, otherwise the whole document,
        then opens the compose dialog. If no account is set up yet, the accounts
        manager is offered first. Disabled in Safe Mode.
        """
        if self._safe_mode:
            self._announce_result("Mastodon posting is disabled in Safe Mode.")
            return
        from quill.core.mastodon import accounts as _accounts
        from quill.ui.mastodon_dialogs import (
            MastodonAccountsDialog,
            MastodonComposeDialog,
        )

        accounts = _accounts.list_accounts()
        if not accounts:
            self._announce_result("Add a Mastodon account to post.")
            MastodonAccountsDialog(self.frame, announce=self._announce_result).show()
            accounts = _accounts.list_accounts()
            if not accounts:
                return
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        selected = editor.GetStringSelection()
        text = selected if selected.strip() else editor.GetValue()
        dialog = MastodonComposeDialog(
            self.frame,
            initial_text=text,
            accounts=accounts,
            default_account_id=_accounts.default_account_id(),
            announce=self._announce_result,
            spell_review=self._spell_review_textctrl,
        )
        if dialog.show() == self._wx.ID_OK:
            url = dialog.posted_url or ""
            self._announce_result("Posted to Mastodon." + (f" {url}" if url else ""))

    def manage_mastodon_accounts(self) -> None:
        """Open the Mastodon account manager (add, remove, set default)."""
        from quill.ui.mastodon_dialogs import MastodonAccountsDialog

        MastodonAccountsDialog(self.frame, announce=self._announce_result).show()

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
            Path(__file__).resolve().parent.parent.parent / "docs" / "user guide" / "userguide.md",
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
        from quill.core.compliance import render_full_third_party_notices

        project_root = self._project_root_path()
        pyproject_path = self._pyproject_path()
        if not pyproject_path.exists():
            notices = (
                "# Third-Party Notices\n\nDependency metadata is not available in this build.\n"
            )
        else:
            notices = render_full_third_party_notices(pyproject_path, project_root)
        self._create_document_tab(
            Document(text=notices, path=None, modified=False),
            select=True,
        )
        self._location_ring = LocationRing()
        self._location_ring.record(0)
        self._refresh_title()
        self._set_status("Opened third-party notices")

    def _project_root_path(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent

    def _pyproject_path(self) -> Path:
        return self._project_root_path() / "pyproject.toml"

    def show_about_quill(self) -> None:
        from quill.core.about_info import gather_about_info
        from quill.ui.info_pages import show_about_quill_native

        about_info = gather_about_info()
        show_about_quill_native(
            self.frame,
            self._wx,
            about_info,
            self.open_third_party_notices,
            self._show_modal_dialog,
        )
        self._set_status("Opened About Quill")

    def show_whisperer_about_page(self) -> None:
        from quill.ui.info_pages import show_whisperer_about_native

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
        principles_rows = [
            (
                "Accessibility first",
                "Screen-reader-first design with clear headings and keyboard flow.",
            ),
            ("Offline-friendly", "Strong local capabilities before cloud dependencies."),
            ("Safe rollout", "Feature flags and staged onboarding for predictable adoption."),
            ("Transparent status", "Status pages and notifications for every async operation."),
        ]
        show_whisperer_about_native(
            self.frame, self._wx, roadmap_rows, principles_rows, self._show_modal_dialog
        )
        self._set_status("Opened About BITS Whisperer")

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
        set_accessible_name(chooser, "External tools")
        chooser.SetSelection(0 if choices else wx.NOT_FOUND)
        details = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(details, "Tool details")
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

    def _convert_file_default_output_dir(self) -> str:
        """Best initial output folder for the Convert File dialog.

        Priority: the folder remembered from the last conversion, then the
        general file-dialog default directory.
        """

        remembered = getattr(self.settings, "convert_file_last_output_dir", "")
        if remembered and Path(remembered).is_dir():
            return remembered
        return self._file_dialog_default_dir()

    def _remember_convert_file_choices(self, output_dir: Path, output_token: str) -> None:
        """Persist the Convert File output folder and format for next time."""

        from quill.core.settings import save_settings

        self.settings.convert_file_last_output_dir = str(output_dir)
        self.settings.convert_file_last_format = output_token
        save_settings(self.settings)

    def _offer_pandoc_download(self, feature: str) -> bool:
        """When a feature needs Pandoc and it isn't present, offer the on-demand
        download (footprint unbundle). Returns True if the user started it.

        On Windows QUILL fetches the official pinned build; elsewhere it points
        the user at their package manager. Either way the conversion is retried
        by the user once Pandoc is ready.
        """
        wx = self._wx
        from quill.core.pandoc_install import pandoc_install_supported

        if pandoc_install_supported():
            result = self._show_message_box(
                (
                    f"{feature} needs Pandoc, which is downloaded on demand to keep "
                    "QUILL's install small. Download the official Pandoc build now "
                    "(about 45 MB)? It is verified and installed automatically."
                ),
                feature,
                wx.ICON_INFORMATION | wx.YES_NO,
            )
            if result == wx.YES:
                self.download_pandoc()
                return True
            # Declining must not look like the command silently did nothing
            # (#798 review): leave a status explaining why it stopped.
            self._set_status(f"{feature} needs Pandoc; nothing was done.")
            return False
        result = self._show_message_box(
            (
                f"{feature} needs Pandoc. Install it with your package manager "
                "(for example: brew install pandoc), then try again. Copy the "
                "install command now?"
            ),
            feature,
            wx.ICON_INFORMATION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if result == wx.YES and self._copy_to_clipboard(copyable_install_command("pandoc")):
            self._set_status("Copied Pandoc install command")
        else:
            self._set_status(f"{feature} needs Pandoc; nothing was done.")
        return False

    #: Sources MarkItDown can read and the Markdown-ish outputs it can produce.
    _MARKITDOWN_SOURCE_SUFFIXES = frozenset({".docx", ".pptx", ".xlsx", ".xls", ".pdf"})
    _MARKITDOWN_OUTPUT_TOKENS = frozenset({"gfm", "commonmark", "markdown", "plain"})

    @classmethod
    def _markitdown_convert_applies(cls, request: object) -> bool:
        """Whether the MarkItDown engine can honestly serve this conversion.

        MarkItDown is a one-way reader: Office/PDF in, Markdown out. Anything
        else must go to Pandoc, and the caller says so instead of silently
        substituting an engine the user did not pick.
        """
        source = Path(getattr(request, "source_path", ""))
        token = str(getattr(request, "output_token", ""))
        return (
            source.suffix.lower() in cls._MARKITDOWN_SOURCE_SUFFIXES
            and token in cls._MARKITDOWN_OUTPUT_TOKENS
        )

    def convert_file(self) -> None:
        """File > Convert File: convert any document to another format via Pandoc."""

        wx = self._wx
        status = get_external_tool_status("pandoc")
        if not status.installed:
            if self._offer_pandoc_download("Convert File"):
                # Download runs in the background; the user re-runs Convert File
                # once Pandoc is ready (the status announcement tells them so).
                return
            self._set_status("Convert File unavailable until Pandoc is installed")
            return

        from quill.core import convert_formats
        from quill.ui.convert_file_dialog import ConvertFileDialog

        dialog = ConvertFileDialog(
            self.frame,
            default_output_dir=self._convert_file_default_output_dir(),
            default_format=getattr(self.settings, "convert_file_last_format", "gfm") or "gfm",
            show_modal_fn=self._show_modal_dialog,
        )
        request = dialog.prompt()
        if request is None:
            self._set_status("Convert File cancelled")
            return

        target = request.output_path
        if target.exists():
            confirm = self._show_message_box(
                f"{target.name} already exists in that folder. Replace it?",
                "Convert File",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            if confirm != wx.YES:
                self._set_status("Convert File cancelled (file already exists)")
                return

        # Braille sources take QUILL's own path: Pandoc has no braille reader,
        # but the auto-detecting back-translation (braille_detect) does exactly
        # this job -- detect the code, back-translate, write the chosen format.
        if request.source_path.suffix.lower() in convert_formats.BRAILLE_INPUT_SUFFIXES:
            self._convert_brf_file_request(request, target)
            return

        engine = getattr(request, "engine", "auto")
        if engine == "markitdown" and not self._markitdown_convert_applies(request):
            proceed = self._show_message_box(
                "MarkItDown reads Word, PowerPoint, Excel, or PDF into Markdown "
                "or plain text only. Convert with Pandoc instead?",
                "Convert File",
                wx.ICON_QUESTION | wx.YES_NO | wx.YES_DEFAULT,
            )
            if proceed != wx.YES:
                self._set_status("Convert File cancelled")
                return
            engine = "pandoc"

        if engine == "markitdown":
            self._set_status(f"Converting {request.source_path.name} with MarkItDown...")
            try:
                from quill.io.markitdown_bridge import convert_with_markitdown

                text = convert_with_markitdown(request.source_path)
                with target.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
            except (ImportError, ValueError, RuntimeError, OSError) as error:
                self._show_message_box(
                    f"Conversion failed: {error}",
                    "Convert File",
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Conversion failed")
                return
        else:
            from_format = convert_formats.reader_for_path(str(request.source_path))
            self._set_status(
                f"Converting {request.source_path.name} to "
                f"{convert_formats.label_for(request.output_token)}..."
            )
            try:
                convert_file_with_pandoc(
                    request.source_path,
                    target,
                    from_format=from_format,
                    to_format=request.output_token,
                    tool_status=status,
                    resolve_writer=False,
                )
            except (PandocUnavailableError, PandocConversionError, ValueError) as error:
                self._show_message_box(
                    f"Conversion failed: {error}",
                    "Convert File",
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Conversion failed")
                return

        self._remember_convert_file_choices(request.output_dir, request.output_token)
        self._record_recent(target)
        self._announce(f"Converted to {target.name}")

        if request.action == "open":
            self.open_file(path=target)
            self._set_status(f"Converted and opened {target.name}")
            return

        # Convert File (save) action: offer to open the result when it is a
        # text format QUILL can edit; binary outputs just land on disk.
        if convert_formats.is_text_output(request.output_token):
            if (
                self._show_message_box(
                    f"Conversion complete. Open {target.name} now?",
                    "Convert File",
                    wx.ICON_QUESTION | wx.YES_NO | wx.YES_DEFAULT,
                )
                == wx.YES
            ):
                self.open_file(path=target)
        self._set_status(f"Converted to {target}")

    # Backwards-compatible alias: the External Tools dialog re-opens the
    # conversion UI after a successful Pandoc install.
    def open_pandoc_wizard(self) -> None:
        self.convert_file()

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
        # feedback_hub ships with QUILL (the [feedback] extra / bundled
        # runtime), so the direct-submission dialog is the one and only form
        # (the old built-in browser form was removed once bundling landed).
        from quill.core.feedback_token import github_token_present

        # No token at all (neither a user token nor a bundled one -- e.g. a build
        # that shipped an empty bundled token): don't open a form that can only
        # dead-end at submit. Offer the online form up front, and say how to fix
        # it for good. This is the "No token in the field" P0 made non-fatal.
        if not github_token_present():
            self._report_bug_online_fallback(
                "Direct bug reporting isn't set up in this build. You can still "
                "file the report on the online support form, or add your own "
                "GitHub token in Settings to enable in-app reporting."
            )
            return
        # A failure must still not strand the user: fall back to the online form.
        try:
            self._report_bug_via_hub()
        except Exception:  # noqa: BLE001 - never strand the user without a path
            import logging

            logging.getLogger(__name__).warning("feedback_hub bug report failed", exc_info=True)
            self._report_bug_online_fallback(
                "The issue form could not be submitted. You can file the report "
                "on the online support form instead."
            )

    def _report_bug_online_fallback(self, reason: str) -> None:
        """Open (and copy) the online support-form URL with an actionable, spoken
        message, so a missing/failed token never leaves the user with no path."""
        import webbrowser

        issue_url = build_support_issue_url(
            {"summary": f"Bug report: {self.document.name}", "body": ""},
            source_app="Quill",
            version=__version__ or "0.0.0",
            platform_label=str(collect_environment_info()["platform"]),
        )
        opened = False
        try:
            opened = bool(webbrowser.open(issue_url))
        except Exception:  # noqa: BLE001 - a browser failure falls back to the clipboard
            opened = False
        self._copy_to_clipboard(issue_url)
        tail = (
            "Your browser is opening it now; the link is also on your clipboard."
            if opened
            else "The link is on your clipboard -- paste it into your browser."
        )
        message = f"{reason}\n\n{tail}"
        self._announce(message)
        self._show_message_box(message, "Report a Bug", self._wx.OK | self._wx.ICON_INFORMATION)

    def _report_bug_via_hub(self) -> None:
        from feedback_hub import load_schema
        from feedback_hub.wx_dialog import FeedbackDialog

        from quill.core.feedback_token import effective_github_token

        schema_path = Path(__file__).parent.parent / "core" / "schemas" / "feedback.json"
        dlg = FeedbackDialog(
            self.frame,
            schema=load_schema(schema_path),
            app_version=__version__ or "0.0.0",
            github_token=effective_github_token(),
        )
        result = self._show_modal_dialog(dlg, "Report an Issue")
        dlg.Destroy()
        if result == self._wx.ID_OK:
            self._record_notification("Submitted feedback via feedback hub", "support")

    def _review_diagnostics_export(self) -> bool | None:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Review Diagnostics Export", size=(780, 560))
        root = wx.BoxSizer(wx.VERTICAL)
        include_paths = wx.CheckBox(dialog, label="Include plain file paths in the bundle")
        review = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(review, "Diagnostics review")
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
        set_accessible_name(logs_field, "Logs folder")
        logs_field.SetValue(str(app_data_dir() / "logs"))
        root.Add(logs_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(dialog, label="Diagnostics folder"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        diagnostics_field = wx.TextCtrl(dialog, style=wx.TE_READONLY)
        set_accessible_name(diagnostics_field, "Diagnostics folder")
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

    def _ensure_glow_enabled(self) -> bool:
        """Gate every GLOW command behind the Experimental opt-in.

        GLOW ships as an experimental feature: it runs only when both the
        Experimental master switch and the GLOW checkbox are on (Preferences >
        Experimental). Commands stay in the palette so they are discoverable;
        invoking one while gated explains exactly how to turn GLOW on — the
        same pattern as Read Document in Browser.
        """
        if self._feature_enabled("core.glow"):
            return True
        wx = self._wx
        self._show_message_box(
            "GLOW is an experimental feature and is currently turned off.\n\n"
            "To enable it, open Preferences > Experimental, tick 'Enable "
            "experimental features', then tick 'GLOW accessibility review and "
            "repair'. It takes effect as soon as you apply Settings - no "
            "restart needed.",
            "GLOW (Experimental)",
            wx.ICON_INFORMATION | wx.OK,
        )
        return False

    def glow_audit_document(self) -> None:
        if not self._ensure_glow_enabled():
            return
        markup = self._current_markup_context()
        text = self.editor.GetValue()
        report = build_audit_report(self.document.name, text, markup, "current document")
        self._create_named_scratch_tab(f"GLOW Audit - {self.document.name}", report)
        self._set_status(f"Opened GLOW audit for {self.document.name}")

    def glow_audit_selection(self) -> None:
        if not self._ensure_glow_enabled():
            return
        text, _start, _end, scope_label = self._glow_scope()
        markup = self._current_markup_context()
        report = build_audit_report(self.document.name, text, markup, scope_label)
        self._create_named_scratch_tab(f"GLOW Audit - {scope_label.title()}", report)
        self._set_status(f"Opened GLOW audit for {scope_label}")

    def glow_fix_document(self) -> None:
        if not self._ensure_glow_enabled():
            return
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
        if not self._ensure_glow_enabled():
            return
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
        from quill.core.accessibility_agent import summarize_plan
        from quill.ui.assistant_tools import AccessibilityAgentDialog

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
        exact = len(starts) > 1
        words_per_page = getattr(self.settings, "page_estimate_words_per_page", 300)
        total_pages = len(starts) if exact else estimate_page_count(text, words_per_page)
        prompt = (
            f"Enter a page number (1-{total_pages}):"
            if exact
            else (
                f"Enter an estimated page number (1-{total_pages}). This is "
                "based on word count, not an exact printed page count:"
            )
        )
        with wx.TextEntryDialog(
            self.frame,
            prompt,
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
        if exact:
            target = page_start_for_number(text, page_number)
        else:
            target = estimate_page_start_for_number(text, page_number, words_per_page)
        if target is None:
            self._show_message_box(
                f"Document has only {total_pages} page(s).",
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
        markup_kind = self._effective_markup_kind()
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
            prefix = (
                f"Moved to {label}, H{context.level}, {context.ordinal} of {context.total}: {title}"
            )
        else:
            prefix = f"Moved to {label}"
        self._announce_navigation_move(prefix, target)

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
        self._announce_navigation_move(f"Moved to {label}", target)

    def _announce_navigation_move(self, prefix: str, target: int) -> None:
        detail = str(getattr(self.settings, "browse_mode_move_detail", "position")).strip().lower()
        if detail == "none":
            return
        line, column = line_column_for_position(self.editor.GetValue(), target)
        if detail == "line":
            message = f"{prefix} at line {line}"
        else:
            message = f"{prefix} at line {line}, column {column}"
        self._quill_feedback(message, status_message=message, sound_kind="move")

    def open_outline_navigator(self) -> None:
        if self.document.path is not None and self.document.path.suffix.lower() == ".epub":
            self.open_epub_navigator()
            return
        markup_kind = self._effective_markup_kind()
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
        context = self._quick_nav_panel_context()
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
            set_accessible_name(search, "Type to filter")
            inner.Add(search, 0, wx.ALL | wx.EXPAND, 8)
            summary = nav_type_summary(items)
            category_labels = [f"All ({len(items)})"] + [
                f"{name} ({count})" for name, count in summary
            ]
            category_values: list[str | None] = [None] + [name for name, _ in summary]
            category_box = wx.ListBox(dialog, choices=category_labels)
            set_accessible_name(category_box, "Category")
            category_box.SetSelection(0)
            inner.Add(category_box, 0, wx.ALL | wx.EXPAND, 8)
            results = wx.ListBox(dialog)
            set_accessible_name(results, "Results")
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
        markup_kind = self._effective_markup_kind()
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
        set_accessible_name(list_box, "Headings")
        preview = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(preview, "Heading preview")
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
            # #303: surface the duplicate-H1 warning only when the user
            # has explicitly opted in. Defaults keep the historical
            # behavior (only "must start at H1" and "skipped level"
            # issues fire) so users who deliberately write multi-H1
            # works are not interrupted by a new warning.
            issues = validate_heading_sequence(
                working,
                require_single_h1=getattr(
                    self.settings,
                    "heading_organizer_warn_duplicate_h1",
                    False,
                ),
            )
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
        if self._effective_markup_kind() != "yaml":
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

    _LANGUAGE_AUTO_LABEL = "Auto-detect from file"

    def set_document_language(self, language: str | None = None) -> None:
        """Set (or clear) the language profile for the current document tab.

        ``language`` may be a profile name, ``"Plain text"``, the auto-detect
        label (clears the user override), or None to prompt. The choice is
        tab-only: it is not remembered when the file is reopened. Setting a
        language never renames the file — when the chosen language's extension
        doesn't match, a Save As hint is announced.
        """
        wx = self._wx
        tab = getattr(self, "_current_tab", None)
        if tab is None:
            return
        auto = self._LANGUAGE_AUTO_LABEL
        if language is not None:
            choice_name = language
        else:
            names = [auto] + [p.name for p in all_profiles()] + ["Plain text"]
            dlg = wx.SingleChoiceDialog(
                self.frame,
                "Select the language profile for this document. This changes editing "
                "behaviour only; it does not rename the file.",
                "Set Document Language",
                names,
            )
            if getattr(tab, "_language_profile_pinned", False):
                current = getattr(tab, "_language_profile", None)
                preselect = current.name if current else "Plain text"
            else:
                preselect = auto
            try:
                dlg.SetSelection(names.index(preselect))
            except ValueError:
                pass
            if self._show_modal_dialog(dlg, "Set Document Language") != wx.ID_OK:
                return
            choice_name = dlg.GetStringSelection()

        if choice_name == auto:
            tab._language_profile_pinned = False
            tab._language_profile = get_profile_for_path(tab.document.path)
            self._last_language_suggestion = None  # allow auto-detection to re-suggest
            self._apply_statusbar_layout()
            self._request_menu_refresh()
            self._set_status_quiet("Language: auto-detect from file")
            self._announce("Language set to auto-detect from file")
            return

        if choice_name == "Plain text":
            profile: LanguageProfile | None = PLAIN_PROFILE
        else:
            profile = get_profile_by_name(choice_name)
            if profile is None:
                self._set_status(f"Unknown language: {choice_name}")
                return
        tab._language_profile = profile
        tab._language_profile_pinned = True
        self._note_language_session_use(profile.name)
        self._apply_statusbar_layout()
        self._request_menu_refresh()
        hint = self._save_as_hint_for_language(profile)
        message = f"Language set to {profile.name}." + (f" {hint}" if hint else "")
        self._set_status(message)

    def _save_as_hint_for_language(self, profile: object) -> str:
        """Save As tip when the pinned language's extension doesn't match the file.

        Returns an empty string when no hint applies (no path, or the current
        extension already matches the language).
        """
        exts = tuple(getattr(profile, "extensions", ()) or ())
        if not exts:
            return ""
        path = self.document.path
        current_suffix = path.suffix.lower() if path is not None else ""
        if current_suffix in exts:
            return ""
        name = getattr(profile, "name", "this language")
        where = current_suffix or "unsaved"
        return (
            f"Tip: the file is still {where}; use File, Save As to save it as a "
            f"{name} ({exts[0]}) file."
        )

    def _on_document_language_menu(self, event: object) -> None:
        """Handle the Format > Document Language radio submenu (#181)."""
        name = getattr(self, "_language_menu_item_ids", {}).get(event.GetId())  # type: ignore[attr-defined]
        if name is None:
            return
        self.set_document_language(self._LANGUAGE_AUTO_LABEL if name == "" else name)

    def _refresh_language_menu_radio(self, menu_bar: object) -> None:
        """Tick the radio item for the current tab's effective language."""
        ids = getattr(self, "_language_menu_item_ids", None)
        if not ids:
            return
        tab = getattr(self, "_current_tab", None)
        if tab is not None and getattr(tab, "_language_profile_pinned", False):
            profile = getattr(tab, "_language_profile", None)
            target = profile.name if profile else "Plain text"
        else:
            target = ""  # Auto-detect
        for item_id, name in ids.items():
            item = menu_bar.FindItemById(item_id)
            if item is not None and item.IsCheckable():
                item.Check(name == target)

    def change_display_language(self, language: str | None = None) -> None:
        """Choose the language for QUILL's menus, dialogs, and messages (#i18n).

        ``language`` may be passed directly (a locale tag, or ``""`` for the OS
        default) to set the display language without prompting; otherwise a
        chooser lists every language that has a compiled translation installed,
        plus "System default". The choice is saved to settings and applied to
        runtime announcements immediately; menus and already-built dialogs pick
        it up after a restart.
        """
        from quill.core.i18n import (
            _,
            available_languages,
            init_locale,
            language_display_name,
        )

        wx = self._wx
        available = available_languages()

        if language is None:
            if not available:
                self._show_message_box(
                    _(
                        "QUILL is currently available in English only. When community "
                        "translations are installed, they will appear here so you can "
                        "switch the display language."
                    ),
                    _("No translations installed yet"),
                    wx.OK | wx.ICON_INFORMATION,
                )
                return
            tags = [""] + available
            labels = [_("System default")] + [language_display_name(t) for t in available]
            with wx.SingleChoiceDialog(
                self.frame,
                _("Choose the language for menus, dialogs, and messages:"),
                _("Change Display Language"),
                labels,
            ) as dlg:
                current = getattr(self.settings, "language", "") or ""
                try:
                    dlg.SetSelection(tags.index(current))
                except ValueError:
                    dlg.SetSelection(0)
                if self._show_modal_dialog(dlg, "Change Display Language") != wx.ID_OK:
                    return
                tag = tags[dlg.GetSelection()]
        else:
            tag = language.strip()

        self.settings.language = tag
        save_settings(self.settings)
        self._active_language = init_locale(tag or None)
        name = _("System default") if not tag else language_display_name(tag)
        message = _(
            "Display language set to {name}. Restart QUILL to update all menus and dialogs."
        ).format(name=name)
        self._set_status(message)

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
        markup_kind = self._effective_markup_kind()
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
        F6 back out.

        The document tab bar is only a real, focusable wx.Notebook when the
        tab control is visible (the hidden Simplebook has no tab strip), so it
        joins the rotation only then — otherwise F6 would "land" on an
        unreachable region. This is the fix for the tab bar being unreachable
        by F6 and by the JAWS cursor when Show Tab Control is on."""
        labels = ["Editor"]
        reveal = getattr(self, "_reveal_pane", None)
        if reveal is not None and reveal.panel.IsShown():
            labels.append("Reveal Codes")
        if self._tab_control_visible:
            try:
                has_tabs = self.notebook.GetPageCount() > 0
            except (AttributeError, RuntimeError):
                has_tabs = False
            if has_tabs:
                labels.append("Document Tabs")
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
        reveal = getattr(self, "_reveal_pane", None)
        while win is not None:
            if reveal is not None and "Reveal Codes" in regions and win is reveal.panel:
                return "Reveal Codes"
            if preview_ctrl is not None and win is preview_ctrl and "Preview" in regions:
                return "Preview"
            if "Document Tabs" in regions and win is self.notebook:
                return "Document Tabs"
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
            # Flag the F6 landing so the status-bar cell focus announces the
            # "Status bar" region name once on entry; arrow moves within the bar
            # clear the flag and speak only the cell (see _on_statusbar_cell_focus).
            self._statusbar_entry_pending = True
            self.statusbar.SetFocus()
            return
        if label == "Reveal Codes":
            reveal = getattr(self, "_reveal_pane", None)
            if reveal is not None and reveal.panel.IsShown():
                reveal.focus()
                return
        if label == "Document Tabs":
            self.notebook.SetFocus()
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
        # The status bar announces its own region name + focused cell on the
        # landing (_on_statusbar_cell_focus), so skip the generic region
        # announcement here to avoid saying "Status Bar" twice on entry.
        if next_label != "Status Bar":
            self._set_status(f"Focused {next_label} region")

    def _outline_entries(self) -> list[OutlineEntry]:
        markup_kind = self._effective_markup_kind()
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
        set_accessible_name(tree, "YAML structure")
        preview = wx.TextCtrl(splitter, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(preview, "Node preview")
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
        *,
        show_counts: bool = False,
    ) -> list[_NavigatorNode]:
        text = self.editor.GetValue()
        counts: dict[str, int] = {}
        if show_counts:
            for item in misspellings:
                key = item.word.lower()
                counts[key] = counts.get(key, 0) + 1
        nodes: list[_NavigatorNode] = []
        for item in misspellings:
            line, column = line_column_for_position(text, item.start)
            line_start = text.rfind("\n", 0, item.start) + 1
            line_end = text.find("\n", item.end)
            if line_end == -1:
                line_end = len(text)
            excerpt = text[line_start:line_end].strip() or item.word
            count_suffix = ""
            if show_counts:
                total = counts[item.word.lower()]
                count_suffix = f", {total} occurrence{'s' if total != 1 else ''}"
            nodes.append(
                _NavigatorNode(
                    label=f"{item.word} (Ln {line}, Col {column}{count_suffix})",
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
        set_accessible_name(tree, root_label)
        preview = wx.TextCtrl(splitter, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(preview, f"{root_label} preview")
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
        # The root is hidden (TR_HIDE_ROOT), so its children are already
        # shown at the top level; wx asserts if you try to Expand() it
        # (#885: "Can't expand/collapse hidden root node!").
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
        self._save_active_bookmarks()
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

    def set_temp_bookmark(self) -> None:
        """Set the single unnamed, one-shot jump point (Leasey-style temp bookmark).

        Deliberately no dialog and no persistence -- this is disposable scratch
        state, overwritten silently on every re-set, and forgotten on restart.
        """
        position = self.editor.GetInsertionPoint()
        self._temp_bookmark = position
        self._active_tab().temp_bookmark = position
        self._set_status("Temporary bookmark set")

    def go_to_temp_bookmark(self) -> None:
        """Jump to the temp bookmark with no picker dialog."""
        if self._temp_bookmark is None:
            self._set_status("No temporary bookmark set")
            return
        self._move_point(self._temp_bookmark)
        self.editor.SetFocus()
        self._set_status("Jumped to temporary bookmark")

    def set_quick_bookmark(self, slot: int) -> None:
        """Set numbered quick-bookmark slot 0-9 (reuses the named-bookmark store)."""
        name = quick_slot_name(slot)
        position = self.editor.GetInsertionPoint()
        self._bookmarks = set_bookmark(self._bookmarks, name, position)
        self._save_active_bookmarks()
        self._set_status(f"Quick bookmark {slot} set")

    def go_to_quick_bookmark(self, slot: int) -> None:
        """Jump to numbered quick-bookmark slot 0-9 with no picker dialog."""
        name = quick_slot_name(slot)
        target = bookmark_position(self._bookmarks, name)
        if target is None:
            self._set_status(f"Quick bookmark {slot} is not set")
            return
        self._move_point(target)
        self.editor.SetFocus()
        self._set_status(f"Jumped to quick bookmark {slot}")

    # -- accessible code folding (x.md PRD) ---------------------------------- #
    # Fold state is spoken metadata, never visual line-hiding: the document
    # text is never mutated, and raw arrow/word/line navigation is never
    # intercepted. Only structural jump commands (here) are fold-aware, so a
    # screen reader user arrowing through a folded region reads it exactly as
    # if it weren't folded -- nothing reachable is ever silently skipped.

    def _current_foldable_regions(self) -> list[FoldableRegion]:
        markup_kind = self._effective_markup_kind()
        return extract_foldable_regions(self.editor.GetValue(), markup_kind)

    def toggle_fold(self) -> None:
        """Fold or unfold the smallest foldable region containing the caret."""
        regions = self._current_foldable_regions()
        caret = self.editor.GetInsertionPoint()
        region = smallest_region_containing(regions, caret)
        if region is None:
            self._set_status("No foldable region at the cursor")
            return
        key = (region.start, region.end)
        text = self.editor.GetValue()
        lines = region_line_count(text, region)
        if key in self._folded_regions:
            self._folded_regions.discard(key)
            self._set_status(f'Unfolded: "{region.label}"')
        else:
            self._folded_regions.add(key)
            self._set_status(f'Folded: {lines} lines under "{region.label}"')

    def next_fold(self) -> None:
        """Jump to the next foldable region boundary, announcing fold state."""
        regions = self._current_foldable_regions()
        if not regions:
            self._set_status("No foldable regions in this document")
            return
        caret = self.editor.GetInsertionPoint()
        region = next_region_boundary(regions, caret)
        if region is None:
            self._set_status("No more foldable regions ahead")
            return
        self._jump_to_fold(region)

    def previous_fold(self) -> None:
        """Jump to the previous foldable region boundary, announcing fold state."""
        regions = self._current_foldable_regions()
        if not regions:
            self._set_status("No foldable regions in this document")
            return
        caret = self.editor.GetInsertionPoint()
        region = previous_region_boundary(regions, caret)
        if region is None:
            self._set_status("No more foldable regions behind")
            return
        self._jump_to_fold(region)

    def _jump_to_fold(self, region: FoldableRegion) -> None:
        self._record_location_before_jump()
        self.editor.SetInsertionPoint(region.start)
        self.editor.SetFocus()
        text = self.editor.GetValue()
        lines = region_line_count(text, region)
        state = "folded" if (region.start, region.end) in self._folded_regions else "expanded"
        self._set_status(f'"{region.label}", {state}, {lines} lines')

    def list_folds(self) -> None:
        """Show every foldable region with its fold state; jump or toggle from here.

        The accessible equivalent of a sighted user scanning the gutter fold
        triangles: a spoken table of contents with fold state, reachable
        without ever having to encounter a region by scrolling past it.
        """
        regions = self._current_foldable_regions()
        if not regions:
            self._set_status("No foldable regions in this document")
            return
        text = self.editor.GetValue()
        nodes: list[_NavigatorNode] = []
        for region in regions:
            key = (region.start, region.end)
            state = "Folded" if key in self._folded_regions else "Expanded"
            lines = region_line_count(text, region)
            nodes.append(
                _NavigatorNode(
                    label=f"{region.label} ({state}, {lines} lines)",
                    preview=f"{region.label}\n\n{state}, {lines} lines",
                    payload=key,
                    action_label="Jump to Region",
                    children=[],
                )
            )
        selected = self._show_tree_navigator(
            title="List Folds",
            root_label="Foldable Regions",
            nodes=nodes,
        )
        if not isinstance(selected, tuple):
            self._set_status("Fold list cancelled")
            return
        region = next((r for r in regions if (r.start, r.end) == selected), None)
        if region is None:
            self._set_status("Region was not found")
            return
        self._jump_to_fold(region)

    # -- favorite folders (community feature request) ------------------------ #
    def _favorite_folders(self) -> FavoriteFolders:
        if getattr(self, "_favorite_folders_cache", None) is None:
            self._favorite_folders_cache = FavoriteFolders.load()
        return self._favorite_folders_cache

    def add_favorite_folder(self) -> None:
        """Add the current document's folder to Favorite Folders.

        Kurzweil-1000-style favorites: a short, deliberately curated list for
        instant access, distinct from Windows' recency-based recent-folders --
        a folder used constantly but not touched in months still belongs here.
        """
        doc_path = getattr(self.document, "path", None)
        if not doc_path:
            self._set_status("Save this document first, or use a specific folder")
            return
        folder = str(Path(doc_path).resolve().parent)
        added = self._favorite_folders().add(folder)
        if added:
            self._set_status(f"Added to Favorite Folders: {Path(folder).name}")
        else:
            self._set_status(f"{Path(folder).name} is already a favorite folder")

    def remove_favorite_folder(self) -> None:
        """Pick a favorite folder to remove from the list."""
        wx = self._wx
        vault = self._favorite_folders()
        names = vault.names()
        if not names:
            self._set_status("No favorite folders yet. Use Add Favorite Folder first.")
            return
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose a favorite folder to remove:",
            "Remove Favorite Folder",
            choices=names,
        ) as dialog:
            if hasattr(dialog, "SetSelection"):
                dialog.SetSelection(0)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Remove Favorite Folder") != wx.ID_OK:
                self._set_status("Remove favorite folder cancelled")
                return
            index = dialog.GetSelection()
        folder = vault.folders[index]
        vault.remove(folder)
        self._set_status(f"Removed favorite folder: {names[index]}")

    def open_from_favorite_folder(self) -> None:
        """VSCode-Quick-Open-style file finder, scoped to favorite folders.

        Quill has no single-project-root "workspace" the way VSCode does, so
        this scans favorite folders (top-level only by default -- see
        list_files_in_favorites) instead of an entire tree. Type to filter by
        filename, arrow to a match, Enter/OK to open it -- the same
        one-keystroke-per-step rhythm as VSCode's Ctrl+P, just bounded to the
        short, deliberately curated favorites list rather than everything on
        disk. An opt-in "Include subfolders" checkbox switches to a recursive
        scan (capped, so a huge favorite still can't hang the dialog) for
        anyone who wants it.
        """
        wx = self._wx
        vault = self._favorite_folders()
        if not vault.folders:
            self._set_status("No favorite folders yet. Use Add Favorite Folder first.")
            return

        dialog = wx.Dialog(self.frame, title="Open From Favorite Folder", size=(560, 440))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(dialog, label="Type to filter, then choose a file to open:"),
            0,
            wx.ALL,
            8,
        )
        search = wx.TextCtrl(dialog)
        search.SetName("Filter")
        root.Add(search, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        recursive_check = wx.CheckBox(dialog, label="Include subfolders")
        recursive_check.SetName("Include subfolders")
        root.Add(recursive_check, 0, wx.ALL, 8)
        results = wx.ListBox(dialog)
        results.SetName("Matching files")
        root.Add(results, 1, wx.ALL | wx.EXPAND, 8)
        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        dialog.SetSizer(root)

        all_files: list[FavoriteFile] = list_files_in_favorites(vault)
        current_matches: list[FavoriteFile] = list(all_files)

        def refresh(query: str) -> None:
            nonlocal current_matches
            current_matches = filter_favorite_files(all_files, query)
            results.Set([f"{item.path.name}  —  {item.folder_label}" for item in current_matches])
            if current_matches:
                results.SetSelection(0)

        def rescan() -> None:
            nonlocal all_files
            all_files = list_files_in_favorites(vault, recursive=recursive_check.GetValue())
            refresh(search.GetValue())

        refresh("")
        search.Bind(wx.EVT_TEXT, lambda _e: refresh(search.GetValue()))
        recursive_check.Bind(wx.EVT_CHECKBOX, lambda _e: rescan())
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        search.SetFocus()
        result = self._show_modal_dialog(dialog, "Open From Favorite Folder")
        selection = results.GetSelection()
        dialog.Destroy()
        if result != wx.ID_OK or selection == wx.NOT_FOUND:
            self._set_status("Open from favorite folder cancelled")
            return
        if not current_matches:
            self._set_status("No files found in your favorite folders.")
            return
        self.open_file(path=current_matches[selection].path)

    # -- persistent per-document bookmarks + last position ------------------ #
    def _save_active_bookmarks(self) -> None:
        """Write the active document's bookmarks back to its tab and (if the
        document is saved to disk) persist them per-document so they survive a
        restart. Untitled documents stay in memory for the session only."""
        tab = self._active_tab()
        if tab is not None:
            tab.bookmarks = dict(self._bookmarks)
        key = DocumentMemory.key_for(getattr(getattr(self, "document", None), "path", None))
        if key:
            try:
                self._doc_memory.set_bookmarks(key, self._bookmarks)
            except Exception:  # noqa: BLE001 - persistence is best-effort
                pass

    def _remember_active_caret(self) -> None:
        """Persist the active document's current caret offset as its last position."""
        key = DocumentMemory.key_for(getattr(getattr(self, "document", None), "path", None))
        editor = getattr(self, "editor", None)
        if not key or editor is None:
            return
        try:
            self._doc_memory.set_last_position(key, editor.GetInsertionPoint())
        except Exception:  # noqa: BLE001
            pass

    def _restore_document_memory(self, tab: object) -> None:
        """On open, load a saved document's bookmarks into its tab and move the
        caret to where it last was. No-op for untitled documents."""
        key = DocumentMemory.key_for(getattr(tab.document, "path", None))
        if not key:
            return
        try:
            tab.bookmarks = self._doc_memory.bookmarks_for(key)
            last = self._doc_memory.last_position(key)
        except Exception:  # noqa: BLE001
            return
        if last is None:
            return
        editor = tab.editor
        try:
            clamped = max(0, min(int(last), editor.GetLastPosition()))
            editor.SetInsertionPoint(clamped)
            show = getattr(editor, "ShowPosition", None)
            if callable(show):
                show(clamped)
        except Exception:  # noqa: BLE001
            pass

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

    def _active_read_aloud_pronunciations(self, engine: str) -> list:
        """Active pronunciation dictionaries for live Read Aloud (same as batch)."""
        if not getattr(self.settings, "pronunciation_enabled", True):
            return []
        from quill.core.speech.pronunciation import active_dictionaries

        ids = list(getattr(self.settings, "pronunciation_enabled_dictionary_ids", []) or [])
        try:
            return active_dictionaries(
                engine, project_dir=None, enabled_ids=set(ids) if ids else None
            )
        except Exception:  # noqa: BLE001 - a broken store must not block read-aloud
            return []

    def _elevenlabs_read_aloud_params(self, engine: str) -> tuple[str, str, str] | None:
        """Resolve (api_key, voice, model) for an ElevenLabs Read Aloud, with consent.

        Returns ``("", "", "")`` when the engine is not ElevenLabs (a no-op passed to
        the controller). For ElevenLabs it obtains a **per-session** consent once — the
        voice sends each sentence to ElevenLabs over the internet and uses the user's
        paid quota — resolves the stored key, and returns the chosen voice/model.
        Returns ``None`` when there is no key or the user declines, so the caller aborts
        the read-aloud cleanly (nothing is sent without consent).
        """
        if engine != "elevenlabs":
            return ("", "", "")
        wx = self._wx
        api_key = self._get_elevenlabs_api_key()
        if not api_key.strip():
            self._show_message_box(
                "Connect ElevenLabs first (in AI setup) to use its Read Aloud voice.",
                "Read Aloud",
                wx.ICON_INFORMATION | wx.OK,
            )
            return None
        if not getattr(self, "_elevenlabs_read_aloud_consented", False):
            answer = self._show_message_box(
                "Reading aloud with the ElevenLabs voice sends each sentence to "
                "ElevenLabs over the internet and uses your ElevenLabs quota. Use it "
                "for this session?",
                "ElevenLabs Read Aloud",
                wx.ICON_QUESTION | wx.YES_NO,
            )
            if answer != wx.YES:
                return None
            self._elevenlabs_read_aloud_consented = True
        return (
            api_key,
            str(getattr(self.settings, "read_aloud_elevenlabs_voice", "") or ""),
            str(getattr(self.settings, "read_aloud_elevenlabs_model", "") or ""),
        )

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
            read_aloud_engine = self.settings.read_aloud_engine.strip().lower() or "sapi5"
            el_params = self._elevenlabs_read_aloud_params(read_aloud_engine)
            if el_params is None:
                return  # ElevenLabs consent declined or no key
            el_key, el_voice, el_model = el_params
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
                elevenlabs_api_key=el_key,
                elevenlabs_voice=el_voice,
                elevenlabs_model=el_model,
                end=end,
                piper_model=self.settings.read_aloud_piper_model,
                kokoro_voice=self.settings.read_aloud_kokoro_voice,
                kokoro_speed=self.settings.read_aloud_kokoro_speed,
                espeak_executable=self.settings.read_aloud_espeak_executable,
                espeak_voice=self.settings.read_aloud_espeak_voice,
                espeak_rate=self.settings.read_aloud_espeak_rate,
                macos_voice=self.settings.read_aloud_macos_voice,
                macos_rate=self.settings.read_aloud_macos_rate,
                sentence_pause_ms=self.settings.read_aloud_sentence_pause_ms,
                punctuation_level=self.settings.announce_punctuation_level,
                pronunciation_dictionaries=self._active_read_aloud_pronunciations(
                    read_aloud_engine
                ),
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

    # ------------------------------------------------------------------
    # Experimental: read the document aloud in the user's real browser, where
    # speechSynthesis exposes the full voice set (including Edge's Online
    # (Natural) voices) — unlike the embedded WebView2, which only sees local
    # SAPI voices. We write a self-contained accessible reader page (voice
    # picker + Play/Pause/Stop) and open it in the chosen browser. Opt-in under
    # Preferences > Experimental. See quill/core/browser_reader.py.
    # ------------------------------------------------------------------
    def _edge_read_aloud_enabled(self) -> bool:
        return bool(
            getattr(self.settings, "edge_read_aloud_enabled", False)
            and getattr(self.settings, "experimental_acknowledged", False)
        )

    def read_document_in_browser(self) -> None:
        wx = self._wx
        if not self._edge_read_aloud_enabled():
            self._show_message_box(
                "Turn on 'Read the document aloud in your browser' under "
                "Preferences > Experimental first (it takes effect right away).",
                "Read in Browser (Experimental)",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        text = self.editor.GetValue()
        if not text.strip():
            self._set_status("Nothing to read")
            return
        from quill.core.browser_reader import build_reader_html

        title = "Document"
        tabs = getattr(self, "_document_tabs", None)
        if tabs:
            tab_index = (
                self._active_tab_index if self._active_tab_index >= 0 else self._current_tab_index()
            )
            if 0 <= tab_index < len(tabs):
                title = tabs[tab_index].document.name or "Document"
        reader_lang = getattr(self, "_active_language", None) or "en"
        payload = build_reader_html(title, text, lang=reader_lang)
        reader_dir = app_data_dir() / "browser-reader"
        reader_dir.mkdir(parents=True, exist_ok=True)
        reader_path = reader_dir / "read-aloud.html"
        temp_path = reader_path.with_suffix(".tmp")
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, reader_path)
        browser_choice = normalize_browser_choice(self.settings.preview_browser)
        open_preview_url(reader_path.as_uri(), browser_choice)
        self._set_status(
            f"Opened read-aloud in {browser_choice_label_for_value(browser_choice)} — "
            "choose a voice and press Play"
        )

    def _cleanup_browser_reader_files(self) -> None:
        """Delete the browser read-aloud plaintext page(s) on exit (privacy)."""
        from quill.core.browser_reader import remove_reader_pages

        remove_reader_pages(app_data_dir() / "browser-reader")

    # ------------------------------------------------------------------
    # Voice preview and settings for the supported read-aloud engines
    # ------------------------------------------------------------------

    _PREVIEW_TEXT = (
        "QUILL is where your words come to life, turning quiet thoughts into "
        "finished pages with a little sprinkle of everyday magic."
    )

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
        if safe_engine == "sapi5":
            safe_voice = _sapi5_voice_short_name(safe_voice)
            if not safe_voice:
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

    def _purge_preview_playback(self) -> None:
        """Best-effort: stop whatever voice-preview audio is currently sounding.

        Covers both playback backends `_play_preview_asset` uses. Never raises --
        called opportunistically whenever a new preview supersedes an old one.
        """
        if _winsound is not None:
            try:
                _winsound.PlaySound(None, _winsound.SND_PURGE)
            except Exception:  # noqa: BLE001
                pass
        try:
            import ctypes as _ct

            _ct.windll.winmm.mciSendStringW("stop quill_preview", None, 0, None)  # type: ignore[attr-defined]
            _ct.windll.winmm.mciSendStringW("close quill_preview", None, 0, None)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def _stop_active_voice_preview(self) -> None:
        """Stop/supersede whatever voice preview is currently active.

        Bumps the generation counter first (so any in-flight callback from the
        old generation becomes a no-op the instant it checks), then best-effort
        stops the old preview's audio: SAPI5 goes through the ReadAloudController
        it already owns; every other engine plays through `_play_preview_asset`,
        stopped via `_purge_preview_playback`. Does NOT stop an old preview's
        synthesis if it is still computing (e.g. a Piper/Kokoro call in
        progress) -- that finishes in the background and its result is
        discarded when the stale generation check fails.
        """
        self._preview_generation = getattr(self, "_preview_generation", 0) + 1
        self._cancel_preview_cue_timer()
        try:
            self._read_aloud.stop()
        except Exception:  # noqa: BLE001
            pass
        self._purge_preview_playback()

    def _cancel_preview_cue_timer(self) -> None:
        """Stop and clear any pending "generating preview" cue timer.

        Called whenever a preview generation is superseded (Task 3) or
        whenever its synthesis completes on its own -- success or error --
        so a stray cue never fires after the preview it belonged to is
        already over (see ``_synth_done`` and ``_finish_background_task``).
        """
        timer = getattr(self, "_preview_cue_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
            self._preview_cue_timer = None

    def _fire_generating_cue(self, generation: int) -> None:
        """One-shot "still generating" cue -- fires only if *generation* is
        still current (the ~400ms delay elapsed before synthesis finished)."""
        if getattr(self, "_preview_generation", 0) != generation:
            return
        post_sound(SoundEvent.VOICE_PREVIEW_GENERATING)
        if getattr(self.settings, "voice_preview_announce_generating", True):
            self._announce("Generating preview, please wait.")

    def _play_preview_asset(self, sample_path: Path) -> None:
        suffix = sample_path.suffix.lower()
        if suffix == ".wav" and _winsound is not None:
            _winsound.PlaySound(str(sample_path), _winsound.SND_FILENAME)
            return
        # MP3 and other formats: use Windows MCI for in-process synchronous playback.
        # This avoids opening an external media player.
        try:
            import ctypes as _ct

            _winmm = _ct.windll.winmm  # type: ignore[attr-defined]
            _alias = "quill_preview"
            _path = str(sample_path).replace('"', "")
            _winmm.mciSendStringW(f'open "{_path}" type mpegvideo alias {_alias}', None, 0, None)
            try:
                _winmm.mciSendStringW(f"play {_alias} wait", None, 0, None)
            finally:
                _winmm.mciSendStringW(f"close {_alias}", None, 0, None)
            return
        except (AttributeError, OSError):
            pass
        if sys.platform == "darwin":
            import subprocess as _subprocess

            _subprocess.Popen(["afplay", str(sample_path)])  # noqa: S603,S607
            return
        import os as _os

        _os.startfile(str(sample_path))

    def _preview_voice(
        self,
        engine: str,
        voice_id: str,
        *,
        live: bool = False,
        text: str | None = None,
        on_state_change: Callable[[str], None] | None = None,
    ) -> None:
        """Preview *voice_id* through *engine* on a background thread.

        ``live`` True means the voice is downloaded and ready, so synthesize the
        preview phrase with the real model. ``live`` False (the voice is not yet
        downloaded) plays the bundled pre-recorded sample instead, so the user
        can still hear what the voice sounds like before downloading; if no
        sample ships for it, we say so rather than failing silently.

        Starting a preview always stops/supersedes whatever preview was
        previously active (see ``_stop_active_voice_preview``): its playback is
        cut short and its completion callback becomes a no-op, so two previews
        started in quick succession never overlap.
        """
        import tempfile as _tmpfile
        from pathlib import Path as _Path

        self._stop_active_voice_preview()
        my_generation = self._preview_generation

        def _still_current() -> bool:
            return getattr(self, "_preview_generation", 0) == my_generation

        def _report(state: str) -> None:
            if on_state_change is not None and _still_current():
                self._wx.CallAfter(on_state_change, state)

        sample = text or self._PREVIEW_TEXT
        s = self.settings

        # Not downloaded: play the bundled pre-recorded sample (same phrase the
        # live synthesis uses), or explain that none is available.
        if not live:
            preview_sample = self._voice_preview_sample_path(engine, voice_id)
            if preview_sample is None:
                self._set_status("Download this voice to hear a preview.")
                return

            def _play_sample(_progress: Callable[[str, int, int], None]) -> object:
                _report("playing")
                try:
                    self._play_preview_asset(preview_sample)
                except Exception:
                    _report("idle")
                    raise
                return None

            def _sample_done(_r: object) -> None:
                if _still_current():
                    self._set_status("Preview finished")
                _report("idle")

            self._run_background_task(
                f"Previewing {engine} voice",
                _play_sample,
                _sample_done,
            )
            return

        # sapi5: delegate to ReadAloudController so SAPI5/COM runs on its own
        # dedicated thread, avoiding the "started a loop" error from ThreadPoolExecutor.
        if engine == "sapi5":
            try:
                _report("playing")
                self._read_aloud.start(
                    sample,
                    0,
                    voice_id,
                    engine_name="sapi5",
                    rate=s.read_aloud_rate,
                    volume=s.read_aloud_volume / 100.0,
                    pitch=s.read_aloud_pitch,
                    on_state_change=lambda state: (
                        (self._wx.CallAfter(self._set_status, "Preview finished"), _report("idle"))
                        if state in ("idle", "error") and _still_current()
                        else None
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"Preview failed: {exc}")
                _report("idle")
            return

        # ElevenLabs previews also cost quota, so gate them on the same per-session
        # consent and resolve the key on the UI thread before the worker runs.
        el_key = ""
        el_model = ""
        if engine == "elevenlabs":
            el_params = self._elevenlabs_read_aloud_params("elevenlabs")
            if el_params is None:
                return
            el_key, _el_voice, el_model = el_params

        def _work(_progress: Callable[[str, int, int], None]) -> object:
            with _tmpfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
                wav = _Path(fh.name)
            try:
                if engine == "dectalk":
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
                        model_path=resolve_piper_model_path(voice_id),
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
                elif engine == "elevenlabs":
                    from quill.core.ai import elevenlabs_tts

                    wav.write_bytes(
                        elevenlabs_tts.synthesize_wav(
                            sample, el_key, voice=voice_id, model=el_model
                        )
                    )
                elif engine == "macos":
                    synthesize_with_macos(
                        sample,
                        wav,
                        voice=voice_id,
                        rate=s.read_aloud_macos_rate,
                    )
                else:
                    raise ReadAloudUnavailableError(f"Unknown engine: {engine}")
                _report("playing")
                self._play_preview_asset(wav)
            except Exception:
                _report("idle")
                raise
            finally:
                try:
                    wav.unlink(missing_ok=True)
                except OSError:
                    pass
            return None

        def _synth_done(_r: object) -> None:
            # Synthesis reported success -- the pending cue is no longer
            # relevant regardless of whether this generation is still
            # current, so cancel it before anything else.
            self._cancel_preview_cue_timer()
            if _still_current():
                self._set_status("Preview finished")
            _report("idle")

        _report("generating")
        self._preview_cue_timer = self._wx.CallLater(400, self._fire_generating_cue, my_generation)
        self._run_background_task(
            f"Previewing {engine} voice",
            _work,
            _synth_done,
        )

    def choose_read_aloud_configuration(self) -> None:
        """Open the unified Speech Hub on the Speech (Offline) tab."""
        from quill.ui.speech_hub_dialog import TAB_SPEECH_OFFLINE

        self.open_speech_hub(TAB_SPEECH_OFFLINE)

    def open_speech_hub(self, initial_tab: int = 0) -> None:  # noqa: PLR0912,PLR0915
        """Open the unified Speech Hub dialog: Speech and Dictation, each split
        into Offline/Online tabs (local engines vs. API-key cloud providers,
        #847)."""
        from quill.core.read_aloud import (
            discover_dectalk_executable,
            discover_espeak_executable,
            discover_piper_executable,
            kokoro_engine_ready,
            macos_say_available,
        )
        from quill.core.speech.engine_install import (
            is_faster_whisper_available,
            is_kokoro_onnx_available,
            is_vosk_available,
            kokoro_onnx_install_supported,
            vosk_install_supported,
        )
        from quill.core.speech.ffmpeg import ffmpeg_available
        from quill.core.speech.providers.whispercpp import resolve_whisper_executable
        from quill.core.speech.service import (
            describe_models,
            detect_has_gpu,
            detect_total_ram_gb,
            machine_summary,
        )
        from quill.ui.speech_hub_dialog import SpeechHubDialog

        wx = self._wx

        # --- Speech (Read Aloud) kwargs, split Offline/Online ---
        from quill.core.ai import elevenlabs_tts

        elevenlabs_ready = (
            bool(self._get_elevenlabs_api_key().strip()) and elevenlabs_tts.available()
        )
        offline_engine_options: list[tuple[str, str]] = [
            ("Windows (SAPI 5)", "sapi5"),
            ("DECtalk", "dectalk"),
            ("Piper (neural, offline)", "piper"),
            ("Kokoro (neural, offline)", "kokoro"),
            ("eSpeak-NG (many languages)", "espeak"),
        ]
        if macos_say_available():
            # macOS system voice via the say CLI — only offered on macOS (#21/#75).
            offline_engine_options.append(("macOS (system voice)", "macos"))
        online_engine_options: list[tuple[str, str]] = [
            ("ElevenLabs (premium cloud)", "elevenlabs"),
        ]
        offline_engine_available = {
            "sapi5": True,
            "dectalk": discover_dectalk_executable(self.settings.read_aloud_dectalk_executable)
            is not None,
            "piper": discover_piper_executable() is not None,
            "kokoro": kokoro_engine_ready(),
            "espeak": discover_espeak_executable(self.settings.read_aloud_espeak_executable)
            is not None,
            "macos": macos_say_available(),
        }
        online_engine_available = {"elevenlabs": elevenlabs_ready}
        configured_engine = self.settings.read_aloud_engine.strip().lower() or "sapi5"
        offline_current_engine = (
            configured_engine
            if configured_engine in {val for _, val in offline_engine_options}
            else "sapi5"
        )
        common_ra_kwargs: dict = {
            "piper_model_dir": default_piper_model_dir(),
            "settings": self.settings,
            "preview_fn": self._preview_voice,
            "preview_stop_fn": self._stop_active_voice_preview,
            "elevenlabs_api_key": self._get_elevenlabs_api_key() if elevenlabs_ready else "",
            "has_preview_sample": (
                lambda eng, vid: self._voice_preview_sample_path(eng, vid) is not None
            ),
        }
        read_aloud_offline_kwargs: dict = {
            "engine_options": offline_engine_options,
            "current_engine": offline_current_engine,
            "engine_available": offline_engine_available,
            **common_ra_kwargs,
        }
        read_aloud_online_kwargs: dict = {
            "engine_options": online_engine_options,
            "current_engine": "elevenlabs",
            "engine_available": online_engine_available,
            **common_ra_kwargs,
        }

        # --- Dictation kwargs, split Offline/Online ---
        registry = self._speech_registry()
        # Show every *registered* engine, not just the ones usable right now
        # (#514/#669 model-manager): an engine whose runtime isn't installed yet
        # — notably whisper.cpp when its binary is missing — must still appear in
        # the chooser, labelled "(not installed)", so the user can discover it and
        # reach its guided install path instead of having it silently disappear.
        all_providers = list(registry.all())  # type: ignore[attr-defined]
        provider = self._configured_speech_provider(registry)  # saved engine, not avail-fallback
        total_ram = detect_total_ram_gb()
        has_gpu = detect_has_gpu()
        rows = describe_models(provider, total_ram, has_gpu)  # type: ignore[arg-type]
        common_dict_kwargs: dict = {
            "machine_summary": machine_summary(total_ram, has_gpu),
            "whispercpp_ok": resolve_whisper_executable() is not None,
            "ffmpeg_ok": ffmpeg_available(),
            "engine_ok": is_faster_whisper_available(),
            "vosk_ok": is_vosk_available(),
            "vosk_can_install": vosk_install_supported(),
            "kokoro_ok": is_kokoro_onnx_available(),
            "kokoro_can_install": kokoro_onnx_install_supported(),
            "all_providers": all_providers,
            "total_ram": total_ram,
            "has_gpu": has_gpu,
            "default_provider_id": str(getattr(self.settings, "speech_provider", "") or ""),
            "announce_cb": self._announce,
        }
        dictation_offline_kwargs: dict = {
            "provider": provider,
            "rows": rows,
            "engine_scope": "offline",
            **common_dict_kwargs,
        }
        known_offline_ids = {"whispercpp", "fasterwhisper", "vosk"}
        cloud_providers = [
            p for p in all_providers if str(getattr(p, "id", "")) not in known_offline_ids
        ]
        dictation_online_kwargs: dict | None = None
        if cloud_providers:
            cloud_provider = (
                next((p for p in cloud_providers if getattr(p, "id", "") == provider.id), None)
                or cloud_providers[0]
            )
            dictation_online_kwargs = {
                "provider": cloud_provider,
                "rows": describe_models(cloud_provider, total_ram, has_gpu),  # type: ignore[arg-type]
                "engine_scope": "online",
                **common_dict_kwargs,
            }

        hub = SpeechHubDialog(
            self.frame,
            read_aloud_offline_kwargs=read_aloud_offline_kwargs,
            read_aloud_online_kwargs=read_aloud_online_kwargs,
            dictation_offline_kwargs=dictation_offline_kwargs,
            dictation_online_kwargs=dictation_online_kwargs,
            initial_tab=initial_tab,
        )
        ra_result, dict_result = hub.show(self._show_modal_dialog)

        # --- Handle Read Aloud result ---
        if ra_result is not None:
            # Downloads open a non-modal progress dialog. The hub modal is still
            # tearing down here, so creating it inline lets focus snap back to the
            # editor and the screen reader never announces the progress window
            # (the user is "thrown back to the document with no notification").
            # Deferring with CallAfter runs the download after the modal fully
            # closes, so the progress dialog presents and is announced.
            if ra_result.action == "download":
                if ra_result.engine == "piper":
                    wx.CallAfter(self._download_piper_voice, ra_result.voice_id)
                elif ra_result.engine == "kokoro":
                    wx.CallAfter(self._download_kokoro_models)
            elif ra_result.action == "download_engine":
                if ra_result.engine == "dectalk":
                    wx.CallAfter(self.download_dectalk_exe)
                elif ra_result.engine == "piper":
                    wx.CallAfter(self.download_piper_exe)
                elif ra_result.engine == "espeak":
                    wx.CallAfter(self.download_espeak_exe)
            else:  # 'select' or 'export'
                eng = ra_result.engine
                piper_dir = default_piper_model_dir()
                self.settings.read_aloud_engine = eng
                if ra_result.voice_id:
                    if eng == "dectalk":
                        self.settings.read_aloud_dectalk_voice = ra_result.voice_id
                    elif eng == "piper":
                        onnx_path = piper_dir / f"{ra_result.voice_id}.onnx"
                        if onnx_path.exists():
                            self.settings.read_aloud_piper_model = str(onnx_path)
                        else:
                            self._show_message_box(
                                f"'{ra_result.voice_id}' is not downloaded yet.\n"
                                "Use the Download Voice button to fetch it first.",
                                "Speech Settings",
                                wx.ICON_INFORMATION | wx.OK,
                            )
                            self.settings.read_aloud_engine = offline_current_engine
                            dict_result = None  # skip dictation processing
                    elif eng == "kokoro":
                        self.settings.read_aloud_kokoro_voice = ra_result.voice_id
                    elif eng == "espeak":
                        self.settings.read_aloud_espeak_voice = ra_result.voice_id
                    elif eng == "macos":
                        self.settings.read_aloud_macos_voice = ra_result.voice_id
                    elif eng == "elevenlabs":
                        self.settings.read_aloud_elevenlabs_voice = ra_result.voice_id
                    else:
                        self.settings.read_aloud_voice = ra_result.voice_id
                if eng == "sapi5":
                    self.settings.read_aloud_rate = ra_result.rate
                    self.settings.read_aloud_volume = ra_result.volume
                    self.settings.read_aloud_pitch = ra_result.pitch
                elif eng == "dectalk":
                    self.settings.read_aloud_dectalk_rate = ra_result.dectalk_rate
                elif eng == "espeak":
                    self.settings.read_aloud_espeak_rate = ra_result.espeak_rate
                elif eng == "macos":
                    self.settings.read_aloud_macos_rate = ra_result.macos_rate
                elif eng == "kokoro":
                    self.settings.read_aloud_kokoro_speed = ra_result.kokoro_speed
                save_settings(self.settings)
                engine_label = dict(offline_engine_options + online_engine_options).get(eng, eng)
                self._set_status(f"Read aloud configured: {engine_label}")
                if ra_result.action == "export":
                    self.generate_speech_audio()

        # --- Handle Dictation result ---
        if dict_result is not None:
            chosen_provider_id = dict_result.provider_id or ""
            if chosen_provider_id and chosen_provider_id != str(
                getattr(self.settings, "speech_provider", "") or ""
            ):
                chosen = registry.get(chosen_provider_id)  # type: ignore[attr-defined]
                if chosen is not None:
                    provider = chosen
                    self.settings.speech_provider = chosen_provider_id
                    try:
                        save_settings(self.settings)
                    except Exception:  # noqa: BLE001
                        pass
                    self._announce(
                        f"Speech engine set to {provider.display_name}."  # type: ignore[attr-defined]
                    )
            if dict_result.action == "download" and dict_result.model_row is not None:
                self._maybe_download_speech_model(provider, dict_result.model_row)
            elif dict_result.action == "remove" and dict_result.model_id:
                self._maybe_remove_speech_model(provider, dict_result.model_id)
            elif dict_result.action == "ffmpeg":
                self.download_ffmpeg()
            elif dict_result.action == "engine":
                self.download_faster_whisper()
            elif dict_result.action == "vosk":
                self.download_vosk()
            elif dict_result.action == "hf_token":
                self.set_huggingface_token()
            elif dict_result.action == "test":
                # Prove the selected engine (SAPI clip -> transcribe), speaking and
                # logging the result; the provider_id block above already made it
                # the default, so a successful Test doubles as "use this engine".
                test_id = dict_result.provider_id or getattr(provider, "id", "")
                self._test_optional_component(test_id)
            elif dict_result.action == "set_default" and dict_result.model_id:
                self.settings.speech_default_model_id = dict_result.model_id
                save_settings(self.settings)
                self._announce(f"{dict_result.model_id} set as the default speech model.")

    def _download_piper_voice(self, voice_id: str) -> None:
        """Download a Piper ONNX voice model in the background."""
        import urllib.request as _ureq

        from quill.core.voice_catalog import piper_voice_download_urls
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        wx = self._wx
        piper_dir = default_piper_model_dir()
        urls = piper_voice_download_urls(voice_id)
        if urls is None:
            self._show_message_box(
                f"Cannot determine download URL for: {voice_id}",
                "Download Piper Voice",
                wx.ICON_WARNING | wx.OK,
            )
            return
        onnx_url, json_url = urls
        onnx_path = piper_dir / f"{voice_id}.onnx"
        json_path = piper_dir / f"{voice_id}.onnx.json"
        if onnx_path.exists() and json_path.exists():
            self._set_status(f"Piper voice '{voice_id}' is already downloaded.")
            self.choose_read_aloud_configuration()
            return
        # Offline Edition: a staged starter voice installs with no network at
        # all (same destination the download below would use).
        from quill.core.speech.piper_install import install_bundled_piper_voice

        if install_bundled_piper_voice(voice_id, dest_dir=piper_dir) is not None:
            self._set_status(f"Piper voice '{voice_id}' installed from the offline bundle.")
            self.choose_read_aloud_configuration()
            return
        piper_dir.mkdir(parents=True, exist_ok=True)

        cancel = threading.Event()
        progress = AIProgressDialog(
            self.frame,
            f"Downloading Piper voice: {voice_id}",
            "Preparing download...",
            on_cancel=cancel.set,
        )
        progress.show()
        self._announce(f"Downloading Piper voice {voice_id}.")

        def _run(
            _ou: str = onnx_url,
            _ju: str = json_url,
            _op: Path = onnx_path,
            _jp: Path = json_path,
            _vid: str = voice_id,
        ) -> None:
            try:
                pairs = [(_ou, _op), (_ju, _jp)]
                for i, (url, path) in enumerate(pairs):
                    if cancel.is_set():
                        raise RuntimeError("Cancelled")
                    wx.CallAfter(
                        progress.set_progress,
                        int(i / len(pairs) * 100),
                        f"Downloading {path.name}...",
                    )
                    with _ureq.urlopen(url, timeout=120) as resp:  # noqa: S310
                        total = int(resp.headers.get("Content-Length", 0))
                        got = 0
                        chunks: list[bytes] = []
                        while True:
                            if cancel.is_set():
                                raise RuntimeError("Cancelled")
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            chunks.append(chunk)
                            got += len(chunk)
                            if total:
                                pct = int((i + got / total) / len(pairs) * 100)
                                wx.CallAfter(
                                    progress.set_progress,
                                    pct,
                                    f"Downloading {path.name}...",
                                )
                    path.write_bytes(b"".join(chunks))
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(progress.close)
                if cancel.is_set():
                    wx.CallAfter(self._set_status, "Piper voice download cancelled.")
                else:
                    wx.CallAfter(self._set_status, f"Piper voice download failed: {exc}")
                return
            done_msg = (
                f"Piper voice '{_vid}' is ready. Click OK to open Manage Voices and select it."
            )
            wx.CallAfter(self._set_status, f"Piper voice '{_vid}' downloaded.")
            wx.CallAfter(self._announce, f"Piper voice {_vid} downloaded.")
            progress.switch_to_ok(done_msg, on_ok=self.choose_read_aloud_configuration)

        threading.Thread(  # GATE-40-OK: Piper voice download worker.
            target=_run, daemon=True
        ).start()

    def _download_kokoro_models(self, *, on_done: Callable[[bool], None] | None = None) -> None:
        """Fetch the Kokoro ONNX model + voices from QUILL's verified release asset,
        then ensure the kokoro-onnx package is installed (Kokoro unbundle, PRD 10.2.4).

        Kokoro is no longer bundled in fresh installers; this downloads it on demand
        into the user data dir, which the runtime prefers. The download is pinned +
        SHA-256-verified via quill.core.release_assets, runs on a worker thread behind
        a cancelable percentage, and is blocked in Safe Mode. Users upgrading from a
        release that bundled Kokoro keep their {app}/kokoro-models copy, so this only
        runs when Kokoro is actually missing.
        """
        from quill.core.read_aloud import (
            KOKORO_ONNX_MODEL_FILENAME,
            KOKORO_ONNX_VOICES_FILENAME,
            default_kokoro_model_dir,
            kokoro_onnx_ready,
        )
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        wx = self._wx
        dest_dir = default_kokoro_model_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        model_path = dest_dir / KOKORO_ONNX_MODEL_FILENAME
        voices_path = dest_dir / KOKORO_ONNX_VOICES_FILENAME

        # Smart re-download: if the voices are already present, don't silently
        # re-fetch ~120 MB -- offer to replace them. Declining keeps the existing
        # copy (and just finishes the package step if needed). Re-fetching only
        # happens when the user opts in. (#kokoro-replace)
        force = True
        if model_path.exists() and voices_path.exists():
            from quill.core.speech.engine_install import is_kokoro_onnx_available

            again = self._show_message_box(
                "The Kokoro voices are already downloaded. Download a fresh copy "
                "(replace what you have)?",
                "Download Kokoro",
                wx.ICON_QUESTION | wx.YES_NO,
            )
            if again != wx.YES:
                force = False  # keep the existing files
                if kokoro_onnx_ready() and is_kokoro_onnx_available():
                    # _set_status already speaks; a second _announce of the same
                    # text would double-speak it (#728).
                    self._set_status("Kokoro is already installed.")
                    return

        cancel = threading.Event()
        progress = AIProgressDialog(
            self.frame,
            "Downloading Kokoro Models",
            "Preparing download...",
            on_cancel=cancel.set,
        )
        progress.show()
        self._announce("Downloading Kokoro models.")

        def _run() -> None:
            try:
                from quill.core.release_assets import fetch_component
                from quill.core.speech.engine_install import (
                    install_kokoro_onnx,
                    is_kokoro_onnx_available,
                )

                if force or not (model_path.exists() and voices_path.exists()):
                    # Reserve 0-80% for the model + voices, 80-100% for the package.
                    def _model_progress(frac: float, msg: str) -> None:
                        wx.CallAfter(progress.set_progress, int(frac * 80), msg)

                    fetch_component(
                        "kokoro",
                        dest_dir,
                        progress=_model_progress,
                        should_cancel=cancel.is_set,
                        label="Downloading Kokoro voices...",
                    )
                if not is_kokoro_onnx_available():

                    def _pkg_progress(frac: float, msg: str) -> None:
                        wx.CallAfter(progress.set_progress, 80 + int(frac * 20), msg)

                    # GATE-40-OK: Kokoro engine install worker.
                    install_kokoro_onnx(progress=_pkg_progress)
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(progress.close)
                if cancel.is_set():
                    wx.CallAfter(self._set_status, "Kokoro download cancelled.")
                else:
                    wx.CallAfter(self._set_status, f"Kokoro download failed: {exc}")
                return
            if kokoro_onnx_ready():
                done_msg = "Kokoro is ready. Click OK to open Manage Voices and select a voice."
                wx.CallAfter(self._set_status, "Kokoro ready.")
                wx.CallAfter(self._announce, "Kokoro models downloaded.")
                progress.switch_to_ok(
                    done_msg,
                    on_ok=(lambda: on_done(True))
                    if on_done
                    else self.choose_read_aloud_configuration,
                )
            else:
                wx.CallAfter(progress.close)
                wx.CallAfter(
                    self._set_status, "Kokoro download failed; check your internet connection."
                )

        threading.Thread(  # GATE-40-OK: Kokoro model download worker.
            target=_run, daemon=True
        ).start()

    def choose_read_aloud_voice(self) -> None:
        self.choose_read_aloud_configuration()

    def choose_read_aloud_settings(self) -> None:
        self.choose_read_aloud_configuration()

    def generate_speech_audio(self) -> None:  # noqa: PLR0912,PLR0915
        wx = self._wx
        _TITLE = "Generate Speech Audio"
        editor = getattr(self, "editor", None)
        text = ""
        if editor is not None:
            text = editor.GetStringSelection().strip() or editor.GetValue().strip()
        if text:
            from quill.core.speech.text_polish import clean_markdown_text, polish_for_tts

            # Raw markdown syntax ('#', '**', '[label](url)') reaching a
            # synthesis engine directly -- Piper's espeak-ng phonemizer badly
            # mis-tokenizes it, sounding garbled or like the wrong language
            # (fix.md #4). Batch export and document-to-speech already clean
            # it; this shares the same sanitizer.
            text = polish_for_tts(clean_markdown_text(text))
        if not text:
            self._show_message_box(
                "There is nothing to export. Open or type a document first, then "
                "try Export to Speech Audio again.",
                _TITLE,
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("Nothing to synthesize")
            return

        # WAV is always available (the engines emit it directly). The compressed
        # listening formats (MP3, M4A/M4B, OGG, Opus, FLAC) need ffmpeg to encode
        # the synthesized WAV, so they only appear when ffmpeg is installed (#750).
        from quill.core.speech.ffmpeg import ffmpeg_available, resolve_export_format

        formats: list[tuple[str, str]] = [("wav", "Wave file")]
        if ffmpeg_available():
            formats += [
                ("mp3", "MP3 audio"),
                ("m4a", "M4A audio"),
                ("m4b", "M4B audiobook"),
                ("ogg", "OGG audio"),
                ("opus", "Opus audio"),
                ("flac", "FLAC audio"),
            ]
        wildcard = "|".join(f"{label} (*.{ext})|*.{ext}" for ext, label in formats)
        wildcard += "|All files (*.*)|*.*"

        with wx.FileDialog(
            self.frame,
            _TITLE,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if self._show_modal_dialog(dlg, _TITLE) != wx.ID_OK:
                self._set_status("Speech generation cancelled")
                return
            output_path = Path(dlg.GetPath())
            filter_index = dlg.GetFilterIndex()

        # Pick the target format: a recognized typed extension wins (so "song.mp3"
        # under "All files" still makes an MP3); otherwise the selected filter
        # decides and the extension is normalized to match (see resolve_export_format).
        target_fmt, _normalize_suffix = resolve_export_format(
            output_path.suffix, filter_index, [ext for ext, _ in formats]
        )
        if _normalize_suffix:
            output_path = output_path.with_suffix(f".{target_fmt}")

        engine = self.settings.read_aloud_engine.strip().lower() or "sapi5"
        s = self.settings

        # Kokoro-only: models on disk but the kokoro_onnx package missing (e.g.
        # upgraded from a build that bundled Kokoro). Set in the gate below and
        # honored on the export worker so the small package install happens off
        # the UI thread. (#kokoro-onnx)
        kokoro_install_pkg = False

        # Resolve / prompt for engine-specific paths before background work
        if engine == "piper":
            exe = discover_piper_executable()
            if exe is None:
                self._show_message_box(
                    "Piper executable was not found. "
                    "Re-run the Quill installer and select the Piper component.",
                    _TITLE,
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Speech generation cancelled")
                return
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

        elif engine == "kokoro":
            from quill.core.read_aloud import kokoro_engine_ready, kokoro_onnx_ready

            if not kokoro_engine_ready():
                if kokoro_onnx_ready():
                    # Model files are present but the kokoro_onnx package is not
                    # importable. The user already opted into Kokoro (downloaded
                    # the voices and selected the voice), so onboard the small
                    # (~20 MB) package on the export worker instead of dead-ending
                    # with a "go install it yourself" dialog. (#kokoro-onnx)
                    kokoro_install_pkg = True
                else:
                    self._show_message_box(
                        "Kokoro voices are not installed yet. Use Manage Voices to "
                        "download the Kokoro voices (~114 MB) before exporting.",
                        _TITLE,
                        wx.ICON_ERROR | wx.OK,
                    )
                    self._set_status("Speech generation cancelled")
                    return

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
        _kokoro_install_pkg = kokoro_install_pkg
        _espeak_voice = s.read_aloud_espeak_voice
        _espeak_rate = s.read_aloud_espeak_rate
        _out = output_path
        _target_fmt = target_fmt

        def work(progress: Callable[[str, int, int], None]) -> object:
            import tempfile

            from quill.core.speech.ffmpeg import transcode_audio

            progress(f"Starting {_engine}", 0, 1)
            # The synthesis engines only emit WAV. For a compressed target, render
            # to a temporary WAV first, then encode it to the chosen format (#750).
            tmp_dir: str | None = None
            if _target_fmt == "wav":
                wav_target = _out
            else:
                tmp_dir = tempfile.mkdtemp(prefix="quill-speech-")
                wav_target = Path(tmp_dir) / f"{_out.stem}.wav"
            if _engine == "sapi5":
                synthesize_to_file_with_sapi5(
                    _out_text, wav_target, voice=_voice, rate=_rate, volume=_vol
                )
            elif _engine == "dectalk":
                synthesize_to_file_with_dectalk(
                    _out_text,
                    wav_target,
                    executable_path=dectalk_exe_snap,
                    voice=_dectalk_voice,
                    rate=_dectalk_rate,
                )
            elif _engine == "piper":
                synthesize_with_piper(
                    _out_text,
                    wav_target,
                    executable_path=piper_exe_snap,
                    model_path=piper_model_snap,
                )
            elif _engine == "kokoro":
                if _kokoro_install_pkg:
                    # GATE-40-OK: runs on the export worker (this callback is the
                    # background task body), so the ~20 MB pip install stays off
                    # the UI thread. A failure surfaces the real installer error
                    # via notify_on_error, not the masked fallback. (#kokoro-onnx)
                    from quill.core.speech.engine_install import install_kokoro_onnx

                    progress("Installing Kokoro component", 0, 1)
                    install_kokoro_onnx(
                        progress=lambda frac, msg: progress(msg, int(frac * 100), 100)
                    )
                synthesize_with_kokoro(
                    _out_text, wav_target, voice=_kokoro_voice, speed=_kokoro_speed
                )
            elif _engine == "espeak":
                synthesize_with_espeak(
                    _out_text,
                    wav_target,
                    executable_path=espeak_exe_snap,
                    voice=_espeak_voice,
                    rate=_espeak_rate,
                )
            if _target_fmt != "wav":
                progress(f"Encoding {_target_fmt.upper()}", 1, 1)
                try:
                    transcode_audio(wav_target, _out, _target_fmt)
                finally:
                    wav_target.unlink(missing_ok=True)
                    if tmp_dir:
                        try:
                            Path(tmp_dir).rmdir()
                        except OSError:
                            pass
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
        # Following along selects each sentence as it is spoken. With a screen
        # reader running this makes it announce the selection over QUILL's voice,
        # so it is gated behind a setting screen-reader users can turn off.
        if self.settings.read_aloud_follow_cursor:
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
            # #10: this early return left focus in the editor with only a silent
            # status, so the command looked like it "did nothing". Speak it.
            self._announce_result("Watch folder is unavailable in this profile")
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
            label = f"Pending {queued}, done {done}, failed {failed}, skipped {skipped}{paused}"
            # Explain an apparently-empty queue: profiles default to ignoring files
            # already present when the watch started (process_existing off), so only
            # newly-added files appear. Surface that so the monitor isn't confusing.
            if not items:
                try:
                    primed = self._watch_service.primed_count()
                except Exception:  # noqa: BLE001 - a hint must never break the monitor
                    primed = 0
                if primed:
                    label += (
                        f". {primed} existing file{'s' if primed != 1 else ''} ignored "
                        "(turn on 'Process existing files' on a profile, or add a new file)"
                    )
            summary.SetLabel(label)
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
        status = install_shell_integration(command)
        try:
            apply_shell_verb_settings(self.settings)
        except Exception:  # pragma: no cover - registry best-effort
            pass
        if status.installed:
            self._show_message_box(
                f"Installed shell integration for:\n{summary}",
                "Shell Integration",
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("Installed shell integration")
        else:
            # #8: macOS best-effort install can be a no-op (duti missing). Tell the
            # user why instead of reporting a false success.
            self._show_message_box(
                status.message,
                "Shell Integration",
                wx.ICON_WARNING | wx.OK,
            )
            self._set_status("Shell integration not fully applied")

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

    def clear_all_notifications(self) -> None:
        """Clear every stored notification without opening the dialog.

        Wired to the "Clear All Notifications" entry on the notifications cell
        context menu so the badge can be emptied in one step."""
        clear_notifications()
        self._notifications = []
        self._refresh_statusbar()
        self._set_status("Cleared all notifications")

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
        set_accessible_name(chooser, "Notifications")
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
        from quill.ui.status_dialog import HelpStatusDialog

        self._ensure_status_page_timer()
        dlg = getattr(self, "_help_status_dialog", None)
        if dlg is not None and dlg.is_alive():
            dlg.refresh(self._build_help_status_data())
            dlg.show()
        else:
            self._help_status_dialog = HelpStatusDialog(
                self.frame, self._wx, self._build_help_status_data()
            )
            self._help_status_dialog.set_refresh_callback(
                lambda: self._help_status_dialog.refresh(self._build_help_status_data())
            )
            self._help_status_dialog.show()
        self._set_status_page_live_updates(True)
        self._set_status("Opened application status page")

    def _build_help_status_data(self) -> dict:
        """Collect runtime status into a structured dict for HelpStatusDialog."""
        from quill.core.bw_providers import get_provider as bw_get_provider
        from quill.core.bw_providers import provider_readiness as bw_provider_readiness
        from quill.core.bw_providers import recommended_provider_id as bw_recommended_provider_id
        from quill.core.bw_speech import downloaded_model_ids as bw_downloaded_model_ids
        from quill.core.bw_speech import faster_whisper_status
        from quill.core.bw_speech import list_models as bw_list_models

        settings = self.settings
        notification_count = len(getattr(self, "_notifications", []))
        active_tasks = int(getattr(self, "_background_task_count", 0))
        profile_name = self.features.active_profile.name

        status_rows: list[tuple[str, str, str]] = [
            ("Overview", "Version", __version__),
            ("Overview", "Active profile", profile_name),
            ("Overview", "Background tasks running", str(active_tasks)),
            ("Overview", "Notifications queued", str(notification_count)),
        ]

        if self.features.is_enabled("core.bw_whisperer"):
            bw_mode = str(getattr(settings, "bw_provider_mode", "local_first"))
            bw_local_first = bw_mode == "local_first"
            bw_provider_id = str(getattr(settings, "bw_provider_id", "local_whisper"))
            bw_provider = bw_get_provider(bw_provider_id, include_cloud=True)
            bw_recommended_provider = bw_recommended_provider_id(local_first=bw_local_first)
            bw_recommended_provider_spec = bw_get_provider(
                bw_recommended_provider, include_cloud=True
            )
            bw_ready = bw_provider_readiness(bw_provider_id, local_first=bw_local_first)
            bw_models = bw_list_models()
            bw_downloaded = bw_downloaded_model_ids()
            bw_engine_ok, bw_engine_status = faster_whisper_status()
            for name, value in [
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
            ]:
                status_rows.append(("BITS Whisperer", name, str(value)))

        for name, value in [
            ("Engine", settings.read_aloud_engine),
            ("Voice (SAPI 5)", settings.read_aloud_voice or "(default system)"),
            ("DECtalk executable", settings.read_aloud_dectalk_executable or "Not configured"),
            ("DECtalk voice", settings.read_aloud_dectalk_voice),
            ("Piper model", settings.read_aloud_piper_model or "Not configured"),
            ("Kokoro voice", settings.read_aloud_kokoro_voice),
            ("eSpeak executable", settings.read_aloud_espeak_executable or "PATH lookup"),
            ("eSpeak English voice", settings.read_aloud_espeak_voice),
        ]:
            status_rows.append(("Speech", name, str(value)))

        task_rows: list[tuple[str, str, str, str, str]] = []
        for entry in sorted(
            self._bw_download_status.values(),
            key=lambda item: str(item.get("started_at", "")),
            reverse=True,
        ):
            task_rows.append((
                str(entry.get("model", "")),
                str(entry.get("status", "")),
                str(entry.get("progress", "")),
                str(entry.get("started_at", "")),
                str(entry.get("finished_at", "Running")),
            ))
        for task in reversed(getattr(self, "_background_tasks", [])[-50:]):
            task_rows.append((
                str(task.get("label", "")),
                str(task.get("status", "")).title(),
                str(task.get("progress", "")),
                str(task.get("started_at", "")),
                str(task.get("finished_at", "") or "Running"),
            ))

        feature_rows: list[tuple[str, str, str, str]] = []
        for feature_id, definition in sorted(FEATURE_DEFINITIONS.items()):
            state = self.features.state_for(feature_id)
            state_label = {"on": "Enabled", "quiet": "Quiet", "off": "Disabled"}.get(state, state)
            feature_rows.append((feature_id, definition.name, definition.category, state_label))

        actions = []
        if self.features.is_enabled("core.bw_whisperer"):
            actions += [
                "Open BITS Whisperer > Providers > Provider Center for staged onboarding guidance.",
                "Open BITS Whisperer > Speech Models to choose recommended or manual model setup.",
            ]
        actions += [
            "Open AI > Speech > Settings to configure engine-specific paths.",
            "Open AI > Speech > Voice to preview voices and variants.",
            "Open AI > Speech > Generate Audio to run asynchronous speech output jobs.",
            "Open Tools > Support > Show Notifications for detailed alerts and outcomes.",
        ]
        return {
            "status_rows": status_rows,
            "task_rows": task_rows,
            "feature_rows": feature_rows,
            "actions": actions,
        }

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

        markup_kind = self._effective_markup_kind()
        snippet = build_link_text(markup_kind, display_text, url)
        result = InsertionResult(inserted_text=snippet, caret_offset=len(snippet))
        self._apply_insertion_result(result)
        self._set_status(f"Inserted link ({markup_kind})")

    def insert_citation(self) -> None:
        """Build a formatted citation from typed fields and insert it (#203)."""
        from quill.core.citations import (
            CITATION_STYLES,
            SOURCE_TYPES,
            Source,
            format_bibliography_entry,
            format_in_text,
        )
        from quill.ui.web_form import show_web_form

        values = show_web_form(
            self.frame,
            self._wx,
            title="Insert Citation",
            intro=(
                "Enter the source details, choose a style, and pick what to insert. "
                "Separate multiple authors with a semicolon (First Last; First Last)."
            ),
            save_label="Insert",
            fields=[
                {
                    "name": "source_type",
                    "label": "Source type",
                    "type": "select",
                    "value": "book",
                    "options": list(SOURCE_TYPES),
                },
                {
                    "name": "style",
                    "label": "Citation style",
                    "type": "select",
                    "value": "mla",
                    "options": list(CITATION_STYLES),
                },
                {
                    "name": "insert",
                    "label": "Insert",
                    "type": "select",
                    "value": "bibliography",
                    "options": [
                        ("bibliography", "Bibliography entry"),
                        ("in_text", "In-text citation"),
                        ("both", "Both"),
                    ],
                },
                {"name": "authors", "label": "Author(s)", "type": "text", "value": ""},
                {"name": "title", "label": "Title", "type": "text", "value": ""},
                {
                    "name": "container",
                    "label": "Journal or website name",
                    "type": "text",
                    "value": "",
                },
                {"name": "publisher", "label": "Publisher (books)", "type": "text", "value": ""},
                {"name": "year", "label": "Year", "type": "text", "value": ""},
                {"name": "volume", "label": "Volume", "type": "text", "value": ""},
                {"name": "issue", "label": "Issue", "type": "text", "value": ""},
                {"name": "pages", "label": "Pages", "type": "text", "value": ""},
                {"name": "url", "label": "URL", "type": "text", "value": ""},
                {"name": "accessed", "label": "Accessed date", "type": "text", "value": ""},
            ],
        )
        if values is None:
            self._set_status("Insert citation cancelled")
            return
        authors = tuple(a.strip() for a in str(values.get("authors", "")).split(";") if a.strip())
        source = Source(
            source_type=str(values.get("source_type", "book")),
            authors=authors,
            title=str(values.get("title", "")).strip(),
            container=str(values.get("container", "")).strip(),
            publisher=str(values.get("publisher", "")).strip(),
            year=str(values.get("year", "")).strip(),
            volume=str(values.get("volume", "")).strip(),
            issue=str(values.get("issue", "")).strip(),
            pages=str(values.get("pages", "")).strip(),
            url=str(values.get("url", "")).strip(),
            accessed=str(values.get("accessed", "")).strip(),
        )
        style = str(values.get("style", "mla"))
        try:
            in_text = format_in_text(source, style)
            entry = format_bibliography_entry(source, style)
        except ValueError as error:
            self._set_status(f"Could not format citation: {error}")
            return
        mode = str(values.get("insert", "bibliography"))
        if mode == "in_text":
            snippet = in_text
        elif mode == "both":
            snippet = f"{in_text}\n\n{entry}"
        else:
            snippet = entry
        result = InsertionResult(inserted_text=snippet, caret_offset=len(snippet))
        self._apply_insertion_result(result)
        self._set_status(f"Inserted {style.upper()} citation")

    def open_snippet_gallery(self) -> None:
        """Browse and insert Quillin-contributed gallery snippets (Part 3)."""
        wx = self._wx
        collect = getattr(self, "collect_snippet_gallery", None)
        entries = collect() if callable(collect) else []
        if not entries:
            self._set_status("No gallery snippets are available.")
            return

        from quill.ui.dialog_contract import apply_modal_ids

        dialog = wx.Dialog(
            self.frame,
            title="Snippet Gallery",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        body = wx.BoxSizer(wx.VERTICAL)
        body.Add(
            wx.StaticText(
                dialog,
                label="Choose a snippet, review its preview, then Insert.",
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )

        labels = [
            f"Snippet: {entry.name} ({quillin_name})" for quillin_name, _qid, entry in entries
        ]
        chooser = wx.ListBox(dialog, choices=labels)
        chooser.SetName("Gallery snippets")
        chooser.SetSelection(0)
        body.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)

        body.Add(wx.StaticText(dialog, label="&Preview"), 0, wx.LEFT | wx.RIGHT, 8)
        preview = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        preview.SetName("Snippet preview")
        body.Add(preview, 1, wx.ALL | wx.EXPAND, 8)

        insert_button = wx.Button(dialog, id=wx.ID_OK, label="&Insert")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="&Cancel")
        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.AddButton(insert_button)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()
        body.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 8)

        dialog.SetSizerAndFit(body)
        dialog.SetSize((600, 520))
        if hasattr(dialog, "CentreOnParent"):
            dialog.CentreOnParent()

        def selected_entry() -> object | None:
            index = chooser.GetSelection()
            if index < 0 or index >= len(entries):
                return None
            return entries[index]

        def refresh_preview() -> None:
            chosen = selected_entry()
            if chosen is None:
                preview.SetValue("")
                return
            quillin_name, _qid, entry = chosen
            preview.SetValue(entry.body)
            self._announce(f"{entry.name} from {quillin_name}")

        chooser.Bind(wx.EVT_LISTBOX, lambda _e: refresh_preview())
        insert_button.SetDefault()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        refresh_preview()

        call_after = getattr(wx, "CallAfter", None)
        if callable(call_after):
            call_after(chooser.SetFocus)
        else:
            chooser.SetFocus()

        try:
            if self._show_modal_dialog(dialog, "Snippet Gallery") != wx.ID_OK:
                return
            chosen = selected_entry()
        finally:
            dialog.Destroy()
        if chosen is None:
            return
        _quillin_name, _qid, entry = chosen
        if entry.params:
            text = self._prompt_snippet_params(entry)
            if text is None:
                self._set_status("Snippet insertion cancelled")
                return
        else:
            text = entry.body
        self._insert_gallery_snippet_text(text)
        self._set_status(f"Inserted snippet {entry.name}")

    def _prompt_snippet_params(self, entry: object) -> str | None:
        """Prompt for each gallery-snippet param and return the expanded body.

        Returns ``None`` if the user cancels any prompt. Each prompt routes
        through the shared single-line dialog so it keeps the keyboard/screen
        reader contract and can be cancelled cleanly (unlike GetTextFromUser,
        which cannot distinguish Cancel from an empty answer).
        """
        values: dict[str, str] = {}
        for param in entry.params:  # type: ignore[attr-defined]
            answer = self._power_tools_prompt_single("Snippet Gallery", param.label, param.default)
            if answer is None:
                return None
            values[param.name] = answer
        body: str = entry.body  # type: ignore[attr-defined]
        for name, value in values.items():
            body = body.replace("{" + name + "}", value)
        return body

    def _insert_gallery_snippet_text(self, text: str) -> None:
        """Insert gallery text at the cursor (or replace the selection)."""
        editor = self.editor
        start, end = editor.GetSelection()
        if start == end:
            editor.WriteText(text)
        else:
            editor.Replace(start, end, text)

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

    def _write_browser_preview(self, tab_index: int) -> tuple[Path, str]:
        """Render the tab's preview HTML to its stable on-disk path.

        Shared by the explicit Preview in Browser command and the silent
        keep-fresh path; only the explicit command opens the browser.
        Returns the file path and the page title.
        """
        tab = self._document_tabs[tab_index]
        text = tab.editor.GetValue()
        kind = guess_preview_kind(tab.document.path, text)
        anchor = preview_anchor_for_text(text, tab.editor.GetInsertionPoint(), kind)
        text = self._vault_preview_text(text, kind, tab.document.path)
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
        return preview_path, title

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
        preview_path, title = self._write_browser_preview(tab_index)
        browser_choice = normalize_browser_choice(self.settings.preview_browser)
        session = self._browser_preview_session
        is_new = (
            session is None
            or session.tab_index != tab_index
            or session.preview_path != preview_path
            or session.browser_choice != browser_choice
        )
        # Opening the browser happens ONLY here, on the explicit user command.
        # The keep-fresh path (_do_refresh_browser_preview) rewrites the file so
        # a reload in the browser shows current text, but never opens a tab —
        # re-opening on every typing pause spammed new tabs (#780 review).
        open_preview_url(preview_path.as_uri(), browser_choice)
        self._browser_preview_session = _BrowserPreviewSession(
            tab_index=tab_index,
            preview_path=preview_path,
            browser_choice=browser_choice,
            title=title,
        )
        opened = f"Opened browser preview in {browser_choice_label_for_value(browser_choice)}"
        self._set_status(opened if is_new else "Refreshed browser preview")

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
        body = render_preview_body(
            self._vault_preview_text(text, kind, tab.document.path),
            kind,
            dark=self._preview_is_dark(),
        )

        # #179: WebView2's first ``New()`` call blocks the UI thread for tens
        # of seconds.  If the deferred warm-up has not finished, defer the
        # preview with a short status nudge so the editor stays responsive.
        if not self._webview_warm:
            self._set_status("Preparing preview... (one-time WebView2 setup)")
            self._wx.CallLater(500, self._show_preview_in_app, title, body, anchor)
            return

        self._show_preview_in_app(title, body, anchor)

    def _show_preview_in_app(self, title: str, body: str, anchor: str | None) -> None:
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
        text = self._vault_preview_text(text, kind, tab.document.path)
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
            #
            # Diagnostics: time this call and log it. WebView2's first New() is
            # the prime suspect for the ~7 s UI-thread stall (review.md §5); this
            # New() runs on the UI thread and cannot be moved off it, so if it is
            # the cause the elapsed here will show it directly in the log. Logged
            # at WARNING when it blocks noticeably so it is findable without
            # enabling QUILL_PROFILE_STARTUP.
            import logging as _logging

            _wv_start = time.perf_counter()
            wv = wx.html2.WebView.New(sentinel)
            _wv_elapsed = time.perf_counter() - _wv_start
            _wv_log = _logging.getLogger(__name__)
            if _wv_elapsed >= 1.0:
                _wv_log.warning(
                    "WebView2 first-init (WebView.New) blocked the UI thread for %.1f s",
                    _wv_elapsed,
                )
            else:
                # INFO (not DEBUG) so the timing is visible at the default level.
                _wv_log.info("WebView2 first-init took %.3f s", _wv_elapsed)

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
                # #179: once the sentinel has loaded (or the 5 s fallback has
                # fired) the WebView2 subprocess is up.  ``_on_update_fetch_done``
                # and ``preview_in_app`` read this flag to decide whether to
                # defer their WebView2 dialog until warm-up completes.
                self._webview_warm = True

            wv.Bind(wx.html2.EVT_WEBVIEW_LOADED, _cleanup)
            self._wx.CallLater(5000, _cleanup)
        except Exception:
            # No wx.html2 — WebView2 is unavailable on this build.  Treat
            # that as "warm" so we don't keep deferring previews forever.
            self._webview_warm = True

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
        # Debounce like the side preview: re-navigating the external browser on
        # every keystroke flickered the page and re-announced from the top for a
        # braille/screen-reader reader (the "meta refresh" feel). Coalescing to
        # shortly after typing pauses cuts the reload churn; the page also
        # restores scroll on reload (render_preview_html). The fully flicker-free
        # live option is the in-app side preview (F6): in-place WebView swap.
        timer = getattr(self, "_browser_preview_timer", None)
        if timer is not None and timer.IsRunning():
            timer.Stop()
        self._browser_preview_timer = self._wx.CallLater(400, self._do_refresh_browser_preview)

    def _do_refresh_browser_preview(self) -> None:
        session = self._browser_preview_session
        if session is None or session.tab_index != self._active_tab_index:
            return
        if session.tab_index < 0 or session.tab_index >= len(self._document_tabs):
            return
        # Rewrite the file only; never open the browser from the typing path
        # (that spawned a new tab on every pause — #780 review finding).
        self._write_browser_preview(session.tab_index)

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
        from quill.ui.train_style_dialog import TrainStyleDialog

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
        # Guard against missing menu bar (frame stubbed in tests, or
        # _flush_pending_menu_refresh running during __init__).
        get_menu_bar = getattr(self.frame, "GetMenuBar", None)
        if not callable(get_menu_bar):
            return
        bar = get_menu_bar()
        if bar is None:
            return
        enabled = load_ai_enabled()
        ai_item_ids = (
            self._id_ai_hub,
            self._id_ask_quill_chat,
            self._id_ask_quill_voice,
            self._id_ai_model,
            self._id_ai_switch_engine,
            self._id_ai_copilot_setup,
            self._id_ai_session_browser,
            self._id_ai_assistant,
            self._id_ai_prompt_studio,
            self._id_ai_agent_center,
            self._id_ai_rewrite_selection,
            self._id_ai_summarize_selection,
            self._id_ai_expand_selection,
            self._id_ai_generate_toc,
            self._id_ai_thesaurus,
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
        self._open_ask_quill(voice_mode=False)

    def open_ask_quill_conversation(self, initial_prompt: str = "") -> None:
        """Open Ask Quill in voice conversation mode (Alt+Shift+Q).

        Same chat, but spoken answers play with transport controls when text-to-
        speech is available, and Ctrl+F9 captures a spoken question. Falls back to
        text + screen-reader announcements when voice I/O is unavailable.

        ``initial_prompt`` (Hey QUILL Phase 4) pre-fills the composer from a
        routed voice question so the user can confirm and send it.
        """
        self._open_ask_quill(voice_mode=True, initial_prompt=initial_prompt)

    def _open_ask_quill(self, *, voice_mode: bool, initial_prompt: str = "") -> None:
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.ai.onboarding import active_connection_consented, ai_connection_ready
        from quill.ui.assistant_panel import AskQuillChatDialog

        # Offer setup not only when AI is off, but also when it's on yet the connection
        # isn't usable (no provider/key) or the active provider has no standing share
        # consent. Without consent QUILL must not send anything, so route to setup (where
        # the allow checkbox lives) instead of failing or hanging at request time.
        if not load_ai_enabled() or not ai_connection_ready() or not active_connection_consented():
            from quill.ui.ai_setup_wizard import maybe_offer_ai_setup

            if not maybe_offer_ai_setup(self, reason="Ask Quill needs AI to chat with you."):
                from quill.core.ai.availability import AI_DISABLED_MESSAGE

                self._set_status(AI_DISABLED_MESSAGE)
                return

        self._apply_style_to_assistant()
        tool_catalog = allowed_tools(self.commands, getattr(self, "features", None))
        voice = self._build_voice_services()
        open_player = None
        if voice is not None and voice.output_available():
            from quill.ui.speech_player_dialog import show_speech_player

            def open_player(text: str) -> None:
                show_speech_player(self, voice, text)

        # Modeless chat: if one is already open, just bring it forward.
        existing = getattr(self, "_ask_quill_dialog", None)
        if existing is not None:
            try:
                existing.dialog.Raise()
                existing.dialog.SetFocus()
                return
            except Exception:  # noqa: BLE001 - stale handle; fall through and reopen
                self._ask_quill_dialog = None

        dialog = AskQuillChatDialog(
            self.frame,
            self._get_assistant(),
            get_document=lambda: self.editor.GetValue(),
            get_selection=lambda: self.editor.GetStringSelection(),
            insert_text=self._ai_insert_text,
            replace_selection=self._ai_replace_selection,
            set_text=self._ai_set_document_text,
            open_new_document=self._ai_open_new_document,
            run_command=self._ai_run_command,
            tool_catalog=tool_catalog,
            announce=self._set_status,
            review_changes=self.open_ai_diff_review,
            conversation=self._build_companion_conversation(),
            voice_mode=voice_mode,
            voice=voice,
            signal_sound=self._signal_ai_sound,
            open_speech_player=open_player,
            rebuild_conversation=self._build_companion_conversation,
            initial_prompt=initial_prompt,
        )
        # Open modeless so the user can keep working with the chat alongside the document.
        # The frame keeps its normal menu bar (a wx.Dialog can't host one, and swapping the
        # frame's bar left the menu unreachable from the focused dialog). Every chat action
        # is a button in the dialog, so no menu bar is needed here.
        self._ask_quill_dialog = dialog
        dialog.show_modeless(on_close=self._on_ask_quill_closed)

    def _on_ask_quill_closed(self) -> None:
        """Drop the chat handle and refresh the menu (reflects any AI state change)."""
        self._ask_quill_dialog = None
        try:
            self._build_menu()  # reflect provider/AI-state changes made while chat was open
        except Exception:  # noqa: BLE001 - never let a menu refresh crash on close
            pass

    def _signal_ai_sound(self, name: str) -> None:
        """Play an AI earcon for the chat ('thinking' / 'response' / 'error')."""
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        event = {
            "thinking": SoundEvent.AI_THINKING_STARTED,
            "response": SoundEvent.AI_RESPONSE_RECEIVED,
            "error": SoundEvent.AI_ERROR,
        }.get(name)
        if event is not None:
            try:
                post_sound(event)
            except Exception:  # noqa: BLE001 - a missing earcon must never break chat
                pass

    def _build_voice_services(self):
        """Build VoiceServices for the chat, or None when voice I/O is unavailable.

        Resolves an installed speech-to-text model (for Ctrl+F9 voice questions) and
        an OpenAI key (for spoken answers + Save as media). Each piece degrades
        independently: no mic/model => text input only; no TTS key => screen-reader
        announcements instead of an audio player.
        """
        if getattr(self, "_safe_mode", False):
            return None
        try:
            from quill.ui.voice_services import VoiceServices
        except Exception:  # noqa: BLE001
            return None

        provider = None
        model_id = ""
        get_provider = getattr(self, "_speech_provider", None)
        if callable(get_provider):
            try:
                candidate = get_provider()
                if candidate is not None and candidate.is_available():
                    provider = candidate
                    installed = candidate.list_installed_models()
                    if installed:
                        first = installed[0]
                        model_id = getattr(first, "model_id", "") or getattr(first, "id", "")
            except Exception:  # noqa: BLE001
                provider, model_id = None, ""

        device_index = -1
        try:
            from quill.core.speech.service import load_input_device

            device_index = load_input_device()
        except Exception:  # noqa: BLE001
            device_index = -1

        tts_key = ""
        try:
            from quill.core.assistant_ai import (
                load_assistant_api_key,
                load_assistant_connection_settings,
            )

            conn = load_assistant_connection_settings()
            if (conn.provider or "").strip().lower() == "openai":
                tts_key = load_assistant_api_key() or ""
        except Exception:  # noqa: BLE001
            tts_key = ""

        return VoiceServices(
            stt_provider=provider,
            stt_model_id=model_id,
            device_index=device_index,
            tts_api_key=tts_key,
        )

    def _build_companion_conversation(self):
        """Build the Phase 1 conversational companion callable, or None to fall back.

        Returns a ``(message, document, selection) -> (answer, edited, error)``
        callable backed by a :class:`ConversationSession` (multi-step tool loop
        through the Safe Editor Tool Gateway), or None when Safe Mode is on or no
        AI provider is available — in which case the dialog uses the legacy path.
        """
        if getattr(self, "_safe_mode", False):
            return None
        try:
            from quill.ui.agent_editor_host import build_companion_session

            session, _engine = build_companion_session(self)
        except Exception:  # noqa: BLE001 - never block the chat from opening
            return None
        if session is None:
            return None

        # Consent is a one-time, per-provider decision made at setup (the wizard's allow
        # checkbox), not a per-chat-session prompt. A provider with standing consent sends
        # with no preview; a provider without it is blocked here (covers a mid-chat provider
        # switch, or a provider configured outside the wizard). Redaction always applies.
        def conversation(message: str, document: str, selection: str):
            from quill.core.ai.onboarding import active_connection_consented
            from quill.core.ai.providers import provider_display_name
            from quill.core.assistant_ai import load_assistant_connection_settings
            from quill.ui.agent_editor_host import prepare_companion_context

            if not active_connection_consented():
                try:
                    pid = load_assistant_connection_settings().provider.strip().lower()
                    name = provider_display_name(pid) if pid else "this provider"
                except Exception:  # noqa: BLE001
                    name = "this provider"
                return (
                    f"{name} isn't allowed to use your writing yet. Open the AI menu, run "
                    "AI Setup, and check the allow box for it — then try again.",
                    False,
                    "",
                )
            context_text, _ok = prepare_companion_context(
                self, document, selection, need_consent=False
            )
            result = session.ask(message, context_text=context_text)
            return result.answer, result.edited, result.error

        return conversation

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
            announce_cb=self._announce,
        )
        self._show_modal_dialog(dlg.dialog, "Prompt Library")
        dlg.close()

    def open_ai_library(self) -> None:
        from quill.ui.ai_library_dialog import open_ai_library

        open_ai_library(self)

    def open_skill_library(self) -> None:
        from quill.ui.skill_library_dialog import open_skill_library

        open_skill_library(self)

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
        # Route through the unified AI Hub connection (ProviderChatBackend), the same
        # path Ask Quill and the AI Library use. The old code read the key from a
        # separate "quill-<provider>-api-key" credential and ai_chat_* settings the
        # setup wizard never writes, so it failed to find a configured key.
        if self._ai_require_connection() is None:
            return
        from quill.core.ai.provider_backend import ProviderChatBackend

        backend = ProviderChatBackend()
        model_id, provider_id = backend.settings.model, backend.settings.provider
        prompt_text = grammar.text.replace("{selection}", selection)
        self._announce(f"Checking grammar with {model_id}...")

        def run() -> None:
            import wx as _wx

            try:
                result = backend.respond(prompt_text)
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

    # ------------------------------------------------------------------
    # AI language tools: spell check, grammar, translation, transcription
    # ------------------------------------------------------------------

    def _ai_require_connection(self) -> tuple[object, str] | None:
        """Return (connection, api_key), or offer AI setup and return None.

        The single choke point for keyed AI text features (spell/grammar check,
        translate, Document Q&A, thesaurus, agent tasks). When AI is off or not
        yet configured, it offers the setup wizard — an actionable dialog — rather
        than dead-ending into a status line a screen-reader user can miss. This
        mirrors what Ask Quill, Transcript Actions, and the AI Library already do,
        so every keyed feature behaves the same when AI isn't ready.
        """
        from quill.core.assistant_ai import (
            load_assistant_api_key,
            load_assistant_connection_settings,
        )
        from quill.ui.ai_setup_wizard import maybe_offer_ai_setup

        if not maybe_offer_ai_setup(self, reason="To use this AI feature, QUILL needs AI."):
            self._set_status("AI isn't set up. Use AI > Set Up AI, or turn on AI in the AI menu.")
            return None
        conn = load_assistant_connection_settings()
        api_key = load_assistant_api_key() or ""
        return conn, api_key

    def ai_spell_check(self) -> None:
        result = self._ai_require_connection()
        if result is None:
            return
        conn, api_key = result
        text = str(self.editor.GetValue())
        if not text.strip():
            self._set_status("Document is empty.")
            return

        self._set_status("AI spell check running...")

        import threading

        def _run() -> None:
            import wx as _wx

            try:
                from quill.core.ai.spell_check import ai_spell_check

                corrections = ai_spell_check(text, conn, api_key)
            except Exception as exc:  # noqa: BLE001
                _wx.CallAfter(self._set_status, f"AI spell check failed: {exc}")
                return
            _wx.CallAfter(self._show_ai_spell_check_dialog, text, corrections)

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def _show_ai_spell_check_dialog(self, text: str, corrections: list) -> None:
        if not corrections:
            self._set_status("AI spell check: no issues found.")
            return
        from quill.ui.ai_spell_check_dialog import AISpellCheckDialog

        dlg = AISpellCheckDialog(self.frame, text, corrections, self._show_modal_dialog)
        new_text, count = dlg.show()
        if count > 0:
            self.editor.SetValue(new_text)
            self._set_status(f"AI spell check: {count} correction(s) applied.")
        else:
            self._set_status("AI spell check: no corrections applied.")

    def ai_spell_check_interactive(self) -> None:
        result = self._ai_require_connection()
        if result is None:
            return
        conn, api_key = result
        text = str(self.editor.GetValue())
        if not text.strip():
            self._set_status("Document is empty.")
            return
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text]
        from quill.core.ai.spell_check import apply_corrections
        from quill.ui.ai_spell_check_dialog import AISpellCheckInteractiveDialog

        def _apply_accepted(accepted_corrections: list) -> None:
            current = str(self.editor.GetValue())
            new_text, count = apply_corrections(current, accepted_corrections)
            if count > 0:
                self.editor.SetValue(new_text)
                self._set_status(f"AI spell check: {count} correction(s) applied.")

        dlg = AISpellCheckInteractiveDialog(
            self.frame, paragraphs, conn, api_key, self._show_modal_dialog, _apply_accepted
        )
        dlg.run()

    def ai_grammar_style_check(self) -> None:
        result = self._ai_require_connection()
        if result is None:
            return
        conn, api_key = result
        text = str(self.editor.GetValue())
        if not text.strip():
            self._set_status("Document is empty.")
            return

        self._set_status("AI grammar check running...")

        import threading

        def _run() -> None:
            import wx as _wx

            try:
                from quill.core.ai.grammar_check import ai_grammar_check

                issues = ai_grammar_check(text, conn, api_key)
            except Exception as exc:  # noqa: BLE001
                _wx.CallAfter(self._set_status, f"AI grammar check failed: {exc}")
                return
            _wx.CallAfter(self._show_ai_grammar_dialog, text, issues)

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def _show_ai_grammar_dialog(self, text: str, issues: list) -> None:
        if not issues:
            self._set_status("AI grammar check: no issues found.")
            return
        from quill.ui.ai_grammar_check_dialog import AIGrammarCheckDialog

        dlg = AIGrammarCheckDialog(self.frame, text, issues, self._show_modal_dialog)
        new_text, count = dlg.show()
        if count > 0:
            self.editor.SetValue(new_text)
            self._set_status(f"AI grammar check: {count} fix(es) applied.")
        else:
            self._set_status("AI grammar check: no fixes applied.")

    def ai_translate_selection(self) -> None:
        self._ai_translate(selection_only=True)

    def ai_translate_document(self) -> None:
        self._ai_translate(selection_only=False)

    def _ai_translate(self, selection_only: bool) -> None:
        result = self._ai_require_connection()
        if result is None:
            return
        conn, api_key = result
        if selection_only:
            text = str(self.editor.GetStringSelection())
            desc = "selection"
        else:
            text = str(self.editor.GetValue())
            desc = "document"
        if not text.strip():
            self._set_status(f"No {desc} text to translate.")
            return

        from quill.core.ai.translation import translate_text

        def _on_translate(t: str, lang: str, provider: str, lt_url: str) -> tuple[str, str]:
            return translate_text(t, lang, conn, api_key, provider, lt_url)

        def _on_replace(new_text: str) -> None:
            if selection_only:
                start, end = self.editor.GetSelection()
                if start != end:
                    self.editor.Replace(start, end, new_text)
            else:
                self.editor.SetValue(new_text)
            self._set_status("Translation applied.")

        def _on_new_doc(new_text: str, lang_name: str) -> None:
            self._power_tools_open_text_in_new_buffer(
                new_text, f"Opened translation ({lang_name}) in new document"
            )

        from quill.ui.ai_translation_dialog import AITranslationDialog

        dlg = AITranslationDialog(
            self.frame,
            text,
            desc,
            self._show_modal_dialog,
            _on_translate,
            _on_replace,
            _on_new_doc,
        )
        dlg.show()

    def ai_transcribe_audio_file(self) -> None:
        self._ai_open_transcribe_dialog(translate_to_english=False)

    def ai_translate_audio_file(self) -> None:
        self._ai_open_transcribe_dialog(translate_to_english=True)

    def _ai_open_transcribe_dialog(self, translate_to_english: bool = False) -> None:
        import threading

        from quill.ui.ai_transcribe_dialog import (
            AIProgressDialog,
            AITranscribeDialog,
        )

        openai_key = self._get_openai_api_key()
        if not openai_key:
            self._show_message_box(
                "Cloud audio transcription uses OpenAI Whisper, which needs an "
                "OpenAI API key. Open the AI Hub to add an OpenAI key, or use "
                "Tools > Speech > Transcribe Audio or Video (Offline) to "
                "transcribe on this device with no key and no internet.",
                "OpenAI Key Needed for Transcription",
                self._wx.OK | self._wx.ICON_INFORMATION,
            )
            return

        def _on_transcribe(path, lang_code, translate, diarize, max_speakers):
            if diarize:
                deepgram_key = self._get_deepgram_api_key()
                if not deepgram_key:
                    self._show_message_box(
                        "Speaker identification uses Deepgram, which needs its own "
                        "Deepgram API key. Add one in AI Hub > Audio, or clear the "
                        "'Identify different speakers' checkbox to transcribe with "
                        "OpenAI Whisper instead.",
                        "Deepgram Key Needed for Speaker Identification",
                        self._wx.OK | self._wx.ICON_INFORMATION,
                    )
                    return
            else:
                deepgram_key = ""
            label = "Translating Audio" if translate else "Transcribing Audio"
            progress = AIProgressDialog(
                self.frame,
                label,
                f"{'Translating' if translate else 'Transcribing'} {path.name}...",
            )
            progress.show()

            def _run():
                import wx as _wx

                try:
                    if diarize:
                        from quill.core.ai.diarization import diarize_file, format_diarization

                        dr = diarize_file(path, "deepgram", deepgram_key, max_speakers)
                        transcript = format_diarization(dr)
                    elif translate:
                        from quill.core.ai.transcription import translate_file

                        transcript = translate_file(path, openai_key)
                    else:
                        from quill.core.ai.transcription import transcribe_file

                        transcript = transcribe_file(path, openai_key, language=lang_code)
                except Exception as exc:  # noqa: BLE001
                    _wx.CallAfter(progress.close)
                    detail = str(exc)
                    lowered = detail.lower()
                    if "401" in detail or "unauthor" in lowered or "invalid_api_key" in lowered:
                        message = (
                            "Transcription failed: OpenAI rejected the API key (401). "
                            "Check your OpenAI key in the AI Hub."
                        )
                    else:
                        message = f"Transcription failed: {detail}"
                    _wx.CallAfter(self._set_status, message)
                    return
                _wx.CallAfter(progress.close)
                _wx.CallAfter(self._show_transcription_result, transcript, path.name)

            threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

        dlg = AITranscribeDialog(self.frame, self._show_modal_dialog, _on_transcribe)
        if translate_to_english:
            dlg._translate_cb.SetValue(True)
        dlg.show()

    def _show_transcription_result(self, transcript: str, file_name: str) -> None:
        # The Listening Companion: first ask "what would you like me to make of this?"
        # and run the chosen Transcript Action. If AI is off/unreachable or the user
        # opts out, fall back to the plain transcript result below.
        from quill.ui.transcript_actions_ui import offer_transcript_actions

        if offer_transcript_actions(self, transcript, file_name):
            return

        from quill.ui.ai_transcribe_dialog import AITranscriptionResultDialog

        def _on_insert(text: str) -> None:
            self.editor.WriteText(text)

        def _on_new_doc(text: str) -> None:
            self._power_tools_open_text_in_new_buffer(
                text, f"Opened transcript ({file_name}) in new document"
            )

        dlg = AITranscriptionResultDialog(
            self.frame,
            transcript,
            file_name,
            self._show_modal_dialog,
            _on_insert,
            _on_new_doc,
        )
        dlg.show()

    def _get_openai_api_key(self) -> str:
        """Return the OpenAI API key, or '' if none.

        Whisper transcription/translation and OpenAI TTS always call OpenAI, so
        they need the OpenAI key specifically — not whatever provider the
        assistant happens to be set to. Using the active assistant key here sent
        (say) an Anthropic key to OpenAI and produced a confusing 401.
        """
        try:
            from quill.core.assistant_ai import load_keyed_provider_api_key

            return load_keyed_provider_api_key("openai")
        except Exception:  # noqa: BLE001
            return ""

    def _get_gemini_api_key(self) -> str:
        """Return the stored Google Gemini API key, or '' if none."""
        try:
            from quill.core.assistant_ai import load_provider_api_key

            return load_provider_api_key("gemini") or ""
        except Exception:  # noqa: BLE001
            return ""

    def _get_deepgram_api_key(self) -> str:
        """Return the stored Deepgram API key (AI Hub > Audio), or '' if none.

        Speaker diarization calls Deepgram, which needs its own key — not the
        OpenAI key the rest of the transcribe flow uses.
        """
        try:
            from quill.platform.windows.credential_manager import load_generic_credential

            stored = load_generic_credential("QUILL_DEEPGRAM_API_KEY")
            return (stored.secret if stored else "") or ""
        except Exception:  # noqa: BLE001
            return ""

    def _get_elevenlabs_api_key(self) -> str:
        """Return the stored 'ElevenLabs API key' credential, or '' if none.

        Reuses the single ElevenLabs credential label the transcription provider
        already uses, so one key unlocks both STT and the export TTS provider.
        """
        try:
            from quill.platform.windows.credential_manager import load_generic_credential

            stored = load_generic_credential("ElevenLabs API key")
            return (stored.secret if stored else "") or ""
        except Exception:  # noqa: BLE001
            return ""

    def _resolve_ai_tts_config(self) -> tuple[str, str, str, float, str, str]:
        """Return (provider, model, voice, speed, api_key, key_hint) for AI Voice.

        Falls back to each provider's default model/voice when settings are blank.
        ``key_hint`` is the status message to show when ``api_key`` is empty.
        """
        from quill.core.ai import cloud_tts

        s = self.settings
        provider = (getattr(s, "ai_tts_provider", "openai") or "openai").strip().lower()
        if provider not in cloud_tts.PROVIDERS:
            provider = "openai"
        model = (getattr(s, "ai_tts_model", "") or "").strip() or cloud_tts.default_model(provider)
        voice = (getattr(s, "ai_tts_voice", "") or "").strip() or cloud_tts.default_voice(provider)
        try:
            speed = float(getattr(s, "ai_tts_speed", 1.0))
        except (TypeError, ValueError):
            speed = 1.0
        if provider == "gemini":
            api_key = self._get_gemini_api_key()
            key_hint = "Gemini API key not configured. Open AI Hub to add your Gemini key."
        elif provider == "elevenlabs":
            api_key = self._get_elevenlabs_api_key()
            key_hint = (
                "ElevenLabs API key not configured. Add an 'ElevenLabs API key' "
                "credential (the same key the ElevenLabs transcription provider uses)."
            )
        else:
            api_key = self._get_openai_api_key()
            key_hint = "OpenAI API key not configured. Open AI Hub to add your key."
        return provider, model, voice, speed, api_key, key_hint

    # ------------------------------------------------------------------
    # AI TTS: Read Aloud via OpenAI TTS provider
    # ------------------------------------------------------------------

    def ai_tts_read_selection(self) -> None:
        text = str(self.editor.GetStringSelection()).strip()
        if not text:
            self._set_status("No text selected. Select text first, then use Read Selection Aloud.")
            return
        self._ai_tts_speak(text, source="selection")

    def ai_tts_read_document(self) -> None:
        text = str(self.editor.GetValue()).strip()
        if not text:
            self._set_status("Document is empty.")
            return
        self._ai_tts_speak(text, source="document")

    def ai_tts_stop(self) -> None:
        stop_evt = getattr(self, "_ai_tts_stop_event", None)
        if stop_evt is not None:
            stop_evt.set()
        self._set_status("AI reading stopped.")

    def _ai_tts_speak(self, text: str, source: str) -> None:
        import threading

        from quill.core.ai import cloud_tts
        from quill.core.ai.tts import TTSError

        provider, model, voice, speed, api_key, key_hint = self._resolve_ai_tts_config()
        if not api_key:
            self._set_status(key_hint)
            return

        # Cancel any in-progress TTS
        old_stop = getattr(self, "_ai_tts_stop_event", None)
        if old_stop is not None:
            old_stop.set()

        stop_event = threading.Event()
        self._ai_tts_stop_event = stop_event

        word_count = len(text.split())
        self._set_status(
            f"AI reading {source} ({word_count} words) with {cloud_tts.provider_label(provider)} "
            f"voice {voice}..."
        )

        def _run() -> None:
            import wx as _wx

            try:
                cloud_tts.speak_text(
                    provider,
                    text,
                    api_key,
                    model=model,
                    voice=voice,
                    speed=speed,
                    on_chunk_complete=None,
                    stop_event=stop_event,
                )
                if not stop_event.is_set():
                    _wx.CallAfter(self._set_status, "AI reading complete.")
            except TTSError as exc:
                _wx.CallAfter(self._set_status, f"AI reading failed: {exc}")

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def ai_tts_export_mp3(self) -> None:
        import wx

        from quill.core.ai import cloud_tts
        from quill.core.ai.tts import TTSError

        provider, model, voice, speed, api_key, key_hint = self._resolve_ai_tts_config()
        if not api_key:
            self._set_status(key_hint)
            return

        text = str(self.editor.GetValue()).strip()
        if not text:
            self._set_status("Document is empty.")
            return

        # OpenAI exports MP3; Gemini exports WAV (its native PCM output).
        if provider == "gemini":
            wildcard, default_file = "WAV files (*.wav)|*.wav", "document.wav"
        else:
            wildcard, default_file = "MP3 files (*.mp3)|*.mp3", "document.mp3"

        with wx.FileDialog(
            self.frame,
            message="Save audio",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            defaultFile=default_file,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: wx.FileDialog, not a custom dialog
                return
            output_path = dlg.GetPath()

        import threading
        from pathlib import Path

        cancel_event = threading.Event()
        word_count = len(text.split())
        cost = cloud_tts.estimate_cost_usd(provider, model, len(text))
        self._set_status(
            f"Exporting {word_count} words with {cloud_tts.provider_label(provider)} "
            f"voice {voice}. {cloud_tts.format_cost(cost)}..."
        )

        def _run() -> None:
            import wx as _wx

            try:
                written = cloud_tts.export_audio(
                    provider,
                    text,
                    Path(output_path),
                    api_key,
                    model=model,
                    voice=voice,
                    speed=speed,
                    cancel_event=cancel_event,
                    on_progress=None,
                )
                _wx.CallAfter(self._set_status, f"Audio exported: {written}")
            except TTSError as exc:
                _wx.CallAfter(self._set_status, f"Audio export failed: {exc}")

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    # ------------------------------------------------------------------
    # AI Document Q&A
    # ------------------------------------------------------------------

    def open_ai_document_qa(self) -> None:
        result = self._ai_require_connection()
        if result is None:
            return
        conn, api_key = result
        text = str(self.editor.GetValue())
        title = getattr(self.document, "title", None) or "Current Document"
        from quill.ui.ai_document_qa_dialog import AIDocumentQADialog

        dlg = AIDocumentQADialog(
            self.frame,
            initial_document_text=text,
            document_title=str(title),
            show_modal_dialog=self._show_modal_dialog,
            connection=conn,
            api_key=api_key,
            on_insert_text=self._ai_insert_text,
        )
        dlg.show()

    def _ai_replace_selection(self, text: str) -> None:
        start, end = self.editor.GetSelection()
        if start != end:
            self.editor.Replace(start, end, text)
            self.editor.SetInsertionPoint(start + len(text))
        else:
            self.editor.WriteText(text)

    def _ai_set_document_text(self, text: str) -> None:
        self._replace_document_text(text)
        self.document.set_text(text)

    def _ai_open_new_document(self, text: str) -> None:
        self._power_tools_open_text_in_new_buffer(text, "Opened AI response in new document")

    def _ai_run_command(self, command_id: str) -> None:
        self.commands.run(command_id)

    # ------------------------------------------------------------------
    # AI Agentic Tasks: Rewrite, Summarize, Expand, Table of Contents
    # ------------------------------------------------------------------

    def _paragraph_at_cursor(self) -> str:
        """Return the paragraph surrounding the insertion point."""
        text = str(self.editor.GetValue())
        cursor = self.editor.GetInsertionPoint()
        start = text.rfind("\n\n", 0, cursor)
        start = 0 if start < 0 else start + 2
        end = text.find("\n\n", cursor)
        end = len(text) if end < 0 else end
        return text[start:end].strip()

    def _run_agent_task(
        self,
        agent_id: str,
        *,
        selection_only: bool = False,
        use_selection_as_source: bool = True,
    ) -> None:
        """Run an agent task for the given agent_id and show the result dialog."""
        import threading

        from quill.core.ai.model_manager import load_ai_enabled

        if not load_ai_enabled():
            self._set_status(
                "AI is turned off. Enable 'Use Artificial Intelligence' in Tools > AI Assistant."
            )
            return

        selection_text = self._selected_text() if use_selection_as_source else ""
        document_text = str(self.editor.GetValue()) if not selection_only else ""

        if selection_only and not selection_text:
            selection_text = self._paragraph_at_cursor()
            if selection_text:
                self._set_status("No selection — using current paragraph.")
            else:
                self._set_status("Select text first.")
                return
        if not selection_text and not document_text.strip():
            self._set_status("Document is empty.")
            return

        result = self._ai_require_connection()
        if result is None:
            return
        conn, api_key = result

        from quill.core.assistant_agents import build_agent_plan

        plan = build_agent_plan(
            agent_id,
            selection_text=selection_text,
            document_text=document_text,
        )
        if plan is None:
            self._set_status(f"Unknown agent: {agent_id}")
            return

        from quill.core.ai.agent_session import AgentContext

        stop_event = __import__("threading").Event()
        self._ai_agent_stop_event = stop_event

        ctx = AgentContext(
            plan=plan,
            connection=conn,
            api_key=api_key,
            stop_event=stop_event,
        )

        profile_title = plan.profile.title
        self._set_status(f"{profile_title}: generating...")

        def _run() -> None:
            import wx as _wx

            from quill.core.ai.agent_session import AgentSessionError, run_agent

            try:
                agent_result = run_agent(ctx)
            except AgentSessionError as exc:
                _wx.CallAfter(self._set_status, f"{profile_title} failed: {exc}")
                return
            except Exception as exc:  # noqa: BLE001
                _wx.CallAfter(self._set_status, f"{profile_title} error: {exc}")
                return
            _wx.CallAfter(self._show_agent_result, agent_result, profile_title)

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def _show_agent_result(self, agent_result: object, title: str) -> None:
        if agent_result.cancelled:
            self._set_status(f"{title}: cancelled.")
            return
        if not agent_result.succeeded:
            self._set_status(f"{title}: no output returned.")
            return

        from quill.ui.ai_agent_result_dialog import AIAgentResultDialog

        dlg = AIAgentResultDialog(
            self.frame,
            result=agent_result,
            title=f"{title} Result",
            show_modal_dialog=self._show_modal_dialog,
            on_insert_text=self._ai_insert_text,
            on_replace_selection=self._ai_replace_selection,
        )
        dlg.show()
        self._set_status(f"{title}: done.")

    def open_ai_rewrite_selection(self) -> None:
        self._run_agent_task("rewrite", selection_only=True)

    def open_ai_summarize_selection(self) -> None:
        self._run_agent_task("summarize", use_selection_as_source=True, selection_only=False)

    def open_ai_expand_selection(self) -> None:
        self._run_agent_task("expand", selection_only=True)

    def open_ai_toc(self) -> None:
        self._run_agent_task("toc", selection_only=False, use_selection_as_source=False)

    # ------------------------------------------------------------------
    # AI Thesaurus
    # ------------------------------------------------------------------

    def open_ai_thesaurus(self) -> None:
        result = self._ai_require_connection()
        if result is None:
            return
        conn, api_key = result

        # Use selected word; if multi-word or empty, still pass through
        selection = self._selected_text().strip()
        # Grab context sentence: the line containing the selection
        full_text = str(self.editor.GetValue())
        context_sentence = ""
        if selection and full_text:
            pos = full_text.find(selection)
            if pos >= 0:
                start = full_text.rfind("\n", 0, pos) + 1
                end_nl = full_text.find("\n", pos)
                end = end_nl if end_nl >= 0 else len(full_text)
                context_sentence = full_text[start:end].strip()

        from quill.core.ai.thesaurus import get_synonyms
        from quill.ui.ai_thesaurus_dialog import AIThesaurusDialog

        def _lookup(word: str, ctx: str) -> list:
            return get_synonyms(word, conn, api_key, context_sentence=ctx)

        dlg = AIThesaurusDialog(
            self.frame,
            initial_word=selection,
            context_sentence=context_sentence,
            show_modal_dialog=self._show_modal_dialog,
            on_lookup=_lookup,
            on_replace=self._ai_replace_selection,
        )
        dlg.show()

    def open_ai_model_settings(self) -> None:
        # Combined AI Model & Connection — the model dialog hosts a button to the
        # connection settings, so there's one entry point for all AI setup.
        from quill.ui.ai_model_panel import AIModelDialog

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
            f"Forget the stored AI provider API key? This removes it from the "
            f"{credential_store_name()} and the encrypted fallback file. You "
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
            # Empty state: a quiet status-bar line reads as "nothing happened"
            # to a screen-reader user, so surface a clear, announced dialog.
            self._show_message_box(
                "No saved AI writing sessions yet. Start a conversation in Ask Quill "
                "(sessions are saved automatically as you chat), then reopen AI Session "
                "Branches to browse and compare its branches.",
                "AI Session Branches",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            self._set_status("No saved AI writing sessions yet")
            return
        from quill.ui.session_browser import SessionBrowserDialog

        SessionBrowserDialog(
            self.frame,
            session,
            announce=self._set_status,
        ).show()

    def open_ai_hub(self, initial_page: str | None = None) -> None:
        from quill.ui.ai_hub_dialog import AIHubDialog

        dlg = AIHubDialog(
            self.frame,
            show_modal_dialog=self._show_modal_dialog,
            announce=self._set_status,
            open_advanced_connection=self.open_ai_preferences,
            initial_page=initial_page,
        )
        dlg.show()
        # The Services tab persists the Datalab config straight to disk; fold
        # those fields back into the live settings object so the very next
        # Import / Convert run sees them without a restart.
        from quill.core.settings import load_settings as _reload_settings

        fresh = _reload_settings()
        for field_name in (
            "datalab_enabled",
            "datalab_endpoint",
            "datalab_mode",
            "datalab_output",
            "datalab_paginate",
        ):
            setattr(self.settings, field_name, getattr(fresh, field_name))
        self._request_menu_refresh()

    def open_ocr_service_settings(self) -> None:
        """AI Hub, opened directly on the Services tab (OCR Service Settings)."""
        self.open_ai_hub(initial_page="Services")

    def open_writing_assistant(self, initial_prompt: str = "") -> None:
        # H-SAFE-1: refuse to even open the AI dialog in safe mode. The
        # assistant_enabled flag is forced off in safe mode (line 870)
        # but a user clicking the menu item or a future hot key could
        # still reach this surface; the dialog is the load-bearing
        # gate that the network calls are now also protected by.
        if self._safe_mode:
            self._set_status("Writing assistant is unavailable in safe mode")
            return
        from quill.ui.assistant_tools import WritingAssistantDialog

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
        # Retired into the unified AI Library (Prompts tab). Kept as a redirect so
        # any keybinding/palette entry lands in the new manager instead of a dead
        # end.
        self.open_ai_library()

    def open_agent_center(self) -> None:
        # Retired into the unified AI Library (Agents tab); redirect like
        # open_prompt_studio so old entry points upgrade rather than break.
        self.open_ai_library()

    def run_python_tool(self) -> None:
        from quill.ui.assistant_tools import RunPythonDialog

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
        # One command, one shortcut — the effect follows the document format:
        # rich mode applies real bold via the TOM; Markdown/HTML insert their
        # native tags; plain text gets the one-time transition prompt.
        if self._rich_format_command("apply_bold", "Bold"):
            return
        surface = self._active_markup_surface()
        if surface is None:
            if self._offer_plain_text_formatting_choice("Bold") != "markdown":
                return
            surface = "markdown"
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

    def _effective_language_profile(self) -> object | None:
        """The user-pinned language profile for the current tab, or None.

        Returned only when the user has explicitly set the Document Language;
        otherwise None so path-based detection (the default) stays in charge.
        """
        tab = getattr(self, "_current_tab", None)
        if tab is None or not getattr(tab, "_language_profile_pinned", False):
            return None
        return getattr(tab, "_language_profile", None)

    def format_toggle_line_comment(self) -> None:
        profile = self._effective_language_profile()
        self._apply_selection_operation(
            lambda text, start, end: toggle_line_comment(
                text, start, end, self.document.path, profile
            ),
            "Toggled line comment",
        )

    def format_toggle_block_comment(self) -> None:
        profile = self._effective_language_profile()
        self._apply_selection_operation(
            lambda text, start, end: toggle_block_comment(
                text, start, end, self.document.path, profile
            ),
            "Toggled block comment",
        )

    def _indent_width(self) -> int:
        return max(1, int(getattr(self.settings, "indent_size", 4)))

    def _indent_unit(self) -> str:
        if bool(getattr(self.settings, "indent_with_tabs", False)):
            return "\t"
        return " " * self._indent_width()

    def _current_line_indent_phrase(self) -> str:
        """The caret line's indentation depth spoken after Tab / Shift+Tab."""
        return describe_indent_depth(self.editor.GetValue(), self.editor.GetInsertionPoint())

    def format_indent(
        self, *, status: str = "Indented lines", force_announce: bool = False
    ) -> None:
        self._apply_selection_operation(
            lambda text, start, end: indent_lines(
                text,
                start,
                end,
                indent_unit=self._indent_unit(),
            ),
            status,
            force_announce=force_announce,
        )

    def format_outdent(
        self, *, status: str = "Outdented lines", force_announce: bool = False
    ) -> None:
        self._apply_selection_operation(
            lambda text, start, end: outdent_lines(
                text,
                start,
                end,
                indent_unit=self._indent_unit(),
            ),
            status,
            force_announce=force_announce,
        )

    def format_italic(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Italic is unavailable in this profile")
            return
        if self._rich_format_command("apply_italic", "Italic"):
            return
        surface = self._active_markup_surface()
        if surface is None:
            if self._offer_plain_text_formatting_choice("Italic") != "markdown":
                return
            surface = "markdown"
        selected_text = self.editor.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_insertion("Italic", selected_text)
        else:
            result = build_html_insertion("em", selected_text, {})
        self._apply_insertion_result(result)
        self._set_status(f"Applied italic ({surface})")

    def format_underline(self) -> None:
        # #267: matches bold/italic. Markdown uses inline HTML <u>...</u> since
        # CommonMark has no native underline; HTML surfaces use the <u> tag.
        if not self._feature_enabled("core.format"):
            self._set_status("Underline is unavailable in this profile")
            return
        if self._rich_format_command("apply_underline", "Underline"):
            return
        surface = self._active_markup_surface()
        if surface is None:
            if self._offer_plain_text_formatting_choice("Underline") != "markdown":
                return
            surface = "markdown"
        selected_text = self.editor.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_insertion("Underline", selected_text)
        else:
            result = build_html_insertion("u", selected_text, {})
        self._apply_insertion_result(result)
        self._set_status(f"Applied underline ({surface})")

    def format_heading(self, level: int) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Heading tools are unavailable in this profile")
            return
        if self._rich_format_command("set_heading", f"Heading {level}", level):
            return
        surface = self._active_markup_surface()
        if surface is None:
            if self._offer_plain_text_formatting_choice(f"Heading {level}") != "markdown":
                return
            surface = "markdown"
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

    def toggle_bullet_list(self) -> None:
        """Insert a bullet list, or strip one if the caret is inside it.

        Bound to Ctrl+Alt+7 (EdSharp port).  HTML and plain-text
        documents announce the chord is unavailable and the action is
        skipped.  Strip mode reads the current selection (or the whole
        document when there is no selection) so the writer can collapse
        a list without leaving the chord.
        """
        self._toggle_list("Bullet List", strip_kind="bullet")

    def toggle_numbered_list(self) -> None:
        """Insert a numbered list with auto-filled markers, or strip one.

        Bound to Ctrl+Alt+8 (EdSharp port).  When the three-way auto-fill
        gate (markdown surface OR list_auto_fill_numbers setting OR
        per-document arming flag) holds, the inserted list gets
        ``1. ``, ``2. ``, ``3. `` ... markers.  Otherwise only the first
        item gets a marker (today's behaviour).  Toggling also arms the
        document for 5 minutes so the writer can stay in fill mode
        without re-pressing the chord.
        """
        surface = self._active_markup_surface()
        if surface is not None:
            # Arm the document so subsequent insertions auto-fill for
            # 5 minutes (covers the case where the writer opens the menu,
            # toggles the chord, and continues typing).
            self._numbered_list_armed_until = time.monotonic() + _LIST_AUTO_FILL_ARM_SECONDS
        self._toggle_list("Numbered List", strip_kind="numbered")

    def _toggle_list(self, kind: str, *, strip_kind: str) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status(f"{kind} is unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status(f"{kind} is only available in Markdown or HTML documents")
            return
        try:
            text = self.editor.GetValue()
            caret = self.editor.GetInsertionPoint()
        except RuntimeError:
            return
        try:
            inside = is_caret_inside_list(text, caret, markup_kind=surface)
        except Exception:
            inside = False
        if inside:
            stripped = strip_list_markers(text)
            try:
                self.editor.SetValue(stripped)
                self.editor.SetInsertionPoint(min(caret, len(stripped)))
                self.editor.SetFocus()
            except RuntimeError:
                return
            self._announce(f"{kind} removed")
            return
        # Insert path
        selected_text = self.editor.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_insertion(kind, selected_text)
            if kind == "Numbered List" and should_auto_fill_numbers(
                self.settings, surface, armed_until=self._numbered_list_armed_until
            ):
                rewritten = fill_numbered_markers(result.inserted_text)
                result = type(result)(inserted_text=rewritten, caret_offset=result.caret_offset)
        else:
            result = self._build_html_structure(kind, selected_text)
        self._apply_insertion_result(result)
        if kind == "Numbered List" and surface == "markdown":
            if should_auto_fill_numbers(
                self.settings, surface, armed_until=self._numbered_list_armed_until
            ):
                self._announce("Numbered list applied (with numbers)")
                return
        self._set_status(f"Inserted {kind.lower()} ({surface})")

    def format_insert_task_list(self) -> None:
        self._insert_structure("Task List", "Inserted task list")

    def open_list_manager(self) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("List Manager is unavailable in this profile")
            return
        if self._effective_markup_kind() not in {"markdown", "plain"}:
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
        set_accessible_name(tree, "List items")
        preview = wx.TextCtrl(splitter, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(preview, "List item preview")
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

    def open_table_studio(self) -> None:
        """Experimental: build a table in the accessible grid, then insert it."""
        if not self._experimental_gate_on("table_studio_experimental_enabled"):
            self._set_status(
                "Table Studio is an experimental feature; enable it in Preferences > Experimental."
            )
            return
        from quill.core.table_studio import TableDocumentModel

        model = TableDocumentModel.from_lists(
            headers=["Column 1", "Column 2", "Column 3"],
            rows=[["", "", ""] for _ in range(3)],
            caption="New table",
        )
        self._run_table_studio(model, title="Table Studio")

    def open_csv_studio(self) -> None:
        """Experimental: open a CSV file in Table Studio (same accessible grid)."""
        if not self._experimental_gate_on("table_studio_experimental_enabled"):
            self._set_status(
                "Table Studio is an experimental feature; enable it in Preferences > Experimental."
            )
            return
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Open CSV in Table Studio",
            wildcard="CSV files (*.csv;*.tsv)|*.csv;*.tsv|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Open CSV") != wx.ID_OK:
                return
            path = dialog.GetPath()
        self._open_csv_in_table_studio(path)

    def _open_csv_in_table_studio(self, path: object) -> None:
        """Load a CSV file into Table Studio's accessible grid (shared entry point)."""
        wx = self._wx
        try:
            from quill.core.table_studio.csv_io import load_csv

            model = load_csv(path)
        except (OSError, ValueError) as error:
            self._show_message_box(
                f"Could not open the CSV: {error}", "Table Studio", wx.ICON_ERROR
            )
            return
        self._run_table_studio(model, title=f"Table Studio — {model.caption}")

    def _run_table_studio(self, model: object, *, title: str) -> None:
        wx = self._wx
        from quill.ui.table_studio import TableStudioDialog

        dialog = TableStudioDialog(
            self.frame, model, self._announce, title=title, save_csv_cb=self._save_table_as_csv
        )
        try:
            outcome = self._show_modal_dialog(dialog, title)
            if outcome == wx.ID_OK and dialog.result_markdown:
                self._apply_insertion_result(dialog.result_markdown)
                self._set_status("Table inserted as Markdown")
            elif outcome == wx.ID_APPLY and dialog.result_html:
                self._apply_insertion_result(dialog.result_html)
                self._set_status("Table inserted as HTML")
        finally:
            dialog.Destroy()

    def _save_table_as_csv(self, model: object, default_path: str | None) -> bool:
        """Save a Table Studio model back out to a CSV file. Returns True on save.

        Used by the Table Studio "Save to CSV" button so an opened CSV — or a
        table you just built — round-trips to disk without leaving the grid.
        """
        wx = self._wx
        default_dir = ""
        default_name = "table.csv"
        if default_path:
            from pathlib import Path as _Path

            p = _Path(default_path)
            default_dir, default_name = str(p.parent), p.name
        with wx.FileDialog(
            self.frame,
            "Save as CSV",
            defaultDir=default_dir,
            defaultFile=default_name,
            wildcard="CSV files (*.csv)|*.csv|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save CSV") != wx.ID_OK:
                return False
            path = dialog.GetPath()
        try:
            from quill.core.table_studio.csv_io import save_csv

            save_csv(model, path)
        except OSError as error:
            self._show_message_box(
                f"Could not save the CSV: {error}", "Table Studio", wx.ICON_ERROR
            )
            return False
        self._set_status(f"Saved CSV: {path}")
        return True

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
        # Pin-aware (and content-aware): routes through _current_markup_context so
        # a pinned HTML/Markdown profile makes bold/italic insert the right markup,
        # matching what the menu items enable.
        kind = self._current_markup_context()
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
        force_announce: bool = False,
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
        if force_announce:
            # Speak even while a screen reader is active. A selection edit such
            # as Tab-indent mutates text with no focus or control change, so the
            # screen reader has nothing to read and the normal status path is
            # suppressed by the announcement engine (prism_bridge). force=True is
            # the same escape hatch the QUILL-key chord prefix uses.
            self._announce(status, force=True)
        else:
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
        # Record what this delete removed so Restore Deleted Text can bring it
        # back at a new location (the WordPerfect Editor "Cancel" buffer).
        removed = removed_span(text, updated)
        if removed:
            self._deletion_ring.record(removed)
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
            set_accessible_name(search, prompt)
            root.Add(search, 0, wx.EXPAND | wx.ALL, 8)

            status = wx.StaticText(dialog, label="")
            root.Add(status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            results = wx.ListBox(dialog)
            set_accessible_name(results, dialog_label)
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
        try:
            rendered = self._render_snippet_with_prompts(snippet)
        except ValueError as exc:
            self._set_status(f'Snippet "{snippet.name}" has an invalid placeholder: {exc}')
            return
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
        # One accessible dialog with an explicitly named field per value, instead
        # of a chain of wx.TextEntryDialog prompts. On macOS a TextEntryDialog's
        # prompt does not become the edit control's accessible name, so VoiceOver
        # read the snippet fields as unlabeled (issue #212). Each TextCtrl below
        # gets a visible StaticText label and a matching SetName, and validation
        # happens in-dialog so a blind user hears which field is missing rather
        # than the dialog closing silently.
        wx = self._wx
        name = existing.name if existing is not None else ""
        trigger = existing.trigger if existing is not None else ";"
        description = existing.description if existing is not None else ""
        body = existing.body if existing is not None else "${cursor}"

        title = "Edit Snippet" if existing is not None else "New Snippet"
        with wx.Dialog(self.frame, title=title) as dialog:
            root = wx.BoxSizer(wx.VERTICAL)

            def _add_field(make_ctrl, label_text: str) -> wx.TextCtrl:
                # A11Y-Z-ORDER: always add the StaticText label to the sizer
                # before instantiating the control, so the control's z-order
                # position follows the label (screen readers associate the
                # two by z-order, so label-after-control breaks association).
                root.Add(wx.StaticText(dialog, label=label_text), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
                ctrl = make_ctrl()
                root.Add(ctrl, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
                return ctrl

            def _make_text(value: str, accessible_name: str, multiline: bool) -> wx.TextCtrl:
                style = wx.TE_MULTILINE if multiline else 0
                ctrl = wx.TextCtrl(
                    dialog, value=value, style=style, size=(-1, 90) if multiline else (-1, -1)
                )
                ctrl.SetName(accessible_name)
                return ctrl

            name_ctrl = _add_field(lambda: _make_text(name, "Name", False), "&Name (required):")
            trigger_ctrl = _add_field(
                lambda: _make_text(trigger, "Trigger", False),
                "&Trigger (required, example: ;meeting):",
            )
            description_ctrl = _add_field(
                lambda: _make_text(description, "Description", False),
                "&Description (optional):",
            )
            body_ctrl = _add_field(
                lambda: _make_text(
                    body,
                    "Body",
                    True,
                ),
                "&Body (required) - supports ${input:name}, ${choice:a|b}, "
                "${date}, ${time}, ${cursor}:",
            )

            buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
            if buttons is not None:
                root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            dialog.SetSizerAndFit(root)

            def _on_ok(event: object) -> None:
                # Validate before closing so the missing field is announced and
                # focus moves to it; the dialog stays open to be corrected.
                if not name_ctrl.GetValue().strip():
                    self._announce("Snippet name is required")
                    name_ctrl.SetFocus()
                    return
                if not trigger_ctrl.GetValue().strip():
                    self._announce("Snippet trigger is required")
                    trigger_ctrl.SetFocus()
                    return
                if not body_ctrl.GetValue():
                    self._announce("Snippet body is required")
                    body_ctrl.SetFocus()
                    return
                event.Skip()

            dialog.Bind(wx.EVT_BUTTON, _on_ok, id=wx.ID_OK)
            name_ctrl.SetFocus()
            dialog._quill_keep_initial_focus = True
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None
            name = name_ctrl.GetValue().strip()
            trigger = trigger_ctrl.GetValue().strip()
            description = description_ctrl.GetValue().strip()
            body = body_ctrl.GetValue()

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
        # #959: wx.MultiChoiceDialog's checked list was inaccessible with NVDA —
        # Space toggled an invisible check with no feedback, and Enter on a
        # merely-highlighted row said "No packs selected". A plain extended-
        # selection ListBox announces selection state natively, arrowing to a
        # pack selects it (so Enter installs the highlighted pack with no extra
        # step), and Shift/Ctrl+arrows extend for multiple packs.
        wx = self._wx
        packs = starter_pack_names()
        dialog = wx.Dialog(self.frame, title="Install Starter Snippet Packs")
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(dialog, label="Choose starter snippet packs to install:"),
            0,
            wx.ALL,
            8,
        )
        chooser = wx.ListBox(dialog, choices=packs, style=wx.LB_EXTENDED)
        chooser.SetName(
            "Starter snippet packs. Arrow to a pack and press Enter to install "
            "it; hold Shift or Control to select more than one."
        )
        if packs:
            chooser.SetSelection(0)
        root.Add(chooser, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizerAndFit(root)
        dialog.SetMinSize((420, 320))
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        chooser.SetFocus()
        try:
            if self._show_modal_dialog(dialog, "Install Starter Snippet Packs") != wx.ID_OK:
                self._set_status("Starter snippet pack installation cancelled")
                return
            selections = list(chooser.GetSelections())
        finally:
            dialog.Destroy()
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

        A RadioBox lets the user filter to disabled-only features so they can
        quickly scan what is available to turn on without wading through the
        full list.
        """
        wx = self._wx
        features = self.features
        toggleable = sorted(
            (
                (feature_id, definition)
                for feature_id, definition in FEATURE_DEFINITIONS.items()
                if not definition.locked_on and not definition.locked_off
            ),
            key=lambda item: (item[1].category, item[1].name),
        )

        dialog = wx.Dialog(self.frame, title="Manage Individual Features", size=(700, 680))
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

        # RadioBox filter — wx.RadioBox announces selection and group label to
        # all major screen readers without any extra ARIA plumbing.
        filter_box = wx.RadioBox(
            dialog,
            label="Show",
            choices=["All features", "Disabled features only"],
            style=wx.RA_SPECIFY_ROWS,
            name="features.filter",
        )
        filter_box.SetSelection(0)
        root.Add(filter_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        # Scrolled panel of individual CheckBox controls — NVDA/JAWS announce
        # "checked" / "not checked" natively when focus moves between them,
        # unlike CheckListBox which only announces name without state.
        scroll = wx.ScrolledWindow(dialog, style=wx.VSCROLL)
        scroll.SetScrollRate(0, 20)
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        scroll.SetSizer(scroll_sizer)

        detail = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            name="features.detail",
        )
        detail.SetValue("Arrow to a feature checkbox to read its description here.")

        # Mutable list tracking the currently visible (feature_id, checkbox) pairs.
        current_items: list[tuple[str, object]] = []

        def make_focus_handler(feature_id: str):
            def _on_focus(_event: object) -> None:
                detail.SetValue(features.describe_feature(feature_id))

            return _on_focus

        def make_toggle_handler(feature_id: str):
            def _on_toggle(_event: object) -> None:
                cb = next((c for fid, c in current_items if fid == feature_id), None)
                if cb is None:
                    return
                enabled = cb.GetValue()  # type: ignore[union-attr]
                affected = features.set_feature_enabled(feature_id, enabled)
                announcement = features.describe_feature_toggle(feature_id, enabled, affected)
                for fid, c2 in current_items:
                    c2.SetValue(features.is_enabled(fid))  # type: ignore[union-attr]
                if filter_box.GetSelection() == 1 and enabled:
                    # Feature just enabled: remove from disabled-only list.
                    rebuild_list(focus_first=True)
                else:
                    detail.SetValue(features.describe_feature(feature_id))
                self._build_menu()
                self._apply_accelerators()
                self._set_status(announcement)

            return _on_toggle

        def rebuild_list(focus_first: bool = True) -> None:
            to_destroy = [
                item.GetWindow()
                for item in scroll_sizer.GetChildren()
                if item.GetWindow() is not None
            ]
            scroll_sizer.Clear()
            for win in to_destroy:
                win.Destroy()
            current_items.clear()

            show_disabled_only = filter_box.GetSelection() == 1
            for feature_id, definition in toggleable:
                if show_disabled_only and features.is_enabled(feature_id):
                    continue
                cb = wx.CheckBox(
                    scroll,
                    label=definition.name,
                    name=f"features.cb.{feature_id}",
                )
                cb.SetValue(features.is_enabled(feature_id))
                current_items.append((feature_id, cb))
                cb.Bind(wx.EVT_CHECKBOX, make_toggle_handler(feature_id))
                cb.Bind(wx.EVT_SET_FOCUS, make_focus_handler(feature_id))
                scroll_sizer.Add(cb, 0, wx.ALL, 3)

            scroll_sizer.Layout()
            scroll.FitInside()
            dialog.Layout()

            if not current_items:
                detail.SetValue(
                    "No disabled features found."
                    if show_disabled_only
                    else "No user-toggleable features available."
                )
            elif focus_first:
                wx.CallAfter(current_items[0][1].SetFocus)  # type: ignore[union-attr]
                detail.SetValue("Arrow to a feature checkbox to read its description here.")

        rebuild_list()
        filter_box.Bind(wx.EVT_RADIOBOX, lambda _evt: rebuild_list())

        root.Add(scroll, 1, wx.ALL | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(dialog, label="Feature description:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8
        )
        root.Add(detail, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        root.SetItemMinSize(detail, (-1, 90))
        buttons = dialog.CreateButtonSizer(wx.OK)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        dialog.SetSizerAndFit(root)
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
        set_accessible_name(chooser, "Recorded macros")
        details = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(details, "Macro details")
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
        set_accessible_name(chooser, "Feature profiles")
        entries: list[tuple[str, str, str]] = []
        summary = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(summary, "Profile summary")
        # keyboard_pack_choices, keyboard_pack_choice, and keyboard_preview are
        # created in the layout section below so their StaticText labels are
        # created first in Z-order (required for JAWS label-buddy association).

        def refresh_profile_list(preferred_id: str | None = None) -> None:
            nonlocal entries
            entries = self._combined_profile_entries()
            labels = [
                str(name) if kind == "built_in" else f"{name} (Custom)"
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
            from quill.core.onboarding_profiles import list_intent_profiles

            entry = selected_entry()
            if entry is None:
                summary.SetValue(self.features.profile_summary())
                return
            kind, profile_id, _name = entry
            if kind == "built_in":
                # Show the intent-profile preview text when one maps to this
                # technical profile -- same rich "what you get" description as
                # the wizard, not a dry feature diff.
                intent_matches = [
                    ip for ip in list_intent_profiles() if ip.technical_profile == profile_id
                ]
                if intent_matches:
                    lines: list[str] = []
                    for ip in intent_matches:
                        lines.append(ip.preview_text)
                        if len(intent_matches) > 1:
                            lines.append("\n" + "-" * 40 + "\n")
                    summary.SetValue("\n".join(lines).strip())
                else:
                    summary.SetValue(self.features.change_profile_preview(profile_id))
                summary.SetInsertionPoint(0)
                return
            custom_profile = self._load_custom_profiles().get(profile_id)
            if custom_profile is None:
                summary.SetValue("Custom profile is no longer available.")
                return
            summary.SetValue(self._custom_profile_summary(custom_profile))
            summary.SetInsertionPoint(0)

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
            # Multi-line description so users can write the same "what you get"
            # style description shown for built-in intent profiles.
            with wx.Dialog(
                dialog,
                title="Create Custom Profile - Description",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                size=(520, 360),
            ) as desc_dlg:
                desc_root = wx.BoxSizer(wx.VERTICAL)
                desc_root.Add(
                    wx.StaticText(
                        desc_dlg,
                        label=(
                            "Write a description for your profile.\n"
                            "Describe what it is for and what features it includes.\n"
                            "This text will be shown in the profile chooser."
                        ),
                    ),
                    0,
                    wx.ALL,
                    8,
                )
                desc_ctrl = wx.TextCtrl(
                    desc_dlg,
                    style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
                    size=(-1, 180),
                )
                desc_ctrl.SetName("Profile description")
                desc_root.Add(desc_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
                btn_row = desc_dlg.CreateButtonSizer(wx.OK | wx.CANCEL)
                if btn_row:
                    desc_root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)
                desc_dlg.SetSizer(desc_root)
                apply_modal_ids(desc_dlg, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
                if self._show_modal_dialog(desc_dlg, "Create Custom Profile") != wx.ID_OK:
                    return
                description = desc_ctrl.GetValue().strip()
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
        # Label created before Choice so JAWS finds the right buddy.
        root.Add(wx.StaticText(dialog, label="Keyboard pack:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        keyboard_pack_choices = keyboard_pack_names(include_custom=True)
        keyboard_pack_choice = wx.Choice(dialog, choices=keyboard_pack_choices)
        current_pack = self.settings.keyboard_pack
        if current_pack not in keyboard_pack_choices:
            current_pack = KEYBOARD_PACK_DEFAULT
        set_accessible_name(keyboard_pack_choice, "Keyboard pack")
        keyboard_pack_choice.SetStringSelection(current_pack)
        keyboard_pack_choice.Bind(wx.EVT_CHOICE, lambda _e: refresh_keyboard_preview())
        root.Add(keyboard_pack_choice, 0, wx.ALL | wx.EXPAND, 8)
        keyboard_preview = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 160),
        )
        set_accessible_name(keyboard_preview, "Keyboard pack preview")
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
        from quill.core.onboarding_profiles import DEFAULT_INTENT_ID, get_intent_profile
        from quill.core.settings import save_settings
        from quill.ui.setup_wizard import run_setup_wizard

        feature_manager: FeatureManager = self.features
        changed, aborted = run_setup_wizard(
            self.frame,
            self.settings,
            feature_manager,
            announce_cb=self._announce,
            show_modal_fn=self._show_modal_dialog,
            open_ai_hub=self.open_ai_hub,
        )
        if changed:
            # Apply Quillin profile from wizard intent choice
            intent_id = getattr(self.settings, "setup_wizard_intent", DEFAULT_INTENT_ID)
            wants_ai = bool(getattr(self.settings, "setup_wizard_wants_ai", False))
            wants_braille = bool(getattr(self.settings, "setup_wizard_wants_braille", False))
            wants_auto = bool(getattr(self.settings, "setup_wizard_wants_automation", False))
            self.apply_intent_quillin_profile(
                intent_id,
                wants_ai=wants_ai,
                wants_braille=wants_braille,
                wants_automation=wants_auto,
            )
            save_settings(self.settings)
            feature_manager.save()
            self._apply_accelerators()
            self._set_status_quiet("Personalise QUILL completed")
            self._announce(
                f"Profile set to {get_intent_profile(intent_id).name}. "
                "QUILL is ready. You can personalise further any time from Help."
            )
            # The wizard's Data Location page defers a real move to the next
            # launch the same way Preferences does -- a first-run choice
            # otherwise appears to be silently ignored until the second
            # launch. Offer the same Restart Now/Later Preferences already
            # gives, so the choice takes effect right away if wanted.
            from quill.core.data_location import pending_data_location_target

            target = pending_data_location_target()
            if target is not None:
                self._confirm_restart_for_data_location(target)
        elif first_run and aborted:
            # User cancelled on first run: apply minimal text_editor profile
            # so they start with a clean, quiet editor rather than the raw defaults.
            from quill.core.feature_catalog import FEATURE_DEFINITIONS

            text_editor = get_intent_profile("text_editor")
            feature_manager.switch_profile(text_editor.technical_profile)
            for feature_id, state in text_editor.feature_overrides.items():
                if feature_id not in FEATURE_DEFINITIONS:
                    continue
                try:
                    feature_manager.set_feature_enabled(feature_id, state == "on")
                except Exception:
                    pass
            self.apply_intent_quillin_profile("text_editor")
            feature_manager.save()
            self.settings.setup_wizard_completed = True
            save_settings(self.settings)
            self._apply_accelerators()
            self._announce(
                "Starting with a clean text editor. "
                "Add features any time from Help > Personalise QUILL."
            )

    def run_profile_onboarding(self) -> None:
        # Backward-compatible alias for older command IDs and automation scripts.
        self.run_startup_wizard()

    def _maybe_run_first_run_onboarding(self) -> None:
        from quill.core.paths import app_data_dir, new_install_marker_path
        from quill.core.settings import save_settings as _save_settings
        from quill.core.storage import read_json, write_json_atomic

        # Consume the new-install marker dropped by the installer.  The marker
        # is written to {app} on every install (including upgrades) so that
        # setup_wizard_completed in %APPDATA% — which survives reinstalls — does
        # not silently suppress the first-run wizard after a fresh install.
        #
        # Deleting the marker can fail (#44) when Quill was installed elevated
        # into a directory the running user cannot write to — e.g. Program
        # Files after accepting a UAC prompt at install time. If the delete is
        # silently swallowed without recording that this marker was already
        # consumed, every subsequent launch re-enters this branch and force-
        # resets setup_wizard_completed, reopening the wizard forever.
        #
        # The sentinel under app_data_dir() (always writable per-user) records
        # the marker's resolved path so a marker we have already consumed is
        # recognized even when it could not be deleted (#647). The marker's
        # mtime alone is not a reliable identity — antivirus tools, filesystem
        # mtime drift, or other processes touching the file can change it
        # between launches, which caused the wizard to keep re-opening. The
        # path is stable for a given install, so a marker at a path the
        # sentinel already knows is treated as already consumed regardless of
        # mtime. A marker at a different path is a genuinely new install
        # (portable bundle moved, custom install location, etc.) and resets
        # the wizard as before.
        marker = new_install_marker_path()
        if marker is not None and marker.exists():
            try:
                marker_resolved = str(marker.resolve())
            except OSError:
                # The marker is visible to .exists() but not resolvable —
                # treat the current path as the identity so we still record
                # a sentinel and don't reopen the wizard on every launch.
                marker_resolved = str(marker)
            marker_mtime = marker.stat().st_mtime
            consumed_marker_path = app_data_dir() / "new-install-marker-consumed.json"
            consumed = read_json(consumed_marker_path, {})
            already_consumed = consumed.get("path") == marker_resolved
            if not already_consumed:
                if getattr(self.settings, "setup_wizard_completed", False):
                    self.settings.setup_wizard_completed = False
                    _save_settings(self.settings)
                write_json_atomic(
                    consumed_marker_path,
                    {"path": marker_resolved, "mtime": marker_mtime},
                )
            try:
                marker.unlink()
            except OSError:
                pass

        def _focus_editor() -> None:
            editor = getattr(self, "editor", None)
            if editor is not None and hasattr(editor, "SetFocus"):
                self._wx.CallAfter(editor.SetFocus)

        # Surface the result of a data move/import that an earlier launch
        # queued (e.g. the legacy-install import below, applied on restart).
        self._surface_data_migration_notice()

        # Before the first-run wizard, offer to import data stranded in a
        # previous install's location (portable<->installed switch, or a lost
        # storage-mode marker). If the user accepts, QUILL relaunches to apply
        # the import before Settings are read, so stop onboarding here.
        if not getattr(self.settings, "setup_wizard_completed", True):
            if self._maybe_offer_legacy_data_import():
                return

        # New unified first-run wizard: run when setup_wizard_completed is False
        # (i.e., a fresh install that has not seen the wizard yet). This is the
        # only onboarding surface shown on first run; once it completes,
        # run_setup_wizard() sets setup_wizard_completed=True and we never
        # re-prompt. The legacy "Startup Wizard overview" and per-feature
        # prompts that used to fire on later launches were removed (#700) -- the
        # unified wizard subsumes them, and each feature remains set up from its
        # own menu/button.
        if not getattr(self.settings, "setup_wizard_completed", True):
            try:
                self.run_startup_wizard(first_run=True)
            except Exception:
                self._report_startup_task_failure("first-run setup wizard")
            # #606: if the default "Untitled" tab was deferred at __init__
            # time, create it now that the wizard has closed. The
            # wizard's modal grabbed focus while the notebook was
            # empty; now we hand the user a fresh document.
            if getattr(self, "_first_run_wizard_pending", False):
                self._first_run_wizard_pending = False
                try:
                    self._create_document_tab(Document())
                except Exception:
                    self._report_startup_task_failure("first-run document tab")
                # Re-run the editor-dependent init steps that __init__
                # skipped for this branch. _create_document_tab() already
                # wired the tab + editor; these restore the location ring,
                # accessibility region, and soft-wrap style for the new document
                # (the _bind_events() call in __init__ no-opped soft wrap because
                # the editor did not exist yet).
                try:
                    self._location_ring.record(0)
                    self._region_tracker.enter("Editor")
                    self._apply_soft_wrap(self.settings.soft_wrap)
                except Exception:
                    pass
            _focus_editor()
            # _build_menu() in __init__ deferred its contextual refresh
            # because self.editor was not yet created. Now that the tab
            # has been added and self.editor is wired, flush the pending
            # refresh so contextual menu items (markup mode, document
            # name, etc.) reflect the active document.
            self._request_menu_refresh()
            return

        _focus_editor()

    def enable_braille_mode(self) -> None:
        """Enable Braille Mode from Help > Enable Braille Mode or the command palette.

        If braille is already active this is a no-op with an announcement. Otherwise
        it shows a brief description, enables the feature, rebuilds the menu, and
        optionally triggers the Braille Pack install prompt.
        """
        if self._feature_enabled("core.braille"):
            self._announce(
                "Braille Mode is already active. Use the Braille menu to access braille tools."
            )
            return
        wx = self._wx
        msg = (
            "Braille Mode adds BRF and BRL file support, Grade 1 and Grade 2 "
            "braille translation, a braille status bar cell, and the Braille "
            "menu with page navigation and translation commands.\n\n"
            "The QUILL Braille Pack is a separate optional component that adds "
            "the translation engine. You can install it after enabling the mode.\n\n"
            "Enable Braille Mode now?"
        )
        with wx.MessageDialog(
            self.frame,
            msg,
            "Enable Braille Mode",
            wx.YES_NO | wx.YES_DEFAULT | wx.ICON_INFORMATION,
        ) as dlg:
            if hasattr(dlg, "SetYesNoLabels"):
                dlg.SetYesNoLabels("Enable Braille Mode", "Not Now")
            apply_modal_ids(dlg, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
            result = self._show_modal_dialog(dlg, "Enable Braille Mode")
        if result != wx.ID_YES:
            return
        self.features.set_feature_enabled("core.braille", True)
        self.features.save()
        self._build_menu()
        self._announce("Braille Mode is now active. The Braille menu has been added.")
        self._set_status("Braille Mode enabled")
        self._maybe_prompt_braille_pack_install()

    def _maybe_prompt_braille_pack_install(self) -> None:
        """One-time post-upgrade prompt when the Braille Pack is absent.

        Runs only in a real (non-dev) install, only once per user, only when
        the pack is actually missing and Braille Mode is enabled. Offers to
        re-run the cached installer so the user can add the braillepack
        component without re-downloading. Choosing 'Disable Braille Mode'
        turns the feature off so the prompt never fires again.
        """
        from quill.core.braille_pack import is_braille_pack_installed
        from quill.core.paths import _DEV_BUILD

        if not self._feature_enabled("core.braille"):
            return
        if _DEV_BUILD:
            return
        if is_braille_pack_installed():
            return
        if getattr(self.settings, "upgrade_prompt_braille_pack", False):
            return

        # Mark shown first so a crash during the dialog doesn't re-show.
        self.settings.upgrade_prompt_braille_pack = True
        save_settings(self.settings)

        wx = self._wx
        msg = (
            "QUILL Braille Pack is not installed.\n\n"
            "The Braille Pack adds braille translation, BRF/BRL file export, "
            "and braille display support. It is a quick on-demand download.\n\n"
            "Choose 'Set Up Braille' to open Download Optional Components with the "
            "Braille Pack ready to fetch. Choose 'Not Now' to skip; you can add it "
            "any time from Help > Download Optional Components. Choose 'Disable "
            "Braille Mode' if you do not need braille tools."
        )
        with wx.MessageDialog(
            self.frame,
            msg,
            "QUILL Braille Pack",
            wx.YES_NO | wx.CANCEL | wx.NO_DEFAULT | wx.ICON_INFORMATION,
        ) as dlg:
            if hasattr(dlg, "SetYesNoCancelLabels"):
                dlg.SetYesNoCancelLabels("Set Up Braille", "Not Now", "Disable Braille Mode")
            apply_modal_ids(dlg, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
            result = self._show_modal_dialog(dlg, "QUILL Braille Pack")

        if result == wx.ID_CANCEL:
            self.features.set_feature_enabled("core.braille", False)
            self.features.save()
            self._build_menu()
            self._set_status("Braille Mode disabled. Use Help > Enable Braille Mode to re-enable.")
            return
        if result != wx.ID_YES:
            self._set_status(
                "Braille Pack skipped. Help > Download Optional Components has it any time."
            )
            return

        # Braille is an on-demand download now: route the user into the unified
        # Download Optional Components hub, preselected on the braille pack, with a
        # one-line popup so a screen-reader user knows exactly what to do there.
        self._show_message_box(
            "Opening Download Optional Components. The Braille Pack is selected — "
            "press Download to set it up, then Close when it finishes.",
            "Set Up Braille",
            wx.ICON_INFORMATION | wx.OK,
        )
        self.open_optional_components(preselect="braille")

    def _maybe_prompt_kokoro_package_install(self) -> None:
        """One-time prompt when the Kokoro models are present but the kokoro_onnx
        package is not importable.

        This is the "upgraded from a build that bundled Kokoro" gap: the ~114 MB
        model files are on disk (so the user clearly set Kokoro up) but the pip
        package that loads them was never installed in this runtime. Runs only in
        a real (non-dev) install, never in Safe Mode, only once per user, and only
        when that exact gap exists. Choosing 'Install Now' routes into the existing
        Kokoro engine installer without a second confirmation. Declining is fine --
        export also self-heals this on demand (#kokoro-onnx).
        """
        from quill.core.paths import _DEV_BUILD
        from quill.core.read_aloud import kokoro_onnx_ready
        from quill.core.speech.engine_install import (
            is_kokoro_onnx_available,
            kokoro_onnx_install_supported,
        )

        if _DEV_BUILD or self._safe_mode:
            return
        if getattr(self.settings, "upgrade_prompt_kokoro_onnx", False):
            return
        # Only the models-present / package-missing gap is worth a prompt: no
        # models means the user never set Kokoro up (nothing to complete), and a
        # present package means there is nothing to install.
        if not kokoro_onnx_ready() or is_kokoro_onnx_available():
            return
        # If this build cannot install it (no pip), a prompt would dead-end.
        if not kokoro_onnx_install_supported():
            return

        # Mark shown first so a crash during the dialog doesn't re-show it.
        self.settings.upgrade_prompt_kokoro_onnx = True
        save_settings(self.settings)

        wx = self._wx
        msg = (
            "Your Kokoro voices are installed, but one small component is missing.\n\n"
            "The Kokoro neural voices need the Kokoro ONNX engine (~20 MB) to speak. "
            "Your voice files are already on this computer -- only this component is "
            "left to install.\n\n"
            "Choose 'Install Now' to add it (a quick download). Choose 'Not Now' to "
            "skip; QUILL will install it automatically the next time you export with "
            "a Kokoro voice, or you can re-download Kokoro any time from Help > "
            "Download Optional Components."
        )
        with wx.MessageDialog(
            self.frame,
            msg,
            "Finish Setting Up Kokoro",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION,
        ) as dlg:
            if hasattr(dlg, "SetYesNoLabels"):
                dlg.SetYesNoLabels("Install Now", "Not Now")
            apply_modal_ids(dlg, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
            result = self._show_modal_dialog(dlg, "Finish Setting Up Kokoro")

        if result != wx.ID_YES:
            self._set_status(
                "Kokoro component skipped. QUILL installs it automatically on your "
                "next Kokoro export."
            )
            return
        # Consent already given by 'Install Now' -- do not ask again.
        self.download_kokoro_engine(skip_confirm=True)

    def _find_cached_quill_installer(self):
        """Return the Path of a cached Quill-Setup-*.exe in the updates folder, or None."""
        try:
            updates_dir = app_data_dir() / "updates"
            candidates = sorted(updates_dir.glob("Quill-Setup-*.exe"), reverse=True)
            return candidates[0] if candidates else None
        except Exception:  # noqa: BLE001
            return None

    def _show_trust_consent_onboarding(self, force: bool) -> bool:
        wx = self._wx
        status = getattr(self, "_trust_consent_status", None)
        reconsent = bool(status is not None and status.accepted and status.needs_reconsent)
        if sys.platform == "darwin":
            _key_storage_clause = "API keys are stored in the macOS Keychain."
        else:
            _key_storage_clause = (
                "API keys are stored in Windows Credential Manager when available, "
                "with DPAPI-encrypted fallback storage."
            )
        message = (
            "By selecting I accept, you confirm that:\n\n"
            "1. You are responsible for how AI outputs are used, reviewed, and shared.\n"
            "2. Cloud AI requests are user-initiated and subject to provider terms.\n"
            "3. Quill does not persist chat session transcripts from AI interactions.\n"
            f"4. {_key_storage_clause}\n\n"
            "Do you accept and want to continue?"
        )
        if reconsent:
            deltas = self._format_reconsent_deltas(status.loaded_version)
            message = (
                "Your prior trust, privacy, and responsible-AI disclosure is out of "
                "date.  Please review the changes below before continuing.\n\n"
                f"Changes since your prior consent:\n\n{deltas}\n\n" + message
            )
        title = (
            "Trust and Privacy Consent" if reconsent else "Trust, Privacy, and Responsible AI Use"
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
            accepted = self._show_modal_dialog(dialog, title) == wx.ID_YES
        finally:
            dialog.Destroy()
        if accepted:
            mark_trust_consent_complete()
            self._trust_consent_status = load_trust_consent_status()
            return True
        return False

    @staticmethod
    def _format_reconsent_deltas(loaded_version: int) -> str:
        """Render the per-version change log as numbered bullet points (#305).

        Returns the deltas for every version strictly greater than
        ``loaded_version``, in version order.  Empty string when no deltas
        are recorded (e.g. the change log was wiped in a future cleanup).
        """
        lines: list[str] = []
        for version, delta in sorted(trust_consent_change_log().items()):
            if version <= loaded_version:
                continue
            if not delta:
                continue
            lines.append(f"- (version {version}) {delta}")
        return "\n".join(lines)

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

    def _sync_ai_enabled_menu(self, enabled: bool) -> None:
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None and hasattr(self, "_id_ai_enabled"):
            item = menu_bar.FindItemById(self._id_ai_enabled)
            if item is not None:
                item.Check(enabled)

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
        set_accessible_name(recipe_list, "Recipes")
        left.Add(recipe_list, 1, wx.EXPAND)
        content.Add(left, 0, wx.EXPAND | wx.ALL, 10)

        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(dialog, label="Pattern"), 0, wx.BOTTOM, 4)
        pattern_ctrl = wx.TextCtrl(dialog, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(pattern_ctrl, "Pattern")
        right.Add(pattern_ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)

        right.Add(wx.StaticText(dialog, label="What this pattern means"), 0, wx.BOTTOM, 4)
        explanation_ctrl = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(explanation_ctrl, "What this pattern means")
        explanation_ctrl.SetMinSize((480, 80))
        right.Add(explanation_ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)

        right.Add(wx.StaticText(dialog, label="Sample text"), 0, wx.BOTTOM, 4)
        default_sample = self.editor.GetStringSelection().strip() or self.editor.GetValue()[:1200]
        sample_ctrl = wx.TextCtrl(dialog, value=default_sample, style=wx.TE_MULTILINE)
        set_accessible_name(sample_ctrl, "Sample text")
        sample_ctrl.SetMinSize((480, 170))
        right.Add(sample_ctrl, 1, wx.EXPAND | wx.BOTTOM, 8)

        right.Add(wx.StaticText(dialog, label="Preview results"), 0, wx.BOTTOM, 4)
        results_ctrl = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(results_ctrl, "Preview results")
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
    cold_import_seconds: float = 0.0,
    persona_name: str | None = None,
) -> None:
    from quill.ui.mac_open_file_app import MacOpenFileApp

    # MacOpenFileApp is a plain wx.App subclass on every platform; the
    # MacOpenFile/MacOpenFiles overrides it adds are only ever invoked by
    # wx on macOS (Finder "Open With", drag-onto-Dock-icon, `open -a Quill
    # file.txt` from Terminal all arrive as an Apple Event, not argv --
    # without this override QUILL silently opened a blank document).
    app = MacOpenFileApp(False)
    # #27: without an explicit app name, wx falls back to the running
    # executable/script's name for the macOS application-menu Hide/Quit
    # items ("Hide Mac_OS_app" / "Quit Mac_OS_app") instead of "QUILL".
    app.SetAppName(APP_SHORT_NAME)
    mark_wx_main_thread()
    if diagnostics_mode or should_trace_memory():
        start_memory_tracing()
    _t_construct = time.perf_counter()
    frame = MainFrame(safe_mode=safe_mode)
    _construct_seconds = time.perf_counter() - _t_construct
    if persona_name:
        try:
            frame.apply_persona_by_name(persona_name)
        except Exception:  # noqa: BLE001 - a bad persona must never block startup
            pass
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
    # Wire up the frame so any Apple Event that arrived (or arrives from
    # here on) while the frame was still under construction gets dispatched.
    app.main_frame = frame
    app.flush_pending()
    # Cold-start timing (import + construction + the synchronous part of
    # show()) is recorded on the instance so _write_startup_timing can
    # prepend it ahead of the deferred-task timings it already collects,
    # giving one combined picture of the whole launch in startup_tasks.txt.
    frame._cold_start_times = [
        ("import quill.ui.main_frame", cold_import_seconds),
        ("MainFrame.__init__", _construct_seconds),
    ]
    _t_show = time.perf_counter()
    frame.show()
    frame._cold_start_times.append((
        "frame.show() (synchronous part)",
        time.perf_counter() - _t_show,
    ))
    try:
        app.MainLoop()
    finally:
        timer = getattr(frame, "_stability_heartbeat_timer", None)
        if timer is not None:
            timer.stop()
        watchdog = getattr(frame, "_stability_watchdog", None)
        if watchdog is not None:
            watchdog.stop()
    # #210: the GUI loop has ended and our timers are stopped, so QUILL is done.
    # Force the process to terminate rather than returning up the stack: a
    # lingering non-daemon thread (a TTS driver loop, an audio backend, a
    # leftover worker) must never be able to keep QUILL alive with no window. The
    # hard-exit watchdog in _on_close covers the other half -- a main loop that
    # never returns at all.
    import logging

    logging.shutdown()
    os._exit(0)
