"""
game_controller.py

GameController class for Polyominoes game - extracts all game logic from main().
Handles state management, game flow, scoring, and user actions.

NO UI CHANGES - This is purely a code organization refactor.
"""

import sys
import os
import csv
import random
from enum import Enum, auto
from typing import Optional, List, Tuple, Set, Dict, Any

import pygame
import polyomino_ratings as pr
#import piecekeeper as pk
from gameboard import BoardModel
from puzzle_codec import encode_params, decode_params, polyomino_schema


class GameState(Enum):
    MENU = auto()
    WAITING = auto()
    INGAME = auto()
    ENDGAME = auto()


class GameController:
    """
    Manages all game state and logic for Polyominoes game.
    Extracted from main() to improve code organization.
    """

    def __init__(self, board_model, board_renderer, menu_items: List, label_to_index: Dict,
                 codec_input=None):
        # Core models
        self.board_model = board_model
        self.board_renderer = board_renderer
        self.menu_items = menu_items
        self.label_to_index = label_to_index
        self.codec_input = codec_input

        # Game state
        self.game_state = GameState.MENU
        self.puzzle_layout: Optional[List] = None
        self.used_seed = None
        self.total_puzzle_units = 0
        self.found_puzzle_units = 0
        self.completed_shape_count = 0
        self.player_pos = None
        self.visited: Set[Tuple[int, int]] = set()
        self.visited_moves: Dict[Tuple[int, int], int] = {}
        self.legal_moves: List[Tuple[int, int]] = []
        self.final_legal_moves: List[Tuple[int, int]] = []
        self.last_nonempty_legal_moves: List[Tuple[int, int]] = []

        # UI state
        self.guide_mode_active = True
        self.track_mode_active = True
        self.peek_mode_visible = False
        self.reveal_mode_active = False

        # Hint mode state
        self.hint_mode_active = False
        self.hint_degrees: Dict[Tuple[int, int], int] = {}
        self.saved_guide_mode = False
        self.start_time: Optional[int] = None
        self.game_time_seconds = 0

        # Visual effects
        self.active_effect: Optional[Dict[str, Any]] = None

        # Scoring
        self.endgame_reason = None
        self.endgame_scores: Dict[str, Any] = {}
        self.challenge_rating = 1.0
        self.completion_score = 0
        self.is_piece_playable = True
        self.mobility_rating = 0
        self.agility_rating = 0
        self.unit_factor = 1000
        self.shape_factor = 1000

        # Menu preview
        self.preview_layout: Optional[List] = None

        # Puzzle code and seed tracking
        self.puzzle_code = None
        self.blind_draw_active = False
        self.seed_mode_active = False
        self.decoded_seed = None
        self.copy_button_clicked = False
        self.previous_game_seed = None
        self.previous_game_codec = None

        # Move history tracking
        self.move_history: List[Tuple[int, int]] = []
        self.board_state_history: List[Dict[str, Any]] = []

        # Replay mode tracking
        self.replay_mode_active = False
        self.replay_index = 0

    def get_current_selections(self) -> Dict[str, Any]:
        """Returns current menu selections as a dictionary."""
        sel = {}
        for label, opt_values, current_opt_idx in self.menu_items:
            sel[label] = opt_values[current_opt_idx]
        return sel

    def generate_menu_preview(self):
        """Generate preview layout for menu screen."""
        from polyomino_dev import place_puzzle_layout, compute_density_from_setting

        preview_selections = self.get_current_selections()
        board_size = int(preview_selections["board"])
        density_setting = preview_selections["density"]
        density = compute_density_from_setting(density_setting)
        color_mode = preview_selections["colors"]
        shapes_choice = preview_selections["shapes"]

        self.preview_layout, _ = place_puzzle_layout(
            board_size, board_size, shapes_choice, density, color_mode
        )

    def resize_board_if_needed(self):
        """Resize board model if board size setting changed."""
        current_selections = self.get_current_selections()
        new_board_size = int(current_selections["board"])

        if self.board_model.cols != new_board_size or self.board_model.rows != new_board_size:
            old_player_pos = self.player_pos
            old_cols = self.board_model.cols
            old_rows = self.board_model.rows

            self.board_model = BoardModel(new_board_size, new_board_size)
            self.board_renderer.model = self.board_model

            # reposition player proportionally
            if old_player_pos and old_cols > 1 and old_rows > 1:
                x_frac = old_player_pos[0] / (old_cols - 1)
                y_frac = old_player_pos[1] / (old_rows - 1)
                new_x = int(round(x_frac * (new_board_size - 1)))
                new_y = int(round(y_frac * (new_board_size - 1)))
                new_x = max(0, min(new_x, new_board_size - 1))
                new_y = max(0, min(new_y, new_board_size - 1))
                self.player_pos = (new_x, new_y)
            else:
                menu_center_x = (new_board_size - 1) // 2
                menu_center_y = (new_board_size - 1) // 2
                self.player_pos = (menu_center_x, menu_center_y)

    def update_challenge_rating(self):
        """Update challenge rating based on current selections."""
        import polyomino_difficulty as pd_diff

        challenge_selections = self.get_current_selections()
        if self.blind_draw_active:
            self.challenge_rating = 1.0
            return

        # check playability - hide challenge rating if board is unplayable
        if not self.is_piece_playable:
            self.challenge_rating = 0.0
            return

        piece_name = challenge_selections.get("piece")
        board_size = challenge_selections.get("board")
        shapes = challenge_selections.get("shapes")
        ratings = pr.get_piece_ratings(piece_name, board_size, shapes)
        self.challenge_rating = pd_diff.calculate_challenge_rating(
            challenge_selections,
            ratings['mobility_rating'],
            ratings['agility_rating'],
        )

    def update_playability(self):
        """Check if current piece is playable on current board size."""
        play_selections = self.get_current_selections()
        piece_name = play_selections["piece"]
        board_size = play_selections["board"]
        status = pr.assess_piece_playability(piece_name, board_size)
        # empty string means playable, 'choose a larger board' means unplayable
        self.is_piece_playable = (status != 'choose a larger board')

    def go_to_menu(self):
        """Reset to menu state."""
        from polyomino_dev import get_globally_valid_pieces

        self.blind_draw_active = False
        self.copy_button_clicked = False

        self.game_state = GameState.MENU
        self.puzzle_layout = None
        self.total_puzzle_units = 0
        self.found_puzzle_units = 0
        self.completed_shape_count = 0
        self.completion_score = 0
        self.start_time = None
        self.game_time_seconds = 0
        self.endgame_scores = {}
        self.visited_moves.clear()
        self.move_history.clear()
        self.board_state_history.clear()
        self.replay_mode_active = False

        self.visited.clear()
        self.legal_moves.clear()
        self.final_legal_moves.clear()
        self.last_nonempty_legal_moves.clear()
        self.peek_mode_visible = False
        self.reveal_mode_active = False
        self.hint_mode_active = False
        self.hint_degrees = {}
        self.saved_guide_mode = False

        current_selections = self.get_current_selections()
        current_board_size = int(current_selections["board"])
        menu_globally_valid_pieces = get_globally_valid_pieces()
        menu_current_piece = current_selections["piece"]

        piece_menu_idx = self.label_to_index["piece"]
        if menu_current_piece in menu_globally_valid_pieces:
            piece_index = menu_globally_valid_pieces.index(menu_current_piece)
        else:
            piece_index = 0
        self.menu_items[piece_menu_idx] = (
            self.menu_items[piece_menu_idx][0], menu_globally_valid_pieces, piece_index
        )

        self.update_playability()
        self.update_challenge_rating()

        old_player_pos = self.player_pos
        old_cols = self.board_model.cols
        old_rows = self.board_model.rows

        self.board_model = BoardModel(current_board_size, current_board_size)
        self.board_renderer.model = self.board_model

        if old_player_pos and old_cols and old_rows and old_cols > 1 and old_rows > 1:
            x_frac = old_player_pos[0] / (old_cols - 1)
            y_frac = old_player_pos[1] / (old_rows - 1)
            new_x = int(round(x_frac * (self.board_model.cols - 1)))
            new_y = int(round(y_frac * (self.board_model.rows - 1)))
            new_x = max(0, min(new_x, self.board_model.cols - 1))
            new_y = max(0, min(new_y, self.board_model.rows - 1))
            self.player_pos = (new_x, new_y)
        else:
            menu_center_x = (self.board_model.cols - 1) // 2
            menu_center_y = (self.board_model.rows - 1) // 2
            self.player_pos = (menu_center_x, menu_center_y)

        # reset codec input
        self.puzzle_code = None
        self.seed_mode_active = False
        self.decoded_seed = None
        self.copy_button_clicked = False

        if self.codec_input:
            self.codec_input.text = ""
            self.codec_input.cursor_pos = 0
            self.codec_input.active = False

        self.generate_menu_preview()

    def update_completion_counters(self):
        """Update counters for found units and completed shapes."""
        if self.puzzle_layout is None:
            self.found_puzzle_units = 0
            self.completed_shape_count = 0
        else:
            self.found_puzzle_units = sum(len(s.found_units) for s in self.puzzle_layout)
            self.completed_shape_count = sum(
                1 for s in self.puzzle_layout if len(s.found_units) == len(s.puzzle_units)
            )

    def capture_board_state(self) -> Dict[str, Any]:
        """Capture the current board state as a snapshot for undo/replay."""
        return {
            'grid': dict(self.board_model.grid),
            'found_units_per_shape': {
                shape.id: set(shape.found_units) for shape in (self.puzzle_layout or [])
            },
            'visited': set(self.visited),
            'visited_moves': dict(self.visited_moves),
            'legal_moves': list(self.legal_moves),
        }

    def _restore_board_state(self, state: Dict[str, Any]) -> None:
        """Restore the board to a previously captured state snapshot."""
        self.board_model.grid.clear()
        self.board_model.grid.update(state['grid'])

        if self.puzzle_layout:
            for shape in self.puzzle_layout:
                shape.found_units = set(state['found_units_per_shape'].get(shape.id, set()))

        self.visited = set(state['visited'])
        self.visited_moves = dict(state['visited_moves'])
        self.legal_moves = list(state['legal_moves'])

    def _recalculate_stats_from_board_state(self) -> None:
        """Recalculate stats from the current puzzle state (found_units per shape)."""
        self.update_completion_counters()
        total_shapes = len(self.puzzle_layout) if self.puzzle_layout else 0
        self.completion_score = self._calculate_completion_score(
            self.found_puzzle_units, self.total_puzzle_units,
            self.completed_shape_count, total_shapes
        )

    def start_flow(self, force_seed=None):
        """Start a new game with current settings."""
        from polyomino_dev import place_puzzle_layout, compute_density_from_setting
        import polyomino_difficulty as pd_diff

        self.board_model.clear()
        self.found_puzzle_units = 0
        self.completed_shape_count = 0
        self.completion_score = 0
        self.reveal_mode_active = False
        self.game_time_seconds = 0
        self.endgame_scores = {}
        self.visited_moves.clear()
        self.copy_button_clicked = False
        self.move_history.clear()
        self.board_state_history.clear()
        self.replay_mode_active = False

        flow_selections = self.get_current_selections()

        board_size = int(flow_selections["board"])
        density_setting = flow_selections["density"]
        density = compute_density_from_setting(density_setting)
        color_mode = flow_selections["colors"]
        shapes_choice = flow_selections["shapes"]
        piece_name = flow_selections["piece"]

        # get piece ratings
        ratings = pr.get_piece_ratings(piece_name, board_size, shapes_choice)
        self.mobility_rating = ratings['mobility_rating']
        self.agility_rating = ratings['agility_rating']

        self.challenge_rating = pd_diff.calculate_challenge_rating(
            flow_selections,
            self.mobility_rating,
            self.agility_rating,
            blind_mode=self.blind_draw_active,
        )

        # seed logic
        if force_seed is not None:
            seed_to_use = force_seed
        elif self.decoded_seed is not None:
            seed_to_use = self.decoded_seed
        else:
            seed_to_use = None

        puzzle_layout_local, seed_local = place_puzzle_layout(
            board_size, board_size, shapes_choice, density, color_mode,
            seed=seed_to_use)
        self.puzzle_layout = puzzle_layout_local
        self.used_seed = seed_local

        try:
            self.puzzle_code = encode_params(flow_selections, polyomino_schema, self.used_seed)
        except (ValueError, KeyError) as e1:
            print(f"Warning: Could not generate puzzle code: {e1}")
            self.puzzle_code = None

        self.total_puzzle_units = sum(len(s.puzzle_units) for s in self.puzzle_layout)
        self.previous_game_seed = self.used_seed
        self.previous_game_codec = self.puzzle_code

        if self.board_model.cols != board_size:
            self.board_model = BoardModel(board_size, board_size)
            self.board_renderer.model = self.board_model

        self.game_state = GameState.WAITING
        self.player_pos = None
        self.visited.clear()
        self.legal_moves.clear()
        self.last_nonempty_legal_moves.clear()
        self.peek_mode_visible = False
        self.update_completion_counters()

    def start_blind_draw_flow(self):
        """Start a game with randomized settings."""
        self.blind_draw_active = True
        self.copy_button_clicked = False
        piece_name = self.get_current_selections()["piece"]
        for i, (label, blind_values, _) in enumerate(self.menu_items):
            if label in ["board", "shapes", "density", "colors"]:
                if label == "board":
                    while True:
                        new_idx = random.randint(0, len(blind_values) - 1)
                        if pr.assess_piece_playability(
                            piece_name, blind_values[new_idx]
                        ) != 'choose a larger board':
                            self.menu_items[i] = (label, blind_values, new_idx)
                            break
                else:
                    new_idx = random.randint(0, len(blind_values) - 1)
                    self.menu_items[i] = (label, blind_values, new_idx)
        self.start_flow()

    def commit_start_square(self, pos_gx: int, pos_gy: int):
        """Commit starting square and transition to INGAME."""
        from polyomino_dev import (get_legal_moves_for_board, reveal_unit,
                                   DK_VISITED, LT_VISITED)

        self.start_time = pygame.time.get_ticks()
        self.player_pos = (pos_gx, pos_gy)
        self.visited = {self.player_pos}

        is_new_unit, shape_id = reveal_unit(self.board_model, self.puzzle_layout, pos_gx, pos_gy)
        if is_new_unit and shape_id is not None:
            self.process_found_unit(shape_id, (pos_gx, pos_gy))
        elif not is_new_unit:
            unit_parity = (pos_gx + (self.board_model.rows - 1 - pos_gy)) % 2
            unit_vcolor = DK_VISITED if unit_parity == 0 else LT_VISITED
            self.board_model.set_cell(pos_gx, pos_gy, unit_vcolor)

        commit_current_piece = self.get_current_selections()["piece"]
        self.legal_moves = get_legal_moves_for_board(
            commit_current_piece, pos_gx, pos_gy,
            self.board_model.cols, self.board_model.rows, self.visited
        )

        if self.legal_moves:
            self.last_nonempty_legal_moves = list(self.legal_moves)

        self.game_state = GameState.INGAME

        # Initialize move history with starting position
        self.move_history = [self.player_pos]
        self.board_state_history = [self.capture_board_state()]

    def process_found_unit(self, shape_id: int, found_grid_pos: Tuple[int, int]):
        """Process a found puzzle unit and update shape completion."""
        prev_completed_count = self.completed_shape_count
        self.update_completion_counters()

        total_shapes = len(self.puzzle_layout) if self.puzzle_layout else 0
        self.completion_score = self._calculate_completion_score(
            self.found_puzzle_units, self.total_puzzle_units,
            self.completed_shape_count, total_shapes
        )

        if self.completed_shape_count > prev_completed_count:
            pass

        shape_object = next((s for s in self.puzzle_layout if s.id == shape_id), None)
        if shape_object:
            center_px, center_py = self.board_renderer.to_pixel(*found_grid_pos)
            cs = self.board_renderer.cell_size
            self.active_effect = {
                "units": [(0, 0)], "color": shape_object.color,
                "center_pos": (center_px + cs // 2, center_py + cs // 2),
                "size": cs * 1.5, "expires": pygame.time.get_ticks() + 500
            }

    def _calculate_completion_score(
            self,
            found_units: int,
            total_units: int,
            completed_shapes: int,
            total_shapes: int
    ) -> int:
        """Calculate completion score based on units and shapes found."""
        if total_units <= 0 or total_shapes <= 0:
            return 0
        unit_completion_ratio = found_units / total_units
        shape_completion_ratio = completed_shapes / total_shapes
        base_score = (
            (unit_completion_ratio * self.unit_factor) +
            (shape_completion_ratio * self.shape_factor)
        )
        return round(base_score)

    def calculate_endgame_scores(self):
        """Calculate all endgame scores."""
        final_score = round(self.completion_score * self.challenge_rating)
        self.endgame_scores = {
            "completion_score": self.completion_score,
            "challenge_rating_multiplier": self.challenge_rating,
            "final_score": final_score,
        }

    def write_endgame_stats_to_csv(self, stats_reason: str):
        """Write game statistics to CSV file."""
        stats_filename = "../polyominoes/endgamestats.csv"
        stats_selections = self.get_current_selections()
        game_mode = "blind draw" if self.blind_draw_active else "regular"
        piece_name = stats_selections["piece"]
        board_size = stats_selections["board"]
        stats_shape_type = stats_selections["shapes"]

        total_shapes_in_puzzle = len(self.puzzle_layout) if self.puzzle_layout else 0
        total_moves = len(self.visited)

        data = {
            "puzzle_code": self.puzzle_code if self.puzzle_code else "",
            "game_mode": game_mode,
            "piece_name": piece_name,
            "board_size": board_size,
            "shape_type": stats_shape_type,
            "density": stats_selections["density"],
            "colors": stats_selections["colors"],
            "mobility_rating": self.mobility_rating,
            "agility_rating": self.agility_rating,
            "challenge_rating": self.challenge_rating,
            "endgame_reason": stats_reason,
            "units_found": self.found_puzzle_units,
            "total_units": self.total_puzzle_units,
            "unit_completion_ratio": (
                self.found_puzzle_units / self.total_puzzle_units
                if self.total_puzzle_units > 0 else 0.0
            ),
            "shapes_completed": self.completed_shape_count,
            "total_shapes": total_shapes_in_puzzle,
            "shape_completion_ratio": (
                self.completed_shape_count / total_shapes_in_puzzle
                if total_shapes_in_puzzle > 0 else 0.0
            ),
            "total_moves": total_moves,
            "completion_score": self.endgame_scores.get("completion_score", 0),
            "final_score": self.endgame_scores.get("final_score", 0),
            "elapsed_time_seconds": self.game_time_seconds,
        }

        file_exists = os.path.isfile(stats_filename)
        fieldnames = list(data.keys())

        try:
            with open(stats_filename, 'r+', newline='') as csvfile:
                reader = csv.reader(csvfile)
                try:
                    header = next(reader)
                    for field in fieldnames:
                        if field not in header:
                            header.append(field)
                    fieldnames = header
                except StopIteration:
                    pass
        except FileNotFoundError:
            pass

        with open(stats_filename, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists or os.path.getsize(stats_filename) == 0:
                writer.writeheader()
            writer.writerow(data)

    def go_to_endgame(self, end_reason: str):
        """Transition to endgame state."""
        import polyomino_difficulty as pd_diff

        if self.game_state == GameState.INGAME:
            if end_reason == 'no legal moves':
                self.final_legal_moves = list(self.last_nonempty_legal_moves)
            else:
                self.final_legal_moves = list(self.legal_moves)

            self.game_state = GameState.ENDGAME
            self.final_legal_moves = list(self.legal_moves)
            self.endgame_reason = end_reason
            self.peek_mode_visible = False
            self.previous_game_codec = self.puzzle_code

            # calculate real challenge rating for blind draw mode
            if self.blind_draw_active:
                current_selections = self.get_current_selections()
                self.challenge_rating = pd_diff.calculate_challenge_rating(
                    current_selections,
                    self.mobility_rating,
                    self.agility_rating,
                    blind_mode=False,  # reveal actual difficulty at endgame
                )

            self.calculate_endgame_scores()
            self.write_endgame_stats_to_csv(end_reason)
            # Deactivate hint mode and restore guide mode if it was suppressed
            if self.hint_mode_active:
                self.guide_mode_active = self.saved_guide_mode
            self.hint_mode_active = False
            self.hint_degrees = {}
            self.saved_guide_mode = False

    def toggle_reveal_all_shapes(self):
        """Toggle reveal mode on/off."""
        if self.game_state == GameState.ENDGAME:
            self.reveal_mode_active = not self.reveal_mode_active

    def undo_last_move(self):
        """Undo the last move, reverting to the previous board state."""
        if self.game_state != GameState.INGAME:
            return
        if len(self.move_history) <= 1:
            # Already at starting position, nothing to undo
            return

        self.move_history.pop()
        self.board_state_history.pop()

        self._restore_board_state(self.board_state_history[-1])
        self.player_pos = self.move_history[-1]
        self._recalculate_stats_from_board_state()
        self.update_hint_degrees_if_active()

    def toggle_replay_mode(self):
        """Toggle replay mode on/off (ENDGAME only)."""
        if self.game_state != GameState.ENDGAME:
            return

        if not self.replay_mode_active:
            # Activate replay mode: restore board to starting state
            self.replay_mode_active = True
            self.replay_index = 0
            if self.board_state_history:
                self._restore_board_state(self.board_state_history[0])
                self.player_pos = self.move_history[0]
                self._recalculate_stats_from_board_state()
        else:
            # Deactivate replay mode: restore final game state
            self.replay_mode_active = False
            if self.board_state_history:
                self._restore_board_state(self.board_state_history[-1])
                self.player_pos = self.move_history[-1]
                self._recalculate_stats_from_board_state()

    def navigate_replay(self, direction: int):
        """Navigate replay forward (+1) or backward (-1) by one step."""
        if not self.replay_mode_active or not self.move_history:
            return

        new_index = max(0, min(len(self.move_history) - 1, self.replay_index + direction))
        if new_index == self.replay_index:
            return

        self.replay_index = new_index
        self._restore_board_state(self.board_state_history[self.replay_index])
        self.player_pos = self.move_history[self.replay_index]
        self._recalculate_stats_from_board_state()

    def toggle_codec_input(self):
        """Toggle puzzle code input mode."""
        if self.seed_mode_active:
            # cancel input: just close input box, don't reset anything
            self.seed_mode_active = False
            self.decoded_seed = None  # Clear any decoded seed
            if self.codec_input:
                self.codec_input.active = False
                self.codec_input.text = ""
                self.codec_input.cursor_pos = 0
        else:
            # activate input box
            self.seed_mode_active = True
            if self.codec_input:
                self.codec_input.active = True
                self.codec_input.text = ""
                self.codec_input.cursor_pos = 0
                self.codec_input.cursor_visible = True
                self.codec_input.cursor_timer = 0

    def resign_game(self):
        """Resign current game."""
        self.go_to_endgame('resigned')

    @staticmethod
    def quit_game():
        """Quit the application."""
        pygame.quit()
        sys.exit()

    def toggle_guide_mode(self):
        """Toggle guide mode (arrows showing legal moves)."""
        self.guide_mode_active = not self.guide_mode_active

    def toggle_track_mode(self):
        """Toggle track mode (showing move numbers)."""
        self.track_mode_active = not self.track_mode_active

    def toggle_hint_mode(self):
        """Toggle hint mode (showing hint_degree for each legal move square)."""
        if not self.hint_mode_active:
            # Activating hint mode: save and suppress guide mode only
            self.saved_guide_mode = self.guide_mode_active
            self.guide_mode_active = False
            self.hint_mode_active = True
            self.update_hint_degrees_if_active()
        else:
            # Deactivating hint mode: restore guide mode only
            self.guide_mode_active = self.saved_guide_mode
            self.hint_mode_active = False
            self.hint_degrees = {}

    def calculate_hint_degrees(self):
        """Calculate the degree (number of onward legal moves) for each square reachable from the current position."""
        from polyomino_dev import get_legal_moves_for_board

        if not self.player_pos or self.game_state != GameState.INGAME:
            self.hint_degrees = {}
            return

        current_piece = self.get_current_selections()["piece"]
        cols = self.board_model.cols
        rows = self.board_model.rows

        # Get all squares reachable from current position (one legal move away)
        reachable = get_legal_moves_for_board(
            current_piece, self.player_pos[0], self.player_pos[1],
            cols, rows, self.visited
        )

        # Calculate degree for each reachable square
        raw_degrees: Dict[Tuple[int, int], int] = {}
        for sq in reachable:
            # visited_from_sq: if we move to sq, it becomes visited
            visited_from_sq = self.visited | {sq}
            onward = get_legal_moves_for_board(
                current_piece, sq[0], sq[1],
                cols, rows, visited_from_sq
            )
            degree = len(onward)
            if degree > 0:
                raw_degrees[sq] = degree

        # For sliding pieces, only show the two lowest non-zero degree values
        lower_piece = current_piece.lower()
        sliding_pieces = {"rook", "bishop", "queen"}
        if lower_piece in sliding_pieces and raw_degrees:
            sorted_degrees = sorted(set(raw_degrees.values()))
            cutoff_values = set(sorted_degrees[:2])
            self.hint_degrees = {sq: deg for sq, deg in raw_degrees.items()
                                 if deg in cutoff_values}
        else:
            self.hint_degrees = dict(raw_degrees)

        # Auto-deactivate if all legal moves have degree 0 (empty dict means all moves are dead ends)
        if not self.hint_degrees:
            self.guide_mode_active = self.saved_guide_mode
            self.hint_mode_active = False

    def update_hint_degrees_if_active(self):
        """Recalculate hint_degrees if hint mode is currently active."""
        if self.hint_mode_active and self.player_pos and self.game_state == GameState.INGAME:
            self.calculate_hint_degrees()

    def copy_puzzle_code_to_clipboard(self):
        """Copy the current puzzle code to clipboard."""
        if self.puzzle_code and not self.copy_button_clicked:
            self.copy_button_clicked = True
            try:
                import pyperclip
                pyperclip.copy(self.puzzle_code)
                self.copy_button_clicked = True
            except Exception as e2:
                print(f"Could not copy to clipboard: {e2}")

    def toggle_peek(self):
        """Toggle peek mode (showing puzzle layout thumbnail)."""
        self.peek_mode_visible = not self.peek_mode_visible

    def new_game_flow(self):
        """Start a completely new game flow."""
        self.used_seed = None
        self.go_to_menu()

    def retry_last_game(self):
        """Retry the last game with same codec."""
        if self.previous_game_codec:
            self.retry_from_codec(self.previous_game_codec)
        else:
            # fallback to old logic if no codec stored; not recommended!
            self.start_flow(force_seed=self.previous_game_seed)

    def retry_from_codec(self, codec: str):
        """Retry game from a puzzle code."""
        # decode all settings and seed from codec
        try:
            params = decode_params(codec, polyomino_schema)
        except (KeyError, ValueError):
            print("Error: Invalid previous game codec, retry not possible.")
            self.go_to_menu()
            return

        # restore menu_items to match previous game settings
        for label, idx in self.label_to_index.items():
            menu_values = self.menu_items[idx][1]
            if label in params and params[label] in menu_values:
                position = menu_values.index(params[label])
                self.menu_items[idx] = (label, menu_values, position)

        # set seed and start game
        self.start_flow(force_seed=params["seed"])