from __future__ import annotations

import threading
from collections.abc import Callable

from quill.core.accessibility_agent import (
    AccessibilityPlan,
    AgentRunResult,
    apply_plan,
    build_plan,
    summarize_plan,
)
from quill.core.assistant import (
    assistant_prompt_presets,
    build_assistant_tools,
    rank_assistant_tools,
    render_assistant_prompt,
)
from quill.core.assistant_ai import (
    AssistantConnectionSettings,
    ModelRecommendation,
    clear_provider_api_key,
    default_host_for_provider,
    default_model_for_provider,
    filter_model_names,
    list_assistant_models,
    load_assistant_api_key,
    load_assistant_connection_settings,
    load_provider_api_key,
    load_provider_model,
    missing_required_api_key,
    provider_api_key_label,
    provider_api_key_storage_hint,
    provider_display_name,
    provider_help_text,
    provider_requires_api_key,
    recommended_model_guidance,
    save_assistant_connection_settings,
    set_active_provider,
    test_chat,
    verify_assistant_connection,
)
from quill.core.commands import CommandRegistry
from quill.core.features import FeatureManager
from quill.core.python_sandbox import PythonSandboxResult, run_python_sandbox
from quill.ui.dialog_contract import apply_modal_ids, show_message_box, show_modal_dialog


class RunPythonDialog:
    def __init__(
        self,
        parent: object,
        *,
        document_text: str,
        selection_text: str,
        outline: list[dict[str, object]] | None = None,
        apply_callback: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        self._document_text = document_text
        self._selection_text = selection_text
        self._outline = outline
        self._apply_callback = apply_callback
        self._latest_result: PythonSandboxResult | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Run Python",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((900, 680))

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Restricted Python (allowlist + resource limits; not a security boundary). "
                    "Set result or print output, then apply the transformed text."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        self.code = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_PROCESS_TAB | wx.BORDER_SIMPLE,
            size=(-1, 280),
        )
        self.code.SetValue(
            "# document_text and selection_text are available.\n"
            "# Set result or call set_result(...).\n"
            "result = selection_text or document_text\n"
        )
        root.Add(self.code, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.status = wx.StaticText(self.dialog, label="Ready.")
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.preview = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 220),
        )
        root.Add(self.preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.run_button = wx.Button(self.dialog, label="Run")
        self.apply_button = wx.Button(self.dialog, label="Apply Result")
        self.close_button = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Close")
        self.apply_button.Enable(False)
        buttons.Add(self.run_button, 0, wx.RIGHT, 8)
        buttons.Add(self.apply_button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(self.close_button, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        self.run_button.Bind(wx.EVT_BUTTON, self._on_run)
        self.apply_button.Bind(wx.EVT_BUTTON, self._on_apply)
        self.close_button.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))
        self.code.SetFocus()

    def show_modal(self) -> None:
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(self.dialog, "Run Python")
        finally:
            self.dialog.Destroy()

    def _on_run(self, _event: object) -> None:
        self.run_button.Enable(False)
        self.apply_button.Enable(False)
        self.status.SetLabel("Running...")
        code = self.code.GetValue()

        def _do_run() -> None:
            result = run_python_sandbox(
                code,
                document_text=self._document_text,
                selection_text=self._selection_text,
                outline=self._outline,
            )
            self._wx.CallAfter(self._finish_run, result)

        threading.Thread(  # GATE-40-OK: python sandbox run; bounded by timeout.
            target=_do_run, name="quill-python-sandbox", daemon=True
        ).start()

    def _finish_run(self, result: PythonSandboxResult) -> None:
        self._latest_result = result
        self.preview.SetValue(self._render_result(result))
        self.apply_button.Enable(
            result.succeeded and bool((result.result or result.stdout).strip())
        )
        self.run_button.Enable(True)
        if result.succeeded:
            self.status.SetLabel(f"Completed in {result.elapsed_seconds:.2f}s.")
            return
        if result.timed_out:
            self.status.SetLabel("Execution timed out.")
            return
        if result.error:
            self.status.SetLabel("Execution failed.")
            return
        self.status.SetLabel("Execution finished.")

    def _on_apply(self, _event: object) -> None:
        if self._latest_result is None:
            return
        updated = self._latest_result.result.strip() or self._latest_result.stdout.strip()
        if not updated:
            return
        self._apply_callback(updated)
        self.dialog.EndModal(self._wx.ID_OK)

    def _render_result(self, result: PythonSandboxResult) -> str:
        parts = [
            f"Return code: {result.returncode}",
            f"Timed out: {result.timed_out}",
            "",
        ]
        if result.result:
            parts.extend(("Result:", result.result, ""))
        if result.stdout:
            parts.extend(("Stdout:", result.stdout, ""))
        if result.stderr:
            parts.extend(("Stderr:", result.stderr, ""))
        if result.error:
            parts.extend(("Error:", result.error, ""))
        return "\n".join(parts).strip()


class AccessibilityAgentDialog:
    """Reviewable, per-step, single-undo "make this document accessible" agent.

    Surfaces the deterministic plan from
    :mod:`quill.core.accessibility_agent` as an accessible checklist. Each
    automatically-fixable step is pre-checked; advisory steps that need human
    judgement are listed for review but cannot be auto-applied. Applying the
    accepted steps is handed back to the caller as a single text replacement so
    the editor records it as one undo unit.
    """

    def __init__(
        self,
        parent: object,
        *,
        document_name: str,
        document_text: str,
        markup: str,
        scope_label: str,
        on_apply: Callable[[AgentRunResult], None],
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._document_text = document_text
        self._on_apply = on_apply
        self._announce = announce or (lambda _message: None)
        self.plan: AccessibilityPlan = build_plan(document_name, document_text, markup, scope_label)
        self.applied = False

        self.dialog = wx.Dialog(
            parent,
            title="Accessibility Tune-Up",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((860, 620))

        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                panel,
                label=(
                    "Accessibility Tune-Up audited this document and proposes the "
                    "steps below. Checked steps are applied automatically; unchecked "
                    "steps need your review. Nothing changes until you choose Apply."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        self.summary = wx.StaticText(panel, label=summarize_plan(self.plan))
        root.Add(self.summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(
            wx.StaticText(panel, label="Proposed steps"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self.step_list = wx.CheckListBox(  # A11Y-SR-1-OK: GLOW steps; pending CheckBox conversion
            panel,
            choices=[self._step_label(step) for step in self.plan.steps],
        )
        root.Add(self.step_list, 1, wx.EXPAND | wx.ALL, 8)
        for index, step in enumerate(self.plan.steps):
            if step.auto_fixable:
                self.step_list.Check(index, True)

        root.Add(
            wx.StaticText(panel, label="Step details"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self.details = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 150),
        )
        root.Add(self.details, 0, wx.EXPAND | wx.ALL, 8)

        self.status = wx.StaticText(panel, label="Ready to apply the checked steps.")
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.apply_button = wx.Button(panel, label="Apply Checked Steps")
        buttons.Add(self.apply_button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        close_button = wx.Button(panel, id=wx.ID_CANCEL, label="Close")
        buttons.Add(close_button, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self.step_list.Bind(wx.EVT_LISTBOX, self._on_step_selected)
        self.apply_button.Bind(wx.EVT_BUTTON, self._on_apply_clicked)
        close_button.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

        if self.plan.steps:
            self.step_list.SetSelection(0)
            self._show_step_details(0)
        else:
            self.apply_button.Enable(False)
            self.details.SetValue(
                "No actionable accessibility issues were detected. The document is "
                "ready for deeper human review and export checks."
            )

    def show_modal(self) -> None:
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(self.dialog, "Accessibility Tune-Up")
        finally:
            self.dialog.Destroy()

    def _step_label(self, step: object) -> str:
        # step is AgentStep; build a screen-reader-friendly one-line label.
        assert hasattr(step, "title")
        location = f" (line {step.line})" if step.line is not None else ""
        tag = "" if step.auto_fixable else " — needs review"
        return f"{step.category}: {step.title}{location}{tag}"

    def _on_step_selected(self, _event: object) -> None:
        index = self.step_list.GetSelection()
        if index != self._wx.NOT_FOUND and 0 <= index < len(self.plan.steps):
            self._show_step_details(index)

    def _show_step_details(self, index: int) -> None:
        step = self.plan.steps[index]
        lines = [step.title, "", step.rationale, ""]
        if step.auto_fixable and step.after != step.before:
            lines.append(f"Before: {step.before}")
            lines.append(f"After: {step.after}")
        else:
            lines.append(f"Context: {step.before}")
            lines.append(
                "This step needs your judgement, so Accessibility Tune-Up will not "
                "change it automatically. Edit it in the document after closing."
            )
        self.details.SetValue("\n".join(lines))

    def _on_apply_clicked(self, _event: object) -> None:
        accepted = {
            self.plan.steps[index].step_id
            for index in range(len(self.plan.steps))
            if self.step_list.IsChecked(index)
        }
        result = apply_plan(self.plan, self._document_text, accepted)
        if not result.changed:
            self.status.SetLabel(
                "No automatic changes were applied. Checked steps may need your review."
            )
            self._announce("Accessibility Tune-Up made no automatic changes")
            return
        self.applied = True
        self._on_apply(result)
        self._announce(
            f"Accessibility Tune-Up applied {len(result.applied)} "
            f"{'change' if len(result.applied) == 1 else 'changes'}"
        )
        self.dialog.EndModal(self._wx.ID_OK)


class DiffReviewDialog:
    """Accessible, line-by-line review of an AI edit (AI-7).

    Presents the diff between the current document text and a proposed revision
    as a navigable checklist of added / removed / changed hunks. Each hunk is
    pre-checked; the reader can read every change line by line in the detail
    pane, then apply all, some (partial apply), or none (reject). Applying is
    handed back to the caller as a single replacement text so the editor records
    it as one undo unit.
    """

    def __init__(
        self,
        parent: object,
        *,
        title: str,
        original_text: str,
        revised_text: str,
        on_apply: Callable[[str], None],
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        from quill.core.ai.diff_review import build_diff_review

        self._wx = wx
        self._on_apply = on_apply
        self._announce = announce or (lambda _message: None)
        self.review = build_diff_review(original_text, revised_text)
        self.applied = False

        self.dialog = wx.Dialog(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((880, 640))

        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        single = len(self.review.hunks) == 1
        intro = (
            "Review the proposed AI change below. Read it line by line in the "
            "details pane, then choose Accept to apply it or Reject to leave the "
            "document unchanged."
            if single
            else (
                "Review the proposed AI changes below. Checked hunks will be "
                "applied; uncheck any you want to keep as-is. Read each hunk "
                "line by line in the details pane. Use Apply Checked for a "
                "partial apply, Accept All to take every change, or Reject All "
                "to leave the document unchanged."
            )
        )
        root.Add(
            wx.StaticText(panel, label=intro),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        self.summary = wx.StaticText(panel, label=self.review.summary())
        root.Add(self.summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(wx.StaticText(panel, label="Changes"), 0, wx.LEFT | wx.RIGHT, 8)
        self.hunk_list = wx.CheckListBox(  # A11Y-SR-1-OK: diff hunks; pending CheckBox conversion
            panel,
            choices=[hunk.describe() for hunk in self.review.hunks],
        )
        root.Add(self.hunk_list, 1, wx.EXPAND | wx.ALL, 8)
        for index in range(len(self.review.hunks)):
            self.hunk_list.Check(index, True)

        root.Add(wx.StaticText(panel, label="Change details"), 0, wx.LEFT | wx.RIGHT, 8)
        self.details = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 170),
        )
        root.Add(self.details, 0, wx.EXPAND | wx.ALL, 8)

        self.status = wx.StaticText(panel, label="Ready to apply the checked changes.")
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        action_buttons: list = []
        if single:
            # A single change needs no bulk controls or partial apply: Accept
            # applies it and closes; Reject closes and leaves the document as-is.
            self.apply_button = wx.Button(panel, id=wx.ID_OK, label="Accept")
            reject_button = wx.Button(panel, id=wx.ID_CANCEL, label="Reject")
            buttons.Add(self.apply_button, 0, wx.RIGHT, 8)
            buttons.AddStretchSpacer(1)
            buttons.Add(reject_button, 0)
            self.apply_button.Bind(wx.EVT_BUTTON, self._on_accept_all_clicked)
            reject_button.Bind(wx.EVT_BUTTON, self._on_reject_clicked)
            action_buttons.append(self.apply_button)
        else:
            self.apply_button = wx.Button(panel, label="Apply Checked")
            accept_all_button = wx.Button(panel, label="Accept All")
            reject_all_button = wx.Button(panel, id=wx.ID_CANCEL, label="Reject All")
            buttons.Add(self.apply_button, 0, wx.RIGHT, 8)
            buttons.Add(accept_all_button, 0, wx.RIGHT, 8)
            buttons.AddStretchSpacer(1)
            buttons.Add(reject_all_button, 0)
            self.apply_button.Bind(wx.EVT_BUTTON, self._on_apply_clicked)
            accept_all_button.Bind(wx.EVT_BUTTON, self._on_accept_all_clicked)
            reject_all_button.Bind(wx.EVT_BUTTON, self._on_reject_clicked)
            action_buttons.extend([self.apply_button, accept_all_button, reject_all_button])
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self.hunk_list.Bind(wx.EVT_LISTBOX, self._on_hunk_selected)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

        if self.review.hunks:
            self.hunk_list.SetSelection(0)
            self._show_hunk_details(0)
        else:
            for button in action_buttons:
                button.Enable(False)
            self.details.SetValue(
                "The proposed revision is identical to the current document. "
                "There is nothing to apply."
            )

    def show_modal(self) -> None:
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(self.dialog, self.dialog.GetTitle())
        finally:
            self.dialog.Destroy()

    def _on_hunk_selected(self, _event: object) -> None:
        index = self.hunk_list.GetSelection()
        if index != self._wx.NOT_FOUND and 0 <= index < len(self.review.hunks):
            self._show_hunk_details(index)

    def _show_hunk_details(self, index: int) -> None:
        hunk = self.review.hunks[index]
        self.details.SetValue("\n".join(hunk.detail_lines()))

    def _on_accept_all_clicked(self, event: object) -> None:
        """Accept every hunk and apply in one step (also serves single Accept)."""
        for index in range(len(self.review.hunks)):
            self.hunk_list.Check(index, True)
        self._on_apply_clicked(event)

    def _on_reject_clicked(self, _event: object) -> None:
        """Reject everything and dismiss the dialog without touching the document."""
        self.applied = False
        count = len(self.review.hunks)
        label = "Rejected the change" if count == 1 else "Rejected all changes"
        self._announce(f"{label}; the document is unchanged")
        self.dialog.EndModal(self._wx.ID_CANCEL)

    def _on_apply_clicked(self, _event: object) -> None:
        accepted = {
            index for index in range(len(self.review.hunks)) if self.hunk_list.IsChecked(index)
        }
        result_text = self.review.apply(accepted)
        if result_text == self.review.original:
            self.status.SetLabel("No changes were applied; the document is unchanged.")
            self._announce("No changes were applied")
            return
        self.applied = True
        self._on_apply(result_text)
        count = len(accepted)
        self._announce(f"Applied {count} {'change' if count == 1 else 'changes'} as one undo step")
        self.dialog.EndModal(self._wx.ID_OK)


class WritingAssistantDialog:
    def __init__(
        self,
        parent: object,
        command_registry: CommandRegistry,
        feature_manager: FeatureManager | None,
        *,
        open_python_tool: Callable[[], None],
        selection_text: str = "",
        document_text: str = "",
        initial_prompt: str = "",
        assistant_enabled: bool = False,
        prompt_style: str = "balanced",
    ) -> None:
        import wx

        self._wx = wx
        self._registry = command_registry
        self._open_python_tool = open_python_tool
        self._selection_text = selection_text
        self._document_text = document_text
        self._assistant_enabled = assistant_enabled
        self._prompt_style = prompt_style
        self._all_tools = build_assistant_tools(command_registry, feature_manager)
        self._filtered_tools = list(self._all_tools)
        self._prompt_presets = assistant_prompt_presets()

        self.dialog = wx.Dialog(
            parent,
            title="Writing Assistant",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((960, 700))

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Use the local command catalog to find writing actions quickly. "
                    "This shell is CPU-only and keeps tool actions accessible."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        preset_row = wx.BoxSizer(wx.HORIZONTAL)
        self.preset_choice = wx.Choice(
            self.dialog,
            choices=[preset.title for preset in self._prompt_presets],
        )
        self.preset_choice.SetSelection(0 if self._prompt_presets else wx.NOT_FOUND)
        self.load_prompt_button = wx.Button(self.dialog, label="Load Prompt")
        self.use_selection_button = wx.Button(self.dialog, label="Use Selection")
        self.use_document_button = wx.Button(self.dialog, label="Use Document")
        preset_row.Add(
            wx.StaticText(self.dialog, label="Prompt presets"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        preset_row.AddSpacer(8)
        preset_row.Add(self.preset_choice, 1, wx.RIGHT, 8)
        preset_row.Add(self.load_prompt_button, 0, wx.RIGHT, 8)
        preset_row.Add(self.use_selection_button, 0, wx.RIGHT, 8)
        preset_row.Add(self.use_document_button, 0)
        root.Add(preset_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # No TE_PROCESS_TAB: this is a prose prompt, so Tab must move focus to the
        # next control rather than insert a tab character (keyboard-trap fix).
        self.prompt = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        self.prompt.SetName("Prompt")
        self.prompt.SetHint("Describe the edit, review, or command you want")
        if initial_prompt.strip():
            self.prompt.SetValue(initial_prompt)
        elif self._prompt_presets:
            self.prompt.SetValue(
                render_assistant_prompt(
                    self._prompt_presets[0].name,
                    selection_text=self._selection_text,
                    document_text=self._document_text,
                )
            )
        root.Add(self.prompt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.status = wx.StaticText(self.dialog, label="Showing all available tools.")
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.chat_log = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 110),
        )
        self.chat_log.SetValue(self._initial_chat_log())
        root.Add(self.chat_log, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.results = wx.ListBox(self.dialog)
        root.Add(self.results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.details = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 120),
        )
        root.Add(self.details, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.suggest_button = wx.Button(self.dialog, label="Suggest")
        self.run_button = wx.Button(self.dialog, id=wx.ID_OK, label="Run Selected Action")
        self.python_button = wx.Button(self.dialog, label="Run Python...")
        self.close_button = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Close")
        buttons.Add(self.suggest_button, 0, wx.RIGHT, 8)
        buttons.Add(self.run_button, 0, wx.RIGHT, 8)
        buttons.Add(self.python_button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(self.close_button, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.suggest_button.Bind(wx.EVT_BUTTON, self._on_suggest)
        self.run_button.Bind(wx.EVT_BUTTON, self._on_run_selected)
        self.python_button.Bind(wx.EVT_BUTTON, lambda _e: self._open_python_tool())
        self.close_button.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))
        self.results.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
        self.results.Bind(wx.EVT_LISTBOX_DCLICK, self._on_run_selected)
        self.prompt.Bind(wx.EVT_TEXT, self._on_prompt_changed)
        self.load_prompt_button.Bind(wx.EVT_BUTTON, self._on_load_prompt)
        self.use_selection_button.Bind(wx.EVT_BUTTON, self._on_use_selection)
        self.use_document_button.Bind(wx.EVT_BUTTON, self._on_use_document)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        self._refresh_results()

    def show_modal(self) -> None:
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(self.dialog, "Writing Assistant")
        finally:
            self.dialog.Destroy()

    def _on_char_hook(self, event: object) -> None:
        key_code = event.GetKeyCode()
        if key_code in (self._wx.WXK_RETURN, self._wx.WXK_NUMPAD_ENTER) and not event.ShiftDown():
            self._run_selected()
            return
        event.Skip()

    def _on_prompt_changed(self, _event: object) -> None:
        self._refresh_results()

    def _on_suggest(self, _event: object) -> None:
        self._refresh_results()

    def _initial_chat_log(self) -> str:
        lines = [
            "Chat log:",
            "- Use a preset to seed a prompt.",
            "- Run a command or Python transform, then apply the result back into the editor.",
        ]
        if self._assistant_enabled:
            lines.append(f"- Assistant prompts are enabled with the {self._prompt_style} style.")
        return "\n".join(lines)

    def _append_chat_log(self, line: str) -> None:
        current = self.chat_log.GetValue().rstrip()
        if current:
            current += "\n"
        self.chat_log.SetValue(f"{current}{line}".strip())

    def _on_load_prompt(self, _event: object) -> None:
        self._apply_prompt_from_preset()

    def _on_use_selection(self, _event: object) -> None:
        self.prompt.SetValue(self._selection_text.strip())
        self._append_chat_log("Loaded selection into the prompt.")

    def _on_use_document(self, _event: object) -> None:
        self.prompt.SetValue(self._document_text.strip())
        self._append_chat_log("Loaded document text into the prompt.")

    def _apply_prompt_from_preset(self) -> None:
        selected = self.preset_choice.GetSelection()
        if selected == self._wx.NOT_FOUND or selected < 0 or selected >= len(self._prompt_presets):
            return
        preset = self._prompt_presets[selected]
        prompt = render_assistant_prompt(
            preset.name,
            selection_text=self._selection_text,
            document_text=self._document_text,
        )
        self.prompt.SetValue(prompt)
        self._append_chat_log(f"Loaded preset: {preset.title}")

    def _refresh_results(self) -> None:
        query = self.prompt.GetValue()
        self._filtered_tools = rank_assistant_tools(query, self._all_tools, limit=50)
        labels: list[str] = []
        for tool in self._filtered_tools:
            suffix = f" [{tool.command_id}]" if tool.command_id else ""
            labels.append(f"{tool.title}{suffix}")
        self.results.Set(labels)
        if labels:
            self.results.SetSelection(0)
            self._update_details()
            self.status.SetLabel(f"{len(labels)} tool(s) matched.")
        else:
            self.details.SetValue("")
            self.status.SetLabel("No matching tools.")

    def _on_selection_changed(self, _event: object) -> None:
        self._update_details()

    def _update_details(self) -> None:
        selected = self.results.GetSelection()
        if selected == self._wx.NOT_FOUND:
            return
        if selected < 0 or selected >= len(self._filtered_tools):
            return
        tool = self._filtered_tools[selected]
        extra = ""
        if tool.command_id:
            extra = f"\nCommand: {tool.command_id}"
        self.details.SetValue(
            f"{tool.title}\n\n{tool.description}\n\nCategory: {tool.category}{extra}"
        )

    def _on_run_selected(self, _event: object) -> None:
        self._run_selected()

    def _run_selected(self) -> None:
        selected = self.results.GetSelection()
        if selected == self._wx.NOT_FOUND:
            return
        if selected < 0 or selected >= len(self._filtered_tools):
            return
        tool = self._filtered_tools[selected]
        if tool.command_id is None:
            if tool.name == "run_python":
                self._open_python_tool()
            return
        if tool.requires_confirmation:
            answer = show_message_box(
                f"Run '{tool.title}' now?",
                "Confirm Assistant Action",
                self._wx.YES_NO | self._wx.ICON_WARNING,
                self.dialog,
            )
            if answer != self._wx.YES:
                return
        self._append_chat_log(f"Ran action: {tool.title}")
        self._registry.run(tool.command_id)
        self.dialog.EndModal(self._wx.ID_OK)


class SearchableModelPickerDialog:
    def __init__(self, parent: object, models: list[str]) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(
            parent,
            title="Available Models",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((640, 520))
        self._models = models
        self._filtered_models = list(models)

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self.dialog, label="Search models"), 0, wx.ALL, 8)
        self.query = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self.query.SetName("Search models")
        root.Add(self.query, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.listbox = wx.ListBox(self.dialog, choices=self._filtered_models)
        root.Add(self.listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        self.query.Bind(wx.EVT_TEXT, self._on_query_changed)
        self.query.Bind(wx.EVT_TEXT_ENTER, self._on_query_enter)
        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._on_double_click)
        if self._filtered_models:
            self.listbox.SetSelection(0)
        self.query.SetFocus()

    def _on_query_changed(self, _event: object) -> None:
        query = self.query.GetValue()
        self._filtered_models = filter_model_names(self._models, query)
        self.listbox.Set(self._filtered_models)
        if self._filtered_models:
            self.listbox.SetSelection(0)

    def _on_query_enter(self, _event: object) -> None:
        if self._filtered_models:
            self.dialog.EndModal(self._wx.ID_OK)

    def _on_double_click(self, _event: object) -> None:
        self.dialog.EndModal(self._wx.ID_OK)

    def show_modal_and_get_selection(self) -> str:
        try:
            if show_modal_dialog(self.dialog, "Available Models") != self._wx.ID_OK:
                return ""
            selection = self.listbox.GetSelection()
            if selection == self._wx.NOT_FOUND:
                return ""
            if selection < 0 or selection >= len(self._filtered_models):
                return ""
            return self._filtered_models[selection].strip()
        finally:
            self.dialog.Destroy()


class AIHubDialog:
    def __init__(
        self,
        parent: object,
        *,
        open_connection: Callable[[], None],
        open_model_settings: Callable[[], None],
        open_writing_assistant: Callable[[str], None],
        open_prompt_studio: Callable[[], None],
        open_agent_center: Callable[[], None],
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._open_connection = open_connection
        self._open_model_settings = open_model_settings
        self._open_writing_assistant = open_writing_assistant
        self._open_prompt_studio = open_prompt_studio
        self._open_agent_center = open_agent_center
        self._announce = announce or (lambda _message: None)
        self._settings = load_assistant_connection_settings()
        self._api_key = load_assistant_api_key()

        self.dialog = wx.Dialog(
            parent,
            title="AI Hub",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((760, 560))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "AI Hub centralizes provider health, model selection, prompt workflows, "
                    "and agent entry points."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        self.summary = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 220),
        )
        root.Add(self.summary, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.status = wx.StaticText(self.dialog, label="Ready.")
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        actions = wx.GridSizer(rows=3, cols=3, hgap=8, vgap=8)
        self.verify_button = wx.Button(self.dialog, label="Verify Now")
        self.list_models_button = wx.Button(self.dialog, label="List Models")
        self.connection_button = wx.Button(self.dialog, label="Open Connection")
        self.model_button = wx.Button(self.dialog, label="Model Settings")
        self.prompt_button = wx.Button(self.dialog, label="Prompt Studio")
        self.agent_button = wx.Button(self.dialog, label="Agent Center")
        self.writing_button = wx.Button(self.dialog, label="Writing Assistant")
        actions.Add(self.verify_button, 0, wx.EXPAND)
        actions.Add(self.list_models_button, 0, wx.EXPAND)
        actions.Add(self.connection_button, 0, wx.EXPAND)
        actions.Add(self.model_button, 0, wx.EXPAND)
        actions.Add(self.prompt_button, 0, wx.EXPAND)
        actions.Add(self.agent_button, 0, wx.EXPAND)
        actions.Add(self.writing_button, 0, wx.EXPAND)
        actions.AddSpacer(0)
        actions.AddSpacer(0)
        root.Add(actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        close_row = wx.BoxSizer(wx.HORIZONTAL)
        close_row.AddStretchSpacer(1)
        close_row.Add(wx.Button(self.dialog, id=wx.ID_CLOSE, label="Close"), 0)
        root.Add(close_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.verify_button.Bind(wx.EVT_BUTTON, self._on_verify)
        self.list_models_button.Bind(wx.EVT_BUTTON, self._on_list_models)
        self.connection_button.Bind(wx.EVT_BUTTON, self._on_open_connection)
        self.model_button.Bind(wx.EVT_BUTTON, self._on_open_model)
        self.prompt_button.Bind(wx.EVT_BUTTON, self._on_open_prompt_studio)
        self.agent_button.Bind(wx.EVT_BUTTON, self._on_open_agent_center)
        self.writing_button.Bind(wx.EVT_BUTTON, self._on_open_writing_assistant)
        self.dialog.Bind(
            wx.EVT_BUTTON,
            lambda _e: self.dialog.EndModal(wx.ID_CLOSE),
            id=wx.ID_CLOSE,
        )
        apply_modal_ids(self.dialog, escape_id=wx.ID_CLOSE)
        self._refresh_summary()

    def show_modal(self) -> None:
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(self.dialog, "AI Hub")
        finally:
            self.dialog.Destroy()

    def _refresh_summary(self, verification: str = "Not checked") -> None:
        self._settings = load_assistant_connection_settings()
        provider = self._settings.provider or "off"
        host = self._settings.host or default_host_for_provider(provider)
        model = self._settings.model or default_model_for_provider(provider)
        requires_key = provider_requires_api_key(provider)
        key_state = "present" if bool(self._api_key.strip()) else "missing"
        guidance = "\n".join(
            f"- {item.model}: {item.framing} ({item.reason})"
            for item in recommended_model_guidance(provider)[:2]
        )
        summary = (
            f"Provider: {provider}\n"
            f"Host: {host or '(not required)'}\n"
            f"Model: {model or '(none)'}\n"
            f"API key required: {requires_key}\n"
            f"API key status: {key_state}\n"
            f"Verification: {verification}\n\n"
            "Recommended model guidance:\n"
            f"{guidance or '- No guidance available.'}\n\n"
            "Safety defaults:\n"
            "- Prompt and agent changes are review-first.\n"
            "- Destructive actions require explicit confirmation.\n"
            "- Cloud connections are user-configured and visible.\n"
            "- Chat transcripts are not persisted by default.\n"
            "- Your API key is stored securely on this device and never shared."
        )
        self.summary.SetValue(summary)

    def _on_verify(self, _event: object) -> None:
        self._settings = load_assistant_connection_settings()
        self._api_key = load_assistant_api_key()
        ok, message = verify_assistant_connection(self._settings, self._api_key)
        self.status.SetLabel(message)
        self._refresh_summary(verification=message)
        self._announce(message)
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        show_message_box(
            message, "AI Hub Verification", icon | self._wx.OK, self.dialog, announce=self._announce
        )

    def _on_list_models(self, _event: object) -> None:
        self._settings = load_assistant_connection_settings()
        self._api_key = load_assistant_api_key()
        models, error = list_assistant_models(self._settings, self._api_key)
        if error is not None:
            self.status.SetLabel(error)
            show_message_box(
                error,
                "AI Hub Models",
                self._wx.ICON_WARNING | self._wx.OK,
                self.dialog,
                announce=self._announce,
            )
            return
        if not models:
            message = "No models were returned by the endpoint."
            self.status.SetLabel(message)
            show_message_box(
                message,
                "AI Hub Models",
                self._wx.ICON_INFORMATION | self._wx.OK,
                self.dialog,
                announce=self._announce,
            )
            return
        picker = SearchableModelPickerDialog(self.dialog, models)
        selected = picker.show_modal_and_get_selection()
        if not selected:
            self.status.SetLabel("Model selection cancelled.")
            return
        self._settings.model = selected
        save_assistant_connection_settings(self._settings)
        self.status.SetLabel(f"Selected model: {selected}")
        self._refresh_summary(verification="Model updated from AI Hub")
        self._announce(f"Selected model {selected}")

    def _on_open_connection(self, _event: object) -> None:
        self._open_connection()
        self._api_key = load_assistant_api_key()
        self._refresh_summary(verification="Connection settings updated")

    def _on_open_model(self, _event: object) -> None:
        self._open_model_settings()
        self._refresh_summary(verification="Model settings opened")

    def _on_open_prompt_studio(self, _event: object) -> None:
        self._open_prompt_studio()
        self._refresh_summary(verification="Prompt Studio opened")

    def _on_open_agent_center(self, _event: object) -> None:
        self._open_agent_center()
        self._refresh_summary(verification="Agent Center opened")

    def _on_open_writing_assistant(self, _event: object) -> None:
        self._open_writing_assistant("")
        self._refresh_summary(verification="Writing Assistant opened")


class AssistantConnectionDialog:
    _PROVIDER_CHOICES: tuple[tuple[str, str], ...] = (
        ("off", "Off"),
        ("ollama", "Ollama (local)"),
        ("openai", "OpenAI"),
        ("custom", "OpenAI-compatible (base URL + key + model)"),
        ("claude", "Claude"),
        ("openrouter", "OpenRouter"),
        ("gemini", "Google Gemini"),
        ("ollama_cloud", "Ollama Cloud (API key)"),
    )

    def __init__(self, parent: object, open_model_settings: object | None = None) -> None:
        import wx

        self._wx = wx
        self._open_model_settings = open_model_settings
        self.dialog = wx.Dialog(
            parent,
            title="AI Hub",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((780, 520))

        self._settings = load_assistant_connection_settings()
        # Prefer the per-provider key for the initial provider so the field
        # always matches what is selected, even when the legacy active-key store
        # still holds a different provider's key from a previous session.
        _initial_provider = self._settings.provider.strip().lower() or "ollama"
        _per_provider_key = load_provider_api_key(_initial_provider)
        self._api_key = _per_provider_key or load_assistant_api_key()
        self._api_key_revealed = False
        self.last_verification_ok: bool | None = None
        self.last_verification_message: str = "Not checked"

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Select a provider, verify connection, then list/filter models. "
                    "For supported cloud providers, default hosts are prefilled."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        panel = wx.Panel(self.dialog)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        self.provider = wx.Choice(
            panel,
            choices=[label for _value, label in self._PROVIDER_CHOICES],
        )
        self.provider.SetName("Provider")
        self.provider.SetSelection(self._provider_choice_index(self._settings.provider))
        panel_sizer.Add(
            wx.StaticText(panel, label="Provider"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        panel_sizer.Add(self.provider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.provider_hint = wx.StaticText(panel, label="")
        panel_sizer.Add(self.provider_hint, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.host = wx.TextCtrl(panel)
        self.host.SetValue(
            self._settings.host or default_host_for_provider(self._settings.provider)
        )
        self.host.SetName("Host URL")
        panel_sizer.Add(wx.StaticText(panel, label="Host URL"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        panel_sizer.Add(self.host, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.model = wx.ComboBox(panel, style=wx.CB_DROPDOWN)
        self.model.SetValue(self._settings.model)
        self.model.SetName("Model")
        panel_sizer.Add(wx.StaticText(panel, label="Model"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        panel_sizer.Add(self.model, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self._set_model_choices(
            self._model_choices_for_provider(self._settings.provider),
            preferred=self._settings.model,
        )

        self.api_key_label = wx.StaticText(
            panel,
            label=provider_api_key_label(self._settings.provider),
        )
        panel_sizer.Add(self.api_key_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.api_key_row = wx.BoxSizer(wx.HORIZONTAL)
        self.api_key = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self.api_key.SetValue(self._api_key)
        self.api_key.SetName("API key")
        self.api_key_row.Add(self.api_key, 1, wx.EXPAND | wx.RIGHT, 8)
        self.reveal_api_key = wx.Button(panel, label="Reveal")
        self.reveal_api_key.SetName("Reveal API key")
        self.api_key_row.Add(self.reveal_api_key, 0)
        panel_sizer.Add(self.api_key_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        # Plain-language reassurance instead of storage jargon on the field
        # label itself (#122), so a screen reader does not read implementation
        # detail every time the key field gets focus.
        self.api_key_hint = wx.StaticText(panel, label=provider_api_key_storage_hint())
        panel_sizer.Add(self.api_key_hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.verify_button = wx.Button(panel, label="Verify Connection")
        self.list_models_button = wx.Button(panel, label="List Models")
        self.recommend_button = wx.Button(panel, label="Recommend Model")
        self.test_chat_button = wx.Button(panel, label="Test Chat")
        self.forget_key_button = wx.Button(panel, label="Forget this provider's key")
        actions.Add(self.verify_button, 0, wx.RIGHT, 8)
        actions.Add(self.list_models_button, 0, wx.RIGHT, 8)
        actions.Add(self.recommend_button, 0, wx.RIGHT, 8)
        actions.Add(self.test_chat_button, 0, wx.RIGHT, 8)
        actions.Add(self.forget_key_button, 0, wx.RIGHT, 8)
        self.model_settings_button: object | None = None
        if self._open_model_settings is not None:
            self.model_settings_button = wx.Button(panel, label="On-device model...")
            actions.Add(self.model_settings_button, 0)
        # Vision prompt library: "Image Prompt Styles…" button
        self.vision_prompt_styles_button = wx.Button(panel, label="Image Prompt Styles…")
        self.vision_prompt_styles_button.SetName("Image Prompt Styles")
        self.vision_prompt_styles_button.Bind(wx.EVT_BUTTON, self._on_vision_prompt_styles)
        actions.Add(self.vision_prompt_styles_button, 0)
        panel_sizer.Add(actions, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.connection_status = wx.StaticText(
            panel,
            label=(
                "Tip: Verify first, then List Models and search to quickly pick the best model."
            ),
        )
        panel_sizer.Add(self.connection_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Vision prompt library settings ---
        from quill.core.settings import load_settings

        _app_settings = load_settings()

        # Picker toggle
        self.vision_picker_enabled = wx.CheckBox(
            panel, label="Show a style picker before each image description"
        )
        self.vision_picker_enabled.SetValue(
            bool(getattr(_app_settings, "vision_prompt_picker_enabled", False))
        )
        self.vision_picker_enabled.SetName("Show style picker before image description")
        panel_sizer.Add(self.vision_picker_enabled, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        # Default style dropdown
        from quill.core.ai.vision_prompts import enabled_style_choices

        _style_choices = enabled_style_choices(
            disabled_builtins=list(getattr(_app_settings, "vision_disabled_builtin_styles", [])),
            custom_prompts=list(getattr(_app_settings, "vision_custom_prompts", [])),
        )
        _style_labels = [c["title"] for c in _style_choices]
        _style_ids = [c["id"] for c in _style_choices]
        _current_default = getattr(_app_settings, "vision_default_prompt_style", "accessibility")
        _default_index = 0
        try:
            _default_index = _style_ids.index(_current_default)
        except ValueError:
            pass

        default_style_sizer = wx.BoxSizer(wx.HORIZONTAL)
        default_style_sizer.Add(
            wx.StaticText(panel, label="Default description style:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            8,
        )
        self.vision_default_style = wx.Choice(panel, choices=_style_labels)
        self.vision_default_style.SetName("Default image description style")
        if _style_labels:
            self.vision_default_style.SetSelection(_default_index)
        default_style_sizer.Add(self.vision_default_style, 1, wx.EXPAND)
        panel_sizer.Add(default_style_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Store the style ID list for saving
        self._vision_style_ids = _style_ids

        panel.SetSizer(panel_sizer)
        root.Add(panel, 1, wx.EXPAND | wx.ALL, 8)

        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.provider.Bind(wx.EVT_CHOICE, self._on_provider_changed)
        self.verify_button.Bind(wx.EVT_BUTTON, self._on_verify_connection)
        self.list_models_button.Bind(wx.EVT_BUTTON, self._on_list_models)
        self.recommend_button.Bind(wx.EVT_BUTTON, self._on_recommend_model)
        self.test_chat_button.Bind(wx.EVT_BUTTON, self._on_test_chat)
        self.forget_key_button.Bind(wx.EVT_BUTTON, self._on_forget_provider_key)
        if self.model_settings_button is not None:
            self.model_settings_button.Bind(wx.EVT_BUTTON, self._on_open_model_settings)
        self.reveal_api_key.Bind(wx.EVT_BUTTON, self._on_toggle_api_key_reveal)
        self._per_provider_models: dict[str, str] = {}
        self._current_provider = self._provider_value()
        self._on_provider_changed(None)

    def _provider_choice_index(self, provider: str) -> int:
        normalized = provider.strip().lower()
        for index, (value, _label) in enumerate(self._PROVIDER_CHOICES):
            if value == normalized:
                return index
        return 1

    def _provider_value(self) -> str:
        selection = self.provider.GetSelection()
        if selection < 0 or selection >= len(self._PROVIDER_CHOICES):
            return "ollama"
        return self._PROVIDER_CHOICES[selection][0]

    def _current_settings(self) -> AssistantConnectionSettings:
        provider = self._provider_value()
        fallback_host = default_host_for_provider(provider)
        fallback_model = default_model_for_provider(provider)
        return AssistantConnectionSettings(
            provider=provider,
            host=self.host.GetValue().strip() or fallback_host,
            model=self.model.GetValue().strip() or fallback_model,
        )

    def _model_choices_for_provider(self, provider: str) -> list[str]:
        choices: list[str] = []

        default_model = default_model_for_provider(provider).strip()
        if default_model:
            choices.append(default_model)

        for item in recommended_model_guidance(provider):
            model_name = item.model.strip()
            if model_name and model_name not in choices:
                choices.append(model_name)

        return choices

    def _set_model_choices(self, choices: list[str], preferred: str = "") -> None:
        merged: list[str] = []
        for candidate in [*choices, preferred.strip()]:
            value = candidate.strip()
            if value and value not in merged:
                merged.append(value)

        self.model.SetItems(merged)

        if preferred.strip():
            self.model.SetValue(preferred.strip())
        elif merged:
            self.model.SetValue(merged[0])
        else:
            self.model.SetValue("")

    def _on_provider_changed(self, event: object | None) -> None:
        provider = self._provider_value()
        if event is not None:
            self._per_provider_models[self._current_provider] = self.model.GetValue().strip()
            self._current_provider = provider
            # Each provider keeps its own saved model and key, so switching never
            # loses another provider's configuration.
            saved = self._per_provider_models.get(provider) or load_provider_model(provider)
            model_value = saved if saved else default_model_for_provider(provider)
            self.api_key.SetValue(load_provider_api_key(provider))
        else:
            model_value = self.model.GetValue().strip()
            known_models = {
                default_model_for_provider(name) for name, _label in self._PROVIDER_CHOICES
            }
            fallback_model = default_model_for_provider(provider)
            if not model_value or model_value in known_models:
                model_value = fallback_model
        host_value = self.host.GetValue().strip()
        known_hosts = {
            default_host_for_provider(name)
            for name, _label in self._PROVIDER_CHOICES
            if default_host_for_provider(name)
        }
        if not host_value or host_value in known_hosts:
            self.host.SetValue(default_host_for_provider(provider))
        self._set_model_choices(self._model_choices_for_provider(provider), preferred=model_value)
        requires_key = provider_requires_api_key(provider)
        self.api_key_label.SetLabel(provider_api_key_label(provider))
        self.provider_hint.SetLabel(provider_help_text(provider))
        self.api_key.Enable(requires_key)
        self.reveal_api_key.Enable(requires_key)
        if not requires_key and self._api_key_revealed:
            self._set_api_key_revealed(False)
        self.dialog.Layout()
        if event is not None:
            self.model.SetFocus()

    def _on_toggle_api_key_reveal(self, _event: object) -> None:
        self._set_api_key_revealed(not self._api_key_revealed)

    def _set_api_key_revealed(self, revealed: bool) -> None:
        value = self.api_key.GetValue()
        parent = self.api_key.GetParent()
        self.api_key_row.Detach(self.api_key)
        self.api_key.Destroy()
        style = 0 if revealed else self._wx.TE_PASSWORD
        self.api_key = self._wx.TextCtrl(parent, style=style)
        self.api_key.SetValue(value)
        self.api_key.SetName("API key")
        self.api_key_row.Insert(0, self.api_key, 1, self._wx.EXPAND | self._wx.RIGHT, 8)
        self._api_key_revealed = revealed
        self.reveal_api_key.SetLabel("Hide" if revealed else "Reveal")
        self.reveal_api_key.SetName("Hide API key" if revealed else "Reveal API key")
        self.dialog.Layout()

    def _on_verify_connection(self, _event: object) -> None:
        # Run the network check on a worker thread so a slow or unresponsive
        # endpoint cannot freeze the UI thread (and with it the screen reader)
        # while verification is in flight (#127).
        settings = self._current_settings()
        api_key = self.api_key.GetValue()
        self.verify_button.Enable(False)
        self.connection_status.SetLabel("Verifying connection...")

        def worker() -> None:
            try:
                ok, message = verify_assistant_connection(settings, api_key)
            except Exception as exc:  # noqa: BLE001 - surface any failure as a result
                ok, message = False, f"Could not verify the connection: {exc}"
            call_after = getattr(self._wx, "CallAfter", None)
            if callable(call_after):
                call_after(self._finish_verify_connection, ok, message)
            else:  # pragma: no cover - fallback when CallAfter is unavailable
                self._finish_verify_connection(ok, message)

        threading.Thread(  # GATE-40-OK: connection probe; posts via CallAfter.
            target=worker, daemon=True
        ).start()

    def _finish_verify_connection(self, ok: bool, message: str) -> None:
        """UI-thread completion for the async verify (#127)."""
        enable = getattr(self.verify_button, "Enable", None)
        if callable(enable):
            self.verify_button.Enable(True)
        self.connection_status.SetLabel(message)
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        show_message_box(message, "AI Connection Check", icon | self._wx.OK, self.dialog)

    def _on_list_models(self, _event: object) -> None:
        settings = self._current_settings()
        if missing_required_api_key(settings.provider, settings.host, self.api_key.GetValue()):
            message = (
                f"An API key is required for {provider_display_name(settings.provider)}. "
                "Enter your key and try again."
            )
            self.connection_status.SetLabel(message)
            show_message_box(
                message, "Model Discovery", self._wx.ICON_WARNING | self._wx.OK, self.dialog
            )
            return
        models, error = list_assistant_models(settings, self.api_key.GetValue())
        if error is not None:
            self.connection_status.SetLabel(error)
            show_message_box(
                error, "Model Discovery", self._wx.ICON_WARNING | self._wx.OK, self.dialog
            )
            return
        if not models:
            message = "Connection succeeded, but the endpoint returned no models."
            self.connection_status.SetLabel(message)
            show_message_box(
                message, "Model Discovery", self._wx.ICON_INFORMATION | self._wx.OK, self.dialog
            )
            return

        picker = SearchableModelPickerDialog(self.dialog, models)
        selected = picker.show_modal_and_get_selection()
        if selected:
            self._set_model_choices(
                self._model_choices_for_provider(settings.provider) + list(models),
                preferred=selected,
            )
            self.connection_status.SetLabel(f"Selected model: {selected}")
        else:
            self.connection_status.SetLabel("Model selection cancelled.")

    def _on_recommend_model(self, _event: object) -> None:
        settings = self._current_settings()
        recommendations = recommended_model_guidance(settings.provider)
        if not recommendations:
            self.connection_status.SetLabel("No model recommendations available.")
            return
        labels = [f"{item.model} - {item.framing}: {item.reason}" for item in recommendations]
        picker = self._wx.SingleChoiceDialog(
            self.dialog,
            "Choose a recommended model profile:",
            "Model Recommendations",
            labels,
        )
        apply_modal_ids(
            picker,
            affirmative_id=self._wx.ID_OK,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            if show_modal_dialog(picker, "Model Recommendations") != self._wx.ID_OK:
                self.connection_status.SetLabel("Recommendation selection cancelled.")
                return
            selected_index = picker.GetSelection()
        finally:
            picker.Destroy()
        if selected_index < 0 or selected_index >= len(recommendations):
            self.connection_status.SetLabel("Recommendation selection cancelled.")
            return
        selected: ModelRecommendation = recommendations[selected_index]
        self.model.SetValue(selected.model)
        self.connection_status.SetLabel(
            f"Recommended model selected: {selected.model} ({selected.framing})"
        )

    def _on_test_chat(self, _event: object) -> None:
        # A quick round-trip to confirm the selected provider/model actually
        # answers — run off the UI thread so a slow endpoint never freezes the
        # screen reader (#127 pattern).
        settings = self._current_settings()
        api_key = self.api_key.GetValue()
        self.test_chat_button.Enable(False)
        self.connection_status.SetLabel("Testing chat...")

        def worker() -> None:
            try:
                ok, message = test_chat(settings, api_key)
            except Exception as exc:  # noqa: BLE001 - surface any failure as a result
                ok, message = False, f"Could not test chat: {exc}"
            call_after = getattr(self._wx, "CallAfter", None)
            if callable(call_after):
                call_after(self._finish_test_chat, ok, message)
            else:  # pragma: no cover - fallback when CallAfter is unavailable
                self._finish_test_chat(ok, message)

        threading.Thread(  # GATE-40-OK: chat probe; posts via CallAfter.
            target=worker, daemon=True
        ).start()

    def _finish_test_chat(self, ok: bool, message: str) -> None:
        enable = getattr(self.test_chat_button, "Enable", None)
        if callable(enable):
            self.test_chat_button.Enable(True)
        self.connection_status.SetLabel(message)
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        self._wx.MessageBox(message, "Test Chat", icon | self._wx.OK)  # MSGBOX-OK: standalone

    def _on_forget_provider_key(self, _event: object) -> None:
        provider = self._provider_value()
        clear_provider_api_key(provider)
        self.api_key.SetValue("")
        self.connection_status.SetLabel(
            f"Forgot the saved key for {provider_display_name(provider)}."
        )

    def _on_open_model_settings(self, _event: object) -> None:
        if callable(self._open_model_settings):
            self._open_model_settings()

    def _on_vision_prompt_styles(self, _event: object) -> None:
        """Open the Manage Image Prompts dialog, then refresh the style dropdown."""
        from quill.core.settings import load_settings
        from quill.ui.vision_prompt_manager_dialog import VisionPromptManagerDialog

        settings = load_settings()
        dlg = VisionPromptManagerDialog(self.dialog, settings)
        dlg.show_modal()
        self._refresh_vision_style_dropdown()

    def _refresh_vision_style_dropdown(self) -> None:
        """Rebuild the default-style Choice control from the current saved settings.

        Called after the Manage Image Prompts dialog closes so that any newly
        added, removed, or disabled styles are reflected immediately without
        requiring the AI Hub to be closed and reopened.
        """
        from quill.core.ai.vision_prompts import enabled_style_choices
        from quill.core.settings import load_settings

        app_settings = load_settings()
        style_choices = enabled_style_choices(
            disabled_builtins=list(app_settings.vision_disabled_builtin_styles),
            custom_prompts=list(app_settings.vision_custom_prompts),
        )
        style_labels = [c["title"] for c in style_choices]
        style_ids = [c["id"] for c in style_choices]
        current_default = app_settings.vision_default_prompt_style
        default_index = 0
        try:
            default_index = style_ids.index(current_default)
        except ValueError:
            pass

        self.vision_default_style.Clear()
        for label in style_labels:
            self.vision_default_style.Append(label)
        if style_labels:
            self.vision_default_style.SetSelection(default_index)
        self._vision_style_ids = style_ids

    def show_modal(self) -> bool:
        self.dialog.CentreOnParent()
        try:
            if show_modal_dialog(self.dialog, "AI Connection Settings") != self._wx.ID_OK:
                return False
            settings = self._current_settings()
            api_key = self.api_key.GetValue()
            # Persist per-provider (key + default model) and make it active so the
            # generation path uses it immediately.
            set_active_provider(settings, api_key)
            ok, message = verify_assistant_connection(settings, api_key)
            self.last_verification_ok = ok
            self.last_verification_message = message
            self.connection_status.SetLabel(message)

            # Save vision prompt library settings
            from quill.core.settings import load_settings, save_settings

            app_settings = load_settings()
            app_settings.vision_prompt_picker_enabled = bool(self.vision_picker_enabled.GetValue())
            style_sel = self.vision_default_style.GetSelection()
            if 0 <= style_sel < len(self._vision_style_ids):
                app_settings.vision_default_prompt_style = self._vision_style_ids[style_sel]
            save_settings(app_settings)

            return True
        finally:
            self.dialog.Destroy()
