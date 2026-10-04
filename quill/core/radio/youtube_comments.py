"""A YouTube video's comments, as rows a screen reader can read.

yt-dlp fetches a video's comments when asked (``getcomments``), capped by the
``max_comments`` extractor argument and ordered by ``comment_sort`` -- ``top``
or ``new``, the same two orders YouTube's own Sort By menu offers. Each comment
comes back as a flat dictionary with a ``parent`` that is ``"root"`` for a
top-level comment and the parent's id for a reply.

What this module adds is the shape a listener needs:

* **Threads in reading order.** Replies follow the comment they answer, each
  saying whose comment that was ("reply to Rick Steves"), so a reply is never
  a sentence out of context.
* **One row says enough to decide.** ``author: first line ... (likes, when)``
  -- the full text is one Tab away in the window, not crammed into the row.
* **Paged by asking for more.** yt-dlp has no "next page of comments" call;
  it walks the thread from the start up to the cap. So Load More asks again
  with a higher cap (100, 200, ...) and keeps what it already had, up to
  :data:`MAX_COMMENTS`. The first hundred cost one request; a listener who
  wants the five-hundredth pays for walking there, and is told when the cap is
  reached rather than having Load More quietly do nothing.

wx-free, strict-typed. The single network call is
:func:`quill.core.radio.youtube_requests.run`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from quill.core.radio.youtube_requests import Fetch, run

TOP = "top"
NEWEST = "new"

#: How many comments one page asks for.
PAGE_SIZE = 100

#: The most Load More will ever ask for. Past this a video's comments are a
#: crowd rather than a conversation, and every further page is a longer walk.
MAX_COMMENTS = 1000

#: How much of the first line a row shows before the ellipsis.
ROW_TEXT_LIMIT = 90


@dataclass(frozen=True, slots=True)
class Comment:
    """One comment or reply."""

    comment_id: str
    author: str
    text: str
    likes: int = 0
    when: str = ""
    #: The id of the comment this answers; ``""`` for a top-level comment.
    parent_id: str = ""
    #: Whose comment this answers, filled in when threading.
    reply_to: str = ""
    pinned: bool = False
    by_uploader: bool = False

    @property
    def is_reply(self) -> bool:
        return bool(self.parent_id)


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))


def parse_comments(info: dict[str, object]) -> list[Comment]:
    """Every comment yt-dlp returned, threaded into reading order (pure).

    yt-dlp already yields each thread's replies right after their parent; the
    threading here makes that a guarantee rather than an accident, and names
    the parent on each reply.
    """
    raw = info.get("comments")
    if not isinstance(raw, list):
        return []
    tops: list[Comment] = []
    replies: dict[str, list[Comment]] = {}
    authors: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        comment_id = str(item.get("id") or "").strip()
        text = str(item.get("text") or "").strip()
        if not comment_id or not text:
            continue
        parent = str(item.get("parent") or "root").strip()
        author = str(item.get("author") or "").strip().lstrip("@") or "Someone"
        authors[comment_id] = author
        comment = Comment(
            comment_id=comment_id,
            author=author,
            text=text,
            likes=_int(item.get("like_count")),
            when=str(item.get("_time_text") or "").strip(),
            parent_id="" if parent in ("", "root") else parent,
            pinned=bool(item.get("is_pinned")),
            by_uploader=bool(item.get("author_is_uploader")),
        )
        if comment.parent_id:
            replies.setdefault(comment.parent_id, []).append(comment)
        else:
            tops.append(comment)
    ordered: list[Comment] = []
    placed: set[str] = set()
    for top in tops:
        ordered.append(top)
        placed.add(top.comment_id)
        for reply in replies.get(top.comment_id, []):
            ordered.append(_named(reply, authors))
            placed.add(reply.comment_id)
    # A reply whose parent fell outside the cap still belongs in the list.
    for orphans in replies.values():
        for reply in orphans:
            if reply.comment_id not in placed:
                ordered.append(_named(reply, authors))
    return ordered


def _named(reply: Comment, authors: dict[str, str]) -> Comment:
    from dataclasses import replace

    return replace(reply, reply_to=authors.get(reply.parent_id, ""))


#: A web address inside a comment.
_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>()]+")

#: Joiners, presentation selectors and skin-tone modifiers: they shape an
#: emoji and have nothing of their own worth saying.
_SILENT = frozenset({0x200D, 0xFE0E, 0xFE0F, *range(0x1F3FB, 0x1F400)})


def speakable(text: str, *, keep_addresses: bool = False) -> str:
    """Emoji as words and links named as links, so a reader says what is there.

    A row of laughing faces is read by some screen readers as question marks
    and by others as nothing; "(face with tears of joy)" is what the commenter
    meant. YouTube's own channel emotes already arrive as text
    (":yt-heart:"), so they read as written. In a row a web address is "link
    to example.com"; in Full text it stays whole, as "link: https://...", so
    it can be read and copied.
    """
    out: list[str] = []
    for char in text:
        point = ord(char)
        if point in _SILENT:
            continue
        if point >= 0x2190 and unicodedata.category(char) in ("So", "Sk"):
            name = unicodedata.name(char, "").lower()
            out.append(f" ({name}) " if name else " ")
        else:
            out.append(char)
    said = re.sub(r"[ \t]{2,}", " ", "".join(out))
    said = "\n".join(line.strip() for line in said.strip().splitlines())

    def _link(match: re.Match[str]) -> str:
        whole = match.group(0)
        address = whole.rstrip(".,!?;:")
        tail = whole[len(address) :]
        if keep_addresses:
            return f"link: {address}{tail}"
        host = re.sub(r"^(?:https?://)?(?:www\.)?", "", address).split("/")[0]
        return f"link to {host}{tail}"

    return _URL_RE.sub(_link, said)


def _first_line(text: str) -> str:
    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    if len(line) > ROW_TEXT_LIMIT:
        return line[:ROW_TEXT_LIMIT].rstrip() + " ..."
    if len(text.strip().splitlines()) > 1:
        return line + " ..."
    return line


def row_label(comment: Comment) -> str:
    """``author: first line ... (likes, when)`` -- what one list row reads (pure).

    The author always comes first, so arrowing the list reads who before what;
    a reply says whose comment it answers straight after its own author.
    """
    who = f"{comment.author} (channel owner)" if comment.by_uploader else comment.author
    if comment.is_reply:
        who += f", reply to {comment.reply_to}" if comment.reply_to else ", reply"
    if comment.pinned:
        who += ", pinned"
    facts = []
    if comment.likes:
        facts.append(f"{comment.likes:,} like{'' if comment.likes == 1 else 's'}")
    if comment.when:
        facts.append(comment.when)
    tail = f" ({', '.join(facts)})" if facts else ""
    return f"{who}: {_first_line(speakable(comment.text))}{tail}"


def full_text(comment: Comment) -> str:
    """The whole comment, for the read-only box beside the list (pure)."""
    heading = comment.author
    if comment.is_reply and comment.reply_to:
        heading += f", replying to {comment.reply_to}"
    facts = []
    if comment.likes:
        facts.append(f"{comment.likes:,} like{'' if comment.likes == 1 else 's'}")
    if comment.when:
        facts.append(comment.when)
    if facts:
        heading += f" ({', '.join(facts)})"
    return f"{heading}\n\n{speakable(comment.text, keep_addresses=True)}"


def filter_comments(comments: list[Comment], words: str) -> list[Comment]:
    """The comments whose author or text contains every word typed (pure).

    Every word, in any order, ignoring case: "bristol bridge" finds a comment
    that mentions the bridge in Bristol however it phrased it.
    """
    wanted = [word for word in words.casefold().split() if word]
    if not wanted:
        return list(comments)
    return [
        comment
        for comment in comments
        if all(
            word in f"{comment.author} {comment.text} {speakable(comment.text)}".casefold()
            for word in wanted
        )
    ]


def merge(existing: list[Comment], incoming: list[Comment]) -> list[Comment]:
    """*incoming* in its own order, with nothing dropped that *existing* had.

    Load More re-reads the thread from the start, so the new answer normally
    contains the old one; keeping anything that went missing in between (a
    comment deleted a second ago) means a row never vanishes under the cursor.
    """
    seen = {comment.comment_id for comment in incoming}
    return [*incoming, *(c for c in existing if c.comment_id not in seen)]


def fetch_comments(
    page_url: str,
    *,
    sort: str = TOP,
    limit: int = PAGE_SIZE,
    fetch: Fetch | None = None,
) -> list[Comment]:
    """Up to *limit* comments for the video at *page_url*, threaded.

    *limit* counts replies as well as top-level comments, which is how yt-dlp
    counts. Raises :class:`~quill.core.radio.youtube_requests.YouTubeRequestError`
    with a speakable reason.
    """
    cap = max(1, min(int(limit), MAX_COMMENTS))
    options: dict[str, object] = {
        "getcomments": True,
        "noplaylist": True,
        # Only the comments are wanted: no format is chosen and no stream is
        # read, and the player's own formats are skipped where yt-dlp allows.
        "extractor_args": {
            "youtube": {
                "max_comments": [str(cap)],
                "comment_sort": [NEWEST if sort == NEWEST else TOP],
            }
        },
    }
    info = run(page_url, options, fetch=fetch)
    return parse_comments(info)[:cap]


def next_limit(current: int) -> int:
    """How many to ask for on the next Load More, or 0 at the cap (pure)."""
    if current >= MAX_COMMENTS:
        return 0
    return min(MAX_COMMENTS, current + PAGE_SIZE)


__all__ = [
    "MAX_COMMENTS",
    "NEWEST",
    "PAGE_SIZE",
    "TOP",
    "Comment",
    "fetch_comments",
    "filter_comments",
    "full_text",
    "merge",
    "next_limit",
    "parse_comments",
    "row_label",
]
