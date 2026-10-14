"""
app.py - Main application window: tool state, mouse handling and the sidebar UI.
================================================================================

Owns the editor loop. Every frame it composes the field + pieces +
annotations via `scene.compose_frame`, draws the sidebar, and routes mouse
and keyboard input to whichever tool is active (select, add piece, arrow,
pass, pick, delete). Steps, preview, export and save/load are all driven
from here.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.0.1  2026-09-15  TCurrie11  Editor and export now share one reference canvas so pieces stay aligned with the field.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    1.2.0  2026-10-14  TCurrie11  Arrows and passes use the new path_smoothing pipeline on release.
"""
import math
import os
import sys

import pygame

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, SIDEBAR_WIDTH, FIELD_MARGIN, FPS, EXPORT_FPS,
    EXPORT_WIDTH, EXPORT_HEIGHT, PANEL_BG, PANEL_TEXT, WHITE, BG_OUTSIDE_FIELD,
    OFFENSE_COLOR, DEFENSE_COLOR, PIECE_RADIUS, PICK_SIZE,
    EXPORTS_DIR, SAVES_DIR, FREEHAND_MIN_DRAG,
)
from ui_widgets import Button, TextInput, Layout
from entities import Piece, Annotation, set_counter_above
from draw_utils import point_near_polyline
from path_smoothing import smooth_freehand_path
from timeline import StepManager, generate_timeline_frames
from exporter import export_mp4, export_gif
from scene import compose_frame, screen_to_canvas
import persistence

APP_TITLE = "Coach Board Tool"


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(APP_TITLE)
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("arial", 13)
        self.font_tiny = pygame.font.SysFont("arial", 11)
        self.font_bold = pygame.font.SysFont("arial", 16, bold=True)
        self.piece_font = pygame.font.SysFont("arial", 18, bold=True)

        self.mode = 'select'          # select, add_x, add_o, add_ball, arrow, pass, pick, delete
        self.field_mode = 'half'      # half, full
        self.active_team = 'X'        # fallback draw color when not starting on a piece
        self.rotation_deg = 0.0

        self.pieces = []
        self.pending_annotations = []
        self.steps = StepManager()

        self.dragging_piece = None
        self.freehand_path = []       # raw points captured while drawing an arrow/pass

        self.action_stack = []        # per-frame undo (piece/annotation snapshots)

        self.selected_step_index = None
        self.step_scroll = 0

        self.previewing = False
        self.preview_frames = []
        self.preview_index = 0
        self.preview_timer = 0.0

        self.container_origin = (FIELD_MARGIN, FIELD_MARGIN)
        _cw, _ch = self._container_wh()
        self.last_transform = {'angle': 0.0, 'scale': 1.0,
                                'ref_center': (_cw / 2, _ch / 2),
                                'out_center': (_cw / 2, _ch / 2)}

        self.status_message = "Welcome! Use 'Add X' / 'Add O' to place players, then draw and hit Add Step."

        self.buttons = []
        self.static_labels = []
        self._build_ui()

    # ---------------------------------------------------------- UI build --
    def _container_wh(self):
        return (WINDOW_WIDTH - SIDEBAR_WIDTH - 2 * FIELD_MARGIN, WINDOW_HEIGHT - 2 * FIELD_MARGIN)

    def _build_ui(self):
        sx = WINDOW_WIDTH - SIDEBAR_WIDTH + 15
        sw = SIDEBAR_WIDTH - 30
        self.buttons = []
        self.static_labels = []
        lay = Layout(sx, 52, sw)

        def label(text, h=13):
            r = lay.row(h, gap=1)
            self.static_labels.append((text, r))

        r1, r2 = lay.split(26, 2)
        self.buttons.append(Button(r1, "Half field", lambda: self.set_field_mode('half'),
                                    lambda: self.field_mode == 'half'))
        self.buttons.append(Button(r2, "Full field", lambda: self.set_field_mode('full'),
                                    lambda: self.field_mode == 'full'))

        r1, r2 = lay.split(26, 2)
        self.buttons.append(Button(r1, "Draw: Red (X)", lambda: self.set_active_team('X'),
                                    lambda: self.active_team == 'X'))
        self.buttons.append(Button(r2, "Draw: Blue (O)", lambda: self.set_active_team('O'),
                                    lambda: self.active_team == 'O'))

        tool_defs = [
            ('select', 'Select / Move'), ('add_x', 'Add X (offense)'),
            ('add_o', 'Add O (defense)'), ('add_ball', 'Add ball'),
            ('arrow', 'Arrow (move)'), ('pass', 'Dotted (pass)'),
            ('pick', 'Triangle (pick)'), ('delete', 'Delete'),
        ]
        for i in range(0, len(tool_defs), 2):
            (m1, l1), (m2, l2) = tool_defs[i:i + 2]
            c1, c2 = lay.split(26, 2)
            self.buttons.append(Button(c1, l1, (lambda m=m1: self.set_mode(m)), (lambda m=m1: self.mode == m)))
            self.buttons.append(Button(c2, l2, (lambda m=m2: self.set_mode(m)), (lambda m=m2: self.mode == m)))

        label("Rotate field")
        presets = lay.split(24, 4)
        for rect, deg in zip(presets, (0, 90, 180, 270)):
            self.buttons.append(Button(rect, f"{deg}\u00b0", (lambda d=deg: self.set_rotation(d)),
                                        (lambda d=deg: abs(self.rotation_deg % 360 - d) < 0.01)))
        rot_row = lay.row(24)
        self.rotation_input = TextInput(rot_row, "0", numeric=True)

        mlbl_row = lay.row(12, gap=1)
        m_lbl_rect = pygame.Rect(mlbl_row.x, mlbl_row.y, mlbl_row.w // 2, 12)
        h_lbl_rect = pygame.Rect(mlbl_row.x + mlbl_row.w // 2, mlbl_row.y, mlbl_row.w // 2, 12)
        self.static_labels.append(("Move (s)", m_lbl_rect))
        self.static_labels.append(("Hold (s)", h_lbl_rect))
        mrow1, mrow2 = lay.split(24, 2)
        self.move_input = TextInput(mrow1, "1.0")
        self.hold_input = TextInput(mrow2, "1.0")

        r = lay.row(28)
        self.buttons.append(Button(r, "Add Step", self.add_step))
        c1, c2 = lay.split(24, 2)
        self.buttons.append(Button(c1, "Undo last action", self.undo_action))
        self.buttons.append(Button(c2, "Undo last step", self.undo_last_step))
        r = lay.row(22)
        self.buttons.append(Button(r, "Update selected step timing", self.update_selected_step))

        label("Steps")
        self.steps_list_top = lay.y
        self.steps_list_height = 118
        lay.space(self.steps_list_height + 6)

        r = lay.row(28)
        self.buttons.append(Button(r, "Preview", self.start_preview))
        c1, c2 = lay.split(24, 2)
        self.buttons.append(Button(c1, "Export MP4", lambda: self.export_video('mp4')))
        self.buttons.append(Button(c2, "Export GIF", lambda: self.export_video('gif')))

        label("File name (no extension)")
        fr = lay.row(22)
        self.filename_input = TextInput(fr, "my_play", numeric=False)
        c1, c2 = lay.split(24, 2)
        self.buttons.append(Button(c1, "Save play", self.save_play))
        self.buttons.append(Button(c2, "Load play", self.load_play))

        self.status_area_top = lay.y + 4

    # -------------------------------------------------------------- state --
    def set_mode(self, m):
        self.mode = m
        self.freehand_path = []

    def set_field_mode(self, m):
        self.field_mode = m

    def set_active_team(self, t):
        self.active_team = t

    def set_rotation(self, deg):
        self.rotation_deg = float(deg)
        self.rotation_input.text = str(int(deg))

    def field_container_rect(self):
        w, h = self._container_wh()
        return (FIELD_MARGIN, FIELD_MARGIN, w, h)

    # -------------------------------------------------------------- run --
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)
            if self.previewing:
                self.update_preview(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()
        sys.exit(0)

    # ------------------------------------------------------------- events --
    def handle_event(self, event):
        if self.previewing:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.previewing = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.previewing = False
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.on_mouse_down(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self.in_sidebar(event.pos):
                self.step_scroll = max(0, self.step_scroll + (-20 if event.button == 4 else 20))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.on_mouse_up(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self.on_mouse_move(event.pos)
        elif event.type == pygame.KEYDOWN:
            self.move_input.handle_key(event)
            self.hold_input.handle_key(event)
            self.filename_input.handle_key(event)
            self.rotation_input.handle_key(event)

        self.rotation_deg = self.rotation_input.value(self.rotation_deg)

    def in_sidebar(self, pos):
        return pos[0] >= WINDOW_WIDTH - SIDEBAR_WIDTH

    def to_canvas(self, pos):
        return screen_to_canvas(pos, self.container_origin, self.last_transform)

    def on_mouse_down(self, pos):
        if self.in_sidebar(pos):
            for b in self.buttons:
                if b.handle_click(pos):
                    return
            self.move_input.handle_click(pos)
            self.hold_input.handle_click(pos)
            self.filename_input.handle_click(pos)
            self.rotation_input.handle_click(pos)
            self.handle_step_row_click(pos)
            return

        self.move_input.focused = False
        self.hold_input.focused = False
        self.filename_input.focused = False
        self.rotation_input.focused = False

        cpos = self.to_canvas(pos)

        if self.mode == 'select':
            hit = self.piece_at(cpos)
            if hit is not None:
                self._push_undo()
                self.dragging_piece = hit
        elif self.mode in ('add_x', 'add_o'):
            team = 'X' if self.mode == 'add_x' else 'O'
            self._push_undo()
            self.pieces.append(Piece.create(team, cpos))
        elif self.mode == 'add_ball':
            self._push_undo()
            ball = self.get_ball()
            if ball is not None:
                ball.pos = cpos
            else:
                self.pieces.append(Piece.create('BALL', cpos))
        elif self.mode in ('arrow', 'pass'):
            self.freehand_path = [cpos]
        elif self.mode == 'pick':
            self._push_undo()
            color = self.color_for_point(cpos)
            self.pending_annotations.append(Annotation('pick', color, (cpos,), False))
        elif self.mode == 'delete':
            self.try_delete_at(cpos)

    def on_mouse_move(self, pos):
        cpos = self.to_canvas(pos)
        if self.dragging_piece is not None:
            self.dragging_piece.pos = cpos
        if self.mode in ('arrow', 'pass') and self.freehand_path:
            last = self.freehand_path[-1]
            if math.hypot(cpos[0] - last[0], cpos[1] - last[1]) >= 3:
                self.freehand_path.append(cpos)

    def on_mouse_up(self, pos):
        if self.dragging_piece is not None:
            self.dragging_piece = None
        if self.mode in ('arrow', 'pass') and self.freehand_path:
            cpos = self.to_canvas(pos)
            self.freehand_path.append(cpos)
            path = self.freehand_path
            total_len = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))
            if total_len > FREEHAND_MIN_DRAG:
                smoothed = smooth_freehand_path(path)
                color = self.color_for_point(path[0])
                kind = 'pass' if self.mode == 'pass' else 'arrow'
                linked_id = None
                if kind == 'arrow':
                    hit = self.piece_at(path[0])
                    if hit is not None and hit.team in ('X', 'O'):
                        linked_id = hit.id
                self._push_undo()
                self.pending_annotations.append(
                    Annotation(kind, color, tuple(smoothed), False, linked_piece_id=linked_id))
            self.freehand_path = []

    def color_for_point(self, pos):
        hit = self.piece_at(pos)
        if hit is not None and hit.team in ('X', 'O'):
            return OFFENSE_COLOR if hit.team == 'X' else DEFENSE_COLOR
        return OFFENSE_COLOR if self.active_team == 'X' else DEFENSE_COLOR

    def piece_at(self, pos):
        for p in reversed(self.pieces):
            if math.hypot(pos[0] - p.pos[0], pos[1] - p.pos[1]) <= PIECE_RADIUS + 4:
                return p
        return None

    def get_ball(self):
        for p in self.pieces:
            if p.team == 'BALL':
                return p
        return None

    def try_delete_at(self, pos):
        p = self.piece_at(pos)
        if p is not None:
            self._push_undo()
            self.pieces.remove(p)
            return
        for a in list(self.pending_annotations):
            if self._annotation_hit(a, pos):
                self._push_undo()
                self.pending_annotations.remove(a)
                return

    def _annotation_hit(self, a, pos):
        if a.kind == 'pick':
            return math.hypot(pos[0] - a.points[0][0], pos[1] - a.points[0][1]) < PICK_SIZE + 6
        return point_near_polyline(pos, a.points, tol=7)

    # --------------------------------------------------------- undo (frame) --
    def _push_undo(self):
        snapshot = ([Piece(p.id, p.team, p.pos) for p in self.pieces], list(self.pending_annotations))
        self.action_stack.append(snapshot)
        if len(self.action_stack) > 50:
            self.action_stack.pop(0)

    def undo_action(self):
        if not self.action_stack:
            self.status_message = "Nothing to undo in this frame."
            return
        pieces_snap, ann_snap = self.action_stack.pop()
        self.pieces = pieces_snap
        self.pending_annotations = ann_snap
        self.dragging_piece = None
        self.freehand_path = []
        self.status_message = "Undid last action."

    # ------------------------------------------------------------- steps --
    def add_step(self):
        positions = {p.id: p.pos for p in self.pieces}
        move_dur = self.move_input.value(1.0, min_value=0.05) if self.steps.steps else 0.0
        hold_dur = self.hold_input.value(1.0, min_value=0.05)
        self.steps.add_step(positions, self.pending_annotations, move_dur, hold_dur)
        self.pending_annotations = []
        self.action_stack = []
        self.status_message = f"Step {len(self.steps.steps)} added."

    def undo_last_step(self):
        if self.steps.steps:
            self.steps.steps.pop()
            self.action_stack = []
            self.status_message = "Removed last step."

    def handle_step_row_click(self, pos):
        row_h = 22
        top = self.steps_list_top - self.step_scroll
        x = WINDOW_WIDTH - SIDEBAR_WIDTH + 15
        for i, step in enumerate(self.steps.steps):
            row_rect = pygame.Rect(x, top + i * row_h, SIDEBAR_WIDTH - 60, row_h - 3)
            del_rect = pygame.Rect(row_rect.right + 4, row_rect.y, 20, row_rect.h)
            if del_rect.collidepoint(pos):
                self.steps.delete_step(i)
                if self.selected_step_index == i:
                    self.selected_step_index = None
                return
            if row_rect.collidepoint(pos):
                self.selected_step_index = i
                self.move_input.text = f"{step.move_duration:.2f}"
                self.hold_input.text = f"{step.hold_duration:.2f}"
                return

    def update_selected_step(self):
        if self.selected_step_index is None:
            self.status_message = "Click a step in the list first."
            return
        step = self.steps.steps[self.selected_step_index]
        step.move_duration = self.move_input.value(step.move_duration, min_value=0.05)
        step.hold_duration = self.hold_input.value(step.hold_duration, min_value=0.05)
        self.status_message = f"Updated timing for step {self.selected_step_index + 1}."

    # ------------------------------------------------------------ preview --
    def start_preview(self):
        if not self.steps.steps:
            self.status_message = "Add at least one step first."
            return
        self.preview_frames = generate_timeline_frames(self.steps.steps, fps=FPS)
        self.preview_index = 0
        self.preview_timer = 0.0
        self.previewing = True

    def update_preview(self, dt):
        self.preview_timer += dt
        idx = int(self.preview_timer * FPS)
        if idx >= len(self.preview_frames):
            self.previewing = False
            return
        self.preview_index = idx

    # ------------------------------------------------------------- export --
    def export_video(self, fmt):
        if not self.steps.steps:
            self.status_message = "Add at least one step first."
            return
        self.status_message = "Rendering... this may take a moment."
        self.draw()
        pygame.display.flip()

        frames_data = generate_timeline_frames(self.steps.steps, fps=EXPORT_FPS)
        rendered = []
        for positions, annotations in frames_data:
            frame_surface, _ = compose_frame(
                EXPORT_WIDTH, EXPORT_HEIGHT, self.field_mode, self.rotation_deg,
                self.pieces, positions, annotations, self.piece_font, BG_OUTSIDE_FIELD,
            )
            rendered.append(frame_surface)

        os.makedirs(EXPORTS_DIR, exist_ok=True)
        name = self.filename_input.text.strip() or "my_play"
        path = os.path.join(EXPORTS_DIR, f"{name}.{fmt}")
        try:
            if fmt == 'mp4':
                export_mp4(rendered, path, fps=EXPORT_FPS)
            else:
                export_gif(rendered, path, fps=EXPORT_FPS)
            self.status_message = f"Exported {len(rendered)} frames to {path}"
        except Exception as e:
            self.status_message = f"Export failed: {e}"

    # ---------------------------------------------------------- persistence --
    def save_play(self):
        os.makedirs(SAVES_DIR, exist_ok=True)
        name = self.filename_input.text.strip() or "my_play"
        path = os.path.join(SAVES_DIR, f"{name}.json")
        persistence.save_play(path, self.pieces, self.steps, self.field_mode, self.rotation_deg)
        self.status_message = f"Saved to {path}"

    def load_play(self):
        name = self.filename_input.text.strip() or "my_play"
        path = os.path.join(SAVES_DIR, f"{name}.json")
        try:
            pieces, steps, field_mode, rotation_deg = persistence.load_play(path)
            self.pieces = pieces
            self.steps.steps = steps
            self.field_mode = field_mode
            self.rotation_deg = rotation_deg
            self.rotation_input.text = str(rotation_deg)
            self.pending_annotations = []
            self.action_stack = []
            self.selected_step_index = None
            if pieces:
                set_counter_above(max(p.id for p in pieces))
            self.status_message = f"Loaded {path}"
        except FileNotFoundError:
            self.status_message = f"No file named {path}"
        except Exception as e:
            self.status_message = f"Load failed: {e}"

    # ---------------------------------------------------------------- draw --
    def draw(self):
        self.screen.fill(BG_OUTSIDE_FIELD)
        container_w, container_h = self._container_wh()

        if self.previewing and self.preview_frames:
            positions, annotations = self.preview_frames[self.preview_index]
            final, transform = compose_frame(container_w, container_h, self.field_mode, self.rotation_deg,
                                              self.pieces, positions, annotations, self.piece_font,
                                              BG_OUTSIDE_FIELD)
            self.last_transform = transform
            self.screen.blit(final, self.container_origin)
            hint = self.font_bold.render("Previewing - click or press Esc to stop", True, WHITE)
            self.screen.blit(hint, (20, WINDOW_HEIGHT - 34))
        else:
            positions = {p.id: p.pos for p in self.pieces}
            annotations = list(self.pending_annotations)
            if self.mode in ('arrow', 'pass') and len(self.freehand_path) >= 2:
                color = self.color_for_point(self.freehand_path[0])
                kind = 'pass' if self.mode == 'pass' else 'arrow'
                annotations.append(Annotation(kind, color, tuple(self.freehand_path), False))
            dragging_id = self.dragging_piece.id if self.dragging_piece is not None else None
            final, transform = compose_frame(container_w, container_h, self.field_mode, self.rotation_deg,
                                              self.pieces, positions, annotations, self.piece_font,
                                              BG_OUTSIDE_FIELD, dragging_piece_id=dragging_id)
            self.last_transform = transform
            self.screen.blit(final, self.container_origin)
            self.draw_sidebar()

    def draw_sidebar(self):
        rect = pygame.Rect(WINDOW_WIDTH - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, PANEL_BG, rect)
        title = self.font_bold.render(APP_TITLE, True, WHITE)
        self.screen.blit(title, (WINDOW_WIDTH - SIDEBAR_WIDTH + 15, 10))
        mode_txt = self.font_small.render(f"Tool: {self.mode}", True, (170, 200, 255))
        self.screen.blit(mode_txt, (WINDOW_WIDTH - SIDEBAR_WIDTH + 15, 30))

        for text, r in self.static_labels:
            txt = self.font_tiny.render(text, True, PANEL_TEXT)
            self.screen.blit(txt, (r.x, r.y))

        for b in self.buttons:
            b.draw(self.screen, self.font_small)
        self.move_input.draw(self.screen, self.font_small)
        self.hold_input.draw(self.screen, self.font_small)
        self.filename_input.draw(self.screen, self.font_small)
        self.rotation_input.draw(self.screen, self.font_small)

        self.draw_steps_list()

        status_rect = pygame.Rect(WINDOW_WIDTH - SIDEBAR_WIDTH + 15, self.status_area_top,
                                   SIDEBAR_WIDTH - 30, WINDOW_HEIGHT - self.status_area_top - 8)
        self._draw_wrapped_text(self.status_message, status_rect, self.font_small, PANEL_TEXT)

    def draw_steps_list(self):
        x = WINDOW_WIDTH - SIDEBAR_WIDTH + 15
        clip_rect = pygame.Rect(x, self.steps_list_top, SIDEBAR_WIDTH - 30, self.steps_list_height)
        pygame.draw.rect(self.screen, (26, 26, 28), clip_rect)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(clip_rect)

        row_h = 22
        top = self.steps_list_top - self.step_scroll
        for i, step in enumerate(self.steps.steps):
            row_rect = pygame.Rect(x, top + i * row_h, SIDEBAR_WIDTH - 60, row_h - 3)
            if row_rect.bottom < self.steps_list_top or row_rect.top > self.steps_list_top + self.steps_list_height:
                continue
            bg = (60, 60, 90) if i == self.selected_step_index else (40, 40, 44)
            pygame.draw.rect(self.screen, bg, row_rect, border_radius=3)
            lbl = f"Step {i + 1}  mv {step.move_duration:.1f}s  hd {step.hold_duration:.1f}s"
            txt = self.font_tiny.render(lbl, True, PANEL_TEXT)
            self.screen.blit(txt, (row_rect.x + 4, row_rect.y + 4))
            del_rect = pygame.Rect(row_rect.right + 4, row_rect.y, 20, row_rect.h)
            pygame.draw.rect(self.screen, (90, 40, 40), del_rect, border_radius=3)
            xtxt = self.font_tiny.render("x", True, WHITE)
            self.screen.blit(xtxt, xtxt.get_rect(center=del_rect.center))

        self.screen.set_clip(old_clip)
        if not self.steps.steps:
            empty = self.font_small.render("No steps yet.", True, (150, 150, 150))
            self.screen.blit(empty, (x, self.steps_list_top + 4))

    def _draw_wrapped_text(self, text, rect, font, color):
        words = text.split(' ')
        lines = []
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if font.size(trial)[0] > rect.w:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        yy = rect.y
        for line in lines:
            txt = font.render(line, True, color)
            self.screen.blit(txt, (rect.x, yy))
            yy += font.get_height() + 2
