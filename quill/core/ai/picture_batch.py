"""Describe a Folder: a folder of pictures described one at a time, kept and resumable.

QUILL Studio's Describe a Folder (and Describe Again over a folder) follows the
approach of Kelly Ford's Image Description Toolkit (MIT; see the third-party
notices): choose a folder and a prompt style, and every picture in it is
described in turn, with one small result file per picture so a run cut short
by a lost connection, a plan limit or a closed laptop picks up where it
stopped, and nothing is paid for twice.

This module is the wx-free half, and keeps no state beyond the run:

* **What is in the folder** (:func:`find_pictures`): the picture files, HEIC
  included, never videos.
* **Where results go** (:func:`results_folder`): a folder under Studio's own
  data, one per source folder, never inside the source folder. One JSON file
  per picture (:func:`save_result`, through ``write_json_atomic``) records each
  description with its connection, model, prompt style and time.
* **What still needs doing** (:func:`plan_batch`): the pictures with no result,
  or whose file changed since; for Describe Again, the pictures with no
  description in that style from that connection and model. A **ceiling** per
  run (:func:`default_ceiling`) keeps a batch from reading as a way around a
  plan's limits (codex.md 10B.2 rule 4): small on a plan, larger on your own
  key, largest on a model running here.
* **The confirmation** (:func:`confirmation_sentence`): one question naming the
  count and who receives the pictures (10B.4).
* **Progress, now and then** (:class:`ProgressCounter`): "40 of 212 described",
  never once per picture.
* **The document** (:func:`markdown_document`): every description as Markdown,
  a heading per picture so heading navigation moves between them, several
  descriptions of one picture side by side under it, labelled. Studio opens
  it in QUILL.

Each picture goes through :mod:`quill.core.ai.picture_prep` and the capability
gate before it is sent; that is the caller's job, on the same path Describe a
Picture uses. strict-typed and network-free.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from quill.core.ai.connection_caps import CHATGPT, CODEX, CONNECTION_NAMES, COPILOT, FREE, OWN_KEY
from quill.core.error_codes import CodedError

__all__ = [
    "CREDIT",
    "MAX_CEILING",
    "PICTURE_SUFFIXES",
    "SCHEMA_VERSION",
    "BatchError",
    "BatchPlan",
    "Description",
    "PictureResult",
    "ProgressCounter",
    "confirmation_sentence",
    "default_ceiling",
    "default_results_root",
    "describe_label",
    "document_path",
    "find_pictures",
    "finished_sentence",
    "load_result",
    "load_results",
    "markdown_document",
    "new_result",
    "plan_batch",
    "read_picture",
    "result_path",
    "results_folder",
    "save_result",
    "with_description",
    "write_document",
]

SCHEMA_VERSION = 1
_KIND = "quill-picture-description"

#: The pictures a folder run reads. Videos are left out: only frames ever go.
PICTURE_SUFFIXES: frozenset[str] = frozenset({
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
})

#: The largest ceiling the dialog offers, whatever the connection.
MAX_CEILING = 1000

#: One run's default ceiling per connection. A plan is shared with everything
#: else the person does on it, so it starts small.
_CEILINGS: dict[str, int] = {CHATGPT: 25, CODEX: 25, COPILOT: 25, OWN_KEY: 200}
_LOCAL_CEILING = 1000

#: The credit the document and the user guide carry, word for word.
CREDIT = "Describe a Folder follows the approach of Kelly Ford's Image Description Toolkit."


class BatchError(CodedError):
    """A folder run could not be planned or kept; the message is a sentence."""

    code = "QUILL-AI-PICTURE-BATCH-FAILED"


# -- the folder ----------------------------------------------------------------- #


def _natural(path: Path) -> list[Any]:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", str(path))]


def find_pictures(folder: Path, *, subfolders: bool = False) -> list[Path]:
    """Every picture file in *folder* (and below it, with *subfolders*), in name order.

    Hidden files and Windows thumbnails are left out. Raises :class:`BatchError`
    when the folder cannot be read.
    """
    if not folder.is_dir():
        raise BatchError(f"{folder} is not a folder that can be read.")
    try:
        found = folder.rglob("*") if subfolders else folder.iterdir()
        pictures = [
            path
            for path in found
            if path.is_file()
            and path.suffix.lower() in PICTURE_SUFFIXES
            and not path.name.startswith(".")
        ]
    except OSError as error:
        raise BatchError(f"{folder.name} could not be read: {error}") from error
    return sorted(pictures, key=lambda p: _natural(p.relative_to(folder)))


def read_picture(path: Path) -> bytes:
    """*path*'s bytes, with HEIC converted to JPEG the way ``vision.py`` does."""
    if path.suffix.lower() in (".heic", ".heif"):
        try:
            from quill.core.ai.vision import _heic_to_jpeg_bytes

            return _heic_to_jpeg_bytes(path)
        except Exception as error:  # noqa: BLE001 - one sentence for the skipped list
            raise BatchError(
                f"{path.name} is a HEIC picture that could not be converted."
            ) from error
    try:
        return path.read_bytes()
    except OSError as error:
        raise BatchError(f"{path.name} could not be read: {error.strerror or error}") from error


# -- where results go --------------------------------------------------------------- #


def default_results_root() -> Path:
    """Studio's own folder for picture descriptions, under its app data."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / "studio-descriptions"


def _safe(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", name).strip(" .")
    return " ".join(cleaned.split())[:60] or "pictures"


def _digest(text: str, length: int = 8) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def results_folder(root: Path, folder: Path) -> Path:
    """The results folder for *folder*: its name and a short hash of where it is,
    so two folders called Photos never share one."""
    where = str(folder.resolve()).lower()
    return root / f"{_safe(folder.name)}-{_digest(where)}"


def result_path(results: Path, folder: Path, picture: Path) -> Path:
    """The one JSON file that holds *picture*'s descriptions."""
    relative = picture.relative_to(folder).as_posix()
    return results / f"{_safe(picture.stem)}-{_digest(relative.lower(), 10)}.json"


def document_path(results: Path, folder: Path) -> Path:
    """The Markdown document of every description in a run's results folder."""
    return results / f"{_safe(folder.name)} - descriptions.md"


# -- one picture's result ----------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Description:
    """One description of one picture, and what produced it."""

    text: str
    connection: str
    model: str = ""
    style: str = ""
    style_title: str = ""
    provider: str = ""
    at: str = ""
    details_sent: bool = False
    location_sent: bool = False

    @property
    def connection_name(self) -> str:
        return CONNECTION_NAMES.get(self.connection, self.connection)

    def same_source(self, style: str, connection: str, model: str, provider: str = "") -> bool:
        """Whether this description came from *style* on *connection* and *model*."""
        return (
            self.style == style
            and self.connection == connection
            and self.model == model
            and (connection != OWN_KEY or self.provider == provider)
        )


@dataclass(frozen=True, slots=True)
class PictureResult:
    """Everything kept about one picture: where it is, its facts, its descriptions."""

    path: str
    relative: str
    size: int
    modified: float
    taken: str = ""
    camera: str = ""
    lens: str = ""
    descriptions: tuple[Description, ...] = field(default_factory=tuple)

    @property
    def name(self) -> str:
        return Path(self.relative).name

    def matches(self, picture: Path) -> bool:
        """Whether *picture* is still the file these descriptions are of."""
        try:
            stat = picture.stat()
        except OSError:
            return False
        return stat.st_size == self.size and abs(stat.st_mtime - self.modified) < 2.0


def new_result(
    folder: Path, picture: Path, *, taken: str = "", camera: str = "", lens: str = ""
) -> PictureResult:
    """A result for *picture* with no description yet. Coordinates are never kept."""
    stat = picture.stat()
    return PictureResult(
        path=str(picture),
        relative=picture.relative_to(folder).as_posix(),
        size=stat.st_size,
        modified=stat.st_mtime,
        taken=taken,
        camera=camera,
        lens=lens,
    )


def with_description(result: PictureResult, description: Description) -> PictureResult:
    """*result* with *description* added after the ones it already has."""
    return replace(result, descriptions=(*result.descriptions, description))


def _as_dict(result: PictureResult) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": _KIND,
        "picture": {
            "path": result.path,
            "relative": result.relative,
            "size": result.size,
            "modified": result.modified,
        },
        "details": {"taken": result.taken, "camera": result.camera, "lens": result.lens},
        "descriptions": [
            {
                "text": d.text,
                "connection": d.connection,
                "connection_name": d.connection_name,
                "provider": d.provider,
                "model": d.model,
                "style": d.style,
                "style_title": d.style_title,
                "at": d.at,
                "details_sent": d.details_sent,
                "location_sent": d.location_sent,
            }
            for d in result.descriptions
        ],
    }


def save_result(path: Path, result: PictureResult) -> None:
    """Keep *result* in *path*, atomically, creating the results folder."""
    from quill.core.storage import write_json_atomic

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, _as_dict(result))
    except OSError as error:
        raise BatchError(f"The description of {result.name} could not be kept: {error}") from error


def _description(raw: Any) -> Description | None:
    if not isinstance(raw, dict) or not str(raw.get("text", "")).strip():
        return None
    return Description(
        text=str(raw.get("text", "")),
        connection=str(raw.get("connection", "")),
        model=str(raw.get("model", "")),
        style=str(raw.get("style", "")),
        style_title=str(raw.get("style_title", "")),
        provider=str(raw.get("provider", "")),
        at=str(raw.get("at", "")),
        details_sent=bool(raw.get("details_sent", False)),
        location_sent=bool(raw.get("location_sent", False)),
    )


def load_result(path: Path) -> PictureResult | None:
    """The result in *path*, or None when there is none or it cannot be read.

    A file from a later schema is read for what this version knows, never
    rewritten in a way that loses what it does not.
    """
    from quill.core.storage import read_json

    raw = read_json(path, default=None)
    if not isinstance(raw, dict) or raw.get("kind") != _KIND:
        return None
    picture: dict[str, Any] = raw["picture"] if isinstance(raw.get("picture"), dict) else {}
    details: dict[str, Any] = raw["details"] if isinstance(raw.get("details"), dict) else {}
    found: list[Any] = raw["descriptions"] if isinstance(raw.get("descriptions"), list) else []
    try:
        return PictureResult(
            path=str(picture.get("path", "")),
            relative=str(picture.get("relative", "")),
            size=int(picture.get("size", 0)),
            modified=float(picture.get("modified", 0.0)),
            taken=str(details.get("taken", "")),
            camera=str(details.get("camera", "")),
            lens=str(details.get("lens", "")),
            descriptions=tuple(d for d in (_description(r) for r in found) if d is not None),
        )
    except (TypeError, ValueError):
        return None


def load_results(results: Path) -> list[PictureResult]:
    """Every result in a results folder, in the pictures' name order."""
    if not results.is_dir():
        return []
    kept = [r for r in (load_result(p) for p in results.glob("*.json")) if r is not None]
    return sorted(kept, key=lambda r: _natural(Path(r.relative)))


# -- the plan ------------------------------------------------------------------------ #


def default_ceiling(connection: str, own_key_provider: str = "") -> int:
    """How many pictures one run sends by default on *connection*."""
    if connection == FREE:
        return 0
    if connection == OWN_KEY:
        from quill.core.ai.own_key_providers import is_local

        if is_local(own_key_provider):
            return _LOCAL_CEILING
    return _CEILINGS.get(connection, 25)


@dataclass(frozen=True, slots=True)
class BatchPlan:
    """What a run will do: every picture found, the ones done, the ones to send."""

    folder: Path
    results: Path
    pictures: tuple[Path, ...]
    pending: tuple[Path, ...]
    ceiling: int

    @property
    def done(self) -> int:
        return len(self.pictures) - len(self.pending)

    @property
    def to_send(self) -> tuple[Path, ...]:
        return self.pending[: max(0, self.ceiling)]

    @property
    def left_after(self) -> int:
        return len(self.pending) - len(self.to_send)


#: ``needs(picture, result) -> bool``: whether *picture* still needs this run.
Needs = Callable[[Path, "PictureResult | None"], bool]


def _not_yet_described(picture: Path, result: PictureResult | None) -> bool:
    return result is None or not result.descriptions or not result.matches(picture)


def plan_batch(
    folder: Path,
    results: Path,
    *,
    ceiling: int,
    subfolders: bool = False,
    needs: Needs | None = None,
    only: Sequence[Path] = (),
) -> BatchPlan:
    """The plan for one run over *folder*.

    By default a picture is pending when it has no description yet, or its
    file changed since (resume). Describe Again passes *needs* to ask instead
    whether a picture lacks a description in one style from one connection.
    *only* limits the run to those pictures (one picture described again).
    """
    pictures = tuple(only) if only else tuple(find_pictures(folder, subfolders=subfolders))
    check = needs or _not_yet_described
    pending = tuple(
        picture
        for picture in pictures
        if check(picture, load_result(result_path(results, folder, picture)))
    )
    return BatchPlan(folder, results, pictures, pending, max(0, min(int(ceiling), MAX_CEILING)))


def _count(number: int, noun: str = "picture") -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def confirmation_sentence(plan: BatchPlan, receiver: str, *, with_what: str = "") -> str:
    """The one question asked before anything is sent (10B.4).

    "50 pictures will go to OpenAI on your ChatGPT plan, with each picture's
    date, camera and lens. 40 are described already and are not sent again.
    This run stops after 50; 122 are left for the next run. Send them?"
    """
    sending = len(plan.to_send)
    parts = [f"{_count(sending)} will go to {receiver}{with_what}, one at a time."]
    if plan.done:
        verb = "is" if plan.done == 1 else "are"
        parts.append(f"{plan.done} {verb} described already and not sent again.")
    if plan.left_after:
        parts.append(
            f"This run stops after {plan.ceiling}; {plan.left_after} "
            f"{'is' if plan.left_after == 1 else 'are'} left for the next run."
        )
    parts.append("Send them?")
    return " ".join(parts)


# -- progress --------------------------------------------------------------------- #


class ProgressCounter:
    """Says how far a run has got now and then, as counts: never once per picture.

    A sentence comes every tenth of the run, and at least every five pictures
    apart, so a 12-picture run speaks twice and a 212-picture run ten times.
    """

    def __init__(self, total: int) -> None:
        self.total = max(0, total)
        self.described = 0
        self.skipped = 0
        self._step = max(5, math.ceil(self.total / 10)) if self.total else 1

    @property
    def finished(self) -> int:
        return self.described + self.skipped

    def step(self, *, skipped: bool = False) -> str:
        """Count one picture; the sentence to say now, or ""."""
        if skipped:
            self.skipped += 1
        else:
            self.described += 1
        if self.finished >= self.total or self.finished % self._step:
            return ""
        return f"{self.finished} of {self.total} described."


def finished_sentence(
    described: int, skipped: Sequence[str], *, left: int = 0, stopped: bool = False
) -> str:
    """What is said when a run ends: counts, what was skipped, and what is left."""
    head = "Stopped. " if stopped else ""
    parts = [f"{head}Described {_count(described)}."]
    if skipped:
        shown = ", ".join(skipped[:3]) + (" and others" if len(skipped) > 3 else "")
        parts.append(f"{_count(len(skipped))} could not be read: {shown}.")
    if left:
        parts.append(f"{left} still to describe; run Describe a Folder on it again to carry on.")
    return " ".join(parts)


# -- the document ------------------------------------------------------------------- #


def describe_label(description: Description) -> str:
    """ "Accessibility style, My own key (Anthropic), claude-sonnet-5"."""
    name = description.connection_name
    if description.connection == OWN_KEY and description.provider:
        from quill.core.ai.own_key_providers import PROVIDER_NAMES

        name = f"{name} ({PROVIDER_NAMES.get(description.provider, description.provider)})"
    parts = [f"{description.style_title or description.style or 'Describe'} style", name]
    if description.model:
        parts.append(description.model)
    return ", ".join(parts)


_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)


def _body(text: str) -> str:
    """The model's words, with any heading it wrote made a plain line, so a
    picture's own heading stays the only heading navigation lands on."""
    return _HEADING.sub("", text.strip()) if text.strip() else "No description came back."


def _picture_section(result: PictureResult) -> list[str]:
    lines = [f"## {result.name}", ""]
    facts = []
    if result.relative != result.name:
        facts.append(f"Folder: {Path(result.relative).parent.as_posix()}")
    if result.taken:
        facts.append(f"Taken: {result.taken}")
    if result.camera:
        facts.append(f"Camera: {result.camera}")
    if facts:
        lines += [*(f"- {fact}" for fact in facts), ""]
    if len(result.descriptions) == 1:
        only = result.descriptions[0]
        lines += [_body(only.text), "", f"Described with {describe_label(only)}.", ""]
        return lines
    for number, description in enumerate(result.descriptions, start=1):
        lines += [f"### Description {number}: {describe_label(description)}", ""]
        lines += [_body(description.text), ""]
    return lines


def markdown_document(
    folder_name: str, results: Iterable[PictureResult], *, when: datetime | None = None
) -> str:
    """Every description as one Markdown document, a heading per picture."""
    kept = [r for r in results if r.descriptions]
    stamp = (when or datetime.now()).strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Pictures in {folder_name}",
        "",
        f"{_count(len(kept))} described by AI, as of {stamp}. AI descriptions can be wrong; "
        "check anything that matters.",
        "",
        CREDIT,
        "",
    ]
    for result in kept:
        lines += _picture_section(result)
    return "\n".join(lines).rstrip() + "\n"


def write_document(results: Path, folder: Path) -> Path:
    """Write the Markdown document for a results folder; returns its path."""
    from quill.core.storage import write_text_atomic

    target = document_path(results, folder)
    text = markdown_document(folder.name, load_results(results))
    try:
        write_text_atomic(target, text, encoding="utf-8")
    except OSError as error:
        raise BatchError(f"The descriptions document could not be written: {error}") from error
    return target
