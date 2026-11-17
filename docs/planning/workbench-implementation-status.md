# GitHub and WordPress Workbench implementation status

**Updated:** 2026-11-17  
**Status:** WordPress's last requirements are in code (#1842). GitHub resumed
on 2026-11-15 and is the current focus.

The accepted specifications are the [GitHub Workbench PRD](../Product%20Requirement%20Documents%20and%20Specifications/github-workbench-prd.md)
and [WordPress Workbench PRD](../Product%20Requirement%20Documents%20and%20Specifications/wordpress-workbench-prd.md).
This page records delivery state and later decisions; the PRDs remain the
complete statement of accepted product requirements. The line-by-line
checklist for both Workbenches is `complete.md` at the repository root
(sections 7 and 10B); the WordPress progress log is section 18 of
[wordpress.md](../design/wordpress.md).

## Current scope decisions

- WordPress plugin-specific integrations in this implementation are
  **QUILL Accessible Forms (QAF), Gravity Forms, Paid Memberships Pro,
  WooCommerce, The Events Calendar and Yoast SEO**.
- **2026-11-13:** WooCommerce (`wc/v3`), The Events Calendar
  (`tribe/events/v1`) and Yoast SEO (`yoast/v1` and the post meta it
  registers) are now supported integrations. Jeff's newer instruction to get
  everything listed in wordpress.md 19 (Packages 8 to 13) replaces the earlier
  limit to QAF, Gravity Forms and PMPro. What each does, and what stays in
  wp-admin, is in wordpress.md's progress log for that date.
- QAF and Gravity Forms are the supported form systems. Paid Memberships Pro
  is supported through its documented WordPress Abilities API for levels,
  member memberships, orders, subscriptions, and search, with its older
  `pmpro/v1` routes as the fallback and for discount codes and access checks.
  The site's own capability checks remain authoritative for every operation.
- The site administration sweep adds the Redirection plugin's redirects and
  404 log (`redirection/v1`), which is not a first-class integration. Every
  other area of running a site (backups, security, caching, multilingual,
  email, newsletters, courses, analytics, sharing) has a recorded disposition
  per site, shown in Administration Areas; which of them to make first-class
  is Jeff's call.
- Other plugin-specific form and membership integrations are outside the
  current delivery scope and are labelled deferred (MemberPress, Restrict
  Content Pro, WPForms, Ninja Forms, Formidable, Contact Form 7, Fluent Forms,
  Forminator). The general WordPress route and Abilities discovery features
  remain part of the Workbench.
- The classic GitHub Items/Explore and WordPress management-window fallback
  choices are retired. The editor doors open the Workbench.

## GitHub: resumed 2026-11-15

Jeff paused GitHub work on 2026-11-13 to finish WordPress first, and resumed it
on 2026-11-15 ("we already have a plan and need to complete the github work"),
in the order this page and `complete.md` section 6 give. The pause note held
no picks of its own and is retired.

**2026-11-15, the rest of Phase 12, first PR.** Check Owners on the CODEOWNERS
sheet asks GitHub whether every owner exists and can write
(`quill/core/github/codeowners_check.py`); New Template > Issue form > From a
SurveyJS or XLSForm file... is the conversion's door
(`quill/ui/github_workbench_form_file.py`, `template_convert.form_file_to_draft`);
and the GitHub guide's chapter 12 gains Templates and community files, which it
never had.

**2026-11-16, the rest of Phase 12, second PR: BFL interop.** Forms written in
BFL (BITS Accessible Forms' language, the plain-text form language QUILL's
Forms read and write) now go to and from GitHub issue forms through
`quill/core/forms/interop_github.py`, which maps the QAF (QUILL Accessible
Forms) model to GitHub's schema and back. GitHub-only keys (labels, title
prefix, ids, `render`, per-option required check boxes) ride in the form's
`@extensions`, so QUILL's own five issue forms round-trip unchanged (tested);
everything a GitHub form cannot hold is one sentence in the report.
`template_convert.qaf_to_draft` is now this module's export, so the SurveyJS
and XLSForm door and the Forms commands convert the same way. Tools > Forms in
both editors gains Save As GitHub Issue Form and Open GitHub Issue Form
(`quill/ui/forms_github_commands.py`). Phase 12 is complete. Next: Phase 13.

**2026-11-17, Phase 13: GitHub from the editor (PRD 22.3).** GitHub > From
This Line in QUILL (and under Tools > Git and GitHub > GitHub), flat rows in
QUILL Lite's GitHub menu: Copy GitHub Link to This Line, Who Changed This
Line? (Local Git's blame, renamed, and fixed to answer for the caret's line
rather than line 1), Open the Pull Request for This Line, Open This Line on
GitHub, New Issue from Selection..., Issues Mentioning This File, Comment on
This Line in the Open Pull Request... and Open the GitHub Reference at the
Cursor. One table (`workbench_menu.LINE_ROWS`), one implementation
(`quill/ui/github_editor_line.py`, core in `quill/core/github/editor_line.py`),
catalogue rows so a sentence reaches them. The Workbench learned three
requests from the editor: `filter:`, `search:` and `issue:`. Next in Phase 13:
comment editors, list export and import, Dry Run and the practice repository.

What is built: the editor menu and QUILL Lite route GitHub browsing doors to
the shared Workbench. Native Items, Explore, review, permissions, and
repository administration features are reached through their Workbench
nodes. New issue creation offers Markdown issue templates with prefill and a
preview. Phase 12, templates, is built (2026-11-13): Repository >
Templates lists issue forms, Markdown templates, the chooser, pull request
templates, discussion forms and community files, own, inherited and missing;
an accessible builder with source and preview, checks before save, save to
the default branch or a branch and pull request with a conflict check and a
read-back, starters, conversion both ways, label and assignee pickers, the
Template Chooser sheet, Organizations > org > Templates, FUNDING, CITATION
and CODEOWNERS sheets, Copy to Repositories for one file or the whole set,
pull request templates in New Pull Request, Check This File for form YAML,
and native discussion forms on Ctrl+N in Discussions. Phase 11, coverage, is done: the snapshot is vendored in
`quill/data/github_api/`, `quill/core/github/api_coverage.json` classifies
it (302 covered, 1103 planned, 15 no_api_needed, 206 out_of_scope),
`GATE-GITHUB-COVER` runs in the suite and in `platform_report`, and
`docs/github/workbench-reference.md` carries the generated "Everything
GitHub can do, and where" chapter. The GHManage port (complete.md 10B.1) is
done.

What remains: the real descriptions for GHEC (GitHub Enterprise Cloud) and
GHES (GitHub Enterprise Server), the rest of Phase 13 (comment editors, list
export and import, plain-language batches, Dry Run, the practice repository,
Compare Accounts and the rest of PRD section 22), the remaining PRD section
14 features, Repository Sets in the UI, and manual NVDA, JAWS, Narrator,
braille, scaling and live-account acceptance. The engineering checklist is
in the [GitHub Workbench roadmap](./github-roadmap.md).

## WordPress

### Done

Everything below is in `S:\QUILL`, uncommitted on
`codex/workbench-combined-2026-11-10`, as of 2026-11-13.

- **Frame and doors.** The Workbench has its own rebindable `APP_KEYMAPS`
  entry, built from its menu table (`workbench_window_menu.py`). Delete,
  Shift+Delete and Ctrl+Z act on the list only. **This Post in the
  Workbench** (File > WordPress, both editors) opens the post's list with it
  selected, and **Insert > Picture from the Media Library** opens the
  Workbench in picking mode. Updates, Membership Orders, Shop, Shop Orders and
  Podcast are real lists; no planned node is left.
- **Discovery and content model.** Taxonomy bases, statuses and query enums
  are discovered; custom types have status nodes, New, filters and batch; the
  Content Model names the registrant; registered meta on terms, users and
  comments is editable in Properties; the seven plugin orderings have spoken
  labels.
- **What REST cannot do.** Plugin, theme and Across Sites rows say what core
  REST cannot do (update, auto-update, theme activate and install) and offer
  Open in Dashboard; Install on Sites Missing It installs a plugin by slug
  after a preview.
- **Gravity Forms.** Feeds (activate, rename, delete with undo), Results,
  entry Notes, Star, Read, Resend Notifications with a recipient preview,
  field filters in the Filter Builder, Test This Form through the validation
  route, a whole-form Copy to Site, and Change a Field Type, which now
  accepts Full access and reads the form back after saving.
- **Paid Memberships Pro.** `pmpro/v1` classified and used as the fallback;
  Discount Codes, Look Up a Discount Code, New Discount Code, Check
  Membership Access, Change Membership Level and Cancel Membership, each
  with a per-run preview of the subscription and gateway consequences. Card
  and billing fields are stripped from every row.
- **QAF spam.** Spam and Not Spam go through QAF's spam routes; a held
  response gives QAF's reason; the site's Properties has a read-only Spam
  page from `qaf/v1/spam`.
- **Site administration sweep.** Site Health > Information and Security (an
  XML-RPC check); WordPress.org theme search and language pack status behind
  consent, with their own egress row; Redirects and 404 Log; Content Audit
  and Media Housekeeping with usage before trashing; Privacy Requests as
  exact wp-admin pointers; Search and Upkeep with each answer's source;
  Administration Areas with every third-sweep row's disposition.
- **By Name and Across Sites.** Rename, split, merge, reassign, replace and
  find-missing over every By Name kind, including template parts; Make Them
  the Same for terms, plugins, settings, people, patterns, menus and themes;
  Compare Global Styles; Promote to Network on a multisite; Revoke
  Everywhere for application passwords; Fleet columns with known, unknown,
  unavailable and stale states; a classified scope matrix.
- **Bold workflows.** Copy to Site, Compare Sites, snapshots and Put Back
  from a Snapshot, Calendar and Move to Another Day with daylight-saving
  checks, the editorial queue (Assign a Reviewer, Send Back, Approve and
  Schedule), Read Site as Document, Watches (site down, review and health
  added), the REST Console (Accepts, What It Returns, saved requests), list
  export and import, Import a Folder of Documents, and the Plain-Language
  Batch.
- **People.** Their Application Passwords, Sign Out Everywhere (a wp-admin
  pointer) and Invite from a Spreadsheet.
- **Practice Site.** Bundled CLI, PHP and WordPress core, loopback only on
  `127.0.0.1:9400`, plain HTTP allowed to that address alone, a full reset
  warning, and three practice-only tutorials in QUILL. The 2026-11-13 source
  run passed start, handoff, sign-in, restart, Workbench close and reset.

### Remaining

- The Practice Site run from an installed build, and including
  `scripts/wp_playground/package-lock.json` with the source change.
- Live checks the code could not do from here: `docs/qa/wordpress-live-run.py`
  and a screen-reader pass (NVDA and JAWS) on the Workbench; By Name, Across
  Sites, Copy to Site and Promote to Network on real sites (a multisite for
  the last); Redirection, WooCommerce, Gravity Forms 2.x and PMPro 3.9 on
  WordPress 6.9 against real installs; payments in test mode.
- QAF: the namespace migration across both repositories; the spam write
  route, question bank, blocklist and weekly history QAF does not expose yet;
  its PHPUnit suites.
- Advanced Custom Fields and other field plugins, QUILL Site Types, and
  re-checking schemas after plugin or version changes.
- Capability reasons, previews and self-lockout protection for roles,
  users, application passwords, settings and plugins; preserving editor
  context on return.
- WordPress.org plugin search and install with rollback limits, and
  import/export archives that keep media and link mapping.
- The first-class priority of each third-sweep area (Jeff's decision).

## Documentation source handling

Both accepted PRDs are in the repository's product specifications folder.
Each Markdown document changed for this work has generated `.html` and
`.epub` siblings. The 2026-11-13 documentation pass brought the WordPress and
Forms manual's Workbench chapter (Chapter 13), its keys chapter, the QUILL
and QUILL Lite WordPress chapters, the release notes and this page up to
date with what shipped.

## Verification record

- 2026-11-13: the new and changed WordPress code carries its own tests,
  named per item in `complete.md` sections 7 and 10B.3 (for example
  `test_wp_workbench_gravity_core.py`, `test_wp_pmpro_membership_ui.py`,
  `test_wp_workbench_sweep_core.py`, `test_wp_workbench_by_name.py`,
  `test_wp_workbench_editor_side.py` and `test_wp_practice_site.py`).
- 2026-11-13: the Practice Site ran live from source with the staged Node
  24.22.1, CLI 3.1.64, PHP 8.3 and WordPress 7.1.4.
- 2026-11-13 documentation pass: `python scripts/check_docs_artifacts.py`
  passes. `tests/unit/docs` and `tests/unit/ui/test_documentation_chords.py`:
  152 passed, 1 skipped, 3 failed, none in WordPress documents. The three
  are the QUILL Lite GitHub guide's chapter 13 menu paths (GitHub is
  paused) and two checks on the family startup and WinGet What's New draft
  missing from the release plan.
- Not yet done: a live WordPress regression run, a screen-reader pass, and
  the full suite on this branch.
