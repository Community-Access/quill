# PyInstaller spec for the shared QuillVille Runtime onedir.
#
# This is the ONE Python runtime every QuillVille app reuses: CPython +
# wxPython + the shared quill and quill_social packages, with a generic
# launcher (runtime_launcher.py) that dispatches `-m <module>` to any app.
# An app installer installs this bundle once (skipping it when a matching
# version is already present -- see quill.core.runtime_marker) and ships only
# a thin per-app launcher that runs QuillVilleRuntime.exe -m <the app>.
#
# collect_all("quill") + collect_all("quill_social") bring both packages'
# code and data; nacl is collected explicitly for Ed25519 verification (lazy
# imports the tracer would miss). The heavy optional ML stacks are NOT
# excluded here (unlike a single-app spec): the shared runtime is the union
# of every app's needs, and QUILL itself uses transcription/neural TTS -- those
# still resolve their models from the shared component store at runtime.

from PyInstaller.utils.hooks import collect_all

quill_datas, quill_binaries, quill_hidden = collect_all("quill")
social_datas, social_binaries, social_hidden = collect_all("quill_social")
nacl_datas, nacl_binaries, nacl_hidden = collect_all("nacl")

a = Analysis(
    ["runtime_launcher.py"],
    pathex=[],
    binaries=quill_binaries + social_binaries + nacl_binaries,
    datas=quill_datas + social_datas + nacl_datas,
    hiddenimports=quill_hidden + social_hidden + nacl_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="QuillVilleRuntime",
    console=False,
    upx=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="QuillVilleRuntime",
    upx=False,
)
