# PyInstaller spec for the shared QuillVille Runtime onedir.
#
# This is the ONE Python runtime every QuillVille app reuses: CPython +
# wxPython + the shared quill and quill_social packages, with a generic
# launcher (runtime_launcher.py) that dispatches `-m <module>` to any app.
# An app installer installs this bundle once (skipping it when a matching
# version is already present -- see quill.core.runtime_marker) and ships only
# a thin per-app launcher that runs QuillVilleRuntime.exe -m <the app>.
#
# collect_all("quill") + collect_all("quill_social") bring both packages'
# code and data; nacl is collected explicitly for Ed25519 verification (lazy
# imports the tracer would miss). The heavy optional ML stacks are NOT
# excluded here (unlike a single-app spec): the shared runtime is the union
# of every app's needs, and QUILL itself uses transcription/neural TTS -- those
# still resolve their models from the shared component store at runtime.

from PyInstaller.utils.hooks import collect_all

# collect_all sweeps whatever is sitting in the package tree, and mypy, pytest
# and ruff all leave caches *inside* quill/ (quill/core/ai/.mypy_cache and
# quill/tools/.mypy_cache alone were 15.8 MB). They are gitignored, so they are
# invisible in a diff, and they were being packaged into every installer:
# regenerable build detritus carrying absolute paths from the build machine.
# build_portable.py already filters them for the portable bundles
# (_DEV_CACHE_IGNORE); this is the same rule for the frozen builds.
_DEV_CACHE_PARTS = ("__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache")


def drop_dev_caches(entries):
    """Filter (source, dest) data entries whose path sits in a dev cache."""
    kept = []
    for entry in entries:
        source = str(entry[0]).replace("\\", "/")
        dest = str(entry[1]).replace("\\", "/")
        if any(f"/{part}/" in f"/{source}/" or f"/{part}/" in f"/{dest}/" for part in _DEV_CACHE_PARTS):
            continue
        kept.append(entry)
    return kept


quill_datas, quill_binaries, quill_hidden = collect_all("quill")
social_datas, social_binaries, social_hidden = collect_all("quill_social")
nacl_datas, nacl_binaries, nacl_hidden = collect_all("nacl")
# yt-dlp: part of the [runtime] dependency set, so the shared runtime
# carries it for every app that resolves a YouTube or media-page link.
# Collected explicitly -- its ~940 site extractors load through a lazy
# registry the import tracer cannot follow.
ytdlp_datas, ytdlp_binaries, ytdlp_hidden = collect_all("yt_dlp")

a = Analysis(
    ["runtime_launcher.py"],
    pathex=[],
    binaries=quill_binaries + social_binaries + nacl_binaries + ytdlp_binaries,
    datas=drop_dev_caches(quill_datas + social_datas + nacl_datas + ytdlp_datas),
    hiddenimports=quill_hidden + social_hidden + nacl_hidden + ytdlp_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # The shared runtime backs QUILL (the full editor) too, so it KEEPS PIL
        # (AI vision), the PDF stack, and the speech engines QUILL uses. These are
        # only the libraries NO QuillVille app -- QUILL included -- imports at
        # runtime, dragged in solely by collect_all pulling unused quill
        # submodules. babel alone is ~152 MB.
        "babel",
        "pandas",
        "psycopg",
        "psycopg2",
        "grpc",
        "matplotlib",
        "scipy",
        "mypy",
        # hypothesis is a property-based TEST library. It reached the sweep the
        # same way mypy did -- installed in the build interpreter, reachable
        # through some collected package's optional import -- and a test
        # framework has no business in a shipped runtime whatever its size.
        "hypothesis",
        "lxml",
        # Additional dead weight dragged in transitively that NO QuillVille app
        # imports (verified: no `import speech_recognition|onnxruntime|av|imageio`
        # anywhere under quill/). speech_recognition (~44 MB) is unused -- QUILL's
        # offline speech is whisper.cpp / faster-whisper. onnxruntime (~29 MB)
        # arrives with the on-demand kokoro-onnx engine-pack, not the base runtime.
        # av / imageio pull in libx265 (~22 MB of H.265 VIDEO encoding) that these
        # audio/text apps never use. Together ~100 MB off the shared runtime.
        "speech_recognition",
        "onnxruntime",
        "av",
        "imageio",
        "imageio_ffmpeg",
        # --- engine-pack-owned modules: MUST NOT be frozen in -----------------
        # These are installed on demand into %APPDATA%\Quill\engine-packs\ by
        # quill.core.speech.engine_install, which puts the pack on sys.path.
        # A frozen copy does not merely duplicate the pack -- it SHADOWS it and
        # cannot be overridden, because PyInstaller's FrozenImporter sits ahead
        # of PathFinder on sys.meta_path (the reason yt-dlp needs the explicit
        # meta-path finder in engine_pack_imports.py to be updatable at all).
        #
        # Freezing them silently broke all three, verified in the 2026-08-17
        # build by importing each one inside the shipped runtime:
        #   vosk         -> OSError: cannot load libvosk.dll (0x7e). The wheel's
        #                   26 MB libvosk.dll is not a PyInstaller-visible
        #                   dependency, so only its three mingw support DLLs
        #                   (27.6 MB) shipped -- the engine itself never did.
        #   faster_whisper -> ModuleNotFoundError: 'av' (excluded above, and
        #                   build_runtime.ps1 then prunes libx265, so `av` can
        #                   never come back). ctranslate2's 59 MB shipped for a
        #                   module that cannot import.
        #   kokoro_onnx  -> ModuleNotFoundError: 'onnxruntime' (excluded above).
        # Worse than the wasted weight: is_vosk_available() and friends use
        # find_spec(), which finds the broken frozen module, so QUILL reported
        # all three as installed and never offered the working engine pack.
        # Excluding them costs no capability -- none of the three could run --
        # and restores the on-demand path that already exists, is SHA-256
        # verified, and is refcounted in the shared component store.
        "vosk",
        "faster_whisper",
        "ctranslate2",
        "kokoro_onnx",
        # Not installed on the 2026-08-17 build machine, so it has never shipped
        # -- which is exactly why it belongs here. sherpa-onnx backs the Nemotron
        # and Parakeet providers and the VAD, all engine-pack-installed, so on a
        # build machine that happens to have it the sweep would freeze it in and
        # shadow the pack silently. Same class of accident as `winrt` vanishing
        # from a release: what ships must not depend on what one laptop has.
        "sherpa_onnx",
        # --- present-but-broken in the 2026-08-18 probe ----------------------
        # weasyprint needs GTK native libraries (libgobject, pango) that no
        # wheel provides and the bundle never carried: it raises OSError the
        # moment anything imports it. Nothing first-party imports it; it was
        # swept in as a transitive extra of the documents stack.
        "weasyprint",
        # tomli is deliberately NOT excluded, though the 2026-08-18 probe found
        # it broken too (a mypyc-compiled dist whose hashed runtime module never
        # shipped). PyInstaller's setuptools hook aliases the vendored
        # setuptools tomli onto that name, and an exclude collides with the
        # alias ("Target module tomli already imported as ExcludedModule").
        # The declared [runtime] closure does not install the mypyc dist, so a
        # clean build machine ships the working vendored copy; a stray mypyc
        # tomli install is exactly the drift build_fingerprint.py compare
        # reports.
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillVilleRuntime",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillVilleRuntime",
    upx=False,
)
