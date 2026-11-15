"""Every write is checked by its tier, and every change is in Change History (how.md 1 to 4).

The review found Read Only, Safe Mode and View As Role enforced only for
commands on the selected row's own context menu: the menu bar's Empty Spam
and imports, a node's New Here, Delete on a person and Shift+Delete on an
application password all ran. It found writes that recorded nothing, so Ctrl+Z
reached past them to an older change, and a change that could not be undone
walling off every older one. And it found previews that went ahead on Enter at
the destructive tier, and three Workbench chords the window's key hook ate.
Reuses the fake site of ``test_wp_workbench_window``; work runs inline.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.core.wordpress.workbench_permissions import Access  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow, item_row  # noqa: E402
from quill.core.workbench.actions import Tier  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _go,
    _inline,
    _select,
)

READ_ONLY = f"Workbench access on {SITE} is Read Only. Site > Workbench Access changes it."
POSTS = NodeRef("site", "posts", SITE)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = FakeApi()
    provider = WordPressWorkbenchProvider(
        _Commands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    wdlg.set_running_tier(None)
    frame.frame.Destroy()
    tx.clear_cache()


def _user() -> WbRow:
    return WbRow("user", SITE, "4", {"name": "Ann"}, "Ann", route="wp/v2/users/4")


def _password(status: str = "") -> WbRow:
    return WbRow(
        "app_password",
        SITE,
        "u1",
        {"name": "Phone"},
        "Phone",
        route="wp/v2/users/me/application-passwords/u1",
        status=status,
    )


def _across() -> WbRow:
    return WbRow(
        "across",
        "",
        "Akismet",
        {"name": "Akismet"},
        "Akismet",
        subkind="plugins",
        raw={"objects": {SITE: {"plugin": "akismet/akismet"}}, "missing": []},
    )


def _post() -> WbRow:
    return item_row(FakeApi().posts[0], "post", SITE)


#: (verb run, the row selected, the handler that would do it) for every write the
#: review found unchecked: menu-bar and node commands, and Delete on two row kinds.
GUARDED = [
    ("empty_spam", None, "do_empty_spam"),
    ("empty_comment_trash", None, "do_empty_comment_trash"),
    ("new_here", None, "do_new_here"),
    ("new_here", "post", "do_new_here"),  # Ctrl+N with a post selected
    ("empty_trash", "post", "do_empty_trash"),
    ("import_posts", None, "do_import_posts"),
    ("import_folder", None, "do_import_folder"),
    ("import_wxr", None, "do_import_wxr"),
    ("import_platform", None, "do_import_platform"),
    ("restore_snapshot", None, "do_restore_snapshot"),
    ("plain_batch", None, "do_plain_batch"),
    ("your_profile", None, "do_your_profile"),
    ("trash", "user", "do_trash"),  # Delete on a person is Remove
    ("delete_permanently", "user", "do_delete_permanently"),
    ("trash", "password", "do_trash"),  # Delete on an application password is Revoke
    ("delete_permanently", "password", "do_delete_permanently"),
    ("promote_network", "across", "do_promote_network"),
    ("install_missing", "across", "do_install_missing"),
]

_ROWS = {"post": _post, "user": _user, "password": _password, "across": _across}


def _run(bench: Any, verb: str, row: str | None, handler: str, monkeypatch) -> list[str]:
    reached: list[str] = []
    monkeypatch.setattr(bench.provider, handler, lambda *_a: reached.append(verb))
    chosen = _ROWS[row]() if row else None
    assert bench.provider.run(command(verb), POSTS, chosen)
    return reached


@pytest.mark.parametrize(("verb", "row", "handler"), GUARDED)
def test_every_write_is_refused_under_read_only_with_the_reason(
    bench, monkeypatch, verb, row, handler
) -> None:
    bench.provider.access_store.set("s1", Access.READ_ONLY)
    assert _run(bench, verb, row, handler, monkeypatch) == []
    assert bench.said[-1] == READ_ONLY


def test_menu_bar_writes_are_greyed_under_read_only(bench) -> None:
    _go(bench, POSTS)
    assert bench.provider.supports(command("empty_spam"))
    bench.provider.access_store.set("s1", Access.READ_ONLY)
    for verb in ("empty_spam", "import_posts", "new_here", "plain_batch"):
        assert not bench.provider.supports(command(verb)), verb
    assert bench.provider.supports(command("roles"))


@pytest.mark.parametrize(("verb", "row", "handler"), GUARDED)
def test_every_write_runs_under_full_access(bench, monkeypatch, verb, row, handler) -> None:
    assert _run(bench, verb, row, handler, monkeypatch) == [verb]


def test_safe_mode_and_view_as_role_refuse_the_menu_bar_too(bench, monkeypatch) -> None:
    bench.provider.safe_mode = True
    assert _run(bench, "empty_spam", None, "do_empty_spam", monkeypatch) == []
    assert bench.said[-1] == "Safe Mode is on, so the Workbench only reads."
    bench.provider.safe_mode = False
    bench.provider.view_as[SITE] = "editor"
    assert _run(bench, "import_posts", None, "do_import_posts", monkeypatch) == []
    assert bench.said[-1].startswith(f"You are viewing {SITE} as Editor")


def test_organize_still_refuses_removing_a_person_on_delete(bench, monkeypatch) -> None:
    """Delete is Move to Trash (Organize) on a post, but Remove (Destructive) on a person."""
    bench.provider.access_store.set("s1", Access.ORGANIZE)
    assert _run(bench, "trash", "user", "do_trash", monkeypatch) == []
    assert "Organize" in bench.said[-1]


def test_reads_are_never_refused(bench, monkeypatch) -> None:
    bench.provider.access_store.set("s1", Access.READ_ONLY)
    for verb in ("roles", "comment_counts", "export_list", "snapshot", "rest_console"):
        assert _run(bench, verb, None, f"do_{verb}", monkeypatch) == [verb], verb


def test_the_password_quill_signs_in_with_is_never_revoked(bench, monkeypatch) -> None:
    for verb in ("trash", "delete_permanently", "revoke"):
        handler = f"do_{verb}"
        reached: list[str] = []
        monkeypatch.setattr(bench.provider, handler, lambda *_a, r=reached, v=verb: r.append(v))
        bench.provider.run(command(verb), POSTS, _password("current"))
        assert reached == []
        assert bench.said[-1].startswith(f"QUILL signs in to {SITE} with this application")


def test_shift_delete_on_a_password_is_revoke_not_a_generic_delete(bench, monkeypatch) -> None:
    revoked: list[WbRow] = []
    monkeypatch.setattr(bench.provider, "do_revoke", lambda _ref, row: revoked.append(row))
    monkeypatch.setattr(bench.provider, "selected_rows", lambda: [_password()])
    bench.provider.do_delete_permanently(POSTS, _password())
    assert [r.key for r in revoked] == ["u1"]
    assert bench.api.writes == []


def test_the_rest_console_refuses_a_write_under_read_only(bench) -> None:
    from quill.ui.wordpress_rest_console import METHODS, RestConsole

    bench.provider.access_store.set("s1", Access.READ_ONLY)
    console = RestConsole(bench.provider, SITE, bench.provider.ctx(SITE))
    try:
        console.method.SetSelection(METHODS.index("POST"))
        console.route.ChangeValue("wp/v2/posts/1")
        console.send()
        assert bench.said[-1] == READ_ONLY
        assert bench.api.writes == []
        assert bench.provider.access_refusal(SITE, Tier.READ) == ""
    finally:
        console.dialog.Destroy()


# -- every change is in Change History ---------------------------------------------


def test_a_reply_is_recorded_so_ctrl_z_does_not_undo_an_older_change(bench, monkeypatch) -> None:
    _go(bench, POSTS)
    _select(bench, 0)
    bench.run(command("trash"))  # an undoable change first
    assert bench.provider.history.can_undo()
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "Thank you")
    comment = WbRow("comment", SITE, "7", {"author": "Ann"}, "Ann", raw={"id": 7, "post": 2})
    bench.provider.run(command("reply"), NodeRef("site", "comments", SITE), comment)
    newest = bench.provider.history.entries[-1]
    assert newest.summary == f"Reply on {SITE}." and newest.undo is None
    bench.run(command("undo"))
    assert bench.said[-1] == (
        f"Reply on {SITE}. This cannot be undone. Ctrl+Z again undoes the change before it."
    )
    assert bench.api.posts[0]["status"] == "trash"  # not undone yet
    bench.run(command("undo"))
    assert bench.api.posts[0]["status"] == "draft"  # the trash, put back on the next press


def test_empty_spam_is_recorded_as_a_change_that_cannot_be_undone(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    bench.provider.run(command("empty_spam"), POSTS, None)
    assert ("DELETE", "wp/v2/comments/8", {"force": True}) in bench.api.writes
    newest = bench.provider.history.entries[-1]
    assert newest.summary == f"Empty Spam on {SITE}." and newest.undo is None


@pytest.mark.parametrize(
    ("verb", "kind"),
    [
        ("merge_into", "term"),
        ("allow_sender", "comment"),
        ("convert_term", "term"),
        ("edit_product", "shop_product"),
        ("change_order_status", "shop_order"),
        ("new_coupon", "shop_coupon"),
        ("edit_event", "tribe_event"),
        ("add_redirect", "redirect"),
        ("change_membership", "user"),
    ],
)
def test_a_write_that_records_nothing_gets_a_history_entry(bench, monkeypatch, verb, kind) -> None:
    """The central rule: a writing command that sent a change and recorded none."""
    provider = bench.provider
    bench.api.role = "administrator"

    def handler(_ref: Any, _row: Any) -> None:
        api = provider.ctx(SITE).api
        provider.background("writing", lambda: api.post("wp/v2/anything", {}), lambda _r: None)

    monkeypatch.setattr(provider, f"do_{verb}", handler)
    before = len(provider.history.entries)
    provider.run(command(verb), POSTS, WbRow(kind, SITE, "1", {}, ""))
    assert len(provider.history.entries) == before + 1
    assert provider.history.entries[-1].undo is None


def test_a_write_that_records_itself_is_not_recorded_twice(bench) -> None:
    _go(bench, POSTS)
    _select(bench, 0)
    bench.run(command("trash"))
    assert len(bench.provider.history.entries) == 1


def test_a_read_and_a_cancelled_write_record_nothing(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: False)
    bench.provider.run(command("empty_spam"), POSTS, None)  # counted, then cancelled
    bench.provider.run(command("comment_counts"), POSTS, _post())
    assert bench.provider.history.entries == ()


# -- Enter in a destructive preview is Cancel ----------------------------------------


def _default_button(dialog: Any) -> int:
    item = dialog.GetDefaultItem()
    return item.GetId() if item is not None else wx.ID_NONE


def test_a_destructive_preview_starts_on_cancel_and_a_reversible_one_on_the_action(
    wx_session_app,
) -> None:
    for destructive, expected in ((True, wx.ID_CANCEL), (False, wx.ID_OK)):
        dialog = wdlg.PreviewDialog(
            None, title="T", summary="S", lines=["a"], yes="Go", destructive=destructive
        )
        try:
            assert _default_button(dialog) == expected
        finally:
            dialog.Destroy()


def test_ask_preview_reads_the_running_tier_and_the_irreversible_buttons(
    wx_session_app, monkeypatch
) -> None:
    made: list[bool] = []

    def show(dialog: Any, _label: str) -> int:
        made.append(dialog.destructive)
        return wx.ID_CANCEL

    def ask(yes: str) -> None:
        wdlg.ask_preview(None, show, title="T", summary="S", lines=[], yes=yes)

    ask("Publish")
    ask("Merge")
    wdlg.set_running_tier(Tier.DESTRUCTIVE)
    ask("Copy")
    wdlg.set_running_tier(Tier.WRITE)
    ask("Copy")
    wdlg.set_running_tier(None)
    assert made == [False, True, True, False]


def test_empty_trash_previews_with_cancel_as_the_default(bench, monkeypatch) -> None:
    bench.api.posts.append({**bench.api.posts[0], "id": 9, "status": "trash"})
    shown: list[int] = []

    def show(dialog: Any, _label: str) -> int:
        shown.append(_default_button(dialog))
        return wx.ID_CANCEL

    monkeypatch.setattr(bench.provider, "show_modal", show)
    _go(bench, POSTS)
    bench.provider.run(command("empty_trash"), POSTS, None)
    assert shown == [wx.ID_CANCEL]
    assert bench.api.writes == []


# -- the three chords the key hook ate ---------------------------------------------------


def _chord(code: str, *, ctrl=True, alt=False, shift=False) -> Any:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(ord(code))
    event.SetControlDown(ctrl)
    event.SetAltDown(alt)
    event.SetShiftDown(shift)
    return event


@pytest.mark.parametrize(
    ("verb", "letter", "alt", "shift"),
    [
        ("filter_builder", "F", False, True),
        ("forget_saved", "F", True, True),
        ("roles", "R", True, False),
    ],
)
def test_the_workbench_chords_reach_their_menu_rows(
    bench, monkeypatch, verb, letter, alt, shift
) -> None:
    moved: list[str] = []
    monkeypatch.setattr(bench.filter, "SetFocus", lambda: moved.append("filter"))
    monkeypatch.setattr(bench, "reload", lambda: moved.append("reload"))
    bench.list.SetFocus()
    event = _chord(letter, alt=alt, shift=shift)
    bench._on_char_hook(event)
    assert moved == []  # neither the filter box nor a reload took it
    assert event.GetSkipped()  # on to the menu bar's accelerator
    item = bench._menu_items[command(verb)]
    accel = item.GetAccel()
    assert accel is not None and accel.GetKeyCode() == ord(letter)
