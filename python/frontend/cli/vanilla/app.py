"""Vanilla terminal frontend — no third-party dependencies.

Uses only stdlib (print, ANSI codes, tty/termios) for rendering and input.
Includes a built-in menu for size selection, play, study, and high scores.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

from backend.engine.gamegenerator import GameGenerator
from backend.engine.gameplay import GamePlay
from backend.engine.gamesolver import Solver
from backend.models.board import Board, Direction
from backend.models.highscore import HighScoreEntry, HighScoreManager
from frontend.cli.input_handler import get_key, get_key_timeout


# -- ANSI helpers -------------------------------------------------------------

_G = "\033[32;1m"    # bold green
_Y = "\033[33;1m"    # bold yellow
_C = "\033[36;1m"    # bold cyan
_DIM = "\033[2m"     # dim
_BOLD = "\033[1m"    # bold
_R = "\033[0m"       # reset
_BG_SEL = "\033[42;30m"  # green bg, black fg (selected size)


def _clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}" if m else f"{s}s"


def _stats_line(game: GamePlay) -> str:
    """Return the formatted Moves + Time string (no newline)."""
    return (
        f"  Moves: {_Y}{game.state.moves}{_R}  |  "
        f"Time: {_Y}{_format_time(game.state.elapsed_time)}{_R}"
    )


# -- board rendering ----------------------------------------------------------


def _render_board(board: Board) -> str:
    """Return an ANSI-coloured text representation of the board."""
    width = len(str(board.size * board.size - 1))  # widest number
    cell_w = width + 2  # padding
    sep = "+" + (("-" * cell_w + "+") * board.size)

    lines: list[str] = [sep]
    for r, row in enumerate(board.tiles):
        cells: list[str] = []
        for c, val in enumerate(row):
            if val == 0:
                cells.append(f"{_DIM} {'·':>{width}} {_R}")
            elif board.is_tile_correct(r, c):
                cells.append(f"{_G} {val:>{width}} {_R}")
            else:
                cells.append(f" {val:>{width}} ")
        lines.append("|" + "|".join(cells) + "|")
        lines.append(sep)
    return "\n".join(lines)


# -- solver helpers -----------------------------------------------------------


def _apply_hint(game: GamePlay) -> str:
    """Apply a single solver hint.  Returns a status message."""
    board = game.state.board
    hint = Solver.hint(board)
    if hint is None:
        if board.is_solved():
            return f"{_G}Already solved!{_R}"
        return f"{_Y}No hint available (unsolvable or solver not implemented).{_R}"
    game.move(hint)
    return f"{_C}Hint:{_R} moved {_BOLD}{hint.value}{_R}"


def _auto_solve(game: GamePlay) -> str:
    """Run the solver and animate moves.  Returns a status message."""
    board = game.state.board
    try:
        moves = Solver.solve(board)
    except NotImplementedError:
        return f"{_Y}Solver not yet implemented.{_R}"

    if not moves:
        if board.is_solved():
            return f"{_G}Already solved!{_R}"
        return "Board is unsolvable."

    for i, direction in enumerate(moves):
        game.move(direction)
        _clear()
        size = game.size
        print(f"  {_C}=== Solving\u2026 ({size}\u00d7{size}) ==={_R}")
        print()
        print(_render_board(game.state.board))
        print()
        print(f"  Move {i + 1}/{len(moves)}  ({direction.value})")
        sys.stdout.flush()
        time.sleep(0.05)

    return f"{_G}Solved in {len(moves)} moves!{_R}"


# -- menu screen --------------------------------------------------------------


def _show_menu(sel_size: int) -> None:
    _clear()
    print()
    print(f"  {_BOLD}======================================{_R}")
    print(f"  {_BOLD}     S L I D I N G   P U Z Z L E     {_R}")
    print(f"  {_BOLD}======================================{_R}")
    print()

    # Size selector
    sizes_str = ""
    for s in range(3, 9):
        if s == sel_size:
            sizes_str += f"  {_BG_SEL} {s}\u00d7{s} {_R}"
        else:
            sizes_str += f"  {_DIM}{s}\u00d7{s}{_R}"
    print(f"    Size:{sizes_str}")
    print(f"    {_DIM}\u2190 \u2192 to change{_R}")
    print()

    # Options
    print(f"    {_C}1{_R}  Play")
    print(f"    {_Y}2{_R}  Study")
    print(f"    {_DIM}3{_R}  High Scores")
    print(f"    {_DIM}Q{_R}  Quit")
    print()


# -- game screens -------------------------------------------------------------


def _show_game(game: GamePlay, status: str = "") -> None:
    """Draw the full game screen.

    The stats line (Moves + Time) is printed last, with no trailing
    newline, so ``_update_time`` can cheaply overwrite it in-place
    using ``\\r\\033[K``.
    """
    _clear()
    size = game.size
    print(f"  {_C}=== Sliding Puzzle ({size}\u00d7{size}) ==={_R}")
    print()
    print(_render_board(game.state.board))
    print()
    print(
        f"  {_C}WASD{_R}/{_C}Arrows{_R}: move  |  "
        f"{_C}N{_R}: hint  |  "
        f"{_C}R{_R}: restart  |  "
        f"{_C}Q{_R}: back"
    )
    if status:
        print(f"  {status}")
    # Stats at the very bottom — no trailing newline.
    sys.stdout.write(f"\n{_stats_line(game)}")
    sys.stdout.flush()


def _update_time(game: GamePlay) -> None:
    """Overwrite just the stats (last) line in-place."""
    sys.stdout.write(f"\r\033[K{_stats_line(game)}")
    sys.stdout.flush()


def _show_study(game: GamePlay, status: str = "") -> None:
    _clear()
    size = game.size
    print(f"  {_Y}=== Study ({size}\u00d7{size}) ==={_R}")
    print()
    print(_render_board(game.state.board))
    if status:
        print(f"\n  {status}")
    print()
    print(
        f"  {_C}WASD{_R}/{_C}Arrows{_R}: move  |  "
        f"{_Y}R{_R}: scramble  |  "
        f"{_C}N{_R}: hint  |  "
        f"{_C}V{_R}: solve  |  "
        f"{_C}Q{_R}: back"
    )


def _show_win(game: GamePlay) -> None:
    _clear()
    size = game.size
    print(f"  {_G}=== Sliding Puzzle ({size}\u00d7{size}) ==={_R}")
    print()
    print(_render_board(game.state.board))
    print()
    print(f"  {_G}\u2605 CONGRATULATIONS! You solved it! \u2605{_R}")
    print()
    print(
        f"  Moves: {_Y}{game.state.moves}{_R}  |  "
        f"Time: {_Y}{_format_time(game.state.elapsed_time)}{_R}"
    )


def _show_highscores(manager: HighScoreManager) -> None:
    _clear()
    print()
    print(f"  {_BOLD}=== HIGH SCORES ==={_R}")
    sizes = manager.get_all_sizes()
    if not sizes:
        print(f"\n  {_DIM}No high scores yet.{_R}")
    else:
        for size in sizes:
            print(f"\n  {_C}--- {size}\u00d7{size} ---{_R}")
            scores = manager.get_scores(size)
            for i, e in enumerate(scores[:10], 1):
                print(
                    f"  {i:>2}. {_Y}{e.moves:>4}{_R} moves  "
                    f"{_Y}{e.time:>7.1f}s{_R}  "
                    f"{_DIM}({e.date}){_R}"
                )
    print(f"\n  {_DIM}Press any key to go back.{_R}")
    get_key()


# -- game loops ---------------------------------------------------------------


def _play_game(size: int, manager: HighScoreManager) -> None:
    """Play mode — hint only, scored."""
    while True:
        game = GamePlay(size)
        status = ""

        while not game.is_won:
            _show_game(game, status)
            status = ""

            # Wait for input; update the time display every 0.5 s.
            while True:
                key = get_key_timeout(0.5)
                if key is not None:
                    break
                _update_time(game)

            direction_map = {
                "up": Direction.UP,
                "down": Direction.DOWN,
                "left": Direction.LEFT,
                "right": Direction.RIGHT,
            }

            if key in direction_map:
                game.move(direction_map[key])
            elif key == "hint":
                status = _apply_hint(game)
            elif key == "restart":
                game = GamePlay(size)
            elif key == "quit":
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
        print(f"\n  {_DIM}Score saved!{_R}")
        print(f"\n  Press {_C}R{_R} to play again, {_C}Q{_R} to go back.")

        while True:
            key = get_key()
            if key == "restart":
                break
            if key == "quit":
                return


def _study_game(size: int) -> None:
    """Study mode — starts solved, scramble/hint/solve available."""
    board = GameGenerator.solved(size)
    game = GamePlay.from_board(board)
    status = ""

    while True:
        _show_study(game, status)
        status = ""
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
            board = GameGenerator.generate(size)
            game = GamePlay.from_board(board)
            status = f"{_Y}Scrambled!{_R}"
        elif key == "hint":
            status = _apply_hint(game)
        elif key == "solve":
            status = _auto_solve(game)
        elif key == "quit":
            return


# -- menu loop ----------------------------------------------------------------


def _menu_loop(data_dir: Path) -> None:
    hs_path = data_dir / "highscores.json"
    manager = HighScoreManager(hs_path)
    sel_size = 4

    while True:
        _show_menu(sel_size)
        key = get_key()

        if key == "quit":
            _clear()
            print("  Goodbye!\n")
            return
        elif key == "left":
            sel_size = max(3, sel_size - 1)
        elif key == "right":
            sel_size = min(8, sel_size + 1)
        elif key in ("1", "enter"):
            _play_game(sel_size, manager)
        elif key == "2":
            _study_game(sel_size)
        elif key in ("3", "help"):
            # 'h' maps to "help", '3' is raw char
            _show_highscores(manager)


# -- public entry point -------------------------------------------------------


def run(data_dir: Path) -> None:
    """Launch the vanilla CLI with interactive menu."""
    _menu_loop(data_dir)
