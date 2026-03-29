from __future__ import absolute_import, division, print_function
import copy, random, math
from game import Game

# ============================================================================
# CONSTANTS
# ============================================================================

# Maps direction integers to their string names (used by the Game engine).
# 0 = up, 1 = left, 2 = down, 3 = right
MOVES = {0: 'up', 1: 'left', 2: 'down', 3: 'right'}

# The two types of players in the expectimax game tree:
#   MAX_PLAYER  (0) = the human/AI player, who picks the move that maximizes score
#   CHANCE_PLAYER (1) = the computer/random player, who places a 2-tile randomly
MAX_PLAYER, CHANCE_PLAYER = 0, 1


# ============================================================================
# NODE CLASS — one node in the expectimax game tree
# ============================================================================

class Node:
    """
    Represents a single node in the expectimax search tree.

    Attributes:
        state        -- tuple of (tile_matrix, score) representing the board
        player_type  -- MAX_PLAYER or CHANCE_PLAYER
        children     -- list of (move, child_node) pairs
                        - For MAX nodes:    move is a direction int (0-3)
                        - For CHANCE nodes: move is None (random placement)
    """
    def __init__(self, state, player_type):
        self.state = (state[0], state[1])   # (4x4 tile grid, cumulative score)
        self.player_type = player_type
        self.children = []                  # populated by build_tree()

    def is_terminal(self):
        """A node is terminal (a leaf) if it has no children."""
        return not self.children


# ============================================================================
# AI CLASS — expectimax search agent for 2048
# ============================================================================

class AI:
    """
    AI agent that uses expectimax search to decide moves in 2048.

    Two modes:
        compute_decision()    -- basic depth-3 expectimax using raw game score
        compute_decision_ec() -- extra-credit version with deeper search + heuristics
    """

    def __init__(self, root_state, search_depth=3):
        """
        Args:
            root_state   -- tuple (tile_matrix, score) for the current board
            search_depth -- how many levels deep to build the game tree (default 3)
        """
        self.root = Node(root_state, MAX_PLAYER)   # root of the search tree
        self.depth_limit = search_depth             # used internally by build_tree
        self.search_depth = search_depth            # exposed for test.py to read
        self.sim = Game(*root_state)                # simulator to try moves without affecting real game

    # ========================================================================
    # PART 1: Standard depth-3 expectimax (DO NOT MODIFY)
    # ========================================================================

    def build_tree(self, current=None, remaining_levels=None):
        """
        Recursively builds the full expectimax game tree from `current` down
        to `remaining_levels` depth.

        Tree structure (depth-3 example):
            Level 0 (root)  -- MAX_PLAYER:    tries all 4 directions
            Level 1         -- CHANCE_PLAYER: tries placing a 2 on every empty cell
            Level 2         -- MAX_PLAYER:    tries all 4 directions again
            Level 3         -- terminal leaves (no children, just score)

        For MAX nodes: each child is the board state after moving in one direction.
        For CHANCE nodes: each child is the board state after placing a 2 on one empty cell.
        """
        node = current or self.root
        depth_left = remaining_levels if remaining_levels is not None else self.depth_limit

        # Base case: we've reached the desired depth, so this node becomes a leaf.
        if depth_left == 0:
            return

        board, score = node.state

        if node.player_type == MAX_PLAYER:
            # --- MAX NODE: try each of the 4 possible moves ---
            for direction, _name in MOVES.items():
                # Load this node's board into the simulator and try the move
                self.sim.set_state(board, score)
                if not self.sim.move(direction):
                    continue  # illegal move (nothing shifted), skip it

                # The move succeeded -- capture the resulting board and score
                new_board, new_score = self.sim.current_state()
                child = Node((new_board, new_score), CHANCE_PLAYER)
                node.children.append((direction, child))

                # Recurse: build the subtree below this child
                self.build_tree(child, depth_left - 1)
        else:
            # --- CHANCE NODE: try placing a 2-tile on each empty cell ---
            for row in range(len(board)):
                for col in range(len(board[0])):
                    if board[row][col] == 0:
                        # Create a new board with a 2 placed at (row, col)
                        new_board = copy.deepcopy(board)
                        new_board[row][col] = 2
                        child = Node((new_board, score), MAX_PLAYER)
                        node.children.append((None, child))  # None = no "move" for chance

                        # Recurse: build the subtree below this child
                        self.build_tree(child, depth_left - 1)

    def expectimax(self, n=None):
        """
        Recursively computes the expectimax value of the game tree.

        Returns:
            (best_move, value)
            - best_move: the direction int (0-3) to play (only meaningful at MAX nodes)
            - value:     the expectimax score of this node

        At MAX nodes:    returns the move with the highest child value.
        At CHANCE nodes: returns the average value across all children.
        At leaf nodes:   returns the raw game score from the state.
        """
        node = n or self.root

        # Base case: leaf node -- return the raw game score
        if node.is_terminal():
            return None, node.state[1]

        if node.player_type == MAX_PLAYER:
            # --- MAX NODE: pick the child with the highest value ---
            best_value = float('-inf')
            best_move = None
            for move, child in node.children:
                _, child_value = self.expectimax(child)
                if child_value > best_value:
                    best_value = child_value
                    best_move = move
            return best_move, best_value
        else:
            # --- CHANCE NODE: compute the average value across all children ---
            # Each empty cell is equally likely, so every child has equal weight.
            total = 0
            for _, child in node.children:
                _, child_value = self.expectimax(child)
                total += child_value
            average = total / len(node.children) if node.children else 0
            return None, average

    def compute_decision(self):
        """
        Main entry point for the basic AI.
        Builds the full depth-3 tree, runs expectimax, returns the best move.
        """
        self.build_tree()
        best_move, _value = self.expectimax()
        return best_move

    # ========================================================================
    # PART 2: Extra Credit -- stronger AI with heuristics + inline search
    # ========================================================================
    #
    # Key improvements over Part 1:
    #   1. Inline recursive search (no tree/Node objects) -- much faster
    #   2. Searches to depth 4 instead of 3
    #   3. Uses a weighted heuristic instead of raw score at leaf nodes
    #   4. Snake-weight pattern evaluated in all 8 orientations
    #   5. Monotonicity + smoothness penalties
    # ========================================================================

    # --- Pre-computed weight grids for the "snake" heuristic ---
    # Filled once by _init_snake_weights(), then shared across all AI instances.
    _all_snake_weight_grids = []

    @staticmethod
    def _init_snake_weights():
        """
        Pre-compute 8 orientations (4 rotations x 2 mirrors) of the snake
        weight matrix. The snake pattern assigns exponentially decreasing
        weights in a zigzag path, rewarding boards where large tiles sit
        in a corner and smaller tiles trail outward in order.

        Base pattern (top-left corner):
            32768  16384  8192  4096
              256    512  1024  2048
              128     64    32    16
                1      2     4     8

        By checking all 8 orientations, the AI does not get stuck favoring
        only one corner -- it adapts if tiles get pushed elsewhere.
        """
        if AI._all_snake_weight_grids:
            return  # already initialized

        base_weights = [
            [2**15, 2**14, 2**13, 2**12],
            [2**8,  2**9,  2**10, 2**11],
            [2**7,  2**6,  2**5,  2**4],
            [2**0,  2**1,  2**2,  2**3],
        ]

        # Generate all unique orientations using rotation + mirror
        unique_grids = set()
        grid = [row[:] for row in base_weights]

        for _ in range(4):
            # Add this rotation as a hashable tuple-of-tuples
            frozen = tuple(tuple(row) for row in grid)
            unique_grids.add(frozen)

            # Add its horizontal mirror (flip each row left-to-right)
            mirrored = tuple(tuple(row[::-1]) for row in grid)
            unique_grids.add(mirrored)

            # Rotate 90 degrees clockwise for the next iteration
            grid = [list(row) for row in zip(*grid[::-1])]

        # Convert back to mutable lists for fast access during search
        AI._all_snake_weight_grids = [
            [list(row) for row in frozen_grid]
            for frozen_grid in unique_grids
        ]

    def _best_snake_score(self, board):
        """
        Compute the snake-weighted sum of the board for each of the 8
        orientations and return the highest one.

        The idea: multiply each tile value by the weight at its position.
        A board where big tiles line up along the snake path scores high.
        """
        best = float('-inf')
        for weight_grid in AI._all_snake_weight_grids:
            weighted_sum = 0
            for row in range(4):
                for col in range(4):
                    weighted_sum += board[row][col] * weight_grid[row][col]
            if weighted_sum > best:
                best = weighted_sum
        return best

    @staticmethod
    def _monotonicity(board):
        """
        Measure how "sorted" each row and column is.

        For each row/column, compute two sums:
            increasing_sum = total amount by which values go up left-to-right
            decreasing_sum = total amount by which values go down left-to-right
        Then take the larger of the two (the dominant direction).

        A perfectly sorted row contributes a large value. A jumbled row
        contributes less. Higher total = board is more orderly.
        """
        total_score = 0

        # Check each row (left-to-right)
        for row in range(4):
            increasing = 0
            decreasing = 0
            for col in range(3):
                left_val = board[row][col]
                right_val = board[row][col + 1]
                if left_val >= right_val:
                    decreasing += left_val - right_val
                if left_val <= right_val:
                    increasing += right_val - left_val
            total_score += max(increasing, decreasing)

        # Check each column (top-to-bottom)
        for col in range(4):
            increasing = 0
            decreasing = 0
            for row in range(3):
                top_val = board[row][col]
                bottom_val = board[row + 1][col]
                if top_val >= bottom_val:
                    decreasing += top_val - bottom_val
                if top_val <= bottom_val:
                    increasing += bottom_val - top_val
            total_score += max(increasing, decreasing)

        return total_score

    @staticmethod
    def _smoothness(board):
        """
        Measure how "rough" the board is by summing the absolute differences
        between adjacent tiles (in log2 space).

        Lower smoothness = tiles are closer in value to their neighbors,
        which means more merge opportunities. We use this as a PENALTY
        (subtracted in the heuristic).
        """
        penalty = 0.0
        for row in range(4):
            for col in range(4):
                tile_value = board[row][col]
                if tile_value == 0:
                    continue
                log_val = math.log2(tile_value)

                # Compare with right neighbor
                if col + 1 < 4 and board[row][col + 1] != 0:
                    penalty += abs(log_val - math.log2(board[row][col + 1]))

                # Compare with bottom neighbor
                if row + 1 < 4 and board[row + 1][col] != 0:
                    penalty += abs(log_val - math.log2(board[row + 1][col]))

        return penalty

    @staticmethod
    def _max_tile(board):
        """Return the value of the largest tile on the board."""
        return max(board[row][col] for row in range(4) for col in range(4))

    def _evaluate_board(self, board, score):
        """
        Heuristic evaluation function for leaf nodes in the EC search.

        Combines five signals into a single score:
            + snake_score     -- rewards large tiles along the snake gradient
            + empty_count     -- more empty cells = more room to maneuver
            + monotonicity    -- rewards rows/columns that are sorted
            - smoothness      -- penalizes big jumps between neighbors
            + game_score      -- the actual cumulative merge score
            + max_tile_bonus  -- small bonus for having a high max tile

        The weights (2000, 100, 300, 2, 500) were tuned experimentally.
        """
        empty_count = sum(
            1 for row in range(4) for col in range(4) if board[row][col] == 0
        )
        snake_score = self._best_snake_score(board)
        monotonicity_score = self._monotonicity(board)
        smoothness_penalty = self._smoothness(board)
        highest_tile = self._max_tile(board)

        return (
            snake_score
            + empty_count * 2000
            + monotonicity_score * 100
            - smoothness_penalty * 300
            + score * 2
            + (math.log2(highest_tile) * 500 if highest_tile else 0)
        )

    def _recursive_expectimax(self, board, score, depth, is_max_player):
        """
        Inline recursive expectimax -- searches without building a tree.

        Instead of creating Node objects and storing them, this function
        recurses directly, passing the board state as arguments. This avoids
        the memory and time cost of deepcopy + object allocation.

        At chance nodes, we mutate the board in-place (place a 2, recurse,
        then set it back to 0) to avoid copying. This is safe because the
        recursion fully finishes before we undo the change.

        Args:
            board          -- the 4x4 tile grid (list of lists)
            score          -- the cumulative game score
            depth          -- how many more levels to search
            is_max_player  -- True if this level is a MAX node, False for CHANCE

        Returns:
            The heuristic value of this state (a float).
        """
        # Base case: reached the depth limit -- evaluate the board
        if depth == 0:
            return self._evaluate_board(board, score)

        if is_max_player:
            # --- MAX LAYER: try all 4 directions, keep the best ---
            best_value = float('-inf')
            found_valid_move = False

            for direction in range(4):
                # Load the board into the simulator and try this move
                self.sim.set_state(board, score)
                if not self.sim.move(direction):
                    continue  # illegal move, skip

                found_valid_move = True
                new_board, new_score = self.sim.current_state()
                value = self._recursive_expectimax(
                    new_board, new_score, depth - 1, False
                )
                if value > best_value:
                    best_value = value

            # If no moves were legal, this is effectively a game-over leaf
            return best_value if found_valid_move else self._evaluate_board(board, score)

        else:
            # --- CHANCE LAYER: try placing a 2 on every empty cell ---
            empty_cells = [
                (row, col)
                for row in range(4)
                for col in range(4)
                if board[row][col] == 0
            ]

            if not empty_cells:
                return self._evaluate_board(board, score)

            value_sum = 0.0
            for row, col in empty_cells:
                # Place a 2-tile temporarily (in-place mutation)
                board[row][col] = 2
                value_sum += self._recursive_expectimax(
                    board, score, depth - 1, True
                )
                board[row][col] = 0  # undo the placement

            # Each empty cell is equally likely, so take the average
            return value_sum / len(empty_cells)

    def compute_decision_ec(self):
        """
        Extra credit entry point: uses deeper search + heuristic evaluation.

        Process:
            1. Initialize the snake weight grids (only runs once)
            2. Get the current board state
            3. For each legal move, run inline expectimax to depth 4
            4. Pick the move with the highest heuristic value
        """
        AI._init_snake_weights()
        board, score = self.sim.current_state()

        search_depth = 4  # deeper than the basic depth-3

        best_move = None
        best_value = float('-inf')

        for direction in range(4):
            # Try this move on the simulator
            self.sim.set_state(board, score)
            if not self.sim.move(direction):
                continue  # illegal move

            new_board, new_score = self.sim.current_state()
            value = self._recursive_expectimax(
                new_board, new_score, search_depth - 1, False
            )

            if value > best_value:
                best_value = value
                best_move = direction

        return best_move
