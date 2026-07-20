# Consolidating Quill Radio and Quill Cast into quill — safely

Date: 2026-07-20. Companion to the Audio Studio reverse-vendor
(`2026-07-17-audio-studio-migration-audit.md` §25) and the family architecture
(QUILL-PRD §35). This one is different from Audio Studio and must be handled
carefully, because **both wrapper products are already shipped and their
in-app updaters point at their own GitHub repos.**

## The critical constraint (why this is not like Audio Studio)

Audio Studio was safe to fold in and delete because it was **never shipped and
never pushed** — no users, no releases, no updater. Radio and Cast are the
opposite:

- **The code is already in quill.** `quill/apps/radio.py` and
  `quill/apps/podcasts.py` are the standalone frames; the feature code lives in
  `quill/` and is shared with embedded QUILL (`RadioMixin`, `PodcastsMixin`).
  The `quill-radio` / `quill-cast` repos are **thin wrappers only** (launcher,
  spec, installer, docs, a `quill @ tag` pin). There is no vendored code to
  merge — that part is already done.
- **Both are shipped.** quill-radio has published releases 2.0.2 → 2.1.2;
  quill-cast has published 1.0.0. Real users are running them.
- **The in-app updater polls each product's own repo.**
  `radio.py: _REPO = "Community-Access/quill-radio"`,
  `podcasts.py: _REPO = "Community-Access/quill-cast"`. Every installed copy
  calls `api.github.com/repos/<repo>/releases` to check for updates.

**Therefore: deleting either GitHub repo would 404 every existing user's update
check — breaking updates for everyone already on Radio or Cast.** The local
folder is re-clonable (it is on GitHub), but the *GitHub repo* is a live piece
of infrastructure users depend on. It cannot be abruptly removed.

## What "consolidation" actually means here

The valuable consolidation — one codebase, no drift — is **already achieved**:
the wrapper repos hold no code, only packaging. They cannot drift from quill
because they build `quill @ <pinned tag>`. So there is little left to do beyond
tidying, and one genuinely hard step (retiring the repos) that must be tiered.

## Tiered plan

### Tier 0 — tidy now (safe, no user impact) — DONE THIS PASS
1. **Move the open issues to quill**, where the code and every other radio/cast
   bug already live (feedback-hub already files "[Quill]" reports to quill).
   Transferred (GitHub leaves a redirect from the old numbers):
   - quill-radio #15 → **quill #1187** (weather: worldwide locations).
   - quill-radio #8 → **quill #1188** (jump cursor to radio list).
   - quill-cast #2 → **quill #1189** (episodes don't load after subscribe;
     wants tree-expand + shortcuts).
2. **Docs stay where they are.** Do *not* copy the product docs into quill:
   because Tier 1 keeps the wrapper repos, duplicating their user guides /
   changelogs / release notes into quill would create two diverging copies
   (drift) — the exact failure mode this consolidation exists to remove. The
   docs live in the wrapper repos next to the builds that ship them. (Only if a
   repo is ever *retired* under Tier 2 do its docs move to quill — at that
   point there is one copy, not two.)

### Tier 1 — the consolidated steady state (safe) — RECOMMENDED END STATE
Keep the `quill-radio` and `quill-cast` repos as **thin release-and-build
shells**: launcher + spec + installer + docs + `quill @ tag` pin. They:
- host the GitHub releases users download and the updater polls,
- build the standalone products,
- cannot drift from quill (no code of their own).

This is the same shape as the target Audio Studio wrapper. There is nothing
unsafe here and nothing more that *needs* doing — the family is already one
codebase. Do **not** delete these repos in this tier.

### Tier 2 — retiring a wrapper repo (deferred; only if going QUILL-only)
Only pursue this if the decision is to stop shipping a standalone product and
make it QUILL-only. It is a **multi-release, multi-month migration**, never an
abrupt delete, because existing installs poll the old repo until they update:

1. **Repoint the updater** in quill: change `_REPO` to a repo that will persist
   (e.g. a single long-lived `Community-Access/quill-releases`, or the quill
   repo's own releases), and give the updater a small fallback that tries the
   new target and then the old.
2. **Ship one transitional release from the OLD repo** carrying that repointed
   updater, so users update once from where they are already pointed and their
   app then polls the new target.
3. **Publish all future releases at the new target.**
4. **Wait for adoption** (weeks/months). Late updaters still poll the old repo.
5. **Archive, do not delete, the old repo.** GitHub "Archive" keeps the
   releases and the API alive (no 404) while freezing the repo. Deleting it
   would break every user who has not yet updated — possibly forever.

Never skip 1–4. A deleted `/<repo>/releases` endpoint is an unrecoverable break
for anyone still pointed at it.

## Cast specifics
Cast is shipped (v1.0.0) but carries the version-chaos and libmpv-staging issues
noted in the audit (Tier 2 item 10 there). Before any Cast repo action, land the
Cast 1.0.x housekeeping in quill (`apps/podcasts.py` `_VERSION`, installer
AppVersion + VersionInfoVersion, changelog, libmpv staging). Same updater
constraint as Radio.

## Recommendation
Do **Tier 0** now (issues + docs to quill — done this pass). Adopt **Tier 1** as
the steady state: one codebase, thin release shells, no drift, updates intact.
Treat **Tier 2** (deleting a repo) as a deliberate, migration-gated project, not
a cleanup — and even then, *archive* rather than delete, so no user's update
check ever 404s.
