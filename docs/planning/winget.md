# WinGet distribution for QuillVille apps

**Status:** Local preparation only. No package has been submitted to
`microsoft/winget-pkgs` and WinGet install commands are not public yet.
**Last checked:** 2026-11-12.

This is the operating guide for adding every first-party QuillVille Windows
desktop app to WinGet, keeping its package current, and avoiding conflicts with
QuillVille's own updater. It is also the checklist to use when a new Windows
app joins the family.

## Current package state

The repository has a local manifest generator, templates, an app catalogue,
and complete draft manifests for the latest signed Stable Setup assets found
on 2026-11-12:

| App | Stable version drafted | Package ID proposal | State |
| --- | --- | --- | --- |
| QUILL Lite | 1.1.2 | `CommunityAccess.QuillLite` | Local draft; needs `winget validate` and disposable-VM install check |
| Quill Radio | 3.0.4 | `CommunityAccess.QuillRadio` | Local draft; needs `winget validate` and disposable-VM install check |
| QUILL | — | `CommunityAccess.Quill` | No eligible published Stable Setup asset confirmed |
| Quill Weather | — | `CommunityAccess.QuillWeather` | Wait for an eligible Stable Setup asset |
| Quill Inkwell | — | `CommunityAccess.QuillInkwell` | Wait for an eligible Stable Setup asset |
| Quill Converter | — | `CommunityAccess.QuillConverter` | Wait for an eligible Stable Setup asset |
| QUILL Transcribe | — | `CommunityAccess.QuillTranscribe` | Wait for an eligible Stable Setup asset |
| QUILL Cast | — | `CommunityAccess.QuillCast` | Wait for an eligible Stable Setup asset |
| QUILL Studio | — | `CommunityAccess.QuillAudioStudio` | Wait for an eligible Stable Setup asset |
| Quill Beacon | — | `CommunityAccess.QuillBeacon` | Wait for an eligible Stable Setup asset |
| QUILL Social | — | `CommunityAccess.QuillSocial` | Wait for an eligible Stable Setup asset |

Package IDs and monikers are durable public names. Every ID in the table is a
proposal until the publisher checks the catalog and approves it. Do not submit
a package or describe it as available before that decision and a successful
merge into the WinGet community repository.

## Why WinGet packages the Setup edition

Use each app's signed, version-specific `Setup-Shared` Inno Setup installer.
It gives WinGet a stable installed product, an Apps & Features entry, and a
versioned download URL. Do not package portable ZIPs, Beta or Dev releases, a
moving `latest` URL, or the shared runtime by itself.

Installed QuillVille apps can update themselves. Their installer manifests
must keep `RequireExplicitUpgrade: true`; this keeps an app from being
silently updated a second way by `winget upgrade --all`. A user can still ask
WinGet to upgrade a named app. Do not invent MSI `ProductCode` or `UpgradeCode`
matching for these Inno installers.

## Repository layout

- `packaging/winget/apps.json` is the package catalogue: app key, permanent ID
  proposal, moniker, exact Setup asset prefix, product URL and description.
- `packaging/winget/templates/` contains the shared version, default-locale,
  and installer manifest templates. The installer template owns the
  self-updater and Apps & Features safeguards.
- `packaging/winget/drafts/manifests/` contains local review copies. These are
  not copied into a public fork automatically.
- `scripts/winget/manifests.py` builds and fail-closed checks the three-file
  manifest set; `scripts/winget/prepare.py` reads a public release and writes
  a draft only; `scripts/winget/submit.py` makes a public PR only with its
  explicit `--submit` flag and the submission gates below.
- `.github/workflows/winget-submit.yml` prepares an artifact for final Stable
  releases and manual dry runs. Its public submission job is disabled unless
  the repository variable and protected environment are configured.
- `tests/unit/scripts/test_winget_manifests.py` protects the shared templates
  and generator from losing required safeguards.

## Onboard another QuillVille app

Run this checklist for each app, and again if its installer identity changes.

1. **Wait for a published Stable installer.** Confirm the GitHub release is
   public, final, not a draft or prerelease, and has the signed per-user Setup
   installer. The source-tree version is not enough. Do not guess a package
   version from a branch, tag that has not shipped, or a Beta build.
2. **Confirm the installer contract.** Install it in Windows Sandbox or a
   disposable VM. Record the executable architecture, publisher/signature,
   Apps & Features display name, version, publisher, and uninstall behavior.
   Check that an in-app update changes the same registration cleanly and that
   a portable build is not being mistaken for the installed product.
3. **Approve a permanent package ID and moniker.** Search the WinGet catalog
   and open pull requests. Confirm the spelling with the package owner before
   first submission. Do not rename an ID or moniker after publication without
   an explicit migration plan.
4. **Add one catalogue entry.** In `packaging/winget/apps.json`, add the exact
   `app_key` used by `quill.core.release_tags`, the approved `package_id`,
   package name, moniker, case-sensitive Setup asset prefix, official product
   page, concise description, and tags. Reuse the family publisher, support,
   and privacy URLs only if they apply to that app. The package ID must be
   unique. Set `package_url_verified` to `true` only after checking the exact
   official product page; the generator refuses an app whose page is still
   unverified. Keep `approved_for_submission` false until the owner authorizes
   public submission.
5. **Check release-tag and version mapping.** The tag must parse as the chosen
   app. The filename must match the configured prefix and the installed
   Apps & Features version. If a release tag includes a build suffix, the
   WinGet version must still match the product's displayed version.
6. **Generate a local draft.** Use the exact published tag:

   ```powershell
   python -m scripts.winget.prepare --tag <exact-stable-release-tag> --dry-run
   python -m scripts.winget.prepare --tag <exact-stable-release-tag>
   ```

   The first command prints the three manifests without writing files. The
   second writes them under `packaging/winget/drafts/manifests/`.
7. **Validate and review.** Confirm the three filenames and all identity,
   version, URL, SHA-256, architecture, installer type, Apps & Features entry,
   product/support/privacy/release-notes URLs, and explicit-upgrade field.
   Run `winget validate --manifest <version-folder>` with the WinGet client
   installed. Review the current upstream schema and PR template; if they have
   moved on, update `apps.json`, all three templates, generated drafts, and
   tests together. Never leave mixed schema versions.
8. **Test outside the everyday PC.** In Windows Sandbox or a disposable VM,
   install, launch, check the registered version, run the app's own updater,
   check `winget list` and named-upgrade behavior, uninstall, and inspect for
   leftovers. Record SmartScreen, quiet-install, ARM64-emulation, and
   accessibility findings. Do not use `winget install --manifest` on a
   development computer with personal data.
9. **Submit only after the owner says to go.** Complete Microsoft's
   contributor license agreement and other first-contribution requirements,
   then submit one package version per manifest-only pull request. Do not add a
   broad-scope token to this repository. The initial public submissions remain
   a deliberate owner-reviewed action.

## Prepare a new Stable version

For an app already in the catalog, repeat steps 1 and 5–9 for its new Stable
tag. The generator skips no approval decision: a clean local draft is not a
public release. Before enabling the protected workflow to submit PRs, confirm it:

- run only for a published, final Stable release;
- use the exact release asset and its SHA-256, and fail if the asset name or
  version does not match the catalogue;
- validate the complete three-file set against the current schema;
- retain `RequireExplicitUpgrade: true` and exact Apps & Features matching;
- detect an already-published version or an existing open PR and do nothing;
- create a fresh branch from Microsoft's current default branch, without
  syncing or force-pushing a fork;
- open a manifest-only PR for one app and one version; and
- use a dedicated protected GitHub Environment with a required reviewer for
  any credential that can write to the public package repository.

The protected workflow is implemented but disabled by default. A final Stable
release prepares a review artifact. It opens a public PR only when the
publisher-approved catalog flag is true, the repository variable
`WINGET_SUBMISSION_ENABLED` is set to `true`, and a reviewer approves the
`winget-submission` environment. A manual run defaults to dry-run; `submit` must
be explicitly selected to request the same protected job.

## Configure public submission after the initial approval

Do these steps only after the package IDs have been approved and the initial
packages have merged:

1. In repository Settings > Environments, create `winget-submission`. Require
   a maintainer review and restrict deployment tags to these release patterns:
   `v*`, `quill-lite-v*`, `quill-radio-v*`, `quill-weather-v*`,
   `quill-inkwell-v*`, `quill-converter-v*`, `quill-transcribe-v*`,
   `quill-cast-v*`, `quill-studio-v*`, `quill-beacon-v*`, and
   `quill-social-v*`. Do not allow branches or pull-request refs to deploy this
   environment.
2. Create a **classic** GitHub personal access token with only `public_repo`
   and an expiration date. GitHub does not accept a fine-grained token for
   this cross-repository pull request flow. `public_repo` can write to every
   public repository owned by the token's account, so keep this token out of
   repository-level secrets and personal computers used for routine testing.
3. Add the token to the `winget-submission` **environment secret** named
   `WINGET_SUBMIT_TOKEN`. The workflow passes it only to the submission job.
4. Set the repository Actions variable `WINGET_SUBMISSION_ENABLED` to `true`
   only after the package catalog and the `approved_for_submission` field in
   `apps.json` have both been reviewed. Leave both disabled until then.
5. Run the workflow manually with `submit` off first and inspect its manifest
   artifact. A later public submission requires the explicit `submit` input
   and approval of the protected environment. Future final Stable releases
   prepare a manifest artifact and wait at the same environment review.

The submitter creates or reuses the token owner's fork, branches from the
current WinGet default-branch commit through the GitHub API, checks for an
existing catalog version and open PR, and adds only the three manifest files.
It never syncs the fork. An existing branch without an open PR is left alone
for a maintainer to inspect rather than overwritten.

## Local validation commands

Validate the two current draft sets from the repository root:

```powershell
winget validate --manifest .\packaging\winget\drafts\manifests\c\CommunityAccess\QuillLite\1.1.2
winget validate --manifest .\packaging\winget\drafts\manifests\c\CommunityAccess\QuillRadio\3.0.4
```

The WinGet client was not available on the development computer during this
drafting pass, so these commands and disposable-VM install/update/uninstall
checks are still open. No claim of successful validation or public
availability is made.

## Upstream references

- [WinGet manifest schema index](https://github.com/microsoft/winget-pkgs/blob/master/doc/manifest/README.md)
- [WinGet 1.28 installer manifest fields](https://github.com/microsoft/winget-pkgs/blob/master/doc/manifest/schema/1.28.0/installer.md)
- [WinGet 1.28 default-locale manifest fields](https://github.com/microsoft/winget-pkgs/blob/master/doc/manifest/schema/1.28.0/defaultLocale.md)
- [First-time contribution checklist](https://github.com/microsoft/winget-pkgs/blob/master/doc/FirstContribution.md)
- [Microsoft manifest validation guidance](https://learn.microsoft.com/en-us/windows/package-manager/package/winget-validation)
