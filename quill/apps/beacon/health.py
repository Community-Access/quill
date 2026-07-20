"""On-demand link-health revalidation (PRD 13.4, 17.4, 44.3).

Rechecks whether each beacon's resource is still reachable and updates
``beacon.health`` to ``available`` or ``broken``. Network is opt-in: the caller
passes a ``fetcher`` (the same shape ``radio.validate_stream`` uses) and when
none is supplied no network call is made -- web URLs are reported as "not
checked" and left untouched, so the feature is safe to run offline and in tests.

Local files and folders are checked against the filesystem (not the network),
so those are always revalidated regardless of ``fetcher``.

Fail-safe throughout: a check that raises never aborts the batch; the beacon is
counted as ``broken`` and the run continues.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.apps.beacon.model import HEALTH_AVAILABLE, HEALTH_BROKEN

Fetcher = Callable[[str, int], "tuple[int, str] | None"]


def revalidate(
    store,
    *,
    fetcher: Fetcher | None = None,
    beacon_ids: list[str] | None = None,
    timeout: int = 5,
) -> dict[str, Any]:
    """Recheck reachability for the given beacons (all non-trashed by default).

    Returns a summary ``{checked, available, broken, skipped, fetcher: bool}``.
    ``skipped`` counts web URLs that were not checked because no ``fetcher`` was
    provided. Never raises.
    """
    if beacon_ids is None:
        rows = store.conn.execute("SELECT beacon_id FROM beacons WHERE trashed=0").fetchall()
        beacon_ids = [r["beacon_id"] for r in rows]

    summary = {
        "checked": 0,
        "available": 0,
        "broken": 0,
        "skipped": 0,
        "fetcher": fetcher is not None,
    }
    for bid in beacon_ids:
        b = store.get_beacon(bid)
        if b is None:
            continue
        res = store.get_resource(b.resource_id) if b.resource_id else None
        uri = res.primary_uri if res else ""
        kind = (res.type if res else "") if res else ""

        outcome = _check_one(uri, kind, fetcher=fetcher, timeout=timeout)
        if outcome == "skip":
            summary["skipped"] += 1
            continue
        summary["checked"] += 1
        new_health = HEALTH_AVAILABLE if outcome == "ok" else HEALTH_BROKEN
        if b.health != new_health:
            b.health = new_health
            store.put_beacon(b)
        if outcome == "ok":
            summary["available"] += 1
        else:
            summary["broken"] += 1
    return summary


def _check_one(uri: str, kind: str, *, fetcher: Fetcher | None, timeout: int) -> str:
    """Return 'ok', 'broken', or 'skip' for one resource.

    Local files/folders are checked against the filesystem. Web (and any other
    remote) URLs are checked only when a fetcher is supplied; otherwise 'skip'.
    """
    if not uri or not uri.strip():
        return "broken"
    if kind in ("file", "folder"):
        try:
            return "ok" if Path(uri).exists() else "broken"
        except Exception:
            return "broken"
    # Remote resource: needs a fetcher to check.
    if fetcher is None:
        return "skip"
    try:
        result = fetcher(uri, timeout)
    except Exception:
        return "broken"
    if result is None:
        return "broken"
    status, _mime = result
    try:
        return "ok" if 200 <= int(status) < 400 else "broken"
    except (TypeError, ValueError):
        return "broken"


def default_fetcher(url: str, timeout: int):
    """A real HTTP HEAD fetcher using requests, if installed.

    Returned to callers that want the network on; ``revalidate`` itself never
    imports requests, so the module loads without it.
    """
    try:
        import requests
    except ImportError as ex:  # pragma: no cover - exercised when requests absent
        raise RuntimeError("requests is not installed") from ex
    r = requests.head(url, timeout=timeout, allow_redirects=True)
    return r.status_code, r.headers.get("Content-Type", "")


def _has_requests() -> bool:
    """True if the requests library is importable (network checks available)."""
    try:
        import requests  # noqa: F401

        return True
    except ImportError:
        return False
