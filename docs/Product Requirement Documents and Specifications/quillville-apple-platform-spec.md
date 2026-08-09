# QuillVille Apple Platform Specification

**Scope:** The shared foundation for Quill Weather for iOS and Quill Radio for iOS -- and for every QuillVille app that follows them onto Apple platforms.
**Status:** Design of record, implementation-ready
**Version:** 1.0
**Date:** August 8, 2026
**Owns:** QuillKit (the shared Swift package), QuillNarrate and the narration golden corpus, QuillSync adoption, QuillPush, the shared accessibility contract, the Apple repository layout, and the cross-platform settings scope map.
**Consumed by:** `standalone/weather/docs/prd-ios.md`, `standalone/radio/docs/prd-ios.md`
**Supersedes, in scope:** the "we will not spin up our own sync process" position recorded in `docs/engineering/sync-engine-history.md` -- see §4.1, which adopts the existing QuillSync engine rather than building a new one, and does not reopen the retired multi-provider OAuth plan.

---

## 1. Why this document exists

Two iOS apps are being built at once, and they are the first two of several. If
each one invents its own settings store, its own sync, its own network policy,
and its own way of turning a number into a sentence, the ecosystem ends up with
four incompatible dialects of itself and a settings file that no longer round
trips between a desktop and a phone.

The Windows product avoided that by putting every portable thing in
`quill/core/*` -- wx-free, clock-free, network-free, strict-typed, and unit
tested. That decision is the reason an Apple port is tractable at all. This
document is the Apple-side equivalent of that decision, made once, up front.

It also answers the two ecosystem questions the iOS work raises and that no
existing document answers end to end:

1. **How do settings and identifications track either way** between a Windows
   desktop and an iPhone, with no account required and nothing readable by a
   server?
2. **What has to be added to the QUILL ecosystem** to make two excellent iOS
   apps possible without either app growing its own private infrastructure?

---

## 2. The Apple repository layout

```
apple/
  QuillKit/                 SwiftPM package, the shared foundation
    Sources/
      QuillCore/            models, settings, storage, error codes, paths
      QuillNarrate/         the narration port; the only place strings are built
      QuillNet/             the single audited HTTP chokepoint + provider clients
      QuillSyncKit/         QuillSync engine, crypto, transports
      QuillA11y/            the shared accessibility contract as reusable modifiers
      QuillWeatherKitAdapter/  WeatherKit -> shared model mapping (Weather only)
      QuillAudio/           AVAudioEngine graph, DSP, ICY tap (Radio only)
    Tests/
    Fixtures/               symlinked/synced golden corpora (see §3.3)
standalone/
  weather-ios/              app target, widgets, watch app, intents, tests
  radio-ios/                app target, widgets, watch app, CarPlay scene, intents, tests
```

- **AP-1.** `apple/` sits outside QUILL's Python CI gates -- the module size
  budget, the dialog inventory, the banned-pattern scan, and `mypy` do not
  apply -- and carries its own Swift CI, exactly as `standalone/radio-mac/`
  does today.
- **AP-2.** The network egress audit **does** apply. Every Swift call site is
  added to `quill/tools/network_egress_audit.py`'s inventory in the same change
  that introduces it, because the audit's purpose is to describe the ecosystem's
  total outbound surface, not one language's.
- **AP-3.** Documentation follows the standing per-product rule: every change is
  documented with the product it belongs to, at ship time, in that product's
  `CHANGELOG.md` and `docs/`, with the `.html` and `.epub` twins regenerated. A
  change to QuillKit that affects both apps gets an entry in both changelogs.
- **AP-4.** Zero third-party runtime dependencies in shipped app targets. The
  only exception permitted is a statically linked Ogg/Opus decoder for Quill
  Radio (its E-3), which must be audited and recorded in
  `docs/legal/THIRD_PARTY_NOTICES.md`.

---

## 3. QuillNarrate and the narration golden corpus

This is the most important section in the document.

### 3.1 The invariant being protected

The Windows weather renderer's module docstring states the product's whole
thesis: pure functions that produce warm, fully spelled-out sentences meant to be
read aloud -- "miles per hour", not "mph"; "west-northwest", not "WNW";
"degrees", not a symbol -- with no clock, no randomness, and no wx, so that
**speech and text share the same strings and can never drift apart**.

That invariant is worth more than any individual feature. If iOS reimplements
the phrasing, the two products slowly become two products. The user notices,
because the sentence they memorized on the desktop is not the sentence the phone
says.

### 3.2 The rule

- **NR-1.** `QuillNarrate` is a **parity port**, not a reimplementation. For any
  given input it produces the same string as its Python counterpart, character
  for character, including punctuation and spacing.
- **NR-2.** `QuillNarrate` is pure: no clock, no locale side effects, no
  randomness, no I/O. The current time is always injected, exactly as
  `render.time_summary(now, ...)` requires on Windows. This is what makes the
  parity test possible.
- **NR-3.** Every user-visible sentence in every Apple app comes from
  `QuillNarrate`. An app target that builds a sentence with string
  interpolation has introduced a dialect and fails review.
- **NR-4.** A wording change is a change to **both** implementations and to the
  corpus, in one commit. There is no "fix it on iOS first."

### 3.3 The corpus

- **NR-5.** `apple/QuillKit/Fixtures/narration/*.json` holds input/expected
  pairs: a serialized domain object and the exact expected output for each
  narrator function and each relevant settings combination. The same files live
  at `tests/fixtures/narration/` on the Python side, kept identical by a
  checked-in sync check that fails CI on divergence.
- **NR-6.** Both test suites iterate the corpus. Python's suite already has the
  behavior; the corpus makes it explicit and shareable.
- **NR-7.** Initial corpus coverage, drawn from the existing Windows tests and
  the acceptance document `docs/release/acceptance/app-weather.md` (858 lines of
  literal expected speech, which is effectively a corpus already):
  - Weather: `temp_phrase`, `wind_phrase` including the calm case, `uv_phrase`
    bands, `moon_phrase` in all four rise/set combinations, `air_quality_phrase`,
    `friendly_datetime`, `local_time_phrase`, `time_summary` in the
    different-zone, same-offset, and stale cases, `current_conditions_block`
    across every settings toggle, `quick_weather_line` with zero, one, and many
    alerts, `DailyOutlook.line`, `HourlyPeriod.line`, every alert list label and
    detail block, every monitor announcement template, and every degradation
    note string.
  - Radio: `display_label`, `details_text`, the now-playing template renderer
    across the `key="value"` and `Artist - Title` conventions and every
    `[optional]` segment case, recording start and stop announcements, the
    reconnect and buffering narrative, the DVR "behind live" phrasing, the
    schedule list line with time zones, and the `compact_braille` variants.

### 3.4 Where new wording comes from

- **NR-8.** iOS will produce sentences Windows cannot -- minute-by-minute
  precipitation, arrival narration, disagreement wording, Live Activity
  countdowns. Each new sentence is added to `QuillNarrate` **and** to
  `render.py` in the same change, even when the Windows app has no way to
  trigger it yet. The Python function exists, is tested, and is available the
  day Windows grows the capability. This is how the ecosystem stays one product.

---

## 4. QuillSync -- how settings and identifications track either way

### 4.1 Adopt, do not invent

The engine already exists and is complete: `quill/apps/beacon/quillsync/`
provides a git-like append-only commit log of AES-GCM encrypted,
content-addressed blobs under a scrypt-derived vault key, with a `Transport`
abstraction, a `RecordStore` protocol, pluggable merge functions, and tombstones
for deletes. Its own docstring names the intent: "Beacon, Quill settings, Quill
Radio stations, and Quill Cast episodes all use the same engine with their own
adapter and merge function." A reference server exists at
`standalone/beacon/server/`, with magic-link auth, per-device revocable tokens,
and a deliberately opaque hint endpoint.

- **SY-1.** No new sync engine is written. The standing decision in
  `docs/engineering/sync-engine-history.md` -- that QUILL will not build its own
  sync process -- is honored in substance: this is adoption of an engine that
  already exists in the tree, not a new one, and it does not revive the retired
  multi-provider OAuth plan.
- **SY-2.** **Promotion is a prerequisite.** QuillSync moves from
  `quill/apps/beacon/quillsync/` to `quill/core/sync/`, with a re-export shim
  left behind for Beacon. No non-Beacon app can adopt it cleanly while it is
  namespaced under one app, and the Beacon docs already assume the promotion has
  happened.

### 4.2 The three transports

All three carry the **identical** encrypted commit log, so a user can switch
transports, or run more than one, without re-pairing or losing history.

| Tier | Transport | Server | Why it exists |
|---|---|---|---|
| T1 | **iCloud Drive folder** (the app's ubiquity container) | None | Default on Apple devices. Because iCloud Drive is also available on Windows, this gives full Windows-to-iPhone sync **with no QUILL infrastructure at all** |
| T2 | **Any folder** -- OneDrive, Dropbox, Syncthing, a network share, a USB stick | None | The existing `FolderTransport`, unchanged. Already works on Windows today |
| T3 | **QuillSync server** -- magic link, per-device revocable token | Yes | For users with no cloud drive, and the only tier that can deliver a push hint |

- **SY-3.** T1 is the recommended default because it is zero-configuration on
  Apple devices, requires no account with QUILL, and is the transport most
  likely to already be working on both of a user's machines.
- **SY-4.** T1 and T2 are the same code path -- a directory of `commits/*.json`
  and `objects/<sha256>` -- so the iCloud tier is a coordinated-file-access
  wrapper over the existing transport, not a new implementation.
- **SY-5.** T3 remains optional forever. **Nothing in either iOS app requires an
  account.** A user who never signs in to anything gets every feature except
  push-hint latency.

### 4.3 Cross-language wire-format parity

- **SY-6.** Swift `QuillSyncKit` and Python `quill/core/sync/` must interoperate
  byte for byte:
  - Key derivation: scrypt, N = 2^15, r = 8, p = 1, 32-byte key, salt and KDF
    parameters stored in the envelope, never the key.
  - Content encryption: AES-GCM, 12-byte nonce, AAD `quillsync:dek`, per-object
    data-encryption keys wrapped by the vault key.
  - Addressing: SHA-256 over the plaintext object.
  - Commit log: the existing `log.jsonl` shape with parent ordering and
    tombstones.
- **SY-7.** A **cross-language fixture test** is checked in and run by both CI
  suites: a vault and a set of commits produced by the Python implementation
  must decrypt and merge correctly in Swift, and the reverse. A change to either
  side that breaks it fails both builds.
- **SY-8.** CryptoKit provides AES-GCM and SHA-256 natively. scrypt is not in
  CryptoKit; the Swift side uses a small, audited, statically linked scrypt
  implementation, recorded in the third-party notices, with test vectors pinned
  against the Python output.
- **SY-9.** The vault key lives in the iOS Keychain with
  `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`. It is never written to the
  log, never sent to any server, never included in a device backup that travels,
  and never derivable from anything the server holds. Losing it costs sync, not
  data -- local data is always intact and always readable.

### 4.4 The settings scope map

Every setting in the ecosystem is classified into exactly one of three scopes.
This map is the contract; an unclassified setting does not sync.

| Scope | Meaning | Entity id prefix |
|---|---|---|
| `shared` | The user's decisions, portable across every device and platform | `shared/...` |
| `device` | Real settings that are meaningless or harmful elsewhere -- audio routes, file paths, per-device enable flags, notification grants | `device/<device-id>/...` |
| `local` | Never leaves the machine under any circumstance -- secrets, location fixes, caches, DPAPI- or Keychain-protected material | not in the log |

- **SY-10.** Secrets are `local` by construction. Windows DPAPI blobs are
  machine-and-user scoped and cannot be decrypted elsewhere; Keychain items are
  device-only by policy. Neither is ever placed in the sync log, and the
  existing separate-file storage for secrets is what makes this easy.
- **SY-11.** Location fixes, travel history, and any derived movement data are
  `local` and additionally have an explicit one-action erase. This is a privacy
  floor, not a default.
- **SY-12.** Identifier stability is a prerequisite for merging. Both platforms
  move to **UUIDs** for saved locations and favorites, accepting the legacy
  sequential `loc_N` and integer favorite ids on read forever. Two devices
  adding an entity independently must not collide, and sequential ids collide by
  design.
- **SY-13.** Merge policy: field-level last-writer-wins on scalars; union merge
  on lists that are sets in spirit (muted alert events, location groups,
  favorites, folder paths) using the existing `merge.union_lists`; a real
  conflict -- removed here, edited there -- surfaces as a single user-resolvable
  item whose resolution is spoken, never a silent pick.
- **SY-14.** The per-app scope tables live in each app's iOS PRD (Quill Weather
  §11, Quill Radio §7) and are normative. This document owns the classification
  rules; the apps own their key lists.

### 4.5 What Windows has to gain

Sync is only bidirectional if the desktop is a peer, so the Windows side is part
of this work, not a follow-on:

- **SY-15.** A `SettingsRecordStore` adapter and a `settings_merge` function for
  QUILL's own settings, as already specified in
  `standalone/beacon/docs/PLAN-quillsync-integration.md`.
- **SY-16.** A `WeatherRecordStore` over `weather_locations.json` and
  `weather_settings.json`, and a `RadioRecordStore` over `radio_favorites.json`
  and the radio history/settings record.
- **SY-17.** A sync surface in the Windows apps: enable, choose a transport,
  pair, sync now, view status, resolve a conflict -- all through the existing
  dialog contract and the existing announcement service, so it is accessible by
  construction.
- **SY-18.** Sequencing: **Quill Radio favorites are the pilot surface**, as the
  Beacon plan already recommends. They are self-contained, high-value, easy to
  verify by ear, and a merge bug is recoverable. Weather locations follow, then
  QUILL preferences.

---

## 5. QuillPush -- the only new service

### 5.1 Why it is needed

The Windows product approximates push with a 30-second poll while an alert is
active, and its own PRD records the NWWS relay as evaluated and deferred because
it needed per-user credentials for a marginal gain. On iOS the calculus is
different in two ways: a phone cannot poll while it is asleep, and a phone is
the device that is with the user when the tornado warning is issued. Push is not
an optimization here; it is the feature.

### 5.2 The privacy-preserving design

- **PU-1.** The device registers only `(APNs device token, a list of NWS zone or
  SAME codes, a minimum tier)`. No account, no email, no coordinates, no
  identifier that outlives an uninstall.
- **PU-2.** Zone codes are derived **on the device** from the saved location's
  already-cached NWS metadata. The relay never receives a coordinate and never
  learns where anyone is -- only which of roughly four thousand public zones a
  token cares about, which is the same information a NOAA Weather Radio receiver
  broadcasts to the room.
- **PU-3.** The push payload carries the alert id, the zone, and the tier. The
  **full alert text is fetched from NWS by the device.** The relay is therefore
  never a source of truth for alert content and cannot inject a fabricated
  warning body, which is the property that matters for a safety product.
- **PU-4.** The relay retains no message history and no per-device log beyond
  what APNs delivery requires. Tokens expire and are pruned.
- **PU-5.** Registration is opt-in, explained in one plain-language screen before
  any token is sent, and revocable in one action. With push off the app degrades
  to background refresh, foreground polling, and manual refresh, and says so.
- **PU-6.** The relay is the **only** QUILL-operated service either iOS app
  talks to. It is inventoried in the network egress audit and disabled by
  Offline Mode.

### 5.3 Shape

- **PU-7.** One process polls NWS alerts once per zone-set per interval -- the
  cost is dominated by the NWS poll, not by fan-out, so it scales with the
  number of zones (fixed) rather than the number of users. It follows the
  hosting pattern already established by `quill-ai-gateway`.
- **PU-8.** Later, the same relay can front NWWS-OI for sub-ten-second latency
  without changing the client contract, which is what the Windows PRD's §17
  always intended.
- **PU-9.** Quill Radio does not use QuillPush. It has nothing to push.

---

## 6. The shared accessibility contract

`QuillA11y` exists so the contract is code, not prose that each app re-reads.

- **AX-1.** Reusable modifiers for the recurring patterns: the parity label
  (label equals displayed text), the concise-label swap with full text in Custom
  Content, the priority-mapped announcement, the "remove from the tree when
  empty" wrapper, the sorted reading order, and the standard custom-action sets.
- **AX-2.** The announcement policy port -- priority mapping, the two-second
  identical-message dedupe, and the burst coalescer with its 150-millisecond
  settle and its error exemption -- lives here once. Both apps get identical
  announcement behavior because they share the implementation, not because they
  each remembered.
- **AX-3.** The **Custom Content** convention is shared: provenance
  (`Source`, `Observed`, `Also reported`, `Confidence`) on any fact-bearing
  element, and full text behind a concise label. Both apps use the same category
  names so a user learns the rotor once.
- **AX-4.** The audit gate is shared: `performAccessibilityAudit()` on every
  screen in both apps, blocking CI. This is the Apple-side equivalent of the
  dialog inventory and dialog button contract gates.
- **AX-5.** The scripted VoiceOver release run is a shared checklist with
  per-app sections, performed with the screen curtain on, and its results are
  recorded in `docs/release/acceptance/` alongside the existing Windows
  acceptance documents.
- **AX-6.** A shared **accessibility statement** ships in both apps and in
  `docs/legal/`, naming what works, what is known-limited (Quill Radio's §13),
  and how to report a defect.

---

## 7. Shared network policy

- **NW-1.** One chokepoint per platform, mirroring `quill/core/weather/_http.py`:
  HTTPS only with a hard failure on any other scheme, the system trust store, a
  fixed timeout, an identifying User-Agent, conditional requests with ETag and
  Last-Modified, `Retry-After` honored, and exponential backoff with jitter.
- **NW-2.** Client-side rate limiting per destination, configured per provider.
  The desktop app never needed this; an App Store install base does, and the
  directories that are free and keyless deserve to stay that way.
- **NW-3.** A shared response cache keyed by URL and validator, shared across
  the app, its widgets, its watch app, and its extensions through the App Group
  container. Widgets must never multiply provider call counts.
- **NW-4.** **Offline Mode** -- the `QUILL_SAFE_MODE` analogue -- is implemented
  in the chokepoint, so a single switch disables every network surface in both
  apps and no individual call site can forget to check it.
- **NW-5.** No App Transport Security exceptions in either app.
- **NW-6.** Every destination is listed, in plain language and with what it
  receives, in an in-app privacy screen, in the Privacy Manifest, and in the
  ecosystem network egress audit.

---

## 8. Shared conventions carried over from the Windows product

These are non-negotiables that already govern the ecosystem and continue to:

- **CV-1.** Atomic writes for every persisted JSON file -- write to a temporary
  file, then replace. A partially written favorites file is unacceptable.
- **CV-2.** Defensive load: a wrong-typed key keeps its default, an unparseable
  record is dropped rather than crashing the app, and a corrupt file yields
  defaults with a spoken notice. Absence is never an error.
- **CV-3.** Every custom error type is coded
  `QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>`, matching its Python sibling where one
  exists, so a user's report is actionable across platforms.
- **CV-4.** No telemetry, no analytics, no tracking, no advertising identifier,
  in any app, ever.
- **CV-5.** Diagnostics are generated on request, shown to the user in full,
  redacted through the ported redaction rules, and transmitted only by an
  explicit user action.
- **CV-6.** Naming follows the family exactly: **Quill Radio**, **Quill
  Weather** -- matching `quill/core/app_launcher.py`, which is the single source
  of truth for product names.
- **CV-7.** Licensing is MIT, with `NOTICE` and the third-party notices carried
  into the app bundles.

---

## 9. What this adds to the QUILL ecosystem

A concise list of the work this specification creates outside the two app
targets, so it can be scheduled rather than discovered:

1. **Promote QuillSync** from `quill/apps/beacon/quillsync/` to
   `quill/core/sync/`, with a Beacon re-export shim (SY-2).
2. **Write three Windows record-store adapters** -- settings, weather, radio --
   plus their merge functions (SY-15, SY-16).
3. **Build a Windows sync UI** through the existing dialog contract (SY-17).
4. **Add UUID identifiers** to `WeatherLocation` and `FavoriteStation`, with
   legacy id acceptance forever (SY-12).
5. **Extract the narration golden corpus** from the existing tests and the
   weather acceptance document, and add the sync check that keeps the Python and
   Swift copies identical (NR-5, NR-6).
6. **Back-port the unit extensions** the iOS work adds -- pressure and
   visibility units -- and any new sentence iOS invents (NR-8).
7. **Add conditional HTTP, backoff, last-good caching, and staleness marking**
   to the Windows weather client, which its own PRD requires and which the
   corpus will now assert.
8. **Replace Nominatim** in the Windows geocoder with a compliant alternative;
   its public endpoint's usage policy does not permit a distributed application
   to use it the way the app does today. This is a live compliance issue that
   the iOS work surfaced.
9. **Add client-side rate limiting** to the shared directory clients (NW-2).
10. **Build QuillPush** (§5).
11. **Extend the network egress audit** to inventory Swift call sites (AP-2).
12. **Add Swift CI** -- build, test, the accessibility audit, and the two
    cross-language fixture tests (narration and sync).
13. **Update `docs/legal/PRIVACY.md`** for QuillPush, iCloud transport, and the
    Apple provider set, and add the shared accessibility statement (AX-6).

Items 1 through 4 and 10 are the only genuinely new infrastructure. Everything
else is either a port, a gate, or a correction to something already known to be
wrong.

---

## 10. Sequencing across the two apps

The two apps share Phase 1, diverge through the middle, and converge again on
sync. This ordering is chosen so that each shared component is built once, by
whichever app needs it first, and is exercised by a real product before the
second app depends on it.

| Stage | Shared work | Quill Weather iOS | Quill Radio iOS |
|---|---|---|---|
| 1 | QuillCore, QuillNet, QuillNarrate + corpus, QuillA11y | Phase 1: locations, NWS, Weather Now, full VoiceOver | Phase 1: directories, favorites, Engine A, full VoiceOver |
| 2 | -- | Phase 2: WeatherKit, fusion, Audio Graphs | Phase 2: resolver ladder, QuillAudio, Sound Enhancements, DVR |
| 3 | App Intents and widget conventions | Phase 3: location, notifications, lifecycle, widgets | Phase 3: CarPlay, Siri, widgets, Live Activity |
| 4 | QuillPush | Phase 4: push | Phase 4: recording and timers |
| 5 | QuillSyncKit + Windows adapters + UUIDs | Phase 5: sync | Phase 5: sync (**pilot surface: favorites**) |
| 6 | Watch and Mac conventions | Phase 6 | Phase 6 |

- **SQ-1.** Stage 5 is where "settings and identifications track either way"
  actually lands, and it is deliberately late: the scope map cannot be written
  honestly until both apps have real settings, and a sync bug in an app nobody
  uses yet is a bug nobody finds.
- **SQ-2.** Quill Radio's favorites are the sync pilot for both platforms, per
  SY-18. Weather locations follow only after favorites have survived real use.

---

## 11. Open questions owned by this document

1. **scrypt in Swift** -- select and audit the implementation, pin test vectors
   against the Python output, and confirm the binary-size and cold-start cost of
   the N = 2^15 parameter set on an iPhone (SY-8).
2. **iCloud Drive as a commit-log transport** -- validate coordinated file
   access, conflict-file behavior, and eventual consistency against a directory
   of many small files written concurrently from Windows and iOS, before making
   T1 the default (SY-4).
3. **iCloud for Windows availability** in the user base -- confirm that the
   recommended default transport is actually reachable for the desktop users we
   expect to pair, and keep T2 prominently offered if it is not.
4. **QuillPush hosting** -- confirm the shape and steady-state cost against the
   `quill-ai-gateway` deployment pattern before building (PU-7).
5. **Corpus scope boundary** -- decide how much of the official NWS prose passes
   through the corpus. The abbreviation-widening transform must be asserted; the
   upstream bulletin text itself cannot be, since NWS controls it.
6. **Windows geocoder replacement** -- choose the compliant alternative for item
   8 of §9, balancing worldwide coverage against licensing and cost.
7. **Whether QUILL Cast, Audio Studio, and Beacon follow** onto iOS, and
   therefore how much of QuillKit should be generalized now versus later. The
   recommendation is to generalize nothing speculatively: build exactly what the
   two apps need, and extract further only when a third app arrives.

---

## 12. Related documents

- `standalone/weather/docs/prd-ios.md` -- Quill Weather for iOS
- `standalone/radio/docs/prd-ios.md` -- Quill Radio for iOS
- `standalone/weather/docs/prd.md` -- the authoritative weather domain spec
- `standalone/radio/docs/prd.md` -- the authoritative radio domain spec
- `standalone/beacon/docs/PRD.md` sections 45 and 46 -- the QuillSync framework spec
- `standalone/beacon/docs/PLAN-quillsync-integration.md` -- the adapter plan, including its iOS section
- `docs/engineering/sync-engine-history.md` -- the standing decision this document works within
- `standalone/radio-mac/docs/superpowers/specs/2026-07-16-quill-radio-mac-design.md` -- the macOS port design, whose data-directory and platform-shim decisions this document is consistent with
- `docs/release/acceptance/app-weather.md` -- the existing literal-speech acceptance document that seeds the narration corpus
