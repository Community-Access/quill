/*
 * QuillVille launcher -- building a Windows command line from an argv.
 *
 * CreateProcessW takes ONE string, and the child splits it back into argv
 * itself (the MSVC CRT, and CommandLineToArgvW, which follow the same rules).
 * Joining the arguments with spaces is only correct while no argument holds a
 * space, a tab, a quote or an empty string. Until 2026-10-04 the launcher did
 * exactly that, so a portable copy unpacked to "C:\portable\Quill Radio" told
 * Python its own path was two words and Python tried to run the second one as
 * a script ("can't open file '...\Radio\pythonw.exe'"); a file opened from
 * Explorer out of "C:\My Music" arrived as two arguments as well.
 *
 * Python mirror + tests: tests/unit/native/test_launcher_cmdline.py (the
 * quoting rules in Python, and a real compile that round-trips through
 * shell32's CommandLineToArgvW).
 */
#ifndef QL_CMDLINE_H
#define QL_CMDLINE_H

#include <stddef.h>
#include <wchar.h>

/* The most characters ql_append_quoted_arg can write for an argument of
 * `len` characters, plus one for a separating space: every character a quote
 * needing a backslash (2 * len), the two surrounding quotes, the space. */
#define QL_QUOTED_ARG_MAX(len) (2 * (len) + 3)

/* Append `arg` to `dst`, quoted so that CommandLineToArgvW and the MSVC CRT
 * read it back as exactly `arg`. An argument that is non-empty and holds no
 * space, tab, newline, vertical tab or quote is copied as it is. Otherwise it
 * is wrapped in quotes; a quote inside becomes \", and the backslashes
 * immediately before a quote -- or before the closing quote -- are doubled.
 * Backslashes anywhere else are literal and stay single. Returns the number
 * of characters written (never more than QL_QUOTED_ARG_MAX(len) - 1); writes
 * no terminator. */
size_t ql_append_quoted_arg(wchar_t *dst, const wchar_t *arg);

/* A heap-allocated command line for `argc` arguments, each quoted by
 * ql_append_quoted_arg and separated by one space, NUL-terminated. The caller
 * frees it with free(). NULL when memory runs out. */
wchar_t *ql_build_command_line(const wchar_t *const *argv, int argc);

#endif /* QL_CMDLINE_H */
