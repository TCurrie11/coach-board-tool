"""
exporter.py - Writes rendered frames out as an MP4 or GIF file.
===============================================================

Frames arrive one at a time as QImages and are streamed straight into the
encoder, so a long play never needs every frame in memory at once. MP4 uses
imageio's bundled ffmpeg (H.264); GIF uses Pillow via imageio.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
    2.0.0  2026-10-14  TCurrie11  Streams QImage frames; fixed GIF frame delay (was passed in seconds, imageio expects ms).
"""
from typing import Iterable

import numpy as np
from PySide6.QtGui import QImage

SUPPORTED_FORMATS = ('mp4', 'gif')
MP4_QUALITY = 8  # imageio scale 0-10


def qimage_to_rgb_array(image: QImage) -> np.ndarray:
    """Copy a QImage into a (height, width, 3) uint8 RGB array."""
    rgb = image.convertToFormat(QImage.Format_RGB888)
    width, height = rgb.width(), rgb.height()
    rows = np.frombuffer(rgb.constBits(), np.uint8).reshape(height, rgb.bytesPerLine())
    return rows[:, :width * 3].reshape(height, width, 3).copy()


def export_video(frames: Iterable[QImage], path, fps, video_format):
    """Encode `frames` into `path` as 'mp4' or 'gif'."""
    import imageio  # imported lazily: it is slow to load and only needed here

    if video_format == 'mp4':
        writer = imageio.get_writer(path, fps=fps, codec='libx264',
                                    quality=MP4_QUALITY, macro_block_size=None)
    elif video_format == 'gif':
        # GIF delays are stored in 1/100 s units, so 30 fps becomes ~33 ms.
        writer = imageio.get_writer(path, mode='I', duration=1000 / fps, loop=0)
    else:
        raise ValueError(f"Unsupported video format {video_format!r}; expected one of {SUPPORTED_FORMATS}")

    try:
        for frame in frames:
            writer.append_data(qimage_to_rgb_array(frame))
    finally:
        writer.close()
