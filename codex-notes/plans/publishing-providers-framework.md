# Publishing Providers Framework Plan

## 2026-06-18 fork PR checkpoint

The publishing framework branch has been pushed to the fork and opened as an upstream PR.

- fork branch:
  - `stickbear2015:features/publishing-providers-framework`
- upstream PR:
  - `https://github.com/Community-Access/quill/pull/268`
- target:
  - `Community-Access/quill:main`

Repository handling note:

- continue pushing branch/log/doc updates to the fork remote only
- do not push directly to `Community-Access/quill` until the user has been given that access

## 2026-06-18 provider operation capability implementation note

The next provider-extraction preparation slice is implemented.

Implemented:

- provider operation constants for:
  - verify
  - browse
  - load
  - update
  - create
  - publish
- `PublishingProviderDefinition.supported_operations`
- `PublishingProviderDefinition.implemented_operations`
- metadata helpers:
  - `provider_supported_operations(...)`
  - `provider_implemented_operations(...)`
  - `provider_supports_operation(...)`
- core action gating before provider-client calls
- publish-specific gating for both:
  - current-document publish-now
  - already-open remote publish/promote

Why this matters:

- future bundled or Quillin-contributed providers can register partial lifecycle capability without pretending to support the full WordPress surface
- the shell can remain provider-neutral while core makes capability decisions from provider metadata
- WordPress stays the reference provider for now, but its full lifecycle support is declared data rather than an implicit framework assumption

Validation:

- `pytest tests/unit/core/test_document.py tests/unit/core/test_publishing.py tests/unit/core/test_publishing_browse.py tests/unit/core/test_publishing_framework.py tests/unit/ui/test_main_frame.py tests/unit/ui/test_main_frame_menu_contract.py tests/unit/ui/test_publishing_connection_dialog_a11y.py tests/unit/ui/test_dialog_inventory.py tests/unit/ui/test_main_frame_characterization.py tests/unit/tools/test_module_size_budget.py tests/unit/tools/test_check_banned_patterns.py tests/unit/tools/test_announce_gap.py tests/unit/tools/test_network_egress_audit.py tests/unit/tools/test_dialog_button_contract.py tests/unit/ui/test_dialog_hardening_contract.py -q --basetemp=.tmp\pytest-publishing-capabilities-wide`
- result: `122 passed in 42.70s`

Next likely implementation direction:

- continue extraction-prep by tightening provider/client registration validation, so provider definitions and clients cannot silently drift apart before WordPress is moved toward a first-party bundled Quillin boundary

## 2026-06-18 remote publish lifecycle implementation note

The possible remote-item lifecycle refinement from the prior publish-now note is now implemented.

Implemented:

- `publishing.publish_remote_item`
- File > Publish menu entry for `Publish Open Remote Content...`
- shared update/publish helper that preserves the existing remote-item metadata checks:
  - opened remote item required
  - current connection required
  - stored provider id must match current connection
  - stored site URL must match current connection
- optional `status` on `PublishingProviderClient.update_remote_item(...)`
- WordPress reference behavior that sends `status=publish` only for the publish-open-remote action
- regression tests for command feature mapping, provider-neutral command ids, menu discoverability, shell source contract, and WordPress update payloads with and without publish status

Validation:

- `pytest tests/unit/core/test_document.py tests/unit/core/test_publishing.py tests/unit/core/test_publishing_browse.py tests/unit/core/test_publishing_framework.py tests/unit/ui/test_main_frame.py tests/unit/ui/test_main_frame_menu_contract.py tests/unit/ui/test_publishing_connection_dialog_a11y.py tests/unit/ui/test_dialog_inventory.py tests/unit/ui/test_main_frame_characterization.py tests/unit/tools/test_module_size_budget.py tests/unit/tools/test_check_banned_patterns.py tests/unit/tools/test_announce_gap.py tests/unit/tools/test_network_egress_audit.py tests/unit/tools/test_dialog_button_contract.py tests/unit/ui/test_dialog_hardening_contract.py -q --basetemp=.tmp\pytest-publishing-remote-publish`
- result: `120 passed in 62.51s`

Next likely implementation direction:

- begin the provider extraction/Quillin packaging preparation work, keeping WordPress as the in-tree reference provider until the first-party bundled Quillin boundary is ready
- alternatively, if product wants more user-visible publishing behavior first, keep routing it through provider-client capabilities rather than adding WordPress-specific shell assumptions

## 2026-06-18 publish-now lifecycle implementation note

The next provider-neutral publishing lifecycle slice is implemented.

Implemented:

- `publishing.publish_current`
- `publishing.publish_current_page`
- File > Publish menu entries for `Publish Post Now...` and `Publish Page Now...`
- provider-client create flow with `status="publish"`
- review-first confirmation and post-send result confirmation through the existing message path

Important constraints preserved:

- no WordPress-specific command ID or shell path
- no new dialog surface
- no silent network write
- publish-now behavior stays in the provider-neutral lifecycle layer while WordPress only receives the provider status in its client payload

Possible next lifecycle refinement:

- add a separate promote/publish action for an already-open remote draft, using the same provider-neutral update seam if product wants remote item promotion before provider extraction work

## 2026-06-18 break-ready implementation status

Current branch state is ready for remote sync after the latest publishing framework slices:

- provider registry and verification seam is implemented
- unknown providers no longer fall back to WordPress
- WordPress remains the in-tree reference provider for now, with a future first-party bundled Quillin extraction direction recorded
- remote item editor identity is implemented with metadata-backed display names and no fake local file path
- latest focused publishing/governance validation passed:
  - `117 passed in 62.98s`

Next implementation direction after the break:

- continue provider-neutral publishing lifecycle behavior on top of the registry and identity seams
- revisit deeper browse scaling only if product wants more collection-loading refinement before lifecycle expansion

## 2026-06-18 WordPress provider packaging direction

Decision note after provider-registry review:

- WordPress should remain the in-tree reference provider while the publishing framework contracts are still being proven.
- The desired end-state is for WordPress to be extractable into a trusted first-party bundled Quillin once the provider registry, client contract, consent/security checks, and publishing lifecycle behavior are stable.
- The framework should therefore continue to be developed as provider-neutral core infrastructure plus one reference provider, not as WordPress-specific publishing with extension points added later.
- New implementation slices must keep WordPress details inside provider metadata/client code and must avoid shell assumptions that would make WordPress special.
- Future Quillin provider loading should use the same provider/client registration seam now present in core, but the current publishing implementation must not depend on live third-party Quillin provider loading before the runtime and policy are ready.

Practical staging:

- short term: keep WordPress bundled in core as a reference implementation and regression anchor
- medium term: formalize the provider capability/registration contract enough that bundled providers and Quillin-contributed providers can share it
- later: extract WordPress into a first-party bundled Quillin or equivalent built-in extension package without changing shell workflows

## 2026-06-18 remote item editor identity implementation note

The `Remote Item Editor Identity` slice is now implemented in code.

Implementation decision:

- use generic `Document.source_metadata["display_name"]` for pathless document display identity
- keep `Document.path` unset for remote publishing documents so Quill does not pretend remote content is a local file
- store the provider-returned remote title separately as `publishing_remote_title`
- use `source_metadata["source_label"]` for a lightweight tab source suffix
- refresh title/display metadata after create/update provider responses

This preserves the planning distinction between UI identity and authoritative remote linkage:

- UI identity: document display name and tab source label
- linkage truth: provider id, site URL, remote id, remote URL, content kind, status, authoring surface, and updated timestamp

## 2026-06-12 browse, confirmation, and remote-identity planning addendum

This addendum records a planning-only review after the first browse/open/update/create-draft publishing slices were integrated.

Research basis:

- WordPress REST API collection endpoints for posts and pages default list queries to `status=publish`
- WordPress REST API pagination guidance explicitly expects large collections to be fetched page by page rather than as one oversized pull
- those WordPress details informed this review, but the resulting product guidance below is intentionally provider-neutral so the publishing framework remains reusable across future providers

Observed product gaps from branch testing:

- drafts created through the current publishing flow may not appear in the browse surface
- loading both posts and pages together can time out on servers with large content collections
- write actions need stronger explicit outcome confirmation for user trust:
  - create draft
  - update remote content
  - later publish/promote flows
- opened remote items still behave too much like anonymous unsaved documents in title-bar identity terms

Planning decisions locked by this addendum:

- publishing browse must evolve from a simple one-shot fetch into a scalable collection-loading model
- draft visibility is part of the browse contract and must be made explicit in product wording and filters
- publishing write actions must always produce unambiguous success or failure confirmation in plain language
- opened remote items should gain a clearer document identity model so the editor title/tab better reflects the remote item title without pretending the item is a normal local source file

Approved planning direction for the next non-coding design pass:

- treat browse as a provider-neutral listing workflow with:
  - explicit content-kind scope
  - explicit status scope
  - progressive or staged loading where feasible
  - timeout/error messages that say which slice failed
- avoid a design that assumes every provider can cheaply return all content kinds and all statuses in one request
- preserve the review-first rule not only before network writes, but also after them with clear result reporting
- keep temporary/local identity work separate from remote-linkage truth:
  - the UI may use a temp-backed or synthesized local identity for tab/title clarity
  - the source metadata must remain the authoritative linkage record

Provider-neutral browse-model guidance:

- the browse surface should be designed around a generic model of:
  - connection
  - content kind
  - status set
  - page of results
  - partial result state
  - timeout / partial-failure state
- WordPress happens to expose posts and pages as separate endpoints with default `publish` status filtering, but future providers may expose:
  - one combined content endpoint
  - different status vocabularies
  - cursor-based pagination instead of page-based pagination
- Quill therefore should normalize browse behavior at the framework layer instead of hard-coding WordPress assumptions into the product contract

Recommended next implementation-planning slices:

- `Browse Remote Content Scaling`
  - add explicit status filters, including drafts
  - add staged or progressive loading for multiple content kinds
  - add timeout-aware partial results and retry wording
- `Publishing Confirmation Model`
  - standardize pre-send confirmation and post-send result confirmation across create/update/publish actions
  - outcome copy should report:
    - target site
    - content kind
    - resulting state
    - public or admin URL when available
- `Remote Item Editor Identity`
  - decide whether opened remote items should use:
    - synthesized temp file names
    - tab-title overrides
    - or both
  - preserve the distinction between UI identity and authoritative remote linkage metadata

Constraints preserved from the main plan:

- no silent network writes
- command-first architecture must remain intact for command palette discoverability
- dialog count should stay low unless a new governed dialog is clearly justified
- every new confirmation or browse filter surface must remain accessibility-first and use standard-control patterns

## 2026-06-10 audit addendum

This addendum reflects a post-merge audit after updating the branch with current `main`.

Audit findings:

- the branch is still aligned with the approved architecture direction: provider-aware core layer, feature gating, `File > Publish` entry points, dialog governance, and explicit network egress review are all present in code
- the branch's current implementation already covers:
  - multi-connection storage
  - WordPress application-password verification
  - provider-aware browse of posts and pages
  - open-remote-item into a normal Quill tab with source metadata
- the branch's audit-identified representation gap has now been implemented in code:
  - remote content opens as `Readable Markdown` by default
  - the browse/open flow now offers a per-open `Raw HTML` override
  - Quill now performs a conservative automatic fallback to `Raw HTML`
  - open metadata now records the chosen Quill authoring surface explicitly

Audit guidance locked in by this addendum:

- preserve metadata that makes the chosen open representation honest and machine-readable for later update work
- treat the next remaining remote-authoring work as update-flow behavior on top of this completed representation choice, not as a fresh representation-design question

Status: Approved and in implementation. Owner: product and engineering. Scope: active implementation guided by this spec.

Tracking:

- GitHub issue: `#140`
- Issue URL: [community-access/quill issue #140](http://github.com/community-access/quill)

This plan must be read together with [docs/QUILL-PRD.md](C:/code/git-src/quill/docs/QUILL-PRD.md), which remains the product source of truth. If this plan conflicts with the PRD, the PRD wins.

## Summary

Introduce a provider-based publishing framework that lets QUILL connect to external publishing platforms without turning WordPress into a one-off special case.

WordPress is the first planned provider because it is common, mature, and exposes a stable REST API. The framework should still be designed so later providers can plug into the same concepts, workflows, and UI surfaces.

This document is the active planning and implementation spec for the publishing work. It describes the approved architecture, rollout path, current constraints, and decision points that should guide implementation changes.

## Spec status

This document now serves two roles:

- a planning record of the repo audit and integration constraints
- an implementation-driving product and engineering spec for the approved publishing slices

Anything in this document labeled as a recommendation is the current preferred direction unless a later review explicitly changes it.

Implementation note:

- planning is complete enough for coding and refinement work to continue against this spec
- implementation changes should update this document when they materially clarify architecture, supported provider behavior, or accessibility requirements

## Goals

- Let users publish without leaving QUILL.
- Treat WordPress as the first provider, not the final architecture.
- Preserve QUILL's accessibility bar across setup, browsing, publishing, and error recovery.
- Reuse existing QUILL patterns where they already solve adjacent problems well.
- Keep the first approved slice small enough to review clearly.
- Follow the PRD requirements for explicit network consent, feature metadata and gating, and standard-control accessibility behavior.

## Planning-stage decisions locked by this spec

These decisions are now the recommended baseline for future implementation unless product review explicitly reopens them:

- publishing enters through the `File` menu rather than a dedicated top-level `Publishing` menu
- WordPress is the only named provider in the first user-visible slices
- publishing ships behind a dedicated gated feature id
- the first implementation adds no publishing status-bar cell
- the first implementation does not depend on Quillins or any third-party plugin runtime
- WordPress can become a first-party bundled Quillin later, but that is an extraction destination after the framework seam is stable, not a prerequisite for the current slices
- publishing must support multiple saved publishing connections, not a single global site
- publishing connection UX must stay provider-agnostic until a provider is explicitly chosen
- publishing authentication cannot assume application passwords are the only realistic user credential path
- for the current WordPress provider, Quill must only surface sign-in methods that are real, standards-based remote WordPress flows we can honestly support today
- local-to-remote linkage starts in a Quill-local registry, not inside the source document
- the first publish path is explicit, review-first, and never silent
- the first content path should prefer HTML-oriented output, with any source transformation explained plainly to the user
- remote content opening must support a clear Quill-level representation choice so a user can work either in readable Markdown or in raw HTML when that is the truer editing surface
- publish and update flows must respect the document's chosen authoring surface: Markdown-authored content is converted to HTML at send time, while explicitly HTML-authored content is sent as HTML without a hidden Markdown pass
- publishing includes both posts and pages from the first approved product design
- simplicity is a hard requirement: reuse existing Quill patterns and avoid inventing parallel systems unless the current codebase truly lacks the needed hook
- every publishing dialog control must have one visible label positioned immediately above or immediately to the left of the control, with no helper text inserted between the label and the field in reading or tab-flow order

These decisions can still be changed, but the burden should be on the change proposal to explain why the current spec is no longer the safest fit for Quill.

## Non-goals for the first approved slice

- Full multi-provider plugin loading.
- A generic third-party provider marketplace.
- Rich media upload workflows.
- Taxonomy, category, tag, SEO, or theme-specific editing.
- Real-time bidirectional sync.
- Bulk cross-site publishing.
- custom publishing-specific infrastructure that duplicates existing Quill menu, dialog, notification, settings, or About-surface patterns

## Why this fits QUILL

QUILL already owns most of the writing lifecycle:

- writing
- editing
- review
- accessibility auditing
- AI-assisted revision

Publishing is the next natural step. If users have to leave QUILL for the final handoff, the workflow breaks at the point where many users most want continuity and low friction.

## Existing repo patterns this plan should reuse

The current codebase already has patterns worth reusing instead of inventing parallel systems:

- Provider metadata modules in `quill/core`
- Dedicated connection dialogs in `quill/ui`
- Secure secret storage via Credential Manager or platform fallback
- Feature-flag gating through `FeatureManager`
- HTTPS and local-endpoint policy checks
- Cause-specific verification messages for network configuration flows

The AI connection system is the strongest direct precedent. The publishing design should borrow its shape where that shape still makes sense.

Additional structure observed in the current codebase that should shape the plan:

- `quill/ui/main_frame_menu.py` already owns a very large, centralized top-level menu build and event-binding surface.
- `quill/ui/assistant_tools.py` already provides a mature pattern for connection dialogs, hub dialogs, verification actions, model discovery, and review-first summary text.
- `dialogs.md` and the generated dialog inventory already act as the project’s explicit dialog-governance system.

## Simplicity rule

Simplicity is a first-order requirement for this feature.

That means:

- reuse existing Quill menu, dialog, command, notification, settings, and secure-storage patterns whenever possible
- keep the first implementation small and obvious rather than framework-heavy for its own sake
- avoid building new generic infrastructure unless the current codebase clearly cannot support the needed behavior
- prefer a thin publishing layer that hooks into existing Quill systems over a separate publishing subsystem with its own rules

If a future implementation choice is between a clever abstraction and a simple reuse of existing Quill behavior, this plan prefers the simpler reuse unless there is a concrete reason not to.

## Repo-wide planning audit

This section records the current repo audit so the plan is based on the real application structure, not assumptions.

### Full-repo audit scope

This planning pass reviewed the repo as a full system, not only the obvious UI files. The audit covered:

- top-level governance and contributor docs
- product docs and user-facing guides
- `quill/core` feature, command, settings, storage, trust, notifications, and network patterns
- `quill/ui` shell integration points for menus, dialogs, status bar, and assistant-style connection flows
- `quill/tools` enforcement gates for dialog inventory and network egress review
- `quill/plugins` and related tests to verify current extensibility limits
- representative unit-test families that would fail if publishing were added carelessly
- project config in `pyproject.toml` to confirm typing, test, packaging, and dependency expectations

This means the plan below is intentionally written against the repo's real contracts, not against a hypothetical clean-slate architecture.

### Documentation and policy audit

Confirmed from `CONTRIBUTING.md`, `README.md`, `RELEASE.md`, `docs/QUILL-PRD.md`, `docs/userguide.md`, and `dialogs.md`:

- the repo already has explicit workflow, product, release, and UX rules
- `docs/QUILL-PRD.md` is the source of truth for behavior, trust, and discoverability requirements
- user-facing behavior is expected to be explicit, plain-language, and accessibility-first
- dialog additions are treated as governed product surfaces, not incidental implementation details
- release discipline matters because `main` is protected and changes are expected to be reviewable and sliceable

Planning implication:

- publishing must be treated as a product feature spanning architecture, UX, tests, and docs from the start
- each user-visible publishing slice should be planned with docs and dialog-governance work included, not postponed

### Architecture and layering

Confirmed from `CONTRIBUTING.md` and the current code:

- `quill/core` is the pure domain layer and should own publishing provider definitions, settings models, connection verification logic, and capability metadata.
- `quill/ui` owns menus, dialogs, status-bar interactions, command palette surfacing, and widget lifecycle.
- `quill/plugins` is intentionally minimal in the current product and should not be treated as a ready-made publishing extension mechanism for the first approved slices.
- `quill/tools` and `tests` already enforce behavior around dialogs, menu wiring, and feature surfaces.

### Menu structure

Confirmed from `quill/ui/main_frame_menu.py`:

- the menu shell is already centralized and very large
- top-level menus are already fixed and tested for order
- menu items are individually bound and the repo has tests that fail if a new menu id is appended without a corresponding menu binding

Planning implication:

- publishing should enter through the existing menu architecture, not a separate shell model
- any future publishing menu entry must be planned together with command ids and bind coverage

Additional planning implication from the menu source:

- `quill/ui/main_frame_menu.py` is already a large contract-heavy surface, so the safest approach is to add publishing by following the existing menu-construction and binding style exactly
- any first implementation should avoid spreading publishing menu construction across multiple new mixins unless there is already an established pattern for that split
- publishing should stay inside the existing `File` menu grouping so it remains close to other document lifecycle actions and avoids unnecessary top-level menu sprawl

### Command system

Confirmed from `quill/core/commands.py` and `quill/core/feature_command_map.py`:

- commands are explicitly registered
- each command needs a stable command id
- each command is tied to a feature id, either explicitly or via the mapping helper
- command visibility can be filtered by the active feature manager

Planning implication:

- publishing must be planned as a command family, not merely as menu labels or dialog launches
- the plan must define command naming early enough that feature gating, palette surfacing, and help coverage can stay consistent

Additional planning implication from the command registry:

- publishing commands should be registered through the same explicit `CommandRegistry.register(...)` path as the rest of the app
- command titles should be plain-language first, because they will surface in menus and the command palette without a second translation layer

### Feature gating and profile integration

Confirmed from the PRD, `quill/core/features.py`, and `quill/core/feature_command_map.py`:

- Quill treats feature ids as a cross-cutting contract
- features gate commands, menus, settings, help, and status surfaces
- hidden and quiet behavior is already a first-class concept

Planning implication:

- publishing needs a dedicated feature id and must be designed as gated from the start
- planning should assume incomplete publishing flows remain hidden or quiet until their corresponding slices are ready

Additional planning implication from the shipped profile model:

- the safest first stance is to keep publishing hidden or quiet outside `Full Quill` and explicit overrides until the end-to-end workflow proves stable
- publishing must declare privacy/network impact metadata honestly, because feature descriptions already carry those semantics

### Dialog governance

Confirmed from `dialogs.md`, `quill/tools/dialog_inventory.py`, `tests/unit/ui/fixtures/dialog_inventory.json`, and `tests/unit/ui/test_dialog_inventory.py`:

- dialogs are a governed surface with explicit inventory and classification
- new dialogs are not informal additions; they require registry presence and sanctioned classification
- the repo already distinguishes `native`, `web`, and `hardened_custom` dialog surfaces

Planning implication:

- every planned publishing dialog must be named and treated as a governed dialog surface
- the first slice should minimize dialog count and nesting because every new surface adds governance and regression burden

Additional planning implication from the dialog governance tooling:

- any publishing dialog implementation will need both human checklist coverage in `dialogs.md` and machine registry coverage in `tests/unit/ui/fixtures/dialog_inventory.json`
- a plan that adds too many secondary or nested dialogs too early will create unnecessary maintenance pressure
- any custom publishing dialog must use Quill's shared dialog contract helpers (`apply_modal_ids`, `show_modal_dialog`, and the associated focus-routing behavior) instead of raw `ShowModal()` or one-off modal wiring
- this requirement is not new policy invented for publishing; it is consistent with the existing repo-wide accessibility contract already stated in `docs/QUILL-PRD.md`, especially the label-association and label-in-name expectations and the A11Y-4 dialog-governance work
- publishing dialog fields should follow the repo's clearer native pattern: one visible label directly paired with one control in the same row or immediately above it, with accessible names that begin with the same visible label text
- publishing manager dialogs should prefer direct labels for their primary list, details, and action regions instead of long introductory paragraphs when the controls themselves are the main thing a screen-reader user needs to reach
- publishing helper or reassurance copy should live in intro, status, or verification text, not as free-floating field-adjacent text that can be announced as though it belongs to the next control
- publishing code and tests should explicitly guard against label-order regressions found in human screen-reader testing, including JAWS and other manual validation called for by the dialog contract

### Existing connection-flow precedent

Confirmed from `quill/ui/assistant_tools.py` and `quill/core/assistant_ai.py`:

- the app already has a mature connection dialog pattern
- the current precedent includes provider choice, help text, secure secret handling, verification, discovery actions, and clear status messaging
- endpoint security and blank-key rules are already enforced in tested core logic

Planning implication:

- publishing should mirror this pattern rather than inventing a bespoke setup flow
- WordPress verification should follow the same cause-specific messaging philosophy

Additional planning implication:

- publishing connection UX should reuse the app's existing pattern of "configure, verify, then discover or act"
- secure-secret handling should follow the same split between ordinary settings and secure credential storage
- generic auth-method architecture may describe more than one future sign-in style, but a provider must not advertise or surface a method unless that provider actually supports a real remote flow Quill can implement honestly
- for WordPress specifically, the current implementation scope should treat application passwords as the built-in remote REST-auth path; browser-session, email-link, and ordinary-site-password flows stay architectural concepts for future providers or explicit provider-specific integrations, not current WordPress UI choices
- browse, open, and later update flows should route through a provider-client seam in `quill/core` so the UI never owns WordPress endpoint knowledge directly

### Notifications and status bar

Confirmed from `quill/core/notifications.py` and `quill/ui/main_frame_statusbar.py`:

- Quill already has a persistent notifications store
- the status bar is interactive and feature-aware
- status cells are deliberately tied to actions, not just passive text

Planning implication:

- publishing does not need a custom “toast” model
- user-facing publishing outcomes should be planned through existing notification/status patterns where appropriate
- the first slices should avoid adding a new status-bar cell unless publishing becomes persistent enough to justify one

Additional planning implication from the status-bar implementation:

- status-bar cells in Quill are interactive, keyboard-navigable, and feature-aware, so adding one is a heavier commitment than adding a message string
- the first publishing slices should use explicit dialog feedback plus the existing notification center rather than introducing a persistent publishing cell too early

### Help and user-facing docs

Confirmed from `README.md`, `docs/userguide.md`, `docs/QUILL-PRD.md`, and `dialogs.md`:

- the project already documents connection flows, trust/privacy expectations, and menu entry points in detail
- user-facing text expects plain-language, explicit wording
- dialog additions imply checklist and eventual userguide/help updates

Planning implication:

- publishing is not done when the core works; help/userguide/discoverability updates must be part of the rollout plan
- the plan should stage documentation work alongside feature slices instead of as an afterthought

Documentation hook-in sequence for publishing:

- update `dialogs.md` as soon as a publishing dialog exists
- update user-facing docs only when the feature is no longer hidden-only
- keep wording honest about provider support and plugin/runtime limitations

Additional About-surface follow-up from the code review:

- the current About surface is built from `quill/ui/main_frame.py`
- contributor GitHub identities are listed through the existing `_ABOUT_GITHUB_LINKS` structure
- contributor thank-you prose is rendered through `_about_markdown()`
- the plan should preserve that pattern and add `stickbear2015` exactly in the same style as the existing contributor GitHub entries
- the plan should not introduce a second contributor-credit mechanism just for publishing follow-up work

### Plugin and extensibility reality

Confirmed from `quill/plugins/__init__.py`, `quill/plugins/api.py`, and `tests/unit/core/test_plugins.py`:

- third-party plugin loading is locked off
- the plugin API is intentionally minimal right now
- the product term “Quillins” exists, but the runtime is not yet a general extension platform for this feature

Planning implication:

- this plan must not depend on Quillins for the first implementation
- future provider extensibility should be architected internally first, then exposed later when plugin runtime policy actually supports it

Implementation clarification:

- the current approved implementation should provide a built-in provider registry and provider-client contract for publishing actions
- WordPress is the first built-in provider client using that contract
- future Quillins may eventually contribute providers through an adapter to that same contract, but the current implementation must not pretend live Quillin provider loading exists before the plugin runtime policy changes

### Test and enforcement audit

Confirmed from the current test suite and tooling:

- menu structure and menu binding contracts are tested
- dialog inventory and dialog classification are tested
- dialog contract and hardening behavior are tested
- feature mapping and profile behavior are tested
- plugin policy expectations are tested
- provider and connection logic already have unit-test precedents in adjacent systems
- network egress is structurally audited in `quill/tools/network_egress_audit.py`

Likely enforcement surfaces for publishing work:

- `tests/unit/ui/test_main_frame_menu_contract.py`
- `tests/unit/ui/test_dialog_inventory.py`
- `tests/unit/ui/test_dialog_contract.py`
- `tests/unit/ui/test_dialog_hardening_contract.py`
- `tests/unit/ui/test_dialog_focus_routing_guard.py`
- `tests/unit/core/test_features.py`
- `tests/unit/ui/test_dialog_button_parenting.py`
- `tests/unit/ui/test_connection_dialog_a11y.py`
- provider-oriented core tests modeled after existing assistant/provider tests
- a likely future `network_egress_audit` entry once real publishing requests are implemented

Planning implication:

- publishing must be planned against existing enforcement points before implementation starts
- every user-visible slice should declare which test contracts it is expected to touch
- publishing work should not be considered complete until it has been run against the relevant accessibility, usability, dialog-governance, menu-contract, feature-gating, and publishing-focused tests already present in `tests/`
- every new publishing dialog must use the repo's shared dialog contract and hardening helpers rather than raw modal wiring

### Settings, storage, and trust-model audit

Confirmed from `quill/core/settings.py`, `quill/core/storage.py`, `quill/core/trust.py`, `quill/core/net.py`, and adjacent connection flows:

- Quill already distinguishes ordinary settings from sensitive secrets
- JSON persistence is atomic and path-guarded
- trusted-location and explicit-consent behavior are already part of the app's design vocabulary
- verified TLS is the baseline for outbound HTTPS requests

Planning implication:

- publishing settings must be split into normal configuration versus secure credentials
- remote publishing must follow the same explicit-consent and verified-transport stance as other networked features
- the publishing plan should assume no ad hoc file persistence shape that bypasses current storage patterns

### Packaging and dependency audit

Confirmed from `pyproject.toml`:

- `quill/core` is under stricter typing expectations than `quill/ui`
- tests, lint, and packaging assume incremental, reviewable additions
- optional dependencies are already grouped by capability, rather than bundled indiscriminately

Planning implication:

- the first publishing slice should prefer a core-heavy design that is easy to type-check and unit-test
- provider dependencies should be kept minimal for the first slice and should not force a broad packaging rethink

### Editor and document-lifecycle audit

Confirmed from the repo structure and product docs:

- Quill centers the local writing/editing workflow and treats external actions as extensions of that workflow
- documents, save paths, format handling, and status/reporting are already designed around local-first editing
- the current product model does not justify mutating arbitrary document formats for remote-link state in the first slice

Planning implication:

- the safest first hook is from the existing current-document workflow outward to publishing actions
- remote linkage should begin with a Quill-local registry unless a later approved design chooses document-embedded metadata

## PRD constraints this plan must satisfy

The PRD sets several non-optional requirements that apply directly to publishing work:

- No silent network calls. Any remote publishing action must be explicit, consented, show progress where appropriate, and report the outcome.
- Accessibility-first UI. Publishing surfaces should use the same stock-control, screen-reader-native approach Quill expects elsewhere in the product.
- Feature-registry integration. Publishing cannot be an orphan surface; it needs a feature id, metadata, privacy and network labels, and consistent gating across commands, menus, settings, help, and status surfaces.
- Local-first trust model. Remote publishing is optional, visible, and never the default path for ordinary editing.
- Plugin realism. The PRD’s plugin runtime is limited in v1.0, so this plan must not assume a broad third-party publishing plugin marketplace as a first implementation dependency.
- Menu and command discoverability. Any eventual publish actions should fit the command palette, menu model, and keybinding conventions rather than becoming a separate ad hoc workflow.

## Proposed architecture

### 1. Core provider model

Add a publishing domain in `quill/core` with:

- provider definitions
- connection profile settings
- secure credential handling
- auth-method definitions
- endpoint verification
- provider capability metadata

The framework should not assume all providers behave like WordPress. The core abstractions should represent QUILL actions, not REST endpoints.

The implementation should also respect Quill’s layer boundaries from `CONTRIBUTING.md` and the PRD:

- `quill/core` owns provider logic, settings models, verification logic, and capability metadata
- `quill/ui` owns dialogs, menus, progress, and announcements
- publishing work should not add raw persistence or widget ownership into `core`

### 2. Provider contract

Each provider should eventually implement a shared contract covering:

- verify connection
- list or browse content
- fetch a single item
- create draft post
- update post
- publish post now
- schedule post publish
- create draft page
- update page
- publish page now
- schedule page publish

Nice-to-have later:

- delete or trash
- upload media
- sync status comparison

Recommended planning shape for the contract:

- one provider interface in `quill/core`
- one command-facing service layer that translates Quill actions into provider calls
- no UI classes in the contract itself

### 3. WordPress provider

The first provider should target the standard WordPress REST API and support:

- self-hosted WordPress
- WordPress.com sites exposing the standard API
- WP Engine-hosted sites
- other hosts exposing compatible WordPress REST endpoints
- both posts and pages as first-class content types

Authentication baseline:

- do not assume a single universal WordPress login method
- support a provider-owned list of possible auth methods
- allow the first real implementation to start with one verified method, but keep the model open to browser-based or email-link style sign-in later

### 4. Settings and secrets

Connection profile settings should likely include:

- connection/profile id
- user-visible connection label
- provider id
- site URL
- auth method id
- account identifier such as username or email when the chosen auth method needs one
- content format preference
- optional site-specific defaults later

Planning correction:

- the implementation must not store publishing setup as one singleton connection record if Quill is expected to work with multiple author sites
- the first data model should start with a list of saved publishing connection profiles plus a default/last-used selection model

Secrets should be stored using the same secure pattern already used by AI connection flows, not plain settings JSON.

### 5. Feature gating

Publishing should ship behind its own feature flag until it is proven end to end.

Recommended initial flag shape:

- hidden or quiet in normal profiles
- visible in Full Quill or explicit feature override
- documented as experimental until the workflow is complete
- labeled with explicit privacy and network impact metadata per the PRD feature-registry model

Recommended feature metadata stance:

- maturity: `advanced` or equivalent early-stage label until draft publishing and update flows are both stable
- privacy label: explicitly network-sending
- visibility: hidden or quiet outside `Full Quill` until the first full user-visible slice is approved

## Proposed UX surfaces

### Current UI structure the plan should fit into

The current application already has these top-level menus in the shell:

- File
- Edit
- Insert
- View
- Search
- AI
- BITS Whisperer
- Navigate
- Format
- Tools
- Window
- Help

Because that structure already exists, publishing should be planned as an extension of the current shell rather than as a separate UI model.

## Phase 1 product spec

This section defines the current target behavior for the first coherent user-visible publishing phase. Connection management and verification are already implemented, so this section now mainly guides the first real remote content workflows built on that foundation.

### Phase 1 scope

Phase 1 should include:

- provider-aware publishing connection profiles
- multiple saved publishing connections
- a provider-agnostic connection manager surface
- WordPress connection verification for the first implemented auth method
- publish-current-document confirmation and draft creation
- browse existing remote items
- open remote items into Quill for review and editing
- update existing remote items after explicit confirmation
- support for both posts and pages
- explicit result reporting
- command and menu discoverability for the approved actions

Phase 1 should not include:

- any additional top-level menu expansion
- persistent sync
- media upload
- category/tag/taxonomy editing
- multi-provider user choice beyond WordPress
- document-embedded remote metadata
- a publishing status-bar cell

### Phase 1 user story

The intended first user journey is:

1. The user discovers publishing actions in the `File` menu.
2. The user opens a provider-agnostic publishing connections surface.
3. The user creates or selects a saved publishing connection profile.
4. Only after choosing a provider does Quill show provider-specific fields or auth language.
5. The user verifies the selected connection using the auth method supported for that provider/profile.
6. The user returns to the current document and chooses an action such as `Create Draft...`, `Publish Current Document...`, or `Browse Published Content...`.
7. For a new publish, Quill presents a review-first confirmation dialog with content type, title, destination summary, publish state, and network explanation.
8. For browse or edit, Quill presents a provider-neutral remote-content browser that clearly distinguishes posts from pages and reports the selected site's host.
9. Quill performs the explicit remote action only after the user confirms it.
10. Quill reports the outcome through the dialog result, status text, and notifications.

### Phase 1 command set

The recommended phase 1 command family is:

- `publishing.connections`
- `publishing.new_connection`
- `publishing.edit_connection`
- `publishing.verify_connection`
- `publishing.create_draft`
- `publishing.publish_current`
- `publishing.create_page_draft`
- `publishing.publish_current_page`

The following commands should be planned into the next active content-workflow slice, with only `publishing.schedule_publish` remaining deferred after that:

- `publishing.browse_content`
- `publishing.open_remote_item`
- `publishing.update_remote_item`
- `publishing.schedule_publish`

### Phase 1 menu contract

The recommended phase 1 menu contract is:

- `File -> Publishing Connections...`
- `File -> Verify Current Publishing Connection`
- separator
- `File -> Create Draft...`
- `File -> Publish Current Document...`
- separator
- `File -> Create Page Draft...`
- `File -> Publish Current Page...`

`Browse Published Content...` is now part of the next approved content-workflow slice and should be implemented in a provider-neutral way even though WordPress is the first backing provider.

### Exact hook-in plan

This section describes the current planning view of exactly how publishing would hook into existing Quill surfaces when implementation is eventually approved.

#### 1. Feature registry hook-in

Planned hook:

- define a dedicated publishing feature id in `quill/core/features.py`
- add command-to-feature mappings in `quill/core/feature_command_map.py`
- ensure publishing surfaces follow the same hidden/quiet/on rules as other advanced features

What this avoids breaking:

- existing profile behavior
- command palette filtering
- help/menu/status consistency gates

#### 2. Command registry hook-in

Planned hook:

- register publishing commands through the existing command registry
- make menu items, palette entries, and later keybindings resolve through those commands

Recommended initial command family:

- `publishing.connections`
- `publishing.new_connection`
- `publishing.edit_connection`
- `publishing.verify_connection`
- `publishing.create_draft`
- `publishing.publish_current`
- `publishing.browse_content`
- `publishing.open_remote_item`
- `publishing.update_remote_item`

What this avoids breaking:

- menu-only feature drift
- orphan dialogs not reachable from the palette
- inconsistent feature-id attribution

#### 3. Menu hook-in

Planned hook:

- add publishing actions within the existing `File` menu in `quill/ui/main_frame_menu.py`
- bind each menu id through the existing `wx.EVT_MENU` pattern
- keep the first menu footprint deliberately small

Recommended initial submenu items:

- `Publishing Connections...`
- `Verify Current Publishing Connection`
- separator
- `Create Draft...`
- `Publish Current Document...`
- separator
- `Create Page Draft...`
- `Publish Current Page...`
- `Browse Published Content...`

Phase 1 refinement:

- `Browse Published Content...` is now part of the next approved content-workflow slice and should stay in the `File` menu contract once that slice is implemented

What this avoids breaking:

- top-level menu sprawl before the workflow is mature
- failure of menu binding contract tests
- discoverability gaps between menu and command palette

#### 4. Dialog hook-in

Planned hook:

- implement publishing dialogs as governed `wx.Dialog` surfaces or sanctioned stock/web surfaces, depending on the specific need
- add each publishing dialog to `dialogs.md`
- ensure each new dialog is accepted by the dialog inventory gate

Planned first dialog surfaces:

- `Publishing Connections Dialog`
- `Edit Publishing Connection Dialog`
- `Publish Current Content Dialog`
- later `Browse Published Content Dialog`

What this avoids breaking:

- dialog inventory gates
- keyboard and screen-reader regression expectations
- focus return and escape/default button contracts

#### 5. Notifications and status hook-in

Planned hook:

- use existing notifications for meaningful results such as connection verified, draft created, or publish failed
- consider status-bar integration only after publishing becomes persistent enough to justify a dedicated surface

Recommended first status behavior:

- no dedicated publishing status-bar cell in the first implementation slices
- rely on explicit dialog feedback, status text, and notifications

What this avoids breaking:

- unnecessary status-bar complexity
- premature persistent UI for a feature that may remain gated or quiet

#### 6. Help and documentation hook-in

Planned hook:

- update `dialogs.md` when dialogs are added
- update user-facing docs only when a slice becomes user-visible
- keep PRD-aligned wording around privacy, network consent, and supported scope

What this avoids breaking:

- stale dialog checklist coverage
- discoverability gaps
- mismatch between the actual shipping UI and the user guide

#### 6a. Governance and audit hook-in

Planned hook:

- keep publishing changes aligned with the existing contributor and release rules
- treat network egress review, dialog registration, and feature mapping as first-class acceptance criteria
- include docs updates in the same slice as newly user-visible publishing surfaces

What this avoids breaking:

- shipping a user-visible feature that bypasses current repo gates
- a plan that looks sound architecturally but fails the repo's actual governance model

#### 7. Extensibility hook-in

Planned hook:

- keep provider architecture internal-first in `quill/core`
- do not expose Quillin/plugin extension points for publishing in the initial approved work
- plan a later internal seam where provider registration could be generalized when plugin policy permits it

What this avoids breaking:

- the current locked-off third-party plugin policy
- false expectations that provider installation is available now

## Exact implementation-thinking summary

This section is intentionally concrete so later implementation, if approved, can proceed from a shared mental model rather than vague intent.

### How the feature would enter the app

The planned entry path is:

- feature registry enables publishing for the active profile
- command registry exposes publishing commands
- the `File` menu surfaces the approved subset of those commands
- dialogs handle connection setup and explicit remote actions
- notifications and status text report outcomes

This means publishing would hook into the existing application shell the same way other advanced features do, instead of becoming a sidecar workflow or a one-off floating tool.

### How the current document would participate

The working assumption is:

- the active document remains the source object
- publish actions read from the active document state
- publish confirmation happens in a dialog before any remote call
- remote identity is stored outside the document in the first design, likely in a Quill-local registry keyed by file path or document identity

This minimizes risk to the existing editor and format handlers while still allowing later update flows.

### How WordPress-specific behavior would stay contained

The working assumption is:

- provider-neutral commands ask for publish, browse, update, or verify actions
- a service layer translates those actions into provider-specific API calls
- WordPress-specific fields or limitations stay inside provider/service code and provider-aware help text, not spread through global shell logic

This keeps the UI language mostly provider-neutral while still allowing the first provider to be WordPress.

### How this avoids breaking today’s app

The current planning model is deliberately conservative:

- one bounded menu change only: add publishing actions inside `File`, with no broader top-level menu reorganization in the first slices
- no new status-bar cell in the first slices
- no plugin-runtime dependency
- no silent background sync
- no document-format mutation for remote ids in the first slice
- no bypass around the command registry, menu bindings, dialog inventory, feature gating, settings persistence, or network-egress review systems

That is the core reason this plan should integrate cleanly with the existing codebase if implementation is later approved.

### Recommended menu placement strategy

Based on the current menu layout, the best planning path is:

### Phase A: use the `File` menu

Use the existing `File` menu for the first implementation slices. That keeps publishing near save, open, and other document lifecycle actions, and it matches the updated product direction.

Implementation note for that slice:

- add publishing actions through the existing `File` menu construction in `quill/ui/main_frame_menu.py`
- keep the new actions inside the existing menu-customization and menu-editor model rather than treating them as a shell special case
- keep the final order stable across menu build, menu customization, command palette discoverability, and help text

Recommended first commands in `File`:

- `Publishing Connection...`
- `Verify Publishing Connection`
- `Publish Current Document...`
- `Create Draft...`
- `Create Page Draft...`
- `Publish Current Page...`
- `Browse Published Content...`

Items that are not yet implemented should remain visible only when consistent with the project’s feature-gating rules; otherwise they should stay hidden behind the feature flag until ready.

Planning note from the menu contract audit:

- each new publishing menu id must have a matching `wx.EVT_MENU` binding
- the plan should treat that as part of the acceptance criteria for any implementation slice that adds menu items

### Phase B: keep publishing in `File`

The current direction is to keep publishing inside `File`, not move it back to a dedicated top-level menu later.

### Command palette integration

Every planned publishing action should also exist as a command-palette command from the start. The menu should not be the only discovery path.

Recommended initial command concepts:

- `publishing.connection`
- `publishing.verify_connection`
- `publishing.create_draft`
- `publishing.publish_current`
- `publishing.browse_content`

### Phase 1 UI surface

The smallest coherent user-facing setup is:

- a top-level `Publishing` entry point
- a connections manager for multiple saved sites
- an add or edit connection dialog that stays provider-agnostic until the provider is chosen
- a verify connection action

This is the minimum needed before post creation flows make sense.

The eventual UI should use Quill’s normal discoverability paths:

- menu entry
- command palette command
- feature-gated visibility
- clear disabled-state explanation when unavailable

Phase 1 recommendation:

- keep the visible first flow to connection plus publish-current actions
- do not expand into browse/update until the connection and draft-creation paths are stable and understandable

### Dialog strategy based on existing app patterns

The existing AI surfaces provide the closest UI precedent for publishing. The publishing plan should intentionally reuse that shape:

- a focused connection dialog for provider-specific credentials and verification
- an optional publishing hub dialog later if the workflow grows beyond one dialog
- plain-language summary text near the top of the dialog
- explicit action buttons for verification and discovery tasks
- `OK` or `Cancel` modal behavior with proper escape and default-action wiring

### Recommended first publishing dialogs

#### 1. Publishing Connections Dialog

Purpose:

- list saved publishing connections
- add a new connection
- edit an existing connection
- choose the current/default connection
- verify the selected connection

Recommended controls:

- list of saved connections
- add button
- edit button
- remove button
- set current/default button
- verify button

This dialog should be the publishing equivalent of a connection manager, not a singleton settings form.

#### 2. Edit Publishing Connection Dialog

Purpose:

- enter a connection label
- choose provider
- enter site URL
- choose auth method
- only then show provider-specific or auth-specific fields
- save and verify the connection profile

Recommended controls:

- connection label text field
- provider choice
- site URL text field
- auth method choice
- account identifier field when needed
- secret field only when the chosen auth method actually needs one
- provider help text
- verify button

Expected plain-language summary text:

- explain that Quill can connect to a publishing site only when the user configures it
- state that verification sends a deliberate network request to the configured site
- state that saved sign-in data, when present, is stored securely on the device
- avoid assuming the user already knows what an application password is

#### 2. Publish Current Content Dialog

Purpose:

- confirm what is being sent
- clearly indicate whether the current action is targeting a post or a page
- choose title
- choose draft or publish now
- choose initial format behavior if needed

Recommended controls:

- read-only content-type summary: post or page
- title text field
- status choice: draft or publish now
- content-format summary
- plain-language network summary
- confirmation buttons

This dialog should be review-first and explicit about remote action. One shared dialog may be reused for both post and page flows as long as the active content type is clear in the title, summary text, and control labels.

Expected plain-language summary text:

- say whether the action will create a draft or publish immediately
- name the target site clearly
- state that document content will be sent over the network if the user continues
- explain any format conversion in one sentence, not jargon

#### 3. Browse Published Content Dialog

Purpose:

- list remote posts and pages
- inspect summary metadata
- open selected item into QUILL
- choose update target when publishing changes later

Recommended controls:

- content-type filter or grouped list that clearly distinguishes posts from pages
- searchable list control
- metadata preview pane or read-only text area
- open button
- refresh button

This is now part of the next approved implementation slice. The same caution still applies: keep it provider-neutral in shell language and governed by the same dialog and command contracts as the connection work.

### Dialog governance requirements

Because the repo already treats dialogs as a governed surface, publishing planning should explicitly require:

- a `dialogs.md` entry for every user-facing publishing dialog
- dialog inventory registration when code is eventually added
- dialog contract compliance: title announcement, tab order, enter/escape behavior, and focus return
- nested dialog planning kept minimal in the first slice

Recommended classification expectations:

- `Publishing Connections Dialog`: likely `hardened_custom`
- `Edit Publishing Connection Dialog`: likely `hardened_custom`
- `Publish Current Content Dialog`: likely `hardened_custom`
- `Browse Published Content Dialog`: likely `hardened_custom`
- confirm-only or pick-one prompts inside the flow: prefer native dialogs where possible

### Phase 2 UI surface

After connection works:

- create post draft
- publish current post
- create page draft
- publish current page
- edit existing posts
- edit existing pages
- schedule publish
- browse existing posts
- browse existing pages
- open a selected item into QUILL for editing

### Accessibility requirements

All publishing surfaces must meet the same QUILL bar as other dialogs:

- keyboard-only complete
- predictable focus
- plain-language verification and failure messages
- no dead-end dialogs
- clear success announcements
- no hidden network behavior
- use stock, screen-reader-friendly controls consistent with the PRD’s writing-surface and dialog philosophy

More specifically, based on the current dialog estate:

- prefer stock `wx.Dialog`, `wx.TextCtrl`, `wx.Choice`, `wx.ListBox`, and standard buttons
- avoid introducing bespoke publishing-specific custom controls in the first iteration
- keep verification and publish flows in short, linear dialogs rather than wizard sprawl

## UX contract for first implementation

This is the planning-level UX contract that future implementation should satisfy.

### Connection setup behavior

The connection dialog should:

- start from saved connections rather than a single global connection record
- keep provider names generic until the user chooses or edits a provider
- support multiple saved sites cleanly
- provide a visible verify action before save-and-exit is the only path forward
- use cause-specific feedback such as invalid URL, insecure endpoint, authentication failure, unreachable host, or successful verification

The connection flow should not:

- auto-verify silently on field blur or dialog open
- hide the fact that a real network call is happening
- assume every user has or understands an application password
- use provider-specific jargon before the provider is chosen

### Publish confirmation behavior

The publish dialog should:

- name the target site
- show the proposed title
- let the user choose at least draft versus publish now, unless the slice is draft-only
- explain content-format behavior in plain language
- require explicit confirmation before any remote call starts

The publish flow should not:

- assume the current filename is always the final title without showing it
- publish immediately on menu command with no confirmation step
- perform background retries or deferred sync in the first slice

### Outcome reporting behavior

Success reporting should:

- confirm what happened in plain language
- identify the target site
- provide the remote result identity that matters most, such as URL or remote item id
- surface the outcome through dialog feedback, status text, and notifications

Failure reporting should:

- say what failed
- keep the message specific where possible
- avoid traceback language and raw protocol noise unless the detailed view is explicitly requested

## Planning-stage acceptance criteria

The plan should consider a future slice ready for implementation only if the slice can satisfy these criteria in concept before any code starts.

### Acceptance criteria for slice 1 foundation work

- the feature id, command ids, and initial provider/service boundaries are defined in advance
- the connection model separates ordinary settings from secure credentials
- the endpoint policy is explicitly HTTPS-first and consistent with existing network rules
- the slice does not require new menus or dialogs unless separately approved
- the test plan names the affected core test families and confirms no dialog/menu gates are expected to change

### Acceptance criteria for the first user-visible slice

- the menu location is fixed inside the `File` menu
- the command names and labels are fixed
- the dialog list is fixed and minimal
- the user journey is explicit and review-first
- the documentation update list is known in advance
- the regression surfaces are named in advance

### Regression checklist for future implementation review

Any implementation proposal should explicitly verify impact on:

- feature registry definitions and profile visibility behavior
- command registry and command-to-feature mappings
- menu ids and `wx.EVT_MENU` binding coverage
- dialog inventory and `dialogs.md`
- notification usage and status-text reporting
- settings persistence versus secure-secret storage boundaries
- network-egress review expectations
- user-facing docs once the feature becomes visible

## Recommended decisions resolved from earlier open questions

These replace the earlier broad ambiguity with a recommended spec stance.

### Menu placement

Recommendation:

- place publishing entry points under the `File` menu
- avoid introducing a permanent top-level `Publishing` menu

Rationale:

- this now matches the updated product direction
- it keeps publishing near other document lifecycle actions
- it still works within the current menu-building architecture as long as the existing shell contract is followed exactly

### Provider naming in the first UI

Recommendation:

- WordPress should be the only implemented provider in the first visible slice, even if the core is provider-based
- the generic connections UI should not hard-code WordPress wording before provider selection

Rationale:

- it keeps the user promise honest
- it prevents a “provider framework” UI from implying support breadth that does not exist yet
- it keeps the generic connection-management surface reusable when later providers arrive

### Title derivation

Recommendation:

- prompt every time, with the default suggested from the first heading and a fallback to filename

Rationale:

- it avoids surprising remote titles
- it still keeps the workflow fast

### Remote linkage storage

Recommendation:

- use a Quill-local registry in the first phase

Rationale:

- it avoids mutating the source document contract
- it reduces risk across multiple document formats

### First publish format behavior

Recommendation:

- prefer HTML-oriented output in the first WordPress slice
- if source text is Markdown or another format, explain the conversion in the confirmation step
- treat conversion as a Quill authoring-surface rule rather than as a WordPress-only special case
- when the current document is a Markdown-authored publishing document, convert Markdown to HTML at publish or update time
- when the current document is explicitly an HTML-authored publishing document, publish the HTML body directly

Rationale:

- WordPress natively expects HTML in the standard REST flow
- this is the least ambiguous first behavior
- Quill already understands Markdown and HTML as distinct working surfaces, so publishing should build on that existing model instead of inventing a second parallel content-mode concept

### First user-visible dialog set

Recommendation:

- `Publishing Connections Dialog`
- `Edit Publishing Connection Dialog`
- `Publish Current Content Dialog`

Deferred by default:

- `Browse Published Content Dialog`

Rationale:

- this is the smallest coherent user journey
- it keeps the first visible surface area reviewable

Accessibility and usability requirement:

- every editable field in the connection flow must have an explicit, speech-friendly purpose in tab order
- helper text must explain what belongs in a field instead of giving only provider background or overly chatty prose
- no field should feel effectively unlabeled just because nearby visual text exists
- every publishing dialog must use Quill's shared dialog contract for modal ids, title announcement, focus routing, and escape/affirmative behavior
- provider-specific sign-in choices shown in the UI must be limited to the methods that genuinely work in the current slice, not broader “planned” concepts that only exist in metadata

### First visible remote action

Recommendation:

- the first visible remote action set should include both `Create Draft...` and `Publish Current Document...`
- the first visible page action set should include both `Create Page Draft...` and `Publish Current Page...`
- the default selection inside the publish confirmation dialog should still be `Draft`

Rationale:

- this keeps the first visible workflow honest about the likely long-term shape of publishing
- it avoids a later UX reset where users must relearn the same dialog for publish-now
- it still preserves the safer path by defaulting to draft

Guardrail:

- publish-now should remain an explicit user choice in the dialog, never the menu command's silent default

### Browse in the next content-workflow rollout

Recommendation:

- `Browse Published Content...` should be implemented in the next approved content-workflow slice

Rationale:

- the connection and verification foundation is already built
- page support should not be deferred, because it is now part of the approved content scope
- browse still adds more dialog surface, more remote state complexity, and more inventory/test burden
- browse should therefore land only in the same disciplined provider-neutral architecture, not as a one-off WordPress browser

Refinement trigger after the first browse/edit implementation:

- refine browse further only after the initial browse, open, and update loop is stable and its local-to-remote linkage model is proven

### Success result model

Recommendation:

- the first slice should preserve both the remote URL and the remote id when both are available

Rationale:

- the URL is the most useful immediate user-facing result
- the remote id is often the more stable internal linkage key
- storing both avoids an early redesign if one is needed later for update, browse, or sync flows

First-slice behavior:

- if only one of these values is returned reliably, Quill should store the available value and leave room in the local record for the other later

### Quill-local linkage record shape

Recommendation:

- the first slice should use a flat Quill-local linkage record shape

Recommended minimum fields:

- `provider_id`
- `site_url`
- `remote_id`
- `remote_url`

Deferred by default:

- `last_synced_at`
- content hash or revision markers
- remote title cache

Rationale:

- a flat local record is easy to inspect, easy to migrate later, and low-risk for the first slice
- it preserves the information most likely to matter for later update and browse flows without overdesigning sync early

### Success wording

Recommendation:

- use plain-language completion messages built around action + site + result
- messages should use the configured host only

Recommended first wording set:

- draft created: `Draft created on <host>.`
- draft created with link: `Draft created on <host>. Link available.`
- published now: `Published to <host>.`
- published now with link: `Published to <host>. Link available.`
- connection verified: `Publishing connection verified for <host>.`

Rationale:

- this matches Quill's preference for concise, useful announcements
- it avoids jargon like `POST succeeded` or `remote object created`
- it keeps success reporting understandable in speech output

### Publish-state label text

Recommendation:

- the publish-state choice should use action-oriented labels:
  - `Create draft`
  - `Publish now`

Rationale:

- these labels describe what will happen next, not just the resulting state
- they are clearer in speech output than bare state words like `Draft`
- they keep the dialog aligned with Quill’s preference for plain, explicit wording

## Proposed rollout plan

### Slice 0: planning and approval

- approve architecture direction
- approve naming
- approve feature-gating approach
- approve first implementation slice
- approve exact hook-in points for commands, menus, dialogs, notifications, and docs

### Slice 1: framework foundation

- publishing provider metadata
- connection profile model
- auth method model
- multi-connection storage model
- secure secret storage
- endpoint security validation
- WordPress verification flow for the first supported auth method
- unit tests for those pieces
- feature-registry and feature-gating integration

Status:

- completed

Delivered scope:

- publishing provider metadata
- connection profile model
- auth method model
- multi-connection storage model
- secure secret storage
- endpoint security validation
- WordPress verification flow for the first supported auth method
- publishing menu placement inside `File`
- publishing connections manager and add or edit connection dialogs
- accessibility hardening for those dialogs
- related menu, dialog-inventory, egress-audit, and size-budget updates needed to keep the repo gates honest

Planned tests and governance for this slice:

- core unit tests modeled after current assistant/provider tests
- no dialog inventory changes
- no menu contract changes

This slice proved that the framework shape is sound and that the connection surfaces can meet the repo's accessibility and governance bar before the larger content workflows land.

### Slice 2: first remote content workflows on the approved connection foundation

- create draft from current QUILL document
- send title and body
- return resulting URL or post id
- announce success clearly
- add the first approved publishing entry points under `File`
- add the first approved publishing dialogs
- browse existing posts and pages
- open a selected remote item into Quill for review and editing
- update an existing post, page, or draft after explicit confirmation

Architecture requirement for this slice:

- the commands, service layer, and dialogs must stay provider-neutral in shape even though the first live backend is WordPress
- content-type handling must be framed as Quill concepts such as post, page, browse, open remote item, and update remote item rather than hard-coded WordPress endpoint language in the shell

Planned tests and governance for this slice:

- menu binding coverage remains green
- dialog inventory snapshot updated deliberately
- dialog checklist entries added
- user-facing text reviewed for plain-language and explicit-consent wording
- relevant accessibility and usability tests in `tests/` must be run against the publishing dialogs and menu flow before the slice is considered complete
- representation-switching and publish-format tests should be added in a dedicated publishing-focused test module rather than folded into unrelated editor or export tests, while still reusing existing Quill conversion helpers where that keeps the implementation simple
- publishing-focused unit tests may stay grouped in a small dedicated publishing test module at first; if the command family, provider matrix, or remote-content workflows grow substantially, split those tests into narrower publishing-specific files rather than folding more coverage into unrelated general test modules

Current implementation progress inside this slice:

- publishing now has a built-in provider-client seam in `quill/core` for browse and open actions
- WordPress browse currently supports both posts and pages through that provider-client seam
- the `File -> Publish` submenu now includes `Browse Published Content...`
- the browse dialog loads published content through the current connection and can open the selected remote post or page into a normal Quill editor tab
- loaded remote content currently enters the editor as an untitled local tab with publishing metadata attached in `Document.source_metadata`
- this keeps the editor flow simple now while leaving room for a later local linkage registry and explicit update flow
- current remote-open behavior already includes remote HTML normalization for common entity readability cases and now supports an explicit Quill authoring-surface decision at open time
- remote content can now open as readable Markdown or raw HTML, with that choice preserved clearly enough that later update and publish actions can remain honest

Next implementation steps for this slice:

- add an explicit `Update Remote Content...` flow that reads the publishing metadata from the current document and confirms the target site, content type, and remote item before sending changes
- define and implement the first Quill-local linkage registry for local file path to remote id plus remote URL so saved local documents can reconnect to the correct remote item without relying only on the open tab state
- add the first publish/create dialogs for current-document post and page creation using the same provider-client seam instead of a WordPress-specific UI path
- ensure loaded remote posts and pages announce enough plain-language context in the editor and status text that users understand whether they are editing local-only content or content already linked to a remote site
- add a provider-neutral remote HTML normalization step before content is placed into the editor so rendered punctuation and similar entities from WordPress and later providers are decoded into readable editor text while still preserving a truthful path for later round-trip and update logic
- extend the new representation-aware open metadata into the first explicit `Update Remote Content...` flow so Quill sends Markdown-authored tabs through Markdown-to-HTML conversion and sends HTML-authored tabs as HTML
- route publish and update send-time formatting through existing Quill Markdown/HTML conversion capabilities instead of a custom publishing-only formatter
- define tests for common remote HTML entity cases, especially curly apostrophes, curly quotes, dashes, ellipses, non-breaking spaces, and mixed named versus numeric entities coming from WordPress classic or block-editor HTML
- expand tests for send-time conversion boundaries:
  - Markdown-authored publishing documents are converted to HTML on create or update
  - HTML-authored publishing documents are sent as HTML without additional Markdown interpretation
- expand focused publishing tests to cover update preconditions, linkage-record persistence, and command wiring for the next publish and update actions before broader sync work begins

### Slice 3: schedule and refinement after create, browse, and update are stable

- schedule publish
- compare local versus remote state
- define the first honest sync model
- refine browse summaries, filtering, and remote-state reporting once the base browse-edit loop is stable

Planned tests and governance for this slice:

- any new schedule or sync-related dialog added to dialog registry and checklist
- command coverage expanded only as later refinement genuinely adds new actions
- feature gating verified across all added publishing commands

### Slice 4: schedule and sync polish

- schedule publish
- compare local versus remote state
- define the first honest sync model

## Document model questions

These need explicit decisions before implementation expands:

### 1. Source format

QUILL documents may be plain text, Markdown, or HTML-oriented content. WordPress expects HTML in the standard REST flow.

Decision needed:

- what authoring surface should a publishing document be considered to use at any given time
- when should Quill convert Markdown to HTML for provider send operations
- when should Quill preserve and expose raw HTML instead of translating it into Markdown

Recommended planning stance:

- first implementation should support a simple, explicit content-format choice
- user-facing behavior must be explicit when a document is being transformed rather than round-tripped as-is
- the primary decision is no longer "HTML only or Markdown conversion"; the primary decision is which Quill authoring surface the document is using right now
- if a publishing document is being authored as Markdown, Quill converts that Markdown to HTML at publish or update time because the provider contract expects HTML
- if a publishing document is being authored as HTML, Quill sends the HTML body as authored
- this choice must be visible enough in the workflow that users are never surprised about whether Quill is treating the document as Markdown or HTML
- when remote HTML is opened into the Quill editor, entity decoding and closely related readability normalization should be treated as part of the editor-loading pipeline rather than as a hidden publish-time mutation, because the immediate problem is that rendered WordPress punctuation can appear as broken raw entity text in the editable surface
- that normalization should be conservative: decode standard HTML entities intended for human-readable text, but avoid a broad cleanup pass that silently strips meaningful markup structure before the later update and round-trip design is settled

### 1a. Remote-open representation

Decision needed:

- should remote content open as Markdown by default
- should remote content open as raw HTML by default
- or should Quill ask at open time while the safest default is still being proven

Recommended planning stance:

- keep the representation model simple and honest by supporting two explicit outcomes only:
  - `Readable Markdown`
  - `Raw HTML`
- use Quill terminology, not provider terminology, because this is an editor-surface choice rather than a WordPress-only behavior
- prefer readable Markdown when Quill can conservatively translate common remote HTML into a faithful editing surface
- fall back to raw HTML when conversion would be obviously lossy, misleading, or contrary to an explicit user preference
- preserve the original remote source facts and the chosen Quill authoring surface in metadata so later update logic knows whether it is converting Markdown to HTML or sending HTML as-authored
- do not silently flip an already opened document from one authoring surface to the other during a later save, update, or publish action

Implementation-guidance note:

- Quill already includes Markdown/HTML-aware authoring behavior and conversion utilities elsewhere in the product, so the publishing architecture should hook into those existing capabilities instead of creating a publishing-only content-transformation stack

### 2. Title extraction

Decision needed:

- derive title from filename
- derive title from first heading
- prompt every time
- allow site-specific default behavior later

Recommended first behavior:

- prompt with a suggested default from the first heading, then fallback to filename

### 3. Remote identity

Once a local document is linked to a remote WordPress post, QUILL needs a way to remember that association.

Options:

- embedded document metadata
- sidecar metadata file
- QUILL-local registry keyed by file path

Recommended first planning direction:

- start with a QUILL-local registry because it is lowest-risk and avoids mutating document formats unexpectedly
- if later moved into document metadata, that should require a separate approval step because it changes the file-behavior contract

### 4. Connection and authentication model

Decision needed:

- should a saved publishing connection represent one site/profile pair
- how should Quill represent auth methods that do not use a long-lived password
- how should Quill support future browser-based or one-time-link sign-in flows without rewriting the whole connection model

Recommended first planning direction:

- model publishing connections as named saved profiles
- model authentication as a provider-owned auth-method choice, not a hard-coded password field
- allow secrets to be optional because some auth methods may rely on browser/session flows instead
- keep the first implementation honest if only one auth method is actually wired for WordPress at first

## Risks

### 1. Architecture risk

If WordPress is implemented directly in UI code, the framework will become WordPress-specific and harder to generalize later.

Mitigation:

- keep provider logic in `quill/core`
- keep UI surfaces provider-agnostic where practical

### 2. Accessibility risk

Publishing workflows can turn into complex multi-step dialogs with hidden state.

Mitigation:

- keep first slices narrow
- verify every dialog flow with the project’s existing dialog hardening expectations
- keep publishing UI within the same command/menu/help/status model rather than inventing a parallel surface

### 3. Security risk

This feature adds new network egress and new stored credentials.

Mitigation:

- reuse existing secure storage patterns
- enforce HTTPS for remote endpoints
- keep all requests explicit and user-driven
- add tests for endpoint policy and auth failure reporting
- include feature metadata that accurately labels privacy and network impact

### 4. Content fidelity risk

Markdown or rich structured content may not map perfectly to WordPress post content.

Mitigation:

- start with clearly defined supported formats
- avoid overpromising sync fidelity in the first release
- explicitly test how remote HTML from WordPress editors is normalized when opened into Quill, because a remote item that renders correctly on the site but exposes raw entities like `&#8217;` in Quill is both a readability bug and a trust bug for later update flows

### 5. Scope risk

Publishing can easily expand into CMS management.

Mitigation:

- explicitly keep first scope to connect, verify, create, update, browse, and schedule

### 6. Regression risk against existing shell contracts

Because Quill already has tests and conventions around menus, dialogs, commands, and feature surfaces, publishing can break the app structurally even before it breaks functionally.

Mitigation:

- plan every new publishing command id before implementation
- plan every menu id and matching event binding before implementation
- plan every publishing dialog as an inventory-governed surface
- avoid introducing a status-bar cell in the first slices
- stage docs and checklist updates as part of each user-visible slice

## Remaining decisions for review

The major planning decisions are now covered by this spec. Any remaining questions should be treated as normal implementation-detail review items rather than planning blockers.

## Recommended first approved implementation slice

If this plan is approved, the first code slice should be limited to:

- publishing provider metadata
- publishing connection settings
- secure application-password storage
- WordPress endpoint verification
- feature gating
- focused unit tests

And it should explicitly avoid:

- assuming the v1.1+ plugin marketplace/runtime is already available
- adding custom-drawn or unusual UI controls
- adding any silent or background remote publishing behavior

That slice is small enough to review clearly and large enough to validate the architecture before we build user-facing publishing actions on top of it.

## Recommended first user-visible slice after the foundation

If the foundation slice succeeds, the next recommended slice should be limited to:

- `File` menu publishing action wiring
- `Publishing Connection Dialog`
- `Publish Current Content Dialog`
- WordPress draft creation from the current document
- WordPress page draft creation from the current document
- explicit publish-now from the current document as a user-controlled choice
- plain-language success and failure reporting
- local preservation of remote URL and remote id when available
- targeted dialog, menu, feature, and core tests

And it should still avoid:

- browse/update/schedule flows unless separately approved
- top-level menu promotion
- status-bar cell addition
- multi-provider UI promises

## Full-repo planning conclusion

After the full repo audit, the current planning direction still looks usable inside Quill's existing architecture if it is implemented conservatively.

Why it looks viable:

- the repo already has a provider-and-connection precedent to borrow from
- the shell already has stable places to surface new commands and dialogs
- the feature/profile system can gate incomplete work safely
- the test suite already tells us where careless integration would break contracts
- the product docs strongly support explicit, user-driven network features when they are accessible and well-labeled

What makes it high-risk if done carelessly:

- menu and dialog surfaces are contract-heavy
- network features are governance-heavy
- plugin/extensibility assumptions would be premature
- status-bar and profile integration carry more blast radius than they first appear to

So the planning recommendation remains:

- design publishing as an internal core-plus-shell feature
- start with WordPress as the first provider, not the whole product model
- support both posts and pages
- enter through the `File` menu
- use explicit dialogs and existing notifications
- keep remote linkage outside the source document at first
- keep publish-now as an explicit writer-controlled choice rather than a system-decided content action
- delay any status-bar cell or external plugin story until the base workflow is proven

## About-surface follow-up

This is not part of the publishing framework itself, but it should be tracked alongside this planning pass because it came up during review.

Observed current pattern:

- the About surface is generated in `quill/ui/main_frame.py`
- contributor names appear in prose in `_about_markdown()`
- contributor GitHub entries appear in `_ABOUT_GITHUB_LINKS`

Planned follow-up:

- add `stickbear2015` to the About-surface contributor GitHub list using the same pattern and style as the existing contributor GitHub entries
- keep the format exactly parallel to the other contributor GitHub links
- avoid inventing a separate contributor-credit mechanism when the About surface already has one

## What this plan deliberately does not change

To reduce risk, the current planning direction does not assume changes to:

- the top-level menu order beyond placing publishing actions inside the existing `File` menu
- the command palette architecture
- the status-bar layout model
- the plugin runtime policy
- the current dialog classification system
- the existing AI or BITS provider systems beyond borrowing their connection-flow patterns

Those systems are integration points, not redesign targets, for this feature.

## Acceptance bar for the planning phase

This plan is ready to move into implementation only when:

- the architecture direction is approved
- the first slice is approved
- we create a branch before implementation starts
