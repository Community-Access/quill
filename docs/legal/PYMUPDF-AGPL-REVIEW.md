# PyMuPDF AGPL-3.0 Distribution Record

**Decision (Jeff Bishop, 2026-11-01):** Keep PyMuPDF and comply with the
AGPL-3.0. Do not replace it with pypdfium2 or alter existing PDF behavior.

**How we comply:** The exact source of PyMuPDF, and of every other GPL, LGPL
or AGPL part, is published with each release. `scripts/collect_copyleft_sources.py`
writes the manifest, and `build-quill-apps.ps1` and `scripts/publish_release.py`
attach it to every release with `LICENSE.txt` and `THIRD-PARTY-NOTICES.txt`.
QUILL is Jeff Bishop's free personal project and is not used commercially, so
no Artifex commercial licence is needed. This is an engineering record, not a
legal opinion.

## Dependency and product inventory

The dependency chain is:

1. The `runtime` extra in [pyproject.toml](../../pyproject.toml) includes
   `quill[glow]`.
2. The `glow` extra includes `quill-glow-core` and `acb-large-print`.
3. `acb-large-print` depends on PyMuPDF. The current lock and notice catalogue
   record PyMuPDF 1.28.2; the shared runtime inventory records the bundled
   `pymupdf` package.
4. The installed QuillVille Runtime is the union of app dependencies. The
   standalone portable builder uses app-specific dependency groups, so its
   output does not automatically contain the full runtime union.

| QUILL distribution | PyMuPDF present? | Use |
|---|---|---|
| QuillVille Runtime | Yes, 1.28.2, in `runtime-inventory.json` | Provides the shared GLOW backend dependency. |
| Installed QUILL for All, QUILL Lite, Quill Radio, QUILL Cast, QUILL Studio, Quill Weather, Quill Inkwell, Quill Converter, QUILL Transcribe, QuillBeacon and QUILL Social | Yes, through the shared runtime each installer installs | Only QUILL's GLOW feature uses it; the other installed apps carry it because the runtime has not been split into app-specific layers. |
| Standalone portable builds | No | Their dependency groups omit the `glow` extra, and the committed portable inventories for Radio, QUILL Lite, Converter and Transcribe omit `pymupdf`. The release build checks each staged artifact. |

Quill Media Player has no separate installer (`standalone: null` in the
catalogue); it runs as a feature of its host product. A host that installs the
shared runtime receives PyMuPDF with that runtime.

This inventory distinguishes distribution from feature use. QUILL's GLOW
commands delegate through `quill.core.glow` and `quill_glow_core` to the
`acb-large-print` backend. GLOW is experimental and opt-in. QUILL's ordinary
PDF text reader uses pdfplumber and pypdf, and scanned-page rendering uses
pypdfium2. These existing paths remain unchanged.

QUILL's ordinary PDF text reader in [quill/io/pdf.py](../../quill/io/pdf.py)
uses pdfplumber and pypdf. Scanned-page rendering in
[quill/io/pdf_raster.py](../../quill/io/pdf_raster.py) uses pypdfium2. These
paths remain unchanged.

The catalogue's product list and current runtime inventory are
[components.json](../../quill/data/third_party/components.json),
[app-profiles.json](../../standalone/runtime/app-profiles.json), and
[runtime-inventory.json](../../standalone/runtime/runtime-inventory.json).
The portable build definitions are in
[build_portable.py](../../standalone/studio/scripts/build_portable.py), and
the committed per-app portable inventories are under `standalone/*/portable-inventory.json`.
The release build must verify the version and files in each actual staged
runtime, installer and portable artifact; the shared-runtime inventory is not
a substitute for a portable inventory.

## AGPL obligations and MIT boundary

QUILL chooses PyMuPDF's AGPL-3.0 option. The Artifex copyright notice and full
AGPL-3.0 text are included in the generated third-party notices and in each
runtime/app distribution. The full text is maintained at
[AGPL-3.0.txt](../../quill/data/third_party/licenses/AGPL-3.0.txt).

AGPL sections 4–6 describe notices and source requirements for source and
object-code conveyance. “Corresponding Source” is defined by the licence and
includes the source and scripts needed to generate, install, and run the
covered work. Section 5 also distinguishes an aggregate of separate,
independent works from a larger combined program. QUILL does not rely on the
aggregate reading for any app.

The installed runtime and the installed apps are conveyed under AGPL-3.0 as
combined works. QUILL's own code is MIT, copyright Jeff Bishop, and MIT is
compatible with the AGPL, so each QUILL file stays MIT while the combination
carries the AGPL's terms. QUILL's own source is already public, so the
Corresponding Source for a release is QUILL at the release commit plus the
exact sources the manifest lists.

Section 13's remote-network source offer applies only to a modified version of
the covered Program that users interact with over a network. The desktop apps
run locally and offer no network service, and QUILL does not patch PyMuPDF, so
section 13 does not apply to them. GLOW's web app is a network service, and it
links its own source on every page.

## Version-specific source and build instructions

The current catalogue and `uv.lock` record PyMuPDF 1.28.2. The PyPI source
archive is:

- URL:
  <https://files.pythonhosted.org/packages/a3/fb/b6761fa2d5266f2cdb24c3b91f4023070ab7848381417678e7a289a1d52a/pymupdf-1.28.2.tar.gz>
- SHA-256: `5e0be7908a715aa20333caddd73f1d6f01e4cd0c26e869fa2dd0b7f344da2249`
- Version page: <https://pypi.org/project/PyMuPDF/1.28.2/>

For QUILL's current Windows runtime build, use a clean checkout at the exact
source commit and follow [Building the QUILL Windows family](../building-windows-family.md).
The relevant commands are:

```powershell
$python = py -3.14 -c 'import sys; print(sys.executable)'
& $python -m pip install --find-links vendor/wheels -e '.[runtime,packaging,dev]'
& $python scripts/check_build_env.py --groups runtime,packaging --python $python
& $python scripts/fetch_build_deps.py
& .\standalone\runtime\build_runtime.ps1 -Python $python
& .\standalone\runtime\build_runtime_installer.ps1 -Channel stable
```

The runtime build checks the declared environment and packages the shared
runtime. `build_runtime_installer.ps1` packages that staged runtime; it does
not rebuild PyMuPDF. To reproduce PyMuPDF itself, obtain the exact source
archive above, verify its SHA-256, and follow Artifex's version-specific
upstream build instructions. QUILL does not patch PyMuPDF. If either the
runtime's PyMuPDF version or its artifact changes, refresh the source URL,
checksum, notices, and release record from the staged artifact rather than
assuming the lockfile alone describes what shipped.

## Release controls

[RELEASE.md](../release/RELEASE.md) makes this part of the pre-tag checklist
for public runtime and app releases:

1. Inspect the built runtime and record the actual PyMuPDF version and binary
   hash. Update the notice catalogue to match.
2. Regenerate the family, runtime, and app notices. Confirm each includes the
   Artifex copyright, full AGPL text, exact PyMuPDF source archive, and its
   SHA-256.
3. Preserve a source snapshot tied to the exact build: QUILL source commit,
   lockfile, vendored build inputs, PyMuPDF source archive, and build
   instructions. Publish the source location alongside the matching binary
   release. Runtime slot tags move, so a moving tag alone is not an immutable
   source reference.
4. Attach the copyleft source manifest (`copyleft-sources.json` and `.txt`)
   and the source archives it names to the release, beside `LICENSE.txt` and
   `THIRD-PARTY-NOTICES.txt`.
5. Keep that source downloadable for as long as the binaries are, and for at
   least three years after the last download of that version. A release must
   not rely on an expired URL or a moving tag as its source.

## Questions settled on 2026-11-01

- **Combined work or aggregate?** Treated as a combined work for every
  installed app, whether or not it exposes GLOW. Complying costs the same
  source bundle either way, so the aggregate argument is not relied on.
- **Corresponding Source scope:** QUILL at the release commit (already public
  under MIT), the lockfile and vendored wheels, quill-glow-core,
  acb-large-print, and the PyMuPDF source archive above.
- **Section 13:** does not apply to the desktop apps. GLOW's web app links its
  source on every page.
- **Delivery and retention:** the source is published beside the binaries for
  each release and kept for at least three years after the last download;
  support@community-access.org also answers source requests.
