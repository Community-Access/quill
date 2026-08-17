# QUILL Platform Review — polish, footing, and modernization

> **Status (2026-08-17, same day):** 15 of the 24 items were executed on
> request the afternoon this review was written — **done:** P0.1+P0.2 (plus
> two latent chord conflicts and a *dead gate* both fixes uncovered), P0.3
> (four staleness sites), P0.4 (GATE-40 wired + 15 sites marked), P0.5 (site
> sync now mechanical), P1.2, P1.3 (compile-verify pending each app's next
> build), P1.5, P1.6, P2.1 (8:58 → 5:36, zero-flake), P2.2, P3.1, P3.2, P3.5,
> P4.1–P4.4, P5.4 (which found eleven unrostered gates on its first run).
> **Deferred:** P1.4 (crash fingerprinting — external repo publish, needs its
> own session). **Open:** P1.1 (ongoing ratchet), P2.3, P3.6/P3.7 (recorded
> positions, no action due), P4.5, P5.1–P5.3. Section texts below are the
> original review, unedited.

**Date:** 2026-08-17 · **Scope:** the whole `quill` package, build/release toolchain,
standalone apps, documentation pipeline · **Rule:** nothing here has been changed —
this is a ranked worklist with justifications, written after a day of unusually deep
contact with the codebase (the installer size forensics, the Python 3.13.15/Inno 7
migration, the dictation reliability pass, and the documentation scoping).

**Method.** Direct evidence over speculation: everything cited below was observed in
this repo today — grep sweeps, gate runs, dependency-version checks against PyPI,
the full 14,569-test suite, and the build pipeline end to end. Where an item
recommends a new library, it is argued against the house rules that matter here:
**torch-free speech**, **lean dependencies** (the pyproject's own MarkItDown
rejection is the model), **egress audited**, **accessibility first**.

**The one-line verdict:** the platform is in genuinely strong shape — dependency
hygiene is current to the week, the gate culture (GATE-9/11/40/EC, banned patterns,
egress audit, dialog contract, menu accelerators, docs artifacts, and now the
runtime inventory) catches whole bug classes before users meet them, and the test
suite is large and fast per test. The items below are about closing the seams that
remain, most of which this codebase's own history predicts.

---

## P0 — Correctness: real bugs and the gates that missed them

### P0.1 The Favorites submenu ships without keyboard accelerators (live bug)
**What:** `_append_radio_favorites_submenu` (`quill/ui/main_frame_radio.py:1556`)
appends favorite-station rows with no accelerator and no `&` access key, violating
the house menu rule. `tests/unit/ui/test_menu_accelerators.py` fails on any profile
that has favorites (`Alpha`, `Mu`, `Zeta` in the fixture data) — reproduced at HEAD
before any of today's work.
**Why it matters:** this is the exact cost the rule exists to prevent — a
screen-reader user walks the list to discover there is no faster route, on every
visit. Recently Played already solves it with positional accelerators
(`Alt+Shift+1..9`, `main_frame_radio.py:1389`); Favorites should mirror that
pattern (positional keys for the first N, first-letter navigation beyond).
**Effort:** small. **Risk:** low — the pattern exists twenty lines away.

### P0.2 The menu-accelerator gate has a blind spot: it tests an empty profile
**What:** the gate builds `RadioAppFrame` with no favorites, so the favorites
submenu is never appended and P0.1 passes CI while failing every real user.
**Fix shape:** the fixture seeds a profile with 2–3 favorites (and a non-empty
Recently Played) before walking the menu bar. A gate that only tests the empty
state will re-admit this bug class the next time a data-driven submenu is added.
**Effort:** small. **Risk:** none.

### P0.3 Config-snapshot staleness: audit the other controllers
**What:** the dictation controller held its `DictationConfig` snapshot forever, so
Preferences changes took effect on *restart*, not next use (fixed today by
re-snapshotting per access). `quill/core/verbosity/throttle.py:57` has the same
shape (`self._config = config or ThrottleConfig()`), and any other
long-lived-controller-with-config-snapshot will too.
**Fix shape:** a one-day audit: grep the snapshot pattern, decide per site whether
the config is meant to be live, and either re-snapshot per use or document why
frozen is correct. Consider a tiny convention (a `live_config` property fed by a
callable) so the decision is visible.
**Effort:** small-medium. **Risk:** low.

### P0.4 44 raw threads without the GATE-40 marker
**What:** 151 `threading.Thread(` sites vs 107 `GATE-40-OK` acknowledgments. The
delta is either unreviewed threading or missing markers — both are audit debt in
the invariant that matters most in a wx app (UI thread owns widgets; background
work goes through `QuillTaskManager`).
**Fix shape:** sweep the 44; convert to task manager where practical, mark and
justify where not. Then make the banned-patterns gate count them so the number
can only go down (the module-budget ratchet pattern, applied to threads).
**Effort:** medium. **Risk:** low, mechanical.

### P0.5 `docs/site/` still carries full copies of Quill Radio's docs
**What:** `docs/site/docs/radio-userguide.html`, `radio-prd.html`,
`radio-release-notes.html` are stale rendered copies of the standalone app's docs
inside QUILL's site tree — found during today's documentation scoping (which
removed Radio's chapters from QUILL's user guide per the new policy).
**Why it matters:** the site republishes documentation the policy just scoped out,
and the copies are already stale against Radio 3.0's own docs. Either the site
generator should link to the apps' own doc sets or these pages need the same
pointer treatment. (Not changed today because the site's generator and publishing
cadence weren't in scope — flagged rather than half-fixed.)
**Effort:** small once the generator is understood. **Risk:** low.

---

## P1 — Platform footing: make the good patterns total

### P1.1 Finish the `main_frame.py` extraction program (19,552 → 15,000)
**What:** `main_frame.py` is down from ~27k to 19,552 lines, and the budget file
already names the next target (`_next_target_main_frame: 15000`). The mixin
pattern (`main_frame_vault/speech/braille/radio/...`) demonstrably works — today's
GATE-11 pressure produced `ui/dictation_transcription.py` in twenty minutes.
**Why:** every future feature pays rent on this file's size: merge conflicts,
review surface, cold-start parse time, and the temptation to "just add it here."
**Fix shape:** keep the ratchet moving — one extraction per feature branch that
touches the file, budget lowered each time. No big-bang rewrite; the ratchet is
the strategy.
**Effort:** ongoing, amortized. **Risk:** low with the existing test surface.

### P1.2 Extend the runtime inventory gate to every artifact that embeds a sweep
**What:** today's `check_runtime_inventory.py` gate closed the drift class that
shipped 82 MB of undeclared payload in the 8/15 installers — but only for the
shared runtime. The portable builds (`build_portable.py`) pip-install from
pyproject (inherently manifest-true), yet their `_copy_quill_source` tree-copy
has the same "whatever is on this machine" exposure for `quill/data`
(the OptiLab build junk observed inside today's dist proves the vector).
**Fix shape:** a manifest per artifact family; the same name-level, ratchet-style
comparison; wired into `build_portable.py` and `build_windows_distribution.py`.
**Effort:** small — the checker is written; it needs call sites and baselines.
**Risk:** none; it only fails builds that changed shape.

### P1.3 Give the remaining installers the Inno 7 x64/128 MB-dictionary treatment
**What:** radio, weather, studio, inkwell got `SetupArchitecture=x64` +
`LZMADictionarySize=131072` today (−27 MB measured on Radio, from deduping the
embedded ffmpeg/ffprobe pair). Cast, Beacon, Player, Social, Converter, and the
main `build_windows_distribution.py` installer have not been evaluated.
**Why:** every shared-runtime installer embeds the same ffmpeg pair; the same
~27 MB is sitting in each of them. Verify each compiles under Inno 7 while at it
(the resolver already prefers 7).
**Effort:** small per app. **Risk:** low — proven change, but each app's `.iss`
should be compiled and smoke-installed once.

### P1.4 Ship the crash-fingerprinting feedback loop
**What:** `feedback-hub` 1.1.0 (D:\code\feedback-hub) has crash fingerprinting
built and installed locally but unpublished. QUILL's `stability/crash_report.py`
already produces redacted diagnostic bundles.
**Why:** the installer-size mystery and the #1415 "update installed no code" bug
were both found *by hand* long after the field had the evidence. Fingerprinted
crash grouping is the difference between "a user mentioned it twice" and a
ranked list of what actually breaks.
**Effort:** medium (publish, wire the ID into crash_report, close the loop in
the issues workflow). **Risk:** low; redaction already exists.

### P1.5 Decide the fate of `D:\QUILL\.venv` (and document the S:→D: history)
**What:** the checkout's `.venv` is broken (Python 3.13.11, PyInstaller crashes
on malformed package metadata) and is exactly the "stale venv silently changed
what shipped" hazard the resolver comment warns about. It survived the S:→D:
drive re-lettering; the recycle-bin still holds S:-era artifacts that were
today's forensic key.
**Fix shape:** delete or rebuild the venv deliberately; keep a short note in the
build docs that `S:\...` paths in old logs/pyc mean this machine pre-relettering.
**Effort:** trivial. **Risk:** none — resolvers already skip it, this removes the
foot-gun for a manually-invoked tool.

### P1.6 Mirror or formally de-support whisper large-v3
**What:** large-v3 (~3.1 GB) exceeds GitHub's 2 GiB release-asset limit, is not
mirrored, and the 617 audit flagged that this "manual install only" state is not
surfaced in the picker. With capability text now spoken per row, the honest
sentence costs one catalog field.
**Effort:** trivial (text) or medium (chunked/split mirror). **Risk:** none.

---

## P2 — Performance

### P2.1 Parallelize the test suite (9 minutes → ~2)
**What:** 14,569 tests in 538 s, single-process. The suite is dominated by
well-isolated unit tests (`QUILL_DATA_DIR` isolation already exists).
**How:** `pytest-xdist` (`-n auto`), dev-dependency only. The conftest's
`_DEV_BUILD` fixture and per-test data dirs are already the hard part; expect a
handful of tests needing serialization markers (wx singletons, the heartbeat
tests).
**Justification for the new dev-dep:** it ships nothing to users, and a sub-3-minute
suite changes contributor behavior — people run the whole thing instead of guessing
a subset. **Effort:** small-medium. **Risk:** flushes out hidden test coupling
(which is itself value).

### P2.2 Startup import audit, measured not vibed
**What:** the codebase already practices lazy imports rigorously (every provider,
every optional engine). What's missing is a *regression gate*: a startup-time
budget test (`python -X importtime -m quill` parsed, top offenders pinned) so a
future top-level `import numpy` in a hot module fails CI instead of costing every
launch 300 ms.
**Effort:** small. **Risk:** none — measurement only.

### P2.3 The catalog pattern is proven — reuse it where live calls still hurt
**What:** the Station Catalog (SQLite+FTS5, generation-swapped, offline-first)
turned browse from network-bound to sub-millisecond. Podcast search, the music
charts fallback, and the abbreviation/emoji pickers with linear scans are
candidates for the same shape where their sources permit caching (each already
has staleness-honesty conventions to lean on).
**Effort:** medium per surface. **Risk:** the honesty labels ("as of <age>") are
already house style; keep them mandatory.

---

## P3 — Modernization and dependencies (each argued, several rejected)

**The standing verdict on hygiene:** every floor checked today resolves to the
current release (`requests 2.34.2`, `cryptography 50.0.0`, `paramiko 5.0.0`,
`wxPython 4.3.1`, `yt-dlp 2026.7.4`, `mutagen 1.48.1`...). Dependabot + the
`check_build_env` gate are doing their jobs. Recommendations:

### P3.1 Raise the `sherpa-onnx` floor to ≥1.13
**Why:** the Parakeet 3 provider and the new Silero tier use the
`OfflineRecognizer`/`VoiceActivityDetector` APIs; 1.10 predates fixes in both.
The floor is a one-line change and the installed reality is already 1.13.5.
**Risk:** none.

### P3.2 `rapidfuzz` as an *optional* accelerator for the vocabulary corrector
**What:** today's fuzzy corrector is stdlib-pure (deliberate — zero new deps for
a text pass). `rapidfuzz` is a small MIT C++ wheel (~2 MB) doing Levenshtein at
50–100× the speed.
**Verdict:** *optional, not required.* Dictation transcripts are short; stdlib is
fine. If the corrector later runs over batch transcription (hour-long files,
thousands of tokens), gate the import exactly like every optional engine:
`rapidfuzz` if importable, stdlib fallback always. Do not make it a hard dep.

### P3.3 `watchfiles` for the watch folder — rejected for now
**Why considered:** Rust-backed filesystem watching beats polling. **Why
rejected:** the current watcher is already event-driven where the OS allows, the
gain is marginal for a single-folder feature, and it adds a compiled dependency
to the base install for no user-visible difference. Revisit only if watch-folder
scale complaints appear.

### P3.4 `pydantic` / `msgspec` for settings & schemas — rejected
**Why:** the pyproject already documents the philosophy (MarkItDown was rejected
over its pydantic-adjacent 150 MB chain). `core/settings.py` (1,724 lines) is
long but *boring* — hand-coerced fields with delta serialization that survived a
schema-version migration cleanly. A validation-framework rewrite risks the
migration behavior for aesthetics. The better investment is P3.6.

### P3.5 Dev tooling: `uv` for contributor installs; PEP 735 dependency groups
**What:** `uv` (dev-only, never shipped) turns the 2-minute `pip install -e
".[ui,dev]"` into seconds and gives lockfile reproducibility for the build
machines — which today's forensics showed is exactly where drift bites. PEP 735
`[dependency-groups]` is where the `[runtime]`/`[packaging]` split naturally
lands as tooling catches up.
**Effort:** small; entirely additive. **Risk:** none to users.

### P3.6 Split `core/settings.py` mechanically, not frameworkily
**What:** if the file's size ever earns a budget entry, split by group (the
registry groups already exist in `settings_migration`) with the same hand-coerce
style — no new library, same tests. Noted here so the pydantic conversation has
a recorded answer.

### P3.7 Python version posture: 3.13.x is right; 3.14 is a 2027 conversation
**Why:** wxPython/Phoenix wheels and the native launcher trail new CPython by
quarters, and free-threading builds are irrelevant to a `wx.CallAfter`
architecture. The embeddable-pin + `RuntimeVersion` machinery proven today makes
the eventual bump a one-day change. Nothing to do now — this is the justified
*absence* of a modernization.

---

## P4 — User experience polish

### P4.1 Surface the new dictation powers in Preferences, not just settings keys
**What:** `dictation_remove_fillers` is toggleable only by editing settings; the
`dictation.md` vocabulary has no discoverable "open my dictation profile" entry
in the dictation settings panel.
**Fix shape:** two rows in the existing Dictation Settings panel: a filler-removal
checkbox (with the language-honesty note in its help text) and an "Edit My
Dictation Words..." button that opens `dictation.md` in QUILL itself (the editor
is right there). Follow the wx-list house rule if a list UI is ever chosen
instead.
**Effort:** small. **Risk:** none; the core is done and tested.

### P4.2 Capability text in the guided setup, not only Manage Speech Models
**What:** `describe_models` rows now speak capabilities, but the guided
Dictation setup's engine step (step 1 of 3) still describes engines with static
prose. The Parakeet recommendation ("never invents text from silence") is
exactly the sentence that helps a user choose at setup time.
**Effort:** small. **Risk:** none.

### P4.3 Let Parakeet's language detection feed the filler gate automatically
**What:** the filler pass takes language evidence from the `dictation_language`
setting only. Parakeet detects the spoken language per utterance; the provider
could report it in `TranscriptionResult.language` and the controller could prefer
*detected* over *configured* evidence — strictly more honest, and it makes the
gated tier work for multilingual users with zero configuration.
**Effort:** small (the plumbing exists; it needs the sherpa result field read).
**Risk:** low — fail closed to the current behavior when detection is absent.

### P4.4 Announce the VAD's work when it changes the outcome
**What:** when the pre-pass skips the engine entirely ("no speech"), the user
hears the honest earcon — good. When it trims 20 s of silence from a 25 s take,
nothing says so; the transcription is just faster. A single quiet log line
exists; consider a status-bar note ("Trimmed 20s of silence") for trust-building,
speakable on demand rather than announced.
**Effort:** trivial. **Risk:** none.

### P4.5 A braille-parity audit for QUILL itself
**What:** Audio Studio's changelog documents the braille-routing overhaul
(announcements reach displays with flash-timing rules). QUILL shares the
announcement service — but an explicit audit that every QUILL announcement path
routes through it (not just the mixins that were touched) would make the parity
claim checkable, ideally as a gate on direct `speak`-only call sites.
**Effort:** medium. **Risk:** none.

---

## P5 — Amazingness (justified ambitions)

### P5.1 Streaming dictation on the landed contract (S2/S3 of #617)
**The pitch:** the committed/tentative protocol and `StreamAnnouncer` shipped
today with tests; Nemotron streams; sherpa-onnx exposes partials. Wire them and
QUILL becomes the first screen-reader-first editor where dictated words appear
*as you speak* — spoken once, brailled once, never repeated — instead of after a
post-utterance pause. The accessibility failure that makes every other live
dictation unusable with a screen reader (double-speak) is already structurally
solved in `speech/streaming.py`; what remains is the capture-loop plumbing and a
live region in the dictation UI.
**Why now:** the multilingual streaming successor (nemotron-3.5-asr-streaming,
28 languages) is published in ONNX form upstream; when its int8 export is
mirrored on assets-v1 the same provider pattern carries it.
**Effort:** the largest item here (weeks). **Payoff:** category-defining.

### P5.2 A "Polish my dictation" AI pass, opt-in, local-first
**The pitch:** Handy ships an optional LLM cleanup phase ("Polishing") with a
distinct announced state. QUILL already has AI sessions, consent-safe fallback
(`core/ai/fallback.py`), and an optional `llama_cpp` backend — the pieces exist.
An explicit command ("Polish last dictation") that rewrites the inserted
paragraph with punctuation/casing cleanup — announced as its own phase, undoable
as one edit, never automatic — fits QUILL's protected-transaction dictation
philosophy and the existing AI consent posture.
**Effort:** medium. **Risk:** contained by being opt-in and undoable.

### P5.3 Property-based tests for the pure cores
**The pitch:** the io readers (`read(path) -> Document`), the braille
translators, `normalize_for_insertion`, the new `vocabulary`/`fillers` passes —
all pure functions with invariants ("never crashes on arbitrary bytes",
"round-trips", "never grows text") that Hypothesis exercises better than
example tests. Ironically, `hypothesis` was *accidentally shipped* inside the
8/15 installers; adding it deliberately — as a dev-dependency where it belongs —
is the correct ending to that story. Start with `quill/io` (the file-format
attack surface) and the two new text passes.
**Effort:** small to start, compounding value. **Risk:** none (dev-only).

### P5.4 A QuillVille health dashboard from the gates you already have
**The pitch:** the repo runs a dozen ratchet gates (budgets, inventory,
accelerators, dialogs, egress, error codes...). One `quill.tools.platform_report`
that runs them all and emits a single markdown/HTML scorecard — trend-tracked in
CI — turns "the gate culture" into a visible instrument. Cheap to build (the
gates all exit with structured output today), and it is the natural home for the
thread-count ratchet (P0.4) and startup budget (P2.2).
**Effort:** small-medium. **Payoff:** the platform's footing becomes something
you can *see*.

---

## Closing note

The strongest thing observed today is cultural: every bug fixed here tends to come
back as a gate, and every gate is a ratchet. The items above follow that grain —
they are mostly "make an existing good pattern total" rather than "adopt something
new." The two real bets (P5.1 streaming dictation, P5.2 local polish) both stand
on contracts and consent machinery that already exist and are already tested.
