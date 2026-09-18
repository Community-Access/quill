"""Target-neutral contract for editing text outside the QUILL editor.

This module deliberately contains no wx, Windows, COM, or browser imports.
Platform adapters use the contract to describe what a focused target can prove;
transaction code uses the snapshots to decide whether a read or write remains
safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

__all__ = [
    "CapabilityEvidence",
    "CapabilityConfidence",
    "ExternalTextAdapter",
    "ExternalTextReason",
    "OperationResult",
    "OperationStatus",
    "SelectionSnapshot",
    "TargetFamily",
    "TargetSnapshot",
    "TargetState",
    "TextCapability",
    "TextReplacement",
    "merge_capabilities",
]


class TextCapability(StrEnum):
    """An independent operation a target may safely support."""

    INSERT_TEXT = "insert_text"
    EXPAND_TRIGGER = "expand_trigger"
    READ_SELECTION = "read_selection"
    REPLACE_SELECTION = "replace_selection"
    READ_CONTEXT = "read_context"
    PLAIN_TEXT = "plain_text"
    RICH_TEXT = "rich_text"
    NATIVE_UNDO = "native_undo"
    DICTATION_TARGET = "dictation_target"
    BROWSER_DOM = "browser_dom"


class CapabilityEvidence(StrEnum):
    """The strongest evidence used by an adapter to grant a capability."""

    UIA_PATTERN = "uia_pattern"
    UIA_CONTROL_TYPE = "uia_control_type"
    NATIVE_CLASS = "native_class"
    TARGET_ADAPTER = "target_adapter"
    KEYBOARD_CLIPBOARD = "keyboard_clipboard"
    EXTENSION_PROTOCOL = "extension_protocol"


class CapabilityConfidence(StrEnum):
    """How strongly an adapter can support the capabilities it reports."""

    UNKNOWN = "unknown"
    ADVISORY = "advisory"
    CONFIRMED = "confirmed"


class TargetFamily(StrEnum):
    """Known target families with different safety and editing semantics."""

    UNKNOWN = "unknown"
    NATIVE_CONTROL = "native_control"
    BROWSER = "browser"
    WORD = "word"
    OUTLOOK = "outlook"
    TERMINAL = "terminal"


class TargetState(StrEnum):
    """Policy state of a target snapshot."""

    UNKNOWN = "unknown"
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    DENIED = "denied"
    READ_ONLY = "read_only"
    PROTECTED = "protected"
    ELEVATED = "elevated"


class OperationStatus(StrEnum):
    """Outcome of an explicit external text operation."""

    APPLIED = "applied"
    UNSUPPORTED = "unsupported"
    DENIED = "denied"
    PROTECTED = "protected"
    STALE = "stale"
    CANCELLED = "cancelled"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NEEDS_REVIEW = "needs_review"


class ExternalTextReason(StrEnum):
    """Stable, document-safe reason codes for operation outcomes."""

    APPLIED = "applied"
    NO_TARGET = "no_target"
    NO_CAPABILITY = "no_capability"
    UNKNOWN_TARGET = "unknown_target"
    READ_ONLY = "read_only"
    PROTECTED_TARGET = "protected_target"
    DENIED_TARGET = "denied_target"
    ELEVATED_TARGET = "elevated_target"
    STALE_TARGET = "stale_target"
    SELECTION_CHANGED = "selection_changed"
    SOURCE_CHANGED = "source_changed"
    CLIPBOARD_CHANGED = "clipboard_changed"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    PARTIAL_INJECTION = "partial_injection"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TargetSnapshot:
    """A bounded description of the focused control at one point in time."""

    target_id: str
    window_handle: int = 0
    process_id: int = 0
    process_name: str = ""
    window_title: str = ""
    control_id: str = ""
    control_class: str = ""
    control_role: str = ""
    family: TargetFamily = TargetFamily.UNKNOWN
    state: TargetState = TargetState.UNKNOWN
    read_only: bool | None = None
    protected: bool = False
    privilege_match: bool | None = None
    capabilities: frozenset[TextCapability] = frozenset()
    evidence: tuple[CapabilityEvidence, ...] = ()
    confidence: CapabilityConfidence = CapabilityConfidence.UNKNOWN
    patterns: frozenset[str] = frozenset()
    captured_at: float = 0.0
    revision: str = ""
    adapter_name: str = ""

    def supports(self, capability: TextCapability) -> bool:
        """Whether this snapshot explicitly grants *capability*."""
        if self.state == TargetState.READ_ONLY:
            return capability in self.capabilities and capability in {
                TextCapability.READ_SELECTION,
                TextCapability.READ_CONTEXT,
                TextCapability.PLAIN_TEXT,
            }
        if self.state != TargetState.SUPPORTED:
            return False
        return capability in self.capabilities and self.state not in {
            TargetState.UNSUPPORTED,
            TargetState.PROTECTED,
            TargetState.ELEVATED,
        }

    def same_identity(self, other: TargetSnapshot) -> bool:
        """Whether two captures refer to the same focused control."""
        if not self.target_id or not other.target_id:
            return False
        return (
            self.target_id == other.target_id
            and self.window_handle == other.window_handle
            and self.process_id == other.process_id
            and self.control_id == other.control_id
        )


@dataclass(frozen=True, slots=True)
class SelectionSnapshot:
    """Selection data associated with the exact target that supplied it."""

    source_target: TargetSnapshot
    selected_text: str | None = None
    full_text: str | None = None
    selection_start: int | None = None
    selection_end: int | None = None
    caret_position: int | None = None
    surrounding_text: str | None = None
    revision: str = ""

    @property
    def has_selection(self) -> bool:
        """Whether the snapshot contains a non-empty selected range."""
        return (
            self.selection_start is not None
            and self.selection_end is not None
            and self.selection_end > self.selection_start
        )

    def belongs_to(self, target: TargetSnapshot) -> bool:
        """Whether this selection was captured from *target*."""
        return self.source_target.same_identity(target)


@dataclass(frozen=True, slots=True)
class TextReplacement:
    """A requested replacement tied to an expected source range and text."""

    expected_source: str
    replacement_text: str
    selection_start: int | None = None
    selection_end: int | None = None
    resulting_caret: int | None = None
    preserve_formatting: bool = False
    operation_label: str = "Replace selection"


@dataclass(frozen=True, slots=True)
class OperationResult:
    """Document-safe result returned by an external text operation."""

    status: OperationStatus
    reason: ExternalTextReason
    message: str
    target_id: str = ""
    capability: TextCapability | None = None
    fallback: str | None = None
    affected_characters: int = 0


class ExternalTextAdapter(Protocol):
    """Adapter contract for target-family capability probing."""

    name: str
    family: TargetFamily

    def probe(self, target: TargetSnapshot) -> TargetSnapshot | None:
        """Return an enriched snapshot when this adapter owns *target*."""
        ...


def merge_capabilities(
    *sets: frozenset[TextCapability] | set[TextCapability],
) -> frozenset[TextCapability]:
    """Merge independent capability grants without allowing mutation."""
    merged: set[TextCapability] = set()
    for capabilities in sets:
        merged.update(capabilities)
    return frozenset(merged)
