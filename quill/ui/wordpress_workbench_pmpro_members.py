"""Members of This Level: one Paid Memberships Pro level's members, as a list (complete.md 2.3).

A mixin of :class:`quill.ui.wordpress_workbench_membership_commands.WorkbenchMembershipCommands`.
The reading is wx-free in :mod:`quill.core.wordpress.workbench_pmpro_members`,
which says why it asks about each person in turn (PMPro has no route that
lists a level's members).

On a row of Memberships > Membership Levels: first the site's count of
people, then a question naming the level, the site and how many people it
will ask about, saying plainly when that is slow. The read runs in the
background; choosing the command again stops it and keeps what it found. The
outcome is said once, then the members open in a list window whose Copy Email
Addresses puts every address, a semicolon between, on the clipboard.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_pmpro_members as pm
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_dialogs as dlg

__all__ = ["WorkbenchPmproMembers"]


class WorkbenchPmproMembers:
    """Members of This Level, for the Workbench provider."""

    frame: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]

    def _members_running(self) -> threading.Event | None:
        stop: threading.Event | None = self.__dict__.get("_members_stop")
        return stop if stop is not None and not stop.is_set() else None

    def do_level_members(self, _ref: Any, row: WbRow | None) -> None:
        running = self._members_running()
        if running is not None:
            running.set()
            self.say("Stopping the members list; the members found so far are kept.")
            return
        if row is None or row.kind != "pmpro" or row.subkind != "level" or not row.key.isdigit():
            self.say("Members of This Level works on a row of Memberships > Membership Levels.")
            return
        site, level, level_id = row.site, row.title, int(row.key)
        api = self.ctx(site).api

        def counted(people: int | None) -> None:
            if not dlg.confirm(
                self.parent,
                self.show_modal,
                title="Members of This Level",
                message=pm.ask_words(level, site, people),
                yes_label="Find Members",
            ):
                return
            stop = threading.Event()
            self.__dict__["_members_stop"] = stop

            def work() -> pm.MembersFound:
                try:
                    return pm.find_members(api, level_id, level, site, people=people, stop=stop)
                finally:
                    stop.set()  # finished, stopped or failed: the next run starts afresh

            def done(found: pm.MembersFound) -> None:
                self.say(found.sentence())
                if found.members:
                    self._show_members(found)

            self.background(f"finding the members of {level} on {site}", work, done)

        self.background(f"counting the people on {site}", lambda: pm.count_people(api), counted)

    def _show_members(self, found: pm.MembersFound) -> None:
        members = found.members

        def copy(_index: int | None) -> object:
            addresses = found.emails()
            if not addresses:
                self.say(f"None of the members of {found.level} has an email address shown.")
                return None
            self.frame.copy_text(addresses)
            return None

        window = dlg.show_list_window(
            self.parent,
            self.show_modal,
            title=f"Members of {found.level} - {found.site}",
            purpose=found.sentence(),
            list_label="&Members:",
            list_help="Each person who holds this level now: their name, email address and "
            "when the membership started.",
            rows=[member.line() for member in members],
            details=lambda index: members[index].line(),
            actions=[
                dlg.Action(
                    "&Copy Email Addresses",
                    "Every member's email address, a semicolon between, for the To box of a "
                    "message.",
                    copy,
                    needs_row=False,
                )
            ],
        )
        window.Destroy()
