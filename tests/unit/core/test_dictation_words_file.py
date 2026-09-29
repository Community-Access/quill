"""``dictation.md`` as three editable lists (``quill/core/windows_dictation/words_file.py``).

The My Words and Phrases window (dict.md 5, 2026-09-28) edits words, phrases
and corrections without anyone opening the file. The file's shape is still
the profile parser's, so the same file feeds recognition unchanged.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.dictation_profile import parse_profile
from quill.core.windows_dictation.profile import LITE_TEMPLATE
from quill.core.windows_dictation.words_file import (
    Entry,
    WordsFile,
    load_words,
    parse_words,
    render_words,
    save_words,
)


def test_the_shipped_template_reads_as_words_and_phrases() -> None:
    words = parse_words(LITE_TEMPLATE)
    assert words.words == ["QUILL", "NVDA", "JAWS"]
    assert words.phrases == [("my email address", "someone@example.com")]
    assert words.corrections == []


def test_corrections_have_their_own_section_and_still_feed_recognition() -> None:
    words = WordsFile(
        words=["Tucson"],
        phrases=[("my signature", "Jeff\nTucson")],
        corrections=[("quill light", "QUILL Lite")],
    )
    text = render_words(words)
    # The window's view round-trips exactly...
    again = parse_words(text)
    assert again.words == ["Tucson"]
    assert again.phrases == [("my signature", "Jeff\nTucson")]
    assert again.corrections == [("quill light", "QUILL Lite")]
    # ...and the recogniser's parser sees a correction as one more replacement,
    # so "quill light" is written as QUILL Lite without any new runtime code.
    profile = parse_profile(text)
    assert profile.vocabulary == ("Tucson",)
    assert ("quill light", "QUILL Lite") in profile.replacements
    assert ("my signature", "Jeff\nTucson") in profile.replacements
    assert profile.apply_replacements("I use quill light daily") == "I use QUILL Lite daily"


def test_a_commands_section_is_carried_across_untouched() -> None:
    text = LITE_TEMPLATE + "\n## Commands\n\nsave it => file.save\n"
    words = parse_words(text)
    assert words.commands_lines == ["save it => file.save"]
    assert "## Commands\n\nsave it => file.save" in render_words(words)


def test_add_refuses_blanks_and_duplicates_case_insensitively() -> None:
    words = WordsFile()
    assert words.add(Entry("word", "  Tucson ")) is True
    assert words.add(Entry("word", "tucson")) is False
    assert words.add(Entry("word", "   ")) is False
    assert words.add(Entry("phrase", "my email", "a@b.c")) is True
    assert words.add(Entry("phrase", "My Email", "x@y.z")) is False
    assert words.add(Entry("phrase", "no text", "")) is False
    assert words.add(Entry("correction", "quill light", "QUILL Lite")) is True
    # The same spoken form may be a phrase AND a correction: separate lists.
    assert words.add(Entry("correction", "my email", "whatever")) is True
    assert [e.kind for e in words.entries()] == ["word", "phrase", "correction", "correction"]


def test_remove_and_replace_keep_positions() -> None:
    words = WordsFile(words=["A", "B", "C"], phrases=[("one", "1"), ("two", "2")])
    assert words.remove(Entry("word", "B")) is True
    assert words.words == ["A", "C"]
    assert words.remove(Entry("word", "B")) is False
    assert words.replace(Entry("phrase", "one", "1"), Entry("phrase", "uno", "1!")) is True
    assert words.phrases == [("uno", "1!"), ("two", "2")]
    # A rename onto an existing spoken form is refused.
    assert words.replace(Entry("phrase", "uno", "1!"), Entry("phrase", "TWO", "x")) is False
    # Changing the kind moves it between lists.
    assert words.replace(Entry("phrase", "two", "2"), Entry("correction", "two", "2")) is True
    assert words.phrases == [("uno", "1!")]
    assert words.corrections == [("two", "2")]


def test_labels_read_as_sentences() -> None:
    assert Entry("word", "NVDA").label() == "Word: NVDA"
    assert Entry("phrase", "my sig", "Jeff\nTucson").label() == (
        "Phrase: say my sig, writes Jeff (new line) Tucson"
    )
    assert Entry("correction", "quill light", "QUILL Lite").label() == (
        "Correction: heard quill light, write QUILL Lite"
    )


def test_load_and_save(tmp_path: Path) -> None:
    path = tmp_path / "dictation.md"
    assert load_words(path).entries() == []  # missing: empty, no error
    words = WordsFile(words=["QUILL"])
    save_words(path, words)
    assert load_words(path).words == ["QUILL"]
    # The header says who keeps it now.
    assert "My Words and Phrases" in path.read_text(encoding="utf-8")
