"""Re-check, and where possible refresh, Quill Radio's curated networks.

``quill/data/radio_networks.json`` pins each network's channels to the
operator's own published stream. Streams move, so this tool checks every one
the way BlindRadio checked them when it built the list it came from: a GET,
HTTP 200, an audio content type, 4096 bytes of the stream read, and then the
connection closed. An HLS address passes when its playlist (and, for a master
playlist, its first variant) is served and the newest segment reads 4096 bytes.

The probe idea, its pass rule and most of the data come from BlindRadio by
serrebidev (MIT), docs/radio-directory-sources.md, "Live verification".

Three networks publish their own channel list through a keyless API, and for
them ``--refresh`` reads the list instead of trusting the hand-kept rows:

- NTS: ``https://www.nts.live/api/v2/mixtapes`` (each ``audio_stream_endpoint``).
- Radio Record: ``https://www.radiorecord.ru/api/stations/`` (``stream_128``).
- BBC: ``https://rms.api.bbc.co.uk/v2/experience/inline/stations``. It names the
  services but carries no stream addresses, so it is a roster check only: a
  service it lists that the snapshot lacks is reported, never invented.

The shipped app never runs any of this; it reads the snapshot. This is a
maintainer's tool, run by hand. It refuses to run under pytest or in CI,
because a test or a build that depends on 500 strangers' servers is a test
that fails for no reason.

Usage::

    python scripts/refresh_radio_networks.py              # probe, report dead
    python scripts/refresh_radio_networks.py --refresh    # read the three APIs first
    python scripts/refresh_radio_networks.py --upgrade-http --drop-dead --write
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "quill" / "data" / "radio_networks.json"

USER_AGENT = "QuillRadio-network-check/1.0 (+https://github.com/Community-Access)"
SAMPLE_BYTES = 4096
TIMEOUT_SECONDS = 15.0
MAX_PLAYLIST_BYTES = 512_000
MAX_API_BYTES = 8_000_000

#: Content types a progressive stream may answer with.
_AUDIO_TYPES = ("audio/", "application/ogg", "application/octet-stream")
_HLS_TYPES = (
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "audio/mpegurl",
    "audio/x-mpegurl",
)
_SEASONAL = re.compile(r"christmas|xmas|weihnacht|halloween|holiday|new year|advent", re.I)
_SLUG = re.compile(r"[^a-z0-9]+")


# --- pure helpers (tested) ----------------------------------------------------


def media_type(content_type: str) -> str:
    """``"audio/mpeg; charset=x"`` -> ``"audio/mpeg"`` (pure)."""
    return content_type.split(";", 1)[0].strip().casefold()


def is_hls(url: str, content_type: str = "") -> bool:
    """Whether *url* (or the type it answered with) is an HLS playlist (pure)."""
    path = urllib.parse.urlsplit(url).path.casefold()
    return path.endswith((".m3u8", ".m3u")) or media_type(content_type) in _HLS_TYPES


def is_audio_type(content_type: str) -> bool:
    """Whether a progressive stream's content type is audio (pure).

    ``application/octet-stream`` is allowed because some Icecast relays send it
    for AAC; the 4096 bytes still have to arrive.
    """
    kind = media_type(content_type)
    return any(kind == t or (t.endswith("/") and kind.startswith(t)) for t in _AUDIO_TYPES)


def hls_next(playlist: str, base_url: str) -> tuple[str, bool]:
    """The URI to fetch next from an HLS playlist, and whether it is a variant.

    A master playlist (``#EXT-X-STREAM-INF``) gives its first variant; a media
    playlist gives its newest segment. ``("", False)`` when there is neither.
    """
    lines = [line.strip() for line in playlist.splitlines()]
    if not lines or not lines[0].startswith("#EXTM3U"):
        return "", False
    uris = [line for line in lines if line and not line.startswith("#")]
    if not uris:
        return "", False
    master = any(line.startswith("#EXT-X-STREAM-INF") for line in lines)
    chosen = uris[0] if master else uris[-1]
    return urllib.parse.urljoin(base_url, chosen), master


def channel_slug(text: str) -> str:
    """A stable channel id from a name (pure)."""
    return _SLUG.sub("-", text.casefold()).strip("-")


def nts_channels(payload: object) -> list[dict[str, str]]:
    """NTS's Infinite Mixtapes as snapshot channel rows (pure)."""
    results = payload.get("results") if isinstance(payload, dict) else None
    rows: list[dict[str, str]] = []
    for item in results if isinstance(results, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("title") or "").strip()
        url = str(item.get("audio_stream_endpoint") or "").strip()
        alias = str(item.get("mixtape_alias") or "").strip() or channel_slug(name)
        if name and url.startswith("https://"):
            rows.append({"id": alias, "name": name, "url": url})
    return rows


def radio_record_channels(payload: object) -> list[dict[str, str]]:
    """Radio Record's channels as snapshot rows (pure); seasonal ones left out."""
    result = payload.get("result") if isinstance(payload, dict) else None
    stations = result.get("stations") if isinstance(result, dict) else None
    rows: list[dict[str, str]] = []
    for item in stations if isinstance(stations, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("title") or "").strip()
        url = str(item.get("stream_128") or "").strip()
        if not name or not url.startswith("https://") or _SEASONAL.search(name):
            continue
        rows.append({
            "id": channel_slug(str(item.get("prefix") or name)),
            "name": name,
            "url": url,
            "info": "AAC",
        })
    return rows


def bbc_roster(payload: object) -> list[tuple[str, str]]:
    """``[(service id, title), ...]`` from the BBC station list (pure)."""
    modules = payload.get("data") if isinstance(payload, dict) else None
    roster: list[tuple[str, str]] = []
    for module in modules if isinstance(modules, list) else []:
        items = module.get("data") if isinstance(module, dict) else None
        for item in items if isinstance(items, list) else []:
            network = item.get("network") if isinstance(item, dict) else None
            if not isinstance(network, dict):
                continue
            service = str(network.get("id") or item.get("id") or "").strip()
            title = str(network.get("short_title") or "").strip()
            if service and (service, title) not in roster:
                roster.append((service, title))
    return roster


def roster_key(title: str) -> str:
    """A BBC service title compared loosely: "Radio 6 Music" is "6 Music" (pure)."""
    key = channel_slug(title)
    for prefix in ("bbc-", "radio-"):
        if key.startswith(prefix):
            key = key[len(prefix) :]
    return key


def merge_channels(
    existing: list[dict[str, str]], fresh: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    """Fold an API's list into a network's rows (pure).

    Matched by stream address first and then by id, so a channel that moved its
    stream keeps its id (and with it every favorite saved from it). Hand-kept
    rows the API does not know -- NTS 1 and 2 are not mixtapes -- stay; rows the
    API used to list and no longer does are reported for a person to decide.
    Returns ``(merged, added names, missing names)``.
    """
    by_url = {row["url"]: row for row in existing}
    by_id = {row["id"]: row for row in existing}
    merged = [dict(row) for row in existing]
    index = {row["id"]: i for i, row in enumerate(merged)}
    added: list[str] = []
    matched: set[str] = set()
    for row in fresh:
        known = by_url.get(row["url"]) or by_id.get(row["id"])
        if known is None:
            new_id = row["id"]
            while new_id in index:
                new_id += "-2"
            merged.append({**row, "id": new_id})
            index[new_id] = len(merged) - 1
            added.append(row["name"])
            matched.add(new_id)
            continue
        matched.add(known["id"])
        slot = merged[index[known["id"]]]
        slot["url"] = row["url"]
        slot["name"] = row["name"] or slot["name"]
    fresh_hosts = {urllib.parse.urlsplit(row["url"]).hostname for row in fresh}
    missing = [
        row["name"]
        for row in existing
        if row["id"] not in matched and urllib.parse.urlsplit(row["url"]).hostname in fresh_hosts
    ]
    return merged, added, missing


# --- network (never in tests) ---------------------------------------------------


def _refuse_in_tests() -> None:
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("CI"):
        raise SystemExit("refresh_radio_networks.py is a hand-run tool; not under pytest or CI.")


def _open(url: str) -> Any:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip", "Icy-MetaData": "0"}
    )
    return urllib.request.urlopen(  # noqa: S310 - fixed http(s) addresses from our own file
        request, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
    )


def _read_text(url: str, limit: int) -> tuple[str, str]:
    with _open(url) as resp:
        data = resp.read(limit + 1)
        if resp.headers.get("Content-Encoding", "").casefold() == "gzip":
            data = gzip.decompress(data)
        return data[:limit].decode("utf-8", errors="replace"), resp.headers.get("Content-Type", "")


def probe(url: str, *, _depth: int = 0) -> tuple[bool, str]:
    """``(answers audio, what happened)`` for one address. Closes every connection."""
    try:
        with _open(url) as resp:
            status = getattr(resp, "status", 200)
            ctype = resp.headers.get("Content-Type", "")
            if status != 200:
                return False, f"HTTP {status}"
            if is_hls(url, ctype):
                body = resp.read(MAX_PLAYLIST_BYTES)
                if resp.headers.get("Content-Encoding", "").casefold() == "gzip":
                    body = gzip.decompress(body)
                text = body.decode("utf-8", errors="replace")
                final = resp.geturl()
            else:
                if not is_audio_type(ctype):
                    return False, f"not audio ({media_type(ctype) or 'no type'})"
                sample = resp.read(SAMPLE_BYTES)
                if len(sample) < SAMPLE_BYTES:
                    return False, f"only {len(sample)} bytes"
                return True, media_type(ctype)
    except urllib.error.HTTPError as error:
        return False, f"HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError, ValueError) as error:
        return False, f"{type(error).__name__}: {getattr(error, 'reason', error)}"
    nxt, is_variant = hls_next(text, final)
    if not nxt:
        return False, "HLS playlist with nothing in it"
    if is_variant and _depth < 2:
        ok, detail = probe(nxt, _depth=_depth + 1)
        return ok, f"HLS variant: {detail}"
    try:
        with _open(nxt) as seg:
            if getattr(seg, "status", 200) != 200:
                return False, f"HLS segment HTTP {seg.status}"
            sample = seg.read(SAMPLE_BYTES)
    except urllib.error.HTTPError as error:
        return False, f"HLS segment HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError, ValueError) as error:
        return False, f"HLS segment {type(error).__name__}"
    if len(sample) < SAMPLE_BYTES:
        return False, f"HLS segment only {len(sample)} bytes"
    return True, "HLS"


def _api(url: str) -> object:
    text, _ctype = _read_text(url, MAX_API_BYTES)
    return json.loads(text)


_REFRESHERS: dict[str, tuple[str, Callable[[object], list[dict[str, str]]]]] = {
    "nts": ("https://www.nts.live/api/v2/mixtapes", nts_channels),
    "radiorecord": ("https://www.radiorecord.ru/api/stations/", radio_record_channels),
}
_BBC_STATIONS = "https://rms.api.bbc.co.uk/v2/experience/inline/stations"


def refresh(doc: dict[str, Any]) -> None:
    """Fold each refreshable network's own list into the snapshot, in place."""
    for network in doc["networks"]:
        kind = network.get("refresh")
        if kind == "bbc":
            have = {roster_key(row["name"]) for row in network["channels"]}
            try:
                roster = bbc_roster(_api(_BBC_STATIONS))
            except (OSError, ValueError) as error:
                print(f"BBC: station list unreadable ({error})")
                continue
            absent = [title for _sid, title in roster if roster_key(title) not in have]
            print(f"BBC: {len(roster)} services listed; not in the snapshot: {absent or 'none'}")
            continue
        if kind not in _REFRESHERS:
            continue
        url, parse = _REFRESHERS[kind]
        try:
            fresh = parse(_api(url))
        except (OSError, ValueError) as error:
            print(f"{network['name']}: list unreadable ({error}); rows kept")
            continue
        if not fresh:
            print(f"{network['name']}: the list came back empty; rows kept")
            continue
        merged, added, missing = merge_channels(network["channels"], fresh)
        network["channels"] = merged
        print(f"{network['name']}: {len(added)} added {added}; no longer listed {missing}")


def _https_of(url: str) -> str:
    return "https://" + url[len("http://") :] if url.startswith("http://") else url


def run_probe(
    doc: dict[str, Any], *, upgrade_http: bool, workers: int = 16
) -> list[tuple[str, dict[str, str], str]]:
    """Probe every channel; return ``[(network name, channel row, reason)]`` for the dead."""
    rows = [(net["name"], ch) for net in doc["networks"] for ch in net["channels"]]

    def check(item: tuple[str, dict[str, str]]) -> tuple[str, dict[str, str], bool, str]:
        name, channel = item
        if upgrade_http and channel["url"].startswith("http://"):
            ok, detail = probe(_https_of(channel["url"]))
            if ok:
                channel["url"] = _https_of(channel["url"])
                channel.pop("http_reason", None)
                return name, channel, True, "upgraded to https"
        ok, detail = probe(channel["url"])
        if not ok:
            # One retry: some hosts (icecast.pulsradio.com, 2026-11-07) refuse a
            # TLS handshake now and then and answer the next one.
            ok, detail = probe(channel["url"])
        return name, channel, ok, detail

    dead: list[tuple[str, dict[str, str], str]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for name, channel, ok, detail in pool.map(check, rows):
            if not ok:
                dead.append((name, channel, detail))
            elif detail == "upgraded to https":
                print(f"https: {name} / {channel['name']}")
    return dead


def save(doc: dict[str, Any], path: Path = SNAPSHOT) -> None:
    """Write the snapshot with LF endings, the way it is committed."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=1)
        handle.write("\n")


def _drop(doc: dict[str, Any], dead: Iterable[tuple[str, dict[str, str], str]]) -> None:
    gone = {id(channel) for _name, channel, _why in dead}
    for network in doc["networks"]:
        network["channels"] = [ch for ch in network["channels"] if id(ch) not in gone]
    doc["networks"] = [net for net in doc["networks"] if net["channels"]]


def main(argv: list[str] | None = None) -> int:
    _refuse_in_tests()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--refresh", action="store_true", help="read the operators' own lists")
    parser.add_argument("--upgrade-http", action="store_true", help="try https for http rows")
    parser.add_argument("--drop-dead", action="store_true", help="remove rows that fail")
    parser.add_argument("--write", action="store_true", help="save the snapshot")
    parser.add_argument("--report", type=Path, help="write the dead list here as JSON")
    args = parser.parse_args(argv)
    doc = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if args.refresh:
        refresh(doc)
    dead = run_probe(doc, upgrade_http=args.upgrade_http)
    total = sum(len(net["channels"]) for net in doc["networks"])
    print(f"{total - len(dead)} of {total} answer audio; {len(dead)} do not.")
    for name, channel, why in dead:
        print(f"DEAD {name} / {channel['name']}: {why} ({channel['url']})")
    for net in doc["networks"]:
        for ch in net["channels"]:
            if ch["url"].startswith("http://") and not ch.get("http_reason"):
                ch["http_reason"] = (
                    f"The operator serves this stream over plain HTTP only "
                    f"(checked {date.today().isoformat()})."
                )
    if args.report:
        args.report.write_text(
            json.dumps(
                [
                    {"network": n, "channel": c["name"], "url": c["url"], "why": w}
                    for n, c, w in dead
                ],
                indent=1,
            ),
            encoding="utf-8",
        )
    if args.drop_dead:
        _drop(doc, dead)
    if args.write:
        doc["checked"] = date.today().isoformat()
        save(doc)
        print(f"Wrote {SNAPSHOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
