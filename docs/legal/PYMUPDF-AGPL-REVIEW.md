# PyMuPDF AGPL-3.0 Distribution Review

**Decision:** Retain PyMuPDF in QUILL. Do not replace it with pypdfium2 solely
for licensing reasons or alter existing PDF behavior.

**Status:** The repository inventory, notice wording, and release gate are
updated. This is an engineering record, not a legal opinion. Counsel or
Artifex must resolve the open scope questions below before the next public
release that carries the shared runtime.

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
| Standalone portable builds | No in the current build definitions | Their dependency groups omit the `glow` extra. The committed portable inventories for Radio, QUILL Lite, Converter and Transcribe also omit `pymupdf`; confirm actual staged artifacts for every release. |

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
independent works from a larger combined program. Packaging a component in a
runtime does not, by itself, settle which category a particular distribution
falls into.

Section 13's remote-network source offer is tied to a **modified version of
the covered Program** that supports remote network interaction. A network
feature elsewhere in QUILL does not alone establish that condition. Whether
QUILL changes, combines, or exposes a covered work in a way that triggers
section 13 needs legal review.

QUILL's own files remain identified under MIT in the project licence and
component catalogue. This review does not assert that every QUILL file is
automatically relicensed under AGPL, or that MIT compatibility resolves the
scope question. Counsel must identify any source files that form part of a
covered combined work and the license terms that may apply to those files.

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

[RELEASE.md](../release/RELEASE.md) now makes this a pre-tag gate for public
runtime and app releases:

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
4. Retain the source and access instructions for the period required by the
   applicable conveyance method. A release must not rely on an expired URL or
   an unmaintained moving tag as its source offer.
5. Before the next public release, obtain counsel or Artifex guidance on the
   combined-work/source scope, section 13, and whether QUILL's source-offer
   method satisfies the requirements for its installer, portable, and
   runtime-repair distribution paths. Record the answer and any resulting
   release changes here.

## Questions for counsel or Artifex

- Does the shared Python runtime's inclusion and import-time integration of
  PyMuPDF through `acb-large-print` make the runtime, QUILL app, or any app
  package a combined work under AGPL-3.0, or can any distribution be treated
  as an aggregate? What source files are Corresponding Source in each case?
- Does the answer differ between QUILL's editor (which exposes GLOW) and the
  other family apps that carry the runtime but do not expose GLOW?
- Does QUILL modify any AGPL-covered program in a way that triggers section
  13 for a remote user, and what exact notice/source-offer placement would be
  required for the installer, portable copy, and runtime repair flow?
- Does the proposed release-specific source snapshot and adjacent source link
  satisfy the applicable conveyance option and retention period, or is a
  written offer or another delivery method required?

Until these questions are answered, the project should preserve the existing
MIT notices for its original components, ship the AGPL notice and exact
PyMuPDF source locator, keep the documented source/build materials, and hold
the next public runtime/app release for legal review.
