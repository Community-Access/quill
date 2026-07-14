"""AI writing-action mixin for MainFrame (extracted for CQ-1 / GATE-11).

These selection-oriented AI commands (rewrite, summarize, continue, fix
grammar) and their shared guards were lifted out of ``main_frame.py`` to keep
that module under its GATE-11 module-size budget. Every method references
``self`` attributes and helpers that live on :class:`MainFrame`
(``self.editor``, ``self._selected_text``, ``self._set_status``,
``self.open_writing_assistant``), so each call resolves identically through the
method-resolution order. No behavior changed.
"""

from __future__ import annotations

from quill.core.assistant import render_assistant_prompt
from quill.core.selection import paragraph_span


class AiActionsMixin:
    """Selection-scoped AI writing actions, mixed into MainFrame."""

    # NOTE: open_ai_rewrite_selection and open_ai_summarize_selection used to live
    # here too, but MainFrame's own class body defines newer agent-task versions
    # (``_run_agent_task``) that override these via MRO — the copies here never ran.
    # They were removed to avoid two conflicting definitions of the same verb.
    # Continue Writing and Fix Grammar have no class-body override, so they remain
    # the live implementations and stay below.

    def open_ai_continue_writing(self) -> None:
        if not self._require_ai_enabled():
            return
        target = self._selected_text() or self.editor.GetValue()
        if not target.strip():
            self._set_status("Nothing to continue from. Type some text first.")
            return
        self.open_writing_assistant(
            render_assistant_prompt(
                "continue",
                selection_text=target,
                document_text=self.editor.GetValue(),
            )
        )

    def open_ai_fix_grammar(self) -> None:
        if not self._require_ai_enabled():
            return
        target, scope = self._ai_target_text(fallback="paragraph")
        if not target.strip():
            self._set_status("Nothing to check. Type or select some text first.")
            return
        self._announce_ai_scope("Checking grammar in", scope, target)
        self.open_writing_assistant(
            render_assistant_prompt(
                "grammar",
                selection_text=target,
                document_text=self.editor.GetValue(),
            )
        )

    def _require_ai_enabled(self) -> bool:
        """Return True when AI is on; otherwise announce how to enable it.

        Menu items are greyed out while AI is off, but these actions are also
        reachable via the command palette and keybindings, so guard here too.
        """
        from quill.core.ai.availability import AI_DISABLED_MESSAGE
        from quill.core.ai.model_manager import load_ai_enabled

        if load_ai_enabled():
            return True
        self._set_status(AI_DISABLED_MESSAGE)
        return False

    def _ai_target_text(self, *, fallback: str) -> tuple[str, str]:
        """Resolve the text an AI writing action should operate on.

        Returns ``(text, scope_label)``. When there is a selection it wins. With
        no selection we fall back to the current paragraph or the whole document
        so the action still does something useful instead of sending an empty
        prompt.
        """
        selected = self._selected_text()
        if selected:
            return selected, "selection"
        text = self.editor.GetValue()
        if fallback == "document":
            return text, "document"
        cursor = self.editor.GetInsertionPoint()
        start, end = paragraph_span(text, cursor)
        return text[start:end], "paragraph"

    def _announce_ai_scope(self, verb: str, scope: str, target: str) -> None:
        from quill.core.announcements import format_progress

        word_count = len(target.split())
        self._set_status(format_progress(verb, scope, count=word_count))

    # ------------------------------------------------------------------
    # Quick engine switcher (Phase 6 UI): hotkey + status-bar cell.
    # ------------------------------------------------------------------

    def _ai_engine_registry(self) -> object:
        """The cached selection registry (Native + every optional SDK pack)."""
        registry = getattr(self, "_ai_engine_registry_cache", None)
        if registry is None:
            from quill.core.ai.engines import build_engine_registry

            registry = build_engine_registry()
            self._ai_engine_registry_cache = registry
        return registry

    def _invalidate_ai_engine_caches(self) -> None:
        """Drop the cached engine label and auto-show flag after a switch."""
        self._ai_engine_label_cache = None
        self._ai_engine_autoshow_cache = None

    def ai_engine_status_text(self) -> str:
        """The status-bar text for the active engine (cached; cheap per refresh)."""
        cached = getattr(self, "_ai_engine_label_cache", None)
        if cached is not None:
            return cached
        from quill.core.ai.quick_switch import active_target

        try:
            target = active_target(self._ai_engine_registry())
            label = target.display_name if target is not None else "None"
        except Exception:  # noqa: BLE001 - status bar must never crash
            label = ""
        self._ai_engine_label_cache = label
        return label

    def _ai_engine_should_autoshow(self) -> bool:
        """True when AI is on and a non-Native agentic engine is preferred.

        Cached and invalidated on switch so the per-keystroke status-bar refresh
        does not re-read the choice file every caret move.
        """
        cached = getattr(self, "_ai_engine_autoshow_cache", None)
        if cached is not None:
            return cached
        try:
            from quill.core.ai.model_manager import load_ai_enabled
            from quill.core.ai.quick_switch import preferred_harness_id

            result = load_ai_enabled() and preferred_harness_id() not in ("auto", "native")
        except Exception:  # noqa: BLE001
            result = False
        self._ai_engine_autoshow_cache = result
        return result

    def cycle_ai_engine(self) -> None:
        """Round-robin to the next available AI engine (the hotkey)."""
        if not self._require_ai_enabled():
            return
        from quill.core.ai.quick_switch import announce_switch, cycle_next

        try:
            target = cycle_next(self._ai_engine_registry())
        except ValueError as exc:
            self._set_status(str(exc))
            return
        self._invalidate_ai_engine_caches()
        self._refresh_statusbar()
        self._set_status(announce_switch(target))

    def open_ai_engine_switcher(self) -> None:
        """Pop up a radio list of engines (the status-bar cell's Enter action)."""
        if not self._require_ai_enabled():
            return
        wx = self._wx
        from quill.core.ai.quick_switch import announce_switch, list_targets, set_active

        registry = self._ai_engine_registry()
        targets = list_targets(registry)
        menu = wx.Menu()
        id_to_harness: dict[int, str] = {}
        for target in targets:
            label = target.display_name
            if not target.available:
                label = f"{target.display_name}  (not installed)"
            item = menu.AppendRadioItem(wx.ID_ANY, label)
            item.Check(target.active)
            id_to_harness[item.GetId()] = target.harness_id

        def _on_select(event: object) -> None:
            harness_id = id_to_harness.get(event.GetId())
            if harness_id is None:
                return
            chosen = set_active(registry, harness_id)
            self._invalidate_ai_engine_caches()
            self._refresh_statusbar()
            self._set_status(announce_switch(chosen))
            # Picking an engine whose SDK is not installed is an explicit request
            # to set it up. Copilot has a guided onboarding (install + sign-in).
            if not chosen.available and chosen.harness_id == "copilot":
                self.open_copilot_onboarding()

        menu.Bind(wx.EVT_MENU, _on_select)
        self.frame.PopupMenu(menu)
        menu.Destroy()

    def open_copilot_onboarding(self) -> None:
        """Open the guided GitHub Copilot setup (install SDK + device sign-in)."""
        if not self._require_ai_enabled():
            return
        from quill.ui.copilot_onboarding_dialog import CopilotOnboardingDialog

        dialog = CopilotOnboardingDialog(
            self.frame, self._show_modal_dialog, announce=self._set_status
        )
        dialog.show()
        self._invalidate_ai_engine_caches()
        self._refresh_statusbar()
        self._request_menu_refresh()

    def open_agent_validator(self) -> None:
        """Open the Validate Agents dialog (the agent standards linter, in-app)."""
        from quill.ui.agent_validator_dialog import AgentValidatorDialog

        AgentValidatorDialog(self.frame, self._show_modal_dialog, announce=self._set_status).show()
