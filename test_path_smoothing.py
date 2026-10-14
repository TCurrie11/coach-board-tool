"""
test_path_smoothing.py - Unit tests for the freehand path smoother.
===================================================================

Each test simulates a realistic mouse drag (an intended shape plus a
seeded, repeatable hand wobble) and checks that the smoother removes the
wobble without distorting the shape. Runs with plain `python
test_path_smoothing.py` or under pytest.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.2.0  2026-10-14  TCurrie11  Initial version.
"""
import math
import random

from geometry import distance_to_segment
from path_smoothing import (
    smooth_freehand_path, simplify, resample_evenly, point_at_distance_from_end, path_length,
)

HAND_WOBBLE_PX = 1.5


def simulated_mouse_drag(intended_shape, wobble_px=HAND_WOBBLE_PX, seed=7):
    """Sample `intended_shape(t)` for t in [0, 1] every ~3 px, adding random
    wobble to every point except the first and last (the mouse-down and
    mouse-up spots are exactly where the coach clicked)."""
    rng = random.Random(seed)
    approx_length = path_length([intended_shape(i / 200) for i in range(201)])
    sample_count = max(2, int(approx_length / 3))
    drag = []
    for i in range(sample_count + 1):
        x, y = intended_shape(i / sample_count)
        is_endpoint = i in (0, sample_count)
        drag.append((x, y) if is_endpoint else
                    (x + rng.uniform(-wobble_px, wobble_px), y + rng.uniform(-wobble_px, wobble_px)))
    return drag


def largest_turn_degrees(points):
    """Sharpest direction change between consecutive segments. A smooth curve
    sampled finely turns only a little at each point; jitter makes it zig-zag."""
    largest = 0.0
    for a, b, c in zip(points, points[1:], points[2:]):
        heading_in = math.atan2(b[1] - a[1], b[0] - a[0])
        heading_out = math.atan2(c[1] - b[1], c[0] - b[0])
        turn = abs((heading_out - heading_in + math.pi) % (2 * math.pi) - math.pi)
        largest = max(largest, math.degrees(turn))
    return largest


def straight_line(t):
    return (100 + 300 * t, 200 + 50 * t)


def quarter_circle(t, radius=150, centre=(100, 100)):
    angle = t * math.pi / 2
    return (centre[0] + radius * math.cos(angle), centre[1] + radius * math.sin(angle))


def test_endpoints_are_preserved_exactly():
    drag = simulated_mouse_drag(quarter_circle)
    smoothed = smooth_freehand_path(drag)
    assert smoothed[0] == drag[0]
    assert smoothed[-1] == drag[-1]


def test_wobbly_straight_drag_becomes_perfectly_straight():
    drag = simulated_mouse_drag(straight_line)
    smoothed = smooth_freehand_path(drag)
    assert smoothed == [drag[0], drag[-1]]


def test_wobble_is_removed_from_curves():
    # The pre-1.2.0 smoother scored 5-29 degrees here; the wobble survived.
    for seed in (1, 7, 42):
        drag = simulated_mouse_drag(quarter_circle, seed=seed)
        smoothed = smooth_freehand_path(drag)
        assert largest_turn_degrees(drag) > 30, "test drag should be visibly jittery"
        assert largest_turn_degrees(smoothed) < 3, f"seed {seed}: curve still zig-zags"


def test_curve_stays_close_to_intended_shape():
    radius, centre = 150, (100, 100)
    smoothed = smooth_freehand_path(simulated_mouse_drag(quarter_circle))
    worst_error = max(abs(math.dist(p, centre) - radius) for p in smoothed)
    assert worst_error < 3.0, f"curve drifted {worst_error:.2f}px from the intended arc"


def test_deliberate_corner_is_kept():
    def l_shape(t):
        return (100 + 400 * t, 100) if t < 0.5 else (300, 100 + 400 * (t - 0.5))

    smoothed = smooth_freehand_path(simulated_mouse_drag(l_shape))
    corner = (300, 100)
    closest_to_corner = min(math.dist(p, corner) for p in smoothed)
    assert closest_to_corner < 12, "smoothing rounded the corner away entirely"


def test_output_is_evenly_spaced():
    smoothed = smooth_freehand_path(simulated_mouse_drag(quarter_circle), output_spacing=3.0)
    gaps = [math.dist(a, b) for a, b in zip(smoothed, smoothed[1:-1])]
    assert max(gaps) - min(gaps) < 0.01


def test_tiny_inputs_are_returned_unchanged():
    assert smooth_freehand_path([(5, 5)]) == [(5, 5)]
    assert smooth_freehand_path([(0, 0), (10, 0)]) == [(0, 0), (10, 0)]


def test_simplify_drops_only_points_within_tolerance():
    points = [(0, 0), (5, 0.5), (10, 0), (15, 8), (20, 0)]
    assert simplify(points, tolerance=1.0) == [(0, 0), (10, 0), (15, 8), (20, 0)]


def test_resample_evenly_keeps_both_ends():
    resampled = resample_evenly([(0, 0), (10, 0)], spacing=3)
    assert resampled == [(0, 0), (3, 0), (6, 0), (9, 0), (10, 0)]


def test_point_at_distance_from_end_walks_back_along_the_path():
    path = [(0, 0), (10, 0), (10, 10)]
    assert point_at_distance_from_end(path, 4) == (10, 6)
    assert point_at_distance_from_end(path, 15) == (5, 0)
    assert point_at_distance_from_end(path, 100) == (0, 0)


def test_distance_to_segment():
    assert distance_to_segment((5, 3), (0, 0), (10, 0)) == 3
    assert distance_to_segment((-4, 3), (0, 0), (10, 0)) == 5


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, test in tests:
        test()
        print(f"ok  {name}")
    print(f"ALL {len(tests)} PATH SMOOTHING TESTS PASSED")
