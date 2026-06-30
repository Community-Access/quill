"""Read-only Google Docs document model and projection (wx-free, strict-typed).

This is the inbound, read-only heart of "open a Google document into the
editor": it turns a Google Docs URL or id into a document id, and turns a Google
Docs API ``documents.get`` payload into a text-first projection suitable for the
plain-text editor. It performs no network access and no content-send: there is
deliberately no write/update/create path here.

The actual OAuth flow, Drive listing, and the network ``documents.get`` call
live in a separate slice (see
``docs/design/publishing/google-docs-drive-inbound-integration-points-2026-06-29.md``)
and require a Google OAuth client plus an approved network-egress entry. Keeping
the parsing and projection pure makes them fully unit-testable without any of
that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A Google file id is a run of URL-safe base64-ish characters. Docs ids are
# long; require a reasonable minimum length so we do not treat a short word as
# an id when no URL structure is present.
_ID_CHARS = r"[A-Za-z0-9_-]"
_BARE_ID_RE = re.compile(rf"^{_ID_CHARS}{{20,}}$")
_PATH_ID_RE = re.compile(rf"/d/(?P<id>{_ID_CHARS}+)")
_QUERY_ID_RE = re.compile(rf"[?&]id=(?P<id>{_ID_CHARS}+)")

_HEADING_PREFIXES: dict[str, str] = {
    "TITLE": "# ",
    "SUBTITLE": "## ",
    "HEADING_1": "# ",
    "HEADING_2": "## ",
    "HEADING_3": "### ",
    "HEADING_4": "#### ",
    "HEADING_5": "##### ",
    "HEADING_6": "###### ",
}


@dataclass(frozen=True, slots=True)
class GoogleDocument:
    """A read-only projection of a Google document.

    ``body_text`` is the text-first projection shown in the editor. ``revision_id``
    is preserved so a future (separately approved) write path can perform a
    revision-aware update; it is never used to send content here.
    """

    doc_id: str
    title: str
    revision_id: str
    body_text: str


def extract_google_doc_id(url_or_id: str) -> str | None:
    """Return the document id from a Google Docs URL or a bare id, else None.

    Handles the common forms (PRD 9.4): a full edit URL
    (``.../document/d/<id>/edit``), a ``?id=<id>`` query, and a bare id pasted on
    its own. Returns None when no plausible id is present so the caller can ask
    the user to paste a valid link.
    """
    candidate = url_or_id.strip()
    if not candidate:
        return None
    path_match = _PATH_ID_RE.search(candidate)
    if path_match:
        return path_match.group("id")
    query_match = _QUERY_ID_RE.search(candidate)
    if query_match:
        return query_match.group("id")
    if _BARE_ID_RE.match(candidate):
        return candidate
    return None


def project_google_document(payload: object) -> GoogleDocument | None:
    """Project a Google Docs ``documents.get`` payload to a read-only document.

    Returns None when the payload is not a well-formed document. The projection
    is intentionally lossy and text-first: paragraphs become lines, named
    heading/title styles become Markdown headings, bulleted/numbered list items
    get a leading marker, and structured objects we cannot edit (tables, inline
    objects) are preserved as a single labeled placeholder line rather than
    silently dropped.
    """
    if not isinstance(payload, dict):
        return None
    doc_id = str(payload.get("documentId", "")).strip()
    if not doc_id:
        return None
    title = str(payload.get("title", "")).strip() or "(untitled)"
    revision_id = str(payload.get("revisionId", "")).strip()
    body = payload.get("body")
    content = body.get("content") if isinstance(body, dict) else None
    lines: list[str] = []
    if isinstance(content, list):
        for element in content:
            line = _project_structural_element(element)
            if line is not None:
                lines.append(line)
    body_text = "\n".join(lines).strip("\n")
    return GoogleDocument(
        doc_id=doc_id,
        title=title,
        revision_id=revision_id,
        body_text=body_text,
    )


def _project_structural_element(element: object) -> str | None:
    if not isinstance(element, dict):
        return None
    if "paragraph" in element:
        return _project_paragraph(element["paragraph"])
    if "table" in element:
        return "[table]"
    if "tableOfContents" in element:
        return "[table of contents]"
    if "sectionBreak" in element:
        return None
    return None


def _project_paragraph(paragraph: object) -> str:
    if not isinstance(paragraph, dict):
        return ""
    elements = paragraph.get("elements")
    text = ""
    if isinstance(elements, list):
        parts: list[str] = []
        for run in elements:
            parts.append(_project_paragraph_element(run))
        text = "".join(parts)
    text = text.replace("\x0b", "\n").rstrip("\n")
    prefix = _paragraph_prefix(paragraph)
    if not text:
        return prefix.rstrip()
    return f"{prefix}{text}"


def _project_paragraph_element(run: object) -> str:
    if not isinstance(run, dict):
        return ""
    text_run = run.get("textRun")
    if isinstance(text_run, dict):
        content = text_run.get("content")
        return str(content) if content is not None else ""
    # Inline objects (images, drawings) cannot be edited as text; preserve a
    # labeled, non-destructive marker so the reader knows something is there.
    if "inlineObjectElement" in run:
        return "[inline object]"
    return ""


def _paragraph_prefix(paragraph: dict[str, object]) -> str:
    if "bullet" in paragraph:
        return "- "
    style = paragraph.get("paragraphStyle")
    if isinstance(style, dict):
        named = str(style.get("namedStyleType", "")).strip().upper()
        return _HEADING_PREFIXES.get(named, "")
    return ""
