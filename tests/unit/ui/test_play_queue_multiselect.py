"""The Play Queue, once it could hold more than one selection (list.md 2.4).

Every other episode list in QUILL Cast already read a multiple selection; the
queue -- the one list whose whole job is a running order somebody rearranges --
was single-select, so removing six episodes meant six round trips.

Making a ``wx.ListBox`` extended is one style flag and three quiet traps, and
this file is those three:

* ``GetSelection`` cannot be used on an extended list at all -- wxMSW raises a
  C++ assertion -- so every single-row verb that read it (Play Now, Move Up,
  Mark for Move) breaks the moment the style flag changes.
* ``SetSelection`` *adds* rather than replaces, so a reload accumulates every
  row it ever landed on, and the next Remove takes all of them.
* Removing front to back renumbers the queue underneath the loop, so from the
  second index onward it takes out the wrong slots.

Plus the rule the gate cares about: a verb that touched twenty rows says
twenty.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary

wx = pytest.importorskip("wx")

from quill.ui.podcasts.play_queue_dialog import PlayQueueDialog  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def frame():
    window = wx.Frame(None)
    yield window
    window.Destroy()


def _library() -> PodcastLibrary:
    show = PodcastShow(
        id="show-1",
        title="Main Menu",
        feed_url="https://e/f.xml",
        episodes=[
            PodcastEpisode(
                guid=guid,
                title=f"Episode {guid}",
                audio_url=f"https://e/{guid}.mp3",
                published="2026-07-01T00:00:00",
            )
            for guid in ("a", "b", "c", "d", "e")
        ],
    )
    library = PodcastLibrary(shows=[show])
    library.queue = [QueueItem("show-1", guid, added_at="2026-07-01T00:00:00") for guid in "abcde"]
    return library


@pytest.fixture
def queue_dialog(frame):
    said: list[str] = []
    library = _library()
    dialog = PlayQueueDialog(frame, library=library, announce_cb=said.append)
    yield dialog, library, said
    dialog.dialog.Destroy()


def _order(library: PodcastLibrary) -> list[str]:
    return [item.episode_guid for item in library.queue]


def _select(dialog, *rows: int) -> None:
    _deselect_all(dialog)
    for row in rows:
        dialog._list.SetSelection(row)


def _deselect_all(dialog) -> None:
    """wx.ListBox has Deselect(n) and no DeselectAll."""
    for row in list(dialog._list.GetSelections()):
        dialog._list.Deselect(row)


# -- the selection itself --------------------------------------------------------


def test_the_list_takes_more_than_one_row(queue_dialog) -> None:
    dialog, _library_, _said = queue_dialog
    assert dialog._list.GetWindowStyleFlag() & wx.LB_EXTENDED


def test_several_rows_read_back_in_queue_order(queue_dialog) -> None:
    dialog, _library_, _said = queue_dialog
    _select(dialog, 3, 0, 2)

    assert dialog._selected_indexes() == [0, 2, 3]


def test_nothing_selected_is_an_empty_list_not_a_row(queue_dialog) -> None:
    dialog, _library_, _said = queue_dialog
    _deselect_all(dialog)

    assert dialog._selected_indexes() == []
    assert dialog._selected() == -1


# -- the trap that disables the single-row verbs ---------------------------------


def test_the_single_row_verbs_still_know_what_is_selected(queue_dialog) -> None:
    """wxMSW does not merely answer wxNOT_FOUND here -- it asserts.

    ``GetSelection() can't be used with multiple-selection listboxes`` is a
    C++ assertion, so a single-row verb that kept reading it would fail
    loudly on Windows and quietly elsewhere. Every one of them reads the
    selection list instead.
    """
    dialog, _library_, _said = queue_dialog
    _select(dialog, 2)

    with pytest.raises(wx.wxAssertionError):
        dialog._list.GetSelection()
    assert dialog._selected() == 2


def test_moving_a_row_still_works(queue_dialog) -> None:
    dialog, library, said = queue_dialog
    _select(dialog, 2)

    dialog._nudge(-1)

    assert _order(library) == ["a", "c", "b", "d", "e"]
    assert "position 2" in said[-1]


def test_mark_for_move_still_works(queue_dialog) -> None:
    dialog, library, said = queue_dialog
    _select(dialog, 0)
    dialog._on_mark()
    _select(dialog, 3)

    dialog._move_marked(above=False)

    assert _order(library) == ["b", "c", "d", "a", "e"]


# -- the trap that grows the selection -------------------------------------------


def test_a_reload_lands_on_exactly_one_row(queue_dialog) -> None:
    """``SetSelection`` adds on an extended list; without the deselect a few
    reloads would leave everything selected and Remove would take the lot."""
    dialog, _library_, _said = queue_dialog
    _select(dialog, 0)

    dialog._reload(select=2)
    dialog._reload(select=4)

    assert dialog._selected_indexes() == [4]


# -- removing many ---------------------------------------------------------------


def test_removing_several_takes_exactly_those(queue_dialog) -> None:
    """Front to back would renumber the queue under the loop and take out the
    wrong slots from the second one onward."""
    dialog, library, _said = queue_dialog
    _select(dialog, 0, 2, 4)

    dialog._on_remove()

    assert _order(library) == ["b", "d"]


def test_removing_several_says_how_many(queue_dialog) -> None:
    dialog, _library_, said = queue_dialog
    _select(dialog, 1, 2, 3)

    dialog._on_remove()

    assert "3" in said[-1]
    assert "Removed" in said[-1]


def test_removing_one_still_reads_as_one(queue_dialog) -> None:
    dialog, library, said = queue_dialog
    _select(dialog, 1)

    dialog._on_remove()

    assert _order(library) == ["a", "c", "d", "e"]
    assert "1 episode" in said[-1]


def test_removing_nothing_says_so_rather_than_silently_doing_nothing(queue_dialog) -> None:
    dialog, library, said = queue_dialog
    _deselect_all(dialog)

    dialog._on_remove()

    assert _order(library) == list("abcde")
    assert "Nothing is selected" in said[-1]


def test_removing_the_marked_row_forgets_the_mark(queue_dialog) -> None:
    dialog, _library_, _said = queue_dialog
    _select(dialog, 2)
    dialog._on_mark()
    _select(dialog, 1, 2)

    dialog._on_remove()

    assert dialog._marked_index is None


# -- where focus lands when the rows under it are the ones removed ----------------


def test_removing_the_tail_lands_on_the_new_last_row(queue_dialog) -> None:
    """Not on row 0, which is where it used to go.

    ``_reload(select=...)`` is given ``min(indexes)``, a queue index; after the
    removal that index is past the end, so the lookup found nothing and the
    fallback selected row 0. Remove the tail of a forty-item queue and focus
    jumped to the top, where the reader read row 1 as though that were where the
    listener had asked to be -- silent, and it loses their place in the run.
    """
    dialog, library, _said = queue_dialog
    _select(dialog, 3, 4)

    dialog._on_remove()

    assert _order(library) == ["a", "b", "c"]
    assert dialog._selected_indexes() == [2]  # the new last row, not 0


def test_removing_from_the_middle_still_lands_where_the_rows_were(queue_dialog) -> None:
    """The ordinary case keeps working: the row that took their place."""
    dialog, library, _said = queue_dialog
    _select(dialog, 1, 2)

    dialog._on_remove()

    assert _order(library) == ["a", "d", "e"]
    assert dialog._selected_indexes() == [1]
