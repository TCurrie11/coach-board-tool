"""
board_view.py - The interactive field widget.
=============================================

Paints the current play and forwards mouse input to the `PlayEditor`,
converting widget coordinates into reference space first. Also plays an
in-place animated preview of the timeline. Resizes freely: the scene
transform rescales everything to fit.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    2.0.0  2026-10-14  TCurrie11  Initial version; replaces the pygame drawing/event loop from app.py (1.x).
"""
from PySide6.QtCore import QElapsedTimer, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from config import PREVIEW_FPS, REFERENCE_W, REFERENCE_H
from editor import PlayEditor, Tool
from render import piece_label_font
from scene import output_to_reference, paint_frame
from timeline import generate_timeline_frames

TOOL_CURSORS = {
    Tool.SELECT: Qt.OpenHandCursor,
    Tool.ADD_OFFENSE: Qt.CrossCursor,
    Tool.ADD_DEFENSE: Qt.CrossCursor,
    Tool.ADD_BALL: Qt.CrossCursor,
    Tool.ARROW: Qt.CrossCursor,
    Tool.PASS: Qt.CrossCursor,
    Tool.PICK: Qt.CrossCursor,
    Tool.DELETE: Qt.PointingHandCursor,
}
PREVIEW_BANNER = "Previewing  -  click or press Esc to stop"


class BoardView(QWidget):
    """Draws the play and turns mouse gestures into editor actions."""

    edited = Signal()              # the play changed because of a mouse gesture
    preview_finished = Signal()

    def __init__(self, editor: PlayEditor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self._label_font = piece_label_font()
        self._hovered_piece_id = None

        self._preview_frames = []
        self._preview_index = 0
        self._preview_clock = QElapsedTimer()
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(1000 // PREVIEW_FPS)
        self._preview_timer.timeout.connect(self._advance_preview)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(480, 400)
        self.refresh_cursor()

    def sizeHint(self):
        return QSize(REFERENCE_W, REFERENCE_H)

    @property
    def is_previewing(self):
        return self._preview_timer.isActive()

    # ------------------------------------------------------------ preview --
    def start_preview(self):
        """Animate the committed steps in place. Returns False if there are none."""
        if not self.editor.steps.steps:
            return False
        self._preview_frames = generate_timeline_frames(self.editor.steps.steps, fps=PREVIEW_FPS)
        self._preview_index = 0
        self._preview_clock.start()
        self._preview_timer.start()
        self.editor.cancel_gesture()
        self.update()
        return True

    def stop_preview(self):
        if self.is_previewing:
            self._preview_timer.stop()
            self.update()
            self.preview_finished.emit()

    def _advance_preview(self):
        frame_index = int(self._preview_clock.elapsed() / 1000 * PREVIEW_FPS)
        if frame_index >= len(self._preview_frames):
            self.stop_preview()
            return
        self._preview_index = frame_index
        self.update()

    # ----------------------------------------------------------- painting --
    def paintEvent(self, _event):
        painter = QPainter(self)
        if self.is_previewing:
            positions, annotations = self._preview_frames[self._preview_index]
            highlighted_id = None
        else:
            positions = {p.id: p.pos for p in self.editor.pieces}
            annotations = self.editor.annotations_to_display()
            dragging = self.editor.dragging_piece
            highlighted_id = dragging.id if dragging is not None else self._hovered_piece_id

        paint_frame(painter, self.width(), self.height(), self.editor.field_mode,
                    self.editor.rotation_deg, self.editor.pieces, positions, annotations,
                    self._label_font, highlighted_piece_id=highlighted_id)

        if self.is_previewing:
            self._paint_banner(painter, PREVIEW_BANNER)
        painter.end()

    def _paint_banner(self, painter, text):
        font = QFont()
        font.setPixelSize(14)
        font.setBold(True)
        painter.setFont(font)
        banner = QRectF(0, self.height() - 40, self.width(), 40)
        painter.fillRect(banner, QColor(0, 0, 0, 150))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(banner, Qt.AlignCenter, text)

    # -------------------------------------------------------------- input --
    def _to_reference(self, event):
        position = event.position()
        return output_to_reference((position.x(), position.y()), self.width(), self.height(),
                                   self.editor.rotation_deg)

    def mousePressEvent(self, event):
        if self.is_previewing:
            self.stop_preview()
            return
        if event.button() != Qt.LeftButton:
            return
        self.editor.press(self._to_reference(event))
        if self.editor.dragging_piece is not None:
            self.setCursor(Qt.ClosedHandCursor)
        self.update()
        self.edited.emit()

    def mouseMoveEvent(self, event):
        if self.is_previewing:
            return
        point = self._to_reference(event)
        if event.buttons() & Qt.LeftButton:
            self.editor.drag(point)
        else:
            self._update_hover(point)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.is_previewing or event.button() != Qt.LeftButton:
            return
        self.editor.release(self._to_reference(event))
        self.refresh_cursor()
        self.update()
        self.edited.emit()

    def leaveEvent(self, _event):
        self._hovered_piece_id = None
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.is_previewing:
            self.stop_preview()
        else:
            super().keyPressEvent(event)

    def _update_hover(self, point):
        """Highlight the piece under the cursor when the tool acts on pieces."""
        acts_on_pieces = self.editor.tool in (Tool.SELECT, Tool.DELETE)
        piece = self.editor.piece_at(point) if acts_on_pieces else None
        self._hovered_piece_id = piece.id if piece is not None else None

    def refresh_cursor(self):
        self.setCursor(TOOL_CURSORS[self.editor.tool])
