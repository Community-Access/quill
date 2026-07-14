"""Unified AI Library dialog — one manager for Prompts, Skills, and Agents.

The AI Library is the single place to manage the Prompt/Skill/Agent continuum
(the four-pillar AI redesign). Three notebook tabs present the three kinds of
saved AI intent with one uniform shape (:class:`~quill.core.ai.library.LibraryItem`)
and one verb set:

* **Prompts** — Run, New, Edit, Enable/Disable, Delete, Import/Export ``.pqp``,
  Promote to Skill.
* **Skills** — Run, Import/Export ``.sqp``, Enable/Disable, Remove, Promote to Agent.
* **Agents** — Run (through the reviewed gateway), Validate. Catalog agents are
  read-only built-ins, so they are the top of the continuum.

The **Promote continuum** is real: a Prompt graduates into an installed Skill, and
a Skill graduates into an Agent scaffold the user can save. The pure source
transforms live in :mod:`quill.core.ai.library`; this dialog persists or displays
the result.

Prompt and skill running go through the same provider the rest of QUILL's AI uses —
the AI Hub connection via :class:`ProviderChatBackend` — so setting up AI once (the
AI Setup Wizard or the Hub) makes the Library work too. When AI isn't ready, the run
offers the setup on-ramp (``on_setup_ai``). Agent running is delegated to the host via
``on_run_agent`` because it needs the full controller and the Safe Editor Tool Gateway.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import wx

from quill.core.ai import library
from quill.core.ai.library import LibraryItem
from quill.core.prompt_library import PromptLibrary
from quill.core.skill_store import SkillStore
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    show_message_box,
)
from quill.ui.prompt_library_dialog import _PromptEditDialog
from quill.ui.skill_library_dialog import (
    _SkillCancelled,
    _SkillParameterDialog,
    _SkillResultDialog,
)

if TYPE_CHECKING:
    from quill.core.settings import Settings


def skill_store_for(controller: Any) -> SkillStore:
    """The host's installed-skills store, created and cached on first use."""
    cache = getattr(controller, "_skill_store_cache", None)
    if cache is None:
        from quill.core.paths import app_data_dir

        cache = SkillStore(app_data_dir() / "skills")
        controller._skill_store_cache = cache
    return cache


def open_ai_library(controller: Any) -> None:
    """Open the unified AI Library for the host MainFrame (keeps main_frame thin)."""
    from quill.ui.agent_editor_host import _catalog_agents, run_agent

    dlg = AILibraryDialog(
        controller.frame,
        prompt_library=controller._get_prompt_library(),
        skill_store=skill_store_for(controller),
        agents=_catalog_agents(),
        settings=controller.settings,
        selection=str(controller.editor.GetStringSelection()),
        document=str(controller.editor.GetValue()),
        title=controller._current_document_title(),
        on_run_agent=lambda agent_id: run_agent(controller, agent_id),
        on_validate_agents=controller.open_agent_validator,
        on_setup_ai=lambda: _offer_ai_setup(controller),
        on_insert=controller._ai_insert_text,
        announce_cb=controller._announce,
    )
    controller._show_modal_dialog(dlg.dialog, "AI Library")
    dlg.close()


def _offer_ai_setup(controller: Any) -> bool:
    from quill.ui.ai_setup_wizard import maybe_offer_ai_setup

    return maybe_offer_ai_setup(controller, reason="To run this on your document, QUILL needs AI.")


class AILibraryDialog:
    """Manage Prompts, Skills, and Agents in one tabbed surface."""

    def __init__(
        self,
        parent: object,
        *,
        prompt_library: PromptLibrary,
        skill_store: SkillStore,
        agents: list[Any],
        settings: Settings,
        selection: str = "",
        document: str = "",
        title: str = "",
        on_run_agent: Callable[[str], None] | None = None,
        on_validate_agents: Callable[[], None] | None = None,
        on_setup_ai: Callable[[], bool] | None = None,
        on_insert: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._lib = prompt_library
        self._skills = skill_store
        self._agents = agents
        self._settings = settings
        self._context = {"selection": selection, "document": document, "title": title}
        self._on_run_agent = on_run_agent
        self._on_validate_agents = on_validate_agents
        self._on_setup_ai = on_setup_ai
        self._on_insert = on_insert
        self._announce = announce_cb or (lambda _: None)
        self._running = False
        self._cancel = threading.Event()

        self.dialog = wx.Dialog(
            parent,
            title="AI Library",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(760, 520))

        root = wx.BoxSizer(wx.VERTICAL)
        self._notebook = wx.Notebook(self.dialog)
        self._notebook.SetName("AI Library tabs")

        self._prompt_page = _LibraryPage(self, self._notebook, "prompt")
        self._skill_page = _LibraryPage(self, self._notebook, "skill")
        self._agent_page = _LibraryPage(self, self._notebook, "agent")
        self._notebook.AddPage(self._prompt_page.panel, "&Prompts")
        self._notebook.AddPage(self._skill_page.panel, "S&kills")
        self._notebook.AddPage(self._agent_page.panel, "&Agents")
        root.Add(self._notebook, 1, wx.EXPAND | wx.ALL, 8)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("AI Library status")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        btns.AddStretchSpacer(1)
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="C&lose")
        btns.Add(close_btn, 0)
        root.Add(btns, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
        )

        self.reload()
        self._check_ai_configured()

    # -- lifecycle ------------------------------------------------------------

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    # -- shared services ------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self._status.SetLabel(msg)
        if msg:
            self._announce(msg)

    def _check_ai_configured(self) -> None:
        ok, _reason = self._ai_ready()
        if not ok:
            self._set_status("No AI set up yet. Use 'Set Up AI' in the AI menu, or the AI Hub.")

    def _backend(self) -> Any:
        from quill.core.ai.provider_backend import ProviderChatBackend

        return ProviderChatBackend()

    def _ai_ready(self) -> tuple[bool, str]:
        try:
            ok, reason = self._backend().is_available()
            return ok, (reason or "")
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _ensure_ai(self) -> bool:
        """True when AI is usable. Offers the setup on-ramp once if it isn't."""
        ok, _reason = self._ai_ready()
        if ok:
            return True
        if self._on_setup_ai is not None and self._on_setup_ai():
            ok, _reason = self._ai_ready()
            if ok:
                return True
        self._check_ai_configured()
        return False

    def reload(self) -> None:
        """Rebuild every tab from its store (after a change or a promotion)."""
        self._prompt_page.set_items(library.list_prompts(self._lib))
        self._skill_page.set_items(library.list_skills(self._skills))
        self._agent_page.set_items(library.list_agents(self._agents))

    # -- item lookups ---------------------------------------------------------

    def _prompt_by_id(self, item_id: str) -> Any:
        return self._lib.find_by_id(item_id)

    def _skill_by_id(self, item_id: str) -> Any:
        return self._skills.find_by_id(item_id)

    # -- run dispatch ---------------------------------------------------------

    def run_item(self, item: LibraryItem) -> None:
        if item.kind == "prompt":
            self._run_prompt(item)
        elif item.kind == "skill":
            self._run_skill(item)
        elif item.kind == "agent":
            self._run_agent(item)

    def _run_agent(self, item: LibraryItem) -> None:
        if self._on_run_agent is None:
            self._set_status("Running agents is not available here.")
            return
        # The agent runs against the live document through the host's gateway, so
        # close the modal first and let the host drive the run.
        self.dialog.EndModal(wx.ID_CANCEL)
        self._on_run_agent(item.id)

    def _run_prompt(self, item: LibraryItem) -> None:
        if self._running:
            return
        input_text = self._context.get("selection") or self._context.get("document") or ""
        if not input_text.strip():
            show_message_box(
                "Select some text in the document before running a prompt.",
                "No Input Text",
                wx.OK | wx.ICON_INFORMATION,
                self.dialog,
                announce=self._announce,
            )
            return
        if not self._ensure_ai():
            return
        prompt_text = (
            item.detail
            .replace("{selection}", input_text)
            .replace("{document}", self._context.get("document") or input_text)
            .replace("{title}", self._context.get("title", ""))
        )
        backend = self._backend()
        self._running = True
        self._set_status(f"Sending to {backend.settings.model}...")

        model, provider = backend.settings.model, backend.settings.provider

        def run() -> None:
            try:
                result = backend.respond(prompt_text)
                wx.CallAfter(self._on_prompt_result, result, model, provider)
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(self._on_run_error, str(exc))

        threading.Thread(  # GATE-40-OK: AI Library prompt send worker.
            target=run, daemon=True
        ).start()

    def _on_prompt_result(self, result: str, model_id: str, provider_id: str) -> None:
        self._running = False
        self._set_status("")
        from quill.ui.ai_chat_dialog import AIResponseDialog

        dlg = AIResponseDialog(self.dialog, result, model_id, provider_id)
        dlg.show()
        dlg.close()

    def _on_run_error(self, message: str) -> None:
        self._running = False
        self._set_status("")
        show_message_box(
            f"AI request failed: {message}",
            "Run Failed",
            wx.OK | wx.ICON_ERROR,
            self.dialog,
            announce=self._announce,
        )

    def _run_skill(self, item: LibraryItem) -> None:
        if self._running:
            return
        from quill.core.skill_pack import parse_skill

        try:
            pack = parse_skill(item.detail)
        except Exception as exc:  # noqa: BLE001
            self._on_run_error(str(exc))
            return
        if not self._ensure_ai():
            return
        ctx = dict(self._context)
        ctx.setdefault("clipboard", "")
        if pack.parameters:
            pdlg = _SkillParameterDialog(self.dialog, pack)
            if pdlg.show() != wx.ID_OK:
                pdlg.dialog.Destroy()
                return
            ctx.update(pdlg.get_values())
            pdlg.dialog.Destroy()
        self._start_skill_run(pack, ctx)

    def _start_skill_run(self, pack: Any, ctx: dict[str, str]) -> None:
        from quill.core.skill_pack import run_skill

        backend = self._backend()
        total = len(pack.steps)
        self._cancel.clear()
        self._running = True
        self._set_status(f"Running skill: {pack.name}...")

        def worker() -> None:
            step_n = [0]

            def send_fn(prompt: str) -> str:
                n = step_n[0] + 1
                step_n[0] = n
                heading = pack.steps[n - 1].heading if n <= len(pack.steps) else ""
                status = f"Running step {n} of {total}"
                if heading:
                    status += f": {heading}"
                wx.CallAfter(self._set_status, status + "...")
                if self._cancel.is_set():
                    raise _SkillCancelled()
                return backend.respond(prompt)

            try:
                results = run_skill(pack, ctx, send_fn)
                wx.CallAfter(self._on_skill_done, pack, results)
            except _SkillCancelled:
                wx.CallAfter(self._on_skill_cancelled)
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(self._on_run_error, str(exc))

        threading.Thread(  # GATE-40-OK: AI Library skill worker; bounded by steps.
            target=worker, daemon=True
        ).start()

    def _on_skill_done(self, pack: Any, results: list[Any]) -> None:
        self._running = False
        self._set_status("")
        active = [r for r in results if not r.skipped]
        if not active:
            show_message_box(
                "The skill ran but produced no output.",
                "Skill Result",
                wx.OK | wx.ICON_INFORMATION,
                self.dialog,
                announce=self._announce,
            )
            return
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
            self.dialog, active, label, accept_into=accept_into, on_accept=on_accept
        )
        rdlg.show()
        rdlg.dialog.Destroy()

    def _on_skill_cancelled(self) -> None:
        self._running = False
        self._set_status("Skill cancelled.")

    # -- prompt verbs ---------------------------------------------------------

    def prompt_new(self) -> None:
        dlg = _PromptEditDialog(self.dialog)
        if dlg.show() == wx.ID_OK:
            name, text, category = dlg.get_values()
            if name and text:
                self._lib.add(name, text, category)
                self.reload()
                self._set_status(f"Added prompt: {name}")
        dlg.close()

    def prompt_edit(self, item: LibraryItem) -> None:
        prompt = self._prompt_by_id(item.id)
        if prompt is None:
            return
        dlg = _PromptEditDialog(self.dialog, prompt)
        if dlg.show() == wx.ID_OK:
            name, text, category = dlg.get_values()
            if name and text:
                self._lib.update(prompt.id, name=name, text=text, category=category)
                self.reload()
        dlg.close()

    def prompt_toggle(self, item: LibraryItem) -> None:
        if item.enabled:
            self._lib.disable(item.id)
        else:
            self._lib.enable(item.id)
        self.reload()

    def prompt_delete(self, item: LibraryItem) -> None:
        if item.is_builtin:
            return
        if not self._confirm(f"Delete the prompt '{item.name}'? This cannot be undone."):
            return
        self._lib.remove(item.id)
        self.reload()
        self._set_status(f"Deleted prompt: {item.name}")

    def prompt_import(self) -> None:
        path = self._ask_open("Import Prompt Pack", "QUILL Prompt Pack (*.pqp)|*.pqp")
        if path is None:
            return
        try:
            added = self._lib.import_pqp(path)
        except Exception as exc:  # noqa: BLE001
            self._error(f"Import failed: {exc}")
            return
        self.reload()
        self._set_status(
            f"Imported {len(added)} prompt(s)." if added else "No new prompts to import."
        )

    def prompt_export(self) -> None:
        path = self._ask_save(
            "Export Prompt Pack", "my-prompts.pqp", "QUILL Prompt Pack (*.pqp)|*.pqp"
        )
        if path is None:
            return
        try:
            count = self._lib.export_pqp(path)
        except Exception as exc:  # noqa: BLE001
            self._error(f"Export failed: {exc}")
            return
        self._set_status(f"Exported {count} prompt(s).")

    # -- skill verbs ----------------------------------------------------------

    def skill_import(self) -> None:
        path = self._ask_open("Import Skill Pack", "Skill Quill Pack (*.sqp)|*.sqp")
        if path is None:
            return
        try:
            skill = self._skills.import_sqp(path)
        except Exception as exc:  # noqa: BLE001
            self._error(f"Import failed: {exc}")
            return
        self.reload()
        self._set_status(f"Imported skill: {skill.name}")

    def skill_build(self) -> None:
        """Open the guided Action Builder; on save, install and reveal the new skill."""
        from quill.ui.action_builder_dialog import ActionBuilderDialog

        builder = ActionBuilderDialog(self.dialog, self._skills, announce_cb=self._announce)
        if builder.show() == wx.ID_OK and builder.get_saved() is not None:
            saved = builder.get_saved()
            self.reload()
            self._skill_page.select_by_id(saved.id)
            self._set_status(f"Built action: {saved.name}")
        builder.close()

    def skill_export(self, item: LibraryItem) -> None:
        path = self._ask_save(
            "Export Skill Pack", f"{item.id}.sqp", "Skill Quill Pack (*.sqp)|*.sqp"
        )
        if path is None:
            return
        try:
            self._skills.export_sqp(item.id, path)
        except Exception as exc:  # noqa: BLE001
            self._error(f"Export failed: {exc}")
            return
        self._set_status(f"Exported skill: {item.name}")

    def skill_toggle(self, item: LibraryItem) -> None:
        if item.enabled:
            self._skills.disable(item.id)
        else:
            self._skills.enable(item.id)
        self.reload()

    def skill_remove(self, item: LibraryItem) -> None:
        if not self._confirm(f"Remove the skill '{item.name}'? This cannot be undone."):
            return
        try:
            self._skills.remove(item.id)
        except KeyError:
            return
        self.reload()
        self._set_status(f"Removed skill: {item.name}")

    # -- agent verbs ----------------------------------------------------------

    def agent_validate(self, item: LibraryItem) -> None:
        # Prefer the full standards linter dialog (the same one the CI gate uses)
        # when the host provides it; fall back to a quick per-spec schema check.
        if self._on_validate_agents is not None:
            self._on_validate_agents()
            return
        from quill.core.ai.agent_catalog import validate_agent

        spec = next((a for a in self._agents if a.id == item.id), None)
        if spec is None:
            self._error("Agent not found.")
            return
        data = {
            "schema": "quill.agent/1",
            "id": spec.id,
            "display_name": spec.display_name,
            "system_prompt": spec.system_prompt,
        }
        problems = validate_agent(data)
        if problems:
            self._error("Validation problems:\n\n" + "\n".join(problems))
        else:
            self._set_status(f"Agent '{item.name}' is valid.")

    # -- promote continuum ----------------------------------------------------

    def promote(self, item: LibraryItem) -> None:
        if item.kind == "prompt":
            source = library.prompt_to_skill_source(
                item.name, item.detail, description=item.description
            )
            try:
                skill = self._skills.add_source(source)
            except Exception as exc:  # noqa: BLE001
                self._error(f"Could not create skill: {exc}")
                return
            self.reload()
            self._notebook.SetSelection(1)
            self._skill_page.select_by_id(skill.id)
            self._set_status(f"Promoted prompt to skill: {skill.name}")
        elif item.kind == "skill":
            skill = self._skill_by_id(item.id)
            if skill is None:
                return
            markdown = library.skill_to_agent_markdown(skill)
            _PromotedAgentDialog(
                self.dialog,
                item.name,
                markdown,
                announce=self._announce,
                on_saved=self._on_agent_promoted,
            ).show()

    def _on_agent_promoted(self, spec: object) -> None:
        """A skill was saved as a first-class user agent: refresh + reveal it."""
        from quill.ui.agent_editor_host import _catalog_agents

        self._agents = _catalog_agents()
        self.reload()
        self._notebook.SetSelection(2)
        self._agent_page.select_by_id(getattr(spec, "id", ""))
        self._set_status(f"Promoted skill to agent: {getattr(spec, 'display_name', '')}")

    # -- small helpers --------------------------------------------------------

    def _confirm(self, message: str) -> bool:
        confirm = wx.MessageDialog(
            self.dialog, message, "Confirm", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        apply_modal_ids(  # dialog_button_contract: exempt
            confirm, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO
        )
        try:
            return confirm.ShowModal() == wx.ID_YES
        finally:
            confirm.Destroy()

    def _error(self, message: str) -> None:
        show_message_box(
            message, "AI Library", wx.OK | wx.ICON_ERROR, self.dialog, announce=self._announce
        )

    def _ask_open(self, title: str, wildcard: str) -> Path | None:
        with wx.FileDialog(
            self.dialog, title, wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as fdlg:
            if fdlg.ShowModal() != wx.ID_OK:
                return None
            return Path(fdlg.GetPath())

    def _ask_save(self, title: str, default_file: str, wildcard: str) -> Path | None:
        with wx.FileDialog(
            self.dialog,
            title,
            defaultFile=default_file,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fdlg:
            if fdlg.ShowModal() != wx.ID_OK:
                return None
            return Path(fdlg.GetPath())


# Buttons available per kind, in display order. Each entry is (label, method).
_VERBS: dict[str, list[tuple[str, str]]] = {
    "prompt": [
        ("&Run with AI", "run"),
        ("&New", "new"),
        ("&Edit", "edit"),
        ("Disa&ble", "toggle"),
        ("&Delete", "delete"),
        ("&Import", "import"),
        ("E&xport", "export"),
        ("Pro&mote to Skill", "promote"),
    ],
    "skill": [
        ("&Run", "run"),
        ("&Build Action...", "build"),
        ("&Import", "import"),
        ("E&xport", "export"),
        ("Disa&ble", "toggle"),
        ("Re&move", "remove"),
        ("Pro&mote to Agent", "promote"),
    ],
    "agent": [
        ("&Run", "run"),
        ("&Validate", "validate"),
    ],
}


class _LibraryPage:
    """One notebook tab: searchable list + preview + kind-specific verb buttons."""

    def __init__(self, owner: AILibraryDialog, notebook: wx.Notebook, kind: str) -> None:
        self._owner = owner
        self._kind = kind
        self._items: list[LibraryItem] = []
        self.panel = wx.Panel(notebook)
        noun = {"prompt": "prompts", "skill": "skills", "agent": "agents"}[kind]

        root = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self.panel, label="&Search:"), 0, wx.BOTTOM, 2)
        self._search = wx.TextCtrl(self.panel)
        self._search.SetName(f"Search {noun}")
        left.Add(self._search, 0, wx.EXPAND | wx.BOTTOM, 4)
        self._list = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self._list.SetName(noun.capitalize())
        left.Add(self._list, 1, wx.EXPAND)
        root.Add(left, 2, wx.EXPAND | wx.RIGHT, 8)

        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(self.panel, label="&Details:"), 0, wx.BOTTOM, 2)
        self._preview = wx.TextCtrl(
            self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._preview.SetName(f"{noun.capitalize()} details")
        right.Add(self._preview, 1, wx.EXPAND)
        root.Add(right, 3, wx.EXPAND)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(root, 1, wx.EXPAND | wx.ALL, 8)

        self._buttons: dict[str, wx.Button] = {}
        btn_sz = wx.BoxSizer(wx.HORIZONTAL)
        for label, verb in _VERBS[kind]:
            btn = wx.Button(self.panel, wx.ID_ANY, label=label)
            btn.Bind(wx.EVT_BUTTON, lambda _e, v=verb: self._invoke(v))
            self._buttons[verb] = btn
            btn_sz.Add(btn, 0, wx.RIGHT, 4)
        outer.Add(btn_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.panel.SetSizer(outer)

        self._search.Bind(wx.EVT_TEXT, lambda _e: self._rebuild())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_select())
        apply_listbox_activation(self._list, lambda _e: self._invoke("run"))

    # -- data -----------------------------------------------------------------

    def set_items(self, items: list[LibraryItem]) -> None:
        self._all = items
        self._rebuild()

    def _rebuild(self) -> None:
        query = self._search.GetValue().lower().strip()
        self._items = [
            it
            for it in self._all
            if not query or query in it.name.lower() or query in it.description.lower()
        ]
        self._list.Clear()
        for it in self._items:
            tag = "" if it.enabled else " [disabled]"
            builtin = " [built-in]" if it.is_builtin else ""
            self._list.Append(f"{it.name}{builtin}{tag}")
        if self._list.GetCount():
            self._list.SetSelection(0)
        self._on_select()

    def select_by_id(self, item_id: str) -> None:
        for i, it in enumerate(self._items):
            if it.id == item_id:
                self._list.SetSelection(i)
                self._on_select()
                return

    def current(self) -> LibraryItem | None:
        idx = self._list.GetSelection()
        if idx < 0 or idx >= len(self._items):
            return None
        return self._items[idx]

    def _on_select(self) -> None:
        it = self.current()
        self._preview.SetValue(it.detail if it else "")
        has = it is not None
        for verb, btn in self._buttons.items():
            if verb in ("new", "import", "build"):
                btn.Enable(True)
            elif verb == "delete":
                btn.Enable(has and it is not None and not it.is_builtin)
            elif verb == "promote":
                btn.Enable(has and it is not None and it.can_promote)
            else:
                btn.Enable(has)
        if it is not None and "toggle" in self._buttons:
            self._buttons["toggle"].SetLabel("Ena&ble" if not it.enabled else "Disa&ble")

    # -- dispatch -------------------------------------------------------------

    def _invoke(self, verb: str) -> None:
        owner = self._owner
        if verb == "new":
            owner.prompt_new()
            return
        if verb == "import":
            (owner.prompt_import if self._kind == "prompt" else owner.skill_import)()
            return
        if verb == "build":
            owner.skill_build()
            return
        it = self.current()
        if it is None:
            return
        if verb == "run":
            owner.run_item(it)
        elif verb == "edit":
            owner.prompt_edit(it)
        elif verb == "toggle":
            (owner.prompt_toggle if self._kind == "prompt" else owner.skill_toggle)(it)
        elif verb == "delete":
            owner.prompt_delete(it)
        elif verb == "export":
            (owner.prompt_export() if self._kind == "prompt" else owner.skill_export(it))
        elif verb == "remove":
            owner.skill_remove(it)
        elif verb == "validate":
            owner.agent_validate(it)
        elif verb == "promote":
            owner.promote(it)


class _PromotedAgentDialog:
    """Show a generated agent ``.md`` scaffold: save it as a first-class user agent.

    "Save to My Agents" writes the spec into the user agents dir so it appears in
    the Agents tab and runs through the gateway immediately; Copy and Save to File
    remain for users who keep their agents elsewhere.
    """

    def __init__(
        self,
        parent: object,
        skill_name: str,
        markdown: str,
        *,
        announce: Callable[[str], None] | None = None,
        on_saved: Callable[[object], None] | None = None,
    ) -> None:
        self._markdown = markdown
        self._announce = announce or (lambda _: None)
        self._on_saved = on_saved
        self.dialog = wx.Dialog(
            parent,
            title=f"Promote to Agent — {skill_name}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(620, 480))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label="Generated agent definition. Save it to My Agents to run it from "
                "the Agents tab:",
            ),
            0,
            wx.ALL,
            8,
        )
        text = wx.TextCtrl(
            self.dialog,
            value=markdown,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        text.SetName("Generated agent definition")
        root.Add(text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(self.dialog, label="Save to My &Agents")
        copy_btn = wx.Button(self.dialog, label="&Copy")
        save_btn = wx.Button(self.dialog, label="&Save to File...")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="C&lose")
        btns.Add(add_btn, 0, wx.RIGHT, 6)
        btns.Add(copy_btn, 0, wx.RIGHT, 6)
        btns.Add(save_btn, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(close_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        self.dialog.Layout()
        apply_modal_ids(
            self.dialog, affirmative_id=wx.ID_CANCEL, cancel_id=wx.ID_CANCEL, cancel_label="Close"
        )
        add_btn.Bind(wx.EVT_BUTTON, self._on_add_to_agents)
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        add_btn.SetFocus()

    def _on_add_to_agents(self, _event: object) -> None:
        from quill.core.ai.agent_catalog import save_user_agent

        try:
            spec = save_user_agent(self._markdown)
        except Exception as exc:  # noqa: BLE001
            show_message_box(
                f"Could not save the agent: {exc}",
                "Promote to Agent",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
                announce=self._announce,
            )
            return
        self._announce(f"Saved agent: {spec.display_name}")
        if self._on_saved is not None:
            self._on_saved(spec)
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)

    def show(self) -> int:
        return self.dialog.ShowModal()

    def _on_copy(self, _event: object) -> None:
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self._markdown))
            wx.TheClipboard.Close()
            self._announce("Agent definition copied to clipboard.")

    def _on_save(self, _event: object) -> None:
        with wx.FileDialog(
            self.dialog,
            "Save Agent Definition",
            defaultFile="agent.md",
            wildcard="Agent definition (*.md)|*.md",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fdlg:
            if fdlg.ShowModal() != wx.ID_OK:
                return
            Path(fdlg.GetPath()).write_text(self._markdown, encoding="utf-8")
            self._announce("Agent definition saved.")
