"""The local station catalog: the whole directory, on this computer.

Browsing used to ask the internet on every expansion. The catalog inverts
that default: **the local store is the source of truth for browsing; the
network is the source of truth for freshness.** The app answers from an
indexed SQLite store in under a millisecond and reconciles with live data in
the background - on startup, on a timer, on demand, each individually
switchable off.

The catalog is **derived data**. Favorites, custom stations, My Servers and
YouTube channels live in their own stores and are never written by anything
in this package; the catalog can be deleted, rebuilt from the shipped seed,
or discarded on schema change with zero loss. That single property is what
makes a database safe here.

Design decisions with measurements behind them (see the Station Catalog PRD):
SQLite over JSON (0.5 ms indexed reads versus a 9 s / 217 MB load), pointer-
based generation swap (``os.replace`` over an open database fails on
Windows), per-page refresh parsing (whole-dump loading measured 217 MB), and
a merge that refuses URL-only matching (7,135 stream URLs are shared by
distinct stations within Radio Browser alone).

Sources are classed, and the class decides everything:

- Class A (bundled + refreshed): Radio Browser, SomaFM, Xiph when its
  backend recovers, and the library seed (LibriVox, Gutenberg audio).
- Class B (live-drill, session cache only, **never** written into this
  store): TuneIn, iHeart and Apple (terms), the Internet Archive (scale),
  free music charts (stale by definition).
- Class C (user-owned, protected): not in this store at all.

wx-free, strict-typed throughout.
"""

from quill.core.error_codes import CodedError


class CatalogError(CodedError):
    """The catalog could not be opened, imported, or refreshed."""

    code = "QUILL-RADIO-CATALOG-FAILED"


class CatalogCorruptError(CatalogError):
    """The store failed integrity checks and must be rebuilt from the seed."""

    code = "QUILL-RADIO-CATALOG-CORRUPT"


class SeedMissingError(CatalogError):
    """No usable bundled seed was found (absent, truncated, or hash-mismatched)."""

    code = "QUILL-RADIO-CATALOG-SEED-MISSING"
