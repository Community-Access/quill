# PyInstaller spec for QuillLite. One directory, not one file: a onefile build
# unpacks wxPython on every launch, and startup speed is the whole point.
from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "tools" / "run_quilllite.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "quilllite" / "lib" / "nvdaControllerClient64.dll"), "quilllite/lib"),
           (str(root / "quilllite" / "lib" / "nvdaControllerClient32.dll"), "quilllite/lib")],
    hiddenimports=["comtypes", "comtypes.client"],
    excludes=["tkinter", "numpy", "PIL", "matplotlib", "pytest", "setuptools", "pip",
              "unittest", "pydoc_data", "sqlite3", "email", "http", "xmlrpc"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QuillLite",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="QuillLite",
)
