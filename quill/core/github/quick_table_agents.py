"""Quick commands for Copilot's cloud agent: tasks, automations and Agent Merge.

GitHub's agent APIs are a public preview (``X-GitHub-Api-Version``
2026-03-10), so these send only what GitHub's documentation names (a task's
``prompt``, ``base_ref`` and ``create_pull_request``; an automation's name,
prompt and a trigger GitHub itself offered) and show GitHub's own answer,
refusal included, rather than guessing at anything more.

* A repository: **Start an Agent Task...**, **Agent Tasks**, **An Agent
  Task's Progress...**, **Automations**, **New Automation...**, **Run an
  Automation...**, **Rename an Automation...**, **Delete an Automation...**,
  **An Automation's History...**, **An Automation's Tasks...**, **Automation
  Tools and Triggers**, **Agent Secrets from the Organization**, **Agent
  Variables from the Organization**.
* A pull request: **Ask Copilot to Review**, **Agent Merge**, **Turn On
  Agent Merge**, **Turn Off Agent Merge...**.
* Your profile: **My Agent Tasks** and **My Automations**.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.quick_actions import Ask, Quick, bulleted, call, plain

__all__ = ["AGENT_QUICK"]

_R = "/agents/repos/{repo}"
_REPO = frozenset({"repo"})
_PR = frozenset({"item"})
_LIVE = "not here: needs a Copilot plan with the cloud agent on the test repository"


def _rows(data: Any, key: str) -> list[Mapping[str, Any]]:
    found = data.get(key) if isinstance(data, Mapping) else data
    return [r for r in found or () if isinstance(r, Mapping)] if isinstance(found, list) else []


def _task_line(t: Mapping[str, Any]) -> str:
    what = str(t.get("prompt") or t.get("title") or t.get("name") or "A task")[:80]
    state = t.get("state") or t.get("status") or "unknown"
    when = str(t.get("created_at") or "")[:16]
    return f"{what}: {state}" + (f", started {when}" if when else "")


def _tasks(data: Any, _ctx: dict[str, str]) -> str:
    return bulleted([_task_line(t) for t in _rows(data, "tasks")], "No agent tasks.")


def _pick_tasks(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", _R + "/tasks", ctx)
    return [(_task_line(t), str(t.get("id"))) for t in _rows(data, "tasks") if t.get("id")]


def _automation_line(a: Mapping[str, Any]) -> str:
    on = a.get("enabled")
    return f"{a.get('name') or 'An automation'}" + ("" if on in (None, True) else ", off")


def _automations(data: Any, _ctx: dict[str, str]) -> str:
    return bulleted([_automation_line(a) for a in _rows(data, "automations")], "No automations.")


def _pick_automations(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    data = call(api, "GET", _R + "/automations", ctx)
    return [
        (_automation_line(a), str(a.get("id"))) for a in _rows(data, "automations") if a.get("id")
    ]


def _triggers(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    import json

    data = call(api, "GET", _R + "/automations/available-triggers", ctx)
    rows = _rows(data, "triggers") or _rows(data, "available_triggers")
    return [
        (str(t.get("name") or t.get("description") or t.get("type") or "A trigger"),
         json.dumps(dict(t)))
        for t in rows
    ]  # fmt: skip


def _new_automation(api: Any, ctx: dict[str, str]) -> Any:
    import json

    body = {"name": ctx["auto_name"], "prompt": ctx["prompt"], "triggers": [
        json.loads(ctx["trigger"])
    ]}  # fmt: skip
    return call(api, "POST", _R + "/automations", ctx, body)


def _tools_and_triggers(api: Any, ctx: dict[str, str]) -> str:
    tools = call(api, "GET", _R + "/automations/available-tools", ctx)
    triggers = call(api, "GET", _R + "/automations/available-triggers", ctx)
    return "Tools:\n" + plain(tools) + "\n\nTriggers:\n" + plain(triggers)


def _say(text: str) -> Any:
    return lambda _d, _ctx: text


AGENT_QUICK: tuple[Quick, ...] = (
    Quick("agent_task_start", "Start an Agent Task...", ("repository",), _REPO,
          "Give Copilot's cloud agent a job here; it works on a branch of its own.",
          ("POST /agents/repos/{owner}/{repo}/tasks",),
          lambda api, ctx: call(api, "POST", _R + "/tasks", ctx, {
              "prompt": ctx["prompt"], "create_pull_request": ctx["pr"] == "true",
              **({"base_ref": ctx["base"]} if ctx.get("base") else {})}),
          lambda data, _ctx: "Started the task. " + str(
              (data or {}).get("html_url") or "Agent Tasks shows how it goes."),
          tier="V", need="repo:write",
          asks=(Ask("prompt", "What should Copilot do?"),
                Ask("base", "Starting from which branch? (empty: the default)", optional=True),
                Ask("pr", "Open a pull request when it is done?", "yesno")),
          needs=("repo",), live=_LIVE),
    Quick("agent_tasks", "Agent Tasks", ("repository",), _REPO,
          "Copilot's cloud agent tasks in this repository, and how each is going.",
          ("GET /agents/repos/{owner}/{repo}/tasks",),
          lambda api, ctx: call(api, "GET", _R + "/tasks", ctx), _tasks, report=True,
          needs=("repo",)),
    Quick("agent_task_detail", "An Agent Task's Progress...", ("repository",), _REPO,
          "Everything GitHub says about one agent task.",
          ("GET /agents/repos/{owner}/{repo}/tasks/{task_id}",),
          lambda api, ctx: call(api, "GET", _R + "/tasks/{task}", ctx), report=True,
          pick=_pick_tasks, pick_key="task", pick_question="Which task?", needs=("repo",)),
    Quick("my_agent_tasks", "My Agent Tasks", ("node",), frozenset({"view"}),
          "Every cloud agent task you started, in any repository.",
          ("GET /agents/tasks", "GET /agents/tasks/{task_id}"),
          lambda api, ctx: call(api, "GET", "/agents/tasks", ctx), _tasks, report=True,
          node="my_profile"),
    Quick("my_automations", "My Automations", ("node",), frozenset({"view"}),
          "Every Copilot automation you made.", ("GET /agents/automations",),
          lambda api, ctx: call(api, "GET", "/agents/automations", ctx), _automations,
          report=True, node="my_profile"),
    Quick("automations", "Automations", ("repository",), _REPO,
          "This repository's Copilot automations.",
          ("GET /agents/repos/{owner}/{repo}/automations",
           "GET /agents/repos/{owner}/{repo}/automations/{automation_id}"),
          lambda api, ctx: call(api, "GET", _R + "/automations", ctx), _automations,
          report=True, needs=("repo",)),
    Quick("new_automation", "New Automation...", ("repository",), _REPO,
          "An automation: a prompt Copilot runs whenever its trigger fires.",
          ("POST /agents/repos/{owner}/{repo}/automations",),
          _new_automation, _say("Made the automation."), tier="V", need="repo:write",
          pick=_triggers, pick_key="trigger", pick_question="When should it run?",
          asks=(Ask("auto_name", "Its name:"), Ask("prompt", "What should Copilot do?")),
          needs=("repo",), live=_LIVE),
    Quick("run_automation", "Run an Automation...", ("repository",), _REPO,
          "Run one of this repository's automations now.",
          ("POST /agents/repos/{owner}/{repo}/automations/{automation_id}/tasks",),
          lambda api, ctx: call(api, "POST", _R + "/automations/{auto}/tasks", ctx, {}),
          _say("Started it. Agent Tasks shows how it goes."), tier="V", need="repo:write",
          pick=_pick_automations, pick_key="auto", pick_question="Which automation?",
          needs=("repo",), live=_LIVE),
    Quick("rename_automation", "Rename an Automation...", ("repository",), _REPO,
          "Give one of this repository's automations another name.",
          ("PATCH /agents/repos/{owner}/{repo}/automations/{automation_id}",),
          lambda api, ctx: call(api, "PATCH", _R + "/automations/{auto}", ctx,
                                {"name": ctx["auto_name"]}),
          _say("Renamed it."), tier="V", need="repo:write", pick=_pick_automations,
          pick_key="auto", pick_question="Which automation?",
          asks=(Ask("auto_name", "Its new name:"),), needs=("repo",), live=_LIVE),
    Quick("delete_automation", "Delete an Automation...", ("repository",), _REPO,
          "Delete one of this repository's automations; tasks it ran stay.",
          ("DELETE /agents/repos/{owner}/{repo}/automations/{automation_id}",),
          lambda api, ctx: call(api, "DELETE", _R + "/automations/{auto}", ctx),
          _say("Deleted the automation."), tier="D", need="repo:write",
          pick=_pick_automations, pick_key="auto", pick_question="Which automation?",
          confirm="Delete the automation {auto_label}? It stops running.", needs=("repo",),
          live=_LIVE),
    Quick("automation_history", "An Automation's History...", ("repository",), _REPO,
          "Each change to one automation, newest first.",
          ("GET /agents/repos/{owner}/{repo}/automations/{automation_id}/revisions",
           "GET /agents/repos/{owner}/{repo}/automations/{automation_id}/revisions/{revision_id}"),
          lambda api, ctx: call(api, "GET", _R + "/automations/{auto}/revisions", ctx),
          report=True, pick=_pick_automations, pick_key="auto",
          pick_question="Which automation?", needs=("repo",)),
    Quick("automation_tasks", "An Automation's Tasks...", ("repository",), _REPO,
          "The tasks one automation has run.",
          ("GET /agents/repos/{owner}/{repo}/automations/{automation_id}/tasks",),
          lambda api, ctx: call(api, "GET", _R + "/automations/{auto}/tasks", ctx), _tasks,
          report=True, pick=_pick_automations, pick_key="auto",
          pick_question="Which automation?", needs=("repo",)),
    Quick("automation_options", "Automation Tools and Triggers", ("repository",), _REPO,
          "What an automation here may do, and what may start it.",
          ("GET /agents/repos/{owner}/{repo}/automations/available-tools",
           "GET /agents/repos/{owner}/{repo}/automations/available-triggers"),
          _tools_and_triggers, lambda said, _ctx: str(said), report=True, needs=("repo",)),
    Quick("agent_org_secrets", "Agent Secrets from the Organization", ("repository",), _REPO,
          "The organization's agent secrets this repository may use (names only).",
          ("GET /repos/{owner}/{repo}/agents/organization-secrets",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/agents/organization-secrets", ctx),
          lambda data, _ctx: bulleted([str(s.get("name")) for s in _rows(data, "secrets")],
                                      "None from the organization."), needs=("repo",)),
    Quick("agent_org_variables", "Agent Variables from the Organization", ("repository",),
          _REPO, "The organization's agent variables this repository may use.",
          ("GET /repos/{owner}/{repo}/agents/organization-variables",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/agents/organization-variables", ctx),
          lambda data, _ctx: bulleted([f"{v.get('name')}: {v.get('value')}"
                                       for v in _rows(data, "variables")],
                                      "None from the organization."), needs=("repo",)),
    Quick("copilot_code_review", "Ask Copilot to Review", ("pull_request",), _PR,
          "Ask Copilot for a code review of this pull request.",
          ("POST /repos/{owner}/{repo}/pulls/{pull_number}/copilot-code-review",),
          lambda api, ctx: call(api, "POST", "/repos/{repo}/pulls/{number}/copilot-code-review",
                                ctx, {}),
          _say("Asked Copilot to review. Its review arrives like anyone's."), tier="V",
          need="repo:write", needs=("repo", "number"), live=_LIVE),
    Quick("agent_merge", "Agent Merge", ("pull_request",), _PR,
          "Whether Copilot merges this pull request itself once it is ready, and how.",
          ("GET /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge",),
          lambda api, ctx: call(api, "GET", _R + "/pulls/{number}/agent-merge", ctx),
          needs=("repo", "number")),
    Quick("agent_merge_on", "Turn On Agent Merge", ("pull_request",), _PR,
          "Let Copilot merge this pull request once its checks and reviews allow.",
          ("PUT /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge",),
          lambda api, ctx: call(api, "PUT", _R + "/pulls/{number}/agent-merge", ctx, {}),
          lambda data, _ctx: "Agent Merge is on. " + plain(data), tier="V", need="repo:write",
          needs=("repo", "number"), live=_LIVE),
    Quick("agent_merge_off", "Turn Off Agent Merge...", ("pull_request",), _PR,
          "Stop Copilot merging this pull request.",
          ("DELETE /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge",),
          lambda api, ctx: call(api, "DELETE", _R + "/pulls/{number}/agent-merge", ctx),
          _say("Agent Merge is off."), tier="V", need="repo:write",
          confirm="Turn off Agent Merge for {name}?", needs=("repo", "number"), live=_LIVE),
)  # fmt: skip
