/*
 * QuillVille runtime bootstrap -- see runtime_bootstrap.h.
 *
 * Flow (Windows):
 *   1. Ask (accessible Yes/No MessageBox) whether to download the runtime.
 *   2. Download the installer to %TEMP% with URLDownloadToFileW, driving a
 *      Win32 progress dialog from an IBindStatusCallback. The progress bar is a
 *      standard msctls_progress32 control (screen readers report its value),
 *      the status static text updates ("Downloading... 45%"), and the window
 *      title mirrors the percentage so JAWS/NVDA announce it as it changes.
 *   3. Run the installer and wait. It (Inno Setup) shows its own accessible
 *      install progress.
 *   4. Report success/failure to the caller, which then re-resolves.
 */

#include "runtime_bootstrap.h"

#ifndef _WIN32
int ql_bootstrap_runtime(const char *display_name, const char *runtime_url) {
    (void)display_name;
    (void)runtime_url;
    return 1; /* self-heal is Windows-only for now */
}
#else

#ifndef WIN32_LEAN_AND_MEAN
#  define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <commctrl.h>
#include <urlmon.h>
#include <shellapi.h>
#include <shlobj.h>
#include <objbase.h>
#include <stdio.h>

#pragma comment(lib, "urlmon.lib")
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "uuid.lib")  /* IID_IBindStatusCallback */

/* ------------------------------------------------------------------ */
/* Accessible progress dialog                                          */
/* ------------------------------------------------------------------ */

typedef struct {
    HWND hwnd;
    HWND bar;
    HWND label;
    const char *display_name;
    int last_pct;
} QlProgress;

static LRESULT CALLBACK ql_progress_wndproc(HWND h, UINT m, WPARAM w, LPARAM l) {
    if (m == WM_CLOSE) {
        /* Ignore the close button -- the download owns this window's lifetime. */
        return 0;
    }
    return DefWindowProcW(h, m, w, l);
}

static void ql_progress_pump(void) {
    MSG msg;
    while (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
}

static int ql_progress_create(QlProgress *p, const char *display_name) {
    static const wchar_t *cls = L"QuillVilleRuntimeBootstrap";
    INITCOMMONCONTROLSEX icc;
    icc.dwSize = sizeof(icc);
    icc.dwICC = ICC_PROGRESS_CLASS;
    InitCommonControlsEx(&icc);

    WNDCLASSW wc;
    ZeroMemory(&wc, sizeof(wc));
    wc.lpfnWndProc = ql_progress_wndproc;
    wc.hInstance = GetModuleHandleW(NULL);
    wc.lpszClassName = cls;
    wc.hCursor = LoadCursorW(NULL, (LPCWSTR)IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1);
    RegisterClassW(&wc);

    p->display_name = display_name;
    p->last_pct = -1;

    wchar_t title[256];
    swprintf(title, 256, L"Installing the QuillVille Runtime");

    int w = 440, h = 150;
    int sx = GetSystemMetrics(SM_CXSCREEN), sy = GetSystemMetrics(SM_CYSCREEN);
    p->hwnd = CreateWindowExW(
        WS_EX_DLGMODALFRAME | WS_EX_TOPMOST | WS_EX_CONTROLPARENT,
        cls, title,
        WS_CAPTION | WS_SYSMENU | WS_VISIBLE,
        (sx - w) / 2, (sy - h) / 2, w, h,
        NULL, NULL, wc.hInstance, NULL);
    if (!p->hwnd) return -1;

    p->label = CreateWindowExW(
        0, L"STATIC", L"Preparing to download the shared runtime...",
        WS_CHILD | WS_VISIBLE, 16, 16, w - 40, 40, p->hwnd, NULL, wc.hInstance, NULL);
    p->bar = CreateWindowExW(
        0, PROGRESS_CLASSW, NULL,
        WS_CHILD | WS_VISIBLE, 16, 64, w - 40, 22, p->hwnd, NULL, wc.hInstance, NULL);
    SendMessageW(p->bar, PBM_SETRANGE32, 0, 1000);
    /* Name the progress bar for assistive tech via the window text. */
    SetWindowTextW(p->bar, L"Runtime download progress");
    ShowWindow(p->hwnd, SW_SHOW);
    UpdateWindow(p->hwnd);
    ql_progress_pump();
    return 0;
}

static void ql_progress_set(QlProgress *p, int pct, ULONG done, ULONG total) {
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    SendMessageW(p->bar, PBM_SETPOS, (WPARAM)(pct * 10), 0);
    if (pct != p->last_pct) {
        p->last_pct = pct;
        wchar_t line[256], title[256];
        if (total > 0) {
            swprintf(line, 256,
                L"Downloading the QuillVille Runtime... %d%%  (%lu of %lu MB)",
                pct, (unsigned long)(done / (1024 * 1024)),
                (unsigned long)(total / (1024 * 1024)));
        } else {
            swprintf(line, 256, L"Downloading the QuillVille Runtime... %d%%", pct);
        }
        SetWindowTextW(p->label, line);
        /* Title mirrors % so screen readers announce the change. */
        swprintf(title, 256, L"Installing the QuillVille Runtime - %d%%", pct);
        SetWindowTextW(p->hwnd, title);
    }
    ql_progress_pump();
}

static void ql_progress_destroy(QlProgress *p) {
    if (p->hwnd) {
        DestroyWindow(p->hwnd);
        p->hwnd = NULL;
    }
    ql_progress_pump();
}

/* ------------------------------------------------------------------ */
/* IBindStatusCallback (C vtable) driving the progress dialog          */
/* ------------------------------------------------------------------ */

typedef struct {
    IBindStatusCallback iface;
    LONG ref;
    QlProgress *progress;
} QlCallback;

static QlCallback *ql_cb_from(IBindStatusCallback *This) {
    return (QlCallback *)This;
}

static HRESULT STDMETHODCALLTYPE cb_QueryInterface(IBindStatusCallback *This, REFIID riid, void **ppv) {
    if (IsEqualIID(riid, &IID_IUnknown) || IsEqualIID(riid, &IID_IBindStatusCallback)) {
        *ppv = This;
        This->lpVtbl->AddRef(This);
        return S_OK;
    }
    *ppv = NULL;
    return E_NOINTERFACE;
}
static ULONG STDMETHODCALLTYPE cb_AddRef(IBindStatusCallback *This) {
    return (ULONG)InterlockedIncrement(&ql_cb_from(This)->ref);
}
static ULONG STDMETHODCALLTYPE cb_Release(IBindStatusCallback *This) {
    return (ULONG)InterlockedDecrement(&ql_cb_from(This)->ref);
}
static HRESULT STDMETHODCALLTYPE cb_OnStartBinding(IBindStatusCallback *This, DWORD r, IBinding *b) {
    (void)This; (void)r; (void)b; return S_OK;
}
static HRESULT STDMETHODCALLTYPE cb_GetPriority(IBindStatusCallback *This, LONG *pr) {
    (void)This; if (pr) *pr = 0; return S_OK;
}
static HRESULT STDMETHODCALLTYPE cb_OnLowResource(IBindStatusCallback *This, DWORD r) {
    (void)This; (void)r; return S_OK;
}
static HRESULT STDMETHODCALLTYPE cb_OnProgress(IBindStatusCallback *This, ULONG done, ULONG total,
                                               ULONG code, LPCWSTR text) {
    (void)code; (void)text;
    QlCallback *cb = ql_cb_from(This);
    int pct = (total > 0) ? (int)((done * 100ULL) / total) : 0;
    ql_progress_set(cb->progress, pct, done, total);
    return S_OK;
}
static HRESULT STDMETHODCALLTYPE cb_OnStopBinding(IBindStatusCallback *This, HRESULT hr, LPCWSTR e) {
    (void)This; (void)hr; (void)e; return S_OK;
}
static HRESULT STDMETHODCALLTYPE cb_GetBindInfo(IBindStatusCallback *This, DWORD *f, BINDINFO *bi) {
    (void)This; (void)f; (void)bi; return S_OK;
}
static HRESULT STDMETHODCALLTYPE cb_OnDataAvailable(IBindStatusCallback *This, DWORD f, DWORD sz,
                                                    FORMATETC *fe, STGMEDIUM *sm) {
    (void)This; (void)f; (void)sz; (void)fe; (void)sm; return S_OK;
}
static HRESULT STDMETHODCALLTYPE cb_OnObjectAvailable(IBindStatusCallback *This, REFIID riid, IUnknown *u) {
    (void)This; (void)riid; (void)u; return S_OK;
}

static IBindStatusCallbackVtbl g_cb_vtbl = {
    cb_QueryInterface, cb_AddRef, cb_Release,
    cb_OnStartBinding, cb_GetPriority, cb_OnLowResource,
    cb_OnProgress, cb_OnStopBinding, cb_GetBindInfo,
    cb_OnDataAvailable, cb_OnObjectAvailable
};

/* ------------------------------------------------------------------ */
/* Public entry                                                        */
/* ------------------------------------------------------------------ */

int ql_bootstrap_runtime(const char *display_name, const char *runtime_url) {
    if (!runtime_url || !*runtime_url) return 1;

    /* 1. Ask. MB_ICONQUESTION + default Yes; accessible standard dialog. */
    char prompt[1024];
    snprintf(prompt, sizeof(prompt),
        "%s needs the QuillVille Runtime, a one-time shared download of about "
        "230 MB.\n\n"
        "Every QuillVille app reuses it, so this happens only once -- after "
        "that, all of them start instantly.\n\n"
        "Download and install it now?",
        display_name);
    if (MessageBoxA(NULL, prompt, display_name,
                    MB_YESNO | MB_ICONQUESTION | MB_SETFOREGROUND) != IDYES) {
        return 1;
    }

    /* 2. Destination in %TEMP%. */
    wchar_t temp_dir[MAX_PATH];
    if (!GetTempPathW(MAX_PATH, temp_dir)) return 1;
    wchar_t dest[MAX_PATH];
    swprintf(dest, MAX_PATH, L"%sQuillVille-Runtime-Setup.exe", temp_dir);

    wchar_t wurl[2048];
    MultiByteToWideChar(CP_UTF8, 0, runtime_url, -1, wurl, 2048);

    QlProgress progress;
    ZeroMemory(&progress, sizeof(progress));
    if (ql_progress_create(&progress, display_name) != 0) {
        /* No UI -- fall back to a quiet download so we still self-heal. */
    }

    QlCallback cb;
    cb.iface.lpVtbl = &g_cb_vtbl;
    cb.ref = 1;
    cb.progress = &progress;

    HRESULT hr = URLDownloadToFileW(NULL, wurl, dest, 0, &cb.iface);
    ql_progress_destroy(&progress);
    if (FAILED(hr)) {
        MessageBoxA(NULL,
            "The QuillVille Runtime could not be downloaded. Please check your "
            "internet connection and try again, or install the runtime manually "
            "from the QuillVille releases page.",
            display_name, MB_OK | MB_ICONERROR | MB_SETFOREGROUND);
        return 1;
    }

    /* 3. Run the installer and wait. Inno shows its own accessible progress. */
    SHELLEXECUTEINFOW sei;
    ZeroMemory(&sei, sizeof(sei));
    sei.cbSize = sizeof(sei);
    sei.fMask = SEE_MASK_NOCLOSEPROCESS;
    sei.lpVerb = L"open";
    sei.lpFile = dest;
    sei.nShow = SW_SHOWNORMAL;
    if (!ShellExecuteExW(&sei) || !sei.hProcess) {
        return 1;
    }
    WaitForSingleObject(sei.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(sei.hProcess, &code);
    CloseHandle(sei.hProcess);
    DeleteFileW(dest);

    /* 0 == Inno "success". The caller re-resolves the runtime regardless. */
    return (code == 0) ? 0 : 1;
}

#endif /* _WIN32 */
