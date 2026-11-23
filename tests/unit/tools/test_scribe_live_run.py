"""The Scribe live regression run, against the fake Scribe server only.

No test here reaches the network or a real sign-in: the client is built on
:class:`FakeScribe`'s transport and channel, the session is a stand-in that
is "signed in", and the family-queue check is stubbed. The plan, the
confirmation, the cap, the run folder's layout, ``validation.json``,
``README.md``, ``run.json`` and the clean-up are what is checked.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from quill.core.scribe.model import FORMAT_IDS
from quill.tools import scribe_live_run as tool
from quill.tools.scribe_live import plan as P
from quill.tools.scribe_live.execute import Executor
from quill.tools.scribe_live.layout import new_record, validation_key
from quill.tools.scribe_live.sources import (
    DEFAULT_OURS,
    OUR_SOURCES,
    PNEUMA_SOURCES,
    REPO_ROOT,
    STAND_INS,
    find_sources,
)
from tests.unit.core.scribe.fake_scribe import (
    BASE,
    FakeClock,
    FakeResponse,
    FakeScribe,
    StaticTokens,
    _json,
)

_BOX = re.compile("[─-╿▀-▟]")


class _Session:
    base_url = BASE

    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in

    def is_signed_in(self) -> bool:
        return self.signed_in


def _scribe(server: FakeScribe, *, signed_in: bool = True) -> tool._Scribe:
    from quill.core.scribe.channel import default_channel_opener
    from quill.core.scribe.client import ScribeClient

    return tool._Scribe(
        session=_Session(signed_in),
        client_factory=lambda: ScribeClient(
            StaticTokens(server), base_url=BASE, transport=server.transport, sleep=lambda _s: None
        ),
        opener=default_channel_opener(server.connector),
    )


@pytest.fixture(autouse=True)
def _no_family_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool, "family_queue_busy", lambda: "")


@pytest.fixture
def pneuma(tmp_path: Path) -> Path:
    """A stand-in for Pneuma's corpus folder: their four file names, our bytes."""
    folder = tmp_path / "pneuma"
    (folder / "sources").mkdir(parents=True)
    for source in PNEUMA_SOURCES:
        (folder / "sources" / source.file).write_bytes(b"%PDF-1.4 stand-in")
    return folder


def _lines(argv: list[str], **kwargs: Any) -> tuple[int, list[str]]:
    said: list[str] = []
    code = tool.main(argv, say=said.append, **kwargs)
    return code, said


# ------------------------------------------------------------------ the plan


def test_our_sources_cover_every_input_type_scribe_takes() -> None:
    from quill.core.scribe.inputs import ACCEPTED_TYPES

    kinds = {s.kind for s in OUR_SOURCES}
    assert {name for name, _exts in ACCEPTED_TYPES} <= kinds
    found = find_sources(DEFAULT_OURS, Path("no-such-folder"))
    assert len(found.ours) == len(OUR_SOURCES), found.notes  # all committed


def test_the_quick_plan_is_about_fifty_and_keeps_pneumas_names(pneuma: Path) -> None:
    found = find_sources(DEFAULT_OURS, pneuma)
    plan = P.build_plan(found, P.QUICK)
    assert 45 <= plan.conversion_count <= 60
    first = plan.uploads[:4]
    assert [u.source.stem for u in first] == [s.stem for s in PNEUMA_SOURCES]
    assert all(sorted(u.formats) == sorted(FORMAT_IDS) for u in first)
    assert [u.run_id for u in first] == ["s1", "s2", "s3", "s4"]
    large, maths = plan.uploads[4], plan.uploads[5]
    assert (large.run_id, large.formats, {c.label for c in large.conversions}) == (
        "v1", ["pdf", "docx", "brf"], {"large-print"},
    )  # fmt: skip
    assert large.settings["braille_cells_per_line"] == 32 and large.settings["large_print"]
    assert maths.run_id == "v2" and maths.settings["math"] is True
    assert all(u.settings["notify_when_complete"] is False for u in plan.uploads)  # F8


def test_without_pneumas_corpus_our_stand_ins_take_their_place(tmp_path: Path) -> None:
    found = find_sources(DEFAULT_OURS, tmp_path / "absent")
    assert [s.stem for s in found.core] == list(STAND_INS)
    assert any("were not found" in note for note in found.notes)


def test_no_setting_is_varied_against_a_format_it_cannot_change(pneuma: Path) -> None:
    plan = P.build_plan(find_sources(DEFAULT_OURS, pneuma), P.FULL)
    seen: set[tuple[str, str, tuple]] = set()
    for upload in plan.uploads:
        for conversion in upload.conversions:
            key = (upload.source.stem, conversion.format,
                   P.relevant_key(conversion.format, upload.settings))  # fmt: skip
            assert key not in seen, f"made twice: {key}"
            seen.add(key)
            if upload.run_id != "v1":  # Pneuma's own label, kept for the replay tests
                assert conversion.label == P.label_for(conversion.format, upload.settings)
            if conversion.format not in ("brf",):
                assert "brf-" not in conversion.label
            if conversion.format not in ("docx", "pdf"):
                assert "large-print" not in conversion.label or upload.run_id == "v1"
    labels = {c.label for u in plan.uploads for c in u.conversions if c.format == "brf"}
    assert "brf-en-ueb-g2-32x20" in labels and "brf-en-us-g2-40-no-pages" in labels
    assert plan.upload_count > 400 and plan.conversion_count > 1500


def test_the_cap_keeps_whole_uploads_in_order(pneuma: Path) -> None:
    found = find_sources(DEFAULT_OURS, pneuma)
    plan = P.build_plan(found, P.QUICK, cap=20)
    assert plan.conversion_count == 18  # two whole nine-format uploads
    assert plan.left_out and plan.left_out[0].run_id == "s3"
    assert any("The cap of 20 conversions leaves out" in s for s in P.plan_sentences(plan, found))


# ------------------------------------------------------- before any live call


def test_a_dry_run_prints_the_plan_and_sends_nothing(pneuma: Path, tmp_path: Path) -> None:
    server = FakeScribe()
    code, said = _lines(
        ["--profile", "full", "--dry-run", "--pneuma", str(pneuma), "--out", str(tmp_path / "r")],
        scribe=_scribe(server),
    )
    assert code == tool.EXIT_OK and server.requests == [] and server.sockets == []
    assert said[0] == "Dry run: this is the plan only, and nothing will be sent to Scribe."
    assert said[1].startswith("The full profile plans ")
    assert said[2].startswith("It costs ") and "for each format made" in said[2]
    assert said[-1] == "End of the dry run. Nothing was sent."
    assert not any(_BOX.search(line) for line in said)
    assert not (tmp_path / "r").exists()


@pytest.mark.parametrize(
    ("interactive", "answer", "words"),
    [
        (False, "", "Nothing was sent. A live run needs --yes"),
        (True, "", "Stopped. Nothing was sent to Scribe."),
        (True, "y", "You typed y, not yes, so nothing was sent."),
    ],
)
def test_nothing_is_sent_without_a_yes(
    pneuma: Path, tmp_path: Path, interactive: bool, answer: str, words: str
) -> None:
    server = FakeScribe()
    code, said = _lines(
        ["--pneuma", str(pneuma), "--out", str(tmp_path / "r")],
        scribe=_scribe(server), ask=lambda _q: answer, interactive=interactive,
    )  # fmt: skip
    assert code == tool.EXIT_STOPPED and server.requests == []
    assert said[-1].startswith(words)


def test_not_signed_in_stops_before_anything_is_sent(pneuma: Path, tmp_path: Path) -> None:
    server = FakeScribe()
    code, said = _lines(
        ["--yes", "--pneuma", str(pneuma), "--out", str(tmp_path / "r")],
        scribe=_scribe(server, signed_in=False),
    )
    assert code == tool.EXIT_STOPPED and server.requests == []
    assert "Sign in from QUILL (Tools, Scribe for Documents, Sign In)" in said[-1]


def test_runs_are_never_written_inside_the_repository(pneuma: Path) -> None:
    code, said = _lines(["--yes", "--pneuma", str(pneuma), "--out", str(REPO_ROOT / "runs")])
    assert code == tool.EXIT_STOPPED and "is inside the repository" in said[-1]


# ------------------------------------------------------------ a whole run


class _Server(FakeScribe):
    """The fake, offering the braille tables the plan names."""

    def _route(self, method: str, path: str, body: bytes) -> FakeResponse:
        if path == "/api/settings/braille_tables":
            tables = [["EBAE grade 2", "en-us-g2.ctb"], ["UEB grade 2", "en-ueb-g2.ctb"]]
            return _json(200, {"braille_tables": tables})
        return super()._route(method, path, body)


def _small_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "html": ("x.html", b'<!DOCTYPE html><html lang="en"><h1>A</h1><p>b</p></html>'),
        "offline_html": ("x-offline.html", b'<!DOCTYPE html><html lang="en"><h1>A</h1></html>'),
        "brf": ("x.brf", b",a ,title\r\n  #a\r\n\x0c"),
    }
    out = {}
    for format_id, (name, data) in files.items():
        path = tmp_path / "served" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        out[format_id] = path
    return out


def test_a_run_collects_everything_in_the_corpus_layout_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = _Server()
    server.serve_files(_small_files(tmp_path))
    clock = FakeClock()
    server.clock = clock
    runs = tmp_path / "runs"
    code, said = _lines(
        ["--yes", "--cap", "9", "--no-replay", "--pneuma", str(tmp_path / "absent"),
         "--out", str(runs)],
        scribe=_scribe(server),
        executor_options={"sleep": clock.sleep, "clock": clock, "queue_now": clock},
    )  # fmt: skip
    run_dir = next(runs.iterdir())
    record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    (entry,) = record["uploads"]
    assert entry["stem"] == "q02-structured" and entry["state"] == "done"
    assert entry["outcome"] == "as planned" and entry["deleted"] is True
    assert sorted(entry["files"]) == sorted(FORMAT_IDS)
    for relative in entry["files"].values():
        assert (run_dir / relative).is_file()
    assert (run_dir / "offline-html" / "q02-structured-offline.html").is_file()  # F1
    assert (run_dir / "daisy" / "q02-structured-daisy3.zip").is_file()
    assert not (run_dir / ".staging").exists()
    assert server.documents == {}  # trashed and deleted for good
    sent = next(r for r in server.requests if r[0] == "POST" and r[1].endswith("/api/documents"))
    assert b'name="document[settings][notify_when_complete]"\r\n\r\nfalse' in sent[3]
    validation = json.loads((run_dir / "validation.json").read_text(encoding="utf-8"))
    assert validation["s1/brf/q02-structured.brf"]["form_feeds"] == 1
    assert "s1/offline_html/q02-structured.html" in validation
    assert "s1/daisy/q02-structured.zip" in validation
    readme = (run_dir / "README.md").read_text(encoding="utf-8")
    block = readme.split("The defaults on the day were:", 1)[1].split("Variants", 1)[0]
    assert len(re.findall(r"\b([a-z_]+):", block)) == 11  # as the replay test reads it
    assert (run_dir / "sources" / "q02-structured.pdf").is_file()
    assert said[-1].startswith("Everything is in ")
    first = next(line for line in said if line.startswith("The quick live run"))
    assert first == (
        "The quick live run passed: it collected all 9 planned files, the replay suite did "
        "not run, and nothing changed that could break QUILL."
    )
    assert "1 test document was deleted from the account." in said[said.index(first) + 1]
    assert not any(_BOX.search(line) for line in said)
    assert code == tool.EXIT_OK


def test_refusals_end_as_planned(tmp_path: Path) -> None:
    from quill.core.scribe.channel import default_channel_opener
    from quill.core.scribe.client import ScribeClient

    found = find_sources(DEFAULT_OURS, tmp_path / "absent")
    by_stem = {s.stem: s for s in found.ours}
    builder = P._Builder()
    for stem in ("q29-web-page", "q30-not-a-pdf"):
        builder.add(by_stem[stem], {}, ("html",))
    plan = P.Plan(P.QUICK, builder.uploads)
    server = FakeScribe()
    server.error_for_format["html"] = ("not_a_document", "That is not a document.")
    clock = FakeClock()
    server.clock = clock
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    record = new_record(plan, found, run_dir)
    said: list[str] = []
    executor = Executor(
        run_dir, record,
        client_factory=lambda: ScribeClient(StaticTokens(server), base_url=BASE,
                                            transport=server.transport, sleep=lambda _s: None),
        channel_opener=default_channel_opener(server.connector),
        say=said.append, sleep=clock.sleep, clock=clock, queue_now=clock,
    )  # fmt: skip
    executor.queue_plan(plan)
    usage = executor.run(plan)
    web, fake = record["uploads"]
    assert web["outcome"] == "as planned" and web["document_id"] == ""
    assert web["error_code"] == "QUILL-SCRIBE-NOTDOC"
    assert fake["outcome"] == "as planned" and fake["document_id"]
    assert usage.uploads == 1 and usage.failed == 0
    assert said[1].startswith("Upload 1 of 2 was refused, as planned. ")
    assert "(" not in said[1]
    assert len([r for r in server.requests if r[0] == "POST"]) == 1  # the web page never went


def test_the_plan_is_said_in_words_not_file_name_labels(pneuma: Path) -> None:
    plan = P.build_plan(find_sources(DEFAULT_OURS, pneuma), P.FULL)
    lines = P.plan_details(plan)
    assert (
        lines[0]
        == f"Upload 1 of {len(lines)}: 01-born-digital-nist-csf2-excerpt.pdf, all 9 formats."
    )
    braille = next(line for line in lines if "UEB grade 2, 32 cells by 20 lines" in line)
    assert "brf-" not in braille and "(" not in braille
    assert any("female voice, double speed" in line for line in lines)
    assert P._duration(335) == "5 hours 35 minutes" and P._duration(61) == "61 minutes"


def test_the_validation_keys_are_pneumas() -> None:
    assert validation_key("s3", "offline-html/x-offline.html") == "s3/offline_html/x.html"
    assert validation_key("s3", "offline-html/x-offline.zip") == "s3/offline_html/x.zip"
    assert validation_key("v1", "daisy/x-large-print-daisy3.zip") == "v1/daisy/x-large-print.zip"
    assert validation_key("u0007", "brf/x-brf-en-ueb-g2-32x20.brf") == (
        "u0007/brf/x-brf-en-ueb-g2-32x20.brf"
    )


def test_a_braille_table_scribe_does_not_offer_is_dropped_before_sending(tmp_path: Path) -> None:
    from quill.core.scribe.client import ScribeClient

    found = find_sources(DEFAULT_OURS, tmp_path / "absent")
    plan = P.build_plan(found, P.QUICK)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    server = FakeScribe()  # offers only "en-ueb-g2"
    executor = Executor(
        run_dir, new_record(plan, found, run_dir),
        client_factory=lambda: ScribeClient(StaticTokens(server), base_url=BASE,
                                            transport=server.transport, sleep=lambda _s: None),
    )  # fmt: skip
    before = plan.conversion_count
    notes = executor.preflight(plan)
    tables = {u.settings["braille_translation_table"] for u in plan.uploads if "brf" in u.formats}
    assert tables == {"en-ueb-g2.ctb"}  # the one the fake offers (named without .ctb)
    assert plan.conversion_count < before
    assert notes[0].endswith("because Scribe does not offer their braille table.")
    assert notes[-1] == "Scribe says the account has 100 pages left."
    assert not [r for r in server.requests if r[0] != "GET"]  # reads only
