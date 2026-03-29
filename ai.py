"""
ai.py — Pathfinding Algorithms
================================
Implements four classic graph-search algorithms on a 2D grid:
  DFS   (Depth-First Search)
  BFS   (Breadth-First Search)
  UCS   (Uniform-Cost Search)
  A*    (A-Star Search)

Each algorithm can be stepped through one node at a time so the
main game loop can animate the search in real time.
"""

from __future__ import print_function
from heapq import heappop, heappush
from collections import deque

# The four cardinal directions a node can expand into: right, down, left, up.
# Each tuple is (row_offset, col_offset).
DIRECTIONS = [(0, 1), (1, 0), (0, -1), (-1, 0)]


class Pathfinder:
    """
    Runs a chosen search algorithm on a Grid, one step at a time.

    Attributes:
        grid        – the Grid object we're searching on
        algorithm   – which algorithm is active ("dfs", "bfs", "ucs", "astar")
        frontier    – the data structure holding nodes to explore next
        came_from   – dict mapping each visited node → the node we reached it from
        visited     – list of nodes in the order they were expanded
        cost_so_far – (UCS / A* only) cheapest known cost to reach each node
        finished    – True when the search has ended (success or failure)
        failed      – True if the search ended without finding the goal
        path_cost   – total cost of the final path once found
    """

    def __init__(self, grid, algorithm):
        self.grid = grid
        self.set_algorithm(algorithm)
        self.reset_search()

    # ── Algorithm selection ──────────────────────

    def set_algorithm(self, algorithm):
        """Switch to a different search algorithm."""
        self.path_cost = 0
        self.algorithm = algorithm

    # ── Search state management ──────────────────

    def reset_search(self):
        """Clear all search state so a fresh search can begin."""
        self.path_cost = 0
        self.grid.reset()
        self.finished = False
        self.failed = False

        # came_from tracks how we reached each node (for path reconstruction).
        # The start node has no predecessor, so it maps to None.
        self.came_from = {self.grid.start: None}
        self.visited = []

        # Each algorithm uses a different frontier data structure.
        if self.algorithm == "dfs":
            # Stack — last-in, first-out
            self.frontier = [self.grid.start]

        elif self.algorithm == "bfs":
            # Queue — first-in, first-out
            self.frontier = deque([self.grid.start])

        elif self.algorithm == "ucs":
            # Min-heap ordered by cumulative path cost
            self.frontier = []
            self.cost_so_far = {self.grid.start: 0}
            heappush(self.frontier, (0, self.grid.start))

        elif self.algorithm == "astar":
            # Min-heap ordered by (cost-so-far + heuristic)
            self.frontier = []
            self.cost_so_far = {self.grid.start: 0}
            heappush(self.frontier, (self.heuristic(self.grid.start), self.grid.start))

    # ── Heuristic for A* ─────────────────────────

    def heuristic(self, node):
        """
        Manhattan distance from `node` to the goal.
        This is admissible (never overestimates) because we can only
        move in four cardinal directions.
        """
        return abs(node[0] - self.grid.goal[0]) + abs(node[1] - self.grid.goal[1])

    # ── Path reconstruction ──────────────────────

    def trace_path(self):
        """
        Walk backward from the goal to the start using came_from,
        marking each cell as part of the path and summing up the total cost.
        """
        total_cost = 0
        current = self.grid.goal

        # Walk backwards from goal to start
        while current != self.grid.start:
            if self.algorithm == "bfs":
                # BFS treats every edge as cost 1 (unweighted)
                total_cost += 1
            else:
                total_cost += self.grid.nodes[current].cost()

            current = self.came_from[current]
            self.grid.nodes[current].is_on_path = True

        # Add the cost of the start node itself
        total_cost += self.grid.nodes[self.grid.start].cost()
        self.path_cost = total_cost

    # ── Step dispatcher ──────────────────────────

    def step(self):
        """Expand one node using the currently selected algorithm."""
        if self.algorithm == "dfs":
            self._dfs_step()
        elif self.algorithm == "bfs":
            self._bfs_step()
        elif self.algorithm == "ucs":
            self._ucs_step()
        elif self.algorithm == "astar":
            self._astar_step()

    # ── DFS (Depth-First Search) ─────────────────

    def _dfs_step(self):
        """
        Pop from the top of the stack (most recently added node).
        DFS dives deep before backtracking. It does NOT guarantee the
        shortest or cheapest path.
        """
        if not self.frontier:
            self.failed = True
            self.finished = True
            print("No available path found!")
            return

        current = self.frontier.pop()
        self.visited.append(current)

        # Check if we've reached the goal
        if current == self.grid.goal:
            self.finished = True
            return

        # Mark this cell as explored in the visualization
        cell = self.grid.nodes[current]
        cell.is_visited = True
        cell.is_frontier = False

        # Expand neighbors in all four directions
        for row_offset, col_offset in DIRECTIONS:
            neighbor = (current[0] + row_offset, current[1] + col_offset)

            # Check bounds
            if 0 <= neighbor[0] < self.grid.row_count and 0 <= neighbor[1] < self.grid.col_count:
                neighbor_cell = self.grid.nodes[neighbor]

                # Only visit passable cells we haven't seen before
                if not neighbor_cell.wall and neighbor not in self.came_from:
                    self.came_from[neighbor] = current
                    self.frontier.append(neighbor)
                    neighbor_cell.is_frontier = True

    # ── BFS (Breadth-First Search) ───────────────

    def _bfs_step(self):
        """
        Dequeue from the front (oldest node added).
        BFS explores layer by layer and guarantees the shortest path
        in an UNWEIGHTED graph.
        """
        if not self.frontier:
            self.failed = True
            self.finished = True
            print("Unable to reach destination.")
            return

        current = self.frontier.popleft()
        self.visited.append(current)

        if current == self.grid.goal:
            self.finished = True
            return

        cell = self.grid.nodes[current]
        cell.is_visited = True
        cell.is_frontier = False

        for row_offset, col_offset in DIRECTIONS:
            neighbor = (current[0] + row_offset, current[1] + col_offset)

            if 0 <= neighbor[0] < self.grid.row_count and 0 <= neighbor[1] < self.grid.col_count:
                neighbor_cell = self.grid.nodes[neighbor]

                if not neighbor_cell.wall and neighbor not in self.came_from:
                    self.came_from[neighbor] = current
                    self.frontier.append(neighbor)
                    neighbor_cell.is_frontier = True

    # ── UCS (Uniform-Cost Search) ────────────────

    def _ucs_step(self):
        """
        Pop the node with the lowest cumulative cost from the heap.
        UCS guarantees the cheapest path in a WEIGHTED graph, but
        it explores in all directions equally (no heuristic guidance).
        """
        if not self.frontier:
            self.failed = True
            self.finished = True
            print("No solution found.")
            return

        current_cost, current = heappop(self.frontier)
        self.visited.append(current)

        if current == self.grid.goal:
            self.finished = True
            return

        cell = self.grid.nodes[current]
        cell.is_visited = True
        cell.is_frontier = False

        for row_offset, col_offset in DIRECTIONS:
            neighbor = (current[0] + row_offset, current[1] + col_offset)

            if 0 <= neighbor[0] < self.grid.row_count and 0 <= neighbor[1] < self.grid.col_count:
                neighbor_cell = self.grid.nodes[neighbor]

                if not neighbor_cell.wall:
                    new_cost = current_cost + neighbor_cell.cost()

                    # Only update if we found a cheaper route to this neighbor
                    if neighbor not in self.cost_so_far or new_cost < self.cost_so_far[neighbor]:
                        self.cost_so_far[neighbor] = new_cost
                        heappush(self.frontier, (new_cost, neighbor))
                        self.came_from[neighbor] = current
                        neighbor_cell.is_frontier = True

    # ── A* Search ────────────────────────────────

    def _astar_step(self):
        """
        Pop the node with the lowest (cost-so-far + heuristic) from the heap.
        A* combines UCS's cost tracking with a heuristic estimate of
        remaining distance, so it finds the optimal path while typically
        exploring fewer nodes than UCS.
        """
        if not self.frontier:
            self.failed = True
            self.finished = True
            print("Cannot find a path.")
            return

        _, current = heappop(self.frontier)
        self.visited.append(current)

        if current == self.grid.goal:
            self.finished = True
            return

        cell = self.grid.nodes[current]
        cell.is_visited = True
        cell.is_frontier = False

        for row_offset, col_offset in DIRECTIONS:
            neighbor = (current[0] + row_offset, current[1] + col_offset)

            if 0 <= neighbor[0] < self.grid.row_count and 0 <= neighbor[1] < self.grid.col_count:
                neighbor_cell = self.grid.nodes[neighbor]

                if not neighbor_cell.wall:
                    new_cost = self.cost_so_far[current] + neighbor_cell.cost()

                    if neighbor not in self.cost_so_far or new_cost < self.cost_so_far[neighbor]:
                        self.cost_so_far[neighbor] = new_cost
                        priority = new_cost + self.heuristic(neighbor)
                        heappush(self.frontier, (priority, neighbor))
                        self.came_from[neighbor] = current
                        neighbor_cell.is_frontier = True
