from __future__ import annotations

import ssl

import truststore

__all__ = ["configure_ssl_trust", "ssl_trust_configured", "verified_ssl_context"]

_SSL_TRUST_CONFIGURED = False


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
