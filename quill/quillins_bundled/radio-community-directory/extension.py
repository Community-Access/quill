"""Radio Community Directory -- a bundled sample ``radio.directory`` provider.

Demonstrates the station-directory capability for Quill Radio: the handler
receives the current search query and returns a small static list of matching
"community" stations, which the host folds into the Find Stations fan-out. It
makes **no** network call -- the stations come from a hard-coded demo list -- so
it needs no ``net`` capability (least privilege).

The out-of-process worker discards a handler's return value, so the result is
handed back by writing a JSON array to storage under ``_RESULT_KEY`` (kept in
lock-step with ``quill.core.quillins.app_host.DIRECTORY_RESULT_KEY``); the host
reads it from the shared storage dict, decodes it, and builds RadioStation rows.
"""

from __future__ import annotations

import json

# Must match quill.core.quillins.app_host.DIRECTORY_RESULT_KEY.
_RESULT_KEY = "__quill_radio_directory_result__"

#: A tiny static "community" directory. A real provider would read these from its
#: own storage or a bundled data file; the sample hard-codes a couple so it works
#: out of the box with no network.
_STATIONS = [
    {
        "name": "Community Voices FM",
        "url": "https://stream.example.org/community-voices.mp3",
        "source": "Community Directory",
    },
    {
        "name": "Local Access Radio",
        "url": "https://stream.example.org/local-access.mp3",
        "source": "Community Directory",
    },
]


def directory_search(api, event: dict) -> None:
    """Return community stations matching the query in ``event``.

    ``event`` carries ``{"query": ...}``. The sample keeps stations whose name
    contains the query (case-insensitively); an empty query returns them all.
    """

    query = str(event.get("query", "")).strip().lower()
    if not query:
        matches = list(_STATIONS)
    else:
        matches = [s for s in _STATIONS if query in s["name"].lower()]
    api.set_storage(_RESULT_KEY, json.dumps(matches))


# --- the browse trio (Quillin Sources) ---------------------------------------
#
# With these three registered, this Quillin is a full browse source in Quill
# Radio's tree, not only a Find Stations contributor. The same static list
# serves both, split into two categories to show the shape; the "key" row shows
# the play-time resolve step a real provider would use for addresses it must
# not cache (a tokenized or expiring stream URL).

_CATEGORIES = {
    "Community": _STATIONS,
    "Late Night": [
        {
            "name": "Night Owl Community Radio",
            # No "url": the row carries a key instead, and the host calls
            # directory_resolve with it when the row is played.
            "key": "night-owl",
            "source": "Community Directory",
        }
    ],
}

_RESOLVABLE = {"night-owl": "https://stream.example.org/night-owl.mp3"}


def directory_categories(api, event: dict) -> None:
    """The category names, as a JSON array of strings."""

    api.set_storage(_RESULT_KEY, json.dumps(sorted(_CATEGORIES)))


def directory_stations(api, event: dict) -> None:
    """One category's stations; ``query`` narrows them when the branch is searched."""

    category = str(event.get("category", "")).strip()
    query = str(event.get("query", "")).strip().lower()
    rows = (
        list(_CATEGORIES.get(category, []))
        if category
        else [row for rows in _CATEGORIES.values() for row in rows]
    )
    if query:
        rows = [row for row in rows if query in row["name"].lower()]
    api.set_storage(_RESULT_KEY, json.dumps(rows))


def directory_resolve(api, event: dict) -> None:
    """The playable URL behind a row's key -- called at play time, never before."""

    api.set_storage(_RESULT_KEY, _RESOLVABLE.get(str(event.get("key", "")), ""))


def register(api) -> None:
    api.register_command("directory_search", directory_search)
    api.register_command("directory_categories", directory_categories)
    api.register_command("directory_stations", directory_stations)
    api.register_command("directory_resolve", directory_resolve)
    api.log("Radio Community Directory loaded")
