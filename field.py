"""Field layout and drawing, oriented horizontally (attack runs left/right)
so exported clips fill a landscape slide well.

Coordinates: x = length axis (toward a goal), y = width axis (sideline to
sideline). For 'half' mode the center line sits at the left edge of the
playable rect and the end line at the right edge. For 'full' mode the
center line sits in the middle with an end/goal at each side.
"""
import pygame
from config import (
    FIELD_WIDTH_YD, HALF_LENGTH_YD, WING_INSET_YD, DIST_RESTRAIN, DIST_GOAL, DIST_END,
    CREASE_RADIUS_YD, GOAL_SIZE_YD, SUBBOX_DEPTH_YD, COACH_DEPTH_YD,
    GRASS_GREEN, ATTACK_TINT, X_ZONE_TINT, CREASE_COLOR, GOAL_COLOR,
    SUBBOX_FILL, COACH_FILL, WHITE, BLACK,
)
from draw_utils import draw_dashed_line

# Extra yards reserved below the field for the substitution box + coaches area,
# baked into the aspect ratio so it scales consistently with the field itself.
PAD_BOTTOM_YD = 12


def fit_field_rect(container, mode):
    """Compute the largest field rect (plus its scale) that fits centered in
    `container` = (x, y, w, h), for the given mode ('half' or 'full')."""
    cx, cy, cw, ch = container
    pad = 20
    aspect_w = HALF_LENGTH_YD if mode == 'half' else HALF_LENGTH_YD * 2
    aspect_h = FIELD_WIDTH_YD + PAD_BOTTOM_YD
    avail_w = max(50, cw - 2 * pad)
    avail_h = max(50, ch - 2 * pad)
    if avail_w / avail_h > aspect_w / aspect_h:
        h = avail_h
        w = h * aspect_w / aspect_h
    else:
        w = avail_w
        h = w * aspect_h / aspect_w
    x = cx + pad + (avail_w - w) / 2
    y = cy + pad + (avail_h - h) / 2
    s = w / aspect_w
    field_h = FIELD_WIDTH_YD * s
    return {'x': x, 'y': y, 'w': w, 'h': field_h, 's': s, 'mode': mode}


def draw_field(surface, layout):
    x, y, w, s, mode = layout['x'], layout['y'], layout['w'], layout['s'], layout['mode']
    field_h = layout['h']
    x0, x1 = x, x + w
    y0, y1 = y, y + field_h

    pygame.draw.rect(surface, GRASS_GREEN, (x0, y0, w, field_h))

    if mode == 'half':
        cx = x0
        _draw_end(surface, y0, y1, cx, s, direction=1)
        _draw_subbox(surface, y1, cx, cx + WING_INSET_YD * s, s)
    else:
        cx = x0 + w / 2
        _draw_end(surface, y0, y1, cx, s, direction=1)
        _draw_end(surface, y0, y1, cx, s, direction=-1)
        _draw_subbox(surface, y1, cx - WING_INSET_YD * s, cx + WING_INSET_YD * s, s)

    pygame.draw.line(surface, WHITE, (cx, y0), (cx, y1), 3)
    pygame.draw.rect(surface, BLACK, (cx - 3, (y0 + y1) / 2 - 3, 6, 6))
    pygame.draw.line(surface, WHITE, (x0, y0), (x1, y0), 3)
    pygame.draw.line(surface, WHITE, (x0, y1), (x1, y1), 3)

    return (x0, y0, x1, y1)


def _draw_end(surface, y0, y1, cx, s, direction):
    d = direction
    wing_edge = cx + d * WING_INSET_YD * s
    restrain_x = cx + d * DIST_RESTRAIN * s
    goal_x = cx + d * DIST_GOAL * s
    end_x = cx + d * DIST_END * s

    ax0, ax1 = sorted((restrain_x, goal_x))
    pygame.draw.rect(surface, ATTACK_TINT, (ax0, y0, ax1 - ax0, y1 - y0))

    zx0, zx1 = sorted((goal_x, end_x))
    pygame.draw.rect(surface, X_ZONE_TINT, (zx0, y0, zx1 - zx0, y1 - y0))

    wx0, wx1 = sorted((cx, wing_edge))
    wing_h = WING_INSET_YD * s
    pygame.draw.line(surface, WHITE, (cx, y0 + wing_h), (wing_edge, y0 + wing_h), 2)
    pygame.draw.line(surface, WHITE, (cx, y1 - wing_h), (wing_edge, y1 - wing_h), 2)

    draw_dashed_line(surface, WHITE, (restrain_x, y0), (restrain_x, y1), 3, 10, 6)
    ext = 12
    draw_dashed_line(surface, WHITE, (goal_x, y0 - ext), (goal_x, y1 + ext), 2, 6, 5)
    pygame.draw.line(surface, WHITE, (end_x, y0), (end_x, y1), 3)

    mid_y = (y0 + y1) / 2
    r = CREASE_RADIUS_YD * s
    pygame.draw.circle(surface, CREASE_COLOR, (int(goal_x), int(mid_y)), int(r), 2)
    gsize = GOAL_SIZE_YD * s
    pygame.draw.rect(surface, GOAL_COLOR, (goal_x - gsize / 2, mid_y - gsize / 2, gsize, gsize))
    pygame.draw.rect(surface, WHITE, (goal_x - gsize / 2, mid_y - gsize / 2, gsize, gsize), 1)


def _draw_subbox(surface, y1, x0, x1, s):
    x0, x1 = sorted((x0, x1))
    depth1 = SUBBOX_DEPTH_YD * s
    depth2 = COACH_DEPTH_YD * s
    r1 = pygame.Rect(x0, y1, x1 - x0, depth1)
    r2 = pygame.Rect(x0, y1 + depth1, x1 - x0, depth2)
    pygame.draw.rect(surface, SUBBOX_FILL, r1)
    pygame.draw.rect(surface, BLACK, r1, 1)
    pygame.draw.rect(surface, COACH_FILL, r2)
    pygame.draw.rect(surface, BLACK, r2, 1)
