"""The Spelling menu's keyboard commands: the toggle, the two hops, the teach.

Not the review dialog and not the suggestion list -- those open real wx windows
and stay shape-only. What is here is the part somebody presses in a run: Alt+F7
to teach a word, Ctrl+F7 to hop to the next one, and the switch that stops the
live check.

Two things are load-bearing in every test below and easy to lose:

* **A miss is announced.** "No further misspellings" and "No misspelling at the
  cursor" are the whole output of a key that found nothing, and a key with no
  output is a key the listener has to assume is broken.
* **A hit selects the word rather than merely landing near it.** The selection
  is what the reader reads on arrival and what Shift+F7 then acts on, so
  asserting the caret moved is not asserting the command worked.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def spelled(lite_window):
    """A window whose dictionary is a fixed, tiny word list.

    The real dictionary is a file on disk that differs between machines and
    installs, which would make every assertion here a guess about somebody
    else's Hunspell build. The commands under test are the real ones; only the
    word list is pinned.
    """

    def make(text: str, cursor: int = 0, words: set[str] | None = None):
        win = lite_window(text, cursor=cursor)
        win._spell_dictionary_cache = set(words or {"the", "quick", "brown", "fox"})
        return win

    return make


# --------------------------------------------------------------------------- #
# The live-check switch
# --------------------------------------------------------------------------- #


def test_toggle_live_spelling_flips_and_says_which_way(spelled):
    win = spelled("hello")
    first = win._live_spelling
    win.cmd_toggle_live_spelling()
    assert win._live_spelling is not first
    assert win.announcements[-1] in {
        "Spell check while typing on",
        "Spell check while typing off",
    }
    win.cmd_toggle_live_spelling()
    assert win._live_spelling is first


def test_toggle_live_spelling_says_on_when_it_is_on(spelled):
    win = spelled("hello")
    win._live_spelling = False
    win.cmd_toggle_live_spelling()
    assert win.announcements[-1] == "Spell check while typing on"
    win.cmd_toggle_live_spelling()
    assert win.announcements[-1] == "Spell check while typing off"


def test_toggle_live_spelling_resyncs_the_menu_check(spelled):
    """The menu item is a check box, and a check box that lies is worse than none."""
    win = spelled("hello")
    before = win.checks_synced
    win.cmd_toggle_live_spelling()
    assert win.checks_synced == before + 1


def test_spelling_commands_are_refused_when_the_area_is_switched_off(spelled, monkeypatch):
    """Customize Features can remove spelling entirely. The keys must say so.

    A key bound to a command in an area the user removed is still a key they can
    press, and silence there is indistinguishable from a bug.
    """
    win = spelled("teh")
    monkeypatch.setattr(win.app, "feature_enabled", lambda _area: False)
    for command in (
        "cmd_toggle_live_spelling",
        "cmd_next_misspelling",
        "cmd_previous_misspelling",
        "cmd_add_word_to_dictionary",
    ):
        getattr(win, command)()
        assert win.announcements[-1] == "Spell check is switched off in Customize Features"


# --------------------------------------------------------------------------- #
# Hopping between misspellings
# --------------------------------------------------------------------------- #


def test_next_misspelling_selects_the_word_and_names_it(spelled):
    win = spelled("the quick brxwn fox", cursor=0)
    win.cmd_next_misspelling()
    start, end = win.control.GetSelection()
    assert win.control.GetValue()[start:end] == "brxwn"
    assert win.announcements[-1] == "Misspelling: brxwn"


def test_previous_misspelling_goes_the_other_way(spelled):
    win = spelled("brxwn the quick fox", cursor=19)
    win.cmd_previous_misspelling()
    start, end = win.control.GetSelection()
    assert win.control.GetValue()[start:end] == "brxwn"
    assert win.announcements[-1] == "Misspelling: brxwn"


def test_a_clean_document_says_there_are_no_more(spelled):
    win = spelled("the quick brown fox", cursor=0)
    win.cmd_next_misspelling()
    assert win.announcements[-1] == "No misspellings found"


def test_a_miss_says_how_many_are_the_other_way(spelled):
    """ "No further misspellings" reads as "your document is clean".

    It is a lie when seven are sitting behind the caret, and the fix -- press
    the other key -- is exactly what the bare sentence does not say. QUILL has
    counted the other direction since #9; QuillLite said nothing (bad.md S9).
    """
    win = spelled("the quick brxwn fox", cursor=19)
    win.cmd_next_misspelling()
    assert win.announcements[-1] == "No misspellings ahead; 1 misspelling behind"


def test_the_count_is_plural_when_it_should_be(spelled):
    text = "brxwn zzqua fxxle end"
    win = spelled(text, cursor=len(text))
    win.cmd_next_misspelling()
    assert win.announcements[-1] == "No misspellings ahead; 3 misspellings behind"


def test_the_two_directions_word_their_misses_differently(spelled):
    """Hearing the forward sentence after pressing the backward key would send
    somebody looking at the wrong end of the document."""
    win = spelled("the quick brxwn fox", cursor=19)
    win.cmd_next_misspelling()
    forward = win.announcements[-1]
    win.control.SetInsertionPoint(0)
    win.cmd_previous_misspelling()
    assert win.announcements[-1] == "No misspellings behind; 1 misspelling ahead"
    assert forward != win.announcements[-1]


def test_hopping_touches_the_status_bar(spelled):
    """The caret moved, so the position cells are stale until something says so."""
    win = spelled("the quick brxwn fox", cursor=0)
    before = win.status_touches
    win.cmd_next_misspelling()
    assert win.status_touches > before


def test_repeated_hops_walk_forward_rather_than_sticking(spelled):
    """Press it three times, land on three different words.

    The sticking failure is the one nobody reports: the key answers, the reader
    reads a misspelling, and it is the same misspelling every time.
    """
    win = spelled("cat teh quick brxwn fxo", cursor=0)
    found = []
    for _ in range(3):
        win.cmd_next_misspelling()
        start, end = win.control.GetSelection()
        found.append(win.control.GetValue()[start:end])
        win.control.SetInsertionPoint(end)
    assert found == ["teh", "brxwn", "fxo"]


def test_the_word_the_caret_is_already_on_is_not_offered_again(spelled):
    """Strictly *after* the caret, which is what makes a run of presses advance.

    The cost, recorded here rather than discovered: with the caret at position 0
    of a document whose first word is wrong, Ctrl+F7 goes to the second one. F7
    reviews from the top, and that is the command for "check the whole thing".
    Shared with QUILL (quill.core.spellcheck), so it is not QuillLite's to change
    alone.
    """
    win = spelled("teh quick brxwn fox", cursor=0)
    win.cmd_next_misspelling()
    start, end = win.control.GetSelection()
    assert win.control.GetValue()[start:end] == "brxwn"


# --------------------------------------------------------------------------- #
# Teaching a word
# --------------------------------------------------------------------------- #


def test_add_word_teaches_the_word_the_caret_is_inside(spelled):
    """Inside, not starting at: the caret is usually in the middle of the word
    somebody has just heard called a misspelling."""
    win = spelled("the quick brxwn fox", cursor=13)
    win.cmd_add_word_to_dictionary()
    assert "brxwn" in win.announcements[-1]
    assert win.announcements[-1].startswith("Added brxwn to ")


def test_add_word_says_which_of_the_two_dictionaries_it_went_to(spelled):
    """There are two, so "added to dictionary" does not answer the question."""
    win = spelled("the quick brxwn fox", cursor=13)
    win.app.settings.share_quill_dictionary = False
    win.cmd_add_word_to_dictionary()
    assert "your QuillLite dictionary" in win.announcements[-1]


def test_add_word_names_the_shared_dictionary_when_sharing_is_on(spelled, tmp_path, monkeypatch):
    """Isolated, because "shared" means QUILL's own data folder.

    ``tmp_path`` was an unused parameter here until 2026-09-17 and the test was
    writing its made-up word into the **developer's real** personal dictionary,
    every run, for good. Nothing noticed, because each app cached the list at
    startup: within one run the word stayed underlined, so the assertion still
    passed while the file quietly grew. Making the cache notice the file change
    (bad.md S10) is what surfaced it -- the second run of the suite failed,
    because by then the word really was taught.

    ``QUILL_DATA_DIR`` is honoured under the dev-build flag ``tests/conftest.py``
    sets for the whole session, so this points the shared folder at a temporary
    one for the duration.
    """
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "quill-data"))
    win = spelled("the quick brxwn fox", cursor=13)
    win.app.settings.share_quill_dictionary = True
    win.cmd_add_word_to_dictionary()
    assert "QUILL's shared dictionary" in win.announcements[-1]
    # And it really went there, rather than into QuillLite's own folder.
    taught = tmp_path / "quill-data" / "dictionaries" / "personal.json"
    assert taught.is_file() and "brxwn" in taught.read_text(encoding="utf-8")


def test_add_word_on_a_correctly_spelled_word_says_there_is_nothing_to_teach(spelled):
    win = spelled("the quick brown fox", cursor=12)
    win.cmd_add_word_to_dictionary()
    assert win.announcements[-1] == "No misspelling at the cursor"


def test_a_taught_word_stops_being_a_misspelling(spelled):
    """The end-to-end claim the command actually makes.

    Teaching a word and still being stopped on it next press is the failure this
    catches, and it is invisible to a test that only reads the announcement.
    """
    win = spelled("the quick brxwn fox", cursor=13)
    win.cmd_add_word_to_dictionary()
    win.control.SetInsertionPoint(0)
    win.cmd_next_misspelling()
    assert win.announcements[-1] == "No misspellings found"


def test_teaching_drops_the_cached_dictionary(spelled):
    """The cache exists so the live check does not read a file per keystroke.

    Which means a word taught into the file and not into the cache is a word the
    editor keeps calling wrong until the document is closed.
    """
    win = spelled("the quick brxwn fox", cursor=13)
    assert win._spell_dictionary_cache is not None
    win.cmd_add_word_to_dictionary()
    assert win._spell_dictionary_cache is None
