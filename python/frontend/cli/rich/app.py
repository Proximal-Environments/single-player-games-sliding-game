"""Rich terminal frontend — beautiful tables, colours, and panels.

Uses the ``rich`` library for styled output while sharing the same
input handler and backend as the vanilla CLI.  Includes a built-in
menu for size selection, play, study, and high scores.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import rich.box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from backend.engine.gamegenerator import GameGenerator
from backend.engine.gameplay import GamePlay
from backend.engine.gamesolver import Solver
from backend.models.board import Board, Direction
from backend.models.highscore import HighScoreEntry, HighScoreManager
from frontend.cli.input_handler import get_key, get_key_timeout

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
                cells.append("[dim]\u00b7[/dim]")
            elif board.is_tile_correct(r, c):
                cells.append(f"[bold green]{val:>{width}}[/bold green]")
            else:
                cells.append(f"[bold white]{val:>{width}}[/bold white]")
        table.add_row(*cells)

    return table


# -- solver helpers -----------------------------------------------------------


def _apply_hint(game: GamePlay) -> str:
    board = game.state.board
    hint = Solver.hint(board)
    if hint is None:
        if board.is_solved():
            return "[green]Already solved![/green]"
        return "[yellow]No hint available (unsolvable or solver not implemented).[/yellow]"
    game.move(hint)
    return f"[cyan]Hint:[/cyan] moved [bold]{hint.value}[/bold]"


def _auto_solve(game: GamePlay) -> str:
    board = game.state.board
    try:
        moves = Solver.solve(board)
    except NotImplementedError:
        return "[yellow]Solver not yet implemented.[/yellow]"

    if not moves:
        if board.is_solved():
            return "[green]Already solved![/green]"
        return "[red]Board is unsolvable.[/red]"

    for i, direction in enumerate(moves):
        game.move(direction)
        console.clear()
        size = game.size
        board_table = _render_board(game.state.board)

        progress = Text()
        progress.append(f"  Solving\u2026 move {i + 1}/{len(moves)} ", style="bold cyan")
        progress.append(f"({direction.value})", style="dim")

        panel = Panel(
            Align.center(board_table),
            title=f"[bold cyan]Auto-Solve  {size}\u00d7{size}[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print()
        console.print(Align.center(panel))
        console.print(Align.center(progress))
        sys.stdout.flush()
        time.sleep(0.05)

    return f"[bold green]Solved in {len(moves)} moves![/bold green]"


# -- menu screen --------------------------------------------------------------


def _draw_menu(sel_size: int) -> None:
    """Draw the main menu."""
    console.clear()

    # Build size selector line
    sizes = Text()
    for s in range(3, 9):
        if s > 3:
            sizes.append("  ")
        if s == sel_size:
            sizes.append(f" {s}\u00d7{s} ", style="bold green on #313244")
        else:
            sizes.append(f" {s}\u00d7{s} ", style="dim")

    nav = Text("  \u2190 \u2192  change size", style="dim")

    # Build options
    opts = Text()
    opts.append("  1", style="bold cyan")
    opts.append("  Play    ")
    opts.append("2", style="bold yellow")
    opts.append("  Study    ")
    opts.append("3", style="dim bold")
    opts.append("  Scores    ", style="dim")
    opts.append("Q", style="dim bold")
    opts.append("  Quit", style="dim")

    body = Group(
        Text(""),
        Align.center(sizes),
        Align.center(nav),
        Text(""),
        Align.center(opts),
        Text(""),
    )

    panel = Panel(
        body,
        title="[bold]S L I D I N G   P U Z Z L E[/bold]",
        border_style="bright_blue",
        padding=(1, 4),
    )

    console.print()
    console.print(Align.center(panel))


# -- game screens -------------------------------------------------------------


def _draw_game(game: GamePlay, status: str = "") -> None:
    """Draw the game screen (play mode — stats visible, hint only)."""
    console.clear()

    size = game.size
    board_table = _render_board(game.state.board)

    stats = Text()
    stats.append("  Moves: ", style="dim")
    stats.append(str(game.state.moves), style="bold yellow")
    stats.append("    Time: ", style="dim")
    stats.append(_format_time(game.state.elapsed_time), style="bold yellow")

    controls = Text()
    controls.append("  \u2191\u2193\u2190\u2192", style="bold cyan")
    controls.append(" / ", style="dim")
    controls.append("WASD", style="bold cyan")
    controls.append("  move   ", style="dim")
    controls.append("N", style="bold cyan")
    controls.append("  hint   ", style="dim")
    controls.append("R", style="bold cyan")
    controls.append("  restart   ", style="dim")
    controls.append("Q", style="bold cyan")
    controls.append("  back", style="dim")

    panel = Panel(
        Align.center(board_table),
        title=f"[bold cyan]Sliding Puzzle  {size}\u00d7{size}[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2),
    )

    console.print()
    console.print(Align.center(panel))
    # Save cursor position right before the stats line so _update_time()
    # can later restore to this exact spot and overwrite only this line.
    sys.stdout.write("\033[s")
    sys.stdout.flush()
    console.print(Align.center(stats))
    if status:
        console.print(Align.center(Text.from_markup(f"  {status}")))
    console.print(Align.center(controls))


def _update_time(game: GamePlay) -> None:
    """Overwrite just the stats line using the saved cursor position.

    Uses raw ANSI codes (bypassing Rich) so only the single stats
    line is repainted — no flicker from a full redraw.
    """
    _DIM = "\033[2m"
    _YB = "\033[33;1m"
    _RS = "\033[0m"

    m, s = divmod(int(game.state.elapsed_time), 60)
    stats_raw = (
        f"{_DIM}Moves: {_RS}{_YB}{game.state.moves}{_RS}"
        f"    {_DIM}Time: {_RS}{_YB}{m:02d}:{s:02d}{_RS}"
    )

    # Centre the visible text to match what Rich would produce.
    visible_len = len(f"Moves: {game.state.moves}    Time: {m:02d}:{s:02d}")
    try:
        tw = console.width
    except Exception:
        tw = 80
    pad = max(0, (tw - visible_len) // 2)

    sys.stdout.write(f"\033[u\033[K{' ' * pad}{stats_raw}")
    sys.stdout.flush()


def _draw_study(game: GamePlay, status: str = "") -> None:
    """Draw the study screen (no stats, scramble/solve available)."""
    console.clear()

    size = game.size
    board_table = _render_board(game.state.board)

    controls = Text()
    controls.append("  \u2191\u2193\u2190\u2192", style="bold cyan")
    controls.append(" / ", style="dim")
    controls.append("WASD", style="bold cyan")
    controls.append("  move   ", style="dim")
    controls.append("R", style="bold yellow")
    controls.append("  scramble   ", style="dim")
    controls.append("N", style="bold cyan")
    controls.append("  hint   ", style="dim")
    controls.append("V", style="bold cyan")
    controls.append("  solve   ", style="dim")
    controls.append("Q", style="bold cyan")
    controls.append("  back", style="dim")

    panel = Panel(
        Align.center(board_table),
        title=f"[bold yellow]Study  {size}\u00d7{size}[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    )

    console.print()
    console.print(Align.center(panel))
    if status:
        console.print(Align.center(Text.from_markup(f"  {status}")))
    console.print(Align.center(controls))


def _draw_win(game: GamePlay) -> None:
    console.clear()

    size = game.size
    board_table = _render_board(game.state.board)

    congrats = Text()
    congrats.append("\n  \u2605 ", style="bold yellow")
    congrats.append("CONGRATULATIONS!", style="bold green")
    congrats.append("  You solved it!  ", style="green")
    congrats.append("\u2605\n", style="bold yellow")

    stats = Text()
    stats.append("  Moves: ", style="dim")
    stats.append(str(game.state.moves), style="bold yellow")
    stats.append("    Time: ", style="dim")
    stats.append(_format_time(game.state.elapsed_time), style="bold yellow")

    group = Group(
        Align.center(board_table),
        Align.center(congrats),
        Align.center(stats),
    )

    panel = Panel(
        group,
        title=f"[bold green]Sliding Puzzle  {size}\u00d7{size}[/bold green]",
        border_style="bold green",
        padding=(1, 2),
    )

    console.print()
    console.print(Align.center(panel))


def _draw_highscores(manager: HighScoreManager) -> None:
    """Full-screen high-scores view (used from the menu)."""
    console.clear()

    sizes = manager.get_all_sizes()
    parts: list[Align] = []

    if not sizes:
        parts.append(
            Align.center(Text("  No high scores yet.", style="dim"))
        )
    else:
        for size in sizes:
            hs_table = Table(
                title=f"{size}\u00d7{size}",
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
            parts.append(Align.center(hs_table))

    panel = Panel(
        Group(*parts) if parts else Text(""),
        title="[bold]HIGH  SCORES[/bold]",
        border_style="bright_blue",
        padding=(1, 2),
    )

    console.print()
    console.print(Align.center(panel))
    console.print(Align.center(Text("\n  Press any key to go back.\n", style="dim")))
    get_key()


# -- game loops ---------------------------------------------------------------


def _play_game(size: int, manager: HighScoreManager) -> None:
    """Play mode — hint only, scored."""
    while True:
        game = GamePlay(size)
        status = ""

        while not game.is_won:
            _draw_game(game, status)
            status = ""

            # Wait for input with a short timeout so the clock keeps ticking.
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
        _draw_win(game)

        entry = HighScoreEntry(
            moves=game.state.moves,
            time=round(game.state.elapsed_time, 2),
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        manager.add_score(size, entry)

        console.print(
            Align.center(
                Text(
                    "\n  Press R to play again, Q to go back.\n",
                    style="dim",
                )
            )
        )

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
        _draw_study(game, status)
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
            status = "[yellow]Scrambled![/yellow]"
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
    sel_size = 3

    while True:
        _draw_menu(sel_size)
        key = get_key()

        if key == "quit":
            console.clear()
            console.print(
                Align.center(Text("\nGoodbye!\n", style="bold cyan"))
            )
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
            _draw_highscores(manager)


# -- public entry point -------------------------------------------------------


def run(data_dir: Path) -> None:
    """Launch the Rich CLI with interactive menu."""
    _menu_loop(data_dir)
