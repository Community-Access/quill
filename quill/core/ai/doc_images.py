"""Alt text for a document's own images, as agent tools (codex.md 6.4, 10B, decision 13).

The one picture feature the editors keep besides Ask About an Image: proposing
alt text for the images already in the document. ``link_inventory`` and
``inline_image_alt`` only *report* missing alt text; this module also writes it,
into Markdown (``![alt](src)``) and HTML (``<img alt="...">``), one image at a
time, and wraps the work as three family tools QUILL and QUILL Lite share
through :class:`~quill.core.ai.document_task.DocumentTaskRunner`:

* ``doc.list_images`` -- every image, numbered, with its alt text or "missing"
  (a read: no question).
* ``doc.image`` -- one image, downscaled for the connection, for a connection
  that can see (asks first, naming the picture; the first picture on each
  connection also asks the 10B.4 consent). A web address is never fetched.
* ``doc.set_alt_text`` -- writes one image's alt text through the editor's own
  reviewed patch: the person sees the change as text in Review AI Changes and
  it is one Control Z (decision 13).

wx-free and strict-typed; the editor supplies the reads, the patch and the
picture loader.
"""

from __future__ import annotations

import base64
import binascii
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.ai.family_tools import EDITOR_APP, FamilyTool, ToolImage, ToolOutput, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "ALT_TEXT_INSTRUCTION",
    "DocImage",
    "doc_image_tools",
    "image_list_text",
    "list_document_images",
    "resolve_image_source",
    "with_alt_text",
]

#: The instruction Propose Alt Text fills in for the person (10B.5).
ALT_TEXT_INSTRUCTION = (
    "Propose alt text for every image in this document that has none. List the "
    "images first, look at each one you can, and write short, plain alt text that "
    "says what the picture shows and why it is there. Set each one separately so "
    "I can review it. Leave images that already have alt text alone, and tell me "
    "about any you could not see."
)

_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
_HTML_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_HTML_ATTR = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(['\"])(.*?)\2", re.DOTALL)
_ALT_ATTR = re.compile(r"\balt\s*=\s*(['\"]).*?\1", re.IGNORECASE | re.DOTALL)
_WEB = re.compile(r"^(?:https?|ftp)://", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class DocImage:
    """One image reference in the document, numbered from 1 in reading order."""

    number: int
    source: str
    alt_text: str
    kind: str  # "markdown" | "html"
    start: int
    end: int

    @property
    def name(self) -> str:
        return os.path.basename(self.source.split("?", 1)[0]) or self.source[:40]


def list_document_images(text: str) -> list[DocImage]:
    """Every Markdown and HTML image, in the order they appear."""
    found: list[tuple[int, int, str, str, str]] = []
    for match in _MD_IMAGE.finditer(text):
        found.append((match.start(), match.end(), match.group(2), match.group(1), "markdown"))
    for match in _HTML_IMG.finditer(text):
        attrs = {m.group(1).lower(): m.group(3) for m in _HTML_ATTR.finditer(match.group(0))}
        if attrs.get("src"):
            found.append((match.start(), match.end(), attrs["src"], attrs.get("alt", ""), "html"))
    found.sort()
    return [
        DocImage(number=i, source=src, alt_text=alt, kind=kind, start=start, end=end)
        for i, (start, end, src, alt, kind) in enumerate(found, start=1)
    ]


def image_list_text(images: list[DocImage]) -> str:
    """The images as plain text for the model and the transcript."""
    if not images:
        return "This document has no images."
    missing = sum(1 for image in images if not image.alt_text.strip())
    lines = [f"{len(images)} image{'s' if len(images) != 1 else ''}, {missing} without alt text."]
    for image in images:
        alt = image.alt_text.strip() or "missing"
        lines.append(f"{image.number}. {image.name} ({image.kind}). Alt text: {alt}")
    return "\n".join(lines)


def _clean_alt(alt: str) -> str:
    return " ".join(alt.replace("\r", " ").replace("\n", " ").split())


def with_alt_text(text: str, number: int, alt: str) -> str:
    """*text* with image *number*'s alt text set to *alt*. Raises ValueError."""
    images = list_document_images(text)
    if not 1 <= number <= len(images):
        raise ValueError(f"There is no image {number}; the document has {len(images)}.")
    image = images[number - 1]
    clean = _clean_alt(alt)
    original = text[image.start : image.end]
    if image.kind == "markdown":
        match = _MD_IMAGE.fullmatch(original)
        if match is None:  # pragma: no cover - list_document_images matched it
            raise ValueError("That image could not be changed.")
        safe = clean.replace("[", "(").replace("]", ")")
        revised = f"![{safe}]({match.group(2)}{match.group(3)})"
    else:
        safe = clean.replace("&", "&amp;").replace('"', "&quot;")
        if _ALT_ATTR.search(original):
            revised = _ALT_ATTR.sub(lambda _m: f'alt="{safe}"', original, count=1)
        else:
            revised = re.sub(r"^<img\b", f'<img alt="{safe}"', original, count=1, flags=re.I)
    return text[: image.start] + revised + text[image.end :]


def resolve_image_source(source: str, document_path: Path | None) -> Path | bytes | None:
    """Where *source* is on this computer, or its bytes for a ``data:`` image.

    A web address is never fetched (nothing leaves for a server the person did
    not choose); a relative path is read beside the document.
    """
    if _WEB.match(source):
        return None
    if source.lower().startswith("data:"):
        _head, _sep, payload = source.partition(",")
        try:
            return base64.b64decode(payload, validate=False)
        except (binascii.Error, ValueError):
            return None
    raw = source.split("?", 1)[0].split("#", 1)[0]
    if raw.lower().startswith("file:///"):
        raw = raw[8:]
    candidate = Path(raw)
    if not candidate.is_absolute():
        if document_path is None:
            return None
        candidate = Path(document_path).parent / candidate
    return candidate if candidate.is_file() else None


#: Loads one image for the model: ``(image) -> ToolImage | str`` (a str says why not).
PictureLoader = Callable[[DocImage], "ToolImage | str"]


def doc_image_tools(
    read_document: Callable[[], str],
    apply_text: Callable[[str, str, str], Any],
    load_picture: PictureLoader | None = None,
) -> list[FamilyTool]:
    """The alt-text tools over one editor.

    ``read_document()`` reads the whole text; ``apply_text(original, revised,
    label)`` is the gateway's reviewed patch (``SafeEditorToolGateway.
    apply_text_patch``), returning True when applied; ``load_picture`` is
    given only when the connection can see.
    """

    def _image(args: dict[str, Any]) -> DocImage:
        images = list_document_images(read_document())
        try:
            number = int(args.get("number", 0))
        except (TypeError, ValueError):
            number = 0
        if not 1 <= number <= len(images):
            raise ValueError(f"There is no image {number}; the document has {len(images)}.")
        return images[number - 1]

    def list_images(_args: dict[str, Any]) -> ToolOutput:
        return image_list_text(list_document_images(read_document()))

    def set_alt(args: dict[str, Any]) -> ToolOutput:
        alt = _clean_alt(str(args.get("alt_text", "")))
        if not alt:
            raise ToolError("Give the alt text to set.")
        original = read_document()
        try:
            image = _image(args)
            revised = with_alt_text(original, image.number, alt)
        except ValueError as error:
            raise ToolError(str(error)) from error
        applied = apply_text(original, revised, f"Alt text for image {image.number}")
        return "True" if applied else "False"

    number = {"type": "integer", "description": "The image's number from doc_list_images."}
    tools = [
        FamilyTool(
            name=f"{EDITOR_APP}.list_images",
            description=(
                "List every image in the document, numbered, with its alt text or 'missing'."
            ),
            handler=list_images,
            category=PermissionCategory.READ_DOCUMENT,
        ),
        FamilyTool(
            name=f"{EDITOR_APP}.set_alt_text",
            description=(
                "Set one image's alt text. The person reviews the change as text "
                "before it is applied."
            ),
            handler=set_alt,
            parameters=_schema(
                {
                    "number": number,
                    "alt_text": {"type": "string", "description": "Short, plain alt text."},
                },
                ("number", "alt_text"),
            ),
            category=PermissionCategory.MODIFY_DOCUMENT,
            risk=RiskLevel.HIGH,
            mutating=True,
            via_gateway=True,
            summarize=lambda a: f"Set the alt text of image {a.get('number', '')}.",
        ),
    ]
    if load_picture is not None:
        loader = load_picture

        def picture(args: dict[str, Any]) -> ToolOutput:
            try:
                image = _image(args)
            except ValueError as error:
                return str(error)
            got = loader(image)
            return got

        def summary(args: dict[str, Any]) -> str:
            try:
                name = _image(args).name
            except ValueError:
                name = f"image {args.get('number', '')}"
            return f"Send the picture {name} from this document to your AI, to describe it."

        tools.append(
            FamilyTool(
                name=f"{EDITOR_APP}.image",
                description=(
                    "Look at one image in the document. Asks the person first, "
                    "because the picture leaves this computer."
                ),
                handler=picture,
                parameters=_schema({"number": number}, ("number",)),
                # A picture leaving the computer asks every time (10B.4): WEB is
                # the category that leaves, and Locked Down denies it.
                category=PermissionCategory.WEB,
                risk=RiskLevel.MEDIUM,
                summarize=summary,
            )
        )
    return tools
