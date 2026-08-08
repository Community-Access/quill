# QUILL artifact signing

QUILL artifacts (Quillins, AI agents, verbosity packs, sound packs,
keyboard packs, skill packs, pronunciation dictionaries) are
distributed through the Quillin Hub with a detached Ed25519 signature
in minisign-shaped text format. This is the workflow every publisher
and every Hub operator needs.

## Threat model

The signature is a *provenance* attestation, not a code-signing system.
What it does cover:

- **Tampered Hub download** -- the sidecar verification fails.
- **MITM on the storefront** -- the sidecar verification fails.
- **Unsigned submission to the Hub** -- the Submission Forge rejects
  it before the validator runs.

What it does *not* cover:

- **Author identity** -- there is no PKI chain. The key id
  (`ca-pubkey-2026`) only tells you the artifact was signed with the
  Community-Access publisher key, not who the author is.
- **Download privacy** -- no anonymity layer.
- **Executable code** -- Quillins (which carry Python) are additionally
  scanned by Bandit and the SecurityWatchdog, but the operating-system
  code-signing runbook for QUILL itself is documented separately
  (see `docs/release/quill-macos-signing-notarization-runbook.md`).

## Key files

| File | Contents |
| --- | --- |
| `quill-pub.key` (and `quillin-hub/quill-pub.key`) | 32-byte Ed25519 public key, base64-encoded. Bundled in the repo so the Hub and the desktop app can verify without a network call. |
| `~/.config/quill/quill-priv.key` (or wherever you keep secrets) | 32-byte seed + 32-byte public key, base64-encoded. The private key. **Never committed.** |
| `<artifact>.minisig` | Per-artifact detached signature. Sits next to the artifact in the same directory. |

The private key is held only by the Community-Access publisher. The
Hub does not have it; it cannot mint new signatures.

## The update-feed signing key (separate key, same discipline)

The autoupdate feed is signed with its **own** Ed25519 keypair, deliberately
distinct from the artifact-signing key above. Different purpose, different
blast radius, independently rotatable: compromising one does not compromise
the other.

| File | Contents |
| --- | --- |
| `quill/core/feed-pub.key` | 32-byte Ed25519 public key, base64. Bundled in the app; `quill.core.updates.verify_manifest_ed25519` verifies every feed against it. |
| `~/.config/quill/quill-feed-priv.key` | The 32-byte seed, base64. **Never committed** -- it lives outside the repository entirely. |
| `QUILL_FEED_SIGNING_KEY` (GitHub repo secret) | The same seed. `scripts/generate_update_feed.py` reads it during the release workflow and writes the `signature_ed25519` field. |

**Back the seed up somewhere durable -- a password manager or a hardware
token -- not just on the build machine.** Losing it does not merely stop
new releases from being signed: every shipped client verifies against the
`feed-pub.key` compiled into it, so recovering means shipping a new build
with a new public key and leaving already-installed copies unable to verify
any newer feed.

Clients accept a feed with no `signature_ed25519` (the legacy salted
checksum still applies, so pre-1.0 builds keep working), but a signature
that is *present and invalid* is a hard failure -- a forged feed is refused
rather than downgraded. Set `QUILL_REQUIRE_SIGNED_FEED=1` to reject unsigned
feeds outright.

### Rotating the feed key

1. `python -c "import base64; from nacl import signing; k=signing.SigningKey.generate(); print(base64.b64encode(bytes(k._seed)).decode()); print(base64.b64encode(bytes(k.verify_key)).decode())"` -- first line is the seed, second the public key.
2. Put the seed in `~/.config/quill/quill-feed-priv.key` and in the
   `QUILL_FEED_SIGNING_KEY` repo secret.
3. Replace `quill/core/feed-pub.key` with the public key and ship a build
   containing it **before** publishing a feed signed with the new seed --
   otherwise existing clients reject the feed they cannot verify.

## Sidecar format

Each `.minisig` is plain text in the standard minisign format -- three
lines, all UTF-8:

```
untrusted comment: quill artifact signature
key id: ca-pubkey-2026
sig: <base64-encoded 64-byte Ed25519 signature>
```

The `key id:` line is informational (verification is over the public
key bytes, not the id string). The `sig:` line is the raw 64-byte
Ed25519 signature of the artifact bytes, base64-encoded.

## CLI

`quill.tools.signing` is a CLI subcommand, not just a Python module.

### Generate a new keypair (publisher onboarding)

```bash
python -m quill.tools.signing keygen --secret-key quill-priv.key
# prints the matching public key in base64 to stdout
```

Store the secret key in a password manager or a hardware token. Add the
public key to `quill-pub.key` (and `quillin-hub/quill-pub.key` if you
ship both copies).

### Sign an artifact

```bash
python -m quill.tools.signing sign path/to/manifest.json
# writes path/to/manifest.json.minisig
```

The CLI prompts for the secret key path (or take it from
`QUILL_PRIV_KEY_PATH`); the public key is read from `quill-pub.key`.
Exit status 0 on success, non-zero on any failure (missing key, bad
sidecar, I/O error).

### Verify a sidecar

```bash
python -m quill.tools.signing verify path/to/manifest.json
# exit 0 = verified, 2 = not signed / invalid, 1 = I/O error
```

CI uses this exit code to gate artifact publication.

### Override the public key (deploy + tests)

`SIGNING_PUBLIC_KEY_PATH` env var overrides the bundled key file. The
Hub deployment uses this to point at the rotated key without rebuilding
the container image. The smoke test uses it to inject a throwaway
test keypair.

## Submission Forge flow

A user uploads a new artifact at `/forge/submit`:

1. The artifact is saved to a per-request upload directory.
2. The optional `signature` field (the `.minisig` sidecar) is saved
   next to the artifact in the same directory.
3. `audit_submission` calls `signature_status(artifact, sidecar=...)`.
4. If `verified=False`, the report is `FAIL` and the submission does
   not become an artifact. The forge report shows whether the
   signature is missing, invalid, or unverified.
5. If `verified=True`, the validator runs (and for Quillins, Bandit +
   the SecurityWatchdog).

Zipped Quillins are an edge case: the sidecar is over the *zip* bytes,
not the extracted files. The route passes the saved zip path as
`sign_target` so the linter verifies the original archive.

## Verifying a downloaded artifact

```python
from pathlib import Path
from quill.tools.signing import signature_status

status = signature_status(Path("journal-stamp.zip"))
if status.verified:
    print(f"OK, signed by {status.signer_key_id}")
else:
    print(f"REFUSE: {status.error}")
```

The desktop app surfaces the same status in the Quillin Manager dialog
(`Tools > Quillins > Manage...`) and the in-app `Submit to Quillin
Hub...` pre-flight check.

## Rotation

To rotate the publisher key:

1. Generate the new keypair (above).
2. Replace the contents of `quill-pub.key` and
   `quillin-hub/quill-pub.key` with the new public key.
3. Sign all existing artifacts with the new key; the old sidecars
   become unverifiable.
4. Bump the `KEY_ID` constant in `quill/tools/signing.py` (e.g. to
   `ca-pubkey-2026b`) and re-sign.
5. Cut a new release; the Hub's `SIGNING_PUBLIC_KEY_PATH` env var
   should be updated at deploy time so the in-process Hub uses the
   new key without rebuilding.

## Threat-model walkthrough

- I download `journal-stamp.zip` from the Hub. The sidecar is
  `journal-stamp.zip.minisig`. `signature_status` returns verified
  and `signer_key_id == "ca-pubkey-2026"`. The Quillin is what the
  publisher signed.
- Someone MITMs the download and replaces the zip with a tampered
  copy. The sidecar no longer matches. `signature_status` returns
  `signature does not match`. The Quillin Manager dialog shows
  "Invalid" and refuses to load.
- I write a Quillin and want to submit it. I sign it with the
  publisher key, upload both files to the Hub, and the Forge accepts.
- I forget to sign. The Forge rejects with "Unsigned -- every
  submission must carry a sidecar signed by `ca-pubkey-2026`".
