# QUILL Radio — macOS port source (captured into quill, #10)

This is the **complete source** of the QUILL Radio macOS port (the
`quill_radio_mac` package: `core/`, `platform/`, tests, docs, pyproject),
captured verbatim into QUILL's repo so the Mac port lives in one place and
nothing is lost. The standalone `s:\qrm` working folder was removed after this
capture; its content is here and in QUILL's git history.

## Status: PRESERVED, not yet merged into the shared Radio app

Unlike QUILL Social (a distinct app), this is a **port** of QUILL Radio, so the
end state is not a separate `quill/apps/radio_mac` package but the Mac-specific
pieces folded into the *existing* shared Radio so one codebase runs on Windows
and macOS. It is kept under `standalone/` (outside the `quill/` package) so it is
excluded from QUILL's gates until that merge is done.

## To finish the merge (follow-up — needs a Mac + GUI validation)

1. Diff `quill_radio_mac/core` against `quill/core/radio`: fold any Mac-only
   behaviour behind `sys.platform == "darwin"` branches in the shared modules
   rather than duplicating them.
2. Move genuinely platform-specific code into `quill/platform/macos/` (the
   established home for the macOS TTS/VoiceOver/announce shims).
3. Ensure the shared audio engine (`quill/ui/audio`) and the Radio surfaces run
   under the macOS build; reconcile any menu/tray differences (macOS has no
   notification-area tray — see app_shell's darwin guards).
4. Validate on real macOS + VoiceOver before shipping.

The point of capturing it here first: the Mac port's learnings and code are now
in QUILL's repo, so the merge can proceed from one source of truth.
