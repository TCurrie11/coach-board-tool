"""
theme.py - Dark application theme.
==================================

Uses Qt's cross-platform Fusion style with a dark palette, plus a short
stylesheet for the details a palette can't express (rounded tool buttons,
section headings, the accent-coloured primary button). Looks the same on
Windows, macOS and Linux.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    2.0.0  2026-10-14  TCurrie11  Initial version.
"""
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

WINDOW = "#1e2024"
PANEL = "#26292e"
INPUT = "#1a1c20"
BORDER = "#3a3e45"
TEXT = "#e6e8eb"
MUTED_TEXT = "#9aa0a8"
ACCENT = "#3d7be0"
ACCENT_HOVER = "#5590ee"
DANGER = "#c94a4a"

STYLESHEET = f"""
QWidget#Sidebar {{ background: {PANEL}; }}
QScrollArea#SidebarScroll {{ border: none; background: {PANEL}; }}

QLabel[role="section"] {{
    color: {MUTED_TEXT};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    padding-top: 10px;
}}

QToolButton, QPushButton {{
    background: #31353b;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    color: {TEXT};
}}
QToolButton:hover, QPushButton:hover {{ background: #3a3f46; }}
QToolButton:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #6b7078; }}

QPushButton[role="primary"] {{ background: {ACCENT}; border-color: {ACCENT}; font-weight: 600; }}
QPushButton[role="primary"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[role="danger"]:hover {{ background: {DANGER}; border-color: {DANGER}; }}

QDoubleSpinBox, QLineEdit {{
    background: {INPUT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 3px 6px;
    color: {TEXT};
}}
QListWidget {{
    background: {INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
}}
QListWidget::item {{ padding: 5px 6px; }}
QListWidget::item:selected {{ background: {ACCENT}; border-radius: 4px; }}

QStatusBar {{ background: {PANEL}; color: {MUTED_TEXT}; }}
"""


def apply_dark_theme(app: QApplication):
    """Apply the Fusion style, dark palette and stylesheet to the whole app."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(WINDOW))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor(INPUT))
    palette.setColor(QPalette.AlternateBase, QColor(PANEL))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor(PANEL))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor(PANEL))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.PlaceholderText, QColor(MUTED_TEXT))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
