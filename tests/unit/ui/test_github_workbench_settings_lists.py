"""What a webhook, deploy key or autolink row can do (GitHub PRD 14.3)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github import repo_settings_lists as sl
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_settings_lists import (
    SETTINGS_LIST_VERBS,
    GitHubWorkbenchSettingsListsMixin,
)
from tests.unit.core.github_workbench.test_account_keys import PUB
from tests.unit.core.github_workbench.test_repo_settings_lists import FakeApi

REF = SimpleNamespace(instance="o/r")


class _Window(GitHubWorkbenchSettingsListsMixin):
    signed_in = True

    def __init__(
        self, node: str, picks: list[int], texts: list[str], secret: str | None = ""
    ) -> None:
        self.api, self.picks, self.texts, self.secret_answer = (
            FakeApi(),
            list(picks),
            list(texts),
            secret,
        )
        self.said: list[str] = []
        self.asked: list[str] = []
        self.frame = SimpleNamespace(
            frame=None,
            current=SimpleNamespace(key=node),
            reload=lambda: self.said.append("(reloaded)"),
        )

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, *_a: Any) -> int:
        return self.picks.pop(0)

    def _confirm(self, _title: str, question: str) -> bool:
        self.asked.append(question)
        return True

    def _ask_text(self, *_a: Any, **kw: Any) -> str:
        answer = self.texts.pop(0)
        return kw.get("value", "") if answer == "(keep)" else answer

    def _secret(self, *_a: Any) -> str | None:
        return self.secret_answer

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_every_verb_is_registered() -> None:
    assert set(SETTINGS_LIST_VERBS) <= set(DEVELOPMENT_VERBS)


def test_a_new_webhook_for_push_only_with_a_secret() -> None:
    window = _Window("webhooks", [0, 0], ["https://ci.example.org/hook"], secret="s3cret")
    assert window._fits_new_webhook(None)
    window._do_new_webhook(REF, None)
    body = window.api.sent[-1][2]
    assert body["events"] == ["push"] and body["config"]["secret"] == "s3cret"
    assert all("s3cret" not in said for said in window.said)


def test_cancel_at_the_secret_sends_nothing() -> None:
    window = _Window("webhooks", [0, 1], ["https://ci.example.org/hook"], secret=None)
    window._do_new_webhook(REF, None)
    assert window.api.sent == []


def test_recent_deliveries_then_redeliver_the_one_chosen() -> None:
    hook = sl.fetch_webhooks(FakeApi(), "o/r")[0]
    window = _Window("webhooks", [1], [])
    window._do_webhook_deliveries(REF, hook)
    assert "pull_request opened" in window.asked[0]
    assert window.api.sent[-1][1] == "/repos/o/r/hooks/9/deliveries/4/attempts"


def test_change_keeps_an_unchanged_address_and_only_sends_the_secret() -> None:
    hook = sl.fetch_webhooks(FakeApi(), "o/r")[0]
    window = _Window("webhooks", [], ["(keep)"], secret="new")
    window._do_change_webhook(REF, hook)
    assert window.api.sent[-1] == ("PATCH", "/repos/o/r/hooks/9/config", {"secret": "new"})


def test_a_pasted_deploy_key_read_only_and_a_new_autolink() -> None:
    window = _Window("deploy_keys", [1, 0], [PUB, "CI"])
    window._do_new_deploy_key(REF, None)
    assert window.api.sent[-1][2]["read_only"] is True
    window = _Window("autolinks", [0], ["TICKET-", "https://jira.example.org/browse/TICKET-<num>"])
    window._do_new_autolink(REF, None)
    assert window.api.sent[-1][2]["is_alphanumeric"] is False


def test_deletes_ask_first() -> None:
    api = FakeApi()
    rows = (
        sl.fetch_webhooks(api, "o/r")[0],
        sl.fetch_deploy_keys(api, "o/r")[0],
        sl.fetch_autolinks(api, "o/r")[0],
    )
    window = _Window("webhooks", [], [])
    window._do_delete_webhook(REF, rows[0])
    window._do_delete_deploy_key(REF, rows[1])
    window._do_delete_autolink(REF, rows[2])
    assert len(window.asked) == 3
    assert [p for m, p, _b in window.api.sent if m == "DELETE"] == [
        "/repos/o/r/hooks/9",
        "/repos/o/r/keys/3",
        "/repos/o/r/autolinks/7",
    ]
