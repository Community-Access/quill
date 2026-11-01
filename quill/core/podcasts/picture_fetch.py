"""One picture QUILL Cast already knows the address of, fetched only when asked.

Cast keeps a podcast's and an episode's artwork as an address
(``artwork_url``) and never downloads it: nothing in the app shows a picture.
Asking the AI about one (codex.md 10B.5, Cast's Ctrl+Alt+F5) is the one moment a
picture is wanted, so this is the one place it is fetched -- one image, on the
person's command, never in the background, never cached to disk -- and it then
goes through :mod:`quill.core.ai.picture_prep` to be fitted to the connection
before anything is sent. Show-note pictures are found the same way, from the
``<img>`` tags in the notes Cast already holds, with their own alt text kept,
because a show that wrote alt text has already answered the question for a
connection that cannot see.

wx-free and strict-typed. The fetch is a reviewed egress site
(``network_egress_entries.py``): HTTPS or HTTP only, a verified TLS context, a
bounded timeout and size, and refused in Safe Mode.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.podcasts import transport

__all__ = [
    "MAX_PICTURE_BYTES",
    "Picture",
    "PictureFetchError",
    "fetch_picture",
    "pictures_for",
    "show_note_pictures",
]

#: The largest picture fetched: the ChatGPT plan's own cap on one image part.
MAX_PICTURE_BYTES = 20 * 1024 * 1024
_TIMEOUT_SECONDS = 20.0
#: The most show-note pictures offered for one episode.
_MAX_NOTE_PICTURES = 12


class PictureFetchError(CodedError):
    """A picture could not be fetched, or Safe Mode refused it."""

    code = "QUILL-PODCASTS-PICTURE-FETCH"


@dataclass(frozen=True, slots=True)
class Picture:
    """One picture Cast can ask about: where it is, what to call it, its alt text."""

    label: str
    url: str
    alt: str = ""


class _ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        values = {name.lower(): (value or "") for name, value in attrs}
        src = values.get("src", "").strip()
        if src and transport.is_allowed(src):
            self.found.append((src, " ".join(values.get("alt", "").split())))


def show_note_pictures(html: str) -> list[tuple[str, str]]:
    """``(address, alt text)`` for each fetchable picture in show-notes HTML."""
    parser = _ImageParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:  # noqa: BLE001 - broken notes have no pictures we can trust
        return []
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for src, alt in parser.found:
        if src not in seen:
            seen.add(src)
            unique.append((src, alt))
    return unique[:_MAX_NOTE_PICTURES]


def pictures_for(
    *, episode_title: str, episode_art: str, show_title: str, show_art: str, notes_html: str
) -> list[Picture]:
    """Every picture Cast can offer for this episode, in the order it offers them."""
    pictures: list[Picture] = []
    if transport.is_allowed(episode_art):
        pictures.append(Picture(f"Episode artwork for {episode_title}", episode_art))
    if transport.is_allowed(show_art) and show_art != episode_art:
        pictures.append(Picture(f"Podcast artwork for {show_title}", show_art))
    for number, (src, alt) in enumerate(show_note_pictures(notes_html), start=1):
        name = f"Show-note picture {number}"
        pictures.append(Picture(f"{name}: {alt}" if alt else name, src, alt))
    return pictures


def _fetch_picture_bytes(url: str) -> bytes:
    """One GET returning the picture's bytes -- the reviewed egress site."""
    request = urllib.request.Request(url, headers={"User-Agent": http_client.podcast_user_agent()})
    try:
        with urllib.request.urlopen(  # noqa: S310 - scheme checked by the caller
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            payload: bytes = resp.read(MAX_PICTURE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise PictureFetchError(f"Could not fetch that picture: {error}") from error
    if len(payload) > MAX_PICTURE_BYTES:
        raise PictureFetchError("That picture is larger than 20 megabytes. Nothing was sent.")
    return payload


def fetch_picture(url: str, *, safe_mode: bool = False) -> bytes:
    """The bytes of the picture at *url*, fetched now because the person asked."""
    if safe_mode:
        raise PictureFetchError("Pictures are not fetched in Safe Mode. Nothing was sent.")
    if not transport.is_allowed(url):
        raise PictureFetchError("A picture address must start with https:// or http://.")
    return _fetch_picture_bytes(url)
