"""Quick commands for Actions: runners, runner groups, checks, step logs, fork workflows.

* An organization's runners: **New Runner...** and **Just-in-Time Runner...**
  in its Runners list, **Removal Commands...**, **Add Runner Label...** and
  **Remove Runner Label...** on a runner; a repository's runners gain the
  just-in-time and removal commands too. A token is put on the clipboard,
  never said.
* A runner group: **Runners in This Group**, **Hosted Runners in This
  Group**, **Add a Runner to This Group...**, **Remove a Runner from This
  Group...**.
* A commit: **Check Run Details...** (with its annotations) and **Re-run a
  Check Suite...**. A run: **Read a Step's Log...**.
* A repository or an organization: **Fork Workflow Settings** and **Fork
  Workflows from Private Repositories...**.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.quick_actions import Ask, Quick, QuickError, bulleted, call

__all__ = ["ACTIONS_QUICK"]

_RUNNERS_ORG = "/orgs/{org}/actions/runners"
_RUNNERS_REPO = "/repos/{repo}/actions/runners"
_GROUP = "/orgs/{org}/actions/runner-groups/{key}"


def _owner(ctx: Mapping[str, str]) -> str:
    return ctx.get("repo") or ctx.get("org", "")


def _downloads(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    from quill.core.github.runner_admin import fetch_downloads

    found = fetch_downloads(api, _owner(ctx))
    return [
        (d.label, "\t".join((d.os, d.architecture, d.url, d.filename, d.sha256))) for d in found
    ]


def _setup(api: Any, ctx: dict[str, str]) -> str:
    from quill.core.github.runner_admin import Download, setup_commands

    os_, arch, url, name, sha = ctx["download"].split("\t")
    return setup_commands(api, _owner(ctx), Download(os_, arch, url, name, sha))


def _removal(api: Any, ctx: dict[str, str]) -> str:
    from quill.core.github.runner_admin import runner_token

    token = runner_token(api, _owner(ctx), "remove")
    return (
        f"# On Linux or macOS, in the runner's folder:\n./config.sh remove --token {token}\n"
        f"# On Windows, in the runner's folder:\n./config.cmd remove --token {token}\n"
    )


def _jit(api: Any, ctx: dict[str, str]) -> str:
    from quill.stability.redaction import remember_secret

    labels = [x.strip() for x in ctx.get("labels", "").split(",") if x.strip()]
    body: dict[str, Any] = {
        "name": ctx["runner_name"],
        "runner_group_id": int(ctx.get("group") or 1),
        "labels": labels or ["self-hosted"],
        "work_folder": "_work",
    }
    base = _RUNNERS_REPO if ctx.get("repo") else _RUNNERS_ORG
    data = call(api, "POST", base + "/generate-jitconfig", ctx, body)
    config = str(data.get("encoded_jit_config") or "") if isinstance(data, Mapping) else ""
    if not config:
        raise QuickError("GitHub sent no runner configuration.")
    remember_secret(config)
    return (
        "# In a folder with the runner downloaded (New Runner shows how), run once:\n"
        f"./run.sh --jitconfig {config}\n"
    )


def _retiring(data: Any, ctx: dict[str, str]) -> str:
    if not isinstance(data, Mapping) or not data:
        return f"GitHub says nothing about runner version {ctx['version']} retiring."
    when = data.get("deprecation_date") or data.get("date") or data.get("deprecated_at")
    if when:
        return f"Runner version {ctx['version']} retires on {str(when)[:10]}. Update it before."
    from quill.core.github.quick_actions import plain

    return plain(data)


def _labels(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", _RUNNERS_ORG + "/{key}/labels", ctx)
    labels = data.get("labels") if isinstance(data, Mapping) else None
    return [
        (str(x.get("name")), str(x.get("name")))
        for x in labels or ()
        if isinstance(x, Mapping) and x.get("type") == "custom" and x.get("name")
    ]


def _runner_rows(data: Any, empty: str) -> str:
    runners = data.get("runners") if isinstance(data, Mapping) else data
    rows = [
        f"{r.get('name')}: {r.get('status', 'unknown')}"
        + (", busy" if r.get("busy") else "")
        + (f", {r['os']}" if r.get("os") else "")
        for r in runners or ()
        if isinstance(r, Mapping)
    ]
    return bulleted(rows, empty)


def _org_runners(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", _RUNNERS_ORG + "?per_page=100", ctx)
    return [
        (str(r.get("name")), str(r.get("id")))
        for r in (data.get("runners") if isinstance(data, Mapping) else None) or ()
        if isinstance(r, Mapping)
    ]


def _group_runners(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", _GROUP + "/runners?per_page=100", ctx)
    return [
        (str(r.get("name")), str(r.get("id")))
        for r in (data.get("runners") if isinstance(data, Mapping) else None) or ()
        if isinstance(r, Mapping)
    ]


def _check_runs(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", "/repos/{repo}/commits/{sha}/check-runs?per_page=100", ctx)
    return [
        (f"{c.get('name')}: {c.get('conclusion') or c.get('status')}", str(c.get("id")))
        for c in (data.get("check_runs") if isinstance(data, Mapping) else None) or ()
        if isinstance(c, Mapping)
    ]


def _check_run(api: Any, ctx: dict[str, str]) -> str:
    run = call(api, "GET", "/repos/{repo}/check-runs/{check}", ctx)
    notes = call(api, "GET", "/repos/{repo}/check-runs/{check}/annotations?per_page=100", ctx)
    run = run if isinstance(run, Mapping) else {}
    found = run.get("output")
    output: Mapping[str, Any] = found if isinstance(found, Mapping) else {}
    lines = [
        f"{run.get('name')}: {run.get('conclusion') or run.get('status')}.",
        f"Started {str(run.get('started_at') or '')[:16]}, finished "
        f"{str(run.get('completed_at') or 'not yet')[:16]}.",
    ]
    if output.get("title"):
        lines.append(str(output["title"]))
    if output.get("summary"):
        lines.append(str(output["summary"]))
    for note in notes if isinstance(notes, list) else ():
        if isinstance(note, Mapping):
            lines.append(
                f"{note.get('annotation_level', 'note')}: {note.get('path')} line "
                f"{note.get('start_line')}: {note.get('message')}"
            )
    if not isinstance(notes, list) or not notes:
        lines.append("No annotations.")
    return "\n".join(lines)


def _suites(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", "/repos/{repo}/commits/{sha}/check-suites?per_page=100", ctx)
    return [
        (
            f"{(s.get('app') or {}).get('name', 'A check suite')}: "
            f"{s.get('conclusion') or s.get('status')}",
            str(s.get("id")),
        )
        for s in (data.get("check_suites") if isinstance(data, Mapping) else None) or ()
        if isinstance(s, Mapping)
    ]


def _steps(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", "/repos/{repo}/actions/runs/{key}/jobs?per_page=100", ctx)
    out = []
    for job in (data.get("jobs") if isinstance(data, Mapping) else None) or ():
        if not isinstance(job, Mapping):
            continue
        for step in job.get("steps") or ():
            if isinstance(step, Mapping):
                label = (
                    f"{job.get('name')}, step {step.get('number')}: {step.get('name')} "
                    f"({step.get('conclusion') or step.get('status')})"
                )
                out.append((label, f"{job.get('id')}/{step.get('number')}"))
    return out


def _step_log(api: Any, ctx: dict[str, str]) -> str:
    job, step = ctx["step"].split("/", 1)
    data = call(
        api,
        "GET",
        "/repos/{repo}/actions/jobs/{job}/steps/{n}/logs",
        {**ctx, "job": job, "n": step},
    )
    text = data if isinstance(data, str) else str(data or "")
    return text[-30000:] if text else "The step wrote nothing to its log."


_FORK_KEYS = (
    ("run_workflows_from_fork_pull_requests", "Run workflows from fork pull requests?"),
    ("send_write_tokens_to_workflows", "Give those workflows a token that can write?"),
    ("send_secrets_and_variables", "Give those workflows your secrets and variables?"),
    ("require_approval_for_fork_pr_workflows", "Ask a maintainer to approve each run first?"),
)


def _fork_path(ctx: Mapping[str, str]) -> str:
    base = "/repos/{repo}" if ctx.get("repo") else "/orgs/{org}"
    return base + "/actions/permissions/fork-pr-workflows-private-repos"


def _fork_said(data: Any, _ctx: dict[str, str]) -> str:
    data = data if isinstance(data, Mapping) else {}
    said = [f"{q.rstrip('?')}: {'yes' if data.get(k) else 'no'}." for k, q in _FORK_KEYS]
    return "Fork pull requests from private repositories: " + " ".join(said)


def _fork_put(api: Any, ctx: dict[str, str]) -> str:
    body = {key: ctx[key] == "true" for key, _q in _FORK_KEYS}
    call(api, "PUT", _fork_path(ctx), ctx, body)
    return "Saved how workflows run for fork pull requests from private repositories."


_ORG_RUNNER = frozenset({"resource", "resource:org_runners"})
_GROUP_ROW = frozenset({"resource", "resource:runner_groups"})
_LIVE_RUNNER = "needs Jeff: a machine to set a self-hosted runner up on"

ACTIONS_QUICK: tuple[Quick, ...] = (
    Quick(
        "org_new_runner", "New Organization Runner...", ("node",), frozenset({"view"}),
        "Copy the commands that set up a runner every allowed repository may use.",
        ("GET /orgs/{org}/actions/runners/downloads",
         "POST /orgs/{org}/actions/runners/registration-token"),
        _setup, tier="A", need="org:owner", pick=_downloads, pick_key="download",
        pick_question="Which system does the machine run?", needs=("org",), node="org_runners",
        copies="Copied the setup commands. Paste them into a terminal on that machine within "
        "the hour; the token in them then stops working.", live=_LIVE_RUNNER,
    ),
    *(
        Quick(
            f"{scope}_jit_runner", "Just-in-Time Runner...", ("node",), frozenset({"view"}),
            "A runner that takes one job and then goes: its configuration, on the clipboard.",
            (f"POST {path}/actions/runners/generate-jitconfig",),
            _jit, tier="A", need=need, needs=(key,), node=node,
            asks=(
                Ask("runner_name", "The runner's name:"),
                Ask("labels", "Its labels, separated by commas (empty for self-hosted):",
                    optional=True),
                *((Ask("group", "Its runner group's number (1 is Default):", "number",
                       default="1"),) if scope == "org" else ()),
            ),
            copies="Copied the command that starts the runner. It takes one job, then GitHub "
            "removes it.", live=_LIVE_RUNNER,
        )
        for scope, path, need, key, node in (
            ("org", "/orgs/{org}", "org:owner", "org", "org_runners"),
            ("repo", "/repos/{owner}/{repo}", "repo:admin", "repo", "runners"),
        )
    ),
    *(
        Quick(
            f"{scope}_runner_retiring", "Is a Runner Version Retiring?...", ("node",),
            frozenset({"view"}),
            "Whether GitHub is retiring a version of the runner program, and when.",
            (f"GET {path}/actions/runners/deprecations/{{version}}",),
            lambda api, ctx: call(
                api, "GET",
                ("/repos/{repo}" if ctx.get("repo") else "/orgs/{org}")
                + "/actions/runners/deprecations/{version}", ctx,
            ),
            _retiring, asks=(Ask("version", "The runner version, such as 2.320.0:"),),
            needs=(key,), node=node,
        )
        for scope, path, key, node in (
            ("org", "/orgs/{org}", "org", "org_runners"),
            ("repo", "/repos/{owner}/{repo}", "repo", "runners"),
        )
    ),
    Quick(
        "org_runner_removal", "Removal Commands...", ("resource",), _ORG_RUNNER,
        "Copy the commands that take this runner off its machine.",
        ("POST /orgs/{org}/actions/runners/remove-token",),
        _removal, tier="A", need="org:owner", needs=("org", "key"),
        copies="Copied the removal commands. Run them in the runner's folder on its machine "
        "within the hour.", live=_LIVE_RUNNER,
    ),
    Quick(
        "repo_runner_removal", "Removal Commands...", ("runner",), frozenset({"runner"}),
        "Copy the commands that take this runner off its machine.",
        ("POST /repos/{owner}/{repo}/actions/runners/remove-token",),
        _removal, tier="A", need="repo:admin", needs=("repo",),
        copies="Copied the removal commands. Run them in the runner's folder on its machine "
        "within the hour.", live=_LIVE_RUNNER,
    ),
    Quick(
        "org_runner_add_label", "Add Runner Label...", ("resource",), _ORG_RUNNER,
        "Give this runner a label workflows can ask for.",
        ("POST /orgs/{org}/actions/runners/{runner_id}/labels",),
        lambda api, ctx: call(api, "POST", _RUNNERS_ORG + "/{key}/labels", ctx,
                              {"labels": [ctx["label"]]}),
        lambda _d, ctx: f"Added the label {ctx['label']}.",
        tier="O", need="org:owner", asks=(Ask("label", "The label to add, such as gpu:"),),
        needs=("org", "key"), reload=True, live="needs Jeff: a self-hosted runner in an org",
    ),
    Quick(
        "org_runner_remove_label", "Remove Runner Label...", ("resource",), _ORG_RUNNER,
        "Take away a label someone gave this runner; GitHub's own labels stay.",
        ("DELETE /orgs/{org}/actions/runners/{runner_id}/labels/{name}",),
        lambda api, ctx: call(api, "DELETE", _RUNNERS_ORG + "/{key}/labels/{label}", ctx),
        lambda _d, ctx: f"Removed the label {ctx['label']}.",
        tier="O", need="org:owner", pick=_labels, pick_key="label",
        pick_question="Which label?", needs=("org", "key"), reload=True,
        live="needs Jeff: a self-hosted runner in an org",
    ),
    Quick(
        "group_runners", "Runners in This Group", ("resource",), _GROUP_ROW,
        "The self-hosted runners in this group.",
        ("GET /orgs/{org}/actions/runner-groups/{runner_group_id}/runners",),
        lambda api, ctx: call(api, "GET", _GROUP + "/runners?per_page=100", ctx),
        lambda data, _ctx: _runner_rows(data, "This group has no self-hosted runners."),
        report=True, needs=("org", "key"),
    ),
    Quick(
        "group_hosted_runners", "Hosted Runners in This Group", ("resource",), _GROUP_ROW,
        "The larger GitHub-hosted runners in this group.",
        ("GET /orgs/{org}/actions/runner-groups/{runner_group_id}/hosted-runners",),
        lambda api, ctx: call(api, "GET", _GROUP + "/hosted-runners?per_page=100", ctx),
        lambda data, _ctx: _runner_rows(data, "This group has no GitHub-hosted runners."),
        report=True, needs=("org", "key"),
    ),
    Quick(
        "group_add_runner", "Add a Runner to This Group...", ("resource",), _GROUP_ROW,
        "Move one of the organization's runners into this group.",
        ("PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}",),
        lambda api, ctx: call(api, "PUT", _GROUP + "/runners/{runner}", ctx, {}),
        lambda _d, ctx: f"{ctx.get('runner_label', 'The runner')} is in this group now.",
        tier="A", need="org:owner", pick=_org_runners, pick_key="runner",
        pick_question="Which runner?", needs=("org", "key"), reload=True,
        live="needs Jeff: a self-hosted runner and a second runner group",
    ),
    Quick(
        "group_remove_runner", "Remove a Runner from This Group...", ("resource",), _GROUP_ROW,
        "Take a runner out of this group; it goes back to the Default group.",
        ("DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}",),
        lambda api, ctx: call(api, "DELETE", _GROUP + "/runners/{runner}", ctx),
        lambda _d, ctx: f"{ctx.get('runner_label', 'The runner')} is out of this group.",
        tier="A", need="org:owner", pick=_group_runners, pick_key="runner",
        pick_question="Which runner?", needs=("org", "key"), reload=True,
        live="needs Jeff: a self-hosted runner in a runner group",
    ),
    Quick(
        "check_run_details", "Check Run Details...", ("commit",), frozenset({"commit"}),
        "One check's result, its summary and every annotation it left.",
        ("GET /repos/{owner}/{repo}/check-runs/{check_run_id}",
         "GET /repos/{owner}/{repo}/check-runs/{check_run_id}/annotations"),
        _check_run, lambda text, _ctx: str(text), report=True, pick=_check_runs,
        pick_key="check", pick_question="Which check?", needs=("repo", "sha"),
    ),
    Quick(
        "rerun_check_suite", "Re-run a Check Suite...", ("commit",), frozenset({"commit"}),
        "Ask an app to run its checks on this commit again.",
        ("POST /repos/{owner}/{repo}/check-suites/{check_suite_id}/rerequest",),
        lambda api, ctx: call(api, "POST", "/repos/{repo}/check-suites/{suite}/rerequest", ctx, {}),
        lambda _d, ctx: f"Asked {ctx.get('suite_label', 'the app')} to run again.",
        tier="V", need="repo:write", pick=_suites, pick_key="suite",
        pick_question="Which app's checks?", needs=("repo", "sha"),
        live="needs Jeff: a commit with a check suite from an app",
    ),
    Quick(
        "step_log", "Read a Step's Log...", ("run",), frozenset({"run"}),
        "One step's log, to read without downloading the whole run's.",
        ("GET /repos/{owner}/{repo}/actions/jobs/{job_id}/steps/{step_number}/logs",),
        _step_log, lambda text, _ctx: str(text), report=True, pick=_steps, pick_key="step",
        pick_question="Which step?", needs=("repo", "key"),
    ),
    *(
        Quick(
            f"{scope}_fork_settings", "Fork Workflow Settings", (menu,), frozenset({kind}),
            "How workflows run for pull requests from forks of private repositories.",
            (f"GET {path}/actions/permissions/fork-pr-workflows-private-repos",),
            lambda api, ctx: call(api, "GET", _fork_path(ctx), ctx), _fork_said, needs=(key,),
        )
        for scope, menu, kind, path, key in (
            ("repo", "repository", "repo", "/repos/{owner}/{repo}", "repo"),
            ("org", "organization", "org", "/orgs/{org}", "org"),
        )
    ),
    *(
        Quick(
            f"{scope}_fork_change", "Fork Workflows from Private Repositories...", (menu,),
            frozenset({kind}),
            "Choose whether fork pull requests run workflows, and with what.",
            (f"PUT {path}/actions/permissions/fork-pr-workflows-private-repos",),
            _fork_put, lambda said, _ctx: str(said), tier="A", need=need,
            asks=tuple(Ask(k, q, "yesno") for k, q in _FORK_KEYS), needs=(key,),
            live="needs Jeff: a private repository and its organization's Actions settings",
        )
        for scope, menu, kind, path, key, need in (
            ("repo", "repository", "repo", "/repos/{owner}/{repo}", "repo", "repo:admin"),
            ("org", "organization", "org", "/orgs/{org}", "org", "org:owner"),
        )
    ),
)  # fmt: skip
