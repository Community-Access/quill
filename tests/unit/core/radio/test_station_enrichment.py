"""Station enrichment: facts, the signed pack, the store, search. No network.

The program's trust rule is the thing most worth pinning: a pack that is not
signed by the publisher key is refused before it is parsed, and a refused or
failed import leaves the facts already installed exactly as they were.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from nacl import signing

from quill.core.radio.enrichment import EnrichmentError, PackRefusedError, client, pack, sources
from quill.core.radio.enrichment.facts import (
    StationFacts,
    call_sign_in,
    frequency_in,
    merge,
    query_terms,
)
from quill.core.radio.enrichment.store import SCHEMA_VERSION, EnrichmentStore, migrate

KUOW = StationFacts(
    key="uuid-kuow",
    name="KUOW 94.9",
    stream_url="https://streams.example.org/kuow",
    slogan="Seattle's NPR station",
    genre="public radio",
    city="Seattle",
    state="Washington",
    country="United States",
    description="News and talk for the Puget Sound.",
)
KIRO = StationFacts(
    key="uuid-kiro",
    name="KIRO-FM",
    stream_url="https://streams.example.org/kiro",
    frequency="97.3 FM",
    slogan="Official home of the Seattle Seahawks",
    genre="news talk",
    city="Seattle",
    state="Washington",
)
JAZZ = StationFacts(
    key="uuid-jazz",
    name="Jazz24",
    stream_url="https://streams.example.org/jazz24",
    genre="jazz",
    city="Tacoma",
    state="Washington",
)


@pytest.fixture
def key() -> signing.SigningKey:
    return signing.SigningKey.generate()


def _signed_pack(tmp: Path, key: signing.SigningKey, *stations: StationFacts, built: str) -> Path:
    built_pack = pack.build_pack(
        stations, [pack.SourceCredit("test", "Test source")], built_at=built
    )
    path, sidecar, _manifest = pack.write_pack(tmp, built_pack, signing_key=key)
    assert sidecar is not None
    return path


# -- facts ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "call", "freq"),
    [
        ("KUOW 94.9", "KUOW", "94.9 FM"),
        ("WNYC-FM", "WNYC-FM", ""),
        ("KCBS 740 AM", "KCBS", "740 AM"),
        ("KISS FM 98.5", "", "98.5 FM"),  # a name, not a call sign
        ("Jazz24", "", ""),
        ("KEXP", "", ""),  # no suffix and no frequency: not certain enough
    ],
)
def test_call_signs_and_frequencies_are_read_conservatively(
    name: str, call: str, freq: str
) -> None:
    assert call_sign_in(name) == call
    assert frequency_in(name) == freq


def test_queries_normalize_frequencies_and_call_signs() -> None:
    assert query_terms("98.5 FM") == ["fm985"]
    assert query_terms("98.5") == ["freq985"]
    assert query_terms("1090 AM") == ["am1090"]
    assert query_terms("KIRO-FM") == ["kiro"]
    assert query_terms("jazz  Seattle") == ["jazz", "seattle"]


def test_merge_keeps_the_trusted_source_and_records_provenance() -> None:
    picks = StationFacts(key="uuid-kuow", name="KUOW", description="Ours, curated.")
    merged = merge([("community_picks", [picks]), ("station_catalog", [KUOW])])
    assert len(merged) == 1
    record = merged[0]
    assert record.description == "Ours, curated."
    assert record.slogan == "Seattle's NPR station"
    assert record.provenance["description"] == "community_picks"
    assert record.provenance["slogan"] == "station_catalog"
    # The trusted name "KUOW" alone is not certain enough for a call sign; the
    # catalog's "KUOW 94.9" is, so the call sign is credited to the catalog.
    assert (record.call_sign, record.frequency) == ("KUOW", "94.9 FM")
    assert record.provenance["call_sign"] == "station_catalog"


def test_merge_never_joins_on_a_shared_url_alone() -> None:
    a = StationFacts(key="a", name="Relay One", stream_url="https://x.example/s")
    b = StationFacts(key="b", name="Relay Two", stream_url="https://x.example/s")
    same = StationFacts(key="c", name="relay one", stream_url="https://X.example/s")
    merged = merge([("one", [a]), ("two", [b, same])])
    assert [r.key for r in merged] == ["a", "b"]


# -- sources ----------------------------------------------------------------------


def test_only_approved_sources_are_built_and_pending_ones_never(tmp_path: Path) -> None:
    approved = [source_id for source_id, _ in sources.approved_source_factories()]
    assert approved == ["community_picks", "station_catalog"]
    pending = {p.id for p in sources.PENDING_SOURCES}
    assert not pending & set(approved)
    built = sources.build_sources({})
    assert [s.id for s in built] == ["community_picks"]
    assert all(isinstance(s, sources.EnrichmentSource) for s in built)


def test_community_picks_yield_streams_only(tmp_path: Path) -> None:
    document = {
        "updated": "2026-10-01T00:00:00Z",
        "collections": [
            {
                "title": "Community Radio",
                "items": [
                    {
                        "type": "stream",
                        "title": "Team FM",
                        "stream_url": "https://team.example/live",
                        "description": "Community radio for the valley.",
                    },
                    {"type": "podcast", "title": "A show", "feed_url": "https://f.example"},
                ],
            }
        ],
    }
    path = tmp_path / "picks.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    records = list(sources.CommunityPicksSource(path).records())
    assert [r.name for r in records] == ["Team FM"]
    assert records[0].key == "https://team.example/live"
    assert records[0].confirmed == "2026-10-01"


def test_station_catalog_source_reads_only_what_the_seed_carries(tmp_path: Path) -> None:
    db = tmp_path / "catalog.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE stations(key, name, stream_url, homepage, country, state, language, "
        "tags, last_seen, vanished_at)"
    )
    con.execute(
        "INSERT INTO stations VALUES ('u1','KUOW 94.9','https://k.example','',"
        "'United States','Washington','english','news,npr','1760000000',NULL)"
    )
    con.execute(
        "INSERT INTO stations VALUES ('u2','Gone','https://g.example','','','','','',"
        "'1760000000','1760000001')"
    )
    con.commit()
    con.close()
    records = list(sources.StationCatalogSource(db).records())
    assert [r.key for r in records] == ["u1"]
    assert records[0].confirmed.startswith("2025-")
    assert merge([("station_catalog", records)])[0].call_sign == "KUOW"


# -- the pack and its signature --------------------------------------------------


def test_a_signed_pack_round_trips(tmp_path: Path, key: signing.SigningKey) -> None:
    path = _signed_pack(tmp_path, key, KUOW, KIRO, built="2026-10-16T00:00:00Z")
    opened = pack.open_verified(path, public_key=key.verify_key)
    assert [s.key for s in opened.stations] == ["uuid-kiro", "uuid-kuow"]
    manifest = pack.read_manifest(tmp_path)
    assert manifest["stations"] == 2 and manifest["signed"] is True


def test_an_unsigned_pack_is_refused(tmp_path: Path) -> None:
    built = pack.build_pack([KUOW], [], built_at="2026-10-16T00:00:00Z")
    path, sidecar, _ = pack.write_pack(tmp_path, built)
    assert sidecar is None
    assert json.loads((tmp_path / pack.MANIFEST_NAME).read_text())["signed"] is False
    with pytest.raises(PackRefusedError, match="not signed"):
        pack.open_verified(path, public_key=signing.SigningKey.generate().verify_key)


def test_a_stranger_signature_is_refused(tmp_path: Path, key: signing.SigningKey) -> None:
    path = _signed_pack(tmp_path, key, KUOW, built="2026-10-16T00:00:00Z")
    with pytest.raises(PackRefusedError, match="refused"):
        pack.open_verified(path, public_key=signing.SigningKey.generate().verify_key)


def test_tampered_bytes_are_refused(tmp_path: Path, key: signing.SigningKey) -> None:
    path = _signed_pack(tmp_path, key, KUOW, built="2026-10-16T00:00:00Z")
    data = bytearray(path.read_bytes())
    data[-1] ^= 0xFF
    path.write_bytes(bytes(data))
    with pytest.raises(PackRefusedError):
        pack.open_verified(path, public_key=key.verify_key)


def test_an_unsigned_rebuild_removes_the_old_signature(
    tmp_path: Path, key: signing.SigningKey
) -> None:
    _signed_pack(tmp_path, key, KUOW, built="2026-10-16T00:00:00Z")
    rebuilt = pack.build_pack([KIRO], [], built_at="2026-10-17T00:00:00Z")
    path, sidecar, _ = pack.write_pack(tmp_path, rebuilt)
    assert sidecar is None and not Path(str(path) + pack.SIGNATURE_SUFFIX).exists()


def test_a_manifest_mismatch_is_refused(tmp_path: Path, key: signing.SigningKey) -> None:
    path = _signed_pack(tmp_path, key, KUOW, built="2026-10-16T00:00:00Z")
    manifest = tmp_path / pack.MANIFEST_NAME
    document = json.loads(manifest.read_text())
    document["sha256"] = "0" * 64
    manifest.write_text(json.dumps(document))
    with pytest.raises(PackRefusedError, match="manifest"):
        pack.open_verified(path, public_key=key.verify_key)


def test_a_newer_format_is_refused_not_guessed() -> None:
    import lzma

    data = lzma.compress(
        json.dumps({
            "format": pack.FORMAT,
            "version": pack.VERSION + 1,
            "built_at": "x",
            "stations": [],
        }).encode()
    )
    with pytest.raises(PackRefusedError, match="newer version"):
        pack.decode(data)


def test_garbage_is_refused() -> None:
    with pytest.raises(PackRefusedError):
        pack.decode(b"not xz at all")


# -- the store -----------------------------------------------------------------------


def _installed(tmp_path: Path, key: signing.SigningKey, *stations: StationFacts) -> EnrichmentStore:
    store = client.open_store(tmp_path / "profile")
    path = _signed_pack(tmp_path / "pack", key, *stations, built="2026-10-16T00:00:00Z")
    result = client.install_pack_file(store, path, public_key=key.verify_key)
    assert result is not None and result.added == len(stations)
    return store


def test_migrations_run_once_and_a_newer_store_is_refused(tmp_path: Path) -> None:
    con = sqlite3.connect(tmp_path / "s.db", isolation_level=None)
    assert migrate(con) == 0
    assert migrate(con) == SCHEMA_VERSION
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    with pytest.raises(EnrichmentError):
        migrate(con)
    con.close()


def test_a_store_from_a_newer_build_is_recreated(tmp_path: Path) -> None:
    path = tmp_path / "radio-enrichment" / "stations.db"
    path.parent.mkdir(parents=True)
    con = sqlite3.connect(path)
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 5}")
    con.close()
    store = client.open_store(tmp_path)
    assert store.count() == 0
    store.close()


def test_search_finds_by_frequency_call_sign_slogan_and_place(
    tmp_path: Path, key: signing.SigningKey
) -> None:
    store = _installed(tmp_path, key, KUOW, KIRO, JAZZ)
    assert [h.name for h in store.search("94.9")] == ["KUOW 94.9"]
    assert store.search("94.9")[0].explanation == "matched frequency: 94.9 FM"
    assert store.details("uuid-kuow").call_sign == "KUOW"  # type: ignore[union-attr]
    assert [h.name for h in store.search("97.3 FM")] == ["KIRO-FM"]
    assert store.search("97.3")[0].explanation == "matched frequency: 97.3 FM"
    assert [h.name for h in store.search("KIRO")] == ["KIRO-FM"]
    seahawks = store.search("Seahawks")
    assert seahawks[0].row_text == (
        "KIRO-FM, matched slogan: Official home of the Seattle Seahawks"
    )
    assert [h.name for h in store.search("jazz Tacoma")] == ["Jazz24"]
    store.close()


def test_name_outranks_description_and_a_home_state_breaks_ties(
    tmp_path: Path, key: signing.SigningKey
) -> None:
    store = _installed(tmp_path, key, KUOW, KIRO, JAZZ)
    assert store.search("Seattle")[0].name in ("KUOW 94.9", "KIRO-FM")
    assert store.search("Washington", home_state="Washington")
    store.close()


def test_fuzzy_names_only_when_the_index_finds_nothing(
    tmp_path: Path, key: signing.SigningKey
) -> None:
    store = _installed(tmp_path, key, KUOW, KIRO, JAZZ)
    hits = store.search("Jaz24")
    assert [h.name for h in hits] == ["Jazz24"] and hits[0].fuzzy
    assert hits[0].explanation == "close spelling of the name"
    assert store.search("") == [] and store.search('"*') == []
    store.close()


def test_find_for_station_joins_by_key_then_url_and_name(
    tmp_path: Path, key: signing.SigningKey
) -> None:
    picks = StationFacts(
        key="https://team.example/live", name="Team FM", stream_url="https://team.example/live"
    )
    store = _installed(tmp_path, key, KUOW, picks)
    assert store.find_for_station("uuid-kuow", "").name == "KUOW 94.9"  # type: ignore[union-attr]
    found = store.find_for_station("other-uuid", "https://TEAM.example:443/live", "Team FM")
    assert found is not None and found.name == "Team FM"
    assert store.find_for_station("", "https://nowhere.example", "X") is None
    store.close()


def test_an_older_pack_is_not_reinstalled_and_a_newer_one_counts_changes(
    tmp_path: Path, key: signing.SigningKey
) -> None:
    store = _installed(tmp_path, key, KUOW, KIRO)
    same = _signed_pack(tmp_path / "again", key, KUOW, built="2026-10-16T00:00:00Z")
    assert client.install_pack_file(store, same, public_key=key.verify_key) is None
    changed = StationFacts(**{**KUOW.to_dict(), "slogan": "New slogan"})  # type: ignore[arg-type]
    newer = _signed_pack(tmp_path / "newer", key, changed, JAZZ, built="2026-10-23T00:00:00Z")
    result = client.install_pack_file(store, newer, public_key=key.verify_key)
    assert result is not None
    assert (result.added, result.changed, result.removed, result.total) == (1, 1, 1, 2)
    assert client.outcome_sentence(result) == (
        "Station details updated: 1 new, 1 changed, 1 removed; 2 stations in all."
    )
    store.close()


def test_a_refused_pack_leaves_the_installed_facts_alone(
    tmp_path: Path, key: signing.SigningKey
) -> None:
    store = _installed(tmp_path, key, KUOW)
    stranger = signing.SigningKey.generate()
    bad = _signed_pack(tmp_path / "bad", stranger, KIRO, built="2026-10-30T00:00:00Z")
    with pytest.raises(PackRefusedError) as caught:
        client.install_pack_file(store, bad, public_key=key.verify_key)
    assert "unchanged" in client.refusal_sentence(caught.value)
    assert "QUILL-" not in client.refusal_sentence(caught.value)
    assert store.count() == 1 and store.details("uuid-kuow") is not None
    store.close()


def test_install_bundled_with_no_pack_is_a_quiet_no_op(tmp_path: Path) -> None:
    store = client.open_store(tmp_path)
    assert client.install_bundled(store, directory=tmp_path / "none") is None
    assert "No station pack is installed" in client.status_sentence(store)
    store.close()


def test_details_are_labelled_lines_with_their_sources(
    tmp_path: Path, key: signing.SigningKey
) -> None:
    facts = StationFacts(
        **{**KIRO.to_dict(), "attribution": "Text from a licensed source."},  # type: ignore[arg-type]
        provenance={"slogan": "test", "name": "test"},
    )
    text = client.details_text(facts, [pack.SourceCredit("test", "Test source")])
    lines = text.splitlines()
    assert lines[0] == "Name: KIRO-FM"
    assert "Frequency: 97.3 FM" in lines
    assert "Format: news talk" in lines
    assert "Where these facts came from: Test source (name, slogan)" in lines
    assert lines[-1] == "Credit: Text from a licensed source."
    assert client.details_text(None) == "The station pack has nothing about this station."
