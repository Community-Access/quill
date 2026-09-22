"""Which number a new QuillLite document gets, and why a closed one's comes back.

Reported by a user: open a window, close it, open another, and the new one is
document 2 rather than document 1 again. The counter only ever went up.

The number is not a record of how many documents a session has seen -- it is the
**handle**. Alt+1 to Alt+9 reach the first nine of them, the Window menu is
written in them, and an MDI child is not in Alt+Tab, so the title's leading
number is the only way to name the window you want. Spent numbers spend the
handle: open and close ten times in a morning and the eleventh document has no
Alt+digit at all, while the ten numbers that would work belong to nothing.

The rule that does *not* change is the one the monotonic counter was protecting:
an open document is never renumbered. A number moving under somebody who is away
from that window is exactly the "document 3 is a different document now" problem.
Only a number nothing is using is handed out again.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.apps.lite import QuillLiteApp

next_number = QuillLiteApp.next_document_number


def _app(*numbers: int) -> SimpleNamespace:
    """A stand-in app holding open documents with the given numbers."""
    return SimpleNamespace(frames=[SimpleNamespace(number=n) for n in numbers])


def test_the_first_document_is_one() -> None:
    assert next_number(_app()) == 1


def test_documents_count_up_while_they_all_stay_open() -> None:
    app = _app()
    for expected in (1, 2, 3):
        assert next_number(app) == expected
        app.frames.append(SimpleNamespace(number=expected))


def test_a_closed_document_gives_its_number_back() -> None:
    # One window, closed, then a new one: the new one is document 1, not 2.
    assert next_number(_app()) == 1


def test_the_lowest_free_number_wins_not_the_highest() -> None:
    # Documents 1, 2 and 3 are open; 2 closes. The next new document is 2,
    # because 2 is the free number a person can still press Alt+2 for.
    assert next_number(_app(1, 3)) == 2


def test_an_open_document_is_never_renumbered() -> None:
    # The gap is filled, and the documents on either side of it keep what they
    # had -- which is the whole reason the number is worth putting in a title.
    app = _app(1, 3)
    app.frames.append(SimpleNamespace(number=next_number(app)))
    assert sorted(frame.number for frame in app.frames) == [1, 2, 3]


def test_numbers_stay_inside_the_alt_digit_range_across_churn() -> None:
    # The user's actual session: one document at a time, opened and closed all
    # morning. Every one of them is document 1 and has Alt+1.
    app = _app()
    for _ in range(20):
        number = next_number(app)
        assert number == 1
        app.frames.append(SimpleNamespace(number=number))
        app.frames.clear()
