"""Accessibility announcer for the F7 spelling review dialog.

Wraps a generic announce callable and enforces the three verbosity modes
(concise, balanced, detailed) plus the optional spell-word feature.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.spelling.models import ReviewCounters, SpellingIssue

_VERBOSITY_LEVELS = {"concise", "balanced", "detailed"}


class AccessibilityAnnouncer:
    """Produce appropriately-verbose announcements for a review session."""

    def __init__(
        self,
        announce: Callable[[str], None],
        verbosity: str = "balanced",
        spell_word: bool = True,
        spell_word_pause_ms: int = 800,
        timer_factory: Callable[..., object] | None = None,
    ) -> None:
        self._announce = announce
        self._verbosity = verbosity if verbosity in _VERBOSITY_LEVELS else "balanced"
        self._spell_word = spell_word
        self._spell_word_pause_ms = spell_word_pause_ms
        # A one-shot timer factory ``(delay_ms, callable, *args) -> timer`` used
        # to debounce the spell-aloud follow-up. The UI injects ``wx.CallLater``;
        # core stays wx-free. When absent (e.g. headless/tests), the delayed
        # spell-aloud is simply skipped.
        self._timer_factory = timer_factory
        self._pending_spell_timer: object | None = None

    # ------------------------------------------------------------------
    # Public announcement methods
    # ------------------------------------------------------------------

    def announce_opening(self, scope_label: str, index: int, total: int, word: str) -> None:
        """Announce the dialog opening with scope, progress, and first issue."""
        self._cancel_pending_spell()
        if self._verbosity == "concise":
            msg = f"Spelling review. Issue {index} of {total}. {word}."
        elif self._verbosity == "detailed":
            msg = (
                f"Spelling review. Checking {scope_label}. "
                f"Issue {index} of {total}. Not in dictionary: {word}."
            )
        else:  # balanced
            msg = f"Spelling review. Issue {index} of {total}. Not in dictionary: {word}."
        self._announce(msg)
        self._schedule_spell(word)

    def announce_issue(self, issue: SpellingIssue, index: int, total: int) -> None:
        """Announce a new issue after advancing from a prior action."""
        self._cancel_pending_spell()
        word = issue.word
        if self._verbosity == "concise":
            msg = f"Issue {index} of {total}."
        elif self._verbosity == "detailed":
            msg = f"Issue {index} of {total}. Not in dictionary: {word}."
        else:
            msg = f"Issue {index} of {total}. Not in dictionary: {word}."
        self._announce(msg)
        self._schedule_spell(word)

    def announce_action_result(self, result: str, index: int, total: int) -> None:
        """Announce the result of an action before moving to the next issue."""
        self._cancel_pending_spell()
        if index > total:
            # Completion will be announced separately.
            self._announce(result)
            return
        if self._verbosity == "concise":
            self._announce(f"Issue {index} of {total}.")
        else:
            self._announce(f"{result} Issue {index} of {total}.")

    def announce_no_issues(self, scope_label: str) -> None:
        self._cancel_pending_spell()
        self._announce(f"Spelling review complete. No issues found in {scope_label}.")

    def announce_no_suggestions(self) -> None:
        self._announce("No suggestions.")

    def announce_complete(self, counters: ReviewCounters) -> None:
        """Announce the review completion summary."""
        self._cancel_pending_spell()
        parts: list[str] = []
        if counters.changed:
            n = counters.changed
            parts.append(f"{n} {'change' if n == 1 else 'changes'}")
        if counters.changed_all:
            n = counters.changed_all
            parts.append(f"{n} Change All {'replacement' if n == 1 else 'replacements'}")
        if counters.ignored_once:
            n = counters.ignored_once
            parts.append(f"{n} ignored {'once' if n == 1 else ''}")
        if counters.ignored_all:
            n = counters.ignored_all
            parts.append(f"{n} {'word' if n == 1 else 'words'} ignored for this session")
        if counters.added_to_dict:
            n = counters.added_to_dict
            parts.append(f"{n} {'word' if n == 1 else 'words'} added to dictionary")

        if parts:
            summary = ", ".join(parts) + "."
        else:
            summary = "No changes made."

        self._announce(f"Spelling review complete. {summary}")

    def announce_wrap_prompt(self) -> None:
        self._announce("Reached end of document. Wrapping to beginning to check remaining text.")

    def announce_error(self, message: str) -> None:
        self._cancel_pending_spell()
        self._announce(f"Spelling review error: {message}")

    # ------------------------------------------------------------------
    # Spell-word feature
    # ------------------------------------------------------------------

    def _schedule_spell(self, word: str) -> None:
        if not self._spell_word or self._spell_word_pause_ms <= 0:
            return
        if self._timer_factory is None:
            return
        try:
            self._pending_spell_timer = self._timer_factory(
                self._spell_word_pause_ms,
                self._spell_word_aloud,
                word,
            )
        except Exception:  # noqa: BLE001 — timer backend unavailable
            pass

    def _cancel_pending_spell(self) -> None:
        timer = self._pending_spell_timer
        self._pending_spell_timer = None
        if timer is None:
            return
        try:
            stop = getattr(timer, "Stop", None)
            if callable(stop):
                stop()
        except Exception:  # noqa: BLE001
            pass

    def _spell_word_aloud(self, word: str) -> None:
        self._pending_spell_timer = None
        letters = ", ".join(ch.upper() for ch in word if ch.isalpha())
        if letters:
            self._announce(letters)
