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
COMMENT = "untrusted comment: QuillVille Community Picks"
ENV_KEY = "PICKS_SIGNING_KEY"


def sign(seed_b64: str) -> Path:
    from nacl import signing

    key = signing.SigningKey(base64.b64decode(seed_b64))
    payload = TARGET.read_bytes()
    signature = key.sign(payload).signature
    SIDECAR.write_text(
        COMMENT + "\n" + base64.b64encode(signature).decode("ascii") + "\n",
        encoding="utf-8",
    )
    return SIDECAR


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
