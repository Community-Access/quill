# GitHub and WordPress Workbench implementation status

**Updated:** 2026-11-10  
**Workspace:** `D:\quill`  
**Status:** Implementation is in progress.

The accepted specifications are the [GitHub Workbench PRD](../Product%20Requirement%20Documents%20and%20Specifications/github-workbench-prd.md)
and [WordPress Workbench PRD](../Product%20Requirement%20Documents%20and%20Specifications/wordpress-workbench-prd.md).
This page records delivery state and later decisions; the PRDs remain the
complete statement of accepted product requirements.

## Current scope decisions

- WordPress plugin-specific integrations in this implementation are limited
  to **QUILL Accessible Forms (QAF), Gravity Forms, and Paid Memberships Pro**.
- QAF and Gravity Forms are the supported form systems. Paid Memberships Pro
  is supported through its documented WordPress Abilities API for levels,
  member memberships, orders, subscriptions, and search. The site's own
  capability checks remain authoritative for every operation.
- Other plugin-specific form and membership integrations are outside the
  current delivery scope. The general WordPress route and Abilities discovery
  features remain part of the Workbench.
- The classic GitHub Items/Explore and WordPress management-window fallback
  choices are retired. The editor doors open the Workbench.

## GitHub

The editor menu and QUILL Lite now route GitHub browsing doors to the shared
Workbench. The classic-window preference and environment override have been
removed. Existing native Items, Explore, review, permissions, and repository
administration features remain available through their Workbench nodes.
New issue creation now discovers readable Markdown issue templates, offers a
template or blank start, carries supported title/body/label/assignee defaults,
and previews the issue before submission. GitHub's structured YAML issue
forms and oversized templates remain unsupported in this flow.

The accepted GitHub PRD's remaining delivery sequence is still open:

1. **Phase 11 — Coverage:** vendor the GitHub API snapshot, add the coverage
   table and `GATE-GITHUB-COVER`, and generate the coverage chapter.
2. **Phase 12 — Templates (partial):** Markdown issue-template selection,
   prefill, and preview are implemented. Discussion forms and the Templates
   node, builder, interop, checks, starters, saving, copying, and community
   files remain.
3. **Phase 13 — Beyond parity:** API Console, Read as Document, Watches,
   editor commands, repository lists, role comparison, Dry Run, practice
   repository, and the remaining features named in PRD section 22.
4. **Remaining feature coverage:** move each item in PRD section 14 from the
   planned list into an implemented Workbench surface or document its actual
   API limitation. Across Repositories and Repository Sets are not complete.

Manual NVDA, JAWS, Narrator, braille, scaling, and live-account acceptance
remain outstanding. The engineering checklist is in the
[GitHub Workbench roadmap](./github-roadmap.md).

## WordPress

The management-window fallback and preference have been removed. Common
plugin discovery labels are narrowed to QAF, Gravity Forms, and Paid
Memberships Pro. The shared API and Abilities surfaces continue to expose
what each connected site actually offers.

### Form control conversion

- **QAF:** Form Outline now previews a field type change, retains shared field
  properties and compatible choice data, adjusts single/multiple defaults,
  and blocks target types whose required setup is missing. An automatically
  created choice matches an existing default value.
- **Gravity Forms:** the Workbench exposes a field conversion action for
  common text, paragraph, email, number, drop-down, radio, and checkbox
  controls. It reads the full form, previews the selected field's changes,
  preserves the rest of the form, checks for concurrent edits, then sends the
  complete form object through REST v2 PUT after confirmation. The action requires the site's
  `gravityforms_create_form` capability and Full Workbench access. Complex
  field families are left untouched.
- Conversion actions use the existing labelled field picker and preview
  dialogs. Manual screen-reader, keyboard, and scale checks remain part of
  acceptance.

### Paid Memberships Pro

PMPro abilities appear with the provider name in the Workbench's Abilities
list. Read and write inputs use the bracketed `input[field]` query format.
Read-only abilities use GET; destructive, idempotent abilities use DELETE;
other writes use POST. PMPro's own permission callback remains authoritative,
including when a site customizes its capability names. QUILL also requires
Full Workbench access and a per-run preview for every write. Cancelling a
membership can also cancel the member's recurring subscription at the payment
gateway, so the preview must keep that consequence visible. This API surface
requires WordPress 6.9 or later and Paid Memberships Pro 3.9 or later.

The Workbench now has read-only Membership Levels, Orders, Subscriptions and
Renewals Due lists backed by PMPro's abilities. Orders show the summary fields
PMPro exposes and omit card and billing details. Change and Cancel remain
explicit, previewed ability commands, with the site's permission callback
deciding whether the connected account may run them.

The User context menu also has **Show Memberships...**. It reads that user's
current and past levels when the site exposes the PMPro ability, and lets the
site enforce its member-view permission.

### Remaining WordPress work

- Stage and run the small local WordPress Playground starter through the
  pinned CLI, then verify its local launch and application-password handoff.
  The starter blueprint is implemented; the CLI and runtime payload remain
  build-staged.
- Finish the Workbench manual and align the existing WordPress implementation
  log with the accepted PRD.
- Review permissions, settings documentation, generated help, surface
  reachability, route coverage, and the remaining W0–W8 / WP-R checklists.
- Complete the live-site and assistive-technology acceptance listed in the
  PRD when an authorized test site and screen-reader environment are available.

## Documentation source handling

Both accepted PRDs have been copied into the repository's product
specifications folder. The temporary copies `D:\wt\github.md` and
`D:\wt\wordpress.md` were removed after import. The handoff note remains at
`D:\wt\quill-workbench-handoff-2026-11-10.md`. Each Markdown document changed
for this work has generated `.html` and `.epub` siblings.

## Verification record

- Editor diagnostics found no errors in the changed core, UI, and existing
  routing-test files.
- No tests or builds have been run in this continuation.
