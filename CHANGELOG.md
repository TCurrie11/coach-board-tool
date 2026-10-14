# Changelog

All notable changes to Coach Board Tool. Versions follow
[Semantic Versioning](https://semver.org/).

Author: [TCurrie11](https://github.com/TCurrie11)

## 2.1.0 - 2026-10-14
- Native **Open / Save / Save as** dialogs replace the file-name text box;
  export also asks where to save. Dialogs remember the last folder used.
- **File → New play** and **File → Open recent** (last 8 plays).
- The window title shows the play's name and marks unsaved changes. You're
  asked to save before closing, opening another play or starting a new one.
  Changes are detected by comparing with the last-saved state, so undoing
  back to it counts as no changes.
- Drag a play file onto the window, or pass one on the command line, to open it.
- 5 new end-to-end tests for dialogs, unsaved changes and recent files.

## 2.0.0 - 2026-10-14
Moved from pygame to Qt (PySide6).

- **Look:** dark Fusion theme, grouped sidebar, tool buttons with icons drawn
  by the board's own renderer, status bar, menus and keyboard shortcuts.
- **Drawing:** everything is rendered as anti-aliased vectors through one
  transform, so lines stay sharp at any window size, rotation or export size.
  Pass dashes run continuously along the curve, pieces have a soft shadow,
  and player letters stay upright when the field is rotated.
- **Window:** freely resizable; hovering a piece highlights it in Select and
  Delete modes; the cursor reflects the active tool.
- **Export:** progress dialog with cancel; frames are streamed to the encoder
  instead of being held in memory.
- **Fix:** GIF exports played about 3x too slowly (frame delay was passed in
  seconds; imageio expects milliseconds).
- **Errors:** the crash dialog now works on every platform, not just Windows,
  and also catches errors raised inside button handlers.
- **Architecture:** the 570-line `App` class is split into `PlayEditor`
  (editing rules, no UI), `BoardView` (field widget) and `MainWindow`
  (controls). `draw_utils.py` is now `geometry.py`.
- **Tests:** `test_headless.py` rewritten as 20 independent tests, including
  click mapping under rotation and GIF timing. Saves from 1.x load unchanged.

## 1.2.0 - 2026-10-14
- Freehand arrows and passes are now properly cleaned up on release. The new
  `path_smoothing` module resamples, denoises, simplifies (Ramer-Douglas-Peucker)
  and refits (centripetal Catmull-Rom) the mouse path, removing hand wobble
  while keeping intended bends. Near-straight drags snap to a straight line.
- Arrowheads aim along the end of the curve instead of its last pixel.
- `test_path_smoothing.py`: unit tests using simulated wobbly mouse drags.

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
