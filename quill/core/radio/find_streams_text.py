"""What Find Streams from a Website says about a checked scan (pure).

Two pieces of text, kept here so they are tested without wx:

* :func:`row_status` -- the first column of each row, which is what a screen
  reader reads first (and, in JAWS's first-column mode, only). So it carries
  the verdict *and* what tells two rows apart: "Live: WXYZ FM, MP3, 128 kbps",
  "Live: jazz on stream.example.org, AAC" when the stream sent no name, and
  "Not checked: Capital UK, there were too many links to check them all". A
  stream a server listed ends with its listener count: "Live: Capital UK, AAC,
  48 kbps, 12 listeners".
* :func:`summary_sentence` -- the one sentence said when a scan finishes
  (FUX-04), in the same order as the list: live, then not checked, then audio
  files, and, when the scan's own limits are why links went unchecked, why:
  "Found 12 live streams and 36 links not checked, because one scan checks at
  most 48 links." Links proven not to be audio are mentioned only in the status label
  while there are rows to read; when nothing is left, they are the result and
  are said.

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import socket
import ssl
import urllib.error
import urllib.parse
from collections.abc import Sequence

from quill.core.radio import live_check
from quill.core.radio.page_links import PageStreamCandidate

__all__ = [
    "NOT_PUBLIC_SENTENCE",
    "failure_sentence",
    "row_status",
    "status_label",
    "summary_sentence",
]

#: Find Streams reads only the public internet (quill.core.net_public); this
#: is what it says when the address typed, or one it led to, is not on it.
NOT_PUBLIC_SENTENCE = (
    "That address is on this computer or your own network, which Find Streams does not scan. "
    "To list a server on your network, add it under My Servers in Browse Stations."
)


def _plural(count: int, one: str, many: str) -> str:
    return f"{count:,} {one if count == 1 else many}"


def _name(candidate: PageStreamCandidate) -> str:
    """What tells this row from the others, best first: the name the stream
    sends; the station's name from the directory or server listing that found
    it; the address's last part on its host ("jazz on radio.example.org");
    the host alone."""
    if candidate.stream_name:
        return candidate.stream_name
    if candidate.label_is_name and candidate.label:
        return candidate.label
    parts = urllib.parse.urlsplit(candidate.url)
    host = parts.hostname or ""
    last = urllib.parse.unquote(parts.path.rstrip("/").rsplit("/", 1)[-1])
    last = " ".join(last.split())[:40]
    if last and host and last.isprintable():
        return f"{last} on {host}"
    return host or candidate.url


def _listeners(count: int) -> str:
    return "no listeners" if count == 0 else _plural(count, "listener", "listeners")


def _detail(candidate: PageStreamCandidate) -> str:
    parts = [_name(candidate), candidate.codec]
    if candidate.bitrate_kbps:
        parts.append(f"{candidate.bitrate_kbps} kbps")
    if candidate.listeners is not None:
        # Last, after what tells two rows apart: only a server listing says it.
        parts.append(_listeners(candidate.listeners))
    return ", ".join(part for part in parts if part)


def row_status(candidate: PageStreamCandidate) -> str:
    """The "Stream" column for one candidate."""
    if candidate.check == "live":
        return f"Live: {_detail(candidate)}"
    if candidate.check == "file":
        return f"Audio file, not a live stream: {_detail(candidate)}"
    if candidate.check == "not checked":
        note = candidate.check_note or "no answer"
        return f"Not checked: {_name(candidate)}, {note}"
    return f"Not checked: {_name(candidate)}"


def _counts(candidates: Sequence[PageStreamCandidate]) -> tuple[int, int, int]:
    live = sum(1 for c in candidates if c.check == "live")
    files = sum(1 for c in candidates if c.check == "file")
    return live, len(candidates) - live - files, files


def _because(candidates: Sequence[PageStreamCandidate], check_limit: int) -> str:
    """Why links were not checked, when it was the scan's own limits."""
    notes = {c.check_note for c in candidates if c.check == "not checked"}
    reasons = []
    if live_check.TOO_MANY in notes:
        reasons.append(f"one scan checks at most {check_limit or live_check.MAX_CHECKS} links")
    if live_check.OUT_OF_TIME in notes:
        reasons.append(f"checking stops after {live_check.TOTAL_SECONDS:g} seconds")
    return f", because {' and '.join(reasons)}" if reasons else ""


def summary_sentence(
    candidates: Sequence[PageStreamCandidate],
    *,
    checked: bool,
    left_out: int = 0,
    check_limit: int = 0,
    not_public: int = 0,
) -> str:
    """The single sentence said when a scan finishes.

    *left_out* links proved not to be audio; *not_public* links were on this
    computer or the listener's own network and were never read, so they are
    never called "not audio".
    """
    if not candidates:
        if checked and not_public and left_out:
            total = left_out + not_public
            was = "was" if left_out == 1 else "were"
            are = "is" if not_public == 1 else "are"
            return (
                f"Found {_plural(total, 'link', 'links')} on that page: {left_out:,} {was} "
                f"not audio, and {not_public:,} {are} on your own network, which Find "
                "Streams does not scan."
            )
        if checked and not_public:
            they = "it is" if not_public == 1 else "they are"
            return (
                f"Found {_plural(not_public, 'link', 'links')} on that page, but {they} on "
                "this computer or your own network, which Find Streams does not scan. To "
                "list a server on your network, add it under My Servers in Browse Stations."
            )
        if checked and left_out:
            return (
                f"Found {_plural(left_out, 'link', 'links')} on that page, "
                f"but {'it was not' if left_out == 1 else 'none of them were'} audio."
            )
        return "No stream links were found on that page."
    if not checked:
        return f"Found {_plural(len(candidates), 'stream link', 'stream links')}."
    live, unchecked, files = _counts(candidates)
    because = _because(candidates, check_limit)
    if not live and not files:
        if unchecked == 1:
            return f"Found 1 link; it could not be checked{because}."
        return f"Found {unchecked:,} links; none could be checked{because}."
    parts = []
    if live:
        parts.append(_plural(live, "live stream", "live streams"))
    if unchecked:
        parts.append(_plural(unchecked, "link", "links") + " not checked")
    if files:
        parts.append(_plural(files, "audio file", "audio files"))
    if len(parts) == 1:
        joined = parts[0]
    else:
        joined = ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"Found {joined}{because}."


def status_label(
    candidates: Sequence[PageStreamCandidate],
    *,
    checked: bool,
    left_out: int = 0,
    check_limit: int = 0,
    not_public: int = 0,
) -> str:
    """The status line: the spoken sentence, plus how many links were left out
    when there are rows (diagnostic, so shown but not spoken)."""
    sentence = summary_sentence(
        candidates,
        checked=checked,
        left_out=left_out,
        check_limit=check_limit,
        not_public=not_public,
    )
    if not candidates or not (left_out or not_public):
        return sentence
    local = f"{not_public:,} on your own network"
    if not left_out:
        noun = "link" if not_public == 1 else "links"
        return f"{sentence} Left out {not_public:,} {noun} on your own network."
    noun = "link that was" if left_out == 1 else "links that were"
    tail = f", and {local}" if not_public else ""
    return f"{sentence} Left out {left_out:,} {noun} not audio or no longer there{tail}."


def _root_cause(error: BaseException) -> BaseException:
    seen: BaseException = error
    while seen.__cause__ is not None and seen.__cause__ is not seen:
        seen = seen.__cause__
    return getattr(seen, "reason", seen) if not isinstance(seen, urllib.error.HTTPError) else seen


def failure_sentence(error: BaseException | None) -> str:
    """A failed scan in plain words -- never raw exception text, which is now
    spoken rather than merely shown."""
    if error is None:
        return "Could not scan that page."
    from quill.core.net_public import NotPublicAddress, RefusedAddress
    from quill.core.radio.link_finder import LinkFinderError

    cause = _root_cause(error)
    if isinstance(cause, NotPublicAddress):
        return NOT_PUBLIC_SENTENCE
    if isinstance(cause, RefusedAddress) and cause.args and isinstance(cause.args[0], str):
        return f"Could not scan that page. {cause.args[0]}"
    own = error.args[0] if error.args and isinstance(error.args[0], str) else ""
    if isinstance(error, LinkFinderError) and error.__cause__ is None and own:
        # A sentence QUILL wrote itself ("Type a website address to scan."),
        # without the support code str() puts in front of it.
        return own
    if isinstance(cause, urllib.error.HTTPError):
        return f"Could not scan that page: the website answered with an error ({cause.code})."
    if isinstance(cause, socket.gaierror):
        return "Could not scan that page: QUILL could not find that website."
    if isinstance(cause, TimeoutError):
        return "Could not scan that page: the website took too long to answer."
    if isinstance(cause, ConnectionRefusedError):
        return "Could not scan that page: the website refused the connection."
    if isinstance(cause, ssl.SSLError):
        return "Could not scan that page: its secure connection failed."
    return "Could not scan that page."
