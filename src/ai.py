import random
from collections import deque


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

AI_OPTIONS = [
    {"id": "easy", "name": "Easy"},
    {"id": "smart", "name": "Smart"},
]
DEFAULT_AI_TYPE = "easy"


def get_ai_name(ai_type):
    for option in AI_OPTIONS:
        if option["id"] == ai_type:
            return option["name"]
    return AI_OPTIONS[0]["name"]


def create_ai(ai_type):
    if ai_type == "smart":
        return SmartBfsAI()
    return EasyGreedyAI()


class BaseSnakeAI:
    def _is_in_bounds(self, game, pos):
        x, y = pos
        return 0 <= x < game.grid_width and 0 <= y < game.grid_height

    def _get_blocked_cells(self, game):
        blocked = set(game.obstacles)
        for snake in game.snakes:
            blocked.update(snake.segments)
        return blocked

    def _player_is_invincible(self, game):
        if not getattr(game, "ai_enabled", False) or len(game.snakes) < 2:
            return False
        player = game.snakes[0]
        current_time = getattr(game, "current_time", None)
        if current_time is None:
            return False
        return game.is_snake_invincible(player, current_time)

    def _distance_to_player(self, game, pos):
        player_segments = list(game.snakes[0].segments)
        if not player_segments:
            return 0
        return min(abs(pos[0] - x) + abs(pos[1] - y) for x, y in player_segments)

    def _open_neighbors_after_move(self, game, snake_index, pos):
        blocked = self._get_blocked_cells(game)
        blocked.discard(game.snakes[snake_index].head())
        open_neighbors = 0
        for dx, dy in DIR_VECTORS.values():
            next_pos = (pos[0] + dx, pos[1] + dy)
            if self._is_in_bounds(game, next_pos) and next_pos not in blocked:
                open_neighbors += 1
        return open_neighbors

    def _avoid_player_direction(self, game, snake_index):
        safe_directions = self._get_safe_directions(game, snake_index)
        if not safe_directions:
            return game.snakes[snake_index].direction

        hx, hy = game.snakes[snake_index].head()

        def safety_score(direction):
            dx, dy = DIR_VECTORS[direction]
            next_pos = (hx + dx, hy + dy)
            return (
                self._distance_to_player(game, next_pos),
                self._open_neighbors_after_move(game, snake_index, next_pos),
            )

        return max(safe_directions, key=safety_score)

    def _get_safe_directions(self, game, snake_index):
        snake = game.snakes[snake_index]
        blocked = self._get_blocked_cells(game)
        safe_directions = []

        for direction, (dx, dy) in DIR_VECTORS.items():
            if direction == OPPOSITE[snake.direction]:
                continue
            hx, hy = snake.head()
            next_pos = (hx + dx, hy + dy)
            if self._is_in_bounds(game, next_pos) and next_pos not in blocked:
                safe_directions.append(direction)

        random.shuffle(safe_directions)
        return safe_directions

    def _fallback_direction(self, game, snake_index):
        safe_directions = self._get_safe_directions(game, snake_index)
        if safe_directions:
            return safe_directions[0]
        return game.snakes[snake_index].direction


class EasyGreedyAI(BaseSnakeAI):
    def __init__(self, random_chance=0.2):
        self.random_chance = random_chance

    def get_direction(self, game, snake_index):
        if snake_index >= len(game.snakes):
            return "UP"

        snake = game.snakes[snake_index]
        if not snake.alive:
            return snake.direction

        if snake_index == 1 and self._player_is_invincible(game):
            return self._avoid_player_direction(game, snake_index)

        safe_directions = self._get_safe_directions(game, snake_index)
        if not safe_directions:
            return snake.direction
        if game.fruit is None or random.random() < self.random_chance:
            return safe_directions[0]

        hx, hy = snake.head()
        fruit_x, fruit_y = game.fruit

        def distance_after_move(direction):
            dx, dy = DIR_VECTORS[direction]
            next_x = hx + dx
            next_y = hy + dy
            return abs(next_x - fruit_x) + abs(next_y - fruit_y)

        return min(safe_directions, key=distance_after_move)


class SmartBfsAI(BaseSnakeAI):
    def get_direction(self, game, snake_index):
        if snake_index >= len(game.snakes):
            return "UP"

        snake = game.snakes[snake_index]
        if not snake.alive:
            return snake.direction

        if snake_index == 1 and self._player_is_invincible(game):
            return self._avoid_player_direction(game, snake_index)

        blocked = self._get_blocked_cells(game)
        start = snake.head()
        target = game.fruit

        if target is not None and target != start:
            queue = deque([start])
            visited = {start}
            first_direction = {start: None}

            while queue:
                current = queue.popleft()
                if current == target:
                    return first_direction[current]

                directions = list(DIR_VECTORS.items())
                random.shuffle(directions)
                for direction, (dx, dy) in directions:
                    if current == start and direction == OPPOSITE[snake.direction]:
                        continue

                    next_pos = (current[0] + dx, current[1] + dy)
                    if (
                        not self._is_in_bounds(game, next_pos)
                        or next_pos in blocked
                        or next_pos in visited
                    ):
                        continue

                    visited.add(next_pos)
                    first_direction[next_pos] = (
                        direction if current == start else first_direction[current]
                    )
                    queue.append(next_pos)

        return self._fallback_direction(game, snake_index)
