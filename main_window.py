"""
main_window.py - The application window: board, sidebar, menus, status bar.
===========================================================================

Builds the sidebar controls and menus and wires them to the `PlayEditor`
and `BoardView`. Holds no editing rules of its own - it reads values from
widgets, calls the editor, and refreshes what's shown.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    2.0.0  2026-10-14  TCurrie11  Initial version; replaces the pygame sidebar from app.py (1.x).
"""
import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractSpinBox, QButtonGroup, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMainWindow, QMessageBox, QProgressDialog, QPushButton, QScrollArea, QSizePolicy, QToolButton,
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
DEFAULT_PLAY_NAME = "my_play"


class ExportCancelled(Exception):
    """Raised inside the frame generator when the user cancels an export."""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
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
        export_row.addWidget(_button("Export MP4", lambda: self.export('mp4')))
        export_row.addWidget(_button("Export GIF", lambda: self.export('gif')))
        column.addLayout(export_row)

        column.addWidget(_section_heading("FILE"))
        self.play_name_input = QLineEdit(DEFAULT_PLAY_NAME)
        self.play_name_input.setPlaceholderText("Play name")
        column.addWidget(self.play_name_input)
        file_row = QHBoxLayout()
        file_row.addWidget(_button("Save play", self.save_play))
        file_row.addWidget(_button("Load play", self.load_play))
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
        _add_action(file_menu, self, "&Save play", QKeySequence.Save, self.save_play)
        _add_action(file_menu, self, "&Load play", QKeySequence.Open, self.load_play)
        file_menu.addSeparator()
        _add_action(file_menu, self, "Export &MP4", "Ctrl+E", lambda: self.export('mp4'))
        _add_action(file_menu, self, "Export &GIF", "Ctrl+Shift+E", lambda: self.export('gif'))
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

    def _set_rotation(self, degrees):
        self.editor.rotation_deg = degrees
        self.board.update()

    def _set_draw_team(self, team):
        self.editor.draw_team = team

    def _set_tool(self, tool):
        self.editor.set_tool(tool)
        self.board.refresh_cursor()

    def _on_board_edited(self):
        self.board.update()

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
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, f"{self._play_name()}.{video_format}")
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
            QMessageBox.warning(self, "Export failed", f"Couldn't export the video:\n\n{error}")
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

    # ======================================================== save / load ==
    def save_play(self):
        os.makedirs(SAVES_DIR, exist_ok=True)
        path = os.path.join(SAVES_DIR, f"{self._play_name()}.json")
        persistence.save_play(path, self.editor.pieces, self.editor.steps,
                              self.editor.field_mode, self.editor.rotation_deg)
        self._show_status(f"Saved to {path}")

    def load_play(self):
        path = os.path.join(SAVES_DIR, f"{self._play_name()}.json")
        try:
            self.editor.replace_play(*persistence.load_play(path))
        except FileNotFoundError:
            self._show_status(f"No saved play at {path}")
            return
        except Exception as error:
            QMessageBox.warning(self, "Load failed", f"Couldn't load {path}:\n\n{error}")
            return
        self._sync_controls_with_editor()
        self._show_status(f"Loaded {path}")

    def _sync_controls_with_editor(self):
        """Update widgets after the editor's state was replaced wholesale."""
        for button in self._field_mode_buttons.buttons():
            button.setChecked(button.property("value") == self.editor.field_mode)
        self.rotation_input.blockSignals(True)
        self.rotation_input.setValue(self.editor.rotation_deg)
        self.rotation_input.blockSignals(False)
        self._refresh_steps_list()
        self.board.update()

    def _play_name(self):
        return self.play_name_input.text().strip() or DEFAULT_PLAY_NAME

    # ============================================================== misc ==
    def _show_status(self, message):
        self.statusBar().showMessage(message)

    def _show_about(self):
        QMessageBox.about(self, f"About {APP_NAME}",
                          f"<b>{APP_NAME}</b> {APP_VERSION}<br>"
                          "Draw lacrosse plays and export them as video.<br><br>"
                          "By <a href='https://github.com/TCurrie11'>TCurrie11</a>")

    def closeEvent(self, event):
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
