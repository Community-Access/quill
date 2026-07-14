#!/usr/bin/env bash
# Run Quill from source on macOS / Linux. Mirror of run-from-source.bat.
#
# Picks the first Python interpreter that has wxPython installed, in order:
#   $QUILL_PYTHON -> active venv -> active conda -> ./.venv -> ./venv -> PATH,
# then runs `python -m quill` from the repo root (so the in-tree `quill`
# package is importable). Pass `--print-python` to just print the interpreter.
#
# First time, create a dev environment:
#   python3 -m venv .venv && .venv/bin/pip install -e ".[dev,ui]"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXE=""

# --- Dev data folder + dev-build flag ---
# QUILL_DATA_DIR is only honored when the dev-build flag is on, and it must live
# under your home directory. Defaulting it here keeps test data out of the repo
# and out of your real install, so you can test source changes without
# rebuilding. Override either var before calling this script.
: "${QUILL_DEV_BUILD:=1}"
: "${QUILL_DATA_DIR:=$HOME/quill-dev-data}"
export QUILL_DEV_BUILD QUILL_DATA_DIR
# Point at an installed QUILL so a source run can discover bundled engine assets
# (whisper.cpp, DECtalk, Piper under tools/speech/) that are not in the source
# tree. Search common install locations; use the first with the engine folder.
# Override by exporting QUILL_APP_ROOT yourself.
if [ -z "${QUILL_APP_ROOT:-}" ]; then
  for _r in "/c/quill:C:\\quill" "$LOCALAPPDATA/Programs/Quill:$LOCALAPPDATA\\Programs\\Quill"; do
    _probe="${_r%%:*}"; _win="${_r#*:}"
    if [ -d "$_probe/tools/speech" ]; then export QUILL_APP_ROOT="$_win"; break; fi
  done
fi
echo "[run-from-source] QUILL_DATA_DIR=$QUILL_DATA_DIR"
[ -n "${QUILL_APP_ROOT:-}" ] && echo "[run-from-source] QUILL_APP_ROOT=$QUILL_APP_ROOT"

has_wx() { [ -x "$1" ] && "$1" -c "import wx" >/dev/null 2>&1; }
try() { [ -z "$PYTHON_EXE" ] && has_wx "$1" && PYTHON_EXE="$1"; return 0; }

[ -n "${QUILL_PYTHON:-}" ] && try "$QUILL_PYTHON"
[ -n "${VIRTUAL_ENV:-}" ] && try "$VIRTUAL_ENV/bin/python"
[ -n "${CONDA_PREFIX:-}" ] && try "$CONDA_PREFIX/bin/python"
try "$ROOT/.venv/bin/python"
try "$ROOT/venv/bin/python"
[ -z "$PYTHON_EXE" ] && try "$(command -v python3 2>/dev/null || true)"
[ -z "$PYTHON_EXE" ] && try "$(command -v python 2>/dev/null || true)"

if [ -z "$PYTHON_EXE" ]; then
  echo "No Python interpreter with wxPython was found." >&2
  echo >&2
  echo "Create or activate a development environment first, for example:" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  .venv/bin/pip install -e \".[dev,ui]\"" >&2
  exit 1
fi

if [ "${1:-}" = "--print-python" ]; then
  echo "$PYTHON_EXE"
  exit 0
fi

# --- Auto-install dependencies when requirements.txt changes ---
# All the hash/compare/pip logic lives in scripts/_autodeps.py (shared with the
# Windows .bat). Reinstalls only after a real change (e.g. a git pull).
# Skip with QUILL_NO_AUTO_DEPS=1.
[ -f "$ROOT/scripts/_autodeps.py" ] && "$PYTHON_EXE" "$ROOT/scripts/_autodeps.py" "$ROOT" || true

cd "$ROOT"
# --new-window forces Quill to open its own window instead of forwarding to a
# single-instance "primary". A leftover instance.lock from a force-killed run
# could otherwise make this exit silently with no window.
exec "$PYTHON_EXE" -m quill --new-window "$@"
