"""The ``RadioStation`` record shared by the RadioBrowser client, the
favorites store, and every UI surface (station browser, status bar, tray).

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass


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

    @property
    def display_name(self) -> str:
        """The accessible list/row label: name plus country if known."""
        if self.country:
            return f"{self.name} ({self.country})"
        return self.name

    @property
    def details_text(self) -> str:
        """A read-only, multi-line summary for the station-details panel."""
        lines = [self.name]
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
            lines.append(f"Homepage: {self.homepage}")
        lines.append(f"Stream URL: {self.stream_url}")
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
        )
