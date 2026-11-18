# Complete the GitHub and WordPress Workbenches

**Owner:** Jeff Bishop / Community Access  
**Created:** 2026-11-10  
**Purpose:** One master delivery checklist for the redesigned Workbenches in QUILL and QUILL Lite.  
**Product direction:** Account for every available REST/API capability, and turn that coverage into understandable, delightful, accessible workflows.

## 1. Destination and rules for this list

The destination is two exceptional native Workbenches sharing one engine: people can discover what is possible, understand what matters, perform the work safely, and recover their place. API coverage is the completeness measure; excellent task flows are the product.

An API operation is accounted for only when its exact capability, permissions, limits, target host/version, UI home, help, and delivery state are recorded. A menu label, generic route listing, planned classification, or API Console alone does not prove a polished feature is finished.

**Checklist states**

- **OPEN:** the implementation record explicitly identifies unfinished work.
- **AUDIT:** code or a prior PR claims implementation; establish current behavior and evidence before deciding whether more coding is needed.
- **DEPENDENCY:** requires another repository, runtime package, supported server/plugin, account, or live environment.
- **PROPOSAL:** a new design recommendation. Recording it does not make it an accepted requirement.
- **SUPERSEDED:** historical wording replaced by a later decision; reconcile the records rather than rebuilding it.

All unchecked requirement-ledger entries below mean “acceptance evidence still needs to be attached,” not “nothing has been built.” Do not estimate a completion percentage from module counts, PR titles, route counts, or this document's checkboxes.

### Definition of finished

- [ ] Every accepted requirement has an implementation reference and acceptance result, or an explicit, owner-approved scope disposition.
- [ ] Every API operation in the supported API snapshots/discovered site indices has a defensible classification; no unclassified operation remains.
- [ ] Every supported operation has an excellent native task flow where appropriate; advanced operations have a discoverable, accessible escape hatch.
- [ ] GitHub REST, GraphQL mutations and relevant query/viewer fields are covered; WordPress core, custom routes, plugin namespaces and Abilities are accounted for per connected site.
- [ ] Both editors expose the shared capability consistently. Differences are deliberate, documented and tested.
- [ ] Current candidate passes CI and the required engineering gates.
- [ ] Live-account/site checks and manual accessibility results are recorded separately from automated checks.
- [ ] Documentation, installed help, generated artifacts and runtime packaging match the released behavior.
- [ ] Reading never changes remote state; writes name their account/site, target, consequences and result.
- [ ] Partial data, missing permissions, unsupported versions, stale evidence and uncertain write outcomes never masquerade as success or emptiness.

## 2. Sources and precedence

Read later explicit decisions before interpreting older status tables.

| Source | Role |
| --- | --- |
| [GitHub Workbench PRD](./docs/Product%20Requirement%20Documents%20and%20Specifications/github-workbench-prd.md) | Accepted redesign, phases 0–13, GH-R requirements, API appendices, cross-repository work and fourth sweep |
| [WordPress Workbench PRD](./docs/Product%20Requirement%20Documents%20and%20Specifications/wordpress-workbench-prd.md) | Accepted redesign, WP-R requirements, W0–W8, recorded site API and later form-integration decision |
| [Implementation status](./docs/planning/workbench-implementation-status.md) | Latest recorded delivery state and later scope decisions |
| [GitHub roadmap](./docs/planning/github-roadmap.md) | Accepted GX01–GX15 expansion, user journeys and shared acceptance contract |
| [Original GitHub developer experience plan](./docs/planning/github-workbench.md) | Earlier vision and historical implementation audit; reconcile against the accepted redesign |
| [WordPress design and implementation log](./docs/design/wordpress.md) | Historical detail plus concrete remaining Workbench/groundwork tasks in section 19 |
| [Command Key design](./docs/design/command-key.md) | Context-aware commands, Jev, previewed batches and catalogue integration |
| [GitHub Workbench reference](./docs/github/workbench-reference.md) | Generated/current surface reference; validate against implementation |
| [WordPress regression plan](./docs/qa/wordpress-regression-testing.md) | Live site scenarios and recorded results |
| [Screen-reader checks](./docs/qa/screen-reader-checks-2026-10.md) | Manual acceptance work |
| [Legacy release acceptance](./docs/release/acceptance/section-github.md) | Historical scenarios; several menus, sign-in and publishing-gate descriptions need reconciliation |
| [Forms payment design](./docs/design/forms-payments-design.md), [plugin contract](./docs/design/forms-payments-plugin-contract.md), [payment acceptance](./docs/qa/forms-payments-acceptance.md) | Related QAF (QUILL Accessible Forms) dependency and payment boundaries, not evidence that the Workbench or live checkout is complete |
| [Inbound embed/safety review](./docs/design/publishing/wordpress-inbound-embed-and-safety-review-2026-06-29.md) | Earlier connection and content-ingress context |

This audit surveyed Markdown planning/design/engineering/superpowers/QA sources under the repository's documentation tree and the accepted PRDs. External QAF/BAF/Site Types repositories and the external handoff note have not been independently audited here. Add their evidence before closing dependent items. MCP configuration is connection plumbing, not a product feature-completion record; no credential values belong in this file.

### Decisions already recorded

- The classic GitHub Items/Explore and WordPress management-window fallback choices are retired; editor doors open the Workbench.
- Alt+Enter opens Properties; ordinary typing remains type-ahead. Do not revive per-property letter shortcuts.
- The current first-class WordPress plugin integrations are QAF, Gravity Forms and Paid Memberships Pro. Earlier additional plugin candidates remain historical/deferred scope unless explicitly restored.
- Generic WordPress route/schema/Abilities discovery remains in scope. Therefore **all other plugins' discovered APIs must still be accounted for**, even when a polished plugin-specific integration is deferred.
- Provider credentials and checkout stay plugin-owned. QUILL does not become a payment gateway or collect provider secrets.
- The accepted GitHub roadmap assigns the user manual Windows assistive-technology acceptance. Engineering completion must not imply that those checks occurred.

### Resolve specification drift

- [ ] Make one decision register linking every superseding decision to affected PRD sections, roadmap rows, tests, help and manual text.
- [ ] Reconcile WordPress PRD decision 17 (“Across Sites” still described as awaiting confirmation) with its Must requirements and already recorded W8 implementation; record the authoritative disposition.
- [ ] Reconcile original plugin-specific promises with the later three-integration scope. Account for every discovered route without silently promising bespoke support.
- [ ] Reconcile “one release of classic fallback” language with its recorded retirement.
- [ ] Reconcile historical G1–G5 and GX wave terminology with phases 0–13 and W0–W8; retain IDs and define their relationship.
- [ ] Remove stale “everything not listed is built” claims unless backed by a current coverage ledger.
- [ ] Replace old menu paths, token-only onboarding and obsolete publishing flags in release acceptance.
- [ ] Confirm which historical WordPress parity packages remain relevant to native Workbench delivery and which are superseded or deferred.

## 3. Baseline: what is recorded as implemented

These are implementation claims to preserve and verify, not instructions to rebuild them.

| Area | Recorded baseline | Outstanding proof or extension |
| --- | --- | --- |
| Shared frame | Tree/list/details/status bar, menus, sheet models, dynamic nodes, actions, filters, history/help infrastructure | Native accessibility, lifetime, parity and performance acceptance |
| GitHub phases 0–6 | Workbench navigation, menus, editor doors, options, help and retirement of classic routing | Reachability regression and documentation consistency |
| GitHub phases 7–10 | Properties, broad sheet coverage, batch/history, filters, permissions and access tooling | Exact per-object/per-operation coverage and live validation |
| GitHub templates | Readable Markdown template selection, defaults, prefill and issue preview | YAML forms, discussion forms and full builder |
| WordPress W1–W6 | Provider/tree, sheets, editing, batch, conflict checks, spam/Gravity Forms, permissions, route classification, doors | Full requirement/combination coverage and live/AT acceptance |
| WordPress W7/W8 | Copy/compare/snapshot, calendar/editorial queue, Read Site, console, import/export, Watches, By Name/Across Sites/Site Sets/Fleet scaffolding | Several operations and packaging remain unfinished |
| Form conversion | QAF conversion previews; common Gravity Forms control conversion with full-form preservation and conflict checks | Behavioral regressions, complex-family boundaries and live/AT verification |
| PMPro | Abilities support; levels, orders, subscriptions, renewals, user memberships; previewed writes | Supported-version/site-permission and live cancellation acceptance |
| Practice Site | Launcher/blueprint and staging entry | Actual pinned runtime payload, lockfile, complete offline packaging and credential handoff |

## 4. First milestone: stabilize the current candidate

**Observed PR:** [#1837 — WordPress and GitHub Workbench follow-up](https://github.com/Community-Access/quill/pull/1837).  
**Observed head:** b3dddc29b2e9b5db586fbae8a0ef22549357123f, branch codex/workbench-combined-2026-11-10.  
**CI snapshot inspected in this session:** 18 successful check entries, four failing unit-test shards, plus their failing aggregate; 31 failing tests across the shards (6 + 9 + 8 + 8). This is a dated observation, not a claim about future runs.

- [ ] Re-fetch the candidate and latest checks before beginning fixes; identify inherited failures versus candidate regressions without dismissing either.
- [x] Fix or intentionally update routing contracts: WordPress Comments Waiting node, GitHub notifications and empty-window launcher. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Preserve QUILL Lite file-opening and current-document-to-Gist callbacks through the new Workbench route. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Resolve QAF field-conversion/duplicate/remove regression; prove conversion preserves rules, defaults, compatible choices and undo. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Fix Content Model source attribution; show the actual registrant where knowable, otherwise state the uncertainty. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Resolve reserved-key conflict around Ctrl+3 and the Workbench key contract. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Repair label ordering in the GitHub Filter Builder and review accessible-name/control-label violations. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Bind background work to surface lifetime; prevent callbacks targeting a closed Workbench. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Classify persistence write sites with retention, migration, account/site isolation and secret-handling evidence. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Restore reachability of legitimate GitHub subdialogs after removal of classic imports; distinguish a real missing entry point from snapshot drift. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [ ] Regenerate and review surface reachability, accessible-name inventory, tutorial reference, command corpus and Jev eval/gateway catalogues after behavior is correct.
- [ ] Update Help purpose coverage, new WordPress Workbench command/key documentation, guide contents and the actual GitHub chapter count.
- [x] Replace prohibited checkbox wording in authored/generated docs. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [ ] Review generated HTML for retained language/title, landmarks, skip links, focus styles, contrast overrides and table semantics. Markdown/HTML parity alone does not establish accessibility.
- [ ] Obtain a fresh successful candidate CI run, review and integration evidence. Rebase/conflict resolution invalidates affected earlier evidence.

**Exit:** no unexplained failing check; regressions are fixed rather than hidden by snapshots or weakened assertions.

## 5. Coverage architecture: every API capability accounted for

### 5.1 One operation ledger shared by both providers

- [ ] Define stable operation identity: provider, host/API version, method + normalized route or GraphQL operation/field, object kind and scope.
- [ ] Record: source/schema revision, documentation URL, supported versions, permission/capability, risk tier, request/response shape, pagination, rate limits, UI home, help, tests, owner and delivery state.
- [ ] Distinguish **native complete**, **schema-built usable**, **console usable**, **planned**, **web/admin-only**, **unavailable on this host/version**, and **explicitly out of product scope**. Keep unknown/unclassified separate and fail the completeness gate on it.
- [ ] Preserve the original PRDs' coverage classifications while adding the more precise delivery/acceptance dimension; avoid silently redefining existing gates.
- [ ] Require an explanation and a useful next action for every unavailable API feature.
- [ ] Record limitations in fields, values, media types, operations and scopes, not only route names.
- [ ] Generate a searchable “What can I do?” catalogue, coverage chapter and engineering backlog from this ledger.
- [ ] Refresh snapshots intentionally; show newly added, changed and removed operations and assign an owner.
- [ ] Test kind × scope × operation × permission × supported version, including mixed-selection and partial-failure cases.
- [ ] Separate API completeness from native UX completeness and from acceptance completeness in all progress reporting.

### 5.2 GitHub completeness

- [x] Vendor and pin the REST description and GraphQL schema; record provenance and licensing. *(Done 2026-11-13: `quill/data/github_api/` is refreshed from github/rest-api-description at commit 53fd7d2ea1380eabdcfcc9ab9a043a56ef444fd6 and docs.github.com's public schema.docs.graphql, both read 2026-11-13 and recorded in each file's `source`; the MIT licence is `quill/data/github_api/LICENSE-rest-api-description.txt`. A components.json notices entry is still to add, outside the GitHub files.)*
- [x] Implement Phase 11 coverage table, GATE-GITHUB-COVER and generated coverage chapter. *(Done 2026-11-13: `quill/core/github/api_coverage.json` + `api_coverage.py`, `tests/unit/core/test_github_api_coverage.py`, `quill.tools.github_api_coverage_audit` rostered in platform_report, and the generated "Everything GitHub can do, and where" chapter in `docs/github/workbench-reference.md`. 1626 rows: 302 covered, 1103 planned (the ceiling), 15 no_api_needed, 206 out_of_scope.)*
- [ ] Reconcile every operation in PRD Appendices E/F with the actual implementation, including GraphQL viewer permission answers and required reads.
- [ ] Track REST/GraphQL alternatives, preview/version headers, host compatibility, app/token types, organization policies and plan restrictions.
- [ ] Include pagination, ETags, secondary limits, GraphQL cost, cancellation and partial GraphQL errors.
- [ ] Reconcile enterprise-admin/migration exclusions with “all capabilities accounted for”: excluded operations still have a visible, justified ledger disposition.
- [ ] Validate GitHub Enterprise Cloud/data-residency and Enterprise Server capabilities per host/version; never send credentials to an unrelated host.
- [ ] Prove every existing Items/Explore action survives the redesign; no loss hidden behind a populated tree.

### 5.3 WordPress completeness

- [ ] Preserve each site's REST index and OPTIONS schemas with site/version/capability provenance and freshness.
- [ ] Cover core routes, custom types/taxonomies/statuses, nested meta, plugins, multisite where exposed, and Abilities input/output schemas.
- [ ] Complete the combination test: every collection GET argument, enum, sort, writable property, method and custom action has an accessible surface or an explicit disposition.
- [ ] Reconcile the historical 802-route classification (143 covered, 33 schema-built, 386 planned, 158 wp-admin-only, 82 out of scope) against the current snapshot. These historical counts are not completion percentages.
- [ ] Inspect every planned and wp-admin-only classification; verify that an API really is unavailable before routing to the browser.
- [ ] Do not call a namespace listing or raw item sheet complete unless a person can actually perform the advertised operation.
- [ ] Handle missing/poor schemas honestly; preserve unknown fields, offer readable raw details, and never invent safe write semantics.
- [ ] Retain read-only/unsupported-type fallback for schema forms whose nested structure cannot yet be edited safely.
- [ ] Account for authentication, REST-disabled sites, plugin capability customization, endpoint filtering and version changes.
- [ ] Every deferred plugin API gets discoverability, a capability description and a useful advanced/admin route; first-class integrations can follow separately.

## 6. GitHub delivery checklist

### GH-A. Native parity, Properties, filtering and permissions — AUDIT

- [ ] Complete Appendix A/B “nothing dropped” mapping and Appendix C object/sheet/filter mapping.
- [ ] Verify every editable field, mixed value, field removal, batch operation, conflict resolution, verify-after-save, history and supported undo/redo.
- [ ] Preserve issue types and organization-defined issue fields as typed values on issue rows, details, filters and Properties. Hidden, unsupported, unset, empty and unreadable values stay distinct.
- [ ] Repository and item-property checklists expose state in the row; Space changes it once, Enter saves, focus returns predictably, and JAWS/NVDA/VoiceOver do not hear a duplicate row.
- [ ] Verify project fields/views, branches/rulesets/protection, releases/assets, Actions, security, account/organization objects and team lifecycle.
- [ ] Verify per-account Read Only/Organize/Full, Safe Mode, tiers, typed confirmations, self-lockout prevention and permission explanations.
- [ ] Verify encrypted write-only secrets for repository/environment/organization scopes and selected-repository access.
- [ ] Verify View As Role, Compare Roles, Why Can't They?, My Access Here, access reviews and bulk changes against actual server authority.
- [ ] Complete all-attribute filters, Show Only/Hide, grouping, sorting, columns, Load More/All and honest local-filter scope. *(2026-11-18: Load More works on every list and Load All reaches the Explore-backed nodes; a partial list says so in the Items cell. Remaining: grouping, sorting and the column chooser beyond issues and pull requests.)*
- [x] Keep readiness tied to the exact HEAD/revision; invalidate it when anything relevant changes. *(2026-11-17: Why Can't I Merge? names the head commit it read, and Merge merges only that commit (REST `sha`); a push in between merges nothing and is said (`merge_readiness.py`).)*

### GH-B. Templates — DONE, Phase 12

- [x] Native YAML issue-form filling with required-field validation and golden body output. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Native discussion-form filling and category behavior. *(Done 2026-11-13: Ctrl+N on Discussions picks the category, fills `.github/DISCUSSION_TEMPLATE/<slug>.yml` in the issue-form window, falls back to title and body when there is no form or it cannot be filled; `quill/ui/github_workbench_templates.py`. The form's labels are not applied by createDiscussion, and the preview says so.)*
- [x] Templates node: Markdown/YAML issue forms, PR templates, discussion templates and applicable community files. *(Done 2026-11-13: Repository > Templates and Organizations > org > Templates, `quill/core/github/template_catalog.py`; own, inherited and missing rows; FUNDING.yml, CITATION.cff and CODEOWNERS open their own sheets (`quill/ui/github_template_sheets_dialog.py`), CODEOWNERS with Who Owns This Path. Since 2026-11-15, Check Owners asks GitHub whether each owner exists and can write (`quill/core/github/codeowners_check.py`).)*
- [x] Accessible builder, raw editor and preview with round-trip interop against real GitHub examples. *(Done 2026-11-13: `quill/ui/github_template_builder_dialog.py` and `quill/core/github/template_builder.py`; unknown keys survive the round trip. Since 2026-11-16, BFL (BITS Accessible Forms' language, the plain-text form language) interop too: `quill/core/forms/interop_github.py` maps the QAF model to GitHub's schema and back, GitHub-only keys ride in `@extensions`, and QUILL's own five issue forms round-trip through BFL unchanged (`tests/unit/core/forms/test_forms_interop_github.py`).)*
- [x] Field kinds, IDs, options, required settings, conditional/unsupported syntax, duplicate names and server constraints are checked before save. *(Done 2026-11-13: `template_builder.check`; errors stop Save, warnings do not; labels and assignees are checked against the repository's own and picked from them; Check This File on a `.github/ISSUE_TEMPLATE` or `DISCUSSION_TEMPLATE` YAML file puts each problem on its line (`quill/core/problems/builtin.py`).)*
- [x] Starters, conversions, repository/.github organization defaults and template chooser behavior. *(Done 2026-11-13: bug, feature, accessibility and blank starters; Markdown template to form and form to Markdown (says what it loses first); SurveyJS, XLSForm and QAF through `template_convert.qaf_to_draft`; since 2026-11-15 New Template > Issue form > From a SurveyJS or XLSForm file... is the door for files (`quill/ui/github_workbench_form_file.py`), and since 2026-11-16 Tools > Forms in both editors has Save As GitHub Issue Form and Open GitHub Issue Form (`quill/ui/forms_github_commands.py`), with `template_convert.qaf_to_draft` now `interop_github`'s export; inherited owner/.github rows and Organizations > org > Templates; the Template Chooser sheet (blank issues, contact links, order saved as numbered renames); New Pull Request offers the repository's pull request templates.)*
- [x] Save to branch or PR according to protection; conflict-check and verify contents. *(Done 2026-11-13: `quill/core/github/template_save.py`; a protected default branch, or the check box, saves to a new branch and opens a pull request; a changed sha stops the save; the file is read back.)*
- [x] Copy to Repositories with variant/missing previews and per-target results. *(Done 2026-11-13: one file, or, from the chooser row, the whole issue template set with its chooser; one result per repository.)*
- [x] Oversized/unreadable/unsupported templates offer an honest fallback without losing a draft. *(Done 2026-11-13: a form the builder cannot read opens as source with the reason; bad source YAML is kept; a failed save reopens the window with the draft.)*

### GH-C. Beyond parity — OPEN/AUDIT, Phase 13 and section 22

- [x] GitHub REST/GraphQL API Console with schema completion, permission/risk explanation, accessible result tree, Copy Value/Path, JSON export and saved commands. *(Done 2026-11-13: Tools > GitHub API Console, Ctrl+Shift+J; `core/github/api_console.py` completes from the vendored `quill/data/github_api/rest.json`, says the operation, tier and scope before sending; writes need Full access and the method typed, and go to Change History; saved commands per account. `ui/github_api_console.py`.)*
- [x] Read issue/PR/discussion as a structured document; preserve authors, dates, headings, code, links and export options. *(Done 2026-11-13: Read as Document..., Ctrl+Shift+I and the row menu; `core/github/thread_document.py` reads comments, reviews and line comments or a discussion with replies, a heading per post with author and date, bodies verbatim; Open in Editor in both editors, Save as Markdown or HTML.)*
- [x] Comment editors: mentions/references/emoji, saved replies, attachments, accessible Markdown preview and optional pre-post accessibility checks. *(Built 2026-11-17 for the Workbench's Comment...: `comment_compose.py`, `github_comment_composer.py`; tests `test_comment_compose.py`, `test_github_comment_composer.py`. Attachments have no GitHub API and are explained instead. 2026-11-18: discussion replies open it, and line comments and the review message have Comment Window... (`compose_with_provider`). Reply to Thread in the review window opens it too.)*
- [x] Watches using existing notification scheduling, consent/feedback settings and explicit freshness; never mark remote notifications read on load. *(Done 2026-11-13: the Watches node (Ctrl+7) lists runs, reviews, releases and comments rules per account (`core/github/watches.py`, `github_watches.json`); checked on the notification interval while the Workbench is open, after consent; rows say "checked 3 minutes ago"; Ctrl+N adds, Enter edits, Delete removes, Pause and Check Now on the row menu; never reads the inbox.)*
- [x] Editor commands: line permalink, blame/related PR, open line/PR, issue from selection, file mentions, comment on PR line and reference Properties. *(Done 2026-11-17: GitHub > From This Line in QUILL (and Tools > Git and GitHub > GitHub > From This Line), flat rows in QUILL Lite's GitHub menu, one table (`workbench_menu.LINE_ROWS`); `quill/core/github/editor_line.py` (permalink, blame sentence, issue draft, file search, open-PR query, line anchor, references in text) and `quill/ui/github_editor_line.py`; QUILL's adapter `main_frame_github_line.py`, QUILL Lite's `lite_github_line.py`. Who Changed This Line? is Local Git's blame command renamed and fixed (it always answered for line 1). The reference command is keyless and opens the item in the Workbench list narrowed to it: rule 1 gives Alt+Enter to Redo. Tests: `test_editor_line.py`, `test_github_editor_line.py`, `test_lite_github_line.py`. Not yet run against a live repository or with a screen reader.)*
- [x] CSV/Excel/Markdown/QUILL table export; previewed issue import; issues/sub-issues from document lines. *(Export done 2026-11-17: Export List... on the Workbench's File menu (Ctrl+Shift+X), shared with the WordPress Workbench through `quill/core/workbench/export.py`; tests `test_workbench_export.py`, `test_github_workbench_export.py`. Since 2026-11-17 too: Import Issues from a Spreadsheet... (Ctrl+Alt+I) and New Issues from Lines... (Ctrl+Alt+L), with sub-issues; `issue_import.py`, `github_workbench_import.py`; tests `test_issue_import.py`, `test_github_workbench_import.py`. Project fields are not mapped by the import yet.)*
- [ ] Plain-language query/batch commands through the shared catalogue, with resolved targets, editable previews and deterministic non-AI paths.
- [x] Dry Run across every write, practice repository creation/seeding/reset/cleanup and guided tutorials. *(2026-11-18: Dry Run at the three write doors (`dry_run.py`) and the practice repository, made, seeded, opened, started over and deleted (`practice_repository.py`). Six GitHub tutorials on the practice repository in QUILL (`github_lessons.py`); QUILL Lite's catalogue does not carry them yet.)*
- [ ] Compare Accounts and one-action Act As with unambiguous identity and cache isolation.
- [ ] Role comparison and learning workflows reach real permission evidence, not guessed privileges.

### GH-D. Fill the remaining GitHub feature families — OPEN/AUDIT

Reconcile these against actual code and the operation ledger. Some individual actions may already exist.

- [ ] Issue close reasons, development links, branch creation for an issue, task-list editing/conversion, organization issue fields. *(Done 2026-11-17 except organization issue fields: Close or Reopen asks the reason, duplicate included; Linked branches on the issue sheet; Create Branch for This Issue; Check or Uncheck a Task; Convert Tasks to Sub-issues. `issue_development.py`, `github_workbench_development.py`; tests `test_issue_development.py`, `test_github_workbench_development.py`. Unlinking a branch is not built.)*
- [ ] Saved replies, repository invitations, wiki and cross-linked discussion → issue → PR workflows. *(2026-11-18: saved replies insert in every comment box; repository invitations listed, accepted and declined (`repo_invitations.py`). Remaining: wiki, cross-linked workflows.)*
- [ ] Repository General/features, complete creation/template options, transfer, standalone tags, topics and star lists. *(2026-11-18: standalone tags made and deleted (`tags.py`).)*
- [ ] Rulesets/protection management, organization/member/team access, custom roles and audit logs.
- [ ] Webhooks and deliveries/redelivery/ping; deploy keys; autolinks; organization secret/variable repository selection.
- [ ] Account profile/status, SSH/GPG/signing keys, token-request administration, billing/usage and Sponsors where APIs permit. *(2026-11-18: status set and cleared (`user_status.py`).)*
- [ ] Workflow enable/disable and accessible workflow authoring; triggers/jobs/steps/inputs/permissions/dependency graph as linear controls. *(2026-11-18: enable and disable on the sheet and as Turn Workflow On or Off... (`workflow_state.py`). Remaining: authoring.)*
- [ ] Dependabot configuration and PR commands; CODEOWNERS editing/ownership lookup.
- [x] Merge conflict resolution in an isolated worktree; PR revert; exact patch review. *(2026-11-17: Resolve Conflicts in a Worktree..., Revert Pull Request... and Open Patch in Editor (`pull_tools.py`, `github_workbench_pull_tools.py`). Conflicts are QUILL's, which keeps local Git.)*
- [x] Review viewed/unviewed state, multiline/file comments, whitespace options, per-commit review, changed-since-review, suggestions and pending review drafts. *(2026-11-17: viewed and unviewed files, Show Only Files Not Viewed and file-level comments built (`review_viewed.py`, `github_pr_review_viewed.py`); multi-line comments, suggestions, changed-since-review and pending reviews were already there. 2026-11-18: Hide Whitespace Changes and Choose Commit... in the diff window (`commit_review.py`).)*
- [ ] Merge queue as a place; required policy explanation, auto-merge and batch merges of independently eligible PRs. *(2026-11-17: Repository > Merge Queue, Why Can't I Merge? with every blocker for the exact head commit, Merge merging only the commit it checked, Auto-Merge... and Add to or Remove from Merge Queue... on the row (`merge_readiness.py`, `merge_queue.py`, `github_workbench_merge.py`). Remaining: batch merges.)*
- [ ] Commit statuses, environments, deployment protection and release/deployment evidence. *(2026-11-18: Set Status... on a commit (`commit_status.py`).)*
- [ ] Packages, runners, dependency graph/SBOM, insights/network/traffic/contributions as readable tables. *(2026-11-18: Runners, read-only, and Export Software Bill of Materials... (`runners_sbom.py`); Commit Activity as tables (`repo_activity.py`); My Packages (`packages.py`).)*
- [ ] Git LFS storage/locks and account/organization export or migration capabilities with correct scope dispositions.
- [ ] Copilot sessions/review/configuration/organization administration and GitHub Models prompt/evaluation files, wherever actual APIs allow.
- [ ] Installed/authorized Apps, repository grants, install requests, suspend/unsuspend and OIDC subject templates.
- [ ] Code/secret scanning, advisories, private reports, bypass/dismissal requests, Autofix/dependency review and organization security overview.
- [ ] Discussion polls, spotlight and category sections.
- [ ] GitHub service status with opt-in network access and a useful explanation.
- [ ] gh sign-in reuse as an additional account path; enterprise hosts and API-version differences.
- [x] Inbox rules with preview; follow a live job log on request; changed-lines-only and optional diff sounds; named emoji. *(2026-11-18: Changed Lines Only and the added and removed line sounds built in the diff window; Follow This Job and Alt+8 in the jobs window, following steps because GitHub's REST log exists only once a job ends. Inbox rules built 2026-11-18 (`inbox_rules.py`, `github_workbench_inbox_rules.py`). Emoji shortcodes read by name in the details pane and Read as Document (`emoji_names.py`).)*
- [ ] Least-privilege advice based on observed usage with honest uncertainty; artifact attestations and immutable release evidence.

### GH-E. Across Repositories and Repository Sets — OPEN

- [ ] First-class by-name collections for every kind in PRD 22.11, not only items inside a repository. *(Partly, 2026-11-13: Labels, Milestones, Topics and Rules and Branch Protection by Name, and the Fleet, under Across Repositories; every other kind is a decided, test-backed cell with its reason in `quill/core/github/across_scope_matrix.py`.)*
- [x] GX16 category-first lists for Issues & PRs, Releases, Workflow Runs, Commits, Tags, Milestones, Discussions and Security Alerts over a local repository set, using the Workbench tree/list/details layout. *(Done 2026-11-13: the eight lists read the Repository Set in use. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Choose Repositories checklist is account-scoped; each row names its repository; Enter opens the exact source item and Back restores the same row, query, group and page. *(Done 2026-11-13: a real checklist (Space checks, Enter saves, Add takes owner/name and checks a listed one once) over the set's repositories and the 100 the account pushed to most recently; Enter opens the item in its own repository and Back lands on the same row, filter, grouping and pages. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Initial page and View More are bounded per repository; latest-release-only is explicit; sort/group and Next/Previous Repository retain stable identity. *(Done 2026-11-13: 30 first, View More from This Repository adds 30 up to 100; Every Release or Latest Only; View > Sort By and Group By Repository in the set's order; ] and [ in the list, and Next and Previous Repository on the row's menu. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Each repository's count, empty category, disabled feature, permission gap, partial page and error is represented honestly; no repository vanishes from the result without explanation. *(Done 2026-11-13: a repository with nothing to list keeps a row of its own saying why; the Items cell counts each state. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Category issue rows carry issue type and visible organization-defined issue fields with field ID, schema type and value; filters use the same typed value and report unavailable separately from empty. *(Done 2026-11-13: Read Issue Type and Fields, or a type: or field: filter; value, empty, unset, hidden, unsupported and unavailable are distinct. Not yet run against a live organization with issue fields: GitHub documents the payloads loosely. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Scopes: own/administered repositories, organization, every permitted repository, hand-made or filter-driven Repository Sets. *(Done 2026-11-13: named sets from a checklist, by a filter (org:name, user:login) or Every Repository I Can Reach, the 200 most recently pushed, saying when GitHub lists more. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Variants, Missing From, choose winning version, per-target permission/conflict preview and results. *(Done 2026-11-13 for labels, milestones, topics, rulesets and default-branch protection. Each target is re-read just before writing, so a changed copy is skipped, not overwritten; every change is in Change History, undoable through its Properties sheet where GitHub allows it. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Labels: rename/align/merge/relabel/copy/delete/find uses. *(Done 2026-11-13: Labels by Name. Merge relabels up to 300 items per repository and keeps the old label past that. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Milestones: align/close/migrate open work/create missing. *(Done 2026-11-13: Milestones by Name; Move Open Work To... moves each repository's open items to another milestone of its own, blocked where it has none. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [ ] Tags/releases/topics/branches: release trains, comparison, publishing, feature-specific safeguards. *(Partly, 2026-11-13: topics are added to the missing or removed everywhere, keeping each repository's other topics; tags, release trains and branch renames remain.)*
- [ ] Rules/protection/environments/secrets/variables/webhooks/keys/autolinks: align or promote to organization when actually supported. *(Partly, 2026-11-13: rulesets and default-branch protection align (who may push is never copied, protection is never removed this way), a ruleset is added where missing, and Promote to Organization makes one organization ruleset and deletes the copies only after it exists. Labels cannot be promoted: GitHub has no organization-label API. Environments, secrets, variables, webhooks, keys and autolinks remain, each classified in `quill/core/github/across_scope_matrix.py`.)*
- [ ] Workflow/template/community/Dependabot/CODEOWNERS content: compare and update through reviewable PRs.
- [ ] People/teams/settings/custom properties/issue types: access and setting matrices with inherited-role explanations.
- [ ] Saved replies/favorites/watch levels/stars, alerts/packages/Pages where supported.
- [x] Fleet view with exact revision/freshness; each failed or inaccessible repository remains visible. *(Done 2026-11-13: Across Repositories > Fleet. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [ ] Cross-repository coverage is complete only when the corresponding single-repository operation and batch behavior are complete; read-only category views are tracked separately from multi-target writes.

### GH-F. GX01–GX15 journey acceptance — AUDIT

The accepted roadmap table is reproduced in the coverage appendices. Close each row with a real journey, failure case and evidence:

- [ ] GX01 reference routing; GX02 attention queue; GX03 context-preserving navigation; GX04 CI diagnosis. *(2026-11-18: journeys, failure cases and test evidence in [docs/qa/github-journeys.md](./docs/qa/github-journeys.md). Open: a screen-reader pass of each. Writing GX04 down found a second Re-run Failed Jobs press sent a second request; fixed and tested.)*
- [ ] GX05 intake/triage; GX06 Projects/dependencies; GX07 local repository continuity; GX08 deep review. *(2026-11-18: the same document. Open: the screen-reader pass listed at its end.)*
- [ ] GX09 policy-aware merging; GX10 release/deployment evidence.
- [ ] GX11 security/dependencies; GX12 collaboration/knowledge; GX13 administration.
- [ ] GX14 workspace/service handoffs; GX15 optional grounded assistance; GX16 category-first cross-repository browsing.

### GH-G. Reference lessons and client boundary — ACCEPTED

- [x] Reviewed The Chat Place v0.5.0 release notes and source. Keep the notes in [github-roadmap.md](./docs/planning/github-roadmap.md).
- [ ] Apply provider-neutral patterns: read long issue/PR/discussion threads as one structured page; preserve the selected row on return; say the actual outcome once through QUILL's existing feedback settings.
- [x] Do not add Claude Code, Codex, Copilot or other third-party chat clients, CLI session readers, transcript parsers, subagent protocols or provider-specific file restore. Any future AI assistance uses QUILL's existing provider and consent boundary and remains optional.

## 7. WordPress delivery checklist

### WP-A. Shared frame, routing and parity — AUDIT

- [x] Validate W0–W6 against every WP-R Must and Appendix A/B object/window. *(Done 2026-11-13: `tests/unit/core/wordpress/test_wp_prd_must_ledger.py` maps all 33 WP-R Musts the PRD lists (it reads the PRD, so a new Must fails until it has a row) to where each lives and the tests that prove it, checks every cited test exists, and checks every Appendix A object has a Properties sheet and every Appendix B window a tree node. 32 are met over fakes. The one open row, WP-R-035 (QAF installed on the test site), is a write on the test host, waiting on Jeff. Closed in this pass: WP-R-024 (QUILL Lite's Tools > WordPress > Open WordPress Workbench already opened QUILL's own window through the shared command; now proven end to end in `tests/unit/apps/test_lite_wordpress_workbench_window.py`), WP-R-047 (every Settings row explains itself with the site's own value, `workbench_settings_help.py`, for example "News, so visitors see your latest posts at https://radio.example/news/"), and Appendix B's Visual Review as Visual Review... on post and page rows, running the editor's own review. Live runs are named per row: QAF spam, Redirection, By Name and Across Sites.)*
- [x] Give WordPress its own rebindable APP_KEYMAPS entry; reconcile shared keys/reserved chords. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Add This Post in the Workbench from the editor and Media Library picking mode for Insert Picture. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Cross-site Search runs through `wp/v2/search`, keeps site/type provenance, shows per-site failures and opens results in the browser.
- [x] Global Styles lists palette colours and font sizes, previews writes, checks for concurrent edits, verifies saves and records undo.
- [x] Needs My Attention > Accessibility lists pictures without alt text across connected sites, with each image's site shown.
- [x] Needs My Attention > Broken Links checks up to 40 unique links from the first published posts and pages using the site's URL-details route, and names any remaining scope.
- [x] Complete actual Workbench surfaces for Updates, Orders, Shop and Podcast where still placeholder/delegated; page-level axe findings stay in Check This Page. *(Done 2026-11-13: Shop and Shop Orders read WooCommerce's wc/v3 read only, Podcast lists the podcast type or episode posts, and a site without either is told so; Updates and Membership Orders load. No `planned:` node is left. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Preserve writing in the editor, drafts, revisions, custom-type opening and selection/context on return. *(Done 2026-11-13: two gaps fixed. Opening the Workbench again from the editor jumped to Needs My Attention; with no node asked for it now stays where it was left (`open_workbench`). Rebuilding the tree (discovery, coming back) fired a selection on another node, which cleared the filter and lost the row; the shared frame now ignores tree events while it rebuilds and keeps a node's rows when the same node is shown again (`quill/ui/workbench_frame.py`). A custom type opens under its REST base and saves back to it, a draft stays a draft, and the newer-autosave offer still stands. Tests: `tests/unit/ui/wordpress/test_wp_workbench_lockout_ui.py` (return keeps node, row and filter; custom type opens as `events`) and the ledger's custom-route test. S:\QUILL, uncommitted.)*
- [x] Verify Delete/Shift+Delete/Ctrl+Z apply to list objects only; text-editing controls retain ordinary editing behavior. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Ensure roles, users, application passwords, settings and plugins expose capability reasons, previews and self-lockout protection. *(Done 2026-11-13: refused with the reason, before any dialog: changing your own role (any role, not only Administrator) or removing yourself; a Role saved from your own Properties sheet (the same guard, `workbench_people.check_role_save`); revoking the application password QUILL signs in with, from the list, from a person's passwords and from Revoke Everywhere; deactivating the connection plugin; and the site address or an Administrator default role as settings. Previewed: Change Role (what the person gains and loses), every setting change, Revoke and plugin on/off. `workbench_permissions.py`; tests in `test_wp_workbench_lockout_and_stamp_core.py` and `test_wp_workbench_lockout_ui.py`. The Settings list does not show `url` or `default_role` today, so those two refusals guard any later door.)*

### WP-B. Discovery, content model and custom fields — OPEN/AUDIT

- [x] Discover taxonomy rest_base and supported types, all statuses, query enums and type-specific terms without guessing. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Complete New per custom type and status child nodes, plus lists, filters and batch for every supported custom type. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Expose registered meta on term, user and comment Properties sheets; scalar fields and safely typed scalar lists save through the site's route.
- [x] Edit schema-backed arrays, nested objects, repeaters, galleries and relationships in labelled JSON fields; coerce nested scalar types, enforce required/enum/size constraints and keep unknown keys. Unsupported schemas stay read only.
- [x] Give the seven historically planned plugin orderings spoken labels and eliminate combination-test gaps. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Content Model: actual registrant, types/taxonomies/field groups, read-only versus editable definition clearly distinguished. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Reconcile ACF read/write and other field-plugin promises with current integration scope; generic schemas remain accounted for. *(Done 2026-11-13: Advanced Custom Fields is read and written. Where the route's schema has an `acf` property, items, terms, users and comments get an Advanced Custom Fields page on Properties; a save goes back as `{"acf": ...}`, coerced against the schema, verified, and undone with Ctrl+Z (`field_plugins.py`, `workbench_edit.py`). Meta Box, Pods and CMB2 are classified in `field_plugins.FIELD_PLUGIN_SCOPE`: no adapter, their fields reached as registered meta, and `pods/v1` and `cmb2/v1` are deferred in the route coverage. Registered meta of every shape stays on the Meta and Custom Fields pages. ACF field-group definitions stay read only in wp-admin. Live check with ACF installed still to do.)*
- [x] Determine and record the QUILL Site Types dependency's delivery status; implement/create definitions, field kinds, accessibility kinds, site-defined kinds and Export as Code if retained. *(Done 2026-11-13 on the QUILL side. The plugin is `S:\code\quill-site-types` 0.1.0: one local commit, unpushed, tested only against its stand-in (`php tests/run.php`), never in a real WordPress. Against its contract (`quill-site-types/v1`), `quill/core/wordpress/site_types_plugin.py` and `quill/ui/wordpress_workbench_site_types.py` give Content Model: Define with QUILL Site Types... (Ctrl+N: a post type, a taxonomy, or a field group with `name: kind` fields checked against the site's kinds, the accessible ones included), Stop Defining... (content kept, Ctrl+Z defines it again), Export as Code (opened in the editor), Fields... (each field on its own sheet: kind, label, help, required, default and choices, or a new field; the whole group is sent, previewed, and Ctrl+Z puts it back) and Add a Field Kind... (a site-defined kind with how it is stored and a pattern; the plugin has no route to remove one, and the preview says so). Content Model lists what the plugin defines as editable, with its field groups. Coverage marks `quill-site-types/v1` covered. Tests: `test_wp_workbench_lockout_and_stamp_core.py` and `test_wp_workbench_lockout_ui.py`. Remaining outside this repository: install the plugin on the test site and run it live.)*
- [x] Verify schemas and permissions after plugin/theme/version changes; do not reuse stale capability claims. *(Done 2026-11-13: `workbench_site_stamp.py` stamps the WordPress version, namespaces, routes, plugins (where `activate_plugins`), the active theme (where `switch_themes`), your roles and capabilities. Every load past five minutes takes it again and always replaces the account and index; on any change the taxonomy and status cache is forgotten, types are discovered again, the tree rebuilt and the change said once. Turning a plugin on or off from the Workbench forgets the site's claims at once. Tests in both lockout test files.)*

### WP-C. QAF, Gravity Forms, membership and spam — OPEN/AUDIT/DEPENDENCY

- [ ] Confirm QAF namespace/name migration and compatible persisted form models across both repositories. *(2026-11-13: both halves are built and tested; what is left is the live run. QAF (S:\code\qaf, uncommitted): QAF_Migrator is now versioned (qaf_migration_version, steps 1 and 2, each once, under a lock) and runs early on plugins_loaded on any request, before the activator can make empty tables or a submission land in one. Step 1 renames tables, copies options, moves meta and adds role capabilities; step 2 moves baf_ cron events, rewrites wp:baf/ blocks and [baf_ shortcodes in posts and widget options (same length, so serialized values stay valid), turns a saved form's extensions.baf_legacy into qaf_legacy, and gives users their own qaf_ capabilities. baf/form renders as an alias, .baf files open, baf/v1 stays a read-only alias; README has the rollback steps. Tests: tests/unit/Model/RenameCompatTest.php (16). QUILL: qaf_site.site_namespace prefers qaf/v1 and falls back to baf/v1, and the Spam page and its commands say which the site runs (workbench_qaf_spam_edit.namespace_note). Open: deploy QAF to the test site, which still runs BAF, and check its forms, entries, pages and Forms node after the migration.)*
- [ ] Install supported QAF/Gravity Forms/PMPro versions on authorized test environments and record exact versions/capabilities. *(2026-11-13: needs an authorized test site with QAF, Gravity Forms 2.x with REST API v2 enabled, and PMPro 3.9+ on WordPress 6.9+, plus an account per role.)*
- [x] QAF type conversion preserves shared properties, rules and compatible choices/defaults, previews loss and refuses missing required setup. *(Done 2026-11-13: quill/core/forms/type_conversion.py had no tests; tests/unit/core/forms/test_forms_type_conversion.py (13) proves label, help, required, the field's own condition and validation are kept, single and multi-choice defaults carry over, lost choices and libraries are listed, starter and matching choices are made, and calculation, matrix, likert and repeater are refused until set up. Form Outline's confirm and refusal are tested in tests/unit/ui/forms.)*
- [x] Gravity Forms conversion reads/preserves the full form, validates concurrency, previews, checks gravityforms_create_form plus Full access and verifies the replacement. *(Done 2026-11-13: two gaps fixed. The permission check read gravityforms_create_form literally, so an administrator holding only gform_full_access was refused; it now uses gravity_can plus Full access (WorkbenchGravityCommands.gravity_conversion_refusal). The save trusted the PUT reply; it now reads the form back, and gravity_replacement_problems (workbench_forms.py) checks the new type and every other field, saying any difference while Ctrl+Z still restores. Tests: tests/unit/core/wordpress/test_wp_gravity_conversion_core.py and tests/unit/ui/wordpress/test_wp_gravity_conversion_ui.py, including a form changed during the preview, which is not overwritten.)*
- [x] Keep complex unsupported Gravity Forms field families untouched; define expansion through actual schema/API behavior. *(Done 2026-11-13: address and list fields are never offered, are refused if asked, and go back exactly as they came (tests above). The rule for adding a family is written at GRAVITY_FIELD_TYPES: only with a gf/v2 form recorded from a real site and a test converting it.)*
- [x] Verify duplicate/remove, conditions, repeaters, section/column structure, undo and error focus in form editing. *(Done 2026-11-13: two bugs fixed in quill/ui/forms_doc.py. Duplicating a repeater or section left the copy's conditions pointing at the original's questions; they now follow the copy. Removing a question that other conditions still named said nothing; it now says how many, and Check This Form's finding carries the question so Go to It lands there. tests/unit/ui/forms/test_forms_doc_structure.py (12) covers repeaters, columns, sections, rules, refused edits leaving the form unchanged, and one undo step per Outline edit.)*
- [ ] QAF spam dependencies: hold-never-drop, identical visitor confirmation, no behavioral rejection, reasons/provider reporting, blocklist/thresholds/question bank. *(2026-11-13: QAF's PHPUnit suite now runs (composer.json with PHPUnit 9.6 in S:\code\qaf; `vendor/bin/phpunit`, mbstring needed): 552 tests, 0 failures, from 509 with 95 errors and 16 failures before. tests/unit/Spam (122) proves all five, plus the new settings, question bank and weeks routes (SpamSettingsWriteTest.php). QUILL uses them: Spam and Not Spam go through entries/{id}/spam and /not-spam, and a held entry's row gives QAF's reason (tests/unit/core/wordpress/test_wp_qaf_spam_core.py). Open: a live submission on the test site once QAF is deployed there.)*
- [x] Implement Workbench Spam-page controls and the weekly Watch once QAF exposes the required contract. *(Done 2026-11-13: QAF now exposes POST qaf/v1/spam (only what is sent changes, if_revision conflict check, OOPSpam key write-only), spam/questions and spam/questions/{id}, and spam/weeks (13 weeks kept), all under manage_options or qaf_manage_settings, documented in its README. In QUILL the site's Properties > Spam page has every check, limit, the question mode and kinds, Send Anyway and a write-only key field, each with F1 help; OK previews the change, reads the settings again and sends nothing if they changed, then reads them back and says what the site holds. A baf/v1 site, an older QAF or a person without Manage Options sees them read only with the reason. Form Spam Questions... and Form Spam by Week are on the site's context menu (no key, reasons in workbench_qaf_spam_edit.KEYLESS), and Workbench Options has a Form spam weekly Watch. Code: quill/core/wordpress/workbench_qaf_spam_edit.py, quill/ui/wordpress_workbench_qaf_spam.py. Tests: tests/unit/core/wordpress/test_wp_qaf_spam_edit_core.py (12), tests/unit/ui/wordpress/test_wp_qaf_spam_ui.py (7). Still not on the REST API: the blocklist, which is WordPress's Disallowed Comment Keys. Not yet run against a live QAF.)*
- [ ] Reconcile text challenges, loose answer matching, Send Anyway and visitor help against QAF's own implementation/acceptance. *(2026-11-13: needs QAF's SpamTextChallengeTest.php run under PHP 8 with PHPUnit, and a screen-reader pass of a challenged submission on the test site; QUILL only reads the mode, the kinds and the Send Anyway count.)*
- [x] PMPro reads/writes use documented Abilities methods and bracketed query inputs; server permission callbacks remain authoritative. *(Done 2026-11-13: tests/unit/core/wordpress/test_wp_pmpro_membership_core.py proves a read-only query ability runs as GET with input[limit] and input[page], one not marked read-only is refused before any call, and a site's refusal of a change surfaces as an error. QUILL adds Full access on top and never decides a PMPro permission itself.)*
- [ ] Verify WP 6.9+/PMPro 3.9+ behavior and customized capabilities; no sensitive card/billing fields leak into lists. *(2026-11-13: the leak half is done. Every PMPro row, member read and subscription has card and billing fields stripped, nested or not (without_payment_details in workbench_pmpro_change.py), tested above. Open: needs WordPress 6.9+ with PMPro 3.9+ live, and a role with customized PMPro capabilities.)*
- [x] Membership cancellation preview states recurring-subscription/gateway consequences; Change/Cancel each require a per-run preview. *(Done 2026-11-13: Change and Cancel did not exist (their routes were classed wp-admin only). Users > person now has Change Membership Level... (write) and Cancel Membership... (destructive), through pmpro/v1/change_membership_level and cancel_membership_level. Each run reads the member and their subscriptions again and previews the subscription, gateway, amount and next payment that stop, that nothing is refunded, and that it cannot be undone. quill/core/wordpress/workbench_pmpro_change.py and quill/ui/wordpress_workbench_membership_commands.py; tests/unit/ui/wordpress/test_wp_pmpro_membership_ui.py. Live gateway acceptance stays with the Payment dependency line.)*
- [x] Distinguish PMPro membership orders from WooCommerce/shop orders throughout navigation and help. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10. WP-C added: an order row's detail now starts "Membership order", Memberships > Orders' help says these are not WooCommerce shop orders, and a test checks both sides of the help.)*
- [ ] Payment dependency: plugin tests, Stripe test mode, PayPal sandbox, webhook authenticity/replay/order, duplicate submission and accessible checkout acceptance. *(2026-11-13: needs QAF's and PMPro's PHP suites, a Stripe test-mode account, a PayPal sandbox and a reachable webhook endpoint on the test site.)*
- [x] Keep desktop authoring/reporting distinct from plugin-owned payment credentials, checkout and authoritative payment state. *(Done 2026-11-13: quill/core/forms/payment_site.py keeps only public configuration and drops anything else the server sends; the redaction gate strips payment keys; PMPro rows never carry card or billing fields; Change and Cancel leave checkout and the gateway to PMPro. tests/unit/core/forms/test_payment_site.py, tests/unit/stability/test_payment_key_redaction.py and test_wp_pmpro_membership_core.py pass.)*
- [x] Deferred form/membership plugins remain explicitly classified with generic discovery/admin routes; do not silently restore them as current commitments. *(Done 2026-11-13: workbench_coverage.py's _DEFERRED names MemberPress, Restrict Content Pro, WPForms, Ninja Forms, Formidable, Contact Form 7, Fluent Forms and Forminator. A readable route goes to More from This Site by namespace and any other to its own wp-admin screen, each labelled deferred and not a current commitment. Tested in test_wp_qaf_spam_core.py.)*

### WP-D. Practice Site and runtime — OPEN/DEPENDENCY

- [x] Verify the pinned @wp-playground/cli version, entry point and package license metadata against the staged package.
- [x] Add the CLI, PHP.wasm and WordPress core to build staging and both QUILL distribution paths.
- [ ] Include the workspace's untracked `scripts/wp_playground/package-lock.json` with the source change before release. *(Verified 2026-11-13: the lock matches package.json and the 3.1.64 pin, every package is registry-resolved with a sha512 hash, it is byte-identical to the staged cache's lock, and `_lock_matches_packages` makes the build use `npm ci` from it; `tests/unit/scripts/test_wp_playground_lock.py` keeps it so. Still untracked: it lands with the next commit.)*
- [x] Regenerate and parity-check the third-party notices from the updated component catalogue. *(Done 2026-11-13: `build_third_party_notices --write` regenerated five drifted files, `--check` passes on all 25; the staged CLI, @php-wasm/node-8-3 and WordPress 7.1.4 versions and licences match the catalogue; `collect_copyleft_sources.py` now names the source for all three GPL components, tested.)*
- [x] Stage the WordPress/PHP/WebAssembly payloads so the Practice Site first launch needs no WordPress download.
- [ ] Run start/connect/reset/stop/restart using the bundled Node and payloads on a clean installation. *(Source run done 2026-11-13 with the staged Node 24.22.1, CLI 3.1.64, PHP 8.3 and WordPress 7.1.4, from an empty data folder: first start 111-168 s, restart 46 s, stop, Workbench close, reset and start-after-reset all pass. It found and fixed three blockers: Playground listened on every interface, `--login` answered every REST call with a 302, and WordPress refused the app password over HTTP. Still open: the same run from an installed build.)*
- [x] Verify blueprint starter content and actual application-password handoff to Credential Manager. *(Done 2026-11-13, live: the welcome page, first post and draft exist; the one-time password reached Credential Manager, the handoff file was removed, and the stored password signed in as administrator; reset removed it again. No password was printed.)*
- [x] Resolve the loopback HTTP exception narrowly for the local Practice Site while retaining HTTPS requirements for remote sites; verify client policy accepts the intended route. *(Done 2026-11-13: `workbench_practice.is_practice_address` allows plain HTTP only to 127.0.0.1, localhost or ::1 on port 9400; `api.check_address` and `media_play.stream_problem` use it, so other loopback ports, `.test`/`.localhost` names and LAN addresses need HTTPS. Tested both sides, and the live client connected.)*
- [x] Bind locally, isolate credentials/data, handle occupied ports and failed startup, avoid orphan processes and make reset consequences clear. *(Done 2026-11-13: a `--require` preload pins every Node listen to 127.0.0.1 (live: LAN address unreachable); an occupied port is refused before spawning; a failed start says what Playground printed and stops it; the server is in a kill-on-close job, stop uses `taskkill /T` plus the job, and the pipes are drained; only the handoff folder is mounted, its password removed after Credential Manager takes it; Reset's confirmation names every consequence. Each has a test in `test_wp_practice_site.py`.)*
- [x] Use the practice site for realistic integration and accessibility tutorials; prove no accidental publication to a real site. *(Done 2026-11-13: a new QUILL tutorial track, "The WordPress Workbench, on the Practice Site", has three lessons in `quill/core/tutorials/wordpress_practice_lessons.py`: start and connect, change a post with Change History and undo, and reset. `practice_only_problems` keeps them off every other site and every command that sends work elsewhere; `docs/user guide/tutorials.md` is regenerated. Copy to Site and Make Them the Same now ask by name, defaulting to No, before practice work goes to a real site. The Workbench labels a practice profile as practice in every row, preview and status line. Tests: `tests/unit/ui/wordpress/test_wp_practice_crossing.py`, `tests/unit/core/test_wordpress_practice_lessons.py`. Not yet taken live with a screen reader.)*

### WP-E. W7 bold workflows — OPEN/AUDIT

- [x] Copy to Site for posts/pages/media/menus/terms/forms/patterns: author mapping, name matching, uploaded media, rewritten internal links and explicit create/replace previews. *(Done 2026-11-13: `workbench_site_copy.py`; exact slug match then name for terms/menus, replace keeps the target's status, authors by username/name, files uploaded with alt/caption or reused, featured images, links in both schemes and block attributes, menus with their links; offered on media and menu rows too. Gravity Forms forms copy whole from `gf/v2/forms/<id>` (POST new, PUT same title), entries never read or sent. Not yet run against a live pair of sites.)*
- [x] Compare Sites and snapshots: completeness, omissions, restore/rollback contract, revisions and media handling are stated. *(Done 2026-11-13: `workbench_snapshot.py`; Compare covers posts, pages, patterns, categories, tags and menus and names what it omits, unreadable kinds and the bound; snapshots record unread parts and take media files only when asked; new Site > Put Back from a Snapshot (Ctrl+Alt+Shift+S) previews under RESTORE_TERMS.)*
- [x] Calendar: all sites/types, timezone/DST ambiguity and schedule previews; editable list equivalent. *(Done 2026-11-13: every site and each site's discovered types, failures shown as rows; `workbench_editorial.site_moment` refuses skipped times and asks first/second for repeated ones; new Item > Move to Another Day (Ctrl+Alt+Shift+D) previews in the site's time and yours. Custom types join once the site's types are discovered.)*
- [x] Editorial queue: reviewer, notes, send back, approve/schedule, contributor ownership and notification semantics. *(Done 2026-11-13: `wordpress_workbench_bold_queue.py`; reviewer chosen from the site's editors, note plus a local record and a Review Watch; approve/schedule on the site's clock with preview; Pending Review shows a Queue column ("2 of 5 waiting"); every outcome says WordPress sends no email.)*
- [x] Read Site as Document: menu/category scope, order, address/provenance, private content, bounded loading and export fidelity. *(Done 2026-11-13: `workbench_read_site.py`; whole site, one menu or one category; published only, protected pages counted out, 500-item bound stated, a header with address/scope/date, page headings nested and lists/links/alt text kept through html_to_markdown.)*
- [x] Watches: off until enabled, no duplicate chatter, first sample silent, site-answering no faster than 15 minutes, consent and explicit offline/stale state. *(Done 2026-11-13: first sample silent per site and per Watch; round claimed before it runs so two editors do not both speak; new site_down and review Watches; the Watches node shows last round, staleness and each site's answering state; a `health` Watch says a Site Health test whose status changed, per test, silent for non-administrators.)*
- [x] REST Console: real discovery/completion, capability/argument/result schemas, all write previews and Change History. *(Done 2026-11-13: reads the full index, completes as `wp/v2/posts/{id}` templates filled from parameters, Accepts box per method, required/unknown/enum checks in the write preview, What It Returns from OPTIONS; Save Request keeps a request (`workbench_rest_saved.py`, atomic, persistence entry) as a Tools > Saved Requests row (1 to 9), Run a Saved Request (Ctrl+Alt+Q), Forget a Saved Request (Ctrl+Alt+Shift+F). The capability line is still QUILL's table for core routes, since the index does not publish capabilities.)*
- [x] Export all promised formats, import spreadsheets and document folders as drafts, mapping previews and per-row results. *(Done 2026-11-13: CSV, Excel and Markdown table (the QUILL table); spreadsheet columns mapped with synonyms and the mapping previewed, publish/future rows made drafts; new Edit > Import a Folder of Documents (Ctrl+Alt+Shift+I) for Markdown, text and Word; a report line per row or file.)*
- [x] Optional plain-language batches resolve exact sites/targets and use the same permission/conflict/batch engine. *(Done 2026-11-13: Tools > Plain-Language Batch (Ctrl+Alt+B), `workbench_plain_batch.py`; a fixed non-AI grammar (status moves; add or remove a tag; by author, in category, on named sites or every site), exact-name resolution with no guessing, an editable checklist of the exact items, then write_refusal per site, check_conflict per item and run_batch. The AI command catalogue is not wired in: no Workbench-facing consent path exists for it, so the grammar is the whole path.)*

### WP-F. By Name, Across Sites, Site Sets and Fleet — OPEN/AUDIT

- [x] Complete by-name **operations**, beyond listing: rename, split, merge, reassign, replace and find uses.
- [x] Terms/custom terms, custom field values, authors, media, patterns/parts, links, blocks/shortcodes and forms each have a usable place.
- [x] Across Sites scopes and Site Sets; Variants/Missing From and winning-version previews with per-site outcomes.
- [x] Complete Make Them the Same for themes, people and menus; install plugins on missing sites; compare global styles.
- [x] Cover terms, plugins, themes, people, settings, menus/navigation, patterns/starter pages/forms/content types and role-pages.
- [x] Account for redirects, application passwords and spam senders across sites where APIs permit.
- [x] Fleet health/backups/security/updates preserve unavailable, unknown and stale states per site.
- [x] Promote to Network only on actual supported network APIs with correct super-admin permission and consequences.
- [x] Classify every kind × site/site-set/all-sites/network × operation combination.

### WP-G. Site administration sweep — OPEN/AUDIT, scope reconciliation required

- [ ] Redirects: verify the existing slug-change offer live; classify redirect lists/edit/test/404-log operations. *(Partly 2026-11-13: Sites > site > Redirects and 404 Log list, add (Ctrl+N), change, turn on/off, delete and test through `redirection/v1`; the slug-change offer path is verified in code and by a test; routes classified covered. Live check against a Redirection install remains; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [ ] Backups, restores, security/sign-ins/2FA/vulnerability data, caching/performance, multilingual content, consent, email, newsletters, courses, event attendance, analytics and social sharing: account for discovered APIs, and separately decide first-class integration priority. *(Partly 2026-11-13: each is a `THIRD_SWEEP` row with a disposition per site (discovered namespace -> More from This Site, else Open in Dashboard) and the Administration Areas node; the first-class priority decision remains Jeff's; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Core plugin search/install/update and abandoned-plugin information include consented directory calls, readable details and rollback/recovery limits. *(Done 2026-11-13: `dotorg.py` asks plugins/info/1.2 (query_plugins, plugin_information, a closed plugin read from its 404) after a consent naming the host and what is sent; Check on WordPress.org and Find a Plugin on WordPress.org on plugin rows say rating, installs, last updated, tested up to and needs, warn on closed or over-two-years-stale plugins, add that to each plugin row and to Install on Sites Missing It's preview; install is `wp/v2/plugins`, inactive, previewed with the update limit and `PLUGIN_RECOVERY` (no rollback; deactivate or delete); egress row updated; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Privacy export/erase requests have exact admin pointers where no API exists; never claim a desktop completion that only opened wp-admin. *(Done 2026-11-13: export-personal-data.php / erase-personal-data.php, or tools.php?page=export_personal_data / remove_personal_data before WordPress 5.3; opening says QUILL cannot see whether requests were done; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Shop/catalog/orders/customers/coupons/reports/settings, events and SEO: reconcile historical parity-package promises against current plugin scope. *(Done 2026-11-13: `THIRD_SWEEP` rows for shop, event attendance and SEO state the historical promises are not current scope and give the generic-route or Dashboard boundary; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Complete Content Audit and Media Housekeeping: orphaned/stale/duplicate content, reading/heading measures, unused/duplicate/large media, captions/transcripts and usage before deletion. *(Done 2026-11-13: duplicate text, Flesch-Kincaid reading level and uploaded-twice media added; Show Where It Is Used and a usage preview before Move to Trash, which never force-deletes media; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Search/sitemaps/index visibility, overdue scheduled tasks, SSL expiry and editing locks carry honest data-source limitations. *(Done 2026-11-13: Sites > site > Search and Upkeep, each row ending with where its answer comes from; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Import/export/archive workflows preserve media/link mapping and make omissions explicit. *(Done 2026-11-13: `workbench_carry.py`: Import a Folder of Documents uploads pictures beside each file once and rewrites their links, points links between the files at their drafts, and lists missing, outside-host and Word pictures, unimported links and front matter; Import Posts, Export List, Take a Snapshot (`left_out` in snapshot.json), Copy to Site (preview and report, private-to-draft and plugin blocks) and Download My Writing each end with what they left out; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] User sessions, others' application passwords, spreadsheet invitations, sign-out-everywhere and role definitions: use APIs where offered; state admin-only limits. *(Done 2026-11-13: others' passwords via wp/v2/users/{id}/application-passwords behind edit_users; sessions and sign-out-everywhere stated as not in core REST and opened in wp-admin; CSV invites as a previewed batch of POST wp/v2/users; roles stay read only with the reason. S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Document the exact supported boundary of every third-sweep row rather than dropping it when a bespoke plugin adapter is deferred. *(Done 2026-11-13: `workbench_coverage.THIRD_SWEEP` and `sweep_disposition`, asserted by `test_wp_workbench_sweep_core.py`; memberships, plugins, people, roles and import/export are recorded with their own nodes; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*

## 8. Shared accessibility, help and reliability acceptance

### Native interaction and assistive technology

- [ ] Validate tree semantics and usability before treating wx.TreeCtrl as accepted: node name, level, position, expansion, loading, selection and empty/error states.
- [ ] F6 traverses panes/status predictably; Tab order follows reading order; no keyboard traps.
- [ ] Menus/context menus/default actions and Properties are discoverable by keyboard; typing navigates without being consumed by action shortcuts.
- [ ] Preserve exact row/thread/diff location after refresh, nested dialogs, browser handoff and Back/Forward.
- [ ] Keep focus stable during background loading; announce completed work once through the existing feedback contract.
- [ ] Avoid duplicate speech from window titles, focus events and explicit announcements; expose full detail on request.
- [ ] Every input has a persistent visible/programmatic label; names, descriptions, errors and read-only reasons work with platform accessibility APIs.
- [ ] Modal sheets focus inside, place Close/Cancel predictably, close on Escape where specified and restore trigger focus.
- [ ] Errors focus the first invalid field or summary and retain drafts; batch errors support Retry Failed without replaying successes.
- [ ] Verify high contrast, contrast ratios, visible focus, large text/scaling, long labels and narrow windows; meaning never depends on color, hover or sound.
- [ ] NVDA, JAWS and Narrator; braille including 40-cell rows; relevant macOS VoiceOver behavior where the product ships.
- [ ] Apply WCAG 2.2 AA to all web/help/exported HTML; native controls require their own platform/manual acceptance.
- [ ] Record every manual result with build SHA, app, OS, assistive tool/version, task, expected/observed behavior and issue link.

### Help and learning

- [ ] GH/WP help gates at zero for nodes, rows, controls, fields, actions and result explanations.
- [ ] Shared Part D D1–D20 help features apply to both providers, not only GitHub.
- [ ] Glossaries, Search Help, What Can I Do Here?, Do Something tasks, situation-aware explanations, printable/exportable help and Ask a Person.
- [ ] WordPress “How WordPress Thinks,” settings explanations using actual site examples, plugin-deactivation/update/deletion explanations and visitor-facing form help.
- [ ] Practice tutorials, first-week path and Break It on Purpose with safe recovery.
- [ ] Optional Ask the Workbench remains grounded in selected evidence, editable and consent-bound.
- [ ] Update GitHub/WordPress manuals, both editor guides, window reference, tutorials, keys, release notes and changelogs together.
- [ ] Generate HTML/EPUB with the accessible template, unique titles/language/landmarks/table semantics and correct links; sync installed/site copies.

### Data, network and operations

- [ ] Pagination/lazy loading, explicit truncation, bounded caches, cancellation, retries and selection preservation on large accounts/sites.
- [ ] Distinguish loaded-row counts from server totals; partial failures never appear as zero results.
- [ ] Credentials isolated by host/account/site, stored in supported secret stores; write-only values never enter speech/logs/history/export.
- [ ] Private draft/navigation/history retention, migration, cleanup and account removal behavior documented and audited.
- [ ] Conflict checks and post-write verification use current remote state; undo is offered only where it can actually restore the change.
- [ ] Ambiguous timeouts require reconciliation, not blind replay of non-idempotent writes.
- [ ] Every remote target/redirect/media fetch stays inside the intended authenticated origin rules; consented extra services are in the egress audit.
- [ ] No background refresh marks GitHub notifications read or changes WordPress content.
- [ ] Frozen preview targets cannot expand silently when a saved filter or server state changes.
- [ ] Server permission checks remain authoritative even when locally cached permission UI is optimistic.

## 9. Live validation and external dependencies

- [ ] GitHub live scenarios: multiple roles/accounts, protected branches, organization restrictions, rate limiting, private repositories, project fields, secrets, failure/retry and no-API fallbacks.
- [ ] WordPress current candidate: run the documented live regression on an authorized test site and distinguish existing site-side failures from regressions.
- [ ] Seed QAF, Gravity Forms, PMPro, custom types/taxonomies/meta, constrained roles and realistic media/content for the supported scope.
- [ ] Verify taxonomy discovery, nested fields, block notes, upload/chunking/regenerate sizes, media listening/watching and contributor restrictions where still unverified.
- [ ] Reconcile “90 pass / 4 site-side fail” from earlier branches with fresh final-candidate results; do not inherit old green evidence.
- [ ] WordPress.com onboarding: confirm application/client registration and the current OAuth path if still incomplete.
- [ ] Audit external QAF/BAF/Site Types branches, names, release state and dependency contracts before relying on historical “waiting on Jeff” notes.
- [ ] Verify packaged app behavior, not only source runs; include clean/offline Practice Site launch.
- [ ] Manual acceptance stays separately signed off by the user/testers; every blocked scenario names the missing environment or permission.

## 10. Bold design recommendations — PROPOSALS

These extend or sharpen the accepted design. Evaluate with users before adding to committed delivery scope. Several build on existing PRD ideas; their added value is the acceptance contract below.

| ID | Proposal | Delight and acceptance |
| --- | --- | --- |
| UX-01 | A task-first Start/Resume page over the complete object tree | “Review my oldest request,” “fix missing alt text,” “schedule next week.” Each card opens the exact scope and explains prerequisites; experienced users keep direct navigation. |
| UX-02 | A persistent Workbench Activity Center | One place for running work, results, partial failures and undo; resume after restart, inspect provenance, retry failed targets only. No modal cascade or stolen focus. |
| UX-03 | Preview as a navigable before/after document | Read changes by target, field and consequence; filter risky changes, compare variants, exclude individual targets and export the plan. Revalidation reports drift before execution. |
| UX-04 | An evidence ribbon on every important conclusion | On request: source, host/site, role, SHA/version, timestamp, completeness and why it is believed. “Ready to merge” and “site healthy” can never outlive their evidence. |
| UX-05 | Context bookmarks richer than saved searches | Save exact filter/sort/columns, item/thread/line, account and draft; reopen offline with clear stale labels, then reconcile live without losing place. |
| UX-06 | A unified What Changed Since I Was Here view | Group meaningful changes, suppress noise by user rules and let users jump to exact evidence. Reading the digest never marks remote notifications done. |
| UX-07 | A cross-site/repository rehearsal mode | Dry Run plus realistic local/sandbox fixtures, explain each capability and show reversible/irreversible outcomes. No promise that every API write is undoable. |
| UX-08 | An accessible impact explorer | Before removing a plugin, role, label, field, media item or template, list dependent objects, broken workflows and alternatives in a linear outline; unknown impact stays explicit. |
| UX-09 | A capability explorer that teaches the API through tasks | Search “who can publish?” rather than a route name; show native workflow, advanced operation, permissions and admin fallback. Unsupported operations remain findable. |
| UX-10 | A permission repair assistant | Explain the smallest role/scope change with before/after effects, account/site alternatives and request-access draft; never grant or elevate automatically. |
| UX-11 | A recovery notebook for multi-target operations | Keep target-by-target verified results, uncertain outcomes and recovery steps. Continue a stopped batch with idempotency/reconciliation controls. |
| UX-12 | Personal speech and braille layouts | Per-kind row templates, terse/expanded reading, speak-changes-only and preview of spoken output; full information remains reachable and defaults work without setup. |
| UX-13 | A quiet interaction mode | Pause nonessential updates, queue summaries and preserve urgent explicit failures. Configurable per Workbench with no suppression of completion/error evidence. |
| UX-14 | Native accessibility coach for things people publish | Check GitHub Markdown and WordPress content/forms before posting; jump to exact issue, explain a fix, preview it and respect an informed decision to continue. |
| UX-15 | A timeline that joins work across services | Issue → PR → run → release → WordPress announcement, with explicit links/provenance and optional prepared drafts. No cross-service publishing occurs automatically. |
| UX-16 | Reusable operational recipes | Save a reviewed sequence such as release train or staging-to-live promotion; parameterize scope, explain every step and revalidate permissions/targets on each run. |
| UX-17 | A drift studio | Compare desired labels/rules/templates/settings against actual copies; review exceptions and decide whether to align, preserve or document a difference. No background enforcement by default. |
| UX-18 | A semantic review reader | Read changes by symbol, heading or content block with exact line/patch provenance; toggle raw diff any time, never let AI summaries replace authoritative changes. |
| UX-19 | A form conversion laboratory | Preview control changes with real sample data and keyboard/screen-reader walkthrough, trace affected rules/defaults/payments, and show reversibility before conversion. |
| UX-20 | A publishing time machine | Compare a site/document snapshot with today, read semantic changes and restore selected supported pieces with conflicts/previews; state which media/settings cannot be restored. |
| UX-21 | Local-first draft continuity | Recover issue/comments/reviews/form/content drafts across interrupted connections; identify target-account drift and require an explicit send after reconnect. |
| UX-22 | A human-readable automation builder | Build event → conditions → proposed action as labelled rows, simulate against historical examples, show permission/cost/notification effects; begin with notifications/drafts rather than autonomous writes. |
| UX-23 | A feature-completeness browser for Jeff and users | Search all API capabilities, filter by native/schema/console/planned/admin-only and inspect exact limitation. Generate engineering backlog and public feature truth from one source. |
| UX-24 | A Workbench usability scorecard | Measure time, wrong turns, focus loss, speech duplication and task success with new/experienced users. Prioritize friction reduction alongside route coverage. |

- [ ] Rank proposals by user benefit, shared reuse, evidence and implementation cost.
- [ ] Prototype the highest-value proposals in the existing frame before adding new windows.
- [ ] Keep complete keyboard/list alternatives to every visual graph/calendar/matrix.
- [ ] Give each accepted proposal a requirement ID, owner, dependency, acceptance journey and release boundary.
- [ ] Do not delay known regression/accessibility fixes while exploring proposals.

## 10A. AI Workbenches and bring your own ChatGPT plan — PROPOSALS

**Added:** 2026-11-10, at Jeff's request to think more boldly about AI and a person's own ChatGPT subscription.  
**Status:** Product/design proposals plus an audit of existing foundations. These are not implementation or acceptance claims.

### 10A.1 The bigger product idea

A person should be able to bring an outcome: “Get this release ready and prepare the announcement,” “Build our volunteer application process,” or “Show me what went wrong while I was away.” The Workbench gathers evidence, creates an understandable plan, prepares changes in the right native places, and helps finish each authorized step.

The result should be a durable **mission**: a named outcome with its evidence, editable plan, prepared artifacts, current step, decisions and verified results. A mission can span repositories and sites. It can be paused, inspected without AI, resumed and handed back to the person at any point.

A ChatGPT subscription supplies an eligible intelligence connection. QUILL supplies the accessible workspace, reliable tools, local context, deterministic permissions, previews, history and recovery. Every mission continues to have a useful keyboard-operated interface.

**Three simple ways to ask**

| Mode | What the person means | What the Workbench produces |
| --- | --- | --- |
| Explain | “Help me understand this.” | An evidence-linked answer, with a short version first and detail on request |
| Prepare | “Make a version I can review.” | Drafts, patches, mappings, forms, schedules or a frozen change plan, with no remote publication |
| Do | “Carry out this defined task.” | Execution within the person's authorized targets/actions, live progress, verified outcomes and remaining work |

Do not add an approval dialog for every harmless read or every sentence of a draft. The user should approve a concrete change plan at meaningful boundaries. Material target, account, consequence or scope changes invalidate the affected authorization.

### 10A.2 What bringing a ChatGPT subscription can mean

**Official documentation checked on 2026-11-10.** OpenAI currently documents a Sign in with ChatGPT path for eligible Plus/Pro subscribers to authorize eligible AI requests in participating open-source/local tools, without configuring an API key. It separates identity from permission to use the plan. QUILL must establish its actual integration eligibility and the user's granted capabilities. Sign-in does not give QUILL access to the person's ChatGPT conversation history. [Sign in with ChatGPT quickstart](https://developers.openai.com/siwc/quickstart), [open-source plan usage](https://developers.openai.com/siwc/token-sharing-open-source).

| Path | Experience to design | What needs proving |
| --- | --- | --- |
| Native QUILL using My ChatGPT plan | Continue with ChatGPT, choose an available model, use Ask and supported task features in the native Workbench | Current eligibility, scopes, account/workspace separation, limits, capability contract and completion/error handling |
| QUILL Workbench tools exposed to ChatGPT | A person asks from ChatGPT and invokes an authenticated QUILL plugin/MCP tool surface; plans/results open in the native Workbench | Supported host/transport, connection permissions, local versus remote availability, secure setup and deep-link/context handoff |
| Codex task engine inside QUILL | Reuse the accepted Codex-for-tasks connection for multi-step Workbench tool use on an authorized ChatGPT plan | Packaged engine readiness, version/protocol maturity, client-executed tools, approvals, cancellation and session recovery |
| User's own API connection | Explicit separately configured API account/project for capabilities or deployment paths the plan route does not offer | Capability discovery, provider consent, usage controls and billing identity |
| Existing QUILL/free/local options | A useful fallback the user deliberately chooses, with truthful feature availability | Same action/preview contracts; no hidden switch of provider, data destination or billing path |

An MCP-backed ChatGPT integration can expose tools and optionally a UI; it is a separate surface from native plan-powered inference. Plan/workspace permissions and actual host support determine availability. A VS Code MCP entry does not itself install or authorize a connection in ChatGPT. [MCP server and UI quickstart](https://developers.openai.com/plugins/build/app-quickstart), [custom MCP connections](https://developers.openai.com/api/docs/guides/custom-mcp-server).

Some eligible Pro/Business subscriptions currently have a separate claimable API-credit benefit linked to an owned API organization. This remains a distinct billing path with eligibility and expiration rules. Do not market every ChatGPT subscription as unlimited API usage or silently consume a different balance. [API-credit benefit](https://developers.openai.com/api/docs/guides/chatgpt-api-credits).

**Product recommendation:** make My ChatGPT plan a first-class path through the existing Choose Your AI experience. Give the user a clear task capability description and a direct route to usage/account management. Keep GitHub, WordPress and AI identities separately named.

### 10A.3 Reuse the AI system that is already here — AUDIT

The source tree already contains relevant foundations. Their existence is not proof that Workbench missions are wired or accepted.

| Existing source | Reuse opportunity / acceptance gap |
| --- | --- |
| [AI family design](./docs/design/codex.md), especially 10A–10E | Accepted Choose Your AI, Ask, capabilities, task engines, parity and per-app connection decisions |
| [ChatGPT account](./quill/core/ai/chatgpt_account.py), [state](./quill/core/ai/chatgpt_state.py) | Existing dynamic sign-in, host/client identity and credential lifecycle; audit against current official contracts |
| [ChatGPT client](./quill/core/ai/chatgpt_client.py), [HTTP transport](./quill/core/ai/chatgpt_http.py), [errors](./quill/core/ai/chatgpt_errors.py) | Model discovery, streaming and typed failure handling; Workbench tasks need the same reliable terminal-state contract |
| [Local usage counts](./quill/core/ai/chatgpt_usage.py) | Show locally observed usage without inventing provider allowance/reset figures |
| [Connection capabilities](./quill/core/ai/connection_caps.py), [engine selection](./quill/core/ai/engines.py) | Gate features by actual connection/model/engine. Current source distinguishes plain ChatGPT Ask from agent-tool-capable routes; audit readiness rather than assuming sign-in enables every tool |
| [App task runner](./quill/core/ai/app_task.py), [family tools](./quill/core/ai/family_tools.py) | Register Workbench tools and derive completion summaries from actual recorded calls |
| [Approval layer](./quill/core/ai/approvals.py), [permissions](./quill/core/ai/permissions.py) | One task authorization and native preview policy across engines |
| [Native tool loop](./quill/core/ai/tool_loop.py), [Codex app-server integration](./quill/core/ai/codex_app_server.py) | Multi-step orchestration with cancellation, normalized events and controlled tools |
| [AI Gateway history](./docs/planning/openai.md), [current Gateway specification](./docs/Product%20Requirement%20Documents%20and%20Specifications/quill-ai-gateway-spec.md) | Distinguish a shared-service route from direct personal-plan and own-key routes; reconcile older gateway-only architecture language |

- [ ] AI-FOUND-01 Map each proposed Workbench workflow to existing Ask/task/connection/permission components before creating new infrastructure.
- [ ] AI-FOUND-02 Audit which engines are actually available in packaged QUILL and Lite. An unavailable capability record or present source module is not a shipped feature.
- [ ] AI-FOUND-03 Reconcile current sign-in implementation with current official identity validation guidance; document and resolve any difference, including signature-validation requirements.
- [ ] AI-FOUND-04 Correct overbroad privacy/cost wording if present. Request storage settings alone do not prove zero provider retention; a subscription does not imply unlimited allowance.
- [ ] AI-FOUND-05 Extend the accepted AI design and Workbench PRDs with accepted proposals rather than creating a competing architecture.
- [ ] AI-FOUND-06 Keep per-app sign-in/revocation behavior and existing shared-family choices consistent with the accepted design.

### 10A.4 Platform capability boundaries that shape the design

The currently documented direct ChatGPT-plan route uses streamed Responses requests with storage disabled, client-supplied context/history, and explicit terminal success/failure handling. Query current account models and do not treat a model catalogue as proof that a request is authorized. [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).

Its preview supports client function/custom tools subject to the documented format. Hosted MCP/connectors, image-generation tools, file search, Code Interpreter, native computer use and audio/transcription are not supported on that direct route; image/file inputs depend on the model. Local tool execution is distinct from hosted tools. Therefore voice, image creation, browser tasks and long-running hosting require their own verified execution/capability path. [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations).

- [ ] AI-CONN-01 Implement/verify the documented public-client browser authorization, stable host ID, persisted issued client registration, granted-scope checks and protected per-account refresh.
- [ ] AI-CONN-02 Represent signed in, plan permission declined, unavailable feature, quota reached, revoked connection and interrupted answer as distinct user states.
- [ ] AI-CONN-03 Resume native task state after sign-in renewal without automatically replaying a remote write.
- [ ] AI-CONN-04 Preserve drafts and verified progress when allowance expires mid-mission; offer pause or an explicit connection choice.
- [ ] AI-CONN-05 Implement model/capability discovery per selected account and respect organization policy.
- [ ] AI-CONN-06 Explain who receives selected private content and how local mission history is retained, exported and removed.
- [ ] AI-CONN-07 Never make a hosted/scheduled worker depend on somebody leaving the desktop open without explaining that dependency.
- [ ] AI-CONN-08 Re-check published platform contracts before implementation/release; record the supported version/date and current limitations.
- [ ] AI-CONN-09 Treat pasted browser cookies, private ChatGPT endpoints or credentials copied from another app as unsupported integration methods.
- [ ] AI-CONN-10 Treat optional separately billed tools as explicit capabilities and explicit choices, with no surprise billing fallback.

### 10A.5 Bold GitHub missions

Each entry below is a proposal with an observable finish, not an assertion that AI can guarantee correctness.

| ID | Person's request | Ambitious experience | Acceptance |
| --- | --- | --- | --- |
| AI-GH-01 | “Get me ready to release.” | Assemble a release room: open blockers, changed APIs, exact checks/reviews, docs gaps, artifacts, draft notes and a suggested order | Every blocker cites current evidence; release/publish remains an explicit step; changed HEAD invalidates affected readiness |
| AI-GH-02 | “Understand this problem and prepare a fix.” | Read issue/history/code, propose hypotheses, reproduce in an isolated worktree, prepare a patch and a PR draft | Separate observed reproduction from hypotheses; preserve edits; report exact checks actually run and unresolved risks |
| AI-GH-03 | “Review this PR with me.” | A guided review by symbol and behavior, linking issue intent, changed lines, tests and previous discussion | Exact patch/line citations; reviewer controls pace; comments remain drafts until submitted |
| AI-GH-04 | “Turn this conversation into work we can finish.” | Extract decisions, unresolved questions, acceptance criteria, dependency order and editable issue/sub-issue drafts | Proposed owners/priorities are labelled suggestions; no inferred private commitments; no automatic issue publication |
| AI-GH-05 | “Explain why this build fails and what to try.” | Trace failed steps to changed files and previous attempts; suggest the smallest experiment and prepare a patch where justified | Preserve run/attempt/SHA provenance; distinguish infrastructure failure, regression and uncertainty; reruns are deliberate |
| AI-GH-06 | “Make these repositories consistent.” | Detect policy/template/workflow drift, explain intentional exceptions, rehearse an alignment and prepare per-repository PRs | No silent winning variant; per-target diff, permissions, conflict checks and recovery |
| AI-GH-07 | “Help a new maintainer take over.” | Create a living orientation book from architecture, ownership, decisions, release practices and worked examples | Source links/freshness, explicit unknowns, account-limited evidence and task-based learning |
| AI-GH-08 | “What should I pay attention to today?” | A personal briefing ranked by actual responsibility, deadlines and evidence, with one useful next action per item | Explain ranking; no people scoring; reading leaves remote notifications unchanged |
| AI-GH-09 | “Walk me through this security finding.” | Explain affected code/dependency, assess available evidence, prepare a patch/test plan and owner-facing report | No claim of exploitability or safety without evidence; no silent dismissal or secret disclosure |
| AI-GH-10 | “What changes if we adopt this API version?” | Compare schemas/code usage, find affected repositories, draft migrations and sequence compatibility changes | Distinguish API facts from inferred impact; use pinned schemas and exact references; validate actual behavior |
| AI-GH-11 | “Build our contribution process.” | Interview the maintainer, generate issue forms/PR templates/CODEOWNERS/labels/workflow drafts, demonstrate a newcomer journey | Native structured editors remain the source of truth; all configuration is reviewable and round-trippable |
| AI-GH-12 | “Prepare the release train across our family.” | Coordinate version dependencies, changelogs, artifacts, release drafts and announcement materials across repositories | Durable dependency graph, per-repository exact revisions and staged authorization; partial release has an explicit recovery plan |

### 10A.6 Bold WordPress missions

| ID | Person's request | Ambitious experience | Acceptance |
| --- | --- | --- | --- |
| AI-WP-01 | “Build our volunteer application process.” | Interview for purpose, audience and data needs; prepare accessible pages, QAF form, confirmation/help, review workflow and navigation in the Practice Site | Real native block/field/rule structures; data minimization; sample submissions; keyboard/manual acceptance and a reviewed promotion plan |
| AI-WP-02 | “Make this site understandable and welcoming.” | Review content structure, headings, link purposes, forms, media descriptions and navigation; offer a prioritized repair studio | Specific findings and before/after previews; preserve author intent; AI text is reviewed; no automatic WCAG conformance claim |
| AI-WP-03 | “Help me publish the next month.” | Build an editorial plan from supplied goals, existing content, events and available contributors; prepare drafts and schedules | Evidence-linked factual claims, explicit timezone, no invented commitments, editable plan and deliberate scheduling |
| AI-WP-04 | “Move this site without breaking the visitor journey.” | Map content/media/forms/redirects, rehearse in a practice/staging site, identify missing plugin equivalents and prepare a migration runbook | Link/asset mapping, unsupported-feature report, sampled real journeys, rollback limits and per-step verified results |
| AI-WP-05 | “Why did this page change?” | Trace WordPress revisions, templates, styles, plugins and related repository changes into a readable timeline | Separate correlation from cause; cite actual records; do not invent actor attribution |
| AI-WP-06 | “Create a membership experience people can use.” | Prepare join/renew/cancel content and help, PMPro configuration drafts where supported, reminders and staff support scripts | Exercise supported test-mode journeys; show real subscription consequences; no charge/cancellation hidden in a draft step |
| AI-WP-07 | “Update all our sites with the fewest surprises.” | Gather versions, dependencies, changed behavior and available backups; rehearse supported updates and build a rollout order | Fresh site-specific evidence, explicit backup uncertainty, per-site approval/result and practical recovery boundaries |
| AI-WP-08 | “Turn this archive into useful knowledge.” | Cluster old posts by topic, find duplication and contradictions, suggest hubs and refreshed drafts with citations | Reviewable classifications, preserved original URLs/authorship, proposed redirects and no unsupported factual rewrites |
| AI-WP-09 | “Make our forms work for real people.” | Translate requirements into fields, conditions, validation, explanations and sample cases; rehearse conversions and error recovery | Deterministic schema/rule checks plus user testing; no fabricated visitor behavior or automatic rejection based on how someone types |
| AI-WP-10 | “Prepare this site for another language.” | Build a terminology/style glossary, propose translations and identify layout/form/media gaps | Human review and language metadata; preserve links/format; plugin-specific writes only where supported |
| AI-WP-11 | “Find the journey that is frustrating our visitors.” | Inspect a user-chosen path such as finding an event or submitting a form, assemble likely friction, propose repairs and a test script | Findings tied to observed UI/content; consented testing, no covert visitor/session recording; manual assistive checks |
| AI-WP-12 | “Explain what running this site needs from me.” | Turn health, pending content, membership renewal exceptions, form queues and updates into a short operational briefing | Unknown/unreachable sites remain visible; actionable next steps and current data; private/member details only when needed |

### 10A.7 Shared intelligence that makes both Workbenches more capable

| ID | Proposal | What makes it valuable | Acceptance boundary |
| --- | --- | --- | --- |
| AI-X-01 | A project map that connects the real objects | Link issue, change, run, release, help page, WordPress content and form into an explorable relationship outline | All edges have provenance; inferred links are labelled; private source access is rechecked |
| AI-X-02 | A release-to-publication mission | Prepare GitHub notes, WordPress announcement, user help and accessible media descriptions from the same verified change set | Separate draft readiness from released/published states; no implicit cross-service publish |
| AI-X-03 | Intent-to-operation compiler | Convert “align the bug label on our family repositories” into a typed query, frozen target set and native change plan | Only registered operations and supported schemas; server permissions, preview and verification remain deterministic |
| AI-X-04 | A task interface generated from the capability ledger | When a new route appears, explain its purpose and propose native labelled controls/actions from its verified schema | Preview generated UI/schema mapping; deny unsupported writes; human review before promoting to a polished native feature |
| AI-X-05 | An AI completeness auditor | Compare API schemas, ledger, tools, UI and help; propose missing coverage rows and tests | Suggestions never mark themselves covered; API source/operation identity and actual acceptance evidence required |
| AI-X-06 | Counterfactual rehearsal | “What would change if we renamed this taxonomy or tightened these repository rules?” produces an impact outline and a simulated plan | Distinguish deterministic analysis, sandbox observation and model speculation; a simulation is not a production guarantee |
| AI-X-07 | Event-driven investigation | On an enabled Watch, collect bounded evidence and prepare a useful brief or draft repair while the user is away | Explicit scope/budget/hosting, deduplication, pause and retention; remote writes require an authorized policy |
| AI-X-08 | Reviewed organizational memory | Save approved terminology, accessibility preferences, release policies, architecture decisions and site facts | View/edit/forget/source/expiry; account/site isolation; no silent extraction of sensitive traits |
| AI-X-09 | A learning partner that works in the actual Workbench | Explain the selected object, guide the next action, rehearse mistakes in a safe environment and gradually reduce hints | Every step has a keyboard path; stable focus; no dependency on AI to complete the task |
| AI-X-10 | An outcome-oriented team of specialist roles | Planner, investigator, implementer, accessibility reviewer and verifier can contribute separate evidence to one mission | Parallel reads may help; serialize conflicting writes; independent-looking model opinions are not independent proof |
| AI-X-11 | Portable mission handoff | Continue a prepared task from ChatGPT to native QUILL or from a GitHub context to the WordPress Workbench | Transfer an explicit mission package/evidence references, not assumed access to private ChatGPT history; keep identities/permissions visible |
| AI-X-12 | Native document outputs for every AI result | A briefing, diff, calendar, plan or impact analysis opens as a structured document/table for find, headings, Read Aloud, braille and export | Full keyboard equivalent, semantic structure, citations and timestamp; no chat transcript as the only usable output |

### 10A.8 Delightful accessible interaction

- [ ] AI-UX-01 One Ask surface takes the selected object/list/site/repository as explicit context; the user can inspect and narrow it.
- [ ] AI-UX-02 Start answers with a useful short conclusion and offer evidence/detail by section; keep raw authoritative views one action away.
- [ ] AI-UX-03 Show a stable mission outline: Goal, Evidence, Plan, Prepared Changes, Activity, Results, Recovery.
- [ ] AI-UX-04 Read progress at useful milestones; offer details on request and braille-readable status. Streaming tokens must not flood speech.
- [ ] AI-UX-05 Stop cancels future work, returns promptly and reports what already happened or remains uncertain.
- [ ] AI-UX-06 “Show me,” “explain that,” “change the plan” and “take me there” all have native commands and visible controls.
- [ ] AI-UX-07 Generated tables/charts/maps/calendars always have linear semantic equivalents.
- [ ] AI-UX-08 Typed requests and supported dictation can share a command path; microphones, transcription and voice services remain separately capability-checked and consented.
- [ ] AI-UX-09 Preview images, media descriptions and form experiences with meaningful alternatives; model confidence is never an accessibility verdict.
- [ ] AI-UX-10 Keep retries, sign-in renewal and usage-limit handling in the mission without losing selection, drafts or decisions.
- [ ] AI-UX-11 A person can finish an AI-prepared plan manually after disconnecting AI.
- [ ] AI-UX-12 Give users a simple level-of-detail preference without hiding essential consequences.

### 10A.9 Execution architecture and all-API accounting

**Recommended flow:** user outcome → scoped evidence → typed plan → native preview → authorized tool execution → remote verification → durable result.

- [ ] AI-ARCH-01 Build Workbench read/prepare/execute tools from the shared action/operation catalogue, not a second set of direct HTTP implementations.
- [ ] AI-ARCH-02 Separate data-read scope from permission to send data to the selected AI connection.
- [ ] AI-ARCH-03 Give every tool a stable operation ID, parameter schema, return schema, prerequisite, risk tier, permission source and idempotency/reconciliation behavior.
- [ ] AI-ARCH-04 Retrieve a small relevant tool set locally from the complete capability ledger. Account for every API operation without sending thousands of tools in every prompt.
- [ ] AI-ARCH-05 Reuse client-executed function/custom-tool support where the selected route allows it; verify engine support rather than assuming hosted MCP is available.
- [ ] AI-ARCH-06 Use prepared-plan identifiers binding targets, proposed values, account/site, scope, revision and expiry. A different proposal requires a new reviewed plan.
- [ ] AI-ARCH-07 Keep API credentials inside the provider layer. Tool outputs return selected content/results rather than passwords, signing keys or raw tokens.
- [ ] AI-ARCH-08 Treat issue bodies, logs, web pages, imported documents and plugin descriptions as untrusted evidence, not authority to change task instructions or permissions.
- [ ] AI-ARCH-09 Track facts, model hypotheses, user decisions and verified results separately.
- [ ] AI-ARCH-10 Persist mission state and tool outcomes atomically; prevent duplicate execution after restart or reconnect.
- [ ] AI-ARCH-11 Derive the closing “what changed” report from actual verified operations; do not accept the model's self-report as completion evidence.
- [ ] AI-ARCH-12 Handle remote changes during reasoning/review; re-check affected plans just before execution.
- [ ] AI-ARCH-13 Use bounded local indexing and explicit retained context, with citations to revisions/objects and clear omissions.
- [ ] AI-ARCH-14 Export mission evidence and drafts in reusable formats; support deletion and account/site removal policies.
- [ ] AI-ARCH-15 Add authenticated MCP access to the same tools only after native contracts work, with per-client scopes, revocation and a native activity record.
- [ ] AI-ARCH-16 Keep the deterministic Workbench, help and API Console useful when AI is unavailable.

### 10A.10 Delegation and automation policy

A person should be able to authorize a bounded outcome once. The system must state what that authorization covers and preserve the original limits.

| Delegation level | Example | Expected behavior |
| --- | --- | --- |
| Observe/explain | “Tell me when these checks finish.” | Read only the named scope; notify with evidence |
| Prepare | “Draft the announcement when the release is published.” | Create a local/private draft within the named scope; do not publish |
| Execute a reviewed plan | “Apply this exact label cleanup.” | Execute frozen targets/values, verify, record per-target outcomes |
| Bounded standing policy — future proposal | “Triage new issues with these exact rules, and prepare anything uncertain for review.” | Explicit action allowlist, scope, lifetime, budget, exceptions, audit, pause/revoke and drift behavior |

- [ ] AI-AUTO-01 Begin with observe/prepare missions; add execution after recovery and preview contracts are proven.
- [ ] AI-AUTO-02 Classify supported operations by delegation suitability and reversibility; do not equate a registered API operation with permission to automate it.
- [ ] AI-AUTO-03 Scheduling/hosting availability and AI allowance are separate prerequisites. A plan subscription does not itself guarantee an always-on worker.
- [ ] AI-AUTO-04 Use current permissions and remote preconditions on each action; expired/revoked authorization pauses the mission.
- [ ] AI-AUTO-05 Make exception queues useful: uncertainty, conflicts, changed scope, rate limits and insufficient authority each get a next action.
- [ ] AI-AUTO-06 Prevent event feedback loops and duplicate actions across native and ChatGPT surfaces.

### 10A.11 Roadmap for AI delivery

| Slice | Build | Finish evidence |
| --- | --- | --- |
| AI-0: foundations | Reconcile accepted AI design, current source and current plan-usage contract | Truthful capability matrix, existing sign-in/limits/revocation audited, no duplicate connection settings |
| AI-1: explain selected work | Grounded Ask for GitHub objects and WordPress content/health with inspectable context | Source/revision citations, accessible answer document, withheld/private/partial-data cases |
| AI-2: prepare useful work | Triage drafts, release/announcement drafts, content/form plans, native change previews | Editable output, no unintended writes, preserved drafts, relevant schemas checked |
| AI-3: execute reviewed missions | Shared Workbench tools, task runner, frozen plans, durable progress and recovery | Authorization scope respected, verified outcomes, interruptions/conflicts/limits recovered |
| AI-4: cross-service missions | Release train plus publication preparation; staging/practice rehearsal; fleet alignment | End-to-end journeys, exact identities, per-step evidence and safe partial completion |
| AI-5: bring QUILL to ChatGPT | Authenticated plugin/MCP tools using the same operation catalogue | Real eligible-account connection, native handoff, revocation and equivalent accessibility |
| AI-6: bounded event missions | Opt-in investigation/preparation and carefully selected policies | Explicit hosting/usage/lifetime, no duplicate loops, useful exception handling |
| AI-7: advanced experiences | Impact rehearsal, generated task interfaces, specialist roles and living project memory | Demonstrated benefit in real user studies plus complete deterministic fallbacks |

**Recommended first three demonstrations**

1. **GitHub:** “Explain why this PR is blocked and prepare the smallest next steps.” Read-only investigation plus reviewable drafts; exact revision evidence.
2. **WordPress:** “Build an accessible volunteer form and its pages in my Practice Site.” A tangible end-to-end result, with sample cases and a clear promotion plan.
3. **Together:** “Prepare our next release and its WordPress announcement.” One mission joining real source changes, current checks and editable publication materials.

### 10A.12 AI acceptance and product decisions

- [ ] AI-ACC-01 Evaluate grounded correctness, task success, time/wrong turns, speech/focus behavior, recovery and surprise actions.
- [ ] AI-ACC-02 Exercise malicious remote instructions, incomplete pages, revoked access, concurrent edits and interrupted/failed model streams.
- [ ] AI-ACC-03 Test usage exhaustion mid-task, explicitly chosen connection changes, local restart and ambiguous remote writes.
- [ ] AI-ACC-04 Compare Explain/Prepare/Do journeys in QUILL and Lite with new/experienced keyboard and screen-reader users.
- [ ] AI-ACC-05 Verify every asserted completed change against recorded tool results and current remote state.
- [ ] AI-ACC-06 Keep model/engine/route-specific evaluation sets and record their versions; improve prompts/tools from actual failures.
- [ ] AI-ACC-07 Reject “AI says accessible,” “AI says tested” and “AI says done” as sign-off evidence without the underlying checks.
- [ ] AI-DEC-01 Decide which proposals enter the accepted Workbench scope and release sequence.
- [ ] AI-DEC-02 Choose the supported native task pathway for My ChatGPT plan and the readiness criteria for Codex versus a native function-tool planner.
- [ ] AI-DEC-03 Decide desktop-only versus separately hosted/background execution as a distinct product/deployment decision.
- [ ] AI-DEC-04 Define editable mission memory, data export, retention and cross-service scope defaults.
- [ ] AI-DEC-05 Decide first supported ChatGPT plugin distribution and eligibility path after validating the native workflows.

**End state:** a person brings their account, chooses an outcome, understands and controls the plan, and gets useful, verified work across GitHub and WordPress. Every API capability remains accounted for; AI makes those capabilities easier to discover and combine.

## 10B. Additions from the 2026-11-13 audits

Two read-only audits on 2026-11-13 added these: a comparison of GHManage
(`S:\code\ghmanage`, v1.0.0 to v1.2.0) against the GitHub Workbench, and an
API-family coverage audit of both Workbenches against this file, the PRDs and
the code. None duplicates an earlier line here. Items marked "probable bug" are
in QUILL's own code, found by reading it; GHManage was only the comparison.

### 10B.1 Ported from GHManage

- [x] **Compare commit list order (probable bug).** `branch_compare.py` and `github_compare_branches_dialog.py` show GitHub's first 30 compare commits, which are the oldest, under a "newest first" label with no "30 of N" note. Page to 250, newest first, and say when the list is cut short. Size S. *(Done 2026-11-13: newest first, up to 250, and the tab says when cut short.)*
- [x] **Ahead/behind on every branch (never built, not a visible bug).** `items_provider.py` sets both counts to 0 and nothing shows them yet. One GraphQL `compare` query per 100 branches fills them (GHManage `gh_data.py`; its query compares the wrong way round, so swap the two numbers). Home: Branches columns and Properties. Size S. *(Done 2026-11-13: Against default column and detail line; blank when GitHub did not say.)*
- [x] **A comparison says what is behind and whether a pull request exists.** Commits-behind list and the open-PR line, with GHManage's sentences moved into a wx-free `quill/core/github/compare_words.py`. Size S-M. *(Done 2026-11-13: Commits Behind tab, open-PR line and Open Pull Request button; words in compare_words.py.)*
- [x] **Create a pull request from a comparison.** Prefilled title, Draft option, a check for an existing PR, and the draft kept on Cancel; `create_pull_request` gains `draft`. Size M. *(Done 2026-11-13: New Pull Request (Ctrl+N on Pull Requests or a branch): prefill, Draft, existing-PR check, kept draft.)*
- [x] **One command per field.** Set Milestone, Labels, Assignees, Projects and Edit Title, each opening the existing sheet at that field, on issue and pull request rows. Size S. *(Done 2026-11-13: Edit Title..., Labels..., Assignees..., Milestone... and Projects... on both row types, keyless (decision 11), now enabled, opening the sheet with focus on the field.)*
- [x] **Projects editable on the issue sheet.** Add to and remove from Projects (v2) with the GraphQL mutations; create a project. Size M. *(Done 2026-11-13: Projects page is a check list on issue and pull request sheets: addProjectV2ItemById, deleteProjectV2Item, New Project... via createProjectV2; no undo, since removal drops field values.)*
- [x] **Label writes.** Creating a label that already exists (GitHub's bare 422) says so and offers to use it; labels save as additions and removals, not a replaced set, so a concurrent addition is not lost. Size S. *(Done 2026-11-13: POST .../labels for additions, DELETE .../labels/{name} for each removal; set fields skip the conflict check and verify only their own changes.)*
- [x] **Rows JAWS reads twice.** Long checklists use a virtual list (GHManage `ghviewer.py`); audit `workbench_frame.py`'s select-then-focus pair and Explore notifications' rewrite-after-Mark-Read for the same double read. Size S. *(Done 2026-11-13: one select-and-focus change, place kept and no-op refills skipped (list_place.py); Explore defers the read row's rewrite. Checklists are already one check box per choice, never a rebuilt list, so no virtual list was needed.)*
- [x] **Compare from a row, and compare links.** Compare With Default or With Previous on branch, tag, release and commit rows; a pasted compare link opens the comparison. Size S. *(Done 2026-11-13: Compare With Default (Ctrl+B) and With Previous (Alt+Shift+B) on all four rows; compare links open from Ctrl+L and favorites.)*
- [x] **Across Repositories categories (GX16).** Port GHManage's Categories mode (`across.py`) into the empty `across` node, with a saved repository-set store. Size L. *(Done 2026-11-13: Ctrl+0: chosen repositories and eight category lists with per-repository outcomes. Repository Set store per account. Site-set style named sets, sort and ] [ keys in the UI remain.)*

### 10B.2 API coverage gaps: GitHub

- [x] **GHEC REST description (audit log, SAML credential authorizations).** Vendor GitHub's Enterprise Cloud OpenAPI description beside the api.github.com one and diff it, so GATE-GITHUB-COVER counts GHEC-only operations. User task: an org owner reads the audit log and revokes a member's SSO-authorized token. Home: Organizations > org > Audit Log and Organizations > org > Single Sign-On. Size M. *(Done 2026-11-13: `enterprise.json` now holds the 310 operations GitHub's own GHEC description has beyond api.github.com (commit 53fd7d2), replacing the hand-named rows. The organization audit log, SAML SSO authorizations and the other organization and repository features (custom roles, announcement banner, bypass and dismissal requests, Git LFS, Advanced Security committers) are planned under their homes; enterprise-account, SCIM, IdP group and closing-down routes are out_of_scope with reasons.)*
- [x] **GHES per-version descriptions.** Vendor the supported Enterprise Server descriptions and mark each ledger row with the first and last GHES version that has it, so an unsupported action on an older server is greyed out with its reason rather than failing. User task: use the Workbench against a company's GitHub Enterprise Server. Home: account Properties > Host, and every action's availability text. Size M. *(Done 2026-11-13: `ghes_versions.json` gives the first and last of GHES 3.18 to 3.22 for 1108 operations; 108 Server-only operations are out_of_scope rows. `api_coverage.unavailable_reason(key, server_version)` returns the greyed-with-reason sentence (needs a later version, removed after a version, or GitHub.com only) and `server_version_for_host()` is the hook. Accounts are GitHub.com only (`accounts.py` refuses other hosts), so it returns None and nothing greys until Enterprise Server sign-in exists.)*
- [x] **Enterprise identity dispositions (SCIM, enterprise teams, enterprise billing).** Record each as out_of_scope with a one-line reason and an Open on GitHub row so the gate is honest. User task: an enterprise admin learns where to go. Home: Organizations > org > Enterprise (Open on GitHub). Size S. *(Done 2026-11-13: SCIM (organization and enterprise), enterprise teams, enterprise billing and the enterprise audit log are out_of_scope rows with reasons and the Open on GitHub home; the 31 `/enterprises/` operations in the api.github.com snapshot and the 44 enterprise-admin mutations likewise.)*
- [x] **GraphQL read-query ledger.** Add query-only connections with no REST twin (pinnedItems, fundingLinks, contributionsCollection, dependencyGraphManifests, discussionCategories, starred lists) to the coverage table as rows with homes, not only mutations and viewer answers. User task: read your contribution table, a repository's sponsor links, or a profile's pins. Home: Account > Profile, Repository > General, People > person. Size S. *(Done 2026-11-13: `graphql_queries` in `api_coverage.json`, 21 rows: 15 reads the Workbench makes (discussionCategories, projectsV2, reviewThreads, subIssues, mergeQueue, viewerPermission and others) covered with their homes, and pinnedItems, contributionsCollection, fundingLinks, dependencyGraphManifests, star lists and linkedBranches planned with theirs.)*

### 10B.3 API coverage gaps: WordPress

- [x] **Core REST cannot update (plugins, themes, core, translations).** Record that `wp/v2/plugins` only installs, activates, deactivates and deletes; `wp/v2/themes` is read-only; core and translation updates have no route. Give "update everywhere", "turn auto-updates on", theme activate/install and the Updates node an exact wp-admin route (or a supported plugin namespace such as Jetpack) and say so in the row before the user acts. User task: keep plugins and themes current across sites. Home: Sites > site > Plugins, Appearance > Themes, Updates; Across Sites > Plugins and Themes. Size S. *(Done 2026-11-13: `workbench_no_rest.py` names each wp-admin screen; plugin, theme and Across Sites rows say the limit; Open in Dashboard on plugin, theme and Across rows; theme Activate opens Appearance > Themes; Install on Sites Missing It installs a plugin by slug after a preview, opens Add New for a theme; `NO_ROUTE` dispositions in workbench_coverage.py. Jetpack's update route left planned with the Jetpack node.)*
- [x] **Gravity Forms feeds.** List each form's add-on feeds (Mailchimp, Stripe, Zapier and others) with active state; toggle and edit known-safe fields; delete with preview. User task: find why a form stopped sending to a mailing list. Home: Sites > site > Forms > form > Feeds. Size M. *(Done 2026-11-13: Sites > site > Forms > Feeds, beside Responses because the tree stays four deep; a form's Show Its Feeds opens it filtered to the form. Activate or Deactivate and Rename preview and PUT the whole feed; Delete Permanently previews, and Ctrl+Z makes the feed again.)*
- [x] **Gravity Forms entry notes and properties.** Read and add notes on an entry; mark starred and read. User task: record follow-up on a submission without wp-admin. Home: entry Properties > Notes; entry context menu. Size S. *(Done 2026-11-13: Notes... (Ctrl+Alt+N), Star or Unstar (Ctrl+Alt+F), Mark Read or Unread (Ctrl+Alt+U); the entry's Properties has Answers and Notes pages and saves Starred and Read, each sent as the whole re-read entry, with undo.)*
- [x] **Gravity Forms resend notifications.** Resend an entry's notifications with a preview of which notifications and recipients. User task: a visitor says they never got the confirmation email. Home: entry context menu > Resend Notifications... Size S. *(Done 2026-11-13: Ctrl+Alt+I; recipients worked out per entry for email, field and routing notifications, checked, previewed, then sent with _notifications.)*
- [x] **Gravity Forms results and field filters.** Show quiz, poll and survey results as tables and sentences; drive the entry filter from the form's own field-filters. User task: read poll results by ear. Home: Sites > site > Forms > form > Results; Filter Builder. Size M. *(Done 2026-11-13: Sites > site > Forms > Results, a row per answer with count and share and the question as one sentence; the Filter Builder on Responses offers the chosen form's field filters and their allowed values. Since 2026-11-14 the filter is sent to the site as `gf/v2/entries`' `search` (field_filters, mode all or any), read page by page, with the site's own count in the status bar (`workbench_gravity_search.py`).)*
- [x] **Gravity Forms test submission.** Validate and submit a test entry through `forms/{id}/submissions` (validation first, practice site preferred). User task: check that a form works after editing it. Home: form context menu > Test This Form... Size S. *(Done 2026-11-13: editable test values, validation route first with each refused field named, then a preview that says when the site is live and a practice site is better; Ctrl+Z moves the test entry to the Trash.)*
- [x] **Build Gravity Forms forms in QUILL.** New Gravity Form and Edit Form open QUILL's own accessible form editor on a Gravity Forms form: common field types, choices, conditional logic, form settings, the default confirmation and the Admin Notification; accessibility checks before saving; POST for new and PUT after a conflict check, the whole form sent so nothing QUILL does not edit is lost; a preview, a read-back and Undo; entries never touched; Copy between QAF and Gravity Forms. User task: "can we also build gravity forms with quill's wordpress features?" Home: Sites > site > Forms (New Here, Ctrl+N), form context menu, Item > Gravity Forms. Size L. *(Done 2026-11-13: core `gravity_build.py` (the form object, edited on a copy; ids never reused), `gravity_build_checks.py` (labels, required marking, empty choices, page and section structure, labels that sound alike, logic naming missing or later fields; plus QUILL's QAF checks over the converted form), `gravity_build_save.py` and `gravity_qaf.py`; UI `wordpress_gravity_editor.py`, `wordpress_gravity_field_dialogs.py`, `wordpress_workbench_gravity_build.py`. Eighteen field types: text, textarea, email, phone, number, select, radio, checkbox, multiselect, date, time, website, name, address, consent, html, section, page; any other field is kept, moved or removed, never edited. Tests: `test_wp_gravity_build_core.py`, `test_wp_gravity_build_ui.py`, `test_wp_gravity_editor_dialogs.py`. Live checks 123 to 126 in `docs/qa/wordpress_live_gravity_build.py` skip until a site with Gravity Forms (licensed) and its REST API is available; not yet run against a real Gravity Forms install.)*
- [x] **PMPro `pmpro/v1` namespace.** Classify its routes in workbench_coverage.py; use it as the fallback where the Abilities API is absent and for discount codes and Has Access checks. User task: create a discount code; check whether a member can see a page. Home: Sites > site > Members > Discount Codes; member Properties > Access. Size M. *(Done 2026-11-13: routes classified; Show Memberships falls back to pmpro/v1; Check Membership Access on a person's context menu, and since 2026-11-14 also the member Properties page Access (Check a Post or Page, on read-only sheets too); Memberships > Discount Codes lists through a discount-codes ability where offered, else says pmpro/v1 reads one code at a time and opens wp-admin; Look Up a Discount Code and New Discount Code with a preview. Not checked against a live PMPro site.)*
- [x] **Site Health Info disposition.** State that the Info tab (server, database, constants) has no REST route; show what the tests and directory sizes cover and open wp-admin for the rest. User task: send a site's health details to a host. Home: Sites > site > Site Health > Information. Size S. *(Done 2026-11-13: Site Health > Information: the tests REST offers, directory sizes, and a row that opens site-health.php?tab=debug.)*
- [x] **XML-RPC disposition.** Record XML-RPC as deliberately unused (security, deprecation), with a check that warns when a site still has it enabled. User task: know whether the site exposes XML-RPC. Home: Sites > site > Site Health > Security. Size S. *(Done 2026-11-13: recorded out_of_scope in NO_ROUTE; Site Health > Security asks the site's xmlrpc.php for system.listMethods, unsigned, and warns when it answers.)*
- [x] **WordPress.org themes and translations directories.** Consented egress rows and readable details for theme search (for "install on sites missing it") and language pack status. User task: install the same theme on another site; see which sites lack a translation. Home: Appearance > Themes > Add New; Settings > General > Language. Size M. *(Done 2026-11-13: `dotorg.py` with its own egress row; Find a Theme on WordPress.org (theme and Across rows) and Language Pack Status (setting rows, every site), each behind a consent naming api.wordpress.org and what is sent.)*
- [x] **Site MCP Adapter and Abilities as AI tools (optional).** Account for a site's own MCP/Abilities server as a tool source for the AI Workbench under the existing consent boundary. User task: Ask about this site using the site's published abilities. Home: Site > Ask About This Site. Size M. *(Done 2026-11-13 as a disposition: Ask the Site already offers the site's abilities to the chosen AI, each run after a yes; the MCP Adapter's `mcp` routes are recorded out_of_scope because they serve the same abilities to outside AI apps. No new seam was added.)*

### 10B.4 Usage, and the documentation pass

- [x] **AI usage.** Ctrl+8 speaks the connection, model and one usage clause where the service reports one (codex.md 10A.11). The local ChatGPT request count that `chatgpt_account.py` describes still has to be built and named as QUILL's own count, never the provider's allowance. *(Verified 2026-11-13: already shipped in #1728 -- `chatgpt_usage.record_request` counts plan requests, `connection_usage.which_ai_sentence` speaks the clause as a local count; 29 tests pass.)*
- [x] **GitHub Billing and Usage.** Account > Billing and Usage, read-only: Actions minutes, Packages and shared storage, Copilot seats where the account may read them; the menu has only a placeholder comment today. *(Done 2026-11-13: People > My Billing and Usage, read only, from the enhanced billing report.)*
- [ ] **Documentation pass at the end of each delivery batch.** Release notes, announcements, What's New, both PRDs and their status page, the QUILL and QUILL Lite user guides, the GitHub guide and the WordPress and Forms guide, with regenerated HTML and EPUB siblings, written in Jeff's voice and matching what shipped.

## 11. Delivery order and ownership

| Milestone | Deliverable | Exit evidence |
| --- | --- | --- |
| M0 | Current candidate stabilized and records reconciled | Fresh green CI; known regressions resolved; authoritative scope register |
| M1 | Complete API/requirement ledgers and gates | Zero unclassified operations; every requirement has an owner/status; meaningful planned backlog |
| M2 | Native parity and shared interaction/accessibility foundations | Both-app journeys, every surviving action reachable, sheet/permission/keyboard/lifetime contracts |
| M3 | GitHub coverage/templates and WordPress discovery/key/runtime gaps | Phase 11/12 evidence, combination audit, packaged Practice Site |
| M4 | Cross-repository/site operations and bold workflows | Kind × scope × operation matrix, preview/conflict/result/recovery evidence |
| M5 | Remaining API feature families and GX journeys | Native/advanced/admin-only dispositions with real task acceptance |
| M6 | Live, manual AT, docs and release sign-off | Exact candidate results, no release blockers, honest published support matrix |

Engineering owns implementation, snapshots, packaging, integration and documentation. Jeff/product owns scope decisions and prioritization. User/testers own the recorded manual acceptance; external plugin/runtime work has its own named owner.

### Task record to use for every closure

- ID / source requirement:
- State: OPEN / AUDIT / DEPENDENCY / PROPOSAL / complete / explicitly deferred:
- Owner and milestone:
- Supported hosts/site/plugin/API versions and permissions:
- Native UI home and accessible command:
- Implementation/PR:
- Automated evidence and exact revision:
- Live and manual evidence:
- Limitations / recovery:
- Documentation and coverage-ledger links:

## 12. Exhaustive source-derived acceptance ledgers

The following appendices retain the accepted requirement IDs and feature-family detail. Review each against the latest code; attach evidence before checking it off. A requirement may be partly implemented. Explicit later scope decisions override historical wording, but every API capability still requires a disposition.


### Appendix A. GitHub accepted requirements — verify every ID


Each requirement has an id, a strength (**Must** ships before the Workbench is
the default; **Should** ships in the program; **May** if time allows) and
the section that designs it. Each Must has at least one test, named in the
phase's PR. Ids are never renumbered; a dropped requirement keeps its id with
"withdrawn".

### E1. The window and its panes

- [ ] **AUDIT** GH-R-001 Must: the Workbench is a top-level frame with its own menu bar,
  status bar and taskbar button, one per app (3.1).
- [ ] **AUDIT** GH-R-002 Must: it never blocks the editor; its dialogs block only it (3.1).
- [ ] **AUDIT** GH-R-003 Must: F6 and Shift+F6 cycle tree, filter, list and details (3.2).
- [ ] **AUDIT** GH-R-004 Must: it remembers size, panes, last node, expanded nodes,
  columns and filters per account (3.1).
- [ ] **AUDIT** GH-R-005 Must: Escape clears the filter, then goes Back, and never closes
  the window (3.1).
- [ ] **AUDIT** GH-R-006 Must: Switch to Editor and Open in Editor raise the editor that
  opened it (3.1).
- [ ] **AUDIT** GH-R-007 Must: the status bar is reached with F6, arrowed across, and every
  cell has Enter and a context menu with Copy and Help, mirrored to the real
  status bar, built in the shared engine on the family's existing focusable
  status bar pattern (3.2.1).

### E2. The tree

- [ ] **AUDIT** GH-R-010 Must: the tree is a native `wx.TreeCtrl`, at most four levels
  deep, loading lazily, with counts after names that are never announced
  (3.3, 9).
- [ ] **AUDIT** GH-R-011 Must: every view in GitHub Items and Explore appears exactly once
  (the "nothing dropped" test) (10).
- [ ] **AUDIT** GH-R-012 Must: nodes needing sign-in, permission or an opt-in are shown,
  explained, and offer the fix (3.3).
- [ ] **AUDIT** GH-R-013 Must: drill-downs move the tree, and Back and Forward walk one
  history (3.3).
- [ ] **AUDIT** GH-R-014 Should: Group By puts groups in the tree as child nodes (17.4).

### E3. Menus and context menus

- [ ] **AUDIT** GH-R-020 Must: every menu row shows its key; no key is claimed twice;
  greyed rows carry a reason (4).
- [ ] **AUDIT** GH-R-021 Must: context menus hold only rows for the selected row type, the
  default first and Properties last, with More mirroring the Item menu (5).
- [ ] **AUDIT** GH-R-022 Must: Codespaces appears only on repositories, branches and pull
  requests; Rate Limit on no context menu (5).
- [ ] **AUDIT** GH-R-023 Must: menus, context menus, Shift+F1 and sheets are
  all built from one action table (10, 18.6, D5).

### E4. Properties

- [ ] **AUDIT** GH-R-030 Must: Alt+Enter, Item > Properties... and the context menu's last
  row open the Properties sheet of the selected object, for every object type
  in Appendix C (15.1).
- [ ] **AUDIT** GH-R-031 Must: every fact is a focusable labelled control; read-only facts
  are read-only text boxes (15.2).
- [ ] **AUDIT** GH-R-032 Must: an editable field is editable exactly when the user may
  change it, and read-only with a reason otherwise (15.2, 18.2).
- [ ] **AUDIT** GH-R-033 Must: a multiple selection opens one sheet with Mixed values and
  three-state check lists, saving only touched fields (15.2).
- [ ] **AUDIT** GH-R-034 Must: before saving, someone else's changes are detected and the
  user chooses per field; after saving, the object is read again and only a
  verified change is reported as done (15.3).
- [ ] **AUDIT** GH-R-035 Must: every picker ends with New... that creates and uses the
  thing (15.2).
- [ ] **AUDIT** GH-R-036 Should: Alt+Enter on a GitHub reference in a document opens its
  sheet (C9, 22.3).

### E5. Editing

- [ ] **AUDIT** GH-R-040 Must: every field GitHub's API can change has a control on its
  object's sheet; the coverage gate proves it (16.1, 19).
- [ ] **AUDIT** GH-R-041 Must: removal and replacement are as available as adding,
  lifting today's add-only batch rule (16.1).
- [ ] **AUDIT** GH-R-042 Withdrawn (2026-11-09): per-property keys. Alt+Enter opens the
  sheet instead (16.3).
- [ ] **AUDIT** GH-R-043 Must: batches preview, run paced for the rate limit, and report a
  result per item with retry (16.4).
- [ ] **AUDIT** GH-R-044 Must: Undo GitHub Change reverses any reversible change, and an
  irreversible one says so before it happens (16.5).
- [ ] **AUDIT** GH-R-045 Must: Projects (version 2): every field type, views, items,
  workflows and status updates are readable and editable (16.6).
- [ ] **AUDIT** GH-R-046 Must: every relationship (star, watch level, follow, subscribe,
  react, block, sponsor, pin) on a You page and in batch (16.7).

### E6. Filtering

- [ ] **AUDIT** GH-R-050 Must: one query, written by the filter box, the Filter Builder,
  the Filter menu and Show Only or Hide on cells, all in step (17.1).
- [ ] **AUDIT** GH-R-051 Must: every attribute GitHub search supports is sent to GitHub;
  every other attribute filters locally with an honest status line and Load
  All (17.3).
- [ ] **AUDIT** GH-R-052 Must: every list attribute has "has none"; every person field has
  "Me" (17.2).
- [ ] **AUDIT** GH-R-053 Must: filters can be saved as searches and pinned as nodes (17.1).
- [ ] **AUDIT** GH-R-054 Should: Or groups where GitHub search allows them (17.2).

### E7. Permissions

- [ ] **AUDIT** GH-R-060 Must: Account > GitHub Permissions lists every scope the Workbench
  can use, what each unlocks, and whether you have it, and adds every missing
  one in one step for each sign-in kind (18.1).
- [ ] **AUDIT** GH-R-061 Must: the viewer fields of Appendix F.1 are fetched with each
  object and drive greying with reasons (18.2).
- [ ] **AUDIT** GH-R-062 Must: every write command and editable field declares its
  requirement and tier; GATE-GITHUB-PERM fails on one without (18.2, 18.6).
- [ ] **AUDIT** GH-R-063 Must: every object with an access list has an Access page with
  Add, Change Role, Remove and pending invitations (18.3, Appendix D).
- [ ] **AUDIT** GH-R-064 Must: rulesets and branch protection expose every rule and
  setting GitHub offers, with a plain-words Summary page (18.3.1).
- [ ] **AUDIT** GH-R-065 Must: tier 2 changes preview in words; tier 3 adds typed
  confirmation; self-lockout is refused (18.4).
- [ ] **AUDIT** GH-R-066 Must: Read Only, Organize and Full per account; Safe Mode makes
  every account Read Only (18.4).
- [ ] **AUDIT** GH-R-067 Must: Change History records every write, with before and after,
  and never a secret (18.5).
- [ ] **AUDIT** GH-R-068 Should: the access matrix, bulk access changes and access
  templates (18.3.2).
- [ ] **AUDIT** GH-R-069 Should: View As Role, Compare Roles and Why Can't They? (22.10).

### E8. Templates

- [ ] **AUDIT** GH-R-070 Must: issue forms and discussion forms are filled natively, with
  bodies identical to GitHub's (21.7).
- [ ] **AUDIT** GH-R-071 Must: every template kind in 21.2 can be listed, created, edited
  field by field, checked, previewed and saved (21.3 to 21.6).
- [x] GH-R-072 Should: forms can be written as BFL and converted to and from
  GitHub's schema through `interop_github.py` (21.4). *(Done 2026-11-16.)*
- [ ] **AUDIT** GH-R-073 Should: Copy to Repositories for templates and community files
  (21.6, 21.8).

### E9. Beyond parity

- [ ] **AUDIT** GH-R-080 Must: the API Console reaches any REST or GraphQL operation, with
  scope shown, tiers applied and Change History kept (22.2).
- [ ] **AUDIT** GH-R-081 Should: Read as Document for threads, with export (22.4).
- [ ] **AUDIT** GH-R-082 Should: posts are checked for accessibility before sending, offering
  and never blocking (22.4).
- [ ] **AUDIT** GH-R-083 Should: Watches with one-sentence results and sounds through the
  shared feedback channels (22.5).
- [ ] **AUDIT** GH-R-084 Should: the editor commands of 22.3. *(Built 2026-11-17, see GH-C; live and screen-reader checks remain.)*
- [ ] **AUDIT** GH-R-085 Should: export of any list; import of issues from CSV (22.7).
- [ ] **AUDIT** GH-R-086 May: plain-language batches through the Command Key work (22.6).
- [ ] **AUDIT** GH-R-087 Should: Dry Run and the practice repository (22.8).
- [ ] **AUDIT** GH-R-088 Should: the GitHub features listed in 22.1, each as the coverage
  gate schedules it.

### E10. Keyboard

- [ ] **AUDIT** GH-R-090 Must: every key in Part C passes the checks in C1 before adoption
  and lives in the Workbench's `APP_KEYMAPS` entry.
- [ ] **AUDIT** GH-R-091 Must: the families of Part C hold: Ctrl+number goes, Alt+number
  says, F-keys keep Windows meanings, and Alt+Enter is the one key that
  changes things.
- [ ] **AUDIT** GH-R-092 Must: typing always moves through the tree and lists; no letter
  is ever a command (16.3).
- [ ] **AUDIT** GH-R-093 Must: every key is rebindable, and the rebinding follows into
  menus, the reference, Shift+F1 and the Key Describer (C10).

### E11. Help

- [ ] **AUDIT** GH-R-100 Must: F1 answers on every node, row, sheet page, field, menu row
  and dialog, in layers (D3).
- [ ] **AUDIT** GH-R-101 Must: Shift+F1 What Can I Do Here? for every selection (D5).
- [ ] **AUDIT** GH-R-102 Must: Alt+F1 glossary, Ctrl+F1 guide chapter, Ctrl+Shift+F1 Search
  Help (D2, D6, D7).
- [ ] **AUDIT** GH-R-103 Must: empty states, greyed rows, previews and errors carry help
  (D4).
- [ ] **AUDIT** GH-R-104 Must: GATE-GITHUB-HELP at zero and the help tests of D10 green.
- [ ] **AUDIT** GH-R-105 Should: the GitHub tutorials of D8.
- [ ] **AUDIT** GH-R-106 Must: Help and Learning in the tree, with every node of D11 (D11).
- [ ] **AUDIT** GH-R-107 Must: Take Me There and Walk Me Through It on every help topic and
  task; Do It where the answer is one command (D12).
- [ ] **AUDIT** GH-R-108 Must: Shift+F9 Explain That for every result, and Why? on every
  automatic behaviour (D13).
- [ ] **AUDIT** GH-R-109 Should: examples from the person's own data and situation (D14).
- [ ] **AUDIT** GH-R-115 Should: key cards in print and braille, the guide as a book, the
  spoken tour (D15).
- [ ] **AUDIT** GH-R-116 Should: QUILLBert and QUILLBee tips at the right moment, with an
  option for plain help (D16).
- [ ] **AUDIT** GH-R-117 Must: Ask a Person and Report a Help Problem, never sending a
  secret (D17).
- [ ] **AUDIT** GH-R-118 May: Ask How through the family's AI, grounded only in the help
  catalogue (D18).
- [ ] **AUDIT** GH-R-119 Must: one source for every help surface (D19), and the measures of
  D20.

### E12. Speech, braille and sound

- [ ] **AUDIT** GH-R-110 Must: the Workbench announces only what the reader cannot see
  (results, background changes, Watches) and nothing on focus, title or
  selection (GATE-13).
- [ ] **AUDIT** GH-R-111 Must: every announcement is also brailled (GATE-BRAILLE).
- [ ] **AUDIT** GH-R-112 Must: one sentence per outcome, naming what changed (A8).
- [ ] **AUDIT** GH-R-113 Must: sounds go through the shared action-feedback channels; a
  failure or a count is always spoken (A8).
- [ ] **AUDIT** GH-R-114 Should: a braille-shaped row option (22.4).

### E13. Settings

- [ ] **AUDIT** GH-R-120 Must: every GitHub preference lives in Workbench Options, stored
  in `github_workbench.json` through `workbench_prefs.py`, shared by both
  editors; nothing GitHub in the main Options (4.1).
- [ ] **AUDIT** GH-R-121 Must: the three poll settings migrate out of the main Settings
  once, with the vocabulary audit and GATE-SETDOC regenerated (4.1).
- [ ] **AUDIT** GH-R-122 Must: the Workbench is fully usable without opening Workbench
  Options (4.1).

### E14. API use

- [ ] **AUDIT** GH-R-130 Must: only `api.github.com`, `github.com` sign-in pages,
  `uploads.github.com` for assets and, with consent, githubstatus.com; each
  new endpoint family named in the network egress audit (18.6).
- [ ] **AUDIT** GH-R-131 Must: conditional requests (ETag) for every repeated read
  (`conditional_requests.py`), and secondary rate limits respected.
- [ ] **AUDIT** GH-R-132 Must: GraphQL where it is the only API (Appendix F) and where one
  query replaces many REST calls; REST otherwise.
- [x] **AUDIT** GH-R-133 Must: the vendored API snapshot and `api_coverage.json` drive
  GATE-GITHUB-COVER (19, Appendices E and F). *(Done 2026-11-13: see 5.2.)*

### E15. Teams

- [ ] **AUDIT** GH-R-140 Must: teams are created, edited, nested, filled, given
  repository and project roles, and deleted, from the Team sheet and the
  Teams node; the old "Teams out" decision in `repo_admin.py` is removed in
  the same change (18.3.3).
- [ ] **AUDIT** GH-R-141 Must: team code review assignment is readable and editable
  (18.3.3).
- [ ] **AUDIT** GH-R-142 Should: batch membership and batch repository roles across teams
  (18.3.3).
- [ ] **AUDIT** GH-R-143 Should: People > My Teams and team review requests in Needs My
  Attention (18.3.3).

### E16. Across repositories

- [ ] **AUDIT** GH-R-150 Must: Across Repositories has a place for every kind in the 22.11
  table, a row per name with its variants and where it is missing.
- [ ] **AUDIT** GH-R-151 Must: every operation a kind allows in one repository is offered
  across a scope, with the preview and a result per repository (22.11).
- [ ] **AUDIT** GH-R-152 Must: Repository Sets, by hand or by filter, usable as the scope of
  any batch (22.11).
- [ ] **AUDIT** GH-R-153 Should: Promote to Organization wherever GitHub has a shared form
  (22.11).
- [ ] **AUDIT** GH-R-154 Should: the fourth sweep of 22.12, each as the coverage gate
  schedules it.
- [ ] **AUDIT** GH-R-155 Must: category-first lists cover the eight item kinds in 22.11.1,
  preserve repository provenance and exact selection, and name partial, empty, disabled
  and inaccessible results.
- [ ] **AUDIT** GH-R-156 Must: issue types and issue fields preserve stable IDs, schema types,
  permission visibility and explicit unset/empty/unavailable states across list, filter and
  Properties surfaces.
- [ ] **AUDIT** GH-R-157 Must: checklists announce each Space toggle once, save from Enter,
  and return focus predictably on Windows and macOS.

### Appendix B. WordPress accepted requirements — verify every ID

Later plugin-scope decisions apply to historical integration promises; generic API accounting remains required.


- [ ] **AUDIT** WP-R-001 Must: the Workbench is the shared engine's frame with a WordPress
  provider; nothing in the engine is GitHub-only or WordPress-only (3).
- [ ] **AUDIT** WP-R-002 Must: writing stays in the editor; Enter on a post or page opens
  it there (2, 14).
- [ ] **AUDIT** WP-R-002a Must: the status bar contract of the GitHub PRD's 3.2.1, with the
  WordPress cells of section 4 (4).
- [ ] **AUDIT** WP-R-003 Must: Needs My Attention gathers every connected site (5).
- [ ] **AUDIT** WP-R-004 Must: every shipped Tools > WordPress window's capability has a
  node, sheet or action (Appendix B), and its command id opens it (14).
- [ ] **AUDIT** WP-R-005 Must: Alt+Enter Properties on every object in Appendix A,
  including discovered custom types (8, 12).
- [ ] **AUDIT** WP-R-006 Must: conflict check on `modified_gmt` and verify after every
  save (8).
- [ ] **AUDIT** WP-R-007 Must: batch edits through `/batch/v1` with a preview and a result
  per item (9).
- [ ] **AUDIT** WP-R-008 Must: Delete means Trash where WordPress has Trash; permanent
  deletion is tier 3 (2, 11).
- [ ] **AUDIT** WP-R-009 Must: filters use the REST API's parameters, with honest local
  filtering for the rest (10).
- [ ] **AUDIT** WP-R-010 Must: every action and field declares its capability; greying
  carries the reason (11).
- [ ] **AUDIT** WP-R-011 Must: user management with roles, reassignment on removal, and no
  self-lockout (11).
- [ ] **AUDIT** WP-R-012 Must: application passwords listed, created and revoked (11).
- [ ] **AUDIT** WP-R-013 Must: the route coverage gate against the test site's recorded
  index (12).
- [ ] **AUDIT** WP-R-014 Must: schema-built nodes and sheets for custom post types and
  taxonomies (12).
- [ ] **AUDIT** WP-R-015 Should: the Abilities API as commands (12).
- [ ] **AUDIT** WP-R-016 Should: Copy to Site, Compare Sites, snapshots (15.2).
- [ ] **AUDIT** WP-R-017 Should: the practice site on WordPress Playground (15.1).
- [ ] **AUDIT** WP-R-018 Should: Calendar and the editorial queue (15.3, 15.4).
- [ ] **AUDIT** WP-R-019 Should: Read Site as Document (15.5).
- [ ] **AUDIT** WP-R-020 Should: Watches, the REST Console, lists in and out (15.7 to 15.10).
- [ ] **AUDIT** WP-R-021 May: plain-language batches (15.8).
- [ ] **AUDIT** WP-R-022 Must: the keys of Part C, passing the C1 checks.
- [ ] **AUDIT** WP-R-023 Must: help per Part D, with GATE-WORDPRESS-HELP at zero.
- [ ] **AUDIT** WP-R-046 Must: every help feature of the GitHub PRD's Part D (D1 to D20),
  from the shared help module, with nothing GitHub-only (Part D).
- [ ] **AUDIT** WP-R-047 Must: the WordPress glossary, How WordPress Thinks, and every
  Settings field explained with the site's own example (D1, D2).
- [ ] **AUDIT** WP-R-048 Must: help before updates, deletions and deactivations, and for
  every Site Health and accessibility finding (D3).
- [ ] **AUDIT** WP-R-049 Should: practice-site tutorials, Break It on Purpose and the
  first-week path (D4).
- [ ] **AUDIT** WP-R-050 Should: visitor-facing help text for forms and challenges (D5).
- [ ] **AUDIT** WP-R-024 Must: QUILL Lite has the same window and commands (16).
- [ ] **AUDIT** WP-R-025 Must: Held as Spam across sites, with the reason and score, Spam
  and Not Spam reported back to the provider, and batch (13a.5).
- [ ] **AUDIT** WP-R-026 Must (QAF): spam is held with its reason, never dropped, and the
  visitor's confirmation is the same either way (13a.2).
- [ ] **AUDIT** WP-R-027 Must (QAF): no check that judges a visitor by how they type or
  move the mouse may reject an entry; it may only hold it (13a.2).
- [ ] **AUDIT** WP-R-028 Should (QAF): the spam-check interface with Akismet, OOPSpam,
  Shield Security, CleanTalk, the site's blocklist, time to fill, link count
  and ALTCHA as providers, plus the `qaf_spam_check` filter and
  `qaf_entry_marked` action (13a.3).
- [ ] **AUDIT** WP-R-030 Must: the combination test of 12a over the recorded index: every
  GET argument a filter, every enum value offered, every writable property a
  field, every method an action.
- [ ] **AUDIT** WP-R-031 Must: taxonomies and statuses discovered from `wp/v2/taxonomies`
  and `wp/v2/statuses`; `taxonomy_route()` reads `rest_base` instead of
  guessing (1a).
- [ ] **AUDIT** WP-R-032 Must: custom post types get nodes, lists, New, batch and filters,
  not only Open (1a).
- [ ] **PARTIAL** WP-R-033 Must: post meta is exposed; term, user and comment sheets now add registered meta fields. Safely typed scalar lists save; nested objects and grouped repeaters still need dedicated editing controls (1a, 12a).
- [ ] **AUDIT** WP-R-034 Should: Advanced Custom Fields, Meta Box, Pods and CMB2 fields
  through their REST exposure (1a).
- [ ] **AUDIT** WP-R-035 Must: QAF installed on the test site so the live run covers it
  (1a).
- [ ] **AUDIT** WP-R-036 Must: Content Model lists every post type, taxonomy and field
  group on a site, with who registered each (12b).
- [ ] **AUDIT** WP-R-037 Should: QUILL Site Types defines post types, taxonomies and field
  groups over REST, with the field kinds of 12b, site-defined kinds, and
  Export as Code (12b).
- [ ] **AUDIT** WP-R-038 Should: ACF, Pods, Meta Box and Custom Post Type UI definitions
  read, and edited where their APIs allow (12b).
- [ ] **AUDIT** WP-R-039 Should (QAF): text challenges asked only when the quiet checks are
  unsure, generated per visit with the answer kept on the server, loosely
  matched, never locking anyone out, with Send Anyway after three tries
  (13a.6).
- [ ] **AUDIT** WP-R-040 Should: every row of 15.11 has a home, reached through its
  plugin's REST namespace where one exists and verified before its phase, or
  opening the named wp-admin screen where none does (15.11).
- [ ] **AUDIT** WP-R-041 Must: a redirect is offered whenever a published item's address
  changes, on sites with a redirect plugin (15.11).
- [ ] **AUDIT** WP-R-042 Should: the content audit and media housekeeping reports
  (15.11).
- [ ] **AUDIT** WP-R-043 Must: terms, field values, authors, media, patterns, links,
  shortcodes and forms each have their own place, with the value itself as
  the object (15.12).
- [ ] **AUDIT** WP-R-044 Must: Across Sites with Site Sets, variants, Missing From and
  every operation over every scope (15.12).
- [ ] **AUDIT** WP-R-045 Should: the Fleet view across sites, and Promote to Network on
  multisite (15.12).
- [ ] **AUDIT** WP-R-029 Should: entries, spam status and export for every form plugin in
  13b.2 at the level its API allows, and import into QAF (13b).

### Appendix C. Accepted GX delivery and acceptance matrix

Each row requires current implementation and acceptance evidence. “Existing foundation” is not a completion claim.

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

### Appendix D. GitHub historical missing-feature inventory

Source: PRD section 14. Its “today” statements describe the source audit revision, not a fresh code audit. Reconcile each row, including features subsequently implemented in phases 7–10.

### 14.1 Worth adding (people will look for these)

| Feature | Status today | New home |
|---|---|---|
| Close reason: completed, not planned, or duplicate of #n | Not found: closing has no reason | Item > Close Issue... asks the reason; the details pane shows it |
| Linked pull requests and branches for an issue ("Development"), and "create a branch for this issue" | Not found | Issue details; Item > Linked Pull Requests; Item > Create Branch for Issue... (next to Start in Local Worktree) |
| Saved replies | Roadmap GX05 and GX12, not built | Item > Insert Saved Reply in every comment box; Tools > Workbench Options > Saved Replies |
| Wiki | Roadmap GX12, not built | Repository > Wiki (pages as a list, read in details, edit in the editor) |
| Repository invitations: accept or decline | Seen only as a notification type | Needs My Attention > Invitations |
| Edit description, website and features (issues, wiki, discussions, projects on or off) | Rename, visibility, default branch and topics only | Repository > Settings > General |
| Rulesets: read them | Read only inside merge readiness, with a link out | Repository > Settings > Rulesets (read-only list; editing stays on github.com) |
| Enable or disable a workflow | Not found | Workflow context menu; Item menu |
| Revert a merged pull request | Not found | PR context menu > More > Revert... |
| Security policy, private vulnerability reports, repository security advisories | Not found (an advisory credit appears only as a notification reason) | Repository > Security > Policy; Security > Advisories (roadmap GX11) |

### 14.2 Worth adding later (useful, less often)

| Feature | Status today | New home |
|---|---|---|
| Packages (GitHub Packages, container registry) | **Built 2026-11-18:** Repositories > My Packages, with Delete Package Version... and Delete Package... (`packages.py`); an organization's packages and restoring remain | Repository > Packages; Repositories > My Packages |
| Teams and organization members | Out of scope by a code comment ("Organizations in, Teams out"); roadmap GX13 adds team permissions. Now in scope: section 18.3.3 | Repositories > Organizations > org > Members, Teams; People > My Teams |
| Insights charts as tables: commit activity, code frequency, punch card | **Built 2026-11-18:** Repository > Insights > Commit Activity (`repo_activity.py`): weekly commits, code frequency, the ten busiest hours, participation and contributors, as sentences | Repository > Insights (tables, never charts only) |
| Dependency graph and software bill of materials (SBOM) export | **Built 2026-11-18:** Repository > Export Software Bill of Materials... (`Ctrl+Alt+B`), SPDX file (`runners_sbom.py`) | Repository > Security > Dependencies |
| Tags: create and delete outside a release | **Built 2026-11-18:** New Tag... and Delete Tag... (`tags.py`); annotated tags with a message, and Read Tag Message | Repository > Code > Tags context menu |
| Hide a comment (moderation: spam, off-topic, outdated) | Not found | Comment context in details > Hide Comment... |
| Transfer a repository | **Built 2026-11-18:** Repository > Transfer Repository... (`Ctrl+Alt+T`), typed confirmation (`repo_transfer.py`) | Repository > Settings > Transfer... |
| Self-hosted runners | **Built 2026-11-18:** Repository > Actions > Runners, read-only (`runners_sbom.py`); registering and removing stay planned | Repository > Actions > Runners (read-only) |
| Star lists | **Built 2026-11-18:** Repositories > Star Lists, New Star List..., Star Lists... on a repository, Rename or Delete Star List... (`star_lists.py`) | Repositories > Starred > each list |
| Your profile and status | **Built 2026-11-18:** Account > Set Your Status... (`user_status.py`); People > My Profile and each person's Profile (`profile.py`) | Account > Profile and Status... |

### 14.3 Brought in after all (Jeff, 2026-11-09: "If I can do it in GitHub I should be able to do it")

The first draft of this plan left these to github.com on purpose. Jeff's
brief overrules that: risk is answered with permission checks, previews and
typed confirmations (section 18.4), not by leaving a feature out. Each now has
a home and a Properties sheet:

- **Webhooks:** Repository > Settings > Webhooks, and the same for an
  organization. Create, edit the address, content type and events (every
  event GitHub offers, as a check list), turn on or off, see recent
  deliveries and their responses, redeliver, ping. The webhook secret is
  write-only: you can set a new one, never read the old one.
- **Deploy keys:** Repository > Settings > Deploy Keys. Add (title, key,
  read-only or read-write), delete. The key text is shown as GitHub shows it.
- **Autolink references:** Repository > Settings > Autolinks. Add a prefix and
  URL template (alphanumeric or numeric), delete.
- **Secret and variable values:** variables are read and written in full.
  Secrets stay write-only, as GitHub itself keeps them: Set Value... encrypts
  the new value with the repository's or environment's or organization's
  public key before it leaves the machine, and the value is never shown,
  logged, spoken or kept. Organization secrets also choose which
  repositories may use them (all, private only, or selected).
- **Billing and usage:** Account > Billing and Usage, read-only: Actions
  minutes, Packages and Codespaces storage, Copilot seats, as tables.
- **Organization audit log:** Organizations > org > Audit Log, read-only and
  filterable by actor, action, repository and date (needs `read:audit_log`
  and an organization plan that offers the API).
- **SSH and GPG keys, SSH signing keys:** Account > Keys. List, add, delete.
- **Personal access tokens:** an organization owner can review, approve and
  deny fine-grained token requests, and revoke access, under Organizations >
  org > Token Requests. Creating a token has no API, so Account > Tokens
  opens the right GitHub page and the Workbench checks the result
  (section 18.1).
- **Sponsors:** People > person > Sponsor, and Account > Sponsors for your
  own sponsorships and sponsors, read and manage what the API allows.

What is left on github.com is only what GitHub offers no API for, and the
coverage table says so row by row (section 19): Marketplace purchases,
creating a token, changing your password or two-factor settings, and
enterprise-level billing. Each still gets an "Open on GitHub" row in its
natural place.

### Appendix E. Cross-repository kinds and operations

Every row needs single-repository coverage, all applicable scopes, permission checks, preview/conflict handling and per-target results.

### 22.11 Across repositories: every kind of thing, by name, everywhere

Jeff, 2026-11-09: "can I handle all tags and labels in their own places and
not tied to a specific thing?", then "think broadly if other combinations
such as this exist." They do, and they share one shape.

**The pattern.** GitHub keeps many things inside one repository (a label, a
milestone, a tag, a secret, a webhook), but people think of them by name
across many: "the bug label", "the 2027.1 milestone", "the production
environment", "our CI workflow". So each such kind gets a place of its own,
above any one repository, where a row is a name and the sheet is that name
everywhere it exists.

**Where it lives.** A new top-level branch, **Across Repositories**
(Ctrl+0, and on the Go menu), with one child per kind:

| Kind | A row reads | What you can do everywhere at once |
|---|---|---|
| Labels | "bug: in 14 repositories, 3 colours, 2 descriptions, 212 open items" | rename everywhere; make colour and description the same (choose which variant wins); merge two labels into one (relabel every item, then delete the old one); copy to more repositories; delete everywhere; find every item with it |
| Milestones | "2027.1: in 9 repositories, due dates differ, 61 of 80 closed" | align title, due date and description; close everywhere; move open items to the next milestone everywhere; create in more repositories |
| Tags (Git) | "v3.2.0: in 4 repositories, on 4 different commits" | create a tag in many repositories (a release train); delete everywhere; compare what each points at |
| Releases | "3.2.0: published in 3, draft in 1" | publish all drafts together; edit notes together; list assets everywhere |
| Topics | "accessibility: on 22 repositories" | add or remove a topic on many repositories |
| Issue types | (already organization-wide) | listed here too, with where each is used |
| Branches | "main: default in 30 repositories, protected in 26" | find the 4 unprotected; rename a branch everywhere (with GitHub's redirects); delete merged branches of the same name |
| Rules and branch protection | "Main branch rules: 18 repositories, 4 variants" | make them the same; promote to one organization ruleset |
| Environments | "production: in 7 repositories, reviewers differ" | align reviewers, wait timers and branch policies |
| Secrets and variables (names) | "NUGET_KEY: in 11 repositories" | set a new value everywhere at once (write-only, section 14.3); delete everywhere; promote to one organization secret with those repositories selected |
| Webhooks | "https://hooks.example.org/ci: on 9 repositories" | change the address or events everywhere; turn off everywhere |
| Deploy keys and autolinks | by title or prefix | add to many, remove everywhere |
| Workflows | "ci.yml: 12 repositories, 3 versions of the file" | compare the versions; update every copy from one (as pull requests); run on all; turn on or off everywhere |
| Templates and community files | "Bug report form: 10 repositories, 2 versions" | make them the same (section 21.6); add the missing ones |
| Dependabot and CODEOWNERS | by setting or owner | align configuration; replace an owner everywhere |
| People | "kellylford: collaborator on 6, team member in 2" | the access matrix (section 18.3.2), from the person's side |
| Teams | (already organization-wide) | where each has access, and the role |
| Repository settings | "Allow auto-merge: on in 20, off in 8" | make any setting the same across many (merge methods, features, delete head branches, security features) |
| Saved replies, favorites, watch levels, stars | yours, across everything | manage in one list |
| Alerts | "lodash, high: in 5 repositories" | the security overview by package or rule; dismiss or fix everywhere |
| Packages and Pages | by name | visibility and access together |

**Scopes, the other half of every combination.** Each place works over a
scope you choose: every repository you can administer, one organization,
your own repositories, or a **Repository Set**, a named list kept in the
Workbench ("QuillVille family", "Docs sites"), made by hand or by a filter
(`org:Community-Access topic:quillville`). Sets appear under Across
Repositories and can be the scope of any batch anywhere in the Workbench.

**Differences are the point.** Every row says where the copies differ, and
the sheet's **Variants** page lists each variant with the repositories that
have it, so "make them the same" is a choice of which variant wins, shown in
the preview repository by repository. A **Missing From** page lists the
repositories in scope that lack it, with Add to These.

**Prefer what GitHub already shares.** Where GitHub has an organization-wide
form (organization rulesets, organization secrets and variables,
organization webhooks, issue types, custom properties, and default labels for
new repositories where its API offers them, to verify), the sheet offers
**Promote to Organization**, which creates the shared one and removes the
copies, with the preview.

**Kind by scope by operation.** Every kind in the table, over every scope,
with every operation the kind allows, is one row of the action table, so the
coverage of combinations is tested like everything else (GATE-GITHUB-COVER
counts a cross-repository operation as covered only when the single
repository one is).

### Appendix F. WordPress site-administration and cross-site inventory

This is the accepted source inventory. First-class adapters beyond the later approved plugin scope need an explicit delivery decision. Deferred adapters do not remove APIs from the accounting ledger. Original “to verify” labels remain unverified until evidence is attached.

#### 15.11 The third sweep: what running a real site also involves

Jeff, 2026-11-09: "anything else missing?" Each row gets a node or a sheet
page, and, where a plugin provides it, is reached through that plugin's REST
namespace when the site has one (section 12). Every plugin's API is marked
**to verify** until it has been checked against its documentation and a live
install on the test site; where no API exists, the row says what wp-admin
screen it opens, so nothing is a dead end.

| Area | What people need | Home | Through |
|---|---|---|---|
| Redirects | a redirect made automatically when a slug or address changes; a list of redirects to add, edit and test; the 404 log, so broken incoming links are found | Sites > site > Redirects; post Properties > Address | Redirection (`redirection/v1`), Yoast Premium, Rank Math; to verify |
| Backups | when the last backup ran, whether it worked, Back Up Now, restore points | Needs My Attention > Site Health; Sites > site > Backups | Jetpack Backup (`jetpack/v4`), UpdraftPlus and host tools; to verify; restore opens the plugin's screen |
| Security | failed sign-ins, blocked addresses, file changes, two-factor status of each user, plugin vulnerability alerts | Needs My Attention > Security; Users > each user's sheet > Security | Shield Security, Wordfence, Solid Security, Patchstack; to verify; vulnerability data for installed plugin versions from a public database only with consent |
| Abandoned plugins | a plugin not updated in two years, or closed on WordPress.org | Plugins, with a "Last updated" column and a Watch | the WordPress.org plugin directory API, with consent (an egress row) |
| Installing plugins | search WordPress.org and install, with ratings, active installs, last update and the accessibility of its admin screens where known | Plugins > Add New | core `wp/v2/plugins` installs by slug; search through the WordPress.org API with consent |
| Caching and speed | purge the cache after an update, per page or whole site; image optimization status; page speed as numbers, in words | Item > Clear Cache; Sites > site > Performance | WP Rocket, LiteSpeed Cache, W3 Total Cache, Jetpack Boost; to verify |
| Multilingual sites | each post's translations linked side by side, missing translations as a list, the language of each page, the language switcher | post Properties > Translations; Needs My Attention > Missing Translations | Polylang, WPML, TranslatePress; to verify; Mark Language (wordpress.md 12) already marks passages |
| Privacy requests | personal data export and erase requests, their status, Confirm and Complete | Needs My Attention > Privacy Requests | core keeps these as requests (their statuses are in the index); if no REST route exists on the site, they open wp-admin's Privacy screens |
| Consent and cookies | which consent tool runs, its categories and texts, checked for accessibility | Settings > Privacy | consent plugins; to verify |
| Email delivery | whether the site's email works, the mail log, Send Test Email | Site Health; Settings > Email | WP Mail SMTP, FluentSMTP, Post SMTP; to verify |
| Newsletters and subscribers | subscriber lists, new subscribers, send a post as a newsletter, open counts | Sites > site > Subscribers | Jetpack Newsletter, MailPoet, The Newsletter Plugin; to verify |
| Memberships | members, levels, expiry, payments, renewals due | Sites > site > Members; Needs My Attention > Renewals | Paid Memberships Pro (BITS runs it), MemberPress, Restrict Content Pro; to verify |
| Courses | courses, lessons, students, progress, quizzes | Sites > site > Courses | LearnDash, LifterLMS, Tutor LMS, Sensei; to verify |
| Event tickets and RSVPs | attendees, check-in as a list, capacity, refunds | Events > each event > Attendees | Event Tickets (The Events Calendar's family), WooCommerce Bookings; to verify |
| Shop, the rest | low stock as a Watch, subscriptions and their renewals, bookings, product reviews (wordpress.md 9.18 lists reviews as missing) | Shop | `wc/v3`; extensions to verify |
| Stats | views and visitors by page and day, top referrers, search terms, as tables and sentences | Sites > site > Stats | Jetpack Stats, Site Kit by Google, Independent Analytics; to verify |
| Search and sitemaps | the sitemap's contents, which pages ask not to be indexed, Search Engine Visibility in plain words | Settings > Reading; Sites > site > SEO | core `wp-sitemap.xml`, Yoast `yoast/v1` (in the index) |
| Social sharing | share a post when it publishes, to which accounts, with what text and alt text | post Properties > Sharing | Jetpack Social; to verify |
| Scheduled tasks | what WordPress plans to run and when, and anything overdue | Site Health > Scheduled Tasks | Site Health's information; WP Crontrol if installed; to verify |
| Someone else is editing | know before opening that another person has a post open, and take over only on purpose | the post's row and Properties | WordPress's post lock is held through its heartbeat, not REST; the Workbench checks `modified` and the lock where exposed, and says what it knows |
| Content audit | pages nobody links to, pages not updated in a year, duplicate titles, very long or very short pages, reading level, headings that skip a level | Needs My Attention > Content Audit; a report as a QUILL table | built from the content QUILL already reads, with Document Statistics' measures |
| Media housekeeping | unused media, duplicate files, very large files, video without captions, audio without transcripts | Media > Housekeeping | built from Media and its Usage page (Appendix A) |
| Moving in | importing from Blogger, Medium, Substack, Squarespace and WordPress export files | File > Import into Site... | the export file read on this computer, sent as posts and media over REST, with a preview |
| Moving out and archiving | a complete export (posts, pages, media list, terms, menus, settings) as files, and a static copy of the site for an archive | Site > Export... | REST reads; the standard export file is made on this computer |
| SSL and the address | the certificate's expiry date, the site answering on HTTPS, the address WordPress thinks it has | Site Health; Site Properties > Connection | read from the connection itself; a Watch at 30 days before expiry |
| Users, the rest | invite in bulk from a spreadsheet, sign a user out everywhere, see who has never signed in | People > Users | core `wp/v2/users`; sessions where exposed; to verify |
| Roles, edited | change what a role may do, and make new roles | People > Roles | only through a role plugin's routes (Members, User Role Editor); to verify; core REST cannot (section 11) |
| Collaboration | notes on drafts, assigning a draft to someone, and, on WordPress versions that add live collaboration, who is in a post now | Pending Review; post Properties > Notes | core notes (`block_notes.py` exists); live collaboration routes when WordPress ships them |
| Asking about the site | "Which pages mention our old address?", "Summarize this week's comments" | Item > Ask; Site > Ask About This Site | the family's Ask AI, over content QUILL already reads, never sending a site's private content without saying so |

#### 15.12 Across sites, and across the whole site: every kind of thing, by name

Jeff, 2026-11-09, on the GitHub PRD's section 22.11 ("handle all tags and
labels in their own places and not tied to a specific thing"): "this is also
true of WordPress where applicable." It is, in two directions.

**Within one site: things in their own places, not inside a post.** A tag or
category is edited today from a post's Properties or from Categories and
Tags. Each kind below gets its own node with every value it has, and its
sheet works on the value itself, wherever it is used:

| Kind | A row reads | What you can do |
|---|---|---|
| Tags, categories, every custom taxonomy's terms | "accessibility: 48 posts, 3 pages, 2 events" | rename and change slug (with a redirect for the archive address, 15.11); merge into another term; split (move some items to a new term); convert between taxonomies (a tag into a category); change parent; set term meta; delete with the items reassigned; list every item that uses it, of every type |
| Custom field values | "Venue: Main Hall, on 31 events" | find every item with a value; change it everywhere; find items missing a required field |
| Authors | "Sam: 120 posts, 4 drafts" | reassign many items to another author; find items by a former user |
| Pictures and files | "logo.png: used on 14 pages, in 2 menus, the site icon" | replace everywhere it is used; find where it is used before deleting (Media > Usage) |
| Patterns and template parts | "Footer: used by 3 templates" | where it is used; update all; detach copies |
| Links | "https://old.example.org: linked from 22 pages" | change every link at once (Site-wide Find and Replace, focused on links); find broken ones (15.11) |
| Shortcodes and blocks | "[gallery]: on 9 pages", "Columns block: on 40 pages" | find every use; convert a shortcode to its block; find blocks from a plugin about to be removed |
| Forms | "Contact: on 5 pages" | where it is used; replace with another form everywhere (13b.3) |

**Across sites: the same name on many sites.** A new top-level branch,
**Across Sites** (Ctrl+0, as in the GitHub Workbench), over every connected
site or a **Site Set** ("Client sites", "Family sites"):

| Kind | A row reads | What you can do everywhere at once |
|---|---|---|
| Tags, categories, custom terms | "Events: on 4 sites, 2 slugs" | align names, slugs and descriptions; create on the sites missing it; merge everywhere |
| Plugins | "Yoast SEO: on 9 sites, 3 versions, 2 inactive" | update everywhere; activate or deactivate; turn auto-updates on; remove everywhere; install on the sites missing it |
| Themes | "Twenty Twenty-Five: active on 3 sites" | update everywhere; compare global styles |
| Users | "Sam: Editor on 2 sites, Author on 1" | the access matrix from the person's side; change a role everywhere; remove everywhere with reassignment on each site |
| Settings | "Discussion: comment approval differs on 2 of 6 sites" | make any setting the same (time zone, permalinks, discussion rules, search visibility, privacy page); see where they drift |
| Menus and navigation | "Footer menu: on 5 sites, 3 versions" | compare and copy one to the others (section 15.2) |
| Patterns, starter pages, forms, content types | by name | copy one to every site; see where versions differ |
| Pages with a role | "Privacy policy: 6 sites, last updated from 2 to 30 months ago" | find the stale ones; update from one |
| Redirects, application passwords, spam senders | by address or name | block a spam sender on every site at once; revoke one application password everywhere |
| Health, backups, security, updates | by site | the Fleet view: every site in one list, read row by row ("Community Radio: health good, backed up today, 2 updates") |

**The same shape as GitHub's:** every row says where the copies differ, a
Variants page lists each variant and the sites that have it, a Missing From
page lists the sites without it, and "make them the same" is a choice of
which variant wins, previewed site by site. On a multisite network, where
WordPress has a network-wide form (network plugins and themes, super
admins), the sheet offers Promote to Network.

**Kind by scope by operation:** every kind, over every scope (one site, a
Site Set, every site, a network), with every operation the kind allows, is a
row in the shared action table, so the combination test (section 12a) and
the coverage gate cover it.

### Appendix G. API-family reconciliation checklist

The PRD operation appendices remain the detailed source. These family-level checkboxes are an index, not a substitute for method/route/field-level accounting. Snapshot totals are historical and must be refreshed.

#### GitHub REST and GraphQL families

- [ ] REST: actions (208 operations)
- [ ] REST: activity (34 operations)
- [ ] REST: agent-automations (12 operations)
- [ ] REST: agent-tasks (5 operations)
- [ ] REST: agents (30 operations)
- [ ] REST: apps (37 operations)
- [ ] REST: billing (13 operations)
- [ ] REST: branches (38 operations)
- [ ] REST: campaigns (5 operations)
- [ ] REST: checks (12 operations)
- [ ] REST: classroom (6 operations)
- [ ] REST: code-quality (4 operations)
- [ ] REST: code-scanning (25 operations)
- [ ] REST: code-security (20 operations)
- [ ] REST: codes-of-conduct (2 operations)
- [ ] REST: codespaces (48 operations)
- [ ] REST: collaborators (11 operations)
- [ ] REST: commits (14 operations)
- [ ] REST: copilot (44 operations)
- [ ] REST: copilot-spaces (28 operations)
- [ ] REST: credentials (1 operations)
- [ ] REST: dependabot (27 operations)
- [ ] REST: dependency-graph (5 operations)
- [ ] REST: deploy-keys (4 operations)
- [ ] REST: deployments (21 operations)
- [ ] REST: emojis (1 operations)
- [ ] REST: gists (20 operations)
- [ ] REST: git (13 operations)
- [ ] REST: gitignore (2 operations)
- [ ] REST: interactions (16 operations)
- [ ] REST: issues (66 operations)
- [ ] REST: licenses (3 operations)
- [ ] REST: markdown (2 operations)
- [ ] REST: meta (5 operations)
- [ ] REST: metrics (10 operations)
- [ ] REST: migrations (22 operations)
- [ ] REST: orgs (129 operations)
- [ ] REST: packages (27 operations)
- [ ] REST: pages (12 operations)
- [ ] REST: private-registries (6 operations)
- [ ] REST: projects (26 operations)
- [ ] REST: pulls (39 operations)
- [ ] REST: rate-limit (1 operations)
- [ ] REST: reactions (15 operations)
- [ ] REST: releases (13 operations)
- [ ] REST: repos (73 operations)
- [ ] REST: search (7 operations)
- [ ] REST: secret-scanning (17 operations)
- [ ] REST: security-advisories (14 operations)
- [ ] REST: teams (32 operations)
- [ ] REST: users (47 operations)
- [ ] GraphQL: activity (4 mutations, in scope)
- [ ] GraphQL: branches (4 mutations, in scope)
- [ ] GraphQL: checks (5 mutations, in scope)
- [ ] GraphQL: commits (1 mutations, in scope)
- [ ] GraphQL: copilot (5 mutations, in scope)
- [ ] GraphQL: dependabot (1 mutations, in scope)
- [ ] GraphQL: deployments (10 mutations, in scope)
- [ ] GraphQL: discussions (13 mutations, in scope)
- [ ] GraphQL: enterprise-admin (44 mutations, out of scope: enterprise and migration administration)
- [ ] GraphQL: git (4 mutations, in scope)
- [ ] GraphQL: issues (51 mutations, in scope)
- [ ] GraphQL: migrations (8 mutations, out of scope: enterprise and migration administration)
- [ ] GraphQL: orgs (11 mutations, in scope)
- [ ] GraphQL: classic projects (16 mutations, out of scope: these are classic Projects, which GitHub has retired in favour of Projects (version 2))
- [ ] GraphQL: packages (1 mutations, in scope)
- [ ] GraphQL: projects (32 mutations, in scope)
- [ ] GraphQL: pulls (36 mutations, in scope)
- [ ] GraphQL: reactions (2 mutations, in scope)
- [ ] GraphQL: repos (18 mutations, in scope)
- [ ] GraphQL: sponsors (9 mutations, in scope)
- [ ] GraphQL: teams (1 mutations, in scope)
- [ ] GraphQL: users (8 mutations, in scope)

#### WordPress recorded index families

- [ ] D.0 GraphQL
- [ ] D.1 Namespaces
- [ ] D: `wp/v2` (150 routes)
- [ ] D: `(index)` (2 routes)
- [ ] D: `baf/v1` (12 routes)
- [ ] D: `jetpack/v4` (18 routes)
- [ ] D: `oembed/1.0` (3 routes)
- [ ] D: `tec/migrations/v1` (6 routes)
- [ ] D: `tec/v1` (8 routes)
- [ ] D: `tec/v2/onboarding` (2 routes)
- [ ] D: `tribe/event-aggregator/v1` (3 routes)
- [ ] D: `tribe/events/v1` (15 routes)
- [ ] D: `tribe/views/v2` (2 routes)
- [ ] D: `wc-admin` (97 routes)
- [ ] D: `wc-admin-email` (5 routes)
- [ ] D: `wc-analytics` (89 routes)
- [ ] D: `wc-push-notifications` (2 routes)
- [ ] D: `wc-telemetry` (2 routes)
- [ ] D: `wc/pos/v1/catalog` (2 routes)
- [ ] D: `wc/private` (2 routes)
- [ ] D: `wc/store` (31 routes)
- [ ] D: `wc/store/v1` (31 routes)
- [ ] D: `wc/v1` (49 routes)
- [ ] D: `wc/v2` (72 routes)
- [ ] D: `wc/v3` (112 routes)
- [ ] D: `wccom-site/v3` (8 routes)
- [ ] D: `wp-abilities/v1` (6 routes)
- [ ] D: `wp-block-editor/v1` (4 routes)
- [ ] D: `wp-site-health/v1` (8 routes)
- [ ] D: `yoast/v1` (61 routes)

### Appendix H. Observed failing tests on PR #1837

Dated CI evidence from the audit session. Refresh before acting. Some failures may require correcting implementation, some stale test expectations, and some generated records; determine which from the intended contract. Never assume they are all snapshot-only.

- [ ] tests/unit/core/test_tutorial_catalogues.py::test_generated_book_matches_the_catalogue[quill]
- [ ] tests/unit/ui/wordpress/test_wp_workbench_window.py::test_the_door_always_opens_the_workbench
- [ ] tests/unit/ui/test_control_labels.py::test_the_report_names_the_worst_files_so_a_fixer_knows_where_to_start
- [ ] tests/unit/tools/test_surface_reachability.py::test_the_snapshot_is_current
- [ ] tests/unit/tools/test_surface_reachability.py::test_the_snapshot_on_disk_matches_the_tree
- [ ] tests/unit/tools/test_jev_eval_set.py::test_the_eval_set_is_current
- [ ] tests/unit/core/lite/test_lite_docs.py::test_every_bound_key_is_in_the_guide
- [ ] tests/unit/core/lite/test_lite_docs.py::test_every_command_name_is_in_the_guide
- [ ] tests/unit/ui/test_github_workbench_window.py::test_the_retired_dialogs_are_unreachable
- [ ] tests/unit/apps/test_lite_empty_window_menu.py::test_the_empty_window_in_workbench_mode_is_a_github_launcher
- [ ] tests/unit/core/test_user_guide_files.py::test_every_chapter_file_is_on_the_contents_page[docs]
- [ ] tests/unit/ui/test_main_frame_github_extras.py::test_notifications_open_the_shared_explore_triage_view
- [ ] tests/unit/tools/test_github_help_audit.py::test_every_github_window_title_has_a_purpose
- [ ] tests/unit/apps/test_lite_github_wave3.py::test_lite_gives_the_workbench_an_open_file_callback
- [ ] tests/unit/docs/test_no_tick_wording.py::test_no_check_box_is_ticked
- [ ] tests/unit/ui/test_main_frame_hosted_ai.py::test_ctrl_3_ctrl_4_and_ctrl_8_are_free_everywhere_else
- [ ] tests/unit/ui/forms/test_forms_ui_outline_rules.py::test_change_type_duplicate_and_remove
- [ ] tests/unit/core/wordpress/test_wp_workbench_leftovers.py::test_the_content_model_says_who_registered_each_type
- [ ] tests/unit/core/test_command_key_corpus.py::test_gate_corpus_every_offered_command_has_its_rows[quill]
- [ ] tests/unit/core/test_command_key_corpus.py::test_gate_corpus_every_offered_command_has_its_rows[lite]
- [ ] tests/unit/tools/test_jev_gateway_catalogue.py::test_the_snapshot_for_this_catalogue_version_is_current
- [ ] tests/unit/tools/test_jev_gateway_catalogue.py::test_the_gateway_asks_the_same_questions
- [ ] tests/unit/ui/test_accessible_name_inventory.py::test_inventory_snapshot_matches_source
- [ ] tests/unit/docs/test_github_guide_reach.py::test_every_contents_page_lists_all_twelve_chapters[userguide.md0]
- [ ] tests/unit/docs/test_github_guide_reach.py::test_every_contents_page_lists_all_twelve_chapters[github-guide.md]
- [ ] tests/unit/docs/test_github_guide_reach.py::test_every_contents_page_lists_all_twelve_chapters[userguide.md1]
- [ ] tests/unit/docs/test_github_guide_reach.py::test_every_contents_page_lists_all_twelve_chapters[lite-github-guide.md]
- [ ] tests/unit/ui/test_surface_lifetime.py::test_no_short_lived_surface_keeps_the_raw_task_manager
- [ ] tests/unit/apps/test_lite_github_last_four.py::test_lite_passes_its_document_to_new_gist
- [ ] tests/unit/tools/test_persistence_audit.py::test_no_unreviewed_persistence_sites
- [ ] tests/unit/tools/test_dialog_zorder.py::test_no_dialog_zorder_violations

### Appendix I. Closure review

- [ ] Current CI snapshot refreshed and all candidate blockers resolved.
- [ ] Accepted requirement IDs reconciled without omissions or duplicate closure claims.
- [ ] Every API operation has a disposition; every deferred operation has a reason and destination.
- [ ] Native UX, schema/console usability and acceptance completion reported independently.
- [ ] Both applications, account/site isolation and unsupported-host behavior verified.
- [ ] External dependency and packaged-runtime evidence attached.
- [ ] Live and manual accessibility acceptance signed off separately.
- [ ] Documentation and installed artifacts reflect actual released behavior.
- [ ] Product owner has a clear next-release boundary and later backlog.

### Appendix J. QuillVille WinGet and startup work (2026-11-12)

These release tasks are outside the WordPress and GitHub Workbench totals above.
Checked rows mean the local implementation or draft is present; platform and
public-release acceptance remains separately listed until it has evidence.

- [x] Add a WinGet catalogue, shared manifest templates, a local-only generator,
  validation guards, and draft manifest sets for the currently eligible QUILL
  Lite 1.1.2 and Quill Radio 3.0.4 Stable installers.
- [x] Add a fail-closed requirement for a verified HTTPS product page before
  generating another app's manifest.
- [x] Add a protected release workflow and API submitter. Public PR creation
  requires an explicit submit request, an approved catalog, a repository gate,
  an environment reviewer and an environment-only token.
- [x] Document how to onboard later apps and prepare their next Stable release
  in `docs/planning/winget.md`.
- [x] Add the family user-guide and release/announcement drafts for startup
  minimization and WinGet status; state that the packages are not public yet.
- [x] Add a separate start-minimized-at-sign-in preference to every app that
  already offers Start with Windows: QUILL, Radio, Cast, Weather, Inkwell and
  Transcribe. Normal launches remain windowed, and portable copies do not
  create login entries.
- [ ] Run the manifest tests and `winget validate` against the current upstream
  schema. The WinGet client and working Python environment were unavailable in
  this checkout.
- [ ] Dry-run the GitHub API submission against a disposable fork with a
  throwaway version; no submission token is configured in this checkout.
- [ ] Test install, app self-update, named WinGet upgrade, uninstall, and
  start-minimized behavior in Windows Sandbox or a disposable VM.
- [ ] Confirm permanent package IDs with the publisher and, after explicit
  authorization, submit and verify the public WinGet package PRs.
- [ ] Add each app's newly approved Stable package and product-page URL to the
  public user guides, versioned changelogs and release announcement.

**Primary delivery-checklist counts:** GitHub has 74 unchecked and 2 checked
items in §6; WordPress has 65 unchecked and 9 checked items in §7. These count
the top-level delivery checklist bullets only. Shared acceptance gates and the
more detailed requirement/API ledgers in §12 remain separate and are not
double-counted here.
