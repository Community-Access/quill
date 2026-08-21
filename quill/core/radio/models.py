"""The ``RadioStation`` record shared by the RadioBrowser client, the
favorites store, and every UI surface (station browser, status bar, tray).

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _coerce_int(value: object, default: int = 0) -> int:
    """Best-effort ``int(value)`` for a loosely-typed JSON/dict field."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value)) if value.strip() else default
        except ValueError:
            return default
    return default


@dataclass(slots=True)
class RadioStation:
    """One station, as returned by RadioBrowser (or reconstructed from a
    saved favorite). ``stream_url`` is the resolved/best-guess playable URL;
    ``station_uuid`` is RadioBrowser's stable id, used for click-through vote
    counting and to de-duplicate favorites."""

    name: str
    stream_url: str
    station_uuid: str = ""
    homepage: str = ""
    favicon: str = ""
    country: str = ""
    language: str = ""
    tags: tuple[str, ...] = ()
    codec: str = ""
    bitrate_kbps: int = 0
    votes: int = 0
    #: Which directory this station came from ("iHeart", "TuneIn", "SomaFM",
    #: "ACB Media", "Website"), for the unified Find Stations source badge/filter.
    #: Empty means a Radio Browser result (it filters/labels under "Radio Browser")
    #: -- also the value for stations loaded before this field existed (back-compat).
    source: str = ""
    #: Other sources that also carried this exact station and were merged away
    #: as duplicates (see ``directory_search.merge_and_rank``). A search-only,
    #: transient field: it lets the Source filter still show a station under a
    #: directory it appeared in even when a different directory won the de-dup
    #: (e.g. a SomaFM channel RadioBrowser also lists). Not persisted, and
    #: excluded from equality so it never changes a station's identity.
    alt_sources: tuple[str, ...] = field(default=(), compare=False)
    #: True when this is a **finished recording** rather than a live stream: an
    #: audiobook chapter, an Archive item, a podcast episode. It is the one fact
    #: the transport cannot work out for itself at load time, and everything
    #: follows from it -- seeking, speed, position, chapters, and resuming where
    #: you stopped. Until Quill Radio 3.0 only a resolved YouTube video was ever
    #: treated as bounded, so a four-hour LibriVox chapter behaved like a live
    #: broadcast: no seek bar, no position, and no memory of where you were.
    is_recording: bool = False
    #: The publisher's own description of this recording -- a podcast episode's
    #: show notes, a book's synopsis -- already converted to plain text. The
    #: details panel had nothing to show for an episode but its address, which
    #: is the one fact a listener deciding whether to play it does not need
    #: (reported 2026-08-18). Transient and excluded from equality, exactly
    #: like ``alt_sources``: it describes a row, it does not identify one.
    notes: str = field(default="", compare=False)
    #: Radio Browser's own checker's verdict on this stream: True when it
    #: played, False when it did not, ``None`` when nobody published a check
    #: (every other directory, and any station saved before this field existed).
    #:
    #: The directory has always sent this on every search and Quill Radio threw
    #: it away, so a results list made the same silent promise for every row and
    #: the only way to find the dead ones was to press Enter on each in turn.
    #: Transient and excluded from equality exactly like ``alt_sources`` and
    #: ``notes``: it describes how a row is doing, it does not identify it --
    #: and a station whose check flips must not thereby become a different
    #: station to the favorites de-duplicator.
    #: See ``quill.core.radio.station_confidence`` for what is done with it.
    last_check_ok: bool | None = field(default=None, compare=False)

    @property
    def display_name(self) -> str:
        """The accessible list/row label: name plus country if known."""
        if self.country:
            return f"{self.name} ({self.country})"
        return self.name

    @property
    def details_text(self) -> str:
        """A read-only, multi-line summary for the station-details panel.

        Written to be *read down*, by a screen reader, in the order somebody
        actually wants it: what this is, who it is from, what it is about, and
        only then the machine facts. A podcast episode used to arrive here as
        its title, the word "Homepage" followed by an RSS address, and a stream
        address -- three lines, none of which answer "what is this episode?".
        """
        lines = [self.name]
        if self.source:
            lines.append(f"From: {self.source}")
        if self.country or self.language:
            where = ", ".join(part for part in (self.country, self.language) if part)
            lines.append(f"Location/language: {where}")
        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")
        if self.codec or self.bitrate_kbps:
            codec_bit = " ".join(
                part
                for part in (self.codec, f"{self.bitrate_kbps} kbps" if self.bitrate_kbps else "")
                if part
            )
            lines.append(f"Format: {codec_bit}")
        if self.votes:
            lines.append(f"Community votes: {self.votes}")
        if self.homepage:
            # A recording's "homepage" is the feed or collection it came out
            # of, and calling that a homepage is how this panel ended up
            # announcing an RSS address as though it were a website.
            lines.append(f"{'Feed' if self.is_recording else 'Homepage'}: {self.homepage}")
        lines.append(f"{'Audio' if self.is_recording else 'Stream URL'}: {self.stream_url}")
        if self.notes:
            # Last, and behind a blank line: show notes run to paragraphs, and
            # somebody who wants the address should not have to arrow through
            # an episode summary to reach it.
            lines.extend(["", "Notes:", self.notes])
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "stream_url": self.stream_url,
            "station_uuid": self.station_uuid,
            "homepage": self.homepage,
            "favicon": self.favicon,
            "country": self.country,
            "language": self.language,
            "tags": list(self.tags),
            "codec": self.codec,
            "bitrate_kbps": self.bitrate_kbps,
            "votes": self.votes,
            "is_recording": self.is_recording,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RadioStation | None:
        name = str(data.get("name", "")).strip()
        stream_url = str(data.get("stream_url", "")).strip()
        if not name or not stream_url:
            return None
        tags = data.get("tags")
        bitrate = _coerce_int(data.get("bitrate_kbps"))
        votes = _coerce_int(data.get("votes"))
        return cls(
            name=name,
            stream_url=stream_url,
            station_uuid=str(data.get("station_uuid", "")),
            homepage=str(data.get("homepage", "")),
            favicon=str(data.get("favicon", "")),
            country=str(data.get("country", "")),
            language=str(data.get("language", "")),
            tags=tuple(str(t) for t in tags) if isinstance(tags, list) else (),
            codec=str(data.get("codec", "")),
            bitrate_kbps=bitrate,
            votes=votes,
            # Absent in favorites saved before 3.0, which is correct: everything
            # saved before then was a live station.
            is_recording=bool(data.get("is_recording", False)),
        )
