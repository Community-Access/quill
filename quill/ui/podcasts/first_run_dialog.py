"""First Run: one screen, one question, and a way straight to a first podcast.

qc.md section 14 (Phase 6). It used to be three screens -- welcome, add your
first podcast, you're set -- and everything those screens explained now lives
in the Tutorials, where it can be found again. What is left is the one thing
only a first run can ask: **where would you like to land each time Cast
opens?** -- the same choices as Preferences' "Where to land on launch" -- and
**Add Your First Podcast**, the thing a new library is waiting for.

The welcome words are a **read-only text field** rather than a wall of labels:
it can be reviewed with the arrow keys and copied. **Skip** is Escape: somebody
who already knows what a podcast player is leaves in one keystroke, and Cast
counts that as done -- showing it again would be overriding their choice.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts import launch_place
from quill.core.podcasts.onboarding import (
    SCREEN_BODIES,
    WELCOME,
    OnboardingState,
    needs_first_run,
)
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Welcome to QUILL Cast"

#: The landing places a first run offers: the automatic rule, then the places
#: a new listener is likely to want. Preferences offers every place.
FIRST_RUN_PLACES: tuple[str, ...] = (
    launch_place.AUTOMATIC,
    "inbox",
    "new_episodes",
    "continue_listening",
    "favorites",
    "podcasts",
)

_WORDS = (
    SCREEN_BODIES[WELCOME]
    + "\n\nOne question below, and then you are ready. The Tutorials, on the Help "
    "menu (Ctrl+Alt+F1), walk you through everything else whenever you like."
)


class FirstRunDialog:
    """Welcome, where to land, and Add Your First Podcast."""

    def __init__(
        self,
        parent: Any,
        *,
        state: OnboardingState,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        on_add_podcast: Callable[[], None] | None = None,
        launch_view: str = "",
        on_launch_place: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._state = state
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._on_add_podcast = on_add_podcast
        self._on_launch_place = on_launch_place
        self._wants_add = False
        self._dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self._dialog, label="About QUILL Cast:"), 0, wx.LEFT | wx.TOP, 12)
        self._body = wx.TextCtrl(
            self._dialog, value=_WORDS, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._body.SetHelpText("About QUILL Cast. Read only: arrow through it at your own pace.")
        root.Add(self._body, 1, wx.EXPAND | wx.ALL, 12)
        root.Add(
            wx.StaticText(self._dialog, label="&Where would you like to land each time?"),
            0,
            wx.LEFT | wx.RIGHT,
            12,
        )
        labels = dict(launch_place.CHOICES)
        self._places = [value for value in FIRST_RUN_PLACES if value in labels]
        self._place = wx.Choice(self._dialog, choices=[labels[value] for value in self._places])
        self._place.SetHelpText(
            "Which place has focus each time QUILL Cast opens. What is new lands on the "
            "Inbox when anything is waiting, else Continue Listening, else Podcasts. "
            "You can change it later in Preferences."
        )
        current = launch_view if launch_view in self._places else launch_place.AUTOMATIC
        self._place.SetSelection(self._places.index(current))
        root.Add(self._place, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        self._tips_check = wx.CheckBox(self._dialog, label="Show me a &tip now and then")
        self._tips_check.SetHelpText(
            "One sentence, once each, the first time you reach somewhere a tip would help."
        )
        self._tips_check.SetValue(state.tips_enabled)
        root.Add(self._tips_check, 0, wx.ALL, 12)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self._dialog, label="&Add Your First Podcast...")
        self._add_btn.SetHelpText("Keeps your choice and opens Add Podcast.")
        self._add_btn.Show(on_add_podcast is not None)
        done = wx.Button(self._dialog, wx.ID_OK, label="Done")
        done.SetHelpText("Keeps your choice and goes to Cast.")
        skip = wx.Button(self._dialog, wx.ID_CANCEL, label="Skip")
        skip.SetHelpText("Goes to Cast and changes nothing. This welcome does not come back.")
        buttons.Add(self._add_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(done, 0, wx.RIGHT, 6)
        buttons.Add(skip, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self._dialog.SetSizer(root)
        self._dialog.SetMinSize((560, 400))
        apply_modal_ids(
            self._dialog, affirmative_id=wx.ID_OK, affirmative_label="Done", cancel_id=wx.ID_CANCEL
        )
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self.add_podcast())
        self._body.SetFocus()

    @property
    def dialog(self) -> Any:
        return self._dialog

    def chosen_place(self) -> str:
        return self._places[max(0, self._place.GetSelection())]

    def add_podcast(self) -> None:
        """Keep the choice, close, and open Add Podcast -- what a new library wants."""
        if self._on_add_podcast is None:
            return
        self._wants_add = True
        self._dialog.EndModal(self._wx.ID_OK)

    def show(self) -> OnboardingState:
        """Run it and return the state, whether finished or skipped.

        Skipping still counts as done and keeps nothing else; Done and Add Your
        First Podcast keep the landing place.
        """
        try:
            if self._show_modal_dialog is not None:
                answer = self._show_modal_dialog(self._dialog, TITLE)
            else:
                answer = self._dialog.ShowModal()  # dialog_button_contract: exempt
            self._state.completed_first_run = True
            self._state.tips_enabled = bool(self._tips_check.GetValue())
            if (answer == self._wx.ID_OK or self._wants_add) and self._on_launch_place:
                self._on_launch_place(self.chosen_place())
            return self._state
        finally:
            self._dialog.Destroy()
            if self._wants_add and self._on_add_podcast is not None:
                self._wx.CallAfter(self._on_add_podcast)


def maybe_run_first_run(host: Any) -> bool:
    """Run the flow at launch if this listener needs it. True when it ran.

    **This function is the whole point of the fix.** The dialog above has
    existed since 1.1 with no caller at all -- written, tested, and never once
    shown -- which Quill Radio's equivalent carried a docstring about, as the
    failure it existed not to repeat. It had gone on being true.

    Called deferred (``wx.CallAfter``) once the window is up. Never raises: a
    welcome that can take the app down on its very first launch would be the
    worst possible first impression, and there is nothing here worth failing a
    launch over.

    **It refuses over a window that is not on screen.** The launch path shows
    the main window and *then* enters the loop this deferred call runs in, so
    a real launch always has a frame up. Anywhere else -- a frame built and
    never shown, which is what a test harness does -- a modal would be a
    dialog with nothing behind it and nobody able to answer it, and
    ``ShowModal`` would sit there forever. A welcome nobody can see is not a
    welcome.

    **And it refuses for somebody who already has podcasts**, however they got
    there -- an imported OPML, a restored `.quillsetup`, an upgrade. Explaining
    how to add a first podcast to somebody with two hundred is a way of saying
    nobody checked.
    """
    import logging

    try:
        frame = getattr(host, "frame", None)
        is_shown = getattr(frame, "IsShown", None)
        if frame is None or (callable(is_shown) and not is_shown()):
            return False
        history = getattr(host, "_podcast_history", None)
        state = getattr(history, "onboarding", None)
        if state is None:
            return False
        shows = getattr(getattr(host, "_podcast_library", None), "shows", [])
        if not needs_first_run(state, has_shows=bool(shows)):
            return False

        add = getattr(host, "_podcast_open_add_dialog", None)
        library = getattr(host, "_podcast_library", None)
        settings = getattr(library, "settings", None)

        def _land(value: str) -> None:
            if settings is None:
                return
            settings.default_launch_view = value
            save = getattr(host, "_save_podcast_library", None)
            if callable(save):
                save()

        dialog = FirstRunDialog(
            frame,
            state=state,
            announce=getattr(host, "_announce", None),
            show_modal_dialog=getattr(host, "_show_modal_dialog", None),
            on_add_podcast=(lambda: add()) if callable(add) else None,
            launch_view=str(getattr(settings, "default_launch_view", "") or ""),
            on_launch_place=_land,
        )
        dialog.show()
        saver = getattr(host, "_save_podcast_history", None)
        if callable(saver):
            saver()
        return True
    except Exception:  # noqa: BLE001 - a welcome must never break a launch
        logging.getLogger(__name__).exception("first-run flow failed")
        return False
