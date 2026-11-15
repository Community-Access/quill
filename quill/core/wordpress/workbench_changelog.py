"""What changed in a plugin between the version a site has and the one waiting (PRD D3, WP-R-048).

WordPress.org's ``plugin_information`` answers with the plugin's readme
sections as HTML; its ``changelog`` section is what the author wrote about
each version. :func:`plain_text` turns that HTML into plain lines (headings
and list items on their own lines, no markup, no scripts, no links' targets),
:func:`entries` splits it into versions, :func:`skipped` keeps the versions
an update would bring, and :func:`summary` says it in one paragraph,
plainly naming security fixes, breaking changes and database updates when
the words are there. Nothing here asks anyone anything. Wx-free.
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence

__all__ = ["MAX_CHARS", "entries", "flags", "plain_text", "skipped", "skipped_text", "summary"]

#: The most of a changelog Read in Full shows; the rest is on WordPress.org.
MAX_CHARS = 3000

_DROP = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.S | re.I)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_BREAK = re.compile(
    r"<\s*(br|/p|/div|/h[1-6]|/li|/ul|/ol|/dd|/dt|p|div|h[1-6]|ul|ol)\b[^>]*>", re.I
)
_ITEM = re.compile(r"<\s*li\b[^>]*>", re.I)
_TAG = re.compile(r"<[^>]+>")
_VERSION = re.compile(r"^\s*(?:=+\s*)?(?:version\s+|v)?(\d+(?:\.\d+){1,3})\b", re.I)


def plain_text(markup: str) -> str:
    """*markup* as plain lines: block ends become line breaks, list items start with a hyphen."""
    text = _COMMENT.sub("", _DROP.sub("", markup or ""))
    text = _ITEM.sub("\n- ", text)
    text = _BREAK.sub("\n", text)
    text = html.unescape(_TAG.sub("", text))
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    out: list[str] = []
    for line in lines:
        if line and line != "-":
            out.append(line)
    return "\n".join(out)


def _parts(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version or ""))


def _newer(a: str, b: str) -> bool:
    """Whether version *a* is later than *b*."""
    x, y = _parts(a), _parts(b)
    width = max(len(x), len(y))
    return x + (0,) * (width - len(x)) > y + (0,) * (width - len(y))


def entries(text: str) -> list[tuple[str, str]]:
    """(version, what changed) for each version the plain changelog names, in its order."""
    found: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        match = _VERSION.match(line)
        if match and not line.lstrip().startswith("-") and len(line) < 80:
            found.append((match.group(1), []))
        elif found:
            found[-1][1].append(line)
    return [(version, "\n".join(body).strip()) for version, body in found]


def skipped(text: str, installed: str, latest: str) -> list[tuple[str, str]]:
    """The versions after *installed*, up to and including *latest*: what an update brings."""
    if not _parts(installed):
        return []
    return [
        (version, body)
        for version, body in entries(text)
        if _newer(version, installed) and not _newer(version, latest or version)
    ]


_FLAGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("security fixes", ("security", "vulnerab", "xss", "csrf", "injection", "cve-", "exploit")),
    (
        "breaking changes",
        ("breaking", "backward incompatible", "backwards incompatible", "no longer support",
         "removed support", "requires php", "requires wordpress", "deprecated"),
    ),
    ("a database update", ("database", "db update", "migration", "schema", "upgrade routine")),
)  # fmt: skip


def flags(text: str) -> list[str]:
    """Which of security fixes, breaking changes and a database update *text* mentions."""
    lowered = (text or "").casefold()
    return [name for name, words in _FLAGS if any(word in lowered for word in words)]


def summary(name: str, text: str, installed: str, latest: str) -> str:
    """What updating *name* from *installed* to *latest* brings, in plain words."""
    if not text.strip():
        return f"WordPress.org has no changelog for {name}."
    brought = skipped(text, installed, latest)
    if not brought:
        return (
            f"{name}'s changelog does not name the versions between {installed or 'yours'} and "
            f"{latest}; Read in Full shows what it says."
        )
    versions = [version for version, _body in brought]
    joined = "\n".join(body for _version, body in brought)
    count = len(versions)
    said = (
        f"What changed in {name}: {count} version{'s' if count != 1 else ''} after "
        f"{installed} ({', '.join(versions[:8])}{' and more' if count > 8 else ''})."
    )
    found = flags(joined)
    if found:
        said += " The changelog mentions " + _and(found) + "."
        if "a database update" in found:
            said += " Back up the site first: a database update cannot be undone by deactivating."
    else:
        said += " It does not mention security, breaking changes or a database update."
    return said


def _and(words: Sequence[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def skipped_text(text: str, installed: str, latest: str) -> str:
    """The skipped versions' own words, for Read in Full, at most :data:`MAX_CHARS`."""
    brought = skipped(text, installed, latest)
    body = "\n\n".join(f"Version {version}:\n{words}" for version, words in brought)
    body = body or text
    return body if len(body) <= MAX_CHARS else body[:MAX_CHARS].rstrip() + " ..."
