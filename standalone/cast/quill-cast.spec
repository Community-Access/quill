# PyInstaller spec for the QUILL Cast onedir build.
# Build with: scripts/build_release.ps1 (stages ffmpeg/docs/data, zips the
# portable, compiles the installer) or pyinstaller quill-cast.spec directly.
#
# Onedir, not onefile, on purpose: one built folder feeds BOTH products --
# zip it for the portable, point Inno Setup at it for the system install --
# and the app starts instantly instead of re-extracting to a temp folder on
# every launch. Same rationale as quill-radio.spec. collect_all("quill")
# brings the entire quill package -- code and package data (schemas, sounds,
# bundled quillins, assets, and the build-time _feedback_token module) -- so
# nothing the shared feature code needs is missing from the frozen build.

from PyInstaller.utils.hooks import collect_all

# collect_all sweeps whatever is sitting in the package tree, and mypy, pytest
# and ruff all leave caches *inside* quill/. They are gitignored, so invisible
# in a diff, and they were being packaged into the installer: regenerable build
# detritus carrying absolute paths from the build machine. build_portable.py
# already filters them for the portable bundles (_DEV_CACHE_IGNORE).
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


quill_datas, quill_binaries, quill_hiddenimports = collect_all("quill")
# PyNaCl (Ed25519 signature verification: signed update manifests, Quillin
# verification in the shared feature code). Its imports are lazy inside
# quill.tools.signing, so collect it explicitly rather than trusting the
# tracer -- the wheel's _sodium extension must land in binaries too.
nacl_datas, nacl_binaries, nacl_hiddenimports = collect_all("nacl")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=quill_binaries + nacl_binaries,
    datas=drop_dev_caches(quill_datas + nacl_datas),
    hiddenimports=quill_hiddenimports + nacl_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # yt-dlp (~3 MB) is bundled only in the apps with a YouTube or
        # URL-import path (Radio, Studio, Converter). collect_all("quill")
        # force-includes quill.core.radio.youtube here too, so without this
        # exclude the tracer would follow its import and ship the whole
        # extractor set into an app that can never call it.
        "yt_dlp",
        # Basic app: QUILL fetches/uses these only for features Cast never
        # touches (speech transcription engines, neural TTS, science stacks).
        # Feed-provided transcripts are plain downloads and need none of them.
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
        # Heavy transitive dependencies this app never imports at runtime
        # (verified by tracing quill.apps.podcasts). collect_all("quill") force-
        # includes every quill submodule; PyInstaller then follows their imports
        # into these libs. Excluding them roughly halves the build (babel ~152 MB).
        "babel",
        "pandas",
        "speech_recognition",
        "pdfminer",
        "pdfplumber",
        "pypdfium2",
        "pypdfium2_raw",
        "grpc",
        "psycopg",
        "psycopg2",
        "mypy",
        "lxml",
        "PIL",
        "Pillow",
        "av",
        "imageio",
        "imageio_ffmpeg",
        "matplotlib",
        "scipy",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QUILLCast",
    icon="assets/quill-cast.ico",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QUILLCast",
    upx=False,
)
