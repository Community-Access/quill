"""Build the Quill Radio station-catalog seed for a release.

Runs the same Class-A fetchers the app uses (they are wx-free precisely so
this is possible), normalizes and imports them into a fresh catalog database,
compresses it with lzma, and stages ``seed.db.xz`` plus a SHA-256 manifest
into ``quill/data/radio-catalog/`` for packaging. Both editions ship it.

**The size gate is a hard failure**: a seed over budget fails the build, so
the installers cannot balloon silently. Measured baseline 2026-08-15: the
full 62,377-station Radio Browser dump plus SomaFM compresses to 6.4 MB
against the 10 MB budget.

Also builds the library shelf (Project Gutenberg audio, ~1,100 records,
freely redistributable; LibriVox stays live in v1 - see the note in
``_build_libraries``) and, when Wikidata answers, the RadioDNS identity
enrichment - resolved here, once, on the build machine, so no listener's
computer ever issues those DNS queries.

Usage:
    python scripts/build_radio_catalog.py [--out DIR] [--skip-libraries]
                                          [--skip-identities] [--budget-mb 10]
                                          [--from-cache FILE]

``--from-cache`` builds the station table from a previously fetched
Radio Browser JSON dump (dev convenience; the release path always fetches
live so a release ships that day's directory).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DEFAULT_OUT = REPO / "quill" / "data" / "radio-catalog"
BUDGET_MB_DEFAULT = 10


def _stations_from_cache(path: Path):
    from quill.core.radio.catalog.sources import row_from_radio_browser

    raw = json.loads(path.read_text(encoding="utf-8"))
    page = [row for row in (row_from_radio_browser(e) for e in raw) if row is not None]
    yield page


def _build_stations(writer, *, from_cache: Path | None) -> dict[str, int]:
    from quill.core.radio.catalog.sources import station_specs

    counts: dict[str, int] = {}
    now = time.time()
    for spec in station_specs():
        pages = (
            _stations_from_cache(from_cache)
            if from_cache is not None and spec.id == "radio_browser"
            else spec.fetch_pages()
        )
        total = 0
        try:
            for page in pages:
                writer.upsert_stations(spec.id, page, now=now)
                total += len(page)
        except Exception as error:  # noqa: BLE001 - a down source ships absent, not broken
            print(f"  {spec.id}: FAILED ({error}); the seed ships without it")
            writer.record_source(spec.id, status="stale", error=str(error)[:200], now=now)
            continue
        status = "ok" if total else "stale"
        if not total:
            print(f"  {spec.id}: returned no stations; marked stale in the seed")
        writer.record_source(spec.id, status=status, now=now)
        counts[spec.id] = total
        print(f"  {spec.id}: {total:,} stations")
    return counts


def _build_libraries(writer) -> None:
    # LibriVox is deliberately NOT seeded in v1. Measured 2026-08-15: the full
    # shelf is 8,978+ books with 194,501 section rows -- 60 MB of chapter
    # listings that alone blow the 10 MB seed budget. Its shelf stays live
    # (exactly as 3.0 served it) until sections get a compact format of their
    # own; ``librivox.fetch_book_page`` is already in place for that follow-up.
    from quill.core.radio import gutendex

    print("  gutenberg: fetching the audio shelf...")
    g_books: list[tuple[str, str, str, str, str]] = []
    g_sections: list[tuple[str, int, str, str]] = []
    page = 1
    while True:
        rows = gutendex.audiobooks(limit=100, page=page)
        for station in rows:
            g_books.append((station.stream_url, station.name, "", "", ""))
            g_sections.append((station.stream_url, 0, station.name, station.stream_url))
        if len(rows) < 32:  # gutendex pages are 32; a short page is the end
            break
        page += 1
        time.sleep(0.4)
    writer.replace_audiobooks("gutenberg", g_books, g_sections)
    writer.record_source("gutenberg", status="ok" if g_books else "stale", now=time.time())
    print(f"  gutenberg: {len(g_books):,} records")


def _build_identities(writer) -> None:
    """RadioDNS resolution at build time: Wikidata supplies frequency+country,
    the resolver runs here, and listeners get a local join instead of DNS."""
    try:
        from quill.core.radio import radiodns, wikidata
    except ImportError:
        print("  identities: radiodns/wikidata unavailable; skipped")
        return
    links: list[tuple[str, str]] = []
    try:
        stations = wikidata.stations_for_axis("city")
        for entry in stations:
            freq = getattr(entry, "frequency_mhz", 0.0) or 0.0
            country = (getattr(entry, "country", "") or "").strip()
            name = getattr(entry, "name", "")
            if not freq or not country:
                continue
            try:
                identity = radiodns.resolve_fm_identity(freq, country)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                continue
            if identity:
                links.append((name, str(identity)))
    except Exception as error:  # noqa: BLE001
        print(f"  identities: skipped ({error})")
        return
    writer.replace_identities("radiodns", links)
    print(f"  identities: {len(links)} RadioDNS links resolved at build time")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--budget-mb", type=float, default=BUDGET_MB_DEFAULT)
    parser.add_argument("--skip-libraries", action="store_true")
    parser.add_argument("--skip-identities", action="store_true")
    parser.add_argument("--from-cache", type=Path, default=None)
    args = parser.parse_args()

    import tempfile

    from quill.core.radio.catalog.store import CatalogStore

    print("Building the station catalog seed...")
    with tempfile.TemporaryDirectory(prefix="quill-seed-") as tmp:
        store = CatalogStore(tmp)
        writer = store.begin_generation()
        _build_stations(writer, from_cache=args.from_cache)
        if not args.skip_libraries:
            _build_libraries(writer)
        if not args.skip_identities:
            _build_identities(writer)
        built_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        writer.set_meta("seed_built_at", built_at)
        writer.connection.commit()
        writer.connection.execute("VACUUM")
        writer.commit()

        from quill.core.radio.catalog.store import current_generation

        generation = current_generation(store.root)
        db_path = store.root / f"catalog.{generation}.db"
        store.close()
        raw = db_path.read_bytes()

    print(f"  database: {len(raw) / 1e6:.1f} MB; compressing...")
    packed = lzma.compress(raw, preset=6)
    size_mb = len(packed) / 1e6
    print(f"  seed: {size_mb:.1f} MB compressed (budget {args.budget_mb} MB)")
    if size_mb > args.budget_mb:
        print("SEED OVER BUDGET - failing the build rather than shipping bloat.")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "seed.db.xz").write_bytes(packed)
    manifest = {
        "built_at": built_at,
        "sha256": hashlib.sha256(packed).hexdigest(),
        "raw_bytes": len(raw),
        "packed_bytes": len(packed),
    }
    (args.out / "seed-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"Seed staged at {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
