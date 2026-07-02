from datetime import datetime
import pygame
from config import *
from game import Game
import ui
import menu
import scoreboard



def main():
    renderer = ui.Renderer() # the renderer class handels all the visual output
    quit_app = False

    while True:
        choice = menu.show_main_menu(renderer)
        if choice is None:
            break

        game = Game(
            difficulty=choice["difficulty"],
            players=choice["players"],
            renderer=renderer,
            ai_enabled=choice["ai"],
            ai_type=choice["ai_type"])
        last_move_time = pygame.time.get_ticks()
        game.last_mystery_box_time = last_move_time

        running = True
        while running:
            current_time = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: # if window close button is clicked.
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_p:
                        game.pause_toggle()
                    elif not game.paused and not game.game_over:
                        if game.players >= 1:
                            if event.key == pygame.K_w:
                                game.set_direction(0, "UP")
                            elif event.key == pygame.K_s:
                                game.set_direction(0, "DOWN")
                            elif event.key == pygame.K_a:
                                game.set_direction(0, "LEFT")
                            elif event.key == pygame.K_d:
                                game.set_direction(0, "RIGHT")
                        if game.players == 2 and not game.ai_enabled:
                            if event.key == pygame.K_UP:
                                game.set_direction(1, "UP")
                            elif event.key == pygame.K_DOWN:
                                game.set_direction(1, "DOWN")
                            elif event.key == pygame.K_LEFT:
                                game.set_direction(1, "LEFT")
                            elif event.key == pygame.K_RIGHT:
                                game.set_direction(1, "RIGHT")

                    if game.game_over and event.key == pygame.K_RETURN: # Enter key
                        score_snakes = game.snakes[:1] if game.ai_enabled else game.snakes
                        timestamp = datetime.utcnow().isoformat()
                        for snake_index, snake in enumerate(score_snakes):
                            if snake.score > 0:
                                name = renderer.get_name_input()
                                if name:
                                    scoreboard.add_score(
                                        name,
                                        snake.score,
                                        game.players,
                                        game.get_result_for_snake(snake_index),
                                        game.difficulty,
                                        timestamp,
                                    )
                        running = False

            if not game.paused and not game.game_over:
                move_delay = BASE_MOVE_DELAY
                if game.snakes[0].is_fast(current_time):
                    move_delay = FAST_MOVE_DELAY
                if current_time - last_move_time >= move_delay:
                    if game.ai_enabled:
                        game.set_direction(1, game.get_ai_direction(1, current_time))
                    game.update(current_time)
                    last_move_time = current_time

            renderer.clear()
            renderer.draw_grid()
            if game.obstacles:
                renderer.draw_obstacles(game.obstacles)
            if game.fruit:
                renderer.draw_fruit(game.fruit)
            if game.mystery_box_active and game.mystery_box:
                renderer.draw_mystery_box(game.mystery_box)
            for snake in game.snakes:
                if snake.alive:
                    renderer.draw_snake(snake, current_time)
            renderer.draw_info_bar(game, current_time)
            if game.game_over:
                renderer.draw_game_over(game)
            renderer.update_display()

        if quit_app:
            break

    pygame.quit()

if __name__ == "__main__":
    main()
