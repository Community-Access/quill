/*
 * QuillVille launcher -- quoting an argv into one Windows command line.
 * See cmdline.h for why this exists.
 *
 * The rules are the ones CommandLineToArgvW and the MSVC CRT parse by
 * (Microsoft's "Parsing C++ command-line arguments"):
 *
 *   - Whitespace (space or tab) separates arguments unless inside quotes.
 *   - 2n backslashes followed by a quote produce n backslashes, and the quote
 *     opens or closes a quoted region.
 *   - 2n+1 backslashes followed by a quote produce n backslashes and a
 *     literal quote.
 *   - Backslashes not followed by a quote are literal.
 *
 * So the encoder below doubles a run of backslashes only where a quote comes
 * next -- an escaped quote inside the argument, or the closing quote after a
 * trailing backslash ("C:\dir\" would otherwise swallow its own closing quote
 * and every argument after it). Pure C, no Windows headers: it compiles on
 * every platform and the test suite builds it on its own.
 */

#include "cmdline.h"

#include <stdlib.h>
#include <string.h>

static int ql_arg_needs_quotes(const wchar_t *arg) {
    if (!arg[0]) return 1; /* an empty argument must survive as "" */
    for (const wchar_t *p = arg; *p; ++p) {
        if (*p == L' ' || *p == L'\t' || *p == L'\n' || *p == L'\v' || *p == L'"') {
            return 1;
        }
    }
    return 0;
}

size_t ql_append_quoted_arg(wchar_t *dst, const wchar_t *arg) {
    wchar_t *out = dst;
    if (!ql_arg_needs_quotes(arg)) {
        size_t len = wcslen(arg);
        memcpy(out, arg, len * sizeof(wchar_t));
        return len;
    }
    *out++ = L'"';
    const wchar_t *p = arg;
    for (;;) {
        size_t backslashes = 0;
        while (*p == L'\\') {
            ++backslashes;
            ++p;
        }
        if (!*p) {
            /* Trailing backslashes: double them, so the closing quote below
             * stays a closing quote. */
            for (size_t i = 0; i < backslashes * 2; ++i) *out++ = L'\\';
            break;
        }
        if (*p == L'"') {
            /* Double the run and add one more to escape the quote itself. */
            for (size_t i = 0; i < backslashes * 2 + 1; ++i) *out++ = L'\\';
            *out++ = L'"';
        } else {
            for (size_t i = 0; i < backslashes; ++i) *out++ = L'\\';
            *out++ = *p;
        }
        ++p;
    }
    *out++ = L'"';
    return (size_t)(out - dst);
}

wchar_t *ql_build_command_line(const wchar_t *const *argv, int argc) {
    size_t cap = 1; /* the terminator */
    for (int i = 0; i < argc; ++i) cap += QL_QUOTED_ARG_MAX(wcslen(argv[i]));
    wchar_t *line = (wchar_t *)calloc(cap, sizeof(wchar_t));
    if (!line) return NULL;
    wchar_t *out = line;
    for (int i = 0; i < argc; ++i) {
        if (i > 0) *out++ = L' ';
        out += ql_append_quoted_arg(out, argv[i]);
    }
    *out = L'\0';
    return line;
}
