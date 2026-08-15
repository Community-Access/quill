"""Picking a video's caption track out of what yt-dlp already answered with.

Extracted from ``youtube.py`` under GATE-11 (extract, never rebaseline). It is
one decision -- *which* of the caption tracks a video publishes is the one worth
having -- and it is worth its own module because the answer is opinionated in
two ways that matter to the person reading it.

**A human-written track beats an automatic one**, always, even when the
automatic one is in a language nearer the top of the list. Machine captions are
useful and they are not accurate, and a transcript is only as good as the words
in it.

**Only timed formats count.** ``json3``, ``srv*`` and ``vtt`` carry positions; a
plain text dump does not, and without positions a transcript cannot follow
playback, cannot be jumped into, and cannot say when a search hit was spoken --
which is most of the reason to have one.

wx-free, strict-typed, pure.
"""

from __future__ import annotations


def pick_caption_track(info: dict[str, object]) -> tuple[str, bool]:
    """The best timed caption track as ``(url, is_automatic)`` (pure).

    A human-written track is preferred over an automatic one, and English is
    preferred over other languages only as a tie-break -- a listener watching a
    French video wants the French captions. Returns ``("", False)`` when the
    video published none, which callers read as "no transcript available"
    rather than as an error.
    """
    for key, automatic in (("subtitles", False), ("automatic_captions", True)):
        tracks = info.get(key)
        if not isinstance(tracks, dict) or not tracks:
            continue
        languages = sorted(tracks, key=lambda code: (not str(code).startswith("en"), str(code)))
        for language in languages:
            formats = tracks.get(language)
            if not isinstance(formats, list):
                continue
            # Timed formats only: json3/srv*/vtt carry positions, and a plain
            # text dump would be useless for both seeking and segmentation.
            for wanted in ("vtt", "srt", "json3", "srv3", "srv1"):
                for entry in formats:
                    if not isinstance(entry, dict):
                        continue
                    if str(entry.get("ext", "")).lower() != wanted:
                        continue
                    url = str(entry.get("url", ""))
                    if url.startswith("https://"):
                        return url, automatic
    return "", False
