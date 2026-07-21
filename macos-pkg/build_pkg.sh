#!/usr/bin/env bash
# Build Markdownify-<version>.pkg — a macOS installer that drops
# Markdownify.app into /Applications. Runs on macOS (uses pkgbuild).
#
#   ./build_pkg.sh
#
# Output: Markdownify-<version>.pkg in this folder.
set -euo pipefail
cd "$(dirname "$0")"

VERSION="1.0.0"
IDENTIFIER="com.1stdigitaltrust.markdownify"
APP="../app/dist/Markdownify.app"

if [ ! -d "$APP" ]; then
  echo "App not built yet. Building it first..."
  (cd ../app && ./build_macos.sh)
fi

rm -rf stage && mkdir -p stage
cp -R "$APP" stage/

pkgbuild \
  --root stage \
  --identifier "$IDENTIFIER" \
  --version "$VERSION" \
  --install-location /Applications \
  "Markdownify-$VERSION.pkg"

rm -rf stage
echo
echo "Built: Markdownify-$VERSION.pkg"
echo
echo "For Intune deployment the pkg must be SIGNED with a Developer ID Installer"
echo "cert (and the app inside notarized). To sign:"
echo "  productsign --sign \"Developer ID Installer: <NAME> (<TEAMID>)\" \\"
echo "    Markdownify-$VERSION.pkg Markdownify-$VERSION-signed.pkg"
