"""
render.py - Drawing routines for pieces and annotations.
========================================================

Pure drawing: given a surface and a piece/annotation, paint it. No
state and no layout logic - positions arrive already in canvas space.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    1.2.0  2026-10-14  TCurrie11  Arrowheads aim along the curve's last 14 px, not its final segment.
"""
import pygame
from config import (
    OFFENSE_COLOR, DEFENSE_COLOR, BALL_COLOR, WHITE, BLACK, YELLOW,
    PIECE_RADIUS, PICK_SIZE, BALL_RADIUS,
)
from draw_utils import draw_dashed_line, draw_arrowhead
from path_smoothing import point_at_distance_from_end

ARROWHEAD_LENGTH = 14


def draw_piece(surface, team, pos, font, selected=False):
    """Draw one player or the ball at `pos`, with a yellow ring if `selected`."""
    p = (int(pos[0]), int(pos[1]))
    if team == 'BALL':
        pygame.draw.circle(surface, BLACK, p, BALL_RADIUS + 2)
        pygame.draw.circle(surface, BALL_COLOR, p, BALL_RADIUS)
        if selected:
            pygame.draw.circle(surface, YELLOW, p, BALL_RADIUS + 6, 2)
        return
    color = OFFENSE_COLOR if team == 'X' else DEFENSE_COLOR
    pygame.draw.circle(surface, WHITE, p, PIECE_RADIUS + 3)
    pygame.draw.circle(surface, color, p, PIECE_RADIUS)
    label = font.render(team, True, WHITE)
    surface.blit(label, label.get_rect(center=p))
    if selected:
        pygame.draw.circle(surface, YELLOW, p, PIECE_RADIUS + 6, 2)


def draw_annotation(surface, ann):
    """Draw an arrow (solid), pass (dashed) or pick (triangle) annotation."""
    if ann.kind in ('arrow', 'pass'):
        pts = ann.points
        if len(pts) < 2:
            return
        if ann.kind == 'pass':
            for a, b in zip(pts, pts[1:]):
                draw_dashed_line(surface, ann.color, a, b, 3, 10, 7)
        else:
            if len(pts) == 2:
                pygame.draw.line(surface, ann.color, pts[0], pts[1], 3)
            else:
                pygame.draw.lines(surface, ann.color, False, pts, 3)
        aim_from = point_at_distance_from_end(pts, ARROWHEAD_LENGTH)
        draw_arrowhead(surface, ann.color, aim_from, pts[-1], length=ARROWHEAD_LENGTH)
    elif ann.kind == 'pick':
        p = ann.points[0]
        size = PICK_SIZE
        pts = [(p[0], p[1] - size), (p[0] - size, p[1] + size), (p[0] + size, p[1] + size)]
        pygame.draw.polygon(surface, ann.color, pts)
        pygame.draw.polygon(surface, WHITE, pts, 2)
