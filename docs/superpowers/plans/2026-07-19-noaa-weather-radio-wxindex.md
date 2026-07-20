# NOAA Weather Radio (wxindex) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace QUILL Radio's fuzzy "NOAA Weather Radio" search with the authoritative WeatherIndex (wxindex) directory, powering Browse, Search, and a Weather-menu "Your Local NOAA Weather Radio" tie-in, resilient via a bundled full-directory snapshot.

**Architecture:** A `wx`-free client (`quill/core/radio/wxindex.py`) parses wxindex JSON into `WxStation` objects and adapts them to the existing `RadioStation` model. A three-tier resolver serves data from the live API, then an app-data cache, then a bundled `quill/data/noaa_directory.json` snapshot. UI layers (Browse tree, unified search, Weather menu) consume only the resolver's domain functions.

**Tech Stack:** Python 3.12+, `urllib`+`ssl` (same egress pattern as `radio_browser.py`), the existing `RadioStation`/Browse/recorder/favorites, `pytest`.

## Global Constraints

- Target release: **QUILL Radio 2.1.1** (bump `s:\quill-radio\pyproject.toml` `version` from `2.1.0`).
- Code lives in the `quill` package (`s:\quill`); `quill_radio` inherits it as a thin wrapper — no vendoring step.
- `wx`-free, strict-typed core (match `radio_browser.py`). No `wx` import under `quill/core/`.
- Network: HTTPS-only, one reviewed egress site funneling through `quill/tools/network_egress_audit.py`, short timeout, blocked in Safe Mode via `refuse_in_safe_mode(safe_mode)` (raise before any request).
- Base URL: `https://api.wxindex.org`. No auth. Cache results; never poll in a loop.
- Adapt to `quill.core.radio.models.RadioStation` so player/recorder/favorites work unchanged; set `source="NOAA Weather Radio"`.
- TDD: every module has unit tests with a **fake fetcher** — no real network in tests. DRY, YAGNI, frequent commits.

---

### Task 1: `WxStation` model + pure JSON parsers

**Files:**
- Create: `quill/core/radio/wxindex_models.py`
- Test: `tests/unit/core/radio/test_wxindex_models.py`

**Interfaces:**
- Produces: `WxState(slug: str, name: str, station_count: int)`;
  `WxStation(callsign, frequency_mhz: float, name, state, counties: tuple[str,...], same_codes: tuple[str,...], wfo: str, latitude: float, longitude: float, feeds: tuple[str,...])`;
  `parse_states(data: object) -> list[WxState]`;
  `parse_stations(data: object) -> list[WxStation]`;
  `parse_station(data: object) -> WxStation | None`;
  `to_radio_station(s: WxStation) -> RadioStation`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/radio/test_wxindex_models.py
from quill.core.radio.wxindex_models import (
    WxStation, parse_states, parse_stations, to_radio_station,
)

_STATION_JSON = {
    "callsign": "KHB36", "frequency": "162.550", "name": "Manassas",
    "state": "VA", "wfo": "LWX", "latitude": 38.75, "longitude": -77.48,
    "counties": ["Prince William, VA"], "same": ["051153"],
    "feeds": [{"url": "https://stream.example/khb36"}],
}

def test_parse_stations_builds_wxstation():
    [s] = parse_stations([_STATION_JSON])
    assert s.callsign == "KHB36"
    assert s.frequency_mhz == 162.55
    assert s.same_codes == ("051153",)
    assert s.feeds == ("https://stream.example/khb36",)

def test_parse_states_reads_counts():
    [st] = parse_states([{"slug": "virginia", "name": "Virginia", "station_count": 42}])
    assert (st.slug, st.name, st.station_count) == ("virginia", "Virginia", 42)

def test_to_radio_station_maps_playable_fields():
    rs = to_radio_station(parse_stations([_STATION_JSON])[0])
    assert rs.stream_url == "https://stream.example/khb36"
    assert rs.source == "NOAA Weather Radio"
    assert "KHB36" in rs.name and "162.55" in rs.name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/radio/test_wxindex_models.py -v`
Expected: FAIL — `ModuleNotFoundError: quill.core.radio.wxindex_models`.

- [ ] **Step 3: Write minimal implementation**

```python
# quill/core/radio/wxindex_models.py
"""wx-free WeatherIndex (NOAA Weather Radio) domain model + JSON parsers."""
from __future__ import annotations
from dataclasses import dataclass, field
from quill.core.radio.models import RadioStation

_SOURCE = "NOAA Weather Radio"

@dataclass(slots=True, frozen=True)
class WxState:
    slug: str
    name: str
    station_count: int = 0

@dataclass(slots=True, frozen=True)
class WxStation:
    callsign: str
    frequency_mhz: float
    name: str = ""
    state: str = ""
    counties: tuple[str, ...] = ()
    same_codes: tuple[str, ...] = ()
    wfo: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    feeds: tuple[str, ...] = ()

def _f(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default

def parse_states(data: object) -> list[WxState]:
    out: list[WxState] = []
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug", "")).strip()
        if slug:
            out.append(WxState(slug, str(row.get("name", slug)),
                               int(_f(row.get("station_count"), 0))))
    return out

def _feeds(row: dict) -> tuple[str, ...]:
    urls: list[str] = []
    for feed in row.get("feeds", []) or []:
        url = str((feed or {}).get("url", "")).strip() if isinstance(feed, dict) else ""
        if url:
            urls.append(url)
    return tuple(urls)

def parse_station(data: object) -> WxStation | None:
    if not isinstance(data, dict):
        return None
    callsign = str(data.get("callsign", "")).strip()
    if not callsign:
        return None
    return WxStation(
        callsign=callsign,
        frequency_mhz=_f(data.get("frequency")),
        name=str(data.get("name", "")).strip(),
        state=str(data.get("state", "")).strip(),
        counties=tuple(str(c).strip() for c in data.get("counties", []) or [] if str(c).strip()),
        same_codes=tuple(str(c).strip() for c in data.get("same", []) or [] if str(c).strip()),
        wfo=str(data.get("wfo", "")).strip(),
        latitude=_f(data.get("latitude")),
        longitude=_f(data.get("longitude")),
        feeds=_feeds(data),
    )

def parse_stations(data: object) -> list[WxStation]:
    rows = data if isinstance(data, list) else []
    return [s for s in (parse_station(r) for r in rows) if s is not None]

def to_radio_station(s: WxStation) -> RadioStation:
    place = f" - {s.name}" if s.name else ""
    label = f"NOAA Weather Radio - {s.callsign} - {s.frequency_mhz:.2f} MHz{place}"
    return RadioStation(
        name=label,
        stream_url=s.feeds[0] if s.feeds else "",
        station_uuid=f"wxindex:{s.callsign}",
        country="United States",
        tags=("weather", "noaa"),
        source=_SOURCE,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/radio/test_wxindex_models.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add quill/core/radio/wxindex_models.py tests/unit/core/radio/test_wxindex_models.py
git commit -m "feat(radio): wxindex WxStation model + JSON parsers"
```

---

### Task 2: wxindex HTTP fetcher (reviewed egress) + Safe Mode

**Files:**
- Create: `quill/core/radio/wxindex_http.py`
- Test: `tests/unit/core/radio/test_wxindex_http.py`

**Interfaces:**
- Consumes: nothing from Task 1 (pure transport).
- Produces: `WxIndexError(RadioError-style Exception)`; `refuse_in_safe_mode(safe_mode: bool) -> None`; `http_json(path: str, *, fetcher: Fetcher | None = None) -> object` where `Fetcher = Callable[[str], str]` (returns the response body for a full URL). Real fetches go through `quill/tools/network_egress_audit.py`; tests pass a `fetcher`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/radio/test_wxindex_http.py
import pytest
from quill.core.radio.wxindex_http import http_json, refuse_in_safe_mode, WxIndexError

def test_http_json_parses_via_injected_fetcher():
    calls = []
    def fake(url: str) -> str:
        calls.append(url)
        return '{"ok": true}'
    assert http_json("/v1/states", fetcher=fake) == {"ok": True}
    assert calls == ["https://api.wxindex.org/v1/states"]

def test_refuse_in_safe_mode_raises():
    with pytest.raises(WxIndexError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise

def test_http_json_wraps_bad_json():
    with pytest.raises(WxIndexError):
        http_json("/v1/states", fetcher=lambda url: "not json")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/radio/test_wxindex_http.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# quill/core/radio/wxindex_http.py
"""The single reviewed egress site for WeatherIndex. wx-free, strict-typed."""
from __future__ import annotations
import json
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable

_BASE = "https://api.wxindex.org"
_TIMEOUT_SECONDS = 15.0
_USER_AGENT = "QUILL-Radio/2.1.1 (+https://github.com/Community-Access/quill)"

Fetcher = Callable[[str], str]

class WxIndexError(Exception):
    """A WeatherIndex request failed, was refused, or returned bad data."""

def refuse_in_safe_mode(safe_mode: bool) -> None:
    if safe_mode:
        raise WxIndexError(
            "NOAA Weather Radio is disabled in Safe Mode. "
            "Restart QUILL normally to browse or update it."
        )

def _default_fetch(url: str) -> str:
    # NETWORK-EGRESS: reviewed site (see quill/tools/network_egress_audit.py).
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise WxIndexError(f"Could not reach the NOAA Weather Radio directory: {error}") from error

def http_json(path: str, *, fetcher: Fetcher | None = None) -> object:
    fetch = fetcher or _default_fetch
    body = fetch(f"{_BASE}{path}")
    try:
        return json.loads(body) if body else []
    except ValueError as error:
        raise WxIndexError("The NOAA Weather Radio directory returned an unreadable reply.") from error
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/radio/test_wxindex_http.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Add the egress site to the audit allowlist and commit**

Add `wxindex_http._default_fetch` to the reviewed-egress registry the same way `radio_browser._http_json` is listed (see `quill/tools/network_egress_audit.py`; run its test to confirm no violation).

```bash
git add quill/core/radio/wxindex_http.py tests/unit/core/radio/test_wxindex_http.py quill/tools/network_egress_audit.py
git commit -m "feat(radio): wxindex reviewed egress fetcher + Safe Mode"
```

---

### Task 3: Bundled snapshot loader + `scripts/snapshot_wxindex.py`

**Files:**
- Create: `quill/core/radio/wxindex_snapshot.py`
- Create: `quill/data/noaa_directory.json` (real snapshot, generated by the script)
- Create: `scripts/snapshot_wxindex.py`
- Test: `tests/unit/core/radio/test_wxindex_snapshot.py`

**Interfaces:**
- Consumes: `parse_states`, `parse_stations` (Task 1).
- Produces: `load_snapshot() -> Snapshot` where
  `Snapshot(generated_at: str, states: list[WxState], stations: list[WxStation])`;
  `snapshot_path() -> Path`. Missing/corrupt snapshot -> empty `Snapshot`, logged, never raises.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/radio/test_wxindex_snapshot.py
import json
from quill.core.radio import wxindex_snapshot as snap

def test_load_snapshot_reads_states_and_stations(tmp_path, monkeypatch):
    doc = {"generated_at": "2026-07-19T00:00:00Z",
           "states": [{"slug": "virginia", "name": "Virginia", "station_count": 1}],
           "stations": [{"callsign": "KHB36", "frequency": "162.550",
                         "feeds": [{"url": "https://s/khb36"}]}]}
    path = tmp_path / "noaa_directory.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(snap, "snapshot_path", lambda: path)
    s = snap.load_snapshot()
    assert s.states[0].slug == "virginia"
    assert s.stations[0].callsign == "KHB36"

def test_load_snapshot_missing_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(snap, "snapshot_path", lambda: tmp_path / "nope.json")
    s = snap.load_snapshot()
    assert s.states == [] and s.stations == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/radio/test_wxindex_snapshot.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# quill/core/radio/wxindex_snapshot.py
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from quill.core.radio.wxindex_models import WxState, WxStation, parse_states, parse_stations

_LOG = logging.getLogger(__name__)

@dataclass(slots=True)
class Snapshot:
    generated_at: str = ""
    states: list[WxState] = field(default_factory=list)
    stations: list[WxStation] = field(default_factory=list)

def snapshot_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "noaa_directory.json"

def load_snapshot() -> Snapshot:
    path = snapshot_path()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        _LOG.warning("NOAA directory snapshot unavailable (%s): %s", path, error)
        return Snapshot()
    if not isinstance(doc, dict):
        return Snapshot()
    return Snapshot(
        generated_at=str(doc.get("generated_at", "")),
        states=parse_states(doc.get("states", [])),
        stations=parse_stations(doc.get("stations", [])),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/radio/test_wxindex_snapshot.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Write the snapshot generator and produce the real snapshot**

```python
# scripts/snapshot_wxindex.py
"""Fetch the full WeatherIndex directory into quill/data/noaa_directory.json."""
from __future__ import annotations
import json
from datetime import UTC, datetime
from pathlib import Path
from quill.core.radio.wxindex_http import http_json
from quill.core.radio.wxindex_snapshot import snapshot_path

def main() -> int:
    states = http_json("/v1/states")
    stations = http_json("/v1/stations/all-known")
    doc = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "states": states if isinstance(states, list) else [],
        "stations": stations if isinstance(stations, list) else [],
    }
    out = snapshot_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {out} ({len(doc['stations'])} stations, {len(doc['states'])} states)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `python scripts/snapshot_wxindex.py` (real network; commits the data file).

- [ ] **Step 6: Commit**

```bash
git add quill/core/radio/wxindex_snapshot.py scripts/snapshot_wxindex.py quill/data/noaa_directory.json tests/unit/core/radio/test_wxindex_snapshot.py
git commit -m "feat(radio): bundled NOAA directory snapshot + generator"
```

---

### Task 4: Three-tier resolver (live -> cache -> snapshot) + manual refresh

**Files:**
- Create: `quill/core/radio/wxindex.py` (the public facade)
- Test: `tests/unit/core/radio/test_wxindex_resolver.py`

**Interfaces:**
- Consumes: `http_json`, `refuse_in_safe_mode` (Task 2); `load_snapshot` (Task 3); parsers (Task 1).
- Produces: `list_states(*, safe_mode=False, fetcher=None) -> list[WxState]`;
  `stations_for_state(slug, *, safe_mode=False, fetcher=None) -> list[WxStation]`;
  `refresh_directory(*, safe_mode=False, fetcher=None) -> RefreshResult` (writes cache atomically);
  `RefreshResult(station_count: int, state_count: int, generated_at: str)`;
  internal `_cache_dir() -> Path` under `app_data_dir()/radio/wxindex-cache`.
  Resolution order for reads: fresh cache (< max_age) -> live (then write cache) -> stale cache -> snapshot.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/radio/test_wxindex_resolver.py
import json
import pytest
from quill.core.radio import wxindex

def _fetcher(mapping):
    return lambda url: mapping[url]

def test_stations_for_state_uses_live_then_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    body = json.dumps([{"callsign": "KHB36", "frequency": "162.550",
                        "feeds": [{"url": "https://s/khb36"}]}])
    f = _fetcher({"https://api.wxindex.org/v1/states/virginia/stations": body})
    got = wxindex.stations_for_state("virginia", fetcher=f)
    assert got[0].callsign == "KHB36"
    assert (tmp_path / "state-virginia.json").is_file()  # cached

def test_stations_for_state_falls_back_to_cache_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    (tmp_path / "state-virginia.json").write_text(
        json.dumps([{"callsign": "KZZ99", "frequency": "162.400", "feeds": []}]),
        encoding="utf-8")
    def boom(url): raise wxindex.WxIndexError("down")
    got = wxindex.stations_for_state("virginia", fetcher=boom, max_age_seconds=0)
    assert got[0].callsign == "KZZ99"  # served stale cache, no raise

def test_refresh_directory_writes_cache_and_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    f = _fetcher({
        "https://api.wxindex.org/v1/states": json.dumps([{"slug": "virginia", "name": "Virginia"}]),
        "https://api.wxindex.org/v1/stations/all-known":
            json.dumps([{"callsign": "KHB36", "frequency": "162.550", "feeds": []}]),
    })
    res = wxindex.refresh_directory(fetcher=f)
    assert res.station_count == 1 and res.state_count == 1
    assert (tmp_path / "directory.json").is_file()

def test_safe_mode_refuses_live(tmp_path, monkeypatch):
    monkeypatch.setattr(wxindex, "_cache_dir", lambda: tmp_path)
    with pytest.raises(wxindex.WxIndexError):
        wxindex.refresh_directory(safe_mode=True, fetcher=lambda url: "[]")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/radio/test_wxindex_resolver.py -v`
Expected: FAIL — `wxindex` facade missing / attributes undefined.

- [ ] **Step 3: Write minimal implementation**

```python
# quill/core/radio/wxindex.py
"""Public NOAA Weather Radio facade: three-tier resolver over WeatherIndex."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass
from pathlib import Path
from quill.core.paths import app_data_dir
from quill.core.radio.wxindex_http import Fetcher, WxIndexError, http_json, refuse_in_safe_mode
from quill.core.radio.wxindex_models import (
    WxState, WxStation, parse_states, parse_stations,
)
from quill.core.radio.wxindex_snapshot import load_snapshot

_DEFAULT_MAX_AGE = 7 * 24 * 3600  # 7 days

@dataclass(slots=True, frozen=True)
class RefreshResult:
    station_count: int
    state_count: int
    generated_at: str

def _cache_dir() -> Path:
    path = app_data_dir() / "radio" / "wxindex-cache"
    path.mkdir(parents=True, exist_ok=True)
    return path

def _read_cache(name: str, max_age_seconds: float) -> object | None:
    path = _cache_dir() / name
    try:
        if max_age_seconds >= 0 and (time.time() - path.stat().st_mtime) > max_age_seconds:
            # too old to be "fresh", but callers may still fall back to it
            return {"_stale": json.loads(path.read_text("utf-8"))}
        return {"_fresh": json.loads(path.read_text("utf-8"))}
    except (OSError, ValueError):
        return None

def _write_cache(name: str, data: object) -> None:
    path = _cache_dir() / name
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)

def _live_or_cache(path: str, cache_name: str, *, safe_mode: bool,
                   fetcher: Fetcher | None, max_age_seconds: float) -> object:
    cached = _read_cache(cache_name, max_age_seconds)
    if cached and "_fresh" in cached:
        return cached["_fresh"]
    try:
        refuse_in_safe_mode(safe_mode)
        data = http_json(path, fetcher=fetcher)
        _write_cache(cache_name, data)
        return data
    except WxIndexError:
        if cached and "_stale" in cached:
            return cached["_stale"]
        raise

def list_states(*, safe_mode: bool = False, fetcher: Fetcher | None = None,
                max_age_seconds: float = _DEFAULT_MAX_AGE) -> list[WxState]:
    try:
        return parse_states(_live_or_cache("/v1/states", "states.json",
                            safe_mode=safe_mode, fetcher=fetcher, max_age_seconds=max_age_seconds))
    except WxIndexError:
        return load_snapshot().states

def stations_for_state(slug: str, *, safe_mode: bool = False, fetcher: Fetcher | None = None,
                       max_age_seconds: float = _DEFAULT_MAX_AGE) -> list[WxStation]:
    try:
        return parse_stations(_live_or_cache(
            f"/v1/states/{slug}/stations", f"state-{slug}.json",
            safe_mode=safe_mode, fetcher=fetcher, max_age_seconds=max_age_seconds))
    except WxIndexError:
        return [s for s in load_snapshot().stations if s.state.lower() == slug[:2].lower()]

def refresh_directory(*, safe_mode: bool = False, fetcher: Fetcher | None = None) -> RefreshResult:
    refuse_in_safe_mode(safe_mode)
    states = http_json("/v1/states", fetcher=fetcher)
    stations = http_json("/v1/stations/all-known", fetcher=fetcher)
    _write_cache("states.json", states)
    doc = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "states": states, "stations": stations}
    _write_cache("directory.json", doc)
    return RefreshResult(
        station_count=len(stations) if isinstance(stations, list) else 0,
        state_count=len(states) if isinstance(states, list) else 0,
        generated_at=doc["generated_at"],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/radio/test_wxindex_resolver.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add quill/core/radio/wxindex.py tests/unit/core/radio/test_wxindex_resolver.py
git commit -m "feat(radio): three-tier wxindex resolver + manual refresh"
```

---

### Task 5: Search routing (SAME / callsign / county) + `local_stations`

**Files:**
- Modify: `quill/core/radio/wxindex.py` (add `search_stations`, `station_detail`, `local_stations`)
- Test: `tests/unit/core/radio/test_wxindex_search.py`

**Interfaces:**
- Produces: `search_stations(query: str, *, safe_mode=False, fetcher=None) -> list[WxStation]` — routes a 6-digit SAME code to `?same=`, a callsign (`^[A-Z]{3}\d{2,3}$`) to `/v1/stations/{callsign}`, `"County, ST"`/state text to `?c=`/`?s=`; empty for non-matching free text. `station_detail(callsign, ...) -> WxStation | None`. `local_stations(lat, lon, *, county="", safe_mode=False, fetcher=None) -> list[WxStation]` — county/SAME match first, else nearest-by-coordinate over the snapshot.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/radio/test_wxindex_search.py
import json
from quill.core.radio import wxindex

def test_search_routes_same_code():
    seen = {}
    def f(url):
        seen["url"] = url
        return json.dumps([{"callsign": "KHB36", "frequency": "162.550", "feeds": []}])
    out = wxindex.search_stations("051153", fetcher=f)
    assert "same=051153" in seen["url"] and out[0].callsign == "KHB36"

def test_search_routes_callsign():
    seen = {}
    def f(url):
        seen["url"] = url
        return json.dumps({"callsign": "KHB36", "frequency": "162.550", "feeds": []})
    out = wxindex.search_stations("KHB36", fetcher=f)
    assert "/v1/stations/KHB36" in seen["url"] and out[0].callsign == "KHB36"

def test_local_stations_nearest_by_coordinate(monkeypatch):
    from quill.core.radio import wxindex_snapshot as snap
    from quill.core.radio.wxindex_models import WxStation
    monkeypatch.setattr(wxindex, "load_snapshot", lambda: snap.Snapshot(
        stations=[WxStation("A", 162.4, latitude=38.0, longitude=-77.0),
                  WxStation("B", 162.5, latitude=48.0, longitude=-100.0)]))
    got = wxindex.local_stations(38.1, -77.1)  # no network; snapshot fallback
    assert got[0].callsign == "A"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/radio/test_wxindex_search.py -v`
Expected: FAIL — `search_stations`/`local_stations` undefined.

- [ ] **Step 3: Write minimal implementation** (append to `quill/core/radio/wxindex.py`)

```python
import math
import re
from urllib.parse import quote

_SAME = re.compile(r"^\d{6}$")
_CALLSIGN = re.compile(r"^[A-Z]{2,3}\d{2,3}$", re.IGNORECASE)

def station_detail(callsign: str, *, safe_mode: bool = False, fetcher: Fetcher | None = None) -> WxStation | None:
    from quill.core.radio.wxindex_models import parse_station
    try:
        refuse_in_safe_mode(safe_mode)
        return parse_station(http_json(f"/v1/stations/{quote(callsign)}", fetcher=fetcher))
    except WxIndexError:
        for s in load_snapshot().stations:
            if s.callsign.lower() == callsign.lower():
                return s
        return None

def search_stations(query: str, *, safe_mode: bool = False, fetcher: Fetcher | None = None) -> list[WxStation]:
    q = query.strip()
    if not q:
        return []
    try:
        refuse_in_safe_mode(safe_mode)
        if _SAME.match(q):
            return parse_stations(http_json(f"/v1/station_search?same={quote(q)}", fetcher=fetcher))
        if _CALLSIGN.match(q):
            s = station_detail(q, safe_mode=safe_mode, fetcher=fetcher)
            return [s] if s else []
        if "," in q:  # "County, ST"
            county, _, st = q.partition(",")
            return parse_stations(http_json(
                f"/v1/station_search?c={quote(county.strip())}&s={quote(st.strip())}", fetcher=fetcher))
        return parse_stations(http_json(f"/v1/station_search?s={quote(q)}", fetcher=fetcher))
    except WxIndexError:
        ql = q.lower()
        return [s for s in load_snapshot().stations
                if ql in s.callsign.lower() or ql in s.state.lower()
                or any(ql in c.lower() for c in s.counties) or q in s.same_codes]

def local_stations(latitude: float, longitude: float, *, county: str = "",
                   safe_mode: bool = False, fetcher: Fetcher | None = None) -> list[WxStation]:
    if county:
        hits = search_stations(county, safe_mode=safe_mode, fetcher=fetcher)
        if hits:
            return hits
    stations = load_snapshot().stations
    def dist(s: WxStation) -> float:
        return math.hypot(s.latitude - latitude, s.longitude - longitude)
    return sorted((s for s in stations if s.latitude or s.longitude), key=dist)[:5]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/radio/test_wxindex_search.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add quill/core/radio/wxindex.py tests/unit/core/radio/test_wxindex_search.py
git commit -m "feat(radio): wxindex search routing + local-station resolution"
```

---

### Task 6: Browse tree — replace the "Weather / NOAA" source

**Files:**
- Modify: `quill/ui/radio/browse_tree_dialog.py` (the `"weather"` loader + expansion to State -> Station)
- Modify: `quill/core/radio/radio_browser.py` (remove the now-unused `noaa_weather_stations`)
- Test: `tests/unit/ui/test_browse_tree_weather_noaa.py`

**Interfaces:**
- Consumes: `wxindex.list_states`, `wxindex.stations_for_state`, `wxindex_models.to_radio_station`.
- Produces: the Browse "Weather / NOAA" branch expands to states (genre-like folders); each state expands to `RadioStation` leaves. Reuses the dialog's existing lazy `genres`/`genre` machinery — add a source kind `("Weather / NOAA", "wx_states", None)` and a `wx_state` child kind.

- [ ] **Step 1: Write the failing characterization test**

```python
# tests/unit/ui/test_browse_tree_weather_noaa.py
from quill.core.radio import wxindex
from quill.core.radio.wxindex_models import WxState, WxStation

def test_weather_noaa_states_then_stations(monkeypatch):
    monkeypatch.setattr(wxindex, "list_states", lambda **k: [WxState("virginia", "Virginia", 1)])
    monkeypatch.setattr(wxindex, "stations_for_state",
                        lambda slug, **k: [WxStation("KHB36", 162.55, feeds=("https://s/k",))])
    from quill.ui.radio.browse_tree_dialog import wx_state_folders, wx_state_stations
    states = wx_state_folders(safe_mode=False)
    assert states[0].name == "Virginia" and states[0].payload == "virginia"
    stations = wx_state_stations("virginia", safe_mode=False)
    assert stations[0].source == "NOAA Weather Radio"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/ui/test_browse_tree_weather_noaa.py -v`
Expected: FAIL — helpers `wx_state_folders`/`wx_state_stations` missing.

- [ ] **Step 3: Implement the helpers and wire the source**

In `quill/ui/radio/browse_tree_dialog.py`: add module-level helpers used by the loaders, replace the `_SOURCES` `("Weather / NOAA", "stations", "weather")` entry with `("Weather / NOAA", "wx_states", None)`, add `"wx_states"`/`"wx_state"` to `_EXPANDABLE`, and handle them in `_fetch_children`.

```python
# module-level, near _STATION_LOADERS:
from quill.core.radio import wxindex
from quill.core.radio.wxindex_models import to_radio_station

class _Folder:  # if the dialog has an existing genre-folder type, reuse it instead
    __slots__ = ("name", "kind", "payload")
    def __init__(self, name, kind, payload):
        self.name, self.kind, self.payload = name, kind, payload

def wx_state_folders(*, safe_mode: bool) -> list[_Folder]:
    return [_Folder(f"{s.name} ({s.station_count})", "wx_state", s.slug)
            for s in wxindex.list_states(safe_mode=safe_mode)]

def wx_state_stations(slug: str, *, safe_mode: bool):
    return [to_radio_station(s) for s in wxindex.stations_for_state(slug, safe_mode=safe_mode)]
```

In `_fetch_children`, add:

```python
if kind == "wx_states":
    return wx_state_folders(safe_mode=self._safe_mode)
if kind == "wx_state":
    return wx_state_stations(payload, safe_mode=self._safe_mode)
```

Then delete `noaa_weather_stations` from `radio_browser.py` and its `_STATION_LOADERS["weather"]` entry.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/ui/test_browse_tree_weather_noaa.py tests/unit/core/radio/ -v`
Expected: PASS. Also run `pytest -q -k "browse or radio_browser"` to catch removed-symbol fallout.

- [ ] **Step 5: Commit**

```bash
git add quill/ui/radio/browse_tree_dialog.py quill/core/radio/radio_browser.py tests/unit/ui/test_browse_tree_weather_noaa.py
git commit -m "feat(radio): Browse Weather/NOAA -> authoritative wxindex state tree"
```

---

### Task 7: Unified Search — blend NOAA results

**Files:**
- Modify: the unified search entry point (`quill/core/radio/directory_search.py` — confirm the aggregator function that fans out to sources)
- Test: `tests/unit/core/radio/test_directory_search_noaa.py`

**Interfaces:**
- Consumes: `wxindex.search_stations`, `to_radio_station`.
- Produces: NOAA stations appear in unified search results (as `RadioStation` with `source="NOAA Weather Radio"`) when the query is a SAME code, callsign, or "County, ST"/state; free-text queries still hit the other sources unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/radio/test_directory_search_noaa.py
from quill.core.radio import wxindex, directory_search
from quill.core.radio.wxindex_models import WxStation

def test_same_code_query_includes_noaa(monkeypatch):
    monkeypatch.setattr(wxindex, "search_stations",
        lambda q, **k: [WxStation("KHB36", 162.55, feeds=("https://s/k",))])
    results = directory_search.search("051153", safe_mode=False)
    assert any(r.source == "NOAA Weather Radio" for r in results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/radio/test_directory_search_noaa.py -v`
Expected: FAIL — NOAA not in results.

- [ ] **Step 3: Add the NOAA branch to the aggregator**

In `directory_search.search(...)`, after the existing sources, append:

```python
from quill.core.radio import wxindex
from quill.core.radio.wxindex_models import to_radio_station
results.extend(to_radio_station(s)
               for s in wxindex.search_stations(query, safe_mode=safe_mode))
```

(Match the module's actual result-accumulation style; keep NOAA additive and de-duped by `station_uuid` if the aggregator already de-dupes.)

- [ ] **Step 4: Run test** — Expected: PASS. Also `pytest -q -k directory_search`.

- [ ] **Step 5: Commit**

```bash
git add quill/core/radio/directory_search.py tests/unit/core/radio/test_directory_search_noaa.py
git commit -m "feat(radio): blend authoritative NOAA results into unified search"
```

---

### Task 8: Weather menu — "Your Local NOAA Weather Radio" + "Update directory"

**Files:**
- Modify: `quill/ui/main_frame_weather.py` (two menu items + handlers)
- Modify: the play path to accept a `RadioStation` (reuse the existing "play this station" call the Browse dialog uses)
- Test: `tests/unit/ui/test_weather_noaa_menu.py`

**Interfaces:**
- Consumes: `wxindex.local_stations`, `wxindex.refresh_directory`, `to_radio_station`; the Weather feature's saved location (lat/lon + county from `quill/core/weather/locations.py` / `geocoding.py`); the existing play-a-`RadioStation` entry point.
- Produces: menu command "Listen to your local NOAA Weather Radio" (resolves via `local_stations`, plays the first, offers pin-to-Favorites); menu command "Update NOAA Weather Radio directory" (off-thread `refresh_directory`, announces `RefreshResult` counts + `generated_at`, Safe-Mode aware). No-location case prompts to set one / pick a state.

- [ ] **Step 1: Write the failing test (core resolution used by the handler)**

```python
# tests/unit/ui/test_weather_noaa_menu.py
from quill.ui import main_frame_weather as mfw
from quill.core.radio.wxindex_models import WxStation

def test_local_noaa_station_for_location(monkeypatch):
    monkeypatch.setattr(mfw.wxindex, "local_stations",
        lambda lat, lon, county="", **k: [WxStation("KHB36", 162.55, feeds=("https://s/k",))])
    rs = mfw.local_noaa_radio_station(latitude=38.75, longitude=-77.48, county="Prince William, VA")
    assert rs is not None and rs.source == "NOAA Weather Radio"

def test_local_noaa_none_when_no_stations(monkeypatch):
    monkeypatch.setattr(mfw.wxindex, "local_stations", lambda *a, **k: [])
    assert mfw.local_noaa_radio_station(latitude=0.0, longitude=0.0) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/ui/test_weather_noaa_menu.py -v`
Expected: FAIL — `local_noaa_radio_station` missing.

- [ ] **Step 3: Implement the pure resolver + wire the menu**

Add to `quill/ui/main_frame_weather.py`:

```python
from quill.core.radio import wxindex
from quill.core.radio.wxindex_models import to_radio_station
from quill.core.radio.models import RadioStation

def local_noaa_radio_station(*, latitude: float, longitude: float, county: str = "",
                             safe_mode: bool = False) -> RadioStation | None:
    stations = wxindex.local_stations(latitude, longitude, county=county, safe_mode=safe_mode)
    return to_radio_station(stations[0]) if stations else None
```

Add two `wx` menu items to the Weather menu with handlers that (a) read the saved Weather location, call `local_noaa_radio_station`, and route the result into the existing "play this station" path (offering pin-to-Favorites); and (b) run `wxindex.refresh_directory` on the existing background-task helper, then announce `RefreshResult`. Both use `self._safe_mode`. If no location is set, prompt to set one or open Browse's Weather/NOAA branch. Match the file's existing menu-append + `wx.CallAfter` announce patterns.

- [ ] **Step 4: Run tests** — Expected: PASS. Also `pytest -q -k "weather and (menu or noaa)"`.

- [ ] **Step 5: Commit**

```bash
git add quill/ui/main_frame_weather.py tests/unit/ui/test_weather_noaa_menu.py
git commit -m "feat(radio): Weather menu local NOAA Weather Radio + directory update"
```

---

### Task 9: Release 2.1.1 — version, changelog, docs

**Files:**
- Modify: `s:\quill-radio\pyproject.toml` (`version = "2.1.1"`)
- Modify: `s:\quill-radio\CHANGELOG.md` (and QUILL's changelog if radio changes are listed there)
- Modify: the Radio user guide section on Browse/Weather (docs source used by `render_docs.ps1`)

**Interfaces:** none (release metadata + docs).

- [ ] **Step 1: Bump the version**

Set `version = "2.1.1"` in `s:\quill-radio\pyproject.toml`.

- [ ] **Step 2: Changelog + user guide**

Add a 2.1.1 entry: "NOAA Weather Radio is now the authoritative WeatherIndex directory — browse by state, search by SAME code/callsign/county, listen to your local transmitter from the Weather menu, and update the directory on demand. Works offline from a bundled snapshot." Update the Browse/Weather user-guide section accordingly.

- [ ] **Step 3: Full test sweep**

Run: `pytest -q -p no:cacheprovider tests/unit/core/radio tests/unit/ui -k "wxindex or noaa or browse or weather"`
Expected: PASS. Then the standard gates: `ruff format --check .`, `ruff check .`, `mypy quill/core quill/io`, `python -m quill.tools.check_banned_patterns`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(radio): release 2.1.1 -- NOAA Weather Radio via wxindex"
```

---

## Self-Review

- **Spec coverage:** data+resilience layer (Tasks 1-4); snapshot script (Task 3); Browse replacement (Task 6); authoritative search (Tasks 5, 7); Weather-menu local + refresh (Tasks 4, 8); full experience — favorites/record reuse `RadioStation` (Task 1 adapter); user-facing refresh (Tasks 4, 8). All spec sections map to a task.
- **Placeholder scan:** UI Tasks 6-8 intentionally reference "match the file's existing patterns" for the surrounding menu/tree wiring the implementer will read; every new function has complete code and a failing test. No TBD/TODO left.
- **Type consistency:** `WxStation`/`WxState`/`RefreshResult`/`Fetcher` names and signatures are consistent across tasks; `to_radio_station` returns `RadioStation`; resolver functions accept `fetcher=`/`safe_mode=` uniformly.

## Notes for the implementer

- Confirm the exact reviewed-egress registration mechanism in `quill/tools/network_egress_audit.py` (Task 2 Step 5) — it is an AST/source scan gate; the new `_default_fetch` must be listed like `radio_browser._http_json`.
- Confirm `directory_search`'s real aggregator function name/shape before Task 7 (the plan assumes a `search(query, *, safe_mode)` that accumulates `RadioStation`s).
- The Browse dialog may already have a genre-folder type; reuse it instead of the illustrative `_Folder` in Task 6.

---

# Part 2 — Radio Reading Services (also 2.1.1)

**Goal:** Add a "Radio Reading Services" category (audio information services for the print-disabled) to Browse and unified Search, powered by the real reading-service stations already in Radio Browser, with a bundled snapshot floor and an in-Radio refresh. Reuses the existing `radio_browser` client and `RadioStation`.

**Global constraints (Part 2):** same as Part 1, plus: these are public Radio Browser streams; `source="Radio Reading Service"`; only list stations with a non-empty `stream_url`. The curated seed list (21 vetted, health-OK services) is at `<scratch>/rrs/reading_services_curated.json` (WKAR RRS, KPBS RRS, CRIS/Chicago Lighthouse, WUFT RRS, Sun Sounds of Arizona, WRBH Reading Radio, ACB Media 1–5, NFBRN, Voice Corps, Owl Radio, Recording Library of West Texas, Audible Local Ledger, Down East RRS, Connecticut Radio Information System, 95alive). Clean it: replace mangled `�` in ACB names with `-`, and dedupe `95alive` to one entry.

### Task 10: Bundled reading-services snapshot + loader

**Files:** Create `quill/data/reading_services.json`; Create `quill/core/radio/reading_services.py`; Test `tests/unit/core/radio/test_reading_services.py`.

**Interfaces:** Produces `load_reading_services() -> list[RadioStation]` (each `source="Radio Reading Service"`); `reading_services_path() -> Path`. Missing/corrupt -> `[]`, logged, never raises.

- [ ] Step 1 — failing test: monkeypatch `reading_services_path` to a tmp json with one service `{"name":"WRBH","stream_url":"https://s/wrbh","state":"Louisiana"}`; assert `load_reading_services()[0].source == "Radio Reading Service"` and `stream_url` set; and missing-file -> `[]`.
- [ ] Step 2 — run, confirm fail (module missing).
- [ ] Step 3 — implement: read `<scratch>/rrs/reading_services_curated.json`, clean per Global Constraints, write it to `quill/data/reading_services.json` as `{"generated_at": "...", "services": [ {name, stream_url, state, station_uuid, homepage, codec}, ... ]}`. Loader parses each into `RadioStation(name=..., stream_url=..., station_uuid=svc.get("station_uuid",""), country="United States", tags=("reading service","blind"), source="Radio Reading Service")`, skipping entries with empty `stream_url`/`name`. Corrupt/missing -> `[]` with `_LOG.warning`.
- [ ] Step 4 — run, pass.
- [ ] Step 5 — gates (`pytest`, `mypy quill/core`, ruff) then commit `feat(radio): bundled Radio Reading Services snapshot + loader`.

### Task 11: RRS resolver + live Radio Browser refresh

**Files:** Modify `quill/core/radio/reading_services.py`; Test `tests/unit/core/radio/test_reading_services_resolver.py`.

**Interfaces:** Produces `list_reading_services(*, safe_mode=False, searcher=None) -> list[RadioStation]` (cache -> live -> bundled snapshot); `refresh_reading_services(*, safe_mode=False, searcher=None) -> RrsRefreshResult(count, generated_at)`. `searcher` seam defaults to `radio_browser.search_stations`; live path queries the reading-service keywords ("radio reading", "reading service", "audio information", "reading radio", "blind radio"), keeps stations whose name/tags match a reading-service term AND have a `stream_url`, de-dupes by `stream_url`, writes the app-data cache (`app_data_dir()/radio/reading-services-cache/`); Safe-Mode refuses live and falls to cache/snapshot. Mirror the wxindex three-tier resolver (`quill/core/radio/wxindex.py`).

- [ ] Step 1 — failing test: inject a fake `searcher` returning two RadioBrowser `RadioStation`s (one matching "reading service", one unrelated); assert `list_reading_services` includes the reading-service one with `source` re-stamped and excludes the unrelated one; assert `refresh_reading_services` writes the cache and returns a `RrsRefreshResult` with the right count; assert Safe Mode refuses the live path and returns the bundled snapshot.
- [ ] Step 2 — run, confirm fail.
- [ ] Step 3 — implement mirroring `wxindex.py`'s cache tier + `radio_browser.refuse_in_safe_mode`. Reuse `radio_browser.search_stations(keyword, safe_mode=...)` per keyword via the `searcher` seam; re-stamp `source="Radio Reading Service"`.
- [ ] Step 4 — run, pass.
- [ ] Step 5 — gates + commit `feat(radio): Radio Reading Services resolver + Radio Browser refresh`.

### Task 12: Browse category + unified-search blend

**Files:** Modify `quill/ui/radio/browse_tree_dialog.py` (add source); Modify `quill/core/radio/directory_search.py` + `quill/ui/radio/station_browser_dialog.py` (search blend); Test `tests/unit/ui/test_reading_services_browse_search.py`.

**Interfaces:** Browse "Radio Reading Services" source loads `list_reading_services` as a flat station list (reuse the existing `"stations"` kind + a `_STATION_LOADERS["reading_services"]` entry — 21 services, no tree needed). Search: add `reading_services_search_stations(query, *, safe_mode=False) -> list[RadioStation]` to `directory_search.py` (case-insensitive name/tag/state match over `list_reading_services`, playable-only) and wire it into `station_browser_dialog._do_search`'s `extras` exactly like Task 7's `wxindex_search_stations`.

- [ ] Step 1 — failing test: `_STATION_LOADERS["reading_services"]` returns `list_reading_services` output (monkeypatched); `reading_services_search_stations("wrbh")` returns the WRBH station with `source=="Radio Reading Service"`; empty query -> `[]`.
- [ ] Step 2 — run, confirm fail.
- [ ] Step 3 — implement: add `("Radio Reading Services", "stations", "reading_services")` to `_SOURCES`; `_STATION_LOADERS["reading_services"] = lambda safe: reading_services.list_reading_services(safe_mode=safe)`. Add the search helper and wire into `_do_search` `extras` (mirror Task 7's committed `wxindex_search_stations` wiring).
- [ ] Step 4 — run, pass; `pytest -q -k "browse or directory_search or station_browser"`.
- [ ] Step 5 — gates (incl. `check_banned_patterns`) + commit `feat(radio): Radio Reading Services in Browse and Search`.

### Task 13: "Update Radio Reading Services" refresh command

**Files:** Modify the Radio menu builder (find it: grep for where the Radio/Stations menu items are appended — likely `quill/ui/main_frame_radio.py` or `quill/apps/radio.py`); Test `tests/unit/ui/test_reading_services_update.py`.

**Interfaces:** A menu command "Update Radio Reading Services" that runs `reading_services.refresh_reading_services(safe_mode=self._safe_mode)` on the host background-task helper (`self._task_manager`), announces the `RrsRefreshResult` count via `self._announce`, Safe-Mode guarded, `self._show_message_box` on any user-facing message (no raw `wx.MessageBox`). Mirror the wxindex Weather-menu "Update NOAA Weather Radio directory" handler committed in Task 8 (`quill/ui/main_frame_weather.py::update_noaa_radio_directory`).

- [ ] Step 1 — failing test: a pure helper `refresh_reading_services_summary() -> str` (or the resolver call) returns a message containing the count when `refresh_reading_services` is monkeypatched. (Menu wiring itself is wx-bound; test the pure part.)
- [ ] Step 2 — run, confirm fail.
- [ ] Step 3 — implement the menu item + handler mirroring `update_noaa_radio_directory`.
- [ ] Step 4 — run, pass; `pytest -q -k radio`.
- [ ] Step 5 — gates + commit `feat(radio): 'Update Radio Reading Services' refresh command`.

### Task 14: Combined 2.1.1 release (wxindex + RRS)

**Files:** Modify `s:\quill-radio\pyproject.toml` (`version = "2.1.1"`); Modify `s:\quill-radio\CHANGELOG.md`; Modify the Radio user guide.

- [ ] Step 1 — bump `version = "2.1.1"`.
- [ ] Step 2 — changelog 2.1.1 entry covering BOTH: "NOAA Weather Radio is now the authoritative WeatherIndex directory (browse by state, search by SAME code/callsign/county, your local transmitter from the Weather menu, on-demand update, works offline). New Radio Reading Services category — audio information services for print-disabled listeners — in Browse and Search, with an on-demand update. Both ship a bundled snapshot so they work offline." Update the user guide Browse/Weather sections.
- [ ] Step 3 — full sweep: `pytest -q tests/unit/core/radio tests/unit/ui -k "wxindex or noaa or reading or browse or weather or directory_search"`; then `ruff format --check .`, `ruff check .`, `mypy quill/core quill/io`, `python -m quill.tools.check_banned_patterns`, and the error-code audit.
- [ ] Step 4 — commit `chore(radio): release 2.1.1 — NOAA Weather Radio + Radio Reading Services`.
