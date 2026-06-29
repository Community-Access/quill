#!/usr/bin/env bash
# Build, sign, notarize, and package the macOS Quill app.
# Prereqs: pip install -e ".[ui,macos]"; an Apple "Developer ID Application"
# certificate; and either an authenticated `asc` (asc auth login) or a
# notarytool keychain profile (xcrun notarytool store-credentials).
set -euo pipefail

ENTITLEMENTS="scripts/macos_entitlements.plist"

echo "==> Building .app with py2app"
python scripts/setup_macos.py py2app

APP="dist/Quill.app"
DMG="dist/Quill.dmg"

# Lift native binaries out of python311.zip. py2app packs pure-Python packages
# into python311.zip, but a package that ships an extension module (protobuf's
# google/_upb/_message.abi3.so) gets zipped along with its .so. dlopen cannot
# load a Mach-O from inside a zip, and codesign cannot sign one there either, so
# notarization rejects it ("binary is not signed"). PIL avoids this by being
# listed in setup_macos.py's `packages`, but `google` is a PEP 420 namespace
# package py2app's finder can't resolve. Extract any top-level package that
# carries a native binary into the on-disk site dir (already on sys.path) and
# drop it from the zip, so the inside-out signing pass below reaches the .so.
# Derive the bundled Python version from the interpreter that built the app
# (py2app bundles whatever Python ran setup_macos.py; that script now enforces
# >=3.12, #755). This was hard-coded to 3.11 / "311", which on any other version
# silently skipped both the native-lib lift below and the framework codesign.
PYVER="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTAG="${PYVER//./}"

ZIP="$APP/Contents/Resources/lib/python${PYTAG}.zip"
SITE="$APP/Contents/Resources/lib/python${PYVER}"
if [[ -f "$ZIP" ]]; then
  NATIVE_PKGS=$(unzip -Z1 "$ZIP" | grep -iE '\.(so|dylib)$' | grep -v '\.dSYM/' \
    | cut -d/ -f1 | sort -u)
  for pkg in $NATIVE_PKGS; do
    echo "==> Lifting native package '$pkg' out of python${PYTAG}.zip"
    ( cd "$SITE" && unzip -oq "../python${PYTAG}.zip" "$pkg/*" )
    zip -dq "$ZIP" "$pkg/*"
  done
fi

# Bundle @rpath dylibs that macholib did not follow. CPython C-extensions
# (_ctypes->libffi, _ssl->libssl/libcrypto, _hashlib, _sqlite3, _lzma, _bz2,
# expat, tcl/tk, z, ...) link their libraries as @rpath/lib*.dylib. With a
# non-framework Python (Homebrew/conda) those dylibs live in <prefix>/lib and
# py2app does not copy them, so the .app dlopen-fails inside py2app's own
# bootstrap, before any QUILL code runs — the launch hang in #755. Copy each
# missing @rpath dylib from the build interpreter's lib dir into Resources/lib,
# looping to a fixpoint so transitive deps (libssl->libcrypto) are caught. The
# newly copied dylibs are themselves rescanned each pass. A framework Python
# already ships these, so this is a no-op there.
PYLIBDIR="$(python -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR") or "")')"
RES_LIB="$APP/Contents/Resources/lib"
if [[ -n "$PYLIBDIR" && -d "$RES_LIB" ]]; then
  echo "==> Bundling missing @rpath dylibs (build libdir: $PYLIBDIR)"
  while : ; do
    missing=""
    # Process substitution (< <(...)) keeps the loop body in the current shell,
    # so 'missing' accumulates across iterations (a piped while would not).
    while IFS= read -r -d '' macho; do
      while IFS= read -r ref; do
        name="${ref#@rpath/}"
        if [[ ! -e "$RES_LIB/$name" && -e "$PYLIBDIR/$name" ]]; then
          missing+="$name"$'\n'
        fi
      done < <(otool -L "$macho" 2>/dev/null | awk '/@rpath\/.*\.dylib/{print $1}')
    done < <(find "$APP" -type f \( -name '*.so' -o -name '*.dylib' \) -print0)
    missing="$(printf '%s' "$missing" | sed '/^$/d' | sort -u)"
    [[ -z "$missing" ]] && break
    while IFS= read -r name; do
      echo "    + $name"
      cp "$PYLIBDIR/$name" "$RES_LIB/$name"
    done <<< "$missing"
  done
fi

if [[ -n "${IDENTITY:-}" ]]; then
  echo "==> Codesigning (hardened runtime, inside-out)"
  # --deep is unreliable: it leaves nested .so/.dylib without a Developer ID
  # signature or secure timestamp, which fails notarization. Sign every nested
  # Mach-O individually first, then the bundle last. The main executables and
  # the bundle carry the hardened-runtime entitlements the bundled Python
  # interpreter needs (JIT, unsigned executable memory, library validation off).
  find "$APP" \( -name "*.so" -o -name "*.dylib" \) -print0 \
    | xargs -0 -P 6 -I{} codesign --force --timestamp --options runtime --sign "$IDENTITY" "{}"
  if [[ -e "$APP/Contents/Frameworks/Python.framework/Versions/$PYVER/Python" ]]; then
    codesign --force --timestamp --options runtime --sign "$IDENTITY" \
      "$APP/Contents/Frameworks/Python.framework/Versions/$PYVER/Python"
  fi
  for exe in "$APP/Contents/MacOS/"*; do
    codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" \
      --sign "$IDENTITY" "$exe"
  done
  codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" \
    --sign "$IDENTITY" "$APP"
  codesign --verify --strict --verbose=2 "$APP"
else
  echo "!! IDENTITY not set — skipping codesign (set IDENTITY='Developer ID Application: ...')"
fi

echo "==> Creating DMG"
# Stage the volume contents so the DMG includes an "Applications" alias next to
# the app. Without this the volume holds only Quill.app and there is nothing to
# drag onto, forcing users to open Applications by hand (issue #662). The alias
# is the standard drag-to-install convention shipped by most macOS DMGs.
STAGE="dist/dmg-stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/Quill.app"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname Quill -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -rf "$STAGE"

# Notarize the DMG. Prefer `asc` (Apple Notary API v2, App Store Connect API
# key auth); fall back to a notarytool keychain profile when NOTARY_PROFILE is
# set. Stapling the DMG lets Gatekeeper verify it offline.
if command -v asc >/dev/null 2>&1 && asc auth status >/dev/null 2>&1; then
  echo "==> Notarizing with asc"
  asc notarization submit --file "$DMG" --wait
  echo "==> Stapling"
  xcrun stapler staple "$DMG"
elif [[ -n "${NOTARY_PROFILE:-}" ]]; then
  echo "==> Notarizing with notarytool"
  xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
  echo "==> Stapling"
  xcrun stapler staple "$DMG"
else
  echo "!! No notarization credentials — set up 'asc auth login' or NOTARY_PROFILE"
fi

echo "==> Done: $DMG"
