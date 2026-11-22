"""What Find Streams from a Website says about a checked scan (pure).

Two pieces of text, kept here so they are tested without wx:

* :func:`row_status` -- the first column of each row, which is what a screen
  reader reads first (and, in JAWS's first-column mode, only). So it carries
  the verdict *and* what tells two rows apart: "Live: WXYZ FM, MP3, 128 kbps",
  "Live: stream.example.org, AAC" when the stream sent no name, and "Not
  checked: it took too long to answer". A stream a server listed ends with its
  listener count: "Live: Capital UK, AAC, 48 kbps, 12 listeners".
* :func:`summary_sentence` -- the one sentence said when a scan finishes
  (FUX-04), in the same order as the list: live, then not checked, then audio
  files. Links proven not to be audio are mentioned only in the status label
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

from quill.core.radio.page_links import PageStreamCandidate

__all__ = ["failure_sentence", "row_status", "status_label", "summary_sentence"]


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _detail(candidate: PageStreamCandidate) -> str:
    name = candidate.stream_name or urllib.parse.urlsplit(candidate.url).hostname or ""
    parts = [name, candidate.codec]
    if candidate.bitrate_kbps:
        parts.append(f"{candidate.bitrate_kbps} kbps")
    if candidate.listeners is not None:
        # Last, after what tells two rows apart: only a server listing says it.
        parts.append(_plural(candidate.listeners, "listener", "listeners"))
    return ", ".join(part for part in parts if part)


def row_status(candidate: PageStreamCandidate) -> str:
    """The "Stream" column for one candidate."""
    if candidate.check == "live":
        return f"Live: {_detail(candidate)}"
    if candidate.check == "file":
        return f"Audio file, not a live stream: {_detail(candidate)}"
    if candidate.check == "not checked":
        note = candidate.check_note or "no answer"
        return f"Not checked: {note}"
    host = urllib.parse.urlsplit(candidate.url).hostname or candidate.url
    return f"Not checked: {host}"


def _counts(candidates: Sequence[PageStreamCandidate]) -> tuple[int, int, int]:
    live = sum(1 for c in candidates if c.check == "live")
    files = sum(1 for c in candidates if c.check == "file")
    return live, len(candidates) - live - files, files


def summary_sentence(
    candidates: Sequence[PageStreamCandidate], *, checked: bool, left_out: int = 0
) -> str:
    """The single sentence said when a scan finishes."""
    if not candidates:
        if checked and left_out:
            return (
                f"Found {_plural(left_out, 'link', 'links')} on that page, "
                f"but {'it was not' if left_out == 1 else 'none of them were'} audio."
            )
        return "No stream links were found on that page."
    if not checked:
        return f"Found {_plural(len(candidates), 'stream link', 'stream links')}."
    live, unchecked, files = _counts(candidates)
    if not live and not files:
        if unchecked == 1:
            return "Found 1 link; it could not be checked."
        return f"Found {unchecked} links; none could be checked."
    parts = []
    if live:
        parts.append(_plural(live, "live stream", "live streams"))
    if unchecked:
        parts.append(f"{unchecked} not checked")
    if files:
        parts.append(_plural(files, "audio file", "audio files"))
    if len(parts) == 1:
        joined = parts[0]
    else:
        joined = ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"Found {joined}."


def status_label(
    candidates: Sequence[PageStreamCandidate], *, checked: bool, left_out: int = 0
) -> str:
    """The status line: the spoken sentence, plus how many links were left out
    when there are rows (diagnostic, so shown but not spoken)."""
    sentence = summary_sentence(candidates, checked=checked, left_out=left_out)
    if candidates and left_out:
        noun = "link that was" if left_out == 1 else "links that were"
        return f"{sentence} Left out {left_out} {noun} not audio or no longer there."
    return sentence


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
    from quill.core.radio.link_finder import LinkFinderError

    cause = _root_cause(error)
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
