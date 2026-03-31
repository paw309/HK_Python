from typing import Optional
from puzzle_codec import encode_params, decode_params, polyomino_schema


class CodecManager:
    """Manages puzzle code generation, validation, input, and clipboard operations."""

    def __init__(self):
        self.current_code: Optional[str] = None
        self.input_mode_active: bool = False
        self.decoded_params: Optional[dict] = None
        self.copy_clicked: bool = False
        self.input_widget = None  # Will be set from main (TextInput instance)

    def generate_code(self, selections: dict, seed: int) -> bool:
        """Generate code from current selections. Returns True on success."""
        try:
            self.current_code = encode_params(selections, polyomino_schema, seed)
            self.copy_clicked = False  # Reset copy state for new puzzle
            return True
        except (ValueError, KeyError) as e:
            print(f"Warning: Could not generate puzzle code: {e}")
            self.current_code = None
            return False

    def validate_input(self, text: str) -> tuple:
        """Validate input code. Returns (is_valid, decoded_params_or_None).

        Also updates self.decoded_params on success and clears it on failure.
        """
        try:
            params = decode_params(text, polyomino_schema)
            self.decoded_params = params
            return True, params
        except Exception:
            self.decoded_params = None
            return False, None

    def copy_to_clipboard(self) -> bool:
        """Copy current code to clipboard. Returns True on success."""
        if self.current_code and not self.copy_clicked:
            try:
                import pyperclip
                pyperclip.copy(self.current_code)
                print(f"Copied puzzle code to clipboard: {self.current_code}")
                self.copy_clicked = True
                return True
            except Exception as e:
                print(f"Could not copy to clipboard: {e}")
        return False

    def activate_input_mode(self):
        """Enter code input mode."""
        self.input_mode_active = True
        if self.input_widget:
            self.input_widget.text = ""
            self.input_widget.cursor_pos = 0
            self.input_widget.active = True

    def deactivate_input_mode(self):
        """Exit code input mode."""
        self.input_mode_active = False

    def reset(self):
        """Reset codec state for new game/menu."""
        self.current_code = None
        self.input_mode_active = False
        self.decoded_params = None
        self.copy_clicked = False
        if self.input_widget:
            self.input_widget.text = ""
            self.input_widget.cursor_pos = 0
            self.input_widget.active = False

    def get_display_code(self) -> Optional[str]:
        """Get formatted code for display (already includes dashes from encode_params)."""
        return self.current_code

    def is_start_enabled(self, is_piece_playable: bool) -> bool:
        """Check if start button should be enabled.

        When input mode is active, start is enabled only when a valid code has
        been entered (decoded_params is not None). Returns False when no code
        or an invalid code is entered. Otherwise, start is enabled when the
        selected piece is playable on the current board.
        """
        if self.input_mode_active:
            return self.decoded_params is not None
        return is_piece_playable