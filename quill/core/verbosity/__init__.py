"""QUILL verbosity system — pure-domain core (wx-free).

This package holds the building blocks of the verbosity rebuild: channels,
profiles, the token system and strict template parser/validator, the data-order
model, the verb catalog and registry, JSON data schemas, the routing engine and
its runtime modes (Quiet/Meeting, mastery, history, explain, safe mode, feedback,
task profiles), profile import/export, custom-data storage, and the QVP pack
loader, template library, and scenario preview renderer. The wxPython UI builds
on these in a later sub-PR.

See ``docs/planning/verbosity-system.md`` for the full design.
"""

from __future__ import annotations

from quill.core.verbosity.channels import (
    ALWAYS_ON_CHANNELS,
    DEFAULT_CHANNELS,
    VISUAL_ALWAYS_ON_NAME,
    Channel,
    route_channels,
)
from quill.core.verbosity.controller import AnnouncementOutcome, VerbosityController
from quill.core.verbosity.data_order import DataOrder
from quill.core.verbosity.engine import (
    RenderedAnnouncement,
    VerbosityEngine,
    speak_legacy_text,
)
from quill.core.verbosity.explain import ExplanationTrace
from quill.core.verbosity.feedback_tuning import FeedbackSignal, FeedbackStore
from quill.core.verbosity.history import AnnouncementHistory, HistoryEntry
from quill.core.verbosity.import_export import (
    ProfileImportError,
    export_profile,
    from_json,
    import_profile,
    to_json,
)
from quill.core.verbosity.library import (
    ApplyResult,
    LibraryTemplate,
    TemplateLibrary,
    TemplateSource,
    apply_template_to_verb,
)
from quill.core.verbosity.mastery import MasteryTracker
from quill.core.verbosity.meeting import MeetingMode
from quill.core.verbosity.parser import (
    ParseResult,
    TemplateError,
    ValidationIssue,
    ValidationReport,
    parse,
    render_template,
    validate,
)
from quill.core.verbosity.preview import (
    BUILTIN_SCENARIOS,
    PreviewOutput,
    Scenario,
    preview_all,
    preview_scenario,
)
from quill.core.verbosity.profiles import (
    BEGINNER,
    BUILTIN_PROFILES,
    DEFAULT_PROFILE,
    EXPERT,
    NORMAL,
    QUIET,
    CustomProfile,
    SoundPolicy,
    VerbosityProfile,
    active_profile,
    profile_for_announcement_verbosity,
)
from quill.core.verbosity.quiet import QuietMode, VerbosityUndoStack
from quill.core.verbosity.qvp import (
    KIND as QVP_KIND,
)
from quill.core.verbosity.qvp import (
    QVPError,
    QVPInstallResult,
    QVPPack,
    QVPTemplate,
    install_pack,
    load_pack,
    parse_pack,
)
from quill.core.verbosity.registry import (
    DuplicateVerbError,
    VerbRegistry,
    default_registry,
)
from quill.core.verbosity.safe_mode import (
    VerbositySafeMode,
    reset_chord,
    reset_verb,
    restore_builtin,
)
from quill.core.verbosity.schema import SCHEMAS, schema_for
from quill.core.verbosity.storage import (
    LoadResult,
    VerbosityCustomData,
    load_custom,
    save_custom,
    verbosity_custom_path,
)
from quill.core.verbosity.task_profiles import TaskProfileSuggester
from quill.core.verbosity.tokens import (
    FILTERS,
    FilterSpec,
    TokenSpec,
    TokenType,
    apply_filter,
    filter_allowed_for_type,
    get_filter,
)
from quill.core.verbosity.verbs import BUILTIN_VERBS, Severity, VerbSpec

__all__ = [
    # channels
    "Channel",
    "DEFAULT_CHANNELS",
    "ALWAYS_ON_CHANNELS",
    "VISUAL_ALWAYS_ON_NAME",
    "route_channels",
    # tokens
    "TokenType",
    "TokenSpec",
    "FilterSpec",
    "FILTERS",
    "get_filter",
    "filter_allowed_for_type",
    "apply_filter",
    # parser
    "ParseResult",
    "TemplateError",
    "ValidationIssue",
    "ValidationReport",
    "parse",
    "validate",
    "render_template",
    # data order
    "DataOrder",
    # profiles
    "VerbosityProfile",
    "CustomProfile",
    "SoundPolicy",
    "BEGINNER",
    "NORMAL",
    "EXPERT",
    "QUIET",
    "BUILTIN_PROFILES",
    "DEFAULT_PROFILE",
    "profile_for_announcement_verbosity",
    "active_profile",
    # verbs / registry
    "Severity",
    "VerbSpec",
    "BUILTIN_VERBS",
    "VerbRegistry",
    "DuplicateVerbError",
    "default_registry",
    # schema
    "SCHEMAS",
    "schema_for",
    # engine
    "VerbosityEngine",
    "RenderedAnnouncement",
    "speak_legacy_text",
    "ExplanationTrace",
    # runtime modes
    "QuietMode",
    "VerbosityUndoStack",
    "MeetingMode",
    # mastery / feedback / history
    "MasteryTracker",
    "FeedbackStore",
    "FeedbackSignal",
    "AnnouncementHistory",
    "HistoryEntry",
    # safe mode
    "VerbositySafeMode",
    "reset_verb",
    "reset_chord",
    "restore_builtin",
    # task profiles
    "TaskProfileSuggester",
    # import / export
    "export_profile",
    "import_profile",
    "to_json",
    "from_json",
    "ProfileImportError",
    # storage
    "VerbosityCustomData",
    "LoadResult",
    "load_custom",
    "save_custom",
    "verbosity_custom_path",
    # QVP packs
    "QVP_KIND",
    "QVPPack",
    "QVPTemplate",
    "QVPInstallResult",
    "QVPError",
    "parse_pack",
    "load_pack",
    "install_pack",
    # template library
    "TemplateLibrary",
    "LibraryTemplate",
    "TemplateSource",
    "ApplyResult",
    "apply_template_to_verb",
    # preview lab
    "Scenario",
    "PreviewOutput",
    "BUILTIN_SCENARIOS",
    "preview_scenario",
    "preview_all",
    # runtime controller (1.5 wiring)
    "VerbosityController",
    "AnnouncementOutcome",
]
