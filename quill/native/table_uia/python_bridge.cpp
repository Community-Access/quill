/*
 * QUILL Table Studio — Python/C++ bridge
 * python_bridge.cpp
 *
 * Wraps TableGridProvider for Python using pybind11.
 *
 * Exposes one module-level function:
 *   _quill_table_uia.attach(hwnd, get_dims, get_value, get_col_header,
 *                            get_row_header, get_focus, set_focus,
 *                            is_editable, caption)
 *     → returns a handle (int) to the native provider
 *
 *   _quill_table_uia.detach(handle)
 *     → releases the provider
 *
 *   _quill_table_uia.notify_focus(handle, row, col)
 *     → fires UIA_AutomationFocusChangedEventId for the given cell
 *
 *   _quill_table_uia.notify_structure(handle)
 *     → fires UIA_StructureChangedEventId
 *
 *   _quill_table_uia.notify_value(handle, row, col, new_value)
 *     → fires UIA_ValueValuePropertyId change event
 *
 * Build:
 *   pip install pybind11
 *   cmake -B build -DCMAKE_BUILD_TYPE=Release
 *   cmake --build build --target _quill_table_uia
 *
 * The resulting .pyd is placed on sys.path and imported optionally in
 * accessibility.py.  If the .pyd is absent the Python wx.Accessible
 * fallback is used transparently.
 */

// Pre-include windows.h ourselves with NOMINMAX set, *before* any
// pybind11 header. pybind11's headers pull in <windows.h> on the win32
// path; if we let pybind11 do that, UIAutomationCore.h (included by
// table_provider.hpp) sees windows.h's default `min`/`max` macros
// collide with the STL helpers used throughout the C++ code, and the
// downstream compile fails with 100+ errors in UIAutomationCore.h
// (the original symptom reported by issue #823). Defining NOMINMAX
// here is enough; do NOT define WIN32_LEAN_AND_MEAN, because UIA
// needs the full Windows header set (the COM base types in
// objbase.h are excluded when WIN32_LEAN_AND_MEAN is set, which
// breaks UIAutomationCore.h's first 50 lines of forward decls).
#if defined(_WIN32)
#  ifndef NOMINMAX
#    define NOMINMAX
#  endif
#  include <windows.h>
#endif

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>

#include "table_provider.hpp"

namespace py = pybind11;

// ── Python → wstring helpers ───────────────────────────────────────────────

static std::wstring str_to_wstr(const std::string& s) {
    return std::wstring(s.begin(), s.end());
}

static std::wstring pystr_to_wstr(const py::str& s) {
    return str_to_wstr(s.cast<std::string>());
}


// ── GIL-safe callback wrappers ─────────────────────────────────────────────
// UIA may call provider methods from a COM thread that does not hold the GIL.
// Each callback acquires the GIL before calling into Python.

static TableCallbacks build_callbacks(
        HWND hwnd,
        py::object get_dims_py,
        py::object get_value_py,
        py::object get_col_header_py,
        py::object get_row_header_py,
        py::object get_focus_py,
        py::object set_focus_py,
        py::object is_editable_py,
        const std::wstring& caption)
{
    TableCallbacks cb;
    cb.hwnd    = hwnd;
    cb.caption = caption;

    cb.get_dims = [get_dims_py]() -> TableDims {
        py::gil_scoped_acquire gil;
        auto tup  = get_dims_py().cast<std::pair<int,int>>();
        return {tup.first, tup.second};
    };

    cb.get_value = [get_value_py](int r, int c) -> std::wstring {
        py::gil_scoped_acquire gil;
        auto s = get_value_py(r, c).cast<std::string>();
        return str_to_wstr(s);
    };

    cb.get_col_header = [get_col_header_py](int c) -> std::wstring {
        py::gil_scoped_acquire gil;
        auto s = get_col_header_py(c).cast<std::string>();
        return str_to_wstr(s);
    };

    cb.get_row_header = [get_row_header_py](int r) -> std::wstring {
        py::gil_scoped_acquire gil;
        auto s = get_row_header_py(r).cast<std::string>();
        return str_to_wstr(s);
    };

    cb.get_focus = [get_focus_py]() -> TableFocus {
        py::gil_scoped_acquire gil;
        auto tup = get_focus_py().cast<std::pair<int,int>>();
        return {tup.first, tup.second};
    };

    cb.set_focus = [set_focus_py](int r, int c) {
        py::gil_scoped_acquire gil;
        set_focus_py(r, c);
    };

    cb.is_editable = [is_editable_py](int r, int c) -> bool {
        py::gil_scoped_acquire gil;
        return is_editable_py(r, c).cast<bool>();
    };

    return cb;
}


// ── Module definition ──────────────────────────────────────────────────────

PYBIND11_MODULE(_quill_table_uia, m) {
    m.doc() = "QUILL native Windows UIA provider for the Table Studio grid.";

    m.def("attach",
        [](py::int_ hwnd_int,
           py::object get_dims,
           py::object get_value,
           py::object get_col_header,
           py::object get_row_header,
           py::object get_focus,
           py::object set_focus,
           py::object is_editable,
           const std::string& caption) -> py::int_ {

            auto hwnd = reinterpret_cast<HWND>(
                static_cast<LONG_PTR>(hwnd_int.cast<long long>()));

            auto cb = build_callbacks(
                hwnd, get_dims, get_value, get_col_header, get_row_header,
                get_focus, set_focus, is_editable, str_to_wstr(caption));

            TableGridProvider* p = QuillTable_Attach(cb);
            return reinterpret_cast<long long>(p);
        },
        py::arg("hwnd"),
        py::arg("get_dims"),
        py::arg("get_value"),
        py::arg("get_col_header"),
        py::arg("get_row_header"),
        py::arg("get_focus"),
        py::arg("set_focus"),
        py::arg("is_editable"),
        py::arg("caption") = "",
        R"(
Attach the native UIA provider to a grid HWND.

Parameters
----------
hwnd          : int   — Win32 HWND of the wx.grid.Grid window
get_dims      : () -> (rows, cols)
get_value     : (row, col) -> str
get_col_header: (col) -> str
get_row_header: (row) -> str
get_focus     : () -> (row, col)
set_focus     : (row, col) -> None
is_editable   : (row, col) -> bool
caption       : str  — table caption / accessible name

Returns the provider handle (int) for use with detach() / notify_*().
)")
    ;

    m.def("detach",
        [](py::int_ handle) {
            auto* p = reinterpret_cast<TableGridProvider*>(
                static_cast<LONG_PTR>(handle.cast<long long>()));
            if (p) QuillTable_Detach(p);
        },
        py::arg("handle"),
        "Release the native UIA provider.");

    m.def("notify_focus",
        [](py::int_ handle, int row, int col) {
            auto* p = reinterpret_cast<TableGridProvider*>(
                static_cast<LONG_PTR>(handle.cast<long long>()));
            if (p) {
                py::gil_scoped_release rel;
                p->NotifyFocusChanged(row, col);
            }
        },
        py::arg("handle"), py::arg("row"), py::arg("col"),
        "Fire UIA focus-changed event for the given cell.");

    m.def("notify_structure",
        [](py::int_ handle) {
            auto* p = reinterpret_cast<TableGridProvider*>(
                static_cast<LONG_PTR>(handle.cast<long long>()));
            if (p) {
                py::gil_scoped_release rel;
                p->NotifyStructureChanged();
            }
        },
        py::arg("handle"),
        "Fire UIA structure-changed event (row/column inserted or deleted).");

    m.def("notify_value",
        [](py::int_ handle, int row, int col, const std::string& value) {
            auto* p = reinterpret_cast<TableGridProvider*>(
                static_cast<LONG_PTR>(handle.cast<long long>()));
            if (p) {
                py::gil_scoped_release rel;
                p->NotifyValueChanged(row, col, str_to_wstr(value));
            }
        },
        py::arg("handle"), py::arg("row"), py::arg("col"), py::arg("value"),
        "Fire UIA value-changed event for the given cell.");
}
