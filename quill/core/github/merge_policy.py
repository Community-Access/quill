"""Read-only merge-policy context for one pull request's base branch."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any

_MAX_RULESET_PAGES = 3
_MAX_RULESET_DETAILS = 50
_MAX_CODEOWNERS_BYTES = 100_000


@dataclass(frozen=True, slots=True)
class GitHubPullQueueState:
    """GraphQL status for the selected pull request and its current head SHA."""

    merge_queue_enabled: bool | None
    in_merge_queue: bool | None
    auto_merge_enabled: bool | None
    head_sha: str = ""


@dataclass(frozen=True, slots=True)
class GitHubRuleSetPolicy:
    """Bounded summary of one branch ruleset applicable to the target branch."""

    ruleset_id: int
    name: str
    enforcement: str
    rule_types: tuple[str, ...] = ()
    required_checks: tuple[str, ...] = ()
    required_approvals: int | None = None
    codeowners_review_required: bool | None = None
    merge_queue_required: bool = False


@dataclass(frozen=True, slots=True)
class GitHubMergePolicy:
    """Observed branch protection and ruleset requirements, with completeness."""

    base_branch: str
    branch_protection_available: bool
    branch_protection_enabled: bool | None
    required_approvals: int | None = None
    required_checks: tuple[str, ...] = ()
    strict_checks: bool | None = None
    codeowners_review_required: bool | None = None
    conversation_resolution_required: bool | None = None
    rulesets: tuple[GitHubRuleSetPolicy, ...] = ()
    rulesets_complete: bool = True
    codeowners_path: str = ""
    codeowners_available: bool = True
    warnings: tuple[str, ...] = ()

    @property
    def active_rulesets(self) -> tuple[GitHubRuleSetPolicy, ...]:
        return tuple(rule for rule in self.rulesets if rule.enforcement == "active")

    @property
    def active_required_checks(self) -> tuple[str, ...]:
        values = list(self.required_checks)
        for ruleset in self.active_rulesets:
            values.extend(ruleset.required_checks)
        return tuple(dict.fromkeys(values))

    @property
    def active_required_approvals(self) -> int:
        values = [self.required_approvals or 0]
        values.extend(
            ruleset.required_approvals or 0
            for ruleset in self.active_rulesets
            if ruleset.required_approvals is not None
        )
        return max(values)

    @property
    def active_codeowners_required(self) -> bool:
        if self.codeowners_review_required:
            return True
        return any(ruleset.codeowners_review_required is True for ruleset in self.active_rulesets)

    @property
    def active_merge_queue_required(self) -> bool:
        return any(rule.merge_queue_required for rule in self.active_rulesets)

    @property
    def complete(self) -> bool:
        return (
            self.branch_protection_available
            and self.rulesets_complete
            and (self.codeowners_available or not self.active_codeowners_required)
            and not self.warnings
        )

    def summary_text(self) -> str:
        """Return plain-language policy evidence without claiming merge authority."""
        protection = (
            "configured"
            if self.branch_protection_enabled
            else "no legacy branch protection reported"
            if self.branch_protection_enabled is False
            else "branch protection unavailable"
        )
        lines = [f"Base branch policy ({self.base_branch}): {protection}."]
        if self.active_required_approvals:
            lines.append(f"Required approvals observed: {self.active_required_approvals}.")
        if self.active_required_checks:
            lines.append(
                "Required checks observed: " + ", ".join(self.active_required_checks) + "."
            )
        if self.active_codeowners_required:
            lines.append("A CODEOWNERS review is required by the observed policy.")
        if self.codeowners_path:
            lines.append(f"CODEOWNERS file found: {self.codeowners_path}.")
        elif self.codeowners_available:
            lines.append("No CODEOWNERS file was found in the standard locations.")
        if self.active_merge_queue_required:
            lines.append("An active branch ruleset requires the merge queue.")
        if self.active_rulesets:
            lines.append(
                "Active rulesets: " + ", ".join(rule.name for rule in self.active_rulesets) + "."
            )
        evaluating = tuple(rule.name for rule in self.rulesets if rule.enforcement == "evaluate")
        if evaluating:
            lines.append("Rulesets in evaluation mode: " + ", ".join(evaluating) + ".")
        lines.append(
            "Policy is advisory; GitHub remains authoritative and may apply additional rules."
        )
        lines.extend(f"Policy data warning: {warning}" for warning in self.warnings)
        return "\n".join(lines)


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    try:
        return getattr(value, key, default)
    except Exception:  # noqa: BLE001 - defensive around incomplete API models
        return default


def _text(value: Any, limit: int = 256) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _names(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(dict.fromkeys(name[:256] for name in value if isinstance(name, str) and name))


def _status(exc: Exception) -> int | None:
    status = getattr(exc, "status", None)
    return status if isinstance(status, int) else None


def _ref_pattern_matches(pattern: str, branch: str, default_branch: str) -> bool:
    if pattern == "~ALL":
        return True
    if pattern == "~DEFAULT_BRANCH":
        return branch == default_branch
    if pattern.startswith("refs/heads/"):
        pattern = pattern[len("refs/heads/") :]
    return fnmatchcase(branch, pattern)


def _applies_to_branch(ruleset: Any, branch: str, default_branch: str) -> bool:
    conditions = _get(ruleset, "conditions", {})
    ref_name = _get(conditions, "ref_name", {})
    includes = _get(ref_name, "include", ())
    excludes = _get(ref_name, "exclude", ())
    if not isinstance(includes, (list, tuple)):
        includes = ()
    if not isinstance(excludes, (list, tuple)):
        excludes = ()
    included = not includes or any(
        _ref_pattern_matches(pattern, branch, default_branch)
        for pattern in includes
        if isinstance(pattern, str)
    )
    excluded = any(
        _ref_pattern_matches(pattern, branch, default_branch)
        for pattern in excludes
        if isinstance(pattern, str)
    )
    return included and not excluded


def _sequence(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _rule_set(value: Any) -> GitHubRuleSetPolicy | None:
    ruleset_id = _get(value, "id")
    if isinstance(ruleset_id, bool) or not isinstance(ruleset_id, int) or ruleset_id <= 0:
        return None
    name = _text(_get(value, "name"), 160) or f"Ruleset {ruleset_id}"
    raw_enforcement = _text(_get(value, "enforcement"), 32).casefold()
    enforcement = (
        "active"
        if raw_enforcement in {"active", "enabled"}
        else "evaluate"
        if raw_enforcement == "evaluate"
        else "disabled"
    )
    types: list[str] = []
    checks: list[str] = []
    approvals: int | None = None
    codeowners: bool | None = None
    merge_queue = False
    for rule in _sequence(_get(value, "rules"))[:100]:
        rule_type = _text(_get(rule, "type"), 80)
        if not rule_type:
            continue
        types.append(rule_type)
        params = _get(rule, "parameters", {})
        if rule_type == "required_status_checks":
            for check in _sequence(_get(params, "required_status_checks"))[:100]:
                context = _text(_get(check, "context"), 256)
                if context:
                    checks.append(context)
        elif rule_type == "pull_request":
            raw_count = _get(params, "required_approving_review_count")
            if isinstance(raw_count, int) and not isinstance(raw_count, bool):
                approvals = max(approvals or 0, max(0, raw_count))
            raw_codeowners = _get(
                params,
                "require_code_owner_review",
                _get(params, "require_code_owner_reviews"),
            )
            if isinstance(raw_codeowners, bool):
                codeowners = raw_codeowners
        elif rule_type == "merge_queue":
            merge_queue = True
    return GitHubRuleSetPolicy(
        ruleset_id=ruleset_id,
        name=name,
        enforcement=enforcement,
        rule_types=tuple(dict.fromkeys(types)),
        required_checks=tuple(dict.fromkeys(checks)),
        required_approvals=approvals,
        codeowners_review_required=codeowners,
        merge_queue_required=merge_queue,
    )


def _legacy_protection(protection: Any) -> tuple[Any, ...]:
    required_reviews = _get(protection, "required_pull_request_reviews")
    raw_approvals = _get(required_reviews, "required_approving_review_count")
    approvals = raw_approvals if isinstance(raw_approvals, int) else 0
    codeowners = _get(required_reviews, "require_code_owner_reviews")
    status_checks = _get(protection, "required_status_checks")
    contexts = list(_names(_get(status_checks, "contexts", ())))
    for check in _sequence(_get(status_checks, "checks")):
        context = _text(_get(check, "context"), 256)
        if context:
            contexts.append(context)
    strict = _get(status_checks, "strict")
    conversation = _get(_get(protection, "required_conversation_resolution"), "enabled")
    return (
        approvals,
        tuple(dict.fromkeys(contexts)),
        strict if isinstance(strict, bool) else None,
        codeowners if isinstance(codeowners, bool) else False,
        conversation if isinstance(conversation, bool) else False,
    )


def _load_codeowners(repo: Any, branch: str, warnings: list[str]) -> tuple[str, bool]:
    for path in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        try:
            entry = repo.get_contents(path, ref=branch)
        except Exception as exc:  # noqa: BLE001 - permission and transport failures stay visible
            if _status(exc) == 404:
                continue
            warnings.append(f"CODEOWNERS lookup failed: {exc}")
            return "", False
        if _get(entry, "type") != "file":
            continue
        try:
            size = int(_get(entry, "size", 0) or 0)
        except (TypeError, ValueError):
            size = 0
        suffix = " (too large to inspect)" if size > _MAX_CODEOWNERS_BYTES else ""
        return f"{path}{suffix}", True
    return "", True


def fetch_merge_policy(provider: Any, full_name: str, base_branch: str) -> GitHubMergePolicy:
    """Read branch protection, matching rulesets, and standard CODEOWNERS paths.

    Every source is bounded and independently reported. Missing permissions or
    unsupported API behavior never become a claim that the branch has no rules.
    """
    warnings: list[str] = []
    try:
        repo = provider._repo(full_name)  # noqa: SLF001 - shared provider resolver
    except Exception as exc:  # noqa: BLE001
        return GitHubMergePolicy(
            base_branch=base_branch,
            branch_protection_available=False,
            branch_protection_enabled=None,
            rulesets_complete=False,
            codeowners_available=False,
            warnings=(f"Could not resolve the repository: {exc}",),
        )

    protection_available = True
    protection_enabled: bool | None = None
    approvals: int | None = None
    required_checks: tuple[str, ...] = ()
    strict_checks: bool | None = None
    codeowners_required: bool | None = None
    conversation_required: bool | None = None
    try:
        branch = repo.get_branch(base_branch)
    except Exception as exc:  # noqa: BLE001
        protection_available = False
        warnings.append(f"Base branch protection could not be read: {exc}")
        branch = None
    if branch is not None:
        try:
            protection = branch.get_protection()
        except Exception as exc:  # noqa: BLE001
            if _status(exc) == 404:
                protection_enabled = False
                approvals = 0
                required_checks = ()
                strict_checks = False
                codeowners_required = False
                conversation_required = False
            else:
                protection_available = False
                warnings.append(f"Branch protection could not be read: {exc}")
        else:
            protection_enabled = True
            (
                approvals,
                required_checks,
                strict_checks,
                codeowners_required,
                conversation_required,
            ) = _legacy_protection(protection)

    rulesets: list[GitHubRuleSetPolicy] = []
    rulesets_complete = True
    requester = getattr(repo, "_requester", None)
    repo_url = _text(getattr(repo, "url", ""), 2048).rstrip("/")
    request = getattr(requester, "requestJsonAndCheck", None)
    if not repo_url or not callable(request):
        rulesets_complete = False
        warnings.append("Repository rulesets are unavailable in this GitHub client.")
    else:
        listed: list[Any] = []
        for page in range(1, _MAX_RULESET_PAGES + 1):
            try:
                _headers, data = request(
                    "GET",
                    f"{repo_url}/rulesets",
                    parameters={
                        "includes_parents": "true",
                        "targets": "branch",
                        "per_page": 100,
                        "page": page,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                rulesets_complete = False
                warnings.append(f"Repository rulesets could not be read: {exc}")
                break
            if not isinstance(data, list):
                rulesets_complete = False
                warnings.append("GitHub returned an invalid repository ruleset list.")
                break
            listed.extend(data)
            if len(data) < 100:
                break
        else:
            rulesets_complete = False
            warnings.append("Repository rulesets exceed the three-page read limit.")

        candidates = listed
        default_branch = _text(getattr(repo, "default_branch", ""))
        for row in candidates[:_MAX_RULESET_DETAILS]:
            raw_id = _get(row, "id")
            if isinstance(raw_id, bool) or not isinstance(raw_id, int) or raw_id <= 0:
                rulesets_complete = False
                warnings.append("GitHub returned a ruleset without a valid ID.")
                continue
            try:
                _headers, detail = request(
                    "GET",
                    f"{repo_url}/rulesets/{raw_id}",
                    parameters={"includes_parents": "true"},
                )
            except Exception as exc:  # noqa: BLE001
                rulesets_complete = False
                warnings.append(f"Ruleset {raw_id} details could not be read: {exc}")
                continue
            if not isinstance(detail, dict):
                rulesets_complete = False
                warnings.append(f"GitHub returned invalid details for ruleset {raw_id}.")
                continue
            if _get(detail, "target") not in (None, "branch") or not _applies_to_branch(
                detail, base_branch, default_branch
            ):
                continue
            mapped = _rule_set(detail)
            if mapped is not None and mapped.enforcement != "disabled":
                rulesets.append(mapped)
        if len(candidates) > _MAX_RULESET_DETAILS:
            rulesets_complete = False
            warnings.append(
                f"Only the first {_MAX_RULESET_DETAILS} matching rulesets were inspected."
            )

    codeowners_path, codeowners_available = _load_codeowners(repo, base_branch, warnings)
    return GitHubMergePolicy(
        base_branch=base_branch,
        branch_protection_available=protection_available,
        branch_protection_enabled=protection_enabled,
        required_approvals=approvals,
        required_checks=required_checks,
        strict_checks=strict_checks,
        codeowners_review_required=codeowners_required,
        conversation_resolution_required=conversation_required,
        rulesets=tuple(rulesets),
        rulesets_complete=rulesets_complete,
        codeowners_path=codeowners_path,
        codeowners_available=codeowners_available,
        warnings=tuple(warnings),
    )


__all__ = [
    "GitHubMergePolicy",
    "GitHubPullQueueState",
    "GitHubRuleSetPolicy",
    "fetch_merge_policy",
]
