"""Data model for pieces and drawn annotations."""
from dataclasses import dataclass
from itertools import count

_counter = count(1)


def next_id():
    return next(_counter)


def set_counter_above(n):
    """Re-seed the id counter so newly created pieces never collide with
    ids loaded from a saved play."""
    global _counter
    _counter = count(n + 1)


@dataclass
class Piece:
    id: int
    team: str          # 'X' (offense, red) or 'O' (defense, blue)
    pos: tuple          # live (x, y) pixel position on the current canvas

    @staticmethod
    def create(team, pos):
        return Piece(id=next_id(), team=team, pos=tuple(pos))


@dataclass
class Annotation:
    kind: str            # 'arrow' | 'pass' | 'pick'
    color: tuple
    points: tuple         # ((x,y),(x,y),...) path for arrow/pass, ((x,y),) for pick
    persist: bool = False  # True = stays on field for later steps.
                            # False = only shown during the step it was drawn in.
    linked_piece_id: int = None  # 'arrow' only: the X/O this arrow's path belongs to,
                                   # so that piece glides along the curve instead of
                                   # a straight line. Never set for 'pass' (ball throw).
