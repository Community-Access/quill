"""The curated catalogue Radio and Cast offer from their Community menu.

A living list of stations, podcasts and places, fetched from
``https://quillforall.org/picks/v1/picks.json`` and rebuilt on the site
whenever a suggestion is approved -- so adding a station on a Tuesday reaches
everybody on Tuesday rather than at the next installer. The whole design,
including how suggestions become entries, is in
``docs/design/community-picks.md``.

Four rules this module exists to keep:

* **A copy ships with the app.** The picker works on first run, offline, and
  if the site is ever down. A fetched copy supersedes it; a failed fetch falls
  back to it rather than to an empty window.
* **Retired means stop offering, never remove.** A pick marked ``retired``
  vanishes from the picker and *nothing a listener already added is touched*.
  Their favorite stays, their subscription stays. A catalogue that could reach
  into somebody's library would be one worth refusing to fetch.
* **An unknown ``type`` is skipped, silently.** That is what lets a future
  entry kind ship without breaking a client that predates it.
* **Nothing is fetched in Safe Mode.**

wx-free, strict-typed. One reviewed egress site (:func:`_fetch`).
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError

#: Versioned in the path, so a breaking change cannot reach a v1 client.
PICKS_URL = "https://quillforall.org/picks/v1/picks.json"

#: The detached Ed25519 signature beside it, verified against the same bundled
#: publisher key that signs Quillins and release artifacts.
#:
#: This file causes the app to subscribe to feeds and add stations, so whoever
#: could replace it could point listeners at content they did not choose.
#: HTTPS from our own domain is decent; a signature makes the question moot,
#: and the machinery already existed (:mod:`quill.tools.signing`).
PICKS_SIGNATURE_URL = PICKS_URL + ".minisig"

#: What a document must say it is before we read a word of it.
FORMAT = "quillville-picks"

#: A day. Long enough that opening the picker is instant and the site is not
#: hammered; short enough that an approval lands the same day. Refresh is
#: always offered, and the summary line always says how old the copy is.
MAX_AGE_SECONDS = 24 * 60 * 60

#: The kinds a client of this version understands. Anything else is skipped.
KNOWN_TYPES = frozenset({"stream", "podcast", "place"})

_TIMEOUT_SECONDS = 20
_MAX_BYTES = 4 * 1024 * 1024
_USER_AGENT = "QUILL (community picks; +https://github.com/Community-Access/quill)"


class CommunityPicksError(CodedError):
    code = "QUILL-PICKS-CATALOGUE"


@dataclass(frozen=True, slots=True)
class Pick:
    """One thing on offer."""

    id: str
    type: str
    title: str
    description: str = ""
    language: str = ""
    homepage: str = ""
    artwork_url: str = ""
    stream_url: str = ""
    feed_url: str = ""
    node_id: str = ""
    tags: tuple[str, ...] = ()
    added: str = ""

    @property
    def target(self) -> str:
        """The URL or node this pick stands for. "" when it stands for nothing."""
        return self.stream_url or self.feed_url or self.node_id


@dataclass(frozen=True, slots=True)
class Collection:
    """A named group of picks, shown as one section."""

    id: str
    title: str
    description: str = ""
    picks: tuple[Pick, ...] = ()


@dataclass(frozen=True, slots=True)
class Catalogue:
    """A parsed, filtered catalogue, plus how it got here."""

    collections: tuple[Collection, ...] = ()
    updated: str = ""
    title: str = ""
    #: True when this is the copy that shipped with the app rather than a
    #: fetched one. The picker says so, because "why is that station missing?"
    #: has a very different answer offline.
    bundled: bool = True
    #: Seconds since the fetched copy was written, or None when bundled.
    age_seconds: float | None = None
    #: Types present in the file that this client does not understand. Counted
    #: rather than hidden: it is how somebody discovers their app is old.
    skipped_unknown: int = 0
    #: Retired picks that were dropped from the offer.
    skipped_retired: int = 0
    warnings: tuple[str, ...] = field(default=())

    @property
    def all_picks(self) -> tuple[Pick, ...]:
        return tuple(pick for collection in self.collections for pick in collection.picks)

    @property
    def is_empty(self) -> bool:
        return not self.all_picks


def _fetch(url: str = PICKS_URL) -> bytes:
    """One HTTPS GET for the catalogue -- the reviewed egress site."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            return payload
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise CommunityPicksError(f"Could not reach the Community Picks list: {error}") from error


def parse(document: Any, *, app: str = "") -> Catalogue:
    """Turn a decoded document into a catalogue. Never raises on bad content.

    Forgiving by design: a catalogue is fetched from the web and a single
    malformed entry must cost that entry, not the window. What it refuses is a
    document that does not say it is one of ours -- past that point, every
    problem is a skipped row and a warning.
    """
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise CommunityPicksError("That file is not a Community Picks catalogue.")

    warnings: list[str] = []
    unknown = retired = 0
    collections: list[Collection] = []
    for raw_collection in document.get("collections") or []:
        if not isinstance(raw_collection, dict):
            continue
        picks: list[Pick] = []
        for raw in raw_collection.get("items") or []:
            if not isinstance(raw, dict):
                continue
            if raw.get("retired"):
                retired += 1
                continue
            apps = raw.get("apps")
            if app and isinstance(apps, list) and apps and app not in apps:
                continue
            kind = str(raw.get("type", "")).strip()
            if kind not in KNOWN_TYPES:
                unknown += 1
                continue
            pick = _pick(raw, kind)
            if pick is None:
                warnings.append(f"{raw.get('id') or 'an entry'} was skipped: nothing to point at.")
                continue
            picks.append(pick)
        if picks:
            collections.append(
                Collection(
                    id=str(raw_collection.get("id", "")),
                    title=str(raw_collection.get("title", "")) or "Picks",
                    description=str(raw_collection.get("description", "")),
                    picks=tuple(picks),
                )
            )
    return Catalogue(
        collections=tuple(collections),
        updated=str(document.get("updated", "")),
        title=str(document.get("title", "")),
        skipped_unknown=unknown,
        skipped_retired=retired,
        warnings=tuple(warnings),
    )


def _pick(raw: dict[str, Any], kind: str) -> Pick | None:
    pick = Pick(
        id=str(raw.get("id", "")).strip(),
        type=kind,
        title=str(raw.get("title", "")).strip(),
        description=str(raw.get("description", "")).strip(),
        language=str(raw.get("language", "")).strip(),
        homepage=_https_only(raw.get("homepage")),
        artwork_url=_https_only(raw.get("artwork_url")),
        stream_url=_https_only(raw.get("stream_url")),
        feed_url=_https_only(raw.get("feed_url")),
        node_id=str(raw.get("node_id", "")).strip(),
        tags=tuple(str(tag) for tag in raw.get("tags") or [] if str(tag).strip()),
        added=str(raw.get("added", "")).strip(),
    )
    if not pick.id or not pick.title or not pick.target:
        return None
    return pick


def _https_only(value: Any) -> str:
    """A URL, or "" if it is not plainly HTTPS.

    Not fussiness: a catalogue that can point the app at plain HTTP is a
    catalogue that can be rewritten by anybody on the path between here and
    the listener.
    """
    text = str(value or "").strip()
    return text if text.lower().startswith("https://") else ""


def verify(document_bytes: bytes, signature_bytes: bytes) -> tuple[bool, str]:
    """``(trusted, why not)`` for a fetched catalogue and its signature.

    Fail-closed and never raises: an unverifiable catalogue is refused and the
    caller falls back to the bundled copy, which is why refusing is safe. A
    picker that quietly showed unsigned picks would make the signature
    decorative.
    """
    import tempfile

    try:
        from quill.tools.signing import load_publisher_public_key, verify_artifact
    except Exception as error:  # noqa: BLE001 - a missing signer is not a crash
        return False, f"the signature could not be checked ({error})"
    try:
        with tempfile.TemporaryDirectory() as folder:
            artifact = Path(folder) / "picks.json"
            artifact.write_bytes(document_bytes)
            sidecar = Path(folder) / "picks.json.minisig"
            sidecar.write_bytes(signature_bytes)
            status = verify_artifact(artifact, load_publisher_public_key(), sidecar)
    except Exception as error:  # noqa: BLE001 - verification must never crash a fetch
        return False, f"the signature could not be checked ({error})"
    if status.verified:
        return True, ""
    return False, status.error or "the signature did not match"


def load_bundled(path: Path | None = None) -> Catalogue:
    """The copy that ships with the app. Never raises; empty on any problem."""
    source = path or (Path(__file__).parent / "data" / "community_picks.json")
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Catalogue()
    try:
        return parse(document)
    except CommunityPicksError:
        return Catalogue()


__all__ = [
    "FORMAT",
    "KNOWN_TYPES",
    "MAX_AGE_SECONDS",
    "PICKS_SIGNATURE_URL",
    "PICKS_URL",
    "Catalogue",
    "Collection",
    "CommunityPicksError",
    "Pick",
    "load_bundled",
    "parse",
    "verify",
]
