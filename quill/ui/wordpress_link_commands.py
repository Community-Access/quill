"""Insert > Link to a Page on This Site (wordpress.md 12).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``.
"""

from __future__ import annotations

import html
from typing import Any

from quill.core.wordpress import site as wp
from quill.ui import wordpress_dialogs as dlg


class WordPressLinkCommands:
    host: Any

    def cmd_insert_link(self) -> None:
        found = self.current(command="Link to a Page on This Site")  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> list[wp.ItemSummary]:
            pages = list(wp.list_items(api, "page", statuses=("publish",)))
            posts = list(wp.list_items(api, "post", statuses=("publish",)))
            return pages + posts

        def chosen(items: list[wp.ItemSummary]) -> None:
            items = [i for i in items if i.link and i.id != copy.remote_id]
            if not items:
                self.host.announce(f"{profile.name} has no published pages or posts to link to.")
                return
            index = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Link to a Page on This Site",
                prompt="&Page or post:",
                rows=[f"{i.title or 'untitled'}, {i.kind}" for i in items],
                help_text=(
                    "The published pages and posts on this site. The link goes in at the "
                    "caret, using the selected text, or the page's title when nothing is selected."
                ),
            )
            if index is None:
                return
            item = items[index]
            words = self.host.selected_text().strip() or item.title or item.link
            self.host.insert_text(link_markup(words, item.link, copy.text_format))
            self.host.announce(f"Link to '{item.title or item.link}' inserted.")

        self.background(f"listing what {profile.name} has published", work, chosen)  # type: ignore[attr-defined]


def link_markup(words: str, url: str, text_format: str) -> str:
    """A link in the document's own format: Markdown, or HTML."""
    if text_format == "html":
        return f'<a href="{html.escape(url, quote=True)}">{html.escape(words, quote=False)}</a>'
    safe = words.replace("[", r"\[").replace("]", r"\]")
    return f"[{safe}]({url.replace(' ', '%20').replace(')', '%29')})"
