"""Fetch the full WeatherIndex directory into quill/data/noaa_directory.json."""

from __future__ import annotations

import json
from datetime import UTC, datetime

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
