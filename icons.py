"""
icons.py - Tool icons, drawn at runtime with the board's own renderer.
======================================================================

Each tool's icon is painted with the same functions that draw the field,
so the "Add X" icon is exactly what lands on the board and an arrow icon
uses the real arrow style. No image files to ship or keep in sync.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    2.0.0  2026-10-14  TCurrie11  Initial version.
"""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

from config import OFFENSE_COLOR, WHITE, PIECE_RADIUS
from editor import Tool
from entities import Annotation
from render import draw_annotation, draw_piece, piece_label_font

ICON_SIZE = 32
# Icons are drawn on a 2x canvas in board units so pieces keep their real
# proportions, then scaled down - this keeps them crisp on high-DPI screens.
CANVAS = 64
LIGHT = QColor(225, 228, 232)


def tool_icon(tool: Tool) -> QIcon:
    pixmap = QPixmap(CANVAS, CANVAS)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    _ICON_PAINTERS[tool](painter)
    painter.end()
    pixmap.setDevicePixelRatio(CANVAS / ICON_SIZE)
    return QIcon(pixmap)


def _paint_select(painter):
    pointer = QPolygonF([QPointF(x, y) for x, y in
                         [(18, 10), (18, 50), (28, 40), (35, 55), (42, 52), (35, 37), (48, 37)]])
    painter.setPen(QPen(QColor(30, 30, 30), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(LIGHT)
    painter.drawPolygon(pointer)


def _paint_piece(team):
    def paint(painter):
        scale = (CANVAS / 2 - 6) / (PIECE_RADIUS + 3)
        painter.translate(CANVAS / 2, CANVAS / 2)
        painter.scale(scale, scale)
        draw_piece(painter, team, (0, 0), piece_label_font())
    return paint


def _paint_line(kind):
    def paint(painter):
        curve = tuple((8 + t * 0.48, 50 - 36 * (t / 100) ** 0.6) for t in range(0, 101, 4))
        draw_annotation(painter, Annotation(kind, OFFENSE_COLOR, curve))
    return paint


def _paint_pick(painter):
    painter.translate(CANVAS / 2, CANVAS / 2 + 2)
    painter.scale(1.7, 1.7)
    draw_annotation(painter, Annotation('pick', OFFENSE_COLOR, ((0, 0),)))


def _paint_delete(painter):
    painter.setPen(QPen(QColor(*WHITE), 5, Qt.SolidLine, Qt.RoundCap))
    painter.setBrush(QColor(201, 74, 74))
    painter.drawEllipse(QPointF(32, 32), 22, 22)
    painter.drawLine(QPointF(23, 23), QPointF(41, 41))
    painter.drawLine(QPointF(41, 23), QPointF(23, 41))


_ICON_PAINTERS = {
    Tool.SELECT: _paint_select,
    Tool.ADD_OFFENSE: _paint_piece('X'),
    Tool.ADD_DEFENSE: _paint_piece('O'),
    Tool.ADD_BALL: _paint_piece('BALL'),
    Tool.ARROW: _paint_line('arrow'),
    Tool.PASS: _paint_line('pass'),
    Tool.PICK: _paint_pick,
    Tool.DELETE: _paint_delete,
}
