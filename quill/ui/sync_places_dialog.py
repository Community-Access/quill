"""**Carry My Place Between Machines...** -- the setup, in one window.

Three things to decide and one button that does the work: a folder both machines
can see, a recovery phrase, and a name for this machine. Then Sync Now.

The window is built around the one question that makes or breaks this feature:
**is this the first machine, or the second?** Getting that wrong is the failure
that loses data -- setting up a fresh vault over a folder that already has one
orphans every record already in it -- so the window answers the question
*itself*, by looking at the folder, and says which case it is in. Choosing a
folder that is already set up switches the phrase field from *"here is your new
phrase, write it down"* to *"type the phrase from your other machine"*, and the
button changes with it.

**The phrase is spoken once, on request, and never again.** *Read My Phrase
Aloud* says it a word at a time with numbers, which is what somebody writing it
down needs. It is stored in the platform credential store like every other
secret, never in a settings file.

**What gets shared is three switches, not one.** They carry genuinely
different exposure, so collapsing them would be a lie about what the folder
learns. The encrypted half is QUILL to QUILL and needs the phrase. The plain
half writes a published ``listening-places/1`` file that another app -- Earshot
on a phone -- reads and writes, and it needs **no phrase at all**: gating it
behind encryption would mean a feature nobody can set up, which syncs nothing.
Names are a third switch because the ids in that file are hashed and the names
are not.

**Sync runs off the UI thread**, and its report is a sentence: what came back,
what went out, and whether two machines disagreed about a place.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.sync import recovery_phrase, vault_file
from quill.core.sync.listening_places import new_device_id as _new_device_id
from quill.core.sync.places_config import PlacesConfig, default_device_name
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Carry My Place Between Machines"

#: What the window says about a folder nobody has synced to yet.
NEW_VAULT_HEADING = (
    "This folder is not set up yet. QUILL will make a recovery phrase for it -- "
    "write it down, because it is the only way to add another machine."
)

#: And one that already has a vault: the second machine's case.
JOIN_VAULT_HEADING = (
    "This folder is already set up. Type the recovery phrase from your other machine to join it."
)


class SyncPlacesDialog:
    """Set up (or join) a shared folder, and sync on demand."""

    def __init__(
        self,
        parent: Any,
        *,
        config: PlacesConfig,
        on_save: Callable[[PlacesConfig, str], None] | None = None,
        sync_now: Callable[[PlacesConfig, str], str] | None = None,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        pick_folder: Callable[[], str] | None = None,
        phrase: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._config = config
        self._on_save = on_save
        self._sync_now = sync_now
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._pick_folder = pick_folder

        self._dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)

        self._heading = wx.StaticText(self._dialog, label="")
        root.Add(self._heading, 0, wx.ALL | wx.EXPAND, 10)

        self._enabled = wx.CheckBox(self._dialog, label="&Carry my place between machines")
        self._enabled.SetName(
            "Send where you got to in a book, an episode or a recording to a shared folder"
        )
        self._enabled.SetValue(config.enabled)
        root.Add(self._enabled, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(wx.StaticText(self._dialog, label="Shared &folder:"), 0, wx.LEFT | wx.RIGHT, 10)
        folder_row = wx.BoxSizer(wx.HORIZONTAL)
        self._folder = wx.TextCtrl(self._dialog, value=config.remote_dir)
        self._folder.SetName("A folder both machines can see, such as one inside OneDrive")
        folder_row.Add(self._folder, 1, wx.RIGHT, 6)
        self._browse_btn = wx.Button(self._dialog, label="&Browse...")
        folder_row.Add(self._browse_btn, 0)
        root.Add(folder_row, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(wx.StaticText(self._dialog, label="&Recovery phrase:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._phrase = wx.TextCtrl(self._dialog, value=phrase)
        self._phrase.SetName("Eight words that unlock the shared folder")
        root.Add(self._phrase, 0, wx.EXPAND | wx.ALL, 10)

        phrase_row = wx.BoxSizer(wx.HORIZONTAL)
        self._make_btn = wx.Button(self._dialog, label="&Make a New Phrase")
        self._speak_btn = wx.Button(self._dialog, label="Read My Phrase A&loud")
        phrase_row.Add(self._make_btn, 0, wx.RIGHT, 6)
        phrase_row.Add(self._speak_btn, 0)
        root.Add(phrase_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(
            wx.StaticText(self._dialog, label="Name for &this machine:"), 0, wx.LEFT | wx.RIGHT, 10
        )
        self._device = wx.TextCtrl(self._dialog, value=config.device or default_device_name())
        self._device.SetName("Shown in the sync history so you can tell the machines apart")
        root.Add(self._device, 0, wx.EXPAND | wx.ALL, 10)

        self._on_stop = wx.CheckBox(self._dialog, label="Sync when playback &stops, as well")
        self._on_stop.SetName("Otherwise syncing happens only when you ask for it")
        self._on_stop.SetValue(config.sync_on_stop)
        root.Add(self._on_stop, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        shared = wx.StaticBoxSizer(wx.VERTICAL, self._dialog, "What goes in that folder")
        self._encrypted = wx.CheckBox(self._dialog, label="&Encrypted, for my other QUILL machines")
        self._encrypted.SetName(
            "Locked with your recovery phrase. Only a machine that has the phrase "
            "can read it, and the folder's provider learns nothing but sizes."
        )
        self._encrypted.SetValue(config.encrypted)
        shared.Add(self._encrypted, 0, wx.ALL, 6)

        self._interchange = wx.CheckBox(self._dialog, label="A &plain file other apps can read")
        self._interchange.SetName(
            "Writes a Listening Places file other podcast apps understand, so your "
            "place follows you to a phone as well as to another computer. It needs "
            "no recovery phrase. Every id in it is hashed, so anybody who can see "
            "the folder learns how much you listen and when, but not to what."
        )
        self._interchange.SetValue(config.interchange)
        shared.Add(self._interchange, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self._labels = wx.CheckBox(self._dialog, label="Include episode and file &names")
        self._labels.SetName(
            'With this off, a message says "an episode" instead of naming it, and '
            "anybody who can see the folder learns less about what you listen to."
        )
        self._labels.SetValue(config.include_labels)
        shared.Add(self._labels, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        root.Add(shared, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.TextCtrl(
            self._dialog, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 60)
        )
        self._status.SetName("What happened")
        self._status.SetValue(config.describe())
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._sync_btn = wx.Button(self._dialog, label="&Sync Now")
        buttons.Add(self._sync_btn, 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self._dialog, wx.ID_OK, "Sa&ve"), 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self._dialog, wx.ID_CANCEL, "Cl&ose"), 0)
        root.Add(buttons, 0, wx.ALL, 10)

        self._dialog.SetSizer(root)
        self._dialog.SetMinSize((640, 520))
        self._dialog.Fit()
        apply_modal_ids(self._dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

        self._browse_btn.Bind(wx.EVT_BUTTON, lambda _e: self.browse())
        self._make_btn.Bind(wx.EVT_BUTTON, lambda _e: self.make_phrase())
        self._speak_btn.Bind(wx.EVT_BUTTON, lambda _e: self.speak_phrase())
        self._sync_btn.Bind(wx.EVT_BUTTON, lambda _e: self.sync())
        self._folder.Bind(wx.EVT_TEXT, lambda _e: self._sync_heading())
        self._dialog.Bind(wx.EVT_BUTTON, self._on_save_clicked, id=wx.ID_OK)
        self._sync_heading()
        self._enabled.SetFocus()

    @property
    def dialog(self) -> Any:
        return self._dialog

    def _set_status(self, text: str) -> None:
        self._status.SetValue(text)
        self._announce(text)

    def _sync_heading(self) -> None:
        """Say whether this is the first machine or the second.

        Answered by looking at the folder rather than asking, because getting it
        wrong is the failure that loses data, and somebody who has to decide has
        to already understand the thing they are setting up.
        """
        folder = self._folder.GetValue().strip()
        joining = bool(folder) and vault_file.exists(folder)
        self._heading.SetLabel(JOIN_VAULT_HEADING if joining else NEW_VAULT_HEADING)
        # Making a fresh phrase for a folder that already has one can only
        # produce a phrase that will be rejected, so the button says so by
        # being unavailable rather than by failing after it is pressed.
        self._make_btn.Enable(not joining)
        self._dialog.Layout()

    def config(self) -> PlacesConfig:
        """What the fields currently say, as a config record."""
        interchange = bool(self._interchange.GetValue())
        return PlacesConfig(
            enabled=bool(self._enabled.GetValue()),
            remote_dir=self._folder.GetValue().strip(),
            device=self._device.GetValue().strip() or default_device_name(),
            has_phrase=bool(recovery_phrase.normalise(self._phrase.GetValue())),
            sync_on_stop=bool(self._on_stop.GetValue()),
            encrypted=bool(self._encrypted.GetValue()),
            interchange=interchange,
            # Minted here, once, the first time the plain half is switched on:
            # it names this device's file in a folder other people may see, so
            # it is random rather than the machine's name, and it must not
            # change afterwards or this device starts leaving a second file
            # behind on every sync.
            device_id=self._config.device_id or (_new_device_id() if interchange else ""),
            include_labels=bool(self._labels.GetValue()),
        )

    def browse(self) -> str:
        """Choose the shared folder."""
        wx = self._wx
        if self._pick_folder is not None:
            chosen = self._pick_folder()
        else:
            with wx.DirDialog(  # dialog_button_contract: exempt
                self._dialog, "Choose a folder both machines can see"
            ) as dialog:
                chosen = dialog.GetPath() if dialog.ShowModal() == wx.ID_OK else ""
        if chosen:
            self._folder.SetValue(chosen)
            self._sync_heading()
        return chosen

    def make_phrase(self) -> str:
        """Generate a phrase, put it in the field, and say to write it down."""
        phrase = recovery_phrase.generate()
        self._phrase.SetValue(phrase)
        self._set_status(
            "A new recovery phrase is in the box. Write it down now: it is the "
            "only way to add another machine, and QUILL cannot recover it for you."
        )
        return phrase

    def speak_phrase(self) -> bool:
        """Read the phrase back, numbered, one word at a time."""
        phrase = self._phrase.GetValue().strip()
        if not phrase:
            self._set_status("There is no recovery phrase to read yet.")
            return False
        self._announce(recovery_phrase.spoken(phrase))
        return True

    def _validate(self) -> str:
        """Everything wrong with the form, as one sentence, or ""."""
        config = self.config()
        if not config.enabled:
            return ""
        if not config.remote_dir:
            return "Choose a folder both machines can see first."
        if not Path(config.remote_dir).is_dir():
            return "That folder does not exist. Choose one both machines can see."
        if not config.encrypted and not config.interchange:
            return "Choose at least one thing to put in that folder."
        # A phrase is the key to the encrypted half and is meaningless to the
        # plain one, so it is only required when the encrypted half is wanted.
        if not config.encrypted:
            return ""
        return recovery_phrase.describe_problem(self._phrase.GetValue())

    def _on_save_clicked(self, event: Any) -> None:
        problem = self._validate()
        if problem:
            # Never closes on a form that would not work: saving a half-set-up
            # sync means finding out at the next sync, somewhere else.
            self._set_status(problem)
            return
        if self._on_save is not None:
            self._on_save(self.config(), recovery_phrase.normalise(self._phrase.GetValue()))
        event.Skip()

    def sync(self) -> bool:
        """Run one sync now and report what it did."""
        problem = self._validate()
        if problem:
            self._set_status(problem)
            return False
        if self._sync_now is None:
            self._set_status("Syncing is not available here.")
            return False
        config = self.config()
        if not config.enabled:
            self._set_status("Turn on carrying your place first.")
            return False
        self._set_status("Syncing...")
        said = self._sync_now(config, recovery_phrase.normalise(self._phrase.GetValue()))
        self._set_status(said)
        self._sync_heading()
        return True

    def show(self) -> int:
        """Show the window, and always destroy it afterwards (A11Y-4)."""
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self._dialog, TITLE))
            return int(self._dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self._dialog.Destroy()
