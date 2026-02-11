"""Vanilla terminal frontend — no third-party dependencies.

Uses only stdlib (print, ANSI codes, tty/termios) for rendering and input.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from backend.engine.gameplay import GamePlay
from backend.models.board import Board, Direction
from backend.models.highscore import HighScoreEntry, HighScoreManager
from frontend.cli.input_handler import get_key


# -- screen helpers -----------------------------------------------------------


def _clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}" if m else f"{s}s"


# -- board rendering ----------------------------------------------------------


def _render_board(board: Board) -> str:
    """Return a plain-text representation of the board."""
    width = len(str(board.size * board.size - 1))  # widest number
    cell_w = width + 2  # padding
    sep = "+" + (("-" * cell_w + "+") * board.size)

    lines: list[str] = [sep]
    for row in board.tiles:
        cells: list[str] = []
        for val in row:
            if val == 0:
                cells.append(" " * cell_w)
            else:
                cells.append(f" {val:>{width}} ")
        lines.append("|" + "|".join(cells) + "|")
        lines.append(sep)
    return "\n".join(lines)


# -- main game loop -----------------------------------------------------------


def _show_game(game: GamePlay) -> None:
    _clear()
    size = game.size
    print(f"=== Sliding Puzzle ({size}x{size}) ===")
    print()
    print(_render_board(game.state.board))
    print()
    print(
        f"  Moves: {game.state.moves}  |  "
        f"Time: {_format_time(game.state.elapsed_time)}"
    )
    print()
    print("  WASD / Arrows: move tile  |  R: restart  |  Q: quit")


def _show_win(game: GamePlay) -> None:
    _clear()
    size = game.size
    print(f"=== Sliding Puzzle ({size}x{size}) ===")
    print()
    print(_render_board(game.state.board))
    print()
    print("  *** CONGRATULATIONS! You solved it! ***")
    print()
    print(
        f"  Moves: {game.state.moves}  |  "
        f"Time: {_format_time(game.state.elapsed_time)}"
    )


def _show_highscores(manager: HighScoreManager) -> None:
    print()
    print("=== HIGH SCORES ===")
    sizes = manager.get_all_sizes()
    if not sizes:
        print("  No high scores yet.")
        return
    for size in sizes:
        print(f"\n  --- {size}x{size} ---")
        scores = manager.get_scores(size)
        for i, e in enumerate(scores[:10], 1):
            print(f"  {i:>2}. {e.moves:>4} moves  {e.time:>7.1f}s  ({e.date})")


# -- public entry point -------------------------------------------------------


def run(size: int, data_dir: Path) -> None:
    """Launch the vanilla CLI game."""
    hs_path = data_dir / "highscores.json"
    manager = HighScoreManager(hs_path)

    while True:
        game = GamePlay(size)

        while not game.is_won:
            _show_game(game)
            key = get_key()

            direction_map = {
                "up": Direction.UP,
                "down": Direction.DOWN,
                "left": Direction.LEFT,
                "right": Direction.RIGHT,
            }

            if key in direction_map:
                game.move(direction_map[key])
            elif key == "restart":
                game = GamePlay(size)
            elif key == "quit":
                _clear()
                print("Thanks for playing!")
                return

        # -- win ---------------------------------------------------------------
        game.state.pause()
        _show_win(game)

        entry = HighScoreEntry(
            moves=game.state.moves,
            time=round(game.state.elapsed_time, 2),
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        manager.add_score(size, entry)
        print()
        _show_highscores(manager)

        print("\n  Press R to play again, Q to quit.")
        while True:
            key = get_key()
            if key == "restart":
                break
            if key == "quit":
                _clear()
                print("Thanks for playing!")
                return
