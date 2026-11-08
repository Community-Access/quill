# AI across the QUILL family: Choose Your AI, Ask, and agents

Plan of record, 2026-10-31; kept here since 2026-11-03 (it was `codex.md` at the
repository root). Code cites it by section as `codex.md <section>` -- for example
"codex.md 10A.9" for Choose Your AI -- and those citations resolve in this file.
Where shipped code differs from the plan, the code and its docstrings are the
record.

## 1. The short version

Every QuillVille app will offer five connections in one Choose Your AI window: QUILL's free AI, My ChatGPT plan, My GitHub Copilot, Codex and My own key (section 10A), with one Ask conversation in every app (10C). Copilot comes before Codex (section 11).

Four QUILL apps can already sign in to ChatGPT on their own:

- QUILL, QUILL Lite, Radio and Cast use `quill/core/ai/chatgpt_account.py`, each under its own agent name. The other apps have no sign-in yet (section 3.1).
- Today they send one-shot requests to `/v1/responses` through `quill/core/ai/chatgpt_client.py`.

QUILL also has a GitHub Copilot engine already (section 3.7). It installs the Copilot SDK on demand, signs in with GitHub's device flow, and runs Copilot text-only: QUILL denies every Copilot tool and applies the answer itself.

The next step is an agent: the model plans, calls tools, asks permission, and finishes a job over several steps.

Two vendor runtimes can run that loop on a subscription the user already has:

- **OpenAI's Codex app-server**, on the ChatGPT plan (section 2). A local Rust child process, JSON-RPC over stdio, threads, turns, streaming, approvals and app-defined tools. A preview programme.
- **The GitHub Copilot SDK**, on a Copilot subscription, including Copilot Free (section 2B). A Python package that drives the Copilot CLI runtime as a child process over JSON-RPC, with custom tools whose handlers run in our own Python, a permission callback, and a tool allowlist. Generally available since 2026-06-02, and being renamed Microsoft Copilot SDK.

Recommendation: one shared agent layer, two engine adapters, Copilot first.

- **Shared:** one tool registry, one approvals UI and one agent window serve every app and both engines (section 5). Most of the work is here, not in either adapter.
- **Copilot first:** the SDK is GA and semver, it is Python, its tool handlers are plain Python callables, and QUILL already has its sign-in, onboarding dialog and pack. Codex follows on the same registry (section 11).
- **Separate connections:** each app runs its own child process. Each keeps its own ChatGPT sign-in. Copilot uses one GitHub sign-in, but no app hands its token to anything else.
- **The vendor's own tools off:** shell, file edits, plugins, connectors and image generation are switched off under either engine.
- **QUILL's tools only:** the model gets only tools QUILL already has (section 3), wrapped as functions. Each runs through the existing `SafeEditorToolGateway` and `PermissionBroker`.
- **Accessible approvals:** every approval appears in QUILL's own accessible dialogs.

Revised 2026-10-31 (section 11): Choose Your AI comes first, in QUILL and QUILL Lite (section 10A), then the Copilot route, then single-request features app by app, then the agent engines. The first agent feature is multi-step document tasks in QUILL and QUILL Lite, on tools that already exist; Studio's "check my recording setup" comes straight after (decision 3).

- It is built on Studio's existing `preflight()` and capture code.
- It needs no new model capability.
- A blind user learns before recording, not after, that the microphone is wrong or the wrong window is captured.

The biggest risks are not technical:

- The size of the download: about 113 MB compressed for the Copilot runtime and 92 MB for Codex (section 9).
- Both vendors are moving: Codex's plan sharing is a preview, and the Copilot SDK is changing owner (section 10).
- Copilot sign-in from inside the app needed a GitHub OAuth App per app (section 3.7, R10). Done: Jeff registered them under Community-Access on 2026-11-02, and their client ids are built into `quill/core/ai/copilot_auth.py`.

## 2. Codex app-server: what the platform allows and refuses

How each claim is marked, here and in section 2B:

- **Confirmed:** read on the page cited, on 2026-10-31.
- **Inferred:** follows from what was read, but no page says it.
- **Unknown:** no primary source found.

### 2.1 Launch, distribution, licence

| Item | Status | Source |
|---|---|---|
| Launch with `codex app-server --listen stdio://`. The plan provider is set with `-c` overrides: `model_provider="openai_chatgpt_plan"`, `base_url=https://api.openai.com/v1`, `env_key="ACCESS_TOKEN"`, `wire_api="responses"`, `requires_openai_auth=false`, `supports_websockets=false`. | Confirmed | developers.openai.com/siwc/token-sharing-open-source/codex-app-server |
| Rust. Release `rust-v0.166.0` (2026-10-29) ships `codex-app-server-x86_64-pc-windows-msvc.exe` at 283,894,064 bytes, or 92,228,613 bytes zipped. There is also an ARM64 build. | Confirmed | GitHub API, openai/codex releases/latest |
| Also on npm (`@openai/codex`), Homebrew, and PowerShell and curl installers. | Confirmed | github.com/openai/codex README |
| Licence: Apache-2.0. | Confirmed | github.com/openai/codex |
| No Node needed; one signed native exe. | Inferred | Release assets |
| Other transports: `ws://` ("experimental and unsupported"), `unix://`, `off`. | Confirmed | learn.chatgpt.com/docs/app-server (developers.openai.com/codex/app-server redirects there) |

### 2.2 The protocol

| Item | Status | Source |
|---|---|---|
| Newline-delimited JSON-RPC. Sequence: `initialize` with `clientInfo {name, title, version}`, then `initialized`. `clientInfo.name` "should match" `agent_name_hint`. | Confirmed | SIWC codex-app-server page |
| `thread/start` fields: `model`, `cwd`, `approvalPolicy`, `sandbox`, `config` (override map), `baseInstructions`, `developerInstructions`, `ephemeral`, `dynamicTools`. `dynamicTools` is experimental and needs `capabilities.experimentalApi`. | Confirmed | app-server docs; `codex-rs/app-server-protocol/src/protocol/v2/thread.rs` |
| `turn/start` takes `threadId` and `input` (text, image, localImage). `turn/interrupt {threadId, turnId}` ends a turn as `interrupted`. `turn/steer` adds input to a running turn. | Confirmed | app-server docs |
| Streaming events: `item/agentMessage/delta`, `item/started`, `item/completed`, `turn/started`, `turn/completed`. Only `completed` means success. | Confirmed | Both pages |
| Approvals: `item/commandExecution/requestApproval` and `item/fileChange/requestApproval`. Decisions: `accept`, `acceptForSession`, `decline`, `cancel`. | Confirmed | app-server docs |
| App tools: the server sends `item/tool/call`. The client answers `{contentItems: [inputText or inputImage], success}`. Tools may be grouped by namespace. | Confirmed | `codex-rs/protocol/src/dynamic_tools.rs`; `app-server/tests/suite/v2/dynamic_tools.rs` |
| `approvalPolicy` values: `untrusted`, `on-request`, `never`. `sandbox` values: `read-only`, `workspace-write`, `danger-full-access`. | Confirmed | `codex-rs/protocol/src/protocol.rs`, `config_types.rs` |
| `account/rateLimits/read` and `/updated` report `usedPercent`, `windowDurationMins` and `resetsAt`. | Confirmed that they exist | app-server docs |
| Whether those rate-limit calls report anything under the SIWC `env_key` provider. | Unknown | Live test needed |
| `codex app-server generate-json-schema --out DIR` produces a schema that matches the exact binary version. | Confirmed | app-server docs |

### 2.3 How the plan token is supplied

- **Confirmed.** The app performs the SIWC OAuth and puts `access_token` in the child's `ACCESS_TOKEN` environment variable. To renew, it gets a fresh token, restarts app-server, runs `initialize` again, then calls `thread/resume`. Sources: the SIWC codex-app-server page and the preview-limitations page.
- **Unknown.** Whether the experimental `account/login/start {type: "chatgptAuthTokens"}` route accepts SIWC tokens. It is not documented for SIWC, and this plan does not use it.
- **Confirmed in our code.** `ChatGptAccount.access_token()` already holds the access token in memory. The refresh token is in the OS store, per app. `PLAN_SCOPE = "chatgpt.tokens.use.direct"`.

### 2.4 Restricting what Codex itself can do

**Feature flags (confirmed, from source only).** `codex-rs/features/src/lib.rs` defines these switches:

- Stable and on by default: `shell_tool`, `unified_exec`, `view_image`, `plugins`, `apps` (hosted connectors), `image_generation`, `hooks`, `sleep_tool`.
- Off by default: `memories`.
- Removed: `tool_search`.

**Turning them off (confirmed).** `thread/start` accepts a `config` override map, and `-c key=value` works at launch.

**Expected result (inferred).** Setting all of these leaves the model seeing only QUILL's dynamic tools:

- `features.shell_tool=false`
- `features.unified_exec=false`
- `features.apps=false`
- `features.plugins=false`
- `features.image_generation=false`
- `features.hooks=false`
- `web_search="disabled"` (the `WebSearchMode` enum has `disabled`)

**Unknown.** Whether `apply_patch` can be removed completely. The backstop is `sandbox: "read-only"` plus declining every file-change approval.

**No official page documents this.** Gate G3 (section 11) must therefore record the tools actually offered to the model.

**Inferred: keep `defer_loading` false.** Deferred tools use tool search, and configurations that emit `tool_search` "will fail" under app-server.

### 2.5 What the plan refuses (confirmed, preview-limitations page)

**Refused inputs and services:**

- audio and video input;
- the Files API;
- the transcription API;
- image generation;
- file search;
- Code Interpreter;
- native computer use;
- hosted MCP and connectors;
- `tool_search`.

**Request rules:**

- `store: false` and `stream: true` are required.
- `system` items are rejected.
- Fifteen request fields must be omitted, including `temperature` and `max_output_tokens`.
- Web search is "subject to model and account/workspace policy".
- Images are accepted when the chosen model accepts them.

**Not covered:** text-to-speech output is not mentioned (unknown). This plan treats it as off the plan.

### 2.6 Usage and limits

- **Confirmed:** no numeric limits are published.
- **Confirmed:** for Plus, "the five-hour usage limit is shared across all apps". Users can set per-app limits in ChatGPT Settings > Usage. Source: profiles-and-sessions.
- **Confirmed:** usage errors are `subscription_sharing_usage_limit_exceeded` (429) and `subscription_sharing_usage_unavailable` (503). Pause; do not loop. OpenAI never silently switches billing. Source: errors-and-recovery.
- **Confirmed:** there is no usage API. The guidelines ask for a "Manage usage" link and a "Using ChatGPT plan" label. Source: siwc/ui-ux-guidelines.
- **Our gap:** `quill/ui/hosted_ai_chatgpt.py` has "Open ChatGPT &Usage", but no code shows "Using ChatGPT plan".

### 2.7 Terms (confirmed)

Source: the Sign in with ChatGPT Terms, dated September 29, 2026. The live page returned 403 to automated fetches, so the text was read from the web.archive.org capture of 2026-10-21.

**What apps must do:**

- **User control:** requests "must originate from the user's local runtime or a remote runtime only that user controls". Tokens are stored only locally, under the user's control.
- **User authorization:** requests come from the user's activity or from "expressly authorized automations or background processes". "Obtain express consent before background use."
- **Connected application only:** "Use the user's plan only for the application they connected." No general-purpose API access for other tools.
- **No charge:** using the plan must not require paying the developer or upgrading.

**What apps must not do:**

- Pool, share or transfer usage or tokens.
- Let one user's plan serve another user.
- "Alter, reverse engineer, or otherwise amend the SIWC software."

**Eligibility (inferred):** the SIWC open-source pages are written for "open-source and locally hosted apps". QUILL is MIT-licensed (`S:\QUILL\LICENSE`) and runs locally.

## 2B. GitHub Copilot SDK: what it allows and refuses

Read 2026-10-31, primary sources only. Same marking as section 2.

### 2B.1 What it is, licence, distribution

| Item | Status | Source |
|---|---|---|
| A multi-language SDK that embeds "the same agent runtime that powers Copilot CLI". Planning, tool calls, file edits, streaming, multi-turn sessions. | Confirmed | github.com/github/copilot-sdk README |
| Languages: Python, TypeScript, Go, .NET, Java, Rust. Python is `pip install github-copilot-sdk`, imports as `copilot`, needs Python 3.11 or later. | Confirmed | README; pypi.org/pypi/github-copilot-sdk/json |
| Python 1.0.28 (2026-10-28) is one pure wheel, `py3-none-any`, 925,301 bytes. Depends on pydantic 2.11+, httpx and python-dateutil. | Confirmed | PyPI JSON |
| SDK licence: MIT. | Confirmed | README, PyPI `license_expression` |
| Timeline: technical preview 2026-01-14, public preview 2026-04-02, GA 2026-06-02 with "a stable API" and semantic versioning. | Confirmed | github.blog changelog entries of those dates |
| 2026-10-28: "We're transitioning GitHub Copilot SDK to Microsoft Copilot SDK." Phased, no dates, "No immediate changes are required for existing users". The repo will move to the Microsoft organisation. | Confirmed | github.blog/changelog/2026-10-28-github-copilot-sdk-is-becoming-microsoft-copilot-sdk |
| Whether the rename changes sign-in, billing or package names later. | Unknown | Same page says nothing |

### 2B.2 The runtime it drives

| Item | Status | Source |
|---|---|---|
| "All SDKs communicate with the Copilot CLI server via JSON-RPC." The SDK starts and stops the CLI itself, or connects to one already running in server mode. | Confirmed | README |
| Python transports: `RuntimeConnection.for_stdio(path=...)`, `for_tcp`, `for_uri`, and `for_inprocess()` (experimental). | Confirmed | `python/README.md` |
| The Python wheel does not contain the CLI. It pins a runtime version and fetches it on first use, or with `python -m copilot download-runtime`. `COPILOT_CLI_PATH` points at our own copy; `COPILOT_SKIP_CLI_DOWNLOAD=1` stops the download. | Confirmed | `python/README.md`. The top README says Python "bundles" the CLI; the Python README and the 925 KB wheel say otherwise. |
| SDK and CLI negotiate a protocol version at start (2 to 3 today). | Confirmed | docs.github.com, SDK and CLI compatibility |
| Copilot CLI v1.0.105 (2026-10-28). Windows x64 assets: `copilot-win32-x64.zip` 112,637,935 bytes, `copilot-x64.msi` 106,479,616 bytes, npm platform tarball 77,606,846 bytes. ARM64 builds too. SHA256SUMS published. | Confirmed | GitHub API, github/copilot-cli releases/latest |
| Node.js 22 or later is needed only for the npm install. WinGet and the standalone download list no Node prerequisite. | Confirmed | docs.github.com, Installing GitHub Copilot CLI |
| The win32 zip is a self-contained executable that needs no Node. | Inferred | No Node prerequisite; size |
| Installed (unzipped) size. | Unknown | Not published |
| CLI licence: the proprietary "GitHub Copilot CLI License", not open source. It allows redistributing "unmodified copies of the Software as part of an application or service", not "on a standalone basis or as a primary product", with the licence included. No modification. | Confirmed | github.com/github/copilot-cli/blob/main/LICENSE.md |
| Login, logout and user info are CLI-only, not in the SDK. The app does its own sign-in and passes a token. | Confirmed | SDK and CLI compatibility page |

### 2B.3 Sessions, streaming, tools

| Item | Status | Source |
|---|---|---|
| `CopilotClient(...)` then `create_session(...)`. Options include `model`, `tools`, `available_tools`, `excluded_tools`, `on_permission_request`, `streaming`, `system_message` (append, replace, customize), `mcp_servers`, `provider` (BYOK), `hooks`, `reasoning_effort`, `working_directory`. | Confirmed | `python/README.md` |
| `session.send(prompt)` "returns a request ID" and does not wait. `send_and_wait` waits for idle and can return None. Events come through `session.on(...)`. | Confirmed | `python/README.md` |
| Events: `assistant.message`, `assistant.message_delta`, `assistant.reasoning_delta`, `session.idle`, `permission.requested`, `external_tool.requested`, `session.compaction_*`, `assistant.usage` and others. | Confirmed | `python/README.md`; usage-and-billing page |
| Custom tools: `@define_tool` with a Pydantic schema, or `Tool(name, description, parameters, handler)`. The handler is our Python; it gets a `ToolInvocation` and returns a `ToolResult`. A tool can be marked `skip_permission`. Overriding a built-in name needs `overrides_built_in_tool=True`. | Confirmed | `python/README.md`; GA changelog |
| MCP servers can be attached per session; their tools appear as `<server>-<tool>`. | Confirmed | `python/README.md` |
| By default the session offers the CLI's own tools, "similar to `--allow-all`", still gated by the permission handler. | Confirmed | README |
| `available_tools` is an allowlist and wins over `excluded_tools`. An empty `available_tools` list was fixed to mean no built-ins (SDK v0.1.29, issue #617, closed 2026-05-04). | Confirmed | github/copilot-sdk issue #617; custom-agents docs |
| CLI bug, open since 2026-10-30: an empty `--available-tools` on the CLI flag exposes all 21 built-ins; a name that matches nothing exposes none. | Confirmed for the CLI flag | github/copilot-cli issue #5306 |
| Whether that bug reaches the SDK's `available_tools=[]`. | Unknown | Gate G3 records the offered tool list |
| Whether our custom tools stay visible when `available_tools` lists only their names. | Inferred yes | Allowlist semantics; G3 checks it |
| Whether a custom tool result can carry an image back to the model. | Unknown | Not documented for Python |

### 2B.4 Approvals and permissions

| Item | Status | Source |
|---|---|---|
| Deny by default: without `on_permission_request`, every request is denied or left pending. | Confirmed | Compatibility page; `python/README.md` |
| Handler `(request, invocation) -> result`, sync or async. Results: `PermissionDecisionApproveOnce`, `PermissionDecisionReject(feedback=...)`, `PermissionDecisionUserNotAvailable` (the default), `PermissionNoResult`. Request kinds include shell, write, read, url, mcp, custom-tool, memory and hook. | Confirmed | `python/README.md`; Node README; release v0.3.0 |
| Hooks at pre and post tool use, session start, MCP calls and permission requests. | Confirmed | GA changelog |
| Organisation-managed settings can require approval (`managed_approval_required`); `approve_all` refuses to run then. | Confirmed | `python/README.md` |

### 2B.5 Authentication and plans

| Item | Status | Source |
|---|---|---|
| Methods: the signed-in CLI user, a token from the app's own GitHub OAuth App or GitHub App, environment variables (`COPILOT_GITHUB_TOKEN`, then `GH_TOKEN`, then `GITHUB_TOKEN`), server-to-server, and BYOK. An explicit `github_token` wins. | Confirmed | docs.github.com, Copilot SDK Authentication |
| Token types: `gho_` (OAuth App), `ghu_` (GitHub App), fine-grained `github_pat_`. Classic `ghp_` is not supported. | Confirmed | Same page |
| "Copilot usage is billed to each user's subscription." The app owns token storage and refresh. | Confirmed | docs.github.com, GitHub OAuth setup |
| The OAuth setup page shows only the server-side code flow with a client secret. Device flow is how the CLI signs in. | Confirmed | OAuth setup page; Authentication page |
| A device-flow token from QUILL's own OAuth App, with scope `read:user`, is accepted for Copilot. | Inferred | Token type `gho_` is supported; no page names a scope. G1 checks it. |
| Plans: "open to existing Copilot subscribers, including the Free plan for personal use". BYOK needs no subscription. | Confirmed | GA changelog |
| An organisation or enterprise can switch the CLI off for its members. | Confirmed | Installing Copilot CLI |
| BYOK: `provider` types openai, azure and anthropic, key only, no Entra ID. | Confirmed | README; `python/README.md` |

### 2B.6 Usage, limits, models

| Item | Status | Source |
|---|---|---|
| Since 2026-06-01 Copilot bills by usage in GitHub AI Credits, not premium requests, except annual Pro and Pro+ plans still on the old model. | Confirmed | docs.github.com, What changed with Copilot billing |
| Monthly AI Credits: Free an unstated allowance, Pro 1,500, Pro+ 7,000, Business 1,900 a user, Enterprise 3,900 a user. "All plans include Copilot CLI." Free gets Auto model selection only. | Confirmed | docs.github.com, Plans for GitHub Copilot |
| The SDK reports cost per model call (`assistant.usage`), session totals (`session.usage.getMetrics`, experimental), and the account quota (`account.getQuota`: used, entitlement, remaining percent, reset date). Model prices come from `models.list` at run time. | Confirmed | docs.github.com, SDK usage and billing |
| Models: OpenAI, Anthropic, Google, xAI and Microsoft models, per plan. The default CLI model has been a Claude Sonnet. Read the list at run time, never hard-code it. | Confirmed in outline | docs.github.com, Supported models; copilot-cli README |
| Image input: attachments as a file path or a base64 blob, PNG, JPEG, WebP and GIF. Whether a given model, or Free's Auto choice, accepts images. | Confirmed / Unknown | `python/README.md` / not stated |
| Audio and video input. | Unknown, treat as no | Not documented |

### 2B.7 Terms

- **Confirmed:** no SDK-specific terms exist. The SDK is MIT; the CLI licence allows bundling unmodified; Copilot use falls under the GitHub Terms of Service and the Acceptable Use Policies.
- **Confirmed:** no rule like SIWC's "connected application only" was found. Nothing requires one sign-in per app.
- **Decided:** the GitHub OAuth App is registered under Community Access, one per app (decisions 9 and 16), and users authorise it by name. That is a normal GitHub integration, not token sharing.
- **Unknown:** whether the CLI sends telemetry by default. The SDK has optional OpenTelemetry (`[telemetry]` extra). Gate G5 measures the CLI.
- **Unknown:** the Copilot product-specific terms for individuals were not read in full.

## 2C. Engine comparison

Small on purpose. "Plan" means a subscription the user already pays for or has free.

| | Codex app-server | Copilot SDK | ChatGPT direct | Own key | Hosted free AI | Local |
|---|---|---|---|---|---|---|
| Auth | SIWC per app | GitHub device flow, our OAuth App | SIWC per app | key in Credential Manager | QUILL sign-in | none |
| Cost to user | ChatGPT plan | Copilot plan, Free included | ChatGPT plan | per token | $0 | $0 |
| Multi-step tools | yes, `dynamicTools` (experimental) | yes, Python handlers (GA) | no | Native loop | Native loop | Native loop, model-dependent |
| Vision | yes, per model | attachments yes; tool-result images unknown | yes | per provider | per model | some models |
| Size | 92 MB zip, 284 MB exe | 113 MB zip, plus 1 MB wheel | in tree | in tree | in tree | model files |
| Terms | strict, preview | ordinary GitHub terms | strict, preview | provider's | ours | none |
| Maturity | preview | GA, changing owner | shipped | shipped | shipped | shipped |

The direct routes stay the default for single-shot work under either engine.

### 2C.1 Can a ChatGPT plan run inside the Copilot harness?

Short answer: **no, not in the Copilot SDK or the Copilot CLI.** Nothing documents it, though no page forbids it in so many words. Read 2026-10-31.

- **SDK bring-your-own-key** takes provider types `openai`, `azure` and `anthropic`, with an API key, a key command or a bearer token. There is no ChatGPT sign-in. Confirmed: github.com/github/copilot-sdk/blob/main/docs/auth/byok.md
- **CLI bring-your-own-key** is the same three types, key or bearer token only. Confirmed: docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-llm-models
- **Agent HQ** runs OpenAI Codex as a coding agent for Copilot Pro+ and Enterprise, on github.com, GitHub Mobile and VS Code. It is billed to the Copilot plan (one premium request a session), not to ChatGPT, and no CLI or SDK route is mentioned. Confirmed: github.blog/changelog/2026-02-04-claude-and-codex-are-now-available-in-public-preview-on-github/
- **VS Code** signs in to ChatGPT only for the Codex harness: the experimental agent host (`chat.agentHost.codexAgent.enabled`, then "Sign in to ChatGPT"), or the separate OpenAI Codex extension. Copilot Chat itself uses GitHub sign-in or keys. So what people see in VS Code is Codex beside Copilot, not Copilot spending a ChatGPT plan. Confirmed: code.visualstudio.com/docs/agents/run/agent-harnesses
- **SIWC terms** on running the plan inside another vendor's harness: unknown, to verify. The live terms page refuses automated reads. Section 2.7's "connected application only" (from the 2026-10-21 archive) points against it in any case.

**How QUILL presents both anyway:** as two separate connections in one window, side by side (section 10A). "My ChatGPT plan" and "Codex" use the ChatGPT sign-in; "My GitHub Copilot" uses the GitHub sign-in. A person with both picks one, and Which AI (Ctrl+8) always says which. Nothing pretends one runs inside the other.

## 3. What the family already has

This is the inventory an agent would draw its tools from. Every path below was checked on 2026-10-31. Nothing here exposes these as model tools yet, except the editor tools in 3.2.

### 3.1 AI routes and engines already in the tree

| Route | Where | Auth |
|---|---|---|
| ChatGPT plan, direct | `quill/core/ai/chatgpt_account.py`, `chatgpt_client.py` (`respond`, `image_part`, `list_models`), `chatgpt_ai_help.py`, `chatgpt_http.py` | SIWC per app |
| Hosted free AI (QUILL's service) | `quill/core/ai/gateway_client.py`, `gateway_session.py`, `gateway_privacy.py`, `quill/ui/hosted_ai_service.py` | QUILL sign-in |
| Own API key | `quill/core/ai/own_key.py`, `own_key_gemini.py`, `own_key_models.py` | user key in Credential Manager |
| Native harness | `quill/core/ai/harness/native.py`, `tool_loop.py`, `tool_planner.py` | any of the above |
| SDK packs | `quill/ai_packs/copilot.py` (GitHub device flow, section 3.7), `claude.py` (key), `openai_agents.py` (key) | per pack |
| Local models | `ollama_capabilities.py`, `llama_cpp_backend.py`, `foundation_models.py` | none |
| External JSONL engine | `quill/core/ai/external_engine.py` | none |

Notes on these routes:

- **Route order:** `AiService.route` in `hosted_ai_service.py` picks `chatgpt`, then `own_key`, then `free`.
- **Engine registry:** `quill/core/ai/engines.py` `build_engine_registry()` lists Native plus the packs, for selection only.
- **Pack rule:** packs run the vendor agent text-only. QUILL owns every edit (memory, PR #801).

ChatGPT agent names now in use:

| App | Agent name | Where |
|---|---|---|
| QUILL | "QUILL" | `quill/ui/main_frame_hosted_ai.py:61` |
| QUILL Lite | "QUILL Lite" | `quill/apps/lite_services.py:53` |
| Radio | "QUILL Radio" | `quill/ui/radio/ask_radio_window.py:43` |
| Cast | "QUILL Cast" | `quill/ui/podcasts/cast_ai_host.py:58` |
| Transcribe | borrows "QUILL" | `quill/apps/transcribe_review.py:53` |

Studio, Converter, Player, Weather, Inkwell, Beacon and Social have no ChatGPT sign-in today.

### 3.2 The agent tool surface that exists today

**Editor tools.** `quill/core/ai/agent_tools.py`, `TOOL_DESCRIPTORS`, is the one definition every harness uses:

- `read_selection`
- `read_document`
- `read_outline`
- `read_section`
- `read_app_state`
- `replace_selection`
- `insert`
- `apply_patch`
- `run_command`
- `audit_accessibility`
- `web_search` (asks consent)
- `web_fetch` (asks consent)

`MUTATING_TOOL_NAMES` marks the ones that change state. `execute_tool()` maps each name to the gateway.

**Gateway.** `quill/core/ai/tool_gateway.py`, `SafeEditorToolGateway`, does three things on every call:

- checks permission and writes an `ActivityLog` entry;
- emits an `AgentEvent`;
- shows a diff review for edits of medium risk and above.

**Permission broker.** `quill/core/ai/permissions.py`, `PermissionBroker`:

- Categories: `READ_SELECTION`, `READ_DOCUMENT`, `READ_WORKSPACE`, `MODIFY_SELECTION`, `MODIFY_DOCUMENT`, `CREATE_FILE`, `GITHUB`, `TERMINAL`, `WEB`, `MEMORY`, `RUN_COMMAND`.
- Decisions: allow, ask, preview_required, deny.

**The `run_command` floor.** `quill/core/ai/agent.py`, `SAFE_TOOL_IDS`, holds 22 command ids:

- File: `file.save`, `file.save_all`, `file.new`.
- Edit: `edit.undo`, `edit.redo`, `edit.select_all`, `edit.find`.
- Format: bold, italic, the four case changes, bullet list, numbered list.
- Tools: `tools.word_count`, `tools.spell_check_dialog`, the two read-aloud commands.
- Navigation and view: three heading-navigation commands, soft wrap, the command palette.

**Assistant command tools.** `quill/core/assistant.py`, `build_assistant_tools()`:

- Turns every registered command into an `AssistantTool`.
- Adds five content tools: `get_document_text`, `get_selection`, `get_outline`, `replace_selection`, `insert_at_cursor`.
- The UI side is `quill/ui/assistant_tools.py`.

**Agent specs.** `quill/core/ai/agents/*.md` holds 17 specs, for example:

- `accessibility-editor`
- `meeting-notes-to-actions`
- `plain-language-rewriter`
- `summarizer`
- `quill-concierge`
- `researcher`
- `reviewer`

**Missing.** There is no app tool surface outside the editor. Studio, Radio, Cast and the others have commands and core functions, but no tool descriptors.

### 3.3 Command tables and keymaps

| App | Where commands live | Size |
|---|---|---|
| QUILL | `quill/core/keymap.py` `DEFAULT_KEYMAP` | 516 bound chords |
| QUILL Lite | `quill/core/lite/commands*.py`; `tests/unit/ui/fixtures/lite_command_coverage.json` | 282 classified handlers |
| Radio | `quill/core/app_keymaps.py` `APP_KEYMAPS["radio"]` | 96 |
| Cast | `APP_KEYMAPS["cast"]` | 43 |
| Studio | `APP_KEYMAPS["studio"]` | 25 |
| Weather | `APP_KEYMAPS["weather"]` | 11 |
| Converter, Inkwell, Player, Transcribe, Beacon | their own menus (`converter_menu.py`, `inkwell.py`, `player_menus.py`, `transcribe_menus.py`, `beacon/commands.py`) | not in `APP_KEYMAPS` |

`APP_KEYMAPS` has entries only for studio, radio, cast and weather.

### 3.4 Each app, as tools an agent could call

**QUILL (editor)**

- Editor tools and gateway: section 3.2.
- Document conversion with Pandoc:
  - `quill/core/convert_formats.py`: 25 curated outputs (gfm, docx, epub, pdf, html5, odt, rtf, latex and others) and 17 inputs.
  - `quill/core/pandoc_formats.py`, `pandoc_install.py`.
- Image alt text:
  - `quill/core/inline_image_alt.py` reports present or missing alt text at the caret.
  - `quill/core/link_inventory.py` audits every image and link (GLOW).
- Vision:
  - `quill/core/ai/vision.py`: `describe_image`, `build_image_description_body`.
  - `vision_prompts.py`.
- Git: `quill/core/local_git.py`, `git_sync.py`, `git_worktree.py`, `git_binaries.py`.
- Structure: `heading_levels.py`, `outline.py`, `auto_outline.py`, `table_studio/`, `spellcheck.py`, `grammar_check` (`quill/core/ai/grammar_check.py`).
- OCR:
  - `tesseract_install.py` and `pdf_ocr_install.py` (local);
  - `datalab_ocr.py` (cloud);
  - `pdf_open.py`.
- Read aloud: `quill/core/read_aloud.py`, `quill/core/ai/tts.py`.

**QUILL Lite**

- The same shared modules. Lite's commands are in `quill/core/lite/commands.py` plus the `commands_ai`, `commands_dictation`, `commands_review` and `commands_words` modules.
- Hosted AI comes from `quill/ui/hosted_ai_*.py`, which QUILL shares.

**Studio**

The `APP_KEYMAPS["studio"]` commands:

- Capture: `studio.capture`, `studio.capture_active`, `studio.capture_desktop`, `studio.capture_selected`, `studio.inspect_capture`.
- Demo recording: `studio.record_demo`, `studio.record_pause`, `studio.record_marker`, `studio.record_mute`, `studio.record_status`, `studio.record_window`, `studio.record_emergency_stop`, `studio.record_discard`, `studio.record_recover`.
- Camera, mixer and AI video: `studio.camera_check`, `studio.mixer`, `studio.ask_ai_video`.
- Pictures and video: `studio.picture_video`, `studio.make_picture`.
- Broadcast: `studio.broadcast`, `studio.broadcast_mute`, `studio.broadcast_stop`.

Core code:

- Pre-flight: `quill/core/demo_recording.py`, with `PreflightFacts` and `preflight(plan, facts) -> list[Finding]`. The rules are in `demo_recording_rules.py`: `screen_findings`, `sound_findings`, `tool_findings`.
- After recording: `quill/core/demo_recording_verify.py` reopens the MP4 with ffprobe and FFmpeg and rates it Verified, Needs review or Failed.
- Video review: `quill/core/video_review.py` builds a contact sheet of 4 to 16 frames, 2048 pixels wide, labelled with times, plus a transcript excerpt.
- Screenshots: `quill/core/studio_capture.py` and `studio_capture_ai.py` (prompts and grounded questions).
- Mixer: `quill/ui/studio_mixer.py`.
- Other: `quill/core/picture_video.py`, `quill/core/streaming.py`, `demo_camera.py`, `demo_recording_ffmpeg.py`.

**Converter (audio and video, not documents)**

- `quill/apps/converter.py`: audio to audio, video to audio, and video to video. It has effect recipes, a 15-second preview, Join into One File, and Split by Chapters.
- Formats (`quill/core/audio/formats.py`):
  - 52 audio input extensions and 30 video input extensions.
  - 25 audio outputs, including mp3, m4b, flac and opus.
  - 9 video outputs, including mp4, mkv and webm.
- Engine: `quill/core/audio/convert.py`, `dsp.py`, `effect_recipes.py`, `chapter_plan.py`, `assemble.py`, `media_probe.py`.
- Settings ids: `converter.format`, `converter.preset`, `converter.effect`, `converter.chapters`, `converter.trim`.

**Radio**

96 commands. The ones an agent would use:

- Recording: `radio.record_station`, `radio.schedule_recording`, `radio.stop_all_recordings`.
- Finding and playing: `radio.find_streams`, `radio.browse`, `radio.play_favorite`.
- Song information: `radio.identify_song`, `radio.whats_playing_details`, `radio.song_history`, `radio.lyrics`.
- Other: `radio.wake_timer`, `radio.update_catalog`.

Core code:

- Search: `quill/core/radio/federated_search.py`, `directory_search.py`.
- Scheduling: `recording_schedule.py` (`RecordingScheduleEntry`, `next_occurrence`, `due_entries`).
- Recording: `recording_commands.py`, `recording_center.py`.
- Lists: `favorites.py`, `song_history.py`, `now_playing.py`.
- Assistant: `quill/core/radio/assistant_prompt.py` (quick questions).

**Cast**

43 commands. The ones an agent would use:

- Feeds and folders: `podcasts.refresh_feed`, `podcasts.move_to_folder`, `podcasts.new_folder`, `podcasts.mark_all_played`.
- Playback: `podcasts.go_to_position`, `podcasts.episode_bookmarks`.
- Hosted AI: the `tools.hosted_ai_*` commands.

Core code in `quill/core/podcasts/`:

- `ai_listening.py` ("the model proposes; the listener disposes");
- `ai_organise.py`;
- `chapter_inference.py`;
- `episode_filters.py`;
- `directory_search.py`, `itunes_search.py`, `apple_podcasts.py`.

**Transcribe**

- Speech-to-text engines, all local:
  - `quill/core/speech/providers/whispercpp.py`;
  - `fasterwhisper.py`;
  - `moonshine_tiny.py`;
  - `sherpa_shared.py`.
- Dictation: `quill/core/windows_dictation/` (`file_transcribe.py`, `local_recognizer.py`, `post_passes.py`, `review_conversation.py`, `review_session.py`).
- Diarization: `quill/core/ai/diarization.py`.
- App modules: `quill/apps/transcribe_*.py`, including `transcribe_files.py`, `transcribe_review.py` and `transcribe_practice.py`.

**Player**

- `quill/apps/player.py`: the shared `PlayerPanel`, `BookmarkStore`, resume, and Go to Position.
- Settings ids: `player.speed`, `player.skip_silence`, `player.sleep`.

**Weather**

- 11 commands: `weather.now`, `weather.quick`, `weather.alerts`, `weather.add_location`, `weather.noaa_listen`, `weather.monitor_toggle` and others.
- `quill/core/weather/`: `nws.py`, `open_meteo.py`, `geocoding.py`, `astronomy.py`, `monitor.py`, `headless_check.py`.

**Inkwell**

- `quill/apps/inkwell.py`: one shared `abbreviations.json` with QUILL.
- Expansion code: `quill/core/abbreviations_store.py`, `abbreviations.py`, `abbreviations_contributed.py`, and `quill/core/expansion/` (`matcher.py`, `fields.py`, `targets.py`, `undo.py`).

**Beacon**

- `quill/apps/beacon/`. The headless CLI `cli.py` has `capture`, `search` and `export` (json, html, markdown, csv, opml, m3u, text).
- Store: `db.py`.
- `assist.py` provides local `suggest_tags`, `extractive_summary`, `suggest_relationships`, and a `SemanticIndex` hook.

**Social**

- `standalone/social/quill_social/`, outside `quill/`, so no repo gate scopes it.

### 3.5 Shared local engines

| Engine | Where |
|---|---|
| STT | `quill/core/speech/providers/*`, `quill/core/windows_dictation/`, `quill/core/ai/transcription.py` |
| TTS | `quill/core/speech/piper_install.py`, `espeak_install.py`, `dectalk_say.py`, `quill/core/ai/tts.py`, `quill/core/read_aloud.py`, `voice_catalog.py` |
| OCR | `quill/core/tesseract_install.py`, `pdf_ocr_install.py` |
| FFmpeg | `quill/core/speech/ffmpeg.py`, `quill/core/audio/ffmpeg_live.py`, `demo_recording_ffmpeg.py` |
| Pandoc | `quill/core/pandoc_formats.py`, `convert_formats.py` |
| Git | `quill/core/local_git.py`, `git_binaries.py` |

### 3.6 Quillins

- Host: `quill/core/quillins/` (`host.py`, `host_worker.py`, `protocol.py`, `registry.py`).
- 23 bundled in `quill/quillins_bundled/`, for example `studio-normalizer`, `weather-extra-alerts`, `radio-community-directory`, `text-tools` and `brf-tools`.
- The manifest (`quill/core/schemas/extension.json`) contributes `commands`, `hotkeys`, `abbreviations`, `transcription_providers`, `feed_auth_providers` and `directory_providers`.
- An agent can reach a Quillin's command only through the host's command table, never directly.

### 3.7 What QUILL already has for Copilot

Checked 2026-10-31. Line numbers are from `main` at `0e447bcd6`.

**Implemented:**

- **The harness interface.** `quill/core/ai/harness/__init__.py`: `HarnessCapabilities` (line 41), `AgentSpec` (67), `AIContext` (101), `HarnessResult` (114), `HarnessSession` (127), `Harness` (137), `HarnessRegistry` (156). Every engine drives the same `SafeEditorToolGateway` and `PermissionBroker`.
- **The pack base.** `quill/ai_packs/_base.py`: `SdkHarness` (170) and `_SdkSession` (108). A session calls the SDK once for text (`Invoke`, line 53), then applies it once through the gateway, as a replace or an insert (157-160). It is single-shot by design.
- **The Copilot pack.** `quill/ai_packs/copilot.py`: `CopilotHarness` (26), capabilities with `tool_calling`, `mcp`, `skills`, `subagents` and `requires_oauth` set (32-43). `_make_invoke` (45-83) opens `CopilotClient()`, creates a session whose permission handler rejects everything (59-63), and calls `session.send(prompt)` (73).
- **Selection.** `quill/core/ai/engines.py` `build_engine_registry()` (35); `quill/ai_packs/__init__.py` `all_packs()` (38); `quill/core/ai/quick_switch.py` keeps the preferred engine; `quill/ui/agent_editor_host.py` `_select_responder` (428-462) runs the chosen pack and falls back to Native.
- **Install on demand.** `quill/core/ai/sdk_install.py`: `PACK_INSTALLS["copilot"]` is `github-copilot-sdk>=1.0` (80-85); `install_pack` (286) runs `pip install --only-binary=:all: --target` into a user folder. `pyproject.toml:363` declares the extra `ai-copilot = ["github-copilot-sdk>=1.0.15rc3"]`. `quill/__main__.py:442-449` adds installed packs to `sys.path` at start.
- **Sign-in.** `quill/core/ai/copilot_auth.py`: GitHub device flow (`GITHUB_DEVICE_AUTH_URL`, line 44), scope `read:user` (48). The token goes to the GitHub token store (DPAPI) and is exported to `GITHUB_TOKEN` and `GH_TOKEN` in QUILL's own process (51, 91-102). Egress entry `core/ai/oauth_poster.py::_real_opener` in `quill/tools/network_egress_entries.py:399`.
- **UI.** `quill/ui/copilot_onboarding_dialog.py`: Install, then Sign in (two steps). `quill/ui/ai_hub_engines_panel.py:125-135` and `quill/ui/main_frame_ai_actions.py:279-292` open it. The wizard's "agent" path is in `quill/core/ai/onboarding.py:105-117` and `:239`.

**How it authenticates:** GitHub OAuth device flow against the app's own OAuth App. Each app's client id is built in (`CLIENT_IDS` in `quill/core/ai/copilot_auth.py`, registered 2026-11-02, one per app, device flow on, no client secret). `QUILL_GITHUB_CLIENT_ID` is now only a developer override, honoured in a dev build. An app with no client id still falls back to telling the user to run `copilot` or `gh auth login` in a terminal (`copilot_onboarding_dialog.py`).

**What it reaches:** whatever model the CLI defaults to. No model is chosen, no image is sent, no tool is offered, and no streaming is read. Text only.

**Stubbed, missing or wrong:**

- **The answer is probably a request id.** Current docs say `session.send` "returns a request ID" and does not wait. The pack would then insert an id string, not the answer (`copilot.py:73-79`). Inferred from docs, not run. The fix is `send_and_wait` or the event stream.
- **No tool allowlist.** The session is made without `available_tools`, so the model is offered every built-in and each one is then refused (`copilot.py:70-72`). That costs tokens and invites refusals.
- **Not multi-step.** QUILL's tools are never registered, though `agent_tools.py:1-14` was written for exactly that.
- **The runtime is fetched from the network.** Nothing sets `COPILOT_CLI_PATH` or `COPILOT_SKIP_CLI_DOWNLOAD`, so the SDK downloads the CLI on first use. That and the pip install both break bundle-everything.
- **The token leaks to children.** It sits in `os.environ`, and `harness_credentials.scrubbed_child_env()` (line 83) removes only `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` (line 30). Quillin workers and external engines inherit `GITHUB_TOKEN`.
- **One token, two uses.** The Copilot token shares the GitHub token store with the GitHub repository features (`quill/core/github/token_store.py`). Inferred: signing out of one signs out of the other.
- **Dead commands.** `quill/core/github/gh_bridge.py:149-174` calls `gh copilot suggest` and `explain`, bound as `github.copilot_suggest` and `github.copilot_explain` (`quill/ui/main_frame_gh_bridge.py:318-325`). GitHub retired that extension on 2025-10-25 (github.blog changelog 2025-09-25). Out of scope here, but they should go.
- **Only QUILL.** No other app reaches the Copilot engine.

## 4. Rules that bind this work

From `S:\QUILL\CLAUDE.md` and memory:

- **Safe Mode:** `quill/stability/safe_mode.py`, `should_enable_safe_mode`, turns off AI. The engine refuses to start under it.
- **GATE-9 egress:**
  - A child process's network calls are not Python `urlopen` sites, so the gate cannot see them. A reviewed entry of a new kind is needed in `quill/tools/network_egress_entries.py`.
  - Verify with `pytest tests/unit/tools/test_network_egress_audit.py`. The module CLI is a no-op (memory note).
- **External-engine allowlist:**
  - `_ENGINE_EXECUTABLE_BASENAMES` in `quill/core/ai/external_engine.py` lists node, python, python3 and quill-engine.
  - That module is "spawned per request and torn down", with no daemon.
  - App-server is long-lived, so it does not belong there (section 5.2).
  - The same goes for the Copilot CLI. The SDK starts it, not `external_engine.py`, so the allowlist is never consulted. Adding `copilot.exe` there would only widen a list that guards something else.
  - Do not install the Copilot CLI through npm: that needs Node 22, and `node` on the allowlist would then be one step from running arbitrary scripts.
- **Accessibility gates:**
  - GATE-13: say only what the screen reader does not.
  - GATE-BRAILLE.
  - GATE-14 access keys.
  - F1 help: inline `SetHelpText`.
  - Dialogs: `_show_modal_dialog`, `bind_close_button`.
  - GATE-REACH.
- **QUILL Lite is never ahead of QUILL.** The engine goes in shared `quill/core/ai`, and QUILL gets every capability in the same change.
- **Bundle everything.** No downloads at install or first use (`feedback_bundle_everything.md`). The only standing exception is optional dictation models. The existing SDK packs predate this rule: they pip-install from PyPI on demand, and the Copilot SDK then downloads its runtime (section 3.7). Both have to change.
- **Errors:** GATE-EC `CodedError` with `QUILL-AI-...` codes.
- **Size:** GATE-11 module budgets.

## 5. Architecture

### 5.1 Shape

```
 app window (Studio, QUILL, Radio, ...)
   |  approvals, progress, results in QUILL's own accessible UI (agent window, NEW)
   v
 ToolSession (NEW protocol in quill/core/ai/harness/__init__.py)
   |  one interface, two adapters; both emit EXISTING AgentEvent
   +--> CopilotToolHarness (EXTENDS quill/ai_packs/copilot.py)
   |      FamilyTool -> copilot Tool(handler=...); permission callback -> Approver
   |      copilot.exe (bundled, COPILOT_CLI_PATH) --(user's GitHub token)--> Copilot
   +--> CodexHarness (NEW quill/core/ai/harness/codex.py)
          FamilyTool -> dynamicTools; item/tool/call -> handler
          codex-app-server.exe (bundled) --(this app's plan token)--> api.openai.com
   |
   v
 FamilyToolRegistry (NEW quill/core/ai/family_tools.py)
   |  EXISTING agent_tools.TOOL_DESCRIPTORS + execute_tool, plus per-app wrappers (section 3)
   |  every call -> EXISTING PermissionBroker, ActivityLog, diff review via SafeEditorToolGateway
   v
 Approver (NEW, wx side): the one approval dialog, through _show_modal_dialog
```

The direct routes stay the default for single-shot work: `chatgpt_client.respond`, own key, hosted free AI and local. That covers summaries, Ask About an Image and Ask QUILL Radio. An engine is used only where a task needs several steps with tools.

### 5.1a What exists and what is new

**Existing, reused unchanged:**

- `Harness`, `HarnessRegistry`, `HarnessCapabilities` (`harness/__init__.py`), and `build_engine_registry()` (`engines.py`) for selection.
- `quick_switch.preferred_harness_id` and the AI Hub Engines tab, for choosing the engine.
- `agent_tools.TOOL_DESCRIPTORS`, `MUTATING_TOOL_NAMES` and `execute_tool`. Its own docstring already plans to "register them as the SDK's custom tools".
- `SafeEditorToolGateway`, `PermissionBroker`, `ActivityLog`, `AgentEvent`, `diff_review.build_diff_review`.
- `copilot_auth` device flow and `CopilotOnboardingDialog`; `ChatGptAccount` and `hosted_ai_chatgpt.py` for ChatGPT.

**New:**

- **`ToolSession`.** Today `HarnessSession.run()` is one shot: `_SdkSession` gets text once and applies it once (`_base.py:142-163`). The new protocol is `start_tool_session(agent, ctx, tools, approver, emit)`, returning a session with `run()`, `cancel()` and `send(follow_up)`. It is added beside the old one, so Native and the existing packs keep working. A new capability flag, `app_tools`, says which engines can take it.
- **`FamilyToolRegistry`.** Each `FamilyTool` has a name, a description, a JSON schema, a `PermissionCategory`, a risk level, a scope (which app), and a handler that returns text or an image. Both adapters translate from this one list, so a tool is written once.
- **`Approver`.** A small protocol in core (`ask(tool, summary) -> once | task | deny`), with one wx implementation. The Copilot permission callback and the Codex approval requests both end here. So does the broker's "ask".
- **The adapters.** Copilot: about 200 lines over the Python SDK; tool handlers run in our process. Codex: a JSON-RPC client and a process manager (section 5.2), more code, because there is no Python SDK for app-server.

**Threading, both engines:** the engine runs on `QuillTaskManager`. A tool handler that needs approval posts to the UI thread with `wx.CallAfter` and waits on a future. The Copilot SDK is asyncio, so its loop lives on that worker thread, never on the UI thread.

### 5.2 New modules (none exist yet)

**`codex_app_server.py`** (wx-free, strict-typed)

- **Binary:** resolves the exe only from the bundled runtime folder. Checks OpenAI's Authenticode signature or a build-pinned SHA-256 before every launch.
- **Launch:** passes `--listen stdio://`, the `-c` overrides from section 2.1, and the switches from section 2.4. Sets `CODEX_HOME` to `app_data_dir()/ai/codex/<slug>`.
- **Token:** passes `ACCESS_TOKEN` only in the child's environment. Adds a redaction pattern in `quill/stability/redaction.py`.
- **Refresh:** serializes refreshes, then restarts and resumes.
- **Interrupt and shutdown:** sends `turn/interrupt`, and kills the child when the app closes.
- **Process start:** launches through `quill/stability/safe_subprocess.py`.

The external-engine allowlist does not change. The launcher has its own constant: one basename, one bundled path, one pinned hash.

**`harness/codex.py`, `CodexHarness`**

- Implements `Harness`.
- Capabilities: `tool_calling`, `images` and `requires_oauth` on; `mcp` and `audio` off.
- Registered in `build_engine_registry()`.

**`quill/ai_packs/copilot.py`, extended to `CopilotToolHarness`** (the pack stays in `ai_packs`, the SDK import stays lazy)

- **Binary:** `CopilotClient(connection=RuntimeConnection.for_stdio(path=<bundled copilot.exe>))`, with `COPILOT_SKIP_CLI_DOWNLOAD=1`. Check the exe's SHA-256 against the build pin before launch.
- **Token:** pass `github_token=` explicitly, read from the store at session start. Stop exporting it to `os.environ`; add `GITHUB_TOKEN`, `GH_TOKEN` and `COPILOT_GITHUB_TOKEN` to `scrubbed_child_env()` and a redaction pattern for `gho_`.
- **Environment:** the child gets a minimal `env=`, and `working_directory` is an empty per-app folder under `app_data_dir()/ai/copilot/<slug>`, so the built-in read tools would find nothing even if one slipped through.
- **Tools:** `available_tools` lists only our tool names, never empty (CLI issue #5306). Each `FamilyTool` becomes a `copilot.tools.Tool` whose handler calls the registry.
- **Permissions:** `on_permission_request` approves `custom-tool` requests for our names only after the broker or the `Approver` says yes, and rejects every other kind with feedback. Our tools are not marked `skip_permission`.
- **Streaming:** `streaming=True`; `assistant.message_delta` becomes `AGENT_TEXT_DELTA`; `session.idle` ends the turn; `assistant.usage` feeds the usage line.
- **Prompt:** `system_message` mode `append` with the agent spec, so the vendor's safety section stays in place.
- **Interrupt:** Stop aborts the session and closes the client. The exact abort call is not yet confirmed in the Python docs (G4).
- **Text-only path kept:** the existing single-shot use moves to `send_and_wait`, which also fixes the request-id bug.

**`family_tools.py`, `FamilyToolRegistry`**

- Starts from `agent_tools.TOOL_DESCRIPTORS` and `execute_tool`, so editor tools behave exactly as they do under Native.
- Adds one namespace per app (`studio.*`, `radio.*` and so on). Each tool is a thin wrapper over a function or command already listed in section 3.
- Each tool carries a `PermissionCategory` and a risk level.
- Serialized to `dynamicTools` for Codex and to `copilot.tools.Tool` for Copilot. Neither adapter defines a tool of its own.
- New `PermissionCategory` values are needed: `CAPTURE_SCREEN` and `RECORD_AUDIO`, and `SCHEDULE` for writes that act later. That is new work in `permissions.py`.

**`quill/ui/codex_agent_window.py`**

- One shared, accessible window for both engines: a conversation, a status line ("Using ChatGPT plan" or "Using GitHub Copilot"), an approval panel, and a Stop button bound to the session's cancel. Name it `agent_window.py`, not after either vendor.

### 5.3 Approvals

- **Built-in command and file approvals** should never arrive, from either engine. If one does (a Codex `requestApproval`, or a Copilot request of kind shell, write, read, url, mcp or memory), decline it and log a defect.
- **App tool calls:** the broker decides.
  - "Ask" uses a dialog through `_show_modal_dialog`. It has one sentence on what will happen, and three buttons: Allow once, Allow for this task, Don't allow. Enter means Allow once. Escape means Don't allow.
  - "Preview" reuses `diff_review.build_diff_review`.
- **Reads** inside the app's own scope are allowed.
- **Writes, recordings, sends, deletions and scheduling** ask every time, unless the user chooses "for this task". Nothing carries over between tasks.
- **Spoken output** follows GATE-13: speak the outcome, never the fact that a dialog opened.

### 5.4 One engine, separate connections

- Each app starts its own child process, with its own `ChatGptAccount` token, its own `clientInfo.name` (equal to its agent name) and its own `CODEX_HOME`.
- No app, Quillin or other process borrows another's token or process.
- Transcribe gets its own "QUILL Transcribe" sign-in first (risk R1).
- Quillins may contribute commands that appear as tools. They never receive a token or a way to ask the model directly, because that would be "general-purpose API access for other tools".
- Seven apps have no sign-in today: Studio, Converter, Player, Weather, Inkwell, Beacon and Social. Each needs one, reusing `quill/ui/hosted_ai_chatgpt.py`. That is new wiring for each app.

**Superseded 2026-10-31:** Jeff decided each app signs in separately, GitHub included (section 10A.2). The paragraph below is kept as the earlier reasoning; the token-store split still stands.

**Copilot is different.** GitHub's terms have no per-app rule (section 2B.7), and a device-flow sign-in per app would mean typing a code nine times.

- One GitHub sign-in for the family, stored once. Each app reads it and passes it to its own child process.
- The token is never in any process's environment, and a Quillin never sees it.
- Give the Copilot token its own store entry, apart from the GitHub repository features, so signing out of one does not sign out of the other (inferred problem, section 3.7).
- Settings vocabulary: the "which engine" setting is `shared` across apps that have it.

## 6. Features, derived from the inventory

Ranked by value to blind and low-vision users. Two questions decide the rank:

- What can a person do alone with this that today needs sighted help or a long manual workaround?
- How much of it already exists in section 3?

Each feature lists:

- **Existing:** tools that already exist and would be wrapped.
- **New:** work that does not exist yet.

| Rank | App | Feature | Existing share | Engine fit |
|---|---|---|---|---|
| 1 | Studio | Recording pre-flight check | High | Either |
| 2 | QUILL, Lite | Multi-step document tasks | High | Either; Copilot first |
| 3 | Studio | Describe a recording with timestamps | High | Codex until G6 |
| 4 | QUILL | Propose alt text for document images | Medium | Codex until G6 |
| 5 | Radio, Cast | Find it and record or follow it | Medium | Either |
| 6 | Transcribe | Speakers, sections and summary | Medium | Either; text only |
| 7 | Converter | "Make this right for my player" | Medium | Either; text only |
| 8 | Studio | Accessible narrative of a recording | Medium | Codex until G6 |
| 9 | Weather | "Should I go out?" | High | Either; text only |
| 10 | Beacon | Organise what I saved | High | Either |
| 11 | Player | Find the part where | Low | Either |
| 12 | Inkwell | Suggest abbreviations | Medium | Either |
| 13 | Social | Read and reply with care | Blocked (R8) | Either |

### 6.0 Which engine fits

Every feature calls the same `FamilyToolRegistry` tools, so the engine is the user's choice, not the feature's. The differences that matter:

- **Text-only features** (6.2, 6.5, 6.6, 6.7, 6.9 to 6.12) call tools that return text: `read_outline`, `read_section`, `apply_patch`, `audit_accessibility` and the per-app read wrappers over `federated_search.py`, `recording_schedule.py`, `media_probe.probe`, `nws.py`, Beacon's `db.py` and `abbreviations_store.py`. Both engines take these. Copilot Free makes them reachable at no cost.
- **Picture features** (6.1's preview still, 6.3, 6.4, 6.8) need a tool that returns an image: `studio.preview_still`, `studio.contact_sheet`, `doc.image`, over `studio_capture.py`, `video_review.py` and `vision.describe_image`. Codex takes `inputImage` in a tool result (confirmed). Copilot takes images as message attachments; images in tool results are unknown. Gate G6 settles it. Until then, Copilot gets pictures by the agent asking and QUILL attaching the image to the next message, which costs one extra turn.
- **6.1 on Copilot:** the check works on text facts alone (`preflight` findings and the mixer's device names). The picture is optional, so it fits either engine now.
- **Writes that act later** (6.5's `radio.schedule_recording`) behave the same under both: the recorder runs it, never the model.

### 6.1 Studio: recording pre-flight check (Phase 4c, the second agent feature)

**Existing:**

- `demo_recording.preflight(plan, facts)` and `PreflightFacts`;
- `demo_recording_rules.screen_findings`, `sound_findings`, `tool_findings`;
- `studio.camera_check`;
- `studio.capture_active`, for one preview still;
- `studio.mixer`, for device and level state.

**New:**

- Wrappers `studio.read_preflight` (facts plus findings, as text), `studio.preview_still` (one image), and `studio.open_mixer` (the existing command; asks first).
- A "QUILL Studio" sign-in.
- The `CAPTURE_SCREEN` permission.

**What the user gets:** a short checklist in plain words. Example: "The microphone is the webcam mic, not the USB headset. The captured window is Settings, not the browser you named."

**Never sent:** audio or video. One still per check, and the user agrees first.

### 6.2 QUILL and QUILL Lite: multi-step document tasks

**Existing:**

- All of `TOOL_DESCRIPTORS`: `read_outline`, `read_section`, `apply_patch`, `audit_accessibility` and the rest;
- `SAFE_TOOL_IDS`;
- agent specs `accessibility-editor.md`, `meeting-notes-to-actions.md`, `plain-language-rewriter.md` and `summarizer.md`, used as `developerInstructions`.

**Dictation cleanup:** speech to text stays local (`windows_dictation/post_passes.py`). Only the text goes to the model.

**New:**

- the Codex harness;
- a test that Lite reaches it only through the shared module (the `main_frame_hosted_ai.py` pattern).

**Examples:**

- "Fix the heading levels, then build a table of contents, then list broken links."
- "Turn these notes into actions grouped by owner."

### 6.3 Studio: describe a recording with timestamps

**Existing:**

- `video_review.py` contact sheets with time labels and a transcript excerpt;
- the `studio.ask_ai_video` command;
- `vision.describe_image`.

**New:**

- `studio.contact_sheet(start, end, frames)`, returning an image;
- `studio.transcript_excerpt(start, end)`.

**Fit with the plan:** video input is refused on the plan, but still images are accepted. The existing contact-sheet design is the right one.

### 6.4 QUILL: propose alt text for document images

**Existing:**

- `link_inventory.py`, which lists images;
- `inline_image_alt.py`, which reports missing alt text;
- `vision.describe_image`;
- `apply_patch` with diff review.

**New:**

- `doc.list_images`;
- `doc.image(i)`, returning an image;
- a way to write alt text into Markdown and HTML (today the code only reports it);
- the same through the Pandoc import path (`convert_formats.py`), so a DOCX or EPUB that has been opened gets proposals too.

**Lite:** gets it in the same change.

**Correction to the brief:** the brief placed this in Converter. Quill Converter (`quill/apps/converter.py`) converts audio and video only. Document conversion is QUILL's Pandoc path.

### 6.5 Radio and Cast: find it, then record or follow it

**Existing reads:**

- `radio.find_streams` with `federated_search.py` and `directory_search.py`;
- `recording_schedule.next_occurrence`;
- `song_history.py`, `favorites.py`;
- Cast's `directory_search.py`, `itunes_search.py`, `episode_filters.py`.

**Existing writes (each asks):**

- `radio.record_station`, `radio.schedule_recording`;
- `podcasts.move_to_folder`, `podcasts.new_folder`;
- Cast's follow action.

**New:**

- wrappers that return station and episode rows as text;
- the `SCHEDULE` permission.

**No background use:** the recording runs in Radio's own recorder. The agent never wakes later, so there is no background plan use.

### 6.6 Transcribe: speakers, sections and summary

**Existing (local):**

- whisper.cpp and faster-whisper providers;
- `diarization.py`;
- `review_conversation.py`.

**New:**

- `transcribe.read_transcript` and `transcribe.write_sections` (with preview);
- Transcribe's own sign-in (R1).

**The model's part:** it sees only text. It names speakers from context and writes a summary and an action list.

### 6.7 Converter: "make this right for my player"

**Existing:**

- `media_probe.describe` and `probe`;
- `formats.AUDIO_OUTPUT_FORMATS` with its constraints;
- `effect_recipes.py`;
- `chapter_plan.py`;
- Split by Chapters and Join into One File.

**New:**

- `converter.probe(file)`, `converter.list_formats` and `converter.queue_job(settings)` (asks first);
- a "QUILL Converter" sign-in.

**What it does:** the model reasons over probe text, never over audio. Example request: "Make these 40 MP3s one M4B audiobook with a chapter per file, at a size my phone can hold."

### 6.8 Studio: accessible narrative of a recording

- **Existing:** 6.3, plus the transcript beside the video, plus QUILL for the result.
- **New:** an "assemble narrative" agent spec, and a hand-off that opens the result as a new QUILL document.

### 6.9 Weather: "should I go out?"

- **Existing:** `nws.py`, `open_meteo.py`, `astronomy.py`, `weather.alerts`.
- **New:** `weather.forecast_text` and `weather.alerts_text` wrappers, plus a sign-in.
- **No change to the alert check:** `headless_check.py` stays model-free. Nothing runs on a timer.

### 6.10 Beacon: organise what I saved

- **Existing:** `cli.py` `search` and `export`, `db.py`, and `assist.suggest_tags` and `suggest_relationships` (local).
- **New:** `beacon.search`, plus `beacon.tag` and `beacon.move` (both ask), and a sign-in.

### 6.11 Player: find the part where

- **Existing:** bookmarks, chapters, and Go to Position in `player.py`.
- **New:** a transcript source. None exists in Player; it would come from Transcribe's local engine. Plus a sign-in.
- **Ranked low** because the transcript is the expensive part, and that part is local work.

### 6.12 Inkwell: suggest abbreviations

- **Existing:** `abbreviations_store.py` and `expansion/matcher.py`.
- **New:** read a document the user picks, propose entries, and add them (asks).
- **Limit:** system-wide expansion is never driven by the model.

### 6.13 Social: read and reply with care

- **Blocked** until `standalone/social/quill_social` moves under `quill/` (R8).
- **When unblocked:** posting is an irreversible send and always asks, with the full text read back first.

## 7. What stays local, or needs a separately billed key

| Job | On the plan? | Route |
|---|---|---|
| Speech to text | No: refused | Local whisper.cpp, faster-whisper or Moonshine (bundled). The OpenAI dictation option stays own-key and consented (`transcribe_commands._agree_to_openai`). |
| Text to speech | Not listed; treat as no | Piper, eSpeak, SAPI, DECtalk or Kokoro. Cloud TTS (`cloud_tts.py`, `elevenlabs_tts.py`, `gemini_tts.py`) only with the user's own key. |
| Image generation | No: refused | Own key only (`quill/core/ai/image_generation.py`), never through the agent. |
| OCR | Not needed | Local Tesseract |
| Video | Input refused | FFmpeg frames into a contact sheet, sent as images |
| Web search | Policy-dependent | Off by default. Follows `chatgpt_account.set_web_search`. |

The column is for the ChatGPT plan. Under Copilot the answers are the same in practice: no audio or video input is documented, image generation is not offered, and the CLI's own `web_fetch`-style tools stay off. QUILL's consented `web_search` and `web_fetch` tools from `agent_tools.py` are the only route to the web under either engine.

## 8. Consent, privacy and usage display

### First run, in each app

- A welcome dialog, as the guidelines describe:
  - eligible AI requests in this app use the user's ChatGPT plan;
  - what the agent can and cannot touch;
  - nothing is sent until the user starts a task;
  - a "Manage usage" link to `USAGE_URL`.

### Before each task

- One line on what may be sent, for example "one picture of your screen and the names of your audio devices".
- Images always need their own check box or an explicit command.

### Background use

- None in phases 1 to 4.
- Anything later needs express, per-app, revocable consent. It runs only while the app is open, and every run is logged in the `ActivityLog`.

### Usage

- "Using ChatGPT plan" is shown in the status line.
- `usedPercent` and the reset time are shown if `account/rateLimits/updated` reports them (unknown).
- On a 429, the app speaks once, offers Manage usage, does not retry, and does not silently switch to a key.
- **Copilot:** "Using GitHub Copilot" in the status line. `account.getQuota` gives used, entitlement, remaining percent and reset date (confirmed), so the window can say "62 percent of this month's Copilot allowance left, resets November 1" on request, not on every turn. A "Manage Copilot usage" link opens the user's GitHub billing page. Never convert nano-AI units to money; the docs say not to.
- **Consent:** the first-run dialog says which engine, and what leaves the machine, in the same words for both.

### Local data

- Thread files are kept for the length of one task, in the app's own `CODEX_HOME`, so a token refresh can resume the task. They are deleted when the task ends, on Stop, and again at the next start (decision 4). Copilot session state under its per-app `working_directory` follows the same rule.
- The token lives only in memory and in the child's environment.
- Crash bundles (`quill/stability/crash_report.py`) redact `ACCESS_TOKEN` and exclude `CODEX_HOME`.

### Telemetry

- Whether app-server sends analytics or OpenTelemetry is unknown. `configRequirements/read` exposes `otel`, and `analytics_*` feature flags exist.
- Whether the Copilot CLI sends telemetry is unknown. Do not install the SDK's `[telemetry]` extra.
- Gate G5 checks both with a network capture.

## 9. Packaging

### Size

- About 92 MB compressed and 284 MB installed for x64. The shared runtime is about 335 MB (memory: runtime layering).
- Whether the app-server exe needs the `codex-windows-sandbox-*` helpers with the shell switched off is unknown. They are about 80 MB more.
- Ship it once in the shared runtime, not in each installer, starting with the release that carries Phase 4b. No opt-in download (decisions 1 and 8).

### Signing

- Ship OpenAI's signed exe unchanged.
- `scripts/code_signing.py` must skip it.
- Check its signature at run time.

### Notices

- Apache-2.0 goes in `quill/core/third_party_notices.py` and `docs/legal`.

### Version pin

- Pin one Codex release per QUILL release.
- Generate the JSON schema at build time and test against it. `dynamicTools` is experimental, and `thread/revert` already replaced `thread/rollback`.

### Copilot

- **Node:** not needed. Ship the standalone `copilot-win32-x64.zip` build, not the npm package, which needs Node 22 (section 2B.2). The zip is 112,637,935 bytes for v1.0.105; the unzipped size is unknown until we unpack it.
- **The SDK:** `github-copilot-sdk` is a 925 KB pure wheel. Bundle it in the shared runtime as an ordinary dependency instead of pip-installing it on demand. Its dependencies are pydantic 2.11+, httpx and python-dateutil; check which the runtime already has (memory: runtime layering).
- **The runtime:** ship `copilot.exe` once in the shared runtime, beside app-server if both ship. Set `COPILOT_CLI_PATH` and `COPILOT_SKIP_CLI_DOWNLOAD=1` so the SDK never downloads. The CLI licence allows this, unmodified and only as part of QUILL, with its licence file shipped (section 2B.7).
- **Signing:** ship GitHub's exe unchanged; `scripts/code_signing.py` must skip it. Whether it carries an Authenticode signature is unknown; pin its SHA-256 from `SHA256SUMS.txt` at build time either way.
- **Version pin:** one CLI version and one SDK version per QUILL release. The SDK negotiates protocol versions 2 to 3, but pin both anyway.
- **External-engine allowlist:** unchanged (section 4).
- **Notices:** MIT for the SDK; the GitHub Copilot CLI License text for the exe.
- **Both engines:** about 205 MB compressed between them. That is the real cost of offering both. Decided: both in the shared runtime, each from the release that first uses it (decisions 1 and 8). Measure the Copilot CLI's unpacked size in Phase 2 and record it here.
- **Retire:** `PACK_INSTALLS["copilot"]` and the Install step of the onboarding dialog, once the SDK is bundled. Sign-in becomes the only step.

### Gates

- GATE-9: a child-process egress entry for each engine. The Copilot CLI talks to GitHub's Copilot endpoints; G5 records which hosts.
- GATE-REACH: the agent window.
- F1 audits.
- Settings vocabulary for any new setting.
- `mypy quill\core` covers the new core modules.

## 10. Risks

- **R1. Transcribe borrows QUILL's sign-in** (`transcribe_review.py:53`).
  - Under "Connected application only" this is arguable now and not acceptable for an agent.
  - Fix it first.
- **R2. Preview programme.**
  - Every SIWC page says "preview", and `dynamicTools` is experimental.
  - Mitigation: pin versions, generate schemas, keep the direct client, and keep the engine optional.
- **R3. Built-in tools.**
  - Turning them off is undocumented, and a future version could add a default-on tool.
  - Run gate G3 on every pinned version.
- **R4. Size.** See section 9.
- **R5. "Alter, reverse engineer, or otherwise amend the SIWC software".**
  - Never patch or rebuild the exe.
- **R6. The shared Plus five-hour limit.**
  - One long Studio job can starve QUILL.
  - Cap turns and frames, and say up front when a task is large.
- **R7. Confidently wrong descriptions** to someone who cannot check them.
  - Everything is a proposal (the `ai_listening.py` rule).
- **R8. Social sits outside `quill/`,** so no gate checks it.
- **R9. The terms page blocks automated reads.**
  - The text quoted here is from a 2026-10-21 archive.
  - Re-read the live page by hand before shipping.
- **R10. GitHub OAuth App: resolved 2026-11-02.**
  - Jeff registered one OAuth App per family app under Community-Access, with device flow on and no client secret.
  - Their client ids are built into `CLIENT_IDS` in `quill/core/ai/copilot_auth.py`; `QUILL_GITHUB_CLIENT_ID` is only a dev-build override.
  - They ask for `read:user` only, which is enough for Copilot. The GitHub workbench (Manage GitHub Accounts) still takes a pasted token; giving it a browser sign-in would need the scopes it uses and is an open decision.
- **R11. The Copilot SDK is changing owner.** GitHub to Microsoft, in phases, no dates.
  - Package names, sign-in or billing could move. Pin versions; keep the adapter thin; re-read the announcement each release.
- **R12. Tool filtering has sharp edges.**
  - An empty CLI allowlist means all tools (issue #5306, open). Never pass an empty list; gate G3 records what the model was offered on every pinned version.
- **R13. Images through tools on Copilot are unknown.** The picture features fall back to attachments (section 6.0) until G6.
- **R14. Fewer users have Copilot than ChatGPT.** Copilot Free costs nothing but needs a GitHub account and Auto model only. Not everyone in the audience has GitHub. That is why Codex still follows.
- **R15. Organisations can switch the CLI off.** A Business or Enterprise user may find Copilot refused. Say so in one sentence and offer the other routes.
- **R16. The existing pack is broken and nobody noticed.** The request-id bug (section 3.7) suggests it has never run end to end. Phase 0 starts by making the text-only path work.

## 10A. Choose Your AI: the connection layer

Decided by Jeff on 2026-10-31. One window, shared by QUILL and QUILL Lite and then by every QuillVille app, built in the shared hosted-AI layer (`quill/ui/hosted_ai_*.py`) so neither editor is ahead (rule 10). The aim is "magical and simple": a person picks where their AI comes from once, hears which one is in use with one key, and is never surprised.

### 10A.1 Where we start: today's code

- **Precedence is silent.** `AiService.route` (`quill/ui/hosted_ai_service.py:143-150`) returns `"chatgpt"` when this app is signed in to ChatGPT, else `"own_key"` when a key is saved for the chosen provider, else `"free"`. The docstring of `chatgpt_active` (`:128-141`) says why: "a sign-in somebody made is the choice". Every request method branches on the same order: `ask` (`:237-309`), `converse` (`:318-386`), `describe_image` (`:388-427`), `limits` (`:159-176`).
- **The guard catches changes, not choices.** `RouteGuardMixin` (`quill/ui/hosted_ai_route_guard.py:66-91`) remembers the route used this session and asks Yes/No before a request goes to a different company. `route_chosen` (`:61-64`) marks a deliberate change. It cannot see a change between sessions (`:27-29`).
- **The words live in one place.** `RouteWords` (`quill/ui/hosted_ai_route_words.py:81-132`) and `route_names` (`hosted_ai_route_guard.py:49-59`) say what each route is called and who receives the text.
- **Own key.** `OwnKeyRouteMixin` (`quill/ui/hosted_ai_own_key_route.py:21-52`): provider, model, and `own_key_can_see` (`:48-52`), true only for Gemini. The provider is an explicit choice (`ai_own_key_provider`, `quill/core/settings.py:297`, `quill/core/lite/settings.py:224`).
- **ChatGPT plan.** `ChatGptAccount` (`quill/core/ai/chatgpt_account.py:197`), one per app under its own agent name (`hosted_ai_service.py:109-126`). Models from `list_models` (`quill/core/ai/chatgpt_client.py:121-142`), which keeps the server's order because that order is OpenAI's recommendation (`:125-127`). The chosen model is `ChatGptState.model` (`quill/core/ai/chatgpt_state.py:40`).
- **Free AI.** `GatewayLimits` (`quill/core/ai/gateway_client.py:99-120`) carries `feature_flags`, `features` and `web_search_enabled`; `GatewayQuota` (`:151-174`) carries the daily and monthly counts.
- **Commands.** `HostedAiMixin` (`quill/ui/hosted_ai_commands.py:49`) holds the shared handlers: `cmd_ai_own_key` (`:136-154`), `cmd_ai_sign_in` (`:156-163`), `cmd_ai_usage` (`:115-134`). The ChatGPT rows are in `hosted_ai_chatgpt_commands.py`; the Ask About an Image check is at `:85-97`. QUILL reaches all of them through the adapter `QuillAiHost` in `quill/ui/main_frame_hosted_ai.py:51-142`, which has no commands of its own (`:31`).
- **Engines are a separate choice.** `quill/core/ai/quick_switch.py` keeps the preferred agent engine in `<app data>/ai/active-harness.json` (`:61-78`) and cycles among ready ones (`:149`). `HarnessCapabilities` (`quill/core/ai/harness/__init__.py:41-63`) already has `images`, `audio`, `tool_calling` and `streaming` flags.
- **Copilot sign-in.** `quill/core/ai/copilot_auth.py`: device-flow URLs (`:44-45`), scope `read:user` (`:48`), client id from `QUILL_GITHUB_CLIENT_ID` (`:54-56`), token exported to `os.environ` (`:91-102`).

### 10A.2 The five connections

| Row, as heard | Sign-in | What it is |
|---|---|---|
| QUILL's free AI | none to choose; Connect as today | the default; QUILL's service and its limits |
| My ChatGPT plan | Continue with ChatGPT, per app | direct to OpenAI on the person's plan |
| My GitHub Copilot | GitHub device code, per app | Copilot SDK, Copilot Free included |
| Codex, for tasks | the same ChatGPT sign-in | the agent engine of section 2, on the plan |
| My own key | paste a key, OpenAI or Gemini | billed per request by that company |

Each is one keypress (free, Codex once ChatGPT is signed in) or one sign-in. Each app signs in separately, as the SIWC terms require. Jeff extended that to GitHub on 2026-10-31, which replaces the "one GitHub sign-in for the family" in section 5.4.

### 10A.3 The window, as a screen-reader user meets it

Opened by Ctrl+4 (section 10A.9), or from AI > Choose Your AI. The title is "Choose Your AI". Focus lands on the connection list, on the row in use. There are five controls in tab order, and nothing else: no tabs, no Advanced page.

1. **Connections** (`&Connections`): a single-column list. Each row reads as name, then state: "QUILL's free AI, in use"; "My ChatGPT plan, signed in"; "My GitHub Copilot, not set up"; "Codex, for tasks, not set up"; "My own key, OpenAI, signed in". Three states only: In use, Signed in, Not set up. A fourth, "Signed out by GitHub" (or OpenAI), appears after a revoked token (10A.5). Enter does the action button's job. Delete on a signed-in row signs it out, after a Yes/No with No as the default.
2. **About this connection**: a read-only line, two sentences at most, rewritten as the selection moves. Who receives the text, what it costs, and what it can do, from the capability registry: "Text and pictures. Agent tasks: yes. Billed to your Copilot plan."
3. **Model** (`&Model`): a choice list filled from the selected connection's own discovery (10A.7). The first item is the service's recommendation, marked "(recommended)". Disabled with one item, "Sign in to see the models", when the row is not set up.
4. **The action button.** One button whose label follows the row: "&Use This" on a signed-in row, "&Sign In..." on a row not set up, "Sign &Out" on the row in use. The three letters are distinct and collide with nothing else here (GATE-14).
5. **Close.** No access key; Escape and Enter-on-Close close it (dialog rule; `bind_close_button`).

**What is spoken (GATE-13).** Nothing on open, on a selection change or on focus: the reader already says the title, the row and its state. The app speaks only outcomes it alone knows, through the announcement service, so they are brailled too (GATE-BRAILLE): "Now using My GitHub Copilot." "Signed in to My ChatGPT plan. It is now in use." "Signed out. No AI is in use until you choose one." When an action changes a row's state, the row text changes too, so a second press of Up and Down reads the truth.

**F1.** Inline `SetHelpText` on each of the five controls, and a surface purpose for the window, in the shared help engine (`quill/ui/app_context_help.py`).

**Sign-in, the same shape for all five.** The action button opens one small sign-in step, through `_show_modal_dialog`. Same layout, same sentences, only the nouns change:

- one sentence: "To use My GitHub Copilot, approve QUILL on GitHub's page."
- for a code: a read-only field with the code, spaced out for the reader (`SignInCode.spoken`, `hosted_ai_service.py:60-69`), already on the clipboard;
- **Open the Page** (default) and **Cancel**;
- on success the step closes itself, and the window says "Signed in to My GitHub Copilot. It is now in use."

ChatGPT and Codex use the existing loopback sign-in (`quill/core/ai/chatgpt_loopback.py`). Copilot uses the device code. Own key uses the existing `OwnKeyDialog` (`quill/ui/hosted_ai_own_key.py`), whose Provider list stays. The free AI uses the existing Connect step (`AiSignInFrame`, `quill/ui/hosted_ai_dialogs.py`). Codex, once ChatGPT is signed in, needs no second sign-in: Use This is the one keypress.

### 10A.4 First run and empty states

- **Nothing is chosen at first run, and nothing is sent.** The free AI is the default row and reads "in use". No network call happens until somebody asks (`hosted_ai_service.py:16-19`); the privacy agreement still comes first (`_ask_ai_privacy`, `hosted_ai_commands.py:299`).
- **No model list yet:** the free AI's model row says "QUILL chooses the model" and is disabled. Copilot Free says "Auto (Copilot Free chooses)", because Free gets Auto selection only (section 2B.6).
- **Discovery failed:** "Could not read the model list. The recommended model is used." Never a stale hard-coded list.
- **Organisation switched Copilot off** (R15): the row says "My GitHub Copilot, not available for your account", and About says why in one sentence.
- **Safe Mode:** the window opens and says, in About, that AI is off in Safe Mode. Nothing can be signed in.
- **The free AI's Connect step stays** (decision 23). The first AI command goes from the privacy agreement straight to the code, already filled in. It is the gateway's human step against scripted accounts, so it never happens by itself.

### 10A.5 Sign-in, sign-out, a revoked token, a limit

- **Sign-in** makes that connection the active one, and calls `route_chosen()` (`hosted_ai_route_guard.py:61-64`). That is Jeff's rule: signing in is choosing.
- **Use This** on a signed-in row makes it active without signing anything.
- **Sign Out of the row in use** leaves no AI in use. The next AI command opens Choose Your AI on the connection list and says, once, "No AI is in use. Choose one." It never quietly drops to the free AI or a key (decision 15).
- **Sign Out of another row** changes nothing about which one is in use.
- **A revoked token** (401 from OpenAI or GitHub, or a refresh that fails): nothing is sent, the row becomes "Signed out by OpenAI", and the app says "Your ChatGPT plan sign-in has ended. Nothing was sent. Press Ctrl+4 to sign in again or choose another." No retry and no fallback. The route guard (`:66-91`) stays as the backstop for any case this misses.
- **A limit is reached:** the ChatGPT plan's 429 `subscription_sharing_usage_limit_exceeded`, Copilot's quota, the free AI's `GatewayQuota`, or an own key's 429. Spoken once, never retried, never switched: "Your ChatGPT plan's limit for QUILL is reached. Nothing was sent. Manage usage is in the Usage window." The 503 `subscription_sharing_usage_unavailable` gets the bounded retry OpenAI asks for (errors-and-recovery page), and then the same sentence.

### 10A.6 Data model and settings

- **One stored choice:** `ai_connection: str`, with values `free`, `chatgpt`, `copilot`, `codex`, `own_key`, and `""` meaning "not yet decided". The same field name in `quill/core/settings.py` and `quill/core/lite/settings.py`, so the settings-vocabulary gate (`quill/tools/settings_vocabulary_audit.py`, snapshot `tests/unit/ui/fixtures/settings_vocabulary_inventory.json`, line 42 of the audit) classifies it `shared`, not `missing`. Regenerate with `--write`.
- **Per-connection model:** existing fields stay. ChatGPT is `ChatGptState.model`; the own key is `ai_own_key_model` (`settings.py:294`, `lite/settings.py:223`). New: `ai_copilot_model` and `ai_codex_model`, both editors, same names. The free AI has none.
- **Migration, so nobody's behaviour changes:** on the first read where `ai_connection` is empty, it is set once to what `route` returns today (ChatGPT signed in, else own key active, else free), and saved through `write_json_atomic`. From then on `route` returns the stored choice, provided that connection is ready. If it is not ready, the request fails with the revoked-token sentence above; it does not fall through.
- **Other apps:** each app's own settings get the same field name. Whether the vocabulary gate covers settings outside the editor pair: to verify.
- **Secrets are untouched:** keys stay in Credential Manager, ChatGPT refresh tokens in the OS store per app, the Copilot token in its own store entry per app, keyed by the app's agent name and apart from the GitHub repository features (section 5.4, decision 11), never in a settings file.

### 10A.7 The capability registry

New, wx-free and strict-typed: `quill/core/ai/connection_caps.py`. One record per connection, plus a per-model override when the service reports it.

| Capability | Free | ChatGPT plan | Copilot | Codex | Own key |
|---|---|---|---|---|---|
| Text | yes | yes | yes | yes | yes |
| Pictures in | no | per model | per model, as attachments | per model | Gemini yes; OpenAI route here no |
| Agent tools | no | no (direct route) | yes | yes | no in this layer |
| Web search | if `web_search_enabled` | account policy | QUILL's consented tool only | QUILL's consented tool only | no |
| Streaming | no | yes (required) | yes | yes | per provider |
| Image generation | no | no | no | no | own key only |
| Speech out, speech in | no | no | no | no | own key or local only |

Where each fact comes from, never guessed:

- **Free:** `GatewayLimits.features` and `feature_flags` (`gateway_client.py:111-115`), fetched as today; pictures are "no" because `describe_image` has no free branch (`hosted_ai_service.py:395-398`).
- **ChatGPT plan and Codex:** the SIWC preview-limitations page (section 2.5) for the refusals; per-model image support from the model metadata the plan's `/models` returns, to verify which field carries it.
- **Copilot:** the SDK's `models.list` at run time, which reports models per plan (section 2B.6). The vision flag's exact field name: to verify. Images in tool results: G6.
- **Own key:** `own_key_can_see` (`hosted_ai_own_key_route.py:48-52`) today; then each provider's model metadata through `own_key_models.list_models` (`quill/core/ai/own_key_models.py:227`).
- **Image generation and speech:** `quill/core/ai/image_generation.py`, `cloud_tts.py`, `elevenlabs_tts.py`, `gemini_tts.py` on an own key; Piper, eSpeak, SAPI, DECtalk and Kokoro locally (section 7). These never appear as a plan capability, and the About line says so plainly: "Pictures made by AI need your own key."

### 10A.8 Capability gating: one rule

**The rule: an AI command is always listed and keyed, and it never pretends.** When the connection in use cannot do it:

- The menu label says what it needs, after the name: "Ask About an Image (needs a connection that sees)...". Menus already rebuild when the route changes (`QuillAiHost.rebuild_all_menus`, `main_frame_hosted_ai.py:131`). The item stays enabled and keeps its key, so the menu accelerator rule holds; only a disabled status readout is exempt from showing a key, and these are commands.
- Pressing it sends nothing. It says which connections can, and offers the switch in one key: "Pictures need a connection that can see. My ChatGPT plan can. Switch to it and ask?" Yes and No, with Yes the default because the person just asked for this. Yes calls `route_chosen()`, so it is a choice, not a fallback. When no connection that is set up can do it: "Pictures need My ChatGPT plan, My GitHub Copilot, Codex or a Gemini key. Choose one now?" and Yes opens Choose Your AI on that row.
- Agent tasks follow the same rule. On the free AI, "Fix headings, then build a table of contents" is listed with "(needs Copilot or Codex)".

Why this rule rather than hiding: a hidden command is one nobody learns exists, and a disabled one is skipped by arrow keys in some readers and says "unavailable" with no reason. The sentence on press is something only the app knows, so it is not over-announcing (GATE-13).

**New gate, GATE-CAPS:** every hosted-AI entry point declares the capabilities it needs (`requires=("pictures",)`), and a test fakes each connection's registry record and asserts that no request reaches a connection whose record lacks one. A source scan fails any `service.ask`, `converse`, `describe_image` or engine call that bypasses `require(...)`. A capability claim in `connection_caps.py` must name its source (a doc URL or a discovery call) in a field the test checks is non-empty.

### 10A.9 Keys

Checked on 2026-10-31 against `DEFAULT_KEYMAP` and `DEFAULT_ALIASES` (`quill/core/keymap.py:67`, `:1271`), every QUILL Lite row in `quill/core/lite/commands*.py`, `APP_KEYMAPS` (`quill/core/app_keymaps.py:24`) and the system-wide keys in `quill/core/family_chords.py:67-73`. The only plain chords free in both editors and in all four `APP_KEYMAPS` are Ctrl+3, Ctrl+4 and Ctrl+8. Everything else free was an Alt+letter (menu access keys), an Alt+F4 neighbour (rule 4), a Ctrl+Alt+digit (AltGr on international layouts, the keymap's own warning at `keymap.py:236-246`), or a key taken system-wide (Ctrl+Alt+Shift+Q, R, F11, F12).

| Command | Chord | Rules |
|---|---|---|
| Which AI Am I Using | Ctrl+8 | rule 3: a quick question, so a short key; it sits in the AI row Ctrl+6, 7, 9 (`keymap.py:268-270`) |
| Choose Your AI... | Ctrl+4 | free in both (rule 5); also Ctrl+8 pressed twice |
| Ask (10C) | Ctrl+6, as today | rule 2: both editors already have it |

- **Ctrl+8, Which AI Am I Using.** Speaks one line: the connection, the model, and one usage clause where the service gives one. "My GitHub Copilot, Auto. 62 percent of this month's allowance left, by GitHub's count." Pressed twice within the existing double-press window (`main_frame.py:7465`, 0.5 seconds) it opens Choose Your AI, like the echo double-press set at `main_frame.py:7453-7463`.
- **Ctrl+4, Choose Your AI.** Not the F-keys past F9 that rule 9 suggests: none is free in both, and this is not a once-a-year command for someone trying the services. Rule 7 says editor chords are for the editor, but rule 6 outranks it here: QUILL Lite reaches its AI on plain chords, so QUILL cannot bury this on the leader.
- **Existing commands keep their keys and ids (rule 5: nothing moves).** Use My Own AI Key (Alt+F2), Use My ChatGPT Subscription (Alt+F5) and Connect or Sign Out (QUILL Ctrl+Alt+Shift+F4, Lite Ctrl+Alt+Shift+F10) each open Choose Your AI with their own row selected and its sign-in step ready. Their ids stay in keymaps, the parity table and people's overrides. Radio's Alt+F5 (`radio.chatgpt_account`, `app_keymaps.py:297`) and Cast's (`:361-369`) do the same.
- **To verify:** Ctrl+4 and Ctrl+8 in the apps whose menus are not in `APP_KEYMAPS` (Converter, Player, Inkwell, Transcribe, Beacon, Social), and Cast's quick-actions list, which answers Ctrl+1 to Ctrl+N inside the list (`quill/ui/podcasts/manager_menus.py:440-442`). The menu-shape gate checks Word for Ctrl+4 and Ctrl+8.

### 10A.10 The status bar

- One status cell, "AI", in every app that has a status bar: "AI: ChatGPT plan" or "AI: Copilot, Auto". It is the same text Ctrl+8 speaks, shortened. Enter on the cell opens Choose Your AI.
- QUILL Lite's twelve cells are catalogued in `quill/apps/lite_status_cells.py`; this is a thirteenth, with its F1 sentence. Decided (decision 19): short and placed last, so it cannot push the editing cells onto another row, and the same cell in QUILL in the same change. It is text, like everything else (decision 13).

### 10A.11 Usage, made easy

What each service actually exposes, read 2026-10-31:

| Connection | What the service reports | Status |
|---|---|---|
| Free AI | `GatewayQuota`: daily and monthly used and cap, reset time, web searches (`gateway_client.py:151-174`) | confirmed, in code |
| ChatGPT plan | no usage API and no rate-limit headers; a 429 when a limit is hit, which may be a per-app limit, so never infer the reset | confirmed, developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery |
| ChatGPT plan, per-app limits | Settings > Usage shows use per app and a weekly cap per app | unknown, to verify (help.openai.com/en/articles/20001542 refused automated reads) |
| Copilot | SDK `account.getQuota`: `quotaSnapshots` for `premium_interactions`, `chat`, `completions`, each with `entitlementRequests` (-1 is unlimited), `usedRequests`, `remainingPercentage`, `resetDate`; per call `assistant.usage` with tokens and cost; counters reset on the 1st, UTC | confirmed, github.com/github/copilot-sdk docs/features/usage-and-billing.md; docs.github.com/en/copilot/how-tos/premium-requests/monitoring-your-copilot-usage-and-entitlements |
| Codex | `account/rateLimits/read` and `/updated`: `primary` and `secondary` windows with `usedPercent`, `windowDurationMins`, `resetsAt`, plus `planType` and credits | confirmed that they exist, learn.chatgpt.com/docs/app-server; whether they report under the SIWC provider: unknown (section 2.2) |
| Own key, OpenAI | `x-ratelimit-limit-*`, `-remaining-*`, `-reset-*` headers per response; usage and costs endpoints need an admin key, which QUILL will never ask for | confirmed, developers.openai.com/api/docs/guides/rate-limits |
| Own key, Gemini | limits per project (requests a minute, tokens a minute, requests a day, reset at midnight Pacific); no endpoint or header reports what is left; a 429 RESOURCE_EXHAUSTED | confirmed, ai.google.dev/gemini-api/docs/rate-limits |

**A gap in our own code:** the comment at `chatgpt_account.py:92-93` says "QUILL keeps a local count of requests", but no counter exists in the ChatGPT modules. `ChatGptAnswer` does carry the token counts OpenAI reports (`chatgpt_client.py:76-83`). The local count is new work.

**One Usage view.** The existing Usage command keeps its keys (QUILL Ctrl+Alt+Shift+F2, Lite Ctrl+Alt+Shift+F9) and opens one window for every connection, in place of today's three (`cmd_ai_usage`, `hosted_ai_commands.py:115-134`). It is a read-only list, one row a connection that is set up, each row saying whose number it is:

- "QUILL's free AI: 14 of 50 requests today, by QUILL's count. Resets at midnight."
- "My ChatGPT plan: 23 requests today from QUILL, counted on this computer. OpenAI sets the limits; Manage usage opens them."
- "My GitHub Copilot: 41 of 300 premium requests this month, by GitHub's count. Resets November 1."
- "My own key, OpenAI: 480 requests left this minute, from OpenAI's last answer. Your bill is on OpenAI's page."

One button, **Manage Usage**, opens the selected connection's own page (`USAGE_URL`, `chatgpt_account.py:94`; `_USAGE_URLS`, `own_key.py:102-105`; GitHub's billing page). Ctrl+8 speaks the in-use row's usage clause; the window holds the rest. A local count is always called a local count; a service's number is always named as the service's. Money is never computed from AI Credits.

**Everything is text (Jeff, 2026-10-31).** Usage is a spoken and brailled sentence or a list, never a chart: no meter, gauge, progress bar or colour carries a number, in this window or anywhere else (decision 13).

### 10A.12 Copilot as a route

- **Chat and pictures** through the SDK: `send_and_wait` for single requests, streaming events for conversations, images as attachments (section 2B.6). This also fixes the request-id bug (section 3.7).
- **Sign-in** by GitHub device flow, which needs Jeff's GitHub OAuth App client id. None exists today (R10). Section 10F is Jeff's checklist. With per-app sign-in, each app gets its own registration (10F step 8).
- **Bundled:** `copilot.exe` and the SDK wheel in `standalone/runtime/quillville-runtime.spec`, with `COPILOT_CLI_PATH` and `COPILOT_SKIP_CLI_DOWNLOAD=1`; about 113 MB compressed, approved by Jeff. The runtime file inventory and its drift test get the new files. The CLI licence text goes in `quill/core/third_party_notices.py` and `docs/legal`. `scripts/code_signing.py` skips GitHub's exe, and the SHA-256 from `SHA256SUMS.txt` is pinned at build time (section 9).
- **Retired:** `PACK_INSTALLS["copilot"]` and the Install step in `copilot_onboarding_dialog.py`; sign-in becomes the only step.

### 10A.13 Codex as a route

- Codex is the agent engine of sections 2 and 5. It is listed as a connection, "Codex, for tasks", because it is a place AI comes from that a person chooses.
- **Multi-step tasks** use the app-server engine.
- **Single requests while Codex is in use** (Rewrite, Ask About an Image, Ask) go over the plan's direct route, `chatgpt_client.respond`, with the same per-app sign-in and agent name. Starting a child process for one rewrite would be slow for nothing. Ctrl+8 says so: "Codex, on your ChatGPT plan. Single requests go to the plan directly."
- Usage is the plan's, so it shares the ChatGPT row's clause.

### 10A.14 QUILL Lite parity

- The window, the registry and the gating live in shared modules: `quill/ui/hosted_ai_connections.py` (new, the window), `quill/core/ai/connection_caps.py` (new), and `AiService.route` reading `ai_connection`. QUILL reaches them through `main_frame_hosted_ai.py`, which still has no commands of its own; the test that asserts that absence stays.
- Parity-table rows in `quill/core/lite/parity.py`: `COMMAND_EQUIVALENTS` (`:170`) gains `cmd_ai_choose` to `tools.hosted_ai_choose` and `cmd_ai_which` to `tools.hosted_ai_which`; `SETTINGS_ALIASES` needs nothing, because the field names match.
- Gates that will check it: bound-command and family rules (`tests/unit/core/test_family_rules_and_gates.py`), menu accelerators (`tests/unit/ui/test_menu_accelerators.py`), menu shape, documentation chords and GATE-DOCKEY for the guides, GATE-LITE-COVER (`quill/tools/lite_command_coverage.py --write`) for behavioural tests of both new handlers, the settings vocabulary, GATE-REACH for the new window, the F1 audits, GATE-13 and GATE-BRAILLE, and the new GATE-CAPS.

## 10B. Pictures, video and sound across the family

**Decided by Jeff on 2026-10-31: everything is text.** No AI output in any app is a graph, chart, diagram or picture, and no usage view shows one; answers are sentences and lists (decision 13). **Decided, for pictures going in: "no pictures or video in the writing", as follows.** QUILL and QUILL Lite get no picture or video features of their own: no "what is on my screen", no screenshot comparison, no chart-to-table, no describe-a-frame. Pictures and video belong in the media apps (Studio, Radio, Cast, Player, Social, Weather, Beacon, Converter, Transcribe). **The one exception** is what an editor already does with a document's own images: the existing Ask About an Image (Ctrl+F5) and the alt-text work of section 6.4 (decision 13).

### 10B.1 What exists to build on

| Piece | Where | State |
|---|---|---|
| Describe an image | `quill/core/ai/vision.py`: `build_image_description_body` :84, `describe_image` :154; HEIC to JPEG :43; other files sent as raw bytes (:215) | exists |
| Plan image part | `chatgpt_client.image_part` (`quill/core/ai/chatgpt_client.py:145`), 20 MB cap (:65, :159) | exists |
| Alt text at the caret | `quill/core/inline_image_alt.py`: `image_at_position` :44, `describe_image` :64, `build_image_markdown` :72, `build_image_html` :94 | exists |
| Image and link audit | `quill/core/link_inventory.py`: `ImageAltRecord` :15, `collect_link_inventory` :34 | exists |
| Contact sheet | `quill/core/video_review.py` (`frame_times` :72, `grid` :80, `question_prompt` :123); the sheet is `contact_sheet()` in `quill/platform/windows/video_review.py:22`, called from `quill/apps/studio_picture_video.py:98-103` | exists |
| Capture facts | `quill/platform/windows/screen_recorder_check.py`: `gather_facts` :150, `trial_grab` :268, `exclude_from_capture` :128 | exists |
| Screen grabs | `quill/platform/windows/screen_capture.py`: `capture_screen` :119, `capture_clipboard_image` :55 | exists |
| Recording check | `quill/core/demo_recording_verify.py`: `classify` :222, `_picture_checks` :291 | exists |
| OCR, Windows | `quill/platform/windows/windows_ocr.py` (`recognize_with_windows_ocr` :54), wrapped by `quill/io/ocr.py` (`WindowsOcrBackend` :96, `ocr_image` :169) | exists |
| OCR, Tesseract | `quill/io/tesseract_ocr.py` (`ocr_image_with_tesseract` :155); PDF tier in `quill/io/docconvert.py:410` | exists |
| Studio vision chooser | `quill/apps/studio_vision_route.py:37`, `:65` | exists; folds into Choose Your AI |
| Radio video snapshot | `quill/ui/radio/video_commands.py`, `take_snapshot` :432 | exists |
| Scene-change frames | no `select=gt(scene)` or `scdet` anywhere; only `-frames:v` (`demo_recording_ffmpeg.py:184`) and `fps=` (:244) | new |
| Downscale before sending | no resize helper in `quill/core/ai` | new |
| Cast and Radio artwork | Cast keeps `artwork_url` only (`feed_reader.py:120`, `:481`; `models.py:89`), never downloaded; Radio has only `favicon_url` (`link_finder.py:128`) | new |
| Weather images | no radar or map images in the tree | new, and a new data source |
| Player video | `quill/apps/player.py` is audio only | not applicable |
| Transcribe slides | not found | new |

### 10B.2 The pipeline, done right (new module `quill/core/ai/picture_prep.py`)

1. **Local frames first.** FFmpeg extracts only what is needed: the frames the person names ("at 2 minutes 10"), an evenly spaced contact sheet (existing), or scene changes (new, the `select='gt(scene,0.3)'` filter, capped).
2. **Local text first.** Where the question is about words on screen, Windows OCR (`quill/io/ocr.py:169`) or Tesseract (`quill/io/tesseract_ocr.py:155`) answers it, and nothing is sent. The model gets the picture only when OCR is not enough, and the person is told which happened: "Read on this computer" or "Described by My ChatGPT plan".
3. **Fit the connection.** Downscale to the longest side the connection accepts and re-encode as JPEG or PNG, from the capability record (10A.7). New: today `vision.py` sends raw bytes.
4. **A strict cap.** At most one contact sheet of 16 frames (the existing `video_review` ceiling), or 4 single frames, per request. Nobody should be able to read this as a way around a service's limits.
5. **Timestamps carried through.** Every frame keeps its time; answers cite times ("at 01:42 a chart appears"), and Go to Position can follow them.
6. **Say what was inspected.** Every answer starts with one sentence: "Looked at 12 frames from 00:00 to 05:30, and the captions beside them."
7. **Cache.** The prepared image and the answer are kept by content hash and question for the session, so asking again costs nothing and sends nothing.

### 10B.3 Capability per connection, for pictures and sound

- **Pictures in:** ChatGPT plan and Codex per model; Copilot as attachments, per model (images in tool results: G6); a Gemini own key; the free AI no; an OpenAI own key no on this route (`hosted_ai_own_key_route.py:48-52`).
- **Video:** only ever as frames. No connection receives a video file.
- **Image generation:** own key only (`quill/core/ai/image_generation.py`; Studio's Make a Picture, `studio_picture_maker.py:19`). The menu label says so when another connection is in use: "Make a Picture (needs your own key)...".
- **Sound:** never sent to a plan. Speech to text is local (section 7); speech out is local or own key. A command that needs a cloud voice says "(needs your own key)" the same way.

### 10B.4 Consent and privacy

- **One first-time consent per app and per connection** for pictures: "Pictures you ask about in QUILL Studio go to OpenAI on your ChatGPT plan. Nothing is sent until you ask." Asked again when the connection changes, because the company changes.
- **A screenshot is never sent silently.** Every capture that would leave the machine is a command the person pressed, and the before-sending line names it ("one picture of the Studio window").
- **Before sending,** where possible, `exclude_from_capture` (`screen_recorder_check.py:128`) keeps QUILL's own windows out of the frame.

### 10B.5 Every place a picture meets a user

One key, the capability, the local preparation, what is spoken, and the fallback when the connection cannot see.

| App and moment | Key | Local first | Spoken | Cannot see |
|---|---|---|---|---|
| QUILL, Lite: an image in the document (the exception) | Ctrl+F5, as today | `image_at_position`; OCR for text in it | the description, then "Insert as alt text?" | 10A.8 switch offer |
| QUILL, Lite: make this document accessible (6.4) | an AI menu row | `collect_link_inventory` lists missing alt | "7 images lack alt text. Proposals are ready to review." | listed, needs a seeing connection |
| Studio: describe the current frame | Studio's Describe key | one frame, downscaled | description with the time | switch offer |
| Studio: scene list with times | menu row | scene-change frames, capped | "11 scenes", then a list | the frames' OCR text only |
| Studio: does this recording look right | after recording | `demo_recording_verify.classify` runs first | Verified or Needs review, then the model's reasons | local verdict only |
| Studio: framing advice, title cards and thumbnails | menu rows | one still, OCR for title text | short checklist | OCR text check only |
| Studio: accessible narrative (6.8) | menu row | contact sheet plus captions | opens as a QUILL document | transcript-only narrative |
| Radio: what is on the video stream | Radio's Describe key | `take_snapshot` (:432) | description | switch offer |
| Cast: episode artwork, show-note images | Cast's image key (Ctrl+Alt+F5, today's) | download the one image, downscale | description | the show notes' own alt text |
| Converter: pictures inside a file | menu row | FFmpeg extracts embedded cover art | "Cover art: ..." | file name and size only |
| Player | none | audio only | none | not applicable |
| Beacon: saved screenshots and attachments | menu row | OCR first; `Attachment` (`model.py:496`) | description, offered as a note | OCR text only |
| Social: alt text before sending, images in the feed | menu row, before Post | downscale | proposed alt text, read back in full | blocked until R8 |
| Weather: radar and maps | none until a source exists | new source needed | none | not applicable |
| Transcribe: slides beside a talk | menu row | scene-change frames from a video file | slide text with times | OCR text only |

### 10B.6 Bold ideas, marked

- **One Describe key for the family** (needs new work). The same command in every media app describes whatever is focused: an image, the current frame, a saved file. Ctrl+F5 where it is free; Cast keeps Ctrl+Alt+F5, because Ctrl+F5 is Refresh there (`app_keymaps.py`, `media.refresh_podcasts`). A per-app chord table is part of the work, checked by the documentation and DOCKEY gates.
- **Tell me when this changes** (needs new work). For a screen region in Studio or a video in Radio: a local pixel difference runs every few seconds, and the model is asked only when the picture changes beyond a threshold, at most once a minute, only while the person keeps it on, with a spoken start and stop. It is not background use: it is a foreground watch the person started, and it ends when the window closes.
- **Make this accessible** in QUILL (uses existing tools plus a little new). `collect_link_inventory` finds the images, `vision.describe_image` proposes each alt text, `apply_patch` with diff review applies them, one image at a time or all at once. On an agent connection this is one task; on a single-request connection it is a loop of single requests with the same review.
- **Read the picture, not the screen** (uses existing tools). Before any picture leaves, OCR answers "what does it say?", which covers many questions at no cost.

## 10C. Ask: one conversation in every app

### 10C.1 What exists today

| Surface | Where | Opened by | History |
|---|---|---|---|
| AI Pad | `quill/ui/hosted_ai_pad.py` | Ctrl+Alt+G, Ctrl+Alt+Z; Ctrl+6 opens it on Ask (`hosted_ai_answers.py:187-189`) | single requests |
| AI Conversation | `quill/ui/hosted_ai_chat.py` | the pad's chat row (`hosted_ai_pad.py:388-394`), Follow Up (`hosted_ai_answers.py:111`) | local `Conversation`, saved to `ai-sessions` via `record_exchange` |
| Saved Conversations | `quill/ui/hosted_ai_saved_chats.py:150` | a button in the chat window | shared store with Ask Quill |
| Ask Quill | `quill/ui/assistant_panel.py`, modeless | Alt+Q, Alt+Shift+Q for voice (`keymap.py:223`, `:307`) | saved via `record_exchange` |
| Ask QUILL Radio | `quill/ui/radio/ask_radio_window.py` | Ctrl+Shift+8 (`app_keymaps.py:296`) | in memory only (`:218-231`) |
| Cast answers | `quill/ui/podcasts/ai_answer_dialog.py:17-25` | Cast's AI features | none |
| AI Response | `quill/ui/ai_chat_dialog.py` | Advanced actions | none |

No surface keeps server-side state: no `previous_response_id`, no `conversation`, no `store=True` anywhere in `quill/` or `standalone/`. The ChatGPT client sends `"store": False` and resends the conversation each turn (`chatgpt_client.py:5-8`, `:240`), and `history_for` drops the oldest turns to fit and counts them (`quill/core/ai/hosted_chat.py:87-121`). That is exactly what the plan requires.

### 10C.2 Converge, do not multiply

- **One surface:** the AI Conversation window (`hosted_ai_chat.py`) becomes "Ask", in every app. Ask QUILL Radio becomes Radio's instance of it: its quick questions and context move to a Radio context provider, and its window goes. The AI Pad stays for the single-request verbs. Ask Quill (Alt+Q) stays, unchanged, as QUILL's advanced companion; decide again once the agent window has passed acceptance (decision 17).
- **One key: Ctrl+6, "Ask"**, in every app. Both editors already bind it (rule 2). Radio keeps Ctrl+Shift+8 as an alias (rule 5). Ctrl+6 in the menu-owned apps: to verify.
- **One connection:** Ask always uses the connection in use. Its first line says which: "Asking My ChatGPT plan about this station."

### 10C.3 What each app gives Ask

Ask takes a small block of structured facts from the app's own state, rebuilt for every turn, plus the person's question. New: one `ask_context()` provider per app, wx-free, returning named facts.

| App | Facts | From |
|---|---|---|
| QUILL, Lite | selection, else paragraph, else section; title; outline | `gateway_context.py:235`, `hosted_ai_commands.py:519-537` |
| Radio | station, now playing; favourites and recent songs only when the question needs them | `assistant_prompt.instructions_for` :57; `ask_radio_wiring.extra_for` :123 |
| Cast | the episode, show notes, chapters, position | `cast_ai_host.py:11-17`; `quill/core/podcasts/models.py`; `chapters.py` |
| Studio | the plan, devices, capture target, last check result | `PreflightFacts` (`demo_recording.py:209`), `gather_facts` (:150), `classify` (:222) |
| Transcribe | the transcript open, speakers | `quill/apps/transcribe_review.py`; `quill/core/ai/diarization.py` |
| Converter | the queued files, as probe text | `quill/core/audio/media_probe.py` |
| Player | book, chapter title, position | `quill/apps/player.py`; `quill/ui/media/recap_actions.py:100-113` |
| Weather | the location's name, current conditions, forecast, alerts | `quill/core/weather/nws.py`, `open_meteo.py`, `astronomy.py` |
| Inkwell | the abbreviations, by name and expansion | `quill/core/abbreviations_store.py` |
| Beacon | the note or search results open | `quill/apps/beacon/db.py` |
| Social | blocked (R8) | - |

**Never leaves the machine without a yes:** pictures and screenshots; audio, ever; a whole document or transcript beyond the scope above; Radio listening history (today's rule, `assistant_prompt.py:86-95`); file paths and folder names; account names and emails; exact coordinates (Weather sends the place name only; to verify in `geocoding.py`).

### 10C.4 Follow-ups

- History is local only, in the `Conversation` (`hosted_chat.py`), resent each turn; never `previous_response_id` or `conversation`, which the plan forbids.
- When history is trimmed to fit, the window says so once, as today ("this conversation is starting to forget its beginning").
- The facts block is fresh every turn, and marked when it changed: "Now playing changed since your last question."
- Saved through `record_exchange` to `ai-sessions` in every app, Radio included (new for Radio). Delete is one key in Saved Conversations.

### 10C.5 Hearing and moving through answers

- A reply is announced through the announcement service (speech, braille and earcons, `main_frame.py:4692-4730`), using `speakable_line` (`quill/core/spoken_answer.py:47`) so Markdown is not read as symbols. QUILL Lite's voice mirrors to braille (`lite_window.py:500-517`).
- The transcript is a read-only multiline field one Shift+Tab away. Alt+1 to Alt+0 read recent messages; Messages lists them; Export writes them out (`hosted_ai_chat.py:37-43`). All of this exists and becomes every app's.
- **Text only (Jeff, 2026-10-31):** every answer is sentences and lists. The family instruction tells every connection never to draw charts, graphs or diagrams, and anything chart-like a model sends anyway is shown as the text it is, never rendered (decision 13).
- **Long answers (new):** the first sentence is spoken and the rest waits in the transcript; a Read in QUILL button opens the answer as a document, where headings navigation works.

## 10D. The prompt library

### 10D.1 The basic prompts do not change

Every built-in prompt stays, with the same name, wording and place. Listed so nobody "improves" one by accident:

- **Hosted AI templates** (`quill/core/ai/own_key.py:107-240`, matching the gateway word for word): summarize, rewrite, proofread, explain, ask, document_qna, chat, shorten, simplify, formal, friendly, make_list, action_items, headings, continue, email_reply, translate, tidy_dictation, revise_dictation. Pad rows from `writing_tools.ACTIONS` (`quill/core/ai/writing_tools.py:41`); extra rows from the free service's catalogue only (`hosted_ai_pad_catalogue.py:42`).
- **QUILL Prompt Library** (`quill/core/prompt_library.py:57-250`, 18 prompts): Check Grammar, Improve Clarity, Make Concise, Fix Grammar, Active Voice, Formal Tone, Conversational Tone, Continue from Here, Summarize, Convert to Bullet Points, Define This Term, Find Counterarguments, Paraphrase, Generate FAQs, Step-by-Step Instructions, Draft a Speech, Summary Email, Social Media Post. Dialog `quill/ui/prompt_library_dialog.py:40`; `.pqp` packs; Quillin prompts merged at `prompt_library.py:364`.
- **Vision styles** (`quill/core/ai/vision_prompts.py:127`, 12): narrative, detailed, concise, artistic, technical, colorful, simple, accessibility, comparison, mood, functional, aialttext.
- **Studio screenshot prompts** (`quill/core/studio_capture_ai.py:25`, 7): screen-overview, screen-controls, screen-text, screen-quality, screen-privacy, screen-alt, screen-chart.
- **Radio quick questions** (`quill/core/radio/assistant_prompt.py:108`): eight, from "What is this song?" to "What have I been hearing on this station lately?", plus "Suggest something new" (about :162).
- **Cast** (`quill/core/podcasts/ai_listening.py`): about the show :82, for me :100, summary :118, listening run :161, playlist rules :221, chapter titles :319; organise (`ai_organise.py:137`).
- **Transcript actions** (`quill/core/ai/transcript_actions.py:114`, 10): meeting-minutes, action-items, executive-summary, interview-notes, study-notes, qa-extraction, clean-draft, follow-up-email, key-quotes, decisions-log.
- **Agent specs** (`quill/core/ai/agents/*.md`, 16): accessibility-editor, citation-link-fixer, code-doctor, data-cleaner, github-maintainer, markdown-publisher, math-tutor, meeting-notes-to-actions, plain-language-rewriter, prd-architect, quill-concierge, release-notes-builder, researcher, reviewer, summarizer, writing-companion. Skills are `.sqp` packs (`quill/core/skill_store.py`, `quill/ui/skill_library_dialog.py:38`).
- **User prompts** live in four stores today, scoped by feature, none by app: `prompts.json` (`main_frame.py:10687`; hosted AI `hosted_ai_answers.py:204`), `assistant-prompts.json` (`quill/core/assistant_prompts.py:54`), vision custom prompts in settings, and user skills and agents in app data.

### 10D.2 Where we add greatness (all new)

- **Per-app prompts** in the Ask window's quick list, beside Radio's existing eight: Cast "What did I miss in this episode?"; Studio "Is my setup ready?"; Weather "Do I need a coat at 5?"; Converter "Will this play in my car?"; Player "Remind me who this character is"; Beacon "What did I save about this?"; Inkwell "What do I type most?". Listed per app in 10E.
- **Prompts that know the connection.** A prompt declares what it needs (`needs: pictures`, `needs: tools`), and the gating rule (10A.8) labels it. "Describe the chart in this picture" shows "(needs a connection that sees)" on the free AI.
- **Shared family prompts:** a small set every app's Ask offers: "Explain this simply", "What can I do here?" (answered from the app's own F1 catalogue, `quill/core/control_help.py`, not from the model's guesses), "Summarise what is in front of me".
- **User prompts that work in every app:** one store for the family, `<app data>/prompts.json`, read by every app's Ask and pad, with `{selection}`, `{document}` and new `{context}` fields filled by each app's `ask_context()`. The four existing stores migrate into it once (`quill/core/prompt_migration.py:45` is the precedent), and nothing is deleted until the migration is checked (decision 18).

## 10E. AI across the QuillVille apps

Built on the inventory in section 3 and the per-app reports read on 2026-10-31. **Single-request features come first**, on the shared connection layer (10A), because they work on every connection, including the free AI. **Agent features come later**, on Copilot or Codex, and appear only where the connection in use has agent tools (10A.8).

Ranked by value to blind and low-vision users: what a person can do alone that today needs sighted help or a long workaround.

| Rank | App | First single-request feature | Later agent task |
|---|---|---|---|
| 1 | Studio | "Is my setup ready?" from pre-flight facts | full pre-flight check (6.1) |
| 2 | QUILL, Lite | Ask on the document; alt-text proposals | multi-step document tasks (6.2) |
| 3 | Cast | Ask about this episode | find and follow shows (6.5) |
| 4 | Radio | Ask, folded from Ask QUILL Radio | find, then record (6.5) |
| 5 | Transcribe | summary and action items, local text only | speakers and sections (6.6) |
| 6 | Weather | "Should I go out?" in words | none needed |
| 7 | Converter | "Will this play on my device?" from probe text | batch to audiobook (6.7) |
| 8 | Player | chapter recap on any connection | find the part where (6.11) |
| 9 | Beacon | describe and summarise a saved item | organise what I saved (6.10) |
| 10 | Inkwell | suggest abbreviations from a document | none needed |
| 11 | Social | blocked (R8) | blocked |

In every app below, "Capabilities required" uses the five connection names: Free, ChatGPT, Copilot, Codex, Own key.

### 10E.1 QUILL

**Today.** Basic AI rows from the shared module (`quill/ui/main_frame_ai_menu.py:34-75`, appended at `main_frame_hosted_ai.py:180-354`): Free AI Assistant Ctrl+Alt+G, Ask About This Document Ctrl+Alt+Z, Ask AI a Question Ctrl+6, Prompt Library Ctrl+7, Web Searches Left Ctrl+9, Usage Ctrl+Alt+Shift+F2, Connect or Sign Out Ctrl+Alt+Shift+F4, Privacy Agreement Ctrl+Alt+Shift+K, Use My Own AI Key Alt+F2, Use My ChatGPT Subscription Alt+F5, Ask About an Image Ctrl+F5, Tidy Dictated Text Ctrl+F3 (`keymap.py:247-271`), and the Dictionary rows (Look Up Alt+F10, Word Explorer Ctrl+F10). Connections: free, ChatGPT or own key. Advanced rows appear only with "Show advanced AI features" (`main_frame_ai_menu.py:274-308`): Ask Quill Alt+Q, Run Agent (`agent_editor_host.py:73-95`, SDK pack or Native, `:428-462`), Proofread, Transform, Translate, AI Read Aloud, Transcript Actions, AI Library, AI Hub; these use the AI Hub's provider (`ai_hub_dialog.py:1-30`) and mostly have no chord (`keymap.py:591-596`).

**Where we are going.**
- Choose Your AI, Which AI and the status cell (10A).
- Ask on Ctrl+6 grounded in the document (10C).
- Single requests: everything on the pad, unchanged, now gated by capability; alt-text proposals (6.4) as the one picture exception.
- Agent tasks (Copilot, Codex): "fix the heading levels, then build a table of contents, then list broken links", calling `read_outline`, `read_section`, `apply_patch`, `audit_accessibility` (`quill/core/ai/agent_tools.py`), each edit through diff review; "turn these notes into actions grouped by owner" with `meeting-notes-to-actions.md`. Approvals: every edit previews; `run_command` limited to `SAFE_TOOL_IDS`. On simpler connections the same verbs stay single requests on the selection.
- Pictures: only the document's own images (10B).
- The Advanced provider routes and Choose Your AI are two ways to pick an AI. They converge: the AI Hub's provider list becomes "My own key" with more providers, a later change (decision 20).

**Prompts.** All of 10D.1 stays. Added: capability-aware labels; the family prompts; the one user store.

**Capabilities required.** Pad verbs: text on any connection. Ask About an Image: pictures (ChatGPT, Copilot, Codex, Gemini key). Agent tasks: tools (Copilot, Codex). Web search: the free AI's allowance or QUILL's consented tool.

**Usage.** The one Usage view; Web Searches Left (Ctrl+9) stays for the free AI.

**Not here, and why.** No screen, frame or screenshot features: the editor is for writing (10B reading, awaiting confirmation). No image generation in the editor.

### 10E.2 QUILL Lite

**Today.** The same twelve rows from `HostedAiMixin` (`lite_window.py:88`, `:107`; `quill/core/lite/commands.py:955-982`), with two different chords: Usage Ctrl+Alt+Shift+F9 and Connect or Sign Out Ctrl+Alt+Shift+F10, because those are QuillVille launchers in QUILL (`parity.py:122-133`). Ask AI a Question Ctrl+6, Prompt Library Ctrl+7 and Web Searches Ctrl+9 come from `commands_ai.py:26-32`. Alt+F5 and Ctrl+F5 were chosen as free in both editors (`commands.py:972-979`); Ctrl+F3 for Tidy Dictated Text because it "was free in both editors and is nothing in Word QUILL has" (`:980-982`). No Ask Quill, no Advanced menu.

**Where we are going.** Exactly QUILL's basic AI, in the same change, from the same modules (rule 10): Choose Your AI on Ctrl+4, Which AI on Ctrl+8, Ask on Ctrl+6, gating, the Usage view. Agent tasks reach QUILL Lite only through the shared module, when they reach QUILL.

**Prompts.** As QUILL's basic set; no Advanced prompts.

**Capabilities required.** As QUILL.

**Usage.** The same view, on Ctrl+Alt+Shift+F9.

**Not here, and why.** Ask Quill and the Advanced provider routes, until QUILL settles them: QUILL Lite may never be ahead.

### 10E.3 Radio

**Today.** Ask QUILL Radio, Ctrl+Shift+8, and Use My ChatGPT Subscription, Alt+F5 (`app_keymaps.py:296-297`), at the top of the Community menu (`ask_radio_wiring.py:40-73`). ChatGPT plan only, no free route, no own key (`ask_radio_window.py:1-10`, `:228-231`). Context: station and now playing on every message (`assistant_prompt.py:46-75`); favourites, songs and history only for the quick questions that need them (`:86-95`). History in memory only.

**Where we are going.**
- Ask on Ctrl+6 (Ctrl+Shift+8 kept as alias), on any connection; history saved like everyone else's.
- Single requests: "tell me about this station", "what is this programme about".
- Agent tasks: "find a jazz station in Chicago and record it tonight from 8 to 10", calling `federated_search`, `directory_search`, `recording_schedule.next_occurrence`, then `radio.schedule_recording`, which asks first (`SCHEDULE`, section 5). On simpler connections the model only suggests; the person presses Record.
- Pictures: describe the video stream from `take_snapshot` (`video_commands.py:432`); station logos when artwork exists (new).

**Prompts.** The eight quick questions stay. Added: "What is on next?", "Record this whenever it is on".

**Capabilities required.** Ask and single requests: text, any connection. Video describe: pictures. Find-then-record: tools (Copilot, Codex).

**Usage.** The one view; Radio gets its own ChatGPT agent name ("QUILL Radio") as today.

**Not here, and why.** Song identification stays the existing service, not a model guess. No AI during a recording's run: the recorder runs it.

### 10E.4 Cast

**Today.** `CastAiMixin(HostedAiMixin)` (`cast_ai_host.py:105`): Free AI Assistant, Ask About These Show Notes, Image, Usage, Sign In, Privacy, Own Key, ChatGPT (`:37-47`), on family chords except Image Ctrl+Alt+F5 and Privacy Alt+Shift+F2 (`app_keymaps.py:361-369`). Help > AI Features (`cast_ai_features.py:28-37`): organise, about the show, for me, summary, listening run, playlist, chapters, all without chords, all through `service.ask` (free, plan or own key). Context: the show-notes pane.

**Where we are going.**
- Ask on Ctrl+6 about the episode in front of the person.
- Single requests: the AI Features, unchanged, gated.
- Agent tasks: "find three shows like this one, follow the best and put it in my Science folder", calling Cast's `directory_search`, `itunes_search`, `episode_filters`, then follow and `podcasts.move_to_folder`, each asking.
- Pictures: artwork and show-note images, downloaded only when asked (new).

**Prompts.** The six `ai_listening` prompts and organise stay. Added: "What did I miss in this episode?", "Is this episode worth my time?".

**Capabilities required.** Text for all of today's; pictures for artwork; tools for find-and-follow.

**Usage.** The one view, under "QUILL Cast".

**Not here, and why.** No audio sent: summaries use the cached transcript (`ai_listening.py:118`) or the show notes.

### 10E.5 Studio

**Today.** Ask AI Questions About a Video, Ctrl+Alt+Shift+K (`app_keymaps.py:61`; `studio_picture_video.py:66`), from a contact sheet plus caption excerpt; Make a Picture, Ctrl+Alt+Shift+J (`studio_picture_maker.py:19`), own key only. The Screenshot Inspector's prompts (`studio_capture_ai.py:25`, `:140`). Its own vision route chooser (`studio_vision_route.py:37`, `:65`): ChatGPT plan or a keyed provider. No ChatGPT sign-in of its own (section 3.1).

**Where we are going.**
- Choose Your AI replaces `studio_vision_route.py`, with a "QUILL Studio" sign-in.
- Ask on Ctrl+6 about the setup or the recording, from `PreflightFacts` and `gather_facts`.
- Single requests: "is my setup ready?", a scene list, framing advice, title cards checked (10B).
- Agent task: the full pre-flight check (6.1); the accessible narrative (6.8).

**Prompts.** The seven screenshot prompts and twelve vision styles stay. Added: "Is my setup ready?", "Does this recording look right?".

**Capabilities required.** Setup questions: text. Frames: pictures. Pre-flight agent: tools. Make a Picture: own key.

**Usage.** The one view; frames counted per request against the cap.

**Not here, and why.** No video file is sent; no audio is sent; no capture without a key press.

### 10E.6 Transcribe

**Today.** No AI menu. Review Dictation, Ctrl+Alt+Shift+F11, can polish text with AI when opted in (`transcribe_review.py:20-27`, `:160`), through `AiService(_FamilyAi)` (`:50-121`) borrowing QUILL's ChatGPT sign-in or own key (risk R1). The OpenAI option in `transcribe_commands.py:95-115` is speech to text, not a model.

**Where we are going.** Its own "QUILL Transcribe" sign-in (R1 fixed). Ask about the transcript. Single requests: the ten transcript actions (`transcript_actions.py:114`). Agent task: speakers, sections and summary (6.6). Pictures: slides beside a talk, from scene-change frames (new).

**Prompts.** The ten transcript actions stay. Added: "Who said what?", "What was decided?".

**Capabilities required.** Text for all; pictures for slides; tools for the sectioning agent.

**Usage.** The one view.

**Not here, and why.** Audio never goes to a plan; speech to text stays local.

### 10E.7 Converter

**Today.** No AI.

**Where we are going.** A "QUILL Converter" sign-in. Ask over probe text (`media_probe`). Single requests: "will this play on my device?", "what are these settings?". Agent task: "make these 40 MP3s one M4B with a chapter each" (6.7), calling `converter.probe`, `list_formats`, `queue_job` (asks). Pictures: embedded cover art described (new).

**Prompts.** None today. Added: "Will this play on my device?", "Make this smaller without losing much".

**Capabilities required.** Text; pictures for cover art; tools for batch jobs.

**Usage.** The one view.

**Not here, and why.** The model never hears the audio; it reasons over probe text.

### 10E.8 Player

**Today.** Summarize This Chapter (AI), Ctrl+Alt+C, and AI Recap of Where I Am, Ctrl+Alt+R (`player_menus.py:113-114`), no command ids, own key only (`recap_actions.py:135-151`), from the chapter title plus a local transcript of at most 5 minutes (`:100-113`, `:191`). Output announced, then a message box (`:129-132`).

**Where we are going.** Both commands get ids and move to the connection in use, so they work on the free AI and the plans. Ask about the book and the place in it. Agent task: find the part where (6.11), once a transcript source exists.

**Prompts.** The two recaps stay. Added: "Remind me who this character is".

**Capabilities required.** Text only.

**Usage.** The one view.

**Not here, and why.** No video features: Player is audio only. Audio itself never leaves; the transcript is made locally.

### 10E.9 Weather

**Today.** No AI.

**Where we are going.** A sign-in. Ask about the forecast, from `nws.py`, `open_meteo.py` and `astronomy.py`. Single request: "should I go out?" in plain words.

**Prompts.** Added: "Do I need a coat at 5?", "When is the rain coming?".

**Capabilities required.** Text only.

**Usage.** The one view.

**Not here, and why.** Alerts stay model-free (`headless_check.py`): an alert is never paraphrased by a model. No radar images until a source exists.

### 10E.10 Inkwell

**Today.** No AI.

**Where we are going.** Suggest abbreviations from a document the person picks (6.12); each added only on a yes, through `abbreviations_store.py`.

**Prompts.** Added: "What do I type most?".

**Capabilities required.** Text only.

**Usage.** The one view.

**Not here, and why.** System-wide expansion is never driven by a model, and no typed text is ever sent.

### 10E.11 Beacon

**Today.** Assist menu (`quill/apps/beacon/app.py:628-647`): Suggest Tags Ctrl+Shift+T, Suggest Relationships Ctrl+Shift+K, Summarize Note Ctrl+Shift+M, all local heuristics (`assist.py:1-13`).

**Where we are going.** The local three stay and stay first. Ask about the note or the search results. Single requests: describe a saved screenshot (OCR first). Agent task: organise what I saved (6.10), with `beacon.tag` and `beacon.move` asking.

**Prompts.** Added: "What did I save about this?".

**Capabilities required.** Text; pictures for screenshots; tools for organising.

**Usage.** The one view.

**Not here, and why.** Nothing runs on a timer.

### 10E.12 Social

**Today.** Summarize This Feed (AI), Ctrl+Alt+R, and Accessibility Check, F7, both deterministic; the gateway has only a `MockProvider` (`standalone/social/quill_social/services/ai/gateway.py:13-18`).

**Where we are going.** Blocked until it moves under `quill/` (R8). Then: alt text proposed before Post, read back in full; images in the feed described on request.

**Prompts.** None until unblocked.

**Capabilities required.** Pictures for alt text.

**Usage.** The one view.

**Not here, and why.** Nothing is ever posted by a model: posting is an irreversible send and always asks.

## 10F. Setting up the GitHub app: Jeff's steps

A checklist to follow in a browser. Each step was checked against docs.github.com on 2026-10-31 unless it says "to verify".

1. **Choose an OAuth App, not a GitHub App.** The Copilot SDK accepts `gho_` (OAuth App), `ghu_` (GitHub App) and fine-grained `github_pat_` tokens, and refuses classic `ghp_` (section 2B.5, docs.github.com Copilot SDK authentication). Both kinds of app would work. The OAuth App is the simpler one: QUILL's code already runs the OAuth device flow with scope `read:user` (`copilot_auth.py:44-48`), a user approves it once with no installation step, and the GitHub App's required Copilot permission, if any, is not documented (to verify).
2. **Create it under the Community-Access organization,** not your personal account. Go to the organization's page, then Settings, then Developer settings, then OAuth Apps, then New OAuth App. The org owns it, so it survives a change of maintainer, and users see the organization's name on the approval page. Docs: docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app (it says any organization where you are an administrator can own one).
3. **Fill in the form, field by field:**
   1. Application name: `QUILL`. This is what users see on GitHub's approval page and in their settings. For the other apps, use the app's name exactly: `QUILL Lite`, `QUILL Studio`, and so on (step 8).
   2. Homepage URL: the QUILL site's home page.
   3. Application description: "Lets QUILL use your GitHub Copilot plan for AI help. QUILL never sees your password."
   4. Authorization callback URL: device flow does not use it, but the field is required. Enter the homepage URL again.
   5. Enable Device Flow: check this box. Without it, sign-in fails with `device_flow_disabled`.
   6. Expire user access tokens: uncheck it for now. GitHub's own advice is to leave it off until the app can refresh short-lived tokens, and QUILL cannot yet (gate G2). Tokens then do not expire unless revoked.
   7. Register application.
4. **Do not create a client secret.** Device flow needs none ("The client_secret is not needed for the device flow"). QUILL must never contain one: anything shipped in an app can be read out of it.
5. **Copy the Client ID** from the app's page and send it to us in any ordinary message. A client id is public: it names the app, it grants nothing, and it appears in every sign-in request anyway.
6. **Wiring it in (our work, not yours). Done.** `copilot_auth.py` now carries a built-in `CLIENT_IDS` table, one per app's agent name, with the environment variable kept only as a developer override. Users never set anything.
7. **Testing it.** In a build with the id: open Choose Your AI, select My GitHub Copilot, press Sign In. You should hear the code, spaced out, and find it on the clipboard. Press Open the Page, sign in to GitHub if asked, paste the code, approve. Back in QUILL you should hear "Signed in to My GitHub Copilot. It is now in use", and Ctrl+8 should say Copilot.
8. **One registration per app.** Decided (decision 16), for two reasons. Each app signs in separately (Jeff's decision), and each should appear by its own name on the approval page and in a user's GitHub settings. And GitHub allows only ten tokens per user, app and scope combination; an eleventh revokes an older one (docs.github.com, authorizing OAuth apps). Eleven family apps signing in on one registration would sign each other out. Start with QUILL and QUILL Lite; add the others as each gets AI.
9. **Revoking and rotating.** A user revokes QUILL at github.com/settings/connections/applications/ followed by the client id; the next request then fails, and QUILL says "Your GitHub Copilot sign-in has ended" (10A.5). You can revoke every token at once from the app's page in the organization's settings (the exact button: to verify); every user then sees the same sentence and signs in again. Deleting the app breaks sign-in until a build with a new client id ships, so do it only if the app is compromised.

## 11. Phased delivery

Revised 2026-10-31 to Jeff's order: Copilot engine fixes, then the Choose Your AI layer in QUILL and QUILL Lite, then the Copilot route, then per-app single-request features, then the agent engines. QUILL and QUILL Lite document tasks are the first agent feature (Phase 4a); Studio's pre-flight check is the second, first in Phase 4c (decision 3).

### Which engine first: Copilot

- **Stable ground.** The Copilot SDK is GA with a stable API. Codex plan sharing is a preview, and `dynamicTools` is experimental.
- **Less new code.** Copilot has a Python SDK, so tool handlers are Python functions in our process. Codex needs our own JSON-RPC client and process manager.
- **Half of it exists.** The Copilot pack, device-flow sign-in, onboarding dialog, Engines tab and wizard path are all in the tree (section 3.7).
- **It costs users nothing.** Copilot Free is included.
- **What it does not settle:** images through tools (G6), and the OAuth App (R10, section 10F).

### Phase 0: Copilot engine fixes (no user-visible feature)

- `send_and_wait` in place of `send` (the request-id bug), an explicit `github_token`, the token out of `os.environ` and added to `scrubbed_child_env()`, a `gho_` redaction pattern, `available_tools` never empty.
- The Copilot token in its own store entry, apart from the GitHub repository features.
- Tested with an injected fake SDK client, the pattern `SdkHarness(invoke=...)` uses now.

### Phase 1: Choose Your AI in QUILL and QUILL Lite (section 10A)

- `ai_connection` with the migration; `AiService.route` reads it; no fall-through.
- `connection_caps.py` and GATE-CAPS; capability-gated labels and the one-key switch.
- The window, Which AI (Ctrl+8), Choose Your AI (Ctrl+4), the status cell, the one Usage view, the local ChatGPT request count.
- Ask converges on the AI Conversation window on Ctrl+6 in both editors (10C), with the editor's context provider.
- Prompts: the capability labels on existing prompts; nothing renamed or reworded (10D.1).
- Both editors in the same PR. Rows are free, ChatGPT and own key; Copilot and Codex rows show "Not available yet" until their phases.

### Phase 2: the Copilot route (section 10A.12)

- Jeff's OAuth App and client id (10F); per-app sign-in.
- `copilot.exe` and the SDK in `standalone/runtime/quillville-runtime.spec`, inventories, notices, signing skip, SHA-256 pin.
- Chat, conversations and pictures as attachments; the model list from `models.list`; usage from `account.getQuota`.
- Gates G1, G2, G4, G5 and G6 for Copilot.

### Phase 3: per-app single-request features, Ask and prompts (sections 10B to 10E)

- Each app gets its sign-in, the window, Which AI, Ask with its `ask_context()` provider, and its first single-request feature from the 10E table, in that table's order.
- Ask QUILL Radio folds into Ask. Player's two recaps get command ids and move to the connection in use. Studio's vision chooser folds into Choose Your AI. Transcribe gets its own sign-in (R1).
- Pictures in the media apps (10B), with `picture_prep.py`: local frames, OCR first, downscale, cap, timestamps, cache.
- The family user-prompt store, with its migration; per-app quick prompts; the shared family prompts.

### Phase 4: the agent engines

- **4a. Shared agent layer plus Copilot tools.** `ToolSession`, `FamilyToolRegistry`, `Approver`, the agent window, then QUILL and QUILL Lite multi-step document tasks (6.2) as the first agent feature, both editors in the same PR (decision 3).
- **4b. The Codex engine.** `codex_app_server.py`, tested with a fake child process; the Codex row lights up.
- **4c. Agent tasks by app,** Studio's pre-flight check (6.1) first, then in the 10E order: QUILL and QUILL Lite alt-text (6.4), Radio and Cast (6.5), Converter (6.7), Transcribe (6.6), then Studio narrative, Beacon, Player and Inkwell. Social after R8.

### Gates for the engines (each engine passes all of them)

- **G1:** with a real account (Copilot Free and Pro; ChatGPT Plus), the pinned exe completes one turn through the token we supply, and the usage-limit path is checked by hand.
- **G2:** a token refresh keeps the conversation. For Codex: restart and `thread/resume`. For Copilot: with "Expire user access tokens" off, record that the token does not expire; with it on, refresh without a client secret.
- **G3:** the recorded tools list contains only QUILL's tools. No shell, file edit, `apply_patch`, image generation, `view_image`, plugins, apps or MCP.
- **G4:** Safe Mode refuses to start either engine. Stop ends a turn within 1 second. Closing the app kills the child within 2 seconds.
- **G5:** a 10-minute network capture shows only the vendor's API and auth hosts.
- **G6 (Copilot):** can a custom tool return an image the model sees? If not, the attachment fallback in section 6.0 is the design.

### Acceptance, every phase

- With NVDA and JAWS, keyboard only: open Choose Your AI, hear the rows and states, sign in, hear the outcome once, and hear Ctrl+8 say the truth.
- A command the connection cannot do never sends, and offers the switch in one key.
- A usage limit speaks once and offers Manage Usage; nothing retries or switches.
- F1 answers on every control.
- `pytest -q`, `python -m quill.tools.platform_report`, the egress pytest file, and new checks in `docs/qa/screen-reader-checks-2026-10.md`.

### Phase 5 (only if Jeff wants it): background tasks

- Express, per-app consent first.

## 12. Decisions (2026-10-31)

Jeff accepted all 25 recommendations on 2026-10-31. They join what was already settled: the five connections, the Copilot CLI in the shared runtime, Copilot before Codex, a separate sign-in in every app, capability gating, and an unchanged unified presentation, usage tracking, Ask in every app and basic prompt library. The body of this plan already reflects each one; the numbers below are what "decision N" means elsewhere in the document.

1. **Codex size.** Codex app-server ships once, in the shared runtime, starting with the release that carries Phase 4b; nothing before then and no opt-in download. About 92 MB compressed and 284 MB installed. Measure at G3 whether the sandbox helpers (about 80 MB) are needed with the shell off, and leave them out if not (section 9).
2. **Transcribe sign-in.** Transcribe gets its own "QUILL Transcribe" ChatGPT sign-in in Phase 3, before it gets any new AI feature, ending the borrowed sign-in at `quill/apps/transcribe_review.py:53` (R1). Say so once, in one sentence, the first time Review Dictation needs the plan.
3. **First agent feature.** QUILL and QUILL Lite document tasks are the first agent feature (Phase 4a), on `TOOL_DESCRIPTORS`, `SafeEditorToolGateway`, `PermissionBroker` and diff review. Studio's pre-flight check is the second, first in Phase 4c (sections 1, 6.1, 11).
4. **Thread storage.** Thread files are kept for the length of one task, in the app's own `CODEX_HOME`, and deleted when the task ends, on Stop, and again at the next start. Copilot session state under its per-app `working_directory` follows the same rule (section 8).
5. **Social.** Left out of this plan. It moves under `quill/` as its own program, with its own PRs, before any AI goes into it (R8).
6. **Accounts for live checks.** Jeff's ChatGPT Plus account, one Copilot Free account and one paid Copilot account. No Pro account. Jeff creates or lends them; Claude never signs in for Jeff. Phase 0 needs none (fake SDK client).
7. **Engine order.** Copilot first.
8. **Both engines.** Both in the shared runtime: Copilot from Phase 2, Codex from Phase 4b, about 205 MB compressed together. No opt-in download for either. Measure the Copilot CLI's unpacked size in Phase 2 and record it in section 9. Each engine gets its own child-process entry in the network egress audit.
9. **GitHub OAuth App.** Registered under the Community-Access organization, device flow on, no client secret, expiring tokens off, following section 10F. Unblocks Phase 2 (R10).
10. **GitHub sign-in.** One per app, matching ChatGPT.
11. **Token split.** Each app's Copilot token gets its own store entry, keyed by that app's agent name, apart from the GitHub repository features' token in `quill/core/github/token_store.py`. One-time migration: an existing token stays with the repository features, and Copilot asks for its own sign-in once. Phase 0 work (section 10A.6).
12. **Dead `gh copilot` commands.** `github.copilot_suggest` and `github.copilot_explain` are removed now, in their own small change, before Phase 2: the handlers in `quill/ui/main_frame_gh_bridge.py`, the functions in `quill/core/github/gh_bridge.py`, the keymap rows, `quill/core/feature_command_map.py` and the sign-off lists.
13. **Everything is text.** No graphs, charts, diagrams or pictures in any app's AI output or usage view. Every answer is sentences and lists, spoken through the announcement service and brailled on the same path. The family instruction tells every connection never to draw charts, graphs or diagrams, in text art or otherwise, and anything chart-like a model sends anyway is shown as the text it is, never rendered. Agent tasks end with a text summary and each edit is reviewed as text. Pictures going in follow 10B: the editors keep only Ask About an Image and alt-text proposals for a document's own images; other picture features live in the media apps. Studio's existing Make a Picture (own key) stays, because the picture is the thing the person asked to make; nothing new generates a picture or a chart.
14. **Chords.** Which AI on Ctrl+8 (pressed twice, opens Choose Your AI), Choose Your AI on Ctrl+4, and Ask on Ctrl+6, in every app; Radio keeps Ctrl+Shift+8 as an alias. Still to check: the menu-owned apps (Converter, Player, Inkwell, Transcribe, Beacon), and Cast's quick-actions list, which keeps Ctrl+4 inside the list if it has more than three entries, with the divergence written as a `keymap.py` comment and a parity row (rule 11).
15. **Signing out of the AI in use.** No AI is left in use until the person chooses. The next AI command opens Choose Your AI and says once "No AI is in use. Choose one." Never a silent fall-back to the free AI or a key (10A.5).
16. **GitHub registrations.** One OAuth App per app, all under Community Access, starting with QUILL and QUILL Lite and adding each app when it gets its AI, because GitHub allows ten tokens per user, app and scope (10F step 8).
17. **Ask Quill.** Unchanged, as QUILL's advanced companion on Alt+Q, through Phases 1 to 3. Decide again once the agent window (Phase 4a) has passed acceptance (10C.2).
18. **User prompts.** One family store at `<app data>/prompts.json`, with a one-time migration in Phase 3. Identical prompts merge; different text under the same name keeps both, the second named by its old store. Old files are kept, read-only, for one release, and deleted only after the migration is checked (10D.2).
19. **AI status cell.** A thirteenth status-bar cell, "AI", short ("AI: Copilot, Auto"), placed last, with its F1 sentence; Enter opens Choose Your AI. QUILL gets the same cell in the same change (10A.10).
20. **AI Hub providers.** After Phase 3, as its own change in both editors at once, My own key gains the AI Hub's keyed providers (Anthropic Claude, OpenRouter, Ollama Cloud, custom OpenAI-compatible), and Ollama on this computer becomes a My own key provider that needs no key, with the About line "Runs on this computer. Nothing is sent." Each provider gets a capability record with a source (GATE-CAPS) and its egress entry checked. The AI Hub's chooser is removed last (10E.1).
21. **Codex in use.** Single requests go over `chatgpt_client.respond` with the same per-app sign-in and agent name; the Codex process starts only for multi-step tasks. Ctrl+8 says so in one sentence (10A.13).
22. **Weather.** Text only. No radar or map source.
23. **Free AI Connect.** No automatic Connect. The one Connect page visit per computer stays, opened by the first AI command straight after the privacy agreement, with the code already filled in (10A.4).
24. **ChatGPT usage.** Phase 1 builds a per-app local count of requests today and this week, plus the token counts OpenAI reports, kept on this computer, shown as text, always called a local count and never used to guess a limit. No network call (10A.11).
25. **"Tell me when this changes".** A foreground watch the person starts and stops, built after the Phase 3 picture pipeline, Studio first, then Radio. Hard rules: explicit Start and Stop commands with keys; a spoken start and stop; local pixel difference and local OCR first; the model asked at most once a minute and at most 30 times a watch, then the watch stops and says so; every ask counted in usage; refused in Safe Mode; nothing sent once the window closes. It reports one sentence, spoken and brailled, only when something changed. Each picture sent follows 10B.4 consent (10B.6).

## Sources (read 2026-10-31)

- developers.openai.com/siwc/token-sharing-open-source/codex-app-server
- developers.openai.com/siwc/token-sharing-open-source/preview-limitations
- developers.openai.com/siwc/token-sharing-open-source, plus `/sign-in`, `/profiles-and-sessions`, `/models-and-inference`, `/errors-and-recovery` and `/self-hosted-vms`
- developers.openai.com/siwc/ui-ux-guidelines
- developers.openai.com/siwc/quickstart.md
- developers.openai.com/blog/codex-as-a-platform (does not mention SIWC)
- learn.chatgpt.com/docs/app-server
- openai.com/policies/sign-in-with-chatgpt-terms/, dated 2026-09-29. The live page returned 403; read via the web.archive.org capture 20261021154407.
- github.com/openai/codex:
  - README;
  - release rust-v0.166.0;
  - `codex-rs/features/src/lib.rs`;
  - `codex-rs/protocol/src/dynamic_tools.rs`;
  - `protocol.rs` and `config_types.rs`;
  - `app-server-protocol/src/protocol/v2/thread.rs`;
  - `app-server/tests/suite/v2/dynamic_tools.rs`.
- help.openai.com/articles/20001542 returned 403 and was not read.

GitHub Copilot SDK (read 2026-10-31):

- github.com/github/copilot-sdk: README, `python/README.md`, root listing, issue #617
- pypi.org/pypi/github-copilot-sdk/1.0.28/json
- github.com/github/copilot-cli: README, `LICENSE.md`, release v1.0.105 (GitHub API), issue #5306
- github.blog/changelog: 2026-01-14 technical preview, 2026-04-02 public preview, 2026-06-02 GA, 2026-10-28 becoming Microsoft Copilot SDK, 2025-09-25 gh-copilot deprecation
- docs.github.com/en/copilot/how-tos/copilot-sdk/: authenticate-copilot-sdk, set-up-copilot-sdk/github-oauth, features/usage-and-billing, troubleshooting/sdk-and-cli-compatibility
- docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli
- docs.github.com/en/copilot/get-started/plans
- docs.github.com/en/copilot/reference/ai-models/supported-models
- docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/what-changed-with-billing
- Not read: the GitHub Copilot product-specific terms in full.

Added 2026-10-31 for sections 2C.1, 10A.11 and 10F:

- docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app
- docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps (device flow; ten-token limit)
- docs.github.com/en/copilot/how-tos/premium-requests/monitoring-your-copilot-usage-and-entitlements
- github.com/github/copilot-sdk: docs/features/usage-and-billing.md, docs/auth/byok.md
- docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-llm-models
- github.blog/changelog/2026-02-04-claude-and-codex-are-now-available-in-public-preview-on-github/
- code.visualstudio.com/docs/agents/run/agent-harnesses
- developers.openai.com/api/docs/guides/rate-limits; ai.google.dev/gemini-api/docs/rate-limits
- Not read: help.openai.com/en/articles/20001542 (refused), the live SIWC terms page (refused).
