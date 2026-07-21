# Markdownify — macOS PKG installer

Builds `Markdownify-1.0.0.pkg`, which installs **Markdownify.app** into
`/Applications`. This is the format **Intune** uses to deploy macOS apps.

## Build it (on a Mac)

```
./build_pkg.sh
```

The script builds the app first if needed, then packages it. Output:
`Markdownify-1.0.0.pkg` in this folder. (A prebuilt one is already here.)

## Test the install locally

```
sudo installer -pkg Markdownify-1.0.0.pkg -target /
```
Then launch Markdownify from /Applications (or Launchpad).

## ⚠️ Signing is REQUIRED for Intune

Intune will deploy a macOS `.pkg`, but Gatekeeper on managed Macs will refuse to
launch an app that isn't **signed + notarized**. Before deploying you need:

1. An Apple **Developer ID Application** cert — sign the app:
   `codesign --deep --force --options runtime --sign "Developer ID Application: <NAME> (<TEAMID>)" ../app/dist/Markdownify.app`
2. An Apple **Developer ID Installer** cert — sign the pkg:
   `productsign --sign "Developer ID Installer: <NAME> (<TEAMID>)" Markdownify-1.0.0.pkg Markdownify-1.0.0-signed.pkg`
3. **Notarize** the app/pkg with `xcrun notarytool submit` and staple it.

This requires an Apple Developer account (Martini / IT to confirm we have one).

## Deploying via Intune (macOS)

1. Intune admin center: **Apps → macOS → Add → macOS app (PKG)**.
2. Upload the **signed** `Markdownify-<version>.pkg`.
3. Set the app's bundle ID (`com.1stdigitaltrust.markdownify`) and version so
   Intune can track installs.
4. Assign to the target Mac group.

## Notes

- Install location: `/Applications/Markdownify.app`.
- The `--version` and `--identifier` are set in `build_pkg.sh`; bump `--version`
  for each new release, keep the identifier constant.
