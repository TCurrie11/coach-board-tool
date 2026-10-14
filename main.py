"""
main.py - Entry point for the Coach Board Tool.
===============================================

Starts the Qt application with the dark theme and opens the main window.
A play file given on the command line (or via "Open with" / double-click
once a file association is set up) is opened straight away.
`--smoke-test` runs a quick self-check instead (see smoke_test.py).

Any uncaught error - at startup or inside a button handler - is written to
error_log.txt in the app's data folder (see config.DATA_DIR) and shown in a dialog, instead of the app
silently disappearing on a coach's machine.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    2.0.0  2026-10-14  TCurrie11  Launches the Qt UI; cross-platform error dialog replaces the Windows-only popup.
    2.1.0  2026-10-14  TCurrie11  Opens a play file passed on the command line; settings identity for recent files.
    2.1.1  2026-10-14  TCurrie11  --smoke-test flag for checking packaged builds in CI.
    2.1.2  2026-10-14  TCurrie11  Creates the data folder before writing the error log.
"""
import os
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, APP_ORGANIZATION, DATA_DIR

ERROR_LOG_PATH = os.path.join(DATA_DIR, "error_log.txt")


def report_unexpected_error(exc_type, exc_value, exc_traceback):
    """Log the traceback to a file and tell the user where to find it."""
    details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    sys.stderr.write(details)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ERROR_LOG_PATH, "w") as log_file:
            log_file.write(details)
    except OSError:
        pass
    if QApplication.instance() is not None:
        QMessageBox.critical(None, f"{APP_NAME} - Error",
                             f"{APP_NAME} hit a problem.\n\n"
                             f"Details were saved to:\n{ERROR_LOG_PATH}\n\n"
                             "Send that file along if you're reporting this.")


def main():
    """Create the application and run it until the user closes the window."""
    sys.excepthook = report_unexpected_error
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANIZATION)  # where QSettings stores recent files

    from theme import apply_dark_theme
    from main_window import MainWindow
    from smoke_test import SMOKE_TEST_FLAG, run_smoke_test

    apply_dark_theme(app)
    if SMOKE_TEST_FLAG in sys.argv:
        return run_smoke_test(app)

    window = MainWindow()
    window.show()
    play_files_to_open = [arg for arg in sys.argv[1:] if os.path.isfile(arg)]
    if play_files_to_open:
        window.open_play_file(play_files_to_open[0])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
