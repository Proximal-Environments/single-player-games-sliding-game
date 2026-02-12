# Sliding Puzzle Game — Python

A classic sliding tile puzzle with multiple frontend options.

## Quick Start

```bash
cd src

# set up virtual env (using uv)
uv sync
uv sync --extra dev  # dev setup

# Start game
uv run main.py cli
uv run main.py gui  # (default: pyqt)
uv run main.py gui:pygame
uv run main.py gui:pyqt
```

## Controls

| Key          | Action           |
|--------------|------------------|
| ↑ / W        | Move tile up     |
| ↓ / S        | Move tile down   |
| ← / A        | Move tile left   |
| → / D        | Move tile right  |
| R            | Restart          |
| Q / Esc      | Quit             |

GUI frontends (Pygame / PyQt) also support clicking tiles directly.
