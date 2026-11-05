"""Tools > Forms > Responses: views, find, exports, delete, the count setting (17a.8)."""

from __future__ import annotations

from typing import Any

import pytest

BAF = "/wp-json/baf/v1"


@pytest.fixture
def three(pub_site: Any, make_form: Any, make_entry: Any) -> Any:
    entries = [
        make_entry(
            43, "2026-11-04 09:05:00", name="Ann Lee", email="ann@example.org", city="Leeds"
        ),
        make_entry(
            42, "2026-11-03 14:10:00", name="Jane Smith", email="jane@example.org", city="York"
        ),
        make_entry(41, "2026-11-03 08:00:00", name="", email="raj@example.org", city="Leeds"),
    ]
    pub_site.on("GET", f"{BAF}/forms", [make_form(12, entry_count=3)])
    pub_site.on("GET", f"{BAF}/forms/12", make_form(12, entry_count=3))
    pub_site.on("GET", f"{BAF}/entries", entries)
    return entries


def _open(fp: Any, pub_dialogs: Any) -> None:
    pub_dialogs.answer("ask_choice", 0)
    fp.cmd_form_responses()


def test_responses_list_newest_first_with_who_and_when(fp, pub_dialogs, pub_site, three):
    _open(fp, pub_dialogs)

    rows = pub_dialogs.rows()
    assert rows[0] == "Response 43, 4 November, 9:05 AM, Ann Lee, Spring fair"
    assert rows[1] == "Response 42, 3 November, 2:10 PM, Jane Smith, Spring fair"
    assert rows[2] == "Response 41, 3 November, 8:00 AM, raj@example.org, Spring fair"
    query = pub_site.query(pub_site.sent("GET", f"{BAF}/entries")[0])
    assert query["form_id"] == ["12"]
    assert fp.published().seen("radio", 12) == 3


def test_read_one_at_a_time_is_question_and_answer(fp, pub_dialogs, three):
    _open(fp, pub_dialogs)

    pub_dialogs.window["on_enter"](1)

    report = pub_dialogs.reports[-1]["text"]
    assert "Your name: Jane Smith\nEmail address: jane@example.org\nCity: York" in report


def test_views_group_by_date_and_by_place(fp, pub_dialogs, three):
    _open(fp, pub_dialogs)

    pub_dialogs.answer("ask_choice", 1)
    rows = pub_dialogs.press("View...")
    assert rows[0] == "Wednesday 4 November 2026, 1 response"
    assert rows[2] == "Tuesday 3 November 2026, 2 responses"

    pub_dialogs.answer("ask_choice", 2)
    rows = pub_dialogs.press("View...")
    assert rows[0] == "Leeds, 2 responses"
    assert rows[3] == "York, 1 response"


def test_reading_a_heading_says_choose_a_response(fp, pub_dialogs, pub_host, three):
    _open(fp, pub_dialogs)
    pub_dialogs.answer("ask_choice", 1)
    pub_dialogs.press("View...")

    pub_dialogs.press("Read", 0)

    assert "That is a heading" in pub_host.said
    assert not pub_dialogs.reports


def test_find_narrows_to_matching_answers(fp, pub_dialogs, pub_host, three):
    _open(fp, pub_dialogs)
    pub_dialogs.answer("ask_text", "leeds")

    rows = pub_dialogs.press("Find...")

    assert len(rows) == 2
    assert "2 responses with leeds." in pub_host.said


def test_export_csv_writes_where_you_choose(fp, pub_dialogs, pub_host, three, tmp_path):
    _open(fp, pub_dialogs)
    pub_dialogs.answer("save_as", tmp_path / "out")

    pub_dialogs.press("Export to CSV...")

    text = (tmp_path / "out.csv").read_bytes().decode("utf-8-sig")
    assert text.splitlines()[0] == "Response,Sent,Your name,Email address,City"
    assert "42,2026-11-03 14:10,Jane Smith,jane@example.org,York" in text
    assert "Saved 3 responses to out.csv." in pub_host.said
    assert not pub_host.opened


def test_open_as_table_saves_then_opens(fp, pub_dialogs, pub_host, three, tmp_path):
    from quill.ui import wordpress_dialogs as dlg

    _open(fp, pub_dialogs)
    pub_dialogs.answer("save_as", tmp_path / "grid.csv")

    assert pub_dialogs.press("Open as Table...") is dlg.CLOSE
    assert pub_host.opened == [tmp_path / "grid.csv"]


def test_export_word_one_response(fp, pub_dialogs, pub_host, three, tmp_path):
    import docx

    _open(fp, pub_dialogs)
    pub_dialogs.answer("ask_choice", 0).answer("save_as", tmp_path / "one.docx")

    pub_dialogs.press("Export to Word...", 1)

    text = [p.text for p in docx.Document(str(tmp_path / "one.docx")).paragraphs]
    assert "Response 42, sent 3 November, 2:10 PM" in text
    assert "Jane Smith" in text
    assert "Saved 1 response to one.docx." in pub_host.said


def test_delete_marked_after_a_confirmation_with_the_count(
    fp, pub_dialogs, pub_site, pub_host, three
):
    pub_site.on("DELETE", f"{BAF}/entries/43", {"deleted": True})
    pub_site.on("DELETE", f"{BAF}/entries/41", {"deleted": True})
    _open(fp, pub_dialogs)
    pub_dialogs.press("Mark", 0)
    pub_dialogs.press("Mark", 2)
    pub_dialogs.answer("confirm", True)

    rows = pub_dialogs.press("Delete...", 1)

    assert pub_dialogs.asked("confirm")[0]["yes_label"] == "Delete 2"
    assert len(pub_site.sent("DELETE", f"{BAF}/entries/43")) == 1
    assert "force" not in pub_site.sent("DELETE", f"{BAF}/entries/43")[0].full_url
    assert rows == ["Response 42, 3 November, 2:10 PM, Jane Smith, Spring fair"]
    assert "2 responses moved to the Trash on Community Radio." in pub_host.said


def test_delete_cancelled_sends_nothing(fp, pub_dialogs, pub_site, three):
    _open(fp, pub_dialogs)

    pub_dialogs.press("Delete...", 0)

    assert not [r for r in pub_site.requests if r.get_method() == "DELETE"]


def test_say_new_count_turns_the_site_setting_off(fp, pub_dialogs, pub_host, three, tmp_path):
    from quill.core.wordpress import sites as st

    fp.profile = fp.form_sites().get("radio")
    from dataclasses import replace

    store = st.load_sites(tmp_path)
    store.upsert(replace(store.get("radio"), announce_new_responses=True))
    st.save_sites(store, tmp_path)
    _open(fp, pub_dialogs)

    pub_dialogs.press("Say New Count")

    assert st.load_sites(tmp_path).get("radio").announce_new_responses is False
    assert "no longer say how many new responses" in pub_host.said


def test_responses_of_the_form_in_front_need_no_choosing(fp, pub_dialogs, pub_host, three):
    from quill.core.forms import published as pub

    fp.published().set_link(pub_host.path, pub.Link("radio", 12, "Spring fair"))

    fp.cmd_form_responses()

    assert not pub_dialogs.asked("ask_choice")
    assert pub_dialogs.list_windows


def test_no_responses_yet_says_so(fp, pub_dialogs, pub_site, pub_host, make_form):
    pub_site.on("GET", f"{BAF}/forms", [make_form(12, entry_count=0)])
    pub_site.on("GET", f"{BAF}/forms/12", make_form(12, entry_count=0))
    pub_site.on("GET", f"{BAF}/entries", [])

    _open(fp, pub_dialogs)

    assert "has no responses yet" in pub_host.said
    assert not pub_dialogs.list_windows


def test_responses_are_off_in_safe_mode(fp, pub_host, pub_site):
    pub_host.ai._safe_mode = True

    fp.cmd_form_responses()

    assert "off in Safe Mode" in pub_host.said
    assert not pub_site.requests


def test_responses_cancelled_at_the_form_reads_no_answers(fp, pub_site, three):
    fp.cmd_form_responses()

    assert not pub_site.sent("GET", f"{BAF}/entries")
