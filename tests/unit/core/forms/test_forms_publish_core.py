"""The wx-free half of publishing, exports, responses and the AI (wordpress.md 17a.7-17a.9)."""

from __future__ import annotations

from pathlib import Path

from quill.core.forms import ai_prompts as ap
from quill.core.forms import baf_site as bs
from quill.core.forms import print_layout as pl
from quill.core.forms import published as pub
from quill.core.forms import responses as rs


def _model(*items: dict) -> dict:
    return {"version": 1, "title": "T", "pages": [{"id": "page_1", "items": list(items)}]}


def test_paper_writes_a_choice_library_out_as_choices():
    model = _model({"id": "c", "type": "select", "label": "Country", "choice_library": "countries"})

    block = pl.blocks(model)[0]

    assert len(block.choices) > 100
    assert "Canada" in block.choices


def test_paper_skips_what_cannot_be_filled_in_and_numbers_the_rest():
    model = _model(
        {"id": "h", "type": "hidden", "label": "Ref"},
        {"id": "s", "type": "section", "label": "About you", "items": [
            {"id": "n", "type": "text", "label": "Name", "required": True},
        ]},
        {"id": "a", "type": "consent", "label": "I agree to the terms"},
    )  # fmt: skip

    blocks = pl.blocks(model)

    assert [b.kind for b in blocks] == ["section", "question", "question"]
    assert pl.question_heading(blocks[1]) == "1. Name (required)"
    assert pl.how_to_answer(blocks[2]) == "Check the box to agree."


def test_braille_text_wraps_at_forty_cells():
    long = "Please tell us, in as much detail as you like, how you heard about the fair"
    text = pl.braille_text(_model({"id": "q", "type": "textarea", "label": long}))

    assert max(len(line) for line in text.splitlines()) <= 40
    assert "Answer:" in text


def test_a_page_shows_the_form_by_block_or_shortcode():
    assert bs.shows_form('<!-- wp:baf/form {"formId":12,"showTitle":false} /-->', 12)
    assert bs.shows_form('[baf_form id="12" title="false"]', 12)
    assert not bs.shows_form('[baf_form id="120"]', 12)
    assert bs.placement(3, "markdown")[1] == "a shortcode"


def test_publish_body_keeps_the_sites_own_config():
    existing = bs.form_from_payload({"id": 4, "config": {"fields": [1], "form_model": {"old": 1}}})
    model = _model()

    body = bs.publish_body(model, "bfl 1\n", status="active", existing=existing)

    assert body["config"] == {"fields": [1], "form_model": model, "model_version": 1}
    assert body["model"] is model


def test_question_labels_fall_back_to_the_builders_fields():
    form = bs.form_from_payload({"id": 4, "config": {"fields": [{"id": "x", "label": "Ex"}]}})

    assert form.question_labels() == {"x": "Ex"}


def test_answers_read_as_words():
    assert rs.answer_text(["a", "b"]) == "a, b"
    assert rs.answer_text(True) == "Yes"
    assert rs.answer_text({"street": "1 Main St", "city": "Leeds"}) == "1 Main St, Leeds"


def test_place_reads_an_address_answer():
    response = bs.Response(1, 1, answers={"addr": {"city": "Leeds", "country": "UK"}})

    assert rs.place(response) == "Leeds, UK"


def test_csv_has_a_column_per_question_and_any_extra_answers():
    response = bs.Response(5, 1, "2026-11-03 14:10:00", {"a": "x", "gone": "y"})

    text = rs.csv_text([response], {"a": "Question A"})

    assert text.splitlines() == ["Response,Sent,Question A,gone", "5,2026-11-03 14:10,x,y"]


def test_published_store_keeps_links_counts_and_ten_versions(tmp_path: Path):
    store = pub.PublishedStore(tmp_path)
    store.set_link(tmp_path / "a.bfl", pub.Link("s", 3, "A"))
    store.mark_seen("s", 3, 7)
    for n in range(12):
        folder = tmp_path / pub.VERSIONS_FOLDER / "s" / "3"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"2026010{n:02d}.bfl").write_text("x", encoding="utf-8")
    store.keep_version("s", 3, "bfl 1\n")

    assert store.link_for(tmp_path / "a.bfl").form_id == 3
    assert pub.new_responses(store, "s", {3: ("A", 9)}) == [("A", 2)]
    assert len(store.versions("s", 3)) == pub.KEEP_VERSIONS


def test_waiting_sentence_names_every_form():
    found = [("Fair", 1), ("Survey", 3)]

    assert pub.waiting_sentence("Radio", found) == (
        "Radio: 1 new response to Fair and 3 new responses to Survey."
    )


def test_extract_bfl_drops_fences_and_chatter():
    assert ap.extract_bfl('Sure!\n```bfl\nbfl 1\nform "X"\n```\nDone.') == 'bfl 1\nform "X"\n'


def test_summary_prompt_says_how_many_fit():
    rows = [[("Q", "a" * 1000)] for _ in range(200)]

    prompt, sent = ap.summary_prompt("F", rows)

    assert 0 < sent < 200
    assert len(prompt) <= ap.MAX_SEND
