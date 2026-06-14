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
})

# Capabilities whose every use must additionally pass QUILL's per-action consent
# gate at runtime (the "no silent network calls / no silent file access" rule).
# The remaining capabilities are disclosed once, at install/enable time.
CONSENT_GATED_CAPABILITIES: frozenset[str] = frozenset({
    CAP_FS_READ,
    CAP_FS_WRITE,
    CAP_NET,
})

# The fixed set of top-level menus an extension may attach a command under.
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
)

# Optional visibility guards for a context-menu contribution.
CONTEXT_WHEN_ALWAYS = "always"
CONTEXT_WHEN_VALUES: tuple[str, ...] = (
    CONTEXT_WHEN_ALWAYS,
    "editor.hasSelection",
    "editor.hasText",
    "editor.empty",
)

# Contributed command ids must be namespaced under ``ext.`` so they can never
# collide with a built-in QUILL command id.
COMMAND_ID_PREFIX = "ext."


class QuillinError(Exception):
    """Base class for every Quillins framework error."""


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
