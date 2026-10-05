"""A YouTube live chat, as rows a screen reader can keep up with.

The Live Chat window (:mod:`quill.ui.radio.youtube_live_chat_window`) shows a
live stream's chat -- or the replay of a finished one, where YouTube kept it --
as an ordinary list. Everything here is the part that does not need a window:

* **One row says who, then what, then what kind.** ``Sam: great show,
  moderator`` -- the author first because that is how a chat is followed by
  ear, the message next, the labels (paid, member, moderator, owner) last and
  short. The time is on demand only: in the full-text box, and on a key.
* **Emoji become words.** chat-downloader already turns YouTube's emoji into
  their shortcut (``:smiling_face:``) and a channel's own emotes into their
  name; a plain Unicode emoji that slipped through becomes its Unicode name in
  the same ``:colon:`` style, so a screen reader never says "symbol" or
  nothing at all.
* **Links say they are links.** A web address in a row reads as
  ``link example.com/page``; the full text keeps the exact address.
* **Speaking new messages never floods the reader.**
  :class:`ChatAnnouncer` speaks at most once every few seconds, and a burst
  becomes one sentence ("12 new messages"). A paid message or one that
  mentions the listener's word still gets its own words inside that one
  sentence, when that is what they chose.
* **Pause holds the list still.** :class:`ChatFeed` keeps what arrives while
  paused and counts it, and hands it over on resume.
* **The reader runs on its own thread** -- see
  :mod:`quill.core.radio.youtube_live_chat_reader`.

wx-free, strict-typed, no network.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime

from quill.core.error_codes import CodedError

#: The labels a row may carry, in the order they are read.
PAID = "paid"
MEMBER = "member"
MODERATOR = "moderator"
OWNER = "owner"
VERIFIED = "verified"

#: What "Speak new messages" may be set to.
SPEAK_OFF = "off"
SPEAK_ALL = "all"
SPEAK_IMPORTANT = "important"
SPEAK_MENTIONS = "mentions"

SPEAK_CHOICES: tuple[tuple[str, str], ...] = (
    (SPEAK_OFF, "Off"),
    (SPEAK_ALL, "Every message"),
    (SPEAK_IMPORTANT, "Only paid messages, moderators and the owner"),
    (SPEAK_MENTIONS, "Only messages that mention a word"),
)

#: The fewest seconds between two spoken chat sentences.
MIN_GAP_SECONDS = 4.0

#: The most rows the window keeps. A busy chat says thousands an hour; past
#: this the oldest go, so the list stays quick to arrow through.
MAX_MESSAGES = 5000

#: How long a row's message may be before it is cut with an ellipsis.
ROW_TEXT_LIMIT = 200

_URL = re.compile(r"https?://[^\s]+", re.IGNORECASE)


class LiveChatError(CodedError):
    """The live chat could not be read, with a speakable reason."""

    code = "QUILL-RADIO-YOUTUBE-LIVECHAT"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One chat message, already in words."""

    message_id: str
    author: str
    text: str
    labels: tuple[str, ...] = ()
    #: How the chat said the time ("12:31 PM", or "1:02:03" into a replay).
    time_text: str = ""
    #: Microseconds since the epoch, when the chat said; ``0`` = not said.
    timestamp_us: int = 0
    #: Seconds into the video, for a replay; ``-1`` for a live message.
    offset_seconds: float = -1.0
    #: The paid amount as YouTube wrote it ("$5.00"), when paid.
    amount: str = ""
    author_channel_id: str = ""

    @property
    def is_paid(self) -> bool:
        return PAID in self.labels

    @property
    def is_important(self) -> bool:
        """Paid, or from a moderator or the owner."""
        return any(label in self.labels for label in (PAID, MODERATOR, OWNER))


# -- turning chat-downloader's dictionaries into words --------------------------


def _emoji_name(char: str) -> str:
    try:
        name = unicodedata.name(char)
    except ValueError:
        return ""
    return ":" + name.lower().replace(" ", "_") + ":"


def emoji_to_text(text: str) -> str:
    """Every pictograph left in *text* as its name in ``:colon:`` style (pure).

    Variation selectors and joiners carry no meaning by ear and are dropped;
    a run of the same emoji is said once with a count, because "laughing,
    laughing, laughing, laughing" is nobody's idea of a message.
    """
    out: list[str] = []
    last = ""
    repeat = 0

    def _flush() -> None:
        nonlocal last, repeat
        if last:
            out.append(f"{last} x{repeat}" if repeat > 1 else last)
        last, repeat = "", 0

    for char in text:
        if char in "️︎‍" or 0x1F3FB <= ord(char) <= 0x1F3FF:
            continue  # variation selectors, joiners, skin-tone modifiers
        if unicodedata.category(char) == "So" and ord(char) > 0x2100:
            name = _emoji_name(char)
            if name:
                if name == last:
                    repeat += 1
                else:
                    _flush()
                    last, repeat = name, 1
                continue
        _flush()
        out.append(char)
    _flush()
    spaced = re.sub(r"(?<=\S)(:[a-z0-9_]+:)", r" \1", "".join(out))
    return re.sub(r"(:[a-z0-9_]+:(?: x\d+)?)(?=\S)", r"\1 ", spaced)


def _link_words(match: re.Match[str]) -> str:
    address = match.group(0).rstrip(".,;:!?)")
    tail = match.group(0)[len(address) :]
    shown = re.sub(r"^https?://(www\.)?", "", address, flags=re.IGNORECASE).rstrip("/")
    return f"link {shown}{tail}"


def links_as_words(text: str) -> str:
    """Each web address in *text* as ``link example.com/page`` (pure)."""
    return _URL.sub(_link_words, text)


def _labels(raw: dict[str, object], author: dict[str, object]) -> tuple[str, ...]:
    found: list[str] = []
    if raw.get("money") or str(raw.get("message_type", "")).startswith("paid"):
        found.append(PAID)
    badges = author.get("badges")
    for badge in badges if isinstance(badges, list) else []:
        if not isinstance(badge, dict):
            continue
        title = str(badge.get("title", "")).lower()
        icon = str(badge.get("icon_name", "")).lower()
        if icon == "owner" or title == "owner":
            found.append(OWNER)
        elif icon == "moderator" or title == "moderator":
            found.append(MODERATOR)
        elif "member" in title:
            found.append(MEMBER)
        elif icon == "verified" or title == "verified":
            found.append(VERIFIED)
    if raw.get("message_type") == "membership_item" and MEMBER not in found:
        found.append(MEMBER)
    order = (PAID, OWNER, MODERATOR, MEMBER, VERIFIED)
    return tuple(label for label in order if label in found)


def parse_message(raw: object) -> ChatMessage | None:
    """One chat-downloader message as a :class:`ChatMessage`, or ``None`` (pure)."""
    if not isinstance(raw, dict):
        return None
    author = raw.get("author")
    author = author if isinstance(author, dict) else {}
    name = str(author.get("name", "") or "").strip().lstrip("@") or "Someone"
    text = str(raw.get("message", "") or "").strip()
    if raw.get("message_type") == "membership_item" and not text:
        text = str(raw.get("header_secondary_text") or raw.get("header_primary_text") or "").strip()
    money = raw.get("money")
    amount = str(money.get("text", "")) if isinstance(money, dict) else ""
    if not text and not amount:
        return None
    try:
        timestamp = int(raw.get("timestamp") or 0)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        timestamp = 0
    offset = raw.get("time_in_seconds")
    return ChatMessage(
        message_id=str(raw.get("message_id", "") or ""),
        author=name,
        text=emoji_to_text(text),
        labels=_labels(raw, author),
        time_text=str(raw.get("time_text", "") or ""),
        timestamp_us=timestamp,
        offset_seconds=float(offset) if isinstance(offset, (int, float)) else -1.0,
        amount=amount,
        author_channel_id=str(author.get("id", "") or ""),
    )


def _label_words(message: ChatMessage) -> list[str]:
    words: list[str] = []
    for label in message.labels:
        if label == PAID:
            words.append(f"paid {message.amount}" if message.amount else "paid")
        else:
            words.append(label)
    return words


def row_label(message: ChatMessage) -> str:
    """``Sam: great show, moderator`` -- author, message, labels (pure)."""
    text = links_as_words(" ".join(message.text.split()))
    if len(text) > ROW_TEXT_LIMIT:
        text = text[:ROW_TEXT_LIMIT].rstrip() + " ..."
    labels = _label_words(message)
    tail = f", {', '.join(labels)}" if labels else ""
    return f"{message.author}: {text or '(no words)'}{tail}"


def when_said(message: ChatMessage) -> str:
    """When the message was sent, in words (pure)."""
    if message.offset_seconds >= 0:
        total = int(message.offset_seconds)
        hours, rest = divmod(total, 3600)
        minutes, seconds = divmod(rest, 60)
        clock = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"
        return f"{clock} into the stream"
    if message.timestamp_us > 0:
        moment = datetime.fromtimestamp(message.timestamp_us / 1_000_000)
        return "sent at " + moment.strftime("%I:%M %p").lstrip("0")
    return f"sent at {message.time_text}" if message.time_text else ""


def full_text(message: ChatMessage) -> str:
    """The whole message for the read-only box: who, what kind, when, then it."""
    heading = message.author
    labels = _label_words(message)
    if labels:
        heading += ", " + ", ".join(labels)
    said = when_said(message)
    if said:
        heading += f", {said}"
    return f"{heading}\n\n{message.text}"


def mentions(message: ChatMessage, word: str) -> bool:
    """Whether *message* contains *word* as a word, ignoring case (pure)."""
    wanted = word.strip()
    if not wanted:
        return False
    pattern = r"(?<!\w)" + re.escape(wanted) + r"(?!\w)"
    return re.search(pattern, message.text, re.IGNORECASE) is not None


def filter_messages(messages: Iterable[ChatMessage], words: str) -> list[ChatMessage]:
    """The messages whose author or text holds every word typed (pure)."""
    wanted = [w for w in words.casefold().split() if w]
    if not wanted:
        return list(messages)
    return [m for m in messages if all(w in f"{m.author} {m.text}".casefold() for w in wanted)]


def same_author_index(messages: list[ChatMessage], start: int, step: int) -> int:
    """The next row before (``step=-1``) or after (``+1``) *start* by the same
    author, or ``-1`` when there is none (pure)."""
    if not 0 <= start < len(messages):
        return -1
    who = messages[start].author
    index = start + step
    while 0 <= index < len(messages):
        if messages[index].author == who:
            return index
        index += step
    return -1


# -- speaking new messages --------------------------------------------------------


def wants_speech(message: ChatMessage, mode: str, word: str = "") -> bool:
    """Whether *mode* asks for *message* to be spoken at all (pure)."""
    if mode == SPEAK_ALL:
        return True
    if mode == SPEAK_IMPORTANT:
        return message.is_important
    if mode == SPEAK_MENTIONS:
        return mentions(message, word)
    return False


def is_priority(message: ChatMessage, mode: str, word: str = "") -> bool:
    """A message that keeps its own words even inside a coalesced burst (pure).

    Paid messages always do, while anything is being spoken; and a mention of
    the listener's word does, whatever else is chosen.
    """
    if mode == SPEAK_OFF:
        return False
    return message.is_paid or mentions(message, word)


class ChatAnnouncer:
    """Speaks new messages at most once every :data:`MIN_GAP_SECONDS`.

    :meth:`offer` takes what arrived; :meth:`tick` (called about once a
    second by the window's timer) decides whether the gap has opened and, if
    so, says one sentence for everything waiting: a lone message in full, a
    burst as a count, with any priority message's own words leading it.
    *held_back* answers whether Quiet Hours silence chat right now; held-back
    messages are dropped rather than saved up for later, because a backlog
    read out at seven in the morning is not what anybody asked for.
    """

    def __init__(
        self,
        speak: Callable[[str], object],
        *,
        min_gap: float = MIN_GAP_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        held_back: Callable[[], bool] = lambda: False,
    ) -> None:
        self._speak = speak
        self._min_gap = min_gap
        self._clock = clock
        self._held_back = held_back
        self._last = -1e9
        self._pending: list[ChatMessage] = []
        self._priority: list[ChatMessage] = []
        self.mode = SPEAK_OFF
        self.word = ""

    @property
    def waiting(self) -> int:
        return len(self._pending) + len(self._priority)

    def clear(self) -> None:
        self._pending.clear()
        self._priority.clear()

    def offer(self, messages: Iterable[ChatMessage]) -> None:
        if self.mode == SPEAK_OFF:
            return
        for message in messages:
            if is_priority(message, self.mode, self.word):
                self._priority.append(message)
            elif wants_speech(message, self.mode, self.word):
                self._pending.append(message)
        self.tick()

    def tick(self) -> str:
        """Speak if the gap has opened; return what was said ("" if nothing)."""
        if not self.waiting:
            return ""
        now = self._clock()
        if now - self._last < self._min_gap:
            return ""
        if self._held_back():
            self.clear()
            return ""
        sentence = self.sentence(self._priority, self._pending)
        self.clear()
        self._last = now
        self._speak(sentence)
        return sentence

    @staticmethod
    def sentence(priority: list[ChatMessage], others: list[ChatMessage]) -> str:
        """One sentence for everything waiting (pure)."""
        parts: list[str] = []
        if len(priority) <= 2:
            parts.extend(row_label(message) for message in priority)
        else:
            parts.append(row_label(priority[-1]))
            others = [*priority[:-1], *others]
        if len(others) == 1 and not parts:
            parts.append(row_label(others[0]))
        elif others:
            noun = "message" if len(others) == 1 else "messages"
            lead = "And " if parts else ""
            more = " more" if parts else " new"
            parts.append(f"{lead}{len(others)}{more} {noun}")
        return " ".join(part if part[-1:] in ".!?" else part + "." for part in parts)


# -- what the list shows ----------------------------------------------------------


@dataclass
class ChatFeed:
    """Every message so far, and what Pause is holding back.

    :meth:`add` answers the rows to append now -- nothing while paused, when
    they are counted instead. :meth:`resume` hands the held rows over.
    """

    paused: bool = False
    messages: list[ChatMessage] = field(default_factory=list)
    held: list[ChatMessage] = field(default_factory=list)
    cap: int = MAX_MESSAGES

    def add(self, batch: Iterable[ChatMessage]) -> list[ChatMessage]:
        incoming = list(batch)
        if self.paused:
            self.held.extend(incoming)
            return []
        self.messages.extend(incoming)
        return incoming

    @property
    def unseen(self) -> int:
        return len(self.held)

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> list[ChatMessage]:
        self.paused = False
        released, self.held = self.held, []
        self.messages.extend(released)
        return released

    def trim(self) -> int:
        """Drop the oldest past :attr:`cap`; return how many went."""
        extra = len(self.messages) - self.cap
        if extra <= 0:
            return 0
        del self.messages[:extra]
        return extra


def release_replay(
    waiting: list[ChatMessage], position_seconds: float
) -> tuple[list[ChatMessage], list[ChatMessage]]:
    """Split a replay's messages into ``(due, still_waiting)`` (pure).

    A finished stream's chat arrives far faster than it was said. When that
    video is playing, rows are released as playback reaches the moment each
    was sent, so the chat reads in step with what is heard.
    """
    due = [m for m in waiting if m.offset_seconds <= position_seconds]
    later = [m for m in waiting if m.offset_seconds > position_seconds]
    return due, later


__all__ = [
    "MAX_MESSAGES",
    "MEMBER",
    "MIN_GAP_SECONDS",
    "MODERATOR",
    "OWNER",
    "PAID",
    "SPEAK_ALL",
    "SPEAK_CHOICES",
    "SPEAK_IMPORTANT",
    "SPEAK_MENTIONS",
    "SPEAK_OFF",
    "ChatAnnouncer",
    "ChatFeed",
    "ChatMessage",
    "LiveChatError",
    "emoji_to_text",
    "filter_messages",
    "full_text",
    "links_as_words",
    "mentions",
    "parse_message",
    "release_replay",
    "row_label",
    "same_author_index",
    "wants_speech",
    "when_said",
]
