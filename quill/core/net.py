"""One certificate check for every secure connection QUILL and its apps make.

Every outbound HTTPS request verifies the server's certificate the way Windows
does: against the operating-system certificate store, through ``truststore``.
That store includes the roots an organization or an antivirus product has
installed, and Windows fetches missing intermediates, so a site that opens in
Edge opens here and a site Edge refuses is refused here too.

The rule, per library
---------------------

``urllib`` (``urlopen``, ``build_opener``, ``HTTPSHandler``)
    Pass ``context=verified_ssl_context()``, or ``context=context_for(url)``
    when the same code also talks plain HTTP to a loopback or LAN service
    (Ollama, a local engine). Never build a context of your own.

``requests``, ``urllib3``, ``httpx``, ``websocket-client``
    Rely on :func:`configure_ssl_trust`. ``truststore.inject_into_ssl()``
    replaces ``ssl.SSLContext`` process-wide, so the default context those
    libraries build is already the system-store one. Never switch their
    verification off (``verify`` or ``cert_reqs``); the gate rejects both.

Media engines (mpv, ffmpeg, VLC) and yt-dlp's own downloader
    Out of Python's TLS: they do their own certificate checks and are not
    routed through here.

Every app entry point calls :func:`configure_ssl_trust` before it can touch
the network (``quill/__main__.py`` for QUILL, ``quill/apps/__init__.py`` for
every family app, which runs before any app module loads).
``tests/unit/core/test_tls_one_check.py`` fails the build on a context built
anywhere else, on any switch that turns verification off, and on a urllib
call in a module that never reaches this one.

When a certificate genuinely does not verify, :func:`certificate_problem`
turns the error into the one sentence every app says about it.
"""

from __future__ import annotations

import ssl
import urllib.error

import truststore

__all__ = [
    "CERTIFICATE_SENTENCE",
    "certificate_problem",
    "configure_ssl_trust",
    "context_for",
    "is_certificate_failure",
    "ssl_trust_configured",
    "verified_ssl_context",
]

_SSL_TRUST_CONFIGURED = False

#: The one sentence for a certificate that does not verify, in every app.
CERTIFICATE_SENTENCE = (
    "The site's security certificate could not be verified. Check this device's date and time, "
    "install system updates, or ask your network administrator whether security software "
    "inspects secure connections."
)

_CERTIFICATE_MARKERS = ("certificate verify failed", "certificate_verify_failed")


def configure_ssl_trust() -> None:
    """Use the operating system certificate store for app-wide HTTPS."""
    global _SSL_TRUST_CONFIGURED
    if _SSL_TRUST_CONFIGURED:
        return
    truststore.inject_into_ssl()
    _SSL_TRUST_CONFIGURED = True


def ssl_trust_configured() -> bool:
    """Whether the application installed truststore's SSL integration."""
    return _SSL_TRUST_CONFIGURED


def verified_ssl_context() -> ssl.SSLContext:
    """Return a native-store SSL context that always verifies certificates.

    The operating-system store can include organization-managed roots and
    retrieve missing intermediates. Certificate and hostname verification
    remain enabled.
    """
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def context_for(url: str) -> ssl.SSLContext | None:
    """The verified context for an ``https`` URL, ``None`` for anything else.

    For code that reaches both cloud services and a plain-HTTP local one; an
    HTTPS address always gets the verifying context, never none.
    """
    return verified_ssl_context() if url.strip().lower().startswith("https:") else None


def _links(error: BaseException) -> list[BaseException]:
    """*error* and every error inside it, without loops.

    Follows ``__cause__``/``__context__``, ``URLError.reason``, a ``reason``
    attribute (urllib3's ``MaxRetryError``) and exception ``args`` (how
    ``requests.exceptions.SSLError`` carries what urllib3 raised).
    """
    seen: list[BaseException] = []
    pending: list[BaseException] = [error]
    while pending:
        current = pending.pop(0)
        if any(current is known for known in seen):
            continue
        seen.append(current)
        inner: list[object] = [current.__cause__, current.__context__]
        inner.append(getattr(current, "reason", None))
        inner.extend(current.args)
        pending.extend(item for item in inner if isinstance(item, BaseException))
    return seen


def is_certificate_failure(error: BaseException) -> bool:
    """Whether *error* is, or wraps, a certificate that did not verify."""
    for link in _links(error):
        if isinstance(link, ssl.SSLCertVerificationError):
            return True
        if isinstance(link, (ssl.SSLError, urllib.error.URLError, OSError)) or (
            type(link).__name__ in {"SSLError", "MaxRetryError", "ConnectError"}
        ):
            text = str(link).lower()
            if any(marker in text for marker in _CERTIFICATE_MARKERS):
                return True
    return False


def certificate_problem(error: BaseException) -> str | None:
    """The one plain sentence for a bad certificate, or ``None`` if it is not one."""
    return CERTIFICATE_SENTENCE if is_certificate_failure(error) else None
