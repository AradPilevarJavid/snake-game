import pygame
import math
import array
from config import *


def generate_tone(freq, duration, volume=0.5):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    period = sample_rate / freq
    buf = array.array(
        "h",
        [
            int(volume * 32767 * math.sin(2 * math.pi * freq * t / sample_rate))
            for t in range(n_samples)
        ],
    )
    sound = pygame.mixer.Sound(buffer=buf)
    return sound


class Renderer:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake Game")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 60)
        self.sound_eat = generate_tone(800, 0.1)
        self.sound_hit = generate_tone(200, 0.3)
        self.sound_mystery = generate_tone(500, 0.2)
        self.sound_button = generate_tone(1000, 0.05)

    def draw_grid(self):
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(
                self.screen, COLORS["grid_line"], (x, 60), (x, WINDOW_HEIGHT)
            )
        for y in range(60, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(
                self.screen, COLORS["grid_line"], (0, y), (WINDOW_WIDTH, y)
            )

    def draw_snake(self, snake, current_time):
        head_color = snake.current_color_head(current_time)
        body_color = snake.current_color_body(current_time)
        segments = list(snake.segments)
        for i, (x, y) in enumerate(segments):
            wx = x % GRID_WIDTH
            wy = y % GRID_HEIGHT
            cx = wx * CELL_SIZE + CELL_SIZE // 2
            cy = wy * CELL_SIZE + CELL_SIZE // 2 + 60
            radius = CELL_SIZE // 2
            if i == 0:
                color = head_color
            else:
                color = body_color
            pygame.draw.circle(self.screen, color, (cx, cy), radius)

        if len(segments) > 1:
            for i in range(len(segments) - 1):
                x1, y1 = segments[i]
                x2, y2 = segments[i + 1]

                wx1, wy1 = x1 % GRID_WIDTH, y1 % GRID_HEIGHT
                wx2, wy2 = x2 % GRID_WIDTH, y2 % GRID_HEIGHT

                if abs(wx1 - wx2) <= 1 and abs(wy1 - wy2) <= 1:
                    cx1 = wx1 * CELL_SIZE + CELL_SIZE // 2
                    cy1 = wy1 * CELL_SIZE + CELL_SIZE // 2 + 60
                    cx2 = wx2 * CELL_SIZE + CELL_SIZE // 2
                    cy2 = wy2 * CELL_SIZE + CELL_SIZE // 2 + 60
                    pygame.draw.line(
                        self.screen, body_color, (cx1, cy1), (cx2, cy2), CELL_SIZE
                    )

    def draw_fruit(self, pos):
        if pos is None:
            return

        x, y = pos
        centerX = x * CELL_SIZE + CELL_SIZE // 2
        centerY = y * CELL_SIZE + CELL_SIZE // 2 + 60

        pygame.draw.circle(
            self.screen, COLORS["fruit"], (centerX, centerY), CELL_SIZE // 2 - 2
        )
        leaf_points = [
            (centerX, centerY - CELL_SIZE // 2 + 4),
            (centerX - 6, centerY - CELL_SIZE // 2 - 2),
            (centerX + 6, centerY - CELL_SIZE // 2 - 2),
        ]
        pygame.draw.polygon(self.screen, COLORS["fruit_leaf"], leaf_points)

    def draw_mystery_box(self, pos):
        if pos is None:
            return

        x, y = pos
        rect = pygame.Rect(
            x * CELL_SIZE + 2, y * CELL_SIZE + 2 + 60, CELL_SIZE - 4, CELL_SIZE - 4
        )
        pygame.draw.rect(self.screen, COLORS["mystery_box"], rect, border_radius=5)
        text = self.font_small.render("?", True, (0, 0, 0))
        self.screen.blit(
            text,
            (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2,
            ),
        )

    def draw_obstacles(self, obstacles):
        for x, y in obstacles:
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE + 60, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(self.screen, COLORS["obstacle"], rect)
            pygame.draw.rect(self.screen, (80, 80, 80), rect, 2)

    def draw_info_bar(self, game, current_time):
        bar_rect = pygame.Rect(0, 0, WINDOW_WIDTH, 60)
        pygame.draw.rect(self.screen, COLORS["info_bar_bg"], bar_rect)
        y_offset = 10
        for i, snake in enumerate(game.snakes):
            label = (
                f"{game.ai_name} AI"
                if getattr(game, "ai_enabled", False) and i == 1
                else f"P{i + 1}"
            )
            lives_text = (
                ""
                if snake.lives_remaining is None
                else f" Lives: {snake.lives_remaining}"
            )
            text = f"{label} Score: {snake.score}{lives_text}"
            color = (
                snake.current_color_head(current_time)
                if snake.alive
                else (150, 150, 150)
            )
            surf = self.font_medium.render(text, True, color)
            self.screen.blit(surf, (10, y_offset))
            y_offset += 25
        if (
            hasattr(game, "effect_countdown_end")
            and current_time < game.effect_countdown_end
        ):
            affected_snake = next(
                (
                    s
                    for s in game.snakes
                    if s.alive
                    and (
                        (
                            hasattr(s, "effect_color_end")
                            and current_time < s.effect_color_end
                        )
                        or (
                            hasattr(s, "effect_speed_end")
                            and current_time < s.effect_speed_end
                        )
                    )
                ),
                None,
            )

            if affected_snake:
                remaining_cs = (game.effect_countdown_end - current_time) // 10
                countdown_text = self.font_medium.render(
                    f"Effect: {remaining_cs}cs", True, (255, 200, 0)
                )
                self.screen.blit(
                    countdown_text, (WINDOW_WIDTH - countdown_text.get_width() - 10, 10)
                )

        if game.paused:
            pause_surf = self.font_large.render("PAUSED", True, (255, 255, 0))
            self.screen.blit(
                pause_surf, (WINDOW_WIDTH // 2 - pause_surf.get_width() // 2, 15)
            )

    def draw_game_over(self, game):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        if game.winner == "tie":
            msg = "TIE!"
            color = (255, 220, 80)
        elif game.winner == 0:
            msg = (
                "PLAYER WINS!"
                if getattr(game, "ai_enabled", False)
                else "PLAYER 1 WINS!"
            )
            color = COLORS["snake1_head"]
        elif game.winner == 1:
            msg = "AI WINS!" if getattr(game, "ai_enabled", False) else "PLAYER 2 WINS!"
            color = COLORS["snake2_head"]
        elif game.win:
            msg = "YOU WIN!"
            color = (50, 255, 50)
        else:
            msg = "GAME OVER"
            color = (255, 50, 50)
        text = self.font_large.render(msg, True, color)
        self.screen.blit(
            text, (WINDOW_WIDTH // 2 - text.get_width() // 2, WINDOW_HEIGHT // 2 - 80)
        )
        score_msg = []
        for i, s in enumerate(game.snakes):
            label = (
                f"{game.ai_name} AI"
                if getattr(game, "ai_enabled", False) and i == 1
                else f"Player {i + 1}"
            )
            score_msg.append(f"{label} Score: {s.score}")
        y = WINDOW_HEIGHT // 2
        for m in score_msg:
            surf = self.font_medium.render(m, True, (255, 255, 255))
            self.screen.blit(surf, (WINDOW_WIDTH // 2 - surf.get_width() // 2, y))
            y += 40
        prompt = self.font_small.render(
            "Press ENTER to continue", True, (200, 200, 200)
        )
        self.screen.blit(prompt, (WINDOW_WIDTH // 2 - prompt.get_width() // 2, y + 20))

    def draw_button(self, rect, text, hover):
        color = COLORS["button_hover"] if hover else COLORS["button"]
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        text_surf = self.font_medium.render(text, True, COLORS["button_text"])
        self.screen.blit(
            text_surf,
            (
                rect.centerx - text_surf.get_width() // 2,
                rect.centery - text_surf.get_height() // 2,
            ),
        )

    def clear(self):
        self.screen.fill(COLORS["bg"])

    def update_display(self):
        pygame.display.flip()
        self.clock.tick(FPS)

    def get_name_input(self):
        name = ""
        input_active = True
        while input_active:
            self.clear()
            prompt = self.font_large.render("Enter Name:", True, (255, 255, 255))
            self.screen.blit(
                prompt,
                (WINDOW_WIDTH // 2 - prompt.get_width() // 2, WINDOW_HEIGHT // 2 - 60),
            )
            name_surf = self.font_medium.render(name + "_", True, (255, 255, 0))
            self.screen.blit(
                name_surf,
                (WINDOW_WIDTH // 2 - name_surf.get_width() // 2, WINDOW_HEIGHT // 2),
            )
            self.update_display()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and name.strip():
                        return name.strip()
                    elif event.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    elif event.unicode.isprintable() and len(name) < 15:
                        name += event.unicode
        return None
