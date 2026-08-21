#!/usr/bin/env python3
"""
test_hexadecominoes.py

Tests all hexadecomino tours to verify:
1. Each tour has exactly 16 tuples (squares)
2. All 16 tuples form a valid knight's tour (each move is a valid knight move)
3. All 16 squares are unique (no repeated positions)
4. The tour forms a connected path
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from z_testing.tours_hexadecominoes import HEXADECOMINO_TOURS
from typing import List, Tuple, Set


class HexadecominoTourValidator:
    """
    Validates knight's tours on hexadecominoes (16-square polyominoes).
    """

    # Knight move offsets - all 8 possible L-shaped moves
    KNIGHT_MOVES = [
        (-2, -1), (-2, 1), (-1, -2), (-1, 2),
        (1, -2), (1, 2), (2, -1), (2, 1)
    ]

    @staticmethod
    def is_valid_knight_move(from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> bool:
        """
        Check if moving from from_pos to to_pos is a valid knight move.

        Args:
            from_pos: Starting position (x, y)
            to_pos: Ending position (x, y)

        Returns:
            True if the move is a valid knight move, False otherwise
        """
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        return (dx, dy) in HexadecominoTourValidator.KNIGHT_MOVES

    @staticmethod
    def validate_tour(tour: List[Tuple[int, int]], key: str) -> Tuple[bool, str]:
        """
        Validate a complete hexadecomino tour.

        Tests all 16 tuples as one unit:
        - Exactly 16 squares
        - All squares unique
        - Each consecutive move is a valid knight move

        Args:
            tour: List of (x, y) coordinates representing the tour
            key: Tour identifier for error messages

        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is empty string
        """
        # Test 1: Must have exactly 16 tuples
        if len(tour) != 16:
            return False, f"{key}: Expected 16 squares, got {len(tour)}"

        # Test 2: All squares must be unique (no position visited twice)
        tour_set = set(tour)
        if len(tour_set) != 16:
            duplicates = [pos for pos in tour if tour.count(pos) > 1]
            return False, f"{key}: Duplicate positions found: {set(duplicates)}"

        # Test 3: Each consecutive move must be a valid knight move
        for i in range(len(tour) - 1):
            from_pos = tour[i]
            to_pos = tour[i + 1]

            if not HexadecominoTourValidator.is_valid_knight_move(from_pos, to_pos):
                dx = to_pos[0] - from_pos[0]
                dy = to_pos[1] - from_pos[1]
                return False, (f"{key}: Invalid knight move from {from_pos} to {to_pos} "
                               f"(offset: ({dx}, {dy}))")

        # Test 4: Verify all tuples are actually tuples of 2 integers
        for i, pos in enumerate(tour):
            if not isinstance(pos, tuple) or len(pos) != 2:
                return False, f"{key}: Position {i} is not a valid tuple: {pos}"
            if not all(isinstance(coord, int) for coord in pos):
                return False, f"{key}: Position {i} contains non-integer coordinates: {pos}"

        # All tests passed
        return True, ""

    @staticmethod
    def get_tour_bounds(tour: List[Tuple[int, int]]) -> Tuple[int, int, int, int]:
        """
        Get the bounding box of a tour.

        Returns:
            (min_x, max_x, min_y, max_y)
        """
        xs = [pos[0] for pos in tour]
        ys = [pos[1] for pos in tour]
        return min(xs), max(xs), min(ys), max(ys)


def test_all_hexadecominoes(verbose: bool = False, stop_on_error: bool = False):
    """
    Test all hexadecomino tours in the HEXADECOMINO_TOURS dictionary.

    Args:
        verbose: If True, print details for each tour
        stop_on_error: If True, stop on first error

    Returns:
        Tuple of (passed_count, failed_count, errors)
    """
    print("=" * 70)
    print("TESTING HEXADECOMINO TOURS")
    print("=" * 70)
    print(f"Total tours to test: {len(HEXADECOMINO_TOURS)}")
    print()

    passed = 0
    failed = 0
    errors = []

    for key, tour in HEXADECOMINO_TOURS.items():
        is_valid, error_msg = HexadecominoTourValidator.validate_tour(tour, key)

        if is_valid:
            passed += 1
            if verbose:
                min_x, max_x, min_y, max_y = HexadecominoTourValidator.get_tour_bounds(tour)
                print(f"✓ {key}: Valid tour (bounds: x=[{min_x},{max_x}], y=[{min_y},{max_y}])")
        else:
            failed += 1
            errors.append(error_msg)
            print(f"✗ {error_msg}")

            if stop_on_error:
                print("\nStopping on first error.")
                break

    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total tours tested: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        print(f"\nFirst few errors:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    else:
        print("\n🎉 All hexadecomino tours are valid!")
        print("   - All tours have exactly 16 squares")
        print("   - All moves are valid knight moves")
        print("   - No duplicate positions in any tour")

    print("=" * 70)

    return passed, failed, errors


def test_sample_tours():
    """
    Test a small sample of tours with detailed output.
    """
    print("=" * 70)
    print("DETAILED SAMPLE TESTS")
    print("=" * 70)

    # Test first 5 tours in detail
    sample_keys = list(HEXADECOMINO_TOURS.keys())[:5]

    for key in sample_keys:
        tour = HEXADECOMINO_TOURS[key]
        print(f"\nTesting {key}:")
        print(f"  Tour: {tour}")
        print(f"  Length: {len(tour)}")

        is_valid, error = HexadecominoTourValidator.validate_tour(tour, key)

        if is_valid:
            print(f"  ✓ Valid tour")
            # Show the moves
            print("  Moves:")
            for i in range(len(tour) - 1):
                from_pos = tour[i]
                to_pos = tour[i + 1]
                dx = to_pos[0] - from_pos[0]
                dy = to_pos[1] - from_pos[1]
                print(f"    {i}: {from_pos} -> {to_pos}  (offset: {dx}, {dy})")
        else:
            print(f"  ✗ Invalid: {error}")

    print("\n" + "=" * 70)


def main():
    """
    Main test function.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Test hexadecomino tours')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print details for each tour')
    parser.add_argument('-s', '--stop-on-error', action='store_true',
                        help='Stop on first error')
    parser.add_argument('--sample', action='store_true',
                        help='Run detailed tests on sample tours only')

    args = parser.parse_args()

    if args.sample:
        test_sample_tours()
    else:
        passed, failed, errors = test_all_hexadecominoes(
            verbose=args.verbose,
            stop_on_error=args.stop_on_error
        )

        # Exit with error code if any tests failed
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()