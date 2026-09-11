"""Accessibility announcer for the F7 spelling review dialog.

Wraps a generic announce callable and enforces the three verbosity modes
(concise, balanced, detailed) plus the spell-aloud that follows each word.

The spelling itself is not done here. It belongs to
:class:`~quill.core.spelling.voicing.SpellAloudVoice`, which every surface that
can land on a misspelled word shares -- the review, the next/previous keys, the
suggestions list -- because "how are letters said, and after how long" is one
question and three different answers to it would be three things for a listener
to tune and two of them would be wrong. This class keeps the review's own
verbosity and its own pause, and hands the word over.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.spelling.models import ReviewCounters, SpellingIssue
from quill.core.spelling.voicing import SpellAloudPolicy, SpellAloudVoice

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
        settings: Any = None,
    ) -> None:
        self._announce = announce
        self._verbosity = verbosity if verbosity in _VERBOSITY_LEVELS else "balanced"
        self._spell_word = spell_word
        self._spell_word_pause_ms = spell_word_pause_ms
        # *settings* carries the shared voicing preferences -- how letters are
        # said, whether capitals are named, whether each suggestion is spelled
        # as you arrow onto it. The review's own two arguments still win over
        # the equivalents in there, because they are the review's: somebody who
        # switched spelling off for the F7 dialog specifically meant the F7
        # dialog. Absent settings give the documented defaults, which is what
        # every existing caller and test relies on.
        policy = SpellAloudPolicy.from_settings(settings)
        self._policy = SpellAloudPolicy(
            enabled=bool(spell_word),
            delay_ms=int(spell_word_pause_ms),
            navigation=policy.navigation,
            navigation_delay_ms=policy.navigation_delay_ms,
            suggestions=policy.suggestions,
            suggestion_delay_ms=policy.suggestion_delay_ms,
            first_suggestion=policy.first_suggestion,
            style=policy.style,
            capitals=policy.capitals,
        )
        # A one-shot timer factory ``(delay_ms, callable, *args) -> timer`` used
        # to debounce the spell-aloud follow-up. The UI injects ``wx.CallLater``;
        # core stays wx-free. When absent (e.g. headless/tests), the delayed
        # spell-aloud is simply skipped.
        self._timer_factory = timer_factory
        self._voice = SpellAloudVoice(announce, self._policy, timer_factory)
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

    def spell_suggestion(self, suggestion: str) -> None:
        """Spell out the suggestion the user has just arrowed onto.

        Choosing between "receive" and "recieve" by ear is exactly as impossible
        in a list of corrections as it was in the document, so the list gets the
        same treatment the word got: the reader says the suggestion, and a
        moment later -- if you are still on it -- the letters follow. Arrowing
        on cancels it, which is what keeps a fast pass through eight
        near-identical suggestions quiet.
        """
        self._cancel_pending_spell()
        if not self._policy.suggestions:
            return
        self._voice.spell_later(suggestion, delay_ms=self._policy.suggestion_delay_ms)

    def spell_word_now(self, word: str) -> None:
        """Spell *word* immediately, for a key whose whole purpose is to."""
        self._cancel_pending_spell()
        self._voice.spell_word_now(word)

    def announce_context_sentence(self, context_text: str) -> None:
        """Read the sentence(s) around the misspelling aloud on demand (Ctrl+R).

        Speaks the full surrounding context verbatim regardless of verbosity so a
        user can hear the misspelling in situ (the in-dialog Ctrl+R).
        Any pending spell-aloud is cancelled first so the two do not overlap.
        """
        self._cancel_pending_spell()
        text = " ".join(context_text.split())
        if text:
            self._announce(text)

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
        """Queue the word's letters, and the top suggestion's when asked.

        The suggestion half is off by default and says why in its setting: it
        doubles the arrival announcement, which is welcome when you are learning
        a word and noise when you are checking one. It rides the same timer, one
        pause further on, so the two never overlap.
        """
        if self._spell_word_pause_ms <= 0:
            return
        self._voice.spell_later(word, delay_ms=self._spell_word_pause_ms)

    def _cancel_pending_spell(self) -> None:
        self._voice.cancel()
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
        """Kept for callers that spell a word without going through the timer."""
        self._pending_spell_timer = None
        self._voice.spell_word_now(word)
