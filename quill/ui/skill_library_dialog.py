"""Skill Library dialog: browse, import, and run .sqp multi-step AI workflows.

Entry point: open_skill_library() in MainFrame (Tools > AI Assistant > Skill Library...).
A11Y-4 hardened: apply_modal_ids, public show()/close().
Status changes are announced via announce_cb (finding #43).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import wx

from quill.core.skill_pack import (
    SkillPack,
    SkillParameter,
    SkillValidationError,
    StepResult,
    parse_skill,
    run_skill,
    validate_skill,
)
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

if TYPE_CHECKING:
    from quill.core.settings import Settings


class _SkillCancelled(Exception):
    pass


class SkillLibraryDialog:
    """Browse installed skills and run them against the current selection."""

    def __init__(
        self,
        parent: object,
        skill_files: list[Path],
        settings: Settings,
        *,
        selection: str = "",
        document: str = "",
        title_text: str = "",
        clipboard: str = "",
        on_insert: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._settings = settings
        self._skill_files = list(skill_files)
        self._packs: dict[str, SkillPack] = {}
        self._context: dict[str, str] = {
            "selection": selection,
            "document": document,
            "title": title_text,
            "clipboard": clipboard,
        }
        self._on_insert = on_insert
        self._announce = announce_cb or (lambda _: None)
        self._running = False
        self._cancel_event = threading.Event()

        self.dialog = wx.Dialog(
            parent,
            title="Skill Library",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(540, 440))

        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Skills:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._list.SetMinSize(wx.Size(-1, 180))
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        root.Add(wx.StaticText(self.dialog, label="&Description:"), 0, wx.LEFT | wx.TOP, 8)
        self._desc = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._desc.SetMinSize(wx.Size(-1, 70))
        root.Add(self._desc, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        self._status = wx.StaticText(self.dialog, label="")
        root.Add(self._status, 0, wx.LEFT | wx.TOP, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._run_btn = wx.Button(self.dialog, label="&Run")
        self._run_btn.Disable()
        self._import_btn = wx.Button(self.dialog, label="&Import .sqp...")
        close_btn = wx.Button(self.dialog, id=wx.ID_CLOSE, label="C&lose")
        btns.Add(self._run_btn, 0, wx.RIGHT, 6)
        btns.Add(self._import_btn, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(close_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog)

        self._list.Bind(wx.EVT_LISTBOX, self._on_select)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_run_or_cancel)
        self._run_btn.Bind(wx.EVT_BUTTON, self._on_run_or_cancel)
        self._import_btn.Bind(wx.EVT_BUTTON, self._on_import)
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.close())
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.close())

        self._populate()
        self._check_ai_configured()

    # ------------------------------------------------------------------
    # Populate + configuration check
    # ------------------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self._status.SetLabel(msg)
        if msg:
            self._announce(msg)

    def _populate(self) -> None:
        self._packs.clear()
        self._list.Clear()
        for path in self._skill_files:
            try:
                pack = parse_skill(path.read_text(encoding="utf-8"))
                self._packs[pack.name] = pack
                self._list.Append(pack.name)
            except Exception:
                pass
        if self._list.GetCount():
            self._list.SetSelection(0)
            self._on_select(None)

    def _check_ai_configured(self) -> None:
        model_id = (
            getattr(self._settings, "ai_prompt_default_model", "")
            or self._settings.ai_chat_default_model
            or ""
        )
        if not model_id:
            self._set_status(
                "No AI model configured. Open Preferences > AI to set a provider and model."
            )

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_select(self, _event: object) -> None:
        idx = self._list.GetSelection()
        self._run_btn.Enable(idx != wx.NOT_FOUND and not self._running)
        if idx == wx.NOT_FOUND:
            self._desc.SetValue("")
            return
        pack = self._packs.get(self._list.GetString(idx))
        if pack is None:
            self._desc.SetValue("")
            return
        parts = []
        if pack.description:
            parts.append(pack.description)
        step_headings = " → ".join(s.heading for s in pack.steps)
        parts.append(f"Steps: {step_headings}.")
        if pack.parameters:
            labels = ", ".join(p.label or p.name for p in pack.parameters)
            parts.append(f"Parameters: {labels}.")
        self._desc.SetValue("  ".join(parts))

    # ------------------------------------------------------------------
    # Run / Cancel
    # ------------------------------------------------------------------

    def _on_run_or_cancel(self, _event: object) -> None:
        if self._running:
            self._cancel_event.set()
            self._run_btn.Disable()
            self._set_status("Cancelling after current step completes...")
            return

        idx = self._list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        pack = self._packs.get(self._list.GetString(idx))
        if pack is None:
            return

        ctx = dict(self._context)
        if pack.parameters:
            pdlg = _SkillParameterDialog(self.dialog, pack)
            if pdlg.show() != wx.ID_OK:
                return
            ctx.update(pdlg.get_values())

        self._start_run(pack, ctx)

    def _start_run(self, pack: SkillPack, ctx: dict[str, str]) -> None:
        from quill.core.ai_chat import send_prompt
        from quill.platform.windows.credential_store import load_secret

        provider_id = self._settings.ai_chat_default_provider or "openrouter"
        model_id = (
            getattr(self._settings, "ai_prompt_default_model", "")
            or self._settings.ai_chat_default_model
            or ""
        )
        if not model_id:
            show_message_box(
                "No AI model configured. Set a default model in Preferences > AI.",
                "No Model",
                wx.OK | wx.ICON_INFORMATION,
                self.dialog,
                announce=self._announce,
            )
            return

        api_key = load_secret(f"quill-{provider_id}-api-key")
        ollama_url = getattr(self._settings, "ollama_base_url", "") or "http://localhost:11434"
        base_url = ollama_url if provider_id.startswith("ollama") else ""

        total = len(pack.steps)
        self._cancel_event.clear()
        self._running = True
        self._run_btn.SetLabel("&Cancel")

        def _update_step_status(msg: str) -> None:
            self._set_status(msg)
            self.dialog.Layout()

        def worker() -> None:
            step_n = [0]

            def send_fn(prompt: str) -> str:
                n = step_n[0] + 1
                step_n[0] = n
                heading = pack.steps[n - 1].heading if n <= len(pack.steps) else ""
                status = f"Running step {n} of {total}"
                if heading:
                    status += f": {heading}"
                wx.CallAfter(_update_step_status, status + "...")
                if self._cancel_event.is_set():
                    raise _SkillCancelled()
                return send_prompt(
                    provider_id, model_id, prompt, api_key=api_key, base_url=base_url
                )

            try:
                results = run_skill(pack, ctx, send_fn)
                wx.CallAfter(self._on_done, pack, results)
            except _SkillCancelled:
                wx.CallAfter(self._on_cancelled)
            except Exception as exc:
                wx.CallAfter(self._on_error, str(exc))

        threading.Thread(  # GATE-40-OK: skill pack worker; bounded by steps.
            target=worker, daemon=True
        ).start()

    def _reset_run_button(self) -> None:
        self._running = False
        self._run_btn.SetLabel("&Run")
        self._run_btn.Enable(self._list.GetSelection() != wx.NOT_FOUND)

    def _on_done(self, pack: SkillPack, results: list[StepResult]) -> None:
        self._reset_run_button()

        active = [r for r in results if not r.skipped]
        if not active:
            self._set_status("")
            show_message_box(
                "The skill ran but produced no output.",
                "Skill result",
                wx.OK | wx.ICON_INFORMATION,
                self.dialog,
                announce=self._announce,
            )
            return

        self._set_status("")

        last_step = pack.steps[-1]
        accept_into = "none"
        label = f"Result: {pack.name}"
        if last_step.output:
            accept_into = last_step.output.accept_into or "none"
            if last_step.output.label:
                label = last_step.output.label

        on_accept: Callable[[str], None] | None = None
        if accept_into == "selection" and self._on_insert is not None:
            on_accept = self._on_insert
        elif accept_into == "clipboard":

            def on_accept(text: str) -> None:
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                    wx.TheClipboard.Close()

        rdlg = _SkillResultDialog(
            self.dialog,
            active,
            label,
            accept_into=accept_into,
            on_accept=on_accept,
        )
        rdlg.show()
        rdlg.dialog.Destroy()

    def _on_cancelled(self) -> None:
        self._reset_run_button()
        self._set_status("Skill cancelled.")

    def _on_error(self, msg: str) -> None:
        self._reset_run_button()
        self._status.SetLabel("")
        show_message_box(
            f"The skill failed:\n\n{msg}",
            "Skill error",
            wx.OK | wx.ICON_ERROR,
            self.dialog,
            announce=self._announce,
        )

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def _on_import(self, _event: object) -> None:
        dlg = wx.FileDialog(
            self.dialog,
            message="Import Skill Quill Pack",
            wildcard="Skill Quill Pack (*.sqp)|*.sqp",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dlg.ShowModal() != wx.ID_OK:
            return
        path = Path(dlg.GetPath())
        try:
            source = path.read_text(encoding="utf-8")
            pack = parse_skill(source)
            errors = validate_skill(pack)
        except SkillValidationError as exc:
            show_message_box(
                "Parse errors:\n\n" + "\n".join(exc.errors),
                "Invalid skill",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
                announce=self._announce,
            )
            return
        except Exception as exc:
            show_message_box(
                str(exc),
                "Import failed",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
                announce=self._announce,
            )
            return
        if errors:
            show_message_box(
                "Validation errors:\n\n" + "\n".join(errors),
                "Invalid skill",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
                announce=self._announce,
            )
            return
        self._skill_files.append(path)
        self._packs[pack.name] = pack
        if self._list.FindString(pack.name) == wx.NOT_FOUND:
            self._list.Append(pack.name)
        self._list.SetStringSelection(pack.name)
        self._on_select(None)
        show_message_box(
            f"Imported: {pack.name}",
            "Skill imported",
            wx.OK | wx.ICON_INFORMATION,
            self.dialog,
            announce=self._announce,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def show(self) -> None:
        self.dialog.CenterOnParent()
        self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CLOSE)


class _SkillParameterDialog:
    """Collect parameter values before running a skill."""

    def __init__(self, parent: object, pack: SkillPack) -> None:
        self._pack = pack
        self._controls: dict[str, wx.Window] = {}

        self.dialog = wx.Dialog(
            parent,
            title=f"Options — {pack.name}",
            style=wx.DEFAULT_DIALOG_STYLE,
        )
        self.dialog.SetMinSize(wx.Size(380, -1))

        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, hgap=8, vgap=8)
        grid.AddGrowableCol(1)

        for param in pack.parameters:
            grid.Add(
                wx.StaticText(self.dialog, label=(param.label or param.name) + ":"),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            ctrl = self._make_control(param)
            self._controls[param.name] = ctrl
            grid.Add(ctrl, 0, wx.EXPAND)

        btn_sizer = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        root.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        root.Add(btn_sizer, 0, wx.EXPAND | wx.BOTTOM | wx.RIGHT, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog)

    def _make_control(self, param: SkillParameter) -> wx.Window:
        default = str(param.default or "")
        if param.type == "choice" and param.choices:
            choices = list(param.choices)
            ctrl: wx.Window = wx.Choice(self.dialog, choices=choices)
            sel = choices.index(default) if default in choices else 0
            ctrl.SetSelection(sel)  # type: ignore[attr-defined]
        elif param.type == "bool":
            ctrl = wx.CheckBox(self.dialog)
            ctrl.SetValue(default.lower() in ("true", "yes", "1"))  # type: ignore[attr-defined]
        elif param.type == "number":
            ctrl = wx.SpinCtrl(self.dialog, value=default or "0", min=0, max=999999)
        elif param.type == "multiline":
            ctrl = wx.TextCtrl(self.dialog, value=default, style=wx.TE_MULTILINE)
            ctrl.SetMinSize(wx.Size(-1, 80))
        else:
            ctrl = wx.TextCtrl(self.dialog, value=default)
        return ctrl

    def show(self) -> int:
        return self.dialog.ShowModal()

    def get_values(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for param in self._pack.parameters:
            ctrl = self._controls.get(param.name)
            if ctrl is None:
                continue
            if isinstance(ctrl, wx.Choice):
                val = ctrl.GetString(ctrl.GetSelection())
            elif isinstance(ctrl, wx.CheckBox):
                val = "true" if ctrl.GetValue() else "false"
            elif isinstance(ctrl, wx.SpinCtrl):
                val = str(ctrl.GetValue())
            else:
                val = ctrl.GetValue()  # type: ignore[attr-defined]
            result[f"parameters.{param.name}"] = val
        return result


class _SkillResultDialog:
    """Show skill output — all step outputs for transparency, Accept and Copy buttons."""

    def __init__(
        self,
        parent: object,
        results: list[StepResult],
        label: str,
        *,
        accept_into: str = "none",
        on_accept: Callable[[str], None] | None = None,
    ) -> None:
        final = results[-1] if results else None
        self._accept_text = final.output_text if final else ""
        self._on_accept = on_accept

        # Build display text: all steps separated by headings when more than one.
        if len(results) > 1:
            sections = [f"--- {r.step_heading} ---\n{r.output_text}" for r in results]
            display_text = "\n\n".join(sections)
        else:
            display_text = self._accept_text

        self.dialog = wx.Dialog(
            parent,
            title=label,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 460))

        root = wx.BoxSizer(wx.VERTICAL)

        if len(results) > 1:
            note = wx.StaticText(
                self.dialog,
                label=f"All {len(results)} steps shown. Accept inserts the final step only.",
            )
            root.Add(note, 0, wx.LEFT | wx.TOP | wx.RIGHT, 8)

        ctrl = wx.TextCtrl(
            self.dialog,
            value=display_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        ctrl.SetName(label)
        root.Add(ctrl, 1, wx.EXPAND | wx.ALL, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        if accept_into != "none" and on_accept is not None:
            accept_label = (
                "&Accept (insert into document)"
                if accept_into == "selection"
                else "&Accept (copy to clipboard)"
            )
            accept_btn = wx.Button(self.dialog, label=accept_label)
            accept_btn.Bind(wx.EVT_BUTTON, self._on_do_accept)
            btns.Add(accept_btn, 0, wx.RIGHT, 6)

        copy_btn = wx.Button(self.dialog, label="&Copy to Clipboard")
        close_btn = wx.Button(self.dialog, id=wx.ID_CLOSE, label="C&lose")
        btns.Add(copy_btn, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(close_btn)
        root.Add(btns, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog)

        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        ctrl.SetFocus()

    def show(self) -> int:
        return self.dialog.ShowModal()

    def _on_do_accept(self, _event: object) -> None:
        if self._on_accept:
            self._on_accept(self._accept_text)
        self.dialog.EndModal(wx.ID_OK)

    def _on_copy(self, _event: object) -> None:
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self._accept_text))
            wx.TheClipboard.Close()
