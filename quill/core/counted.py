"""Counting out loud: the shared vocabulary for every bulk action.

Earshot's habit, taken deliberately (list.md 14.2): almost every action that
touches more than one row ends by announcing exact numbers -- how many were
eligible, how many it did, how many it skipped and why, how many failed. The
alternative is the sentence this family used to say, "Removed downloads", and
a listener who cannot see the list has no way to learn whether that meant two
files or two hundred, or whether the three it could not touch were mentioned
at all.

So the rule (11.4): **a verb that touches more than one row ends by saying
eligible / done / skipped.** Not a habit applied where somebody remembered --
a rule, with :mod:`quill.tools.bulk_count_audit` enforcing that every bulk
action either counts or is a reviewed exception.

:class:`Counted` is the vocabulary that makes the rule cheap to follow. It is
the general form of :class:`quill.core.podcasts.download_batch.DownloadBatch`,
which stays as it is because a download batch has a fourth number nothing else
has (deferred over the cap) and wording tuned to it.

Wording rules, so the sentences read as one voice:

* Every clause carries a number. "some were skipped" is the thing this
  module exists to prevent.
* Say the skipped reason, not just the count: "3 skipped, already downloaded".
* Nothing eligible is a sentence of its own, and says *why* nothing was
  eligible rather than announcing a zero.
* Failures are never folded into skipped: a file that could not be deleted
  and a file that was deliberately kept are different news.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Counted", "plural"]


def plural(count: int, singular: str, plural_form: str = "") -> str:
    """``3 episodes`` / ``1 episode`` -- the count and its noun, agreeing."""
    word = singular if count == 1 else (plural_form or f"{singular}s")
    return f"{count} {word}"


@dataclass(frozen=True, slots=True)
class Counted:
    """What one bulk action did, in numbers that can be read aloud.

    *done* is what actually happened; *skipped* what was deliberately left
    (with *skipped_because* saying which rule left it); *failed* what was
    attempted and could not be done. *eligible* defaults to the sum, which is
    right whenever the action considered exactly the rows it was given.
    """

    done: int = 0
    skipped: int = 0
    failed: int = 0
    skipped_because: str = ""
    #: Why nothing was eligible, when nothing was: "it has no episodes yet".
    nothing_because: str = ""
    _eligible: int | None = None

    @property
    def eligible(self) -> int:
        if self._eligible is not None:
            return self._eligible
        return self.done + self.skipped + self.failed

    @property
    def touched_anything(self) -> bool:
        return bool(self.done or self.failed)

    def sentence(self, verb: str, subject: str = "", *, noun: str = "item") -> str:
        """The spoken summary. Every clause carries a number, always.

        *verb* is what was done, in the past tense as the announcement wants
        to read it ("Removed", "Marked as played"); *subject* is what it was
        done to ("The Daily"), and *noun* names a row ("episode", "file").
        """
        on = f" for {subject}" if subject.strip() else ""
        if not self.eligible:
            because = self.nothing_because.strip().rstrip(".")
            tail = f": {because}" if because else ""
            return f"Nothing to {verb.lower()}{on}{tail}."
        if not self.touched_anything:
            because = self.skipped_because.strip().rstrip(".")
            tail = f" -- {because}" if because else ""
            return (
                f"Nothing to {verb.lower()}{on}: all {plural(self.skipped, noun)} "
                f"were skipped{tail}."
            )
        parts = [f"{plural(self.eligible, noun)} eligible", f"{self.done} done"]
        if self.skipped:
            because = self.skipped_because.strip().rstrip(".")
            parts.append(f"{self.skipped} skipped" + (f", {because}" if because else ""))
        if self.failed:
            parts.append(f"{self.failed} failed")
        sentence = f"{verb}{on}: " + ", ".join(parts) + "."
        # Nothing got done and there is a reason on file: say it. A tally that
        # reads "0 done, 1 failed" and stops is the counted version of the
        # silence this vocabulary exists to replace.
        because = self.nothing_because.strip().rstrip(".")
        if not self.done and because:
            sentence += f" {because[0].upper()}{because[1:]}."
        return sentence
