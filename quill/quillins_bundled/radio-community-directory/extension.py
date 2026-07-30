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


def register(api) -> None:
    api.register_command("directory_search", directory_search)
    api.log("Radio Community Directory loaded")
