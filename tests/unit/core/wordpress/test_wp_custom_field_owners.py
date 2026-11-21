"""Properties hides another plugin's custom fields until Show All Fields (wordpress.md 9.15).

Jeff, 2026-11-20: on the test site an ordinary post's Properties listed 37
custom fields, 34 of them The Events Calendar's event, venue and organizer
fields. WordPress's own, QUILL's own, Yoast's SEO fields and ACF's field
groups stay in view; the rest wait behind a check box.
"""

from __future__ import annotations

from quill.core.wordpress import custom_fields as cf
from quill.core.wordpress.custom_field_owners import hidden_sentence, plugin_of, split_keys
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import sheet_for

#: The post schema's meta keys on the test site (WordPress 7.1.5, 2026-11-20), trimmed.
LIVE = {
    "_EventStartDate": {"type": "string"},
    "_EventEndDate": {"type": "string"},
    "_VenueCity": {"type": "string"},
    "_OrganizerEmail": {"type": "string"},
    "_acf_changed": {"type": "boolean"},
    "_yoast_wpseo_title": {"type": "string"},
    "_yoast_wpseo_metadesc": {"type": "string"},
    "_yoast_wpseo_focuskw": {"type": "string"},
    "footnotes": {"type": "string"},
    "pmpro_default_level": {"type": "integer"},
    "subtitle": {"type": "string", "title": "Subtitle"},
    "qaf_form_id": {"type": "integer"},
}


def test_owners_by_prefix_and_what_stays_in_view() -> None:
    assert plugin_of("_EventStartDate") == "The Events Calendar"
    assert plugin_of("_VenueCity") == plugin_of("_OrganizerEmail") == "The Events Calendar"
    assert plugin_of("pmpro_default_level") == "Paid Memberships Pro"
    assert plugin_of("_acf_changed") == "Advanced Custom Fields"
    for key in ("_yoast_wpseo_title", "subtitle", "qaf_form_id", "quill_note", "footnotes"):
        assert plugin_of(key) == "", key
    shown, hidden = split_keys(sorted(LIVE))
    assert shown == [
        "_yoast_wpseo_focuskw",
        "_yoast_wpseo_metadesc",
        "_yoast_wpseo_title",
        "footnotes",
        "qaf_form_id",
        "subtitle",
    ]
    assert hidden == {
        "The Events Calendar": [
            "_EventEndDate",
            "_EventStartDate",
            "_OrganizerEmail",
            "_VenueCity",
        ],
        "Advanced Custom Fields": ["_acf_changed"],
        "Paid Memberships Pro": ["pmpro_default_level"],
    }


def test_the_sentence_counts_the_hidden_fields_largest_owner_first() -> None:
    said = hidden_sentence({"Paid Memberships Pro": 1, "The Events Calendar": 34})
    assert said == (
        "35 fields are hidden because a plugin adds them to every item: "
        "34 from The Events Calendar, 1 from Paid Memberships Pro."
    )
    assert hidden_sentence({"Rank Math": 1}) == (
        "1 field is hidden because a plugin adds it to every item: 1 from Rank Math."
    )
    assert hidden_sentence({}) == ""


def test_the_form_hides_them_counts_them_and_shows_all_on_request() -> None:
    form = cf.build_form(LIVE, {"_EventStartDate": "2027-01-15"}, {})
    keys = [f.key for f in form.fields]
    assert keys == [
        "_yoast_wpseo_title",
        "_yoast_wpseo_metadesc",
        "_yoast_wpseo_focuskw",
        "subtitle",
        "qaf_form_id",
    ]
    assert form.hidden == {
        "The Events Calendar": 4,
        "Advanced Custom Fields": 1,
        "Paid Memberships Pro": 1,
    }
    assert "_EventStartDate" not in form.site_values  # never compared, so never sent
    every = cf.build_form(LIVE, {}, {}, show_all=True)
    assert len(every.fields) == len(LIVE) - 1 and every.hidden == {}  # footnotes is plumbing


def test_the_show_all_box_leads_the_page_with_its_own_access_key() -> None:
    form = cf.build_form(LIVE, {}, {})
    fields = cf.with_show_all(form)
    box = fields[0]
    assert box.key == cf.SHOW_ALL_KEY and box.kind == "check" and box.value is False
    assert box.label == "&Show all fields, including 6 hidden"
    assert box.help.startswith("Check this and choose OK to reopen this window")
    letters = [f.label[f.label.index("&") + 1].lower() for f in fields if "&" in f.label]
    assert len(letters) == len(set(letters))  # GATE-14
    # A box answer is never a change to send.
    answers = {f.key: f.value for f in form.fields}
    assert cf.changes(form, answers) == {}
    assert cf.with_show_all(cf.build_form(LIVE, {}, {}, show_all=True))[0].key != cf.SHOW_ALL_KEY


def test_the_workbench_sheet_puts_other_plugins_fields_on_their_own_page() -> None:
    row = WbRow("item", "Radio", "41", {"title": "Spring fair"}, "", raw={"type": "post"})
    sheet = sheet_for(row, meta=LIVE)
    pages = {p.key: p for p in sheet.pages}
    meta = [f.key for f in pages["meta"].fields]
    assert "meta._yoast_wpseo_title" in meta and "meta.subtitle" in meta
    assert not any(k.startswith(("meta._Event", "meta.pmpro")) for k in meta)
    other = pages["meta_other"]
    assert other.title == "Fields Plugins Add to Every Item" and list(sheet.pages)[-1] is other
    assert [f.label for f in other.fields][:2] == [
        "acf changed (Advanced Custom Fields)",
        "pmpro default level (Paid Memberships Pro)",
    ]
