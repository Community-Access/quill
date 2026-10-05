"""The one door the newer YouTube features go through to reach YouTube.

Search with types, a channel's live tab, My YouTube, comments and the new-video
check all ask yt-dlp for something and read back a dictionary. Each used to be
a candidate for its own ``YoutubeDL(...)`` block -- its own copy of the cache
folder, the quiet flags, the JavaScript runtime and now the sign-in -- and five
copies of a policy are five places for one to be forgotten. So they share this
module, and the network-egress inventory has one entry to review instead of
five.

Every call:

* refuses in Safe Mode, before yt-dlp is imported;
* carries the listener's sign-in when, and only when, they turned it on
  (:mod:`quill.core.radio.youtube_signin` -- a browser name or a file path,
  never a cookie value);
* reports any failure as :class:`YouTubeRequestError` with a sentence fit to
  speak, preferring the sign-in's own explanation when that is what broke.

``fetch`` parameters on the callers take the same ``(target, options)`` shape
as :func:`extract`, so tests hand in recorded dictionaries and nothing in the
test suite touches the network.

wx-free, strict-typed.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping

from quill.core.error_codes import CodedError

#: ``(target, extra_options) -> info dict``. What every caller injects in tests.
Fetch = Callable[[str, Mapping[str, object]], dict[str, object]]


class YouTubeRequestError(CodedError):
    """A YouTube request through yt-dlp failed, with a speakable reason."""

    code = "QUILL-RADIO-YOUTUBE-REQUEST"


def plain(error: BaseException) -> str:
    """The sentence an error carries, without the ``[QUILL-...]`` code prefix.

    ``str()`` of a coded error leads with its code, which is right in a log and
    noise in a spoken sentence.
    """
    if isinstance(error, CodedError) and error.args:
        return str(error.args[0])
    return str(error)


def refuse_in_safe_mode(safe_mode: bool = False) -> None:
    if safe_mode or os.environ.get("QUILL_SAFE_MODE") == "1":
        raise YouTubeRequestError("YouTube is not available in Safe Mode.")


def base_options() -> dict[str, object]:
    """The options every request shares, sign-in included when it is on."""
    from quill.core.js_runtime import yt_dlp_js_options
    from quill.core.paths import yt_dlp_cache_dir
    from quill.core.radio.youtube_signin import cookie_options

    options: dict[str, object] = {
        "cachedir": yt_dlp_cache_dir(),
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    options.update(yt_dlp_js_options())
    options.update(cookie_options())
    return options


def extract(target: str, options: Mapping[str, object]) -> dict[str, object]:
    """Ask yt-dlp about *target* with *options* on top of :func:`base_options`.

    The reviewed egress site (``network_egress_entries_radio``). Nothing is
    downloaded: ``skip_download`` is in the base and ``download=False`` here.
    """
    refuse_in_safe_mode()
    try:
        import yt_dlp
    except ImportError as error:
        raise YouTubeRequestError(
            "YouTube support is not installed. Station, Repair YouTube Support adds it."
        ) from error
    merged = base_options()
    merged.update(dict(options))
    try:
        with yt_dlp.YoutubeDL(merged) as ydl:
            info = ydl.extract_info(target, download=False)
    except Exception as error:  # noqa: BLE001 - yt-dlp raises many shapes
        raise YouTubeRequestError(speakable(error)) from error
    return info if isinstance(info, dict) else {}


def speakable(error: object) -> str:
    """One sentence for a yt-dlp failure. Never the raw traceback text."""
    from quill.core.radio.youtube_signin import describe_failure

    said = describe_failure(error)
    if said:
        return said
    text = str(error or "")
    lowered = text.lower()
    if "private" in lowered:
        return "That is private on YouTube, so it cannot be opened."
    if "unavailable" in lowered or "removed" in lowered or "does not exist" in lowered:
        return "YouTube says that is not available any more."
    if "comments are turned off" in lowered or "comments disabled" in lowered:
        return "Comments are turned off for that video."
    if "timed out" in lowered or "getaddrinfo" in lowered or "network" in lowered:
        return "YouTube could not be reached. Check your connection and try again."
    return "YouTube did not answer the way Quill Radio expected. Try again in a moment."


def run(
    target: str, options: Mapping[str, object], *, fetch: Fetch | None = None
) -> dict[str, object]:
    """:func:`extract`, or the injected *fetch* (tests), with one error shape."""
    if fetch is None:
        return extract(target, options)
    refuse_in_safe_mode()
    try:
        return fetch(target, options)
    except YouTubeRequestError:
        raise
    except Exception as error:  # noqa: BLE001 - same contract as extract
        raise YouTubeRequestError(speakable(error)) from error


__all__ = [
    "Fetch",
    "YouTubeRequestError",
    "base_options",
    "extract",
    "plain",
    "run",
    "speakable",
]
