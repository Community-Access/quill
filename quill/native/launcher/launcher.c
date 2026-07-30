/*
 * QuillVille native launcher -- a tiny Windows executable that resolves a
 * Python runtime and spawns `python.exe -m quill.apps.<product>` inside it.
 *
 * This replaces the prior practice of stamping a copy of pythonw.exe with
 * rcedit (see _stamp_quill_launcher in scripts/build_windows_distribution.py),
 * which was a repackaged-Python binary that AV heuristics routinely flagged.
 *
 * One source file compiles to one executable per product. The product identity
 * is supplied at build time via -DPRODUCT_* macros (see CMakeLists.txt):
 *
 *   PRODUCT_NAME         -- internal/executable name (e.g. "quill-radio")
 *   PRODUCT_DISPLAY_NAME -- user-facing name (e.g. "Quill Radio")
 *   PRODUCT_VERSION      -- dotted version string (e.g. "2.2.0")
 *   PRODUCT_PYTHON_MODULE -- Python module to invoke (e.g. "quill.apps.radio")
 *   PRODUCT_REPO         -- update-feed repo (used by the updater)
 *   PRODUCT_APP_ID       -- AppUserModelID for taskbar grouping
 *
 * Runtime resolution order (see runtime_resolve.c):
 *
 *   1. Shared QuillVille runtime at %LOCALAPPDATA%\QuillVille\Runtime\<suite-major>\
 *      when the marker file (quillville-runtime.json) is present and valid.
 *   2. Private embedded runtime beside this launcher (the onedir's python.exe
 *      or _internal\python.exe from PyInstaller).
 *   3. pythonw.exe beside this launcher (legacy fallback during transition).
 *
 * If none of the above yield a runnable interpreter, the launcher shows a
 * clean error message and exits with code 2 -- never a crash dialog.
 *
 * Cross-platform: this same source compiles on macOS and Linux. The Windows
 * path uses Win32 APIs; the POSIX path uses execve. The product macros are
 * shared.
 */

#include "runtime_resolve.h"
#include "runtime_bootstrap.h"
#include "product.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
/* MSVC deprecates the POSIX name strdup; the C standard conformant
 * alternative is _strdup. The launcher's only strdup calls are in
 * build_argv() and they want a heap-allocated copy of a C string --
 * the same behavior as _strdup. Suppress the warning at the file
 * scope; alternative would be four #pragma warning(push/pop) pairs
 * around each call site, which is more noise than the warning. */
#  pragma warning(disable : 4996)
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  include <windows.h>
#  include <shellapi.h>
#  include <io.h>
#  define QL_PATH_SEP "\\"
#  define QL_PATH_SEP_CHAR '\\'
#  define QL_EXE_EXT ".exe"
#else
#  include <unistd.h>
#  include <sys/wait.h>
#  include <libgen.h>
#  define QL_PATH_SEP "/"
#  define QL_PATH_SEP_CHAR '/'
#  define QL_EXE_EXT ""
#endif

#define QL_MAX_PATH_ 4096

/* The fixed width we allocate for path buffers. */
#ifndef QL_PATH_MAX
#  define QL_PATH_MAX 4096
#endif

/* ------------------------------------------------------------------ */
/* argv construction: [python, "-m", <module>, ...userArgs]          */
/* ------------------------------------------------------------------ */

static int build_argv(
    const char *python_path,
    const char *module,
    int argc_in,
    char *const argv_in[],
    char ***argv_out
) {
    /* Child argv layout: [python, "-m", module, <user args>, NULL].
     * User args are argv_in[1..argc_in-1] (argv_in[0], this launcher's own
     * path, is dropped). That is 3 + (argc_in - 1) = argc_in + 2 strings, plus
     * one NULL terminator = argc_in + 3 slots. (This was argc_in + 4, which
     * left a stray NULL slot BEFORE the terminator and made the returned
     * child_argc one too large -- the spawn loop then hit that NULL and
     * dereferenced it in MultiByteToWideChar/strlen, crashing the launcher on
     * every real launch. The resolver unit tests never exercised this path.) */
    int n = argc_in + 3;
    char **out = (char **)calloc((size_t)n, sizeof(char *));
    if (!out) return -1;
    out[0] = strdup(python_path);
    out[1] = strdup("-m");
    out[2] = strdup(module);
    if (!out[0] || !out[1] || !out[2]) {
        free(out[0]); free(out[1]); free(out[2]); free(out);
        return -1;
    }
    for (int i = 1; i < argc_in; ++i) {
        out[2 + i] = strdup(argv_in[i]);
        if (!out[2 + i]) {
            for (int j = 0; j < 2 + i; ++j) free(out[j]);
            free(out);
            return -1;
        }
    }
    out[n - 1] = NULL;
    *argv_out = out;
    return n - 1; /* argc for the child */
}

/* ------------------------------------------------------------------ */
/* Environment: forward PATH, USERPROFILE, TEMP, plus QUILL_APP_ROOT  */
/* ------------------------------------------------------------------ */

static int set_quill_env(
    const char *install_root,
    const char *data_dir
) {
    if (install_root && *install_root) {
#ifdef _WIN32
        SetEnvironmentVariableA("QUILL_APP_ROOT", install_root);
#else
        setenv("QUILL_APP_ROOT", install_root, 1);
#endif
    }
    if (data_dir && *data_dir) {
        char portable[QL_PATH_MAX];
        snprintf(portable, sizeof(portable), "%s" QL_PATH_SEP "data", data_dir);
#ifdef _WIN32
        DWORD attr = GetFileAttributesA(portable);
        if (attr != INVALID_FILE_ATTRIBUTES &&
            (attr & FILE_ATTRIBUTE_DIRECTORY)) {
            SetEnvironmentVariableA("QUILL_PORTABLE", "1");
        }
#else
        /* POSIX equivalent: stat() the directory. The runtime_resolve module
         * has already validated the layout, so a simple existence check
         * suffices here. */
        struct stat st;
        if (stat(portable, &st) == 0 && S_ISDIR(st.st_mode)) {
            setenv("QUILL_PORTABLE", "1", 1);
        }
#endif
    }
    /* Always set the product identity for child log/UA strings. */
#ifdef _WIN32
    SetEnvironmentVariableA("QUILL_PRODUCT_NAME", PRODUCT_NAME);
    SetEnvironmentVariableA("QUILL_PRODUCT_DISPLAY", PRODUCT_DISPLAY_NAME);
    SetEnvironmentVariableA("QUILL_PRODUCT_VERSION", PRODUCT_VERSION);
#else
    setenv("QUILL_PRODUCT_NAME", PRODUCT_NAME, 1);
    setenv("QUILL_PRODUCT_DISPLAY", PRODUCT_DISPLAY_NAME, 1);
    setenv("QUILL_PRODUCT_VERSION", PRODUCT_VERSION, 1);
#endif
    return 0;
}

/* ------------------------------------------------------------------ */
/* Error reporting: clean, screen-reader-friendly messages.           */
/* ------------------------------------------------------------------ */

static void show_error(
    const char *title,
    const char *message
) {
    fprintf(stderr, "%s: %s\n", title, message);
#ifdef _WIN32
    /* MessageBoxW with MB_OK | MB_ICONERROR | MB_SETFOREGROUND. Use the
     * ASCII path -- the messages are ASCII English on Windows by design
     * (the user-facing localized string is the installer's responsibility). */
    MessageBoxA(NULL, message, title, MB_OK | MB_ICONERROR | MB_SETFOREGROUND);
#else
    (void)title;
#endif
}

static int fail_no_runtime(const char *display_name) {
    char msg[1024];
    snprintf(msg, sizeof(msg),
        "%s could not find a Python runtime.\n\n"
        "Please reinstall %s. The application will now exit.",
        display_name, display_name);
    show_error(display_name, msg);
    return 2;
}

static int fail_spawn_failed(const char *display_name, const char *python_path) {
    char msg[1024];
    snprintf(msg, sizeof(msg),
        "%s could not start Python.\n\nPython path: %s\n\n"
        "Please reinstall %s.",
        display_name, python_path, display_name);
    show_error(display_name, msg);
    return 3;
}

#ifdef _WIN32
/*
 * Prefer the genuine, GUI-subsystem pythonw.exe over the console python.exe
 * when both sit beside a resolved private runtime.
 *
 * The launcher is itself a WIN32 (GUI) subsystem process with no console.
 * When it spawns a CONSOLE-subsystem child (python.exe), Windows allocates a
 * fresh console for that child -- a black window flashes for a screen-reader
 * user. CPython ships pythonw.exe precisely to avoid this: it is a one-line
 * trampoline (PC/WinMain.c: wWinMain -> Py_Main) built for the WINDOWS
 * subsystem, so it never gets a console. We spawn the UNMODIFIED pythonw.exe
 * -- we do NOT rename or rcedit-stamp it (that repackaged-interpreter shape is
 * what tripped the AV heuristic); the QUILL identity lives on THIS launcher.
 *
 * Only rewrites the path when the tail is exactly "\python.exe" and a sibling
 * "pythonw.exe" exists. The shared-runtime path (QuillVilleRuntime.exe) and the
 * legacy pythonw.exe fallback are already windowless and are left untouched.
 */
static void prefer_windowless_python(char *python_path, size_t size) {
    size_t len = strlen(python_path);
    const char *tail = "\\python.exe";
    size_t tlen = strlen(tail);
    if (len < tlen) return;
    if (_stricmp(python_path + (len - tlen), tail) != 0) return;
    char candidate[QL_PATH_MAX];
    snprintf(candidate, sizeof(candidate), "%.*s\\pythonw.exe",
             (int)(len - tlen), python_path);
    DWORD attr = GetFileAttributesA(candidate);
    if (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY)) {
        snprintf(python_path, size, "%s", candidate);
    }
}
#endif

/* ------------------------------------------------------------------ */
/* main / WinMain                                                      */
/* ------------------------------------------------------------------ */

#ifdef _WIN32
/*
 * When the CMake target sets WIN32_EXECUTABLE TRUE, the MSVC linker uses
 * /SUBSYSTEM:WINDOWS and looks for wWinMain (or WinMain) as the entry
 * point. The standard CRT startup that calls wmain (wmainCRTStartup) is
 * the CONSOLE-subsystem entry; if you use it under WINDOWS, the linker
 * still wants wWinMain at the symbol level.
 *
 * The simplest, most portable fix is a thin wWinMain shim that forwards
 * the Win32-flavored argv (which is already wide on Windows) to wmain.
 * We don't use the HINSTANCE / hPrevInstance / nCmdShow parameters.
 */
int wmain(int argc, wchar_t *wargv[]);

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance,
                    LPWSTR lpCmdLine, int nCmdShow)
{
    (void)hInstance;
    (void)hPrevInstance;
    (void)lpCmdLine;
    (void)nCmdShow;
    int argc = 0;
    LPWSTR *wargv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!wargv) {
        return 1;
    }
    int rc = wmain(argc, wargv);
    LocalFree(wargv);
    return rc;
}

int wmain(int argc, wchar_t *wargv[])
{
    /* Convert wide argv to UTF-8 narrow. */
    char **argv = (char **)calloc((size_t)argc + 1, sizeof(char *));
    if (!argv) return 1;
    for (int i = 0; i < argc; ++i) {
        int needed = WideCharToMultiByte(CP_UTF8, 0, wargv[i], -1, NULL, 0, NULL, NULL);
        if (needed <= 0) { free(argv); return 1; }
        argv[i] = (char *)malloc((size_t)needed);
        if (!argv[i]) { free(argv); return 1; }
        WideCharToMultiByte(CP_UTF8, 0, wargv[i], -1, argv[i], needed, NULL, NULL);
    }

    /* Get our own executable path. */
    char self_path[QL_PATH_MAX];
    if (ql_get_self_path(self_path, sizeof(self_path)) != 0) {
        show_error(PRODUCT_DISPLAY_NAME, "Could not determine install location.");
        for (int i = 0; i < argc; ++i) free(argv[i]);
        free(argv);
        return 4;
    }

    /* Resolve the runtime. */
    QlRuntime runtime;
    if (ql_resolve_runtime(self_path, &runtime) != 0 || !runtime.python[0]) {
        /* Self-heal: offer to download + install the shared runtime once, then
         * re-resolve. A feather-light "Companion" build (no bundled Python)
         * relies on this on its first launch; a full build only ever gets here
         * if its own runtime is missing. If the user declines or it fails, fall
         * back to the clean "please reinstall" error. */
        if (ql_bootstrap_runtime(PRODUCT_DISPLAY_NAME, PRODUCT_RUNTIME_URL) != 0 ||
            ql_resolve_runtime(self_path, &runtime) != 0 || !runtime.python[0]) {
            for (int i = 0; i < argc; ++i) free(argv[i]);
            free(argv);
            return fail_no_runtime(PRODUCT_DISPLAY_NAME);
        }
    }

    /* GUI apps: spawn the windowless pythonw.exe so no console flashes. */
    prefer_windowless_python(runtime.python, sizeof(runtime.python));

    /* Set environment for the child. */
    set_quill_env(runtime.install_root, runtime.data_dir);

    /* Build argv for the child. */
    char **child_argv = NULL;
    int child_argc = build_argv(runtime.python, PRODUCT_PYTHON_MODULE, argc, argv, &child_argv);
    if (child_argc < 0) {
        for (int i = 0; i < argc; ++i) free(argv[i]);
        free(argv);
        return fail_spawn_failed(PRODUCT_DISPLAY_NAME, runtime.python);
    }

    /* Convert child argv back to wide for CreateProcessW. */
    wchar_t **wchild = (wchar_t **)calloc((size_t)(child_argc + 1), sizeof(wchar_t *));
    if (!wchild) {
        for (int i = 0; i < argc; ++i) free(argv[i]);
        free(argv);
        return 1;
    }
    for (int i = 0; i < child_argc; ++i) {
        int needed = MultiByteToWideChar(CP_UTF8, 0, child_argv[i], -1, NULL, 0);
        wchild[i] = (wchar_t *)malloc(((size_t)needed) * sizeof(wchar_t));
        MultiByteToWideChar(CP_UTF8, 0, child_argv[i], -1, wchild[i], needed);
    }
    wchild[child_argc] = NULL;

    /* Build wide python path and command line. */
    wchar_t wpython[QL_PATH_MAX];
    MultiByteToWideChar(CP_UTF8, 0, runtime.python, -1, wpython, QL_PATH_MAX);

    /* Build a single command-line string for CreateProcessW. */
    size_t cmdlen = 0;
    for (int i = 0; i < child_argc; ++i) cmdlen += strlen(child_argv[i]) + 1;
    wchar_t *wcmdline = (wchar_t *)calloc(cmdlen + 1, sizeof(wchar_t));
    if (!wcmdline) {
        for (int i = 0; i < argc; ++i) free(argv[i]);
        free(argv);
        return 1;
    }
    wchar_t *wp = wcmdline;
    for (int i = 0; i < child_argc; ++i) {
        int needed = MultiByteToWideChar(CP_UTF8, 0, child_argv[i], -1, NULL, 0);
        MultiByteToWideChar(CP_UTF8, 0, child_argv[i], -1, wp, needed);
        wp += needed - 1;
        *wp++ = (i + 1 == child_argc) ? L'\0' : L' ';
    }

    /* Spawn. */
    STARTUPINFOW si;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi;
    ZeroMemory(&pi, sizeof(pi));

    /*
     * A Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE ties the whole child
     * process tree to this launcher: if the launcher dies (or the job handle is
     * closed), Windows terminates the interpreter and everything it spawned, so
     * a killed launcher never orphans a headless python. This mirrors CPython's
     * own venv redirector (PC/venvlauncher.c), which wraps its child the same
     * way. Best-effort: if the job can't be created we still launch.
     */
    HANDLE hJob = CreateJobObjectW(NULL, NULL);
    if (hJob) {
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION jeli;
        ZeroMemory(&jeli, sizeof(jeli));
        jeli.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        SetInformationJobObject(
            hJob, JobObjectExtendedLimitInformation, &jeli, sizeof(jeli));
    }

    /*
     * CREATE_NO_WINDOW is belt-and-suspenders: prefer_windowless_python() has
     * already steered us to pythonw.exe, but if only a console python.exe is
     * present this flag still suppresses the console window. CREATE_SUSPENDED
     * lets us assign the process to the job BEFORE its first instruction, so
     * any grandchildren are captured too.
     */
    BOOL ok = CreateProcessW(
        wpython,
        wcmdline,
        NULL, NULL,
        TRUE, /* inherit handles */
        CREATE_NO_WINDOW | CREATE_SUSPENDED,
        NULL,
        NULL,
        &si, &pi);

    int exit_code = 0;
    if (!ok) {
        exit_code = fail_spawn_failed(PRODUCT_DISPLAY_NAME, runtime.python);
        if (hJob) CloseHandle(hJob);
    } else {
        if (hJob) AssignProcessToJobObject(hJob, pi.hProcess);
        ResumeThread(pi.hThread);
        CloseHandle(pi.hThread);
        WaitForSingleObject(pi.hProcess, INFINITE);
        DWORD code = 0;
        GetExitCodeProcess(pi.hProcess, &code);
        CloseHandle(pi.hProcess);
        /* Close the job only after the child has exited so the
         * kill-on-close limit never reaps a still-running interpreter. */
        if (hJob) CloseHandle(hJob);
        exit_code = (int)code;
    }

    for (int i = 0; i < argc; ++i) free(argv[i]);
    free(argv);
    for (int i = 0; i < child_argc; ++i) free(child_argv[i]);
    free(child_argv);
    for (int i = 0; i < child_argc; ++i) free(wchild[i]);
    free(wchild);
    free(wcmdline);
    return exit_code;
}
#else
int main(int argc, char *argv[])
{
    char self_path[QL_PATH_MAX];
    if (ql_get_self_path(self_path, sizeof(self_path)) != 0) {
        fprintf(stderr, "%s: could not determine install location.\n", PRODUCT_DISPLAY_NAME);
        return 4;
    }

    QlRuntime runtime;
    if (ql_resolve_runtime(self_path, &runtime) != 0 || !runtime.python[0]) {
        return fail_no_runtime(PRODUCT_DISPLAY_NAME);
    }

    set_quill_env(runtime.install_root, runtime.data_dir);

    char **child_argv = NULL;
    int child_argc = build_argv(runtime.python, PRODUCT_PYTHON_MODULE, argc, argv, &child_argv);
    if (child_argc < 0) {
        return fail_spawn_failed(PRODUCT_DISPLAY_NAME, runtime.python);
    }

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return fail_spawn_failed(PRODUCT_DISPLAY_NAME, runtime.python);
    }
    if (pid == 0) {
        execv(runtime.python, child_argv);
        perror("execv");
        _exit(127);
    }
    int status = 0;
    waitpid(pid, &status, 0);
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return 1;
}
#endif
