"""Composes one frame (field + pieces + annotations) at a fixed internal
reference size, optionally rotated, then scales the *entire finished
picture* to fit whatever output size is requested. Doing it in that order -
compose first, scale the whole thing second - is what guarantees the field
and everything drawn on it always stay aligned, whether the output is the
live editor window or an exported video at a completely different size and
aspect ratio.

Also provides the inverse transform so mouse clicks on the (possibly
rotated and scaled) view can be mapped back to reference-space coordinates,
which is the space pieces/annotations actually store their positions in.
"""
import math
import pygame

from config import REFERENCE_W, REFERENCE_H
from field import fit_field_rect, draw_field
from render import draw_piece, draw_annotation


def compose_frame(output_w, output_h, field_mode, rotation_deg,
                   pieces, piece_positions, annotations, piece_font,
                   bg_color, dragging_piece_id=None):
    layout = fit_field_rect((0, 0, REFERENCE_W, REFERENCE_H), field_mode)

    canvas = pygame.Surface((REFERENCE_W, REFERENCE_H), pygame.SRCALPHA)
    canvas.fill((0, 0, 0, 0))
    draw_field(canvas, layout)
    for a in annotations:
        draw_annotation(canvas, a)
    for p in pieces:
        pos = piece_positions.get(p.id, p.pos)
        draw_piece(canvas, p.team, pos, piece_font, selected=(p.id == dragging_piece_id))

    angle = rotation_deg % 360
    rotated = pygame.transform.rotate(canvas, angle) if angle != 0 else canvas
    rw, rh = rotated.get_size()

    scale = min(output_w / rw, output_h / rh)
    if abs(scale - 1.0) > 0.001:
        new_size = (max(1, int(rw * scale)), max(1, int(rh * scale)))
        rotated = pygame.transform.smoothscale(rotated, new_size)

    final = pygame.Surface((output_w, output_h))
    final.fill(bg_color)
    out_center = (output_w / 2, output_h / 2)
    dest_rect = rotated.get_rect(center=out_center)
    final.blit(rotated, dest_rect.topleft)

    transform = {
        'angle': angle,
        'scale': scale,
        'ref_center': (REFERENCE_W / 2, REFERENCE_H / 2),
        'out_center': out_center,
    }
    return final, transform


def screen_to_canvas(pos, container_origin, transform):
    """Inverse of compose_frame's rotate+scale+recenter pipeline. Converts
    an absolute screen position into reference-space coordinates - the same
    space pieces/annotations store their positions in, regardless of what
    output size was actually rendered."""
    ref_cx, ref_cy = transform['ref_center']
    out_cx, out_cy = transform['out_center']
    scale = transform['scale'] if transform['scale'] > 1e-6 else 1.0
    x = (pos[0] - container_origin[0] - out_cx) / scale
    y = (pos[1] - container_origin[1] - out_cy) / scale
    ang = math.radians(transform['angle'])
    s, c = math.sin(ang), math.cos(ang)
    rx = x * c - y * s
    ry = x * s + y * c
    return (ref_cx + rx, ref_cy + ry)
