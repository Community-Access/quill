# QUILL Social — preserved source (captured into quill, #10)

This is the **complete source** of QUILL Social 0.3.0 (the `quill_social`
package plus its docs, tests, changelog, launcher, and build scripts), captured
verbatim into QUILL's repo so nothing is lost and everything lives in one place.
The standalone `s:\quill-social` working folder was removed after this capture;
its content is here and in QUILL's git history.

QUILL Social never shipped, so moving it here (rather than keeping a separate
repo) is safe.

## Status: PRESERVED, not yet functionally integrated

The code still imports its own top-level package (`quill_social`), so it is NOT
wired into the `quill` package and is deliberately excluded from QUILL's gates
(everything under `standalone/` is outside the `quill/` package and is skipped by
ruff, pytest `testpaths`, and the size/dialog/banned-pattern audits). It runs
today only from this preserved tree.

## To finish the integration (follow-up, mirrors the QuillBeacon vendoring)

1. Move `quill_social/` -> `quill/apps/social/` and rewrite `quill_social.*`
   imports to `quill.apps.social.*`.
2. Add a `__main__.py`; migrate raw `wx.MessageBox` -> `quill.ui.dialog_contract.
   show_message_box` (GATE-16); register dialog surfaces (`dialog_inventory
   --write`); green the module-size budgets, mypy (core/io), and egress audit.
3. Keep a thin `standalone/social/` build shell (launcher, PyInstaller spec,
   installer) like `standalone/beacon`.
4. Validate on a real screen-reader setup before shipping.

See `CHANGELOG.md` here for the app's own history (initial 0.3.0 + OAuth sign-in).
