"""Native header/footer export for DOCX and RTF (#892 follow-up).

The Header/Footer Builder (``quill/core/header_footer.py``) authors a
three-zone spec from a small token vocabulary (``{title}`` / ``{filename}`` /
``{date}`` / ``{page}``) and QUILL has always drawn it when printing. This
module writes the same spec into the *files* themselves:

* **DOCX** — real ``w:hdr``/``w:ftr`` parts via python-docx section
  headers/footers, with ``{page}`` emitted as a genuine Word ``PAGE`` field
  (so Word renumbers it live) and the Roman style carried on the section's
  page-number format.
* **RTF** — real ``{\\header ...}`` / ``{\\footer ...}`` groups with
  ``{\\field{\\*\\fldinst PAGE}}`` page fields, ``\\titlepg`` for a different
  first page, and ``\\pgnlcrm``/``\\pgnstarts`` for numbering style/start.

Zones are laid out the word-processor way: one line with a centered tab stop
and a right-aligned tab stop, ``left⇥center⇥right``. Static tokens (title,
filename, date) are substituted at export time — they are document identity,
not live fields; ``{page}`` is the one token that must stay live.

wx-free; in scope for strict ``mypy``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.header_footer import HeaderFooterSpec, PageNumberStyle

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass

__all__ = [
    "docx_apply_header_footer",
    "inject_rtf_header_footer",
    "spec_has_content",
]


def spec_has_content(spec: HeaderFooterSpec | None) -> bool:
    """True when the spec would actually draw something (any non-empty zone)."""
    if spec is None:
        return False
    zones = (
        spec.header_left,
        spec.header_center,
        spec.header_right,
        spec.footer_left,
        spec.footer_center,
        spec.footer_right,
        spec.first_page_header_left,
        spec.first_page_header_center,
        spec.first_page_header_right,
        spec.first_page_footer_left,
        spec.first_page_footer_center,
        spec.first_page_footer_right,
    )
    return any(zone.strip() for zone in zones)


class _KeepPage(dict):
    """format_map helper: substitute static tokens, keep ``{page}`` literal."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _substitute_static(template: str, *, title: str, filename: str, date: str) -> str:
    try:
        return template.format_map(_KeepPage(title=title, filename=filename, date=date))
    except (ValueError, KeyError):
        # A malformed template (stray brace) exports as literal text rather
        # than failing the whole save.
        return template


# --------------------------------------------------------------------------- #
# DOCX
# --------------------------------------------------------------------------- #

_PAGE_FIELD_XML = (
    '<w:fldSimple xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    ' w:instr=" PAGE {fmt}\\* MERGEFORMAT "><w:r><w:t>1</w:t></w:r></w:fldSimple>'
)


def _docx_fill_paragraph(paragraph: Any, text: str, *, roman: bool) -> None:
    """Write ``left\\tcenter\\tright`` into a header/footer paragraph.

    The built-in Word Header/Footer styles carry the centered + right tab
    stops, so a single tab-separated line is the native three-zone layout.
    ``{page}`` segments become live PAGE fields.
    """
    from docx.oxml import parse_xml

    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)
    fmt = "\\* ROMAN " if roman else ""
    segments = text.split("{page}")
    for index, segment in enumerate(segments):
        if index:
            paragraph._p.append(parse_xml(_PAGE_FIELD_XML.format(fmt=fmt)))
        if segment:
            paragraph.add_run(segment)


def _docx_zone_line(
    left: str, center: str, right: str, *, title: str, filename: str, date: str
) -> str:
    parts = (
        _substitute_static(left, title=title, filename=filename, date=date),
        _substitute_static(center, title=title, filename=filename, date=date),
        _substitute_static(right, title=title, filename=filename, date=date),
    )
    return "\t".join(parts).rstrip("\t") if any(parts) else ""


def docx_apply_header_footer(
    docx_document: Any,
    spec: HeaderFooterSpec,
    *,
    title: str,
    filename: str,
    date: str,
) -> None:
    """Write the spec into ``docx_document``'s first section, in place.

    No-op for an all-blank spec. Requires python-docx (the caller is already
    on the native docx path when it invokes this).
    """
    if not spec_has_content(spec):
        return
    roman = spec.page_number_style == PageNumberStyle.ROMAN
    section = docx_document.sections[0]
    section.different_first_page_header_footer = bool(spec.first_page_different)
    targets: list[tuple[Any, str, str, str]] = [
        (section.header, spec.header_left, spec.header_center, spec.header_right),
        (section.footer, spec.footer_left, spec.footer_center, spec.footer_right),
    ]
    if spec.first_page_different:
        targets += [
            (
                section.first_page_header,
                spec.first_page_header_left,
                spec.first_page_header_center,
                spec.first_page_header_right,
            ),
            (
                section.first_page_footer,
                spec.first_page_footer_left,
                spec.first_page_footer_center,
                spec.first_page_footer_right,
            ),
        ]
    for container, left, center, right in targets:
        line = _docx_zone_line(left, center, right, title=title, filename=filename, date=date)
        if not line:
            continue
        container.is_linked_to_previous = False
        paragraph = container.paragraphs[0]
        _docx_fill_paragraph(paragraph, line, roman=roman)
    if roman or spec.start_page_number != 1:
        _docx_set_page_number_format(section, roman=roman, start=spec.start_page_number)


def _docx_set_page_number_format(section: Any, *, roman: bool, start: int) -> None:
    """Set ``w:pgNumType`` (format/start) on the section, creating it if needed."""
    from docx.oxml.ns import qn

    sect_pr = section._sectPr
    pg_num = sect_pr.find(qn("w:pgNumType"))
    if pg_num is None:
        from docx.oxml import OxmlElement

        pg_num = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num)
    if roman:
        pg_num.set(qn("w:fmt"), "lowerRoman")
    if start != 1:
        pg_num.set(qn("w:start"), str(max(1, start)))


# --------------------------------------------------------------------------- #
# RTF
# --------------------------------------------------------------------------- #

_RTF_PAGE_FIELD = "{\\field{\\*\\fldinst PAGE}}"
# Centered tab at ~3.25in, right tab at ~6.5in (twips) — the classic letter
# layout the built-in Word header style uses.
_RTF_ZONE_TABS = "\\tqc\\tx4680\\tqr\\tx9360"


def _rtf_zone_group(
    keyword: str,
    left: str,
    center: str,
    right: str,
    *,
    title: str,
    filename: str,
    date: str,
) -> str:
    from quill.io.rtf import _escape_rtf_text

    def _zone(template: str) -> str:
        static = _substitute_static(template, title=title, filename=filename, date=date)
        pieces = [_escape_rtf_text(piece) for piece in static.split("{page}")]
        return _RTF_PAGE_FIELD.join(pieces)

    if not any(part.strip() for part in (left, center, right)):
        return ""
    line = f"{_zone(left)}\\tab {_zone(center)}\\tab {_zone(right)}"
    return "{\\" + keyword + f"\\pard{_RTF_ZONE_TABS} {line}\\par}}"


def inject_rtf_header_footer(
    rtf: str,
    spec: HeaderFooterSpec | None,
    *,
    title: str,
    filename: str,
    date: str,
) -> str:
    """Insert header/footer groups into a ``markdown_to_rtf`` document string.

    The writer's preamble line (``{\\rtf1...`` + font/color tables) ends at the
    first newline; the groups belong immediately after it, before any body
    text. Returns ``rtf`` unchanged for a blank/None spec or an unexpected
    document shape — header/footer export must never break a save.
    """
    if not spec_has_content(spec) or spec is None:
        return rtf
    newline = rtf.find("\n")
    if newline < 0 or not rtf.startswith("{\\rtf1"):
        return rtf
    controls: list[str] = []
    if spec.page_number_style == PageNumberStyle.ROMAN:
        controls.append("\\pgnlcrm")
    if spec.start_page_number != 1:
        controls.append(f"\\pgnstarts{max(1, spec.start_page_number)}\\pgnrestart")
    if spec.first_page_different:
        controls.append("\\titlepg")
    groups = [
        _rtf_zone_group(
            "header",
            spec.header_left,
            spec.header_center,
            spec.header_right,
            title=title,
            filename=filename,
            date=date,
        ),
        _rtf_zone_group(
            "footer",
            spec.footer_left,
            spec.footer_center,
            spec.footer_right,
            title=title,
            filename=filename,
            date=date,
        ),
    ]
    if spec.first_page_different:
        groups += [
            _rtf_zone_group(
                "headerf",
                spec.first_page_header_left,
                spec.first_page_header_center,
                spec.first_page_header_right,
                title=title,
                filename=filename,
                date=date,
            ),
            _rtf_zone_group(
                "footerf",
                spec.first_page_footer_left,
                spec.first_page_footer_center,
                spec.first_page_footer_right,
                title=title,
                filename=filename,
                date=date,
            ),
        ]
    payload = "".join(controls) + "\n" + "\n".join(group for group in groups if group)
    return rtf[: newline + 1] + payload.strip() + "\n" + rtf[newline + 1 :]
