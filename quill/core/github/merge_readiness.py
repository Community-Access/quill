"""Why a pull request can or cannot merge, for one exact commit (GH-MR).

GitHub's merge box answers "can this merge?" with a colour and a few icons.
:func:`load_readiness` asks GitHub the same questions in one GraphQL read --
the pull request's state, draft, ``mergeable`` and ``mergeStateStatus``, its
review decision, every check on the head commit with whether it is required,
auto-merge and the merge queue -- and :class:`Readiness` says the answer in
words: either that it can merge, or each reason it cannot, each with what to
do about it.

The answer is for **one commit**, the head GitHub reported, and says which.
:func:`merge_at` merges only that commit (REST ``sha``): if somebody pushes in
between, GitHub refuses with 409 and nothing is merged, so what was checked is
what goes in.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = ["Check", "MergeReadinessError", "Readiness", "load_readiness", "merge_at"]


class MergeReadinessError(CodedError):
    """Readiness could not be read, or the merge was refused; the message is said."""

    code = "QUILL-GITHUB-MERGE-READINESS"


_QUERY = """
query($o: String!, $n: String!, $i: Int!) {
  repository(owner: $o, name: $n) {
    pullRequest(number: $i) {
      state isDraft mergeable mergeStateStatus reviewDecision
      headRefOid baseRefName headRefName viewerCanMergeAsAdmin
      autoMergeRequest { mergeMethod enabledBy { login } }
      mergeQueueEntry { position state }
      commits(last: 1) { nodes { commit { statusCheckRollup { contexts(first: 100) { nodes {
        __typename
        ... on CheckRun { name status conclusion isRequired(pullRequestNumber: $i) }
        ... on StatusContext { context state isRequired(pullRequestNumber: $i) }
      } } } } } }
    }
  }
}
"""

#: A check run's conclusion, or a status's state, that passes.
_PASSING = {"SUCCESS", "NEUTRAL", "SKIPPED"}
_FAILING = {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}


@dataclass(frozen=True)
class Check:
    name: str
    state: str
    """``passed``, ``failed`` or ``pending``."""
    required: bool


def _check(node: Mapping[str, Any]) -> Check:
    if node.get("__typename") == "StatusContext":
        raw = str(node.get("state") or "").upper()
        name = str(node.get("context") or "")
        done = raw not in {"PENDING", "EXPECTED"}
    else:
        raw = str(node.get("conclusion") or "").upper()
        name = str(node.get("name") or "")
        done = str(node.get("status") or "").upper() == "COMPLETED"
    if not done:
        state = "pending"
    elif raw in _PASSING:
        state = "passed"
    elif raw in _FAILING:
        state = "failed"
    else:
        state = "pending"
    return Check(name, state, bool(node.get("isRequired")))


@dataclass(frozen=True)
class Readiness:
    number: int
    head: str
    base: str
    state: str = "OPEN"
    draft: bool = False
    mergeable: str = "UNKNOWN"
    merge_state: str = "UNKNOWN"
    review: str = ""
    checks: tuple[Check, ...] = field(default_factory=tuple)
    auto_merge: str = ""
    queue_position: int | None = None
    admin_can_merge: bool = False

    @property
    def short_head(self) -> str:
        return self.head[:7]

    def _required(self, state: str) -> list[str]:
        return [c.name for c in self.checks if c.required and c.state == state]

    @property
    def reasons(self) -> tuple[str, ...]:
        """Each reason it cannot merge now, with what to do; empty when it can."""
        if self.state == "MERGED":
            return (f"#{self.number} is already merged.",)
        if self.state == "CLOSED":
            return (f"#{self.number} is closed. Reopen it first.",)
        found: list[str] = []
        if self.draft:
            found.append("It is a draft. Mark it ready for review first.")
        if self.mergeable == "CONFLICTING" or self.merge_state == "DIRTY":
            found.append(
                f"It conflicts with {self.base}. Resolve Conflicts in a Worktree... "
                "takes the conflicts to your computer."
            )
        if self.merge_state == "BEHIND":
            found.append(
                f"It is behind {self.base}, and the branch's rules want it up to date. "
                "Update the branch first."
            )
        if self.review == "CHANGES_REQUESTED":
            found.append("A reviewer requested changes. Their review has to be answered first.")
        elif self.review == "REVIEW_REQUIRED":
            found.append("It needs an approving review.")
        failed, pending = self._required("failed"), self._required("pending")
        if failed:
            found.append(_listed("Required check", failed, "failed") + ". Re-run or fix it.")
        if pending:
            found.append(_listed("Required check", pending, "has not finished") + ".")
        if self.merge_state == "BLOCKED" and not found:
            found.append(f"A rule on {self.base} blocks it. Check Merge Policy names the rules.")
        if self.merge_state == "UNKNOWN" and not found:
            found.append("GitHub is still working out whether it can merge. Ask again shortly.")
        return tuple(found)

    @property
    def can_merge(self) -> bool:
        return not self.reasons

    @property
    def sentence(self) -> str:
        at = f"as of commit {self.short_head}" if self.head else "as GitHub has it now"
        if self.can_merge:
            said = f"#{self.number} can merge into {self.base}, {at}."
            others = [c.name for c in self.checks if not c.required and c.state == "failed"]
            if others:
                not_required = "it is not" if len(others) == 1 else "they are not"
                said += " " + _listed("Check", others, "failed") + f", but {not_required} required."
        else:
            said = f"#{self.number} cannot merge yet, {at}. " + " ".join(self.reasons)
        if self.auto_merge:
            said += f" Auto-merge is on, to {self.auto_merge.casefold()} it when it can."
        if self.queue_position is not None:
            said += f" It is in the merge queue, at position {self.queue_position}."
        return said


def _listed(noun: str, names: list[str], verb: str) -> str:
    if len(names) == 1:
        return f"{noun} {names[0]} {verb}"
    verb_many = {"has not finished": "have not finished"}.get(verb, verb)
    return f"{noun}s {', '.join(names[:-1])} and {names[-1]} {verb_many}"


def load_readiness(api: GitHubApi, repository: str, number: int) -> Readiness:
    owner, _slash, name = repository.partition("/")
    data = api.graphql(_QUERY, {"o": owner, "n": name, "i": int(number)})
    pull = ((data or {}).get("repository") or {}).get("pullRequest")
    if not isinstance(pull, Mapping):
        raise MergeReadinessError(f"{repository} has no pull request #{number}.")
    commits = (pull.get("commits") or {}).get("nodes") or []
    rollup = ((commits[-1] or {}).get("commit") or {}).get("statusCheckRollup") if commits else {}
    nodes = ((rollup or {}).get("contexts") or {}).get("nodes") or []
    auto = pull.get("autoMergeRequest") or {}
    queue = pull.get("mergeQueueEntry") or {}
    position = queue.get("position") if isinstance(queue, Mapping) else None
    return Readiness(
        number=int(number),
        head=str(pull.get("headRefOid") or ""),
        base=str(pull.get("baseRefName") or ""),
        state=str(pull.get("state") or "OPEN"),
        draft=bool(pull.get("isDraft")),
        mergeable=str(pull.get("mergeable") or "UNKNOWN"),
        merge_state=str(pull.get("mergeStateStatus") or "UNKNOWN"),
        review=str(pull.get("reviewDecision") or ""),
        checks=tuple(_check(node) for node in nodes if isinstance(node, Mapping)),
        auto_merge=str(auto.get("mergeMethod") or "") if isinstance(auto, Mapping) else "",
        queue_position=int(position) if isinstance(position, int) else None,
        admin_can_merge=bool(pull.get("viewerCanMergeAsAdmin")),
    )


def merge_at(api: GitHubApi, repository: str, number: int, method: str, head: str) -> str:
    """Merge #*number* only if its head is still *head*; returns the merge commit's SHA."""
    from quill.core.github.rest_transport import GitHubRestError

    if method not in ("merge", "squash", "rebase"):
        raise MergeReadinessError(f"Unknown merge method {method!r}.")
    body: dict[str, object] = {"merge_method": method}
    if head:
        body["sha"] = head
    try:
        data = api.rest("PUT", f"/repos/{repository}/pulls/{int(number)}/merge", body=body).data
    except GitHubRestError as exc:
        if exc.status == 409:
            raise MergeReadinessError(
                f"Somebody pushed to #{number} after commit {head[:7]} was checked, so "
                "nothing was merged. Check again, and merge what you have read."
            ) from exc
        if exc.status == 405:
            said = str((exc.data or {}).get("message") or "") if isinstance(exc.data, dict) else ""
            raise MergeReadinessError(
                f"GitHub will not merge #{number}: {said or 'it is not mergeable'}."
            ) from exc
        raise
    sha = str((data or {}).get("sha") or "") if isinstance(data, Mapping) else ""
    if not sha:
        raise MergeReadinessError(f"GitHub did not confirm #{number} merged.")
    return sha
