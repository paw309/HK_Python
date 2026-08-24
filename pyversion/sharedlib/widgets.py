"""
Reusable UI widgets for Pygame games: Button, TextInput, move overlays.

Classes:
    - Button: Basic clickable button UI element
    - TextInput: Simple text entry box with optional base32 validation
    - MoveTrackOverlay: Draws numbers at tracked move positions on a grid
    - MoveGuideOverlay: Draws arrows pointing to legal move destinations on a grid

Usage:
    - Import in your game: from sharedlib.widget import Button, TextInput, MoveTrackOverlay, MoveGuideOverlay
    - Use object methods for draw and event handling.

Dependencies:
    - pygame
"""

import pygame
from typing import Tuple, Callable, Optional, Dict, Any, Set, List

class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        text_color: Tuple[int, int, int] = (255, 255, 255),
        bg_color: Tuple[int, int, int] = (0, 128, 255),
        on_click: Optional[Callable[[], None]] = None,
        active: bool = True,
    ):
        self.rect = rect
        self.text = text
        self.font = font
        self.text_color = text_color
        self.bg_color = bg_color
        self.on_click = on_click
        self.active = active
        self.disabled_color = (128, 128, 128)
        self.disabled_text_color = (180, 180, 180)

    def draw(self, surface: pygame.Surface) -> None:
        color = self.bg_color if self.active else self.disabled_color
        text_color = self.text_color if self.active else self.disabled_text_color
        pygame.draw.rect(surface, color, self.rect)
        label = self.font.render(self.text, True, text_color)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()

class TextInput:
    """
    Simple text input box for Pygame.
    By default, allows only base32 (A-Z, 2-7) and uppercases input.
    Provides blinking cursor and basic mouse/keyboard event handling.
    """
    def __init__(
        self,
        rect: pygame.Rect,
        font: pygame.font.Font,
        max_length: int = 19,
        allowed_chars: Optional[str] = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567',
        placeholder: str = "enter text",
        bg_color: Tuple[int, int, int] = (232, 200, 150),
        text_color: Tuple[int, int, int] = (0, 0, 0),
        cursor_color: Tuple[int, int, int] = (0, 0, 0),
    ):
        self.rect = rect
        self.font = font
        self.max_length = max_length
        self.allowed_chars = allowed_chars
        self.placeholder = placeholder
        self.bg_color = bg_color
        self.text_color = text_color
        self.cursor_color = cursor_color

        self.text = ""
        self.active = False
        self.cursor_pos = 0
        self.cursor_visible = True
        self.cursor_timer = 0

    def insert_text(self, text: str) -> None:
        for char in text.upper():
            if len(self.text) >= self.max_length:
                break
            if self.allowed_chars and char not in self.allowed_chars:
                continue
            self.text = self.text[:self.cursor_pos] + char + self.text[self.cursor_pos:]
            self.cursor_pos += 1

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if text changed"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            return False

        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
                    return True
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
                    return True
            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
            elif event.key == pygame.K_HOME:
                self.cursor_pos = 0
            elif event.key == pygame.K_END:
                self.cursor_pos = len(self.text)
            elif event.unicode and event.unicode.isprintable():
                self.insert_text(event.unicode)
                return True

        return False

    def update(self, dt: int) -> None:
        """Call once per frame with milliseconds elapsed to update cursor blink."""
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer >= 530:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0
        else:
            self.cursor_visible = True
            self.cursor_timer = 0

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, self.bg_color, self.rect)
        border_color = (100, 100, 255) if self.active else (107, 70, 51)
        pygame.draw.rect(surface, border_color, self.rect, 2)
        if self.text:
            text_surf = self.font.render(self.text, True, self.text_color)
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)
            if self.active and self.cursor_visible:
                text_before_cursor = self.text[:self.cursor_pos]
                cursor_x_offset = self.font.size(text_before_cursor)[0]
                cursor_x = text_rect.left + cursor_x_offset
                cursor_y_top = text_rect.top
                cursor_y_bottom = text_rect.bottom
                pygame.draw.line(surface, self.cursor_color,
                                 (cursor_x, cursor_y_top),
                                 (cursor_x, cursor_y_bottom), 2)
        else:
            # Draw placeholder text when inactive
            if not self.active:
                placeholder = self.font.render(self.placeholder, True, (128, 128, 128))
                surface.blit(placeholder, placeholder.get_rect(center=self.rect.center))
            elif self.cursor_visible:
                cursor_x = self.rect.centerx
                cursor_y_top = self.rect.centery - self.font.get_height() // 2
                cursor_y_bottom = self.rect.centery + self.font.get_height() // 2
                pygame.draw.line(surface, self.cursor_color,
                                 (cursor_x, cursor_y_top),
                                 (cursor_x, cursor_y_bottom), 2)

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = ""
        self.cursor_pos = 0
        self.insert_text(text)

class MoveTrackOverlay:
    """
    Draws move numbers at visited positions on a board/grid.
    Usage:
        overlay = MoveTrackOverlay(track_data, font)
        overlay.draw(surface, board_renderer, cell_size)
    """
    def __init__(
        self,
        track_data: Dict[Tuple[int, int], int],   # (grid_x, grid_y): move_number
        font: pygame.font.Font,
        text_color: Tuple[int, int, int] = (0, 0, 0)
    ):
        self.track_data = track_data
        self.font = font
        self.text_color = text_color

    def draw(self, surface: pygame.Surface, board_renderer: Any, cell_size: int):
        for (gx, gy), move_num in self.track_data.items():
            px, py = board_renderer.to_pixel(gx, gy)
            num_surf = self.font.render(str(move_num), True, self.text_color)
            num_rect = num_surf.get_rect(center=(px + cell_size // 2, py + cell_size // 2))
            surface.blit(num_surf, num_rect)

class MoveGuideOverlay:
    """
    Draws arrows pointing to legal move destinations from a current board position.
    Usage:
        overlay = MoveGuideOverlay(arrows_dict)
        overlay.draw(surface, legal_moves, player_pos, board_renderer, cell_size)
    """
    def __init__(
        self,
        arrow_images: Dict[Tuple[int, int], pygame.Surface]  # (dx, dy): surface
    ):
        self.arrow_images = arrow_images

    def draw(
        self,
        surface: pygame.Surface,
        legal_moves: List[Tuple[int, int]],
        player_pos: Tuple[int, int],
        board_renderer: Any,
        cell_size: int
    ):
        px_pos, py_pos = player_pos
        for mx, my in legal_moves:
            dx, dy = mx - px_pos, my - py_pos
            # Clamp difference to direction vector
            norm_dx = int(max(-1, min(1, dx)))
            norm_dy = int(max(-1, min(1, dy)))
            direction_key = (norm_dx, norm_dy)
            arrow_surface = self.arrow_images.get(direction_key)
            if arrow_surface:
                grid_px, grid_py = board_renderer.to_pixel(mx, my)
                arrow_rect = arrow_surface.get_rect(center=(grid_px + cell_size // 2, grid_py + cell_size // 2))
                surface.blit(arrow_surface, arrow_rect)

