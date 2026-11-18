"""Quick commands on a repository, its commits, pull requests, releases and alerts.

* A repository: **Languages**, **License**, **Star History**, **Mark Its
  Notifications Read**, **Set a Custom Property...**, **Compare
  Dependencies...**, **SBOM Report**, **Ruleset History...**, **Secret
  Scanning History**.
* A commit: **Branches at This Commit**, and the reactions on its comments:
  **Reactions on a Commit Comment...**, **React to a Commit Comment...**,
  **Remove My Reaction...**.
* A pull request: **Re-request Review...**. A release: **GitHub's Release
  Notes...**.
* A secret scanning alert: **Where It Was Found**. A security advisory:
  **Advisory Comments**, **Comment on Advisory...**, **Edit an Advisory
  Comment...**, **Make a Private Fork for the Fix**.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from quill.core.github.quick_actions import Ask, Quick, QuickError, bulleted, call, plain

__all__ = ["REPO_QUICK"]

_REACTIONS = ("+1", "-1", "laugh", "confused", "heart", "hooray", "rocket", "eyes")
_REACTION_WORDS = (
    "Thumbs up", "Thumbs down", "Laugh", "Confused", "Heart", "Hooray", "Rocket", "Eyes",
)  # fmt: skip


def _languages(data: Any, _ctx: dict[str, str]) -> str:
    if not isinstance(data, Mapping) or not data:
        return "GitHub found no code it recognises here."
    total = sum(v for v in data.values() if isinstance(v, int)) or 1
    parts = [f"{name} {round(100 * size / total)} percent" for name, size in data.items()]
    return "Languages: " + ", ".join(parts) + "."


def _license(data: Any, _ctx: dict[str, str]) -> str:
    data = data if isinstance(data, Mapping) else {}
    found = data.get("license") if isinstance(data.get("license"), Mapping) else {}
    name = found.get("name") or "a licence GitHub does not recognise"
    return f"{name} ({found.get('spdx_id') or 'no SPDX id'}), in {data.get('path', 'its file')}."


def _stars(data: Any, _ctx: dict[str, str]) -> str:
    rows = data if isinstance(data, list) else (data or {}).get("history") or []
    lines = [
        f"{str(r.get('date') or r.get('starred_at') or r.get('week') or '')[:10]}: "
        f"{r.get('count', r.get('stars', ''))}"
        for r in rows
        if isinstance(r, Mapping)
    ]
    return bulleted(lines, plain(data))


def _compare(data: Any, _ctx: dict[str, str]) -> str:
    rows = []
    for d in data if isinstance(data, list) else ():
        if isinstance(d, Mapping):
            vulns = d.get("vulnerabilities") or []
            rows.append(
                f"{d.get('change_type')}: {d.get('name')} {d.get('version')} "
                f"({d.get('ecosystem')}, {d.get('manifest')})"
                + (f", {len(vulns)} known vulnerabilities" if vulns else "")
            )
    return bulleted(rows, "No dependency changed between those two.")


def _sbom(api: Any, ctx: dict[str, str]) -> str:
    asked = call(api, "GET", "/repos/{repo}/dependency-graph/sbom/generate-report", ctx)
    text = str(asked)
    found = re.search(r"fetch-report/([0-9a-fA-F-]{8,})", text) or re.search(
        r"'(?:sbom_uuid|uuid)': '([0-9a-fA-F-]{8,})'", text
    )
    if not found:
        return plain(asked)
    report = call(
        api,
        "GET",
        "/repos/{repo}/dependency-graph/sbom/fetch-report/{uuid}",
        {**ctx, "uuid": found.group(1)},
    )
    return plain(report)


def _rulesets(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", "/repos/{repo}/rulesets?per_page=100", ctx)
    return [
        (f"{r.get('name')} ({r.get('enforcement')})", str(r.get("id")))
        for r in data if isinstance(r, Mapping)
    ] if isinstance(data, list) else []  # fmt: skip


def _history(data: Any, _ctx: dict[str, str]) -> str:
    rows = [
        f"Version {v.get('version_id')}, {str(v.get('updated_at') or '')[:16]}, by "
        f"{(v.get('actor') or {}).get('login') or (v.get('actor') or {}).get('type') or 'someone'}"
        for v in data if isinstance(v, Mapping)
    ] if isinstance(data, list) else []  # fmt: skip
    return bulleted(rows, "No changes are recorded for this ruleset.")


def _comments(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", "/repos/{repo}/commits/{sha}/comments?per_page=100", ctx)
    return [
        (f"{(c.get('user') or {}).get('login')}: {str(c.get('body') or '')[:60]}", str(c["id"]))
        for c in data if isinstance(c, Mapping) and c.get("id")
    ] if isinstance(data, list) else []  # fmt: skip


def _mine(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    me = call(api, "GET", "/user", ctx)
    login = me.get("login") if isinstance(me, Mapping) else ""
    out = []
    for label, comment in _comments(api, ctx):
        reactions = call(api, "GET", "/repos/{repo}/comments/{c}/reactions", {**ctx, "c": comment})
        for r in reactions if isinstance(reactions, list) else ():
            if isinstance(r, Mapping) and (r.get("user") or {}).get("login") == login:
                out.append((f"{r.get('content')} on {label}", f"{comment}/{r.get('id')}"))
    return out


def _reactions(data: Any, _ctx: dict[str, str]) -> str:
    rows = [
        f"{(r.get('user') or {}).get('login')}: {r.get('content')}"
        for r in data if isinstance(r, Mapping)
    ] if isinstance(data, list) else []  # fmt: skip
    return bulleted(rows, "Nobody has reacted to that comment.")


def _secret(ctx: dict[str, str]) -> str:
    kind, _sep, number = ctx.get("key", "").partition(":")
    if "secret" not in kind or not number:
        raise QuickError("Where It Was Found is for a secret scanning alert.")
    return number


def _locations(api: Any, ctx: dict[str, str]) -> Any:
    number = _secret(ctx)
    return call(
        api, "GET", "/repos/{repo}/secret-scanning/alerts/{n}/locations", {**ctx, "n": number}
    )


def _where(data: Any, _ctx: dict[str, str]) -> str:
    rows = []
    for loc in data if isinstance(data, list) else ():
        if isinstance(loc, Mapping):
            found = loc.get("details")
            d: Mapping[str, Any] = found if isinstance(found, Mapping) else {}
            where = d.get("path") or d.get("issue_title_url") or d.get("pull_request_body_url")
            line = f", line {d['start_line']}" if d.get("start_line") else ""
            commit = f", commit {str(d['commit_sha'])[:7]}" if d.get("commit_sha") else ""
            rows.append(f"{loc.get('type')}: {where or 'somewhere GitHub names'}{line}{commit}")
    return bulleted(rows, "GitHub lists no place for this secret.")


_ADV = "/repos/{repo}/security-advisories/{key}"


def _advisory_comments(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", _ADV + "/comments?per_page=100", ctx)
    return [
        (f"{(c.get('user') or c.get('author') or {}).get('login')}: "
         f"{str(c.get('body') or '')[:60]}", str(c.get("id")))
        for c in data if isinstance(c, Mapping)
    ] if isinstance(data, list) else []  # fmt: skip


_REPO = frozenset({"repo"})
_ADVISORY = frozenset({"advisory"})

REPO_QUICK: tuple[Quick, ...] = (
    Quick("languages", "Languages", ("repository",), _REPO,
          "How much of the code is in each language, as GitHub counts it.",
          ("GET /repos/{owner}/{repo}/languages",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/languages", ctx), _languages,
          needs=("repo",)),
    Quick("repo_license", "License", ("repository",), _REPO,
          "The licence GitHub found, and the file it is in.",
          ("GET /repos/{owner}/{repo}/license",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/license", ctx), _license,
          needs=("repo",)),
    Quick("star_history", "Star History", ("repository",), _REPO,
          "How many people starred it over time.",
          ("GET /repos/{owner}/{repo}/stargazers/history",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/stargazers/history", ctx), _stars,
          report=True, needs=("repo",)),
    Quick("repo_notifications_read", "Mark Its Notifications Read", ("repository",), _REPO,
          "Mark every notification about this repository as read.",
          ("PUT /repos/{owner}/{repo}/notifications",),
          lambda api, ctx: call(api, "PUT", "/repos/{repo}/notifications", ctx, {}),
          lambda _d, _ctx: "Marked this repository's notifications as read.",
          tier="O", need="sign_in", needs=("repo",),
          live="needs Jeff: changes his own notifications"),
    Quick("repo_custom_property", "Set a Custom Property...", ("repository",), _REPO,
          "Give one of the organization's custom properties a value here.",
          ("PATCH /repos/{owner}/{repo}/properties/values",),
          lambda api, ctx: call(api, "PATCH", "/repos/{repo}/properties/values", ctx, {
              "properties": [{"property_name": ctx["prop"], "value": ctx.get("value") or None}]
          }),
          lambda _d, ctx: f"Set {ctx['prop']}.",
          tier="V", need="repo:admin",
          asks=(Ask("prop", "The property's name:"),
                Ask("value", "Its value (empty clears it):", optional=True)),
          needs=("repo",), live="needs Jeff: an organization with a custom property"),
    Quick("compare_dependencies", "Compare Dependencies...", ("repository",), _REPO,
          "Which dependencies changed between two branches, tags or commits, and their "
          "known vulnerabilities.",
          ("GET /repos/{owner}/{repo}/dependency-graph/compare/{basehead}",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/dependency-graph/compare/{bh}", ctx),
          _compare, report=True,
          asks=(Ask("bh", "Compare, as base...head (such as main...my-branch):"),),
          needs=("repo",)),
    Quick("sbom_report", "SBOM Report", ("repository",), _REPO,
          "Ask GitHub to build a software bill of materials report, and read it.",
          ("GET /repos/{owner}/{repo}/dependency-graph/sbom/generate-report",
           "GET /repos/{owner}/{repo}/dependency-graph/sbom/fetch-report/{sbom_uuid}"),
          _sbom, lambda text, _ctx: str(text), report=True, needs=("repo",)),
    Quick("ruleset_history", "Ruleset History...", ("repository",), _REPO,
          "Each change to one of this repository's rulesets, and who made it.",
          ("GET /repos/{owner}/{repo}/rulesets/{ruleset_id}/history",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/rulesets/{ruleset}/history", ctx),
          _history, report=True, pick=_rulesets, pick_key="ruleset",
          pick_question="Which ruleset?", needs=("repo",)),
    Quick("secret_scan_history", "Secret Scanning History", ("repository",), _REPO,
          "When GitHub last scanned this repository for secrets, and how.",
          ("GET /repos/{owner}/{repo}/secret-scanning/scan-history",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/secret-scanning/scan-history", ctx),
          report=True, needs=("repo",)),
    Quick("branches_at_commit", "Branches at This Commit", ("commit",), frozenset({"commit"}),
          "Which branches end at this commit.",
          ("GET /repos/{owner}/{repo}/commits/{commit_sha}/branches-where-head",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/commits/{sha}/branches-where-head",
                                ctx),
          lambda data, _ctx: "Branches here: " + (", ".join(
              str(b.get("name")) for b in data if isinstance(b, Mapping)
          ) if isinstance(data, list) and data else "none") + ".",
          needs=("repo", "sha")),
    Quick("commit_comment_reactions", "Reactions on a Commit Comment...", ("commit",),
          frozenset({"commit"}), "Who reacted to a comment on this commit, and how.",
          ("GET /repos/{owner}/{repo}/comments/{comment_id}/reactions",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/comments/{comment}/reactions", ctx),
          _reactions, report=True, pick=_comments, pick_key="comment",
          pick_question="Which comment?", needs=("repo", "sha")),
    Quick("react_commit_comment", "React to a Commit Comment...", ("commit",),
          frozenset({"commit"}), "Add a reaction to a comment on this commit.",
          ("POST /repos/{owner}/{repo}/comments/{comment_id}/reactions",),
          lambda api, ctx: call(api, "POST", "/repos/{repo}/comments/{comment}/reactions", ctx,
                                {"content": ctx["reaction"]}),
          lambda _d, _ctx: "Reacted.", tier="O", need="sign_in",
          asks=(Ask("reaction", "Which reaction?", "choice", _REACTION_WORDS, _REACTIONS),),
          pick=_comments, pick_key="comment", pick_question="Which comment?",
          needs=("repo", "sha"), live="needs Jeff: a commit comment on the test repository"),
    Quick("unreact_commit_comment", "Remove My Reaction from a Commit Comment...", ("commit",),
          frozenset({"commit"}), "Take back a reaction you gave a comment on this commit.",
          ("DELETE /repos/{owner}/{repo}/comments/{comment_id}/reactions/{reaction_id}",),
          lambda api, ctx: call(api, "DELETE", "/repos/{repo}/comments/{c}/reactions/{r}", {
              **ctx, "c": ctx["mine"].split("/")[0], "r": ctx["mine"].split("/")[1]}),
          lambda _d, _ctx: "Removed your reaction.", tier="O", need="sign_in",
          pick=_mine, pick_key="mine", pick_question="Which of your reactions?",
          needs=("repo", "sha"), live="needs Jeff: a commit comment he reacted to"),
    Quick("rerequest_review", "Re-request Review...", ("pull_request",), frozenset({"item"}),
          "Ask reviewers who already reviewed to look again.",
          ("POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers/rerequest",),
          lambda api, ctx: call(
              api, "POST", "/repos/{repo}/pulls/{number}/requested_reviewers/rerequest", ctx,
              {"reviewers": [x.strip().lstrip("@") for x in ctx["who"].split(",") if x.strip()]},
          ),
          lambda _d, ctx: f"Asked {ctx['who']} to review again.", tier="V", need="repo:write",
          asks=(Ask("who", "Who to ask again, by login, separated by commas:"),),
          needs=("repo", "number"), live="needs Jeff: a pull request someone reviewed"),
    Quick("generate_release_notes", "GitHub's Release Notes...", ("release",),
          frozenset({"release"}), "The notes GitHub writes from the changes since another tag.",
          ("POST /repos/{owner}/{repo}/releases/generate-notes",),
          lambda api, ctx: call(api, "POST", "/repos/{repo}/releases/generate-notes", ctx, {
              "tag_name": ctx["tag"],
              **({"previous_tag_name": ctx["since"]} if ctx.get("since") else {}),
          }),
          lambda data, _ctx: str((data or {}).get("body") or plain(data)), report=True,
          asks=(Ask("since", "Since which tag? (empty: the release before)", optional=True),),
          needs=("repo", "tag")),
    Quick("secret_locations", "Where It Was Found", ("security_alert",),
          frozenset({"security"}), "Every file, commit, issue or comment the secret is in.",
          ("GET /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}/locations",),
          _locations, _where, report=True, needs=("repo", "key")),
    Quick("advisory_comments", "Advisory Comments", ("advisory",), _ADVISORY,
          "The private discussion on this draft advisory.",
          ("GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments",),
          lambda api, ctx: call(api, "GET", _ADV + "/comments?per_page=100", ctx),
          lambda data, _ctx: bulleted([
              f"{(c.get('user') or c.get('author') or {}).get('login')}: {c.get('body')}"
              for c in data if isinstance(c, Mapping)
          ] if isinstance(data, list) else [], "No comments yet."),
          report=True, needs=("repo", "key")),
    Quick("advisory_comment", "Comment on Advisory...", ("advisory",), _ADVISORY,
          "Write in the advisory's private discussion.",
          ("POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments",),
          lambda api, ctx: call(api, "POST", _ADV + "/comments", ctx, {"body": ctx["body"]}),
          lambda _d, _ctx: "Commented.", tier="V", need="repo:admin",
          asks=(Ask("body", "Your comment:"),), needs=("repo", "key"),
          live="needs Jeff: a draft security advisory on the test repository"),
    Quick("advisory_comment_edit", "Edit an Advisory Comment...", ("advisory",), _ADVISORY,
          "Change something you wrote in the advisory's discussion.",
          ("PATCH /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments/{comment_id}",),
          lambda api, ctx: call(api, "PATCH", _ADV + "/comments/{comment}", ctx,
                                {"body": ctx["body"]}),
          lambda _d, _ctx: "Saved the comment.", tier="V", need="repo:admin",
          pick=_advisory_comments, pick_key="comment", pick_question="Which comment?",
          asks=(Ask("body", "Its new text:"),), needs=("repo", "key"),
          live="needs Jeff: a draft security advisory with his comment"),
    Quick("advisory_fork", "Make a Private Fork for the Fix", ("advisory",), _ADVISORY,
          "A temporary private fork where collaborators can work on the fix.",
          ("POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/forks",),
          lambda api, ctx: call(api, "POST", _ADV + "/forks", ctx, {}),
          lambda data, _ctx: f"Made {(data or {}).get('full_name', 'the private fork')}. "
          "Work on the fix there; it merges into the advisory's repository.",
          tier="V", need="repo:admin",
          confirm="Make a temporary private fork for the fix to {name}?",
          needs=("repo", "key"), live="needs Jeff: a draft security advisory"),
)  # fmt: skip
