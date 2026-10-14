"""
render.py - Drawing routines for pieces and annotations.
========================================================

Pure drawing: given a QPainter and a piece/annotation, paint it. No state
and no layout logic - positions arrive already in reference-canvas space,
and the caller's painter transform takes care of rotation and scaling.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    1.2.0  2026-10-14  TCurrie11  Arrowheads aim along the curve's last 14 px, not its final segment.
    2.0.0  2026-10-14  TCurrie11  QPainter rendering: anti-aliased curves, continuous dashes, piece shadows, upright labels.
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF

from config import (
    OFFENSE_COLOR, DEFENSE_COLOR, BALL_COLOR, WHITE, BLACK, SELECTION_HIGHLIGHT,
    PIECE_RADIUS, PICK_SIZE, BALL_RADIUS, LINE_WIDTH, ARROWHEAD_LENGTH,
)
from path_smoothing import path_length, point_at_distance_from_end

ARROWHEAD_SPREAD_DEG = 28
PASS_DASH_PX = 11
PASS_GAP_PX = 7
SHADOW_OFFSET = 1.5
SHADOW_COLOR = QColor(0, 0, 0, 90)
PIECE_RING_WIDTH = 3
SELECTION_RING_GAP = 6

TEAM_COLORS = {'X': OFFENSE_COLOR, 'O': DEFENSE_COLOR}


def piece_label_font() -> QFont:
    """Bold font used for the X / O letters on pieces."""
    font = QFont()
    font.setBold(True)
    font.setPixelSize(17)
    return font


def draw_piece(painter: QPainter, team, pos, label_font: QFont, selected=False, label_rotation_deg=0.0):
    """Draw one player or the ball at `pos`, with a highlight ring if `selected`.
    `label_rotation_deg` turns the X / O letter, so it can be kept upright
    when the whole field is rotated."""
    centre = QPointF(*pos)
    radius = BALL_RADIUS if team == 'BALL' else PIECE_RADIUS
    outline_color = BLACK if team == 'BALL' else WHITE
    fill_color = BALL_COLOR if team == 'BALL' else TEAM_COLORS[team]
    outline_width = 2 if team == 'BALL' else PIECE_RING_WIDTH

    painter.setPen(Qt.NoPen)
    painter.setBrush(SHADOW_COLOR)
    painter.drawEllipse(centre + QPointF(SHADOW_OFFSET, SHADOW_OFFSET),
                        radius + outline_width, radius + outline_width)

    painter.setBrush(QColor(*outline_color))
    painter.drawEllipse(centre, radius + outline_width, radius + outline_width)
    painter.setBrush(QColor(*fill_color))
    painter.drawEllipse(centre, radius, radius)

    if team != 'BALL':
        painter.save()
        painter.translate(centre)
        painter.rotate(label_rotation_deg)
        painter.setFont(label_font)
        painter.setPen(QColor(*WHITE))
        painter.drawText(QRectF(-radius, -radius, 2 * radius, 2 * radius), Qt.AlignCenter, team)
        painter.restore()

    if selected:
        ring_radius = radius + outline_width + SELECTION_RING_GAP
        painter.setPen(QPen(QColor(*SELECTION_HIGHLIGHT), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(centre, ring_radius, ring_radius)


def draw_annotation(painter: QPainter, annotation):
    """Draw an arrow (solid), pass (dashed) or pick (triangle) annotation."""
    if annotation.kind == 'pick':
        _draw_pick(painter, annotation.points[0], annotation.color)
    elif len(annotation.points) >= 2:
        _draw_movement_line(painter, annotation.points, annotation.color,
                            dashed=(annotation.kind == 'pass'))


def _draw_movement_line(painter, points, rgb, dashed):
    """Curve through `points` finished with an arrowhead. The curve stops just
    short of the tip so the thick line never pokes out past the arrowhead."""
    color = QColor(*rgb)
    tip = points[-1]
    aim_from = point_at_distance_from_end(points, ARROWHEAD_LENGTH)
    shaft = _trim_end(points, ARROWHEAD_LENGTH * 0.6)

    pen = QPen(color, LINE_WIDTH)
    pen.setJoinStyle(Qt.RoundJoin)
    if dashed:
        pen.setCapStyle(Qt.FlatCap)
        pen.setDashPattern([PASS_DASH_PX / LINE_WIDTH, PASS_GAP_PX / LINE_WIDTH])
    else:
        pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(_polyline_path(shaft))

    painter.setPen(QPen(color, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(color)
    painter.drawPolygon(_arrowhead(aim_from, tip))


def _draw_pick(painter, centre, rgb):
    """Upward-pointing filled triangle with a white outline."""
    x, y = centre
    triangle = QPolygonF([QPointF(x, y - PICK_SIZE),
                          QPointF(x - PICK_SIZE, y + PICK_SIZE),
                          QPointF(x + PICK_SIZE, y + PICK_SIZE)])
    painter.setPen(QPen(QColor(*WHITE), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(QColor(*rgb))
    painter.drawPolygon(triangle)


def _arrowhead(aim_from, tip) -> QPolygonF:
    """Triangle with its point at `tip`, pointing along aim_from -> tip."""
    heading = math.atan2(tip[1] - aim_from[1], tip[0] - aim_from[0])
    spread = math.radians(ARROWHEAD_SPREAD_DEG)
    back_left = heading + math.pi - spread
    back_right = heading + math.pi + spread
    return QPolygonF([
        QPointF(*tip),
        QPointF(tip[0] + ARROWHEAD_LENGTH * math.cos(back_left), tip[1] + ARROWHEAD_LENGTH * math.sin(back_left)),
        QPointF(tip[0] + ARROWHEAD_LENGTH * math.cos(back_right), tip[1] + ARROWHEAD_LENGTH * math.sin(back_right)),
    ])


def _polyline_path(points) -> QPainterPath:
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        path.lineTo(QPointF(*point))
    return path


def _trim_end(points, distance):
    """The polyline with its last `distance` pixels removed."""
    keep_length = path_length(points) - distance
    if keep_length <= 0:
        return [points[0], points[0]]
    trimmed = [points[0]]
    travelled = 0.0
    for a, b in zip(points, points[1:]):
        segment = math.dist(a, b)
        if travelled + segment >= keep_length:
            t = (keep_length - travelled) / segment
            trimmed.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            return trimmed
        trimmed.append(b)
        travelled += segment
    return trimmed
