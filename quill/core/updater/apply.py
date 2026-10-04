"""Undoing an update that did not start (release-channels plan 6.6, Phase 4).

**The health check.** When the update helper has installed a new version it
starts it again and waits up to two minutes for this file to appear::

    <updates>/started-<version>.ok

The app writes it from :func:`confirm_started`, which every app calls once its
first window is on screen. If it never appears, the helper undoes the update:

* **installed copies** run the previous version's installer again, kept in
  ``<updates>/rollback/`` for exactly this;
* **portable copies** swap the folders back: the update went into
  ``<folder>.new``, the old copy was renamed ``<folder>.previous``, and the
  helper renames them back and moves ``data`` home.

Either way the helper writes ``<updates>/apply-result.json`` with
``"rolled_back": true``, and on its next start the app says once, plainly,
what happened, and Update History records the undo.

**What is kept, and for how long** (owner decisions, 2026-10-03 and
2026-10-04). The installer of the version you are running is kept in
``<updates>/rollback/`` -- it is what a failed *next* update goes back to.
How long depends on the channel (:func:`keeps_installer`):

* **Beta and Dev** keep it for as long as that version is the one running,
  because an update that does not start is likeliest there;
* **Stable** keeps it only for seven days or three successful starts after
  each update, whichever comes first, and then gives the disk space (about
  200 MB) back. A later failed update on Stable cannot undo itself; the
  installer of the version it came from can be downloaded again.

After an update, the previous version's installer (or a portable copy's
``.previous`` folder) is kept until the new version has started three times,
or for seven days, whichever comes first, on every channel.

wx-free and strict-typed. Nothing here runs an installer: it keeps the books
the helper and the app read.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from quill.core.versioning import ReleaseVersion

__all__ = [
    "KEEP_DAYS",
    "KEEP_STARTS",
    "HEALTH_WAIT_SECONDS",
    "StartReport",
    "confirm_started",
    "installed_version",
    "keeps_installer",
    "pending_path",
    "record_pending",
    "result_path",
    "rollback_setup_for",
    "started_marker",
]

KEEP_STARTS = 3
KEEP_DAYS = 7
HEALTH_WAIT_SECONDS = 120

_STATE = "rollback-state.json"


def keeps_installer(channel: str) -> bool:
    """True when *channel* keeps the running version's installer for as long as
    it runs (Beta, Dev); Stable ages it out like the previous one."""
    from quill.core.updater.channels import normalize_channel

    return normalize_channel(channel) != "stable"


def _channel_of(app_key: str) -> str:
    try:
        from quill.core.updater.channels import state_for

        return state_for(app_key).channel
    except Exception:  # noqa: BLE001 - unknown: Stable, the cautious answer for disk
        return "stable"


def _canon(version: str) -> str:
    """One spelling per version (``1.1.0 Beta 1`` and ``1.1.0-beta.1`` agree).

    The build stays in it (``3.2.0-build.2``; commit metadata does not): a
    rebuild of the same version is a different version to wait for, and build
    1 starting must never count as build 2 having started.
    """
    parsed = ReleaseVersion.try_parse(version)
    return parsed.tag_version() if parsed is not None else version.strip()


def _same(a: object, b: str) -> bool:
    return bool(a) and _canon(str(a)) == _canon(b)


def _safe(version: str) -> str:
    return re.sub(r"[^0-9A-Za-z.\-]+", "-", _canon(version)).strip("-") or "unknown"


def started_marker(updates: Path, version: str) -> Path:
    """The file the helper waits for: the new version is up."""
    return updates / f"started-{_safe(version)}.ok"


def result_path(updates: Path) -> Path:
    return updates / "apply-result.json"


def pending_path(updates: Path) -> Path:
    return updates / "apply-pending.json"


def _read(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write(path: Path, data: dict[str, object]) -> None:
    from quill.core.storage import write_json_atomic

    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, data)


def installed_version(updates: Path) -> str:
    """The version the kept installer is for -- the running one, as far as the
    books know (:func:`confirm_started` forgets it when another version starts)."""
    installed = _read(updates / "rollback" / _STATE).get("installed")
    return str(installed.get("version") or "") if isinstance(installed, dict) else ""


def rollback_setup_for(updates: Path, version: str) -> Path | None:
    """The kept installer for *version* (the running one), if there is one."""
    state = _read(updates / "rollback" / _STATE)
    installed = state.get("installed")
    if not isinstance(installed, dict) or not _same(installed.get("version"), version):
        return None
    setup = Path(str(installed.get("setup") or ""))
    return setup if setup.is_file() else None


def record_pending(
    updates: Path,
    *,
    app_key: str,
    from_version: str,
    to_version: str,
    setup: Path | None,
    portable_previous: Path | None = None,
    now: datetime | None = None,
) -> None:
    """Note an update about to be applied, before the helper starts.

    Clears any old ``apply-result.json`` and ``started-*.ok`` so the helper
    cannot mistake a previous run's answer for this one.
    """
    for old in [result_path(updates), *updates.glob("started-*.ok")]:
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass
    _write(
        pending_path(updates),
        {
            "app": app_key,
            "from": from_version,
            "to": to_version,
            "setup": str(setup or ""),
            "portable_previous": str(portable_previous or ""),
            "at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
        },
    )


@dataclass(frozen=True)
class StartReport:
    """What :func:`confirm_started` found, for the app to say and record."""

    #: The update to this version just succeeded.
    installed: str = ""
    #: An update failed and was undone: the version that did not start.
    rolled_back_from: str = ""
    #: The sentence to say once (empty when there is nothing to say).
    notice: str = ""


def _shown(version: str) -> str:
    parsed = ReleaseVersion.try_parse(version)
    return parsed.display() if parsed is not None else version


def confirm_started(
    updates: Path,
    *,
    app_key: str,
    app_name: str,
    version: str,
    now: datetime | None = None,
    history_path: Path | None = None,
    channel: str | None = None,
) -> StartReport:
    """Call once the first window is up. Never raises.

    Writes the marker the helper waits for, settles a pending update (success
    or undo, each recorded in Update History), and ages out what was kept for
    rolling back -- by *channel* (default: this app's, from ``channels.json``).
    """
    try:
        return _confirm(
            updates,
            app_key,
            app_name,
            version,
            now or datetime.now(UTC),
            history_path,
            _channel_of(app_key) if channel is None else channel,
        )
    except Exception:  # noqa: BLE001 - book-keeping must never cost a launch
        return StartReport()


def _confirm(
    updates: Path,
    app_key: str,
    app_name: str,
    version: str,
    moment: datetime,
    history_path: Path | None,
    channel: str,
) -> StartReport:
    from quill.core.updater import history

    pending = _read(pending_path(updates))
    result = _read(result_path(updates))
    if pending and _same(pending.get("to"), version):
        updates.mkdir(parents=True, exist_ok=True)
        started_marker(updates, version).write_text("started\n", encoding="utf-8")
    report = StartReport()
    if result.get("rolled_back") and _same(result.get("version"), version):
        failed = str(result.get("failed_version") or pending.get("to") or "")
        history.record(
            app_key,
            "rolled_back",
            from_version=failed,
            to_version=version,
            detail=f"{failed} did not start, so the update was undone.",
            path=history_path,
            now=moment,
        )
        report = StartReport(
            rolled_back_from=failed,
            notice=(
                f"The update to {_shown(failed)} didn't start, so {app_name} went back to "
                f"{_shown(version)}. Nothing of yours was changed. Details are in Help, "
                "Update History."
            ),
        )
        _clear(updates)
    elif pending and _same(pending.get("to"), version):
        _promote_kept(updates, pending, moment)
        history.record(
            app_key,
            "installed",
            from_version=str(pending.get("from") or ""),
            to_version=version,
            path=history_path,
            now=moment,
        )
        report = StartReport(installed=version)
        _clear(updates, keep_marker=True)
    _forget_stale(updates, version)
    _age_out(updates, moment)
    _age_out_installed(updates, moment, keep=keeps_installer(channel))
    return report


def _forget_stale(updates: Path, version: str) -> None:
    """A kept installer for some other version than the running one is no use
    for an undo (somebody installed by hand since): forget it, delete it."""
    folder = updates / "rollback"
    state = _read(folder / _STATE)
    installed = state.get("installed")
    if not isinstance(installed, dict) or _same(installed.get("version"), version):
        return
    setup = Path(str(installed.get("setup") or ""))
    if installed.get("setup") and setup.is_file():
        setup.unlink(missing_ok=True)
    state.pop("installed", None)
    _write(folder / _STATE, state)


def _clear(updates: Path, *, keep_marker: bool = False) -> None:
    for path in (pending_path(updates), result_path(updates)):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    if not keep_marker:
        for marker in updates.glob("started-*.ok"):
            try:
                marker.unlink(missing_ok=True)
            except OSError:
                pass


def _promote_kept(updates: Path, pending: dict[str, object], moment: datetime) -> None:
    """After a good update: the new installer is the one kept; the old one ages out."""
    folder = updates / "rollback"
    state = _read(folder / _STATE)
    previous = state.get("installed") if isinstance(state.get("installed"), dict) else None
    setup = Path(str(pending.get("setup") or ""))
    new_state: dict[str, object] = {"version": 1}
    if setup.is_file():
        folder.mkdir(parents=True, exist_ok=True)
        kept = folder / setup.name
        if kept != setup:
            shutil.move(str(setup), str(kept))
        new_state["installed"] = {
            "version": str(pending.get("to") or ""),
            "setup": str(kept),
            "since": moment.isoformat(timespec="seconds"),
            "starts": 0,
        }
    aging: dict[str, object] = {"since": moment.isoformat(timespec="seconds"), "starts": 0}
    if isinstance(previous, dict) and previous.get("setup"):
        aging["setup"] = str(previous.get("setup"))
        aging["version"] = str(previous.get("version") or "")
    portable_previous = str(pending.get("portable_previous") or "")
    if portable_previous:
        aging["folder"] = portable_previous
    if len(aging) > 2:
        new_state["previous"] = aging
    _write(folder / _STATE, new_state)


def _expired(entry: dict[str, object], moment: datetime) -> bool:
    """Count this start; True once 3 starts or 7 days have passed since ``since``."""
    starts = int(str(entry.get("starts") or 0)) + 1
    try:
        since = datetime.fromisoformat(str(entry.get("since")))
    except ValueError:
        since = moment
        entry["since"] = moment.isoformat(timespec="seconds")
    entry["starts"] = starts
    return starts >= KEEP_STARTS or moment - since >= timedelta(days=KEEP_DAYS)


def _age_out_installed(updates: Path, moment: datetime, *, keep: bool) -> None:
    """Stable: the running version's installer goes after 3 starts or 7 days.
    Beta and Dev (*keep*): it stays while that version runs."""
    folder = updates / "rollback"
    state = _read(folder / _STATE)
    installed = state.get("installed")
    if not isinstance(installed, dict) or not installed.get("setup"):
        return
    if keep:
        if "since" in installed or "starts" in installed:
            installed.pop("since", None)
            installed.pop("starts", None)
            _write(folder / _STATE, state)
        return
    if not _expired(installed, moment):
        _write(folder / _STATE, state)
        return
    setup = Path(str(installed.get("setup") or ""))
    if setup.is_file():
        setup.unlink(missing_ok=True)
    # The version stays known (the next update's "from"); only the file goes.
    state["installed"] = {"version": str(installed.get("version") or ""), "setup": ""}
    _write(folder / _STATE, state)


def _age_out(updates: Path, moment: datetime) -> None:
    folder = updates / "rollback"
    state = _read(folder / _STATE)
    previous = state.get("previous")
    if not isinstance(previous, dict):
        return
    starts = int(str(previous.get("starts") or 0)) + 1
    try:
        since = datetime.fromisoformat(str(previous.get("since")))
    except ValueError:
        since = moment
    if starts < KEEP_STARTS and moment - since < timedelta(days=KEEP_DAYS):
        previous["starts"] = starts
        _write(folder / _STATE, state)
        return
    setup = Path(str(previous.get("setup") or ""))
    if previous.get("setup") and setup.is_file():
        setup.unlink(missing_ok=True)
    old_folder = Path(str(previous.get("folder") or ""))
    if previous.get("folder") and old_folder.name.endswith(".previous") and old_folder.is_dir():
        shutil.rmtree(old_folder, ignore_errors=True)
    state.pop("previous", None)
    _write(folder / _STATE, state)
