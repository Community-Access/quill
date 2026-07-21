# QUILL Social architecture (P0 slice)

This document maps the code to the PRD's layered design (section 29) and records
the decisions that matter for future work.

## Layers

```
wxPython presentation            quill_social/ui/
        |
commands, view logic             quill_social/ui/{app,commands,composer}.py
        |
domain services                  quill_social/services/
        |
network adapters                 quill_social/adapters/
        |
model + capabilities + store     quill_social/{model,capabilities,db}.py
        |
OS data dir (+ future keystore)  quill_social/paths.py
```

Everything below the UI is **wx-free** and unit-tested headlessly. The UI is a
thin layer: it renders items, routes keystrokes to commands, and speaks state.

## Key decisions

- **Capability detection before assumption.** Nothing branches on a network
  name. The UI and composer ask the `CapabilityRegistry`, which is seeded per
  network and refined by a live server probe. Two Mastodon servers can differ.

- **The mock network is a first-class adapter.** `MockNetwork` is the reference
  implementation of `NetworkAdapter` and the thing the shell drives out of the
  box. It makes the whole app runnable and testable with no credentials, which
  is exactly the PRD's recommended MVP posture (section 42).

- **Local state survives re-fetch.** `SocialStore.upsert_item` dedupes on
  `(network, account_id, remote_id)` and preserves read/flag/folder state, so a
  background refresh never marks a read post unread or drops a filed post.

- **One publication plan per account.** A cross-network draft produces one plan
  per target, so a failure on one destination never blocks or duplicates the
  others (PRD 39.3). The scheduler is a pure state machine; the store just
  persists it.

- **Pause, don't shred.** The thread publisher stops on the first failure and
  hands back a repair plan with the last good parent id and per-segment
  idempotency keys, so a resumed run reconnects the chain without duplicating.

- **Text before everything.** The field reader and Where Am I produce the exact
  strings that are spoken and shown. Read state, media state, and moderation
  labels are always available as text; color is only ever a secondary cue.

## Where the boundaries are

- `adapters/mastodon.py` and `adapters/bluesky.py` ship capability descriptors
  and raise a clear `AdapterError` on any live call, with a `refine_from_*`
  method showing how a real probe sharpens the defaults. Wiring the live client
  means implementing the read/publish methods against a token resolved from the
  OS credential store — no schema or UI change required.

- Cloud scheduling, AI, GitHub, media playback, and QuilleSync have model and
  service seams but no implementation in this slice.

## Testing

`pytest` covers the model roundtrips, capability registry, persistence
(including re-fetch preservation and prune safety), the thread splitter's
boundary and protected-token behavior, the scheduler transition/backoff policy,
the thread publisher's pause/repair/idempotency, catch-up collapsing, composer
capability checks, smart-folder rules, fields, Where Am I, keymap, a11y, the
adapters, and the CLI. A guarded wx smoke test builds the full frame and
exercises navigation, field reading, Where Am I, and command construction; it
skips cleanly where wx cannot initialize.
