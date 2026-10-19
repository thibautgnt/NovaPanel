# Contributing

Thanks for your interest in NovaPanel. Bug reports, tests on other systems and pull requests are welcome.

## Reporting a bug

Open an [issue](https://github.com/thibautgnt/NovaPanel/issues/new/choose) with your system, your base station model and firmware, and the output of `novapanel --debug`. For security issues, see [SECURITY.md](SECURITY.md) instead.

## Development

```sh
git clone https://github.com/thibautgnt/NovaPanel.git
cd NovaPanel
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .[dev]
pytest
python -m novapanel --debug
```

Layout:

- `novapanel/device.py`: USB protocol of the base station
- `novapanel/screen.py`: what is drawn on the 128x64 OLED
- `novapanel/system/`: everything that depends on the operating system
- `novapanel/ui/`: the interface (HTML, CSS, JavaScript), talking to Python through `QWebChannel`
- `novapanel/i18n.py`: English and French texts

## Pull requests

- `main` is protected: every change goes through a pull request and needs the CI to pass (tests on Windows, macOS and Linux, CodeQL).
- Keep a pull request to one topic. Add a test when you change logic.
- Titles follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `ci:`, `chore:`, `refactor:`, `test:`. Pull requests are squash-merged, so the title becomes the commit message.
- New user-facing text goes in both languages in `novapanel/i18n.py`.

## Releases

Update `novapanel/__version__` and `CHANGELOG.md`, then push a `vX.Y.Z` tag. GitHub Actions builds the Windows installer and the macOS disk image, attests them and publishes the checksums.
