"""Build the station pack: facts from the approved sources, merged, signed.

The build side of the Radio station enrichment program (Jeff's todo P2 #33;
design record ``docs/design/2026-10-16-station-pack-format.md``). Run weekly by
``.github/workflows/station-pack.yml``; runnable by hand.

It reads **only the approved sources** in
``quill.core.radio.enrichment.sources`` -- today the Community Picks catalogue
and, when ``--catalog`` names one, a station catalog generation as Radio
already ships it. It fetches nothing: no stream is probed and no page is read.
Sources awaiting a decision on their data terms are listed in
``PENDING_SOURCES`` and never read.

**Signing.** ``STATION_PACK_SIGNING_KEY`` is the base64 Ed25519 seed of the
publisher key already committed as ``quill-pub.key`` -- the key every shipped
build verifies against. It comes from the environment only, never a file in
the repository. Without it the pack is written **unsigned**, and every build
of Quill Radio refuses an unsigned pack; that is the intended outcome of a dry
run or a fork's run, not an error. A key that is not the publisher's is
refused before anything is signed, because a pack signed with a stranger's key
would be refused by every listener's app just as surely, only silently.

Usage::

    python scripts/build_station_pack.py --out build/station-pack
    python scripts/build_station_pack.py --out build/station-pack --catalog catalog.db
    STATION_PACK_SIGNING_KEY=<base64 seed> python scripts/build_station_pack.py --out ...
    python scripts/build_station_pack.py --verify build/station-pack
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

ENV_KEY = "STATION_PACK_SIGNING_KEY"


def signing_key_from(seed_b64: str) -> Any:
    """The signing key from the secret, or exit saying exactly what is wrong."""
    from nacl import signing

    try:
        seed = base64.b64decode(seed_b64.strip(), validate=True)
    except Exception as error:  # noqa: BLE001 - any decode failure is one message
        raise SystemExit(f"{ENV_KEY} is not valid base64: {error}") from error
    if len(seed) == 64:
        seed = seed[:32]  # seed followed by public key, as some tools export it
    if len(seed) != 32:
        raise SystemExit(
            f"{ENV_KEY} decodes to {len(seed)} bytes; an Ed25519 seed is 32 "
            "(or 64 for seed followed by public key)."
        )
    return signing.SigningKey(seed)


def refuse_a_stranger(key: Any, expected: Any = None) -> None:
    """Stop before signing with a key no shipped build trusts."""
    from quill.tools.signing import load_publisher_public_key

    try:
        trusted = expected if expected is not None else load_publisher_public_key()
    except Exception as error:  # noqa: BLE001 - a missing key file is its own message
        raise SystemExit(f"cannot check the signing key: {error}") from error
    if key.verify_key.encode() != trusted.encode():
        raise SystemExit(
            f"{ENV_KEY} is not the seed for the publisher key in quill-pub.key. "
            "Every shipped build would refuse a pack signed with it."
        )


def build(
    out_dir: Path,
    *,
    picks: Path | None = None,
    catalog: Path | None = None,
    signing_key: Any = None,
    built_at: str | None = None,
) -> dict[str, Any]:
    """Build and write the pack. Returns a summary for the log."""
    from quill.core.radio.enrichment.facts import merge
    from quill.core.radio.enrichment.pack import SourceCredit, build_pack, write_pack
    from quill.core.radio.enrichment.sources import build_sources

    inputs: dict[str, Path] = {}
    if picks is not None:
        inputs["picks"] = picks
    if catalog is not None:
        inputs["catalog"] = catalog
    sources = build_sources(inputs)
    batches = [(source.id, list(source.records())) for source in sources]
    stations = merge(batches)
    stamp = built_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    credits = [
        SourceCredit(id=s.id, title=s.title, terms=s.terms, attribution=s.attribution)
        for s in sources
    ]
    pack = build_pack(stations, credits, built_at=stamp)
    pack_path, sidecar, manifest = write_pack(out_dir, pack, signing_key=signing_key)
    return {
        "pack": pack_path,
        "signature": sidecar,
        "manifest": manifest,
        "stations": len(pack.stations),
        "sources": {source_id: len(records) for source_id, records in batches},
        "bytes": pack_path.stat().st_size,
    }


def verify(directory: Path) -> int:
    """Check a built pack exactly as the app would. Exit 0 only when trusted."""
    from quill.core.radio.enrichment import PackRefusedError
    from quill.core.radio.enrichment.pack import PACK_NAME, open_verified

    try:
        pack = open_verified(directory / PACK_NAME)
    except PackRefusedError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    print(f"trusted: {len(pack.stations)} stations, built {pack.built_at}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, help="directory to write the pack into")
    parser.add_argument("--picks", type=Path, help="Community Picks file (default: bundled)")
    parser.add_argument("--catalog", type=Path, help="a station catalog generation (.db)")
    parser.add_argument("--built-at", help="override the build stamp (reproducible builds)")
    parser.add_argument(
        "--require-signature",
        action="store_true",
        help="fail instead of writing an unsigned pack when the key is absent",
    )
    parser.add_argument("--verify", type=Path, help="check a built pack as the app would")
    args = parser.parse_args(argv)

    if args.verify is not None:
        return verify(args.verify)
    if args.out is None:
        parser.error("--out is required unless --verify is given")

    seed = (os.environ.get(ENV_KEY) or "").strip()
    key = None
    if seed:
        key = signing_key_from(seed)
        refuse_a_stranger(key)
    elif args.require_signature:
        print(f"{ENV_KEY} is not set; refusing to write an unsigned pack.", file=sys.stderr)
        return 1

    summary = build(
        args.out, picks=args.picks, catalog=args.catalog, signing_key=key, built_at=args.built_at
    )
    for source_id, count in summary["sources"].items():
        print(f"  {source_id}: {count} record(s)")
    print(f"{summary['stations']} station(s), {summary['bytes']:,} bytes -> {summary['pack']}")
    if summary["signature"] is None:
        print(f"UNSIGNED: {ENV_KEY} is not set. Quill Radio refuses an unsigned pack.")
    else:
        print(f"signed -> {summary['signature'].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
