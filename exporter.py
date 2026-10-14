"""
exporter.py - Writes rendered frames out as an MP4 or GIF file.
===============================================================

Takes the pygame Surfaces produced by `scene.compose_frame` and hands
them to imageio (with its bundled ffmpeg for MP4).

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    1.0.0  2026-09-15  TCurrie11  Initial release.
    1.1.1  2026-10-14  TCurrie11  Added file header, version history and docstrings.
"""
import pygame


def _surface_to_array(surface):
    """Convert a pygame Surface to an (height, width, 3) array, the layout video libraries expect."""
    arr = pygame.surfarray.array3d(surface)
    return arr.swapaxes(0, 1)  # pygame is (w, h, 3); video libs want (h, w, 3)


def export_mp4(frame_surfaces, path, fps=30):
    """Encode the frames as an H.264 MP4 at `path`."""
    import imageio
    writer = imageio.get_writer(path, fps=fps, codec='libx264', quality=8, macro_block_size=None)
    try:
        for surf in frame_surfaces:
            writer.append_data(_surface_to_array(surf))
    finally:
        writer.close()


def export_gif(frame_surfaces, path, fps=30):
    """Encode the frames as an animated GIF at `path`."""
    import imageio
    images = [_surface_to_array(s) for s in frame_surfaces]
    imageio.mimsave(path, images, duration=1.0 / fps)
