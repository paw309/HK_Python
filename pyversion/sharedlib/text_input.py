"""
Reusable Pygame TextInput box, ideal for puzzle or share-code input.

Usage:
    from text_input import TextInput
    ...
    input_box = TextInput(pygame.Rect(...), font, max_length=16)
    ...
    # In event loop:
        input_box.handle_event(event)
        input_box.update(dt)
        input_box.draw(screen)
    # To get/set value:
        code = input_box.get_text()
        input_box.set_text("ABCD...")
"""

import pygame
from typing import Optional


class TextInput:
    """Simple reusable text input box for limited, formatted codes.

    Set `max_length` as needed. By default, restricts to base32 without dashes.
    """

    def __init__(
            self,
            rect: pygame.Rect,
            font: pygame.font.Font,
            max_length: int = 19,
            bg_color=(232, 200, 150),
            text_color=(0, 0, 0),
            cursor_color=(0, 0, 0),
            dash_positions=(4, 8, 12),
    ):
        """
        Args:
            rect: Bounding rectangle for the input box.
            font: Pygame font used to render text.
            max_length: Maximum total character count including dashes.
            bg_color: Background fill colour.
            text_color: Text colour.
            cursor_color: Blinking cursor colour.
            dash_positions: Raw-character positions (excluding dashes) after which a
                dash is automatically inserted.  The default (4, 8, 12) matches the
                standard XXXX-XXXX-XXXX-XXXX share-code format (16 payload chars,
                19 chars total with dashes).  Pass (2, 7) for the megalomino
                NN-CCCCC-CCCCC format.
        """
        self.rect = rect
        self.font = font
        self.max_length = max_length
        self.text = ""
        self.active = False
        self.cursor_pos = 0
        self.cursor_visible = True
        self.cursor_timer = 0
        self.bg_color = bg_color
        self.text_color = text_color
        self.cursor_color = cursor_color
        self.dash_positions = dash_positions

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process a single event. Returns True if the text was changed."""
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
            elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                try:
                    import pyperclip
                    paste_text = pyperclip.paste()
                    # Strip dashes and surrounding whitespace so auto-dash logic re-formats cleanly
                    paste_text = paste_text.replace('-', '').strip()
                    self.insert_text(paste_text)
                    return True
                except Exception:
                    pass
            elif event.key == pygame.K_a and (event.mod & pygame.KMOD_CTRL):
                self.cursor_pos = len(self.text)
            elif event.unicode and event.unicode.isprintable():
                self.insert_text(event.unicode)
                return True

        return False

    def insert_text(self, text: str) -> None:
        """Insert text at cursor position, formatting as share-code (0-9, A-Z, auto-dash insertion)"""
        for char in text:
            if len(self.text) >= self.max_length:
                break
            if char == '-':
                # Allow explicit dashes to be typed/pasted, but don't double-insert
                if self.cursor_pos > 0 and self.text[self.cursor_pos - 1] != '-':
                    if len(self.text) < self.max_length:
                        self.text = self.text[:self.cursor_pos] + '-' + self.text[self.cursor_pos:]
                        self.cursor_pos += 1
                continue
            char = char.upper()
            # Allow base-36 chars: digits 0-9 and letters A-Z
            if char not in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                continue
            self.text = self.text[:self.cursor_pos] + char + self.text[self.cursor_pos:]
            self.cursor_pos += 1
            # Auto-insert dashes at configured positions (counted in raw chars)
            raw_len = len(self.text.replace('-', ''))
            if raw_len in self.dash_positions and self.cursor_pos < self.max_length:
                # Only insert dash if not already there
                if self.cursor_pos < len(self.text) and self.text[self.cursor_pos] != '-':
                    self.text = self.text[:self.cursor_pos] + '-' + self.text[self.cursor_pos:]
                    self.cursor_pos += 1
                elif self.cursor_pos == len(self.text):
                    self.text = self.text + '-'
                    self.cursor_pos += 1

    def update(self, dt: int) -> None:
        """Update the cursor blink animation."""
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer >= 530:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0
        else:
            self.cursor_visible = True
            self.cursor_timer = 0

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the input box."""
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
            if not self.active:
                placeholder = self.font.render("e.g. 16-4RH0B-00017", True, (128, 128, 128))
                surface.blit(placeholder, placeholder.get_rect(center=self.rect.center))
            elif self.cursor_visible:
                cursor_x = self.rect.centerx
                cursor_y_top = self.rect.centery - self.font.get_height() // 2
                cursor_y_bottom = self.rect.centery + self.font.get_height() // 2
                pygame.draw.line(surface, self.cursor_color,
                                 (cursor_x, cursor_y_top),
                                 (cursor_x, cursor_y_bottom), 2)

    def get_text(self) -> str:
        """Return text with dashes removed."""
        return self.text.replace('-', '')

    def set_text(self, text: str) -> None:
        """Set text, auto-formatting as code."""
        self.text = ""
        self.cursor_pos = 0
        self.insert_text(text)