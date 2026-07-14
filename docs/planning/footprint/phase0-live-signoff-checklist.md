# Phase 0 footprint — live sign-off checklist

The footprint baseline has three parts. Two are automated; one is a short manual
pass. Run all three on the **reference machine** (the cheap CPU-only laptop the
optimization work targets), with the AI + speech engines and at least one model
of each installed.

Roadmap: §1.1 "AI footprint & optimization". Design: PRD §5.25f.

## 1. Static inventory (automated)

```
python scripts/footprint_report.py
```

Writes `docs/planning/footprint/footprint-baseline.json` (installed size by
component, on-disk model/asset sizes, machine context) and prints a speakable
Markdown summary. Read-only; safe to run anytime.

## 2. Per-engine timings + peak RSS (automated)

```
python scripts/footprint_live.py --merge-baseline
```

Runs each installed speech engine in an isolated subprocess on a 1-second
synthetic clip and records **cold start** (model load), **first output** (first
transcription), and **peak RSS** (sampled by the parent), merging an
`engine_timings` block into the baseline JSON. Engines with no model, or not
installed, are recorded as notes — no fabricated numbers. Add `--timeout N` to
raise the per-engine cap on a slow machine.

> Note which engines actually reported timings. An engine that shows
> "engine not available" or "no model installed" needs its runtime/model
> installed before its numbers count toward the baseline.

## 3. Live runtime behaviors (manual — a few minutes)

These exercise the now-wired runtime policies that only show up in the running
app. Tick each; note the observed behavior next to it.

- [ ] **Idle-sweep unloads a model.** Load a model (run any AI or transcription
      action), then leave QUILL idle past the idle-unload interval. Confirm the
      model is released (memory drops; the next use reloads it). Expected: the
      idle-sweep timer fires and unloads without freezing the UI.
- [ ] **Model upgrade hint.** Open the AI model / connection dialog with a small
      model selected on a machine that could run a stronger one. Confirm the
      upgrade hint is shown and is announced by the screen reader.
- [ ] **Cloud → local fallback announcement.** With a cloud provider active,
      force a failure (disconnect the network, or use a bad key) and run an AI
      action. Confirm QUILL announces the offline/cloud→local fallback clearly
      rather than a generic error.
- [ ] **Nothing regresses in Safe Mode.** Launch with `--safe-mode` and confirm
      the AI/speech features are disabled as expected (no engine loads, no
      timers arm).

Record the results (screen-reader announcements verbatim where relevant) in the
PR or the baseline notes so the sign-off is auditable.

## What is still out of scope here

- **macOS offline-speech parity** (a mac `whisper-cli` / Faster Whisper default)
  is a separate cross-platform task — see roadmap §1.1.
- **New quant catalog entries** (q5/q8, int8_float16) need real pinned files +
  SHA-256 hashes before they can be added to the download catalog.
