"""
field.py - Lacrosse field layout and drawing.
=============================================

The field is oriented horizontally (attack runs left/right) so exported
clips fill a landscape slide.

Coordinates: x is the length axis (toward a goal), y is the width axis
(sideline to sideline). In 'half' mode the centre line sits at the left
edge of the playable rect and the end line at the right edge. In 'full'
mode the centre line sits in the middle with a goal at each end.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    2.0.0  2026-10-14  TCurrie11  Drawn with anti-aliased QPainter vectors; added mowing stripes.
"""
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from config import (
    FIELD_WIDTH_YD, HALF_LENGTH_YD, WING_INSET_YD, DIST_RESTRAIN, DIST_GOAL, DIST_END,
    CREASE_RADIUS_YD, GOAL_SIZE_YD, SUBBOX_DEPTH_YD, COACH_DEPTH_YD,
    GRASS_GREEN, GRASS_STRIPE, ATTACK_TINT, X_ZONE_TINT, CREASE_COLOR, GOAL_COLOR,
    SUBBOX_FILL, COACH_FILL, WHITE, BLACK,
)

# Extra yards reserved below the field for the substitution box + coaches area,
# baked into the aspect ratio so it scales consistently with the field itself.
PAD_BOTTOM_YD = 12
FIELD_PADDING_PX = 20
STRIPE_WIDTH_YD = 5
ZONE_TINT_ALPHA = 150

BOUNDARY_LINE_WIDTH = 3
MARKING_LINE_WIDTH = 2


def fit_field_rect(container, mode):
    """Compute the largest field rect (plus its scale) that fits centered in
    `container` = (x, y, w, h), for the given mode ('half' or 'full').

    Returns a dict: x, y (top-left), w, h (field only, without the sub box),
    s (pixels per yard) and mode."""
    cx, cy, cw, ch = container
    aspect_w = HALF_LENGTH_YD if mode == 'half' else HALF_LENGTH_YD * 2
    aspect_h = FIELD_WIDTH_YD + PAD_BOTTOM_YD
    avail_w = max(50, cw - 2 * FIELD_PADDING_PX)
    avail_h = max(50, ch - 2 * FIELD_PADDING_PX)
    if avail_w / avail_h > aspect_w / aspect_h:
        h = avail_h
        w = h * aspect_w / aspect_h
    else:
        w = avail_w
        h = w * aspect_h / aspect_w
    x = cx + FIELD_PADDING_PX + (avail_w - w) / 2
    y = cy + FIELD_PADDING_PX + (avail_h - h) / 2
    s = w / aspect_w
    field_h = FIELD_WIDTH_YD * s
    return {'x': x, 'y': y, 'w': w, 'h': field_h, 's': s, 'mode': mode}


def draw_field(painter: QPainter, layout):
    """Paint the whole field described by `layout`."""
    x0, y0, w, s, mode = layout['x'], layout['y'], layout['w'], layout['s'], layout['mode']
    field_h = layout['h']
    x1, y1 = x0 + w, y0 + field_h

    _draw_grass(painter, QRectF(x0, y0, w, field_h), s)

    if mode == 'half':
        centre_x = x0
        _draw_attacking_end(painter, y0, y1, centre_x, s, direction=1)
        _draw_sub_box(painter, y1, centre_x, centre_x + WING_INSET_YD * s, s)
    else:
        centre_x = x0 + w / 2
        _draw_attacking_end(painter, y0, y1, centre_x, s, direction=1)
        _draw_attacking_end(painter, y0, y1, centre_x, s, direction=-1)
        _draw_sub_box(painter, y1, centre_x - WING_INSET_YD * s, centre_x + WING_INSET_YD * s, s)

    painter.setPen(_pen(WHITE, BOUNDARY_LINE_WIDTH))
    painter.drawLine(QLineF(centre_x, y0, centre_x, y1))
    painter.drawLine(QLineF(x0, y0, x1, y0))
    painter.drawLine(QLineF(x0, y1, x1, y1))

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(*BLACK))
    painter.drawRect(QRectF(centre_x - 3, (y0 + y1) / 2 - 3, 6, 6))


def _draw_grass(painter, field_rect: QRectF, pixels_per_yard):
    """Base grass with alternating mowing stripes across the field's length."""
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(*GRASS_GREEN))
    painter.drawRect(field_rect)

    painter.setBrush(QColor(*GRASS_STRIPE))
    stripe_w = STRIPE_WIDTH_YD * pixels_per_yard
    x = field_rect.left()
    while x < field_rect.right():
        width = min(stripe_w, field_rect.right() - x)
        painter.drawRect(QRectF(x, field_rect.top(), width, field_rect.height()))
        x += 2 * stripe_w


def _draw_attacking_end(painter, y0, y1, centre_x, s, direction):
    """Paint one attacking end of the field. `direction` is +1 for the
    right-hand end, -1 for the left."""
    wing_edge_x = centre_x + direction * WING_INSET_YD * s
    restrain_x = centre_x + direction * DIST_RESTRAIN * s
    goal_x = centre_x + direction * DIST_GOAL * s
    end_x = centre_x + direction * DIST_END * s

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(*ATTACK_TINT, ZONE_TINT_ALPHA))
    painter.drawRect(_rect_between_x(restrain_x, goal_x, y0, y1))
    painter.setBrush(QColor(*X_ZONE_TINT, ZONE_TINT_ALPHA))
    painter.drawRect(_rect_between_x(goal_x, end_x, y0, y1))

    wing_h = WING_INSET_YD * s
    painter.setPen(_pen(WHITE, MARKING_LINE_WIDTH))
    painter.drawLine(QLineF(centre_x, y0 + wing_h, wing_edge_x, y0 + wing_h))
    painter.drawLine(QLineF(centre_x, y1 - wing_h, wing_edge_x, y1 - wing_h))

    painter.setPen(_pen(WHITE, BOUNDARY_LINE_WIDTH, dash=(10, 6)))
    painter.drawLine(QLineF(restrain_x, y0, restrain_x, y1))
    goal_line_overhang = 12
    painter.setPen(_pen(WHITE, MARKING_LINE_WIDTH, dash=(6, 5)))
    painter.drawLine(QLineF(goal_x, y0 - goal_line_overhang, goal_x, y1 + goal_line_overhang))
    painter.setPen(_pen(WHITE, BOUNDARY_LINE_WIDTH))
    painter.drawLine(QLineF(end_x, y0, end_x, y1))

    mid_y = (y0 + y1) / 2
    crease_r = CREASE_RADIUS_YD * s
    painter.setPen(_pen(CREASE_COLOR, MARKING_LINE_WIDTH))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QPointF(goal_x, mid_y), crease_r, crease_r)

    goal_size = GOAL_SIZE_YD * s
    painter.setPen(_pen(WHITE, 1))
    painter.setBrush(QColor(*GOAL_COLOR))
    painter.drawRect(QRectF(goal_x - goal_size / 2, mid_y - goal_size / 2, goal_size, goal_size))


def _draw_sub_box(painter, sideline_y, x0, x1, s):
    """Paint the substitution box and coaches' area below the sideline between x0 and x1."""
    left, right = sorted((x0, x1))
    sub_depth = SUBBOX_DEPTH_YD * s
    coach_depth = COACH_DEPTH_YD * s
    painter.setPen(_pen(BLACK, 1))
    painter.setBrush(QColor(*SUBBOX_FILL))
    painter.drawRect(QRectF(left, sideline_y, right - left, sub_depth))
    painter.setBrush(QColor(*COACH_FILL))
    painter.drawRect(QRectF(left, sideline_y + sub_depth, right - left, coach_depth))


def _rect_between_x(xa, xb, y0, y1) -> QRectF:
    left, right = sorted((xa, xb))
    return QRectF(left, y0, right - left, y1 - y0)


def _pen(rgb, width, dash=None) -> QPen:
    """Solid pen, or dashed when `dash` = (dash_px, gap_px) is given."""
    pen = QPen(QColor(*rgb), width)
    pen.setCapStyle(Qt.FlatCap)
    if dash:
        dash_px, gap_px = dash
        pen.setDashPattern([dash_px / width, gap_px / width])
    return pen
