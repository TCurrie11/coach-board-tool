"""Save/load a play (pieces + steps) to/from a JSON file."""
import json
from entities import Piece, Annotation
from timeline import Step


def _serialize(pieces, steps_manager, field_mode, rotation_deg=0.0):
    return {
        'field_mode': field_mode,
        'rotation_deg': rotation_deg,
        'pieces': [{'id': p.id, 'team': p.team, 'pos': list(p.pos)} for p in pieces],
        'steps': [
            {
                'positions': {str(k): list(v) for k, v in s.positions.items()},
                'annotations': [
                    {
                        'kind': a.kind,
                        'color': list(a.color),
                        'points': [list(pt) for pt in a.points],
                        'persist': a.persist,
                        'linked_piece_id': a.linked_piece_id,
                    }
                    for a in s.annotations
                ],
                'move_duration': s.move_duration,
                'hold_duration': s.hold_duration,
            }
            for s in steps_manager.steps
        ],
    }


def save_play(path, pieces, steps_manager, field_mode, rotation_deg=0.0):
    data = _serialize(pieces, steps_manager, field_mode, rotation_deg)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_play(path):
    with open(path) as f:
        data = json.load(f)

    pieces = [Piece(id=p['id'], team=p['team'], pos=tuple(p['pos'])) for p in data['pieces']]

    steps = []
    for sd in data['steps']:
        positions = {int(k): tuple(v) for k, v in sd['positions'].items()}
        annotations = [
            Annotation(a['kind'], tuple(a['color']), tuple(tuple(pt) for pt in a['points']),
                       a.get('persist', False), a.get('linked_piece_id'))
            for a in sd['annotations']
        ]
        steps.append(Step(positions, annotations, sd['move_duration'], sd['hold_duration']))

    return pieces, steps, data.get('field_mode', 'half'), data.get('rotation_deg', 0.0)
