import pygame
from config import *
import scoreboard


def show_main_menu(renderer):
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

    selected_mode = "single"
    selected_difficulty = "normal"

    while True:
        renderer.clear()
        mx, my = pygame.mouse.get_pos()
        mouse_click = False

        for event in pygame.event.get(): # returns a list of event objects.each event object has a type atr
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True

        title = renderer.font_large.render("SNAKE GAME", True, (100, 255, 100))
        renderer.screen.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 30))

        sub_y = 100
        mode_text = f"Mode: {'Two Players' if selected_mode == 'Two players' else 'Single Player'}"
        mode_surf = renderer.font_medium.render(mode_text, True, (255, 255, 255))
        renderer.screen.blit(mode_surf, (WINDOW_WIDTH//2 - mode_surf.get_width()//2, sub_y))
        sub_y += 40
        diff_text = f"Difficulty: {selected_difficulty.capitalize()}"
        diff_surf = renderer.font_medium.render(diff_text, True, (255, 255, 255))
        renderer.screen.blit(diff_surf, (WINDOW_WIDTH//2 - diff_surf.get_width()//2, sub_y))

        for b in buttons:
            hover = b["rect"].collidepoint(mx, my)
            renderer.draw_button(b["rect"], b["text"], hover)
            if mouse_click and hover:
                renderer.sound_button.play()
                if b["action"] == "new_game":
                    return {"action": "new_game", "players": 2 if selected_mode == "Two players" else 1, "difficulty": selected_difficulty}
                elif b["action"] == "scoreboard":
                    result = scoreboard.show_scoreboard(renderer)
                    if result is False:
                        return None
                elif b["action"] == "quit":
                    return None

        choice = None
        keys = pygame.key.get_pressed()
        if keys[pygame.K_m]:
            selected_mode = "Two players" if selected_mode == "single" else "single"
            pygame.time.wait(200)
        if keys[pygame.K_d]:
            selected_difficulty = "hard" if selected_difficulty == "normal" else "normal"
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
                return {"action": "new_game", "players": 2 if selected_mode == "Two players" else 1, "difficulty": selected_difficulty}
            elif choice == "show scoreboard":
                result = scoreboard.show_scoreboard(renderer)
                if result is False:
                    return None
            elif choice == "quit":
                return None

        renderer.update_display()