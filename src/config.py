CELL_SIZE = 31
GRID_WIDTH = 30
GRID_HEIGHT = 30
WINDOW_WIDTH = GRID_WIDTH * CELL_SIZE
WINDOW_HEIGHT = GRID_HEIGHT * CELL_SIZE + 60
FPS = 100
BASE_MOVE_DELAY = 120 # increase this number to slow the game down
FAST_MOVE_DELAY = BASE_MOVE_DELAY / 2
MYSTERY_BOX_INTERVAL = 10000
EFFECT_DURATION = 5000
SCORE_FILE = "scores.json"


COLORS = {
    "bg": (30, 30, 30),
    "grid_line": (50, 50, 50),
    "snake1_head": (0, 200, 100),
    "snake1_body": (0, 150, 80),
    "snake2_head": (200, 100, 0),
    "snake2_body": (150, 80, 0),
    "fruit": (220, 50, 50),
    "fruit_leaf": (50, 180, 50),
    "mystery_box": (220, 180, 30),
    "obstacle": (120, 120, 120),
    "text": (240, 240, 240),
    "button": (80, 80, 80),
    "button_hover": (120, 120, 120),
    "button_text": (255, 255, 255),
    "info_bar_bg": (45, 45, 45),
}
