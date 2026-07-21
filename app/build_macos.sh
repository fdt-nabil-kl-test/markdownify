#!/usr/bin/env bash
# Build the macOS .app. Run on a Mac.
#   ./build_macos.sh
# Output: dist/MarkItDown Converter.app
set -euo pipefail
cd "$(dirname "$0")"

# tkinter must be available. On Homebrew Python: brew install python-tk@3.14
python3 -c "import tkinter" 2>/dev/null || {
  echo "ERROR: tkinter missing. On Homebrew Python run: brew install python-tk@\$(python3 -c 'import sys;print(f\"{sys.version_info.major}.{sys.version_info.minor}\")')"
  exit 1
}

python3 -m venv .buildvenv
./.buildvenv/bin/pip install --quiet --upgrade pip
echo "Installing engines (markitdown + docling ~1.5 GB, please wait)..."
./.buildvenv/bin/pip install --quiet -r requirements.txt

# Download Docling models into assets/ so the Deep tab works fully offline (~1.2 GB).
echo "Fetching Docling models (one-time, ~1.2 GB)..."
./.buildvenv/bin/python fetch_models.py

# Regenerate the icon (.icns) from the drawing script.
./.buildvenv/bin/python make_icon.py
rm -rf markdownify.iconset && mkdir markdownify.iconset
for sz in 16 32 128 256 512; do
  sips -z $sz $sz icon_master.png --out "markdownify.iconset/icon_${sz}x${sz}.png" >/dev/null
  sips -z $((sz*2)) $((sz*2)) icon_master.png --out "markdownify.iconset/icon_${sz}x${sz}@2x.png" >/dev/null
done
iconutil -c icns markdownify.iconset -o markdownify.icns

echo "Packaging (this produces a ~2.3 GB app and takes several minutes)..."
./.buildvenv/bin/pyinstaller \
  --name "Markdownify" \
  --windowed \
  --noconfirm \
  --icon markdownify.icns \
  --add-data "assets:assets" \
  --collect-all markitdown --collect-all magika \
  --collect-all docling --collect-all docling_core --collect-all docling_ibm_models \
  --collect-all docling_parse --collect-all rapidocr --collect-all onnxruntime \
  --collect-all pdfminer --collect-all transformers --collect-all torch --collect-all torchvision \
  --copy-metadata torch --copy-metadata tqdm --copy-metadata transformers --copy-metadata numpy \
  --exclude-module easyocr \
  markitdown_gui.py

echo
echo "Built: dist/Markdownify.app"
echo "To distribute without Gatekeeper warnings, code-sign + notarize:"
echo "  codesign --deep --force --sign \"Developer ID Application: <NAME>\" \"dist/Markdownify.app\""
echo "  xcrun notarytool submit ... (see Apple notarization docs)"
