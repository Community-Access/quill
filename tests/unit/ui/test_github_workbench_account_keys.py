"""New Here in My Keys, and Delete Key... (GitHub PRD 14.3)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.account_keys import fetch_keys
from quill.ui.github_workbench_account_keys import GitHubWorkbenchAccountKeysMixin
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from tests.unit.core.github_workbench.test_account_keys import PRINT, PUB, FakeApi


class _Window(GitHubWorkbenchAccountKeysMixin):
    signed_in = True

    def __init__(self, picks: list[int], texts: list[str], yes: bool = True) -> None:
        self.api, self.picks, self.texts, self.yes = FakeApi(), list(picks), list(texts), yes
        self.said: list[str] = []
        self.asked: list[str] = []
        self.frame = SimpleNamespace(
            frame=None,
            current=SimpleNamespace(key="my_keys"),
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
        return self.yes

    def _ask_text(self, *_a: Any, **kw: Any) -> str:
        answer = self.texts.pop(0)
        return kw.get("value", "") if answer == "(keep)" else answer

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_registered_and_where_each_fits() -> None:
    assert {"new_key", "delete_key"} <= set(DEVELOPMENT_VERBS)
    window = _Window([], [])
    rows = fetch_keys(FakeApi())
    assert window._fits_new_key(None) and window._fits_delete_key(rows[0])


def test_a_pasted_key_keeps_its_comment_as_the_suggested_name() -> None:
    window = _Window([0, 1], [PUB, "(keep)"])
    window._do_new_key(None, None)
    assert window.api.sent[-1] == ("POST", "/user/keys", {"title": "jeff@laptop", "key": PUB})
    assert window.said[0] == f"Added SSH key jeff@laptop, {PRINT}."


def test_a_key_read_from_a_file(monkeypatch: Any, tmp_path: Any) -> None:
    key = tmp_path / "id_ed25519.pub"
    key.write_text(PUB, encoding="utf-8")
    window = _Window([1, 0], ["Signing"])
    monkeypatch.setattr(window, "_read_key_file", lambda _kind: key.read_text(encoding="utf-8"))
    window._do_new_key(None, None)
    assert window.api.sent[-1][1] == "/user/ssh_signing_keys"


def test_delete_says_what_stops_working_first() -> None:
    rows = fetch_keys(FakeApi())
    window = _Window([], [], yes=False)
    window._do_delete_key(None, rows[0])
    assert "can no longer push or pull over SSH" in window.asked[0]
    assert not any(method == "DELETE" for method, _p, _b in window.api.sent)
    window = _Window([], [])
    window._do_delete_key(None, rows[1])
    assert window.api.sent[-1][:2] == ("DELETE", "/user/gpg_keys/2")
