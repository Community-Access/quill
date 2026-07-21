# PyInstaller spec for the QUILL Social onedir build.
# Build with: scripts/build_release.ps1 (renders docs, stages them, zips the
# portable, compiles the installer) or `pyinstaller quill-social.spec` directly.
#
# Onedir, not onefile, on purpose (same rationale as quill-radio): one built
# folder feeds BOTH products -- zip it for the portable, point Inno Setup at it
# for the system install -- and the app starts instantly instead of
# re-extracting to a temp folder on every launch.
#
# QUILL Social depends on the shared quill package (quill.ui.app_shell) AND its
# own quill_social package, so collect_all both. nacl is collected explicitly
# for Ed25519 verification in the shared feature code (lazy imports the tracer
# would otherwise miss). The live Mastodon/Bluesky adapters (Mastodon.py,
# atproto) are the optional [networks] extra: when installed in the build venv
# they are picked up automatically; when absent the app still runs on the mock
# adapter, so they are not hard requirements here.

from PyInstaller.utils.hooks import collect_all

quill_datas, quill_binaries, quill_hiddenimports = collect_all("quill")
social_datas, social_binaries, social_hiddenimports = collect_all("quill_social")
nacl_datas, nacl_binaries, nacl_hiddenimports = collect_all("nacl")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=quill_binaries + social_binaries + nacl_binaries,
    datas=quill_datas + social_datas + nacl_datas,
    hiddenimports=quill_hiddenimports + social_hiddenimports + nacl_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Social is text-and-network: QUILL fetches/uses these only for editor
        # features Social never touches (transcription, neural TTS, science).
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
    name="QuillSocial",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillSocial",
    upx=False,
)
