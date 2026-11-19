# Everything left to do for QUILL, in one list

**Owner:** Jeff Bishop / Community Access
**Trimmed:** 2026-11-18 to open work only. Everything done, every proposal not adopted, and the old source files (`complete2.md`, `wp_missing.md`, `how.md`, the delivery checklist, the design companion and the requirement ledgers) are in git history: `git log -- complete.md`.
**Rule:** this is the one place to track open work. Add to it rather than starting a new root file. When an item is built, delete it here and say so in the changelog.

## Pick up here

For whoever continues, person or AI. Jeff's log of every step is `D:\quill\claude.log`. The commands and gates are in `CLAUDE.md`.

- **Done on 2026-11-18:** five WordPress data-loss fixes (Send Back, Approve and Schedule, plugin Status, Gravity spam, Replace File, Put Back), Kelly Ford's diff marks (#1890), the Cast queue and download fixes for Chris Nova and Jessica Dail (#1889, #1892), every EdSharp item (#1891), and the Copilot SDK 2.0 source migration and requested feature work (#1893, including opt-in Auto routing; maintained design record in `docs/design/codex.md`). Clean Windows runtime verification remains open below.
- **Screen-reader testing** is done by Jeff's testers and is not tracked here.
- **Next:** Part 1 below, the GitHub Workbench: the endpoints are done (1.1); next the open features and checks (1.3), then the documentation pass (1.4).
- **How to work here:**
  - Squash-merge with `gh api -X PUT repos/Community-Access/quill/pulls/N/merge -f merge_method=squash`.
  - Log each step to `claude.log`, with the time read from a clock.
  - Run the gates the change touches, and `python -m quill.tools.platform_report` before a release.
- **Model use:** the endpoint batches are repetitive and suit a smaller model; keep the larger one for design and the documentation pass.

## The order of work

1. **The GitHub Workbench (Part 1)**, above everything else.
2. **WordPress (Part 2).**
3. **Other work (Part 3):** Copilot runtime verification, then Earshot parity.

## Part 1. The GitHub Workbench

### 1.1 Where it stands, and 1.2 the endpoints

Every operation in GitHub's API is now covered, needs no route of its own,
or is out of scope with its reason written down in
`quill/core/github/api_coverage.json`: the planned ceiling is 0. The last
272 were built on 2026-11-18 in batches 15 to 22 (#1895 to #1901 and
#1907), the last 116 of them as one table of single-call commands
(`quill/core/github/quick_tables.py`) that feeds the menus, the write
requirements, the live run and the coverage table. Out of scope by Jeff's
decision: GitHub Enterprise Cloud, company administration (billing, Copilot
seats, private runner networking, migrations, paid Advanced Security),
Copilot Spaces, GitHub Classroom and the preview features listed in the
table. The Copilot cloud agent's APIs are a public preview; their commands
send only what GitHub documents and show GitHub's own answer, so they need
a live run on a Copilot plan before anyone relies on them (1.5).

### 1.3 Not endpoints: features and checks still open

The endpoint count is not the whole job. These rows from the Workbench delivery checklist are still open; several are partly done, as their notes say. Each is done only with evidence: a test or a live run.

#### Features and verification

- [ ] Complete Appendix A/B “nothing dropped” mapping and Appendix C object/sheet/filter mapping.
- [ ] Verify every editable field, mixed value, field removal, batch operation, conflict resolution, verify-after-save, history and supported undo/redo.
- [ ] Preserve issue types and organization-defined issue fields as typed values on issue rows, details, filters and Properties. Hidden, unsupported, unset, empty and unreadable values stay distinct.
- [ ] Repository and item-property checklists expose state in the row; Space changes it once, Enter saves, focus returns predictably, and JAWS/NVDA/VoiceOver do not hear a duplicate row.
- [ ] Verify project fields/views, branches/rulesets/protection, releases/assets, Actions, security, account/organization objects and team lifecycle.
- [ ] Verify per-account Read Only/Organize/Full, Safe Mode, tiers, typed confirmations, self-lockout prevention and permission explanations.
- [ ] Verify encrypted write-only secrets for repository/environment/organization scopes and selected-repository access.
- [ ] Verify View As Role, Compare Roles, Why Can't They?, My Access Here, access reviews and bulk changes against actual server authority.
- [ ] Complete all-attribute filters, Show Only/Hide, grouping, sorting, columns, Load More/All and honest local-filter scope. *(2026-11-18: Load More works on every list and Load All reaches the Explore-backed nodes; a partial list says so in the Items cell. Remaining: grouping, sorting and the column chooser beyond issues and pull requests.)*
- [ ] Plain-language query/batch commands through the shared catalogue, with resolved targets, editable previews and deterministic non-AI paths.
- [ ] Compare Accounts and one-action Act As with unambiguous identity and cache isolation.
- [ ] Role comparison and learning workflows reach real permission evidence, not guessed privileges.
- [ ] Issue close reasons, development links, branch creation for an issue, task-list editing/conversion, organization issue fields. *(Done 2026-11-17 except organization issue fields: Close or Reopen asks the reason, duplicate included; Linked branches on the issue sheet; Create Branch for This Issue; Check or Uncheck a Task; Convert Tasks to Sub-issues. `issue_development.py`, `github_workbench_development.py`; tests `test_issue_development.py`, `test_github_workbench_development.py`. Unlinking a branch is not built.)*
- [ ] Saved replies, repository invitations, wiki and cross-linked discussion → issue → PR workflows. *(2026-11-18: saved replies insert in every comment box; repository invitations listed, accepted and declined (`repo_invitations.py`). Remaining: wiki, cross-linked workflows.)*
- [ ] Repository General/features, complete creation/template options, transfer, standalone tags, topics and star lists. *(2026-11-18: standalone tags made and deleted (`tags.py`).)*
- [ ] Rulesets/protection management, organization/member/team access, custom roles and audit logs.
- [ ] Webhooks and deliveries/redelivery/ping; deploy keys; autolinks; organization secret/variable repository selection.
- [ ] Account profile/status, SSH/GPG/signing keys, token-request administration, billing/usage and Sponsors where APIs permit. *(2026-11-18: status set and cleared (`user_status.py`).)*
- [ ] Workflow enable/disable and accessible workflow authoring; triggers/jobs/steps/inputs/permissions/dependency graph as linear controls. *(2026-11-18: enable and disable on the sheet and as Turn Workflow On or Off... (`workflow_state.py`). Remaining: authoring.)*
- [ ] Dependabot configuration and PR commands; CODEOWNERS editing/ownership lookup.
- [ ] Merge queue as a place; required policy explanation, auto-merge and batch merges of independently eligible PRs. *(2026-11-17: Repository > Merge Queue, Why Can't I Merge? with every blocker for the exact head commit, Merge merging only the commit it checked, Auto-Merge... and Add to or Remove from Merge Queue... on the row (`merge_readiness.py`, `merge_queue.py`, `github_workbench_merge.py`). Remaining: batch merges.)*
- [ ] Commit statuses, environments, deployment protection and release/deployment evidence. *(2026-11-18: Set Status... on a commit (`commit_status.py`).)*
- [ ] Packages, runners, dependency graph/SBOM, insights/network/traffic/contributions as readable tables. *(2026-11-18: Runners, read-only, and Export Software Bill of Materials... (`runners_sbom.py`); Commit Activity as tables (`repo_activity.py`); My Packages (`packages.py`).)*
- [ ] Git LFS storage/locks and account/organization export or migration capabilities with correct scope dispositions.
- [ ] Copilot sessions/review/configuration/organization administration and GitHub Models prompt/evaluation files, wherever actual APIs allow.
- [ ] Installed/authorized Apps, repository grants, install requests, suspend/unsuspend and OIDC subject templates.
- [ ] Code/secret scanning, advisories, private reports, bypass/dismissal requests, Autofix/dependency review and organization security overview.
- [ ] Discussion polls, spotlight and category sections.
- [x] GitHub service status with opt-in network access and a useful explanation. *(2026-11-18: Help > GitHub Service Status... (`Ctrl+Alt+F1`) reads www.githubstatus.com after asking once, never on its own or in Safe Mode, and says the overall status, the parts not working and any incident with its latest update (`service_status.py`, `github_workbench_service_status.py`).)*
- [ ] gh sign-in reuse as an additional account path; enterprise hosts and API-version differences.
- [ ] Least-privilege advice based on observed usage with honest uncertainty; artifact attestations and immutable release evidence.
- [ ] First-class by-name collections for every kind in PRD 22.11, not only items inside a repository. *(Partly, 2026-11-13: Labels, Milestones, Topics and Rules and Branch Protection by Name, and the Fleet, under Across Repositories; every other kind is a decided, test-backed cell with its reason in `quill/core/github/across_scope_matrix.py`.)*
- [ ] Tags/releases/topics/branches: release trains, comparison, publishing, feature-specific safeguards. *(Partly, 2026-11-13: topics are added to the missing or removed everywhere, keeping each repository's other topics; tags, release trains and branch renames remain.)*
- [ ] Rules/protection/environments/secrets/variables/webhooks/keys/autolinks: align or promote to organization when actually supported. *(Partly, 2026-11-13: rulesets and default-branch protection align (who may push is never copied, protection is never removed this way), a ruleset is added where missing, and Promote to Organization makes one organization ruleset and deletes the copies only after it exists. Labels cannot be promoted: GitHub has no organization-label API. Environments, secrets, variables, webhooks, keys and autolinks remain, each classified in `quill/core/github/across_scope_matrix.py`.)*
- [ ] Workflow/template/community/Dependabot/CODEOWNERS content: compare and update through reviewable PRs.
- [ ] People/teams/settings/custom properties/issue types: access and setting matrices with inherited-role explanations.
- [ ] Saved replies/favorites/watch levels/stars, alerts/packages/Pages where supported.
- [ ] Cross-repository coverage is complete only when the corresponding single-repository operation and batch behavior are complete; read-only category views are tracked separately from multi-target writes.
- [ ] GX09 policy-aware merging; GX10 release/deployment evidence.
- [ ] GX11 security/dependencies; GX12 collaboration/knowledge; GX13 administration.
- [ ] GX14 workspace/service handoffs; GX15 optional grounded assistance; GX16 category-first cross-repository browsing.
- [ ] Apply provider-neutral patterns: read long issue/PR/discussion threads as one structured page; preserve the selected row on return; say the actual outcome once through QUILL's existing feedback settings.

#### Additions from the 2026-11-13 audits

- [ ] **Documentation pass at the end of each delivery batch.** Release notes, announcements, What's New, both PRDs and their status page, the QUILL and QUILL Lite user guides, the GitHub guide and the WordPress and Forms guide, with regenerated HTML and EPUB siblings, written in Jeff's voice and matching what shipped.

#### Requirement audits

About 99 GitHub requirement ids (GH-R-001 onward) were never checked off against the code. They are defined in `docs/Product Requirement Documents and Specifications/github-workbench-prd.md`; the checklist that listed them is in git history. Verify each against the code and tests, a section of the PRD at a time, and record the evidence in `docs/qa/`.

### 1.4 Then: documentation as good as WordPress's

When 1.2 and 1.3 are done, the GitHub Workbench's documentation is brought up to the WordPress standard: the GitHub Guide's chapters in both editors, F1 help, the GitHub PRD, the release notes and the live-run rows, all rendered and checked. Until then, batches are written up in both changelogs only, by Jeff's choice.

### 1.5 Waiting on Jeff

- Run `python docs/qa/github-live-run.py --create` after signing in again, and the live rows marked "needs Jeff".
- Live validation:
- [ ] GitHub live scenarios: multiple roles/accounts, protected branches, organization restrictions, rate limiting, private repositories, project fields, secrets, failure/retry and no-API fallbacks.
- [ ] WordPress current candidate: run the documented live regression on an authorized test site and distinguish existing site-side failures from regressions.
- [ ] Seed QAF, Gravity Forms, PMPro, custom types/taxonomies/meta, constrained roles and realistic media/content for the supported scope.
- [ ] Verify taxonomy discovery, nested fields, block notes, upload/chunking/regenerate sizes, media listening/watching and contributor restrictions where still unverified.
- [ ] Reconcile “90 pass / 4 site-side fail” from earlier branches with fresh final-candidate results; do not inherit old green evidence.
- [ ] WordPress.com onboarding: confirm application/client registration and the current OAuth path if still incomplete.
- [ ] Audit external QAF/BAF/Site Types branches, names, release state and dependency contracts before relying on historical “waiting on Jeff” notes.
- [ ] Verify packaged app behavior, not only source runs; include clean/offline Practice Site launch.
- [ ] Manual acceptance stays separately signed off by the user/testers; every blocked scenario names the missing environment or permission.

## Part 2. WordPress

### 2.1 Decisions (Jeff, 2026-11-18)

- **Updates:** stay in the WordPress Dashboard. QUILL opens Dashboard > Updates; no WP-CLI, MainWP or Jetpack.
- **Backups:** snapshots and WXR (WordPress's export file) only.
- **Security:** no Security Review for now.
- **Plugin scope:** WooCommerce and Yoast are in, with QAF, Gravity Forms and Paid Memberships Pro. **To do:** update the WordPress PRD and `docs/design/wordpress.md` to say so.
- **Rank Math:** read only (assumed; Jeff did not answer).

### 2.3 Missing in QUILL

The most useful to a site owner come first in each area. "Route" means the REST route that does it. "wp-admin" means there is no route.

##### Media

- **Scale, crop or turn a picture on this computer, and send it back:** built 2026-11-18 (Edit Picture's last choice). What stays wp-admin only: the site-wide media size settings (thumbnail, medium and large widths), because WordPress does not expose them to REST.

##### Forms

QAF is covered end to end: build, publish, settings, status, delete, entries, views, spam and spam settings, and so is Gravity Forms, notifications and confirmations included (2026-11-18).


Gravity Forms' own settings, add-ons and licence are wp-admin only.

###### Payments in QUILL Accessible Forms (QAF)

Square and more than one payment connection per provider are built in both
editors (#1906) and in the QAF plugin (quill-accessible-forms #1, contract
version 2): Square through its Web Payments SDK and Payments API, named
connections chosen by the payer or by rule with a required otherwise, Check
This Form finding rules that can never fire, publishing refusing a missing,
unfinished or wrong-mode connection, and refunds through the connection that
took the money. What is left needs the test site and a person:

- **Square and connections on a real site.** On the test site's sandbox: a
  Square payment, a declined card (4000 0000 0000 0002), a refund, and a
  webhook replay, with the receipt and the entry showing the same amount and
  status; then a form with two Stripe connections, a PayPal and a Square
  routing a test payment by each kind of rule, and each refund returning to
  the account that took it.
- **Square's card field with a screen reader**, before any live use: NVDA
  and JAWS on Windows, VoiceOver on macOS and iOS (the field is Square's
  iframe, so this is a check of Square's markup, with QAF's group label and
  status messages around it).
- **Per-connection test or live mode.** Today the site's one mode covers all
  its connections, which is what keeps a form from mixing them. If a site
  needs a live connection beside a test one, the contract already reports
  `test_mode` per connection.

##### Shop (WooCommerce)

- **Create an order, or change its items and addresses.** Who: shops taking phone orders. Route: `POST wc/v3/orders`, `POST wc/v3/orders/{id}`.

Many products can now be changed at once (Change Many Products..., `products/batch`, 2026-11-18). Also missing but less urgent: generating variations (`products/{id}/variations/generate`), shipping classes (`products/shipping_classes`), and Analytics (`wc-analytics/reports/*`). Scheduled Actions and the extensions marketplace are wp-admin only. Subscriptions and Bookings are paid extensions with their own routes, not in scope.

##### SEO (Yoast SEO)

- **Canonical address, primary category and schema type per post.** Route: only where Yoast registers that post meta for REST, which most sites do not. I have not verified which of these the bulk editor routes carry. Otherwise they stay in the post's Yoast panel.

##### Memberships (Paid Memberships Pro)

- **Create or edit a membership level.** Who: the site owner changing a price or adding a tier. Route: PMPro's abilities, if the site offers a level-writing one, or `pmpro/v1/membership_level` (I believe it takes POST, unverified). Today levels are read only.
- **Members of a level, as a list.** Who: the owner emailing or counting one tier's members. Route: unverified. `pmpro/v1/recent_memberships` exists. Otherwise build it from users plus each person's levels, which is slow on big sites. Today you see a person's memberships one person at a time.
- **Every discount code, as a list.** `pmpro/v1` reads one code at a time. The list works only where an ability offers it, and otherwise opens wp-admin, which QUILL says.

##### Redirects (Redirection)

List, add, change, turn on and off, delete, test an address, and the 404 log are built from Redirection's documentation and have never met a real install.

- **Redirection's options.** Route: `redirection/v1/setting` (from the plugin's docs, unverified). They stay in the plugin's own screen for now. Groups, import and export were built 2026-11-18: groups through `group` and `bulk/group`, import and export on this computer through the redirect routes already used (the plugin's own import takes an uploaded form file).

##### Maintenance

- **Missed scheduled tasks beyond posts.** Search and Upkeep lists posts still Scheduled after their time. No other WP-Cron task is visible to REST. WP Crontrol is named as the plugin that lists them. I do not know that it has a REST API (unverified).

### 2.4 Built but not yet tried live

All of the following has tests over recorded or fake answers and none has met a real site. The checklist is `docs/qa/wordpress-regression-testing.md` (the Workbench section and the Live run section), and wordpress.md section 19 keeps the list.

- The whole Workbench, W1 to W8 and packages 1 to 14. It is now the default, so this comes before the next release.
- WooCommerce, The Events Calendar and Yoast SEO, signed in on the test site, which has all three. A refund only against a gateway's test mode.
- Redirection, and the slug-change redirect offer, and Redirect Groups (new, rename, turn off, delete) and Import Redirects.
- QAF on the test site (it still runs BAF), the QAF migration, and the spam settings with a live submission.
- Gravity Forms building, conversion, feeds, results and test submissions. These need a licensed Gravity Forms with its REST API on.
- Paid Memberships Pro 3.9 or later on WordPress 6.9 or later, with a role whose PMPro capabilities were changed.
- Advanced Custom Fields read and write, and the QUILL Site Types plugin in a real WordPress.
- Copy to Site and Compare Sites between two real sites, and Promote to Network on a real multisite.
- The Practice Site from an installed build, not only from source.
- WordPress.com sign-in, which waits on the app's client ID.

### 2.5 Open rows from the WordPress delivery checklist

- [ ] Confirm QAF namespace/name migration and compatible persisted form models across both repositories. *(2026-11-13: both halves are built and tested; what is left is the live run. QAF (S:\code\qaf, uncommitted): QAF_Migrator is now versioned (qaf_migration_version, steps 1 and 2, each once, under a lock) and runs early on plugins_loaded on any request, before the activator can make empty tables or a submission land in one. Step 1 renames tables, copies options, moves meta and adds role capabilities; step 2 moves baf_ cron events, rewrites wp:baf/ blocks and [baf_ shortcodes in posts and widget options (same length, so serialized values stay valid), turns a saved form's extensions.baf_legacy into qaf_legacy, and gives users their own qaf_ capabilities. baf/form renders as an alias, .baf files open, baf/v1 stays a read-only alias; README has the rollback steps. Tests: tests/unit/Model/RenameCompatTest.php (16). QUILL: qaf_site.site_namespace prefers qaf/v1 and falls back to baf/v1, and the Spam page and its commands say which the site runs (workbench_qaf_spam_edit.namespace_note). Open: deploy QAF to the test site, which still runs BAF, and check its forms, entries, pages and Forms node after the migration.)*
- [ ] Install supported QAF/Gravity Forms/PMPro versions on authorized test environments and record exact versions/capabilities. *(2026-11-13: needs an authorized test site with QAF, Gravity Forms 2.x with REST API v2 enabled, and PMPro 3.9+ on WordPress 6.9+, plus an account per role.)*
- [ ] QAF spam dependencies: hold-never-drop, identical visitor confirmation, no behavioral rejection, reasons/provider reporting, blocklist/thresholds/question bank. *(2026-11-13: QAF's PHPUnit suite now runs (composer.json with PHPUnit 9.6 in S:\code\qaf; `vendor/bin/phpunit`, mbstring needed): 552 tests, 0 failures, from 509 with 95 errors and 16 failures before. tests/unit/Spam (122) proves all five, plus the new settings, question bank and weeks routes (SpamSettingsWriteTest.php). QUILL uses them: Spam and Not Spam go through entries/{id}/spam and /not-spam, and a held entry's row gives QAF's reason (tests/unit/core/wordpress/test_wp_qaf_spam_core.py). Open: a live submission on the test site once QAF is deployed there.)*
- [ ] Verify WP 6.9+/PMPro 3.9+ behavior and customized capabilities; no sensitive card/billing fields leak into lists. *(2026-11-13: the leak half is done. Every PMPro row, member read and subscription has card and billing fields stripped, nested or not (without_payment_details in workbench_pmpro_change.py), tested above. Open: needs WordPress 6.9+ with PMPro 3.9+ live, and a role with customized PMPro capabilities.)*
- [ ] Payment dependency: plugin tests, Stripe test mode, PayPal sandbox, webhook authenticity/replay/order, duplicate submission and accessible checkout acceptance. *(2026-11-13: needs QAF's and PMPro's PHP suites, a Stripe test-mode account, a PayPal sandbox and a reachable webhook endpoint on the test site.)*
- [ ] Include the workspace's untracked `scripts/wp_playground/package-lock.json` with the source change before release. *(Verified 2026-11-13: the lock matches package.json and the 3.1.64 pin, every package is registry-resolved with a sha512 hash, it is byte-identical to the staged cache's lock, and `_lock_matches_packages` makes the build use `npm ci` from it; `tests/unit/scripts/test_wp_playground_lock.py` keeps it so. Still untracked: it lands with the next commit.)*
- [ ] Run start/connect/reset/stop/restart using the bundled Node and payloads on a clean installation. *(Source run done 2026-11-13 with the staged Node 24.22.1, CLI 3.1.64, PHP 8.3 and WordPress 7.1.4, from an empty data folder: first start 111-168 s, restart 46 s, stop, Workbench close, reset and start-after-reset all pass. It found and fixed three blockers: Playground listened on every interface, `--login` answered every REST call with a 302, and WordPress refused the app password over HTTP. Still open: the same run from an installed build.)*
- [ ] Redirects: verify the existing slug-change offer live; classify redirect lists/edit/test/404-log operations. *(Partly 2026-11-13: Sites > site > Redirects and 404 Log list, add (Ctrl+N), change, turn on/off, delete and test through `redirection/v1`; the slug-change offer path is verified in code and by a test; routes classified covered. Live check against a Redirection install remains; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [ ] Backups, restores, security/sign-ins/2FA/vulnerability data, caching/performance, multilingual content, consent, email, newsletters, courses, event attendance, analytics and social sharing: account for discovered APIs, and separately decide first-class integration priority. *(Partly 2026-11-13: each is a `THIRD_SWEEP` row with a disposition per site (discovered namespace -> More from This Site, else Open in Dashboard) and the Administration Areas node; the first-class priority decision remains Jeff's; S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*

### 2.6 The WordPress UX review: done

Every item from the review of 2026-11-14 is fixed (the walkthrough is `docs/design/wordpress-ux-walkthrough.md`; the items and their fixes are in git history and the CHANGELOG). The safety items by #1837 and the WordPress safety pull request; items 26 to 37 and 1, 15, 16, 20, 25 and 30 by the 2026-11-18 pull requests #1902 to #1921. Two calls are left to Jeff: whether page commands such as Check This Page should have a WordPress-layer key (they have a written reason, `wordpress/menu_unbound.py`), and whether menu items want a Workbench tree node beside the Menus window's Undo.

## Part 3. Other work

- [ ] **Copilot SDK 2.0 runtime verification:** build the QuillVille Runtime from a clean Windows environment, regenerate `standalone/runtime/runtime-inventory.json` with `python scripts/check_runtime_inventory.py <dist-dir> --write`, and verify the resulting inventory contains Microsoft Copilot SDK 2.0.1 but no `github-copilot-sdk` 1.x package. The committed inventory still names the legacy 1.x distribution; keep its notice entry until this build is verified.

### 3.1 Earshot parity, what is left

`ear.md`, the Earshot round-two review of 2026-11-15, was built in full (#1845, #1846) and its plan of record is `docs/design/earshot.md`. What it left:

- [ ] **Listen to the three compression levels** on quiet and loud speech, and decide whether turning compression on should keep starting at Light (a little gentler than the old fixed -18 dB, 3:1).
- [ ] **Sound Enhancements window:** a strength choice in the window itself, which means changing the editor Quill Radio shares; waits for a reason.
- [ ] **Round three** starts from Earshot `c11dda93`: when Earshot's Listening Places starts reading other devices' files, check the records Cast writes against what it expects.

### 3.2 Design decisions still open (from the design companion)

These are prioritization decisions for later; they do not block producing this document.

1. Choose two packaged-app pilots and the real users/tasks to observe.
2. Confirm whether to start with truthful results/stable lists or a more urgent observed lost-work/input issue.
3. Choose one cross-app journey to make exceptional before adding more handoff types.
4. Confirm the shared behavior boundaries, especially audio ownership, preferences and target-app text insertion.
5. Promote only the accepted proposals into the relevant product PRDs and release backlogs.

**My recommendation:** start by making the family dependable at the transitions—between tasks, between apps, between devices, and between a command and its result. That is where a small change can make the whole family feel more thoughtful.
