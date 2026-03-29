"""
main.py — Application Entry Point
====================================
Creates the Pygame window, handles user input, and runs the main
game loop. This is the file you run to start the visualizer.

Usage:
    python main.py          – launch the GUI
    python main.py -t       – run automated tests (no GUI)
    python main.py -l 3     – launch GUI and load test case #3
"""

import sys
import random
from ai import Pathfinder
from game import (Grid, WHITE, BLACK, CELL_SIZE, GRID_OFFSET,
                  BG_DARK, BG_PANEL, ACCENT_PURPLE, ACCENT_CYAN,
                  DIM_TEXT, TITLE_GOLD, MODE_HIGHLIGHT, LEGEND,
                  CELL_EMPTY, CELL_START, CELL_GOAL)
from test import test
import argparse

# Fixed seed so the random board is the same every launch (for debugging)
random.seed(0)


# ── Layout constants ─────────────────────────────

SCREEN_WIDTH  = 430
SCREEN_HEIGHT = 620
GRID_PIXEL_WIDTH  = CELL_SIZE * 25    # 400 px
GRID_PIXEL_HEIGHT = CELL_SIZE * 25    # 400 px
GRID_BOTTOM_Y = GRID_OFFSET[1] + GRID_PIXEL_HEIGHT  # y where the grid ends

# Maps internal algorithm keys to display names
ALGO_DISPLAY_NAMES = {
    "dfs":   "DFS",
    "bfs":   "BFS",
    "ucs":   "UCS",
    "astar": "A*",
}

# Order in which algorithms appear in the tab bar
ALGO_ORDER = ["dfs", "bfs", "ucs", "astar"]

# Keyboard shortcuts for each algorithm
ALGO_HOTKEYS = {"dfs": "1", "bfs": "2", "ucs": "3", "astar": "4"}


# ╔══════════════════════════════════════════════╗
#   GRID WORLD — Main Application
# ╚══════════════════════════════════════════════╝

class GridWorld:
    """
    The main application. Sets up Pygame, owns the Grid and Pathfinder,
    handles keyboard/mouse input, and drives the animation loop.
    """

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Pathfinding Visualizer")

        self.clock = pygame.time.Clock()
        self.last_tick = pygame.time.get_ticks()
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE, 32
        )

        # Fonts — monospace for a retro terminal look
        self.font       = pygame.font.SysFont("Consolas", 14)
        self.font_title = pygame.font.SysFont("Consolas", 22, bold=True)
        self.font_small = pygame.font.SysFont("Consolas", 13)
        self.font_mode  = pygame.font.SysFont("Consolas", 15, bold=True)

        # Application state
        self.show_checked = True
        self.quit = False
        self.current_algorithm = "dfs"
        self.grid = Grid(True)
        self.pathfinder = Pathfinder(self.grid, self.current_algorithm)
        self.is_running = False   # True while a search is actively animating
        self.is_paused = False

    # ── Main loop ────────────────────────────────

    def loop(self):
        """Run forever: draw, advance the search, handle events."""
        while True:
            self.draw()
            self.clock.tick(60)  # Cap at 60 FPS
            self.mouse_pos = pygame.mouse.get_pos()

            # If a search is running and not paused, advance one step per frame
            if self.is_running and not self.is_paused:
                if self.pathfinder.finished:
                    # Search just ended — trace the path if it succeeded
                    if not self.pathfinder.failed:
                        self.pathfinder.trace_path()
                    self.is_running = False
                else:
                    self.pathfinder.step()

            # ── Event handling ───────────────────
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == KEYDOWN:
                    # ── Always-available keys ────
                    if event.key == K_ESCAPE:
                        pygame.quit()
                        sys.exit()

                    # Clear the current search visualization
                    if event.key == K_c:
                        self.pathfinder.reset_search()
                        self.is_running = False

                    # Start a new search, or pause/resume the current one
                    if event.key == K_RETURN:
                        if not self.is_running:
                            self.pathfinder.reset_search()
                            self.is_running = True
                            self.is_paused = False
                        else:
                            self.is_paused = not self.is_paused

                    # Switch algorithm with number keys
                    if event.key == K_1:
                        self._switch_algorithm("dfs")
                    if event.key == K_2:
                        self._switch_algorithm("bfs")
                    if event.key == K_3:
                        self._switch_algorithm("ucs")
                    if event.key == K_4:
                        self._switch_algorithm("astar")

                    # ── Board-editing keys (disabled while searching) ──
                    if not self.is_running:
                        # Save / load board
                        if event.key == K_w:
                            self.grid.save("saved_grid")
                        if event.key == K_l:
                            try:
                                with open("saved_grid") as file:
                                    self.grid.load(file.read())
                            except Exception:
                                print("no saved file present")

                        # Generate new random boards
                        if event.key == K_m:
                            self.grid.randomize()
                        if event.key == K_n:
                            self.grid.randomize_empty()

                        # Per-cell editing: hover over a cell and press a key
                        for node in self.grid.nodes.values():
                            if node.get_rect(pygame)[1].collidepoint(self.mouse_pos):
                                if event.key == K_p:
                                    self.grid.reset()
                                    node.set_wall()
                                if event.key == K_r:
                                    self.grid.reset()
                                    node.set_grass()
                                if event.key == K_x:
                                    self.grid.reset()
                                    node.clear_terrain()
                                if event.key == K_s:
                                    self.grid.reset()
                                    self.grid.set_start(node.position)
                                if event.key == K_g:
                                    self.grid.reset()
                                    self.grid.set_goal(node.position)

    def _switch_algorithm(self, algorithm):
        """Change the active algorithm and reset any in-progress search."""
        if self.current_algorithm != algorithm:
            self.grid.clear_path()
            self.is_running = False
            self.is_paused = False
        self.current_algorithm = algorithm
        self.pathfinder.set_algorithm(self.current_algorithm)

    # ── Drawing ──────────────────────────────────

    def draw(self):
        """Redraw the entire screen: background, header, grid, footer."""
        self.screen.fill(BG_DARK)
        self._draw_header()
        self.grid.draw(self, pygame)
        self._draw_footer()
        pygame.display.update()

    # ── Header panel ─────────────────────────────

    def _draw_header(self):
        """Draw the title, keyboard shortcuts, and algorithm tabs."""
        # Centered title
        title_surface = self.font_title.render("PATHFINDING VISUALIZER", True, TITLE_GOLD)
        title_x = SCREEN_WIDTH // 2 - title_surface.get_width() // 2
        self.screen.blit(title_surface, (title_x, 6))

        # Decorative line under title
        line_y = 34
        pygame.draw.line(self.screen, ACCENT_PURPLE,
                         (GRID_OFFSET[0], line_y),
                         (SCREEN_WIDTH - GRID_OFFSET[0], line_y))

        # Controls — compact two-column layout
        controls_y = 42
        left_controls = [
            ("Enter", "search/pause"),
            ("C", "clear path"),
            ("M", "random board"),
            ("N", "clear board"),
        ]
        right_controls = [
            ("S/G", "start/goal"),
            ("P/R", "puddle/grass"),
            ("X", "clear node"),
            ("W/L", "save/load"),
        ]

        for i, (key, description) in enumerate(left_controls):
            self._draw_key_hint(GRID_OFFSET[0], controls_y + i * 18, key, description)

        for i, (key, description) in enumerate(right_controls):
            self._draw_key_hint(SCREEN_WIDTH // 2 + 5, controls_y + i * 18, key, description)

        # Algorithm selector tabs (just above the grid)
        self._draw_algo_tabs(y=GRID_OFFSET[1] - 30)

    def _draw_key_hint(self, x, y, key_label, description):
        """Draw a styled keyboard hint like [C] clear path."""
        key_surface = self.font_small.render(key_label, True, ACCENT_CYAN)
        desc_surface = self.font_small.render(description, True, DIM_TEXT)

        # Draw a small bordered box around the key name
        key_width = key_surface.get_width()
        pygame.draw.rect(self.screen, BG_PANEL, (x, y - 1, key_width + 6, 16))
        pygame.draw.rect(self.screen, ACCENT_CYAN, (x, y - 1, key_width + 6, 16), 1)

        self.screen.blit(key_surface, (x + 3, y))
        self.screen.blit(desc_surface, (x + key_width + 10, y))

    def _draw_algo_tabs(self, y):
        """Draw the algorithm selector as a row of retro tab buttons."""
        tab_width = 70
        gap = 6
        total_width = tab_width * len(ALGO_ORDER) + gap * (len(ALGO_ORDER) - 1)
        start_x = SCREEN_WIDTH // 2 - total_width // 2

        for i, algo in enumerate(ALGO_ORDER):
            x = start_x + i * (tab_width + gap)
            is_active = (self.current_algorithm == algo)

            # Tab background and border change when active
            bg_color = MODE_HIGHLIGHT if is_active else BG_PANEL
            border_color = ACCENT_CYAN if is_active else DIM_TEXT
            pygame.draw.rect(self.screen, bg_color, (x, y, tab_width, 18))
            pygame.draw.rect(self.screen, border_color, (x, y, tab_width, 18), 1)

            # Label like "1:DFS"
            label_text = "{}:{}".format(ALGO_HOTKEYS[algo], ALGO_DISPLAY_NAMES[algo])
            text_color = WHITE if is_active else DIM_TEXT
            label_surface = self.font_small.render(label_text, True, text_color)
            label_x = x + tab_width // 2 - label_surface.get_width() // 2
            self.screen.blit(label_surface, (label_x, y + 2))

    # ── Footer panel ─────────────────────────────

    def _draw_footer(self):
        """Draw the status bar (mode + cost) and color legend below the grid."""
        footer_y = GRID_BOTTOM_Y + 10

        # Separator line
        pygame.draw.line(self.screen, ACCENT_PURPLE,
                         (GRID_OFFSET[0], footer_y - 4),
                         (SCREEN_WIDTH - GRID_OFFSET[0], footer_y - 4))

        # Determine what to show for the cost display
        if self.pathfinder.finished and not self.pathfinder.failed:
            cost_text = str(self.pathfinder.path_cost)
            cost_color = CELL_START
        elif self.pathfinder.finished and self.pathfinder.failed:
            cost_text = "NO PATH"
            cost_color = (215, 48, 48)
        elif self.is_running:
            cost_text = "..."
            cost_color = ACCENT_CYAN
        else:
            cost_text = "READY"
            cost_color = DIM_TEXT

        # Render "MODE: A*" on the left and "COST: 42" on the right
        mode_surface = self.font_mode.render(
            "MODE: {}".format(ALGO_DISPLAY_NAMES[self.current_algorithm]), True, WHITE)
        cost_label_surface = self.font_mode.render("COST: ", True, WHITE)
        cost_value_surface = self.font_mode.render(cost_text, True, cost_color)

        self.screen.blit(mode_surface, (GRID_OFFSET[0], footer_y))
        cost_x = (SCREEN_WIDTH - GRID_OFFSET[0]
                  - cost_label_surface.get_width()
                  - cost_value_surface.get_width())
        self.screen.blit(cost_label_surface, (cost_x, footer_y))
        self.screen.blit(cost_value_surface,
                         (cost_x + cost_label_surface.get_width(), footer_y))

        # Color legend row
        self._draw_legend(footer_y + 22)

    def _draw_legend(self, y):
        """Draw a compact, centered row of color swatches with labels."""
        swatch_size = 8
        padding = 6

        # Pre-render all label surfaces to calculate total width
        label_surfaces = []
        total_width = 0
        for name, color in LEGEND:
            surface = self.font_small.render(name, True, DIM_TEXT)
            label_surfaces.append(surface)
            total_width += swatch_size + 3 + surface.get_width() + padding

        # Draw centered
        x = SCREEN_WIDTH // 2 - total_width // 2
        for (name, color), label_surface in zip(LEGEND, label_surfaces):
            # Color swatch with a thin border
            pygame.draw.rect(self.screen, color, (x, y + 1, swatch_size, swatch_size))
            pygame.draw.rect(self.screen, DIM_TEXT, (x, y + 1, swatch_size, swatch_size), 1)
            x += swatch_size + 3
            self.screen.blit(label_surface, (x, y - 1))
            x += label_surface.get_width() + padding


# ── CLI argument parsing ─────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument('-t', action='store_true', help='run automated tests')
parser.add_argument('--load', '-l', dest='load_num', type=int,
                    default=-1, help='test map number to load at startup')
args = parser.parse_args()


# ── Entry point ──────────────────────────────────

if __name__ == '__main__':
    if args.t:
        # Run tests without launching the GUI
        test()
    else:
        import pygame
        from pygame.locals import *

        game = GridWorld()

        # Optionally load a specific test map at startup
        with open("tests") as file:
            lines = file.readlines()
            if args.load_num in range(len(lines)):
                print("loading test case {}...".format(args.load_num))
                game.grid.load(" ".join(lines[args.load_num].split()[3:]))

        game.loop()
