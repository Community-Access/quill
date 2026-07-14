# Sync Engine History: why QUILL Sync reuses infrastructure instead of building one

Canonical engineering record, written 2026-07-12 as part of shipping "QUILL
Sync" for 0.9.0 Beta 3. It preserves the reasoning behind a deliberate,
considered decision: build the large custom sync engine described in the
retired `docs/planning/quill-sync-plan.md` (recoverable from git history), or
reuse infrastructure that already exists and is already trusted. QUILL chose
reuse.

## The outcome (what ships)

**"QUILL Sync" is two small, honest features, not one large service:**

1. **Sync via a folder (local or cloud).** `quill/core/data_location.py`
   already let a user relocate QUILL's entire settings/snippets/dictionaries/
   keymap directory to any folder they choose — this shipped in an earlier
   release (#615) for a different reason (letting people keep QUILL's data
   off the system drive) and turns out to already be exactly the mechanism a
   lightweight sync story needs: point that folder at one already mirrored by
   OneDrive, Dropbox, Google Drive, iCloud, a NAS share, or a USB drive, and
   QUILL's data travels with it. Nothing new was built here beyond
   documentation and framing (the wizard's "Data Location" page, the user
   guide, and the PRD now describe this explicitly as a sync strategy, with
   the honest caveat that QUILL has no cross-device conflict resolution — do
   not run QUILL from two devices against the same folder at once).
2. **Sync Folder with GitHub, generalized.** Accessible Vault's "Sync Vault"
   (`quill/core/vault/sync.py::run_vault_sync`) already implements
   commit/pull/push over a user's own git remote, with conflicts surfaced as
   a spoken, itemized list rather than a silent auto-merge — and it turns out
   to have zero Vault-specific logic in it at all. `quill/core/git_sync.py`
   gives that exact engine a general-purpose, non-Vault-branded home (plus
   two small pieces Vault didn't need: checking whether a folder is even a
   git repository with a remote yet, and setting one up when it isn't), and
   `quill/ui/main_frame_git_sync.py` wires it to **Tools > Sync Folder with
   GitHub...** — any folder, not just a Vault.

Both rely entirely on infrastructure QUILL already shipped and trusted:
`data_location.py`'s relocation mechanism, and the exact git commit/pull/push
implementation Vault Sync already used in production. There is exactly one
git-sync engine in the tree, not two.

## The road not taken, and why it stays not taken

`docs/planning/quill-sync-plan.md` (2026-07-04, retired 2026-07-12) designed
a full QUILL-native sync service: a `quill/core/sync/` engine with its own
SQLite state store and content-addressed version history, a `SyncAdapter`
interface, and per-provider OAuth adapters for OneDrive (Microsoft Graph),
Dropbox, and Google Drive (plus a GitHub "advanced mode" adapter), a Sync
Center dialog, a first-run wizard, and a six-phase, multi-release rollout —
each provider needing its own app registration, consent-screen verification,
and long external lead times (Google's OAuth verification review alone was
flagged as "the single longest external lead time in the plan").

That design was not wrong on its own terms — it is a careful, thorough,
accessibility-first spec for what a *first-class, QUILL-branded* sync product
would need. It was explicitly decided against for 0.9.0 Beta 3, on a direct
instruction: **"we will not spin up our own sync process."** The reasoning
that decision made explicit:

- **A folder is already a solved sync problem.** OneDrive, Dropbox, Google
  Drive, and iCloud already replicate a folder's contents across devices,
  reliably, with their own conflict handling, at zero cost to QUILL in code,
  maintenance, or OAuth app registrations. QUILL relocating its data
  directory onto such a folder gets the same outcome as a purpose-built
  "Settings sync" adapter, for work already done.
- **Git is already a solved sync problem for structured, versioned content.**
  It has its own conflict detection, its own credential model (SSH keys, or
  the system's git credential manager), and its own remote-hosting options
  (GitHub being the obvious one, but not the only one). Building a parallel
  version-vector/conflict-resolution engine inside QUILL to do a worse
  version of what git already does well was the single largest piece of
  scope in the original plan (Layer 1: the Local Sync Engine, SQLite state,
  content-addressed blob store, version vectors, a journal) — cut entirely
  by reusing git instead.
- **No new OAuth surface, no new credential storage, no new external app
  registrations, no new long external lead times** (Google's verification
  review, Dropbox's production-approval process) — all avoided, because
  QUILL never becomes a client of any cloud provider's API.

The multi-provider OAuth adapter layer, the SQLite-backed version-vector
engine, the Sync Center dialog, and the phased six-release rollout remain
undone **by decision, not oversight.** If a first-class QUILL-branded sync
product with per-provider App Folder scopes, encrypted recovery, and a phone
companion is ever pursued, the analysis in `quill-sync-plan.md`'s prior git
history is the place to resume from — but nothing in the shipped 0.9.0 Beta 3
"QUILL Sync" depends on it, and Beta 3 does not build toward it.
