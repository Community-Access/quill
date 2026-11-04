# Agentic coding in QUILL: what we have, and what it would take

Plan of record, 2026-11-02 to 2026-11-05; kept here since 2026-11-05 (it was
`code.md` at the repository root). Code cites it by section as
`code.md <section>` -- for example "code.md 6.4" for the Developer profile --
and those citations resolve in this file. The work it describes shipped in
PR #1760; where shipped code differs from the plan, the code and its
docstrings are the record.

Research and plan, 2026-11-02. Read-only research; this file is the only thing written. It builds on `codex.md` (the AI family plan of record) and does not change any decision in it.

## The short version

**The question.** Could QUILL and QUILL Lite let a blind person work with an AI coding agent: give it a task in plain words, hear its plan, review every change it proposes across several files, approve the commands it wants to run, hear the test results in a sentence, and undo a whole turn with one key? And could that be approachable, rather than another VS Code?

**What we have today.** More than you might think, and less than coding needs.

- Both editors already run a real agent. Do a Document Task (Ctrl+3) opens the agent window, and My GitHub Copilot or Codex works through a task with QUILL's own tools. Every change is shown first in Review AI Changes, word by word, and every applied change is one Ctrl+Z. Approvals use one small dialog: Allow once, Allow for this task, Don't allow. Stop ends a task within a second. Only the closing summary is spoken, and it is brailled too.
- Both engines are bundled and hash-pinned in the shared runtime. The vendors' own shell, file and web tools are switched off; the model sees only QUILL's tools. The twelve apps' GitHub client ids landed in #1737, so Copilot sign-in can work from inside the app.
- QUILL already has strong developer bones: an accessible local git engine (uncommitted changes with a spoken diff, merge conflicts hunk by hunk, blame, stash, bisect, worktrees), GitHub items and PR diffs, Search and Replace in Files, SSH editing, restore points, a sandboxed Python console and code folding as spoken state.

**The gap.** The agent's world is one open document. It cannot list a folder, open a second file, create a file, or run a command or a test. There is no idea of a project, no multi-file review, no undo for a turn that spans files, and no place for command output to land.

**The recommendation.**

1. **Same window, wider world.** Grow Do a Document Task into Do a Project Task. One window, one conversation, the same approval dialog, the same engines. A project is just a folder.
2. **QUILL's own tools, not the vendor's.** The agent reads, searches and edits through new `project.*` family tools, and runs commands through one QUILL `project.run` tool. That keeps every approval, every review and every undo in QUILL's accessible UI, the same under Copilot and Codex.
3. **Copilot first, Codex second,** exactly as `codex.md` decided. Claude through the Agent SDK only on the person's own key, later. Local models through Ollama as a labelled practice mode. Not the free AI: an agent burns many requests a task, and that would cost Jeff money.
4. **A safety net under every turn.** QUILL keeps a private checkpoint of the project before each turn, outside the person's own git history. Undo Last Turn puts every file back. The person's repository is never committed to, pushed or rewritten unless they ask.
5. **Accessibility is the design, not a layer.** One window. Focus never jumps. Nothing streams at the reader. A turn's record is a document with headings. Test results arrive as one sentence. A coach mode explains what the agent did and why, for people learning.

**The phases.** Read-only project questions first (medium), then reviewed multi-file edits with checkpoints (large), then commands and test summaries (medium to large), then the headed transcript and coach mode (medium), then Codex and the other engines on the same tools (medium), then QUILL Lite if Jeff wants it there (decision 1).

**Decisions for Jeff** are at the end, fourteen of them, each with a recommended answer.

## 1. What exists today, verified

Everything here was read in the tree on 2026-11-02, at `295788cf0` on `fix/portable-pip-bootstrap`. Line counts are rough.

### 1.1 The agent that ships now: Do a Document Task

`codex.md` section 5 planned a shared agent layer. PR #1728 ("AI family: Choose Your AI, Copilot and Codex, every app") built it. These modules exist and are wired:

| Module | What it does |
|---|---|
| `quill/core/ai/document_task.py` | `DocumentTaskRunner`: start, follow-up, end, cancel, and a plain-text closing summary built from what actually happened |
| `quill/core/ai/family_tools.py` | `FamilyToolRegistry`: one tool list, translated for Copilot and for Codex; every call goes through the broker and the activity log |
| `quill/core/ai/approvals.py` | `Approver`, `ApprovalGate` (once, this task, deny; nothing carries over between tasks) and the UI-thread bridges |
| `quill/ai_packs/copilot_tool_session.py` | Copilot SDK session: only our tools in `available_tools`, every other permission kind rejected and logged, streaming, Stop |
| `quill/core/ai/harness/codex.py`, `codex_app_server.py`, `codex_binary.py` | Codex app-server child, hash-pinned, `sandbox: read-only`, `approvalPolicy: untrusted`, built-in tools off |
| `quill/core/ai/copilot_runtime.py` | the bundled Copilot runtime in `tools\copilot`, hash-pinned, never from PATH |
| `quill/core/ai/agent_workdir.py` | per-app engine folders, emptied after every task |
| `quill/ui/agent_window.py` | the one agent window, shared by both editors and reused by the apps |
| `quill/ui/hosted_ai_task_commands.py` | the Do a Document Task command, Ctrl+3 in both editors, capability-gated |
| `quill/ui/agent_task_host.py` | the editor as the tools see it; every edit through Review AI Changes and one Ctrl+Z |
| `quill/core/ai/agent_task_words.py` | every sentence the window says, in one place |
| `quill/core/ai/app_task.py`, `quill/ui/app_agent_task.py` | the same shape for the other apps (Radio already has tools) |
| `quill/core/ai/doc_images.py` | alt-text tools: a good pattern for a small, reviewed, namespaced tool set |

The document task's tools (`DOCUMENT_TASK_TOOLS`) are: `read_outline`, `read_section`, `read_document`, `read_selection`, `apply_patch`, `audit_accessibility` and `run_command`. Note that `run_command` here means a QUILL editor command from the 22 in `SAFE_TOOL_IDS` (save, bold, word count and so on), not a shell command.

The window is already good for a screen-reader user, by design:

- Focus starts in the instruction field. Enter sends. A follow-up typed while the task runs goes to the task.
- The transcript and the status line fill in silently; you reach them with Shift+Tab.
- The approval question is a dialog whose text the reader says as focus lands on it. The app says nothing on top of it (GATE-13).
- The closing summary is spoken once and brailled (GATE-BRAILLE).
- Every control has an F1 sentence at construction.
- `docs/qa/screen-reader-checks-2026-10.md` has eleven checks for it (from line 1776), still open for NVDA, JAWS and Narrator.

### 1.2 The permission model

`quill/core/ai/permissions.py` already names the categories coding needs, and three of them are unused today:

- `READ_WORKSPACE`: used only by Radio's task tools.
- `CREATE_FILE`, `TERMINAL`: defined, given defaults in every safety profile, and listed as mutating in `agent_catalog.py`, but no tool uses them.
- Under Balanced, `TERMINAL` is Ask; under Careful it is Deny.

The four safety profiles (Careful, Balanced, Power User, Locked Down) and the decisions (allow, ask, preview required, deny) carry straight over. An agent spec can never grant itself `allow` on a mutating category; `agent_catalog.py` and `quill/tools/agent_lint.py` both enforce that.

### 1.3 Developer features QUILL already has

| Area | Where | Notes for coding |
|---|---|---|
| Local git | `quill/core/local_git.py`, `quill/ui/local_git_dialogs.py`, `main_frame_local_git.py` | Uncommitted changes as a file list with a spoken diff; merge conflicts walked hunk by hunk; an interactive rebase as a real list; blame; stash; bisect. This is the best starting point for multi-file review. |
| Worktrees | `quill/core/git_worktree.py`, `main_frame_worktrees.py` | Written for exactly the accessibility reason we need: a branch switch never rewrites the file under your cursor. |
| GitHub | `quill/core/github/*`, `github_pr_diff_dialog.py` | PR diffs as a file list with QUILL's own spoken compare ("Difference 2 of 5. Text changed at line 41."). |
| Search in files | `quill/core/file_search.py`; QUILL `main_frame_search.py`, Lite `lite_file_search.py` | A folder-wide search both editors share. |
| Compare | `quill/core/compare_service.py` | Next and previous difference, announced. |
| Restore points | `quill/core/restore_points.py` | Content-addressed snapshots per saved document. |
| SSH editing | `quill/core/ssh/*`, `main_frame_ssh.py` | Edit over SSH, `RejectPolicy` by default. |
| Developer Console | `main_frame_devtools.py`, `quill/core/scripting.py`, `quill/core/python_sandbox.py` | Python and TypeScript; the sandbox uses a Job Object and an import guard. |
| Code-ish editing | `code_folding.py` (spoken state, never hides text), `indent_infer.py`, `token_nav.py`, `intellisense.py`, `emmet.py` | Helpful, but there is no language server, no lint and no build. |
| Quillins | `quill/core/quillins/*` | Python and Node runtimes, out of process. Third-party Quillins are locked off because, as `host_worker.py` says honestly, process isolation "is NOT an OS-level sandbox". |

What does not exist, checked by searching the tree:

- **No terminal.** Nothing in `quill/ui` hosts a shell.
- **No project or open-folder concept.** There is no file tree, no project root, no recent projects. Search in Files asks for a folder each time.
- **No build, run or test command,** and no problems list for code. "Recent Problems" (`problem_log.py`) is Radio and Cast's failure log, not lint.
- **No code surface.** The memory note about a Notepad++-style STC surface is out of date; no `wx.stc` control remains in `quill/ui`. QUILL edits code in its ordinary text control, which is what screen readers handle best.

### 1.4 QUILL Lite

QUILL Lite has the document task (Ctrl+3, `quill/core/lite/commands_ai.py`), Choose Your AI, Search in Files (Ctrl+Alt+Shift+F) and Replace in Files. It has no git, GitHub, SSH or console. That is fine: the family rule is that Lite may never be **ahead** of QUILL. Lite being behind on developer features is allowed, and it is consistent with Lite being the editor-only sibling.

### 1.5 Two defects found on the way

- **The Claude pack does not do what its docstring says.** `quill/ai_packs/claude.py` runs the Claude Agent SDK "text-only" with `ClaudeAgentOptions(allowed_tools=[])`. Anthropic's permissions page says `allowed_tools` only pre-approves; it does not hide anything. To remove a built-in tool you name it in `disallowed_tools`, and `disallowed_tools=["*"]` removes them all. In practice recent Claude Code starts in `default` mode and denies unapproved calls when there is no callback, so the risk is refusals and wasted tokens rather than writes. Worth a small fix whatever else happens. Source: https://code.claude.com/docs/en/agent-sdk/permissions.md
- **Review AI Changes is tuned for prose.** Its word-level detail ("changed 'quick' to 'rapid'" with the sentence around it) is exactly right for writing. Code needs line numbers, indentation spoken as a count, and a token-level diff rather than a sentence-level one. See section 5.4.

### 1.6 The honest one-paragraph answer

Today, in either editor, an agent can work on **the one document you have open**: read it, plan, propose patches you review word by word, and run a few safe editor commands. It cannot see the rest of your project, make a new file, or run your code or your tests. So a single-file fix in a script works now. A real coding task ("add a --verbose flag and a test for it") does not.

## 2. What agentic coding in QUILL should mean

Here is the experience, written from the chair of someone using JAWS or NVDA with a braille display. Everything below is the target, not the present.

### 2.1 A walk through one task

1. **Open a project.** File, Open Project Folder. A project is a folder. QUILL says nothing extra; the title bar now names the project, and the status bar has a Project cell. If the folder is a git repository, the Project cell says the branch.
2. **Ask.** Ctrl+3 opens the task window, already on the project. You type: "Add a --verbose flag to cli.py that prints each file as it is processed, and add a test."
3. **Hear the plan.** The agent reads around first (no questions asked for reads inside the project), then writes its plan into the transcript under a heading. The app says one thing: "The plan is ready. 4 steps." Focus does not move. You read the plan with your reader, or press the window's Plan key to land on it.
4. **Approve or change the plan.** Go ahead, or type a change ("don't touch the README") and press Enter.
5. **Review the changes.** When the agent has edits for this turn, the Review Changes window opens on a list: "cli.py, 3 changes", "tests/test_cli.py, new file, 24 lines". Enter on a file walks its changes one at a time with line numbers. You accept or reject each change, or a file at once. Nothing reaches disk that you have not accepted.
6. **Approve a command.** The agent wants to run the tests. A small dialog says, in one sentence, what and why: "Run pytest -q tests/test_cli.py in your project folder, to check the new test." The exact command is in a read-only field below. Allow once, Always allow this command in this project, or Don't allow.
7. **Hear the result.** "Tests: 12 passed, 1 failed: test_verbose_prints_names." The full output is a read-only document you can open with one key and read like any other.
8. **Iterate.** The agent fixes the failure; you review the one-line change; the tests pass. "Tests: 13 passed."
9. **Finish.** The closing summary is spoken once and brailled: "Done. Changed cli.py and added tests/test_cli.py. Ran the tests twice; they pass now." If you change your mind, Undo Last Turn puts every file back as it was before that turn.

### 2.2 The promises

These are the promises a blind learner can rely on. Each one becomes a test or a gate (section 7).

- **Nothing happens silently.** Every write is reviewed as text first. Every command is approved first, unless you put it on this project's allow list yourself.
- **Nothing moves your focus** except an approval you are already waiting on in the task window. If you are writing in another document, the task waits and says so once (section 5.3).
- **Nothing chatters.** No streaming text is read at you. The app speaks outcomes it alone knows: the plan is ready, the task needs you, the tests passed or failed, the task ended.
- **Everything is text.** Plans, changes, command output and results are text you can read, search and braille. No diagrams, no colour-only state (decision 13 of `codex.md`).
- **One undo per turn.** Undo Last Turn reverses everything a turn changed, across every file, and says what it did.
- **You can stop at any moment,** from anywhere in QUILL, and the running command dies with it.
- **The record is navigable.** The transcript is a document with a heading per turn and sub-headings for Plan, Changes, Commands and Result, so H and Shift+H (or QUILL's heading keys) move through it.
- **Errors are plain language.** "The test command was not found. Is pytest installed in this project's Python?" rather than a stack trace. The raw text is one key away for anyone who wants it.

## 3. Engines

Same marking as `codex.md`: **Confirmed** means read on the cited page on 2026-11-02 (or confirmed in `codex.md` on 2026-10-31 and still current), **Inferred** means it follows from what was read, **Unknown** means no primary source.

### 3.1 GitHub Copilot (SDK and CLI): the primary path

What matters for coding:

- **Confirmed (codex.md 2B):** the Python SDK `github-copilot-sdk` drives the same agent runtime as Copilot CLI. Custom tools are plain Python handlers. `available_tools` is an allowlist. A permission callback receives every request by kind: shell, write, read, url, mcp, custom-tool, memory, hook. Hooks run before and after tool use. It is GA with semver, and it is changing owner to Microsoft. Copilot Free is included. Usage is reported per call and per account.
- **Confirmed:** the CLI's own controls are two layers: `--available-tools` and `--excluded-tools` decide which tools the model sees; `--allow-tool` and `--deny-tool` decide which run, with patterns such as `shell(git:*)` and `write(path)`, and "Deny rules always take precedence over allow rules". `--allow-all` (also called `--yolo`) turns on everything including all paths and URLs. Source: https://docs.github.com/en/copilot/how-tos/copilot-cli/allowing-tools
- **Confirmed:** Copilot CLI can run as an Agent Client Protocol server (`copilot --acp --stdio`), in public preview; options are fixed at server start. Source: https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server
- **In the tree:** the bundled runtime, the pin, the per-app sign-in with real client ids, the tool session with Stop.

Why it is the primary path:

- It is already built and bundled. Project tools are new registry entries, not a new engine.
- It costs the user nothing on Copilot Free, and it does not cost Jeff anything.
- Tool handlers run in our own Python, so review, checkpoints and command running are QUILL code we can test.
- Copilot's models are strong at code, and the person can choose among them where their plan allows.

### 3.2 Codex (app-server): the second engine

- **Confirmed (codex.md 2):** app-server is a JSON-RPC child with threads, turns, streaming, approvals and app-defined `dynamicTools` (experimental). It runs on the person's ChatGPT plan through Sign in with ChatGPT, which is a preview. The plan refuses hosted MCP, Code Interpreter and the Files API, and the terms say "use the user's plan only for the application they connected".
- **In the tree:** built and bundled, read-only sandbox, untrusted approvals, built-ins off.
- **Inferred from secondary sources, to verify:** Codex's own sandbox has modes `read-only`, `workspace-write` and `danger-full-access`, with network off by default in `workspace-write`; Windows sandboxing is described as experimental, using a restricted token. The official security page points to separate sandboxing pages that refused automated reads today. Sources: https://developers.openai.com/codex/security and the secondary summary at https://codex.danielvaughan.com/2026/05/08/codex-cli-permission-profiles-sandbox-modes-security-layers/

Recommendation: keep Codex on QUILL's tools with its own sandbox at `read-only`, exactly as for document tasks. Codex models are trained on their own `apply_patch` and shell tools, so give our edit tool a patch-shaped input (section 4.2) to play to that training. Revisit Codex's own `workspace-write` sandbox only if G3-style measurements show our tools are clearly worse for it.

### 3.3 Claude (Agent SDK): own key only, later

- **Confirmed:** the Agent SDK embeds Claude Code's loop, tools, permissions, sessions and hooks in Python or TypeScript. Source: https://code.claude.com/docs/en/agent-sdk/overview
- **Confirmed:** "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK." Same page. So QUILL cannot offer "use my Claude subscription" the way it offers ChatGPT and Copilot; it is an API key, billed per token.
- **Confirmed:** permission modes `default`, `dontAsk`, `acceptEdits`, `bypassPermissions`, `plan` and `auto`; a `can_use_tool` callback; deny rules beat everything; "Auto-approved tools never reach `canUseTool`". Source: https://code.claude.com/docs/en/agent-sdk/permissions.md
- **Confirmed:** branding rules: QUILL may say "Claude Agent" or "Powered by Claude", never "Claude Code". Same overview page.

Recommendation: after Copilot and Codex, as a My own key provider (decision 20 of `codex.md` already plans Anthropic there). Run it with `disallowed_tools=["*"]` plus QUILL's tools as an in-process MCP server, `permission_mode="default"`, and our approver in `can_use_tool`.

### 3.4 OpenAI Agents SDK

Already a pack (`quill/ai_packs/openai_agents.py`, key-billed, text-only). It is a framework for building our own loop rather than a coding runtime. Lowest priority; the native loop below covers the same ground for keyed providers.

### 3.5 Local models through Ollama: practice mode

- **In the tree:** `quill/core/ai/tool_loop.py` is a provider-neutral multi-step loop over the same gateway; `ollama_capabilities.py` discovers models.
- **Inferred, from general knowledge, to verify per model:** some local models handle tool calls (Qwen and Llama families), but small models on a typical laptop are weak at multi-file coding, slow, and prone to calling tools wrongly.

Recommendation: offer it, honestly labelled "Practice, on this computer. Nothing is sent. Slower and less capable." It is valuable for learners who cannot or will not sign in to anything, and for classrooms. Never the default.

### 3.6 The free AI: no

The free gateway is paid for by Jeff. A coding task makes many model calls a turn, with long file contents. Recommendation: no agent on the free AI. It keeps answering single questions about a selection ("what does this function do?") as today, within its limits. Decision 3.

### 3.7 A watch item: the Agent Client Protocol

**Inferred from the ACP design as published, to verify before any work:** ACP lets an editor host any compliant agent, and the editor, not the agent, can provide file reads and writes, terminals and permission prompts. Copilot CLI speaks it now (3.1). If ACP matures and Codex and Claude adapters stay current, QUILL could become an ACP client: one integration, many agents, and file writes still routed through our review. It is in public preview for Copilot, and its permission prompts would still need our accessible UI. Recommendation: do not build on it yet; re-read it when Phase 5 starts.

### 3.8 Summary

| Engine | Billing | Tools in QUILL | Status | Role |
|---|---|---|---|---|
| Copilot SDK | Copilot plan, Free included | ours, Python handlers | GA, bundled | primary |
| Codex app-server | ChatGPT plan | ours, dynamicTools | preview, bundled | second |
| Claude Agent SDK | own API key | ours, as in-process MCP | GA | later |
| Ollama, native loop | none | ours | shipped loop | practice |
| Free AI | Jeff | none | shipped | not for agents |

## 4. Architecture

### 4.1 One principle: QUILL owns the tools

There are two ways to give an agent a project.

- **A. QUILL's own tools.** The vendor's shell and file tools stay off. The model gets `project.list`, `project.read`, `project.search`, `project.edit`, `project.create`, `project.run` and a few more, all QUILL code.
- **B. The vendor's tools in the vendor's sandbox,** with QUILL answering permission callbacks. Faster to start, and the models know those tools well. But edits land on disk before we can show them, approvals arrive in two vendor shapes, the sandboxes differ (Copilot's CLI has none of its own on Windows that we can rely on; Codex calls its Windows sandbox experimental), and the two engines would behave differently in front of the person.

**Recommendation: A**, and it is what `codex.md` already decided for documents ("the vendor's own tools off", "QUILL's tools only"). It is the only way to promise that every change is reviewed as text before it reaches disk, under every engine, and to test that promise.

### 4.2 The project tools

New, in `quill/core/ai/project_tools.py` (wx-free, strict-typed), registered with `FamilyToolRegistry.register_app("project", ...)`. Names are namespaced like `doc.read_outline`; the wire names are `project_read` and so on.

| Tool | Category | Asks? | What it does |
|---|---|---|---|
| `project.list` | READ_WORKSPACE | no | files under a folder, honouring `.gitignore`, with sizes; hides secret files (4.4) |
| `project.read` | READ_WORKSPACE | no | a file or a line range, with line numbers; refuses binaries and secrets |
| `project.search` | READ_WORKSPACE | no | text or regex across the project, over `file_search.py` |
| `project.outline` | READ_WORKSPACE | no | functions and classes in a file, where we can tell cheaply |
| `project.git_status` | READ_WORKSPACE | no | branch, changed files, over `local_git.py` |
| `project.edit` | MODIFY_DOCUMENT (preview) | review | a change to an existing file, as search-and-replace blocks or a unified diff |
| `project.create` | CREATE_FILE (preview) | review | a new file with its full text |
| `project.delete` / `project.rename` | CREATE_FILE | always asks | never under a "for this task" grant |
| `project.run` | TERMINAL | asks, or the allow list | one command in the project folder (section 4.6) |
| `project.plan` | none | no | records the agent's plan as a list, so the window can read it back |
| `project.ask_person` | none | no | a clarifying question shown in the transcript, answered in the instruction field |

Reads inside the project do not ask, which matches `ApprovalGate`'s rule that reads inside the app's own scope are free. The person can tighten that to "ask" with the Careful profile.

Two details carried from the document tools:

- **Edits do not touch disk when proposed.** `project.edit` and `project.create` add to the turn's **change set**. The change set is what Review Changes shows. Only accepted changes are written, and then all of them together.
- **The model is told the truth.** The tool result says exactly what happened: "Accepted 2 of 3 changes in cli.py; the person rejected the change at line 40." The closing summary is built from the registry's record, never from the model's claims, as `summarize_outcome` already does.

### 4.3 Where things live

```
quill/core/ai/project.py            Project: root, ignore rules, secret rules, path checks (new)
quill/core/ai/project_tools.py      the tools above, wx-free (new)
quill/core/ai/change_set.py         a turn's proposed edits; apply all or some, atomically (new)
quill/core/ai/checkpoints.py        private snapshots per turn; Undo Last Turn (new)
quill/core/ai/command_runner.py     run one approved command: job object, timeout, scrubbed env (new)
quill/core/ai/test_summary.py       output to one sentence for pytest, unittest, jest, dotnet, cargo, go (new)
quill/core/ai/project_task.py       ProjectTaskRunner, the DocumentTaskRunner shape (new)
quill/core/ai/project_task_words.py every sentence the window says (new)
quill/ui/project_review_dialog.py   multi-file Review Changes (new; reuses diff_review and compare)
quill/ui/project_task_commands.py   the commands, a mixin shared through the hosted-AI layer (new)
quill/ui/agent_window.py            extended: plan, changes and output reachable by keys (existing)
```

Everything under `quill/core` is wx-free and in `mypy` scope. The UI pieces follow the hosted-AI pattern: a mixin both editors could reach, with QUILL's adapter still having no commands of its own.

### 4.4 The project boundary

`quill/core/ai/project.py` decides what the agent may see. Rules, each with a test:

- **Inside the root only.** Every path is resolved and must stay under the project root after resolving symlinks and junctions. `..`, absolute paths, UNC paths, device names and alternate data streams are refused.
- **Secrets are invisible.** Never listed, never read, never sent: `.env` and `.env.*`, `*.pem`, `*.key`, `*.pfx`, `id_rsa*`, `.ssh/`, `.aws/`, `.git/` internals, `*.kdbx`, `credentials*`, `secrets*`, token files, and anything `.gitignore` marks plus a name matching those patterns. `project.list` says "3 files hidden by QUILL because they look like secrets", so the model knows something is there and can ask the person.
- **Content scrubbed on the way out.** `quill/stability/redaction.py` runs over every file excerpt sent to the model, catching keys that live in ordinary files.
- **Size caps.** A read returns at most a set number of lines; the model asks for ranges. Keeps cost down on Copilot and on plans.
- **Binary files** are described ("PNG image, 48 KB"), never sent.

### 4.5 Checkpoints and undo

A turn can touch many files, so one Ctrl+Z in one document is not enough.

- **Before each turn,** QUILL snapshots every file the turn might change, into a private store in app data. Recommended mechanism: a shadow git repository (`git --git-dir=<app data>/ai/checkpoints/<project-hash> --work-tree=<project>`), using the git QUILL already locates (`git_binaries.py`). It never touches the person's own `.git`. For a folder without git, the same works; for a machine without git, fall back to content-addressed copies in the style of `restore_points.py`.
- **Undo Last Turn** restores those files and removes files the turn created, then says once: "Undid turn 3. cli.py and test_cli.py are back as they were."
- **Undo is refused, with a reason,** if the person has edited one of those files since: "cli.py has changed since the agent's turn. Undo would lose your edits. Open the comparison?" Compare opens on the two versions.
- **The person's repository is untouched.** No commits, branches, stashes or pushes, unless the person asks the agent for one in words and approves the git command like any other (decision 8).
- **Optional: work on a worktree.** For a git project, "Do this task on its own branch" creates a worktree through `git_worktree.py`, so the files the person has open are never rewritten underneath them. That is the accessibility argument `git_worktree.py` already makes. Recommended as an option, not the default, because a second folder is one more thing to understand when learning.
- **Checkpoints are local, bounded and swept** like `agent_workdir.py`: kept for the session and the last few tasks, never sent anywhere.

### 4.6 Running commands

`project.run` is where the real risk is, and where Windows gives us the least help.

**How a command runs.**

- Through `quill/stability/safe_subprocess.py`, in a Windows Job Object so Stop kills the whole process tree (the pattern `python_sandbox.py` already uses).
- The working folder is the project root (or the task's worktree).
- A minimal environment: the scrubbed child environment, with every token removed (`scrubbed_child_env()` already removes the Copilot and GitHub tokens and API keys) plus PATH and the project's own variables. QUILL's own `QUILL_*` variables are not passed.
- A timeout, chosen per command kind, with a spoken notice before it is enforced: "The tests have run for 5 minutes. Keep waiting, or stop them?"
- Output captured to a file, not streamed to the reader. The tool result to the model is trimmed: the summary line, the failures, and the last part of the output.

**What QUILL cannot do on Windows, said honestly.** QUILL cannot stop an approved command from reaching the network, reading files outside the project, or doing anything the person's own account can do. A real OS sandbox (AppContainer, a VM, Windows Sandbox) needs admin rights or features many users do not have. So the approval is the safety boundary, and the approval must be clear. That is why commands ask by default and why the allow list belongs to the person, not the repository.

**The approval.** The existing approval dialog, with one more read-only field:

- one sentence: what will run, where, and the agent's reason in its own words;
- the exact command text, in a read-only field the person can arrow through and braille character by character;
- a warning line only when it applies, worked out by QUILL, not the model: "This may reach the internet." for installers and network tools (`pip install`, `npm install`, `curl`, `git push`, `Invoke-WebRequest`), "This deletes files." for `del`, `rm`, `Remove-Item`, `rmdir`, "This runs outside the project." for a path that leaves the root;
- buttons: Allow once (default, Enter), Always allow this command here, Don't allow (Escape). "Always" is offered only for commands without a warning line.

**The allow list.** Per project, stored in QUILL's app data keyed by the project path, never in the repository. A cloned repository must not be able to pre-approve its own `rm -rf`. The person can see and edit the list in the project's settings. Matching is by exact command text or a simple prefix the person typed ("pytest"), never by pattern the model proposed.

**Never, in version one:** `git push`, publishing (`npm publish`, `twine upload`), anything with `--force` against a remote, changing system settings, and running a command the agent wrote into a new script in the same turn without that script first going through review. The agent gets "The person keeps this step for themselves" and can tell them how.

**Test results as a sentence.** `test_summary.py` reads the output of common runners and produces one line: "Tests: 41 passed, 2 failed: test_parse_date, test_empty_file." or "Build failed: 3 errors. The first is in parser.py line 88: name 'tokn' is not defined." Unknown runners get "The command ended with exit code 1. The last error line was: ..." That sentence is what is spoken. The full output is a read-only document one key away.

### 4.7 Instructions in the repository

Many projects carry instructions for agents: `AGENTS.md`, `.github/copilot-instructions.md`, `CLAUDE.md`. They help a lot, and they are also the easiest place to hide a prompt injection. Recommendation:

- The first time a project is used, QUILL says which files it found and asks once: "This project has instructions for AI agents in AGENTS.md. Use them for tasks here?" Yes, No, or Read Them First (opens the file read-only).
- Content in any project file is data. The task instructions say so, and the approvals stay the backstop: nothing a file says can approve a command or a write.

### 4.8 Threading and stopping

As today: the engine on a `QuillTaskManager` worker, approvals through `UiThreadBridge`, every wx touch with `wx.CallAfter`. Stop cancels the session, releases any open question as Don't allow, and kills the command's job object. A new global **Stop Agent** command reaches Stop from any QUILL window, so the person does not have to find the task window first.

### 4.9 How one turn flows, inside

For whoever builds it, the order of things in one turn:

1. The person presses Enter in the instruction field. `ProjectTaskRunner.start` runs on the UI thread and does nothing slow.
2. On the worker: `checkpoints.begin_turn` records the project's state; the change set is empty.
3. The engine plans. `project.plan` records the steps; the window adds them under the turn's Plan heading and speaks "The plan is ready."
4. Reads run without questions. Each one is a line in the activity log and, briefly, in the transcript ("Read cli.py, lines 1 to 120").
5. Edits go into the change set. Nothing is written.
6. When the engine wants to run a command, or the turn ends with edits pending, the turn pauses for review. Review Changes opens (or the "waiting for you" notice plays, if the person is elsewhere).
7. Accepted changes are written together. The tool result tells the engine exactly what was accepted.
8. A command, once approved, runs in its job object. Its result sentence is spoken; its output becomes a document; the trimmed result goes back to the engine.
9. Steps 4 to 8 repeat until the engine ends the turn, the person presses Stop, or a cap on steps is reached ("The task stopped after 40 steps. Continue?").
10. The closing summary is built from the registry's record and spoken once. `checkpoints.end_turn` keeps the snapshot for Undo Last Turn.

## 5. Accessibility, in depth

### 5.1 What makes VS Code and Copilot hard

Jeff knows this from the inside; this is the list the design answers. VS Code's accessibility team has done serious work (accessible view, accessibility signals, accessible diff viewer), and many blind developers use it well. The trouble is mostly the number of moving parts, and it lands hardest on people who are learning.

- **Too many places.** Editor groups, side bar, panel, terminal, chat view, inline chat, the problems list, notifications, the status bar, the command palette. Each has its own keys and its own idea of focus. You have to know where you are before you can do anything.
- **Focus moves under you.** A diff editor opens, a notification takes focus, a chat response steals the cursor, a quick pick appears. Each is announced differently, or not at all.
- **Ghost text.** Inline suggestions are visual by nature. With a reader they are either silent or a constant interruption, and accepting one by accident with Tab is easy.
- **Streaming chatter.** A chat answer that arrives token by token is either read in fragments or not at all, and you cannot tell when it is finished without checking.
- **Side-by-side diffs.** Two columns of code with coloured gutters. The accessible diff viewer helps, but you have to know it exists and remember its key.
- **The terminal.** A wall of output, with prompts, colours and progress bars, that the reader may or may not echo. Finding the one failing test means reviewing line by line.
- **Agent mode multiplies it.** The agent edits several files, opens them, runs commands in the terminal, and keeps going. A sighted user watches it happen. A blind user hears a stream of focus changes and has to reconstruct what happened afterwards.
- **Settings as the cure.** Most of these are fixable with a setting, which means the learner has to learn the settings before they can learn to code.

### 5.2 QUILL's answers

| Pain | QUILL's answer |
|---|---|
| Too many places | One task window: conversation, status, instruction, and keys to reach the plan, changes and output. Everything else is a document or a dialog you open on purpose. |
| Focus jumps | The agent never moves focus. Only an approval in the task window you are using takes focus, and only because you are waiting for it (5.3). |
| Ghost text | None. QUILL does not do inline completion for agents. Suggestions arrive as reviewable changes. |
| Streaming | The transcript fills silently. The app speaks outcomes: plan ready, needs you, tests passed or failed, done. |
| Side-by-side diff | A list of files, then one change at a time, read as text with line numbers (5.4). |
| Terminal walls | One sentence for the result; the full output as a read-only document with QUILL's own navigation. |
| Reconstructing what happened | The transcript is a document with a heading per turn; each turn lists its changes and commands. |
| Settings as the cure | Verbosity by design: say less rather than make the person configure how much less (GATE-13's own principle). |

### 5.3 Focus and interruptions

- **In the task window,** an approval opens as today, over the window, with focus on its sentence.
- **Elsewhere in QUILL,** the task does not pop a dialog over the person's typing. It plays the "needs you" sound once, speaks once: "The project task is waiting for you. Press Ctrl+3 to answer.", and waits. The status bar's Project cell says "waiting". Ctrl+3 brings the task window forward with the question open. This needs a check in the existing window: today an approval opens wherever the task is running.
- **Outside QUILL** (another app has focus), nothing is spoken by QUILL at all; the sound plays only if the person has turned on background sounds. When they come back, the status cell and Ctrl+3 tell the story.
- **Stop is always one key away,** in the window and globally (4.8).

### 5.4 Multi-file review that reads well

The new Review Changes window for a project turn is a list over detail, the shape `UncommittedChangesDialog` and the PR diff viewer already use and that readers handle well.

- **The file list.** One row per file, a whole sentence: "cli.py, changed, 3 changes", "tests/test_cli.py, new file, 24 lines", "old_util.py, deleted". Each row has a check box state for "take this file". Space toggles. Enter opens the file's changes.
- **One file's changes.** The existing Review AI Changes engine, with a code mode:
  - each change says where it is: "Change 2 of 3, lines 40 to 44, in function parse_args";
  - indentation is spoken as a count, once, when it changes: "indent 8";
  - a token-level word diff for code ("changed 'tokn' to 'token'"), with the line as context instead of a sentence;
  - new files read as plain text with line numbers;
  - Accept, Reject, Accept All in File, Reject All in File, Back to Files.
- **Braille.** One row, one line. Line numbers lead, so a braille reader can jump by number. No column layouts.
- **Applying.** Accept Turn writes every accepted change at once, through `write_json_atomic`'s cousin for text (temp file and replace), and only after the checkpoint is safe. Files open in QUILL reload with the person's cursor kept where it was and one spoken line: "cli.py was updated by the task."
- **Gate (new, GATE-PROJECT-REVIEW):** a test proves that no project tool writes to disk except through the change set, and that a rejected change never reaches disk (section 7).

### 5.5 The transcript as a document

Rather than a list control or a web view, the transcript is a read-only QUILL document, so everything QUILL already does for reading works on it: heading navigation, find, bookmarks, braille, read aloud and export. Shape:

```
# Project task: add a verbose flag
## Turn 1: you asked
Add a --verbose flag to cli.py ...
### Plan
1. Read cli.py and its tests.
2. Add the flag to the argument parser.
3. Print each file name when the flag is on.
4. Add a test.
### Changes
- cli.py: 3 changes, all accepted.
- tests/test_cli.py: new file, accepted.
### Commands
- pytest -q tests/test_cli.py: 12 passed, 1 failed.
### Result
...
## Turn 2: you asked
...
```

Saved to the project's task history in app data, never into the repository unless the person saves it there. Exportable as Markdown.

### 5.6 Speech, braille and sound

- **Speech only for what the reader does not say (GATE-13).** Never: the window opening, a focus move, a list selection, a dialog's own text. Only: plan ready, needs you, a command's result sentence, a turn applied, undone, stopped, done, could not start.
- **Braille parity (GATE-BRAILLE).** Every spoken line goes through the announcement service, so it is brailled on the same path.
- **Sound cues** through the existing sound scheme and `action_feedback`: task started, needs you, command finished (a different cue for pass and fail), task done, error. No repeating sound while it thinks; silence means working, and the status line says "Working" for anyone who checks. Failures and counts are always spoken, as `action_feedback.py` already rules: no tone carries "2 failed".
- **Reduced motion and visuals** do not apply much here, because nothing animates; the progress state is text.

### 5.7 F1 everywhere

Every control in the task window, the review window and the command approval gets an inline `SetHelpText` at construction, and each surface gets an authored purpose in the shared help engine. The command field's help says what the warning lines mean. New surfaces join the editors' help audits and `docs/f1-help-reference.md` regenerates.

### 5.8 Keys, under the family rules

- **Ctrl+3 stays the front door** (rule 2: the command both products have keeps the chord). With a project open it starts a project task; with no project it stays a document task. One key, one window, and the status line says which.
- **Inside the window,** access keys for Plan, Changes, Output, Undo Last Turn, Stop (Alt+T today), following GATE-14: OK, Cancel and Close carry none, and no letter is claimed twice.
- **New global commands** (Open Project Folder, Stop Agent, Undo Last Agent Turn, Open Command Output) need keys or written reasons (rule 8). They are QUILL-only at first, so rule 6 does not force plain chords, and rule 9 lets a once-in-a-while command take a longer key. The actual chords must be checked against `DEFAULT_KEYMAP`, `DEFAULT_ALIASES`, Lite's tables, `APP_KEYMAPS` and the family-wide keys before anyone writes them down; this plan proposes none, on purpose, because a chord guessed in a plan is how the documentation-chord gates were born.
- Every menu row shows its key (the menu accelerator rule), through `_menu_label`.

### 5.9 Coach mode, for people learning

This is the part that could make QUILL matter for blind people learning to code, rather than only being a safer VS Code.

- **Explain this turn.** After any turn, one command asks the agent to explain what it changed and why, in plain words, as a new section in the transcript. "I added a parameter called verbose to the parser. argparse turns --verbose into args.verbose, which is True when you type the flag."
- **Why this change?** In the review window, a key on any change asks why, and the answer lands under that change.
- **Coach mode.** A task setting where the agent does not edit at all. It explains, points to file and line ("Look at cli.py line 40: the loop over files"), and suggests what to type, and the person makes the change themselves. QUILL's ordinary editing does the rest. This is how a tutor works, and it costs very little.
- **Plain-language errors.** When a command fails, the agent is asked for one sentence on what the error means before it tries a fix. The raw output is still one key away.
- **Guided first task.** QUILL's tutorial engine (the shared one behind the 88 lessons) gets a short lesson: open a sample project, ask for a small change, review it, run the tests, undo the turn.

### 5.10 What QUILL will deliberately not do

- No inline completion or ghost text.
- No file tree pane. `project.list` and a quick-open list are enough, and a tree is one more place.
- No integrated terminal for the person. Commands run on the agent's behalf, with approval, and land as documents. A person who wants a shell already has one.
- No autonomous "keep going until done" mode in version one. Every turn ends with the person.

## 6. QUILL and QUILL Lite

### 6.1 The rule

QUILL Lite may never be ahead of QUILL. If Lite needs something, it goes into the shared package and QUILL reaches it in the same change (`CLAUDE.md`, family rule 10).

### 6.2 What each gets

| Capability | QUILL | QUILL Lite |
|---|---|---|
| Document task (today) | yes | yes |
| Project tasks, read-only questions | Phase 1 | decision 1 |
| Project tasks with edits and review | Phase 2 | decision 1 |
| Commands and tests | Phase 3 | decision 1 |
| Coach mode on a document | Phase 4 | yes, same change, because it needs no project |
| Git-aware extras (worktree option, branch in status) | yes | no; Lite has no git |
| Who sees any of the rows above beyond document tasks | the Developer profile only (6.4) | the Developer profile only (6.4) |

### 6.3 Shared code

All of `quill/core/ai/project*.py`, `change_set.py`, `checkpoints.py`, `command_runner.py` and `test_summary.py` are shared and wx-free. The review window and the commands live in the hosted-AI style shared UI, so Lite can reach them later through its own command table without a second implementation, and so a test can assert there is only one. Recommendation for decision 1: project tasks in QUILL only for now; Lite keeps document tasks. Lite's identity is the small editor, and a developer feature there should be Jeff's choice, not a default.

### 6.4 The Developer profile: developer features only when chosen (decided by Jeff, 2026-11-04)

Coding features are switched on by choosing a **Developer** profile, and only
then. This holds in both editors. Someone who writes letters, posts or books
never meets a project task, a command runner or a test summary in a menu, the
palette or a tutorial.

**QUILL:**

- **The existing profile is renamed.** "Developer and Power Text" becomes
  **Developer**. It keeps the regular-expression, cleanup and analysis tools
  it has today, and is the only profile that turns on the coding features:
  - Do a Project Task, and the review window;
  - commands and tests;
  - checkpoints;
  - coach mode on a project;
  - the git extras.
- **The developer features already in QUILL move behind it:** the shell, Git
  and GitHub, Codespaces, IntelliSense, the Developer Console and agent
  standards lint. They stay available, but are off in every other profile
  rather than merely quiet.
- **One new feature id, `core.developer`, groups them.** Each developer
  feature depends on it (the catalogue's `dependencies`). Turning it on by
  hand in Manage Individual Features is the escape hatch for someone who wants
  one tool without the whole profile, and the dependency chain (FLAG-1) means
  a profile cannot half-enable them by accident.
- **Full Quill** also turns them on, because its promise is everything.

**QUILL Lite:**

- **A fifth profile, Developer,** joins Recommended, Everything, WordPad and
  Notepad. It is Recommended plus one new area, **Coding**: Do a Project
  Task, the review window, commands and tests, and coach mode. It uses the
  same shared code as QUILL, reached through Lite's command table.
- **Coding is off in every other profile,** Everything included, so
  Everything means every writing area. Its description says so, and says the
  Developer profile is where coding lives.
- **This answers decision 1 (section 9):** project tasks come to QUILL Lite,
  but only in the Developer profile. QUILL gets them in the same change, which
  keeps the rule in 6.1.

**What both editors share:**

- **Choosing the profile is the opt-in,** so no feature asks again whether you
  want developer tools. Leaving the profile turns them off and hides their
  menus. Open project tasks finish first, and the person is told.
- **The profile description is the plain promise:** "Everything in
  Recommended, plus tools for writing code: project tasks with an AI, running
  commands and tests, and undo for every change an AI makes."
- **Tests:**
  - a gate asserts that no developer command is visible, in the menus or the
    palette, in any non-Developer profile;
  - another asserts that both editors' Developer profiles turn on the same
    shared commands.

## 7. Phased plan

Sizes: small is days, medium is one to two weeks, large is several weeks, for the way this repository is usually worked.

### Phase 0: groundwork (small)

- Fix the Claude pack's `allowed_tools=[]` to `disallowed_tools=["*"]` (1.5), with a fake-SDK test.
- Close the open screen-reader checks for Do a Document Task with NVDA, JAWS and Narrator. Everything after this builds on that window, so its acceptance matters first.
- Decide the open questions in section 9.
- Tests: the existing agent window and document task tests stay green; one new test for the Claude options.

### Phase 1: a project, and read-only questions (medium)

- `project.py` with the boundary and secret rules; Open Project Folder; the Project status cell; recent projects.
- `project.list`, `project.read`, `project.search`, `project.outline`, `project.git_status`, `project.plan`, `project.ask_person`.
- Ctrl+3 with a project open: "Ask about this project" works end to end on Copilot. "Where is the date parsed?" "Why might this test fail?"
- Gates and tests:
  - boundary tests: `..`, absolute, UNC, symlink and junction escapes, alternate data streams, device names, all refused;
  - secret tests: a fixture project with `.env`, a key file and `.ssh`; assert none is listed, read or sent, and the "hidden" count is right;
  - redaction runs on every excerpt;
  - GATE-REACH for any new window; F1 sentences; GATE-14 on the window.
- Depends on: Phase 0. Copilot sign-in (client ids exist since #1737) and the bundled runtime in the build under test.

### Phase 2: reviewed multi-file edits and Undo Last Turn (large)

- `change_set.py`, `project.edit`, `project.create`, `project.delete`, `project.rename`.
- `project_review_dialog.py` with the code mode in the diff engine (5.4).
- `checkpoints.py` and Undo Last Turn, with the "you edited since" refusal.
- Reload of open documents after a turn, cursor kept.
- Gates and tests:
  - **GATE-PROJECT-REVIEW** (new): an AST scan that no project tool calls a file-writing API except `change_set.apply`; and a behavioural test that a rejected change never reaches disk;
  - property-style test: apply some hunks, undo the turn, the tree is byte-identical to the checkpoint;
  - partial-failure test: a write that fails half way rolls the whole turn back;
  - the code-mode diff: line numbers, indentation counts, token diffs, with fixtures;
  - UIA checks (CI nightly, never on Jeff's machine, per the memory note): the review list reads one sentence per row; Enter opens a file's changes; accept and reject change the row text.
- Depends on Phase 1.

### Phase 3: commands and test results (medium to large)

- `command_runner.py` (job object, timeout, scrubbed environment, output to file), `project.run`, the command approval with warning lines, the per-project allow list and its editor, `test_summary.py`, Open Command Output, global Stop Agent.
- Gates and tests:
  - environment test: no token, key or `QUILL_*` variable reaches the child;
  - Stop test: a command that spawns a grandchild dies, tree and all, within 2 seconds;
  - warning-line classifier tests over a table of commands;
  - allow-list tests: stored outside the project; a file in the repository cannot add to it; "always" is not offered with a warning line;
  - the never-list (4.6) refuses with the right sentence;
  - test-summary fixtures for pytest, unittest, jest, dotnet test, cargo test and go test, plus the unknown-runner fallback;
  - **network egress:** the command runner gets a reviewed entry of a new kind ("person-approved command") in `quill/tools/network_egress_entries.py`; verify with `pytest tests/unit/tools/test_network_egress_audit.py`, not the module CLI;
  - Safe Mode refuses project tasks, as it refuses the engines (G4).
- Depends on Phase 2, because a command without undo is a risk we should not ship.

### Phase 4: the headed transcript, coach mode and sounds (medium)

- The transcript as a read-only document with headings; export to Markdown.
- Explain This Turn, Why This Change, Coach mode, plain-language errors.
- Sound cues through the scheme; the "waiting for you" behaviour away from the window (5.3).
- Gates and tests: GATE-13's `check_over_announce.py` stays clean; the braille-parity audit classifies every new speech call; the transcript's heading levels never skip (the docs heading rule); the help reference regenerates.
- Coach mode on a single document reaches QUILL Lite in the same change (it needs no project).

### Phase 5: Codex and the other engines (medium)

- Codex on the same project tools, with the patch-shaped `project.edit` input; G3 re-run to record the tools offered.
- Claude through the Agent SDK on the person's own key, if decision 10 says yes: `disallowed_tools=["*"]`, our tools as an in-process MCP server, `can_use_tool` to our approver.
- Ollama practice mode on the native loop, labelled.
- Re-read ACP (3.7).
- Gates: G1 to G5 from `codex.md` for each engine, now with project tools; one scripted coding task as an acceptance test for each engine, judged by the tests in the sample project passing.

### Phase 6: QUILL Lite, only if Jeff decides so (medium)

- The shared commands reach Lite's command table; Lite's behavioural coverage gate (GATE-LITE-COVER) classifies every new handler `covered`; the parity table and settings vocabulary updated.

### Acceptance, every phase

- With NVDA and JAWS, keyboard only, in a sample project: ask, hear the plan, review, approve a command, hear the result, undo the turn, stop mid-command. Narrator for the core path.
- The checks are written into `docs/qa/screen-reader-checks-2026-10.md` (or its successor) in the same change.
- `pytest -q`, `python -m quill.tools.platform_report`, the egress pytest file, and `mypy quill\core quill\io`.

## 8. Risks

- **R1. Command safety on Windows.** No real sandbox without admin features. Mitigation: commands ask by default, warning lines worked out by QUILL, an allow list only the person writes, a never-list, job objects, scrubbed environments, and undo. Say it plainly in the docs and the F1 text.
- **R2. Prompt injection from project files.** A README or a code comment can tell the agent to do something. Mitigation: consent for instruction files, approvals as the backstop, no auto-approval of commands in a new project, and no reads outside the project.
- **R3. Cost and limits.** Coding tasks are large. Copilot Free's allowance goes quickly; plan limits are shared across apps. Mitigation: read caps, show usage in Ctrl+8 and the Usage view as `codex.md` designed, and say up front when a task looks big.
- **R4. Vendor churn.** The Copilot SDK is changing owner; Codex plan sharing is a preview; ACP is a preview. Mitigation: thin adapters over one registry, pinned versions, the engine gates on each upgrade.
- **R5. Confidently wrong code for someone who cannot see it run.** Mitigation: tests as the judge, reviewed changes, coach mode, and summaries built from what happened rather than what the model claims.
- **R6. Review fatigue.** Twenty small approvals a turn would drive anyone to "allow everything". Mitigation: reads never ask, edits are reviewed once a turn as a set, and "for this task" grants exist for edits but never for deletes or warned commands.
- **R7. Scope creep into an IDE.** Every request for a file tree, a terminal pane or a debugger pulls toward VS Code. Mitigation: section 5.10 is part of the plan; changes to it are Jeff's call.
- **R8. Size budgets.** New modules join GATE-11's budgets from the start; nothing new goes into `main_frame.py`.
- **R9. Live checks need real accounts.** As `codex.md` decision 6: Jeff's accounts, never Claude signing in for Jeff.

## 9. Decisions only Jeff can make

Each has a recommended answer. Answer by number.

1. **QUILL Lite.** Decided 2026-11-04: project tasks come to both editors, and only in the Developer profile (6.4).
2. **Primary engine.** Copilot first for project tasks, Codex second? Recommended: yes, matching `codex.md` decision 7.
3. **The free AI.** No coding agent on QUILL's free AI? Recommended: no agent. Single questions about a selection stay as today.
4. **Whose tools.** QUILL's own project tools with the vendors' tools off, rather than the vendors' tools in their sandboxes? Recommended: QUILL's own (section 4.1).
5. **The undo net.** A private shadow checkpoint before every turn, in app data, never in the person's repository? Recommended: yes, always on.
6. **Worktrees.** Offer "do this task on its own branch" for git projects? Recommended: yes, as an option, off by default.
7. **Commands by default.** Ask every time, with a per-project allow list stored in app data and never in the repository? Recommended: yes.
8. **Git from the agent.** May the agent commit or push? Recommended: no pushing and no publishing in version one. A commit only when the person asks for one in words, approved like any command.
9. **Network from commands.** Accept that QUILL cannot block an approved command's network use, and label it instead? Recommended: yes, with the "may reach the internet" line.
10. **Claude.** Add Claude through the Agent SDK on the person's own key, in Phase 5? Recommended: yes, after Copilot and Codex, as a My own key provider. No Claude subscription sign-in: Anthropic does not allow it for third-party products.
11. **Local practice.** Offer Ollama as a labelled practice mode? Recommended: yes, never the default.
12. **Agent instruction files.** Use `AGENTS.md` and `.github/copilot-instructions.md` after asking once per project? Recommended: yes.
13. **Coach mode.** Build coach mode in Phase 4, and make "explain this turn" one key from the start? Recommended: yes. It is the part of this plan that serves people learning to code.
14. **Names.** "Do a Project Task" for the command and "project" for a folder, rather than "workspace" or "repository"? Recommended: yes. Plain words, and a project need not be code: a book manuscript folder works the same way.

## 10. What you could try today

In a build that carries the bundled Copilot runtime and this app's GitHub registration (#1737):

1. Press Ctrl+4 and sign in to My GitHub Copilot (or choose Codex if your ChatGPT plan is signed in).
2. Open a single script, for example a Python file, in QUILL or QUILL Lite.
3. Press Ctrl+3 and ask for a change to that file: "Add a docstring to every function" or "Rename the variable tokn to token everywhere."
4. Allow the step, review the change in Review AI Changes, accept, and press Ctrl+Z in the document if you want it back.

What it cannot do yet: look at other files, create a file, or run your code or tests. For those you still need your own terminal, and QUILL's local git dialogs are a good way to read what changed afterwards (Uncommitted Changes speaks each file's diff).

The eleven checks for this window in `docs/qa/screen-reader-checks-2026-10.md` (from line 1776) are worth running at the same time; Phase 0 depends on them.

## Sources

Read 2026-11-02 unless marked.

- GitHub Copilot CLI, allowing and denying tools: https://docs.github.com/en/copilot/how-tos/copilot-cli/allowing-tools
- GitHub Copilot CLI as an ACP server: https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server
- GitHub Copilot SDK, Python README, authentication, usage and billing: as listed in `codex.md` Sources (read 2026-10-31)
- Claude Agent SDK overview (login rule, branding, capabilities): https://code.claude.com/docs/en/agent-sdk/overview
- Claude Agent SDK permissions (modes, evaluation order, `allowed_tools` versus `disallowed_tools`): https://code.claude.com/docs/en/agent-sdk/permissions.md
- OpenAI Codex security (official entry point; sandbox subpages refused automated reads): https://developers.openai.com/codex/security
- Secondary, unverified summary of Codex sandbox modes and Windows support: https://codex.danielvaughan.com/2026/05/08/codex-cli-permission-profiles-sandbox-modes-security-layers/
- Codex app-server and Sign in with ChatGPT: as listed in `codex.md` Sources (read 2026-10-31)
- In the tree: the modules named in section 1, at commit `295788cf0`

## Decisions made (Jeff, 2026-11-04)

- **1 to 3:** as recommended. Decision 1 is the Developer profile in both
  editors (6.4).
- **4:** QUILL's own project tools are the default. There is also a way to
  see each engine vendor's tools, opt in to them, and choose which to
  enable:
  - per engine;
  - off until checked;
  - remembered per project, in app data;
  - shown in the plan and the transcript.
- **5 and 6:** approved.
- **7:** ask every time, plus two more choices:
  - "Always allow this command in this project", which adds it to the
    allow list;
  - a deliberate per-project bypass, "Run commands without asking". It is
    off by default, confirmed when turned on, and always shown.
- **8 to 11:** approved.
- **12:** support the current industry standards for agent instruction files.
  Research them first (`AGENTS.md`, Copilot's instruction files, `CLAUDE.md`,
  Cursor rules, and any newer cross-vendor standard). Approved if code.md
  already matches them.
- **13 and 14:** approved.
- **No phases:** build all of it as one release, as for WordPress.

## Progress log

**The rule (Jeff, 2026-11-04):** every fix and every feature is recorded in
three places when it is done:

1. here, saying what was done and how it was checked;
2. in the changelogs, QUILL's `CHANGELOG.md` and QUILL Lite's;
3. by removing it from Remaining tasks at the bottom of this file.

Work is not finished until all three are done.

**Where the work is:**

- The worktree is `S:\wt\quill-agentic-coding`, on branch
  `feat/agentic-coding`. From 2026-11-04 the work is committed there in
  logical commits and pushed; a PR to main opens when Remaining tasks is
  empty, and the parent session merges it.
- It was copied byte for byte on 2026-11-04 from the session's original
  worktree, `S:\QUILL\.claude\worktrees\agentic-coding-0091e0` (branch
  `claude/agentic-coding-0091e0`). Windows would not let that folder move
  while its session was open.
- Continue in the new folder.

### 2026-11-04: first pass, stopped at Jeff's request

The session built these before Jeff stopped all work. They are **not yet
checked or logged by that session**, so treat them as started, not done:

- **Shared, wx-free modules in `quill/core/ai/`:**
  - `project.py`
  - `project_store.py`
  - `project_tools.py`
  - `project_outline.py`
  - `project_task.py`
  - `project_task_words.py`
  - `project_transcript.py`
  - `change_set.py`
  - `checkpoints.py`
  - `code_diff.py`
  - `command_runner.py`
  - `test_summary.py`
- `quill/stability/process_tree.py`.
- **Changed:** `quill/core/ai/family_tools.py`.
- **Tests:** `tests/unit/core/ai/test_project_boundary.py`. A test run had
  finished in the background, unread, when work stopped.
- **Not started:** no changelog entries yet.

### 2026-11-04: the started modules reviewed and fixed

The second session read every started module, ran its tests and fixed what
was wrong. All of it is under `quill/core/ai/` unless named.

- **Checked:** `project.py`, `project_store.py`, `project_tools.py`,
  `project_outline.py`, `project_task.py`, `project_task_words.py`,
  `project_transcript.py`, `change_set.py`, `checkpoints.py`, `code_diff.py`,
  `command_runner.py`, `test_summary.py`, `quill/stability/process_tree.py`,
  and the `asks_itself` change to `family_tools.py`. The first session had
  also left five more test files (change set, checkpoints, command runner,
  task runner, test summary), which were not in its notes.
- **Fixed:**
  - a command with quotes in it reached `cmd /s /c` with backslash-escaped
    quotes, so it failed; the Windows command line is now built as one
    string (`process_tree.start_tree_process` takes either);
  - the program's own path (`C:\...\python.exe`) set off "This runs outside
    the project", which also took Always Allow away; only arguments count now;
  - the closing summary was always given an empty command list; it now says
    how many commands ran and the last result (`words.commands_sentence`);
  - test results said "1 errors";
  - GATE-PROJECT-REVIEW flagged every `str.replace` as a file write; it now
    counts `replace`, `remove` and `copy` only on `os` and `shutil`;
  - ruff line-length and format problems in the tests.
- **Added:** a classifier test for the program-path rule.
- **How checked:** `pytest tests/unit/core/ai/test_project_*.py`: 110 passed,
  1 skipped (the symlink test needs developer mode; the junction test runs).
  `ruff check` and `ruff format --check` clean; `mypy` clean on all twelve
  modules.

### 2026-11-04: the Claude pack hides its own tools

- `quill/ai_packs/claude.py` now passes `TEXT_ONLY_OPTIONS`:
  `disallowed_tools=["*"]`, `allowed_tools=[]`, `permission_mode="default"`.
- **How checked:** `tests/unit/core/ai/test_claude_pack_text_only.py` puts a
  stand-in `claude_agent_sdk` in `sys.modules` and asserts the options the
  pack builds; it passes.
- Both changelogs have the entry.

### 2026-11-04: Developer profile, project windows and commands, engine tools

Committed and pushed on `feat/agentic-coding` as `e24dc1db7`.

- **Developer profile, QUILL** (6.4). "Developer and Power Text" is now
  **Developer**. The id `developer_power_text` stays, because saved settings
  name it. A new feature, `core.developer`, uses a new catalogue field,
  `default_off`: it is off in every profile that does not name it, so a new
  profile cannot switch coding on by forgetting it. Developer and Full Quill
  turn it on. `core.github_remote`, `core.developer_console` (and so the
  TypeScript console) and `core.intellisense` now depend on it, and
  `project.*`, `localgit.*` and `tools.validate_agents` belong to it.
- **Developer profile, QUILL Lite.** A Coding area (22 areas now) and a fifth
  profile, Developer: Recommended plus Coding, eighteen of the 22. Coding is
  off in every other profile, Everything included. A store seeded before
  Coding existed gets Coding off once, through a second seeding marker.
- **The shared windows,** in `quill/ui/`:
  - `project_task_window.py`: the agent window, grown. Plan, Changes,
    Output, Transcript, Undo Last Turn, Explain Last Turn, Coach mode,
    Allowed Commands and Engine Tools. One runner lasts the whole task. The
    "waiting for you" behaviour of 5.3: a question opens only while the
    window is active; elsewhere in QUILL the waiting sentence is said once;
    with QUILL in the background nothing is said.
  - `project_review_dialog.py`: the files over one change at a time in code
    mode. Each row's sentence says "taken" or "not taken" and Space toggles
    it; the commit hook bans `wx.CheckListBox` (A11Y-SR-1), whose state a
    reader does not say on arrowing, so Engine Tools uses one real check box
    per tool for the same reason. Accept, Reject, Next, Previous, all in a file,
    and Why This Change?. Apply Accepted Changes, or Reject All.
  - `project_command_dialog.py`: Run This Command?, with the exact text and
    QUILL's warning line; Always allow appears only when there is no
    warning. The allow-list editor, with the bypass.
  - `project_open_dialog.py`: Open Project Folder with recent projects; Use
    This Project's Agent Notes?, with Read Them First; Engine Tools.
- **The shared commands:** `project_task_commands.py`, a base of
  `HostedAiMixin`, so both editors have one implementation. Ctrl+3 opens a
  project task when a project is open, and a document task when none is.
  Also Stop Agent, Undo Last Agent Turn (it works after the window closes,
  from the checkpoints on disk), Explain Last Turn, Open Command Output, Open
  Task Transcript, Commands Allowed, Engine Tools and Close Project.
  - QUILL's adapter, `main_frame_project_rows.py`, adds menu rows and an
    in-place reload, and no commands of its own.
  - QUILL Lite has `Tools > Project` rows, in the Coding area, and an
    in-place reload in `lite_window_sources.py`.
  - Both reload a changed open plain-text document with the cursor kept,
    and say one line. A document with unsaved edits, or in rich text, is
    left alone and named.
- **Keys.** No plain chord is free in both editors: every three-modifier
  candidate is a system-wide hotkey, a QuillVille launcher or a recent-file
  key. `project.` is a rule-7 family in the bound-command gate. QUILL puts
  Stop Agent and Undo Last Agent Turn on the leader (K and U), with Key
  Describer titles. Lite's rows have written reasons in its keyless table.
- **Engine tools (decision 4).** `quill/core/ai/vendor_tools.py` lists each
  engine's own tools: Copilot's `view`, `grep`, `glob`, `edit`, `bash`,
  `web_fetch` and `web_search` (from GitHub's allowing-tools page); Codex's
  command execution and file changes; Claude's. All are off until checked,
  kept per project in app data. A turn with any on says so in the
  conversation and under the transcript's Plan heading, and takes its
  checkpoint first. `FamilyToolRegistry.authorize_vendor` refuses a kind
  that is not on, logging a defect, and asks the person every time for one
  that is. Copilot adds them to `available_tools` and works in the project
  folder; Codex answers its built-in approvals through the same question.
- **Run Commands Without Asking (decision 7).** Stored with the allow list,
  off by default, confirmed when turned on, shown in the status line, and
  every command it runs is noted in the conversation. The never-list still
  applies.
- **Agent instruction files (decision 12).** Researched on 2026-11-04:
  - nested `AGENTS.md`, with the nearest winning;
  - `.github/copilot-instructions.md`, and `.github/instructions/*.instructions.md`
    with `applyTo`;
  - `CLAUDE.md` and `.claude/CLAUDE.md`, and `GEMINI.md`;
  - Cursor's `.cursor/rules/*.mdc` with `globs`;
  - the older `.cursorrules`, `.windsurfrules` and `.clinerules`.

  All are found. A scoped file goes to the engine marked "applies to ...".
  QUILL asks once per project, and keeps the answer in app data.
- **How checked:**
  - `tests/unit/core/ai/test_project_developer_profile.py`: the visibility
    gate over every profile, the escape hatch, and that both editors'
    Developer profiles turn on the same ten shared commands;
  - `tests/unit/core/ai/test_project_vendor_and_notes.py`: the opt-in store,
    refusal without asking, asking every time, the bypass, and every
    instruction-file shape;
  - `tests/unit/ui/test_project_task_windows.py`: review marking and wording,
    Always allow hidden with a warning, the allow-list editor, the task
    window's Plan and Output keys, and F1 on every control;
  - the Lite profile tests, the family-rule gates and the menu-shape gate:
    400 passed in those sets.
  - **Still failing, as expected until the guide is written:** six tests in
    `tests/unit/core/lite/test_lite_docs.py`, which read the Lite user guide.
- **Next:** Jeff's placement principle, below in Remaining tasks. Today the
  rows sit in AI > Project Tasks (QUILL) and Tools > Project (QUILL Lite).

### 2026-11-04: Do a Document Task screen-reader checks closed by Jeff

- **What:** Jeff closed the open screen-reader checks for Do a Document Task
  (NVDA, JAWS, Narrator). They no longer block anything in this plan.

### 2026-11-04: merged main, and every Developer command where people look

Committed and pushed as `7d35174a1`.

- **Merged `origin/main`** into the branch (`32f2db077`), for #1748's one AI
  menu shape (`quill/core/ai/ai_menu_layout.py`). Five conflicts, all
  resolved by keeping both sides: the two changelogs, Lite's area map, Lite's
  command table (main's `AI_MENU_ROWS`) and QUILL's AI menu builder.
- **Placement (Jeff's principle, 2026-11-04).** Each Developer command now
  sits where people already look for that kind of command, the same in both
  editors, and only in the Developer profile:
  - **File:** Open Project Folder (its window lists the recent projects) and
    Close Project, above Exit;
  - **Edit > Agent Work:** Undo Last Agent Turn and Stop Agent. A submenu
    because Lite's Edit menu has only J, K, Q, W and Z left, and every
    key-less Lite row needs a letter;
  - **View:** Agent Task Transcript and Agent Command Output;
  - **Tools:** Commands Allowed in This Project;
  - **AI menu, second group (what the AI does):** Do a Project Task, Explain
    Last Turn and Engine Tools for This Project, after Do a Document Task.
    `ai_menu_layout.DEVELOPER_TASK_HANDLERS` names them.
  - The old AI > Project Tasks (QUILL) and Tools > Project (Lite) submenus
    are gone. QUILL places its rows through `_place_project_rows`, one call
    in `main_frame_menu.py`; Lite maps each handler to the Coding area in
    `command_areas.COMMAND_AREA`, so a row is hidden wherever it sits.
  - There is no separate Review Changes command to put in View: the review
    opens by itself when a turn has changes, which is the point of it.
- **How checked:** a new test,
  `test_each_developer_command_sits_where_people_look_in_both_editors`,
  asserts the same menu for every command in both editors and that the AI
  rows fall between Do a Document Task and Which AI Am I Using. Lite's
  command, profile and keyless-reason tests pass (59); QUILL's menu contract,
  ids, access keys, bound items, routes, accelerators, bar keys and
  Microsoft-shape gates pass (66, the access-key test once on its own after a
  load timeout in the parallel run).

### 2026-11-04: egress entry, Safe Mode, undo's comparison, the undo property

Committed and pushed as `8be57e942`.

- **Network egress.** A new kind of reviewed entry, "person-approved
  command", for `stability/process_tree.py::start_tree_process`, in a new
  `quill/tools/network_egress_entries_agents.py` (split out under GATE-11,
  with the Codex entry beside it): what the command may reach, how
  QUILL labels it rather than blocks it, the allow list, the bypass, the
  never-list, the scrubbed environment and Safe Mode. The Codex entry now
  says what changes when a project turns on Codex's own tools.
- **Safe Mode** refuses project tasks: Open Project Folder and Do a Project
  Task say the Safe Mode sentence and stop.
- **Undo's refusal offers the comparison** (4.5). When Undo Last Agent Turn
  refuses because the person edited a file since, it asks once: "... Open
  the file as it was before the agent's turn, to compare?" Yes opens that
  text as a document from QUILL's app data; the person's file is untouched.
  Same path from the task window and from Edit > Agent Work.
- **The undo property, randomized.** Twelve seeded runs of random edits,
  random hunk choices, a new file and a deletion, mixed line endings: after
  Undo Last Turn the tree is byte for byte what it was. The partial-failure
  test (a write failing half way rolls the whole turn back) was already in
  `test_project_change_set.py` and passes.
- **How checked:** `tests/unit/tools/test_network_egress_audit.py` (6
  passed); new `tests/unit/ui/test_project_task_commands.py` (9 passed: the
  Developer gate, Safe Mode, Ctrl+3's two doors, the commands that need a
  project, Stop with nothing running, undo with the window closed, Close
  Project, and the refused undo's comparison);
  `test_project_checkpoints.py` (18 passed).

### 2026-11-04: the engines: Codex, Claude, Ollama practice, ACP re-read

Committed and pushed as `1f83f179f`.

- **Codex on the project tools.** Nothing new was needed in the engine: its
  `dynamicTools` come from the same registry, so a project task offers Codex
  every project tool, and `project_edit` takes the unified-diff `patch` its
  models are trained on. A test asserts both.
- **A loop QUILL drives itself:** `quill/core/ai/harness/loop_session.py`,
  a `ToolSession` for a chat model with no agent runtime. It sends the
  conversation and the tool list, runs each tool call through the registry
  (so the broker, approvals and review apply as under Copilot), and stops on
  plain text, on Stop, or after 60 requests.
- **Ollama practice mode:** `quill/core/ai/harness/ollama_tools.py`, on
  `/api/chat` with tools, on this computer only (`_post` refuses any other
  address). Labelled "Practice, on this computer. Nothing is sent. Slower and
  less capable." Reached by choosing Ollama on this computer in My own key.
- **Claude on the person's own key:** `quill/ai_packs/claude_tool_session.py`.
  QUILL's tools as an in-process MCP server named `quill`, only their names
  in `allowed_tools`; every Claude Code built-in denied **by name** (a `"*"`
  deny would also deny QUILL's MCP tools, since deny rules win); a built-in
  the person turned on for the project is left out of that list and asked
  through `can_use_tool` each time; `permission_mode="default"`; the key goes
  only into the SDK child's environment. Branding: "Claude Agent".
- **Wiring:** `agent_harness` returns these engines for My own key when its
  provider is Ollama or Claude, and the capability table now claims agent
  tasks for those two providers, with sources (GATE-CAPS). Other own-key
  providers stay text only.
- **Egress:** Ollama's loopback POST is reviewed in
  `network_egress_entries_agents.py` (`AGENT_HTTP_EGRESS`). The Claude SDK's
  own child is started inside the SDK, where the audit does not see a call
  site; its traffic is a live G5 check.
- **ACP re-read (3.7), 2026-11-04.** Copilot CLI's ACP server is still a
  public preview; Codex and Claude reach ACP only through adapters, some
  third-party, and sources disagree on which are official. Decision kept:
  do not build on ACP in this release; re-read it after.
- **Acceptance task:** `tests/unit/core/ai/test_project_acceptance.py`. A
  sample project with a failing `unittest`; a scripted engine on QUILL's own
  loop plans, reads, runs the tests (1 failed), edits through review, runs
  them again (1 passed), and Undo Last Turn puts the bug back. Judged by the
  sample project's own tests.
- **The G gates per engine.** G3 (only our tools) is asserted for Claude
  and Ollama by the new tests; G4 (Stop) for the loop; G5 (what leaves the
  machine) is nothing for Ollama by construction. The live runs on Copilot,
  Codex and Claude need real accounts and are in the screen-reader and live
  checks for Jeff.
- **How checked:** `tests/unit/core/ai/test_project_engines.py` (8 passed),
  the acceptance test (2 passed), the capability and route tests (98
  passed), the egress audit (6 passed).

### 2026-11-04: the Project status cell, in both editors

Committed and pushed as `d80224b66`.

- **What it says:** "Project cli-tool, main", with ", waiting for you" while
  the project task is waiting on a question the person has not seen yet.
  Enter on it opens Do a Project Task. One sentence for both editors
  (`project_task_words.project_cell`, through
  `ProjectTaskMixin.project_status_text`).
- **QUILL:** a new status-bar item, `project`, before `ai` (the last two stay
  `ai` and `message`). Hidden by default; Open Project Folder shows it the
  first time, the way the Radio cell surfaces. Its text and Enter live in
  `main_frame_ai_status.py` beside the AI cell, so `main_frame.py` and
  `main_frame_statusbar.py` did not grow; F1 text in
  `statusbar_cell_help.py`.
- **QUILL Lite:** a `project` cell shown only while it has text, so nobody
  without a project open ever meets it; Enter opens the task.
- **How checked:** the settings, Lite status bar layout and message, QUILL
  status context and message tests (162 passed), plus a new test of the
  cell's three states.

### 2026-11-04: the platform gates over the new work

Committed and pushed as `c8c97de78`.

`python -m quill.tools.platform_report` showed 44 of 53 gates passing. Each
failure, and what was done:

- **GATE-14 (access keys):** the agent-notes question had &Notes and
  Do&n't Use Them on N; it is &Don't Use Them now. Clean.
- **List activation:** Open Project Folder's recent list answered only a
  double-click; it now uses `apply_listbox_activation`, so Enter and Space
  open the selected project.
- **GATE-CTLLABEL (control labels):** two read-only fields with no label
  before them (About this list; the agent-notes question) now get a spoken
  name through `set_spoken_name`. No new unnamed control.
- **GATE-REACH:** the review, command and open-project windows are all
  reachable from an app entry point; the snapshot is regenerated.
- **GATE-KEYREF:** `docs/keyboard-reference.md` is regenerated: ten project
  commands, two on the QUILL key (K for Stop Agent, U for Undo Last Agent
  Turn). Its HTML and EPUB are rendered with the docs, next.
- **GATE-LITE-COVER:** a new `tests/unit/apps/test_lite_project_task.py`
  calls every Coding handler on a real QUILL Lite window (9 tests). The
  coverage snapshot is regenerated: 296 handlers, all covered, none
  shape-only.
- **GATE-11:** `lite_window_status.py` had grown by two lines with the
  Project cell; the Project and AI cells now come from one helper,
  `shared_ai_cells`, and the file is back at its budget.
- **Accessible names:** failed on a transient file read under load
  (Errno 22 reading an unrelated module), not on the new code.
- **Doc artifacts:** waits for the docs work, which renders every changed
  Markdown file to HTML and EPUB.
- **Passing already:** GATE-13 (no over-announcing), the braille-parity
  audit, every app's F1 help audit, the settings vocabulary, the dialog
  inventory, the egress audit and the banned-pattern gate.

### 2026-11-04: F1 for the new windows, and the transcript as Markdown

Committed and pushed as `334f70236`.

- **Window purposes (5.7).** A new `quill/core/project_surface_help.py`
  says what each project window is for, in one to three sentences: Do a
  Project Task, Review Changes, Run This Command?, Commands Allowed in This
  Project, Open Project Folder, Use This Project's Agent Notes? and Engine
  Tools for This Project. They merge into QUILL Lite's catalogue and its
  shared-with-QUILL set, and GATE-LITE-HELP now scans `quill/ui/project_*.py`
  (as it does `hosted_ai*.py`). The task window's title is now plain "Do a
  Project Task", so F1 finds its purpose; the project's name is in the
  status line and the Project cell.
- **The F1 help reference** (`docs/f1-help-reference.md`, with HTML and
  EPUB) is regenerated: every control's sentence in the new windows is in it.
- **Export to Markdown.** The transcript is Markdown already: Transcript in
  the window (and Agent Task Transcript in View) opens the task's history,
  headed one turn at a time, as a document in the editor, where Save As
  puts a copy anywhere. Nothing more was needed; the user guides say so.
- **How checked:** the Lite help audit (278 controls, all helped), the help
  reference test (4 passed), the window tests.

### 2026-11-04: the tutorial lesson, in both editors

Committed and pushed as `db154b46f`.

- **"Your first project task"** (`quill/core/tutorials/coding_lessons.py`),
  twelve minutes, eight steps: make a practice folder, open it as a project,
  ask for one change, read the plan, review the change, allow the test
  command and hear the result, undo the whole turn, and try coach mode. Each
  step says what you should hear. One text for both editors; the commands
  are mapped per editor, as the dictation lessons are, so keys render live.
- **A Coding track,** "Coding, in the Developer profile", in QUILL and QUILL
  Lite. Each editor's Tutorials window leaves the track out unless coding is
  on (`model.without_track`, applied in `quill/ui/quill_tutorials.py` and
  `quill/apps/lite_tutorials.py`), so nobody outside the Developer profile
  meets it.
- **The printed tutorial books** (`docs/user guide/tutorials.md` and QUILL
  Lite's `docs/tutorials.md`) are regenerated, with HTML and EPUB; they list
  the lesson under its track, which names the Developer profile.
- **How checked:** the tutorial catalogue tests (no problems in either
  catalogue; the books match), the distribution build tests that read the
  books (58 passed), and 204 tutorial-related tests in all.

### 2026-11-04: the documentation, and the screen-reader checks written

Committed and pushed as `b32520d06`.

- **QUILL user guide** (`docs/user guide/userguide.md`): a new chapter,
  "Project tasks: coding with an AI", beside the AI chapter, with sections
  on the Developer profile, which AI can run a task, opening a project, the
  task window and its keys, the plan, Review Changes, files you have open,
  Run This Command?, what QUILL cannot stop on Windows, Commands Allowed,
  Undo Last Agent Turn, Stop Agent, coach mode and Explain Last Turn, agent
  notes, engine tools, the transcript, where records are kept, the tutorial,
  and the menus at a glance. "Developer and Power Text" is now "Developer".
- **QUILL PRD:** a new section 36, "Project tasks: agentic coding with an
  AI", in requirement form.
- **QUILL release notes and announcement** (`release1.0.0.md`,
  `announcement-1.0.0.md`): a section each.
- **QUILL Lite user guide:** a new section in Chapter 10, "Coding: project
  tasks, in the Developer profile", with the menu table, the task window's
  keys, review, commands and their warnings, undo, Stop, coach mode, engine
  tools, engines and where things are kept. The profiles chapter now says
  five profiles and 22 areas, has a Developer section, and every other
  profile names coding among what it leaves off. The status-bar table has the
  Project part.
- **QUILL Lite PRD, release notes 2.0 and announcement:** a section each.
- **Screen-reader acceptance:** thirteen checks in
  `docs/qa/screen-reader-checks-2026-10.md`, "Project tasks in the Developer
  profile", for NVDA, JAWS and Narrator in both editors, in a sample project,
  including the live runs on Copilot, Codex, Claude and Ollama on Jeff's
  accounts. They are written; running them is Jeff's, at the keyboard.
- **Rendered:** HTML and EPUB for every changed Markdown file.
- **How checked:** the QUILL Lite docs tests (profiles, counts, every
  command and status cell named), the documented-menus, documentation-chord
  and chord-ownership gates, the check-box wording gate, and the tutorial catalogue
  tests.

### 2026-11-04: final gates, first pass; three red results fixed

The parallel run (`pytest -q -n 8 --dist loadgroup`) reported four failures
and lost workers until xdist gave up. Each failure was rerun on its own:

- **Practice mode's call to Ollama now goes through `quill.core.net`**
  (`harness/ollama_tools.py`). The TLS one-check gate requires every urllib
  caller to pass a context from net; loopback is plain HTTP, so
  `context_for(url)` gives none, and the gate holds. Checked with
  `test_tls_one_check.py` and the engine tests.
- **The accelerator map test counts the ten project rows**
  (`test_main_frame_hosted_ai.py`): QUILL's map now carries them, as intended.
- **The empty-document sweep starts each case without a dictation session**
  (`test_lite_no_silent_command_on_empty_document.py`). Where a speech engine
  is installed, Speak a Command really started one and left it running, so
  Switch Dictation Language talked to that session and said nothing. Not a
  product bug: a fresh checkout without Moonshine never starts a session, which
  is why main passed. Found by bisecting the file; it now passes in order.
- The Cast AI rows test failed only in parallel and passed on its own.

### 2026-11-04: final gates, second pass; Final gates taken off

- **Serial `pytest -q`** ran to 62 percent, then pytest-timeout stopped the
  run on `test_sound_app_events.py`, a whole-tree scan that takes 17 seconds
  alone and passes; under load on S: it went over 30. Before that, two
  failures were tests written before the project rows:
  - `test_lite_ai.py`: with AI help off, Tools > AI keeps only Accounts and
    Usage. The test now switches Coding off too, as it is by default, since
    the project rows also sit in Tools > AI.
  - `test_lite_pdf.py`: the status cells shown only while they have text are
    now Page and Project.
  The two performance budgets that failed under load passed on their own.
- **platform_report:** every gate passes.
- **Scoped mypy** (`quill\core quill\io`): no errors in either. The 798
  reported are in modules mypy follows from them (quill\ui, Beacon and the
  AI packs), the same number as on main.
- The rest of the suite is left to CI's sharded run, which is the gate that
  counts; anything it finds is fixed on the branch.

### 2026-11-04: three CI gaps on PR #1760, fixed

- **Persistence audit:** the six new write sites are classified in a new
  `quill/tools/persistence_entries_project.py`, reached through `AI_ENTRIES`
  so `persistence_audit.py` stays at its GATE-11 ceiling. They are:
  - the checkpoint index and the recent projects list: `cache`;
  - the agent-notes answer: `marker`;
  - the allow list and the engine tools: `versioned`, each a version-1 envelope
    that reads as the safe default when damaged.
  Checked with `test_persistence_audit.py`.
- **Accessible-name inventory:** regenerated with
  `accessible_name_audit --write`. All eight new sites are `named` or
  `modal-hook`, none missing.
- **Hardened dialog contract:** Commands Allowed in This Project and Use This
  Project's Agent Notes? now go through `apply_modal_ids` instead of a bare
  `SetEscapeId`. In the first, Close is the affirmative and the escape. In the
  second, Use Them is the affirmative and Escape is Don't Use Them. Checked
  with `test_dialog_hardening_contract.py`, the dialog contract, the button
  contract and the project window tests.

## Remaining tasks

This list is kept current. A task is removed when it is done, checked, logged
above and in the changelogs. Everything not listed here is built.

Nothing remains. The two checks that need Jeff at the keyboard, the live
engine runs and the screen-reader acceptance, are written in
`docs/qa/screen-reader-checks-2026-10.md`.
