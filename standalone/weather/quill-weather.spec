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

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillWeather",
    icon="assets/quill-weather.ico",
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
