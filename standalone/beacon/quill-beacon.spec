# PyInstaller spec for the QuillBeacon onedir build.
# Build with: scripts/build_release.ps1 (renders docs, zips the portable,
# compiles the installer) or `pyinstaller quill-beacon.spec` directly.
#
# Onedir, not onefile, on purpose: one built folder feeds BOTH products -- zip
# it for the portable, point Inno Setup at it for the system install -- and the
# app starts instantly. collect_all("quill") brings the whole quill package
# (code + data), which includes quill.apps.beacon and quillsync.
#
# Unlike radio/cast, QuillBeacon plays media through wx.media (the OS-native
# backend), so there is NO ffmpeg/libmpv staging here.

from PyInstaller.utils.hooks import collect_all, collect_submodules

quill_datas, quill_binaries, quill_hiddenimports = collect_all("quill")
# PyNaCl (Ed25519: signed update manifests + QuillSync vault crypto). Its
# imports are lazy inside quill.tools.signing / quillsync.crypto, so collect it
# explicitly; the wheel's _sodium extension must land in binaries too.
nacl_datas, nacl_binaries, nacl_hiddenimports = collect_all("nacl")

# feedparser loads its sub-parsers dynamically (podcast/RSS feeds); requests is
# QuillSync's hosted transport. Name them so the tracer cannot miss them.
extra_hidden = collect_submodules("feedparser") + ["requests"]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=quill_binaries + nacl_binaries,
    datas=quill_datas + nacl_datas,
    hiddenimports=quill_hiddenimports + nacl_hiddenimports + extra_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # QuillBeacon never touches the neural-speech / science stacks QUILL
        # fetches on demand for other features.
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

# No app icon yet -- drop a real assets/quill-beacon.ico in and add
# icon="assets/quill-beacon.ico" here (and SetupIconFile in the .iss) once it
# exists. PyInstaller uses its default icon until then.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillBeacon",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillBeacon",
    upx=False,
)
