# NOTE: Do not modify (for submission). Comments and local variable renames
# added here are for study purposes only.
#
# This is the entry point for the 2048 program. It has three modes:
#   python main.py        → launches the GUI game (requires pygame)
#   python main.py -t 1   → runs the basic depth-3 expectimax tests
#   python main.py -t 2   → runs the extra-credit AI tests

from __future__ import absolute_import, division, print_function
import sys, time, math, random, os, argparse
from game import Game
from ai import AI
from test import test, test_ec

# Fix the random seed so results are reproducible across runs.
random.seed(0)

# ============================================================================
# COLOR DEFINITIONS (for the pygame GUI)
# ============================================================================

MAXC = 255  # maximum color channel value (used for grayscale calculation)

# RGB color tuples for the UI
WHITE       = (240, 240, 240)
BLACK       = (0, 0, 0)
RED         = (244, 67, 54)
PINK        = (234, 30, 99)
PURPLE      = (156, 39, 176)
DEEP_PURPLE = (103, 58, 183)
BLUE        = (33, 150, 243)
TEAL        = (0, 150, 136)
L_GREEN     = (139, 195, 74)
GREEN       = (60, 175, 80)
ORANGE      = (255, 152, 0)
DEEP_ORANGE = (255, 87, 34)
BROWN       = (121, 85, 72)

# Map each tile value to its display color.
# Higher tile values get distinct colors so you can see the board at a glance.
COLORS = {
    0: WHITE,       2: RED,         4: PINK,        8: PURPLE,
    16: DEEP_PURPLE, 32: BLUE,      64: TEAL,       128: L_GREEN,
    256: GREEN,     512: ORANGE,    1024: DEEP_ORANGE, 2048: BROWN,
    4096: DEEP_PURPLE, 8192: DEEP_ORANGE, 16384: BROWN, 32768: TEAL
}

# ============================================================================
# LAYOUT CONSTANTS
# ============================================================================

BOARD_SIZE_PX = 400          # total width/height of the board area in pixels
BOARD_Y_OFFSET_PX = 50       # vertical offset to leave room for the score label
TEXT_X_OFFSET_PX = 10         # text padding inside each tile
TEXT_Y_OFFSET_PX = 10
SCORE_LABEL_POS = (10, 10)   # where "Score: X" is drawn
EC_LABEL_POS = (350, 10)     # where "[EC]" indicator is drawn

PADDING = 5                   # padding around text highlight boxes
MAX_CORD = 13                 # max color order (for grayscale mode: log2 cap)


# ============================================================================
# GAME RUNNER — the pygame GUI wrapper
# ============================================================================

class GameRunner:
    """
    Manages the pygame window, user input, and render loop.

    Controls:
        Arrow keys  — manual moves (up/down/left/right)
        Enter       — toggle AI auto-play on/off
        E           — toggle extra-credit AI mode
        R           — restart with a fresh board
        U           — undo the last move
        3-7         — change board size
        S           — save game state to file
        L           — load game state from file
        G           — toggle grayscale rendering
    """

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("2048")
        self.surface = pygame.display.set_mode(
            (BOARD_SIZE_PX, BOARD_SIZE_PX + BOARD_Y_OFFSET_PX), 0, 32
        )
        self.myfont = pygame.font.SysFont("arial", 20)       # font for tile numbers
        self.scorefont = pygame.font.SysFont("arial", 20)     # font for score/labels

        self.grayscale = False    # if True, render tiles as grayscale shades
        self.game = Game()        # the actual game instance
        self.auto = False         # if True, AI plays automatically each frame
        self.ec = False           # if True, use extra-credit AI instead of basic

    def loop(self):
        """
        Main game loop. Runs forever until the window is closed.

        Each iteration:
            1. Check for game-over (if so, stop auto-play)
            2. Process keyboard/window events
            3. If auto-play is on, ask the AI for a move
            4. Apply the move (if any)
            5. Redraw the board
        """
        while True:
            game_over = self.game.game_over()
            if game_over:
                self.auto = False  # stop AI when the game ends

            direction = None  # will be set if the player/AI chooses a move

            # --- Process all pending pygame events ---
            for event in pygame.event.get():
                if not game_over:
                    if event.type == KEYDOWN:
                        if self.is_arrow(event.key):
                            direction = ROTATIONS[event.key]

                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == KEYDOWN:
                    if event.key == K_RETURN:
                        # Toggle AI auto-play
                        self.auto = not self.auto

                    if event.key == K_e:
                        # Toggle extra-credit mode
                        self.ec = not self.ec

                    if event.key == pygame.K_r:
                        # Restart: fresh board
                        self.game.set_state()
                        self.auto = False

                    if 50 < event.key and 56 > event.key:
                        # Keys '3' through '7' (ASCII 51-55): change board size
                        self.game.board_size = event.key - 48
                        self.game.set_state()
                        self.auto = False

                    if event.key == pygame.K_s:
                        self.game.save_state()
                    elif event.key == pygame.K_l:
                        self.game.load_state()
                    elif event.key == pygame.K_u:
                        self.game.undo()
                    elif event.key == pygame.K_g:
                        self.grayscale = not self.grayscale

            # --- AI auto-play: ask the AI for a move ---
            if self.auto and not game_over:
                ai = AI(self.game.current_state())
                if not self.ec:
                    direction = ai.compute_decision()       # basic AI
                else:
                    direction = ai.compute_decision_ec()    # extra-credit AI

            # --- Apply the move (if any) ---
            if direction != None:
                self.game.move_and_place(direction)

            # --- Redraw ---
            self.print_matrix()
            if game_over:
                self.print_game_over()
            pygame.display.update()

    def print_matrix(self):
        """
        Draw the entire board: background, tiles, numbers, and score.

        For each cell:
            1. Calculate pixel position from (row, col) and tile_size.
            2. Pick a color (from COLORS dict or grayscale gradient).
            3. Draw a filled rectangle for the tile.
            4. Draw a black border around it.
            5. Render the tile number as text.
        """
        tile_size = BOARD_SIZE_PX / self.game.board_size
        self.surface.fill(WHITE)

        for row in range(0, self.game.board_size):
            for col in range(0, self.game.board_size):
                tile_value = self.game.tile_matrix[row][col]

                # Pixel coordinates for the upper-left corner of this tile.
                # NOTE: rows map to X and cols map to Y here (transposed rendering).
                upper_left_x = row * tile_size
                upper_left_y = col * tile_size + BOARD_Y_OFFSET_PX

                # Choose tile color
                color = None
                if self.grayscale:
                    # Map tile value to grayscale: higher tiles are darker.
                    # log2(value) gives the "order" (2→1, 4→2, 8→3, ...),
                    # capped at MAX_CORD. Then invert so 0 = white, max = black.
                    color_order = min(math.log(tile_value, 2), MAX_CORD) if tile_value > 0 else 0
                    shade = MAXC - ((color_order / float(MAX_CORD)) * MAXC)
                    color = [shade] * 3  # same value for R, G, B = gray
                else:
                    color = COLORS[tile_value]

                # Draw the filled tile rectangle
                pygame.draw.rect(self.surface, color,
                    (upper_left_x, upper_left_y, tile_size, tile_size))

                # Draw black border around the tile
                pygame.draw.rect(self.surface, BLACK,
                    (upper_left_x, upper_left_y, tile_size, tile_size), 2)

                # Render the tile's number
                tile_label = self.myfont.render(str(tile_value), 1, BLACK)
                score_label = self.getScoreLabel()

                tile_label_x = upper_left_x + TEXT_X_OFFSET_PX
                tile_label_y = upper_left_y + TEXT_Y_OFFSET_PX
                tile_label_pos = (tile_label_x, tile_label_y)

                # Draw a small highlight box behind the number for readability
                self.draw_label_hl(tile_label_pos, tile_label, 2, [230] * 3, 1, False)
                self.surface.blit(tile_label, tile_label_pos)

                # Draw the score label (top-left corner of the window)
                self.surface.blit(score_label, SCORE_LABEL_POS)

                # If extra-credit mode is active, show "[EC]" indicator
                if self.ec:
                    ec_label = self.scorefont.render("[EC]", 1, BLACK, WHITE)
                    self.surface.blit(ec_label, EC_LABEL_POS)

    def getScoreLabel(self):
        """Render the "Score: X" text surface."""
        return self.scorefont.render("Score: {}".format(self.game.score), 1, BLACK, WHITE)

    def draw_label_hl(self, pos, label, padding=PADDING, bg=WHITE, wd=2, border=True):
        """
        Draw a highlight rectangle behind a text label.

        Args:
            pos     -- (x, y) position of the label
            label   -- the rendered text surface (used for width/height)
            padding -- extra space around the text
            bg      -- background color for the highlight
            wd      -- border line width
            border  -- if True, draw a black border; if False, just the fill
        """
        draw_specs = [(bg, 0)]  # filled background rectangle
        if border:
            draw_specs += [(BLACK, wd)]  # add a border on top

        for color, width in draw_specs:
            pygame.draw.rect(self.surface, color,
                (pos[0] - padding, pos[1] - padding,
                 label.get_width() + padding * 2,
                 label.get_height() + padding * 2), width)

    def print_game_over(self):
        """Draw the game-over overlay: "Game Over!", score, and restart hint."""
        game_over_label = self.scorefont.render("Game Over!", 1, BLACK, WHITE)
        score_label = self.getScoreLabel()
        restart_label = self.myfont.render("Press r to restart!", 1, BLACK, WHITE)

        for label, position in [
            (game_over_label, (50, 100)),
            (score_label, (50, 200)),
            (restart_label, (50, 300))
        ]:
            self.draw_label_hl(position, label)
            self.surface.blit(label, position)

    def is_arrow(self, key):
        """Check if a key code is one of the four arrow keys."""
        return (key == pygame.K_UP or key == pygame.K_DOWN or
                key == pygame.K_LEFT or key == pygame.K_RIGHT)


# ============================================================================
# COMMAND-LINE ARGUMENT PARSING
# ============================================================================
# --test 0 (default): launch the GUI game
# --test 1:           run basic expectimax tests (test.py → test())
# --test 2:           run extra-credit tests (test.py → test_ec())

parser = argparse.ArgumentParser(description='2048.')
parser.add_argument('--test', '-t', dest="test", type=int, default=0,
                    help='0: initializes game, 1: autograde, 2: extra credit test')
args = parser.parse_args()

if __name__ == '__main__':
    if args.test == 1:
        test()
    elif args.test == 2:
        test_ec()
    else:
        # Only import pygame when we actually need the GUI.
        # This allows tests to run on machines without pygame installed.
        import pygame
        from pygame.locals import *

        # Map pygame arrow key codes to direction integers (matching game.py)
        ROTATIONS = {
            pygame.K_UP: 0,
            pygame.K_DOWN: 2,
            pygame.K_LEFT: 1,
            pygame.K_RIGHT: 3
        }

        game = GameRunner()
        game.loop()
