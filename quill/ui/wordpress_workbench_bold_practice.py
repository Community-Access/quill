"""The Practice Site part of the WordPress Workbench (PRD 15.1; W7).

A mixin under :class:`quill.ui.wordpress_workbench_bold.WorkbenchBoldCommands`:
Tools > Practice Site starts, stops, resets and connects a WordPress site on
this computer only, for learning with nothing at stake. Every request runs
through ``self.background``; a reset is confirmed first.
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
    crossing_warning,
    find_cli,
    is_practice_address,
    missing_words,
    practice_dir,
    read_password,
    reset,
    site_url,
    start_process,
    stop_process,
    together_warning,
    wait_for_site,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_dialogs as dlg

__all__ = ["RESET_WARNING", "WorkbenchPracticeCommands"]

#: What Reset costs, said before it happens: every consequence, and what it spares.
RESET_WARNING = (
    "Reset the Practice Site? This permanently deletes everything on it: every post, "
    "page, upload, comment, user, plugin and setting you made or changed there. QUILL "
    "also forgets its Practice Site connection and removes its stored password from "
    "Windows Credential Manager. Your real WordPress sites are not touched. This cannot "
    "be undone. The next start builds a brand-new site with the starter content."
)


class WorkbenchPracticeCommands:
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
        tools = find_cli()
        running = getattr(self, "_practice", None)
        if running is not None and running.poll() is not None:
            with self._practice_lock:  # type: ignore[attr-defined]
                if self._practice is running:  # type: ignore[attr-defined]
                    self._practice = None  # type: ignore[attr-defined]
            running = None
            self.say("The Practice Site stopped. Its saved data is still there.")
        if running is None:
            missing = missing_words(tools)
            if missing:
                self.say(missing)
                return
        choices = (
            ["Connect It as Practice Site", "Stop the Practice Site"]
            if running is not None
            else ["Start the Practice Site", "Reset the Practice Site"]
        )
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=PRACTICE_NAME,
            prompt="&Do:",
            rows=choices,
            help_text="A WordPress site on this computer only, for learning with nothing at "
            "stake. Reset puts it back as new.",
        )
        if index is None:
            return
        choice = choices[index]
        folder = practice_dir(self._base())
        if choice.startswith("Start"):

            def start() -> Any:
                # Refuses an occupied port; binds loopback only; job-tied to QUILL.
                process = start_process(tools, folder)
                with self._practice_lock:  # type: ignore[attr-defined]
                    if self._practice_closed:  # type: ignore[attr-defined]
                        stop_process(process)
                        raise RuntimeError("The Workbench closed before the Practice Site started.")
                    self._practice = process  # type: ignore[attr-defined]
                try:
                    wait_for_site(process, folder)
                except BaseException:
                    with self._practice_lock:  # type: ignore[attr-defined]
                        if self._practice is process:  # type: ignore[attr-defined]
                            self._practice = None  # type: ignore[attr-defined]
                    stop_process(process)
                    raise
                return process

            def started(process: Any) -> None:
                if process is not None and process.poll() is None:
                    self.say(
                        f"The Practice Site is running at {site_url()}. Connect it in a moment."
                    )
                else:
                    self.say(
                        "The Practice Site stopped as it was starting. Start it again or reset it."
                    )

            self.background("starting the Practice Site", start, started)
        elif choice.startswith("Stop"):
            stop_process(running)
            with self._practice_lock:  # type: ignore[attr-defined]
                if self._practice is running:  # type: ignore[attr-defined]
                    self._practice = None  # type: ignore[attr-defined]
            self.say("The practice site has stopped.")
        elif choice.startswith("Reset"):
            if dlg.confirm(
                self.parent,
                self.show_modal,
                title="Reset the Practice Site",
                message=RESET_WARNING,
                yes_label="Reset",
            ):

                def reset_practice() -> None:
                    reset(folder)
                    store = self.commands.sites()
                    local_url = site_url().rstrip("/")
                    profile = next(
                        (
                            p
                            for p in store.sites
                            if p.kind == "self_hosted" and p.site_url.rstrip("/") == local_url
                        ),
                        None,
                    )
                    if profile is not None:
                        st.forget_secret(profile.id)
                        store.remove(profile.id)
                        st.save_sites(store, self._data_dir)

                def reset_done(_result: None) -> None:
                    self._contexts.clear()  # type: ignore[attr-defined]
                    self.reload_profiles()  # type: ignore[attr-defined]
                    self.frame.rebuild_tree()
                    self.say("The practice site is new again. Start it to use it.")

                self.background(
                    "resetting the Practice Site",
                    reset_practice,
                    reset_done,
                )
        else:
            self._connect_practice(folder)

    def _connect_practice(self, folder: Path) -> None:
        store = self.commands.sites()
        local_url = site_url().rstrip("/")
        profile = next(
            (
                p
                for p in store.sites
                if p.kind == "self_hosted" and p.site_url.rstrip("/") == local_url
            ),
            None,
        )
        found = read_password(folder)
        if found is None:
            if profile is not None:
                self.reload_profiles()  # type: ignore[attr-defined]
                self.frame.rebuild_tree()
                self.say(f"{profile.name} is already connected. It is under Sites.")
                return
            self.say("The practice site is still starting. Try Connect again in a moment.")
            return
        username, secret = found
        if profile is None:
            used_names = {p.name for p in store.sites}
            name = PRACTICE_NAME
            if name in used_names:
                name = f"{PRACTICE_NAME} (local)"
            suffix = 2
            while name in used_names:
                name = f"{PRACTICE_NAME} (local {suffix})"
                suffix += 1
            profile = st.SiteProfile(st.new_site_id(), name, local_url, username)
        elif profile.username != username:
            profile = replace(profile, username=username)
        st.save_secret(profile.id, secret)
        store.upsert(profile)
        st.save_sites(store, self._data_dir)
        handoff_cleared = clear_password(folder)
        self.reload_profiles()  # type: ignore[attr-defined]
        self.frame.rebuild_tree()
        if handoff_cleared:
            self.say(f"{profile.name} is connected. It is under Sites.")
        else:
            self.say(
                f"{profile.name} is connected. It is under Sites, but the one-time password "
                "file could not be removed. Reset the practice site to remove it."
            )
