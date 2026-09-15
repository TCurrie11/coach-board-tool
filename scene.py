"""Composes one frame (field + pieces + annotations), optionally rotated to
an arbitrary angle and scaled to fit, and provides the inverse transform so
mouse clicks on the rotated view can be mapped back to canvas-local
coordinates (the space pieces/annotations actually live in).
"""
import math
import pygame

from field import fit_field_rect, draw_field
from render import draw_piece, draw_annotation


def compose_frame(container_w, container_h, field_mode, rotation_deg,
                   pieces, piece_positions, annotations, piece_font,
                   bg_color, dragging_piece_id=None):
    layout = fit_field_rect((0, 0, container_w, container_h), field_mode)

    canvas = pygame.Surface((container_w, container_h), pygame.SRCALPHA)
    canvas.fill((0, 0, 0, 0))
    draw_field(canvas, layout)
    for a in annotations:
        draw_annotation(canvas, a)
    for p in pieces:
        pos = piece_positions.get(p.id, p.pos)
        draw_piece(canvas, p.team, pos, piece_font, selected=(p.id == dragging_piece_id))

    angle = rotation_deg % 360
    rotated = pygame.transform.rotate(canvas, angle) if abs(angle) > 0.01 or abs(angle - 360) > 0.01 else canvas
    if angle == 0:
        rotated = canvas

    rw, rh = rotated.get_size()
    scale = min(container_w / rw, container_h / rh, 1.0)
    if scale < 0.999:
        new_size = (max(1, int(rw * scale)), max(1, int(rh * scale)))
        rotated = pygame.transform.smoothscale(rotated, new_size)

    final = pygame.Surface((container_w, container_h))
    final.fill(bg_color)
    center = (container_w / 2, container_h / 2)
    dest_rect = rotated.get_rect(center=center)
    final.blit(rotated, dest_rect.topleft)

    transform = {'angle': angle, 'scale': scale, 'center': center}
    return final, transform


def screen_to_canvas(pos, container_origin, transform):
    """Inverse of the rotate+scale+recenter pipeline in compose_frame.
    Converts an absolute screen position into canvas-local coordinates."""
    cx, cy = transform['center']
    scale = transform['scale'] if transform['scale'] > 1e-6 else 1.0
    x = (pos[0] - container_origin[0] - cx) / scale
    y = (pos[1] - container_origin[1] - cy) / scale
    ang = math.radians(transform['angle'])
    s, c = math.sin(ang), math.cos(ang)
    rx = x * c - y * s
    ry = x * s + y * c
    return (cx + rx, cy + ry)
