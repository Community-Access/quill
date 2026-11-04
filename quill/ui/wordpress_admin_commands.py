"""File > WordPress > Running the Site: comments, and the class that gathers the rest.

Plan: wordpress.md 9.2, 9.8 to 9.10, 9.13, 9.14.

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``. The
Running the Site handlers live in several small mixins, one per area, and
:class:`WordPressAdminCommands` inherits them all, so the commands class needs
only this one name.

The Comments window (9.8): a status (Waiting, Approved, Spam, Trash), the
comments as threads with each reply under its parent, and the moderation an
account is allowed. The count of waiting comments is spoken once a session,
the first time a site is used (:meth:`announce_waiting_once`).
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import comments as cm
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_admin as sa
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_admin_base import WordPressAdminBase
from quill.ui.wordpress_manage_commands import WordPressManageCommands
from quill.ui.wordpress_menu_commands import WordPressMenuCommands
from quill.ui.wordpress_people_commands import WordPressPeopleCommands
from quill.ui.wordpress_structure_commands import WordPressStructureCommands
from quill.ui.wordpress_terms_commands import WordPressTermsCommands

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

#: What each status's moderation buttons do: (label, help, new status, what was done).
_MODERATION: dict[str, tuple[tuple[str, str, str, str], ...]] = {
    "hold": (
        ("&Approve", "Publish the selected comment.", "approve", "approved"),
        ("&Spam", "Mark the selected comment as spam.", "spam", "marked as spam"),
        ("&Trash", "Move the selected comment to the Trash.", "trash", "moved to the Trash"),
    ),
    "approve": (
        ("&Unapprove", "Take the comment off the site; it waits again.", "hold", "unapproved"),
        ("&Spam", "Mark the selected comment as spam.", "spam", "marked as spam"),
        ("&Trash", "Move the selected comment to the Trash.", "trash", "moved to the Trash"),
    ),
    "spam": (
        ("&Not Spam", "It was not spam: it goes back to Waiting.", "hold", "moved to Waiting"),
        ("&Trash", "Move the selected comment to the Trash.", "trash", "moved to the Trash"),
    ),
    "trash": (
        ("&Restore", "Bring the comment back to Waiting.", "hold", "restored to Waiting"),
        ("&Spam", "Mark the selected comment as spam.", "spam", "marked as spam"),
    ),
}


class WordPressAdminCommands(
    WordPressMenuCommands,
    WordPressStructureCommands,
    WordPressPeopleCommands,
    WordPressManageCommands,
    WordPressTermsCommands,
    WordPressAdminBase,
):
    # ------------------------------------------------------------------ #
    # waiting comments, once a session (9.8)

    def announce_waiting_once(self, profile: st.SiteProfile) -> None:
        """Say "Community Radio: 3 comments waiting." the first time a site is used.

        Once per site per session, only when the site's setting allows it and
        only when there are some. A failure is silent: this is a courtesy, and
        the command the person actually asked for reports its own problems.
        """
        said: set[str] = self.__dict__.setdefault("_waiting_said", set())
        if not profile.announce_waiting_comments or profile.id in said:
            return
        said.add(profile.id)
        from quill.core.wordpress import sites as st_

        api = st_.api_for(profile, opener=getattr(self, "_opener", None))

        def done(count: int) -> None:
            if count:
                self.host.announce(cm.waiting_sentence(profile.name, count))

        self.host.run_task(
            "WordPress: counting waiting comments",
            lambda: cm.count_waiting(api),
            done,
            lambda _exc: None,
        )

    # ------------------------------------------------------------------ #
    # the Comments window

    def cmd_comments(self, status: str = "hold") -> None:
        profile = self.admin_site("Comments")
        if profile is not None:
            self._load_comments(profile, status)

    def _load_comments(self, profile: st.SiteProfile, status: str) -> None:
        def work(api: Any, account: wp.Account) -> list[cm.Comment]:
            return cm.list_comments(api, status if sa.can(account, "comments") else "approve")

        self.admin_load(
            profile,
            f"reading comments on {profile.name}",
            None,
            work,
            lambda api, account, found: self._show_comments(profile, api, account, status, found),
        )

    def _show_comments(
        self,
        profile: st.SiteProfile,
        api: Any,
        account: wp.Account,
        status: str,
        comments: list[cm.Comment],
    ) -> None:
        moderator = sa.can(account, "comments")
        if not moderator:
            status = "approve"
        live = list(comments)
        shown: list[tuple[int, cm.Comment]] = cm.threaded(live)

        def rows() -> list[str]:
            shown[:] = cm.threaded(live)
            return cm.thread_rows(shown)

        def at(index: int | None) -> cm.Comment | None:
            return shown[index][1] if index is not None and index < len(shown) else None

        def moderate(new_status: str, said: str) -> Any:
            def run(index: int | None) -> object:
                c = at(index)
                if c is None:
                    return None
                self.site_job(
                    "moderating a comment",
                    lambda: cm.set_status(api, c.id, new_status),
                    lambda _r: f"Comment from {c.author_name} {said}.",
                )
                live.remove(c)
                return rows()

            return run

        def reply(index: int | None) -> object:
            c = at(index)
            if c is None:
                return None
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Reply to {c.author_name}",
                prompt="&Reply:",
                multiline=True,
                help_text=(
                    "Your reply. It is published under your name on the site, under this "
                    "comment. Spelling and dictation work here as in the editor."
                ),
            )
            if text and text.strip():
                self.site_job(
                    "replying to a comment",
                    lambda: cm.reply(api, c, text.strip()),
                    lambda _r: f"Reply to {c.author_name} published on {profile.name}.",
                )
            return None

        def edit(index: int | None) -> object:
            c = at(index)
            if c is None:
                return None
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Edit Comment from {c.author_name}",
                prompt="&Comment:",
                value=c.content,
                multiline=True,
                help_text="The comment's text as the site keeps it. OK saves it on the site.",
            )
            if text is None or text.strip() == c.content.strip():
                return None
            self.site_job(
                "saving a comment",
                lambda: cm.edit_comment(api, c.id, text.strip()),
                lambda _r: f"Comment from {c.author_name} saved on {profile.name}.",
            )
            live[live.index(c)] = replace(c, content=text.strip())
            return rows()

        def open_on_site(index: int | None) -> object:
            c = at(index)
            if c is not None and c.link:
                self.host.open_in_browser(c.link)
            elif c is not None:
                self.host.announce("This comment has no address on the site yet.")
            return None

        def approve_all(_index: int | None) -> object:
            if not live:
                return None
            count = len(live)
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Approve All",
                message=f"Approve all {count} waiting comments on {profile.name}?",
                yes_label=f"Approve {count}",
            ):
                return None
            ids = [c.id for c in live]
            self.site_job(
                "approving comments",
                lambda: cm.set_many(api, ids, "approve"),
                lambda n: f"{n} comments approved on {profile.name}.",
            )
            live.clear()
            return rows()

        def choose_status(_index: int | None) -> object:
            names = [label for _s, label in cm.STATUSES]
            current = [s for s, _l in cm.STATUSES].index(status)
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Show Comments",
                prompt="&Show:",
                rows=names,
                initial=current,
                help_text=(
                    "Which comments to list: waiting for you, approved, spam or in the Trash."
                ),
            )
            if picked is None or cm.STATUSES[picked][0] == status:
                return None
            new_status = cm.STATUSES[picked][0]
            self.after_close(lambda: self._load_comments(profile, new_status))
            return dlg.CLOSE

        def toggle_waiting(_index: int | None) -> object:
            store = self.sites()  # type: ignore[attr-defined]
            fresh = store.get(profile.id) or profile
            turned = not fresh.announce_waiting_comments
            store.upsert(replace(fresh, announce_waiting_comments=turned))
            self.save_sites(store)  # type: ignore[attr-defined]
            self.host.announce(
                f"QUILL will {'now' if turned else 'no longer'} say how many comments are "
                f"waiting when you first use {profile.name} in a session."
            )
            return None

        actions: list[dlg.Action] = []
        if moderator:
            actions.append(
                dlg.Action(
                    "Sho&w...",
                    "Choose which comments to list: Waiting, Approved, Spam or Trash.",
                    choose_status,
                    needs_row=False,
                )
            )
            for label, help_text, new_status, said in _MODERATION[status]:
                actions.append(dlg.Action(label, help_text, moderate(new_status, said)))
            if status == "hold":
                actions.append(
                    dlg.Action(
                        "Approve A&ll...", "Approve every waiting comment at once.", approve_all
                    )
                )
        if status in ("hold", "approve"):
            actions.append(dlg.Action("Re&ply...", "Reply to the selected comment.", reply))
        if moderator:
            actions.append(dlg.Action("&Edit...", "Change the selected comment's text.", edit))
        actions.append(
            dlg.Action("&Open on Site", "Open the comment in your browser.", open_on_site)
        )
        actions.append(
            dlg.Action(
                "Waiting &Count on First Use",
                "Turn on or off the spoken count of waiting comments when you first use this "
                "site in a session.",
                toggle_waiting,
                needs_row=False,
            )
        )
        name = dict(cm.STATUSES)[status]
        purpose = (
            f"{name} comments on {profile.name}: {len(comments)}. Replies sit under the comment "
            "they answer."
        )
        if not moderator:
            purpose += " " + sa.cannot_sentence(profile.name, account, "comments")
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Comments: {name}, {profile.name}",
            purpose=purpose,
            list_label="Co&mments:",
            list_help=(
                "Each row says who, on what, when, and the first words. A reply says whom it "
                "answers and its level."
            ),
            rows=rows(),
            details=lambda i: wp.plain_text(shown[i][1].content),
            actions=actions,
        )
        window.Destroy()
