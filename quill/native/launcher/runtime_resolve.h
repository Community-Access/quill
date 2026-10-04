/*
 * QuillVille runtime resolver -- public surface.
 *
 * Included by launcher.c. The QlRuntime struct is filled in by
 * ql_resolve_runtime(); the caller passes the result to set_quill_env()
 * and to the spawn routine.
 */
#ifndef QL_RUNTIME_RESOLVE_H
#define QL_RUNTIME_RESOLVE_H

#include <stddef.h>

#define QL_PATH_MAX 4096

#define QL_SLOT_MAX 32

typedef struct QlRuntime {
    char python[QL_PATH_MAX];      /* absolute path to python.exe (or POSIX bin/python3) */
    char install_root[QL_PATH_MAX]; /* directory to set as QUILL_APP_ROOT */
    char data_dir[QL_PATH_MAX];    /* directory the child should treat as portable root */
    /* The release-channel runtime slot named by [runtime] slot= in the
     * quill-app-version.ini beside the launcher ("3.13-beta"), or "" when the
     * ini has none -- then the Stable folder "3.13" is used, as before.
     * Filled in even when resolution fails, so the caller can choose where a
     * missing runtime is repaired from. */
    char slot[QL_SLOT_MAX];
} QlRuntime;

/* Return the absolute path of the running executable in `out` (size `out_size`).
 * Returns 0 on success, -1 on failure. */
int ql_get_self_path(char *out, size_t out_size);

/* Resolve a runtime given the launcher's own path. On success, fills in
 * out->python with an absolute path to a runnable Python interpreter and
 * out->install_root / out->data_dir. On failure, out->python[0] is set to 0
 * and the function returns -1. */
int ql_resolve_runtime(const char *self_path, QlRuntime *out);

/* Read and validate [runtime] slot= from <self_dir>/quill-app-version.ini.
 * Returns 0 and fills `out` with e.g. "3.13-beta"; -1 when absent or invalid
 * (out is then ""). Valid: <digits>.<digits>, optionally -beta or -dev. */
int ql_runtime_slot(const char *self_dir, char *out, size_t out_size);

/* Where a missing runtime in `slot` is downloaded from. Copies `base_url` (the
 * compiled-in runtime-latest URL) for the Stable slot, swaps its
 * /runtime-latest/ segment for /runtime-beta/ for the Beta slot, and returns
 * -1 for a Dev slot: Dev runtimes do not repair themselves ("Reinstall the Dev
 * build"). Returns 0 on success. */
int ql_runtime_url_for_slot(const char *base_url, const char *slot, char *out, size_t out_size);

#endif /* QL_RUNTIME_RESOLVE_H */
