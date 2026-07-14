from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_PUBLISHING_LINKAGE_FILE = "publishing-linkage.json"


@dataclass(frozen=True, slots=True)
class PublishingLinkageEntry:
    provider_id: str = ""
    site_url: str = ""
    remote_id: str = ""
    remote_url: str = ""
    remote_title: str = ""
    content_kind: str = ""
    authoring_surface: str = ""
    open_representation: str = ""
    status: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PublishingLinkageEntry:
        return cls(
            provider_id=str(data.get("provider_id", "")).strip(),
            site_url=str(data.get("site_url", "")).strip(),
            remote_id=str(data.get("remote_id", "")).strip(),
            remote_url=str(data.get("remote_url", "")).strip(),
            remote_title=str(data.get("remote_title", "")).strip(),
            content_kind=str(data.get("content_kind", "")).strip(),
            authoring_surface=str(data.get("authoring_surface", "")).strip(),
            open_representation=str(data.get("open_representation", "")).strip(),
            status=str(data.get("status", "")).strip(),
            updated_at=str(data.get("updated_at", "")).strip(),
        )


def publishing_linkage_path() -> Path:
    return app_data_dir() / _PUBLISHING_LINKAGE_FILE


def _registry_key(path: Path) -> str:
    return str(path.resolve())


def load_publishing_linkage_registry() -> dict[str, PublishingLinkageEntry]:
    raw = read_json(publishing_linkage_path(), default={})
    if not isinstance(raw, dict):
        return {}
    raw_entries = raw.get("entries", {})
    if not isinstance(raw_entries, dict):
        return {}
    registry: dict[str, PublishingLinkageEntry] = {}
    for key, value in raw_entries.items():
        if isinstance(key, str) and isinstance(value, dict):
            registry[key] = PublishingLinkageEntry.from_dict(value)
    return registry


def save_publishing_linkage_registry(registry: dict[str, PublishingLinkageEntry]) -> None:
    payload = {
        "schema_version": 1,  # persistence contract
        "entries": {key: asdict(entry) for key, entry in registry.items()},
    }
    write_json_atomic(publishing_linkage_path(), payload)


def get_publishing_linkage(path: Path) -> PublishingLinkageEntry | None:
    return load_publishing_linkage_registry().get(_registry_key(path))


def upsert_publishing_linkage(path: Path, entry: PublishingLinkageEntry) -> None:
    registry = load_publishing_linkage_registry()
    registry[_registry_key(path)] = entry
    save_publishing_linkage_registry(registry)


def remove_publishing_linkage(path: Path) -> None:
    registry = load_publishing_linkage_registry()
    key = _registry_key(path)
    if key not in registry:
        return
    del registry[key]
    save_publishing_linkage_registry(registry)


def publishing_linkage_from_source_metadata(
    metadata: dict[str, object],
) -> PublishingLinkageEntry | None:
    if metadata.get("source_kind") != "publishing_remote":
        return None
    provider_id = str(metadata.get("publishing_provider_id", "")).strip()
    if not provider_id:
        return None
    return PublishingLinkageEntry(
        provider_id=provider_id,
        site_url=str(metadata.get("publishing_site_url", "")).strip(),
        remote_id=str(metadata.get("publishing_remote_id", "")).strip(),
        remote_url=str(metadata.get("publishing_remote_url", "")).strip(),
        remote_title=str(metadata.get("publishing_remote_title", "")).strip(),
        content_kind=str(metadata.get("publishing_content_kind", "")).strip(),
        authoring_surface=str(metadata.get("publishing_authoring_surface", "")).strip(),
        open_representation=str(metadata.get("publishing_open_representation", "")).strip(),
        status=str(metadata.get("publishing_status", "")).strip(),
        updated_at=str(metadata.get("publishing_updated_at", "")).strip(),
    )


def apply_publishing_linkage_to_source_metadata(
    metadata: dict[str, object], entry: PublishingLinkageEntry
) -> None:
    metadata["source_kind"] = "publishing_remote"
    metadata["source_label"] = "from publishing"
    metadata["publishing_provider_id"] = entry.provider_id
    metadata["publishing_site_url"] = entry.site_url
    metadata["publishing_remote_id"] = entry.remote_id
    metadata["publishing_remote_url"] = entry.remote_url
    metadata["publishing_remote_title"] = entry.remote_title
    metadata["publishing_content_kind"] = entry.content_kind
    metadata["publishing_authoring_surface"] = entry.authoring_surface
    metadata["publishing_open_representation"] = entry.open_representation
    metadata["publishing_status"] = entry.status
    metadata["publishing_updated_at"] = entry.updated_at
