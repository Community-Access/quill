# Google Docs and Drive: Inbound Integration Points

Date: 2026-06-29
Source of record: `docs/planning/QUILL-Native-Google-Docs-Support-PRD.md`
Scope: Identify exactly where the inbound (read-only) Google integration
touchpoints embed in QUILL - connect an account, list/open Drive documents, and
load a Google Doc into the editor - and explicitly fence off every content-send
path until separately approved.

This is a design and embed map only. No code is added and nothing is lit up.
Building real OAuth + Drive + Docs network code is deliberately out of scope for
this pass because it cannot be exercised safely or tested unattended, and because
the standing instruction is to not light up sending content to Google.

## 1. In scope vs out of scope for the inbound pass

In scope (read-only):

- Connect / switch / disconnect a Google account (OAuth, read scopes only).
- List authorized Google documents (Drive Picker, recent, or pasted URL/ID).
- Open a Google Doc as a text-first projection into the QUILL editor.
- Open the current document in Google Docs (web) - a navigation action, not a
  write.

Out of scope for now (all are content-send / mutation; defer behind a separate
approval, mirroring how WordPress send stays locked):

- New Google Document (PRD 8.1, 9.5).
- Save a Copy to Google Drive (PRD 9.1).
- Synchronize Now / autosave writes / Update / Repair Synchronization (PRD 9.2).
- Comment/suggestion creation or resolution (PRD 5, Level B).

## 2. Why this is its own subsystem, not a publishing provider

The WordPress provider is a REST + application-password model that fits the
`publishing_providers` framework. Google Docs is materially different:

- OAuth 2.0 with the system browser and a token store, not a static secret.
- Google Drive for listing/Picker and Google Docs API for the document model.
- A provider-independent semantic document model and a text-first projection
  (PRD sections 7, 10, 11), not HTML or Markdown round-tripping.

So Google should be a sibling subsystem with its own File-menu surface and its
own feature flag, reusing QUILL's cross-cutting primitives (command registry,
feature gating, credential storage, egress audit, task manager) rather than the
`PublishingProviderClient` contract.

## 3. Feature gating (proposed)

- Add `future.google_docs` to `quill/core/feature_catalog.py` with
  `locked_off=True`, `privacy="network after confirmation"`, category `future` -
  exactly mirroring `future.publishing`. While locked off, the menu is omitted
  and the palette filters the commands.
- Map every `google.*` command to `future.google_docs` in
  `quill/core/feature_command_map.py`, so a locked flag keeps them unreachable
  (the same mechanism that keeps `publishing.*` dark today).

## 4. Inbound command and menu embed map

Per PRD 9.1, add a File submenu (built only when `future.google_docs` is
enabled), with handlers registered in the command registry alongside the
existing `publishing.*` block in `quill/ui/main_frame.py`:

- `google.connect_account` -> Connect / Switch / Manage / Disconnect account.
  Read-only OAuth consent in the system browser; token stored via the same
  credential path used by publishing secrets (Windows Credential Manager, DPAPI
  fallback). New core module suggestion: `quill/core/google_auth.py`.
- `google.open_from_drive` -> Google Picker in the default browser, returns a
  document id; loads read-only. Network listing only.
- `google.open_from_link` -> Paste a Google Docs URL or id; validate, extract id,
  check access, open read-only or launch authorization (PRD 9.4).
- `google.recent_documents` -> Previously authorized docs (local, no network
  until open).
- `google.open_in_browser` -> Open the current cloud doc in Google Docs (web).

Out-of-scope commands (`google.new_document`, `google.save_copy_to_drive`,
`google.sync_now`, `google.refresh`, ...) are intentionally not registered in
this pass. When they are, they must land behind the send approval, never as part
of the inbound surface.

## 5. Load-into-editor flow (mirrors the WordPress inbound shape)

1. `google.open_from_*` resolves an account + document id.
2. A new core module (suggested `quill/core/google_docs.py`) fetches the Docs API
   document and maps it to QUILL's semantic model, then projects to text-first
   content (PRD 10, 11). For a first inbound slice this can be a lossy but safe
   read-only projection; unsupported objects are preserved as labeled markers.
3. The UI wraps the projection in a `Document` with
   `source_metadata["source_kind"] = "google_doc"` plus account, file id,
   revision id, and permission level - the analogue of the `publishing_remote`
   metadata in `_browse_publishing_content`.
4. Open as a new tab via `_create_document_tab`. Title bar shows the read-only
   state form from PRD 9.3 (for example `... - Google Docs - Read only`).

Because step 2 is read-only, no `requiredRevisionId`/`targetRevisionId` write
path is created. The shadow snapshot and operation journal described in the PRD
belong to the later sync (send) phase and are not built here.

## 6. Safety requirements for the eventual implementation

- OAuth scopes must be the minimum read scopes for the inbound slice; request
  write scopes only when the send phase is approved.
- Reuse `verified_ssl_context()` for every Google endpoint.
- Register each Google network call site in `quill/tools/network_egress_audit.py`
  (GATE-9) before it ships.
- Store only OAuth tokens via the OS credential store; never store Google
  passwords (PRD 5 non-goal) and never log tokens (respect
  `quill/stability/redaction.py`).
- Gate the whole subsystem under Safe Mode in addition to the feature flag, since
  it is a network + credential feature.

## 7. Suggested first slice (when approved)

1. `future.google_docs` flag (locked off) + command-to-feature mapping.
2. `quill/core/google_auth.py`: OAuth connect/disconnect with read scopes, token
   in credential store, egress entry. No document operations yet.
3. `quill/core/google_docs.py`: open-by-id read-only -> semantic model ->
   text-first projection; wx-free and strict-typed.
4. UI: `google.connect_account`, `google.open_from_link`, and the read-only open
   into a tab; menu built only when the flag is enabled.

Send (new/save-copy/sync) remains a separate, later, explicitly approved phase.
