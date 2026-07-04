import json
import os
from datetime import datetime
from config import *
import pygame


def load_scores():
    if not os.path.exists(SCORE_FILE):
        return []
    with open(SCORE_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    return data


def save_scores(scores):
    with open(SCORE_FILE, "w") as f:
        json.dump(scores, f, indent=4)


def add_score(name, score, players, result="n/a", difficulty="normal", timestamp=None):
    scores = load_scores()
    entry = {
        "name": name,
        "score": score,
        "players": players,
        "result": result,
        "difficulty": difficulty,
        "timestamp": timestamp or datetime.utcnow().isoformat(),
    }
    scores.append(entry)
    scores.sort(key=lambda x: x["score"], reverse=True)
    scores = scores[:10]
    save_scores(scores)


def format_timestamp(timestamp):
    if not timestamp:
        return "Unknown time"
    try:
        parsed = datetime.fromisoformat(timestamp)
        return parsed.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return timestamp[:16]


def get_result_badge(result):
    result = (result or "n/a").lower()
    if result == "win":
        return "WIN", (90, 230, 120)
    if result == "loss":
        return "LOSS", (240, 90, 90)
    if result == "tie":
        return "TIE", (245, 210, 80)
    return "N/A", (170, 170, 170)


def show_scoreboard(renderer):
    scores = load_scores()
    running = True

    # The colors are declared here for top 3
    GOLD = (255, 215, 0)
    SILVER = (192, 192, 192)
    BRONZE = (205, 127, 50)

    while running:
        renderer.clear()
        mx, my = pygame.mouse.get_pos()

        # the render function turns text into a image-like object.
        # blit = bit block transfer.
        title = renderer.font_large.render("Hall of Fame", True, (68, 214, 44))
        title_shadow = renderer.font_large.render("Hall of Fame", True, (0, 0, 0))
        renderer.screen.blit(
            title_shadow, (WINDOW_WIDTH // 2 - title.get_width() // 2 + 2, 32)
        )
        renderer.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 30))

        panel_rect = pygame.Rect(50, 100, WINDOW_WIDTH - 100, 500)
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((20, 20, 20, 200))
        renderer.screen.blit(panel_surf, panel_rect.topleft)
        pygame.draw.rect(renderer.screen, (80, 80, 80), panel_rect, 2, border_radius=15)

        if not scores:
            no_data = renderer.font_medium.render(
                "No scores yet", True, (200, 200, 200)
            )
            renderer.screen.blit(
                no_data, (WINDOW_WIDTH // 2 - no_data.get_width() // 2, 250)
            )
        else:
            row_height = 48
            start_y = panel_rect.y + 20
            for i, entry in enumerate(scores):
                y = start_y + i * row_height

                row_rect = pygame.Rect(
                    panel_rect.x + 10, y, panel_rect.width - 20, row_height - 4
                )
                if i % 2 == 0:
                    row_color = (60, 60, 60)
                else:
                    row_color = (40, 40, 40)
                pygame.draw.rect(renderer.screen, row_color, row_rect, border_radius=10)

                rank_color = (200, 200, 200)
                if i == 0:
                    rank_color = GOLD
                elif i == 1:
                    rank_color = SILVER
                elif i == 2:
                    rank_color = BRONZE
                rank_surf = renderer.font_medium.render(str(i + 1), True, rank_color)
                rank_x = row_rect.x + 15
                rank_y = row_rect.centery - rank_surf.get_height() // 2
                renderer.screen.blit(rank_surf, (rank_x, rank_y))

                result_text, result_color = get_result_badge(entry.get("result", "n/a"))
                result_surf = renderer.font_small.render(
                    result_text, True, result_color
                )
                result_pad_x = 10
                result_badge = pygame.Rect(
                    row_rect.right - result_surf.get_width() - result_pad_x * 2 - 12,
                    row_rect.centery - 13,
                    result_surf.get_width() + result_pad_x * 2,
                    26,
                )
                pygame.draw.rect(
                    renderer.screen, (25, 25, 25), result_badge, border_radius=13
                )
                pygame.draw.rect(
                    renderer.screen, result_color, result_badge, 1, border_radius=13
                )
                renderer.screen.blit(
                    result_surf,
                    (
                        result_badge.centerx - result_surf.get_width() // 2,
                        result_badge.centery - result_surf.get_height() // 2,
                    ),
                )

                players_count = entry.get("players", 1)
                badge_text = "1P" if players_count == 1 else "2P"
                badge_color = (150, 150, 255) if players_count == 1 else (255, 150, 150)
                badge_surf = renderer.font_small.render(badge_text, True, badge_color)
                badge_x = result_badge.x - badge_surf.get_width() - 18
                badge_y = row_rect.centery - badge_surf.get_height() // 2
                renderer.screen.blit(badge_surf, (badge_x, badge_y))

                name_surf = renderer.font_medium.render(
                    entry["name"], True, (255, 255, 255)
                )
                name_x = rank_x + 50
                name_y = row_rect.y + 5
                renderer.screen.blit(name_surf, (name_x, name_y))

                difficulty = entry.get("difficulty", "normal").capitalize()
                time_text = format_timestamp(entry.get("timestamp"))
                detail_text = f"{difficulty} • {time_text}"
                detail_surf = renderer.font_small.render(
                    detail_text, True, (165, 165, 165)
                )
                detail_y = row_rect.y + 27
                renderer.screen.blit(detail_surf, (name_x, detail_y))

                score_text = str(entry["score"])
                score_surf = renderer.font_medium.render(
                    score_text, True, (255, 255, 100)
                )
                score_x = badge_x - score_surf.get_width() - 30
                score_y = row_rect.centery - score_surf.get_height() // 2
                renderer.screen.blit(score_surf, (score_x, score_y))

        return_rect = pygame.Rect(0, 0, 200, 60)
        return_rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 55)
        return_hover = return_rect.collidepoint(mx, my)
        renderer.draw_button(return_rect, "Return", return_hover)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if return_rect.collidepoint(event.pos):
                        return True

        renderer.update_display()
    return True
