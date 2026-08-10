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
entry as real Radio Browser results are reviewed. wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.radio import radio_browser
from quill.core.radio.models import RadioStation

#: Group labels, in display order.
GROUP_PUBLIC = "Public broadcasters"
GROUP_US_NEWS = "US news & talk"
GROUP_US_PUBLIC = "US public radio"
GROUP_SPORTS = "Sports"
GROUP_SYNDICATORS = "Syndicators (affiliates)"
GROUP_MUSIC = "Music"

GROUP_ORDER: tuple[str, ...] = (
    GROUP_PUBLIC,
    GROUP_US_NEWS,
    GROUP_US_PUBLIC,
    GROUP_SPORTS,
    GROUP_SYNDICATORS,
    GROUP_MUSIC,
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


#: The catalog. SomaFM stays a built-in source (its own channels.json), so it is
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
)


def groups() -> tuple[str, ...]:
    """Group labels that actually have at least one network, in display order."""
    present = {n.group for n in NETWORKS}
    return tuple(g for g in GROUP_ORDER if g in present)


def networks_in_group(group: str) -> tuple[Network, ...]:
    """Every network in *group*, in catalog order."""
    return tuple(n for n in NETWORKS if n.group == group)


def get_network(network_id: str) -> Network | None:
    """The network with *network_id*, or ``None``."""
    return next((n for n in NETWORKS if n.network_id == network_id), None)


def network_stations(network: Network, *, safe_mode: bool = False) -> list[RadioStation]:
    """Playable stations for *network*, via a curated Radio Browser query.

    Reuses the integrated Radio Browser client, so no new egress site is
    introduced. Safe Mode is enforced by ``search_stations`` itself.
    """
    return radio_browser.search_stations(
        network.query,
        tag=network.tag,
        country=network.country,
        limit=network.limit,
        safe_mode=safe_mode,
    )
