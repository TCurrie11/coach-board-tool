# PyInstaller spec for Coach Board Tool.
# Build with:  pyinstaller coach_board_tool.spec
#
# IMPORTANT: before building, run the app (or the one-liner below) at least
# once so imageio-ffmpeg has downloaded its ffmpeg binary into its own
# package folder - that's what lets this spec bundle ffmpeg INTO the exe,
# so end users never need internet access or a separate ffmpeg install:
#
#   python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
#
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

for pkg in ('pygame', 'imageio_ffmpeg', 'imageio'):
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
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

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
