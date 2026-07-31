# PyInstaller spec for the Quill Converter onedir build.
# Build with: scripts/build_release.ps1 (stages ffmpeg/data, zips the portable,
# compiles the installer) or `pyinstaller quill-converter.spec` directly.
#
# Onedir, not onefile, on purpose: one built folder feeds BOTH products --
# zip it for the portable, point Inno Setup at it for the system install --
# and the app starts instantly instead of re-extracting to a temp folder on
# every launch. collect_all("quill") brings the entire quill package -- code
# and package data (schemas, sounds, bundled quillins, assets, and the
# build-time _feedback_token module) -- so nothing the shared conversion code
# needs is missing.
#
# The converter is a Basic app: it drives the bundled ffmpeg/ffprobe as
# external binaries and needs no transcription / neural-TTS / science stacks,
# so those are excluded (mirroring the Quill Radio build). yt-dlp (URL import)
# is intentionally NOT bundled -- it installs on demand into the user data dir.

from PyInstaller.utils.hooks import collect_all

quill_datas, quill_binaries, quill_hiddenimports = collect_all("quill")
# PyNaCl (Ed25519 signature verification: signed update manifests, Quillin
# verification in the shared feature code). Its imports are lazy inside
# quill.tools.signing, so collect it explicitly rather than trusting the tracer.
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
        # Basic app: QUILL uses these only for features the converter never
        # touches (transcription, neural TTS, science stacks).
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
        # Heavy transitive dependencies the converter never imports at runtime
        # (verified by tracing `import quill.apps.converter`). collect_all("quill")
        # force-includes every quill submodule -- AI vision, PDF I/O, publishing,
        # dev tooling -- and PyInstaller then follows their imports into these
        # libs. The converter keeps its real audio stack (bundled ffmpeg.exe,
        # driven as an external binary, not these Python packages).
        "babel",  # i18n .po/.mo compiler -- build tooling only (~152 MB)
        "pandas",
        "speech_recognition",
        "pdfminer",
        "pdfplumber",
        "pypdfium2",
        "pypdfium2_raw",
        "grpc",
        "psycopg",
        "psycopg2",
        "mypy",  # type checker -- must never ship in a release
        "lxml",
        "PIL",  # AI vision + Windows screen capture only
        "Pillow",
        "av",  # PyAV / video codecs (pulls the libx265 DLL)
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
    name="QuillConverter",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
    icon="assets/quill-converter.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillConverter",
    upx=False,
)
