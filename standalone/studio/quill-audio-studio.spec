# PyInstaller spec for the QUILL Audio Studio onedir build.
# Build with: scripts/build_release.ps1 (stages ffmpeg/docs/data, zips the
# portable, compiles the installer) or pyinstaller quill-audio-studio.spec directly.
#
# Onedir, not onefile, on purpose: one built folder feeds BOTH products --
# zip it for the portable, point Inno Setup at it for the system install --
# and the app starts instantly instead of re-extracting ~175 MB to a temp
# folder on every launch. collect_all("quill") brings the entire quill
# package -- code and package data (schemas, sounds, bundled quillins,
# assets, and the build-time _feedback_token module) -- so nothing the
# shared feature code needs is missing.
#
# As of 2026-07-24, the entry-point EXE is NOT produced by PyInstaller
# anymore -- it is replaced by the native QuillVille launcher
# (quill-audio-studio.exe) which is placed at the onedir root by
# scripts/build_release.ps1. See quill/native/launcher/README.md.

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
        # The heavy speech/science stacks are NOT bundled: Audio Studio fetches
        # the neural TTS engine (Kokoro/Piper) and any transcription engine on
        # demand through QUILL's shared, SHA-verified component system (the same
        # assets-v1 mirrors QUILL uses), keeping the base build small. ffmpeg is
        # staged into tools\ffmpeg by build_release.ps1. To ship a fully-offline
        # Studio with TTS bundled, drop "kokoro_onnx"/"onnxruntime" from this list.
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
        # Heavy transitive dependencies this app never imports at runtime
        # (verified by tracing quill.apps.studio). collect_all("quill") force-
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

# COLLECT-only build. See quill-radio.spec for the full rationale. The
# native launcher (quill-audio-studio.exe) is built by
# scripts/build_native_launcher.py and placed at the onedir root by
# scripts/build_release.ps1. The EXE() below is a PyInstaller-required
# placeholder -- COLLECT() refuses to run without one -- and is
# overwritten by the native launcher at the same path.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillAudioStudio",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillAudioStudio",
    upx=False,
)
