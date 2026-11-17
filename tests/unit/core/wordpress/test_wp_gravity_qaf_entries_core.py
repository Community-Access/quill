"""Old Gravity Forms entries mapped onto a QAF form and sent one by one (WP-R-029)."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress import gravity_qaf_entries as ge
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.gravity_qaf import to_qaf

FORM = {
    "id": "1",
    "title": "Signup",
    "fields": [
        {"id": 1, "type": "name", "label": "Name"},
        {"id": 2, "type": "checkbox", "label": "Shows"},
        {"id": 3, "type": "email", "label": "Email"},
        {"id": 4, "type": "fileupload", "label": "Photo"},
        {"id": 5, "type": "product", "label": "Ticket"},
        {"id": 6, "type": "section", "label": "More"},
        {"id": 7, "type": "text", "label": "Note"},
    ],
}

ENTRY = {
    "id": "41",
    "form_id": "1",
    "date_created": "2024-05-01 10:00:00",
    "is_starred": "1",
    "1.3": "Ann",
    "1.6": "Lee",
    "2.1": "am",
    "2.2": "",
    "2.3": "pm",
    "3": "ann@example.org",
    "4": "https://radio.example/wp-content/uploads/gravity_forms/a.jpg",
    "5.1": "Ticket",
    "payment_status": "Paid",
}


def _model() -> dict[str, Any]:
    # The QAF form Copy as a QUILL Accessible Form made, without the Note question.
    model = to_qaf({**FORM, "fields": FORM["fields"][:3]}).form
    return model


def test_answers_map_through_the_conversions_field_ids_and_losses_are_named() -> None:
    plan = ge.plan_copy(FORM, [ENTRY], 8, "Signup", _model())
    (copy,) = plan.copies
    assert copy.fields == {
        "field_1": "Ann Lee",
        "field_2": ["am", "pm"],
        "field_3": "ann@example.org",
    }
    assert copy.lost == ["Photo", "Ticket", "its payment status"]
    lost = " ".join(plan.lost)
    assert "uploaded files stay" in lost and "payment details stay" in lost
    assert "Note: the QUILL Accessible Forms form has no question for it" in lost
    lines = plan.lines()
    assert "POST qaf/v1/entries" in lines[1] and "must offer that route" in lines[1]
    assert lines[-1].startswith("Entry 41 from 2024-05-01 10:00:00: 3 answers; left out:")
    body = copy.body(8)
    assert body["form_id"] == 8 and body["created_at"] == "2024-05-01 10:00:00"
    assert body["source"] == "Imported from Gravity Forms entry 41" and body["is_starred"] == 1


class Api:
    def __init__(self, fail: WordPressApiError | None = None) -> None:
        self.fail = fail
        self.sent: list[tuple[str, Any]] = []
        self.pages: list[dict[str, Any]] = []

    def post(self, route: str, body: Any = None, **_k: Any) -> Any:
        self.sent.append((route, body))
        if self.fail is not None:
            raise self.fail
        return {"id": 100 + len(self.sent)}

    def get(self, route: str, **params: Any) -> Any:
        self.pages.append(params)
        return {"total_count": "1", "entries": [ENTRY]}


def test_each_entry_is_sent_and_has_its_own_outcome() -> None:
    api = Api()
    plan = ge.plan_copy(FORM, [ENTRY, {**ENTRY, "id": "42"}], 8, "Signup", _model())
    outcomes, made = ge.send_copies(api, "Radio", plan)
    assert made == [101, 102]
    assert [r for r, _b in api.sent] == ["qaf/v1/entries", "qaf/v1/entries"]
    assert outcomes[0].ok and outcomes[0].words.startswith("copied as entry 101; left out:")


def test_a_site_without_the_create_route_is_one_sentence() -> None:
    api = Api(WordPressApiError("No route.", status=404, wp_code="rest_no_route"))
    plan = ge.plan_copy(FORM, [ENTRY, {**ENTRY, "id": "42"}], 8, "Signup", _model())
    outcomes, made = ge.send_copies(api, "Radio", plan)
    assert made == [] and len(api.sent) == 1
    (only,) = outcomes
    assert not only.ok and "cannot take entries yet" in only.words
    assert "POST qaf/v1/entries" in only.words


def test_one_refused_entry_does_not_stop_the_rest() -> None:
    class Picky(Api):
        def post(self, route: str, body: Any = None, **_k: Any) -> Any:
            if body["source"].endswith("41"):
                self.sent.append((route, body))
                raise WordPressApiError("That entry is invalid.", status=400)
            return super().post(route, body)

    api = Picky()
    plan = ge.plan_copy(FORM, [ENTRY, {**ENTRY, "id": "42"}], 8, "Signup", _model())
    outcomes, made = ge.send_copies(api, "Radio", plan)
    assert [o.ok for o in outcomes] == [False, True] and made == [102]
    assert outcomes[0].words == "That entry is invalid."


def test_entries_are_read_through_gravity_forms_entries_route() -> None:
    api = Api()
    assert ge.read_gravity_entries(api, "1") == [ENTRY]
    assert api.pages[0]["form_ids[0]"] == "1" and '"status": "active"' in api.pages[0]["search"]
