"""UI- and platform-agnostic registry of "Send to Quill" shell verbs (SHELL-1).

A *shell verb* is one action QUILL can offer on a file from outside the editor:
the file-manager context menu (Windows Explorer / macOS Finder), an in-app
"Send To" menu, or a scripted ``quill --action=<id> <path>`` invocation. Every
surface is driven from this single registry so the menu the user sees, the CLI
action that runs, and the Settings toggles that enable each verb can never drift
apart.

This module imports no ``wx`` and no platform code. The Windows shell
integration (``quill/platform/windows/shell_integration.py``) consumes it to
build registry verbs, the CLI (``quill/__main__.py``) maps ``--action`` onto it,
and the Settings registry exposes one toggle per verb.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

#: File-type groups a verb can apply to. Kept here (core) so the shell
#: integration and the CLI agree on exactly which extensions each verb targets.
IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
    ".heic",
    ".heif",
)
PDF_EXTENSIONS: tuple[str, ...] = (".pdf",)
TEXT_EXTENSIONS: tuple[str, ...] = (".txt",)
MARKUP_EXTENSIONS: tuple[str, ...] = (".md", ".markdown", ".mdx")
HTML_EXTENSIONS: tuple[str, ...] = (".html", ".htm", ".xhtml")

#: Everything QUILL can open as a document, for the "Open in Quill" verb.
OPENABLE_EXTENSIONS: tuple[str, ...] = TEXT_EXTENSIONS + MARKUP_EXTENSIONS + HTML_EXTENSIONS


@dataclass(frozen=True, slots=True)
class ShellVerb:
    """One file action surfaced outside the editor.

    ``verb_id``/``action`` are the stable identifiers (``action`` is what the
    CLI ``--action`` flag and the IPC queue carry). ``settings_key`` is the
    boolean :class:`~quill.core.settings.Settings` attribute that enables this
    verb; ``feature_id`` (when set) gates it behind a feature flag, and
    ``requires_ai``/``requires_consent`` mark verbs that may only run when the
    assistant is enabled and after explicit per-action consent.
    """

    verb_id: str
    label: str
    action: str
    extensions: tuple[str, ...]
    settings_key: str
    description: str = ""
    feature_id: str = ""
    requires_ai: bool = False
    requires_consent: bool = False

    def applies_to(self, extension: str) -> bool:
        """True when this verb targets the given file extension (e.g. ``.png``)."""
        normalized = extension.lower()
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        return normalized in self.extensions


#: The built-in verb set (SHELL-1 v1). Order is the order shown in menus.
_SHELL_VERBS: tuple[ShellVerb, ...] = (
    ShellVerb(
        verb_id="ocr",
        label="OCR with Quill",
        action="ocr",
        extensions=IMAGE_EXTENSIONS + PDF_EXTENSIONS,
        settings_key="shell_verb_ocr",
        description="Recognize text in the image or PDF and open the OCR review.",
        feature_id="core.ocr",
    ),
    ShellVerb(
        verb_id="ocr_structured",
        label="OCR with Quill (structured Markdown)",
        action="ocr-structured",
        extensions=IMAGE_EXTENSIONS + PDF_EXTENSIONS,
        settings_key="shell_verb_ocr_structured",
        description=(
            "Recognize text and reconstruct headings, lists, and tables as "
            "Markdown using the assistant."
        ),
        feature_id="core.ocr",
        requires_ai=True,
    ),
    ShellVerb(
        verb_id="open",
        label="Open in Quill",
        action="open",
        extensions=OPENABLE_EXTENSIONS,
        settings_key="shell_verb_open",
        description="Open the file in a new Quill editor tab.",
    ),
    ShellVerb(
        verb_id="read",
        label="Read aloud in Quill",
        action="read",
        extensions=OPENABLE_EXTENSIONS + IMAGE_EXTENSIONS + PDF_EXTENSIONS,
        settings_key="shell_verb_read",
        description="Open the file in Quill and start reading it aloud.",
        feature_id="read_aloud",
    ),
)


def default_shell_verbs() -> tuple[ShellVerb, ...]:
    """Return the built-in verb registry."""
    return _SHELL_VERBS


def verb_for_action(action: str) -> ShellVerb | None:
    """Return the verb whose ``action`` matches ``action`` (case-insensitive)."""
    needle = action.strip().lower()
    for verb in _SHELL_VERBS:
        if verb.action == needle:
            return verb
    return None


def verb_actions() -> tuple[str, ...]:
    """Every known ``action`` id, for CLI validation."""
    return tuple(verb.action for verb in _SHELL_VERBS)


def enabled_verbs(
    *,
    settings_values: object,
    master_enabled: bool,
    assistant_enabled: bool,
    verbs: Iterable[ShellVerb] | None = None,
) -> list[ShellVerb]:
    """Filter the registry to the verbs that should be shown right now.

    A verb is included only when the master integration toggle is on, its own
    ``settings_key`` is truthy on ``settings_values``, and — for AI verbs — the
    assistant is enabled. ``settings_values`` is any object exposing the verb
    settings as attributes (typically a :class:`~quill.core.settings.Settings`).
    """
    if not master_enabled:
        return []
    pool = tuple(verbs) if verbs is not None else _SHELL_VERBS
    result: list[ShellVerb] = []
    for verb in pool:
        if verb.requires_ai and not assistant_enabled:
            continue
        if not bool(getattr(settings_values, verb.settings_key, False)):
            continue
        result.append(verb)
    return result


def verbs_for_extension(
    extension: str, verbs: Iterable[ShellVerb] | None = None
) -> list[ShellVerb]:
    """Return the verbs that apply to a given file extension (e.g. ``.pdf``)."""
    pool = tuple(verbs) if verbs is not None else _SHELL_VERBS
    return [verb for verb in pool if verb.applies_to(extension)]


__all__ = [
    "HTML_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "MARKUP_EXTENSIONS",
    "OPENABLE_EXTENSIONS",
    "PDF_EXTENSIONS",
    "TEXT_EXTENSIONS",
    "ShellVerb",
    "default_shell_verbs",
    "enabled_verbs",
    "verb_actions",
    "verb_for_action",
    "verbs_for_extension",
]
