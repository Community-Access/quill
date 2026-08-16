"""The single network egress site for the library layer (GATE-9).

HTTPS-only over a verified TLS context, with a bounded timeout, a size cap, and an
identifying User-Agent. Reached only by an explicit user action (searching a
catalogue or downloading a book) and disabled in Safe Mode. Every catalogue and
download call funnels through :func:`fetch_bytes` so there is exactly one
reviewable outbound site; it is registered in
``quill.tools.network_egress_audit._REVIEWED_EGRESS``.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request

from quill.core.library.model import LibraryHTTPError

_USER_AGENT = "QUILL-Library/0.1 (+https://github.com/Community-Access/quill)"
_TIMEOUT_S = 20.0
# Books (EPUB/PDF) are larger than feeds; cap generously but bounded.
_MAX_BYTES = 80_000_000


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Block all library egress in Safe Mode (parity with feed_reader/nws)."""
    if safe_mode:
        raise LibraryHTTPError("Book libraries are disabled in Safe Mode.")


def fetch_bytes(
    url: str,
    *,
    safe_mode: bool = False,
    accept: str = "",
    body: bytes | None = None,
    content_type: str = "",
    timeout_s: float = _TIMEOUT_S,
) -> bytes:
    """Fetch ``url`` over verified HTTPS and return the (capped) response bytes.

    Pass ``body`` (with ``content_type``) to issue a POST instead of a GET — used
    by catalogue sources whose search endpoint takes a JSON request body (e.g. the
    NLS BARD public catalogue search). No key or credential is ever sent.
    """
    refuse_in_safe_mode(safe_mode)
    if not url.lower().startswith("https://"):
        raise LibraryHTTPError(f"Library URL must be https://: {url}")
    headers = {"User-Agent": _USER_AGENT}
    if accept:
        headers["Accept"] = accept
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=body, headers=headers)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s, context=context) as response:
            data = response.read(_MAX_BYTES + 1)
            return bytes(data[:_MAX_BYTES])
    except urllib.error.HTTPError as exc:
        raise LibraryHTTPError(f"{exc.code} fetching {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise LibraryHTTPError(f"could not fetch {url}: {exc}") from exc
