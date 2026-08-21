#!/usr/bin/env python3
"""
knights_tour_tester.py

Tests whether a knight's tour is possible on various polyominoes.
For each polyomino, attempts to find a Hamiltonian path (knight's tour)
starting from any square on the polyomino.
"""

import os
from typing import List, Tuple, Set, Optional, Dict

# Import the polyomino data
from pyversion.tourbus.polymath.tridecomino_data import SAMPLE_POLYOMINOES

class KnightTourPolyomino:
    """
    Tests if a knight's tour is possible on a given polyomino shape.
    """

    # knight move offset
    KNIGHT_MOVES = [
        (-2, -1), (-2, 1), (-1, -2), (-1, 2),
        (1, -2), (1, 2), (2, -1), (2, 1)
    ]

    def __init__(self, polyomino: List[Tuple[int, int]]):
        """
        Initialize with a polyomino (list of (x, y) coordinates).
        """
        self.polyomino = set(polyomino)
        self.size = len(polyomino)
        self.coord_list = list(polyomino)

    def get_valid_moves(self, pos: Tuple[int, int], visited: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Get all valid knight moves from current position that are:
        1. Within the polyomino
        2. Not yet visited
        """
        x, y = pos
        valid_moves = []

        for dx, dy in self.KNIGHT_MOVES:
            new_pos = (x + dx, y + dy)
            if new_pos in self.polyomino and new_pos not in visited:
                valid_moves.append(new_pos)

        return valid_moves

    def count_onward_moves(self, pos: Tuple[int, int], visited: Set[Tuple[int, int]]) -> int:
        """
        Count how many valid moves are available from this position.
        Used for Warnsdorff's heuristic.
        """
        return len(self.get_valid_moves(pos, visited))

    def find_tour_from_start(self, start_pos: Tuple[int, int], use_warnsdorff: bool = True) -> Optional[
        List[Tuple[int, int]]]:
        """
        Attempt to find a knight's tour starting from a specific position.
        Uses backtracking with optional Warnsdorff's heuristic.

        Returns:
            List of coordinates in tour order if successful, None otherwise.
        """
        visited = set()
        path = []

        def backtrack(pos: Tuple[int, int]) -> bool:
            visited.add(pos)
            path.append(pos)

            # Check if we've completed the tour
            if len(visited) == self.size:
                return True

            # Get valid next moves
            next_moves = self.get_valid_moves(pos, visited)

            # Apply Warnsdorff's heuristic: prioritize moves with fewer onward options
            if use_warnsdorff and next_moves:
                next_moves.sort(key=lambda p: self.count_onward_moves(p, visited))

            # Try each move
            for next_pos in next_moves:
                if backtrack(next_pos):
                    return True

            # Backtrack
            visited.remove(pos)
            path.pop()
            return False

        if backtrack(start_pos):
            return path
        return None

    def find_any_tour(self) -> Optional[Tuple[List[Tuple[int, int]], Tuple[int, int]]]:
        """
        Try to find a knight's tour starting from any square in the polyomino.

        Returns:
            Tuple of (path, start_position) if successful, None otherwise.
        """
        # Try each square as a starting point
        for start_pos in self.coord_list:
            tour = self.find_tour_from_start(start_pos, use_warnsdorff=True)
            if tour:
                return (tour, start_pos)

        return None


def test_polyominoes(polyomino_dict: Dict[str, List[Tuple[int, int]]], output_file: str):
    """
    Test all polyominoes in the dictionary for knight's tour feasibility.
    Write successful tours to output file.

    Args:
        polyomino_dict: Dictionary mapping polyomino keys to coordinate lists
        output_file: Path to output file
    """
    successful_tours = {}
    failed_polyominoes = []

    print(f"\nTesting {len(polyomino_dict)} polyominoes...")

    for key, coords in polyomino_dict.items():
        print(f"  Testing {key} ({len(coords)} squares)...", end=" ")

        tester = KnightTourPolyomino(coords)
        result = tester.find_any_tour()

        if result:
            tour_path, start_pos = result
            successful_tours[key] = tour_path
            print(f"✓ Tour found (starting from {start_pos})")
        else:
#            failed_polyominoes.append(key)
            print("✗ No tour found")

    # Write results to file
    with open(output_file, 'w') as f:
        f.write(f"# Successfully found tours for {len(successful_tours)}/{len(polyomino_dict)} polyominoes\n\n")

        if successful_tours:
            f.write("SUCCESSFUL_TOURS = {\n")
            for key, path in successful_tours.items():
                # Format as specified: coordinates in order of moves
                coords_str = ", ".join([f"({x}, {y})" for x, y in path])
                f.write(f'    "{key}": [{coords_str}],\n')
            f.write("}\n\n")

        #if failed_polyominoes:
        #    f.write(f"# Failed polyominoes (no tour found): {failed_polyominoes}\n")

    print(f"\nResults written to: {output_file}")
    print(f"  Successful: {len(successful_tours)}")
    print(f"  Failed: {len(failed_polyominoes)}")


def main():
    """
    Main function to test enneominoes and decominoes.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Test xdecominoes
    print("=" * 60)
    print("z_testing 13-square polyominoes")
    print("=" * 60)
    tridecominoes_output = os.path.join(script_dir, "tridectemp_tours.py")
    test_polyominoes(SAMPLE_POLYOMINOES, tridecominoes_output)


    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")



if __name__ == "__main__":
    main()