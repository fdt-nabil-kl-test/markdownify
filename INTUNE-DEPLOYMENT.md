# Markdownify — Intune Deployment Runbook

Step-by-step for deploying Markdownify to managed devices via Microsoft Intune
(intune.microsoft.com). Windows is ready today. macOS is blocked until an Apple
Developer ID is obtained (see that section).

---

# 🪟 WINDOWS — ready to deploy

## Prerequisites
- **The MSI**: from GitHub → Actions → latest green run → download the
  **`Markdownify-Windows-MSI`** artifact → unzip → `Markdownify.msi`.
- **The public cert**: `1FD-CodeSigning-Public.cer` (in `windows-msi/`).

## Step 1 — Trust the signing certificate (one-time)
So managed PCs trust the signature on the MSI.
1. Go to **intune.microsoft.com** → **Devices** → **Configuration** → **Create** → **New policy**.
2. Platform: **Windows 10 and later**. Profile type: **Templates** → **Trusted certificate** → **Create**.
3. **Name**: `1FD Code Signing – Trusted Root`.
4. **Configuration settings**: upload **`1FD-CodeSigning-Public.cer`**.
   Destination store: **Computer certificate store – Root**.
5. **Assignments**: add your target device group (or a pilot group first).
6. **Create**.

## Step 2 — Add the app (Win32 — recommended for a large installer)
Because the MSI is ~1.5 GB, package it as a Win32 app (more reliable than LOB/MSI).

**2a. Wrap the MSI into `.intunewin` (one-time, on a Windows PC):**
1. Download Microsoft's **Win32 Content Prep Tool** (`IntuneWinAppUtil.exe`) from
   `github.com/microsoft/Microsoft-Win32-Content-Prep-Tool`.
2. Put `Markdownify.msi` in a folder, e.g. `C:\pkg\`.
3. Run:
   ```
   IntuneWinAppUtil.exe -c C:\pkg -s Markdownify.msi -o C:\out
   ```
   → produces `C:\out\Markdownify.intunewin`.

**2b. Upload to Intune:**
1. **Apps** → **Windows** → **Add** → App type: **Windows app (Win32)** → **Select**.
2. **App package file**: upload `Markdownify.intunewin`.
3. **Program**:
   - Install command: `msiexec /i "Markdownify.msi" /qn`
   - Uninstall command: `msiexec /x "Markdownify.msi" /qn`
   - Install behavior: **System**.
4. **Requirements**: OS architecture **x64**, minimum OS **Windows 10 1809** (or your baseline).
5. **Detection rules**: **Manually configure** → Rule type **MSI** → Intune auto-fills
   the MSI product code. (Or "Automatically" if offered.)
6. **Assignments**:
   - **Required** = silent auto-install on the device, OR
   - **Available for enrolled devices** = shows in **Company Portal** for self-install.
7. **Review + create**.

> Simpler alternative (fewer steps, but less reliable at this size): Apps →
> Windows → Add → **Line-of-business app** → upload `Markdownify.msi` directly.
> Try this first if you prefer; switch to Win32 if installs are flaky.

## Step 3 — Pilot, then broaden
Assign to a small pilot group first. Confirm it installs and launches, then widen
the assignment. Users find it in **Company Portal** (if Available) or it just
appears (if Required).

## Updating later
Build a new MSI with a higher `Version` (keep the same UpgradeCode), re-sign, and
upload as a new version. Intune handles the upgrade.

---

# 🍎 macOS — BLOCKED until Apple Developer ID

Intune supports macOS PKG apps, but it **requires the pkg to be signed and the app
notarized by Apple**. Our pkg is currently unsigned, so Intune cannot deploy it
yet. The steps below can only be done **after** IT obtains the Apple Developer ID.

## Step 0 — Get the Apple Developer ID (procurement — IT / Martini)
1. Obtain a **D-U-N-S number** for 1st Digital Trust (free, ~1–2 weeks if not held).
2. Enrol in the **Apple Developer Program (Organization)** at developer.apple.com
   — **US$99/year**. Requires someone authorized to bind the company.
3. In the Apple Developer portal, create two certificates:
   - **Developer ID Application** (signs the app)
   - **Developer ID Installer** (signs the pkg)
   Download and install both in the signing Mac's Keychain.

## Step 1 — Sign the app (on a Mac, once certs are installed)
```
codesign --deep --force --options runtime \
  --sign "Developer ID Application: 1st Digital Trust (TEAMID)" \
  app/slimdist/Markdownify.app
```

## Step 2 — Build a signed pkg
```
pkgbuild --root <staging-with-app> --identifier com.1stdigitaltrust.markdownify \
  --version 1.0.0 --install-location /Applications --sign \
  "Developer ID Installer: 1st Digital Trust (TEAMID)" Markdownify-1.0.0.pkg
```

## Step 3 — Notarize + staple
```
xcrun notarytool submit Markdownify-1.0.0.pkg --apple-id <id> \
  --team-id TEAMID --password <app-specific-pw> --wait
xcrun stapler staple Markdownify-1.0.0.pkg
```

## Step 4 — Upload to Intune
1. **Apps** → **macOS** → **Add** → App type: **macOS app (PKG)**.
2. Upload the **signed, notarized** `Markdownify-1.0.0.pkg`.
3. Set **App bundle ID**: `com.1stdigitaltrust.markdownify`, **Version**: `1.0.0`.
4. **Assignments**: Required or Available (Company Portal).
5. **Review + create**.

---

# Before either goes to staff (governance)
Per the project rollout note, get sign-off from **Thevan (IT Risk)**, **John
(Compliance)**, and **Martini** before assigning to real users — Markdownify runs
locally and makes no external calls, but internal software distribution in a
regulated firm should have that nod on record.
