# QuillVille shared runtime & component service — plan

Date: 2026-07-20. Builds on the family audit
(`2026-07-17-audio-studio-migration-audit.md`, §15–25) and the consolidation
program (`2026-07-20-quillville-consolidation-program.md`). The audit's §22
recommended **build-time sharing only** (each app ships its own frozen `quill`
off a pinned tag) and explicitly parked **runtime sharing** as "real
engineering." The owner has since chosen **Option A — a shared runtime** all
apps resolve at launch and register their components against. This document is
that engineering: how to build it so nothing is stored twice where sharing is
safe, while still letting people install only the apps they want, across every
install mode.

## 0. The finished system, in plain English (the outcome when complete)

This section describes what the world looks like when the plan is done, for a
non-engineer reader. Everything below is the *destination*; the numbered
sections after it are how we get there.

### What a person actually experiences

**Installing one app.** You download "Quill Radio," run the installer, and click
through it once. Behind the scenes it lays down a shared **QuillVille Runtime**
(the Python engine + the common code, installed one time for the whole family)
and the Radio app itself, and it fetches the small audio tools Radio needs.
Radio opens and works. Basic playback and recording work even with no internet.

**Adding a second app.** Later you download "Quill Cast." Its installer notices
the QuillVille Runtime is already on your machine, so it **doesn't install
Python or the shared code again** — it just adds Cast and the few extra pieces
only Cast needs. The download and install are small and quick. You now have two
apps sharing one engine and one set of components.

**Getting the whole suite.** Alternatively you run the single "QuillVille"
installer, which shows every app as a checkbox. Tick the ones you want. They all
share the one runtime and one component store. You can come back and add or
remove apps anytime; nothing is ever installed twice.

**Portable (on a USB stick).** You download the portable version, unzip it to a
stick, and run it on any Windows PC — including one that has nothing installed.
It carries its own copy of everything and leaves nothing behind on the host
machine. A portable copy is deliberately self-contained: it trades disk space
for the freedom to run anywhere. **If you want several apps on one stick**, use
the portable *suite* folder and add apps into it — the apps in that one folder
share a single engine and a single set of components on the stick, just like a
normal install shares them on a PC. What you cannot do is make two *separate*
portable copies (different folders or different sticks) share with each other —
each one is self-contained by design, so each carries its own.

**Offline (no internet, ever).** For places with no reliable connection, the
"Offline" installer and the "Offline portable" zip come with every engine and
voice already inside them. Nothing is downloaded, at install or in use.

**Updates.** Each app updates itself on its own schedule. When the shared engine
gets a fix, every app built for that generation of the suite picks it up at once
— safely, because a new generation of the engine installs *next to* the old one
rather than replacing it, so updating one app can never break another.

**Uninstalling.** Removing one app leaves the others working perfectly. Any
components that only that app used are cleaned up (or kept, your choice);
anything the remaining apps still need is left alone. The shared runtime stays
until you remove the last app in the family.

### How packages and installers work

- **One shared Runtime, installed once.** The Python engine and the common
  `quill` code live in one place and are shared by every installed app. Apps are
  thin: they find and use the runtime rather than each carrying their own.
- **App installers are small.** They add the app, tell the system which shared
  runtime generation and which components they need, and reuse whatever is
  already present.
- **Two flavours of every build, by design.** *Standard/Lean* is a small
  install that downloads the big optional pieces (neural voices, transcription
  engines) the first time you use them. *Offline/Full* is a bigger, additive
  build with all of those pieces already inside, for no-internet use. Portable
  and installed versions both come in Lean and Offline flavours — four
  combinations from one payload.
- **Every download is verified.** All optional components come from one signed
  catalogue that records each file's exact fingerprint and size. A download is
  only used if its fingerprint and signature match; a corrupted or tampered file
  is refused, never run.

### How the code is laid out

- **`quill/` — one repository, the single source of truth.** The shared engine
  (`quill/core`), the shared interface pieces (`quill/ui`), and every app side
  by side under `quill/apps/` (radio, podcasts/Cast, studio/Audio Studio,
  beacon, and later social). The component-download service lives in the shared
  core, so every app downloads things the same audited way.
- **`standalone/<app>/` — the packaging for each product.** A thin launcher, the
  build recipe, the installer script, and the docs for each shippable app. The
  launcher's job is to find the shared runtime and hand off to the app.
- **The Runtime build** — the embeddable Python + the pinned shared code,
  produced as one artifact and laid down once per machine.
- **The small "release" repos** (quill-radio, quill-cast, …) hold only the
  published downloads and drive the in-app updater; they carry no code.

### The failsafe guarantees (the promises the finished system keeps)

These are the invariants the design is built to guarantee, in plain terms:

1. **One app can never break another.** A new generation of the shared engine is
   installed alongside the old one, and each app states which generation it
   needs, so upgrading or installing one app cannot change the engine another
   app relies on.
2. **Your settings are never silently lost or downgraded.** When any app writes
   a shared settings file it keeps fields it doesn't recognise (written by a
   newer app), only rewrites old-format files, and stamps who wrote last — so an
   older app can't quietly erase a newer app's preferences.
3. **Nothing runs unverified.** Every downloaded component is checked against a
   signed catalogue (fingerprint + signature) before it is used; a bad file is
   refused, not executed.
4. **It always works offline when it must.** Anything already downloaded, or
   staged inside an Offline build, is used without touching the network; a
   missing optional piece produces a clear, guided prompt, never a crash or a
   spurious error.
5. **Portable means portable.** A portable copy runs on a machine with nothing
   installed and leaves nothing behind — it never depends on, or writes to, the
   host machine's shared install.
6. **Uninstall is clean and safe.** Removing an app never breaks a sibling and
   never orphans a component another app still needs; the shared runtime is only
   removed when the last family app is gone.
7. **Nothing is stored twice where it can be shared.** On a given machine, all
   installed apps share one runtime and one component store; the only duplication
   is the intentional self-containment of portable copies.
8. **Builds are reproducible and updates never strand a user.** Each app is built
   against an exact pinned version of the shared code, and a shipped product's
   update source is never deleted out from under existing users (it is archived,
   not removed), so "check for updates" never breaks.

## 1. What is already done (extracted from the audit + shipped since)

**Code consolidation — done.** All family apps now live in the one `quill`
package as the source of truth: `quill.apps.radio`, `quill.apps.podcasts`
(Cast), `quill.apps.studio` (Audio Studio, reverse-vendored), and
`quill.apps.beacon` (vendored + GATE-green this week). The wx-free `quill/core`
seams (player, recorder, speech, publish, versioned-store) are the shared API
line. QRM (macOS radio) and Social remain to reverse-vendor.

**Heavy assets already runtime-share — done, and it works.** ffmpeg, libmpv,
engine packs, neural voices, and models all resolve to **one** location,
`%APPDATA%\Quill`, used by every installed app:
- `ffmpeg_install.py: managed_ffmpeg_dir()` → `%APPDATA%\Quill\tools\ffmpeg`
- libmpv → `%APPDATA%\Quill\engine-packs\mpv`
- Piper voices → `%APPDATA%\Quill\speech\piper`, `\piper-models`
- whisper / vosk / kokoro models → the same tree
A component downloaded by one app is reused by all. **This is the single most
important fact: the disk-heavy sharing already exists.** What is *not* yet
shared is the Python runtime + the `quill` code (tens of MB), and there is no
registration/refcount layer so the store can't be GC'd safely.

**Packaging model that works — proven.** QUILL ships an **embeddable-Python +
pip** payload (`portable/*` with pip and a `wheels\` offline cache); on-demand
downloads run because pip is present. Two variants exist and are proven:
- **Standard = LEAN**: runtime + core + ffmpeg/mpv, downloads engines/voices on
  demand (`engine_install.py` already looks in `{app}\wheels\<name>` then the
  network). Small.
- **Offline = FULL**: same payload plus a staged wheelhouse
  (`wheels\kokoro|faster-whisper|vosk|mp3`) + engine binaries, for no-internet
  use. Additive superset of LEAN.
Portable zip = payload **with** `data\` (portable mode); installer = same
payload **without** `data\` (installed → `%APPDATA%\Quill`). Radio/Cast today
use PyInstaller freezes (no pip); Audio Studio needs the embeddable payload
(pip) for engines and its installer switch is the audit's open build task.

**Data-contract groundwork — partly done.** `FAMILY-DATA.md` ownership map
exists; the shared-store downgrade risk (a newer app's `versioned_store`
rewrite dropping an older app's unknown fields) is **confirmed** (§17.1) and the
preserve-unknown-fields / rewrite-only-on-legacy / last-writer-stamp hardening
is designed but not yet all landed. **This is a hard prerequisite for a shared
runtime** — see §7.

## 2. What "the runtime" is — two shared things, refcounted

There are **two** distinct shared surfaces. Keep them separate; they have
different sharing rules.

1. **The Runtime** = one installed copy of *{embeddable Python + pip + the
   `quill` package}*, pinned to a **QuillVille suite major** (the compatibility
   anchor from §23). Apps become thin launchers that resolve a compatible
   runtime at startup instead of each freezing their own copy.
2. **The Component Store** = `%APPDATA%\Quill` (ffmpeg, mpv, engine packs,
   voices, models). Already shared; this plan adds a **registration + refcount +
   signed-manifest** layer so it can dedup, verify, and garbage-collect safely.

Apps **register** against both: at install/first-run an app declares "I need
runtime ≥ suite-major N" and "I require components {ffmpeg, mpv, …}". The
runtime resolves, refcounts, downloads what is missing, and reuses what is
present.

## 3. The core principle — and the one law that constrains it

**Principle: store once wherever sharing is safe.** Two apps on the same machine
in system-install mode should share one Runtime and one Component Store.

**The law: portability ⊥ dedup.** A *portable* build (runs from a stick, no
install, leaves nothing on the host) is by definition **self-contained** — it
must carry its own runtime, components, and data so it works on a machine that
has nothing installed. Therefore a portable copy **cannot** dedup against a
system install or against another portable copy. Dedup is maximised in
system-install mode and is intentionally *absent* across portable copies. Any
plan that promises "store once" must state this boundary or it will over-promise.

The practical consequence: **dedup is a property of a *root*, not of the app.**
A root is a self-contained boundary that holds one runtime + one component store
+ one data store. For a system install the root is the machine
(`%LOCALAPPDATA%\QuillVille` + `%APPDATA%\Quill`); for a portable build the root
is the travelling folder. Apps sharing a root dedup; a root never reaches outside
itself.

**Multiple portable copies and sharing (the subtle case).** "Can several
portable apps share components?" depends entirely on whether they share a
portable *root*:
- **Same portable root → yes, they share.** A `QuillVille-Portable\` folder on a
  stick can hold several apps under one runtime + one component store; adding a
  second app to that same folder reuses everything and only stages its unique
  pieces. The folder as a whole is still self-contained and borrows nothing from
  the host, so the law holds. This is the portable analogue of the machine's
  shared runtime, and it is the supported way to get portable dedup.
- **Separate portable copies → no, they cannot share.** Two independently
  unzipped per-app portable bundles (different folders, or different sticks) are
  different roots; making one use the other's components would require reaching
  outside a self-contained root, which breaks "works on a bare machine / leaves
  nothing." Not allowed.

So the mechanism to share across portable apps is **one portable root with
multiple apps in it** (a "portable suite"), not several standalone portable
zips placed next to each other. The build produces a portable-suite unpacker
(pick apps into one root) alongside the single-app portable zips; a single-app
portable zip may also, on the *same* stick, detect an existing
`QuillVille-Portable\` root and install into it (same-root only, never the
host).

## 4. The shared Runtime — design

**Location & layout (system mode).** Per-user by default (no elevation), with an
optional all-users install to `%ProgramFiles%\QuillVille` for shared machines:
```
%LOCALAPPDATA%\QuillVille\        (or %ProgramFiles%\QuillVille if "all users")
  Runtime\<suite-major>\        one embeddable Python + pip + quill\ (pinned)
  Runtime\<suite-major>\wheels\ offline wheel cache (FULL variant only)
  Apps\<app>\                   thin launcher, icon, per-app metadata
  runtimes.json                 registry: installed runtimes + refcounts
```

**Side-by-side by suite major (the §22 safety answer).** Runtimes are keyed by
**suite major**, never overwritten in place. QuillVille 1 apps resolve
`Runtime\1`; a future QuillVille 2 lays down `Runtime\2` **alongside** it. An
app declares a **compat floor** (`min_suite_major`, and optionally a
`max_suite_major` it was tested against). This removes the compatibility-matrix
objection: upgrading the QuillVille-2 runtime can never break a QuillVille-1
app, because they are different runtimes on disk.

**Resolver (app launch).** The thin launcher: (1) reads its `min/max suite
major`; (2) finds the highest installed `Runtime\<major>` within range; (3)
exports `QUILL_APP_ROOT` + adds the runtime to `sys.path` / spawns the runtime's
python; (4) calls `quill.apps.<app>:main`. If no compatible runtime is present
(should not happen after install), it points the user at repair. This mirrors
the launcher shims already in `standalone/*/quill_*` — they become
runtime-resolving instead of self-contained.

**Refcount & GC.** `runtimes.json` records, per suite major, the set of
installed apps referencing it. Installing an app adds a ref; uninstalling
removes it; when a runtime's ref set is empty **and** it is not the newest, it
is eligible for GC (removed by the uninstaller or a maintenance pass). The
newest runtime is retained even at zero refs (fast re-install / repair).

**Per-app release flexibility (the §22 requirement).** An app still releases
independently: it bumps the runtime *tag* it pins within its suite major and
re-lays that runtime. A hotfix to one app never forces releasing the others.
Because runtimes are keyed by suite major (not by exact tag), a patch-level
runtime refresh replaces `Runtime\1` in place *only within the same suite
major*, and the data contract guarantees that is safe (§7). Cross-major is
always side-by-side.

## 5. The Component Store — registration, manifest, refcount

**One signed manifest (the §23 component service).** A single, signed
`components.json` in `quill/` (served from the update site, cached in the store)
is the source of truth for every downloadable: `{id, kind, url, sha256, size,
min_suite_major, provides, license}`. Verification (SHA-256 + signature) is
**mandatory**; downloads are resumable; the resolver is **offline-first** (see
§6). This replaces the three divergent per-app download vintages the audit
found (Radio/Cast/AS each rolled their own).

**Apps register requirements.** Each app declares the components it needs, split
into **required** (must be present to function — e.g. Radio requires `ffmpeg`,
`mpv`) and **optional/on-demand** (Kokoro, Whisper, extra voices). Registration
is a small declarative table in the app module (e.g.
`quill.apps.radio.REQUIRED_COMPONENTS = ("ffmpeg", "mpv")`).

**Refcount in the store.** `%APPDATA%\Quill\components.state.json` records, per
component, which apps require it and which are installed. A component is fetched
once; the second app that needs it just adds a ref. When the last app that
requires a component is removed, that component becomes GC-eligible (optional
components can be pruned; a "keep downloaded components" setting can override).
This is what makes "store once" real for the heavy assets while still letting
people uninstall cleanly.

**"Only some apps" falls out of this for free.** Install Radio only → runtime +
`{ffmpeg, mpv}`. Add Cast later → runtime **reused** (ref++), Cast's extra
requirements added, shared ones ref++ not re-downloaded. Remove Radio →
components *exclusively* Radio's are GC-eligible; anything Cast still refs stays.
No component is ever stored twice, and no app carries another app's weight.

## 6. The offline-first resolver (one code path, four inputs)

Every component request resolves in this fixed order, so LEAN/FULL/portable all
use **one** code path:
1. **Already in the store** (`%APPDATA%\Quill` or the portable `data\`)? Use it.
2. **Staged wheelhouse / engine tree** next to the payload (`{app}\wheels\<id>`,
   FULL and offline-portable variants)? Copy/register it into the store, then use.
3. **Network** (LEAN/system, if online): download → verify against the signed
   manifest → register into the store.
4. Otherwise: a guided, accessible "component needed" prompt (never a crash or a
   bug-report for a normal not-yet-downloaded state — the §7 guided-installer
   principle).

Because step 2 registers staged components **into the shared store**, a FULL
offline install of a second app finds the first app's already-registered
components and stages nothing twice.

## 7. Hard prerequisites (must land before the runtime is safe)

The shared runtime makes the confirmed shared-store downgrade risk (§17.1)
**more** dangerous, because more apps hit the same store through the same core.
Before shipping runtime sharing:
- **Data-store hardening**: preserve-unknown-fields on rewrite,
  rewrite-only-on-legacy, last-writer stamp — so no app can silently downgrade
  another's settings. (Designed; land on a branch under the GATE suite.)
- **FAMILY-DATA.md** kept authoritative as the schema/ownership map, versioned
  by suite major.
- **Beacon's silo joins the family store**: Beacon still uses
  `%APPDATA%\QuillBeacon` + its own SQLite; to share the runtime it should read
  the shared store's contract (or at least register its components there). Its
  sync-merge data-loss + plaintext-token defects (§16.5) are independent bugs
  to fix regardless.

## 8. Install-mode matrix — exactly how dedup behaves in each

| Mode | Runtime | Component Store | Data | Dedup across apps |
| --- | --- | --- | --- | --- |
| **System (LEAN)** | Shared `Program Files\QuillVille\Runtime\<major>`, refcounted | Shared `%APPDATA%\Quill`, downloaded on demand, refcounted | `%APPDATA%\Quill` | **Full** — one runtime, one store for all installed apps |
| **System (Offline/FULL, non-portable)** | Same shared runtime; installer also lays a wheelhouse into the runtime | Shared `%APPDATA%\Quill`; staged components registered in on first run (offline-first step 2) | `%APPDATA%\Quill` | **Full** — staged components dedup into the shared store |
| **Portable (LEAN)** | Private runtime inside the portable folder | Private store in the portable `data\`; may download on demand if online | portable `data\` | **None across sticks** (self-contained by law §3); full *within* one multi-app portable |
| **Portable (Offline/FULL)** | Private runtime in the folder | All components pre-staged in the folder, fully self-contained, no network | portable `data\` | **None across sticks**; full *within* the one folder |

Two design choices make this coherent:
- **A multi-app portable is one payload.** If a portable bundle carries several
  apps, they share the *one* runtime + store inside that folder (dedup within).
  What you cannot do is dedup one portable against another, or against a system
  install — that would break portability.
- **Offline = "components pre-staged," orthogonal to portable.** Offline is
  about *where components come from* (bundled vs network); portable is about
  *where everything lives* (travelling folder vs machine). The four modes are
  the 2×2 of those two axes, and the offline-first resolver (§6) makes them one
  code path.

## 9. Migration from today

1. Land the §7 data-store hardening on a branch (GATE suite).
2. Add the **component registration + signed manifest + refcount** layer to
   `quill/core` (one service; retire the three per-app download vintages).
   Backwards-compatible: the store paths are unchanged, only a state file + a
   resolver are added.
3. Build the **QuillVille Runtime** artifact (embeddable Python + pip + pinned
   `quill`) and a **runtime installer** that lays `Runtime\<major>` refcounted.
4. Convert the standalone shells (`standalone/*/`) from self-contained freezes
   to **runtime-resolving launchers** (the shim already anchors env; point it at
   the shared runtime; keep a portable self-contained build path for the
   portable modes).
5. Do it **one app at a time**, LEAN system-install first (highest value, lowest
   risk), then the offline + portable variants as additive builds — exactly the
   "lean now, full later" discipline that already works for QUILL.

## 10. Decisions (settled 2026-07-20)

The four architecture forks were decided with the owner:

1. **Runtime location — per-user, no elevation.** The shared runtime installs to
   `%LOCALAPPDATA%\QuillVille\Runtime\<major>` with **no admin/UAC prompt**,
   deduping across all apps for that Windows user and matching where app data
   already lives (`%APPDATA%\Quill`). The installer offers an optional
   "install for all users" (`Program Files`) checkbox for shared/lab machines,
   which is the only path that requires elevation.
2. **Runtime versioning — one runtime per suite major.** One runtime per
   QuillVille generation (`Runtime\1`); patch/minor updates replace it **in
   place within that generation**; a new generation lays `Runtime\2`
   **side-by-side**. Smallest disk, "one update fixes all apps of that
   generation," and within-generation safety rests on the §7 data-contract
   guarantees. A suite-major bump is the only place breaking changes to shared
   spaces are allowed, and it is coordinated across all apps.
3. **Portability — fully self-contained, never borrows.** A portable copy
   carries its own runtime + components + data, runs on a bare machine, and
   leaves nothing behind; it never reads or writes a host's shared install
   (§3's law, confirmed). The cost — a larger portable folder — is accepted.
4. **Component GC — keep by default, manage to prune.** Downloaded components
   stay in the shared store even when no installed app currently needs them, so
   reinstalling an app is instant and a large voice/model pack is never
   re-downloaded. A **Manage components** screen lets the user reclaim disk
   deliberately. (Refcounts still track requirement so "prune unused" is
   precise; they just don't auto-delete.)

**One item still open — Beacon's data store.** Beacon still uses its own
`%APPDATA%\QuillBeacon` silo + SQLite. Recommendation (adopted as the plan
unless you say otherwise): **register Beacon's components in the shared store
now** so it participates in dedup immediately, and **migrate its data store onto
the shared `%APPDATA%\Quill` contract as part of the §7 hardening**, after
Beacon's confirmed sync-merge data-loss and plaintext-token defects (§16.5) are
fixed. Flag if you'd rather leave Beacon fully siloed for longer.

## 10a. Installer: Inno Setup (decided 2026-07-20)

We stay on **Inno Setup**; we do not move to MSI/WiX or MSIX.

Rationale: the framework's hard parts are runtime-side, not installer-side. The
component service (signed manifest, verified on-demand downloads, the shared
`%APPDATA%\Quill` store, dedup/refcount) runs in the app; portable is the ZIP
path; per-user vs all-users and side-by-side `Runtime\<major>` folders are native
to Inno (`PrivilegesRequired=lowest` + `{localappdata}`/`{autopf}`). The decisive
factor is **accessibility** — Inno's wizard is well-behaved with NVDA/JAWS, a
first-class requirement for our audience that MSI/MSIX custom UIs do not match.

The one thing Inno lacks natively is MSI-style **shared-component reference
counting** for the shared runtime. We handle it ourselves rather than switch
tools:
- Keep the refcount + runtime-resolution logic in **one place** -- a QuillVille
  bootstrapper (Inno) or a shared `[Code]` include reused by every app `.iss` --
  not copied per app. A per-user registry refcount increments on install and
  decrements on uninstall; `Runtime\<major>` is GC'd at zero (newest retained).
- Sign the installer (Authenticode); component-manifest signing stays app-side
  with the existing Ed25519/PyNaCl.
- Reserve MSI only if a hard requirement later demands native cross-installer
  component refcounting -- weighed against the accessibility loss.

Note: the real work is the **install topology**, not the tool. Today each `.iss`
installs a fully self-contained frozen app; the shared-runtime model makes them
thin apps that resolve one runtime. That `.iss` redesign is required regardless
of the installer choice.

## 10b. Component service — settled design (2026-07-20)

Built to the "written once, breaks everywhere, smallest footprint" rule. It
unifies the existing pieces (`release_assets.fetch_file`, the per-tool
`*_install.py` modules, the `optional_components` registry) rather than adding a
parallel system.

- **Store: our GitHub releases, SHA-256 pinned. No HuggingFace for core models.**
  Extend `release_assets.py`'s proven pattern (a Community-Access release tag,
  each component pinned by SHA-256, download+verify+atomic-install via
  `fetch_file`). The public speech models -- whisper.cpp GGML (`ggerganov`),
  Piper voices (`rhasspy`), Faster Whisper (`systran`) -- are **mirrored to our
  release store** and pinned, removing `huggingface_hub` and the HF-token dance
  for the whole speech stack. (Verify each model's license permits
  redistribution before mirroring; whisper.cpp is permissive, Piper voices vary.)
- **HuggingFace shrinks to one isolated opt-in.** The only gated model,
  **pyannote speaker-diarization**, stays an optional advanced feature on HF +
  token; everything else leaves HF. Reduces fragility to a single, clearly-
  optional surface.
- **Manifest: in-code, pinned per build** (not a remote signed feed for now) --
  reproducible, no extra network/signature layer; new/updated components arrive
  via a normal app update.
- **One download core.** Every tool (ffmpeg/mpv/piper/whisper/tesseract/pandoc/
  node/...) routes its download+verify+extract+install through the single
  `fetch_file`-based core; the per-tool modules become thin specs, deleting the
  duplicated download logic.
- **Refcount: app-owned + thin installer hook.** Each app declares
  `REQUIRED_COMPONENTS`; on launch it registers refs in
  `%APPDATA%\Quill\components.state.json`; the Inno uninstaller calls a tiny
  Python "unregister" step. The dedup/GC logic lives in one testable place; the
  installer stays thin.
- **Spoken progress (Leasey-style), in the app.** The core takes a progress
  callback; the app speaks periodic updates ("Downloading the offline speech
  engine, 45 percent") through its own speech engine -- the long installs happen
  in-app, post-install, where we fully control speech. The Inno wizard stays
  screen-reader-native (frequent accessible status text); SAPI speech in the
  wizard is an optional, off-by-default extra so it never talks over a running
  screen reader.
- **Offline-first resolver, one code path:** store -> staged wheelhouse (Offline
  builds) -> our GitHub-release network -> a guided, spoken "component needed"
  prompt (never a crash).

## 11. Summary

The heavy, disk-dominating sharing (components) already works — this plan makes
it *safe and refcounted* via a signed manifest + registration, and adds a
**side-by-side, suite-major-versioned shared runtime** so the Python/code stops
duplicating too, without the compatibility-matrix trap. "Store once" is achieved
in every mode where it is physically possible (all system installs; within a
portable), and the one place it cannot be (across portable copies) is stated
plainly rather than promised away. Install only the apps you want; each adds
only its unique components; removing one cleans up only what nothing else needs.
