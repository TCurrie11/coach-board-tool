"""
entities.py - Data model for the things placed on the field.
============================================================

`Piece` is a player (X / O) or the ball. `Annotation` is something drawn
for a single step: a movement arrow, a dashed pass line, or a pick marker.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
"""
from dataclasses import dataclass
from itertools import count

_counter = count(1)


def next_id():
    """Return the next unique piece id."""
    return next(_counter)


def set_counter_above(n):
    """Re-seed the id counter so newly created pieces never collide with
    ids loaded from a saved play."""
    global _counter
    _counter = count(n + 1)


@dataclass
class Piece:
    """A player ('X' offense / 'O' defense) or the ball ('BALL') on the field."""
    id: int
    team: str          # 'X' (offense, red) or 'O' (defense, blue)
    pos: tuple          # live (x, y) pixel position on the current canvas

    @staticmethod
    def create(team, pos):
        """Build a new piece with a freshly allocated id."""
        return Piece(id=next_id(), team=team, pos=tuple(pos))


@dataclass
class Annotation:
    """Something drawn on the field for one step: a movement arrow, a pass, or a pick."""
    kind: str            # 'arrow' | 'pass' | 'pick'
    color: tuple
    points: tuple         # ((x,y),(x,y),...) path for arrow/pass, ((x,y),) for pick
    persist: bool = False  # True = stays on field for later steps.
                            # False = only shown during the step it was drawn in.
    linked_piece_id: int = None  # 'arrow' only: the X/O this arrow's path belongs to,
                                   # so that piece glides along the curve instead of
                                   # a straight line. Never set for 'pass' (ball throw).
