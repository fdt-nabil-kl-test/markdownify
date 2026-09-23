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
if ($signtool) {
  Write-Host "signtool: $signtool"
} else {
  Write-Warning "signtool.exe not found - will fall back to Set-AuthenticodeSignature."
}
Write-Host ("signing certificate secret: " + $(if ($env:CODESIGN_PFX_BASE64) { "present" } else { "MISSING" }))

if ($env:CODESIGN_PFX_BASE64) {
  Write-Host "Signing with the company code-signing certificate (from secret)..."
  $tmp = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
  $pfx = Join-Path $tmp "codesign.pfx"
  [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:CODESIGN_PFX_BASE64))
  try {
    if ($signtool) {
      & $signtool sign /f $pfx /p $env:CODESIGN_PFX_PASSWORD /fd SHA256 /tr $timestamp /td SHA256 $File
      if ($LASTEXITCODE -ne 0) { throw "signtool failed with exit code $LASTEXITCODE" }
    } else {
      $pw = ConvertTo-SecureString $env:CODESIGN_PFX_PASSWORD -AsPlainText -Force
      $cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($pfx, $pw, 'Exportable')
      Set-AuthenticodeSignature -FilePath $File -Certificate $cert `
        -TimestampServer $timestamp -HashAlgorithm SHA256 | Out-Null
    }
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
  if ($signtool) {
    & $signtool sign /fd SHA256 /tr $timestamp /td SHA256 /sha1 $cert.Thumbprint $File
  } else {
    Set-AuthenticodeSignature -FilePath $File -Certificate $cert `
      -TimestampServer $timestamp -HashAlgorithm SHA256 | Out-Null
  }
}

$sig = Get-AuthenticodeSignature $File
if ($sig.SignerCertificate) {
  Write-Host "Signed OK: $File"
  Write-Host ("  status: " + $sig.Status)
  Write-Host ("  signer: " + $sig.SignerCertificate.Subject)
} else {
  throw "Signing did not take - $File is unsigned (status: $($sig.Status))"
}
