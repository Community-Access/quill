"""Quillins manifest model, capability catalogue, and error hierarchy.

This module is the wx-free, dependency-free heart of the Quillins framework. It
defines the immutable data model for a ``quill.extension/1`` manifest (the same
contract documented in ``docs/quillins.md`` §13), the catalogue of capabilities
an extension may request, the host API version, and the typed errors an author
or the host may encounter.

Nothing here performs validation, IO, or code execution; see
:mod:`quill.core.quillins.validation` and :mod:`quill.core.quillins.loader`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.error_codes import CodedError

# The manifest schema discriminator and the host API version. The schema string
# is a stable wire identifier; the integer version tracks the Python
# ``QuillExtensionApi`` surface and is bumped only on a breaking change.
SCHEMA_ID = "quill.extension/1"
API_VERSION = 1

# Supported handler runtimes. Python (default) runs the bundled host-worker;
# Node spawns an external Node.js subprocess over the Quillin stdio protocol.
RUNTIME_PYTHON = "python"
RUNTIME_NODE = "node"
RUNTIMES: frozenset[str] = frozenset({RUNTIME_PYTHON, RUNTIME_NODE})

# Capability catalogue (docs/quillins.md §14.1). Default-deny: an extension may
# only do what it declares, and ``fs.*``/``net`` additionally pass the per-action
# consent gate at runtime. A pure snippet-only Quillin declares none of these.
CAP_EDITOR_READ = "editor.read"
CAP_EDITOR_WRITE = "editor.write"
CAP_UI_ANNOUNCE = "ui.announce"
CAP_UI_COMMAND = "ui.command"
CAP_UI_PROMPT = "ui.prompt"
CAP_FS_READ = "fs.read"
CAP_FS_WRITE = "fs.write"
CAP_NET = "net"
CAP_CLIPBOARD_READ = "clipboard.read"
CAP_CLIPBOARD_WRITE = "clipboard.write"
CAP_UI_STATUS = "ui.status"
CAP_UI_CHOICES = "ui.choices"
CAP_STORAGE = "storage"
CAP_SETTINGS_OWN_READ = "settings.own.read"
CAP_SETTINGS_OWN_WRITE = "settings.own.write"
CAP_SETTINGS_CORE_READ = "settings.core.read"
CAP_SETTINGS_CORE_WRITE = "settings.core.write"
CAP_DOCUMENT_DIRECTIVES = "document.directives"
CAP_DOCUMENT_EVENTS = "document.events"
# schedule lets a Quillin run a handler on a fixed background timer (Part 1).
CAP_SCHEDULE = "schedule"
# ui.log routes api.log() calls to the Developer Console (QUILL_DEV_BUILD or
# via Tools > Developer Console). No user-visible side-effect; no consent gate.
CAP_UI_LOG = "ui.log"
# podcast.feed.auth lets a Quillin contribute an Authorization header for a
# matching feed host (Quill Cast), so a premium/authenticated podcast provider
# can supply credentials the host attaches. Purely a host-mediated provider
# contribution; the Quillin returns a header string and makes no network call.
CAP_PODCAST_FEED_AUTH = "podcast.feed.auth"
# radio.directory lets a Quillin contribute a station-directory provider (Quill
# Radio): the host asks its handler for stations matching a search and folds them
# into the Find Stations fan-out. Host-mediated; the handler returns station rows
# (from its own storage/static data) and makes no network call of its own.
CAP_RADIO_DIRECTORY = "radio.directory"
# weather.alerts lets a Quillin contribute an alert source (Quill Weather): the
# host asks its handler for extra active alerts and merges them into the alert
# watch. Host-mediated; the handler returns alert rows and makes no network call.
CAP_WEATHER_ALERTS = "weather.alerts"
# studio.pipeline lets a Quillin contribute an audio-processing step (Audio
# Studio): the host asks its handler for an ffmpeg filter fragment for a named
# processing stage and appends it to the export/enhancement graph. Host-mediated;
# the handler returns a filter string and makes no network call.
CAP_STUDIO_PIPELINE = "studio.pipeline"
# beacon.resolver lets a Quillin contribute a location resolver (Quill Beacon):
# the host asks its handler to resolve a ULD against current content as a
# fallback layer. Host-mediated; the handler returns a position and makes no
# network call of its own.
CAP_BEACON_RESOLVER = "beacon.resolver"

CAPABILITIES: frozenset[str] = frozenset({
    CAP_EDITOR_READ,
    CAP_EDITOR_WRITE,
    CAP_UI_ANNOUNCE,
    CAP_UI_COMMAND,
    CAP_UI_PROMPT,
    CAP_FS_READ,
    CAP_FS_WRITE,
    CAP_NET,
    CAP_CLIPBOARD_READ,
    CAP_CLIPBOARD_WRITE,
    CAP_UI_STATUS,
    CAP_UI_CHOICES,
    CAP_STORAGE,
    CAP_SETTINGS_OWN_READ,
    CAP_SETTINGS_OWN_WRITE,
    CAP_SETTINGS_CORE_READ,
    CAP_SETTINGS_CORE_WRITE,
    CAP_DOCUMENT_DIRECTIVES,
    CAP_DOCUMENT_EVENTS,
    CAP_SCHEDULE,
    CAP_UI_LOG,
    CAP_PODCAST_FEED_AUTH,
    CAP_RADIO_DIRECTORY,
    CAP_WEATHER_ALERTS,
    CAP_STUDIO_PIPELINE,
    CAP_BEACON_RESOLVER,
})

# The set of application ids a manifest may declare in its ``targets`` field.
# ``quill`` is the editor; the others are the standalone companion apps. Kept in
# lock-step with the ``targets`` enum in ``quill/core/schemas/extension.json``
# and with ``quill.core.app_launcher`` (where ``cast`` is the podcasts app).
APP_IDS: frozenset[str] = frozenset({
    "quill",
    "radio",
    "cast",
    "weather",
    "studio",
    "beacon",
})

# The default ``targets`` for a manifest that omits the field: the editor only.
# This keeps every pre-existing (targets-less) Quillin loading in the editor and
# invisible to the companion apps unless it explicitly opts in.
DEFAULT_TARGETS: tuple[str, ...] = ("quill",)

# Capabilities that only make sense inside the full editor (they touch the live
# document / editor buffer). A manifest declaring any of these must not target a
# non-editor app -- there is no document there to act on (enforced in validation).
EDITOR_ONLY_CAPABILITIES: frozenset[str] = frozenset({
    CAP_EDITOR_READ,
    CAP_EDITOR_WRITE,
    CAP_DOCUMENT_DIRECTIVES,
    CAP_DOCUMENT_EVENTS,
})

# Capabilities whose every use must additionally pass QUILL's per-action consent
# gate at runtime (the "no silent network calls / no silent file access" rule).
# The remaining capabilities are disclosed once, at install/enable time.
CONSENT_GATED_CAPABILITIES: frozenset[str] = frozenset({
    CAP_FS_READ,
    CAP_FS_WRITE,
    CAP_NET,
    # Changing a QUILL core setting requires explicit user confirmation per
    # change, making it as privileged as file/network access.
    CAP_SETTINGS_CORE_WRITE,
})

# The fixed set of menu parents an extension may attach a command under.
# These are the conventional top-level menus ("File", "Insert", ...) and a
# handful of conventional submenu names (e.g. "Date and Time") that the host
# builds and exposes to Quillins. The host maps each parent string to the
# correct live wx menu; submenu parents are routed to the dedicated submenu
# declared in ``quill/ui/main_frame_menu.py`` and skip the conventional
# "Append a separator + the item" path used for the top-level menus.
MENU_PARENTS: tuple[str, ...] = (
    "File",
    "Edit",
    "Insert",
    "Format",
    "Tools",
    "Navigate",
    "Search",
    "View",
    "Help",
    # Conventional submenu parents. Keep this list in lock-step with the
    # submenus actually built by ``quill.ui.main_frame_menu._build_menus``
    # and with the schema enum in ``quill/core/schemas/extension.json``.
    "Date and Time",
)

# Optional visibility guards for a context-menu contribution.
CONTEXT_WHEN_ALWAYS = "always"
CONTEXT_WHEN_VALUES: tuple[str, ...] = (
    CONTEXT_WHEN_ALWAYS,
    "editor.hasSelection",
    "editor.hasText",
    "editor.empty",
)

# Document lifecycle events a Quillin may subscribe to (docs/quillins.md).
# These are the only events available in version 1. High-frequency events
# (text.changed, cursor.moved, key.pressed) are deliberately excluded; they
# would let Quillins observe keystrokes and hurt screen-reader predictability.
DOCUMENT_EVENTS: frozenset[str] = frozenset({
    # Document lifecycle
    "document.opened",
    "document.activated",
    "document.before_save",
    "document.after_save",
    "document.before_close",
    "document.after_close",
    "document.created",
    "document.loaded_from_session",
    # Insert automation
    "smart_trigger.entered",
    "abbreviation.expanded",
    # Quillin lifecycle — fired by the host when this Quillin is toggled or QUILL exits.
    "quillin.enabled",
    "quillin.disabled",
    "quill.shutdown",
    # Settings — fired when any setting this Quillin owns changes.
    "settings.changed",
})

# Valid taxonomy labels an extension may self-classify under (``categories`` field).
# Used for filtering in the Quillins Manager. Extensions may declare zero or more.
QUILLIN_CATEGORIES: frozenset[str] = frozenset({
    "writing",
    "accessibility",
    "braille",
    "productivity",
    "developer",
    "formatting",
    "navigation",
    "ai",
    "integration",
    "education",
    "utilities",
})

# Priority levels for ``api.announce()``. The host maps these to the screen
# reader's urgency channel (SSML priority, NVDA speak flags, etc.).
ANNOUNCEMENT_PRIORITIES: frozenset[str] = frozenset({
    "quiet",
    "normal",
    "urgent",
})

# Contributed command ids must be namespaced under ``ext.`` so they can never
# collide with a built-in QUILL command id.
COMMAND_ID_PREFIX = "ext."


class QuillinError(CodedError):
    """Base class for every Quillins framework error."""

    code = "QUILL-QUILLIN-FRAMEWORK-FAILED"


class ManifestError(QuillinError):
    """A manifest failed schema validation.

    Carries the full list of human-readable problems so the Quillins Manager can
    present every issue at once rather than one at a time.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors: list[str] = list(errors)
        summary = "; ".join(self.errors) if self.errors else "invalid manifest"
        super().__init__(summary)


class CapabilityError(QuillinError):
    """An extension invoked an API requiring a capability it was not granted."""

    def __init__(self, capability: str, *, detail: str = "") -> None:
        self.capability = capability
        message = f"Capability not granted: {capability}"
        if detail:
            message = f"{message} ({detail})"
        super().__init__(message)


class ConsentDeniedError(QuillinError):
    """A consent-gated action (filesystem/network) was refused by the user."""


class ConflictError(QuillinError):
    """A contributed hotkey, menu item, or command id conflicts with another."""


class ApiVersionError(QuillinError):
    """The extension targets a host API version this build does not support."""


@dataclass(frozen=True, slots=True)
class ExtensionCommand:
    """A command contributed by an extension.

    Exactly one of ``snippet`` (Layer 1, no code) or ``handler`` (Layer 2, a
    function name registered by the Python entry module) is set.
    """

    id: str
    title: str
    description: str = ""
    snippet: str | None = None
    handler: str | None = None

    @property
    def is_snippet(self) -> bool:
        return self.snippet is not None

    @property
    def is_handler(self) -> bool:
        return self.handler is not None


@dataclass(frozen=True, slots=True)
class MenuContribution:
    """Attach a command under a fixed top-level menu."""

    parent: str
    command: str


@dataclass(frozen=True, slots=True)
class ContextMenuContribution:
    """Attach a command to the editor right-click menu, optionally guarded."""

    command: str
    when: str = CONTEXT_WHEN_ALWAYS


@dataclass(frozen=True, slots=True)
class HotkeyContribution:
    """Bind a command using QUILL's binding grammar (QUILL Key chord allowed)."""

    command: str
    binding: str


@dataclass(frozen=True, slots=True)
class StatusBarContribution:
    """A cell contributed to the QUILL status bar (requires ui.status capability).

    ``id`` must be unique within the Quillin. ``label`` is the static visible text
    when the Quillin has not yet pushed a value. ``handler`` is the function the
    host calls (no args) to refresh the cell on demand; it must return a ``str``.
    ``tooltip`` is an optional description read to screen-reader users on focus.
    ``width`` is a suggested character width hint (1-40); the host may ignore it.
    """

    id: str
    label: str
    handler: str
    tooltip: str = ""
    width: int = 10


@dataclass(frozen=True, slots=True)
class ScheduleContribution:
    """A background timer contribution (requires the schedule capability + main).

    ``id`` must be unique within the Quillin. ``interval_seconds`` is the timer
    period (60-86400). ``handler`` is the function the host invokes on each tick
    with a context of ``{"timer_id", "interval_seconds"}``.
    """

    id: str
    interval_seconds: int
    handler: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class FileTypeContribution:
    """A file-type handler fired when a matching document opens.

    ``extensions`` are lowercase, dot-prefixed suffixes (e.g. ``.csv``). When a
    file with a matching suffix opens, ``handler`` runs with a context of
    ``{"file_path", "extension", "filename"}``. A specialized document.opened, so
    it reuses the document.events capability.
    """

    extensions: tuple[str, ...]
    handler: str
    description: str = ""


#: Host-implemented transcription provider "kinds". The canonical definition lives
#: in ``quill.core.speech.cloud_transcribers`` (the host module present in both QUILL
#: and the standalone Audio Studio, which ships without Quillins); re-exported here
#: so existing Quillin validation imports keep working unchanged.
from quill.core.speech.cloud_transcribers import (  # noqa: E402,F401 - re-export for Quillin validation
    TRANSCRIPTION_PROVIDER_KINDS,
)


@dataclass(frozen=True, slots=True)
class TranscriptionProviderContribution:
    """A cloud transcription provider declared by a Quillin (host-mediated).

    The Quillin declares *which* provider and its branding/limits; QUILL's host
    performs the actual upload through the network-egress audit using the named
    ``kind`` adapter, so the sandbox never handles audio bytes or the API key.
    This contribution is purely declarative -- the Quillin runs no code and makes
    no network calls of its own, so it needs no ``net`` capability (least
    privilege); the host's call is governed by the egress audit.

    ``id`` is namespaced under ``ext.`` and must be unique across enabled
    Quillins. ``kind`` selects the host adapter. ``credential`` is the
    credential-store label holding the API key (empty = the adapter default).
    ``max_file_mb`` overrides the adapter's upload ceiling when > 0.
    """

    id: str
    display_name: str
    kind: str
    description: str = ""
    credential: str = ""
    max_file_mb: float = 0.0


@dataclass(frozen=True, slots=True)
class FeedAuthProviderContribution:
    """A podcast feed authentication provider declared by a Quillin (Quill Cast).

    Declarative + host-mediated: the Quillin declares *which* feed hosts it can
    supply credentials for (``match_hosts``, hostname / ``*.host`` patterns) and
    the ``handler`` function the host calls to obtain an ``Authorization`` header
    for a matching request. The Quillin makes no network call of its own; it
    returns a header string (typically read from its own storage) which the host
    attaches to the feed request. Requires the ``podcast.feed.auth`` capability
    and a ``main`` module.

    ``id`` is namespaced under ``ext.`` and must be unique across enabled
    Quillins. ``match_hosts`` is a non-empty list of hostname patterns.
    """

    id: str
    match_hosts: tuple[str, ...]
    handler: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class DirectoryProviderContribution:
    """A station-directory provider declared by a Quillin (Quill Radio).

    Declarative + host-mediated: the Quillin declares a ``handler`` the host
    calls with the current search query; the handler returns station rows
    (``{"name", "url", "source"}``) read from its own storage or a bundled
    static list, which the host folds into the Find Stations fan-out. The
    Quillin makes no network call of its own. Requires the ``radio.directory``
    capability and a ``main`` module.

    ``id`` is namespaced under ``ext.`` and must be unique across enabled
    Quillins. ``display_name`` is the Source badge shown for the provider's
    stations.

    **The browse trio** (2026-08-27, radio2.md part VIII): a provider that also
    declares ``stations_handler`` (plus optional ``categories_handler`` and
    ``resolve_handler``) becomes a full **browse source** in Quill Radio's
    tree, under the Quillin Sources branch. ``categories_handler`` returns a
    JSON array of category names ([] or undeclared = a flat source);
    ``stations_handler`` receives ``{"category", "query"}`` and returns station
    rows; ``resolve_handler`` receives ``{"key"}`` from a row that carried one
    and returns the playable URL at play time -- the tokenized-locator rule, so
    an address the provider must not cache (or cannot know until playback)
    stays opaque in every list, favourite and export. Any network a handler
    does goes through the host's fetch API, SSRF-hardened and bounded by the
    manifest's ``net_allowed_hosts`` -- the declared-and-bounded egress the
    StreamTuner review asked for and StreamTuner itself has no answer to.
    """

    id: str
    display_name: str
    handler: str
    description: str = ""
    categories_handler: str = ""
    stations_handler: str = ""
    resolve_handler: str = ""


@dataclass(frozen=True, slots=True)
class AlertSourceContribution:
    """An extra weather-alert source declared by a Quillin (Quill Weather).

    Declarative + host-mediated: the Quillin declares a ``handler`` the host
    calls to obtain additional active alerts (``{"id", "event", ...}`` rows),
    merged into the alert watch alongside the built-in NWS feed. The Quillin
    makes no network call of its own -- it returns rows from its own storage or
    a static list. Requires the ``weather.alerts`` capability and a ``main``
    module.

    ``id`` is namespaced under ``ext.`` and must be unique across enabled
    Quillins. ``interval_seconds`` is the provider's suggested poll cadence
    (60-86400); the host may use it to schedule refreshes.
    """

    id: str
    handler: str
    interval_seconds: int = 300
    description: str = ""


@dataclass(frozen=True, slots=True)
class AudioPipelineStepContribution:
    """An audio-processing step declared by a Quillin (Audio Studio).

    Declarative + host-mediated: the Quillin declares a ``handler`` the host
    calls for a named processing ``stage``; the handler returns an ffmpeg filter
    fragment (e.g. ``"loudnorm"``) the host appends to the export/enhancement
    filter graph. The Quillin makes no network call and touches no audio bytes
    itself -- the host runs ffmpeg. Requires the ``studio.pipeline`` capability
    and a ``main`` module.

    ``id`` is namespaced under ``ext.`` and must be unique across enabled
    Quillins. ``stage`` is the pipeline stage the step attaches to. ``display_name``
    labels the step in the Studio processing chain.
    """

    id: str
    stage: str
    handler: str
    display_name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class LocationResolverContribution:
    """A location (ULD) resolver declared by a Quillin (Quill Beacon).

    Declarative + host-mediated: the Quillin declares a ``handler`` the host
    calls as a fallback resolver layer when the built-in locators fail to place
    a Universal Location Descriptor against current content. The handler returns
    a resolution (position + confidence). The Quillin makes no network call of
    its own. Requires the ``beacon.resolver`` capability and a ``main`` module.

    ``id`` is namespaced under ``ext.`` and must be unique across enabled
    Quillins. ``content_types`` optionally scopes the resolver to certain
    resource kinds (e.g. ``["web", "epub"]``); empty means "any".
    """

    id: str
    handler: str
    content_types: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True, slots=True)
class SnippetParam:
    """A single fill-in field prompted before a gallery snippet is inserted."""

    name: str
    label: str
    default: str = ""


@dataclass(frozen=True, slots=True)
class SnippetGalleryEntry:
    """A named, optionally parameterized template shown in the Snippet Gallery.

    ``body`` may contain ``{param_name}`` placeholders; each ``params`` name must
    appear in ``body``. No code runs — this is pure text expansion.
    """

    id: str
    name: str
    body: str
    description: str = ""
    category: str = ""
    params: tuple[SnippetParam, ...] = ()


@dataclass(frozen=True, slots=True)
class Contributions:
    """Everything a manifest contributes to the host's accessible surfaces."""

    commands: tuple[ExtensionCommand, ...] = ()
    menus: tuple[MenuContribution, ...] = ()
    context_menu: tuple[ContextMenuContribution, ...] = ()
    hotkeys: tuple[HotkeyContribution, ...] = ()
    # QSP: optional sound pack shipped inside the extension bundle.
    # sound_pack is a relative directory path; sound_events maps event IDs to WAV filenames.
    sound_pack: str = ""
    sound_events: tuple[tuple[str, str], ...] = ()
    # Insert Automation: abbreviation expansions and = -prefixed smart triggers.
    # Stored as raw dicts; deep structure validated in quillins/validation.py.
    abbreviations: tuple[object, ...] = ()
    smart_triggers: tuple[object, ...] = ()
    # Quillin Preferences: declarative settings pages rendered by the host.
    preferences: tuple[object, ...] = ()
    # Document event subscriptions. Each entry is a dict with event/handler/title/description.
    document_events: tuple[object, ...] = ()
    # Status bar cells. Each entry is a StatusBarContribution.
    status_bar: tuple[StatusBarContribution, ...] = ()
    # Background timers. Each entry is a ScheduleContribution (Part 1).
    schedule: tuple[ScheduleContribution, ...] = ()
    # File-type handlers. Each entry is a FileTypeContribution (Part 2).
    file_types: tuple[FileTypeContribution, ...] = ()
    # Snippet gallery templates. Each entry is a SnippetGalleryEntry (Part 3).
    snippet_gallery: tuple[SnippetGalleryEntry, ...] = ()
    # Host-mediated cloud transcription providers. Each is a
    # TranscriptionProviderContribution; requires the 'net' capability.
    transcription_providers: tuple[TranscriptionProviderContribution, ...] = ()
    # Host-mediated podcast feed auth providers (Quill Cast). Each entry is a
    # FeedAuthProviderContribution; requires the 'podcast.feed.auth' capability.
    feed_auth_providers: tuple[FeedAuthProviderContribution, ...] = ()
    # Host-mediated station-directory providers (Quill Radio). Each entry is a
    # DirectoryProviderContribution; requires the 'radio.directory' capability.
    directory_providers: tuple[DirectoryProviderContribution, ...] = ()
    # Host-mediated weather alert sources (Quill Weather). Each entry is an
    # AlertSourceContribution; requires the 'weather.alerts' capability.
    alert_sources: tuple[AlertSourceContribution, ...] = ()
    # Host-mediated audio-processing steps (Audio Studio). Each entry is an
    # AudioPipelineStepContribution; requires the 'studio.pipeline' capability.
    pipeline_steps: tuple[AudioPipelineStepContribution, ...] = ()
    # Host-mediated location resolvers (Quill Beacon). Each entry is a
    # LocationResolverContribution; requires the 'beacon.resolver' capability.
    location_resolvers: tuple[LocationResolverContribution, ...] = ()


@dataclass(frozen=True, slots=True)
class RequiresDependency:
    """A declared Quillin dependency (``requires`` array in the manifest).

    ``id`` is the fully-qualified Quillin ID (e.g. ``com.quill.journalstamp``).
    ``min_version`` is a semver string; empty string means any version accepted.
    The host checks that the dependency is installed and enabled before loading
    this Quillin.
    """

    id: str
    min_version: str = ""


@dataclass(frozen=True, slots=True)
class ExtensionManifest:
    """A fully validated ``quill.extension/1`` manifest."""

    id: str
    name: str
    version: str
    author: str = ""
    description: str = ""
    license: str = ""
    min_quill_version: str = ""
    capabilities: tuple[str, ...] = ()
    main: str | None = None
    runtime: str = RUNTIME_PYTHON
    contributes: Contributions = field(default_factory=Contributions)
    # Optional taxonomy labels (from QUILLIN_CATEGORIES) for the Quillins Manager filter.
    categories: tuple[str, ...] = ()
    # Inter-Quillin dependency declarations. The host verifies each before loading.
    requires: tuple[RequiresDependency, ...] = ()
    # Restricts net capability to a declared allowlist of hostnames/IP-prefix strings.
    # When empty and net is declared, all outbound hosts are permitted (with consent).
    net_allowed_hosts: tuple[str, ...] = ()
    # The apps this Quillin loads in (from APP_IDS). An empty tuple means the
    # default (``DEFAULT_TARGETS`` -- the editor only). ``target_apps`` resolves
    # the effective set including that default.
    targets: tuple[str, ...] = ()

    @property
    def target_apps(self) -> tuple[str, ...]:
        """The effective ``targets`` set, defaulting to the editor when omitted."""

        return self.targets or DEFAULT_TARGETS

    def targets_app(self, app_id: str) -> bool:
        """True when this Quillin should load in the app identified by ``app_id``."""

        return app_id in self.target_apps

    @property
    def is_layer_two(self) -> bool:
        """True when the manifest ships an entry module (Python or Node, Layer 2)."""

        return self.main is not None

    @property
    def is_node_runtime(self) -> bool:
        """True when the manifest targets the Node.js runtime."""

        return self.runtime == RUNTIME_NODE

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities
