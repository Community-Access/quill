"""BAF's choice libraries, as data QUILL can use with no site."""

from __future__ import annotations

import datetime as dt

import pytest

from quill.core.forms import libraries
from quill.core.forms.bfl_lexer import LIBRARY_KEYWORDS
from quill.core.forms.errors import ChoiceLibraryError


def test_all_124_libraries_are_there() -> None:
    ids = libraries.library_ids()
    assert len(ids) == 124
    assert {
        "countries",
        "us_states",
        "months",
        "time_slots_hourly",
        "currencies",
        "languages",
    } <= set(ids)


def test_countries_are_baf_values_and_labels() -> None:
    countries = libraries.choices("countries")
    by_value = {c["value"]: c["label"] for c in countries}
    assert by_value["US"] == "United States"
    assert by_value["AX"] == "Åland Islands"
    assert len(countries) > 240


def test_cascading_states_follow_the_country() -> None:
    assert libraries.choices("states") == []
    canada = [c["label"] for c in libraries.choices("states", "CA")]
    assert "Ontario" in canada and "Alabama" not in canada
    assert [c["label"] for c in libraries.choices("states", "us")][:2] == ["Alabama", "Alaska"]
    assert libraries.info("states").cascade_parent == "countries"
    europe = {c["value"] for c in libraries.choices("countries_by_continent", "EU")}
    assert {"FR", "DE"} <= europe and "US" not in europe


def test_year_lists_follow_the_calendar() -> None:
    today = dt.date(2026, 11, 4)
    years = libraries.choices("years", today=today)
    assert years[0]["value"] == "2026" and years[-1]["value"] == "1926"
    assert libraries.choices("years_future", today=today)[-1]["value"] == "2046"
    birth = libraries.choices("birth_years", today=today)
    assert birth[0]["value"] == "2013" and birth[-1]["value"] == "1906"
    assert libraries.info("years").count == 101


def test_search_and_missing() -> None:
    names = [i.id for i in libraries.search("us state")]
    assert "us_states" in names
    with pytest.raises(ChoiceLibraryError) as caught:
        libraries.choices("no_such_list")
    assert caught.value.code == "QUILL-FORMS-LIBRARY-MISSING"


def test_bfl_library_keywords_that_have_no_library() -> None:
    """BAF's lexer knows these words as libraries; the report names the ones BAF never registered."""  # noqa: E501
    missing = sorted(k for k in LIBRARY_KEYWORDS if not libraries.exists(k))
    assert missing == ["provinces"]
