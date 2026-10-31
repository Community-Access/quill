"""What spell check reads, by file type (QUILLVille list, 2026-10-29).

The complaint: "if you spell check www.example.com, www is an error, example
is an error and so is com." The fix reaches further than web addresses -- email
addresses and paths in any text, and in code and markup only what a person
wrote as language -- and every case here goes through the same public functions
both editors call, so QUILL and QUILL Lite cannot answer differently.
"""

from __future__ import annotations

import pytest

from quill.core import spellcheck_lexers, spellcheck_spans
from quill.core.spellcheck import (
    list_misspellings,
    misspelling_at_position,
    misspelling_behind,
    next_misspelling,
    no_misspelling_message,
    previous_misspelling,
)
from quill.core.spellcheck_spans import (
    checkable_spans,
    masked_for_checking,
    spell_kind_for,
    word_is_checkable,
)


@pytest.fixture(autouse=True)
def _fresh_caches():
    spellcheck_spans.reset_caches()
    yield
    spellcheck_spans.reset_caches()


def _words(text: str, filename: str | None = None) -> list[str]:
    return [m.word for m in list_misspellings(text, set(), filename=filename)]


@pytest.mark.parametrize(
    "address",
    [
        "www.exampel.com",
        "https://exampel.org/some/pathh?q=wrod",
        "exampel.com",
        "exampel.co.uk/pagge",
        "mailto:jo@exmple.org",
        "jo.smiht@exmple.org",
        r"C:\Usres\jo\Documnts\notse.txt",
        r"\\servr\sharre\fiel",
        "~/projcts/notse",
        "/usr/lcoal/bin",
        "readem.txt",
    ],
)
def test_addresses_and_paths_are_not_words(address):
    assert _words(f"See {address} for teh details.") == ["teh"]


@pytest.mark.parametrize("name", [None, "letter.txt", "notes.docx", "untitled"])
def test_prose_rule_applies_to_every_prose_file(name):
    assert spell_kind_for(name) == "prose"
    assert _words("Visit www.exampel.com, teh end", name) == ["teh"]


def test_offsets_are_never_shifted():
    text = "Go to www.exampel.com and fix teh typo"
    masked = masked_for_checking(text)
    assert len(masked) == len(text)
    (item,) = list_misspellings(text, set())
    assert text[item.start : item.end] == "teh"


def test_markdown_skips_code_and_link_targets_but_checks_link_text():
    text = (
        "Some `inlin cdoe` and [linkk txet](https://exampel.com/pagge).\n"
        "```\nfenced blokc\n```\n"
        "After teh fence.\n"
    )
    assert _words(text, "notes.md") == ["linkk", "txet", "teh"]


def test_html_checks_text_and_readable_attributes_only():
    text = '<p class="wrnog" alt="pictre">Helo <b>wrold</b></p><!-- a commnet -->'
    assert _words(text, "page.html") == ["pictre", "Helo", "wrold", "commnet"]


def test_html_script_is_read_as_code():
    text = '<script>var undefnied = "a strnig";</script><p>Fien</p>'
    assert _words(text, "page.html") == ["strnig", "Fien"]


@pytest.mark.parametrize(
    ("filename", "source", "expected"),
    [
        ("a.py", 'x = 1  # a comnent\ns = "speling"\nundefinedd_name()\n', ["comnent", "speling"]),
        ("a.js", "// a comnent\nconst wrod = `templat ${nmae}`;\n", ["comnent", "templat"]),
        ("a.cs", '/* blokc */ var s = "strnig {0}";', ["blokc", "strnig"]),
        ("a.sql", "-- a comnent\nSELECT 'vlaue' FROM tabel;", ["comnent", "vlaue"]),
        ("a.css", "/* a comnent */ .clas { content: 'strnig'; }", ["comnent", "strnig"]),
        ("a.ps1", '# a comnent\nWrite-Host "strnig $varr"', ["comnent", "strnig"]),
        # A JSON key is a name, like an identifier; its value is text.
        ("a.json", '{"keyy": "vlaue"}', ["vlaue"]),
    ],
)
def test_code_reads_only_strings_and_comments(filename, source, expected):
    assert spell_kind_for(filename) == "code"
    assert _words(source, filename) == expected


def test_inside_a_string_identifiers_placeholders_and_escapes_are_skipped():
    source = 'msg = "Helo {name} %s snake_case camelCase v2beta\\nwrold"\n'
    assert _words(source, "a.py") == ["Helo", "wrold"]


def test_regex_fallback_agrees_when_pygments_is_unavailable(monkeypatch):
    monkeypatch.setattr(spellcheck_lexers, "_pygments_lexer", lambda *_a: None)
    monkeypatch.setattr(spellcheck_spans, "_pygments_lexer", lambda *_a: None)
    source = 'x = 1  # a comnent\ns = "speling"\nundefinedd_name()\n'
    assert _words(source, "a.py") == ["comnent", "speling"]
    html = '<p class="wrnog" alt="pictre">Helo</p>'
    assert _words(html, "a.html") == ["pictre", "Helo"]


def test_pygments_is_what_lexes_code_when_present():
    pytest.importorskip("pygments")
    assert spellcheck_lexers._pygments_lexer("a.py", "code") is not None


def test_spans_are_sorted_and_inside_the_text():
    source = "# one\nx = 'two'\n# three\n"
    spans = checkable_spans(source, "a.py")
    assert spans == sorted(spans)
    assert all(0 <= s < e <= len(source) for s, e in spans)


def test_word_level_questions_agree_with_the_document_scan():
    text = "Mail jo@exmple.org about teh plan"
    start = text.index("exmple")
    assert not word_is_checkable(text, start, start + 6)
    assert misspelling_at_position(text, start + 2, set()) is None
    after = text.index("exmple") + len("exmple.org ")
    assert misspelling_behind(text, after, set()) is None
    assert next_misspelling(text, 0, set()).word == "teh"
    assert previous_misspelling(text, len(text), set()).word == "teh"


def test_no_misspelling_message_counts_with_the_same_rule():
    text = "teh www.exampel.com"
    said = no_misspelling_message(text, len(text), set(), ahead=True)
    assert said == "No misspellings ahead; 1 misspelling behind"


def test_the_filename_is_part_of_the_cache_key():
    source = '# a comnent\nundefinedd = "x"\n'
    assert "undefinedd" in _words(source)
    assert _words(source, "a.py") == ["comnent"]


#: Every spell finder an editor calls. Each takes the document's file name, and
#: a call without it silently falls back to the prose rule -- right for a
#: letter, a wall of false alarms for a script.
_FINDERS = {
    "list_misspellings",
    "misspelling_at",
    "misspelling_behind",
    "next_misspelling",
    "previous_misspelling",
    "no_misspelling_message",
    "misspelling_at_position",
    "spelling_context",
    "finder",
}


def test_every_editor_call_passes_the_file_name():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "quill"
    missing: list[str] = []
    for folder in ("ui", "apps"):
        for path in sorted((root / folder).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if name not in _FINDERS:
                    continue
                if name == "finder" and "spell" not in path.name:
                    continue  # a local alias in, say, the folding commands
                if len(node.args) < 2:
                    continue  # an editor's own menu command, not the shared finder
                if not any(k.arg == "filename" for k in node.keywords):
                    missing.append(f"{path.relative_to(root)}:{node.lineno} {name}")
    assert not missing, "spell finder called without filename=: " + ", ".join(missing)


def test_the_f7_review_uses_the_same_rule():
    """F7 is the check Chris Nova ran: it stopped on www, example and com."""
    from quill.core.spelling.session import ReviewSession

    session = ReviewSession("Visit www.exampel.com and fix teh typo", set(), filename="a.txt")
    assert session.total() == 1
    assert session.current().word == "teh"
    code = ReviewSession('# a comnent\nundefinedd = "x"\n', set(), filename="a.py")
    assert code.total() == 1
    assert code.current().word == "comnent"
