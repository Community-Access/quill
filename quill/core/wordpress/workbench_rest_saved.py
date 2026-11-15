"""Saved REST Console requests (PRD 15.9; W7).

A request the person keeps from the REST Console (Save Request) becomes a
row in the Workbench's Tools > Saved Requests menu, numbered 1 to 9 as its
access keys, and in Run a Saved Request (Ctrl+Alt+Q). Running one opens the
console filled in: a read is sent at once, a write still shows its preview.

Kept in ``workbench_rest_requests.json`` beside the site list, written
atomically; a request names its site, method, route and the parameters as
typed. Parameters are what the person typed in the console, so the console's
own help says not to type a password there. Saving under a name already used
replaces that request. Wx-free and network-free.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.sites import sites_path

__all__ = ["MAX_SAVED", "SavedRequest", "forget", "load_saved", "remember", "save_all"]

MAX_SAVED = 30


@dataclass(frozen=True)
class SavedRequest:
    name: str
    site: str
    method: str
    route: str
    params: str = ""

    @property
    def label(self) -> str:
        return f"{self.name} ({self.method} {self.route} on {self.site})"


def _path(base: Path | None) -> Path:
    return sites_path(base).parent / "workbench_rest_requests.json"


def load_saved(base: Path | None = None) -> list[SavedRequest]:
    raw = read_json(_path(base), default=[])
    found: list[SavedRequest] = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("route"):
            continue
        found.append(
            SavedRequest(
                str(entry["name"]),
                str(entry.get("site", "")),
                str(entry.get("method", "GET")).upper(),
                str(entry["route"]),
                str(entry.get("params", "")),
            )
        )
    return found


def save_all(requests: Sequence[SavedRequest], base: Path | None = None) -> None:
    write_json_atomic(_path(base), [asdict(r) for r in requests[:MAX_SAVED]])


def remember(request: SavedRequest, base: Path | None = None) -> list[SavedRequest]:
    """Keep *request* first, replacing one of the same name; all of them."""
    kept = [r for r in load_saved(base) if r.name.casefold() != request.name.casefold()]
    every = [request, *kept][:MAX_SAVED]
    save_all(every, base)
    return every


def forget(name: str, base: Path | None = None) -> list[SavedRequest]:
    kept = [r for r in load_saved(base) if r.name.casefold() != name.casefold()]
    save_all(kept, base)
    return kept
