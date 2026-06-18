from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from quill.core.html_to_markdown import html_to_markdown
from quill.core.paths import app_data_dir
from quill.core.browser_preview import render_preview_body
from quill.core.publishing_clients import (
    PublishingRemoteDocument,
    PublishingRemoteItemSummary,
    publishing_provider_client,
)
from quill.core.publishing_providers import (
    AUTH_METHOD_APP_PASSWORD,
    default_content_format_for_provider,
    provider_content_kind_label,
    provider_content_kinds,
    provider_implemented_auth_methods,
    provider_supported_auth_methods,
    publishing_auth_method_name,
    publishing_provider_definition,
    publishing_provider_display_name,
)
from quill.core.storage import read_json, write_json_atomic
from quill.platform.windows.credential_manager import (
    credential_manager_available,
    delete_generic_credential,
    load_generic_credential,
    save_generic_credential,
)
from quill.platform.windows.dpapi import protect_secret, unprotect_secret

_PUBLISHING_CONNECTIONS_FILE = "publishing-connections.json"
PUBLISHING_OPEN_REPRESENTATION_READABLE_MARKDOWN = "readable_markdown"
PUBLISHING_OPEN_REPRESENTATION_RAW_HTML = "raw_html"
_RAW_HTML_FALLBACK_TAGS = (
    "<table",
    "<tr",
    "<td",
    "<th",
    "<figure",
    "<figcaption",
    "<iframe",
    "<svg",
    "<math",
    "<form",
    "<input",
    "<textarea",
    "<select",
    "<video",
    "<audio",
)


@dataclass(slots=True)
class PublishingConnectionProfile:
    id: str = ""
    label: str = ""
    provider_id: str = "wordpress"
    site_url: str = ""
    auth_method: str = AUTH_METHOD_APP_PASSWORD
    account_identifier: str = ""
    content_format: str = "html"

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PublishingConnectionProfile:
        provider_id = str(data.get("provider_id", "wordpress")).strip().lower() or "wordpress"
        allowed_auth = set(provider_supported_auth_methods(provider_id))
        auth_method = str(data.get("auth_method", AUTH_METHOD_APP_PASSWORD)).strip().lower()
        if auth_method not in allowed_auth:
            auth_method = AUTH_METHOD_APP_PASSWORD
        content_format = (
            str(data.get("content_format", default_content_format_for_provider(provider_id)))
            .strip()
            .lower()
        )
        if content_format not in {"html"}:
            content_format = default_content_format_for_provider(provider_id)
        profile = cls(
            id=str(data.get("id", "")).strip(),
            label=str(data.get("label", "")).strip(),
            provider_id=provider_id,
            site_url=str(data.get("site_url", "")).strip(),
            auth_method=auth_method,
            account_identifier=str(data.get("account_identifier", "")).strip(),
            content_format=content_format,
        )
        if not profile.id:
            profile.id = generate_publishing_connection_id()
        if not profile.label:
            profile.label = publishing_provider_display_name(profile.provider_id)
        return profile


@dataclass(slots=True)
class PublishingConnectionStore:
    connections: list[PublishingConnectionProfile]
    current_connection_id: str = ""


@dataclass(frozen=True, slots=True)
class PreparedPublishingRemoteContent:
    text: str
    authoring_surface: str
    open_representation: str


def generate_publishing_connection_id() -> str:
    return "pub-" + uuid4().hex[:12]


def publishing_connections_path() -> Path:
    return app_data_dir() / _PUBLISHING_CONNECTIONS_FILE


def load_publishing_connections() -> PublishingConnectionStore:
    raw = read_json(publishing_connections_path(), default={})
    if not isinstance(raw, dict):
        return PublishingConnectionStore(connections=[])
    raw_connections = raw.get("connections", [])
    connections: list[PublishingConnectionProfile] = []
    if isinstance(raw_connections, list):
        for item in raw_connections:
            if isinstance(item, dict):
                connections.append(PublishingConnectionProfile.from_dict(item))
    current_connection_id = str(raw.get("current_connection_id", "")).strip()
    if current_connection_id and not any(item.id == current_connection_id for item in connections):
        current_connection_id = ""
    if not current_connection_id and connections:
        current_connection_id = connections[0].id
    return PublishingConnectionStore(
        connections=connections,
        current_connection_id=current_connection_id,
    )


def save_publishing_connections(store: PublishingConnectionStore) -> None:
    payload = {
        "connections": [asdict(_normalized_profile(item)) for item in store.connections],
        "current_connection_id": store.current_connection_id.strip(),
    }
    write_json_atomic(publishing_connections_path(), payload)


def upsert_publishing_connection(profile: PublishingConnectionProfile) -> PublishingConnectionStore:
    normalized = _normalized_profile(profile)
    store = load_publishing_connections()
    replaced = False
    updated: list[PublishingConnectionProfile] = []
    for existing in store.connections:
        if existing.id == normalized.id:
            updated.append(normalized)
            replaced = True
        else:
            updated.append(existing)
    if not replaced:
        updated.append(normalized)
    current_connection_id = store.current_connection_id or normalized.id
    if normalized.id == store.current_connection_id or not store.current_connection_id:
        current_connection_id = normalized.id
    new_store = PublishingConnectionStore(updated, current_connection_id)
    save_publishing_connections(new_store)
    return new_store


def remove_publishing_connection(connection_id: str) -> PublishingConnectionStore:
    store = load_publishing_connections()
    connection_id = connection_id.strip()
    updated = [item for item in store.connections if item.id != connection_id]
    clear_publishing_secret(connection_id)
    current_connection_id = store.current_connection_id
    if current_connection_id == connection_id:
        current_connection_id = updated[0].id if updated else ""
    new_store = PublishingConnectionStore(updated, current_connection_id)
    save_publishing_connections(new_store)
    return new_store


def set_current_publishing_connection(connection_id: str) -> PublishingConnectionStore:
    store = load_publishing_connections()
    if any(item.id == connection_id for item in store.connections):
        store.current_connection_id = connection_id
        save_publishing_connections(store)
    return store


def current_publishing_connection() -> PublishingConnectionProfile | None:
    store = load_publishing_connections()
    if not store.current_connection_id:
        return None
    for item in store.connections:
        if item.id == store.current_connection_id:
            return item
    return None


def save_publishing_secret(connection_id: str, secret: str) -> None:
    normalized_id = connection_id.strip()
    path = _publishing_secret_path(normalized_id)
    clean = secret.strip()
    if not clean:
        _delete_secret_from_credential_manager(normalized_id)
        if path.exists():
            path.unlink()
        return
    if _save_secret_with_credential_manager(normalized_id, clean):
        if path.exists():
            path.unlink()
        return
    write_json_atomic(path, {"protected_secret": protect_secret(clean)})


def load_publishing_secret(connection_id: str) -> str:
    normalized_id = connection_id.strip()
    credential_secret = _load_secret_from_credential_manager(normalized_id)
    if credential_secret:
        return credential_secret
    raw = read_json(_publishing_secret_path(normalized_id), default={})
    if not isinstance(raw, dict):
        return ""
    encrypted = str(raw.get("protected_secret", "")).strip()
    if not encrypted:
        return ""
    decrypted = unprotect_secret(encrypted)
    if not decrypted:
        return ""
    if _save_secret_with_credential_manager(normalized_id, decrypted):
        path = _publishing_secret_path(normalized_id)
        if path.exists():
            path.unlink()
    return decrypted


def clear_publishing_secret(connection_id: str) -> bool:
    normalized_id = connection_id.strip()
    had_credential = bool(_load_secret_from_credential_manager(normalized_id))
    _delete_secret_from_credential_manager(normalized_id)
    path = _publishing_secret_path(normalized_id)
    had_file = path.exists()
    if had_file:
        path.unlink(missing_ok=True)
    return had_credential or had_file


def verify_publishing_connection(
    profile: PublishingConnectionProfile,
    secret: str,
    *,
    timeout_seconds: float = 8.0,
) -> tuple[bool, str]:
    normalized = _normalized_profile(profile)
    if not normalized.site_url:
        return False, "Enter a site URL before verifying the publishing connection."
    policy_error = _validate_endpoint_security(normalized.site_url)
    if policy_error:
        return False, policy_error
    if publishing_provider_definition(normalized.provider_id) is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return False, f"{provider_name} publishing provider is not registered."
    if normalized.auth_method not in provider_implemented_auth_methods(normalized.provider_id):
        return (
            False,
            (
                f"{publishing_auth_method_name(normalized.auth_method)} is planned for "
                f"{publishing_provider_display_name(normalized.provider_id)}, "
                "but is not implemented yet."
            ),
        )
    client = publishing_provider_client(normalized.provider_id)
    if client is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return False, f"{provider_name} publishing is not implemented yet."
    return client.verify_connection(normalized, secret, timeout_seconds=timeout_seconds)


def browse_publishing_content(
    profile: PublishingConnectionProfile,
    secret: str,
    *,
    content_kinds: tuple[str, ...] | None = None,
    statuses: tuple[str, ...] | None = None,
    timeout_seconds: float = 10.0,
) -> tuple[bool, str, list[PublishingRemoteItemSummary]]:
    normalized = _normalized_profile(profile)
    if not normalized.site_url:
        return False, "Enter a site URL before browsing publishing content.", []
    policy_error = _validate_endpoint_security(normalized.site_url)
    if policy_error:
        return False, policy_error, []
    if publishing_provider_definition(normalized.provider_id) is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return False, f"{provider_name} publishing provider is not registered.", []
    if normalized.auth_method not in provider_implemented_auth_methods(normalized.provider_id):
        return (
            False,
            (
                f"{publishing_auth_method_name(normalized.auth_method)} is planned for "
                f"{publishing_provider_display_name(normalized.provider_id)}, "
                "but is not implemented yet."
            ),
            [],
        )
    client = publishing_provider_client(normalized.provider_id)
    if client is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return (
            False,
            f"{provider_name} browsing is not implemented yet.",
            [],
        )
    requested_kinds = content_kinds or provider_content_kinds(normalized.provider_id)
    allowed_kinds = set(provider_content_kinds(normalized.provider_id))
    filtered_kinds = tuple(kind for kind in requested_kinds if kind in allowed_kinds)
    if not filtered_kinds:
        return False, "No supported publishing content types are available for this provider.", []
    return client.browse_content(
        normalized,
        secret,
        content_kinds=filtered_kinds,
        statuses=statuses or ("publish", "draft"),
        timeout_seconds=timeout_seconds,
    )


def load_publishing_remote_item(
    profile: PublishingConnectionProfile,
    secret: str,
    *,
    content_kind: str,
    remote_id: str,
    timeout_seconds: float = 10.0,
) -> tuple[bool, str, PublishingRemoteDocument | None]:
    normalized = _normalized_profile(profile)
    if not normalized.site_url:
        return False, "Enter a site URL before opening publishing content.", None
    policy_error = _validate_endpoint_security(normalized.site_url)
    if policy_error:
        return False, policy_error, None
    if publishing_provider_definition(normalized.provider_id) is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return False, f"{provider_name} publishing provider is not registered.", None
    if normalized.auth_method not in provider_implemented_auth_methods(normalized.provider_id):
        return (
            False,
            (
                f"{publishing_auth_method_name(normalized.auth_method)} is planned for "
                f"{publishing_provider_display_name(normalized.provider_id)}, "
                "but is not implemented yet."
            ),
            None,
        )
    client = publishing_provider_client(normalized.provider_id)
    if client is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return (
            False,
            f"{provider_name} loading is not implemented yet.",
            None,
        )
    if content_kind not in provider_content_kinds(normalized.provider_id):
        return False, "That publishing content type is not supported for this provider.", None
    if not remote_id.strip():
        return False, "Select publishing content before opening it.", None
    return client.load_remote_item(
        normalized,
        secret,
        content_kind=content_kind,
        remote_id=remote_id,
        timeout_seconds=timeout_seconds,
    )


def update_publishing_remote_item(
    profile: PublishingConnectionProfile,
    secret: str,
    *,
    content_kind: str,
    remote_id: str,
    title: str,
    document_text: str,
    authoring_surface: str,
    status: str | None = None,
    timeout_seconds: float = 10.0,
) -> tuple[bool, str, PublishingRemoteDocument | None]:
    normalized = _normalized_profile(profile)
    if not normalized.site_url:
        return False, "Enter a site URL before updating publishing content.", None
    policy_error = _validate_endpoint_security(normalized.site_url)
    if policy_error:
        return False, policy_error, None
    if publishing_provider_definition(normalized.provider_id) is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return False, f"{provider_name} publishing provider is not registered.", None
    if normalized.auth_method not in provider_implemented_auth_methods(normalized.provider_id):
        return (
            False,
            (
                f"{publishing_auth_method_name(normalized.auth_method)} is planned for "
                f"{publishing_provider_display_name(normalized.provider_id)}, "
                "but is not implemented yet."
            ),
            None,
        )
    client = publishing_provider_client(normalized.provider_id)
    if client is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return False, f"{provider_name} updating is not implemented yet.", None
    if content_kind not in provider_content_kinds(normalized.provider_id):
        return False, "That publishing content type is not supported for this provider.", None
    if not remote_id.strip():
        return False, "Open a publishing item before updating remote content.", None
    clean_title = title.strip() or "(untitled)"
    body_html = _publishing_update_body_html(document_text, authoring_surface)
    return client.update_remote_item(
        normalized,
        secret,
        content_kind=content_kind,
        remote_id=remote_id,
        title=clean_title,
        body_html=body_html,
        timeout_seconds=timeout_seconds,
        status=status,
    )


def create_publishing_remote_item(
    profile: PublishingConnectionProfile,
    secret: str,
    *,
    content_kind: str,
    title: str,
    document_text: str,
    authoring_surface: str,
    status: str = "draft",
    timeout_seconds: float = 10.0,
) -> tuple[bool, str, PublishingRemoteDocument | None]:
    normalized = _normalized_profile(profile)
    if not normalized.site_url:
        return False, "Enter a site URL before creating publishing content.", None
    policy_error = _validate_endpoint_security(normalized.site_url)
    if policy_error:
        return False, policy_error, None
    if publishing_provider_definition(normalized.provider_id) is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return False, f"{provider_name} publishing provider is not registered.", None
    if normalized.auth_method not in provider_implemented_auth_methods(normalized.provider_id):
        return (
            False,
            (
                f"{publishing_auth_method_name(normalized.auth_method)} is planned for "
                f"{publishing_provider_display_name(normalized.provider_id)}, "
                "but is not implemented yet."
            ),
            None,
        )
    client = publishing_provider_client(normalized.provider_id)
    if client is None:
        provider_name = publishing_provider_display_name(normalized.provider_id)
        return False, f"{provider_name} publishing is not implemented yet.", None
    if content_kind not in provider_content_kinds(normalized.provider_id):
        return False, "That publishing content type is not supported for this provider.", None
    clean_title = title.strip() or "(untitled)"
    body_html = _publishing_update_body_html(document_text, authoring_surface)
    return client.create_remote_item(
        normalized,
        secret,
        content_kind=content_kind,
        title=clean_title,
        body_html=body_html,
        status=status.strip().lower() or "draft",
        timeout_seconds=timeout_seconds,
    )


def prepare_publishing_remote_content(
    body_html: str,
    *,
    requested_open_representation: str = PUBLISHING_OPEN_REPRESENTATION_READABLE_MARKDOWN,
) -> PreparedPublishingRemoteContent:
    requested = requested_open_representation.strip().lower()
    if requested == PUBLISHING_OPEN_REPRESENTATION_RAW_HTML:
        return PreparedPublishingRemoteContent(
            text=body_html,
            authoring_surface="html",
            open_representation=PUBLISHING_OPEN_REPRESENTATION_RAW_HTML,
        )
    if _should_fallback_to_raw_html(body_html):
        return PreparedPublishingRemoteContent(
            text=body_html,
            authoring_surface="html",
            open_representation=PUBLISHING_OPEN_REPRESENTATION_RAW_HTML,
        )
    markdown = html_to_markdown(body_html)
    if markdown.strip():
        return PreparedPublishingRemoteContent(
            text=markdown,
            authoring_surface="markdown",
            open_representation=PUBLISHING_OPEN_REPRESENTATION_READABLE_MARKDOWN,
        )
    return PreparedPublishingRemoteContent(
        text=body_html,
        authoring_surface="html",
        open_representation=PUBLISHING_OPEN_REPRESENTATION_RAW_HTML,
    )


def publishing_result_message(action: str, document: PublishingRemoteDocument) -> str:
    verb = "Updated" if action.strip().lower() == "updated" else "Created"
    content_kind = provider_content_kind_label(document.provider_id, document.content_kind).lower()
    title = document.title.strip() or "(untitled)"
    status = _display_status(document.status)
    lines = [
        f"{verb} {content_kind} on {_display_host(document.site_url)}.",
        f"Title: {title}",
        f"Status: {status}",
    ]
    remote_url = document.remote_url.strip()
    if remote_url:
        lines.append(f"Link: {remote_url}")
    return "\n".join(lines)


def _publishing_update_body_html(document_text: str, authoring_surface: str) -> str:
    normalized_surface = authoring_surface.strip().lower()
    if normalized_surface == "html":
        return document_text
    return render_preview_body(document_text, "markdown")


def _normalized_profile(profile: PublishingConnectionProfile) -> PublishingConnectionProfile:
    normalized = PublishingConnectionProfile.from_dict(asdict(profile))
    return normalized


def _should_fallback_to_raw_html(body_html: str) -> bool:
    lowered = body_html.lower()
    return any(tag in lowered for tag in _RAW_HTML_FALLBACK_TAGS)


def _publishing_secret_path(connection_id: str) -> Path:
    return app_data_dir() / f"publishing-secret-{connection_id}.json"


def _credential_target(connection_id: str) -> str:
    return f"QUILL:publishing:{connection_id}:secret"


def _load_secret_from_credential_manager(connection_id: str) -> str:
    if not credential_manager_available():
        return ""
    credential = load_generic_credential(_credential_target(connection_id))
    if credential is None:
        return ""
    return credential.secret.strip()


def _save_secret_with_credential_manager(connection_id: str, secret: str) -> bool:
    clean = secret.strip()
    if not clean or not credential_manager_available():
        return False
    try:
        save_generic_credential(_credential_target(connection_id), clean)
    except OSError:
        return False
    return True


def _delete_secret_from_credential_manager(connection_id: str) -> None:
    if not credential_manager_available():
        return
    try:
        delete_generic_credential(_credential_target(connection_id))
    except OSError:
        return


def _validate_endpoint_security(site_url: str) -> str | None:
    parsed = urlparse(site_url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if scheme == "https":
        return None
    if scheme == "http" and _is_local_host(hostname):
        return None
    return (
        "Only HTTPS endpoints are allowed for remote publishing sites. "
        "HTTP is only supported for local loopback/private-network endpoints."
    )


def _is_local_host(hostname: str) -> bool:
    if not hostname:
        return False
    if hostname in {"localhost", "::1"}:
        return True
    if hostname.endswith(".localhost"):
        return True
    if hostname.startswith("127."):
        return True
    if hostname.startswith("10.") or hostname.startswith("192.168."):
        return True
    if hostname.startswith("172."):
        try:
            second_octet = int(hostname.split(".")[1])
        except (IndexError, ValueError):
            return False
        return 16 <= second_octet <= 31
    return False


def _display_host(site_url: str) -> str:
    return (urlparse(site_url).netloc or site_url.strip()).strip().rstrip("/")


def _display_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "publish":
        return "published"
    if normalized:
        return normalized.replace("_", " ")
    return "unknown"
