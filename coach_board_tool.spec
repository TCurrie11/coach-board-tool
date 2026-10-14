# =====================================================================
# coach_board_tool.spec - PyInstaller build recipe for Coach Board Tool.
#
# Author:  TCurrie11 (https://github.com/TCurrie11)
# Project: Coach Board Tool
#
# Version history:
#     1.0.0  2026-09-15  TCurrie11  Initial release.
#     1.1.0  2026-09-16  TCurrie11  macOS .app bundle (onedir + BUNDLE).
#     1.1.1  2026-10-14  TCurrie11  Added file header and version history.
#     2.0.0  2026-10-14  TCurrie11  Bundles PySide6 instead of pygame; excludes unused Qt modules.
# =====================================================================
#
# PyInstaller spec for Coach Board Tool.
# Build with:  pyinstaller coach_board_tool.spec
#
# IMPORTANT: before building, run the app (or the one-liner below) at least
# once so imageio-ffmpeg has downloaded its ffmpeg binary into its own
# package folder - that's what lets this spec bundle ffmpeg INTO the app,
# so end users never need internet access or a separate ffmpeg install:
#
#   python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
#
# On Windows this produces dist/CoachBoardTool.exe (single file).
# On macOS this produces dist/CoachBoardTool.app (a proper app bundle -
# onedir + BUNDLE launches noticeably faster than a onefile .app would).
#
# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# PySide6 is handled by PyInstaller's own built-in hook; only the video
# libraries need their data files (e.g. the ffmpeg binary) collected here.
for pkg in ('imageio_ffmpeg', 'imageio'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Qt modules the app never imports - leaving them out keeps the download small.
    excludes=[
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml',
        'PySide6.QtQuick', 'PySide6.Qt3DCore', 'PySide6.QtMultimedia',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtPdf',
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='CoachBoardTool',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        name='CoachBoardTool',
    )
    app = BUNDLE(
        coll,
        name='CoachBoardTool.app',
        icon=None,
        bundle_identifier='com.coachboardtool.app',
        info_plist={'NSHighResolutionCapable': 'True'},
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='CoachBoardTool',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
