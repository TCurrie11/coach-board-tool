# Changelog

All notable changes to Coach Board Tool. Versions follow
[Semantic Versioning](https://semver.org/).

Author: [TCurrie11](https://github.com/TCurrie11)

## 1.1.2 - 2026-10-14
- **Fix:** the test suite deleted the real `exports/` and `saved_plays/`
  folders. It now writes to a temporary folder via the new
  `COACH_BOARD_DATA_DIR` environment override, and cleans up after itself.

## 1.1.1 - 2026-10-14
- Every source file now has a header with its purpose, author and version history.
- Docstrings for all public functions and classes.
- Added `.gitignore` for bytecode, runtime output folders and build artefacts.

## 1.1.0 - 2026-09-16
- PyInstaller spec and GitHub Actions workflow that build a native macOS `.app`.

## 1.0.1 - 2026-09-15
- Fixed pieces drifting away from the field in exported videos: the editor and
  the exporter now compose on one shared reference canvas.

## 1.0.0 - 2026-09-15
- Initial release: half/full field, X/O/ball pieces, freehand arrows and passes,
  picks, step timeline, preview, MP4/GIF export, JSON save/load.
