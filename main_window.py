"""
main_window.py - The application window: board, sidebar, menus, status bar.
===========================================================================

Builds the sidebar controls and menus and wires them to the `PlayEditor`
and `BoardView`. Holds no editing rules of its own - it reads values from
widgets, calls the editor, and refreshes what's shown.

Also owns the document lifecycle: which file the play belongs to, whether
it has unsaved changes, native open/save/export dialogs and recent files.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    2.0.0  2026-10-14  TCurrie11  Initial version; replaces the pygame sidebar from app.py (1.x).
    2.1.0  2026-10-14  TCurrie11  Native open/save/export dialogs, recent files, unsaved-changes prompt, drag-and-drop.
    2.1.2  2026-10-14  TCurrie11  Dialogs fall back to the home folder if the default folder can't be created.
"""
import os

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractSpinBox, QButtonGroup, QDoubleSpinBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QMainWindow, QMessageBox, QProgressDialog, QPushButton, QScrollArea, QSizePolicy, QToolButton,
    QVBoxLayout, QWidget,
)

import persistence
from board_view import BoardView
from config import (
    APP_NAME, APP_VERSION, DEFAULT_HOLD_SECONDS, DEFAULT_MOVE_SECONDS, EXPORT_FPS,
    EXPORT_HEIGHT, EXPORT_WIDTH, EXPORTS_DIR, MIN_STEP_SECONDS, SAVES_DIR,
)
from editor import PlayEditor, Tool
from exporter import export_video
from icons import tool_icon
from render import piece_label_font
from scene import render_frame_image
from timeline import generate_timeline_frames

SIDEBAR_WIDTH = 300
TOOL_BUTTONS = [
    # (tool, label, shortcut, tooltip)
    (Tool.SELECT, "Select", "V", "Drag pieces to reposition them"),
    (Tool.DELETE, "Delete", "D", "Click a piece, line or pick to remove it"),
    (Tool.ADD_OFFENSE, "Add X", "X", "Place an offensive player (red)"),
    (Tool.ADD_DEFENSE, "Add O", "O", "Place a defensive player (blue)"),
    (Tool.ADD_BALL, "Ball", "B", "Place or move the ball"),
    (Tool.PICK, "Pick", "K", "Drop a pick / screen marker"),
    (Tool.ARROW, "Run", "A", "Draw a movement arrow. Start it on a player and they follow the curve"),
    (Tool.PASS, "Pass", "P", "Draw a dashed pass line"),
]
ROTATION_PRESETS = (0, 90, 180, 270)
STEPS_LIST_HEIGHT = 104
UNTITLED_PLAY_NAME = "Untitled play"
PLAY_FILE_FILTER = f"Coach Board plays (*{persistence.PLAY_FILE_SUFFIX})"
VIDEO_FILE_FILTERS = {'mp4': "MP4 video (*.mp4)", 'gif': "Animated GIF (*.gif)"}
MAX_RECENT_FILES = 8

# QSettings keys (persisted per user by Qt in the platform's usual place)
RECENT_FILES_KEY = "recentFiles"
LAST_PLAY_DIR_KEY = "lastPlayDirectory"
LAST_EXPORT_DIR_KEY = "lastExportDirectory"


class ExportCancelled(Exception):
    """Raised inside the frame generator when the user cancels an export."""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings()
        self.current_file_path = None     # None until the play is saved or opened
        self.editor = PlayEditor()
        self.board = BoardView(self.editor)
        self.board.edited.connect(self._on_board_edited)
        self.board.preview_finished.connect(lambda: self._show_status("Preview finished."))

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.board, stretch=1)
        layout.addWidget(self._build_sidebar())
        self.setCentralWidget(central)

        self._build_menus()
        self._refresh_steps_list()
        self._mark_current_state_as_saved()
        self.setAcceptDrops(True)
        self._show_status("Add players with X / O, draw runs and passes, then press Add step.")
        self.resize(1300, 820)

    # ============================================================ sidebar ==
    def _build_sidebar(self):
        sidebar = QWidget(objectName="Sidebar")
        column = QVBoxLayout(sidebar)
        column.setContentsMargins(14, 6, 14, 14)
        column.setSpacing(5)

        column.addWidget(_section_heading("FIELD"))
        self._field_mode_buttons = _exclusive_toggle_row(
            column, [("Half field", 'half'), ("Full field", 'full')], self.editor.field_mode,
            self._set_field_mode)
        column.addLayout(self._build_rotation_controls())

        column.addWidget(_section_heading("TOOLS"))
        column.addLayout(self._build_tool_grid())
        draw_colour_buttons = _exclusive_toggle_row(
            column, [("Draw red", 'X'), ("Draw blue", 'O')], self.editor.draw_team, self._set_draw_team)
        for button in draw_colour_buttons.buttons():
            button.setToolTip("Colour for lines and picks that don't start on a player.\n"
                              "Lines starting on a player always use that player's colour.")

        column.addWidget(_section_heading("STEPS"))
        column.addLayout(self._build_timing_inputs())
        self.add_step_button = _button("Add step", self.add_step, role="primary")
        self.add_step_button.setToolTip("Save current positions and drawings as the next step (Ctrl+Enter)")
        column.addWidget(self.add_step_button)
        self.steps_list = QListWidget()
        self.steps_list.setFixedHeight(STEPS_LIST_HEIGHT)
        self.steps_list.currentRowChanged.connect(self._on_step_selected)
        column.addWidget(self.steps_list)
        step_actions = QHBoxLayout()
        self.apply_timing_button = _button("Apply timing", self.apply_timing_to_selected_step)
        self.delete_step_button = _button("Delete step", self.delete_selected_step, role="danger")
        step_actions.addWidget(self.apply_timing_button)
        step_actions.addWidget(self.delete_step_button)
        column.addLayout(step_actions)

        column.addWidget(_section_heading("PLAY"))
        column.addWidget(_button("Preview", self.preview, role="primary"))
        export_row = QHBoxLayout()
        export_row.addWidget(_button("Export MP4\u2026", lambda: self.export('mp4')))
        export_row.addWidget(_button("Export GIF\u2026", lambda: self.export('gif')))
        column.addLayout(export_row)

        column.addWidget(_section_heading("FILE"))
        file_row = QHBoxLayout()
        file_row.addWidget(_button("Open\u2026", self.open_play))
        file_row.addWidget(_button("Save", self.save_play))
        file_row.addWidget(_button("Save as\u2026", self.save_play_as))
        column.addLayout(file_row)
        column.addStretch()

        scroll = QScrollArea(objectName="SidebarScroll")
        scroll.setWidget(sidebar)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(SIDEBAR_WIDTH)
        return scroll

    def _build_rotation_controls(self):
        rows = QVBoxLayout()
        presets = QHBoxLayout()
        for degrees in ROTATION_PRESETS:
            presets.addWidget(_button(f"{degrees}°", lambda _=False, d=degrees: self.rotation_input.setValue(d)))
        rows.addLayout(presets)

        self.rotation_input = QDoubleSpinBox(minimum=-360, maximum=360, decimals=1,
                                             singleStep=15, suffix="°", wrapping=True)
        self.rotation_input.setPrefix("Rotation  ")
        self.rotation_input.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.rotation_input.setToolTip("Any angle; scroll or use the arrow keys to nudge by 15\u00b0")
        self.rotation_input.valueChanged.connect(self._set_rotation)
        rows.addWidget(self.rotation_input)
        return rows

    def _build_tool_grid(self):
        grid = QGridLayout()
        grid.setSpacing(6)
        self._tool_buttons = QButtonGroup(self)
        for index, (tool, label, shortcut, tooltip) in enumerate(TOOL_BUTTONS):
            button = QToolButton(text=label, checkable=True, icon=tool_icon(tool), iconSize=QSize(22, 22))
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            button.setShortcut(QKeySequence(shortcut))
            button.setToolTip(f"{tooltip}  ({shortcut})")
            button.setChecked(tool is self.editor.tool)
            button.clicked.connect(lambda _=False, t=tool: self._set_tool(t))
            self._tool_buttons.addButton(button)
            grid.addWidget(button, index // 2, index % 2)
        return grid

    def _build_timing_inputs(self):
        row = QHBoxLayout()
        self.move_input = _seconds_input("Move ", DEFAULT_MOVE_SECONDS,
                                         "How long pieces take to glide into this step")
        self.hold_input = _seconds_input("Hold ", DEFAULT_HOLD_SECONDS,
                                         "How long to pause once everyone has arrived")
        row.addWidget(self.move_input)
        row.addWidget(self.hold_input)
        return row

    # ============================================================== menus ==
    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        _add_action(file_menu, self, "&New play", QKeySequence.New, self.new_play)
        _add_action(file_menu, self, "&Open\u2026", QKeySequence.Open, self.open_play)
        self.recent_files_menu = file_menu.addMenu("Open &recent")
        self.recent_files_menu.aboutToShow.connect(self._rebuild_recent_files_menu)
        file_menu.addSeparator()
        _add_action(file_menu, self, "&Save", QKeySequence.Save, self.save_play)
        _add_action(file_menu, self, "Save &as\u2026", QKeySequence.SaveAs, self.save_play_as)
        file_menu.addSeparator()
        _add_action(file_menu, self, "Export &MP4\u2026", "Ctrl+E", lambda: self.export('mp4'))
        _add_action(file_menu, self, "Export &GIF\u2026", "Ctrl+Shift+E", lambda: self.export('gif'))
        file_menu.addSeparator()
        _add_action(file_menu, self, "&Quit", QKeySequence.Quit, self.close)

        edit_menu = self.menuBar().addMenu("&Edit")
        _add_action(edit_menu, self, "&Undo last action", QKeySequence.Undo, self.undo_last_action)
        _add_action(edit_menu, self, "Remove last &step", "Ctrl+Shift+Backspace", self.remove_last_step)

        play_menu = self.menuBar().addMenu("&Play")
        _add_action(play_menu, self, "&Add step", "Ctrl+Return", self.add_step)
        _add_action(play_menu, self, "&Preview", "F5", self.preview)

        help_menu = self.menuBar().addMenu("&Help")
        _add_action(help_menu, self, "&About", None, self._show_about)

    # ======================================================= field / tools ==
    def _set_field_mode(self, mode):
        self.editor.field_mode = mode
        self.board.update()
        self._refresh_unsaved_indicator()

    def _set_rotation(self, degrees):
        self.editor.rotation_deg = degrees
        self.board.update()
        self._refresh_unsaved_indicator()

    def _set_draw_team(self, team):
        self.editor.draw_team = team

    def _set_tool(self, tool):
        self.editor.set_tool(tool)
        self.board.refresh_cursor()

    def _on_board_edited(self):
        self.board.update()
        self._refresh_unsaved_indicator()

    # ============================================================== steps ==
    def add_step(self):
        self.editor.commit_step(self.move_input.value(), self.hold_input.value())
        self._refresh_steps_list()
        self.board.update()
        self._show_status(f"Step {len(self.editor.steps.steps)} added.")

    def undo_last_action(self):
        undone = self.editor.undo_last_action()
        self.board.update()
        self._show_status("Undid last action." if undone else "Nothing to undo in this step.")

    def remove_last_step(self):
        removed = self.editor.remove_last_step()
        self._refresh_steps_list()
        self._show_status("Removed last step." if removed else "There are no steps to remove.")

    def delete_selected_step(self):
        row = self.steps_list.currentRow()
        if row < 0:
            return
        self.editor.delete_step(row)
        self._refresh_steps_list()
        self._show_status(f"Deleted step {row + 1}.")

    def apply_timing_to_selected_step(self):
        row = self.steps_list.currentRow()
        if row < 0:
            return
        self.editor.set_step_timing(row, self.move_input.value(), self.hold_input.value())
        self._refresh_steps_list(keep_row=row)
        self._show_status(f"Updated timing for step {row + 1}.")

    def _on_step_selected(self, row):
        has_selection = row >= 0
        self.apply_timing_button.setEnabled(has_selection)
        self.delete_step_button.setEnabled(has_selection)
        if has_selection:
            step = self.editor.steps.steps[row]
            self.move_input.setValue(step.move_duration)
            self.hold_input.setValue(step.hold_duration)

    def _refresh_steps_list(self, keep_row=-1):
        self.steps_list.blockSignals(True)
        self.steps_list.clear()
        for number, step in enumerate(self.editor.steps.steps, start=1):
            timing = f"hold {step.hold_duration:.1f}s"
            if number > 1:
                timing = f"move {step.move_duration:.1f}s  ·  {timing}"
            self.steps_list.addItem(f"Step {number}    {timing}")
        if not self.editor.steps.steps:
            self.steps_list.addItem("No steps yet")
            self.steps_list.item(0).setFlags(Qt.NoItemFlags)
        self.steps_list.setCurrentRow(keep_row)
        self.steps_list.blockSignals(False)
        self._on_step_selected(keep_row)
        self._refresh_unsaved_indicator()

    # ============================================================ preview ==
    def preview(self):
        if self.board.start_preview():
            self.board.setFocus()
            self._show_status("Previewing. Click the field or press Esc to stop.")
        else:
            self._show_status("Add at least one step first.")

    # ============================================================= export ==
    def export(self, video_format):
        if not self.editor.steps.steps:
            self._show_status("Add at least one step first.")
            return
        suggested = os.path.join(self._remembered_directory(LAST_EXPORT_DIR_KEY, EXPORTS_DIR),
                                 f"{self._play_display_name()}.{video_format}")
        path = self._ask_save_path(f"Export {video_format.upper()}", suggested,
                                   VIDEO_FILE_FILTERS[video_format], f".{video_format}")
        if not path:
            return
        self._remember_directory(LAST_EXPORT_DIR_KEY, path)
        frames = generate_timeline_frames(self.editor.steps.steps, fps=EXPORT_FPS)

        progress = QProgressDialog(f"Rendering {video_format.upper()}…", "Cancel", 0, len(frames), self)
        progress.setWindowTitle("Exporting")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        try:
            export_video(self._render_export_frames(frames, progress), path, EXPORT_FPS, video_format)
        except ExportCancelled:
            _remove_if_exists(path)
            self._show_status("Export cancelled.")
            return
        except Exception as error:
            _remove_if_exists(path)
            self._show_warning("Export failed", f"Couldn't export the video:\n\n{error}")
            return
        finally:
            progress.close()
        self._show_status(f"Exported {len(frames)} frames to {path}")

    def _render_export_frames(self, frames, progress):
        """Yield one rendered image per frame, keeping the progress dialog current."""
        label_font = piece_label_font()
        for index, (positions, annotations) in enumerate(frames):
            if progress.wasCanceled():
                raise ExportCancelled()
            progress.setValue(index)
            yield render_frame_image(EXPORT_WIDTH, EXPORT_HEIGHT, self.editor.field_mode,
                                     self.editor.rotation_deg, self.editor.pieces,
                                     positions, annotations, label_font)
        progress.setValue(len(frames))

    # ===================================================== open / save ==
    def new_play(self):
        if not self._confirm_discard_unsaved_changes():
            return
        self.editor.new_play()
        self.current_file_path = None
        self._sync_controls_with_editor()
        self._mark_current_state_as_saved()
        self._show_status("Started a new play.")

    def open_play(self):
        """Ask for a play file and open it."""
        if not self._confirm_discard_unsaved_changes():
            return
        path = self._ask_open_path("Open play", self._remembered_directory(LAST_PLAY_DIR_KEY, SAVES_DIR),
                                   PLAY_FILE_FILTER)
        if path:
            self._load_play_from(path)

    def open_play_file(self, path):
        """Open a specific file (recent-files menu, drag-and-drop, command line)."""
        if self._confirm_discard_unsaved_changes():
            self._load_play_from(path)

    def save_play(self):
        """Save to the play's current file, asking for one if it has none.
        Returns True if the play was saved."""
        if self.current_file_path is None:
            return self.save_play_as()
        return self._write_play_to(self.current_file_path)

    def save_play_as(self):
        """Ask where to save the play, then save it there. Returns True if saved."""
        suggested = self.current_file_path or os.path.join(
            self._remembered_directory(LAST_PLAY_DIR_KEY, SAVES_DIR),
            UNTITLED_PLAY_NAME + persistence.PLAY_FILE_SUFFIX)
        path = self._ask_save_path("Save play as", suggested, PLAY_FILE_FILTER, persistence.PLAY_FILE_SUFFIX)
        return bool(path) and self._write_play_to(path)

    def _load_play_from(self, path):
        try:
            self.editor.replace_play(*persistence.load_play(path))
        except FileNotFoundError:
            self._forget_recent_file(path)
            self._show_warning("File not found", f"{path}\n\nno longer exists.")
            return
        except Exception as error:
            self._show_warning("Couldn't open play",
                               f"{os.path.basename(path)} isn't a readable play file.\n\n{error}")
            return
        self.current_file_path = path
        self._sync_controls_with_editor()
        self._mark_current_state_as_saved()
        self._remember_file(path)
        self._show_status(f"Opened {path}")

    def _write_play_to(self, path):
        try:
            persistence.save_play(path, self.editor.pieces, self.editor.steps,
                                  self.editor.field_mode, self.editor.rotation_deg)
        except OSError as error:
            self._show_warning("Couldn't save play", f"Couldn't write {path}:\n\n{error}")
            return False
        self.current_file_path = path
        self._mark_current_state_as_saved()
        self._remember_file(path)
        self._show_status(f"Saved {path}")
        return True

    def _sync_controls_with_editor(self):
        """Update widgets after the editor's state was replaced wholesale."""
        for button in self._field_mode_buttons.buttons():
            button.setChecked(button.property("value") == self.editor.field_mode)
        self.rotation_input.blockSignals(True)
        self.rotation_input.setValue(self.editor.rotation_deg)
        self.rotation_input.blockSignals(False)
        self._refresh_steps_list()
        self.board.update()

    # ================================================== unsaved changes ==
    def _current_play_snapshot(self):
        return persistence.serialize_play(self.editor.pieces, self.editor.steps,
                                          self.editor.field_mode, self.editor.rotation_deg)

    def _mark_current_state_as_saved(self):
        self._saved_snapshot = self._current_play_snapshot()
        self._refresh_window_title()

    def has_unsaved_changes(self):
        """True if the play differs from what was last saved or opened.
        Comparing snapshots (rather than flagging every edit) means undoing
        back to the saved state correctly counts as "no changes"."""
        return self._current_play_snapshot() != self._saved_snapshot

    def _refresh_unsaved_indicator(self):
        if hasattr(self, "_saved_snapshot"):
            self.setWindowModified(self.has_unsaved_changes())

    def _refresh_window_title(self):
        # Qt replaces "[*]" with an asterisk (or the macOS dot) while modified.
        self.setWindowTitle(f"{self._play_display_name()}[*] \u2014 {APP_NAME}")
        self._refresh_unsaved_indicator()

    def _play_display_name(self):
        if self.current_file_path is None:
            return UNTITLED_PLAY_NAME
        return os.path.splitext(os.path.basename(self.current_file_path))[0]

    def _confirm_discard_unsaved_changes(self):
        """Offer to save unsaved changes. Returns False if the user cancelled."""
        if not self.has_unsaved_changes():
            return True
        choice = self._ask_save_changes()
        if choice == QMessageBox.Save:
            return self.save_play()
        return choice == QMessageBox.Discard

    # ======================================================= recent files ==
    def recent_files(self):
        return [path for path in (self.settings.value(RECENT_FILES_KEY) or []) if path]

    def _remember_file(self, path):
        path = os.path.abspath(path)
        recent = [path] + [p for p in self.recent_files() if p != path]
        self.settings.setValue(RECENT_FILES_KEY, recent[:MAX_RECENT_FILES])
        self._remember_directory(LAST_PLAY_DIR_KEY, path)

    def _forget_recent_file(self, path):
        path = os.path.abspath(path)
        self.settings.setValue(RECENT_FILES_KEY, [p for p in self.recent_files() if p != path])

    def _rebuild_recent_files_menu(self):
        self.recent_files_menu.clear()
        for path in self.recent_files():
            action = self.recent_files_menu.addAction(os.path.basename(path))
            action.setToolTip(path)
            action.triggered.connect(lambda _=False, p=path: self.open_play_file(p))
        if self.recent_files_menu.isEmpty():
            self.recent_files_menu.addAction("No recent plays").setEnabled(False)

    # ================================================ dialogs and folders ==
    # Each native dialog is wrapped in one small method so tests can replace it.
    def _ask_open_path(self, title, directory, file_filter):
        path, _ = QFileDialog.getOpenFileName(self, title, directory, file_filter)
        return path

    def _ask_save_path(self, title, suggested_path, file_filter, required_suffix):
        """Native save dialog. Adds `required_suffix` if the user left it off."""
        path, _ = QFileDialog.getSaveFileName(self, title, suggested_path, file_filter)
        if path and not path.lower().endswith(required_suffix):
            path += required_suffix
        return path

    def _show_warning(self, title, message):
        QMessageBox.warning(self, title, message)

    def _ask_save_changes(self):
        return QMessageBox.question(
            self, "Unsaved changes",
            f"Save changes to \u201c{self._play_display_name()}\u201d before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)

    def _remembered_directory(self, key, fallback):
        """Last folder used for this kind of file, else `fallback` (created
        if needed), else the home folder if `fallback` can't be created."""
        directory = self.settings.value(key)
        if directory and os.path.isdir(directory):
            return directory
        try:
            os.makedirs(fallback, exist_ok=True)
            return fallback
        except OSError:
            return os.path.expanduser("~")

    def _remember_directory(self, key, file_path):
        self.settings.setValue(key, os.path.dirname(os.path.abspath(file_path)))

    # ===================================================== drag and drop ==
    def dragEnterEvent(self, event):
        if self._dropped_play_path(event) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = self._dropped_play_path(event)
        if path is not None:
            event.acceptProposedAction()
            self.open_play_file(path)

    @staticmethod
    def _dropped_play_path(event):
        """Path of the first local play file being dragged in, or None."""
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(persistence.PLAY_FILE_SUFFIX):
                return url.toLocalFile()
        return None

    # ============================================================== misc ==
    def _show_status(self, message):
        self.statusBar().showMessage(message)

    def _show_about(self):
        QMessageBox.about(self, f"About {APP_NAME}",
                          f"<b>{APP_NAME}</b> {APP_VERSION}<br>"
                          "Draw lacrosse plays and export them as video.<br><br>"
                          "By <a href='https://github.com/TCurrie11'>TCurrie11</a>")

    def closeEvent(self, event):
        if not self._confirm_discard_unsaved_changes():
            event.ignore()
            return
        self.board.stop_preview()
        super().closeEvent(event)


# ======================================================== widget helpers ==
def _section_heading(text):
    label = QLabel(text)
    label.setProperty("role", "section")
    return label


def _button(text, on_click, role=None):
    button = QPushButton(text)
    button.clicked.connect(lambda _=False: on_click())
    if role:
        button.setProperty("role", role)
    return button


def _seconds_input(prefix, value, tooltip):
    spin = QDoubleSpinBox(minimum=MIN_STEP_SECONDS, maximum=60, decimals=2, singleStep=0.25,
                          value=value, prefix=prefix, suffix=" s")
    spin.setToolTip(f"{tooltip}. Scroll or use the arrow keys to adjust.")
    spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
    return spin


def _exclusive_toggle_row(parent_layout, options, current_value, on_change) -> QButtonGroup:
    """A row of checkable buttons where exactly one is on, like a segmented control.
    `options` is a list of (label, value) pairs."""
    row = QHBoxLayout()
    group = QButtonGroup(parent_layout)
    for label, value in options:
        button = QToolButton(text=label, checkable=True)
        button.setProperty("value", value)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button.setChecked(value == current_value)
        button.clicked.connect(lambda _=False, v=value: on_change(v))
        group.addButton(button)
        row.addWidget(button)
    parent_layout.addLayout(row)
    return group


def _add_action(menu, owner, text, shortcut, on_trigger):
    action = QAction(text, owner)
    if shortcut is not None:
        action.setShortcut(QKeySequence(shortcut))
    action.triggered.connect(lambda _=False: on_trigger())
    menu.addAction(action)
    return action


def _remove_if_exists(path):
    if os.path.exists(path):
        os.remove(path)
