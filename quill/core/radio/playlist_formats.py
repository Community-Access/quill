"""The playlist formats the internet-radio world actually emits.

``playlist_import.py`` handles M3U, which covers a lot of the web and not the
part a listener most often has in hand. A "Listen Live" link is at least as
likely to be a ``.pls`` (the standard SHOUTcast and Icecast listen link), an
``.xspf`` (what Xiph's own directory serves, and we already integrate Xiph), or
an ``.asx`` (still in use by older US public radio and several radio reading
services -- squarely this app's audience).

Everything here is **pure**: text in, :class:`RadioStation` list out. No
network, no files, no wx, so every format is unit-tested against real-world
samples with nothing mocked.

Two things this module exists to get right:

**The M3U8 ambiguity.** A ``.m3u8`` file is either a playlist of stream URLs or
an HLS media manifest. They share an extension *and* a first line (``#EXTM3U``).
Handing an HLS manifest to the playlist importer yields a list of two-second
segment URLs presented to a listener as stations, which is a genuinely baffling
failure. :func:`classify_m3u` tells them apart before anything else happens.

**XML is parsed safely.** XSPF and ASX are XML from an untrusted source, so they
go through :func:`quill.core.safe_xml.fromstring`, which disables entity
expansion and external entities. A playlist is exactly the kind of small
attacker-supplied file that a billion-laughs payload arrives in.

Tolerance is the house style, per ``xiph.py`` and ``tunein.py``: a malformed
document degrades to fewer or zero stations, never to an exception reaching the
UI. The one exception is XML that is *hostile* rather than merely broken, which
is refused loudly.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse
from xml.etree.ElementTree import Element

from quill.core.error_codes import CodedError
from quill.core.radio.models import RadioStation
from quill.core.safe_xml import ParseError, UnsafeXMLError, fromstring

#: Schemes we will hand to a player. Everything else in a playlist -- a local
#: file path, an ``mms://`` URL for a protocol that died a decade ago -- is not
#: a station and is skipped rather than offered and then failing to play.
_PLAYABLE_SCHEMES = ("http://", "https://")

#: Any ``#EXT-X-`` tag marks an HLS manifest rather than a playlist of streams.
_HLS_TAG_RE = re.compile(r"^\s*#EXT-X-", re.MULTILINE)

#: ``FileN=<url>`` in a PLS ``[playlist]`` section; ``TitleN=`` names it.
_PLS_FILE_RE = re.compile(r"^\s*File(\d+)\s*=\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_PLS_TITLE_RE = re.compile(r"^\s*Title(\d+)\s*=\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

PlaylistKind = str  # "m3u" | "m3u8-hls" | "pls" | "xspf" | "asx" | "asf" | "b4s"
#                   | "wpl" | "shortcut" | "stream" | "unknown"


class PlaylistFormatError(CodedError):
    """A playlist document could not be parsed safely."""

    code = "QUILL-RADIO-PLAYLIST-FORMAT"


def _name_from_url(url: str) -> str:
    """A readable fallback station name from a stream URL -- its host.

    Same rule as ``playlist_import._name_from_url`` so an entry that arrives via
    PLS and the same entry via M3U get the same name.
    """
    host = urlparse(url).hostname or url
    return host[4:] if host.startswith("www.") else host


def _playable(url: str) -> bool:
    return url.lower().startswith(_PLAYABLE_SCHEMES)


def _stations(pairs: list[tuple[str, str]]) -> list[RadioStation]:
    """Build stations from ``(name, url)`` pairs, skipping unplayable entries
    and collapsing duplicate URLs (first name wins), as M3U import does."""
    stations: list[RadioStation] = []
    seen: set[str] = set()
    for name, url in pairs:
        cleaned = url.strip()
        if not _playable(cleaned) or cleaned in seen:
            continue
        seen.add(cleaned)
        stations.append(
            RadioStation(name=name.strip() or _name_from_url(cleaned), stream_url=cleaned)
        )
    return stations


# --- M3U8: playlist or HLS manifest? ----------------------------------------


def classify_m3u(text: str) -> str:
    """``"hls"`` or ``"playlist"`` for a ``.m3u``/``.m3u8`` document (pure).

    Any ``#EXT-X-`` tag means HLS: ``#EXT-X-STREAM-INF`` is a master playlist
    (still HLS -- the player follows it), ``#EXT-X-TARGETDURATION`` and
    ``#EXTINF`` with segment URIs are a media playlist. Absent any of them it is
    an ordinary playlist of stream URLs.

    Deliberately one-way: an HLS manifest must never be imported as a station
    list, so anything HLS-shaped is called HLS and handed to the player whole.
    """
    return "hls" if _HLS_TAG_RE.search(text or "") else "playlist"


def is_hls_manifest(text: str) -> bool:
    """True when *text* is an HLS manifest to hand to the player, not import."""
    return classify_m3u(text) == "hls"


# --- PLS ---------------------------------------------------------------------


def parse_pls(text: str) -> list[RadioStation]:
    """Parse a PLS (``[playlist]``) document (pure).

    PLS numbers its entries -- ``File1=``/``Title1=``, ``File2=``/``Title2=`` --
    and the numbers are not guaranteed contiguous or ordered in the file, so
    titles are matched to files by *number* rather than by position. An entry
    with no matching ``Title`` falls back to its host, as in M3U import.
    """
    titles = {index: value for index, value in _PLS_TITLE_RE.findall(text or "")}
    entries = [
        (int(index), titles.get(index, ""), url) for index, url in _PLS_FILE_RE.findall(text or "")
    ]
    entries.sort(key=lambda row: row[0])  # NumberOfEntries order, not file order
    return _stations([(name, url) for _index, name, url in entries])


# --- XSPF --------------------------------------------------------------------


def _local(tag: str) -> str:
    """An XML tag without its namespace: ``{ns}track`` -> ``track`` (pure)."""
    return tag.rsplit("}", 1)[-1].lower()


def _find_child_text(element: object, name: str) -> str:
    for child in element:  # type: ignore[attr-defined]
        if _local(child.tag) == name and child.text:
            return str(child.text).strip()
    return ""


def parse_xspf(text: str) -> list[RadioStation]:
    """Parse an XSPF (Xiph's own playlist format) document (pure and safe).

    XSPF is namespaced XML, and real files vary on whether they declare the
    namespace, so tags are matched on their local name. Each ``<track>``
    contributes its ``<location>`` as the stream and its ``<title>``, falling
    back to ``<creator>``, then to the host.

    Raises :class:`PlaylistFormatError` only for *hostile* XML (a DTD or entity
    payload); malformed-but-harmless XML yields an empty list, like every other
    parser here.
    """
    root = _parse_xml(text)
    if root is None:
        return []
    pairs: list[tuple[str, str]] = []
    for element in root.iter():
        if _local(element.tag) != "track":
            continue
        location = _find_child_text(element, "location")
        if not location:
            continue
        name = _find_child_text(element, "title") or _find_child_text(element, "creator")
        pairs.append((name, location))
    return _stations(pairs)


# --- ASX (and its WAX / WMX / WVX siblings) ----------------------------------


def parse_asx(text: str) -> list[RadioStation]:
    """Parse an ASX/WAX/WMX/WVX document (pure and safe).

    ASX is XML in name only: it is case-insensitive by convention (``<ASX>``,
    ``<Asx>``, ``<asx>``), routinely unclosed, and frequently not well-formed at
    all. So this tries the XML parser first and falls back to a regex sweep for
    ``<ref href="...">`` when the document will not parse -- which, for this
    format, is the common case rather than the exception.

    Entries are ``<entry>`` elements; each contributes its ``<ref href>`` and
    its ``<title>``. A bare ``<ref>`` outside any entry is still taken, because
    plenty of real reading-service ASX files are exactly that and nothing else.
    """
    root = _parse_xml(text, strict=False)
    pairs: list[tuple[str, str]] = []
    if root is not None:
        for element in root.iter():
            tag = _local(element.tag)
            if tag == "entry":
                title = _find_child_text(element, "title")
                for child in element.iter():
                    if _local(child.tag) == "ref":
                        href = _attr_ci(child, "href")
                        if href:
                            pairs.append((title, href))
            elif tag == "ref" and not _has_entry_parent(root, element):
                href = _attr_ci(element, "href")
                if href:
                    pairs.append(("", href))
    if not pairs:
        # Not well-formed, or well-formed with nothing we recognised: sweep for
        # href attributes on <ref> tags directly. ASX in the wild earns this.
        pairs = [
            ("", url)
            for url in re.findall(
                r"<\s*ref\b[^>]*\bhref\s*=\s*[\"']([^\"']+)[\"']", text or "", re.IGNORECASE
            )
        ]
    return _stations(pairs)


def _attr_ci(element: object, name: str) -> str:
    """An attribute value, matched case-insensitively (ASX uses ``HREF``)."""
    for key, value in element.attrib.items():  # type: ignore[attr-defined]
        if key.rsplit("}", 1)[-1].lower() == name:
            return str(value).strip()
    return ""


def _has_entry_parent(root: object, target: object) -> bool:
    """True when *target* sits inside an ``<entry>`` (ElementTree has no parent
    pointers, so this walks once; ASX files are small)."""
    for element in root.iter():  # type: ignore[attr-defined]
        if _local(element.tag) != "entry":
            continue
        for child in element.iter():
            if child is target:
                return True
    return False


def _parse_xml(text: str, *, strict: bool = True) -> Element | None:
    """Safely parse *text*, or return ``None`` when it is merely malformed.

    Hostile XML -- a DTD or entity payload -- raises
    :class:`PlaylistFormatError` when *strict*, because refusing loudly is the
    right answer to an attack and a silent empty list is not. ASX passes
    ``strict=False`` only so that its regex fallback still gets a turn.
    """
    if not (text or "").strip():
        return None
    try:
        return fromstring(text)
    except UnsafeXMLError as error:
        if strict:
            raise PlaylistFormatError(
                "That playlist file uses XML constructs QUILL refuses to expand "
                "(a DTD or custom entities). It was not opened."
            ) from error
        return None
    except (ParseError, ValueError):
        return None


# --- the long tail -----------------------------------------------------------
#
# Formats nobody would choose today and listeners still have in hand, catalogued
# by StreamTuner2 over a decade of pasted links (see radio2.md part IX). Each is
# a handful of lines, and each one turns "that link does nothing" into a
# station. They are deliberately grouped here rather than mixed in with the
# three formats that matter: this is the salvage yard, not the main road.

#: A one-URL INI file, in its three spellings: an ASF redirector's
#: ``[Reference] Ref1=``, a Windows ``[InternetShortcut] URL=``, and a
#: freedesktop ``[Desktop Entry] Link=``. All three are "here is an address",
#: written by three different decades.
_SHORTCUT_RE = re.compile(r"^\s*(?:Ref\d+|URL|Link)\s*=\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)
#: Winamp's B4S: ``<entry Playstring="http://...">`` with an optional ``<Name>``.
_B4S_ENTRY_RE = re.compile(r'<entry\b[^>]*\bPlaystring\s*=\s*"([^"]+)"', re.IGNORECASE)
_B4S_NAME_RE = re.compile(r"<Name>(.*?)</Name>", re.IGNORECASE | re.DOTALL)
#: Windows Media Player's WPL: ``<media src="http://..."/>``.
_WPL_MEDIA_RE = re.compile(r'<media\b[^>]*\bsrc\s*=\s*"([^"]+)"', re.IGNORECASE)


def parse_shortcut(text: str) -> list[RadioStation]:
    """Stations from an ASF redirector or a URL shortcut file (pure).

    ``Ref1=http://...`` in an ASF ``[Reference]`` file is the shape old Windows
    Media "listen live" links still arrive in, and the two shortcut formats are
    what a listener gets when a browser or a desktop saves a stream link as a
    file. An ``mmsh://`` reference -- ASF's own scheme wearing an http coat --
    is rewritten to ``http://``, which is what the address always was.
    """
    stations: list[tuple[str, str]] = []
    for raw in _SHORTCUT_RE.findall(text or ""):
        url = raw.strip()
        for scheme in ("mmsh://", "mms://"):
            if url.lower().startswith(scheme):
                url = "http://" + url[len(scheme) :]
                break
        stations.append(("", url))
    return _stations(stations)


def parse_b4s(text: str) -> list[RadioStation]:
    """Stations from a Winamp B4S playlist (pure)."""
    urls = _B4S_ENTRY_RE.findall(text or "")
    names = _B4S_NAME_RE.findall(text or "")
    pairs = [
        (names[index].strip() if index < len(names) else "", url) for index, url in enumerate(urls)
    ]
    return _stations(pairs)


def parse_wpl(text: str) -> list[RadioStation]:
    """Stations from a Windows Media Player WPL playlist (pure)."""
    return _stations([("", url) for url in _WPL_MEDIA_RE.findall(text or "")])


# --- sniffing ----------------------------------------------------------------

_PARSERS = {
    "pls": parse_pls,
    "xspf": parse_xspf,
    "asx": parse_asx,
    "asf": parse_shortcut,
    "shortcut": parse_shortcut,
    "b4s": parse_b4s,
    "wpl": parse_wpl,
}


def sniff(text: str, *, url: str = "", content_type: str = "") -> str:
    """What kind of document this is (pure), by the ladder radio2.md 3.4 sets.

    Content-Type, then extension, then the first bytes of the body, then
    ``"stream"`` for "hand it to the player and see". Body sniffing outranks a
    wrong extension on purpose: a server that names an HLS manifest ``.m3u`` is
    common, and believing the extension there is how segment URLs end up in a
    station list.
    """
    body = (text or "").lstrip()
    lowered_type = (content_type or "").split(";")[0].strip().lower()
    extension = (urlparse(url).path.rsplit(".", 1)[-1] if "." in urlparse(url).path else "").lower()

    # Body first for the M3U family, because the extension cannot resolve it.
    if body.startswith("#EXTM3U") or _HLS_TAG_RE.search(body):
        return "m3u8-hls" if classify_m3u(body) == "hls" else "m3u"
    if body[:20].lower().startswith("[playlist]"):
        return "pls"
    ini_head = body[:24].lower()
    if ini_head.startswith("[reference]"):
        return "asf"
    if ini_head.startswith("[internetshortcut]") or ini_head.startswith("[desktop entry]"):
        return "shortcut"
    if body.startswith("<") or body.startswith("<?"):
        head = body[:512].lower()
        # B4S and WPL are checked before the generic XML shapes: a WPL is a
        # <smil> document and a B4S contains <playlist>, so the broad tests
        # below would claim both of them.
        if "<winampxml" in head:
            return "b4s"
        if "<?wpl" in head or ("<smil" in head and "<media" in body[:2048].lower()):
            return "wpl"
        if "<playlist" in head or "xspf" in head:
            return "xspf"
        if "<asx" in head or "<ref" in head:
            return "asx"
    for candidate, marker in (
        ("pls", "scpls"),
        ("xspf", "xspf"),
        ("asx", "x-ms-asf"),
        ("m3u8-hls", "mpegurl"),
    ):
        if marker in lowered_type:
            return candidate
    if extension in ("pls", "xspf", "asx", "wax", "wmx", "wvx"):
        return "asx" if extension in ("wax", "wmx", "wvx") else extension
    if extension in ("m3u", "m3u8"):
        return "m3u8-hls" if classify_m3u(body) == "hls" else "m3u"
    return "stream" if not body or _playable(body.split("\n", 1)[0]) else "unknown"


def disagreements(text: str, *, url: str = "", content_type: str = "") -> list[str]:
    """Where the three signals about this document conflict (pure).

    A document announces what it is three times over -- its ``Content-Type``,
    its file extension, and its own first bytes -- and :func:`sniff` resolves
    the argument by ranking them. Ranking is the right behaviour and *silence*
    about the disagreement is not: "this link says it is a playlist and serves
    audio" is precisely the diagnosis a listener cannot make for themselves, and
    it is the difference between a station that will not play and a station that
    is already playing under a misleading name.

    StreamTuner2 logged this and did nothing else with it; here the notes are
    returned so Add Custom Station and the bad-station report can say them out
    loud. Empty means the three agreed, or said nothing.
    """
    body_kind = sniff(text, url="", content_type="")
    type_kind = sniff("", url="", content_type=content_type)
    ext_kind = sniff("", url=url, content_type="")
    notes: list[str] = []
    if type_kind not in ("stream", "unknown") and body_kind not in ("stream", "unknown"):
        if type_kind != body_kind:
            notes.append(
                f"The server calls this {type_kind}, but the file itself looks like {body_kind}."
            )
    if ext_kind not in ("stream", "unknown") and body_kind not in ("stream", "unknown"):
        if ext_kind != body_kind:
            notes.append(
                f"The address ends in .{ext_kind}, but the file itself looks like {body_kind}."
            )
    lowered_type = (content_type or "").split(";")[0].strip().lower()
    # ...but audio/x-scpls IS a playlist type, however much it starts with
    # "audio/", so this only fires when the MIME named no playlist kind at all.
    if (
        lowered_type.startswith("audio/")
        and type_kind in ("stream", "unknown")
        and body_kind not in ("stream", "unknown")
    ):
        notes.append(
            f"The server sends {lowered_type}, which is audio, but the file is a {body_kind} "
            "playlist."
        )
    return notes


def parse_playlist(text: str, *, url: str = "", content_type: str = "") -> list[RadioStation]:
    """Parse *text* as whatever kind of playlist it is (pure).

    Returns an empty list for an HLS manifest or a bare stream: those are not
    playlists and must be handed to the player whole. Use :func:`sniff` when the
    caller needs to say which of those happened -- and it should, because
    "that is an HLS stream, playing it" and "that playlist was empty" are very
    different things to hear.
    """
    kind = sniff(text, url=url, content_type=content_type)
    if kind == "m3u":
        from quill.core.radio.playlist_import import parse_m3u

        return parse_m3u(text)
    parser = _PARSERS.get(kind)
    return parser(text) if parser is not None else []


def spoken_sniff_result(kind: str, count: int) -> str:
    """What to say about a sniffed document (pure).

    Every outcome is spoken, per radio2.md 3.4: a sniffer that is right silently
    and wrong silently is worse than one that narrates.
    """
    if kind == "m3u8-hls":
        return "That is an HLS stream. Playing."
    if kind == "stream":
        return "That is a direct stream. Playing."
    if kind == "unknown":
        return "That does not look like a stream or a playlist. Trying it anyway."
    label = {
        "m3u": "playlist",
        "pls": "PLS playlist",
        "xspf": "XSPF playlist",
        "asx": "ASX playlist",
    }
    name = label.get(kind, "playlist")
    if count == 0:
        return f"That is a {name}, but it has no playable stations."
    if count == 1:
        return f"That is a {name} with 1 station."
    return f"That is a {name} with {count} stations."
