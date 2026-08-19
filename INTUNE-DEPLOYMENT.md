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

---

# Company Portal listing (app name & description)

Paste these into the Intune app's properties. Written for staff browsing
Company Portal — deliberately plain-language, no internal jargon.

**Name**

```
Markdownify
```

**Description**

```
Convert documents into clean, plain-text Markdown (.md) files.

Turn Word, Excel, PowerPoint, PDFs and scanned documents into simple text you
can search, reuse, or feed into AI tools. Pick your files, click convert, and
the .md file is saved next to the original.

Two modes:
• Quick — instant. Best for Word, Excel, PowerPoint and normal PDFs.
• Deep — slower but smarter. Reads scanned pages and photos using OCR, and
  handles complex tables.

Not sure which to use? The app checks your files and suggests the better option.

Images from your documents are kept inside the .md file, so nothing is lost.

Everything runs on your own computer — no files are uploaded and no internet
connection is needed.
```

**Publisher**: `1st Digital Trust`

| Field | Value |
| --- | --- |
| Category | Productivity |
| App version | 1.0.3 |
| Owner / Developer | Enterprise IT |
| Information URL | *(internal wiki page, if any)* |
| Show as featured app | Optional — useful during the pilot |

**Notes (admin-only, not shown to users)**

```
Internal build. Wraps MarkItDown (Microsoft) + Docling (IBM), both MIT-licensed.
Windows MSI is signed with the 1FD internal code-signing cert — requires the
Trusted Certificate profile (see Step 1). Source:
github.com/fdt-nabil-kl-test/markdownify
```

---

# Defender ASR block ("Risky action blocked")

**Symptom** — after install, launching the app shows:

```
Risky action blocked ... Blocked by: Attack surface reduction
Rule: Block executable files from running unless they meet a prevalence,
      age, or trusted list criteria
Affected items: C:\Program Files\Markdownify\Markdownify.exe
```

**Cause** — this ASR rule blocks executables the world hasn't seen before.
Markdownify is freshly built in-house, so it has zero global prevalence and no
age. Every new internal line-of-business app hits this. It is not a sign that
anything is wrong with the app.

> Note: our internal self-signed certificate does **not** satisfy this rule's
> "trusted list" criteria. Only a publicly-trusted signing certificate builds
> reputation, and even then prevalence takes time. An exclusion is the normal,
> supported fix for internal LOB software.

## Fix A — ASR exclusion (recommended)

1. Intune → **Endpoint security** → **Attack surface reduction** → open the ASR
   policy that applies to your devices → **Edit**.
2. Find **"ASR Only Per Rule Exclusions"** (preferred — scopes the exclusion to
   this one rule) or **"Attack Surface Reduction Only Exclusions"**.
3. For the rule *Block executable files from running unless they meet a
   prevalence, age, or trusted list criteria*, add:
   ```
   C:\Program Files\Markdownify\Markdownify.exe
   ```
   (or the folder `C:\Program Files\Markdownify\`)
4. Save and let the policy sync to the pilot devices.

## Fix B — allow by file hash (tightest scope)

Microsoft Defender portal (security.microsoft.com) → **Settings** →
**Endpoints** → **Indicators** → **File hashes** → **Add indicator** → paste the
SHA-256 of `Markdownify.exe`, action **Allow**.

Get the hash on the Windows PC:
```
certutil -hashfile "C:\Program Files\Markdownify\Markdownify.exe" SHA256
```

Downside: the hash changes with every new build, so the indicator must be
re-added on each release. Fix A survives updates.

## Note on the install path

The MSI is now built with `-arch x64`, so it installs to
`C:\Program Files\Markdownify\`. Earlier builds landed in
`C:\Program Files (x86)\Markdownify\` because the package defaulted to 32-bit —
if you are excluding a path, check which one the device actually has.
