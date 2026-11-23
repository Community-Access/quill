"""What the Find Streams results list shows, in what order, and what it says.

Pure and wx-free, so every sentence and every order is tested without a window.
The dialog (``quill/ui/radio/link_finder_dialog.py``) asks this module which
rows to show; it never sorts or filters itself.

* **Four orders**: scan order, name A to Z, bitrate highest first, listeners
  most first (offered only when a row has a count). Unknowns always go last,
  and the groups stay as the scan made them -- live, then not checked, then
  audio files -- so "Live:" is still what each row starts with.
* **A filter** by format (only the formats present are offered) and "live
  streams only". A filter that would leave nothing is refused with one
  sentence and the list stays as it is: the list is never emptied by a filter.
* **Find**, which wraps, ignores case and accents, and reads the row's Stream,
  Link and Found by text.
* **Distinct row text**: rows that would read the same get " (host/path)", and
  rows still the same after that get " (link 2)".
* **Sentences**, each said once: what a sort, a filter, Select All, Add,
  Save and Copy did, always with the count.

Sorting, filtering, finding and acting on several rows at once are ideas from
Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift), written here
in QUILL's own code: StreamSift's seven orders are four here, few enough to
hold by ear.

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import unicodedata
import urllib.parse
from collections.abc import Sequence
from dataclasses import dataclass

from quill.core.net_public import host_is_refused
from quill.core.radio.find_streams_text import row_status
from quill.core.radio.page_links import PageStreamCandidate

__all__ = [
    "FORMATS",
    "ORDERS",
    "FindResult",
    "ViewState",
    "added_sentence",
    "copied_sentence",
    "distinct_rows",
    "empty_filter_sentence",
    "find",
    "format_of",
    "formats_present",
    "has_listeners",
    "order_sentence",
    "saved_sentence",
    "select_all_sentence",
    "server_to_scan",
    "shown_sentence",
    "visible",
]

SCAN, NAME, BITRATE, LISTENERS = "scan", "name", "bitrate", "listeners"
ORDERS = (SCAN, NAME, BITRATE, LISTENERS)
#: The formats the filter offers, in menu order. FLAC and WAV are rare enough
#: on a station's site that they are not offered; "All formats" still shows them.
FORMATS = ("MP3", "AAC", "Ogg", "HLS", "Opus")

_ORDER_SENTENCES = {
    SCAN: "Back in scan order.",
    NAME: "Sorted by name, A to Z.",
    BITRATE: "Sorted by bitrate, highest first.",
    LISTENERS: "Sorted by listeners, most first.",
}
_GROUP = {"live": 0, "not checked": 1, "": 1, "file": 2}
_LAST = 1 << 62


@dataclass(frozen=True, slots=True)
class ViewState:
    """How the list is shown: an order, a format ("" for all), live only."""

    order: str = SCAN
    format: str = ""
    live_only: bool = False

    @property
    def filtered(self) -> bool:
        return bool(self.format or self.live_only)


def _plural(count: int, one: str, many: str) -> str:
    return f"{count:,} {one if count == 1 else many}"


def format_of(candidate: PageStreamCandidate) -> str:
    """The filter's name for a row's format, or "" when it is not one offered."""
    codec = (candidate.codec or "").strip()
    if codec == "Ogg Opus":
        return "Opus"
    if codec.startswith("Ogg"):
        return "Ogg"
    return codec if codec in FORMATS else ""


def formats_present(candidates: Sequence[PageStreamCandidate]) -> list[str]:
    """The formats the filter may offer: only those some row has."""
    present = {format_of(c) for c in candidates}
    return [name for name in FORMATS if name in present]


def has_listeners(candidates: Sequence[PageStreamCandidate]) -> bool:
    return any(c.listeners is not None for c in candidates)


def _keeps(candidate: PageStreamCandidate, state: ViewState) -> bool:
    if state.live_only and candidate.check != "live":
        return False
    return not state.format or format_of(candidate) == state.format


def _name_key(candidate: PageStreamCandidate) -> str:
    return _fold(row_status(candidate).split(": ", 1)[-1])


def visible(candidates: Sequence[PageStreamCandidate], state: ViewState) -> list[int]:
    """Indexes into *candidates* of the rows shown, in the order shown.

    Sorting keeps the scan's groups (live, not checked, files); within a group
    the order is stable, so ties keep scan order, and unknowns go last.
    """
    shown = [i for i, c in enumerate(candidates) if _keeps(c, state)]
    order = state.order
    if order == LISTENERS and not has_listeners(candidates):
        order = SCAN

    def key(index: int) -> tuple[int, object]:
        candidate = candidates[index]
        group = _GROUP.get(candidate.check, 1)
        if order == NAME:
            return group, _name_key(candidate)
        if order == BITRATE:
            return group, -candidate.bitrate_kbps if candidate.bitrate_kbps else _LAST
        if order == LISTENERS:
            count = candidate.listeners
            return group, -count if count is not None else _LAST
        return group, index

    return sorted(shown, key=key) if order != SCAN else shown


def order_sentence(order: str) -> str:
    return _ORDER_SENTENCES.get(order, _ORDER_SENTENCES[SCAN])


def _filter_words(state: ViewState) -> str:
    """ "MP3 only", "live streams only", "live MP3 streams only"."""
    if state.live_only and state.format:
        return f"live {state.format} streams only"
    if state.live_only:
        return "live streams only"
    return f"{state.format} only"


def shown_sentence(shown: int, total: int, state: ViewState) -> str:
    """ "Showing 4 of 31 links: MP3 only." or "Showing all 31 links." """
    if not state.filtered:
        return f"Showing all {_plural(total, 'link', 'links')}."
    return f"Showing {shown:,} of {_plural(total, 'link', 'links')}: {_filter_words(state)}."


def empty_filter_sentence(state: ViewState) -> str:
    """Said instead of filtering to an empty list, which never happens."""
    if state.live_only and state.format:
        what = f"live {state.format} streams"
    elif state.live_only:
        what = "live streams"
    else:
        what = f"{state.format} streams"
    return f"No links are {what}, so the list is unchanged."


# -- distinct rows -------------------------------------------------------------


def _where(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = parts.path.rstrip("/")
    return f"{parts.netloc}{path}" if parts.netloc else url


def distinct_rows(candidates: Sequence[PageStreamCandidate]) -> list[str]:
    """Each row's Stream text, made unique: " (host/path)", then " (link N)"."""
    texts = [row_status(c) for c in candidates]
    seen: dict[str, int] = {}
    for text in texts:
        seen[text] = seen.get(text, 0) + 1
    out = [
        f"{text} ({_where(c.url)})" if seen[text] > 1 else text
        for text, c in zip(texts, candidates, strict=True)
    ]
    counts: dict[str, int] = {}
    for text in out:
        counts[text] = counts.get(text, 0) + 1
    numbered: dict[str, int] = {}
    final = []
    for text in out:
        if counts[text] > 1:
            numbered[text] = numbered.get(text, 0) + 1
            if numbered[text] > 1:
                text = f"{text} (link {numbered[text]})"
        final.append(text)
    return final


# -- find --------------------------------------------------------------------------


def _fold(text: str) -> str:
    """Case and accents ignored: "Écouter" finds "ecouter"."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def _haystack(candidate: PageStreamCandidate, row_text: str) -> str:
    return _fold(f"{row_text}\n{candidate.url}\n{candidate.reason}")


@dataclass(frozen=True, slots=True)
class FindResult:
    """Where Find landed (a position in the shown rows, or None) and what to say."""

    position: int | None
    sentence: str = ""


def find(
    candidates: Sequence[PageStreamCandidate],
    rows: Sequence[str],
    shown: Sequence[int],
    term: str,
    start: int,
    *,
    backwards: bool = False,
) -> FindResult:
    """The next shown row matching *term* after position *start* (wrapping).

    *rows* is each candidate's row text (by candidate index); *shown* the
    candidate indexes in display order. Wrapping is silent. "That is the only
    match." is said only when the one match is the row already focused.
    """
    needle = _fold(term.strip())
    if not needle:
        return FindResult(None)
    count = len(shown)
    matches = [
        pos
        for pos, index in enumerate(shown)
        if needle in _haystack(candidates[index], rows[index])
    ]
    if not matches:
        on_show = set(shown)
        hidden = sum(
            1
            for index, candidate in enumerate(candidates)
            if index not in on_show and needle in _haystack(candidate, rows[index])
        )
        quoted = term.strip()
        if hidden:
            noun = "link that does is" if hidden == 1 else "links that do are"
            return FindResult(
                None,
                f"Nothing shown matches '{quoted}'; {hidden:,} {noun} hidden by the filter.",
            )
        return FindResult(None, f"Nothing in the list matches '{quoted}'.")
    step = -1 if backwards else 1
    for offset in range(1, count + 1):
        pos = (start + step * offset) % count
        if pos in matches:
            if pos == start:
                return FindResult(pos, "That is the only match.")
            return FindResult(pos)
    return FindResult(matches[0])  # pragma: no cover - the loop always lands


# -- results of actions ----------------------------------------------------------


def select_all_sentence(already: bool, shown: int, total: int) -> str:
    """Ctrl+A: "Selected all 31 links." / "Selected all 4 links shown." """
    if shown < total:
        if already:
            return f"All {_plural(shown, 'link', 'links')} shown are already selected."
        return f"Selected all {_plural(shown, 'link', 'links')} shown."
    if already:
        return f"All {_plural(total, 'link', 'links')} are already selected."
    return f"Selected all {_plural(total, 'link', 'links')}."


def added_sentence(names: Sequence[str], added: int, already: int, folder: str = "") -> str:
    """After Add to Favorites, always with the count."""
    total = added + already
    if total == 1:
        if added:
            return f"Added {names[0]} to Favorites."
        return f"{names[0]} is already in your Favorites."
    if not added:
        return f"All {total:,} streams were already in your Favorites."
    where = f", in the folder {folder}" if folder else ""
    sentence = f"Added {_plural(added, 'stream', 'streams')} to Favorites{where}"
    if already:
        verb = "was" if already == 1 else "were"
        sentence += f"; {already:,} {verb} already there"
    return sentence + "."


def saved_sentence(count: int, file_name: str) -> str:
    return f"Saved {_plural(count, 'stream', 'streams')} to {file_name}."


def copied_sentence(count: int) -> str:
    return "Copied the stream link." if count == 1 else f"Copied {count:,} stream links."


# -- Scan This Stream's Server ----------------------------------------------------

#: Hosts that serve streams for others -- resolvers and CDNs -- whose root lists
#: nothing a listener could use, so the action is not offered for them.
_NOT_A_SERVER = (
    "streamtheworld.com",
    "tritondigital.com",
    "ihrhls.com",
    "iheart.com",
    "akamaihd.net",
    "akamaized.net",
    "cloudfront.net",
    "fastly.net",
    "radio.co",
    "zeno.fm",
    "tunein.com",
    "radiotime.com",
    "live365.com",
    "streamguys1.com",
    "googlevideo.com",
    "soundcloud.com",
    "securenetsystems.net",
)
#: Reasons that mean the row came from a server's own listing already.
_LISTED = ("listed by the", "Icecast status page")


def server_to_scan(candidate: PageStreamCandidate, page_url: str) -> str:
    """The stream server's root address to scan, or "" when it would add nothing.

    Not offered for the page's own host, for a host on this computer or the
    listener's own network (Find Streams reads only the public internet), for
    known resolver and CDN hosts, for HLS, or for a row a server listing
    already gave.
    """
    parts = urllib.parse.urlsplit(candidate.url)
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or not host or host_is_refused(host):
        return ""
    page_host = (urllib.parse.urlsplit(page_url).hostname or "").lower().removeprefix("www.")
    if host.removeprefix("www.") == page_host:
        return ""
    if any(host == known or host.endswith("." + known) for known in _NOT_A_SERVER):
        return ""
    if candidate.codec == "HLS" or parts.path.lower().endswith(".m3u8"):
        return ""
    if any(word in candidate.reason for word in _LISTED):
        return ""
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/", "", ""))
