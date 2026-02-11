"""Rich terminal frontend — beautiful tables, colours, and panels.

Uses the ``rich`` library for styled output while sharing the same
input handler and backend as the vanilla CLI.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import rich.box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from backend.engine.gameplay import GamePlay
from backend.models.board import Board, Direction
from backend.models.highscore import HighScoreEntry, HighScoreManager
from frontend.cli.input_handler import get_key

console = Console()


# -- helpers ------------------------------------------------------------------


def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


# -- board rendering ----------------------------------------------------------


def _render_board(board: Board) -> Table:
    """Return a Rich Table representing the puzzle grid."""
    width = len(str(board.size * board.size - 1))
    table = Table(
        show_header=False,
        show_edge=True,
        pad_edge=True,
        box=rich.box.HEAVY,
        border_style="bright_blue",
        padding=(0, 1),
    )
    for _ in range(board.size):
        table.add_column(width=width + 1, justify="center")

    for r, row in enumerate(board.tiles):
        cells: list[str] = []
        for c, val in enumerate(row):
            if val == 0:
                cells.append("[dim]·[/dim]")
            elif board.is_tile_correct(r, c):
                cells.append(f"[bold green]{val:>{width}}[/bold green]")
            else:
                cells.append(f"[bold white]{val:>{width}}[/bold white]")
        table.add_row(*cells)

    return table


# -- screen composition ------------------------------------------------------


def _draw_game(game: GamePlay) -> None:
    """Clear the terminal and draw the full game screen."""
    console.clear()

    size = game.size
    board_table = _render_board(game.state.board)

    # Stats line
    stats = Text()
    stats.append("  Moves: ", style="dim")
    stats.append(str(game.state.moves), style="bold yellow")
    stats.append("    Time: ", style="dim")
    stats.append(_format_time(game.state.elapsed_time), style="bold yellow")

    # Controls line
    controls = Text()
    controls.append("  ↑↓←→", style="bold cyan")
    controls.append(" / ", style="dim")
    controls.append("WASD", style="bold cyan")
    controls.append("  move tile   ", style="dim")
    controls.append("R", style="bold cyan")
    controls.append("  restart   ", style="dim")
    controls.append("Q", style="bold cyan")
    controls.append("  quit", style="dim")

    # Assemble panel
    inner = Text("\n")
    inner_group = Align.center(board_table)

    panel = Panel(
        inner_group,
        title=f"[bold cyan]Sliding Puzzle  {size}×{size}[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2),
    )

    console.print()
    console.print(Align.center(panel))
    console.print(Align.center(stats))
    console.print(Align.center(controls))


def _draw_win(game: GamePlay) -> None:
    """Draw the winning screen."""
    console.clear()

    size = game.size
    board_table = _render_board(game.state.board)

    congrats = Text()
    congrats.append("\n  ★ ", style="bold yellow")
    congrats.append("CONGRATULATIONS!", style="bold green")
    congrats.append("  You solved it!  ", style="green")
    congrats.append("★\n", style="bold yellow")

    stats = Text()
    stats.append("  Moves: ", style="dim")
    stats.append(str(game.state.moves), style="bold yellow")
    stats.append("    Time: ", style="dim")
    stats.append(_format_time(game.state.elapsed_time), style="bold yellow")

    from rich.console import Group

    group = Group(
        Align.center(board_table),
        Align.center(congrats),
        Align.center(stats),
    )

    panel = Panel(
        group,
        title=f"[bold green]Sliding Puzzle  {size}×{size}[/bold green]",
        border_style="bold green",
        padding=(1, 2),
    )

    console.print()
    console.print(Align.center(panel))


def _draw_highscores(manager: HighScoreManager) -> None:
    """Draw a high-scores table below the current output."""
    sizes = manager.get_all_sizes()
    if not sizes:
        console.print(
            Align.center(Text("  No high scores yet.", style="dim"))
        )
        return

    for size in sizes:
        hs_table = Table(
            title=f"{size}×{size}",
            title_style="bold cyan",
            box=rich.box.ROUNDED,
            border_style="dim",
            show_lines=False,
        )
        hs_table.add_column("#", justify="right", style="dim", width=3)
        hs_table.add_column("Moves", justify="right", style="yellow")
        hs_table.add_column("Time", justify="right", style="yellow")
        hs_table.add_column("Date", style="dim")

        scores = manager.get_scores(size)
        for i, e in enumerate(scores[:10], 1):
            hs_table.add_row(
                str(i),
                str(e.moves),
                f"{e.time:.1f}s",
                e.date,
            )

        console.print()
        console.print(Align.center(hs_table))


# -- public entry point -------------------------------------------------------


def run(size: int, data_dir: Path) -> None:
    """Launch the Rich CLI game."""
    hs_path = data_dir / "highscores.json"
    manager = HighScoreManager(hs_path)

    while True:
        game = GamePlay(size)

        while not game.is_won:
            _draw_game(game)
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
                console.clear()
                console.print(
                    Align.center(
                        Text("\nThanks for playing!\n", style="bold cyan")
                    )
                )
                return

        # -- win ---------------------------------------------------------------
        game.state.pause()
        _draw_win(game)

        entry = HighScoreEntry(
            moves=game.state.moves,
            time=round(game.state.elapsed_time, 2),
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        manager.add_score(size, entry)

        _draw_highscores(manager)
        console.print(
            Align.center(
                Text(
                    "\n  Press R to play again, Q to quit.\n",
                    style="dim",
                )
            )
        )

        while True:
            key = get_key()
            if key == "restart":
                break
            if key == "quit":
                console.clear()
                console.print(
                    Align.center(
                        Text("\nThanks for playing!\n", style="bold cyan")
                    )
                )
                return
