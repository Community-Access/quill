# GHManage + Quill Developer Experience Plan

> **Implementation status (2026-11-06):** QUILL and QUILL Lite share the GitHub
> Items viewer. Its PR review reader uses an expandable native outline: PR,
> changed files with review threads, general conversations, and checks. The
> selected node drives a readable detail field, and context menus expose
> relevant actions. Ctrl+R replies; Ctrl+Shift+R resolves or reopens a thread
> when GitHub permits. Exact patch-line targeting, Explore views, global saved
> searches, My Work, the account-scoped attention queue, Pages, labels,
> activity, workflow job logs, and issue-to-worktree handoff are now
> implemented in this worktree. Open GitHub Reference... routes repository,
> issue, pull-request, branch, and file links; direct pull requests open the
> review reader. QUILL Lite has the shared Open Link... entry, with an explicit
> browser fallback for file links until its editor can open remote files
> directly. Workflow job details include steps, the selected attempt, head SHA,
> bounded annotations, and bounded log output. Review adds next-unresolved and
> local next-unvisited navigation. Items restores the last repository, view,
> filters, and selected row per local account key. The user accepted the complete GX01–GX15
> expansion; its durable scope and acceptance live in
> [the GitHub Workbench Roadmap](./github-roadmap.md). Manual Windows
> assistive-technology acceptance is user-owned and separate from engineering
> completion and merge.

This document is the pre-implementation design plan for making GitHub a native, first-class part of the QUILL developer experience. It is intentionally ambitious: we want to make GitHub work feel as integrated as writing code, reviewing diffs, navigating branches, and shipping changes — not bolted on as a separate tool.

The north star is simple:

- GitHub should feel like an extension of the editor's mental model
- PRs, issues, diffs, threads, and commits should become readable in context
- Human decisions should stay human, while AI accelerates comprehension and execution
- Developer profile gating should be explicit, safe, and respectful of consent
- We should build something that is more than "GHManage in QUILL" — we should generalize the real patterns that make repository work feel magical and trustworthy

## 1. Why this matters

GitHub is no longer a sidecar. It is central to the developer workflow:

- reading code and reviewing change history
- understanding work in progress
- triaging issues and pull requests
- following threads and deciding what to do next
- preparing a patch or PR from a local working state
- explaining the state of a project to a teammate or AI assistant

The current QUILL experience already has the right instincts:

- read-only GitHub items browsing exists in `quill.ui.main_frame_github_items`
- the GitHub consent and safe-mode gates are already enforced
- developer profile gating is built around the `coding` capability
- the architecture already separates UX, permissions, and source-of-truth logic

That means we are not starting from zero. We are turning a useful surface into a cohesive GitHub operating system for developers.

## 2. Product vision

### The magical experience

We want a developer to be able to do the following without context switching or mental overhead:

- open a repo and immediately see the working state, outstanding PRs, and open issues
- click a PR or issue and get a context-rich summary in plain language
- review a diff beside the file currently open in the editor
- follow a review thread without losing the code context
- ask: "What changed since the last review, and what do I need to know before I ship?"
- ask AI to summarize, explain, or compare threads and commits
- prepare a patch or branch update from local work with a single, guided flow
- move from issue to branch to patch to PR without leaving the app

### The trustworthy experience

Magic must not come at the cost of safety. We need:

- consent before network access
- safe mode refusal for GitHub operations
- explicit repository prefill from the current working repo
- local-only trust boundaries for secrets and tokens
- read-only functionality first, then write flows behind stronger guards
- AI summarization that is optional, clearly scoped, and clearly explainable

## 3. Design principles

### 3.1 Make GitHub a native workspace surface

GitHub features should live in the same conceptual layer as file management and project tasks, not as a second-class dialog.

The base patterns already in QUILL are a good blueprint:

- `main_frame_github_items.py` is a read-only GitHub browser entry point
- `project_task_commands.py` is a developer-profile gate for coding features
- `feature_catalog.py` defines the shared feature model and default-off behavior

We should extend this pattern: GitHub operations should be first-class capabilities of the developer profile, not arbitrary one-off commands.

### 3.2 Keep the model explicit

A productive GitHub integration needs clear boundary layers:

1. Repository discovery and link mapping
2. Auth and token handling
3. GitHub API/provider access
4. Diff and thread analytics
5. AI summarization / explanation
6. UI presentation and action orchestration
7. Safe mode, consent, and profile enforcement

This makes transformations safer and easier to test.

### 3.3 Prefer context-rich actions over raw API exposure

The biggest product win is not “the app can call GitHub.” It is:

- open repo
- understand the state
- explain what matters
- recommend next actions

This means we should prefer:

- diff summaries over raw JSON dumps
- issue PR context over API-driven searching alone
- commit-story over commit-list only
- threaded review awareness over disconnected comments

### 3.4 Treat GHManage as an inspiration, not a template to copy blindly

GHManage is a useful reference because it models GitHub as a real developer workflow surface. But QUILL should go beyond GHManage by layering in:

- stronger local repo context
- developer profile gating
- safe mode integration
- AI summarization and issue triage in the editor itself
- parity with the QUILL Lite and QUILL app model
- release documentation, onboarding, and feature visibility

This is not just “import GHManage”; it is “turn the repo-native GitHub workflow into a native QUILL capability.”

## 4. Core feature set for the developer experience

### 4.1 Repository workbench

Add a `GitHub Workbench` surface accessible from the editor.

Capabilities:

- repo selection from current document or active git checkout
- recent repos
- repo health summary
- open issues, PRs, draft PRs, branch status, commits, releases, workflow runs
- filter by owner, repo, label, status, reviewer, assignee
- one-click open in the editor or as a detail panel

This should be the umbrella surface that most GitHub actions flow through.

### 4.2 Diff and review context

When a PR or commit is selected, render a context-aware review view:

- file list
- changed hunks
- side-by-side or inline summary view
- summary of intent and risk
- links back to the local repo state
- “compare with current branch” mode

This is dramatically more useful than a raw list of PRs.

### 4.2.1 PR review UX: rich access to comments, checks, and review flow

The PR review experience must be first-class, not an afterthought. A reviewer should be able to get to the right conversation, code, and decision state in one or two actions without hunting through menus or tabs.

The default review layout should be a three-part native QUILL experience:

- left: PR summary, metadata, status chips, reviewer state, and file list
- center: diff pane with inline hunk navigation and review markers
- right: conversation panel with review comments, replies, checks, and action rail

#### Review surface behaviors

- Every PR row should expose a single, obvious review entry point: “Open Review”, “Comments”, or “Files” from the row action menu and the detail toolbar.
- The details pane should include a full review toolbar with buttons for:
  - Open Thread
  - Show Files
  - Show Comments
  - Show Checks
  - Open in Browser
  - Copy PR Link
  - Copy Review Summary
  - Resolve / Reopen Thread
- Review thread count, unresolved count, review requested count, and approval state should be visible at all times in the header bar.
- Thread headers should show whether they are outdated, resolved, pending, or awaiting a reply.

#### Comment access should feel effortless

Comments are not a side channel; they are part of the code review process.

- selecting a file should immediately show that file’s comments and review decisions
- clicking a comment should jump to its exact hunk or changed line in the diff
- pressing Enter on a comment row should open the full thread in context
- the thread panel should show all replies, nested conversations, and metadata in readable order
- the UI should clearly separate “review comment”, “general conversation”, and “system status” messages
- users should be able to expand/collapse thread groups without losing place

#### Native QUILL action model

We should implement review actions as native controls instead of browser-like overlays:

- context menu on a PR item: Review, Open Thread, Open Files, Open Checks, Copy URL, Mark as Read, Request Reviewers, Reopen/Close
- context menu on a comment: Reply, Quote, Copy Text, Copy Link, Open File, Jump to Hunk, Resolve/Unresolve
- context menu on a changed file: Open Diff, Show Comments, Review File, Open in GitHub
- buttons in the detail toolbar for the most frequent operations
- keyboard accelerators for the high-frequency flows such as comments, thread navigation, and file jump
- screen-reader-friendly labels for every action and status chip so keyboard and assistive tech users get the same power as mouse users

#### Review intelligence and summaries

Beyond raw comment access, we need review understanding:

- collapse repeated or noisy feedback into a summarized action list
- extract unresolved concerns and required follow-ups from all review threads
- highlight approval state and blocked status in plain language
- show a “what needs attention” summary for the selected PR
- surface likely review hotspots before the user reads every comment in the thread

This should be optional AI assistance, not the only path to actionable review context.

#### Checks, approvals, and merge-ready status

The review experience should bridge discussion and merge readiness:

- show CI status, check runs, and failed job summaries in the review panel
- surface whether the PR is draft, ready, blocked, approved, or changes requested
- expose “approve”, “request changes”, “comment”, and “merge” actions from the same review surface
- show when the branch is stale or out of date and turn that into a clear warning ribbon
- allow users to open the exact check or job log directly from the review panel

#### PR review data model and UX contract

The underlying model should expose all of this explicitly:

- PR metadata: status, mergeability, review state, author, requested reviewers
- comments: thread id, user, path, line, reply depth, resolved state, outdated state
- file-level review insight: changed files, comments by file, risk summary, changed-line hotspots
- checks: status, conclusion, failing jobs, links to logs
- merge actions: ready/draft toggle, merge method, rebase/merge/squash choices

This keeps the experience rich, consistent, and testable while still feeling immediate and native in QUILL.

### 4.3 Thread and conversation intelligence

Turn review threads and issue discussions into structured, readable updates:

- summarize thread intent
- extract action items
- identify blocking questions
- highlight unresolved concerns
- surface reviewer approval state

This should be optional AI-augmented behavior, never required for access.

### 4.4 Issue-to-branch-to-PR workflow

We need a complete loop:

- choose an issue or draft task
- create or open a branch
- generate a patch plan
- make changes in local repo
- review diff
- optionally generate PR text
- publish a PR from the app

This is the real productivity win.

### 4.5 Local repo awareness

The biggest differentiator is tying GitHub state back to the local repo state:

- repo prefill from Git remotes
- current document repo detection
- branch comparison against GitHub default branch
- local dirty-state awareness
- PR branch tracking from remote branch metadata
- warnings when local work is not in sync with remote

### 4.6 AI-assisted understanding

We need a lightweight, explainable AI layer:

- “Summarize this PR”
- “What changed in this review thread?”
- “What are the risks of merging this?”
- “What should I look at first?”
- “What changed since my last review?”

This should call into the same AI connection model already used elsewhere in QUILL, not a bespoke parallel mechanism.

### 4.7 Developer profile gating and safe mode integrity

GitHub features must respect the same developer profile and safe-mode semantics as the rest of the product:

- `core.developer` / `coding` feature flag is required for full GitHub workflow surfaces
- safe mode refuses network-operated GitHub actions
- feature gating should be handled by the host, not by a special-case dialog
- the developer profile should expose “GitHub Workbench” as a first-class capability, not a hidden coder mode

This is essential for trust and product coherence.

## 5. Proposed UX model

### 5.1 surfaces

We should add these user-facing surfaces:

- GitHub Workbench
- Repo Summary Panel
- PR / Issue Detail pane
- Review Thread Reader
- Branch / Commit Explorer
- AI Summary Panel
- PR Draft Composer

These are not disconnected windows. They should behave like the rest of QUILL: one core UI shell, contextual actions, and consistent keyboard support.

### 5.2 interactions

The user interaction model should feel natural:

- open repo from current file or repo root
- select issue/PR/commit
- inspect summary, diff, and thread state in context
- click “Open in Local Repo” or “Compare with Current Branch”
- generate a summary or action plan
- prepare PR or patch without manual copy-pasting

This is the “GitHub as a second brain” pattern, and it is much more valuable than a plain list of API objects.

## 6. Architecture plan

### 6.1 Layered design

We should implement the integration in the same layered pattern QUILL already uses.

#### Core domain models

New or extended domain areas:

- repo metadata
- issue / PR models
- review thread models
- commit / branch state models
- summary and risk models
- action plan / patch-plan models

These should live in `quill/core/github` or a parallel core package and avoid UI dependencies.

#### Provider layer

A provider abstraction should handle GitHub API interactions:

- authentication and token resolution
- repository lookup
- issue/PR fetching
- thread and comment retrieval
- diff fetch and render metadata
- branch and commit queries

This should sit under the UI and remain generic and testable.

#### UI orchestration layer

The UI should handle:

- window creation
- show/hide panels
- input and keyboard navigation
- thread selection updates
- context menu and launcher actions
- AI-summarize calls on demand

This is where the actual “magic” becomes visible.

### 6.2 Relevant QUILL patterns to follow

We should align with the existing repo patterns:

- feature gating via `FeatureDefinition` and `default_off`
- safe mode refusal patterns in GitHub-related commands
- document-origin and repo detection from local git metadata
- AI availability checks via the same connection gate used elsewhere
- layered UI mixins rather than monolithic widget code

The existing files provide a strong foundation:

- `quill/ui/main_frame_github_items.py`
- `quill/ui/project_task_commands.py`
- `quill/core/feature_catalog.py`
- `quill/core/github/*.py` (existing GitHub layer)

## 7. Implementation roadmap

### Phase 1: complete the GitHub workspace foundation

Objectives:

- finalize the GitHub provider abstraction
- standardize repo detection and origin mapping
- clean up the read-only GitHub browser to be a stable entry point
- enforce safe mode and consent gates consistently

Deliverables:

- repo detection + current-file prefill is reliable
- GitHub browser works as a documented entry surface
- issue/PR browse path is consistent across app flows

### Phase 2: add review + diff intelligence

Objectives:

- make PRs and issues readable in context
- show diff summaries, changed files, and branch comparison
- surface blocking comments and unresolved threads

Deliverables:

- PR detail panel
- commit and branch comparison views
- thread summary and action-item extraction

### Phase 3: connect the local repo lifecycle

Objectives:

- bind local repo state to remote review state
- add branch status and merge-risk awareness
- align GitHub work with the current project state

Deliverables:

- local repo to remote repo mapping
- branch mismatch warnings
- commit story summarization
- dirty-state warnings around GitHub actions

### Phase 4: add AI workflow automation

Objectives:

- add contextual summarization for issues, PRs, diffs, and review threads
- offer “what changed”, “what matters”, and “what should I do next?” flows
- generate PR descriptions from the actual diff and thread data

Deliverables:

- summary actions in the GitHub UI
- AI-generated PR text draft
- issue triage summary / reviewer brief

### Phase 5: production polish and release documentation

Objectives:

- add release notes, changelog entries, developer guide updates, and user-facing guidance
- ensure both QUILL and QUILL Lite are documented appropriately
- include attribution for the GHManage inspiration as part of product credits and design docs

Deliverables:

- release notes and changelog updates
- developer guide coverage
- announcement text and feature documentation
- attribution documentation

## 8. Documentation and release plan

We need this feature to be not just code, but a visible part of the developer story.

### Developer guide updates

Add a section describing:

- how GitHub features are accessed in the app
- the role of safe mode and consent
- how developer profile gating works
- how GitHub browser and repo-aware workflows are intended to behave

### Announcements and release notes

Feature narrative should explain:

- GitHub has become part of the editor’s developer surface
- the app now understands repo context, issue/PR state, and review threads
- this is not a raw API crawler; it is the editor’s GitHub workbench

### Changelog

Entry should include:

- GHManage-inspired GitHub experience integration
- repo-aware issue / PR browsing
- AI summaries and diff-aware review context
- developer profile gating and safety architecture
- improvement of the overall coding workflow

### Attribution

This should be properly credited, with attribution to Kelly Ford and GHManage as inspiration for the product patterns, while being explicit that the final QUILL implementation is a purpose-built adaptation of those ideas into the QUILL architecture and safety model.

## 9. Feature-gating, safety, and trust

This is a core requirement. We must hold the line on safe behavior:

- no GitHub access in safe mode
- no secret handling in UI code
- provider access is isolated to the trusted layer
- AI summarization is optional and dimensioned to the same connection autonomy as other AI features
- the developer profile is the gate for coding-level GitHub features

This is not a footnote; it is the product guarantee.

## 10. Success criteria

The feature is successful when a developer can:

- start from the active repo or file and open the GitHub surface
- understand repo state quickly
- review issues and PRs without leaving context
- get useful summaries of threads, diffs, and changes
- move from repo state to patch generation to PR drafting without friction
- trust that the experience respects safe mode, consent, and developer profile gates

## 11. Execution strategy

The work should be shipped in narrow, reviewable slices:

1. repo-aware GitHub browser and gating cleanup
2. diff and thread overview panels
3. local/remote repo comparison and branch awareness
4. AI summarization and action extraction
5. PR draft / branch flow orchestration
6. release docs, onboarding, and product narrative

This keeps the work grounded, testable, and useful throughout the rollout.

## 12. Final strategic statement

This should not just be “GitHub inside an editor.”

It should be “the developer workflow is complete in the editor.”

That means the repository becomes a first-class object in the app, GitHub becomes a readable and actionable part of the workspace, and the developer can move from code to comprehension to action without hitting the ceiling of a disconnected toolchain.

The goal is not merely to imitate GHManage. The goal is to make the world better by turning repository intelligence into the default experience of a modern developer toolchain.

## 13. GHManage feature audit and product lessons

The GHManage codebase is materially broader and more mature than a basic GitHub viewer. It is not merely a repo list with some issue browsing. It is a complete GitHub workbench designed around a veteran developer workflow.

### 13.1 Feature inventory from the actual GHManage product

Based on the code and product docs, the most important capabilities to preserve as inspiration are:

- Repository chooser with favorites, activity, starred repos, watched repos, notifications, My Work, and saved searches
- Notifications inbox with read/done workflow and direct issue/PR opening
- Search across GitHub using GH CLI qualifiers with saved-search persistence
- “My Work” aggregation for assigned work, review requests, mentions, authored work, and repo-level needs
- Open any GitHub address: repo, issue, PR, commit, release, workflow run, or branch
- Issue creation from the app, using the current repo or selected context
- Pull request controls: checks, review, draft/ready toggles, merge, request reviewers, update branch
- Copy actions for links, markdown links, titles, numbers, SHAs, and details
- GitHub account switching and per-repo watch settings
- Activity feed from followed users and watched repos
- People view including following/followers, repo ownership, stars, forks, watchers, and activity traversal
- Combined issues/PRs inbox view with filters and sort rules
- Git metadata views: branches, commits, tags, releases, workflow runs, and GitHub Pages
- Release visibility including download counts and per-file asset breakdowns
- Label management and label-driven filtering
- Branch-specific commit browsing and file history access
- File and diff review, with inline patch context and repo file browsing
- Security alerts for Dependabot, code scanning, and secret scanning with classification logic
- Discussions support and comment reading
- Contextual actions menu that answers “what can I do here?” without guesswork
- Keyboard-first interface with screen-reader-friendly detail modes

This is the historical landscape that matters. GHManage wasn’t just a side app; it was a full developer-facing GitHub work surface with a strong opinion about developer flow.

### 13.2 Product lessons we should carry into QUILL

The biggest product lessons are not cosmetic. They are operational and architectural:

1. GitHub should be repository-first
   - The app should begin from the current repo, file, or branch context, not from a stand-alone empty canvas.
   - QUILL should make the repo the anchor for GitHub work.

2. The experience should be context-rich, not raw-API-driven
   - GHManage’s value comes from turning API data into meaningful views: issue inbox, repo activity, thread context, branch comparisons, diff summaries, and workflow status.
   - QUILL should do the same with a tighter local-repo context model.

3. The action menu matters as much as the content list
   - GHManage’s actions menu is a smart design choice: it transparently tells the user what actions apply to the selected item and blocks irrelevant operations.
   - This creates trust and reduces accidental misuse.

4. Accessibility is a product feature, not a luxury
   - The full-mode views, status announcements, comment navigation, and keyboard-first interaction are part of the strength of the app.
   - QUILL should carry these patterns forward, especially in the developer profile and editor surfaces.

5. Reader-first design scales better than write-heavy design
   - The easiest wins are in monitoring repo state, reading diffs, reviewing issues, and surfacing review context.
   - Write flows should follow after the read surface is mature and safe.

6. Feature limits and safe mode are not optional
   - GHManage is careful about auth, permissions, and GitHub capability boundaries. QUILL should take that seriously and keep its developer-profile gating explicit.

### 13.3 How this should map to QUILL and QUILL Lite

The GHManage patterns should be adapted into the QUILL ecosystem as a native feature set rather than a direct port.

For QUILL:

- full GitHub workbench
- issue/PR detail and diff review surfaces
- repo context from active project
- AI-powered summary and triage
- branch/commit/repository state awareness
- fuller developer profile integration

For QUILL Lite:

- the same GitHub Items viewer and PR review outline as QUILL
- the same context menus and available read/write review actions
- the same consent, token store, and network boundary
- the same newly added workbench capabilities by default; any exception must
  be explicit in the product requirements and user documentation

The first shared entry point is **File > GitHub Workbench...** in Lite. Other
GitHub commands still need their own Lite entry points and parity verification.

### 13.4 Attribution and design integrity

This work should be explicitly credited as inspired by the GHManage ecosystem and by the product maturity and UX thinking of Kelly Ford, while remaining a QUILL-native implementation.

The right framing is:

- “GHManage provided a high-quality historical model for GitHub workbench design and interaction patterns.”
- “QUILL adapts those patterns to the editor architecture, local repo context, and developer profile safety model.”
- “This is not a blind copy; it is a purpose-built integration for the QUILL platform.”

This is both more respectful and more commercially and technically credible.

## 14. Documentation, release, and developer-profile rollout

We need the feature to be visible everywhere the user sees the product story:

### Developer guide

Add a dedicated section covering:

- GitHub access as a first-class developer surface
- repo-detection and prefill behavior
- safe mode and consent behavior
- issue/PR workflow entry points
- developer profile gates and feature availability
- how to reach each shared GitHub feature in QUILL and QUILL Lite

### Announcements and release notes

Document the launch as:

- GitHub is native to the Quill workspace
- repository context now feeds issue/PR review flows
- GHManage-inspired GitHub workbench patterns are now part of the developer experience
- AI assistance is layered on top of the same trusted repo view, not bolted on separately

### Changelog

Add release notes entries covering:

- GitHub workbench launch and developer-profile gating
- repo-aware issue and PR browsing
- branch and commit awareness
- AI summary and diff review support
- GitHub accessibility and keyboard-first developer workflows
- attribution to GHManage and Kelly Ford’s design influence

### Documentation strategy

This should be documented as a top-level product narrative, not only as a technical implementation note. Developers need to understand that GitHub is now a core part of the workspace, not an occasional side panel.

## 15. Implementation notes for follow-up work

Planned technical touchpoints in this repo:

- `quill/ui/main_frame_github_items.py` — main GitHub viewer entry point
- `quill/core/github/*` — provider and repo logic
- `quill/ui/project_task_commands.py` — developer profile gating pattern
- `quill/core/feature_catalog.py` — feature model and default-off behavior
- docs and release materials under `docs/` and release-facing markdown files

## 16. Implementation audit (2026-11-05)

This is a status check against the local GHManage reference at `S:\code\ghmanage`.
The earlier sections describe a product plan; they must not be read as a claim
that every item has shipped. QUILL uses PyGithub and its own consent, token, and
safe-mode gates; GHManage's `gh` transport and standalone app shell are not
directly copied.

| GHManage capability | QUILL status | Current surface or remaining work |
| --- | --- | --- |
| Issues and PRs, search, filtering, sorting, columns, details, comments | Implemented | GitHub Items viewer; repository-scoped search and local quick filter |
| Branches, commits, tags, releases, workflow definitions and runs | Implemented | GitHub Items viewer and workflow actions |
| PR changed files and branch comparison | Implemented | Accessible diff and compare dialogs |
| PR reviews, threads, checks, reviewers, draft/ready, update branch | Implemented in this worktree | Shared QUILL and QUILL Lite reader; native PR outline and contextual menus; manual screen-reader acceptance remains pending |
| Issue and PR writes, batch actions, repository administration | Implemented in separate flows | GitHub Items viewer and GitHub administration commands |
| Pinned repositories and favorites | Implemented | Items saved items; Explore repository chooser includes pinned and recent repositories |
| Notifications and security alerts | Implemented | Existing commands and Explore views; notifications can be marked read |
| Account management and local repository context | Implemented in QUILL form | Account/token management and checkout-derived repository prefill |
| Global saved searches, My Work, activity feed, people traversal | Implemented in this worktree | Explore list/detail views and local saved-query store |
| Personal attention queue | Implemented in this worktree | Combines assignments, review requests, mentions, and failed-check PRs; saved repository/category filters and snoozes are local and account-scoped; partial data stays visible |
| GitHub issue or PR to local worktree | Implemented in this worktree | Verifies a matching GitHub remote, names a local branch, shows the starting ref and dirty-file count, then creates a separate worktree without fetching or writing remotely |
| Projects and issue dependencies | Implemented in this worktree | Lists Projects v2 items and fields, blockers, sub-issues, and parent progress; supports confirmed field and relationship changes and a next-unblocked action |
| Starred/watched repository discovery and per-repository watch settings | Implemented in this worktree | Explore discovery and star/watch context actions |
| GitHub Pages browsing and publish history | Implemented in this worktree | Explore Pages view shows site and builds where API access permits |
| Label management and label-driven issue navigation | Implemented in this worktree | Explore label view, label create/edit/delete, issue search from label |
| Gists, release download counts, workflow job logs and artifacts | Implemented in this worktree | Explore gists, release assets, run jobs/logs/artifacts |
| Open any GitHub address, contextual copy actions, and unified Actions menu | Partial | Repository URL parsing and contextual copy/actions exist; deep routing of every GitHub URL remains open |

Address routing and the other accepted GX roadmap items remain feature gaps
until they are built and verified. Keep the audit synchronized with the
product requirements, [GitHub Workbench Roadmap](./github-roadmap.md), and
user-facing [workbench reference](../github/workbench-reference.md). The user
will perform the manual Windows assistive-technology acceptance separately.

This plan is intentionally written to be reviewed before implementation, so that the feature is shaped as a coherent QUILL product story rather than a collection of API wrappers.
