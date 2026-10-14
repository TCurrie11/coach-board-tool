"""
config.py - Shared constants: window size, colours, field dimensions, folders.
==============================================================================

Everything tunable lives here so the rest of the code has no magic
numbers. Field measurements are in yards and are converted to pixels by
`field.fit_field_rect`.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.0.1  2026-09-15  TCurrie11  Editor and export now share one reference canvas so pieces stay aligned with the field.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    1.1.2  2026-10-14  TCurrie11  COACH_BOARD_DATA_DIR environment override for output folders.
"""
import os
import sys

# --- Window / timing -------------------------------------------------
WINDOW_WIDTH = 1300
WINDOW_HEIGHT = 800
SIDEBAR_WIDTH = 320
FIELD_MARGIN = 20
FPS = 60
EXPORT_FPS = 30
EXPORT_WIDTH = 1280
EXPORT_HEIGHT = 720

# --- Colors ------------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
YELLOW = (255, 210, 40)

GRASS_GREEN = (43, 110, 62)
ATTACK_TINT = (70, 138, 88)
X_ZONE_TINT = (58, 126, 78)
CREASE_COLOR = (242, 166, 35)
GOAL_COLOR = (25, 25, 25)
SUBBOX_FILL = (225, 225, 220)
COACH_FILL = (200, 200, 194)

PANEL_BG = (32, 32, 35)
PANEL_TEXT = (225, 225, 225)
BUTTON_BG = (55, 55, 60)
BUTTON_BG_ACTIVE = (70, 120, 190)
BUTTON_BORDER = (85, 85, 90)
BG_OUTSIDE_FIELD = (18, 18, 20)

OFFENSE_COLOR = (205, 35, 35)   # red - X (offense)
DEFENSE_COLOR = (35, 95, 205)   # blue - O (defense)
BALL_COLOR = (255, 130, 20)     # orange

PIECE_RADIUS = 15
PICK_SIZE = 13
BALL_RADIUS = 9

# --- Output folders (created automatically next to the app / .exe) -----
def _base_dir():
    """Folder the app runs from: next to the .exe/.app when frozen, else next to this file."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# COACH_BOARD_DATA_DIR redirects all output (used by the test suite so it
# never touches a coach's real saved plays or exports).
DATA_DIR = os.environ.get("COACH_BOARD_DATA_DIR") or _base_dir()
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
SAVES_DIR = os.path.join(DATA_DIR, "saved_plays")

# --- Fixed internal coordinate space -------------------------------------
# Pieces/annotations are always laid out at this size; compose_frame scales
# the *whole finished picture* to fit whatever output size is requested
# (the live editor window vs. an exported video are different sizes/aspect
# ratios), so the field and everything on it always move together.
REFERENCE_W = WINDOW_WIDTH - SIDEBAR_WIDTH - 2 * FIELD_MARGIN
REFERENCE_H = WINDOW_HEIGHT - 2 * FIELD_MARGIN

# --- Freehand-to-smooth-arrow tuning ------------------------------------
FREEHAND_MIN_DRAG = 6      # px - below this, treat as a click, not a drag
PATH_SMOOTH_MIN_DIST = 10  # px - jitter filter before spline fitting

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
