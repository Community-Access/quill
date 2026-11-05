"""Which site each form was published to, and what has been seen there (17a.7, 17a.8).

wx-free. One small file in QUILL's data folder, ``forms-published.json``,
holds three things and nothing personal:

- **links:** a form document's path -> the site, BAF's form id, its title and
  the ``updated_at`` the site gave when it was last published. Conflict
  protection compares that stamp with the site's (as 5.4 does for pages), and
  Test on Site and Responses start from it;
- **seen:** per site, per form, how many responses there were when Responses
  was last opened -- the "new responses" count is the difference. A count, not
  a response;
- **versions:** before Publish Form replaces a form on the site, the site's
  copy (its BFL) is kept beside this file, the newest ten per form, so a
  publish over somebody else's change can be undone by hand (5.6).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic, write_text_atomic

STORE_FILE = "forms-published.json"
VERSIONS_FOLDER = "forms-versions"
#: Previous versions kept per form.
KEEP_VERSIONS = 10
STORE_VERSION = 1


@dataclass(frozen=True)
class Link:
    site_id: str
    form_id: int
    title: str = ""
    updated_at: str = ""
    status: str = "draft"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Link:
        return cls(
            site_id=str(data.get("site_id", "")),
            form_id=int(data.get("form_id", 0) or 0),
            title=str(data.get("title", "")),
            updated_at=str(data.get("updated_at", "")),
            status=str(data.get("status", "draft")),
        )


class PublishedStore:
    """The links, seen counts and previous versions, under one data folder."""

    def __init__(self, base: Path | None = None) -> None:
        self.base = base or app_data_dir()

    @property
    def path(self) -> Path:
        return self.base / STORE_FILE

    def _read(self) -> dict[str, Any]:
        raw = read_json(self.path, default=None)
        data = raw if isinstance(raw, dict) else {}
        data.setdefault("version", STORE_VERSION)
        data.setdefault("links", {})
        data.setdefault("seen", {})
        return data

    def _write(self, data: dict[str, Any]) -> None:
        write_json_atomic(self.path, data)

    # -- links --------------------------------------------------------------- #

    @staticmethod
    def key(path: Path | str) -> str:
        try:
            return str(Path(path).resolve()).lower()
        except OSError:
            return str(path).lower()

    def link_for(self, path: Path | str | None) -> Link | None:
        if not path:
            return None
        found = self._read()["links"].get(self.key(path))
        return Link.from_dict(found) if isinstance(found, dict) else None

    def set_link(self, path: Path | str, link: Link) -> None:
        data = self._read()
        data["links"][self.key(path)] = asdict(link)
        self._write(data)

    def links_on(self, site_id: str) -> list[Link]:
        """Every form published from this computer to one site."""
        out = [Link.from_dict(v) for v in self._read()["links"].values() if isinstance(v, dict)]
        return [link for link in out if link.site_id == site_id]

    # -- seen counts --------------------------------------------------------- #

    def seen(self, site_id: str, form_id: int) -> int:
        site = self._read()["seen"].get(site_id) or {}
        return int(site.get(str(form_id), 0) or 0)

    def mark_seen(self, site_id: str, form_id: int, count: int) -> None:
        data = self._read()
        data["seen"].setdefault(site_id, {})[str(form_id)] = int(count)
        self._write(data)

    # -- previous versions --------------------------------------------------- #

    def keep_version(self, site_id: str, form_id: int, bfl: str) -> Path | None:
        """Keep the site's copy before it is replaced; the oldest beyond ten go."""
        if not bfl.strip():
            return None
        folder = self.base / VERSIONS_FOLDER / _safe(site_id) / str(int(form_id))
        folder.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        target = folder / f"{stamp}.bfl"
        write_text_atomic(target, bfl, newline="\n")
        for old in sorted(folder.glob("*.bfl"))[:-KEEP_VERSIONS]:
            old.unlink(missing_ok=True)
        return target

    def versions(self, site_id: str, form_id: int) -> list[Path]:
        folder = self.base / VERSIONS_FOLDER / _safe(site_id) / str(int(form_id))
        return sorted(folder.glob("*.bfl"), reverse=True) if folder.is_dir() else []


def new_responses(
    store: PublishedStore, site_id: str, counts: dict[int, tuple[str, int]]
) -> list[tuple[str, int]]:
    """``(form title, new count)`` for each form with more responses than were seen."""
    out: list[tuple[str, int]] = []
    for form_id, (title, count) in counts.items():
        fresh = count - store.seen(site_id, form_id)
        if fresh > 0:
            out.append((title, fresh))
    return out


def waiting_sentence(site_name: str, found: list[tuple[str, int]]) -> str:
    """ "Community Radio: 4 new responses to Event registration." -- one sentence for all."""
    parts = [
        f"{count} new {'response' if count == 1 else 'responses'} to {title or 'a form'}"
        for title, count in found
    ]
    if not parts:
        return ""
    joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"{site_name}: {joined}."


def _safe(part: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in part) or "site"


__all__ = [
    "KEEP_VERSIONS",
    "Link",
    "PublishedStore",
    "new_responses",
    "waiting_sentence",
]
