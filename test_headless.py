"""
test_headless.py - End-to-end tests that run without a display.
===============================================================

Uses Qt's off-screen platform so the real editor, board widget, main
window, renderer and exporter all run headless (e.g. in CI). Covers piece
placement, freehand lines, steps, timeline animation, click mapping under
rotation, field alignment at every output size, MP4/GIF export,
open/save dialogs, recent files and unsaved-change prompts. Runs with plain `python test_headless.py` or under pytest; exits
non-zero on failure.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.0.1  2026-09-15  TCurrie11  Editor and export now share one reference canvas so pieces stay aligned with the field.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    1.1.2  2026-10-14  TCurrie11  Test output goes to a temp folder; no longer deletes real saves/exports.
    1.2.0  2026-10-14  TCurrie11  Uses smooth_freehand_path.
    2.0.0  2026-10-14  TCurrie11  Rewritten for the Qt UI as independent test functions; added rotation-mapping and GIF-timing tests.
    2.1.0  2026-10-14  TCurrie11  Tests for file dialogs, unsaved-change tracking and recent files.
"""
import math
import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Write every export/save into a throwaway folder, never the real
# exports/ and saved_plays/ folders. Must be set before `config` is imported.
TEST_DATA_DIR = tempfile.mkdtemp(prefix="coach_board_test_")
os.environ["COACH_BOARD_DATA_DIR"] = TEST_DATA_DIR

import numpy as np
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

# Keep test settings (recent files, last folders) out of the user's real ones.
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, TEST_DATA_DIR)
APP = QApplication.instance() or QApplication(sys.argv)
APP.setOrganizationName("CoachBoardToolTests")
APP.setApplicationName("CoachBoardToolTests")

import persistence
from config import (
    CREASE_COLOR, DIST_GOAL, EXPORT_HEIGHT, EXPORT_WIDTH, EXPORTS_DIR, OFFENSE_COLOR,
    REFERENCE_H, REFERENCE_W, SAVES_DIR,
)
from editor import PlayEditor, Tool
from entities import Annotation, Piece
from exporter import qimage_to_rgb_array
from field import fit_field_rect
from main_window import MainWindow
from render import piece_label_font
from scene import output_to_reference, render_frame_image, view_transform
from timeline import StepManager, generate_timeline_frames

assert EXPORTS_DIR.startswith(TEST_DATA_DIR), "tests must not write to the real exports folder"

RED = OFFENSE_COLOR


def drag_with_tool(editor, tool, points):
    """Simulate press -> drags -> release through `points` with `tool`."""
    editor.set_tool(tool)
    editor.press(points[0])
    for point in points[1:-1]:
        editor.drag(point)
    editor.release(points[-1])


def bowed_path(start, end, bulge, samples=11):
    """Points from start to end bowing `bulge` px upward at the middle."""
    return [(start[0] + (end[0] - start[0]) * i / (samples - 1),
             start[1] + (end[1] - start[1]) * i / (samples - 1) - bulge * math.sin(math.pi * i / (samples - 1)))
            for i in range(samples)]


def fake_dialogs(window, open_path="", save_path="", save_changes_answer=QMessageBox.Cancel):
    """Replace the window's native dialogs and warning popups with canned
    answers, and record which ones were shown."""
    shown = []

    def ask_open(*_):
        shown.append("open")
        return open_path

    def ask_save(title, suggested, file_filter, suffix):
        shown.append("save")
        return save_path + suffix if save_path and not save_path.endswith(suffix) else save_path

    def ask_save_changes():
        shown.append("save changes?")
        return save_changes_answer

    window._ask_open_path = ask_open
    window._ask_save_path = ask_save
    window._ask_save_changes = ask_save_changes
    window._show_warning = lambda title, message: shown.append(f"warning: {title}")
    return shown


def close_without_saving(window):
    """Close a window, answering "Discard" if it asks about unsaved changes
    (a real dialog would block the headless run forever)."""
    fake_dialogs(window, save_changes_answer=QMessageBox.Discard)
    window.close()


def colour_centroid(rgb_array, colour, tolerance=10):
    """Mean (x, y) of every pixel within `tolerance` of `colour`, or None."""
    close = np.all(np.abs(rgb_array.astype(int) - np.array(colour)) < tolerance, axis=2)
    ys, xs = np.nonzero(close)
    return (xs.mean(), ys.mean()) if len(xs) else None


# ================================================================ editor ==
def test_add_tools_place_pieces_and_only_one_ball():
    editor = PlayEditor()
    for tool, point in [(Tool.ADD_OFFENSE, (300, 300)), (Tool.ADD_DEFENSE, (500, 300)),
                        (Tool.ADD_BALL, (60, 60)), (Tool.ADD_BALL, (80, 90))]:
        editor.set_tool(tool)
        editor.press(point)
    assert [p.team for p in editor.pieces] == ['X', 'O', 'BALL']
    assert editor.ball().pos == (80, 90), "second ball click should move the existing ball"


def test_select_tool_drags_a_piece():
    editor = PlayEditor()
    piece = Piece.create('X', (200, 200))
    editor.pieces.append(piece)
    drag_with_tool(editor, Tool.SELECT, [(203, 198), (250, 240), (300, 260)])
    assert piece.pos == (250, 240), "release only ends the drag; the last drag point wins"
    assert editor.dragging_piece is None


def test_ball_position_carries_forward_into_new_steps():
    editor = PlayEditor()
    editor.set_tool(Tool.ADD_BALL)
    editor.press((60, 60))
    editor.commit_step(1.0, 1.0)
    editor.commit_step(0.8, 1.0)
    ball_id = editor.ball().id
    assert editor.steps.steps[1].positions[ball_id] == editor.steps.steps[0].positions[ball_id]


def test_first_step_never_has_a_glide_in():
    editor = PlayEditor()
    editor.commit_step(2.5, 1.0)
    assert editor.steps.steps[0].move_duration == 0.0


def test_arrow_started_on_a_player_is_linked_and_smoothed():
    editor = PlayEditor()
    runner = Piece.create('X', (200, 200))
    editor.pieces.append(runner)
    drag_with_tool(editor, Tool.ARROW, [(200 + i * 15, 200 + i * 4) for i in range(7)])
    arrow = editor.pending_annotations[-1]
    assert arrow.kind == 'arrow' and arrow.linked_piece_id == runner.id
    assert arrow.color == RED
    assert arrow.points[0] == (200, 200)


def test_pass_is_never_linked_to_a_player():
    editor = PlayEditor()
    passer = Piece.create('O', (200, 200))
    editor.pieces.append(passer)
    drag_with_tool(editor, Tool.PASS, [(200 + i * 15, 200) for i in range(7)])
    assert editor.pending_annotations[-1].linked_piece_id is None


def test_tiny_drag_is_treated_as_a_click_not_a_line():
    editor = PlayEditor()
    drag_with_tool(editor, Tool.ARROW, [(100, 100), (102, 101)])
    assert editor.pending_annotations == []


def test_delete_tool_removes_pieces_then_lines():
    editor = PlayEditor()
    piece = Piece.create('X', (100, 100))
    editor.pieces.append(piece)
    editor.pending_annotations.append(Annotation('arrow', RED, ((300, 300), (400, 300))))
    editor.set_tool(Tool.DELETE)
    editor.press((100, 100))
    editor.press((350, 302))
    assert editor.pieces == [] and editor.pending_annotations == []


def test_undo_reverts_one_action_at_a_time():
    editor = PlayEditor()
    editor.set_tool(Tool.ADD_OFFENSE)
    editor.press((100, 100))
    editor.press((200, 200))
    assert editor.undo_last_action() and len(editor.pieces) == 1
    assert editor.undo_last_action() and len(editor.pieces) == 0
    assert not editor.undo_last_action()


# ============================================================== timeline ==
def test_linked_arrow_makes_the_piece_follow_the_curve():
    steps = StepManager()
    mover = Piece.create('X', (100, 100))
    steps.add_step({mover.id: mover.pos}, [], 0.0, 0.2)
    arrow = Annotation('arrow', RED, tuple(bowed_path((100, 100), (300, 100), bulge=80)),
                       linked_piece_id=mover.id)
    steps.add_step({mover.id: (300, 100)}, [arrow], 1.0, 0.2)
    midway = [pos[mover.id] for pos, _ in generate_timeline_frames(steps.steps, fps=30)
              if abs(pos[mover.id][0] - 200) < 15]
    assert midway and midway[0][1] < 80, "piece should bow upward with the arrow, not travel straight"


def test_pass_never_moves_a_piece_along_its_curve():
    steps = StepManager()
    stander = Piece.create('O', (500, 500))
    steps.add_step({stander.id: stander.pos}, [], 0.0, 0.2)
    bogus_pass = Annotation('pass', RED, tuple(bowed_path((500, 500), (700, 500), bulge=80)),
                            linked_piece_id=stander.id)
    steps.add_step({stander.id: (700, 500)}, [bogus_pass], 1.0, 0.2)
    midway = [pos[stander.id] for pos, _ in generate_timeline_frames(steps.steps, fps=30)
              if abs(pos[stander.id][0] - 600) < 15]
    assert midway and abs(midway[0][1] - 500) < 5


def test_picks_only_show_during_their_own_step():
    steps = StepManager()
    steps.add_step({}, [], 0.0, 0.2)
    steps.add_step({}, [Annotation('pick', RED, ((400, 350),))], 0.5, 0.2)
    steps.add_step({}, [], 0.5, 0.2)
    frames = generate_timeline_frames(steps.steps, fps=30)
    assert any(a.kind == 'pick' for _, annotations in frames for a in annotations)
    assert not any(a.kind == 'pick' for a in frames[-1][1])


# ========================================================= scene / view ==
def test_click_mapping_round_trips_at_any_rotation():
    for rotation in (0, 35, 90, 180, 271.5):
        transform = view_transform(1000, 700, rotation)
        for reference_point in [(0, 0), (REFERENCE_W / 2, REFERENCE_H / 2), (812.5, 133)]:
            on_screen = transform.map(*reference_point)
            back = output_to_reference(on_screen, 1000, 700, rotation)
            assert math.dist(back, reference_point) < 1e-6, f"rotation {rotation}: {back} != {reference_point}"


def test_rotation_turns_the_field_anticlockwise_like_1x():
    # In 1.x a +90 degree rotation put the field's right edge at the top.
    top_of_screen = view_transform(1000, 1000, 90).map(REFERENCE_W, REFERENCE_H / 2)
    assert top_of_screen[1] < 100


def test_pieces_stay_on_the_crease_at_editor_and_export_sizes():
    """Regression for 1.0.1: pieces used to drift from the field in exports."""
    layout = fit_field_rect((0, 0, REFERENCE_W, REFERENCE_H), 'half')
    on_goal = Piece.create('X', (layout['x'] + DIST_GOAL * layout['s'], layout['y'] + layout['h'] / 2))
    for width, height in [(REFERENCE_W, REFERENCE_H), (EXPORT_WIDTH, EXPORT_HEIGHT), (600, 900)]:
        image = render_frame_image(width, height, 'half', 0, [on_goal], {}, [], piece_label_font())
        pixels = qimage_to_rgb_array(image)
        piece_centre = colour_centroid(pixels, OFFENSE_COLOR)
        crease_centre = colour_centroid(pixels, CREASE_COLOR)
        assert piece_centre and crease_centre, f"{width}x{height}: piece or crease not found"
        assert math.dist(piece_centre, crease_centre) < 3, f"{width}x{height}: piece drifted off the crease"


def test_board_view_turns_a_mouse_drag_into_a_piece_move():
    window = MainWindow()
    window.show()
    board = window.board
    piece = Piece.create('X', (300, 300))
    window.editor.pieces.append(piece)
    window.editor.rotation_deg = 30

    def screen_point(reference_point):
        x, y = view_transform(board.width(), board.height(), 30).map(*reference_point)
        return QPoint(round(x), round(y))

    QTest.mousePress(board, Qt.LeftButton, Qt.NoModifier, screen_point((300, 300)))
    QTest.mouseMove(board, screen_point((400, 350)))
    QTest.mouseRelease(board, Qt.LeftButton, Qt.NoModifier, screen_point((400, 350)))
    assert math.dist(piece.pos, (400, 350)) < 2, f"piece ended at {piece.pos}"
    close_without_saving(window)


# =================================================== window: steps/preview ==
def test_window_add_step_preview_and_step_list():
    window = MainWindow()
    window.editor.pieces.append(Piece.create('X', (300, 300)))
    window.add_step()
    window.editor.pieces[0].pos = (450, 300)
    window.add_step()
    assert window.steps_list.count() == 2
    window.preview()
    assert window.board.is_previewing
    window.board.stop_preview()
    assert not window.board.is_previewing
    close_without_saving(window)


# ================================================== export / save / load ==
def _window_with_a_two_step_play():
    window = MainWindow()
    editor = window.editor
    editor.pieces = [Piece.create('X', (300, 300)), Piece.create('O', (500, 300)),
                     Piece.create('BALL', (310, 290))]
    window.add_step()
    editor.pieces[0].pos = (450, 300)
    editor.pending_annotations.append(Annotation('arrow', RED, ((300, 300), (450, 300)),
                                                 linked_piece_id=editor.pieces[0].id))
    window.move_input.setValue(0.5)
    window.hold_input.setValue(0.5)
    window.add_step()
    window.rotation_input.setValue(20)
    return window


def test_export_mp4_and_gif_with_correct_gif_timing():
    from PIL import Image

    window = _window_with_a_two_step_play()
    mp4_path = os.path.join(TEST_DATA_DIR, "test_export.mp4")
    gif_path = os.path.join(TEST_DATA_DIR, "test_export.gif")
    fake_dialogs(window, save_path=mp4_path)
    window.export('mp4')
    fake_dialogs(window, save_path=os.path.join(TEST_DATA_DIR, "test_export"))  # suffix added for us
    window.export('gif')
    assert os.path.getsize(mp4_path) > 0
    # Pillow merges identical consecutive frames (the holds) into one longer
    # frame, so check total running time rather than frame count.
    with Image.open(gif_path) as gif:
        gif_seconds = 0.0
        for index in range(gif.n_frames):
            gif.seek(index)
            gif_seconds += gif.info["duration"] / 1000
    play_seconds = window.editor.steps.total_duration()
    assert abs(gif_seconds - play_seconds) < 0.1, f"GIF runs {gif_seconds:.2f}s; the play is {play_seconds:.2f}s"
    close_without_saving(window)


def test_cancelling_the_export_dialog_writes_nothing():
    window = _window_with_a_two_step_play()
    shown = fake_dialogs(window, save_path="")
    before = set(os.listdir(TEST_DATA_DIR))
    window.export('mp4')
    assert shown == ["save"] and set(os.listdir(TEST_DATA_DIR)) == before
    close_without_saving(window)


def test_first_save_asks_where_then_saves_in_place():
    window = _window_with_a_two_step_play()
    path = os.path.join(TEST_DATA_DIR, "zone_offense")
    shown = fake_dialogs(window, save_path=path)
    assert window.save_play()
    assert window.current_file_path == path + ".json" and os.path.isfile(path + ".json")
    assert window.windowTitle().startswith("zone_offense")

    window.editor.pieces[0].pos = (10, 10)
    assert window.save_play()
    assert shown == ["save"], "second save should go straight to the same file"
    close_without_saving(window)


def test_save_and_open_round_trip():
    window = _window_with_a_two_step_play()
    path = os.path.join(TEST_DATA_DIR, "round_trip.json")
    fake_dialogs(window, save_path=path)
    window.save_play()
    saved_pieces = [(p.id, p.team, p.pos) for p in window.editor.pieces]

    window.new_play()
    assert window.editor.pieces == [] and window.rotation_input.value() == 0
    fake_dialogs(window, open_path=path)
    window.open_play()

    assert [(p.id, p.team, p.pos) for p in window.editor.pieces] == saved_pieces
    assert window.editor.rotation_deg == 20 and window.rotation_input.value() == 20
    assert window.steps_list.count() == 2
    assert window.editor.steps.steps[1].annotations[0].linked_piece_id == saved_pieces[0][0]
    assert not window.has_unsaved_changes()
    close_without_saving(window)


def test_unsaved_changes_are_tracked_and_undo_clears_them():
    window = MainWindow()
    assert not window.has_unsaved_changes()
    window.editor.set_tool(Tool.ADD_OFFENSE)
    window.editor.press((100, 100))
    window._on_board_edited()
    assert window.has_unsaved_changes() and window.isWindowModified()
    window.undo_last_action()
    assert not window.has_unsaved_changes(), "undoing back to the saved state means nothing to save"
    close_without_saving(window)


def test_unsaved_changes_prompt_cancel_discard_and_save():
    window = _window_with_a_two_step_play()

    shown = fake_dialogs(window, save_changes_answer=QMessageBox.Cancel)
    window.new_play()
    assert shown == ["save changes?"] and window.editor.pieces, "cancel must keep the play"

    fake_dialogs(window, save_changes_answer=QMessageBox.Discard)
    window.new_play()
    assert window.editor.pieces == []

    window.editor.pieces.append(Piece.create('X', (1, 1)))
    path = os.path.join(TEST_DATA_DIR, "saved_on_prompt.json")
    fake_dialogs(window, save_path=path, save_changes_answer=QMessageBox.Save)
    window.new_play()
    assert os.path.isfile(path) and window.editor.pieces == []
    close_without_saving(window)


def test_recent_files_are_remembered_and_missing_ones_dropped():
    window = MainWindow()
    paths = []
    for name in ("first", "second"):
        path = os.path.join(TEST_DATA_DIR, f"recent_{name}.json")
        fake_dialogs(window, save_path=path)
        window.save_play_as()
        paths.append(os.path.abspath(path))
    assert window.recent_files()[:2] == [paths[1], paths[0]], "most recent first"

    os.remove(paths[0])
    shown = fake_dialogs(window)
    window.open_play_file(paths[0])
    assert shown == ["warning: File not found"]
    assert paths[0] not in window.recent_files()
    window._rebuild_recent_files_menu()
    assert window.recent_files_menu.actions()[0].text() == "recent_second.json"
    close_without_saving(window)


def test_new_pieces_never_reuse_loaded_ids():
    path = os.path.join(TEST_DATA_DIR, "ids.json")
    persistence.save_play(path, [Piece(id=500, team='X', pos=(1, 1))], StepManager(), 'half')
    editor = PlayEditor()
    editor.replace_play(*persistence.load_play(path))
    editor.set_tool(Tool.ADD_OFFENSE)
    editor.press((50, 50))
    assert editor.pieces[-1].id > 500


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn)]
    try:
        for name, test in tests:
            test()
            print(f"ok  {name}")
        print(f"ALL {len(tests)} HEADLESS TESTS PASSED")
    finally:
        shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
