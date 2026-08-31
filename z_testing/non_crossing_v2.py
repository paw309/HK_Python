import pandas as pd

# Load the spreadsheet data into memory
EXCEL_PATH = 'non-crossing path lengths.xlsx'


def load_tables(file_path):
    df = pd.read_excel(file_path, sheet_name='Sheet1')

    # Locate table headers by searching for key section titles
    known_idx = df[df.iloc[:, 0] == 'known path lengths'].index[0]
    est_idx = df[df.iloc[:, 0] == 'estimated path lengths'].index[0]

    # Process Known Path Lengths Table
    known_df = df.iloc[known_idx + 2: est_idx].dropna(how='all').copy()
    known_df.columns = ['piece', 'vectors'] + [int(x) for x in df.iloc[known_idx + 1, 2:].values]
    known_df = known_df.dropna(subset=['piece'])

    # Process Estimated Path Lengths Table
    est_df = df.iloc[est_idx + 2:].dropna(how='all').copy()
    est_df.columns = ['piece', 'vectors'] + [int(x) for x in df.iloc[est_idx + 1, 2:].values]
    est_df = est_df.dropna(subset=['piece'])

    return known_df, est_df


def get_estimated_upper_bound(piece_name: str, board_size: int, known_df: pd.DataFrame, est_df: pd.DataFrame):
    """
    Retrieves the estimated upper bound path length for a piece on a given board size.
    Checks the estimated table first, then falls back to the known table if exact.
    """
    piece_name = piece_name.strip().lower()

    # Search estimated table first
    match_est = est_df[est_df['piece'].astype(str).str.lower() == piece_name]
    if not match_est.empty and board_size in match_est.columns:
        val = match_est[board_size].values[0]
        if pd.notna(val):
            return int(val), "Estimated Table"

    # Fallback: check known table
    match_known = known_df[known_df['piece'].astype(str).str.lower() == piece_name]
    if not match_known.empty and board_size in match_known.columns:
        val = match_known[board_size].values[0]
        if pd.notna(val):
            return int(val), "Known Table (exact)"

    return None, "No data available for this combination"


def main():
    known_df, est_df = load_tables(EXCEL_PATH)

    print("=== Non-Crossing Path Upper Bound Lookup ===")
    piece_input = input("Enter piece name (e.g., knight, zebra, gnu): ").strip()
    board_input = input("Enter board size (5 to 16): ").strip()

    try:
        board_size = int(board_input)
        if not (5 <= board_size <= 16):
            print("Error: Board size must be between 5 and 16.")
            return
    except ValueError:
        print("Error: Board size must be an integer.")
        return

    result, source = get_estimated_upper_bound(piece_input, board_size, known_df, est_df)

    print("\n--- Result ---")
    print(f"Piece: {piece_input}")
    print(f"Board Size: {board_size}x{board_size}")
    if result is not None:
        print(f"Estimated Upper Bound: {result} (Source: {source})")
    else:
        print(f"Status: {source}")


if __name__ == "__main__":
    main()