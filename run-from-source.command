#!/usr/bin/env bash
# Finder launcher for Quill (macOS).
#
# Double-click this file in Finder to run Quill from source. macOS opens it in
# Terminal, which runs this wrapper. All it does is locate its own directory
# (the repo root) and hand off to run-from-source.sh, forwarding any arguments.
#
# The first time you use it, macOS may block it ("cannot be opened because it is
# from an unidentified developer"). Right-click the file -> Open -> Open, or run
# `xattr -d com.apple.quarantine run-from-source.command` once in Terminal.
#
# Note: .command files must stay executable (chmod +x) to launch from Finder.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/run-from-source.sh" "$@"
