/*
 * QUILL Table Studio — Native Windows UIA Provider
 * table_provider.hpp
 *
 * Implements a true Microsoft UI Automation table/grid provider for the
 * virtual wx.ListCtrl grid in quill/ui/table_studio.py (TableListCtrl).
 *
 * Architecture
 * ────────────
 * Python owns the data (TableDocumentModel).  The C++ layer is intentionally
 * thin:
 *   • All table data is read through narrow Python callbacks (TableCallbacks).
 *   • Focus and selection changes are dispatched back to Python via
 *     SetFocusFn / SetSelectionFn.
 *   • The provider registers with UIA through WM_GETOBJECT on the grid HWND.
 *   • Virtual cell fragments are created on demand and reference-counted.
 *
 * UIA patterns implemented
 * ────────────────────────
 * TableGridProvider:
 *   IRawElementProviderSimple
 *   IRawElementProviderFragment
 *   IRawElementProviderFragmentRoot
 *   IGridProvider
 *   ITableProvider
 *   ISelectionProvider
 *
 * TableCellProvider (virtual child):
 *   IRawElementProviderSimple
 *   IRawElementProviderFragment
 *   IGridItemProvider
 *   ITableItemProvider
 *   IValueProvider
 *   ISelectionItemProvider
 *   IInvokeProvider
 *
 * Threading
 * ─────────
 * UIA may call provider methods from any thread.  Read-only properties are
 * satisfied from a lock-protected snapshot.  Focus/mutation requests are
 * marshaled back to the wx main thread via PostMessage / CallAfter.
 *
 * Build requirements
 * ──────────────────
 * Compiler:  MSVC 2022 or Clang 16+ (C++17)
 * Link:      UIAutomationCore.lib, oleaut32.lib, uuid.lib
 * Python:    pybind11 ≥ 2.10  (for the python_bridge.cpp wrapper)
 */

#pragma once

#ifndef QUILL_TABLE_UIA_H
#define QUILL_TABLE_UIA_H

#include <UIAutomation.h>
#include <wrl/client.h>

#include <atomic>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <utility>


// ── Python callback signatures ─────────────────────────────────────────────

struct TableDims { int rows; int cols; };
struct TableFocus { int row; int col; };

struct TableCallbacks {
    std::function<TableDims()>                   get_dims;
    std::function<std::wstring(int row, int col)> get_value;
    std::function<std::wstring(int col)>          get_col_header;
    std::function<std::wstring(int row)>          get_row_header;
    std::function<TableFocus()>                   get_focus;
    std::function<void(int row, int col)>         set_focus;
    std::function<bool(int row, int col)>         is_editable;
    std::wstring                                  caption;
    HWND                                          hwnd;
};


// ── Forward declarations ────────────────────────────────────────────────────

class TableGridProvider;
class TableCellProvider;


// ── Snapshot (thread-safe model read) ─────────────────────────────────────

struct ModelSnapshot {
    int          rows     = 0;
    int          cols     = 0;
    TableFocus   focus    = {0, 0};
    std::wstring caption;

    static ModelSnapshot capture(const TableCallbacks& cb) {
        ModelSnapshot s;
        auto dims = cb.get_dims();
        s.rows    = dims.rows;
        s.cols    = dims.cols;
        s.focus   = cb.get_focus();
        s.caption = cb.caption;
        return s;
    }
};


// ── TableCellProvider ──────────────────────────────────────────────────────

class TableCellProvider
    : public IRawElementProviderSimple
    , public IRawElementProviderFragment
    , public IGridItemProvider
    , public ITableItemProvider
    , public IValueProvider
    , public ISelectionItemProvider
    , public IInvokeProvider
{
public:
    TableCellProvider(TableGridProvider* grid, int row, int col);
    virtual ~TableCellProvider() = default;

    // IUnknown
    ULONG   STDMETHODCALLTYPE AddRef()  override;
    ULONG   STDMETHODCALLTYPE Release() override;
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void** ppv) override;

    // IRawElementProviderSimple
    HRESULT STDMETHODCALLTYPE get_ProviderOptions(ProviderOptions* pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetPatternProvider(PATTERNID pid, IUnknown** pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetPropertyValue(PROPERTYID pid, VARIANT* pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_HostRawElementProvider(
        IRawElementProviderSimple** pRetVal) override;

    // IRawElementProviderFragment
    HRESULT STDMETHODCALLTYPE Navigate(NavigateDirection dir,
        IRawElementProviderFragment** pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetRuntimeId(SAFEARRAY** pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_BoundingRectangle(UiaRect* pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetEmbeddedFragmentRoots(SAFEARRAY** pRetVal) override;
    HRESULT STDMETHODCALLTYPE SetFocus() override;
    HRESULT STDMETHODCALLTYPE get_FragmentRoot(
        IRawElementProviderFragmentRoot** pRetVal) override;

    // IGridItemProvider
    HRESULT STDMETHODCALLTYPE get_Row(int* pRetVal)     override;
    HRESULT STDMETHODCALLTYPE get_Column(int* pRetVal)  override;
    HRESULT STDMETHODCALLTYPE get_RowSpan(int* pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_ColumnSpan(int* pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_ContainingGrid(
        IRawElementProviderSimple** pRetVal) override;

    // ITableItemProvider
    HRESULT STDMETHODCALLTYPE GetRowHeaderItems(SAFEARRAY** pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetColumnHeaderItems(SAFEARRAY** pRetVal) override;

    // IValueProvider
    HRESULT STDMETHODCALLTYPE SetValue(LPCWSTR val) override;
    HRESULT STDMETHODCALLTYPE get_Value(BSTR* pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_IsReadOnly(BOOL* pRetVal) override;

    // ISelectionItemProvider
    HRESULT STDMETHODCALLTYPE Select()   override;
    HRESULT STDMETHODCALLTYPE AddToSelection()      override;
    HRESULT STDMETHODCALLTYPE RemoveFromSelection() override;
    HRESULT STDMETHODCALLTYPE get_IsSelected(BOOL* pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_SelectionContainer(
        IRawElementProviderSimple** pRetVal) override;

    // IInvokeProvider
    HRESULT STDMETHODCALLTYPE Invoke() override;

private:
    std::atomic<ULONG>  ref_count_{1};
    TableGridProvider*  grid_;      // non-owning back-pointer
    int                 row_;
    int                 col_;
};


// ── TableGridProvider (root) ───────────────────────────────────────────────

class TableGridProvider
    : public IRawElementProviderSimple
    , public IRawElementProviderFragment
    , public IRawElementProviderFragmentRoot
    , public IGridProvider
    , public ITableProvider
    , public ISelectionProvider
{
public:
    explicit TableGridProvider(const TableCallbacks& callbacks);
    virtual ~TableGridProvider();

    // IUnknown
    ULONG   STDMETHODCALLTYPE AddRef()  override;
    ULONG   STDMETHODCALLTYPE Release() override;
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void** ppv) override;

    // IRawElementProviderSimple
    HRESULT STDMETHODCALLTYPE get_ProviderOptions(ProviderOptions* pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetPatternProvider(PATTERNID pid, IUnknown** pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetPropertyValue(PROPERTYID pid, VARIANT* pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_HostRawElementProvider(
        IRawElementProviderSimple** pRetVal) override;

    // IRawElementProviderFragment
    HRESULT STDMETHODCALLTYPE Navigate(NavigateDirection dir,
        IRawElementProviderFragment** pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetRuntimeId(SAFEARRAY** pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_BoundingRectangle(UiaRect* pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetEmbeddedFragmentRoots(SAFEARRAY** pRetVal) override;
    HRESULT STDMETHODCALLTYPE SetFocus() override;
    HRESULT STDMETHODCALLTYPE get_FragmentRoot(
        IRawElementProviderFragmentRoot** pRetVal) override;

    // IRawElementProviderFragmentRoot
    HRESULT STDMETHODCALLTYPE ElementProviderFromPoint(
        double x, double y,
        IRawElementProviderFragment** pRetVal) override;
    HRESULT STDMETHODCALLTYPE GetFocus(
        IRawElementProviderFragment** pRetVal) override;

    // IGridProvider
    HRESULT STDMETHODCALLTYPE GetItem(int row, int col,
        IRawElementProviderSimple** pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_RowCount(int* pRetVal)    override;
    HRESULT STDMETHODCALLTYPE get_ColumnCount(int* pRetVal) override;

    // ITableProvider
    HRESULT STDMETHODCALLTYPE GetRowHeaders(SAFEARRAY** pRetVal)    override;
    HRESULT STDMETHODCALLTYPE GetColumnHeaders(SAFEARRAY** pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_RowOrColumnMajor(
        RowOrColumnMajor* pRetVal) override;

    // ISelectionProvider
    HRESULT STDMETHODCALLTYPE GetSelection(SAFEARRAY** pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_CanSelectMultiple(BOOL* pRetVal) override;
    HRESULT STDMETHODCALLTYPE get_IsSelectionRequired(BOOL* pRetVal) override;

    // ── Called by Python when model state changes ──────────────────────
    void NotifyFocusChanged(int row, int col);
    void NotifyStructureChanged();
    void NotifyValueChanged(int row, int col, const std::wstring& new_value);

    // ── Internal helpers used by TableCellProvider ────────────────────
    const TableCallbacks& callbacks() const { return callbacks_; }
    TableCellProvider*    get_or_create_cell(int row, int col);

    // Hook for WM_GETOBJECT.  Call from a subclassed WndProc.
    static LRESULT HandleWmGetObject(TableGridProvider* provider,
                                     WPARAM wParam, LPARAM lParam);

private:
    std::atomic<ULONG>   ref_count_{1};
    TableCallbacks       callbacks_;
    mutable std::mutex   snap_mutex_;
    ModelSnapshot        snapshot_;   // refreshed before every UIA query

    // Cell fragment cache: keyed by row*max_cols + col
    std::mutex                               cell_mutex_;
    std::unordered_map<int, TableCellProvider*> cell_cache_;

    void refresh_snapshot();
    int  cell_key(int row, int col) const;
};


// ── Entry point ────────────────────────────────────────────────────────────
// Called from python_bridge.cpp to attach the provider to a grid HWND.
TableGridProvider* QuillTable_Attach(const TableCallbacks& cbs);
void               QuillTable_Detach(TableGridProvider* provider);

#endif // QUILL_TABLE_UIA_H
