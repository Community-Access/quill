"""Header/Footer Builder (#892): named presets over a small, fixed token set,
not a general macro/field-code system.

Every header/footer is three zones (left/center/right) built from tokens --
``{title}``, ``{filename}``, ``{date}``, ``{page}``, or literal text -- so a
screen-reader user composes one from a short, learnable vocabulary instead
of a blank canvas. A curated set of named presets covers the common real
requests directly; "Custom" is there for anything else.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "PRESETS",
    "HeaderFooterSpec",
    "PageNumberStyle",
    "page_number_text",
    "render_zone",
]


class PageNumberStyle:
    ARABIC = "arabic"
    ROMAN = "roman"


@dataclass(frozen=True, slots=True)
class HeaderFooterSpec:
    header_left: str = ""
    header_center: str = ""
    header_right: str = ""
    footer_left: str = ""
    footer_center: str = ""
    footer_right: str = ""
    first_page_different: bool = False
    first_page_header_left: str = ""
    first_page_header_center: str = ""
    first_page_header_right: str = ""
    first_page_footer_left: str = ""
    first_page_footer_center: str = ""
    first_page_footer_right: str = ""
    page_number_style: str = PageNumberStyle.ARABIC
    start_page_number: int = 1


def _to_roman(n: int) -> str:
    values = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    parts = []
    for value, symbol in values:
        count, n = divmod(n, value)
        parts.append(symbol * count)
    return "".join(parts)


def page_number_text(n: int, style: str) -> str:
    """The page number as displayed text, per *style* ("arabic" or "roman")."""
    if style == PageNumberStyle.ROMAN:
        return _to_roman(max(1, n))
    return str(n)


def render_zone(
    template: str,
    *,
    title: str = "",
    filename: str = "",
    date: str = "",
    page_number: int = 1,
    page_number_style: str = PageNumberStyle.ARABIC,
) -> str:
    """Substitute ``{title}``/``{filename}``/``{date}``/``{page}`` in *template*."""
    return template.format(
        title=title,
        filename=filename,
        date=date,
        page=page_number_text(page_number, page_number_style),
    )


PRESETS: dict[str, HeaderFooterSpec] = {
    "Blank": HeaderFooterSpec(),
    "Title left, page number right": HeaderFooterSpec(
        header_left="{title}",
        footer_right="{page}",
    ),
    "Filename and date": HeaderFooterSpec(
        footer_left="{filename}",
        footer_right="{date}",
    ),
    "Roman numerals for front matter": HeaderFooterSpec(
        footer_center="{page}",
        page_number_style=PageNumberStyle.ROMAN,
    ),
}
