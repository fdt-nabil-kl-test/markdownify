<#
  sign_windows.ps1 — sign the MSI for INTERNAL distribution.

  In CI: signs with the company code-signing certificate supplied via the
  GitHub secrets CODESIGN_PFX_BASE64 (+ CODESIGN_PFX_PASSWORD). This is a stable,
  self-signed cert; deploy its public .cer to your fleet via Intune so managed
  machines trust it (see README).

  Locally (no secret set): falls back to a throwaway self-signed cert — dev only.

  Run:  powershell -ExecutionPolicy Bypass -File sign_windows.ps1 -File Markdownify.msi
#>
param(
  [string]$File = "Markdownify.msi"
)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
if (-not (Test-Path $File)) { throw "File not found: $File  (build the MSI first)" }

$timestamp = "http://timestamp.digicert.com"

# Locate signtool.exe (Windows SDK)
$signtool = (Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
if (-not $signtool) {
  $signtool = (Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" `
               -ErrorAction SilentlyContinue | Sort-Object FullName -Descending |
               Select-Object -First 1).FullName
}
if (-not $signtool) { throw "signtool.exe not found (install the Windows SDK)." }

if ($env:CODESIGN_PFX_BASE64) {
  Write-Host "Signing with the company code-signing certificate (from secret)..."
  $tmp = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
  $pfx = Join-Path $tmp "codesign.pfx"
  [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:CODESIGN_PFX_BASE64))
  try {
    & $signtool sign /f $pfx /p $env:CODESIGN_PFX_PASSWORD /fd SHA256 /tr $timestamp /td SHA256 $File
  } finally {
    Remove-Item $pfx -Force -ErrorAction SilentlyContinue
  }
} else {
  Write-Warning "No CODESIGN_PFX_BASE64 secret set — using a throwaway self-signed cert (dev only)."
  $subject = "CN=1st Digital Trust"
  $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
          Where-Object { $_.Subject -eq $subject } | Select-Object -First 1
  if (-not $cert) {
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
              -CertStoreLocation Cert:\CurrentUser\My -KeyExportPolicy Exportable `
              -KeyLength 2048 -NotAfter (Get-Date).AddYears(5)
  }
  & $signtool sign /fd SHA256 /tr $timestamp /td SHA256 /sha1 $cert.Thumbprint $File
}

& $signtool verify /pa $File
Write-Host "Signed: $File"
