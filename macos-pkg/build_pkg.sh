#!/usr/bin/env bash
# Build Markdownify-<version>.pkg — a macOS installer that drops
# Markdownify.app into /Applications. Runs on macOS (uses pkgbuild).
#
#   ./build_pkg.sh
#
# Output: Markdownify-<version>.pkg in this folder.
set -euo pipefail
cd "$(dirname "$0")"

VERSION="1.0.6"
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

# Intune reads the FIRST bundle declared in the package. PyInstaller nests a
# Python.framework whose version (e.g. 3.14.6) never changes between our
# releases, so Intune saw every build as the same version and refused updates
# ("existing package is [3.14.6], the one you selected has version [3.14.6]").
# Strip the nested framework declaration so only Markdownify.app is declared.
echo "Removing nested framework bundle declaration (Intune version detection)..."
EXP="$(mktemp -d)/expanded"
pkgutil --expand "Markdownify-$VERSION.pkg" "$EXP"
python3 - "$EXP/PackageInfo" <<'PYEOF'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(re.sub(r'\s*<bundle[^>]*id="org\.python\.python"[^>]*/>', '', p.read_text()))
PYEOF
rm -f "Markdownify-$VERSION.pkg"
pkgutil --flatten "$EXP" "Markdownify-$VERSION.pkg"
rm -rf "$(dirname "$EXP")"

rm -rf stage
echo
echo "Built: Markdownify-$VERSION.pkg"
echo
echo "For Intune deployment the pkg must be SIGNED with a Developer ID Installer"
echo "cert (and the app inside notarized). To sign:"
echo "  productsign --sign \"Developer ID Installer: <NAME> (<TEAMID>)\" \\"
echo "    Markdownify-$VERSION.pkg Markdownify-$VERSION-signed.pkg"
