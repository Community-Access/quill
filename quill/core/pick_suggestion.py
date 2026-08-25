"""Suggesting a station or podcast for the Community Picks catalogue.

**Nobody should need a GitHub account to suggest a radio station.** Quill Radio
already files real GitHub issues for people who have configured nothing, using
the bundled issues-only token behind Report a Bug -- so a suggestion goes
straight from an accessible dialog to a real issue, with no login, no browser
and no form somebody else designed.

This module is the part with no wx and no network in it: checking what the
person typed, and composing an issue body a workflow can read back. Both the
in-app dialog and the public web form produce the **same body**, so
``picks-build.yml`` has one format to parse and the catalogue has one shape of
input however it arrived.

Design: docs/design/community-picks.md.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass, field

#: Where suggestions land, and the labels that drive the pipeline.
REPO = "Community-Access/quill"
SUGGESTION_LABEL = "pick:suggestion"
APPROVED_LABEL = "pick:approved"

#: The kinds somebody may suggest. Mirrors community_picks.KNOWN_TYPES; kept
#: separate so a client can offer fewer kinds than it can read.
SUGGESTABLE_TYPES = ("stream", "podcast")

#: Fenced and labelled so a workflow can find it without parsing prose, and a
#: human reading the issue can still see exactly what was submitted.
_BLOCK_START = "```json pick"
_BLOCK_END = "```"

_MAX_TITLE = 120
_MAX_DESCRIPTION = 600


@dataclass(frozen=True, slots=True)
class Suggestion:
    """One proposed catalogue entry, as typed."""

    type: str
    title: str
    url: str
    description: str = ""
    language: str = ""
    homepage: str = ""
    collection: str = ""
    why: str = ""

    @property
    def is_podcast(self) -> bool:
        return self.type == "podcast"


@dataclass(frozen=True, slots=True)
class Validation:
    """What is wrong, in words somebody can act on."""

    errors: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(suggestion: Suggestion, *, known_urls: set[str] | None = None) -> Validation:
    """Check a suggestion before it costs anybody anything.

    Catching a duplicate here costs one dialog; catching it after moderation
    costs a round trip through a person. Every message says what to do rather
    than what went wrong.
    """
    errors: list[str] = []
    if suggestion.type not in SUGGESTABLE_TYPES:
        errors.append("Choose whether this is a radio station or a podcast.")
    if not suggestion.title.strip():
        errors.append("Give it a name -- what would you call it in a list?")
    elif len(suggestion.title) > _MAX_TITLE:
        errors.append(f"The name is longer than {_MAX_TITLE} characters. Shorten it.")
    if len(suggestion.description) > _MAX_DESCRIPTION:
        errors.append(f"The description is longer than {_MAX_DESCRIPTION} characters. Shorten it.")

    url = suggestion.url.strip()
    if not url:
        errors.append(
            "Add the feed address." if suggestion.is_podcast else "Add the stream address."
        )
    elif not url.lower().startswith("https://"):
        errors.append(
            "The address must start with https:// -- a plain http address can be "
            "tampered with between the station and the listener."
        )
    elif " " in url:
        errors.append("The address has a space in it. Check it was pasted whole.")

    if known_urls and _normalise(url) in known_urls:
        errors.append("That one is already in the Community Picks list.")
    return Validation(tuple(errors))


def _normalise(url: str) -> str:
    """Compare addresses the way a human would: scheme and slash noise aside."""
    text = url.strip().lower().rstrip("/")
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    return text.removeprefix("www.")


def known_urls(catalogue: object) -> set[str]:
    """Every address the catalogue already offers, normalised for comparison."""
    picks = getattr(catalogue, "all_picks", ()) or ()
    return {
        _normalise(getattr(pick, "target", "")) for pick in picks if getattr(pick, "target", "")
    }


def issue_title(suggestion: Suggestion) -> str:
    kind = "Podcast" if suggestion.is_podcast else "Station"
    return f"[Pick] {kind}: {suggestion.title.strip()}"[:_MAX_TITLE]


def issue_body(suggestion: Suggestion, *, submitted_from: str = "") -> str:
    """The issue text: prose for a person, one JSON block for the workflow.

    Both, deliberately. A body only a machine can read makes moderation a
    guessing game; a body only a person can read makes the pipeline a
    transcription job.
    """
    payload = {
        "type": suggestion.type,
        "title": suggestion.title.strip(),
        "description": suggestion.description.strip(),
        "language": suggestion.language.strip(),
        "homepage": suggestion.homepage.strip(),
        "collection": suggestion.collection.strip(),
    }
    payload["feed_url" if suggestion.is_podcast else "stream_url"] = suggestion.url.strip()
    payload = {key: value for key, value in payload.items() if value}

    lines = [
        f"**{payload['title']}** -- suggested for the Community Picks list.",
        "",
        f"- Kind: {suggestion.type}",
        f"- Address: {suggestion.url.strip()}",
    ]
    if suggestion.description.strip():
        lines.append(f"- Description: {suggestion.description.strip()}")
    if suggestion.language.strip():
        lines.append(f"- Language: {suggestion.language.strip()}")
    if suggestion.collection.strip():
        lines.append(f"- Suggested group: {suggestion.collection.strip()}")
    if suggestion.why.strip():
        lines += ["", "Why it belongs:", "", suggestion.why.strip()]
    if submitted_from:
        lines += ["", f"_Submitted from {submitted_from}._"]
    lines += [
        "",
        "<!-- picks-build.yml reads the block below. Edit it, not the prose, "
        "to change what lands in the catalogue. -->",
        _BLOCK_START,
        json.dumps(payload, indent=2, ensure_ascii=False),
        _BLOCK_END,
    ]
    return "\n".join(lines)


def parse_issue_body(body: str) -> dict[str, str] | None:
    """Read back the JSON block. ``None`` when there is not exactly one.

    Used by the build workflow and by the review page. Refuses ambiguity: an
    issue somebody has edited into two blocks is one a person should look at,
    not one to guess about.
    """
    blocks = re.findall(
        re.escape(_BLOCK_START) + r"\s*(.*?)\s*" + re.escape(_BLOCK_END), body or "", re.S
    )
    if len(blocks) != 1:
        return None
    try:
        payload = json.loads(blocks[0])
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    return {str(key): str(value) for key, value in payload.items()}


def browser_url(suggestion: Suggestion) -> str:
    """A pre-filled new-issue URL, for when posting directly is not possible.

    The fallback, never the main path: it needs a GitHub account, which is the
    barrier this whole flow exists to remove.
    """
    query = urllib.parse.urlencode({
        "title": issue_title(suggestion),
        "body": issue_body(suggestion, submitted_from="the browser"),
        "labels": SUGGESTION_LABEL,
    })
    return f"https://github.com/{REPO}/issues/new?{query}"


__all__ = [
    "APPROVED_LABEL",
    "REPO",
    "SUGGESTABLE_TYPES",
    "SUGGESTION_LABEL",
    "Suggestion",
    "Validation",
    "browser_url",
    "issue_body",
    "issue_title",
    "known_urls",
    "parse_issue_body",
    "validate",
]
