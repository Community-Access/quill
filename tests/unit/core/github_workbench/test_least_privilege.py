"""Least-privilege advice from what QUILL saw, with honest uncertainty (complete.md 1.3).

Recorded answers only: the observed-use record fed by the REST transport and
the write gate, Change History entries, and a token's ``X-OAuth-Scopes``.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError

from quill.core.github.least_privilege import (
    advise,
    classic_needs,
    fine_grained_needs,
    parse_accepted,
    report,
)
from quill.core.github.observed_use import AccountUse, ObservedUseTracker, area_of
from quill.core.github.permissions import AccessLevel

TOKEN = "test-token-not-real"


def _use(*requests: str, refused: dict[str, str] | None = None, **commands: int) -> AccountUse:
    return AccountUse(
        1_760_000_000.0,
        set(requests),
        refused or {},
        {f"github.workbench.{k}": v for k, v in commands.items()},
    )


def test_an_area_names_no_repository_person_or_number() -> None:
    assert area_of("/repos/o/r/issues/5/comments") == "repos/issues"
    assert area_of("/repos/o/r") == "repos"
    assert area_of("/repos/o/r/contents/.github/workflows/ci.yml") == "repos/contents:workflows"
    assert area_of("/repos/o/r/contents/README.md") == "repos/contents"
    assert area_of("/orgs/acme/members") == "orgs/members"
    assert area_of("/user/keys") == "user/keys"
    assert area_of("/gists/abc123") == "gists"
    assert area_of("/notifications?all=true") == "notifications"


def test_the_record_is_kept_per_account_written_only_when_something_new_is_seen(
    tmp_path: Path,
) -> None:
    path = tmp_path / "use.json"
    tracker = ObservedUseTracker(path)
    tracker.observe_reply(TOKEN, "GET", "/repos/o/r/issues", 200, {})
    first = path.stat().st_mtime_ns
    path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    stamp = path.stat().st_mtime_ns
    tracker.observe_reply(TOKEN, "GET", "/repos/o/other/issues/9", 200, {})  # same area
    assert path.stat().st_mtime_ns == stamp >= first
    tracker.observe_reply(
        TOKEN,
        "PATCH",
        "/repos/o/r/issues/9",
        403,
        {"x-accepted-github-permissions": "issues=write"},
    )
    tracker.observe_command(TOKEN, "github.workbench.labels", 0)
    tracker.observe_reply(None, "GET", "/user", 200, {})  # no token, nothing to record
    saved = json.loads(path.read_text(encoding="utf-8"))
    (account,) = saved["accounts"]
    assert account.startswith("token-") and TOKEN not in path.read_text(encoding="utf-8")
    record = saved["accounts"][account]
    assert record["requests"] == ["GET repos/issues"]
    assert record["refused"] == {"PATCH repos/issues": "issues=write"}
    assert record["commands"] == {"github.workbench.labels": 0}
    assert "o/r" not in path.read_text(encoding="utf-8")  # no object is named
    again = ObservedUseTracker(path).use_for(TOKEN)
    assert again.requests == {"GET repos/issues"} and again.since > 0


def test_the_transport_reports_replies_and_refusals(monkeypatch, tmp_path: Path) -> None:
    from quill.core.github import observed_use, rest_transport

    tracker = ObservedUseTracker(tmp_path / "use.json")
    monkeypatch.setattr(observed_use, "OBSERVED_USE", tracker)

    class Reply(io.BytesIO):
        status = 200
        headers = {"X-OAuth-Scopes": "repo"}

        def __enter__(self) -> Reply:
            return self

        def __exit__(self, *_a: object) -> None:
            pass

    class Opener:
        def __init__(self, refuse: bool) -> None:
            self.refuse = refuse

        def open(self, request: Any, timeout: float) -> Any:
            if self.refuse:
                raise HTTPError(
                    request.full_url,
                    403,
                    "Forbidden",
                    {"X-Accepted-GitHub-Permissions": "contents=write"},  # type: ignore[arg-type]
                    io.BytesIO(b'{"message": "Resource not accessible by personal access token"}'),
                )
            return Reply(b"[]")

    rest_transport.request_json(TOKEN, "GET", "/repos/o/r/pulls", opener=Opener(False))
    try:
        rest_transport.request_json(TOKEN, "PUT", "/repos/o/r/contents/a.md", opener=Opener(True))
    except rest_transport.GitHubRestError as exc:
        assert exc.status == 403
    use = tracker.use_for(TOKEN)
    assert use.requests == {"GET repos/pulls"}
    assert use.refused == {"PUT repos/contents": "contents=write"}


def test_classic_needs_say_what_depends_on_a_private_repository() -> None:
    use = _use("GET repos/issues", "PATCH repos/issues", "GET orgs/members", "POST gists")
    needed, private = classic_needs(use)
    assert needed == {"public_repo", "read:org", "gist"}
    assert private == {"repo"}
    workflow = _use("PUT repos/contents:workflows", "DELETE repos")
    assert classic_needs(workflow)[0] >= {"workflow", "delete_repo", "public_repo"}
    gated = _use(dismiss_alert=1, follow=0)  # scope:security_events, scope:user:follow
    assert classic_needs(gated)[0] >= {"security_events", "user:follow"}


def test_fine_grained_needs_use_githubs_names_and_say_what_they_cannot_reach() -> None:
    use = _use("GET repos/issues", "POST repos/issues", "GET repos/contents", "GET notifications",
               "GET widgets/frobs")  # fmt: skip
    fine, unreachable, unnamed = fine_grained_needs(use)
    assert fine == {"Contents": "Read-only", "Issues": "Read and write", "Metadata": "Read-only"}
    assert unreachable == {"the notifications inbox"}
    assert unnamed == ["widgets/frobs"]
    assert parse_accepted("issues=write; pull_requests=read") == [
        "Issues: write",
        "Pull requests: read",
    ]


def test_the_advice_for_a_broad_classic_token_names_what_was_never_used() -> None:
    history = [
        SimpleNamespace(account="jo", kind="issue", tier=1),
        SimpleNamespace(account="someone-else", kind="organization", tier=3),
    ]
    advice = advise(
        login="jo",
        use=_use("GET repos/issues", "PATCH repos/issues", labels=0),
        scopes=("repo", "admin:org", "delete_repo", "workflow"),
        history=history,
        level=AccessLevel.FULL,
    )
    assert advice.classic and advice.seen_changes == 1  # another account's change is not counted
    assert advice.unused == ("admin:org", "delete_repo", "workflow")
    assert advice.smallest_level is AccessLevel.ORGANIZE and advice.highest_tier == 1
    text = report(advice)
    assert "Organize covers it: the most a change needed was tier 1, visible to others." in text
    assert "This account is set to Full." in text
    assert "Never used here: admin:org, delete_repo, workflow." in text
    assert "https://github.com/settings/tokens/new?scopes=public_repo%2Crepo" in text
    assert "Add repo only if a repository you use is private" in text
    assert "It changes nothing." in text


def test_a_broader_scope_than_was_used_is_said_with_the_narrow_one() -> None:
    advice = advise(login="jo", use=_use("GET orgs/members"), scopes=("admin:org",))
    assert advice.narrower == {"admin:org": ("read:org",)}
    assert "admin:org is more than was used: read:org would do." in report(advice)


def test_a_fine_grained_token_is_never_guessed_at() -> None:
    advice = advise(
        login="jo",
        use=_use("GET repos/pulls", refused={"POST repos/pulls": "pull_requests=write"}),
        scopes=None,
    )
    text = report(advice)
    assert not advice.classic and advice.unused == ()
    assert "This token sends no scopes, so it is a fine-grained token or an app's." in text
    assert "Pull requests: Read-only." in text
    assert "POST repos/pulls: it wanted Pull requests: write." in text
    assert "GitHub does not list a fine-grained token's exact permissions" in text
    assert "It saw only this computer's use of this account." in text
    assert "Read Only covers it: nothing QUILL saw changed GitHub." in text


def test_nothing_seen_yet_is_said_and_still_changes_nothing() -> None:
    text = report(advise(login="", use=AccountUse(), scopes=("repo",)))
    assert "Since this session: 0 kinds of request" in text
    assert "Never used here: repo." in text
    assert "What QUILL cannot know" in text
