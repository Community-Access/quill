"""Find a Person or Organization in the Workbench: mixin, Tracked Accounts rows, the window."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.account_desk import AccountDesk
from quill.core.github.account_discovery import KIND_PERSON, AccountHit
from quill.core.github.explore_models import ExploreRow
from quill.core.github.tracked_accounts import TrackedAccounts
from quill.ui.github_workbench_accounts import ACCOUNT_VERBS, GitHubWorkbenchAccountsMixin
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from tests.unit.core.test_github_account_discovery import FakeApi


def test_verbs_are_registered_with_the_workbench() -> None:
    assert set(ACCOUNT_VERBS) <= set(DEVELOPMENT_VERBS)


def test_account_actions_fit_person_and_organization_rows_only_when_signed_in() -> None:
    class Window(GitHubWorkbenchAccountsMixin):
        signed_in = True

    window = Window()
    row = ExploreRow("octocat", "", "", "", "person", "octocat")
    assert window._fits_account_actions(row) and window._fits_find_account(None)
    window.signed_in = False
    assert not window._fits_account_actions(row) and not window._fits_find_account(None)


def test_tracked_accounts_rows_put_favorites_first_and_say_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import github_workbench_loaders as loaders

    store = _fresh(tmp_path)
    real = TrackedAccounts.load
    monkeypatch.setattr(
        TrackedAccounts,
        "load",
        classmethod(lambda cls, key, data_dir=None: real("acct", data_dir=tmp_path)),
    )
    store.track(AccountHit("zed", KIND_PERSON))
    store.set_favorite(AccountHit("octo-org", "organization"), True)
    store.set_favorite_repository("o/r", True)
    rows = loaders._tracked_rows(SimpleNamespace(token="t"))
    assert [r.kind for r in rows] == ["org", "person", "repo"]
    assert rows[0].label.startswith("Favorite organization: octo-org")
    assert all("GitHub" in r.detail for r in rows)
    assert "not a GitHub star" in rows[2].detail


def _fresh(tmp_path: Path) -> TrackedAccounts:
    return TrackedAccounts.load("acct", data_dir=tmp_path)


def test_window_types_ahead_and_drops_stale_answers(wx_session_app: Any, tmp_path: Path) -> None:
    from quill.ui.github_find_account_dialog import FindAccountDialog

    said: list[str] = []
    pending: list[Any] = []

    def background(_name: str, work: Any, done: Any) -> None:
        pending.append((work, done))

    desk = AccountDesk(FakeApi(), _fresh(tmp_path), refuse=lambda _w: "")
    window = FindAccountDialog(
        None,
        desk,
        say=said.append,
        background=background,
        open_url=lambda url: said.append(f"open {url}"),
        add_to_list=lambda repo: said.append(f"list {repo}"),
    )
    try:
        window.query.ChangeValue("octo")
        window.search_now()
        window.query.ChangeValue("octoc")
        window.search_now()
        (work1, done1), (work2, done2) = pending
        done2(work2())  # the newer answer
        done1(work1())  # the older one arrives late and must not replace it
        assert window.list.GetCount() == 3 and said == ["3 matches."]
        window.list.SetSelection(0)
        window.toggle_track()
        window.toggle_favorite()
        assert desk.store.is_tracked("octocat") and desk.store.is_favorite("octocat")
        assert said[-1].endswith("GitHub is not told.")
        window.list.SetSelection(1)  # the organization
        window.toggle_follow()
        assert "Open on GitHub" in said[-2] and said[-1].endswith("octo-org")
        window.list.SetSelection(0)
        window.toggle_follow()
        work, done = pending[-1]
        done(work())
        assert said[-1] == "You now follow octocat."
    finally:
        window.dialog.Destroy()
