"""
config.py - Shared constants: colours, sizes, field dimensions, folders.
========================================================================

Everything tunable lives here so the rest of the code has no magic
numbers. Colours are plain (r, g, b) tuples so this module, the data model
and saved files stay independent of the UI toolkit. Field measurements are
in yards and are converted to pixels by `field.fit_field_rect`.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.0.1  2026-09-15  TCurrie11  Editor and export now share one reference canvas so pieces stay aligned with the field.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    1.1.2  2026-10-14  TCurrie11  COACH_BOARD_DATA_DIR environment override for output folders.
    1.2.0  2026-10-14  TCurrie11  Dropped PATH_SMOOTH_MIN_DIST; smoothing tuning now lives in path_smoothing.py.
    2.0.0  2026-10-14  TCurrie11  Qt UI: removed pygame window/sidebar sizes and widget colours; reference canvas size is now fixed explicitly.
    2.1.0  2026-10-14  TCurrie11  Added APP_ORGANIZATION for per-user settings.
    2.1.2  2026-10-14  TCurrie11  Packaged Mac app keeps its folders in ~/Documents/Coach Board Tool, not inside the .app.
    2.1.3  2026-10-14  TCurrie11  Version bump for automated releases.
"""
import os
import sys

APP_NAME = "Coach Board Tool"
APP_VERSION = "2.1.3"
APP_ORGANIZATION = "TCurrie11"

# --- Timing / export ---------------------------------------------------
PREVIEW_FPS = 60
EXPORT_FPS = 30
EXPORT_WIDTH = 1280
EXPORT_HEIGHT = 720

# --- Fixed internal coordinate space -------------------------------------
# Pieces and annotations store their positions in this space, whatever size
# the window or exported video is. The whole picture is composed here and
# then scaled to fit the output, so the field and everything on it always
# move together. Do not change: saved plays from 1.x use these exact numbers.
REFERENCE_W = 940
REFERENCE_H = 760

# --- Colours (r, g, b) ---------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
SELECTION_HIGHLIGHT = (255, 210, 40)

GRASS_GREEN = (43, 110, 62)
GRASS_STRIPE = (47, 117, 67)
ATTACK_TINT = (70, 138, 88)
X_ZONE_TINT = (58, 126, 78)
CREASE_COLOR = (242, 166, 35)
GOAL_COLOR = (25, 25, 25)
SUBBOX_FILL = (225, 225, 220)
COACH_FILL = (200, 200, 194)
BG_OUTSIDE_FIELD = (24, 26, 30)

OFFENSE_COLOR = (205, 35, 35)   # red - X (offense)
DEFENSE_COLOR = (35, 95, 205)   # blue - O (defense)
BALL_COLOR = (255, 130, 20)     # orange

# --- Piece and annotation sizes (reference-space pixels) ----------------
PIECE_RADIUS = 15
PICK_SIZE = 13
BALL_RADIUS = 9
LINE_WIDTH = 3.5
ARROWHEAD_LENGTH = 16
PIECE_HIT_RADIUS = PIECE_RADIUS + 4
ANNOTATION_HIT_TOLERANCE = 7

# --- Freehand drawing -----------------------------------------------------
FREEHAND_MIN_DRAG = 6           # px - below this, treat as a click, not a drag
FREEHAND_SAMPLE_SPACING = 3     # px - ignore mouse moves smaller than this

# --- Editing ----------------------------------------------------------------
UNDO_LIMIT = 50
DEFAULT_MOVE_SECONDS = 1.0
DEFAULT_HOLD_SECONDS = 1.0
MIN_STEP_SECONDS = 0.05


# --- Output folders (default save/export locations, plus the error log) --
def _default_data_dir():
    """Where the app keeps its default folders and error log.

    - Running from source: next to this file.
    - Packaged Mac app: ~/Documents/Coach Board Tool. Never inside the .app -
      macOS runs freshly downloaded apps from a temporary read-only copy
      ("app translocation"), so anything written there would fail or vanish.
    - Packaged Windows .exe: next to the .exe, where coaches expect it.
    """
    if not getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(__file__))
    if sys.platform == 'darwin':
        return os.path.join(os.path.expanduser("~"), "Documents", APP_NAME)
    return os.path.dirname(sys.executable)


# COACH_BOARD_DATA_DIR redirects all output (used by the test suite so it
# never touches a coach's real saved plays or exports).
DATA_DIR = os.environ.get("COACH_BOARD_DATA_DIR") or _default_data_dir()
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
SAVES_DIR = os.path.join(DATA_DIR, "saved_plays")

# --- Field dimensions (yards), horizontal orientation -------------------
# x-axis = length (toward the goal), y-axis = sideline-to-sideline width.
FIELD_WIDTH_YD = 60      # sideline to sideline
HALF_LENGTH_YD = 55      # center line to end line
WING_INSET_YD = 10       # wing area, measured from center line and from sideline
DIST_RESTRAIN = 20       # restraining line, measured from center line
DIST_GOAL = 40           # goal line, measured from center line (55 - 15)
DIST_END = 55            # end line, measured from center line
CREASE_RADIUS_YD = 3
GOAL_SIZE_YD = 2
SUBBOX_DEPTH_YD = 6
COACH_DEPTH_YD = 5
