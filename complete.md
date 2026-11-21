# Everything left to do for QUILL, in one list

**Owner:** Jeff Bishop / Community Access
**Trimmed:** 2026-11-19 to open work only. Everything done, every proposal not adopted, and the old source files (`complete2.md`, `wp_missing.md`, `how.md`, the delivery checklist, the design companion and the requirement ledgers) are in git history: `git log -- complete.md`.
**Rule:** this is the one place to track open work. Add to it rather than starting a new root file. When an item is built, delete it here and say so in the changelog. Partly built items keep only what is left.

**Who owns what (2026-11-20):**
- **This file** is the list of open work. Each item stays until it is built.
- **`D:\quill\status.md`** is the live count of what remains, kept by Jeff and the coordinator. It is not committed.
- **The requirement audit** (`docs/qa/github-workbench-requirement-audit-2026-11.md`) holds the status of every GH-R requirement. This file names only the requirements still open.
- `docs/planning/workbench-implementation-status.md` is the Workbench delivery log, and `docs/planning/roadmap.md` is the July plan of record, kept for history. Neither lists open work.

## Pick up here

For whoever continues, person or AI. Jeff's log of every step is `D:\quill\claude.log`. The commands and gates are in `CLAUDE.md`.

- **Screen-reader testing** is done by Jeff's testers and is not tracked here.
- **Where it stands (2026-11-20):** merged since 2026-11-19: #1943 to #1962, #1964 to #1966, #1968, #1969, #1972, #1976, #1977 and #1979 to #1983. Merged in the 2026-11-20 merge train: #1963, #1967, #1970, #1971, #1973, #1974 and #1975. Rule (Jeff): nothing Enterprise Cloud only; organization-only checks run in a test organization.
- **Next (Jeff, 2026-11-20):** the known defects in Part 0 come first, worst harm first. Screen-reader testing is a given on everything. A tester's defect report always comes first.
- **Live testing runs alongside.** On 2026-11-19 Jeff said live testing waits until all code is done. On 2026-11-20 he changed that: the known defects are fixed while live testing goes on, and documentation and live testing run side by side once the code is in. The WordPress live run (#1976) followed that. The test site is reached over SSH (`ssh lp.csedesigns.com`, wp-cli through `~/app/wordpress-test/wpcli.sh`, which needs more PHP memory). Gravity Forms 3.2.3.1 is licensed there with its REST API v2 on.
- **How to work here:**
  - Squash-merge with `gh api -X PUT repos/Community-Access/quill/pulls/N/merge -f merge_method=squash`.
  - Log each step to `claude.log`, with the time read from a clock.
  - Run the gates the change touches, and `python -m quill.tools.platform_report` before a release.
  - When an item lands, delete it here in the same pull request.

## The order of work

1. **A tester's defect report**, whenever one arrives.
2. **The known defects (Part 0)**, in the order given there.
3. **Merging the GitHub Workbench pull requests** waiting in Part 1, and documenting what they add in the GitHub Guide.
4. **Live testing**, alongside: 1.5, 2.4 and 2.5, the test site and the GitHub test repository.
5. **Other work (Part 3):** the Copilot runtime build and the family UX pilots' follow-ups.
6. **The wider code review (Part 0, H to L)**, last. (Earshot parity was taken off the list by Jeff, 2026-11-19.)

## Part 0. Code review fixes (plan.md, 2026-11-19)

The code review in `D:\quill\plan.md` found these, each confirmed by a reproduction or a probe; plan.md is the record of how. Jeff, 2026-11-20: add them all and fix them, worst harm first (settings, and anything that can lose work, charge the wrong amount or leak data). Each group is one agent and one pull request. Delete a group here when its pull request merges. Group F (the native launcher and macOS Radio) is in the Backlog, not this release.

### The known defects, in order of harm

- [ ] **D. Settings that do not stick** (6 left; QUILL Lite's stale save is fixed in #1979): a portable backup carries the startup folder and accepts another app's envelope; Converter loses settings-write failures silently; malformed Inkwell and Weather settings crash their loaders; Radio does not publish or adopt shared family choices.
- [ ] **G. Practice Site payload**: the built runtime is missing `tools\wp-playground-cli`, so the runtime-inventory gate fails. Ship it; do not rebaseline it away. Waits on the Windows build (Part 3).

### The wider review, after the defects

- [ ] **H. Practice Site follow-ups**: a synchronous stop may block the UI; missing tools hide the reset and cleanup choices; lesson markers do not prove the PHP seeding worked; reset, history and late completion callbacks need lifecycle tests. Sizing the Practice Site for shipping (installer increase, installed size, first start, offline start) waits on the Windows build with G.
- [ ] **I. Diagnostics follow-ups**: the stdlib regex fallback drops its timeout; diagnostic readers lack the bounds their comments promise; fault-handler ownership during handle cleanup; full logging queues on relocation and shutdown; the app shell's modal entered/exited cue setting has no callback (reconcile it with GATE-13, with no duplicate speech).
- [ ] **K. AI choices and settings people can understand**: every AI entry point says which provider and model, local or cloud, what is sent, limits, consent and fallback, before use, and never switches provider silently. Settings whose effect is not obvious (AI, privacy, accessibility, portability) show the effective value, where it comes from, and how to reset it. Fix real gaps only; no duplicate UI.
- [ ] **L. The rest of the code audit** (plan.md Phase 3), with the "change it, use it, reopen it" checks, in three parts: L1 Cast and the rest of Windows Radio; L2 WordPress operations and the GitHub Actions workflows; L3 Beacon, Converter, Inkwell, Media Player, Social, Studio, Transcribe and Weather. Confirmed defects are fixed with tests; everything else is reported.

Done and deleted here: A, WordPress local writing (#1980); B, Windows Radio recording (#1982); C, diagnostics and help (#1981); E, the hosted AI gateway (#1977); and J, the records and design documents (the pull request that added this part).

## Part 1. The GitHub Workbench

Every GitHub API operation is covered, needs no route of its own, or is out of scope with its reason in `quill/core/github/api_coverage.json` (planned ceiling 0). The Copilot cloud agent's commands use a public preview API and need a live run on a Copilot plan before anyone relies on them (1.5).

### 1.3 Features and checks still open

Each is done only with evidence: a test or a live run.

#### Features and verification

- [ ] First-class by-name collections for the PRD 22.11 kinds still "not yet" in `quill/core/github/across_scope_matrix.py`: workflows, templates, Dependabot and CODEOWNERS, people, settings and packages.
- [ ] GX14 workspace/service handoffs; GX15 optional grounded assistance.

#### Documentation at the end of each delivery batch

- [ ] Release notes, announcements, What's New, both PRDs and their status page, the QUILL and QUILL Lite user guides, the GitHub guide and the WordPress and Forms guide, with regenerated HTML and EPUB siblings, written in Jeff's voice and matching what shipped.

#### Requirement audit: what is still open

The record is `docs/qa/github-workbench-requirement-audit-2026-11.md`. After the 2026-11-20 merge train it counts 92 of 100 GH-R ids met and 8 partly met; none is not met.

- [ ] **GH-R-150 and 151:** more kinds under Across Repositories (see the by-name collections row above).
- [ ] **GH-R-105:** the branch rule tutorial, the eleventh lesson of D8. The ruleset and branch protection editing it needs is in (#1961). Not started.

### 1.5 Waiting on Jeff and the testers

- [ ] Run `python docs/qa/github-live-run.py --create` after signing in again, and the live rows marked "needs Jeff".
- [ ] Read Only, Organize, Full and Safe Mode on the test repository refuse and allow as tested, and the permission explanations (greyed rows, Shift+F1, GitHub's own refusals) match what GitHub does.
- [ ] GitHub live scenarios: multiple roles/accounts, protected branches, organization restrictions, rate limiting, private repositories, project fields, secrets, failure/retry and no-API fallbacks; the Copilot cloud agent commands on a Copilot plan.
- [ ] Vote... in a real discussion poll, and the Pinned (spotlight) place, on the test repository.
- [ ] Edit Workflow..., New Workflow... and Compare Configuration... on the test repository (each through a pull request, then closed); Dependabot Commands... on a real Dependabot pull request, and whether GitHub still accepts `@dependabot merge`, `squash and merge`, `cancel merge`, `close` and `reopen`.
- [ ] Secrets on the test repository (create, change, list shows only the name, delete); Dependency Review on an open pull request and Security Overview on an organization repository; an organization secret in Community-Access set to selected with a repository added and removed, then back to private (confirms a visibility-only change is accepted); Allow a Blocked Secret... needs a real blocked push and its placeholder id.
- [ ] Issue types and fields in an organization that has them: typed values in the Issue fields column (a date, a number, a choice), `type:Bug` and `field.priority:high` searches, the Properties Issue Fields page, "hidden from you" for an account that cannot see fields, a person's repository (`/user/issue-fields`).
- [ ] Merge Selected... on two throwaway pull requests, and Release Evidence on `v0.0.1-quill-live`, on the test repository; Merge Selected on a queue-only branch needs an organization repository with a merge-queue ruleset; confirm GitHub's `immutable` and asset `digest` fields.
- [ ] Rulesets, members and teams on GitHub: the organization ruleset sheet on a throwaway organization; push restrictions and signed commits surviving a branch protection save; members' two-factor as an owner and as a member; making a member an outside collaborator and removing one; a team's parent and repository changes; the team-admin guard; and Access Review: People and Teams against real permissions.
- [ ] Across Repositories on the two test repositories: Release Train..., Set Secret Everywhere..., Turn On or Off Everywhere... (needs a webhook on both), Rename Everywhere on a throwaway branch, and Promote to Organization for a secret, a variable and a webhook in the test organization.
- [ ] Roles and accounts on GitHub: My Access Here, Why Can't They? and Access Review against real permissions (a custom role, a team grant, an outside collaborator); Bulk Access Changes on the test organization; Compare Accounts and Act As with two signed-in accounts; Use GitHub CLI Sign-In...; and an account on a GitHub Enterprise Server, if one can be borrowed.
- [ ] **GH-R-119:** timed find-the-answer sessions with people.
- [ ] Plain-Language Batch on the test repository (assign, then unassign, by sentence; GitHub's search may need a moment to index a new issue), and Ctrl+Shift+S in the real window.
- [ ] **GH-R-157:** the JAWS and NVDA checks for the checklists. The VoiceOver part is in the Backlog with the other macOS work.
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

Scheduled Actions and the extensions marketplace are wp-admin only. Subscriptions and Bookings are paid extensions with their own routes, not in scope.

##### Payments in QAF: waiting on the test site and a person

- [ ] **Square and connections on a real site.** On the test site's sandbox: a Square payment, a declined card (4000 0000 0000 0002), a refund, and a webhook replay, with the receipt and the entry showing the same amount and status; then a form with two Stripe connections, a PayPal and a Square routing a test payment by each kind of rule, and each refund returning to the account that took it.
- [ ] **Square's card field with a screen reader**, before any live use: NVDA and JAWS on Windows (the field is Square's iframe, so this is a check of Square's markup, with QAF's group label and status messages around it). The VoiceOver check on macOS and iOS is in the Backlog.
- [ ] **Per-connection test or live mode**, only if a site needs a live connection beside a test one. Today the site's one mode covers all its connections; the contract already reports `test_mode` per connection.

### 2.4 Built but not yet tried live

What is left here has tests over recorded or fake answers but has not been checked on a real site yet. The shop orders, shipping classes, variations, Shop Analytics, Yoast's fields, PMPro members and levels, Redirection, Gravity Forms building and submissions, ACF and Site Types passed live on 2026-11-20 (159 pass, 0 fail). A second pass the same day added every Gravity Forms field type, entry edits, messages and conversion both ways (144 to 150), QAF's spam checks with real submissions (151), the move from BAF to QAF (152), PMPro's discount codes past PMPro's 20 (153) and Members of This Level at 260 people (154), and test 86 with a menu it makes. The checklist is `docs/qa/wordpress-regression-testing.md` (the Workbench section and the Live run section), and wordpress.md section 19 keeps the list.

- [ ] The whole Workbench, W1 to W8 and packages 1 to 14. It is now the default, so this comes before the next release.
- [ ] A WooCommerce refund, only against a gateway's test mode: the test site has no gateway in test mode yet (only Cash on Delivery).
- [ ] Yoast: Open in wp-admin landing on the Yoast panel (needs a browser).
- [ ] Gravity Forms feeds and results (tests 140 and the Results half of 141): Jeff installs, from Forms > Add-Ons on the test site, the Gravity Forms Webhooks Add-On (a feed add-on with no outside account) and the Gravity Forms Quiz, Polls and Survey Add-Ons. Everything else in Gravity Forms passed live on 2026-11-20 (tests 104 to 108, 123 to 126, 139, 141 and 144 to 150).
- [ ] PMPro with a role whose PMPro capabilities were changed (quill-members, Membership Manager, needs an application password). PMPro 3.9.2's level route drops the billing and expiry periods and refuses DELETE; QUILL now says so.
- [ ] Copy to Site and Compare Sites between two real sites, and Promote to Network on a real multisite.
- [ ] The Practice Site from an installed build, not only from source.
- [ ] WordPress.com sign-in, which waits on the app's client ID.

### 2.5 Open rows from the WordPress delivery checklist

- [ ] **PMPro, live:** WordPress 6.9+ with PMPro 3.9+ and a role with customized PMPro capabilities (the card and billing field stripping is done).
- [ ] **Payments, live:** QAF's and PMPro's PHP suites, Stripe test mode, a PayPal sandbox and a reachable webhook endpoint on the test site: webhook authenticity/replay/order, duplicate submission and accessible checkout acceptance.
- [ ] **Practice Site from an installed build:** start/connect/reset/stop/restart with the bundled Node and payloads on a clean installation (the source run passes).

## Part 3. Other work

- [ ] **Copilot SDK 2.0 runtime verification (needs a Windows build).** The source pins `microsoft-copilot-sdk==2.0.1` everywhere; what still names 1.x is the committed `standalone/runtime/runtime-inventory.json`, and `scripts/check_build_env.py` now stops a build whose Python still has `github-copilot-sdk`. On the build machine: `py -m pip uninstall -y github-copilot-sdk`, `py -m pip install -e ".[runtime,packaging]"`, build the runtime, run `python scripts/check_runtime_inventory.py <dist-dir> --write`, confirm the inventory names `microsoft-copilot-sdk` and not `github-copilot-sdk`, then drop the legacy notices entry (`github-copilot-sdk` in `quill/data/third_party/components.json`) and regenerate the notices.

### 3.2 Family UX pilots

Decided on 2026-11-19 in `docs/design/2026-11-19-family-ux-pilots.md`: the pilots are Quill Cast and QUILL Lite, and the work starts with truthful results and stable lists. Lost work or misdirected input seen in a pilot jumps the queue.

- [ ] Testers, with a screen reader, on Cast's still lists: one re-read, not two, when rows arrive above the selected episode; the list's changing name ("Inbox (9)") is not read again; QUILL's Play Queue window keeps its caret when an episode finishes (speech and braille); "3 new episodes in The Daily." is heard once.
- [ ] Journey A, from Cast to a saved place to QUILL. Ready now that FUX-04 and FUX-06 are in (#1958, #1969).

## Backlog (not this release, Jeff 2026-11-20)

Not scheduled for this release. All macOS features are here: where a row above covers Windows and macOS, only its macOS part is here.

- **A runnable macOS Radio app.** Its entry point and UI do not exist yet, although `standalone/radio-mac/pyproject.toml` names them.
- **Code-review group F, the native launcher and macOS Radio** (9). Launcher: a damaged portable can fall back to the host runtime and storage; ANSI path APIs lose characters; the launcher icon macro is never defined; a launch failure shows two dialogs; a failed runtime installer is left in the temporary folder. Mac Radio: Stop can lose a reconnect race; continuations restart the full duration; same-name starts overwrite; three tests fail with a NameError on a missing import; packaging names a README that is missing. Not started; plan.md ("Native launcher delivery review", "macOS Radio review") is the record.
- **Verifying release attestation signatures inside QUILL**, which would add Sigstore. QUILL keeps pointing to `gh attestation verify` (GX10).
- **A date range for Shop Analytics' Customers report** (also in the WordPress Workbench PRD's Backlog).
- **The macOS and iOS screen-reader checks:** VoiceOver on Square's card field, and on the GitHub checklists (GH-R-157).
