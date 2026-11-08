"""Curated networks: each channel pinned to the operator's own published stream.

Most Networks entries (:mod:`quill.core.radio.networks`) are a Radio Browser
query, so a network is only as good as the directory's rows -- the BBC query
returns whatever listeners added, half of it relays. The networks here are a
checked-in table instead, ``quill/data/radio_networks.json``: WFMU and its side
channels, Global's UK brands, Big R Radio, Sunshine Live, Planet Radio, Nightride
FM, Power Hitz, Radio Record, PulsRadio, MPR and YourClassical, the ABC by
region, K-LOVE and Air1, NZME, Triple M and ARN, Radio Swiss, WFUV, NTS with its
Infinite Mixtapes, and the BBC's own services.

The idea, the network list and the stream addresses come from BlindRadio by
serrebidev (MIT), ``crates/blindradio-core/data/networks.json`` and
``docs/radio-directory-sources.md``; the MIT notice travels inside the data file
(``license``) and beside it (``radio_networks.LICENSE.txt``). Each network also
says where its addresses came from (``origin``).

Listing a curated network makes **no network call**: the app reads the snapshot.
Only playing a channel reaches the operator's stream, through the player like
any other station. ``scripts/refresh_radio_networks.py`` re-checks every address
and, for NTS, Radio Record and the BBC, reads the operator's own list; it is run
by hand, never by the app, a test or CI.

A curated network may **replace** a Radio Browser network of the same id
(``replaces``), so the BBC is one folder, not two. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from quill.core.radio.models import RadioStation

_LOG = logging.getLogger(__name__)

#: ``"AAC 128k"`` -> codec ``AAC``, 128 kbps.
_INFO_RE = re.compile(r"^\s*([A-Za-z+]+)(?:\s+(\d+)\s*k)?", re.IGNORECASE)
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True, slots=True)
class CuratedChannel:
    """One channel: a name and the operator's own stream address."""

    channel_id: str
    name: str
    url: str
    info: str = ""
    #: Why this address is plain HTTP, when it is. Empty for HTTPS.
    http_reason: str = ""


@dataclass(frozen=True, slots=True)
class CuratedNetwork:
    """One network from the snapshot."""

    network_id: str
    display_name: str
    group: str
    channels: tuple[CuratedChannel, ...]
    homepage: str = ""
    #: Where the addresses came from, in a sentence or two.
    origin: str = ""
    #: The Radio Browser network id this one stands in for, or "".
    replaces: str = ""
    #: The operator API the refresh tool reads ("nts", "radiorecord", "bbc"), or "".
    refresh: str = ""


def snapshot_path() -> Path:
    """Where the snapshot lives in the package (``quill/data``)."""
    return Path(__file__).resolve().parents[2] / "data" / "radio_networks.json"


def _channel(raw: object) -> CuratedChannel | None:
    if not isinstance(raw, dict):
        return None
    channel_id = str(raw.get("id") or "").strip()
    name = " ".join(str(raw.get("name") or "").split())
    url = str(raw.get("url") or "").strip()
    if not channel_id or not name or not url.startswith(("https://", "http://")):
        return None
    return CuratedChannel(
        channel_id=channel_id,
        name=name,
        url=url,
        info=str(raw.get("info") or "").strip(),
        http_reason=str(raw.get("http_reason") or "").strip(),
    )


def parse_snapshot(doc: object) -> tuple[CuratedNetwork, ...]:
    """Every usable network in a snapshot document (pure, tolerant).

    A malformed row is skipped rather than failing the whole table; the strict
    checks live in :func:`problems`, which the tests run.
    """
    rows = doc.get("networks") if isinstance(doc, dict) else None
    out: list[CuratedNetwork] = []
    for raw in rows if isinstance(rows, list) else []:
        if not isinstance(raw, dict):
            continue
        network_id = str(raw.get("id") or "").strip()
        name = str(raw.get("name") or "").strip()
        group = str(raw.get("group") or "").strip()
        raw_channels = raw.get("channels")
        channel_rows = raw_channels if isinstance(raw_channels, list) else []
        channels = tuple(ch for ch in (_channel(item) for item in channel_rows) if ch)
        if not network_id or not name or not group or not channels:
            continue
        out.append(
            CuratedNetwork(
                network_id=network_id,
                display_name=name,
                group=group,
                channels=channels,
                homepage=str(raw.get("homepage") or "").strip(),
                origin=str(raw.get("origin") or "").strip(),
                replaces=str(raw.get("replaces") or "").strip(),
                refresh=str(raw.get("refresh") or "").strip(),
            )
        )
    return tuple(out)


def problems(doc: object) -> list[str]:
    """Everything wrong with a snapshot document, in words (pure); ``[]`` is clean.

    Duplicate network or channel ids, a plain-HTTP address with no stated
    reason, a network with no ``origin``, and an attribution or licence that has
    gone missing are all failures: the last because the MIT notice is the
    condition the data is used under.
    """
    found: list[str] = []
    if not isinstance(doc, dict):
        return ["the snapshot is not a JSON object"]
    if "serrebidev" not in str(doc.get("attribution") or ""):
        found.append("the BlindRadio attribution is missing")
    license_text = str(doc.get("license") or "")
    if "MIT License" not in license_text or "Copyright (c) 2026 serrebidev" not in license_text:
        found.append("the MIT notice is missing")
    rows = doc.get("networks")
    if not isinstance(rows, list) or not rows:
        return [*found, "there are no networks"]
    network_ids: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            found.append("a network entry is not an object")
            continue
        network_id = str(raw.get("id") or "")
        if not _ID_RE.match(network_id):
            found.append(f"bad network id {network_id!r}")
        if network_id in network_ids:
            found.append(f"network id {network_id!r} appears twice")
        network_ids.add(network_id)
        if not str(raw.get("origin") or "").strip():
            found.append(f"{network_id}: no origin")
        if raw.get("replaces") and raw["replaces"] != network_id:
            found.append(f"{network_id}: replaces {raw['replaces']!r} under another id")
        channel_ids: set[str] = set()
        urls: set[str] = set()
        channels = raw.get("channels")
        for channel in channels if isinstance(channels, list) else []:
            if not isinstance(channel, dict):
                found.append(f"{network_id}: a channel is not an object")
                continue
            channel_id = str(channel.get("id") or "")
            url = str(channel.get("url") or "")
            if not _ID_RE.match(channel_id):
                found.append(f"{network_id}: bad channel id {channel_id!r}")
            if channel_id in channel_ids:
                found.append(f"{network_id}: channel id {channel_id!r} appears twice")
            channel_ids.add(channel_id)
            if url in urls:
                found.append(f"{network_id}: {url} appears twice")
            urls.add(url)
            if not str(channel.get("name") or "").strip():
                found.append(f"{network_id}/{channel_id}: no name")
            if url.startswith("http://"):
                if not str(channel.get("http_reason") or "").strip():
                    found.append(f"{network_id}/{channel_id}: plain HTTP with no reason")
            elif not url.startswith("https://"):
                found.append(f"{network_id}/{channel_id}: not a web address")
        if not channel_ids:
            found.append(f"{network_id}: no channels")
    return found


@lru_cache(maxsize=1)
def networks() -> tuple[CuratedNetwork, ...]:
    """Every curated network, in the snapshot's order. Read once per process.

    A missing or unreadable file yields no curated networks -- the Radio Browser
    ones still show -- rather than an exception reaching the browse tree.
    """
    path = snapshot_path()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        _LOG.warning("Curated networks unavailable (%s): %s", path, error)
        return ()
    return parse_snapshot(doc)


def get(network_id: str) -> CuratedNetwork | None:
    """The curated network with *network_id*, or ``None``."""
    return next((n for n in networks() if n.network_id == network_id), None)


def replaced_ids() -> frozenset[str]:
    """Radio Browser network ids a curated network stands in for."""
    return frozenset(n.replaces for n in networks() if n.replaces)


def _codec_and_bitrate(info: str) -> tuple[str, int]:
    match = _INFO_RE.match(info)
    if not match:
        return "", 0
    codec = match.group(1).upper()
    return codec, int(match.group(2)) if match.group(2) else 0


def to_station(network: CuratedNetwork, channel: CuratedChannel) -> RadioStation:
    """One channel as a station that plays, records and saves like any other.

    ``station_uuid`` is ``net:<network>:<channel>`` -- stable across snapshot
    refreshes, because the refresh tool keeps a channel's id when its address
    moves -- so a favorite or a play count follows the channel, not the URL.
    """
    codec, bitrate = _codec_and_bitrate(channel.info)
    return RadioStation(
        name=channel.name,
        stream_url=channel.url,
        station_uuid=f"net:{network.network_id}:{channel.channel_id}",
        homepage=network.homepage,
        # No country: Browse adds it to every label, and the network's own
        # folder already says where it is.
        tags=(network.display_name,),
        codec=codec,
        bitrate_kbps=bitrate,
        source=network.display_name,
    )


def stations(network_id: str) -> list[RadioStation]:
    """Every channel of *network_id*, A to Z, as stations. No network call."""
    network = get(network_id)
    if network is None:
        return []
    rows = [to_station(network, channel) for channel in network.channels]
    return sorted(rows, key=lambda s: s.name.casefold())


def search_stations(query: str) -> list[RadioStation]:
    """Channels whose name or network matches *query* (no network call).

    A blank query finds nothing rather than every channel, so a search box left
    empty does not pour five hundred rows into the results.
    """
    words = query.casefold().split()
    if not words:
        return []
    found: list[RadioStation] = []
    for network in networks():
        for channel in network.channels:
            haystack = f"{channel.name} {network.display_name}".casefold()
            if all(word in haystack for word in words):
                found.append(to_station(network, channel))
    return found
