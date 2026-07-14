"""Resolve a vault note's links and embeds for the in-app preview (wx-free).

The static site export already turns `[[links]]` into anchors and inlines `![[embeds]]`
(``site_export``); this brings the same resolution to the live in-app preview so a writer
hears/sees the *resolved* note, not raw `[[ ]]`/`![[ ]]` markup. Links render as titled,
inert anchors (preview navigation is out of scope); embeds expand inline. Pure and
unit-tested; the wx preview layer calls this only for a note that lives in the open vault.
"""

from __future__ import annotations

from quill.core.vault.render import expand_embeds, render_links_html
from quill.core.vault.resolve import Resolver
from quill.core.vault.vault import Vault


def resolve_for_preview(text: str, vault: Vault, resolver: Resolver, current_path: str) -> str:
    """Return ``text`` with embeds expanded and wikilinks rendered as titled anchors.

    Links point at ``#`` (visible and titled, but inert — the preview is a view, not a
    navigator); embeds are inlined with an announced boundary. Non-link/non-embed text is
    preserved, so the downstream Markdown renderer behaves exactly as before around it.
    """
    expanded = expand_embeds(text, vault, resolver, current_path)
    return render_links_html(expanded, vault, resolver, current_path, url_for=lambda _p, _a: "#")
