"""The Scribe for Documents REST API (PRD 7.1), written from Pneuma's client.

Why our own client and not Pneuma's ``scribe-client`` wheel: the wheel is a
compiled Rust module, so GATE-9 could not see its calls, and it lacks rename,
feedback, account defaults, billing and account info.

**One egress site.** Every request goes through :func:`_open`, the call site
the network egress audit names. It refuses anything but HTTPS (a loopback
``http`` address is allowed for tests), checks certificates with
:func:`quill.core.net.verified_ssl_context`, and does **not** follow
redirects itself: a download is answered with a redirect to storage, and
following it with urllib would carry the bearer token to the storage host.
:meth:`ScribeClient.download` follows it by hand, without the token.

**Tokens** come from a :class:`TokenSource` (:class:`quill.core.scribe.auth.
ScribeSession`), which refreshes five minutes before expiry; a 401 forces one
refresh and one retry (7.2).

**Logging.** Only methods, paths (document IDs), status codes and byte counts
are logged; never a token, a password, a file's contents or a response body.

wx-free; tests hand :class:`ScribeClient` a fake ``transport``.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlencode, urlsplit

from quill.core.scribe.errors import (
    GENERIC_MESSAGE,
    ScribeCancelled,
    ScribeError,
    ScribeNotCompleteError,
    ScribeOfflineError,
    ScribeSaveError,
    ScribeSignInError,
    error_from_server,
)
from quill.core.scribe.forms import content_disposition_file_name, multipart, total_bytes
from quill.core.scribe.model import (
    Account,
    DocumentSummary,
    Output,
    ScribeSettings,
    parse_documents,
    parse_outputs,
    parse_pairs,
    parse_voices,
)

logger = logging.getLogger(__name__)

_TIMEOUT_S = 60.0
_UPLOAD_TIMEOUT_S = 600.0
_CHUNK = 64 * 1024
_DOWNLOAD_ATTEMPTS = 4
USER_AGENT = "QUILL (Scribe for Documents)"


class Response(Protocol):
    status: int
    headers: Mapping[str, str]

    def read(self, size: int = -1) -> bytes: ...
    def close(self) -> None: ...


#: ``transport(request, timeout) -> Response``. Never raises for an HTTP
#: status (an error status comes back as a response); raises ``OSError`` for a
#: network failure.
Transport = Callable[[urllib.request.Request, float], Response]
ProgressFn = Callable[[int, int | None], None]
CancelFn = Callable[[], bool]


class TokenSource(Protocol):
    def access_token(self) -> str: ...
    def force_refresh(self) -> str: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:  # type: ignore[override]
        return None  # the 3xx comes back as an HTTPError, read as a response


class _Wrapped:
    """A urllib response or HTTPError seen as one :class:`Response` shape."""

    def __init__(self, raw: Any) -> None:
        self._raw = raw
        self.status: int = int(getattr(raw, "status", None) or getattr(raw, "code", 0) or 0)
        self.headers: Mapping[str, str] = {
            str(k).lower(): str(v) for k, v in (raw.headers or {}).items()
        }

    def read(self, size: int = -1) -> bytes:
        data: bytes = self._raw.read(size) if size >= 0 else self._raw.read()
        return data

    def close(self) -> None:
        try:
            self._raw.close()
        except Exception:  # noqa: BLE001 - closing never fails a request
            pass


def _open(request: urllib.request.Request, timeout: float) -> Response:
    """GATE-9: the only place Scribe's REST calls leave the computer."""
    from quill.core.net import verified_ssl_context

    opener = urllib.request.build_opener(
        _NoRedirect(), urllib.request.HTTPSHandler(context=verified_ssl_context())
    )
    try:
        return _Wrapped(opener.open(request, timeout=timeout))
    except urllib.error.HTTPError as error:
        return _Wrapped(error)


def require_secure(url: str) -> None:
    """HTTPS only; plain HTTP only to this computer (tests and the fake server)."""
    parts = urlsplit(url)
    if parts.scheme == "https":
        return
    if parts.scheme == "http" and parts.hostname in {"127.0.0.1", "localhost", "::1"}:
        return
    raise ScribeError("Scribe for Documents must be reached over a secure (HTTPS) address.")


class ScribeClient:
    """The REST endpoints, each a method; errors are :mod:`.errors` classes."""

    def __init__(
        self,
        tokens: TokenSource,
        *,
        base_url: str | None = None,
        transport: Transport | None = None,
        locale: str = "",
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        from quill.core.scribe import base_url as default_base

        self._tokens = tokens
        self.base_url = (base_url or default_base()).rstrip("/")
        require_secure(self.base_url)
        self._transport = transport or _open
        self._locale = locale
        self._sleep = sleep

    # -------------------------------------------------------------- plumbing

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        content_type: str = "",
        headers: Mapping[str, str] | None = None,
        token: str | None = None,
        timeout: float = _TIMEOUT_S,
    ) -> Response:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        require_secure(url)
        request = urllib.request.Request(url, data=body, method=method)
        request.add_header("User-Agent", USER_AGENT)
        request.add_header("Accept", "application/json")
        if self._locale:
            request.add_header("Accept-Language", self._locale)
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        if content_type:
            request.add_header("Content-Type", content_type)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            return self._transport(request, timeout)
        except OSError as error:
            logger.info(
                "Scribe %s %s: network failure (%s)", method, _log_path(path), type(error).__name__
            )
            raise ScribeOfflineError(
                "Couldn't connect to Scribe. Check your connection and try again."
            ) from None

    def _authed(self, method: str, path: str, **kwargs: Any) -> Response:
        """A request with the bearer token, refreshed once on a 401 (7.2)."""
        response = self._request(method, path, token=self._tokens.access_token(), **kwargs)
        if response.status == 401:
            response.close()
            response = self._request(method, path, token=self._tokens.force_refresh(), **kwargs)
            if response.status == 401:
                response.close()
                raise ScribeSignInError(
                    "Your Scribe for Documents sign-in has ended. Sign in again to continue.",
                    reason="unauthenticated",
                )
        logger.info("Scribe %s %s -> %s", method, _log_path(path), response.status)
        return response

    def _json(self, method: str, path: str, payload: Any = None, **kwargs: Any) -> Any:
        if payload is not None:
            kwargs["body"] = json.dumps(payload).encode("utf-8")
            kwargs["content_type"] = "application/json"
        response = self._authed(method, path, **kwargs)
        try:
            raw = response.read()
        finally:
            response.close()
        if response.status >= 400:
            raise _api_error(response.status, raw)
        if not raw.strip():
            return {}
        try:
            return json.loads(raw.decode("utf-8", errors="replace"))
        except ValueError:
            raise ScribeError(GENERIC_MESSAGE, reason="decode") from None

    # ------------------------------------------------------------ documents

    def create_document(
        self,
        *,
        path: Path | None = None,
        url: str = "",
        password: str = "",
        settings: ScribeSettings | None = None,
    ) -> str:
        """``POST /api/documents`` with a file or a link; returns the document ID.

        The free ``html_stream`` preview starts on its own. *password* is used
        for this one request and never kept (10.2.6). *settings* go in as
        ``document[settings][field]`` form fields, the full set: the HTML
        conversion starts as soon as the upload lands, so language, picture
        descriptions, mathematics and large print can only be set here (3.3).
        """
        fields: list[tuple[str, str]] = []
        if url:
            fields.append(("document[url]", url))
        if password:
            fields.append(("document[password]", password))
        if settings is not None:
            fields.extend(settings.to_upload_fields())
        file_field = ("document[file]", path) if path is not None and not url else None
        try:
            body, content_type = multipart(fields, file_field)
        except OSError as error:
            raise ScribeError(f"The file could not be read: {error.strerror or error}") from None
        data = self._json(
            "POST",
            "/api/documents",
            body=body,
            content_type=content_type,
            timeout=_UPLOAD_TIMEOUT_S,
        )
        document_id = str((data or {}).get("document_id") or "")
        if not document_id:
            raise ScribeError(GENERIC_MESSAGE, reason="no_document_id")
        logger.info("Scribe document created id=%s", document_id)
        return document_id

    def list_documents(self) -> tuple[list[DocumentSummary], int | None]:
        """Every document in the account with its outputs, and pages remaining."""
        data = self._json("GET", "/api/documents")
        pages = data.get("pages_remaining") if isinstance(data, dict) else None
        documents = parse_documents(data.get("documents") if isinstance(data, dict) else [])
        return documents, int(pages) if isinstance(pages, (int, float)) else None

    def list_trash(self) -> list[DocumentSummary]:
        data = self._json("GET", "/api/documents/trash")
        return parse_documents(data.get("documents") if isinstance(data, dict) else [])

    def trash(self, document_id: str) -> None:
        self._json("POST", f"/api/documents/{_seg(document_id)}/trash")

    def recover(self, document_id: str) -> None:
        self._json("POST", f"/api/documents/{_seg(document_id)}/recover")

    def delete_forever(self, document_id: str) -> None:
        """Permanent; the document must already be in the trash."""
        self._json("DELETE", f"/api/documents/{_seg(document_id)}")

    def rename(self, document_id: str, title: str) -> DocumentSummary | None:
        data = self._json(
            "PATCH", f"/api/documents/{_seg(document_id)}", {"document": {"title": title}}
        )
        return DocumentSummary.from_mapping(data)

    def ask_for_review(self, document_id: str, comment: str) -> None:
        """Send for human review (Scribe's paid remediation) with a comment."""
        self._json("POST", f"/api/documents/{_seg(document_id)}/feedback", {"comment": comment})

    def list_outputs(self, document_id: str) -> tuple[list[Output], bool]:
        """The document's outputs, and whether it still needs its password."""
        data = self._json("GET", f"/api/documents/{_seg(document_id)}/outputs")
        if not isinstance(data, dict):
            return [], False
        return parse_outputs(data.get("outputs")), bool(data.get("is_password_needed", False))

    # -------------------------------------------------------------- settings

    def get_settings(self, document_id: str) -> ScribeSettings:
        return ScribeSettings.from_mapping(
            self._json("GET", f"/api/documents/{_seg(document_id)}/settings")
        )

    def update_settings(
        self, document_id: str, settings: ScribeSettings, *, leave_out: frozenset[str] = frozenset()
    ) -> None:
        """``PATCH /api/documents/{id}/settings``: applies to formats not made yet."""
        self._json(
            "PATCH",
            f"/api/documents/{_seg(document_id)}/settings",
            {"settings": settings.to_update(leave_out=leave_out)},
        )

    def default_settings(self) -> ScribeSettings:
        """``GET /api/document_settings``: the person's account defaults, the
        convert dialog's starting values (3.3). Read only, never changed here."""
        return ScribeSettings.from_mapping(self._json("GET", "/api/document_settings"))

    def update_default_settings(self, settings: ScribeSettings) -> None:
        """Changes the Scribe website's defaults too; only when the person asks."""
        self._json("PATCH", "/api/document_settings", {"settings": settings.to_update()})

    def languages(self) -> list[tuple[str, str]]:
        return parse_pairs(self._json("GET", "/api/settings/languages").get("languages"))

    def dialects(self) -> dict[str, list[tuple[str, str]]]:
        raw = self._json("GET", "/api/settings/dialects").get("dialects") or {}
        return {str(k): parse_pairs(v) for k, v in raw.items()} if isinstance(raw, dict) else {}

    def voices(self) -> dict[str, list[tuple[str, str, bool]]]:
        raw = self._json("GET", "/api/settings/voices").get("voices") or {}
        return {str(k): parse_voices(v) for k, v in raw.items()} if isinstance(raw, dict) else {}

    def braille_tables(self) -> list[tuple[str, str]]:
        return parse_pairs(self._json("GET", "/api/settings/braille_tables").get("braille_tables"))

    def voice_sample_url(self, short_name: str) -> str:
        """A voice's sample MP3; it needs no token. Letters, digits and ``-`` only."""
        if not short_name or not all(c.isalnum() or c == "-" for c in short_name):
            raise ScribeError(f"There's no sample of the voice {short_name!r}.", reason="not_found")
        return f"{self.base_url}/sounds/tts-samples/{short_name}.mp3"

    def voice_sample(self, short_name: str) -> bytes:
        """The sample's MP3 bytes (no token is sent: the sample is public)."""
        response = self._request("GET", self.voice_sample_url(short_name))
        try:
            data = response.read()
        finally:
            response.close()
        if response.status >= 400:
            raise ScribeError(f"There's no sample of the voice {short_name!r}.", reason="not_found")
        return data

    # --------------------------------------------------------------- account

    def account(self) -> Account:
        """Who is signed in and pages remaining (``account_info`` + ``billing``)."""
        info = self._json("GET", "/api/account_info")
        billing = self._json("GET", "/api/billing")
        return Account.from_mappings(info, billing)

    def browser_entry_url(self, return_to: str = "/") -> str:
        """A link that signs the browser in as this person, then opens *return_to*.

        The token is in the link, so the link is handed straight to the browser
        and never shown, copied or logged.
        """
        token = self._tokens.access_token()
        query = urlencode({"token": token, "state": json.dumps({"return_to": return_to})})
        return f"{self.base_url}/auth/browser_from_oauth?{query}"

    # -------------------------------------------------------------- download

    def download(
        self,
        document_id: str,
        format_id: str,
        folder: Path,
        *,
        name_for: Callable[[str], Path] | None = None,
        on_progress: ProgressFn | None = None,
        cancel_requested: CancelFn | None = None,
    ) -> Path:
        """Download one output into *folder*; returns the saved file.

        Resumes with ``Range`` after a drop (7.6). The server's file name is
        used, made safe, and never overwrites a file (*name_for* picks the final
        path, normally :func:`quill.core.scribe.library.unique_path`).
        """
        from quill.core.scribe.library import safe_file_name, unique_path

        api = f"/api/documents/{_seg(document_id)}/outputs/{_seg(format_id)}/download"
        response = self._authed("GET", api)
        file_name = content_disposition_file_name(response.headers.get("content-disposition", ""))
        target_url = ""
        if 300 <= response.status < 400:
            target_url = response.headers.get("location", "")
            response.close()
            if not target_url:
                raise ScribeError(GENERIC_MESSAGE, reason="redirect_without_location")
            response = None  # type: ignore[assignment]
        elif response.status >= 400:
            raw = response.read()
            response.close()
            if response.status == 409 or b"conversion_not_complete" in raw:
                raise ScribeNotCompleteError("That format is not finished converting yet.")
            raise _api_error(response.status, raw)

        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ScribeSaveError(
                f"{folder} could not be created: {error.strerror or error}"
            ) from None
        part = folder / f".{document_id}.{format_id}.part"
        total: int | None = None
        for attempt in range(_DOWNLOAD_ATTEMPTS):
            have = part.stat().st_size if part.exists() else 0
            if response is None:
                headers = {"Range": f"bytes={have}-"} if have else {}
                try:
                    response = self._request("GET", target_url, headers=headers)
                except ScribeOfflineError:
                    if attempt + 1 >= _DOWNLOAD_ATTEMPTS:
                        raise
                    self._sleep(2.0 * (attempt + 1))
                    continue
                if response.status >= 400:
                    raw = response.read()
                    response.close()
                    raise _api_error(response.status, raw)
            if not file_name:
                file_name = content_disposition_file_name(
                    response.headers.get("content-disposition", "")
                )
            if response.status != 206:
                have = 0  # the server sent the whole file: start again
            total = total_bytes(response, have)
            try:
                done = self._stream(response, part, have, total, on_progress, cancel_requested)
            except OSError:
                done = False
            finally:
                response.close()
                response = None  # type: ignore[assignment]
            if done:
                break
            if attempt + 1 >= _DOWNLOAD_ATTEMPTS:
                raise ScribeOfflineError("The download was interrupted. Try again.")
            self._sleep(2.0 * (attempt + 1))
        from quill.core.scribe.model import format_by_id

        found = format_by_id(format_id)
        fallback = f"{document_id}{found.extension if found else ''}"
        safe = safe_file_name(file_name or fallback)
        final = (name_for or (lambda n: unique_path(folder / n)))(safe)
        try:
            part.replace(final)
        except OSError as error:
            raise ScribeSaveError(
                f"{final.parent} is not writable: {error.strerror or error}"
            ) from None
        logger.info(
            "Scribe download id=%s format=%s bytes=%s", document_id, format_id, final.stat().st_size
        )
        return final

    @staticmethod
    def _stream(
        response: Response,
        part: Path,
        have: int,
        total: int | None,
        on_progress: ProgressFn | None,
        cancel_requested: CancelFn | None,
    ) -> bool:
        mode = "ab" if have else "wb"
        try:
            handle = part.open(mode)
        except OSError as error:
            raise ScribeSaveError(
                f"{part.parent} is not writable: {error.strerror or error}"
            ) from None
        received = have
        with handle:
            if on_progress is not None:
                on_progress(received, total)
            while True:
                if cancel_requested is not None and cancel_requested():
                    raise ScribeCancelled("Download stopped.")
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                try:
                    handle.write(chunk)
                except OSError as error:
                    raise ScribeSaveError(
                        f"{part.parent} could not be written to: {error.strerror or error}"
                    ) from None
                received += len(chunk)
                if on_progress is not None:
                    on_progress(received, total)
        return total is None or received >= total


def _api_error(status: int, raw: bytes) -> ScribeError:
    """The server's ``{"error": {"code", "message"}}`` envelope as a coded error.

    A body that is not the envelope (an HTML error page, a proxy's text) is
    never shown; the generic sentence is used instead.
    """
    try:
        body = json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError:
        body = None
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return error_from_server(
            str(error.get("code") or ""),
            str(error.get("message") or "") or None,
            purchase_url=str(error.get("purchase_url") or ""),
            status=status,
        )
    if isinstance(error, str):  # an OAuth-style body
        return error_from_server(error, str(body.get("message") or "") or None, status=status)
    return error_from_server("", None, status=status)


def _seg(value: str) -> str:
    return quote(str(value), safe="")


def _log_path(path: str) -> str:
    """A path fit for the log: no query string (a token may be in one)."""
    return path.split("?", 1)[0] if not path.startswith("http") else urlsplit(path).path


__all__ = [
    "USER_AGENT",
    "Response",
    "ScribeClient",
    "TokenSource",
    "Transport",
    "content_disposition_file_name",
    "require_secure",
]
