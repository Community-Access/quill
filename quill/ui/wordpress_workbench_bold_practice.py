"""The Practice Site part of the WordPress Workbench (PRD 15.1; W7).

A mixin under :class:`quill.ui.wordpress_workbench_bold.WorkbenchBoldCommands`:
Tools > Practice Site starts, stops, resets and connects a WordPress site on
this computer only, for learning with nothing at stake. Every request runs
through ``self.background``; a reset is confirmed first. Starting it connects
it, and the server's life is in :mod:`quill.ui.wordpress_workbench_practice_run`.

Its commands are also on the context menu of everything that is the Practice
Site -- its list's rows, its row and its node under Sites, and its own node --
from :mod:`quill.core.wordpress.workbench_practice_actions`; each is greyed,
with a sentence saying why, when it cannot run now (:meth:`practice_refusal`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from quill.core.wordpress import sites as st
from quill.core.wordpress import workbench_practice_material as material
from quill.core.wordpress.workbench_practice import (
    PRACTICE_NAME,
    crossing_warning,
    find_cli,
    is_practice_address,
    missing_words,
    practice_dir,
    reset,
    site_url,
    together_warning,
)
from quill.core.wordpress.workbench_practice_actions import (
    PRACTICE_NODE_KIND,
    PRACTICE_ROW_KIND,
    PRACTICE_SITE_NODE_KIND,
    PRACTICE_VERBS,
    command,
)
from quill.core.wordpress.workbench_rows import WbRow, fact_rows
from quill.core.wordpress.workbench_window_menu import PREFIX
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_workbench_practice_run import WorkbenchPracticeRun

__all__ = ["RESET_WARNING", "SET_UP", "TAKE_AWAY", "WorkbenchPracticeCommands"]

#: The two Practice Site rows for the lesson material, as the lessons name them.
SET_UP = "Set Up the Lesson Material"
TAKE_AWAY = "Take Away the Lesson Material"
#: The chooser's other rows (Ctrl+Alt+P), worded as the context menus word them.
START = "Start the Practice Site"
STOP = "Stop the Practice Site"
CONNECT = "Connect It as Practice Site"
RESET = "Reset the Practice Site"
DEFAULT = "Make It My Default Site"

#: Why a Practice Site command is greyed, said when you reach it.
_RUNNING = "The Practice Site is already running."
_STARTING_NOW = "The Practice Site is starting. QUILL connects it once it answers."
_NOT_RUNNING = "The Practice Site is not running."
_START_FIRST = "The Practice Site is not running. Starting it connects it."
_ALREADY_CONNECTED = "The Practice Site is already connected. It is under Sites."
_STOP_FIRST = "Stop the Practice Site before you reset it."
_NOT_UNDER_SITES = "The Practice Site is not connected yet. Starting it connects it."
_CONNECT_FIRST = "The Practice Site is not connected yet. Choose Connect It as Practice Site first."
_ALREADY_DEFAULT = "The Practice Site is already your default site."

#: What Reset costs, said before it happens: every consequence, and what it spares.
RESET_WARNING = (
    "Reset the Practice Site? This permanently deletes everything on it: every post, "
    "page, upload, comment, user, plugin and setting you made or changed there. QUILL "
    "also forgets its Practice Site connection and removes its stored password from "
    "Windows Credential Manager. Your real WordPress sites are not touched. This cannot "
    "be undone. The next start builds a brand-new site with the starter content."
)


class WorkbenchPracticeCommands(WorkbenchPracticeRun):
    """Tools > Practice Site: start, stop, reset and connect the local site."""

    frame: Any
    parent: Any
    commands: Any
    _data_dir: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    show_modal: Callable[[Any, str], int]
    _base: Callable[[], Path]

    def is_practice(self, site: str) -> bool:
        """Whether the connected site called *site* is the practice site on this computer."""
        profile = self.profile(site)  # type: ignore[attr-defined]
        return profile is not None and is_practice_address(profile.site_url)

    def practice_crossing_ok(
        self,
        action: str,
        sources: list[str],
        targets: list[str],
        *,
        together: bool = False,
        from_practice: bool = False,
    ) -> bool:
        """Ask, by name and defaulting to No, before practice work reaches a real site.

        True when nothing crosses (no practice source, or no real target) or
        the person chose to send it; every cross-site write calls this before
        its own preview, so practice content never leaves by accident.
        *together*: one action changes practice and real sites in the same step
        (Promote to Network, Revoke Everywhere). *from_practice*: the sources
        are practice whatever their name says now (a snapshot taken there).
        """
        practice = [s for s in dict.fromkeys(sources) if from_practice or self.is_practice(s)]
        real = [t for t in dict.fromkeys(targets) if not self.is_practice(t)]
        if together:
            question = together_warning(action, practice, real)
            title = f"{action}: the Practice Site and Real Sites Together"
            yes = f"Change {real[0]} Too" if len(real) == 1 else "Change Them Too"
        else:
            question = crossing_warning(action, practice, real)
            title = f"{action}: from the Practice Site to a Real Site"
            yes = f"Send to {real[0]}" if len(real) == 1 else "Send to Them"
        if not question:
            return True
        return dlg.confirm(
            self.parent, self.show_modal, title=title, message=question, yes_label=yes
        )

    def do_practice(self, _ref: Any, _row: WbRow | None) -> None:
        """Tools > Practice Site > All Practice Site Choices (Ctrl+Alt+P)."""
        tools = find_cli()
        running = self.practice_process()
        if running is None:
            missing = missing_words(tools)
            if missing:
                self.say(missing)
                return
        folder = practice_dir(self._base())
        profile = self.practice_profile()
        if running is None:
            choices = [START, RESET]
        else:
            choices = [STOP] if profile is not None else [CONNECT, STOP]
        if profile is not None and self.commands.sites().default_id != profile.id:
            choices.append(DEFAULT)
        if not material.missing_site_words(folder):  # started once, so it has a WordPress
            choices.append(TAKE_AWAY if material.is_set_up(folder) else SET_UP)
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=PRACTICE_NAME,
            prompt="&Do:",
            rows=choices,
            help_text="A WordPress site on this computer only, for learning with nothing at "
            "stake. Start also connects it, so it is under Sites. Reset puts it back as new; "
            "the lesson material is what the practice tutorials find and fix.",
        )
        if index is None:
            return
        choice = choices[index]
        if choice in (SET_UP, TAKE_AWAY):
            self._lesson_material(folder, set_up=choice == SET_UP)
        elif choice == START:
            self.practice_start(tools, folder)
        elif choice == STOP:
            self.practice_stop(running)
        elif choice == RESET:
            self._reset_practice(folder)
        elif choice == DEFAULT and profile is not None:
            self.make_practice_default(profile.id)
        else:
            self._connect_practice(folder)

    # -- the context menus' commands (workbench_practice_actions) -------------------

    def do_practice_start(self, _ref: Any, _row: WbRow | None) -> None:
        tools = find_cli()
        if self.practice_process(quiet=True) is not None:
            self.say(self.practice_refusal(command("practice_start")) or _RUNNING)
            return
        missing = missing_words(tools)
        if missing:
            self.say(missing)
            return
        self.practice_start(tools, practice_dir(self._base()))

    def do_practice_stop(self, _ref: Any, _row: WbRow | None) -> None:
        running = self.practice_process()
        if running is None:
            self.say(_NOT_RUNNING)
            return
        self.practice_stop(running)

    def do_practice_connect(self, _ref: Any, _row: WbRow | None) -> None:
        if self.practice_process() is None:
            self.say(_START_FIRST)
            return
        self._connect_practice(practice_dir(self._base()))

    def do_practice_default(self, _ref: Any, _row: WbRow | None) -> None:
        profile = self.practice_profile()
        if profile is None:
            self.say(self.practice_refusal(command("practice_default")) or _NOT_UNDER_SITES)
            return
        if self.commands.sites().default_id == profile.id:
            self.say(_ALREADY_DEFAULT)
            return
        self.make_practice_default(profile.id)

    def do_practice_reset(self, _ref: Any, _row: WbRow | None) -> None:
        if self.practice_process() is not None:
            self.say(_STOP_FIRST)
            return
        self._reset_practice(practice_dir(self._base()))

    def practice_refusal(self, command_id: str) -> str:
        """Why a Practice Site command is greyed now ("" when it may run), as a sentence."""
        verb = command_id.removeprefix(PREFIX)
        if verb not in PRACTICE_VERBS:
            return ""
        process = getattr(self, "_practice", None)
        running = process is not None and process.poll() is None
        if verb == "practice_start":
            if running:
                return _RUNNING if self.practice_ready() else _STARTING_NOW
            return missing_words(find_cli())
        if verb == "practice_stop":
            return "" if running else _NOT_RUNNING
        if verb == "practice_connect":
            if not running:
                return _START_FIRST
            if self.practice_profile() is not None:
                return _ALREADY_CONNECTED
            return "" if self.practice_ready() else _STARTING_NOW
        if verb == "practice_reset":
            return _STOP_FIRST if running else ""
        profile = self.practice_profile()
        if profile is None:
            return _CONNECT_FIRST if running else _NOT_UNDER_SITES
        return _ALREADY_DEFAULT if self.commands.sites().default_id == profile.id else ""

    def node_menu_kind(self, ref: Any) -> str:
        """The Practice Site node, and its own node under Sites, have its commands on top."""
        if getattr(ref, "key", "") == "practice" and not getattr(ref, "template", ""):
            return PRACTICE_NODE_KIND
        if getattr(ref, "template", "") == "site" and getattr(ref, "key", "") == "site":
            return PRACTICE_SITE_NODE_KIND if self.is_practice(ref.instance) else "node"
        return "node"

    def practice_rows(self) -> list[WbRow]:
        """Off the UI thread: the Practice Site list, each fact with its commands."""
        tools = find_cli()
        process = getattr(self, "_practice", None)
        alive = process is not None and process.poll() is None
        profile = self.practice_profile()
        default = profile is not None and self.commands.sites().default_id == profile.id
        menus = "from Tools > Practice Site or this list's context menu"
        if not alive:
            running, todo = "no", f"Start it {menus}. Starting it connects it."
        elif not self.practice_ready():
            running, todo = "starting", "Wait. QUILL connects it when it answers."
        elif profile is None:
            running = f"yes, at {site_url()}"
            todo = f"Choose Connect It as Practice Site, {menus}."
        else:
            running = f"yes, at {site_url()}"
            todo = f"Write on it with New Page or New Post. Stop it {menus} when you are done."
        connected = "no"
        if profile is not None:
            connected = f"yes, under Sites as {profile.name}"
            connected += ", your default site" if default else ""
        # "Missing", not "not in this build" / "not bundled": the label names
        # the part, and "What to do" says how to get it back. WordPress ships
        # as its pinned archive, so the row names that when nothing is
        # unpacked -- it said "not bundled" beside a ready site.
        wordpress = tools.wordpress or tools.wordpress_archive
        facts = [
            ("Playground's tool", str(tools.cli) if tools.cli else "Missing"),
            ("Node.js", str(tools.node) if tools.node else "Missing"),
            ("WordPress core", str(wordpress) if tools.has_wordpress else "Missing"),
            ("Running", running),
            ("Connected", connected),
            ("What to do", missing_words(tools) or todo),
        ]
        return [replace(row, kind=PRACTICE_ROW_KIND) for row in fact_rows("", facts)]

    def _reset_practice(self, folder: Path) -> None:
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Reset the Practice Site",
            message=RESET_WARNING,
            yes_label="Reset",
        ):
            return

        def reset_practice() -> None:
            reset(folder)
            store = self.commands.sites()
            profile = self.practice_profile(store)
            if profile is not None:
                st.forget_secret(profile.id)
                store.remove(profile.id)
                st.save_sites(store, self._data_dir)

        def reset_done(_result: None) -> None:
            self._contexts.clear()  # type: ignore[attr-defined]
            self.reload_profiles()  # type: ignore[attr-defined]
            self.frame.rebuild_tree()
            self.say("The Practice Site is new again. Start it to use it.")

        self.background("resetting the Practice Site", reset_practice, reset_done)

    def _lesson_material(self, folder: Path, *, set_up: bool) -> None:
        """Set up or take away the practice lessons' material, after a preview (WP-R-049).

        Files written into the Practice Site's own WordPress folder only; a set-up
        goes into Change History with Take Away as its undo, so Ctrl+Z works.
        """
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title=SET_UP if set_up else TAKE_AWAY,
            message=material.PREVIEW if set_up else material.TAKE_AWAY_PREVIEW,
            yes_label="Set Up" if set_up else "Take Away",
        ):
            return

        def work() -> str:
            return material.set_up(folder) if set_up else material.take_away(folder)

        def done(said: str) -> None:
            history = getattr(self, "history", None)
            if history is not None:
                history.record(
                    Change(
                        PRACTICE_NAME,
                        f"{'Set up' if set_up else 'Took away'} the lesson material on the "
                        f"{PRACTICE_NAME}.",
                        undo=(lambda: material.take_away(folder))
                        if set_up
                        else (lambda: material.set_up(folder)),
                    )
                )
            self.say(said)

        self.background(
            f"{'setting up' if set_up else 'taking away'} the lesson material", work, done
        )
