import random
from collections import deque
from ai import DEFAULT_AI_TYPE, create_ai, get_ai_name
from config import *

DIR_VECTORS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}

OPPOSITE = {
    "UP": "DOWN",
    "DOWN": "UP",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT",
}


class Snake:
    def __init__(self, start_pos, direction, color_head, color_body):
        self.segments = deque([start_pos])
        self.direction = direction
        self.next_direction = direction
        self.color_head = color_head
        self.color_body = color_body
        self.alive = True
        self.grow_count = 0
        self.score = 0
        self.effect_color = None
        self.effect_color_end = 0
        self.effect_speed_end = 0

    def head(self):
        return self.segments[0]

    def move(self, grow=False):
        if not self.alive:
            return

        self.direction = self.next_direction
        dx, dy = DIR_VECTORS[self.direction]
        hx, hy = self.head()
        new_head = (hx + dx, hy + dy)
        self.segments.appendleft(new_head)
        if grow:
            self.grow_count += 1
        else:
            if self.grow_count > 0:
                self.grow_count -= 1
            else:
                self.segments.pop()

    def check_self_collision(self):
        return self.head() in list(self.segments)[1:]

    def check_wall_collision(self):
        x, y = self.head()
        return x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT

    def check_collision_with_obstacles(self, obstacles):
        return self.head() in obstacles

    def check_collision_with_other_snake(self, other):
        if not other.alive:
            return False
        return self.head() in other.segments

    def apply_color_effect(self, color, end_time):
        self.effect_color = color
        self.effect_color_end = end_time

    def apply_speed_effect(self, end_time):
        self.effect_speed_end = end_time

    def current_color_head(self, current_time):
        if self.effect_color and current_time < self.effect_color_end:
            return self.effect_color
        return self.color_head

    def current_color_body(self, current_time):
        if self.effect_color and current_time < self.effect_color_end:
            return self.effect_color
        return self.color_body

    def is_fast(self, current_time):
        return current_time < self.effect_speed_end


class Game:
    def __init__(self, difficulty, players, renderer, ai_enabled=False, ai_type=DEFAULT_AI_TYPE):
        self.difficulty = difficulty
        self.players = players
        self.ai_enabled = ai_enabled
        self.ai_type = ai_type
        self.ai_name = get_ai_name(ai_type)
        self.ai_controller = create_ai(ai_type) if ai_enabled else None
        self.renderer = renderer
        self.grid_width = GRID_WIDTH
        self.grid_height = GRID_HEIGHT
        self.paused = False
        self.game_over = False
        self.win = False
        self.winner = None
        self.snakes = []
        self.fruit = None
        self.mystery_box = None
        self.mystery_box_active = False
        self.last_mystery_box_time = 0
        self.obstacles = set()
        self.score_popup = None
        self.popup_timer = 0
        self.current_time = 0

        start1 = (GRID_WIDTH // 4, GRID_HEIGHT // 2)
        snake1 = Snake(start1, "UP", COLORS["snake1_head"], COLORS["snake1_body"])
        self.snakes.append(snake1)

        if players == 2:
            start2 = (3 * GRID_WIDTH // 4, GRID_HEIGHT // 2)
            snake2 = Snake(start2, "DOWN", COLORS["snake2_head"], COLORS["snake2_body"])
            self.snakes.append(snake2)

        if difficulty == "hard":
            self._place_obstacles()

        self._spawn_fruit()

    def _get_occupied_cells(self, include_fruit=True, include_mystery_box=True):
        occupied = set()
        for s in self.snakes:
            occupied.update(s.segments)
        occupied.update(self.obstacles)
        if include_fruit and self.fruit:
            occupied.add(self.fruit)
        if include_mystery_box and self.mystery_box_active and self.mystery_box:
            occupied.add(self.mystery_box)
        return occupied

    def _place_obstacles(self):
        self.obstacles.clear()
        occupied = self._get_occupied_cells()
        available = [
            (x, y) for x in range(self.grid_width)
            for y in range(self.grid_height)
            if (x, y) not in occupied
        ]
        chosen = random.sample(available, min(10, len(available)))
        self.obstacles = set(chosen)

    def _spawn_fruit(self):
        occupied = self._get_occupied_cells(include_mystery_box=True)
        available = [
            (x, y) for x in range(self.grid_width)
            for y in range(self.grid_height)
            if (x, y) not in occupied
        ]
        self.fruit = random.choice(available) if available else None

    def _spawn_mystery_box(self):
        occupied = self._get_occupied_cells(include_fruit=True)
        available = [
            (x, y) for x in range(self.grid_width)
            for y in range(self.grid_height)
            if (x, y) not in occupied
        ]
        if available:
            self.mystery_box = random.choice(available)
            self.mystery_box_active = True
        else:
            self.mystery_box_active = False

    def _activate_mystery_effect(self, snake, current_time):
        effect = random.choice(["color", "fruit_pack", "speed"])
        if effect == "color":
            end_time = current_time + EFFECT_DURATION
            snake.apply_color_effect((random.randint(50, 255), random.randint(50, 255), random.randint(50, 255)),
                                     end_time)
            self.effect_countdown_end = end_time
            self.score_popup = ("color change", current_time + 1000)
        elif effect == "fruit_pack":
            snake.grow_count += 5
            snake.score += 5
            self.score_popup = ("+5 fruits", current_time + 1000)
        elif effect == "speed":
            end_time = current_time + EFFECT_DURATION
            snake.apply_speed_effect(end_time)
            self.effect_countdown_end = end_time
            self.score_popup = ("speed boost", current_time + 1000)

    def get_ai_direction(self, snake_index, current_time=None):
        if current_time is not None:
            self.current_time = current_time
        if self.ai_controller:
            return self.ai_controller.get_direction(self, snake_index)
        return self.snakes[snake_index].direction

    def is_snake_invincible(self, snake, current_time):
        return snake.effect_color is not None and current_time < snake.effect_color_end

    def _set_winner_by_score(self):
        if self.players < 2:
            return

        score1 = self.snakes[0].score
        score2 = self.snakes[1].score
        if score1 > score2:
            self.winner = 0
        elif score2 > score1:
            self.winner = 1
        else:
            self.winner = "tie"

    def get_result_for_snake(self, snake_index):
        if self.players == 1:
            return "n/a"
        if self.winner is None:          # <-- FIX: undefined winner → "n/a"
            return "n/a"
        if self.winner == "tie":
            return "tie"
        if self.winner == snake_index:
            return "win"
        return "loss"

    def update(self, current_time):
        if self.game_over or self.paused:
            return

        self.current_time = current_time

        for s in self.snakes:
            if not s.alive:
                continue
            s.move(grow=False)

        for s in self.snakes:
            if not s.alive:
                continue
            if s.effect_color and current_time < s.effect_color_end:
                hx, hy = s.head()
                wrapped_x = hx % self.grid_width
                wrapped_y = hy % self.grid_height
                if (wrapped_x, wrapped_y) != (hx, hy):
                    s.segments[0] = (wrapped_x, wrapped_y)

        for s in self.snakes:
            if not s.alive:
                continue

            invincible = self.is_snake_invincible(s, current_time)

            if (
                self.ai_enabled
                and self.players == 2
                and s is self.snakes[1]
                and self.is_snake_invincible(self.snakes[0], current_time)
                and s.head() in self.snakes[0].segments
            ):
                s.alive = False
                self.renderer.sound_hit.play()
                continue

            if not invincible:
                if (s.check_wall_collision() or s.check_self_collision() or
                    s.check_collision_with_obstacles(self.obstacles)):
                    s.alive = False
                    self.renderer.sound_hit.play()
                    continue
                if self.players == 2:
                    other = self.snakes[1] if s is self.snakes[0] else self.snakes[0]
                    if s.check_collision_with_other_snake(other):
                        s.alive = False
                        self.renderer.sound_hit.play()
                        continue

        # --- Handle game‑over for AI mode (already correct) ---
        if self.ai_enabled and self.players == 2:
            player_alive = self.snakes[0].alive
            ai_alive = self.snakes[1].alive
            if not player_alive or not ai_alive:
                if not player_alive and not ai_alive:
                    self._set_winner_by_score()
                elif not player_alive:
                    self.winner = 1
                else:
                    self.winner = 0
                self.game_over = True
                return

        # --- FIX: handle death in two‑player human vs human ---
        elif self.players == 2:
            alive_snakes = [s for s in self.snakes if s.alive]
            if len(alive_snakes) == 1:
                self.winner = 0 if alive_snakes[0] is self.snakes[0] else 1
                self.game_over = True
                return
            elif not alive_snakes:
                self._set_winner_by_score()
                self.game_over = True
                return

        # --- end of death handling fix ---

        alive_snakes = [s for s in self.snakes if s.alive]
        if not alive_snakes:
            if self.players == 2:
                self._set_winner_by_score()
            self.game_over = True
            return

        for s in self.snakes:
            if s.alive and s.head() == self.fruit:
                s.grow_count += 1
                s.score += 1
                self.score_popup = ("+1", current_time + 800)
                self.renderer.sound_eat.play()
                self._spawn_fruit()
                if self.difficulty == "hard":
                    self._place_obstacles()

        if self.mystery_box_active:
            for s in self.snakes:
                if s.alive and s.head() == self.mystery_box:
                    self._activate_mystery_effect(s, current_time)
                    self.renderer.sound_mystery.play()
                    self.mystery_box_active = False
                    self.last_mystery_box_time = current_time
                    self.mystery_box = None

        if not self.mystery_box_active and current_time - self.last_mystery_box_time > MYSTERY_BOX_INTERVAL:
            self._spawn_mystery_box()
            self.last_mystery_box_time = current_time

        total_cells = self.grid_width * self.grid_height
        occupied = sum(len(s.segments) for s in self.snakes if s.alive) + len(self.obstacles)
        if self.fruit:
            occupied += 1
        if self.mystery_box_active:
            occupied += 1
        if occupied >= total_cells:
            self.win = True
            self._set_winner_by_score()
            self.game_over = True

    def pause_toggle(self):
        if not self.game_over:
            self.paused = not self.paused

    def set_direction(self, snake_idx, direction):
        snake = self.snakes[snake_idx]
        if direction == OPPOSITE[snake.direction]:
            return
        snake.next_direction = direction
