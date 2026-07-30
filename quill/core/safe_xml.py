"""Hardened XML parsing for untrusted document inputs.

The stdlib :mod:`xml.etree.ElementTree` parser still expands internal
entities, which leaves it open to "billion laughs" denial-of-service attacks
from crafted files (DOCX, XLSX, ODT, PPTX, EPUB, and generic XML). This module
provides a single ``fromstring`` entry point that disables entity expansion and
external-entity resolution.

When :mod:`defusedxml` is available it is used directly. If it is not
installed, a conservative fallback rejects any document that declares a DTD or
custom entities before falling back to the stdlib parser, so an attack payload
is refused rather than expanded.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as _ET
from typing import cast
from xml.etree.ElementTree import Element

from quill.core.error_codes import CodedError

ParseError = _ET.ParseError

# Matches a DOCTYPE declaration or an explicit ENTITY definition, the building
# blocks of entity-expansion attacks.
_DTD_OR_ENTITY = re.compile(rb"<!(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)


class UnsafeXMLError(CodedError):
    """Raised when untrusted XML uses a forbidden construct (entity expansion
    or external entities)."""

    code = "QUILL-XML-UNSAFE"


try:  # Preferred: defusedxml disables entity expansion and external entities.
    from defusedxml.common import DefusedXmlException
    from defusedxml.ElementTree import fromstring as _defused_fromstring

    _HAVE_DEFUSED = True
except ImportError:  # pragma: no cover - exercised only without defusedxml
    _defused_fromstring = None
    DefusedXmlException = ()  # type: ignore[assignment]
    _HAVE_DEFUSED = False


def _as_bytes(text: str | bytes) -> bytes:
    if isinstance(text, bytes):
        return text
    return text.encode("utf-8", errors="ignore")


def fromstring(text: str | bytes) -> Element:
    """Parse untrusted XML with entity-expansion attacks disabled.

    Raises:
        UnsafeXMLError: if the document declares a DTD or custom entities (when
            defusedxml is unavailable) or defusedxml refuses the document.
        ParseError: if the XML is malformed.
    """
    if _HAVE_DEFUSED and _defused_fromstring is not None:
        try:
            return cast("Element", _defused_fromstring(text))
        except DefusedXmlException as exc:  # entity / external-entity abuse
            raise UnsafeXMLError(
                f"Refused to parse untrusted XML with forbidden constructs: {exc}"
            ) from exc

    # Fallback when defusedxml is not installed: refuse any DTD or entity
    # declaration outright, then parse with the stdlib parser.
    if _DTD_OR_ENTITY.search(_as_bytes(text)):
        raise UnsafeXMLError(
            "Refused to parse untrusted XML containing a DTD or entity declaration."
        )
    return _ET.fromstring(text)
