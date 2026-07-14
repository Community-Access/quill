"""Safe Editor Tool Gateway (PRD §9) — the one audited surface every harness uses.

Today `AskQuillChatDialog` receives a loose bundle of editor callbacks
(`get_document`, `get_selection`, `insert_text`, `replace_selection`,
`run_command`, `announce`, `review_changes`, ...). That bundle *is* the editor
tool surface — just unformalized, with no permission checks and no audit trail.

This module promotes it into one typed object:

- :class:`EditorHost` — the Protocol the UI implements (wraps the existing
  callbacks; the gateway never touches wx).
- :class:`SafeEditorToolGateway` — every tool call goes through the
  :class:`~quill.core.ai.permissions.PermissionBroker`, records a redacted
  :class:`~quill.core.ai.activity_log.ActivityEntry`, emits normalized
  :class:`~quill.core.ai.events.AgentEvent`s, and routes every medium+ edit
  through :func:`~quill.core.ai.diff_review.build_diff_review` for accessible,
  one-undo preview.

Because it is wx-free and host-injected, it is fully unit-testable with a fake
host. Native and every SDK-pack harness drive this identical surface; none edits
the buffer directly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from quill.core.ai.activity_log import ActivityEntry, ActivityLog
from quill.core.ai.diff_review import DiffReview, build_diff_review
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.permissions import (
    Decision,
    PermissionBroker,
    PermissionCategory,
    PermissionRequest,
    PermissionResult,
    RiskLevel,
)

__all__ = [
    "EditorHost",
    "AgentIdentity",
    "Emit",
    "ToolError",
    "PermissionDeniedError",
    "SafeEditorToolGateway",
]

# Forwards a normalized event to the Streaming Event Bridge / announcer.
Emit = Callable[[AgentEvent], None]


class ToolError(RuntimeError):
    """A tool could not run (denied, declined, or a host failure)."""


class PermissionDeniedError(ToolError):
    """The broker denied the request, or the user declined a prompt/preview."""


class EditorHost(Protocol):
    """The editor capabilities the gateway needs, implemented by the UI.

    Every method here already exists in QUILL as a callback or command (PRD §9);
    the host is a thin adapter. Read methods return current editor state; apply
    methods mutate the buffer (the host owns the undo checkpoint mechanics, the
    gateway tells it when to take one). Prompt methods are how the host surfaces
    a permission ask (`confirm`) or an accessible diff review (`preview_diff`).
    """

    def get_document(self) -> str: ...
    def get_selection(self) -> str: ...
    def get_outline(self) -> list[str]: ...
    def get_file_type(self) -> str: ...
    # Phase 3 (app/editor-state awareness). Optional: the gateway probes these via
    # getattr and degrades gracefully, so a host may omit them.
    def get_cursor_position(self) -> tuple[int, int]: ...
    def get_current_section(self) -> str: ...
    def get_status_flags(self) -> dict[str, bool]: ...
    def create_undo_checkpoint(self, label: str) -> None: ...
    def apply_replacement(self, text: str) -> None: ...
    def apply_insert(self, text: str) -> None: ...
    def apply_document_text(self, text: str) -> None: ...
    def run_command(self, command_id: str) -> None: ...
    def confirm(self, message: str) -> bool: ...
    def preview_diff(self, review: DiffReview) -> bool: ...
    def announce(self, message: str) -> None: ...


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    """Who is acting, for permission resolution and audit attribution."""

    agent_id: str
    risk: RiskLevel
    harness: str = "native"


class SafeEditorToolGateway:
    """Typed, permission-checked, audited editor tool surface.

    One gateway is created per running agent session (it carries that agent's
    identity for the broker and the log). Construct with the UI host, the active
    :class:`PermissionBroker`, an :class:`ActivityLog`, and an ``emit`` callback
    that forwards :class:`AgentEvent`s to the Streaming Event Bridge.
    """

    def __init__(
        self,
        host: EditorHost,
        broker: PermissionBroker,
        activity: ActivityLog,
        identity: AgentIdentity,
        emit: Emit | None = None,
        web: object | None = None,
    ) -> None:
        self._host = host
        self._broker = broker
        self._activity = activity
        self._who = identity
        self._emit = emit or (lambda _event: None)
        if web is None:
            from quill.core.ai.web_research import NullWebResearchProvider

            web = NullWebResearchProvider()
        self._web = web

    # -- read tools --------------------------------------------------------

    def read_selection(self) -> str:
        """Return the current selection (lowest-risk read)."""
        self._require(PermissionCategory.READ_SELECTION, "read the selection")
        text = self._host.get_selection()
        self._record("tool_call_completed", "Read selection.", {"category": "read_selection"})
        return text

    def read_current_document(self, scope: str = "full") -> str:
        """Return the document text, gated by the read-document permission."""
        self._require(
            PermissionCategory.READ_DOCUMENT,
            "read the whole document",
            detail={"scope": scope},
        )
        text = self._host.get_document()
        self._record(
            "tool_call_completed",
            "Read document.",
            {"category": "read_document", "scope": scope},
        )
        return text

    def read_document_outline(self) -> list[str]:
        """Return heading-level outline entries (cheap, selection-level read)."""
        self._require(PermissionCategory.READ_SELECTION, "read the outline")
        outline = self._host.get_outline()
        self._record("tool_call_completed", "Read outline.", {"category": "read_selection"})
        return outline

    def read_current_section(self) -> str:
        """Return the text of the section the cursor is in (document-level read)."""
        self._require(PermissionCategory.READ_DOCUMENT, "read the current section")
        getter = getattr(self._host, "get_current_section", None)
        text = getter() if callable(getter) else ""
        self._record("tool_call_completed", "Read current section.", {"category": "read_document"})
        return str(text) if text else ""

    def read_app_state(self) -> str:
        """Return cursor position + which features are on/off (cheap read).

        App state is not document content, so it is gated at the lowest read level.
        Host methods are optional (probed via getattr); anything missing is simply
        omitted, so the tool degrades rather than failing.
        """
        self._require(PermissionCategory.READ_SELECTION, "read the app state")
        lines: list[str] = []
        cursor = getattr(self._host, "get_cursor_position", None)
        if callable(cursor):
            try:
                line, col = cursor()
                lines.append(f"Cursor: line {line}, column {col}")
            except Exception:  # noqa: BLE001 - best-effort context
                pass
        file_type = self._host.get_file_type()
        if file_type:
            lines.append(f"File type: {file_type}")
        flags = getattr(self._host, "get_status_flags", None)
        if callable(flags):
            try:
                items = flags()
                if items:
                    lines.append(
                        "Features: "
                        + "; ".join(f"{k}={'on' if v else 'off'}" for k, v in items.items())
                    )
            except Exception:  # noqa: BLE001
                pass
        self._record("tool_call_completed", "Read app state.", {"category": "read_selection"})
        return "\n".join(lines) if lines else "No app state available."

    def audit_accessibility(self) -> str:
        """Audit the document for accessibility issues and return a findings report."""
        self._require(PermissionCategory.READ_DOCUMENT, "check accessibility")
        from quill.core.accessibility_agent import build_plan, build_plan_report

        document = self._host.get_document()
        file_type = (self._host.get_file_type() or "").lower()
        markup = "html" if file_type in {"html", "htm"} else "markdown"
        plan = build_plan("the document", document, markup)
        report = build_plan_report(plan)
        self._record(
            "tool_call_completed",
            f"Accessibility audit: {len(plan.steps)} finding(s).",
            {"category": "read_document"},
        )
        return report

    def web_search(self, query: str) -> str:
        """Search the web (WEB permission + consent + audit); off unless configured."""
        self._require(PermissionCategory.WEB, f"search the web for {query!r}")
        from quill.core.ai.web_research import WebResearchUnavailable, format_results

        if not self._web.available():  # type: ignore[attr-defined]
            return "Web research is not configured."
        try:
            results = self._web.search(query)  # type: ignore[attr-defined]
        except WebResearchUnavailable as exc:
            return str(exc)
        self._record(
            "tool_call_completed",
            f"Web search: {query!r} ({len(results)} result(s)).",
            {"category": "web"},
        )
        return format_results(query, results)

    def web_fetch(self, url: str) -> str:
        """Fetch a web page as text (WEB permission + consent + audit)."""
        self._require(PermissionCategory.WEB, f"fetch {url!r}")
        from quill.core.ai.web_research import WebResearchUnavailable

        if not self._web.available():  # type: ignore[attr-defined]
            return "Web research is not configured."
        try:
            text = self._web.fetch(url)  # type: ignore[attr-defined]
        except WebResearchUnavailable as exc:
            return str(exc)
        self._record("tool_call_completed", f"Web fetch: {url!r}.", {"category": "web"})
        return str(text)

    # -- mutating tools ----------------------------------------------------

    def replace_selection(self, new_text: str, *, label: str = "Replace selection") -> bool:
        """Replace the selection as one undoable edit, previewing if required."""
        result = self._resolve(PermissionCategory.MODIFY_SELECTION)
        if not self._clear_to_proceed(result, f"{label}?"):
            return False
        if result.decision is Decision.PREVIEW_REQUIRED:
            original = self._host.get_selection()
            if not self._preview(original, new_text, label):
                return False
        self._apply(lambda: self._host.apply_replacement(new_text), label, "modify_selection")
        return True

    def insert_at_cursor(self, text: str, *, label: str = "Insert text") -> bool:
        """Insert text at the cursor as one undoable edit."""
        result = self._resolve(PermissionCategory.MODIFY_SELECTION)
        if not self._clear_to_proceed(result, f"{label}?"):
            return False
        if result.decision is Decision.PREVIEW_REQUIRED:
            if not self._preview("", text, label):
                return False
        self._apply(lambda: self._host.apply_insert(text), label, "modify_selection")
        return True

    def apply_text_patch(
        self, original: str, proposed: str, *, label: str = "Apply changes"
    ) -> bool:
        """Apply a whole-document change; preview by default (PRD §12)."""
        result = self._resolve(PermissionCategory.MODIFY_DOCUMENT)
        if not self._clear_to_proceed(result, f"{label}?"):
            return False
        # Document-wide mutations require a preview unless the broker said ALLOW.
        if result.decision is not Decision.ALLOW:
            if not self._preview(original, proposed, label):
                return False
        self._apply(lambda: self._host.apply_document_text(proposed), label, "modify_document")
        return True

    def run_quill_command(self, command_id: str) -> bool:
        """Run a registered command, hard-floored to ``SAFE_TOOL_IDS``."""
        result = self._resolve(PermissionCategory.RUN_COMMAND, command_id=command_id)
        if not self._clear_to_proceed(result, f"Run command {command_id}?"):
            return False
        self._host.run_command(command_id)
        self._record(
            "tool_call_completed",
            f"Ran command {command_id}.",
            {"category": "run_command", "command": command_id},
        )
        self._emit(AgentEvent(AgentEventKind.TOOL_CALL_COMPLETED, f"Ran {command_id}."))
        return True

    def announce_status(self, message: str) -> None:
        """Speak a balanced status line through the host (no permission needed)."""
        self._host.announce(message)

    # -- internals ---------------------------------------------------------

    def _resolve(
        self, category: PermissionCategory, *, command_id: str | None = None
    ) -> PermissionResult:
        request = PermissionRequest(
            category=category,
            agent_id=self._who.agent_id,
            agent_risk=self._who.risk,
            command_id=command_id,
        )
        return self._broker.resolve(request)

    def _require(
        self,
        category: PermissionCategory,
        action: str,
        *,
        detail: dict[str, str] | None = None,
    ) -> None:
        """Resolve a read-style permission; raise if it cannot proceed."""
        result = self._resolve(category)
        if not self._clear_to_proceed(result, f"Allow the agent to {action}?"):
            raise PermissionDeniedError(f"Not permitted to {action}: {result.reason}")

    def _clear_to_proceed(self, result: PermissionResult, prompt: str) -> bool:
        """Apply deny/ask handling shared by every tool. Returns True to continue."""
        if result.blocked:
            self._deny(result, prompt)
            return False
        if result.decision is Decision.ASK:
            self._emit(AgentEvent(AgentEventKind.PERMISSION_REQUIRED, prompt))
            if not self._host.confirm(prompt):
                self._deny(result, prompt, declined=True)
                return False
            self._emit(AgentEvent(AgentEventKind.TOOL_CALL_ALLOWED, prompt))
        return True

    def _preview(self, original: str, proposed: str, label: str) -> bool:
        """Build a diff review, show it, and report whether the user applied it."""
        review = build_diff_review(original, proposed)
        self._emit(
            AgentEvent(
                AgentEventKind.PATCH_PROPOSED,
                f"{label}: {len(review.hunks)} change(s) proposed.",
            )
        )
        if not self._host.preview_diff(review):
            self._record(
                "tool_call_denied",
                f"{label} declined at preview.",
                {"category": "preview"},
            )
            self._emit(AgentEvent(AgentEventKind.TOOL_CALL_DENIED, f"{label} declined."))
            return False
        return True

    def _apply(self, action: Callable[[], None], label: str, category: str) -> None:
        """Take an undo checkpoint, perform the edit, log, announce, and emit."""
        self._host.create_undo_checkpoint(label)
        action()
        self._record("patch_applied", f"{label}.", {"category": category}, undo_label=label)
        self._emit(AgentEvent(AgentEventKind.PATCH_APPLIED, f"{label}."))
        self._host.announce(f"{label}. Press Control Z to undo.")

    def _deny(self, result: PermissionResult, prompt: str, *, declined: bool = False) -> None:
        why = "declined by user" if declined else result.reason
        self._record(
            "tool_call_denied",
            f"Denied: {prompt} ({why}).",
            {"category": result.category.value, "decision": result.decision.value},
        )
        self._emit(AgentEvent(AgentEventKind.TOOL_CALL_DENIED, f"Denied: {prompt}"))

    def _record(
        self,
        kind: str,
        summary: str,
        detail: dict[str, str] | None = None,
        *,
        undo_label: str | None = None,
    ) -> None:
        self._activity.append(
            ActivityEntry.now(
                kind=kind,
                agent_id=self._who.agent_id,
                harness=self._who.harness,
                summary=summary,
                detail=detail,
                undo_label=undo_label,
            )
        )
