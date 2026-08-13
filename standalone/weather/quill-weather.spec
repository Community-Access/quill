# PyInstaller spec for the Quill Weather onedir build.
# Build with: pyinstaller quill-weather.spec
#
# Onedir, not onefile, on purpose (mirrors Quill Radio): one built folder feeds
# BOTH products -- zip it for the portable, point Inno Setup at it for the
# system install -- and the app starts instantly instead of re-extracting to a
# temp folder on every launch. collect_all("quill") brings the entire quill
# package (code and package data: schemas, the bundled NOAA transmitter
# snapshot, the weather-alert sound, assets) so nothing the shared weather code
# needs is missing.
#
# Note: drop a `quill-weather.ico` into assets/ before building (or set
# icon=None). Quill Weather is a much smaller app than Radio -- it needs no
# ffmpeg or mpv engine -- so this build excludes the heavy media/AI stacks.
#
# As of 2026-07-24, the entry-point EXE is NOT produced by PyInstaller
# anymore -- it is replaced by the native QuillVille launcher
# (quill-weather.exe, ~50-200 KB, compiled from quill/native/launcher/) which
# is placed at the onedir root by scripts/build_release.ps1 after
# PyInstaller runs. See quill/native/launcher/README.md for the design.

from PyInstaller.utils.hooks import collect_all

quill_datas, quill_binaries, quill_hiddenimports = collect_all("quill")
# PyNaCl (Ed25519 signature verification for signed update manifests).
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
        # yt-dlp (~3 MB) is bundled only in the apps with a YouTube or
        # URL-import path (Radio, Studio, Converter). collect_all("quill")
        # force-includes quill.core.radio.youtube here too, so without this
        # exclude the tracer would follow its import and ship the whole
        # extractor set into an app that can never call it.
        "yt_dlp",
        # Quill Weather never touches audio playback/recording, transcription,
        # neural TTS, or the science stacks -- keep the build small.
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
        "mpv",
        "ffmpeg",
        # Heavy transitive dependencies the app never imports at runtime (verified
        # by tracing `import quill.apps.weather`). collect_all("quill") force-
        # includes every quill submodule -- AI vision, PDF I/O, publishing, dev
        # tooling -- and PyInstaller then follows their imports into these libs.
        # Excluding them roughly halves the build (babel alone is ~152 MB).
        "babel",  # i18n .po/.mo compiler -- build tooling only
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

# COLLECT-only build (see quill-radio.spec for the rationale). The native
# QuillVille launcher (quill-weather.exe) is built by
# scripts/build_native_launcher.py and placed at the onedir root by
# scripts/build_release.ps1. The EXE() below is a PyInstaller-required
# placeholder -- COLLECT() refuses to run without one -- and is overwritten
# by the native launcher at the same path. The placeholder keeps the
# product's AppExeName name so the Inno installer ({app}\QuillWeather.exe)
# and the storage_mode._has_portable_evidence allowlist still resolve.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillWeather",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillWeather",
    upx=False,
)
