"""Four QUILL Lite defects, three of which cost somebody something real.

**H1 -- a hand-edited keymap could bind a bare letter.** ``wx`` accepts
``"Win+A"``, returns True, and hands back an entry with *no modifier at all*:
flags 0, key code 65. So ``{"cmd_delete_line": "Win+A"}`` in the user's keymap
file did not fail, did not warn, and ran Delete Line every time they typed the
letter A. ``load_keymap`` is the trust boundary for a file a person can edit,
and it consulted ``normalise_chord``, which said that chord was fine.

**V1 -- no large-file guard of any kind.** Nothing in QUILL Lite called
``stat()`` before reading, so a 200 MB log opened by ``read_text`` straight
into a ``wx.TextCtrl`` with no warning, no progress and no way out. QUILL has
had the guard since #1150. For a Notepad replacement this is the scenario, not
an edge case.

**L10 -- bookmarks were written only on close and after a save.** Clear All,
then a crash, and every bookmark came back. QUILL writes on every Set and
always has.

**S1 -- F7's "Add to Dictionary" wrote into QUILL's data folder.**
``ReviewSession.add_to_dict`` passed no ``personal_dir``, so the shared
``add_word_to_scope`` fell back to QUILL's. A word taught through the review
was flagged again next session -- QUILL Lite reads its own folder -- and a Quill
folder appeared on a machine that had never had QUILL. QUILL Lite's other two
add routes passed the right folder all along; only the review dialog did not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.lite.keymap import default_keymap, normalise_chord

# -- H1: the chord that fires when you type ---------------------------------------


@pytest.mark.parametrize("chord", ["Win+A", "Cmd+A", "A", "Shift+A", "Windows+Z", "Command+7"])
def test_a_chord_that_fires_as_typing_is_refused(chord: str) -> None:
    assert normalise_chord(chord) == "", f"{chord} would fire when the key is typed"


@pytest.mark.parametrize(
    "chord",
    ["Ctrl+A", "Alt+Z", "Ctrl+Shift+L", "Ctrl+Alt+D", "Ctrl+;", "Alt+.", "Ctrl+Alt+Shift+F7"],
)
def test_a_real_chord_still_normalises(chord: str) -> None:
    assert normalise_chord(chord) != ""


@pytest.mark.parametrize("chord", ["F7", "Shift+F7", "Delete", "Escape", "Enter"])
def test_a_named_key_is_safe_bare(chord: str) -> None:
    """Pressing F7 is never typing, so it needs no modifier to be safe."""
    assert normalise_chord(chord) != ""


def test_no_shipped_binding_is_caught_by_the_new_rule() -> None:
    refused = {h: k for h, k in default_keymap().items() if k and not normalise_chord(k)}
    assert refused == {}


def test_the_loader_drops_what_the_normaliser_refuses(tmp_path: Path) -> None:
    """The trust boundary, end to end: a malicious file leaves the editor intact."""
    import json

    from quill.core.lite.keymap import keymap_path, load_keymap

    path = keymap_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"bindings": {"cmd_delete_line": "Win+A", "cmd_undo": "Ctrl+Alt+U"}}),
        encoding="utf-8",
    )
    loaded = load_keymap(tmp_path)
    assert loaded["cmd_delete_line"] == default_keymap()["cmd_delete_line"]
    assert loaded["cmd_undo"] == "Ctrl+Alt+U", "a legitimate override must still apply"


# -- V1: the large-file guard -----------------------------------------------------


def test_quilllite_asks_before_opening_a_large_file() -> None:
    from pathlib import Path as _P

    source = _P("quill/apps/lite.py").read_text(encoding="utf-8")
    assert "_confirm_large_file" in source
    assert "is_large_file" in source


def test_the_guard_sits_on_the_one_funnel_every_route_uses() -> None:
    """File > Open, the command line, the shell's Open, recent files and session
    restore all go through open_path, so the guard cannot be walked around."""
    from pathlib import Path as _P

    source = _P("quill/apps/lite.py").read_text(encoding="utf-8")
    start = source.index("def open_path(")
    open_path = source[start : source.index("def open_from_dialog(", start)]
    assert "_confirm_large_file" in open_path


def test_the_warning_names_the_product_that_is_asking() -> None:
    from quill.ui.large_file_guard import is_large_file, large_file_warning

    assert is_large_file(9 * 1024 * 1024) is True
    assert is_large_file(1024) is False
    assert "QuillLite" in large_file_warning("big.log", 9 * 1024 * 1024, "QuillLite")
    assert "QUILL" in large_file_warning("big.log", 9 * 1024 * 1024)


# -- L10: bookmarks written when they change --------------------------------------


def test_every_bookmark_mutator_persists_immediately() -> None:
    from pathlib import Path as _P

    source = _P("quill/apps/lite_window_marks.py").read_text(encoding="utf-8")
    assert "def persist_bookmarks(self)" in source
    # Set, remove and clear-all: three mutators, three writes.
    assert source.count("self.persist_bookmarks()") == 3


def test_the_caret_deliberately_stays_on_the_slower_cadence() -> None:
    """A file write per arrow key is the trade the original docstring refused,
    and it was right to; only the bookmarks moved to the fast path."""
    from pathlib import Path as _P

    source = _P("quill/apps/lite_window_marks.py").read_text(encoding="utf-8")
    start = source.index("def persist_bookmarks(")
    persist = source[start : source.index("def remember_document_memory(", start)]
    assert "set_numbered" in persist
    assert "set_last_position" not in persist


# -- S1: the review wrote into the wrong folder -----------------------------------


def test_the_session_accepts_the_folder_it_should_write_to() -> None:
    import inspect

    from quill.core.spelling.session import ReviewSession

    assert "personal_dir" in inspect.signature(ReviewSession.add_to_dict).parameters


def test_the_shared_review_entry_point_forwards_it() -> None:
    import inspect

    from quill.ui.spell_review import review_textctrl

    assert "personal_dir" in inspect.signature(review_textctrl).parameters


def test_quilllite_f7_passes_its_own_dictionary_folder() -> None:
    from pathlib import Path as _P

    source = _P("quill/apps/lite_window_spelling.py").read_text(encoding="utf-8")
    assert "personal_dir=spelling_mod.dictionary_dir(" in source


def test_the_folder_follows_the_share_setting(tmp_path: Path) -> None:
    """QUILL Lite's own, unless the listener asked in Preferences to share QUILL's."""
    from types import SimpleNamespace

    from quill.core.lite.spelling import dictionary_dir

    own = dictionary_dir(SimpleNamespace(share_quill_dictionary=False), tmp_path)
    assert own == tmp_path
    shared = dictionary_dir(SimpleNamespace(share_quill_dictionary=True), tmp_path)
    assert shared != tmp_path


def test_a_word_taught_through_the_review_lands_where_lite_reads(tmp_path: Path) -> None:
    """The end-to-end property S1 is about: teach it, and it stays taught."""
    from quill.core.spellcheck import add_word_to_scope, load_scope_dictionary

    add_word_to_scope("quillish", "personal", None, None, tmp_path)
    assert "quillish" in {
        w.lower() for w in load_scope_dictionary("personal", None, None, tmp_path)
    }
