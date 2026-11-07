# GitHub Workbench Roadmap

**Accepted scope:** 2026-11-06. This is the implementation record for the full GitHub expansion (GX01–GX15), in addition to the bounded G1–G4 engineering finish. The user owns the Windows assistive-technology acceptance in G5; that work is outside the engineering completion percentage and will be handled by the user.

## Product direction

Build one shared QUILL and QUILL Lite workbench that makes the next useful action clear: what needs attention, what changed, what blocks progress, and what can happen next. Extend the native Items, Explore, review, and administration dialogs. Keep keyboard operation, screen-reader names, plain-language status, and a readable list or outline equivalent in every workflow.

Three journeys guide the work:

- **Resume work:** restore the repository, issue or pull request, filters, exact thread or diff location, and unpublished draft. Show changes since the last visit. Loading the workbench never marks remote notifications read.
- **Explain a blocker:** name the reason and freshness of every status, then link directly to the requested review, failed check, job, or source line. Partial, stale, unknown, and missing data remain explicit.
- **Finish the loop:** guide issue → local branch/worktree → change → pull request → review → checks → merge → release evidence. Suggest the next valid action and leave publishing, merging, and repository changes under user control.

## Roadmap

The waves show implementation order. Existing foundations are listed so work reuses the current provider and native dialogs instead of rebuilding them.

| ID / wave | Existing foundation | Accepted delivery and acceptance |
| --- | --- | --- |
| **GX01 / W1 — Open a GitHub reference** | Repository parsing and browser handoff exist. | Accept repository, issue, pull request, discussion, commit, branch/file/line, release, and workflow URLs. Route supported links to the best native view and preserve location. State unsupported or enterprise hosts plainly; malformed links never write or send credentials. |
| **GX02 / W1 — Personal attention queue** | My Work, notifications, repository selection, and local saved items exist. | Combine review requests, mentions, assignments, and failed checks across selected repositories. Explain source and freshness, deduplicate rows, support local snooze and saved filters, and show since-last-visit changes. Partial pages never look like an empty inbox; load never marks notifications read. |
| **GX03 / W1 — Context-preserving navigation** | Recent/pinned repositories, favorites, saved searches, and back navigation exist in separate views. | Add searchable actions, recent locations, Back/Forward, saved views, and local draft recovery. Returning from a browser, diff, or nested dialog restores the selected row/thread. Every unavailable action explains its prerequisite. |
| **GX04 / W1 — CI diagnosis** | Workflow jobs, status, logs, artifacts, and explicit rerun controls exist. | Show failed steps, annotations, bounded excerpts, prior attempts, source links, run/attempt/SHA provenance, and visible truncation. Rerunning failed jobs is explicit and duplicate activation cannot start duplicate work. |
| **GX05 / W2 — Issue intake and triage** | Issue creation, labels, comments, and batch updates exist. | Support repository templates/forms, required-field validation, assignees, milestones, duplicate suggestions, cross-links, reusable replies, and batch previews. Drafts do not publish; duplicate suggestions never close issues; every batch item reports its result. |
| **GX06 / W2 — Projects and dependencies** | GitHub Projects and issue dependencies remain the source of truth. | Provide keyboard-editable tables/outlines for supported project fields, sub-issues, blocking links, parent progress, and next unblocked work. Every board has a linear reading order; unsupported fields or permissions are named. |
| **GX07 / W2 — Local repository continuity** | Local Git and remote repository browsing exist as separate surfaces. | Show fork/upstream, dirty files, ahead/behind, branches, and worktrees. Starting an issue prepares a named branch/worktree after a preflight. Never overwrite dirty files or run shell text taken from remote content. |
| **GX08 / W2 — Deep accessible review** | The native PR outline, exact diff-line mapping, replies, and thread resolution exist. | Add changed-since-review, next unread/unresolved navigation, reviewer checklists, pending review drafts, and suggestions with exact patch preview. Renames, deletions, binary/large files, outdated threads, and unavailable patches remain honest; applying a suggestion verifies current content and preserves edits. |
| **GX09 / W2 — Policy-aware merge path** | GitHub mergeability, reviews, checks, and merge actions exist. | Read required checks/reviews, rulesets, CODEOWNERS context, and merge-queue/auto-merge state. Explain every blocker and watch the exact revision. GitHub remains authoritative; changing HEAD invalidates prior readiness; no branch-protection bypass. |
| **GX10 / W2 — Release and deployment evidence** | Releases, tags, assets, and Pages/build history exist. | Draft release notes from an explicit compare range; verify assets and provenance; show deployment environments/checks and release history. Draft versus published stays clear, and publishing/deploying requires a deliberate action. |
| **GX11 / W3 — Security and dependencies** | Dependabot alerts are available when the token and repository allow them. | Add code/secret scanning and advisory views, linked fixes, and evidence-based grouping. Missing permission never means zero risk; exports redact sensitive details; alerts are not auto-dismissed. |
| **GX12 / W2–W3 — Collaboration and knowledge** | Gists, activity, mentions, and issue/PR conversations are available. | Add Discussions, answers, wiki/docs, saved replies, and links across discussion → issue → pull request. Preserve author and thread context; suggestions remain drafts until submitted. |
| **GX13 / W3 — Account and repository administration** | Repository administration exists in QUILL; Lite shares Items, Explore, review, and diff. | Add account-aware repository switching, team/collaborator permissions, SSO/auth-expiry diagnostics, and Lite entry points. Cache and tokens are isolated by host/account; consequential changes retain explicit confirmation. |
| **GX14 / W3 — Workspace and service handoffs** | Codespaces commands and browser handoffs exist. | Preserve exact context when opening Codespaces or integrations; show health and opt-in workspace/repository metrics. Disclose cost-bearing launches, never provision automatically, and report team bottlenecks without ranking people. |
| **GX15 / W2 — Optional grounded assistance** | QUILL already has configured AI providers and local consent boundaries. | Explain selected diffs, draft PR descriptions/reviewer briefs, decompose issues, and prepare release notes from user-selected evidence. Cite file/line/thread/SHA, show omitted or truncated context, keep drafts editable, and retain deterministic non-AI workflows. Remote text is untrusted input; no model upload outside configured consent. |

## Shared acceptance contract

- No silent partial results, stale readiness, missing pages represented as empty, or remote state changes caused by reading.
- Every action is keyboard reachable, named for assistive technology, usable without color or hover, and returns focus predictably.
- Large logs and result sets load on demand with selection preserved, bounded memory use, explicit truncation, and a readable fallback.
- Local drafts and navigation state are private, recoverable, account-isolated, and never auto-submitted after reconnect.
- Writes state the target and effect before execution. Non-idempotent actions are not blindly retried after timeouts; batch outcomes identify each item.
- AI is optional, grounded in selected evidence, and subject to existing consent. It never invents checks, merge readiness, or completion claims.

## Delivery order

1. Finish G1–G4 engineering contracts, documentation, gates, and integration preparation for the current workbench.
2. Complete W1 (GX01–GX04), then W2 (GX05–GX10, GX12, GX15), then W3 (GX11, GX13, GX14).
3. For each delivery, add focused failure cases, run relevant repository gates, review on the final candidate, and retain fresh CI evidence. Rebase/conflict resolution invalidates affected test evidence.
4. The user owns the manual Windows keyboard, screen-reader, scaling, and braille acceptance. Engineering changes and merge readiness must not claim that acceptance has occurred.
