"""Live streaming to Icecast and SHOUTcast: settings, checks and commands (roadmap section 6).

Studio becomes a source client. What goes out is the **stream mix**: the
sources the presenter turned on for the stream, each at its own level, and
nothing else. The screen reader starts off and needs confirmation; Studio's
own cues can never be in it. Going live runs a spoken check first (MX-166).

Settings carry plain names first (``QUALITY_PRESETS``: Speech, Talk and
music, Music) with the technical choices under Custom. The password is never
part of these settings: it lives in Windows Credential Manager, keyed by
:func:`credential_name`, and is never written to logs or saved setups.

wx-free and network-free. Every command, URL and handshake line is built and
tested here; the platform layer opens the sockets.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal
from urllib.parse import quote, urlencode

from quill.core.demo_recording import Finding
from quill.core.error_codes import CodedError

ServerKind = Literal["icecast", "shoutcast"]
StreamFormat = Literal["mp3", "aac", "vorbis", "opus", "flac"]

#: format -> (plain name, FFmpeg encoder, container, content type)
FORMATS: dict[StreamFormat, tuple[str, str, str, str]] = {
    "mp3": ("MP3, plays everywhere", "libmp3lame", "mp3", "audio/mpeg"),
    "aac": ("AAC, better sound at the same size", "aac", "adts", "audio/aac"),
    "vorbis": ("Ogg Vorbis, open format", "libvorbis", "ogg", "application/ogg"),
    "opus": ("Ogg Opus, best for speech at low sizes", "libopus", "ogg", "audio/ogg"),
    "flac": ("FLAC in Ogg, lossless, needs a fast connection", "flac", "ogg", "audio/ogg"),
}
SHOUTCAST_FORMATS: tuple[StreamFormat, ...] = ("mp3", "aac")
BITRATES = (16, 24, 32, 48, 64, 96, 128, 160, 192, 256, 320)
SAMPLE_RATES = (22050, 32000, 44100, 48000)

#: Plain-word quality presets -> (format, kbit/s, channels, sample rate)
QUALITY_PRESETS: dict[str, tuple[str, StreamFormat, int, int, int]] = {
    "speech": ("Speech: smallest, clear voices", "mp3", 64, 1, 44100),
    "talk": ("Talk and music: a good balance", "mp3", 128, 2, 44100),
    "music": ("Music: best sound", "mp3", 192, 2, 44100),
    "custom": ("Custom: choose everything", "mp3", 128, 2, 44100),
}

#: Loudness targets in plain words -> integrated LUFS (None = leave the mix alone).
LOUDNESS: dict[str, tuple[str, float | None]] = {
    "off": ("Off: send the mix exactly as it is", None),
    "talk": ("Even, for talk (-16 LUFS)", -16.0),
    "music": ("Even, for music (-14 LUFS)", -14.0),
    "broadcast": ("Broadcast standard (-23 LUFS)", -23.0),
}


class StreamingError(CodedError):
    """A stream could not be set up, started or kept going."""

    code = "QUILL-STUDIO-STREAM-FAILED"


@dataclass(frozen=True)
class StreamSource:
    """One source's send to the stream: in or out, and its own level."""

    source_id: str
    label: str
    on: bool = False
    level_db: float = 0.0
    is_screen_reader: bool = False


@dataclass(frozen=True)
class StreamSettings:
    name: str = "My show"
    kind: ServerKind = "icecast"
    host: str = ""
    port: int = 8000
    mount: str = "/live"
    stream_id: int = 1
    user: str = "source"
    secure: bool = False
    title: str = ""
    description: str = ""
    genre: str = ""
    website: str = ""
    public: bool = False
    quality: str = "talk"
    format: StreamFormat = "mp3"
    bitrate: int = 128
    channels: int = 2
    sample_rate: int = 44100
    loudness: str = "off"
    archive: bool = False
    archive_folder: str = ""
    archive_format: Literal["same", "flac", "wav"] = "same"
    reconnect_tries: int = 10
    sources: tuple[StreamSource, ...] = field(default_factory=tuple)

    @property
    def effective(self) -> StreamSettings:
        """Settings with a non-custom preset applied."""
        if self.quality == "custom" or self.quality not in QUALITY_PRESETS:
            return self
        _label, fmt, rate, channels, sample_rate = QUALITY_PRESETS[self.quality]
        return replace(self, format=fmt, bitrate=rate, channels=channels, sample_rate=sample_rate)

    def enabled(self) -> tuple[StreamSource, ...]:
        return tuple(source for source in self.sources if source.on)


def credential_name(settings: StreamSettings) -> str:
    """Where the password lives in Windows Credential Manager, per server and mount."""
    where = settings.mount if settings.kind == "icecast" else f"sid{settings.stream_id}"
    return f"QUILL Studio stream {settings.host}:{settings.port} {where}"


def upload_kbps(settings: StreamSettings) -> int:
    effective = settings.effective
    if effective.format == "flac":
        return int(effective.sample_rate * 16 * effective.channels / 1000 * 0.6)
    return effective.bitrate


def validate(settings: StreamSettings) -> None:
    if not settings.host.strip() or "/" in settings.host or " " in settings.host:
        raise StreamingError("Type the server's address, such as stream.example.org.")
    if not 1 <= settings.port <= 65535:
        raise StreamingError("The port is a number from 1 to 65535.")
    effective = settings.effective
    if settings.kind == "icecast" and not re.fullmatch(r"/[\w.\-/]+", settings.mount):
        raise StreamingError("An Icecast mount starts with a slash, such as /live.")
    if settings.kind == "shoutcast" and effective.format not in SHOUTCAST_FORMATS:
        raise StreamingError("SHOUTcast takes MP3 or AAC. Choose one of those formats.")
    if effective.bitrate not in BITRATES:
        raise StreamingError("Choose a quality from the list.")
    if effective.channels not in (1, 2) or effective.sample_rate not in SAMPLE_RATES:
        raise StreamingError("Choose stereo or mono and a sample rate from the list.")


def preflight(settings: StreamSettings, *, password: str, measured_kbps: int = 0) -> list[Finding]:
    """Stops and Warns before going live (MX-166): where, what, and what is wrong."""
    findings: list[Finding] = []
    try:
        validate(settings)
    except StreamingError as error:
        findings.append(Finding("Stop", str(error)))
    if not password:
        findings.append(Finding("Stop", "No password is stored for this server."))
    on = settings.enabled()
    if not on:
        findings.append(
            Finding(
                "Stop", "No sound is turned on for the stream, so listeners would hear silence."
            )
        )
    if not any("microphone" in s.source_id for s in on):
        findings.append(Finding("Warn", "Your microphone is not in the stream."))
    if any(s.is_screen_reader for s in on):
        findings.append(
            Finding(
                "Warn",
                "Your screen reader's speech is in the stream: listeners hear everything it says.",
            )
        )
    if measured_kbps and upload_kbps(settings) > measured_kbps * 0.7:
        findings.append(
            Finding(
                "Warn",
                f"This quality needs about {upload_kbps(settings)} kilobits a second; the "
                f"connection measured about {measured_kbps}. Choose a lower quality.",
            )
        )
    if settings.archive and not settings.archive_folder:
        findings.append(Finding("Stop", "Choose a folder for the saved copy, or turn it off."))
    if not settings.archive:
        findings.append(Finding("Warn", "No copy of the show is being saved on this computer."))
    return findings


def summary(settings: StreamSettings, findings: Sequence[Finding]) -> str:
    effective = settings.effective
    where = (
        f"{settings.host}:{settings.port}{settings.mount}"
        if settings.kind == "icecast"
        else f"{settings.host}:{settings.port}, stream {settings.stream_id}"
    )
    label = FORMATS[effective.format][0].split(",", 1)[0]
    lines = [
        f"Going live on {'Icecast' if settings.kind == 'icecast' else 'SHOUTcast'} at {where}.",
        f"Show: {settings.title or settings.name}"
        + (", listed publicly." if settings.public else ", not listed publicly."),
        f"Sound: {label} at {effective.bitrate} kilobits a second, "
        f"{'stereo' if effective.channels == 2 else 'mono'}, {effective.sample_rate} hertz.",
        "In the stream: "
        + (", ".join(f"{s.label} ({s.level_db:+.0f} dB)" for s in settings.enabled()) or "nothing")
        + ".",
        "Saved copy: " + (f"on, in {settings.archive_folder}." if settings.archive else "off."),
    ]
    stops = [f for f in findings if f.severity == "Stop"]
    lines += [f"{f.severity}: {f.text}" for f in findings]
    lines.append(
        "Going live is blocked until every Stop is fixed."
        if stops
        else "Press Enter or Go live to start."
    )
    return "\n".join(lines)


def encode_args(settings: StreamSettings) -> list[str]:
    """FFmpeg arguments that encode the stream mix in the chosen format."""
    effective = settings.effective
    _label, encoder, container, _ctype = FORMATS[effective.format]
    args: list[str] = []
    target = LOUDNESS.get(settings.loudness, LOUDNESS["off"])[1]
    if target is not None:
        args += ["-af", f"loudnorm=I={target}:TP=-1.5:LRA=11,alimiter=limit=0.97"]
    args += ["-c:a", encoder, "-ar", str(effective.sample_rate), "-ac", str(effective.channels)]
    if effective.format != "flac":
        args += ["-b:a", f"{effective.bitrate}k"]
    args += ["-f", container]
    return args


def icecast_output(settings: StreamSettings, password: str) -> list[str]:
    """The Icecast output: options first, the URL last, the password as an option."""
    effective = settings.effective
    content_type = FORMATS[effective.format][3]
    url = f"icecast://{quote(settings.user)}@{settings.host}:{settings.port}{settings.mount}"
    return [
        "-content_type",
        content_type,
        "-ice_name",
        settings.title or settings.name,
        "-ice_description",
        settings.description,
        "-ice_genre",
        settings.genre,
        "-ice_url",
        settings.website,
        "-ice_public",
        "1" if settings.public else "0",
        "-tls",
        "1" if settings.secure else "0",
        "-password",
        password,
        url,
    ]


def stream_command(
    ffmpeg: str, settings: StreamSettings, password: str, *, archive_path: str = ""
) -> list[str]:
    """Raw 48 kHz stereo PCM on standard input becomes the encoded stream.

    Icecast is sent by FFmpeg itself; SHOUTcast's handshake FFmpeg cannot do, so
    for SHOUTcast the encoded bytes go to standard output for Studio's client.
    """
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-stats_period",
        "1",
        "-f",
        "s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-i",
        "pipe:0",
    ]
    command += encode_args(settings)
    if settings.kind == "icecast":
        command += icecast_output(settings, password)
    else:
        command += ["pipe:1"]
    if archive_path:
        command += ["-c:a", "flac" if archive_path.endswith(".flac") else "pcm_s16le"]
        command += ["-ar", "48000", "-ac", "2", archive_path]
    return command


def shoutcast_handshake(settings: StreamSettings, password: str) -> tuple[bytes, bytes]:
    """SHOUTcast source login: ``(password line, header block)``.

    DNAS 2 takes a legacy (v1) source when the password carries the stream
    number, ``password:#2``; DNAS 1 ignores the suffix for stream 1.
    """
    effective = settings.effective
    login = password if settings.stream_id == 1 else f"{password}:#{settings.stream_id}"
    content_type = "audio/mpeg" if effective.format == "mp3" else "audio/aacp"
    headers = [
        f"icy-name:{settings.title or settings.name}",
        f"icy-genre:{settings.genre}",
        f"icy-url:{settings.website}",
        f"icy-pub:{1 if settings.public else 0}",
        f"icy-br:{effective.bitrate}",
        f"content-type:{content_type}",
    ]
    return (login + "\r\n").encode("utf-8"), ("\r\n".join(headers) + "\r\n\r\n").encode("utf-8")


def shoutcast_source_port(settings: StreamSettings) -> int:
    """SHOUTcast v1 sources connect to the listener port plus one."""
    return settings.port + 1


def metadata_request(
    settings: StreamSettings, password: str, title: str
) -> tuple[str, dict[str, str]]:
    """``(url, headers)`` that set the now-playing title."""
    scheme = "https" if settings.secure else "http"
    base = f"{scheme}://{settings.host}:{settings.port}"
    if settings.kind == "icecast":
        query = urlencode({"mount": settings.mount, "mode": "updinfo", "song": title})
        token = base64.b64encode(f"{settings.user}:{password}".encode()).decode()
        return f"{base}/admin/metadata?{query}", {"Authorization": f"Basic {token}"}
    query = urlencode({
        "mode": "updinfo",
        "song": title,
        "pass": password,
        "sid": settings.stream_id,
    })
    return f"{base}/admin.cgi?{query}", {}


def settings_to_dict(settings: StreamSettings) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(settings)


def settings_from_dict(data: dict[str, Any]) -> StreamSettings:
    known = {k: v for k, v in data.items() if k in StreamSettings.__annotations__}
    known["sources"] = tuple(
        StreamSource(**{k: v for k, v in row.items() if k in StreamSource.__annotations__})
        for row in data.get("sources", [])
        if isinstance(row, dict)
    )
    return StreamSettings(**known)
