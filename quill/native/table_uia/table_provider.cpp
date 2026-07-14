/*
 * QUILL Table Studio — Native Windows UIA Provider
 * table_provider.cpp
 *
 * Implementation skeleton.  IUnknown boilerplate is complete.  The key UIA
 * property and pattern handlers include enough logic to demonstrate the
 * approach; the remainder are stubs that return S_OK / E_NOTIMPL until
 * filled in during Spike 3 (PRD §32).
 *
 * Build:  cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build
 * Output: _quill_table_uia.pyd  (via python_bridge.cpp + pybind11)
 */

#include "table_provider.hpp"

#include <UIAutomation.h>
#include <UIAutomationClient.h>
#include <cassert>
#include <stdexcept>

// Handy BSTR wrapper
static BSTR BstrFromWide(const std::wstring& s) {
    return SysAllocStringLen(s.data(), static_cast<UINT>(s.size()));
}


// ── TableGridProvider ──────────────────────────────────────────────────────

TableGridProvider::TableGridProvider(const TableCallbacks& callbacks)
    : callbacks_(callbacks)
{
    refresh_snapshot();
}

TableGridProvider::~TableGridProvider() {
    std::lock_guard<std::mutex> lk(cell_mutex_);
    for (auto& [key, cell] : cell_cache_) {
        cell->Release();
    }
    cell_cache_.clear();
}

ULONG STDMETHODCALLTYPE TableGridProvider::AddRef() {
    return ++ref_count_;
}

ULONG STDMETHODCALLTYPE TableGridProvider::Release() {
    ULONG rc = --ref_count_;
    if (rc == 0) delete this;
    return rc;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::QueryInterface(
        REFIID riid, void** ppv) {
    if (!ppv) return E_POINTER;
    *ppv = nullptr;

    if (riid == IID_IUnknown)
        *ppv = static_cast<IRawElementProviderSimple*>(this);
    else if (riid == IID_IRawElementProviderSimple)
        *ppv = static_cast<IRawElementProviderSimple*>(this);
    else if (riid == IID_IRawElementProviderFragment)
        *ppv = static_cast<IRawElementProviderFragment*>(this);
    else if (riid == IID_IRawElementProviderFragmentRoot)
        *ppv = static_cast<IRawElementProviderFragmentRoot*>(this);
    else if (riid == IID_IGridProvider)
        *ppv = static_cast<IGridProvider*>(this);
    else if (riid == IID_ITableProvider)
        *ppv = static_cast<ITableProvider*>(this);
    else if (riid == IID_ISelectionProvider)
        *ppv = static_cast<ISelectionProvider*>(this);
    else
        return E_NOINTERFACE;

    AddRef();
    return S_OK;
}

// ── IRawElementProviderSimple ──────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableGridProvider::get_ProviderOptions(
        ProviderOptions* pRetVal) {
    if (!pRetVal) return E_POINTER;
    // ServerSideProvider: we own the provider.
    // ProviderOwnsSetFocus: we handle SetFocus ourselves.
    *pRetVal = static_cast<ProviderOptions>(
        ProviderOptions_ServerSideProvider |
        ProviderOptions_UseComThreading);
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::GetPatternProvider(
        PATTERNID pid, IUnknown** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    if (pid == UIA_GridPatternId   ||
        pid == UIA_TablePatternId  ||
        pid == UIA_SelectionPatternId) {
        *pRetVal = static_cast<IRawElementProviderSimple*>(this);
        AddRef();
    }
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::GetPropertyValue(
        PROPERTYID pid, VARIANT* pRetVal) {
    if (!pRetVal) return E_POINTER;
    VariantInit(pRetVal);
    refresh_snapshot();

    switch (pid) {
    case UIA_NamePropertyId: {
        std::wstring name = snapshot_.caption.empty()
            ? L"Table"
            : snapshot_.caption;
        name += L". " + std::to_wstring(snapshot_.rows) + L" rows, "
              + std::to_wstring(snapshot_.cols) + L" columns.";
        pRetVal->vt      = VT_BSTR;
        pRetVal->bstrVal = BstrFromWide(name);
        return S_OK;
    }
    case UIA_ControlTypePropertyId:
        pRetVal->vt   = VT_I4;
        pRetVal->lVal = UIA_TableControlTypeId;
        return S_OK;
    case UIA_IsKeyboardFocusablePropertyId:
        pRetVal->vt       = VT_BOOL;
        pRetVal->boolVal  = VARIANT_TRUE;
        return S_OK;
    case UIA_IsGridPatternAvailablePropertyId:
    case UIA_IsTablePatternAvailablePropertyId:
        pRetVal->vt       = VT_BOOL;
        pRetVal->boolVal  = VARIANT_TRUE;
        return S_OK;
    default:
        break;
    }
    return S_OK;  // return VT_EMPTY for unrecognized properties
}

HRESULT STDMETHODCALLTYPE TableGridProvider::get_HostRawElementProvider(
        IRawElementProviderSimple** pRetVal) {
    if (!pRetVal) return E_POINTER;
    // Return the HWND-backed provider so UIA can correlate our virtual tree
    // with the actual Win32 window tree.
    return UiaHostProviderFromHwnd(callbacks_.hwnd, pRetVal);
}

// ── IRawElementProviderFragment ────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableGridProvider::Navigate(
        NavigateDirection dir, IRawElementProviderFragment** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;

    if (dir == NavigateDirection_FirstChild) {
        // Return the top-left cell as first child
        auto* cell = get_or_create_cell(0, 0);
        if (cell) {
            *pRetVal = static_cast<IRawElementProviderFragment*>(cell);
            cell->AddRef();
        }
    }
    // NavigateDirection_LastChild, _Parent, _NextSibling, _PreviousSibling:
    // stub — implement during Spike 3
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::GetRuntimeId(SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    // Grid itself gets a runtime id based on the HWND.
    int ids[] = { UiaAppendRuntimeId, static_cast<int>(
        reinterpret_cast<LONG_PTR>(callbacks_.hwnd)) };
    *pRetVal = SafeArrayCreateVector(VT_I4, 0, 2);
    for (LONG i = 0; i < 2; ++i)
        SafeArrayPutElement(*pRetVal, &i, &ids[i]);
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::get_BoundingRectangle(
        UiaRect* pRetVal) {
    if (!pRetVal) return E_POINTER;
    RECT rc{};
    if (GetWindowRect(callbacks_.hwnd, &rc)) {
        pRetVal->left   = static_cast<double>(rc.left);
        pRetVal->top    = static_cast<double>(rc.top);
        pRetVal->width  = static_cast<double>(rc.right  - rc.left);
        pRetVal->height = static_cast<double>(rc.bottom - rc.top);
    }
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::GetEmbeddedFragmentRoots(
        SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::SetFocus() {
    SetForegroundWindow(callbacks_.hwnd);
    ::SetFocus(callbacks_.hwnd);
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::get_FragmentRoot(
        IRawElementProviderFragmentRoot** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = static_cast<IRawElementProviderFragmentRoot*>(this);
    AddRef();
    return S_OK;
}

// ── IRawElementProviderFragmentRoot ───────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableGridProvider::ElementProviderFromPoint(
        double x, double y, IRawElementProviderFragment** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    // Stub: in production map screen coords → grid row/col via wxGrid API
    // then return the appropriate TableCellProvider.
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::GetFocus(
        IRawElementProviderFragment** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    refresh_snapshot();
    auto* cell = get_or_create_cell(snapshot_.focus.row, snapshot_.focus.col);
    if (cell) {
        *pRetVal = static_cast<IRawElementProviderFragment*>(cell);
        cell->AddRef();
    }
    return S_OK;
}

// ── IGridProvider ──────────────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableGridProvider::GetItem(
        int row, int col, IRawElementProviderSimple** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    refresh_snapshot();
    if (row < 0 || col < 0 || row >= snapshot_.rows || col >= snapshot_.cols)
        return E_INVALIDARG;
    auto* cell = get_or_create_cell(row, col);
    if (cell) {
        *pRetVal = static_cast<IRawElementProviderSimple*>(cell);
        cell->AddRef();
    }
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::get_RowCount(int* pRetVal) {
    if (!pRetVal) return E_POINTER;
    refresh_snapshot();
    *pRetVal = snapshot_.rows;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::get_ColumnCount(int* pRetVal) {
    if (!pRetVal) return E_POINTER;
    refresh_snapshot();
    *pRetVal = snapshot_.cols;
    return S_OK;
}

// ── ITableProvider ─────────────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableGridProvider::GetRowHeaders(SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;  // TODO: return row-header cell providers when implemented
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::GetColumnHeaders(SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    // TODO: return a SAFEARRAY of IRawElementProviderSimple* for column headers.
    *pRetVal = nullptr;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::get_RowOrColumnMajor(
        RowOrColumnMajor* pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = RowOrColumnMajor_RowMajor;
    return S_OK;
}

// ── ISelectionProvider ─────────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableGridProvider::GetSelection(SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    refresh_snapshot();
    // Return the focused cell as the single selected item.
    auto* cell = get_or_create_cell(snapshot_.focus.row, snapshot_.focus.col);
    *pRetVal = SafeArrayCreateVector(VT_UNKNOWN, 0, 1);
    IUnknown* unk = static_cast<IRawElementProviderSimple*>(cell);
    unk->AddRef();
    LONG idx = 0;
    SafeArrayPutElement(*pRetVal, &idx, unk);
    unk->Release();
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::get_CanSelectMultiple(
        BOOL* pRetVal) {
    if (!pRetVal) return E_POINTER;
    // The backing widget is a wx.ListCtrl created with LC_SINGLE_SEL, so UIA
    // clients must not be told multi-select is possible (#802 review).
    *pRetVal = VARIANT_FALSE;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableGridProvider::get_IsSelectionRequired(
        BOOL* pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = VARIANT_FALSE;
    return S_OK;
}

// ── Notifications fired from Python ───────────────────────────────────────

void TableGridProvider::NotifyFocusChanged(int row, int col) {
    auto* cell = get_or_create_cell(row, col);
    if (cell) {
        UiaRaiseAutomationEvent(
            static_cast<IRawElementProviderSimple*>(cell),
            UIA_AutomationFocusChangedEventId);
    }
}

void TableGridProvider::NotifyStructureChanged() {
    refresh_snapshot();
    UiaRaiseStructureChangedEvent(
        static_cast<IRawElementProviderSimple*>(this),
        StructureChangeType_ChildrenBulkRemoved,
        nullptr, 0);
}

void TableGridProvider::NotifyValueChanged(
        int row, int col, const std::wstring& new_value) {
    auto* cell = get_or_create_cell(row, col);
    if (!cell) return;
    // Old value is VT_EMPTY (we do not track it); passing the same VARIANT
    // as both old and new made clients treat the event as a no-op (#802).
    VARIANT old_var;
    VariantInit(&old_var);  // VT_EMPTY
    VARIANT new_var;
    VariantInit(&new_var);
    new_var.vt      = VT_BSTR;
    new_var.bstrVal = BstrFromWide(new_value);
    UiaRaiseAutomationPropertyChangedEvent(
        static_cast<IRawElementProviderSimple*>(cell),
        UIA_ValueValuePropertyId,
        old_var, new_var);
    VariantClear(&new_var);
}

// ── WM_GETOBJECT hook ──────────────────────────────────────────────────────

LRESULT TableGridProvider::HandleWmGetObject(
        TableGridProvider* provider, WPARAM wParam, LPARAM lParam) {
    if (static_cast<DWORD>(lParam) != UiaRootObjectId)
        return DefWindowProc(provider->callbacks_.hwnd, WM_GETOBJECT, wParam, lParam);
    return UiaReturnRawElementProvider(
        provider->callbacks_.hwnd, wParam, lParam,
        static_cast<IRawElementProviderSimple*>(provider));
}

// ── Helpers ────────────────────────────────────────────────────────────────

void TableGridProvider::refresh_snapshot() {
    std::lock_guard<std::mutex> lk(snap_mutex_);
    snapshot_ = ModelSnapshot::capture(callbacks_);
}

int TableGridProvider::cell_key(int row, int col) const {
    // A 16-bit column space supports up to 65535 columns.
    return row * 65536 + col;
}

TableCellProvider* TableGridProvider::get_or_create_cell(int row, int col) {
    // Returns a borrowed pointer: the cache holds the one owning reference
    // (released in ~TableGridProvider). Callers that hand the provider to UIA
    // AddRef at the hand-off. The old extra AddRef here leaked one reference
    // per lookup and kept cells alive past cache cleanup (#802 review).
    int key = cell_key(row, col);
    std::lock_guard<std::mutex> lk(cell_mutex_);
    auto it = cell_cache_.find(key);
    if (it != cell_cache_.end()) {
        return it->second;
    }
    auto* cell = new TableCellProvider(this, row, col);  // refcount 1 = cache reference
    cell_cache_[key] = cell;
    return cell;
}


// ── TableCellProvider ──────────────────────────────────────────────────────

TableCellProvider::TableCellProvider(TableGridProvider* grid, int row, int col)
    : grid_(grid), row_(row), col_(col)
{}

ULONG STDMETHODCALLTYPE TableCellProvider::AddRef() { return ++ref_count_; }

ULONG STDMETHODCALLTYPE TableCellProvider::Release() {
    ULONG rc = --ref_count_;
    if (rc == 0) delete this;
    return rc;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::QueryInterface(
        REFIID riid, void** ppv) {
    if (!ppv) return E_POINTER;
    *ppv = nullptr;

    if (riid == IID_IUnknown || riid == IID_IRawElementProviderSimple)
        *ppv = static_cast<IRawElementProviderSimple*>(this);
    else if (riid == IID_IRawElementProviderFragment)
        *ppv = static_cast<IRawElementProviderFragment*>(this);
    else if (riid == IID_IGridItemProvider)
        *ppv = static_cast<IGridItemProvider*>(this);
    else if (riid == IID_ITableItemProvider)
        *ppv = static_cast<ITableItemProvider*>(this);
    else if (riid == IID_IValueProvider)
        *ppv = static_cast<IValueProvider*>(this);
    else if (riid == IID_ISelectionItemProvider)
        *ppv = static_cast<ISelectionItemProvider*>(this);
    else if (riid == IID_IInvokeProvider)
        *ppv = static_cast<IInvokeProvider*>(this);
    else
        return E_NOINTERFACE;

    AddRef();
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_ProviderOptions(
        ProviderOptions* pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = static_cast<ProviderOptions>(
        ProviderOptions_ServerSideProvider | ProviderOptions_UseComThreading);
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::GetPatternProvider(
        PATTERNID pid, IUnknown** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    if (pid == UIA_GridItemPatternId   ||
        pid == UIA_TableItemPatternId  ||
        pid == UIA_ValuePatternId      ||
        pid == UIA_SelectionItemPatternId ||
        pid == UIA_InvokePatternId) {
        *pRetVal = static_cast<IRawElementProviderSimple*>(this);
        AddRef();
    }
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::GetPropertyValue(
        PROPERTYID pid, VARIANT* pRetVal) {
    if (!pRetVal) return E_POINTER;
    VariantInit(pRetVal);
    const auto& cb = grid_->callbacks();

    switch (pid) {
    case UIA_NamePropertyId: {
        // Compose: "[row header], [col header], [value]"
        std::wstring rh  = cb.get_row_header(row_);
        std::wstring ch  = cb.get_col_header(col_);
        std::wstring val = cb.get_value(row_, col_);
        if (val.empty()) val = L"Blank";
        std::wstring name = rh + L", " + ch + L", " + val;
        pRetVal->vt      = VT_BSTR;
        pRetVal->bstrVal = BstrFromWide(name);
        return S_OK;
    }
    case UIA_ControlTypePropertyId:
        pRetVal->vt   = VT_I4;
        pRetVal->lVal = UIA_DataItemControlTypeId;
        return S_OK;
    case UIA_IsKeyboardFocusablePropertyId:
        pRetVal->vt      = VT_BOOL;
        pRetVal->boolVal = VARIANT_TRUE;
        return S_OK;
    case UIA_HasKeyboardFocusPropertyId: {
        auto focus = cb.get_focus();
        pRetVal->vt      = VT_BOOL;
        pRetVal->boolVal = (focus.row == row_ && focus.col == col_)
                           ? VARIANT_TRUE : VARIANT_FALSE;
        return S_OK;
    }
    case UIA_IsOffscreenPropertyId:
        pRetVal->vt      = VT_BOOL;
        pRetVal->boolVal = VARIANT_FALSE;   // simplified; clip to grid rect in production
        return S_OK;
    default:
        break;
    }
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_HostRawElementProvider(
        IRawElementProviderSimple** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;   // virtual child — no HWND
    return S_OK;
}

// ── IRawElementProviderFragment (cell) ────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableCellProvider::Navigate(
        NavigateDirection dir, IRawElementProviderFragment** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    // TODO: implement full sibling/parent navigation in Spike 3
    if (dir == NavigateDirection_Parent) {
        *pRetVal = static_cast<IRawElementProviderFragment*>(grid_);
        grid_->AddRef();
    }
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::GetRuntimeId(SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    // Stable ID: [UiaAppendRuntimeId, hwnd_int, row, col]
    int ids[] = {
        UiaAppendRuntimeId,
        static_cast<int>(reinterpret_cast<LONG_PTR>(
            grid_->callbacks().hwnd)),
        row_,
        col_
    };
    *pRetVal = SafeArrayCreateVector(VT_I4, 0, 4);
    for (LONG i = 0; i < 4; ++i)
        SafeArrayPutElement(*pRetVal, &i, &ids[i]);
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_BoundingRectangle(
        UiaRect* pRetVal) {
    if (!pRetVal) return E_POINTER;
    // TODO: query wxGrid for physical cell rect and map to screen coords.
    *pRetVal = {0, 0, 0, 0};
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::GetEmbeddedFragmentRoots(
        SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::SetFocus() {
    // Ask Python to move the logical cursor to this cell.
    grid_->callbacks().set_focus(row_, col_);
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_FragmentRoot(
        IRawElementProviderFragmentRoot** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = static_cast<IRawElementProviderFragmentRoot*>(grid_);
    grid_->AddRef();
    return S_OK;
}

// ── IGridItemProvider ──────────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableCellProvider::get_Row(int* pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = row_;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_Column(int* pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = col_;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_RowSpan(int* pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = 1;  // spans handled in Phase 4
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_ColumnSpan(int* pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = 1;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_ContainingGrid(
        IRawElementProviderSimple** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = static_cast<IRawElementProviderSimple*>(grid_);
    grid_->AddRef();
    return S_OK;
}

// ── ITableItemProvider ─────────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableCellProvider::GetRowHeaderItems(
        SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    // TODO: return provider for the row-header cell (col 0) if configured
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::GetColumnHeaderItems(
        SAFEARRAY** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = nullptr;
    // TODO: return provider for the column-header cell (row -1)
    return S_OK;
}

// ── IValueProvider ─────────────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableCellProvider::SetValue(LPCWSTR val) {
    grid_->callbacks().set_focus(row_, col_);
    // NOTE: actual value change must be dispatched to the Python main thread.
    // In production: PostMessage(hwnd, WM_QUILL_SET_CELL_VALUE, row_, col_)
    // and pass val through a thread-safe queue.
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_Value(BSTR* pRetVal) {
    if (!pRetVal) return E_POINTER;
    std::wstring v = grid_->callbacks().get_value(row_, col_);
    *pRetVal = BstrFromWide(v.empty() ? L"Blank" : v);
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_IsReadOnly(BOOL* pRetVal) {
    if (!pRetVal) return E_POINTER;
    bool editable = grid_->callbacks().is_editable(row_, col_);
    *pRetVal = editable ? VARIANT_FALSE : VARIANT_TRUE;
    return S_OK;
}

// ── ISelectionItemProvider ─────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableCellProvider::Select() {
    grid_->callbacks().set_focus(row_, col_);
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::AddToSelection()       { return S_OK; }
HRESULT STDMETHODCALLTYPE TableCellProvider::RemoveFromSelection()  { return S_OK; }

HRESULT STDMETHODCALLTYPE TableCellProvider::get_IsSelected(BOOL* pRetVal) {
    if (!pRetVal) return E_POINTER;
    auto focus = grid_->callbacks().get_focus();
    *pRetVal = (focus.row == row_ && focus.col == col_)
               ? VARIANT_TRUE : VARIANT_FALSE;
    return S_OK;
}

HRESULT STDMETHODCALLTYPE TableCellProvider::get_SelectionContainer(
        IRawElementProviderSimple** pRetVal) {
    if (!pRetVal) return E_POINTER;
    *pRetVal = static_cast<IRawElementProviderSimple*>(grid_);
    grid_->AddRef();
    return S_OK;
}

// ── IInvokeProvider ────────────────────────────────────────────────────────

HRESULT STDMETHODCALLTYPE TableCellProvider::Invoke() {
    // Activation = move focus and enter edit mode.
    grid_->callbacks().set_focus(row_, col_);
    // TODO: PostMessage(hwnd, WM_QUILL_INVOKE_CELL_EDIT, row_, col_)
    return S_OK;
}


// ── Module entry points ────────────────────────────────────────────────────

TableGridProvider* QuillTable_Attach(const TableCallbacks& cbs) {
    return new TableGridProvider(cbs);
}

void QuillTable_Detach(TableGridProvider* provider) {
    if (provider) provider->Release();
}
