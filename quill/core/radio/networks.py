"""Curated "Networks" directory -- well-known broadcasters as one-click nodes.

Every network here is resolved through the **already-integrated Radio Browser**
directory (:func:`quill.core.radio.radio_browser.search_stations`), so this adds
**no new network-egress site** (``network_egress_audit`` stays unchanged), needs
no API keys, and hard-codes no expiring stream URL. No broadcaster's own curated
list or data is copied -- only public directory queries by name/tag/country.

Three kinds of "network" exist and are handled differently (see
``standalone/radio/docs/networks-catalog.md``):

* **Broadcasters with real streams** (BBC, NPR, CBC, ...) -- a curated query that
  returns playable stations.
* **Syndication networks** (Westwood One, NBC News Radio, ...) -- there is *no
  single stream*; the node runs a name search across their **affiliates** and is
  labelled honestly (``note``).
* **CBS News Radio is intentionally absent** -- the syndicated service is ending
  2026-05-22 and CBS-owned local radio became Audacy in 2017.

The queries are an initial, tunable catalog; refine the name/tag/country of any
entry as real Radio Browser results are reviewed.

**Curated networks** (2026-11-07) sit beside the queries: a checked-in table of
channels pinned to each operator's own stream
(:mod:`quill.core.radio.curated_networks`, from BlindRadio by serrebidev, MIT).
Where one covers a network this catalog also queries -- BBC, ABC, MPR, Big R
Radio -- it **replaces** the query under the same id, in the same place, so the
folder is shown once and anything remembered against ``network:bbc`` still
lands on the BBC. :func:`catalog` is the merged list everything here reads.
wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.radio import curated_networks, radio_browser
from quill.core.radio.models import RadioStation

#: Group labels, in display order.
GROUP_PUBLIC = "Public broadcasters"
GROUP_US_NEWS = "US news & talk"
GROUP_US_PUBLIC = "US public radio"
GROUP_SPORTS = "Sports"
GROUP_SYNDICATORS = "Syndicators (affiliates)"
GROUP_MUSIC = "Music"
#: 2026-11-07, for the curated networks: Global UK, Triple M, ARN, NZME.
GROUP_COMMERCIAL = "Commercial radio"
#: 2026-11-07, for the curated networks: K-LOVE and Air1.
GROUP_CHRISTIAN = "Christian radio"

GROUP_ORDER: tuple[str, ...] = (
    GROUP_PUBLIC,
    GROUP_US_NEWS,
    GROUP_US_PUBLIC,
    GROUP_SPORTS,
    GROUP_SYNDICATORS,
    GROUP_MUSIC,
    GROUP_COMMERCIAL,
    GROUP_CHRISTIAN,
)


@dataclass(frozen=True, slots=True)
class Network:
    """One curated network node: a Radio Browser query with a display badge.

    At least one of ``query`` / ``tag`` / ``country`` must be set. ``note`` is a
    short honest qualifier shown for syndicators ("programming carried by local
    stations") or approximate queries.
    """

    network_id: str
    display_name: str
    group: str
    query: str = ""
    tag: str = ""
    country: str = ""
    note: str = ""
    limit: int = 80
    #: Keep only stations whose name starts with this (case-insensitive). For a
    #: network whose name is a common substring: a search for "1.FM" also
    #: returns "011.FM" and "Radio 1.FM", which are not the network.
    name_prefix: str = ""
    #: True for a network read from the curated snapshot rather than queried.
    curated: bool = False
    #: How many channels a curated network has (0 for a query: unknown).
    channel_count: int = 0


#: The catalog. Sources already available through a dedicated directory are
#: not duplicated here.
NETWORKS: tuple[Network, ...] = (
    # -- International public broadcasters (real streams) --------------------
    Network(
        "bbc",
        "BBC",
        GROUP_PUBLIC,
        query="BBC",
        country="The United Kingdom Of Great Britain And Northern Ireland",
    ),
    Network("cbc", "CBC / Radio-Canada", GROUP_PUBLIC, query="CBC", country="Canada"),
    Network("abc-au", "ABC (Australia)", GROUP_PUBLIC, query="ABC", country="Australia"),
    Network("rte", "RTÉ (Ireland)", GROUP_PUBLIC, query="RTÉ", country="Ireland"),
    Network("rnz", "RNZ (New Zealand)", GROUP_PUBLIC, query="RNZ", country="New Zealand"),
    Network("nhk", "NHK (Japan)", GROUP_PUBLIC, query="NHK"),
    Network("dw", "Deutsche Welle", GROUP_PUBLIC, query="Deutsche Welle"),
    Network(
        "deutschlandfunk",
        "Deutschlandfunk",
        GROUP_PUBLIC,
        query="Deutschlandfunk",
        country="Germany",
    ),
    Network(
        "radio-france",
        "Radio France (France Inter)",
        GROUP_PUBLIC,
        query="France Inter",
        note="flagship; more Radio France stations via Search",
    ),
    Network("rfi", "RFI (France Int'l)", GROUP_PUBLIC, query="RFI"),
    Network("orf", "ORF (Austria)", GROUP_PUBLIC, query="ORF", country="Austria"),
    Network("srf", "SRF (Switzerland)", GROUP_PUBLIC, query="SRF", country="Switzerland"),
    Network("rai", "RAI (Italy)", GROUP_PUBLIC, query="Rai Radio", country="Italy"),
    Network("rne", "RNE / RTVE (Spain)", GROUP_PUBLIC, query="RNE", country="Spain"),
    Network("npo", "NPO (Netherlands)", GROUP_PUBLIC, query="NPO Radio", country="The Netherlands"),
    Network("nrk", "NRK (Norway)", GROUP_PUBLIC, query="NRK", country="Norway"),
    Network("dr", "DR (Denmark)", GROUP_PUBLIC, query="DR P", country="Denmark"),
    Network(
        "sr-se", "Sveriges Radio (Sweden)", GROUP_PUBLIC, query="Sveriges Radio", country="Sweden"
    ),
    Network("yle", "Yle (Finland)", GROUP_PUBLIC, query="Yle", country="Finland"),
    Network("voa", "Voice of America", GROUP_PUBLIC, query="Voice of America"),
    Network("kbs", "KBS (Korea)", GROUP_PUBLIC, query="KBS"),
    # -- US news & talk (real national streams) -----------------------------
    Network("npr", "NPR", GROUP_US_NEWS, tag="npr"),
    Network("fox-news-radio", "Fox News Radio", GROUP_US_NEWS, query="Fox News"),
    Network("cnn", "CNN", GROUP_US_NEWS, query="CNN"),
    Network("bloomberg", "Bloomberg Radio", GROUP_US_NEWS, query="Bloomberg"),
    # -- US public radio (beyond NPR) ---------------------------------------
    Network("apm", "American Public Media / MPR", GROUP_US_PUBLIC, query="MPR News"),
    Network("kexp", "KEXP", GROUP_US_PUBLIC, query="KEXP"),
    Network("kcrw", "KCRW", GROUP_US_PUBLIC, query="KCRW"),
    Network("wnyc", "WNYC", GROUP_US_PUBLIC, query="WNYC"),
    # -- Sports --------------------------------------------------------------
    Network("espn-radio", "ESPN Radio", GROUP_SPORTS, query="ESPN"),
    # -- Syndicators (no single stream: search their affiliates) ------------
    Network(
        "westwood-one",
        "Westwood One",
        GROUP_SYNDICATORS,
        query="Westwood One",
        note="syndication; programming carried by local affiliate stations",
    ),
    Network(
        "nbc-news-radio",
        "NBC News Radio",
        GROUP_SYNDICATORS,
        query="NBC News Radio",
        note="syndicated news service; carried by affiliates",
    ),
    Network(
        "abc-news-radio",
        "ABC News Radio (US)",
        GROUP_SYNDICATORS,
        query="ABC News Radio",
        note="syndicated; distinct from ABC Australia above",
    ),
    # -- Music ---------------------------------------------------------------
    Network("radio-paradise", "Radio Paradise", GROUP_MUSIC, query="Radio Paradise"),
    Network("fip", "FIP (Radio France)", GROUP_MUSIC, query="FIP"),
    # 2026-10-25. 181.FM also has its own branch with the network's genres
    # (one_eighty_one.py); this is its place among the networks. Big R Radio and
    # 1.FM publish no station list a player may use -- 1.FM's needs a private
    # key -- so the directory's own entries for them are the honest route.
    Network("181fm", "181.FM", GROUP_MUSIC, query="181.FM", name_prefix="181.FM", limit=200),
    Network(
        "big-r-radio",
        "Big R Radio",
        GROUP_MUSIC,
        query="Big R Radio",
        name_prefix="Big R Radio",
        limit=120,
    ),
    Network("1fm", "1.FM", GROUP_MUSIC, query="1.FM", name_prefix="1.FM", limit=400),
)


def _from_curated(entry: curated_networks.CuratedNetwork) -> Network:
    group = entry.group if entry.group in GROUP_ORDER else GROUP_MUSIC
    return Network(
        entry.network_id,
        entry.display_name,
        group,
        curated=True,
        channel_count=len(entry.channels),
    )


def merge(
    queried: tuple[Network, ...], curated: tuple[curated_networks.CuratedNetwork, ...]
) -> tuple[Network, ...]:
    """The queried networks with the curated ones folded in (pure).

    A curated network that ``replaces`` a queried one takes its place and its
    id; any other curated network follows the queried ones. A curated network
    whose id collides with a query it did not declare it replaces is dropped,
    because two folders under one id would be one folder that cannot be told
    apart from the other.
    """
    by_id = {entry.network_id: entry for entry in curated}
    replacing = {entry.replaces: entry for entry in curated if entry.replaces}
    queried_ids = {n.network_id for n in queried}
    merged: list[Network] = []
    placed: set[str] = set()
    for network in queried:
        stand_in = replacing.get(network.network_id)
        if stand_in is not None and stand_in.network_id not in placed:
            placed.add(stand_in.network_id)
            merged.append(_from_curated(stand_in))
        else:
            merged.append(network)
    for network_id, entry in by_id.items():
        if network_id in placed or network_id in queried_ids:
            continue
        merged.append(_from_curated(entry))
    return tuple(merged)


def catalog() -> tuple[Network, ...]:
    """Every network the branch shows: the queries, with the curated ones merged."""
    return merge(NETWORKS, curated_networks.networks())


def groups() -> tuple[str, ...]:
    """Group labels that actually have at least one network, in display order."""
    present = {n.group for n in catalog()}
    return tuple(g for g in GROUP_ORDER if g in present)


def networks_in_group(group: str) -> tuple[Network, ...]:
    """Every network in *group*, in catalog order."""
    return tuple(n for n in catalog() if n.group == group)


def get_network(network_id: str) -> Network | None:
    """The network with *network_id*, or ``None``."""
    return next((n for n in catalog() if n.network_id == network_id), None)


def network_stations(network: Network, *, safe_mode: bool = False) -> list[RadioStation]:
    """Playable stations for *network*, via a curated Radio Browser query.

    Reuses the integrated Radio Browser client, so no new egress site is
    introduced. Safe Mode is enforced by ``search_stations`` itself. A network
    with a ``name_prefix`` keeps only stations named for it, each stream once.
    A curated network reads its snapshot and makes no request at all.
    """
    if network.curated:
        return curated_networks.stations(network.network_id)
    stations = radio_browser.search_stations(
        network.query,
        tag=network.tag,
        country=network.country,
        limit=network.limit,
        safe_mode=safe_mode,
    )
    if not network.name_prefix:
        return stations
    prefix = network.name_prefix.casefold()
    seen: set[str] = set()
    kept: list[RadioStation] = []
    for station in stations:
        if station.name.casefold().startswith(prefix) and station.stream_url not in seen:
            seen.add(station.stream_url)
            kept.append(station)
    return kept
