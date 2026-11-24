"""The shell apps' automatic update offer, at a quiet moment (FUX-15).

Quill Radio, QUILL Cast and QUILL Studio run a silent update check at launch
(``app_shell.check_for_app_updates``). Its offer used to open the moment the
check came back: over the station or episode that had just resumed, during a
recording, over a Studio live broadcast, and from the tray. Now it goes
through :func:`quill.ui.maintenance_moment_ui.offer_when_quiet` with the app's
own probes (:mod:`quill.ui.maintenance_probes`), and Help > Check for Updates
opens a held offer at once (:func:`run_held`).

While it waits, the status bar carries one line saying what is waiting, after
whatever the app writes there, and Update History records it for an app with
release channels. Nothing is spoken.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["run_held", "shell_offer_when_quiet"]

ROUTE = "Help, Check for Updates offers it now."


def _key(app_key: str) -> str:
    return app_key or "shell"


def _clear(shell: Any) -> None:
    """The offer is opening: the "waits" line is no longer true."""
    shell._maintenance_note = ""
    shell._set_status(getattr(shell, "_status_base", ""))


def run_held(app_key: str) -> bool:
    """Check for Updates asked for: open a held update offer now, if any."""
    from quill.ui.maintenance_moment_ui import take_held

    run = take_held(_key(app_key), "update")
    if run is None:
        return False
    run()
    return True


def _clear_after(shell: Any, offer: Callable[[], object]) -> Callable[[], object]:
    def _run() -> object:
        _clear(shell)
        return offer()

    return _run


def shell_offer_when_quiet(
    shell: Any, app_key: str, release: Any, offer: Callable[[], object]
) -> bool:
    """Open the launch check's *offer* now, or hold it until quiet."""
    from quill.core.updater.profiles import PROFILES
    from quill.core.versioning import ReleaseVersion
    from quill.ui.maintenance_moment_ui import offer_when_quiet
    from quill.ui.maintenance_probes import probes_for

    version = str(getattr(release, "version", "") or "")
    shown = ReleaseVersion.try_parse(version)

    def _note(line: str) -> None:
        # Kept on the bar after the app's own status (Radio and Cast rewrite
        # it on every playback change), until the offer opens.
        shell._maintenance_note = line
        shell._set_status(getattr(shell, "_status_base", ""))
        if app_key in PROFILES:
            from quill.core.updater import history

            history.record(app_key, "held_back", to_version=version, detail=line)

    return offer_when_quiet(
        _key(app_key),
        kind="update",
        label=f"Update {shown.display() if shown is not None else version}",
        run=_clear_after(shell, offer),  # cleared on Check for Updates too
        route=ROUTE,
        window=shell.frame,
        note=_note,
        probes=probes_for(app_key, shell),
    )
