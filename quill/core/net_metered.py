"""Is this connection metered? And what to do when nobody knows.

QUILL Cast has mentioned the metered case in comments for two releases and has
never checked: an automatic download on a phone hotspot cost whatever it cost.
This is the check, and it is small on purpose.

**Unknown means unmetered.** That is the whole design decision. Windows reports
a connection's cost through ``NetworkInformation.GetInternetConnectionProfile``,
which needs the WinRT bridge, which is not present in every build and answers
nothing on a machine with no profile at all. Refusing to download on a *guess*
would mean a listener whose episodes silently stopped arriving, with no message
that made sense and nothing to fix -- which is a far worse failure than one
unwanted download on a tethered connection.

So the three answers are **metered**, **unmetered** and **unknown**, they are
distinguishable to a caller that cares, and the shipped rule treats unknown as
unmetered.

**It only ever holds an automatic download.** A download somebody asked for by
name happens whatever this says. Nobody who pressed Download wants to be told
that their connection has opinions.

wx-free, strict-typed, no network of its own.
"""

from __future__ import annotations

__all__ = [
    "METERED",
    "UNKNOWN",
    "UNMETERED",
    "connection_cost",
    "held_back_message",
    "may_download",
]

METERED = "metered"
UNMETERED = "unmetered"
UNKNOWN = "unknown"

#: WinRT's ``NetworkCostType``: 1 is Unrestricted, 2 Fixed (a capped plan), 3
#: Variable (paid by the byte), 0 Unknown. Two and three are both "this costs
#: money", which is the only distinction that matters here.
_COST_UNRESTRICTED = 1


def connection_cost() -> str:
    """:data:`METERED`, :data:`UNMETERED`, or :data:`UNKNOWN`. Never raises."""
    try:
        from winrt.windows.networking.connectivity import NetworkInformation
    except Exception:  # noqa: BLE001 - no WinRT bridge in this build
        return UNKNOWN
    try:
        profile = NetworkInformation.get_internet_connection_profile()
        if profile is None:
            return UNKNOWN
        cost = profile.get_connection_cost()
        if cost is None:
            return UNKNOWN
        network_cost = int(getattr(cost, "network_cost_type", 0))
    except Exception:  # noqa: BLE001 - a machine that will not answer is "unknown"
        return UNKNOWN
    if network_cost == 0:
        return UNKNOWN
    return UNMETERED if network_cost == _COST_UNRESTRICTED else METERED


def may_download(settings: object, *, automatic: bool = True) -> bool:
    """Whether a download should go ahead now.

    *automatic* False -- somebody pressed Download -- is always True: the guard
    exists to stop the app spending somebody's data without being asked, not to
    argue with them when they ask.
    """
    if not automatic:
        return True
    if bool(getattr(settings, "download_on_metered", True)):
        return True
    return connection_cost() != METERED


def held_back_message(count: int) -> str:
    """What to say, once, when downloads are waiting on the connection.

    Once, and with the count, because the failure this replaces is episodes
    quietly not arriving -- which somebody discovers on a train with nothing to
    listen to, and cannot diagnose.
    """
    if count <= 0:
        return ""
    thing = "download" if count == 1 else "downloads"
    return (
        f"Holding {count} {thing} until you are off a metered connection. "
        "You can still download anything yourself."
    )
