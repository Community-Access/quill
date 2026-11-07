"""The words the Say commands speak, and the press counting under them.

``quill.core.say_commands`` is what both editors say; ``PressStreak`` is how a
quick second or third press is told apart from a fresh one. Both are wx-free,
so every rule is checked here without a window.
"""

from __future__ import annotations

from datetime import datetime

from quill.core import say_commands as say
from quill.core.press_streak import PressStreak
from quill.core.say_commands import ClipboardContents

# -- PressStreak ----------------------------------------------------------- #


def test_quick_presses_climb_and_then_start_again() -> None:
    streak = PressStreak(0.5, 3)
    assert [streak.press("x", t) for t in (0.0, 0.2, 0.4, 0.6)] == [1, 2, 3, 1]


def test_a_slow_press_is_a_first_press() -> None:
    streak = PressStreak(0.5)
    assert streak.press("x", 0.0) == 1
    assert streak.press("x", 0.9) == 1


def test_another_command_in_between_starts_over() -> None:
    streak = PressStreak(0.5)
    streak.press("x", 0.0)
    streak.press("y", 0.1)
    assert streak.press("x", 0.2) == 1


def test_a_lower_ceiling_per_press_wraps_sooner() -> None:
    streak = PressStreak(0.5, 3)
    assert [streak.press("t", t, max_count=2) for t in (0.0, 0.1, 0.2)] == [1, 2, 1]


# -- the clipboard --------------------------------------------------------- #


def test_text_is_said_as_it_is() -> None:
    assert say.describe_clipboard(ClipboardContents(text="hello")) == "hello"


def test_long_text_says_how_much_is_left_and_how_to_read_it() -> None:
    text = "a" * (say.SPEAK_LIMIT + 5)
    said = say.describe_clipboard(ClipboardContents(text=text))
    assert said.startswith("a" * say.SPEAK_LIMIT)
    assert "and 5 more characters" in said and "three times" in said


def test_files_win_over_their_path_text_and_are_named() -> None:
    files = tuple(f"C:\\x\\f{n}.txt" for n in range(12))
    said = say.describe_clipboard(ClipboardContents(text=files[0], files=files))
    assert said.startswith("12 files on the clipboard: f0.txt, f1.txt")
    assert said.endswith("and 2 more")


def test_one_file_is_singular() -> None:
    said = say.describe_clipboard(ClipboardContents(files=("C:\\a.txt",)))
    assert said == "1 file on the clipboard: a.txt"


def test_empty_blank_and_picture_clipboards_each_say_so() -> None:
    assert say.describe_clipboard(ClipboardContents()) == "The clipboard is empty"
    assert "blank space, 3 characters" in say.describe_clipboard(ClipboardContents(text="  \n"))
    assert "not text" in say.describe_clipboard(ClipboardContents(other=True))


def test_spelling_is_capped_and_says_so() -> None:
    assert say.spell_clipboard(ClipboardContents(text="Hi")) == "cap H. I"
    long = say.spell_clipboard(ClipboardContents(text="b" * 250))
    assert long.startswith(f"The first {say.SPELL_LIMIT} of 250 characters: B. B")


def test_a_second_press_on_files_gives_their_full_paths() -> None:
    contents = ClipboardContents(files=("C:\\a\\one.txt", "D:\\two.txt"))
    assert say.spell_clipboard(contents) == "C:\\a\\one.txt; D:\\two.txt"
    assert say.review_text(contents) == "C:\\a\\one.txt\nD:\\two.txt"


def test_append_puts_the_selection_on_its_own_line_without_a_blank_one() -> None:
    assert say.append_selection("", "new") == "new"
    assert say.append_selection("old", "new") == "old\nnew"
    assert say.append_selection("old\n", "new") == "old\nnew"
    assert say.describe_append("new", "old\nnew") == (
        "Appended 3 characters to the clipboard, which now holds 7 characters"
    )


def test_clear_says_whether_there_was_anything() -> None:
    assert say.describe_clear(True) == "Cleared the clipboard"
    assert say.describe_clear(False) == "The clipboard was already empty"


def test_save_normalises_line_breaks_and_writes_utf8(tmp_path) -> None:
    import os

    target = tmp_path / "clip.txt"
    say.save_clipboard_text(target, "one\r\ntwo\rthree\nfour é")
    expected = os.linesep.join(["one", "two", "three", "four é"])
    assert target.read_bytes() == expected.encode("utf-8")
    assert say.describe_saved_clipboard(target, "abc") == "Saved 3 characters to clip.txt"


def test_the_suggested_name_carries_the_date_and_time() -> None:
    name = say.suggested_clipboard_file_name(datetime(2026, 11, 6, 14, 5))
    assert name == "clipboard 2026-11-06 1405.txt"


# -- the time, the documents, the log -------------------------------------- #


def test_the_time_reads_like_a_clock() -> None:
    assert say.say_time(datetime(2026, 11, 6, 0, 7)) == "12:07 AM"
    assert say.say_time(datetime(2026, 11, 6, 12, 0)) == "12:00 PM"
    assert say.say_time(datetime(2026, 11, 6, 23, 59)) == "11:59 PM"


def test_the_date_is_said_in_full() -> None:
    assert say.say_date(datetime(2026, 11, 6, 9, 0)) == "Friday, November 6, 2026"


def test_open_documents_are_counted_then_named_with_the_current_one_marked() -> None:
    assert say.windows_open_count(["a"]) == "1 document open"
    assert say.windows_open_count(["a", "b"]) == "2 documents open"
    assert say.windows_open_names(["a", "b"], 1) == "2 documents: a, b (current)"
    assert say.windows_open_names([], -1) == "No documents open"


def test_the_session_log_is_quill_log_when_it_exists(tmp_path) -> None:
    assert say.session_log_file(tmp_path) is None
    (tmp_path / "quill.log").write_text("x", encoding="utf-8")
    assert say.session_log_file(tmp_path) == tmp_path / "quill.log"
    assert "attach the file" in say.describe_copied_log(tmp_path / "quill.log")
