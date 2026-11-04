"""WordPress.org's Pattern Directory in Insert Block, and pattern categories (wordpress.md 9.15).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`.

* Insert Block gains **WordPress.org Patterns...** when the site offers the
  directory route. Each found pattern is described in words, with its blocks
  listed and its pictures counted, before it goes in; inserting is the same
  ``_insert_choice`` every other pattern takes, so one Undo removes it.
* Synced Patterns asks **which category** first when the site groups its
  patterns, then shows only those.

The directory is fetched through the site's own route, so QUILL reaches no
host but the site.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import block_catalog as bc
from quill.core.wordpress import pattern_directory as pd
from quill.core.wordpress import site_features as sf
from quill.core.wordpress.api import WordPressApiError
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_api_site_base import WordPressApiSiteBase

if TYPE_CHECKING:
    from quill.core.wordpress import site_library as lib
    from quill.core.wordpress import sites as st


class WordPressPatternCommands(WordPressApiSiteBase):
    # ------------------------------------------------------------------ #
    # The Pattern Directory, from Insert Block

    def index_or_none(self, profile: st.SiteProfile, api: Any) -> sf.SiteIndex | None:
        """The site's index for Insert Block's extras; None when it will not say (off-thread)."""
        try:
            return self.site_facts(profile, api)[0]
        except WordPressApiError:
            return None

    def directory_actions(self, profile: st.SiteProfile, index: sf.SiteIndex | None) -> list[Any]:
        """Insert Block's directory button, only when the site offers the directory."""
        if index is None or not index.has_route(pd.DIRECTORY_ROUTE):
            return []

        def search(_row: int | None) -> object:
            self.after_close(lambda: self.search_pattern_directory(profile))  # type: ignore[attr-defined]
            return dlg.CLOSE

        return [
            dlg.Action(
                "&WordPress.org Patterns...",
                "Search the free patterns on WordPress.org, each described before it goes in.",
                search,
                needs_row=False,
            )
        ]

    def search_pattern_directory(self, profile: st.SiteProfile) -> None:
        words = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="WordPress.org Patterns",
            prompt="&Search for:",
            help_text=(
                "Words for the pattern you want, such as hero, pricing or contact. The site "
                "asks WordPress.org's Pattern Directory for you."
            ),
        )
        if words is None or not words.strip():
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def found(patterns: list[pd.DirectoryPattern]) -> None:
            if not patterns:
                self.host.announce(f"No WordPress.org patterns match {words.strip()}.")
                return
            self.host.announce(
                f"{len(patterns)} WordPress.org {'pattern' if len(patterns) == 1 else 'patterns'} "
                f"for {words.strip()}."
            )
            self._choose_directory_pattern(patterns)

        self.background(  # type: ignore[attr-defined]
            "searching WordPress.org's patterns", lambda: pd.search(api, words), found
        )

    def _choose_directory_pattern(self, patterns: list[pd.DirectoryPattern]) -> None:
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="WordPress.org Patterns",
            prompt="&Patterns:",
            rows=[p.row() for p in patterns],
            help_text="Each pattern's name and what it is for. Its blocks are listed next.",
        )
        if index is None:
            return
        pattern = patterns[index]
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Insert Pattern",
            message=pd.describe(pattern) + " Insert it after the block the caret is in?",
            yes_label=f"Insert {pattern.title}",
        ):
            return
        choice = bc.InsertChoice(
            "pattern",
            f"wordpress-org/{pattern.id}",
            pattern.title,
            pattern.description,
            content=pattern.content,
        )
        self._insert_choice(choice)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Pattern categories, for Synced Patterns

    def patterns_by_category(
        self,
        profile: st.SiteProfile,
        api: Any,
        patterns: list[lib.Pattern],
        uses: dict[int, list[lib.Use]],
        categories: pd.PatternCategories,
    ) -> None:
        """Ask which category when the site groups its patterns, then show those."""
        groups = categories.choices([p.id for p in patterns])
        if len(groups) > 1:
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Synced Patterns",
                prompt="&Category:",
                rows=[row for row, _ids in groups],
                help_text=(
                    "Show every pattern, or only one category's. Each row says how many "
                    "patterns it holds."
                ),
            )
            if picked is None:
                return
            wanted = set(groups[picked][1])
            patterns = [p for p in patterns if p.id in wanted]
        self._show_patterns(profile, api, patterns, uses)  # type: ignore[attr-defined]
