import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
import shutil
import traceback


def main():
    from app import App
    from entities import Piece, Annotation
    from timeline import generate_timeline_frames
    from config import EXPORTS_DIR, SAVES_DIR

    for d in (EXPORTS_DIR, SAVES_DIR):
        if os.path.isdir(d):
            shutil.rmtree(d)

    app = App()
    print("App initialized OK")

    # --- pieces + ball -----------------------------------------------
    p1 = Piece.create('X', (300, 300))
    p2 = Piece.create('O', (500, 300))
    app.pieces = [p1, p2]
    app.mode = 'add_ball'
    app.on_mouse_down((60, 60))  # within the field canvas, exercises the real add_ball code path
    ball = app.get_ball()
    assert ball is not None, "ball was not created by add_ball tool"
    print("Ball created at", ball.pos)

    app.hold_input.text = "1.0"
    app.add_step()
    assert len(app.steps.steps) == 1
    ball_pos_step0 = app.steps.steps[0].positions[ball.id]

    # --- freehand smoothing -------------------------------------------
    from draw_utils import smooth_path
    raw = [(0, 0), (20, 5), (40, 25), (60, 60), (90, 70), (120, 65)]
    smoothed = smooth_path(raw, min_dist=10)
    assert len(smoothed) >= len(raw), "smoothing should densify the path"
    print(f"smooth_path: {len(raw)} raw points -> {len(smoothed)} smoothed points")

    app.pending_annotations.append(Annotation('arrow', (205, 35, 35), tuple(smoothed), False))
    app.pending_annotations.append(Annotation('pick', (205, 35, 35), ((400, 350),), False))  # picks: persist=False now

    p1.pos = (450, 300)
    app.move_input.text = "0.8"
    app.hold_input.text = "1.0"
    app.add_step()
    assert len(app.steps.steps) == 2
    # ball position should have carried forward unchanged (nobody moved it)
    assert app.steps.steps[1].positions[ball.id] == ball_pos_step0, "ball position did not persist across steps"
    print("Ball position correctly carried forward into step 2")

    # pick should be transient (persist=False) -> confirm via generated frames
    frames = generate_timeline_frames(app.steps.steps, fps=30)
    print(f"Generated {len(frames)} timeline frames")
    # after all frames, no 'pick' annotation should remain in the final frame
    _, last_anns = frames[-1]
    assert not any(a.kind == 'pick' for a in last_anns), "pick should not persist into later frames"
    print("Pick correctly non-persistent")

    # --- per-action undo -----------------------------------------------
    before = len(app.pieces)
    app.mode = 'add_x'
    app._push_undo()
    app.pieces.append(Piece.create('X', (100, 100)))
    assert len(app.pieces) == before + 1
    app.undo_action()
    assert len(app.pieces) == before, "undo_action did not revert piece addition"
    print("Per-action undo OK")

    # --- linked movement arrow: piece should follow the CURVE, not a straight line --
    from timeline import StepManager, generate_timeline_frames as gen_frames
    sm = StepManager()
    mover = Piece.create('X', (100, 100))
    sm.add_step({mover.id: mover.pos}, [], 0.0, 0.2)
    # A pronounced curved (bowed) path from (100,100) to (300,100): bulges up to y=20 at the midpoint.
    curved_path = tuple((100 + i * 20, 100 - (i * (10 - i)) * 4) for i in range(11))
    arrow = Annotation('arrow', (205, 35, 35), curved_path, False, linked_piece_id=mover.id)
    sm.add_step({mover.id: (300, 100)}, [arrow], 1.0, 0.2)
    curve_frames = gen_frames(sm.steps, fps=30)
    mid_frame_positions = [pos[mover.id] for pos, _ in curve_frames if abs(pos[mover.id][0] - 200) < 15]
    assert mid_frame_positions, "couldn't find a mid-path frame to check"
    mid_y = mid_frame_positions[0][1]
    straight_line_mid_y = 100  # a straight line from (100,100) to (300,100) never leaves y=100
    assert abs(mid_y - straight_line_mid_y) > 20, (
        f"piece did not follow the curved arrow (mid_y={mid_y}, expected well above/below {straight_line_mid_y})")
    print(f"Linked-arrow curve following OK (mid-path y={mid_y:.1f}, straight-line would be {straight_line_mid_y})")

    # a 'pass' must never move a piece along its path, even if a curved one is
    # (incorrectly) tagged with linked_piece_id - the engine should ignore that.
    sm2 = StepManager()
    stander = Piece.create('O', (500, 500))
    sm2.add_step({stander.id: stander.pos}, [], 0.0, 0.2)
    curved_pass = tuple((500 + i * 20, 500 - (i * (10 - i)) * 4) for i in range(11))  # bulges to y=420
    bogus_pass = Annotation('pass', (35, 95, 205), curved_pass, False, linked_piece_id=stander.id)
    sm2.add_step({stander.id: (700, 500)}, [bogus_pass], 1.0, 0.2)  # real target: straight line to (700,500)
    pass_frames = gen_frames(sm2.steps, fps=30)
    mid_pass_positions = [pos[stander.id] for pos, _ in pass_frames if abs(pos[stander.id][0] - 600) < 15]
    assert mid_pass_positions, "couldn't find a mid-path frame to check"
    assert abs(mid_pass_positions[0][1] - 500) < 5, (
        f"a pass must never move a piece along its curve (got y={mid_pass_positions[0][1]}, expected ~500)")
    print("Pass annotations correctly never move a piece along their path")

    # --- the app's own arrow-drawing path links to the piece it starts on --
    app.mode = 'arrow'
    app.pending_annotations = []
    mover2 = Piece.create('X', (200, 200))
    app.pieces.append(mover2)
    start_screen = (mover2.pos[0] + app.container_origin[0], mover2.pos[1] + app.container_origin[1])
    app.on_mouse_down(start_screen)
    for i in range(1, 6):
        app.on_mouse_move((start_screen[0] + i * 15, start_screen[1] + i * 4))
    app.on_mouse_up((start_screen[0] + 90, start_screen[1] + 30))
    arrows = [a for a in app.pending_annotations if a.kind == 'arrow']
    assert arrows and arrows[-1].linked_piece_id == mover2.id, "arrow drawn from a piece was not linked to it"
    print("App correctly links a freehand arrow to the piece it starts on")

    # --- rotation + round trip through the scene composer --------------
    app.rotation_deg = 35
    app.draw()
    print("draw() with rotation=35 OK")
    app.field_mode = 'full'
    app.draw()
    app.field_mode = 'half'
    print("Field mode toggle with rotation OK")

    # --- preview ---------------------------------------------------------
    app.start_preview()
    for _ in range(5):
        app.update_preview(0.05)
        app.draw()
    app.previewing = False
    print("Preview OK")

    # --- export (rotation baked in) + folder creation --------------------
    app.filename_input.text = "test_export"
    app.rotation_deg = 20
    app.export_video('mp4')
    print("MP4 export status:", app.status_message)
    assert os.path.isfile(os.path.join(EXPORTS_DIR, "test_export.mp4")), "mp4 not written into exports/ folder"
    app.export_video('gif')
    assert os.path.isfile(os.path.join(EXPORTS_DIR, "test_export.gif")), "gif not written into exports/ folder"
    print("Exports folder OK:", os.listdir(EXPORTS_DIR))

    # --- save/load round trip (rotation + ball) --------------------------
    app.filename_input.text = "test_play"
    app.save_play()
    assert os.path.isfile(os.path.join(SAVES_DIR, "test_play.json")), "save file not written into saved_plays/ folder"
    print("Save status:", app.status_message)

    saved_piece_count = len(app.pieces)
    saved_rotation = app.rotation_deg
    app.pieces = []
    app.steps.steps = []
    app.rotation_deg = 0
    app.load_play()
    print("Load status:", app.status_message)
    assert len(app.pieces) == saved_piece_count, "piece count mismatch after load"
    assert app.rotation_deg == saved_rotation, "rotation did not round-trip through save/load"
    assert app.get_ball() is not None, "ball did not round-trip through save/load"
    print("Save/load round trip OK (including ball + rotation)")

    print("ALL HEADLESS TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
