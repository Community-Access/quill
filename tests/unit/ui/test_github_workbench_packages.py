"""Delete Package Version... and Delete Package... on a package's row (GitHub PRD 14.2)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.packages import package_row
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_packages import GitHubWorkbenchPackagesMixin
from tests.unit.core.github_workbench.test_packages import ENGINE, FakeApi

ROW = package_row(ENGINE)


class _Window(GitHubWorkbenchPackagesMixin):
    signed_in = True

    def __init__(self, *, pick: int = 0, yes: bool = True) -> None:
        self.api, self.pick, self.yes = FakeApi(), pick, yes
        self.said: list[str] = []
        self.asked: list[str] = []
        self.frame = SimpleNamespace(frame=None, reload=lambda: self.said.append("(reloaded)"))

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, _title: str, _prompt: str, labels: list[str]) -> int:
        self.asked.append(" | ".join(labels))
        return self.pick

    def _confirm(self, _title: str, question: str) -> bool:
        self.asked.append(question)
        return self.yes

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_registered_and_fits_only_a_package() -> None:
    assert {"delete_package", "delete_package_version"} <= set(DEVELOPMENT_VERBS)
    window = _Window()
    assert window._fits_delete_package(ROW) and window._fits_delete_package_version(ROW)
    assert not window._fits_delete_package(None)


def test_a_version_is_chosen_newest_first_then_deleted_after_asking() -> None:
    window = _Window(pick=0)
    window._do_delete_package_version(None, ROW)
    assert window.asked[0].startswith("sha256:bbb, tagged latest, 1.2")
    assert "Delete version sha256:bbb" in window.asked[1]
    assert window.api.sent[-1][:2] == (
        "DELETE",
        "/user/packages/container/quill-engine/versions/2",
    )
    assert window.said[-1] == "(reloaded)"


def test_no_at_the_question_deletes_nothing() -> None:
    window = _Window(yes=False)
    window._do_delete_package_version(None, ROW)
    assert not any(method == "DELETE" for method, _p, _q in window.api.sent)


def _typed(monkeypatch: Any, answer: bool) -> list[str]:
    seen: list[str] = []

    class Typed:
        def __init__(self, _parent: Any, **kw: Any) -> None:
            seen.append(kw["expected"])

        def show(self) -> bool:
            return answer

    monkeypatch.setattr("quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", Typed)
    return seen


def test_delete_package_wants_the_typed_name(monkeypatch: Any) -> None:
    seen = _typed(monkeypatch, True)
    window = _Window()
    window._do_delete_package(None, ROW)
    assert seen == ["quill-engine"]
    assert window.said[0] == (
        "Deleted the container package quill-engine. GitHub can restore it for 30 days."
    )
    _typed(monkeypatch, False)
    window = _Window()
    window._do_delete_package(None, ROW)
    assert window.said == ["Cancelled; the package was not deleted."]
    assert not any(method == "DELETE" for method, _p, _q in window.api.sent)
