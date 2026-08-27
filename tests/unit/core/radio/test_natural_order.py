"""Sorting names the way a person reads them (reported 2026-08-26).

The report was "ACB Media 1, ACB Media 10, then 2 through 9", and the fix that
was explicitly refused was renaming the stations to ``ACB Media 01``: the
display name belongs to the broadcaster, the ordering belongs to us.
"""

from __future__ import annotations

from quill.core.radio import browse_helpers, live365
from quill.core.radio.natural_order import natural_key, sorted_by_name


def test_two_comes_before_ten() -> None:
    names = ["ACB Media 1", "ACB Media 10", "ACB Media 2", "ACB Media 9", "ACB Media 3"]
    assert sorted(names, key=natural_key) == [
        "ACB Media 1",
        "ACB Media 2",
        "ACB Media 3",
        "ACB Media 9",
        "ACB Media 10",
    ]


def test_no_name_is_rewritten_to_make_it_sort() -> None:
    """The whole point: the key changes, the name never does."""
    names = ["ACB Media 10", "ACB Media 2"]
    assert sorted(names, key=natural_key) == ["ACB Media 2", "ACB Media 10"]
    assert "01" not in " ".join(names)


def test_case_does_not_split_the_alphabet() -> None:
    assert sorted(["kexp", "KBOO", "Kdvs"], key=natural_key) == ["KBOO", "Kdvs", "kexp"]


def test_text_and_numbers_never_compare_against_each_other() -> None:
    """The naive version raises TypeError on exactly this list."""
    names = ["Radio 4", "4 Radio", "Radio", "42", "", "Radio 4 Extra"]
    assert len(sorted(names, key=natural_key)) == len(names)


def test_a_number_anywhere_in_the_name_is_read_as_a_number() -> None:
    assert sorted(["Channel 9 News", "Channel 10 News"], key=natural_key) == [
        "Channel 9 News",
        "Channel 10 News",
    ]


def test_sorted_by_name_reads_as_what_it_means() -> None:
    class Row:
        def __init__(self, name: str) -> None:
            self.name = name

    rows = [Row("Studio 10"), Row("Studio 2")]
    assert [r.name for r in sorted_by_name(rows, lambda r: r.name)] == ["Studio 2", "Studio 10"]


def test_the_live365_directory_is_ordered_this_way() -> None:
    """Where the report came from: a letter folder full of numbered stations."""
    sitemap = "".join(
        f"<url><loc>https://live365.com/station/ACB-Media-{n}-a1000{n}</loc></url>"
        for n in (10, 2, 1, 9)
    )
    names = [station.name for station in live365.parse_sitemap(f"<urlset>{sitemap}</urlset>")]
    assert names == ["ACB Media 1", "ACB Media 2", "ACB Media 9", "ACB Media 10"]


def test_an_a_to_z_group_is_ordered_this_way_too() -> None:
    rows = ["ACB Media 10", "ACB Media 2", "ACB Media 1"]
    groups = dict(browse_helpers.letter_groups(rows, label=lambda row: row))
    assert groups["A"] == ["ACB Media 1", "ACB Media 2", "ACB Media 10"]
