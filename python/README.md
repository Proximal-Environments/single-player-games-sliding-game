# Sliding Puzzle Game — Python

A classic sliding tile puzzle with multiple frontend options.

## Project Layout

```
sliding-game/
├── assets/                  # shared across all language implementations
│   └── images/
├── data/
│   └── highscores.json      # shared high-score store
├── python/                  # ← Python root
│   ├── backend/
│   │   ├── engine/
│   │   │   ├── gamegenerator/   # solvable board generation
│   │   │   ├── gameplay/        # move processing & win detection
│   │   │   └── gamestate/       # state tracking (moves, time)
│   │   └── models/              # Board, Direction, HighScore
│   ├── frontend/
│   │   ├── cli/
│   │   │   ├── rich/            # Rich library terminal UI
│   │   │   └── vanilla/         # plain terminal UI (stdlib only)
│   │   └── gui/
│   │       ├── pygame/          # Pygame GUI
│   │       └── pyqt/            # PyQt6 GUI
│   ├── main.py              # entry point (typer CLI)
│   └── pyproject.toml
├── rust/                    # (future)
└── go/                      # (future)
```

## Quick Start

```bash
cd python

# set up virtual env (using uv)
uv venv && source .venv/bin/activate
uv sync

# interactive menu
python main.py

# or jump straight in
python main.py play -f vanilla -s 4   # vanilla terminal, 4×4
python main.py play -f rich -s 3      # rich terminal, 3×3
python main.py play -f pygame -s 4    # Pygame GUI
python main.py play -f pyqt -s 3      # PyQt6 GUI
python main.py scores                  # view high scores
python main.py scores -s 4            # high scores for 4×4 only
```

## Controls

| Key          | Action           |
|--------------|------------------|
| ↑ / W       | Move tile up     |
| ↓ / S       | Move tile down   |
| ← / A       | Move tile left   |
| → / D       | Move tile right  |
| R            | Restart          |
| Q / Esc      | Quit             |

GUI frontends (Pygame / PyQt) also support clicking tiles directly.

## Porting to Other Languages

The `backend/` and `frontend/` split is intentional — replicate the same
directory layout in other language roots (`rust/`, `go/`, `typescript/`, …)
to keep a consistent cross-language structure.  `assets/` and `data/` live
at the project root so every implementation shares them.
