#!/usr/bin/env python3
"""
Deduplicate heptadecomino tours by sorting by tuple sequences and removing duplicates.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from z_testing.tours_heptadecominoes import HEPTADECOMINO_TOURS


def deduplicate_tours(tours_dict):
    """
    Deduplicate tours by:
    1. Sorting entries by their tuple sequences
    2. Comparing consecutive entries
    3. Removing duplicates where the 16-tuple sequence is identical

    Returns:
        dict: Deduplicated tours with original keys for unique sequences
    """
    print(f"Original number of tours: {len(tours_dict)}")

    # Create list of (key, tuple_sequence) pairs
    tours_list = [(key, tuple(tour)) for key, tour in tours_dict.items()]

    # Sort by tuple sequences (sorts by first tuple, then second, etc.)
    tours_list.sort(key=lambda x: x[1])

    print(f"Sorted {len(tours_list)} entries by tuple sequences")

    # Deduplicate consecutive identical sequences
    deduplicated = []
    duplicates = []

    for i in range(len(tours_list)):
        key, tour_seq = tours_list[i]

        # For first entry, always keep it
        if i == 0:
            deduplicated.append((key, tour_seq))
            continue

        # Compare with previous entry
        prev_key, prev_tour_seq = tours_list[i - 1]

        if tour_seq == prev_tour_seq:
            # Duplicate found - discard this one
            duplicates.append((key, prev_key))
            print(f"  Duplicate: {key} matches {prev_key}")
        else:
            # Different from previous - keep it
            deduplicated.append((key, tour_seq))

    print(f"\nDeduplication complete:")
    print(f"  Unique tours: {len(deduplicated)}")
    print(f"  Duplicates removed: {len(duplicates)}")

    # Convert back to dictionary with lists
    result = {key: list(tour_seq) for key, tour_seq in deduplicated}

    return result, duplicates


def write_deduplicated_file(deduplicated_tours, output_file):
    """
    Write deduplicated tours to a new Python file.
    """
    with open(output_file, 'w') as f:
        f.write('"""\n')
        f.write('Deduplicated heptadecomino tours.\n')
        f.write('"""\n\n')
        f.write('HEPTADECOMINO_TOURS = {\n')

        for key, tour in deduplicated_tours.items():
            # Format the tour as a list of tuples on one line
            tour_str = ', '.join([f"({x}, {y})" for x, y in tour])
            f.write(f'    "{key}": [{tour_str}],\n')

        f.write('}\n')

    print(f"\nDeduplicated tours written to: {output_file}")


def write_duplicates_report(duplicates, output_file):
    """
    Write a report of duplicates found.
    """
    with open(output_file, 'w') as f:
        f.write('# Duplicate Tours Report\n\n')
        f.write(f'Total duplicates found: {len(duplicates)}\n\n')

        if duplicates:
            f.write('## Duplicates (duplicate_key matches original_key)\n\n')
            for dup_key, orig_key in duplicates:
                f.write(f'- {dup_key} is identical to {orig_key}\n')

    print(f"Duplicates report written to: {output_file}")


def main():
    """
    Main function to deduplicate tours.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 70)
    print("DEDUPLICATING HEPTADECOMINO TOURS")
    print("=" * 70)
    print()

    # Deduplicate
    deduplicated_tours, duplicates = deduplicate_tours(HEPTADECOMINO_TOURS)

    # Write outputs
    output_file = os.path.join(script_dir, "tours_heptadecominoes_deduplicated.py")
    write_deduplicated_file(deduplicated_tours, output_file)

    duplicates_file = os.path.join(script_dir, "duplicates_report.txt")
    write_duplicates_report(duplicates, duplicates_file)

    print("\n" + "=" * 70)
    print("DEDUPLICATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()