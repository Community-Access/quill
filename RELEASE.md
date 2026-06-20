# QUILL Release Process

This file documents the operational steps for cutting a QUILL release.
It is the canonical checklist referenced from `MAINTAINERS.md` and the
release notes.

## Pre-tag checklist

1. **Wave sign-off.** All issues in the active waves for this release are
   closed, with their PRs merged into the release branch.
2. **Quality gates green.** On the release branch head:
   - `pytest -q`
   - `ruff check .`
   - `ruff format --check .`
   - `mypy quill\core quill\io`
   - `python -m quill.tools.quillin_lint <dir> --strict`
   - `python -m quill.tools.menu_lint`
3. **Docs in sync.** `CHANGELOG.md`, `docs/release notes/release<X>.md`,
   the user guide, and `CONTROL_REFERENCE.md` agree on the closed issues,
   the menu paths, and the shipped feature set.
4. **Translations template current.** `quill/locale/quill.pot` shows the
   target version stamp and a fresh `POT-Creation-Date`.
5. **No `.po` or `.mo` files ship.** Verified with
   `git ls-files | grep -E '\.(po|mo)$'` returning empty.
6. **Manifest regenerated.** `docs/site/updates/manifests/manifest-<X>.json`
   exists for the target version, alongside the historical `0.5.0`
   manifest that the public feed still points at during pre-release.

## Tag-time flip

7. **Flip the GitHub Pages update feed.** Until the 0.7.0 stable tag is
   cut, `docs/site/updates/manifests/manifest-0.5.0.json` is the public
   feed so testers checking for updates do not see a phantom bump. When
   tagging the stable release, replace the feed manifest with
   `manifest-<X>.json` and re-sign the update feed
   (`python -m quill.tools.generate_signed_feed <X>`).
8. **Verify the feed.** `python -m quill.tools.verify_update_manifest`
   confirms the signature and the version stamp.
9. **Tag and push.** `git tag -s v<X> -m "QUILL <X>"` from the release
   branch, then `git push origin v<X>`.

## Post-tag checklist

10. **GitHub Release.** Create the release on GitHub from the tag, paste
    the release notes, and attach the signed installer artifacts.
11. **Announce.** Post in the community channel and update the website.
12. **Archive old notes.** Move the prior release notes into
    `docs/release notes/archived/`.