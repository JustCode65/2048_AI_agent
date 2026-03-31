# 2048 AI — Expectimax Search

# MAJOR NOTE: finished orginal project in 2025, but made major improvements starting last December of 2025 until end of March 2026 (not improvements in Things I'd try next).

An AI that plays 2048 by looking ahead and picking the best move at each step. Built to explore how expectimax search handles games with randomness, and how far you can push it with better heuristics.

The base game engine is adapted from [this gist](https://gist.github.com/lewisjdeane/752eeba4635b479f8bb2).

## How it works

2048 has two "players" taking turns — you slide tiles in a direction, then the game drops a random 2-tile on the board. That back-and-forth maps perfectly onto **expectimax search**:

- **Your turn (MAX node):** try all 4 directions, pick the one with the best outcome.
- **Game's turn (CHANCE node):** a 2-tile could land on any empty cell with equal probability, so we average over all possibilities.

The basic version builds a depth-3 game tree (you move → tile drops → you move → evaluate) and uses the raw game score at the leaves. It reliably hits 512 tiles and scores above 5,000.

### The improved version

The basic approach works, but I wanted to see how much better it could get. The improved AI (`compute_decision_ec`) makes a few changes:

- **Depth 4 instead of 3** — looks one more step ahead.
- **No tree objects** — instead of building a tree in memory and then traversing it, the search recurses inline. Board mutations at chance nodes are done in-place and undone after recursing, which skips thousands of `deepcopy` calls. Roughly 2x faster.
- **Heuristic evaluation** instead of raw score. Combines five signals:
  - **Snake weights** — rewards keeping big tiles in a corner with values decreasing along a zigzag path. Checked across all 8 board orientations so it adapts if tiles get pushed to a different corner.
  - **Empty cell count** — more breathing room = fewer dead ends.
  - **Monotonicity** — rewards rows/columns that are sorted, which sets up chain merges.
  - **Smoothness penalty** — penalizes big jumps between neighboring tiles (in log₂ space).
  - **Game score + max tile bonus** — keeps the AI grounded in actual progress.

With these changes it hits 2048 in ~80% of games and regularly scores 25,000–37,000.

## Results

Tested over 10 runs with deterministic seeding:

| Version | Avg Score | Hit 2048 | Score ≥ 20k |
|---------|-----------|----------|-------------|
| Basic (depth 3) | ~5,500 | rarely | 0/10 |
| Improved (depth 4 + heuristics) | ~27,000 | 8/10 | 8/10 |

## Setup

Needs Python 3. The GUI requires `pygame`, but the tests run without it.

```bash
pip install pygame
```

## Usage

**Play it yourself:**
```bash
python main.py
```

**Watch the AI play:** press `Enter` to toggle auto-play. Press `E` to switch between the basic and improved AI.

**Run tests:**
```bash
python main.py -t 1    # basic expectimax correctness (15 board states)
python main.py -t 2    # improved AI benchmark (10 full games)
```

### Controls

| Key | What it does |
|-----|-------------|
| Arrow keys | Move tiles manually |
| Enter | Toggle AI auto-play |
| E | Switch between basic / improved AI |
| R | Restart |
| U | Undo last move |
| G | Toggle grayscale mode |

## Project structure

```
├── ai.py       — the AI agent (expectimax search + heuristics)
├── game.py     — game engine (board mechanics, move/merge, scoring)
├── main.py     — entry point (pygame GUI + CLI test runner)
├── test.py     — correctness tests + benchmark suite
├── test_states — 15 pre-computed board states for validation
└── test_sols   — expected expectimax values for each test state
```

## Things I'd try next

- **Transposition table** — cache board evaluations to avoid re-computing duplicate states
- **Adaptive depth** — search deeper when the board is sparse (fewer empty cells = smaller branching factor at chance nodes)
- **Bitboard representation** — pack the whole board into a 64-bit int for faster state manipulation
- **Monte Carlo rollouts** — replace or supplement the heuristic with random playouts to estimate board quality
