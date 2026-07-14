# Table Studio native UIA provider (`_quill_table_uia`)

An optional, compiled Windows UI Automation provider for the Table Studio /
CSV Studio accessible grid. It implements a real `ITableProvider` /
`IGridProvider` with cell-level focus, value, and structure events and true
row/column header relationships — richer and more reliable than the
`wx.Accessible` MSAA fallback in `quill/ui/table_studio_accessible.py`.

**It is entirely optional.** When the compiled `_quill_table_uia.pyd` is present,
the grid uses it; when it is absent, the grid transparently falls back to the
MSAA provider. QUILL never requires the native module to run — this is a
deploy-time enhancement.

## What it exposes (pybind11)

```
attach(hwnd, get_dims, get_value, get_col_header, get_row_header,
       get_focus, set_focus, is_editable, caption) -> handle:int
detach(handle)
notify_focus(handle, row, col)      # UIA AutomationFocusChanged for a cell
notify_structure(handle)            # UIA StructureChanged
notify_value(handle, row, col, new) # UIA Value property change
```

## Building

Requires MSVC (Visual Studio 2022), the Windows 10 SDK (10.0.19041+),
`pip install pybind11`, and CMake 3.20+.

```
python scripts/build_table_uia.py            # wraps the CMake build
```

or manually:

```
cd quill/native/table_uia
cmake -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
cmake --install build --config Release
```

The resulting `_quill_table_uia.pyd` is staged in this directory;
`scripts/build_windows_distribution.py` copies it into the shipped runtime as an
optional dependency. If the toolchain is unavailable at build time, the build
skips it and QUILL ships with the MSAA fallback.
