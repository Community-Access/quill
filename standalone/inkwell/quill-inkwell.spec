# PyInstaller spec for the Quill Inkwell onedir build.
# Build with: pyinstaller quill-inkwell.spec
#
# Onedir, not onefile, on purpose (mirrors Quill Weather): one built folder
# feeds BOTH products -- zip it for the portable, point Inno Setup at it for
# the system install -- and the app starts instantly instead of re-extracting
# to a temp folder on every launch. collect_all("quill") brings the entire
# quill package so the shared abbreviation library, dialog contract, sound
# packs, and announcement service are all present.
#
# Inkwell is the smallest app in the family: a keyboard hook, a matcher, two
# dialogs, and a tray icon. It needs no media, AI, or science stacks, so the
# exclude list below is aggressive.
#
# The entry-point EXE is replaced by the native QuillVille launcher
# (quill-inkwell.exe) placed at the onedir root by scripts/build_release.ps1
# after PyInstaller runs. See quill/native/launcher/README.md.

import os

from PyInstaller.utils.hooks import collect_all

quill_datas, quill_binaries, quill_hiddenimports = collect_all("quill")
# No bug-report credential ships in any QuillVille build (2026-09-26; feedback
# is email-only). collect_all("quill") would sweep a stale, gitignored
# quill/_feedback_token.py left in the checkout, so drop it here, exclude it
# below, and let scripts/check_no_credentials.py refuse the build if it or
# feedback_hub reaches the archive anyway.
quill_hiddenimports = [m for m in quill_hiddenimports if m != "quill._feedback_token"]
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
        # The retired bug-report credential and its client (see above).
        "quill._feedback_token",
        "feedback_hub",
        # yt-dlp (~3 MB) is bundled only in the apps with a YouTube or
        # URL-import path (Radio, Studio, Converter). collect_all("quill")
        # force-includes quill.core.radio.youtube here too, so without this
        # exclude the tracer would follow its import and ship the whole
        # extractor set into an app that can never call it.
        "yt_dlp",
        # Nothing about text expansion touches audio, transcription, neural
        # TTS, or the science stacks.
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
        "mpv",
        "ffmpeg",
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
        "PIL",
        "Pillow",
        "av",
        "imageio",
        "imageio_ffmpeg",
        "matplotlib",
        "scipy",
        # The 2026-08-18 [runtime] declarations put the editor's documents/GLOW
        # stack on every build machine (pymupdf, markitdown, magika, azure,
        # openai, msal). quill.core.glow imports its backend lazily and degrades
        # to absent, and this app can call none of it -- but a self-contained
        # sweep ships whatever is importable, so each is named here.
        "quill_glow_core",
        "acb_large_print",
        "pymupdf",
        "fitz",
        "markitdown",
        "magika",
        "azure",
        "openai",
        "msal",
        "curl_cffi",
    ],
    noarchive=False,
)

import sys as _sys  # noqa: E402

_sys.path.insert(0, os.path.join(SPECPATH, "..", "..", "scripts"))
from check_no_credentials import assert_toc_clean  # noqa: E402

assert_toc_clean(a.pure)

pyz = PYZ(a.pure)

# COLLECT-only build. The EXE() below is a PyInstaller-required placeholder --
# COLLECT() refuses to run without one -- and is overwritten by the native
# launcher at the same path. The placeholder keeps the product's AppExeName so
# the Inno installer ({app}\QuillInkwell.exe) still resolves.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillInkwell",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillInkwell",
    upx=False,
)
