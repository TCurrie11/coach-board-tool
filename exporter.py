"""Turn a list of rendered pygame Surfaces into an MP4 or GIF file."""
import pygame


def _surface_to_array(surface):
    arr = pygame.surfarray.array3d(surface)
    return arr.swapaxes(0, 1)  # pygame is (w, h, 3); video libs want (h, w, 3)


def export_mp4(frame_surfaces, path, fps=30):
    import imageio
    writer = imageio.get_writer(path, fps=fps, codec='libx264', quality=8, macro_block_size=None)
    try:
        for surf in frame_surfaces:
            writer.append_data(_surface_to_array(surf))
    finally:
        writer.close()


def export_gif(frame_surfaces, path, fps=30):
    import imageio
    images = [_surface_to_array(s) for s in frame_surfaces]
    imageio.mimsave(path, images, duration=1.0 / fps)
