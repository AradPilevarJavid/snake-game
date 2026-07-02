# 🐍 Snake Game

[![Pygame](https://img.shields.io/badge/library-pygame-brightgreen)](https://www.pygame.org/)
[![Made with Python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![GitHub last commit](https://img.shields.io/github/last-commit/yourusername/yourrepo)](https://github.com/yourusername/yourrepo)
[![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)

Have fun playing a classic Snake game built with Python and Pygame.  
It includes single‑player, two‑player, **Player vs AI** modes, selectable difficulty, smart AI options, mystery power‑ups, procedurally generated sound, and a persistent scoreboard.

## ✨ Features

- 👤👥🤖 **Game modes:** Single‑player, two‑player, and Player vs AI on a shared 30×30 grid
- 🧠 **AI difficulty:**
  - 🟢 **Easy** – greedy AI that sometimes moves randomly
  - 🔵 **Smart** – BFS‑based AI that actively avoids the invincible player
- ⚡ **Invincibility rule:** when you’re invincible, the AI snake **dies** if it hits you
- 🎮 **Game difficulty:**
  - 🟩 **Normal** – classic play
  - 🟥 **Hard** – reshuffling obstacles appear with each fruit eaten
- 🎁 **Mystery boxes** appear periodically and grant one of three random effects:
  - 🌈 **Colour change** – temporary invincibility + wall wrap
  - 🍎 **Fruit pack** – +5 length and +5 score
  - ⚡ **Speed boost** – move twice as fast
- 🏆 **Hall of Fame** – top 10 scores saved locally, with 🥇🥈🥉 medals and 1P/2P badges
- 🔊 **Procedural sound** – no external audio files needed
- 🏁 Win by filling the entire board

## 📋 Requirements

- 🐍 Python 3.x
- 🎮 Pygame

Install dependencies:

```bash
pip install -r requirements.txt
```

## 🚀 Running

```bash
python src/main.py
```

### 🕹️ In‑Game Controls

| Key(s)          | Action                                      |
|-----------------|---------------------------------------------|
| **W A S D**     | Move Player 1                               |
| **Arrow keys**  | Move Player 2 (two‑player, human vs human) |
| **P**           | Pause / Resume                              |
| **Esc**         | Return to main menu                         |
| **Enter**       | Submit score after game over                |

### 📋 Menu Controls

| Key / Mouse                 | Action                                                       |
|-----------------------------|--------------------------------------------------------------|
| **Click `Mode` text**       | Cycle Single Player → Two Players → Player vs AI             |
| **Click `Difficulty` text** | Toggle Normal / Hard                                         |
| **Click `AI` text**         | Cycle Easy / Smart AI (Player vs AI mode)                    |
| **M**                       | Same as clicking Mode                                        |
| **D**                       | Same as clicking Difficulty                                 |
| **A**                       | Same as clicking AI (if visible)                             |
| **N** / **Click New Game**  | Start a new game                                             |
| **S** / **Click Scoreboard**| Open Scoreboard                                              |
| **Q** / **Click Quit**      | Quit                                                         |

In the scoreboard, click **Return** or press **Esc** to go back.

## 📁 Project Structure

```
├── LICENSE
├── README.md
├── assets/
│   └── tone.wav
├── scores.json
├── requirements.txt
└── src/
    ├── ai.py
    ├── config.py
    ├── game.py
    ├── main.py
    ├── menu.py
    ├── scoreboard.py
    └── ui.py
```

## ⚙️ For Pro Users

You can easily tweak the game’s behaviour by editing src/config.py:

  Mystery box frequency – find the line and change the number (in milliseconds). Lower values = boxes spawn more often.

```
  MYSTERY_BOX_INTERVAL = 10000
```
  
Snake speed – find the line and decrease the value to make the snake move faster. You can also adjust FPS for smoother animation.
```
BASE_MOVE_DELAY = 120
```
Feel free to experiment! All changes are safe – just restart the game to see them in action.


## 📜 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
