#!/usr/bin/env python3
"""Sliding Puzzle Game.

Usage::

    python main.py                # interactive menu
    python main.py -f rich -s 3   # Rich terminal, 3×3
    python main.py -f pygame      # Pygame GUI (has its own menu)
    python main.py --scores       # view high scores
"""

import importlib
import sys
from enum import StrEnum
from pathlib import Path
from typing import Optional

import typer

ROOT = Path(__file__).resolve().parent  # python/
PROJECT_ROOT = ROOT.parent  # sliding-game/
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# -- frontend registry -------------------------------------------------------


class Frontend(StrEnum):
    vanilla = "vanilla"
    rich = "rich"
    pygame = "pygame"
    pyqt = "pyqt"


_RUNNERS = {
    Frontend.vanilla: "frontend.cli.vanilla.app",
    Frontend.rich: "frontend.cli.rich.app",
    Frontend.pygame: "frontend.gui.pygame.app",
    Frontend.pyqt: "frontend.gui.pyqt.app",
}

_GUI = {Frontend.pygame, Frontend.pyqt}


# -- helpers ------------------------------------------------------------------


def _print_highscores() -> None:
    from backend.models.highscore import HighScoreManager

    manager = HighScoreManager(DATA_DIR / "highscores.json")
    sizes = manager.get_all_sizes()

    print("\n  === HIGH SCORES ===")
    if not sizes:
        print("  No high scores yet.\n")
        return
    for size in sizes:
        entries = manager.get_scores(size)
        if not entries:
            continue
        print(f"\n  --- {size}x{size} ---")
        for i, e in enumerate(entries[:10], 1):
            print(f"  {i:>2}. {e.moves:>4} moves  {e.time:>7.1f}s  ({e.date})")
    print()


def _ask_size() -> int:
    raw = input("  Grid size (3-8, default 4): ").strip() or "4"
    try:
        size = int(raw)
        if not 3 <= size <= 8:
            raise ValueError
    except ValueError:
        print("  Invalid size — using 4.")
        size = 4
    return size


def _menu_loop() -> None:
    while True:
        print()
        print("  ====================================")
        print("       S L I D I N G   P U Z Z L E    ")
        print("  ====================================")
        print()
        print("  1.  Play  (Vanilla Terminal)")
        print("  2.  Play  (Rich Terminal)")
        print("  3.  Play  (Pygame GUI)")
        print("  4.  Play  (PyQt GUI)")
        print("  5.  View High Scores")
        print("  0.  Quit")
        print()

        choice = input("  Select: ").strip()

        if choice == "0":
            print("\n  Goodbye!\n")
            return

        if choice in ("1", "2"):
            size = _ask_size()
            mod = importlib.import_module(
                {"1": _RUNNERS[Frontend.vanilla], "2": _RUNNERS[Frontend.rich]}[choice]
            )
            mod.run(size=size, data_dir=DATA_DIR)

        elif choice in ("3", "4"):
            mod = importlib.import_module(
                {"3": _RUNNERS[Frontend.pygame], "4": _RUNNERS[Frontend.pyqt]}[choice]
            )
            mod.run(data_dir=DATA_DIR)

        elif choice == "5":
            _print_highscores()

        else:
            print("  Unknown option.")


# -- CLI entry point ----------------------------------------------------------

app = typer.Typer(add_completion=False)


@app.command()
def main(
    frontend: Optional[Frontend] = typer.Option(
        None, "-f", "--frontend",
        help="Frontend to launch. Omit for interactive menu.",
    ),
    size: int = typer.Option(
        4, "-s", "--size",
        min=3, max=8,
        help="Grid size (3-8).",
    ),
    scores: bool = typer.Option(
        False, "--scores",
        help="Show high scores and exit.",
    ),
) -> None:
    """Sliding Puzzle Game."""
    if scores:
        _print_highscores()
        return

    if frontend is None:
        _menu_loop()
        return

    mod = importlib.import_module(_RUNNERS[frontend])
    mod.run(size=size, data_dir=DATA_DIR)


if __name__ == "__main__":
    app()
