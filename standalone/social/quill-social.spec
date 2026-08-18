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

# collect_all sweeps whatever is sitting in the package tree, and mypy, pytest
# and ruff all leave caches *inside* quill/. They are gitignored, so invisible
# in a diff, and they were being packaged into the installer: regenerable build
# detritus carrying absolute paths from the build machine. build_portable.py
# already filters them for the portable bundles (_DEV_CACHE_IGNORE).
_DEV_CACHE_PARTS = ("__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache")


def drop_dev_caches(entries):
    """Filter (source, dest) data entries whose path sits in a dev cache."""
    kept = []
    for entry in entries:
        source = str(entry[0]).replace("\\", "/")
        dest = str(entry[1]).replace("\\", "/")
        if any(f"/{part}/" in f"/{source}/" or f"/{part}/" in f"/{dest}/" for part in _DEV_CACHE_PARTS):
            continue
        kept.append(entry)
    return kept


quill_datas, quill_binaries, quill_hiddenimports = collect_all("quill")
social_datas, social_binaries, social_hiddenimports = collect_all("quill_social")
nacl_datas, nacl_binaries, nacl_hiddenimports = collect_all("nacl")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=quill_binaries + social_binaries + nacl_binaries,
    datas=drop_dev_caches(quill_datas + social_datas + nacl_datas),
    hiddenimports=quill_hiddenimports + social_hiddenimports + nacl_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # yt-dlp (~3 MB) is bundled only in the apps with a YouTube or
        # URL-import path (Radio, Studio, Converter). collect_all("quill")
        # force-includes quill.core.radio.youtube here too, so without this
        # exclude the tracer would follow its import and ship the whole
        # extractor set into an app that can never call it.
        "yt_dlp",
        # Social is text-and-network: QUILL fetches/uses these only for editor
        # features Social never touches (transcription, neural TTS, science).
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
        "pandas",
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

pyz = PYZ(a.pure)

# The icon is generated, not hand-drawn -- see scripts/build_app_icons.py, which
# owns the whole family's design system. Do not edit the .ico directly.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillSocial",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
    icon="assets/quill-social.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillSocial",
    upx=False,
)
