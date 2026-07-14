# Publishing Providers Framework — Design Documents

Design and planning documents for QUILL's provider-aware publishing feature
(connect to a remote site such as WordPress and browse / open / create / update /
publish content through a vetted provider adapter).

These were authored during the framework's development and relocated here from the
working notes for durable reference.

| Document | What it covers |
|---|---|
| [publishing-framework-design-record.md](publishing-framework-design-record.md) | The consolidated, chronological design record: early remote-integration planning (2026-06-10), the follow-up phase plan and bundled provider adapter contract (2026-06-19), the implementation checkpoints through live third-party loading (2026-06-21), and the writer-tier-and-above profile restriction (2026-06-22). |
| [auphonic-integration-reference-chapterforge.md](auphonic-integration-reference-chapterforge.md) | Archived ChapterForge Auphonic design, kept as reference for growing QUILL's shipped Auphonic client. |
| [google-docs-drive-inbound-integration-points-2026-06-29.md](google-docs-drive-inbound-integration-points-2026-06-29.md) | Embed map for the on-hold read-only Google Docs/Drive integration. |
| [wordpress-inbound-embed-and-safety-review-2026-06-29.md](wordpress-inbound-embed-and-safety-review-2026-06-29.md) | Audit of the shipped WordPress inbound touchpoints and their safety posture. |

## Status: locked off (developer-only)

The feature ships **disabled** behind `future.publishing`, which is `locked_off=True`
in `quill/core/feature_catalog.py`. `FeatureManager.state_for()` returns `OFF` for a
locked-off feature before it consults any user override or active profile, so
`is_enabled("future.publishing")` is always False — a user cannot enable it via
profile, override, or the feature-toggle UI. Only a developer removing `locked_off`
in source can lift the gate. The File > Publish menu and all `publishing.*` commands
are gated on this flag (the command palette and Go to Anything exclude locked-off
features automatically).
