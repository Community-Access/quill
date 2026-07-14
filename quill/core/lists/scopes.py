"""Scoped settings precedence for the Structured List Studio (§3).

Resolves the effective :class:`StructuredListSettings` from layered, optional
*partial* overrides. Precedence, lowest → highest:

    app-default  <  format  <  workspace  <  document  <  this-operation

Each scope above the app-default contributes only the fields it pins, so a
narrower scope overrides exactly those fields and inherits the rest. The
``format`` scope pins the definition-list Markdown profile to suit the document's
markup; ``document`` is stored per document; ``operation`` is the dialog's
in-session choices. ``workspace`` has no source in QUILL today (§3 "workspace
configuration where applicable") but is a first-class layer here so a future
workspace store needs no change to the precedence model.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from typing import Any

from quill.core.lists.settings import DefinitionMarkdownProfile, StructuredListSettings

# Lowest → highest precedence. The app-default is the base the others layer onto.
SCOPE_ORDER: tuple[str, ...] = ("app", "format", "workspace", "document", "operation")

_FIELD_NAMES: frozenset[str] = frozenset(f.name for f in fields(StructuredListSettings))


def format_scope_override(markup_kind: str) -> dict[str, Any]:
    """The format scope's pin: the definition-list Markdown profile for *markup_kind*.

    Embedded ``<dl>`` for HTML, Pandoc ``term / : definition`` for Markdown, so the
    generated definition syntax always fits the document. Returned as a partial
    override (the profile field only).
    """
    profile = (
        DefinitionMarkdownProfile.HTML_FALLBACK
        if markup_kind == "html"
        else DefinitionMarkdownProfile.PANDOC
    )
    return {"definition_markdown_profile": profile.value}


def resolve_settings(
    app_default: StructuredListSettings,
    *,
    format: Mapping[str, Any] | None = None,  # noqa: A002 - "format" mirrors the scope name
    workspace: Mapping[str, Any] | None = None,
    document: Mapping[str, Any] | None = None,
    operation: Mapping[str, Any] | None = None,
) -> StructuredListSettings:
    """Layer the partial scope overrides onto *app_default* in precedence order.

    Unknown keys in any override are ignored, so a hand-edited or out-of-date
    override never breaks resolution.
    """
    data = app_default.to_dict()
    for override in (format, workspace, document, operation):
        if override:
            data.update({key: value for key, value in override.items() if key in _FIELD_NAMES})
    return StructuredListSettings.from_dict(data)


def diff_override(settings: StructuredListSettings, base: StructuredListSettings) -> dict[str, Any]:
    """The partial override holding only the fields where *settings* differs from *base*.

    What a narrower scope (e.g. one document) stores so it pins just its
    intentional changes and inherits everything else. An empty dict means
    *settings* equals *base* — the narrower scope can be cleared.
    """
    settings_data = settings.to_dict()
    base_data = base.to_dict()
    return {
        name: settings_data[name] for name in _FIELD_NAMES if settings_data[name] != base_data[name]
    }
