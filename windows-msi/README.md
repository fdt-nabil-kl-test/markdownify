# Markdownify — Windows MSI installer

Builds `Markdownify.msi`, a standard Windows Installer package that:

- installs the app to `C:\Program Files\Markdownify`
- adds a **Start Menu** shortcut with the FD icon
- registers an **Add/Remove Programs** entry
- upgrades cleanly over an older version (no side-by-side installs)
- is **Intune-ready** — Intune deploys `.msi` line-of-business apps natively

## ⚠️ Must be built on Windows

An MSI packages the **Windows** executable, which only exists after PyInstaller
runs on Windows. It cannot be built on a Mac. This folder contains the complete
authoring; you run one script on a Windows PC.

## One-time prerequisites on the build PC

1. **Python 3.10–3.13** — https://www.python.org/downloads/ (tick "Add to PATH")
2. **.NET SDK 6+** — https://dotnet.microsoft.com/download
3. **WiX v5** — in a terminal: `dotnet tool install --global wix`
   *(the build script installs this automatically if it's missing)*

## Build it

1. Copy the whole `markitdown-eval` folder (at least `app/` and `windows-msi/`)
   to the Windows PC — the MSI build reaches into `..\app`.
2. Double-click **`build_msi.bat`** (or run it in a terminal).
3. Result: **`Markdownify.msi`** in this folder.

The script runs the PyInstaller app build first, then packages it into the MSI.

## Install / test

```
msiexec /i Markdownify.msi          REM interactive install
msiexec /i Markdownify.msi /qn      REM silent install (what Intune uses)
msiexec /x Markdownify.msi          REM uninstall
```

## Signing — free, for internal use

A single, **stable self-signed code-signing certificate** (`CN=1st Digital Trust`)
signs every build, so its identity never changes across versions. In CI,
`sign_windows.ps1` signs the MSI using the certificate supplied via two GitHub
**repository secrets**:

| Secret | Value |
| --- | --- |
| `CODESIGN_PFX_BASE64` | base64 of the `.pfx` (private key + cert) |
| `CODESIGN_PFX_PASSWORD` | the `.pfx` password |

The public half — `1FD-CodeSigning-Public.cer` (committed here) — is what you
deploy to your fleet via Intune so managed machines trust the signature.

**Where the private material lives:** `windows-msi/signing/` (git-ignored — never
committed). It contains the `.pfx`, its base64, and the password. Keep this
folder safe; anyone with it can sign software your fleet trusts. Back it up
securely (e.g. Bitwarden / a controlled vault), and have Thevan (IT Risk) /
Martini sign off on holding it.

> No paid certificate authority needed. This works ONLY on machines where the
> public cert is installed (your managed fleet). It will NOT remove the warning
> on unmanaged / external PCs — that requires a paid publicly-trusted cert.

## Deploying via Intune (Martini)

**Step A — make the internal signature trusted (one-time):**
Deploy the public cert so managed PCs trust anything we sign.
1. Intune → **Devices → Configuration → Create profile** →
   Windows 10+ → **Templates → Trusted certificate**.
2. Upload `1FD-CodeSigning-Public.cer`, store = **Computer certificate store – Root**.
3. Assign to the target device group.
   *(Optional, for AppLocker/WDAC environments: also add it to the Trusted
   Publishers store via a Platform Script / OMA-URI.)*

**Step B — deploy the app:**
1. Intune → **Apps → Windows → Add → Line-of-business app**.
2. Upload `Markdownify.msi`. Intune reads the product code and version itself.
3. Assign to the target group.

Updates: build a new MSI with a higher `Version` (keep the same `UpgradeCode`),
re-sign, and upload.

> Note: when Intune installs an MSI it runs as SYSTEM and typically does **not**
> show a SmartScreen prompt even unsigned — signing + the trusted cert is the
> belt-and-braces that also satisfies AppLocker/WDAC and manual double-click runs.

## Keep constant across releases

Keep the `UpgradeCode` GUID in `Markdownify.wxs` the same forever; bump only the
`Version`. Same for the signing certificate (reuse it, don't regenerate).

## Note on this authoring

`Markdownify.wxs` was authored on macOS and has **not** been compiled here (no
Windows / .NET available). It uses standard WiX v5 constructs and should build
as-is, but treat the first Windows build as the validation step — if `wix build`
reports an error, it will name the line, and it's almost always a small fix.
