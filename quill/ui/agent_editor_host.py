"""Wire the 2.0 Safe Editor Tool Gateway to the real editor (opt-in, default off).

This is the UI adapter that lets the new agentic framework drive the actual
QUILL editor, reusing the *exact* primitives the shipping Ask Quill chat already
uses (`_ai_replace_selection`, `_record_persistent_undo_state`,
`open_ai_diff_review`, `_set_status`), so edit/undo/diff behavior is identical to
today.

It is **opt-in and inert by default**: nothing imports this module unless the
experimental command is enabled (the command is only registered when the
``QUILL_AI_AGENT_GATEWAY`` environment variable is set). The legacy chat path is
untouched and remains the default.

:class:`MainFrameEditorHost` implements the gateway's ``EditorHost`` Protocol over
a MainFrame controller. :func:`run_agent` orchestrates one run with correct
threading: the provider/model call happens on a background thread (the same
pattern as ``_run_agent_task``), and every wx touch — the diff preview, the apply,
the announcements — happens back on the UI thread via ``wx.CallAfter``. The agent's
scope and write permissions decide whether it transforms the selection, transforms
the whole document, or opens its output in a new document.
"""

from __future__ import annotations

from typing import Any

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.context_builder import ContextScope, choose_context_scope
from quill.core.ai.diff_review import DiffReview
from quill.core.ai.event_bridge import AnnouncementLevel, EventBridge
from quill.core.ai.harness import AIContext
from quill.core.ai.harness.native import responder_from_backend
from quill.core.ai.permissions import PermissionBroker, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway

__all__ = [
    "MainFrameEditorHost",
    "run_agent",
    "run_selection_agent",
    "register_agent_commands",
    "append_agent_menu",
    "append_action_ring_menu",
    "register_experimental_agent_command",
    "append_experimental_agent_menu",
    "experimental_gateway_enabled",
    "build_companion_session",
]

# Near-single-shot tool-loop budget for small/free models that are unreliable at
# multi-step tool use (see _companion_loop_budget). Two steps lets a weak model
# make at most one tool call plus a synthesis turn, instead of looping.
_WEAK_MODEL_MAX_STEPS = 2


def experimental_gateway_enabled() -> bool:
    """True when the (now legacy) ``QUILL_AI_AGENT_GATEWAY`` override is set.

    The agent run path is wired into the AI menu by default now; this remains only
    so the env override (and anything reading it) keeps working.
    """
    import os

    return bool(os.environ.get("QUILL_AI_AGENT_GATEWAY"))


def _catalog_agents() -> list[Any]:
    """Bundled + user/promoted agents, sorted by display name (stable order)."""
    from quill.core.ai.agent_catalog import load_full_catalog

    return sorted(load_full_catalog().agents, key=lambda a: a.display_name.lower())


def append_agent_menu(controller: Any, ai_menu: Any) -> None:
    """Append a 'Run Agent' submenu listing every catalog agent.

    Each item runs the agent at its declared scope through the reviewed Safe
    Editor Tool Gateway (permission broker + diff preview + one-step undo). AI
    on/off and Safe Mode are enforced in :func:`run_agent`, so the items stay
    reachable but refuse with a clear status when AI is unavailable. Built here
    (not the size-budgeted menu module) so the menu file only needs one call.
    """
    from quill.core.i18n import _

    wx = controller._wx
    submenu = wx.Menu()
    for agent in _catalog_agents():
        item_id = wx.NewIdRef()
        submenu.Append(item_id, agent.display_name, agent.description or agent.display_name)
        controller.frame.Bind(
            wx.EVT_MENU,
            lambda _e, agent_id=agent.id: run_agent(controller, agent_id),
            id=item_id,
        )
    ai_menu.AppendSeparator()
    ai_menu.AppendSubMenu(submenu, _("Run &Agent"))


def _ring_actions_for(controller: Any) -> list[Any]:
    """The Selection Action Ring entries for the current document's file type.

    Reads the open document's extension (best-effort) so a code file offers code
    actions and prose offers writing actions, exactly like the concierge would
    suggest. Falls back to the general writing ring when the type is unknown.
    """
    from quill.core.ai.agent_catalog import load_catalog
    from quill.core.ai.concierge import ring_actions

    file_type = ""
    try:
        path = getattr(getattr(controller, "document", None), "path", None)
        if path is not None and "." in str(path):
            file_type = str(path).rsplit(".", 1)[-1].lower()
    except Exception:  # noqa: BLE001 - file type is best-effort context
        file_type = ""
    return ring_actions(file_type, load_catalog().agents)


def append_action_ring_menu(controller: Any, ai_menu: Any) -> None:
    """Append a context 'Rewrite & Improve' submenu from the Selection Action Ring.

    Each item runs a real catalog agent with a focused instruction through the
    reviewed Safe Editor Tool Gateway, so the entries match what the concierge
    recommends for the current file type (writing actions for prose, code actions
    for source). AI on/off and Safe Mode are enforced in :func:`run_agent`. Built
    here (not the size-budgeted menu module) so the menu file needs one call.
    """
    from quill.core.i18n import _

    wx = controller._wx
    actions = _ring_actions_for(controller)
    if not actions:
        return
    submenu = wx.Menu()
    for action in actions:
        item_id = wx.NewIdRef()
        submenu.Append(item_id, action.label, action.label)
        controller.frame.Bind(
            wx.EVT_MENU,
            lambda _e, a=action: run_agent(controller, a.agent_id, instruction=a.instruction),
            id=item_id,
        )
    ai_menu.AppendSubMenu(submenu, _("&Rewrite && Improve Selection"))


def register_agent_commands(controller: Any) -> None:
    """Register command-palette entries for the agent run path.

    A quick ``tools.run_agent`` (Writing Companion on the selection) plus one
    ``tools.run_agent.<id>`` per catalog agent, so document-scoped agents are
    reachable from the palette and bindable in the keymap. AI on/off and Safe Mode
    are enforced at run time in :func:`run_agent`.
    """
    controller.commands.register(
        "tools.run_agent",
        "Run Agent on Selection",
        lambda: run_agent(controller, "writing-companion"),
        None,
    )
    for agent in _catalog_agents():
        controller.commands.register(
            "tools.run_agent." + agent.id.replace("-", "_"),
            f"Run Agent: {agent.display_name}",
            lambda agent_id=agent.id: run_agent(controller, agent_id),
            None,
        )


# Back-compat aliases: the menu/command wiring is no longer gated on the env flag.
append_experimental_agent_menu = append_agent_menu
register_experimental_agent_command = register_agent_commands


def _cursor_line_col(editor: Any) -> tuple[int, int]:
    """Return the 1-based (line, column) of the cursor, or (0, 0) on failure."""
    try:
        pos = editor.GetInsertionPoint()
        result = editor.PositionToXY(pos)
        if isinstance(result, tuple) and len(result) == 3:
            _ok, col, row = result
        else:
            col, row = result
        return int(row) + 1, int(col) + 1
    except Exception:  # noqa: BLE001 - cursor position is best-effort context
        return 0, 0


def _current_section_text(controller: Any) -> str:
    """Return the text of the outline section the cursor is currently in."""
    try:
        editor = controller.editor
        document = str(editor.GetValue())
        entries = sorted(controller._outline_entries(), key=lambda e: e.position)
        if not entries:
            return ""
        pos = editor.GetInsertionPoint()
        idx = -1
        for i, entry in enumerate(entries):
            if entry.position <= pos:
                idx = i
            else:
                break
        if idx < 0:
            return document[: entries[0].position].strip()
        start = entries[idx].position
        end = entries[idx + 1].position if idx + 1 < len(entries) else len(document)
        return document[start:end].strip()
    except Exception:  # noqa: BLE001 - section is best-effort context
        return ""


def _status_flags(controller: Any) -> dict[str, bool]:
    """Return which app features are on/off (for the read_app_state tool)."""
    flags: dict[str, bool] = {}
    try:
        from quill.core.ai.model_manager import load_ai_enabled

        flags["ai_enabled"] = bool(load_ai_enabled())
    except Exception:  # noqa: BLE001
        pass
    flags["safe_mode"] = bool(getattr(controller, "_safe_mode", False))
    document = getattr(controller, "document", None)
    if document is not None:
        flags["document_modified"] = bool(getattr(document, "modified", False))
    return flags


class MainFrameEditorHost:
    """``EditorHost`` over a MainFrame controller, reusing existing primitives.

    The ``controller`` is the live ``MainFrame`` (it exposes ``editor`` and the
    ``_ai_*`` helpers). Because the real per-hunk diff dialog
    (``open_ai_diff_review``) both reviews *and* applies the accepted hunks, this
    host applies inside :meth:`preview_diff` and then makes the gateway's
    follow-up checkpoint/apply a no-op for that turn (tracked by
    ``_applied_in_preview``), so a previewed edit is never applied twice and the
    user's per-hunk choices are honored.
    """

    def __init__(self, controller: Any) -> None:
        self._c = controller
        self._applied_in_preview = False
        # Which apply path the preview dialog should use this turn: "selection"
        # replaces the selection, "document" replaces the whole buffer. The runner
        # sets it from the agent's scope before driving the gateway.
        self._apply_mode = "selection"

    def set_apply_mode(self, mode: str) -> None:
        self._apply_mode = mode

    # -- reads -------------------------------------------------------------

    def get_document(self) -> str:
        return str(self._c.editor.GetValue())

    def get_selection(self) -> str:
        return str(self._c.editor.GetStringSelection())

    def get_outline(self) -> list[str]:
        try:
            return [entry.title for entry in self._c._outline_entries()]
        except Exception:  # outline is best-effort context, never fatal
            return []

    def get_file_type(self) -> str:
        path = getattr(getattr(self._c, "document", None), "path", None)
        if path is None:
            return ""
        suffix = str(path).rsplit(".", 1)
        return suffix[-1].lower() if len(suffix) == 2 else ""

    # -- app/editor state (Phase 3) ---------------------------------------

    def get_cursor_position(self) -> tuple[int, int]:
        return _cursor_line_col(self._c.editor)

    def get_current_section(self) -> str:
        return _current_section_text(self._c)

    def get_status_flags(self) -> dict[str, bool]:
        return _status_flags(self._c)

    # -- mutations (reusing the shipping undo/replace path) ----------------

    def create_undo_checkpoint(self, label: str) -> None:
        if self._applied_in_preview:
            return  # the preview dialog already checkpointed before applying
        self._c._record_persistent_undo_state(str(self._c.editor.GetValue()))

    def apply_replacement(self, text: str) -> None:
        if self._applied_in_preview:
            self._applied_in_preview = False  # already applied the accepted hunks
            return
        self._c._ai_replace_selection(text)

    def apply_insert(self, text: str) -> None:
        self._c._ai_insert_text(text)

    def apply_document_text(self, text: str) -> None:
        if self._applied_in_preview:
            self._applied_in_preview = False
            return
        self._c._ai_set_document_text(text)

    def run_command(self, command_id: str) -> None:
        self._c._ai_run_command(command_id)

    # -- prompts -----------------------------------------------------------

    def confirm(self, message: str) -> bool:
        # Route through MainFrame's sanctioned message-box path (GATE-16), not a
        # raw wx.MessageBox, so z-order parent + SR announcement wrappers apply.
        wx = self._c._wx
        result = self._c._show_message_box(message, "QUILL", wx.YES_NO | wx.ICON_QUESTION)
        return result == wx.YES

    def preview_diff(self, review: DiffReview) -> bool:
        """Show the real per-hunk review dialog; apply the accepted hunks.

        Returns whether the user applied anything. Applying happens here (via the
        dialog's ``on_apply``) so per-hunk choices are honored; the gateway's
        subsequent checkpoint/apply then no-op for this turn.
        """
        self._applied_in_preview = False

        def on_apply(accepted_text: str) -> None:
            self._c._record_persistent_undo_state(str(self._c.editor.GetValue()))
            if self._apply_mode == "document":
                self._c._ai_set_document_text(accepted_text)
            else:
                self._c._ai_replace_selection(accepted_text)
            self._applied_in_preview = True

        self._c.open_ai_diff_review(review.original, review.accept_all(), on_apply)
        return self._applied_in_preview

    def announce(self, message: str) -> None:
        self._c._set_status(message)


_SELECTION_SCOPES = (ContextScope.SELECTION, ContextScope.CURRENT_SECTION)
_DOCUMENT_SCOPES = (ContextScope.FULL_DOCUMENT, ContextScope.DOCUMENT_SUMMARY)


def _effective_scope(controller: Any, scope: ContextScope) -> tuple[ContextScope | None, str]:
    """Return (effective_scope, error). ``effective_scope`` is None on error.

    Keeps the agent's declared intent — selection agents require a selection,
    document agents require a non-empty buffer — but a whole-document scope is
    downgraded to a structure-aware summary when the document is too large to send
    verbatim (Phase 2 large-doc handling).
    """
    if scope in _SELECTION_SCOPES:
        if not controller._selected_text().strip():
            return None, "Select text first."
        return scope, ""
    if scope in _DOCUMENT_SCOPES:
        document = str(controller.editor.GetValue())
        if not document.strip():
            return None, "Document is empty."
        # selection forced empty: pick FULL vs DOCUMENT_SUMMARY purely by size.
        return choose_context_scope("", document), ""
    return None, "This agent's scope is not supported yet."


def _file_name(controller: Any) -> str:
    """The current document's file name (empty for an unsaved buffer)."""
    from pathlib import Path

    path = getattr(getattr(controller, "document", None), "path", None)
    return Path(str(path)).name if path is not None else ""


def _context_preview(controller: Any, host: Any, scope: ContextScope) -> Any:
    """Assemble + redact the context for ``scope`` into a :class:`ContextPreview`."""
    from quill.core.ai.context_builder import (
        ContextBuilder,
        ContextRequest,
        StringContextSource,
    )

    source = StringContextSource(
        document=host.get_document(),
        selection=host.get_selection(),
        outline=tuple(host.get_outline()),
        file_name=_file_name(controller),
        file_type=host.get_file_type(),
    )
    return ContextBuilder(source).build(ContextRequest(scope=scope))


def _classify(agent: Any) -> tuple[str, str]:
    """Return (apply_kind, apply_mode) from the agent's WRITE classification.

    ``apply_kind`` is ``document`` (transform whole buffer), ``selection``
    (transform the selection), or ``produce`` (output is new content, not an
    in-place edit -> opened in a new document). ``apply_mode`` tells the host
    which apply path the preview dialog should use. Classification lives in core
    (:func:`quill.core.ai.concierge.write_kind`) so it is shared with the catalog
    recommendation logic.
    """
    from quill.core.ai.concierge import write_kind

    kind = write_kind(agent)
    return (kind, "document") if kind == "document" else (kind, "selection")


def _apply_result(
    controller: Any,
    gateway: SafeEditorToolGateway,
    host: MainFrameEditorHost,
    agent: Any,
    apply_kind: str,
    apply_mode: str,
    proposed: str,
) -> None:
    """Apply the model output per its kind, on the UI thread."""
    host.set_apply_mode(apply_mode)
    if apply_kind == "document":
        original = str(controller.editor.GetValue())
        gateway.apply_text_patch(original, proposed, label=agent.display_name)
    elif apply_kind == "selection":
        gateway.replace_selection(proposed, label=agent.display_name)
    else:  # produce: non-destructive, open the result in a new document
        controller._ai_open_new_document(proposed)
        controller._set_status(f"{agent.display_name}: opened result in a new document.")


def _select_responder(backend: Any, controller: Any) -> tuple[Any, str]:
    """Pick the produce-text transport for the user's chosen AI engine.

    Returns ``(responder, engine_name)``. Honors the engine selected via the
    quick switcher / AI Hub: an available SDK pack supplies its own transport;
    otherwise (Native, ``auto``, or an unavailable/failed pack) it falls back to
    the provider backend. When Native is required but the backend is unavailable,
    returns ``(None, reason)`` so the caller can report it. The returned callable
    has the same ``(AgentSpec, AIContext) -> str`` shape either way, so the run
    path's threading and gateway apply are unchanged.
    """
    from quill.core.ai.quick_switch import preferred_harness_id

    preferred = preferred_harness_id()
    if preferred not in ("auto", "native"):
        from quill.ai_packs import all_packs

        pack = next((p for p in all_packs() if p.id == preferred), None)
        if pack is not None:
            ok, reason = pack.is_available()
            if ok:
                try:
                    return pack.responder(), pack.display_name
                except Exception as exc:  # noqa: BLE001 - fall back, never crash
                    controller._set_status(
                        f"{pack.display_name} could not start ({exc}); using Native."
                    )
            else:
                controller._set_status(
                    f"{pack.display_name} is not set up; using Native. {reason or ''}".strip()
                )
    available, reason = backend.is_available()
    if not available:
        return None, reason or "AI provider is not available."
    return responder_from_backend(backend), "Native (QUILL)"


def run_agent(
    controller: Any, agent_id: str = "writing-companion", *, instruction: str = ""
) -> None:
    """Run a catalog agent through the gateway, at whatever scope it declares.

    Selection-scope agents transform the selection; document-scope agents
    transform the whole buffer (preview-gated); read-only agents open their output
    in a new document. Threading mirrors ``_run_agent_task``: the provider call is
    on a daemon thread, every wx touch (preview, apply, announce) is marshalled
    back to the UI thread via ``wx.CallAfter``.
    """
    from quill.core.ai.agent_catalog import load_full_catalog
    from quill.core.ai.model_manager import load_ai_enabled

    # Guards first, before importing wx, so an early bail stays headless-testable
    # and never spins up the UI/provider stack needlessly.
    if getattr(controller, "_safe_mode", False):
        controller._set_status("Agents are unavailable in safe mode.")
        return

    if not load_ai_enabled():
        controller._set_status("AI is turned off. Enable it in the AI menu.")
        return

    agent = next((a for a in load_full_catalog().agents if a.id == agent_id), None)
    if agent is None:
        controller._set_status(f"Unknown agent: {agent_id}")
        return

    scope, error = _effective_scope(controller, agent.default_scope)
    if scope is None:
        controller._set_status(error)
        return

    import threading

    import wx

    from quill.core.ai.provider_backend import ProviderChatBackend

    backend = ProviderChatBackend()
    responder, engine_name = _select_responder(backend, controller)
    if responder is None:
        controller._set_status(engine_name)  # engine_name carries the reason here
        return

    apply_kind, apply_mode = _classify(agent)
    host = MainFrameEditorHost(controller)

    # Assemble + redact the context, then get the user's OK before anything is sent
    # to a provider (PRD §11). Cancel aborts the run; nothing leaves the machine.
    from quill.ui.context_preview_dialog import confirm_context_share

    preview = _context_preview(controller, host, scope)
    if not confirm_context_share(controller, preview):
        controller._set_status(f"{agent.display_name}: cancelled.")
        return

    gateway = SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.BALANCED, overrides=agent.overrides_map()),
        activity=ActivityLog(),
        identity=AgentIdentity(agent_id=agent.id, risk=agent.risk),
        emit=EventBridge(AnnouncementLevel.BALANCED, controller._set_status).handle,
    )
    ctx = AIContext(prompt=instruction, context_text=preview.text, file_type=host.get_file_type())
    controller._set_status(f"{agent.display_name} ({engine_name}): generating...")

    def _run() -> None:
        try:
            proposed = responder(agent, ctx)
        except Exception as exc:  # noqa: BLE001 - surface provider errors, never crash
            wx.CallAfter(controller._set_status, f"{agent.display_name} error: {exc}")
            return

        def _apply() -> None:
            try:
                _apply_result(controller, gateway, host, agent, apply_kind, apply_mode, proposed)
            except Exception as exc:  # noqa: BLE001
                controller._set_status(f"{agent.display_name} error: {exc}")

        wx.CallAfter(_apply)

    threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread


def run_selection_agent(controller: Any, agent_id: str = "writing-companion") -> None:
    """Back-compat thin wrapper; prefer :func:`run_agent`."""
    run_agent(controller, agent_id)


# ---------------------------------------------------------------------------
# Conversational companion (Companion PRD, Phase 1)
# ---------------------------------------------------------------------------
#
# The single-pass :func:`run_agent` transforms one scope and applies the result.
# The *companion* is a remembered, multi-turn conversation that drives the native
# tool loop (:mod:`quill.core.ai.conversation`) so the user can ask questions
# about the open document, request edits/revisions, and follow up — each turn
# choosing tools dynamically through the same Safe Editor Tool Gateway.


def _run_on_ui(wx: Any, fn: Any) -> Any:
    """Run ``fn`` on the wx UI thread and block until it returns its value.

    The conversation loop runs on a worker thread (model calls block); the editor
    host touches wx (reads, the modal diff preview, announcements), and the UI
    thread must own every widget. When already on the UI thread, call directly.
    Exceptions are re-raised on the calling thread so the loop sees real failures.
    """
    if wx.IsMainThread():
        return fn()

    import threading

    done = threading.Event()
    box: dict[str, Any] = {}

    def runner() -> None:
        try:
            box["result"] = fn()
        except BaseException as exc:  # noqa: BLE001 - propagate to the worker thread
            box["error"] = exc
        finally:
            done.set()

    wx.CallAfter(runner)
    done.wait()
    if "error" in box:
        raise box["error"]
    return box.get("result")


class _CompanionEditorHost:
    """``EditorHost`` for the conversational companion, marshalled to the UI thread.

    Unlike :class:`MainFrameEditorHost` (single-pass transforms that apply *inside*
    the preview to honor per-hunk choices), the companion loop calls insert,
    replace-selection, and whole-document edits dynamically. So this host keeps the
    gateway's intended two-step shape: :meth:`preview_diff` only *reviews* (returns
    whether the user approved) and the gateway's follow-up step performs the
    matching mutation through the correct ``_ai_*`` primitive. That keeps every
    mutation type correct without tracking an apply mode. Reviewing the whole
    proposed edit (accept/reject) rather than per-hunk is the Phase 1 trade-off.
    """

    def __init__(self, controller: Any, wx: Any) -> None:
        self._c = controller
        self._wx = wx

    # -- reads -------------------------------------------------------------

    def get_document(self) -> str:
        return _run_on_ui(self._wx, lambda: str(self._c.editor.GetValue()))

    def get_selection(self) -> str:
        return _run_on_ui(self._wx, lambda: str(self._c.editor.GetStringSelection()))

    def get_outline(self) -> list[str]:
        def read() -> list[str]:
            try:
                return [entry.title for entry in self._c._outline_entries()]
            except Exception:  # outline is best-effort context, never fatal
                return []

        return _run_on_ui(self._wx, read)

    def get_file_type(self) -> str:
        def read() -> str:
            path = getattr(getattr(self._c, "document", None), "path", None)
            if path is None:
                return ""
            suffix = str(path).rsplit(".", 1)
            return suffix[-1].lower() if len(suffix) == 2 else ""

        return _run_on_ui(self._wx, read)

    def get_cursor_position(self) -> tuple[int, int]:
        return _run_on_ui(self._wx, lambda: _cursor_line_col(self._c.editor))

    def get_current_section(self) -> str:
        return _run_on_ui(self._wx, lambda: _current_section_text(self._c))

    def get_status_flags(self) -> dict[str, bool]:
        return _run_on_ui(self._wx, lambda: _status_flags(self._c))

    # -- mutations (reusing the shipping undo/replace primitives) -----------

    def create_undo_checkpoint(self, label: str) -> None:
        _run_on_ui(
            self._wx,
            lambda: self._c._record_persistent_undo_state(str(self._c.editor.GetValue())),
        )

    def apply_replacement(self, text: str) -> None:
        _run_on_ui(self._wx, lambda: self._c._ai_replace_selection(text))

    def apply_insert(self, text: str) -> None:
        _run_on_ui(self._wx, lambda: self._c._ai_insert_text(text))

    def apply_document_text(self, text: str) -> None:
        _run_on_ui(self._wx, lambda: self._c._ai_set_document_text(text))

    def run_command(self, command_id: str) -> None:
        _run_on_ui(self._wx, lambda: self._c._ai_run_command(command_id))

    # -- prompts -----------------------------------------------------------

    def confirm(self, message: str) -> bool:
        def ask() -> bool:
            wx = self._c._wx
            result = self._c._show_message_box(message, "QUILL", wx.YES_NO | wx.ICON_QUESTION)
            return bool(result == wx.YES)

        return _run_on_ui(self._wx, ask)

    def preview_diff(self, review: DiffReview) -> bool:
        """Show the per-hunk review dialog; return whether the user approved.

        The gateway applies the matching mutation on its next step, so this only
        reviews — it never edits the buffer itself.
        """

        def show() -> bool:
            approved = {"v": False}

            def on_apply(_accepted_text: str) -> None:
                approved["v"] = True

            self._c.open_ai_diff_review(review.original, review.accept_all(), on_apply)
            return approved["v"]

        return _run_on_ui(self._wx, show)

    def announce(self, message: str) -> None:
        _run_on_ui(self._wx, lambda: self._c._set_status(message))


def _companion_agent() -> Any:
    """The general conversational companion AgentSpec (PRD §3).

    Reads are allowed (so it can look at the document to answer fact questions);
    edits are preview-required (so every change is reviewed and undoable). A
    ``final`` answer with no edit is a plain Q&A response.
    """
    from quill.core.ai.context_builder import ContextScope
    from quill.core.ai.harness import AgentSpec
    from quill.core.ai.permissions import Decision, PermissionCategory, RiskLevel

    return AgentSpec(
        id="quill-companion",
        display_name="Quill",
        system_prompt=(
            "You are Quill, the user's writing companion inside the QUILL editor, a "
            "screen-reader-first word processor. You help with their open document: "
            "answer questions about its content, explain and discuss topics, and make "
            "edits or revisions the user asks for. Use the read tools to look at the "
            "document, selection, outline, current section, or app state before "
            "answering. You can audit the document for accessibility issues, and — "
            "with the user's consent — research on the web to gather facts. To change "
            "the document, propose the edit through the edit tools; the user reviews "
            "and approves every change before it is applied. If the user only asks a "
            "question, answer it directly without editing. Keep answers concise and "
            "clear for screen-reader users."
        ),
        description="Your context-aware partner for the open document.",
        risk=RiskLevel.LOW,
        default_scope=ContextScope.FULL_DOCUMENT,
        permission_overrides=(
            (PermissionCategory.READ_SELECTION, Decision.ALLOW),
            (PermissionCategory.READ_DOCUMENT, Decision.ALLOW),
            (PermissionCategory.MODIFY_SELECTION, Decision.PREVIEW_REQUIRED),
            (PermissionCategory.MODIFY_DOCUMENT, Decision.PREVIEW_REQUIRED),
        ),
    )


def _companion_loop_budget() -> tuple[int, str]:
    """Pick the tool-loop step budget for the active model, degrading small ones.

    Returns ``(max_steps, engine_label)``. A model our free catalog flags as
    unreliable for tool use gets a near-single-shot budget so a weak/free model
    still answers rather than looping on malformed tool calls; capable models use
    the full loop. Best-effort — any lookup failure keeps the full budget.
    """
    from quill.core.ai.tool_loop import MAX_STEPS

    try:
        from quill.core.ai.free_models import supports_tool_use
        from quill.core.assistant_ai import load_assistant_connection_settings

        model = load_assistant_connection_settings().model.strip()
        if model and not supports_tool_use(model):
            return _WEAK_MODEL_MAX_STEPS, "Native (QUILL, simplified for a small model)"
    except Exception:  # noqa: BLE001 - degradation is a convenience, never block the chat
        pass
    return MAX_STEPS, "Native (QUILL)"


def build_companion_session(controller: Any) -> tuple[Any, str]:
    """Build a conversational companion session for the Ask Quill dialog.

    Returns ``(session, engine_name)``, or ``(None, reason)`` when no AI provider
    is available — so the caller can fall back to the legacy chat path (which lets
    the user configure a provider inline). The session drives the native multi-step
    tool loop over the user's configured provider through the Safe Editor Tool
    Gateway, so reads, edits, previews, undo, and audit all apply. SDK-pack native
    tool loops are a later phase; Phase 1 uses the provider backend.
    """
    from quill.core.ai.activity_log import ActivityLog
    from quill.core.ai.conversation import ConversationSession
    from quill.core.ai.permissions import PermissionBroker, SafetyProfile
    from quill.core.ai.provider_backend import ProviderChatBackend
    from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway
    from quill.core.ai.tool_planner import PromptToolPlanner, model_responder_from_backend

    backend = ProviderChatBackend()
    available, reason = backend.is_available()
    if not available:
        return None, reason or "AI provider is not available."

    import wx

    agent = _companion_agent()
    emit = EventBridge(AnnouncementLevel.BALANCED, controller._set_status).handle
    gateway = SafeEditorToolGateway(
        host=_CompanionEditorHost(controller, wx),
        broker=PermissionBroker(SafetyProfile.BALANCED, overrides=agent.overrides_map()),
        activity=ActivityLog(),
        identity=AgentIdentity(agent_id=agent.id, risk=agent.risk),
        emit=emit,
    )
    planner = PromptToolPlanner(model_responder_from_backend(backend))
    # Graceful degradation for small/free models: they are unreliable at the
    # multi-step tool loop and can burn steps on malformed tool calls. Cap the
    # loop low so the companion still answers (the document is already in the
    # turn's context, so a direct answer needs no tools) instead of spinning.
    max_steps, engine = _companion_loop_budget()
    session = ConversationSession(agent, gateway, planner, emit=emit, max_steps=max_steps)
    return session, engine


def prepare_companion_context(
    controller: Any, document: str, selection: str, *, need_consent: bool
) -> tuple[str, bool]:
    """Build the redacted context for one companion turn; confirm before sending.

    Returns ``(context_text, ok)``. ``context_text`` is the assembled, redacted
    payload (a selection, the whole document, or a structure-aware summary when the
    document is large). ``ok`` is False only when ``need_consent`` is set and the
    user cancelled the share preview — the caller then aborts the turn so nothing
    leaves the machine. ``document`` / ``selection`` are passed in (already read on
    the UI thread); only the consent dialog is marshalled back to the UI thread.
    """
    from quill.core.ai.context_builder import (
        ContextBuilder,
        ContextRequest,
        StringContextSource,
    )

    file_name = _file_name(controller)
    scope = choose_context_scope(selection, document)
    source = StringContextSource(
        document=document,
        selection=selection,
        file_name=file_name,
        file_type=file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "",
    )
    preview = ContextBuilder(source).build(ContextRequest(scope=scope))

    if need_consent:
        import wx

        from quill.ui.context_preview_dialog import confirm_context_share

        if not _run_on_ui(wx, lambda: confirm_context_share(controller, preview)):
            return "", False
    return preview.text, True
