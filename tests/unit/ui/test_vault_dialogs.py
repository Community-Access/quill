"""Seam tests for VaultListDialog (no live wx control tree).

Guards the wx-free logic: the row labels it shows and how activating a row hands
the row's payload to the callback. The ListBox and keyboard wiring are exercised
by hand with a screen reader.
"""

from __future__ import annotations

from quill.ui.vault_dialogs import VaultListDialog


def _dialog(items, on_activate=None):
    return VaultListDialog(wx=object(), heading="Backlinks", items=items, on_activate=on_activate)


def test_labels_are_exposed_in_order() -> None:
    dialog = _dialog([("Note A — context", ("a.md", 0)), ("Note B — context", ("b.md", 12))])
    assert dialog.labels == ["Note A — context", "Note B — context"]


def test_activate_index_hands_payload_to_callback() -> None:
    got: list[object] = []
    dialog = _dialog([("A", ("a.md", 5)), ("B", ("b.md", 9))], on_activate=got.append)
    assert dialog.activate_index(1) is True
    assert got == [("b.md", 9)]


def test_activate_out_of_range_is_false_and_silent() -> None:
    got: list[object] = []
    dialog = _dialog([("A", 1)], on_activate=got.append)
    assert dialog.activate_index(5) is False
    assert dialog.activate_index(-1) is False
    assert got == []


# --- VaultFilterDialog (quick switcher / search) seam ----------------------

from quill.ui.vault_dialogs import VaultFilterDialog  # noqa: E402


def test_filter_dialog_initial_items_from_empty_query() -> None:
    view = VaultFilterDialog(
        wx=object(),
        heading="Go to Note",
        prompt="Type a title:",
        provider=lambda q: [("Alpha", "a.md"), ("Beta", "b.md")] if q == "" else [("Beta", "b.md")],
    )
    assert view.labels == ["Alpha", "Beta"]  # empty query = full list


def test_filter_dialog_update_refilters_and_counts() -> None:
    view = VaultFilterDialog(
        wx=object(),
        heading="Go to Note",
        prompt="Type a title:",
        provider=lambda q: (
            [("Beta", "b.md")] if q == "be" else [("Alpha", "a.md"), ("Beta", "b.md")]
        ),
    )
    assert view.update("be") == 1
    assert view.labels == ["Beta"]


def test_filter_dialog_activate_hands_payload() -> None:
    got: list[object] = []
    view = VaultFilterDialog(
        wx=object(),
        heading="Go to Note",
        prompt="p",
        provider=lambda q: [("Alpha", "a.md")],
        on_activate=got.append,
    )
    assert view.activate_index(0) is True and got == ["a.md"]


def test_filter_dialog_passes_options_to_provider() -> None:
    seen: dict = {}

    def provider(query, options):
        seen.update(options)
        return [("hit", ("x.md", 3))] if query else []

    view = VaultFilterDialog(
        wx=object(),
        heading="Search Vault",
        prompt="Search:",
        provider=provider,
        option_labels=("Regex", "Whole word"),
    )
    assert view.update("fox", {"Regex": True, "Whole word": False}) == 1
    assert seen == {"Regex": True, "Whole word": False}
