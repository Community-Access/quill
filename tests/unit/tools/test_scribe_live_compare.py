"""The live run's comparison, facts, replay summary and the one-command check.

The comparison flags what could break collecting or using a file -- a
format gone, a zip become one HTML file (F1's kind of change), a file that
no longer opens, DAISY chapters or BRF pages gone, a different cell width --
and only notes sizes and counts. It never grades quality.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from quill.tools import scribe_check
from quill.tools.scribe_live.compare import BREAK, INFO, compare_runs, comparison_sentences
from quill.tools.scribe_live.facts import brf_facts, facts_for, html_facts, sniff
from quill.tools.scribe_live.replay import Case, Replay, read_junit

PAGE = b'<!DOCTYPE html><html lang="en"><title>T</title><h1>A</h1><h2>B</h2><p>x</p></html>'


def _write(folder: Path, relative: str, data: bytes) -> Path:
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _zip(entries: dict[str, bytes]) -> bytes:
    import io

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return out.getvalue()


def _daisy(chapters: int) -> bytes:
    points = "".join(
        f'<navPoint id="n{i}" playOrder="{i}"><navLabel><text>Part {i}</text></navLabel>'
        f'<content src="s{i}.smil#p{i}"/></navPoint>'
        for i in range(1, chapters + 1)
    )
    ncx = (
        '<?xml version="1.0"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">'
        f"<navMap>{points}</navMap></ncx>"
    ).encode()
    return _zip({"book/dtb.ncx": ncx, "book/dtb.opf": b"<package/>"})


def test_facts_name_the_shape_not_the_quality(tmp_path: Path) -> None:
    facts = html_facts(PAGE.decode() + '<img src="a.png" alt="A"><img src="data:x" alt="">')
    assert (facts["headings"], facts["lang"], facts["imgs"]) == (2, "en", 2)
    assert (facts["external_img_refs"], facts["data_uri_imgs"], facts["imgs_without_alt"]) == (
        1, 1, 1,
    )  # fmt: skip
    brf = brf_facts(b",a\tb\xc2\xb4\r\n  #a\r\n\x0cpage two\r\n\x0c")
    assert (brf["form_feeds"], brf["tabs"], brf["non_ascii_bytes"], brf["crlf"]) == (2, 1, 2, True)
    assert sniff(_write(tmp_path, "a.zip", _zip({"x": b"y"}))) == "zip"
    assert sniff(_write(tmp_path, "a.html", PAGE)) == "html"
    assert sniff(_write(tmp_path, "a.pdf", b"%PDF-1.7")) == "pdf"
    book = facts_for("daisy", _write(tmp_path, "b.zip", _daisy(3)))
    assert book["ncx"] is True and book["chapters"] == 3 and book["opens"] is True


def test_a_zip_that_became_one_html_file_could_break_things(tmp_path: Path) -> None:
    before, now = tmp_path / "before", tmp_path / "now"
    _write(before, "offline-html/x-offline.zip", _zip({"index.html": PAGE}))
    _write(now, "offline-html/x-offline.html", PAGE)
    result = compare_runs(now, before)
    (finding,) = [f for f in result.findings if f.severity == BREAK]
    assert finding.kind == "file type"
    assert finding.sentence == (
        "Different kind of file: offline-html/x-offline.html was a zip, now a web page, "
        "named x-offline.zip before."
    )


def test_structure_quill_relies_on_is_a_break_and_sizes_are_only_noted(tmp_path: Path) -> None:
    before, now = tmp_path / "before", tmp_path / "now"
    _write(before, "daisy/x-daisy3.zip", _daisy(3))
    _write(now, "daisy/x-daisy3.zip", _zip({"book/dtb.opf": b"<package/>"}))
    _write(before, "brf/x.brf", b",a ,b ,c ,d\r\n\x0c")
    _write(now, "brf/x.brf", b",a\r\n,b\r\n")
    _write(before, "html/x.html", PAGE)
    _write(now, "html/x.html", PAGE + b"<p>" + b"longer " * 40 + b"</p>")
    _write(before, "mobi/gone.mobi", b"x" * 80)
    result = compare_runs(now, before)
    kinds = {(f.severity, f.kind) for f in result.findings}
    assert (BREAK, "ncx") in kinds and (BREAK, "does not open") in kinds
    assert (BREAK, "form_feeds") in kinds and (BREAK, "cell width") in kinds
    assert (BREAK, "missing") in kinds
    assert (INFO, "size") in kinds and (BREAK, "size") not in kinds
    lines = comparison_sentences(result)
    assert lines[0].startswith("Comparison with before: ")
    assert lines[0].endswith("out of 3 files compared.")
    assert "Braille width changed: brf/x.brf was 11 cells wide, now 2." in lines
    assert all("None" not in line for line in lines)
    assert any(line.endswith("cannot open it now. No dtb.ncx in the book.") for line in lines)


def test_a_planned_file_that_never_arrived_is_a_break(tmp_path: Path) -> None:
    now = tmp_path / "now"
    _write(now, "html/q01.html", PAGE)
    record = {
        "uploads": [
            {
                "name": "q01", "stem": "q01", "expect": "converts", "state": "done",
                "conversions": [{"format": "html", "label": ""}, {"format": "brf", "label": ""}],
            }
        ]
    }  # fmt: skip
    (now / "run.json").write_text(json.dumps(record), encoding="utf-8")
    result = compare_runs(now, None)
    assert [f.sentence for f in result.breaks] == ["Planned and not collected: brf/q01.brf."]
    assert result.summary() == (
        "There was no earlier run or corpus to compare with: 1 change could break collecting "
        "or using the files, and 0 are for information."
    )


def test_the_replay_is_summed_up_per_app_and_format(tmp_path: Path) -> None:
    junit = tmp_path / "r.xml"
    junit.write_text(
        '<testsuites><testsuite name="pytest">'
        '<testcase classname="t" name="test_it_opens_and_reads[QUILL-x.html]"><properties>'
        '<property name="scribe_app" value="QUILL"/><property name="scribe_format" value="html"/>'
        "</properties></testcase>"
        '<testcase classname="t" name="test_the_media_player_listens"><failure message="boom"/>'
        "</testcase>"
        '<testcase classname="t" name="test_lite_brf"><skipped message="no corpus"/></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    replay = Replay(True, read_junit(junit))
    assert [(c.app, c.format, c.outcome) for c in replay.cases] == [
        ("QUILL", "html", "passed"),
        ("Media Player", "general", "failed"),
        ("QUILL Lite", "brf", "skipped"),
    ]
    lines = replay.sentences()
    assert lines[0] == "The replay suite passed 1 of 2 tests, and skipped 1."
    assert lines[1] == "By app: Media Player, 0 of 1 passed; QUILL, 1 of 1 passed."
    assert lines[2] == (
        "By format: Accessible HTML, 1 of 1 passed; not tied to one format, 0 of 1 passed."
    )
    assert lines[3] == "Failed: test_the_media_player_listens, in t.py. boom"


def test_the_one_command_says_the_result_first() -> None:
    said: list[str] = []
    cases = [Case("a", "passed", "QUILL", "docx"), Case("b", "failed", "Studio", "mp3", "why")]
    code = scribe_check.report(Replay(True, cases), said.append, what="offline")
    assert code == 1
    assert said[0] == "Scribe check failed, offline: 1 of 2 tests failed, 1 passed."
    assert said[1] == "By app: QUILL, 1 of 1 passed; Studio, 0 of 1 passed."
    said.clear()
    assert scribe_check.report(Replay(False, note="no pytest"), said.append, what="x") == 1
    assert said == ["Scribe check could not run: no pytest"]


def test_the_one_command_runs_the_offline_suite_without_the_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[object, Path]] = []

    def fake_suite(corpus: object, out: Path, say: object = None) -> Replay:
        calls.append((corpus, out))
        return Replay(True, [Case("a", "passed", "QUILL", "html")])

    monkeypatch.setattr(scribe_check, "run_suite", fake_suite)
    said: list[str] = []
    code = scribe_check.main(["--pneuma", str(tmp_path / "absent")], say=said.append)
    assert code == 0 and calls[0][0] is None
    assert said[0].startswith("Pneuma's corpus was not found, so only our own fixtures run.")
    assert said[2] == (
        "Scribe check passed, offline with our own fixtures only: 1 of 1 tests passed."
    )
