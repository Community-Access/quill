"""Turn FFmpeg's last words into a sentence somebody can act on.

A failed conversion used to be reported as the last 300 characters of FFmpeg's
error stream -- "Stream map '0:V:0' matches no streams", "Error while opening
encoder for output stream #0:0 - maybe incorrect parameters such as bit_rate,
rate, width or height". Accurate, and useless read aloud. Each pattern below is
a failure the converter can actually produce, paired with what it means for
the file in front of you. The original text is kept after it, because support
still wants it.

Pure and wx-free.
"""

from __future__ import annotations

import re

#: (substring of FFmpeg's message, lowercased) -> what it means.
_EXPLANATIONS: tuple[tuple[str, str], ...] = (
    (
        "matches no streams",
        "The file has no track of the kind this format needs -- "
        "for example, a sound file cannot become a video",
    ),
    (
        "no such file or directory",
        "The file could not be found; it may have been moved, renamed or deleted",
    ),
    (
        "invalid data found when processing input",
        "The file is damaged, or is not really the kind of file its name says",
    ),
    ("permission denied", "Windows refused access to the file or the output folder"),
    ("no space left on device", "The output drive is full"),
    (
        "could not find tag for codec",
        "That combination of tracks cannot be copied "
        "into this container; choose a preset that converts rather than copies",
    ),
    (
        "codec not currently supported in container",
        "That combination of tracks "
        "cannot be copied into this container; choose a preset that converts rather "
        "than copies",
    ),
    (
        "error while opening encoder",
        "The chosen format could not accept this file's sound or picture settings",
    ),
    ("drm", "The file is copy-protected and cannot be converted"),
    ("encrypted", "The file is copy-protected and cannot be converted"),
    (
        "decoding requested, but no decoder found",
        "This file uses a codec the bundled FFmpeg cannot read",
    ),
    (
        "does not contain any stream",
        "The file has no sound track to convert -- for example, a video with no audio",
    ),
    ("no audio stream present", "The file has no sound track to convert"),
)


#: The "[mp2 @ 000002c4339bf440] " addresses FFmpeg prefixes its lines with.
_BRACKETS = re.compile(r"^(\[[^\]]*\]\s*)+")


_CAUSE = re.compile(
    r"not allowed|not supported|unsupported|invalid|error|no such|denied|matches no|"
    r"does not contain|no space|not found|could not|cannot|unable",
    re.IGNORECASE,
)


#: Decoder complaints about a damaged frame or two, which FFmpeg survives and
#: which are never why a conversion stopped.
_CHATTER = re.compile(
    r"error while decoding|concealing|non-existing pps|no frame|last message repeated|"
    r"decode_slice|corrupt(ed)? (input|frame|macroblock)",
    re.IGNORECASE,
)


def explain_failure(stderr: str) -> str:
    """A plain sentence for *stderr*, followed by FFmpeg's own last line."""
    text = (stderr or "").strip()
    lowered = text.lower()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # FFmpeg names the cause first and the consequences after it ("bitrate 192
    # is not allowed", then five lines of shutdown); the first line is the one
    # worth quoting.
    # The first line that names a problem is the cause; decoder chatter such as
    # "non-existing PPS 0 referenced" often comes before it and is not.
    flagged = [line for line in lines if _CAUSE.search(line) and not _CHATTER.search(line)]
    cause = _BRACKETS.sub("", (flagged or lines or [""])[0])
    for needle, meaning in _EXPLANATIONS:
        if needle in lowered:
            return f"{meaning}. (FFmpeg said: {cause[-200:]})" if cause else f"{meaning}."
    return cause[-300:] or "FFmpeg stopped without saying why."
