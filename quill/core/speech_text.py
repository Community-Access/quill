"""Speech-shaped text for the announcement path (assessment item 9, 5a.9/5a.10).

QUILL already normalizes text for *synthesis*: :mod:`quill.core.speech.text_normalize`
rewrites typography, phone numbers and URLs before a TTS engine sees them, and
:mod:`quill.core.punctuation_speech` verbalizes punctuation for Read Aloud. Neither
runs on the **announcement** path -- the strings QUILL hands to NVDA, JAWS or
Narrator through the announcement service.

That path carries a lot of text QUILL did not write: AI responses (Markdown),
Mastodon profiles (HTML), file names, and pasted fragments. Announced verbatim,
a Markdown response reads as "asterisk asterisk Important asterisk asterisk",
an HTML bio reads as its tags, and a run of decorative characters can stall a
synthesizer outright.

The three transformations here are deliberately *lossy in favour of listening*:

* :func:`strip_markdown_for_speech` -- remove syntax that carries no meaning
  when heard, keeping the words and the reading order.
* :func:`scrub_tts_hazards` -- neutralize the token shapes that make
  synthesizers stall, garble, or read forever (invisible and bidirectional
  controls, combining-mark stacks, long repeated runs, decorative box drawing).
* :func:`html_to_speech_text` -- flatten HTML to spoken text, including the
  Mastodon-specific ``<span class="invisible">`` convention that hides the
  scheme and tail of a link, so a URL is heard the way it is displayed.

:func:`prepare_for_speech` is the funnel that applies them in the right order.

A second group exists only because social text is *listened to* rather than
scanned. A sighted reader skips a row of leading @mentions and a decorated
display name in well under a second; a listener hears every one of them before
the first real word, spelled out in full:

* :func:`condense_leading_mentions` -- a pile of leading usernames becomes the
  first plus a count.
* :func:`strip_decorative_unicode` -- emoji go, accented letters stay.
* :func:`first_sentence` -- one sentence, for a summary that is spoken.
* :func:`format_relative_time` -- "3 minutes ago", not a timestamp.

Two duration formatters (5a.10) round the module out: durations are read one way
and pasted another, and every call site that reports one needs both.

wx-free, strict-typed, no I/O.
"""

from __future__ import annotations

import html as _html
import re
import unicodedata
from datetime import UTC, datetime
from html.parser import HTMLParser

__all__ = [
    "clock_duration",
    "condense_leading_mentions",
    "first_sentence",
    "format_relative_time",
    "html_to_speech_text",
    "prepare_for_speech",
    "scrub_tts_hazards",
    "speak_duration",
    "strip_decorative_unicode",
    "strip_markdown_for_speech",
]


# -- Markdown ----------------------------------------------------------------

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_ATX_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(?P<text>.*?)\s*#*\s*$")
_SETEXT_RULE = re.compile(r"^\s{0,3}(?:=+|-{2,})\s*$")
_THEMATIC_BREAK = re.compile(r"^\s{0,3}(?:\*\s*){3,}$|^\s{0,3}(?:-\s*){3,}$|^\s{0,3}(?:_\s*){3,}$")
_BLOCKQUOTE = re.compile(r"^\s{0,3}(?:>\s?)+")
_LIST_MARKER = re.compile(r"^(\s*)(?:[-*+]|\d{1,9}[.)])\s+")
_TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)*\|?\s*$")

_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\([^)]*\)")
_LINK = re.compile(r"\[(?P<label>[^\]]+)\]\([^)]*\)")
_AUTOLINK = re.compile(r"<((?:https?|mailto):[^>\s]+)>")
_INLINE_CODE = re.compile(r"`+([^`]+?)`+")
_STRONG = re.compile(r"(\*\*|__)(?P<text>\S(?:.*?\S)?)\1")
_EMPHASIS = re.compile(r"(?<![\w*_])([*_])(?P<text>[^*_\n]+?)\1(?![\w*_])")
_STRIKE = re.compile(r"~~(?P<text>\S(?:.*?\S)?)~~")


def _flatten_table_row(line: str) -> str:
    """Turn ``| a | b |`` into ``a, b`` so a table row reads as a sentence."""
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return ", ".join(cell for cell in cells if cell)


def strip_markdown_for_speech(text: str) -> str:
    """Reduce Markdown to the words a listener needs, in reading order.

    Headings keep their text (the screen reader's own heading cue is not
    available in an announcement, and speaking "hash hash" instead is strictly
    worse). Emphasis, inline code, strikethrough and link syntax collapse to
    their content; a link's *label* survives and its URL does not, because the
    label is what the author wrote for a human. Images become "image, <alt>" so
    a described image is still announced and an undescribed one is still
    counted. Fenced code blocks collapse to the words "code block" -- announcing
    forty lines of Python is never what a listener wanted from a status message.

    Unlike :func:`quill.core.text_utils.strip_md_to_plain`, which targets a
    ``wx.MessageDialog`` body and keeps heading underlines and link URLs for a
    *reader*, this is shaped for a *listener*: nothing decorative survives.
    """
    out: list[str] = []
    in_fence = False
    fenced_lines = 0
    for raw_line in text.splitlines():
        if _FENCE.match(raw_line):
            if in_fence:
                in_fence = False
                out.append("code block" if fenced_lines else "empty code block")
            else:
                in_fence = True
                fenced_lines = 0
            continue
        if in_fence:
            fenced_lines += 1
            continue

        line = raw_line
        if _THEMATIC_BREAK.match(line) or _SETEXT_RULE.match(line) or _TABLE_DIVIDER.match(line):
            continue
        heading = _ATX_HEADING.match(line)
        if heading:
            line = heading.group("text")
        line = _BLOCKQUOTE.sub("", line)
        line = _LIST_MARKER.sub(r"\1", line)
        if line.strip().startswith("|"):
            line = _flatten_table_row(line)
        out.append(line)

    if in_fence and fenced_lines:
        out.append("code block")

    result = "\n".join(out)
    result = _IMAGE.sub(lambda m: f"image, {m.group('alt')}" if m.group("alt") else "image", result)
    result = _LINK.sub(r"\g<label>", result)
    result = _AUTOLINK.sub(r"\1", result)
    result = _INLINE_CODE.sub(r"\1", result)
    result = _STRONG.sub(r"\g<text>", result)
    result = _STRIKE.sub(r"\g<text>", result)
    result = _EMPHASIS.sub(r"\g<text>", result)
    return _collapse_blank_lines(result)


def _collapse_blank_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    kept: list[str] = []
    for line in lines:
        if not line and (not kept or not kept[-1]):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


# -- TTS hazards -------------------------------------------------------------

#: Characters that are invisible on screen but are not ignored by every
#: synthesizer or screen reader: zero-width joiners and spaces, the
#: bidirectional embedding/override controls, the isolate controls, the word
#: joiner, and a stray byte-order mark. A bidi override in particular can
#: reverse the rest of an announcement.
_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿]")

#: Box drawing, block elements, geometric shapes and dingbat arrows. These are
#: decorative in the source and read as a long list of character names aloud.
_DECORATIVE = re.compile("[─-╿▀-▟■-◿➔-➿]+")

#: Any run of the same punctuation mark. Three is enough to convey emphasis and
#: short enough that no engine stalls on it.
_PUNCT_RUN = re.compile(r"([!?.,;:*#~_=+\-/\\|<>^\"'`])\1{2,}")

_WHITESPACE_RUN = re.compile(r"[^\S\n]{2,}")
_NEWLINE_RUN = re.compile(r"\n{3,}")

#: How many combining marks may follow one base character before the stack is
#: treated as decoration rather than as an accented letter. Real orthographies
#: stay well under this; "Zalgo" text stacks dozens and can hang a synthesizer.
_MAX_COMBINING_MARKS = 2

#: Longest unbroken run of non-space characters kept intact. Beyond this a token
#: is a hash, a base64 blob or a tracking URL, and reading it out is never
#: useful in an announcement.
_MAX_TOKEN_CHARS = 60


def _strip_combining_stacks(text: str) -> str:
    """Drop combining marks past :data:`_MAX_COMBINING_MARKS` per base character."""
    out: list[str] = []
    run = 0
    for ch in text:
        if unicodedata.combining(ch):
            run += 1
            if run > _MAX_COMBINING_MARKS:
                continue
        else:
            run = 0
        out.append(ch)
    return "".join(out)


def _shorten_long_tokens(text: str) -> str:
    def shorten(match: re.Match[str]) -> str:
        token = match.group(0)
        return token if len(token) <= _MAX_TOKEN_CHARS else token[:_MAX_TOKEN_CHARS] + "…"

    return re.sub(r"\S+", shorten, text)


def scrub_tts_hazards(text: str) -> str:
    """Neutralize the token shapes that stall or garble a synthesizer.

    Applied to any text QUILL did not author before it is announced. The passes,
    in order: strip invisible and bidirectional control characters; drop
    combining-mark stacks past a plausible accent depth; replace decorative box
    drawing with a space; collapse a repeated punctuation run to three; truncate
    an unbroken token longer than :data:`_MAX_TOKEN_CHARS`; and collapse runs of
    spaces and blank lines.

    Newlines survive -- they are how a listener hears structure, and the
    announcement sinks decide their own line handling.
    """
    result = _INVISIBLE.sub("", text)
    result = _strip_combining_stacks(result)
    result = _DECORATIVE.sub(" ", result)
    result = _PUNCT_RUN.sub(r"\1\1\1", result)
    result = _shorten_long_tokens(result)
    result = _WHITESPACE_RUN.sub(" ", result)
    result = _NEWLINE_RUN.sub("\n\n", result)
    return result.strip()


# -- HTML --------------------------------------------------------------------

_BLOCK_TAGS = frozenset({
    "p",
    "div",
    "li",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "pre",
})


class _SpeechHTMLParser(HTMLParser):
    """Flatten HTML to spoken text, honouring Mastodon's link conventions.

    Mastodon renders a link as three spans: ``invisible`` for the scheme,
    ``ellipsis`` for the visible head, and a second ``invisible`` for the tail.
    A naive tag strip therefore speaks the entire raw URL, including the parts
    the sender's client deliberately hid. Dropping the invisible spans makes the
    announcement match what a sighted user sees.

    Custom emoji arrive as ``<img class="custom-emoji" alt=":shortcode:">``; the
    alt text is the shortcode, which is the only speakable form available.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._invisible_depth = 0
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = ""
        alt = ""
        for name, value in attrs:
            if name == "class":
                classes = value or ""
            elif name == "alt":
                alt = value or ""
        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if tag == "span" and "invisible" in classes.split():
            self._invisible_depth += 1
            return
        if tag == "br":
            self._parts.append("\n")
            return
        if tag == "img":
            if alt:
                self._parts.append(alt)
            return
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "span" and self._invisible_depth:
            self._invisible_depth -= 1
            return
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._invisible_depth:
            return
        self._parts.append(data)

    @property
    def text(self) -> str:
        return "".join(self._parts)


def html_to_speech_text(markup: str) -> str:
    """Flatten *markup* to plain text shaped for listening.

    Block elements and ``<br>`` become line breaks; ``<script>`` and ``<style>``
    bodies are dropped; ``<img>`` contributes its alt text; and a
    ``<span class="invisible">`` -- Mastodon's hidden URL scheme and tail -- is
    omitted so a link is heard as it is displayed.

    Entities are decoded. Malformed markup degrades to a tag strip rather than
    raising: an announcement must never fail because a remote server sent bad
    HTML.
    """
    parser = _SpeechHTMLParser()
    try:
        parser.feed(markup)
        parser.close()
        text = parser.text
    except Exception:  # noqa: BLE001 - bad remote markup must not break an announcement
        text = _html.unescape(re.sub(r"<[^>]*>", " ", markup))
    text = _WHITESPACE_RUN.sub(" ", text)
    # One line per block, never a blank line between them: an announcement is a
    # message, not a document, and a closing tag followed by an opening one
    # would otherwise produce two breaks where a listener needs one.
    text = re.sub(r"[^\S\n]*\n[^\S\n]*(?:\n[^\S\n]*)*", "\n", text)
    return text.strip()


# -- social text: mentions, decoration, sentences, times ---------------------

#: Two or more @mentions at the very start of a post. One mention is address
#: information a listener needs; a run of them is a routing header.
_LEADING_MENTIONS = re.compile(r"\A((?:@\S+\s+){2,})(.*)\Z", re.DOTALL)
#: The remainder when a post is nothing *but* mentions, so the last one is
#: counted rather than left dangling as the whole "body".
_ONE_MENTION = re.compile(r"\A@\S+\Z")


def condense_leading_mentions(text: str) -> str:
    """Collapse a run of leading @mentions to the first plus a count.

    A reply that opens ``@alice @bob @carol Actually...`` is read by a screen
    reader as three usernames -- often letter by letter, since handles are rarely
    pronounceable -- before a single word of the message. Sighted readers skip
    that block; listeners cannot. Two or more leading mentions become
    ``@alice and 2 more``, which preserves who was addressed and how many
    without spending the opening of the message on it.

    A *single* leading mention is left alone: it is short, and in a direct reply
    it is the most important word in the post.
    """
    match = _LEADING_MENTIONS.match(text)
    if match is None:
        return text
    mentions = match.group(1).split()
    rest = match.group(2)
    tail = rest.strip()
    if tail and _ONE_MENTION.match(tail):
        # The whole post is mentions; count the last one instead of speaking it.
        mentions.append(tail)
        rest = ""
    hidden = len(mentions) - 1
    counted = "one" if hidden == 1 else str(hidden)
    condensed = f"{mentions[0]} and {counted} more"
    rest = rest.lstrip()
    return f"{condensed} {rest}" if rest else condensed


#: Unicode general categories that are decoration rather than language: other
#: symbols (emoji, pictographs, dingbats, flags), modifier symbols (skin-tone
#: modifiers), enclosing marks (the keycap ring), and lone surrogates / private
#: use characters, which no synthesizer can name usefully.
_DECORATIVE_CATEGORIES = frozenset({"Co", "Cs", "Me", "Sk", "So"})
#: The emoji zero-width joiner. It is invisible, but it is what turns a run of
#: separate pictographs into one sequence, so it goes with them.
_ZERO_WIDTH_JOINER = 0x200D


def _is_decorative(char: str) -> bool:
    code = ord(char)
    if code < 0x80:
        return False  # plain ASCII is never decoration
    if code == _ZERO_WIDTH_JOINER or 0xFE00 <= code <= 0xFE0F:
        return True  # ZWJ and the variation selectors that make emoji emoji
    return unicodedata.category(char) in _DECORATIVE_CATEGORIES


def strip_decorative_unicode(text: str) -> str:
    """Remove emoji and pictographs, keeping every character that is language.

    A screen reader announces an emoji by its full Unicode name, so a display
    name of ``Alice (she/her)`` with three emoji is heard as a sentence of
    character names before the actual name. This matters most in **names** --
    they are announced constantly, in every list row and every notification, and
    they are where decorated text actually collects.

    Accented Latin letters, non-Latin scripts, curly quotes, dashes, ellipses
    and currency signs all survive: they are how real text is written, and
    stripping them would corrupt names rather than clean them. Only the symbol
    and enclosing-mark categories go.

    A name that was *nothing but* emoji becomes empty, so callers should keep a
    fallback (a handle, an id) for that case.
    """
    kept = "".join("" if _is_decorative(char) else char for char in text)
    return _WHITESPACE_RUN.sub(" ", kept).strip()


#: A sentence terminator, plus any closing quotes or brackets that belong to it,
#: that is actually followed by a space or the end of the text. The lookahead is
#: what keeps "3.5" and "example.test/a" from being read as sentence ends.
_SENTENCE_END = re.compile(r"""[.!?]+["')\]}»”’]*(?=\s|\Z)""")

#: Words whose trailing period is an abbreviation, not a sentence end. Compared
#: case-insensitively against the word before the terminator.
_ABBREVIATIONS = frozenset({
    "dr",
    "e.g",
    "etc",
    "fig",
    "i.e",
    "jr",
    "mr",
    "mrs",
    "ms",
    # Deliberately not "no.": the word "no" ends a sentence far more often than
    # it abbreviates "number", and losing a real sentence break is the worse bug.
    "prof",
    "sr",
    "st",
    "vs",
})
_WORD_BEFORE = re.compile(r"([\w.]+)\Z")


def _is_abbreviation(text: str, dot: int) -> bool:
    word = _WORD_BEFORE.search(text[:dot])
    return word is not None and word.group(1).rstrip(".").lower() in _ABBREVIATIONS


def first_sentence(text: str) -> str:
    """Return the first sentence of *text*, for a summary that is spoken.

    A notification, a status line and a list row all get one spoken breath. The
    first sentence is almost always the part the author wrote to be read first,
    and truncating at a character count instead cuts words in half.

    A line break ends a sentence too -- a post whose first line has no full stop
    still has a first line, and that is the summary. Common abbreviations
    ("Dr.", "e.g.") do not end a sentence, and neither does a period inside a
    number or a URL. Text with no terminator at all is returned whole.
    """
    stripped = text.strip()
    if not stripped:
        return ""
    break_at = stripped.find("\n")
    for match in _SENTENCE_END.finditer(stripped):
        if _is_abbreviation(stripped, match.start()):
            continue
        end = match.end()
        if break_at != -1 and break_at < end:
            break
        return stripped[:end].strip()
    if break_at != -1:
        return stripped[:break_at].strip()
    return stripped


#: Seconds per unit, largest first. The month and year are the average Gregorian
#: lengths: a relative time is an approximation by definition, and "1 month ago"
#: is the right answer whether the month had 28 days or 31.
_RELATIVE_UNITS: tuple[tuple[int, str], ...] = (
    (31_556_952, "year"),
    (2_629_746, "month"),
    (604_800, "week"),
    (86_400, "day"),
    (3_600, "hour"),
    (60, "minute"),
    (1, "second"),
)
#: Below this many seconds in either direction, no number is worth speaking.
_JUST_NOW_SECONDS = 45


def _align_timezones(then: datetime, now: datetime) -> tuple[datetime, datetime]:
    """Make two datetimes comparable, assuming UTC for a naive one.

    Mastodon timestamps are timezone-aware; a caller's ``datetime.now()`` often
    is not. Subtracting the two raises, and a relative time is never worth an
    exception, so the naive side is read as UTC.
    """
    if (then.tzinfo is None) == (now.tzinfo is None):
        return then, now
    if then.tzinfo is None:
        return then.replace(tzinfo=UTC), now
    return then, now.replace(tzinfo=UTC)


def format_relative_time(then: datetime, now: datetime) -> str:
    """Describe *then* relative to *now*: "3 minutes ago", "in 2 hours".

    An absolute timestamp is read out as a string of numbers a listener then has
    to subtract from the current time in their head. A relative time is the
    answer they wanted. Both directions are handled, because a scheduled post
    and a published one appear in the same list.

    Anything inside three quarters of a minute either way is "just now": the
    exact count is noise at that range and changes between one announcement and
    the next.
    """
    then, now = _align_timezones(then, now)
    delta = (then - now).total_seconds()
    magnitude = abs(delta)
    if magnitude < _JUST_NOW_SECONDS:
        return "just now"
    for size, name in _RELATIVE_UNITS:
        if magnitude >= size:
            count = int(magnitude // size)
            unit = name if count == 1 else f"{name}s"
            break
    else:  # pragma: no cover - the ladder ends at 1 second, which always matches
        count, unit = int(magnitude), "seconds"
    return f"in {count} {unit}" if delta > 0 else f"{count} {unit} ago"


# -- the funnel --------------------------------------------------------------


def prepare_for_speech(text: str, *, markdown: bool = False, html: bool = False) -> str:
    """Shape *text* for announcement, applying the requested transformations.

    Order matters: HTML is flattened first (its entities may reveal Markdown or
    hazardous characters), Markdown syntax is removed next, and hazard scrubbing
    runs last so it sees the final character stream.

    With both flags false this is a hazard scrub alone -- the right default for
    any string QUILL did not author, such as a file name or a pasted fragment.
    """
    result = html_to_speech_text(text) if html else text
    if markdown:
        result = strip_markdown_for_speech(result)
    return scrub_tts_hazards(result)


# -- durations (5a.10) -------------------------------------------------------


def speak_duration(seconds: float) -> str:
    """A duration as it should be *heard*: "3 minutes 12 seconds".

    Zero and sub-second values round to "0 seconds" rather than vanishing, units
    are singular where the count is one, and a zero component is omitted unless
    it is the only one -- "1 hour 5 seconds", never "1 hour 0 minutes 5 seconds".
    """
    total = int(round(max(0.0, float(seconds))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
    if minutes:
        parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
    if secs or not parts:
        parts.append(f"{secs} second" + ("s" if secs != 1 else ""))
    return " ".join(parts)


def clock_duration(seconds: float) -> str:
    """A duration as it should be *pasted*: ``00:03:12``.

    Always hours:minutes:seconds, zero-padded, so pasted values sort and compare
    as strings. Durations past 99 hours widen the hour field rather than wrap.
    """
    total = int(round(max(0.0, float(seconds))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
