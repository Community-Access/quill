"""Station enrichment: what a station says about itself, searchable offline.

Jeff's todo P2 #33, the "Radio station data program" (planned in the
consolidated todo, 2026-10-11). The station catalog already knows *that* a
station exists; this package holds what makes a search for "Seahawks", "98.5",
"KIRO" or "public radio Spokane" find it -- call sign, frequency, slogan,
description, format, place, owner -- in a local SQLite store with an FTS5
index, filled only from a **signed station pack**.

The approach was learned from Jamal Mazrui's RadioTrail (DbDo, MIT licence):
enrich once, on our side, for everybody, rather than probing 60,000 streams
from every listener's computer. We port the approach, never his data.

Four pieces, all wx-free:

- :mod:`.sources` -- the pluggable source interface. Only sources whose data
  terms are settled may be registered as approved; the built-in ones read data
  the project already ships (the Community Picks catalogue and the station
  catalog seed). ``PENDING_SOURCES`` names the ones awaiting a decision.
- :mod:`.facts` -- one station's facts, call-sign and frequency parsing, and
  the field-by-field merge that keeps where each fact came from.
- :mod:`.pack` -- the pack format: build, read, and verify against the
  bundled publisher key. An unsigned or mis-signed pack is refused.
- :mod:`.store` -- the store: schema, migrations, import in one transaction,
  details, and ranked search that says why each result matched.

Design record: ``docs/design/2026-10-16-station-pack-format.md``.
"""

from quill.core.error_codes import CodedError


class EnrichmentError(CodedError):
    """The station enrichment store could not be opened, read or updated."""

    code = "QUILL-RADIO-ENRICHMENT-FAILED"


class PackRefusedError(EnrichmentError):
    """A station pack was refused: unsigned, mis-signed, damaged or malformed."""

    code = "QUILL-RADIO-ENRICHMENT-PACK-REFUSED"


__all__ = ["EnrichmentError", "PackRefusedError"]
