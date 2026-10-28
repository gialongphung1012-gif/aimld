# AIMLD iOS sample (SwiftUI)

An Xcode project is included at `ios/AIMLD.xcodeproj`. The app is a standalone license activation client; it does not include the original game's code, a tweak loader, or a signed IPA.

## Configure and build

1. Open `ios/AIMLD.xcodeproj` in Xcode on a Mac or a supported remote Mac build service.
2. Open `AIMLD/LicenseViewModel.swift` and replace `https://YOUR-DOMAIN.example` with the deployed AIMLD HTTPS origin.
3. In the project target, choose your Apple development team and set a unique Bundle Identifier if needed.
4. Select an iOS 16+ simulator or connected iPhone and build/run.
5. For a signed IPA, select **Any iOS Device (arm64)**, choose **Product → Archive**, then use Organizer to distribute/export the archive with your signing identity and provisioning profile.

A command-line archive can be created on a configured Mac:

```sh
xcodebuild -project ios/AIMLD.xcodeproj -scheme AIMLD -configuration Release -destination 'generic/platform=iOS' -archivePath build/AIMLD.xcarchive archive
```

Exporting an IPA additionally requires a valid signing team, provisioning profile and an `ExportOptions.plist` matched to that account. A browser on iPhone alone cannot sign an IPA using Apple's standard Xcode workflow; use a remote Mac/cloud build service if you do not own a Mac.

## License behavior

- Activation posts the entered key and device ID to `/api/license/activate`.
- The returned activation token is stored in iOS Keychain.
- “Kiểm tra phiên đã kích hoạt” validates the token with the server; it does not trust a local `isLicensed` flag.
- No admin password or server pepper is embedded in the app.
- A device ID in this sample is an app-generated UUID stored in Keychain, not a hardware-unique identifier. Reinstalling the app may produce a new ID; admin device reset is available from the web panel.
- There is no offline authorization cache. If the server cannot be reached, the app reports the error and does not claim a fresh validation succeeded.
