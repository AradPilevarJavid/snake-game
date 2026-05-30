# Snake Game 🐍

A classic Snake game built with Python and Pygame. It includes single and two-player modes, selectable difficulty, mystery power-ups, procedurally generated sound, and a persistent scoreboard.

## Features

- Single and two-player modes on a shared 30x30 grid
- Two difficulties: Normal, and Hard, which scatters obstacles that reshuffle each time fruit is eaten
- Mystery boxes that appear periodically and grant one of three random effects:
  - Color change: temporary invincibility with wall wrap-around
  - Fruit pack: +5 length and +5 score
  - Speed boost: move twice as fast
- Hall of Fame: top 10 scores saved to disk, with medals for the top three and 1P/2P badges
- Procedural sound effects generated at runtime, so no audio files are required
- Win by filling the entire board

## Requirements

- Python 3.x
- Pygame

## Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

```bash
python src/main.py
```

- move with WASD for single player and WASD and arrows for two player
- P: pause / resume
- Esc: return to the menu
- Enter: continue and submit your score after game over

Menu:

- Click New Game, Scoreboard, or Quit, or use the keyboard:
- M: toggle single / two-player mode
- D: toggle Normal / Hard difficulty
- N: new game
- S: scoreboard
- Q: quit

## Project Structure

```
├── assets
│   └── scores.json
├── src
│   ├── config.py
│   ├── game.py
│   ├── main.py
│   ├── menu.py
│   ├── scoreboard.py
│   └── ui.py
├── README.md
└── requirements.txt
```
