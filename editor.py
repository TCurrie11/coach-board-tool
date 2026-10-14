"""
editor.py - Editing logic for a play, independent of any UI widgets.
====================================================================

`PlayEditor` holds everything about the play being edited - pieces, the
annotations drawn for the next step, the committed steps, the field
settings and the undo history - and implements what each tool does on
press / drag / release. All coordinates are in reference space.

Keeping this free of Qt widgets means the window code only has to forward
mouse events and display state, and the editing rules can be tested
directly without a screen.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    2.0.0  2026-10-14  TCurrie11  Extracted from the pygame App class in app.py (1.x).
"""
import math
from dataclasses import dataclass
from enum import Enum

from config import (
    OFFENSE_COLOR, DEFENSE_COLOR, PIECE_HIT_RADIUS, PICK_SIZE, ANNOTATION_HIT_TOLERANCE,
    FREEHAND_MIN_DRAG, FREEHAND_SAMPLE_SPACING, UNDO_LIMIT,
)
from entities import Annotation, Piece, set_counter_above
from geometry import point_near_polyline
from path_smoothing import path_length, smooth_freehand_path
from timeline import StepManager


class Tool(Enum):
    SELECT = 'select'
    ADD_OFFENSE = 'add_x'
    ADD_DEFENSE = 'add_o'
    ADD_BALL = 'add_ball'
    ARROW = 'arrow'
    PASS = 'pass'
    PICK = 'pick'
    DELETE = 'delete'

    @property
    def draws_freehand(self):
        return self in (Tool.ARROW, Tool.PASS)


TEAM_DRAW_COLORS = {'X': OFFENSE_COLOR, 'O': DEFENSE_COLOR}


@dataclass
class _UndoSnapshot:
    pieces: list
    pending_annotations: list


class PlayEditor:
    """The play being edited, plus what each tool does to it."""

    def __init__(self):
        self.tool = Tool.SELECT
        self.field_mode = 'half'          # 'half' or 'full'
        self.rotation_deg = 0.0
        self.draw_team = 'X'              # colour used when a line doesn't start on a piece
        self.pieces = []
        self.pending_annotations = []     # drawn since the last committed step
        self.steps = StepManager()
        self._undo_stack = []
        self.dragging_piece = None
        self.freehand_path = []           # raw mouse points of the line being drawn

    # ------------------------------------------------------------ queries --
    def piece_at(self, point):
        """Topmost piece under `point`, or None."""
        for piece in reversed(self.pieces):
            if math.dist(point, piece.pos) <= PIECE_HIT_RADIUS:
                return piece
        return None

    def ball(self):
        return next((p for p in self.pieces if p.team == 'BALL'), None)

    def color_for_line_starting_at(self, point):
        """Lines take the colour of the player they start on, otherwise the
        currently selected draw colour."""
        piece = self.piece_at(point)
        team = piece.team if piece is not None and piece.team in TEAM_DRAW_COLORS else self.draw_team
        return TEAM_DRAW_COLORS[team]

    def annotations_to_display(self):
        """Pending annotations plus the line currently being drawn, if any."""
        annotations = list(self.pending_annotations)
        if self.tool.draws_freehand and len(self.freehand_path) >= 2:
            annotations.append(Annotation(self.tool.value, self.color_for_line_starting_at(self.freehand_path[0]),
                                          tuple(self.freehand_path)))
        return annotations

    @property
    def can_undo_action(self):
        return bool(self._undo_stack)

    # --------------------------------------------------------- tool input --
    def set_tool(self, tool: Tool):
        self.tool = tool
        self.cancel_gesture()

    def cancel_gesture(self):
        self.dragging_piece = None
        self.freehand_path = []

    def press(self, point):
        """Mouse button pressed on the field at `point`."""
        if self.tool is Tool.SELECT:
            piece = self.piece_at(point)
            if piece is not None:
                self._remember_for_undo()
                self.dragging_piece = piece
        elif self.tool in (Tool.ADD_OFFENSE, Tool.ADD_DEFENSE):
            self._remember_for_undo()
            team = 'X' if self.tool is Tool.ADD_OFFENSE else 'O'
            self.pieces.append(Piece.create(team, point))
        elif self.tool is Tool.ADD_BALL:
            self._remember_for_undo()
            existing_ball = self.ball()
            if existing_ball is not None:
                existing_ball.pos = tuple(point)
            else:
                self.pieces.append(Piece.create('BALL', point))
        elif self.tool.draws_freehand:
            self.freehand_path = [tuple(point)]
        elif self.tool is Tool.PICK:
            self._remember_for_undo()
            self.pending_annotations.append(
                Annotation('pick', self.color_for_line_starting_at(point), (tuple(point),)))
        elif self.tool is Tool.DELETE:
            self._delete_at(point)

    def drag(self, point):
        """Mouse moved with the button held."""
        if self.dragging_piece is not None:
            self.dragging_piece.pos = tuple(point)
        elif self.tool.draws_freehand and self.freehand_path:
            if math.dist(point, self.freehand_path[-1]) >= FREEHAND_SAMPLE_SPACING:
                self.freehand_path.append(tuple(point))

    def release(self, point):
        """Mouse button released. Finishes a drag or a freehand line."""
        self.dragging_piece = None
        if self.tool.draws_freehand and self.freehand_path:
            self.freehand_path.append(tuple(point))
            self._finish_freehand_line(self.freehand_path)
            self.freehand_path = []

    def _finish_freehand_line(self, raw_path):
        if path_length(raw_path) <= FREEHAND_MIN_DRAG:
            return
        kind = self.tool.value
        start_piece = self.piece_at(raw_path[0])
        # Only movement arrows move a player; a pass is the ball's path.
        follows_piece = kind == 'arrow' and start_piece is not None and start_piece.team in TEAM_DRAW_COLORS
        self._remember_for_undo()
        self.pending_annotations.append(Annotation(
            kind, self.color_for_line_starting_at(raw_path[0]), tuple(smooth_freehand_path(raw_path)),
            persist=False, linked_piece_id=start_piece.id if follows_piece else None))

    def _delete_at(self, point):
        piece = self.piece_at(point)
        if piece is not None:
            self._remember_for_undo()
            self.pieces.remove(piece)
            return
        for annotation in reversed(self.pending_annotations):
            if self._annotation_contains(annotation, point):
                self._remember_for_undo()
                self.pending_annotations.remove(annotation)
                return

    @staticmethod
    def _annotation_contains(annotation, point):
        if annotation.kind == 'pick':
            return math.dist(point, annotation.points[0]) < PICK_SIZE + 6
        return point_near_polyline(point, annotation.points, ANNOTATION_HIT_TOLERANCE)

    # --------------------------------------------------------------- undo --
    def _remember_for_undo(self):
        snapshot = _UndoSnapshot([Piece(p.id, p.team, p.pos) for p in self.pieces],
                                 list(self.pending_annotations))
        self._undo_stack.append(snapshot)
        del self._undo_stack[:-UNDO_LIMIT]

    def undo_last_action(self):
        """Revert the most recent edit in the current (uncommitted) step.
        Returns False if there was nothing to undo."""
        if not self._undo_stack:
            return False
        snapshot = self._undo_stack.pop()
        self.pieces = snapshot.pieces
        self.pending_annotations = snapshot.pending_annotations
        self.cancel_gesture()
        return True

    # -------------------------------------------------------------- steps --
    def commit_step(self, move_seconds, hold_seconds):
        """Freeze current positions and drawn annotations into a new step.
        The first step has no glide-in, so its move time is always 0."""
        positions = {p.id: p.pos for p in self.pieces}
        move_seconds = move_seconds if self.steps.steps else 0.0
        self.steps.add_step(positions, self.pending_annotations, move_seconds, hold_seconds)
        self.pending_annotations = []
        self._undo_stack.clear()

    def remove_last_step(self):
        """Returns False if there were no steps."""
        if not self.steps.steps:
            return False
        self.steps.steps.pop()
        self._undo_stack.clear()
        return True

    def delete_step(self, index):
        self.steps.delete_step(index)

    def set_step_timing(self, index, move_seconds, hold_seconds):
        step = self.steps.steps[index]
        step.move_duration = move_seconds if index > 0 else 0.0
        step.hold_duration = hold_seconds

    # ------------------------------------------------------- whole play --
    def replace_play(self, pieces, steps, field_mode, rotation_deg):
        """Swap in a loaded play, discarding any unsaved edits."""
        self.pieces = pieces
        self.steps.steps = steps
        self.field_mode = field_mode
        self.rotation_deg = rotation_deg
        self.pending_annotations = []
        self._undo_stack.clear()
        self.cancel_gesture()
        if pieces:
            set_counter_above(max(p.id for p in pieces))

    def new_play(self):
        self.replace_play([], [], 'half', 0.0)
