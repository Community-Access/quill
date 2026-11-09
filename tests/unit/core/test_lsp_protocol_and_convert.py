"""The language-server wire format and conversions (quill.core.lsp.protocol,
quill.core.lsp.convert): pure, no process."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.lsp.convert import (
    apply_text_edits,
    completion_names,
    lsp_position,
    offset_from_lsp,
    problems_from_diagnostics,
    quick_fixes,
    signature_sentence,
)
from quill.core.lsp.protocol import (
    FrameError,
    FrameReader,
    encode_message,
    path_from_uri,
    uri_for_path,
)


def test_frames_round_trip_even_when_split_anywhere() -> None:
    data = encode_message({"jsonrpc": "2.0", "id": 1, "result": "é"}) + encode_message({
        "jsonrpc": "2.0",
        "method": "x",
    })
    for cut in range(1, len(data)):
        reader = FrameReader()
        got = reader.feed(data[:cut]) + reader.feed(data[cut:])
        assert [m.get("id", m.get("method")) for m in got] == [1, "x"]


@pytest.mark.parametrize(
    "header",
    [b"Nope: 3\r\n\r\n{}", b"Content-Length: x\r\n\r\n", b"Content-Length: 99999999999\r\n\r\n"],
)
def test_bad_frames_are_refused(header: bytes) -> None:
    with pytest.raises(FrameError):
        FrameReader().feed(header)


def test_uris_round_trip_spaces_and_drive_letters(tmp_path: Path) -> None:
    path = tmp_path / "a b" / "c#.py"
    uri = uri_for_path(path)
    assert uri.startswith("file:///") and "%20" in uri and "%23" in uri
    assert path_from_uri(uri) == path.resolve()
    assert path_from_uri("https://example.com/x") is None


def test_positions_count_utf16_units() -> None:
    text = "a😀b\nxyz"
    offset = text.index("b")
    assert lsp_position(text, offset) == {"line": 0, "character": 3}
    assert offset_from_lsp(text, 0, 3) == offset
    assert offset_from_lsp(text, 1, 2) == text.index("z")
    assert offset_from_lsp(text, 9, 0) == len(text)


def test_completions_keep_the_fragment_same_case_first_and_say_kinds() -> None:
    items = {
        "isIncomplete": False,
        "items": [
            {"label": "Counter", "kind": 7, "sortText": "1"},
            {"label": "count", "kind": 3, "sortText": "2", "detail": "(n: int) -> int"},
            {"label": "other", "kind": 6},
            {"label": "div", "kind": 10, "filterText": "<div"},
        ],
    }
    names = completion_names(items, "cou")
    assert [(n.label, n.kind) for n in names] == [("count", "function"), ("Counter", "class")]
    assert names[0].detail == "(n: int) -> int"
    assert [n.label for n in completion_names(items, "di")] == ["div"]


def test_diagnostics_become_one_based_problems() -> None:
    problems = problems_from_diagnostics(
        [
            {"range": {"start": {"line": 3, "character": 4}}, "severity": 2, "message": "a\n b"},
            {"range": {"start": {"line": 0, "character": 0}}, "message": ""},
        ],
        source="Pyright",
    )
    assert [(p.line, p.column, p.severity, p.message, p.source) for p in problems] == [
        (4, 5, "warning", "a b", "Pyright")
    ]


def test_signature_sentence_names_the_parameter() -> None:
    result = {
        "signatures": [
            {
                "label": "sleep(ms, seconds, label)",
                "parameters": [{"label": [6, 8]}, {"label": "seconds"}, {"label": "label"}],
            }
        ],
        "activeParameter": 1,
    }
    assert signature_sentence(result) == "Parameter 2 of 3, seconds. sleep(ms, seconds, label)"
    assert signature_sentence(None) == ""
    assert signature_sentence({"signatures": []}) == ""


def test_quick_fixes_keep_only_edits_to_this_file_preferred_first() -> None:
    text = "let a = 1\n"
    uri = "file:///x.ts"
    edit = {"range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 3}}}
    actions = [
        {"title": "Run a command", "command": {"command": "x"}},
        {"title": "Use const", "edit": {"changes": {uri: [{**edit, "newText": "const"}]}}},
        {
            "title": "Preferred",
            "isPreferred": True,
            "edit": {
                "documentChanges": [
                    {"textDocument": {"uri": uri}, "edits": [{**edit, "newText": "var"}]}
                ]
            },
        },
        {
            "title": "Touches another file",
            "edit": {"changes": {uri: [{**edit, "newText": "x"}], "file:///y.ts": []}},
        },
    ]
    fixes = quick_fixes(actions, uri, text)
    assert [fix.title for fix in fixes] == ["Preferred", "Use const"]
    assert apply_text_edits(text, fixes[1].edits) == "const a = 1\n"


def test_edits_apply_from_the_end_backwards() -> None:
    assert apply_text_edits("abcdef", ((0, 1, "X"), (4, 6, "YZ!"))) == "XbcdYZ!"
