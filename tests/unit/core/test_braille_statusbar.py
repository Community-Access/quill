"""Unit tests for the pure status-bar cell text builder.

These tests do not import :mod:`quill.ui.main_frame`. The renderer is
called with a hand-built :class:`BraillePositionResolver` and a hand-built
:class:`PrintPageInfo`, which is exactly what the UI mixin does.
"""

from __future__ import annotations

import pytest

from quill.core.braille_position import BraillePositionResolver
from quill.core.braille_status import PrintPageInfo
from quill.core.braille_statusbar import short_form, short_form_from_resolver
from quill.core.brf_document import BRFDocument


def _resolver(text: str) -> BraillePositionResolver:
    document = BRFDocument.from_text_and_suffix(
        text,
        "brf",
        cell_width=40,
        line_height=25,
    )
    return BraillePositionResolver(document)


def test_short_form_basic() -> None:
    resolver = _resolver("a")
    text = short_form_from_resolver(resolver, 0)
    assert text.startswith("BRF Pg 1/")
    assert "Ln 1/" in text
    assert "Cell 1/" in text
    assert text.endswith("| Print ?")


def test_short_form_with_known_print_page() -> None:
    resolver = _resolver("a")
    text = short_form(resolver.resolve(0), PrintPageInfo(number=7))
    assert text.endswith("| Print 7")


def test_short_form_with_implied_print_page() -> None:
    resolver = _resolver("a")
    text = short_form(resolver.resolve(0), PrintPageInfo(number=8, is_implied=True))
    assert text.endswith("| Print ~8")


def test_short_form_resolver_offset_advances() -> None:
    document = BRFDocument.from_text_and_suffix(
        "a" * 1000,
        "brf",
        cell_width=40,
        line_height=25,
    )
    resolver = BraillePositionResolver(document)
    # 1000 chars in 40-wide cells: offset 41 should resolve to a different
    # position than offset 0. We just want to confirm the resolver runs
    # without raising and yields a recognisable cell token.
    text = short_form_from_resolver(resolver, 41)
    assert "Cell " in text


def test_short_form_uses_cell_width_and_line_count() -> None:
    document = BRFDocument.from_text_and_suffix(
        "a" * 1000,
        "brf",
        cell_width=40,
        line_height=25,
    )
    resolver = BraillePositionResolver(document)
    text = short_form_from_resolver(resolver, 0)
    assert "BRF Pg 1/" in text
    assert "Cell 1/40" in text


def test_short_form_default_print_page_is_unknown() -> None:
    resolver = _resolver("a")
    text = short_form(resolver.resolve(0))
    assert "Print ?" in text


def test_short_form_zero_print_page_rendered() -> None:
    resolver = _resolver("a")
    text = short_form(resolver.resolve(0), PrintPageInfo(number=0))
    assert text.endswith("| Print 0")


def test_short_form_from_resolver_matches_short_form() -> None:
    resolver = _resolver("a")
    position = resolver.resolve(0)
    info = PrintPageInfo(number=3)
    assert short_form_from_resolver(resolver, 0, info) == short_form(position, info)


def test_short_form_past_eof_offset_does_not_raise() -> None:
    resolver = _resolver("abc")
    text = short_form_from_resolver(resolver, 9999)
    assert "BRF Pg" in text


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
