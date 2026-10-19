#!/bin/sh
# Construit dist/NovaPanel.dmg a partir de dist/NovaPanel.app.
# Signature et notarisation si ces variables sont definies :
#   MACOS_SIGN_IDENTITY  "Developer ID Application: Nom (TEAMID)"
#   MACOS_NOTARY_PROFILE profil cree avec `xcrun notarytool store-credentials`
set -eu
cd "$(dirname "$0")/../.."
APP=dist/NovaPanel.app
DMG=dist/NovaPanel.dmg

if [ -n "${MACOS_SIGN_IDENTITY:-}" ]; then
  codesign --force --deep --timestamp --options runtime \
    --entitlements packaging/macos/entitlements.plist --sign "$MACOS_SIGN_IDENTITY" "$APP"
  codesign --verify --deep --strict "$APP"
fi

tiffutil -cathidpicheck packaging/macos/dmg-background.png packaging/macos/dmg-background@2x.png \
  -out build/dmg-background.tiff
rm -f "$DMG"
create-dmg --volname NovaPanel --volicon packaging/icon.icns \
  --background build/dmg-background.tiff --window-size 660 448 --icon-size 112 \
  --icon NovaPanel.app 170 211 --app-drop-link 490 211 --hide-extension NovaPanel.app \
  --no-internet-enable "$DMG" "$APP"

if [ -n "${MACOS_SIGN_IDENTITY:-}" ]; then
  codesign --timestamp --sign "$MACOS_SIGN_IDENTITY" "$DMG"
fi
if [ -n "${MACOS_NOTARY_PROFILE:-}" ]; then
  if [ -n "${NOTARY_KEYCHAIN:-}" ]; then
    xcrun notarytool submit "$DMG" --keychain-profile "$MACOS_NOTARY_PROFILE" --keychain "$NOTARY_KEYCHAIN" --wait
  else
    xcrun notarytool submit "$DMG" --keychain-profile "$MACOS_NOTARY_PROFILE" --wait
  fi
  xcrun stapler staple "$DMG"
fi
