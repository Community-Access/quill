"""Chapter auto-skip: mark chapters to skip, and jump past them (1.1.0).

Cast already reads chapters from three sources -- the feed's own chapters
document, markers in the file, and timestamps inferred from show notes --
which is more than most players manage. What it could not do was *use* them
to skip anything: the ad break at 00:00, the sponsor read in the middle, the
outro you have heard two hundred times.

Marking is per episode and deliberately does not persist across a restart.
A chapter you skipped in yesterday's episode says nothing about today's, and
a durable "always skip chapter 3" would be a rule about chapter *numbers*,
which mean nothing across episodes.

Two details that are easy to get wrong and are the whole reason this is a
separate, pure module:

**Consecutive skipped chapters.** Skipping chapter 3 when 4 and 5 are also
skipped must land on 6, not play 4. The walk is forward to the first chapter
*not* marked.

**The loop guard.** A seek's own position update can momentarily still report
the old chapter, which re-triggers the skip, which seeks again -- an endless
loop that pins the audio at one point. So an auto-skip records the index it
skipped *from* and will not fire again until the active chapter has actually
moved away from it. (This shape, and the bug behind it, come from reading
Earshot's ``ChapterSkipLogic``; the trap is real and worth borrowing rather
than rediscovering.)

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.podcasts.chapters import PodcastChapter


@dataclass(frozen=True, slots=True)
class SkipDecision:
    """What to do at the current position.

    ``kind`` is ``"none"`` (stay put), ``"seek"`` (jump to
    :attr:`target_start_ms`, announcing :attr:`target_title`), or
    ``"end"`` (every remaining chapter is skipped, so the episode is
    effectively over and should finish exactly as it would naturally).
    """

    kind: str = "none"
    target_index: int = -1
    target_start_ms: int = 0
    target_title: str = ""
    skipped_title: str = ""


NO_SKIP = SkipDecision()


def active_chapter_index(chapters: list[PodcastChapter], position_ms: int) -> int | None:
    """Which chapter *position_ms* falls in, or None before the first starts."""
    active: int | None = None
    for index, chapter in enumerate(chapters):
        if chapter.start_ms <= position_ms:
            active = index
        else:
            break
    return active


def decide(
    chapters: list[PodcastChapter], skipped: set[int], active_index: int | None
) -> SkipDecision:
    """The decision for one position; see the module docstring."""
    if active_index is None or not (0 <= active_index < len(chapters)):
        return NO_SKIP
    if active_index not in skipped:
        return NO_SKIP
    skipped_title = chapters[active_index].title
    target = active_index + 1
    while target < len(chapters) and target in skipped:
        target += 1
    if target >= len(chapters):
        return SkipDecision(kind="end", skipped_title=skipped_title)
    chapter = chapters[target]
    return SkipDecision(
        kind="seek",
        target_index=target,
        target_start_ms=chapter.start_ms,
        target_title=chapter.title,
        skipped_title=skipped_title,
    )


def should_auto_skip(
    active_index: int | None, skipped: set[int], last_skipped_from: int | None
) -> bool:
    """Whether a skip may fire now -- the loop guard. See the docstring."""
    if active_index is None or active_index not in skipped:
        return False
    return active_index != last_skipped_from


@dataclass(slots=True)
class ChapterSkipState:
    """Per-episode marking plus the loop guard, held for one playback session.

    Reset whenever the episode changes, which is what makes "your skip
    choices clear when you restart" true without any storage at all.
    """

    #: (show_id, episode_guid) the marks belong to.
    key: tuple[str, str] = ("", "")
    skipped: set[int] = field(default_factory=set)
    last_skipped_from: int | None = None

    def retarget(self, show_id: str, episode_guid: str) -> None:
        """Point at a different episode, dropping the previous one's marks."""
        if self.key != (show_id, episode_guid):
            self.key = (show_id, episode_guid)
            self.skipped = set()
            self.last_skipped_from = None

    def toggle(self, index: int) -> bool:
        """Mark or unmark one chapter; returns whether it is now skipped."""
        if index in self.skipped:
            self.skipped.discard(index)
            return False
        self.skipped.add(index)
        return True

    def clear(self) -> None:
        self.skipped = set()
        self.last_skipped_from = None

    def evaluate(self, chapters: list[PodcastChapter], position_ms: int) -> SkipDecision:
        """The decision for *position_ms*, honouring the loop guard.

        Records the guard as a side effect when a skip fires, so a caller can
        poll this once a second without arming an infinite loop.
        """
        if not self.skipped or not chapters:
            return NO_SKIP
        active = active_chapter_index(chapters, position_ms)
        if not should_auto_skip(active, self.skipped, self.last_skipped_from):
            return NO_SKIP
        decision = decide(chapters, self.skipped, active)
        if decision.kind != "none":
            self.last_skipped_from = active
        return decision


__all__ = [
    "NO_SKIP",
    "ChapterSkipState",
    "SkipDecision",
    "active_chapter_index",
    "decide",
    "should_auto_skip",
]
