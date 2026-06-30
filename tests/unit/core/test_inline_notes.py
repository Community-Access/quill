from __future__ import annotations

from pathlib import Path

from quill.core.inline_notes import (
    InlineNote,
    InlineNoteVault,
    line_bounds,
    make_inline_note,
    note_at,
    resolve_inline_note,
    resolved_notes,
)

DOC = "Alpha line one\nBeta line two\nGamma line three\n"


def test_anchor_to_selection_captures_quote_and_context() -> None:
    start = DOC.index("Beta")
    note = make_inline_note("about beta", DOC, start, start + 4)
    assert note.quote == "Beta"
    assert note.text == "about beta"
    assert DOC[note.start : note.end] == "Beta"


def test_anchor_to_line_when_no_selection() -> None:
    caret = DOC.index("Gamma") + 3  # somewhere inside the Gamma line
    note = make_inline_note("line note", DOC, caret, caret)
    assert note.quote == "Gamma line three"


def test_line_bounds_excludes_newline() -> None:
    assert DOC[slice(*line_bounds(DOC, DOC.index("Beta")))] == "Beta line two"


def test_note_follows_content_after_insert() -> None:
    start = DOC.index("Beta")
    note = make_inline_note("n", DOC, start, start + 4)
    edited = "NEW HEADER\n" + DOC
    located = resolve_inline_note(edited, note)
    assert located is not None
    assert edited[located[0] : located[1]] == "Beta"


def test_orphaned_note_when_quote_deleted() -> None:
    start = DOC.index("Beta")
    note = make_inline_note("n", DOC, start, start + 4)
    edited = DOC.replace("Beta line two", "REPLACED")
    assert resolve_inline_note(edited, note) is None


def test_duplicate_quote_uses_context_and_proximity() -> None:
    doc = "see foo here\nand foo there\n"
    # Anchor the SECOND "foo".
    second = doc.index("foo", doc.index("foo") + 1)
    note = make_inline_note("n", doc, second, second + 3)
    located = resolve_inline_note(doc, note)
    assert located == (second, second + 3)


def test_resolved_notes_are_sorted_and_skip_orphans() -> None:
    a = make_inline_note("a", DOC, DOC.index("Gamma"), DOC.index("Gamma") + 5)
    b = make_inline_note("b", DOC, DOC.index("Alpha"), DOC.index("Alpha") + 5)
    orphan = InlineNote("x", "gone", "NOT PRESENT", "", "", 0, 0)
    located = resolved_notes(DOC, [a, b, orphan])
    assert [n.text for n, _s, _e in located] == ["b", "a"]  # sorted by position; orphan dropped


def test_note_at_returns_containing_then_nearest() -> None:
    a = make_inline_note("a", DOC, DOC.index("Beta"), DOC.index("Beta") + 4)
    assert note_at(DOC, [a], DOC.index("Beta") + 1).text == "a"
    assert note_at(DOC, [a], 0).text == "a"  # nearest when none contains


def test_summary_is_single_line_and_truncated() -> None:
    note = make_inline_note("first line\nsecond line", DOC, 0, 5)
    assert note.summary() == "first line"
    long = make_inline_note("x" * 200, DOC, 0, 5)
    assert long.summary().endswith("…") and len(long.summary()) <= 60


def test_vault_persists_per_document(tmp_path: Path) -> None:
    store = tmp_path / "inline_notes.json"
    vault = InlineNoteVault(path=store)
    key = InlineNoteVault.key_for(tmp_path / "doc.md")
    note = make_inline_note("hello", DOC, 0, 5)
    vault.set_notes(key, [note])
    reloaded = InlineNoteVault.load(store)
    got = reloaded.notes_for(key)
    assert len(got) == 1 and got[0].text == "hello" and got[0].quote == note.quote


def test_vault_untitled_is_never_persisted(tmp_path: Path) -> None:
    vault = InlineNoteVault(path=tmp_path / "inline_notes.json")
    assert InlineNoteVault.key_for(None) is None
    vault.set_notes(None, [make_inline_note("x", DOC, 0, 5)])  # no-op, no crash
    assert vault.notes_for(None) == []
    assert not (tmp_path / "inline_notes.json").exists()


def test_vault_load_is_forgiving(tmp_path: Path) -> None:
    bad = tmp_path / "inline_notes.json"
    bad.write_text("{ not json", encoding="utf-8")
    assert InlineNoteVault.load(bad).documents == {}
