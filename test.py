"""
test.py — Automated Test Runner
==================================
Reads test cases from a file called "tests". Each line contains:
    <bfs_expected_cost> <ucs_expected_cost> <astar_expected_cost> <board_layout...>

For each test case, it runs BFS, UCS, and A* and checks:
  1. The algorithm actually explored nodes (didn't silently fail).
  2. The path cost matches the expected value.
  3. A* explored fewer nodes than UCS (since the heuristic should help).
"""

from ai import Pathfinder
from game import Grid


def test():
    """Run all test cases from the 'tests' file and print results."""
    with open("tests") as file:
        grid = Grid()
        pathfinder = Pathfinder(grid, "dfs")

        lines = file.readlines()

        for test_index, line in enumerate(lines):
            print("test {}/{}: ".format(test_index + 1, len(lines)))

            # Parse the line: first 3 tokens are expected costs, rest is the board
            tokens = line.split()
            expected_costs = {
                "bfs":   int(tokens[0]),
                "ucs":   int(tokens[1]),
                "astar": int(tokens[2]),
            }
            board_layout = " ".join(tokens[3:])
            grid.load(board_layout)

            nodes_explored = {}

            for algorithm in ["bfs", "ucs", "astar"]:
                # Set up and run the algorithm to completion
                pathfinder.set_algorithm(algorithm)
                pathfinder.reset_search()
                while not pathfinder.finished:
                    pathfinder.step()

                # If a path was found, reconstruct it to get the cost
                if not pathfinder.failed:
                    pathfinder.trace_path()

                expected = expected_costs[algorithm]
                actual = pathfinder.path_cost
                nodes_explored[algorithm] = len(pathfinder.visited)

                # ── Check #1: Did the algorithm explore anything? ──
                if nodes_explored[algorithm] == 0:
                    print("\t {} FAILED: No paths explored".format(algorithm))

                # ── Check #2: Does the cost match the expected value? ──
                elif expected != actual:
                    print("\t {} FAILED: expected score of {}, actual {}".format(
                        algorithm, expected, actual))

                # ── Check #3: A* should explore fewer nodes than UCS ──
                elif algorithm == 'astar' and nodes_explored["ucs"] <= nodes_explored["astar"]:
                    print(
                        f"\t astar FAILED: expected fewer explored nodes than ucs, "
                        f"got ucs={nodes_explored['ucs']} and astar={nodes_explored['astar']}")

                else:
                    print("\t {} PASSED".format(algorithm))
