# Getting two build machines to agree

Two checkouts at the same commit can produce installers tens of megabytes
apart, and nothing in the build output says why. This is the procedure for
finding the difference and closing it.

Read this when: the same app builds to a different size on two machines, a
release is unexpectedly larger than the last one, or you are setting up a new
build machine and want it to produce byte-comparable output.

## Why builds drift

`standalone/runtime/quillville-runtime.spec` builds with `collect_all("quill")`.
PyInstaller's `Analysis` then follows every optional import the `quill` package
makes and bundles whatever it finds **importable on that machine**. A package
that is installed but undeclared ships silently; a package that is declared but
missing silently stops shipping. Both cases exit 0.

This is not hypothetical. Two recorded incidents:

- 2026-08-15: Radio installers carried 81.8 MB of undeclared payload — pymupdf,
  a second OpenBLAS, pydantic, curl_cffi, pyphen, winrt, even hypothesis —
  swept out of one machine's site-packages. The next build on a leaner machine
  came out 31 MB smaller with no code change.
- 2026-08-09: Windows OCR (the `winrt-*` packages) shipped in that release and
  then silently vanished from the next one the same way.

Four gates now cover this, and it helps to know which answers which question:

| Gate | Question it answers | Runs |
|---|---|---|
| `scripts/check_build_env.py` | Is everything `[runtime]` needs installed? (the floor) | before PyInstaller |
| `scripts/check_runtime_inventory.py` | Did a top-level package appear or vanish? (the ceiling) | after the dist is complete |
| `scripts/check_runtime_imports.py` | Does everything in the box actually *work*? | after the inventory gate |
| `scripts/build_fingerprint.py` | **What exactly differs between these two machines?** | on demand |

The first three protect one machine from itself. The fourth is the one to reach
for when two machines disagree, because it records sizes and versions, not just
names.

The import gate is the newest and answers a question the other two structurally
cannot. They compare *names*; it runs the finished bundle and imports things. On
2026-08-17 that caught three speech engines that were present, resolved through
`find_spec`, and raised the moment anything imported them — `vosk` (its engine
DLL loads via cffi, which PyInstaller cannot see, so only its support libraries
shipped), `faster_whisper` (needs `av`, a deliberate exclude) and `kokoro_onnx`
(needs `onnxruntime`, likewise). Every build carrying them exited 0. It also
enforces the rule that came out of that: a module installed on demand into
`engine-packs` must never be frozen into the runtime, because the frozen copy
shadows the pack permanently and cannot be overridden.

## The procedure

### 1. Capture on both machines

At the checkout root on each machine:

```powershell
python scripts\build_fingerprint.py capture --label work -o work.json
```

```powershell
python scripts\build_fingerprint.py capture --label home -o home.json
```

`capture` is read-only. It never installs, builds, or modifies anything, and
anything it cannot find (no built runtime, no staged ffmpeg, no git) is recorded
as absent rather than failing — so it works on a fresh clone.

The JSON is small and safe to email or drop on a stick. It contains: the git
commit/branch/dirty state, the interpreter path and version, every installed
distribution and its version, the SHA-256 of each staged binary dependency, the
byte size of every top-level item in the built runtime, and the size of every
release artifact — the standalone apps' `standalone/*/dist` plus the main QUILL
editor's `dist/windows*` portable zips and compiled `Setup.exe`.

For the contents comparison to mean anything, both machines should have built
the shared runtime at least once:

```powershell
.\standalone\runtime\build_runtime.ps1
```

That is the whole command now. The runtime build no longer stages ffmpeg or
libmpv and no longer takes `-FfmpegDir` / `-LibmpvDir`; the media apps add those
to their own installers afterwards (`scripts\StageMediaTools.ps1`). If you are
comparing two machines, build the shared runtime **without** staging on both, so
you are comparing the same thing — a base runtime is 335 MB, one with the media
tools added is 640 MB, and mixing the two makes the report unreadable.

If one side has no built runtime the report says so and still compares
everything else.

### 2. Compare, with both files in one place

```powershell
python scripts\build_fingerprint.py compare work.json home.json
```

`compare` always exits 0 so a drifted report can be read in peace. Add
`--fail-on-drift` to exit 1 when anything that can change what a build ships
differs — interpreter version, packages, staged binaries, runtime contents,
artifact sizes — which lets a CI job or release script gate on it. Machine
identity (commit, branch, dirty state, interpreter path, OS) is reported but
never counted: two machines legitimately differ there. The final "Drift"
section states the count either way.

The report is plain text, one fact per line, in five sections:

- **Checkout and interpreter** — commit, branch, dirty flag, Python version and
  path. Any difference here explains everything below it, so fix this first.
- **Release artifacts** — every installer and zip, with the size delta. This is
  the symptom you started from.
- **Staged binary dependencies** — ffmpeg, ffprobe, libmpv with SHA-256. These
  are ~300 MB of the payload and no import-based gate can see them.
- **Installed packages** — present only on one side, or at different versions.
  This is where the answer usually is.
- **Built shared runtime** — total size plus a per-item size delta for
  `_internal` and `tools`, sorted by how much each differs. `tools` is normally
  empty now; if it is populated on one side only, that side ran a media app's
  release script rather than the plain runtime build.

### 3. Fix what it found

**A package on one side only.** Decide which machine is right.

- Genuinely needed: add it to the appropriate extra in `pyproject.toml`, make
  sure it is reachable from `[runtime]`, install it on the other machine, then
  rebaseline: `python scripts\check_runtime_inventory.py <dist> --write`.
- A stray: `pip uninstall <name>` on the machine that has it. Check what
  depends on it first — a stray is often a transitive dependency of a dev tool
  you installed into the same interpreter, which is an argument for keeping
  release builds on a clean system Python rather than a working venv.

**Different versions.** Usually harmless for size, occasionally not (a
duplicated package ships its native libraries twice —
`check_runtime_inventory.py` has a dedicated check for exactly that). Bring both
to the pyproject floor:

```powershell
python -m pip install -e ".[runtime,packaging]"
```

**A staged-binary SHA mismatch.** One machine is not building from the pinned,
verified asset. Re-stage it:

```powershell
python scripts\fetch_build_deps.py --only ffmpeg --force
python scripts\fetch_build_deps.py --only libmpv --force
```

Never pass `-FfmpegDir` pointing at a hand-assembled directory for a release —
`build_release.ps1` refuses PATH auto-discovery on purpose, and the pinned
asset is the stronger guarantee.

**A runtime item that differs in size but not in name.** This is the subtle one:
same package, different payload. The pyenchant case below is the worked
example.

### 4. Lock it in

Once both machines agree, commit the rebaselined
`standalone/runtime/runtime-inventory.json`. From then on the ceiling gate fails
the build on either machine the moment the drift returns, naming the package.

## Which interpreter a release build uses

`scripts/BuildEnv.ps1` resolves the newest *installable* system CPython — never
a checkout venv. A venv whose base interpreter moved still has a `python.exe`
that fails several minutes into the build with a misleading error, and a
drifted venv silently changes what ships. An `EXTERNALLY-MANAGED` interpreter
(uv- or distro-managed) is skipped, because the build must be able to
`pip install` the `[runtime]` closure into it.

If two machines report different `executable` paths, that alone can account for
a large size difference: they are two different package sets.

## What is actually in the box

The shared runtime is **335.2 MB** as of 2026-08-18, down from 734.9 MB. If your
machine builds a number far from that, the fingerprint compare will say why.

Top items, measured, real bytes:

| Component | MB | Notes |
|---|---|---|
| quill | 56 | code + data (catalog seed, dictionaries, voice previews) |
| pymupdf | 37.7 | documents; leaves every app but QUILL in Stage 3 |
| enchant | 26.8 | after the prune below; 20.2 MB of it is dictionaries |
| wx | 23.1 | |
| numpy.libs | 20.0 | |
| PIL | 12.8 | |
| yt_dlp | 9.5 | |
| hf_xet | 9.1 | |

A media app's release script then adds `tools\ffmpeg` (194 MB, ffmpeg + ffprobe)
and `tools\mpv` (110 MB), SHA-256 pinned, to its own installer — Radio takes
both, Cast and Studio ffmpeg. Those 304 MB used to be in the runtime itself, so
every app installed them; that is the single largest change here.

Gone since the 3.0.0 measurement, and worth knowing so their absence does not
read as drift: `ctranslate2` (59 MB), `vosk` (26 MB), `kokoro_onnx`,
`phonemizer-fork`, `tokenizers` and `rdflib`. All are engine-pack-owned and were
frozen in by accident; three of them did not work. See the import gate above.

Radio itself imports almost none of the speech and spellcheck stack. The dead
`standalone/radio/quill-radio.spec` still documents this — it excludes
`faster_whisper`, `vosk`, `kokoro_onnx`, `onnxruntime`, `torch`, `PIL`,
`pdfminer`, `pypdfium2` and `lxml` by name, with the note that QUILL uses them
"only for features Radio never touches".

That spec is no longer built. Since the 3.0 shared-runtime switch, Radio's
installer is the delivery vehicle for a runtime deliberately sized as the union
of every QuillVille app's needs, QUILL included. That is the design: one
runtime installed once at `%LOCALAPPDATA%\QuillVille\Runtime\3.13`, reused by
Radio, Cast, Weather, Studio, Social and Inkwell. The per-app install stays
tiny — `C:\qr` is a 24 KB native launcher, an icon, and docs.

So the goal is not "make the runtime Radio-shaped". It is "make the runtime
contain nothing that no app can call".

### The pyenchant case (~64 MB)

`pyenchant`'s Windows wheel does not vendor libenchant and its dependencies —
it vendors a slice of an MSYS2/mingw64 `bin` directory. As shipped it carried
Tcl/Tk, a second CPython (`libpython3.10.dll`), GNU readline and ncurses, the
GCC support libraries (`libisl`, `libgmp`, `libmpfr`, `libmpc`, `libquadmath`),
gettext's translation *toolchain*, a private OpenSSL, SQLite, and 34 MB of ICU.
That is 67.6 MB of `bin` against the 20.2 MB of hunspell dictionaries that are
the actual point.

None of it is reachable from libenchant, and a PyInstaller `excludes` entry
cannot drop any of it — to PyInstaller it is not code, it is package *data*
swept in by `collect_all`.

`scripts/prune_enchant_payload.py` fixes this by computing the answer rather
than hardcoding it: it parses the PE import table of `libenchant-2.dll` and each
kept provider, walks the import graph transitively, and keeps exactly that
closure. A future wheel linked against different libraries prunes correctly with
no list to maintain. Link-only artefacts (`*.a`, `*.dll.a`, `*.la`) go too.

It keeps the hunspell provider and drops nuspell, which is a second, unused
spelling engine — every dictionary shipped is hunspell format — and is the only
thing in the payload that pulls ICU. Dropping the provider drops 34 MB of ICU
with it.

Dictionaries are deliberately untouched. They are the payload, and 20 MB is a
fair price for spell checking that works in en_ZA.

Result: 91.0 MB to 27.1 MB, verified end to end — identical `check()` results,
identical `suggest()` output, `en_GB` and `en_ZA` still resolving. It runs as
part of `build_runtime.ps1`, beside the existing prunes for `Pythonwin`,
`*.chm`, `*.pdb` and `libx265*.dll`.

### Settled since this was written

- **`vosk\libstdc++-6.dll`, 25.4 MB.** Moot, and the reason is worth keeping. It
  was one of three mingw support DLLs beside a `libvosk.dll` **that was never in
  the bundle at all** — the wheel loads its engine through cffi, which
  PyInstaller cannot follow. So there was nothing to test a smaller libstdc++
  against. All 27.6 MB left with the `vosk` exclude.
- **Moving `fasterwhisper` / `vosk` / `kokoro` out of the runtime.** Done, and it
  was not a trade-off after all: all three were already broken in the bundle and
  were shadowing the working on-demand engine packs. Excluding them cost no
  capability and restored three that had silently stopped working. About 96 MB.

### Still on the table

- **English dictionary variants, ~19 MB.** 24 of the 48 hunspell files are
  English locales (en_AG, en_BS, en_BW, en_BZ, en_DK, en_GH, en_HK, en_JM,
  en_NA, en_NG, en_PH, en_SG, en_TT, en_ZW and so on) at 0.84 MB each, most with
  identical word lists. Deduplicating them would break any user whose locale
  resolves to one of the dropped names, so it needs a mapping layer rather than
  a delete. The better move is the Stage 3 spell-check layer split: only QUILL
  the editor uses the spell checker, yet all eight apps ship its 27 MB.
- **`ffprobe`, 97 MB.** Genuinely used, for M4B/M4A chapter marks and track
  durations, so it cannot simply be dropped. A shared-library ffmpeg build could
  plausibly halve the 194 MB pair, but it needs building and testing first.

## Related

- `scripts/build_fingerprint.py` — capture and compare
- `scripts/check_build_env.py` — the floor
- `scripts/check_runtime_inventory.py` — the ceiling
- `scripts/check_runtime_imports.py` — does the box actually work
- `scripts/StageMediaTools.ps1` — ffmpeg/libmpv into a media app's installer
- `scripts/prune_enchant_payload.py` — the enchant closure prune
- `scripts/fetch_build_deps.py` — pinned ffmpeg / libmpv staging
- `scripts/BuildEnv.ps1` — interpreter, ISCC and token resolution
- `scripts/footprint_report.py` — a different question: the size of an
  *installed build tree*, release over release. Use that one for "is QUILL
  getting fatter?"; use `build_fingerprint.py` for "why do these two machines
  disagree?"
