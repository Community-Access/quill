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
#
# As of 2026-07-24, the entry-point EXE is NOT produced by PyInstaller
# anymore -- it is replaced by the native QuillVille launcher
# (quill-radio.exe, ~50-200 KB, compiled from quill/native/launcher/) which
# is placed at the onedir root by scripts/build_release.ps1 after
# PyInstaller runs. The PyInstaller COLLECT below still produces
# `_internal/` (the Python interpreter and the quill package code); the
# native launcher sits beside it and spawns it. The launcher name matches
# this spec's prior EXE name so the Inno installer ({app}\QuillRadio.exe)
# and the portable-mode evidence check in
# quill/core/storage_mode.py continue to work unchanged.
#
# The icon= field below is preserved for PyInstaller's PYZ phase (it
# stamps the icon onto the COLLECT scratch, which the native launcher
# builder can also pick up). The native launcher's own VERSIONINFO icon
# is set by build_native_launcher.py from quill-radio.ico.

from PyInstaller.utils.hooks import collect_all

quill_datas, quill_binaries, quill_hiddenimports = collect_all("quill")
# PyNaCl (Ed25519 signature verification: signed update manifests, Quillin
# verification in the shared feature code). Its imports are lazy inside
# quill.tools.signing, so collect it explicitly rather than trusting the
# tracer -- the wheel's _sodium extension must land in binaries too.
nacl_datas, nacl_binaries, nacl_hiddenimports = collect_all("nacl")
# yt-dlp: resolves a YouTube link (station, playlist, chapters) to a playable
# audio stream. Bundled rather than downloaded on demand -- the wheel is ~3 MB,
# so making a new user consent to a download before their first YouTube link
# costs more than the disk does. Collected explicitly because yt-dlp loads its
# ~940 site extractors through a lazy registry the tracer cannot follow.
ytdlp_datas, ytdlp_binaries, ytdlp_hiddenimports = collect_all("yt_dlp")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=quill_binaries + nacl_binaries + ytdlp_binaries,
    datas=quill_datas + nacl_datas + ytdlp_datas,
    hiddenimports=quill_hiddenimports + nacl_hiddenimports + ytdlp_hiddenimports,
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
        # Heavy transitive dependencies Radio never imports at runtime (verified
        # by tracing `import quill.apps.radio`). collect_all("quill") force-
        # includes every quill submodule -- AI vision, PDF I/O, publishing, dev
        # tooling -- and PyInstaller then follows their imports into these libs.
        # Radio keeps its real audio stack (bundled ffmpeg.exe + libmpv-2.dll,
        # driven as external binaries, not these Python packages).
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

# COLLECT-only build: PyInstaller produces the onedir's _internal/ tree
# (Python interpreter + the quill package), but the user-facing entry
# EXE is the native QuillVille launcher (quill-radio.exe) -- built
# separately by scripts/build_native_launcher.py and placed at the
# onedir root by scripts/build_release.ps1. The launcher is a
# process-spawn shim that resolves a Python interpreter and runs
# `python -m quill.apps.radio` -- see quill/native/launcher/README.md.
#
# The EXE() below is a PyInstaller-required placeholder -- COLLECT()
# refuses to run without one -- and is overwritten by the native
# launcher at the same path. The placeholder keeps the product's
# AppExeName name so the Inno installer ({app}\QuillRadio.exe) and the
# storage_mode._has_portable_evidence allowlist still resolve.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillRadio",
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
