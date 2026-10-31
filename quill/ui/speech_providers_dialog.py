"""Speech Providers: use a speech service you already have an account with (D-31).

Reached from Dictation Settings (**Speech Pro&viders...**) in QUILL, QUILL
Lite, QUILL Transcribe and Quill Inkwell -- one window, one store. Local
dictation stays the default and the recommendation; this is for a person who
already pays a speech provider and wants dictation to use it.

* **Providers** lists every service (:mod:`quill.core.windows_dictation.cloud.registry`),
  each marked "set up" once its details are saved. Choosing one shows what it
  can do and its fields, built from its own ``fields()``, each with its F1
  sentence.
* **Secret fields** never show a saved value: empty means "keep what is saved".
  **Save** puts secrets in Windows Credential Manager at once (a service-account
  file is protected with Windows' own encryption first); the plain fields --
  region, project -- are kept with Dictation Settings' OK, like every other
  setting there.
* **Test Connection** asks the provider about the account (a token or a list),
  never with anybody's speech, and says one sentence: "Azure answered: ready,
  region westeurope", or what to fix, naming the field -- and the focus goes to
  that field.
* **Remove** forgets everything saved for the provider.
* Choosing a provider as the speech engine happens in Dictation Settings, and
  asks first whether speech may go there (the consent).

Close carries no access key (GATE-14); Escape closes. Nothing here is spoken
that the screen reader already says (GATE-13): only the test's outcome and
what Save and Remove did.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Mapping
from typing import Any

import wx

from quill.core.windows_dictation.cloud.credentials import (
    has_required,
    remove,
    save,
    values_for,
)
from quill.core.windows_dictation.cloud.errors import CloudSpeechError, said
from quill.core.windows_dictation.cloud.registry import providers
from quill.core.windows_dictation.cloud.types import CloudProvider, ProviderField
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_message_box,
)
from quill.ui.dpi import dip_size

__all__ = ["SpeechProvidersDialog", "about_provider"]

_PAD = 8
_TITLE = "Speech Providers"


def about_provider(provider: CloudProvider) -> str:
    """What the page says a provider is and can do, in plain sentences."""
    capabilities = provider.capabilities()
    lines = [provider.description or provider.name]
    lines.append(
        "Words while you speak: yes."
        if capabilities.streaming
        else "Words while you speak: no. Each phrase is written when you pause."
    )
    if capabilities.biasing:
        lines.append(
            f"Learns your words: up to {capabilities.biasing_limit} from My Words "
            f"and Phrases, as its {capabilities.biasing_name}."
        )
    else:
        lines.append("Learns your words: not from QUILL.")
    lines.append(f"Speech goes to {provider.company}. Your provider bills you; see its usage page.")
    if provider.console_url:
        lines.append(f"Usage page: {provider.console_url}")
    missing = provider.available()
    if missing:
        lines.append(missing)
    lines.append(
        f"Details last checked against {provider.name}'s documents on {provider.last_checked}."
    )
    return "\n".join(lines)


class SpeechProvidersDialog(wx.Dialog):
    """The providers, their fields, and Test Connection. Read :meth:`stored` after."""

    def __init__(
        self,
        parent: Any,
        stored: Mapping[str, Mapping[str, str]] | None = None,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, title=_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._announce = announce or (lambda _text: None)
        self._stored: dict[str, dict[str, str]] = {
            str(key): dict(value) for key, value in (stored or {}).items()
        }
        self._providers = [item for item in providers() if item.id != "openai"]
        self._controls: dict[str, Any] = {}
        self._dirty = False
        self._row = -1
        self._testing = False

        outer = wx.BoxSizer(wx.VERTICAL)
        list_label = wx.StaticText(self, label="&Providers:")
        self.providers = wx.ListBox(self, choices=[self._label(item) for item in self._providers])
        self.providers.SetHelpText(
            "Speech services you can use for dictation with your own account. Choose "
            "one to see what it can do and what it needs. The built-in engines stay "
            "the default: they never send anything anywhere. A provider bills you, "
            "not QUILL, and is used only after you choose it as the speech engine in "
            "Dictation Settings and agree to send your speech there."
        )
        self.providers.Bind(wx.EVT_LISTBOX, self._on_choose)
        outer.Add(list_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        outer.Add(self.providers, 1, wx.EXPAND | wx.ALL, _PAD)

        about_label = wx.StaticText(self, label="Abo&ut this provider:")
        self.about = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=dip_size(self, -1, 110)
        )
        self.about.SetHelpText(
            "What the chosen provider is, whether it gives words while you speak, "
            "whether it learns your words, where your speech goes, and its usage page."
        )
        outer.Add(about_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        outer.Add(self.about, 0, wx.EXPAND | wx.ALL, _PAD)

        # The fields live in a panel of their own, rebuilt per provider, so Tab
        # still reaches them between the description and the buttons.
        self.fields_panel = wx.Panel(self)
        self.fields_panel.SetHelpText("The details the chosen provider needs.")
        self._fields_sizer = wx.FlexGridSizer(cols=2, vgap=_PAD // 2, hgap=_PAD)
        self._fields_sizer.AddGrowableCol(1, 1)
        self.fields_panel.SetSizer(self._fields_sizer)
        outer.Add(self.fields_panel, 0, wx.EXPAND | wx.ALL, _PAD)

        result_label = wx.StaticText(self, label="Last &result:")
        self.result = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.result.SetHelpText("What the last Test Connection, Save or Remove said.")
        outer.Add(result_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        outer.Add(self.result, 0, wx.EXPAND | wx.ALL, _PAD)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.test_button = wx.Button(self, label="&Test Connection")
        self.test_button.SetHelpText(
            "Asks the provider whether these details work, using a check of the "
            "account, never your speech. Says what it answered, or which field to fix."
        )
        self.test_button.Bind(wx.EVT_BUTTON, self._on_test)
        self.save_button = wx.Button(self, label="&Save")
        self.save_button.SetHelpText(
            "Keeps these details. Keys go to Windows Credential Manager now and are "
            "never written in QUILL's settings; the other details are kept when you "
            "choose OK in Dictation Settings."
        )
        self.save_button.Bind(wx.EVT_BUTTON, self._on_save)
        self.remove_button = wx.Button(self, label="Re&move")
        self.remove_button.SetHelpText("Forgets everything saved for this provider, keys included.")
        self.remove_button.Bind(wx.EVT_BUTTON, self._on_remove)
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText(
            "Close Speech Providers. Asks first if you changed details and did not save them."
        )
        for button in (self.test_button, self.save_button, self.remove_button):
            buttons.Add(button, 0, wx.RIGHT, _PAD)
        buttons.Add(close, 0)
        outer.Add(buttons, 0, wx.ALL | wx.EXPAND, _PAD)

        self.SetSizer(outer)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)
        # Bound after, so it runs first: unsaved changes are asked about before
        # bind_close_button's handler closes the window (event.Skip lets it).
        close.Bind(wx.EVT_BUTTON, self._on_close)
        if self._providers:
            self.providers.SetSelection(0)
            self._show(0)
        self.SetMinSize(dip_size(self, 560, 560))
        self.Fit()
        self.providers.SetFocus()

    # -- what the host reads ---------------------------------------------------- #

    def stored(self) -> dict[str, dict[str, str]]:
        """The plain fields per provider, for ``windows_dictation_speech_providers``."""
        return {key: dict(value) for key, value in self._stored.items() if value}

    # -- the list ------------------------------------------------------------- #

    def _label(self, provider: CloudProvider) -> str:
        plain = self._stored.get(provider.id)
        try:  # the credential store is read only for a provider somebody saved
            ready = bool(plain) and has_required(provider, values_for(provider, plain))
        except Exception:  # noqa: BLE001 - an unreadable store is "not set up"
            ready = False
        return f"{provider.name}, {'set up' if ready else 'not set up'}"

    def _provider(self) -> CloudProvider | None:
        row = self._row
        return self._providers[row] if 0 <= row < len(self._providers) else None

    def _on_choose(self, _event: Any) -> None:
        row = self.providers.GetSelection()
        if row == self._row or row < 0:
            return
        if not self._settle_unsaved():
            self.providers.SetSelection(self._row)
            return
        self._show(row)

    def _show(self, row: int) -> None:
        """Show provider *row*: its description and its fields."""
        self._row = row
        provider = self._providers[row]
        self.about.SetValue(about_provider(provider))
        self.result.SetValue("")
        self.fields_panel.Freeze()
        try:
            self._fields_sizer.Clear(delete_windows=True)
            self._controls = {}
            stored = self._stored.get(provider.id, {})
            for spec in provider.fields():
                self._add_field(spec, stored)
            self.fields_panel.Layout()
        finally:
            self.fields_panel.Thaw()
        self._dirty = False
        self.Layout()
        self.Fit()

    def _add_field(self, spec: ProviderField, stored: Mapping[str, str]) -> None:
        panel = self.fields_panel
        label = spec.label + ("" if spec.required else " (optional)") + ":"
        saved = str(stored.get(spec.key, "") or "")
        # Each control's label is built just before it, so the screen reader
        # takes the control's name from it (GATE-CTLLABEL).
        if spec.kind == "choice":
            caption = wx.StaticText(panel, label=label)
            control: Any = wx.Choice(panel, choices=[text for _value, text in spec.choices])
            values = [value for value, _text in spec.choices]
            chosen = saved or spec.default
            control.SetSelection(values.index(chosen) if chosen in values else 0)
            control.SetHelpText(spec.help or spec.label)
            control.Bind(wx.EVT_CHOICE, self._on_edit)
            holder: Any = control
        elif spec.kind == "file":
            holder = wx.BoxSizer(wx.HORIZONTAL)
            caption = wx.StaticText(panel, label=label)
            control = wx.TextCtrl(panel, value="")
            control.SetHelpText(
                (spec.help or spec.label)
                + " A saved file stays saved when this is empty; choose another to replace it."
            )
            control.SetHint("saved" if saved else "")
            control.Bind(wx.EVT_TEXT, self._on_edit)
            browse = wx.Button(panel, label="&Browse...")
            browse.SetHelpText(f"Choose the file for {spec.label}.")
            browse.Bind(wx.EVT_BUTTON, lambda _e, c=control, s=spec: self._browse(c, s))
            holder.Add(control, 1, wx.EXPAND | wx.RIGHT, _PAD)
            holder.Add(browse, 0)
        else:
            style = wx.TE_PASSWORD if spec.kind == "secret" else 0
            # A saved secret is never shown: empty means "keep what is saved".
            value = "" if spec.kind == "secret" else (saved or spec.default)
            caption = wx.StaticText(panel, label=label)
            control = wx.TextCtrl(panel, value=value, style=style)
            help_text = spec.help or spec.label
            control.SetHelpText(help_text)
            control.Bind(wx.EVT_TEXT, self._on_edit)
            holder = control
        self._controls[spec.key] = control
        self._fields_sizer.Add(caption, 0, wx.ALIGN_CENTER_VERTICAL)
        self._fields_sizer.Add(holder, 1, wx.EXPAND)

    def _browse(self, control: Any, spec: ProviderField) -> None:
        with wx.FileDialog(
            self,
            f"Choose {spec.label}",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() == wx.ID_OK:
                control.SetValue(picker.GetPath())
        control.SetFocus()

    def _on_edit(self, _event: Any) -> None:
        self._dirty = True

    def _entered(self) -> dict[str, str]:
        """What the fields hold now (secrets as typed; empty means unchanged)."""
        provider = self._provider()
        out: dict[str, str] = {}
        if provider is None:
            return out
        for spec in provider.fields():
            control = self._controls.get(spec.key)
            if control is None:
                continue
            if spec.kind == "choice":
                row = control.GetSelection()
                out[spec.key] = spec.choices[row][0] if 0 <= row < len(spec.choices) else ""
            else:
                out[spec.key] = control.GetValue().strip()
        return out

    def _values_to_use(self) -> dict[str, str]:
        """The fields as they would be after Save: typed values over saved ones."""
        provider = self._provider()
        if provider is None:
            return {}
        merged = values_for(provider, self._stored.get(provider.id))
        for key, value in self._entered().items():
            if value:
                merged[key] = value
        for spec in provider.fields():  # a chosen file is read for the test
            if spec.kind == "file" and self._entered().get(spec.key):
                try:
                    with open(self._entered()[spec.key], encoding="utf-8") as handle:
                        merged[spec.key] = handle.read()
                except OSError:
                    merged[spec.key] = ""
        return merged

    # -- the buttons ------------------------------------------------------------ #

    def _say(self, sentence: str) -> None:
        self.result.SetValue(sentence)
        self._announce(sentence)

    def _focus_field(self, label: str) -> None:
        provider = self._provider()
        if provider is None or not label:
            return
        for spec in provider.fields():
            if spec.label == label and spec.key in self._controls:
                self._controls[spec.key].SetFocus()
                return

    def _on_test(self, _event: Any) -> None:
        provider = self._provider()
        if provider is None or self._testing:
            return
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._say("Safe Mode is on, and Safe Mode never sends anything to the internet.")
            return
        values = self._values_to_use()
        problem = provider.available() or ""
        if not problem:
            field_problem = provider.problem(values)
            if field_problem is not None:
                self._say(said(field_problem))
                self._focus_field(field_problem.field)
                return
        if problem:
            self._say(problem)
            return
        self._testing = True
        self.test_button.Disable()
        self._say(f"Asking {provider.name}...")

        def run() -> None:
            try:
                sentence, field = provider.test(values), ""
            except CloudSpeechError as error:
                sentence, field = said(error), error.field
            except Exception:  # noqa: BLE001 - one sentence, never a traceback
                sentence, field = f"{provider.name} could not be tested.", ""
            wx.CallAfter(self._tested, sentence, field)

        threading.Thread(  # GATE-40-OK: one account check asked for, result marshalled back
            target=run, name="speech-provider-test", daemon=True
        ).start()

    def _tested(self, sentence: str, field: str) -> None:
        if not dialog_alive(self):
            return
        self._testing = False
        self.test_button.Enable()
        self._say(sentence)
        self._focus_field(field)

    def _save_now(self) -> bool:
        provider = self._provider()
        if provider is None:
            return False
        values = self._values_to_use()
        problem = provider.problem(values)
        if problem is not None:
            self._say(f"Not saved. {said(problem)}")
            self._focus_field(problem.field)
            return False
        try:
            plain = save(provider, self._entered())
        except CloudSpeechError as error:
            self._say(f"Not saved. {said(error)}")
            self._focus_field(error.field)
            return False
        self._stored[provider.id] = plain
        self._dirty = False
        self.providers.SetString(self._row, self._label(provider))
        self._show_saved(provider)
        return True

    def _show_saved(self, provider: CloudProvider) -> None:
        """Clear the secret fields again: a saved secret is never shown."""
        for spec in provider.fields():
            control = self._controls.get(spec.key)
            if spec.secret and control is not None:
                control.ChangeValue("")
                if spec.kind == "file":
                    control.SetHint("saved")
        self._dirty = False

    def _on_save(self, _event: Any) -> None:
        provider = self._provider()
        if provider is not None and self._save_now():
            self._say(
                f"{provider.name} saved. Choose it as the speech engine in Dictation "
                "Settings to use it."
            )

    def _on_remove(self, _event: Any) -> None:
        provider = self._provider()
        if provider is None:
            return
        answer = show_message_box(
            f"Forget everything saved for {provider.name}, keys included?",
            _TITLE,
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self,
        )
        if answer != wx.YES:
            return
        remove(provider)
        self._stored.pop(provider.id, None)
        self.providers.SetString(self._row, self._label(provider))
        self._show(self._row)
        self._say(f"{provider.name} removed. Nothing is saved for it now.")

    def _settle_unsaved(self) -> bool:
        """Ask about unsaved changes; ``False`` when the person cancelled."""
        provider = self._provider()
        if not self._dirty or provider is None:
            return True
        answer = show_message_box(
            f"Save your changes to {provider.name}?",
            _TITLE,
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
            self,
        )
        if answer == wx.CANCEL:
            return False
        if answer == wx.YES:
            return self._save_now()
        self._dirty = False
        return True

    def _on_close(self, event: Any) -> None:
        if self._settle_unsaved():
            event.Skip()
