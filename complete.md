# Everything left to do for QUILL, in one list

**Owner:** Jeff Bishop / Community Access
**Trimmed:** 2026-11-19 to open work only. Everything done, every proposal not adopted, and the old source files (`complete2.md`, `wp_missing.md`, `how.md`, the delivery checklist, the design companion and the requirement ledgers) are in git history: `git log -- complete.md`.
**Rule:** this is the one place to track open work. Add to it rather than starting a new root file. When an item is built, delete it here and say so in the changelog. Partly built items keep only what is left.

## Pick up here

For whoever continues, person or AI. Jeff's log of every step is `D:\quill\claude.log`. The commands and gates are in `CLAUDE.md`.

- **Screen-reader testing** is done by Jeff's testers and is not tracked here.
- **Where it stands (2026-11-19, night):** merged today: every PR from #1943 to #1957. Open: #1958 (Cast lists that stay still), #1959 (workflow authoring, Dependabot, CODEOWNERS), #1960 (sort, group, place kept, plain-language batch), #1961 (rulesets, members, teams, access matrices; Enterprise Cloud-only parts being removed). Paused by the usage limit, to be resumed: roles and accounts, Across Repositories, repository administration, wiki/collaboration/Copilot, and the GH-R items not met. Rule (Jeff): nothing Enterprise Cloud only; organization-only checks run in a test organization.
- **Next:** finish 1.3 smallest first, then the documentation pass (1.4), then the rest of 2.3 and 3.2. A tester's defect report always comes first.
- **Live testing waits until all code is done (Jeff, 2026-11-19).** That covers the WordPress test site over SSH (`ssh lp.csedesigns.com`, wp-cli through `~/app/wordpress-test/wpcli.sh`, which needs more PHP memory), installing QAF and the other plugins, the GitHub test repository, and the 1.5 and 2.4 rows. Gravity Forms waits until later.
- **How to work here:**
  - Squash-merge with `gh api -X PUT repos/Community-Access/quill/pulls/N/merge -f merge_method=squash`.
  - Log each step to `claude.log`, with the time read from a clock.
  - Run the gates the change touches, and `python -m quill.tools.platform_report` before a release.
  - When an item lands, delete it here in the same pull request.

## The order of work

1. **A tester's defect report**, whenever one arrives.
2. **The GitHub Workbench (Part 1)**, code first.
3. **WordPress (Part 2)**, code first.
4. **Other work (Part 3):** the family UX pilots and the Copilot runtime build. (Earshot parity was taken off the list by Jeff, 2026-11-19.)
5. **Then all live testing:** 1.5, 2.4 and 2.5, the test site and the GitHub test repository.

## Part 1. The GitHub Workbench

Every GitHub API operation is covered, needs no route of its own, or is out of scope with its reason in `quill/core/github/api_coverage.json` (planned ceiling 0). The Copilot cloud agent's commands use a public preview API and need a live run on a Copilot plan before anyone relies on them (1.5).

### 1.3 Features and checks still open

Each is done only with evidence: a test or a live run.

#### Features and verification

- [ ] Complete Appendix A/B "nothing dropped" mapping and Appendix C object/sheet/filter mapping.
- [ ] Verify every editable field, mixed value, field removal, batch operation, conflict resolution, verify-after-save, history and supported undo/redo.
- [ ] Edit issue fields directly on the Properties sheet's Issue Fields page (today read only; Issue Fields... on the row edits them).
- [ ] Verify project fields/views, branches/rulesets/protection, releases/assets, Actions, security, account/organization objects and team lifecycle.
- [ ] Live check on the GitHub test repository: Read Only, Organize, Full and Safe Mode refuse and allow as tested, and the permission explanations (greyed rows, Shift+F1, GitHub's own refusals) match what GitHub does.
- [ ] Verify View As Role, Compare Roles, Why Can't They?, My Access Here, access reviews and bulk changes against actual server authority.
- [ ] Compare Accounts and one-action Act As with unambiguous identity and cache isolation.
- [ ] Role comparison and learning workflows reach real permission evidence, not guessed privileges.
- [ ] Wiki, and cross-linked discussion → issue → pull request workflows (saved replies and repository invitations are done).
- [ ] Repository General/features, complete creation/template options, transfer, topics and star lists (standalone tags are done).
- [ ] Copilot sessions/review/configuration/organization administration and GitHub Models prompt/evaluation files, wherever actual APIs allow.
- [ ] gh sign-in reuse as an additional account path; enterprise hosts and API-version differences.
- [ ] First-class by-name collections for the PRD 22.11 kinds still "not yet" in `quill/core/github/across_scope_matrix.py`: workflows, templates, Dependabot and CODEOWNERS, people, settings and packages.
- [ ] Saved replies/favorites/watch levels/stars, alerts/packages/Pages where supported.
- [ ] Cross-repository coverage is complete only when the corresponding single-repository operation and batch behavior are complete; read-only category views are tracked separately from multi-target writes.
- [ ] GX12 collaboration/knowledge; GX13: account-aware repository switching (Compare Accounts and Act As, still open).
- [ ] GX09: Why Can't I Merge? and Merge Selected... do not yet name the specific ruleset or CODEOWNERS rule that blocks (only the review window's Check Merge Policy does), and nothing watches a pull request to say when its readiness changes.
- [ ] GX10: attestation signatures are not verified in QUILL (it points to gh attestation verify), and a downloaded release file is not checked against its digest.
- [ ] GX14 workspace/service handoffs; GX15 optional grounded assistance.

#### Documentation at the end of each delivery batch

- [ ] Release notes, announcements, What's New, both PRDs and their status page, the QUILL and QUILL Lite user guides, the GitHub guide and the WordPress and Forms guide, with regenerated HTML and EPUB siblings, written in Jeff's voice and matching what shipped.

#### Requirement audit: what is still open

The record is `docs/qa/github-workbench-requirement-audit-2026-11.md`: 82 of 100 GH-R ids met, 11 partly met, 7 not met; every Must is at least partly met.

- [ ] **The rest of PRD 16.7:** a menu row for Subscribe and Block, star lists, Fork and Pin and Favorite on the You page, sponsoring a repository's owner from the repository, blocking from an organization, leaving an organization and answering an invitation, reactions on comments, and commits.
- [ ] **GH-R-150 and 151:** more kinds under Across Repositories (see the by-name collections row above).
- [ ] **Shoulds and Mays:** Alt+Enter on a GitHub reference in a document (036), real permission evidence for the role views (069), the branch rule tutorial (105; the ruleset and branch protection editing it needs is now in, #1961), own-data examples (109), a short braille row (114), key cards and the spoken tour (115), QUILLBert and QUILLBee tips (116) and Ask How (118).

### 1.4 Then: documentation as good as WordPress's

When 1.3 is done, the GitHub Workbench's documentation is brought up to the WordPress standard: the GitHub Guide's chapters in both editors, F1 help, the GitHub PRD, the release notes and the live-run rows, all rendered and checked. Until then, batches are written up in both changelogs only, by Jeff's choice.

### 1.5 Waiting on Jeff and the testers

- [ ] Run `python docs/qa/github-live-run.py --create` after signing in again, and the live rows marked "needs Jeff".
- [ ] GitHub live scenarios: multiple roles/accounts, protected branches, organization restrictions, rate limiting, private repositories, project fields, secrets, failure/retry and no-API fallbacks; the Copilot cloud agent commands on a Copilot plan.
- [ ] Vote... in a real discussion poll, and the Pinned (spotlight) place, on the test repository.
- [ ] Edit Workflow..., New Workflow... and Compare Configuration... on the test repository (each through a pull request, then closed); Dependabot Commands... on a real Dependabot pull request, and whether GitHub still accepts `@dependabot merge`, `squash and merge`, `cancel merge`, `close` and `reopen`.
- [ ] Secrets on the test repository (create, change, list shows only the name, delete); Dependency Review on an open pull request and Security Overview on an organization repository; an organization secret in Community-Access set to selected with a repository added and removed, then back to private (confirms a visibility-only change is accepted); Allow a Blocked Secret... needs a real blocked push and its placeholder id.
- [ ] Issue types and fields in an organization that has them: typed values in the Issue fields column (a date, a number, a choice), `type:Bug` and `field.priority:high` searches, the Properties Issue Fields page, "hidden from you" for an account that cannot see fields, a person's repository (`/user/issue-fields`).
- [ ] Merge Selected... on two throwaway pull requests, and Release Evidence on `v0.0.1-quill-live`, on the test repository; Merge Selected on a queue-only branch needs an organization repository with a merge-queue ruleset; confirm GitHub's `immutable` and asset `digest` fields.
- [ ] Rulesets, members and teams on GitHub: the organization ruleset sheet on a throwaway organization; push restrictions and signed commits surviving a branch protection save; members' two-factor as an owner and as a member; making a member an outside collaborator and removing one; a team's parent and repository changes; the team-admin guard; and Access Review: People and Teams against real permissions.
- [ ] Across Repositories on the two test repositories: Release Train..., Set Secret Everywhere..., Turn On or Off Everywhere... (needs a webhook on both), Rename Everywhere on a throwaway branch, and Promote to Organization for a secret, a variable and a webhook in the test organization.
- [ ] **GH-R-119:** timed find-the-answer sessions with people.
- [ ] Plain-Language Batch on the test repository (assign, then unassign, by sentence; GitHub's search may need a moment to index a new issue), and Ctrl+Shift+S in the real window.
- [ ] **GH-R-157:** the JAWS, NVDA and VoiceOver checks for the checklists.
- [ ] WordPress current candidate: run the documented live regression on an authorized test site and distinguish existing site-side failures from regressions.
- [ ] Seed QUILL Accessible Forms (QAF), Gravity Forms, Paid Memberships Pro (PMPro), custom types/taxonomies/meta, constrained roles and realistic media/content for the supported scope.
- [ ] Verify taxonomy discovery, nested fields, block notes, upload/chunking/regenerate sizes, media listening/watching and contributor restrictions where still unverified.
- [ ] Reconcile "90 pass / 4 site-side fail" from earlier branches with fresh final-candidate results; do not inherit old green evidence.
- [ ] WordPress.com onboarding: confirm application/client registration and the current OAuth path if still incomplete.
- [ ] Audit external QAF/BAF/Site Types branches, names, release state and dependency contracts before relying on historical "waiting on Jeff" notes.
- [ ] Verify packaged app behavior, not only source runs; include clean/offline Practice Site launch.
- [ ] Manual acceptance stays separately signed off by the user/testers; every blocked scenario names the missing environment or permission.

## Part 2. WordPress

### 2.1 Decisions (Jeff, 2026-11-18)

- **Updates:** stay in the WordPress Dashboard. QUILL opens Dashboard > Updates; no WP-CLI, MainWP or Jetpack.
- **Backups:** snapshots and WXR (WordPress's export file) only.
- **Security:** no Security Review for now.
- **Plugin scope:** WooCommerce and Yoast are in, with QAF, Gravity Forms and PMPro.
- **Rank Math:** read only (confirmed by Jeff, 2026-11-19).

### 2.3 Missing in QUILL

"Route" means the REST route that does it. "wp-admin" means there is no route.

##### Shop (WooCommerce)


Scheduled Actions and the extensions marketplace are wp-admin only. Subscriptions and Bookings are paid extensions with their own routes, not in scope.

##### Payments in QAF: waiting on the test site and a person

- [ ] **Square and connections on a real site.** On the test site's sandbox: a Square payment, a declined card (4000 0000 0000 0002), a refund, and a webhook replay, with the receipt and the entry showing the same amount and status; then a form with two Stripe connections, a PayPal and a Square routing a test payment by each kind of rule, and each refund returning to the account that took it.
- [ ] **Square's card field with a screen reader**, before any live use: NVDA and JAWS on Windows, VoiceOver on macOS and iOS (the field is Square's iframe, so this is a check of Square's markup, with QAF's group label and status messages around it).
- [ ] **Per-connection test or live mode**, only if a site needs a live connection beside a test one. Today the site's one mode covers all its connections; the contract already reports `test_mode` per connection.

### 2.4 Built but not yet tried live

All of the following has tests over recorded or fake answers and none has met a real site. The checklist is `docs/qa/wordpress-regression-testing.md` (the Workbench section and the Live run section), and wordpress.md section 19 keeps the list.

- [ ] The whole Workbench, W1 to W8 and packages 1 to 14. It is now the default, so this comes before the next release.
- [ ] WooCommerce, The Events Calendar and Yoast SEO, signed in on the test site, which has all three. A refund only against a gateway's test mode.
- [ ] New Order, Change Items and Change Address on a test order: especially that a quantity of 0 takes an item off, which WooCommerce's order controller documents but QUILL has only met in fakes.
- [ ] PMPro Members of This Level (built from users plus each person's levels: the `pmpro/member-memberships-get` ability or `pmpro/v1/get_membership_levels_for_user`), its speed on a big site, and the paged discount-code list.
- [ ] Shop Analytics against a real store: the `wc-analytics` answer shapes, a store that has not imported its order history, and whether Customers should take a date range.
- [ ] Yoast's canonical address, primary category and schema type: whether the test site registers those meta keys for REST (expect read only), the `yoast_head_json` schema shape, and Open in wp-admin landing on the Yoast panel. WP Crontrol's Cron Events page slug and plugin name.
- [ ] Redirection's options (`redirection/v1/setting`, built from the plugin's documentation, never seen live).
- [ ] Redirection: the slug-change redirect offer, the redirect list and 404 log, Redirect Groups (new, rename, turn off, delete) and Import Redirects.
- [ ] QAF on the test site (it still runs BAF), the QAF migration, and the spam settings with a live submission.
- [ ] Gravity Forms building, conversion, feeds, notifications and confirmations, results and test submissions. These need a licensed Gravity Forms with its REST API on.
- [ ] PMPro 3.9 or later on WordPress 6.9 or later, with a role whose PMPro capabilities were changed; and New and Edit Membership Level on a test level.
- [ ] Advanced Custom Fields read and write, and the QUILL Site Types plugin in a real WordPress.
- [ ] Copy to Site and Compare Sites between two real sites, and Promote to Network on a real multisite.
- [ ] The Practice Site from an installed build, not only from source.
- [ ] WordPress.com sign-in, which waits on the app's client ID.

### 2.5 Open rows from the WordPress delivery checklist

- [ ] **QAF name migration, live:** both halves are built and tested; deploy QAF to the test site, which still runs BAF, and check its forms, entries, pages and Forms node after the migration.
- [ ] **Test environments:** install QAF, Gravity Forms 2.x with REST API v2 enabled, and PMPro 3.9+ on WordPress 6.9+ on an authorized test site, with an account per role, and record exact versions and capabilities.
- [ ] **QAF spam, live:** the five spam guarantees are proven in QAF's PHPUnit suite; what is left is a live submission on the test site once QAF is deployed there.
- [ ] **PMPro, live:** WordPress 6.9+ with PMPro 3.9+ and a role with customized PMPro capabilities (the card and billing field stripping is done).
- [ ] **Payments, live:** QAF's and PMPro's PHP suites, Stripe test mode, a PayPal sandbox and a reachable webhook endpoint on the test site: webhook authenticity/replay/order, duplicate submission and accessible checkout acceptance.
- [ ] **Practice Site from an installed build:** start/connect/reset/stop/restart with the bundled Node and payloads on a clean installation (the source run passes).

## Part 3. Other work

- [ ] **Copilot SDK 2.0 runtime verification (needs a Windows build).** The source pins `microsoft-copilot-sdk==2.0.1` everywhere; what still names 1.x is the committed `standalone/runtime/runtime-inventory.json`, and `scripts/check_build_env.py` now stops a build whose Python still has `github-copilot-sdk`. On the build machine: `py -m pip uninstall -y github-copilot-sdk`, `py -m pip install -e ".[runtime,packaging]"`, build the runtime, run `python scripts/check_runtime_inventory.py <dist-dir> --write`, confirm the inventory names `microsoft-copilot-sdk` and not `github-copilot-sdk`, then drop the legacy notices entry (`github-copilot-sdk` in `quill/data/third_party/components.json`) and regenerate the notices.

### 3.2 Family UX pilots

Decided on 2026-11-19 in `docs/design/2026-11-19-family-ux-pilots.md`: the pilots are Quill Cast and QUILL Lite, and the work starts with truthful results and stable lists. Lost work or misdirected input seen in a pilot jumps the queue.

- [ ] Testers, with a screen reader, on Cast's still lists: one re-read, not two, when rows arrive above the selected episode; the list's changing name ("Inbox (9)") is not read again; QUILL's Play Queue window keeps its caret when an episode finishes (speech and braille); "3 new episodes in The Daily." is heard once.
- [ ] Journey A, from Cast to a saved place to QUILL, once FUX-04 and FUX-06 are in.
