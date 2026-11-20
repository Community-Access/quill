"""Why Can't I Merge? names the rule, Watch Readiness, and Check Download... (GX09, GX10)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import asset_digest as ad
from quill.core.github import merge_readiness as mr
from quill.core.github.item_actions import GITHUB_ACTIONS
from quill.core.github.items_provider import GitHubItem, GitHubReleaseAsset
from quill.core.github.watches import READY, WatchStore
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS
from quill.ui.github_workbench_development import DEVELOPMENT_REASONS, DEVELOPMENT_VERBS
from quill.ui.github_workbench_evidence import GitHubWorkbenchEvidenceMixin
from quill.ui.github_workbench_merge import GitHubWorkbenchMergeMixin

PULL = GitHubItem(number=4, title="Add it", state="open", url="u", is_pr=True)
REF = SimpleNamespace(instance="o/r")
ASSET = GitHubReleaseAsset(
    name="app.zip",
    download_count=0,
    size_bytes=1,
    browser_download_url="https://github.com/o/r/releases/download/v1/app.zip",
)


class _Window(GitHubWorkbenchMergeMixin, GitHubWorkbenchEvidenceMixin):
    signed_in = True

    def __init__(self) -> None:
        self.said: list[str] = []
        self.shown: list[tuple[str, str]] = []
        self.items = SimpleNamespace(token=None)
        self.frame = SimpleNamespace(current=SimpleNamespace(instance="o/r"))
        self.picked: Path | None = None

    def github_api(self) -> Any:
        return "API"

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _show_text(self, title: str, text: str) -> None:
        self.shown.append((title, text))

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())

    def _pick_download(self, name: str) -> Path | None:
        return self.picked


def test_the_new_rows_are_registered_with_their_needs() -> None:
    for verb in ("watch_readiness", "check_download"):
        assert verb in DEVELOPMENT_VERBS and verb in DEVELOPMENT_REASONS
    assert COMMAND_REQUIREMENTS["github.workbench.watch_readiness"][0] == "local"
    pulls = [row.command_id for row in GITHUB_ACTIONS.rows_for("pull_request")]
    assets = [row.command_id for row in GITHUB_ACTIONS.rows_for("release_asset")]
    assert "github.workbench.watch_readiness" in pulls
    assert "github.workbench.check_download" in assets


def test_why_cant_merge_asks_for_the_rules_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[dict[str, Any]] = []
    named = mr.Readiness(
        number=4,
        head="abc1234def",
        base="main",
        merge_state="BLOCKED",
        rules=mr.NamedRules(blockers=('The ruleset "Protect main" requires signed commits.',)),
    )
    monkeypatch.setattr(
        mr, "load_readiness", lambda api, repo, number, **kw: (asked.append(kw), named)[1]
    )
    window = _Window()
    window._do_why_cant_merge(REF, PULL)
    assert asked == [{"named": True}]
    assert window.said == [
        '#4 cannot merge yet, as of commit abc1234. The ruleset "Protect main" requires '
        "signed commits."
    ]


def test_watch_readiness_adds_one_watch_and_not_a_second(quill_data_dir: Path) -> None:
    window = _Window()
    assert window._fits_watch_readiness(PULL)
    window._do_watch_readiness(REF, PULL)
    assert window.said == [
        "Watching: Whether pull request o/r#4 can merge. QUILL says once when it becomes able "
        "to merge, and once when it stops."
    ]
    from quill.core.github.navigation_state import account_key_for_token

    watches = WatchStore.load(account_key_for_token(None)).watches
    assert [(w.kind, w.repository, w.number) for w in watches] == [(READY, "o/r", 4)]
    window._do_watch_readiness(REF, PULL)
    assert window.said[-1].startswith("Already watching: Whether pull request o/r#4 can merge.")
    assert len(WatchStore.load(account_key_for_token(None)).watches) == 1
    window.signed_in = False
    assert not window._fits_watch_readiness(PULL)


def test_check_download_says_whether_it_matched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = b"the release file"
    good = "sha256:" + hashlib.sha256(body).hexdigest()
    asked: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        ad, "asset_digest", lambda api, repo, tag, name: (asked.append((repo, tag, name)), good)[1]
    )
    window = _Window()
    assert window._fits_check_download(ASSET)
    window._do_check_download(REF, ASSET)  # cancelled in the Open box: nothing read
    assert asked == [] and window.said == []
    window.picked = tmp_path / "app.zip"
    window.picked.write_bytes(body)
    window._do_check_download(REF, ASSET)
    assert asked == [("o/r", "v1", "app.zip")]
    assert window.said[-1].startswith("app.zip matches app.zip: its SHA-256 is the digest")
    assert window.shown[-1][0] == "Check Download: app.zip"
    window.picked.write_bytes(body + b"!")
    window._do_check_download(REF, ASSET)
    assert "does not match app.zip" in window.said[-1]


def test_check_download_without_a_digest_says_so(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ad, "asset_digest", lambda api, repo, tag, name: "")
    window = _Window()
    window.picked = tmp_path / "app.zip"
    window.picked.write_bytes(b"x")
    window._do_check_download(REF, ASSET)
    assert window.said == [
        "GitHub has no digest for app.zip, so app.zip cannot be checked. Files uploaded before "
        "GitHub kept digests have none."
    ]
    assert window.shown == []
