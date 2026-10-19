# Security

## What NovaPanel does and does not do

- It talks to the Arctis Nova Pro Wireless base station over USB (HID), and to nothing else.
- Its only network request is the update check: once at startup and once a day, it reads `https://api.github.com/repos/thibautgnt/NovaPanel/releases/latest`. Nothing is sent about you or your device, nothing is downloaded or installed automatically, and you can turn it off in **Settings**. There is no telemetry and no account.
- The interface is a local page with remote content disabled. Links (GitHub, Sponsor, new version) open in your browser.
- The installed app turns on *Start at login* the first time it runs. You can turn it off in **Settings**.
- It runs as your user. No administrator rights are needed, except on Windows when you choose to stop SteelSeries GG from starting (that writes one registry value, after a Windows prompt).
- Settings are a plain JSON file in your user folder.

## Verifying a download

Every release comes with `SHA256SUMS.txt`.

```sh
# macOS / Linux
shasum -a 256 -c SHA256SUMS.txt --ignore-missing
# Windows (PowerShell)
Get-FileHash .\NovaPanel-Setup.exe -Algorithm SHA256
```

Files built by GitHub Actions also carry a [build provenance attestation](https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations) that proves they were built from this repository's source:

```sh
gh attestation verify NovaPanel-Setup.exe --repo thibautgnt/NovaPanel
```

The macOS disk image is signed with a Developer ID certificate (team `33MB9HPP65`) and notarized by Apple:

```sh
spctl -a -vv -t open --context context:primary-signature NovaPanel.dmg
```

The Windows installer is not code-signed yet, so SmartScreen may warn on first launch. Use the checksum or attestation above to check it.

## Reporting a vulnerability

Please do not open a public issue. Use [private vulnerability reporting](https://github.com/thibautgnt/NovaPanel/security/advisories/new) instead. You will get an answer within a week.

Only the latest release receives fixes.
