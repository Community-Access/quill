"""Why a pull request can or cannot merge, for one exact commit (GH-MR).

GitHub's merge box answers "can this merge?" with a colour and a few icons.
:func:`load_readiness` asks GitHub the same questions in one GraphQL read --
the pull request's state, draft, ``mergeable`` and ``mergeStateStatus``, its
review decision, every check on the head commit with whether it is required,
auto-merge and the merge queue -- and :class:`Readiness` says the answer in
words: either that it can merge, or each reason it cannot, each with what to
do about it.

With ``named=True`` (Why Can't I Merge?, Merge Selected... and Watch
Readiness) a pull request that cannot merge also has its blocking rules named
by :func:`quill.core.github.merge_rules.name_blockers`: which ruleset or
branch protection wants which check, how many approving reviews, which
CODEOWNERS line's owners have not approved, and which rule makes the branch
merge only through a queue. Naming never changes GitHub's answer; it only
says it more exactly.

The answer is for **one commit**, the head GitHub reported, and says which.
:func:`merge_at` merges only that commit (REST ``sha``): if somebody pushes in
between, GitHub refuses with 409 and nothing is merged, so what was checked is
what goes in.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "Check",
    "MergeReadinessError",
    "NamedRules",
    "Readiness",
    "load_readiness",
    "merge_at",
]


class MergeReadinessError(CodedError):
    """Readiness could not be read, or the merge was refused; the message is said."""

    code = "QUILL-GITHUB-MERGE-READINESS"


_QUERY = """
query($o: String!, $n: String!, $i: Int!) {
  repository(owner: $o, name: $n) {
    mergeCommitAllowed squashMergeAllowed rebaseMergeAllowed
    pullRequest(number: $i) {
      state isDraft mergeable mergeStateStatus reviewDecision isMergeQueueEnabled
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
class NamedRules:
    """The rules that block a pull request, by name (:mod:`quill.core.github.merge_rules`)."""

    blockers: tuple[str, ...] = ()
    """One sentence per blocking rule, each naming the ruleset or protection it is from."""
    checks: frozenset[str] = frozenset()
    """The required checks a blocker already names, so they are not said twice."""
    reviews: bool = False
    """Whether a blocker names the reviews it is waiting for."""
    queue_rule: str = ""
    """The rule that makes the base branch merge only through its queue, in words."""
    unread: tuple[str, ...] = ()
    """What QUILL could not read, so a rule there may be unnamed."""


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
    queue_required: bool = False
    """The base branch has a merge queue, so the pull request joins it rather than merging."""
    methods: tuple[str, ...] = ()
    """The REST merge methods the repository allows (``squash``, ``merge``, ``rebase``);
    empty when GitHub did not say, and then all three are offered."""
    rules: NamedRules | None = None
    """The blocking rules by name, when they were asked for (``named=True``)."""

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
        named = self.rules or NamedRules()
        if self.review == "CHANGES_REQUESTED":
            found.append("A reviewer requested changes. Their review has to be answered first.")
        elif self.review == "REVIEW_REQUIRED" and not named.reviews:
            found.append("It needs an approving review.")
        failed = [name for name in self._required("failed") if name not in named.checks]
        pending = [name for name in self._required("pending") if name not in named.checks]
        if failed:
            found.append(_listed("Required check", failed, "failed") + ". Re-run or fix it.")
        if pending:
            found.append(_listed("Required check", pending, "has not finished") + ".")
        found.extend(named.blockers)
        if self.merge_state == "BLOCKED" and not found and not self.queue_required:
            found.append(
                f"A rule on {self.base} blocks it. Check Merge Policy names the rules."
                if self.rules is None
                else f"A rule on {self.base} blocks it, and GitHub's list of the branch's "
                "rules does not say which. The pull request's page on GitHub does."
            )
        if self.merge_state == "UNKNOWN" and not found:
            found.append("GitHub is still working out whether it can merge. Ask again shortly.")
        return tuple(found)

    @property
    def allowed_methods(self) -> tuple[str, ...]:
        """What the repository allows, best first; all three when GitHub did not say."""
        return self.methods or ("squash", "merge", "rebase")

    @property
    def can_merge(self) -> bool:
        return not self.reasons

    @property
    def sentence(self) -> str:
        at = f"as of commit {self.short_head}" if self.head else "as GitHub has it now"
        if self.can_merge and self.queue_required:
            by = f", by {self.rules.queue_rule}" if self.rules and self.rules.queue_rule else ""
            said = (
                f"#{self.number} can join the merge queue for {self.base}, {at}; "
                f"{self.base} merges only through its queue{by}."
            )
        elif self.can_merge:
            said = f"#{self.number} can merge into {self.base}, {at}."
            others = [c.name for c in self.checks if not c.required and c.state == "failed"]
            if others:
                not_required = "it is not" if len(others) == 1 else "they are not"
                said += " " + _listed("Check", others, "failed") + f", but {not_required} required."
        else:
            said = f"#{self.number} cannot merge yet, {at}. " + " ".join(self.reasons)
            if self.rules and self.rules.unread:
                said += (
                    f" QUILL could not read {_and(list(self.rules.unread))}, "
                    "so a rule there may not be named."
                )
        if self.auto_merge:
            said += f" Auto-merge is on, to {self.auto_merge.casefold()} it when it can."
        if self.queue_position is not None:
            said += f" It is in the merge queue, at position {self.queue_position}."
        return said


def _and(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _listed(noun: str, names: list[str], verb: str) -> str:
    if len(names) == 1:
        return f"{noun} {names[0]} {verb}"
    verb_many = {"has not finished": "have not finished"}.get(verb, verb)
    return f"{noun}s {_and(names)} {verb_many}"


def load_readiness(
    api: GitHubApi, repository: str, number: int, *, named: bool = False
) -> Readiness:
    """GitHub's answer for #*number* now; with *named*, its blocking rules by name too.

    Rules are read only when they can add something: the pull request is open
    and cannot merge, or merges only through a queue.
    """
    ready = _load(api, repository, number)
    if not named or ready.state != "OPEN" or (ready.can_merge and not ready.queue_required):
        return ready
    from quill.core.github.merge_rules import name_blockers

    try:
        rules = name_blockers(api, repository, ready)
    except Exception:  # noqa: BLE001 - naming is extra; GitHub's own answer still stands
        rules = NamedRules(unread=(f"the rules on {ready.base}",))
    return replace(ready, rules=rules)


def _load(api: GitHubApi, repository: str, number: int) -> Readiness:
    owner, _slash, name = repository.partition("/")
    data = api.graphql(_QUERY, {"o": owner, "n": name, "i": int(number)})
    pull = ((data or {}).get("repository") or {}).get("pullRequest")
    if not isinstance(pull, Mapping):
        raise MergeReadinessError(f"{repository} has no pull request #{number}.")
    commits = (pull.get("commits") or {}).get("nodes") or []
    rollup = ((commits[-1] or {}).get("commit") or {}).get("statusCheckRollup") if commits else {}
    nodes = ((rollup or {}).get("contexts") or {}).get("nodes") or []
    repo = (data or {}).get("repository") or {}
    allowed = tuple(
        method
        for method, key in (
            ("squash", "squashMergeAllowed"),
            ("merge", "mergeCommitAllowed"),
            ("rebase", "rebaseMergeAllowed"),
        )
        if repo.get(key)
    )
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
        queue_required=bool(pull.get("isMergeQueueEnabled")),
        methods=allowed,
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
