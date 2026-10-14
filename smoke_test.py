"""
smoke_test.py - Self-check that a packaged build actually works.
================================================================

Run as `CoachBoardTool --smoke-test` (or `python main.py --smoke-test`).
Opens the real main window, builds a two-step play, draws it, and exports
a short MP4 and GIF into a temporary folder, then quits with exit code 0
on success or 1 on failure.

CI runs this against the finished .app on a real Mac, which catches the
problems that only show up after packaging - a missing Qt plugin, ffmpeg
not bundled, a module PyInstaller failed to include - before a coach
ever downloads the app.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    2.1.1  2026-10-14  TCurrie11  Initial version.
"""
import os
import shutil
import tempfile
import traceback

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

SMOKE_TEST_FLAG = "--smoke-test"


def run_smoke_test(app: QApplication) -> int:
    """Exercise the window, renderer and both exporters. Returns an exit code."""
    output_dir = tempfile.mkdtemp(prefix="coach_board_smoke_")
    # Keep the check from touching the user's real recent files / folders.
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, output_dir)
    try:
        from entities import Annotation, Piece
        from main_window import MainWindow

        window = MainWindow()
        window.show()
        app.processEvents()
        print(f"Window opened on Qt platform '{app.platformName()}'")

        runner = Piece.create('X', (300, 300))
        window.editor.pieces = [runner, Piece.create('O', (500, 300)), Piece.create('BALL', (310, 290))]
        window.add_step()
        runner.pos = (450, 350)
        window.editor.pending_annotations.append(
            Annotation('arrow', (205, 35, 35), ((300, 300), (380, 280), (450, 350)), linked_piece_id=runner.id))
        window.move_input.setValue(0.3)
        window.hold_input.setValue(0.2)
        window.add_step()
        window.board.repaint()
        print("Play built and drawn")

        for video_format in ('mp4', 'gif'):
            path = os.path.join(output_dir, f"smoke.{video_format}")
            window._ask_save_path = lambda *_args, target=path: target
            window.export(video_format)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise RuntimeError(f"{video_format.upper()} export produced no file")
            print(f"{video_format.upper()} export OK ({os.path.getsize(path)} bytes)")

        window._confirm_discard_unsaved_changes = lambda: True  # quit without the save prompt
        window.close()
        print("SMOKE TEST PASSED")
        return 0
    except Exception:
        traceback.print_exc()
        print("SMOKE TEST FAILED")
        return 1
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
