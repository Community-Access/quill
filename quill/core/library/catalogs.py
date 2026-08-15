"""Catalogues you add yourself -- the payoff for building on OPDS.

OPDS is an open, decentralised standard: a catalogue is a URL, and any library
that publishes one can be searched by any client that speaks it. That is the
whole reason the ebook half was built on OPDS rather than on a provider-by-
provider adapter, and this is where the payoff lands.

A personal Calibre library on the machine down the hall, a school's repository, a
nonprofit accessible-book collection, a community catalogue -- each is a URL and
a name, and none of them needs a QUILL release to become searchable.

Three rules:

* **HTTPS, or explicitly not.** A catalogue on a home network is often plain
  HTTP, and refusing those outright would rule out exactly the personal-library
  case this feature exists for. So ``http://`` is accepted and the record
  **remembers that it is not encrypted**, which the UI says on the row. A quiet
  downgrade would be worse than either.
* **Nothing is fetched by adding one.** Adding a catalogue writes a name and an
  address. It is searched when a search runs, like every other source.
* **A catalogue can be turned off without being forgotten.** ``enabled`` exists
  so a slow or unreachable one stops slowing every search down without somebody
  having to re-type its address later.

Stored as atomic JSON beside the rest of QUILL's data
(``core.storage.write_json_atomic``), like every other user-owned list.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.storage import write_json_atomic

_FILENAME = "library_catalogs.json"

#: The catalogues QUILL ships knowing about. Not stored, so an upgrade that adds
#: one gets it, and somebody who deleted one does not have it silently return:
#: a built-in is disabled by id in the stored file rather than removed from here.
BUILTIN_CATALOGS: dict[str, str] = {
    "standard-ebooks": "https://standardebooks.org/feeds/opds/all",
    "feedbooks": "https://catalog.feedbooks.com/catalog/public_domain.atom",
}


@dataclass(slots=True)
class Catalog:
    """One OPDS catalogue: what it is called and where it lives."""

    id: str
    name: str
    url: str
    enabled: bool = True

    @property
    def is_encrypted(self) -> bool:
        return self.url.strip().lower().startswith("https://")

    @property
    def display(self) -> str:
        """The row: the name, and the one caveat worth hearing."""
        if not self.enabled:
            return f"{self.name} (switched off)"
        if not self.is_encrypted:
            return f"{self.name} -- not an encrypted connection"
        return self.name

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name, "url": self.url, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, data: object) -> Catalog | None:
        if not isinstance(data, dict):
            return None
        catalog_id = str(data.get("id", "")).strip()
        url = str(data.get("url", "")).strip()
        if not catalog_id or not url:
            return None
        return cls(
            id=catalog_id,
            name=str(data.get("name", "")).strip() or catalog_id,
            url=url,
            enabled=bool(data.get("enabled", True)),
        )


def is_supported_url(url: str) -> bool:
    """Whether *url* is an address this can even try.

    Deliberately permissive about the scheme and strict about everything else:
    a ``file://`` or a bare path would make a catalogue address into a way to
    read the disk, and that is not what adding a library should be able to do.
    """
    text = str(url or "").strip().lower()
    return text.startswith(("https://", "http://")) and len(text) > len("https://")


def catalogs_path(data_dir: Path | str) -> Path:
    return Path(data_dir) / _FILENAME


def load(data_dir: Path | str) -> list[Catalog]:
    """Every catalogue: the built-ins, then whatever has been added.

    A stored record for a built-in id overrides it, which is how a built-in gets
    switched off without being deleted from the code.
    """
    import json

    stored: list[Catalog] = []
    path = catalogs_path(data_dir)
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = []
        if isinstance(raw, list):
            stored = [c for c in (Catalog.from_dict(item) for item in raw) if c is not None]

    by_id = {catalog.id: catalog for catalog in stored}
    result: list[Catalog] = []
    for catalog_id, url in BUILTIN_CATALOGS.items():
        override = by_id.pop(catalog_id, None)
        result.append(
            override
            if override is not None
            else Catalog(id=catalog_id, name=_builtin_name(catalog_id), url=url)
        )
    result.extend(by_id.values())
    return result


def save(data_dir: Path | str, catalogs: list[Catalog]) -> None:
    """Persist *catalogs*. Atomic, like every other list QUILL owns."""
    write_json_atomic(catalogs_path(data_dir), [c.to_dict() for c in catalogs])


def add(catalogs: list[Catalog], *, name: str, url: str) -> Catalog | None:
    """Add one, or ``None`` when the address is unusable or already here."""
    address = str(url or "").strip()
    if not is_supported_url(address):
        return None
    if any(existing.url.rstrip("/") == address.rstrip("/") for existing in catalogs):
        return None
    catalog = Catalog(
        id=_slug(name or address),
        name=str(name or "").strip() or address,
        url=address,
    )
    catalogs.append(catalog)
    return catalog


def remove(catalogs: list[Catalog], catalog_id: str) -> bool:
    """Remove one that was added. A built-in is switched off instead.

    Removing a built-in from the list would only bring it back on the next
    launch, since the built-ins are code rather than data -- so the honest
    action for one of those is to disable it, and this says which it did.
    """
    for index, catalog in enumerate(catalogs):
        if catalog.id != catalog_id:
            continue
        if catalog.id in BUILTIN_CATALOGS:
            catalog.enabled = False
            return False
        catalogs.pop(index)
        return True
    return False


def enabled_urls(catalogs: list[Catalog]) -> dict[str, str]:
    """``{id: url}`` for every catalogue a search should actually visit."""
    return {catalog.id: catalog.url for catalog in catalogs if catalog.enabled and catalog.url}


def _builtin_name(catalog_id: str) -> str:
    return {
        "standard-ebooks": "Standard Ebooks",
        "feedbooks": "Feedbooks (public domain)",
    }.get(catalog_id, catalog_id)


def _slug(text: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return slug or "catalog"
