# Building the Windows installer via GitHub Actions

You're on a Mac, so the Windows `.msi` can't be built locally. This repo includes
a GitHub Actions workflow that builds it on a **Microsoft-hosted Windows runner**
— no Windows PC needed. You push once, then download the finished installer.

## One-time: put this on GitHub

From `markitdown-eval/`:

```bash
git add -A
git commit -m "Markdownify: combined app + Windows CI"

# Create a PRIVATE repo on github.com (e.g. 1stdigital/markdownify), then:
git remote add origin https://github.com/<org-or-you>/markdownify.git
git branch -M main
git push -u origin main
```

> Make the repo **private** — this is internal company tooling.

The push triggers the build automatically. You can also run it any time from the
repo's **Actions** tab → *Build Windows installer* → **Run workflow**.

## Get the installer

1. Open the repo's **Actions** tab.
2. Click the latest **Build Windows installer** run (green check = success).
3. Scroll to **Artifacts** and download:
   - **Markdownify-Windows-MSI** — the `Markdownify.msi` to share / push to Intune,
     plus the public signing cert.
   - **Markdownify-Windows-app-zip** — a runnable app folder (unzip, run
     `Markdownify.exe`). This is a safety net if the MSI step needs a tweak.

Share either with your team to test. They double-click the `.msi` to install
(Windows may show a SmartScreen "unknown publisher" prompt — click *More info →
Run anyway* for testing; this goes away once the signing cert is deployed via
Intune, per `windows-msi/README.md`).

## Notes

- The build takes ~20–40 min (it installs PyTorch, downloads ~1.2 GB of Docling
  models, and packages a ~2.3 GB app). That's expected.
- The `.msi` is large (~1.5–2 GB) because the Deep engine + models are bundled
  for offline use — the trade-off you chose.
- First run is also where the WiX config gets validated. If the MSI step fails,
  open the run log — it names the exact line — and send it to me; the zip
  artifact is still produced so your team isn't blocked meanwhile.
