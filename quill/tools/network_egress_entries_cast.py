"""QUILL Cast's reviewed outbound call sites for an episode's extras.

Split from :mod:`quill.tools.network_egress_entries` under GATE-11 -- extract,
never rebaseline -- on 2026-11-01, when Cast's pictures (codex.md 10B.5) gave
Cast a second fetch of something an episode merely points at. Both are one
file, fetched once, only when the person opens or asks about it: the
transcript, and a picture for the AI to describe. Feeds and downloads stay in
the main table.
"""

from __future__ import annotations

CAST_EXTRAS_EGRESS: dict[str, str] = {
    "core/podcasts/transcripts.py::_fetch_transcript_bytes": (
        "Single egress site for podcast transcripts: fetches one episode's "
        "Podcasting 2.0 transcript file (VTT/SRT/JSON, parsed locally, no "
        "further network activity) and caches the parsed text so reopening "
        "never re-fetches. Reached only when the user opens the transcript "
        "view for an episode that has a transcript_url. HTTPS-only over a "
        "verified TLS context with a bounded timeout and response size. "
        "Disabled in Safe Mode via refuse_in_safe_mode."
    ),
    "core/podcasts/picture_fetch.py::_fetch_picture_bytes": (
        "Single egress site for QUILL Cast's pictures (codex.md 10B.5): fetches "
        "one image whose address Cast already holds -- a podcast's or episode's "
        "artwork_url, or an <img> in the show notes -- only when the user runs "
        "Ask About an Image (Ctrl+Alt+F5) and chooses that picture. Never in the "
        "background and never cached to disk; the bytes are fitted locally by "
        "picture_prep and then go only to the AI connection the user chose. "
        "HTTPS or HTTP only over a verified TLS context, a bounded timeout and a "
        "20 MB cap. Refused in Safe Mode."
    ),
}
