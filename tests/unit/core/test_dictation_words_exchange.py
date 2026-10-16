"""Import, export and merging for My Words and Phrases (dict.md D-12).

``quill/core/windows_dictation/words_exchange.py``: Markdown and CSV out, the
same two in, a merge that never replaces, and the counts said afterwards.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.windows_dictation.words_exchange import (
    BACKUP_NAME,
    WordsImportError,
    apply_merge,
    back_up,
    count_phrase,
    export_words,
    plan_merge,
    preview_sentence,
    read_import,
    render_csv,
    summary_sentence,
)
from quill.core.windows_dictation.words_file import (
    Entry,
    WordsFile,
    load_words,
    save_words,
)


def _sample() -> WordsFile:
    return WordsFile(
        words=["NVDA", "Okonkwo", "Zoë"],
        phrases=[("my signature", "Jeff Bishop\nTucson"), ("my email", "a,b@example.com")],
        corrections=[("quill light", "QUILL Lite")],
        commands_lines=["- read that back => read_last"],
    )


@pytest.mark.parametrize("suffix", [".md", ".csv"])
def test_export_then_import_round_trips_the_file_exactly(tmp_path: Path, suffix: str) -> None:
    """The D-12 acceptance test: the list a file came from, byte for byte."""
    words = _sample()
    if suffix == ".csv":
        words.commands_lines = []  # CSV carries the three lists, not Commands
    original = tmp_path / "dictation.md"
    save_words(original, words)
    exported = tmp_path / f"export{suffix}"
    assert export_words(load_words(original), exported) == 6

    fresh = tmp_path / "other" / "dictation.md"
    target = load_words(fresh)
    plan = plan_merge(target, read_import(exported))
    assert len(plan.new) == 6 and not plan.already and not plan.different
    apply_merge(target, plan)
    save_words(fresh, target)
    assert fresh.read_bytes() == original.read_bytes()


def test_csv_has_say_write_kind_columns_and_keeps_real_line_breaks() -> None:
    text = render_csv(_sample())
    assert text.splitlines()[0] == "say,write,kind"
    assert "NVDA,,word" in text
    assert '"Jeff Bishop\nTucson",phrase' in text
    assert '"a,b@example.com"' in text  # a comma inside a cell is quoted


def test_a_spreadsheet_csv_without_a_kind_column_is_words_and_phrases(tmp_path: Path) -> None:
    path = tmp_path / "list.csv"
    path.write_bytes("Say,Write\r\nCafé,\r\nmy address,1 Main St\r\n,orphan\r\n".encode("cp1252"))
    words = read_import(path)
    assert words.words == ["Café"]  # the ANSI code page a spreadsheet saves in
    assert words.phrases == [("my address", "1 Main St")]


def test_a_csv_with_no_header_is_read_by_position(tmp_path: Path) -> None:
    path = tmp_path / "list.csv"
    path.write_text("quill light,QUILL Lite,correction\nJAWS\n", encoding="utf-8")
    words = read_import(path)
    assert words.corrections == [("quill light", "QUILL Lite")]
    assert words.words == ["JAWS"]


def test_merging_keeps_yours_and_counts_the_rest() -> None:
    mine = WordsFile(words=["NVDA"], phrases=[("my email", "me@home.example")])
    theirs = WordsFile(
        words=["NVDA", "Narrator", "narrator", "Jaws"],
        phrases=[("My Email", "other@example.com"), ("my phone", "555")],
    )
    plan = plan_merge(mine, theirs)
    assert [e.spoken for e in plan.new] == ["Narrator", "Jaws", "my phone"]
    # "narrator" repeats the file's own "Narrator": counted once, as already there.
    assert [e.spoken for e in plan.already] == ["NVDA", "narrator"]
    assert [(e.spoken, y.written) for e, y in plan.different] == [("My Email", "me@home.example")]
    assert apply_merge(mine, plan) == 3
    assert mine.phrases[0] == ("my email", "me@home.example")  # yours kept
    assert mine.words == ["NVDA", "Narrator", "Jaws"]


def test_the_spoken_counts() -> None:
    plan = plan_merge(WordsFile(words=["a", "b", "c"]), WordsFile(words=list("abcdefghijklmno")))
    assert summary_sentence(plan) == "Imported 12 words, 3 already there."
    assert preview_sentence(plan) == "12 words will be added. 3 already in your list."
    mixed = plan_merge(
        WordsFile(words=["NVDA"]), WordsFile(words=["nvda", "JAWS"], phrases=[("x y", "z")])
    )
    assert summary_sentence(mixed) == (
        "Imported 2 entries, 1 differs from yours and yours were kept."
    )
    assert count_phrase([Entry("phrase", "a", "b")]) == "1 phrase"


@pytest.mark.parametrize(
    ("name", "body", "says"),
    [
        ("list.docx", "x", "is not a word list"),
        ("empty.md", "# Notes\n\nJust prose here.\n", "No words, phrases or corrections"),
        ("empty.csv", "say,write\n", "header row of say and write"),
    ],
)
def test_files_that_are_not_word_lists_are_refused_in_a_sentence(
    tmp_path: Path, name: str, body: str, says: str
) -> None:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    with pytest.raises(WordsImportError) as caught:
        read_import(path)
    assert says in caught.value.args[0]
    assert caught.value.code == "QUILL-DICTATION-WORDS-IMPORT"


def test_a_backup_is_taken_beside_the_list(tmp_path: Path) -> None:
    path = tmp_path / "dictation.md"
    assert back_up(path) is None  # nothing to keep yet
    save_words(path, _sample())
    backup = back_up(path)
    assert backup == tmp_path / BACKUP_NAME
    assert backup.read_bytes() == path.read_bytes()
