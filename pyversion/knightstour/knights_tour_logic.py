import random

class KnightsTour:
    """
    Computes a knight's tour on an n x n board.
    Default is 8x8, but can be used for other sizes.
    Usage:
        kt = KnightsTour(size=8)
        path = kt.find_tour()
        # path is a list of (x, y) coordinates
    """
    def __init__(self, size=8):
        self.size = size
        self.rank_string = [str(i+1) for i in range(size)]
        self.file_string = [chr(ord('a') + i) for i in range(size)]
        self.wheel_rank = [-2, -2, -1, -1, 1, 1, 2, 2]
        self.wheel_file = [-1, 1, -2, 2, -2, 2, -1, 1]

    def coords_to_index(self, x, y):
        """ Maps (x, y) to a linear index for flat arrays. """
        return y * self.size + x

    def index_to_coords(self, index):
        """ Maps a linear index to (x, y) coordinates. """
        return (index % self.size, index // self.size)

    def find_tour(self, start_square=None):
        """
        Computes one knight's tour using Warnsdorff's rule.
        Returns a list of (x, y) moves. If no tour found, may return partial path.
        """
        size = self.size
        total_squares = size * size
        exit_value = [0] * (total_squares)
        # Initialize exit values (Count valid knight moves from each square)
        for i in range(total_squares):
            x, y = self.index_to_coords(i)
            valid_moves = 0
            for k in range(8):
                nx, ny = x + self.wheel_file[k], y + self.wheel_rank[k]
                if 0 <= nx < size and 0 <= ny < size:
                    valid_moves += 1
            exit_value[i] = valid_moves

        # Choose start square
        if start_square is None:
            current = random.randint(0, total_squares-1)
        else:
            current = start_square
        path = []
        used = [False] * total_squares

        for move_num in range(total_squares):
            x, y = self.index_to_coords(current)
            path.append( (x, y) )
            used[current] = True
            exit_value[current] = -1  # mark visited

            # Find valid next squares
            next_candidates = []
            for k in range(8):
                nx, ny = x + self.wheel_file[k], y + self.wheel_rank[k]
                idx = self.coords_to_index(nx, ny)
                if 0 <= nx < size and 0 <= ny < size and not used[idx]:
                    next_candidates.append( (exit_value[idx], idx) )

            if not next_candidates:
                break  # Stuck, tour incomplete

            # Warnsdorff rule: pick the square with the lowest exit_value, break ties randomly
            next_candidates.sort()
            lowest_exit = next_candidates[0][0]
            min_candidates = [idx for ev, idx in next_candidates if ev == lowest_exit]
            current = random.choice(min_candidates)
            # decrement exit values for neighbors (optional, for more variety)
            for k in range(8):
                nx, ny = x + self.wheel_file[k], y + self.wheel_rank[k]
                idx = self.coords_to_index(nx, ny)
                if 0 <= nx < size and 0 <= ny < size and exit_value[idx] > 0:
                    exit_value[idx] -= 1

        return path  # Always (x, y) pairs; length = tour completed squares

    def is_closed_tour(self, path):
        """ Returns True if the tour returns to starting square in one knight move. """
        if not path or len(path) < self.size * self.size:
            return False
        sx, sy = path[0]
        ex, ey = path[-1]
        for dx, dy in zip(self.wheel_file, self.wheel_rank):
            if sx == ex + dx and sy == ey + dy:
                return True
        return False

    def algebraic_for_square(self, x, y):
        return f"{self.file_string[x]}{self.rank_string[y]}"