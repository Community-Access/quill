"""The Tutorials window: a book that can watch you use the app.

Two pages in one peer window. **Contents** is a tree of tracks and lessons
with a filter box over it. **Lesson** is one step at a time in a read-only
field you can arrow through, with the keys rendered from the command registry
so they are the keys you actually have.

What makes it worth building rather than shipping another document:

* **Try it runs the step.** A step that names a command can be performed from
  here, which means a lesson can open Browse Stations for you and then talk
  you through what you are standing in.
* **Follow me notices that you did it.** Steps that carry a check are watched
  -- once a second, against the app's live state, never against keystrokes --
  and when the state changes the lesson says what it noticed and moves on. You
  can be standing in another window while that happens: this window is a peer,
  so the tutorial keeps going while you work in the app it is teaching.
* **Your place is kept.** Close it mid-lesson and it opens there again.

Announcement discipline (GATE-13): this window announces a step when it
*changes under you*, which is exactly what a screen reader does not say -- and
says nothing at all about its own title, its controls, or focus moving, which
is what the reader already says. Nothing here is announced twice.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import tutorials as catalogue
from quill.core.radio.tutorial_progress import (
    TutorialProgressStore,
    load_progress,
    save_progress,
)
from quill.core.radio.tutorials.model import Tutorial, render_step, render_tutorial
from quill.ui.dialog_contract import announce_surface_exit, apply_modal_ids, bind_close_button
from quill.ui.radio import tutorial_checks, tutorials_contents

TITLE = "Quill Radio Tutorials"

#: The one open window, if any. Asking for it again raises it rather than
#: opening a second copy -- the rule every Radio surface follows.
_OPEN: TutorialsWindow | None = None

#: How often Follow me asks the app whether the step happened. A second is
#: slow enough to cost nothing and fast enough that the answer feels immediate.
_WATCH_MS = 1000


def open_tutorials(host: Any, *, slug: str = "") -> None:
    """Open (or raise) the window; *slug* starts that lesson straight away."""
    global _OPEN
    if _OPEN is not None:
        _OPEN.raise_window(slug=slug)
        return
    window = TutorialsWindow(host)
    _OPEN = window
    window.show(slug=slug)


class TutorialsWindow:
    """Contents and lesson, in one window."""

    def __init__(self, host: Any) -> None:
        import wx

        self._wx = wx
        self._host = host
        self._announce = getattr(host, "_announce", None)
        self._windows = getattr(host, "_windows", None)
        self._modeless = self._windows is not None
        self._progress: TutorialProgressStore = self._load_progress()
        self._tutorial: Tutorial | None = None
        self._index = 0
        self._baseline: dict[str, Any] = {}
        self._reading_whole = False
        self._menu_id_refs: list[Any] = []
        self._rows: dict[Any, str] = {}
        # Where this was opened from, captured before this window registers
        # itself: "here" in the filter box means the window you came from, and
        # after registration the newest window would be this one.
        self._came_from = tutorials_contents.front_window_title(self)

        if self._modeless:
            self._win = wx.Frame(None, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._win = wx.Dialog(
                getattr(host, "frame", None),
                title=TITLE,
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._surface = self._win
        self._win.SetSize(wx.Size(820, 620))
        self._timer = wx.Timer(self._win)
        self._win.Bind(wx.EVT_TIMER, self._on_tick, self._timer)
        self._build_ui()

    # -- persistence -------------------------------------------------------------

    def _data_dir(self) -> Any:
        from quill.core.paths import data_dir

        return data_dir()

    def _load_progress(self) -> TutorialProgressStore:
        try:
            return load_progress(self._data_dir())
        except Exception:  # noqa: BLE001 - a missing store is an empty one, never a failure
            return TutorialProgressStore()

    def _save_progress(self) -> None:
        try:
            save_progress(self._data_dir(), self._progress)
        except Exception:  # noqa: BLE001 - losing a bookmark in a tutorial is not worth a dialog
            pass

    # -- window furniture --------------------------------------------------------

    def _build_surface_menu_bar(self) -> None:
        wx = self._wx
        menu_bar = wx.MenuBar()
        surface_menu = wx.Menu()
        close_id = wx.NewIdRef()
        surface_menu.Append(close_id, "&Close\tCtrl+W")
        self._win.Bind(wx.EVT_MENU, lambda _e: self._win.Close(), id=close_id)
        menu_bar.Append(surface_menu, "&View")
        from quill.ui.radio import surface_app_menu

        self._menu_id_refs.extend(
            surface_app_menu.install(
                win=self._win,
                host=surface_app_menu.host_of(self),
                menu_bar=menu_bar,
                wx=wx,
                skip=(),
            )
        )
        self._windows.install(self._win, menu_bar)
        self._win.SetMenuBar(menu_bar)
        self._menu_id_refs.append(close_id)

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE or (code == wx.WXK_F4 and event.ControlDown()):
            self._win.Close()
            return
        event.Skip()

    def _on_close(self, event: Any) -> None:
        global _OPEN
        self._timer.Stop()
        self._remember_place()
        if _OPEN is self:
            _OPEN = None
        previous = self._windows.previous_key(self._win)
        self._windows.unregister(self._win)
        if self._announce:
            announce_surface_exit(TITLE, self._announce)
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)

    # -- building ----------------------------------------------------------------

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)
        self._book = wx.Simplebook(self._surface)
        self._contents = wx.Panel(self._book, style=wx.TAB_TRAVERSAL)
        self._lesson = wx.Panel(self._book, style=wx.TAB_TRAVERSAL)
        tutorials_contents.build(self, self._contents)
        self._build_lesson(self._lesson)
        self._book.AddPage(self._contents, "Contents")
        self._book.AddPage(self._lesson, "Lesson")
        root.Add(self._book, 1, wx.EXPAND)
        if not self._modeless:
            self._build_close_button(self._surface, root)
        self._surface.SetSizer(root)
        if self._modeless:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizer(outer)
            from quill.ui.radio import transport_keys

            transport_keys.install(
                self._win,
                self._host,
                wx=wx,
                extra_entries=self._windows.accelerator_entries(),
            )

    def _open_book(self) -> None:
        """The generated document, in the browser.

        The book is rendered from these same lessons, so it cannot say anything
        the window does not -- and a document nobody can open from inside the
        app is a document that does not really ship.
        """
        from quill.apps import radio_help_docs

        try:
            radio_help_docs.open_doc(self._host, "tutorials")
        except Exception:  # noqa: BLE001 - a document that will not open is not a crash
            self._say("The tutorial document could not be opened.")

    def _build_lesson(self, parent: Any) -> None:
        wx = self._wx
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._heading = wx.StaticText(parent, label="")
        sizer.Add(self._heading, 0, wx.ALL, 8)

        self._step_field = wx.TextCtrl(parent, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._step_field.SetName("This step")
        self._step_field.SetHelpText(
            "The step you are on: what to do, why, the keys for it, and what you "
            "should hear. Read-only, so arrow through it freely and copy from it "
            "with Ctrl+C."
        )
        sizer.Add(self._step_field, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._follow = wx.CheckBox(parent, label="Follow &me")
        self._follow.SetValue(self._progress.guide_me)
        self._follow.SetHelpText(
            "While this is ticked, the lesson watches the app and moves you to the "
            "next step by itself once it can see you have done this one. It watches "
            "what changed, not which key you pressed, so any route counts."
        )
        sizer.Add(self._follow, 0, wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self._try_btn = wx.Button(parent, label="&Try it")
        self._try_btn.SetHelpText(
            "Runs this step's command for you, exactly as its key would -- so a "
            "step that opens a window opens it."
        )
        self._next_btn = wx.Button(parent, label="&Next")
        self._next_btn.SetHelpText("Moves to the next step, and reads it.")
        self._back_btn = wx.Button(parent, label="&Back")
        self._back_btn.SetHelpText("Moves to the previous step, and reads it.")
        self._again_btn = wx.Button(parent, label="Say it a&gain")
        self._again_btn.SetHelpText("Reads the current step out again, in full.")
        self._contents_btn = wx.Button(parent, label="&Contents")
        self._contents_btn.SetHelpText("Goes back to the list of tutorials, keeping your place.")
        for button in (
            self._try_btn,
            self._next_btn,
            self._back_btn,
            self._again_btn,
            self._contents_btn,
        ):
            row.Add(button, 0, wx.RIGHT, 6)
        sizer.Add(row, 0, wx.ALL, 8)
        parent.SetSizer(sizer)

        self._try_btn.Bind(wx.EVT_BUTTON, lambda _e: self._try_step())
        self._next_btn.Bind(wx.EVT_BUTTON, lambda _e: self._step_by(1))
        self._back_btn.Bind(wx.EVT_BUTTON, lambda _e: self._step_by(-1))
        self._again_btn.Bind(wx.EVT_BUTTON, lambda _e: self._say_step())
        self._contents_btn.Bind(wx.EVT_BUTTON, lambda _e: self._show_contents())
        self._follow.Bind(wx.EVT_CHECKBOX, lambda _e: self._follow_changed())

    def _build_close_button(self, parent: Any, sizer: Any) -> Any:
        """The modal shape's way out, wired for real.

        A peer window closes with Escape, Ctrl+W, Ctrl+F4 or Alt+F4 and carries
        no Close button at all -- the house rule since the radio windows became
        peers. Embedded in QUILL this is a modal dialog, which needs one, and it
        goes through ``bind_close_button`` because a wx.Dialog answers ID_CANCEL
        for free and a wx.Frame does not.
        """
        wx = self._wx
        button = wx.Button(parent, wx.ID_CLOSE, label="C&lose")
        button.SetHelpText("Closes the tutorials, keeping your place in the lesson.")
        sizer.Add(button, 0, wx.ALL, 8)
        bind_close_button(self._win, button, modeless=False)
        apply_modal_ids(self._win, affirmative_id=button.GetId(), escape_id=button.GetId())
        return button

    # -- lesson behaviour --------------------------------------------------------

    def _start_selected(self, *, whole: bool = False) -> None:
        slug = tutorials_contents.selected_slug(self)
        if not slug:
            self._say("Choose a tutorial first.")
            return
        self.start(slug, whole=whole)

    def start(self, slug: str, *, whole: bool = False) -> None:
        tutorial = catalogue.find(slug)
        if tutorial is None:
            return
        self._tutorial = tutorial
        self._reading_whole = whole
        self._index = min(self._progress.step_of(slug), tutorial.step_count - 1)
        self._book.SetSelection(1)
        self._render()
        # Focus lands in the step field and the screen reader reads it, so
        # opening a lesson deliberately announces nothing (GATE-13: never say
        # what the reader already says). Moving *between* steps does announce,
        # because there the text changes under a focus that did not move -- or
        # under somebody standing in another window doing the step.
        self._wx.CallAfter(self._step_field.SetFocus)
        self._restart_watch()

    def _show_contents(self) -> None:
        self._timer.Stop()
        self._remember_place()
        tutorials_contents.rebuild_tree(self)
        self._book.SetSelection(0)
        self._wx.CallAfter(self._tree.SetFocus)

    def _key_for(self, command_id: str) -> str:
        binding = getattr(self._host, "_binding_for", None)
        if callable(binding):
            try:
                return str(binding(command_id) or "")
            except Exception:  # noqa: BLE001 - a missing binding is "no key", not a failure
                return ""
        return ""

    def _step_text(self) -> str:
        if self._tutorial is None:
            return ""
        if self._reading_whole:
            return render_tutorial(self._tutorial, self._key_for)
        return render_step(self._tutorial, self._index, self._key_for)

    def _render(self) -> None:
        if self._tutorial is None:
            return
        if self._reading_whole:
            self._heading.SetLabel(f"{self._tutorial.title} -- the whole tutorial")
        else:
            self._heading.SetLabel(
                f"{self._tutorial.title} -- step {self._index + 1} of {self._tutorial.step_count}"
            )
        self._step_field.SetValue(self._step_text())
        self._step_field.SetInsertionPoint(0)
        step = None if self._reading_whole else self._tutorial.steps[self._index]
        runnable = bool(step and step.command and self._command_exists(step.command))
        self._try_btn.Enable(runnable)
        self._next_btn.Enable(not self._reading_whole)
        self._back_btn.Enable(not self._reading_whole and self._index > 0)
        self._baseline = tutorial_checks.snapshot(self._host)

    def _command_exists(self, command_id: str) -> bool:
        registry = getattr(self._host, "commands", None)
        getter = getattr(registry, "get", None)
        if not callable(getter):
            return False
        try:
            return getter(command_id) is not None
        except Exception:  # noqa: BLE001 - an unknown command is simply not runnable
            return False

    def _try_step(self) -> None:
        if self._tutorial is None or self._reading_whole:
            return
        step = self._tutorial.steps[self._index]
        registry = getattr(self._host, "commands", None)
        runner = getattr(registry, "run", None)
        if not step.command or not callable(runner):
            self._say("This step has no command to run -- press the keys yourself.")
            return
        try:
            runner(step.command)
        except Exception:  # noqa: BLE001 - the command speaks for itself; this must not fall over
            self._say("That command could not run just now.")

    def _step_by(self, delta: int) -> None:
        if self._tutorial is None:
            return
        target = self._index + delta
        if target < 0:
            self._say("You are on the first step.")
            return
        if target >= self._tutorial.step_count:
            self._finish()
            return
        self._index = target
        self._render()
        self._remember_place()
        self._say_step()

    def _finish(self) -> None:
        if self._tutorial is None:
            return
        self._timer.Stop()
        self._progress.record_finished(self._tutorial.slug)
        self._save_progress()
        closing = self._tutorial.closing or ""
        self._say(f"That is the end of {self._tutorial.title}. {closing}".strip())
        self._show_contents()

    def _remember_place(self) -> None:
        if self._tutorial is None:
            return
        self._progress.record_step(self._tutorial.slug, self._index)
        self._save_progress()

    def _say_step(self) -> None:
        text = self._step_text()
        if not text:
            return
        self._say(text)

    def _say(self, text: str) -> None:
        if self._announce and text:
            self._announce(text)

    # -- follow me ---------------------------------------------------------------

    def _follow_changed(self) -> None:
        self._progress.guide_me = bool(self._follow.GetValue())
        self._save_progress()
        self._restart_watch()

    def _restart_watch(self) -> None:
        self._timer.Stop()
        if self._progress.guide_me and not self._reading_whole and self._tutorial is not None:
            self._timer.Start(_WATCH_MS)

    def _on_tick(self, _event: Any) -> None:
        if self._tutorial is None or self._reading_whole or not self._progress.guide_me:
            self._timer.Stop()
            return
        step = self._tutorial.steps[self._index]
        if not step.check:
            return
        satisfied, sentence = tutorial_checks.evaluate(step.check, self._host, self._baseline)
        if not satisfied:
            return
        # Say what was noticed before the next step, so the two are one thought:
        # "Done: something is playing now." then the step that follows from it.
        self._say(f"Done: {sentence}.")
        self._step_by(1)

    # -- showing -----------------------------------------------------------------

    def raise_window(self, *, slug: str = "") -> None:
        if self._modeless:
            self._windows.activate_title(TITLE)
        if slug:
            self.start(slug)

    def show(self, *, slug: str = "") -> int:
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            self._windows.register(self._win, TITLE, focus=self._filter.SetFocus)
            show_modeless_surface(self._win, TITLE, announce=self._announce)
            if slug:
                self.start(slug)
            else:
                self._say(tutorials_contents.here_hint(self))
            return 0
        if slug:
            self.start(slug)
        result = self._host._show_modal_dialog(self._win, TITLE)
        self._timer.Stop()
        self._win.Destroy()
        global _OPEN
        if _OPEN is self:
            _OPEN = None
        return int(result)
