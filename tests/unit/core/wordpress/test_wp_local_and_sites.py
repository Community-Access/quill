"""Sites, working copies, versions and conflict protection, on disk only."""

from __future__ import annotations

from quill.core.wordpress import local as lc
from quill.core.wordpress import sites as st


def test_many_sites_one_default_and_matching_by_address(tmp_path) -> None:
    store = st.SiteStore()
    radio = st.SiteProfile(id="a", name="Community Radio", site_url="https://radio.example")
    blog = st.SiteProfile(id="b", name="Blog", site_url="https://radio.example/blog")
    com = st.SiteProfile(
        id="c",
        name="Notes",
        site_url="https://notes.wordpress.com",
        kind="wpcom",
        wpcom_site="notes.wordpress.com",
    )
    for site in (radio, blog, com):
        store.upsert(site)
    assert store.default is radio
    assert store.match_url("https://www.radio.example/about/").id == "a"
    assert store.match_url("https://radio.example/blog/2026/11/hi").id == "b"
    assert store.match_url("https://notes.wordpress.com/x").id == "c"
    assert store.match_url("https://elsewhere.example/") is None
    st.save_sites(store, tmp_path)
    again = st.load_sites(tmp_path)
    assert [s.name for s in again.sites] == ["Community Radio", "Blog", "Notes"]
    again.remove("a")
    assert again.default_id == "b"
    again.rename("b", "  The Blog ")
    assert again.get("b").name == "The Blog"


def test_old_publishing_connections_are_imported_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    from quill.core import publishing

    publishing.upsert_publishing_connection(
        publishing.PublishingConnectionProfile(
            id="pub-1", label="Radio", site_url="https://radio.example", account_identifier="jeff"
        )
    )
    store = st.load_sites()
    assert [(s.id, s.name, s.username) for s in store.sites] == [("pub-1", "Radio", "jeff")]
    assert st.sites_path().exists()


def test_api_for_signs_with_the_right_kind() -> None:
    self_hosted = st.SiteProfile(
        id="a", name="R", site_url="https://radio.example", username="jeff"
    )
    api = st.api_for(self_hosted, secret_loader=lambda _id: "pw")
    assert api.auth.kind == "app_password" and api.site_name == "R"
    com = st.SiteProfile(
        id="c",
        name="N",
        site_url="https://n.wordpress.com",
        kind="wpcom",
        wpcom_site="n.wordpress.com",
    )
    assert st.api_for(com, secret_loader=lambda _id: "tok").auth.kind == "bearer"


def test_working_copy_versions_and_restore(tmp_path) -> None:
    store = lc.LocalStore(tmp_path)
    copy = lc.WorkingCopy(
        site_id="a", kind="post", local_id=lc.new_local_id(), title="Spring", text="One"
    )
    store.save(copy)
    store.add_version(copy, lc.REASON_SAVED)
    store.add_version(copy, lc.REASON_SAVED)  # identical: not kept twice
    copy.text = "Two"
    store.save(copy)
    store.add_version(copy, lc.REASON_SAVED)
    versions = store.versions(copy.key)
    assert [v.text for v in versions] == ["Two", "One"]
    restored = store.restore(copy, versions[1].id)
    assert restored.text == "One"
    # What it replaced is still there (here it was already the newest version).
    assert store.versions(copy.key)[0].text == "Two"
    assert versions[0].spoken().endswith("Spring, Saved")


def test_a_sent_draft_keeps_its_folder_and_is_found_by_its_site_id(tmp_path) -> None:
    """The editor still has the file open, so the folder must not move under it."""
    store = lc.LocalStore(tmp_path)
    copy = store.save(lc.WorkingCopy(site_id="a", kind="page", local_id="x1", title="About"))
    path = store.write_document(copy)
    store.add_version(copy, lc.REASON_SAVED)
    old_key = copy.key
    store.rekey(copy, 42)
    assert copy.key == old_key
    assert store.copy_for_path(path).remote_id == 42
    assert store.find("a", "page", 42).title == "About"
    assert store.find("a", "page", 43) is None
    assert len(store.versions(copy.key)) == 1


def test_drafts_are_listed_per_site_newest_first(tmp_path) -> None:
    store = lc.LocalStore(tmp_path)
    store.save(lc.WorkingCopy(site_id="a", kind="post", local_id="1", title="Old"))
    store.save(lc.WorkingCopy(site_id="b", kind="post", local_id="2", title="Other"))
    store.save(lc.WorkingCopy(site_id="a", kind="post", local_id="3", title="New"))
    assert [d.title for d in store.drafts("a")] == ["New", "Old"]
    assert len(store.drafts()) == 3


def test_conflict_only_when_the_site_is_newer() -> None:
    assert lc.conflict_between("2026-11-03T10:00:00", "2026-11-03T10:00:00") is None
    assert lc.conflict_between("", "2026-11-03T10:00:00") is None
    conflict = lc.conflict_between("2026-11-03T10:00:00", "2026-11-03T11:30:00")
    assert conflict is not None
    assert conflict.spoken("Community Radio", "Sam") == (
        "The copy on Community Radio was changed by Sam on 3 November 2026, 11:30 AM, "
        "after you opened it. Nothing was sent."
    )
