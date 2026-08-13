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
        # yt-dlp (~3 MB) is bundled only in the apps with a YouTube or
        # URL-import path (Radio, Studio, Converter). collect_all("quill")
        # force-includes quill.core.radio.youtube here too, so without this
        # exclude the tracer would follow its import and ship the whole
        # extractor set into an app that can never call it.
        "yt_dlp",
        # QuillBeacon never touches the neural-speech / science stacks QUILL
        # fetches on demand for other features.
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
        # Heavy transitive dependencies this app never imports at runtime
        # (verified by tracing quill.apps.beacon). collect_all("quill") force-
        # includes every quill submodule; PyInstaller then follows their imports
        # into these libs. Excluding them roughly halves the build (babel ~152 MB).
        # (Beacon keeps cryptography -- its encrypted sync hard-imports AESGCM.)
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

# The icon is generated, not hand-drawn -- see scripts/build_app_icons.py, which
# owns the whole family's design system. Do not edit the .ico directly.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillBeacon",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
    icon="assets/quill-beacon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillBeacon",
    upx=False,
)
