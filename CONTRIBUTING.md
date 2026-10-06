# Contributing to metamoult

Thanks for helping! Small, focused changes are easiest to review.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev,gui]"
python -m pytest
```

Python 3.10 or newer is required.

## Ground rules

1. **Offline only.** No network access, no telemetry, no HTTP libraries.
   Coordinates are only ever shown as text.
2. **The original is never modified.** Cleaning always writes a copy.
3. **Few dependencies.** Pillow, pillow-heif, pypdf and piexif. Please discuss
   before adding another one.
4. **No real private data in the repository.** Tests must create their files
   artificially (see `tests/conftest.py`) with invented names, serial numbers
   and GPS positions. Use `samples/private/` (git-ignored) for your own photos.
5. **Every change comes with a test.** A new field rule, format or bug fix
   needs a test that fails without it.
6. **Code and docs are in English.**

## Where things live

| Path | Purpose |
| --- | --- |
| `src/metamoult/core.py` | `Finding`, `Risk`, format detection, `scan_file` |
| `src/metamoult/risk.py` | rules that rate a field and explain it |
| `src/metamoult/scanners/` | readers for images, PDF and Office files |
| `src/metamoult/cleaner.py` | writes cleaned copies |
| `src/metamoult/cli.py`, `gui.py` | command line and window |

To change how a field is rated, edit the rules in `risk.py` and add a test.

## Commits and pull requests

Use short, clear commit messages ("Add WebP XMP scanning"). Describe what
changed and why, and mention the formats you tested.

By contributing you agree that your contribution is licensed under the MIT
license of this project. Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
