# Windows UI-Automation Regression Suite

Date established: 2026-07-04. Location: `tests/uia/` (pytest marker `uia`).
CI: `.github/workflows/uia-regression.yml` (manual dispatch + nightly).

## What it is

An opt-in suite that launches the **real QUILL** on a Windows desktop session
and drives it through UI Automation (pywinauto, UIA backend). It asserts the
things the unit suite cannot: that the app actually launches, that the window
title tells the truth, that keystrokes reach the editor, that dialogs honor
the Escape contract, that every keyboard-reachable control has an accessible
name, and — the accessibility-regression primitive — **what QUILL spoke**,
read from the announcement trace (`announcement_trace_enabled` mirrors every
announcement to `diagnostics/announcement-trace.log` in the test profile).

## The two hard rules

1. **Never on a live screen-reader desktop.** The suite types real keystrokes
   into the focused window and steals foreground. On a machine with JAWS or
   NVDA running it fights the screen reader (verified: JAWS intercepted
   harness keys and opened its Dictionary Manager). Run it in CI, a VM, or a
   dedicated Windows session — never on a developer's working desktop.
2. **It observes; it never decides.** The CI workflow is informational only:
   not a required check, gates nothing, files nothing, fixes nothing. A red
   run is a report for a human to read. This is deliberate — an automated
   accessibility verdict that blocked work on a false positive would cost more
   trust than it protects.

## Running it

```powershell
# On a suitable session only (see rule 1):
$env:QUILL_UIA_TESTS = "1"
pytest tests/uia -m uia -q
```

Without `QUILL_UIA_TESTS=1` every test self-skips, so the default suite and
existing CI are untouched.

## How the harness works

- Each test gets a fresh, isolated app profile (its own `QUILL_DATA_DIR`
  under the user's home, honoring the dev-build constraint), pre-seeded so
  nothing modal blocks automation: setup wizard marked complete, trust
  consent accepted at the current version, update checks off (no network),
  announcement trace on.
- `quill_app` (in `conftest.py`) spawns `python -m quill`, waits for the main
  window by title, and yields a handle with `spoken()` / `wait_spoken()` for
  spoken-output assertions. Teardown terminates the app and deletes the
  profile.
- `a11y_scan.py` walks a window's UIA tree into flat records (control type,
  accessible name, keyboard focusability). `unnamed_focusable()` is the
  axe-style failure list: anything a user can Tab to that has no accessible
  name is a bug. `summarize()` produces diff-friendly lines suitable for
  snapshot baselines as coverage grows.

## Extending coverage

Grow it dialog by dialog, keystroke path by keystroke path:

- Open a surface with its real keyboard path (accelerator or menu), scan it
  with `scan_window` + `unnamed_focusable`, assert empty, Escape out.
- Prefer asserting on the announcement trace over pixel/geometry facts: the
  trace is what a screen-reader user actually experiences, and it is stable.
- The dialog inventory (`tests/unit/ui/fixtures/dialog_inventory.json`, 370+
  surfaces) is the to-do list; the highest-traffic dialogs come first.
- Keep each test independent (one app instance per test); flaky timing waits
  belong in helpers with generous timeouts, not `sleep` calls in tests.

## Known limitations

- GitHub-hosted Windows runners provide a desktop session, but foreground
  handling there can be stricter than a real console session; treat early red
  runs as calibration, not product verdicts (rule 2 exists for this).
- wx exposes two UIA `MenuBar` elements (system + app menu); helpers already
  account for it.
- The suite exercises the plain editor surface; grid/rich surfaces get their
  own tests as coverage grows.
