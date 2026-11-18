# Microsoft Copilot SDK 2.0: what it means for QUILL, and the plan

**Owner:** Jeff Bishop / Community Access
**Written:** 2026-11-18, after Microsoft's Ignite 2026 announcement (17 November 2026).
**Status:** planning only. Nothing here is built. Open work is tracked in `complete.md`.

**Decision (Jeff, 2026-11-18): 2.0 replaces 1.x completely.** There is no side-by-side period, no fallback to 1.x and no second pack. The change removes `github-copilot-sdk` from the build, the bundled 1.x Copilot CLI, and every 1.x code path, in the same pull request that brings 2.0 in.

## What changed

Microsoft Copilot SDK 2.0 is the renamed GitHub Copilot SDK, the library QUILL's
**My GitHub Copilot** connection runs on. Microsoft describes it as programmatic
access to the same agent "harness" behind its Copilot products. The points that
matter to QUILL:

- **A new package name.** 2.0 is on PyPI (the Python package index) as
  `microsoft-copilot-sdk`, now at 2.0.1. The old `github-copilot-sdk` is at
  1.0.34 and QUILL pins 1.0.28 (`pyproject.toml`, extra `ai-copilot`). The
  source moved to `github.com/microsoft/copilot-sdk`.
- **The runtime is rewritten in Rust**, with bindings for TypeScript, Python,
  Go, .NET (Microsoft's application framework), Java and Rust.
- **Many sessions in one process.** In 1.x every session needed its own
  container or process. In 2.0 one runtime hosts many isolated sessions, each
  with its own state, credentials, tools, files and history.
- **Much faster and lighter.** Microsoft's figures: creating a session fell
  from 5.25 seconds to 55 milliseconds, and ten clients use about 126 MB of
  memory instead of 1.4 GB.
- **Sessions outlive the client.** A session can persist after the process
  that started it has gone.
- **The architecture is the integrator's choice**: where the model loop runs,
  and where file and shell actions run, from no sandbox at all to sandboxes
  and separate workers.

Not yet known, and to be read in the 2.0 source before building:

- whether the 1.x calls QUILL depends on survive (see below);
- what the runtime download fetches on first use (`python -m copilot
  download-runtime --in-process` pre-stages it, checked against the release's
  SHA-256 sums), and so what the installer must ship and the network egress
  audit must list.

Answered by the package itself: the default transport runs the runtime
in-process (a separate process is still available); a persisted session
keeps its state on this computer, in `~/.copilot/session-state/<id>/`; and
the licence is MIT.

## How QUILL uses the SDK today

- `quill/ai_packs/copilot.py`: the harness pack. Text only, or QUILL's own
  family tools offered as Copilot custom tools. The SDK's own file and shell
  tools are never offered, and every permission request outside QUILL's tools
  is refused, so QUILL owns every edit.
- `quill/core/ai/copilot_chat.py`: Ask and the chat. Each turn runs in a
  **fresh session** with QUILL's local history resent, so nothing about a
  conversation lives in Copilot.
- `copilot_sign_in.py`, `copilot_auth.py`, `copilot_quota.py`,
  `copilot_state.py`: sign-in with the token passed explicitly
  (`github_token=`, `use_logged_in_user=False`), never through the
  environment; quota and model lists.
- The facts the pack relies on were "checked against the SDK 1.0.28 source":
  `send_and_wait` with QUILL's own timeout and `session.abort()`,
  `system_message` in **append** mode (keeping the CLI's safety sections),
  `available_tools`, `on_permission_request`, an `env=` that passes the child
  no other credential, `models.list`, and the `session.error` event fields.

## What 2.0 could do for QUILL

1. **Faster answers.** QUILL starts a fresh session every turn. At 55
   milliseconds instead of five seconds, that design costs almost nothing, so
   the privacy choice behind it no longer costs speed.
2. **Less memory across the family.** QUILL, QUILL Lite and the QuillVille
   apps that use Ask can each start Copilot. One lighter runtime matters most
   on smaller machines (a BrailleNote Evolve, for instance).
3. **Possibly a smaller install**, if the Python binding no longer needs the
   bundled CLI. To be confirmed.
4. **Resumable conversations, if wanted.** Persistent sessions would let a
   long agent task survive closing the window. This goes against "nothing
   lives in Copilot", so it is a decision for Jeff, not a default.

## Risks

- **The 1.x line will fall behind.** It is at 1.0.34 and QUILL is on 1.0.28.
  Fixes from here on will land in 2.x, which is why QUILL moves outright.
- **A renamed package and a rewritten runtime** can break every fact the pack
  pins. The tests that pin them are the guard; each must be re-checked, not
  assumed.
- **Persistent sessions are new data.** If 2.0 keeps sessions by default, QUILL
  must turn that off or delete them, or a chat QUILL believes is private would
  be kept somewhere QUILL does not show. That needs a row in the network
  egress audit and the privacy notes.
- **Safe Mode and consent** must still stop every Copilot path.

## Features worth bringing into QUILL, most impact first

Read from the 2.0.1 package's own README (`microsoft-copilot-sdk`, MIT, Python
3.11 or later) on 2026-11-18. None is built or tried yet.

1. **Questions asked in QUILL's own dialogs (UI elicitation and user input
   requests).** The agent can ask the person to confirm, choose from a list,
   or type an answer, through handlers the app supplies. QUILL would answer
   them with its own accessible dialogs (a list for choices, a labelled text
   field, OK and Cancel with no access keys, F1 help), so an agent never
   stalls or guesses when it needs a decision. This is the biggest gain for a
   screen-reader user: today a Copilot turn can only end in text.
2. **Hearing what the agent is doing (session hooks).** Hooks fire before
   and after each tool call and when a sub-agent starts or stops. QUILL can
   say each step once, in plain words ("Reading notes.md", "Searching the
   repository", "Done: 3 files changed"), through the announcement service,
   so it is also brailled. Long agent runs stop being silent.
3. **No separate Copilot program (in-process transport).** The default
   transport loads the runtime as a library inside QUILL instead of starting
   a child process. QUILL could drop the bundled CLI in `tools\copilot`,
   start faster and use less memory. The trade-off is stated plainly in the
   README: no crash isolation and no sandbox. QUILL already offers the agent
   no file or shell tools of its own, which is what makes this acceptable,
   but a crash in the runtime would take QUILL down, so 2.0 should be able to switch to its own separate-process transport if
   testing shows the in-process one unstable (1.x is gone either way).
4. **Any AI through one engine (custom providers, BYOK).** A session can use
   an OpenAI-compatible service, Azure, Anthropic, Google or a local Ollama,
   with the person's own key. Choose Your AI could run every connection
   through the same agent engine, with QUILL's family tools, permission
   broker and diff review the same everywhere, instead of a separate client
   per provider. Local Ollama gives a private, offline agent.
5. **Answers QUILL can rely on (structured output).** `send_and_wait_typed`
   returns a checked Pydantic object instead of free text. Suggest Document
   Metadata, alt-text review, triage labels, commit messages and WordPress
   SEO fields would get validated fields, not text to parse and hope.
6. **QUILL's own skills (skill providers).** A session can be given skills
   from the app instead of files on disk: how QUILL's keys work, the house
   style for docs, how to write alt text, the WordPress and GitHub task
   recipes. The agent then knows the family's rules without a long prompt.
7. **Long work that does not forget (infinite sessions).** The runtime
   compacts a long conversation in the background so it does not hit the
   context limit. Useful for the coding agent and long documents. **But**
   by default it saves session state to `~/.copilot/session-state/<id>/` on
   this computer. QUILL must turn this off, or delete each session's folder
   when the turn ends, until Jeff decides otherwise (see Risks).
8. **Images as data (blob attachments).** A picture can be sent as data
   rather than a file path. Describe Image and Ask about a picture could use
   Copilot without writing a temporary file.
9. **Smaller ones.**
   - Auto routing tiers: a "faster" or "smarter" choice for one session
     without naming a model.
   - Network callbacks: QUILL answers proxy questions, so people behind a
     company proxy can sign in.
   - `get_events()`: a session's history for the diagnostic bundle.
   - Customize mode for the system message: replace one section (tone)
     while keeping the safety sections, more precise than append.
   - Memory (opt-in, across turns): leave off, as QUILL keeps its own
     history.
   - Telemetry: an optional extra; leave it out.

Suggested order: 3 and 2 with the replacement (they change how it runs and
what is heard), then 1, then 5, then 4 and 6 (they reshape Choose Your AI and
need Jeff's yes), and 7 only after the persistence decision.

## The plan

Each step is one pull request.

1. **Read and pin (no behaviour change).**
   - Read the 2.0 Python binding, and record answers to the "not yet known"
     list above in this file.
2. **Replace 1.x with 2.0, in place.**
   - Change the extra `ai-copilot` to `microsoft-copilot-sdk==2.0.x` and
     delete `github-copilot-sdk`. Rewrite `quill/ai_packs/copilot.py`,
     `copilot_tool_session.py` and `quill/core/ai/copilot_*.py` against 2.0,
     keeping the same contract: text only or QUILL's family tools, every
     other permission refused, the system prompt kept with the safety
     sections, the token passed explicitly, Safe Mode respected.
   - Remove the bundled 1.x CLI (`tools\copilot`) from the installers and
     the build scripts, and stage the 2.0 runtime instead
     (`python -m copilot download-runtime --in-process`, checked against its
     SHA-256 sums), so it is never downloaded on a listener's computer.
   - Choose the "no sandbox" architecture, with no SDK file or shell actions,
     because QUILL's Safe Editor Tool Gateway already does that job.
   - Turn off session persistence, or delete each session when its turn
     ends, and test that nothing is left behind.
3. **Prove it before merging.** Every test that pinned a 1.x fact is
   rewritten against 2.0 and passes. Time to first token, memory with three
   apps asking, and install size are measured and written down here, as the
   record of what the switch bought. There is no 1.x to fall back to, so the
   in-process transport's crash risk is handled by using 2.0's
   separate-process transport if testing shows the in-process one unstable.
4. **Finish in the same release.** Update `components.json`, the third-party
   notices (the new package, MIT), the network egress audit (the runtime
   download, if any remains), the Choose Your AI help, `docs/design/codex.md`
   and both changelogs. Nothing named 1.x remains in the tree.
5. **Decide (Jeff).** Whether to offer resumable agent sessions at all, and if
   so, only for the coding agent (`docs/design/code.md`) with a visible list
   of kept sessions and a way to delete each.

## Sources

- [Thurrott: Ignite 2026, Microsoft Copilot SDK 2.0 is now available](https://www.thurrott.com/a-i/microsoft-copilot-a-i/344006/ignite-2026-microsoft-copilot-sdk-2-0-is-now-available)
- Microsoft's announcement: commandline.microsoft.com/microsoft-copilot-sdk-2-0-github/
- Getting started: github.com/microsoft/copilot-sdk/blob/main/docs/getting-started.md (not yet read)
- PyPI: `microsoft-copilot-sdk` 2.0.1; `github-copilot-sdk` 1.0.34 (checked with pip on 2026-11-18)
