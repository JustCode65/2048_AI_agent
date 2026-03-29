"""
game.py — Grid World & Cell Definitions
=========================================
Defines the Grid (the 2D board) and the Node (an individual cell).
Also holds every color constant and layout value used by the UI.

Terrain types:
  - Empty  (cost 1)  — default open ground
  - Grass  (cost 10) — passable but expensive
  - Wall   (impassable) — blocks movement entirely

The Grid can randomly generate terrain, save/load board layouts
to a file, and draw itself using Pygame.
"""

import random


# ╔══════════════════════════════════════════════╗
#   COLOR PALETTE  (retro pixel-art theme)
# ╚══════════════════════════════════════════════╝

# Core UI colors
BLACK       = (10, 10, 24)
WHITE       = (210, 208, 230)
BG_DARK     = (10, 10, 24)       # Main background
BG_PANEL    = (18, 18, 40)       # Panel / key-hint background

# Grid structure
GRID_LINE_COLOR = (32, 32, 60)

# Cell state colors
CELL_EMPTY         = (14, 14, 32)     # Default empty cell
CELL_WALL          = (28, 85, 165)    # Impassable wall (blue)
CELL_GRASS         = (18, 95, 44)     # Weighted terrain (green, cost 10)
CELL_START         = (235, 195, 35)   # Start position (gold)
CELL_GOAL          = (235, 110, 18)   # Goal position (orange)
CELL_PATH          = (215, 48, 48)    # Final path (red)
CELL_VISITED       = (44, 40, 72)     # Already-explored node (dark purple)
CELL_FRONTIER      = (95, 82, 145)    # In the frontier / queued (lighter purple)
CELL_GRASS_PATH    = (145, 58, 44)    # Path cell that is also grass
CELL_GRASS_VISITED = (42, 65, 52)     # Visited cell that is also grass

# UI accent colors
ACCENT_PURPLE  = (140, 120, 210)
ACCENT_CYAN    = (70, 195, 195)
DIM_TEXT       = (110, 105, 135)
TITLE_GOLD     = (235, 195, 35)
MODE_HIGHLIGHT = (55, 48, 100)

# Legacy aliases so old references still work
GREEN     = CELL_GRASS
GREY      = CELL_FRONTIER
DARKGREY  = CELL_VISITED
GREENGREY = CELL_GRASS_VISITED
RED       = CELL_PATH
REDGREY   = CELL_GRASS_PATH
BLUE      = CELL_WALL
PURPLE    = (128, 80, 180)
GOLD      = CELL_START
YELLOW    = CELL_START
ORANGE    = CELL_GOAL


# ╔══════════════════════════════════════════════╗
#   LAYOUT CONSTANTS
# ╚══════════════════════════════════════════════╝

# Pixel offset of the grid's top-left corner from the window's top-left
GRID_OFFSET = (15, 155)

# Width & height of a single cell in pixels
CELL_SIZE = 16


# ╔══════════════════════════════════════════════╗
#   LEGEND DATA  (used by main.py to draw swatches)
# ╚══════════════════════════════════════════════╝

LEGEND = [
    ("Start",    CELL_START),
    ("Goal",     CELL_GOAL),
    ("Wall",     CELL_WALL),
    ("Grass",    CELL_GRASS),
    ("Path",     CELL_PATH),
    ("Explored", CELL_VISITED),
    ("Frontier", CELL_FRONTIER),
]


# ── Pixel-art bevel helpers ──────────────────────

def _lighten(color, amount=22):
    """Return a brighter version of `color` (clamped at 255)."""
    return tuple(min(255, channel + amount) for channel in color)

def _darken(color, amount=18):
    """Return a darker version of `color` (clamped at 0)."""
    return tuple(max(0, channel - amount) for channel in color)


# ╔══════════════════════════════════════════════╗
#   GRID — the 2D game board
# ╚══════════════════════════════════════════════╝

class Grid:
    """
    A width × height grid of Nodes.

    Attributes:
        width      – number of columns
        height     – number of rows
        nodes      – dict mapping (row, col) → Node
        row_count  – alias for height (used by Pathfinder for bounds checks)
        col_count  – alias for width
        start      – (row, col) of the start cell
        goal       – (row, col) of the goal cell
    """

    def __init__(self, ui=False):
        self.width = 25
        self.height = 25

        # Build every cell in the grid, keyed by (row, col)
        self.nodes = {
            (row, col): Node((row, col))
            for row in range(self.height)
            for col in range(self.width)
        }

        self.row_count = self.height
        self.col_count = self.width

        # Initialize with random terrain and random start/goal
        self.reset_all()
        self.randomize()

    # ── Save / Load ──────────────────────────────

    def save(self, filename):
        """
        Write the board layout to a text file.
        Each cell becomes a single character:
          P = wall, G = grass, S = start, E = goal (end), . = empty
        """
        grid_string = ""
        for row in range(self.height):
            for col in range(self.width):
                node = self.nodes[(row, col)]
                if node.wall:
                    grid_string += "P"
                elif node.grass:
                    grid_string += "G"
                elif node.start:
                    grid_string += "S"
                elif node.goal:
                    grid_string += "E"
                else:
                    grid_string += "."
                grid_string += " "

        with open(filename, "w") as file:
            file.write(grid_string)

    def load(self, grid_string):
        """
        Rebuild the board from a space-separated string of characters.
        Expected format matches save(): P, G, S, E, or a dot.
        """
        for index, char in enumerate(grid_string.split()):
            row = index // self.width
            col = index - (row * self.width)
            coord = (row, col)
            node = self.nodes[coord]
            node.clear_all()

            if char == "P":
                node.set_wall()
            elif char == "G":
                node.set_grass()
            elif char == "S":
                self.set_start(coord)
            elif char == "E":
                self.set_goal(coord)

    # ── State management ─────────────────────────

    def reset(self):
        """Clear only the search visualization (path, visited, frontier colors)."""
        for node in self.nodes.values():
            node.clear_search_state()

    def reset_all(self):
        """Clear everything — terrain, start, goal, and search state."""
        for node in self.nodes.values():
            node.clear_all()

    def clear_path(self):
        """Same as reset — clear search visualization only."""
        for node in self.nodes.values():
            node.clear_search_state()

    # ── Random board generation ──────────────────

    def randomize_empty(self):
        """Reset the board and place start + goal at random positions."""
        self.reset_all()
        all_positions = list(self.nodes.keys())
        start_pos = random.choice(all_positions)
        goal_pos = random.choice(all_positions)
        while goal_pos == start_pos:
            goal_pos = random.choice(all_positions)
        self.set_start(start_pos)
        self.set_goal(goal_pos)

    def randomize(self):
        """Generate a random board with walls, grass, and random start/goal."""
        self.randomize_empty()
        for node in self.nodes.values():
            node.randomly_become_wall()
            node.randomly_become_grass()

    # ── Start / Goal placement ───────────────────

    def set_start(self, position):
        """Move the start marker to `position`, clearing the old one."""
        new_start_node = self.nodes[position]
        if not new_start_node.goal:
            # Remove old start
            for node in self.nodes.values():
                if node.start:
                    node.clear_all()
            new_start_node.clear_all()
            new_start_node.start = True
            self.start = position

    def set_goal(self, position):
        """Move the goal marker to `position`, clearing the old one."""
        new_goal_node = self.nodes[position]
        if not new_goal_node.start:
            # Remove old goal
            for node in self.nodes.values():
                if node.goal:
                    node.clear_all()
            new_goal_node.clear_all()
            new_goal_node.goal = True
            self.goal = position

    # ── Drawing ──────────────────────────────────

    def draw(self, game, pygame):
        """Render the entire grid: cells, grid lines, and border."""
        # Make sure start/goal flags are set on the correct nodes
        self.nodes[self.start].start = True
        self.nodes[self.goal].goal = True

        # Draw every cell
        for node in self.nodes.values():
            node.draw(game, pygame)

        # Draw vertical grid lines
        offset_x, offset_y = GRID_OFFSET
        for col in range(self.width + 1):
            x = CELL_SIZE * col + offset_x
            pygame.draw.line(game.screen, GRID_LINE_COLOR,
                             (x, offset_y),
                             (x, offset_y + CELL_SIZE * self.height))

        # Draw horizontal grid lines
        for row in range(self.height + 1):
            y = CELL_SIZE * row + offset_y
            pygame.draw.line(game.screen, GRID_LINE_COLOR,
                             (offset_x, y),
                             (offset_x + CELL_SIZE * self.width, y))

        # Decorative double border around the grid
        inner_border = (offset_x - 2, offset_y - 2,
                        CELL_SIZE * self.width + 4,
                        CELL_SIZE * self.height + 4)
        pygame.draw.rect(game.screen, ACCENT_PURPLE, inner_border, 1)

        outer_border = (offset_x - 4, offset_y - 4,
                        CELL_SIZE * self.width + 8,
                        CELL_SIZE * self.height + 8)
        pygame.draw.rect(game.screen, _darken(ACCENT_PURPLE, 40), outer_border, 1)


# ╔══════════════════════════════════════════════╗
#   NODE — a single cell in the grid
# ╚══════════════════════════════════════════════╝

class Node:
    """
    Represents one cell in the grid.

    Terrain flags (persistent across searches):
        wall   – impassable obstacle
        grass  – passable but costs 10 instead of 1
        start  – this is the start cell
        goal   – this is the goal cell

    Visualization flags (reset each search):
        is_on_path  – cell is part of the final solution path
        is_visited  – cell has been expanded / explored
        is_frontier – cell is currently in the frontier (queued)
    """

    def __init__(self, position):
        self.position = position
        self.clear_all()

    # ── State clearing ───────────────────────────

    def clear_all(self):
        """Reset everything: terrain, role, and visualization."""
        self.clear_search_state()
        self.wall = False
        self.grass = False
        self.start = False
        self.goal = False

    def clear_search_state(self):
        """Reset only visualization flags (keeps terrain intact)."""
        self.is_on_path = False
        self.is_visited = False
        self.is_frontier = False

    # ── Pygame helpers ───────────────────────────

    def get_rect(self, pygame):
        """Return a (Surface, Rect) pair positioned at this cell's pixel location."""
        pixel_x = self.position[1] * CELL_SIZE + GRID_OFFSET[0]
        pixel_y = self.position[0] * CELL_SIZE + GRID_OFFSET[1]
        surface = pygame.Surface((CELL_SIZE, CELL_SIZE))
        rect = surface.get_rect(topleft=(pixel_x, pixel_y))
        return surface, rect

    # ── Determine which color to display ─────────

    def _pick_color(self):
        """
        Choose the cell's display color based on its current state.
        Priority order: wall > start > goal > path > frontier > visited > grass > empty
        """
        if self.wall:
            return CELL_WALL
        if self.start:
            return CELL_START
        if self.goal:
            return CELL_GOAL
        if self.is_on_path:
            return CELL_GRASS_PATH if self.grass else CELL_PATH
        if self.is_frontier:
            return CELL_FRONTIER
        if self.is_visited:
            return CELL_GRASS_VISITED if self.grass else CELL_VISITED
        if self.grass:
            return CELL_GRASS
        return CELL_EMPTY

    # ── Draw this cell ───────────────────────────

    def draw(self, game, pygame):
        """Render the cell with a pixel-art beveled look."""
        surface, rect = self.get_rect(pygame)
        color = self._pick_color()

        surface.fill(color)

        # Draw a 1-pixel highlight on top-left edges and shadow on bottom-right
        # to give each cell a raised-tile appearance
        edge = CELL_SIZE - 1
        highlight = _lighten(color, 20)
        shadow = _darken(color, 16)

        pygame.draw.line(surface, highlight, (0, 0), (edge, 0))   # top edge
        pygame.draw.line(surface, highlight, (0, 0), (0, edge))   # left edge
        pygame.draw.line(surface, shadow, (0, edge), (edge, edge)) # bottom edge
        pygame.draw.line(surface, shadow, (edge, 0), (edge, edge)) # right edge

        game.screen.blit(surface, rect)

    # ── Terrain setters ──────────────────────────

    def set_wall(self):
        """Make this cell an impassable wall (unless it's start or goal)."""
        if not self.goal and not self.start:
            self.clear_all()
            self.wall = True

    def set_grass(self):
        """Make this cell grass terrain, cost 10 (unless it's start or goal)."""
        if not self.goal and not self.start:
            self.clear_all()
            self.grass = True

    def clear_terrain(self):
        """Remove any terrain from this cell, making it empty."""
        if not self.goal and not self.start:
            self.clear_all()

    def randomly_become_wall(self):
        """~12.5% chance (1 in 9) to become a wall."""
        if not random.randint(0, 8):
            self.set_wall()

    def randomly_become_grass(self):
        """~25% chance (1 in 4) to become grass."""
        if not random.randint(0, 3):
            self.set_grass()

    # ── Movement cost ────────────────────────────

    def cost(self):
        """Return the cost to enter this cell: 10 for grass, 1 for everything else."""
        return 10 if self.grass else 1
