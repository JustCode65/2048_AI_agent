# NOTE: Do not modify (for submission). Comments and local variable renames
# added here are for study purposes only.
#
# This file contains two test functions:
#   test()    — verifies the basic depth-3 expectimax returns correct scores
#               on 15 pre-computed board states.
#   test_ec() — runs the extra-credit AI on 10 full games and checks if it
#               achieves a score >= 20,000 on at least 4 of them.

from ai import *
import time


def read_sol_line(line):
    """
    Parse one line from the solutions file.

    Format: "direction_int expected_score"
    Example: "0 4438.222222222223" means the best move is direction 0 (up)
             with an expectimax value of 4438.22.

    Returns:
        (sol_direction, sol_score) — the expected direction and score.
    """
    tokens = line.split(" ")
    sol_direction = int(tokens[0])
    sol_score = float(tokens[1])
    return sol_direction, sol_score


def print_test_result(passed, item_name):
    """Print a PASSED/FAILED message for a specific test item."""
    if passed:
        print("PASSED: Correct {}.".format(item_name))
    else:
        print("FAILED: Incorrect {}.".format(item_name))


# Floating-point tolerance for comparing expectimax scores.
# Scores are computed through many divisions (averaging at chance nodes),
# so tiny floating-point differences are expected.
TOL = 0.001


def test(board_file='test_states', sol_file='test_sols'):
    """
    Test the basic depth-3 expectimax implementation.

    For each of the 15 test boards:
        1. Load the board state into a Game object.
        2. Create an AI with search_depth=3.
        3. Build the full depth-3 game tree.
        4. Run expectimax to get the best move and its value.
        5. Compare the computed score against the known-correct score
           (within floating-point tolerance).

    This tests that build_tree() constructs the correct tree structure
    and that expectimax() computes the correct values at every node.
    """
    game = Game()

    # Read all test boards and their expected solutions
    with open(board_file) as file:
        state_lines = file.readlines()

    with open(sol_file) as file:
        solution_lines = file.readlines()

    for test_index in range(len(state_lines)):
        print("Test {}/{}:".format(test_index + 1, len(state_lines)))

        # Load the board state from the test file
        game.load_state_line(state_lines[test_index])

        # Create AI and build the full tree from this board
        ai = AI(game.current_state(), search_depth=3)
        ai.build_tree(ai.root, ai.search_depth)

        # Run expectimax to get the best direction and its value
        direction, computed_score = ai.expectimax(ai.root)

        # Load the expected answer
        sol_direction, sol_score = read_sol_line(solution_lines[test_index])

        # Check if the computed score matches (within tolerance)
        score_matches = (computed_score >= sol_score - TOL) and (computed_score <= sol_score + TOL)
        print_test_result(score_matches, "expected score")


def get_best_tile(tile_matrix):
    """Return the value of the highest tile on the board."""
    best_tile = 0
    for row in range(0, len(tile_matrix)):
        for col in range(0, len(tile_matrix[row])):
            tile_value = tile_matrix[row][col]
            if tile_value > best_tile:
                best_tile = tile_value
    return best_tile


# ============================================================================
# EXTRA CREDIT TEST CONFIGURATION
# ============================================================================

NUM_TESTS = 10        # run 10 full games
REQ_PASSES = 4        # need at least 4 games with score >= 20,000
MIN_SCORE = 20000     # threshold for a "pass"
TIME_LIMIT = 30       # seconds per game before we give up


def test_ec():
    """
    Test the extra-credit AI by playing 10 full games.

    For each game:
        1. Seed the random number generator (for reproducibility).
        2. Start a fresh game.
        3. Loop: create an AI, call compute_decision_ec(), apply the move.
        4. Stop if the game is over or the 30-second time limit is hit.
        5. Check if the final score >= 20,000.

    The EC AI passes if at least 4 out of 10 games reach 20,000+.

    Note: random.seed(i) ensures the same tile placements happen every run,
    making the test deterministic (same seed = same game = same result).
    """
    game = Game()
    print("Note: each test may take a while to run.")
    passes = 0

    for game_number in range(NUM_TESTS):
        random.seed(game_number)  # deterministic tile placement for this game
        start_time = time.time()
        print("Test {}/{}:".format(game_number + 1, NUM_TESTS))

        game.set_state()  # fresh board with 2 random tiles

        # Play the game until it's over or time runs out
        while not game.game_over():
            ai = AI(game.current_state())
            direction = ai.compute_decision_ec()
            game.move_and_place(direction)

            elapsed = time.time() - start_time
            if elapsed > TIME_LIMIT:
                print("\tTime limit of {} seconds broken. Exiting...".format(TIME_LIMIT))
                break

        # Report results for this game
        print("\tScore/Best Tile: {}/{}".format(game.score, get_best_tile(game.tile_matrix)))
        if game.score >= MIN_SCORE:
            print("\tSUFFICIENT")
            passes += 1
        else:
            print("\tNOT SUFFICIENT (score less than {})".format(MIN_SCORE))

    # Final verdict
    if passes < REQ_PASSES:
        print("FAILED (less than {} passes)".format(REQ_PASSES))
    else:
        print("PASSED")
