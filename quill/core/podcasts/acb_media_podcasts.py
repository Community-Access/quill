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
from quill.core.podcasts.opml import OpmlImportOutcome, decode_opml_bytes, import_opml
from quill.core.podcasts.subscriptions import PodcastLibrary

#: ACB's own published podcast directory (the file ACB Link itself reads).
ACB_PODCASTS_OPML_URL = "https://link.acb.org/link.opml"

#: The library folder every ACB Media podcast lands in.
ACB_PODCASTS_FOLDER = "ACB Media"

_TIMEOUT_SECONDS = 20
_MAX_BYTES = 2 * 1024 * 1024  # the directory is ~10 KB; 2 MB is generous
_USER_AGENT = "QUILL (podcast client; +https://github.com/Community-Access/quill)"


class AcbMediaPodcastsError(CodedError):
    code = "QUILL-PODCASTS-ACB-DIRECTORY"


def _fetch_opml_bytes() -> bytes:
    """One HTTPS GET for ACB's directory OPML -- the reviewed egress site."""
    request = urllib.request.Request(ACB_PODCASTS_OPML_URL, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            return payload
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise AcbMediaPodcastsError(f"Could not reach ACB's podcast directory: {error}") from error


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
