"""Quillins — QUILL's extension framework (wx-free core).

Product naming: a QUILL extension is branded a **Quillin** in everything a user
reads or hears. The neutral technical terms used in code, schemas, and APIs —
``extension``, the ``quill.extension/1`` manifest schema, the ``ext.*`` command
namespace, and :class:`QuillExtensionApi` — stay stable, so wire formats never
change while the experience speaks of Quillins. See ``docs/quillins.md``.

This package is the **framework foundation**:

* :mod:`quill.core.quillins.model` — manifest dataclasses, the capability
  catalogue, the API version, and the error hierarchy.
* :mod:`quill.core.quillins.validation` — a hand-rolled, dependency-free
  validator enforcing the normative ``quill.extension/1`` manifest contract.
* :mod:`quill.core.quillins.snippets` — Layer 1 snippet placeholder expansion.
* :mod:`quill.core.quillins.registry` — collecting contributions from loaded
  manifests and detecting menu/hotkey/command conflicts.
* :mod:`quill.core.quillins.loader` — discovery and enable/disable state for
  installed Quillins, gated behind the SEC-8 ``core.third_party_plugins`` flag.
* :mod:`quill.core.quillins.protocol` — the line-delimited JSON RPC framing
  shared by the host controller and the out-of-process worker.
* :mod:`quill.core.quillins.host` — the parent-process host controller that
  spawns and talks to the sandboxed worker (Layer 2).
* :mod:`quill.core.quillins.host_worker` — the child-process worker entry point
  that loads extension code and exposes :class:`QuillExtensionApi`.

SEC-8 guarantee: discovery and execution of third-party Quillins is refused
unless the ``core.third_party_plugins`` feature flag is enabled, and that flag is
``locked_off`` for QUILL 1.0. A default build therefore never loads or runs
third-party extension code. This package imports no ``wx`` and no platform code.
"""

from __future__ import annotations

from quill.core.quillins.model import (
    API_VERSION,
    CAPABILITIES,
    CONTEXT_WHEN_VALUES,
    MENU_PARENTS,
    SCHEMA_ID,
    ApiVersionError,
    CapabilityError,
    ConflictError,
    ConsentDeniedError,
    ContextMenuContribution,
    Contributions,
    ExtensionCommand,
    ExtensionManifest,
    FileTypeContribution,
    HotkeyContribution,
    ManifestError,
    MenuContribution,
    QuillinError,
    ScheduleContribution,
    SnippetGalleryEntry,
    SnippetParam,
)
from quill.core.quillins.registry import (
    Conflict,
    ContributionRegistry,
    build_registry,
)
from quill.core.quillins.snippets import SnippetContext, expand_snippet
from quill.core.quillins.validation import parse_manifest, validate_manifest

__all__ = [
    "API_VERSION",
    "CAPABILITIES",
    "CONTEXT_WHEN_VALUES",
    "MENU_PARENTS",
    "SCHEMA_ID",
    "ApiVersionError",
    "CapabilityError",
    "Conflict",
    "ConflictError",
    "ConsentDeniedError",
    "ContextMenuContribution",
    "ContributionRegistry",
    "Contributions",
    "ExtensionCommand",
    "ExtensionManifest",
    "FileTypeContribution",
    "HotkeyContribution",
    "ManifestError",
    "MenuContribution",
    "QuillinError",
    "ScheduleContribution",
    "SnippetContext",
    "SnippetGalleryEntry",
    "SnippetParam",
    "build_registry",
    "expand_snippet",
    "parse_manifest",
    "validate_manifest",
]
