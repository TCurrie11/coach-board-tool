"""
draw_utils.py - Generic drawing and geometry helpers.
=====================================================

Dashed lines, arrowheads, hit-testing against line segments and easing.
Freehand smoothing lives in `path_smoothing`.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    1.2.0  2026-10-14  TCurrie11  Moved freehand smoothing out to path_smoothing.py.
"""
import math
import pygame


def draw_dashed_line(surface, color, start, end, width=2, dash_len=8, gap_len=6):
    """Draw a straight dashed line from `start` to `end`."""
    x1, y1 = start
    x2, y2 = end
    total = math.hypot(x2 - x1, y2 - y1)
    if total == 0:
        return
    dx, dy = (x2 - x1) / total, (y2 - y1) / total
    dist = 0.0
    draw_seg = True
    while dist < total:
        seg = min(dash_len if draw_seg else gap_len, total - dist)
        if draw_seg:
            sx, sy = x1 + dx * dist, y1 + dy * dist
            ex, ey = x1 + dx * (dist + seg), y1 + dy * (dist + seg)
            pygame.draw.line(surface, color, (sx, sy), (ex, ey), width)
        dist += seg
        draw_seg = not draw_seg


def draw_arrowhead(surface, color, p0, p1, length=14, spread_deg=28):
    """Draw a filled triangular arrowhead at `p1`, pointing in the direction p0 -> p1."""
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    a1 = ang + math.pi - math.radians(spread_deg)
    a2 = ang + math.pi + math.radians(spread_deg)
    pt1 = (p1[0] + length * math.cos(a1), p1[1] + length * math.sin(a1))
    pt2 = (p1[0] + length * math.cos(a2), p1[1] + length * math.sin(a2))
    pygame.draw.polygon(surface, color, [p1, pt1, pt2])


def point_near_segment(pos, a, b, tol=6):
    """Return True if `pos` lies within `tol` pixels of the line segment a-b."""
    px, py = pos
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return math.hypot(px - ax, py - ay) <= tol
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy) <= tol


def smoothstep(t):
    """Ease-in-out easing curve, t in [0,1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def point_near_polyline(pos, points, tol=7):
    """Return True if `pos` lies within `tol` pixels of any segment of the polyline."""
    for a, b in zip(points, points[1:]):
        if point_near_segment(pos, a, b, tol):
            return True
    return False
