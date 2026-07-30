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

typedef struct QlRuntime {
    char python[QL_PATH_MAX];      /* absolute path to python.exe (or POSIX bin/python3) */
    char install_root[QL_PATH_MAX]; /* directory to set as QUILL_APP_ROOT */
    char data_dir[QL_PATH_MAX];    /* directory the child should treat as portable root */
} QlRuntime;

/* Return the absolute path of the running executable in `out` (size `out_size`).
 * Returns 0 on success, -1 on failure. */
int ql_get_self_path(char *out, size_t out_size);

/* Resolve a runtime given the launcher's own path. On success, fills in
 * out->python with an absolute path to a runnable Python interpreter and
 * out->install_root / out->data_dir. On failure, out->python[0] is set to 0
 * and the function returns -1. */
int ql_resolve_runtime(const char *self_path, QlRuntime *out);

#endif /* QL_RUNTIME_RESOLVE_H */
