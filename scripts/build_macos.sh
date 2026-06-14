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

if [[ -n "${IDENTITY:-}" ]]; then
  echo "==> Codesigning (hardened runtime, inside-out)"
  # --deep is unreliable: it leaves nested .so/.dylib without a Developer ID
  # signature or secure timestamp, which fails notarization. Sign every nested
  # Mach-O individually first, then the bundle last. The main executables and
  # the bundle carry the hardened-runtime entitlements the bundled Python
  # interpreter needs (JIT, unsigned executable memory, library validation off).
  find "$APP" \( -name "*.so" -o -name "*.dylib" \) -print0 \
    | xargs -0 -P 6 -I{} codesign --force --timestamp --options runtime --sign "$IDENTITY" "{}"
  if [[ -e "$APP/Contents/Frameworks/Python.framework/Versions/3.11/Python" ]]; then
    codesign --force --timestamp --options runtime --sign "$IDENTITY" \
      "$APP/Contents/Frameworks/Python.framework/Versions/3.11/Python"
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
hdiutil create -volname Quill -srcfolder "$APP" -ov -format UDZO "$DMG"

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
