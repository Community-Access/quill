"""Described audio: finding the track that tells you what is happening on screen.

**This is the feature this application exists for**, and almost nothing else
offers it. A video's *described* audio track is a second narration mixed into the
programme that says what a sighted viewer can see -- who entered the room, what
the caption on screen reads, where the camera went. Broadcasters and streaming
services have published these for years. Desktop players either ignore them
entirely or bury them in a submenu of numbered "Track 2 / Track 3" entries that
tell a blind listener nothing at all about which one is which.

YouTube exposes multiple audio renditions on a growing number of videos, and
yt-dlp reports every one of them with its language code and a label. Some of
those are genuinely descriptive tracks. All this module does is read that list
honestly: name each track the way a person would say it, and work out which one
-- if any -- is the described one.

Three rules it keeps, and each of them is the difference between a feature and a
gesture:

* **Detection is a pure function with tests** (:func:`is_described`), so the
  heuristic can be improved as publishers change their labelling without
  touching a single line of UI.
* **A track is named, never numbered.** "English (described)" is useful;
  "Track 2" is a guess somebody has to make by listening.
* **Absence is reported, not hidden.** When a video has no described track, the
  command says exactly that rather than being greyed out. A disabled menu item
  teaches nothing; a menu item that explains itself teaches the listener
  something true about the video.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Markers that identify a rendition as descriptive. Publishers are not
#: consistent -- these are the forms actually seen in the wild, in labels, in
#: language tags, and in the role yt-dlp surfaces for DASH audio adaptation
#: sets. Matched case-insensitively against the label *and* the language code.
_DESCRIBED_MARKERS = (
    "audio_description",
    "audio description",
    "audiodescription",
    "descriptive",
    "description",
    "described",
    "-desc",
    "_desc",
    " ad)",
    "(ad)",
)

#: Language codes carry the descriptive marker as a subtag on some platforms:
#: BCP 47 allows ``en-x-description`` and broadcasters use it. Checked
#: separately so a language that merely *contains* one of the words above --
#: there is none today, and there could be tomorrow -- cannot be mistaken.
_DESCRIBED_SUBTAGS = ("x-description", "x-desc", "x-ad")


@dataclass(frozen=True, slots=True)
class AudioTrack:
    """One selectable audio rendition of a video.

    ``track_id`` is whatever the player uses to select it -- mpv's ``aid``, a
    yt-dlp format id -- and is opaque here on purpose: this module decides
    *which* track, and never *how* to play it.
    """

    track_id: str
    language: str = ""
    label: str = ""
    #: The address that plays *this* rendition. A described track is a separate
    #: stream, not a channel of one -- so selecting it is a reload, and this is
    #: what gets reloaded.
    stream_url: str = ""

    @property
    def is_described(self) -> bool:
        return is_described(self.label, self.language)

    @property
    def display_name(self) -> str:
        """The row a listener reads, as a sentence rather than a number."""
        return describe_track(self)


def is_described(label: str, language: str = "") -> bool:
    """Whether this rendition is a described (audio-description) track.

    Pure, and deliberately generous about *form* while strict about *meaning*:
    publishers write "English (Audio Description)", "en-US descriptive",
    "eng-desc" and "English AD", and all four mean the same thing to a listener
    who needs it.
    """
    haystack = f"{label} {language}".lower()
    if any(marker in haystack for marker in _DESCRIBED_MARKERS):
        return True
    code = language.lower()
    return any(subtag in code for subtag in _DESCRIBED_SUBTAGS)


def language_name(code: str) -> str:
    """A language code as a word, where it is one we can name.

    Only the common cases, and it falls back to the code itself rather than
    guessing: "und" spoken as a language name would be a fabrication, and an
    unfamiliar code shown as itself is honest and still useful.
    """
    base = (code or "").split("-", 1)[0].lower()
    return _LANGUAGE_NAMES.get(base, code or "Unknown")


_LANGUAGE_NAMES = {
    "ar": "Arabic",
    "bn": "Bangla",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fi": "Finnish",
    "fr": "French",
    "he": "Hebrew",
    "hi": "Hindi",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "ml": "Malayalam",
    "mr": "Marathi",
    "nl": "Dutch",
    "no": "Norwegian",
    "pa": "Punjabi",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sv": "Swedish",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
    "zh": "Chinese",
}


def describe_track(track: AudioTrack) -> str:
    """One audio track as a whole sentence: "English (described)".

    Never "Track 2". A numbered track list is unusable for the person this
    feature is for, because choosing between them means playing each in turn and
    listening for which one narrates.
    """
    name = language_name(track.language) if track.language else (track.label or "Audio")
    extra = track.label.strip()
    # A code the map cannot name is worth less than the track's own label: for
    # a language missing from the table, yt-dlp says "ta" and the publisher
    # says "Tamil", and the listener needs the word.
    if track.language and name == track.language and extra:
        name, extra = extra, ""
    if track.is_described:
        return f"{name} (described)"
    # A label that adds something the language does not -- "Original", "Dubbed"
    # -- is worth keeping; one that merely repeats the language, or that is
    # yt-dlp's own quality note, is noise. "English (medium)" tells a listener
    # nothing about which track to choose, which is the whole job of this row.
    # YouTube names a track "English original", so the language is said twice
    # unless the repeat is taken off the front: "English (English original)" is
    # a row nobody can read. Only at a word boundary -- "Tamil" also starts
    # with "ta", and stripping mid-word leaves "mil".
    if extra.lower() == name.lower():
        extra = ""
    elif extra.lower().startswith(name.lower() + " "):
        extra = extra[len(name) :].strip()
    # A region in brackets -- "English (US) original" -- is kept when it is the
    # only thing left distinguishing the row, because two tracks both reading
    # "English" is the numbered-track problem wearing a different hat, and
    # dropped when a real word follows it.
    region = ""
    if extra.startswith("(") and ")" in extra:
        region, extra = extra[1:].split(")", 1)
        extra = extra.strip()
    if not extra or extra.lower() in _QUALITY_NOTES:
        return f"{name} ({region.strip()})" if region.strip() else name
    if extra.lower() in {name.lower(), track.language.lower()}:
        return name
    return f"{name} ({extra})"


def track_name_from_note(note: str) -> str:
    """The *track's* name out of yt-dlp's ``format_note``, without the tier.

    This is the load-bearing parse in the module, so it is worth saying why it
    exists. yt-dlp does not fill in an ``audio_track`` dictionary for YouTube;
    it writes the track's own name into ``format_note`` alongside the encoding
    quality, joined with commas::

        "English original (default), low"
        "English descriptive, medium"

    Take the note whole and one track looks like several, because each bitrate
    is a separate row. Throw the note away and *several tracks look like one*,
    because a video's original and descriptive renditions share a language code
    -- which would lose the described track, in the feature that exists to find
    it. So: drop the quality tiers and the "(default)" marker, keep the name.
    """
    kept: list[str] = []
    for part in str(note or "").split(","):
        cleaned = " ".join(part.replace("(default)", "").split())
        if not cleaned or cleaned.lower() in _QUALITY_NOTES:
            continue
        # yt-dlp appends "MISSING POT" to formats served without a
        # proof-of-origin token. It is a delivery detail, not a track name --
        # and left in, it makes the same rendition from two player clients look
        # like two different tracks.
        if cleaned.lower() == "missing pot":
            continue
        kept.append(cleaned)
    return ", ".join(kept)


#: yt-dlp's own audio *quality* notes, which are not track names. Dropped from
#: the display so a row says what the track is rather than how it is encoded.
_QUALITY_NOTES = frozenset({
    "ultralow",
    "low",
    "medium",
    "high",
    "default",
    "original",
    "drc",
    "tiny",
})


def described_track(tracks: list[AudioTrack]) -> AudioTrack | None:
    """The described track among *tracks*, or ``None``.

    The first one wins where a video somehow publishes several, because a
    listener asking for described audio wants described audio, and choosing
    between two of them is a question nobody has ever wanted to be asked.
    """
    for track in tracks:
        if track.is_described:
            return track
    return None


def tracks_from_info(info: dict[str, object]) -> list[AudioTrack]:
    """Every audio rendition in a yt-dlp info dict (pure).

    Audio-only formats, deduplicated by language plus label, in yt-dlp's own
    order except that a described track is **not** promoted -- promotion is the
    preference's job, and doing it here would hide the ordinary track from
    somebody who did not ask.
    """
    formats = info.get("formats")
    if not isinstance(formats, list):
        return []
    seen: set[str] = set()
    tracks: list[AudioTrack] = []
    for entry in formats:
        if not isinstance(entry, dict):
            continue
        # Audio-only: a video rendition carries the same audio and would double
        # every row for no gain.
        if str(entry.get("vcodec", "none")).lower() != "none":
            continue
        if str(entry.get("acodec", "none")).lower() == "none":
            continue
        language = str(entry.get("language") or "")
        audio_track = entry.get("audio_track")
        audio_track = audio_track if isinstance(audio_track, dict) else {}
        # Where an extractor fills in ``audio_track`` -- some do -- that is the
        # track speaking for itself and is trusted first. YouTube does not, and
        # puts the name in ``format_note`` next to the quality tier, so the tier
        # is parsed off rather than either kept (one track looks like three) or
        # the whole note discarded (three tracks look like one). See
        # :func:`track_name_from_note`.
        label = str(audio_track.get("display_name") or "") or track_name_from_note(
            str(entry.get("format_note") or "")
        )
        # Identity is the track, not the rendition: language *and* name, because
        # a video's original and described renditions share a language code and
        # keying on language alone would silently drop the described one.
        key = str(audio_track.get("id") or "").lower() or f"{language}|{label}".lower()
        if key in seen:
            continue
        seen.add(key)
        tracks.append(
            AudioTrack(
                track_id=str(entry.get("format_id") or ""),
                language=language,
                label=label,
                stream_url=str(entry.get("url") or ""),
            )
        )
    return tracks


def summarise(tracks: list[AudioTrack]) -> str:
    """What to say when a listener asks for described audio and there is none.

    Names what the video *does* have, because "no described audio" alone leaves
    somebody wondering whether the feature or the video is at fault.
    """
    if not tracks:
        return "This video does not report its audio tracks, so described audio cannot be offered."
    if described_track(tracks) is not None:
        described = described_track(tracks)
        assert described is not None
        return f"Described audio is available: {described.display_name}."
    names = ", ".join(track.display_name for track in tracks)
    if len(tracks) == 1:
        return f"This video has one audio track, {names}. No described audio was published."
    return f"This video has {len(tracks)} audio tracks: {names}. No described audio was published."
