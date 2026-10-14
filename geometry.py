"""
geometry.py - Small, toolkit-free geometry and easing helpers.
==============================================================

Hit-testing against lines and polylines, and the ease-in-out curve used
when pieces glide between steps. Contains no drawing code, so it is shared
by the editor, the timeline and the smoother.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release (as draw_utils.py).
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    1.2.0  2026-10-14  TCurrie11  Moved freehand smoothing out to path_smoothing.py.
    2.0.0  2026-10-14  TCurrie11  Renamed from draw_utils.py; pygame drawing helpers replaced by QPainter in render.py.
"""
import math

Point = tuple[float, float]


def distance_to_segment(point: Point, start: Point, end: Point) -> float:
    """Shortest distance from `point` to the line segment start-end."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return math.dist(point, start)
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared
    t = max(0.0, min(1.0, t))
    return math.dist(point, (start[0] + t * dx, start[1] + t * dy))


def point_near_polyline(point: Point, polyline: list[Point], tolerance: float) -> bool:
    """True if `point` lies within `tolerance` of any segment of the polyline."""
    return any(distance_to_segment(point, a, b) <= tolerance
               for a, b in zip(polyline, polyline[1:]))


def smoothstep(t: float) -> float:
    """Ease-in-out curve: slow start, fast middle, slow finish. t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)
