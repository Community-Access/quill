<!--
Use this template for a Quillin submission. Open your PR with
?template=quillin_submission.md appended to the compare URL, or copy this in.
See docs/quillins.md for the full process.
-->

## Quillin submission

- **Quillin id** (reverse-DNS): `com.example.…`
- **Name / version**:
- **Layer**: <!-- Layer 1 (snippet only) or Layer 2 (Python handler) -->
- **Directory**: `quill/quillins_bundled/…` <!-- or the submission area -->

## What it does

Describe the commands it contributes, where they appear (menus, context menu,
hotkeys), and what each announces on completion.

## Capabilities

List every declared capability and justify each one. Call out any consent-gated
capability (`fs.read`, `fs.write`, `net`) and how a refusal is handled.

- 

## Verification

- [ ] `python -m quill.tools.quillin_lint <dir> --strict` is green
- [ ] Tests added (manifest + registry + snippet/handler; host round-trip for handlers)
- [ ] `Quillin Verify` workflow passes

## Accessibility

- [ ] Every command announces a clear outcome (NVDA/JAWS/Narrator parity)
- [ ] Fully keyboard-operable; no focus traps or surprise focus changes
- [ ] Plain-text-first; uses stock controls / sanctioned surfaces

## Author Covenant

- [ ] I have read [`docs/quillins/quillins.md`](../../docs/quillins/quillins.md)
      and attest this Quillin upholds every promise in it
- [ ] Minimum capabilities only; no silent network, telemetry, or tracking
- [ ] Readable source (no obfuscation); no sandbox-escape; no malware
- [ ] `README` and license present; `id` is reverse-DNS I control

## Risks / follow-ups

List any known risks, edge cases, or follow-up work.
