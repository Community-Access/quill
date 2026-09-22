"""The triage that turned sixty-nine documents into three rows.

The bug this module exists for was not subtle and was never caught by a test,
because nothing ever asked what happens to the *store* across many bad exits.
Each test below is one sentence of that answer, and the last one is the
invariant the whole design rests on: nothing is ever silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.recovery_triage import (
    DEFAULT_KEEP_DAYS,
    describe_restored,
    describe_tidy,
    fingerprint,
    is_untitled,
    row_label,
    size_phrase,
    summarise_recovery,
    triage,
    when_phrase,
)

_NOW = 1_700_000_000.0
_DAY = 86400.0


@dataclass
class FakeSlot:
    """A recovery slot's whole surface as far as triage is concerned."""

    mode: str
    original_path: str
    content_path: Path

    @property
    def title(self) -> str:
        return Path(self.original_path).name if self.original_path else "Untitled"


def _slot(
    tmp_path: Path,
    name: str,
    text: str,
    *,
    path: str = "",
    age_days: float = 0.0,
    mode: str = "plain",
) -> FakeSlot:
    content = tmp_path / name
    content.write_text(text, encoding="utf-8")
    written = _NOW - age_days * _DAY
    import os

    os.utime(content, (written, written))
    return FakeSlot(mode=mode, original_path=path, content_path=content)


def test_identical_untitled_copies_collapse_to_one(tmp_path: Path) -> None:
    """The reported case: 67 copies of "body" were 67 rows in a Yes/No box."""
    slots = [_slot(tmp_path, f"{index}.txt", "body") for index in range(67)]
    result = triage(slots, now=_NOW)
    assert len(result.offer) == 1
    assert len(result.duplicates) == 66
    assert result.copies_of(result.offer[0]) == 67


def test_the_survivor_of_a_duplicate_group_is_the_newest(tmp_path: Path) -> None:
    """The newest copy is the one whose age a person would recognise."""
    old = _slot(tmp_path, "old.txt", "same", age_days=5)
    new = _slot(tmp_path, "new.txt", "same", age_days=1)
    result = triage([old, new], now=_NOW)
    assert result.offer == (new,)
    assert result.duplicates == (old,)


def test_different_text_is_never_folded_together(tmp_path: Path) -> None:
    first = _slot(tmp_path, "a.txt", "one")
    second = _slot(tmp_path, "b.txt", "two")
    result = triage([first, second], now=_NOW)
    assert len(result.offer) == 2
    assert result.duplicates == ()


def test_the_same_text_from_two_different_files_is_two_documents(tmp_path: Path) -> None:
    """Two files that happen to agree are still two files."""
    first = _slot(tmp_path, "a.txt", "same", path=r"C:\one\notes.md")
    second = _slot(tmp_path, "b.txt", "same", path=r"C:\two\notes.md")
    result = triage([first, second], now=_NOW)
    assert len(result.offer) == 2


def test_the_same_text_in_two_modes_is_two_documents(tmp_path: Path) -> None:
    """A rich slot and a plain slot restore through different readers."""
    plain = _slot(tmp_path, "a.txt", "same")
    rich = _slot(tmp_path, "b.rtf", "same", mode="rich")
    result = triage([plain, rich], now=_NOW)
    assert len(result.offer) == 2


def test_copies_older_than_the_keep_window_are_expired(tmp_path: Path) -> None:
    fresh = _slot(tmp_path, "fresh.txt", "new", age_days=1)
    ancient = _slot(tmp_path, "old.txt", "old", age_days=DEFAULT_KEEP_DAYS + 1)
    result = triage([fresh, ancient], now=_NOW)
    assert result.offer == (fresh,)
    assert result.stale == (ancient,)


def test_zero_keep_days_expires_nothing(tmp_path: Path) -> None:
    """The pre-2026-09-21 behaviour stays reachable for somebody who wants it."""
    ancient = _slot(tmp_path, "old.txt", "old", age_days=4000)
    result = triage([ancient], now=_NOW, keep_days=0)
    assert result.offer == (ancient,)
    assert result.stale == ()


def test_expiry_runs_before_duplicate_folding(tmp_path: Path) -> None:
    """An expired slot must not earn a row by being the newest expired one."""
    slots = [
        _slot(tmp_path, f"{index}.txt", "same", age_days=DEFAULT_KEEP_DAYS + index + 1)
        for index in range(3)
    ]
    result = triage(slots, now=_NOW)
    assert result.offer == ()
    assert len(result.stale) == 3


def test_untitled_work_is_dropped_only_when_the_setting_says_so(tmp_path: Path) -> None:
    scratch = _slot(tmp_path, "scratch.txt", "paste")
    named = _slot(tmp_path, "named.txt", "letter", path=r"C:\work\letter.md")

    kept = triage([scratch, named], now=_NOW)
    assert {id(slot) for slot in kept.offer} == {id(scratch), id(named)}

    dropped = triage([scratch, named], now=_NOW, offer_untitled=False)
    assert dropped.offer == (named,)
    assert dropped.untitled == (scratch,)


def test_every_slot_lands_in_exactly_one_bucket(tmp_path: Path) -> None:
    """The invariant a caller relies on to restore some and delete the rest."""
    slots = [
        _slot(tmp_path, "dup1.txt", "same"),
        _slot(tmp_path, "dup2.txt", "same"),
        _slot(tmp_path, "old.txt", "gone", age_days=99),
        _slot(tmp_path, "scratch.txt", "paste"),
        _slot(tmp_path, "named.txt", "letter", path=r"C:\work\letter.md"),
    ]
    result = triage(slots, now=_NOW, offer_untitled=False)
    landed = list(result.offer) + list(result.tidied)
    assert len(landed) == len(slots)
    assert {id(slot) for slot in landed} == {id(slot) for slot in slots}
    assert result.total == len(slots)


def test_an_unreadable_slot_is_never_folded_into_a_readable_one(tmp_path: Path) -> None:
    """Failing towards "these differ" keeps work; the other way deletes it."""
    real = _slot(tmp_path, "real.txt", "same")
    ghost = FakeSlot(mode="plain", original_path="", content_path=tmp_path / "gone.txt")
    assert fingerprint(ghost) != fingerprint(real)
    result = triage([real, ghost], now=_NOW)
    assert len(result.offer) == 2


def test_an_unreadable_slot_is_treated_as_new_not_ancient(tmp_path: Path) -> None:
    """Expiry deletes; a filesystem that will not answer is no reason to."""
    ghost = FakeSlot(mode="plain", original_path="", content_path=tmp_path / "gone.txt")
    result = triage([ghost], now=_NOW, keep_days=1)
    assert result.stale == ()


def test_is_untitled_reads_the_original_path(tmp_path: Path) -> None:
    assert is_untitled(_slot(tmp_path, "a.txt", "x"))
    assert is_untitled(_slot(tmp_path, "b.txt", "x", path="   "))
    assert not is_untitled(_slot(tmp_path, "c.txt", "x", path=r"C:\a\b.md"))


def test_the_row_says_how_much_and_when_and_how_many(tmp_path: Path) -> None:
    """The three facts a listener cannot get by looking at the list."""
    slots = [_slot(tmp_path, f"{index}.txt", "body") for index in range(67)]
    result = triage(slots, now=_NOW)
    label = row_label(result.offer[0], result.copies_of(result.offer[0]), now=_NOW)
    assert "Untitled" in label
    assert "4 characters" in label
    assert "67 identical copies" in label


def test_a_named_row_carries_its_path(tmp_path: Path) -> None:
    slot = _slot(tmp_path, "a.txt", "x" * 20, path=r"C:\work\letter.md")
    label = row_label(slot, 1, now=_NOW)
    assert "letter.md" in label
    assert r"C:\work\letter.md" in label
    assert "identical copies" not in label


def test_size_phrase_measures_rich_text_in_bytes(tmp_path: Path) -> None:
    """An RTF file is mostly envelope; quoting it as characters overstates it."""
    rich = _slot(tmp_path, "a.rtf", "x" * 300, mode="rich")
    assert size_phrase(rich) == "300 bytes of rich text"
    plain = _slot(tmp_path, "b.txt", "x" * 300)
    assert size_phrase(plain) == "300 characters"
    single = _slot(tmp_path, "c.txt", "x")
    assert size_phrase(single) == "1 character"


def test_when_phrase_is_relative_not_a_timestamp(tmp_path: Path) -> None:
    assert when_phrase(_slot(tmp_path, "a.txt", "x", age_days=0.01), now=_NOW) == "in the last hour"
    assert when_phrase(_slot(tmp_path, "b.txt", "x", age_days=1.2), now=_NOW) == "yesterday"
    assert when_phrase(_slot(tmp_path, "c.txt", "x", age_days=4), now=_NOW) == "4 days ago"
    assert when_phrase(_slot(tmp_path, "d.txt", "x", age_days=90), now=_NOW) == "3 months ago"


def test_the_summary_leads_with_the_count_and_says_what_was_tidied(tmp_path: Path) -> None:
    slots = [_slot(tmp_path, f"{index}.txt", "body") for index in range(67)]
    slots.append(_slot(tmp_path, "old.txt", "gone", age_days=99))
    result = triage(slots, now=_NOW)
    said = summarise_recovery(result)
    assert said.startswith("Unsaved work from 1 document.")
    assert "66 identical copies" in said
    assert "older than a month" in said


def test_tidying_is_never_silent_but_says_nothing_when_nothing_happened(
    tmp_path: Path,
) -> None:
    """Tidying that happens without a word reads as work having gone missing."""
    clean = triage([_slot(tmp_path, "a.txt", "x")], now=_NOW)
    assert describe_tidy(clean) == ""
    assert summarise_recovery(clean) == "Unsaved work from 1 document."


def test_an_empty_store_says_so(tmp_path: Path) -> None:
    assert summarise_recovery(triage([], now=_NOW)) == "There is no unsaved work to come back to."


def test_describe_restored_never_goes_quiet() -> None:
    """ "Restored none" is a result; silence is a command that did not run."""
    assert describe_restored(0, 0) == "Nothing was restored."
    assert "none of the 3" in describe_restored(0, 3)
    assert describe_restored(1, 1).startswith("Restored 1 unsaved document.")
    assert describe_restored(2, 5).startswith("Restored 2 of 5.")
    # Always says the work is still unsaved: restoring is not saving, and a
    # window that looks like a document is exactly where that gets forgotten.
    assert "Save each one to keep it." in describe_restored(2, 5)
