"""Approvals for agent tool calls (codex.md 5.3) -- wx-free.

Every engine ends in the same place when a tool call needs the person's
say-so: the Copilot permission callback, a Codex approval request, and the
broker's "ask" all reach one :class:`Approver`. The UI implements it once
(the approval dialog, through ``_show_modal_dialog``: Allow once, Allow for
this task, Don't allow; Enter is once, Escape is don't); tests implement it
with a lambda.

Three pieces live here:

- :class:`Approver` -- the protocol: ``ask(tool, summary)`` answers
  :class:`ApprovalChoice` ``ONCE``, ``TASK`` or ``DENY``.
- :class:`ApprovalGate` -- the per-task policy over an approver. Reads inside
  the app's own scope are allowed without a question; writes, recordings,
  sends, deletions and scheduling ask every time unless the person chose
  "for this task". :meth:`ApprovalGate.begin_task` and
  :meth:`ApprovalGate.end_task` clear every task grant, so nothing carries
  over between tasks.
- :class:`UiThreadBridge` / :class:`UiApprovalBridge` -- the threading
  helper. A tool handler runs on a worker thread; the question must be asked
  on the UI thread. The bridge posts the question with the UI's ``post``
  (``wx.CallAfter`` in the app) and waits on a future; :meth:`cancel`
  unblocks every waiter, answering ``DENY``, so Stop never hangs behind an
  open dialog.

:class:`ApprovingEditorHost` routes the editor gateway's own ``confirm`` (the
broker's "ask" for editor tools) through the gate, so an editor tool is asked
about once, by the same dialog, with the same task grants.
"""

from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from quill.core.ai.permissions import PermissionCategory

if TYPE_CHECKING:
    from quill.core.ai.family_tools import FamilyTool

__all__ = [
    "ApprovalChoice",
    "Approver",
    "ApprovalRequest",
    "ApprovalGate",
    "ApprovingEditorHost",
    "UiThreadBridge",
    "UiApprovalBridge",
    "READ_CATEGORIES",
    "is_read_tool",
]

T = TypeVar("T")

#: Categories that only read. A tool in one of these, inside the app's own
#: scope, is allowed without a question (5.3); the broker can still deny it.
READ_CATEGORIES: frozenset[PermissionCategory] = frozenset({
    PermissionCategory.READ_SELECTION,
    PermissionCategory.READ_DOCUMENT,
    PermissionCategory.READ_WORKSPACE,
})


class ApprovalChoice(StrEnum):
    """The three answers the approval dialog offers."""

    ONCE = "once"
    TASK = "task"
    DENY = "deny"


@runtime_checkable
class Approver(Protocol):
    """Asks the person whether one tool call may run.

    ``summary`` is one plain sentence on what will happen ("Replace the whole
    document with the reviewed text."). Called on a worker thread; a UI
    implementation marshals through :class:`UiApprovalBridge`.
    """

    def ask(self, tool: FamilyTool, summary: str) -> ApprovalChoice: ...


def is_read_tool(tool: FamilyTool) -> bool:
    """True when the tool only reads."""
    return tool.category in READ_CATEGORIES


class ApprovalGate:
    """The per-task approval policy over an :class:`Approver`. Thread-safe.

    The gate also carries the *current* tool for the calling thread (set by
    the registry around a handler) so that a confirm raised deep inside the
    editor gateway is attributed to the right tool, and one-shot *passes*: a
    tool approved by an engine's own permission callback (Copilot asks before
    it calls) is not asked about a second time inside the handler.
    """

    def __init__(self, approver: Approver | None = None, *, app_scope: str = "") -> None:
        self._approver = approver
        self._app_scope = app_scope
        self._lock = threading.Lock()
        self._task_grants: set[str] = set()
        # One-shot passes keyed by (tool name, engine call id).
        self._passes: Counter[tuple[str, str]] = Counter()
        self._local = threading.local()

    @property
    def app_scope(self) -> str:
        return self._app_scope

    def begin_task(self, approver: Approver | None = None) -> None:
        """Start a task: optionally swap the approver, and clear every grant."""
        with self._lock:
            if approver is not None:
                self._approver = approver
            self._task_grants.clear()
            self._passes.clear()

    def end_task(self) -> None:
        """End a task: nothing granted "for this task" survives it."""
        with self._lock:
            self._task_grants.clear()
            self._passes.clear()

    def granted_for_task(self, tool_name: str) -> bool:
        with self._lock:
            return tool_name in self._task_grants

    # -- the current tool (per thread) ---------------------------------------

    def set_current(self, tool: FamilyTool | None, call_id: str = "") -> None:
        self._local.tool = tool
        self._local.call_id = call_id

    def current(self) -> FamilyTool | None:
        return getattr(self._local, "tool", None)

    def current_call_id(self) -> str:
        return str(getattr(self._local, "call_id", ""))

    # -- deciding -----------------------------------------------------------

    def allowed_without_asking(self, tool: FamilyTool, call_id: str | None = None) -> bool:
        """Reads in scope, a task grant, or an unspent pass for this call."""
        if is_read_tool(tool) and self._in_scope(tool):
            return True
        key = (tool.name, self.current_call_id() if call_id is None else call_id)
        with self._lock:
            if tool.name in self._task_grants:
                return True
            if self._passes[key] > 0:
                self._passes[key] -= 1
                return True
        return False

    def check(self, tool: FamilyTool, summary: str, call_id: str | None = None) -> bool:
        """Decide one call: allowed outright, or ask the approver."""
        if self.allowed_without_asking(tool, call_id):
            return True
        return self._ask(tool, summary)

    def authorize_ahead(self, tool: FamilyTool, summary: str, call_id: str = "") -> bool:
        """Approve a call before the engine makes it, leaving one pass.

        Used by an engine whose own permission callback runs before the tool
        handler (Copilot's ``custom-tool`` request). A yes leaves a single pass
        so the handler's own confirm does not ask again.
        """
        if is_read_tool(tool) and self._in_scope(tool):
            return True
        with self._lock:
            if tool.name in self._task_grants:
                return True
        if not self._ask(tool, summary):
            return False
        with self._lock:
            self._passes[(tool.name, call_id)] += 1
        return True

    def _ask(self, tool: FamilyTool, summary: str) -> bool:
        approver = self._approver
        if approver is None:
            return False  # no one to ask means no
        choice = approver.ask(tool, summary)
        if choice is ApprovalChoice.TASK:
            with self._lock:
                self._task_grants.add(tool.name)
            return True
        return choice is ApprovalChoice.ONCE

    def _in_scope(self, tool: FamilyTool) -> bool:
        return not self._app_scope or tool.app == self._app_scope


class ApprovingEditorHost:
    """An ``EditorHost`` whose ``confirm`` goes through the gate.

    Every other attribute is the wrapped host's, so the gateway's optional
    ``getattr`` probes behave exactly as before. A confirm raised while no
    family tool is current (the gateway used outside an agent task) falls
    back to the wrapped host's own confirm.
    """

    def __init__(self, host: Any, gate: ApprovalGate) -> None:
        self._wrapped = host
        self._gate = gate

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)

    def confirm(self, message: str) -> bool:
        tool = self._gate.current()
        if tool is None:
            return bool(self._wrapped.confirm(message))
        return self._gate.check(tool, message)


@dataclass
class ApprovalRequest:
    """One question waiting on the UI: what to show, and how to answer."""

    tool: FamilyTool
    summary: str
    _future: Future[ApprovalChoice] = field(default_factory=Future, repr=False)

    def answer(self, choice: ApprovalChoice) -> None:
        """Answer from the UI thread. A second answer is ignored."""
        if not self._future.done():
            self._future.set_result(choice)

    @property
    def answered(self) -> bool:
        return self._future.done()


class UiThreadBridge:
    """Run a callable on the UI thread from a worker thread, and wait.

    ``post`` schedules a zero-argument callable on the UI thread
    (``wx.CallAfter``). :meth:`call` blocks the worker until the callable has
    run, then returns its value; :meth:`cancel` releases every waiter with its
    default, so a closing window or Stop never strands a worker. The UI side
    uses this for anything the gateway's host must do on the UI thread, such
    as showing a diff review.
    """

    def __init__(self, post: Callable[[Callable[[], None]], None]) -> None:
        self._post = post
        self._lock = threading.Lock()
        self._pending: list[tuple[Future[Any], Any]] = []
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def reset(self) -> None:
        """Accept calls again after a cancel (a new task)."""
        with self._lock:
            self._cancelled = False

    def call(self, fn: Callable[[], T], *, default: T) -> T:
        future: Future[Any] = Future()
        with self._lock:
            if self._cancelled:
                return default
            self._pending.append((future, default))

        def _on_ui() -> None:
            if future.done():
                return
            try:
                future.set_result(fn())
            except BaseException as exc:  # noqa: BLE001 - handed back to the worker
                future.set_exception(exc)

        try:
            self._post(_on_ui)
            result: T = future.result()
            return result
        finally:
            with self._lock:
                self._pending = [p for p in self._pending if p[0] is not future]

    def call_with_answer(self, present: Callable[[Future[T]], None], *, default: T) -> T:
        """Post ``present(future)``; the UI answers later by resolving the future.

        For a modeless question: the UI shows it and calls
        ``future.set_result`` whenever the person answers.
        """
        future: Future[Any] = Future()
        with self._lock:
            if self._cancelled:
                return default
            self._pending.append((future, default))

        def _on_ui() -> None:
            try:
                present(future)
            except BaseException:  # noqa: BLE001 - a broken dialog answers the default
                if not future.done():
                    future.set_result(default)
                raise

        try:
            self._post(_on_ui)
            result: T = future.result()
            return result
        finally:
            with self._lock:
                self._pending = [p for p in self._pending if p[0] is not future]

    def cancel(self) -> None:
        """Release every waiter with its default and refuse new calls."""
        with self._lock:
            self._cancelled = True
            pending = list(self._pending)
        for future, default in pending:
            if not future.done():
                future.set_result(default)


class UiApprovalBridge:
    """An :class:`Approver` that asks on the UI thread and waits.

    ``present`` runs on the UI thread with an :class:`ApprovalRequest`; the
    dialog calls ``request.answer(choice)``. :meth:`cancel` answers every
    open question ``DENY``.
    """

    def __init__(
        self,
        post: Callable[[Callable[[], None]], None],
        present: Callable[[ApprovalRequest], None],
    ) -> None:
        self._bridge = UiThreadBridge(post)
        self._present = present

    @property
    def thread_bridge(self) -> UiThreadBridge:
        return self._bridge

    def ask(self, tool: FamilyTool, summary: str) -> ApprovalChoice:
        def _present(future: Future[ApprovalChoice]) -> None:
            request = ApprovalRequest(tool=tool, summary=summary, _future=future)
            self._present(request)

        return self._bridge.call_with_answer(_present, default=ApprovalChoice.DENY)

    def cancel(self) -> None:
        self._bridge.cancel()

    def reset(self) -> None:
        self._bridge.reset()
