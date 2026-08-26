"""Sign the published Community Picks catalogue with the publisher key.

Writes a detached Ed25519 sidecar (``picks.json.minisig``) beside the served
file, in the same shape :mod:`quill.tools.signing` already reads for Quillins
and release artifacts -- so the app verifies picks with the key and the code it
already ships.

Why sign a public file at all: this catalogue causes the app to subscribe to
feeds and add stations, so whoever could replace it could point listeners at
content they never chose. HTTPS from our own domain is decent, and a signature
makes the question moot for one CI step.

The key never leaves CI. ``PICKS_SIGNING_KEY`` is the base64 Ed25519 seed, held
as a repository secret; without it this script exits 0 and signs nothing, so a
fork's workflow run cannot publish an unsigned catalogue.

**It has to be the seed for the publisher key already committed as
``quill-pub.key``**, not a freshly generated pair. That file is what every
shipped build verifies against, and it verifies Quillins and release artifacts
too -- so a new keypair would not merely fail to help here, it would have to
replace a key other signatures already depend on. Generating one is the wrong
instinct and this paragraph exists to interrupt it; :func:`sign` refuses a
stranger rather than trusting the reader to have got here.

The sidecar is written by :func:`quill.tools.signing.sign_artifact` -- the same
function that writes every other signature in this project, and the counterpart
of the one that reads them. That matters more than it looks. This script used
to hand-roll a two-line file (comment, then base64), while ``read_minisig``
requires three lines with a ``key id:`` between them. The signature itself was
perfectly good and the app rejected the file as an unreadable sidecar, which
fails closed -- so with the secret set and everything apparently done, the
catalogue would have been published *signed* and still never used. One writer,
one reader, one shape.

Usage::

    PICKS_SIGNING_KEY=<base64 seed> python scripts/sign_community_picks.py
    python scripts/sign_community_picks.py --verify   # check, sign nothing
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
TARGET = _ROOT / "docs" / "site" / "picks" / "v1" / "picks.json"
SIDECAR = TARGET.with_suffix(".json.minisig")
ENV_KEY = "PICKS_SIGNING_KEY"


def _signing_key(seed_b64: str):  # noqa: ANN202 - nacl is imported lazily
    """The signing key from the secret, or exit saying exactly what is wrong."""
    from nacl import signing

    try:
        seed = base64.b64decode(seed_b64, validate=True)
    except Exception as error:  # noqa: BLE001 - any decode failure is one message
        raise SystemExit(f"{ENV_KEY} is not valid base64: {error}") from error
    if len(seed) == 64:
        # Some tools export the seed and the public key concatenated. Take the
        # seed rather than signing with the wrong 32 bytes and producing a
        # signature that verifies against nothing.
        seed = seed[:32]
    if len(seed) != 32:
        raise SystemExit(
            f"{ENV_KEY} decodes to {len(seed)} bytes; an Ed25519 seed is 32 "
            "(or 64 for seed followed by public key)."
        )
    return signing.SigningKey(seed)


def _refuse_a_stranger(key) -> None:  # noqa: ANN001 - nacl is imported lazily
    """Stop before signing with a key no shipped build trusts.

    Without this the failure is silent and slow: CI signs, publishes, and every
    listener's app refuses the catalogue and quietly falls back to the bundled
    copy -- which looks exactly like working software, because falling back is
    what it is supposed to do. The mismatch would surface days later as "why
    are the new picks not appearing?". Far better to fail the workflow run.
    """
    sys.path.insert(0, str(_ROOT))
    from quill.tools.signing import load_publisher_public_key

    try:
        expected = load_publisher_public_key()
    except Exception as error:  # noqa: BLE001 - a missing key file is its own message
        raise SystemExit(f"cannot check the signing key: {error}") from error
    if key.verify_key.encode() != expected.encode():
        raise SystemExit(
            f"{ENV_KEY} is not the seed for the publisher key in quill-pub.key. "
            "Signing with it would publish a catalogue every shipped build "
            "refuses. Use the existing publisher seed, not a new keypair."
        )


def sign(seed_b64: str) -> Path:
    """Write the detached signature, in the shape the app's verifier reads."""
    sys.path.insert(0, str(_ROOT))
    from quill.tools.signing import sign_artifact

    key = _signing_key(seed_b64)
    _refuse_a_stranger(key)
    return sign_artifact(TARGET, key)


def verify() -> bool:
    """True when the sidecar matches the file, using the app's own verifier."""
    sys.path.insert(0, str(_ROOT))
    from quill.tools.signing import load_publisher_public_key, verify_artifact

    status = verify_artifact(TARGET, load_publisher_public_key(), SIDECAR)
    print(f"verified={status.verified} error={status.error}")
    return bool(status.verified)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="check the sidecar, sign nothing")
    args = parser.parse_args()

    if not TARGET.is_file():
        print(f"nothing to sign: {TARGET} does not exist", file=sys.stderr)
        return 1
    if args.verify:
        return 0 if verify() else 1

    seed = (os.environ.get(ENV_KEY) or "").strip()
    if not seed:
        # Not an error. A fork, or a local dry run, simply does not sign -- and
        # leaving the previous sidecar untouched is what stops an unsigned
        # rebuild from replacing a good signature with nothing.
        print(f"{ENV_KEY} is not set; leaving the existing signature alone")
        return 0
    written = sign(seed)
    print(f"signed {TARGET.relative_to(_ROOT)} -> {written.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
