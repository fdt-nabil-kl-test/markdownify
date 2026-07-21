@echo off
REM ============================================================
REM  Build Markdownify.msi  —  RUN THIS ON WINDOWS ONLY.
REM
REM  One-time prerequisites on the build PC:
REM    1. Python 3.10-3.13   (python.org)
REM    2. .NET SDK 6+        (https://dotnet.microsoft.com/download)
REM    3. WiX v5 tool:       dotnet tool install --global wix
REM
REM  Then just double-click this file (or run it in a terminal).
REM  Output:  Markdownify.msi  in this folder.
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/3] Building the app with PyInstaller...
call ..\app\build_windows.bat
if errorlevel 1 (echo App build failed. & exit /b 1)

cd /d "%~dp0"

echo [2/3] Checking WiX toolset...
where wix >nul 2>nul
if errorlevel 1 (
  echo Installing WiX v5 ^(dotnet tool^)...
  dotnet tool install --global wix
  if errorlevel 1 (echo Could not install WiX. Install .NET SDK first. & exit /b 1)
)

echo [3/4] Building the MSI...
wix build Markdownify.wxs -o Markdownify.msi
if errorlevel 1 (echo MSI build failed. & exit /b 1)

echo [4/4] Signing the MSI (free self-signed, for internal use)...
powershell -ExecutionPolicy Bypass -File sign_windows.ps1 -File Markdownify.msi
if errorlevel 1 (echo WARNING: signing failed - the unsigned MSI is still usable. Continuing.)

echo.
echo Done. Created: %~dp0Markdownify.msi
echo Public cert for Intune: %~dp01FD-CodeSigning-Public.cer
echo Test it:  msiexec /i Markdownify.msi
echo Silent (Intune):  msiexec /i Markdownify.msi /qn
endlocal
