"""
scene.py - Composes one complete frame: field, annotations and pieces.
======================================================================

Pieces, annotations and the field are all positioned in one fixed
reference space (REFERENCE_W x REFERENCE_H). `view_transform` maps that
space onto any output size - the live editor widget or an exported video -
by rotating around its centre and scaling uniformly to fit. Because the
whole scene goes through the same transform, the field and everything on
it always stay aligned at every size, angle and aspect ratio.

The inverse of the same transform maps mouse clicks back into reference
space, which is where pieces and annotations store their positions.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.0.1  2026-09-15  TCurrie11  Editor and export now share one reference canvas so pieces stay aligned with the field.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    2.0.0  2026-10-14  TCurrie11  Vector rendering through a QTransform instead of rotating/scaling a bitmap; stays sharp at any size.
"""
import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter, QTransform

from config import REFERENCE_W, REFERENCE_H, BG_OUTSIDE_FIELD
from field import fit_field_rect, draw_field
from render import draw_piece, draw_annotation


def view_transform(output_w, output_h, rotation_deg) -> QTransform:
    """Reference space -> output space: rotate the scene about its centre,
    then scale it as large as fits inside the output without cropping.

    Positive angles turn the field anticlockwise on screen (the same
    direction as 1.x, so saved plays look identical)."""
    angle = math.radians(rotation_deg % 360)
    rotated_w = abs(REFERENCE_W * math.cos(angle)) + abs(REFERENCE_H * math.sin(angle))
    rotated_h = abs(REFERENCE_W * math.sin(angle)) + abs(REFERENCE_H * math.cos(angle))
    scale = min(output_w / rotated_w, output_h / rotated_h)

    transform = QTransform()
    transform.translate(output_w / 2, output_h / 2)
    transform.scale(scale, scale)
    transform.rotate(-(rotation_deg % 360))
    transform.translate(-REFERENCE_W / 2, -REFERENCE_H / 2)
    return transform


def output_to_reference(point, output_w, output_h, rotation_deg):
    """Map a point in output space (e.g. a mouse click) back to reference space."""
    inverse, _ = view_transform(output_w, output_h, rotation_deg).inverted()
    mapped = inverse.map(QPointF(*point))
    return (mapped.x(), mapped.y())


def paint_frame(painter: QPainter, output_w, output_h, field_mode, rotation_deg,
                pieces, piece_positions, annotations, label_font, highlighted_piece_id=None):
    """Paint one full frame onto `painter`, filling output_w x output_h.

    `piece_positions` maps piece id -> position for this frame; a piece
    missing from it is drawn at its own live position."""
    painter.save()
    painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    painter.fillRect(0, 0, output_w, output_h, QColor(*BG_OUTSIDE_FIELD))
    painter.setTransform(view_transform(output_w, output_h, rotation_deg), combine=True)

    layout = fit_field_rect((0, 0, REFERENCE_W, REFERENCE_H), field_mode)
    draw_field(painter, layout)
    for annotation in annotations:
        draw_annotation(painter, annotation)
    for piece in pieces:
        position = piece_positions.get(piece.id, piece.pos)
        draw_piece(painter, piece.team, position, label_font,
                   selected=(piece.id == highlighted_piece_id),
                   label_rotation_deg=rotation_deg)  # undo the field's turn so letters read upright
    painter.restore()


def render_frame_image(output_w, output_h, field_mode, rotation_deg,
                       pieces, piece_positions, annotations, label_font) -> QImage:
    """Render one frame off-screen (used for video export and tests)."""
    image = QImage(output_w, output_h, QImage.Format_RGB32)
    painter = QPainter(image)
    try:
        paint_frame(painter, output_w, output_h, field_mode, rotation_deg,
                    pieces, piece_positions, annotations, label_font)
    finally:
        painter.end()
    return image
