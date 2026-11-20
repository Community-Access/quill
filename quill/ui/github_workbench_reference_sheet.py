"""Alt+Enter on a GitHub reference in a document: its sheet (GH-R-036, decision 23).

The editor (QUILL or QUILL Lite, through :mod:`quill.ui.github_editor_line`)
opens the Workbench with ``properties:<json [kind, ident]>``, built by
:func:`quill.core.github.editor_line.sheet_request`. This opens that object's
Properties sheet, the same one Alt+Enter opens on its row in the Workbench.

A ``#42`` is kind ``"item"``: GitHub alone knows whether 42 is an issue or a
pull request, so the item is read first (``fetch_item``) and its own row
chooses the sheet, as a list row would.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = ["open_reference_sheet"]


def open_reference_sheet(window: Any, payload: str) -> None:
    """Open the sheet *payload* names, on the Workbench *window*'s provider."""
    from quill.core.github.sheet_catalog import SHEETS, Target, target_for

    try:
        kind, ident = json.loads(payload)
        ident = {str(key): str(value) for key, value in dict(ident).items()}
    except (TypeError, ValueError):
        window._say("That GitHub reference could not be read.")
        return
    if kind == "item":

        def work() -> Any:
            return window.items.fetch_item(ident["repo"], int(ident["number"]))

        def done(item: Any) -> None:
            target = target_for(item, ident["repo"])
            if target is None:
                window._say(f"{ident['repo']}#{ident['number']} has no Properties sheet.")
                return
            window._open_one(window._with_me(target))

        window._background(f"find {ident['repo']}#{ident['number']}", work, done)
        return
    if kind not in SHEETS:
        window._say("This kind of GitHub reference has no Properties sheet yet.")
        return
    window._open_one(window._with_me(Target(str(kind), ident)))
