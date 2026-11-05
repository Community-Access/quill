"""Site-wide Find and Replace (wordpress.md 9.5).

The same machinery as Fix in Bulk, for words rather than problems: a phone
number that changed, a person who left, a renamed programme. It lists every
match with its sentence, lets each be included or skipped, replaces in
``batch/v1`` requests after one named confirmation, and keeps what each page
said before, so Undo Site Fix puts it all back. A block's settings comment
(``<!-- wp:... -->``) is left alone unless the person asks.

Split from :mod:`quill.ui.wordpress_site_check_commands` for size.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site_fixes as sf
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_site_check_commands import Key, WordPressSiteCheckCommands, _pages, plain

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class WordPressFindReplaceCommands(WordPressSiteCheckCommands):
    # ------------------------------------------------------------------ #
    # Site-wide Find and Replace

    def cmd_site_find_replace(self) -> None:
        profile = self._site_for("Site-wide Find and Replace")
        if profile is None:
            return
        find = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Site-wide Find and Replace",
            prompt="&Find:",
            help_text="The words to find in every page and post on the site, published or not.",
        )
        if not find:
            return
        replace = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Site-wide Find and Replace",
            prompt="&Replace with:",
            help_text="What to put in their place. Leave it empty to remove the words.",
        )
        if replace is None:
            return
        mode = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Site-wide Find and Replace",
            prompt="&How to match:",
            rows=[
                "Plain words, any case",
                "Plain words, matching case",
                "A pattern (regular expression), any case",
                "A pattern (regular expression), matching case",
            ],
            help_text="Plain words is right almost every time. A pattern is for the technical.",
        )
        if mode is None:
            return
        options = sf.FindOptions(find, replace, regex=mode >= 2, match_case=mode % 2 == 1)
        try:
            options.compiled()
        except sf.PatternError as exc:
            self.host.announce(plain(exc))
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        search = "" if options.regex else find
        self.background(  # type: ignore[attr-defined]
            f"searching {profile.name}",
            lambda: sf.fetch_items(api, statuses=sf.ALL_STATUSES, search=search),
            lambda pages: self._show_matches(profile, options, pages),
        )

    def _show_matches(
        self, profile: st.SiteProfile, options: sf.FindOptions, pages: list[sf.SitePage]
    ) -> None:
        entries: list[list[Any]] = []  # [page, match, included]
        hidden = 0

        def scan(opts: sf.FindOptions) -> None:
            nonlocal hidden
            entries.clear()
            hidden = 0
            for page in pages:
                found, more = sf.find_matches(page.content, opts)
                hidden += more
                entries.extend([page, m, True] for m in found)

        scan(options)
        if not entries and not hidden:
            self.host.announce(f"No matches for '{options.find}' on {profile.name}.")
            return
        page_count = len({(e[0].kind, e[0].item_id) for e in entries})
        if entries:
            matches = f"{len(entries)} match" + ("" if len(entries) == 1 else "es")
            self.host.announce(f"{matches} on {_pages(page_count)} on {profile.name}.")
        else:
            self.host.announce(
                f"'{options.find}' is only inside block settings on {profile.name}, which "
                "Find and Replace leaves alone unless you choose Include Block Settings."
            )

        def rows() -> list[str]:
            return [
                f"{'Included' if inc else 'Skipped'}: {page.title or '(untitled)'}: {m.context}"
                for page, m, inc in entries
            ]

        def toggle(index: int | None) -> object:
            if index is None or index >= len(entries):
                return None
            entries[index][2] = not entries[index][2]
            return rows()

        def set_all(value: bool) -> Callable[[int | None], object]:
            def run(_index: int | None) -> object:
                for entry in entries:
                    entry[2] = value
                return rows()

            return run

        def with_settings(_index: int | None) -> object:
            scan(dataclasses.replace(options, include_block_settings=True))
            return rows()

        def replace(_index: int | None) -> object:
            return self._replace_chosen(profile, options, entries)

        actions = [
            dlg.Action("&Include or Skip", "Include or skip the selected match.", toggle),
            dlg.Action("Include &All", "Include every match.", set_all(True), needs_row=False),
            dlg.Action("S&kip All", "Skip every match.", set_all(False), needs_row=False),
        ]
        if hidden:
            actions.append(
                dlg.Action(
                    "Include &Block Settings",
                    f"Also list the {hidden} matches inside block settings comments. Changing "
                    "those can break a block.",
                    with_settings,
                    needs_row=False,
                )
            )
        actions.append(
            dlg.Action(
                "&Replace...",
                "Replace every included match, after one confirmation.",
                replace,
                needs_row=False,
            )
        )
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Site-wide Find and Replace",
            purpose=(
                f"Every match for '{options.find}' on {profile.name}, with its sentence. "
                "All are included to start with."
            ),
            list_label="&Matches:",
            list_help="Included or skipped, the page, and the sentence with the match in brackets.",
            rows=rows(),
            actions=actions,
        )
        window.Destroy()

    def _replace_chosen(
        self, profile: st.SiteProfile, options: sf.FindOptions, entries: list[list[Any]]
    ) -> object:
        chosen: dict[Key, list[sf.Match]] = {}
        expected: dict[Key, str | None] = {}
        for page, match, included in entries:
            if included:
                key = (page.kind, page.item_id)
                chosen.setdefault(key, []).append(match)
                expected[key] = page.content
        if not chosen:
            self.host.announce("Nothing is included, so nothing was replaced.")
            return None
        count = sum(len(m) for m in chosen.values())
        pages = len(chosen)
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title=f"Replace on {profile.name}",
            message=(
                f"Replace {count} matches of '{options.find}' with '{options.replace}' on "
                f"{_pages(pages)} on {profile.name}? A copy of each page as it is now is kept "
                "on this computer, so Undo Site Fix can put them all back."
            ),
            yes_label=f"Replace in {_pages(pages).title()}",
        ):
            return None
        self._send_site_fix(
            profile,
            f"Replaced '{options.find}' with '{options.replace}'",
            expected,
            lambda page: sf.apply_matches(page.content, chosen[(page.kind, page.item_id)]),
            verb="Changed",
        )
        return dlg.CLOSE
