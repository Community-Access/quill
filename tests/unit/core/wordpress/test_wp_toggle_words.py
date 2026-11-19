"""Review item 29: a toggle row names the one thing it will do."""

from __future__ import annotations

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_toggle_words import toggle_label
from quill.core.workbench.menus import keep_access_key


def _row(kind: str, status: str = "", **raw: object) -> WbRow:
    return WbRow(kind, "Radio", "1", {}, "", status=status, raw=raw)


def test_each_toggle_says_which_way_it_goes() -> None:
    never = lambda _row: False  # noqa: E731
    always = lambda _row: True  # noqa: E731
    assert toggle_label("toggle_plugin", _row("plugin", "active"), never) == "Deactivate"
    assert toggle_label("toggle_plugin", _row("plugin", "inactive"), never) == "Activate"
    assert toggle_label("toggle_feed", _row("feed", "active"), never) == "Deactivate Feed..."
    assert toggle_label("offer_to_ask", _row("ability"), always) == "Stop Offering to Ask the Site"
    assert toggle_label("offer_to_ask", _row("ability"), never) == "Offer to Ask the Site"
    on = _row("menu", auto_add=True)
    assert toggle_label("menu_auto_add", on, never) == "Stop Adding New Pages Automatically..."
    assert toggle_label("publish", _row("item"), never) == ""


def test_the_access_letter_stays_with_the_row() -> None:
    assert keep_access_key("&Activate or Deactivate Feed...", "Deactivate Feed...") == (
        "De&activate Feed..."
    )
    assert keep_access_key("Activate or Deactivate", "Activate") == "Activate"
