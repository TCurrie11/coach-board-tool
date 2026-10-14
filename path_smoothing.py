"""
path_smoothing.py - Turns a shaky freehand mouse path into a clean curve.
=========================================================================

When a coach drags out an arrow, the mouse reports a dense trail of points
that carries small 1-3 px wobbles from the hand and the sensor. This module
removes those wobbles while keeping the shape the coach actually meant.

Pipeline (`smooth_freehand_path`):

    1. Resample      Re-space the raw points evenly along the path, so later
                     steps behave the same however fast the mouse moved.
    2. Denoise       Moving-average each point with its neighbours. Removes
                     high-frequency jitter; the endpoints are pinned.
    3. Simplify      Ramer-Douglas-Peucker keeps only the points needed to
                     describe the intended shape. A nearly straight drag
                     collapses to a perfectly straight line.
    4. Fit curve     Centripetal Catmull-Rom spline through the kept points.
                     The centripetal variant never overshoots or forms small
                     loops at tight bends, unlike the uniform variant.
    5. Resample      Even spacing again, so dashed passes look regular and
                     pieces gliding along the arrow move at a steady speed.

The module is pure geometry (no drawing library), so it is easy to unit-test
and is independent of the UI toolkit.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.2.0  2026-10-14  TCurrie11  Initial version; replaces the old jitter-preserving smoother.
    2.0.0  2026-10-14  TCurrie11  distance_to_segment moved to geometry.py.
"""
import math

from geometry import Point, distance_to_segment

DEFAULT_SAMPLE_SPACING = 4.0      # px between points while denoising
DEFAULT_NOISE_WINDOW = 7          # points averaged together (odd number)
DEFAULT_SHAPE_TOLERANCE = 2.5     # px a point may stray before it counts as "shape"
DEFAULT_OUTPUT_SPACING = 3.0      # px between points of the finished curve
SPLINE_SAMPLES_PER_SEGMENT = 16


def smooth_freehand_path(raw_points: list[Point],
                         sample_spacing: float = DEFAULT_SAMPLE_SPACING,
                         noise_window: int = DEFAULT_NOISE_WINDOW,
                         shape_tolerance: float = DEFAULT_SHAPE_TOLERANCE,
                         output_spacing: float = DEFAULT_OUTPUT_SPACING) -> list[Point]:
    """Return a smooth version of a freehand path that starts and ends at
    exactly the same points as the original."""
    if len(raw_points) < 2:
        return list(raw_points)

    evenly_spaced = resample_evenly(raw_points, sample_spacing)
    denoised = moving_average(evenly_spaced, noise_window)
    shape_points = simplify(denoised, shape_tolerance)
    if len(shape_points) == 2:
        return shape_points
    curve = centripetal_catmull_rom(shape_points, SPLINE_SAMPLES_PER_SEGMENT)
    return resample_evenly(curve, output_spacing)


def path_length(points: list[Point]) -> float:
    """Total length of the polyline through `points`."""
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def resample_evenly(points: list[Point], spacing: float) -> list[Point]:
    """Points spaced `spacing` apart along the polyline, always including
    both original endpoints."""
    if len(points) < 2:
        return list(points)

    resampled = [points[0]]
    distance_to_next_sample = spacing
    for segment_start, segment_end in zip(points, points[1:]):
        segment_length = math.dist(segment_start, segment_end)
        travelled = 0.0
        while segment_length - travelled >= distance_to_next_sample:
            travelled += distance_to_next_sample
            resampled.append(_lerp(segment_start, segment_end, travelled / segment_length))
            distance_to_next_sample = spacing
        distance_to_next_sample -= segment_length - travelled

    if math.dist(resampled[-1], points[-1]) > 1e-9:
        resampled.append(points[-1])
    return resampled


def moving_average(points: list[Point], window: int) -> list[Point]:
    """Replace each point by the mean of the `window` points centred on it.
    The window shrinks near the ends so the first and last points never move."""
    reach = window // 2
    last = len(points) - 1
    averaged = []
    for i in range(len(points)):
        local_reach = min(reach, i, last - i)
        neighbours = points[i - local_reach: i + local_reach + 1]
        averaged.append((sum(x for x, _ in neighbours) / len(neighbours),
                         sum(y for _, y in neighbours) / len(neighbours)))
    return averaged


def simplify(points: list[Point], tolerance: float) -> list[Point]:
    """Ramer-Douglas-Peucker: drop every point that lies within `tolerance`
    of the straight line its neighbours would draw anyway."""
    if len(points) < 3:
        return list(points)

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    ranges_to_check = [(0, len(points) - 1)]
    while ranges_to_check:
        first, last = ranges_to_check.pop()
        farthest_index, farthest_distance = None, tolerance
        for i in range(first + 1, last):
            distance = distance_to_segment(points[i], points[first], points[last])
            if distance > farthest_distance:
                farthest_index, farthest_distance = i, distance
        if farthest_index is not None:
            keep[farthest_index] = True
            ranges_to_check.append((first, farthest_index))
            ranges_to_check.append((farthest_index, last))

    return [p for p, kept in zip(points, keep) if kept]


def centripetal_catmull_rom(control_points: list[Point], samples_per_segment: int) -> list[Point]:
    """Smooth curve that passes through every control point. Uses the
    centripetal parameterisation (alpha = 0.5), which avoids cusps and
    self-intersections."""
    padded = [_reflect(control_points[1], control_points[0]),
              *control_points,
              _reflect(control_points[-2], control_points[-1])]
    curve = []
    for i in range(len(padded) - 3):
        p0, p1, p2, p3 = padded[i: i + 4]
        for step in range(samples_per_segment):
            curve.append(_catmull_rom_point(p0, p1, p2, p3, step / samples_per_segment))
    curve.append(control_points[-1])
    return curve


def point_at_distance_from_end(points: list[Point], distance: float) -> Point:
    """The point `distance` back along the path from its last point. Used to
    aim arrowheads along the curve's overall direction rather than whichever
    way its final pixel happened to point."""
    remaining = distance
    for later, earlier in zip(reversed(points), list(reversed(points))[1:]):
        segment_length = math.dist(later, earlier)
        if segment_length >= remaining:
            return _lerp(later, earlier, remaining / segment_length)
        remaining -= segment_length
    return points[0]


def _lerp(a: Point, b: Point, t: float) -> Point:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _reflect(point: Point, about: Point) -> Point:
    """Mirror `point` through `about`; gives the spline a natural phantom
    control point beyond each end."""
    return (2 * about[0] - point[0], 2 * about[1] - point[1])


def _catmull_rom_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    """Barry-Goldman evaluation of a centripetal Catmull-Rom segment between
    p1 and p2, with t in [0, 1]."""
    def knot_gap(a, b):
        return max(math.dist(a, b) ** 0.5, 1e-6)

    t0 = 0.0
    t1 = t0 + knot_gap(p0, p1)
    t2 = t1 + knot_gap(p1, p2)
    t3 = t2 + knot_gap(p2, p3)
    u = t1 + (t2 - t1) * t

    def blend(a, b, ta, tb):
        return _lerp(a, b, (u - ta) / (tb - ta))

    a1 = blend(p0, p1, t0, t1)
    a2 = blend(p1, p2, t1, t2)
    a3 = blend(p2, p3, t2, t3)
    b1 = blend(a1, a2, t0, t2)
    b2 = blend(a2, a3, t1, t3)
    return blend(b1, b2, t1, t2)
