from __future__ import annotations

import base64
import html
import json
import re
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.publishing_providers import (
    WORDPRESS_PROVIDER_ID,
    PublishingOperationCancelled,
    provider_content_kind_label,
    publishing_provider_display_name,
)

_HTML_ENTITY_PATTERN = re.compile(r"&(?:#\d+|#[xX][0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);")
_PRESERVE_HTML_ESCAPES = {"<", ">", "&"}


@dataclass(frozen=True, slots=True)
class PublishingRemoteItemSummary:
    provider_id: str
    site_url: str
    remote_id: str
    remote_url: str
    title: str
    status: str
    content_kind: str
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class PublishingRemoteDocument:
    provider_id: str
    site_url: str
    remote_id: str
    remote_url: str
    title: str
    status: str
    content_kind: str
    body: str
    updated_at: str = ""
    scheduled_for: str = ""


class PublishingProviderClient(Protocol):
    provider_id: str

    def verify_connection(
        self,
        profile: object,
        secret: str,
        *,
        timeout_seconds: float,
    ) -> tuple[bool, str]: ...

    def browse_content(
        self,
        profile: object,
        secret: str,
        *,
        content_kinds: tuple[str, ...],
        statuses: tuple[str, ...],
        timeout_seconds: float,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[bool, str, list[PublishingRemoteItemSummary]]: ...

    def load_remote_item(
        self,
        profile: object,
        secret: str,
        *,
        content_kind: str,
        remote_id: str,
        timeout_seconds: float,
    ) -> tuple[bool, str, PublishingRemoteDocument | None]: ...

    def update_remote_item(
        self,
        profile: object,
        secret: str,
        *,
        content_kind: str,
        remote_id: str,
        title: str,
        body_html: str,
        timeout_seconds: float,
        status: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> tuple[bool, str, PublishingRemoteDocument | None]: ...

    def create_remote_item(
        self,
        profile: object,
        secret: str,
        *,
        content_kind: str,
        title: str,
        body_html: str,
        status: str,
        timeout_seconds: float,
        scheduled_at: datetime | None = None,
    ) -> tuple[bool, str, PublishingRemoteDocument | None]: ...


class WordPressPublishingClient:
    provider_id = WORDPRESS_PROVIDER_ID

    def verify_connection(
        self,
        profile: object,
        secret: str,
        *,
        timeout_seconds: float,
    ) -> tuple[bool, str]:
        account_identifier = str(getattr(profile, "account_identifier", "")).strip()
        site_url = str(getattr(profile, "site_url", "")).strip()
        provider_id = str(getattr(profile, "provider_id", WORDPRESS_PROVIDER_ID)).strip()
        if not account_identifier:
            return False, "Enter a username or email before verifying the publishing connection."
        if not secret.strip():
            return (
                False,
                "Enter an application password before verifying the publishing connection.",
            )
        endpoint = _wordpress_users_me_endpoint(site_url)
        request = Request(
            endpoint,
            headers={
                "Accept": "application/json",
                "Authorization": _basic_auth_header(account_identifier, secret),
            },
            method="GET",
        )
        try:
            with urlopen(
                request, timeout=timeout_seconds, context=_context_for(endpoint)
            ) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except HTTPError as exc:
            if exc.code == 401:
                return (
                    False,
                    "Authentication failed. Check the sign-in name or application password.",
                )
            if exc.code == 403:
                return False, "Access denied. This account cannot publish on that site."
            return (
                False,
                (
                    f"{publishing_provider_display_name(provider_id)} returned HTTP "
                    f"{exc.code} while verifying the connection."
                ),
            )
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            text = str(reason).strip() or "unknown network error"
            if "timed out" in text.lower():
                return False, "Connection timed out. Check the site URL and try again."
            return False, f"Could not reach the publishing site: {text}"
        except TimeoutError:
            return False, "Connection timed out. Check the site URL and try again."
        except json.JSONDecodeError:
            return False, "The publishing site returned an invalid response."
        if not isinstance(payload, dict):
            return False, "The publishing site returned an invalid response."
        return True, f"Publishing connection verified for {_display_host(site_url)}."

    def browse_content(
        self,
        profile: object,
        secret: str,
        *,
        content_kinds: tuple[str, ...],
        statuses: tuple[str, ...],
        timeout_seconds: float,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[bool, str, list[PublishingRemoteItemSummary]]:
        account_identifier = str(getattr(profile, "account_identifier", "")).strip()
        site_url = str(getattr(profile, "site_url", "")).strip()
        provider_id = str(getattr(profile, "provider_id", WORDPRESS_PROVIDER_ID)).strip()
        if not account_identifier:
            return False, "Enter a username or email before browsing publishing content.", []
        if not secret.strip():
            return False, "Enter an application password before browsing publishing content.", []
        results: list[PublishingRemoteItemSummary] = []
        failures: list[str] = []
        requested_statuses = _normalized_statuses(statuses)
        for content_kind in content_kinds:
            if is_cancelled is not None and is_cancelled():
                raise PublishingOperationCancelled("Browse publishing content cancelled.")
            endpoint = _wordpress_collection_endpoint(
                site_url,
                content_kind,
                statuses=requested_statuses,
            )
            try:
                payload = _request_json(
                    endpoint,
                    account_identifier=account_identifier,
                    secret=secret,
                    timeout_seconds=timeout_seconds,
                )
            except _PublishingRequestError as exc:
                failures.append(
                    f"{_content_kind_label(provider_id, content_kind)}: {exc.message.rstrip('.')}"
                )
                continue
            if not isinstance(payload, list):
                failures.append(
                    f"{_content_kind_label(provider_id, content_kind)}: invalid response"
                )
                continue
            for item in payload:
                summary = _wordpress_summary_from_payload(site_url, content_kind, item)
                if summary is not None:
                    results.append(summary)
        if failures and not results:
            return False, failures[0], []
        results.sort(key=lambda item: (item.updated_at, item.title.lower()), reverse=True)
        host = _display_host(site_url)
        if failures:
            failed_scopes = "; ".join(failures)
            return (
                True,
                (
                    f"Loaded partial publishing content from {host}. "
                    f"Some content could not be loaded: {failed_scopes}. "
                    "Try again with a narrower content scope."
                ),
                results,
            )
        return True, f"Loaded publishing content from {host}.", results

    def load_remote_item(
        self,
        profile: object,
        secret: str,
        *,
        content_kind: str,
        remote_id: str,
        timeout_seconds: float,
    ) -> tuple[bool, str, PublishingRemoteDocument | None]:
        account_identifier = str(getattr(profile, "account_identifier", "")).strip()
        site_url = str(getattr(profile, "site_url", "")).strip()
        if not account_identifier:
            return False, "Enter a username or email before opening publishing content.", None
        if not secret.strip():
            return False, "Enter an application password before opening publishing content.", None
        endpoint = _wordpress_item_endpoint(site_url, content_kind, remote_id)
        try:
            payload = _request_json(
                endpoint,
                account_identifier=account_identifier,
                secret=secret,
                timeout_seconds=timeout_seconds,
            )
        except _PublishingRequestError as exc:
            return False, exc.message, None
        if not isinstance(payload, dict):
            return False, "The publishing site returned an invalid response.", None
        document = _wordpress_document_from_payload(site_url, content_kind, payload)
        if document is None:
            return False, "The publishing site returned an invalid response.", None
        host = _display_host(site_url)
        return True, f"Opened publishing content from {host}.", document

    def update_remote_item(
        self,
        profile: object,
        secret: str,
        *,
        content_kind: str,
        remote_id: str,
        title: str,
        body_html: str,
        timeout_seconds: float,
        status: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> tuple[bool, str, PublishingRemoteDocument | None]:
        account_identifier = str(getattr(profile, "account_identifier", "")).strip()
        site_url = str(getattr(profile, "site_url", "")).strip()
        if not account_identifier:
            return False, "Enter a username or email before updating publishing content.", None
        if not secret.strip():
            return False, "Enter an application password before updating publishing content.", None
        endpoint = _wordpress_item_endpoint(site_url, content_kind, remote_id)
        payload = {
            "title": title,
            "content": body_html,
        }
        if status is not None:
            clean_status = status.strip().lower()
            if clean_status:
                payload["status"] = clean_status
        if scheduled_at is not None:
            payload["date_gmt"] = _wordpress_date_gmt(scheduled_at)
        try:
            result = _request_json(
                endpoint,
                account_identifier=account_identifier,
                secret=secret,
                timeout_seconds=timeout_seconds,
                method="POST",
                json_payload=payload,
            )
        except _PublishingRequestError as exc:
            return False, exc.message, None
        if not isinstance(result, dict):
            return False, "The publishing site returned an invalid response.", None
        document = _wordpress_document_from_payload(site_url, content_kind, result)
        if document is None:
            return False, "The publishing site returned an invalid response.", None
        host = _display_host(site_url)
        return True, f"Updated publishing content on {host}.", document

    def create_remote_item(
        self,
        profile: object,
        secret: str,
        *,
        content_kind: str,
        title: str,
        body_html: str,
        status: str,
        timeout_seconds: float,
        scheduled_at: datetime | None = None,
    ) -> tuple[bool, str, PublishingRemoteDocument | None]:
        account_identifier = str(getattr(profile, "account_identifier", "")).strip()
        site_url = str(getattr(profile, "site_url", "")).strip()
        if not account_identifier:
            return False, "Enter a username or email before creating publishing content.", None
        if not secret.strip():
            return (
                False,
                "Enter an application password before creating publishing content.",
                None,
            )
        endpoint = _wordpress_collection_write_endpoint(site_url, content_kind)
        payload = {
            "title": title,
            "content": body_html,
            "status": status,
        }
        if scheduled_at is not None:
            payload["date_gmt"] = _wordpress_date_gmt(scheduled_at)
        try:
            result = _request_json(
                endpoint,
                account_identifier=account_identifier,
                secret=secret,
                timeout_seconds=timeout_seconds,
                method="POST",
                json_payload=payload,
            )
        except _PublishingRequestError as exc:
            return False, exc.message, None
        if not isinstance(result, dict):
            return False, "The publishing site returned an invalid response.", None
        document = _wordpress_document_from_payload(site_url, content_kind, result)
        if document is None:
            return False, "The publishing site returned an invalid response.", None
        host = _display_host(site_url)
        return True, f"Created publishing content on {host}.", document


_PUBLISHING_PROVIDER_CLIENTS: dict[str, PublishingProviderClient] = {
    WORDPRESS_PROVIDER_ID: WordPressPublishingClient(),
}


def register_publishing_provider_client(client: PublishingProviderClient) -> None:
    provider_id = client.provider_id.strip().lower()
    if not provider_id:
        raise ValueError("Publishing provider client id is required.")
    _PUBLISHING_PROVIDER_CLIENTS[provider_id] = client


def unregister_publishing_provider_client(provider_id: str) -> None:
    normalized = provider_id.strip().lower()
    if normalized == WORDPRESS_PROVIDER_ID:
        raise ValueError("The built-in WordPress publishing client cannot be unregistered.")
    _PUBLISHING_PROVIDER_CLIENTS.pop(normalized, None)


def publishing_provider_client(provider_id: str) -> PublishingProviderClient | None:
    return _PUBLISHING_PROVIDER_CLIENTS.get(provider_id.strip().lower())


@dataclass(frozen=True, slots=True)
class _PublishingRequestError(CodedError):
    code = "QUILL-PUBLISH-CLIENT-REQUEST"
    message: str


def _request_json(
    endpoint: str,
    *,
    account_identifier: str,
    secret: str,
    timeout_seconds: float,
    method: str = "GET",
    json_payload: object | None = None,
) -> object:
    body: bytes | None = None
    headers = {
        "Accept": "application/json",
        "Authorization": _basic_auth_header(account_identifier, secret),
    }
    if json_payload is not None:
        body = json.dumps(json_payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        endpoint,
        headers=headers,
        data=body,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout_seconds, context=_context_for(endpoint)) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        if exc.code == 401:
            raise _PublishingRequestError(
                "Authentication failed. Check the sign-in name or application password."
            ) from exc
        if exc.code == 403:
            raise _PublishingRequestError(
                "Access denied. This account cannot access publishing content on that site."
            ) from exc
        if exc.code == 404:
            raise _PublishingRequestError(
                "The requested publishing content could not be found."
            ) from exc
        if exc.code == 400 and method != "GET":
            raise _PublishingRequestError(
                "The publishing site rejected the remote update request."
            ) from exc
        raise _PublishingRequestError(
            f"Publishing site returned HTTP {exc.code} while "
            f"{'loading content' if method == 'GET' else 'updating content'}."
        ) from exc
    except URLError as exc:
        reason = getattr(exc, "reason", None)
        text = str(reason).strip() or "unknown network error"
        if "timed out" in text.lower():
            raise _PublishingRequestError(
                "Connection timed out. Check the site URL and try again."
            ) from exc
        raise _PublishingRequestError(f"Could not reach the publishing site: {text}") from exc
    except TimeoutError as exc:
        raise _PublishingRequestError(
            "Connection timed out. Check the site URL and try again."
        ) from exc
    except json.JSONDecodeError as exc:
        raise _PublishingRequestError("The publishing site returned an invalid response.") from exc


def _wordpress_collection_endpoint(
    site_url: str,
    content_kind: str,
    *,
    statuses: tuple[str, ...],
) -> str:
    query = urlencode({
        "context": "edit",
        "per_page": "50",
        "status": ",".join(statuses),
        "_fields": "id,link,title,status,modified_gmt,type",
    })
    return site_url.rstrip("/") + f"/wp-json/wp/v2/{_wordpress_kind_path(content_kind)}?{query}"


def _wordpress_collection_write_endpoint(site_url: str, content_kind: str) -> str:
    query = urlencode({
        "context": "edit",
        "_fields": "id,link,title,status,modified_gmt,date_gmt,type,content",
    })
    return site_url.rstrip("/") + f"/wp-json/wp/v2/{_wordpress_kind_path(content_kind)}?{query}"


def _wordpress_item_endpoint(site_url: str, content_kind: str, remote_id: str) -> str:
    query = urlencode({
        "context": "edit",
        "_fields": "id,link,title,status,modified_gmt,date_gmt,type,content",
    })
    return (
        site_url.rstrip("/")
        + f"/wp-json/wp/v2/{_wordpress_kind_path(content_kind)}/{remote_id.strip()}?{query}"
    )


def _wordpress_users_me_endpoint(site_url: str) -> str:
    return site_url.rstrip("/") + "/wp-json/wp/v2/users/me?context=edit"


def _wordpress_kind_path(content_kind: str) -> str:
    normalized = content_kind.strip().lower()
    if normalized == "page":
        return "pages"
    return "posts"


def _wordpress_summary_from_payload(
    site_url: str,
    content_kind: str,
    payload: object,
) -> PublishingRemoteItemSummary | None:
    if not isinstance(payload, dict):
        return None
    remote_id = str(payload.get("id", "")).strip()
    if not remote_id:
        return None
    title = _wordpress_rendered_text(payload.get("title")) or "(untitled)"
    return PublishingRemoteItemSummary(
        provider_id=WORDPRESS_PROVIDER_ID,
        site_url=site_url,
        remote_id=remote_id,
        remote_url=str(payload.get("link", "")).strip(),
        title=title,
        status=str(payload.get("status", "")).strip() or "unknown",
        content_kind=_normalized_content_kind(payload.get("type"), fallback=content_kind),
        updated_at=str(payload.get("modified_gmt", "")).strip(),
    )


def _wordpress_document_from_payload(
    site_url: str,
    content_kind: str,
    payload: object,
) -> PublishingRemoteDocument | None:
    if not isinstance(payload, dict):
        return None
    remote_id = str(payload.get("id", "")).strip()
    if not remote_id:
        return None
    body = _wordpress_rendered_text(payload.get("content"))
    return PublishingRemoteDocument(
        provider_id=WORDPRESS_PROVIDER_ID,
        site_url=site_url,
        remote_id=remote_id,
        remote_url=str(payload.get("link", "")).strip(),
        title=_wordpress_rendered_text(payload.get("title")) or "(untitled)",
        status=str(payload.get("status", "")).strip() or "unknown",
        content_kind=_normalized_content_kind(payload.get("type"), fallback=content_kind),
        body=body,
        updated_at=str(payload.get("modified_gmt", "")).strip(),
        scheduled_for=str(payload.get("date_gmt", "")).strip(),
    )


def _wordpress_rendered_text(value: object) -> str:
    if isinstance(value, dict):
        rendered = value.get("rendered")
        return _normalize_remote_html_text(str(rendered).strip()) if rendered is not None else ""
    if value is None:
        return ""
    return _normalize_remote_html_text(str(value).strip())


def _normalize_remote_html_text(value: str) -> str:
    if "&" not in value:
        return value

    def _replace(match: re.Match[str]) -> str:
        entity = match.group(0)
        decoded = html.unescape(entity)
        if decoded == entity:
            return entity
        if decoded in _PRESERVE_HTML_ESCAPES:
            return entity
        if decoded == "\xa0":
            return " "
        return decoded

    normalized = _HTML_ENTITY_PATTERN.sub(_replace, value)
    return normalized.replace("\xa0", " ")


def _normalized_content_kind(value: object, *, fallback: str) -> str:
    normalized = str(value or fallback).strip().lower()
    if normalized == "page":
        return "page"
    return "post"


def _wordpress_date_gmt(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def _normalized_statuses(statuses: tuple[str, ...]) -> tuple[str, ...]:
    allowed = {"publish", "draft"}
    normalized = tuple(
        dict.fromkeys(
            status.strip().lower() for status in statuses if status.strip().lower() in allowed
        )
    )
    return normalized or ("publish", "draft")


def _context_for(endpoint: str) -> ssl.SSLContext | None:
    if urlparse(endpoint).scheme == "https":
        return verified_ssl_context()
    return None


def _display_host(site_url: str) -> str:
    return (urlparse(site_url).netloc or site_url.strip()).strip().rstrip("/")


def _content_kind_label(provider_id: str, content_kind: str) -> str:
    return provider_content_kind_label(provider_id, content_kind, plural=True)


def _basic_auth_header(identifier: str, secret: str) -> str:
    token = f"{identifier.strip()}:{secret.strip()}".encode()
    return "Basic " + base64.b64encode(token).decode("ascii")
