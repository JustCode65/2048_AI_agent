# Pathfinding Visualizer

A real-time visualizer for four classic graph search algorithms built with Python and Pygame. Drop walls and weighted terrain onto a grid, pick an algorithm, and watch it find the path step by step.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Pygame](https://img.shields.io/badge/Pygame-2.x-green)

## Why I Built This

I wanted to actually *see* how DFS, BFS, UCS, and A\* behave differently on the same board — not just read about them in a textbook. The idea is simple: slow the algorithm down to one step per frame so you can watch the frontier expand, see which nodes get explored, and compare how each algorithm approaches the same problem.

It's also a good way to build intuition for *when* each algorithm matters. BFS finds the shortest path by steps but ignores terrain cost. UCS handles weighted terrain but explores blindly in every direction. A\* does what UCS does but smarter, because the heuristic pulls it toward the goal. And DFS just does its own thing — it'll find *a* path, but don't expect it to be a good one.

## Algorithms

| Algorithm | Data Structure | Optimal? | Notes |
|-----------|---------------|----------|-------|
| **DFS** | Stack | No | Dives deep, backtracks. Fast but finds bad paths. |
| **BFS** | Queue | Yes (unweighted) | Explores in layers. Shortest path by step count. |
| **UCS** | Min-Heap | Yes (weighted) | Expands cheapest node first. Same as Dijkstra's. |
| **A\*** | Min-Heap | Yes (weighted) | UCS + Manhattan distance heuristic. Fewer nodes explored. |

## How It Works

The grid is 25×25. Each cell is one of:
- **Empty** — costs 1 to enter
- **Grass** (green) — costs 10 to enter
- **Wall** (blue) — impassable

You place a start point (gold) and a goal point (orange), then hit Enter. The algorithm runs one node per frame at 60fps so you can watch the search happen live. Explored nodes turn dark purple, the frontier is light purple, and the final path is red.

## Setup

You'll need Python 3 and Pygame.

```bash
pip install pygame
```

If you want to use a virtual environment (recommended):

```bash
conda create -n pathfinding python=3.12
conda activate pathfinding
pip install pygame
```

## Usage

```bash
python main.py
```

### Controls

| Key | What it does |
|-----|-------------|
| `Enter` | Start search / pause / resume |
| `C` | Clear the search visualization |
| `1` `2` `3` `4` | Switch to DFS / BFS / UCS / A\* |
| `M` | Generate a new random board |
| `N` | Generate an empty board (just start + goal) |
| `S` | Set start at mouse position |
| `G` | Set goal at mouse position |
| `P` | Place a wall at mouse position |
| `R` | Place grass at mouse position |
| `X` | Clear the cell at mouse position |
| `W` / `L` | Save / load board layout |
| `Esc` | Quit |

### Loading test boards

There's a `tests` file with 52 predefined boards. You can load any of them:

```bash
python main.py -l 0    # load test case 0
python main.py -l 1    # load test case 1
```

A couple of the boards have fun pixel-art patterns in them. The rest are randomly generated stress tests.

### Running tests

```bash
python main.py -t
```

This runs BFS, UCS, and A\* on every test board and checks that:
1. The path cost matches the expected optimal cost
2. A\* explores fewer nodes than UCS (validates the heuristic is actually helping)

DFS isn't tested because it doesn't guarantee optimal paths — there's no single correct cost to check against.

## Project Structure

```
├── main.py     # Pygame window, input handling, game loop
├── ai.py       # The four search algorithms (Pathfinder class)
├── game.py     # Grid and Node classes, colors, layout constants
├── test.py     # Automated test runner
└── tests       # 52 predefined board layouts with expected costs
```

The algorithms in `ai.py` don't know anything about Pygame — they just operate on a Grid. This means you can run them headlessly (which is what the test runner does) or swap out the rendering without touching the search logic.

## Things I'd Add Next

- Click-and-drag to paint walls instead of hovering + pressing P
- Speed slider to control how many nodes expand per frame
- Bidirectional search
- Jump Point Search for uniform-cost grids
- Side-by-side mode to run two algorithms on the same board simultaneously
