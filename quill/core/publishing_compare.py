from __future__ import annotations

from dataclasses import dataclass

from quill.core.publishing_clients import PublishingRemoteDocument


@dataclass(frozen=True, slots=True)
class PublishingComparison:
    provider_id: str
    site_url: str
    remote_url: str
    content_kind: str
    local_title: str
    remote_title: str
    title_differs: bool
    body_differs: bool
    local_status: str
    remote_status: str
    status_differs: bool
    last_known_updated_at: str
    remote_updated_at: str
    remote_changed_since_last_known: bool


def build_publishing_comparison(
    remote: PublishingRemoteDocument,
    *,
    local_title: str,
    local_body_html: str,
    local_status: str,
    last_known_updated_at: str,
) -> PublishingComparison:
    clean_local_status = local_status.strip().lower()
    clean_remote_status = remote.status.strip().lower()
    clean_last_known = last_known_updated_at.strip()
    clean_remote_updated_at = remote.updated_at.strip()
    return PublishingComparison(
        provider_id=remote.provider_id,
        site_url=remote.site_url,
        remote_url=remote.remote_url,
        content_kind=remote.content_kind,
        local_title=local_title,
        remote_title=remote.title,
        title_differs=local_title.strip() != remote.title.strip(),
        body_differs=local_body_html.strip() != remote.body.strip(),
        local_status=clean_local_status,
        remote_status=clean_remote_status,
        status_differs=clean_local_status != clean_remote_status,
        last_known_updated_at=clean_last_known,
        remote_updated_at=clean_remote_updated_at,
        remote_changed_since_last_known=(
            bool(clean_last_known)
            and bool(clean_remote_updated_at)
            and clean_last_known != clean_remote_updated_at
        ),
    )
