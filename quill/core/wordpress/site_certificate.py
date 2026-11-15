"""When a site's own security certificate runs out (the certificate Watch, PRD 15.7).

The one thing here that touches the network is :func:`certificate_expiry`: a
TLS handshake with the site's own host, on the port its address names (443
by default), to read the date the certificate it presents runs out. Nothing
is sent but the handshake itself -- no request, no path, no credential -- and
it runs only for the "Security certificate running out" Watch, which is off
until the person checks it in Workbench Options (the consent). A WordPress.com
site is skipped: its certificate is WordPress.com's to renew, not the
person's. Wx-free.
"""

from __future__ import annotations

import socket
import ssl
from urllib.parse import urlparse

from quill.core.error_codes import CodedError

__all__ = ["CertificateError", "certificate_expiry", "certificate_host"]

_TIMEOUT = 10.0


class CertificateError(CodedError):
    """The site's certificate could not be read, or is not trusted now."""

    code = "QUILL-WORDPRESS-CERTIFICATE-READ"

    def __init__(self, message: str, *, untrusted: bool = False) -> None:
        super().__init__(message)
        self.untrusted = untrusted

    @property
    def plain(self) -> str:
        """The message without its support code, for speech."""
        return str(self.args[0]) if self.args else ""


def certificate_host(site_url: str) -> tuple[str, int] | None:
    """The host and port to ask for *site_url*, or None when it has no certificate to read."""
    parsed = urlparse((site_url or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    return parsed.hostname, parsed.port or 443


def certificate_expiry(host: str, port: int = 443, *, timeout: float = _TIMEOUT) -> float:
    """When the certificate *host* presents runs out, as a POSIX time.

    The certificate is verified as every other QUILL connection verifies one,
    so one that has already run out, or is for another name, raises
    :class:`CertificateError` with ``untrusted`` set.
    """
    from quill.core.net import verified_ssl_context

    context = verified_ssl_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls:
                cert = tls.getpeercert()
    except ssl.SSLCertVerificationError as exc:
        reason = getattr(exc, "verify_message", "") or "it is not trusted"
        raise CertificateError(
            f"The certificate is not trusted: {reason}.", untrusted=True
        ) from None
    except (OSError, ssl.SSLError) as exc:
        raise CertificateError(f"Could not read the certificate ({exc}).") from None
    not_after = cert.get("notAfter") if isinstance(cert, dict) else None
    if not isinstance(not_after, str) or not not_after:
        raise CertificateError("The site sent a certificate with no end date.")
    return float(ssl.cert_time_to_seconds(not_after))
