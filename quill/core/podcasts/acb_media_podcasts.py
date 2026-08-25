"""ACB Media's podcast directory, fetched live from ACB's own OPML.

ACB Link (both the mobile app and its open-source desktop sibling) drives
its podcast list from ``https://link.acb.org/link.opml`` -- ACB's published,
maintained directory of every ACB Media podcast (36 shows at the time of
writing). Unlike the ten radio streams in ``core/radio/acb_media.py`` (a
rarely-changing list bundled statically), the podcast lineup genuinely
changes, so this is fetched live each time the user asks for it: adding the
folder twice simply picks up whatever is new, and the existing OPML import
machinery guarantees no duplicates (matching by normalized feed URL).

wx-free, strict-typed. One reviewed egress site (:func:`_fetch_opml_bytes`);
disabled in Safe Mode via :func:`feed_reader.refuse_in_safe_mode`.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request

from quill.core.error_codes import CodedError
from quill.core.podcasts.feed_reader import refuse_in_safe_mode
from quill.core.podcasts.opml import (
    ImportedShow,
    OpmlImportOutcome,
    decode_opml_bytes,
    import_opml,
    parse_opml,
)
from quill.core.podcasts.subscriptions import PodcastLibrary

#: ACB's own published podcast directory (the file ACB Link itself reads).
ACB_PODCASTS_OPML_URL = "https://link.acb.org/link.opml"

#: The same lineup as ACB publishes on Pinecast, the network that hosts it.
#:
#: Used by the **picker** (Community > ACB Media Podcasts...) rather than by
#: :func:`add_acb_media_podcasts`, and the difference is the reason it exists:
#: compared on 2026-08-25, ACB's own copy lists 36 shows with no descriptions,
#: while Pinecast's lists 41 *with* a one-line summary on every one. A picker
#: whose whole job is helping somebody choose between forty shows they have
#: not heard cannot do it from titles alone. (ACB's copy also strips the "ACB "
#: prefix -- "Advocacy Update" against "ACB Advocacy Update" -- so the two read
#: differently even where they agree.)
ACB_NETWORK_OPML_URL = "https://pinecast.com/network/d6beadf5-05de-49dd-bd82-066af8baae4a/opml"

#: The library folder every ACB Media podcast lands in.
ACB_PODCASTS_FOLDER = "ACB Media"

#: The folder the picker files its choices under, in the podcast library and in
#: Quill Radio's favorites alike. Deliberately not ACB_PODCASTS_FOLDER: "add
#: every ACB show" and "the handful I picked" are different collections, and
#: dropping the second into the first would make the choosing pointless.
ACB_PICKED_FOLDER = "ACB Media Podcasts"

_TIMEOUT_SECONDS = 20
_MAX_BYTES = 2 * 1024 * 1024  # the directory is ~10 KB; 2 MB is generous
_USER_AGENT = "QUILL (podcast client; +https://github.com/Community-Access/quill)"


class AcbMediaPodcastsError(CodedError):
    code = "QUILL-PODCASTS-ACB-DIRECTORY"


def _fetch_opml_bytes(url: str = ACB_PODCASTS_OPML_URL) -> bytes:
    """One HTTPS GET for a directory OPML -- the reviewed egress site.

    Both ACB directories come through here rather than growing a second
    ``urlopen``: the egress audit inventories call *sites*, and one site with a
    parameter is one thing to review instead of two things to keep in step.
    """
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            return payload
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise AcbMediaPodcastsError(f"Could not reach ACB's podcast directory: {error}") from error


def fetch_acb_media_catalog(
    *, safe_mode: bool = False, opml_text: str | None = None
) -> list[ImportedShow]:
    """Every ACB Media podcast on offer, A-Z, each with its description.

    What the picker lists. Sorted here rather than in the dialog so the order
    a reader first meets is the order the pure rule
    (:mod:`quill.core.podcasts.pick_list`) maintains -- one definition of
    "alphabetical", used on both sides of the window.

    *opml_text* short-circuits the fetch, for tests and for a caller that has
    already read the file.
    """
    if opml_text is None:
        refuse_in_safe_mode(safe_mode)
        opml_text = decode_opml_bytes(_fetch_opml_bytes(ACB_NETWORK_OPML_URL))
    shows = [show for show in parse_opml(opml_text) if show.feed_url]
    shows.sort(key=lambda show: show.title.casefold())
    return shows


def add_acb_media_podcasts(
    library: PodcastLibrary,
    *,
    safe_mode: bool = False,
    opml_text: str | None = None,
) -> OpmlImportOutcome:
    """Fetch ACB's live directory and subscribe to every show in it, inside
    the :data:`ACB_PODCASTS_FOLDER` folder. Idempotent: running it again
    adds only shows that are new since last time (normalized-URL dedupe).

    New shows arrive stream-only so pressing one menu item never queues 36
    podcasts of downloads. ``opml_text`` injects a pre-fetched document
    (tests; never the UI path).
    """
    refuse_in_safe_mode(safe_mode)
    if opml_text is None:
        opml_text = decode_opml_bytes(_fetch_opml_bytes())
    return import_opml(library, opml_text, stream_only=True, into_folder=ACB_PODCASTS_FOLDER)
