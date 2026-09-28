/*
 * QuillVille launcher -- the "it did not start" report.
 *
 * Included by launcher.c. The launcher redirects the interpreter's stdout and
 * stderr to a launch log, and when the child exits non-zero it turns the exit
 * code and the log's last line into one dialog a person can act on.
 *
 * Python mirror + tests: tests/unit/native/test_launch_failure.py. Keep the
 * constants and the phrases aligned; that test pins them to this source.
 */
#ifndef QL_LAUNCH_REPORT_H
#define QL_LAUNCH_REPORT_H

#include <stddef.h>

/* The longest tail line the dialog repeats. */
#define QL_LAST_LINE_MAX 300

/* A child that ran at least this long (ms) before exiting non-zero "stopped
 * unexpectedly"; a shorter run "did not start". */
#define QL_STARTED_AFTER_MS 60000

/* True when the launcher is running from an archive tool's scratch folder --
 * the user opened the exe from *inside* the zip, so only that one file was
 * extracted. Pure string logic; portable. */
int ql_looks_like_archive_preview(const char *self_path);

/* The words for that case: extract the whole zip, then open `exe_name`. */
void ql_archive_preview_message(const char *display_name, const char *exe_name,
                                char *out, size_t out_size);

/* Name the launch log: <data_dir>\data\logs\launch.log for a portable copy,
 * %APPDATA%\Quill\logs\<product>-launch.log for an installed one, %TEMP% as
 * the last resort. Returns 0 and fills `out`, or -1 with out[0] == 0. Does not
 * create anything. */
int ql_launch_log_path(const char *data_dir, const char *product_name,
                       char *out, size_t out_size);

/* The last non-blank line of the log that is not `header`, bounded to
 * QL_LAST_LINE_MAX bytes. Returns 0 and fills `out` (empty when there is
 * nothing), -1 when the file could not be read. */
int ql_last_message_line(const char *log_path, const char *header,
                         char *out, size_t out_size);

/* One paragraph saying why `display_name` exited with `code`, given the last
 * line of its log (may be empty). Always fills `out`. */
void ql_describe_exit(unsigned long code, const char *last_line,
                      const char *display_name, char *out, size_t out_size);

/* "<display_name> did not start." or "... stopped unexpectedly." */
void ql_headline(const char *display_name, unsigned long long ran_for_ms,
                 char *out, size_t out_size);

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  include <windows.h>

/* Create (truncate) the launch log, write `header` + newline to it, and
 * return an INHERITABLE handle for the child's stdout/stderr. Creates the
 * parent folders. Returns INVALID_HANDLE_VALUE when it cannot (the launch
 * then proceeds unlogged, as before). */
HANDLE ql_open_launch_log(const char *log_path, const char *header);

/* Show the report for a non-zero exit: headline, reason, where the log is,
 * and where to send it. `log_path` may be empty when no log was written. */
void ql_report_failed_exit(const char *display_name, unsigned long code,
                           unsigned long long ran_for_ms, const char *log_path,
                           const char *header);
#endif

#endif /* QL_LAUNCH_REPORT_H */
