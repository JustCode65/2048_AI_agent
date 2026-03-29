# NOTE: Do not modify (for submission). Comments and local variable renames
# added here are for study purposes only.

import copy, random


# ============================================================================
# GAME CLASS — the 2048 game engine
# ============================================================================
#
# This class handles ALL game mechanics: board state, sliding tiles, merging,
# scoring, undo, save/load, and game-over detection. The AI never modifies
# this file — it only calls its public methods.
#
# Key concepts:
#   - The board is a 4×4 list-of-lists (self.tile_matrix).
#   - Directions are integers: 0 = up, 1 = left, 2 = down, 3 = right.
#   - Moves work via the "rotation trick": rotate the board so the desired
#     direction becomes "left", slide/merge leftward, then rotate back.
# ============================================================================

class Game:

    def __init__(self, init_tile_matrix=None, init_score=0):
        """
        Create a new 2048 game.

        Args:
            init_tile_matrix -- optional 4×4 grid to start from (None = fresh game)
            init_score       -- starting score (default 0)
        """
        self.board_size = 4
        self.set_state(init_tile_matrix, init_score)

    def set_state(self, init_tile_matrix=None, init_score=0):
        """
        Reset the game to a specific state. If no matrix is given, creates
        a blank board and places two random 2-tiles.

        This is the method the AI uses to "load" a hypothetical board into
        the simulator before trying a move. It deep-copies the matrix so
        the original is never corrupted.
        """
        self.undoMat = []             # stack of (board, score) for undo
        self.score = init_score

        if init_tile_matrix == None:
            # Fresh game: empty board + two starting tiles
            self.tile_matrix = self.new_tile_matrix()
            self.place_random_tile()
            self.place_random_tile()
        else:
            # Restore from a given state (deep copy to avoid aliasing)
            self.tile_matrix = copy.deepcopy(init_tile_matrix)

        self.board_size = len(self.tile_matrix)

    def new_tile_matrix(self):
        """Return a board_size × board_size grid of zeros."""
        return [[0 for col in range(self.board_size)] for row in range(self.board_size)]

    def current_state(self):
        """
        Return a snapshot of the current game state as (tile_matrix, score).

        Returns a DEEP COPY of the tile matrix, so the caller can modify
        it freely without affecting this game instance. This is critical
        for the AI — it captures the "after move" state without corrupting
        the simulator.
        """
        return (copy.deepcopy(self.tile_matrix), self.score)

    # ========================================================================
    # MOVE MECHANICS
    # ========================================================================

    def move_and_place(self, direction):
        """
        Perform a full game turn: slide tiles in the given direction,
        then place a new random 2-tile. This is what the main game loop
        calls. The AI does NOT call this — it uses move() directly so it
        can control tile placement separately.
        """
        if self.move(direction):
            self.place_random_tile()

    def move(self, direction):
        """
        Slide and merge tiles in the specified direction.

        Args:
            direction -- 0=up, 1=left, 2=down, 3=right

        Returns:
            True if the board changed (legal move), False otherwise.

        The rotation trick:
            1. Rotate the board clockwise `direction` times so the target
               direction aligns with "left".
            2. Slide everything left (move_tiles) and merge (merge_tiles).
            3. Rotate back (4 - direction) % 4 times to restore orientation.

        This way, move_tiles() and merge_tiles() only need to handle the
        "slide left" case — one implementation covers all four directions.
        """
        moved = False
        self.addToUndo()  # save state for undo

        # Step 1: Rotate so our target direction becomes "left"
        for rotation in range(0, direction):
            self.rotate_matrix_clockwise()

        # Step 2: Try to slide/merge leftward
        if self.can_move():
            self.move_tiles()    # collapse gaps (shift non-zero tiles left)
            self.merge_tiles()   # combine matching adjacent tiles
            moved = True

        # Step 3: Rotate back to original orientation
        for rotation in range(0, (4 - direction) % 4):
            self.rotate_matrix_clockwise()

        return moved

    def rotate_matrix_clockwise(self):
        """
        Rotate the tile matrix 90° clockwise, in-place.

        Uses the standard 4-corner rotation algorithm:
            For each "ring" of the matrix (outer ring, then inner ring):
                For each element in that ring:
                    Cycle the 4 corresponding corners one position clockwise.

        Example for a 4×4 matrix, the outer ring swaps:
            top-left → top-right → bottom-right → bottom-left → top-left
        """
        board = self.tile_matrix
        for ring in range(0, int(self.board_size / 2)):
            for offset in range(ring, self.board_size - ring - 1):
                # Save the four corners that will be cycled
                top_left     = board[ring][offset]
                bottom_left  = board[self.board_size - 1 - offset][ring]
                bottom_right = board[self.board_size - 1 - ring][self.board_size - 1 - offset]
                top_right    = board[offset][self.board_size - 1 - ring]

                # Rotate: each corner takes the value of the one before it
                board[self.board_size - 1 - offset][ring]                         = top_left
                board[self.board_size - 1 - ring][self.board_size - 1 - offset]   = bottom_left
                board[offset][self.board_size - 1 - ring]                         = bottom_right
                board[ring][offset]                                               = top_right

    def move_tiles(self):
        """
        Slide all non-zero tiles to the LEFT, collapsing gaps.

        For each row, scan left-to-right. Whenever a cell is 0 but there
        are non-zero cells to its right, shift everything left by one.
        Repeat until no more gaps exist.

        Example: [0, 0, 4, 2] → [4, 2, 0, 0]
        """
        board = self.tile_matrix
        for row in range(0, self.board_size):
            for col in range(0, self.board_size - 1):
                # While this cell is empty and there's something to its right...
                while board[row][col] == 0 and sum(board[row][col:]) > 0:
                    # Shift everything from col onward one position left
                    for shift_col in range(col, self.board_size - 1):
                        board[row][shift_col] = board[row][shift_col + 1]
                    board[row][self.board_size - 1] = 0  # rightmost cell becomes empty

    def merge_tiles(self):
        """
        Merge matching adjacent tiles (LEFT direction assumed).

        Scan each row left-to-right. If two adjacent cells match (and aren't 0),
        double the left one, zero the right one, add the merged value to score,
        then re-collapse gaps with move_tiles().

        Example: [4, 4, 2, 2] → [8, 0, 2, 2] → [8, 2, 2, 0] → [8, 4, 0, 0]
                                  (merge 4+4)   (collapse gap)   (merge 2+2)

        Note: calling move_tiles() after each merge ensures that gaps created
        by the merge are immediately filled, so the next pair can be checked.
        """
        board = self.tile_matrix
        for row in range(0, self.board_size):
            for col in range(0, self.board_size - 1):
                if board[row][col] == board[row][col + 1] and board[row][col] != 0:
                    board[row][col] = board[row][col] * 2     # double the left tile
                    board[row][col + 1] = 0                   # clear the right tile
                    self.score += board[row][col]              # add merged value to score
                    self.move_tiles()                          # collapse any new gaps

    def can_move(self):
        """
        Check if any tile can slide LEFT.

        Two conditions make a leftward slide possible:
            1. A gap exists: cell is 0 and the cell to its right is non-zero.
            2. A merge exists: two adjacent cells have the same non-zero value.

        This only checks the "left" direction. The rotation trick in move()
        ensures this works for all four directions.
        """
        board = self.tile_matrix
        for row in range(0, self.board_size):
            for col in range(1, self.board_size):
                # Case 1: gap — empty cell with a non-zero cell to its right
                if board[row][col - 1] == 0 and board[row][col] > 0:
                    return True
                # Case 2: merge — two matching non-zero tiles side by side
                elif (board[row][col - 1] == board[row][col]) and board[row][col - 1] != 0:
                    return True
        return False

    # ========================================================================
    # TILE PLACEMENT
    # ========================================================================

    def place_random_tile(self):
        """
        Place a 2-tile on a random empty cell.

        Uses rejection sampling: pick random (row, col) until we find an
        empty one. This is simple but inefficient when the board is nearly
        full (could loop many times). A better approach would be to use
        get_open_tiles() and pick from the list, but this works fine for
        a 4×4 board.

        Note: the real 2048 game places a 4-tile 10% of the time, but
        this engine always places a 2.
        """
        while True:
            row = random.randint(0, self.board_size - 1)
            col = random.randint(0, self.board_size - 1)
            if self.tile_matrix[row][col] == 0:
                break
        self.tile_matrix[row][col] = 2

    # ========================================================================
    # UNDO SYSTEM
    # ========================================================================

    def undo(self):
        """Pop the most recent saved state from the undo stack and restore it."""
        if len(self.undoMat) > 0:
            previous_state = self.undoMat.pop()
            self.tile_matrix = previous_state[0]
            self.score = previous_state[1]

    def addToUndo(self):
        """Push the current state onto the undo stack (called before every move)."""
        self.undoMat.append((copy.deepcopy(self.tile_matrix), self.score))

    # ========================================================================
    # SAVE / LOAD
    # ========================================================================

    def save_state(self, filename="savedata"):
        """
        Save the current game state to a text file.

        Format: "board_size score tile0 tile1 tile2 ... tile15"
        Tiles are written left-to-right, top-to-bottom.
        """
        file = open(filename, "w")
        tile_values = " ".join([
            str(self.tile_matrix[int(index / self.board_size)][index % self.board_size])
            for index in range(0, self.board_size ** 2)
        ])
        file.write(str(self.board_size) + " " + str(self.score) + " " + tile_values)
        file.close()

    def load_state(self, filename="savedata"):
        """Load a game state from a text file."""
        file = open(filename, "r")
        self.load_state_line(file.readline())
        file.close()

    def load_state_line(self, line):
        """
        Parse a single line of saved state and restore the game.

        Format: "board_size score tile0 tile1 tile2 ... tile15"
        Used by both load_state() and test.py to set up test boards.
        """
        tokens = line.split(' ')
        self.board_size = int(tokens[0])
        new_score = int(tokens[1])

        # Reconstruct the tile matrix from the flat list of values
        new_tile_matrix = self.new_tile_matrix()
        for index in range(0, self.board_size ** 2):
            row = int(index / self.board_size)
            col = index % self.board_size
            new_tile_matrix[row][col] = int(tokens[2 + index])

        self.set_state(new_tile_matrix, new_score)

    # ========================================================================
    # GAME STATE QUERIES
    # ========================================================================

    def get_open_tiles(self):
        """
        Return a list of (row, col) tuples for all empty cells on the board.
        """
        open_cells = []
        for row in range(0, self.board_size):
            for col in range(0, self.board_size):
                if self.tile_matrix[row][col] == 0:
                    open_cells.append((row, col))
        return open_cells

    def game_over(self):
        """
        Check if the game is over (no legal moves in any direction).

        Rotates the board 4 times (a full 360°) and checks can_move()
        at each rotation. If no rotation allows a move, the game is over.

        Note: 4 clockwise rotations = 360° = back to original orientation,
        so the board is not corrupted by this check.
        """
        found_valid_direction = False
        for rotation in range(0, 4):
            self.rotate_matrix_clockwise()
            if self.can_move():
                found_valid_direction = True
        return not found_valid_direction

    # ========================================================================
    # DEPRECATED METHODS — do not use in new code
    # ========================================================================

    # WARNING: Deprecated — use current_state() instead.
    # Returns a SHALLOW reference to tile_matrix (not a copy), which means
    # modifying the returned matrix would corrupt the game state.
    def get_state(self):
        return (self.tile_matrix, self.score)

    # WARNING: Deprecated — use set_state() instead.
    # Identical to set_state(); kept for backward compatibility.
    def reset(self, init_tile_matrix=None, init_score=0):
        self.undoMat = []
        self.score = init_score
        if init_tile_matrix == None:
            self.tile_matrix = self.new_tile_matrix()
            self.place_random_tile()
            self.place_random_tile()
        else:
            self.tile_matrix = copy.deepcopy(init_tile_matrix)
        self.board_size = len(self.tile_matrix)
