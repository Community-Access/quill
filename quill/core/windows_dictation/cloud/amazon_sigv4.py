"""AWS Signature Version 4, with the standard library only (D-34).

Two uses, both for Amazon Transcribe:

* :func:`presign_url` -- a WebSocket address signed in its query string
  (``X-Amz-Algorithm``, ``X-Amz-Credential``, ``X-Amz-Date``,
  ``X-Amz-Expires``, ``X-Amz-Security-Token`` when there is a session token,
  ``X-Amz-SignedHeaders=host`` and ``X-Amz-Signature``). The secret access key
  is never in the address: only the access key ID and the signature are.
* :func:`sign_headers` -- the ``Authorization`` header (and ``X-Amz-Date``,
  ``X-Amz-Security-Token``) for an ordinary HTTPS request, such as the JSON
  ``ListVocabularies`` call Test Connection makes.

The algorithm, as AWS documents it: a canonical request (method, URI,
sorted query, sorted lower-case headers, the signed header names, the payload's
SHA-256), a string to sign (``AWS4-HMAC-SHA256``, the time, the credential
scope, the canonical request's SHA-256), and an HMAC-SHA256 chain
(``AWS4`` + secret, date, region, service, ``aws4_request``) for the key.

wx-free.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from urllib.parse import quote

__all__ = [
    "ALGORITHM",
    "EMPTY_SHA256",
    "Signed",
    "amz_date",
    "canonical_query",
    "canonical_request",
    "presign_url",
    "sign_headers",
    "signature",
    "signing_key",
    "string_to_sign",
]

ALGORITHM = "AWS4-HMAC-SHA256"
#: The SHA-256 of an empty payload.
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def _encode(text: str) -> str:
    """URI-encode as SigV4 wants: everything but ``A-Z a-z 0-9 - _ . ~``."""
    return quote(text, safe="-_.~")


def amz_date(when: datetime | None = None) -> str:
    """``20150830T123600Z`` for *when* (now, in UTC, by default)."""
    moment = (when or datetime.now(UTC)).astimezone(UTC)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def canonical_query(params: Sequence[tuple[str, str]]) -> str:
    """The query, each name and value encoded, sorted by name then value."""
    encoded = sorted((_encode(str(name)), _encode(str(value))) for name, value in params)
    return "&".join(f"{name}={value}" for name, value in encoded)


def _canonical_headers(headers: Mapping[str, str]) -> tuple[str, str]:
    """``(canonical headers, signed header names)``."""
    cleaned = sorted(
        (str(name).strip().lower(), " ".join(str(value).split())) for name, value in headers.items()
    )
    block = "".join(f"{name}:{value}\n" for name, value in cleaned)
    return block, ";".join(name for name, _value in cleaned)


def canonical_request(
    method: str,
    path: str,
    params: Sequence[tuple[str, str]],
    headers: Mapping[str, str],
    payload_hash: str,
) -> str:
    """The canonical request AWS hashes, with *headers* all signed."""
    block, names = _canonical_headers(headers)
    uri = quote(path or "/", safe="/-_.~")
    return "\n".join([method.upper(), uri, canonical_query(params), block, names, payload_hash])


def _scope(date: str, region: str, service: str) -> str:
    return f"{date}/{region}/{service}/aws4_request"


def string_to_sign(stamp: str, region: str, service: str, request: str) -> str:
    """What is signed: the algorithm, the time, the scope and the request's hash."""
    digest = hashlib.sha256(request.encode("utf-8")).hexdigest()
    return "\n".join([ALGORITHM, stamp, _scope(stamp[:8], region, service), digest])


def _hmac(key: bytes, text: str) -> bytes:
    return hmac.new(key, text.encode("utf-8"), hashlib.sha256).digest()


def signing_key(secret_key: str, date: str, region: str, service: str) -> bytes:
    """The derived key for one day, region and service."""
    key = _hmac(("AWS4" + secret_key).encode("utf-8"), date)
    key = _hmac(key, region)
    key = _hmac(key, service)
    return _hmac(key, "aws4_request")


def signature(secret_key: str, stamp: str, region: str, service: str, request: str) -> str:
    """The hex signature of canonical *request* at *stamp*."""
    key = signing_key(secret_key, stamp[:8], region, service)
    text = string_to_sign(stamp, region, service, request)
    return hmac.new(key, text.encode("utf-8"), hashlib.sha256).hexdigest()


def presign_url(
    *,
    scheme: str,
    host: str,
    path: str,
    params: Sequence[tuple[str, str]],
    access_key: str,
    secret_key: str,
    region: str,
    service: str,
    session_token: str = "",
    expires: int = 300,
    when: datetime | None = None,
) -> str:
    """A ``scheme://host/path?query`` address signed in its query string.

    *host* is exactly what the client sends as ``Host`` (with ``:8443`` when
    the port is not the scheme's usual one), because it is signed.
    """
    stamp = amz_date(when)
    query = list(params) + [
        ("X-Amz-Algorithm", ALGORITHM),
        ("X-Amz-Credential", f"{access_key}/{_scope(stamp[:8], region, service)}"),
        ("X-Amz-Date", stamp),
        ("X-Amz-Expires", str(int(expires))),
        ("X-Amz-SignedHeaders", "host"),
    ]
    if session_token:
        query.append(("X-Amz-Security-Token", session_token))
    request = canonical_request("GET", path, query, {"host": host}, EMPTY_SHA256)
    query.append(("X-Amz-Signature", signature(secret_key, stamp, region, service, request)))
    return f"{scheme}://{host}{path}?{canonical_query(query)}"


class Signed(dict[str, str]):
    """The headers to send with a signed request (a plain dict of them)."""


def sign_headers(
    *,
    method: str,
    host: str,
    path: str,
    headers: Mapping[str, str],
    body: bytes,
    access_key: str,
    secret_key: str,
    region: str,
    service: str,
    session_token: str = "",
    params: Sequence[tuple[str, str]] = (),
    when: datetime | None = None,
) -> Signed:
    """*headers* plus ``Host``, ``X-Amz-Date``, ``X-Amz-Security-Token`` (when
    given) and ``Authorization``, every header signed."""
    stamp = amz_date(when)
    signed: dict[str, str] = {**headers, "Host": host, "X-Amz-Date": stamp}
    if session_token:
        signed["X-Amz-Security-Token"] = session_token
    request = canonical_request(method, path, params, signed, hashlib.sha256(body).hexdigest())
    _block, names = _canonical_headers(signed)
    credential = f"{access_key}/{_scope(stamp[:8], region, service)}"
    value = signature(secret_key, stamp, region, service, request)
    signed["Authorization"] = (
        f"{ALGORITHM} Credential={credential}, SignedHeaders={names}, Signature={value}"
    )
    return Signed(signed)
