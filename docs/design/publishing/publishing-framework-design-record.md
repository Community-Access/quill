# Publishing Providers Framework — Consolidated Design Record

The dated design and checkpoint notes for QUILL's provider-aware publishing
feature, merged into one chronological record (2026-07-05). Each section below
is a formerly standalone document, preserved verbatim with its headings demoted
one level; the original files are in git history under this folder.

The feature remains **locked off** behind `future.publishing`
(`locked_off=True`); see [README.md](README.md) for the current gate state.

Contents:

- [Remote-integration planning (2026-06-10)](#publishing--remote-integration-planning-2026-06-10)
- [Follow-up phases (2026-06-19)](#publishing-follow-up-phases-2026-06-19)
- [Bundled provider adapter contract (2026-06-19)](#bundled-publishing-provider-adapter-contract-2026-06-19)
- [Framework current plan state (2026-06-19 through 2026-06-21)](#publishing-providers-framework-current-plan-state-2026-06-19-through-2026-06-21)
- [Profile restriction, "writer and above" (2026-06-22)](#publishing-profile-restriction-writer-and-above--scoping-plan-2026-06-22)

---

## Publishing / Remote Integration Planning (2026-06-10)

Timestamp: `2026-06-10 17:24:40 -04:00`

Purpose:

- planning-only note
- no code changes proposed in this note
- evaluates how much of the publishing framework could be rolled into the newer remote-site infrastructure from current `main`

### Short Answer

Some of it can and probably should be aligned later, but not all of it should be merged.

Best planning direction:

- share storage and transport concepts where they are genuinely the same
- keep publishing-specific content workflows separate where the product semantics are different

In other words:

- unify lower-level remote profile and credential patterns carefully
- do not collapse publishing into generic file-transfer UX

### What The New Remote Infrastructure Already Gives Us

Current `main` now has a real remote-site stack for:

- FTP
- SFTP
- WebDAV
- S3
- generic “open from remote” / “save to remote” flows

That stack already includes:

- a saved remote-site profile model in `quill/core/remote_sites.py`
- password persistence patterns
- a governed remote-sites dialog in `quill/ui/remote_sites_dialog.py`
- `File` menu integration in `quill/ui/main_frame_menu.py`
- remote open/save shell wiring in `quill/ui/main_frame.py`

This means the repo now has a broader “remote destination” concept than when the publishing plan was first drafted.

### Where Publishing And Remote Sites Truly Overlap

These parts overlap enough that future alignment is worth planning:

#### 1. Saved Remote Destination Pattern

Both systems need:

- named saved profiles
- a current/last-used selection model
- secure credential storage
- endpoint-specific metadata
- explicit user-driven network actions

Planning takeaway:

- publishing connections and remote sites are both variants of a saved remote destination
- they do not need to stay totally unrelated forever

#### 2. Credential Persistence Strategy

Both systems already use the same broad trust model:

- secure persistence
- no plaintext credentials
- explicit user action before network use

Planning takeaway:

- we should eventually standardize the credential-storage facade, naming, and lifecycle expectations
- this is a strong candidate for shared infrastructure

#### 3. File Menu Placement And Dialog Rhythm

Both systems live under `File` and follow a similar high-level rhythm:

- choose remote destination
- verify or browse
- act explicitly

Planning takeaway:

- the shell can probably grow toward a more coherent “Remote” mental model without changing the underlying publishing semantics

### Where Publishing And Remote Sites Should Stay Separate

This is the important part.

#### 1. Publishing Is Not File Transfer

Remote Sites is fundamentally about files and paths:

- host
- directory
- remote file path
- transport protocol

Publishing is fundamentally about content objects:

- post
- page
- remote content id
- authoring surface
- publish/update semantics
- site API behavior

Planning takeaway:

- publishing should not be rewritten as “just another remote file transport”
- a WordPress post is not analogous to an SFTP path in the user’s mental model or in the code’s behavior

#### 2. Publishing Needs Content-Aware Metadata

Publishing already depends on content-specific truth:

- content kind
- remote id
- remote URL
- publishing status
- chosen authoring surface
- open representation

Remote Sites does not own those concepts.

Planning takeaway:

- publishing must continue to own its content identity and representation metadata
- collapsing this into generic remote-site metadata would likely make the design less honest and harder to maintain

#### 3. Publishing Uses Provider Logic, Not Just Transport Logic

Remote Sites is transport-oriented.
Publishing is provider-oriented.

That difference matters because publishing needs:

- provider-specific browse logic
- provider-specific content-kind support
- provider-specific create/update workflows
- provider-specific API contracts

Planning takeaway:

- the existing provider/client seam in publishing is still the right architectural center
- remote sites should not replace that seam

### My Recommendation

I would not merge publishing directly into the current Remote Sites feature.

I would plan a phased alignment instead.

### Recommended Alignment Plan

#### Phase A: Keep Product Flows Separate

For now:

- keep `File > Publish` as its own content workflow
- keep `Open from Remote` / `Save to Remote` as file-transfer workflows
- keep publishing dialogs and remote-sites dialogs separate

Reason:

- they solve different user jobs
- forcing a single UI too early would create confusion and probably regress accessibility clarity

#### Phase B: Introduce A Shared “Remote Destination” Concept Under The Hood

Later, if we want less duplication:

- define a shared lower-level remote destination/storage abstraction
- let both publishing connections and remote sites build on it

That shared layer could eventually cover:

- id / label / endpoint basics
- secret persistence helpers
- current-selection storage
- maybe some normalized trust/network metadata

But it should not own:

- publishing content kinds
- publishing authoring-surface rules
- browse/update/publish semantics
- remote file browser semantics

#### Phase C: Consider A Shell-Level Discoverability Cleanup

Once both systems are more mature:

- we could revisit the `File` menu wording and grouping
- maybe shape a clearer “Remote” cluster

Example future direction:

- file transfer actions remain path/file oriented
- publishing actions remain content/site oriented
- both live near each other without pretending they are the same thing

### What Feels Safe To Reuse Later

These are the pieces I think are safest to fold together over time:

- saved-profile persistence conventions
- secret storage helpers
- current-selection / last-used selection behavior
- some dialog structural patterns
- some network/trust validation helpers where semantics truly match

### What I Would Not Reuse Blindly

These should stay publishing-owned unless a later design proves otherwise:

- provider registry
- publishing client seam
- browse published content UX
- remote content identity metadata
- authoring-surface / representation logic
- update remote content flow
- local linkage registry for publish/update relationships

### Overall Judgment

A moderate amount of future consolidation looks worthwhile.

But the right consolidation target is:

- shared remote-destination infrastructure

not:

- one merged publishing-and-file-transfer feature

If we over-merge them, we’ll probably make the code less synchronized in practice, because we’d be forcing two different product models into one abstraction too early.

If we align them at the storage/trust/credential layer, we get most of the maintainability win without losing the publishing model we already planned carefully.

### Best Next Planning Follow-Up

Before any code:

- inventory exactly which fields overlap between `PublishingConnectionProfile` and `RemoteSite`
- separate overlaps into:
  - truly shared
  - superficially similar but semantically different
- decide whether a future shared `remote_destinations` core module would reduce duplication cleanly or just rename it

That would give us a clean answer on whether consolidation is actually worth it before we touch the implementation.

---

## Publishing Follow-Up Phases (2026-06-19)

### 2026-06-19 Phase Order

The publishing framework readiness checkpoint is complete. The next work moves into follow-up phases. These phases should be developed deliberately, with local commits and validation after each slice.

Recommended order:

1. WordPress first-party bundled provider package path.
2. Schedule publish.
3. Local-vs-remote compare and first honest sync model.
4. Live third-party publishing provider loading.

This order keeps the highest security and runtime-risk item, live third-party provider loading, last. WordPress extraction can use the trusted first-party bundled path as a proving ground before any third-party provider loading is exposed.

### Phase 1: WordPress First-Party Bundled Provider Package

Goal:

- Move WordPress toward a first-party bundled provider package or adapter while preserving the existing provider/client contract and user-facing behavior.

Initial slices:

- define the bundled-provider adapter contract
- decide whether the first package remains in-process but separately registered, or crosses the Quillin worker boundary
- keep host-owned credential storage and explicit network egress review
- prove the package passes `python -m quill.tools.check_publishing_providers`
- keep all command ids and menus provider-neutral

Done when:

- WordPress can be represented as a first-party bundled provider without shell-specific WordPress assumptions
- the provider registry gate catches missing metadata/client pieces before exposure
- existing publishing workflows behave the same from the user's perspective

Non-goals:

- no third-party provider loading
- no marketplace or auto-discovery of publishing providers
- no rewrite of publishing dialogs just to expose package internals

### Phase 2: Schedule Publish

Goal:

- Add explicit user-controlled scheduled publishing for supported providers.

Initial slices:

- add provider operation metadata for scheduling if the current publish operation is not precise enough
- define scheduled publish data model and validation
- design UI flow with plain-language time/date confirmation
- ensure timezone and date handling are explicit
- add provider-client method or status/date payload strategy as needed
- keep scheduled action review-first and never silent

Done when:

- users can schedule publish for a current or remote publishing document only after explicit confirmation
- unsupported providers report capability gaps clearly
- scheduled publish paths have focused unit tests and dialog/accessibility coverage

Non-goals:

- no background CMS polling
- no recurring schedule automation
- no broad calendar/task system

### Phase 3: Local-Vs-Remote Compare And First Honest Sync Model

Goal:

- Let users understand whether their local publishing document differs from the remote item, without promising automatic bidirectional sync.

Initial slices:

- define remote identity/linkage source of truth
- load current remote state on explicit user request
- compare title, body, status, URL/id, and updated timestamp
- present a readable comparison summary
- decide what conflict states are detectable versus unknown
- keep update/publish actions explicit after comparison

Done when:

- users can request a clear comparison between local and remote publishing content
- Quill reports unknown/stale states honestly
- no automatic overwrite or background sync happens without user action

Non-goals:

- no real-time sync
- no automatic conflict resolution
- no bulk cross-site sync

### Phase 4: Live Third-Party Publishing Provider Loading

Goal:

- Eventually allow non-core publishing providers to register through the same provider/client contract after the runtime, policy, and security gates are ready.

Prerequisites:

- WordPress first-party package path proven
- provider package validation contract complete
- capability and consent flow reviewed for provider network operations
- third-party Quillin/security policy explicitly lifted or scoped for publishing providers
- conflict handling for provider ids and command contributions
- CI gate prevents invalid providers from surfacing

Done when:

- a provider can be discovered, validated, consented, and exposed without weakening SEC-8 or bypassing host-owned secret/network controls
- invalid or conflicting providers are rejected with actionable diagnostics

Non-goals for now:

- do not enable this before the trusted first-party path is proven
- do not make publishing provider loading a hidden side effect of generic Quillin discovery
- do not allow providers to persist secrets outside host-owned storage

### Current Recommendation

Start with Phase 1 slice A: define the bundled-provider adapter contract in docs and tests, then implement only the smallest adapter seam needed to prove WordPress can be package-shaped without changing user-visible publishing behavior.
---

## Bundled Publishing Provider Adapter Contract (2026-06-19)

### Phase 1 Slice A Decision

The first trusted bundled-provider path remains in-process. A bundled publishing
provider contributes one `BundledPublishingProviderAdapter` containing:

- a stable provider id
- its `PublishingProviderDefinition`
- its matching `PublishingProviderClient`
- an explicit network-capability rationale
- the fixed `host_owned` secret-access policy
- the fixed `in_process` execution policy

Registration validates the package shape before changing either existing
provider registry. Definition, client, and adapter ids must match. Missing
network rationale, provider-owned secret storage, and worker execution are
rejected in this slice.

WordPress now has a package-shaped adapter factory under
`quill.core.publishing_bundled.wordpress`. It wraps the same in-tree definition
and client already used by publishing workflows, so registering it through the
adapter preserves object identity and user-visible behavior.

### Deliberate Boundaries

- no package scanning or auto-discovery
- no live third-party provider loading
- no Quillin worker boundary yet
- no provider-owned credential persistence
- no new network action or consent surface
- no shell, command, menu, or dialog change
- no schedule-publish or compare/sync work

The existing provider registry gate remains authoritative after adapter
registration. Focused tests prove WordPress passes that gate in package shape
and malformed adapters are rejected before registry exposure.

### Startup Bootstrap Decision - 2026-06-20

Normal application startup explicitly calls `bootstrap_bundled_publishing_providers()` before importing the UI. WordPress is registered through `wordpress_bundled_provider_adapter()` on this path. Repeated bootstrap replaces only the adapter record; the existing provider definition and client objects retain identity.

This decision does not add package scanning, third-party loading, worker execution, credential access, or network activity. Those boundaries remain unchanged.

Every future adapter/bootstrap slice must run focused publishing tests, relevant unit tests, Ruff, the provider registry gate, and the full unit suite with workspace-local temporary state.

### Phase 1 Contract Finalized - 2026-06-20

The closeout audit accepts this bundled-adapter contract as the completed Phase 1 foundation. Later phases may extend execution and loading policy only in separate reviewed slices; they must not silently weaken identity validation, host-owned secret handling, explicit network action, or validation-before-exposure.
---

## Publishing Providers Framework Current Plan State (2026-06-19 through 2026-06-21)

### Phase 1 Slice A Complete

This checkpoint supplements `publishing-providers-framework.md` with the latest
implemented state.

Implemented:

- `BundledPublishingProviderAdapter` pairs a stable provider id, provider
  definition, and matching provider client.
- Registration rejects mismatched ids before changing either existing registry.
- Trusted bundled adapters require a network-capability rationale.
- Secret access is fixed to host-owned storage.
- Execution is fixed to the trusted in-process path for this phase.
- `quill.core.publishing_bundled.wordpress` represents WordPress using the same
  definition and client objects already used by publishing workflows.

Validation:

- focused adapter, publishing, and provider-gate tests: `34 passed in 0.69s`
- Ruff: passed
- provider registry gate: passed

Recommended next Phase 1 slice:

- decide whether normal app bootstrap should register WordPress through the
  bundled adapter
- preserve current provider/client behavior and all user-visible workflows
- rerun focused publishing tests and the provider registry gate

Do not begin schedule publish, compare/sync, worker execution, or live
third-party provider loading without explicit approval.

### Phase 1 Slice B Complete - 2026-06-20

Decision: WordPress should bootstrap through the trusted bundled adapter during normal application startup.

Implemented:

- explicit first-party bootstrap in `quill.core.publishing_bundled`
- bootstrap call at the application entry point before UI import
- repeat-safe registration preserving existing provider-definition and client identity
- no change to credentials, network behavior, commands, menus, dialogs, or user-visible publishing behavior

Required validation for every next slice: focused publishing tests, slice-specific unit tests, Ruff, provider registry gate, and the complete unit suite using a workspace-local temp root. Record any non-slice baseline failures instead of silently omitting the full run.

Phase 1 remains active. The prohibited later-phase work remains out of scope.

### Phase 1 Closed - 2026-06-20

The closeout audit found no remaining acceptance gap in the WordPress first-party bundled-provider path. Phase 1 is complete. Focused closeout validation passed with `77 passed`, Ruff, the module-size gate, and the provider registry gate.

The user explicitly approved schedule publishing, local-versus-remote compare/sync, Quillin worker execution, and live third-party provider loading to become unblocked after this audit. Continue with schedule publishing as the next separately reviewable roadmap phase. Authorization does not waive SEC-8, consent, accessibility, validation, or testing requirements.

### Schedule Publishing Complete - 2026-06-21

Implemented as the smallest coherent slice: one new `schedule` provider operation, a timezone-aware `validate_scheduled_publish_time` model, an optional `scheduled_at` parameter on the existing `create_publishing_remote_item`/`update_publishing_remote_item` functions (no new top-level action function), WordPress `status="future"` + UTC `date_gmt` behavior with round-tripped `scheduled_for`, and one accessible `SchedulePublishDialog` plus one command/menu entry covering both new-document and already-open-remote-item scheduling.

Validation: core focused battery `61 passed`; combined publishing/accessibility/governance battery `153 passed`; Ruff and the provider registry gate passed; full unit suite `4074 passed, 66 failed, 14 skipped`, the 66 failures matching the pre-existing baseline exactly with no new failures.

Next roadmap phase: local-versus-remote compare and the first honest sync model.

### Compare With Remote Complete - 2026-06-21

Implemented as the smallest coherent slice: `build_publishing_comparison` (pure diff model), `compare_publishing_remote_item` (reuses `load_publishing_remote_item`/`PUBLISHING_OPERATION_LOAD`, no new provider operation or client method), `publishing_comparison_message`, and one command/menu entry reporting through the existing native message-box pattern (no new dialog surface). Cross-session linkage persistence (a durable local registry so compare/update still works after closing and reopening a locally-saved publishing document) was explicitly deferred — `source_metadata` does not survive save/reopen today, and building that registry is a separable, larger concern than this phase's actual scope required.

Validation: focused battery `86 passed`; Ruff and the provider registry gate passed; full unit suite `4083 passed, 66 failed, 14 skipped`, the 66 failures matching the pre-existing baseline exactly.

Next roadmap phase: Quillin worker execution boundaries and lifecycle behavior.

### Quillin Worker Execution Boundaries Complete - 2026-06-21

Scoped narrowly after confirming there's no untrusted provider yet to validate a real subprocess worker boundary against. Implemented: cooperative cancellation (`is_cancelled`/`PublishingOperationCancelled`) threaded through `browse_publishing_content` and the WordPress client's `browse_content`; a new `publishing_worker.py` dispatch module bridging to `quill.stability.task_manager`; `BrowsePublishingContentDialog` now runs its load through the existing `TaskManager` with a real Cancel button instead of blocking the UI thread; `publishing_adapters.py` recognizes `"worker"` as a declared-but-deferred execution policy with its own honest rejection message. The real subprocess/IPC boundary itself remains deferred to the live third-party loading phase.

Validation: focused battery `97 passed`; Ruff, mypy, and the provider registry gate passed; full unit suite `4093 passed, 66 failed, 14 skipped` matching the pre-existing baseline exactly.

Next roadmap phase: live third-party provider loading.

### Live Third-Party Provider Loading — Contract Shipped, Roadmap Closed - 2026-06-21

Found this phase was really a product security policy question, not an engineering scoping one: SEC-8 (`core.third_party_plugins`, `locked_off=True`) is product-wide, and the publishing provider registries have zero gate of their own today. Presented the user three options; they chose: build the `ThirdPartyPublishingProviderAdapter` validation contract (id-conflict checking against bundled providers, host-owned secrets, required worker execution) while leaving real loading unimplemented and the SEC-8 lock untouched — mirroring exactly how Phase 1 shipped a contract before wiring WordPress through it.

Validation: focused battery `82 passed`; Ruff, mypy, and the provider registry gate passed (confirming zero registry impact); full unit suite `4100 passed, 66 failed, 14 skipped` matching the pre-existing baseline exactly.

All four roadmap phases authorized by the 2026-06-20 Phase 1 closeout are now addressed. Two decisions remain explicitly open for the user/product, not engineering defaults: the deferred cross-session publishing-linkage registry (from the compare phase), and whether/when to loosen SEC-8 for real third-party execution.
---

## Publishing Profile Restriction ("Writer and Above") — Scoping Plan (2026-06-22)

### Status

**Implemented 2026-06-22**, same day as the scoping. The two open
questions in "Open questions / flagged assumptions" below were resolved
before coding: soft restriction (Recommended option chosen) and
`FEATURE_STATE_ON` (Recommended option chosen) for the included profiles.
The third open question (timing) was resolved by the user asking to begin
coding immediately — landed now, while still inert behind
`future.publishing`'s `locked_off=True`.

Implementation: `quill/core/features.py`'s `PROFILE_DEFINITIONS` now match
the table below exactly (`author_or_student`'s previously-absent key was
added, not left as an implicit default). `quill/core/feature_catalog.py`'s
`future.publishing` description was extended to state the restriction.
No UI/menu/palette code changed, confirmed unnecessary as predicted.
Two new tests added to `tests/unit/core/test_publishing_framework.py`:
`test_publishing_profile_states_match_writer_tier_and_above` (the
configured values) and `test_publishing_profile_states_are_overridden_by_the_lock`
(the regression test guarding the lock/profile interaction). Module-size
budget for `features.py` bumped 727->738. Full suite, scoped mypy, ruff,
provider-registry gate, and a smoke launch all clean — see
`codex-notes/logs/publishing-providers-framework-current-work-log-2026-06-19.md`'s
matching 2026-06-22 entry for full validation numbers.

The rest of this document is preserved as written during scoping, for
the historical record of what was decided and why.

Note (2026-07-04): the `codex-notes/` working-notes folder cited below
was retired when the repository root was reorganized. The cited plans
and work logs remain available in git history (last present at the
`chore/root-docs-new-homes` merge, PR #824).

### Context

The user was told (by someone above them in the project) that the
publishing feature must only be available in "writer and above"
profiles. This is a separate, additive requirement from the existing
`future.publishing` `locked_off=True` review-gate lock added 2026-06-22
(see `codex-notes/logs/publishing-providers-framework-current-work-log-2026-06-19.md`'s
"Locked publishing off behind the existing feature flag" entry) to keep
publishing out of the public release until this branch's PR is reviewed.

The two are independent and stack:

- **The `locked_off` lock** is the master kill switch. While it's `True`,
  `FeatureManager.state_for("future.publishing")` returns
  `FEATURE_STATE_OFF` unconditionally, for every profile, with no
  exceptions — it is checked before any profile is ever consulted.
- **This profile restriction** describes the feature's *intended
  configuration once that lock is eventually lifted* — which profiles
  should see/use publishing by default once it's actually live. It has
  zero user-visible effect today and will continue to have zero effect
  for as long as `locked_off=True` remains in place.

Do not confuse "configuring the profile states correctly" with "lifting
the review-gate lock." They are two separate decisions; this plan only
scopes the first.

### Decided scope

QUILL's 10 feature profiles (`quill/core/features.py`,
`PROFILE_DEFINITIONS`) have **no existing tier or rank** — they're
independent personas (Essential, Casual Writer, Author or Student, Reader
and Student, Office and Admin, Developer and Power Text, Low Vision,
Braille and Screen Reader Power User, Accessibility Professional, Full
Quill), not a capability ladder. "Writer and above" therefore has no
formal, pre-existing meaning in this codebase. Confirmed directly with
the user (offered three concrete readings; they chose the second):

> **Writer + "serious writing" profiles**: Writer, Author or Student,
> Developer and Power Text, and Full Quill get publishing access.
> Reader and Student, Office and Admin, Low Vision, Braille and Screen
> Reader Power User, and Accessibility Professional are treated as
> different use cases, not a writing-capability tier, and do not get it.
> Essential — the baseline/default profile — does not get it either.

| Profile (id) | Display name | Gets publishing? | Target `future.publishing` state |
| --- | --- | --- | --- |
| `essential` | Essential | No | `FEATURE_STATE_OFF` |
| `writer` | Casual Writer | **Yes** | `FEATURE_STATE_ON` |
| `author_or_student` | Author or Student | **Yes** | `FEATURE_STATE_ON` |
| `reader_and_student` | Reader and Student | No | `FEATURE_STATE_OFF` |
| `office_and_admin` | Office and Admin | No | `FEATURE_STATE_OFF` |
| `developer_power_text` | Developer and Power Text | **Yes** | `FEATURE_STATE_ON` |
| `low_vision` | Low Vision | No | `FEATURE_STATE_OFF` |
| `braille_screen_reader_power_user` | Braille and Screen Reader Power User | No | `FEATURE_STATE_OFF` |
| `accessibility_professional` | Accessibility Professional | No | `FEATURE_STATE_OFF` |
| `full_quill` | Full Quill | **Yes** | already `FEATURE_STATE_ON` — no change needed |

### Current state vs. target state

Read directly from `quill/core/features.py` (lines as of this writing):

- Every profile listed above **except `author_or_student`** already has
  an explicit `"future.publishing": FEATURE_STATE_QUIET` entry in its
  `states` dict (lines 76, 104, 155, 177, 200, 224, 248, 270). All of
  these need to change from `FEATURE_STATE_QUIET` to either
  `FEATURE_STATE_ON` (the 3 included profiles: `writer`,
  `developer_power_text`) or `FEATURE_STATE_OFF` (the 5 excluded
  profiles: `essential`, `reader_and_student`, `office_and_admin`,
  `low_vision`, `braille_screen_reader_power_user`,
  `accessibility_professional` — that's 6, not 5; see the table above for
  the authoritative list).
- `author_or_student`'s `states` dict (lines 116-134) has **no**
  `"future.publishing"` key at all. Today, ignoring the lock, that
  silently falls back to the default `FEATURE_STATE_ON` via
  `state_for()`'s `self.active_profile.states.get(feature_id,
  FEATURE_STATE_ON)` — which happens to already match the target state,
  but as an unintentional gap, not a deliberate choice. The implementation
  should add the key explicitly (`FEATURE_STATE_ON`) so the intent is
  documented in the data rather than relying on an accidental default.
- `full_quill`'s `states` dict is `{feature_id: FEATURE_STATE_ON for
  feature_id in FEATURE_DEFINITIONS}` — a comprehension over every
  registered feature. It already evaluates to `ON` for
  `future.publishing` and needs no change.

### Why no UI/menu code changes are needed

The gating added for the review-gate lock already reads the *live,
active* profile on every call — confirmed by tracing the call chain:

```
main_frame_menu.py:
    if self._feature_enabled("future.publishing"):   # wraps the Publish submenu

MainFrame._feature_enabled (main_frame.py:7082-7086):
    return self.features.is_enabled(feature_id)

FeatureManager.is_enabled (features.py:451-459):
    if self.state_for(feature_id) == FEATURE_STATE_OFF: return False
    ...

FeatureManager.state_for (features.py:436-446):
    if definition.locked_on: return ON
    if definition.locked_off: return OFF          # <- short-circuits today
    if feature_id in self.overrides: return override
    return self.active_profile.states.get(feature_id, ON)   # <- profile-aware
```

The same chain backs `quill/ui/palette.py`'s `is_visible()` (Command
Palette / Go to Anything filtering, via `COMMAND_FEATURE_MAP`). Once
`locked_off` is lifted, both surfaces will automatically respect whichever
profile is active — **no changes are needed in `main_frame_menu.py`,
`quill/ui/palette.py`, or `quill/core/feature_command_map.py`** for the
profile restriction itself. The only source-of-truth file is
`quill/core/features.py`'s `PROFILE_DEFINITIONS`.

### Implementation checklist (for whenever this is actually built)

1. In `quill/core/features.py`, change `"future.publishing"` in these
   `states` dicts:
   - `PROFILE_ESSENTIAL` → `FEATURE_STATE_OFF`
   - `PROFILE_WRITER` → `FEATURE_STATE_ON`
   - `PROFILE_AUTHOR_STUDENT` → **add** `"future.publishing":
     FEATURE_STATE_ON` (key currently absent)
   - `"reader_and_student"` → `FEATURE_STATE_OFF`
   - `"office_and_admin"` → `FEATURE_STATE_OFF`
   - `PROFILE_DEVELOPER_POWER_TEXT` → `FEATURE_STATE_ON`
   - `"low_vision"` → `FEATURE_STATE_OFF`
   - `"braille_screen_reader_power_user"` → `FEATURE_STATE_OFF`
   - `PROFILE_ACCESSIBILITY_PROFESSIONAL` → `FEATURE_STATE_OFF`
   - `PROFILE_FULL_QUILL` — no change (comprehension already yields `ON`)
2. Update `future.publishing`'s `description` in
   `quill/core/feature_catalog.py` to also state the profile restriction
   once it's actually live (today's description only mentions the
   review-gate lock — e.g. append something like "Once enabled, available
   by default in the Casual Writer, Author or Student, Developer and
   Power Text, and Full Quill profiles; off by default elsewhere, but any
   user can still turn it on individually via Manage Individual
   Features.").
3. No changes to `main_frame_menu.py`, `palette.py`,
   `feature_command_map.py`, or any dialog/menu surface (see above).

### Test plan (for whenever this is implemented)

- **Direct profile-data assertions** (independent of the live
  `locked_off` short-circuit — these test the *configured* values):
  for each of the 10 profile ids, assert
  `PROFILE_DEFINITIONS[profile_id].states["future.publishing"]` equals
  the target state in the table above. Natural home:
  `tests/unit/core/test_features.py` or a new test in
  `tests/unit/core/test_publishing_framework.py`.
- **Lock/profile interaction regression test** (important — prevents a
  future session from mistaking "the profile data says ON" for "the
  feature is actually reachable"): with the profile states set as above
  and `locked_off` still `True`, assert
  `FeatureManager(active_profile_id=...).state_for("future.publishing")`
  is `FEATURE_STATE_OFF` for **every** profile, including the 3 that are
  configured `ON`. This documents the lock's precedence explicitly rather
  than leaving it implicit.
- **Once the lock is separately lifted** (a later, distinct change — not
  part of this profile-restriction work):
  - `FeatureManager(active_profile_id=PROFILE_WRITER).is_enabled("future.publishing")`
    is `True`; same for `PROFILE_AUTHOR_STUDENT`,
    `PROFILE_DEVELOPER_POWER_TEXT`, `PROFILE_FULL_QUILL`.
  - `FeatureManager(active_profile_id=PROFILE_ESSENTIAL).is_enabled("future.publishing")`
    is `False`; same for the other 5 excluded profiles.
  - `open_individual_feature_toggles`'s feature list still includes
    `future.publishing` (proves the restriction is a soft per-profile
    default, not a hard lock — see below) once `locked_off` no longer
    excludes it from that screen.

### Open questions / flagged assumptions (confirm before implementing)

These are genuine product decisions, not engineering defaults — flagged
explicitly rather than silently assumed:

1. **Soft vs. hard restriction.** Every profile-scoped feature in this
   catalog today (`future.ai`, `future.character_inspector`,
   `future.cleanup`, and publishing itself) uses a *soft* default: the
   profile sets what's on by default, but `open_individual_feature_toggles`
   lets any user override any non-locked feature regardless of profile.
   There is no existing mechanism in this codebase for a *hard*,
   unoverridable per-profile restriction — building one would be new
   infrastructure, not a data change. **This plan assumes soft**
   (matching every existing precedent). If "only available in writer and
   above" was meant literally — i.e., an Essential-profile user must never
   be able to turn it on even manually — that requires a different,
   larger design and should be raised explicitly before implementing.
2. **`FEATURE_STATE_ON` vs. `FEATURE_STATE_QUIET` for the 3 included
   profiles.** This plan recommends `ON` (fully available, not gated
   behind a separate "show quiet/future features" toggle) since the
   instruction was "available," not "discoverable for advanced users
   only." `QUIET` would mean even Writer-profile users wouldn't see it by
   default without first enabling that separate toggle.
3. **Timing.** This plan doesn't decide *when* to make the
   `features.py` edit — it could land now (harmless and inert while
   `locked_off=True` stays in place) so it's ready the instant the
   review-gate lock is lifted, or it could be deferred until the
   lock-lifting decision is made. That's a separate "when" question for
   the user, not an engineering call.

### Relationship to the rest of the roadmap

This is a refinement of the already-closed publishing-providers-framework
roadmap, not a new roadmap phase. See
`codex-notes/plans/publishing-providers-framework.md` for the full
history; a one-paragraph pointer to this file has been appended there.
