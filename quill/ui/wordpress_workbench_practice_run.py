"""Starting, stopping and connecting the Practice Site (PRD 15.1; W7; Jeff, 2026-11-23).

A mixin under :class:`quill.ui.wordpress_workbench_bold_practice.WorkbenchPracticeCommands`.
Jeff started the Practice Site and could not find it in File > WordPress >
New Page, because only Connect saved it to Sites. So:

- **Start connects it** once the site answers, and says so once
  (:data:`RUNNING_AND_CONNECTED`). If it cannot, it says why and Connect It as
  Practice Site stays for another try.
- **The first time it connects**, it asks whether to make it the default site
  (No is the default), so New Page starts there while learning. The default
  is never changed silently. The question is asked when you choose Start (or
  Connect), never when the site answers minutes later: a dialog arriving then
  would take focus from whatever you had moved on to (FUX-06). The answer is
  applied, and said, with the connection.
- **The Practice Site list follows the server**: it is refreshed in place
  when the server starts, is ready, stops, fails or exits on its own (FUX-06),
  without moving focus or reading unchanged rows again.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from quill.core.wordpress import sites as st
from quill.core.wordpress.workbench_practice import (
    PRACTICE_NAME,
    clear_password,
    forget_setup,
    is_practice_address,
    read_password,
    site_url,
    start_process,
    stop_process,
    wait_for_site,
)
from quill.ui import wordpress_dialogs as dlg

__all__ = [
    "DEFAULT_TITLE",
    "EXITED",
    "NOW_DEFAULT",
    "RUNNING_AND_CONNECTED",
    "STARTING",
    "STOPPED",
    "WorkbenchPracticeRun",
    "default_question",
]

STARTING = (
    "Starting the Practice Site. The first start can take a few minutes. "
    "QUILL tells you when it is ready."
)
RUNNING_AND_CONNECTED = "The Practice Site is running and connected. It is under Sites."
STOPPED = "The Practice Site has stopped. What is on it stays for the next start."
EXITED = "The Practice Site stopped on its own. What is on it stays. Start it again to use it."
#: Start could not connect: the one-time password was already used.
USED_UP = (
    "The Practice Site is running, but QUILL could not connect it. Its one-time password "
    "was already used. Stop the Practice Site and start it again to get a new one. What "
    "you made on it stays."
)
DEFAULT_TITLE = "Default Site"
#: Added to the connected sentence when the person said Yes to the question.
NOW_DEFAULT = "It is now your default site, so New Page and New Post start there."
#: How often the running server is checked for having exited on its own.
WATCH_MS = 2000


def default_question(current: str) -> str:
    """The default-site question: what Yes changes, what No keeps, where to change it later."""
    return (
        f"When the {PRACTICE_NAME} is connected, should it be your default site? Then New "
        "Page and New Post start there while you learn. "
        f"Your default site now is {current}. No keeps {current}. "
        "You can change it later with File > WordPress > Switch Site, in the editor."
    )


class WorkbenchPracticeRun:
    """The Practice Site server's life: start, stop, connect, the default and the watch."""

    frame: Any
    parent: Any
    commands: Any
    _data_dir: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    show_modal: Callable[[Any, str], int]
    _base: Callable[[], Path]
    _practice: Any
    _practice_lock: Any
    _practice_closed: bool

    # -- state --------------------------------------------------------------------

    def practice_profile(self, store: st.SiteStore | None = None) -> st.SiteProfile | None:
        """The connection under Sites that is the Practice Site, or None."""
        store = store if store is not None else self.commands.sites()
        return next(
            (p for p in store.sites if p.kind == "self_hosted" and is_practice_address(p.site_url)),
            None,
        )

    def practice_process(self, *, quiet: bool = False) -> Any:
        """The running server, or None; one that exited is noticed and let go here.

        *quiet*: the caller is about to start it, so "start it again" is not said.
        """
        running = getattr(self, "_practice", None)
        if running is not None and running.poll() is not None:
            self._let_go(running)
            if not quiet:
                self.say(EXITED)
            return None
        return running

    def practice_ready(self) -> bool:
        """Running and answering: started all the way, not still starting."""
        process = getattr(self, "_practice", None)
        return (
            process is not None
            and process.poll() is None
            and getattr(self, "_practice_ready", None) is process
        )

    def _let_go(self, process: Any) -> bool:
        """Forget *process* as the running server; False when it was not the one."""
        with self._practice_lock:
            if self._practice is not process:
                return False
            self._practice = None
            self._practice_ready = None
        return True

    def practice_changed(self) -> None:
        """Refresh the Practice Site list in place, if it is the list shown (FUX-06)."""
        frame = self.frame
        current = getattr(frame, "current", None) if frame is not None else None
        if current is not None and getattr(current, "key", "") == "practice":
            frame.reload()  # no report: the change was said once, by whoever made it

    # -- start, stop --------------------------------------------------------------

    def practice_start(self, tools: Any, folder: Path) -> None:
        import wx

        def start() -> tuple[Any, str]:
            # Refuses an occupied port; binds loopback only; job-tied to QUILL.
            process = start_process(tools, folder)
            with self._practice_lock:
                if self._practice_closed:
                    stop_process(process)
                    raise RuntimeError("The Workbench closed before the Practice Site started.")
                self._practice = process
            wx.CallAfter(self.practice_changed)  # Running: starting
            try:
                wait_for_site(process, folder)
            except BaseException as error:
                stopped_by_you = not self._let_go(process)
                stop_process(process)
                if stopped_by_you:
                    return None, ""  # Stop was chosen while it started; Stop said so
                return None, str(error) or "The Practice Site could not start."
            return process, ""

        def started(result: tuple[Any, str]) -> None:
            process, failed = result
            if failed:
                self.say(failed)
            elif process is not None and process.poll() is None:
                with self._practice_lock:
                    if self._practice is process:
                        self._practice_ready = process
                self._watch(process)
                self._connect_practice(folder, started=True)
            elif process is not None:
                self._let_go(process)
                self.say(
                    "The Practice Site stopped as it was starting. Start it again or reset it."
                )
            self.practice_changed()

        self.ask_default_first()  # now, while you are here; applied when it connects
        self.say(STARTING)
        self.background("starting the Practice Site", start, started)

    def practice_stop(self, running: Any) -> None:
        self._let_go(running)  # first, so the watch does not take it for an exit
        stop_process(running)
        self.say(STOPPED)
        self.practice_changed()

    def _watch(self, process: Any) -> None:
        """Notice the server exiting on its own (a crash, a killed process)."""
        import wx

        timer = getattr(self, "_practice_timer", None)
        if timer is None:
            timer = self._practice_timer = wx.Timer()
            timer.Bind(wx.EVT_TIMER, lambda _event: self.practice_tick())
        timer.Start(WATCH_MS)

    def practice_tick(self) -> None:
        """One look at the server: say once, and refresh, if it exited on its own."""
        process = getattr(self, "_practice", None)
        timer = getattr(self, "_practice_timer", None)
        if process is None or self._practice_closed:
            if timer is not None:
                timer.Stop()
            return
        if process.poll() is None or not self._let_go(process):
            return
        if timer is not None:
            timer.Stop()
        self.background("tidying up after the Practice Site", lambda: stop_process(process), _none)
        self.say(EXITED)
        self.practice_changed()

    # -- connect ------------------------------------------------------------------

    def _connect_practice(self, folder: Path, *, started: bool = False) -> None:
        """Save the Practice Site under Sites; *started*: Start did this, not Connect."""
        store = self.commands.sites()
        profile = self.practice_profile(store)
        found = read_password(folder)
        if found is None:
            if profile is not None:
                self._connected(profile, started=started, new=False)
            elif not self.practice_ready():
                self.say("The Practice Site is still starting. QUILL connects it once it answers.")
            else:
                forget_setup(folder)  # the next start makes a new password
                self.say(USED_UP)
            return
        username, secret = found
        new = profile is None
        if new and not started:
            self.ask_default_first()  # Connect chosen by hand: ask now, as Start does
        if profile is None:
            used_names = {p.name for p in store.sites}
            name = PRACTICE_NAME
            if name in used_names:
                name = f"{PRACTICE_NAME} (local)"
            suffix = 2
            while name in used_names:
                name = f"{PRACTICE_NAME} (local {suffix})"
                suffix += 1
            profile = st.SiteProfile(st.new_site_id(), name, site_url().rstrip("/"), username)
        elif profile.username != username:
            profile = replace(profile, username=username)
        if store.sites and not store.default_id and store.default is not None:
            store.default_id = store.default.id  # adding a site never moves the default
        try:
            st.save_secret(profile.id, secret)
            store.upsert(profile)
            st.save_sites(store, self._data_dir)
        except Exception as error:  # noqa: BLE001 - Credential Manager, the disk: said plainly
            self.say(
                "The Practice Site is running, but QUILL could not connect it: "
                f"{str(error).rstrip('.') or 'it could not be saved'}. "
                "Choose Connect It as Practice Site, in Tools > Practice Site, to try again."
            )
            return
        handoff_cleared = clear_password(folder)
        self._connected(profile, started=started, new=new, handoff_cleared=handoff_cleared)

    def _connected(
        self, profile: st.SiteProfile, *, started: bool, new: bool, handoff_cleared: bool = True
    ) -> None:
        self.reload_profiles()  # type: ignore[attr-defined]
        self.frame.rebuild_tree()
        name = f"The {PRACTICE_NAME}" if profile.name == PRACTICE_NAME else profile.name
        said = f"{name} is {'running and ' if started else ''}connected. It is under Sites."
        if not handoff_cleared:
            said += (
                " The one-time password file could not be removed. Reset the Practice Site to "
                "remove it."
            )
        store = self.commands.sites()
        wanted = getattr(self, "_practice_wants_default", None)
        self._practice_wants_default = None
        if new and wanted and store.default_id != profile.id:
            store.default_id = profile.id
            st.save_sites(store, self._data_dir)
            said += f" {NOW_DEFAULT}"
        elif store.default_id == profile.id and len(store.sites) == 1:
            said += " It is your default site, because it is your only one."
        self.say(said)

    # -- the default ----------------------------------------------------------------

    def ask_default_first(self) -> None:
        """Before a first connection: ask, by name and defaulting to No, about the default.

        Asked only when it would be new under Sites and another site is the
        default; the answer waits for the connection (``_practice_wants_default``).
        """
        self._practice_wants_default = None
        store = self.commands.sites()
        current = store.default
        if self.practice_profile(store) is not None or current is None:
            return
        self._practice_wants_default = dlg.confirm(
            self.parent,
            self.show_modal,
            title=DEFAULT_TITLE,
            message=default_question(current.listed),
            yes_label="Make It My Default",
            no_label="No",
        )

    def make_practice_default(self, profile_id: str) -> None:
        store = self.commands.sites()
        profile = store.get(profile_id)
        if profile is None:
            self.say("The Practice Site is not connected yet. Starting it connects it.")
            return
        store.default_id = profile.id
        st.save_sites(store, self._data_dir)
        name = f"The {PRACTICE_NAME}" if profile.name == PRACTICE_NAME else profile.name
        self.say(f"{name} is now your default site. New Page and New Post start there.")
        self.practice_changed()


def _none(_result: object) -> None:
    return None
