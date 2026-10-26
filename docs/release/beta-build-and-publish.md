# Beta builds and publishing: QUILL Lite, Quill Radio and QUILL Cast

Step-by-step instructions for building beta copies of QUILL Lite, Quill Radio
and QUILL Cast on Windows, sharing them with a beta group, and publishing them
to quillforall.org. Written 2026-10-18. For the full background see
[Building the QUILL Windows family](../building-windows-family.md) and
[QUILL Release Process](RELEASE.md).

## 1. Building the beta copies

Build from an up-to-date main.
reference: `docs/building-windows-family.md`.

1. **Get main.** In PowerShell at `D:\QUILL`:
   `git switch main` then `git pull`
   (close any running QUILL Lite, Radio or Cast first).
2. **One-time build environment** (skip if done before):
   ```powershell
   $python = py -3.14 -c 'import sys; print(sys.executable)'
   & $python -m pip install --find-links vendor/wheels -e '.[runtime,packaging,dev]'
   & $python scripts/check_build_env.py --groups runtime,packaging --python $python
   & $python scripts/fetch_build_deps.py
   ```
   Inno Setup 7 must be installed. Set `QUILL_PODCAST_INDEX_KEY` and
   `QUILL_PODCAST_INDEX_SECRET` (or keep the ignored
   `quill/_podcast_index_key.py` from an earlier build): the runtime refuses to
   build without them.
3. **Dry run first**, to hear the plan without building:
   `.\build-quill-apps.ps1 lite,radio,cast -DryRun`
4. **Build:** `.\build-quill-apps.ps1 lite,radio,cast`
   It rebuilds the shared runtime, checks sibling versions, builds each app in
   turn with spoken-friendly "Step N of M" progress, passes
   `-SkipPublishedCheck` itself (beta builds are not published versions), and
   leaves unsigned builds. Add `-Sign` only if signing credentials are set up.
5. **Expect two stops on this first build after 2026-10-17, both normal:**
   - the runtime inventory gate names `lxml` (Word support). Run
     `& $python scripts\check_runtime_imports.py standalone\runtime\dist\QuillVilleRuntime`,
     confirm it ends "all correct", then follow *Rebaselining after the Word
     support change* in `docs/building-windows-family.md` and run step 4 again;
   - QUILL Lite's portable inventory names the new PDF and OCR packages:
     follow *QUILL Lite portable: the PDF reader and OCR* in the same document,
     then run step 4 again.
   Commit the two rebaselined inventory files afterwards.
6. **Collect:** everything lands in `dist\release-builds\<date-time>\`:
   an installer and a portable zip per app, a zip per app, an everything zip
   and `SHA256SUMS.txt`. Share that folder (or the per-app zips) with the beta
   group together with the checksums.
7. **Before sending, a two-minute smoke test** on each: install or unzip,
   start it, and for QUILL Lite open a `.docx`, edit, save, reopen; for Radio
   play a station; for Cast play an episode.
8. **Tell testers** that older portable copies should be updated by hand
   (`docs/release/portable-update-by-hand-notice.md`).

## 2. Getting the builds onto quillforall.org

How it works: the files live on **GitHub Releases** of `Community-Access/quill`;
quillforall.org is **GitHub Pages**, built from `docs/site` by
`.github/workflows/github-pages.yml` on every push to main. The site's download
links and the apps' in-app update lists (`docs/site/updates/v2`) point at those
GitHub Release files. Full reference: `docs/release/RELEASE.md`, "Publishing to
Beta", "Promoting" and "One-time setup (owner)".

**Once only (owner setup):** the update-list signing key stays on your
computer (RELEASE.md "The feed key stays on your computer"); `gh auth login`
done; Actions allowed to create pull requests; `stable-promotion` environment
with you as reviewer.

**For each beta app (after A3 built the files):**
1. Use the app's "What's new" from `docs/release/whats-new/`, such as
   `whats-new-radio-3.2.0.md`. It is what the update window shows when Check
   for Updates offers the build, so it must show whole: at most 60 lines and
   4,000 characters (`tests/unit/docs/test_whats_new_fits.py`). For a later
   build, add a new file the same way rather than pasting a section of the
   release notes, which run far longer.
2. Rehearse first, nothing is created:
   `python scripts/publish_release.py --app radio --version 3.2.0 --build 4 --channel beta --dist standalone/radio/dist --notes-file docs/release/whats-new/whats-new-radio-3.2.0.md --dry-run`
3. Publish for real (same command without `--dry-run`). It hashes the files,
   creates a GitHub **prerelease** (never "Latest"), uploads the installer and
   portable zip, adds the build to the **Beta** update list and signs it.
4. Repeat for QUILL Lite (`--app quilllite --version 1.2.0 --build 5 --dist standalone/quilllite/dist`)
   and QUILL Cast (`--app cast --version 2.0.0 --build 5 --dist standalone/cast/dist`),
   each with its own file from `docs/release/whats-new/`.
   The script accepts `cast`, `quill`, `quilllite`, `radio` and (since
   2026-10-24) `transcribe`; leaving out `--build` uses the next build after
   the newest published tag. QUILL Transcribe publishes the same way:
   `--app transcribe --version 1.0.0 --build 2 --dist standalone/transcribe/dist`.
5. **Commit the updated update list** (`docs/site/updates/v2`) through a pull
   request and merge it. When main updates, GitHub Pages republishes
   quillforall.org within a few minutes, and Beta-channel users are offered
   the new build.
6. **Website download links** (optional for a beta): the site's download pages
   link to specific release files (for example
   `releases/download/quill-radio-v3.0.4/...`). For a beta, testers can use the
   GitHub prerelease page directly; when a build is promoted to Stable, update
   those links  and merge, and the site updates itself.
7. Watch the page budget: installed Radio 3.0.4 and Lite 1.1.2 read only the
   first 30 releases; `publish_release.py` refuses unsafe publishes and removes
   older Beta release objects unless you pass `--keep-superseded`.
