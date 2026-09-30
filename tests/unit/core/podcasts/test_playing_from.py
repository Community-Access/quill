"""Where the playing episode came from (ear.md R6).

Three different evenings -- the rest of the queue, the rest of a folder, or
nothing -- and a listener who cannot see the window has no other way to tell
which one they are in.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.playing_from import QUEUE, folder_path, playing_from
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    news = library.add_folder("News")
    mornings = library.add_folder("Mornings", parent_folder_id=news.id)
    library.shows.append(
        PodcastShow(id="s1", title="The Daily", feed_url="https://e/f.xml", folder_id=mornings.id)
    )
    library.shows.append(PodcastShow(id="s2", title="Loose", feed_url="https://e/g.xml"))
    return library


def test_a_nested_folder_reads_as_a_path() -> None:
    library = _library()
    assert playing_from(library, library.find_show("s1")) == "News > Mornings"


def test_the_queue_wins_over_the_folder() -> None:
    """The more specific answer to the question the line exists for."""
    library = _library()
    assert playing_from(library, library.find_show("s1"), from_queue=True) == QUEUE


def test_an_unfiled_show_says_nothing_rather_than_nowhere() -> None:
    """A report line with nothing to say should not be printed at all."""
    library = _library()
    assert playing_from(library, library.find_show("s2")) == ""


def test_nothing_playing_says_nothing() -> None:
    assert playing_from(_library(), None) == ""


def test_an_inbox_show_says_the_inbox() -> None:
    library = _library()
    library.find_show("s2").route_to_inbox = True
    assert playing_from(library, library.find_show("s2")) == "the Inbox"


def test_a_folder_whose_parent_vanished_still_names_itself() -> None:
    library = _library()
    orphan = library.add_folder("Orphan", parent_folder_id="gone")
    assert folder_path(library, orphan.id) == "Orphan"


def test_a_cycle_in_the_folder_tree_terminates() -> None:
    """A hand-edited file can contain one, and it must not hang the report."""
    library = _library()
    first = library.add_folder("A")
    second = library.add_folder("B", parent_folder_id=first.id)
    first.parent_folder_id = second.id
    path = folder_path(library, second.id)
    assert path and len(path) < 200
