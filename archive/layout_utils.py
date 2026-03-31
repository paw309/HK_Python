def get_centered_board_origin(
        area_left: int,
        area_top: int,
        area_width: int,
        area_height: int,
        cols: int,
        rows: int,
        cell_size: int
) -> tuple:
    """
    Returns (origin_x, origin_y) pixel coordinates to center a board within a given area.

    Parameters:
        area_left   -- pixel x of area top-left corner
        area_top    -- pixel y of area top-left corner
        area_width  -- width of area
        area_height -- height of area
        cols        -- number of columns on board
        rows        -- number of rows on board
        cell_size   -- pixel size for each cell

    Returns:
        (origin_x, origin_y)
    """
    board_pixel_w = cols * cell_size
    board_pixel_h = rows * cell_size
    origin_x = area_left + (area_width - board_pixel_w) // 2
    origin_y = area_top + (area_height - board_pixel_h) // 2
    return origin_x, origin_y