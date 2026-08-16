"""Project Gutenberg audiobooks via Gutendex -- keyless, and it complements
LibriVox rather than duplicating it.

Gutendex is an open, keyless index of Project Gutenberg. Most of what it lists
is text, but 1,124 of its records carry audio (measured 2026-08-13), and those
are human-read recordings that are not all in LibriVox.

Two operational facts, both learned by probing rather than by reading docs, and
both of which shape the code below:

* **``mime_type`` is a prefix match, and it lies a little.** Asking for
  ``audio/mpeg`` returns books whose only audio format is ``audio/ogg``. So the
  adapter reads the whole ``formats`` map and picks by its own preference order
  instead of trusting the mime it asked for.
* **Use the specific form.** ``mime_type=audio`` -- the bare prefix -- took
  **32.9 seconds**; ``audio/mpeg`` takes about 150 ms for the same shape of
  answer. The specific one is not an optimisation, it is the difference between
  a usable browse node and one that looks broken.

Gutendex is a small free service that timed out three times on one run and
answered instantly on the next, so it gets a real timeout and its results are
cached. It also returns HTTP 403 to an anonymous fetcher and 200 to a
descriptive one, which is why the User-Agent here is not optional.

One reviewed egress site (:func:`_fetch`), HTTPS-only over a verified TLS
context, Safe Mode gated, wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

_USER_AGENT = f"QUILL-Radio/{__version__} (+https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 30.0
_MAX_BYTES = 4_000_000
_BASE = "https://gutendex.com/books"
_MAX_AGE_SECONDS = 7 * 24 * 3600

#: The specific mime to filter on. See the module docstring: the bare prefix
#: form is two hundred times slower for the same answer.
AUDIO_MIME = "audio/mpeg"

#: Audio formats we will play, most preferred first. Gutenberg's audio is mostly
#: MP3 and Ogg, and a record often carries only one of them.
_AUDIO_PREFERENCE = ("audio/mpeg", "audio/ogg", "audio/mp4", "audio/x-wav")

#: Browse shelves. Gutendex's ``topic`` matches subjects and bookshelves, so
#: these are ordinary search terms rather than an enumerated taxonomy -- there
#: is no topic-list endpoint to fetch.
BROWSE_TOPICS: tuple[tuple[str, str], ...] = (
    ("fiction", "Fiction"),
    ("children", "Children's Books"),
    ("poetry", "Poetry"),
    ("adventure", "Adventure"),
    ("detective", "Detective & Mystery"),
    ("science fiction", "Science Fiction"),
    ("history", "History"),
    ("biography", "Biography"),
    ("philosophy", "Philosophy"),
    ("humor", "Humour"),
    ("drama", "Plays & Drama"),
    ("short stories", "Short Stories"),
)

#: Languages worth offering. Gutendex takes two-letter codes.
BROWSE_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("fr", "French"),
    ("de", "German"),
    ("es", "Spanish"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("nl", "Dutch"),
    ("fi", "Finnish"),
)


class GutendexError(CodedError):
    """A Gutendex request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-GUTENDEX-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`GutendexError` when Safe Mode is active."""
    if safe_mode:
        raise GutendexError(
            "Project Gutenberg audiobooks are disabled in Safe Mode. "
            "Restart QUILL normally to browse them."
        )


def _fetch(url: str) -> str:
    """One HTTPS GET of Gutendex -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise GutendexError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (
        urllib.error.URLError,
        TimeoutError,
        ssl.SSLError,
        OSError,
        # LineTooLong and friends are HTTPException, NOT OSError -- ccMixter
        # echoes a >64 KB HTTP header at larger page sizes, and without this
        # the exception escaped as an unhandled type and the branch went
        # silently empty instead of saying it could not load.
        http.client.HTTPException,
    ) as error:
        raise GutendexError(f"Could not reach Project Gutenberg: {error}") from error
    return payload.decode("utf-8", errors="replace")


def parse_books(json_text: str) -> list[RadioStation]:
    """Gutendex records into playable audiobook rows (pure).

    A record's ``formats`` map is read in full and the best audio format chosen
    from it -- never the mime that was asked for, which may not be the one the
    record actually carries. A record with no audio at all is dropped, so the
    branch never offers a book with nothing to play.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    results = data.get("results") if isinstance(data, dict) else None
    books: list[RadioStation] = []
    for book in results if isinstance(results, list) else []:
        if not isinstance(book, dict):
            continue
        title = str(book.get("title", "")).strip()
        formats = book.get("formats")
        if not title or not isinstance(formats, dict):
            continue
        audio = ""
        for mime in _AUDIO_PREFERENCE:
            for key, value in formats.items():
                if str(key).lower().startswith(mime) and str(value).startswith("http"):
                    audio = str(value)
                    break
            if audio:
                break
        if not audio:
            continue
        authors = ", ".join(
            str(a.get("name", "")).strip()
            for a in book.get("authors", []) or []
            if isinstance(a, dict) and a.get("name")
        )
        books.append(
            RadioStation(
                name=f"{title} -- {authors}" if authors else title,
                stream_url=audio,
                homepage=str(formats.get("text/html", "") or ""),
                tags=("Public domain",),
                source="Project Gutenberg",
                is_recording=True,
            )
        )
    return books


def audiobooks(
    *,
    query: str = "",
    topic: str = "",
    language: str = "",
    limit: int = 60,
    page: int = 1,
    safe_mode: bool = False,
    refresh: bool = False,
) -> list[RadioStation]:
    """Audiobooks, optionally narrowed by *query*, *topic* and/or *language*.

    *query* is Gutendex's own ``search`` parameter (author and title), which is
    what lets federated search reach Gutenberg's human-read recordings without a
    second endpoint or a second egress site.
    """
    refuse_in_safe_mode(safe_mode)
    params: dict[str, str] = {"mime_type": AUDIO_MIME}
    if query.strip():
        params["search"] = query.strip()
    if topic.strip():
        params["topic"] = topic.strip()
    if language.strip():
        params["languages"] = language.strip()
    if page > 1:
        params["page"] = str(int(page))
    url = f"{_BASE}?{urllib.parse.urlencode(params)}"
    key = (
        f"gutendex:{query.strip().lower()}:{topic.strip().lower()}"
        f":{language.strip().lower()}:{int(page)}"
    )
    payload, _age = directory_cache.resolve(
        key,
        lambda: [
            {"name": s.name, "url": s.stream_url, "home": s.homepage}
            for s in parse_books(_fetch(url))[: max(1, limit)]
        ],
        max_age_seconds=_MAX_AGE_SECONDS,
        refresh=refresh,
        empty=[],
    )
    return [
        RadioStation(
            name=str(row.get("name", "")),
            stream_url=str(row.get("url", "")),
            homepage=str(row.get("home", "")),
            tags=("Public domain",),
            source="Project Gutenberg",
            is_recording=True,
        )
        for row in payload
        if isinstance(row, dict) and row.get("name") and row.get("url")
    ]
