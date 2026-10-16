"""The station pack: one signed file of station facts, and how it is trusted.

Three files travel together (design record:
``docs/design/2026-10-16-station-pack-format.md``):

- ``station-pack.json.xz`` -- the pack itself: canonical JSON, xz-compressed.
- ``station-pack.json.xz.minisig`` -- its detached Ed25519 signature, written
  by :func:`quill.tools.signing.sign_artifact`, the one writer every signed
  artifact in this project uses, and read by its counterpart.
- ``station-pack-manifest.json`` -- a small summary (build time, SHA-256,
  size, station count) so a client can tell whether a pack is newer without
  opening it. The manifest is a convenience, never the trust: the signature
  covers the pack's own bytes.

**Fail closed, always.** :func:`open_verified` refuses a pack with no
signature, a signature that does not verify against the bundled publisher
key, a hash that disagrees with its manifest, an over-large body, or a format
it does not know -- by raising :class:`PackRefusedError` with one plain
sentence. A pack built without the signing key is written unsigned on
purpose, so this refusal is the only thing that happens to it.
"""

from __future__ import annotations

import hashlib
import json
import lzma
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.radio.enrichment import PackRefusedError
from quill.core.radio.enrichment.facts import StationFacts

if TYPE_CHECKING:
    from nacl import signing as nacl_signing

FORMAT = "quill-station-pack"
#: The major version this build reads. A higher one is refused, not guessed at.
VERSION = 1
PACK_NAME = "station-pack.json.xz"
MANIFEST_NAME = "station-pack-manifest.json"
SIGNATURE_SUFFIX = ".minisig"
#: No genuine pack comes near this (60,000 stations measured at well under
#: 60 MB raw in the plan); a bigger one is damage or abuse, not data.
MAX_UNPACKED_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class SourceCredit:
    """One source a pack was built from, with its terms and credit line."""

    id: str
    title: str
    terms: str = ""
    attribution: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "terms": self.terms,
            "attribution": self.attribution,
        }


@dataclass(frozen=True, slots=True)
class StationPack:
    """A pack's contents, read and checked."""

    built_at: str
    kind: str = "full"
    sources: tuple[SourceCredit, ...] = ()
    stations: tuple[StationFacts, ...] = field(default_factory=tuple)


def encode(pack: StationPack) -> bytes:
    """The pack's bytes: canonical JSON, xz-compressed. Deterministic."""
    document = {
        "format": FORMAT,
        "version": VERSION,
        "kind": pack.kind,
        "built_at": pack.built_at,
        "sources": [credit.to_dict() for credit in pack.sources],
        "stations": [facts.to_dict() for facts in pack.stations],
    }
    text = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return lzma.compress(text.encode("utf-8"), preset=6)


def decode(data: bytes) -> StationPack:
    """Read a pack's bytes. Raises :class:`PackRefusedError` on anything odd."""
    try:
        decompressor = lzma.LZMADecompressor()
        raw = decompressor.decompress(data, max_length=MAX_UNPACKED_BYTES + 1)
    except lzma.LZMAError as error:
        raise PackRefusedError("The station pack is damaged and could not be opened.") from error
    if len(raw) > MAX_UNPACKED_BYTES or not decompressor.eof:
        raise PackRefusedError("The station pack is larger than any genuine pack.")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise PackRefusedError("The station pack is not readable.") from error
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise PackRefusedError("This file is not a station pack.")
    version = document.get("version")
    if not isinstance(version, int) or version < 1:
        raise PackRefusedError("The station pack has no version.")
    if version > VERSION:
        raise PackRefusedError(
            "The station pack is from a newer version of Quill Radio; update to use it."
        )
    built_at = str(document.get("built_at") or "")
    if not built_at:
        raise PackRefusedError("The station pack does not say when it was built.")
    stations = document.get("stations")
    if not isinstance(stations, list):
        raise PackRefusedError("The station pack has no station list.")
    sources_raw = document.get("sources") if isinstance(document.get("sources"), list) else []
    credits = tuple(
        SourceCredit(
            id=str(item.get("id", "")),
            title=str(item.get("title", "")),
            terms=str(item.get("terms", "")),
            attribution=str(item.get("attribution", "")),
        )
        for item in sources_raw or []
        if isinstance(item, dict) and item.get("id")
    )
    facts = tuple(
        StationFacts.from_dict(item)
        for item in stations
        if isinstance(item, dict) and str(item.get("key") or "").strip()
    )
    return StationPack(
        built_at=built_at,
        kind=str(document.get("kind") or "full"),
        sources=credits,
        stations=facts,
    )


def manifest_for(data: bytes, pack: StationPack, *, signed: bool) -> dict[str, Any]:
    """The manifest that travels beside a pack's bytes."""
    return {
        "format": FORMAT,
        "version": VERSION,
        "kind": pack.kind,
        "built_at": pack.built_at,
        "file": PACK_NAME,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "stations": len(pack.stations),
        "sources": [credit.id for credit in pack.sources],
        "signed": signed,
    }


def write_pack(
    out_dir: Path,
    pack: StationPack,
    *,
    signing_key: nacl_signing.SigningKey | None = None,
) -> tuple[Path, Path | None, Path]:
    """Write the pack, its signature when a key is given, and its manifest.

    Without a key the pack is written **unsigned** and any old signature
    beside it is removed, so a stale sidecar can never vouch for new bytes.
    Returns ``(pack path, signature path or None, manifest path)``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    data = encode(pack)
    target = out_dir / PACK_NAME
    target.write_bytes(data)
    sidecar_path = target.with_name(target.name + SIGNATURE_SUFFIX)
    sidecar: Path | None = None
    if signing_key is not None:
        from quill.tools.signing import sign_artifact

        sidecar = sign_artifact(target, signing_key)
    else:
        sidecar_path.unlink(missing_ok=True)
    manifest = out_dir / MANIFEST_NAME
    manifest.write_text(
        json.dumps(manifest_for(data, pack, signed=sidecar is not None), indent=2) + "\n",
        encoding="utf-8",
    )
    return target, sidecar, manifest


def verify_signature(
    pack_path: Path,
    *,
    public_key: nacl_signing.VerifyKey | None = None,
) -> tuple[bool, str]:
    """``(trusted, why not)`` for a pack file and its sidecar. Never raises.

    ``public_key`` is for tests; the app always passes None, which means the
    publisher key bundled with this build (``quill-pub.key``).
    """
    try:
        from quill.tools.signing import load_publisher_public_key, verify_artifact
    except Exception as error:  # noqa: BLE001 - no verifier means no trust
        return False, f"the signature could not be checked ({error})"
    sidecar = pack_path.with_name(pack_path.name + SIGNATURE_SUFFIX)
    if not sidecar.is_file():
        return False, "it is not signed"
    try:
        key = public_key if public_key is not None else load_publisher_public_key()
        status = verify_artifact(pack_path, key, sidecar)
    except Exception as error:  # noqa: BLE001 - verification must never crash
        return False, f"the signature could not be checked ({error})"
    if status.verified:
        return True, ""
    return False, status.error or "the signature did not match"


def read_manifest(directory: Path) -> dict[str, Any]:
    """The manifest beside a pack, or {} when there is none or it is unreadable."""
    try:
        document = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return document if isinstance(document, dict) else {}


def open_verified(
    pack_path: Path,
    *,
    public_key: nacl_signing.VerifyKey | None = None,
) -> StationPack:
    """Verify, then read, a pack. The only way the app reads one.

    Order matters: the signature is checked over the file's bytes **before**
    anything is decompressed or parsed, so an untrusted file never reaches the
    parser at all.
    """
    if not pack_path.is_file():
        raise PackRefusedError("There is no station pack here.")
    trusted, why = verify_signature(pack_path, public_key=public_key)
    if not trusted:
        raise PackRefusedError(f"The station pack was refused: {why}.")
    data = pack_path.read_bytes()
    manifest = read_manifest(pack_path.parent)
    expected = str(manifest.get("sha256") or "")
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise PackRefusedError("The station pack does not match its manifest.")
    return decode(data)


def build_pack(
    stations: Iterable[StationFacts],
    credits: Iterable[SourceCredit],
    *,
    built_at: str,
    kind: str = "full",
) -> StationPack:
    """Assemble a pack value (sorted by key, so two builds of the same data match)."""
    return StationPack(
        built_at=built_at,
        kind=kind,
        sources=tuple(credits),
        stations=tuple(sorted(stations, key=lambda facts: facts.key)),
    )


__all__ = [
    "FORMAT",
    "MANIFEST_NAME",
    "MAX_UNPACKED_BYTES",
    "PACK_NAME",
    "SIGNATURE_SUFFIX",
    "VERSION",
    "SourceCredit",
    "StationPack",
    "build_pack",
    "decode",
    "encode",
    "manifest_for",
    "open_verified",
    "read_manifest",
    "verify_signature",
    "write_pack",
]
