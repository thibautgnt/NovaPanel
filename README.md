<div align="center">

<img src="docs/logo.png" width="112" alt="NovaPanel logo">

# NovaPanel

**A lightweight SteelSeries GG replacement for the Arctis Nova Pro Wireless.**
Noise cancelling, equalizer, base station OLED screen and batteries, without GG running in the background.

English · [Français](README.fr.md)

[![Release](https://img.shields.io/github/v/release/thibautgnt/NovaPanel?label=release&color=5b8def)](https://github.com/thibautgnt/NovaPanel/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/thibautgnt/NovaPanel/total?color=5b8def)](https://github.com/thibautgnt/NovaPanel/releases)
[![CI](https://github.com/thibautgnt/NovaPanel/actions/workflows/ci.yml/badge.svg)](https://github.com/thibautgnt/NovaPanel/actions/workflows/ci.yml)
[![Notarized](https://img.shields.io/badge/macOS-notarized-success?logo=apple)](SECURITY.md)
[![Security policy](https://img.shields.io/badge/security-policy-success)](SECURITY.md)
[![License: MIT](https://img.shields.io/github/license/thibautgnt/NovaPanel?color=5b8def)](LICENSE)
![Windows | macOS | Linux](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
[![Sponsor](https://img.shields.io/badge/sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/thibautgnt)

<img src="docs/screenshot.png" width="860" alt="NovaPanel main window">

**[Try the live demo](https://thibautgnt.github.io/NovaPanel/)** in your browser, no headset needed.

</div>

## Why

It started with a small annoyance: the base station stays powered over USB when the computer is off, so its screen stayed lit all night. NovaPanel was first written to turn that screen off in the evening, when the computer sleeps or shuts down. It then grew into a full replacement for GG.

SteelSeries GG is a heavy app with several background services, only to change a few settings that are stored in the base station itself. NovaPanel talks to the base station directly over USB and does the same job in one small app that lives in the system tray.

> [!IMPORTANT]
> **NovaPanel is for people who don't use SteelSeries Sonar.** Sonar (the virtual audio mixer: game / chat / media channels, spatial audio, parametric EQ) is part of GG and needs it running. If you rely on Sonar, keep GG. NovaPanel replaces everything else: the headset, base station and screen settings.

## Features

- **Headset**: active noise cancelling / transparency (and its level), sidetone, mic volume, mute LED brightness, gain, auto power-off.
- **10-band equalizer**: drag the curve, use the base station presets, save your own curves.
- **Base station screen**
  - turns black when the computer is idle, locked, asleep or shut down (no more OLED burn-in);
  - shows "MIC MUTED" for as long as the mic is muted;
  - announces the noise cancelling mode and shows a volume bar;
  - optional NovaPanel screens: clock, now playing, CPU / RAM, or rotating;
  - live 3D preview of the base station in the app.
- **Base station**: screen brightness and dimming, line out, wireless mode, Bluetooth.
- **Batteries**: tray icon with the headset level, low battery alert, notification when the spare battery is full.
- **Automation**: per-app equalizer (switches when a game comes to the foreground), global shortcuts (`Ctrl+Alt+N` noise cancelling mode, `Ctrl+Alt+B` black screen, `Ctrl+Alt+P` next screen).
- **English and French** interface, following the system language.
- **Updates**: tells you when a new version is out (can be turned off). Starts with your computer once installed.
- **GG switch**: stop GG and keep it from starting with Windows, or bring it back for firmware updates.

<table>
<tr>
<td><img src="docs/screenshot-eq.png" alt="Equalizer"></td>
<td><img src="docs/screenshot-screen.png" alt="Base station screen settings"></td>
</tr>
</table>

## Install

### Windows

1. Download **[NovaPanel-Setup.exe](https://github.com/thibautgnt/NovaPanel/releases/latest/download/NovaPanel-Setup.exe)** and run it. No administrator rights needed.
2. In **Settings**, turn on *Launch NovaPanel at startup* and, if you like, stop GG.

The installer is not code-signed yet: Windows SmartScreen may ask you to confirm (*More info → Run anyway*). A portable zip is also available in the [release](https://github.com/thibautgnt/NovaPanel/releases/latest).

### macOS

Download **[NovaPanel.dmg](https://github.com/thibautgnt/NovaPanel/releases/latest/download/NovaPanel.dmg)**, open it and drag NovaPanel to *Applications*.

The app is signed and notarized by Apple: it opens like any other app.

### Linux

Install from source (below), then allow your user to access the base station:

```sh
sudo cp packaging/linux/70-novapanel.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
```

### From source (all systems)

Python 3.11 or later:

```sh
pip install git+https://github.com/thibautgnt/NovaPanel.git
novapanel
```

Options: `--tray` starts minimized to the tray, `--debug` prints the USB traffic.

## Compatibility

| Base station | USB ID | Status |
| --- | --- | --- |
| Arctis Nova Pro Wireless (PC / PlayStation) | `1038:12E0` | Tested |
| Arctis Nova Pro Wireless for Xbox | `1038:12E5`, `1038:225D` | Same protocol, not tested yet |

The wired Arctis Nova Pro (GameDAC Gen 2) uses a different protocol and is not supported.

| Feature | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| Headset, equalizer, screen, batteries | ✓ | ✓ | ✓ |
| Black screen when idle / locked / asleep | ✓ | ✓ | – |
| Per-app equalizer | ✓ | ✓ | – |
| Now playing screen | ✓ | – | – |
| Global shortcuts, GG switch | ✓ | – | – |

NovaPanel only runs on computers. Consoles keep working with the base station as usual; the settings you make with NovaPanel are stored in the base station and stay active when it is plugged into a console.

macOS and Linux support is new: if something does not work with your setup, please [open an issue](https://github.com/thibautgnt/NovaPanel/issues/new/choose) with the output of `novapanel --debug`.

## FAQ

**Can GG and NovaPanel run at the same time?**
Yes, but they will overwrite each other's settings. It is best to stop GG from **Settings → SteelSeries GG**.

**Where are my settings stored?**
Headset and base station settings live in the base station. NovaPanel's own settings are in `%APPDATA%\NovaPanel` (Windows), `~/Library/Application Support/NovaPanel` (macOS) or `~/.config/NovaPanel` (Linux).

**How do I update the base station firmware?**
Firmware updates still need GG. Use *Reactivate GG* in **Settings**, update, then stop it again.

## Security

- No telemetry, no account. Its only network request is an optional check for new versions on GitHub; nothing is downloaded or installed without you.
- The macOS disk image is signed with a Developer ID and notarized by Apple.
- Every release ships `SHA256SUMS.txt`, and the files built by GitHub Actions carry a build provenance attestation (`gh attestation verify <file> --repo thibautgnt/NovaPanel`).
- Code is scanned with CodeQL, and dependencies are kept up to date by Dependabot.

Details and vulnerability reporting: [SECURITY.md](SECURITY.md).

## Build

```sh
pip install -e .[dev]
pytest
python packaging/build.py   # dist/NovaPanel (Windows) or dist/NovaPanel.app (macOS)
packaging/macos/make_dmg.sh # macOS: dist/NovaPanel.dmg
```

The Windows installer is built with [Inno Setup](https://jrsoftware.org/isinfo.php) from `packaging/windows/novapanel.iss`. Pushing a `v*` tag builds both packages on GitHub Actions and attaches them to the release.

## Credits

The base station protocol was reverse-engineered by these projects:

- [ggoled](https://github.com/Donimax/ggoled): OLED screen
- [HeadsetControl](https://github.com/Sapd/HeadsetControl): equalizer, sidetone, battery
- [Arctis Sound Manager](https://github.com/loteran/Arctis-Sound-Manager): noise cancelling, transparency and other settings

Base station screen font: [Barlow](https://github.com/jpt/barlow) (SIL Open Font License). 3D preview: [three.js](https://threejs.org) (MIT).

## Support

NovaPanel is free and open source. If it saves you from running GG, you can [sponsor the project on GitHub](https://github.com/sponsors/thibautgnt).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [changelog](CHANGELOG.md).

## License

[MIT](LICENSE). NovaPanel is an unofficial project, not affiliated with or endorsed by SteelSeries. Arctis and SteelSeries are trademarks of SteelSeries ApS.
