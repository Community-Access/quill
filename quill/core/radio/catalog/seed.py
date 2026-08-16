"""The bundled seed: a complete catalog before the first network request.

The release build ships ``seed.db.xz`` plus a manifest inside the package
(both editions - installer and portable; Jeff, 2026-08-15). On first run, or
after an app update whose seed is newer than the profile catalog's lineage,
the seed is verified against its SHA-256 and imported as a fresh generation.
The next live refresh replays any newer deltas - correct precisely because
the catalog is derived data.

An absent or damaged seed is never fatal and never silent-fatal either: the
app raises :class:`SeedMissingError` to its caller, which degrades to live
browsing and lets the first refresh build the catalog from the network
instead. A dev checkout without a seed therefore behaves like 3.0.0 until
the first refresh completes - and then it has a catalog anyway.
"""

from __future__ import annotations

import hashlib
import json
import lzma
import time
from pathlib import Path

from quill.core.radio.catalog import SeedMissingError
from quill.core.radio.catalog.store import CatalogStore, current_generation

SEED_NAME = "seed.db.xz"
MANIFEST_NAME = "seed-manifest.json"


def seed_dir() -> Path:
    """Where the packaged seed lives: ``quill/data/radio-catalog``."""
    return Path(__file__).resolve().parents[3] / "data" / "radio-catalog"


def seed_version(directory: Path | None = None) -> str:
    """The shipped seed's build stamp, or "" when no seed is packaged."""
    root = directory if directory is not None else seed_dir()
    try:
        manifest = json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(manifest.get("built_at", ""))


def import_seed(store: CatalogStore, *, directory: Path | None = None) -> bool:
    """Install the packaged seed as a new generation, verifying its hash.

    Returns True when a generation was imported, False when the profile
    catalog is already at (or past) the shipped seed's lineage. Raises
    :class:`SeedMissingError` when no usable seed is packaged.
    """
    root = directory if directory is not None else seed_dir()
    packed = root / SEED_NAME
    manifest_path = root / MANIFEST_NAME
    if not packed.is_file() or not manifest_path.is_file():
        raise SeedMissingError("No station catalog seed is packaged with this build.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SeedMissingError(f"The seed manifest could not be read: {error}") from error
    expected = str(manifest.get("sha256", ""))
    built_at = str(manifest.get("built_at", ""))
    if not expected or not built_at:
        raise SeedMissingError("The seed manifest is incomplete.")

    if store.exists():
        try:
            have = store.meta("seed_version")
        except Exception:  # noqa: BLE001 - a corrupt store means import anyway
            have = ""
        if have >= built_at:
            return False
        store.close()

    data = packed.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected:
        # A mismatched seed is a truncated or tampered install; importing it
        # would put unverified data in front of the listener.
        raise SeedMissingError("The packaged seed failed its integrity check.")
    raw = lzma.decompress(data)

    store.root.mkdir(parents=True, exist_ok=True)
    next_gen = (current_generation(store.root) or 0) + 1
    target = store.root / f"catalog.{next_gen}.db"
    tmp = target.with_suffix(".db.importing")
    tmp.write_bytes(raw)
    tmp.replace(target)

    # Stamp lineage inside the new generation before publishing it.
    import sqlite3

    con = sqlite3.connect(target)
    try:
        con.execute(
            "INSERT OR REPLACE INTO catalog_meta(key, value) VALUES ('seed_version', ?)",
            (built_at,),
        )
        con.execute(
            "INSERT OR REPLACE INTO catalog_meta(key, value) VALUES ('imported_at', ?)",
            (f"{time.time():.0f}",),
        )
        con.commit()
    finally:
        con.close()

    pointer_tmp = store.root / "CURRENT.tmp"
    pointer_tmp.write_text(target.name, encoding="utf-8")
    pointer_tmp.replace(store.root / "CURRENT")
    store.reopen_if_stale()
    return True


def rebuild_from_seed(store: CatalogStore) -> None:
    """ "Rebuild From Shipped Snapshot": drop everything derived, reimport.

    Deletes only the catalog directory - a byte-identity test elsewhere
    asserts the user stores are untouched across this call.
    """
    store.destroy()
    import_seed(store)
