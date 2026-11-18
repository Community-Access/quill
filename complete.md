# Everything left to do for QUILL, in one list

**Owner:** Jeff Bishop / Community Access
**Made one file:** 2026-11-18, from `complete.md` (2026-11-10), `complete2.md` (2026-11-10), `wp_missing.md` (2026-11-14), the review notes at the end of `how.md` (2026-11-14), the EdSharp review, and the work queued in conversation on 2026-11-18.
**Rule:** this is the one place to track what is still to do. A new list goes in here, not in a new file at the root. When an item is built, mark it done here, with its pull request.

## Start here

### Pick up here (handoff, 2026-11-18 09:05 MST)

For whoever continues this work, person or AI. The running log of every step is `D:\quill\claude.log` on Jeff's computer.

- **Merged today:** #1887 and #1888 (GitHub Workbench batches). 272 GitHub endpoints are still planned (Part 1.2).
- **Open:** #1889, Chris Nova's Cast queue fix (branch `cast/queue-advance`). Its size-gate failure is fixed; merge it when CI is green. See Part 5 for what is still unknown.
- **In progress:** Kelly Ford's diff marks (Part 2), on branch `diff/kelly-marks`. Built and tested; the pull request is the next step.
- **Then:** the EdSharp items (Part 4), then the GitHub API batches in the order of Part 1.2 until planned is 0, then the GitHub documentation pass (1.3).
- **How to work here:** the commands and gates are in `CLAUDE.md`. Squash-merge with `gh api -X PUT repos/Community-Access/quill/pulls/N/merge -f merge_method=squash`. Log each step to `claude.log` with the time read from a clock, never guessed.

### The order of work

Jeff set this order on 2026-11-18. The GitHub Workbench comes first, above everything else.

1. **The GitHub Workbench backlog (Part 1).** Every GitHub API endpoint still planned is built, until the planned count is 0, then the Workbench's documentation is brought up to the WordPress standard.
2. **Diff features everywhere (Part 2).** Kelly Ford's ways of marking changes, in every compare mode, the GitHub Workbench and both editors.
3. **WordPress (Part 3).** Re-check `wp_missing.md`'s list against today's code, then build what is still missing. Six decisions are Jeff's.
4. **From the EdSharp review (Part 4).**
5. **Other queued work (Part 5):** Microsoft Copilot SDK 2.0, and Chris Nova's Cast queue report.
6. **The Workbench delivery checklist (Part 6), the design companion (Part 7) and the WordPress UX review notes (Part 8)** are the detailed lists behind parts 1 and 3, kept word for word from their files.

### How to read this file

- Parts 1 to 5 are written for this file. Parts 6 to 8 are the old files, each under one heading, with every heading moved down a level and nothing else changed. Their own section numbers ("section 6", "section 10B") still mean their sections inside that part.
- Code comments and commit messages that cite `wp_missing.md`, `complete2.md` or `how.md` now point to Part 3, Part 7 and Part 8 here. The old files are in git history.
- "Planned" counts come from `quill/core/github/api_coverage.json`, the table the coverage gate checks. `python -m quill.tools.github_api_coverage_audit` prints the current numbers.

## Part 1. The GitHub Workbench (top priority)

### 1.1 Where it stands, 2026-11-18

- GitHub's API has 2,004 rows in the coverage table. After the pull requests open on 2026-11-18 merge (#1879 Repositories Allowed, #1880 more settings on Properties, #1881 code scanning), 540 are covered, 217 need no route of their own, 744 are out of scope with a reason written down, and **503 are still planned**.
- Done on 2026-11-18: one resource engine for 34 lists of settings (#1877); 327 planned rows settled as needing nothing or out of scope, Enterprise Cloud among them (#1878); Repositories Allowed for secrets, variables and runner groups (#1879); Actions rules, immutable releases, code scanning setup and safety on Properties (#1880); Copilot Autofix, every place an alert was found, and SARIF upload (#1881).
- Out of scope by Jeff's decision on 2026-11-18: everything that needs GitHub Enterprise Cloud, and company administration such as billing, Copilot seat management, private runner networking, migrations and paid Advanced Security. What a small organization such as Community-Access uses stays in.

### 1.2 Endpoints still to build, by area

Not done until this table is empty.

| Area | Endpoints still planned |
|---|---|
| Packages: one version at a time, and other people's | 14 |
| codespaces/codespaces | 14 |
| actions/permissions | 12 |
| reactions/reactions | 12 |
| actions/self-hosted-runners | 10 |
| agent-automations/agent-automations | 10 |
| projects/items | 10 |
| actions/workflow-runs | 9 |
| issues/issues | 9 |
| orgs/custom-properties | 9 |
| apps/installations | 8 |
| copilot-spaces/collaborators | 8 |
| copilot-spaces/copilot-spaces | 8 |
| copilot-spaces/resources | 8 |
| copilot/copilot-code-review | 8 |
| orgs/organization-roles | 8 |
| orgs/orgs | 8 |
| pages/pages | 8 |
| activity/events | 7 |
| repos/repos | 7 |
| gists/gists | 6 |
| interactions/repos | 6 |
| Security advisories: comments, private forks, an organization's | 5 |
| actions/self-hosted-runner-groups | 5 |
| activity/starring | 5 |
| classroom/classroom | 5 |
| orgs/members | 5 |
| pulls/comments | 5 |
| pulls/pulls | 5 |
| pulls/reviews | 5 |
| Dependency graph and SBOM export | 4 |
| Self-hosted runners: just-in-time setup and removal tokens | 4 |
| actions/secrets | 4 |
| actions/variables | 4 |
| code-scanning/code-scanning | 4 |
| deployments/branch-policies | 4 |
| deployments/protection-rules | 4 |
| gists/comments | 4 |
| issues/artifacts | 4 |
| issues/comments | 4 |
| issues/issue-dependencies | 4 |
| orgs/rules | 4 |
| projects/fields | 4 |
| pulls/stacks | 4 |
| secret-scanning/secret-scanning | 4 |
| section 21.8 | 4 |
| users/issue-fields | 4 |
| activity/watching | 3 |
| agent-tasks/agent-tasks | 3 |
| checks/runs | 3 |
| checks/suites | 3 |
| code-quality/code-quality | 3 |
| commits/comments | 3 |
| dependabot/repository-access | 3 |
| deployments/deployments | 3 |
| interactions/user | 3 |
| issues/issue-field-values | 3 |
| issues/labels | 3 |
| issues/sub-issues | 3 |
| orgs/issue-fields | 3 |
| pulls/agent-merge | 3 |
| search/search | 3 |
| users/followers | 3 |
| actions/concurrency-groups | 2 |
| actions/workflow-jobs | 2 |
| activity/notifications | 2 |
| codespaces/machines | 2 |
| commits/commits | 2 |
| interactions/orgs | 2 |
| issues/events | 2 |
| orgs/webhooks | 2 |
| projects/drafts | 2 |
| projects/projects | 2 |
| projects/views | 2 |
| releases/releases | 2 |
| repos/contents | 2 |
| repos/custom-properties | 2 |
| repos/webhooks | 2 |
| secret-scanning/push-protection | 2 |
| teams/teams | 2 |
| users/emails | 2 |
| users/users | 2 |
| actions/workflows | 1 |
| activity/feeds | 1 |
| agents/secrets | 1 |
| agents/variables | 1 |
| branches/branches | 1 |
| commits/statuses | 1 |
| dependabot/alerts | 1 |
| deployments/environments | 1 |
| deployments/statuses | 1 |
| issues/assignees | 1 |
| issues/milestones | 1 |
| orgs/outside-collaborators | 1 |
| orgs/rule-suites | 1 |
| pulls/copilot-code-review | 1 |
| pulls/review-requests | 1 |
| releases/assets | 1 |
| repos/planning-statuses | 1 |
| repos/rule-suites | 1 |
| repos/rules | 1 |
| teams/members | 1 |
| users/gpg-keys | 1 |
| users/keys | 1 |
| users/social-accounts | 1 |
| users/ssh-signing-keys | 1 |
| GraphQL-only changes (Projects, Discussions, Sponsors tiers, issue fields and types, and others) | 86 |
| **Total** | **503** |


### 1.3 Then: documentation as good as WordPress's

When the table above is empty, the GitHub Workbench's documentation is brought up to the WordPress standard: the GitHub Guide's chapters in both editors, F1 help, the GitHub PRD, the release notes and the live-run rows, all rendered and checked. Batches built after 2026-11-18 are written up in both changelogs only, by Jeff's choice, until then.

### 1.4 Still waiting on Jeff for GitHub

- Run `python docs/qa/github-live-run.py --create` after signing in again, and the live rows marked "needs Jeff".
- The 17 screen-reader checks in `docs/qa/screen-reader-checks-2026-10.md`.
- The detailed GitHub checklists are in Part 6, sections 6, 10, 10A, 10B and 12.

## Part 2. Diff features, from Kelly Ford's GHManage

Kelly Ford asked on 2026-11-18 whether QUILL had seen how GHManage and The Chat Place let a person choose how changes are marked. Jeff: make it rich, everywhere, and give attribution. Kelly's `difftext.py` (in TheIdeaPlace/app-kit) is MIT licensed, so it may be adapted with its copyright notice and credit.

Built on branch `diff/kelly-marks` (2026-11-18): `quill/core/diff_marks.py` (adapted from Kelly's `difftext.py`, MIT notice kept) with the four styles, "!-"/"!+" pairing, "Lines 10 to 15:", file summaries, "blank line" and the punctuation reminder. It is used by Compare Files (a new Mark lines as choice), Compare with File, WordPress Compare with Site, and the Workbench's pull request patch list, File Differences, Compare Branches and local git differences, all through one saved choice. Credited in the code, the changelog, both guides and CONTRIBUTING. QUILL Lite has no compare views, so nothing there to change.

Still to do:

- [ ] A changed pair in the Workbench's patch list also says which words changed (Compare Files already does, through `_word_diff_label`).
- [ ] Next and previous change in the Workbench's patch list, saying "Change 2 of 5" (Compare Files already says "Difference 2 of 5").

## Part 3. WordPress: what is still missing

Below is `wp_missing.md` (2026-11-14) as it was. Before building from it, check each line against today's code, since some were built after it was written. Its six decisions for Jeff are at its end.

Checked 2026-11-14 on branch `codex/workbench-combined-2026-11-10`, uncommitted tree.

### How this was checked, and how to read it

I made a list of the jobs a WordPress site owner, editor, author, contributor and administrator actually do. I took it from every menu and submenu of wp-admin (WordPress 6.9 and 7.x), plus WooCommerce, The Events Calendar, Yoast SEO, Gravity Forms, Paid Memberships Pro, Redirection and QUILL Accessible Forms, and from the REST API reference. Then I looked for each job in the code: the editors' WordPress commands, the WordPress Workbench's tree, its row actions, the wp-admin map, the route coverage rules and the scope matrix. I also read wordpress.md (9.16 to 9.18 and section 19), complete.md section 7 and the Workbench PRD.

A job counts as done only when code does it. A doc line saying it is done was not enough.

Each job lands in one of five places:

- **Done**: QUILL does it, in the editor or the Workbench.
- **wp-admin only**: WordPress has no REST route for it, and QUILL already says so and opens the right wp-admin screen. Nothing to build unless we go outside REST.
- **Being built today**: another session is writing it right now. The files exist but are not finished or tested yet. Check again when that work lands.
- **Missing**: there is a route, or QUILL could do it locally, and nothing does it yet.
- **Deferred**: security, backups and updates, which you asked to wait. They have their own section near the end.

One caution. Other sessions were changing WordPress files while I read, so this is a snapshot. The Shop, Events and SEO lines were moving as I wrote.

### Built since this audit (2026-11-14, later the same day)

These were missing when the audit was written and are now built, with tests; none has met a live site yet. Their lines are gone from the lists below.

- Earlier Versions on post, page and custom-type rows in the Workbench.
- Replace File on a Media Library row: in place where a plugin route exists, otherwise upload and point every use at the new file (Ctrl+Z puts them back), or open Enable Media Replace, with a redirect offered through Redirection.
- Tools > WXR Files: Export Site as WXR, and Import WXR as Drafts.
- Check for Updates on WordPress.org: plugins, themes and WordPress itself say when an update is waiting.
- Check Every Link under By Name > Links, for the whole site, with a count and a stop.
- A Gravity Forms response's answers, edited on its Properties.
- wp-admin for This Place reaches the plugins' own screens, and the WooCommerce Settings row is corrected.
- Menus: Add Menu Item, Add New Pages Automatically, and Arrange Items (the Menus window on that menu).
- Offer to Ask the Site on an ability row, which had become impossible to turn on.

### The short version

The everyday jobs are done: writing, publishing, scheduling, media, comments, categories and tags, people, menus, widgets, templates and styles. What is left falls into four groups:

- A handful of small gaps in core WordPress (menu auto-add, revisions from a Workbench row, replacing a media file, WXR import and export, a complete link check).
- Plugin depth: the rest of WooCommerce, Gravity Forms entry editing, membership levels, and Redirection's groups and options.
- Updates, backups and security, which need either a plugin's API or a way in that is not REST (WP-CLI over SSH).
- Nothing at all has been tried on a live site with a screen reader since the Workbench work began.

| Area | Jobs | Done | wp-admin only | Being built today | Missing | Deferred |
|---|---|---|---|---|---|---|
| Posts and pages | 27 | 25 | 1 | 0 | 1 | 0 |
| Media | 15 | 12 | 2 | 0 | 1 | 0 |
| Categories, tags, taxonomies | 6 | 6 | 0 | 0 | 0 | 0 |
| Comments | 9 | 7 | 2 | 0 | 0 | 0 |
| Users | 15 | 10 | 5 | 0 | 0 | 0 |
| Menus and widgets | 11 | 10 | 0 | 0 | 1 | 0 |
| Appearance | 10 | 7 | 3 | 0 | 0 | 0 |
| Plugins and themes | 10 | 6 | 2 | 0 | 1 | 1 |
| Settings | 10 | 4 | 6 | 0 | 0 | 0 |
| Tools | 12 | 6 | 3 | 0 | 3 | 0 |
| Forms | 14 | 11 | 1 | 0 | 2 | 0 |
| Shop (WooCommerce) | 30 | 12 | 2 | 7 | 9 | 0 |
| Events | 9 | 5 | 3 | 1 | 0 | 0 |
| SEO | 9 | 4 | 1 | 2 | 2 | 0 |
| Memberships | 10 | 6 | 1 | 0 | 3 | 0 |
| Redirects | 3 | 2 | 0 | 0 | 1 | 0 |
| Multisite | 3 | 2 | 1 | 0 | 0 | 0 |
| Maintenance | 9 | 2 | 2 | 0 | 2 | 3 |
| Total | 212 | 137 | 35 | 10 | 26 | 4 |

These are counts from my list of jobs, not from a code metric, so read them as rough. The "wp-admin only" column is mostly WordPress's limit, not QUILL's.

### Missing in QUILL

The most useful to a site owner come first in each area. "Route" means the REST route that does it. "wp-admin" means there is no route.

#### Posts and pages

Nothing missing.

Already done and worth knowing: Markdown or HTML on new items, open existing items as HTML (blocks kept) or Markdown (blocks kept as islands), drafts, publish, schedule, preview, conflict check, Properties with author, template, parent, format, pingbacks and featured image, bulk edit with Undo, Trash, Empty Trash, duplicate, the review queue, the calendar, site-wide Find and Replace, importing folders and spreadsheets as drafts, and Copy to Site. The post lock is wp-admin only, and QUILL opens the edit screen and says why.

#### Media

Scaling the original and the media size settings are wp-admin only, and QUILL already says so.

#### Categories, tags and custom taxonomies

Nothing missing. Add, rename, merge, convert, delete, hierarchy, term fields and Advanced Custom Fields, custom taxonomies found from the site, and Across Sites all work. Defining a new taxonomy needs the QUILL Site Types plugin, which has never run in a real WordPress (see "Built but not yet tried live").

#### Comments

Nothing missing that REST allows. The comment blocklist (`disallowed_keys`), moderation keys, avatars, threading and notification settings are wp-admin only, and the scope matrix says so.

#### Users

Nothing missing that REST allows. Password reset emails, the welcome email, Log Out Everywhere, profile preferences and editing roles are wp-admin only. Editing roles needs a plugin such as Members or User Role Editor, and neither has a REST API that I know of (unverified). QUILL opens the right screen for each.

#### Menus and widgets

Menus can be created (New Here), deleted (Shift+Delete), have items added from the Workbench (Add Menu Item, or Ctrl+N with a menu selected) and edited (the editor's Menus window), add new top-level pages automatically (a check box on Properties, and a command), have locations set and earlier versions restored. Widgets can be added, changed, moved, removed and previewed.

#### Appearance

Nothing missing that REST allows. Activating, installing, updating or deleting a theme, the classic Customizer and the theme file editor are wp-admin only, because `wp/v2/themes` only reads. Global Styles, templates and template parts (edit, create, reset, earlier versions), Additional CSS, patterns and fonts all work.

#### Plugins and themes

- **Running updates** is in the deferred section below, because REST cannot do it.

Uploading a plugin as a zip file (every premium plugin) and turning automatic updates on or off are wp-admin only.

#### Settings

Nothing missing that REST allows. Permalinks, media sizes, the privacy policy page, who may register and the default role, feeds, post by email and search engine visibility are wp-admin only. Search engine visibility is judged from the sitemap and says so.

#### Tools

Site Health's Info tab and the privacy export and erase requests are wp-admin only, and QUILL opens them without pretending a request was done.

#### Forms

QAF is covered end to end: build, publish, settings, status, delete, entries, views, spam and spam settings. Gravity Forms is close.

- **More than one notification or confirmation on a Gravity Form.** Who: forms that send different emails by answer. Route: the `notifications` and `confirmations` objects inside `gf/v2/forms/{id}`. Today QUILL's form editor edits the default confirmation and the Admin Notification and keeps the rest untouched.

Gravity Forms' own settings, add-ons and licence are wp-admin only.

#### Shop (WooCommerce)

Being built today, in new uncommitted files (`workbench_shop_care.py`, `workbench_shop_setup.py`): product reviews, webhooks, customer details, editing one variation, shipping zones with their locations and methods, tax rates and classes, attributes and their terms, and brands. I found no commands wired to them in the window yet.

Still missing after that:

- **Edit every product field.** Who: shop managers. Route: `POST wc/v3/products/{id}`. Edit Product changes price, sale price, stock, status and categories only. Missing: SKU, description, short description, sale dates, weight and dimensions, shipping class, images, downloads, upsells and cross-sells, tax class.
- **Create an order, or change its items and addresses.** Who: shops taking phone orders. Route: `POST wc/v3/orders`, `POST wc/v3/orders/{id}`.
- **Resend an order email or invoice.** Who: a customer who says the receipt never came. Route: `wc/v3/orders/{id}/actions/send_email` and `send_order_details`, which were on the test site's index on 2026-11-04.
- **Payment gateways: turn on or off, and their settings.** Route: `wc/v3/payment_gateways/{id}`. Any key fields must stay write-only, as Store Settings already does.
- **System status and its tools** (clear transients, recount terms). Route: `wc/v3/system_status`, `system_status/tools/{id}`. This also gives the PHP and database versions that core REST does not.

Also missing but less urgent: editing many products at once (`products/batch`), generating variations (`products/{id}/variations/generate`), shipping classes (`products/shipping_classes`), and Analytics (`wc-analytics/reports/*`). Scheduled Actions and the extensions marketplace are wp-admin only. Subscriptions and Bookings are paid extensions with their own routes, not in scope.

#### Events (The Events Calendar)

Events, venues and organizers (list, past, filter, new, edit, trash) are done. Event categories and tags are being built today (`workbench_event_terms.py`). Recurring events need Events Calendar Pro, and its series is changed in wp-admin, which QUILL says. Settings and the importer are wp-admin only. Tickets and RSVP (Event Tickets) are deferred plugins.

#### SEO (Yoast SEO)

SEO title, description, keyphrase, show in search results, search appearance and site scores are done. Social title and description and the bulk editor are being built today (`workbench_seo_bulk.py`).

Still missing:

- **Canonical address, primary category and schema type per post.** Route: only where Yoast registers that post meta for REST, which most sites do not. I have not verified which of these the bulk editor routes carry. Otherwise they stay in the post's Yoast panel.
- **Rank Math.** It is the other common SEO plugin and has its own `rankmath/v1` namespace. QUILL has no adapter, so it is read only, under More from This Site. Whether to support it is a decision (below).

Yoast's settings, redirects (Premium), schema settings and indexing are wp-admin only, and the SEO node lists each with its screen.

#### Memberships (Paid Memberships Pro)

Levels, orders, subscriptions and renewals due are listed. Change Membership Level, Cancel Membership, Check Membership Access and discount codes (look up one, make one) work.

- **Create or edit a membership level.** Who: the site owner changing a price or adding a tier. Route: PMPro's abilities, if the site offers a level-writing one, or `pmpro/v1/membership_level` (I believe it takes POST, unverified). Today levels are read only.
- **Members of a level, as a list.** Who: the owner emailing or counting one tier's members. Route: unverified. `pmpro/v1/recent_memberships` exists. Otherwise build it from users plus each person's levels, which is slow on big sites. Today you see a person's memberships one person at a time.
- **Every discount code, as a list.** `pmpro/v1` reads one code at a time. The list works only where an ability offers it, and otherwise opens wp-admin, which QUILL says.

Reports and payment settings are wp-admin only. The wp-admin map has only PMPro's Dashboard. Add Levels, Members, Orders, Discount Codes, Reports and Settings so "wp-admin for This Place" reaches each one.

#### Redirects (Redirection)

List, add, change, turn on and off, delete, test an address, and the 404 log are built from Redirection's documentation and have never met a real install.

- **Groups, import and export, and Redirection's options.** Route: `redirection/v1/group`, `/import`, `/export`, `/setting` (from the plugin's docs, unverified). Coverage marks them planned.

#### Multisite

Each subsite works as its own site, and Promote to Network is built. The Network Admin screens have no REST routes, so they are wp-admin only.

#### Maintenance

- **Missed scheduled tasks beyond posts.** Search and Upkeep lists posts still Scheduled after their time. No other WP-Cron task is visible to REST. WP Crontrol is named as the plugin that lists them. I do not know that it has a REST API (unverified).

Caching (purge), maintenance mode, email delivery tests and an activity log (who changed what) all need plugins. They are in the Administration Areas node with "Open in Dashboard". Updates, backups and security are below.

### Built but not yet tried live

All of the following has tests over recorded or fake answers and none has met a real site with NVDA or JAWS. The checklist is `docs/qa/wordpress-regression-testing.md` (the Workbench section and the Live run section), and wordpress.md section 19 keeps the list.

- The whole Workbench, W1 to W8 and packages 1 to 14. It is now the default, so this comes before the next release.
- WooCommerce, The Events Calendar and Yoast SEO, signed in on the test site, which has all three. A refund only against a gateway's test mode.
- Redirection, and the slug-change redirect offer.
- QAF on the test site (it still runs BAF), the QAF migration, and the spam settings with a live submission.
- Gravity Forms building, conversion, feeds, results and test submissions. These need a licensed Gravity Forms with its REST API on.
- Paid Memberships Pro 3.9 or later on WordPress 6.9 or later, with a role whose PMPro capabilities were changed.
- Advanced Custom Fields read and write, and the QUILL Site Types plugin in a real WordPress.
- Copy to Site and Compare Sites between two real sites, and Promote to Network on a real multisite.
- The Practice Site from an installed build, not only from source.
- WordPress.com sign-in, which waits on the app's client ID.
- Payments: Stripe test mode, a PayPal sandbox, and a screen-reader pass through checkout.

### Security and backups (deferred by Jeff)

You asked to wait on these. Here is exactly what the Workbench can do with core WordPress alone, what needs a plugin, and what first-class support would look like.

#### What core REST gives, with no plugin

Already built:

- **People and roles review.** Users with their roles (Group By Role gives counts, so "how many Administrators" is one look), Roles and What They May Do (read only), and guards that stop you removing yourself or the last Administrator.
- **Application passwords.** Every person's passwords with when each was made and last used, revoke one, Revoke Everywhere across sites, and Across Sites > Application Passwords. The one QUILL signs in with cannot be revoked by accident.
- **Plugin and theme versions.** Installed versions, and with consent, WordPress.org's view: closed plugins, plugins not updated in over two years, and what WordPress and PHP versions they need.
- **Site Health's security-related tests over REST.** HTTPS status, whether automatic updates can run, whether the site can reach WordPress.org, and the authorization header.
- **HTTPS and the certificate.** Expiry date from QUILL's own connection, with a warning inside 30 days.
- **XML-RPC.** An unsigned probe that says whether `xmlrpc.php` still answers. No password is sent.

What core REST cannot give, and why:

- **The file-editing constant** (`DISALLOW_FILE_EDIT`), debug mode, the PHP version and the database. These are Site Health's direct tests and its Info tab, which have no REST route. I am not certain `DISALLOW_FILE_EDIT` appears in the Info tab at all (unverified). Today QUILL opens Site Health > Info. A WooCommerce site gives PHP and database versions through `wc/v3/system_status`.
- **Failed sign-ins and lockouts.** Core keeps no record. Only a security plugin does.
- **Sessions.** Who is signed in where, and Log Out Everywhere, are wp-admin only.
- **Who may register, and the default role.** Not in `wp/v2/settings`.

Could be added with no plugin, using the same kind of unsigned probe as XML-RPC, and only for sites you connected:

- whether the user list answers without signing in (`/wp-json/wp/v2/users`), which lets strangers learn usernames;
- whether `wp-login.php?action=register` offers a sign-up form;
- whether `/wp-content/debug.log` can be downloaded;
- whether the home page sends the usual security headers (HSTS, X-Content-Type-Options, frame options);
- application passwords not used in 90 days, and inactive plugins and themes left installed, both from data QUILL already reads.

These would make a "Security Review" node under Site Health, each row a plain sentence with where the answer came from.

#### What needs a plugin's API

I checked from what I know of each plugin, not against live installs, so every claim here is **unverified** until it is tried on the test site.

| Plugin | What its API offers | Usable by QUILL? |
|---|---|---|
| Solid Security (`ithemes-security/v1`) | Its own admin is built on REST: site scans, logs, lockouts, banned hosts, user groups, settings | Probably, with an application password and an admin account (unverified) |
| Wordfence (`wordfence/v1`) | Routes exist for Wordfence Central, signed with Central's own tokens | Probably not with an application password (unverified) |
| Shield Security (`shield/v1`) | A documented REST API, Pro only | Possibly, on Pro (unverified) |
| Two Factor (`two-factor/1.0`) | Per-person setup and backup codes | Partly. Whether it lists who has two-factor on is unverified |
| Jetpack Backup and Scan | Backups and threats go through WordPress.com's API, signed in with WordPress.com | Only after WordPress.com sign-in (unverified) |
| UpdraftPlus | No public REST API that I know of. UpdraftCentral uses its own protocol | No (unverified) |
| BlogVault | A hosted service. The plugin talks only to BlogVault | No (unverified) |
| WPvivid | No documented REST API that I know of | No (unverified) |

Two more ways in are worth knowing about, neither of them a security plugin:

- **MainWP.** A separate dashboard WordPress with a documented REST API that runs updates and, through its extensions, backups across child sites. If someone already uses it, QUILL could drive it (unverified for the current version).
- **Managed hosts.** Several hosts (Kinsta, WP Engine among them) offer APIs that list and make backups. This is per host and unverified.

Vulnerability data (a plugin version with a known hole) would come from Wordfence Intelligence, Patchstack or WPScan. Each needs a key, I believe (unverified), and a new egress row with consent.

#### What first-class support could look like

- **Security Review node** (no plugin): the rows above, Needs My Attention picking up anything serious, and a weekly Watch.
- **Solid Security adapter** (if it checks out live): lockouts and the scan results as lists, Unban as a previewed action, and the log under the site.
- **Vulnerability check** (with consent): each plugin and theme version compared with one public database, flagged on its row and in Needs My Attention.
- **Backups, the honest version**: Take a Snapshot already saves content and, if asked, media. Say plainly what it leaves out (plugin tables, settings outside REST, theme and plugin files, passwords), add WXR export (above), and for a full backup open the backup plugin's screen.
- **Backups and updates over SSH with WP-CLI**: see Decisions. This is the only path to real updates and full database backups without a plugin.

### Decisions for Jeff

1. **Updates.** REST cannot update anything. The choices are:
   - keep opening Dashboard > Updates;
   - add WP-CLI over SSH for sites where you have SSH (`wp core update`, `wp plugin update`, `wp language core update`, `wp db export`), using QUILL's existing SSH client with its strict host-key policy, every command previewed;
   - drive MainWP or Jetpack where a site already has them.

   Either of the last two runs commands on a server, which is a new kind of thing for QUILL to do.
2. **Backups.** Snapshots and WXR only, or pick one backup plugin or host API to support first-class?
3. **Security.** Build the no-plugin Security Review first? If yes, are the unsigned probes (user list, registration, debug.log, headers) acceptable? They only ask your own site public questions, as the XML-RPC check already does. Then, which plugin first, if any? Solid Security looks the most REST-shaped, but that is unverified.
4. **Plugin scope drift.** The PRD's 2026-11-10 decision limits plugin integrations to QAF, Gravity Forms and PMPro. complete.md WP-G says the shop, events and SEO promises "are not current scope". Yet `workbench_coverage.py` says WooCommerce and Yoast are supported since 2026-11-13, wordpress.md section 19 says the same, and more of WooCommerce is being built today. Which is the record? If the three are in, the PRD and complete.md need updating. If they are out, today's Shop work should stop.
5. **Rank Math.** Support it alongside Yoast, or leave it read only?
6. **Live testing.** Everything above in "Built but not yet tried live" needs writes on the test host or plugins installed there, which only you can do. Which comes first? I suggest the Workbench core with NVDA and JAWS, because it is now the default.


## Part 4. From the EdSharp review

From EdSharp's `help/History.md`, 9 October to 17 November 2026 (D:\code\jamal\EdSharp), checked against QUILL on 2026-11-18. QUILL already has EdSharp's Say Clipboard presses, its search syntax, its settings migration, its safe saves and its key checks.

- [ ] **testSay:** press every Say command once and twice, and write what the screen reader said beside what QUILL meant to say. It would catch over-announcing (GATE-13) and missing speech on real JAWS and NVDA.
- [ ] **Log what was not spoken:** when QUILL is not in front, a message it does not speak goes into the session log with the reason.
- [ ] **Every command in one list, sorted three ways:** menu order, name order and key order, with a filter and a jump to a line.
- [ ] **A second press opens a review window:** Where Am I pressed twice shows everything in a window, followed by every command and key; Shift+F1 pressed twice does the same for the control's help.
- [ ] **Say Position:** line, column and percent, counting lines in the text itself, so a wrapped paragraph is one line. Check whether QUILL already speaks all three.
- [ ] **A reading-grade check for the guides**, about ninth grade, and a check that each tutorial runs under its promised length.
- [ ] **Two small checks:** save `.cmd` and `.bat` files without a byte order mark, and make Replace take a `$` in the replacement as typed unless Regex is on.

## Part 5. Other queued work

- [ ] **Microsoft Copilot SDK 2.0** (Ignite 2026, https://www.thurrott.com/a-i/microsoft-copilot-a-i/344006/ignite-2026-microsoft-copilot-sdk-2-0-is-now-available): read it and say what it means for QUILL's AI (`docs/design/codex.md`, Choose Your AI, the Copilot chat code).
- [ ] **Quill Cast queue, from Chris Nova (2026-11-17):** with two items in the queue, the first finished and the second did not start until he started it.
  - Found and fixed in #1889: when the next episode cannot start (nothing downloaded, no address), Cast stopped and said nothing. It now says why.
  - Simulated on 2026-11-18 with two real MP3s through the real Cast window, library, queue and libmpv: downloaded and streamed episodes both advance on their own. Not reproduced.
  - Not tested: the Windows Media engine (used when libmpv is not installed), which runs only on Windows. Next: ask Chris which engine he uses and whether the episodes were downloaded or streamed, or try it on a Windows machine.

## Part 6. The Workbench delivery checklist

Below is `complete.md` (2026-11-10) as it was.

**Owner:** Jeff Bishop / Community Access  
**Created:** 2026-11-10  
**Purpose:** One master delivery checklist for the redesigned Workbenches in QUILL and QUILL Lite.  
**Product direction:** Account for every available REST/API capability, and turn that coverage into understandable, delightful, accessible workflows.

### 1. Destination and rules for this list

The destination is two exceptional native Workbenches sharing one engine: people can discover what is possible, understand what matters, perform the work safely, and recover their place. API coverage is the completeness measure; excellent task flows are the product.

An API operation is accounted for only when its exact capability, permissions, limits, target host/version, UI home, help, and delivery state are recorded. A menu label, generic route listing, planned classification, or API Console alone does not prove a polished feature is finished.

**Checklist states**

- **OPEN:** the implementation record explicitly identifies unfinished work.
- **AUDIT:** code or a prior PR claims implementation; establish current behavior and evidence before deciding whether more coding is needed.
- **DEPENDENCY:** requires another repository, runtime package, supported server/plugin, account, or live environment.
- **PROPOSAL:** a new design recommendation. Recording it does not make it an accepted requirement.
- **SUPERSEDED:** historical wording replaced by a later decision; reconcile the records rather than rebuilding it.

All unchecked requirement-ledger entries below mean “acceptance evidence still needs to be attached,” not “nothing has been built.” Do not estimate a completion percentage from module counts, PR titles, route counts, or this document's checkboxes.

#### Definition of finished

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

### 2. Sources and precedence

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

#### Decisions already recorded

- The classic GitHub Items/Explore and WordPress management-window fallback choices are retired; editor doors open the Workbench.
- Alt+Enter opens Properties; ordinary typing remains type-ahead. Do not revive per-property letter shortcuts.
- The current first-class WordPress plugin integrations are QAF, Gravity Forms and Paid Memberships Pro. Earlier additional plugin candidates remain historical/deferred scope unless explicitly restored.
- Generic WordPress route/schema/Abilities discovery remains in scope. Therefore **all other plugins' discovered APIs must still be accounted for**, even when a polished plugin-specific integration is deferred.
- Provider credentials and checkout stay plugin-owned. QUILL does not become a payment gateway or collect provider secrets.
- The accepted GitHub roadmap assigns the user manual Windows assistive-technology acceptance. Engineering completion must not imply that those checks occurred.

#### Resolve specification drift

- [ ] Make one decision register linking every superseding decision to affected PRD sections, roadmap rows, tests, help and manual text.
- [ ] Reconcile WordPress PRD decision 17 (“Across Sites” still described as awaiting confirmation) with its Must requirements and already recorded W8 implementation; record the authoritative disposition.
- [ ] Reconcile original plugin-specific promises with the later three-integration scope. Account for every discovered route without silently promising bespoke support.
- [ ] Reconcile “one release of classic fallback” language with its recorded retirement.
- [ ] Reconcile historical G1–G5 and GX wave terminology with phases 0–13 and W0–W8; retain IDs and define their relationship.
- [ ] Remove stale “everything not listed is built” claims unless backed by a current coverage ledger.
- [ ] Replace old menu paths, token-only onboarding and obsolete publishing flags in release acceptance.
- [ ] Confirm which historical WordPress parity packages remain relevant to native Workbench delivery and which are superseded or deferred.

### 3. Baseline: what is recorded as implemented

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

### 4. First milestone: stabilize the current candidate

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

### 5. Coverage architecture: every API capability accounted for

#### 5.1 One operation ledger shared by both providers

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

#### 5.2 GitHub completeness

- [x] Vendor and pin the REST description and GraphQL schema; record provenance and licensing. *(Done 2026-11-13: `quill/data/github_api/` is refreshed from github/rest-api-description at commit 53fd7d2ea1380eabdcfcc9ab9a043a56ef444fd6 and docs.github.com's public schema.docs.graphql, both read 2026-11-13 and recorded in each file's `source`; the MIT licence is `quill/data/github_api/LICENSE-rest-api-description.txt`. A components.json notices entry is still to add, outside the GitHub files.)*
- [x] Implement Phase 11 coverage table, GATE-GITHUB-COVER and generated coverage chapter. *(Done 2026-11-13: `quill/core/github/api_coverage.json` + `api_coverage.py`, `tests/unit/core/test_github_api_coverage.py`, `quill.tools.github_api_coverage_audit` rostered in platform_report, and the generated "Everything GitHub can do, and where" chapter in `docs/github/workbench-reference.md`. 1626 rows: 302 covered, 1103 planned (the ceiling), 15 no_api_needed, 206 out_of_scope.)*
- [ ] Reconcile every operation in PRD Appendices E/F with the actual implementation, including GraphQL viewer permission answers and required reads.
- [ ] Track REST/GraphQL alternatives, preview/version headers, host compatibility, app/token types, organization policies and plan restrictions.
- [ ] Include pagination, ETags, secondary limits, GraphQL cost, cancellation and partial GraphQL errors.
- [ ] Reconcile enterprise-admin/migration exclusions with “all capabilities accounted for”: excluded operations still have a visible, justified ledger disposition.
- [ ] Validate GitHub Enterprise Cloud/data-residency and Enterprise Server capabilities per host/version; never send credentials to an unrelated host.
- [ ] Prove every existing Items/Explore action survives the redesign; no loss hidden behind a populated tree.

#### 5.3 WordPress completeness

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

### 6. GitHub delivery checklist

#### GH-A. Native parity, Properties, filtering and permissions — AUDIT

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

#### GH-B. Templates — DONE, Phase 12

- [x] Native YAML issue-form filling with required-field validation and golden body output. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Native discussion-form filling and category behavior. *(Done 2026-11-13: Ctrl+N on Discussions picks the category, fills `.github/DISCUSSION_TEMPLATE/<slug>.yml` in the issue-form window, falls back to title and body when there is no form or it cannot be filled; `quill/ui/github_workbench_templates.py`. The form's labels are not applied by createDiscussion, and the preview says so.)*
- [x] Templates node: Markdown/YAML issue forms, PR templates, discussion templates and applicable community files. *(Done 2026-11-13: Repository > Templates and Organizations > org > Templates, `quill/core/github/template_catalog.py`; own, inherited and missing rows; FUNDING.yml, CITATION.cff and CODEOWNERS open their own sheets (`quill/ui/github_template_sheets_dialog.py`), CODEOWNERS with Who Owns This Path. Since 2026-11-15, Check Owners asks GitHub whether each owner exists and can write (`quill/core/github/codeowners_check.py`).)*
- [x] Accessible builder, raw editor and preview with round-trip interop against real GitHub examples. *(Done 2026-11-13: `quill/ui/github_template_builder_dialog.py` and `quill/core/github/template_builder.py`; unknown keys survive the round trip. Since 2026-11-16, BFL (BITS Accessible Forms' language, the plain-text form language) interop too: `quill/core/forms/interop_github.py` maps the QAF model to GitHub's schema and back, GitHub-only keys ride in `@extensions`, and QUILL's own five issue forms round-trip through BFL unchanged (`tests/unit/core/forms/test_forms_interop_github.py`).)*
- [x] Field kinds, IDs, options, required settings, conditional/unsupported syntax, duplicate names and server constraints are checked before save. *(Done 2026-11-13: `template_builder.check`; errors stop Save, warnings do not; labels and assignees are checked against the repository's own and picked from them; Check This File on a `.github/ISSUE_TEMPLATE` or `DISCUSSION_TEMPLATE` YAML file puts each problem on its line (`quill/core/problems/builtin.py`).)*
- [x] Starters, conversions, repository/.github organization defaults and template chooser behavior. *(Done 2026-11-13: bug, feature, accessibility and blank starters; Markdown template to form and form to Markdown (says what it loses first); SurveyJS, XLSForm and QAF through `template_convert.qaf_to_draft`; since 2026-11-15 New Template > Issue form > From a SurveyJS or XLSForm file... is the door for files (`quill/ui/github_workbench_form_file.py`), and since 2026-11-16 Tools > Forms in both editors has Save As GitHub Issue Form and Open GitHub Issue Form (`quill/ui/forms_github_commands.py`), with `template_convert.qaf_to_draft` now `interop_github`'s export; inherited owner/.github rows and Organizations > org > Templates; the Template Chooser sheet (blank issues, contact links, order saved as numbered renames); New Pull Request offers the repository's pull request templates.)*
- [x] Save to branch or PR according to protection; conflict-check and verify contents. *(Done 2026-11-13: `quill/core/github/template_save.py`; a protected default branch, or the check box, saves to a new branch and opens a pull request; a changed sha stops the save; the file is read back.)*
- [x] Copy to Repositories with variant/missing previews and per-target results. *(Done 2026-11-13: one file, or, from the chooser row, the whole issue template set with its chooser; one result per repository.)*
- [x] Oversized/unreadable/unsupported templates offer an honest fallback without losing a draft. *(Done 2026-11-13: a form the builder cannot read opens as source with the reason; bad source YAML is kept; a failed save reopens the window with the draft.)*

#### GH-C. Beyond parity — OPEN/AUDIT, Phase 13 and section 22

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

#### GH-D. Fill the remaining GitHub feature families — OPEN/AUDIT

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

#### GH-E. Across Repositories and Repository Sets — OPEN

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

#### GH-F. GX01–GX15 journey acceptance — AUDIT

The accepted roadmap table is reproduced in the coverage appendices. Close each row with a real journey, failure case and evidence:

- [ ] GX01 reference routing; GX02 attention queue; GX03 context-preserving navigation; GX04 CI diagnosis. *(2026-11-18: journeys, failure cases and test evidence in [docs/qa/github-journeys.md](./docs/qa/github-journeys.md). Open: a screen-reader pass of each. Writing GX04 down found a second Re-run Failed Jobs press sent a second request; fixed and tested.)*
- [ ] GX05 intake/triage; GX06 Projects/dependencies; GX07 local repository continuity; GX08 deep review. *(2026-11-18: the same document. Open: the screen-reader pass listed at its end.)*
- [ ] GX09 policy-aware merging; GX10 release/deployment evidence.
- [ ] GX11 security/dependencies; GX12 collaboration/knowledge; GX13 administration.
- [ ] GX14 workspace/service handoffs; GX15 optional grounded assistance; GX16 category-first cross-repository browsing.

#### GH-G. Reference lessons and client boundary — ACCEPTED

- [x] Reviewed The Chat Place v0.5.0 release notes and source. Keep the notes in [github-roadmap.md](./docs/planning/github-roadmap.md).
- [ ] Apply provider-neutral patterns: read long issue/PR/discussion threads as one structured page; preserve the selected row on return; say the actual outcome once through QUILL's existing feedback settings.
- [x] Do not add Claude Code, Codex, Copilot or other third-party chat clients, CLI session readers, transcript parsers, subagent protocols or provider-specific file restore. Any future AI assistance uses QUILL's existing provider and consent boundary and remains optional.

### 7. WordPress delivery checklist

#### WP-A. Shared frame, routing and parity — AUDIT

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

#### WP-B. Discovery, content model and custom fields — OPEN/AUDIT

- [x] Discover taxonomy rest_base and supported types, all statuses, query enums and type-specific terms without guessing. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Complete New per custom type and status child nodes, plus lists, filters and batch for every supported custom type. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Expose registered meta on term, user and comment Properties sheets; scalar fields and safely typed scalar lists save through the site's route.
- [x] Edit schema-backed arrays, nested objects, repeaters, galleries and relationships in labelled JSON fields; coerce nested scalar types, enforce required/enum/size constraints and keep unknown keys. Unsupported schemas stay read only.
- [x] Give the seven historically planned plugin orderings spoken labels and eliminate combination-test gaps. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Content Model: actual registrant, types/taxonomies/field groups, read-only versus editable definition clearly distinguished. *(Done 2026-11-13, S:\QUILL, uncommitted on codex/workbench-combined-2026-11-10.)*
- [x] Reconcile ACF read/write and other field-plugin promises with current integration scope; generic schemas remain accounted for. *(Done 2026-11-13: Advanced Custom Fields is read and written. Where the route's schema has an `acf` property, items, terms, users and comments get an Advanced Custom Fields page on Properties; a save goes back as `{"acf": ...}`, coerced against the schema, verified, and undone with Ctrl+Z (`field_plugins.py`, `workbench_edit.py`). Meta Box, Pods and CMB2 are classified in `field_plugins.FIELD_PLUGIN_SCOPE`: no adapter, their fields reached as registered meta, and `pods/v1` and `cmb2/v1` are deferred in the route coverage. Registered meta of every shape stays on the Meta and Custom Fields pages. ACF field-group definitions stay read only in wp-admin. Live check with ACF installed still to do.)*
- [x] Determine and record the QUILL Site Types dependency's delivery status; implement/create definitions, field kinds, accessibility kinds, site-defined kinds and Export as Code if retained. *(Done 2026-11-13 on the QUILL side. The plugin is `S:\code\quill-site-types` 0.1.0: one local commit, unpushed, tested only against its stand-in (`php tests/run.php`), never in a real WordPress. Against its contract (`quill-site-types/v1`), `quill/core/wordpress/site_types_plugin.py` and `quill/ui/wordpress_workbench_site_types.py` give Content Model: Define with QUILL Site Types... (Ctrl+N: a post type, a taxonomy, or a field group with `name: kind` fields checked against the site's kinds, the accessible ones included), Stop Defining... (content kept, Ctrl+Z defines it again), Export as Code (opened in the editor), Fields... (each field on its own sheet: kind, label, help, required, default and choices, or a new field; the whole group is sent, previewed, and Ctrl+Z puts it back) and Add a Field Kind... (a site-defined kind with how it is stored and a pattern; the plugin has no route to remove one, and the preview says so). Content Model lists what the plugin defines as editable, with its field groups. Coverage marks `quill-site-types/v1` covered. Tests: `test_wp_workbench_lockout_and_stamp_core.py` and `test_wp_workbench_lockout_ui.py`. Remaining outside this repository: install the plugin on the test site and run it live.)*
- [x] Verify schemas and permissions after plugin/theme/version changes; do not reuse stale capability claims. *(Done 2026-11-13: `workbench_site_stamp.py` stamps the WordPress version, namespaces, routes, plugins (where `activate_plugins`), the active theme (where `switch_themes`), your roles and capabilities. Every load past five minutes takes it again and always replaces the account and index; on any change the taxonomy and status cache is forgotten, types are discovered again, the tree rebuilt and the change said once. Turning a plugin on or off from the Workbench forgets the site's claims at once. Tests in both lockout test files.)*

#### WP-C. QAF, Gravity Forms, membership and spam — OPEN/AUDIT/DEPENDENCY

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

#### WP-D. Practice Site and runtime — OPEN/DEPENDENCY

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

#### WP-E. W7 bold workflows — OPEN/AUDIT

- [x] Copy to Site for posts/pages/media/menus/terms/forms/patterns: author mapping, name matching, uploaded media, rewritten internal links and explicit create/replace previews. *(Done 2026-11-13: `workbench_site_copy.py`; exact slug match then name for terms/menus, replace keeps the target's status, authors by username/name, files uploaded with alt/caption or reused, featured images, links in both schemes and block attributes, menus with their links; offered on media and menu rows too. Gravity Forms forms copy whole from `gf/v2/forms/<id>` (POST new, PUT same title), entries never read or sent. Not yet run against a live pair of sites.)*
- [x] Compare Sites and snapshots: completeness, omissions, restore/rollback contract, revisions and media handling are stated. *(Done 2026-11-13: `workbench_snapshot.py`; Compare covers posts, pages, patterns, categories, tags and menus and names what it omits, unreadable kinds and the bound; snapshots record unread parts and take media files only when asked; new Site > Put Back from a Snapshot (Ctrl+Alt+Shift+S) previews under RESTORE_TERMS.)*
- [x] Calendar: all sites/types, timezone/DST ambiguity and schedule previews; editable list equivalent. *(Done 2026-11-13: every site and each site's discovered types, failures shown as rows; `workbench_editorial.site_moment` refuses skipped times and asks first/second for repeated ones; new Item > Move to Another Day (Ctrl+Alt+Shift+D) previews in the site's time and yours. Custom types join once the site's types are discovered.)*
- [x] Editorial queue: reviewer, notes, send back, approve/schedule, contributor ownership and notification semantics. *(Done 2026-11-13: `wordpress_workbench_bold_queue.py`; reviewer chosen from the site's editors, note plus a local record and a Review Watch; approve/schedule on the site's clock with preview; Pending Review shows a Queue column ("2 of 5 waiting"); every outcome says WordPress sends no email.)*
- [x] Read Site as Document: menu/category scope, order, address/provenance, private content, bounded loading and export fidelity. *(Done 2026-11-13: `workbench_read_site.py`; whole site, one menu or one category; published only, protected pages counted out, 500-item bound stated, a header with address/scope/date, page headings nested and lists/links/alt text kept through html_to_markdown.)*
- [x] Watches: off until enabled, no duplicate chatter, first sample silent, site-answering no faster than 15 minutes, consent and explicit offline/stale state. *(Done 2026-11-13: first sample silent per site and per Watch; round claimed before it runs so two editors do not both speak; new site_down and review Watches; the Watches node shows last round, staleness and each site's answering state; a `health` Watch says a Site Health test whose status changed, per test, silent for non-administrators.)*
- [x] REST Console: real discovery/completion, capability/argument/result schemas, all write previews and Change History. *(Done 2026-11-13: reads the full index, completes as `wp/v2/posts/{id}` templates filled from parameters, Accepts box per method, required/unknown/enum checks in the write preview, What It Returns from OPTIONS; Save Request keeps a request (`workbench_rest_saved.py`, atomic, persistence entry) as a Tools > Saved Requests row (1 to 9), Run a Saved Request (Ctrl+Alt+Q), Forget a Saved Request (Ctrl+Alt+Shift+F). The capability line is still QUILL's table for core routes, since the index does not publish capabilities.)*
- [x] Export all promised formats, import spreadsheets and document folders as drafts, mapping previews and per-row results. *(Done 2026-11-13: CSV, Excel and Markdown table (the QUILL table); spreadsheet columns mapped with synonyms and the mapping previewed, publish/future rows made drafts; new Edit > Import a Folder of Documents (Ctrl+Alt+Shift+I) for Markdown, text and Word; a report line per row or file.)*
- [x] Optional plain-language batches resolve exact sites/targets and use the same permission/conflict/batch engine. *(Done 2026-11-13: Tools > Plain-Language Batch (Ctrl+Alt+B), `workbench_plain_batch.py`; a fixed non-AI grammar (status moves; add or remove a tag; by author, in category, on named sites or every site), exact-name resolution with no guessing, an editable checklist of the exact items, then write_refusal per site, check_conflict per item and run_batch. The AI command catalogue is not wired in: no Workbench-facing consent path exists for it, so the grammar is the whole path.)*

#### WP-F. By Name, Across Sites, Site Sets and Fleet — OPEN/AUDIT

- [x] Complete by-name **operations**, beyond listing: rename, split, merge, reassign, replace and find uses.
- [x] Terms/custom terms, custom field values, authors, media, patterns/parts, links, blocks/shortcodes and forms each have a usable place.
- [x] Across Sites scopes and Site Sets; Variants/Missing From and winning-version previews with per-site outcomes.
- [x] Complete Make Them the Same for themes, people and menus; install plugins on missing sites; compare global styles.
- [x] Cover terms, plugins, themes, people, settings, menus/navigation, patterns/starter pages/forms/content types and role-pages.
- [x] Account for redirects, application passwords and spam senders across sites where APIs permit.
- [x] Fleet health/backups/security/updates preserve unavailable, unknown and stale states per site.
- [x] Promote to Network only on actual supported network APIs with correct super-admin permission and consequences.
- [x] Classify every kind × site/site-set/all-sites/network × operation combination.

#### WP-G. Site administration sweep — OPEN/AUDIT, scope reconciliation required

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

### 8. Shared accessibility, help and reliability acceptance

#### Native interaction and assistive technology

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

#### Help and learning

- [ ] GH/WP help gates at zero for nodes, rows, controls, fields, actions and result explanations.
- [ ] Shared Part D D1–D20 help features apply to both providers, not only GitHub.
- [ ] Glossaries, Search Help, What Can I Do Here?, Do Something tasks, situation-aware explanations, printable/exportable help and Ask a Person.
- [ ] WordPress “How WordPress Thinks,” settings explanations using actual site examples, plugin-deactivation/update/deletion explanations and visitor-facing form help.
- [ ] Practice tutorials, first-week path and Break It on Purpose with safe recovery.
- [ ] Optional Ask the Workbench remains grounded in selected evidence, editable and consent-bound.
- [ ] Update GitHub/WordPress manuals, both editor guides, window reference, tutorials, keys, release notes and changelogs together.
- [ ] Generate HTML/EPUB with the accessible template, unique titles/language/landmarks/table semantics and correct links; sync installed/site copies.

#### Data, network and operations

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

### 9. Live validation and external dependencies

- [ ] GitHub live scenarios: multiple roles/accounts, protected branches, organization restrictions, rate limiting, private repositories, project fields, secrets, failure/retry and no-API fallbacks.
- [ ] WordPress current candidate: run the documented live regression on an authorized test site and distinguish existing site-side failures from regressions.
- [ ] Seed QAF, Gravity Forms, PMPro, custom types/taxonomies/meta, constrained roles and realistic media/content for the supported scope.
- [ ] Verify taxonomy discovery, nested fields, block notes, upload/chunking/regenerate sizes, media listening/watching and contributor restrictions where still unverified.
- [ ] Reconcile “90 pass / 4 site-side fail” from earlier branches with fresh final-candidate results; do not inherit old green evidence.
- [ ] WordPress.com onboarding: confirm application/client registration and the current OAuth path if still incomplete.
- [ ] Audit external QAF/BAF/Site Types branches, names, release state and dependency contracts before relying on historical “waiting on Jeff” notes.
- [ ] Verify packaged app behavior, not only source runs; include clean/offline Practice Site launch.
- [ ] Manual acceptance stays separately signed off by the user/testers; every blocked scenario names the missing environment or permission.

### 10. Bold design recommendations — PROPOSALS

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

### 10A. AI Workbenches and bring your own ChatGPT plan — PROPOSALS

**Added:** 2026-11-10, at Jeff's request to think more boldly about AI and a person's own ChatGPT subscription.  
**Status:** Product/design proposals plus an audit of existing foundations. These are not implementation or acceptance claims.

#### 10A.1 The bigger product idea

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

#### 10A.2 What bringing a ChatGPT subscription can mean

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

#### 10A.3 Reuse the AI system that is already here — AUDIT

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

#### 10A.4 Platform capability boundaries that shape the design

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

#### 10A.5 Bold GitHub missions

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

#### 10A.6 Bold WordPress missions

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

#### 10A.7 Shared intelligence that makes both Workbenches more capable

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

#### 10A.8 Delightful accessible interaction

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

#### 10A.9 Execution architecture and all-API accounting

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

#### 10A.10 Delegation and automation policy

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

#### 10A.11 Roadmap for AI delivery

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

#### 10A.12 AI acceptance and product decisions

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

### 10B. Additions from the 2026-11-13 audits

Two read-only audits on 2026-11-13 added these: a comparison of GHManage
(`S:\code\ghmanage`, v1.0.0 to v1.2.0) against the GitHub Workbench, and an
API-family coverage audit of both Workbenches against this file, the PRDs and
the code. None duplicates an earlier line here. Items marked "probable bug" are
in QUILL's own code, found by reading it; GHManage was only the comparison.

#### 10B.1 Ported from GHManage

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

#### 10B.2 API coverage gaps: GitHub

- [x] **GHEC REST description (audit log, SAML credential authorizations).** Vendor GitHub's Enterprise Cloud OpenAPI description beside the api.github.com one and diff it, so GATE-GITHUB-COVER counts GHEC-only operations. User task: an org owner reads the audit log and revokes a member's SSO-authorized token. Home: Organizations > org > Audit Log and Organizations > org > Single Sign-On. Size M. *(Done 2026-11-13: `enterprise.json` now holds the 310 operations GitHub's own GHEC description has beyond api.github.com (commit 53fd7d2), replacing the hand-named rows. The organization audit log, SAML SSO authorizations and the other organization and repository features (custom roles, announcement banner, bypass and dismissal requests, Git LFS, Advanced Security committers) are planned under their homes; enterprise-account, SCIM, IdP group and closing-down routes are out_of_scope with reasons.)*
- [x] **GHES per-version descriptions.** Vendor the supported Enterprise Server descriptions and mark each ledger row with the first and last GHES version that has it, so an unsupported action on an older server is greyed out with its reason rather than failing. User task: use the Workbench against a company's GitHub Enterprise Server. Home: account Properties > Host, and every action's availability text. Size M. *(Done 2026-11-13: `ghes_versions.json` gives the first and last of GHES 3.18 to 3.22 for 1108 operations; 108 Server-only operations are out_of_scope rows. `api_coverage.unavailable_reason(key, server_version)` returns the greyed-with-reason sentence (needs a later version, removed after a version, or GitHub.com only) and `server_version_for_host()` is the hook. Accounts are GitHub.com only (`accounts.py` refuses other hosts), so it returns None and nothing greys until Enterprise Server sign-in exists.)*
- [x] **Enterprise identity dispositions (SCIM, enterprise teams, enterprise billing).** Record each as out_of_scope with a one-line reason and an Open on GitHub row so the gate is honest. User task: an enterprise admin learns where to go. Home: Organizations > org > Enterprise (Open on GitHub). Size S. *(Done 2026-11-13: SCIM (organization and enterprise), enterprise teams, enterprise billing and the enterprise audit log are out_of_scope rows with reasons and the Open on GitHub home; the 31 `/enterprises/` operations in the api.github.com snapshot and the 44 enterprise-admin mutations likewise.)*
- [x] **GraphQL read-query ledger.** Add query-only connections with no REST twin (pinnedItems, fundingLinks, contributionsCollection, dependencyGraphManifests, discussionCategories, starred lists) to the coverage table as rows with homes, not only mutations and viewer answers. User task: read your contribution table, a repository's sponsor links, or a profile's pins. Home: Account > Profile, Repository > General, People > person. Size S. *(Done 2026-11-13: `graphql_queries` in `api_coverage.json`, 21 rows: 15 reads the Workbench makes (discussionCategories, projectsV2, reviewThreads, subIssues, mergeQueue, viewerPermission and others) covered with their homes, and pinnedItems, contributionsCollection, fundingLinks, dependencyGraphManifests, star lists and linkedBranches planned with theirs.)*

#### 10B.3 API coverage gaps: WordPress

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

#### 10B.4 Usage, and the documentation pass

- [x] **AI usage.** Ctrl+8 speaks the connection, model and one usage clause where the service reports one (codex.md 10A.11). The local ChatGPT request count that `chatgpt_account.py` describes still has to be built and named as QUILL's own count, never the provider's allowance. *(Verified 2026-11-13: already shipped in #1728 -- `chatgpt_usage.record_request` counts plan requests, `connection_usage.which_ai_sentence` speaks the clause as a local count; 29 tests pass.)*
- [x] **GitHub Billing and Usage.** Account > Billing and Usage, read-only: Actions minutes, Packages and shared storage, Copilot seats where the account may read them; the menu has only a placeholder comment today. *(Done 2026-11-13: People > My Billing and Usage, read only, from the enhanced billing report.)*
- [ ] **Documentation pass at the end of each delivery batch.** Release notes, announcements, What's New, both PRDs and their status page, the QUILL and QUILL Lite user guides, the GitHub guide and the WordPress and Forms guide, with regenerated HTML and EPUB siblings, written in Jeff's voice and matching what shipped.

### 11. Delivery order and ownership

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

#### Task record to use for every closure

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

### 12. Exhaustive source-derived acceptance ledgers

The following appendices retain the accepted requirement IDs and feature-family detail. Review each against the latest code; attach evidence before checking it off. A requirement may be partly implemented. Explicit later scope decisions override historical wording, but every API capability still requires a disposition.


#### Appendix A. GitHub accepted requirements — verify every ID


Each requirement has an id, a strength (**Must** ships before the Workbench is
the default; **Should** ships in the program; **May** if time allows) and
the section that designs it. Each Must has at least one test, named in the
phase's PR. Ids are never renumbered; a dropped requirement keeps its id with
"withdrawn".

#### E1. The window and its panes

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

#### E2. The tree

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

#### E3. Menus and context menus

- [ ] **AUDIT** GH-R-020 Must: every menu row shows its key; no key is claimed twice;
  greyed rows carry a reason (4).
- [ ] **AUDIT** GH-R-021 Must: context menus hold only rows for the selected row type, the
  default first and Properties last, with More mirroring the Item menu (5).
- [ ] **AUDIT** GH-R-022 Must: Codespaces appears only on repositories, branches and pull
  requests; Rate Limit on no context menu (5).
- [ ] **AUDIT** GH-R-023 Must: menus, context menus, Shift+F1 and sheets are
  all built from one action table (10, 18.6, D5).

#### E4. Properties

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

#### E5. Editing

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

#### E6. Filtering

- [ ] **AUDIT** GH-R-050 Must: one query, written by the filter box, the Filter Builder,
  the Filter menu and Show Only or Hide on cells, all in step (17.1).
- [ ] **AUDIT** GH-R-051 Must: every attribute GitHub search supports is sent to GitHub;
  every other attribute filters locally with an honest status line and Load
  All (17.3).
- [ ] **AUDIT** GH-R-052 Must: every list attribute has "has none"; every person field has
  "Me" (17.2).
- [ ] **AUDIT** GH-R-053 Must: filters can be saved as searches and pinned as nodes (17.1).
- [ ] **AUDIT** GH-R-054 Should: Or groups where GitHub search allows them (17.2).

#### E7. Permissions

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

#### E8. Templates

- [ ] **AUDIT** GH-R-070 Must: issue forms and discussion forms are filled natively, with
  bodies identical to GitHub's (21.7).
- [ ] **AUDIT** GH-R-071 Must: every template kind in 21.2 can be listed, created, edited
  field by field, checked, previewed and saved (21.3 to 21.6).
- [x] GH-R-072 Should: forms can be written as BFL and converted to and from
  GitHub's schema through `interop_github.py` (21.4). *(Done 2026-11-16.)*
- [ ] **AUDIT** GH-R-073 Should: Copy to Repositories for templates and community files
  (21.6, 21.8).

#### E9. Beyond parity

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

#### E10. Keyboard

- [ ] **AUDIT** GH-R-090 Must: every key in Part C passes the checks in C1 before adoption
  and lives in the Workbench's `APP_KEYMAPS` entry.
- [ ] **AUDIT** GH-R-091 Must: the families of Part C hold: Ctrl+number goes, Alt+number
  says, F-keys keep Windows meanings, and Alt+Enter is the one key that
  changes things.
- [ ] **AUDIT** GH-R-092 Must: typing always moves through the tree and lists; no letter
  is ever a command (16.3).
- [ ] **AUDIT** GH-R-093 Must: every key is rebindable, and the rebinding follows into
  menus, the reference, Shift+F1 and the Key Describer (C10).

#### E11. Help

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

#### E12. Speech, braille and sound

- [ ] **AUDIT** GH-R-110 Must: the Workbench announces only what the reader cannot see
  (results, background changes, Watches) and nothing on focus, title or
  selection (GATE-13).
- [ ] **AUDIT** GH-R-111 Must: every announcement is also brailled (GATE-BRAILLE).
- [ ] **AUDIT** GH-R-112 Must: one sentence per outcome, naming what changed (A8).
- [ ] **AUDIT** GH-R-113 Must: sounds go through the shared action-feedback channels; a
  failure or a count is always spoken (A8).
- [ ] **AUDIT** GH-R-114 Should: a braille-shaped row option (22.4).

#### E13. Settings

- [ ] **AUDIT** GH-R-120 Must: every GitHub preference lives in Workbench Options, stored
  in `github_workbench.json` through `workbench_prefs.py`, shared by both
  editors; nothing GitHub in the main Options (4.1).
- [ ] **AUDIT** GH-R-121 Must: the three poll settings migrate out of the main Settings
  once, with the vocabulary audit and GATE-SETDOC regenerated (4.1).
- [ ] **AUDIT** GH-R-122 Must: the Workbench is fully usable without opening Workbench
  Options (4.1).

#### E14. API use

- [ ] **AUDIT** GH-R-130 Must: only `api.github.com`, `github.com` sign-in pages,
  `uploads.github.com` for assets and, with consent, githubstatus.com; each
  new endpoint family named in the network egress audit (18.6).
- [ ] **AUDIT** GH-R-131 Must: conditional requests (ETag) for every repeated read
  (`conditional_requests.py`), and secondary rate limits respected.
- [ ] **AUDIT** GH-R-132 Must: GraphQL where it is the only API (Appendix F) and where one
  query replaces many REST calls; REST otherwise.
- [x] **AUDIT** GH-R-133 Must: the vendored API snapshot and `api_coverage.json` drive
  GATE-GITHUB-COVER (19, Appendices E and F). *(Done 2026-11-13: see 5.2.)*

#### E15. Teams

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

#### E16. Across repositories

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

#### Appendix B. WordPress accepted requirements — verify every ID

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

#### Appendix C. Accepted GX delivery and acceptance matrix

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

#### Appendix D. GitHub historical missing-feature inventory

Source: PRD section 14. Its “today” statements describe the source audit revision, not a fresh code audit. Reconcile each row, including features subsequently implemented in phases 7–10.

#### 14.1 Worth adding (people will look for these)

| Feature | Status today | New home |
|---|---|---|
| Close reason: completed, not planned, or duplicate of #n | **Built:** Close or Reopen... asks the reason (2026-11-17); Not a Duplicate... takes the mark back (2026-11-18, `issue_links.py`) | Item > Close Issue... asks the reason; the details pane shows it |
| Linked pull requests and branches for an issue ("Development"), and "create a branch for this issue" | **Built:** the issue sheet's Relationships page and Create Branch for This Issue... (2026-11-17); Unlink Branch... (2026-11-18, `issue_links.py`) | Issue details; Item > Linked Pull Requests; Item > Create Branch for Issue... (next to Start in Local Worktree) |
| Saved replies | **Built 2026-11-17:** Insert Saved Reply in the comment window (`comment_compose.saved_replies`, `viewer.savedReplies`); GitHub has no API to make or edit them, so that stays on GitHub | Item > Insert Saved Reply in every comment box; Tools > Workbench Options > Saved Replies |
| Wiki | **Partly built 2026-11-18:** Repository > Wiki says whether it is on; Clone Wiki... (`Ctrl+Alt+W`) copies its pages to edit as Markdown (`wiki.py`). GitHub has no wiki API, so listing pages in the Workbench remains | Repository > Wiki (pages as a list, read in details, edit in the editor) |
| Repository invitations: accept or decline | **Built 2026-11-18** (`repo_invitations.py`) | Needs My Attention > Invitations |
| Edit description, website and features (issues, wiki, discussions, projects on or off) | **Built:** the repository sheet's Description and feature switches (`sheets_repo.py`) | Repository > Settings > General |
| Rulesets: read them | **Built:** the ruleset sheet (`sheets_code.py`, `rulesets.py`) | Repository > Settings > Rulesets (read-only list; editing stays on github.com) |
| Enable or disable a workflow | **Built 2026-11-18:** Turn Workflow On or Off... (`workflow_state.py`) | Workflow context menu; Item menu |
| Revert a merged pull request | **Built:** Revert... on a merged pull request (`revert_pull`) | PR context menu > More > Revert... |
| Security policy, private vulnerability reports, repository security advisories | **Built 2026-11-18:** Security > Policy and Advisories, private reports and drafts, publish, close, request a CVE, and the Advisory Database search (`security_advisories.py`); comments and private forks remain | Repository > Security > Policy; Security > Advisories (roadmap GX11) |

#### 14.2 Worth adding later (useful, less often)

| Feature | Status today | New home |
|---|---|---|
| Packages (GitHub Packages, container registry) | **Built 2026-11-18:** Repositories > My Packages, with Delete Package Version... and Delete Package... (`packages.py`); an organization's packages and restoring followed the same day | Repository > Packages; Repositories > My Packages |
| Teams and organization members | Out of scope by a code comment ("Organizations in, Teams out"); roadmap GX13 adds team permissions. Now in scope: section 18.3.3 | Repositories > Organizations > org > Members, Teams; People > My Teams |
| Insights charts as tables: commit activity, code frequency, punch card | **Built 2026-11-18:** Repository > Insights > Commit Activity (`repo_activity.py`): weekly commits, code frequency, the ten busiest hours, participation and contributors, as sentences | Repository > Insights (tables, never charts only) |
| Dependency graph and software bill of materials (SBOM) export | **Built 2026-11-18:** Repository > Export Software Bill of Materials... (`Ctrl+Alt+B`), SPDX file (`runners_sbom.py`) | Repository > Security > Dependencies |
| Tags: create and delete outside a release | **Built 2026-11-18:** New Tag... and Delete Tag... (`tags.py`); annotated tags with a message, and Read Tag Message | Repository > Code > Tags context menu |
| Hide a comment (moderation: spam, off-topic, outdated) | Not found | Comment context in details > Hide Comment... |
| Transfer a repository | **Built 2026-11-18:** Repository > Transfer Repository... (`Ctrl+Alt+T`), typed confirmation (`repo_transfer.py`) | Repository > Settings > Transfer... |
| Self-hosted runners | **Built 2026-11-18:** Repository > Actions > Runners (`runners_sbom.py`); New Runner (setup commands to the clipboard), Runner Labels and Remove Runner followed the same day (`runner_admin.py`) | Repository > Actions > Runners (read-only) |
| Star lists | **Built 2026-11-18:** Repositories > Star Lists, New Star List..., Star Lists... on a repository, Rename or Delete Star List... (`star_lists.py`) | Repositories > Starred > each list |
| Your profile and status | **Built 2026-11-18:** Account > Set Your Status... (`user_status.py`); People > My Profile and each person's Profile (`profile.py`) | Account > Profile and Status... |

#### 14.3 Brought in after all (Jeff, 2026-11-09: "If I can do it in GitHub I should be able to do it")

The first draft of this plan left these to github.com on purpose. Jeff's
brief overrules that: risk is answered with permission checks, previews and
typed confirmations (section 18.4), not by leaving a feature out. Each now has
a home and a Properties sheet:

- **Webhooks:** Repository > Settings > Webhooks, and the same for an
  organization. Create, edit the address, content type and events (every
  event GitHub offers, as a check list), turn on or off, see recent
  deliveries and their responses, redeliver, ping. The webhook secret is
  write-only: you can set a new one, never read the old one. *(Repository
  webhooks built 2026-11-18, `repo_settings_lists.py`, and an
  organization's the same day.)*
- **Deploy keys:** Repository > Settings > Deploy Keys. Add (title, key,
  read-only or read-write), delete. The key text is shown as GitHub shows it.
  *(Built 2026-11-18.)*
- **Autolink references:** Repository > Settings > Autolinks. Add a prefix and
  URL template (alphanumeric or numeric), delete. *(Built 2026-11-18.)*
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
- **SSH and GPG keys, SSH signing keys:** Account > Keys. List, add, delete. *(Built 2026-11-18 as People > My Keys, `account_keys.py`.)*
- **Personal access tokens:** an organization owner can review, approve and
  deny fine-grained token requests, and revoke access, under Organizations >
  org > Token Requests. Creating a token has no API, so Account > Tokens
  opens the right GitHub page and the Workbench checks the result
  (section 18.1). *(2026-11-18: not possible. GitHub serves the token-request
  and token-grant endpoints to GitHub Apps only, so a person's sign-in is
  refused; the coverage table marks them out of scope with that reason.)*
- **Sponsors:** People > person > Sponsor, and Account > Sponsors for your
  own sponsorships and sponsors, read and manage what the API allows. *(Built
  2026-11-18: People > Sponsorships and each person's Sponsor, sponsoring at a
  tier with the login typed, and cancelling; `sponsors.py`. Running a
  sponsors listing of your own, its tiers, stays on GitHub.)*

What is left on github.com is only what GitHub offers no API for, and the
coverage table says so row by row (section 19): Marketplace purchases,
creating a token, changing your password or two-factor settings, and
enterprise-level billing. Each still gets an "Open on GitHub" row in its
natural place.

#### Appendix E. Cross-repository kinds and operations

Every row needs single-repository coverage, all applicable scopes, permission checks, preview/conflict handling and per-target results.

#### 22.11 Across repositories: every kind of thing, by name, everywhere

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

#### Appendix F. WordPress site-administration and cross-site inventory

This is the accepted source inventory. First-class adapters beyond the later approved plugin scope need an explicit delivery decision. Deferred adapters do not remove APIs from the accounting ledger. Original “to verify” labels remain unverified until evidence is attached.

##### 15.11 The third sweep: what running a real site also involves

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

##### 15.12 Across sites, and across the whole site: every kind of thing, by name

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

#### Appendix G. API-family reconciliation checklist

The PRD operation appendices remain the detailed source. These family-level checkboxes are an index, not a substitute for method/route/field-level accounting. Snapshot totals are historical and must be refreshed.

##### GitHub REST and GraphQL families

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

##### WordPress recorded index families

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

#### Appendix H. Observed failing tests on PR #1837

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

#### Appendix I. Closure review

- [ ] Current CI snapshot refreshed and all candidate blockers resolved.
- [ ] Accepted requirement IDs reconciled without omissions or duplicate closure claims.
- [ ] Every API operation has a disposition; every deferred operation has a reason and destination.
- [ ] Native UX, schema/console usability and acceptance completion reported independently.
- [ ] Both applications, account/site isolation and unsupported-host behavior verified.
- [ ] External dependency and packaged-runtime evidence attached.
- [ ] Live and manual accessibility acceptance signed off separately.
- [ ] Documentation and installed artifacts reflect actual released behavior.
- [ ] Product owner has a clear next-release boundary and later backlog.

#### Appendix J. QuillVille WinGet and startup work (2026-11-12)

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


## Part 7. Design companion: delight without clutter

Below is `complete2.md` (2026-11-10) as it was.

**Prepared for:** Jeff Bishop / Community Access  
**Date:** 2026-11-10  
**Status:** Design recommendations for review; not approved scope or implementation claims.  
**Companion:** [GitHub/WordPress completion and AI vision](./complete.md).

### 1. The aim

The family should feel considerate: it remembers what matters, tells the truth, makes the next useful action easy, and lets people recover without a struggle.

Delight can be a small moment: returning to the exact sentence you left, hearing that a recording actually contains the microphone, finding a completed file immediately, or changing a setting and understanding the result. These moments earn their place because they remove effort or uncertainty.

**Recommendation:** improve a small number of shared interaction contracts and apply them carefully in each app. Keep every app's purpose and familiar layout. A shared behavior does not require a shared dashboard, a new assistant, or another window.

#### The admission test for a proposed change

Keep an idea only when we can answer:

1. What real task or recurring frustration does it address?
2. What does the person do before and after the change?
3. Which existing control, store or command can carry it?
4. Can it reduce decisions, interruptions or steps?
5. Can a person discover and use it by keyboard, speech and braille?
6. How will we observe that it helped?
7. What should we remove, simplify or avoid adding in exchange?

Feature count, cleverness, engagement time and AI usage are not success measures. Task success, confidence, retained work and low effort are.

### 2. What the source already provides

This is a targeted source-and-document survey, not a live usability test. Presence of a module is not proof of complete adoption or acceptance in every app.

| Foundation inspected | Consequence for this plan |
| --- | --- |
| [App launcher and release gates](./quill/core/app_launcher.py) | Apps already open one another. Improve context and outcomes rather than proposing a second launcher |
| [Action feedback](./quill/core/action_feedback.py) | Sound/speech/both/silent already exist. Improve consistency without replacing established defaults |
| [Notifications](./quill/core/notifications.py) | Durable notices and actionable targets already exist. A new family inbox needs to prove value beyond this |
| [Session restoration](./quill/core/session_restore.py), [recovery triage](./quill/core/recovery_triage.py) | Restore and recovery already address real problems. Extend continuity without restoring clutter or silently discarding meaningful work |
| [Shared preferences](./quill/core/family_preferences.py) | Sharing is deliberately narrow and opt-in. Do not casually synchronize keys, focus behavior or account state |
| [Quick Actions](./quill/core/quick_actions.py) | User ordering/default actions already have a mechanism. Preserve deliberate arrangements instead of adding automatic menu reshuffling |
| [Audio routing](./quill/core/app_sound_route.py) | Audit existing ownership/routing before adding family-wide media control |
| [Family data contract](./docs/design/FAMILY-DATA.md) | Shared state has ownership/versioning obligations; a new convenience cannot risk another app's data |
| [Radio surface design](./docs/planning/radio-surface-design.md) | A favorites-first surface and controls one action away are deliberate. Do not restore permanent button rows |
| [Current Studio plan](./docs/planning/QUILL-Studio-PRD.md), [recording/preview proposals](./docs/planning/studio-demo-roadmap-proposals.md) | Rehearsal/routing/verification already have accepted or proposed scope. Connect proposals to that work rather than rebuilding it |
| [Reviewing documents by ear](./docs/design/2026-10-04-plancake-lessons.md) | Notes, exact places, safe saves and outcome-only feedback already have a detailed design history |
| [Command Key design](./docs/design/command-key.md), [AI family design](./docs/design/codex.md) | Discovery, Ask and task engines have a shared home. Reuse them |
| [Beacon purpose](./standalone/beacon/README.md), [Social purpose](./standalone/social/README.md) | Exact-place saving and context-preserving reading already have product homes; avoid duplicating whole products |

Some planning/app overview documents describe older release states. Before implementation, verify current source, packaged behavior, accepted decisions and public release gates. Recommendations for Studio, Cast, Player, Beacon or Social do not authorize exposing a gated app or assuming its live integration is complete.

### 3. The five changes I would prioritize

| Rank | Proposal | Why it matters | First place to prove it |
| --- | --- | --- | --- |
| 1 | FUX-01: Return to the exact place | People spend less effort reconstructing their own work | QUILL Lite reading/editing, then Cast or Player |
| 2 | FUX-04: Useful, truthful completion | A job ends with a result the person can find and act on | Converter batch, then Transcribe export |
| 3 | FUX-06: Lists that respect the reader | Background work stops moving the thing someone is trying to read | Radio browsing, then Cast/Social/Workbench lists |
| 4 | FUX-07: Text always goes to the intended place | Dictation and abbreviation expansion feel dependable | Transcribe and Inkwell |
| 5 | FUX-03: Know where sound is coming from and going | Listening and recording become less confusing and more verifiable | Radio plus Studio rehearsal |

These rankings reflect expected user value from the surveyed architecture, not measured severity. If observation finds a frequent lost-work, misleading-state or inaccessible-control defect, that defect comes first.

### 4. Sixteen proposals worth considering

#### FUX-01 — Return to the exact place, with a useful way back

**Moment:** “I was interrupted. Let me continue without finding everything again.”

**Change:** Preserve the meaningful place, not only an open file or URL: document passage and selection, podcast episode/time, transcript segment, selected station/category, or list item/filter. When navigating elsewhere, preserve the origin so Back returns to the exact source.

**Keep it small:** Use existing restoration and navigation. No mandatory Start screen. A normal reopen can simply restore the place; show a choice only when recovery, several competing sessions or a changed resource makes one necessary.

**Important detail:** A timestamp/line number may drift. Use existing stable identifiers or Beacon location resolution where appropriate; if exact recovery fails, say what was restored and offer the nearest verified place. Do not guess silently.

**First pilot:** Read a long document, follow a link or open an associated recording, then return. Repeat after restart and after the source has changed.

**Acceptance**

- [ ] The original passage/item and reading context are restored where supported.
- [ ] Missing/moved content remains visible and understandable.
- [ ] Live radio is not represented as a seekable recording.
- [ ] A recovered recording or draft is not automatically played, sent or published.
- [ ] Observe time and wrong turns needed to resume, compared with the current app.

**Existing overlap:** session restoration, Beacon locations, and the Workbench context-bookmark proposals. This extends their reach and consistency.

#### FUX-02 — Carry the work between apps, including the reason

**Moment:** “Transcribe this part of my recording,” or “Open that transcript in QUILL.”

**Change:** Handoffs carry an explicit source, selected range, intended destination and useful metadata. A receiving app opens the right object at the right place and makes the originating app reachable again.

**Examples:** A Studio time selection becomes a Transcribe task; its result opens in QUILL with source time references. A Cast passage saved in Beacon returns to the episode at the relevant point. A Converter output opens in the intended installed player.

**Keep it small:** Put the action where the object is already selected. Reuse the existing launcher/deep links and product boundaries. No required family portal.

**Acceptance**

- [ ] Distinguish passing a reference, making a copy and creating a transformed output.
- [ ] Preserve the original and explain where the new artifact lives.
- [ ] Unavailable/gated destinations offer a useful save/export path without an installation detour.
- [ ] Do not change the receiving app's playback, microphone or account choice unexpectedly.
- [ ] Return to the origin restores its selection.
- [ ] Exercise portable installs, missing apps, duplicate names, changed files and unavailable remote resources.

**Existing overlap:** sibling launch, Beacon, Studio/Transcribe plans and AI mission handoff. The extra value is a dependable artifact/context contract.

#### FUX-03 — Make audio ownership understandable

**Moment:** “Something is playing. Which app is it? Is the screen reader going into my recording?”

**Change:** Within the relevant app, expose a concise, on-demand account of active media, playback destination, recording inputs and monitored versus recorded sound. When another family app requests media control, make the consequence explicit at the point of conflict.

**Keep it small:** Reuse status cells, transport commands and existing audio-routing controls. No permanent family mixer floating over every app.

**Design details**

- A reliable “What is playing/recording here?” command, reachable through existing command discovery; assign any new shortcut only after a family key audit.
- Distinguish pausing a player from stopping a recording or muting a monitor.
- On device loss, report the actual affected route. Do not silently move a private monitor or microphone to a new destination.
- Headphone/device return can offer a deliberate recovery of the previous route.
- Ducking or pausing another app is a user choice; preserve configured accessibility feedback and Weather alert policies.

**Acceptance**

- [ ] Play Radio while rehearsing a Studio recording and determine each route without sight.
- [ ] Listen back to a real short test capture to verify what entered the recording.
- [ ] Identify and recover a disconnected input/output device.
- [ ] OS/device limitations are stated; a configured route is not reported as proof of captured audio.

**Existing overlap:** app sound routing and Studio's source/bus/rehearsal plans. Improve the common explanation and conflict behavior.

#### FUX-04 — Finish with the actual result and the next useful action

**Moment:** “It says complete. Where is my file, and did every item work?”

**Change:** The end of a job provides an understandable receipt: what succeeded, where it went, what is partial and the next appropriate action. “Converted 4 of 5 files. One needs attention. Open results / Retry failed.”

**Keep it small:** Extend existing task results and durable notices. A successful single-file save usually needs only its normal confirmation and reachable result; do not open a report window every time.

**Acceptance**

- [ ] A completed output can be opened or located with keyboard commands from its result.
- [ ] Result identity survives duplicate file names; show enough path/source information to distinguish them.
- [ ] Keep successful items when retrying failures.
- [ ] Cancellation says what exists, what is incomplete and what can resume.
- [ ] Output validation is reported separately from processing completion.
- [ ] A delayed result does not steal focus from the document someone is now writing.
- [ ] After missing the spoken notification, the same useful result remains reachable.

**Existing overlap:** notifications, recent problems, task/AI activity and batch result infrastructure.

#### FUX-05 — Recovery that speaks in terms of the person's work

**Moment:** “I changed the wrong thing. Can I get back?”

**Change:** Undo/recovery names the action and object: “Undo changing this paragraph,” “Restore the previous export settings,” or “This remote publication cannot be undone here; open the published item.”

**Keep it small:** Improve existing undo, checkpoints and recovery surfaces. Avoid another universal history database that stores every piece of private content.

**Acceptance**

- [ ] The proposed recovery names what will change and what cannot be restored.
- [ ] Local edits preserve ordinary undo grouping and selection.
- [ ] Recoverable drafts and original files are distinct from disposable caches.
- [ ] Destructive or remote actions are not labelled undoable until recovery is verified.
- [ ] Review ambiguous duplicates instead of silently declaring one copy worthless.
- [ ] Include failures during undo and recovery, not only successful cases.

**Existing overlap:** recovery triage, local undo, Workbench history and AI checkpoints. The proposal improves predictability and language across them.

#### FUX-06 — Let lists update without moving the reader

**Moment:** “I was reading that episode/post/station, and a refresh moved everything.”

**Change:** Maintain focus and selection by stable item identity. Gather new arrivals without replacing the item being read. Let the person reveal new content deliberately; when the selected object disappears, explain that fact and choose a predictable neighbor.

**Keep it small:** Use a shared update/selection contract in existing lists. A small “new items available” state is enough; no animated feed or automatic resorting.

**Acceptance**

- [ ] Refreshes do not move focus, restart details reading or repeatedly announce unchanged data.
- [ ] The person controls when arrivals enter the current sorted reading list.
- [ ] Genuine object changes remain inspectable with a timestamp.
- [ ] Filtering/sorting retains the selection where valid and explains when it no longer matches.
- [ ] Expired/deleted content remains recognizable as such; no fabricated details.
- [ ] Test slow responses arriving out of order, reconnect, paging and multiple windows.

**First pilot:** Radio browsing, then episode/timeline and Workbench lists. Existing products may already implement much of this; audit adoption before coding.

#### FUX-07 — Protect the destination of dictated and expanded text

**Moment:** “I started dictating a message, but focus changed.”

**Change:** Transcribe and Inkwell keep the intended application/control visible and understandable before text insertion. If focus or target identity changes ambiguously, retain the captured text and offer a deliberate insertion or copy action.

**Keep it small:** Use existing Dictate Here and expansion controls. Do not ask for confirmation before every normal phrase or collect an ongoing keystroke history.

**Acceptance**

- [ ] The user can determine the current target and whether insertion is live or pending.
- [ ] Alt+Tab, dialogs, closed controls and application restart cannot redirect a pending insertion silently.
- [ ] Ambiguous targets preserve text instead of losing it.
- [ ] An expansion supports the existing literal/escape path and usable undo where the target allows it.
- [ ] Password/secure controls follow explicit platform-supported restrictions. Unknown platform state is not advertised as a proven secure-target detector.
- [ ] Explain target failures without reading private text aloud unexpectedly.
- [ ] Test with actual supported receiving applications and assistive tools.

**Why this ranks highly:** trust in system-wide input determines whether people will use the feature at all.

#### FUX-08 — Let people hear or see what a setting will do

**Moment:** “What does this option change? I don't want to break my setup.”

**Change:** For settings with meaningful observable effects, offer a short reversible preview: sample feedback, reading verbosity, export example or layout behavior. Show the setting's current value, where it applies and whether it is shared.

**Keep it small:** Use the existing settings/help surface and the narrow shared-preference contract. Many settings need only a better sentence.

**Acceptance**

- [ ] Preview has a clear end/cancel and restores prior state.
- [ ] Shared versus app-only scope is understandable before applying.
- [ ] Nothing silently synchronizes keys, focus behavior, microphone choices or credentials.
- [ ] A setting that needs restart says so; avoid pretending the preview is applied.
- [ ] No extra confirmation for ordinary reversible choices.
- [ ] People can undo the change without remembering the old value.

**Existing overlap:** Preferences Search, action feedback, sound previews, and shared preferences.

#### FUX-09 — Give the first useful task a clear beginning

**Moment:** “I installed this. What can I do successfully right now?”

**Change:** Empty states offer one or two actions that match the app's purpose, plus an optional tiny sample. A person can complete a useful task before learning the product's whole vocabulary.

**Examples:** Converter: choose files and a practical output. Radio: browse stations or add a known address. Transcribe: dictate into a scratch document or try a short bundled clip. Studio: record and listen to a short rehearsal.

**Keep it small:** No compulsory tour, account funnel, feature carousel, pop-up sequence or mandatory sample library.

**Acceptance**

- [ ] First-task wording is a genuine action with a keyboard path and visible label.
- [ ] Sample content is clearly marked, removable and never mixed into personal work.
- [ ] Declining the sample leaves the normal app ready to use.
- [ ] First tasks do not require a network, account or download unless intrinsic; name that dependency before asking.
- [ ] Observe time to first successful result and the places where new users stop.

**Existing overlap:** tutorials/help. The proposal joins them to the empty state instead of creating a parallel training product.

#### FUX-10 — Help that explains the selected situation

**Moment:** “Why can't I do this here?” or “What does that word mean?”

**Change:** Existing F1 and command discovery answer the question for the selected object and current state: what this is, what Enter does, which actions are available and why another action is unavailable.

**Keep it small:** Reuse the command catalogue and help engine. No separate search assistant or second command system.

**Acceptance**

- [ ] A disabled action has a readable reason and next step.
- [ ] Existing users retain menu paths and stable command identities.
- [ ] Search matches familiar intent/synonyms as well as exact labels.
- [ ] Context help knows source/live/file/draft/selection state where relevant.
- [ ] Help does not interrupt focus reading or open irrelevant product documentation.
- [ ] A short explanation can be expanded into a worked example or tutorial.

**Existing overlap:** Command Key, F1 help, Workbench help and AI Ask. Audit consistent application across products.

#### FUX-11 — Rehearse the real outcome before a long job

**Moment:** “I don't want to record an hour before finding the microphone was wrong.”

**Change:** Offer a small, representative trial using the exact proposed setup. Play/read/inspect the resulting sample and explain what was actually verified.

**Examples:** Studio captures ten seconds with current routes; Converter processes a representative input segment; Transcribe tries a chosen clip with names/language; a document export renders a representative page/table where practical.

**Keep it small:** “Try a sample” within the normal task, not another wizard. Cache a successful trial only for the configuration it actually tested.

**Acceptance**

- [ ] A sample does not replace the full result or alter the source.
- [ ] Input devices, formats and relevant settings match the eventual job.
- [ ] Sample limits are explicit; one successful page or clip does not prove the whole artifact.
- [ ] If the setup changes, earlier evidence is labelled stale.
- [ ] Every audition/preview has a nonvisual inspection path where meaningful.

**Existing overlap:** Studio preflight/rehearsal and other preview work. Integrate with those accepted plans.

#### FUX-12 — Compare changes in a way people can actually inspect

**Moment:** “Is that improvement better, or just different?”

**Change:** A meaningful transformation offers a focused comparison using the same selected passage or media segment. Explain what changed and let the user keep either version.

**Examples:** Loudness/denoise audition, transcript correction with source playback, AI rewrite compared paragraph by paragraph, format conversion with metadata/loss warnings.

**Keep it small:** Add a comparison action to the existing result/preview. Avoid mandatory review after every trivial edit.

**Acceptance**

- [ ] Preserve original and proposed versions until the person decides.
- [ ] Repeated playback compares the same region without restarting the whole file.
- [ ] Explain level matching where an audio comparison would otherwise favor the louder result.
- [ ] Text changes have heading/paragraph/changed-item navigation and source references.
- [ ] State format loss, omissions and uncertain semantic judgments plainly.
- [ ] “Keep this” applies exactly the reviewed result, not a newly regenerated version.

**Existing overlap:** document comparison, Studio preview and Workbench before/after plans. Family adaptation is the improvement.

#### FUX-13 — Be clear about live, downloaded, cached and unavailable

**Moment:** “Is this current? Will it still work when I lose internet?”

**Change:** Present the object's relevant freshness and availability as ordinary readable state, with a useful action.

**Examples:** “Forecast issued 40 minutes ago; update failed.” “Episode downloaded and playable offline.” “Station disconnected; reconnecting.” “Draft saved on this computer; not published.”

**Keep it small:** Extend existing status and details. No connectivity dashboard.

**Acceptance**

- [ ] Source/observation/retrieval times are distinguishable where they matter.
- [ ] Cached data is not represented as a current observation.
- [ ] Reconnect behavior does not replay a send, restart a recording or mark remote items read.
- [ ] Users can deliberately prepare selected media/documents for offline use.
- [ ] Storage/expiry behavior is discoverable and controllable.
- [ ] Weather retains official wording and configured warning policies; summaries do not substitute for the authoritative alert.

**Why it matters:** accurate ordinary state creates more confidence than elaborate “smart” recommendations.

#### FUX-14 — Navigate meaningful structure, not just distances

**Moment:** “Take me to the next idea, chapter, speaker or finding.”

**Change:** Where structural metadata exists, let the person move through it with consistent interaction language: heading, chapter, speaker turn, marker, result, note or changed block. Clearly label model-generated structure.

**Keep it small:** Reuse each app's existing outline/list and the shared keymap/help conventions. Do not force every object into a new tree.

**Acceptance**

- [ ] Available structure is navigable and announced with name/type/position.
- [ ] Next/previous commands preserve expected playback/reading behavior.
- [ ] Distinguish timed transcript evidence from estimated alignment.
- [ ] Preserve navigation after edits where anchors can be remapped; explain otherwise.
- [ ] Never silently reassign established shortcut keys.
- [ ] Readable tables/lists accompany graphs, waveforms and visual timelines.

**Existing overlap:** document outlines, media chapters, transcript markers, Beacon and Workbench structure.

#### FUX-15 — Keep maintenance away from the moment that matters

**Moment:** “I'm about to record. Please don't make me manage software.”

**Change:** Installation/update/component checks explain what the current task needs and defer disruptive maintenance when recording, dictation or important background work is active.

**Keep it small:** Improve current updater/runtime flows. No new family store or all-app installer requirement.

**Acceptance**

- [ ] Identify the affected app/component and the exact useful capability it enables.
- [ ] A download/update failure leaves user files and the current usable setup intact.
- [ ] No forced restart during protected work.
- [ ] Show progress and a usable retry without stealing focus.
- [ ] Shared-runtime compatibility and portable installations are respected.
- [ ] Update notes emphasize changed user behavior and stable learned controls.
- [ ] App availability respects current release gates; installing one app does not quietly install the family.

**Existing overlap:** shared runtime, installer, update and migration work. This is a user experience contract across it.

#### FUX-16 — Turn a problem into a recoverable next step

**Moment:** “Something failed. I don't know whether to retry or start over.”

**Change:** Failure messages state the affected task, what was preserved, what is uncertain and one or two useful next actions. “Could not save to this folder. Your recording is still available. Choose another folder.”

**Keep it small:** Improve existing error language, Recent Problems and activity results. Keep diagnostic detail expandable.

**Acceptance**

- [ ] Preserve work before offering retry, alternate destination or export.
- [ ] Avoid “try again” when retry could duplicate a remote action.
- [ ] A support report can include versions and error context without sending private content by default.
- [ ] The user can inspect/redact included information and copy/save a report without sending it.
- [ ] Distinguish an unsupported feature, denied permission, unavailable dependency and transient failure.
- [ ] Return focus to a useful control after recovery.
- [ ] Confirm actual recovery; do not only dismiss the error.

**Existing overlap:** coded errors, stability/task management, recent problems and notification targets.

### 5. How these improvements should feel in each app

These are focused applications of the shared proposals, not commitments to add entire new subsystems.

| App | Meaningful improvement | What the person experiences | Scope caution |
| --- | --- | --- | --- |
| QUILL | Reading/review continuity with reliable comparison | Follow a source, annotate a passage, inspect a proposed revision and return to the exact place | Reuse editor focus/undo/notes; do not add a competing workspace shell |
| QUILL Lite | Start and resume with minimal ceremony | Open, write/read, find your place and recover a draft without being pushed through setup | Preserve its lightweight purpose; add discoverable depth only where needed |
| Radio | Stable browsing and understandable transport ownership | Favorites remain predictable; live connection/recording state is truthful; audio routes can be identified | Respect the accepted favorites-first surface and existing transport model |
| Cast | A queue that respects listening context | Resume the episode at its real position, know what is offline and inspect arrivals without losing the current item | Preserve user order/default actions; do not build an engagement feed |
| Player | Read/listen through meaningful structure | Reach a chapter/marker, compare a short segment and return to playback without hunting | Verify supported media/structure and product release status |
| Studio | A recording someone can verify independently | Rehearse exact sources, listen back, fix a route and start the long recording with evidence | Follow existing capture/preview/routing scope; do not equate a session mixer with a complete production engine |
| Converter | Results prepared for a chosen use | Choose a practical destination/profile, understand format changes, audition a sample and open finished outputs | Explain the preset's actual transformations; preserve originals; avoid a huge device-preset catalogue |
| Transcribe | Reliable target and source-linked corrections | Know where dictation will go; keep words if focus moves; jump from uncertain text to the relevant audio | Honor language/model availability and real timing evidence |
| Inkwell | Expansion that helps without surprising | Know when expansion is active, insert literally when intended and recover an unwanted expansion | Preserve privacy and target-app boundaries; avoid passive typing surveillance |
| Weather | Trustworthy current state and predictable alerts | Hear when information was issued, distinguish an update failure and rehearse the configured alert experience | Retain official warnings and user alert policy; no invented safety assurances |
| Beacon | Save a meaningful place and return reliably | Capture source plus selected location, reopen the right app, and understand when only a fallback was found | Reuse existing Universal Location Descriptor logic; no duplicate bookmark system |
| Social | Read at the user's pace and publish deliberately | New posts wait to be revealed; a draft's account/audience/attachments stay clear; partial publication is recoverable | Network capabilities differ; source/mock behavior is not proof of live acceptance |

### 6. Three family journeys worth making exceptional

#### Journey A: “I heard something worth keeping”

1. Hear a useful episode or recording passage.
2. Save the exact location and an optional short note using the existing capture path.
3. Open it later from Beacon.
4. Continue in the appropriate media app at the verified place.
5. Open a related transcript or document without losing the origin.

**Delight:** one thought survives the movement between apps.

**Prove it:** interrupted playback, missing local media, changed source, offline use and a failed exact-location match are all understandable.

#### Journey B: “I need to record something and trust the result”

1. Choose the recording sources already exposed by Studio.
2. Make a short rehearsal and inspect/listen to the captured result.
3. Start recording; see/hear honest progress without unnecessary interruption.
4. Finish with the file location and playable result.
5. If desired, hand the relevant file/range to Transcribe, then open the transcript in QUILL.
6. Convert or export a suitable deliverable with its provenance and limitations retained.

**Delight:** people can produce and verify their own work without relying on someone sighted.

**Prove it:** device loss, low disk space, partial export, absent destination app and interruption each preserve the usable artifacts.

#### Journey C: “I have twenty minutes and want to continue”

1. Open the app and reach the last meaningful place with ordinary startup behavior.
2. New background results are available without displacing the current task.
3. Get a short situation explanation only when needed.
4. Do a useful piece of work.
5. Leave knowing whether the draft, position, recording or result was saved.

**Delight:** continuity feels natural; resuming does not become a setup task.

**Prove it:** changed files, unavailable accounts, multiple windows and large result sets do not break context or invent completion.

### 7. Where AI could earn its place

The AI connection and larger mission design remain in [complete.md](./complete.md). These family improvements should remain useful without AI.

| Appropriate addition | What must stay deterministic |
| --- | --- |
| Suggest chapter names or a brief recap of a user-selected passage | Source position, actual saved location and playback state |
| Explain a conversion choice in terms of the intended use | Actual codec/settings, output validation and file identity |
| Suggest a clearer paragraph while comparing it with the original | Which version was approved and exactly what is applied |
| Help turn a recording into an edited transcript and publication draft | Source boundaries, timestamps where verified, consent and publication actions |
| Explain a real error and suggest the next supported step | Preserved work, recorded error facts, actual retry/result |
| Adapt a tutorial explanation to the selected task | Commands available, permissions, keyboard paths and the user's progress |

- [ ] Keep the existing Ask/Choose Your AI/task infrastructure.
- [ ] Use the user's deliberately selected connection and supported capabilities.
- [ ] Clearly mark generated structure and uncertainty.
- [ ] Require no AI call for knowing the current window, target, file, task status or audio route.
- [ ] Keep private drafts/media out of model context unless needed and authorized.
- [ ] Do not expand this UX plan into another generic chat product.

### 8. Interaction contracts to apply across every pilot

#### Keyboard, focus and speech

- Stable tab order, visible focus and accessible names/descriptions.
- Type-ahead and text editing keep their established meaning.
- Restore focus to the originating control after dialogs.
- Background updates do not steal focus or interrupt reading.
- Speak only outcomes the screen reader does not already communicate; retain discoverable full detail.
- Respect the established sound/speech/both/silent behavior and error policies.
- Every essential state is available as text and through braille; sound and color are supplementary.
- Choose new keys only after checking existing family/app bindings, aliases and assistive-tool conflicts.
- Treat keyboard-only, screen-reader, braille, magnification and high-contrast use as normal task paths.
- Keep web/help/exported HTML at WCAG 2.2 AA; native behavior also needs platform/manual validation.

#### Identity, changes and confidence

- Name the relevant object, account/destination and actual result.
- Distinguish local draft, prepared change, processing, saved output and remotely published state.
- Use confirmations at meaningful consequence boundaries; routine safe actions should not be slowed by warnings.
- Show unavailable actions with useful explanations according to each app's existing surface rules.
- Respect stored user choices and current release gates.
- Preserve originals/drafts and state recovery limits honestly.
- Keep local defaults local unless the user chooses the narrow supported sharing path.

#### Performance and durability

- Immediate control response; long work is cancellable and visibly/textually active.
- Bound large lists, histories and caches without silently losing meaningful work.
- Separate media/documents from caches and configuration.
- Version and preserve shared data, including unknown fields used by a newer sibling app.
- No new telemetry service is needed to observe usability improvements.
- Do not infer behavior in real receiving applications or frozen builds from unit tests alone.

### 9. What I would deliberately leave out

These are design recommendations to keep the scope useful.

- A required family dashboard, new home app or launcher before someone can use an installed product.
- A second universal notification/history/task centre overlapping existing notices, recent problems and activity.
- Automatically rearranged menus, renamed familiar controls or continually changing default actions.
- A new panel/button for every useful command; prefer existing menus, context actions, status and help.
- Mandatory account creation or cloud synchronization to listen, read, write, convert or use local tools.
- A “smart” default that silently changes audio destinations, publication accounts, dictation targets or billing.
- Large settings migrations in the name of consistency; share only behavior that truly means the same thing.
- Streaks, badges, engagement reminders or dashboards that reward time spent.
- An AI approval ceremony for ordinary reads and harmless local actions.
- Animations, decorative sound or welcome messages that slow real work or compete with a screen reader.
- A claim that all companions are shipped because their source exists.
- Replacement of an app's useful personality with one compulsory layout.

### 10. Delivery order

| Stage | Scope | Exit |
| --- | --- | --- |
| A: observe | Watch a small set of real tasks in the current packaged builds; audit existing features | Evidence of friction and a baseline; avoid implementing an already solved behavior again |
| B: prove the basics | FUX-04 results and FUX-06 stable lists in two appropriate apps | Clearer completion, fewer lost selections and no added modal steps |
| C: continuity and input | FUX-01 resume and FUX-07 intended target | Useful work retained through interruptions and real receiving-app scenarios |
| D: verify media | FUX-03 audio clarity plus FUX-11 rehearsal and FUX-12 comparison | Independently verifiable recording/listening tasks |
| E: connect the family | FUX-02 handoff and FUX-14 structure | Two real cross-app journeys with correct return/context and missing-app recovery |
| F: simplify the rest | Settings, first-task guidance, contextual help, freshness and maintenance | Remove redundant controls/prompts; preserve learned behavior |

Roll out in the shared layer when semantics match. Keep app-specific behavior where it matters. Social and independently packaged/migrating apps may need adapters rather than assumptions about a common shell.

#### For each pilot

- [ ] Identify the existing implementation/accepted requirement and the precise remaining gap.
- [ ] Record one realistic before/after task.
- [ ] Define the proposed control/command and what gets simpler.
- [ ] Name supported app/build/platform boundaries.
- [ ] Specify failure, cancellation, restart and multi-window behavior.
- [ ] Observe keyboard/screen-reader users and at least one relevant braille/scaling path.
- [ ] Run meaningful checks for any implementation changes; document actual manual results.
- [ ] Update help/examples and remove stale directions.
- [ ] Confirm that the improvement does not add a mandatory step to the everyday path.
- [ ] Accept, revise or drop the proposal on evidence.

### 11. How we will know it helped

Use local pilot notes and consenting participants; this plan does not require passive usage tracking.

| Measure | What to observe |
| --- | --- |
| Completion | Can the person finish the task independently? |
| Resume effort | Time/actions needed to regain the original passage, item or task |
| Focus stability | Unexpected selection moves, lost place and focus recovery |
| Trust | Can the person accurately say where text, audio and files are going? |
| Recovery | Does failure preserve work and lead to a successful next action? |
| Discoverability | Can a new user find the useful action without memorizing the manual? |
| Speech/braille burden | Duplicate speech, interruptions, excessive row length and missing state |
| Effort | Dialogs, keypresses, decisions and avoidable context switches |
| Practical benefit | Does the improvement solve a recurring problem rather than merely impress in a demo? |

Set numerical acceptance targets after measuring the current behavior. Test first-time and experienced users separately: a useful explanation for the first session can become noise in the hundredth.

### 12. Decisions for Jeff

These are prioritization decisions for later; they do not block producing this document.

1. Choose two packaged-app pilots and the real users/tasks to observe.
2. Confirm whether to start with truthful results/stable lists or a more urgent observed lost-work/input issue.
3. Choose one cross-app journey to make exceptional before adding more handoff types.
4. Confirm the shared behavior boundaries, especially audio ownership, preferences and target-app text insertion.
5. Promote only the accepted proposals into the relevant product PRDs and release backlogs.

**My recommendation:** start by making the family dependable at the transitions—between tasks, between apps, between devices, and between a command and its result. That is where a small change can make the whole family feel more thoughtful.


## Part 8. WordPress UX review notes

Below are the review notes from the end of `how.md` (2026-11-14), as they were. The walkthrough above them stays in `how.md`.

### Review notes, all in one place

The first part ranks the concerns that matter most, merged across every section. The second part lists every review note in the document, section by section, so nothing is lost. None of this was tried live; each line comes from reading code.

#### Most important first

##### Safety: things that can change or lose data unexpectedly

1. Workbench Access, Safe Mode and View As Role can be bypassed. The access check (refusal_for) only looks at commands in the selected row's own context menu, so menu-bar and node commands run unchecked under Read Only: Empty Spam, Empty Comment Trash, New Here, Import Posts, Import a Folder, Import WXR, Put Back from a Snapshot, Install on Sites Missing It, Promote to Network, and REST Console writes. Delete and Shift+Delete on a user row (Remove) and on an Application Passwords row (Revoke) also skip the check.
2. Shift+Delete on an Application Passwords row goes through generic Delete Permanently and skips the guard that stops you revoking the password the Workbench itself signs in with.
3. Ctrl+Z is unreliable in two opposite ways. A change recorded with no undo stays on top of Change History, so Ctrl+Z repeats "{summary} cannot be undone." and every older undo becomes unreachable (Delete Permanently, Approve and Schedule, Send Back, Copy to Site, imports, batches, Resend Notifications, Revoke Everywhere). And many writes are not recorded at all (Reply, Merge Into, Convert, Allow This Sender, the Empty commands, New Here, products, orders, coupons, events, redirects, membership changes, form status and settings, Find a Plugin install), so Ctrl+Z right after them silently undoes an older, unrelated change, perhaps on another site.
4. Preview windows default to the action button while message boxes default to Cancel, so Enter proceeds through previews, even at the Destructive tier (Empty Trash's "Delete Permanently", Merge Into).
5. The plugin Properties sheet's Status field can deactivate any plugin with no confirmation, skipping both the Application Passwords lockout guard and the "QUILL relies on" warning that Activate or Deactivate gives.
6. Put Back from a Snapshot restores only title, content and excerpt (name and description for terms); status, slug, terms, featured image and parent are not set back, deleted items return as bare drafts, and a snapshot silently leaves out custom post types, templates, global styles, Navigation menus and form data.
7. Sign Out This Site is irreversible but preselects "Remove {site} from QUILL" with OK as the default, so Enter twice signs out and forgets the site.
8. Send Back with a Note on a published post unpublishes it with no preview and no undo; Approve and Schedule reschedules published posts without the warning Move to Another Day gives.
9. Gravity Spam and Not Spam send the entry as it was when the list loaded, overwriting answers changed since.
10. Replace File asks about deleting the old file after the preview, and after "Delete the old file", Ctrl+Z points every page back at the deleted file.
11. Properties on posts drops plain category and tag names (only "News (12)" or an id works) while the confirmation says they were added.

##### Keys that do not work, or teach the wrong thing

12. Ctrl+Shift+F (Filter Builder) and Ctrl+Alt+Shift+F (Forget a Saved Request) only move to the filter box, and Ctrl+Alt+R (Roles) reloads the list, because the shared frame's key hook (workbench_frame_commands.py) runs before the menu.
13. In QUILL's Insert menu all seven WordPress rows reuse access letters other Insert rows already hold, and three of four View rows do too, so none can be chosen by its letter.
14. Tools > WordPress, Tools > Forms and Edit > WordPress have no access letter in either editor; QUILL Lite menu labels also give no Alt route.
15. Menu letters and layer letters disagree for several rows (Check Before Publishing P against K; Media Library B against M; about eight across Tools and Forms).
16. Four Gravity rows in the Workbench Item menu have no access letter; context-menu rows and "More" have none at all, and context menus show no chords.
17. The layer keeps modifiers held from the prefix ("No WordPress command on Ctrl+Alt+Shift+O."), and its four-second timeout is silent, so a late letter types into the document.
18. Responses shows "(Ctrl+Alt+Shift+Grave, F)" even when WordPress is off and the layer is refused.

##### Dead ends and lost features

19. Fifteen Tools > WordPress rows now always open the Workbench (workbench_door always returns True), making their older windows unreachable; some of those windows did things the Workbench cannot, such as Fonts install and delete, Synced Patterns block editing, and, until Arrange Items arrived on 2026-11-14, rearranging menu items. Docstrings still say "behind its flag".
20. Menu items cannot be seen, renamed, moved or removed inside the Workbench; Arrange Items hands off to the editor's Menus window, which has no previews and no Ctrl+Z.
21. WordPress.com is offered in Connect, then refused with "not available in this build yet".
22. The wp-admin map still says WXR import and export are "Only in wp-admin" though Tools > WXR Files now does both; there is no Tools node in the site tree.
23. Start Here still says the Workbench is "early preview, behind a developer setting" and that the Tools windows still work; both are false.
24. Help and refusal sentences point at commands that moved or never existed ("Menus is in File, WordPress, Running the Site", "choose Trash as the status in Open", "then reconnect").

##### What is heard, and what is not

25. The reason a row is greyed is never heard: menu help goes to a status pane that does not exist, context menus give no reason, and every greyed row says "Not available here." Shift+F1 opens a generic list instead of the provider's real "your role and what each action needs" view.
26. Long operations announce their start but not their end (Load More, Load All, Refresh, filters), and an empty list says nothing.
27. Watches are fire-and-forget: nothing is kept, one refused read silences every Watch on that site, and a round can produce a burst of separate announcements.
28. Names by ear: widget areas, menus and sheets are spoken by id ("Add a Widget to sidebar-1", "12 Properties"); Gravity entries have no number; settings and Gravity values are raw stored values ("left_label (was top_label)", 0 to 6); list values print as Python tuples ("('News',)"); grammar slips such as "1 items" and "a event".
29. Confusing names: "Publish or Update" never updates; "Publish a Document as a Page" and "Publish to Another Site" make drafts; "Site Check" opens Site Health; two different "Coming Up" lists; toggles ("Activate or Deactivate", "Offer to Ask the Site", "Add New Pages Automatically") do not say which way they will go.

##### Structure and consistency

30. The site tree gives every site every plugin's branch whether installed or not (over 100 nodes per site), each selection reads the network, and discovery rebuilds the tree and collapses what you expanded.
31. The Item menu leaves out rows the context menu has (Earlier Versions, Duplicate, Change Role, Remove, Set New Password, Replace File, Edit Picture), breaking the engine's promise that More never hides anything only a right-click can reach.
32. The Properties sheet closes on OK before the save finishes, so a failure or a conflict Cancel loses the edits.
33. Consent is uneven: In Short and Ask the Site send text to an AI without asking while Visual Review asks; Make a Listening Version and Publish a Document as a Page upload without a first confirmation.
34. Shop, event and membership rows mostly name no capability, so they are never greyed and an Editor answers several dialogs before WooCommerce or PMPro refuses; choosers in those dialogs do not start on the current value.
35. QUILL Lite ignores the Form Payments switch, so payment commands run in Lite where QUILL would refuse: Lite ahead of QUILL, which the family rules forbid.
36. Escape outside the filter box goes Back to another node from any pane, so pressing Escape to leave Details jumps the tree.
37. Dozens of editor WordPress commands have no key and no written reason; the rule 8 gate cannot see them because they are not in DEFAULT_KEYMAP.

#### Every review note, by section

Each line names the feature it sits under, then the note.

##### Getting connected

- The WordPress feature switch: The catalogue description promises WordPress.com, but WordPress.com sign-in is not available in this build (see Connect a Site). The description is the first thing a person reads when deciding to turn the feature on.
- The WordPress feature switch: The description says "from File > WordPress", but since the 2026-11 placement most commands live in Insert, Format, View, Edit and Tools. A person told to look in File will not find Media Library, Comments or Check Before Publishing there.
- Connect a Site: When the dialog comes back after a failure, the password field is always empty: ConnectSiteDialog never fills it from the previous answer. Any failure (a typo in the address, a slow host, a 500) means retyping or re-fetching the application password. On the browser route this is worse: the fetched password is thrown away and a new one must be minted, leaving an orphan password on the site each time.
- Connect a Site: Tier 2 reads the clipboard the instant the browser opens, before WordPress has even shown the password, so the "offer" is whatever was on the clipboard before. The module docstring says it offers the value "when focus comes back"; the code does not.
- Connect a Site: Tier 2 asks for a username when it is empty and, if cancelled, reopens Connect with an empty password field, so the pasted password is lost.
- Connect a Site: The Problem field's "&Problem:" and the password field's "Application &password:" both claim P whenever the error is shown, so Alt+P cycles between them instead of pressing (a GATE-14 duplicate that only exists on the retry, which is when a person is most likely to need it).
- Connect a Site: WordPress.com is offered as a choice, its help says "you will sign in with your browser", and the browser button's help says "For WordPress.com this is how you sign in"; the result is a dead end sentence after the dialog has already closed. Either hide the choice or keep the dialog open with the explanation in the Problem field.
- Connect a Site: "Approve QUILL in your browser..." is spoken at the moment the browser takes focus, so the screen reader is likely to talk over it. There is no way to cancel the 300-second wait from QUILL, and a listener failure is swallowed silently (the failure callback only cancels the listener).
- Connect a Site: The browser's done page says "You're signed in" before QUILL has verified anything; if verification then fails, the browser and QUILL disagree.
- Connect a Site: A failure on the browser route speaks a sentence and drops you back in the editor, while the same failure on the manual route reopens the dialog with a Problem field. Two behaviours for one dialog.
- Connect a Site: A malformed or state-mismatched reply from WordPress raises inside the success callback; no code here turns that into a spoken sentence (not found in code).
- Connect a Site: Connect and Get Password both beep with no words when the address is empty. A beep is not an explanation; a sentence in the Problem field, or speaking "Type the site's address first", would be.
- Connect a Site: "then reconnect" in the 401 sentence names an action with no command of that name; the way to replace a password is to run Connect a Site again with the same address and username, which nothing tells you.
- Sites: Add... is backwards. If you cancel the Connect dialog, the whole Sites window closes (the action returns CLOSE when the flow returns None). If you complete it, the list refreshes immediately, before the background verification has saved the new site, so the site you just added is not in the list until you close and reopen the window.
- Sites: Verify, Which Password and Remove all go through the site client, which on first use in a session also counts waiting comments and may speak "<site>: N comments waiting." in the middle of a sign-in check (the same is true of Sign Out). Unrelated news arriving with a diagnostic.
- Sites: Remove forgets the password locally but leaves it live on the site; Sign Out This Site (which does revoke it) lives in a different menu (Tools > WordPress > Manage). A person managing sites in this window will not find the safer action here.
- Sites: There is no way to change the address, username or password of an existing site from this window. "Verify" can only tell you it is broken.
- Sites: Sites and Switch Site both change the default site (Make Default, and Switch Site), with different sentences: "<name> is now your default site." versus "Default site: <name>."
- Switch Site: "Switch Site" suggests the document in front moves to another site; it only changes where New and Open start. The help text ("Choose which of your WordPress sites to use") does not say so either.
- Switch Site: It has the everyday key S while the Sites list has Shift+S, yet Switch Site is a subset of the Sites window's Make Default.
- Switch Site: After "Connect a WordPress site first." the Connect dialog opens at once, so the sentence is very likely talked over by the dialog title. After connecting, the original command does not resume. This is true of every command that calls need_site.
- Sign Out This Site: The confirmation is a two-row list with a generic "OK" button. The action is not reversible on the site, so the button should say "Sign Out", as Remove Site's says "Remove".
- Sign Out This Site: "Keep <name> in the list, to connect again later" leaves a site in the list with no password; every later command on it will fail with the 401 sentence. Nothing marks such a site in the Sites list.
- Sign Out This Site: It lives four levels deep under Tools while Connect a Site, Sites and Switch Site are in File > WordPress.
- When no site is connected: Which of the two "not a WordPress document" sentences you hear depends on whether the handler happened to pass its name; Save Draft, Publish, Properties, Open on Site, Copy Address, Trash, Compare, every block command and Image Size use the generic one.
- When no site is connected: "Connect it again with Connect a Site, and the document will find it" is only true when you reconnect with the same address and username and the old id survives; a removed site's id is gone, so the document's site id will not match a fresh connection (sites.py upsert matches by id, and a new connection after Remove gets a new id). Not verified at runtime, but nothing in the connect code looks up an orphaned document's site id.

##### The editor's WordPress commands

- The WordPress keys (the layer): Any modifier still held when the letter is pressed makes a different key. Holding Ctrl+Alt+Shift through from the prefix and pressing O says "No WordPress command on Ctrl+Alt+Shift+O." Holding Shift only turns O into "Shift+O" and S into Sites instead of Switch Site. Since the prefix itself needs Shift, this will happen often; the layer could ignore modifiers held over from the prefix, or the "No WordPress command" sentence could say "release the keys first".
- The WordPress keys (the layer): The timeout is silent. Press the prefix, think for five seconds, press P, and a "p" lands in the document with nothing said. "Left WordPress keys" on timeout, as on Escape, would cost one sentence.
- The WordPress keys (the layer): The menus spell the chord as "(Ctrl+Alt+Shift+Grave, O)" on every row, read aloud in full on every visit to File > WordPress. The QUILL key is displayed as "QUILL Key + S"; the WordPress layer gets no friendly name ("WordPress Key + O" would be shorter and match the spoken "WordPress keys").
- The WordPress keys (the layer): Only 24 of the about 45 editor-side commands have a letter. The per-page navigation commands (Next Block, Previous Block, Where Am I), the most frequent things a writer does in a block document, have none, and nothing records a reason (see "Keyless" below).
- The WordPress keys (the layer): A command failure from the layer goes through _run_command, which reports exceptions with _set_status (status bar), not speech (not verified that the status bar is spoken).
- File > WordPress (the submenu itself): The submenu has 22 rows and four separators plus a submenu; with each label carrying "(Ctrl+Alt+Shift+Grave, X)", arrowing through it is long.
- File > WordPress (the submenu itself): Several access letters are not the word's first letter and do not match the layer key (New Page is P in the menu and G on the layer; Publish is U in the menu and P on the layer; This Post in the Workbench is K in the menu and Shift+H on the layer; Compare is M in the menu and C on the layer; Sites is S in the menu and Shift+S on the layer, while S on the layer is Switch Site whose menu letter is H). The menu.py comment says "A row's own access letter wherever it is free, so the menu teaches the key", but for these rows the menu teaches a different key from the layer.
- New Page: The "Write in" radio box has no access letter, and its label is not "&Write in"; every other field in the dialog has one.
- New Page: The site is chosen inside the dialog, but for posts categories and tags are loaded from the default site before the dialog opens; choosing another site silently drops any categories and tags checked (the code sets them only when the chosen site is the default). Not an issue for pages, but the same dialog is used.
- New Post: Categories and tags are lost without a word if you change the Site choice away from the default (see New Page).
- New Post: Starting a post needs the network; starting a page does not. A writer offline cannot start a post at all, and the sentence they hear is a connection error, not "QUILL needs the site to list categories".
- New Post: A site with hundreds of tags puts hundreds of check boxes in a scrolled group with no filter.
- Open Page or Post: Four to five dialogs to open one post (site, kind, list, autosave, format). The format question comes every time and always starts on HTML; New remembers the last format, Open does not.
- Open Page or Post: The status filter only matches the raw status: rows say "Published" but typing "published" finds nothing; you must type "publish". "Pending review" rows need "pending", "Scheduled" needs "future".
- Open Page or Post: Trash and Restore from this window do not refresh the list; the row still says its old status until you close and reopen.
- Open Page or Post: Opening an item you already have a working copy of opens the local copy without checking the site, so you may edit a stale copy; the sentence tells you to run Compare yourself.
- Open Page or Post: Trashed items are mixed in with live ones in the default list.
- Open Page or Post: "<site> has no <kind>s yet." builds the plural by adding "s" to the type slug, so a custom type such as "tribe_events" is read as "tribe_eventss".
- Open Page or Post: "Opened <title> from <site>." follows a document opening, whose new window title the reader announces anyway; the site name is the only new information.
- Open by Web Address: Using the clipboard without asking is a trap: any web address copied for another reason is used silently, and if it is not on a connected site you are dropped into the Connect dialog for a stranger's site. At minimum the dialog should open with the clipboard address filled in, so the person can see and change it.
- Open by Web Address: Nothing is spoken when the clipboard is used, so the person does not know which address QUILL took.
- Open Local Draft: Silent on success, while Open Page or Post says "Opened <title> from <site>." Inconsistent, though the silent one is the GATE-13-friendlier of the two.
- Open Local Draft: "Drafts" here means every working copy, including copies of published posts; the name suggests only unsent drafts.
- Open Local Draft: No filter on a list that will grow to every item ever opened.
- Save Draft to Site: Choosing "Update the published <kind>" from Save Draft updates the live page with no further confirmation, while Publish or Update asks "Update '<title>' on <site>?". Save Draft is the command people press when they think it is safe.
- Save Draft to Site: The conflict sentence is announced immediately before the conflict dialog opens, so the dialog title is likely to cut it off; the dialog's own prompt does not repeat what happened.
- Save Draft to Site: "Open the site's copy" discards your working copy (it is kept in Previous Versions) without a confirmation.
- Save Draft to Site: The "lines could not be turned into blocks" sentence is spoken and then the send carries on; for Publish it is spoken just before the confirmation dialog, where it will be lost.
- Publish or Update: For a contributor the confirmation says "Publish" and the button says "Publish", but the item is submitted for review (target_status turns publish into pending). The question should say "Submit '<title>' for review on <site>?" when the account cannot publish.
- Publish or Update: Putting the address on the clipboard silently overwrites what the person had copied. Either ask, or say "The address replaced what was on the clipboard."
- Publish or Update: Two sentences in the Add to a Menu flow send people to "File, WordPress, Running the Site", a place that no longer exists; Menus is now Tools > WordPress > Menus.
- Publish or Update: With Cancel as the default, Enter in the confirmation cancels. Safe, but the labels passed to SetYesNoLabels ("Publish", "Update", "Publish Anyway") carry no "&", so the publish button has no access key; the route is Tab to it, then Space. Worth checking with a reader.
- Schedule Publish: The role check happens only at the very end, after the person has typed a date and confirmed twice; a contributor should hear the refusal before the dialog opens (the account is already read for the time zone call's site).
- Schedule Publish: Two confirmations in a row: the dialog's own "Schedule" button, then a "Schedule" message box. The second adds the spoken moment, which is useful, but it could be the dialog's purpose text instead.
- Schedule Publish: The date is a typed field with a format in its label; there is no date picker (deliberate for screen readers, but the label "(year-month-day)" is long to hear on every Tab).
- Open on Site: For a draft, the browser opens an address that needs a WordPress sign-in; Copy Address warns about this ("It needs a WordPress sign-in to open."), Open on Site does not.
- Copy Address: none beyond the generic "not a WordPress document" sentence.
- This Post in the Workbench: When the site is not among the Workbench's sites, the Workbench window has already been opened before the sentence is spoken, so the person lands in a window that does not show what they asked for.
- This Post in the Workbench: Menu letter K, layer key Shift+H: two different things to learn for one command.
- Properties: The outcome sentence always counts categories and tags, so a page says "Kept with your copy: 0 categories, 0 tags." Pages have neither. It also speaks when nothing changed but Apply was pressed.
- Properties: The facts a person most often wants (status, address) are on the last page of the notebook, not the first.
- Properties: A second dialog (Custom Fields) can open straight after OK with no warning; a listener may think Properties reopened.
- Properties: Opening Properties on a post needs the network (categories and tags); offline it fails with a connection sentence and the sheet does not open.
- Custom Fields: A non-number in a number field closes the dialog and discards every other field typed ("Nothing was kept; try again."). It should reopen with the values kept and the problem named.
- Plugin Fields: Custom Fields and Properties keep changes until the next send; Plugin Fields, one row below, sends immediately. Same menu, same kind of data, opposite rule; the OK label "Save to Site" is the only hint.
- Plugin Fields: Event dates and venue are always re-sent and always reported as saved, even when unchanged.
- Plugin Fields: A bad date closes the dialog and loses everything typed.
- Previous Versions: Restore replaces the text but not the title; a version with a different title restores only its body.
- Previous Versions: There is no "compare this version with mine"; the only way to see differences is to read both.
- Previous Versions: The View report is titled just "Version", which says nothing about which one.
- Compare with Site: The comparison is of your text converted to HTML against the site's HTML, so a Markdown document shows block markup lines as differences the writer never typed.
- Compare with Site: "Same" is shown in a report window rather than simply spoken; a one-line answer does not need a dialog.
- Compare with Site: No action from the report (take the site's line, keep mine); it is read-only.
- Move to Trash: "choose Trash as the status in Open" describes a control that does not exist; Open has a find field where you type "trash", and a "Restore from Trash" button.
- Move to Trash: The document stays open in the editor afterwards with its local status set to trash; nothing says what Save Draft or Publish will do next with it.
- Send This Document to WordPress: Two sentences for one action, the first while a new document window opens (likely talked over).
- Send This Document to WordPress: The title is taken from the first heading without showing it; a person cannot correct it before it lands on the site.
- Publish to Another Site: The command is named "Publish" but always creates a draft. "Copy to Another Site" would say what it does.
- Publish to Another Site: With two sites there is no confirmation before content is created on the other site.
- Publish to Another Site: In the Categories and Tags message, "Cancel" does not cancel: it carries on and copies without them. A Cancel button that continues the action breaks a universal expectation; the buttons should be "Create Them" and "Copy Without Them", with a real Cancel.
- Duplicate: In a WordPress document, Duplicate copies the site's copy, not your unsent edits; Publish to Another Site copies your local text. Neighbouring rows, different sources, no word about it.
- Duplicate: With one site, Duplicate in a document creates a draft on the site with no confirmation at all.
- Duplicate: The item list is a plain choice with no filter.
- Send a Folder as Drafts: Every file becomes a post; there is no Post or Page choice, unlike Send This Document.
- Send a Folder as Drafts: Only the first failure is named.
- Download My Writing: "Saving ... QUILL says when it is done." is spoken before the permission check; a refused account then hears a second sentence contradicting the first.
- Download My Writing: The final sentence always ends with a long "Left out:" list, every time, even on a resume that saved nothing new.
- Insert menu rows (overview): Every one of the seven WordPress access letters collides with an existing Insert row in QUILL: "WordPress &Block..." (B) with "Insert Code &Block"; "Pict&ure from the Media Library..." (U) with "Q&uick Insert..."; "Picture from This &Computer..." (C) with "Insert &Citation..."; "Li&nk to a Page on This Site..." (N) with "I&nsert HTML Tag..."; "N&ote on This Block..." (O) with "Insert Em&oji..."; "Make a Pictu&re..." (R) with "Insert Horizontal &Rule"; "WordPress &Icon..." (I) with "L&ist". In a Windows menu a repeated letter cycles the highlight instead of choosing, so none of these rows can be chosen by its letter. menu.py chose these letters for QUILL Lite's menus; nothing checks them against QUILL's.
- WordPress Block: Menu says "WordPress Block", the window says "Insert Block", and the no-blocks sentence elsewhere says "Insert one with Insert Block". Three names for one command.
- WordPress Block: Enter on a row does nothing (no on_enter); you must Tab to Insert. Every other picker in this family (Open, Notes, Fix Link Text) honours Enter.
- WordPress Block: It needs the network even for QUILL's own core blocks; offline, nothing can be inserted.
- Picture from the Media Library: Inserting a picture now opens a whole second window (the Workbench) rather than a dialog; for a screen-reader user that is a heavy context switch for a common task, and you must find your way back.
- Picture from the Media Library: "Use Upload Files" points at a command in Tools > WordPress > More Media without saying where.
- Picture from This Computer: Undoing the insert leaves the picture queued for upload (the pending upload is kept in the working copy and uploaded on the next send if the file exists; _upload_pending replaces the address only if it is in the text but uploads either way).
- Link to a Page on This Site: No filter on what can be hundreds of rows; first-letter navigation in a list box is the only help.
- Link to a Page on This Site: Drafts and scheduled pages cannot be linked to, with no word about why they are missing.
- Note on This Block: The note is sent to the site immediately, while the tie to the block waits for the next send; Undo in the editor takes back the tie but leaves an orphan note on the site.
- Note on This Block: The "protected line" warning is a heavy consequence (the block's words become uneditable in Markdown) for adding a comment; worth surfacing in the menu row or offering to switch to HTML.
- Make a Picture: It is not document-only, so a person can spend AI time making a picture in an ordinary document and only learn at Insert that "This is not a WordPress document...".
- Make a Picture: A made picture uploads the moment you insert it; a picture from this computer waits for the next send. Same menu, two rules.
- WordPress Icon: the refusal names it "Insert Icon"; the menu row says "WordPress Icon".
- Block Settings: needs the network just to read colours; offline, no settings can be changed at all.
- Image Size: replace_text rewrites the whole document; the caret is then put back at the picture with go_to_offset, which is good.
- Mark Language: With nothing selected the whole page is wrapped with no confirmation; forgetting to select is the likely mistake, and the result changes the language of everything. A confirm, or "Nothing is selected: mark the whole page?", would catch it.
- View menu rows: Three of the four access letters collide in QUILL's View menu: "WordPress &Blocks..." (B) with "&Browser Preview..."; "Pre&view Blocks" (V) with "Pre&view Side by Side"; "B&lock Notes..." (L) with "Announce &Lists". Only Play Media Here's M is free (from the rows found in main_frame_menu.py).
- WordPress Blocks: After Move Up or Move Down the list keeps the same row number selected, so the selection stays put while the block moves; pressing Move Up twice swaps the pair back. The Rows type in wordpress_dialogs.py exists for exactly this ("a row moved down follows the row") and is not used here.
- WordPress Blocks: No Enter action; Enter on a row does nothing (Go To is a button).
- WordPress Blocks: Menu "WordPress Blocks", window title "Blocks", and the no-blocks sentence names "Insert Block", which the Insert menu calls "WordPress Block".
- Preview Blocks: the failure count is spoken only after you close the report, when it is no longer useful; it belongs at the top of the report.
- Block Notes: the list is updated optimistically before the site answers; if the reply fails, the list still shows it.
- Play Media Here: "Insert from Media Library" is not the menu's name ("Picture from the Media Library...", which also inserts audio and video despite saying "Picture").
- Edit > WordPress (submenu): The one submenu a writer would visit most while working in a page has no letter (the Edit menu's W is "&Word Prediction..."), and none of its rows has a chord, so moving block by block means Alt+E, arrows, Enter, N for every block. This is the strongest case in the section for a key.
- Edit > WordPress (submenu): The Command Palette now has two commands titled "Next Block" (navigate.next_block and wordpress.next_block) and two titled "Where Am I" (verbosity.where_am_i and wordpress.where_am_i), with no way to tell them apart by name.
- Hear Where a Link Goes: The target sentence is spoken and then repeated as the first line of the confirm that opens at once, so it is said twice, and the spoken copy is the one likely to be cut off.
- Hear Where a Link Goes: A "hear" command that turns into an "insert a link" command when there is no link at the caret is a surprise; the two would be clearer as separate rows.
- Fix Link Text: Each fix rewrites the whole document with replace_text and never puts the caret back, so after closing the window the caret is at the end of the document, far from where you were.
- Fix Link Text: Use All is several Undo steps, not one, unlike every Blocks window change.
- Fix Link Text: There is no way to type your own words for a link from this window; the only choices are the page title or nothing.

##### The editor's WordPress commands

- Open WordPress Workbench...: It is the only row in the submenu with no access letter. Opening it from the menu means arrowing to the top of the submenu or knowing the H layer key.
- Open WordPress Workbench...: The trailing "..." suggests a dialog, but it opens a full peer window.
- Check Before Publishing...: The summary is announced just before a modal opens, so the dialog title announcement may cut it off. The purpose text that repeats it is reachable only with F1.
- Check Before Publishing...: When there are no findings, nothing opens and only the summary is spoken. That is good, but it is the only feedback.
- Check Before Publishing...: Go to It on a conversion-problem row is a guaranteed dead end. Those rows could go to their line number instead.
- Check This Page: The summary is announced right before the modal opens, so it can be cut off.
- Check This Page: A list with zero findings still opens a window with an empty list. Unlike Check Before Publishing, there is no early return when nothing was found.
- Check This Page: The name says "This Page", but from a non-WordPress document it silently checks the site's home page. The chooser does not say so.
- Check the Whole Site...: Access-key collision (GATE-14): the list label "&Problems:" and the "&Pages..." button both claim P in one window, so Alt+P cycles focus instead of pressing. check_access_keys.py cannot see this, because the labels are runtime arguments to the shared ListWindow.
- Check the Whole Site...: Reading every page can take a long time with no progress sentence; only the visitor pass reports progress.
- Check the Whole Site...: Fix in Bulk is two modals in a row, the preview report and then the confirmation. Closing the preview with Escape does not cancel; the confirmation still follows.
- Undo Site Fix...: Only covers Fix in Bulk and Site-wide Find and Replace. Manage > Bulk Edit has its own separate "Undo Bulk Edit", and Style Variations and Site Styles have "Put Back the Previous Look". That is three undo models for site-wide changes.
- Undo Site Fix...: Fixes that were already undone stay in the list. It is not clear from the code whether their spoken rows say so.
- Site-wide Find and Replace...: Grammar: the confirmation always says "matches", so one match reads "Replace 1 matches of ...".
- Site-wide Find and Replace...: It takes three modal steps before any search. A single dialog with Find, Replace with, Match case and Pattern controls would be faster and closer to Word's Replace.
- Site-wide Find and Replace...: Toggling a match does not say the new state, but the row text changes ("Included" or "Skipped" first), which the list re-reads. That is fine.
- Write an Accessibility Statement...: The draft is Markdown or HTML according to the format last chosen in New Page or New Post (self._last_format), not a choice offered here.
- Write an Accessibility Statement...: Leaving the contact empty and pressing OK still makes a statement with an empty contact. No check is made.
- Palette Report: The title has no ellipsis but opens a report. That is inconsistent with the other rows.
- Palette Report: A classic theme silently gives "could not read a colour palette", with no hint that block themes are needed. Design > Style Variations does explain this.
- Palette Report: The same palette data is in Design > Style Variations and in Manage > Previous Looks > Palette Report. That is three doors to one report.
- In Short...: It sends page text to AI with no "this will send N words to {AI}" confirmation. Visual Review asks first; this does not.
- In Short...: The trailing "..." suggests a dialog, but none opens.
- In Short...: It is a content-writing command, not site upkeep. It sits oddly in Tools beside site checks.
- Media Library...: The code comment "the developer flag sends this door to the WordPress Workbench" is stale. There is no flag check.
- Media Library...: Access letter B, but the layer key is M. WordPress key, then B, opens View > WordPress Blocks instead.
- Alt Text Review...: Edit and Mark Decorative speak nothing afterward; only the row text changes. Suggest does announce. That is inconsistent.
- Alt Text Review...: The Alternative Text box is multiline, so Enter adds a new line instead of pressing OK. The user must Tab to OK.
- Alt Text for the Whole Library...: Close saves. That is good for a long session, but Escape (usually "cancel") silently sends pending descriptions to the site.
- Alt Text for the Whole Library...: The save on close announces after the window is gone. That is fine.
- Visual Review...: It should be on DOCUMENT_ONLY (or work on the home page the way Check This Page does). Today it is enabled everywhere and refuses with a sentence that names File > WordPress rather than this command.
- Visual Review...: It is a good model of consent before sending; In Short and Ask the Site should match it.
- More Media > Upload Files...: There is no way to cancel the whole batch from a details dialog. With 20 files, the user must Cancel 20 times.
- More Media > Upload Files...: Enter in the multiline Alt box adds a line instead of pressing Upload.
- More Media > Paste Image: It is an insert-into-this-page command filed under Tools > More Media, while Insert has "Picture from This Computer". Paste Image belongs beside it, or in Edit.
- More Media > Paste Image: It should be on DOCUMENT_ONLY.
- More Media > Paste Image: No "..." even though a dialog opens.
- More Media > Upload a Large File...: It puts the address on the clipboard without being asked, and Upload Files does not. That is inconsistent and overwrites the clipboard.
- More Media > Upload a Large File...: Having both "Upload Files" and "Upload a Large File" makes the user decide what "large" means. The code could choose for them.
- More Media > Make a Smaller Copy...: three modals plus a confirmation for one shrink. A single dialog holding the width and format choices would halve the steps.
- More Media > Edit a Picture on the Site...: one command can chain up to five modals and several announcements. The follow-ups (Use here, Regenerate) could be check boxes in the first confirmation.
- More Media > Site Logo...: Access-key collision (GATE-14): the list label "&Logo and icon:" and the button "From the &Library..." both claim L in one window.
- More Media > Site Logo...: After a replace the list rows are not refreshed (the actions return None), so the window keeps showing the old logo until it is reopened.
- More Media > Site Logo...: The menu title "Site L&ogo" uses O, which is also the submenu's own letter (M&ore). That is harmless but means pressing O twice.
- More Media > Preview and Review...: The refusal sentence is about 60 words, far longer than the one-sentence rule the other commands follow.
- More Media > Preview and Review...: It overlaps with Site Logo > Preview a Width.
- More Media > Captions for Video...: A Cancel after minutes of transcription is silent and loses the work. A "Discard the captions?" confirmation, or keeping a draft, would help.
- More Media > Captions for Video...: It should be on DOCUMENT_ONLY.
- More Media > Make a Listening Version...: the first time, it uploads a file to the site with no confirmation at all; only a remake asks.
- More Media > Name Embeds: It edits the document with no preview or confirmation; the report comes after the fact.
- More Media > Name Embeds: It is a this-page command filed under media upkeep.
- More Media > Publish a Document as a Page...: The name says "Publish", but it uploads the original and opens a draft. The menu name overpromises.
- More Media > Publish a Document as a Page...: In the duplicate prompt, Cancel (and Escape) means "upload a second copy". Cancel starts an action instead of stopping one, which is backwards for a keyboard user.
- More Media > Publish a Document as a Page...: The original file is uploaded to the site with no confirmation.
- Comments...: the legacy comments window under this door is unreachable from the menu, though cmd_comments(status=...) can still be called with another status from elsewhere.
- Menu History...: "1 items back" grammar.
- Menu History...: Menus now opens the Workbench, but Menu History is a separate legacy window beside it, and the Workbench has its own "Earlier Versions". That is two histories reached two ways.
- Menu History...: The classic-menu empty message is about 50 words.
- Site Check: the name "Site Check" sits beside three other "Check" rows but means Site Health. Calling the row "Site Health" would match the node it opens and WordPress's own name.
- Design > Site Styles...: The list rows update to the new value as soon as Yes is pressed, before the save comes back. A failure then leaves the list showing a value the site does not have.
- Design > Site Styles...: It is good that the confirmation says the contrast before anything is saved.
- Plugin Extras > Events Coming Up...: the chooser and window are titled "Coming Up", the same as Your Sites > Coming Up, which is a different list (scheduled posts across sites). By ear the two cannot be told apart.
- Plugin Extras > New Event...: Dates are free text in one fixed format. A wrong guess closes the dialog and loses everything typed. Validation should keep the dialog open.
- Plugin Extras > Shop Orders...: a confirmation before a clipboard copy is unusual, but it is justified by the personal data, and it is clearly worded.
- Manage > Synced Patterns...: the menu says "Synced Patterns", but the node is "Patterns". Whether the Workbench filters it to synced patterns is not in this code.
- Manage > Site Map...: "Site Map" opens a node named "Pages", while Page Order (two rows down) is a separate legacy tree window over the same pages.
- Manage > Template Outline: there is no "..." although a window opens. Indentation by depth is hard to hear in a plain text box; a tree, or "level N" prefixes, would carry the structure.
- Manage > Bulk Edit...: The list rows are not refreshed after Change, so status and author still read the old values.
- Manage > Bulk Edit...: "1 posts" grammar.
- Manage > Bulk Edit...: The Workbench has its own batch editing (Phases 7 to 10), so this window duplicates it.
- Manage > Page Order...: Moves go live on the site with no confirmation and no undo, so a mistaken Alt+I re-parents a page in public menus.
- Manage > Page Order...: Focus returns to the list after a move, but because the rows are rebuilt the selection stays at the old index, not on the page that moved. The row the user hears next may be a different page.
- Manage > Previous Looks...: the window title lacks the site name, unlike its siblings ("Style Variations, {site}").
- Manage > Space Used: no "..." although a report opens. The total is announced and then repeated in the report.
- Manage > AI Abilities...: The menu says "AI Abilities", but the node and the legacy window say "Abilities".
- Manage > AI Abilities...: Ask the Site's refusal tells the user to "Turn them on one by one in Abilities", which now means a Workbench node. This code does not confirm that the Workbench node writes the same per-site choices (ability_choices).
- Manage > Ask the Site...: The question is sent to the AI with no consent step. Only running an ability asks.
- Manage > Ask the Site...: The Question box is multiline, so Enter adds a line and Tab then Enter is needed to ask.
- Manage > Sign Out This Site...: It cannot be undone, and the only step is a two-row chooser whose preselected row is the more destructive one ("Remove"), with OK as the default. Enter twice (menu, then dialog) signs out and removes the site. There is no named confirmation, unlike every other destructive command here.
- Manage > Sign Out This Site...: With one site there is no site chooser, so nothing on screen names the site before the chooser.
- Manage > Sign Out This Site...: It calls self.api(profile) first, so on first use in a session it may announce "{site}: N comments waiting." just before signing out.
- Your Sites > Coming Up...: Bug: Open or Enter on a "Did not answer: ..." row reads items[index] past the end of the list (open_it has no bounds check), which raises an exception instead of speaking.
- Your Sites > Coming Up...: "1 sites did not answer" grammar.
- Your Sites > Coming Up...: When every site fails and nothing is scheduled, no list opens, so the failed sites are named nowhere, unlike What Changed.
- Your Sites > What Changed on My Sites...: The "looked at" mark is set before the user has read the list, so closing it by accident loses the changes.
- Your Sites > What Changed on My Sites...: Enter on a row does nothing (no on_enter), while Enter opens the item in Coming Up. The two sibling windows behave differently.

##### QUILL Lite differences

- Where the rows sit in QUILL Lite: Lite's Tools menu has 30 entries, and the two submenus a WordPress user needs most are the last two, with no letter. That only works if the user knows that Up Arrow wraps to the bottom. No label says so.
- Access letters: what Lite has and QUILL computes: This is the biggest Lite-versus-QUILL gap in this area. In QUILL every keyless Forms and WordPress row says its Alt path aloud. In Lite the same row says nothing, and its parent submenu has no letter to type. The house rule that every enabled item shows a keyboard route is met in QUILL and not in Lite. That is the permitted direction (Lite behind QUILL), but it is a real cost on every visit.
- Access letters: what Lite has and QUILL computes: The layer letters and the menu letters disagree for eight rows. The table comment says "A row's own access letter wherever it is free, so the menu teaches the key", but File > WordPress has New &Page (layer G), P&ublish (layer P), Co&mpare (layer C), Switc&h Site (layer S), &Sites (layer Shift+S) and This Post in the Wor&kbench (layer Shift+H). Tools > WordPress has Check Before &Publishing (layer K) and Media Li&brary (layer M). The menu does not teach the layer key for these. Because the bracketed chord is in the label, you hear both and have to ignore one. This is the same in both editors.
- The WordPress key layer (shared, with three small differences): Responses' label advertises a key that can be dead. If Forms is on and WordPress is off (separate features in QUILL, separate areas in Lite), both editors still show "Responses... (Ctrl+Alt+Shift+Grave, F)". The prefix is refused, though, because the layer belongs to WordPress. A Forms-only user is shown a chord that does nothing and is not told why.
- The WordPress key layer (shared, with three small differences): In Lite, a layer command reached on a document under the Read-Only Guard runs anyway. Every Forms command that rewrites the document (Insert Form Field, Outline moves, Form Rules, Form Properties, Plain Language, Payments Setup) writes through `WriteText` on the control. Whether a read-only native edit control accepts that is not proven here; verify by hand. The menu route behaves the same way, since `_dispatch` also goes through `run_unless_read_only` and finds nothing to refuse.
- The WordPress key layer (shared, with three small differences): The "WordPress keys" announcement is correct under GATE-13, because the prefix changes nothing on screen.
- Document-only dimming: Insert Form Into Page is enabled in every document, but it only works in a WordPress page. It could be dimmed by the WordPress `DOCUMENT_ONLY` test instead of always being enabled, and right now it is the only Tools > Forms row that is enabled in places it cannot work.
- Document-only dimming: A form is recognised only by its file name. An unsaved buffer holding QAF text, or a form saved under another extension, dims every Forms row.
- Command Palette, profiles and feature areas: Lite has no Form Payments gate. `_payment_document` asks the host's editor for `_feature_enabled("core.forms_payments")`. A Lite window has no `_feature_enabled` method, so the check is skipped and Form Payments Setup, Insert Payment Field and Verify Payment Setup always run in Lite whenever Forms is on. In QUILL, with Form Payments off, the same rows stay visible and say "Turn on Form Payments in Features before using this command." This is a divergence, and in the "Lite has it, QUILL may not" direction the house rule forbids.
- Command Palette, profiles and feature areas: In QUILL, those three payment rows stay on the menu and enabled with the feature off. You find out the feature is off only by choosing one.
- Command Palette, profiles and feature areas: Both editors describe Forms as local when it is not. The Lite area description ends "Everything here runs on this computer", and QUILL's feature description says "Runs on this computer". But Publish Form, Insert Form Into Page, Test on Site, Responses, Verify Payment Setup and the three AI rows all reach a site or an AI.
- Command Palette, profiles and feature areas: Lite's Everything profile calls AI help "the one area here that does something outside this computer". WordPress and Forms also reach the network.
- Words that say QUILL inside QUILL Lite: A Lite user hears "QUILL" for the editor they are in. Whether that is acceptable branding, or whether these strings should name the product through the host, is the owner's call.

##### Forms (QAF)

- Forms in the menus, and the one Forms key: With 17 rows in four groups, Tools > Forms is long. The editing commands (Check, Fill In, Properties) are mixed in with payments.
- Forms in the menus, and the one Forms key: Payments has three rows here, and a fourth door through the payment kind in Insert Form Field.
- New Form: The announcement uses "a" before every template name: "a event registration with 4 questions" and "a accessibility feedback with ...". It is also odd for "a blank with 1 question".
- New Form: The dialog's purpose is reachable only through F1. Nothing on screen states it.
- New Form: Cancelling silently is correct here.
- Insert > Form Field: The payment kind is offered in the list even where Form Payments is turned off in QUILL. It then answers with the Features refusal.
- Insert > Form Field: When choices and a library are both left empty on a choice kind, a placeholder "Choice 1" is added without saying so.
- View > Form Outline: Cancelling Rename, Change Id or Change Type speaks "Nothing changed." That is a spoken result for a cancel, where every other Cancel in Forms is silent. This is mild chattiness.
- View > Form Outline: An Alt+Shift+arrow move on a disabled action only beeps (`wx.Bell`). Nothing is spoken.
- Format > Form Rules: Enter or Go to It on a free-standing rule row (the kind stored in the form's rules list) does nothing at all, silently (`go` returns None when the row's kind is "rule"). The list help promises "Press Enter to go to the question it is on."
- Format > Form Rules: The Add Rule dialog's Then default is "show" and its target default is the last question. A rule added with every default is "Show {last question} when {first question} is """. That is valid, but probably not what was meant.
- Tools > Forms > Check This Form: Check Again is a dead end. The window is modal, so you cannot change the form while it is open, and "Check Again after you change it" can never show anything new. When Check Again does empty the list, nothing is spoken.
- Tools > Forms > Fill It In Yourself: Submit does not check the last page's required questions the way Next does. It only lists them at the bottom of the report.
- Tools > Forms > Fill It In Yourself: Next both moves focus (which the screen reader reads) and announces the page heading. Those two can talk over each other. The heading is not otherwise spoken, so the announcement is allowed under GATE-13, but listen for collisions.
- Tools > Forms > Form Properties: Emptying the Title is silently ignored: the old title is kept, with no message.
- Tools > Forms > Form Properties: The read-only box's label "On the site (read only):" has no access key, so the only way to reach the box is Tab.
- Tools > Forms > Form Properties: It says "saved in the document" even when nothing changed.
- Tools > Forms > Form Payments Setup, Insert Payment Field, Verify Payment Setup: Insert Payment Field always adds the field at the end of the last page, whatever the caret position. Insert Form Field places items at the caret.
- Tools > Forms > Form Payments Setup, Insert Payment Field, Verify Payment Setup: The Lite gate bypass is described under QUILL Lite differences.
- Tools > Forms > Publish Form: After the first publish, Publish Form never asks for a site again: the stored link wins (`choose_site` returns the preferred site first). There is no route in the editor to publish the same form to a second site.
- Tools > Forms > Publish Form: Nothing is spoken while QUILL reads the site and then publishes. The task names ("reading {site}", "publishing to {site}") are not announced, so on a slow site there is silence between the button and the result.
- Tools > Forms > Responses (the editor's Responses window): Access-key collision. The list label "&Responses:" and the button "&Read" both claim R in one window. Under GATE-14, Windows cycles between the two instead of pressing, so Alt+R may never press Read. The dialogs are built at runtime, so the static gate may not see it. Verify.
- Tools > Forms > Responses (the editor's Responses window): Refresh Payment Status is the first button in the bar, and is shown for every form, payment or not. The first Tab stop after the list is a payments command most forms never need.
- Tools > Forms > Responses (the editor's Responses window): Delete takes the rows out of the list before the site has answered. If the delete then fails, only the failure sentence is spoken, and the rows stay gone from the window until it is reopened.
- Tools > Forms > Responses (the editor's Responses window): Mark is silent. Whether the reader re-reads the changed row after `set_rows` is not certain. Listen for it.
- Tools > Forms > Responses (the editor's Responses window): From a published form document, Responses always opens that form. To read another form's responses you must first switch to a document that is not a form. Nothing says so.
- Tools > Forms > Responses (the editor's Responses window): This window and the Workbench's Responses do different jobs. The editor has Read, Find, Mark, Export, Summarise and Delete, but no Spam or Not Spam. The Workbench has Spam, Not Spam, Search on the Site and Saved Views, but no Delete and no Export of QAF responses. Someone handling spam and exports has to use both.
- Tools > Forms > Draft a Form, Plain Language, Suggest Autofill Hints: Draft a Form sends as soon as you press OK. Only a spoken sentence comes first, with no confirmation, which is acceptable because only your own description goes. Summarise asks every time, as it should, because it sends people's answers.
- Tools > Forms > Draft a Form, Plain Language, Suggest Autofill Hints: "The draft is in ... Undo takes it out" replaces the whole form, including any rules or properties you wrote. The confirmation says "replace the form in front", which is honest, but it is a large single step.
- Workbench: the Forms node and its rows: Four nodes say "Responses" or "Held as Spam" in two places each. Forms > Responses and Attention > Form Responses are the same thing under two names. Forms > Held as Spam and Attention > Held as Spam share a name and differ in scope (the Attention one also has comments).
- Workbench: the Forms node and its rows: The 300-row and 3-page caps cut the list silently. A busy form shows fewer responses than its count, and nothing says the list is partial.
- Workbench: the Forms node and its rows: The response row's help mentions only Gravity Forms extras. It never says that Ctrl+Shift+S marks spam and Ctrl+Shift+A releases.
- Workbench: Show Its Responses (on a form row): The filter goes by the form's title, not its id. Two forms with the same title, or a title that is part of another title, may share one filtered list. This is plausible from the code; verify how the filter matches.
- Workbench: Show Its Responses (on a form row): It shows only Received responses. Held-as-spam responses to the same form are in a different node, and nothing tells you they exist.
- Workbench: Change Form Status (QAF form row): The preview's summary uses the raw status word ("becomes inactive", "becomes active") while the lines and the result use the friendly phrase ("closed, shown but not taking responses"). Two vocabularies in one preview.
- Workbench: Change Form Status (QAF form row): There is no undo, and no Change History entry. A Ctrl+Z pressed afterwards undoes whatever was recorded before, which may be an earlier spam mark, not this status change. This is plausible from the `_record` and history design; verify.
- Workbench: Form Settings (QAF form row): Settings are shown by their raw keys with underscores turned into spaces (for example "save continue enabled"). They are not friendly labels.
- Workbench: Form Settings (QAF form row): Only one setting can be changed per trip. Changing three means three round trips through the menu.
- Workbench: Saved Views and Search Responses on the Site (QAF form row): Saved Views is offered on one form's row but lists every view on the site. Views of other forms are named "form {id}", because only this form's title is known.
- Workbench: Saved Views and Search Responses on the Site (QAF form row): Search results are a read-only report, not rows. You cannot mark a found response as spam, or open it, from there. It searches Received responses only (`status: active`), so held spam is never found.
- Workbench: Delete Form (QAF form row): Pressing Cancel at the name question also says "The name typed did not match, so nothing was deleted." That reads as an error for a deliberate cancel.
- Workbench: Delete Form (QAF form row): "Export the responses first (Tools > Forms > Responses)" sends a Workbench user to the editor's menu, because the Workbench cannot export QAF responses itself.
- Workbench: Not Spam and Spam (on a response row): "and the site was told" is said even when an older QAF only moved the response and told nobody. `mark_entry` returns the providers it told, and nothing reads that list.
- Workbench: Not Spam and Spam (on a response row): The wording is borrowed from comments. Marking a response spam says "1 item marked as spam", and Not Spam on a response that was not held says "1 item approved". Responses are never "approved".
- Workbench: Not Spam and Spam (on a response row): Item > Unapprove (Ctrl+Shift+U) on a response acts as Not Spam but announces "1 item unapproved on {site}."
- Workbench: Not Spam and Spam (on a response row): Undo reverses every selected response, including any whose change failed. After Not Spam on a response that was already Received, Ctrl+Z marks it as spam. Plausible from `_moderate`; verify.
- Workbench: Not Spam and Spam (on a response row): The permission refusal talks about "Editing posts" when the person is marking a form response. That is accurate to the capability, but confusing.
- Workbench: Not Spam and Spam (on a response row): QAF responses also show Notes... and Resend Notifications... in the context menu (the Gravity rows are shared). Both refuse with "That is a Gravity Forms command. Choose a Gravity Forms form, entry or feed; QUILL Accessible Forms keeps no notes, feeds or notifications." Star or Unstar and Mark Read or Unread do work on QAF responses ("Starred {n} entries on {site}." and similar, with undo). The node help says these four are Gravity Forms only.
- Workbench: the site row's QAF spam commands: Cancelling the Question prompt of Add a question announces "A question needs its words and at least one right answer. Nothing was added." That is a reproach for a deliberate Cancel.
- Workbench: the site row's QAF spam commands: The Spam page's save remembers the revision read when the sheet opened. A second Apply in the same sheet, after a first that succeeded, sends the old revision and is likely to be refused as a conflict caused by your own first save. Plausible from `site_sheet_with_spam`; verify.
- Workbench: the site row's QAF spam commands: `on_save` returns True as soon as the background save starts. The sheet can close before a conflict is reported, and the edits typed into it are lost with it.
- Workbench: the site row's QAF spam commands: These two commands sit on every site row, including sites with no QAF. There they answer "This site has no QUILL Accessible Forms." only after a background read.

##### The WordPress Workbench window

- Opening it: Start Here still says "This is an early preview, behind a developer setting. Your Tools > WordPress windows still work." (workbench_help.py START_HERE). Both sentences are false now: there is no developer setting and the doors always open the Workbench. The first thing a new user reads is wrong.
- Opening it: A door opens on the FIRST site in the store, not the default site and not the site of the open document: current_site() falls back to next(iter(self._profiles)) because frame.current is still None when _start_ref runs. With two sites, Tools > WordPress > Users from a document on site B opens site A's Users.
- Opening it: The window does not remember its place across closes. The frame supports recall_place/remember_place hooks, but the WordPress provider implements neither, so every fresh open starts at Inbox with the tree collapsed. The GitHub Workbench does remember.
- Opening it: Closing the Workbench silently stops a running Practice Site. A person who opened the practice site from here and closes the window to write in the editor loses it without a word.
- Opening it: The workbench_door docstring (wordpress_commands.py) still says it returns False "without the developer flag"; it never does. Harmless to users, misleading to maintainers.
- Layout and panes: Start Here's words live in the Details box, but Ctrl+9 leaves focus on the tree, over an empty list. A first-time user has to press F6 three times (filter, list, details) to read the page they asked for. Ctrl+9 should land in Details, or Start Here should open its text where focus goes.
- Layout and panes: Escape outside the filter box goes Back to the previous node, from any pane, including Details. "Read in Full" (Enter on a comment, plugin, fact and many other rows) moves focus to Details; the natural Escape to return to the list instead navigates the tree to a different node and throws away the list you were reading. Escape in Details should return to the list.
- Layout and panes: Backspace in the tree goes Back. The native tree's type-ahead uses letters, so this is safe, but Backspace as navigation is a browser idiom that surprises in a tree.
- The tree: Every site gets every plugin's branch whether or not the plugin is installed: Shop alone is 16 nodes, Events Calendar 6, Memberships 6, plus SEO, Podcast, Forms' Feeds and Results. That is well over 100 nodes per site, most of which, on a typical site, load only a sentence such as "<site> does not list WooCommerce's wc/v3 routes in its REST index, so it has no shop QUILL can read." For a screen-reader user arrowing through a site this is the single biggest cost in the window. Hide or collapse branches whose namespace is absent from the site's REST index.
- The tree: Every tree selection fires a network load. Arrowing down through a site sends a request per node passed (stale answers are dropped, but the requests still go out). A short delay before loading, or loading only on Enter or a pause, would cut the traffic and the "Loading" churn in the status bar.
- The tree: Discovery rebuilds the whole tree once per connected site shortly after opening. rebuild_tree deletes and re-adds every item, so any branch you expanded in the first seconds collapses again, and the current node is re-selected (the reader may say it again) and its list reloaded. Keep expansion state across rebuilds, or add discovered nodes in place.
- The tree: "Drafts" under Needs My Attention is "Your own drafts, on every site" (NODE_HELP), but the label is just "Drafts", the same word as Posts > Drafts. "My Drafts" would say what it is.
- The tree: "Site Health" and "Held as Spam" each appear twice with different meanings (across sites under Needs My Attention, and per site). The labels do not say which is which; only the position does.
- The tree: Search has no Go key and no menu row; it is reachable only through the tree, and it only works with words typed into the filter box, which is not obvious from the node name.
- The list: Column headers and the Columns dialog disagree on names: the list header is name.replace("_", " ").capitalize() in the frame, the dialog uses column_title, which renames some ("mime_type" is "File type" in the dialog, "Mime type" in the header; "id" is "Number" in the dialog and "Id" in the header). One function should name a column everywhere.
- The list: The Columns dialog's help says "Check each column the list shows, in this order. The first is what your screen reader says first." but the dialog cannot reorder anything; the order is fixed. Either offer Move Up and Move Down or drop "in this order".
- The list: Column choices, groupings and Load More depth are kept in memory only (column_choice, grouping, paging on the provider) and are lost when the window closes.
- The list: Group By counts come from the rows currently loaded and filtered (frame.rows), not from the site, so "Draft (12)" can be the 12 among the first 300, not the site's total. The node label gives no hint.
- The list: Load More, Load All, Refresh and remote filters announce when they START but never when they finish. A blind user hears "Reading every row. A big site takes a while." and then silence, with no signal that the list is ready except polling the Loading status cell. GATE-13 does not forbid saying a background result; "Loaded 1,240 rows." is exactly the kind of thing the reader cannot know.
- The list: The precise sentence cut_words builds ("The first 300 are shown, and the site has more. View > Load More reads 300 more; Load All reads every one.") is computed and stored but never shown or spoken; only the terse ", more on the site" reaches the Items cell.
- The list: "More on the site" is decided by count >= limit, so a site with exactly 300 posts is told there are more.
- The list: An empty list says nothing. "No comments are waiting on Radio." in Details (via the empty_text hook) would answer the first question a listener has.
- The list: Ctrl+A and Ctrl+C do nothing in the list: the frame has select_all and copy verbs, but the WordPress menu binds neither, and a native list view does not select all on Ctrl+A. Select-all-and-act is a common screen-reader workflow (for example Approve all waiting comments).
- The list: After any refresh the landing row is selected alone (focus_row deselects the others), so a multi-selection is lost after every batch action.
- The filter box and filter commands: Ctrl+Shift+F never opens the Filter Builder. The frame's key hook (_on_char_hook: "if event.ControlDown() and event.ShiftDown() and code is F: self.filter.SetFocus()") runs before menu accelerators (the keep_list_key docstring states that order), so the chord only moves to the filter box. The menu shows Ctrl+Shift+F, the filter box help and the Keys node both teach it, and only the menu click works. This is a GitHub-only alias leaking into WordPress.
- The filter box and filter commands: The same hook catches Ctrl+Alt+Shift+F (it checks Control and Shift, not Alt), so Tools > Forget a Saved Request's chord also just moves to the filter box.
- The filter box and filter commands: "Filtering." is said and then nothing: the listener never hears how many rows the site sent back. Say "<n> shown." when the remote answer fills the list.
- The filter box and filter commands: Filter wording is raw: Only Mine adds author:7, so Alt+1 says "filtered to author is 7", and the Filter Builder asks for "Author number" and "Parent number". People do not know their user number. describe() takes attribute labels but the WordPress window never passes any.
- The filter box and filter commands: The Filter Builder offers "after" and "before" for every attribute, including Status and Slug, where they mean nothing, and offers no "contains". Operators should follow the attribute.
- The filter box and filter commands: Only Mine's refusal ("once the site has said who you are") is wrong when the real problem is that you are on Needs My Attention or another non-site node.
- The filter box and filter commands: Edit > Filter... has an ellipsis but opens no dialog; it only moves focus.
- The filter box and filter commands: Filters are cleared without a word when you change nodes. A listener who filters Posts, checks Pages and comes back finds the filter gone. At least the Filter status cell shows "No filter".
- The filter box and filter commands: describe_scope in workbench_filter.py (the "Filtered on this computer, 12 rows loaded" sentence the docstring promises) is not used anywhere in the UI.
- The Properties sheet and Site Properties: WordPress gets the simpler sheet. GitHub's PropertiesSheet has Ctrl+S to apply, Ctrl+Enter for OK from a multi-line box, F5 reload, Ctrl+1 to Ctrl+9 page jumps, Ctrl+Shift+C copy, a "Sheet status" line showing what the last save did, and opens on the last page used. The WordPress sheet has none of these, so the two Workbenches teach different keys for the same window.
- The Properties sheet and Site Properties: OK closes before the save is done. If the save then fails, or a conflict is answered Cancel, the typed changes are gone with no way back. Keep the sheet open until the site answers, or reopen it with the edits on failure.
- The Properties sheet and Site Properties: Apply twice in one sheet will likely raise a false conflict: on_save always passes the modified time read when the sheet opened, so the second Apply finds the site's time changed by your own first Apply and asks "changed on the site after you opened it ... replacing theirs?". (Plausible; depends on the modified time changing between saves.)
- The Properties sheet and Site Properties: Apply updates the sheet as if the save succeeded before the site answers; there is no status line on this sheet to show a failure.
- The Properties sheet and Site Properties: Changing Status to publish on the sheet publishes immediately on OK, with no "Visitors will see them" confirmation, while Item > Publish or Update asks first. The same outcome should not have two confirmation levels.
- The Properties sheet and Site Properties: Status values are raw slugs (publish, future, pending), and Comments and Pingbacks are "open" and "closed". WordPress's own screen says Published, Scheduled, Pending Review, Allow comments. A choice box can show words and send slugs.
- The Properties sheet and Site Properties: The batch confirmation prints list values as Python tuples: "Add categories to ('News', 'Events')" (the f-string formats the tuple from value_of). Format lists as words.
- The Properties sheet and Site Properties: The conflict box offers "Use Mine" and "Cancel"; the module docstring promises "Use Mine or Keep Theirs". "Keep Theirs" (and re-reading their version) is the more useful second choice than a bare Cancel that discards your edits silently.
- The Properties sheet and Site Properties: Escape and Cancel discard edits without asking, even after many changes across pages.
- The Properties sheet and Site Properties: Tab order (Copy as Text, OK, Apply, Cancel) does not match the visual order (OK, Cancel, Apply) because Apply is created before Cancel.
- The Properties sheet and Site Properties: Field labels carry no access keys, so a long General page can only be walked with Tab.
- The Properties sheet and Site Properties: Site Properties is almost all read-only text boxes inside a modal sheet with OK/Cancel semantics; "Close" is right, but a listener must Tab through every read-only box to reach it or press Escape.
- The context menu: The reason a row is greyed is never heard. The menu-bar reason goes into the item's help string, but the frame calls SetStatusBarPane(-1), so menu help is shown nowhere, and screen readers do not read menu help strings. In context menus no reason is set at all. The only place the real sentence appears is when a command is run by key.
- The context menu: The WordPress provider has no reason() hook, so the frame's fallback is used: every greyed row's reason is "Not available here." (workbench_frame_commands.py reason), including in Shift+F1's list (", greyed: Not available here."). The good refusal sentences exist in refusal_for but are not wired to reason().
- The context menu: Context menu rows show no keys and have no access letters, and "More" has none either. The help strings carry the keys ("Delete.", "Ctrl+Shift+P.") but, as above, are never displayed. A listener learns no chords from the context menu.
- The context menu: On a post, Copy Link and Delete Permanently sit inside More, behind Visual Review and Restore from Trash. Restore from Trash is shown on top even for a post that is not in the Trash (it then says "Nothing selected is in the Trash."). The top six should be the ones that apply to the row's state.
- The context menu: "Empty Trash..." (a whole-site, permanent action) is offered on a single post's context menu, under More. A row menu should hold only actions on the row; this one belongs on the node.
- The context menu: On a user, "Cancel Membership..." (DESTRUCTIVE) is on top while "Send Password Reset" is buried in More.
- The context menu: Greying only reflects permission, never applicability: a comment command on a post row is enabled and then says "Choose a comment or a form entry." when run (see the Item menu below).
- The context menu: Merge Into and Convert are DESTRUCTIVE and confirmed, but record nothing in Change History at all, while Delete Permanently records an entry marked cannot be undone. Change History is therefore not "every change made here".
- History and undo: A change that cannot be undone blocks every earlier undo. next_undo() always returns the newest change, and undo() never removes one without an inverse. After one Delete Permanently, Import, REST Console write or Plain-Language Batch, every Ctrl+Z repeats "<summary> This cannot be undone." and the Trash you did five minutes earlier can no longer be undone from here. Ctrl+Z should skip (and say it skipped) entries with no inverse, or Change History should let you undo a chosen entry.
- History and undo: Change History is read only: you cannot pick an entry to undo, and entries have no times (Change.when is never set).
- History and undo: The undo message for summaries like the batch ("move all drafts by Sam to pending on Radio This cannot be undone.") reads as one run-on sentence; the summary needs its own full stop.
- History and undo: Ctrl+Z in the tree is silently ignored; a short "Ctrl+Z works in the list, or use Edit > Undo." would be better than nothing.
- History and undo: A failed undo leaves the change on top, so pressing Ctrl+Z again retries; that is reasonable, but the failure text is the raw error.
- The status bar: The Waiting cell's count is filled only when Needs My Attention > Comments Waiting has been loaded in this window; before that the cell is absent, and it goes stale until that node is loaded again. It reads like a live count and is not.
- The status bar: "1 comments waiting": the plural is fixed.
- The status bar: The Role cell's Enter opens the provider's role-aware report ("You are <Role> on <site>. ... <Action>: yes" or the refusal), which is what Shift+F1 promises but does not open (see Help). Two different What Can I Do Here windows exist.
- The status bar: The Filter cell is always present with "No filter", so F6 into the bar always lands on Site, Your role, Items, Filter, Loading before anything useful changes; fine, but the Items cell already says the count, so most visits read five cells to learn one fact.
- The status bar: A site name containing "&" becomes an access-key mnemonic in the cell's button label (SetLabel with the raw name). Minor, but it can swallow the character.
- F1, Shift+F1 and Help for This View: Shift+F1 opens the wrong window. "what_can_i_do" is a frame verb, so the frame's generic list runs and the provider's do_what_can_i_do (which starts "You are <Role> on <site>. Workbench access on <site> is <Access>." and gives the real refusal for each action) is unreachable from Shift+F1 and from the menu. The menu row's help says "What your role allows." and the Keys node says "Shift+F1: What your role lets you do here."; neither is what opens. The role-aware report is reachable only from the Your role status cell.
- F1, Shift+F1 and Help for This View: In the frame's list, every greyed row says "greyed: Not available here." (no reason hook), and "About this action" shows only the help, never the reason. So the window that exists to say why you cannot do something never says why.
- F1, Shift+F1 and Help for This View: The list is a plain list box; "greyed" rows are not disabled items, just text, and Enter on them only beeps.
- F1, Shift+F1 and Help for This View: F1 has no purpose sentence (no help_purpose hook) and no "open the guide" button: guide routes are registered only for GitHub windows (guide_opener.py), so the WordPress Workbench's F1 cannot open a user guide.
- F1, Shift+F1 and Help for This View: Alt+F1 (What Is This?), Ctrl+F1 (guide chapter), Ctrl+Shift+F1 (Search Help), Alt+Shift+F1 (Keys) and F9 (repeat last result) exist in the shared frame but are not on the WordPress menu, so they are not bound. The Keys node lists only 18 keys and is called "Every key the Workbench answers to" in its help; it omits Ctrl+9, Ctrl+N, F5, the Go row beyond Ctrl+1 and Ctrl+2, and the whole Site and Tools menus.
- F1, Shift+F1 and Help for This View: The Keys node teaches Ctrl+Shift+F for the Filter Builder, which does not work (see The filter box).
- F1, Shift+F1 and Help for This View: The Help menu has one row. Start Here (Ctrl+9) is on the Go menu, and What Can I Do Here? is on the Site menu; a listener looking for help in Help finds neither.
- Workbench Access, View As Role, and Roles: Workbench Access, Safe Mode and View As Role are enforced only for commands that appear in the selected row's action table (refusal_for returns "" for any command not in that table, and for no row). Menu-bar-only commands do not check access: Site > Empty Spam and Empty Comment Trash (permanent deletes), Edit > Import Posts and Import a Folder of Documents, Tools > WXR Files > Import WXR as Drafts, Site > Put Back from a Snapshot, Tools > REST Console (POST, PUT, PATCH and DELETE go straight through after its own preview), and New Here. So "Read Only: look, never change" and View As Role's "Nothing can be changed until you stop" are not true, and Safe Mode ("the Workbench only reads") can still delete every spam comment. This is the most serious finding in the window.
- Workbench Access, View As Role, and Roles: Ctrl+Alt+R does not open Roles: the frame's key hook treats any Ctrl+R without Shift, Alt included, as Reload ("event.ControlDown() and not event.ShiftDown() and code is R"), and it runs before the menu accelerator. Only the menu and the context menu reach it.
- Workbench Access, View As Role, and Roles: When you are not inside a site (for example on Needs My Attention), all three silently act on the first connected site; only the Workbench Access prompt names it.
- Workbench Access, View As Role, and Roles: View As Role always preselects "Myself, as I am", not the role you are currently viewing as.
- Workbench Access, View As Role, and Roles: View As Role is per window and forgotten on close; Workbench Access is per site and persistent. The status bar shows both, but nothing tells you that one survives and the other does not.
- Menu bar: File: New Here's menu help, "A new user or password, where you are.", is out of date: it also makes posts, pages, custom items, categories, tags, terms, menus, redirects, discount codes, shop and event items and forms.
- Menu bar: File: File has no Close Window-style "Open the Editor" or Export; that is fine, but Export List and the imports live in Edit, where a Windows user would look under File.
- Menu bar: Edit: No Cut, Copy, Paste or Select All rows: Ctrl+C and Ctrl+A do nothing in the list (see The list), and the familiar Edit menu shape is missing.
- Menu bar: Edit: Only Mine is a toggle but is not a check item, so the menu does not say whether it is on.
- Menu bar: View: "Load All" says "Read every row the site has." but stops at 10,000 (ALL_PAGES 100 pages of 100).
- Menu bar: View: Back's help mentions Backspace but not Escape, which also goes Back and is the more surprising of the two.
- Menu bar: Go: Every Go key leaves focus on the tree, not the list. After Ctrl+Shift+4 (Comments) you still need F6 twice to reach the comments. A Go key is a "take me to the things" key; landing in the list (or making that an option) would save two presses every time.
- Menu bar: Go: The Go row's digits are not in the order of the tree: Ctrl+1 Needs My Attention, Ctrl+2 Current Site, Ctrl+3 Calendar, Ctrl+5 Watches, Ctrl+6 Practice Site, Ctrl+9 Start Here, Ctrl+0 Across Sites, with 4 and 8 empty. The menu lists them Start Here first but Start Here is Ctrl+9. Hard to learn by ear.
- Menu bar: Go: "Appearance" lands on Themes, and "Needs My Attention" lands on Inbox, not on the folder the label names; the Where Am I words will differ from the menu word.
- Menu bar: Go: Across Sites lands on a folder with an empty list; Ctrl+0 then Right Arrow is always needed.
- Menu bar: Go: Practice Site appears as Go > Practice Site (Ctrl+6) and Tools > Practice Site... (Ctrl+Alt+P), two rows with the same name doing different things (a node versus a start/stop dialog).
- Menu bar: Go: Parent Node at the top silently does nothing.
- Menu bar: Item: The four Gravity entry rows cannot be reached by letter. Free letters remain (H, J, K, Q, X, Z), so they could have them.
- Menu bar: Item: The Item menu has 23 top-level rows plus a 10-row submenu, for every row kind at once. Greying is by permission only, so on a post, Approve, Spam, Reply, Merge Into, Convert, Entry Notes, Star and the rest are all enabled and each says a refusal sentence when chosen ("Choose a comment or a form entry.", "Merge Into works on a category, tag or term."). A listener walks past 15 irrelevant rows to find Publish. Grey by row kind too, or build the Item menu from the selected row's action table (which is what the actions.py docstring says the Item menu is: "the same rows, in the same order").
- Menu bar: Item: Greying is computed only when a menu opens (EVT_MENU_OPEN), never on selection change. On Windows a disabled menu item's accelerator does not fire, so a chord greyed the last time you opened the menu (for example while access was Read Only) likely stays dead, silently, until you open that menu again. (Plausible; verify on Windows.)
- Menu bar: Item: Delete Permanently's help says "after you confirm by name", which suggests typing the name; the dialog only lists names and asks Yes or No. Say "after you confirm" or really ask for the name.
- Menu bar: Item: Delete and Shift+Delete do nothing, silently, in the tree and Details (keep_list_key swallows them); in the filter box they edit text, which is right.
- Menu bar: Site: "Empty Spam" takes M and "Empty Comment Trash" takes E, so the two siblings that start with the same word do not share a letter pattern; acceptable, but E for "Empty" belonging to the second row is a trap for the first.
- Menu bar: Site: Empty Spam and Empty Comment Trash run under Read Only, Safe Mode and View As Role (see Workbench Access).
- Menu bar: Site: What Can I Do Here? belongs in Help.
- Menu bar: Tools: Workbench Options holds only Watches. The name promises the window's options (columns, landing node, Go-key focus, announcements) and delivers one checklist; "Watches..." would be honest, or the options should grow.
- Menu bar: Window: The menu could also list the editor's other open windows; with one row it is a long way to one command that already has a key.
- Menu bar: Help: Start Here, What Can I Do Here?, How WordPress Thinks, Words and Keys are all help and none is here.
- New Here: A new post or page is made on the site and then left there: it is not opened in the editor, the new row is not selected, and the person must find it in the list. "Made the post X on Radio as a draft." followed by opening it in the editor (or at least selecting the row) is the expected flow.
- New Here: A category asks for its parent by number. The site has the category list; a choice would do.
- New Here: A chain of one-field dialogs, each with the same title, is slow and gives no sense of how many steps remain.
- New Here: Not in Change History, so Ctrl+Z cannot undo an accidental Ctrl+N.
- Open on the Site, Preview, Copy Link: With nothing selected, or on Needs My Attention, Open on the Site and Copy Link fall back to the FIRST connected site's address and say only "Copied." A listener cannot tell they copied a home page rather than the row. Say what was copied ("Copied the address of Hello World.") or refuse without a row.
- Open on the Site, Preview, Copy Link: Shift+Enter and Ctrl+Enter are window accelerators, so they also fire from the filter box, where a listener pressing Shift+Enter by habit opens a browser instead of running the filter.
- Open on the Site, Preview, Copy Link: Preview of a draft needs a signed-in browser; nothing says so if the browser is not signed in to wp-admin.
- Export List: The left-out sentence is spoken in full on every export. It is honest but long; the hidden-columns part is news, the rest is the same every time and could be in the help.
- Export List: When the list stopped at its 300-row limit, the export silently writes 300 rows; the generic "not loaded yet" phrase does not say that this export is short. Say "300 of more than 300; Load All first for every row."
- Export List: The file is written on the UI thread; a 10,000-row Excel export will freeze the window briefly.
- Import Posts from a Spreadsheet: Importing from the Media or Comments node makes posts, without saying that it chose posts; the preview's first words should say "posts" or "pages" explicitly and let you switch.
- Import Posts from a Spreadsheet: The Open dialog offers no "All files" choice (the helper choose_spreadsheet in wordpress_workbench_dialogs.py, which says "Spreadsheets saved as CSV", is a different, unused-here dialog).
- Import Posts from a Spreadsheet: The import could easily be undone (move the new drafts to the Trash) but is not.
- Import a Folder of Documents: The chord Ctrl+Alt+Shift+I is a four-key chord for an action used a few times a year; rule 9 would say a letter is enough.
- Import a Folder of Documents: Same Undo and access gaps as the spreadsheet import.
- Workbench Options: Every check box starts with "Watch:", so a listener hears "Watch" eight times; the group could be labelled "Watches" and the boxes left plain.
- Workbench Options: The fifteen-minute interval (watch_minutes) is stored but not offered.
- Workbench Options: The module docstring names quill.core.wordpress.workbench_flag.workbench_window_enabled, a flag the doors no longer read.
- REST Console: The console ignores Workbench Access, Safe Mode and View As Role: a DELETE goes through under Read Only after only its own preview.
- REST Console: do_rest_console calls self.ensure(...) on the UI thread before the dialog opens, which may block on two network reads for a site not yet read.
- REST Console: "answered." is said even when the site answered with a WordPress error object in a 200 body; the listener has to open the tree to learn it failed.
- REST Console: The docstring calls the copy button "Copy Answer"; it is "Copy JSON". The help on Save Request warns "Do not type a password into the parameters of one you keep." which is the right warning but the saved file is not encrypted; a stronger guard (refuse to save a parameter named password) would be safer.
- Run a Saved Request, the Saved Requests submenu, Forget a Saved Request: Ctrl+Alt+Shift+F does not reach Forget: the frame's Ctrl+Shift+F hook catches it and moves to the filter box.
- Run a Saved Request, the Saved Requests submenu, Forget a Saved Request: run_saved also calls ensure on the UI thread.
- Run a Saved Request, the Saved Requests submenu, Forget a Saved Request: A saved request for a site that is gone silently runs against a different site (the current one). For a saved write, that is a risk; say which site it will use, or refuse.
- Run a Saved Request, the Saved Requests submenu, Forget a Saved Request: Only nine show in the submenu with no "More..." row; the tenth is reachable only through Run a Saved Request.
- Plain-Language Batch: The help says "press Change" but the button is OK (ask_checks uses the default OK label). Name the button Change, as the other previews do.
- Plain-Language Batch: The checklist is the only preview: it lists items but not the change itself per item (for example "Draft becomes Pending"); the phrase is only in the F1 help. Put the change sentence above the list.
- Plain-Language Batch: A batch over many items cannot be undone, although every item's before-state was read.
- Read Site as Document: The row has no ellipsis although it opens a dialog first.
- Read Site as Document: Nothing is said while a large site is read; a long silence follows the choice.
- Your Profile: A four-key chord for an occasional command; most people change their profile a few times ever.

##### Posts and pages

- The tree nodes and what the list shows: the six status children under Pages use the Posts columns and are not tree-ordered, so Pages > Drafts loses the Level column the Pages node has. Moving from Pages to Pages > Drafts silently changes the column set.
- The tree nodes and what the list shows: the extra column titled "Comments" shows the item's comment_status ("open" or "closed"), not a count. A listener will expect a number. Calling it "Comments allowed" would fix that.
- The tree nodes and what the list shows: dates in the list and details pane are made from modified_gmt and date_gmt by friendly_date, which the code documents as "UTC as given". Nothing in the cell says UTC, so a site in another time zone hears times that look local and are not.
- The item row's context menu, as it is actually laid out: "More" is appended with no access key, and the context menu labels carry no chord text. The chords live only in each row's help string, which goes to the status bar and is not normally spoken. So the context menu never teaches a listener that Delete Permanently is Shift+Delete or Approve and Schedule is Ctrl+Shift+D.
- The item row's context menu, as it is actually laid out: actions.py promises that "the same rows, in the same order, are the Item menu, so More never hides anything that only a right-click could reach". The WordPress Item menu breaks that promise. Open in Editor, Visual Review, Earlier Versions, Duplicate as Draft, Counts by Status, Empty Trash and Open in wp-admin are only on the context menu, and the Item menu's order differs from the context menu's.
- The item row's context menu, as it is actually laid out: Delete Permanently, a tier 3 command, sits first under More, directly above the harmless Copy Link. One arrow press separates a copy from a permanent delete. The confirmation stops it, but its placement is still careless.
- The item row's context menu, as it is actually laid out: a greyed row gives no reason when you arrow onto it. The reason is reachable through Shift+F1, but nothing in the menu points there.
- Open in Editor: an Author pressing Enter on someone else's page hears a refusal and nothing else. Offering to open it read only, or pointing at Preview on the Site (Ctrl+Enter), would turn the dead end into a choice.
- Preview on the Site: a draft's preview link only works for someone signed in to WordPress in that browser. Open in wp-admin says "You must be signed in to wp-admin in your browser" and Visual Review explains the same limit, but Preview says nothing, so the first time someone previews a draft they meet a login page with no warning.
- Preview on the Site: Open on the Site (Shift+Enter, File > Open on the Site, Alt+F, S) is the published address. It is not on the item context menu at all, though it is on the Site row's.
- Visual Review...: the row is enabled on drafts, pending and scheduled items, where it can only refuse. It is one of the six top rows, so most of the time it is the wrong thing to offer there. It should be greyed, or say before it starts, when the row's status is not "publish".
- Publish or Update...: the label promises "or Update", but published items are filtered out before anything happens, so on a published post the only result is "Nothing selected is waiting to be published." Either drop "or Update" or make it update.
- Publish or Update...: there are two ways to publish now. This one uses a message box whose default is Cancel and records an undo. Approve and Schedule with an empty time uses a preview list whose default is Publish and records no undo (see below). The same act has two dialogs, two default buttons and two answers to Ctrl+Z.
- Publish or Update...: the help says "after a preview", but this is a message box, not the Workbench's preview window.
- Publish or Update...: when every item fails, an undo is still recorded, and Ctrl+Z says "Put 0 items back as they were."
- Approve and Schedule...: it does not look at status. It will "approve" a post that is already published and reschedule it into the future, which takes it off the site until then. Move to Another Day warns about exactly that ("Published items moved to a future time are scheduled again, and are off the site until then.") and this command does not.
- Approve and Schedule...: the items are sent one at a time in a single loop with no per-item outcome. If the third of five fails, the error is said, the first two are already changed, the rest are not, and nothing says which. Publish, Trash and moderation all report each item.
- Approve and Schedule...: a typing mistake in the time throws away what was typed. The error is spoken after the dialog has closed, and the person must press Ctrl+Shift+D and type it all again.
- Approve and Schedule...: "{n} published." and "Publish {n} on {site} now." say a bare number with no noun ("1 published."), unlike Publish's "Published 1 item on {site}."
- Send Back with a Note...: critical. It does not check status. On a published post it sets the post to draft, so the post disappears from the site, with no preview, no warning and no undo. The module's own docstring says "every change is previewed", and this one is not.
- Send Back with a Note...: an empty note cancels silently. A listener who pressed OK by accident on an empty box hears nothing and cannot tell whether anything was sent.
- Send Back with a Note...: "Sent back 1 as drafts" reads oddly for one item.
- Assign a Reviewer...: the fallback list is who=authors, which includes Contributors and Authors who cannot publish others' posts. The list's own help still says "who may edit and publish others' posts", so the fallback can offer people the help says are not there.
- Assign a Reviewer...: a typed name is not checked against anyone on the site; a misspelt reviewer is accepted and recorded.
- Assign a Reviewer...: the closing sentence is about forty words and is said every time. A short "Asked {reviewer} to review {n}. No email is sent." would carry the same fact; the Review Watch explanation belongs in F1.
- Move to Another Day...: the old date of every item is known before the move, so this is one of the easiest changes to undo, and it is not undoable.
- Move to Another Day...: with several items selected, the box shows only the first one's date and every item gets the same new moment. The preview does not show each item's old date, so a listener cannot hear what is being lost.
- Copy Link: when a row has no link, the provider falls back to the site's own address, and the outcome is still just "Copied." A listener pasting expects the post and gets the home page.
- Copy to Site...: "Replace" overwrites an existing item on the target site, and nothing can put it back. The preview line "Replace post About." is the only warning, and it is phrased like the harmless "Make" lines. A replace deserves its own sentence in the summary saying it cannot be undone.
- Show Its Comments: the count is spoken after focus has already moved to the list, so it competes with the screen reader reading the first focused row. One or the other gets cut off. Saying the count first, or putting it in the status bar, avoids the collision.
- Earlier Versions... (in progress): the date in the summary and the announcement is made by stripping "Saved " and cutting at the first comma. friendly_date writes "3 November 2026, 4:12 PM", so the time is cut off. Two versions saved the same day sound identical in the summary and in the closing sentence.
- Earlier Versions... (in progress): in the list, OK means "compare", not "restore". That is a reasonable two-step design, but it is the reverse of Their Application Passwords, where OK in a list means "revoke". The same list dialog means different things in different places.
- Earlier Versions... (in progress): only the title and content are restored. WordPress's own restore also brings back the excerpt; the preview does not say the excerpt is left alone.
- Duplicate as Draft: after the copy is made the list refreshes, and nothing in the handler moves the selection to the copy. Unless the refresh happens to land there, the next Enter opens the original rather than the copy someone presumably wanted to edit. Offering "Open the copy in the editor?" would close the loop.
- Counts by Status: a refused view is silently dropped, so "Private" may simply be missing from the sentence with no hint why. "Private: not shown to you" would be honest.
- Empty Trash...: critical. The preview window makes its action button the default, so Enter in this dialog permanently deletes the whole Trash. Delete Permanently on one item uses a message box whose default is Cancel. The most destructive command in this section is the easiest one to confirm by accident. Every tier 3 preview should default to Cancel.
- Empty Trash...: offered on any item row, even a published post in Posts > Published, where it empties the Trash of that whole kind rather than doing anything to the selected row. Its place on the row menu suggests it acts on the row.
- Open in wp-admin: a hand-off to wp-admin. The sentence is honest but long, and it is said every time. The REST explanation could live in F1, leaving "Opening wp-admin's editor. Sign in there if asked."
- Move to Trash: "Ctrl+Z puts them back." is said for a single item too.
- Restore from Trash: two restores behave differently. Ctrl+Z after Trash puts a published post back as published. Restore from Trash on the same post brings it back as a draft, which is WordPress's own rule. A listener who trashed a post yesterday and restores it today finds it is no longer on the site, and the closing sentence's "as drafts or waiting" is easy to miss.
- Restore from Trash: it is one of the six top rows on every item, including published posts where it can only say "Nothing selected is in the Trash." It is most useful in the Trash node, where it is the only row that matters.
- Delete Permanently...: "after you confirm by name" suggests typing the name, which some products require for a permanent delete. It is a Yes/No box that lists the names. The help should say "after a confirmation that names it".
- Delete Permanently...: it works on items that are not in the Trash, skipping WordPress's safety net. wp-admin offers Delete Permanently only from the Trash view.
- New Here (Ctrl+N), on Posts, Pages and content types: the File menu's help, "A new user or password, where you are.", is stale. New Here now makes posts, pages, terms, menus and more.
- New Here (Ctrl+N), on Posts, Pages and content types: in Posts > Pending or Posts > Scheduled the new item is still a draft, so it does not appear in the list you are standing in. Nothing says where it went, and focus does not move to it. Offering to open the new draft in the editor would finish the job.
- New Here (Ctrl+N), on Posts, Pages and content types: Read Only access, Safe Mode and View As Role ("Nothing can be changed until you stop") do not stop Ctrl+N here.
- Properties (Alt+Enter), one item: the Status, Comments, Pingbacks and Format choices are WordPress's raw slugs ("publish", "future", "open"). The list column says "Published" and "Scheduled" for the same values. A listener meets two vocabularies for one field.
- Properties (Alt+Enter), one item: Published is typed as "2026-11-09T14:00", while Approve and Schedule and Move to Another Day take "2026-11-20 9:00 AM". Three ways to set a date, two formats.
- Properties on several items at once: critical. Add categories, Remove categories, Add tags and Remove tags only understand "News (12)" or "12". A plain name such as "News" is silently dropped (the code calls term_ids with no name table and ignores what it cannot match). The confirmation still says "Add categories to News", the save reports success, and nothing was filed. The one-item sheet refuses an unknown name out loud; the batch sheet should resolve or refuse names the same way.
- Properties on several items at once: on one item Author is a choice of names; on several it is "Author number", a text box wanting a number. The same field asks two different things.
- Ctrl+Z and Change History, as they behave across these sections: critical. When the newest entry has no undo, Ctrl+Z says "{summary} This cannot be undone." and leaves that entry on top. It never moves past it, so every older change that could be undone becomes unreachable for the rest of the session. One Delete Permanently, Send Back or Move to Another Day locks out the undo of everything before it. Skipping past an entry that cannot be undone, and saying so, would keep the rest reachable.
- Ctrl+Z and Change History, as they behave across these sections: critical, the opposite problem. Reply, Merge Into, Convert, Allow This Sender, New Here and the two Empty commands are not recorded. Pressing Ctrl+Z straight after a Reply does not touch the reply; it undoes whatever came before it (an Approve, a role change) and says so in words that do not mention the reply. A listener expects Ctrl+Z to undo the last thing they did.
- Ctrl+Z and Change History, as they behave across these sections: when an undo itself fails (a conflict), the error is said and the entry stays on top, so the next Ctrl+Z tries the same failing undo again.
- Ctrl+Z and Change History, as they behave across these sections: the summary is reused as the start of the refusal, so the listener hears, for example, "Published on {site}. This cannot be undone.", a sentence about what was done followed by one about what cannot be. "Cannot undo: published on {site}." would put the answer first.

##### Media

- The media row's context menu: Insert into the Document is the second row on every media row, and it works only in picking mode. Outside picking mode it is enabled and can only explain itself. It should be hidden, or greyed, unless the Workbench was opened by Insert > Picture from the Media Library.
- The media row's context menu: Edit Picture, Regenerate Sizes and Download are offered on audio, video and documents too. Edit Picture and Regenerate Sizes refuse with "Edit Picture works on a picture in the Media Library." and "Regenerate Sizes works on a picture in the Media Library." Greying them on non-pictures would spare a round trip.
- The media row's context menu: the Item menu has none of the media commands except Copy to Site and Delete Permanently, and its Delete row still reads "Move to Trash" on a media row.
- View or Play: Enter, the most-pressed key, leaves QUILL. Arrowing through the library and pressing Enter to hear what a file is takes the listener into a browser tab every time. Read in Full (the details pane), or an in-app play for audio, would be a gentler default, with View or Play second.
- Insert into the Document: picking mode changes what Enter does, and nothing on the window says so after the first announcement. A listener who arrows away to the tree and back has no cue that Enter now inserts instead of opening a browser. Saying "Picking" in the status bar or the window title would keep the mode audible.
- Replace File... (just built): critical. If you chose "Delete the old file permanently", Ctrl+Z still puts every item back, pointing them at the old file, which no longer exists. The undo turns a working site into one full of broken images and links. Either refuse the undo after a delete, or refuse the delete when an undo is wanted, and say so in the old-file choice.
- Replace File... (just built): the two decisions with the largest consequences, deleting the old file and adding a redirect, are asked after the preview, so the preview the listener approved did not include them. Asking them first, and showing them as lines in the preview, would make the preview true.
- Replace File... (just built): when Enable Media Replace is not active, the "How:" list has a single row. It is a dialog with one choice, and Enter just accepts it. Saying the fact in the preview's summary would remove a step.
- Replace File... (just built): the help text says "every page, post and featured image" and the dialog says "every post, page, pattern and featured image". Small, but a listener checking whether patterns are covered hears two answers.
- Replace File... (just built): the closing sentence after a repoint can run past sixty words. Splitting it into the outcome now and the rest in a report window would be easier to follow.
- Edit Picture...: the preview's line "Sent to wp/v2/media/{id}/edit" is a REST route, not words. It is jargon in a dialog that otherwise speaks plainly.
- Edit Picture...: the edit is undoable in practice (delete the copy), and the closing sentence even says how, but Ctrl+Z will not do it and instead blocks everything older.
- Edit Picture...: a crop typing mistake closes the dialog and loses the four numbers.
- Attach to a Post or Page...: a number skips the search and is not checked. "Attach {title} to number 99 on {site}?" is asked even if post 99 does not exist, and the name in the confirmation is "number 99", not a title.
- Detach: the confirmation names the post by number only ("from post 412"). The listener cannot tell what they are detaching it from.
- Download...: the closing sentence reads out the whole path, which can be long. "Saved {file name}." is enough, since the person just chose the folder.
- Download...: the 2026-11-13 audit table says a file over 512 MB "opens in the browser". The code does not do that. download_file raises a too-big error and that error is what is said.
- Delete Permanently... (media), and the Delete key: the confirmation does not say where the file is used. By Name > Media Usage and Housekeeping already know, and the Housekeeping node "shows usage before Move to Trash". The plain Delete Permanently on a Media row can remove a picture that twenty pages show, with no warning.
- Delete Permanently... (media), and the Delete key: the role sentence says "Changing media" for a permanent delete, which undersells it.
- Properties (Alt+Enter), one file: the row's own F1 says "Alt+Enter edits its alt text", but alt text is on the second tab. Alt+Enter lands on Title, and the listener must press Ctrl+Tab to reach Alt text. For a library whose main accessibility job is alt text, Alt Text and Caption should be the first page, or Alt text the first field.
- Properties (Alt+Enter), one file: "Uploaded by" reads author_name, which the media route does not send and values_for does not fill. It is very likely always empty.
- Properties (Alt+Enter), one file: "Attached to number" is a bare number field. Attach to a Post or Page finds posts by words; the sheet does not.
- Properties on several files: setting one Alt text on many different pictures is rarely right, and nothing warns that every selected picture will get the same description.
- New Here on Media: wp-admin's Media screen has Add New. Uploading from the Workbench is not offered here; the sentence lists everything except what the listener is looking at.

##### Categories and tags

- The tree nodes and what the list shows: Categories and Tags have no Go key, while Posts to Site Health each have one. A listener reaches them by the tree.
- Show Its Posts: it always lands in Posts. For a plugin taxonomy that belongs to a custom content type (an Events category, say), the Posts list is filtered to nothing, or refuses the filter. It should open the content type the taxonomy is on.
- Show Its Posts: when the filter goes to the site, the first thing said is "Filtering.", and the count of what was found is not announced when it arrives.
- Merge Into...: the preview's lines are a route word and a number ("posts 123", "posts 98"), not titles. A listener hears a column of numbers and cannot check what moves.
- Merge Into...: the "Into:" list holds only the rows already loaded, by name only. Two categories called "News" under different parents sound identical, and a term past the first 300 is not offered.
- Merge Into...: the tier 3 preview defaults to Merge, so Enter merges and deletes.
- Convert to Category or Tag...: Convert does the same kind of change as Merge (move every post, delete the term) but previews less. It gives no count, no list and no "cannot be undone" warning; Merge gives all three. They should share one preview.
- Convert to Category or Tag...: on a partial failure the new term has already been made and some posts already moved, yet the sentence says only that the old term "was kept". The site is left with both terms and the posts split between them, and the listener is not told.
- Convert to Category or Tag...: converting a category with child categories or a parent says nothing about the hierarchy, which a tag cannot hold.
- Delete Permanently... (terms), and the Delete key: the confirmation does not say how many posts lose the term, though the Count column already knows. "News is on 34 posts" belongs in that sentence.
- New Here (Ctrl+N), on Categories, Tags and plugin taxonomies: three separate modal dialogs, one after another, each with its own title read out, where one small form would do. Escape on the second throws away the first.
- New Here (Ctrl+N), on Categories, Tags and plugin taxonomies: the parent is asked by number only. Anything that is not a number is silently ignored and the category is made at the top level.
- Properties (Alt+Enter), a term: Parent number is shown on tags too, with help that says "Categories only." A field that cannot apply should not be there.

##### Comments

- Approve, or Not Spam: "Not spam: 1 item on {site}, and the site was told." does not say the comment is now waiting, not published. A listener who pressed Approve on a spam comment reasonably believes it is now visible. It needs a second Ctrl+Shift+A, and nothing says so. Either approve it, or say "back in Waiting; Ctrl+Shift+A again approves it".
- Approve, or Not Spam: the noun is "item", not "comment", in every moderation sentence ("1 item approved"). It is shared with form entries, but in the Comments list it is the wrong word.
- Approve, or Not Spam: a mixed selection of spam and held comments gets the plain "approved" sentence, although the spam ones went back to Waiting instead.
- Not Spam, and Allow This Sender: the name promises an allow list that does not exist. The command is "Approve" plus an explanation of WordPress's own rule, and on a site that holds every comment the closing sentence admits the sender is not allowed at all. "Approve and Explain" would be honest; or it should be greyed on such sites.
- Not Spam, and Allow This Sender: reading the discussion settings needs manage_options. For an Editor the read fails, the empty settings fall back to the first sentence, and an Editor is told the sender's next comments get through whether or not that is true on this site.
- Not Spam, and Allow This Sender: unlike Approve, it is not recorded, so the two moderation commands next to each other have different undo stories.
- Unapprove: the sentence says "unapproved" while the list and status cell say "Waiting". "Back to Waiting" would match what the listener then hears in the list.
- Reply...: a reply is public the moment OK is pressed, and nothing can take it back from here. A multi-line box where Enter does not submit is safe, but there is no preview and no undo for a public post. At least record it, with Ctrl+Z moving the reply to the Trash.
- Reply...: needing moderate_comments means an Author cannot reply to comments on their own posts from the Workbench, although WordPress lets them.
- Reply...: Approve and Reply (wp-admin's one action) is two commands here: Ctrl+Shift+A, then Ctrl+Shift+M. The audit table says so, but nothing in the Reply dialog notes that replying to a waiting comment leaves it waiting.
- Move to Trash, Restore from Trash, Delete Permanently (comments): the Restore row's help says "Out of the Trash, as a draft.", which is wrong for a comment; comments come back Waiting.
- Move to Trash, Restore from Trash, Delete Permanently (comments): Move to Trash, the action Delete performs and the F1 for the node names, is under More on the comment menu, while Read in Full takes the top.
- Empty Spam...: critical. Empty Spam is not a row action, so the Workbench's access check never sees it. Read Only access, Safe Mode, and View As Role, whose own sentence says "Nothing can be changed until you stop", all let Ctrl+Alt+E permanently delete every spam comment after one Yes.
- Empty Spam...: "Delete all 1 comments held as spam" for a single comment; Empty Comment Trash gets the singular right.
- Empty Spam...: an Editor without the right role hears the confirmation, says yes, and then hears "Deleted 0 spam comments on {site}. 37 could not be deleted." with no reason. A refusal before the question would be kinder.
- Empty Comment Trash...: the same critical access gap as Empty Spam.
- Empty Comment Trash...: the two Empty commands sit on the Site menu with access letters M and E, next to each other, and both are destructive. Empty Trash for posts is on the row menu instead. Three "empty" commands live in two places.
- Comment Counts: "1 are yours" for one comment.
- Comment Counts: the sentence is long and fixed in order. "4 waiting" is what a moderator wants first, and it is first, which is good; "which is waiting and approved together" is an explanation that belongs in F1 after the first hearing.
- Properties (Alt+Enter), a comment: the Status choice offers "hold", WordPress's internal word, where the list says "Waiting".
- Properties (Alt+Enter), a comment: the sheet's title is built from the row's title, which for a comment is "Comment by {author} on {post}", so the reader hears "Comment by Ann on Hello World Properties - Community Radio". It is long and runs two names together.

##### People

- The tree nodes and what the list shows: F1 on Users says "Site > Roles explains each role", but the Site menu's row is "Roles and What They May Do" (Ctrl+Alt+R).
- The user row's context menu: the three Paid Memberships Pro rows are offered and enabled on every site, including sites without the plugin, and they hold three of the six top places. Remove, Set New Password and Send Password Reset, which every WordPress site has, are pushed under More. Membership rows should appear only where Paid Memberships Pro answers, or go last.
- The user row's context menu: "Invite from a Spreadsheet" adds new people to the site; it is not about the selected person, yet it sits on the person's row.
- Show Their Posts: only Posts. Their pages and content-type items are not shown, and nothing says so.
- Change Role...: one person gets a preview window that lists what they gain and lose, and Enter confirms. Several people get a message box with no gains or losses, and Enter cancels. The bigger change gets the smaller preview and the opposite default.
- Change Role...: a person with a role the site defines itself (a shop manager, say) opens the list on Subscriber, because only the five default roles are offered. One Enter and one more Enter in the preview demotes them. Custom roles should be listed, or the list should start on nothing.
- Change Role...: the role can also be changed on the Properties sheet's Role page. The same guards apply there, but no gains-and-losses preview does.
- Their Application Passwords...: in a list whose purpose is reading, OK means "revoke". Cancel is the only way to just read. A listener who presses Enter to choose a password to hear about gets a revoke question.
- Their Application Passwords...: the row is tier 0 (reading), but it leads to a permanent revoke. Read Only Workbench access, Safe Mode and View As Role therefore do not stop the revoke.
- Sign Out Everywhere...: a hand-off to wp-admin with a trailing ellipsis in the label, though no dialog follows.
- Send Password Reset: the label says it sends a reset; it opens a web page. It has a chord, unlike the other hand-offs, so a listener pressing Ctrl+Shift+W in a hurry leaves QUILL.
- Send Password Reset: two other texts promise more than it does. The Add a Person note says "Send Password Reset on their row opens wp-admin" (correct), but the Invite note says "Send Password Reset on their row sends them the link to choose their own" (not true).
- Send Password Reset: the refusal sentence "Doing this (edit users)" is the fallback for a capability missing from the plain-words table. edit_users needs an entry, such as "Changing other people's accounts".
- Set New Password...: a password the check rejects closes the box first. A listener who typed their own password hears the problem and must start again from the menu, with the generated one back in the box. The check should keep the box open.
- Set New Password...: the help says "previewed", but it is a confirmation message box. The password is never shown again in it.
- Set New Password...: being recorded with no undo, it blocks Ctrl+Z for everything done before it in the session.
- Remove...: critical. Delete and Shift+Delete on a user row run Move to Trash and Delete Permanently, which hand over to Remove. The Workbench checks a command against the row's own menu rows, and the user row has no Trash or Delete Permanently row, so neither the tier 3 access check nor the delete_users check runs. With Read Only access, Safe Mode or View As Role, Delete on a person still opens Remove, and Yes still removes them.
- Remove...: the "Give their posts to" list includes Subscribers, who cannot edit what they are given. wp-admin offers everyone too, but a hint ("Subscriber") beside each name would help.
- Remove...: the one-person confirmation does not name the site, unlike the several-people one.
- Properties (Alt+Enter), a person: Language wants a code such as en_US typed by hand. wp-admin offers a list of installed languages.
- New Here (Ctrl+N) in Users: Add a Person: the most important fact, that no email goes and the person cannot sign in until someone sends a reset, is in the help of the second tab and in the confirmation. It is not visible on the first tab, where the listener fills everything in.
- New Here (Ctrl+N) in Users: Add a Person: an account just added is easy to remove, but Ctrl+Z will not, and its entry blocks every earlier undo.
- Application Passwords: New Here (Ctrl+N): Copy All copies the name and the instruction too, not just the secret. A listener pasting it into another app's password field pastes three lines. A "Copy Password" button that copies only the secret would fix it.
- Application Passwords: Revoke...: critical. Shift+Delete on an application password row runs the generic Delete Permanently, which has no case for application passwords. It asks "Delete 1 item from {site} permanently? This cannot be undone: {name}." and then deletes the password's route. It skips the guard above, so Shift+Delete on the row marked "QUILL on this computer signs in with it" revokes the password the Workbench is using and locks it out mid-session.
- Application Passwords: Revoke...: Delete reaches Revoke without the tier 3 access check, for the same reason as Remove on a person: the row has no Trash row for the check to find.

##### Menus

- The Menus and Navigation node: The items column is always empty: load_menus fills `"items": ""` for every row. A listener hears a column header with nothing under it on every row.
- The Menus and Navigation node: The locations column shows WordPress's location slugs exactly as `wp/v2/menus` sends them (for example `primary`), not the theme's names for them ("Primary Menu"). Not translated anywhere I could find.
- The Menus and Navigation node: The list reads `wp/v2/menus`, which is classic menus only. A block theme's Navigation menus (`wp_navigation` posts) do not appear in this node at all. The only trace of them is the Default Navigation Menu command, which names one by number.
- The Menus and Navigation node: There is no way to see a menu's items in the Workbench itself: no child node per menu, no items in the detail, nothing in Properties. The only way is Arrange Items, which leaves the Workbench for another window.
- The Menus and Navigation node: Rename an item, move it up, down, in or out, and remove it: not in the Workbench's own rows. The editor's Menus window (wordpress_menu_commands.py) has Rename, Move Up, Move Down, Move In, Move Out, Remove, Check Menu and Locations; `cmd_menus` returns early through `workbench_door("wordpress.menus")` (and `open_from_door` always returns True), so from the editor's Tools menu that window is gone, and it is now reached only through Arrange Items or the editor's add-this-page-to-a-menu path.
- The Menus and Navigation node: No Go key for Menus, although it is one of the places people visit most in wp-admin after Posts and Pages.
- Read in Full (menu row, default): The default action of a menu reads one short sentence that the list row already said. For a menu, Enter is the one key people press expecting to go inside; here it goes to a pane that cannot show the items.
- Add Menu Item...: Up to six dialogs in a row for one item (kind, search, pick, under, position, preview). Each is correct, but there is no single "Add Menu Item" dialog where the kind, the item and the place can be reviewed together and changed before the preview. A wrong choice at step five means Cancel and start again.
- Add Menu Item...: View All reads at most 100 items (`LIMIT = 100`, one page) and never says it stopped. On a site with 300 pages, page 101 onward is silently missing from View All; only Search finds it.
- Add Menu Item...: Search results that share a title (two pages both called "Contact") are indistinguishable in the list: rows are titles only, with no parent, date or address.
- Add Menu Item...: Custom Links sits in the middle of the kinds list (after the post types, before Categories). wp-admin's panel order is the reason, but in a list box a listener has to arrow past every custom post type to find it.
- Add Menu Item...: The "Where" step is skipped entirely for an empty menu and the position step for an empty level, which is good, but the preview then says `Where: at the top level, first, 1 of 1.` with no hint that the Under question was skipped.
- Add Menu Item...: Ctrl+N with a menu selected bypasses the context menu's permission check: `run` checks `new_here` (which needs nothing), then calls `do_add_menu_item` directly. An Editor walks all six dialogs and only fails when the site refuses the write. Not tested on a live site; read from wordpress_workbench_lists.py and wordpress_workbench_window.py.
- Add New Pages Automatically...: The summary is built from the check box label lowercased, so it reads "Turn On automatically add new top-level pages to this menu for Main on Radio?", which is ungrammatical spoken English. Something like "Turn on adding new top-level pages to Main?" would read better.
- Add New Pages Automatically...: The command is a toggle with no indication of the current state in its label. You learn the state only from the preview's Now line. That is acceptable because the preview always comes first, but the context-menu label could say "Turn On..." or "Turn Off...".
- Add New Pages Automatically...: Two routes to one setting: this command (previewed, re-read before and after) and the Properties check box (a sheet save: conflict check, no preview, undone by Ctrl+Z as `Put {menu number} back as it was.`). Same result, two different confirmation styles.
- Arrange Items...: It restores the missing jobs, but as a different window with different rules: no previews, no Ctrl+Z, its own Add buttons that duplicate Add Menu Item with fewer choices (end only). A person learns two ways to add to a menu that behave differently.
- Arrange Items...: The label says "Arrange" but the window also renames, removes, adds and sets locations; "Edit Items..." or "Open in the Menus Window..." would set the right expectation.
- Arrange Items...: When the window closes, the Workbench list is not known to refresh (not verified).
- Earlier Versions... (menu): It only brings back removed items, and puts them at the end of the menu at the top level, not where they were. A restored submenu comes back flattened. The preview does say "at its end", but not "at the top level".
- Earlier Versions... (menu): It cannot undo a rename or a move, only a removal, although the label "Earlier Versions" suggests a full restore.
- Earlier Versions... (menu): History starts only the first time QUILL reads the menu, and only on this computer. The first use always says there are no versions, which teaches the user the command does nothing.
- Earlier Versions... (menu): If the version lost nothing the brought-back count can never be zero here, but between the preview and the write another person could restore items, and the announcement would then say "Brought back 0 items" (the work re-checks what is missing). Minor.
- Default Navigation Menu...: It sits on a classic menu's row but answers a question about block Navigation menus, which this node does not list. A person on a classic theme gets a question that does not apply to them.
- Default Navigation Menu...: The answer speaks the menu's number (`Navigation menu 1234`), which means nothing to a listener and cannot be used anywhere in the Workbench.
- Default Navigation Menu...: The tier is Read, but it can create a menu on the site. The confirmation is honest about that; the history is not (no entry, no undo).
- Copy to Site... (menu): "Copied 3 from Radio to Studio." is missing its noun.
- Copy to Site... (menu): For a menu, the copy replaces the target menu's links (workbench_site_copy.py says "its links there are replaced"). That is a destructive change on the target with no undo; check that the preview says it plainly.
- Properties (menu): The sheet title, the saved sentence and the undo sentence all name the menu by its number, not its name: WbRow.title looks for a title, name, what, plugin, theme, setting, form or site cell, and a menu row's name is in a `menu` cell, so the title falls back to the row key (the menu id). The menu commands work around it with their own `_named()`, the sheet does not.
- Properties (menu): This is the only place to rename a menu, and Shown in is read only: choosing which theme location shows a menu is only in the Menus window's Locations... (through Arrange Items).
- Properties (menu): Shown in lists location slugs, as in the list.
- New Here on Menus (Ctrl+N): A new menu is made with no preview and no undo, unlike every other write in this node. Worse, because it is not in Change History, Ctrl+Z right after it silently undoes the previous, unrelated change.
- New Here on Menus (Ctrl+N): File > New Here's own help still says "A new user or password, where you are.", which is out of date in every node.
- New Here on Menus (Ctrl+N): Delete a menu: not found in the Workbench.

##### Widgets

- The Widgets and Sidebars node: The id-for-name problem above is the first thing to fix: every widget sentence names an area the way only a theme developer would.
- The Widgets and Sidebars node: The detail says `{n} widgets.` and nothing about what they are. To hear the widgets you must run Preview Widgets, which opens a report.
- The Widgets and Sidebars node: "1 widgets" is said for an area with one widget (no singular form in load_sidebars).
- The Widgets and Sidebars node: On a block theme this node is normally empty or shows only WordPress's inactive area; nothing says "your theme uses the Site Editor instead; see Templates and Template Parts".
- Add a Widget...: The help says Block "holds any block, as text", but Add makes only a paragraph block from plain words (`paragraph_block(text)`). You cannot add a heading, a list or a Latest Posts block from here; only Change edits a block widget's markup.
- Add a Widget...: The widget is always added at the end of the area. There is no position choice, unlike Add Menu Item.
- Add a Widget...: "Visitors see:" is WordPress's rendering turned into words, which is the right idea; for a widget that renders nothing until configured, "(nothing yet)" is clear.
- Change a Widget...: A legacy widget whose form has no fields returns no answers, and the command then stops without a word (`if not data: return`). The person hears nothing and does not know why.
- Change a Widget...: Unchanged block markup also stops silently, while Edit Block Markup for templates says `{title} is unchanged, so nothing was sent.` Inconsistent.
- Move a Widget...: The only widget write with no preview. Moving a widget changes every page that shows either area, the same reach Add's preview warns about.
- Move a Widget...: The undo puts it back at the end of the original area, not in its old position.
- Move a Widget...: Moving within an area (reordering) is not offered.
- Remove a Widget...: Good: honest about where it goes and how to undo it.
- Remove a Widget...: The confirmation is a message box, while Add and Change use the preview window; a listener meets two confirmation styles for one family of commands.
- Preview Widgets: The keyless reason calls it "Read Widgets"; the menu calls it "Preview Widgets". The written reason names a command that does not exist.
- Preview Widgets: This is the only way to hear the widgets at all; it would serve better as the area's default (Enter) than Read in Full.
- Properties (widget area): Labels are WordPress's developer descriptions (for example the route's description of before_widget HTML), not words a site owner uses. Not verified on a live site which fields end up editable.
- wp-admin for This Place (Widgets and Sidebars): It tells you the Workbench does all of it, then opens wp-admin anyway. When the map says `workbench`, the sentence could ask first or explain what wp-admin adds (drag-and-drop, the Customizer's live preview).

##### Appearance and the Site Editor

- The Appearance folder and its Go key: F1 for Appearance does not mention Global Styles, Template Parts or Additional CSS, which are three of its eight children.
- The Appearance folder and its Go key: Go > Appearance landing on Themes means the key never shows you the folder; the help "Themes, templates, patterns." suggests otherwise. For an Editor (who cannot list themes) Ctrl+Shift+7 lands on a node that only says they lack the role.
- The Themes node: The refusal says "Changing the theme" when the person only tried to look. An Editor cannot even read which theme is active from the Workbench, although that is harmless information (At a Glance does name the theme).
- Properties (theme): No "Requires WordPress", "Requires PHP", "Tested up to", screenshot description or tags, all of which `wp/v2/themes` sends; a person choosing between themes has only the description.
- The Global Styles node: F1 promises spacing; the node lists colours and font sizes only. Font families, spacing, element styles (links, headings, buttons) and block styles are not listed.
- The Global Styles node: The contrast column is good and rare. It measures against the page background and text colour only; a colour used as a button background against white text is not judged.
- Change... (global style): F1 says "Change... previews the new value", but this is a plain message box, not the preview window every other Site Editor write uses, and Cancel is its default button. Inconsistent with Edit Additional CSS and Edit Block Markup.
- Change... (global style): The module's own comment says "Enter on a Global Styles row changes that colour or font size"; Enter actually reads (Read in Full is the default).
- Change... (global style): Colours are typed as hex or rgb. Named colours, and choosing from the theme's own palette, are not offered. A listener has no way to hear a colour except as a code plus a nearest-colour name.
- Change... (global style): The confirmation repeats the old and new values and then a contrast sentence that repeats the new value again; long for a message box.
- Properties (global style): Alt+Enter cannot change the value although Properties is where values change in most lists, and nothing on the sheet points to Change....
- The Templates and Template Parts nodes: New Template is only on a row's context menu. On an empty Templates list (a classic theme, or a fresh one) there is no row, so there is no way to make the first template; Ctrl+N (New Here) on Templates says `New Here makes posts, pages, custom items, categories, tags, terms, menus, people and application passwords. Choose one of those nodes first.`
- The Templates and Template Parts nodes: A template part's area (header, footer, general) is not a column, though it is what tells parts apart.
- Edit Block Markup...: Editing a whole template as raw block comments in a plain text box is honest and complete, but heavy: a header part is often hundreds of lines of nested comments. The editor's own block tools are not offered here (no "Open in Editor" for a template).
- Edit Block Markup...: The conflict message says "read it again and make the change there" but does not offer to reload; your edit is lost.
- Earlier Versions... (template): A template still from the theme always says it has no earlier versions, without saying why (only customized copies have revisions).
- Earlier Versions... (template): Rows are dates only; no author, no size of change.
- Reset to the Theme's Version...: The row's help says "Confirmed by name", but the confirmation is the ordinary preview with a Reset or Delete button; nothing is typed.
- New Template...: For a template part the help still says it starts from the template WordPress would use, but the code never looks one up for a part: it always starts empty.
- New Template...: A part is made with no area (header, footer), so it lands in General; not offered.
- New Template...: The preview title capitalises only the first word: "New Template part".
- Open in the Site Editor: Fine as a hand-off. The Site Editor is one of the least accessible screens in wp-admin, so its help could say what it is for ("to lay it out by sight") as the row help does.
- Properties (template): Field labels are developer descriptions (for example the schema's sentence describing the slug), and a 60-character cut can end mid-word.
- Properties (template): Not verified whether the content field is editable here; if it is, it is a second route to change a template that skips Edit Block Markup's line-by-line preview.
- The Additional CSS node: The column header "reach" holds a line count on a block theme. A listener hears "reach, 12 lines of Additional CSS".
- The Additional CSS node: On a classic theme, Enter announces only ` Opening Appearance > Customize > Additional CSS on {site} in your browser.`: the row's raw data has no `why`, so the reason sentence before "Opening" is empty.
- The Additional CSS node: On a classic theme, Go to Its Place in the Workbench selects Additional CSS, the node you are already in.
- Edit Additional CSS...: Good brace and markup checks before the preview, said in one sentence.
- Edit Additional CSS...: "Kept in Previous Looks" points at a feature the Workbench does not have; Previous Looks is only in the editor (Tools > WordPress > Manage > Previous Looks...).
- Edit Additional CSS...: A failed check throws the typed text away; the person has to retype the whole edit.
- The Patterns node: `wp/v2/blocks` returns unsynced patterns too, but every row says "a synced pattern" (not verified on a live site whether unsynced ones are filtered).
- The Patterns node: No way to edit a pattern's blocks, rename it, make one or delete one from its row. The editor's old Synced Patterns window had Edit (a "Blocks:" text box and a "Save Synced Pattern" confirmation), but its door now opens this node instead. Regression unless the schema sheet covers it (not verified).
- The Patterns node: Pattern categories: not found.
- The Patterns node: Row help "A synced pattern." is the shortest F1 in the Workbench and says nothing about what can be done.
- The Fonts node: Install a font and delete a font: not found in the Workbench. The editor's old Fonts window (wordpress_design_commands.py) offers both (`Install {name}`, `Delete {name}`), but its door now opens this read-only list. Regression.
- The Fonts node: No font faces (weights and styles) are listed; the Properties sheet shows the raw family settings.
- Style variations and Previous Looks: Three Workbench help strings say "kept in Previous Looks", but there is no Previous Looks node or command in the Workbench. Either add the node (Appearance > Previous Looks, listing global-styles revisions) or say "in the editor's Tools > WordPress > Manage > Previous Looks".
- Style variations and Previous Looks: Switching a block theme's style variation, one of the most common appearance jobs, has no place in the Appearance branch.
- wp-admin for This Place (Appearance nodes): Template Parts finds nothing, while Templates finds the Site Editor: the lookup falls back from `template_parts` to `template`, which is not a node key.
- wp-admin for This Place (Appearance nodes): Customize is mapped to Themes, not to the Appearance folder, so on a classic theme the Customizer is two levels away from where people expect it.

##### Plugins and themes

- The Plugins node: Every row's detail ends with "Updates and automatic updates are in wp-admin: Open in Dashboard." The same sentence on every one of forty plugins is exactly the chattiness GATE-13 warns about; say it once in the node's F1 or the status bar.
- The Plugins node: Delete a plugin: not found as a row action, although `wp/v2/plugins` can delete (the map's Plugins row says "Activate, deactivate, install and delete are in Plugins").
- The Plugins node: The refusal for an Editor talks about turning plugins on and off when they only opened the list.
- Activate or Deactivate: The label "Activate or Deactivate" does not say which it will do for this row. A listener must read the status column first or wait for the message box. Label it from the row's status ("Deactivate..." on an active plugin), and add the ellipsis since it asks.
- Activate or Deactivate: The plugin's Properties sheet has an editable Status choice (active, inactive). Saving it goes through the generic sheet save, which has no preview and never calls `deactivate_refusal` or `deactivate_warning`. So Alt+Enter, Status, inactive, OK can turn off the Application Passwords plugin that the context menu refuses to touch, locking the Workbench out. Read from wordpress_workbench_sheets.py and workbench_sheets.py; not tried live. This is the most serious finding in this section.
- Activate or Deactivate: "{plugin} put back." does not say which state it went back to.
- Activate or Deactivate: Network-active plugins on a multisite: deactivating sends `inactive` from a single site's route; not verified what WordPress does.
- Check on WordPress.org...: The row command checks every plugin on the site, not the row it was chosen on; the label reads as if it is about this plugin.
- Check on WordPress.org...: Consent is asked once per window per kind of question (plugins, themes, updates, languages): four separate "Ask WordPress.org" boxes for one source. Reasonable for privacy, but the person may agree four times in one session and is never told the agreement lasts only until the window closes.
- Find a Plugin on WordPress.org...: The consent question comes after you have typed the search, so declining wastes the typing; Check on WordPress.org asks first.
- Find a Plugin on WordPress.org...: The install is not in Change History. Ctrl+Z right after it undoes the change before it, silently. Either record it with an undo (delete the inactive plugin) or record it as "cannot be undone".
- Find a Plugin on WordPress.org...: After installing, the plugin is inactive and the next step (Activate) is not offered; the person must find the new row and use Activate or Deactivate.
- Find a Plugin on WordPress.org...: "installed on 1 of 1 sites" is the multi-site sentence reused for one site.
- Find a Plugin on WordPress.org...: The refusal sentence reads "Doing this (install plugins)", the only place a raw capability name is spoken.
- Find a Plugin on WordPress.org...: The command needs a plugin row to be selected; on a site with no plugins listed there is no row, so no way to find the first plugin.
- Open in Dashboard (plugin): The row help shared with themes says "for a theme, activating and installing", on a plugin row.
- Open in Dashboard (plugin): It opens the whole Plugins screen, not this plugin; the person has to find the plugin again in wp-admin's table.
- Open in Dashboard (plugin): After an update waiting is found, the detail says "Dashboard > Updates runs it", but Open in Dashboard on a plugin row goes to Plugins, not Dashboard > Updates.
- Check for Updates on WordPress.org... ("update waiting"): This is the cheapest real win wp_missing.md asked for, and it is here. But it checks one site per run. On Needs My Attention > Updates, which gathers every site, you must run it once per site (choosing a row of each), and the marks last only until the window closes. There is no "check every site" and no Watch that uses it.
- Check for Updates on WordPress.org... ("update waiting"): The Watch "Plugin updates available" (workbench_watches.py) still looks only for an update field the site itself sends, which core WordPress never sends, so the Watch stays silent even after this check finds updates.
- Check for Updates on WordPress.org... ("update waiting"): A plugin WordPress.org has closed is marked `Unknown: not on WordPress.org` (latest_plugins returns None for a closed plugin). A closed plugin is a security warning, not an unknown; Check on WordPress.org says "closed", this check hides it.
- Check for Updates on WordPress.org... ("update waiting"): Each row's detail keeps the earlier sentence too, so an Updates row can say "REST does not say whether an update waits." and then "so an update waits." in one detail.
- Check for Updates on WordPress.org... ("update waiting"): The command is on every plugin row, but it checks all of the site's plugins and themes and WordPress; the label suggests it is about the row.
- Check for Updates on WordPress.org... ("update waiting"): Up to 100 theme lookups, one request a theme; plugins one request each. On a site with many plugins this is slow, with no progress said beyond the background task name.
- Properties (plugin): See Activate or Deactivate: the Status choice skips the lockout refusal, the QUILL-relies-on warning and the confirmation.
- Properties (plugin): No "update waiting", WordPress.org facts, "Needs PHP" or "Network only" on the sheet, though the row's detail and `wp/v2/plugins` carry them.
- Theme rows: Activate...: The label has an ellipsis but opens no dialog; it opens the browser.
- Theme rows: Activate...: The spoken reason starts with "it cannot activate" immediately after you asked to activate, which sounds like a failure. Lead with the hand-off: "Activating happens in wp-admin; opening Appearance > Themes ...".
- Theme rows: Activate...: Nothing comes back: the Workbench does not notice the switch until a later read, when (up to five minutes later, on the next request) it announces `{site} changed since QUILL last looked: the theme is now {stylesheet and version}...` out of context.
- Theme rows: Find a Theme on WordPress.org...: Prefilling the search with the theme you already have makes the first search find that theme. An empty box would be the better start.
- Theme rows: Find a Theme on WordPress.org...: The search, the consent and the list all happen in QUILL, then the job is finished in wp-admin's theme browser, which is visual and searches again. The hand-off is honest but it is a dead end for a screen-reader user who wanted QUILL to install it.
- Theme rows: Find a Theme on WordPress.org...: No requirement is checked, although installing a theme needs `install_themes`.
- Theme rows: Open in Dashboard and Check for Updates: Activate... and Open in Dashboard open the same screen with the same sentence (Activate adds `?theme=`); two rows, one job.
- Theme rows: Open in Dashboard and Check for Updates: Delete a theme, update a theme, theme auto-updates: wp-admin only, said in the row; no Workbench path.
- wp-admin map rows for plugins: The WooCommerce Settings row now says Store Settings changes settings, which fixes the stale line wp_missing.md flagged.
- wp-admin map rows for plugins: Only seven plugins are mapped. Every other installed plugin's settings screen (a cache plugin, a security plugin, an SEO plugin other than Yoast) is not reachable through wp-admin for This Place on Plugins. A plugin row has no "Open Its Settings" action. Not found in code.
- wp-admin map rows for plugins: "wp-admin for This Place" is on the tree's node menu, under More, fourth of four. On the Plugins list you must move to the tree, open its context menu, open More, and find it. It is not on the plugin row's own menu.
- wp-admin map rows for plugins: "All of it in the Workbench" for Add New Plugin is generous: wp-admin's screen also uploads a plugin zip, which the Workbench cannot.

##### Settings

- The Settings node: The explanations are excellent and should be the model for other lists.
- The Settings node: The refusal says "Changing" to someone who only opened the list. An Editor cannot even read the site's time zone or date format here.
- The Settings node: Missing from the list because REST does not carry them (said only in the wp-admin map rows): who may register, the default role, the WordPress and site addresses, permalinks, search engine visibility, the privacy policy page, media sizes, discussion's moderation settings.
- The Settings node: The Site icon reads `picture {number}`; the picture's title is not looked up, unlike the front and posts pages.
- Read in Full (setting, default): Row help says "Alt+Enter changes it", which is right, but Enter is what people press to change a value in a list; a setting's Enter could open the change directly.
- Properties: Change a Setting: The Value box holds the raw stored value, not the friendly one the list shows: `posts` or `page` for Front page shows, a page number for Front page and Posts page, `0` to `6` for First day of the week, `open` or `closed`, an empty string for the standard post format, and the raw on/off for emoticons. The list knows the words (CHOICES) but the sheet offers no choice list, no page picker and no check box. A listener has to know WordPress's internal values to change most of these.
- Properties: Change a Setting: The value is sent as typed text, without converting it to a number or a true/false (workbench_edit.py puts the string straight into the body). Whether WordPress accepts "6" for start_of_week or "false" for use_smilies was not checked live.
- Properties: Change a Setting: The preview shows raw values too: "Front page (page_on_front): 12 becomes 34" tells a listener nothing about which pages those are.
- Properties: Change a Setting: The site-address and default-role guards can never fire from this list, because neither setting is in SETTINGS_FIELDS. Harmless, but the protection is in code nobody reaches here.
- Properties: Change a Setting: One setting per sheet: there is no batch sheet for settings, so changing title and tagline is two round trips.
- Language Pack Status...: It is on one site's setting rows but reports on every connected site. The label and placement suggest this site.
- Language Pack Status...: Installing a missing pack is wp-admin only (`WordPress's REST API cannot install or update a language pack.`), but the report has no "open Settings > General" action.
- wp-admin for This Place (Settings): Settings > Media and Settings > Discussion are mapped to Media and Comments, so they do not appear here, where a person who knows wp-admin's Settings menu looks for them.
- wp-admin for This Place (Settings): The reason sentences are long, and every one is spoken before the browser opens.

##### Tools

- Where wp-admin's Tools screens land: The Import and Export rows are stale. The Workbench's own Tools menu now has WXR Files > Export Site as WXR... and Import WXR as Drafts... (engineering log, 2026-11-14), yet the map still says "The WXR export is not in REST; Download My Writing, in the editor, saves posts." and marks both "Only in wp-admin". A person following the map is sent to the browser for something QUILL now does.
- Where wp-admin's Tools screens land: Tools > Available Tools maps to More from This Site, a list of REST namespaces; nothing there relates to the categories and tags converter. The Workbench does have Convert to Category or Tag... (Ctrl+Shift+K) on a term row, which the map does not mention.
- Where wp-admin's Tools screens land: With no Tools node, a person who knows wp-admin ("Tools > Site Health") has to know that Site Health is directly under the site, and that privacy is under Privacy Requests. The wp-admin Screens list is the only bridge, and it is under Overview, not where Tools would be.
- The wp-admin Screens node: A row's spoken detail is long: name, raw path, reach, reason, place, instruction. The path (`wp-admin/options-general.php`) is the least useful part for a listener and comes second.
- The wp-admin Screens node: There is no filter by reach, so finding "what can I only do in wp-admin" means Filter Builder or Show Only on the reach cell.
- Open in Dashboard (wp-admin Screens row, default): For a screen marked "All of it in the Workbench", Enter still leaves for the browser, after saying the Workbench does it all. The default for those rows could be Go to Its Place.
- Go to Its Place in the Workbench: Nothing is announced on success beyond what the tree says on focus, which is right by GATE-13.
- Go to Its Place in the Workbench: The failure sentence names the row by its internal key (for example `plugin_install has no place ...`): a wp-admin Screens row has no title-like cell, so its title falls back to its key.
- Properties (wp-admin Screens row): Not useful: everything here is already in the detail, and Node is an internal name. The engine requires Properties last on every menu, so it cannot be removed, but it could show the screen, path, reach and reason with proper labels.
- wp-admin for This Place...: Buried: fourth of four under More, on the tree's menu only. A row's own menu never has it. For the job it exists for (the thing REST cannot do here), it should be one level up.
- wp-admin for This Place...: The keyless reason says "only for what REST cannot do", but it also opens screens the map marks "All of it in the Workbench" (Menus, Widgets, Posts), with no question first.
- wp-admin for This Place...: "Empty Trash..." and "Counts by Status" sit beside it on every node's menu, including Menus, Settings and Site Health, where they mean nothing.
- Open This wp-admin Screen (privacy): Honest and complete for what REST allows. It is a pure hand-off: the node lists two fixed rows, not the requests, so it cannot tell you whether any request is waiting, which is the one thing a site owner needs from it (a legal deadline applies to these).
- Open This wp-admin Screen (privacy): When a plugin route exists the rows become plain problem rows (Read in Full and Properties only) that name the route, with no way to open or act on the requests.
- Go There (administration area): The browser case speaks the whole address (`Opened {full address} in your browser.`, the row's link, which for most areas ends in `wp-admin/plugins.php?plugin_status=active`). Every other hand-off says the screen's name.
- Go There (administration area): For Backups, Security, Caching and most others the "screen" is the Plugins list filtered to active, not the plugin's own screen, so Go There lands on a generic list.
- Go There (administration area): This list is the closest thing to a Tools node, and it is good orientation, but it is a flat list of 20-odd areas with long boundary sentences read in full.
- Import and export: Fix the map rows so wp-admin for This Place on Posts and the wp-admin Screens list point at WXR Files instead of sending people to wp-admin.
- Run... (ability row, default): The menu cannot show in advance whether a given ability will change the site; the tier is only decided when it runs, so a Read Only window hears the refusal after choosing Run.
- Run... (ability row, default): The cancel path is silent, unlike most Workbench previews.
- Offer to Ask the Site (ability row): Before this row existed (added 2026-11-14, coordinator report), the AI Abilities door sent people to the Workbench, where nothing could turn an ability on, so Ask the Site's refusal "Turn them on one by one in Abilities" was a dead end. It is now reachable, but only from the context menu.
- Offer to Ask the Site (ability row): The label is a toggle that does not say its current state; the list has no column showing which abilities are offered. A person must remember, or run it and listen to the outcome to find out (which flips it).
- Offer to Ask the Site (ability row): Consider "Offered to Ask the Site" as a column, or the label changing to "Stop Offering to Ask the Site" when on.

##### Site Health and maintenance

- The Site Health node: The test column is the first sentence of the line and the says column is the whole line, so every row reads its first sentence twice.
- The Site Health node: Good rows say "A problem a check found." on F1, even for `HTTPS: the site's address uses HTTPS.`
- The Site Health node: Every test runs each time the node loads (each test is its own request; the loopback test waits on the site), with no cache; opening Site Health is slow on a slow host. Not measured.
- The Site Health node: "Search engine visibility: WordPress does not share this over its API" contradicts Search and Upkeep, which does judge it (from the sitemap) and says where its answer comes from. Two answers to one question in one tree.
- The Site Health node: Nothing to do on a problem row: no "Open in Dashboard" to the test's own screen, no "how to fix" link, although WordPress's test answers carry an actions link. The only hand-off is through the node's wp-admin for This Place (Tools > Site Health > Status, marked "All of it in the Workbench").
- Read in Full and Properties (Site Health row): Test and Problem hold the same text; Says repeats it. Five fields, two facts.
- Information (Site Health > Information): Open in Dashboard on that row opens the browser silently: it runs the generic open-on-site command, which speaks nothing, while Open in Dashboard on a plugin or theme row says its reason first. (The reason is in the row's detail, already heard.)
- Information (Site Health > Information): The directory sizes are the Workbench's only "space used" view; the editor's Tools > WordPress > Manage > Space Used is separate. WordPress computes these sizes on request, so this node can be the slowest in the tree; nothing warns.
- Security (Site Health > Security): Clear and careful. The name "Security" promises more than one check; the Administration Areas row for security plugins is where the rest is said, and nothing here links to it.
- Needs My Attention > Site Health: It runs every site's full Site Health (every test on every site) to keep a few rows; on several sites this is slow.
- Needs My Attention > Site Health: "Worst first" holds within a site; across sites the gathered rows are not re-sorted by status (not verified on a live run).
- Needs My Attention > Updates: This is the least "needs my attention" list in Needs My Attention: it lists every plugin and theme on every site, waiting or not. Even after Check for Updates, the up-to-date rows stay. It should list only what waits (after the check) or be renamed Versions.
- Needs My Attention > Updates: Check for Updates runs per site, so with five sites the person runs it five times from rows of each site; the marks are lost when the window closes.
- Needs My Attention > Updates: Open Dashboard Updates in the Browser opens silently (the generic open-on-site command), while the detail already said it.
- Needs My Attention > Updates: The Properties sheet for a plugin or theme row is the raw REST payload (fields labelled from their keys, for example "Plugin uri", "Requires php", "Textdomain"); for the WordPress row, the four cells.
- Open Dashboard Updates in the Browser (Updates row, default): Updates are the one maintenance job a site owner must do, and here it is a pure hand-off to wp-admin's Updates screen, which is a long form of check boxes. Said honestly in every row; still a dead end.
- The Search and Upkeep node: Strong: every row says how it knows. The certificate warning inside 30 days is the kind of thing a site owner never sees until it is too late.
- The Search and Upkeep node: A missed schedule's detail says `Approve and Schedule on its row in Posts or Pages publishes it now.`, but that command is not on the upkeep row; you have to find the post again elsewhere.
- Open Where It Is Checked: On rows without their own link, "Open Where It Is Checked" opening the home page is a silent wrong answer.
- Open Where It Is Checked: Same command id as "Open on the Site" (Shift+Enter) elsewhere, under another label; Shift+Enter does the same here, which is not said.
- Move to Trash... (audit finding): Ctrl+Z does not undo it, although the item is only in the Trash and every other Trash move in the Workbench is undoable. Ctrl+Z here undoes the change before it.
- Move to Trash... (audit finding): Good that usage is shown in the preview itself, not only on request.
- Add Redirect..., Redirect This Address... and Change Redirect...: None of the three prompts has an access key (no `&` in "Old address...", "New address it leads to:", "Kind of redirect:", "Group to keep it in:"), unlike every other Workbench dialog.
- Add Redirect..., Redirect This Address... and Change Redirect...: A redirect write is not in Change History: Ctrl+Z after saving undoes something else.
- Add Redirect..., Redirect This Address... and Change Redirect...: "Kind: 301" in the preview drops the words the list used ("moved for good").
- Turn On or Off and Delete Redirect...: Delete Redirect's row help says "Gone for good, after you confirm by name", but it is an ordinary Yes/No box; nothing is typed, unlike Delete Permanently elsewhere.
- Turn On or Off and Delete Redirect...: "Turn On or Off" does not say which it will do.
- Test an Address...: Useful and safe. The help's "Nothing is sent" is true of the test; the first run does read every redirect from the site.
- Space used: wordpress.md marks Space Used in Site Check "in progress"; in the Workbench it is a set of Information rows, readable only by an administrator.

##### Snapshots and moving sites

- Take a Snapshot: Review note: the completion sentence is very long to hear. It reads out a full Windows path with a profile id, then the whole left-out list. A screen-reader user gets a 30-plus-word path read character-ish, and no way to act on it. Offer "Open the Snapshot Folder" or a report instead.
- Take a Snapshot: Review note: custom post types are not taken. Only `wp/v2/posts` and `wp/v2/pages` are read, so Events, Products, Podcast episodes and the rest are left out. So are templates, template parts, global styles, block-theme Navigation menus (`wp_navigation`) and form-plugin data. None of these appears in the left-out list, which names only "people, passwords, plugins, themes, revisions and comments". The person is told a snapshot is complete when it is not.
- Take a Snapshot: Review note: the menu help says "Everything but media, saved here." That is wrong both ways: media records are always saved, and much more than media is left out (see the note above).
- Take a Snapshot: Review note: "1 patterns", "1 media" and the like: the count words are never made singular.
- Take a Snapshot: Review note: there is no way to list, open, rename or delete snapshots from the Workbench. They pile up, with media files possibly large, in the data folder.
- Take a Snapshot: Review note: Ctrl+Alt+S (take a snapshot) is one modifier away from Ctrl+Alt+Shift+S (Put Back, which writes to the site) and from Ctrl+Shift+S (mark as Spam). Put Back is protected by a picker and a preview, so the risk is a startled moment rather than data loss. On keyboards where Ctrl+Alt is AltGr, these chords may also collide with typing in the filter box.
- Put Back from a Snapshot: Review note (critical): Put Back writes to the site with no Workbench Access, Safe Mode or View As Role check. A person who set a site to Read Only, or who is in Safe Mode, can still overwrite posts and pages from this menu.
- Put Back from a Snapshot: Review note (critical): it puts back far less than "set back to it" promises. For posts, pages and patterns only the title, content and excerpt are compared and sent; for terms, only the name and description. Status, slug, date, author, categories, tags, featured image, parent and menu order are never compared or restored. A post unpublished since the snapshot stays unpublished, and the preview does not say so.
- Put Back from a Snapshot: Review note (critical): an item deleted since the snapshot is "made again as a draft, at a new address" with only title, content and excerpt. Its categories, tags, featured image and parent are lost. A deleted category made again gets a new id, and no post is re-filed under it.
- Put Back from a Snapshot: Review note: items moved to the Trash since the snapshot are probably treated as deleted, because WordPress's `status=any` leaves out trashed items. Put Back then makes a duplicate draft while the original still sits in the Trash. A Restore from Trash would have been the right move. Worth checking on the live site.
- Put Back from a Snapshot: Review note: the chooser shows only a timestamp. There are no counts, no "with media files", no "taken on the practice site", and no way to read what a snapshot holds before choosing it.
- Put Back from a Snapshot: Review note: it is all or nothing. The preview is a read-only list, with no check boxes to put back only some items, unlike Split in By Name, which uses check boxes.
- Put Back from a Snapshot: Review note: the preview's default button is "Put Back", so Enter in the list sends the change. The confirmation dialogs elsewhere (crossing, Reset, Check Every Link) default to Cancel. Two different safety habits sit in the same window.
- Put Back from a Snapshot: Review note: the plan reads every post and page of the site (up to 1000 pages of 100) with no progress or count. A big site sits silent for a long time.
- Copy to Site: Review note: the success sentence says "new items are drafts there", even when every line was a Replace. A replaced published page goes live at once, and the spoken outcome hides that. Say how many were replaced live.
- Copy to Site: Review note: the permission check uses only the first selected row's kind. A mixed selection (a post plus a menu) is checked against post rights only.
- Copy to Site: Review note: "Connect a second site first: File > WordPress > Connect a Site." The Workbench's own File menu has no WordPress submenu. The path exists only in the editor, and unlike `_site_now`'s sentence this one does not say "in the editor".
- Copy to Site: Review note: there is no undo, and this is a write to another site. Ctrl+Z also cannot reach any earlier undoable change while this entry is newest, because `do_undo` only looks at the newest entry (see the Needs My Attention section's note on the undo stack).
- Copy to Site: Review note: the module docstring says custom terms travel; COPY_LEFT_OUT says "taxonomies other than categories and tags" do not. The preview is the one the person hears, so it is probably right, but the two disagree.
- Copy to Site: Review note: "Left out:" lines are mixed into the same "Each change" list as the actions, so arrowing through the plan reads things that will not happen as if they were steps.
- Compare Sites: Review note: status words are WordPress's raw values ("publish here, future there"), not the plain words used elsewhere ("published", "scheduled").
- Compare Sites: Review note: custom post types are not compared, and the omissions line does not name them.
- Compare Sites: Review note: it is a dead end. Nothing in the report leads to Copy to Site or Make Them the Same for a line, so acting on a difference means finding the item again by hand.
- Compare Sites: Review note: the report is one flat list with no per-kind headings or counts at the top. On a big pair of sites the person must arrow through every line to learn the scale.
- Export Site as WXR: Review note: the counts are spoken with WordPress post-type slugs and never go plural: "12 post, 40 attachment, 2 wp_block". Use the plain names ("posts", "files", "synced patterns").
- Export Site as WXR: Review note: the outcome is spoken and then the report opens with the same sentence. The dialog's arrival cuts the speech off, and the person hears it twice. Speak nothing, or open nothing (GATE-13).
- Export Site as WXR: Review note: one bad date ends the whole export, and From and To are not checked against each other, so From after To gives an empty file. Ask again on the same field instead.
- Export Site as WXR: Review note: the Save dialog suggests no file name (such as "{site} {date}.xml"), so the person types one every time.
- Export Site as WXR: Review note: an Everything export writes commenters' emails and IP addresses (`wp:comment_author_email`, `wp:comment_author_IP`) and authors' emails to a plain file. That matches WordPress, but neither the chooser nor the report says the file holds personal data.
- Export Site as WXR: Review note: no Practice Site crossing guard. That is correct for the export itself, but see Import below.
- Import WXR as Drafts: Review note (critical): the import skips Workbench Access, Safe Mode and View As Role, as Put Back does. It can make hundreds of drafts, terms and uploads on a site marked Read Only.
- Import WXR as Drafts: Review note: the order of questions is backwards. The person presses "Import as Drafts" and is then asked about files, and Cancel there throws away the yes they just gave. Ask about files before the preview, and show the choice in the preview.
- Import WXR as Drafts: Review note: the spoken result always ends "Ctrl+Z moves the drafts to the Trash", even when nothing was made. In that case no undo is recorded, and Ctrl+Z says "... This cannot be undone." The two sentences contradict each other.
- Import WXR as Drafts: Review note: no Practice Site guard. A WXR exported from the Practice Site can be imported into a real site with no crossing question, which is the very path the guard exists to stop.
- Import WXR as Drafts: Review note: undo leaves the new terms and uploaded files behind. It says so, but the person must then clean up by hand across two lists.

##### By Name

- The By Name node and its children: Review note: F5 does not re-read. The scan is kept for five minutes (`_SCAN_SECONDS = 300`), and `refresh` does not clear it; only a By Name change does. After editing on the site, F5 shows the old answer, silently.
- The By Name node and its children: Review note: the scan reads at most 10 pages of 100 (1000 posts and 1000 pages, and the same for terms, media and people), and a cap is never said. On a bigger site, Rename Everywhere and Replace Everywhere change "everywhere" except the items past 1000, and the preview looks complete. The unread note covers refusals, not truncation.
- The By Name node and its children: Review note: the By Name node's F1 lists "terms, fields, authors, media, links, blocks" and leaves out patterns, forms and template parts, which are three of its nine children.
- The By Name node and its children: Review note: only posts and pages are scanned (`wp/v2/posts`, `wp/v2/pages`). Custom types that use a term, field or link are not counted, so a Rename can leave them behind. Check Every Link, by contrast, includes custom types.
- The value row's context menu: Review note (critical for discoverability): Check Every Link, the only command built for Links rows, is buried under More. Meanwhile Rename, Split, Merge and Reassign, which all refuse on a Links row, sit on top. On every other kind, Check Every Link sits under More and refuses. The menu does not adapt to the kind it is on.
- The value row's context menu: Review note: refused actions are enabled rather than disabled or hidden, so a screen-reader user tries each one to learn which work. The scope matrix already knows (`by_name_support`). Use it in `supports` so they read "unavailable", or leave them out.
- Where It Is Used (Enter): it is a read-only text report, not a list, so there is no way to open one of those posts from it. Compare the Broken Links window, which has "Open in Editor".
- Rename Everywhere: the preview's title keeps the menu's ellipsis ("Rename Everywhere..."). Every other preview in the window has a plain title. It is read as the dialog title on every open.
- Split: Review note: pressing OK with nothing checked does nothing and says nothing (`if not picked: return None`). Say "Nothing checked, so nothing moves."
- Split: Review note: the check-box group has no access key. It is the only control, so that is minor.
- Merge Into: Review note: tier mismatch. This row is Tier WRITE (`merge_value`), while Merge Into on a term row is Tier DESTRUCTIVE (workbench_actions.py), for the same irreversible term deletion. Under Organize access both are refused, but the tiers should agree, and DESTRUCTIVE elsewhere means confirm by name.
- Merge Into: Review note: the chooser lists every other term with no post counts, so the person cannot tell "News (300 posts)" from "news (1 post)". The By Name row itself shows the counts.
- Replace Everywhere: the media chooser lists bare file names from the library ("IMG_2041.jpg"), with no title or alt text. For a screen-reader user choosing a replacement picture by file name alone is guesswork.
- Find Items Missing This Field: like Where It Is Used, it is a dead-end text report with no Open.
- Check Every Link: Review note (critical for discoverability): see the menu note above. The command is under More, and only one of nine By Name kinds can use it. A Links node command, or a node context-menu row, would be easier to find than a row command that ignores its row.
- Check Every Link: Review note: the label never changes. While a check runs, the same "Check Every Link..." row, with its ellipsis promising a dialog, silently means Stop. Show "Stop Checking Links" while one runs.
- Check Every Link: Review note: one check at a time across all sites, and choosing it on another site's Links row stops the running check instead of starting one. The person hears "Stopping the link check..." when they meant "check this site".
- Check Every Link: Review note: skipped types are silent. A custom type the account cannot read is dropped with no line, so "All 300 links ... work" can be said for a partial read. By Name's unread rows exist for exactly this.
- Check Every Link: Review note: the result is spoken and then the Broken Links window opens with the same sentence as its purpose. The window title interrupts the speech (GATE-13, said twice).
- Check Every Link: Review note: "Open in Editor" opens only the first item that holds the link. A link on 22 pages needs 22 trips, with no way to choose which holder; the details pane lists them but they cannot be opened. Replace Everywhere is the bulk fix and is not offered from this window.
- Check Every Link: Review note: the check runs on the window's two-worker pool, which list loading also uses. A run that takes minutes takes one worker, and with any other long job (a Practice Site start, a big Put Back plan) no node in the window loads until one finishes. See the Practice Site note.
- Check Every Link: Review note: it competes with Needs My Attention > Broken Links (a sample of the first 40 links). The two are not linked: the Broken Links node does not offer "check everything", and this command's results do not feed that node.

##### Across Sites

- The Across Sites node: Review note: Ctrl+0 lands on an empty container. The person hears the node and an empty list, and must know to press Right Arrow. Ctrl+1 (Needs My Attention) avoids this by landing on Inbox, a child. Ctrl+0 could land on Tags and Categories, or the container could list its children as rows.
- The Across Sites node: Review note: a row's detail is one long run-on sentence of variants, missing sites and, for plugins and themes, the same REST disclaimer on every row. Arrowing down a 40-plugin list repeats the disclaimer 40 times if the details pane is read. Put the disclaimer in the node's help once.
- The Across Sites node: Review note: the Plugins variant is "version {v}, {status}", which mixes two facts into one variant. See Make Them the Same.
- Across row context menu: Review note (critical): across rows carry no site (`WbRow("across", "", ...)`), so the window's `refusal_for` returns nothing for every across action. Each handler must check access itself:
- Across row context menu: Make Them the Same and Revoke Everywhere check per site.
- Across row context menu: Install on Sites Missing It checks nothing.
- Across row context menu: Promote to Network checks only `activate_plugins`, not Workbench Access.
- Across row context menu: Under Read Only access, Safe Mode or View As Role, those last two still write.
- Across row context menu: Review note: Revoke Everywhere is irreversible ("a revoked password cannot be restored") but is Tier WRITE, the same tier as Make Them the Same. It should be DESTRUCTIVE, like Delete Permanently, with a confirmation by name.
- Across row context menu: Review note: five of seven actions refuse on most kinds. Hide the rows a kind cannot use; the scope matrix already says which.
- Make Them the Same: Review note (critical): for plugins, the variant includes the version, but the edit sends only `{"status": ...}`. Choose "version 2.3, active" when another site has "version 2.1, active": the plan says "changes from version 2.1, active to version 2.3, active", the request changes nothing, and the outcome says "2 of 2 sites changed to version 2.3, active". That is a false success. Either compare plugin status only, or say plainly that versions are not changed and point to Open in Dashboard.
- Make Them the Same: Review note: Make Them the Same on Settings can push values such as `siteurl`, `home` or `admin_email` from one site to the others. Those are in `wp/v2/settings`. The preview lists them, but nothing warns that some settings are site-identity values that must never be the same.
- Make Them the Same: Review note: the winner chooser shows only variant words, not which sites hold each variant or how many. The person must read the row's Properties first to know which is the majority.
- Revoke Everywhere: Review note: the Ctrl+Z sentence is doubled: "It cannot be undone. This cannot be undone." `do_undo` appends its own "This cannot be undone." to a summary that already says it.
- Revoke Everywhere: Review note: a destructive, irreversible action whose preview defaults to "Revoke" on Enter. Every other irreversible action in the window (Delete Permanently, Reset) asks with Cancel as the default.
- Compare Global Styles: Review note: it compares every site's styles in effect, not the selected theme's. The row the person chose makes no difference beyond being a theme row.
- Compare Global Styles: Review note: spoken, and then a report with the same sentence opens (GATE-13).
- Install on Sites Missing It: Review note (critical): installs plugins with no Workbench Access, Safe Mode or View As Role check, and no `install_plugins` check.
- Install on Sites Missing It: Review note: plugin installs are not recorded in Change History, so they do not appear in Edit > Change History either. Every other site change in this section is recorded.
- Install on Sites Missing It: Review note: declining WordPress.org consent still goes straight to an install preview, which installs from WordPress.org anyway. Saying no to "ask WordPress.org" and then pressing Install sends the request to the site, which itself asks WordPress.org. The consent wording should make clear what "no" covers.
- Open in Dashboard: one site at a time. "Open it on every site missing it" is what Install already does for themes, but Open in Dashboard has no "all" choice.
- Properties on an across row (Alt+Enter): the sheet's only purpose is reading; it adds no actions. Fine, but the row's detail already holds the same text.
- Site Sets: Review note: the person types a set name blind. Existing sets are never listed, so changing "Client sites" means remembering its exact spelling, and a typo silently makes a second set. Start with a chooser of existing sets plus "New Set...".
- Site Sets: Review note: there is no rename. A set is deleted only by unchecking every site, which is not discoverable from the first dialog.
- Site Sets: Review note: members are stored by display name. Renaming a site, or a Practice Site picking up " (practice)", drops it from every set with no word said.
- Across Sites Scope: Review note (critical for trust): the scope is invisible and short-lived.
- Across Sites Scope: It is not in Where Am I (Alt+1), not in the status bar, and not in the node help.
- Across Sites Scope: It is kept only on the provider object (`self.scope`), so closing the window returns it to every site.
- Across Sites Scope: The chooser always starts on "Every site", whatever the current scope.
- Across Sites Scope: A person who set "Client sites" yesterday and presses Make Them the Same today is changing every site.
- Across Sites Scope: Review note: the scope covers Across Sites, the Fleet and Compare Global Styles only. The Calendar, Needs My Attention, Watches and Copy to Site's site list ignore it. The help names "Across Sites and the Fleet", which is accurate but easy to miss.
- Across Sites Scope: Review note: if the chosen set is removed, the scope silently becomes every site (`members is None`).
- Calendar: Review note: days run oldest first, so the list opens on two weeks ago. Today and the coming week, the part people plan with, are in the middle. Start at today, or select today's row.
- Calendar: Review note: the day words have no year, so late December and early January read the same pattern with no year cue.
- Calendar: Review note: each status and type is capped at 300 (`max_pages=3`), and no row says so.
- Calendar: Review note: rebuilding the tree after each Calendar load (`wx.CallAfter(self._days_changed)`) may make the screen reader re-announce the tree or move its virtual position. Worth a JAWS and NVDA check.
- Fleet: it is read only and that is said ("The Fleet only reads; it changes nothing."). It is a good summary view, but nothing links a "critical" health state to Needs My Attention > Site Health.

##### Needs My Attention and Watches

- Needs My Attention and Inbox: Review note: Inbox's F1 says "Everything below Needs My Attention". It actually holds four of the twelve: waiting comments, pending review, spam and form responses. Scheduled, drafts, updates, health, accessibility, broken links and membership orders are not in it.
- Needs My Attention and Inbox: Review note: a stopped Practice Site stays connected. Every Needs My Attention node then starts with "Could not ask Practice Site" every time QUILL starts (the site stops when QUILL closes). Mark a practice site as stopped rather than failed, or leave it out of the account-level lists while it is not running.
- Needs My Attention and Inbox: Review note: "Could not ask {site}" rows have kind "fact", so their F1 says "A fact about the site. Enter reads it in the details pane." That is accurate enough, but it would help to say what to do (check the connection, or Site Properties).
- Needs My Attention and Inbox: Review note: Broken Links here is a sample (first 40 unique links, said in its row). Its F1 does not mention Check Every Link under By Name > Links, the full version.
- Watches node: Review note: the rows read "on" and "off" but cannot be changed where they are. Space or Enter on "New comments waiting off" does nothing useful. Let Enter (or a context-menu row) turn a Watch on or off, or open Workbench Options with that Watch focused.
- Watches node: Review note: the row F1 ("A fact about the site") is wrong for a Watch row, which is about the account.
- Watches node: Review note: nothing the Watches said is kept. There is no "what changed" list on this node, so a sentence missed while away from the computer is gone. The node shows when the last round ran, but not what it found.
- Workbench Options (choosing Watches): Review note: the consent is only in F1. Checking a box starts network requests to every site, but the visible label says only "Watch: New comments waiting", and the screen reader reads the help only if F1 is pressed.
- Workbench Options (choosing Watches): Review note: the interval is not a choice. `watch_minutes` (minimum 15) exists in the options file and is shown on the Watches node, but no dialog sets it.
- Workbench Options (choosing Watches): Review note: "Workbench options saved." does not say what is now on. Saying "3 Watches on: comments, form responses, site down." would confirm the change without a trip to the Watches node.
- Workbench Options (choosing Watches): Review note: the window is titled "Workbench Options" but holds only Watches. Site Sets, which share the same file, live in another dialog.
- Workbench Options (choosing Watches): Review note: the help says "while the editor is open"; the Watches node says "while QUILL is open". Watches run from the editor's timer, in QUILL and in QUILL Lite, whether or not the Workbench is open. One wording, please.
- What Watches announce, and when: Review note (critical): one failed read silences every other Watch on that site. `_site_round` runs the comments check first, and any `WordPressApiError` (for example an Author account refused on held comments) is caught around the whole site (`except WordPressApiError: continue`). Form responses, updates, health and reviews on that site are then never said, every round, and nothing tells the person.
- What Watches announce, and when: Review note: "Plugin updates available" depends on an `update` or `new_version` field in `wp/v2/plugins`. Core WordPress does not send it (the Fleet's own docstring says core REST "does not report waiting updates"). On most sites this Watch will never speak, and its label promises otherwise.
- What Watches announce, and when: Review note: a round can produce a burst. Eight kinds times several sites, each sentence a separate announce, arrive at once and may interrupt each other or whatever the person is reading in the editor. Combine a round into one sentence ("3 changes: ...") with the details on the Watches node.
- What Watches announce, and when: Review note: "A new form response on {site}." is said whatever the count. Ten new responses sound like one. Watches only track the newest id, so the count is not known; say "New form responses".
- What Watches announce, and when: Review note: comments waiting are read one page of 100 (`max_pages=1`). On a site with a large backlog, new comments past the first 100 are not counted.
- What Watches announce, and when: Review note: the Practice Site stops whenever QUILL closes. With "A site not answering" on, the next session can say "Practice Site is not answering..." and later "Practice Site answers again." for something the person never meant to watch.
- What Watches announce, and when: Review note: ISO week codes ("2026-W46") are spoken as is in the form-spam sentence. "the week of 9 November" would be friendlier.
- What Watches announce, and when: Review note: Watches ignore Across Sites Scope and Site Sets; every connected site is asked.

##### Practice Site

- Practice Site node: Review note: the node reports but cannot act. Its "What to do" row says "Tools > Practice Site starts it." Enter on that row, or a node context-menu row, should simply open the Practice Site dialog.
- Practice Site node: Review note: the first three rows are file paths, which are long to hear and matter only when something is missing. "Ready" or the missing piece would be enough, with paths in Properties.
- Start the Practice Site: Review note (critical): a start of up to five minutes is silent. No "Starting; this can take three minutes the first time" is said at the start, and nothing is said during it. The person cannot tell a slow start from a hung one. Say the expected wait up front, and give a status-bar cell like Check Every Link's.
- Start the Practice Site: Review note: the start holds one of the window's two background workers for up to five minutes. With a link check running, no node can load until one finishes (see Check Every Link).
- Start the Practice Site: Review note: "Connect it in a moment." means opening the dialog again and choosing Connect. Starting and connecting are two trips for what is always wanted together. Connect when the start finishes, or offer "Start and Connect".
- Connect It as Practice Site: Review note: Connect stays on the menu after connecting. Choosing it again says "already connected", which is fine, but the dialog could say "Connected" in the choice instead.
- Connect It as Practice Site: Review note: the site always shows under Sites as "(practice)" (practice_label), which is the right protection; every preview and history line carries it.
- Stop the Practice Site: Review note: "practice site" is lower case here and in Reset's sentence, but "Practice Site" in the menu, the dialog title, Start's sentence and the node. A small thing, but braille shows it.
- Stop the Practice Site: Review note: Stop runs on the UI thread (`stop_process` is called directly, not through `background`). On Windows this may run taskkill and wait, which freezes the window briefly with no announcement.
- Stop the Practice Site: Review note: the profile stays connected after Stop, so every account-level node (Needs My Attention, Calendar) lists "Could not ask Practice Site" until it is started again or forgotten.
- Reset the Practice Site: Review note: Reset is unreachable when a piece is missing. The dialog does not open at all if the tool, Node or core files are absent, so a person cannot clear an old practice site's data and its stored password on a build that no longer has the tool. Reset needs only the folder.
- Reset the Practice Site: Review note: a snapshot of the Practice Site survives a Reset (snapshots are keyed by the profile id, which Reset forgets). Those snapshots can no longer be reached from Put Back, because Put Back looks under the current profile's id. They are orphaned on disk.
- The practice crossing question (used by other commands): Review note: WXR is a gap in the guard. Export from the Practice Site, then Import WXR as Drafts into a real site, carries practice work across with no question.
- The practice crossing question (used by other commands): Review note: the question comes before the command's own preview, so the person agrees to "send it" before seeing what "it" is. That order is deliberate in the code ("every cross-site write calls this before its own preview"). A sentence in the preview ("This comes from the Practice Site") would keep the reminder in view at the moment of the real decision.
- The practice crossing question (used by other commands): Review note: on the Cancel default, Enter cancels. That is the right default for this question, and it is the opposite of every preview's default, so the same Enter key means "go ahead" one dialog later.
- Undo across this section (Ctrl+Z, Edit > Undo WordPress Change): Review note (critical): a non-undoable entry blocks the whole stack. After any of the commands above, Ctrl+Z can no longer reach the undoable change made just before it (a Trash, a Rename Everywhere). The person hears "... This cannot be undone." and may conclude the earlier change cannot be undone either. Skip past non-undoable entries, or say "The newest change cannot be undone; Change History lists the earlier ones."
- Undo across this section (Ctrl+Z, Edit > Undo WordPress Change): Review note: summaries that already say "It cannot be undone." get " This cannot be undone." added (Revoke Everywhere).

##### Gravity Forms

- Where Gravity Forms appears in the tree: a response row's title is "{form title} entry", so every response to one form has the same name. "Added a note to Contact entry on Example Site" never says which entry. The entry number is in the Properties sheet but not in any spoken outcome.
- Where Gravity Forms appears in the tree: the list shows no column that tells two responses apart (no submitter name or email). Only the details pane carries the first three answers.
- Context menus on Gravity Forms rows (order as shown): New Gravity Form is under More on every form row, but it acts on the site, not on the form you are on. On the form menu it is the only row that ignores the selection.
- Context menus on Gravity Forms rows (order as shown): the form row's F1 sentence says "Enter lists responses; the context menu shows its feeds and results, tests it, and changes a field type." It does not mention Edit Form, New Gravity Form or the two Copy commands.
- The Item menu for Gravity Forms: the four chord rows have no access letter, so walking Item by letter cannot reach them. Every other Item row has one.
- The Item menu for Gravity Forms: Ctrl+Alt+F for Star and Ctrl+Alt+I for Resend are hard to guess. The help says "Star it to come back to. Ctrl+Alt+F." and gives no hint why F (flag) or I.
- The Item menu for Gravity Forms: the labels differ between the two menus: "Notes..." on the context menu and "Entry Notes..." on Item; "Star or Unstar" against "Star or Unstar Entry"; "Copy as a Gravity Form..." against "Copy QAF Form as a Gravity Form...". A listener who learns one name hears another.
- Permissions (applies to every Gravity Forms command): "You are Editor on" has no article. The core permission sentence elsewhere says "You are an Editor on". Two styles of the same message sit side by side in one window.
- Permissions (applies to every Gravity Forms command): Change a Field Type checks gravityforms_create_form, but Edit Form, which can change every field, checks gravityforms_edit_forms. Someone who may edit forms but not create them can rebuild a whole form in the editor, yet is refused the smaller job.
- Permissions (applies to every Gravity Forms command): Not Spam and Spam on a response check the WordPress capability edit_posts (requirement "forms"). They do not check a Gravity Forms permission, unlike every other Gravity entry command.
- Read in Full (response, feed, result): the details pane names answers by field number ("3: Jane"), not by question label. Properties does better (labels from the form). The pane is what a listener hears first.
- Not Spam (response): "and the site was told" is true for QAF, which reports to its spam providers. For Gravity Forms only the status changes; no spam service hears about it. The sentence overclaims.
- Not Spam (response): on a response that is not spam, the outcome says "approved", a comment word that means nothing for a form entry.
- Not Spam (response): set_entry_spam sends row.raw, the entry as it was when the list loaded. It does not read the entry again first, unlike Star, Read and answers. An answer changed in wp-admin since the list loaded is overwritten with the old copy. This is a silent data-loss risk.
- Not Spam (response): Unapprove (Ctrl+Shift+U, on the Item menu) on a response also sets it not spam, while its label says "Back to waiting".
- Spam (response): the same stale-copy risk as Not Spam. The help "Hold it as spam." is the only explanation; nothing says whether Gravity Forms then hides it from the Responses node (it moves to Held as Spam after the refresh).
- Notes... (response): the notes are shown in a dialog built for change previews. The list is labelled "Each change:" and its help says "One line for each thing the change creates, replaces or skips". Both are wrong for reading notes, and the listener hears them every time.
- Notes... (response): Enter in the notes list presses the default button "Add a Note...". A person reading notes with Enter in mind ends up in the Add a Note box.
- Notes... (response): long notes are one list row each; a listbox truncates nothing, but there is no way to read one note in a text box or copy it, except the read-only report version for people who cannot add.
- Star or Unstar (response): the list has no Starred column, so after the refresh nothing tells a listener which rows are starred except Properties.
- Mark Read or Unread (response): "Marked read 3 entries" reads oddly; "Marked 3 entries read" would be natural English. No Read column either.
- Resend Notifications... (response): because it is recorded with no undo, Ctrl+Z straight after says "{that sentence} cannot be undone." (history.py), with a doubled full stop ("Admin Notification. cannot be undone."). It also blocks Ctrl+Z for every change before it, since the history never steps past an un-undoable change.
- Resend Notifications... (response): unchecking every box and pressing OK returns an empty list. The code treats that as Cancel and says nothing.
- Properties on a response, and editing its answers: a choice answer (drop-down, radio, check box part) is a plain text box. Nothing offers the form's choices, so a typo stores a value the form never allowed. The same goes for dates and numbers: no check before sending.
- Properties on a response, and editing its answers: a check-box field's parts each become a field ("Toppings, Cheese"), and the value is the choice value, not "checked". An empty part means unchecked, which a listener must guess.
- Properties on a response, and editing its answers: fields locked by edit_posts give a WordPress-role reason, then the save gives a Gravity Forms reason. A person can be told two different things for the same edit.
- Properties on a response, and editing its answers: the undo sends without the date_updated check, so Ctrl+Z after someone else's later edit overwrites it.
- Properties on a response, and editing its answers: the sheet's title is "{form} entry Properties", with no entry number. The number is only inside General.
- Properties on a feed or a result: this is a raw dump. Meta is JSON text, and the key names are Gravity Forms' own. Nothing here is editable, although Rename and Activate exist on the menu.
- Properties on a form: the sheet title comes from the row's title, which for a form row is its plugin cell, so the title is "Gravity Forms Properties - {site}", not the form's name. (The commands work around this with a replace; the sheet does not.)
- Properties on a form: the generic sheet is not where a form is edited (Edit Form is), but nothing on it says so.
- Show Its Feeds (form): filtering by title means two forms with the same title share their feeds in the view.
- Show Its Results (form): a form with no quiz, poll or survey field adds no rows (load_results skips it), so the filtered list is empty and nothing from the Gravity Forms code says the form has nothing to count.
- Test This Form... (form): the edit box uses Gravity Forms' input names (input_3_3), not question labels. A listener cannot tell which line is which question until the preview, which shows labels. This is the biggest usability gap in Test This Form.
- Test This Form... (form): on a live site the warning is one line in a list. It is not a separate confirmation, and the default button still submits. Feeds such as Stripe or Mailchimp fire for real.
- Change a Field Type... (form): the type names here ("Single line text", "Drop-down list") differ from the form editor's ("Single Line Text", "Drop Down"). One product, two vocabularies.
- Change a Field Type... (form): "Cannot carry over" lists raw Gravity Forms keys ("enableChoiceValue", "randomize") that mean nothing to a listener.
- Change a Field Type... (form): the help for the editor's Type box points here to change a type ("Change a Field Type on the form changes it later"), but only 7 of the editor's 18 types convert. A Phone or Date field never appears in the Field list, with no sentence saying why.
- Edit Form... (form): Cancel (or Escape) in the editor throws away every edit with no "Discard changes?" question. After the Check Before Saving loop it is easy to lose a session's work with one Escape.
- Edit Form... (form): Remove Field takes effect at once in the editor with no confirmation. The preview catches it before anything is sent, but there is no in-editor undo.
- Edit Form... (form): the save preview says label placement as its code: "Label placement: left_label (was top_label)."
- Edit Form... (form): "Fields move:" speaks the entire field order, not what moved. On a 30-field form one move is a very long line.
- Edit Form... (form): the Choices syntax ("text = value", leading asterisk) is power-user markup typed into a text box, with the rules only in F1 help.
- Edit Form... (form): only the default confirmation and the Admin Notification are editable; others are kept untouched, and the editor never says that more exist.
- New Gravity Form... (site, from a Forms row or node): Ctrl+N on Forms always means a Gravity form. On a QAF-only site it says "Gravity Forms is not on {site}: ..." instead of making a QAF form or saying how to make one.
- New Gravity Form... (site, from a Forms row or node): "Entries were not touched." after making a brand-new form is noise.
- New Gravity Form... (site, from a Forms row or node): Ctrl+N on Forms > Responses, Feeds or Results is not mapped and gives the generic New Here sentence.
- Copy as a QUILL Accessible Form... (Gravity form): every other "make" command in this area undoes with Ctrl+Z; this one tells the person to go and delete the draft themselves.
- Copy as a Gravity Form... (QAF form): the new Gravity form goes straight to the site with no accessibility check, while Edit Form and New Gravity Form both run Check Before Saving.
- Delete Permanently... (feed): the Item menu help for Delete Permanently says "Gone for good, after you confirm by name." A feed is confirmed with a button, not by name, and Ctrl+Z brings it back, so the same row says two contradictory things.
- Delete Permanently... (feed): feed row F1 says "Shift+Delete deletes it", which is the only place the key is taught for feeds.
- Filter Builder on Responses (Gravity): on a site with both QAF and Gravity Forms, Filter Builder on Responses always opens the Gravity Forms builder (gravity_filter_builder returns True whenever the site has Gravity Forms), so QAF responses cannot be filtered by their questions there.
- Filter Builder on Responses (Gravity): five or six dialogs in a row to build one condition, each titled only "Filter Builder", so the title never tells a listener which step they are on.

##### Shop

- Where the Shop appears in the tree: the Shop node sits under the site even on a site without WooCommerce; opening it is how you learn there is none.
- Where the Shop appears in the tree: nothing gates a shop row by capability (needs is "" for products, orders, coupons, settings). An Editor sees every row enabled, fills in five dialogs, previews, and only then hears WooCommerce's refusal.
- Properties on shop rows (all kinds): this is not tailored. A product can have dozens of WooCommerce fields, in WooCommerce's order. The "Edit Product..." command and the sheet are two different ways to change a product, with different checks.
- Products: context menu: Enter leaves QUILL for the browser. On every other row type, Enter stays in QUILL. A listener pressing Enter to read a product is sent to the browser.
- Products: context menu: Move to Trash is under More, though Delete runs it.
- Edit Product...: the Status list does not start on the product's current status (no initial), so OK on a published product makes it published only by luck of order. If the first row is chosen by accident, a draft becomes published. The preview catches it, but only if the person reads it.
- Edit Product...: five modal dialogs for one change is slow. One sheet with five fields would be quicker to review and to correct.
- Edit a Variation...: Edit a Variation has an undo and a conflict check; Edit Product, its sibling, has neither.
- New Product...: New Product is on every product's menu, though it ignores the product.
- Move to Trash... (product): a Trash that can only be emptied or restored in wp-admin is a dead end. Reviews, by contrast, restore with Ctrl+Z.
- Shop orders: context menu: Enter opens wp-admin in the browser. Reading the order, which is what most visits are for, is the second row.
- Change Status... (order): a customer email is sent and there is no undo. That is correct, but the outcome sentence does not say the email went.
- Notes... (order): notes are listed in a single-line choice list; Enter on a note closes the dialog with nothing done. The two "Add" rows sit after every note, so on a busy order they are a long arrow away (End reaches them).
- Notes... (order): the Gravity Forms notes and the shop notes are two different dialogs for the same idea.
- Refund... (order): the strongest confirmation in the Workbench, and well worded. The only gap: the "How" list starts on the gateway, so OK on autopilot moves money.
- Customers: editing a billing address is one dialog per address line, about ten in a row, and Cancel on the eighth loses the first seven.
- Coupons: on Edit Coupon the Discount list does not start on the coupon's current kind, so a percent coupon edited for its date becomes a cart discount unless the person moves back to the first row.
- Store Settings: Change Setting...: the choice list does not start on the current value, so a listener cannot hear what is set without leaving the dialog.
- Product Reviews: the shop's best-behaved area, with selection, outcomes, undo and conflict checks. It shows what the product, order and coupon commands are missing.
- Shipping Zones, Tax Rates, Tax Classes, Attributes, Brands, Webhooks: the Delete command for zones, attributes and brands is labelled "Delete..." while the help on the Item menu says Delete Permanently is "confirm by name". Here it is a preview button, which is fine, but three words for the same idea (Delete, Delete Permanently, Remove) appear in one product.
- Shipping Zones, Tax Rates, Tax Classes, Attributes, Brands, Webhooks: removing a shipping method sends at once after the preview and records no undo.

##### Events

- Events: context menu: as with products, Enter goes to the browser.
- New Event...: there is no way to choose an organizer or categories at creation; categories need a second command.
- New Event...: typing "YYYY-MM-DD HH:MM" by hand is error-prone; no date picker or "tomorrow at 7" understanding.
- Edit Event...: the help and the PLUGIN_ACTION_ROWS text both promise "title, start, end, time zone, venue and cost", but Edit Event never asks for the venue; it keeps the old one. A wrong promise.
- Edit Event...: "All day:" starting on "No" means an all-day event edited for its cost becomes timed unless the person changes it back.
- Events Between Dates...: a report rather than a filtered list, so you cannot act on what you find.
- Categories and Tags... (event): names typed must match existing terms; there is no list to choose from, though QUILL has just read them.
- Venues and Organizers: eight dialogs to make a venue, and a blank answer on an edit clears that field, which the preview shows but which is easy to do by Enter-Enter-Enter.

##### SEO

- Where SEO appears in the tree: the node is called "SEO" but is Yoast-only. A Rank Math or All in One SEO site hears only the error.
- Edit SEO...: seven dialogs for one item, and the indexing list does not start on the current setting.
- Edit SEO...: no running character count while typing the SEO title, though Search Appearance knows the limits.
- Bulk SEO Editor...: the Bulk SEO Editor is on every SEO item's menu, though it opens the whole site.
- Open in Dashboard (Site SEO row): half the Site SEO node is pointers to wp-admin. That is honest, but it is the plugin's hand-off.

##### Memberships

- Where memberships appear in the tree: the Discount Codes list is usually just a pointer row to wp-admin, so the node promises a list it rarely has.
- Membership row context menu (every pmpro row): the two discount-code commands appear on a level, an order and a subscription row too, where they have nothing to do with the row. A level row has no level command at all.
- Membership row context menu (every pmpro row): Properties is a raw read-only sheet of the item's fields.
- Look Up a Discount Code...: the answer is only spoken. There is no window to read it again or copy it.
- New Discount Code...: levels must be typed as numbers learned in wp-admin, though the Membership Levels node lists them. The preview passes no level names, so it says "Level 2 (level 2)", which says the number twice and the name never.
- New Discount Code...: the code is upper-cased silently.
- Show Memberships... (on a person): the dates are the site's raw strings, not friendly dates as elsewhere.
- Show Memberships... (on a person): the membership rows (Show, Check Access, Change, Cancel) are on every person's menu on every site, PMPro or not. Not found in code: any hiding or greying of them on a site without PMPro.
- Check Membership Access...: words from a title take the first search result without saying so or offering a choice. A common word can check the wrong page.
- Change Membership Level...: the fallback asks for a number from wp-admin.
- Change Membership Level...: no undo for a change that stops a recurring payment; the preview says so only for cancellation.
- Cancel Membership...: the dialog's own Cancel button sits next to "Cancel Membership". A listener hears "Cancel Membership, button" and "Cancel, button" side by side, and Escape is the safe one. A button named "End Membership" would avoid the clash.
- Cancel Membership...: tier 3, but confirmed by one button, while a refund asks for the amount typed.

##### Redirects

- Add Redirect...: no undo for a new redirect, though deleting what was just made would be safe.
- Add Redirect...: the preview does not warn when the new redirect makes a chain or loop, though Test an Address can work that out from the list already read.
- Turn On or Off: a reversible on/off with a confirmation but no Ctrl+Z is backwards: every other on/off in the Workbench undoes.
- Delete Redirect...: the row help says "Gone for good, after you confirm by name", and the Administration Areas text says "deleted after a confirmation by name". The code asks a plain Yes/No; nothing is typed. The help is wrong.
- Delete Redirect...: QUILL has the redirect's fields, so an undo that makes it again would be easy and would match feeds and tax rates.
- Test an Address...: a clear, useful answer. It uses the list as last read, so a redirect added in wp-admin since is missed until F5.
- Redirect This Address... (404): the 404 stays in the log after it is redirected; nothing marks it done.
- Add a Redirect after a new slug: it uses the default group without asking, unlike Add Redirect, and a 301 without offering the kind.

##### Multisite

- What there is not: a person managing a 20-site network must connect each subsite by hand, with its own application password. Nothing says this in the Sites node or in F1.
- Promote to Network...: when no site qualifies, only the first site's reason is spoken; the others are lost.
- Promote to Network...: each connected subsite counts as a network, so two subsites of one network say "network-active on 2 of 2 networks", and WordPress is asked twice.
- Promote to Network...: there is no "Demote" or network-deactivate, and no undo, for a change the summary itself calls one no single site can reverse.
- Promote to Network...: the check activate_plugins is a single-site capability; the real requirement (super admin) is only known when WordPress refuses.
- Network Admin row (wp-admin Screens): the row is listed on every site, single sites included (it has no namespace gate), so a single-site owner is offered a screen that does not exist.
- Plugin rows on a subsite: Activate or Deactivate offers "Deactivate" on a network-active plugin and sends status inactive from the subsite. QUILL does not check whether WordPress allows that from a subsite; any refusal is the site's own error, spoken as it comes.
