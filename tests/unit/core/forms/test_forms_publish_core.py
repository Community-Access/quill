"""The wx-free half of publishing, exports, responses and the AI (wordpress.md 17a.7-17a.9)."""

from __future__ import annotations

from pathlib import Path

from quill.core.forms import ai_prompts as ap
from quill.core.forms import print_layout as pl
from quill.core.forms import published as pub
from quill.core.forms import qaf_site as bs
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
    assert bs.shows_form('<!-- wp:qaf/form {"formId":12,"showTitle":false} /-->', 12)
    assert bs.shows_form('[qaf_form id="12" title="false"]', 12)
    assert not bs.shows_form('[qaf_form id="120"]', 12)
    assert bs.placement(3, "markdown") == ('\n[qaf_form id="3"]\n', "a shortcode")
    assert bs.placement(3, "html")[0] == '\n<!-- wp:qaf/form {"formId":3} /-->\n'


def test_a_page_written_while_the_site_ran_baf_still_shows_the_form():
    """QAF keeps BAF's shortcode as an alias (17a.17), so the older names still count."""
    assert bs.shows_form('<!-- wp:baf/form {"formId":12,"showTitle":false} /-->', 12)
    assert bs.shows_form('[baf_form id="12" title="false"]', 12)
    assert not bs.shows_form('[baf_form id="120"]', 12)


class _Api:
    """A client that answers the REST index and records every other route asked."""

    def __init__(self, *namespaces: str) -> None:
        self.index = {"namespaces": ["wp/v2", *namespaces], "routes": {}}
        self.asked: list[str] = []

    def get(self, route: str, **_params: object) -> object:
        if route == "":
            self.asked.append("index")
            return self.index
        self.asked.append(route)
        return {"id": 7, "title": "Fair"}

    def post(self, route: str, _body: object) -> object:
        self.asked.append("POST " + route)
        return {"id": 7, "title": "Fair"}

    def delete(self, route: str) -> object:
        self.asked.append("DELETE " + route)
        return {"deleted": True}

    def iter_collection(self, route: str, _params: object = None, **_kw: object):
        self.asked.append(route)
        return iter([])


def test_qaf_v1_is_preferred_when_the_site_offers_both():
    """QAF answers writes on qaf/v1 only; baf/v1 is a read-only alias for one release."""
    api = _Api("baf/v1", "qaf/v1")

    assert bs.site_namespace(api) == "qaf/v1"
    assert bs.supports_qaf(api)
    bs.list_forms(api)
    bs.get_form(api, 7)
    bs.create_form(api, {})
    bs.update_form(api, 7, {})
    bs.delete_responses(api, [3])

    assert api.asked == [
        "index",
        "qaf/v1/forms",
        "qaf/v1/forms/7",
        "POST qaf/v1/forms",
        "POST qaf/v1/forms/7",
        "DELETE qaf/v1/entries/3",
    ]
    assert bs.plugin_prefix(api) == "qaf"
    assert "page=qaf-form-builder" in bs.builder_url("https://x.example", 7)


def test_a_site_still_running_baf_is_answered_on_baf_v1():
    api = _Api("baf/v1")

    assert bs.site_namespace(api) == "baf/v1"
    bs.list_forms(api)
    bs.create_form(api, {})

    assert api.asked == ["index", "baf/v1/forms", "POST baf/v1/forms"]
    assert bs.plugin_prefix(api) == "baf"
    assert bs.placement(3, "markdown", "baf")[0] == '\n[baf_form id="3"]\n'
    assert "page=baf-form-builder" in bs.builder_url("https://x.example", 7, "baf")


def test_a_site_with_neither_is_asked_nothing_else():
    api = _Api()

    assert not bs.supports_qaf(api)
    assert bs.site_namespace(api) == ""
    assert api.asked == ["index"]


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
    store.set_link(tmp_path / "a.qaf", pub.Link("s", 3, "A"))
    store.mark_seen("s", 3, 7)
    for n in range(12):
        folder = tmp_path / pub.VERSIONS_FOLDER / "s" / "3"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"2026010{n:02d}.bfl").write_text("x", encoding="utf-8")
    store.keep_version("s", 3, "bfl 1\n")

    assert store.link_for(tmp_path / "a.qaf").form_id == 3
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
