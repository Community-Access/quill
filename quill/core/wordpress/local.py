"""Local working copies and previous versions of WordPress documents (wordpress.md 5.3, 5.6).

Three saves are kept apart, and this module is the first of them: **Save**
writes a local working copy and never sends anything. The other two (Save
Draft to Site, Publish or Update) live in the commands; this file only
remembers.

A working copy is keyed by site, kind and remote id -- or, before the item
exists on the site, by a local id -- so the same title on two sites is two
documents. Each copy keeps:

* the text in the format it was created in (Markdown stays Markdown: the
  source is kept here, and only the HTML goes to the site);
* the properties (title, slug, status, categories, tags, featured image...);
* the site's ``modified_gmt`` when the copy was opened, for the conflict
  check (5.4);
* which local pictures are not uploaded yet (6.4).

Versions are kept at the moments wordpress.md names ("Opened from site",
"Saved", "Site copy before update", "Before AI change", "Before restore"),
newest first, capped per document so the folder does not grow without end.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

MAX_VERSIONS = 50

REASON_OPENED = "Opened from site"
REASON_SAVED = "Saved"
REASON_SITE_BEFORE_UPDATE = "Site copy before update"
REASON_BEFORE_AI = "Before AI change"
REASON_BEFORE_RESTORE = "Before restore"
REASON_PUBLISHED = "Published"


@dataclass
class WorkingCopy:
    site_id: str
    kind: str
    local_id: str
    remote_id: int = 0
    title: str = ""
    text: str = ""
    text_format: str = "markdown"  # "markdown" or "html"; fixed at creation (5.1)
    properties: dict[str, Any] = field(default_factory=dict)
    base_modified_gmt: str = ""
    link: str = ""
    status: str = "draft"
    saved_at: str = ""
    pending_uploads: list[dict[str, Any]] = field(default_factory=list)
    #: Where this copy lives, fixed at its first save. A new draft that gets an
    #: id on the site keeps its folder, because the editor still has the file
    #: in it open (moving it lost the document on its first send).
    folder: str = ""

    @property
    def key(self) -> str:
        return self.folder or document_key(self.site_id, self.kind, self.remote_id, self.local_id)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkingCopy:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass(frozen=True)
class Version:
    id: str
    saved_at: str
    reason: str
    title: str
    text: str
    text_format: str
    properties: dict[str, Any]

    def spoken(self) -> str:
        return f"{_friendly(self.saved_at)}, {self.title or '(untitled)'}, {self.reason}"


def document_key(site_id: str, kind: str, remote_id: int, local_id: str = "") -> str:
    ident = str(remote_id) if remote_id else f"local-{local_id}"
    return f"{_safe(site_id)}/{_safe(kind)}-{_safe(ident)}"


def new_local_id() -> str:
    return uuid4().hex[:12]


class LocalStore:
    """Working copies and versions under ``<data>/wordpress``."""

    def __init__(self, base: Path | None = None) -> None:
        self.root = (base or app_data_dir()) / "wordpress"

    # -- working copies ----------------------------------------------------

    def save(self, copy: WorkingCopy) -> WorkingCopy:
        copy.saved_at = now_stamp()
        copy.folder = copy.key
        write_json_atomic(self._dir(copy.key) / "working.json", asdict(copy))
        return copy

    def load(self, key: str) -> WorkingCopy | None:
        raw = read_json(self._dir(key) / "working.json", default=None)
        return WorkingCopy.from_dict(raw) if isinstance(raw, dict) else None

    def find(self, site_id: str, kind: str, remote_id: int) -> WorkingCopy | None:
        found = self.load(document_key(site_id, kind, remote_id))
        if found is not None:
            return found
        # A draft started in QUILL keeps its first folder after it is sent.
        return next(
            (
                c
                for c in self.drafts(site_id)
                if c.kind == kind and remote_id and c.remote_id == remote_id
            ),
            None,
        )

    def rekey(self, copy: WorkingCopy, remote_id: int) -> WorkingCopy:
        """A local-only draft got an id on the site. It stays where it is."""
        copy.remote_id = remote_id
        return self.save(copy)

    def drafts(self, site_id: str | None = None) -> list[WorkingCopy]:
        """Every working copy, newest first (Open Local Draft)."""
        found: list[WorkingCopy] = []
        if not self.root.exists():
            return found
        sites = (
            [self.root / _safe(site_id)]
            if site_id
            else [p for p in self.root.iterdir() if p.is_dir()]
        )
        for site_dir in sites:
            if not site_dir.is_dir():
                continue
            for doc_dir in site_dir.iterdir():
                raw = read_json(doc_dir / "working.json", default=None)
                if isinstance(raw, dict):
                    found.append(WorkingCopy.from_dict(raw))
        return sorted(found, key=lambda c: c.saved_at, reverse=True)

    def discard(self, key: str) -> None:
        directory = self._dir(key)
        for name in ("working.json",):
            (directory / name).unlink(missing_ok=True)

    # -- the file the editor opens -------------------------------------------

    def document_path(self, copy: WorkingCopy) -> Path:
        """The file a WordPress document is edited in, so Ctrl+S is a local save.

        The editor opens and saves this file like any other; the WordPress
        commands find the working copy beside it by :meth:`copy_for_path`.
        """
        suffix = ".html" if copy.text_format == "html" else ".md"
        return self._dir(copy.key) / f"{_safe(copy.title)[:60] or 'untitled'}{suffix}"

    def write_document(self, copy: WorkingCopy) -> Path:
        path = self.document_path(copy)
        path.parent.mkdir(parents=True, exist_ok=True)
        for old in path.parent.glob("*.md"):
            if old != path:
                old.unlink(missing_ok=True)
        for old in path.parent.glob("*.html"):
            if old != path:
                old.unlink(missing_ok=True)
        path.write_bytes(copy.text.encode("utf-8"))
        copy.properties["document_file"] = path.name
        self.save(copy)
        return path

    def copy_for_path(self, path: Path | None) -> WorkingCopy | None:
        """The working copy behind an open file, or None for an ordinary file."""
        if path is None:
            return None
        try:
            relative = Path(path).resolve().relative_to(self.root.resolve())
        except (ValueError, OSError):
            return None
        if len(relative.parts) != 3:
            return None
        copy = self.load("/".join(relative.parts[:2]))
        if copy is None:
            return None
        try:
            copy.text = Path(path).read_bytes().decode("utf-8")
        except OSError:
            pass
        return copy

    # -- versions ----------------------------------------------------------

    def add_version(
        self, copy: WorkingCopy, reason: str, *, text: str | None = None, title: str | None = None
    ) -> Version:
        version = Version(
            id=uuid4().hex[:10],
            saved_at=now_stamp(),
            reason=reason,
            title=copy.title if title is None else title,
            text=copy.text if text is None else text,
            text_format=copy.text_format,
            properties=dict(copy.properties),
        )
        versions = self.versions(copy.key)
        # Two identical versions in a row say nothing new.
        if versions and versions[0].text == version.text and versions[0].title == version.title:
            return versions[0]
        versions.insert(0, version)
        self._write_versions(copy.key, versions[:MAX_VERSIONS])
        return version

    def versions(self, key: str) -> list[Version]:
        raw = read_json(self._dir(key) / "versions.json", default=[])
        if not isinstance(raw, list):
            return []
        return [Version(**v) for v in raw if isinstance(v, dict) and "id" in v]

    def restore(self, copy: WorkingCopy, version_id: str) -> WorkingCopy:
        """Put a version in the working copy. Keeps what it replaces first. Never sends."""
        target = next((v for v in self.versions(copy.key) if v.id == version_id), None)
        if target is None:
            return copy
        self.add_version(copy, REASON_BEFORE_RESTORE)
        copy.title = target.title
        copy.text = target.text
        copy.properties = dict(target.properties)
        return self.save(copy)

    def _write_versions(self, key: str, versions: list[Version]) -> None:
        write_json_atomic(self._dir(key) / "versions.json", [asdict(v) for v in versions])

    def _dir(self, key: str) -> Path:
        return self.root / key


# --------------------------------------------------------------------------- #
# Conflict protection (wordpress.md 5.4)


@dataclass(frozen=True)
class Conflict:
    base_modified_gmt: str
    site_modified_gmt: str

    def spoken(self, site_name: str, who: str = "") -> str:
        by = f" by {who}" if who else ""
        return (
            f"The copy on {site_name} was changed{by} on {_friendly(self.site_modified_gmt)}, "
            "after you opened it. Nothing was sent."
        )


def conflict_between(base_modified_gmt: str, site_modified_gmt: str) -> Conflict | None:
    """A conflict when the site changed after the working copy was opened."""
    if not base_modified_gmt or not site_modified_gmt:
        return None
    if _parse(site_modified_gmt) > _parse(base_modified_gmt):
        return Conflict(base_modified_gmt, site_modified_gmt)
    return None


# --------------------------------------------------------------------------- #


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")


def _parse(stamp: str) -> datetime:
    try:
        return datetime.fromisoformat(stamp.replace("Z", ""))
    except ValueError:
        return datetime.min


def _friendly(stamp: str) -> str:
    from quill.core.wordpress.site import friendly_date

    return friendly_date(stamp.split(".", 1)[0])


def _safe(part: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", part) or "_"
