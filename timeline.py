"""
timeline.py - Steps (keyframes) and expanding them into animation frames.
=========================================================================

A play is a list of `Step`s. Each step stores where every piece ends up
and how long to glide / hold. `generate_timeline_frames` interpolates
between steps; a piece with a linked movement arrow follows that arrow's
curve instead of a straight line.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
"""
import math
from dataclasses import dataclass, field as dc_field
from draw_utils import smoothstep


@dataclass
class Step:
    """One keyframe of the play: where every piece ends up, and how long to glide there and hold."""
    positions: dict            # piece_id -> (x, y) at the END of this step
    annotations: list          # Annotation objects drawn while building this step
    move_duration: float = 1.0  # seconds to glide in from the previous step (0 for step 0)
    hold_duration: float = 1.0  # seconds to pause once arrived


class StepManager:
    """Ordered list of steps that make up a play."""

    def __init__(self):
        self.steps = []

    def add_step(self, positions, annotations, move_duration, hold_duration):
        """Append a step, copying the inputs so later edits don't leak into it."""
        self.steps.append(Step(dict(positions), list(annotations), move_duration, hold_duration))

    def delete_step(self, index):
        """Remove the step at `index`; out-of-range indexes are ignored."""
        if 0 <= index < len(self.steps):
            self.steps.pop(index)

    def clear(self):
        """Remove every step."""
        self.steps = []

    def total_duration(self):
        """Total playback length in seconds. The first step has no glide-in, only a hold."""
        total = 0.0
        for i, s in enumerate(self.steps):
            total += (s.move_duration if i > 0 else 0.0) + s.hold_duration
        return total


def _path_lengths(path):
    """Cumulative arc length at each point of the path, starting at 0."""
    dists = [0.0]
    for a, b in zip(path, path[1:]):
        dists.append(dists[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return dists


def _point_along_path(path, t, lengths):
    """Point at fraction `t` of the path's total arc length (constant speed along the curve)."""
    if len(path) == 1:
        return path[0]
    total = lengths[-1]
    if total <= 1e-9:
        return path[-1] if t >= 1 else path[0]
    target = t * total
    for i in range(1, len(lengths)):
        if lengths[i] >= target:
            seg_len = lengths[i] - lengths[i - 1]
            local_t = 0.0 if seg_len <= 1e-9 else (target - lengths[i - 1]) / seg_len
            a, b = path[i - 1], path[i]
            return (a[0] + (b[0] - a[0]) * local_t, a[1] + (b[1] - a[1]) * local_t)
    return path[-1]


def _remap_path_to_endpoints(path, new_start, new_end):
    """Rigidly translate/rotate/scale a drawn path so it starts and ends
    exactly at the step's real start/end positions, keeping its curve shape."""
    p0, pn = path[0], path[-1]
    d0 = (pn[0] - p0[0], pn[1] - p0[1])
    d1 = (new_end[0] - new_start[0], new_end[1] - new_start[1])
    len0 = math.hypot(*d0)
    if len0 < 1e-6:
        return [new_start, new_end]
    len1 = math.hypot(*d1)
    scale = len1 / len0
    rot = math.atan2(d1[1], d1[0]) - math.atan2(d0[1], d0[0])
    s, c = math.sin(rot), math.cos(rot)
    out = []
    for px, py in path:
        rx, ry = px - p0[0], py - p0[1]
        rxr, ryr = rx * c - ry * s, rx * s + ry * c
        out.append((new_start[0] + rxr * scale, new_start[1] + ryr * scale))
    return out


def generate_timeline_frames(steps, fps=30):
    """Return a list of (positions_dict, annotations_list) frames spanning
    the whole play. A piece with a linked movement arrow for this step
    glides along that curve (arc-length paced); everything else glides in
    a straight line. 'pick' annotations persist once placed; arrow/pass
    annotations are only shown while their own step's glide is playing."""
    frames = []
    if not steps:
        return frames

    persistent = []
    step0 = steps[0]
    for a in step0.annotations:
        if a.persist:
            persistent.append(a)
    n0 = max(1, int(round(step0.hold_duration * fps)))
    for _ in range(n0):
        frames.append((dict(step0.positions), list(persistent)))

    prev_positions = step0.positions
    for step in steps[1:]:
        n_move = max(1, int(round(step.move_duration * fps)))
        transient = [a for a in step.annotations if not a.persist]
        all_ids = set(prev_positions.keys()) | set(step.positions.keys())

        path_for_piece = {}
        for a in step.annotations:
            if a.kind == 'arrow' and a.linked_piece_id is not None and len(a.points) >= 2:
                path_for_piece[a.linked_piece_id] = a.points

        remapped = {}
        for pid, path in path_for_piece.items():
            if pid in step.positions:
                start = prev_positions.get(pid, step.positions[pid])
                target = step.positions[pid]
                rp = _remap_path_to_endpoints(path, start, target)
                remapped[pid] = (rp, _path_lengths(rp))

        for f in range(n_move):
            t = smoothstep((f + 1) / n_move)
            pos = {}
            for pid in all_ids:
                if pid in remapped:
                    rp, lengths = remapped[pid]
                    pos[pid] = _point_along_path(rp, t, lengths)
                else:
                    target = step.positions.get(pid, prev_positions.get(pid))
                    start = prev_positions.get(pid, target)
                    pos[pid] = (start[0] + (target[0] - start[0]) * t,
                                start[1] + (target[1] - start[1]) * t)
            frames.append((pos, persistent + transient))

        for a in step.annotations:
            if a.persist:
                persistent.append(a)

        n_hold = max(1, int(round(step.hold_duration * fps)))
        for _ in range(n_hold):
            frames.append((dict(step.positions), list(persistent)))

        prev_positions = step.positions

    return frames
