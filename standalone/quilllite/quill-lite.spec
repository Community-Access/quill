# PyInstaller spec for the QuillLite onedir build.
# Build with: pyinstaller quill-lite.spec
#
# Onedir, not onefile, on purpose (mirrors every sibling): one built folder
# feeds BOTH products -- zip it for the portable, point Inno Setup at it for the
# system install -- and the app starts instantly instead of re-extracting to a
# temp folder on every launch. collect_all("quill") brings the whole quill
# package, which is what supplies the Rich Edit surface, the RTF safety scanner,
# the dialog contract, the F1 help engine and the announcement path.
#
# QuillLite is the second-smallest app in the family: one editor control, six
# small windows, and a settings file. It touches no media, no documents stack,
# no AI, no speech engines and no science stacks, so the exclude list below is
# aggressive -- and every entry has been checked to be unreachable from
# quill.apps.lite rather than merely unlikely.
#
# The entry-point EXE is replaced by the native QuillVille launcher
# (QuillLite.exe) placed at the onedir root by scripts/build_release.ps1 after
# PyInstaller runs. See quill/native/launcher/README.md.

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
        # yt-dlp (~3 MB) is bundled only in the apps with a YouTube or URL-import
        # path (Radio, Studio, Converter). collect_all("quill") force-includes
        # quill.core.radio.youtube here too, so without this exclude the tracer
        # would follow its import and ship the whole extractor set into an editor.
        "yt_dlp",
        # Nothing about editing text touches audio, transcription or neural TTS.
        "faster_whisper",
        "vosk",
        "kokoro_onnx",
        "onnxruntime",
        "torch",
        "numpy.f2py",
        "mpv",
        "ffmpeg",
        "sounddevice",
        "speech_recognition",
        "babel",  # i18n .po/.mo compiler -- build tooling only
        "pandas",
        "scipy",
        "matplotlib",
        # The documents stack. QuillLite reads .txt and .rtf and nothing else:
        # RTF goes to the native control through the Text Object Model, and
        # plain text is bytes. None of these readers is reachable from
        # quill.apps.lite.
        "pdfminer",
        "pdfplumber",
        "pypdfium2",
        "pypdfium2_raw",
        "pymupdf",
        "fitz",
        "docx",
        "pptx",
        "openpyxl",
        "markitdown",
        "magika",
        "lxml",
        "PIL",
        "Pillow",
        "pillow_heif",
        "av",
        "imageio",
        "imageio_ffmpeg",
        # The spell checker. QuillLite has no spell-check surface; the whole
        # pyenchant payload would be dead weight.
        "enchant",
        # AI and the cloud clients behind it. QuillLite has no AI surface at all,
        # by design, and that is the single biggest thing it does not ship.
        "openai",
        "anthropic",
        "azure",
        "msal",
        "huggingface_hub",
        "quill_glow_core",
        "acb_large_print",
        # Servers, databases and build tooling that a self-contained sweep will
        # otherwise pick up from the build machine's environment.
        "grpc",
        "psycopg",
        "psycopg2",
        "curl_cffi",
        "mypy",  # type checker -- must never ship in a release
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# COLLECT-only build. The EXE() below is a PyInstaller-required placeholder --
# COLLECT() refuses to run without one -- and is overwritten by the native
# launcher at the same path. The placeholder keeps the product's AppExeName so
# the Inno installer ({app}\QuillLite.exe) still resolves.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillLite",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillLite",
    upx=False,
)
