"""Access Templates and Apply Access Template in the Workbench window (GH-R-068).

The real provider over a recorded API: the command goes through the one
dispatcher (and so the write gate), the batch is previewed once in words, and
each change reports a result and is recorded in Change History.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.change_log import ChangeLog  # noqa: E402
from quill.core.github.permissions import AccessLevel  # noqa: E402
from quill.ui.github_workbench_access_templates import _templates_for  # noqa: E402
from tests.unit.ui import test_github_workbench_tools as _tools  # noqa: E402

bench = _tools.bench  # the window over a recorded API, shared with the tools tests

_P = "github.workbench."


def _make(provider: Any) -> None:
    store = _templates_for(provider.items)
    store.set_template("Contributor", "write on owner/repo\nmember of owner/docs")
    store.save()


def test_applying_a_template_previews_once_sends_each_and_records_each(bench, monkeypatch) -> None:
    provider = bench.provider
    _make(provider)
    previews: list[tuple[Any, str]] = []
    monkeypatch.setattr(provider, "_choose", lambda title, prompt, labels: 0)
    monkeypatch.setattr(provider, "_ask_text", lambda *a, **k: "@kelly")
    monkeypatch.setattr(
        provider, "confirm_tier", lambda tier, words, name: previews.append((tier, words)) or True
    )

    assert provider.run(f"{_P}apply_access_template", bench.current, None)

    assert len(previews) == 1
    assert previews[0][1].splitlines() == [
        "Add kelly to the team docs as a member.",
        "Invite kelly to owner/repo with write access. GitHub sends them an invitation.",
    ]
    assert provider.api.writes()[-2:] == [
        ("PUT", "/orgs/owner/teams/docs/memberships/kelly", {"role": "member"}),
        ("PUT", "/repos/owner/repo/collaborators/kelly", {"permission": "push"}),
    ]
    assert bench.said[-1] == "2 done, 0 failed."
    assert [e.summary for e in ChangeLog.load().entries[-2:]] == previews[0][1].splitlines()


def test_declining_the_preview_sends_nothing(bench, monkeypatch) -> None:
    provider = bench.provider
    _make(provider)
    monkeypatch.setattr(provider, "_choose", lambda title, prompt, labels: 0)
    monkeypatch.setattr(provider, "_ask_text", lambda *a, **k: "kelly")
    monkeypatch.setattr(provider, "confirm_tier", lambda *a: False)
    provider.run(f"{_P}apply_access_template", bench.current, None)
    assert provider.api.writes() == []


def test_read_only_refuses_before_anything_is_asked(bench, monkeypatch) -> None:
    provider = bench.provider
    _make(provider)
    monkeypatch.setattr(provider, "access_level", lambda: AccessLevel.READ_ONLY)
    monkeypatch.setattr(provider, "_choose", lambda *a: pytest.fail("asked at Read Only"))
    provider.run(f"{_P}apply_access_template", bench.current, None)
    assert provider.api.writes() == []
    assert "this account is Read Only" in bench.said[-1]


def test_with_no_templates_apply_says_where_to_make_one(bench, monkeypatch) -> None:
    provider = bench.provider
    monkeypatch.setattr(provider, "_choose", lambda *a: pytest.fail("nothing to choose"))
    provider.run(f"{_P}apply_access_template", bench.current, None)
    assert bench.said[-1] == "There are no access templates yet. Access Templates... makes one."


def test_access_templates_makes_renames_and_deletes_without_sending(bench, monkeypatch) -> None:
    provider = bench.provider
    choices = iter([0, 1, 1, 1, 2])  # New; then the template, Rename; then it, Delete
    answers = iter(["Contributor", "write on owner/repo; push on owner/repo", "Writer"])
    monkeypatch.setattr(provider, "_choose", lambda *a: next(choices))
    monkeypatch.setattr(provider, "_ask_text", lambda *a, **k: next(answers))
    monkeypatch.setattr(provider, "_confirm", lambda *a: True)

    provider.run(f"{_P}access_templates", bench.current, None)
    assert bench.said[-1] == (
        "Saved Contributor: 1 place. Left out, not understood: push on owner/repo."
    )
    provider.run(f"{_P}access_templates", bench.current, None)
    assert _templates_for(provider.items).names() == ["Writer"]
    provider.run(f"{_P}access_templates", bench.current, None)
    assert bench.said[-1] == "Deleted Writer. Nobody's access changed."
    assert _templates_for(provider.items).names() == []
    assert provider.api.writes() == []
