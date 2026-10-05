"""Subscriptions and folders through Listening Places (ear.md B3; sync.md 6.7).

Positions answer "where am I"; this answers "what am I following". It follows
the shared proposal's section 6.7 exactly, because the whole value of the
format is that two apps agree on it -- nothing here is a Cast-only shape:

* **Identity.** ``sub:`` plus the first 16 hex characters of the SHA-256 of the
  canonical feed URL (scheme and host lower-cased, default port, fragment and
  trailing slash removed, path case and query kept). Two records whose
  ``alt_urls`` meet are the same subscription. Titles are never compared.
* **Same folder, same device file, same last-write-wins merge.** These rows go
  into this device's ``listening-places/1`` file beside the place rows.
* **Its own switch, off by default.** A plain file lists what somebody
  follows, readably, to anybody who can see the folder.
* **Private feeds never go into the plain file** -- a feed with a sign-in, or a
  token in its address. They are counted and said, never written.
* **Unsubscribing removes the subscription only**, never episodes, downloads
  or history; it is always named ("Stopped following X, removed on Studio
  PC"); and a tombstone older than when this device started following is
  ignored, so a deliberate resubscribe is not undone.
* **Carry what you cannot use.** A record's fields Cast does not understand
  (Earshot's extra folder memberships, its ``app_private`` bag, a folder's
  ``sortOrder``) are kept and written back untouched.
* **Only ``prefs.speed`` syncs** among per-show settings.

Folders: Cast nests and files a podcast in one folder; Earshot is flat and
many-to-many. A ``folder:`` record carries ``name`` and ``parent``; a
subscription lists its ``folders`` in order. Cast files a podcast in the first
folder it knows and keeps the rest.

State (what was written last time, first-seen times, tombstones, carried
fields, which remote folder is which local one) lives in
``listening_subscriptions.json`` in the data folder. wx-free, strict-typed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

__all__ = [
    "SubscriptionsReport",
    "canonical_url",
    "is_private",
    "subscription_id",
    "sync_subscriptions",
]

_STATE_FILE = "listening_subscriptions.json"
_APP_KEY = "quill-cast"
#: Query parameters that make an address a key rather than an address.
_TOKEN_KEYS = {
    "token",
    "auth",
    "key",
    "apikey",
    "api_key",
    "access_token",
    "secret",
    "sig",
    "signature",
    "password",
    "pass",
    "uid",
}
#: Fields a subscription record carries that Cast reads or writes itself; any
#: other field is carried through untouched.
_SUB_KNOWN = {
    "id",
    "kind",
    "feed_url",
    "alt_urls",
    "title",
    "artwork_url",
    "private",
    "subscribed_at",
    "updated_at",
    "folders",
    "prefs",
    "app_private",
    "deleted",
}
_FOLDER_KNOWN = {"id", "kind", "name", "parent", "updated_at", "deleted"}


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_url(url: str) -> str:
    """sync.md 6.7: the one form two apps hash to the same id."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    default = {"http": 80, "https": 443}.get(scheme)
    netloc = host if port is None or port == default else f"{host}:{port}"
    path = parts.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def subscription_id(url: str) -> str:
    return "sub:" + hashlib.sha256(canonical_url(url).encode("utf-8")).hexdigest()[:16]


def _folder_record_id(local_folder_id: str) -> str:
    return "folder:" + hashlib.sha256(local_folder_id.encode("utf-8")).hexdigest()[:8]


def is_private(show: Any) -> bool:
    """A feed with a sign-in, or a key in its address (sync.md 6.7)."""
    url = str(getattr(show, "feed_url", "") or "")
    if str(getattr(show, "feed_username", "") or "").strip():
        return True
    parts = urlsplit(url)
    if parts.username or parts.password:
        return True
    return any(name.lower() in _TOKEN_KEYS for name, _value in parse_qsl(parts.query))


def _public_url(url: str) -> str:
    """The address without any sign-in in it, whatever else is true."""
    parts = urlsplit(url.strip())
    netloc = parts.hostname or ""
    if parts.port is not None:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


@dataclass(slots=True)
class SubscriptionsReport:
    """What one pass did with subscriptions, in sentences a person can act on."""

    rows: list[dict[str, Any]] = field(default_factory=list)
    said: list[str] = field(default_factory=list)
    changed: bool = False
    private_skipped: int = 0


# -- state -------------------------------------------------------------------


def _load_state(data_dir: Path) -> dict[str, Any]:
    try:
        raw = json.loads((data_dir / _STATE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    state: dict[str, Any] = {}
    for key in ("fingerprints", "updated", "first_seen", "tombstones", "folder_map", "carried"):
        value = raw.get(key)
        state[key] = dict(value) if isinstance(value, dict) else {}
    return state


def _save_state(data_dir: Path, state: dict[str, Any]) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(data_dir / _STATE_FILE, {"version": 1, **state})


# -- reading what other devices wrote -----------------------------------------


@dataclass(slots=True)
class _Incoming:
    row: dict[str, Any]
    device: str


def _newest_rows(others: list[Any]) -> dict[str, _Incoming]:
    """For each subscription or folder id, the newest row across other devices."""
    from quill.core.sync.listening_places import spoken_device

    best: dict[str, _Incoming] = {}
    for device_file in others:
        name = spoken_device(device_file)
        for row in getattr(device_file, "raw_records", []) or []:
            if not isinstance(row, dict):
                continue
            entity_id = str(row.get("id", ""))
            if not entity_id.startswith(("sub:", "folder:")):
                continue
            current = best.get(entity_id)
            if current is None or str(row.get("updated_at", "")) > str(
                current.row.get("updated_at", "")
            ):
                best[entity_id] = _Incoming(dict(row), name)
    return best


# -- the pass ------------------------------------------------------------------


def sync_subscriptions(
    library: Any, data_dir: Path | str, others: list[Any]
) -> SubscriptionsReport:
    """Apply newer subscription and folder rows from *others*, then build this
    device's own rows. Mutates *library*; the caller saves it when
    ``report.changed`` and writes ``report.rows`` into the device file."""
    data = Path(data_dir)
    state = _load_state(data)
    report = SubscriptionsReport()
    now = _now()
    incoming = _newest_rows(others)
    _notice_local_changes(library, state, now)
    _apply_folders(library, state, incoming, report)
    _apply_subscriptions(library, state, incoming, report, now)
    report.rows = _outgoing(library, state, report, now)
    try:
        _save_state(data, state)
    except OSError:
        report.said.append("What was shared could not be remembered; it will be sent again.")
    return report


def _notice_local_changes(library: Any, state: dict[str, Any], now: str) -> None:
    """Before reading anybody else: what changed here since the last pass.

    A podcast followed last time and gone now was unfollowed *here*, and that
    tombstone has to exist before another device's older "following" row is
    read, or the row would quietly follow it again. And every podcast followed
    here gets a first-seen time on its first pass, so an unfollow written
    before this device ever shared its list cannot remove it (sync.md 6.7).
    """
    present = {
        subscription_id(show.feed_url)
        for show in getattr(library, "shows", [])
        if getattr(show, "feed_url", "") and not getattr(show, "is_local", False)
    }
    for key in present:
        state["first_seen"].setdefault(key, now)
    for key in list(state["fingerprints"]):
        if key.startswith("sub:") and key not in present:
            state["tombstones"].setdefault(key, now)
            del state["fingerprints"][key]


def _apply_folders(
    library: Any, state: dict[str, Any], incoming: dict[str, _Incoming], report: SubscriptionsReport
) -> None:
    from quill.core.podcasts.models import PodcastFolder
    from quill.core.podcasts.subscriptions import new_id

    folder_map: dict[str, str] = state["folder_map"]
    local_ids = {folder.id for folder in getattr(library, "folders", [])}
    by_record = {_folder_record_id(fid): fid for fid in local_ids}
    rows = [item for key, item in incoming.items() if key.startswith("folder:")]
    # Parents first, so a nested folder finds the folder it sits in.
    rows.sort(key=lambda item: 0 if not item.row.get("parent") else 1)
    for item in rows:
        row = item.row
        record_id = str(row["id"])
        state["carried"][record_id] = {k: v for k, v in row.items() if k not in _FOLDER_KNOWN}
        if row.get("deleted"):
            continue  # a folder is never removed by another device; its podcasts stay
        local = folder_map.get(record_id) or by_record.get(record_id)
        if local in local_ids:
            folder_map[record_id] = str(local)
            continue
        name = str(row.get("name", "") or "").strip()[:120]
        if not name:
            continue
        parent_record = str(row.get("parent", "") or "")
        parent = folder_map.get(parent_record) or by_record.get(parent_record)
        same = next(
            (
                f
                for f in library.folders
                if f.name == name and (f.parent_folder_id or None) == (parent or None)
            ),
            None,
        )
        if same is None:
            same = PodcastFolder(id=new_id(), name=name, parent_folder_id=parent or None)
            library.folders.append(same)
            report.changed = True
            report.said.append(f"Added the folder {name}, made on {item.device}.")
        folder_map[record_id] = same.id
        local_ids.add(same.id)


def _show_urls(show: Any) -> set[str]:
    return {canonical_url(str(show.feed_url))} if getattr(show, "feed_url", "") else set()


def _apply_subscriptions(
    library: Any,
    state: dict[str, Any],
    incoming: dict[str, _Incoming],
    report: SubscriptionsReport,
    now: str,
) -> None:
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.subscriptions import new_id

    shows = [s for s in getattr(library, "shows", []) if getattr(s, "feed_url", "")]
    for record_id, item in incoming.items():
        if not record_id.startswith("sub:"):
            continue
        row = item.row
        at = str(row.get("updated_at", ""))
        wanted = {
            canonical_url(str(u)) for u in row.get("alt_urls", []) or [] if isinstance(u, str)
        }
        if row.get("feed_url"):
            wanted.add(canonical_url(str(row["feed_url"])))
        local = next(
            (
                s
                for s in shows
                if subscription_id(s.feed_url) == record_id or _show_urls(s) & wanted
            ),
            None,
        )
        if local is not None:
            local_record = subscription_id(local.feed_url)
            known = str(state["updated"].get(local_record, ""))
            # An unfollow wins a tie, for the same reason as below.
            if at < known or (at == known and not row.get("deleted")):
                continue
        if row.get("deleted"):
            if local is None:
                continue
            first = str(state["first_seen"].get(subscription_id(local.feed_url), ""))
            if first and at < first:
                continue  # an old unsubscribe must not undo a deliberate resubscribe
            library.remove_show(local.id)
            shows.remove(local)
            report.changed = True
            report.said.append(f"Stopped following {local.title}, removed on {item.device}.")
            state["tombstones"][subscription_id(local.feed_url)] = at
            continue
        if bool(row.get("private")):
            continue  # never in the plain file; a writer that put it there erred
        state["carried"][record_id] = {k: v for k, v in row.items() if k not in _SUB_KNOWN}
        state["carried"][record_id]["alt_urls"] = sorted({
            str(u) for u in row.get("alt_urls", []) or [] if isinstance(u, str)
        })
        state["carried"][record_id]["folders"] = [str(f) for f in row.get("folders", []) or []]
        state["carried"][record_id]["app_private"] = (
            row.get("app_private") if isinstance(row.get("app_private"), dict) else {}
        )
        folder = _first_known_folder(state, row)
        if local is None:
            if str(state["tombstones"].get(record_id, "")) >= at:
                # This device unfollowed at or after that follow; a tie keeps
                # the unfollow, because re-adding is the louder mistake.
                continue
            feed_url = str(row.get("feed_url", "") or "").strip()
            if not feed_url.startswith(("http://", "https://")):
                continue
            title = str(row.get("title", "") or "").strip()[:200] or feed_url
            local = PodcastShow(
                id=new_id(),
                title=title,
                feed_url=feed_url,
                artwork_url=str(row.get("artwork_url", "") or ""),
                folder_id=folder,
            )
            if not library.add_show(local):
                continue
            shows.append(local)
            state["first_seen"][subscription_id(feed_url)] = now
            state["tombstones"].pop(subscription_id(feed_url), None)
            report.changed = True
            report.said.append(
                f"Now following {title}, added on {item.device}. "
                "Its episodes arrive at the next check."
            )
        else:
            if folder and local.folder_id != folder:
                local.folder_id = folder
                report.changed = True
        _apply_speed(library, local, row, report)
        own = (
            row.get("app_private", {}).get(_APP_KEY)
            if isinstance(row.get("app_private"), dict)
            else None
        )
        if isinstance(own, dict) and isinstance(own.get("is_favorite"), bool):
            if local.is_favorite != own["is_favorite"]:
                local.is_favorite = own["is_favorite"]
                report.changed = True
        key = subscription_id(local.feed_url)
        state["updated"][key] = at
        state["fingerprints"][key] = _fingerprint(_sub_core(library, local, state))


def _first_known_folder(state: dict[str, Any], row: dict[str, Any]) -> str | None:
    for record_id in row.get("folders", []) or []:
        local = state["folder_map"].get(str(record_id))
        if local:
            return str(local)
    return None


def _apply_speed(library: Any, show: Any, row: dict[str, Any], report: SubscriptionsReport) -> None:
    prefs = row.get("prefs")
    if not isinstance(prefs, dict) or not isinstance(prefs.get("speed"), (int, float)):
        return
    from quill.core.podcasts.models_settings import clamp_speed

    speed = clamp_speed(float(prefs["speed"]))
    if _own_speed(library, show) != speed:
        library.apply_show_override(show, speed=speed)
        report.changed = True


def _own_speed(library: Any, show: Any) -> float | None:
    from quill.core.podcasts.settings_resolver import overrides_at

    value = overrides_at(library, level="show", scope_id=show.id).get("speed")
    return float(value) if isinstance(value, (int, float)) else None


def _sub_core(library: Any, show: Any, state: dict[str, Any]) -> dict[str, Any]:
    """The fields that, when they change, make this a newer record."""
    folders = []
    if show.folder_id:
        # The id another device gave this folder, when it came from one, so a
        # round trip does not rename it.
        back = {local: record for record, local in state["folder_map"].items()}
        folders.append(back.get(show.folder_id) or _folder_record_id(show.folder_id))
    row: dict[str, Any] = {
        "feed_url": _public_url(show.feed_url),
        "title": show.feed_title or show.title,
        "artwork_url": show.artwork_url,
        "folders": folders,
        "favorite": bool(show.is_favorite),
    }
    speed = _own_speed(library, show)
    if speed is not None:
        row["speed"] = speed
    return row


def _fingerprint(row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()


def _outgoing(
    library: Any, state: dict[str, Any], report: SubscriptionsReport, now: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    folder_back = {local: record for record, local in state["folder_map"].items()}
    written: set[str] = set()
    for folder in getattr(library, "folders", []):
        record_id = folder_back.get(folder.id) or _folder_record_id(folder.id)
        core = {"name": folder.name, "parent": folder.parent_folder_id or ""}
        key = record_id
        if state["fingerprints"].get(key) != _fingerprint(core):
            state["fingerprints"][key] = _fingerprint(core)
            state["updated"][key] = now
        row: dict[str, Any] = dict(state["carried"].get(record_id, {}))
        row.update({
            "id": record_id,
            "kind": "folder",
            "name": folder.name,
            "updated_at": state["updated"][key],
        })
        if folder.parent_folder_id:
            row["parent"] = folder_back.get(folder.parent_folder_id) or _folder_record_id(
                folder.parent_folder_id
            )
        rows.append(row)
        written.add(record_id)
    for show in getattr(library, "shows", []):
        if not getattr(show, "feed_url", "") or getattr(show, "is_local", False):
            continue
        if is_private(show):
            report.private_skipped += 1
            continue
        key = subscription_id(show.feed_url)
        core = _sub_core(library, show, state)
        if state["fingerprints"].get(key) != _fingerprint(core):
            state["fingerprints"][key] = _fingerprint(core)
            state["updated"][key] = now
        state["first_seen"].setdefault(key, now)
        carried = dict(state["carried"].get(key, {}))
        alt = set(carried.pop("alt_urls", []) or [])
        folders = list(core["folders"])
        for extra in carried.pop("folders", []) or []:
            if extra not in folders:
                folders.append(extra)  # memberships Cast cannot hold, carried back
        app_private = dict(carried.pop("app_private", {}) or {})
        app_private[_APP_KEY] = {"is_favorite": bool(show.is_favorite)}
        row = dict(carried)
        row.update({
            "id": key,
            "kind": "subscription",
            "feed_url": core["feed_url"],
            "alt_urls": sorted(alt - {core["feed_url"]}),
            "title": core["title"],
            "private": False,
            "subscribed_at": state["first_seen"][key],
            "updated_at": state["updated"][key],
            "folders": folders,
            "app_private": app_private,
        })
        if show.artwork_url:
            row["artwork_url"] = show.artwork_url
        if "speed" in core:
            row["prefs"] = {"speed": core["speed"]}
        rows.append(row)
        written.add(key)
    # Tombstones are kept so they reach every device, and dropped once this
    # device follows the podcast again.
    for key, at in sorted(state["tombstones"].items()):
        if key in written:
            del state["tombstones"][key]
            continue
        rows.append({"id": key, "deleted": True, "updated_at": at})
    return rows
