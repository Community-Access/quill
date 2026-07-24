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
    datas=quill_datas + nacl_datas,
    hiddenimports=quill_hiddenimports + nacl_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
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
