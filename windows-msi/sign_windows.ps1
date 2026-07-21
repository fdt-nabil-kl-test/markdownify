<#
  sign_windows.ps1 — free, self-signed code signing for INTERNAL distribution.

  What it does:
    1. Creates a self-signed code-signing certificate the first time (reused after).
    2. Exports the PUBLIC cert (.cer) — this is what you deploy to your fleet via
       Intune so the signature is trusted on managed machines.
    3. Signs the target file (the MSI) with a trusted timestamp.

  Run (from this folder, on Windows):
    powershell -ExecutionPolicy Bypass -File sign_windows.ps1

  Sign a specific file:
    powershell -ExecutionPolicy Bypass -File sign_windows.ps1 -File Markdownify.msi

  NOTE: the private key lives in your user certificate store. Whoever holds it can
  sign software your fleet will trust — protect the machine/account. This is a
  security decision for IT Risk (Thevan) / Martini to sign off on.
#>
param(
  [string]$File = "Markdownify.msi",
  [string]$Subject = "CN=1st Digital Trust Internal Code Signing",
  [string]$PublicCertOut = "1FD-CodeSigning-Public.cer"
)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path $File)) { throw "File not found: $File  (build the MSI first with build_msi.bat)" }

# 1. Find or create the self-signed code-signing certificate
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.Subject -eq $Subject } | Select-Object -First 1
if (-not $cert) {
  Write-Host "Creating self-signed code-signing certificate (valid 5 years)..."
  $cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $Subject `
    -FriendlyName "1st Digital Trust Internal Code Signing" `
    -CertStoreLocation Cert:\CurrentUser\My `
    -KeyExportPolicy Exportable `
    -KeyUsage DigitalSignature `
    -KeyLength 2048 `
    -NotAfter (Get-Date).AddYears(5)
} else {
  Write-Host "Reusing existing certificate: $($cert.Thumbprint)"
}

# 2. Export the public certificate for Intune deployment
Export-Certificate -Cert $cert -FilePath $PublicCertOut | Out-Null
Write-Host "Exported public cert -> $PublicCertOut  (deploy this via Intune; see README)"

# 3. Sign the file — prefer signtool (correct for MSI); fall back to PowerShell
$signtool = $null
$cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
if ($cmd) { $signtool = $cmd.Source }
if (-not $signtool) {
  $found = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
           Sort-Object FullName -Descending | Select-Object -First 1
  if ($found) { $signtool = $found.FullName }
}

$timestamp = "http://timestamp.digicert.com"
if ($signtool) {
  Write-Host "Signing with signtool: $signtool"
  & $signtool sign /fd SHA256 /tr $timestamp /td SHA256 /sha1 $cert.Thumbprint $File
  & $signtool verify /pa $File
} else {
  Write-Warning "signtool.exe not found (install the Windows SDK for best MSI support)."
  Write-Host "Falling back to Set-AuthenticodeSignature..."
  Set-AuthenticodeSignature -FilePath $File -Certificate $cert -TimestampServer $timestamp -HashAlgorithm SHA256
}

Write-Host ""
Write-Host "Done. Signed: $File"
