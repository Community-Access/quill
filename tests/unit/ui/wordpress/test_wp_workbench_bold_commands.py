"""W7's bold commands in the real frame on a fake site, each called through its command:
Copy to Site, Compare Sites, snapshots and Put Back, the queue's clock and reviewers,
Move to Another Day, Import a Folder of Documents, the REST Console's argument check,
and Watches' standing and rounds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import block_notes  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command  # noqa: E402
from quill.core.wordpress.workbench_editorial import load_reviews  # noqa: E402
from quill.core.wordpress.workbench_options import WorkbenchOptions, save_options  # noqa: E402
from quill.core.wordpress.workbench_snapshot import COMPARE_OMITS  # noqa: E402
from quill.core.wordpress.workbench_watches import load_state  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE, _go, _select  # noqa: E402

bench = _bench
OTHER = "Staging"


@pytest.fixture
def answers(monkeypatch):
    """Every chooser picks the first row and every preview is accepted; reports are kept."""
    reports: list[str] = []
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: True)
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: reports.append(k["text"]))
    return reports


def _second_site(bench) -> None:
    bench.provider._profiles[OTHER] = SiteProfile("s2", OTHER, "https://staging.example", "jeff")


def _posts(bench, *rows: int) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, *rows)


def test_copy_and_move_offer_on_every_kind_the_prd_names() -> None:
    for kind in ("item", "media", "menu", "term", "pattern", "form"):
        verbs = [row.command_id for row in WORDPRESS_ACTIONS.rows_for(kind)]
        assert command("copy_to_site") in verbs, kind
    assert command("move_day") in [r.command_id for r in WORDPRESS_ACTIONS.rows_for("item")]


def test_copy_to_site_previews_then_makes_drafts_and_records_history(bench, answers) -> None:
    _second_site(bench)
    _posts(bench, 1)
    bench.run(command("copy_to_site"))
    made = [w for w in bench.api.writes if w[1] == "wp/v2/posts"]
    assert made and made[0][2]["status"] == "draft" and made[0][2]["title"] == "News"
    assert "Copied to Staging" in bench.said[-1]


def test_compare_sites_reports_and_states_what_it_does_not_compare(bench, answers) -> None:
    _second_site(bench)
    _go(bench, NodeRef("site", "overview", SITE))
    bench.run(command("compare_sites"))
    assert answers and answers[-1].endswith(COMPARE_OMITS)


def test_a_snapshot_can_be_put_back_after_a_preview(bench, answers) -> None:
    _go(bench, NodeRef("site", "overview", SITE))
    bench.run(command("snapshot"))
    assert "Snapshot of" in bench.said[-1]
    bench.api.posts[0]["title"] = {"raw": "Spoiled", "rendered": "Spoiled"}
    bench.run(command("restore_snapshot"))
    assert ("POST", "wp/v2/posts/1") in [(w[0], w[1]) for w in bench.api.writes]
    put = next(w[2] for w in bench.api.writes if w[1] == "wp/v2/posts/1")
    assert put["title"] == "Hello" and "Put back 1 of 1" in bench.said[-1]


def test_approve_and_schedule_reads_the_site_clock_and_sends_gmt(bench, answers, monkeypatch):
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "2030-01-02 9:00 AM")
    _posts(bench, 0)
    bench.run(command("approve_schedule"))
    sent = ("POST", "wp/v2/posts/1", {"status": "future", "date_gmt": "2030-01-02T09:00:00"})
    assert sent in bench.api.writes
    assert "Wednesday 2 January 2030, 9:00 AM at the site (UTC)" in bench.said[-1]


def test_a_time_that_does_not_exist_is_refused_with_why(bench, answers, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "2030-13-40 9:00")
    _posts(bench, 0)
    bench.run(command("approve_schedule"))
    assert "year, month and day" in bench.said[-1]
    assert not [w for w in bench.api.writes if w[1] == "wp/v2/posts/1"]


def test_move_to_another_day_previews_and_sends_the_new_date(bench, answers, monkeypatch):
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "2030-01-02 10:15")
    _posts(bench, 1)
    bench.run(command("move_day"))
    assert ("POST", "wp/v2/posts/2", {"date_gmt": "2030-01-02T10:15:00"}) in bench.api.writes
    assert bench.said[-1].startswith("Moved 1 to")


def test_assign_a_reviewer_from_the_site_notes_it_and_keeps_it(bench, answers, monkeypatch):
    noted: list[tuple[int, str]] = []
    monkeypatch.setattr(block_notes, "add_note", lambda api, i, text: noted.append((i, text)))
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 1)  # Ann
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "The intro")
    _posts(bench, 0)
    bench.run(command("assign_reviewer"))
    assert noted == [(1, "Review requested from Ann. The intro")]
    assert [(r.reviewer, r.item_id) for r in load_reviews(bench.provider._data_dir)] == [("Ann", 1)]
    assert "WordPress sends no email" in bench.said[-1]


def test_import_a_folder_makes_a_draft_per_document_and_reports_each(
    bench, answers, monkeypatch, tmp_path: Path
) -> None:
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "one.md").write_text("# Opening Night\n\nDoors at 7.", encoding="utf-8")
    monkeypatch.setattr(type(bench.provider), "_folder", lambda self, title: folder)
    _go(bench, NodeRef("site", "posts", SITE))
    bench.run(command("import_folder"))
    made = [w[2] for w in bench.api.writes if w[1] == "wp/v2/posts"]
    assert made[0]["title"] == "Opening Night" and made[0]["status"] == "draft"
    assert answers[-1].startswith("Made one.md: Opening Night")


def test_the_console_stops_a_write_missing_a_required_argument(bench, answers) -> None:
    from quill.ui.wordpress_rest_console import RestConsole

    bench.provider.discover(SITE)
    ctx = bench.provider.ctx(SITE)
    sent: list[Any] = []
    bench.api.request = lambda method, route, **kw: sent.append((method, route))  # type: ignore[method-assign]
    console = RestConsole(bench.provider, SITE, ctx)
    try:
        console.by_template["wp/v2/posts"] = {
            "endpoints": [{"methods": ["POST"], "args": {"title": {"required": True}}}]
        }
        console.route.ChangeValue("wp/v2/posts")
        console.method.SetSelection(1)  # POST
        console._on_route(None)
        assert "title (any, required)" in console.accepts.GetValue()
        console.send()
        assert sent == [] and bench.said[-1] == "title is required."
    finally:
        console.dialog.Destroy()


def test_watches_say_when_they_last_ran_and_each_site_state(bench) -> None:
    save_options(WorkbenchOptions(watches=("comment",)), bench.provider._data_dir)
    _go(bench, NodeRef("", "watches"))
    facts = {r.cell("fact"): r.cell("value") for r in bench.rows}
    assert facts["Last round"] == "none yet" and facts[SITE] == "not checked yet"


def test_a_watch_round_claims_its_turn_and_keeps_a_down_site_quiet_the_first_time(
    tmp_path: Path,
) -> None:
    from quill.ui.wordpress_watch_commands import watch_round

    said: list[str] = []

    class _Host:
        def announce(self, text: str) -> None:
            said.append(text)

        def run_task(self, _name: str, work: Any, done: Any, _failed: Any) -> None:
            done(work())

    class _Commands:
        _data_dir = tmp_path
        host = _Host()

        def sites(self) -> SiteStore:
            return SiteStore([SiteProfile("s1", SITE, "https://radio.example", "jeff")], "s1")

        def api(self, _profile: Any) -> Any:
            raise OSError("offline")

    save_options(WorkbenchOptions(watches=("site_down",)), tmp_path)
    watch_round(_Commands())
    state = load_state(tmp_path)
    assert said == [] and SITE in state.down and state.last_round > 0
    watch_round(_Commands())  # not due again for fifteen minutes
    assert said == []


def test_a_plain_language_batch_lists_exact_items_then_sends_the_checked(
    bench, answers, monkeypatch
) -> None:
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "move all drafts to pending")
    listed: list[list[str]] = []

    def checks(*_a: Any, **k: Any) -> list[int]:
        listed.append(list(k["rows"]))
        return [0]

    monkeypatch.setattr(wdlg, "ask_checks", checks)
    _go(bench, NodeRef("site", "posts", SITE))
    bench.run(command("plain_batch"))
    assert listed == [[f"{SITE}: Hello"]]
    assert ("POST", "wp/v2/posts/1", {"status": "pending"}) in bench.api.writes
    assert answers[-1].startswith("Set draft posts to pending")


def test_words_it_does_not_read_are_answered_with_examples(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "make it nice")
    _go(bench, NodeRef("site", "posts", SITE))
    bench.run(command("plain_batch"))
    assert bench.said[-1].startswith("It reads phrases like")


def test_a_saved_request_becomes_a_menu_row_and_runs_filled_in(bench, monkeypatch) -> None:
    from quill.ui.wordpress_rest_console import RestConsole

    sent: list[tuple[str, str]] = []

    class _R:
        payload: Any = {"id": 1}

    def request(method: str, route: str, **kw: Any) -> Any:
        sent.append((method, route))
        return _R()

    bench.api.request = request  # type: ignore[method-assign]
    monkeypatch.setattr(RestConsole, "show", lambda self: self.dialog.Destroy() or 0)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Post one")
    bench.provider.discover(SITE)
    console = RestConsole(bench.provider, SITE, bench.provider.ctx(SITE))
    try:
        console.route.ChangeValue("wp/v2/posts/1")
        console.save_request()
    finally:
        console.dialog.Destroy()
    labels = [label for label, _run in bench.provider.dynamic_menu("rest_saved")]
    assert labels == [f"Post one (GET wp/v2/posts/1 on {SITE})"]
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    _go(bench, NodeRef("site", "overview", SITE))
    bench.run(command("run_saved"))
    assert sent[-1] == ("GET", "wp/v2/posts/1")
    bench.run(command("forget_saved"))
    assert bench.provider.dynamic_menu("rest_saved") == []


def test_a_gravity_form_copies_to_another_site_without_entries(bench, answers, monkeypatch):
    from quill.core.wordpress.workbench_rows import WbRow

    _second_site(bench)
    whole = {"id": 3, "title": "Sign Up", "fields": [], "entries": 4}
    original = bench.api.get
    monkeypatch.setattr(
        bench.api,
        "get",
        lambda route, **p: dict(whole) if route == "gf/v2/forms/3" else original(route, **p),
    )
    monkeypatch.setattr(bench.provider, "selected_rows", lambda: [])
    row = WbRow(
        "gravity_form", SITE, "3", {}, "", subkind="gravity", raw={"id": 3, "title": "Sign Up"}
    )
    bench.provider.do_copy_to_site(None, row)
    made = [w for w in bench.api.writes if w[1] == "gf/v2/forms"]
    assert made and made[0][2] == {"title": "Sign Up", "fields": []}
