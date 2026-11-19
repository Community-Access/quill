"""Quick commands for security: push protection, dependency review and the security overview.

* A repository: **Allow a Blocked Secret...** lets one secret that push
  protection stopped through, from the placeholder id ``git push`` printed
  and one of GitHub's three reasons (``POST
  .../secret-scanning/push-protection-bypasses``). The secret is still in the
  push, so it asks first and says GitHub keeps an alert for it.
* A pull request: **Dependency Review** reads what the pull request changes
  in the dependency graph, from its base commit to its head commit: each
  dependency added or removed, its licence, and every known vulnerability
  with its severity and advisory (``GET .../dependency-graph/compare``).
* An organization: **Security Overview** counts the open Dependabot, code
  scanning and secret scanning alerts in every repository, worst first, from
  the organization's alert lists. A kind GitHub will not show you is said in
  words, never counted as none (GX11: missing permission never means zero
  risk), and a secret's value is never asked for (``hide_secret``).

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.quick_actions import Ask, Quick, QuickError, call

__all__ = ["BYPASS_REASONS", "SECURITY_QUICK", "dependency_changes", "security_overview"]

#: GitHub's reasons for letting a blocked secret through, and the words QUILL shows.
BYPASS_REASONS: tuple[tuple[str, str], ...] = (
    ("false_positive", "It is not really a secret (a false positive)"),
    ("used_in_tests", "It is only used in tests"),
    ("will_fix_later", "It is real, and I will fix it later"),
)
_SEVERITIES = ("critical", "high", "medium", "moderate", "low", "warning", "note", "error")
_KINDS = (
    ("dependabot", "Dependabot"),
    ("code-scanning", "code scanning"),
    ("secret-scanning", "secret scanning"),
)
_PAGE = 100


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


# -- dependency review --------------------------------------------------------------------


def _vulnerabilities(change: Mapping[str, Any]) -> list[str]:
    out = []
    for vuln in change.get("vulnerabilities") or ():
        if isinstance(vuln, Mapping):
            words = ", ".join(
                part
                for part in (
                    _text(vuln.get("severity")),
                    _text(vuln.get("advisory_ghsa_id")),
                    _text(vuln.get("advisory_summary")),
                )
                if part
            )
            out.append(words or "an advisory GitHub names")
    return out


def dependency_changes(data: Any) -> str:
    """GitHub's dependency diff in words: a summary, then each change with licence and risk."""
    changes = [d for d in (data if isinstance(data, list) else ()) if isinstance(d, Mapping)]
    if not changes:
        return "No dependency changed between those two."
    added = [d for d in changes if d.get("change_type") == "added"]
    removed = [d for d in changes if d.get("change_type") == "removed"]
    risky = [d for d in added if d.get("vulnerabilities")]
    lines = [
        f"Added {len(added)}, removed {len(removed)}. "
        + (
            f"{len(risky)} added {'dependency has' if len(risky) == 1 else 'dependencies have'} "
            "known vulnerabilities."
            if risky
            else "No added dependency has a known vulnerability."
        )
    ]
    for d in sorted(changes, key=lambda d: (not d.get("vulnerabilities"), _text(d.get("name")))):
        kind = _text(d.get("change_type")).capitalize() or "Changed"
        where = ", ".join(x for x in (_text(d.get("ecosystem")), _text(d.get("manifest"))) if x)
        line = f"{kind}: {d.get('name')} {_text(d.get('version'))}".rstrip()
        line += f" ({where})" if where else ""
        line += f", licence {d.get('license') or 'unknown'}"
        found = _vulnerabilities(d)
        if found:
            line += ". Vulnerable: " + "; ".join(found)
        lines.append(line + ".")
    return "\n".join(lines)


def _dependency_review(api: Any, ctx: dict[str, str]) -> Any:
    pull = _mapping(call(api, "GET", "/repos/{repo}/pulls/{number}", ctx))
    base = _text(_mapping(pull.get("base")).get("sha"))
    head = _text(_mapping(pull.get("head")).get("sha"))
    if not base or not head:
        raise QuickError("GitHub did not say which commits this pull request compares.")
    return call(
        api,
        "GET",
        "/repos/{repo}/dependency-graph/compare/{bh}",
        {**ctx, "bh": f"{base}...{head}"},
    )


# -- push protection ------------------------------------------------------------------------


def _bypass(api: Any, ctx: dict[str, str]) -> Any:
    placeholder = ctx.get("placeholder", "").strip()
    if ctx.get("reason") not in {value for value, _words in BYPASS_REASONS}:
        raise QuickError("Choose one of GitHub's reasons for letting the secret through.")
    return call(
        api,
        "POST",
        "/repos/{repo}/secret-scanning/push-protection-bypasses",
        ctx,
        {"reason": ctx["reason"], "placeholder_id": placeholder},
    )


def _bypass_said(data: Any, _ctx: dict[str, str]) -> str:
    found = _mapping(data)
    until = _text(found.get("expire_at"))[:16].replace("T", " at ")
    what = _text(found.get("token_type")) or "the secret"
    return (
        f"GitHub will let {what} through"
        + (f" until {until} UTC" if until else "")
        + ". Push again now; GitHub keeps an alert for it."
    )


# -- the organization's security overview -------------------------------------------------


def _severity(kind: str, alert: Mapping[str, Any]) -> str:
    if kind == "dependabot":
        found = _mapping(alert.get("security_advisory")).get("severity") or _mapping(
            alert.get("security_vulnerability")
        ).get("severity")
    elif kind == "code-scanning":
        rule = _mapping(alert.get("rule"))
        found = rule.get("security_severity_level") or rule.get("severity")
    else:
        found = ""
    return _text(found).lower()


def _tally(words: list[str]) -> str:
    named = [w for w in words if w]
    if not named:
        return ""
    order = {name: i for i, name in enumerate(_SEVERITIES)}
    counts: dict[str, int] = {}
    for word in named:
        counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts, key=lambda w: order.get(w, len(order)))
    return " (" + ", ".join(f"{counts[w]} {w}" for w in ranked) + ")"


def security_overview(api: Any, ctx: dict[str, str]) -> str:
    """Open alerts by repository and kind, worst first; a refused kind said, never zero."""
    seen: dict[str, dict[str, list[str]]] = {}
    refused: list[str] = []
    refused_keys: set[str] = set()
    full: list[str] = []
    for key, label in _KINDS:
        query = f"?state=open&per_page={_PAGE}" + (
            "&hide_secret=true" if key == "secret-scanning" else ""
        )
        try:
            alerts = call(api, "GET", f"/orgs/{{org}}/{key}/alerts{query}", ctx)
        except QuickError as exc:
            refused_keys.add(key)
            refused.append(
                f"{label.capitalize()}: GitHub would not show these to you, so this is not a "
                f"zero. {exc}"
            )
            continue
        listed = [a for a in alerts if isinstance(a, Mapping)] if isinstance(alerts, list) else []
        if len(listed) >= _PAGE:
            full.append(label)
        for alert in listed:
            repo = _text(_mapping(alert.get("repository")).get("full_name")) or "a repository"
            seen.setdefault(repo, {}).setdefault(key, []).append(_severity(key, alert))
    org = ctx.get("org", "the organization")
    if not seen and not refused:
        return f"No open security alerts in {org}'s repositories."

    def weight(repo: str) -> tuple[int, int, str]:
        words = [w for kinds in seen[repo].values() for w in kinds]
        return (-sum(w == "critical" for w in words), -len(words), repo.lower())

    lines = [f"Open security alerts in {org}, by repository, worst first."]
    for repo in sorted(seen, key=weight):
        parts = []
        for key, label in _KINDS:
            found = seen[repo].get(key, [])
            if found:
                parts.append(f"{len(found)} {label}{_tally(found)}")
        lines.append(f"{repo}: " + "; ".join(parts) + ".")
    totals = [
        f"{sum(len(kinds.get(key, [])) for kinds in seen.values())} {label}"
        for key, label in _KINDS
        if key not in refused_keys
    ]
    where = f"{len(seen)} {'repository' if len(seen) == 1 else 'repositories'}"
    lines.append(f"Totals: {', '.join(totals) or 'none GitHub would show'}, in {where}.")
    if full:
        lines.append(
            f"GitHub sends {_PAGE} alerts at a time; {', '.join(full)} has at least that many. "
            "Open the organization's alert list for the rest."
        )
    return "\n".join(lines + refused)


_ORG = frozenset({"org"})

SECURITY_QUICK: tuple[Quick, ...] = (
    Quick("allow_blocked_secret", "Allow a Blocked Secret...", ("repository",),
          frozenset({"repo"}),
          "When push protection stopped your push, let that one secret through: give the "
          "placeholder id git push printed and say why.",
          ("POST /repos/{owner}/{repo}/secret-scanning/push-protection-bypasses",),
          _bypass, _bypass_said, tier="A", need="repo:write",
          asks=(Ask("placeholder", "The placeholder id git push printed for the secret:"),
                Ask("reason", "Why may it go through?", "choice",
                    tuple(words for _v, words in BYPASS_REASONS),
                    tuple(value for value, _w in BYPASS_REASONS))),
          confirm="Let the blocked secret {placeholder} be pushed to {repo}? It stays in the "
          "repository's history, and GitHub keeps an alert for it.",
          needs=("repo",),
          live="needs Jeff: a push that push protection blocked, and its placeholder id"),
    Quick("dependency_review", "Dependency Review", ("pull_request",), frozenset({"item"}),
          "What this pull request changes in the dependencies: each one added or removed, "
          "its licence, and its known vulnerabilities.",
          ("GET /repos/{owner}/{repo}/dependency-graph/compare/{basehead}",),
          _dependency_review, lambda data, _ctx: dependency_changes(data), report=True,
          needs=("repo", "number")),
    Quick("security_overview", "Security Overview", ("organization",), _ORG,
          "Open Dependabot, code scanning and secret scanning alerts in every repository, "
          "counted by severity, worst first.",
          ("GET /orgs/{org}/dependabot/alerts", "GET /orgs/{org}/code-scanning/alerts",
           "GET /orgs/{org}/secret-scanning/alerts"),
          security_overview, lambda text, _ctx: str(text), report=True, needs=("org",)),
)  # fmt: skip
