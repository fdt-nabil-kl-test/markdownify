@echo off
REM Build the Windows .exe. Run on a Windows PC with Python 3.10-3.13 installed.
REM   build_windows.bat
REM Output: dist\MarkItDown Converter\MarkItDown Converter.exe  (a folder you can zip)
REM
REM NOTE: A Windows .exe CANNOT be built on a Mac — it must be built here on Windows.
REM tkinter ships with the standard python.org Windows installer (no extra step).

cd /d "%~dp0"

python -m venv .buildvenv
call .buildvenv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
echo Installing engines (markitdown + docling, ~1.5 GB, please wait)...
python -m pip install --quiet -r requirements.txt

REM Download Docling models into assets\ so the Deep tab works fully offline (~1.2 GB).
echo Fetching Docling models (one-time, ~1.2 GB)...
python fetch_models.py

REM Regenerate the Windows .ico from the drawing script.
python make_icon.py

echo Packaging (produces a ~2.3 GB folder and takes several minutes)...
pyinstaller ^
  --name "Markdownify" ^
  --windowed ^
  --noconfirm ^
  --icon markdownify.ico ^
  --add-data "assets;assets" ^
  --collect-all markitdown --collect-all magika ^
  --collect-all docling --collect-all docling_core --collect-all docling_ibm_models ^
  --collect-all docling_parse --collect-all rapidocr --collect-all onnxruntime ^
  --collect-all pdfminer --collect-all transformers --collect-all torch --collect-all torchvision ^
  --copy-metadata torch --copy-metadata tqdm --copy-metadata transformers --copy-metadata numpy ^
  --exclude-module easyocr ^
  markitdown_gui.py

echo.
echo Built: dist\Markdownify\  (zip this folder to distribute)
echo To avoid SmartScreen warnings, sign the .exe with your code-signing cert:
echo   signtool sign /fd SHA256 /a "dist\Markdownify\Markdownify.exe"
