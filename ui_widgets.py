"""Minimal, dependency-free UI widgets for the sidebar."""
import pygame
from config import PANEL_TEXT, BUTTON_BG, BUTTON_BG_ACTIVE, BUTTON_BORDER


class Button:
    def __init__(self, rect, label, callback, active_check=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.active_check = active_check

    def draw(self, surface, font):
        active = bool(self.active_check()) if self.active_check else False
        bg = BUTTON_BG_ACTIVE if active else BUTTON_BG
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, BUTTON_BORDER, self.rect, 1, border_radius=6)
        txt = font.render(self.label, True, PANEL_TEXT)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.callback()
            return True
        return False


class TextInput:
    def __init__(self, rect, initial="1.0", numeric=True):
        self.rect = pygame.Rect(rect)
        self.text = initial
        self.focused = False
        self.numeric = numeric

    def draw(self, surface, font):
        bg = (70, 70, 78) if self.focused else (48, 48, 52)
        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        pygame.draw.rect(surface, BUTTON_BORDER, self.rect, 1, border_radius=4)
        txt = font.render(self.text, True, PANEL_TEXT)
        surface.blit(txt, (self.rect.x + 6, self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle_click(self, pos):
        self.focused = self.rect.collidepoint(pos)
        return self.focused

    def handle_key(self, event):
        if not self.focused:
            return
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            self.focused = False
        else:
            ch = event.unicode
            if self.numeric:
                if ch.isdigit() or (ch == '.' and '.' not in self.text):
                    self.text += ch
                elif ch == '-' and self.text == '':
                    self.text += ch
            else:
                if ch.isprintable():
                    self.text += ch

    def value(self, default=1.0, min_value=None):
        try:
            v = float(self.text)
        except ValueError:
            return default
        if min_value is not None:
            v = max(min_value, v)
        return v


class Layout:
    """Stacks rows/columns top-down in the sidebar without hand-computed pixels."""

    def __init__(self, x, y, w):
        self.x = x
        self.w = w
        self.y = y

    def row(self, h, gap=4):
        r = pygame.Rect(int(self.x), int(self.y), int(self.w), h)
        self.y += h + gap
        return r

    def split(self, h, n, gap=4):
        total_gap = gap * (n - 1)
        cw = (self.w - total_gap) / n
        rects = [pygame.Rect(int(self.x + i * (cw + gap)), int(self.y), int(cw), h) for i in range(n)]
        self.y += h + gap
        return rects

    def space(self, h):
        self.y += h
