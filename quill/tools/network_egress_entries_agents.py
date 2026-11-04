"""Reviewed egress for agent tasks: the Codex engine, and person-approved commands.

Split out of :mod:`quill.tools.network_egress_entries` under GATE-11, like
its Radio, speech and Cast siblings. Adding an entry here is the review.
"""

from __future__ import annotations

AGENT_EGRESS: dict[str, str] = {
    "core/ai/codex_app_server.py::start": (
        "The Codex engine (ChatGPT plan, agent tasks; Phase 4b). "
        "CodexAppServer.start launches the bundled codex-app-server.exe "
        "(tools/codex, found only by find_codex_app_server and checked "
        "against the SHA-256 pin in core/ai/codex_binary.py before every "
        "launch) through safe_subprocess.spawn_subprocess_safely, as a "
        "long-lived child over stdio. The child talks to api.openai.com over "
        "HTTPS with this app's own ChatGPT plan token, passed only as "
        "ACCESS_TOKEN in a minimal child environment (never this process's "
        "environment, never the command line). What is sent: the agent's "
        "instructions, the person's instruction and follow-ups, and the "
        "results of the QUILL tools the agent calls. Codex's own shell, file "
        "edit, apply_patch, image generation, view_image, plugins, apps, MCP "
        "and web search are switched off at launch and in thread/start, the "
        "sandbox is read-only and every built-in approval is declined, unless "
        "the person turned on Codex's own command runner or file changes for "
        "one project (decision 4, core/ai/vendor_tools.py): then the thread "
        "works in that project folder, file changes switch the sandbox to "
        "workspace-write, and every built-in approval is asked of the person. "
        "Analytics is switched off (analytics.enabled=false); whether the "
        "child sends other telemetry is checked by gate G5. CODEX_HOME and "
        "the working directory are this app's per-task folders, deleted "
        "after the task. Reached only when the person starts an agent task "
        "with Codex chosen; never in the background; refused in Safe Mode. "
        "Not on the external-engine allowlist, which guards a different, "
        "per-request spawn."
    ),
    # A new kind of entry (code.md 4.6): not QUILL reaching the network, but a
    # command the PERSON approved, which may.
    "stability/process_tree.py::start_tree_process": (
        "Person-approved command (code.md 4.6, decisions 7 and 9). A project "
        "task's project_run tool runs one command in the project folder, "
        "through cmd /d /s /c or /bin/sh -c, in a Job Object that Stop ends "
        "whole. QUILL itself sends nothing here, but the command can reach the "
        "network, as anything the person's account runs can: pip install, npm "
        "install, git fetch, curl. QUILL cannot block that on Windows without "
        "admin features, so it labels it instead: assess_command adds 'This may "
        "reach the internet.' for installers and network tools, and Always "
        "Allow is never offered with a warning. Every command asks first, "
        "unless the person put that exact command or a prefix they typed on "
        "this project's allow list (kept in QUILL's app data, never in the "
        "repository) or turned on Run Commands Without Asking for the project. "
        "Pushing, publishing and system changes are never run for an agent. "
        "The child gets a scrubbed environment: no API key, token, secret or "
        "QUILL_* variable. Output goes to a file in app data. Refused in Safe "
        "Mode, with the rest of the project task."
    ),
}


#: Agent engines that QUILL itself talks to over HTTP (not a child process).
AGENT_HTTP_EGRESS: dict[str, str] = {
    "core/ai/harness/ollama_tools.py::_post": (
        "Ollama practice mode (code.md 3.5): a project or document task on a model "
        "running on this computer. POSTs the conversation, the tool list and the "
        "tool results to Ollama's /api/chat on 127.0.0.1, localhost or [::1] only; "
        "_post refuses any other address, so nothing leaves the machine. Reached "
        "only when the person has chosen Ollama on this computer in My own key and "
        "starts an agent task; never in the background; refused in Safe Mode with "
        "the rest of the agent tasks. No key or token is sent."
    ),
}
