"""Entry point. When frozen into a standalone .exe (PyInstaller), any
uncaught error is written to error_log.txt next to the executable and
shown in a native popup, instead of the app just disappearing."""
import os
import sys
import traceback


def _base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    from app import App
    App().run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        log_path = os.path.join(_base_dir(), "error_log.txt")
        try:
            with open(log_path, "w") as f:
                f.write(tb)
        except Exception:
            pass

        if getattr(sys, 'frozen', False):
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "Coach Board Tool hit a problem and had to close.\n\n"
                    f"Details were saved to:\n{log_path}\n\n"
                    "Send that file along if you're reporting this.",
                    "Coach Board Tool - Error",
                    0x10,  # MB_ICONERROR
                )
            except Exception:
                pass
        else:
            raise
