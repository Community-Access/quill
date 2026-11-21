"""The GitHub Workbench key cards, print and braille, cannot drift (GH-R-115)."""

from __future__ import annotations

from quill.tools import build_github_key_card as card


def test_the_committed_cards_match_the_key_table() -> None:
    for path, wanted in card.outputs().items():
        assert path.read_text(encoding="utf-8") == wanted, (
            f"{path.name} drifted. Regenerate with: "
            "python -m quill.tools.build_github_key_card --write"
        )


def test_every_workbench_key_is_on_both_cards() -> None:
    from quill.core.github.workbench_window_menu import WORKBENCH_KEYS

    html = card.render_html()
    braille = card.render_braille()
    for key in WORKBENCH_KEYS.values():
        assert f"<td>{key}</td>" in html, key
        assert f"{key}: " in braille, key


def test_the_braille_card_fits_a_braille_page() -> None:
    braille = card.render_braille()
    braille.encode("ascii")  # nothing a braille-ready file cannot carry
    pages = braille.split("\x0c\n")
    for page in pages:
        lines = page.splitlines()
        assert len(lines) <= card.LINES
        assert all(len(line) <= card.CELLS for line in lines)
        assert lines[0].strip()  # no page starts blank


def test_the_print_card_is_accessible_html() -> None:
    html = card.render_html()
    assert '<html lang="en">' in html and f"<title>{card.TITLE}</title>" in html
    assert "<main>" in html and '<th scope="col">Key</th>' in html
    assert html.count("<caption>") == html.count("<table>")
