import csv
import json

# Load the JSON data from 'paths.json'
with open("paths.json", "r") as f:
  data = json.load(f)

# Define CSV output headers
csv_filename = "path_summary.csv"
headers = [
    "Piece",
    "Board Size",
    "Starting Square",
    "Longest Path Length",
    "Number of Paths",
]

rows = []

# Iterate through each piece, board size, and starting square
for piece, board_sizes in data.items():
  for board_size, board_info in board_sizes.items():
    starts = board_info.get("starts", {})
    for start_square, start_data in starts.items():
      # Get the length specified for the starting square
      length = start_data.get("length", 0)

      # Alternatively, find the maximum path length from the actual path lists if needed:
      # paths = start_data.get("paths", [])
      # max_path_length = max((len(p) for p in paths), default=0) if paths else length

      # Count the number of paths available for this starting square
      paths = start_data.get("paths", [])
      num_paths = len(paths)

      rows.append(
          [piece, board_size, start_square, length, num_paths]
      )

# Write data to CSV file
with open(csv_filename, "w", newline="", encoding="utf-8") as csv_file:
  writer = csv.writer(csv_file)
  writer.writerow(headers)
  writer.writerows(rows)

print(
    f"Successfully generated '{csv_filename}' with {len(rows)} summary rows."
)