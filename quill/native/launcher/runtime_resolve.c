/*
 * QuillVille runtime resolver.
 *
 * Given the path of the launcher executable (self_path), populates a QlRuntime
 * struct with the absolute path of a runnable Python interpreter and the
 * install-root directory (used to set QUILL_APP_ROOT in the child process).
 *
 * Resolution order:
 *   1. Shared QuillVille runtime at $LOCALAPPDATA/QuillVille/Runtime/<major>/
 *      (Windows) or $XDG_DATA_HOME/quillville/Runtime/<major>/ (POSIX).
 *      Validated by the presence of quillville-runtime.json with a parseable
 *      "python" key matching the current CPython major.minor.
 *   2. Private embedded runtime beside the launcher: <dir>/python.exe
 *      (Windows onedir) or <dir>/_internal/python.exe (PyInstaller).
 *   3. pythonw.exe beside the launcher (legacy fallback during the transition
 *      from the old stamped-launcher design). This branch is removed in a
 *      later release.
 *
 * The function never crashes. If nothing resolves, runtime.python[0] is set to
 * 0 and the caller (launcher.c) shows a clean error dialog.
 *
 * -- Reuse note: the marker file format -------------------------------------
 * The quillville-runtime.json contract is owned by the Python side:
 *     quill/core/runtime_marker.py    (write_marker, read_marker,
 *                                      installed_version, needs_install)
 * The Python side is the source of truth -- it writes the marker, the C
 * side reads it. If you change the JSON shape (e.g. add a "build_date"
 * field), update both: the writer in runtime_marker.py and the
 * read_python_version_from_marker() parser below. A unit test in
 * tests/unit/native/test_runtime_resolver.py exercises the Python mirror
 * of this algorithm; keep them aligned.
 *
 * The hand-rolled JSON parser below is intentionally minimal -- the marker
 * is always a small {"python": "X.Y.Z", "build": "YYYY-MM-DD"} object
 * produced by runtime_marker.write_marker(). A real JSON parser would
 * add a dependency for no gain; the parser only looks for the "python"
 * string value.
 */

#include "runtime_resolve.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  include <windows.h>
#  include <shlwapi.h>
#  pragma comment(lib, "shlwapi.lib")
#  define PATH_SEP_CHAR '\\'
#  define PATH_SEP_STR "\\"
#  define EXE_EXT ".exe"
#else
#  include <sys/stat.h>
#  include <libgen.h>
#  include <limits.h>
#  include <unistd.h>
#  define PATH_SEP_CHAR '/'
#  define PATH_SEP_STR "/"
#  define EXE_EXT ""
#endif

/* ------------------------------------------------------------------ */
/* Path helpers                                                        */
/* ------------------------------------------------------------------ */

static void path_join(char *out, size_t out_size, const char *a, const char *b) {
    size_t la = strlen(a);
    if (la == 0) {
        snprintf(out, out_size, "%s", b);
        return;
    }
    char sep = a[la - 1];
    if (sep == '/' || sep == '\\') {
        snprintf(out, out_size, "%s%s", a, b);
    } else {
        snprintf(out, out_size, "%s%c%s", a, PATH_SEP_CHAR, b);
    }
}

static int path_exists(const char *p) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesA(p);
    return attr != INVALID_FILE_ATTRIBUTES;
#else
    struct stat st;
    return stat(p, &st) == 0;
#endif
}

static int path_is_file(const char *p) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesA(p);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
#else
    struct stat st;
    return stat(p, &st) == 0 && S_ISREG(st.st_mode);
#endif
}

/* ------------------------------------------------------------------ */
/* Self path: returns the absolute path of the running executable.   */
/* ------------------------------------------------------------------ */

int ql_get_self_path(char *out, size_t out_size) {
#ifdef _WIN32
    DWORD n = GetModuleFileNameA(NULL, out, (DWORD)out_size);
    if (n == 0 || n >= out_size) return -1;
    return 0;
#else
    ssize_t n = readlink("/proc/self/exe", out, out_size - 1);
    if (n < 0) return -1;
    out[n] = '\0';
    return 0;
#endif
}

static int dirname_of(const char *path, char *out, size_t out_size) {
#ifdef _WIN32
    /* Use a temporary buffer so we can mutate in place. */
    if (strlen(path) >= out_size) return -1;
    strncpy(out, path, out_size - 1);
    out[out_size - 1] = '\0';
    if (!PathRemoveFileSpecA(out)) return -1;
    return 0;
#else
    if (strlen(path) >= out_size) return -1;
    strncpy(out, path, out_size - 1);
    out[out_size - 1] = '\0';
    char *d = dirname(out);
    if (!d) return -1;
    /* dirname may return a pointer into out, or a static string. */
    if (d != out) {
        size_t dl = strlen(d);
        memmove(out, d, dl + 1);
    }
    return 0;
#endif
}

/* ------------------------------------------------------------------ */
/* Shared runtime probe                                                */
/* ------------------------------------------------------------------ */

/* Tiny JSON reader: finds the value of "python" in a small JSON object.
 * Avoids a JSON dependency. The marker is always produced by
 * quill.core.runtime_marker.write_marker; format is stable. */
static int read_python_version_from_marker(
    const char *path,
    char *out, size_t out_size
) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    char buf[512];
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    if (n == 0) return -1;
    buf[n] = '\0';
    const char *key = "\"python\"";
    const char *p = strstr(buf, key);
    if (!p) return -1;
    p += strlen(key);
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
    if (*p != ':') return -1;
    p++;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
    if (*p != '"') return -1;
    p++;
    size_t i = 0;
    while (*p && *p != '"' && i < out_size - 1) {
        out[i++] = *p++;
    }
    out[i] = '\0';
    return (i > 0) ? 0 : -1;
}

/* Best-effort: read this launcher's compiled-in major.minor.
 * Hard-coded for now to 3.13 since the platform pin is in
 * scripts/build_windows_distribution.py:102. A future change can expose this
 * via the version marker instead. */
static void launcher_python_baseline(char *out, size_t out_size) {
    snprintf(out, out_size, "3.13");
}

static int python_version_compatible(const char *marker_python) {
    char baseline[16];
    launcher_python_baseline(baseline, sizeof(baseline));
    /* Compare "X.Y" prefix. */
    size_t bl = strlen(baseline);
    if (strncmp(marker_python, baseline, bl) != 0) return 0;
    char next = marker_python[bl];
    return next == '\0' || next == '.';
}

static int try_shared_runtime(char *out_python, size_t out_size, char *out_root, size_t out_root_size) {
    char base[QL_PATH_MAX];

#ifdef _WIN32
    const char *local = getenv("LOCALAPPDATA");
    if (!local || !*local) return -1;
    snprintf(base, sizeof(base),
        "%s\\QuillVille\\Runtime", local);
#else
    const char *xdg = getenv("XDG_DATA_HOME");
    if (!xdg || !*xdg) {
        const char *home = getenv("HOME");
        if (!home || !*home) return -1;
        snprintf(base, sizeof(base), "%s/.local/share/quillville/Runtime", home);
    } else {
        snprintf(base, sizeof(base), "%s/quillville/Runtime", xdg);
    }
#endif

    if (!path_exists(base)) return -1;

    /* Walk subdirectories: runtime/3.13/, runtime/3.14/, etc.
     * The current build only supports 3.13, so the directory is hard-coded.
     * A future runtime major can be added by reading the marker JSON's
     * "python" key. */
    char runtime_dir[QL_PATH_MAX];
    path_join(runtime_dir, sizeof(runtime_dir), base, "3.13");
    if (!path_exists(runtime_dir)) return -1;

    char marker[QL_PATH_MAX];
    path_join(marker, sizeof(marker), runtime_dir, "quillville-runtime.json");
    if (!path_is_file(marker)) return -1;

    char marker_python[32];
    if (read_python_version_from_marker(marker, marker_python, sizeof(marker_python)) != 0) {
        return -1;
    }
    if (!python_version_compatible(marker_python)) {
        return -1;
    }

    /* The shared runtime is a PyInstaller onedir. The boot loader exe
     * (QuillVilleRuntime.exe) is the onedir root's only executable, and
     * IS the entry point the per-app C launchers spawn. The onedir does
     * not have a real python.exe at this location -- PyInstaller's
     * COLLECT places the bootloader at the onedir root and unpacks the
     * python interpreter at runtime from the bundled archive.
     *
     * Phase 4 (see docs/design/native-launcher-2026-07-24.md §7) drops
     * the PyInstaller bootloader in favour of a real embeddable CPython
     * (python.exe / python313.dll / Lib/) extracted at the same path.
     * When that lands, change the probe below back to "python.exe" /
     * "bin/python3". The Python mirror in
     * tests/unit/native/test_runtime_resolver.py must change in lockstep. */
#ifdef _WIN32
    char python[QL_PATH_MAX];
    path_join(python, sizeof(python), runtime_dir, "QuillVilleRuntime.exe");
    if (!path_is_file(python)) return -1;
    snprintf(out_python, out_size, "%s", python);
    snprintf(out_root, out_root_size, "%s", runtime_dir);
    return 0;
#else
    char python[QL_PATH_MAX];
    path_join(python, sizeof(python), runtime_dir, "QuillVilleRuntime");
    if (!path_is_file(python)) return -1;
    snprintf(out_python, out_size, "%s", python);
    snprintf(out_root, out_root_size, "%s", runtime_dir);
    return 0;
#endif
}

/* ------------------------------------------------------------------ */
/* Private embedded runtime probe                                      */
/* ------------------------------------------------------------------ */

static int try_private_runtime(
    const char *self_dir,
    char *out_python, size_t out_size,
    char *out_root, size_t out_root_size
) {
    char candidate[QL_PATH_MAX];

    /* (a) PyInstaller onedir: <dir>/_internal/python.exe */
    path_join(candidate, sizeof(candidate), self_dir, "_internal" PATH_SEP_STR "python" EXE_EXT);
    if (path_is_file(candidate)) {
        snprintf(out_python, out_size, "%s", candidate);
        snprintf(out_root, out_root_size, "%s", self_dir);
        return 0;
    }

    /* (b) Flat-embedded layout: <dir>/python.exe (the main QUILL build). */
    path_join(candidate, sizeof(candidate), self_dir, "python" EXE_EXT);
    if (path_is_file(candidate)) {
        snprintf(out_python, out_size, "%s", candidate);
        snprintf(out_root, out_root_size, "%s", self_dir);
        return 0;
    }

    /* (c) Legacy pythonw.exe fallback (transition only). */
    path_join(candidate, sizeof(candidate), self_dir, "pythonw" EXE_EXT);
    if (path_is_file(candidate)) {
        snprintf(out_python, out_size, "%s", candidate);
        snprintf(out_root, out_root_size, "%s", self_dir);
        return 0;
    }

    return -1;
}

/* ------------------------------------------------------------------ */
/* Public entry point                                                 */
/* ------------------------------------------------------------------ */

int ql_resolve_runtime(const char *self_path, QlRuntime *out) {
    if (!out) return -1;
    memset(out, 0, sizeof(*out));
    out->python[0] = 0;
    out->install_root[0] = 0;
    out->data_dir[0] = 0;

    /* 1. Shared QuillVille runtime. */
    if (try_shared_runtime(out->python, sizeof(out->python),
                            out->install_root, sizeof(out->install_root)) == 0) {
        return 0;
    }

    /* 2 & 3. Beside the launcher. */
    char self_dir[QL_PATH_MAX];
    if (dirname_of(self_path, self_dir, sizeof(self_dir)) != 0) {
        return -1;
    }
    if (try_private_runtime(self_dir,
                            out->python, sizeof(out->python),
                            out->install_root, sizeof(out->install_root)) == 0) {
        /* data_dir == self_dir for portable detection (the storage_mode
         * helper looks for self_dir/data/). */
        snprintf(out->data_dir, sizeof(out->data_dir), "%s", self_dir);
        return 0;
    }

    return -1;
}
