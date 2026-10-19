# Changelog

All notable changes to NovaPanel. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Release notes on the website, taken from this changelog.

### Fixed
- App and curve names in the automation lists, and the equalizer graph, are no longer built as HTML.

## [1.1.0] - 2026-10-19

### Added
- English interface, alongside French. The language follows the system and can be changed in Settings.
- Windows installer and a signed, notarized macOS disk image.
- Notification when a new version is published on GitHub (can be turned off).
- The installed app starts at login after its first launch.
- About window with version, credits and support links.
- `SHA256SUMS.txt` and build provenance attestations for every release.

### Fixed
- The base station's own volume bar no longer stays over the NovaPanel screen when turning the dial.

## [1.0.0] - 2026-10-19

### Added
- First public release: noise cancelling, sidetone, mic, 10-band equalizer, base station screen (black screen when idle or locked, mic muted warning, clock, now playing, CPU / RAM), batteries, per-app equalizer, global shortcuts, GG switch.
- Windows, macOS and Linux support.

[Unreleased]: https://github.com/thibautgnt/NovaPanel/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/thibautgnt/NovaPanel/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/thibautgnt/NovaPanel/releases/tag/v1.0.0
