# PyInstaller spec for the Quill Radio onedir build.
# Build with: scripts/build_release.ps1 (stages ffmpeg/docs/data, zips the
# portable, compiles the installer) or pyinstaller quill-radio.spec directly.
#
# Onedir, not onefile, on purpose: one built folder feeds BOTH products --
# zip it for the portable, point Inno Setup at it for the system install --
# and the app starts instantly instead of re-extracting ~175 MB to a temp
# folder on every launch. collect_all("quill") brings the entire quill
# package -- code and package data (schemas, sounds, bundled quillins,
# assets, and the build-time _feedback_token module) -- so nothing the
# shared feature code needs is missing.

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
        # Basic app: QUILL fetches/uses these only for features Radio never
        # touches (transcription, neural TTS, science stacks).
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillRadio",
    icon="assets/quill-radio.ico",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillRadio",
    upx=False,
)
