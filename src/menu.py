import pygame
from ai import AI_OPTIONS
from config import *
import scoreboard


def show_main_menu(renderer):
    modes = [
        {"name": "Single Player", "players": 1, "ai": False},
        {"name": "Two Players", "players": 2, "ai": False},
        {"name": "Player vs AI", "players": 2, "ai": True},
    ]
    buttons = [
        {"text": "New Game", "action": "new_game", "rect": pygame.Rect(0, 0, 200, 60)},
        {"text": "Scoreboard", "action": "scoreboard", "rect": pygame.Rect(0, 0, 200, 60)},
        {"text": "Quit", "action": "quit", "rect": pygame.Rect(0, 0, 200, 60)},
    ]

    spacing = 100
    start_y = (WINDOW_HEIGHT - len(buttons) * spacing) // 2

    for i, b in enumerate(buttons):
        b["rect"].centerx = WINDOW_WIDTH // 2
        b["rect"].centery = start_y + i * spacing

    selected_mode_idx = 0
    selected_difficulty = "normal"
    selected_ai_idx = 0

    def build_new_game_choice():
        selected_mode = modes[selected_mode_idx]
        selected_ai = AI_OPTIONS[selected_ai_idx]
        return {
            "action": "new_game",
            "players": selected_mode["players"],
            "ai": selected_mode["ai"],
            "ai_type": selected_ai["id"],
            "difficulty": selected_difficulty,
        }

    while True:
        renderer.clear()
        mx, my = pygame.mouse.get_pos()
        mouse_click = False
        clicked_pos = None

        for event in pygame.event.get(): # returns a list of event objects.each event object has a type atr
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True
                    clicked_pos = event.pos

        title = renderer.font_large.render("SNAKE GAME", True, (100, 255, 100))
        renderer.screen.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 30))

        sub_y = 100
        selected_mode = modes[selected_mode_idx]
        mode_text = f"Mode: {selected_mode['name']}"
        mode_surf = renderer.font_medium.render(mode_text, True, (255, 255, 255))
        mode_rect = mode_surf.get_rect(center=(WINDOW_WIDTH // 2, sub_y + mode_surf.get_height() // 2))
        renderer.screen.blit(mode_surf, mode_rect)
        sub_y += 40
        diff_text = f"Difficulty: {selected_difficulty.capitalize()}"
        diff_surf = renderer.font_medium.render(diff_text, True, (255, 255, 255))
        diff_rect = diff_surf.get_rect(center=(WINDOW_WIDTH // 2, sub_y + diff_surf.get_height() // 2))
        renderer.screen.blit(diff_surf, diff_rect)
        sub_y += 40
        ai_rect = None
        if selected_mode["ai"]:
            selected_ai = AI_OPTIONS[selected_ai_idx]
            ai_text = f"AI: {selected_ai['name']}"
            ai_surf = renderer.font_medium.render(ai_text, True, COLORS["snake2_head"])
            ai_rect = ai_surf.get_rect(center=(WINDOW_WIDTH // 2, sub_y + ai_surf.get_height() // 2))
            renderer.screen.blit(ai_surf, ai_rect)

        if mouse_click and clicked_pos:
            if mode_rect.collidepoint(clicked_pos):
                selected_mode_idx = (selected_mode_idx + 1) % len(modes)
                renderer.sound_button.play()
                mouse_click = False
            elif diff_rect.collidepoint(clicked_pos):
                selected_difficulty = "hard" if selected_difficulty == "normal" else "normal"
                renderer.sound_button.play()
                mouse_click = False
            elif ai_rect and ai_rect.collidepoint(clicked_pos):
                selected_ai_idx = (selected_ai_idx + 1) % len(AI_OPTIONS)
                renderer.sound_button.play()
                mouse_click = False

        for b in buttons:
            hover = b["rect"].collidepoint(mx, my)
            renderer.draw_button(b["rect"], b["text"], hover)
            if mouse_click and hover:
                renderer.sound_button.play()
                if b["action"] == "new_game":
                    return build_new_game_choice()
                elif b["action"] == "scoreboard":
                    result = scoreboard.show_scoreboard(renderer)
                    if result is False:
                        return None
                elif b["action"] == "quit":
                    return None

        choice = None
        keys = pygame.key.get_pressed()
        if keys[pygame.K_m]:
            selected_mode_idx = (selected_mode_idx + 1) % len(modes)
            pygame.time.wait(200)
        if keys[pygame.K_d]:
            selected_difficulty = "hard" if selected_difficulty == "normal" else "normal"
            pygame.time.wait(200)
        if selected_mode["ai"] and keys[pygame.K_a]:
            selected_ai_idx = (selected_ai_idx + 1) % len(AI_OPTIONS)
            pygame.time.wait(200)
        if keys[pygame.K_n]:
            choice = "New game"
            pygame.time.wait(200)
        if keys[pygame.K_s]:
            choice = "show scoreboard"
            pygame.time.wait(200)
        if keys[pygame.K_q]:
            choice = "quit"
            pygame.time.wait(200)

        if choice:
            if choice == "New game":
                return build_new_game_choice()
            elif choice == "show scoreboard":
                result = scoreboard.show_scoreboard(renderer)
                if result is False:
                    return None
            elif choice == "quit":
                return None

        renderer.update_display()
