# WinGet packaging drafts

These are local, reviewable manifest drafts and templates for QUILL's Windows
app family. They are **not** submitted to `microsoft/winget-pkgs` yet. The two
draft manifest sets target the latest published Stable Setup assets observed
on 2026-11-12: QUILL Lite 1.1.2 and Quill Radio 3.0.4. Their package IDs are
proposals and must be approved before the first public contribution.

The mirrored `drafts/manifests/c/CommunityAccess/...` folders are shaped like
the official repository so `winget validate --manifest <version-folder>` can
validate each set. Each package has the required version, default-locale, and
installer files. The shared `templates/` files are the commented source for
future release generation. The protected release workflow can prepare these
same sets as review artifacts; public submission stays disabled until its
separate owner-reviewed gates are configured.

Current choices to verify in Windows Sandbox before a public submission:

- Install only the signed, version-specific `Setup-Shared` Inno installer;
  never a portable ZIP, beta build, or moving runtime installer.
- Match the installed Apps & Features entry emitted by Inno Setup.
- Mark self-updating packages `RequireExplicitUpgrade: true` so
  `winget upgrade --all` does not compete with the in-app updater.
- Keep any GitHub credential out of this repository. The protected release
  workflow and public submission steps are tracked in
  [the WinGet deployment guide](../../docs/planning/winget.md).

## Local validation

On a Windows development machine with the WinGet client installed:

```powershell
winget validate --manifest .\packaging\winget\drafts\manifests\c\CommunityAccess\QuillLite\1.1.2
winget validate --manifest .\packaging\winget\drafts\manifests\c\CommunityAccess\QuillRadio\3.0.4
```

Do not use `winget install --manifest` on the everyday development PC. Install
and uninstall tests belong in Windows Sandbox or a disposable test VM.
