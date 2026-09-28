/*
 * QuillVille launcher -- the "it did not start" report.
 *
 * Until 2026-09-28 the launcher spawned pythonw.exe, waited, and returned the
 * child's exit code -- and nothing else. pythonw.exe has no console, so a
 * traceback at import time went nowhere; a DLL Windows refused to load
 * killed the process before Python ran, with no text at all. The user saw
 * nothing: no window, no dialog, no file. The first report of it was "no
 * matter what she does it just doesn't return anything".
 *
 * Now the launcher (1) points the child's stdout and stderr at a launch log,
 * (2) recognises when it is running from inside a zip that was never
 * extracted, and (3) after a non-zero exit shows one dialog: what happened
 * in words, where the log is, and where to send it. A MessageBox is the one
 * surface every screen reader reads without help.
 *
 * Python mirror + tests: tests/unit/native/test_launch_failure.py. The
 * constants and the phrases here are pinned to that file; change both.
 */
#include "launch_report.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#  include <io.h>
#else
#  include <sys/stat.h>
#endif

/* NTSTATUS values a process exits with when Windows, not Python, killed it.
 * None of these leave a line in the log, which is why they need words. */
#define QL_STATUS_ACCESS_VIOLATION      0xC0000005UL
#define QL_STATUS_ACCESS_DENIED         0xC0000022UL
#define QL_STATUS_INVALID_IMAGE_FORMAT  0xC000007BUL
#define QL_STATUS_DLL_NOT_FOUND         0xC0000135UL
#define QL_STATUS_DLL_INIT_FAILED       0xC0000142UL
#define QL_STATUS_HEAP_CORRUPTION       0xC0000374UL
#define QL_STATUS_STACK_BUFFER_OVERRUN  0xC0000409UL

#define QL_SUPPORT_EMAIL "support@community-access.org"

/* ------------------------------------------------------------------ */
/* Small string helpers                                                */
/* ------------------------------------------------------------------ */

static int starts_with_ci(const char *s, const char *prefix) {
    while (*prefix) {
        if (!*s) return 0;
        if (tolower((unsigned char)*s) != tolower((unsigned char)*prefix)) return 0;
        ++s;
        ++prefix;
    }
    return 1;
}

static int ends_with_ci(const char *s, size_t len, const char *suffix) {
    size_t slen = strlen(suffix);
    if (len < slen) return 0;
    for (size_t i = 0; i < slen; ++i) {
        if (tolower((unsigned char)s[len - slen + i]) != tolower((unsigned char)suffix[i]))
            return 0;
    }
    return 1;
}

static int is_dir(const char *path) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY);
#else
    struct stat st;
    return stat(path, &st) == 0 && S_ISDIR(st.st_mode);
#endif
}

/* ------------------------------------------------------------------ */
/* Archive preview detection                                           */
/* ------------------------------------------------------------------ */

/* One path component (no separators, NUL-terminated copy). The three
 * archive tools people open a download with each extract *only the file
 * that was double-clicked* into a scratch folder with a recognisable name:
 * Explorer's zip folder view uses Temp<n>_<zip name>.zip, 7-Zip uses
 * 7zO<hex>, WinRAR uses Rar$EXa<...>. */
static int component_is_archive_scratch(const char *part, size_t len) {
    char buf[512];
    if (len == 0 || len >= sizeof(buf)) return 0;
    memcpy(buf, part, len);
    buf[len] = 0;

    if (starts_with_ci(buf, "Temp")) {
        const char *p = buf + 4;
        if (!isdigit((unsigned char)*p)) return 0;
        while (isdigit((unsigned char)*p)) ++p;
        if (*p != '_') return 0;
        return ends_with_ci(buf, len, ".zip");
    }
    if (starts_with_ci(buf, "7zO")) {
        const char *p = buf + 3;
        if (!*p) return 0;
        while (*p) {
            if (!isalnum((unsigned char)*p)) return 0;
            ++p;
        }
        return 1;
    }
    if (starts_with_ci(buf, "Rar$")) return 1;
    return 0;
}

int ql_looks_like_archive_preview(const char *self_path) {
    if (!self_path) return 0;
    const char *start = self_path;
    const char *p = self_path;
    for (;; ++p) {
        if (*p == '\\' || *p == '/' || *p == 0) {
            /* A component is a folder only if a separator follows it; the
             * final component is the exe's own name and never counts. */
            if (*p != 0 && component_is_archive_scratch(start, (size_t)(p - start))) {
                return 1;
            }
            if (*p == 0) break;
            start = p + 1;
        }
    }
    return 0;
}

void ql_archive_preview_message(const char *display_name, const char *exe_name,
                                char *out, size_t out_size) {
    snprintf(out, out_size,
        "%s was opened from inside the zip file, so Windows copied only that "
        "one file out and left the rest of the program behind.\n\n"
        "Extract the whole zip first: select it in File Explorer, press the "
        "Applications key, choose Extract All, and choose a folder. Then open "
        "%s in the extracted folder.",
        display_name, exe_name);
}

/* ------------------------------------------------------------------ */
/* Where the log goes                                                  */
/* ------------------------------------------------------------------ */

int ql_launch_log_path(const char *data_dir, const char *product_name,
                       char *out, size_t out_size) {
    out[0] = 0;
    if (data_dir && *data_dir) {
        char portable[2048];
        snprintf(portable, sizeof(portable), "%s\\data", data_dir);
        if (is_dir(portable)) {
            snprintf(out, out_size, "%s\\data\\logs\\launch.log", data_dir);
            return 0;
        }
    }
    const char *appdata = getenv("APPDATA");
    if (appdata && *appdata) {
        snprintf(out, out_size, "%s\\Quill\\logs\\%s-launch.log", appdata, product_name);
        return 0;
    }
    const char *temp = getenv("TEMP");
    if (temp && *temp) {
        snprintf(out, out_size, "%s\\%s-launch.log", temp, product_name);
        return 0;
    }
    return -1;
}

/* ------------------------------------------------------------------ */
/* Reading the tail                                                    */
/* ------------------------------------------------------------------ */

static void copy_trimmed(const char *begin, const char *end, char *out, size_t out_size) {
    while (begin < end && isspace((unsigned char)*begin)) ++begin;
    while (end > begin && isspace((unsigned char)end[-1])) --end;
    size_t n = (size_t)(end - begin);
    if (n > QL_LAST_LINE_MAX) n = QL_LAST_LINE_MAX;
    if (n >= out_size) n = out_size - 1;
    memcpy(out, begin, n);
    out[n] = 0;
}

int ql_last_message_line(const char *log_path, const char *header,
                         char *out, size_t out_size) {
    out[0] = 0;
    if (!log_path || !*log_path || out_size == 0) return -1;
    FILE *f = fopen(log_path, "rb");
    if (!f) return -1;

    /* Only the tail matters. 8 KiB is many tracebacks. */
    static char tail[8192];
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return -1; }
    long size = ftell(f);
    if (size < 0) { fclose(f); return -1; }
    long from = size > (long)sizeof(tail) ? size - (long)sizeof(tail) : 0;
    if (fseek(f, from, SEEK_SET) != 0) { fclose(f); return -1; }
    size_t got = fread(tail, 1, sizeof(tail), f);
    fclose(f);

    char trimmed_header[QL_LAST_LINE_MAX + 1] = {0};
    if (header) copy_trimmed(header, header + strlen(header), trimmed_header, sizeof(trimmed_header));

    char candidate[QL_LAST_LINE_MAX + 1];
    const char *line = tail;
    const char *end = tail + got;
    while (line < end) {
        const char *nl = memchr(line, '\n', (size_t)(end - line));
        const char *line_end = nl ? nl : end;
        copy_trimmed(line, line_end, candidate, sizeof(candidate));
        if (candidate[0] && strcmp(candidate, trimmed_header) != 0) {
            snprintf(out, out_size, "%s", candidate);
        }
        if (!nl) break;
        line = nl + 1;
    }
    return 0;
}

/* ------------------------------------------------------------------ */
/* The sentence                                                        */
/* ------------------------------------------------------------------ */

void ql_describe_exit(unsigned long code, const char *last_line,
                      const char *display_name, char *out, size_t out_size) {
    switch (code) {
    case QL_STATUS_DLL_NOT_FOUND:
        snprintf(out, out_size,
            "A file it needs is missing (Windows reported that a DLL could not be "
            "found). If this is a portable copy, extract the whole zip again, keeping "
            "every file together, and check whether antivirus quarantined a file from "
            "its folder.");
        return;
    case QL_STATUS_DLL_INIT_FAILED:
        snprintf(out, out_size,
            "A file it needs could not be started (a DLL failed to initialise). "
            "Sign out of Windows and back in, or restart the computer, then try again.");
        return;
    case QL_STATUS_INVALID_IMAGE_FORMAT:
        snprintf(out, out_size,
            "A file in its folder is damaged, or is the wrong kind for this computer "
            "(%s needs 64-bit Windows). Download and extract it again.",
            display_name);
        return;
    case QL_STATUS_ACCESS_DENIED:
        snprintf(out, out_size,
            "Windows refused to run its files. Antivirus, application control or a "
            "folder permission is blocking it. Try extracting it to a folder of your "
            "own, such as Documents, and check the antivirus quarantine.");
        return;
    case QL_STATUS_ACCESS_VIOLATION:
    case QL_STATUS_HEAP_CORRUPTION:
    case QL_STATUS_STACK_BUFFER_OVERRUN:
        snprintf(out, out_size,
            "It crashed inside a component (a memory fault), not in its own code.");
        return;
    default:
        break;
    }
    if (last_line && *last_line) {
        const char *hint = "";
        if (strstr(last_line, "No module named")) {
            hint = " Part of the program is missing: this copy is incomplete, or its files "
                   "are mixed with another version's. Extract the whole zip again into an "
                   "empty folder.";
        } else if (strstr(last_line, "DLL load failed")) {
            hint = " A component could not be loaded. Check the antivirus quarantine, and "
                   "extract the whole zip again, keeping every file together.";
        } else if (strstr(last_line, "PermissionError") || strstr(last_line, "Permission denied")) {
            hint = " It is not allowed to write where it is. Move the folder somewhere "
                   "you own, such as Documents, or run it from a different drive.";
        }
        snprintf(out, out_size, "Python reported: %s%s", last_line, hint);
        return;
    }
    snprintf(out, out_size, "It exited with code %lu and left no message.", code);
}

void ql_headline(const char *display_name, unsigned long long ran_for_ms,
                 char *out, size_t out_size) {
    if (ran_for_ms >= QL_STARTED_AFTER_MS) {
        snprintf(out, out_size, "%s stopped unexpectedly.", display_name);
    } else {
        snprintf(out, out_size, "%s did not start.", display_name);
    }
}

/* ------------------------------------------------------------------ */
/* Windows: the log file and the dialog                                */
/* ------------------------------------------------------------------ */

#ifdef _WIN32

/* mkdir -p for the folder that will hold `file_path`. Best effort. */
static void ensure_parent_folders(const char *file_path) {
    char path[2048];
    snprintf(path, sizeof(path), "%s", file_path);
    char *last_sep = strrchr(path, '\\');
    if (!last_sep) return;
    *last_sep = 0;
    /* Walk forward creating each prefix. Skip the drive ("C:") and any
     * UNC head; CreateDirectory on an existing folder just fails
     * harmlessly with ERROR_ALREADY_EXISTS. */
    for (char *p = path + 1; *p; ++p) {
        if (*p == '\\') {
            *p = 0;
            if (strlen(path) > 2) CreateDirectoryA(path, NULL);
            *p = '\\';
        }
    }
    CreateDirectoryA(path, NULL);
}

HANDLE ql_open_launch_log(const char *log_path, const char *header) {
    if (!log_path || !*log_path) return INVALID_HANDLE_VALUE;
    ensure_parent_folders(log_path);

    SECURITY_ATTRIBUTES sa;
    ZeroMemory(&sa, sizeof(sa));
    sa.nLength = sizeof(sa);
    sa.bInheritHandle = TRUE;

    /* FILE_SHARE_READ only: a second launcher (the single-instance hand-off,
     * which exits 0 at once) must not truncate a running instance's log
     * from under it. It fails to open, launches unlogged, and that is fine. */
    HANDLE h = CreateFileA(log_path, GENERIC_WRITE, FILE_SHARE_READ, &sa,
                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return INVALID_HANDLE_VALUE;
    if (header && *header) {
        DWORD written = 0;
        WriteFile(h, header, (DWORD)strlen(header), &written, NULL);
        WriteFile(h, "\n", 1, &written, NULL);
    }
    return h;
}

void ql_report_failed_exit(const char *display_name, unsigned long code,
                           unsigned long long ran_for_ms, const char *log_path,
                           const char *header) {
    char last_line[QL_LAST_LINE_MAX + 1] = {0};
    if (log_path && *log_path) {
        ql_last_message_line(log_path, header, last_line, sizeof(last_line));
    }
    char head[256];
    ql_headline(display_name, ran_for_ms, head, sizeof(head));
    char reason[1024];
    ql_describe_exit(code, last_line, display_name, reason, sizeof(reason));

    char message[4096];
    if (log_path && *log_path) {
        snprintf(message, sizeof(message),
            "%s\n\n%s\n\nWhat happened was written to:\n%s\n\n"
            "If it keeps happening, send that file to " QL_SUPPORT_EMAIL ".",
            head, reason, log_path);
    } else {
        snprintf(message, sizeof(message),
            "%s\n\n%s\n\nNo launch log could be written. "
            "If it keeps happening, write to " QL_SUPPORT_EMAIL ".",
            head, reason);
    }
    fprintf(stderr, "%s: %s\n", display_name, message);
    MessageBoxA(NULL, message, display_name, MB_OK | MB_ICONERROR | MB_SETFOREGROUND);
}

#endif /* _WIN32 */
